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
    11. environment/skills/ 中只允许保留当前 shipped skills。
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

    已知约束:
    ${skillConstraint}
    - 你可以从 source_task/environment/ 中选择性复制需要的输入资产到 drafts/${plan.derivedTaskId}/environment/。
    - 请基于 source_task/environment/Dockerfile 调整出新的 environment/Dockerfile。
    - environment/Dockerfile 必须保留 COPY skills /root/.codex/skills。
    - task.toml 中 metadata.id 必须等于 "${plan.derivedTaskId}"。
    - task.toml 中 metadata.name 必须显式包含 "${roleLabel}"。
    - instruction.md 不能直接明示要使用技能，也不能直接点名具体 skill 名称。
    - solution/solve.sh 和 tests/test_outputs.py 必须能验证该任务。
    - primaryOutputFile 必须为 "${plan.primaryOutputFile}"。
    - 当前 source task ID 为 "${sourceTask.sourceTaskId}"。

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
      ? `- 每个任务是否只依赖当前唯一 shipped skill：${unit.targetSkill?.name ?? "unknown"} (${unit.targetSkill?.dirName ?? "unknown"})，而不是偷偷依赖其他专用 skills`
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
      - instruction.md 是否直接明示了技能或具体 skill 名称
      - 测试是否可判定
      ${skillReviewRule}
      - 该任务是否应通过 reviewer
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
