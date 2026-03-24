`/app` 里有一个 Next.js 视频会议预检大厅，首屏存在明显的视觉不稳定问题。请先定位根因，再用合适的 Next.js 与 React 实践修复这些体验问题，同时保留现有交互和测试选择器：

- 设备预览区在异步拿到会议信息后会突然变高，导致主区域明显下跳
- 网络提示条晚到后会把整个大厅内容向下推
- 参会者列表晚到后才插入右侧，导致主列横向收缩
- 权限状态卡片加载后会把底部的加入会议区域再次往下挤
- 摄像头和麦克风偏好从 `localStorage` 恢复时，在 hydration 前后会出现可见闪屏

完成修复后，把结果写入 `output/precall-lobby-stability-report.json`。这个 JSON 至少要覆盖以上 5 个问题，并为每项提供 `id`、`status` 和 `strategy` 字段。

## Rules

- 不要破坏现有功能
- 不要修改现有 class name、id 或 data-testid
