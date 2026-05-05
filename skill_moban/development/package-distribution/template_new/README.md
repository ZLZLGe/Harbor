# Package Distribution Template

这是面向 Package Distribution 类 skill 的模板。它综合参考 SkillsMP Package Distribution 类热门 skill 的共性能力：包结构整理、构建后端选择、CLI 入口暴露、发布前元数据校验、分发产物生成，以及安装态资源可用性验证。

## 第一部分：任务设计参考

* **Skill 价值定位**：Package Distribution 类热门 skill 的核心价值，是把“仓库里有可运行代码”推进到“可以作为标准软件包被构建、安装、调用和交付”。它要求 solver 同时处理包结构、构建元数据、入口点、资源打包、版本约束和分发产物校验，并避免只补单个脚本或单个配置文件。
* **Task 目标形态**：任务应落在发布准备或分发整理场景里，例如内部 CLI 工具、SDK、框架扩展、数据处理库、自动化组件等。题面主要交代输入、交付产物、运行约束和禁止事项，把具体的打包路线、后端选择和资源收录策略留给 solver 自己识别。
* **Verifier 设计重点**：Verifier 应优先验证安装态行为，弱化对源码态表象的依赖，包括 wheel 与 sdist 是否齐备、控制台入口和 `python -m` 是否都可用、安装后的自动化 entry point 是否可被发现、包根级 API 是否能被下游直接导入、类型信息是否随包分发，以及交付清单是否和产物一致。防作弊点应覆盖硬编码输出、绕开构建产物、只在源码目录下可运行和篡改输入数据等问题。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`package_distribution__pkgmeta_kit_release_candidate`
- 类别：Package Distribution
- 难度：`hard`
- 绑定 Skill：`python-pypi-package-builder`
- 输入数据参考来源：
  - `environment/workspace/pkgmeta-kit/data/licenses.json`：任务内许可证目录快照，直接来源于  
    https://github.com/spdx/license-list-data/blob/main/json/licenses.json
  - `environment/workspace/pkgmeta-kit/data/trove_classifiers.py`：任务内 classifier 目录快照，直接来源于  
    https://github.com/pypa/trove-classifiers/blob/main/src/trove_classifiers/__init__.py
  - `environment/workspace/pkgmeta-kit/seed_sampleproject_README.md`：包 README 结构参考，直接来源于  
    https://github.com/pypa/sampleproject/blob/main/README.md

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：官方解会把题目中的内部工具仓整理为标准 Python 包，生成可安装的 wheel 与 sdist，补齐 `pkgmeta-kit` CLI、`python -m pkgmeta_kit` 入口，以及供下游自动化发现的安装态 entry point，并在安装态下证明数据目录仍可被程序读取。
- Verifier策略：

主测试

| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 双产物交付 | 校验仓库根目录能产出 wheel 与 sdist，且 `release_manifest.json` 与实际产物一致 | 标准打包链路、交付清单维护 |
| wheel 安装后的 CLI 契约 | 校验安装 wheel 后，`pkgmeta-kit` 命令在脱离源码目录的临时环境中仍能输出正确结果 | console script 暴露、安装态可运行性 |
| wheel 安装后的模块入口契约 | 校验 `python -m pkgmeta_kit` 可用，且与 CLI 契约一致 | 模块入口组织、包执行入口 |
| 安装态自动化发现 | 校验安装后的包能被 `importlib.metadata` 发现指定 entry point，且返回约定快照 | `[project.entry-points]`、安装态集成能力 |
| 安装态公共 API | 校验安装后的包根级 `pkgmeta_kit` 可被直接导入，并向下游暴露约定函数 | `__init__.py`、公共 API 出口整理 |
| sdist 安装一致性 | 校验从 `dist/*.tar.gz` 安装到 fresh venv 后，CLI、模块入口与包根级 API 仍满足同一契约 | source distribution、双产物一致性 |
| 资源随包分发 | 校验许可证与 classifier 数据文件被包含进 wheel 与 sdist，并能在安装态读取 | package data 收录、资源访问路径 |
| 类型能力随包分发 | 校验 fresh venv 中的 typed consumer 能识别安装包并通过严格类型检查 | PEP 561、`py.typed`、类型分发完整性 |
| 分发元数据对齐 | 校验 manifest、wheel metadata 与已声明入口保持一致 | `pyproject.toml`、分发元数据对齐 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 动态查询泛化 | 使用题面示例外的许可证 ID 和 classifier 前缀重新调用已安装程序，拦截只对固定示例成立的硬编码实现 |
| 输入完整性 | 校验提供的 `licenses.json` 与 `trove_classifiers.py` 哈希保持不变，防止通过篡改输入规避任务 |
| 产物来源一致性 | 校验程序行为来自安装后的 wheel 与 sdist，避免源码目录旁路执行或预生成静态答案 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，Skill 的核心价值集中在 Python 包结构决策、构建元数据补齐、wheel 与 sdist 双产物校验、安装态资源访问，以及安装后 entry point 的暴露方式。最近这轮迭代把关键差异转到安装态自动化发现与类型分发能力后，with Skill 仍能稳定通过，without Skill 更容易漏掉完整分发链路中的关键动作。

基于最近 **3** 次有效对比实验（均真正跑到 task-level、存在完整 agent 轨迹；已排除 build cancelled 等启动异常 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `100%` | 最近 3 次有效对照里，without Skill 都留下至少 1 项 verifier 失败；with Skill 都完成了全部测试点 |
| Agent 执行耗时 | `273.0s` | `326.1s` | With Skill 的执行更完整，额外覆盖了打包与安装态核验路径，因此平均耗时更高 |
| Tokens | `771,132` | `1,083,635` | With Skill 在这组实验中为了完成更完整的分发链路校验，平均 token 开销更高（含 cache token） |

## 📁 标准目录结构说明

```text
模板任务：
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
