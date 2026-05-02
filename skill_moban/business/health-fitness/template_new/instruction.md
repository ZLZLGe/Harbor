你需要为一家精品健身工作室的一位新会员生成下一周的 7 天入门方案，交付给门店教练与营养顾问。现有 intake 文件和候选动作/食物导出已经放进容器，但它们可能过期或不完整；当前容器内的 planning service 才是本次交付应依据的权威来源。

输入数据在 `/root/data/`：

- `planner_manifest.json`：会员 ID、计划窗口、交付要求，以及本地 planning service 的 base URL。
- `member_profile.json`：会员基础信息、目标阶段、训练经验、可训练日期、过敏原、不吃食材、动作禁忌和器械限制。
- `equipment_inventory.csv`：当前门店可用器械、别名和可替代器械分组。
- `meal_slot_rules.csv`：早餐、午餐、训练前、训练后、晚餐等餐次的角色约束和最小要求。
- `reference_exercise_shortlist.json`：较早导出的候选动作列表，可能缺项或已过期。
- `reference_food_shortlist.csv`：较早导出的候选食物列表，可能缺项或已过期。

你的任务

1. 完成该会员的结构化评估，并生成后续训练与饮食方案需要使用的关键指标。
2. 为该会员制定 4 次训练课表，并覆盖 `member_profile.json` 中要求的全部训练日。
3. 为该会员制定两套可复用日型餐单：
   - 一套 `training_day`
   - 一套 `rest_day`
4. 为门店教练生成一份可直接执行的交接摘要。

输出

如 `/root/output/` 不存在，请先创建该目录。

1. 写入 `/root/output/member_assessment.json`

顶层结构必须严格如下：

```json
{
  "member_id": "HF-001",
  "goal_phase": "cut",
  "bmi": 0.0,
  "bmr_kcal": 0.0,
  "tdee_kcal": 0.0,
  "training_day_kcal": 0.0,
  "rest_day_kcal": 0.0,
  "protein_g": 0.0,
  "fat_g": 0.0,
  "carbs_training_g": 0.0,
  "carbs_rest_g": 0.0,
  "fiber_target_g": 0.0
}
```

要求：

- 所有数值字段必须为数值类型。
- `goal_phase` 必须与输入保持一致。
- 所有数值保留 2 位小数。
- 所有字段都必须依据当前权威数据和会员资料推导，不得留空或使用占位值。

2. 写入 `/root/output/workout_plan.csv`

列名必须严格如下：

```csv
session_id,day_label,focus_block,exercise_id,exercise_name,primary_muscle,equipment_name,sets,reps_min,reps_max,rest_seconds,notes
```

要求：

- 必须覆盖 `member_profile.json` 中要求的全部训练日。
- 每个 `session_id` 至少包含 4 个动作。
- 只能使用当前权威来源中存在且仍可用的动作。
- 只能使用 `equipment_inventory.csv` 中可用的器械或允许的替代器械。
- 必须遵守会员的伤病限制、禁忌动作关键字和禁用器械限制。
- 必须满足当前 program policy 的训练结构与安排要求。
- `notes` 必须是简短说明，指出该动作的用途、限制或替代背景。

3. 写入 `/root/output/meal_plan.csv`

列名必须严格如下：

```csv
day_type,meal_slot,food_id,food_name,grams,kcal,protein_g,carbs_g,fat_g,fiber_g
```

要求：

- `day_type` 只能是 `training_day` 或 `rest_day`。
- 两种 `day_type` 都必须出现。
- 每个 `meal_slot` 必须来自 `meal_slot_rules.csv`。
- 只能使用当前权威来源中存在且仍可用的食物。
- 必须遵守会员的过敏原和不吃食材限制。
- 每条食物记录的营养字段都必须与所选食物和填写克数一致。
- 所有食物克数必须是 5g 的整数倍。
- 单个餐次不得用空餐、删餐次或改餐次名称规避约束。
- 每种 `day_type` 的整日总量必须落在当前 program policy 规定的容差内。

4. 写入 `/root/output/coach_handoff.md`

内容必须包含以下一级标题，顺序不可变：

- `# Client Goal`
- `# Assessment`
- `# Training Plan`
- `# Nutrition Plan`
- `# Risks And Substitutions`

要求：

- 必须引用与 `member_assessment.json` 一致的核心指标。
- 必须概括与 `workout_plan.csv`、`meal_plan.csv` 一致的实际安排。
- 必须明确写出执行提醒、风险点和至少一种可落地的动作替代或饮食替代处理。

说明：

- 当前容器内 planning service 才是本次交付的权威来源。
- `reference_exercise_shortlist.json` 和 `reference_food_shortlist.csv` 只是较早导出，不是最终事实依据。
- 不要修改 `/root/data/` 下的任何输入文件。
- 不要替换真实链路、不要绕过本地 planning service、不要用缓存答案或手工伪造输出来代替真实规划过程。
- 不要删除训练日、删除餐次、删除约束、停掉服务，或通过删功能规避问题。
- 不要用虚构动作、虚构食物或外部网站上的其他数据替换本地数据链路。
- 不要修改 tests、verifier、skill 文件或 environment 文件。
- 你可以在工作目录中编写辅助脚本，但最终只需要提交 `/root/output/` 下要求的 4 个文件。

