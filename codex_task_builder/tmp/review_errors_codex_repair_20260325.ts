import path from "node:path";
import { promises as fs } from "node:fs";

import { Codex } from "@openai/codex-sdk";

import type {
  DerivedTaskPlan,
  FamilyPlan,
  WriterSummary,
} from "../src/schema.ts";
import {
  validateDraftStatic,
  type ValidationIssue,
} from "../src/validate.ts";
import {
  copyDir,
  ensureDir,
  pathExists,
  readText,
  writeJson,
} from "../src/utils.ts";

const REPO_ROOT = "/home/levi/Harbor";
const INPUT_ROOT = path.join(
  REPO_ROOT,
  "tasks_library",
  "perSkill_unpublished_20260325_scratch_slice",
  "review_errors",
);
const OUTPUT_ROOT = path.join(
  REPO_ROOT,
  "tasks_library",
  "perSkill_unpublished_20260325_scratch_slice",
  "review_errors_FIXED",
);
const PASS_ROOT = path.join(OUTPUT_ROOT, "pass");
const FAIL_ROOT = path.join(OUTPUT_ROOT, "fail");
const RUN_SUMMARY_ROOT = path.join(REPO_ROOT, "codex_task_builder_runs");
const DEFAULT_WORK_ROOT = "/tmp/harbor_review_errors_fixed_candidates";
const DEFAULT_MAX_CONCURRENT = 10;
const DEFAULT_MAX_REPAIR_ATTEMPTS = 3;
const DEFAULT_REVIEW_RETRIES = 2;

const SINGLE_TASK_REPAIR_SCHEMA = {
  type: "object",
  additionalProperties: false,
  required: ["summary", "changedFiles"],
  properties: {
    summary: { type: "string" },
    changedFiles: {
      type: "array",
      items: { type: "string" },
    },
  },
} as const;

type SingleTaskRepairResult = {
  summary: string;
  changedFiles: string[];
};

const SINGLE_TASK_REVIEW_SCHEMA = {
  type: "object",
  additionalProperties: false,
  required: ["pass", "issues", "visibilityPass", "skillBenefitPass", "testabilityPass"],
  properties: {
    pass: { type: "boolean" },
    issues: {
      type: "array",
      items: { type: "string" },
    },
    visibilityPass: { type: "boolean" },
    skillBenefitPass: { type: "boolean" },
    testabilityPass: { type: "boolean" },
  },
} as const;

type SingleTaskReviewResult = {
  pass: boolean;
  issues: string[];
  visibilityPass: boolean;
  skillBenefitPass: boolean;
  testabilityPass: boolean;
};

type Workspace = {
  runId: string;
  sourceTaskId: string;
  skillMode: "all" | "per-skill";
  targetSkill: {
    name: string;
    dirName: string;
    relativeDir: string;
    skillMdPath: string;
  } | null;
  scopeSlug: string;
  rootDir: string;
  sourceTaskDir: string;
  draftsDir: string;
  artifactsDir: string;
  briefPath: string;
};

type CentralRunSummary = {
  sourceTaskId: string;
  targetSkillDirName?: string;
  targetSkillName?: string;
  issues?: string[];
  workspace?: Workspace;
};

type LocalRunSummary = {
  scratch_run_dir: string;
  source_task_id: string;
  skill_name?: string;
  skill_norm?: string;
  issues?: string[];
  failed_task_ids?: string[];
};

type TaskRecord = {
  key: string;
  sourceTaskId: string;
  targetSkillDirName: string;
  runId: string;
  taskId: string;
  sourcePath: string;
  runRoot: string;
  localSummaryPath: string;
};

type RunContext = {
  runId: string;
  sourceTaskId: string;
  targetSkillDirName: string;
  targetSkillName: string;
  workspace: Workspace;
  familyPlan: FamilyPlan;
  planByTaskId: Map<string, DerivedTaskPlan>;
  originalReviewerIssuesByTaskId: Map<string, string[]>;
  originalStaticIssuesByTaskId: Map<string, string[]>;
};

type AttemptRecord = {
  attempt: number;
  requestedReviewerIssues: string[];
  requestedStaticIssues: string[];
  repairThreadId: string | null;
  repairSummary: string;
  reviewThreadId: string | null;
  reviewerIssues: string[];
  staticIssues: string[];
  pass: boolean;
};

type RepairRecord = {
  sourceTaskId: string;
  targetSkillDirName: string;
  targetSkillName: string;
  runId: string;
  taskId: string;
  sourceInputPath: string;
  sourceScratchDraftPath: string;
  candidatePath: string;
  outputPath: string;
  status: "pass" | "fail";
  originalReviewerIssues: string[];
  originalStaticIssues: string[];
  finalReviewerIssues: string[];
  finalStaticIssues: string[];
  changedFiles: string[];
  attempts: AttemptRecord[];
};

