# 项目文件结构与数据流

本文描述已有原型及本次新增文档，不把尚未实现的模块画成已完成系统。主工作目录为 `/Users/kevinkel/PycharmProjects/5003test`。

## 1. 完整布局

```text
5003test/
├── README.md                     # 选题、研究计划和运行说明
├── docs/
│   ├── PROJECT_STRUCTURE.md       # 本文件：模块与数据流
│   ├── TEAM_GUIDE.md              # 学习、分工和里程碑
│   ├── REFERENCES.md              # 五篇论文、来源和报告用途
│   ├── STARTUP_CHECK.md           # 本次检查与历史结果的区分
│   └── archive/
│       └── README_before_2026-11-07.md
├── configs/
│   └── default.json
├── monkey_lab/
│   ├── __init__.py
│   ├── __main__.py                # run / plot 命令入口
│   ├── upstream.py                # 固定上游工具与层大小生成
│   ├── bloom.py                   # 位数组、哈希、过滤器操作
│   ├── allocation.py              # uniform / monkey 分配
│   ├── store.py                   # Run / Level / StaticLSM
│   ├── model.py                   # 理论成本与网格搜索
│   ├── experiments.py             # 数据生成、配对实验、CSV
│   └── plotting.py                # 图表与 HTML 报告
├── tests/
│   └── test_core.py
├── results/
│   ├── demo/                     # 初始实验
│   ├── migration_check/          # 已有迁移验证实验
│   └── final/                    # 交付复跑与层数图
├── vendor/
│   └── predictive-lsm-trees/     # 保留上游目录与 Git 版本信息
├── THIRD_PARTY.md
├── upstream_manifest.json
├── requirements.txt
├── requirements-lock.txt
├── .gitignore
├── .idea/                        # 本机 PyCharm 配置
└── .venv/                        # 本机环境，不在组员间复制
```

`.cache/`、`.mplconfig/`、`__pycache__/` 为运行缓存，不是研究交付物。正式运行生成额外的 `results/<run_name>/`，无需为了规划目录改动现有可运行模块。

## 2. 两条执行路径

```text
静态实测：
configs/default.json
  → experiments.build_cases：生成并去重场景
  → upstream.geometric_sizes：确定每层键数量
  → experiments.workload：生成层数据、查询、真实答案
  → allocation.allocate：同一总预算的两种分配
  → bloom.BloomFilter + store.StaticLSM：建过滤器、执行查询
  → 正确性校验、逐层 FPR、逻辑访问计数
  → experiments.csv / levels.csv / summary.csv

理论搜索：
config.model_search
  → model.search_parameters
  → model.cost_model + allocation.allocate
  → model_search.csv / best_configs.json

共同展示：两条路径的输出 → plotting.make_report → figures/ + report.html
```

第一条执行真实过滤器操作；第二条计算预测成本。虽然都用到分配器，但数据规模、内存口径与结果含义不同。

## 3. 模块接口与审阅重点

| 文件 | 主要入口 | 应检查什么 |
|---|---|---|
| `upstream.py` | `geometric_sizes(total, levels, ratio)` | 层大小为正整数、总量不变；直接复用上游 `calculate_level_capacity` |
| `allocation.py` | `allocate(sizes, budget_bytes, strategy)` | 返回各层／run 的字节数；总和严格等于预算；均匀基线是统一 bits/key |
| `bloom.py` | `BloomFilter` | 位打包、确定性编码、整数 k、无漏判、零预算始终阳性 |
| `store.py` | `StaticLSM.get(key)` | 返回值和 QueryStats；过滤器阳性后计逻辑页访问；命中即停 |
| `model.py` | `cost_model`、`search_parameters` | R/V/W/Q 含义、工作负载权重、有限网格、预测标签 |
| `experiments.py` | `run_case`、`run_all` | 两种策略共用输入、真正的未命中键、保存配置和指纹 |
| `plotting.py` | `make_report(output)` | 轴单位、样本标准差、实测／预测区分 |
| `tests/test_core.py` | unittest discovery | 正确性与边界情况，避免只检查“程序能运行” |

`StaticLSM` 的预算是过滤器载荷预算；不能把它解释成 Python 进程的内存限制。当前没有为每个 run 额外使用 min/max 范围预过滤，以隔离过滤器误报率求和这一目标。

## 4. 一次运行的结果目录

```text
results/<run_name>/
├── config.json                  # 配置快照
├── metadata.json                # 系统／Python／上游提交／源码 SHA-256
├── datasets/*.json              # levels、queries、absent_probes
├── experiments.csv              # 每场景、种子、策略一行
├── levels.csv                   # 每层过滤器统计
├── summary.csv                  # 跨种子汇总
├── model_search.csv             # 理论候选全集
├── best_configs.json            # 网格内最优项
├── figures/
│   ├── benchmarks.png / .svg
│   ├── level_count.png / .svg    # 当配置比较多个层数时生成
│   ├── model_check.png / .svg
│   └── parameter_search.png / .svg
└── report.html
```

CSV 中 `measured_blocks`、`measured_false_positives` 等字段表示每次查询的平均数，而不是总数；看字段时先核对 `experiments.py` 中的聚合方式。`measured_absent_blocks` 来自逐层完整未命中探测，不等同于混合负载的平均访问数。

## 5. 可追加但尚未实现的工作

已完成的层数图及分析见[结果与交付核对](RESULTS.md)。后续可补充公式与代码的对照记录，并按课程范围考虑附录 C 分配器或偏斜查询生成器。

[返回 README](../README.md) · [查看研究计划](../README.md#研究问题与可检验预期)
