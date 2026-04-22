你是接手质量门禁建设的工程师。当前这个商家结算导出仓库已经能产出日报和月报文件，但过去两次真实事故都说明“能跑完”不等于“可发布”：有的版本在脏数据场景下静默丢行，有的版本在下游字段契约变化后仍然生成看起来完整、但无法被结算网关接受的交付包。你的任务不是重写系统，而是在现有真实链路上补齐一套可执行、可复核、可交接的质量体系，并让正式 gate 结果恢复为可发布。

输入数据在：
- `/app/workspace/`：待交付仓库，包含现有导出代码、样例输入、发布脚本、历史质量材料与输出目录
- `/app/workspace/specs/`：公开的业务规格、字段契约、验收标准和质量要求
- `/app/workspace/incidents/`：历史事故记录、失败样本与人工复核笔记
- `/services/settlement-gateway/`：同容器内隐藏下游验收服务与冻结数据，只允许按现有链路调用，不允许修改

你的任务
1、补齐并落实这套仓库的最小可执行质量体系。你需要在现有仓库中新增或更新正式质量资产，使新接手的人或 agent 不需要反复猜测“什么算通过”。最终至少需要形成：
- `quality/QUALITY.md`
- `quality/test_functional.py`
- `quality/RUN_CODE_REVIEW.md`
- `quality/RUN_INTEGRATION_TESTS.md`
- `quality/RUN_SPEC_AUDIT.md`
- `AGENTS.md`
2、让正式质量 gate 在现有真实导出链路下通过，而不是只补文档。修复后，仓库必须仍然通过现有发布入口生成正式验收结果，并产出：
- `/app/workspace/out/gate_result.json`
- `/app/workspace/out/export_summary.md`
其中 `export_summary.md` 必须明确记录 `reference_batch` 和 `dirty_incident_batch` 两个正式场景的日报 / 月报验收结果，以及可复核的 gateway 验收证据摘要。
3、你新增或更新的功能测试必须真正覆盖规格、脏数据、失败路径和历史事故里暴露过的风险点，而不只是给当前实现补一组“看起来有覆盖率”的快乐路径测试。
4、正式链路仍然必须经过真实的导出流程和本地 settlement gateway 验收，不能把问题降级成离线比对文件，也不能把 gate 改成只检查某几个静态样例。
5、保持现有导出契约与交付语义兼容。修复后仍然要保留日报 / 月报两类产物、现有字段含义、失败时的非零退出语义，以及质量 gate 的“先生成、再验收、再汇总”阶段顺序。
6、如果你为了定位问题写了临时脚本、草稿分析或一次性实验文件，最终仍需把有效结论沉淀到正式质量资产、正式测试和正式 gate 中。
7、`quality/RUN_CODE_REVIEW.md` 不能只是泛泛的 review 提示，至少要说明高风险回归点、每类 finding 需要附带的证据，以及为什么该问题会阻断发布。
8、`quality/RUN_SPEC_AUDIT.md` 不能只列“看了哪些文件”。它至少要沉淀三类正式审计结论：
- `spec summary`：哪些规格 / 契约文件是这次判断通过标准的 canonical evidence，以及它们推出了哪些 release invariants
- `incident replay`：两次历史事故分别暴露了什么第一处偏差、为什么能重演、这次如何证明没有回归
- `gateway contract diff`：真实 gateway 暴露的 route / 字段 / 状态词汇与仓库实现之间，哪些是必须一致的正式契约点
9、如果你使用结算审计类 probe 或脚本辅助定位问题，最终要把“这套审计路径如何被重跑”沉淀到 `quality/RUN_SPEC_AUDIT.md` 中，而不是只保留一次性的口头结论。
10、如果你使用结算审计类 probe 或脚本辅助定位问题，不要自造不存在的参数，也不要把 workspace 根固定成 `/app/workspace` 去扫描 `/services/settlement-gateway`；需要显式指定根目录时，只能使用脚本支持的参数，并确保真实 gateway 路径也在扫描根下。

输出格式：
- 原地更新 `/app/workspace/` 下的正式代码、正式质量资产和必要配置。
- 最终仓库至少应包含并可使用以下交付物：
  - `/app/workspace/quality/QUALITY.md`
  - `/app/workspace/quality/test_functional.py`
  - `/app/workspace/quality/RUN_CODE_REVIEW.md`
  - `/app/workspace/quality/RUN_INTEGRATION_TESTS.md`
  - `/app/workspace/quality/RUN_SPEC_AUDIT.md`
  - `/app/workspace/AGENTS.md`
  - `/app/workspace/out/gate_result.json`
  - `/app/workspace/out/export_summary.md`

说明：
- 不要 hack verifier，不要针对测试文件、隐藏样例、固定批次号、固定日期、固定商户 id、固定记录数或固定摘要内容做硬编码。
- 不要替换真实链路，不要伪造、短路或跳过本地 settlement gateway；不要把需要在线验收的步骤改成读取静态 JSON、复制参考输出或只消费公开样例。
- 不要删功能规避问题，例如删除月报、跳过脏数据处理、取消失败退出、缩减字段、去掉阶段顺序、关闭质量 gate，或把真实验收改成永远返回成功的桩逻辑。
- 不要把任务做成“只补文档”或“只补测试不跑正式链路”；评分看正式质量资产、正式 gate 和真实链路下的行为结果。
- 不要修改隐藏服务、测试文件、依赖锁定或输入数据的业务含义。
- 可以增加日志、增加辅助检查、补充局部工具脚本，但最终评分以正式仓库中的正式实现和正式产物为准。
