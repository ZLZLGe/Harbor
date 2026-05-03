你正在为一场“全球可再生能源扩张进展”季度简报制作正式 HTML 演示文稿。策略团队已经准备好了简报提纲、数据快照、引用目录和一组可用视觉素材，现在需要一套可离线打开、适合投影和移动端预览、可直接交付给管理层的浏览器端 deck。

输入数据在：
- `/root/environment/data/brief/`：简报提纲、受众说明、信息优先级、语气要求、章节顺序和最终交付约束
- `/root/environment/data/series/`：来自公开能源数据源的本地数值快照，包含全球年度装机、发电结构、国家对比和补充维度
- `/root/environment/data/assets/`：可用于演示文稿的本地图片、标识和辅助视觉素材
- `/root/environment/data/sources/`：本次简报允许使用的来源目录、简称和链接映射
- `/root/environment/deck/`：正式演示文稿构建入口、样式、脚本和图表生成代码
- `/services/source-registry/server.py`：同容器内的本地 source registry 服务启动入口，只允许调用，不允许修改

你的任务
1、根据简报提纲、数据快照、视觉素材和受众要求，生成正式 HTML 演示文稿，完整覆盖简报要求的全部章节与核心结论。
2、管理层目前只确认了内容范围，还没有确认最终视觉方向；你需要先做 3 个明显不同的单页视觉方向探索，再自行收敛成 1 套正式演示风格落到最终 deck，且这 3 份探索稿需要保留在工作区供后续复核。
3、正式演示文稿必须形成统一且适合管理层简报的视觉表达，不依赖外网资源，并适合桌面投影、小屏竖屏和小屏横屏预览；具体目标尺寸见输出要求。
4、所有图表脚注、来源简称和引用链接都必须与本地 source registry 返回的规范结果一致。
5、如果你编写了临时脚本或辅助文件，最终仍需把正确结果写回正式构建链路，并保证正式入口 `/root/environment/deck/build_briefing.py --output /root/answer` 可重复运行。

输出：
- `/root/answer/presentation.html`
  - 必须是一个可本地直接打开的完整 HTML deck，不依赖外网资源
  - 必须包含 8 张正式幻灯片，且 `slide_id` 顺序和页面锚点都必须使用这组固定值：`slide-cover`、`slide-summary`、`slide-growth`、`slide-mix`、`slide-country`、`slide-risks`、`slide-actions`、`slide-sources`
  - 必须支持键盘方向键、鼠标滚轮和触摸滑动翻页，并以 deck 内状态切换完成，不要依赖整页滚动或只靠锚点跳转；实现上要真实处理 `keydown`、`wheel`、`touchstart` / `touchend` 这类浏览器输入事件
  - 必须持续显示当前页序或等效的进度提示，便于投影和移动端预览时识别当前位置；该元素需要在 DOM 中可直接识别，使用 `id="progress-text"` 或等效的 `data-progress-text`
  - 除来源页外，凡使用数据、判断或结论的页面，都必须在页脚或等效位置显示可见的来源简称，并链接到本地 source registry 返回的规范链接；每个来源标记都要带 `data-source-id="<source_id>"`，不要只在最后一页集中列来源
  - 文字内容必须保持 DOM 可访问，不要把整页导出成单张图片或整页 canvas
  - 每张正式幻灯片都必须在单个视口内完整展示，不允许页内滚动；每页都要保留足够的正文、说明或脚注文字，避免只剩标题和占位元素
- `/root/answer/presentation_manifest.json`
  - 必须包含顶层键：`deck_title`, `slide_count`, `slides`, `data_files_used`, `asset_files_used`, `source_ids_used`, `viewport_targets`, `design_notes`
  - `slide_count` 必须为 `8`
  - `slides` 中每个对象必须包含键：`slide_id`, `title`, `primary_message`, `visuals_used`, `chart_ids`, `source_ids`
  - `viewport_targets` 必须覆盖这 5 个尺寸：`1920x1080`、`1280x720`、`768x1024`、`375x667`、`667x375`
  - `design_notes` 必须是对整体视觉方向、排版节奏和图表处理原则的简要说明，并明确记录最终收敛采用的视觉方向
- `/root/answer/source_audit.json`
  - 必须包含顶层键：`registry_endpoint`, `registry_checked`, `sources_resolved`, `slide_source_map`, `notes`
  - `registry_checked` 只能为 `true` 或 `false`；正式结果必须为 `true`
  - `registry_endpoint` 必须写入 `http://127.0.0.1:4873`
  - `sources_resolved` 中每个对象必须包含键：`source_id`, `short_label`, `canonical_url`
  - 必须覆盖本次要求的全部 `source_id`，并能对应回各页实际使用的来源

说明：
- 使用容器内提供的提纲、数据、素材和本地 source registry 完成任务，最终结果必须可复现。
- 在正式稿落地前，先做视觉方向探索，再确定正式方向；不要跳过探索过程直接产出最终页，也不要在完成正式稿后删除探索稿。
- 正式构建过程中必须真实探测本地 source registry 的健康状态，并逐个解析题面要求的来源；最终结果中的引用、简称、链接和来源映射要与该解析结果一致。
- 可以自由决定图表样式、版式、色彩、字体、动效、章节内的信息分配和素材使用方式，但必须保留真实数据链路、完整章节和可复核引用。
- 不要替换真实链路，不要把数据读取、图表生成、来源核对或正式输出改成静态占位、截图、录屏、硬编码结论或伪造 registry 响应。
- 不要把翻页体验退化成目录跳转页或长页面浏览；管理层实际使用时需要稳定的逐页浏览和当前位置提示。
- 不要通过删功能规避问题，例如把 8 张正式幻灯片缩减成更少页、删除图表、删除来源页、删除章节、删除翻页能力，或把所有内容堆到单页长滚动页面。
- 不要修改输入数据、本地 source registry 服务、测试、依赖基线或任何 skill 文件。
- 不要要求 solve 时访问互联网；正式结果应完全由容器内数据和本地服务生成。
