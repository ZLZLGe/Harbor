# Design Template

这是面向 `design` 类 skill 的模板。它综合参考 SkillsMP design 类热门 skill 的共性能力：把素材包、结构化数据、引用约束和视觉方向整合成可直接交付的浏览器端成果，并通过运行时验证确保成品在真实使用场景下可读、可导航、可复核。

## 第一部分：任务设计参考

* **Skill 价值定位**：design 类热门 skill 的核心价值，不只是“做得好看”，而是把内容结构、视觉系统、信息密度、交互方式和交付介质统一起来，形成真正可用的最终产物。对 HTML slides 这一子类来说，skill 的价值尤其体现在视口约束、多终端适配、离线交付和视觉探索闭环，而不是单纯输出一页静态页面。
* **Task 目标形态**：这类任务更适合设计成“给定真实素材包与数据约束，生成正式交付物”的形态，而不是纯审美题或故障排查题。理想目标是让 solver 必须处理结构化内容编排、图表落地、引用一致性、交互方式和多尺寸呈现，最终输出一个真实团队会接收的浏览器端成品。
* **Verifier 设计重点**：Verifier 不应把判断停留在文件是否存在或样式是否像模板，而应验证最终产物是否在真实使用条件下成立。对 slides / HTML presentation 类任务，重点应覆盖离线运行、导航行为、单页视口完整展示、真实 DOM 文本、数据与引用映射一致性，以及防止把任务偷换成长滚动页面、截图拼装页或远程依赖页面。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`design__renewable-briefing-deck`
- 类别：`design`
- 难度：`hard`
- 绑定 Skill：`frontend-slides`
- 输入数据参考来源：
  - `environment/data/series/global_renewables_2014_2023.csv`：任务内全球年度发电与可再生发电时间序列；数据筛选自 Our World in Data energy dataset  
    <https://github.com/owid/energy-data/blob/master/owid-energy-data.csv>
  - `environment/data/series/country_renewables_share_2019_2023.csv`：任务内国家年度可再生发电占比与结构对比；数据筛选自 Our World in Data energy dataset  
    <https://github.com/owid/energy-data/blob/master/owid-energy-data.csv>
  - `environment/data/series/country_mix_2023.csv`：任务内 2023 年重点国家发电结构快照；数据筛选自 Our World in Data energy dataset  
    <https://github.com/owid/energy-data/blob/master/owid-energy-data.csv>
  - `environment/data/brief/briefing_requirements.json`：任务内简报结构、交付约束与叙事重点；设计形态参考 IEA 对 2030 年可再生扩张的公开分析  
    <https://www.iea.org/commentaries/tripling-renewable-power-capacity-by-2030-is-vital-to-keep-the-15c-goal-within-reach>
  - `environment/data/brief/editorial_notes.json`：任务内风险与行动提示；设计形态参考 IEA 2025 pledge update 和 IRENA Renewable Capacity Statistics 2025  
    <https://www.iea.org/reports/cop28-tripling-renewable-capacity-pledge-2025-update>  
    <https://www.irena.org/Publications/2025/Mar/Renewable-capacity-statistics-2025>
  - `environment/data/sources/source_catalog.json`：任务内引用目录；链接直接对应本地 registry 暴露的真实来源  
    <https://github.com/owid/energy-data/blob/master/owid-energy-data.csv>  
    <https://www.iea.org/commentaries/tripling-renewable-power-capacity-by-2030-is-vital-to-keep-the-15c-goal-within-reach>  
    <https://www.iea.org/reports/cop28-tripling-renewable-capacity-pledge-2025-update>  
    <https://www.irena.org/Publications/2025/Mar/Renewable-capacity-statistics-2025>

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：Oracle 用官方 `solve.sh` 把正式 `build_briefing.py` 回写到环境入口，再通过同一个正式入口生成 `presentation.html`、`presentation_manifest.json` 和 `source_audit.json`。Verifier 随后在真实浏览器里检查 deck 的离线运行、导航行为、视口完整性、DOM 文本和引用一致性。
- Verifier 策略：

主测试

| 测试点 | 验证内容 | 对应 skill 内化点 |
| :--- | :--- | :--- |
| 输出合同 | 三个正式产物存在且 JSON 合同完整，slide count / viewport targets / source audit 符合题面 | 交付物完整性、正式入口回写 |
| 本地引用链路 | `build_briefing.py` 必须真实访问本地 source registry，并把 source id / label / URL 写入最终结果 | 来源核对、真实链路保留 |
| 浏览器结构 | 8 张 slide 真正渲染，文字保留在 DOM 中，不是 canvas 或整页图片拼装 | HTML slide 语义结构、可访问内容 |
| 交互导航 | 键盘、滚轮、触摸都能切换 slide，且不是靠文档整体滚动伪装 | presentation controller、多输入导航 |
| 多视口 fit | 在 5 个目标尺寸下，slide 本体和关键页脚都完整留在 viewport 内且无内部滚动 | viewport-safe layout、内容密度控制 |
| 离线完整性 | 页面不存在远程字体/脚本/样式/图片请求，浏览器运行时不泄漏外链依赖 | zero-dependency / offline delivery |
| 数据与图表 | 所需 chart id 与 manifest 一致，世界趋势、结构变化、国家对比都真正落图 | 数据驱动视觉产物 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 输入保护 | 核对数据快照、source catalog 和本地 registry 服务文件哈希，防止修改输入或下游服务 |
| 长滚动伪装 | 检查是否缺失 `100vh` slide 约束、是否没有 wheel / touch / keydown 导航逻辑，拦截把任务偷换成长页面 |
| 引用一致性 | manifest 与 source audit 的 source 集合必须一致，且必须能从 registry request log 证明真实访问过本地服务 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值不是“帮忙画一页好看的图”，而是把 HTML slides 的完整工作流标准化，包括内容分段、视觉系统选择、离线打包、导航控制、视口安全和浏览器验收。without Skill 更容易停在“能打开的网页”而不是“真正可交付的 deck”。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0/3` | `3/3` | With Skill 在最终版 3 次有效 trial 中全部通过；Without Skill 3 次都留有至少 1 项 verifier 失败，且失败集中在探索稿保留、8 页 deck 结构、视口约束与导航链路这类行动级工作流缺口。 |
| Agent 执行耗时 | `737.0s` | `1219.1s` | With Skill 明显更重，因为它更稳定地执行了视觉探索、正式收敛和引用核对这整套流程；Without Skill 虽然平均耗时更低，但没有一条能完成最终交付合同。 |
| Tokens | `875.9K` | `4.12M` | With Skill 的上下文和执行开销更高，主要来自 3 轮风格探索、正式 deck 收敛和多环节自检；这部分成本换来了稳定的 task-level 通过，而 Without Skill 仍停留在未收敛的行动层失败。 |

## 📁 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── data/
│   ├── deck/
│   ├── services/
│   └── skills/
│       └── frontend-slides/
├── tests/
│   ├── test.sh
│   ├── test_helpers.py
│   ├── test_outputs.py
│   └── test_guardrails.py
└── solution/
    ├── fixed/
    └── solve.sh
```
