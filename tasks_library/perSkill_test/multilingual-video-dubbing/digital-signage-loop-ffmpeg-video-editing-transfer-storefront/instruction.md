你会拿到四段门店商品展示短视频和一份排播清单：

- `/root/espresso_hero.mp4`
- `/root/pastry_vertical.mp4`
- `/root/loyalty_square.mp4`
- `/root/evening_special.mp4`
- `/root/storefront_plan.json`

请把这些素材整理成一条门店橱窗屏幕循环播放片。

交付物：

1. `/outputs/storefront_loop.mp4`
   - 必须按照 `storefront_plan.json` 中 `clips` 的顺序拼接。
   - 输出视频必须统一为 `1280x720`、`30 fps`、H.264 视频编码、AAC 音频编码、`48000 Hz`、单声道。
   - 画面需要铺满 `16:9` 画布，使用居中裁切，不要留黑边。
   - 如果某段素材长于清单里的目标时长，只保留开头到目标时长为止。
   - 如果某段素材短于目标时长，画面要冻结最后一帧补足时长，音频末尾补静音。
   - 最终总时长应接近所有目标时长之和。

不要输出额外说明文件。只需要准备好 `/outputs/storefront_loop.mp4`。
