你接手的是一个采石场重复爆破筛查批次。已有少量高信噪比参考事件已经人工审过，现在需要用这些参考事件去筛一批较弱、较脏的候选窗口，只保留真正属于这些重复家族的事件，并把 P/S 到时精修出来。

输入位于 `/root/repeaters/`：

- `/root/repeaters/template_manifest.csv`：模板库清单，给出每个参考模板的 `template_id`、模板文件路径，以及该模板对应的参考 `p_idx`、`s_idx`
- `/root/repeaters/candidate_manifest.csv`：候选窗口清单
- `/root/repeaters/survey_notes.txt`：本批次的简要背景
- 模板文件位于 `/root/repeaters/templates/`
- 候选窗口位于 `/root/repeaters/candidates/`

每个 `.npz` 文件至少包含：

- `data`: 三分量波形数组，形状为 `n_samples x 3`
- `dt`: 采样间隔（秒）
- `channels`: 通道顺序
- `start_time`: 窗口起始时间

你的任务是找出哪些候选窗口与模板库中的某个参考事件属于同一重复家族，并把结果写到 `/root/repeater_template_matches.csv`。

输出 CSV 必须包含且只包含以下 5 列：

1. `template_id`
2. `file_name`
3. `phase`
4. `pick_idx`
5. `score`

约束：

1. 只对真正匹配到某个模板家族的候选窗口输出结果；不相关窗口不要写入输出。
2. 每个被保留的候选窗口必须恰好输出两行：一行 `P`，一行 `S`。
3. 同一个候选窗口的两行必须使用同一个 `template_id`，并且 `P` 的 `pick_idx` 要早于 `S`。
4. `score` 使用 0 到 1 之间的浮点数，表示该候选窗口与所选模板家族的一致性；同一个候选窗口的 P/S 两行应写同一个分数。
5. 重点不是泛化到任意新事件，而是在已有高质量参考事件的前提下，把弱重复事件筛出来，并保证同一家族的到时更一致。

评测重点：

- 是否正确剔除了不属于任何模板家族的干扰窗口
- 是否给每个保留窗口选对了模板家族
- P/S 精修后的 `pick_idx` 是否足够接近参考答案
- `score` 是否与匹配强弱大体一致
