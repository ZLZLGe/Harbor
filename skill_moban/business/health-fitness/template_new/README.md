# Health-Fitness Template

这是面向 `health-fitness` 类 skill 的模板。它综合参考 SkillsMP health-fitness 类热门 skill 的共性能力：把训练动作筛选、饮食选择、宏量营养核算、周内覆盖检查和教练交接整合成一条可执行的交付链路。

## 第一部分：任务设计参考

* **Skill 价值定位**：health-fitness 类热门 skill 的稳定价值，通常在于把“训练安排是否合规、餐单是否达标、交付是否能直接执行”这三件事连起来。模板题面应明确交付合同和业务约束，把动作筛选顺序、宏量营养核算细节和选择路径留给 skill 与 solver 自己处理。
* **Verifier 设计重点**：Verifier 应优先检查行动层结果是否成立，例如是否选到了当前可用动作、是否避开了旧 shortlist 中已不合适的条目、是否把每个餐日算进目标范围、是否把关键变化写进交接。它还应压住靠旧导出偷懒、漏掉当前目录新增条目、或只做表面文件拼装的捷径。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`health-fitness__strength-cycle-meal-plan`
- 类别：`health-fitness`
- 绑定 Skill：`fitness-nutrition`
- 输入数据参考来源：
  - `environment/data/exercise_catalog.json`：任务内动作目录；设计形态参考 wger exercise catalog 与 exercise info  
    https://wger.de/api/v2/
  - `environment/data/food_catalog.csv`：任务内食物与宏量营养目录；设计形态参考 USDA FoodData Central API 与下载数据  
    https://api.nal.usda.gov/fdc/v1/  
    https://fdc.nal.usda.gov/download-datasets/
  - `environment/data/program_rules.json`：任务内训练覆盖与营养目标规则；规则形态参考 CDC 体能活动建议与 Dietary Guidelines for Americans  
    https://www.cdc.gov/physical-activity/php/guidelines-recommendations/index.html  
    https://www.dietaryguidelines.gov/

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：

主测试

| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 输出契约 | 检查 4 个输出文件存在、可解析，并包含必需字段、列名和标题 | 先理解交付合同，再组织最终结果 |
| 训练安排 | 检查 4 天动作选择、器械匹配、周内覆盖和组数累计 | 从当前动作目录里做出正确选择 |
| 餐单结果 | 检查 2 个餐日的食物选择、份量和宏量营养计算 | 从当前食物目录里算对热量与宏量营养 |
| 总结一致性 | 检查 summary 中的目标范围、餐日总量和覆盖标记 | 让计划、汇总和计算保持一致 |
| 交接信息 | 检查 handoff 是否写出旧 shortlist 变更和当前关键条目 | 把变化和关注项交接给教练 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 当前目录优先 | 最终训练计划必须包含当前目录新增的关键动作，不能只沿用旧 shortlist |
| 旧条目拦截 | 旧 shortlist 里的不可用动作和已禁用食物不能进入最终输出 |
| 计算对齐 | verifier 会重算餐日总量和周内组数，防止只拼字段不做核算 |
| 资产保护 | `/root/data/` 文件内容不得变化 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值，是把当前目录筛选、训练安排、餐单核算和交付校验串成一条清晰工作流；缺少 skill 时，更容易在旧 shortlist 依赖、动作替换和宏量营养计算上出现行动级失误。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | 近 3 次有效对照里，without Skill 都保留了至少 1 项 verifier 失败，主要集中在复用动作、把 servings 写成小数、以及餐日汇总未对齐；with Skill 都能稳定完成交付。 |
| Agent 执行耗时 | `270.7s` | `172.5s` | With Skill 的筛选、构建和校验路径更短，平均 Agent 耗时降低约 `36.3%`。 |
| Tokens | `323,435` | `292,801` | Without Skill 的试错与回看开销更高，平均总输入输出 tokens 约为 With Skill 的 `1.10x`。 |

## 📁 标准目录结构说明

```text
模板任务：
├── instruction.md          # 任务说明（仅包含症状、业务约束和禁止事项）
├── task.toml               # 任务元数据（标签、技能要求、运行入口）
├── PLAN.json               # 任务构建过程的结构化元信息
├── environment/            # 运行环境
│   ├── Dockerfile          # 单容器镜像定义
│   ├── data/               # 当前目录数据与较早 shortlist 导出
│   └── skills/             # 任务绑定的 health-fitness skill 定义与配套脚本
├── tests/                  # Verifier 与 Guardrail 测试集
└── solution/               # 官方参考解法及 solve.sh
```
