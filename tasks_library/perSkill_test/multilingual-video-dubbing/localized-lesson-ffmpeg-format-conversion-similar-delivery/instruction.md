你在 `/root` 会拿到两个输入文件：

- `lesson_clip.mp4`：原始教学短视频
- `aligned_narration.wav`：已经和画面节奏对齐好的本地化旁白

请输出最终交付文件 `/outputs/localized_lesson.mp4`，要求如下：

1. 保留原始视频画面，不要裁剪、缩放、加字幕、加水印，也不要改输出文件名。
2. 丢弃原视频自带音轨，改用 `aligned_narration.wav` 作为唯一音轨。
3. 成品必须是 MP4，视频编码为 H.264，音频编码为 AAC。
4. 成品音频必须是 `48000 Hz`、`单声道`。
5. 成品总时长应与原视频一致，只允许封装层面的极小误差。

除了 `/outputs/localized_lesson.mp4` 以外，不需要额外输出别的文件。
