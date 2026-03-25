处理 `/root/tutorial_walkthrough.mp4`，输出一个供后期插入提示卡片或遮罩说明使用的无语音窗口清单 `/root/overlay_windows.csv`。

计算规则全部以 `/root/overlay_policy.json` 为准：

- `merge_gap_seconds`：如果两段讲解人声之间的间隔不超过这个值，把它们视为同一段连续讲解。
- `speech_guard_seconds`：对每段最终讲解区间的前后都额外留出这段保护时间，保护后不能越过时间轴边界。
- `timeline_duration_seconds`：计算补集时使用的完整时间轴长度。
- `min_window_seconds`：只保留时长不少于这个值的无语音窗口。
- `blocked_ranges`：列出已经被其他视觉元素占用、因此不能再放提示卡片的时间区间。

要求：

- 先定位视频里明显包含讲解人声的时间区间。
- 纯静音、房间底噪、键盘声、鼠标点击或其他非人声噪声都不应单独算作讲解区间。
- 按 `merge_gap_seconds` 合并相邻讲解区间，再按 `speech_guard_seconds` 扩展保护边界。
- 在 `[0, timeline_duration_seconds]` 这条时间轴上对保护后的讲解区间取补集，得到可插卡窗口。
- 再从这些窗口里扣除 `blocked_ranges` 中给出的禁用区间。
- 只输出满足 `min_window_seconds` 的窗口；过短空档不要输出。

`/root/overlay_windows.csv` 必须使用这个表头：

```csv
window_id,start,end,duration
overlay_01,1.784,5.226,3.442
overlay_02,12.670,16.782,4.112
```

补充约束：

- 所有时间单位都是秒，数值保留到 3 位小数以内即可。
- 行必须按 `start` 升序排列，窗口之间不能重叠。
- `window_id` 必须从 `overlay_01` 开始连续编号。
- 每行都必须满足 `duration = end - start`。
- 不要输出额外列、额外说明文字或第二个结果文件。

验收标准：

- 除了 CSV 结构和 `overlay_policy.json` 规则一致性检查外，验证还会把你输出的窗口按顺序与参考窗口做语义对齐比较。
- 你的窗口数量必须与参考答案完全一致。
- 所有输出窗口的 `duration` 总和与参考答案相比，绝对误差不得超过 `0.8` 秒。
- 对齐后的每个窗口都必须同时满足：
  - `start` 与参考窗口起点的绝对误差 `<= 0.45` 秒
  - `end` 与参考窗口终点的绝对误差 `<= 0.45` 秒
  - 相对参考窗口的覆盖率 `>= 0.88`
  - 与参考窗口的 IoU `>= 0.80`