type SummaryJson = {
  generatedAt: string;
  inputRoot: string;
  outputRoot: string;
  workRoot: string;
  maxConcurrent: number;
  maxRepairAttempts: number;
  reviewRetries: number;
  counts: {
    pass: number;
    fail: number;
  };
  runCount: number;
  taskCount: number;
  runs: Array<{
    runId: string;
    sourceTaskId: string;
    targetSkillDirName: string;
    passCount: number;
    failCount: number;
  }>;
  tasks: RepairRecord[];
};

type Options = {
  inputRoot: string;
  outputRoot: string;
  passRoot: string;
  failRoot: string;
  workRoot: string;
  maxConcurrent: number;
  maxRepairAttempts: number;
  reviewRetries: number;
  limitRuns: number | null;
  limitTasks: number | null;
  sourceTaskId: string | null;
  runId: string | null;
  taskId: string | null;
};

function nowIso(): string {
  return new Date().toISOString();
}

function log(message: string): void {
  console.log(`[${nowIso()}] ${message}`);
}

function usage(): string {
  return [
    "Usage:",
    "  node --import tsx tmp/review_errors_codex_repair_20260325.ts [options]",
    "",
    "Options:",
    `  --max-concurrent <n>       Codex SDK 并发数，默认 ${DEFAULT_MAX_CONCURRENT}`,
    `  --max-repair-attempts <n> 单任务最大修复轮数，默认 ${DEFAULT_MAX_REPAIR_ATTEMPTS}`,
    `  --review-retries <n>      reviewer 重试次数，默认 ${DEFAULT_REVIEW_RETRIES}`,
    "  --limit-runs <n>          只处理前 n 个 run",
    "  --limit-tasks <n>         只处理前 n 个 task",
    "  --source-task-id <id>     只处理某个 sourceTaskId",
    "  --run-id <id>             只处理某个 runId",
    "  --task-id <id>            只处理某个 taskId",
    `  --work-root <path>        候选任务工作目录，默认 ${DEFAULT_WORK_ROOT}`,
    "  --help                    显示帮助",
  ].join("\n");
}

function parseNumberFlag(flag: string, value: string | undefined): number {
  if (!value) {
    throw new Error(`${flag} 缺少值`);
  }
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    throw new Error(`${flag} 必须是正数`);
  }
  return parsed;
}

function parseArgs(argv: string[]): Options {
  const options: Options = {
    inputRoot: INPUT_ROOT,
    outputRoot: OUTPUT_ROOT,
    passRoot: PASS_ROOT,
    failRoot: FAIL_ROOT,
    workRoot: DEFAULT_WORK_ROOT,
    maxConcurrent: DEFAULT_MAX_CONCURRENT,
    maxRepairAttempts: DEFAULT_MAX_REPAIR_ATTEMPTS,
    reviewRetries: DEFAULT_REVIEW_RETRIES,
    limitRuns: null,
    limitTasks: null,
    sourceTaskId: null,
    runId: null,
    taskId: null,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    switch (arg) {
      case "--max-concurrent":
        options.maxConcurrent = parseNumberFlag(arg, argv[index + 1]);
        index += 1;
        break;
      case "--max-repair-attempts":
        options.maxRepairAttempts = parseNumberFlag(arg, argv[index + 1]);
        index += 1;
        break;
      case "--review-retries":
        options.reviewRetries = parseNumberFlag(arg, argv[index + 1]);
        index += 1;
        break;
      case "--limit-runs":
        options.limitRuns = parseNumberFlag(arg, argv[index + 1]);
        index += 1;
        break;
      case "--limit-tasks":
        options.limitTasks = parseNumberFlag(arg, argv[index + 1]);
        index += 1;
        break;
      case "--source-task-id":
        options.sourceTaskId = argv[index + 1] ?? null;
        index += 1;
        break;
      case "--run-id":
        options.runId = argv[index + 1] ?? null;
        index += 1;
        break;
      case "--task-id":
        options.taskId = argv[index + 1] ?? null;
        index += 1;
        break;
      case "--work-root":
        options.workRoot = argv[index + 1] ?? DEFAULT_WORK_ROOT;
        index += 1;
        break;
      case "--help":
      case "-h":
        console.log(usage());
        process.exit(0);
        break;
      default:
        throw new Error(`未知参数: ${arg}`);
    }
  }

  return options;
}

