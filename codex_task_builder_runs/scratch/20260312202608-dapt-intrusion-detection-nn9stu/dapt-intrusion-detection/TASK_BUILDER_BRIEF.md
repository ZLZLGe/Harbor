    # Codex Task Builder Brief

    你现在位于 Harbor task builder 的 scratch workspace 中。

    源任务 ID: dapt-intrusion-detection
    源任务目录: source_task/
    派生任务草稿目录: drafts/
    产物目录: artifacts/

    可用 skills:
    - pcap-analysis (pcap-analysis)
- threat-detection (threat-detection)

    目标:
    1. 从 source_task/ 读取完整上下文，包括 task.toml、instruction.md、environment/、environment/skills/、solution/、tests/。
    2. 为这个源任务设计一个 4-task family。
    3. family 固定包含 1 个 similar 任务和 3 个 transfer 任务。
    4. similar 任务用于测试技能有效性，必须与原任务足够接近，但不能只是轻微改名。
    5. transfer 任务用于测试技能泛化性，三者必须彼此明显不同。
    6. instruction.md 不应直接明示技能，也不应直接点名具体 skill。
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
