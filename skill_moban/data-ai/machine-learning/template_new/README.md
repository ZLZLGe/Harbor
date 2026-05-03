# Machine Learning Template

这是面向 Machine Learning 类 skill 的模板。它综合参考 SkillsMP Machine Learning 类热门 skill 的共性能力：从真实风格时序数据构建可复现训练链路、按业务合同拆分开发集、导出可重放模型包并保持离线推理一致性。

## 第一部分：任务设计参考

* **Skill 价值定位**：Machine Learning 类热门 skill 的核心价值，不只是“把模型跑起来”，而是把训练、验证、holdout 评估、导出和复现过程工程化。高质量任务应要求 solver 在真实数据约束下交付稳定、可重放、可审计的训练结果。
* **Task 目标形态**：任务目标应是生成一条完整训练链路，而非静态答题或格式拼装。输入应包含真实风格数据快照、时序样本索引与输出合同，输出应覆盖样本级预测、整体指标、逐类表现、训练轨迹与模型包清单。
* **Verifier 设计重点**：Verifier 应优先验证行为结果：合同驱动的 split 是否真实、指标是否可复算、导出包能否复现预测、重复运行是否稳定。防作弊重点应覆盖硬编码结果、绕过真实训练、无视有效前缀约束和非确定性输出。

## 第二部分：示例任务

### 📌 任务元数据
- 任务 ID：`machine-learning__occupancy-phase-sequence-classifier`
- 类别：Machine Learning
- 难度：`hard`
- 绑定 Skill：`pytorch-patterns`
- 输入数据参考来源：
  - `environment/data/phase_sequences/development_index.csv`：任务内开发集序列索引；由 UCI Occupancy Detection 的 `datatraining.txt` 与 `datatest.txt` 生成固定窗口序列快照  
    https://cdn.uci-ics-mlr-prod.aws.uci.edu/357/occupancy%2Bdetection.zip
  - `environment/data/phase_sequences/holdout_index.csv`：任务内 holdout 序列索引；由 UCI Occupancy Detection 的 `datatest2.txt` 生成固定窗口序列快照  
    https://cdn.uci-ics-mlr-prod.aws.uci.edu/357/occupancy%2Bdetection.zip
  - `environment/data/phase_sequences/source_metadata.json`：任务内数据来源元信息；来源说明参考  
    https://archive-beta.ics.uci.edu/dataset/357/occupancy+detection

### 📊 验证与测试指标（Oracle & Verifier）
- Oracle：官方解在现有项目骨架上生成确定性训练与导出链路，满足合同驱动验证分区、CPU-only 运行、bundle 重载一致和重复运行一致等行为约束。
- Verifier 策略：

主测试
| 测试点 | 验证内容 | 对应 skill 内化点 |
| :--- | :--- | :--- |
| 输出合同完整性 | 必需输出文件、字段、JSON 键存在且可解析 | 训练链路交付规范 |
| Holdout 样本覆盖 | holdout 预测样本必须与输入 holdout 序列索引逐行一致 | 评估数据链路完整性 |
| 指标可复算 | accuracy / macro_f1 / weighted_f1 与样本预测一致 | 评估可信性 |
| 合同驱动分区 | 验证集来源必须按 split contract 动态得出 | 数据切分与工作流执行 |
| Bundle 可重放 | 导出模型包重载后预测与交付预测一致 | 导出与推理一致性 |
| 质量门槛 | holdout 上必须达到设定精度门槛 | 训练配置与模型选择收敛 |

防作弊测试
| 测试点 | 验证内容 |
| :--- | :--- |
| 动态 split 合同变更 | 修改验证源分区合同后重跑，split 元数据必须跟着变化 |
| 尾部噪声防护 | 对序列末尾追加无效 tail 后，若 `sequence_length` 不变则预测必须稳定 |
| 重复运行一致性 | 同输入与同合同重复运行产物保持一致 |

### ⚡ Skill 相关性评估

结论：强相关。该任务核心是生成可复现、可导出、可重放的 PyTorch 训练链路，并且要真实执行合同驱动的开发集拆分、变长序列 batching 和 CPU-safe bundle reload，这直接对应 `pytorch-patterns` 的使用场景：编写训练脚本、控制可复现性、保证设备无关行为、组织模型与数据加载流程。相对无 skill 情况，with skill 更容易一次性同时满足 determinism、contract-driven split、variable-length batching 和 bundle-reload 一致性。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）。其中最早一轮发生在最终 verifier 双门槛口径确定前，已按当前最终口径统一回算；其余两轮直接跑在当前最终 verifier 上：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | 近 3 次有效对照里，without skill 均至少遗留 1 项 verifier 失败；失败以动作级问题为主，集中在未稳定满足最终质量门槛或未完全满足 bundle reload 合同。 |
| Agent 执行耗时 | `854.9s` | `869.7s` | 本任务里 with skill 的主要收益体现在通过率与完整交付稳定性，而不是平均耗时下降。 |
| Tokens | `4.59M` | `3.04M` | Without skill 的上下文与试错开销约为 With skill 的 `1.51x`。 |

## 📁 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── generate_seed_data.py
│   ├── data/
│   ├── project/
│   └── skills/
├── tests/
│   ├── test.sh
│   └── test_outputs.py
└── solution/
    ├── fixed_run_pipeline.py
    └── solve.sh
```
