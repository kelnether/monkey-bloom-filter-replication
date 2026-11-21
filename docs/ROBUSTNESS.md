# 多种子、查询量和附录 C 对照

在四层、5 bits/key 的基础场景中，将随机种子从 3 个增至 10 个后，Monkey 的平均逻辑页访问数为 **0.18668**，统一分配为 **0.36978**，相对降幅 **49.5%**。10 个种子下的配对差值均为正。附录 C 在四个测试场景中得到与现有求解器相同的各层整字节预算。

[多种子和附录 C 报告](../results/robustness_seeds/report.html) · [固定数据的查询量报告](../results/robustness_queries/report.html) · [原始交付结果](RESULTS.md)

## 增加种子

每个场景使用 20,000 个键、层大小比例 T=4、5,000 次未命中查询和种子 1–10。每个种子内，三种分配策略共享各层键、查询、哈希盐和总预算。先计算同一个种子下的「统一分配 − Monkey」，再按种子汇总。表中单位为次逻辑页访问／查询，标准差描述这十个种子的波动。

| 层数 | 平均 bits/key | 统一分配 | Monkey 二分法 | 附录 C | 配对差值均值 ± 标准差 | 降幅 |
|---:|---:|---:|---:|---:|---:|---:|
| 2 | 5 | 0.18170 | 0.14586 | 0.14586 | 0.03584 ± 0.00980 | 19.7% |
| 4 | 5 | 0.36978 | 0.18668 | 0.18668 | 0.18310 ± 0.00671 | 49.5% |
| 6 | 5 | 0.55948 | 0.19254 | 0.19254 | 0.36694 ± 0.01741 | 65.6% |
| 4 | 2 | 1.57348 | 0.79816 | 0.79816 | 0.77532 ± 0.03111 | 49.3% |

在四层基础场景中，每个种子的绝对配对差值介于 **0.1712–0.1934**。在固定 5 bits/key 的三种层数下，层数越大，观察到的相对降幅越大。[层数图](../results/robustness_seeds/figures/level_count.png) · [逐种子数据](../results/robustness_seeds/experiments.csv) · [汇总](../results/robustness_seeds/summary.csv)

## 固定数据，增加查询量

每个种子先生成固定的 20,000 个数据键和一组 20,000 个不同的未命中查询。较短的一轮使用同一序列的前 5,000 个键，较长的一轮使用完整序列。两轮每层的键、过滤器字节数、哈希盐和哈希数均相同。固定数据组使用种子 1、2、3，配置为四层、T=4、平均 5 bits/key。

| 每种子查询次数 | 统一分配均值 ± 标准差 | Monkey 均值 ± 标准差 | 降幅 |
|---:|---:|---:|---:|
| 5,000 | 0.37260 ± 0.01226 | 0.18660 ± 0.00597 | 49.9% |
| 20,000 | 0.36980 ± 0.00201 | 0.18703 ± 0.00520 | 49.4% |

增加查询量后，两种策略的均值小幅变化，降幅仍接近 50%。这两个样本共享前缀。表中的标准差还包含不同数据及哈希盐的影响，用来描述这三个种子的观测波动。[查询量图](../results/robustness_queries/figures/query_count.png) · [汇总](../results/robustness_queries/summary.csv)

## 附录 C 分配器

`monkey_appendix_c` 根据 Monkey 论文附录 C 的 Algorithms 1–3 实现。它将总位数放入第一个 run，尝试在两个 run 之间双向转移整数位。总预测误报率下降且捐出端仍有余量时保留转移。一轮遍历没有改进时将步长减半，处理到 1 位为止。随后使用与 `monkey` 相同的整字节规则填满总预算。这里每层有一个 run。[论文附录 C](https://nivdayan.github.io/monkeykeyvaluestore.pdf#page=15) · [分配器代码](../monkey_lab/allocation.py)

例如在四层基础场景中，两种求法都得到 **376、1,160、3,279、7,685 字节**，连续误报模型的总目标值都约为 **0.18677**。对照还逐个核查了每层预算和逐种子的实测记录。在这四个配置中，两种求法的整字节分配、预测误报率和逻辑页访问数一致。[逐层记录](../results/robustness_seeds/levels.csv)

## 运行与验证

按 [README](../README.md#环境与首次安装) 准备 Python 环境和子模块，再在项目根目录运行。每次使用新输出目录。

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m monkey_lab run \
  --config configs/robustness_seeds.json --out results/recheck_seeds
.venv/bin/python -m monkey_lab run \
  --config configs/robustness_queries.json --out results/recheck_queries
```

- `include_appendix_c: true` 为静态查询加入第三种分配策略。报告的理论参数搜索沿用默认两种策略和独立的成本配置。
- `query_pool_size` 固定全未命中查询池，可与 `sweeps.queries` 配合使用。各查询次数须为正整数且不超过池大小。
- 本次扩展共有 **132 条策略运行记录、46 份数据快照**。750,000 次查询答案均正确，已插入键漏判数为 0。16 项测试通过。
- 默认配置另做了回归复跑。66 条记录的非计时指标、逐层统计、数据快照和模型搜索结果与原始交付版一致。两组扩展的配置和源码指纹保存在各自结果目录。

[多种子配置](../configs/robustness_seeds.json) · [查询量配置](../configs/robustness_queries.json) · [多种子元数据](../results/robustness_seeds/metadata.json) · [查询量元数据](../results/robustness_queries/metadata.json)
