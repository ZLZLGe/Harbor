# Transfer: 六角农田喷灌布局优化

你要为一块蜂巢式果园规划喷灌设备布局。

## 输入

读取场景文件：

- `/data/orchard_plan.json`

文件中给出：

- `coordinate_system`: 坐标系说明，本题固定为 `odd-r`
- `irrigation_radius`: 单个喷灌设备的覆盖半径
- `base_exclusion_distance`: 基座冲突阈值；若两个被选基座的六角距离小于等于该值，则不能同时选中
- `crops`: 全部作物格，包含 `id`、作物类型和坐标
- `candidate_bases`: 可安装喷灌设备的候选基座，包含 `id` 和坐标

坐标规则：

- 使用 **odd-r 偏移六角坐标**
- `x` 向右增加，`y` 向上增加
- 奇数行右移半格

## 任务

从 `candidate_bases` 中选出一个基座子集，使所有作物格都被覆盖，并且设备数最少。

## 规则

### 覆盖

1. 一个被选中的基座可以覆盖所有与它的六角距离 **不超过 `irrigation_radius`** 的作物格。
2. 所有作物格都必须至少被一个被选中的基座覆盖。
3. 只需要考虑对 `crops` 中作物格的覆盖，不需要输出空地或候选基座本身的覆盖情况。

### 基座冲突

1. 任意两个被选中的基座，如果它们的六角距离等于 `1`，则视为相邻冲突，不能同时选中。
2. 由于本题的 `base_exclusion_distance = 1`，所以六角距离大于 `1` 的两个基座才可以同时选中。

### 最优性与并列解

1. 优先使 `total_devices` 最小。
2. 如果存在多个设备数同样最少的可行方案，选择 `selected_bases` 中 `base_id` 升序后的列表按字典序最小的那一个。
   - 例如先比较第 1 个 `base_id`，若相同再比较第 2 个，依此类推。

## 输出

把结果写入：

- `/output/irrigation_layout.json`

输出格式必须是：

```json
{
  "selected_bases": [
    {"base_id": "BASE_A", "x": 1, "y": 5},
    {"base_id": "BASE_E", "x": 3, "y": 4}
  ],
  "base_coverages": [
    {"base_id": "BASE_A", "covers": ["PLOT_01", "PLOT_02"]},
    {"base_id": "BASE_E", "covers": ["PLOT_02", "PLOT_03"]}
  ],
  "crop_coverages": [
    {"crop_id": "PLOT_01", "covered_by": ["BASE_A"]},
    {"crop_id": "PLOT_02", "covered_by": ["BASE_A", "BASE_E"]}
  ],
  "total_devices": 2
}
```

## 输出要求

1. 顶层字段固定为：
   - `selected_bases`
   - `base_coverages`
   - `crop_coverages`
   - `total_devices`
2. `selected_bases`：
   - 必须按 `base_id` 升序排列
   - 每项字段固定为 `base_id`、`x`、`y`
   - 必须与输入中对应候选基座的坐标完全一致
3. `base_coverages`：
   - 必须与 `selected_bases` 一一对应，且顺序一致
   - 每项字段固定为 `base_id`、`covers`
   - `covers` 必须是该基座实际覆盖到的全部作物 `id`，按 `crop_id` 升序排列
4. `crop_coverages`：
   - 必须按 `orchard_plan.json` 中 `crops` 的原始顺序输出
   - 每项字段固定为 `crop_id`、`covered_by`
   - `covered_by` 必须列出覆盖该作物的全部已选基座 `id`，按 `base_id` 升序排列
5. `total_devices` 必须等于被选中的基座数量。
6. 输出必须是合法 JSON。
