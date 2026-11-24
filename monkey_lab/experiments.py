"""Paired static workloads, per-level FPRs, and complete reproducibility metadata."""
import csv
import hashlib
import json
import math
import platform
import random
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

from .allocation import model_sum
from .layout import geometric_sizes
from .model import search_parameters
from .store import StaticLSM


def workload(total, sizes, query_count, miss_fraction, seed):
    rng = random.Random(seed)
    keys = rng.sample(range(20*(total+query_count)), total+query_count)
    levels, start = [], 0
    for n in sizes:
        levels.append(keys[start:start+n])
        start += n
    # Probe FPR independently even in a 100% hit query workload.
    absent = keys[total:]
    misses = round(query_count*miss_fraction)
    queries = [(key, False) for key in absent[:misses]]
    queries.extend((rng.choice(keys[:total]), True) for _ in range(query_count-misses))
    rng.shuffle(queries)
    return levels, queries, absent


def run_case(config, seed, out_dir, *, query_pool_size=None, include_appendix_c=False):
    total, ratio, count = config['entries'], config['ratio'], config['levels']
    sizes = geometric_sizes(total, count, ratio)
    query_count = config['queries']
    levels, queries, absent = workload(
        total, sizes, query_pool_size or query_count, config['miss_fraction'], seed)
    signature = f"n{total}_l{count}_t{ratio}_b{config['bits_per_key']:g}_m{config['miss_fraction']:g}_s{seed}"
    if query_pool_size is not None:
        # The pool is all misses. Use the same prefix for lookup and FPR measurement.
        queries = queries[:query_count]
        absent = [key for key, _ in queries]
        signature += f'_q{query_count}'
    budget = math.floor(total*config['bits_per_key']/8)
    serialized = json.dumps({'levels': levels, 'queries': queries, 'absent_probes': absent}, separators=(',',':'))
    digest = hashlib.sha256(serialized.encode()).hexdigest()
    (out_dir/'datasets'/f'{signature}.json').write_text(serialized)
    rows, detail = [], []
    strategies = ('uniform', 'monkey')
    if include_appendix_c:
        strategies += ('monkey_appendix_c',)
    for strategy in strategies:
        start = time.perf_counter()
        store = StaticLSM(levels, budget, strategy, seed, config['entries_per_page'])
        build_seconds = time.perf_counter()-start
        # Exhaustive no-FN verification of filters on all inserted keys.
        for keys, bloom in zip(levels, store.filters):
            if not all(bloom.might_contain(key) for key in keys):
                raise AssertionError('false negative in Bloom filter')
        access, false_positive, probes = [], [], []
        start = time.perf_counter()
        for key, present in queries:
            value, stats = store.get(key)
            if value != (f'value:{key}' if present else None):
                raise AssertionError('query result differs from generated ground truth')
            access.append(stats.block_accesses)
            false_positive.append(stats.false_positives)
            probes.append(stats.filter_probes)
        query_seconds = time.perf_counter()-start
        empirical = []
        predicted = []
        for i, (keys, bloom) in enumerate(zip(levels, store.filters)):
            fp = sum(bloom.might_contain(key) for key in absent)/len(absent)
            empirical.append(fp)
            predicted.append(bloom.predicted_fpr())
            detail.append(dict(case=signature, strategy=strategy, seed=seed, level=i+1,
                               entries=len(keys), payload_bytes=bloom.get_size_bytes(),
                               bits_per_key=bloom.size/len(keys), hash_count=bloom.hash_count,
                               measured_fpr=fp, predicted_fpr=bloom.predicted_fpr()))
        # Expected mixed-workload cost using exact hit positions and integer-k model.
        owner = {key:i for i,keys in enumerate(levels) for key in keys}
        mixed_prediction = statistics.mean(1+sum(predicted[:owner[key]]) if present else sum(predicted)
                                            for key,present in queries)
        rows.append(dict(case=signature, strategy=strategy, seed=seed, entries=total,
                         levels=count, ratio=ratio, bits_per_key=config['bits_per_key'],
                         requested_miss_fraction=config['miss_fraction'],
                         actual_miss_fraction=sum(not p for _,p in queries)/len(queries),
                         queries=len(queries), dataset_sha256=digest,
                         filter_payload_bytes=sum(b.get_size_bytes() for b in store.filters),
                         measured_blocks=statistics.mean(access),
                         measured_false_positives=statistics.mean(false_positive),
                         measured_filter_probes=statistics.mean(probes),
                         measured_absent_blocks=sum(empirical),
                         continuous_absent_model=model_sum(sizes,store.allocation),
                         integer_k_absent_model=sum(predicted), mixed_model=mixed_prediction,
                         build_seconds=build_seconds, python_query_seconds=query_seconds,
                         correct_queries=len(queries), false_negatives=0))
    return rows, detail


