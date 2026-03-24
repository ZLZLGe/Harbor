import path from "node:path";
import { getVisibleSkills, type GenerationUnit, type SkillInfo } from "./discovery.js";
import type { DerivedTaskPlan, FamilyPlan } from "./schema.js";
import { dedent } from "./utils.js";

function renderSkills(skills: SkillInfo[]): string {
  if (skills.length === 0) {
    return "- 无 skills";
  }
  return skills
    .map((skill) => `- ${skill.name} (${skill.dirName})`)
    .join("\n");
}

function renderScopeBrief(unit: GenerationUnit): string {
  if (unit.skillMode === "all") {
    return dedent(`
      当前模式: all
      当前 family 需要保留 source task 中全部 shipped skills 的核心收益点。
    `);
  }

  return dedent(`
    当前模式: per-skill
    当前目标 skill: ${unit.targetSkill?.name ?? "unknown"} (${unit.targetSkill?.dirName ?? "unknown"})
    这是严格单技能构造模式：
    - 当前 family 只允许围绕这个目标 skill 设计。
    - workspace 中唯一可用的 shipped skill 就是它。
    - 不要把任何其他 source task skill 当作背景知识、隐含前提、辅助工具或依赖。
    - 任务必须在只提供该 skill 的前提下成立。
  `);
}

function renderSourceTaskReferenceRules(assetTargetDir: string): string {
  return dedent(`
    源任务参考规则:
    - source_task/ 只是参考，不是模板；不要机械复写原任务。
    - 你可以复用、裁剪、重命名 source_task/environment/ 中的输入资产，也可以在 ${assetTargetDir} 下新建全新的输入资产。
    - 派生任务不要求保留 source task 的原始素材、文件名或目录结构；只要任务目标、验证方式和 shipped skill 约束合理即可。
  `);
}

function renderHarborOracleBaseline(): string {
  return dedent(`
    Harbor oracle 基线:
    - Harbor 会执行 /tests/test.sh 作为 verifier 入口。
    - tests/test.sh 在任何写日志、CTRF 或 reward 之前，必须先执行 mkdir -p /logs/verifier。
    - Harbor 只识别 /logs/verifier/reward.txt 和 /logs/verifier/reward.json；写到其他位置不会被识别，可能触发 RewardFileNotFoundError。
    - tests/test.sh 不得只是裸跑 pytest、python3 /tests/test_outputs.py 或其他单条测试命令后直接结束；你必须显式捕获测试退出码并据此写 reward。
    - 如果使用 set -e 或 pipefail，必须确保测试失败时不会在写 reward 前提前退出。
    - 是否联网不是默认违规项；如果 verifier 需要联网或外部服务，仍必须保证 Harbor 中可运行，并稳定落盘 reward。
    - 优先单容器、轻量环境；避免明显超重的镜像构建、多服务编排、长启动链路、运行时大下载或需要长时间预热的模型/服务。
    - 如果 source task 的旧写法与 Harbor verifier 契约冲突，以 Harbor verifier 契约为准。
  `);
}

export function buildTaskBuilderBrief(unit: GenerationUnit): string {
  const sourceTask = unit.sourceTask;
  const visibleSkills = getVisibleSkills(unit);
  return dedent(`
    # Codex Task Builder Brief

    你现在位于 Harbor task builder 的 scratch workspace 中。

    源任务 ID: ${sourceTask.sourceTaskId}
    源任务目录: source_task/
    派生任务草稿目录: drafts/
    产物目录: artifacts/

    当前 shipped skills:
    ${renderSkills(visibleSkills)}

    ${renderScopeBrief(unit)}

    目标:
    1. 从 source_task/ 读取完整上下文，包括 task.toml、instruction.md、environment/、environment/skills/、solution/、tests/。
    2. 为这个源任务设计一个 4-task family。
    3. family 固定包含 1 个 similar 任务和 3 个 transfer 任务。
    4. similar 任务用于测试当前 shipped skill 的典型用法，必须足够接近，但不能只是轻微改名。
    5. transfer 任务用于测试当前 shipped skill 在不同场景中的泛化性，三者必须彼此明显不同。
    6. instruction.md 不要直接出现当前 environment/skills/ 里的 shipped skill 的 name 或 dirName；只有这种直接点名才算技能暴露。
       - 不要把当前 shipped skill 的 name 或 dirName 写成任务提示、工具名、能力名或解题线索。
       - 不要让任务依赖 source task 中其他未随当前 per-skill workspace 提供的 skills。
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
    ${renderSourceTaskReferenceRules("drafts/<derived_task_id>/environment/")}
    ${renderHarborOracleBaseline()}
  `);
}

