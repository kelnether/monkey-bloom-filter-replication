# Monkey: Optimizing Bloom Filter Memory Allocation

**DSC5003 Storing and Retrieving Data · Track 2 · Research Paper Replication**

DENG Tianyu, XIA Tianquan, ZHANG Yue, LI Wenhao, and ZHAO Yining

We reproduce the Bloom filter allocation method from *Monkey: Optimal Navigable Key-Value Store* (SIGMOD 2017) in a static Python implementation of a log-structured merge tree (LSM-tree). With 20,000 keys, four levels, a level-size ratio of 4, and a 12,500-byte filter budget, Monkey reduced mean logical page accesses per unsuccessful lookup from **0.36978 to 0.18668 (49.5%)** across ten seeds. [Paper](https://doi.org/10.1145/3035918.3064054) · [Multi-seed results](results/robustness_seeds/summary.csv)

[Quick start](#quick-start) · [Project overview](#project-overview) · [Repository structure](#repository-structure) · [Method](#method) · [Evaluation](#experiments-and-datasets) · [Correctness](#correctness-and-reproducibility) · [Results](#results) · [Lessons learned](#challenges-and-lessons-learned) · [References](#references) · [Deliverables](#links-to-deliverables) · [中文导读](#chinese-summary)

## Quick start

### Install and test

Use **Git** to clone and **Python 3.12** to run the project. The core implementation, tests, and CSV-only runs use the Python standard library. Install the locked dependencies to generate figures and HTML reports. The archived runs used Python 3.12.6 and Matplotlib 3.11.2 on macOS ARM64. [Dependency lock](requirements-lock.txt)

```bash
git clone https://github.com/kelnether/monkey-bloom-filter-replication.git
cd monkey-bloom-filter-replication
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m unittest discover -s tests -v
```

For an existing checkout, start at the repository root before creating the environment. In PyCharm, use that root as the working directory and select `.venv/bin/python` as the interpreter. You can skip the pip command for tests and runs with `--no-plots`.

### Run the default benchmark

```bash
run_dir=$(mktemp -d results/recheck.XXXXXX)
.venv/bin/python -m monkey_lab run --config configs/default.json --out "$run_dir/default"
```

Open the printed `report.html` path in a browser. The default suite produces **66 strategy records and 33 synthetic dataset snapshots**. The `run` command requires a new or empty `--out` directory to protect the archived results.

### Run the robustness checks

Use the same `run_dir` from the default benchmark.

```bash
for config in robustness_seeds robustness_queries; do
  .venv/bin/python -m monkey_lab run \
    --config "configs/$config.json" --out "$run_dir/$config"
done
```

For a CSV-only run, append `--no-plots` to the `run` command. To generate or regenerate figures and HTML from the saved outputs, run `.venv/bin/python -m monkey_lab plot --out "$run_dir/default"` with the plotting dependencies installed.

## Project overview

**Replicated paper.** Niv Dayan, Manos Athanassoulis, and Stratos Idreos. *Monkey: Optimal Navigable Key-Value Store*. ACM SIGMOD 2017, pp. 79–94. [DOI](https://doi.org/10.1145/3035918.3064054)

**Motivation.** Bloom filters consume a shared memory budget in an LSM-tree. Monkey gives a testable prediction about how reallocating that memory changes search cost. We chose the allocation problem because keeping the dataset, workload, layout, and total budget fixed isolates the cost of a single design choice. Per-level measurements then show which filters account for the change in lookup cost.

## Repository structure

| Path | What to review |
| --- | --- |
| [`monkey_lab/allocation.py`](monkey_lab/allocation.py) | Uniform baseline, Monkey bisection, and Appendix C allocation |
| [`monkey_lab/bloom.py`](monkey_lab/bloom.py) and [`store.py`](monkey_lab/store.py) | Packed Bloom filters, static LSM-tree point lookups, and logical page-access counters |
| [`monkey_lab/__main__.py`](monkey_lab/__main__.py) and [`experiments.py`](monkey_lab/experiments.py) | CLI, seeded dataset generation, paired benchmarks, correctness checks, and result export |
| [`monkey_lab/model.py`](monkey_lab/model.py) and [`plotting.py`](monkey_lab/plotting.py) | Analytical cost model, parameter grid search, figures, and HTML reports |
| [`monkey_lab/layout.py`](monkey_lab/layout.py) | Geometric level sizes with integer rounding and exact key-count conservation |
| [`tests/test_core.py`](tests/test_core.py) | Unit and integration tests for the allocators, filtering and lookup, and reproducible experiments |
| [`configs/`](configs/) | Three runnable experiment suites |
| [`results/`](results/) | Saved synthetic datasets, measurements, predictions, figures, and run metadata |
| [`THIRD_PARTY.md`](THIRD_PARTY.md) and [`upstream_manifest.json`](upstream_manifest.json) | Paper attribution, design influences, and the upstream revision used for the archived runs |

## Method

### Technical design

The paper tunes per-level false-positive rates to minimize the expected I/O cost of a zero-result lookup under a shared filter budget. It also models lookup and update costs to tune buffer size, level-size ratio, and compaction policy. The replication implements the allocation objective from Section 4.1 and Appendix B, adapts the iterative solver in Appendix C, and uses the cost equations from Section 4.2 in a separate analytical experiment. [Original paper](https://cs-people.bu.edu/mathan/publications/sigmod17-dayan.pdf) · [Cost model](monkey_lab/model.py)

| Component | Implementation choice and scope |
| --- | --- |
| Storage engine | The paper modifies LevelDB. Here, a static Python LSM-tree holds one sorted run per level in memory. The benchmark measures point lookups with a fixed layout. |
| Filter tuning | The default strategy solves for the continuous allocation by bisection and converts it to whole bytes. The Appendix C transfer algorithm is a separate comparison. Filters use an integer hash count. |
| System tuning | The paper searches the design space for a system configuration. This project evaluates a finite grid of modeled configurations, including leveling and tiering. Buffer operations, compaction, updates, and range scans are represented by cost estimates where applicable. |

### Algorithm and system implementation

The benchmark assigns seeded keys to geometric levels. Each run stores sorted pages, an array of page-minimum fence keys, and a packed Bloom filter. On a positive filter result, binary search on the fence keys selects one candidate page, and a second binary search checks that page. A hit ends the lookup. A miss checks all levels, and every false positive adds one logical page access. [Layout](monkey_lab/layout.py) · [Lookup code and counters](monkey_lab/store.py)

For a run with `n` keys, `m` filter bits, and `k` hash positions per key, the false-positive rate is approximated by `(1 - exp(-k*n/m))^k`. Using the continuous optimal hash count gives `p = exp(-(ln 2)^2 * m/n)`. A zero-byte filter always passes the lookup, giving `p = 1`. The expected miss cost sums these rates across runs.

| Strategy | Budget allocation |
| --- | --- |
| `uniform` | Assigns the same bits per key, up to whole-byte rounding. |
| `monkey` | Uses bisection to minimize the sum of continuous false-positive rates. Funded runs have equal `p/n` at the continuous optimum, so smaller runs receive more bits per key. The solver rounds down and assigns residual bytes by marginal gain. |
| `monkey_appendix_c` | Starts with the budget in the first run and tests transfers between pairs of runs. It keeps improving transfers with a positive donor balance and halves the step after a full pass without improvement. It finishes at a one-bit step, then uses the shared whole-byte rule. |

The filter uses a `bytearray`, deterministic SHAKE-256 hashing, and an integer hash count. Whole-byte rounding adjusts the continuous allocation to the byte budget. [Allocation code](monkey_lab/allocation.py) · [Filter code](monkey_lab/bloom.py) · [Query path](monkey_lab/store.py)

## Experiments and datasets

The base case has 20,000 synthetic integer keys across four levels at ratio 4, five filter bits per key, up to 128 keys per page, and 5,000 unsuccessful lookups per seed. The default sweep varies one factor at a time. Each strategy within a scenario and seed uses the same level layout, query sequence, hash salts, and total filter budget.

The primary metric is **logical page accesses per point lookup**. The benchmark also records measured and predicted per-level false-positive rates, filter probes, and filter payload bytes. Python timings are recorded for context and depend on the run environment. The memory metric covers the Bloom filter bits and excludes data pages, fence pointers, and Python object overhead.

| Configuration | What changes | Seeds | Saved run |
| --- | --- | --- | --- |
| [Default](configs/default.json) | Filter budget (0, 2, 5, 8, or 10 bits/key), level-size ratio (2, 4, or 10), levels (2, 4, or 6), and miss fraction (0%, 50%, or 100%) | 1–3 | [`results/final/`](results/final/) |
| [Seed comparison](configs/robustness_seeds.json) | Two, four, and six levels at five bits/key, plus four levels at two bits/key. Includes the Appendix C allocator. | 1–10 | [`results/robustness_seeds/`](results/robustness_seeds/) |
| [Query-count comparison](configs/robustness_queries.json) | 5,000 or 20,000 misses against the same data and filters within each seed | 1–3 | [`results/robustness_queries/`](results/robustness_queries/) |

[`workload()`](monkey_lab/experiments.py) generates the data from the configuration and seed. Each run writes one JSON snapshot per scenario and seed in `datasets/`. A snapshot contains `levels` (keys by level), `queries` (query key and expected membership), and `absent_probes` (keys used to measure per-level false-positive rates). In mixed workloads, the misses come from the saved absent-probe set. [Saved datasets](results/final/datasets/) · [Base-case snapshot](results/final/datasets/n20000_l4_t4_b5_m1_s1.json)

### Output files

| File or directory | Contents |
| --- | --- |
| [`config.json`](results/final/config.json) and [`metadata.json`](results/final/metadata.json) | Run configuration, Python and platform details, and source SHA-256 fingerprints. Archived runs also record the upstream revision used at the time. |
| [`experiments.csv`](results/final/experiments.csv) | Per-scenario, per-seed, per-strategy results, including filter bytes, dataset hash, logical accesses, correctness, and Python timings |
| [`levels.csv`](results/final/levels.csv) | Keys, allocated bytes, hash count, and measured and predicted false-positive rates by level |
| [`summary.csv`](results/final/summary.csv) | Means and sample standard deviations across seeds |
| [`model_search.csv`](results/final/model_search.csv) and [`best_configs.json`](results/final/best_configs.json) | Analytical grid candidates and the lowest-cost candidate for each strategy and write fraction |
| [`figures/`](results/final/figures/) and `report.html` | PNG and SVG figures and a local HTML report. Open the report from a clone to load the linked figures and CSVs. |

## Correctness and reproducibility

The 17 tests cover exact byte budgets, a small exhaustive allocation check, zero-budget filters, false negatives, page boundaries, query early exit, repeated experiments, and the CLI output argument. The benchmark verifies each inserted key against its filter and checks every point lookup against its saved label. For the same scenario and seed, compare `dataset_sha256` and `filter_payload_bytes` across strategies in `experiments.csv` to verify the pairing.

| Saved run | Strategy records | Dataset snapshots | Checked query executions |
| --- | ---: | ---: | ---: |
| [Default](results/final/experiments.csv) | 66 | 33 | 330,000 |
| [Seed comparison](results/robustness_seeds/experiments.csv) | 120 | 40 | 600,000 |
| [Query-count comparison](results/robustness_queries/experiments.csv) | 12 | 6 | 150,000 |
| **Total** | **198** | **79** | **1,080,000** |

All query answers matched the saved labels, and the filters returned zero false negatives on inserted keys. A Python 3.12 rerun reproduced all 79 dataset hashes and the non-timing experiment and model fields. Build and query timings vary with the machine and load. [`results/demo/`](results/demo/) and [`results/migration_check/`](results/migration_check/) are earlier default runs outside the totals above.

## Results

### Default benchmark

Across three seeds, mean logical page accesses fell from **0.37387 to 0.18580** in the base case, a **50.3%** reduction. The ten-seed result at the top of this README uses the same base configuration with seven additional seeds. [Default summary](results/final/summary.csv) · [Benchmark figures](results/final/figures/benchmarks.png)

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

The level-count sweep holds the key count, size ratio, filter bytes, and all-miss workload fixed. Each paired difference subtracts the Monkey value from the uniform value for the same seed. [Per-seed records](results/final/experiments.csv)

![Mean logical page accesses per miss for two, four, and six levels, with error bars showing one sample standard deviation across seeds](results/final/figures/level_count.png)

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

[Multi-seed summary](results/robustness_seeds/summary.csv) · [Query-count plot](results/robustness_queries/figures/query_count.png) · [Query-count summary](results/robustness_queries/summary.csv)

### Analytical parameter search

The model combines predictions for unsuccessful lookups, hits at the deepest run, range queries, and amortized updates. Its separate 128,000-byte budget covers the write buffer and filters, excluding fence pointers. The workload weights sum to one, and range queries have zero weight in the default search.

The grid evaluates 144 candidates using 100,000 entries at 128 bytes each and 4,096-byte pages. It crosses level-size ratios of 2, 4, 8, and 10, buffer shares of 5%, 20%, and 50%, leveling and tiering, both default filter strategies, and three write fractions. For Monkey at 10% and 50% writes, the lowest predicted costs use leveling at ratio 2 with buffer shares of 5% and 20%, respectively. At 90% writes, the selected candidate uses tiering at ratio 8 with a 20% buffer share. The search uses the model and this finite grid. The benchmark itself runs static point lookups. [Cost model](monkey_lab/model.py) · [Candidate CSV](results/final/model_search.csv) · [Grid winners](results/final/best_configs.json)

### Comparison with the original paper

| Original result | Evidence from this replication |
| --- | --- |
| Figure 7 predicts equal unsuccessful-lookup cost at zero filter memory and lower cost under Monkey at positive budgets. Figure 11(C) observes the same direction in the LevelDB memory sweep. | At zero bits per key, both strategies averaged 4.0 logical page accesses per miss. At every positive tested budget (2, 5, 8, and 10 bits per key), Monkey averaged fewer accesses. [Budget sweep](results/final/figures/benchmarks.png) |
| Figure 11(A) varies data volume and reports that Monkey's latency advantage grows with data size. | The level-count sweep keeps the dataset size at 20,000 keys. The gap grew from 21.7% at two levels to 64.9% at six levels. This supports the level-count mechanism under a fixed data size. [Level-count results](results/final/summary.csv) |

The empirical results in Section 5 come from a modified LevelDB on disk. Its default workload uses 1 GB of data, 1 KB entries, a level-size ratio of 2, and 16K unsuccessful lookups. Here, the ten-seed base case uses 20,000 integer keys, a size ratio of 4, and 5,000 unsuccessful lookups per seed. The **49.5%** reduction measures logical page accesses in the static benchmark. The paper's **50–80%** figure measures lookup latency across its data sizes. The comparison concerns the direction and mechanism of the improvement. [Paper, Section 5 and Figure 11](https://cs-people.bu.edu/mathan/publications/sigmod17-dayan.pdf#page=10)

## Challenges and lessons learned

- **Preserving the exact byte budget.** The optimizer produces a continuous solution, while the filter stores whole bytes and uses an integer hash count. Assigning the residual bytes explicitly preserves the budget. Testing a small case against exhaustive allocations and checking the Appendix C solver provided two independent checks on the allocation logic.
- **Isolating the effect of the allocator.** Independent data or hash salts would make the allocator comparison harder to interpret. Pairing strategies on the same dataset, workload, salts, and budget makes the differences traceable to filter allocation. The query-count check also holds each seed's layout fixed and uses a shared query prefix.
- **Interpreting the metric.** Moving filter bytes away from the largest level can increase its false-positive rate while reducing the total page reads. Per-level measurements explain this trade-off. Logical accesses quantify the lookup mechanism in a static layout. Measuring disk latency, compaction, or throughput would require a storage-engine experiment.

## References

1. Niv Dayan, Manos Athanassoulis, and Stratos Idreos. 2017. *Monkey: Optimal Navigable Key-Value Store*. SIGMOD, 79–94. The replication uses the allocation objective in Section 4.1, the cost model in Section 4.2, and Appendices B and C. [DOI](https://doi.org/10.1145/3035918.3064054) · [Author PDF](https://cs-people.bu.edu/mathan/publications/sigmod17-dayan.pdf).
2. Zichen Zhu, Yanpeng Wei, Ju Hyoung Mun, and Manos Athanassoulis. 2025. *Mnemosyne: Dynamic Workload-Aware BF Tuning via Accurate Statistics in LSM trees*. PACMMOD 3(3), Article 190 (SIGMOD 2025). Covers dynamic filter reallocation and access statistics. [DOI](https://doi.org/10.1145/3725327) · [Author PDF](https://cs-people.bu.edu/mathan/publications/pacmmod25-zhu.pdf).
3. Niv Dayan and Stratos Idreos. 2018. *Dostoevsky: Better Space-Time Trade-Offs for LSM-Tree Based Key-Value Stores via Adaptive Removal of Superfluous Merging*. SIGMOD, 505–520. Covers the effect of merge policy on read, update, and space costs. [DOI](https://doi.org/10.1145/3183713.3196927) · [Author PDF](https://nivdayan.github.io/dostoevsky.pdf).
4. Russell Sears and Raghu Ramakrishnan. 2012. *bLSM: A General Purpose Log Structured Merge Tree*. SIGMOD, 217–228. Background on LSM design and merge scheduling. [DOI](https://doi.org/10.1145/2213836.2213862) · [Public proceedings copy](https://awoc.wolski.fi/dlib/access-methods/SR12-bLSM.pdf).
5. Manos Athanassoulis, Michael S. Kester, Lukas M. Maas, Radu Stoica, Stratos Idreos, Anastasia Ailamaki, and Mark Callaghan. 2016. *Designing Access Methods: The RUM Conjecture*. EDBT, 461–466. Frames the trade-offs among reads, updates, and memory or storage. [DOI](https://doi.org/10.5441/002/EDBT.2016.42) · [Proceedings PDF](https://www.openproceedings.org/2016/conf/edbt/paper-12.pdf).

[LevelDB](https://github.com/google/leveldb) was the basis of the paper's system experiments. [RocksDB](https://github.com/meta/rocksdb) is a related LSM-based engine. See [THIRD_PARTY.md](THIRD_PARTY.md) for the Python design reference and archived-run provenance.

## Links to deliverables

- [Source code repository](https://github.com/kelnether/monkey-bloom-filter-replication)
- [Saved evaluation results and synthetic datasets](#experiments-and-datasets)
- Video demonstration link pending.

## Chinese summary

本项目用 Python 复现 Monkey 的分层 Bloom filter 内存分配。在相同的 12,500 字节过滤器预算下，十个随机种子的基础实验中，未命中查询的平均逻辑页访问数从 0.36978 降至 0.18668，下降 49.5%。仓库包含核心算法、测试、可生成的合成数据和评估脚本。[安装和运行](#quick-start) · [代码结构](#repository-structure) · [实验与数据](#experiments-and-datasets) · [实验结果](#results)
