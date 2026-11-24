# Monkey: Optimizing Bloom Filter Memory Allocation

DSC5003 · Track 2: Research Paper Replication

DENG Tianyu, XIA Tianquan, ZHANG Yue, LI Wenhao, and ZHAO Yining

We reproduced the Bloom filter allocation method from [Monkey: Optimal Navigable Key-Value Store](https://doi.org/10.1145/3035918.3064054) in a static Python implementation of a log-structured merge tree (LSM-tree). With 20,000 keys, four levels, a level-size ratio of 4, and a 12,500-byte filter budget, Monkey reduced the mean number of logical page accesses per unsuccessful lookup from **0.36978 to 0.18668**, a **49.5% reduction** across ten seeds. [Multi-seed results](results/robustness_seeds/summary.csv)

[Run the experiments](#run-the-experiments) · [Method](#method) · [Results](#results) · [References](#references) · [中文导读](#chinese-summary)

## Run the experiments

Use Python 3.12 and clone with submodules. The project imports a level-capacity helper directly from the pinned upstream checkout. [Third-party code and provenance](THIRD_PARTY.md)

```bash
git clone --recurse-submodules https://github.com/kelnether/monkey-bloom-filter-replication.git
cd monkey-bloom-filter-replication
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m unittest discover -s tests -v
```

For an existing checkout, run `git submodule update --init --recursive` before testing. GitHub's source ZIP omits submodule contents. In PyCharm, open the repository root, select `.venv/bin/python` as the interpreter, and use the repository root as the working directory. The reference runs used Python 3.12.6 and Matplotlib 3.11.2 on macOS ARM64.

```bash
run_dir="results/recheck_$(date +%Y%m%d_%H%M%S)"
for config in default robustness_seeds robustness_queries; do
  .venv/bin/python -m monkey_lab run \
    --config "configs/$config.json" --out "$run_dir/$config"
done
open "$run_dir/default/report.html"
```

The output directory for each run must be new or empty. Add `--no-plots` to a `run` command to produce data and CSVs with the standard library. Use `.venv/bin/python -m monkey_lab plot --out "$run_dir/default"` to rebuild the plots and HTML from an existing run. The last line of the example opens the HTML on macOS. On other systems, open it in a browser.

## Method

Each level has one sorted run. A lookup first probes the run's packed Bloom filter. On a positive result, it uses the page boundary keys (fence pointers) to find one candidate page, then searches that page. A hit ends the lookup. A miss checks all levels, and every false positive adds one logical page access. The static benchmark uses the same layout, query sequence, hash salts, and total filter budget for each strategy within a seed.

For a run with `n` keys, `m` filter bits, and `k` hash positions per key, the false-positive rate is approximated by `(1 - exp(-k*n/m))^k`. Using the continuous optimal hash count gives `p = exp(-(ln 2)^2 * m/n)`. A zero-byte filter always passes the lookup, giving `p = 1`. The expected miss cost is the sum of the rates across runs, by linearity of expectation.

- **Uniform allocation** gives each level the same bits per key, up to integer-byte rounding.
- **Monkey bisection** minimizes the sum of the continuous false-positive rates under a fixed budget. At the optimum, funded runs have the same ratio `p/n`, so smaller runs receive more bits per key. The implementation rounds down to whole bytes and assigns residual bytes by marginal gain.
- **Appendix C** starts with the bits in the first run and tries two-way transfers between pairs of runs. It retains a transfer when it improves the objective and leaves a positive donor allocation. After a full pass without an improvement, it halves the step down to one bit and then applies the shared whole-byte rule.

The filter uses a `bytearray`, deterministic SHAKE-256 hashes, and an integer hash count. Whole-byte rounding is part of this implementation. Its results need not equal the discrete optimum for arbitrary run sizes. These experiments count logical accesses to in-memory pages and bytes in the filter payload. [Allocation code](monkey_lab/allocation.py) · [Filter code](monkey_lab/bloom.py) · [Query path](monkey_lab/store.py)

### Workloads

The runs use seeded synthetic integer keys. The query labels follow membership in the saved key set. The default base case has 20,000 keys across four levels at ratio 4, five bits per key, up to 128 keys per page, and 5,000 unsuccessful lookups per seed. The default sweep changes one factor at a time and deduplicates identical cases.

| Configuration | What changes | Seeds |
| --- | --- | --- |
| [Default](configs/default.json) | Budget of 0, 2, 5, 8, or 10 bits/key, level-size ratio of 2, 4, or 10, level count of 2, 4, or 6, and miss fraction of 0%, 50%, or 100% | 1–3 |
| [Seed comparison](configs/robustness_seeds.json) | Two, four, and six levels at five bits/key, plus four levels at two bits/key. Includes the Appendix C allocator. | 1–10 |
| [Query-count comparison](configs/robustness_queries.json) | 5,000 or 20,000 misses against the same data and filters within each seed | 1–3 |

Per-level false-positive rates use the complete saved set of absent keys. Mixed workloads draw their misses from that set. Figures show a sample standard deviation across seeds. Relative reductions divide the difference between the two strategy means by the uniform mean.

## Results

### Default benchmark

Across three seeds, mean logical page accesses fell from **0.37387 to 0.18580** in the base case, a **50.3%** reduction. The ten-seed result at the top of this README uses the same base configuration with seven additional seeds. [Default summary](results/final/summary.csv) · [Experiment plots](results/final/report.html)

| Level | Keys | Uniform bytes | Monkey bytes | Uniform false-positive rate | Monkey false-positive rate |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 236 | 147 | 376 | 9.65% | 0.19% |
| 2 | 942 | 589 | 1,160 | 9.21% | 0.76% |
| 3 | 3,765 | 2,353 | 3,279 | 9.26% | 3.57% |
| 4 | 15,057 | 9,411 | 7,685 | 9.26% | 14.06% |

Monkey moves 1,726 bytes from the largest level to the three smaller levels. Their combined false-positive rate falls by about 23.61 percentage points, while the largest level's rate rises by 4.80 points. The net effect is about 0.18807 fewer logical page accesses per miss. A single lookup can trigger false positives at several levels. [Per-level records](results/final/levels.csv)

| Levels | Uniform mean ± SD | Monkey mean ± SD | Paired difference mean ± SD | Reduction |
| ---: | ---: | ---: | ---: | ---: |
| 2 | 0.18047 ± 0.00753 | 0.14133 ± 0.00605 | 0.03913 ± 0.01245 | 21.7% |
| 4 | 0.37387 ± 0.00533 | 0.18580 ± 0.00193 | 0.18807 ± 0.00530 | 50.3% |
| 6 | 0.55473 ± 0.00965 | 0.19480 ± 0.00100 | 0.35993 ± 0.01051 | 64.9% |

The level-count sweep holds the key count, size ratio, filter bytes, and all-miss workload fixed. Each paired difference subtracts the Monkey value from the uniform value for the same seed. [Level-count plot](results/final/figures/level_count.png) · [Per-seed records](results/final/experiments.csv)

- With no filter budget, a miss reads one page at each of the four levels. At 2, 5, 8, and 10 bits per key, the relative reductions were 49.1%, 50.3%, 50.4%, and 51.6%.
- As the level-size ratio rose from 2 to 4 to 10, the reduction rose from 21.7% to 50.3% to 63.5%. At a larger ratio, the same extra byte provides more bits per key in the smaller levels.
- At miss fractions of 0%, 50%, and 100%, the reductions were 17.5%, 25.1%, and 50.3%. A hit includes a read of the page containing the key and can skip later levels. [Budget, ratio, and miss-fraction plots](results/final/figures/benchmarks.png)

In the base case, the integer-hash-count model predicts **0.36800** accesses for uniform allocation and **0.18712** for Monkey. The absolute differences from measurement are about **0.00587** and **0.00132**, respectively. The formula approximates bit occupancy, while the benchmark probes the actual filters with 5,000 miss keys per seed. [Model comparison](results/final/figures/model_check.png)

### Seed and query-count checks

The ten-seed runs use 5,000 misses per seed, 20,000 keys, and a level-size ratio of 4. The columns below report mean logical accesses per query.

| Levels | Bits/key | Uniform | Monkey bisection | Appendix C | Paired difference mean ± SD | Reduction |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 5 | 0.18170 | 0.14586 | 0.14586 | 0.03584 ± 0.00980 | 19.7% |
| 4 | 5 | 0.36978 | 0.18668 | 0.18668 | 0.18310 ± 0.00671 | 49.5% |
| 6 | 5 | 0.55948 | 0.19254 | 0.19254 | 0.36694 ± 0.01741 | 65.6% |
| 4 | 2 | 1.57348 | 0.79816 | 0.79816 | 0.77532 ± 0.03111 | 49.3% |

In the four-level, five-bit case, the paired difference was positive for every seed, ranging from 0.1712 to 0.1934. Both Monkey solvers assigned 376, 1,160, 3,279, and 7,685 bytes in the base case, with a continuous objective of about 0.18677. Their whole-byte allocations and measured access counts matched in all four tested configurations. [Seed-level records](results/robustness_seeds/experiments.csv) · [Per-level records](results/robustness_seeds/levels.csv)

The query-count check keeps the data, per-level budget, hash salts, and hash counts fixed within each seed. Each short trial uses the first 5,000 queries of the corresponding 20,000-query trial. The samples share that prefix. The standard deviations describe variation across three seeds, including changes in data and filter salt.

| Miss queries per seed | Uniform mean ± SD | Monkey mean ± SD | Reduction |
| ---: | ---: | ---: | ---: |
| 5,000 | 0.37260 ± 0.01226 | 0.18660 ± 0.00597 | 49.9% |
| 20,000 | 0.36980 ± 0.00201 | 0.18703 ± 0.00520 | 49.4% |

[Multi-seed report](results/robustness_seeds/report.html) · [Query-count plot](results/robustness_queries/figures/query_count.png) · [Query-count summary](results/robustness_queries/summary.csv)

### Analytical parameter search

The model combines predictions for unsuccessful lookups, hits at the deepest run, range queries, and amortized updates. Its separate 128,000-byte budget covers the write buffer and filters, excluding fence pointers. The workload weights sum to one, and range queries have zero weight in the default search.

The grid evaluates 144 candidates using 100,000 entries at 128 bytes each and 4,096-byte pages. It crosses level-size ratios of 2, 4, 8, and 10, buffer shares of 5%, 20%, and 50%, leveling and tiering, both default filter strategies, and three write fractions. For Monkey at 10% and 50% writes, the lowest predicted costs use leveling at ratio 2 with buffer shares of 5% and 20%, respectively. At 90% writes, the selected candidate uses tiering at ratio 8 with a 20% buffer share. The search uses the model and this finite grid. The benchmark itself runs static point lookups. [Cost model](monkey_lab/model.py) · [Candidate CSV](results/final/model_search.csv) · [Grid winners](results/final/best_configs.json)

## Code and reproducibility

| File or directory | Role |
| --- | --- |
| [`monkey_lab/__main__.py`](monkey_lab/__main__.py) and [`experiments.py`](monkey_lab/experiments.py) | CLI, seeded workload generation, paired runs, correctness checks, and output files |
| [`upstream.py`](monkey_lab/upstream.py) | Load the pinned capacity helper and compute integer level sizes |
| [`allocation.py`](monkey_lab/allocation.py) and [`bloom.py`](monkey_lab/bloom.py) | Divide the budget, select the integer hash count, and store and probe filter bits |
| [`store.py`](monkey_lab/store.py) | Search static runs and count filter probes, logical page accesses, and false positives |
| [`model.py`](monkey_lab/model.py) and [`plotting.py`](monkey_lab/plotting.py) | Evaluate analytical costs and produce figures and HTML |
| [`tests/test_core.py`](tests/test_core.py) | Test budget conservation, filters, lookup correctness, and reproducibility |
| [`configs/`](configs/) | Experiment inputs and analytical grid settings |
| [`results/`](results/) | Saved input snapshots, measurements, predictions, provenance, and figures |
| [`vendor/predictive-lsm-trees/`](vendor/predictive-lsm-trees) | Pinned reference repository. The project reuses its capacity helper and adapts parts of its design. |

Each run saves the exact input in `datasets/` and `config.json`. The main CSVs are `experiments.csv` for each scenario, seed, and strategy, `levels.csv` for per-level measurements, and `summary.csv` for means and sample standard deviations. `model_search.csv` and `best_configs.json` contain model estimates and the grid winners. `metadata.json` records the environment, pinned upstream revision, and source file SHA-256 fingerprints from the run. The saved HTML is a readable view of the CSVs and figures.

| Saved run | Strategy records | Dataset snapshots | Checked query executions |
| --- | ---: | ---: | ---: |
| [Default](results/final/report.html) | 66 | 33 | 330,000 |
| [Seed comparison](results/robustness_seeds/report.html) | 120 | 40 | 600,000 |
| [Query-count comparison](results/robustness_queries/report.html) | 12 | 6 | 150,000 |
| **Total** | **198** | **79** | **1,080,000** |

All checked query answers matched the saved workload labels, and the filters returned zero false negatives on inserted keys. All 16 unit tests passed. A clean-clone rerun reproduced the dataset hashes, non-timing experiment fields, model results, and PNG plots. Build and query timings vary with machine and load. `demo` and `migration_check` contain earlier default runs and are outside the totals above. [Default metadata](results/final/metadata.json) · [Seed comparison metadata](results/robustness_seeds/metadata.json) · [Query-count metadata](results/robustness_queries/metadata.json) · [Upstream fingerprints](upstream_manifest.json)

## References

1. Niv Dayan, Manos Athanassoulis, and Stratos Idreos. 2017. *Monkey: Optimal Navigable Key-Value Store*. SIGMOD, 79–94. The replication uses the allocation objective in Section 4.1, the cost model in Section 4.2, and Appendices B and C. [DOI](https://doi.org/10.1145/3035918.3064054) · [Author PDF](https://cs-people.bu.edu/mathan/publications/sigmod17-dayan.pdf)
2. Zichen Zhu, Yanpeng Wei, Ju Hyoung Mun, and Manos Athanassoulis. 2025. *Mnemosyne: Dynamic Workload-Aware BF Tuning via Accurate Statistics in LSM trees*. PACMMOD 3(3), Article 190 (SIGMOD 2025). Covers dynamic filter reallocation and access statistics. [DOI](https://doi.org/10.1145/3725327)
3. Niv Dayan and Stratos Idreos. 2018. *Dostoevsky: Better Space-Time Trade-Offs for LSM-Tree Based Key-Value Stores via Adaptive Removal of Superfluous Merging*. SIGMOD, 505–520. Covers the effect of merge policy on read, update, and space costs. [DOI](https://doi.org/10.1145/3183713.3196927)
4. Russell Sears and Raghu Ramakrishnan. 2012. *bLSM: A General Purpose Log Structured Merge Tree*. SIGMOD, 217–228. Background on LSM design and merge scheduling. [DOI](https://doi.org/10.1145/2213836.2213862)
5. Manos Athanassoulis, Michael S. Kester, Lukas M. Maas, Radu Stoica, Stratos Idreos, Anastasia Ailamaki, and Mark Callaghan. 2016. *Designing Access Methods: The RUM Conjecture*. EDBT, 461–466. Frames the trade-offs among reads, updates, and memory or storage. [DOI](https://doi.org/10.5441/002/EDBT.2016.42)

[LevelDB](https://github.com/google/leveldb) was the basis of the paper's system experiments. [RocksDB](https://github.com/meta/rocksdb) is a related LSM-based engine. See [THIRD_PARTY.md](THIRD_PARTY.md) for the pinned Python reference and the exact reuse in this project.

## Chinese summary

本项目以 Python 复现 Monkey 的分层 Bloom filter 内存分配。固定过滤器预算时，十个种子的基础实验中，未命中查询的平均逻辑页访问数下降了 49.5%。[运行命令](#run-the-experiments) · [实验结果](#results)
