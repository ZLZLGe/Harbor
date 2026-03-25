你会拿到一组已经提取好的圆桌访谈证据文件：

- `/root/audio_turn_candidates.json`
- `/root/visual_windows.json`
- `/root/cluster_face_affinity.json`
- `/root/speaker_roster.json`

请基于这些输入生成 `/root/speaker_timeline.json`。

输出文件必须是一个 JSON 数组，并按 `start_sec` 升序排列。数组中的每个元素都必须包含以下字段：

- `speaker_id`: 字符串，且必须来自 `speaker_roster.json`
- `start_sec`: 数字
- `end_sec`: 数字
- `visible_face_count`: 整数
- `lip_motion_confirmed`: 布尔值
- `visual_confidence`: 字符串，只能是 `high`、`medium` 或 `low`

请满足这些结果约束：

1. 只覆盖 `audio_turn_candidates.json` 中给出的有声区间，不要新增静音片段。
2. 对 `split_by_visual = true` 的候选段，如果它跨越了多个 visual window，且这些窗口里的 `active_face_id` 发生变化，就按这些窗口边界拆分。
3. 对未拆分的候选段，`speaker_id` 使用该段 `audio_cluster` 在 `cluster_face_affinity.json` 中分数最高的说话人。
4. 对拆分后的子段，如果该子段对应的 visual window 里存在 `active_face_id`，则该子段的 `speaker_id` 直接使用这个 `active_face_id`；如果该窗口没有 `active_face_id`，再回退到该段 `audio_cluster` 的最高分说话人。
5. `visible_face_count` 取覆盖该片段中点的 visual window 里的 `visible_face_ids` 数量。
6. `lip_motion_confirmed` 在片段中点所在窗口中，只有当 `active_face_id == speaker_id` 时才为 `true`，否则为 `false`。
7. `visual_confidence` 规则如下：
   - `high`: `speaker_id == active_face_id`
   - `medium`: `speaker_id` 出现在 `visible_face_ids` 中，但 `lip_motion_confirmed` 为 `false`
   - `low`: `speaker_id` 不在 `visible_face_ids` 中
8. 最终片段不能重叠，且每个片段都必须满足 `start_sec < end_sec`。
