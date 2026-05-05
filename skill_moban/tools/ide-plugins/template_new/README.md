# IDE Plugins Template

这是面向 IDE Plugins 类 skill 的模板。它综合参考 SkillsMP IDE Plugins 类热门 skill 的共性能力：扩展脚手架整理、本地化资源布置、命令与视图接线、引导内容配置、导出产物生成与 VSIX 交付。

## 第一部分：任务设计参考

* **Skill 价值定位**：IDE Plugins 类热门 skill 的核心价值，在于帮助 solver 快速识别一个编辑器扩展的交付面并把这些面接齐。对于本地化相关任务，常见关键点包括贡献项文案、运行态消息、引导内容和打包产物是否一起到位。
* **Task 目标形态**：任务宜放在“完成一项扩展交付”这类场景里，例如版本简报扩展、内部导航扩展、团队脚手架扩展或工作区辅助扩展。题面保留输入、输出、业务约束和禁止事项，把具体的扩展本地化接线留给 solver 和 skill 自己识别。
* **Verifier 设计重点**：Verifier 应优先验证扩展交付是否完整，而不是只看某几个文件有没有被编辑。重点包括多语言贡献项是否覆盖、运行态消息是否可用、引导内容是否随语言切换、导出产物是否跟随输入变化，以及 VSIX 中是否带上所需资源。

## 第二部分：示例任务

### 📌 任务元数据

- 任务 ID：`ide-plugins__vscode-release-briefing-localization`
- 类别：`IDE Plugins`
- 难度：`hard`
- 绑定 Skill：`vscode-ext-localization`
- 输入数据参考来源：
  - `environment/data/releases/1.87.json`：任务内 VS Code 1.87 更新快照；内容整理自官方 2024 年 2 月更新说明  
    【https://code.visualstudio.com/updates/v1_87】
  - `environment/data/releases/1.88.json`：任务内 VS Code 1.88 更新快照；内容整理自官方 2024 年 3 月更新说明  
    【https://code.visualstudio.com/updates/v1_88】
  - `environment/data/releases/1.89.json`：任务内 VS Code 1.89 更新快照；内容整理自官方 2024 年 4 月更新说明  
    【https://code.visualstudio.com/updates/v1_89】
  - `environment/data/locales/*/briefing_terms.json`：任务内多语言术语与文案结构；设计形态参考 VS Code 扩展本地化指南与公开语言资源仓库  
    【https://code.visualstudio.com/api/working-with-extensions/localization】  
    【https://github.com/microsoft/vscode-loc】

### 📊 验证与测试指标（Oracle & Verifier）

- Oracle：官方解法会沿着现有扩展入口补齐版本浏览、简报导出、本地化资源接线和打包流程，让三种语言的贡献项、引导内容、运行态消息和 Markdown 产物一起通过。题目里的工作区、输入数据和 VSIX 产物会按同一条链路收敛。
- Verifier策略：

主测试

| 测试点 | 验证内容 | 对应skill内化点 |
| :--- | :--- | :--- |
| 默认请求导出 | 校验默认请求可产出三份多语言简报和一个 VSIX | 本地化导出与打包闭环 |
| Manifest 覆盖 | 校验命令、视图、配置和引导入口都具备三语言覆盖 | `package.json` 贡献项本地化 |
| Walkthrough 覆盖 | 校验引导内容的多语言资源路径与内容都可用 | 引导内容本地化 |
| Runtime 覆盖 | 校验运行态消息包在三种语言下都齐全 | `bundle.l10n` 资源接线 |
| 变体请求泛化 | 校验换一份请求后简报内容跟随变化 | 避免硬编码，保持输入驱动 |

防作弊测试

| 测试点 | 验证内容 |
| :--- | :--- |
| 输入文件保护 | 校验更新快照、语言素材和请求文件 hash 保持不变 |
| 变体请求回归 | 切换另一份请求后结果必须随之变化 |
| 产物再生成 | 清空输出目录后重新执行，结果仍需完整生成 |

### ⚡ Skill 相关性评估

结论：强相关。这个任务里，`vscode-ext-localization` 的核心价值是帮助 solver 把一个 VS Code 扩展的多语言交付面一次性看全，并沿着现有扩展入口把这些面接齐。题目把多语言命令、视图、引导内容、运行态消息和导出简报放在同一条交付链路上，可以有效拦住只做单一语言导出或只补局部文案的解法。

基于最近 **待补** 次有效对比实验（完成 `template_new` 的 E2B 对照实验后填写）：

| 维度 | Without Skill | With Skill | 结果对比 |
| :--- | :--- | :--- | :--- |
| 通过率 | `待补` | `待补` | `待补` |
| Agent 执行耗时 | `待补` | `待补` | `待补` |
| Tokens | `待补` | `待补` | `待补` |

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
└── solution/
```
