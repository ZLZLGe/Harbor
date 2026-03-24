给定两个已经整理好的港口雷达输入文件：

- `/root/harbor_radar_sweeps.json`
- `/root/harbor_echo_components.json`

请输出下面两个结果文件：

1. `/root/pred_harbor_tracks.json`
   记录相邻采样扫描区间到船舶整体机动标签的映射。合法标签仅限：
   `锚泊待命`、`沿航道驶入`、`沿航道驶离`、`右舷转向`、`左舷回转`。

   输出格式示例：
   ```json
   {
     "0->2": ["锚泊待命"],
     "2->5": ["沿航道驶入"]
   }
   ```

   这里的 `start` 和 `end` 是采样扫描之间的区间编号，而不是原始时间戳。若一共提供了 `N` 次采样扫描，则这些区间必须按顺序连续覆盖从 `0` 到 `N - 1` 之前的全部相邻扫描区间，不能有缺口，也不能重叠。

2. `/root/pred_harbor_echo_masks.npz`
   为每次采样扫描输出一个活动目标回波区域的二值 mask，并使用 CSR 稀疏格式保存。要求：
   - 全局分辨率写在键 `shape` 中，格式为 `[H, W]`
   - 对每个采样扫描 `i`，分别写入 `f_{i}_data`、`f_{i}_indices`、`f_{i}_indptr`

补充说明：

- `harbor_radar_sweeps.json` 给出了采样扫描顺序、允许标签以及已经整理好的机动分段。
- `harbor_echo_components.json` 给出了每次扫描中的矩形回波组件；请只把 `active = true` 的组件并入输出 mask。
- 静态结构回波不要写入输出。
- 重点是保证区间命名、扫描覆盖范围以及 CSR 稀疏存储结构都正确且可校验。