function renderPlannerRules(unit: GenerationUnit): string {
  if (unit.skillMode === "all") {
    return dedent(`
      - similar 任务允许与原任务较接近，但不能只是原任务轻微改名。
      - 所有任务都必须保留源任务所在领域，并保留 shipped skills 的核心收益点。
    `);
  }

  return dedent(`
    - similar 任务应贴近当前目标 skill 的典型用法，而不是简单复写原任务。
    - 所有任务都必须让当前目标 skill 成为唯一关键 shipped skill。
    - 不允许要求 workspace 中不存在的其他 source task skills。
    - transfer 任务应把当前目标 skill 迁移到彼此明显不同的场景中。
    - 每个 derivedTaskId 都必须包含当前目标 skill slug: ${unit.targetSkill?.dirName ?? "unknown"}。
    - 命名模式固定为:
      - similar: <prefix>-${unit.targetSkill?.dirName ?? "unknown"}-similar-<suffix>
      - transfer: <prefix>-${unit.targetSkill?.dirName ?? "unknown"}-transfer-<suffix>
  `);
}

export function buildFamilyPlannerPrompt(unit: GenerationUnit): string {
  const sourceTask = unit.sourceTask;
  const visibleSkills = getVisibleSkills(unit);
  return dedent(`
    先阅读 TASK_BUILDER_BRIEF.md，然后完整检查 source_task/ 目录。

    源任务摘要:
    - sourceTaskId: ${sourceTask.sourceTaskId}
    - difficulty: ${sourceTask.metadata.difficulty ?? "unknown"}
    - category: ${sourceTask.metadata.category ?? "unknown"}
    - tags: ${(sourceTask.metadata.tags ?? []).join(", ") || "none"}
    - skills:
    ${renderSkills(visibleSkills)}

    现在只做 family 规划，不要写文件。

    规划规则:
    - 输出 4 个派生任务。
    - 4 个任务中必须恰好包含 1 个 taskRole="similar" 和 3 个 taskRole="transfer"。
    - 3 个 transfer 任务必须彼此明显不同。
    ${renderPlannerRules(unit)}
    - derivedTaskId 必须使用 kebab-case。
    - similar 任务 derivedTaskId 必须包含 "-similar-"。
    - transfer 任务 derivedTaskId 必须包含 "-transfer-"。
    - primaryOutputFile 必须在 4 个任务之间唯一。
    - metadata.name 后续必须能显式显示 Similar/Transfer 角色。
    - 只规划那些能在 Harbor 常规 build/start/verify 时限内完成的任务。
    - source_task/ 只是参考，不是模板；必要时可以新增全新输入资产，而不是机械复用原始素材。
    - family 内任务应通过任务目标、输入资产、输出语义和验证方式拉开差异，不要只靠轻微改名或改参数区分。
    - 如果规划需要联网或外部服务，不要把它视为默认违规项，但仍要保证 Harbor 中可运行，且 verifier 能稳定写 reward。
    返回严格符合 schema 的 JSON，不要输出额外解释。
  `);
}

