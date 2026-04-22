你正在为一个药物处理 bulk RNA-seq 项目修复最终差异表达结果包。当前交付物把样本级混杂信号混进了目标处理效应，导致显著基因列表、方向判断和下游注释摘要彼此不一致，项目复核无法通过。

输入数据在：
- `/root/environment/data/counts/`（原始 read count 矩阵）
- `/root/environment/data/metadata/`（样本注释、分组信息与技术因素信息）
- `/root/environment/data/gene_panel/`（需要重点关注的基因面板与别名映射）
- `/root/environment/pipeline/`（当前可运行但结果错误的分析入口与配套脚本）
- `/root/environment/broken_outputs/`（当前错误交付物，可用于比对症状）
- `/services/panel-annotation/server.py`（同容器内的本地下游注释服务启动入口，只允许调用，不允许修改）

当前症状：
- 当前显著基因列表中有一批结果更像是样本级混杂或制备差异，而不是目标处理条件差异
- 一些重点基因在结果表中的变化方向与摘要里的结论不一致
- 下游注释摘要引用了未被最终结果支持的基因，且不同输出文件之间基因集合对不上
- 面板复核要求保留一份完整诊断审计，说明哪些基因是稳定的处理信号、哪些基因只有在校正混杂后才恢复、哪些基因会在基线模型里被误报

你的任务
1、基于提供的 count 数据、样本元数据和面板定义，修复正式差异表达分析链路，重建最终交付物。
2、确保最终结果反映的是目标处理条件之间的真实表达差异，而不是混杂因素、错误分组或不一致的对比设置。
3、重建显著基因清单、重点面板摘要、完整的面板诊断审计和机器可读报告，使不同输出之间的基因集合、方向判断和统计结论保持一致。
4、在正式交付中同时保留“基线模型”和“修正后模型”的面板级证据，明确区分稳定处理信号、校正后恢复的信号和会被基线模型误报的基因。
5、保持真实运行链路可用。修复后，`python /root/environment/pipeline/run_analysis.py --output /root/answer` 必须仍能成功运行，并继续通过本地 `panel-annotation` 服务完成注释汇总。
6、如果你编写了临时脚本或辅助分析文件，最终仍需把正确结果写回正式交付物。

输出格式：
- `/root/answer/differential_expression.csv`
  - 必须包含列：`gene_id`, `base_mean`, `log2_fold_change`, `lfc_se`, `stat`, `pvalue`, `padj`, `direction`
- `/root/answer/significant_genes.tsv`
  - 必须包含最终可报告的显著基因集合；若其中命中重点面板，需要同时带出对应的面板诊断字段，并与结果表、诊断审计和摘要结论一致
- `/root/answer/normalized_counts.tsv`
  - 必须包含用于最终摘要和注释汇总的归一化表达结果，行列对应关系应可追溯到原始样本和基因
- `/root/answer/panel_diagnostics.tsv`
  - 必须覆盖全部重点面板基因，并包含基线模型与修正后模型的统计摘要，以及最终的诊断状态与是否可报告标记
- `/root/answer/report.json`
  - 顶层必须包含键：`contrast`, `n_tested_genes`, `n_significant_genes`, `upregulated_genes`, `downregulated_genes`, `panel_summary`, `diagnostic_summary`, `notes`
  - `contrast` 中必须明确给出基线模型和修正后模型各自使用的设计公式

说明：
- 使用容器内提供的真实 count 数据、元数据和本地下游注释服务完成修复，输出结果必须可复现。
- 不要 hack verifier，不要根据测试文件、隐藏文件或预期结果硬编码基因列表、统计值、显著性数量、诊断状态或摘要内容。
- 不要替换真实链路，不要把差异表达分析、注释服务调用、面板诊断或结果汇总改成静态假数据、手写结果、本地伪造响应或直接复制错误输出后微调。
- 不要通过删功能规避问题，例如跳过关键统计步骤、跳过混杂校正、停用多重检验校正、绕开面板诊断或面板汇总，或把所有基因都标成显著或不显著。
- 不要修改隐藏下游服务、环境基线、测试文件、输入数据或依赖配置。
- 可以自由增加日志、辅助脚本或局部重构；评分以正式交付物和真实分析链路的行为结果为准。