async function listDirs(root: string): Promise<string[]> {
  const entries = await fs.readdir(root, { withFileTypes: true });
  return entries
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name)
    .sort((a, b) => a.localeCompare(b));
}

function taskKey(record: Pick<TaskRecord, "sourceTaskId" | "targetSkillDirName" | "runId" | "taskId">): string {
  return [record.sourceTaskId, record.targetSkillDirName, record.runId, record.taskId].join("\t");
}

async function collectTasks(inputRoot: string): Promise<TaskRecord[]> {
  const tasks: TaskRecord[] = [];
  for (const sourceTaskId of await listDirs(inputRoot)) {
    const sourceRoot = path.join(inputRoot, sourceTaskId);
    for (const targetSkillDirName of await listDirs(sourceRoot)) {
      const skillRoot = path.join(sourceRoot, targetSkillDirName);
      for (const runId of await listDirs(skillRoot)) {
        const runRoot = path.join(skillRoot, runId);
        const localSummaryPath = path.join(runRoot, "run-summary.json");
        for (const taskId of await listDirs(runRoot)) {
          const sourcePath = path.join(runRoot, taskId);
          const record: TaskRecord = {
            key: taskKey({ sourceTaskId, targetSkillDirName, runId, taskId }),
            sourceTaskId,
            targetSkillDirName,
            runId,
            taskId,
            sourcePath,
            runRoot,
            localSummaryPath,
          };
          tasks.push(record);
        }
      }
    }
  }
  return tasks.sort((a, b) => a.key.localeCompare(b.key));
}

function stripScopedIssue(issue: string, scope: "reviewer" | "static", taskId: string): string | null {
  const prefix = `${scope}:${taskId} `;
  if (!issue.startsWith(prefix)) {
    return null;
  }
  return issue.slice(prefix.length).trim();
}

function syntheticWriterSummary(plan: DerivedTaskPlan): WriterSummary {
  return {
    derivedTaskId: plan.derivedTaskId,
    draftRelativePath: path.posix.join("drafts", plan.derivedTaskId),
    primaryOutputFile: plan.primaryOutputFile,
    filesWritten: ["synthetic-placeholder.txt"],
    summary: "synthetic writer summary for review_errors repair",
  };
}

async function loadRunContext(task: TaskRecord): Promise<RunContext> {
  const localRunSummary = JSON.parse(await readText(task.localSummaryPath)) as LocalRunSummary;
  const centralSummaryPath = path.join(RUN_SUMMARY_ROOT, `${task.runId}.json`);
  const centralRunSummary = (await pathExists(centralSummaryPath))
    ? (JSON.parse(await readText(centralSummaryPath)) as CentralRunSummary)
    : null;

  const workspace = centralRunSummary?.workspace ?? {
    runId: task.runId,
    sourceTaskId: task.sourceTaskId,
    skillMode: "per-skill" as const,
    targetSkill: localRunSummary.skill_name
      ? {
          name: localRunSummary.skill_name,
          dirName: task.targetSkillDirName,
          relativeDir: task.targetSkillDirName,
          skillMdPath: path.join(
            localRunSummary.scratch_run_dir,
            task.sourceTaskId,
            "source_task",
            "environment",
            "skills",
            task.targetSkillDirName,
            "SKILL.md",
          ),
        }
      : null,
    scopeSlug: task.targetSkillDirName,
    rootDir: path.join(localRunSummary.scratch_run_dir, task.sourceTaskId),
    sourceTaskDir: path.join(localRunSummary.scratch_run_dir, task.sourceTaskId, "source_task"),
    draftsDir: path.join(localRunSummary.scratch_run_dir, task.sourceTaskId, "drafts"),
    artifactsDir: path.join(localRunSummary.scratch_run_dir, task.sourceTaskId, "artifacts"),
    briefPath: path.join(localRunSummary.scratch_run_dir, task.sourceTaskId, "TASK_BUILDER_BRIEF.md"),
  };

  const familyPlanPath = path.join(workspace.artifactsDir, "family-plan.json");
  if (!(await pathExists(familyPlanPath))) {
    throw new Error(`family-plan.json 不存在: ${familyPlanPath}`);
  }
  const familyPlan = JSON.parse(await readText(familyPlanPath)) as FamilyPlan;
  const issues = [...(centralRunSummary?.issues ?? localRunSummary.issues ?? [])];

  const originalReviewerIssuesByTaskId = new Map<string, string[]>();
  const originalStaticIssuesByTaskId = new Map<string, string[]>();
  for (const plan of familyPlan.derivedTasks) {
    const reviewerIssues = issues
      .map((issue) => stripScopedIssue(issue, "reviewer", plan.derivedTaskId))
      .filter((value): value is string => Boolean(value));
    const staticIssues = issues
      .map((issue) => stripScopedIssue(issue, "static", plan.derivedTaskId))
      .filter((value): value is string => Boolean(value));
    originalReviewerIssuesByTaskId.set(plan.derivedTaskId, reviewerIssues);
    originalStaticIssuesByTaskId.set(plan.derivedTaskId, staticIssues);
  }

  return {
    runId: task.runId,
    sourceTaskId: task.sourceTaskId,
    targetSkillDirName: task.targetSkillDirName,
    targetSkillName:
      centralRunSummary?.targetSkillName ??
      localRunSummary.skill_name ??
      task.targetSkillDirName,
    workspace,
    familyPlan,
    planByTaskId: new Map(familyPlan.derivedTasks.map((plan) => [plan.derivedTaskId, plan])),
    originalReviewerIssuesByTaskId,
    originalStaticIssuesByTaskId,
  };
}

