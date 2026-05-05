# Full-Stack Template

这是面向 full-stack 类 skill 的模板。它综合参考 SkillsMP full-stack 热门 skill 的共性能力：在空白工作目录中建立完整项目结构，补齐依赖与启动链路，在单容器里交付同项目内的页面、接口和本地状态持久化，并让结果能够被稳定校验。

## 第一部分：任务设计参考
* **Skill 价值定位**：这类 skill 的核心价值，在于把“从空工作目录到可运行项目”的初始化路径标准化，减少 solver 在目录结构、脚本入口、依赖装配和本地运行方式上的试错。模板任务应让 skill 的这部分优势直接影响能否尽快进入业务实现阶段。
* **Task 目标形态**：这类任务更适合要求 solver 一次性交付完整工作台，少依赖对现成代码的局部补缀。题面重点应落在交付合同、业务动作、运行方式和约束边界，让 solver 需要自己建立项目骨架、页面路由、接口契约和本地状态链路；如果示例任务明确限定了 Next.js App Router 或其他现代框架，题面应把这类初始化合同写清楚。
* **Verifier 设计重点**：校验不应只盯静态文件是否存在，而应覆盖默认启动是否成功、项目骨架是否与题面约束一致、接口是否按输入数据计算、页面是否可实际操作，以及状态变更是否在重启后保留。对照实验里，without_skill 的失败最好落在项目初始化或联调动作没有完成，避免只剩轻微格式偏差。

## 第二部分：示例任务
### 📌 任务元数据
- 任务 ID：`imdb-curation-workbench-scaffold`
- 类别：`full-stack`
- 难度：`hard`
- 绑定 Skill：`project-setup-info-local`
- 输入数据参考来源：
  - `environment/data/title_basics_sample.tsv`：任务内片目基础信息；设计形态参考 IMDb `title.basics.tsv.gz`  
    【https://datasets.imdbws.com/title.basics.tsv.gz】
  - `environment/data/title_ratings_sample.tsv`：任务内评分与票数快照；直接取自 IMDb `title.ratings.tsv.gz`  
    【https://datasets.imdbws.com/title.ratings.tsv.gz】
  - `environment/data/title_crew_sample.tsv`：任务内导演与编剧关联；设计形态参考 IMDb `title.crew.tsv.gz`  
    【https://datasets.imdbws.com/title.crew.tsv.gz】
  - `environment/data/title_principals_sample.tsv`：任务内主要演职员关联；设计形态参考 IMDb `title.principals.tsv.gz`  
    【https://datasets.imdbws.com/title.principals.tsv.gz】
  - `environment/data/name_basics_sample.tsv`：任务内人物名称映射；设计形态参考 IMDb `name.basics.tsv.gz`  
    【https://datasets.imdbws.com/name.basics.tsv.gz】

### 📊 验证与测试指标（Oracle & Verifier）
- Oracle：官方解会在空白 `/app/workspace` 中建立完整的 Next.js App Router TypeScript 工作台，保留默认启动脚本，基于本地 IMDb 快照生成浏览、详情和 shortlist 管理能力，并通过重启验证本地持久化。
- Verifier 策略：

主测试

| 测试点 | 验证内容 | 对应 skill 内化点 |
| :--- | :--- | :--- |
| Bootstrap & Health | 默认入口是否能安装、构建并启动应用 | 项目初始化、依赖与脚本入口 |
| Next.js Scaffold Contract | 是否建立了 `Next.js App Router + TypeScript + src/app` 的完整项目骨架 | 空目录起项目、框架脚手架、标准目录组织 |
| Catalog Query Contract | 筛选、排序、分页是否按本地快照计算 | 数据装载、接口契约、列表页联动 |
| Detail Contract | 单片详情接口是否返回稳定字段 | 路由建立、详情页与数据聚合 |
| Shortlist API Persistence | 新增、编辑、删除及重启保留是否成立 | 本地状态写入、重启后读取 |
| Browser Workflow | 页面是否能完成检索、跳转详情和加入 shortlist | 前后端联调、实际交互闭环 |
| Alternate Fixture Generalization | 切换备用数据后是否仍能正确返回新条目 | 避免写死答案、保留数据链路 |
| Input Integrity & Skill Payload | 输入数据与 skill 载荷是否未被篡改 | 遵守边界、不能靠改题取巧 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| Alternate Fixture Switch | 重新以 `data_alt` 启动后，必须能检索默认快照里没有的片目 |
| Static Hash Check | 比对输入文件哈希，阻止通过改数据规避任务约束 |

### ⚡ Skill 相关性评估
结论：中等相关。这个任务把空工作目录起项目、保留默认脚本链路、补齐 App Router 骨架和本地持久化放在前置位置；without_skill 多次停在脚手架、启动健康检查或浏览器工作流，说明 skill 对进入业务实现阶段有帮助，但最近几次 trial 里 with_skill 侧仍存在收敛波动。

基于最近 **4** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `50%` | 近 4 次有效对照里，without_skill 均有 verifier 失败，主要落在浏览器工作流、Next.js 脚手架合同或健康检查；with_skill 有 `2/4` 次完整通过。 |
| Agent 执行耗时 | `651.5s` | `628.7s` | With Skill 的平均 Agent 耗时下降约 `3.5%`，在起项目和联调阶段收敛更快。 |
| Tokens | `2.68M` | `2.65M` | With Skill 的上下文与试错开销略低，平均总 tokens 下降约 `1.0%`。 |

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
│   ├── data_alt/
│   ├── scripts/
│   └── skills/
├── tests/
│   ├── test.sh
│   └── verify_curation_workbench.py
└── solution/
    ├── solve.sh
    └── reference/
```
