import itertools
import json
import math
import tempfile
import unittest
from pathlib import Path

from monkey_lab.allocation import allocate, model_sum
from monkey_lab.bloom import BloomFilter
from monkey_lab.experiments import run_case, aggregate, build_cases
from monkey_lab.model import cost_model, search_parameters
from monkey_lab.store import Run, StaticLSM, QueryStats
from monkey_lab.upstream import geometric_sizes, calculate_level_capacity


class AllocationTests(unittest.TestCase):
    def test_exact_byte_budget_and_zero(self):
        for budget in [0,1,2,3,11,100,1000]:
            for strategy in ['uniform','monkey']:
                a=allocate([10,100,1000],budget,strategy)
                self.assertEqual(sum(a),budget)
                self.assertTrue(all(type(x) is int and x>=0 for x in a))
        self.assertEqual(allocate([100,1000],0),[0,0])

    def test_small_exhaustive_oracle(self):
        sizes=[5,20,80]; budget=12
        oracle=min(model_sum(sizes,[a,b,budget-a-b]) for a,b in itertools.product(range(budget+1),repeat=2) if a+b<=budget)
        self.assertAlmostEqual(model_sum(sizes,allocate(sizes,budget)),oracle,places=10)

    def test_appendix_c_transfer_matches_small_oracle(self):
        sizes = [5, 20, 80]
        budget = 12
        result = allocate(sizes, budget, 'monkey_appendix_c')
        optimum = min(
            model_sum(sizes, [a, b, budget - a - b])
            for a in range(budget+1) for b in range(budget-a+1))
        self.assertEqual(sum(result), budget)
        self.assertTrue(all(type(value) is int and value >= 0 for value in result))
        self.assertAlmostEqual(model_sum(sizes, result), optimum)
        self.assertEqual(allocate(sizes, 0, 'monkey_appendix_c'), [0, 0, 0])

    def test_large_budget_kkt_proportionality(self):
        sizes=[1000,10000,100000]
        a=allocate(sizes,138750)
        rates=[math.exp(-math.log(2)**2*8*b/n)/n for n,b in zip(sizes,a)]
        self.assertLess(max(rates)/min(rates),1.005)
        self.assertLess(model_sum(sizes,a),model_sum(sizes,allocate(sizes,138750,'uniform')))

    def test_invalid_inputs(self):
        for sizes,budget in [([],1),([0],1),([1],-1),([1.5],1)]:
            with self.assertRaises(ValueError): allocate(sizes,budget)

    def test_geometric_sizes_and_real_upstream_reuse(self):
        self.assertEqual(calculate_level_capacity(3,2,4),48)
        for n,L,T in [(3,3,10),(111,3,10),(20000,6,4)]:
            sizes=geometric_sizes(n,L,T)
            self.assertEqual(sum(sizes),n)
            self.assertTrue(all(x>0 for x in sizes))


class FilterAndStoreTests(unittest.TestCase):
    def test_no_false_negatives_and_packed_storage(self):
        b=BloomFilter(1000,1250,7)
        for key in range(1000): b.add(key)
        self.assertTrue(all(b.might_contain(key) for key in range(1000)))
        self.assertIsInstance(b.bit_array,bytearray)
        self.assertEqual(len(b.bit_array),1250)
        rate=sum(b.might_contain(key) for key in range(1000,21000))/20000
        self.assertLess(abs(rate-b.predicted_fpr()),0.005)

    def test_zero_filter_and_key_encoding(self):
        b=BloomFilter(3,0)
        self.assertTrue(b.might_contain(5))
        b.add(-10)
        with self.assertRaises(TypeError): b.might_contain('5')

    def test_page_boundaries_and_misses(self):
        run=Run([0,2,4,6,8],0,1,entries_per_page=2)
        for key in range(-2,11):
            stats=QueryStats()
            value=run.get(key,stats)
            self.assertEqual(value,f'value:{key}' if key in [0,2,4,6,8] else None)
            self.assertEqual(stats.block_accesses,1)
            self.assertEqual(stats.false_positives,int(value is None))

    def test_store_short_circuit(self):
        store=StaticLSM([[1,3],[5,7],[9,11]],0,'monkey')
        self.assertEqual(store.get(1)[1].block_accesses,1)
        self.assertEqual(store.get(11)[1].block_accesses,3)
        self.assertEqual(store.get(12)[1].block_accesses,3)
        self.assertIsNone(store.get(12)[0])


