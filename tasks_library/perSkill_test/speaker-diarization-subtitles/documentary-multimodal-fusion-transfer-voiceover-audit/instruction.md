你会拿到一组已经从纪录片片段中抽取好的证据文件：

- `/root/speech_events.json`
- `/root/shot_observations.json`
- `/root/clip_manifest.json`

请基于这些输入生成 `/root/narration_audit.json`。

输出文件必须是一个 JSON 数组，并按 `start_sec` 升序排列。数组中的每个元素都必须对应 `speech_events.json` 中的一个语音事件，并包含以下字段：

- `event_id`: 字符串，且必须来自 `speech_events.json`
- `start_sec`: 数字，必须等于该事件的开始时间
- `end_sec`: 数字，必须等于该事件的结束时间
- `label`: 字符串，只能是 `on_camera_speech`、`off_camera_voiceover` 或 `ambiguous`
- `visible_face_count`: 整数，表示与该事件重叠的所有 shot observation 中，`visible_face_ids` 的最大数量
- `mouth_motion_evidence`: 字符串，只能是 `aligned_lip_motion`、`no_visible_faces`、`visible_faces_without_lip_motion` 或 `mixed_visual_signal`

请按下面的规则判定每个事件：

1. 只审计 `speech_events.json` 中给出的语音事件，不要新增或删除事件。
2. 对每个事件，收集 `shot_observations.json` 中所有与它有时间重叠的 observation，并按重叠时长累计证据。
3. 定义三个时长：
   - `aligned_motion_sec`: 重叠部分里，`lip_motion_face_ids` 非空的总时长
   - `no_face_sec`: 重叠部分里，`visible_face_ids` 为空的总时长
   - `visible_no_motion_sec`: 重叠部分里，`visible_face_ids` 非空但 `lip_motion_face_ids` 为空的总时长
4. 分类规则：
   - 如果 `aligned_motion_sec / 事件时长 >= 0.6`，标记为 `on_camera_speech`
   - 否则，如果 `no_face_sec / 事件时长 >= 0.6` 且 `aligned_motion_sec == 0`，标记为 `off_camera_voiceover`
   - 其他情况都标记为 `ambiguous`
5. `mouth_motion_evidence` 规则：
   - `on_camera_speech` 必须写 `aligned_lip_motion`
   - `off_camera_voiceover` 必须写 `no_visible_faces`
   - 对 `ambiguous`：
     - 如果 `aligned_motion_sec > 0`，或者同时存在 `no_face_sec > 0` 和 `visible_no_motion_sec > 0`，写 `mixed_visual_signal`
     - 否则写 `visible_faces_without_lip_motion`
6. 最终结果中每个事件都必须满足 `start_sec < end_sec`，并且不得与别的事件重复 `event_id`。
