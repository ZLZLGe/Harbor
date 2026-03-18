    # Codex Task Builder Brief

    你现在位于 Harbor task builder 的 scratch workspace 中。

    源任务 ID: earthquake-plate-calculation
    源任务目录: source_task/
    派生任务草稿目录: drafts/
    产物目录: artifacts/

    当前 shipped skills:
    - geospatial-analysis (geospatial-analysis)

    当前模式: per-skill
当前目标 skill: geospatial-analysis (geospatial-analysis)
这是严格单技能构造模式：
- 当前 family 只允许围绕这个目标 skill 设计。
- workspace 中唯一可用的 shipped skill 就是它。
- 不要把任何其他 source task skill 当作背景知识、隐含前提、辅助工具或依赖。
- 任务必须在只提供该 skill 的前提下成立。

    目标:
    1. 从 source_task/ 读取完整上下文，包括 task.toml、instruction.md、environment/、environment/skills/、solution/、tests/。
    2. 为这个源任务设计一个 4-task family。
    3. family 固定包含 1 个 similar 任务和 3 个 transfer 任务。
    4. similar 任务用于测试当前 shipped skill 的典型用法，必须足够接近，但不能只是轻微改名。
    5. transfer 任务用于测试当前 shipped skill 在不同场景中的泛化性，三者必须彼此明显不同。
    6. instruction.md 应尽量避免直接明示技能，也不应新增 source task 中没有的具体 skill 点名。
       - 以 source_task/instruction.md 为基线判断。
       - 如果 source task 本身已经直接写出某个技术或技能名称，派生任务沿用同等级别的表述不算违规。
       - 只有当派生任务比 source task 更直接地提示技能，或引入 source task 没写过的新 skill 名称时，才算越界。
    7. 每个完整任务必须是 Harbor 风格目录，至少包含:
       - task.toml
       - instruction.md
       - environment/Dockerfile
       - environment/skills/**
       - solution/solve.sh
       - tests/test.sh
       - tests/test_outputs.py
    8. 派生任务先写到 drafts/<derived_task_id>/，不要直接写入 integrated_tasks/。
    9. environment/Dockerfile 必须保留 COPY skills /root/.codex/skills。
    10. 任务命名必须显式显示 Similar 或 Transfer 角色。
    11. environment/skills/ 中只允许保留当前 shipped skills。
    12. 同一 scratch workspace 内，后续任务生成时必须检查 drafts/ 下已经完成的 sibling tasks，并主动避免与它们在任务场景、输入资产、输出物语义和测试判定方式上过于接近。
       - 这里只需要关注当前 workspace 的 drafts/，不需要查看更早之前生成的 integrated_tasks/ 或 manifest。
