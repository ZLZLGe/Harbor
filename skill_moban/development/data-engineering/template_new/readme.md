## 📌 任务元数据

- 任务 ID：`marketplace-cdc-publish-bundle`
- 任务名称：`Marketplace CDC Publish Bundle`
- 任务类别：`data-engineering`
- 任务目标：在单容器环境中，基于冻结的 marketplace 订单 CDC、履约事件、退款流水、卖家 SLA 配置和商品维表，真实构建 `warehouse.duckdb`、生成 manifest 驱动的 publish bundle，并通过本地 live audit 服务拿到正式 receipt。
- 官方输出：
  - `/app/output/warehouse.duckdb`
  - `/app/output/publish_bundle.json`
  - `/app/output/publish_receipt.json`
- 绑定 Skill：`cdc-lakehouse-publish`
- 对照口径：`with_skill` 与 `without_skill` 的唯一区别只来自 `environment/skills/` 及其对应 runtime 复制逻辑；题面、测试、数据、依赖和 verifier 完全一致。

任务形态对齐 SkillsMP `data-engineering` 分类里更高相关、也更稳定的热门方向：`implementing-warehouse-sources`、`projection-patterns`、`dbt-transformation-patterns`、`data-quality-frameworks`、`clickhouse-io`、`airflow-dag-patterns` 这一簇。它不是 toy ETL 题，也不是隐藏答案 puzzle，而是一个更像真实值班现场的“冻结 feed -> warehouse -> publish audit”交付任务。

## 📊 验证与测试指标（Oracle & Verifier）

e2b Oracle 结果：

- 整体结论：✅ 通过（Reward: `1.0`）
- Job：`marketplace-oracle-hardened-fix-20260422_013500`
- Trial：`task_with_skills_e2b__24XNkES`
- Task checksum：`8f79bc0ac5fc2ad9611f42cabde41dd5c828fc04bdd7e54ba7d2b8145eb8c78b`
- 测试用例：`8/8` 通过

Verifier 策略：

- 主测：验证正式输出文件存在、两张 mart 的字段与粒度契约、live manifest -> live publish 链路、bundle replay、替代 fixture 泛化、以及输入乱序后的稳定性。
- 防作弊：校验隐藏 audit 服务 launcher + 二进制哈希不变、冻结输入仍存在且未被绕过、正式 receipt 必须与 live publish 请求哈希一致，禁止手写 receipt / bundle 伪造通过。
- 行为约束：verifier 只看行为结果，不绑定唯一实现；只要 solver 在真实 CDC、金额归一化、UTC 口径、SLA 判定和 publish 契约上做对，就允许不同修复路径通过。

数据质量：

- 数据结构：任务使用冻结的 marketplace 风格 CDC 与事实流，而不是静态 CSV puzzle。输入同时覆盖晚到重放、同业务键多版本、金额字段迁移、跨时区事件、退款多流水、以及履约事件聚合。
- 真实链路：环境内保留真实风格下游服务，solver 必须先取 live manifest，再提交 live publish，最终由 audit 服务返回 receipt。
- 确定性：主数据、替代 fixture、隐藏 audit 契约与 verifier 均为仓内冻结版本；评测不依赖在线抓取，保证可复现和可测。

数据来源：

- 数据内容为仓内冻结的 marketplace-like 运营数据集，用于模拟真实 CDC / warehouse / publish 工作流，不在评测时在线抓取外部网站。
- 字段风格与任务设计参考公开常见数据工程实践，而不是复刻某一个具体公开数据集。

多模态：

- 不适用（纯数据工程 / 本地服务运行时任务）。

## ⚡ Skill 相关性评估

结论：强相关，而且在最终 hardening 版上已经重新恢复到我们希望的 task contrast：同一版 checksum 下，`oracle=1.0`、`with_skill=1.0`、`without_skill=0.0`。

这个任务里，Skill 的核心价值不是直接给出修复答案，而是把最关键的诊断路径标准化：

- 用 `probe_marketplace_snapshot.py` 暴露 replay-safe latest-version、金额字段漂移和 UTC/SLA 翻转这三类高信号问题。
- 用 `validate_marketplace_snapshot.py` 把“主数据行为正确”与“合成边界样本下 publish 仍失败”区分开，避免 solver 只修表结构不修 publish 语义。
- 用 `submit_marketplace_bundle.py` 把 live manifest、canonical `row_count` / `sha256` 和正式 receipt 的链路固化下来，减少“表算对了但 publish 还是挂”的试错成本。

