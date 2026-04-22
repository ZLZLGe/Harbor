你是一名设计工程团队的交付工程师，需要把一组冻结的真实风格品牌资料、产品指标、竞品对比、用户证据和流程拓扑整理成一份可审阅、可导出、可复核的 HTML 发布演示稿。当前已经有一版内部评审 draft 放在 `/app/workspace/drafts/internal_review_draft.html`，但它还没有通过正式交付约束与最终 QA；你的任务是在不绕开正式渲染与校验链路的前提下，把这份 draft 收敛成可以通过审核的正式 deck。

输入数据在：

- `/app/workspace/brief/creative_brief.md`：本次发布演示的业务目标、受众、必须回答的问题与禁止误导项
- `/app/workspace/specs/deck_contract.md`：正式交付约束，包括视口、可访问性、来源标注、导出与导航要求
- `/app/workspace/data/weekly_kpis.csv`：冻结的周度业务指标数据
- `/app/workspace/data/feature_matrix.csv`：冻结的方案 / 竞品能力对比表
- `/app/workspace/data/customer_quotes.json`：可公开使用的客户证据、访谈摘录与适用边界
- `/app/workspace/data/user_journey.json`：需要可视化表达的流程 / 概念拓扑
- `/app/workspace/mirror/site/`：冻结的官网镜像、局部截图与品牌素材，供视觉与文案对齐使用
- `/app/workspace/drafts/internal_review_draft.html`：当前内部评审 draft，可先诊断并收敛，再交付到正式输出目录
- 如果运行环境里提供了 task-local `launch-deck-diagnostics` 诊断技能，可以把它当作本地诊断工具集合；如果没有，也仍然需要独立完成正式交付
- 本地 render / QA 服务（只允许调用，不允许修改或替换）：
  - `GET http://127.0.0.1:8364/manifest`
  - `POST http://127.0.0.1:8364/validate`

你的任务
1、基于现有输入资料和当前 draft，交付一份正式 HTML 演示稿到 `/app/output/deck/index.html`。你可以先基于 `/app/workspace/drafts/internal_review_draft.html` 继续收敛，也可以在确认原稿不足后重做，但最终结果必须落到正式输出目录。该演示稿必须是浏览器可直接打开的成品，不依赖外网，不要求构建系统才能查看。
2、演示稿必须围绕输入资料形成 6 个逻辑完整的全屏页面，至少覆盖以下内容：
- 封面与核心结论
- 关键指标概览
- 方案或竞品对比
- 用户证据或场景说明
- 基于 `/app/workspace/data/user_journey.json` 生成的流程 / 概念图
- 风险、边界与下一步
3、所有数值结论、对比结论和引用性表述都必须来自给定输入，不得凭空编造；其中至少要包含：
- 1 个由 `/app/workspace/data/weekly_kpis.csv` 生成的数据驱动图表
- 1 个由 `/app/workspace/data/user_journey.json` 生成的流程 / 概念图
- 1 处以上对输入来源的显式标注，使审阅者能够追溯图表或结论来自哪份输入
4、保持正式交付约束兼容：演示稿在规定视口下不得出现依赖滚动才能看全主要内容的页面，不得把关键内容藏在 hover-only 或点击后才出现的区域里；同时要保留基本的键盘翻页或等价浏览方式。
5、通过正式本地 QA 链路获取 manifest，并提交最终演示稿校验，生成：
- `/app/output/deck_submission.json`
- `/app/output/deck_receipt.json`
6、如果你编写了辅助脚本、数据清洗脚本、临时导出页或排查说明，最终仍需把可交付结果落实为正式的 `/app/output/deck/index.html` 和正式 QA 回执，而不是只留下中间产物。
7、优先诊断并修正当前 draft 的真实问题，再决定是否需要大改视觉结构；不要在还没确认失败来源前直接整份重做。

输出格式：
- 生成文件：
  - `/app/output/deck/index.html`
  - `/app/output/deck_submission.json`
  - `/app/output/deck_receipt.json`
- `/app/output/deck/index.html` 必须是可直接在浏览器打开的 HTML 成品
- `/app/output/deck_submission.json` 必须是最终 live localhost 校验链路实际使用的正式提交 payload
- `/app/output/deck_receipt.json` 必须是真实 localhost QA 服务返回的正式回执，而不是手写的伪结果

说明：
- 不要 hack verifier，不要针对测试文件、固定 slide 数值、固定 KPI 值、固定文案片段、固定节点数量或固定校验字段做硬编码。
- 不要替换真实链路，不要伪造、跳过、短路或手写本地 render / QA 服务的提交与回执；不要把需要正式校验的步骤改成自己生成一个“看起来像成功”的 JSON。
- 不要把正式交付规避成截图集、纯图片海报、视频录屏、PDF 截图页或只有静态长图的伪 deck；正式结果必须是可在浏览器中打开并审阅的 HTML 演示稿。
- 不要删功能规避问题，例如删掉必需页面、删掉图表、删掉流程图、删掉来源标注、删掉导航能力，或让页面只剩空壳标题与占位内容。
- 不要修改本地 QA 服务、测试文件、冻结输入数据的业务含义、正式校验契约或依赖配置。
- 可以增加日志、辅助脚本、局部样式与结构重构，但评分以正式 HTML 成品和真实 QA 链路下的行为结果为准。
