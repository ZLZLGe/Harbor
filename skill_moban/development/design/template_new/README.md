# Design Template

这是面向 `design` 类 skill 的模板。它综合参考 SkillsMP design 类热门 skill 的共性能力：HTML 演示文稿、设计系统、UI/UX 原型、响应式布局、可访问性、视觉层级、数据叙事、演示导航和浏览器验证闭环。

## 第一部分：任务设计参考

* **Skill 价值定位**：design 类 skill 的核心价值，是把内容、数据和品牌约束转化为可读、可演示、可验证的视觉体验。模板任务应让 skill 在视觉层级、设计 token、一致性、viewport fit、交互导航、reduced motion 和可访问语义上降低遗漏率，而不是只奖励漂亮截图或静态页面。
* **Task目标形态**：任务应要求 Agent 基于真实风格的业务数据、品牌约束和本地 API，产出可直接运行的设计交付物。目标形态适合设计成 HTML slide deck、交互原型、数据可视化演示、响应式 UI 或设计系统应用，不适合做普通长网页、静态图片、单屏 mockup 或不可用浏览器验证的纯视觉稿。
* **Verifier设计重点**：Verifier 应用真实浏览器检查视觉和交互行为，同时重算数据 grounding。重点应覆盖自包含 HTML、语义化 slide 结构、输入不可变、真实数据进入可见内容、键盘/滚轮/触摸导航、进度状态、reduced-motion、多视口无溢出、非图片伪装和反 verifier/test 引用。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`design__frontend-slides-mobility-operations-review`
- 类别：`design`
- 难度：`hard`
- 绑定 Skill：`frontend-slides`

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：Oracle 使用同一批城市微出行运营数据、品牌 token 和本地业务 API，独立生成并验证单文件 HTML executive deck。它关注 slide deck 是否可播放、可读、可访问、数据 grounded 且多视口不溢出，而不是视觉实现是否唯一。

- Verifier策略：

| Verifier 测试内容 | 对应 skill 要求掌握的部分 |
| :--- | :--- |
| 自包含 HTML、内联 CSS/JS、禁止 CDN/远程资源/runtime fetch | 零依赖浏览器交付与离线运行 |
| 8-10 个语义化 `<section>` slide、标题和 required story beats | slide deck 架构、演示叙事和信息层级 |
| city、quarter、KPI、区域、天气、投诉、建议等数据 grounding | 从多源业务数据生成 executive narrative |
| 至少 3 个数据可视化元素和品牌颜色 token 使用 | 数据图表、视觉系统和品牌一致性 |
| keyboard、wheel、touch、progress、reduced motion | 演示控制器、交互导航和可访问动效 |
| 1920x1080、1280x720、768x1024、375x667、667x375 viewport fit | responsive design、密度控制和移动端适配 |
| 输入/服务/skill hash、禁止图片伪装、隐藏文字和 verifier 引用 | 防作弊 guardrail、真实文本和可审计交付 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把自包含 HTML deck、viewport-safe CSS、演示控制器和浏览器尺寸验证标准化；without Skill 理论上能完成，但更容易在移动横屏、滚轮/触摸支持、内容密度和真实数据叙事上失败。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除早期 skill 未加载和 verifier 调整前 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | without Skill 三次均未通过，主要失败在移动端/横屏 viewport 溢出、演示导航不完整和数据内容组织不足；with Skill 三次全通过。 |
| Agent 执行耗时 | `743.3s` | `979.1s` | With Skill 花更多时间做 skill 阅读、自检和迭代，但换来稳定通过。 |
| Tokens | `1.74M` | `2.46M` | With Skill 上下文更大，主要来自读取 `SKILL.md` / `STYLE_PRESETS.md` 和浏览器自检过程。 |

## 📁 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── environment/
│   ├── Dockerfile
│   ├── build-scripts/
│   ├── data/
│   ├── hidden-service-src/
│   └── skills/
├── tests/
├── solution/
└── README.md
```
