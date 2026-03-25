你会在容器里看到两个输入文件：

- `/root/warehouse_patrol.mp4`
- `/root/run_manifest.json`

任务目标：按 `run_manifest.json` 里给定的固定采样率，对这段仓库通道巡检视频做全局相机运动分析，并把压缩后的区间到标签映射写入 `/root/egomotion_segments.json`。

输出文件必须是一个 JSON 对象，键是半开区间 `"start->end"`，值是该区间对应的标签数组。例如：

```json
{
  "0->3": ["Stay"],
  "3->10": ["Dolly In"],
  "10->17": ["Dolly In", "Pan Right"]
}
```

要求：

- 只写一个结果文件：`/root/egomotion_segments.json`
- 使用 `run_manifest.json` 中的 `sample_fps`
- 标签只能来自这 9 个值：`Stay`、`Dolly In`、`Dolly Out`、`Pan Left`、`Pan Right`、`Tilt Up`、`Tilt Down`、`Roll Left`、`Roll Right`
- 同一个区间可以有多个标签
- 每个标签数组必须非空，且同一区间内不要重复标签
- 所有区间必须连续覆盖全部采样步，不能有重叠，也不能留空档
- 如果两个相邻区间的标签集合完全相同，必须合并成一个更长的区间

评测会检查：

- JSON 格式是否合法
- 区间是否连续、无重叠且已经压缩
- 展开到逐采样步后，运动标签时间线是否与视频内容一致；宏平均 F1 需要至少达到 `0.85`
