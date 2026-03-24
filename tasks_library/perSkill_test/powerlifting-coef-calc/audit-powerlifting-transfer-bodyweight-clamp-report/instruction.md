你需要读取 `/root/data/extreme_bodyweight_audit_input.json`，并生成 `/root/data/bodyweight_clamp_audit.json`。

输入文件是一个 JSON 对象，顶层包含：

- `meet_id`
- `audit_batch`
- `athletes`

其中 `athletes` 是一个数组；每个元素都包含：

- `athlete_id`
- `profile`
  - `lifter_name`
  - `sex`
- `weigh_in`
  - `bodyweight_kg`
- `best_lifts_kg`
  - `squat`
  - `bench`
  - `deadlift`

请输出一个新的 JSON 对象，并满足下面要求：

1. 顶层字段必须且只允许包含：`meet_id`、`audit_batch`、`summary`、`entries`。
2. `meet_id` 和 `audit_batch` 直接从输入复制。
3. `entries` 必须按输入里 `athletes` 的原始顺序逐条输出，不要重排。
4. 每条 `entries` 记录必须且只允许包含这些字段：
   `athlete_id`、`lifter_name`、`sex`、`original_bodyweight_kg`、`applied_bodyweight_kg`、`adjustment`、`total_kg`、`dots`
5. `total_kg` 等于 `squat + bench + deadlift`，并四舍五入到 3 位小数。
6. `applied_bodyweight_kg` 要按性别分别裁剪：
   - `M`：保底 `40.0`，封顶 `210.0`
   - `F`：保底 `40.0`，封顶 `150.0`
7. `adjustment` 只能使用这三个值：
   - `floor_to_min`
   - `cap_to_max`
   - `none`
8. `dots` 使用裁剪后的体重和 `total_kg` 计算，并四舍五入到 3 位小数。
9. `summary` 必须且只允许包含这 5 个字段：
   - `athlete_count`
   - `adjusted_count`
   - `floor_adjustment_count`
   - `cap_adjustment_count`
   - `unchanged_count`
10. `summary` 中的计数要与 `entries` 严格对应。
11. 所有数值字段都写成 JSON 数字，不要写成字符串。
12. 不要输出任何额外字段、注释或 Markdown。

Dots 公式系数如下。

男性：

`score = total_kg * (500 / (a*x^4 + b*x^3 + c*x^2 + d*x + e))`

- `a = -0.0000010930`
- `b = 0.0007391293`
- `c = -0.1918759221`
- `d = 24.0900756`
- `e = -307.75076`

女性：

`score = total_kg * (500 / (a*x^4 + b*x^3 + c*x^2 + d*x + e))`

- `a = -0.0000010706`
- `b = 0.0005158568`
- `c = -0.1126655495`
- `d = 13.6175032`
- `e = -57.96288`

其中 `x` 是按第 6 条裁剪后的 `applied_bodyweight_kg`。
