你会在容器内看到 4 个输入文件：

- `/root/conference_manifest.json`
- `/root/room_seat_map.csv`
- `/root/meeting_schedule.json`
- `/root/checkin_log.csv`

请基于这些输入生成两个结果文件。

1. `/root/room_state_timeline.json`
   - 根节点必须是 JSON object。
   - 顶层字段必须包含：
     - `room_id`：等于 manifest 里的 `room_id`
     - `seat_matrix_shape`：等于 manifest 里的 `seat_matrix_shape`
     - `seat_matrix_path`：固定写成 manifest 里的 `seat_matrix_path`
     - `timeline`：长度等于 `slot_count` 的数组
   - `timeline` 中每个元素都必须是 object，并且包含：
     - `slot_idx`：当前时隙编号，范围 `0..slot_count-1`
     - `window`：等于 manifest 里对应的 `slot_windows[slot_idx]`
     - `state`：只能从 manifest 的 `allowed_states` 里取值
     - `meeting_id`：当前时隙正在使用房间的会议 ID；若没有会议占用该时隙则写 `null`
     - `meeting_title`：若该时隙没有会议则写 `null`，否则等于排期里的 `title`
     - `occupied_count`：当前时隙被占用的座位数
     - `occupied_seat_ids`：当前时隙被占用的座位 ID 数组，按字典序升序排列
   - `meeting_schedule.json` 里的区间使用半开区间 `[start_slot, end_slot)`，并且同一时隙最多只会有一个会议。
   - `checkin_log.csv` 里的占座区间也使用半开区间 `[slot_start, slot_end)`；某个时隙里，只要 `slot_start <= slot_idx < slot_end`，该记录对应的 `seat_id` 就视为被占用。
   - 房间状态规则如下：
     - 若当前时隙没有会议：
       - `occupied_count == 0` 时，`state = "Vacant"`
       - `occupied_count > 0` 时，`state = "Reset"`
     - 若当前时隙存在会议，记该会议的保留座位数为 `reserved_seats`：
       - `occupied_count > reserved_seats` 时，`state = "Overflow"`
       - 否则，只要 `slot_idx == start_slot` 或 `occupied_count < reserved_seats`，`state = "Check-In"`
       - 其他情况，`state = "In Session"`

2. `/root/seat_usage_csr.npz`
   - 表示每个时隙的已占用座位矩阵，必须使用 CSR 稀疏格式。
   - 文件中必须包含：
     - `shape`: `[rows, cols]`
     - `slots`: `[0, 1, ..., slot_count-1]`
     - 对每个时隙 `i` 都要写出：
       - `slot_{i}_data`
       - `slot_{i}_indices`
       - `slot_{i}_indptr`
   - `shape` 必须等于 manifest 里的 `seat_matrix_shape`。
   - `room_seat_map.csv` 是座位矩阵；每个单元格要么是一个座位 ID，要么是 manifest 的 `empty_seat_token`。
   - 对于每个时隙 `i`，dense 矩阵中凡是对应 `occupied_seat_ids` 的座位位置都应为 1/True，其余位置都应为 0/False。
   - `empty_seat_token` 所在的走道/空白单元永远不能被标为占用。
   - 即使某个时隙没有任何座位被占用，也必须写出合法的空 CSR。

只需要交付这两个结果文件。测试会检查 JSON 结构、时隙状态语义、座位 ID 与矩阵映射关系，以及 CSR 结构是否正确。