class ModelAndExperimentTests(unittest.TestCase):
    def test_query_count_keeps_data_and_query_prefix_fixed(self):
        base = dict(entries=120, levels=3, ratio=3, bits_per_key=5,
                    miss_fraction=1, entries_per_page=8)
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            (out/'datasets').mkdir()
            small, small_levels = run_case(dict(base, queries=50), 42, out, query_pool_size=200)
            large, large_levels = run_case(dict(base, queries=200), 42, out, query_pool_size=200)
            data = [json.loads((out/'datasets'/f"{rows[0]['case']}.json").read_text())
                    for rows in (small, large)]
            self.assertEqual(data[0]['levels'], data[1]['levels'])
            self.assertEqual(data[0]['queries'], data[1]['queries'][:50])
            self.assertEqual(data[0]['absent_probes'], data[1]['absent_probes'][:50])
            for field in ('payload_bytes', 'hash_count', 'predicted_fpr'):
                self.assertEqual([r[field] for r in small_levels], [r[field] for r in large_levels])
            self.assertEqual({r['queries'] for r in aggregate(small+large)}, {50, 200})

    def test_sweep_deduplicates_numeric_equivalents(self):
        config={'experiment':{'miss_fraction':1.0,'bits_per_key':5},
                'sweeps':{'miss_fraction':[0,.5,1],'bits_per_key':[5.0,10]}}
        self.assertEqual(len(build_cases(config)),4)

    def test_t2_policies_equal_and_known_equations(self):
        kwargs=dict(entries=10000,entry_bytes=128,memory_bytes=16000,
                    buffer_fraction=.2,ratio=2,workload=[1,0,0,0])
        a=cost_model(**kwargs,policy='leveling')
        b=cost_model(**kwargs,policy='tiering')
        for key in ['R','V','W','Q','theta']: self.assertAlmostEqual(a[key],b[key])
        self.assertAlmostEqual(a['W'],a['levels']/32)
        self.assertAlmostEqual(a['theta'],a['R'])
        self.assertEqual(a['buffer_bytes']+a['filter_bytes'],16000)

    def test_invalid_workload(self):
        with self.assertRaises(ValueError):
            cost_model(entries=1000,entry_bytes=128,memory_bytes=16000,buffer_fraction=.2,
                       ratio=4,policy='leveling',workload=[1,0,0,1])

    def test_grid_winner_and_counts(self):
        config=dict(entries=10000,entry_bytes=128,memory_bytes=16000,page_bytes=4096,
                    ratios=[2,4],buffer_fractions=[.1,.5],write_fractions=[.1,.9],
                    miss_fraction_among_reads=.5)
        all_rows,best=search_parameters(config)
        self.assertEqual(len(all_rows),32)
        for winner in best:
            candidates=[r['theta'] for r in all_rows if r['strategy']==winner['strategy'] and r['write_fraction']==winner['write_fraction']]
            self.assertEqual(winner['theta'],min(candidates))

    def test_paired_experiment_ground_truth_and_reproducibility(self):
        cfg=dict(entries=120,levels=3,ratio=3,bits_per_key=2,queries=100,
                 miss_fraction=.5,entries_per_page=8)
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory); (out/'datasets').mkdir()
            rows,detail=run_case(cfg,42,out)
            repeat,_=run_case(cfg,42,out)
            self.assertEqual(rows[0]['filter_payload_bytes'],rows[1]['filter_payload_bytes'])
            self.assertEqual(rows[0]['dataset_sha256'],rows[1]['dataset_sha256'])
            self.assertEqual(rows[0]['measured_blocks'],repeat[0]['measured_blocks'])
            self.assertEqual(rows[0]['correct_queries'],100)
            self.assertEqual(len(detail),6)
            self.assertEqual(aggregate(rows+repeat)[0]['replicates'],2)
            data=json.loads(next((out/'datasets').glob('*.json')).read_text())
            truth=set(itertools.chain.from_iterable(data['levels']))
            self.assertTrue(all((key in truth)==present for key,present in data['queries']))
            self.assertTrue(truth.isdisjoint(data['absent_probes']))


if __name__=='__main__': unittest.main()
