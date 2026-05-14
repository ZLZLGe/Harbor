Media Pickup Bundle Template

这是面向 media 类 skill 的模板。它综合参考 SkillsMP media 热门 skill 的共性能力：从公开媒体输入读取片段，按帧或时间定位抽取素材，生成可回放的交付包，并让输出能被稳定校验。

## 第一部分：任务设计参考
* **Skill 价值定位**：这类 skill 的共性价值，是把媒体读取、定位抽取、批量导出和结构化交付串成一条稳定工作流。对模板任务来说，关键是把“找对片段并正确交付”变成可直接核验的行为结果。
* **Verifier 设计重点**：verifier 需要同时检查覆盖率、内容一致性、顺序一致性和输出目录整洁度。除了主路径产物，还要防止改输入、写占位结果或绕开规定工作流。

## 第二部分：示例任务
### 📌 任务元数据
- 任务 ID：`media__frame_pickup_delivery_bundle`
- 类别：`media`
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
- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier 策略：

主测试

| 测试点 | 验证内容 | 对应 skill 内化点 |
| :--- | :--- | :--- |
| 静帧生成 | `stills/` 包含所有请求的图片，且内容完全正确 | 准确的抽帧能力 |
| 预览片段 | `previews/` 的时长、大小等信息与源视频相符 | 视频截取与属性保留 |
| 排版检查 | `sheets/` 的排版布局与图片内容一致 | 批量处理和排版能力 |
| 整理清单 | 清单文件里的文件顺序和数量能完全对上 | 信息整理和校对能力 |
| 目录整洁 | 输出文件夹只包含要求的文件 | 只提供需要的内容 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 保护输入 | 源文件（`/root/media_pick/input`）未被篡改 |
| 保护环境 | 提供的媒体输入素材未被篡改 |
| 隐藏作弊 | 输出文件不能有 `placeholder` 或测试痕迹 |
| 输出限制 | 文件夹里没有多余的无关文件 |

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
