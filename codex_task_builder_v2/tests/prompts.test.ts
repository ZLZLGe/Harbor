import assert from "node:assert/strict";
import {
  buildFamilyPlannerPrompt,
  buildRepairPrompt,
  buildReviewerPrompt,
  buildTaskBuilderBrief,
  buildTaskWriterPrompt,
} from "../src/prompts.js";
import type { DerivedTaskPlan, FamilyPlan } from "../src/schema.js";
import { buildGenerationUnits, type GenerationUnit, type SkillInfo, type SourceTask } from "../src/discovery.js";

const pdfSkill: SkillInfo = {
  name: "PDF",
  dirName: "pdf",
  relativeDir: "pdf",
  skillMdPath: "/tmp/pdf/SKILL.md",
};

const sourceTask: SourceTask = {
  sourceTaskId: "find-topk-similiar-chemicals",
  sourceDir: "/tmp/source-task",
  taskTomlPath: "/tmp/source-task/task.toml",
  instructionPath: "/tmp/source-task/instruction.md",
  environmentDir: "/tmp/source-task/environment",
  solutionDir: "/tmp/source-task/solution",
  testsDir: "/tmp/source-task/tests",
  skillsDir: "/tmp/source-task/environment/skills",
  metadata: {
    id: "find-topk-similiar-chemicals",
    name: "Find Topk Similiar Chemicals",
    difficulty: "medium",
    category: "science",
    tags: ["pdf", "chemistry"],
  },
  skills: [pdfSkill],
};

const unit: GenerationUnit = {
  sourceTask,
  skillMode: "per-skill",
  targetSkill: pdfSkill,
  scopeSlug: "pdf",
  scopeLabel: "PDF",
  similarCount: 2,
  transferCount: 3,
  pendingSimilarOrdinals: [1, 2],
  pendingTransferOrdinals: [1, 2, 3],
  finalFamilyDir: "/tmp/final/find-topk-similiar-chemicals/pdf",
  publishedTasks: [],
};

const historyAwareUnit: GenerationUnit = {
  ...unit,
  pendingSimilarOrdinals: [2],
  publishedTasks: [
    {
      derivedTaskId: "similar1",
      taskRole: "similar",
      roleOrdinal: 1,
      taskDir: "/tmp/final/find-topk-similiar-chemicals/pdf/similar1",
      planPath: "/tmp/final/find-topk-similiar-chemicals/pdf/similar1/plan.json",
      instructionPath: "/tmp/final/find-topk-similiar-chemicals/pdf/similar1/instruction.md",
      taskTomlPath: "/tmp/final/find-topk-similiar-chemicals/pdf/similar1/task.toml",
      testOutputsPath: "/tmp/final/find-topk-similiar-chemicals/pdf/similar1/tests/test_outputs.py",
      environmentDir: "/tmp/final/find-topk-similiar-chemicals/pdf/similar1/environment",
    },
  ],
};

const plan: DerivedTaskPlan = {
  derivedTaskId: "similar1",
  taskRole: "similar",
  roleOrdinal: 1,
  title: "Clinic Intake PDF Similar 1",
  goal: "Fill the intake form PDF from records.",
  primaryOutputFile: "filled_intake.pdf",
  difficulty: "medium",
  category: "document",
  skillBenefitRationale: "Requires PDF form inspection and writing.",
  sourceTaskId: sourceTask.sourceTaskId,
  skillMode: "per-skill",
  targetSkillDirName: "pdf",
  targetSkillName: "PDF",
};

