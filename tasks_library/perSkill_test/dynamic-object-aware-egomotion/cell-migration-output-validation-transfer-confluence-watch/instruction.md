给定同一段细胞单层愈合实验导出的两个预处理文件：

- `/root/cell_migration_observations.json`
- `/root/cell_migration_dense_masks.npz`

请整理并输出下面两个结果文件：

1. `/root/pred_cell_activity.json`
   记录细胞群体状态区间到标签的映射。合法标签仅限：
   `静止扩张`、`定向迁移`、`快速汇合`。

   输出格式示例：
   ```json
   {
     "0->2": ["静止扩张"],
     "2->5": ["定向迁移"]
   }
   ```

   这里的 `start` 和 `end` 都是按采样时刻编号定义的相邻区间索引。如果一共提供了 `N` 个采样帧，那么这些区间必须按顺序连续覆盖全部相邻采样区间，也就是从 `0` 一直覆盖到 `N - 1` 之前，不要出现缺口或重叠。

2. `/root/pred_cell_activity_masks.npz`
   为每个采样帧输出一个活跃迁移区域二值 mask，并使用 CSR 稀疏格式保存。要求：
   - 全局分辨率写在键 `shape` 中，格式为 `[H, W]`
   - 对每个采样帧 `i`，分别写入 `f_{i}_data`、`f_{i}_indices`、`f_{i}_indptr`

补充说明：

- `cell_migration_observations.json` 已经按采样顺序给出时序统计摘要和状态分段信息。
- `cell_migration_dense_masks.npz` 按 `frame_0`、`frame_1` 这样的键保存了每个采样帧的 dense 二值活跃区域。
- 不需要重新做图像分割；重点是保证时间索引、标签集合和 CSR 存储结构都正确、连续并且可以本地校验。
