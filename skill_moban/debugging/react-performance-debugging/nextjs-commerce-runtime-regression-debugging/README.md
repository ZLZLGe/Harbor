# Template Structure

这个目录是一个可复用的调试任务模板，主要结构如下。

- `instruction.md`
  任务说明。只放 solver 可见的症状、业务约束和禁止事项。
- `task.toml`
  任务元数据，包括标签、技能要求、运行入口等。
- `environment/`
  任务运行环境。
- `environment/website/`
  待修复的前端应用代码。
- `environment/api-simulator/`
  隐藏服务或模拟后端，用来提供真实下游数据和运行时依赖。
- `environment/skills/`
  任务绑定的 skill 定义和配套脚本。
- `tests/`
  verifier 与 guardrail 测试。
- `solution/`
  参考修复和 `solve.sh`。
- `validation/`
  维护侧验证材料、基准报告、轨迹摘要，以及少量必须随报告归档的外部证据。
- `PLAN.json`
  任务规划或构建过程中的结构化元信息。
