# Content Creation Template

这是面向 `content-creation` 类 skill 的模板。它综合参考 SkillsMP content-creation 热门 skill 的共性能力：把一份来源材料整理成多平台内容包，同时保持事实口径一致、平台开头区分清楚、交付清单可直接核验。

## 第一部分：任务设计参考

* **Skill 价值定位**：这类 skill 的共性价值，在于把单一资料包转成多平台成稿，并把“能写”推进到“能按发布场景交付成套内容”。模板任务应让 skill 在来源提炼、平台改写、事实收口和交付清单对齐上形成明显帮助。
* **Verifier 设计重点**：Verifier 应同时检查主张覆盖、事实口径、平台差异、输出清单和重跑适配能力。重点要拦下漏稿件、漏 claim、硬编码文案、改输入，以及把多平台稿件写成一份文案改壳这类问题。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`content_creation__north_america_power_mix_multichannel_pack`
- 类别：`content-creation`
- 绑定 Skill：`content-engine`
- 输入数据参考来源：
  - `environment/input/data/country_profile.json`：任务内国家基础信息；直接来源于  
    【https://api.worldbank.org/v2/country/USA;CAN;MEX?format=json&per_page=100】
  - `environment/input/data/world_bank_population.json`：任务内人口数据快照；直接来源于  
    【https://api.worldbank.org/v2/country/USA;CAN;MEX/indicator/SP.POP.TOTL?format=json&per_page=20000】
  - `environment/input/data/world_bank_gdp.json`：任务内 GDP 数据快照；直接来源于  
    【https://api.worldbank.org/v2/country/USA;CAN;MEX/indicator/NY.GDP.MKTP.CD?format=json&per_page=20000】
  - `environment/input/data/annual_co2_emissions.csv`：任务内年度 CO2 排放数据快照；直接来源于  
    【https://ourworldindata.org/grapher/annual-co2-emissions-per-country.csv?v=1&csvType=full&useColumnShortNames=false】
  - `environment/input/data/electricity_prod_source.csv`：任务内按能源来源拆分的发电数据快照；直接来源于  
    【https://ourworldindata.org/grapher/electricity-prod-source-stacked.csv?v=1&csvType=full&useColumnShortNames=false】
  - `environment/input/voice_samples/owid_observation.md`：任务内文风样本；设计形态参考  
    【https://ourworldindata.org/electricity-mix】
  - `environment/input/voice_samples/owid_comparison.md`：任务内文风样本；设计形态参考  
    【https://ourworldindata.org/co2-and-greenhouse-gas-emissions】
  - `environment/input/voice_samples/owid_close.md`：任务内文风样本；设计形态参考  
    【https://ourworldindata.org/energy】

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier 策略：

主测试

| 测试点 | 验证内容 | 对应 skill 内化点 |
| :--- | :--- | :--- |
| 输出生成 | 能生成完整内容包和 manifest | 完成交付主产物 |
| claim 覆盖 | 各稿件包含规定 claim 的关键事实 | 来源提炼与事实收口 |
| 平台区分 | 各平台开头和组织方式不重复套用 | 平台原生改写能力 |
| 清单对齐 | manifest 与各稿件、claim、来源文件一致 | 成套交付校对能力 |
| 重跑适配 | 替换输入后的关键数值与文案会同步更新 | 避免硬编码和一次性写法 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 保护输入 | 源文件（`/app/input`）未被篡改 |
| 输出限制 | `/app/output` 仅包含规定文件 |
| 隐藏作弊 | 结果中不能有占位痕迹或测试痕迹 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，skill 的核心价值是把同一份资料包改写成多平台内容，并把 hook、事实口径和 manifest 收口到一起。最近 3 次有效对比里，without_skill 的稳定短板集中在 manifest 来源映射不完整；with_skill 能更稳定地补齐来源链路与多平台区分，但仍可能在清单结构上出现一次性失误。

基于最近 `3` 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial，其中 1 次为按当前终版 verifier 复核）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0/3` | `2/3` | without_skill 三次都至少留下一项 verifier 失败，且都落在交付动作相关的来源映射问题；with_skill 有明显提升。 |
| Agent 执行耗时 | `401.7s` | `462.4s` | with_skill 平均更久，主要花在来源收口和平台差异化组织上；这次收益体现在通过率，不体现在耗时。 |
| Tokens | `603.9k` | `622.8k` | with_skill 的平均 tokens 略高，约为 without_skill 的 `1.03x`，换来更高的交付完成度。 |

## 📁 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── input/
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