const familyPlan: FamilyPlan = {
  sourceTaskId: sourceTask.sourceTaskId,
  skillMode: "per-skill",
  targetSkillDirName: "pdf",
  targetSkillName: "PDF",
  familyTheme: "Clinical document processing",
  similarTasks: [
    {
      title: plan.title,
      goal: plan.goal,
      primaryOutputFile: plan.primaryOutputFile,
      difficulty: plan.difficulty,
      category: plan.category,
      skillBenefitRationale: plan.skillBenefitRationale,
    },
    {
      title: "Clinic Intake PDF Similar 2",
      goal: "Normalize a different PDF intake packet.",
      primaryOutputFile: "normalized_intake.pdf",
      difficulty: "medium",
      category: "document",
      skillBenefitRationale: "Requires PDF extraction and rewrite.",
    },
  ],
  transferTasks: [
    {
      title: "Pharmacy Label Transfer 1",
      goal: "Rebuild a label pack PDF.",
      primaryOutputFile: "label_pack.pdf",
      difficulty: "medium",
      category: "document",
      skillBenefitRationale: "Uses PDF layout handling.",
    },
    {
      title: "Appeal Packet Transfer 2",
      goal: "Assemble an appeal packet PDF.",
      primaryOutputFile: "appeal_packet.pdf",
      difficulty: "medium",
      category: "document",
      skillBenefitRationale: "Uses PDF annotation and merge.",
    },
    {
      title: "Audit Binder Transfer 3",
      goal: "Build an audit binder PDF.",
      primaryOutputFile: "audit_binder.pdf",
      difficulty: "medium",
      category: "document",
      skillBenefitRationale: "Uses PDF transformation.",
    },
  ],
};

const taskPlans: DerivedTaskPlan[] = [
  plan,
  {
    ...plan,
    derivedTaskId: "similar2",
    roleOrdinal: 2,
    title: "Clinic Intake PDF Similar 2",
    primaryOutputFile: "normalized_intake.pdf",
  },
  {
    ...plan,
    derivedTaskId: "transfer1",
    taskRole: "transfer",
    roleOrdinal: 1,
    title: "Pharmacy Label Transfer 1",
    primaryOutputFile: "label_pack.pdf",
  },
  {
    ...plan,
    derivedTaskId: "transfer2",
    taskRole: "transfer",
    roleOrdinal: 2,
    title: "Appeal Packet Transfer 2",
    primaryOutputFile: "appeal_packet.pdf",
  },
  {
    ...plan,
    derivedTaskId: "transfer3",
    taskRole: "transfer",
    roleOrdinal: 3,
    title: "Audit Binder Transfer 3",
    primaryOutputFile: "audit_binder.pdf",
  },
];

const brief = buildTaskBuilderBrief(unit);
const plannerPrompt = buildFamilyPlannerPrompt(unit);
const writerPrompt = buildTaskWriterPrompt(unit, plan);
const reviewerPrompt = buildReviewerPrompt(unit, familyPlan, taskPlans);
const historyPlannerPrompt = buildFamilyPlannerPrompt(historyAwareUnit);
const historyWriterPrompt = buildTaskWriterPrompt(historyAwareUnit, plan);
const historyReviewerPrompt = buildReviewerPrompt(historyAwareUnit, familyPlan, taskPlans);
const repairPrompt = buildRepairPrompt({
  unit,
  plan,
  reviewerIssues: ["reviewer:similar1 instruction.md 必须使用英文描述，不能包含中文"],
  staticIssues: ["static:similar1 task.toml metadata.description 必须使用英文描述，不能包含中文"],
  runtimeIssues: ["runtime:similar1 harbor verifier reward=0 < 1.0"],
  runtimeDir: "/tmp/runtime/similar1/cycle-1-attempt-2",
  runtimeLogRoot: "/tmp/runtime/similar1/cycle-1-attempt-2",
  runtimeLogIndexPath: "/tmp/runtime/similar1/cycle-1-attempt-2/log-index.json",
  runtimeLogPath: "/tmp/runtime/similar1/cycle-1-attempt-2/harbor-run.log",
  runtimeResultPath: "/tmp/runtime/similar1/cycle-1-attempt-2/result.json",
  jobLogPath: "/tmp/runtime/similar1/cycle-1-attempt-2/job.log",
  trialLogPath: "/tmp/runtime/similar1/cycle-1-attempt-2/trial.log",
  verifierStdoutPath: "/tmp/runtime/similar1/cycle-1-attempt-2/verifier/test-stdout.txt",
  rewardPath: "/tmp/runtime/similar1/cycle-1-attempt-2/verifier/reward.txt",
  artifactManifestPath: "/tmp/runtime/similar1/cycle-1-attempt-2/artifacts/manifest.json",
});
const allModeUnit = buildGenerationUnits(sourceTask, {
  skillMode: "all",
  similarCount: 1,
  transferCount: 1,
})[0];
const allModeBrief = buildTaskBuilderBrief(allModeUnit);
const allModePlannerPrompt = buildFamilyPlannerPrompt(allModeUnit);

