import assert from "node:assert/strict";
import {
  buildFamilyPlannerPrompt,
  buildReviewerPrompt,
  buildTaskBuilderBrief,
  buildTaskWriterPrompt,
} from "../src/prompts.js";
import type { DerivedTaskPlan, FamilyPlan } from "../src/schema.js";
import type { GenerationUnit, SourceTask, SkillInfo } from "../src/discovery.js";

const pdfSkill: SkillInfo = {
  name: "PDF",
  dirName: "pdf",
  relativeDir: "pdf",
  skillMdPath: "/tmp/pdf/SKILL.md",
};

const sourceTask: SourceTask = {
  sourceTaskId: "pdf-excel-diff",
  sourceDir: "/tmp/source-task",
  taskTomlPath: "/tmp/source-task/task.toml",
  instructionPath: "/tmp/source-task/instruction.md",
  environmentDir: "/tmp/source-task/environment",
  solutionDir: "/tmp/source-task/solution",
  testsDir: "/tmp/source-task/tests",
  skillsDir: "/tmp/source-task/environment/skills",
  metadata: {
    id: "pdf-excel-diff",
    name: "PDF Excel Diff",
    difficulty: "medium",
    category: "document",
    tags: ["pdf", "diff"],
  },
  skills: [pdfSkill],
};

const unit: GenerationUnit = {
  sourceTask,
  skillMode: "per-skill",
  targetSkill: pdfSkill,
  scopeSlug: "pdf",
  scopeLabel: "PDF",
};

const plan: DerivedTaskPlan = {
  derivedTaskId: "clinic-pdf-similar-form-fill",
  taskRole: "similar",
  title: "Clinic PDF Similar Form Fill",
  goal: "Fill a clinic PDF form from supplied records.",
  primaryOutputFile: "/root/output/filled.pdf",
  difficulty: "medium",
  category: "document",
  skillBenefitRationale: "Requires the PDF skill to inspect and update the form correctly.",
  targetSkillDirName: "pdf",
  targetSkillName: "PDF",
};

const familyPlan: FamilyPlan = {
  sourceTaskId: sourceTask.sourceTaskId,
  familyTheme: "Clinic document workflows",
  derivedTasks: [
    plan,
    {
      ...plan,
      derivedTaskId: "pharmacy-pdf-transfer-label-reconciliation",
      taskRole: "transfer",
      title: "Pharmacy PDF Transfer Label Reconciliation",
      goal: "Reconcile prescription labels into a PDF packet.",
      primaryOutputFile: "/root/output/labels.pdf",
    },
    {
      ...plan,
      derivedTaskId: "intake-pdf-transfer-claim-audit",
      taskRole: "transfer",
      title: "Intake PDF Transfer Claim Audit",
      goal: "Audit intake claim forms and produce an annotated PDF.",
      primaryOutputFile: "/root/output/claim_audit.pdf",
    },
    {
      ...plan,
      derivedTaskId: "triage-pdf-transfer-appeal-summary",
      taskRole: "transfer",
      title: "Triage PDF Transfer Appeal Summary",
      goal: "Prepare an appeal summary PDF from case notes.",
      primaryOutputFile: "/root/output/appeal_summary.pdf",
    },
  ],
};

const brief = buildTaskBuilderBrief(unit);
const plannerPrompt = buildFamilyPlannerPrompt(unit);
const writerPrompt = buildTaskWriterPrompt(unit, plan);
const reviewerPrompt = buildReviewerPrompt(unit, familyPlan);

assert.match(brief, /Harbor oracle 基线:/);
assert.match(brief, /source_task\/ 只是参考，不是模板/);
assert.match(brief, /在 drafts\/<derived_task_id>\/environment\/ 下新建全新的输入资产/);
assert.match(brief, /Harbor 会执行 \/tests\/test\.sh 作为 verifier 入口/);
assert.match(brief, /\/logs\/verifier\/reward\.txt/);
assert.match(brief, /如果 source task 的旧写法与 Harbor verifier 契约冲突/);
assert.match(brief, /关键文件职责:/);
assert.match(brief, /solution\/solve\.sh 是参考解脚本/);
assert.match(brief, /不得只是复制、移动、重命名或直接输出随任务一起提供的完整标准答案文件/);
assert.match(brief, /tests\/test_outputs\.py 只应校验 instruction\.md 明确要求的输出契约/);
assert.match(brief, /如果 tests\/test_outputs\.py 使用 pytest 风格测试，tests\/test\.sh 必须用 pytest 执行它/);
assert.match(brief, /task\.toml 环境配额:/);
assert.match(brief, /task\.toml 必须包含 \[environment\]/);
assert.match(brief, /cpus = 2/);
assert.match(brief, /memory_mb = 2048/);
assert.match(brief, /storage_mb = 5120/);
assert.match(brief, /gpus = 0/);

assert.match(plannerPrompt, /只规划那些能在 Harbor 常规 build\/start\/verify 时限内完成的任务/);
assert.match(plannerPrompt, /source_task\/ 只是参考，不是模板/);
assert.match(plannerPrompt, /family 内任务应通过任务目标、输入资产、输出语义和验证方式拉开差异/);
assert.match(plannerPrompt, /如果规划需要联网或外部服务，不要把它视为默认违规项/);

