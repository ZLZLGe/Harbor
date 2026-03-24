# Workflow context

- 变更来源：PR #908 `align-service-analysis`
- 目标：把每个服务的静态检查拆到复用 workflow `.github/workflows/reusable-service-analysis.yml`
- 现象：`analyze-service` 的两个 matrix job 都在调用复用 workflow 之前失败，下游 `publish-analysis-summary` 没有执行
- 排查重点：caller workflow 与 reusable workflow 的 `workflow_call.inputs` 是否仍然保持同一份参数契约
