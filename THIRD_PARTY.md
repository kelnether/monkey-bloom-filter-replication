# 来源、复用与改动

## 原论文

Niv Dayan, Manos Athanassoulis, Stratos Idreos. **Monkey: Optimal Navigable Key-Value Store**. SIGMOD 2017. DOI: [10.1145/3035918.3064054](https://doi.org/10.1145/3035918.3064054).

核心依据包括第 4.1 节过滤器分配目标、第 4.2 节成本模型、附录 B 的分配推导，以及附录 C 的 Algorithms 1–3。默认 `monkey` 使用 KKT 连续解的二分法。扩展策略 `monkey_appendix_c` 根据论文重新实现迭代转移，采用整数位步长并共用整字节舍入。参数搜索使用有限网格。[论文附录 C](https://nivdayan.github.io/monkeykeyvaluestore.pdf#page=15) · [扩展实验](docs/ROBUSTNESS.md)

## 用户指定参考项目

- 仓库：https://github.com/fiidalgo/predictive-lsm-trees
- 本地位置：`vendor/predictive-lsm-trees`
- 检查的提交：`495e71a94559a845c76019740341745900a87666`
- 初始仓库状态干净；MVP 未修改 vendor 源文件。
- `upstream_manifest.json` 保存上游核心文件的 SHA-256。

| 上游文件 | MVP 如何使用 |
|---|---|
| `lsm/utils.py` | 在 `monkey_lab/upstream.py` 中直接加载并复用 `calculate_level_capacity`；用于生成几何层权重 |
| `lsm/bloom.py` | 参考 BloomFilter 类及 add / might_contain / get_size_bytes 接口；重写存储、哈希和预算入口 |
| `lsm/traditional.py` | 参考 Level 中按 run 新旧顺序查询、找到后停止的组织方式；提取为静态 Level |
| `lsm/run.py` | 参考 Run 和 page_min_keys 页边界索引设计；改成明确计数的内存有序页 |

这是**参考及改造上游结构，并直接复用其工具函数**的最小实现。没有运行其完整 TraditionalLSMTree，也没有复用其机器学习模块或声称复现其性能结果。

## 读取源码后的重要差异

1. 上游 `bloom.py` 使用 `[False] * self.size`，但 `get_size_bytes()` 返回 `ceil(size / 8)`。后者描述理想位数组载荷，不是 Python 布尔列表的实际空间。本项目用 `bytearray` 按位存储，并仅报告实际载荷字节数，不冒充总进程内存。
2. 上游 `Constants.get_level_fpr` 按固定的 10 倍倍率增加目标 FPR、上限 0.5，没有接受全局过滤器预算。本项目按各 run 的实际键数和严格总字节预算求解，并允许零空间过滤器。
3. 上游 Run 的部分读取路径会反序列化整个 run。本项目使用内存静态页，所有计数明确标记为 logical block accesses，不把文件调用次数或整段加载当作物理页 I/O。
4. 上游有机器学习分类器、学习型过滤器、动态合并、持久化等内容。MVP 没有纳入它们，避免超出用户要求的三项基础复现范围。

上游 README 标注了 MIT License 链接，但本地提交没有独立 LICENSE 文件；本项目保留上游文件及原始来源，不额外替上游声明许可证。