最终版在实验中还额外做了一次必要的 hardening：早期版本曾暴露可直接反编译的隐藏 audit `server.pyc`，导致一条 `without_skill` 轨迹通过逆向隐藏服务逻辑而意外全过。最终版把隐藏服务改成 `server.pyc` 薄启动壳 + `server.bin` 内嵌实现，并用 guardrail 固定二进制哈希；随后又把 with-skill helper 的暴露条件收紧到稳定的 `/opt/task-skills/...` 路径，恢复了 `with_skill` 的可发现性。

基于最近 `3` 次有效 `with_skill` trial 与最近 `3` 次有效 `without_skill` trial（均为真实 task-level 运行，存在完整 agent 轨迹；已排除 `BuildException`、`ConnectError` 这类启动失败样本。样本跨越“可见性修复 -> 隐藏服务 hardening -> helper 暴露修复”三个稳定收敛阶段，但题面、数据、tests 与 skill 绑定关系保持一致）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0/3 = 0%` | `3/3 = 100%` | With Skill 已出现稳定通过；Without Skill 最近 3 次有效样本均未通过 |
| 平均总耗时 | `823.8s` | `774.4s` | With Skill 更快，平均总耗时降低约 `6.0%` |
| 平均 Agent 执行耗时 | `715.2s` | `672.2s` | With Skill 的诊断与收敛更快，平均 Agent 耗时降低约 `6.0%` |
| 平均 Input Tokens | `2.57M` | `2.15M` | Without Skill 的上下文与试错开销约为 With Skill 的 `1.19x` |

最近有效样本：

- With Skill：
  - `marketplace-with-visible-b-20260422_000459 / task_with_skills_e2b__Nb6VCML` -> `1.0`
  - `marketplace-with-final-20260422_003700 / task_with_skills_e2b__qohqdqX` -> `1.0`
  - `marketplace-with-hardened-fix-20260422_012200 / task_with_skills_e2b__ipzswJJ` -> `1.0`
- Without Skill：
  - `marketplace-without-visible-c-20260422_000934 / task_without_skills_e2b__ioesVE6` -> `0.0`
  - `marketplace-without-hardened-20260422_010500 / task_without_skills_e2b__5c6PreG` -> `0.0`
  - `marketplace-without-hardened-fix-20260422_013500 / task_without_skills_e2b__8nRDYwo` -> `0.0`

失败模式归纳：

- 早一阶段的 `without_skill` 失败主要卡在 `test_d_alternate_fixture_builds_and_publishes`，即主数据 publish 可以通过，但替代 fixture 的 live publish 返回 `400`。
- 最终 hardening 版的 `without_skill` 更早暴露出收敛失败：agent 没能稳定闭合 live manifest / publish 链，最终缺失 `publish_bundle.json` 与 `publish_receipt.json`，因此在主测上保留多项失败。
- 当前最终版的 `with_skill` 成功样本明确读取并执行了 `/root/.codex/skills/cdc-lakehouse-publish/` 与 `/opt/task-skills/cdc-lakehouse-publish/` 下的 `START_HERE.md`、`validate_marketplace_snapshot.py`、`probe_marketplace_snapshot.py` 等脚本，再回到 workspace 代码收敛，说明 skill 诊断脚本确实进入了 agent 工作流。

## 📁 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── readme.md
├── environment/
│   ├── Dockerfile
│   ├── audit-service/
│   ├── workspace/
│   └── skills/
│       └── cdc-lakehouse-publish/
├── tests/
│   ├── conftest.py
│   ├── test_outputs.py
│   ├── test_guardrails.py
│   ├── test.sh
│   └── fixtures_alt/
└── solution/
    ├── fixed/
    └── solve.sh
```

说明：

- `environment/` 采用单容器实现，容器内同时承载 solver 工作区、隐藏 audit 服务和 task-bound skill。
- `tests/` 同时包含主测试与 guardrails，验证真实 CDC -> warehouse -> publish 行为，而不是某一份唯一答案文件。
- `solution/` 提供官方参考修复与一键求解脚本；final 版 oracle 已在 e2b 下稳定通过。
