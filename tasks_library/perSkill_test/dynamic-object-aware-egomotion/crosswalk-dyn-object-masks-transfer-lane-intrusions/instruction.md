给定车载视频 `/root/crosswalk_drive.mp4` 和 ROI 配置 `/root/ego_lane_roi.json`，请输出 `/root/crosswalk_intrusions.json`，表示动态目标侵入自车车道 ROI 的时间窗。

请按下面这套公开规则处理视频：

1. 读取视频原始帧率 `native_fps`，按 ROI 配置里的 `sample_fps` 做固定采样。
2. 第 `i` 个采样帧对应原视频帧 `round(i * native_fps / sample_fps)`；越界后停止。
3. 对每个采样帧（从第 1 个采样帧开始）提取动态前景：
   - 转灰度。
   - 用上一采样帧到当前采样帧的稀疏光流估计全局仿射运动；若匹配不足，则退化为恒等变换。
   - 将上一灰度帧和全 1 有效区域一起 warp 到当前帧坐标系。
   - 在有效区域上计算 `diff = abs(curr - warped_prev)`。
   - 在 `diff[valid]` 上计算阈值 `max(20, median + 3 * 1.4826 * MAD)`，其中 `MAD = median(abs(x - median))`。
   - 对二值结果先做 `3x3` 开运算，再做 `7x7` 闭运算。
   - 只保留面积至少 `max(400, round(0.002 * H * W))` 的连通域，得到该采样帧的动态前景掩码。
4. 第 0 个采样帧没有上一采样帧，动态前景视为全 0。
5. 对每个采样帧，把动态前景掩码与 ROI 求交；交集像素数大于等于 `intrusion_min_pixels` 时，该采样帧记为一次“侵入”。
6. 只把严格连续的侵入采样帧合并为一个时间窗。

`/root/ego_lane_roi.json` 的字段约定如下：

- `image_size`: `[H, W]`，视频采样帧分辨率。
- `polygon`: ROI 多边形顶点，按像素坐标给出。
- `sample_fps`: 采样帧率。
- `intrusion_min_pixels`: 某个采样帧内，只要动态前景与 ROI 的交集像素数大于等于这个阈值，就把该采样帧视为一次“侵入”。

输出文件 `/root/crosswalk_intrusions.json` 必须满足：

1. JSON 根对象包含：
   - `sample_fps`: 数值，必须与 ROI 配置里的 `sample_fps` 一致。
   - `windows`: 数组，按时间升序排列。
2. `windows` 中每个元素都是对象，且包含：
   - `start_frame`: 整数，表示一个侵入时间窗的起始采样帧索引（包含）。
   - `end_frame`: 整数，表示该时间窗的结束采样帧索引（不包含）。
3. 先按上面的采样规则对整段视频做固定采样，再基于每个采样帧上的动态前景与 ROI 的交集像素数判断该帧是否“侵入”。
4. 只合并严格连续的侵入采样帧；中间只要出现一个非侵入采样帧，就必须断开成两个时间窗。
5. 如果某一段连续侵入采样帧是 `[start_frame, end_frame)`，则 `windows` 里必须恰好输出一个对应时间窗，不能把这段连续区间拆成多个首尾相接的小窗口。
6. 所有时间窗都必须满足 `0 <= start_frame < end_frame`，并且彼此不重叠。

除了 `/root/crosswalk_intrusions.json` 之外，不要求输出其他文件。
