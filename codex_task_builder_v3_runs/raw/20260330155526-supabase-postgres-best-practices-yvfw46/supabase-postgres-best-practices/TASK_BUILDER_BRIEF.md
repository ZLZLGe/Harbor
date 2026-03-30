    # Codex Task Builder Brief

    你现在位于 Harbor task builder 的 scratch workspace 中。

    source skill bundle ID: supabase-postgres-best-practices
    source skill bundle 目录: source_bundle/
    Harbor builder refs: builder_refs/harbor/
    派生任务草稿目录: drafts/
    产物目录: artifacts/
    当前 family 目标数量:
    - similar: 1
    - transfer: 1
    本轮只需要补齐这些任务槽位:
    - similar: similar1
    - transfer: transfer1

    当前 shipped skills:
    - supabase-postgres-best-practices | shipped dir: supabase-postgres-best-practices | source bundle path: .
    已发布 Harbor family 目录: /home/levi/Harbor/tasks_library/auto_harbor_tasks_v3/supabase-postgres-best-practices
当前还没有已发布任务；如果该目录之后出现内容，也要把它当成历史已发布任务直接读取。

    总体目标:
    1. 先递归读取 source_bundle/ 中所有 SKILL.md 与相关 references，再阅读 builder_refs/harbor/SKILL.md 和 builder_refs/harbor/references/task-format.md。
    2. 如 final-root 中已有同 bundle 的已发布任务，必须直接读取这些任务目录，避免和它们撞题。
    3. 只补齐当前缺失的任务槽位，输出一个完整 Harbor task family 增量。
    4. 最终任务短名固定采用 similar1、similar2、transfer1、transfer2 这种命名，不要自创其他 task id。
    5. instruction.md 不要直接出现当前 environment/skills/ 里的 shipped skill 的 name、dirName 或 shipped dir name；只有这种直接点名才算技能暴露。
    6. 派生任务先写到 drafts/<task_name>/，不要直接写入最终发布目录。
    7. 每个完整任务至少包含:
       - task.toml
       - instruction.md
       - environment/Dockerfile
       - environment/skills/**
       - solution/solve.sh
       - tests/test.sh
       - tests/test_outputs.py
       - plan.json
    8. plan.json 是 planner 产物，后续 materialize/publish 也要保留，不要删除。
    9. 同一 workspace 内，后续任务生成时必须检查 drafts/ 下已经完成的 sibling tasks，并主动避免与它们在任务场景、输入资产、输出语义和测试判定方式上过于接近。
    10. environment/Dockerfile 必须保留 COPY skills /root/.codex/skills。
    11. 最终 Harbor 任务面向用户可见的文本必须使用英文，至少包括 instruction.md、task.toml 的 metadata.name 和 metadata.description。
    12. 如果 bundle 内有多个 skills，优先设计真正能从组合使用这些 skills 中受益的任务，而不是把大多数 skills 当作摆设。
    skill bundle 参考规则:
- source_bundle/ 只是技能与参考资料输入，不是任务模板；不要机械照抄其中的示例文本。
- builder_refs/harbor/ 是 Harbor task builder 参考，不是最终要随任务发布的 shipped skill。
- 你可以在 drafts/<task_name>/environment/ 下新建任务输入资产，也可以基于 source_bundle/ 中的示例、references 或脚本思路重新组织任务素材。
- 任务不得依赖 bundle 之外的 skill；如果 bundle 内有多个 skill，不要把任务写成只假设其中一个 skill 存在、其余 skill 完全无关的形态。
    关键文件职责:
- solution/solve.sh 是参考解脚本；它应基于题目提供的输入资产生成可通过测试的结果，不是给最终做题者直接照抄的答案清单。
- solution/solve.sh 不得只是复制、移动、重命名或直接输出随任务一起提供的完整标准答案文件。
- tests/test_outputs.py 只应校验 instruction.md 明确要求的输出契约、允许使用的接口和可观察结果；不要引入 instruction.md 未声明的隐藏字段、隐藏阈值、隐藏步骤、隐藏 helper 函数或隐藏导出接口。
- tests/test_outputs.py 应尽量面向结果语义而非具体实现；不要把合法解法锁死到某个内部函数名、唯一中间步骤、固定日志文本或其他未承诺的实现细节。
- 如果 tests/test_outputs.py 使用 pytest 风格测试，tests/test.sh 必须用 pytest 执行它，而不是直接 python3 /tests/test_outputs.py。
    task.toml 环境配额:
- task.toml 必须包含 [environment]。
- [environment] 必须固定为:
  - cpus = 2
  - memory_mb = 2048
  - storage_mb = 5120
  - gpus = 0
    Harbor oracle 基线:
- Harbor 会执行 /tests/test.sh 作为 verifier 入口。
- tests/test.sh 在任何写日志、CTRF 或 reward 之前，必须先执行 mkdir -p /logs/verifier。
- Harbor 只识别 /logs/verifier/reward.txt 和 /logs/verifier/reward.json；写到其他位置不会被识别。
- tests/test.sh 不得只是裸跑 pytest、python3 /tests/test_outputs.py 或其他单条测试命令后直接结束；你必须显式捕获测试退出码并据此写 reward。
- 如果使用 set -e 或 pipefail，必须确保测试失败时不会在写 reward 前提前退出；必要时局部 set +e 或采用等价写法。
- 无论测试通过还是失败，都必须稳定写出 /logs/verifier/reward.txt 或 /logs/verifier/reward.json。
- 是否联网不是默认违规项；如果 verifier 需要联网或外部服务，仍必须保证 Harbor 中可运行，并稳定落盘 reward。
- 优先单容器、轻量环境；避免明显超重的镜像构建、多服务编排、长启动链路、运行时大下载或需要长时间预热的模型/服务。
- environment/Dockerfile 不能使用本地私有镜像或只在你机器上可用的 registry；必须使用公开可复现的公共镜像，或 FROM scratch。
