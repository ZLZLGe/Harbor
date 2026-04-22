你正在为一次董事会前的经营复盘补做正式分析包。

输入数据在：
- `/app/data/orders/`
- `/app/data/subscriptions/`
- `/app/data/marketing/`
- `/app/data/product/`
- `/app/data/support/`
- `/app/data/reference/metric_contract.json`
- `/app/data/reference/analysis_brief.md`
- 本地审计链路：
  - `GET http://127.0.0.1:8321/manifest`
  - `POST http://127.0.0.1:8321/validate-metrics`
  - `POST http://127.0.0.1:8321/submit-report`

你的任务
1、基于冻结的经营数据，产出一份按月汇总、可复核、可审计的 SaaS 经营分析结果包。
2、按公开口径计算核心指标，并把结果写入正式交付物，而不是只在临时脚本或 Notebook 里得到答案。
3、识别最值得董事会关注的增长来源、风险来源、效率问题和支持/产品联动问题，并给出量化证据。
4、通过真实的本地审计链路完成校验与最终提交，保存正式回执。

输出格式：
- 生成文件：
  - `/app/output/metrics_snapshot.csv`
  - `/app/output/diagnosis_report.json`
  - `/app/output/executive_summary.md`（必须是 markdown 文档，首行以 `# ` 一级标题开头）
  - `/app/output/final_submission.json`
  - `/app/output/audit_receipt.json`

说明：
- 正式交付物之间必须彼此一致；摘要、结构化诊断和最终提交不能各写各的。
- `executive_summary.md` 必须是董事会可直接阅读的 markdown 摘要，首行用一级标题概括核心结论，正文再展开增长、风险与效率信号。
- `metrics_snapshot.csv` 需要反映真实计算结果，不能手填、伪造或只覆盖部分切片。
- `metrics_snapshot.csv` 中每个数值单元都必须等于合同定义下最终应落盘的月度展示值；接近但不相等的舍入结果也会被 live validation 拒绝。
- `final_submission.json` 必须来自对磁盘正式交付物的整理，而不是一套与落盘文件不一致的内存对象。
- 如果环境中已经挂载了 `/app/.codex/skills/saas-board-metrics-diagnostics/`，应优先把它当作正式诊断辅助链路使用。
- 可以编写辅助脚本，但最终评分只看正式交付物和真实审计行为结果。
- 明确禁止 hack verifier、伪造或静态写死 audit receipt、替换真实提交流程、删除功能规避问题。
- 明确禁止修改隐藏服务、原始输入数据、测试文件、依赖配置、环境基线或 skill 本体。
