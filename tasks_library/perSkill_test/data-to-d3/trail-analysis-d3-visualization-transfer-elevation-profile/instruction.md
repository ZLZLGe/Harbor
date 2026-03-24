请使用 D3.js 基于以下两个输入文件生成一个单页可视化页面，并把主文件写到 `/root/output/elevation-profile.html`。页面需要能直接在浏览器中打开。

- `/root/data/trail-samples.csv`
- `/root/data/trail-waypoints.json`

数据含义：
- `trail-samples.csv` 中每一行是路线上的一个采样点，包含 `distance_km`、`elevation_m`、`grade_pct`。
- `trail-waypoints.json` 中每个对象是一个途经点，包含 `id`、`name`、`distance_km`、`elevation_m`、`category`、`eta`、`note`。

页面要求：
- 页面主体分为两部分：左侧为高程剖面图，右侧为途经点浏览区；窄屏下可以上下排列。
- 高程剖面图容器使用 `#profile-chart`，需要同时显示一条高程面积图和一条高程折线。
- 每一段按坡度区间着色的折线段元素使用类名 `profile-segment`。
- 折线必须按相邻采样点之间的坡度区间逐段着色，并在 `#slope-legend` 中提供固定 4 档图例，标签顺序必须是：
  - `0-3.9% 平缓`
  - `4-7.9% 持续爬升`
  - `8-11.9% 陡坡`
  - `12%+ 冲顶段`
- 图上要有距离（km）和海拔（m）坐标轴，并能清楚看出整体爬升趋势。
- 为了保证悬停稳定，SVG 中需要为每个采样点提供一个可交互热点，类名为 `sample-hotspot`，可以是透明元素。
- 悬停任意采样点热点时，需要显示十字线和 tooltip。十字线横向元素使用 `#crosshair-x`，纵向元素使用 `#crosshair-y`，悬停焦点圆点使用 `#hover-focus`。tooltip 元素需带 `role="tooltip"`，内容固定为 3 行：
  - `距离: x.x km`
  - `海拔: n m`
  - `坡度: y.y%`
- 右侧途经点浏览区中，所有途经点按钮放在 `#waypoint-list` 内；按钮文本需要至少包含途经点名称和距离。
- 每个途经点都要在高程剖面上显示对应标记，标记元素使用类名 `waypoint-marker`，被选中的标记额外带 `is-selected` 类。
- 页面初始加载后，默认选中海拔最高的途经点。
- 点击任意途经点按钮后，需要同步完成这三件事：
  - 更新 `#waypoint-list` 中的选中状态，当前按钮的 `aria-pressed` 为 `true`
  - 高亮剖面图中对应的途经点标记
  - 更新 `#waypoint-detail` 说明面板，展示该途经点的名称、距离、海拔、类别、预计到达时间和说明文字

可以按需要在 `/root/output/` 下生成辅助脚本、样式和可直接访问的数据文件，但主页面必须是 `/root/output/elevation-profile.html`。
