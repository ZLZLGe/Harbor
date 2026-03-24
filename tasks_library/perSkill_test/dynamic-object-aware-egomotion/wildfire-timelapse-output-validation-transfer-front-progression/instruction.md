给定两个已经整理好的野火遥感输入文件：

- `/root/wildfire_sampling_manifest.csv`
- `/root/wildfire_fireline_runs.json`

请输出下面两个结果文件：

1. `/root/pred_fire_progression.json`
   记录相邻采样时刻区间到火势阶段标签的映射。合法标签仅限：
   `初始点火`、`顺风扩展`、`峡谷跃进`、`侧翼回燃`。

   输出格式示例：
   ```json
   {
     "0->1": ["初始点火"],
     "1->3": ["顺风扩展"]
   }
   ```

   这里的 `start` 和 `end` 都是按采样时刻编号定义的相邻区间索引。如果一共给出 `N` 个采样时刻，那么这些区间必须按顺序连续覆盖从 `0` 到 `N - 1` 之前的全部相邻采样区间，不能有缺口，也不能重叠。

2. `/root/pred_fireline_masks.npz`
   为每个采样时刻输出一个活跃火线区域二值 mask，并使用 CSR 稀疏格式保存。要求：
   - 全局分辨率写在键 `shape` 中，格式为 `[H, W]`
   - 对每个采样时刻 `i`，分别写入 `f_{i}_data`、`f_{i}_indices`、`f_{i}_indptr`

补充说明：

- `wildfire_sampling_manifest.csv` 按采样顺序给出观测时间、对应下一相邻时段的阶段标签以及少量辅助字段。最后一个采样时刻的 `phase_to_next` 会留空，因为它后面没有新的相邻区间。
- `wildfire_fireline_runs.json` 给出了每个采样时刻的活跃火线行段；`col_ranges` 使用 `[start, end)` 半开区间表示列范围。请把这些行段栅格化成输出 mask。
- 不需要重新做火场检测；重点是保证区间合并、标签值域、mask 帧数和 CSR 存储结构都正确，并在提交前先完成本地一致性检查。