assert.match(writerPrompt, /写作前必须先检查当前 workspace 的 drafts\/ 目录：/);
assert.match(writerPrompt, new RegExp(`把 drafts/${plan.derivedTaskId}/ 视为当前任务目录`));
assert.match(writerPrompt, /把 drafts\/ 下其他已经有内容的 sibling task 目录视为之前已经生成好的任务/);
assert.match(writerPrompt, /优先阅读：[\s\S]*PLAN\.json[\s\S]*instruction\.md[\s\S]*task\.toml/);
assert.match(writerPrompt, /如有必要，再补充检查：[\s\S]*tests\/test_outputs\.py[\s\S]*environment\/ 下的输入资产/);
assert.match(writerPrompt, /任务场景或叙事/);
assert.match(writerPrompt, /输入资产类型、结构或素材来源/);
assert.match(writerPrompt, /输出物的语义目标/);
assert.match(writerPrompt, /测试判定方式/);
assert.match(writerPrompt, /你不能修改 blueprint 中已经固定的核心约束：derivedTaskId、taskRole、primaryOutputFile、source_task_id，以及当前 skill scope/);
assert.match(writerPrompt, /如果 drafts\/ 中还没有其他已生成 sibling tasks，就按正常流程继续写当前任务/);
assert.match(writerPrompt, /source_task\/ 只是参考，不是模板/);
assert.match(writerPrompt, new RegExp(`在 drafts/${plan.derivedTaskId}/environment/ 下新建全新的输入资产`));
assert.match(writerPrompt, /Harbor 会执行 \/tests\/test\.sh 作为 verifier 入口/);
assert.match(writerPrompt, /mkdir -p \/logs\/verifier/);
assert.match(writerPrompt, /写到其他位置不会被识别/);
assert.match(writerPrompt, /不得只是裸跑 pytest、python3 \/tests\/test_outputs\.py/);
assert.match(writerPrompt, /set -e 或 pipefail/);
assert.match(writerPrompt, /\/logs\/verifier\/reward\.txt/);
assert.match(writerPrompt, /\/logs\/verifier\/reward\.json/);
assert.match(writerPrompt, /是否联网不是默认违规项/);
assert.match(writerPrompt, /不要把 Harbor 关键 verifier 依赖留到 tests\/test\.sh 中临时安装/);
assert.match(writerPrompt, /task\.toml 必须包含 \[environment\]，并固定写为:/);
assert.match(writerPrompt, /cpus = 2/);
assert.match(writerPrompt, /memory_mb = 2048/);
assert.match(writerPrompt, /storage_mb = 5120/);
assert.match(writerPrompt, /gpus = 0/);
assert.match(writerPrompt, /solution\/solve\.sh 是参考解脚本/);
assert.match(writerPrompt, /不要把预置答案藏在 environment\/、solution\/ 或其他目录里再由 solve\.sh 直接搬运/);
assert.match(writerPrompt, /tests\/test_outputs\.py 只应校验 instruction\.md 明确要求的输出契约/);
assert.match(writerPrompt, /不要把合法解法锁死到某个内部函数名、唯一中间步骤、固定日志文本或其他未承诺的实现细节/);
assert.match(writerPrompt, /如果 tests\/test_outputs\.py 使用 pytest 风格测试，tests\/test\.sh 必须用 pytest 执行它/);

assert.match(reviewerPrompt, /tests\/test\.sh 是否先创建 \/logs\/verifier/);
assert.match(reviewerPrompt, /source_task\/ 是否只是参考，而不是机械复写源任务/);
assert.match(reviewerPrompt, /是否合理复用或新建输入资产/);
assert.match(reviewerPrompt, /reward 是否写到 \/logs\/verifier\/reward\.txt 或 \/logs\/verifier\/reward\.json/);
assert.match(reviewerPrompt, /是否稳定写出 reward\.txt\/reward\.json/);
assert.match(reviewerPrompt, /set -e\/pipefail 导致写 reward 前提前退出/);
assert.match(reviewerPrompt, /solution\/solve\.sh 是否只是复制、搬运或暴露随任务提供的完整标准答案/);
assert.match(reviewerPrompt, /tests\/test_outputs\.py 是否只检查 instruction\.md 明示的输出契约，而没有引入隐藏要求/);
assert.match(reviewerPrompt, /tests\/test_outputs\.py 是否把合法解法锁死到某种内部实现细节，而不是校验结果语义/);
assert.match(reviewerPrompt, /如果 tests\/test_outputs\.py 是 pytest 风格测试，tests\/test\.sh 是否通过 pytest 正确执行它/);
assert.match(reviewerPrompt, /如果任务使用联网或外部服务，是否仍能在 Harbor 中稳定运行并稳定写 reward/);
assert.match(reviewerPrompt, /testabilityPass 设为 false/);

console.log("prompts.test.ts passed");
