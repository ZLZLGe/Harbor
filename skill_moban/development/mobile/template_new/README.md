# Mobile Template

这是面向 `mobile` 类 skill 的模板。它综合参考 SkillsMP `mobile` 类热门 skill 的共性能力：移动端交互收口、再次进入体验、缓存更新策略、快捷入口、弱网可用性，以及把公开数据驱动的应用交付成可运行结果。

## 第一部分：任务设计参考

* **Skill 价值定位**：`mobile` 类热门 skill 的共同价值，在于把移动端场景下容易分散的交付点串起来，例如狭窄视口、再次进入、状态恢复、快捷入口和资源加载策略。高质量 skill 不应直接给出答案，而应帮助 solver 更快识别要补哪条链路、哪些状态需要保留、哪些更新必须在线优先。
* **Task 目标形态**：任务适合落在通勤工具、移动工作台、轻量消费应用或安装式 Web 应用这类场景，要求 Agent 同时处理移动端交互、数据展示、再次进入和状态提示。题面应重点交代应用症状、交付合同和禁止事项，把具体实现步骤更多留给 skill 和 solver 自己识别。
* **Verifier 设计重点**：Verifier 应优先验证 solver 是否完成了移动端主链路和关键行为，避免把主要判定压力放在文案格式上。重点应覆盖当前数据更新、再次进入链路、离线说明页、快捷入口元数据、移动视口可操作性、状态提示一致性，以及对硬编码结果、输入篡改和缓存策略错误的防护。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`mobile__citibike-commuter-reentry-pwa`
- 类别：`mobile`
- 难度：`hard`
- 绑定 Skill：`progressive-web-app`
- 输入数据参考来源：
  - `environment/data/system_information.json`：任务内系统信息  
    https://gbfs.citibikenyc.com/gbfs/en/system_information.json
  - `environment/data/station_information.json`：任务内站点元数据  
    https://gbfs.citibikenyc.com/gbfs/en/station_information.json
  - `environment/data/station_status.json`：任务内站点状态数据  
    https://gbfs.citibikenyc.com/gbfs/en/station_status.json

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：oracle 会补齐移动站点看板的再次进入链路、当前数据更新链路、快捷入口元数据和状态提示，然后在单容器里重跑应用与 verifier。它关注的是完整行为是否可运行、可复测，不绑定某个文件名。
- Verifier策略：

主测试

| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 移动主流程 | 首页、搜索、详情在手机视口下可完成主要浏览流程 | 移动端主链路梳理 |
| 入口元数据 | manifest 与 service worker 已接入并在浏览器中生效 | 快捷入口与安装式 Web 交付 |
| 再次进入 | 离线后再次进入首页与已访问详情页仍可使用，并带状态提示 | 再次进入体验与保留内容 |
| 离线说明页 | 断网后可直接打开离线说明页，并给出恢复引导 | 离线导航兜底页 |
| 说明文档 | release-notes.md 与应用行为一致 | 面向交付方的结果说明 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 当前数据链路 | 本地 API 必须返回题目约定的当前快照和交付合同 |
| 替代快照 | 切换到替代站点状态后，页面必须反映新的站点数据 |
| 输入与服务完整性 | `/app/workspace/data` 和本地 API 服务代码不得变化 |

### ⚡ Skill 相关性评估

结论：强相关，但 solver 收敛仍受执行质量影响。这个任务里，Skill 的核心价值是把快捷入口、再次进入、离线说明页、在线更新和状态提示这几条移动 Web 高成本链路标准化；without Skill 会稳定丢失离线再次进入或离线说明页，而 with Skill 仍可能在站点详情链路或 manifest 合同上失手。

基于最近 **3** 次有效对照实验（均为真正跑到 task-level、存在完整 agent 轨迹；已排除启动失败类 trial）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `0%` | `33.3%` | 近 3 次有效对照里，without Skill 全部失败；失败点集中在离线再次进入首页和离线说明页，with Skill 有 1 次完整通过、2 次停在详情链路或 manifest 合同遗漏。 |
| Agent 执行耗时 | `573.2s` | `656.7s` | Without Skill 更早停在未完成状态，因此平均耗时更低；With Skill 在完整链路上投入更多诊断与实现时间。 |
| Tokens | `1.51M` | `1.61M` | Without Skill 较早收束到不完整解法，tokens 略低；With Skill 为补齐完整行为链路承担了更高上下文和实现开销。 |

## 📁 标准目录结构说明

```text
template_new/
├── instruction.md
├── task.toml
├── PLAN.json
├── environment/
│   ├── Dockerfile
│   ├── app/
│   ├── data/
│   ├── services/
│   ├── scripts/
│   └── skills/
├── tests/
└── solution/
```
