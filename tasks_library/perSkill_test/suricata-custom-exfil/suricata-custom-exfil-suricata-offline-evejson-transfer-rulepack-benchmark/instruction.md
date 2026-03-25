你在做一组 TLS 外传候选规则包的离线基准评测。

已提供输入资产：

- 带标签的样本目录：`/root/rulepack-benchmark/pcaps/`
- 标签文件：`/root/rulepack-benchmark/labels.json`
- 两套候选规则包目录：`/root/rulepack-benchmark/rulepacks/`
- Suricata 配置：`/root/rulepack-benchmark/suricata.yaml`

请生成 `answer/rulepack-benchmark.json`，并满足以下输出契约：

1. 顶层必须是 JSON 对象，且恰好包含键 `metric`、`winner`、`rulepacks`
2. `metric` 必须固定写为字符串 `f1`
3. `rulepacks` 必须是数组，覆盖 `/root/rulepack-benchmark/rulepacks/` 下所有 `.rules` 文件，并按规则包文件名字典序升序排列
4. `rulepacks` 中每个元素都必须是对象，且恰好包含以下字段：
   - `rulepack`：规则包文件名
   - `tp`：真阳性样本数
   - `fp`：假阳性样本数
   - `fn`：假阴性样本数
   - `precision`：按 `tp / (tp + fp)` 计算；若分母为 0，则写 `0.0`
   - `recall`：按 `tp / (tp + fn)` 计算；若分母为 0，则写 `0.0`
   - `f1`：按 `2 * precision * recall / (precision + recall)` 计算；若分母为 0，则写 `0.0`
   - `samples`：该规则包在全部样本上的逐样本评测明细
5. 对每个规则包，都需要分别对 `labels.json` 中列出的每个 PCAP 单独离线运行 Suricata；如果该样本对应的 `eve.json` 中存在至少一条 `event_type == "alert"` 的事件，则该样本的 `predicted` 记为 `exfil`，否则记为 `benign`
6. 每个规则包对象里的 `samples` 必须是数组，并且按 `pcap` 文件名字典序升序排列；每个元素都必须恰好包含以下字段：
   - `pcap`：PCAP 文件名
   - `label`：标签文件给出的真实标签，只能是 `exfil` 或 `benign`
   - `predicted`：按是否出现告警得出的预测标签，只能是 `exfil` 或 `benign`
   - `alert_count`：该样本在对应 `eve.json` 中的告警事件总数
   - `matched_sids`：该样本所有告警事件里的 `alert.signature_id` 去重后升序列表
7. `precision`、`recall` 和 `f1` 都必须是 JSON 数字，并四舍五入保留 6 位小数
8. `winner` 必须是优胜规则包的文件名；优先选择 `f1` 更高的规则包，若 `f1` 相同，则选择 `precision` 更高的；若仍相同，则选择 `fp` 更少的；如果还相同，则选择文件名字典序更小的

要求：

- 只提交 `answer/rulepack-benchmark.json`
- 不要修改输入资产
- 输出内容必须来自对两套候选规则包的实际离线回放结果，而不是手工猜测
