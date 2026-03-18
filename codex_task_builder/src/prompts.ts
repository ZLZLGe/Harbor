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
    - 你可以从 source_task/environment/ 中选择性复制需要的输入资产到 drafts/${plan.derivedTaskId}/environment/。
    - 请基于 source_task/environment/Dockerfile 调整出新的 environment/Dockerfile。
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
    - instruction.md 应尽量避免直接明示要使用技能，也不要引入 source task 没写过的具体 skill 名称。
    - 以 source_task/instruction.md 为基线：如果 source task 本身已经明确点出同一技术或技能名称，派生任务沿用同等级别表述可以接受，但不要写得比 source task 更直接。
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
      - 先把 source_task/instruction.md 当作基线，而不是脱离 source task 单独判定
      - instruction.md 是否比 source_task/instruction.md 更直接地明示了技能，或引入了 source task 未出现的具体 skill 名称
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
