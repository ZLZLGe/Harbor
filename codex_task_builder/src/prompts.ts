import path from "node:path";
import type { SourceTask } from "./discovery.js";
import type { DerivedTaskPlan, FamilyPlan } from "./schema.js";
import { dedent } from "./utils.js";

function renderSkills(sourceTask: SourceTask): string {
  if (sourceTask.skills.length === 0) {
    return "- 无 skills";
  }
  return sourceTask.skills
    .map((skill) => `- ${skill.name} (${skill.dirName})`)
    .join("\n");
}

export function buildTaskBuilderBrief(sourceTask: SourceTask): string {
  return dedent(`
    # Codex Task Builder Brief

    你现在位于 Harbor task builder 的 scratch workspace 中。

    源任务 ID: ${sourceTask.sourceTaskId}
    源任务目录: source_task/
    派生任务草稿目录: drafts/
    产物目录: artifacts/

    可用 skills:
    ${renderSkills(sourceTask)}

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
  `);
}

export function buildFamilyPlannerPrompt(sourceTask: SourceTask): string {
  return dedent(`
    先阅读 TASK_BUILDER_BRIEF.md，然后完整检查 source_task/ 目录。

    源任务摘要:
    - sourceTaskId: ${sourceTask.sourceTaskId}
    - difficulty: ${sourceTask.metadata.difficulty ?? "unknown"}
    - category: ${sourceTask.metadata.category ?? "unknown"}
    - tags: ${(sourceTask.metadata.tags ?? []).join(", ") || "none"}
    - skills:
    ${renderSkills(sourceTask)}

    现在只做 family 规划，不要写文件。

    规划规则:
    - 输出 4 个派生任务。
    - 4 个任务中必须恰好包含 1 个 taskRole="similar" 和 3 个 taskRole="transfer"。
    - similar 任务允许与原任务较接近，但不能只是原任务轻微改名。
    - 3 个 transfer 任务必须彼此明显不同。
    - 所有任务都必须保留源任务所在领域，并保留 shipped skills 的核心收益点。
    - derivedTaskId 必须使用 kebab-case。
    - similar 任务 derivedTaskId 必须包含 "-similar-"。
    - transfer 任务 derivedTaskId 必须包含 "-transfer-"。
    - primaryOutputFile 必须在 4 个任务之间唯一。
    - metadata.name 后续必须能显式显示 Similar/Transfer 角色。

    返回严格符合 schema 的 JSON，不要输出额外解释。
  `);
}

export function buildTaskWriterPrompt(sourceTask: SourceTask, plan: DerivedTaskPlan): string {
  const roleLabel = plan.taskRole === "similar" ? "Similar" : "Transfer";
  return dedent(`
    先阅读 TASK_BUILDER_BRIEF.md，然后阅读 source_task/ 与下面的 blueprint。

    Blueprint:
    ${JSON.stringify(plan, null, 2)}

    现在只生成一个完整派生任务，写入:
    - drafts/${plan.derivedTaskId}/

    已知约束:
    - drafts/${plan.derivedTaskId}/environment/skills/ 已预先复制 source_task/environment/skills/。
    - 你可以从 source_task/environment/ 中选择性复制需要的输入资产到 drafts/${plan.derivedTaskId}/environment/。
    - 请基于 source_task/environment/Dockerfile 调整出新的 environment/Dockerfile。
    - environment/Dockerfile 必须保留 COPY skills /root/.codex/skills。
    - task.toml 中 metadata.id 必须等于 "${plan.derivedTaskId}"。
    - task.toml 中 metadata.name 必须显式包含 "${roleLabel}"。
    - instruction.md 不能直接明示要使用技能，也不能直接点名具体 skill 名称。
    - solution/solve.sh 和 tests/test_outputs.py 必须能验证该任务。
    - primaryOutputFile 必须为 "${plan.primaryOutputFile}"。

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

export function buildReviewerPrompt(sourceTask: SourceTask, familyPlan: FamilyPlan): string {
  const taskList = familyPlan.derivedTasks
    .map((task) => `- ${task.derivedTaskId} (${task.taskRole}) -> drafts/${task.derivedTaskId}/`)
    .join("\n");

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
    - family 是否满足 1 个 similar + 3 个 transfer
    - 3 个 transfer 任务是否彼此足够不同
    - similar 任务是否足够接近原任务，能够用于测试技能有效性
    - instruction.md 是否直接明示了技能或具体 skill 名称
    - 测试是否可判定
    - 任务是否真的能从 shipped skills 受益

    返回严格符合 schema 的 JSON，不要输出额外解释。
  `);
}

export function relativeDraftPath(derivedTaskId: string): string {
  return path.posix.join("drafts", derivedTaskId);
}