assert.equal(allModeUnit?.scopeSlug, "all-skills");

assert.match(brief, /最终任务短名固定采用 similar1、similar2、transfer1、transfer2/);
assert.match(brief, /plan\.json 是 planner 产物，后续 materialize\/publish 也要保留/);
assert.match(brief, /environment\/Dockerfile 不能使用本地私有镜像/);
assert.match(brief, /environment\/Dockerfile 必须显式声明 WORKDIR/);
assert.match(brief, /不要使用 COPY \. \/root、COPY \. \/root\/、COPY \.\/ \/root、ADD \. \/root/);
assert.match(brief, /不要把 skills 复制到普通运行时路径/);
assert.match(brief, /instruction\.md、task\.toml 的 metadata\.name 和 metadata\.description/);
assert.match(brief, /Harbor builder refs: builder_refs\/harbor\//);
assert.match(brief, /builder_refs\/harbor\/SKILL\.md/);
assert.match(brief, /hard to solve but easy to verify/);
assert.match(brief, /任务必须 self-contained/);
assert.match(brief, /无论 all 模式还是 per-skill 模式，benchmark 任务默认都应规划为 hard/);
assert.match(brief, /不要把任务写成只靠单个明显文件、单条 shell 命令，或浅层 grep\/jq\/排序\/聚合就能完成的小题/);
assert.match(brief, /answer-like 文件、可直接复制\/改名的 deliverable，或其他明显 no-skill shortcut/);
assert.match(brief, /目标 skill 必须依赖其 SKILL\.md 中独特、非通用模板化的能力点/);
assert.match(brief, /实质改变解题成败/);
assert.match(brief, /常见 bash\/python 模板、通用调试套路或轻量试错/);
assert.match(brief, /solution\/solve\.sh 与 verifier（tests\/test\.sh、tests\/test_outputs\.py）必须和 environment\/skills/);
assert.match(brief, /无论评测时是否额外安装 skill，参考解与 verifier 都应能独立运行并完成验收/);
assert.match(brief, /similar: 2/);
assert.match(brief, /transfer: 3/);
assert.match(brief, /本轮只需要补齐这些任务槽位/);
assert.match(brief, /已发布 Harbor family 目录/);
assert.match(allModeBrief, /all 模式下，多个 shipped skills 的核心收益点必须真实参与解题/);
assert.equal(brief.includes("实验污染"), false);
assert.equal(brief.includes("无技能对照"), false);

assert.match(plannerPrompt, /familyTheme、每个任务的 title、goal、category、skillBenefitRationale 都必须用英文书写/);
assert.match(plannerPrompt, /similarTasks 数组，长度必须恰好为 2/);
assert.match(plannerPrompt, /transferTasks 数组，长度必须恰好为 3/);
assert.match(plannerPrompt, /不要输出 derivedTaskId/);
assert.match(plannerPrompt, /只允许围绕当前目标 skill 设计：PDF \(pdf\)/);
assert.match(plannerPrompt, /完整检查 source_task\/ 和 builder_refs\/harbor\//);
assert.match(plannerPrompt, /hard to solve but easy to verify/);
assert.match(plannerPrompt, /self-contained/);
assert.match(plannerPrompt, /参考解与 verifier 和 skill runtime 解耦/);
assert.match(plannerPrompt, /无论 all 模式还是 per-skill 模式，benchmark 任务默认都应规划为 hard/);
assert.match(plannerPrompt, /带相关 skill 时能明显压缩搜索空间，而不用相关 skill 时容易走错路/);
assert.match(plannerPrompt, /不要规划成只靠单个明显文件、单条命令或浅层通用脚本就能完成的题/);
assert.match(plannerPrompt, /规划前必须先阅读当前目标 shipped skill 的 SKILL\.md/);
assert.match(plannerPrompt, /必须先提炼 2-4 个该 skill 独有、非通用模板化的关键能力点/);
assert.match(plannerPrompt, /通用 agent 最可能卡在哪一步/);
assert.match(plannerPrompt, /读 helper \+ 套模板 \+ 调参/);
assert.match(plannerPrompt, /资产天然暴露解法结构的 family/);
assert.match(plannerPrompt, /只需要复用 source task 求解骨架的 family/);
assert.match(plannerPrompt, /主要考模板填空，而不是 skill 对应推理、建模或工作流能力的 family/);
assert.match(historyPlannerPrompt, /final-root 已有同 family 的已发布任务/);
assert.match(historyPlannerPrompt, /当前已发布任务: similar1/);
assert.match(historyPlannerPrompt, /本轮需要补齐的 similar 槽位: similar2/);
assert.match(allModePlannerPrompt, /all 模式下，family 必须保留全部 shipped skills 的核心收益点/);
assert.match(allModePlannerPrompt, /规划前必须先阅读当前全部 shipped skills 的 SKILL\.md/);
assert.match(allModePlannerPrompt, /必须先为每个 shipped skill 分别提炼 2-4 个独特、非通用模板化的关键能力点/);

assert.match(writerPrompt, /drafts\/similar1\/environment\/skills\/ 中只能保留一个 shipped skill/);
assert.match(writerPrompt, /builder_refs\/harbor\//);
assert.match(writerPrompt, /task\.toml 中 metadata\.id 必须等于 "similar1"/);
assert.match(writerPrompt, /metadata\.name 必须显式包含 "Similar 1"/);
assert.match(writerPrompt, /instruction\.md 必须使用英文描述/);
assert.match(writerPrompt, /metadata\.name 和 metadata\.description 必须使用英文描述/);
assert.match(writerPrompt, /必须保留 plan\.json，不要删除或改名/);
assert.match(writerPrompt, /environment\/Dockerfile 必须显式声明 WORKDIR/);
assert.match(writerPrompt, /默认优先使用 WORKDIR \/root/);
assert.match(writerPrompt, /不要使用 COPY \. \/root、COPY \. \/root\/、COPY \.\/ \/root、ADD \. \/root/);
assert.match(writerPrompt, /不要把 skills 复制到普通运行时路径，例如 \/root\/environment\/skills、\/app\/skills、\/workspace\/skills/);
assert.match(writerPrompt, /environment\/Dockerfile 不能使用本地私有镜像或只在你机器上可用的 registry/);
assert.match(writerPrompt, /expected 应优先从输入资产、题目规则或可复算逻辑推导/);
assert.match(writerPrompt, /fresh state、no-op、仅复制\/改名已有 deliverable、直接搬运任务内现成答案/);
assert.match(writerPrompt, /路径契约必须一致/);
assert.match(writerPrompt, /任务必须 self-contained/);
assert.match(writerPrompt, /不要把当前任务实现成比 blueprint 更轻的版本/);
assert.match(writerPrompt, /instruction\.md 只应清楚说明任务目标、输入资产、输出契约和边界条件，不要写成按顺序执行即可过关的操作手册/);
assert.match(writerPrompt, /不要提供可直接复制\/改名的标准答案、近似最终产物或其他明显 no-skill shortcut/);
assert.match(writerPrompt, /不要让 agent 仅凭单个明显文件、单条 shell 命令或浅层 grep\/jq\/排序\/聚合就能完成任务/);
assert.match(writerPrompt, /目标 skill 必须依赖其 SKILL\.md 中独特、非通用模板化的能力点/);
assert.match(writerPrompt, /常见 bash\/python 模板、通用调试套路或轻量试错/);
assert.match(writerPrompt, /drafts\/<sibling_task>\/plan\.json/);
assert.match(historyWriterPrompt, /final-root 下已发布的同 family 任务/);
assert.match(historyWriterPrompt, /\/tmp\/final\/find-topk-similiar-chemicals\/pdf\/similar1\/plan\.json/);
assert.equal(writerPrompt.includes("实验污染"), false);
assert.equal(writerPrompt.includes("无技能对照"), false);

assert.match(reviewerPrompt, /family 是否满足 2 个 similar \+ 3 个 transfer/);
assert.match(reviewerPrompt, /builder_refs\/harbor\//);
assert.match(reviewerPrompt, /environment\/Dockerfile 是否显式声明 WORKDIR；如果不是 \/root，相关脚本路径是否仍然一致/);
assert.match(reviewerPrompt, /environment\/Dockerfile 是否显然使用了私有\/本地镜像/);
assert.match(reviewerPrompt, /environment\/Dockerfile 是否出现 COPY \. \/root、ADD \. \/root 或同类宽泛复制/);
assert.match(reviewerPrompt, /environment\/Dockerfile 是否把 skills 复制到了 \/root\/environment\/skills、\/app\/skills、\/workspace\/skills 等普通运行时路径/);
assert.match(reviewerPrompt, /是否使用英文；只要出现中文，就直接判定失败/);
assert.match(reviewerPrompt, /plan\.json、task\.toml、instruction、tests、solution 是否互相一致/);
assert.match(reviewerPrompt, /expected 是否来自输入资产、题目规则或可复算逻辑/);
assert.match(reviewerPrompt, /fresh state、no-op、仅复制\/改名已有 deliverable、直接搬运任务内现成答案/);
assert.match(reviewerPrompt, /是否直接引用 environment\/skills\/\*\*、\/root\/\.codex\/skills\/\*\*、\/app\/skills\/\*\*/);
assert.match(reviewerPrompt, /hard to solve but easy to verify/);
assert.match(reviewerPrompt, /该任务是否其实偏 easy，或虽然写了 skill 但没有相关 skill 也大概率能直接做出来/);
assert.match(reviewerPrompt, /该任务是否存在明显 no-skill shortcut/);
assert.match(reviewerPrompt, /如果当前 difficulty 不是 hard，原因是否真的是 hard 只会主要引入 runtime 噪声/);
assert.match(reviewerPrompt, /too easy、skill not critical、no-skill shortcut 或 difficulty too low/);
assert.match(reviewerPrompt, /任务是否 self-contained/);
assert.match(reviewerPrompt, /运行时需要写入的目录是否显式创建/);
assert.match(historyReviewerPrompt, /final-root 下同 family 已发布任务/);
assert.match(historyReviewerPrompt, /本轮 drafts 与 final-root 中已发布任务是否足够区分/);
assert.match(historyReviewerPrompt, /\/tmp\/final\/find-topk-similiar-chemicals\/pdf\/similar1\/instruction\.md/);
assert.equal(reviewerPrompt.includes("实验污染"), false);
assert.equal(reviewerPrompt.includes("无技能对照"), false);

assert.match(repairPrompt, /本次 Oracle runtime 完整日志目录/);
assert.match(repairPrompt, /不要修改 source_task\/、builder_refs\/、artifacts\//);
assert.match(repairPrompt, /log-index\.json/);
assert.match(repairPrompt, /instruction\.md、task\.toml 的 metadata\.name、metadata\.description 必须保持英文/);
assert.match(repairPrompt, /如果需要修改 environment\/Dockerfile，必须显式声明 WORKDIR；默认优先 \/root/);
assert.match(repairPrompt, /必须保留 COPY skills \/root\/\.codex\/skills/);
assert.match(repairPrompt, /不要写 COPY \. \/root、COPY \. \/root\/、COPY \.\/ \/root、ADD \. \/root 或带 flag 的等价写法/);
assert.match(repairPrompt, /不要把 skills 复制到 \/root\/environment\/skills、\/app\/skills、\/workspace\/skills 等普通运行时路径/);
assert.match(repairPrompt, /verifier\/test-stdout\.txt/);
assert.match(repairPrompt, /完整日志目录当作主入口/);
assert.match(repairPrompt, /不要只根据 reward=0、摘要 issue 或 failure label 猜问题/);
assert.match(repairPrompt, /Harbor oracle\/runtime 失败原因/);
assert.match(repairPrompt, /如果 solution\/solve\.sh 或 tests\/\*\* 直接调用 skill 模块，必须去耦/);
assert.match(repairPrompt, /优先排查 verifier 契约问题、输入资产复制问题、运行时路径错误、目录未创建、reward 未稳定落盘/);
assert.match(repairPrompt, /不要通过降低任务难度、补写教程式步骤、暴露关键线索、删除必要干扰项/);
assert.match(repairPrompt, /继续保持 benchmark 默认 hard 的设计目标/);
assert.match(repairPrompt, /修复后仍要避免明显 no-skill shortcut，并保持相关 skill 依然是关键瓶颈/);
assert.equal(repairPrompt.includes("实验污染"), false);
assert.equal(repairPrompt.includes("无技能对照"), false);

console.log("prompts.test.ts passed");
