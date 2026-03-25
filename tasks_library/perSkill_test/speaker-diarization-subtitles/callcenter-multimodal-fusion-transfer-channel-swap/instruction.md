你会拿到一组已经从双人分屏客服培训片段中抽取好的证据文件：

- `/root/session_manifest.json`
- `/root/audio_activity_windows.json`
- `/root/split_screen_observations.json`

请基于这些输入生成 `/root/channel_swap_alerts.json`。

输出文件必须是一个 JSON 对象，并且只包含以下两个顶层字段：

- `session_id`: 字符串，必须等于 `session_manifest.json` 中的 `session_id`
- `alerts`: JSON 数组，按 `start_sec` 升序排列

`alerts` 数组中的每个元素都必须包含这些字段：

- `alert_id`: 字符串，按输出顺序依次写成 `alert_01`、`alert_02`、...
- `start_sec`: 数字，告警开始时间
- `end_sec`: 数字，告警结束时间，且必须满足 `end_sec > start_sec`
- `alert_type`: 字符串，只能是 `channel_swap`、`role_mismatch` 或 `cross_screen_speech`
- `audio_side_active`: 字符串，只能是 `left` 或 `right`
- `audio_speaker_role`: 字符串，只能是 `agent` 或 `customer`
- `left_face_visibility`: 字符串，只能是 `always_visible`、`partial` 或 `never_visible`
- `right_face_visibility`: 字符串，只能是 `always_visible`、`partial` 或 `never_visible`
- `left_mouth_state`: 字符串，只能是 `continuous_motion`、`intermittent_motion` 或 `no_motion`
- `right_mouth_state`: 字符串，只能是 `continuous_motion`、`intermittent_motion` 或 `no_motion`

请按下面的规则生成告警：

1. `audio_activity_windows.json` 和 `split_screen_observations.json` 都包含 `windows` 数组。你必须按 `window_id` 对齐同名 window；不要新增或删除 window。
2. 每个 window 的时间边界使用音频文件里的 `start_sec` 和 `end_sec`。
3. 先为每个 window 计算视觉说话状态：
   - 如果只有左侧 `mouth_moving = true`，视觉说话状态记为 `left_only`
   - 如果只有右侧 `mouth_moving = true`，视觉说话状态记为 `right_only`
   - 如果左右两侧都为 `true`，记为 `both`
   - 如果左右两侧都为 `false`，记为 `none`
4. 对每个 window，按下面顺序判断是否触发告警：
   - `channel_swap`: `audio_side_active` 为 `left` 且视觉说话状态为 `right_only`，或 `audio_side_active` 为 `right` 且视觉说话状态为 `left_only`
   - `role_mismatch`: 视觉说话状态刚好等于 `audio_side_active` 对应的一侧，并且 `audio_speaker_role` 不等于 `session_manifest.json` 中该侧的 `expected_role`
   - `cross_screen_speech`: 视觉说话状态为 `none` 或 `both`，并且音频激活那一侧的 `mouth_moving = false`
   - 其他情况不生成告警
5. 只保留触发告警的 windows，然后按时间顺序合并相邻告警。只有在以下条件同时满足时才允许合并：
   - 前后两个告警的 `alert_type` 相同
   - `audio_side_active` 相同
   - `audio_speaker_role` 相同
   - 后一个告警的开始时间减去前一个告警的结束时间，不大于 `session_manifest.json` 中的 `merge_gap_sec`
6. 合并后，告警的 `start_sec` 取第一段开始时间，`end_sec` 取最后一段结束时间。
7. 合并后四个聚合状态字段按该告警覆盖的所有 windows 汇总：
   - 对 `left_face_visibility` 和 `right_face_visibility`：
     - 全部为 `true` 时写 `always_visible`
     - 全部为 `false` 时写 `never_visible`
     - 其他情况写 `partial`
   - 对 `left_mouth_state` 和 `right_mouth_state`：
     - 全部为 `true` 时写 `continuous_motion`
     - 全部为 `false` 时写 `no_motion`
     - 其他情况写 `intermittent_motion`
8. 输出中的所有时间数值都保留到小数点后两位。

不要输出额外字段，也不要把未触发告警的正常 window 写进结果。