function normalizeTaskIssues(issues: ValidationIssue[]): string[] {
  return issues.map((issue) => issue.message);
}

async function runWithRetries<T>(
  label: string,
  retries: number,
  action: () => Promise<T>,
): Promise<T> {
  let lastError: unknown = null;
  for (let attempt = 1; attempt <= retries + 1; attempt += 1) {
    try {
      return await action();
    } catch (error) {
      lastError = error;
      if (attempt > retries) {
        break;
      }
      log(`${label} 第 ${attempt}/${retries + 1} 次失败，准备重试`);
      await new Promise((resolve) => setTimeout(resolve, attempt * 1500));
    }
  }
  throw lastError;
}

function makeSdkCodex(): Codex {
  return new Codex({
    config: {
      sandbox_workspace_write: {
        network_access: true,
      },
    },
  });
}

function buildSingleTaskReviewerPrompt(args: {
  sourceTaskId: string;
  taskId: string;
  targetSkillName: string;
  targetSkillDirName: string;
}): string {
  return [
    "不要修改任何文件。你现在只负责审查当前单个 Harbor per-skill task。",
    "当前工作目录就是该任务根目录。",
    "",
    `sourceTaskId: ${args.sourceTaskId}`,
    `taskId: ${args.taskId}`,
    `当前唯一 shipped skill name: ${args.targetSkillName}`,
    `当前唯一 shipped skill dirName: ${args.targetSkillDirName}`,
    "",
    "请至少检查这些文件与目录：",
    "- instruction.md",
    "- task.toml",
    "- environment/",
    "- environment/skills/",
    "- solution/solve.sh",
    "- tests/test.sh",
    "- tests/test_outputs.py",
    "",
    "审查规则：",
    "- visibilityPass 只看 instruction.md 是否直接出现当前 environment/skills/ 里的 shipped skill 的 name 或 dirName；只有这种直接点名才算技能暴露。",
    "- 如果 instruction.md 中出现了当前 shipped skill 的 name 或 dirName，即使它出现在文件名、字段名、命令、示例或正文中，也算 direct mention。",
    "- 如果 instruction.md 没有直接点名当前 shipped skill，则不要因为主题相近、同义词、隐含能力、文件格式常识或其他旁证而判 visibility fail。",
    "- skillBenefitPass 只在任务能在仅提供当前 shipped skill 的前提下成立，且不依赖其他未提供 shipped skills 时为 true。",
    "- testabilityPass 只在任务没有答案泄露、没有隐藏要求、tests 可判定且与 instruction/solution 一致时为 true。",
    "- pass 只有在 visibilityPass、skillBenefitPass、testabilityPass 全部为 true 且没有其他足以阻止发布的问题时才为 true。",
    "",
    "issues 字段要求：",
    "- 只写会阻止该任务发布的问题。",
    "- 每条 issue 用简洁中文一句话描述。",
    "- 不要在 issue 里重复写 visibilityPass=false、skillBenefitPass=false、testabilityPass=false；这些由布尔字段表达。",
    "",
    "返回严格 JSON：",
    "{",
    '  "pass": true,',
    '  "issues": ["..."],',
    '  "visibilityPass": true,',
    '  "skillBenefitPass": true,',
    '  "testabilityPass": true',
    "}",
  ].join("\n");
}

function normalizeSingleTaskReviewerIssues(result: SingleTaskReviewResult): string[] {
  const issueParts = [...result.issues];
  if (!result.visibilityPass) {
    issueParts.push("visibilityPass=false");
  }
  if (!result.skillBenefitPass) {
    issueParts.push("skillBenefitPass=false");
  }
  if (!result.testabilityPass) {
    issueParts.push("testabilityPass=false");
  }
  if (result.pass && issueParts.length === 0) {
    return [];
  }
  return [issueParts.join("; ") || "reviewer 判定失败，但未提供原因"];
}

