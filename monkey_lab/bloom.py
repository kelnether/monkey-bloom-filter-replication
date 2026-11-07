"""Adapted BloomFilter API from upstream lsm/bloom.py; storage/hash rewritten.

The original used a bool list and mmh3. Here the budget is physical bytearray
payload, and SHAKE-256 provides reproducible hash positions without extensions.
"""
import hashlib
import math


class BloomFilter:
    def __init__(self, expected_elements, budget_bytes, seed=0):
        if expected_elements <= 0 or budget_bytes < 0:
            raise ValueError('positive entries and nonnegative byte budget required')
        self.expected_elements = expected_elements
        self.bit_array = bytearray(budget_bytes)
        self.size = budget_bytes * 8
        self.salt = f'{seed}:'.encode()
        optimum = self.size / expected_elements * math.log(2)
        candidates = sorted({max(1, math.floor(optimum)), max(1, math.ceil(optimum))})
        self.hash_count = min(candidates, key=self.predicted_fpr) if self.size else 0

    def predicted_fpr(self, k=None):
        if not self.size:
            return 1.0
        k = self.hash_count if k is None else k
        return (-math.expm1(-k*self.expected_elements/self.size)) ** k

    def _get_hash_values(self, item):
        if type(item) is not int:
            raise TypeError('this lab uses integer keys')
        digest = hashlib.shake_256(self.salt + str(item).encode()).digest(8*self.hash_count)
        for j in range(self.hash_count):
            yield int.from_bytes(digest[8*j:8*j+8], 'little') % self.size

    def add(self, item):
        for pos in self._get_hash_values(item):
            self.bit_array[pos//8] |= 1 << (pos % 8)

    def might_contain(self, item):
        return all(self.bit_array[p//8] & (1 << (p % 8)) for p in self._get_hash_values(item))

    def get_size_bytes(self):
        return len(self.bit_array)
