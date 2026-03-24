你在排查一批离线采集的 SMTP 投递会话。

请编写 Suricata 规则，只在以下条件全部同时满足时告警：

1. 邮件投递目标收件人是 `dropbox@shadow.example`
2. 邮件主题严格为 `Quarterly Archive`
3. 邮件正文中存在一个 MIME 附件段，且该附件段包含 `Content-Transfer-Encoding: base64`
4. 这个附件的文件名匹配 `finance-YYYYMM.zip`

普通正文提到相同文件名、错误收件人、错误主题、非 Base64 编码附件、或文件名不匹配的邮件都不应误报。

容器里已经提供：

- PCAP：`/root/pcaps/`
- Suricata 配置：`/root/suricata.yaml`
- 待编辑规则文件：`/root/smtp_finance_drop.rules`

请更新 `/root/smtp_finance_drop.rules`，让 Suricata 对真实命中流量产生 `sid:2305001` 告警，并尽量避免误报。
