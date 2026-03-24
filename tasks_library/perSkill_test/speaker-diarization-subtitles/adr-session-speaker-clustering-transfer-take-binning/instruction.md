影视 ADR 会话的切分与嵌入已经准备好。输入文件 `/root/adr_session_takes.json` 给出了每个 take 的录制顺序、时间码、cue 信息以及声纹 embedding，并且已知本场 ADR 一共有固定数量的演员。

请完成以下目标：

1. 读取 `/root/adr_session_takes.json`，对全部 take 做全局分桶。
2. 严格按照输入中的 `actor_count` 产出固定数量的演员桶。
3. 将同一演员的 take 放进同一个 `actor_bin_id`，即使这些 take 分散在不同 cue、不同 pickup group。
4. 按输入中的命名规则生成稳定编号：`actor_bin_00`、`actor_bin_01` 这类编号必须按照每个桶里最早 `record_order` 的先后顺序分配。
5. 将结果写入 `/root/adr_take_bins.tsv`，供后期对轨使用。

输出文件必须是制表符分隔的 TSV，表头顺序必须完全等于：

`session_id	actor_bin_id	take_id	cue_id	slate	record_order	start_tc	end_tc	duration_sec	pickup_group	guide_track_ref	bin_take_index`

写出规则：

- 输出必须覆盖输入中的全部 take，且每个 take 恰好出现一次。
- 所有数据行必须按 `record_order` 升序排序。
- `bin_take_index` 表示该 take 在所属演员桶内按 `record_order` 排序后的 1-based 序号。
- `duration_sec` 统一保留两位小数。
- 除了表头和数据行，不要写任何额外说明、注释或空行。