function buildRepairPrompt(args: {
  sourceTaskId: string;
  taskId: string;
  targetSkillDirName: string;
  reviewerIssues: string[];
  staticIssues: string[];
}): string {
  const reviewerBlock =
    args.reviewerIssues.length > 0
      ? args.reviewerIssues.map((issue) => `- ${issue}`).join("\n")
      : "- 无 reviewer 问题";
  const staticBlock =
    args.staticIssues.length > 0
      ? args.staticIssues.map((issue) => `- ${issue}`).join("\n")
      : "- 无 static 问题";

  return [
    "你正在修复一个 Harbor per-skill task 的副本。",
    "只允许修改当前工作目录内的任务文件，不要修改任何 Harbor 仓库代码，也不要修改 environment/skills/ 下 shipped skill 的内容。",
    "不要修改 REPAIR.json。可以读取 PLAN.json，但除非绝对必要，不要修改它。",
    "优先最小化改动，只修当前列出的 reviewer/static 问题，并保持任务可解、测试可判定、目录仍是完整 Harbor task。",
    `sourceTaskId: ${args.sourceTaskId}`,
    `taskId: ${args.taskId}`,
    `当前 shipped skill dirName: ${args.targetSkillDirName}`,
    "",
    "当前 reviewer 问题:",
    reviewerBlock,
    "",
    "当前 static 问题:",
    staticBlock,
    "",
    "关键约束:",
    "- reviewer 的技能暴露判定只看 instruction.md 是否直接出现当前 shipped skill 的 name 或 dirName；只有这种直接点名才算暴露。",
    "- 如果要消除 instruction.md 中的 skill 暴露，可以同步调整输入资产名、输出字段名、tests 和 solution，但要保持任务目标一致。",
    "- 不要让任务依赖当前 environment/skills/ 之外的其他 shipped skills。",
    "- 不要引入隐藏测试要求；instruction、tests、solution 应保持一致。",
    "- 不要改变 task.toml 的 metadata.id、metadata.source_task_id、metadata.task_role、metadata.primary_output_file 所代表的任务身份；如当前这些字段缺失或错误，可以把它们修正到与 PLAN.json 一致。",
    "- 允许修改 instruction.md、task.toml、environment/Dockerfile、environment/输入资产、solution/solve.sh、tests/test.sh、tests/test_outputs.py。",
    "",
    "完成修改后，返回严格 JSON:",
    "{",
    '  "summary": "简短说明你修了什么",',
    '  "changedFiles": ["相对路径1", "相对路径2"]',
    "}",
  ].join("\n");
}

async function runRepairAttempt(candidateDir: string, prompt: string): Promise<{
  repairThreadId: string | null;
  result: SingleTaskRepairResult;
}> {
  const codex = makeSdkCodex();
  const thread = codex.startThread({
    workingDirectory: candidateDir,
    sandboxMode: "workspace-write",
    approvalPolicy: "never",
    skipGitRepoCheck: true,
    networkAccessEnabled: true,
    modelReasoningEffort: "high",
  });
  const turn = await thread.run(prompt, {
    outputSchema: SINGLE_TASK_REPAIR_SCHEMA,
  });
  return {
    repairThreadId: thread.id,
    result: JSON.parse(turn.finalResponse) as SingleTaskRepairResult,
  };
}

async function runSingleTaskReview(candidateDir: string, prompt: string): Promise<{
  reviewThreadId: string | null;
  result: SingleTaskReviewResult;
}> {
  const codex = makeSdkCodex();
  const thread = codex.startThread({
    workingDirectory: candidateDir,
    sandboxMode: "workspace-write",
    approvalPolicy: "never",
    skipGitRepoCheck: true,
    networkAccessEnabled: true,
    modelReasoningEffort: "medium",
  });
  const turn = await thread.run(prompt, {
    outputSchema: SINGLE_TASK_REVIEW_SCHEMA,
  });
  return {
    reviewThreadId: thread.id,
    result: JSON.parse(turn.finalResponse) as SingleTaskReviewResult,
  };
}

async function listRelativeFiles(rootDir: string): Promise<string[]> {
  const results: string[] = [];
  async function walk(currentDir: string, relativeDir: string): Promise<void> {
    const entries = await fs.readdir(currentDir, { withFileTypes: true });
    for (const entry of entries) {
      const rel = relativeDir ? path.posix.join(relativeDir, entry.name) : entry.name;
      const full = path.join(currentDir, entry.name);
      if (entry.isDirectory()) {
        await walk(full, rel);
        continue;
      }
      if (entry.isFile()) {
        results.push(rel);
      }
    }
  }
  if (!(await pathExists(rootDir))) {
    return results;
  }
  await walk(rootDir, "");
  return results.sort((a, b) => a.localeCompare(b));
}

