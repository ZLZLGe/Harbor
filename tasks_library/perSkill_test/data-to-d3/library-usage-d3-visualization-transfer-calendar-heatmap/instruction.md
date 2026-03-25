请读取 `/root/data/library_daily_checkouts_2025.csv`，生成一个静态 SVG 报告到 `/root/output/library-checkout-heatmap.svg`。

这是一个离线报表任务。最终产物必须是单个 SVG 文件，不要输出 HTML，也不要依赖任何外网资源、远程脚本或浏览器运行时。

请满足下面这些明确要求：

1. 根元素必须是 `<svg>`，并带有 `id="library-checkout-report"`。
2. 报告必须把 2025 年 12 个月分成 12 个独立面板。
   - 每个月面板都必须是一个 `<g class="month-panel">`
   - 每个月面板都必须带 `data-month="YYYY-MM"`
   - 每个月面板内都必须有一个 `<text class="month-label">`
3. 每条 CSV 记录都必须对应一个 `<rect class="day-cell">`，并放在所属月份面板内。
   - 每个日期方块都必须带这些属性：
     - `data-date="YYYY-MM-DD"`
     - `data-count="<原始借阅量整数>"`
     - `data-month="YYYY-MM"`
     - `data-weekday="<0-6>"`
     - `data-week-index="<从 0 开始的月内周序号>"`
     - `data-weekend="true|false"`
     - `data-holiday="true|false"`
   - 这里的 `data-weekday` 使用 Monday=0, Tuesday=1, ..., Sunday=6
   - 周六和周日的日期方块必须额外带有 `weekend` class
   - 如果该行 `holiday_name` 非空，则这个方块还必须带非空的 `data-holiday-name`
4. 日期方块必须按“月份内日历网格”排布，而不是单纯按时间线摆放。
   - 同一个月份面板内，同一 `data-weekday` 的方块应落在同一列
   - 同一 `data-week-index` 的方块应落在同一行
5. 必须用颜色编码 `checkout_count`，并且整个 SVG 中的日期方块至少要出现 5 种不同的填充颜色。
6. 必须包含颜色图例 `<g id="checkout-legend">`。
   - 图例内必须有且仅有 5 个 `<rect class="legend-swatch">`
   - 必须有 `<text class="legend-min">`，文本中包含 CSV 最小借阅量
   - 必须有 `<text class="legend-max">`，文本中包含 CSV 最大借阅量
7. 必须同时标记周末和节假日。
   - 周末通过第 3 条中的 `weekend` class 表达
   - 每一个 `holiday_name` 非空的日期，还必须额外生成一个 `<circle class="holiday-marker" data-date="YYYY-MM-DD">`
8. 必须对借阅量最高的 3 个日期添加文字注释，规则是先按 `checkout_count` 降序，再按日期升序打破并列。
   - 注释容器必须是 `<g id="peak-annotations">`
   - 容器内必须有且仅有 3 个 `<text class="peak-annotation">`
   - 每个注释文本都必须包含对应日期和借阅量
   - 如果该行 `event_label` 非空，注释文本里还必须包含这个 `event_label`
   - 每个注释文本都必须带 `data-date="YYYY-MM-DD"`
9. 最终 SVG 必须是 standalone 文件，不能包含 `<script>` 标签，也不能包在 HTML 外壳里。

除以上契约外，版式、配色和附加说明文字可以自由发挥，但必须保证可读性。
