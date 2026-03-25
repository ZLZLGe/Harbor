你在复盘一段东区办公网的内网横向移动窗口。

已提供输入资产：

- 长 PCAP：`/root/lateral-timeline/ops-east-long.pcap`
- 现成规则集：`/root/lateral-timeline/lateral.rules`
- Suricata 配置：`/root/lateral-timeline/suricata.yaml`

请生成 `answer/lateral-timeline.csv`，并满足以下输出契约：

1. 文件必须是 UTF-8 编码的 CSV，第一行表头必须严格为 `timestamp,sid,src_ip,dest_ip,signature`
2. 先对给定 PCAP 做离线回放，再从产生的 `eve.json` 中只筛选 `event_type` 为 `alert` 且 `alert.signature` 以 `[first-wave] ` 开头的事件
3. 对每个不同的 `sid`，只保留整份 PCAP 中最早出现的那一条告警事件
4. 输出行必须按 `timestamp` 升序排列；如果时间戳相同，再按 `sid` 升序排列
5. 每一行都必须恰好包含这 5 列：
   - `timestamp`：直接使用对应告警事件在 `eve.json` 里的原始 `timestamp`
   - `sid`：对应 `alert.signature_id`
   - `src_ip`：对应事件的 `src_ip`
   - `dest_ip`：对应事件的 `dest_ip`
   - `signature`：对应 `alert.signature`

要求：

- 只提交 `answer/lateral-timeline.csv`
- 不要修改输入资产
- 输出应反映“首轮关键动作”的时间线，因此不能包含后续重复触发的同一 `sid`