async function readFileOrNull(targetPath: string): Promise<string | null> {
  if (!(await pathExists(targetPath))) {
    return null;
  }
  return fs.readFile(targetPath, "utf8");
}

async function diffChangedFiles(sourceRoot: string, candidateRoot: string): Promise<string[]> {
  const ignore = new Set(["REPAIR.json"]);
  const sourceFiles = new Set(await listRelativeFiles(sourceRoot));
  const candidateFiles = new Set(await listRelativeFiles(candidateRoot));
  const all = new Set([...sourceFiles, ...candidateFiles]);
  const changed: string[] = [];

  for (const rel of Array.from(all).sort((a, b) => a.localeCompare(b))) {
    if (ignore.has(rel)) {
      continue;
    }
    const sourceText = await readFileOrNull(path.join(sourceRoot, rel));
    const candidateText = await readFileOrNull(path.join(candidateRoot, rel));
    if (sourceText !== candidateText) {
      changed.push(rel);
    }
  }

  return changed;
}

async function copyFiltered(sourceRoot: string, outputRoot: string, excludeFiles: Set<string>): Promise<void> {
  await ensureDir(path.dirname(outputRoot));
  await fs.cp(sourceRoot, outputRoot, {
    recursive: true,
    force: true,
    filter: (src) => {
      const relativePath = path.relative(sourceRoot, src);
      if (!relativePath || relativePath === ".") {
        return true;
      }
      const normalized = relativePath.split(path.sep).join(path.posix.sep);
      return !excludeFiles.has(normalized);
    },
  });
}

async function evaluateCandidateTask(
  run: RunContext,
  taskId: string,
  candidateDir: string,
  reviewRetries: number,
): Promise<{
  reviewerIssues: string[];
  staticIssues: string[];
  reviewThreadId: string | null;
}> {
  const plan = run.planByTaskId.get(taskId);
  if (!plan) {
    throw new Error(`找不到 task 对应的 family plan: ${run.runId}/${taskId}`);
  }
  const reviewResult = await runWithRetries(
    `review ${run.runId}/${taskId}`,
    reviewRetries,
    () =>
      runSingleTaskReview(
        candidateDir,
        buildSingleTaskReviewerPrompt({
          sourceTaskId: run.sourceTaskId,
          taskId,
          targetSkillName: run.targetSkillName,
          targetSkillDirName: run.targetSkillDirName,
        }),
      ),
  );
  const staticIssues = await validateDraftStatic(
    candidateDir,
    plan,
    run.sourceTaskId,
    syntheticWriterSummary(plan),
  );
  return {
    reviewerIssues: normalizeSingleTaskReviewerIssues(reviewResult.result),
    staticIssues: normalizeTaskIssues(staticIssues),
    reviewThreadId: reviewResult.reviewThreadId,
  };
}

async function loadExistingRepairRecord(passRoot: string, failRoot: string, sourceTaskId: string, taskId: string): Promise<RepairRecord | null> {
  for (const root of [passRoot, failRoot]) {
    const metaPath = path.join(root, sourceTaskId, taskId, "REPAIR.json");
    if (await pathExists(metaPath)) {
      return JSON.parse(await readText(metaPath)) as RepairRecord;
    }
  }
  return null;
}

