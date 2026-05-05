Culinary Arts Template

This template is for culinary-arts skills that turn planning intent into an operational packet. It synthesizes common strengths from high-signal SkillsMP culinary skills: structured meal lookup, recipe-to-procurement transformation, and lightweight nutrition review tied to a concrete service plan.

## 第一部分：任务设计参考
* **Skill 价值定位**：Culinary-arts skills are most valuable when the solver must pull meal or recipe facts from a dedicated planning surface, carry those facts through ingredient and schedule decisions, and produce outputs that a kitchen or event team can act on immediately. The strongest skills reduce search friction, standardize lookup order, and keep procurement or nutrition decisions anchored to the same source of truth.
* **Task 目标形态**：A strong task in this category should ask for a deliverable packet, not freeform cooking advice. Typical outputs are a scheduled meal manifest, a consolidated shopping or prep delta, and a concise nutrition or service review derived from the same operational data.
* **Verifier 设计重点**：Verifier design should check both result correctness and workflow discipline. For this category, that usually means recomputing meal coverage, ingredient rollups, and nutrition checks from source records, then separately checking that the solver used the intended planning interface rather than bypassing it with backing-store reads.

## 第二部分：示例任务
### 📌 任务元数据
- 任务 ID：`culinary-arts__paprika_workshop_ops_packet`
- 类别：Culinary Arts
- 难度：`hard`
- 绑定 Skill：`paprika`, `healthy-eating`
- 输入数据参考来源：
  - `environment/paprika_seed/recipes.json`：任务内 Paprika recipe detail records；具体 recipe 来源形态参考  
    【https://www.themediterraneandish.com/chickpea-salad/】  
    【https://www.bbcgoodfood.com/recipes/orzo-salmon-traybake】  
    【https://www.eatingwell.com/recipe/275923/white-bean-turkey-bowls/】  
    【https://www.feastingathome.com/miso-tofu-bowls/】  
    【https://www.loveandlemons.com/quinoa-lentil-salad/】  
    【https://www.delish.com/cooking/recipe-ideas/a28625784/sheet-pan-pesto-chicken-recipe/】
  - `environment/paprika_seed/meals.json`：任务内 meal-plan rows；Paprika meal planning interface 形态参考  
    【https://www.paprikaapp.com/】
  - `environment/paprika_seed/groceries.json`：任务内 grocery carryover rows；Paprika grocery list interface 形态参考  
    【https://www.paprikaapp.com/】
  - `environment/data/event_brief.json`：任务内 nutrition target brief；daily target framing 参考  
    【https://www.dietaryguidelines.gov/】

### 📊 验证与测试指标（Oracle & Verifier）
- Oracle：Oracle 通过官方 `solution/solve.sh` 在同一 E2B 单容器环境中调用本地 Paprika CLI，生成四个正式交付文件，再运行全量 verifier。当前最终版 Oracle cloud run 已通过，reward=`1.0`。
- Verifier策略：

主测试

| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| Scheduled meal coverage | `meal_manifest.json` 是否按服务日期和 meal slot 完整覆盖 6 个计划餐次 | `paprika meals --json` |
| Recipe detail hydration | recipe UID、标签、时长、serving 放大后是否与预期一致 | `paprika recipe <uid> --json` |
| Carryover-adjusted shopping delta | pantry 扣减、reserved grocery 扣减、正向采购行排序是否正确 | `paprika groceries --all --json` |
| Daily nutrition audit | 每日 kcal / protein / fiber 结果与 target check 是否一致 | `healthy-eating` 的 nutrition check framing |
| Kitchen handoff contract | note 结构、菜名覆盖、carryover 摘要是否完整 | 从操作数据提炼可执行 handoff |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| Visible inputs unchanged | `/root/data` 输入快照保持不变 |
| Paprika seed unchanged | backing seed 数据未被篡改 |
| Bound skill payload unchanged | shipped skill 文件保持原样，without-skill 变体不额外注入任务 skill |
| Workflow guardrail | access log 必须体现 `paprika` CLI entrypoint 的 meals / recipe / groceries 查询 |
| Output boundary | `/root/output` 之外不能生成额外顶层交付物 |

### ⚡ Skill 相关性评估
结论：强相关。这个任务的核心差异在于，with-skill 直接把 Paprika lookup workflow 固化为 `paprika meals --json`、`paprika recipe <uid> --json` 和 `paprika groceries --all --json` 的工作链，而 without-skill 会更容易自行发现内部入口并绕开 skill 约定的 CLI entrypoint。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | 近 3 次有效对照里，without Skill 都在 workflow guardrail 上失败：agent 使用了内部 `mealops` 路径，没有走 skill 指定的 `paprika` CLI entrypoint |
| Agent 执行耗时 | `192.9s` | `175.9s` | With Skill 的发现和收敛更快，平均 Agent 耗时降低约 `9%` |
| Tokens | `195156.3` | `137603.0` | Without Skill 的上下文与试错开销约为 With Skill 的 `1.42x` |

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
│   ├── paprika_cli/
│   ├── paprika_seed/
│   └── skills/
├── tests/
└── solution/
```
