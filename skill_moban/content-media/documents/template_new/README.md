# Documents Template

这是面向 `documents` 类 skill 的模板。它综合参考 SkillsMP documents 类热门 skill 的共性能力：结构化文档交付、现有草稿沿用、内容替换、图表落版、清理审阅残留和可复跑的生成入口。

## 第一部分：任务设计参考

* **Skill 价值定位**：documents 类 skill 的核心价值，是把“把资料写进文档”推进到“沿用既有文档壳完成正式交付”。模板任务应让 skill 在 `.docx` 包结构理解、占位替换、媒体落版、文档清理和交付入口收敛上形成明显帮助。
* **Task 目标形态**：任务适合设计成已有 Word 草稿上的正式交付，例如简报包、备忘录、评审材料或成套说明文档。目标应强调沿用原有样式壳、章节顺序、页眉页脚和文档入口，同时要求数据驱动内容真正落到最终文档。
* **Verifier 设计重点**：Verifier 应同时检查文档内容、文档壳保留、包内媒体替换、清理状态和可复跑入口。重点应覆盖输入不可改、skill 区域不可改、占位文本清除、评论或审阅残留清除、文档与 manifest 一致，以及 alternate fixture 下的泛化能力。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`documents__north_america_energy_briefing_packet`
- 类别：`documents`
- 难度：`hard`
- 绑定 Skill：`docx`
- 输入数据参考来源：
  - `environment/briefing/data/country_profile.json`：任务内国家基础信息；直接来源于  
    【https://api.worldbank.org/v2/country/USA;CAN;MEX?format=json&per_page=100】
  - `environment/briefing/data/world_bank_population.json`：任务内人口数据快照；直接来源于  
    【https://api.worldbank.org/v2/country/USA;CAN;MEX/indicator/SP.POP.TOTL?format=json&per_page=20000】
  - `environment/briefing/data/world_bank_gdp.json`：任务内 GDP 数据快照；直接来源于  
    【https://api.worldbank.org/v2/country/USA;CAN;MEX/indicator/NY.GDP.MKTP.CD?format=json&per_page=20000】
  - `environment/briefing/data/annual_co2_emissions.csv`：任务内年度 CO2 排放数据快照；直接来源于  
    【https://ourworldindata.org/grapher/annual-co2-emissions-per-country.csv?v=1&csvType=full&useColumnShortNames=false】
  - `environment/briefing/data/electricity_prod_source.csv`：任务内电力来源结构数据快照；直接来源于  
    【https://ourworldindata.org/grapher/electricity-prod-source-stacked.csv?v=1&csvType=full&useColumnShortNames=false】

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：Oracle 通过正式 build 入口从同一份本地 briefing 输入重建输出，独立计算每项指标的最新共同年份、摘要数字和图表依赖，再检查最终 `.docx` 包和 manifest 是否与合同一致。
- Verifier 策略：

主测试

| 测试点 | 验证内容 | 对应 skill 内化点 |
| :--- | :--- | :--- |
| 正式产物生成 | build 入口生成 `.docx` 与 manifest | 文档交付入口收敛 |
| 合同内容落版 | 必备章节、表格和图表标识出现在正式文档中 | 文档内容替换与结构保留 |
| 文档壳保留 | 页眉、页脚、样式壳和附录入口继续可用 | 编辑既有 `.docx` 而非另起外壳 |
| 清理状态 | 占位文本、评论残留和演示文字被清掉 | 审阅状态清理 |
| manifest 对齐 | 章节、图表、表格和指标年份与文档一致 | 结构化交付清单 |
| alternate fixture 泛化 | 同一 build 入口在替代输入下重新产出并变化 | 可复跑工作流 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 输入不可变 | `/app/briefing` 文件哈希不变 |
| Skill 载荷不可变 | `environment/skills/docx` 哈希不变 |
| 输出白名单 | `/app/output` 顶层仅有规定产物 |
| 占位残留 | 输出中不允许出现占位或定向测试痕迹 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把现有 Word 草稿、OOXML 包编辑、图表替换和清理收尾串成一条可执行路径；如果没有这条路径，agent 更容易把任务做成外部格式导出、另起文档壳，或停在包内媒体替换与残留清理阶段。

基于最近 **3 次** 有效对比实验（round12、round13、round14；均为真正跑到 task-level、存在完整 agent 轨迹；已排除 build cancelled 类 trial），并按最终稳定版 verifier 口径统一判读：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | 这 3 次有效对比里，without skill 都停在 `.docx` 包损坏或正式文档结构收尾失败；with skill 在最终 verifier 口径下都能交出完整文档包。 |
| Agent 执行耗时 | `514.8s` | `565.5s` | with skill 为了读取和沿用 `.docx` 工作流，平均执行时长略高，增加约 `9.8%`，但换来了稳定通过。 |
| Tokens | `2.15M` | `3.24M` | with skill 会为 OOXML 结构理解和文档清理投入更多上下文；without skill 虽然 tokens 更低，但仍停在无效交付。 |

## 📁 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── briefing/
│   ├── workspace/
│   └── skills/
├── tests/
│   ├── conftest.py
│   ├── test.sh
│   ├── test_guardrails.py
│   └── test_outputs.py
└── solution/
    └── solve.sh
```