export function buildTaskWriterPrompt(unit: GenerationUnit, plan: DerivedTaskPlan): string {
  const roleLabel = plan.taskRole === "similar" ? "Similar" : "Transfer";
  const sourceTask = unit.sourceTask;
  const skillConstraint =
    unit.skillMode === "per-skill"
      ? dedent(`
        - drafts/${plan.derivedTaskId}/environment/skills/ 中只有一个 shipped skill：${unit.targetSkill?.name ?? "unknown"} (${unit.targetSkill?.dirName ?? "unknown"})。
        - 你必须保持只有这一个 shipped skill，不要复制、引用或假设其他 source task skills 存在。
        - 这个任务必须在只提供该 skill 的前提下成立。
      `)
      : dedent(`
        - drafts/${plan.derivedTaskId}/environment/skills/ 已预先复制 source_task/environment/skills/。
      `);
  return dedent(`
    先阅读 TASK_BUILDER_BRIEF.md，然后阅读 source_task/ 与下面的 blueprint。

    Blueprint:
    ${JSON.stringify(plan, null, 2)}

    现在只生成一个完整派生任务，写入:
    - drafts/${plan.derivedTaskId}/

    写作前必须先检查当前 workspace 的 drafts/ 目录：
    - 把 drafts/${plan.derivedTaskId}/ 视为当前任务目录，不要把它当成已存在 sibling task。
    - 把 drafts/ 下其他已经有内容的 sibling task 目录视为之前已经生成好的任务。
    - 对每个已有 sibling task，优先阅读：
      - drafts/<sibling_task_id>/PLAN.json
      - drafts/<sibling_task_id>/instruction.md
      - drafts/<sibling_task_id>/task.toml
    - 如有必要，再补充检查：
      - drafts/<sibling_task_id>/tests/test_outputs.py
      - drafts/<sibling_task_id>/environment/ 下的输入资产
    - 基于这些已有 drafts，主动避免当前任务与前面任务在以下方面过于接近：
      - 任务场景或叙事
      - 输入资产类型、结构或素材来源
      - 输出物的语义目标
      - 测试判定方式
    - 如果发现当前 blueprint 对应的任务与已有 drafts 明显重合，你可以调整当前任务的具体情境、输入资产、验证方式和 instruction 文案来拉开差异。
    - 但你不能修改 blueprint 中已经固定的核心约束：derivedTaskId、taskRole、primaryOutputFile、source_task_id，以及当前 skill scope。
    - 如果 drafts/ 中还没有其他已生成 sibling tasks，就按正常流程继续写当前任务。

    已知约束:
    ${skillConstraint}
    ${renderSourceTaskReferenceRules(`drafts/${plan.derivedTaskId}/environment/`)}
    - 请基于 source_task/environment/Dockerfile 调整出新的 environment/Dockerfile；必要时可以做实质性改写。
    - environment/Dockerfile 必须保留 COPY skills /root/.codex/skills。
    - task.toml 中 metadata.id 必须等于 "${plan.derivedTaskId}"。
    - task.toml 中 metadata.name 必须显式包含 "${roleLabel}"。
    - task.toml 的 [metadata] 至少必须包含这些字段:
      - id = "${plan.derivedTaskId}"
      - name = <显式包含 ${roleLabel} 的标题>
      - description = <非空单句摘要，描述任务目标和输出>
      - author_name = <非空字符串>
      - author_email = <非空字符串>
      - difficulty = <非空字符串>
      - category = <非空字符串>
      - tags = <至少 1 个元素的数组>
      - primary_output_file = "${plan.primaryOutputFile}"
      - source_task_id = "${sourceTask.sourceTaskId}"
      - task_role = "${plan.taskRole}"
    - 如果 task.toml 缺少上述任一 metadata 字段，或者关键字段值不匹配，该任务会在 static validate 阶段直接失败，不能发布。
    - instruction.md 不要直接出现当前 environment/skills/ 里的 shipped skill 的 name 或 dirName；只有这种直接点名才算技能暴露。
    - solution/solve.sh 和 tests/test_outputs.py 必须能验证该任务。
    - primaryOutputFile 必须为 "${plan.primaryOutputFile}"。
    - 当前 source task ID 为 "${sourceTask.sourceTaskId}"。
    - 下面这些 Harbor oracle 约束默认优先于 source task 中较旧或较松散的写法：
      - Harbor 会执行 /tests/test.sh 作为 verifier 入口。
      - tests/test.sh 在任何写日志、CTRF 或 reward 之前，必须先执行 mkdir -p /logs/verifier。
      - Harbor 只识别 /logs/verifier/reward.txt 和 /logs/verifier/reward.json；写到其他位置不会被识别，可能触发 RewardFileNotFoundError。
      - tests/test.sh 不得只是裸跑 pytest、python3 /tests/test_outputs.py 或其他单条测试命令后直接结束；你必须显式捕获测试退出码并据此写 reward。
      - 如果使用 set -e 或 pipefail，必须确保测试失败时不会在写 reward 前提前退出；必要时对测试命令局部 set +e 或采用等价写法。
      - 无论测试通过还是失败，都必须稳定写出 /logs/verifier/reward.txt 或 /logs/verifier/reward.json；推荐通过写 1，失败写 0。
      - 应优先采用这个顺序：先 mkdir -p /logs/verifier，再运行测试并捕获退出码，再写 reward，最后再复制可选 artifacts。
      - 是否联网不是默认违规项；如果 verifier 需要联网或外部服务，仍必须保证 Harbor 中可运行，并稳定落盘 reward。
      - environment/Dockerfile 应尽量保持轻量、稳定、可在 Harbor 中快速 build/start；避免明显超重的镜像、长启动链路、运行时大下载或多服务编排。
      - 不要把 Harbor 关键 verifier 依赖留到 tests/test.sh 中临时安装；必须依赖的核心系统包、运行库或重量级 Python 包应尽量前置到 environment/Dockerfile。
      - environment/Dockerfile 默认只保留 Harbor 实际需要的 skill copy：必须保留 COPY skills /root/.codex/skills，不要额外复制到 /root/.claude/skills、/root/.gemini/skills 等其他代理目录，除非任务在 Harbor 中确实需要。

    你需要创建或更新这些文件:
    - task.toml
    - instruction.md
    - environment/Dockerfile
    - environment/ 下必要输入资产
    - solution/solve.sh
    - tests/test.sh
    - tests/test_outputs.py

    写完文件后，返回严格符合 schema 的 JSON，总结你写入了哪些文件。
  `);
}
export function buildReviewerPrompt(unit: GenerationUnit, familyPlan: FamilyPlan): string {
  const taskList = familyPlan.derivedTasks
    .map((task) => `- ${task.derivedTaskId} (${task.taskRole}) -> drafts/${task.derivedTaskId}/`)
    .join("\n");
  const skillReviewRule =
    unit.skillMode === "per-skill"
      ? `- 每个任务是否只依赖当前唯一 shipped skill：${unit.targetSkill?.name ?? "unknown"} (${unit.targetSkill?.dirName ?? "unknown"})，如果完成任务除了当前 shipped skill 之外，还需要依赖 source task 其他未随当前 per-skill workspace一起提供的 skills，就直接判定失败`
      : `- 任务是否真的能从 shipped skills 受益`;

  return dedent(`
    不要修改任何文件。你现在只负责审稿。

    先阅读:
    - TASK_BUILDER_BRIEF.md
    - source_task/
    - drafts/

    当前 family 规划:
    ${JSON.stringify(familyPlan, null, 2)}

    当前 drafts:
    ${taskList}

    审查目标:
    - 对每个任务分别判断：
      - instruction.md 是否直接出现了当前 environment/skills/ 里的 shipped skill 的 name 或 dirName；只有这种直接点名才算技能暴露
      - source_task/ 是否只是参考，而不是机械复写源任务
      - 是否合理复用或新建输入资产，并与同 family 其他任务拉开差异
      - 测试是否可判定，尤其要检查：
        - tests/test.sh 是否先创建 /logs/verifier
        - reward 是否写到 /logs/verifier/reward.txt 或 /logs/verifier/reward.json，而不是写到其他目录
        - 是否稳定写出 reward.txt/reward.json，而不是裸跑测试后直接结束
        - 是否存在 set -e/pipefail 导致写 reward 前提前退出的路径
        - 如果任务使用联网或外部服务，是否仍能在 Harbor 中稳定运行并稳定写 reward
        - Dockerfile / test harness 是否明显过重，容易导致 Harbor build/start timeout
        - environment/Dockerfile 是否只保留 Harbor 需要的 skill copy，避免无谓复制到其他 agent 目录
      ${skillReviewRule}
      - 该任务是否应通过 reviewer
      - 只要命中上述任一 Harbor testability 问题，就将 testabilityPass 设为 false，并在 issues 中直接点明具体问题
    - 对 family 整体单独给出观察：
      - family 是否满足 1 个 similar + 3 个 transfer
      - 3 个 transfer 任务是否彼此足够不同
      - similar 任务是否足够贴近当前 shipped skill 的典型用法

    返回格式要求:
    - taskResults 中必须覆盖 familyPlan.derivedTasks 里的每一个 derivedTaskId
    - taskResults[].pass=false 只表示该任务不应发布，不表示整组 family 失败
    - familyObservations 只记录 family 级观察，不决定单个任务是否发布

    返回严格符合 schema 的 JSON，不要输出额外解释。
  `);
}

export function relativeDraftPath(derivedTaskId: string): string {
  return path.posix.join("drafts", derivedTaskId);
}
