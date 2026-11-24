"""Analytical predictions, not measurements of a dynamic storage engine.

Finite run sizes + optimized Bloom allocation; W and Q follow Monkey Eq.10/11.
V is the worst-position successful lookup, not an average over hit locations.
Memory budget in this module covers buffer + filters, excluding fence pointers.
"""
import math

from .allocation import allocate, model_sum, fpr
from .layout import geometric_sizes


def cost_model(*, entries, entry_bytes, memory_bytes, buffer_fraction, ratio,
               policy, workload, page_bytes=4096, range_fraction=0.01,
               write_read_cost_ratio=1.0, strategy='monkey'):
    if entries < 1 or entry_bytes < 1 or memory_bytes < entry_bytes:
        raise ValueError('invalid data or memory size')
    if not 0 < buffer_fraction < 1 or ratio < 2 or policy not in ('leveling', 'tiering'):
        raise ValueError('invalid configuration')
    if len(workload) != 4 or any(not math.isfinite(x) or x < 0 for x in workload) or not math.isclose(sum(workload), 1):
        raise ValueError('workload [miss,hit,range,write] must be nonnegative and sum to 1')
    if not 0 <= range_fraction <= 1 or write_read_cost_ratio < 0:
        raise ValueError('invalid range selectivity or write/read cost')
    B = page_bytes // entry_bytes
    if B < 1:
        raise ValueError('a page must fit at least one entry')
    buffer_bytes = max(entry_bytes, int(memory_bytes*buffer_fraction))
    if buffer_bytes >= memory_bytes:
        raise ValueError('memory must leave room for filters')
    buffer_entries = buffer_bytes // entry_bytes
    # Minimum levels whose geometric capacities can hold the disk population.
    L, capacity, cumulative = 1, buffer_entries*ratio, buffer_entries*ratio
    while cumulative < entries:
        capacity *= ratio
        cumulative += capacity
        L += 1
    sizes = geometric_sizes(entries, L, ratio)
    if policy == 'tiering':
        # Full-tier approximation; distribute each level among T-1 nonempty runs.
        run_sizes = []
        for n in sizes:
            count = min(ratio-1, n)
            q, extra = divmod(n, count)
            run_sizes.extend(q + (i < extra) for i in range(count))
    else:
        run_sizes = sizes
    budgets = allocate(run_sizes, memory_bytes-buffer_bytes, strategy)
    R = model_sum(run_sizes, budgets)
    V = R - fpr(8*budgets[-1], run_sizes[-1]) + 1
    W = L/B * (ratio-1)/(2 if policy == 'leveling' else ratio) * (1+write_read_cost_ratio)
    Q = range_fraction*entries/B + len(run_sizes)
    theta = sum(x*y for x,y in zip(workload, [R,V,Q,W]))
    return dict(policy=policy, ratio=ratio, buffer_fraction=buffer_fraction,
                levels=L, buffer_bytes=buffer_bytes, filter_bytes=sum(budgets),
                strategy=strategy, R=R, V=V, W=W, Q=Q, theta=theta,
                run_count=len(run_sizes))


def search_parameters(config):
    rows = []
    for write_fraction in config['write_fractions']:
        reads = 1-write_fraction
        workload = [reads*config['miss_fraction_among_reads'],
                    reads*(1-config['miss_fraction_among_reads']), 0, write_fraction]
        for strategy in ('uniform', 'monkey'):
            for policy in ('leveling', 'tiering'):
                for ratio in config['ratios']:
                    for fraction in config['buffer_fractions']:
                        row = cost_model(entries=config['entries'], entry_bytes=config['entry_bytes'],
                                         memory_bytes=config['memory_bytes'], buffer_fraction=fraction,
                                         ratio=ratio, policy=policy, workload=workload,
                                         page_bytes=config['page_bytes'], strategy=strategy)
                        row['write_fraction'] = write_fraction
                        rows.append(row)
    best = []
    for write_fraction in config['write_fractions']:
        for strategy in ('uniform', 'monkey'):
            candidates = [r for r in rows if r['write_fraction']==write_fraction and r['strategy']==strategy]
            best.append(min(candidates, key=lambda r: r['theta']))
    return rows, best
