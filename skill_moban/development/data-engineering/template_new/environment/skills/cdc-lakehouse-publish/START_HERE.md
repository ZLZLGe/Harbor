# Marketplace Snapshot Skill Quickstart

优先走这条最短路径：

1. 先运行：

```bash
python3 /opt/task-skills/cdc-lakehouse-publish/validate_marketplace_snapshot.py
```

2. 重点看 `synthetic_edge`。如果 `main.accepted = true` 但 `synthetic_edge.accepted = false`，继续运行：

```bash
probe_marketplace_snapshot
```

3. 修完后再次运行 validator；只有当 `main` 和 `synthetic_edge` 都通过时，再执行正式 publish：

```bash
submit_marketplace_bundle
```

不要手写 bundle 或 receipt。
