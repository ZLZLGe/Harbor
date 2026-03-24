值班 SRE 把本轮故障切换实例整理在 `/app/recovery_manifest.json` 中。每个条目都包含：

- `id`：集群恢复实例编号
- `domain`：PDDL 域文件路径
- `problem`：PDDL 问题文件路径
- `plan_output`：该实例对应的输出计划文件路径
- `cluster`：集群名
- `gateway`：需要切换的入口网关
- `standby_site`：承接流量的备用机房
- `failed_site`：当前失效机房
- `core_service`：需要先恢复的核心服务
- `edge_service`：依赖核心服务的边缘入口服务
- `replicas`：切换完成后需要重建的副本列表

你需要读取 `recovery_manifest.json` 中列出的全部实例，并为每个集群生成一份合法的顺序恢复计划，逐个写入各自的 `plan_output` 路径。

要求：

- 每个输出文件都必须存在，不能遗漏任何实例。
- 计划必须符合对应 PDDL 域与问题文件中的动作定义和对象命名。
- 恢复顺序必须体现先恢复链路、再提升主节点、再恢复核心与边缘服务、随后切换流量、最后重建副本。
- 计划文件中每行只能有一个动作。
- 如有需要，请自行创建输出目录。

例如，`recovery_plans/cluster_a_recovery.txt` 必须是其中一个生成出来的计划文件。
