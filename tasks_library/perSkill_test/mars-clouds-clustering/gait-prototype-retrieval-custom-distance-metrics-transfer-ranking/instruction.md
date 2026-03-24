# Transfer: 康复步态原型检索

## 任务目标

你需要在验证患者集上选出表现最好的特征加权距离配置，然后为待评估患者生成治疗原型库的 top-3 最近原型排行，并把结果写入 `/root/gait_protocol_rankings.csv`。

## 数据

数据位于 `/root/data/`：

- `gait_prototypes.csv`：治疗原型库，列为 `prototype_id, cadence_spm, stride_time_cv, left_right_asymmetry, knee_flexion_deg, balance_index, therapy_track`
- `validation_patients.csv`：用于选择权重配置的验证患者，列为 `patient_id, cadence_spm, stride_time_cv, left_right_asymmetry, knee_flexion_deg, balance_index, expected_best_prototype`
- `query_patients.csv`：需要输出排行的患者，列为 `patient_id, cadence_spm, stride_time_cv, left_right_asymmetry, knee_flexion_deg, balance_index`
- `weight_profiles.csv`：候选权重配置，列为 `profile_id, cadence_weight, stride_time_cv_weight, left_right_asymmetry_weight, knee_flexion_weight, balance_weight`

## 距离定义

对任意患者 `p` 与原型 `q`，先按以下固定尺度做归一化：

- `cadence_spm` 除以 `20`
- `stride_time_cv` 除以 `8`
- `left_right_asymmetry` 除以 `0.2`
- `knee_flexion_deg` 除以 `20`
- `balance_index` 除以 `50`

设归一化后的差值依次为：

- `dc`
- `ds`
- `da`
- `dk`
- `db`

若当前候选配置的五个权重分别为：

- `wc`
- `ws`
- `wa`
- `wk`
- `wb`

则患者与原型之间的距离为：

```text
distance(p, q) =
sqrt(
  (wc * dc)^2 +
  (ws * ds)^2 +
  (wa * da)^2 +
  (wk * dk)^2 +
  (wb * db)^2
)
```

距离越小，表示该原型越接近该患者。

## 选择最佳权重配置

对 `weight_profiles.csv` 中的每个 `profile_id`：

1. 对 `validation_patients.csv` 的每位患者，计算其到全部原型的距离
2. 按距离升序排列原型；若距离相同，则按 `prototype_id` 升序打破平局
3. 取每位验证患者的第 1 名原型，与 `expected_best_prototype` 比较
4. 计算 `validation_accuracy = 命中人数 / 验证患者总数`
5. 同时计算 `validation_mean_expected_distance`：每位验证患者到其 `expected_best_prototype` 的距离平均值

最佳配置按以下顺序确定：

1. `validation_accuracy` 更高
2. `validation_mean_expected_distance` 更低
3. `profile_id` 字典序更小

## 生成待评估患者排行

将选出的最佳配置应用到 `query_patients.csv`：

1. 对每位患者计算其到全部原型的距离
2. 取最近的 3 个原型
3. 对每位患者的 3 行结果按 `rank = 1, 2, 3` 输出
4. 全部结果先按 `patient_id` 升序，再按 `rank` 升序排列

## 输出

写入 `/root/gait_protocol_rankings.csv`，列顺序必须严格为：

```csv
patient_id,rank,prototype_id,therapy_track,distance,selected_profile,validation_accuracy
```

要求：

- 每位 `patient_id` 恰好输出 3 行
- `rank` 写成整数 `1` 到 `3`
- `distance` 保留 5 位小数
- `validation_accuracy` 保留 5 位小数
- `selected_profile` 必须是所有行都相同的最终入选配置名
