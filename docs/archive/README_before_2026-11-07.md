# Monkey Python MVP

用 Python 在 Mac 上完成 Monkey 核心思想的复现与评估，参考用户指定的 [predictive-lsm-trees](https://github.com/fiidalgo/predictive-lsm-trees) 项目。

**先看结果：** `results/demo/report.html`。它展示实际运行生成的图表、基础场景效果和参数搜索结果。

## 本机已验证的结果

14 项测试全部通过；完整实验产生 66 条记录、33 份共享数据集和 144 个理论搜索候选。所有查询均与真实答案一致，已插入键未出现漏判。

基础场景为 20,000 个键、4 层、层大小比例 4、平均 5 bits/key、全部为未命中查询；每种策略运行 3 个种子，每次 5,000 次查询：

| 分配策略 | 过滤器载荷预算 | 每次查询的平均逻辑页访问次数 |
|---|---:|---:|
| 统一 bits/key | 12,500 字节 | 0.37387 |
| Monkey 数值分配 | 12,500 字节 | 0.18580 |

该场景访问次数减少约 **50.3%**。这是静态实验的逻辑访问次数，不表示真实磁盘延迟或吞吐量提升 50.3%；其他参数下的效果见报告。

## 已实现

1. **真实 Bloom filter**：bytearray 位打包、稳定键编码、可重复哈希、整数哈希数、零空间过滤器。
2. **严格总预算分配**：统一 bits/key 基线与 Monkey 连续优化目标的数值解；以字节为单位严格用满相同预算。
3. **静态多层键值查询**：每层一个有序 run；真实键、合成值、内存分页、页边界索引、找到目标后结束。
4. **实验矩阵**：内存预算、层大小比例、未命中比例、层数；固定总键数；多个随机种子；共享数据与查询的配对对照。
5. **成本模型与搜索**：空结果点查 R、最深位置命中 V、摊销更新 W、范围查询 Q；对策略、T、buffer 比例枚举搜索。
6. **输出**：原始数据、逐次/逐层 CSV、均值/样本标准差、环境与源码指纹、PNG/SVG 图表及 HTML 报告。
7. **正确性测试**：预算、无漏判、页边界、空结果、提前结束、小规模穷举分配、T=2 模型一致性和重现性。

## 在当前 Mac 上运行

在 PyCharm 中打开 `/Users/kevinkel/PycharmProjects/5003test`，使用项目现有解释器 `/Users/kevinkel/PycharmProjects/5003test/.venv/bin/python`，工作目录设为项目根目录。已有 `.idea` 配置已保留。原项目目录保留为迁移备份，后续修改请在本目录进行。

本目录已经建立 `.venv` 并安装绘图依赖。运行：

```bash
cd "/Users/kevinkel/PycharmProjects/5003test"
.venv/bin/python -m unittest discover -s tests -v
MPLCONFIGDIR="$PWD/.mplconfig" .venv/bin/python -m monkey_lab run --config configs/default.json --out results/my_run
open results/my_run/report.html
```

为避免覆盖旧结果，`--out` 必须是新目录或空目录。现有 `results/demo` 是已运行结果，不需要重复计算就能打开查看。

只跑算法和 CSV、不生成图：

```bash
python3 -m monkey_lab run --config configs/default.json --out results/core_only --no-plots
```

对已有实验重新绘图：

```bash
MPLCONFIGDIR="$PWD/.mplconfig" .venv/bin/python -m monkey_lab plot --out results/demo
```

核心模块只依赖标准库；绘图依赖 Matplotlib。无需 GPU、Docker、数据库服务或机器学习库。

## 迁移到另一台电脑

保留整个项目（包括 vendor），但不复制 `.venv`，重新创建环境：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
```

建议 Python 3.10 或更新版本；当前验证环境为 Python 3.12 / macOS ARM64。`requirements-lock.txt` 记录本次安装的确切版本。

若没有 vendor 副本，获取已经核查的版本：

```bash
git clone https://github.com/fiidalgo/predictive-lsm-trees.git vendor/predictive-lsm-trees
git -C vendor/predictive-lsm-trees checkout 495e71a94559a845c76019740341745900a87666
```

本机初次安装遇到 Python CA 证书链错误，指定系统 CA 后成功安装，未关闭 TLS 校验：

```bash
.venv/bin/python -m pip install --cert /etc/ssl/cert.pem -r requirements.txt
```

## 配置与实验含义

编辑 `configs/default.json`：

| 参数 | 默认值 | 含义 |
|---|---:|---|
| entries | 20000 | 所有磁盘层的总键数 |
| levels | 4 | 静态层数，每层一个 run |
| ratio | 4 | 层大小几何比例，整数分配后严格保持总键数 |
| bits_per_key | 5 | 过滤器总预算 / 总键数；各层实际值可以不同 |
| queries | 5000 | 每个场景每个种子的查询数；另有同规模未命中探测集 |
| miss_fraction | 1.0 | 工作负载中的未命中比例 |
| entries_per_page | 128 | 静态数据页中最多存多少个键 |
| seeds | [1,2,3] | 独立重复实验 |

`sweeps` 一次只改变一个变量，其余保持基础配置；重复场景自动去重。默认共 11 个场景、3 个种子、2 种策略，即 66 条实验记录。

每个场景生成唯一键，再随机分到各层；各层键范围交错。未命中键与全部已插入键不相交。命中键从全体插入键中均匀抽取。两种策略共享同一数据、查询和哈希盐，且使用同样的过滤器载荷字节数。

位预算向下取整到完整字节。Monkey 对连续目标求解，再处理字节取整；实际 Bloom filter 使用整数哈希数，因此分别记录连续模型、整数哈希模型和实测结果。

## 输出文件

```text
results/demo/
├── report.html           # 可直接打开的结果报告
├── config.json           # 运行配置快照
├── metadata.json         # Python/系统/上游提交/本地代码指纹
├── datasets/             # 实际使用的各层键、查询和未命中探测集
├── experiments.csv       # 每个场景、种子、策略的实测指标
├── levels.csv            # 各层字节、bits/key、哈希数、误报率
├── summary.csv           # 跨种子均值和样本标准差
├── model_search.csv      # 全部理论搜索候选
├── best_configs.json     # 各工作负载、各分配策略的网格最优项
└── figures/              # benchmarks / model_check / parameter_search，PNG+SVG
```

`python_query_seconds` 只用于程序开销诊断；不是存储引擎延迟，也不是主要结论。误差线是跨种子的一个样本标准差，不是置信区间。

## 代码结构

```text
monkey_lab/
├── upstream.py      # 直接加载上游容量工具函数，生成层大小
├── bloom.py         # 改写上游 BloomFilter 接口，真实位打包
├── allocation.py    # 严格预算分配及连续误报模型
├── store.py         # 静态 Run / Level / StaticLSM 与逻辑页计数
├── model.py         # 理论成本与有限网格搜索
├── experiments.py   # 配对数据、验证、批量实验、CSV/元数据
├── plotting.py      # Matplotlib 图与 HTML 报告
└── __main__.py      # 命令行入口
```

## 准确表述项目范围

- 这是**静态多层布局下的真实过滤器实验**，不实现写入、删除、版本管理、动态 compaction、持久化或真实磁盘测量。
- 一次阳性过滤器探测访问一个内存逻辑页；没有叠加 min/max 范围预过滤，以隔离论文的误报率求和目标。
- 过滤器预算仅计算 bytearray 载荷；Python 对象、页索引、实际键集合、缓冲区都不在该数字内。
- 模型搜索支持 leveling/tiering，但静态实测仅包含每层一个 run；没有实测 tiering、更新或范围查询。
- 模型中的总内存仅指 buffer + filters，不包括 fence pointers；W/Q 采用论文公式，R 使用有限 run 的误报率求和，V 采用最深位置命中的保守成本。
- 搜索是在显式网格内找最小值，不声称是整个设计空间的全局最优配置，也不将结果宣称为实测吞吐量。
- 本项目不是 Monkey 原作者实现，不是附录 C/D 算法的逐行复现。上游项目也不是原作者实现。完整来源映射和发现的差异见 `THIRD_PARTY.md`。

## 推荐下一步

扩大数据与查询规模，增加随机种子；补充论文附录 C 分配器与当前求解器对照；如需真实系统性能，再另行加入 LevelDB/C++ 实验。
