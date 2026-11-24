# Paper and third-party code provenance

## Original paper

Niv Dayan, Manos Athanassoulis, and Stratos Idreos. **Monkey: Optimal Navigable Key-Value Store**. SIGMOD 2017. [DOI 10.1145/3035918.3064054](https://doi.org/10.1145/3035918.3064054)

The replication draws on the allocation objective in Section 4.1, the cost model in Section 4.2, the derivation in Appendix B, and Algorithms 1–3 in Appendix C. The default `monkey` strategy solves the continuous KKT conditions by bisection. The `monkey_appendix_c` strategy adapts the iterative transfer routine with integer bit steps and the same byte remainder rule. Parameter tuning uses a finite grid. [Appendix C](https://nivdayan.github.io/monkeykeyvaluestore.pdf#page=15) · [Robustness checks](README.md#seed-and-query-count-checks)

## Reference implementation

The [predictive-lsm-trees reference source](https://github.com/fiidalgo/predictive-lsm-trees/tree/495e71a94559a845c76019740341745900a87666) informed several interfaces and the lookup organization. Its reference commit is `495e71a94559a845c76019740341745900a87666`. [upstream_manifest.json](upstream_manifest.json) records SHA-256 fingerprints for eight upstream files.

| Upstream file | Use in this project |
| --- | --- |
| `lsm/utils.py` | The archived runs called `calculate_level_capacity` through a Git submodule. The current [layout module](monkey_lab/layout.py) calculates geometric weights directly as powers of the size ratio. |
| `lsm/bloom.py` | The `BloomFilter` API informed `add`, `might_contain`, and `get_size_bytes`. The storage, hashing, and byte budget are implemented locally. |
| `lsm/traditional.py` | Informed the static level's lookup ordering and early exit. |
| `lsm/run.py` | Informed the run and page-minimum-key index. The local implementation counts accesses to in-memory pages. |

## Implementation differences

1. The upstream Bloom filter uses a Python Boolean list and reports its ideal packed size. This project stores individual bits in a `bytearray` and reports the payload bytes.
2. Upstream target false-positive rates grow by a factor of ten with a cap of 0.5. Here, the allocation uses each run's key count and a fixed global byte budget, including zero-byte filters.
3. Some upstream reads deserialize an entire run. This project keeps pages in memory and counts logical page accesses.
4. The upstream project also contains a classifier, learned filters, dynamic merging, and persistence. The local benchmark uses a static layout with prebuilt levels and pages.

The Git submodule is available in the [historical repository snapshot](https://github.com/kelnether/monkey-bloom-filter-replication/tree/db067a223df46f6e797b6de96e4a757c78a2d656). The archived metadata retains the upstream commit used for those runs. Current runs record the hashes of the local Python sources. At the reference commit, the upstream README links to an MIT License and the tree has no separate `LICENSE` file.
