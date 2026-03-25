给定视频 `/root/goalmouth_pan.y4m` 和配置文件 `/root/goalmouth_roi.json`，请使用环境中提供的动态目标掩码能力，在按 `sample_fps` 采样后的帧上生成动态目标二值掩码，再输出 `/root/goalmouth_occupancy.csv`，表示每个采样帧内动态目标对球门区域的遮挡比例时间序列。

`/root/goalmouth_roi.json` 的字段约定如下：

- `image_size`: `[H, W]`，视频采样帧分辨率。
- `polygon`: 球门区域多边形顶点，按像素坐标给出。
- `sample_fps`: 固定采样帧率。

输出文件 `/root/goalmouth_occupancy.csv` 必须满足：

1. 使用 UTF-8 编码，首行表头必须严格为：
   `sample_index,timestamp_sec,goal_pixels,occluded_pixels,occlusion_ratio`
2. 先按 `sample_fps` 对整段视频做固定采样，覆盖完整视频时长；CSV 必须对每个采样帧各输出一行，且 `sample_index` 从 `0` 开始连续递增。
3. `timestamp_sec` 必须等于 `sample_index / sample_fps`。
4. `goal_pixels` 必须是给定多边形栅格化后的像素数，并且在所有行中保持一致。
5. `occluded_pixels` 表示当前采样帧内，同时属于球门多边形和动态前景的像素数，必须是 `0` 到 `goal_pixels` 之间的整数。
6. `occlusion_ratio` 必须等于 `occluded_pixels / goal_pixels`，取值范围为 `[0, 1]`。
7. 行顺序必须按 `sample_index` 升序排列，不要求输出其他文件。
8. verifier 会从同一视频与 ROI 直接估计一条动态遮挡参考时间序列做比对；你的 CSV 还必须同时满足以下误差上限：
   - `occlusion_ratio` 相对参考序列的平均绝对误差 `<= 0.08`
   - `occlusion_ratio` 相对参考序列的最大绝对误差 `<= 0.18`
   - `occluded_pixels` 相对参考序列的平均绝对误差 `<= 260`
   - 全序列 `occluded_pixels` 总和相对参考总和的误差 `<= 0.25`
