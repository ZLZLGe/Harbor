# Frontend Template

这是面向 Frontend 类 skill 的模板。它综合参考 SkillsMP Frontend 类热门 skill 的共性能力：组件组合、共享状态治理、URL 与页面状态同步、按需加载、键盘与焦点可访问性，以及在真实数据链路下修复运行时前端回归。

## 第一部分：任务设计参考

* **Skill 价值定位**：Frontend 类热门 skill 的核心价值，不是把页面“修到能看”，而是把组件结构、状态所有权、导航同步、性能边界和可访问交互变成稳定的工程模式。它帮助 solver 更快识别哪些 UI 症状其实来自状态源分裂、错误的加载时机或不完整的交互闭环。
* **Task 目标形态**：任务应落在真实风格的前端整改场景里，例如内部工作台、分析面板、运营后台或产品控制台。题面主要交代业务症状、运行边界和禁止事项，把状态诊断、组件收敛、性能处理和无障碍修复的具体路径留给 skill 和 solver 自己识别。
* **Verifier 设计重点**：Verifier 应优先验证真实前端行为，而不是只看静态 DOM 形状。重点包括 URL 与 UI 状态是否一致、最后一次用户意图是否覆盖旧状态、重型代码是否只在需要时加载、键盘与焦点是否形成闭环，以及在变体数据和历史导航下是否仍然稳定。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`react-energy-workbench-state-regressions`
- 类别：`Frontend`
- 难度：`hard`
- 绑定 Skill：`frontend-patterns`
- 输入数据参考来源：
  - `environment/data/owid_energy_snapshot.csv`：任务内国家年度能源指标快照；直接裁剪自 Our World in Data energy dataset  
    https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv
  - `environment/data/owid_energy_codebook.csv`：任务内指标说明与单位；直接裁剪自 Our World in Data energy codebook  
    https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-codebook.csv
  - `environment/data/world_bank_countries.json`：任务内国家地区与收入组元数据；直接来源于 World Bank Country API  
    https://api.worldbank.org/v2/country?format=json&per_page=400

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：官方解的核心不是“逐点打补丁”，而是把 URL、筛选、搜索、排序、当前查看上下文、比较区开合、详情抽屉和摘要/图表派生面收敛到同一份前端状态模型，再补齐按需加载、异步详情竞争和键盘/焦点闭环。只要沿着这条工程路径修复，Oracle 就能在真实数据链路和全部浏览器行为测试下稳定通过。
- Verifier策略：

主测试

| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 真实数据链路与共享状态恢复 | 基于本地 API 的真实国家数据，校验 deeplink、刷新、回退后，筛选/搜索/排序/比较/详情上下文，以及表格、摘要卡片、图表是否仍指向同一页面状态 | 单一状态源、URL 同步、派生视图一致性 |
| 当前查看上下文的分享与历史恢复 | 校验图表高亮区的当前查看模式能随 deeplink、刷新、回退保持一致，且与表格排序关系明确 | 路由状态建模、共享 UI context、历史导航 |
| 详情抽屉按需加载与最新意图获胜 | 详情抽屉必须延迟加载，并在快速切换国家时稳定落到最后一次点击目标 | 异步数据流、竞争保护、组件边界 |
| 详情抽屉的 modal 行为闭环 | 详情抽屉打开后要将焦点放入抽屉并保持在抽屉内，点击遮罩后还能正确关闭并清理监听器 | 可访问性、focus management、effect cleanup |
| 变体数据泛化 | 在替代夹具中加入 Spain 后，页面行为仍要沿真实排序和状态逻辑生效，不能只对固定国家写死 | 非硬编码实现、可泛化派生逻辑 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 输入数据与隐藏服务保护 | 校验 OWID / World Bank 数据快照和本地 API 服务 hash，防止通过改输入、改下游服务或改真实链路绕过问题 |
| 替代夹具回归 | 在不改题面的前提下切换替代数据夹具，拦截只对固定国家、固定排序路径成立的硬编码解 |
| Skill 可用性留痕 | 在 with_skill 试验中确认 agent 轨迹确实读取过绑定 skill，避免把无技能路径误记成技能路径 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，`frontend-patterns` 的核心价值不在于提示某个单点 bug，而在于更稳定地引导 solver 把 URL、共享状态、派生视图、按需加载和键盘焦点当成同一条前端状态链来修。新增的“当前查看上下文”恢复要求，会继续拦下只修表面筛选或只补局部组件行为的解法。

基于最近 **3** 次有效对比实验（`p6`、`p8`、`p9`；均真正跑到 task-level、存在完整 agent 轨迹，已排除 `BuildException` / 构建取消类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `66.7%` | 近 3 次有效对照里，without Skill 没有一次完整通过；主要失败集中在共享状态恢复、派生摘要一致性和抽屉交互闭环，而 with Skill 有 2 次完整通过。 |
| Agent 执行耗时 | `578.2s` | `549.2s` | With Skill 的诊断和收敛更快，平均 Agent 执行耗时降低约 `5.0%`。 |
| Tokens | `1.35M` | `1.41M` | 这 3 轮里 With Skill 的平均 tokens 略高约 `4.4%`；但这些额外开销换来了显著更高的通过率，而 without Skill 仍停留在动作级失败。 |

## 📁 标准目录结构说明

```text
模板任务：
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── app/
│   ├── data/
│   ├── energy-api/
│   └── skills/
├── tests/
└── solution/
```
