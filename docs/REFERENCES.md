# 参考文献与阅读用途

核对日期：2026-11-07。只有 [1] 是本项目的主复现对象；[2]–[5] 用于理解后续工作、研究背景和局限，不代表承诺复现五套系统。下面使用本项目编号，而非 Monkey 原文编号。

## [1] Monkey — 主复现论文

Niv Dayan, Manos Athanassoulis, and Stratos Idreos. 2017. **Monkey: Optimal Navigable Key-Value Store.** Proceedings of the ACM SIGMOD International Conference on Management of Data, 79–94.

[DOI: 10.1145/3035918.3064054](https://doi.org/10.1145/3035918.3064054) · [作者公开 PDF](https://cs-people.bu.edu/mathan/publications/sigmod17-dayan.pdf) · [作者介绍](https://stratos.seas.harvard.edu/publications/monkey-optimal-navigable-key-value-store)

报告用途：问题定义、分层过滤器分配、成本模型及实验对照。建议先读摘要与引言，再读第 4.1 节和附录 B，最后看成本分析、实验及附录 C/D。分配推导与参数搜索的具体复现边界见 [README 的方法与复现对应关系](../README.md#方法与复现对应关系)。

## [2] Mnemosyne — 动态工作负载相关研究

Zichen Zhu, Yanpeng Wei, Ju Hyoung Mun, and Manos Athanassoulis. 2025. **Mnemosyne: Dynamic Workload-Aware BF Tuning via Accurate Statistics in LSM trees.** Proceedings of the ACM on Management of Data, 3(3), Article 190, 28 pages（SIGMOD 2025）.

[DOI: 10.1145/3725327](https://doi.org/10.1145/3725327) · [作者公开 PDF](https://cs-people.bu.edu/mathan/publications/pacmmod25-zhu.pdf) · [SIGMOD 2025 接收列表](https://2025.sigmod.org/sigmod_papers.shtml)

报告用途：解释实际 LSM 形状变化和访问分布为何使静态配置存在局限。该研究提出动态 BF 重分配及访问统计机制，适合未来工作讨论。已将原草稿标题末尾误写的 `treeso` 更正为 `trees`。其正式出版记录是 PACMMOD 论文，不应写成普通预印本。

建议阅读：摘要、引言及图 1，先理解动态统计问题；不要求所有组员立即实现 Merlin 或 Mnemosyne+。

## [3] Dostoevsky — 合并策略与设计空间

Niv Dayan and Stratos Idreos. 2018. **Dostoevsky: Better Space-Time Trade-Offs for LSM-Tree Based Key-Value Stores via Adaptive Removal of Superfluous Merging.** Proceedings of the ACM SIGMOD International Conference on Management of Data, 505–520.

[DOI: 10.1145/3183713.3196927](https://doi.org/10.1145/3183713.3196927) · [作者公开 PDF](https://nivdayan.github.io/dostoevsky.pdf)

报告用途：介绍过滤器优化之外的合并策略优化及读写空间权衡。建议读引言、Lazy Leveling 的动机和设计空间图；当前原型没有复现该系统的动态合并机制。

## [4] bLSM — LSM 系统基础

Russell Sears and Raghu Ramakrishnan. 2012. **bLSM: A General Purpose Log Structured Merge Tree.** Proceedings of the ACM SIGMOD International Conference on Management of Data, 217–228.

[DOI: 10.1145/2213836.2213862](https://doi.org/10.1145/2213836.2213862) · [SIGMOD 可复现性站点书目信息](https://reproducibility.cs.arizona.edu/v2/data/sigmod12_SearsR12_bib.html)

报告用途：介绍 LSM 系统、读写开销及合并调度背景。它是 Monkey 原文参考文献 [29]；适合帮助组员理解“静态多层查询”只是完整系统的一部分。[Monkey 参考文献](https://cs-people.bu.edu/mathan/publications/sigmod17-dayan.pdf#page=13)

## [5] RUM Conjecture — 研究动机

Manos Athanassoulis, Michael S. Kester, Lukas M. Maas, Radu Stoica, Stratos Idreos, Anastasia Ailamaki, and Mark Callaghan. 2016. **Designing Access Methods: The RUM Conjecture.** Proceedings of the International Conference on Extending Database Technology (EDBT), 461–466.

[DOI: 10.5441/002/EDBT.2016.42](https://doi.org/10.5441/002/EDBT.2016.42) · [官方 PDF](https://www.openproceedings.org/2016/conf/edbt/paper-12.pdf) · [官方会议目录](https://www.openproceedings.org/html/pages/2016_edbt.html)

报告用途：解释读取、更新与内存／存储开销的权衡。它是 EDBT Visionary Paper，也是 Monkey 原文参考文献 [8]；应称为猜想及分析视角，不应写成已经普遍证明的定理。它作为背景材料，不替代可实现、可评估的 Monkey 主论文。

## 类似应用与实现参考

| 项目 | 与本课题的联系 | 本项目如何使用 |
|---|---|---|
| [LevelDB](https://github.com/google/leveldb) | 有序键值存储库；Monkey 原论文在其基础上做系统验证 | 理解实际应用背景，不作为当前运行依赖 |
| [RocksDB](https://github.com/meta/rocksdb) | 持久化键值存储引擎，相关研究的系统平台 | 讨论后续系统验证；目前不安装或修改 |
| [predictive-lsm-trees](https://github.com/fiidalgo/predictive-lsm-trees) | Python LSM 与 learned Bloom filter 实验项目 | 固定版本工具函数复用与结构参考；不复现 ML 部分 |

开源仓库链接不替代正式论文引用。具体复用文件、版本和改写见 [THIRD_PARTY.md](../THIRD_PARTY.md)。这五篇论文的关系是主论文、背景及后续工作；尤其 2025 年的 Mnemosyne 不可能是 2017 年 Monkey 所引用的前置论文。

[返回 README](../README.md)
