Media Pickup Bundle Template

这是面向 media 类 skill 的模板。它综合参考 SkillsMP media 热门 skill 的共性能力：从公开媒体输入读取片段，按帧或时间定位抽取素材，生成可回放的交付包，并让输出能被稳定校验。

## 第一部分：任务设计参考
* **Skill 价值定位**：这类 skill 的共性价值，是把媒体读取、定位抽取、批量导出和结构化交付串成一条稳定工作流。对模板任务来说，关键是把“找对片段并正确交付”变成可直接核验的行为结果。
* **Task 目标形态**：任务目标应当落在公开媒体素材上的确定性交付，例如静帧、短预览、联系表和元数据清单。输出既要覆盖全部请求，也要保留顺序、尺寸和来源字段，方便 verifier 逐项比对。
* **Verifier 设计重点**：verifier 需要同时检查覆盖率、内容一致性、顺序一致性和输出目录整洁度。除了主路径产物，还要防止改输入、改 skill 载荷、写占位结果或绕开规定工作流。

## 第二部分：示例任务
### 📌 任务元数据
- 任务 ID：`media__frame_pickup_delivery_bundle`
- 类别：`media`
- 难度：`hard`
- 绑定 Skill：`video-frames`
- 输入数据参考来源：
  - `environment/data/clip_manifest.json`：任务内 clip 清单，绑定以下公开片源  
    【https://download.blender.org/peach/trailer/trailer_iphone.m4v】  
    【https://download.blender.org/durian/trailer/sintel_trailer-720p.mp4】  
    【https://download.blender.org/peach/bigbuckbunny_movies/BigBuckBunny_320x180.mp4】
  - `environment/data/shot_requests.csv`：任务内 pickup 请求，locator 与预览时间窗均基于同一组公开片源  
    【https://download.blender.org/peach/trailer/trailer_iphone.m4v】  
    【https://download.blender.org/durian/trailer/sintel_trailer-720p.mp4】  
    【https://download.blender.org/peach/bigbuckbunny_movies/BigBuckBunny_320x180.mp4】

### 📊 验证与测试指标（Oracle & Verifier）
- Oracle：用同一组输入视频重建参考静帧、预览采样帧和联系表布局，并对输出 JSON 的字段、顺序和文件清单做一致性比对。
- Verifier 策略：

主测试

| 测试点 | 验证内容 | 对应 skill 内化点 |
| :--- | :--- | :--- |
| 静帧覆盖与一致性 | `stills/` 覆盖全部请求且逐张匹配目标 locator | 正确按帧或时间定位抽帧 |
| 预览片段一致性 | `previews/` 的时长、分辨率和采样帧与源视频窗口一致 | 正确裁取时间窗并保留媒体属性 |
| 联系表排版 | `sheets/` 的 2x2 布局、尺寸和格内内容与静帧一致 | 批量拼版与顺序保持 |
| 元数据与顺序 | `frame_index.json`、`delivery_report.json` 的 clip 顺序、request 顺序、路径和计数一致 | 结构化交付与清单回填 |
| 输出目录整洁 | 顶层仅包含规定产物 | 受控交付边界 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 输入不可变 | `/root/media_pick/input` 哈希不变 |
| Skill 载荷不可变 | 已下发的 `environment/skills/video-frames` 哈希不变 |
| 禁止占位文本 | 输出 JSON 不含 `placeholder`、`todo`、`verifier` 等定向痕迹 |
| 目录白名单 | 输出目录没有额外顶层文件 |

### ⚡ Skill 相关性评估
结论：强相关。这个任务要求 solver 把公开视频输入、定位片段、批量导出和交付清单连成一条闭环；`video-frames` 的核心价值，是把帧定位与媒体导出路径标准化，从而让 agent 更容易进入正确行动链路。

基于最近 **3 次** 有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0% (0/3)` | `100% (3/3)` | 近 3 次有效对照里，without Skill 都停在 helper 路径阻塞，未完成交付包；with Skill 3 次均通过全部 verifier |
| Agent 执行耗时 | `114.7s` | `187.9s` | without Skill 耗时更低，但原因是更早失败；with Skill 完成了全量媒体产物生成与回读校验 |
| Tokens | `250.8k` | `371.8k` | without Skill 的 token 更少，同样源于提前停在阻塞点；with Skill 覆盖了完整媒体处理链路 |

## 📁 标准目录结构说明
```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── data/
│   └── skills/
├── tests/
│   ├── test.sh
│   ├── test_guardrails.py
│   └── test_outputs.py
└── solution/
    └── solve.sh
```
