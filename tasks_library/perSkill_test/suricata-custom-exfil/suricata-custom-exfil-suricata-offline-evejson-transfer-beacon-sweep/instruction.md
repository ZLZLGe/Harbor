你需要对一批 HTTP beacon 样本做离线归类。

已提供输入资产：

- 样本 PCAP 目录：`/root/beacon-sweep/pcaps/`
- 现成规则集：`/root/beacon-sweep/beacon.rules`
- Suricata 配置：`/root/beacon-sweep/suricata.yaml`

请生成 `answer/beacon-sweep.json`，并满足以下输出契约：

1. 顶层是一个 JSON 对象，且包含键 `samples`
2. `samples` 是数组，必须覆盖 `/root/beacon-sweep/pcaps/` 下所有 `.pcap` 文件，且按文件名字典序升序排列
3. `samples` 中每个元素都必须是对象，并且恰好包含以下字段：
   - `pcap`：PCAP 文件名
   - `matched_sids`：该样本在离线回放后所有告警事件里的 `signature_id` 去重后升序列表
   - `alert_count`：该样本告警事件总数
   - `classification`：当 `alert_count` 大于 0 时写 `infected`，否则写 `clean`

要求：

- 需要逐个样本离线运行 Suricata，再基于对应 `eve.json` 统计结果
- 不要修改输入资产
- 只提交 `answer/beacon-sweep.json`
