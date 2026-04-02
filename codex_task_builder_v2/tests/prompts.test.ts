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
  daytonaLogRoot: "/tmp/runtime/similar1/cycle-1-attempt-2",
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

assert.equal(allModeUnit?.scopeSlug, "all-skills");

assert.match(brief, /最终任务短名固定采用 similar1、similar2、transfer1、transfer2/);
assert.match(brief, /plan\.json 是 planner 产物，后续 materialize\/publish 也要保留/);
assert.match(brief, /environment\/Dockerfile 不能使用本地私有镜像/);
assert.match(brief, /instruction\.md、task\.toml 的 metadata\.name 和 metadata\.description/);
assert.match(brief, /similar: 2/);
assert.match(brief, /transfer: 3/);
assert.match(brief, /本轮只需要补齐这些任务槽位/);
assert.match(brief, /已发布 Harbor family 目录/);

assert.match(plannerPrompt, /familyTheme、每个任务的 title、goal、category、skillBenefitRationale 都必须用英文书写/);
assert.match(plannerPrompt, /similarTasks 数组，长度必须恰好为 2/);
assert.match(plannerPrompt, /transferTasks 数组，长度必须恰好为 3/);
assert.match(plannerPrompt, /不要输出 derivedTaskId/);
assert.match(plannerPrompt, /只允许围绕当前目标 skill 设计：PDF \(pdf\)/);
assert.match(historyPlannerPrompt, /final-root 已有同 family 的已发布任务/);
assert.match(historyPlannerPrompt, /当前已发布任务: similar1/);
assert.match(historyPlannerPrompt, /本轮需要补齐的 similar 槽位: similar2/);

assert.match(writerPrompt, /drafts\/similar1\/environment\/skills\/ 中只能保留一个 shipped skill/);
assert.match(writerPrompt, /task\.toml 中 metadata\.id 必须等于 "similar1"/);
assert.match(writerPrompt, /metadata\.name 必须显式包含 "Similar 1"/);
assert.match(writerPrompt, /instruction\.md 必须使用英文描述/);
assert.match(writerPrompt, /metadata\.name 和 metadata\.description 必须使用英文描述/);
assert.match(writerPrompt, /必须保留 plan\.json，不要删除或改名/);
assert.match(writerPrompt, /不能使用本地私有镜像、localhost registry、内网 registry、带私有端口的 registry/);
assert.match(writerPrompt, /drafts\/<sibling_task>\/plan\.json/);
assert.match(historyWriterPrompt, /final-root 下已发布的同 family 任务/);
assert.match(historyWriterPrompt, /\/tmp\/final\/find-topk-similiar-chemicals\/pdf\/similar1\/plan\.json/);

assert.match(reviewerPrompt, /family 是否满足 2 个 similar \+ 3 个 transfer/);
assert.match(reviewerPrompt, /environment\/Dockerfile 是否显然使用了私有\/本地镜像/);
assert.match(reviewerPrompt, /是否使用英文；只要出现中文，就直接判定失败/);
assert.match(reviewerPrompt, /plan\.json、task\.toml、instruction、tests、solution 是否互相一致/);
assert.match(historyReviewerPrompt, /final-root 下同 family 已发布任务/);
assert.match(historyReviewerPrompt, /本轮 drafts 与 final-root 中已发布任务是否足够区分/);
assert.match(historyReviewerPrompt, /\/tmp\/final\/find-topk-similiar-chemicals\/pdf\/similar1\/instruction\.md/);

assert.match(repairPrompt, /你可以直接读取完整 Daytona 日志目录/);
assert.match(repairPrompt, /log-index\.json/);
assert.match(repairPrompt, /instruction\.md、task\.toml 的 metadata\.name、metadata\.description 必须保持英文/);
assert.match(repairPrompt, /verifier\/test-stdout\.txt/);

console.log("prompts.test.ts passed");
