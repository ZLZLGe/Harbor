客服质检团队已经完成了上游切分与嵌入提取。输入文件 `/root/call_center_segments.json` 里包含 6 通客服电话、每通电话的短话轮片段，以及每个片段对应的声纹 embedding。你的任务是跨通话聚类这些片段，建立重复出现声线的稳定台账。

请完成以下目标：

1. 读取 `/root/call_center_segments.json`，对全部片段做全局聚类。
2. 将同一声线的片段分到同一个 cluster，即使它们来自不同通话。
3. 根据输入里的 `speaker_type_rule` 判断每个 cluster 是 `agent` 还是 `caller`。
4. 严格按照输入里的 `cluster_id_rule` 给 cluster 命名为 `cluster_00`、`cluster_01` 这类稳定编号。
5. 将结果写入 `/root/agent_voice_roster.json`。

输出 JSON 至少必须包含以下顶层字段：

- `dataset_id`
- `distance_threshold`
- `clusters`
- `agent_roster`
- `caller_roster`
- `segment_assignments`

其中：

- `clusters` 中的每个元素至少要包含 `cluster_id`、`speaker_type`、`distinct_call_count`、`call_ids`、`segment_count`、`segment_ids`。
- `agent_roster` 和 `caller_roster` 都应是簇摘要列表，每个元素至少包含 `cluster_id`、`call_ids`、`segment_count`。
- `segment_assignments` 需要覆盖输入中的全部片段，并至少包含 `call_id`、`segment_id`、`cluster_id`、`speaker_type`。

额外要求：

- `distance_threshold` 必须是本次聚类实际使用的数值阈值，且应满足 `0 < distance_threshold < 1`。
- `segment_assignments` 必须按 `call_id` 再按 `segment_index` 对应的顺序输出。
- `call_ids` 与 `segment_ids` 请保持去重后升序。
- `distinct_call_count` 必须等于该 cluster 覆盖的不同 `call_id` 数量。
- 最终 `agent_roster` 与 `caller_roster` 应与 `clusters` 中的 `speaker_type` 保持一致。
- `agent_roster` 与 `caller_roster` 都必须按 `cluster_id` 升序输出。
