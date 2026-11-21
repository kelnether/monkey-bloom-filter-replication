# Monkey: Optimizing Bloom Filter Memory Allocation

**DSC5003 · Track 2 · Python 核心算法复现: DENG Tianyu; XIA Tianquan; ZHANG Yue; LI Wenhao; ZHAO Yining**

在相同 Bloom filter 内存预算下，比较统一 bits/key 和 Monkey 分层分配，观察误报率、逻辑页访问次数及成本模型预测的变化。主复现论文为 [Monkey: Optimal Navigable Key-Value Store（SIGMOD 2017）](https://doi.org/10.1145/3035918.3064054)。

本项目已有探索性原型。小组接下来的工作是理解、审阅、完善并形成可重复的实验结论。所有静态查询在内存中完成，逻辑访问数不代表真实 SSD 延迟。

## 小组从这里开始

| 需要做什么 | 阅读入口 |
|---|---|
| 了解选题、研究问题和实验计划 | 本文的[项目简介](#项目简介)、[研究问题](#研究问题与可检验预期)和[实验方案](#实验方案) |
| 找到模块、接口和数据流 | [项目文件结构](docs/PROJECT_STRUCTURE.md) |
| 上传 GitHub、获取项目与日常协作 | [GitHub 操作指南](docs/GITHUB_GUIDE.md) |
| 分工、补基础、准备组会 | [小组学习与协作指南](docs/TEAM_GUIDE.md) |
| 阅读五篇论文和类似系统 | [参考文献与用途](docs/REFERENCES.md) |
| 区分论文、第三方代码和本地改写 | [来源与修改说明](THIRD_PARTY.md) |
| 查阅此次整理前的说明 | [原 README 存档](docs/archive/README_before_2026-11-07.md) |

建议首次组会：先读本文的项目简介、研究问题和方法说明，运行测试，打开已有报告，然后每人跟踪一次未命中查询经过的代码。项目规划统一维护在本 README，供小组沟通和实施使用。

## 项目简介

**Track:** Track 2 — Research Paper Replication

**Title:** Monkey: Optimizing Bloom Filter Memory Allocation

**Brief description of content to be covered:**

We will replicate the core Bloom filter memory allocation ideas of *Monkey: Optimal Navigable Key-Value Store* (SIGMOD 2017). Our project asks whether allocating a fixed filter memory budget non-uniformly across LSM-tree levels reduces false positives and unnecessary data accesses compared with uniform bits-per-key allocation. Using Python, we will implement packed Bloom filters, memory allocation algorithms, and static multi-level sorted datasets. We will conduct controlled experiments varying filter memory, level-size ratio, number of levels, and the fraction of unsuccessful lookups. Evaluation will cover per-level false-positive rates, average logical block accesses, correctness, and agreement between analytical predictions and measurements. We will also explore a finite parameter grid using an analytical cost model. Deliverables include source code, test scripts, synthetic datasets, evaluation code, and a reproducible report. The initial scope focuses on core algorithms and static experiments; dynamic compaction and physical disk performance are outside this scope.

**References:** Monkey [1] is the replication target. Mnemosyne [2] and Dostoevsky [3] provide follow-up research; bLSM [4] and the RUM Conjecture [5] provide background. Full bibliographic entries and verified links are in [References](docs/REFERENCES.md).

**Similar applications / implementations:** [LevelDB](https://github.com/google/leveldb) and [RocksDB](https://github.com/meta/rocksdb) are relevant key-value storage systems. The third-party [predictive-lsm-trees](https://github.com/fiidalgo/predictive-lsm-trees) repository supplies implementation references; it is not Monkey's official artifact. Reuse is documented in [THIRD_PARTY.md](THIRD_PARTY.md).

## 选题与切入角度

中文题目：**Monkey：面向 LSM-tree 的 Bloom Filter 内存分配优化与实验复现**。

主问题是：总过滤器空间相同，是否应该为每层每个键分配相同的位数？我们比较统一 bits/key 与依据各层键数量优化的分配策略，解释差异来自哪里，而不仅仅展示一条性能曲线。

将最小实验限定为静态数据、每层一个有序 run、点查询。查询先检查过滤器；阳性时访问对应逻辑页，找到键即停止。所有键与页面驻留内存，因此“访问次数”是受控的逻辑指标。这个范围适合 Python，也便于组员从 Bloom filter、概率和多层查询逐步理解论文。

## 研究问题与可检验预期

| 编号 | 研究问题 | 方法与判断依据 |
|---|---|---|
| RQ1 | 固定空间下，非均匀分配是否减少未命中查询访问？ | 同一数据、查询与哈希盐配对比较两种策略 |
| RQ2 | 收益如何随内存、层数、层大小比例变化？ | 一次改变一个变量，报告多种子的均值和标准差 |
| RQ3 | 连续误报模型能否解释真实位数组过滤器的行为？ | 分别比较连续近似、整数哈希数近似与实测；分析取整和抽样误差 |
| RQ4 | 成功查询比例变化时，优化收益是否保持？ | 测试全部未命中、混合、全部命中，考虑提前结束的影响 |
| RQ5 | 成本模型会为不同读写比例选择什么参数？ | 在显式网格内比较层大小比例、buffer 比例、leveling/tiering |

预期 Monkey 在其优化目标下通常减少无效访问，但不预设固定提升百分比。零内存场景应退化到所有过滤器均为阳性；高命中率、较小预算及离散取整可能改变收益。观察到差异或优势不显著也应完整报告。

## 方法与复现对应关系

设第 i 层有 n_i 个键，过滤器使用 m_i 位、k_i 个哈希位置。单层近似误报率为：

```text
p_i ≈ (1 - exp(-k_i * n_i / m_i)) ^ k_i
采用连续最优哈希数近似时：p_i ≈ exp(-(ln 2)^2 * m_i / n_i)
未命中查询期望逻辑访问数：R ≈ Σ p_i
目标：min Σ p_i，约束 Σ m_i = M，m_i ≥ 0
```

上述公式需 m_i > 0；m_i = 0 时单独定义 p_i = 1。内存约束在实现中按完整字节执行。基线的空间与 n_i 成比例，含义是每键相同位数，不是每层相同字节。

| 论文思想 | 本项目实现／计划 | 复现边界 |
|---|---|---|
| 第 4.1 节及附录 B：跨层误报率优化 | 现有 KKT 连续解数值求解，再按字节分配余量 | 复现优化目标；并非附录 C 的逐行实现，不声称离散全局最优 |
| 多层查询与过滤器 | 真实位打包过滤器、静态有序页、逻辑访问计数 | 实测布局为每层一个 run；不实现后台合并 |
| 第 4.2 节成本分析 | 有限层误报率求和、最深位置命中成本、更新和范围成本近似 | 更新／范围是模型预测；默认搜索的范围查询权重为 0 |
| 参数调优 | 枚举有限网格并保存所有候选 | 并非附录 D 搜索算法，不声称全设计空间最优 |
| 实验验证 | 均匀基线、多个种子、真实答案校验、图表 | 不复现原论文 LevelDB 端到端延迟数字 |

理论依据见 [Monkey 原文](https://cs-people.bu.edu/mathan/publications/sigmod17-dayan.pdf)。上表中的实现选择是本项目设计，不是论文原作者的实现声明。

## 当前实现及边界

| 功能 | 当前实现 |
|---|---|
| Bloom filter | bytearray 位打包、确定性哈希、整数哈希数、零空间处理 |
| 分配算法 | `uniform`：统一 bits/key；`monkey`：连续优化数值解＋字节取整 |
| 静态查询 | 每层一个有序 run，页边界索引，命中后提前结束 |
| 实验 | 改变预算、T、层数、未命中比例；配对种子和数据 |
| 成本与搜索 | 理论 leveling/tiering 成本，有限网格枚举 |
| 结果 | JSON 数据、CSV、PNG/SVG、HTML、源码指纹 |

没有实现动态 compaction、写入／删除、事务或真实磁盘读写；不声称完整复制原作者系统。`monkey` 是当前策略名，表示遵循论文优化目标的实现，未逐行复现附录 C/D。

## 环境与首次安装

推荐 Python 3.12，以贴近原型验证环境；核心模块使用标准库，绘图需要 Matplotlib。Mac 无需 GPU、Docker 或独立数据库服务。

组员从 GitHub 获取项目时，需同时获取固定版本的上游子模块。将下面的 `YOUR_REPOSITORY_URL` 替换为本项目仓库地址：

```bash
git clone --recurse-submodules YOUR_REPOSITORY_URL
```

若已使用普通 `git clone`，进入项目根目录后执行 `git submodule update --init --recursive`。不要运行 `--remote`，以免将参考代码更新到不同于本项目记录的版本。GitHub 的 Download ZIP 不包含子模块源码；推荐使用 Git 克隆。

组员获取整个项目文件夹（包括 `vendor/`）后，在项目根目录执行：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m unittest discover -s tests -v
```

`requirements-lock.txt` 固定既有环境版本；若因 Python／平台不匹配安装失败，先核对版本，可使用 `requirements.txt` 安装兼容版本并记录实际依赖。不要复制其他电脑的 `.venv`。

当前主项目位置为 `/Users/kevinkel/PycharmProjects/5003test`。这里已存在 `.venv`，无需重复创建；在 PyCharm 打开该目录，解释器选择 `.venv/bin/python`，Working directory 设为项目根目录。

若 vendor 缺失，先恢复固定版本：

```bash
git clone https://github.com/fiidalgo/predictive-lsm-trees.git vendor/predictive-lsm-trees
git -C vendor/predictive-lsm-trees checkout 495e71a94559a845c76019740341745900a87666
```

它不是 Monkey 官方代码。本项目直接加载其中的容量函数，因此 vendor 不是可随意删除的资料目录。

## 运行与查看结果

在项目根目录运行完整默认实验；输出使用带时间戳的新目录：

```bash
run_dir="results/team_$(date +%Y%m%d_%H%M%S)"
MPLCONFIGDIR="$PWD/.mplconfig" XDG_CACHE_HOME="$PWD/.cache" \
  .venv/bin/python -m monkey_lab run --config configs/default.json --out "$run_dir"
open "$run_dir/report.html"
```

`open` 是 macOS 命令；其他平台可直接用浏览器打开报告。相同 `--out` 非空时会拒绝覆盖，重复实验请换目录。

只运行算法和 CSV（无需安装绘图依赖）：

```bash
python3 -m monkey_lab run --config configs/default.json --out results/core_only --no-plots
```

已有结果重新绘图，不重新计算实验：

```bash
MPLCONFIGDIR="$PWD/.mplconfig" XDG_CACHE_HOME="$PWD/.cache" \
  .venv/bin/python -m monkey_lab plot --out results/demo
```

已有报告：[初始实验](results/demo/report.html) · [迁移验证实验](results/migration_check/report.html)。

如遇本机 Python 证书链错误，可尝试使用系统证书，不要关闭 TLS 校验：

```bash
.venv/bin/python -m pip install --cert /etc/ssl/cert.pem -r requirements-lock.txt
```

## 配置：先只改一个变量

入口：[configs/default.json](configs/default.json)。

| 参数 | 默认值 | 含义 |
|---|---:|---|
| `entries` | 20000 | 静态各层总键数 |
| `levels` | 4 | 层数，每层一个 run |
| `ratio` | 4 | 层大小几何比例 T |
| `bits_per_key` | 5 | 总过滤器位预算／总键数 |
| `queries` | 5000 | 每场景、每种子的查询数 |
| `miss_fraction` | 1.0 | 查询键不存在的比例 |
| `entries_per_page` | 128 | 每个内存逻辑页最多存放的键数 |
| `seeds` | [1,2,3] | 三次重复实验 |

`sweeps` 一次改变一个变量并去重：默认 11 场景 × 3 种子 × 2 策略 = 66 条实测记录。`model_search` 是独立的理论实验，具有自己的数据规模、总内存和参数网格；默认 144 个候选。正式实验前复制配置为新文件，不覆盖原始配置和旧结果。

## 实验方案

以下实验以上述默认配置为起点。键范围在各层交错，所有插入键唯一；未命中键与插入集合不相交。

| 实验 | 改变的变量 | 当前默认取值 | 主要输出 |
|---|---|---|---|
| E1 | 平均过滤器 bits/key | 0、2、5、8、10 | 总访问数、逐层 FPR、模型误差 |
| E2 | 层大小比例 T | 2、4、10 | 非均匀分配的收益变化 |
| E3 | 未命中比例 | 0、0.5、1 | 混合工作负载访问数 |
| E4 | 层数 L | 2、4、6 | 固定总键数下的层数影响 |
| E5 | 理论配置网格 | T=2/4/8/10；buffer 比例 0.05/0.2/0.5；两种合并策略 | 每种读写比例下的网格最优候选 |

E1–E4 去重后为 11 个场景 × 3 个种子 × 2 种分配策略，共 66 条记录。E5 使用独立的模型数据规模与内存预算，默认共 144 个候选，不能与 E1–E4 的实测值混作同一场景。E4 结果目前保存在 CSV 中，专门的层数曲线拟补充。

公平性要求：配对策略共享输入和查询、过滤器载荷总字节数相同、记录随机种子与源码指纹。逐层 FPR 使用完整未命中探测集计算；它在混合负载下不受提前停止影响，但不应宣称与未命中工作负载样本完全独立。

验收应关注：全部查询答案正确、已插入键不漏判、预算准确、零预算行为正确、小实例分配检查、预测与实测差异可解释、组员能在另一环境重跑。均值以外报告样本标准差；它不是置信区间。正式实验可增加种子和查询量，先观察运行成本再决定规模。

## 怎样解释结果

- `levels.csv`：每层键数、载荷字节、哈希数、实测与预测误报率。
- `experiments.csv`：每次配对实验的平均逻辑页访问数、误报数、过滤器探测数与正确性。
- `summary.csv`：跨种子的均值和样本标准差；标准差不等于置信区间。
- `model_search.csv`、`best_configs.json`：全部理论候选和网格内最优参数。
- `metadata.json`：运行环境、上游提交及本地源码指纹。
- `datasets/`：真实使用的层数据、查询及未命中探测集。
- `figures/`：预算／T／未命中比例、预测与实测、参数搜索三组图；层数结果目前在 CSV 中。

主要指标是每次查询的逻辑页访问数。未命中查询中，每次过滤器误报触发一次逻辑页访问；成功查询还包括找到结果的那次访问，并可能提前结束。`python_query_seconds` 仅作 Python 实现开销诊断。

内存口径：静态过滤器预算只计算 bytearray 的位数组载荷，不含 Python 对象、数据和页索引；理论调参的总内存包含 buffer 与 filters，但仍不包含页索引。两种口径须在图注中区分。

## 历史可行性结果

现有迁移验证数据中，20,000 键／4 层／T=4／5 bits/key／全部未命中的基础场景，两种策略均使用 12,500 字节过滤器载荷，三个种子的平均逻辑访问数分别为 0.37387（uniform）和 0.18580（monkey）。该场景约减少 50.3%，不等于物理磁盘性能提升，也不是正式实验必须达到的目标。

原始依据：[summary.csv](results/migration_check/summary.csv)。2026-11-07 文档整理时重新检查源码指纹及记录正确性，并重新运行测试；没有重新运行完整实验矩阵。当前验证详情见 [启动检查](docs/STARTUP_CHECK.md)。

## 项目布局

```text
5003test/
├── README.md                 # 选题、研究计划、组员入口和运行方法
├── docs/                     # 文件结构、文献、协作与历史说明
├── configs/default.json      # 默认实验与成本搜索参数
├── monkey_lab/               # Python 核心实现
├── tests/test_core.py        # unittest 测试
├── results/                  # 运行产物，每次独立子目录
├── vendor/predictive-lsm-trees/ # 固定版本的参考代码
├── THIRD_PARTY.md            # 复用和改写的对应关系
├── upstream_manifest.json    # 上游文件指纹
├── requirements.txt          # 绘图依赖范围
└── requirements-lock.txt     # 已记录的确切版本
```

## 交付物与当前状态

仓库已有探索性原型，供组员学习、审阅与继续改进；项目启动不等于代码从零开始，也不等于正式研究已经完成。

| 交付物 | 当前基础 | 下一步 |
|---|---|---|
| 核心源码 | Bloom filter、分配器、静态布局、成本模型均存在 | 逐模块核对论文依据，解释边界条件 |
| 测试脚本 | 现有 unittest 测试 | 小组运行并审阅，新增功能再加必要测试 |
| 数据与生成器 | 可重复合成数据及 JSON 快照 | 冻结正式配置，不要求额外采集真实数据 |
| 评估代码 | CSV、模型搜索、PNG/SVG 和 HTML | 增加 E4 图；补充误差讨论 |
| 报告与演示 | README 项目计划、阅读与协作指南 | 撰写结果、局限和贡献归属，制作演示 |

既有输出是可行性证据，不将其提升幅度作为验收门槛。核心限制：无动态写入／删除／compaction、事务、持久化或物理磁盘测量；过滤器预算不含 Python 对象及数据集开销，成本模型中的 buffer+filters 预算也不含页索引。

## 建议分工与阶段

按四个工作包分工，人数不足时合并；每个工作包另设一名交叉审阅者，不预填组员身份。

| 工作包 | 负责内容 | 可检查产物 |
|---|---|---|
| A：理论与分配 | 论文推导、基线定义、分配器 | 公式到代码的对照说明 |
| B：过滤器与数据 | 位数组、哈希、页面、查询路径 | 正确性与内存口径说明 |
| C：实验与图表 | 配置、批量运行、统计、模型比较 | 可重复结果与图注 |
| D：整合与写作 | 相关文献、报告、演示、复现说明 | 可交付材料与来源记录 |

建议四个阶段，按课程期限压缩或延长：第一阶段统一概念并运行原型；第二阶段审核算法与模型；第三阶段冻结配置并运行正式实验；第四阶段完成报告及互相演示。详见 [小组学习与协作指南](docs/TEAM_GUIDE.md)。

## 可选扩展与主要风险

可选扩展：补充附录 C 分配器用于对照；研究非几何层大小；增加偏斜查询以讨论工作负载感知。Mnemosyne 的动态统计维护与在线调优仅作为后续方向，不承诺复现整套机制。[Mnemosyne 原文](https://cs-people.bu.edu/mathan/publications/pacmmod25-zhu.pdf)

主要风险及处理：数据库基础不足时先手工跟踪一次查询；模型偏差时检查整数 k、字节取整和样本数；Python 运行时间受实现影响时以逻辑访问为主要指标；范围过大时优先完成 E1–E4 和一个可解释的模型搜索。论文阅读、第三方代码和现有辅助原型的贡献应据实区分。
