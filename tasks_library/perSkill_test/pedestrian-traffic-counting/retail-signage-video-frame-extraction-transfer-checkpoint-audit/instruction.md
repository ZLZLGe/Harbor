## 任务说明

`/app/input/checkpoint_requests.json` 是门店数字标牌素材的抽检清单，`/app/input/signage_archive/` 下是对应录像。请按清单逐条定位检查点，导出命中的 JPG，并生成一份审计 JSON 报告。

## 你需要产出

1. 在 `/app/output/checkpoint_audit_report.json` 写出 UTF-8 编码的 JSON 报告。
2. 在 `/app/output/checkpoint_frames/` 下写出所有命中请求对应的 JPG。

## 输入清单格式

`/app/input/checkpoint_requests.json` 顶层对象包含：

- `audit_id`
- `requests`

`requests` 数组中的每个对象都包含：

- `checkpoint_id`
- `store_code`
- `source_video`
- `timestamp_seconds`

其中 `source_video` 是相对 `/app/input/` 的路径，例如 `signage_archive/east/store_014/window_loop.mp4`。

## 定位与命中规则

- 按 `requests` 在输入文件中的原始顺序处理，并在输出报告里保留同样顺序。
- 对每个请求，先读取对应视频的实际 fps 和总帧数。
- 目标源帧号定义为 `floor(timestamp_seconds * fps)`。
- 当 `timestamp_seconds` 为非负数，且目标源帧号严格小于该视频总帧数时，该请求视为 `captured`。
- 其余情况都视为 `unreachable`。
- `captured` 请求必须导出 1 张 JPG；`unreachable` 请求不能导出图片。

## JPG 输出规则

- JPG 输出根目录固定为 `/app/output/checkpoint_frames/`。
- 每个命中请求的输出目录固定为 `/app/output/checkpoint_frames/<store_code>/`。
- 文件名固定为 `<checkpoint_id>__t<timestamp_ms>.jpg`。
- 其中 `timestamp_ms` 等于 `round(timestamp_seconds * 1000)` 后的十进制结果，并补零到 6 位。
  - 例如 `8.25` 秒对应 `008250`，文件名示例为 `cp_store014_midmorning__t008250.jpg`。
- `output_file` 字段必须写相对 `/app/output/` 的相对路径，例如 `checkpoint_frames/store_014/cp_store014_midmorning__t008250.jpg`。

## JSON 报告格式

顶层对象必须包含以下字段：

- `audit_id`
- `total_requests`
- `captured_count`
- `unreachable_count`
- `requests`
- `unreachable_checkpoints`

其中：

- `audit_id` 必须直接复制输入文件中的值。
- `total_requests` 等于输入请求总数。
- `captured_count` 等于状态为 `captured` 的请求数量。
- `unreachable_count` 等于状态为 `unreachable` 的请求数量。
- `unreachable_checkpoints` 必须是数组，按输入顺序列出所有 `unreachable` 请求的 `checkpoint_id`。

`requests` 数组中的每个对象必须包含以下字段：

- `checkpoint_id`
- `store_code`
- `source_video`
- `requested_timestamp_seconds`
- `status`
- `output_file`

其中：

- `requested_timestamp_seconds` 必须直接复用输入中的时间值。
- `status` 只能是 `captured` 或 `unreachable`。
- 当 `status` 为 `captured` 时，`output_file` 必须是对应 JPG 的相对路径字符串，且该文件必须真实存在。
- 当 `status` 为 `unreachable` 时，`output_file` 必须为 `null`。

## 其他要求

- 不要生成题目未要求的主输出文件路径。
- 所有报告中列出的 JPG 都必须是对应请求命中的那一帧。
