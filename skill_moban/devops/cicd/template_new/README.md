# CI/CD 模板任务说明

本模板面向 `cicd` 类任务，目标是构造一个更像真实 release engineering 值班现场的模板：solver 需要修复一条 GitHub Actions 风格的多阶段发布 dry-run，让它在保留真实 broker 链路和阶段约束的前提下重新产出可交付的 release bundle。

## 📌 任务元数据

- 任务名：`github-actions-release-bundle-dryrun-repair`
- 类别：`cicd`
- 难度：`hard`
- 绑定 Skill：`github-actions-release-audit`
- SkillsMP 相关方向：`github-actions-templates`、`deployment-pipeline-design`、`gitlab-ci-patterns`

## 📊 验证与测试指标（Oracle & Verifier）

e2b oracle 结果：

- 整体结论：✅ 通过（Reward: `1.0`）
- 测试用例：`7/7` 通过
- 有效样本：`cicd-template-oracle-20260421e1 / template_new__Y3K5UJg`

Verifier 策略：

- 主测：验证 `release-bundle.json`、`promotion-plan.json`、`release-summary.md` 都来自 live broker，且 bundle、provenance、promotion plan 的行为结果一致。
- 防作弊：验证隐藏 broker 与冻结数据未被修改；验证输出没有退回 `fallback_snapshot`；验证 workflow 仍保留 `inspect -> package -> attest -> promote` 的阶段语义，且 `promote` 仅依赖 `attest`。

数据质量：

- 下游 broker 使用冻结的 release snapshot，字段风格参考公开 GitHub release 资产与 release engineering 常见元数据，覆盖 `repo`、`version`、`git_sha`、`artifact_name`、`digest`、`promotion_targets`、`requires_attestation` 等真实字段。
- 数据来源风格主要参考 `cli/cli` 与 `helm/helm` 的公开 release 资产命名与发布元数据表达；评测时使用仓内冻结快照，不在线抓取，保证确定性与可测性。
- 环境保留真实风格链路：workflow -> scripts -> hidden broker -> bundle/provenance/promotion plan，而不是静态 JSON puzzle。

多模态：

- 不适用（纯 CI/CD / 文件与本地服务运行时任务）。

## ⚡ Skill 相关性评估

结论：强相关。这个任务里，skill 的价值不在“帮忙写修复代码”，而在于把三类关键探针标准化了：

- workflow graph 探针会直接暴露 `promote` 是否还保留了多余依赖。
- dry-run replay 探针会先把 broken ordering 的失败现场跑出来，再驱动修复后的回归验证。
- contract check 探针会把 live broker contract 和正式输出做对照，避免 solver 只修到“表面结果能过一部分测试”。

基于最近 `3` 次有效对比实验（均为真正进入 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0/3` (`0%`) | `3/3` (`100%`) | With Skill 3 次全部通过；Without Skill 3 次全部保留 verifier 失败 |
| 总耗时 | `369.2s` | `281.6s` | With Skill 更快，平均总耗时降低约 `23.7%` |
| Agent 执行耗时 | `247.2s` | `189.7s` | With Skill 的诊断与收敛更快，平均 Agent 耗时降低约 `23.3%` |
| Input Tokens | `441,657.0` | `383,228.7` | Without Skill 的上下文与试错开销约为 With Skill 的 `1.15x` |

最近 3 次有效样本：

- With Skill：
  - `cicd-template-with-skill-20260421e1 / task_with_skills_e2b__rzxfX4P` -> `1.0`
  - `cicd-template-with-skill-20260421e2 / task_with_skills_e2b__qohJF3L` -> `1.0`
  - `cicd-template-with-skill-20260421e3 / task_with_skills_e2b__qyrkb4o` -> `1.0`
- Without Skill：
  - `cicd-template-without-skill-20260421e1 / task_without_skills_e2b__5Z7twBV` -> `0.0`
  - `cicd-template-without-skill-20260421e2 / task_without_skills_e2b__J6pRFq2` -> `0.0`
  - `cicd-template-without-skill-20260421e3 / task_without_skills_e2b__K48CJ7Z` -> `0.0`

失败轨迹摘要：

- Without Skill 的 3 次失败都修到了 live broker 行为结果，但稳定停在同一个 guardrail：`promote.needs` 被保留成 `['package', 'attest']`，而不是严格的 `['attest']`。
- With Skill 的 3 次通过都先使用了 `/opt/task-skills/github-actions-release-audit/` 下的 probe 脚本检查 workflow graph、replay 和 contract，再落正式修复。

## 📁 标准目录结构说明

```text
.
├── instruction.md
├── task.toml
├── PLAN.json
├── environment/
│   ├── Dockerfile
│   ├── workspace/
│   ├── release-broker/
│   └── skills/
├── tests/
└── solution/
```
