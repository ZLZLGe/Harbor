# Scripting Template

这是面向 `scripting` 类 skill 的模板。它综合参考 SkillsMP scripting 类热门 skill 的共性能力：脚本环境确认、可靠的 shell 编排、真实输入处理、失败路径治理、可重复执行和任务级交付校验。

## 第一部分：任务设计参考

* **Skill 价值定位**：scripting 类热门 skill 的核心价值，不只是“写出一段脚本”，而是把真实任务链路变成可运行、可复查、可重跑的自动化交付。对于 `bash-defensive-patterns` 这类 skill，关键点是严格模式、输入校验、安全文件处理、日志与清理，而不是仅靠一次性命令凑出结果。
* **Task 目标形态**：任务应尽量贴近真实脚本维护场景，例如多步 shell pipeline、真实数据切片、阶段性中间产物、失败重跑、日志留痕和跨文件聚合。题面只保留症状、交付合同和禁止事项，把具体诊断与修复工作流留给 solver 和 skill 自己识别。
* **Verifier 设计重点**：Verifier 应覆盖真实输出重算、重复执行稳定性、失败路径清理、并发重入控制、中断恢复、路径安全、输入不可篡改和反硬编码。重点不是卡格式细节，而是确认 solver 真的修好了现有脚本链路，而不是绕开链路、手写结果或只对当前快照打补丁。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`scripting__airport-report-pipeline`
- 类别：`scripting`
- 难度：`hard`
- 绑定 Skill：`bash-defensive-patterns`
- 输入数据参考来源：
  - `environment/data/ourairports/countries.tsv`：任务内国家维表；数据直接来源于  
    `https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/countries.csv`
  - `environment/data/ourairports/regions.tsv`：任务内地区维表；数据直接来源于  
    `https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/regions.csv`
  - `environment/data/ourairports/airports.tsv`：任务内机场事实表；数据直接来源于  
    `https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/airports.csv`
  - `environment/data/ourairports/runways.tsv`：任务内跑道事实表；数据直接来源于  
    `https://raw.githubusercontent.com/davidmegginson/ourairports-data/main/runways.csv`

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：Oracle 修复现有 shell 入口和阶段脚本，保持真实链路不变，在基线数据与 alternate fixture 上都能稳定重建 CSV、JSON 和本次运行日志，并在失败路径、临时目录处理和重复触发场景下正确返回可预期结果，不留下最终交付物伪完成态。
- Verifier策略：

主测试
| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 基线输出契约 | 重算国家汇总 CSV 和地区 JSON，校验字段、排序和业务口径 | 修复真实脚本链路，而不是手工写结果 |
| 重复执行稳定性 | 同一输入下连续执行两次，输出一致且日志是本次运行 | 幂等、可重复执行 |
| 失败路径治理 | 制造缺失输入后再次执行，必须返回非零且不留下最终交付物 | 严格错误传播、失败清理 |
| 全输入校验 | 逐个移除四份输入文件后复跑，必须立刻失败且不保留最终交付物 | 输入存在性校验、早失败 |
| alternate fixture | 在带空格路径的复制工作区和另一套真实数据切片上仍然通过 | 变量引用安全、通用化而非硬编码 |
| 自定义临时目录 | 指定带空格的 `AIRPORTS_TMP_DIR` 后仍然通过，且任务结束后目录被清空 | 临时目录约定、安全清理 |
| 重复触发隔离 | 同一输出目录上已有一次重建在执行时，新的执行必须被拒绝且不能破坏第一条运行的最终产物 | shell 并发防踩踏、输出发布治理 |
| 中断后恢复 | 成功发布后再次重建并在中途终止，必须撤掉旧完成态与内部控制痕迹，并允许同目录干净重跑成功 | 信号退出治理、清理收口、恢复性重试 |

防作弊测试
| 测试点 | 验证内容 |
| :--- | :--- |
| 输入不可篡改 | 基线输入数据文件哈希不得变化 |
| 真实链路保留 | 既有 shell 入口和阶段脚本必须保留且仍可执行 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把 shell pipeline 的失败传播、路径安全、输入校验、临时目录处理和输出交付方式标准化，从而显著降低试错成本；而 alternate fixture、失败复跑和链路保留约束，可以有效拦住只修表面症状或直接换实现的解法。

基于最近 **4 次** 有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除非任务本体失败的 `ReadError` trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0/4` | `2/4` | 近 4 次有效对照里，without Skill 始终卡在共享临时根目录并发隔离与中断清理；with Skill 有 2 次完整通过。 |
| Agent 执行耗时 | `493.6s` | `510.3s` | With Skill 的成功样本会做更完整的诊断与验证，平均耗时略高约 `3.4%`，但换来了明显更高的通过率。 |
| Tokens | `611,481` | `635,147` | With Skill 的平均 token 略高约 `3.9%`；without Skill 更早停在未修复状态，token 反而更低。 |

另有 1 条 `with_skill` E2B run 在 task-level 过程中遭遇 `ReadError`，未计入有效对照统计。

## 📁 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── bin/
│   ├── data/
│   └── skills/
├── tests/
│   ├── fixtures/
│   ├── test.sh
│   ├── test_outputs.py
│   ├── test_guardrails.py
│   └── conftest.py
└── solution/
    ├── fixed/
    └── solve.sh
```
