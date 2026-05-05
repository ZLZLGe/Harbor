# CMS Platforms Template

这是面向 `cms-platforms` 类 skill 的模板。它综合参考 SkillsMP `cms-platforms` 类热门 skill 的共性能力：搭建内容模型、整理导入链路、约束发布与权限边界，并向前台提供可消费的数据接口。

## 第一部分：任务设计参考

* **Skill 价值定位**：这类热门 skill 的共同价值，在于帮助 Agent 沿着 CMS 平台的主工作流完成 collections、relationships、draft/publish、access control 与 feed/query 设计。高质量模板应让 skill 在内容模型、行为约束、行级可见范围和接口拼装上提供帮助，而不是把任务压成纯脚本生成或简单格式修改。
* **Task 目标形态**：这类任务适合设计成单容器内可运行的 CMS 工作区建设题，输入含多份结构化内容数据和业务约束文件，输出是可重建的数据后台与对外接口。任务目标应强调可运行、可核验和可重复重建，同时保留角色边界、发布约束、草稿归属与关系查询这类平台行为。
* **Verifier 设计重点**：Verifier 应优先验证 solver 是否沿着内容导入、关系建模、发布控制、接口过滤和角色授权这条链路完成交付，并检查输出文件与接口结果之间的一致性。对于这类 skill，还应重点验证 local API、draft/publish、row-level access 和草稿工作队列的执行结果，而不是只看静态文件是否存在。

## 第二部分：示例任务

### 📌 任务元数据
- 任务 ID：`cms-platforms__met-highlight-feed`
- 类别：`cms-platforms`
- 难度：`hard`
- 绑定 Skill：`payload`
- 输入数据参考来源：
  - `environment/data/met_departments.json`：任务内部门数据；设计形态参考 The Met Collection API departments endpoint  
    【https://collectionapi.metmuseum.org/public/collection/v1/departments】
  - `environment/data/met_object_details.ndjson`：任务内馆藏对象详情快照；设计形态参考 The Met Collection API object endpoint  
    【https://metmuseum.github.io/】
  - `environment/data/met_objects_seed.csv`：任务内对象种子与编辑位映射；字段形态参考 The Met Open Access catalog 与对象详情接口  
    【https://github.com/metmuseum/openaccess】

### 📊 验证与测试指标（Oracle & Verifier）
- Oracle：Oracle 从任务内 seed CSV、对象详情 NDJSON 和 lane 配置重算 summary 与公开 feed 结果，再结合在线接口验证角色动作是否真正改变系统状态。
- Verifier策略：

主测试
| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 数据重建入口 | 校验 `scripts/reseed.ts` 能基于当前输入生成 `seed-summary.json` | 本地导入链路与 Payload 数据重建 |
| 内容关系 | 校验部门、艺术家、馆藏条目、lane 与 highlight 的数量和关系结果 | collection 建模与 relationship 使用 |
| 公开 feed | 精确比对 `/api/highlight-lanes/feed` 返回结果 | custom endpoint、query、depth、字段拼装 |
| 过滤行为 | 校验 `department`、`audience`、`limit` 过滤 | relationship query 与结果裁剪 |
| 发布边界 | 校验未满足条件或仍为 draft 的内容不会进入公开 feed | draft/publish 工作流 |
| 角色动作 | 校验 editor 与 curator 对 publish/order 的操作结果不同 | access control 与行为边界 |
| 草稿归属 | 校验编辑者只能看到并修改自己的草稿队列，且删除动作不会越过角色边界 | row-level access 与 owner/workflow 约束 |

防作弊测试
| 测试点 | 验证内容 |
| :--- | :--- |
| 输入变更重跑 | 改动 `met_objects_seed.csv` 后 rerun，summary 与 feed 必须变化 |
| 静态答案拦截 | 禁止把公开 feed、summary 或 slug 直接写死在代码里 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值主要落在 collections、relationships、draft/publish、row-level access、hook 归属控制和 feed endpoint 的联动上。最近 3 次有效对照里，without_skill 都卡在草稿生命周期与角色边界动作上；with_skill 至少完成过 1 次全通过，但仍会受模型执行波动影响。

基于最近 **3** 次有效对比实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0% (0/3)` | `33% (1/3)` | without_skill 在 3 次有效对照里都保留了 verifier 失败；with_skill 有 1 次完整通过，说明 skill 对收敛有帮助，但当前仍存在执行波动 |
| Agent 执行耗时 | `730.5s` | `744.1s` | with_skill 的 2 次失败试跑拉高了均值，当前耗时优势不明显 |
| Tokens | `3.28M` | `3.17M` | with_skill 的平均上下文开销略低，约为 without_skill 的 `0.97x` |

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
│   ├── skills/
│   └── workspace/
├── tests/
│   ├── oracle.py
│   ├── test_outputs.py
│   ├── test_mutation.py
│   └── test.sh
└── solution/
    ├── fixed/
    └── solve.sh
```
