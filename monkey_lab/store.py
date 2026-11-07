"""Adapted Run/Level lookup organization from predictive-lsm-trees.

Static, memory-resident sorted pages. Each filter-positive lookup accesses one
logical page selected by fence pointers. Counters are NOT physical disk I/O.
No min/max prefilter: isolates Bloom's expected sum-of-FPR objective.
"""
from bisect import bisect_left, bisect_right
from dataclasses import dataclass

from .allocation import allocate
from .bloom import BloomFilter


@dataclass
class QueryStats:
    filter_probes: int = 0
    block_accesses: int = 0
    false_positives: int = 0


class Run:
    def __init__(self, keys, budget_bytes, seed, entries_per_page=128):
        if entries_per_page < 1 or not keys or len(set(keys)) != len(keys):
            raise ValueError('run requires unique nonempty keys and positive page capacity')
        ordered = sorted(keys)
        self.pages = [ordered[i:i+entries_per_page] for i in range(0, len(ordered), entries_per_page)]
        self.page_min_keys = [page[0] for page in self.pages]
        self.bloom_filter = BloomFilter(len(keys), budget_bytes, seed)
        for key in keys:
            self.bloom_filter.add(key)

    def get(self, key, stats):
        stats.filter_probes += 1
        if not self.bloom_filter.might_contain(key):
            return None
        stats.block_accesses += 1
        page_id = max(0, bisect_right(self.page_min_keys, key)-1)
        page = self.pages[page_id]
        pos = bisect_left(page, key)
        if pos < len(page) and page[pos] == key:
            return f'value:{key}'
        stats.false_positives += 1
        return None


class Level:
    def __init__(self, runs):
        self.runs = runs

    def get(self, key, stats):
        # Upstream Level.get organization: newest run first, filter before data.
        for run in reversed(self.runs):
            value = run.get(key, stats)
            if value is not None:
                return value
        return None


class StaticLSM:
    def __init__(self, keys_by_level, budget_bytes, strategy, seed=0, entries_per_page=128):
        sizes = [len(keys) for keys in keys_by_level]
        self.allocation = allocate(sizes, budget_bytes, strategy)
        self.levels = [Level([Run(keys, b, seed*1000+i, entries_per_page)])
                       for i, (keys, b) in enumerate(zip(keys_by_level, self.allocation))]

    def get(self, key):
        stats = QueryStats()
        for level in self.levels:
            value = level.get(key, stats)
            if value is not None:
                return value, stats
        return None, stats

    @property
    def filters(self):
        return [level.runs[0].bloom_filter for level in self.levels]
