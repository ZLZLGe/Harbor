# Database Tools Template

这是面向 database-tools 类 skill 的模板。它综合参考 SkillsMP 数据库工具类热门 skill 的共性能力：围绕带版本的数据库变更、数据回填、发布回退、以及基于当前输入重建结果的校验，设计一个可运行、可验证、且能在仓库既有工作流中完成的任务。

## 第一部分：任务设计参考
* **Skill 价值定位**：这类 skill 的共性价值，是把数据库变更放回仓库工作流中处理，而不是临时手改或只做表面产物。它们通常强调迁移边界、回退路径、数据回填、以及面向当前输入的重复构建验证。
* **Verifier 设计重点**：Verifier 应同时覆盖最终数据内容、迁移状态、回退后状态、以及对当前输入目录变化的响应，避免只检验单次静态输出。对数据库工具类任务，还应防止通过改输入、缓存答案、绕开数据库入口或重写已交付迁移来取巧。

## 第二部分：示例任务
### 📌 任务元数据
- 任务 ID：`database-tools-movielens-catalog-release`
- 类别：`database-tools`
- 绑定 Skill：`database-migrations`, `database-migrations-codex`
- 输入数据参考来源：
  - `environment/data/movies.csv`：任务内电影主数据；设计形态参考 MovieLens Latest Small 数据集中的电影与类型字段  
    【https://files.grouplens.org/datasets/movielens/ml-latest-small.zip】
  - `environment/data/ratings.csv`：任务内评分事件；设计形态参考 MovieLens Latest Small 数据集中的评分与时间戳字段  
    【https://files.grouplens.org/datasets/movielens/ml-latest-small.zip】
  - `environment/data/tags.csv`：任务内标签事件；设计形态参考 MovieLens Latest Small 数据集中的标签与时间戳字段  
    【https://files.grouplens.org/datasets/movielens/ml-latest-small.zip】
  - `environment/data/links.csv`：任务内 IMDb / TMDb 映射；直接来源于 MovieLens Latest Small 数据集中的 links 表  
    【https://files.grouplens.org/datasets/movielens/ml-latest-small.zip】

### 📊 验证与测试指标（Oracle & Verifier）
- Oracle：按正式流程独立运行并完成交付，结果可直接 100% 通过验证。
- Verifier策略：

主测试

| 测试点 | 验证内容 | 对应skill内化点 |
| --- | --- | --- |
| rebuild contract | rebuild 后报告字段、步骤顺序、迁移版本链和核心对象全部成立 | 以仓库入口驱动迁移发布 |
| catalog content | 维表、映射表、标签事件内容与源数据语义一致 | schema / backfill 语义正确 |
| release content | 月度热度与导出视图满足发布后的完整业务定义 | 发布层数据刷新与导出逻辑 |
| rollback and replay | `migrate_down` 后保留基线状态，`migrate_up` 后恢复发布状态 | 回退边界和重放路径 |
| input sensitivity | 切换输入目录后，数据库和报告随当前输入变化 | 基于当前输入重建，不走缓存 |

防作弊测试

| 测试点 | 验证内容 |
| --- | --- |
| source integrity | 原始 CSV 文件哈希不变，不能靠改输入过关 |
| baseline integrity | 已交付基线迁移哈希不变，不能重写既有迁移 |
| no cached answers | 结果必须来自数据库重建与查询，不能只保留预计算报告 |
| no workflow bypass | 不能绕过 PostgreSQL 或仓库既有迁移入口完成任务 |

### ⚡ Skill 相关性评估
结论：强相关。这个任务的核心难点不在写单条 SQL，而在于沿既有迁移工作流交付一版增量 catalog 发布，并让 rebuild、rollback、replay 与输入切换共同成立。skill 的主要价值，是把“新增迁移、分离 schema / backfill / export、控制回退边界、再用当前输入验证”这套路径固定下来，从而明显降低错误试探成本。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | 近 3 次有效对照里，without Skill 都至少保留了 1 项 verifier 失败；主要失败点是直接改写既有基线迁移，触发 baseline migration hash guard。 |
| Agent 执行耗时 | `364.1s` | `348.9s` | With Skill 的迁移分层和回退路径收敛更快，平均 Agent 耗时约下降 `4.2%`。 |
| Tokens | `608421` | `529625` | Without Skill 的试探和返工更多，平均 tokens 约为 With Skill 的 `1.15x`。 |

## 📁 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── workspace/
│   └── skills/
├── tests/
└── solution/
```