async function processRepairTask(task: TaskRecord, run: RunContext, options: Options): Promise<RepairRecord> {
  const existing = await loadExistingRepairRecord(options.passRoot, options.failRoot, task.sourceTaskId, task.taskId);
  if (existing) {
    return existing;
  }

  const candidatePath = path.join(
    options.workRoot,
    task.sourceTaskId,
    task.targetSkillDirName,
    task.runId,
    task.taskId,
  );
  if (!(await pathExists(candidatePath))) {
    await copyDir(task.sourcePath, candidatePath);
  }

  let currentReviewerIssues = [...(run.originalReviewerIssuesByTaskId.get(task.taskId) ?? [])];
  let currentStaticIssues = [...(run.originalStaticIssuesByTaskId.get(task.taskId) ?? [])];
  const attempts: AttemptRecord[] = [];

  for (let attempt = 1; attempt <= options.maxRepairAttempts; attempt += 1) {
    if (currentReviewerIssues.length === 0 && currentStaticIssues.length === 0) {
      break;
    }

    let repairThreadId: string | null = null;
    let repairSummary = "";
    try {
      const repairResult = await runWithRetries(
        `repair ${task.runId}/${task.taskId} attempt ${attempt}`,
        1,
        () =>
          runRepairAttempt(
            candidatePath,
            buildRepairPrompt({
              sourceTaskId: task.sourceTaskId,
              taskId: task.taskId,
              targetSkillDirName: task.targetSkillDirName,
              reviewerIssues: currentReviewerIssues,
              staticIssues: currentStaticIssues,
            }),
          ),
      );
      repairThreadId = repairResult.repairThreadId;
      repairSummary = repairResult.result.summary;
    } catch (error) {
      repairSummary = error instanceof Error ? error.stack ?? error.message : String(error);
    }

    const evaluation = await evaluateCandidateTask(run, task.taskId, candidatePath, options.reviewRetries);
    currentReviewerIssues = evaluation.reviewerIssues;
    currentStaticIssues = evaluation.staticIssues;
    attempts.push({
      attempt,
      requestedReviewerIssues: [...currentReviewerIssues],
      requestedStaticIssues: [...currentStaticIssues],
      repairThreadId,
      repairSummary,
      reviewThreadId: evaluation.reviewThreadId,
      reviewerIssues: [...currentReviewerIssues],
      staticIssues: [...currentStaticIssues],
      pass: currentReviewerIssues.length === 0 && currentStaticIssues.length === 0,
    });
  }

  const status: "pass" | "fail" =
    currentReviewerIssues.length === 0 && currentStaticIssues.length === 0 ? "pass" : "fail";
  const outputPath = path.join(
    status === "pass" ? options.passRoot : options.failRoot,
    task.sourceTaskId,
    task.taskId,
  );
  await copyFiltered(candidatePath, outputPath, new Set(["REPAIR.json"]));
  const changedFiles = await diffChangedFiles(task.sourcePath, candidatePath);
  const record: RepairRecord = {
    sourceTaskId: task.sourceTaskId,
    targetSkillDirName: task.targetSkillDirName,
    targetSkillName: run.targetSkillName,
    runId: task.runId,
    taskId: task.taskId,
    sourceInputPath: task.sourcePath,
    sourceScratchDraftPath: path.join(run.workspace.draftsDir, task.taskId),
    candidatePath,
    outputPath,
    status,
    originalReviewerIssues: [...(run.originalReviewerIssuesByTaskId.get(task.taskId) ?? [])],
    originalStaticIssues: [...(run.originalStaticIssuesByTaskId.get(task.taskId) ?? [])],
    finalReviewerIssues: [...currentReviewerIssues],
    finalStaticIssues: [...currentStaticIssues],
    changedFiles,
    attempts,
  };
  await writeJson(path.join(candidatePath, "REPAIR.json"), record);
  await writeJson(path.join(outputPath, "REPAIR.json"), record);
  return record;
}

function mergeByKey<T>(existing: T[], incoming: T[], keyFn: (value: T) => string): T[] {
  const map = new Map<string, T>();
  for (const item of existing) {
    map.set(keyFn(item), item);
  }
  for (const item of incoming) {
    map.set(keyFn(item), item);
  }
  return Array.from(map.values());
}

async function loadSummary(summaryPath: string, options: Options): Promise<SummaryJson> {
  if (!(await pathExists(summaryPath))) {
    return {
      generatedAt: nowIso(),
      inputRoot: options.inputRoot,
      outputRoot: options.outputRoot,
      workRoot: options.workRoot,
      maxConcurrent: options.maxConcurrent,
      maxRepairAttempts: options.maxRepairAttempts,
      reviewRetries: options.reviewRetries,
      counts: {
        pass: 0,
        fail: 0,
      },
      runCount: 0,
      taskCount: 0,
      runs: [],
      tasks: [],
    };
  }
  return JSON.parse(await readText(summaryPath)) as SummaryJson;
}

