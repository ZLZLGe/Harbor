你在 `/root` 会拿到一个播客预告母带文件：

- `podcast_preview_master.wav`

请把它发布成移动端预览音频 `/outputs/podcast_preview.opus`，要求如下：

1. 输出文件必须是 `Opus` 音频，文件名固定为 `/outputs/podcast_preview.opus`。
2. 输出采样率必须是 `48000 Hz`。
3. 输出必须保持 `双声道`，不要改成单声道。
4. 目标发布比特率为 `64 kb/s`。
5. 不要裁切、拼接或额外加工音频内容；成品时长应与输入基本一致。

除了 `/outputs/podcast_preview.opus` 之外，不需要额外输出别的文件。
