你需要分析一份混杂了多条明文 IRC 会话的抓包，并恢复真正恶意控制会话中的关键命令与响应。

输入文件固定为 `/workspace/inputs/irc_mix.pcap`。

请生成 `/workspace/outputs/irc_c2_transcript.txt`。输出必须是纯文本文件，每行一条记录，且严格使用下面的格式：

`YYYY-MM-DDTHH:MM:SSZ | direction | message`

其中：

- `direction` 只能是 `controller->bot` 或 `bot->controller`
- `message` 只保留 IRC 私聊消息里的正文，不要保留 nick、userhost、`PRIVMSG`、前导冒号或其他协议包装

只输出真正恶意控制流中的“关键命令与响应”，并满足以下要求：

- 仅保留控制端发给 bot 的私聊命令，以及 bot 回给控制端的对应执行结果
- 不要输出注册阶段流量、数值回复、`PING`/`PONG`、`JOIN`、普通聊天、其他机器人对话，或任何非恶意会话内容
- 各行必须按时间先后排序
- 不要添加标题、编号、空行或额外注释

抓包中存在多个 IRC TCP 会话，正常聊天流和自动化消息会混在一起；验证重点是你是否找对了真正的 C2 会话，并完整恢复其命令顺序。