async function updateSummary(summaryPath: string, options: Options, newRecords: RepairRecord[]): Promise<void> {
  const existing = await loadSummary(summaryPath, options);
  const tasks = mergeByKey(existing.tasks, newRecords, (record) => `${record.runId}\t${record.taskId}`);
  const runMap = new Map<string, SummaryJson["runs"][number]>();
  for (const task of tasks) {
    const current = runMap.get(task.runId) ?? {
      runId: task.runId,
      sourceTaskId: task.sourceTaskId,
      targetSkillDirName: task.targetSkillDirName,
      passCount: 0,
      failCount: 0,
    };
    if (task.status === "pass") {
      current.passCount += 1;
    } else {
      current.failCount += 1;
    }
    runMap.set(task.runId, current);
  }
  const summary: SummaryJson = {
    ...existing,
    generatedAt: nowIso(),
    inputRoot: options.inputRoot,
    outputRoot: options.outputRoot,
    workRoot: options.workRoot,
    maxConcurrent: options.maxConcurrent,
    maxRepairAttempts: options.maxRepairAttempts,
    reviewRetries: options.reviewRetries,
    counts: {
      pass: tasks.filter((task) => task.status === "pass").length,
      fail: tasks.filter((task) => task.status === "fail").length,
    },
    runCount: runMap.size,
    taskCount: tasks.length,
    runs: Array.from(runMap.values()).sort((a, b) => a.runId.localeCompare(b.runId)),
    tasks: tasks.sort((a, b) => a.outputPath.localeCompare(b.outputPath)),
  };
  await writeJson(summaryPath, summary);
}

async function runPool<T, R>(items: T[], concurrency: number, worker: (item: T, index: number) => Promise<R>): Promise<R[]> {
  const results: R[] = new Array(items.length);
  let nextIndex = 0;

  async function loop(): Promise<void> {
    while (true) {
      const index = nextIndex;
      nextIndex += 1;
      if (index >= items.length) {
        return;
      }
      results[index] = await worker(items[index] as T, index);
    }
  }

  await Promise.all(Array.from({ length: Math.max(1, concurrency) }, () => loop()));
  return results;
}

async function main(): Promise<void> {
  const options = parseArgs(process.argv.slice(2));
  await ensureDir(options.passRoot);
  await ensureDir(options.failRoot);
  await ensureDir(options.workRoot);

  let tasks = await collectTasks(options.inputRoot);
  if (options.sourceTaskId) {
    tasks = tasks.filter((task) => task.sourceTaskId === options.sourceTaskId);
  }
  if (options.runId) {
    tasks = tasks.filter((task) => task.runId === options.runId);
  }
  if (options.taskId) {
    tasks = tasks.filter((task) => task.taskId === options.taskId);
  }

  const runKeysAll = Array.from(
    new Set(tasks.map((task) => `${task.sourceTaskId}\t${task.targetSkillDirName}\t${task.runId}`)),
  ).sort((a, b) => a.localeCompare(b));
  const selectedRunKeys =
    options.limitRuns === null ? runKeysAll : runKeysAll.slice(0, options.limitRuns);
  const selectedRunSet = new Set(selectedRunKeys);
  tasks = tasks.filter((task) =>
    selectedRunSet.has(`${task.sourceTaskId}\t${task.targetSkillDirName}\t${task.runId}`),
  );
  if (options.limitTasks !== null) {
    tasks = tasks.slice(0, options.limitTasks);
  }

  log(`input root: ${options.inputRoot}`);
  log(`output root: ${options.outputRoot}`);
  log(`work root: ${options.workRoot}`);
  log(`selected runs: ${new Set(tasks.map((task) => task.runId)).size}`);
  log(`selected tasks: ${tasks.length}`);
  log(`codex concurrency: ${options.maxConcurrent}`);

  if (tasks.length === 0) {
    log("没有匹配到需要处理的任务");
    return;
  }

  const runContextMap = new Map<string, RunContext>();
  for (const task of tasks) {
    if (runContextMap.has(task.runId)) {
      continue;
    }
    runContextMap.set(task.runId, await loadRunContext(task));
  }

  const records = await runPool(tasks, options.maxConcurrent, async (task, index) => {
    log(`task ${index + 1}/${tasks.length}: ${task.sourceTaskId}/${task.taskId} 开始`);
    const run = runContextMap.get(task.runId);
    if (!run) {
      throw new Error(`缺少 run context: ${task.runId}`);
    }
    const record = await processRepairTask(task, run, options);
    log(`task ${index + 1}/${tasks.length}: ${task.sourceTaskId}/${task.taskId} -> ${record.status}`);
    return record;
  });

  const summaryPath = path.join(options.outputRoot, "summary.json");
  await updateSummary(summaryPath, options, records);

  const passCount = records.filter((record) => record.status === "pass").length;
  const failCount = records.filter((record) => record.status === "fail").length;
  console.log(
    JSON.stringify(
      {
        outputRoot: options.outputRoot,
        summaryPath,
        taskCount: records.length,
        passCount,
        failCount,
        runCount: new Set(records.map((record) => record.runId)).size,
      },
      null,
      2,
    ),
  );
}

void main().catch((error) => {
  const message = error instanceof Error ? error.stack ?? error.message : String(error);
  console.error(message);
  process.exitCode = 1;
});
