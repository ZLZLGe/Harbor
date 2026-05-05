# Gaming Template

这是面向 `gaming` 类 skill 的模板。它综合参考 SkillsMP gaming 类热门 skill 的共性能力：程序化生成、场景参数控制、页面内状态切换、本地数据驱动展示、浏览器即时反馈与可复现输出。

## 第一部分：任务设计参考

* **Skill 价值定位**：gaming 类热门 skill 的核心价值，通常在于把玩法规则、程序化内容、状态切换和交互呈现组合成一份可直接操作的浏览器交付物。模板任务应让 skill 在数据解释、生成逻辑、交互分区和可复现行为上明显降低试错成本，而不只奖励把数据摆成静态图表。
* **Task 目标形态**：任务适合要求 Agent 读取本地游戏数据快照、交付合同和页面骨架，在单页面环境里完成一份可浏览、可切换、可导出的互动成品。目标形态应强调同一输入下结果一致、不同输入下结果有可观察差异，并保留团队接手所需的说明与结构完整性。
* **Verifier 设计重点**：Verifier 应同时检查页面能否启动、交互控件是否齐备、局部状态变化是否符合合同、导出内容是否可追溯到输入数据，以及可复现约束是否成立。除此之外，还要覆盖输入不可改写、skill 文件不可改写、禁止占位输出与 verifier-hack 等 guardrail。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`gaming__kanto_encounter_atlas`
- 类别：`gaming`
- 难度：`hard`
- 绑定 Skill：`algorithmic-art`
- 输入数据参考来源：
  - `environment/data/pokedex_kanto.json`：Kanto 图鉴快照；设计形态参考 PokeAPI Kanto Pokedex  
    【https://pokeapi.co/api/v2/pokedex/2/】
  - `environment/data/encounter_zones.json`：区域遭遇层、等级区间、出现权重与地点分组；设计形态参考下列 location-area 接口  
    【https://pokeapi.co/api/v2/location-area/viridian-forest-area/】  
    【https://pokeapi.co/api/v2/location-area/mt-moon-1f/】  
    【https://pokeapi.co/api/v2/location-area/rock-tunnel-1f/】  
    【https://pokeapi.co/api/v2/location-area/kanto-power-plant-area/】  
    【https://pokeapi.co/api/v2/location-area/seafoam-islands-b1f/】  
    【https://pokeapi.co/api/v2/location-area/kanto-safari-zone-middle/】
  - `environment/data/type_relations.json`：属性攻防关系与分组；数据形态参考 PokeAPI type 接口  
    【https://pokeapi.co/api/v2/type/】

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：Oracle 使用同一批本地 JSON 快照、同一份 render contract 和官方 `solution/studio` 成品独立完成浏览器验证，重点覆盖页面启动、交互合同、种子复现、摘要计算和导出结构。
- Verifier 策略：

主测试

| 测试点 | 验证内容 | 对应 skill 内化点 |
| :--- | :--- | :--- |
| 页面与入口 | `index.html`、`app.js`、`styles.css`、`notes.md` 完整，页面可启动且使用本地数据与本地 vendor | 保留既有页面入口与单页交付结构 |
| 控件与分区合同 | 种子输入、区域切换、摘要区、导出按钮、局部说明区齐备 | 参数探索、交互分区与浏览器内工作流 |
| 同种子复现 | 重生成与刷新后，同一输入条件下场景和导出载荷保持一致 | seeded randomness 与 deterministic replay |
| 不同种子差异 | 不同种子或跳转输入会带来可观察的场景差异 | 参数驱动的程序化变化 |
| 区域摘要与高亮 | zone summary、highlighted species、type pressure、zone signals 与本地数据对应 | 用输入数据驱动叙事层与解释层 |
| 导出结构 | 导出 JSON 的 schema、字段口径和数值来源符合合同 | 可导出、可追溯的交付结果 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 输入不可改写 | 校验 `/app/data` 哈希，防止通过改输入规避合同 |
| Skill 不可改写 | 在有 skill 的变体中校验 `environment/skills/algorithmic-art` 内容哈希 |
| 禁止占位与投机输出 | 扫描 `studio/` 文件中的 placeholder、verifier-hack 和答案型痕迹 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把 seeded generative viewer、参数探索、可复现场景和页面内解释层组织成一套收敛更快的实现路径。当前 verifier 也会继续卡住只做表层摘要、缺少交互解释层或缺少可复现生成链路的解法。

基于最近 **3** 次有效对比实验（均为完整 task-level 运行，并按最终 verifier 口径核对）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0/3` | `3/3` | 最近 3 次有效对照里，without Skill 主要停在 seeded 复现稳定性、参数几何语义或分析面板语义层；with Skill 在最终口径下稳定满足交付合同 |
| Agent 执行耗时 | `733.4s` | `749.5s` | With Skill 平均耗时略高约 `2.2%`，但更多时间花在把交付收尾到 verifier 通过，而不是在无效试错上反复回摆 |
| Tokens | `2.77M` | `2.16M` | Without Skill 的上下文与试错开销约为 With Skill 的 `1.28x` |

## 📁 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── environment/
│   ├── Dockerfile
│   ├── data/
│   ├── skills/
│   ├── verifier/
│   └── workspace/
├── tests/
├── solution/
└── README.md
```
