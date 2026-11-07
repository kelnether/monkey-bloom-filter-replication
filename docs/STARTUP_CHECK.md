# 项目启动检查记录

检查日期：2026-11-07（Asia/Hong_Kong）。检查对象：`/Users/kevinkel/PycharmProjects/5003test`。

## 本次实际执行

- 阅读现有 README、来源说明、默认配置、分配器、成本模型、上游适配和实验代码，确保文档描述对应当前实现。
- 使用项目现有 `.venv/bin/python` 执行 `python -m unittest discover -s tests -v`：**14 项测试通过**。
- 比较 `results/migration_check/metadata.json` 中所有核心源码 SHA-256 与当前 `monkey_lab/*.py`：一致。
- 核对既有 `experiments.csv`：66 条记录，所有记录的正确查询数与查询数一致，漏判数为 0。
- 核对五篇文献的正式来源及 Mnemosyne 的 SIGMOD 2025 接收信息，见 [References](REFERENCES.md)。

本次任务以项目启动文档为主，没有再次运行完整实验矩阵，也没有修改算法源码。README 中的 50.3% 是既有基础场景结果，并非 2026-11-07 新跑出的结果。

## 本次文档交付

更新根目录 README，集中维护选题、研究问题、实验方案和分工计划；新增项目结构、团队指南、参考文献及本检查记录。根据小组说明，课程未明确要求独立的正式 proposal，相关内容已合并到 README，并移除独立方案文件。旧 README 原样保存在 `docs/archive/README_before_2026-11-07.md`，仅用于历史追溯，运行说明以根目录最新 README 为准。

## 正式实验前仍需小组完成

- 每名组员运行测试并能解释关键指标。
- 审核公式与代码的对应关系、确定正式配置和工作包负责人。
- 将现有探索性结果作为起点，决定是否增加种子与规模。
- 完成正式运行与组员之间的重复验证，补充层数曲线和误差讨论。
- 根据 TA 反馈调整复现范围，特别是是否需要额外系统实验。

[返回 README](../README.md)
