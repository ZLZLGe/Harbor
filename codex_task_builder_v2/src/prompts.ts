import path from "node:path";
import { getVisibleSkills, type GenerationUnit, type PublishedTaskInfo, type SkillInfo } from "./discovery.js";
import type { DerivedTaskPlan, FamilyPlan } from "./schema.js";
import { dedent } from "./utils.js";

function renderSkills(skills: SkillInfo[]): string {
  if (skills.length === 0) {
    return "- 无 skills";
  }
  return skills.map((skill) => `- ${skill.name} (${skill.dirName})`).join("\n");
}

function renderScopeBrief(unit: GenerationUnit): string {
  if (unit.skillMode === "all") {
    return dedent(`
      当前模式: all
      当前 family 需要保留 source task 中全部 shipped skills 的核心收益点。
      最终任务目录层固定使用 all-skills。
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

function renderTaskSlotList(taskRole: "similar" | "transfer", ordinals: number[]): string {
  if (ordinals.length === 0) {
    return "none";
  }
  return ordinals.map((ordinal) => `${taskRole}${ordinal}`).join(", ");
}

function renderPublishedTaskEntry(task: PublishedTaskInfo): string {
  return dedent(`
    - ${task.derivedTaskId}
      task dir: ${task.taskDir}
      read first: ${task.planPath}
      then read: ${task.instructionPath}
      then read: ${task.taskTomlPath}
      optional: ${task.testOutputsPath}
      optional assets dir: ${task.environmentDir}
  `);
}

function renderPublishedTaskReference(unit: GenerationUnit): string {
  if (unit.publishedTasks.length === 0) {
    return dedent(`
      已发布 Harbor family 目录: ${unit.finalFamilyDir || "unknown"}
      当前还没有已发布任务；如果该目录之后出现内容，也要把它当成历史已发布任务直接读取。
    `);
  }

  return dedent(`
    已发布 Harbor family 目录: ${unit.finalFamilyDir}
    这些任务已经发布到 final-root。planner、writer、reviewer 都必须直接读取这些绝对路径，不要依赖人工整理的摘要：
    ${unit.publishedTasks.map((task) => renderPublishedTaskEntry(task)).join("\n")}
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
    - Harbor 只识别 /logs/verifier/reward.txt 和 /logs/verifier/reward.json；写到其他位置不会被识别。
    - tests/test.sh 不得只是裸跑 pytest、python3 /tests/test_outputs.py 或其他单条测试命令后直接结束；你必须显式捕获测试退出码并据此写 reward。
    - 如果使用 set -e 或 pipefail，必须确保测试失败时不会在写 reward 前提前退出；必要时局部 set +e 或采用等价写法。
    - 无论测试通过还是失败，都必须稳定写出 /logs/verifier/reward.txt 或 /logs/verifier/reward.json。
    - 是否联网不是默认违规项；如果 verifier 需要联网或外部服务，仍必须保证 Harbor 中可运行，并稳定落盘 reward。
    - 优先单容器、轻量环境；避免明显超重的镜像构建、多服务编排、长启动链路、运行时大下载或需要长时间预热的模型/服务。
    - environment/Dockerfile 不能使用本地私有镜像或只在你机器上可用的 registry；必须使用公开可复现的公共镜像，或 FROM scratch。
  `);
}

function renderTaskArtifactContracts(): string {
  return dedent(`
    关键文件职责:
    - solution/solve.sh 是参考解脚本；它应基于题目提供的输入资产生成可通过测试的结果，不是给最终做题者直接照抄的答案清单。
    - solution/solve.sh 不得只是复制、移动、重命名或直接输出随任务一起提供的完整标准答案文件。
    - tests/test_outputs.py 只应校验 instruction.md 明确要求的输出契约、允许使用的接口和可观察结果；不要引入 instruction.md 未声明的隐藏字段、隐藏阈值、隐藏步骤、隐藏 helper 函数或隐藏导出接口。
    - tests/test_outputs.py 应尽量面向结果语义而非具体实现；不要把合法解法锁死到某个内部函数名、唯一中间步骤、固定日志文本或其他未承诺的实现细节。
    - 如果 tests/test_outputs.py 使用 pytest 风格测试，tests/test.sh 必须用 pytest 执行它，而不是直接 python3 /tests/test_outputs.py。
  `);
}

function renderEnvironmentResourceRules(): string {
  return dedent(`
    task.toml 环境配额:
    - task.toml 必须包含 [environment]。
    - [environment] 必须固定为:
      - cpus = 2
      - memory_mb = 2048
      - storage_mb = 5120
      - gpus = 0
  `);
}

export function buildRoleDisplayName(plan: DerivedTaskPlan): string {
  return `${plan.taskRole === "similar" ? "Similar" : "Transfer"} ${plan.roleOrdinal}`;
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
    当前 family 目标数量:
    - similar: ${unit.similarCount}
    - transfer: ${unit.transferCount}
    本轮只需要补齐这些任务槽位:
    - similar: ${renderTaskSlotList("similar", unit.pendingSimilarOrdinals)}
    - transfer: ${renderTaskSlotList("transfer", unit.pendingTransferOrdinals)}

    当前 shipped skills:
    ${renderSkills(visibleSkills)}

    ${renderScopeBrief(unit)}
    ${renderPublishedTaskReference(unit)}

    总体目标:
    1. 从 source_task/ 读取完整上下文，包括 task.toml、instruction.md、environment/、environment/skills/、solution/、tests/。
    2. 如 final-root 中已有同 family 的已发布任务，必须直接读取这些任务目录，避免和它们撞题。
    3. 只补齐当前缺失的任务槽位，输出一个完整 Harbor task family 增量。
    4. 最终任务短名固定采用 similar1、similar2、transfer1、transfer2 这种命名，不要自创其他 task id。
    5. instruction.md 不要直接出现当前 environment/skills/ 里的 shipped skill 的 name 或 dirName；只有这种直接点名才算技能暴露。
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
    ${renderSourceTaskReferenceRules("drafts/<task_name>/environment/")}
    ${renderTaskArtifactContracts()}
    ${renderEnvironmentResourceRules()}
    ${renderHarborOracleBaseline()}
  `);
}

export function buildFamilyPlannerPrompt(unit: GenerationUnit): string {
  const sourceTask = unit.sourceTask;
  const visibleSkills = getVisibleSkills(unit);

  return dedent(`
    先阅读 TASK_BUILDER_BRIEF.md，然后完整检查 source_task/ 目录；如果 final-root 已有同 family 任务，也必须直接读取这些已发布任务目录。

    源任务摘要:
    - sourceTaskId: ${sourceTask.sourceTaskId}
    - difficulty: ${sourceTask.metadata.difficulty ?? "unknown"}
    - category: ${sourceTask.metadata.category ?? "unknown"}
    - tags: ${(sourceTask.metadata.tags ?? []).join(", ") || "none"}
    - skills:
    ${renderSkills(visibleSkills)}
    已发布 Harbor family 目录: ${unit.finalFamilyDir || "unknown"}
    当前已发布任务: ${unit.publishedTasks.length === 0 ? "none" : unit.publishedTasks.map((task) => task.derivedTaskId).join(", ")}
    本轮需要补齐的 similar 槽位: ${renderTaskSlotList("similar", unit.pendingSimilarOrdinals)}
    本轮需要补齐的 transfer 槽位: ${renderTaskSlotList("transfer", unit.pendingTransferOrdinals)}

    当前只做 family 规划，不要写文件。

    规划要求:
    - familyTheme、每个任务的 title、goal、category、skillBenefitRationale 都必须用英文书写，避免后续 writer 产出中文任务描述。
    - 返回 similarTasks 数组，长度必须恰好为 ${unit.pendingSimilarOrdinals.length}。
    - 返回 transferTasks 数组，长度必须恰好为 ${unit.pendingTransferOrdinals.length}。
    - 任务短名会由程序映射到当前缺失槽位 ${renderTaskSlotList("similar", unit.pendingSimilarOrdinals)} / ${renderTaskSlotList("transfer", unit.pendingTransferOrdinals)}，所以你不要输出 derivedTaskId。
    - family 内 primaryOutputFile 必须全局唯一。
    - 所有任务必须足够轻量，能在 Harbor 常规 build/start/verify 时限内完成。
    - family 内任务应通过任务目标、输入资产、输出语义和验证方式拉开差异，不要只靠轻微改名或改参数区分。
    - source_task/ 只是参考，不是模板；必要时可以新增全新输入资产，而不是机械复用原始素材。
    - 如果 final-root 已有同 family 的已发布任务，必须先直接读取它们，并主动避免与这些历史任务在任务场景、输入资产、输出语义和测试判定方式上过于接近。
    - 如果规划需要联网或外部服务，不要把它视为默认违规项，但仍要保证 Harbor 中可运行，且 verifier 能稳定写 reward。
    - 类别、难度、目标输出、技能收益说明都必须具体，不要写空泛占位。
    ${unit.skillMode === "all"
      ? dedent(`
        - all 模式下，family 必须保留全部 shipped skills 的核心收益点。
        - similar 任务允许与原任务较接近，但不能只是原任务轻微改名。
      `)
      : dedent(`
        - per-skill 模式下，family 只允许围绕当前目标 skill 设计：${unit.targetSkill?.name ?? "unknown"} (${unit.targetSkill?.dirName ?? "unknown"})。
        - 任务不得依赖当前 workspace 中不存在的其他 source task skills。
        - transfer 任务必须把当前 skill 迁移到彼此明显不同的场景中。
      `)}

    返回严格符合 schema 的 JSON，不要输出额外解释。
  `);
}

export function buildTaskWriterPrompt(unit: GenerationUnit, plan: DerivedTaskPlan): string {
  const sourceTask = unit.sourceTask;
  const roleDisplayName = buildRoleDisplayName(plan);
  const skillConstraint =
    unit.skillMode === "per-skill"
      ? dedent(`
        - drafts/${plan.derivedTaskId}/environment/skills/ 中只能保留一个 shipped skill：${unit.targetSkill?.name ?? "unknown"} (${unit.targetSkill?.dirName ?? "unknown"})。
        - 你必须保持只有这一个 shipped skill，不要复制、引用或假设其他 source task skills 存在。
        - 这个任务必须在只提供该 skill 的前提下成立。
      `)
      : dedent(`
        - drafts/${plan.derivedTaskId}/environment/skills/ 已预先复制 source_task/environment/skills/。
      `);

  return dedent(`
    先阅读 TASK_BUILDER_BRIEF.md，然后阅读 source_task/、当前 task 的 plan.json blueprint、已有 sibling drafts，以及 final-root 下已发布的同 family 任务。

    当前 task blueprint:
    ${JSON.stringify(plan, null, 2)}

    现在只生成一个完整派生任务，写入:
    - drafts/${plan.derivedTaskId}/

    写作前必须先检查当前 workspace 的 drafts/ 目录：
    - 把 drafts/${plan.derivedTaskId}/ 视为当前任务目录，不要把它当成已存在 sibling task。
    - 把 drafts/ 下其他已经有内容的 sibling task 目录视为之前已经生成好的任务。
    - 对每个已有 sibling task，优先阅读：
      - drafts/<sibling_task>/plan.json
      - drafts/<sibling_task>/instruction.md
      - drafts/<sibling_task>/task.toml
    - 如有必要，再补充检查：
      - drafts/<sibling_task>/tests/test_outputs.py
      - drafts/<sibling_task>/environment/ 下的输入资产
    - 主动避免与已有 sibling task 在任务场景、输入资产、输出物语义和测试判定方式上过于接近。
    - 还必须检查 final-root 中已经发布的同 family 任务；优先阅读：
      - <published_task>/plan.json
      - <published_task>/instruction.md
      - <published_task>/task.toml
    - 如有必要，再补充检查：
      - <published_task>/tests/test_outputs.py
      - <published_task>/environment/
    - 主动避免与已发布任务在任务场景、输入资产、输出物语义和测试判定方式上过于接近。
    - 已发布 Harbor family 目录: ${unit.finalFamilyDir || "unknown"}
    - 已发布任务列表:
    ${unit.publishedTasks.length === 0 ? "- none" : unit.publishedTasks.map((task) => renderPublishedTaskEntry(task)).join("\n")}
    - 你不能修改 blueprint 中已经固定的核心约束：derivedTaskId、taskRole、roleOrdinal、primaryOutputFile、sourceTaskId、skillMode、targetSkillDirName、targetSkillName。

    已知约束:
    ${skillConstraint}
    ${renderSourceTaskReferenceRules(`drafts/${plan.derivedTaskId}/environment/`)}
    - task.toml 中 metadata.id 必须等于 "${plan.derivedTaskId}"。
    - task.toml 中 metadata.name 必须显式包含 "${roleDisplayName}"。
    - instruction.md 必须使用英文描述。
    - task.toml 中 metadata.name 和 metadata.description 必须使用英文描述。
    - task.toml 中 metadata.primary_output_file 必须等于 "${plan.primaryOutputFile}"。
    - task.toml 中 metadata.source_task_id 必须等于 "${sourceTask.sourceTaskId}"。
    - task.toml 中 metadata.task_role 必须等于 "${plan.taskRole}"。
    - task.toml 的 [metadata] 至少必须包含:
      - id
      - name
      - description
      - author_name
      - author_email
      - difficulty
      - category
      - tags
      - primary_output_file
      - source_task_id
      - task_role
    - task.toml 必须包含 [environment]，并固定写为:
      - cpus = 2
      - memory_mb = 2048
      - storage_mb = 5120
      - gpus = 0
    - 必须保留 plan.json，不要删除或改名；如需更新，只能与当前 blueprint 保持一致。
    - environment/Dockerfile 必须保留 COPY skills /root/.codex/skills。
    - environment/Dockerfile 不能使用本地私有镜像、localhost registry、内网 registry、带私有端口的 registry；请使用公开镜像仓库或 Docker Hub 公共镜像。
    - instruction.md 不要直接出现当前 environment/skills/ 里的 shipped skill 的 name 或 dirName。
    - solution/solve.sh 不得只是复制、移动、重命名或直接输出随任务一起提供的完整标准答案产物。
    - tests/test_outputs.py 只应校验 instruction.md 明确要求的输出契约。
    - 如果 tests/test_outputs.py 使用 pytest 风格测试，tests/test.sh 必须通过 pytest 执行它。
    ${renderHarborOracleBaseline()}

    你需要创建或更新这些文件:
    - plan.json
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

export function buildReviewerPrompt(
  unit: GenerationUnit,
  familyPlan: FamilyPlan,
  taskPlans: DerivedTaskPlan[],
): string {
  const taskList = taskPlans
    .map((task) => `- ${task.derivedTaskId} (${buildRoleDisplayName(task)}) -> drafts/${task.derivedTaskId}/`)
    .join("\n");
  const publishedTaskList =
    unit.publishedTasks.length === 0
      ? "- none"
      : unit.publishedTasks.map((task) => renderPublishedTaskEntry(task)).join("\n");
  const skillReviewRule =
    unit.skillMode === "per-skill"
      ? `- 每个任务是否只依赖当前唯一 shipped skill：${unit.targetSkill?.name ?? "unknown"} (${unit.targetSkill?.dirName ?? "unknown"})；如果完成任务还需要依赖其他未提供 skills，就直接判定失败`
      : `- 任务是否真的能从 shipped skills 受益`;

  return dedent(`
    不要修改任何文件。你现在只负责审稿。

    先阅读:
    - TASK_BUILDER_BRIEF.md
    - source_task/
    - drafts/
    - final-root 下同 family 已发布任务

    当前 family 规划:
    ${JSON.stringify(familyPlan, null, 2)}

    本轮 drafts tasks:
    ${taskList}

    已发布 Harbor family 目录: ${unit.finalFamilyDir || "unknown"}
    已发布 tasks:
    ${publishedTaskList}

    审查目标:
    - 对每个任务分别判断：
      - instruction.md 是否直接出现当前 environment/skills/ 里的 shipped skill 的 name 或 dirName
      - instruction.md、task.toml 的 metadata.name、metadata.description 是否使用英文；只要出现中文，就直接判定失败
      - source_task/ 是否只是参考，而不是机械复写源任务
      - 是否合理复用或新建输入资产，并与同 family 其他任务拉开差异
      - plan.json、task.toml、instruction、tests、solution 是否互相一致
      - tests/test.sh 是否先创建 /logs/verifier
      - reward 是否写到 /logs/verifier/reward.txt 或 /logs/verifier/reward.json
      - 是否稳定写出 reward，而不是裸跑测试后直接结束
      - 是否存在 set -e/pipefail 导致写 reward 前提前退出的路径
      - solution/solve.sh 是否只是复制、搬运或暴露随任务提供的完整标准答案
      - tests/test_outputs.py 是否只检查 instruction.md 明示的输出契约，而没有引入隐藏要求
      - tests/test_outputs.py 是否把合法解法锁死到某种内部实现细节，而不是校验结果语义
      - environment/Dockerfile 是否显然使用了私有/本地镜像
      ${skillReviewRule}
      - 该任务是否应通过 reviewer
      - 只要命中上述任一 Harbor testability 问题，就将 testabilityPass 设为 false，并在 issues 中直接点明具体问题
    - 对 family 整体单独给出观察：
      - 本轮 drafts 与 final-root 中已发布任务是否足够区分，不应只是历史任务的轻微变体
      - family 是否满足 ${unit.similarCount} 个 similar + ${unit.transferCount} 个 transfer
      - transfer 任务之间是否足够不同
      - similar 任务是否足够贴近目标技能的典型用法

    返回格式要求:
    - taskResults 中必须覆盖当前全部任务
    - taskResults[].pass=false 只表示该任务不应发布，不表示整组 family 失败
    - familyObservations 只记录 family 级观察，不决定单个任务是否发布

    返回严格符合 schema 的 JSON，不要输出额外解释。
  `);
}

export function buildRepairPrompt(args: {
  unit: GenerationUnit;
  plan: DerivedTaskPlan;
  reviewerIssues: string[];
  staticIssues: string[];
  runtimeIssues: string[];
  runtimeDir?: string;
  daytonaLogRoot?: string;
  runtimeLogIndexPath?: string;
  runtimeLogPath?: string;
  runtimeResultPath?: string;
  jobLogPath?: string;
  trialLogPath?: string;
  verifierStdoutPath?: string;
  rewardPath?: string;
  artifactManifestPath?: string;
}): string {
  const reviewerBlock =
    args.reviewerIssues.length > 0
      ? args.reviewerIssues.map((issue) => `- ${issue}`).join("\n")
      : "- 无 reviewer 问题";
  const staticBlock =
    args.staticIssues.length > 0
      ? args.staticIssues.map((issue) => `- ${issue}`).join("\n")
      : "- 无 static 问题";
  const runtimeBlock =
    args.runtimeIssues.length > 0
      ? args.runtimeIssues.map((issue) => `- ${issue}`).join("\n")
      : "- 无 runtime 问题";

  return dedent(`
    你正在修复一个 Harbor task 草稿。

    只允许修改当前任务目录 drafts/${args.plan.derivedTaskId}/ 内的文件，不要修改 source_task/、artifacts/、Harbor 仓库代码，也不要修改 environment/skills/ 下 shipped skill 的内容。

    当前 task blueprint:
    ${JSON.stringify(args.plan, null, 2)}

    当前问题:
    reviewer:
    ${reviewerBlock}

    static:
    ${staticBlock}

    runtime:
    ${runtimeBlock}

    你还可以读取这些运行证据:
    - 本次 Oracle/Daytona 完整日志目录: ${args.daytonaLogRoot ?? args.runtimeDir ?? "当前没有完整 runtime 目录"}
    - 日志索引: ${args.runtimeLogIndexPath ?? "当前没有 log-index.json"}
    - Oracle 日志: ${args.runtimeLogPath ?? "当前没有 runtime log"}
    - Oracle 结果 JSON: ${args.runtimeResultPath ?? "当前没有 result.json"}
    - Harbor job 日志: ${args.jobLogPath ?? "当前没有 job.log"}
    - trial 日志: ${args.trialLogPath ?? "当前没有 trial.log"}
    - verifier 输出: ${args.verifierStdoutPath ?? "当前没有 verifier/test-stdout.txt"}
    - reward 文件: ${args.rewardPath ?? "当前没有 reward.txt/reward.json"}
    - artifacts manifest: ${args.artifactManifestPath ?? "当前没有 artifacts/manifest.json"}

    修复要求:
    - 优先最小化改动，只修当前列出的问题。
    - 必须保留 plan.json，不要删除。
    - instruction.md、task.toml 的 metadata.name、metadata.description 必须保持英文，不要写中文任务描述。
    - 不要改变 task.toml 的 metadata.id、metadata.source_task_id、metadata.task_role、metadata.primary_output_file 所代表的任务身份；如当前这些字段缺失或错误，可以把它们修正到与 plan.json 一致。
    - 如果要消除 instruction.md 中的 skill 暴露，可以同步调整输入资产名、输出字段名、tests 和 solution，但要保持任务目标一致。
    - 不要让任务依赖当前 environment/skills/ 之外的其他 shipped skills。
    - 不要引入隐藏测试要求；instruction、tests、solution 应保持一致。
    - 如果需要修改 environment/Dockerfile，不能改成私有/本地镜像；必须使用公共镜像。
    - 你可以直接读取完整 Daytona 日志目录，而不只是看摘要文件；优先检查 log-index.json、harbor-run.log、job.log、trial.log、verifier/test-stdout.txt、reward 文件和 trial 级 result.json。
    - 如果 runtime 日志或 result.json 暴露了 Harbor/Daytona oracle 失败原因，必须优先根据日志修正，而不是忽略它或只根据 reward=0 猜测。

    完成修改后，返回严格 JSON:
    {
      "summary": "简短说明你修了什么",
      "changedFiles": ["相对路径1", "相对路径2"]
    }
  `);
}

export function relativeDraftPath(derivedTaskId: string): string {
  return path.posix.join("drafts", derivedTaskId);
}
