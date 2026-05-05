# Architecture Patterns Template

这是面向 Architecture Patterns 类 skill 的模板。它综合参考 SkillsMP Architecture Patterns 类热门 skill 的共性能力：在已有系统中补一项新能力、沿既有入口和契约接入、保持领域逻辑与交付方式解耦，并通过完整运行链路验证行为，避免停留在表面拼接。

## 第一部分：任务设计参考

* **Skill 价值定位**：Architecture Patterns 类热门 skill 的核心价值，在于让新增能力沿现有系统边界落地，保持接口、数据映射、运行入口和交付结果之间的清晰职责分离。对于 `api-connector-builder` 这类 skill，关键点是先识别仓库里已有集成模式，再把新能力按同一风格接完整。
* **Task 目标形态**：任务应尽量落在贴近生产协作的新增能力场景，例如 provider gateway、外部目录接入、本地快照查询层、统一导出入口补齐、已有平台中的新数据源接入等。题面只保留交付合同、输入、输出和禁止事项，把具体的诊断、集成收敛和实现路径留给 solver 与 skill 自己识别。
* **Verifier 设计重点**：Verifier 应优先验证 solver 是否沿现有链路完成了能力接入，是否让 HTTP 与批量导出走同一业务口径，是否能在 alternate fixture 上保持泛化能力，以及是否保留了既有入口和完整运行方式。重点不在格式细节，而在于确认 solver 没有绕过系统边界、没有只修可见样例、也没有把任务退化成静态结果生成。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`architecture-patterns__mta-schedule-provider-gateway`
- 类别：`architecture-patterns`
- 难度：`hard`
- 绑定 Skill：`api-connector-builder`
- 输入数据参考来源：
  - `environment/workspace/data/gtfs/agency.txt`：任务内机构元数据；直接来源于 MTA static GTFS subway feed  
    【https://www.mta.info/developers】
  - `environment/workspace/data/gtfs/routes.txt`：任务内线路主数据；直接来源于 MTA static GTFS subway feed  
    【https://www.mta.info/developers】
  - `environment/workspace/data/gtfs/stops.txt`：任务内站点与父子站台关系；直接来源于 MTA static GTFS subway feed  
    【https://www.mta.info/developers】
  - `environment/workspace/data/gtfs/trips.txt`：任务内班次主数据；直接来源于 MTA static GTFS subway feed  
    【https://www.mta.info/developers】
  - `environment/workspace/data/gtfs/stop_times.txt`：任务内停靠时序；直接来源于 MTA static GTFS subway feed  
    【https://www.mta.info/developers】
  - `environment/workspace/data/gtfs/calendar.txt`：任务内服务日历；直接来源于 MTA static GTFS subway feed  
    【https://www.mta.info/developers】
  - `environment/workspace/data/gtfs/calendar_dates.txt`：任务内服务例外日历；直接来源于 MTA static GTFS subway feed  
    【https://www.mta.info/developers】
  - `environment/workspace/data/delivery_contract.yaml`：任务内字段合同；设计语义参考 GTFS Schedule Reference  
    【https://gtfs.org/】

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：官方解法已在 E2B 通过 Harbor oracle，`arch_patterns_oracle4b_20260503_005906 / task_oracle_e2b__fmQgbzp` 的 verifier reward 为 `1.0`。Oracle 口径是直接运行参考解并校验全部主测试与防作弊测试是否完整通过。
- Verifier策略：

主测试
| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| Provider 目录与可见 HTTP 查询 | 校验 provider catalog 中包含 `mta_static`，并逐条比对站点搜索、下一班次、线路服务窗口 | 先沿既有 provider/gateway 形态补齐能力，再交付给 HTTP 面 |
| 可见导出一致性 | 校验 `export_snapshot.sh` 产物与同批查询的参考计算一致 | 让批量导出和在线查询共享同一业务口径 |
| Alternate fixture 泛化 | 切换到另一组 GTFS 子集后重跑 HTTP 与导出 | 防止按可见 stop/route 做特判，要求能力可随 data root 泛化 |
| Audit compare-root 行为 | 设置 compare root 后运行 `provider_audit.sh`，校验 baseline / comparison 两侧各自命中对应数据 | 识别本地诊断入口也属于交付链路，不能只补一条主路径 |
| Same-process dual-root compare | 在同一 Node 进程内运行 `provider_compare.sh`，校验两组 mounted root 互不串用 | 共享 loader / registry 的作用域要跟 source path 对齐 |

防作弊测试
| 测试点 | 验证内容 |
| :--- | :--- |
| 输入数据保护 | 校验 GTFS 切片、seed queries、字段合同与已有 provider 数据未被改写 |
| 既有入口保护 | 校验 `start_server.sh`、`export_snapshot.sh`、`provider_audit.sh`、`provider_compare.sh` 与 `server.js` 仍保留 |
| 交付面特判规避 | 校验 `app.js`、`export_snapshot.js`、`provider_audit.js` 中未新增 `mta_static` 直写分支 |
| 可见路径硬编码规避 | 校验 `providers/mta_static/index.js` 未把可见 GTFS 目录硬编码到实现中 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值是把“先找现有 provider 接入形态、再检查共享 loader / registry 作用域、最后统一校验 HTTP / export / local toolchain”这条工作流压实；without skill 时，solver 更容易只把主查询链路补通，漏掉多 data-root 同进程场景下的共享缓存边界。

基于最近 **3 次**有效对照实验（均为跑到 task-level、存在完整 trial 结果；已排除 build/startup 失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | without Skill 的 3 次 trial 都留下了 action-level 漏项，集中表现为只补可见查询链路、漏掉 compare-root / same-process dual-root，或误删既有 provider catalog；with Skill 3 次均完整通过 |
| Agent 执行耗时 | `326.6s` | `324.7s` | 两侧耗时接近，差异主要体现在收敛质量；with Skill 略快约 `0.6%` |
| Tokens | `0.72M` | `0.72M` | token 规模接近；with Skill 平均 token 更低，约为 without Skill 的 `0.99x` |

## 📁 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── README.md
├── environment/
│   ├── Dockerfile
│   ├── skills/
│   └── workspace/
├── tests/
└── solution/
```