def csv_write(path, rows):
    if not rows:
        raise ValueError('cannot write empty result table')
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def aggregate(rows):
    grouping = ['strategy','entries','levels','ratio','bits_per_key','requested_miss_fraction']
    if len({row['queries'] for row in rows}) > 1:
        grouping.append('queries')
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row[k] for k in grouping)].append(row)
    result = []
    for key, group in groups.items():
        row = dict(zip(grouping,key))
        row['replicates'] = len(group)
        for metric in ['measured_blocks','measured_absent_blocks','mixed_model','integer_k_absent_model','continuous_absent_model']:
            values = [g[metric] for g in group]
            row[metric+'_mean'] = statistics.mean(values)
            row[metric+'_sd'] = statistics.stdev(values) if len(values)>1 else 0.0
        result.append(row)
    return result


def build_cases(config):
    base = config['experiment']
    cases = [dict(base)]
    sweep_fields = {'bits_per_key', 'ratio', 'miss_fraction', 'levels'}
    if 'query_pool_size' in config:
        sweep_fields.add('queries')
    for name, values in config['sweeps'].items():
        if name not in sweep_fields:
            raise ValueError('unknown sweep '+name)
        cases.extend(dict(base, **{name:value}) for value in values)
    # Numeric equality matters: JSON 1 and 1.0 describe the same scenario.
    return list({tuple(sorted(c.items())):c for c in cases}.values())


def run_all(config_path, output):
    config = json.loads(Path(config_path).read_text())
    base = config['experiment']
    if base['entries'] < base['levels'] or base['queries'] < 1 or base['entries_per_page'] < 1:
        raise ValueError('invalid data/query/page size')
    if not config['seeds'] or len(set(config['seeds'])) != len(config['seeds']):
        raise ValueError('provide distinct random seeds')
    cases = build_cases(config)
    query_pool_size = config.get('query_pool_size')
    if 'query_pool_size' in config:
        if type(query_pool_size) is not int or any(
                type(c['queries']) is not int or not 1 <= c['queries'] <= query_pool_size
                or c['miss_fraction'] != 1 for c in cases):
            raise ValueError('query_pool_size requires integer query counts within the pool and all-miss workloads')
    include_appendix_c = config.get('include_appendix_c', False)
    if type(include_appendix_c) is not bool:
        raise ValueError('include_appendix_c must be a boolean')
    for c in cases:
        if c['bits_per_key'] < 0 or not math.isfinite(c['bits_per_key']) or not 0<=c['miss_fraction']<=1:
            raise ValueError('invalid memory or miss fraction')
        geometric_sizes(c['entries'], c['levels'], c['ratio'])
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError('output directory must be new or empty; preserves previous runs')
    (output/'datasets').mkdir(parents=True, exist_ok=True)
    (output/'config.json').write_text(json.dumps(config,indent=2)+'\n')
    records, detail = [], []
    for i,c in enumerate(cases):
        for seed in config['seeds']:
            rows, levels = run_case(
                c, seed, output, query_pool_size=query_pool_size, include_appendix_c=include_appendix_c)
            records.extend(rows)
            detail.extend(levels)
        print(f'Completed scenario {i+1}/{len(cases)}: {c}',flush=True)
    summary = aggregate(records)
    costs, best = search_parameters(config['model_search'])
    csv_write(output/'experiments.csv', records)
    csv_write(output/'levels.csv', detail)
    csv_write(output/'summary.csv', summary)
    csv_write(output/'model_search.csv', costs)
    (output/'best_configs.json').write_text(json.dumps(best,indent=2)+'\n')
    source = Path(__file__).resolve().parent
    metadata = {'python':sys.version,'platform':platform.platform(),'machine':platform.machine(),
                'core_file_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in sorted(source.glob('*.py'))},
                'measurement':'in-memory logical block probes, not physical I/O',
                'memory':'filter bytearray payload only; excludes data and Python object overhead'}
    (output/'metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    return output
