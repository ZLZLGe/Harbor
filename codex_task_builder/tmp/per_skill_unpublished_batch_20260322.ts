import path from "node:path";
import { promises as fs } from "node:fs";
import { randomUUID } from "node:crypto";

import { Codex } from "@openai/codex-sdk";

import { CodexTaskBuilderClient } from "../src/codex.ts";
import { discoverSourceTaskById } from "../src/discovery.ts";
import {
  validateDraftStatic,
  validateReviewerResult,
  type ValidationIssue,
} from "../src/validate.ts";
import {
  copyDir,
  ensureDir,
  pathExists,
  readText,
  writeJson,
  type CommandResult,
} from "../src/utils.ts";

const REPO_ROOT = "/home/levi/Harbor";
const SOURCE_TASKS_ROOT = path.join(REPO_ROOT, "tasks_library", "skillsbench", "tasks");
const SCRATCH_ROOT = path.join(REPO_ROOT, "codex_task_builder_runs", "scratch");
const RUN_SUMMARY_ROOT = path.join(REPO_ROOT, "codex_task_builder_runs");
const UNPUBLISHED_ROOT = path.join(REPO_ROOT, "tasks_library", "perSkill_unpublished");
const REVIEWER_REREVIEW_ROOT = path.join(REPO_ROOT, "tasks_library", "perSkill_unpublished_reviewer_rereview");
const REVIEWER_FIXED_ROOT = path.join(REPO_ROOT, "tasks_library", "perSkill_unpublished_reviewer_fixed");
const STATIC_COMBO_FIXED_ROOT = path.join(REPO_ROOT, "tasks_library", "perSkill_unpublished_static_combo_fixed");
const RUN_ID_PREFIX = process.env.RUN_ID_PREFIX ?? "20260322";
const MAX_CONCURRENT = Number(process.env.MAX_CONCURRENT ?? "10");
const MAX_REPAIR_ATTEMPTS = Number(process.env.MAX_REPAIR_ATTEMPTS ?? "3");
const REVIEW_RETRIES = Number(process.env.REVIEW_RETRIES ?? "2");
const LIMIT_RUNS = process.env.LIMIT_RUNS ? Number(process.env.LIMIT_RUNS) : null;
const LIMIT_TASKS = process.env.LIMIT_TASKS ? Number(process.env.LIMIT_TASKS) : null;
const TMP_WORK_ROOT = process.env.TMP_WORK_ROOT ?? "/tmp";
const OVERLAY_ROOT = path.join(TMP_WORK_ROOT, "per_skill_repair_review_overlays");
const REVIEWER_WORK_ROOT = path.join(TMP_WORK_ROOT, "per_skill_repair_workspaces");
const STATIC_WORK_ROOT = path.join(TMP_WORK_ROOT, "per_skill_static_combo_repair_workspaces");

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

type TaskKey = string;

type UnpublishedTaskRecord = {
  key: TaskKey;
  sourceTaskId: string;
  targetSkillDirName: string;
  runId: string;
  taskId: string;
  sourcePath: string;
};

type SourceTaskInfo = Awaited<ReturnType<typeof discoverSourceTaskById>>;

type Plan = {
  derivedTaskId: string;
  taskRole: string;
  primaryOutputFile: string;
  targetSkillDirName?: string;
  targetSkillName?: string;
};

type FamilyPlan = {
  sourceTaskId: string;
  skillMode?: "all" | "per-skill";
  targetSkillDirName?: string;
  targetSkillName?: string;
  derivedTasks: Plan[];
};

type WriterSummary = {
  derivedTaskId: string;
  draftRelativePath: string;
  primaryOutputFile: string;
  filesWritten: string[];
  summary: string;
};

type RunSummary = {
  sourceTaskId: string;
  skillMode: "all" | "per-skill";
  targetSkillDirName?: string;
  targetSkillName?: string;
  issues: string[];
  familyObservationIssues: string[];
  workspace: {
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
};

type RunContext = {
  runId: string;
  sourceTaskId: string;
  sourceTask: SourceTaskInfo;
  targetSkillDirName: string;
  targetSkillName: string;
  familyPlan: FamilyPlan;
  runSummary: RunSummary;
  workspace: {
    runId: string;
    sourceTaskId: string;
    skillMode: "all" | "per-skill";
    targetSkill: RunSummary["workspace"]["targetSkill"];
    scopeSlug: string;
    rootDir: string;
    sourceTaskDir: string;
    draftsDir: string;
    artifactsDir: string;
    briefPath: string;
  };
  planByTaskId: Map<string, Plan>;
  originalReviewerIssuesByTaskId: Map<string, string[]>;
  originalStaticIssuesByTaskId: Map<string, string[]>;
  originalFamilyObservationIssues: string[];
};

type TaskEvaluation = {
  reviewerIssues: string[];
  staticIssues: string[];
};

type RunEvaluation = {
  reviewThreadId: string | null;
  reviewerIssuesByTaskId: Map<string, string[]>;
  staticIssuesByTaskId: Map<string, string[]>;
  familyObservationIssues: string[];
};

type RereviewRecord = {
  sourceTaskId: string;
  targetSkillDirName: string;
  runId: string;
  taskId: string;
  sourceTaskPath: string;
  outputPath: string;
  status: "pass" | "fail";
  oldReviewerIssues: string[];
  oldFamilyObservationIssues: string[];
  newReviewerIssues: string[];
  newStaticIssues: string[];
  familyObservationIssues: string[];
  reviewThreadId: string | null;
};

type AttemptRecord = {
  attempt: number;
  requestedTaskIds: string[];
  requestedIssuesByTaskId: Record<
    string,
    {
      reviewerIssues: string[];
      staticIssues: string[];
      pass: boolean;
    }
  >;
  repairThreadId: string | null;
  repairSummary: string;
  reviewThreadId: string | null;
  evaluationByTaskId: Record<
    string,
    {
      reviewerIssues: string[];
      staticIssues: string[];
      pass: boolean;
    }
  >;
};

type RepairRecord = {
  sourceTaskId: string;
  targetSkillDirName: string;
  runId: string;
  taskId: string;
  sourceFailPath: string;
  sourceScratchDraftPath: string;
  candidatePath: string;
  outputPath: string;
  status: "pass" | "fail";
  issueCategories: string[];
  originalReviewerIssues: string[];
  originalStaticIssues: string[];
  baselineReviewerIssues: string[];
  baselineStaticIssues: string[];
  finalReviewerIssues: string[];
  finalStaticIssues: string[];
  changedFiles: string[];
  attempts: AttemptRecord[];
  originErrorCombo?: "static" | "reviewer__static";
};

function nowIso(): string {
  return new Date().toISOString();
}

function log(message: string): void {
  console.log(`[${nowIso()}] ${message}`);
}

function taskKeyOf(record: Pick<UnpublishedTaskRecord, "sourceTaskId" | "targetSkillDirName" | "runId" | "taskId">): TaskKey {
  return [record.sourceTaskId, record.targetSkillDirName, record.runId, record.taskId].join("\t");
}

async function listDirs(root: string): Promise<string[]> {
  const entries = await fs.readdir(root, { withFileTypes: true });
  return entries
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name)
    .sort((a, b) => a.localeCompare(b));
}

async function collectComboTasks(comboName: "reviewer" | "static"): Promise<UnpublishedTaskRecord[]> {
  const comboRoot = path.join(UNPUBLISHED_ROOT, comboName);
  const results: UnpublishedTaskRecord[] = [];
  if (!(await pathExists(comboRoot))) {
    return results;
  }

  for (const sourceTaskId of await listDirs(comboRoot)) {
    const sourceRoot = path.join(comboRoot, sourceTaskId);
    for (const targetSkillDirName of await listDirs(sourceRoot)) {
      const skillRoot = path.join(sourceRoot, targetSkillDirName);
      for (const runId of await listDirs(skillRoot)) {
        if (!runId.startsWith(RUN_ID_PREFIX)) {
          continue;
        }
        const runRoot = path.join(skillRoot, runId);
        for (const taskId of await listDirs(runRoot)) {
          const sourcePath = path.join(runRoot, taskId);
          const record: UnpublishedTaskRecord = {
            key: taskKeyOf({ sourceTaskId, targetSkillDirName, runId, taskId }),
            sourceTaskId,
            targetSkillDirName,
            runId,
            taskId,
            sourcePath,
          };
          results.push(record);
        }
      }
    }
  }

  return results.sort((a, b) => a.key.localeCompare(b.key));
}

function stripScopedIssue(issue: string, scope: "reviewer" | "static", taskId: string): string | null {
  const prefix = `${scope}:${taskId} `;
  if (!issue.startsWith(prefix)) {
    return null;
  }
  return issue.slice(prefix.length).trim();
}

function syntheticWriterSummary(plan: Plan): WriterSummary {
  return {
    derivedTaskId: plan.derivedTaskId,
    draftRelativePath: path.posix.join("drafts", plan.derivedTaskId),
    primaryOutputFile: plan.primaryOutputFile,
    filesWritten: [],
    summary: "synthetic writer summary for rereview/repair static validation",
  };
}

async function loadRunContext(runId: string, sourceTaskId: string, targetSkillDirName: string): Promise<RunContext> {
  const runSummaryPath = path.join(RUN_SUMMARY_ROOT, `${runId}.json`);
  const runSummary = JSON.parse(await readText(runSummaryPath)) as RunSummary;
  const familyPlan = JSON.parse(
    await readText(path.join(runSummary.workspace.artifactsDir, "family-plan.json")),
  ) as FamilyPlan;
  const sourceTask = await discoverSourceTaskById(sourceTaskId, SOURCE_TASKS_ROOT);

  const originalReviewerIssuesByTaskId = new Map<string, string[]>();
  const originalStaticIssuesByTaskId = new Map<string, string[]>();
  for (const plan of familyPlan.derivedTasks) {
    const reviewerIssues = runSummary.issues
      .map((issue) => stripScopedIssue(issue, "reviewer", plan.derivedTaskId))
      .filter((value): value is string => Boolean(value));
    const staticIssues = runSummary.issues
      .map((issue) => stripScopedIssue(issue, "static", plan.derivedTaskId))
      .filter((value): value is string => Boolean(value));
    originalReviewerIssuesByTaskId.set(plan.derivedTaskId, reviewerIssues);
    originalStaticIssuesByTaskId.set(plan.derivedTaskId, staticIssues);
  }

  return {
    runId,
    sourceTaskId,
    sourceTask,
    targetSkillDirName,
    targetSkillName: runSummary.targetSkillName ?? targetSkillDirName,
    familyPlan,
    runSummary,
    workspace: runSummary.workspace,
    planByTaskId: new Map(familyPlan.derivedTasks.map((plan) => [plan.derivedTaskId, plan])),
    originalReviewerIssuesByTaskId,
    originalStaticIssuesByTaskId,
    originalFamilyObservationIssues: [...(runSummary.familyObservationIssues ?? [])],
  };
}

function normalizeTaskIssues(issues: ValidationIssue[]): string[] {
  return issues.map((issue) => issue.message);
}

async function runWithRetries<T>(
  label: string,
  action: () => Promise<T>,
  retries: number,
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
      log(`${label} failed on attempt ${attempt}/${retries + 1}; retrying`);
      await new Promise((resolve) => setTimeout(resolve, attempt * 1500));
    }
  }
  throw lastError;
}

async function evaluateRun(run: RunContext, client: CodexTaskBuilderClient): Promise<RunEvaluation> {
  const sourceTask = run.sourceTask;
  const targetSkill = sourceTask.skills.find((skill) => skill.dirName === run.targetSkillDirName) ?? null;
  const unit = {
    sourceTask,
    skillMode: (run.familyPlan.skillMode ?? "all") as "all" | "per-skill",
    targetSkill,
    scopeSlug: run.targetSkillDirName ?? "all-skills",
    scopeLabel: run.targetSkillName ?? "All skills",
  };

  const reviewResult = await runWithRetries(
    `review run ${run.runId}`,
    () => client.reviewFamily(unit, run.workspace, run.familyPlan),
    REVIEW_RETRIES,
  );
  const reviewValidation = validateReviewerResult(run.familyPlan, reviewResult.data);
  const reviewerIssuesByTaskId = new Map<string, string[]>();
  const staticIssuesByTaskId = new Map<string, string[]>();
  for (const plan of run.familyPlan.derivedTasks) {
    const draftDir = path.join(run.workspace.draftsDir, plan.derivedTaskId);
    const staticIssues = await validateDraftStatic(
      draftDir,
      plan,
      run.sourceTaskId,
      syntheticWriterSummary(plan),
    );
    reviewerIssuesByTaskId.set(
      plan.derivedTaskId,
      normalizeTaskIssues(reviewValidation.taskIssuesById.get(plan.derivedTaskId) ?? []),
    );
    staticIssuesByTaskId.set(plan.derivedTaskId, normalizeTaskIssues(staticIssues));
  }

  return {
    reviewThreadId: reviewResult.threadId,
    reviewerIssuesByTaskId,
    staticIssuesByTaskId,
    familyObservationIssues: reviewValidation.familyObservationIssues.map((issue) => issue.message),
  };
}

async function copyTaskOutput(sourcePath: string, outputPath: string): Promise<void> {
  await fs.rm(outputPath, { recursive: true, force: true }).catch(() => {});
  await copyDir(sourcePath, outputPath);
}

async function fileExists(targetPath: string): Promise<boolean> {
  return pathExists(targetPath);
}

function rereviewOutputPath(record: Pick<RereviewRecord, "status" | "sourceTaskId" | "taskId">): string {
  return path.join(REVIEWER_REREVIEW_ROOT, record.status, record.sourceTaskId, record.taskId);
}

async function loadExistingRereviewRecord(sourceTaskId: string, taskId: string): Promise<RereviewRecord | null> {
  for (const status of ["pass", "fail"] as const) {
    const metaPath = path.join(REVIEWER_REREVIEW_ROOT, status, sourceTaskId, taskId, "REREVIEW.json");
    if (await fileExists(metaPath)) {
      return JSON.parse(await readText(metaPath)) as RereviewRecord;
    }
  }
  return null;
}

async function writeRereviewRecord(record: RereviewRecord, sourcePath: string): Promise<void> {
  const outputPath = rereviewOutputPath(record);
  await copyTaskOutput(sourcePath, outputPath);
  await writeJson(path.join(outputPath, "REREVIEW.json"), record);
}

function categorizeIssues(reviewerIssues: string[], staticIssues: string[]): string[] {
  const categories = new Set<string>();
  for (const issue of reviewerIssues) {
    if (issue.includes("visibilityPass=false") || /技能暴露|直接点名|直接出现|dirName/i.test(issue)) {
      categories.add("visibility");
      continue;
    }
    if (issue.includes("skillBenefitPass=false")) {
      categories.add("skill_benefit");
      continue;
    }
    if (issue.includes("testabilityPass=false")) {
      categories.add("testability");
      continue;
    }
    categories.add("other");
  }
  if (staticIssues.length > 0) {
    categories.add("static");
  }
  return Array.from(categories);
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
  const ignore = new Set(["REPAIR.json", "REREVIEW.json"]);
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

async function symlinkIntoTemp(source: string, target: string): Promise<void> {
  await ensureDir(path.dirname(target));
  await fs.symlink(source, target);
}

async function buildOverlayWorkspace(run: RunContext, taskId: string, candidateDir: string): Promise<RunContext["workspace"]> {
  const overlayRoot = path.join(OVERLAY_ROOT, `${run.runId}-${taskId}-${randomUUID()}`);
  const draftsDir = path.join(overlayRoot, "drafts");
  await ensureDir(draftsDir);
  await symlinkIntoTemp(run.workspace.sourceTaskDir, path.join(overlayRoot, "source_task"));
  await symlinkIntoTemp(run.workspace.briefPath, path.join(overlayRoot, "TASK_BUILDER_BRIEF.md"));
  for (const plan of run.familyPlan.derivedTasks) {
    const sourceDir =
      plan.derivedTaskId === taskId ? candidateDir : path.join(run.workspace.draftsDir, plan.derivedTaskId);
    await symlinkIntoTemp(sourceDir, path.join(draftsDir, plan.derivedTaskId));
  }
  return {
    runId: run.runId,
    sourceTaskId: run.sourceTaskId,
    skillMode: run.workspace.skillMode,
    targetSkill: run.workspace.targetSkill,
    scopeSlug: run.workspace.scopeSlug,
    rootDir: overlayRoot,
    sourceTaskDir: path.join(overlayRoot, "source_task"),
    draftsDir,
    artifactsDir: path.join(overlayRoot, "artifacts"),
    briefPath: path.join(overlayRoot, "TASK_BUILDER_BRIEF.md"),
  };
}

async function evaluateCandidateTask(run: RunContext, taskId: string, candidateDir: string, client: CodexTaskBuilderClient): Promise<{
  reviewerIssues: string[];
  staticIssues: string[];
  reviewThreadId: string | null;
}> {
  const plan = run.planByTaskId.get(taskId);
  if (!plan) {
    throw new Error(`missing plan for ${run.runId}/${taskId}`);
  }
  const reviewResult = await runWithRetries(
    `review candidate ${run.runId}/${taskId}`,
    async () => {
      const targetSkill =
        run.sourceTask.skills.find((skill) => skill.dirName === run.targetSkillDirName) ??
        run.workspace.targetSkill;
      return runSingleTaskReview(candidateDir, buildSingleTaskReviewerPrompt({
        sourceTaskId: run.sourceTaskId,
        taskId,
        targetSkillName: targetSkill?.name ?? run.targetSkillName,
        targetSkillDirName: targetSkill?.dirName ?? run.targetSkillDirName,
      }));
    },
    REVIEW_RETRIES,
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

function makeSdkCodex(reasoningEffort: "medium" | "high"): Codex {
  return new Codex({
    config: {
      sandbox_workspace_write: {
        network_access: true,
      },
    },
  });
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
  originErrorCombo?: string;
}): string {
  const reviewerBlock =
    args.reviewerIssues.length > 0
      ? args.reviewerIssues.map((issue) => `- ${issue}`).join("\n")
      : "- 无 reviewer 问题";
  const staticBlock =
    args.staticIssues.length > 0
      ? args.staticIssues.map((issue) => `- ${issue}`).join("\n")
      : "- 无 static 问题";
  const comboLine = args.originErrorCombo ? `原始错误组合: ${args.originErrorCombo}\n` : "";

  return [
    "你正在修复一个 Harbor per-skill task 的副本。",
    "只允许修改当前工作目录内的任务文件，不要修改任何 Harbor 仓库代码，也不要修改 environment/skills/ 下 shipped skill 的内容。",
    "不要修改 REPAIR.json 或 REREVIEW.json。可以读取 PLAN.json，但除非绝对必要，不要修改它。",
    "优先最小化改动，只修当前列出的 reviewer/static 问题，并保持任务可解、测试可判定、目录仍是完整 Harbor task。",
    `sourceTaskId: ${args.sourceTaskId}`,
    `taskId: ${args.taskId}`,
    `当前 shipped skill dirName: ${args.targetSkillDirName}`,
    comboLine.trimEnd(),
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
    '{',
    '  "summary": "简短说明你修了什么",',
    '  "changedFiles": ["相对路径1", "相对路径2"]',
    '}',
  ].join("\n");
}

function makeRepairCodex(): Codex {
  return makeSdkCodex("high");
}

async function runRepairAttempt(candidateDir: string, prompt: string): Promise<{
  repairThreadId: string | null;
  result: SingleTaskRepairResult;
}> {
  const codex = makeRepairCodex();
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
  const codex = makeSdkCodex("medium");
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

async function copyFiltered(sourceRoot: string, outputRoot: string, options: {
  excludeFiles: Set<string>;
}): Promise<void> {
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
      return !options.excludeFiles.has(normalized);
    },
  });
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

async function processRepairTask(args: {
  sourceTaskId: string;
  targetSkillDirName: string;
  runId: string;
  taskId: string;
  sourceInputPath: string;
  sourceScratchDraftPath: string;
  candidateRoot: string;
  passRoot: string;
  failRoot: string;
  run: RunContext;
  baselineReviewerIssues: string[];
  baselineStaticIssues: string[];
  originalReviewerIssues: string[];
  originalStaticIssues: string[];
  originErrorCombo?: "static" | "reviewer__static";
  client: CodexTaskBuilderClient;
}): Promise<RepairRecord> {
  const existing = await loadExistingRepairRecord(args.passRoot, args.failRoot, args.sourceTaskId, args.taskId);
  if (existing) {
    return existing;
  }

  const candidatePath = path.join(args.candidateRoot, args.sourceTaskId, args.taskId);
  const passPath = path.join(args.passRoot, args.sourceTaskId, args.taskId);
  const failPath = path.join(args.failRoot, args.sourceTaskId, args.taskId);

  if (!(await pathExists(candidatePath))) {
    await copyTaskOutput(args.sourceInputPath, candidatePath);
  }

  let currentReviewerIssues = [...args.baselineReviewerIssues];
  let currentStaticIssues = [...args.baselineStaticIssues];
  const attempts: AttemptRecord[] = [];

  for (let attempt = 1; attempt <= MAX_REPAIR_ATTEMPTS; attempt += 1) {
    if (currentReviewerIssues.length === 0 && currentStaticIssues.length === 0) {
      break;
    }

    const requestedIssuesByTaskId = {
      [args.taskId]: {
        reviewerIssues: [...currentReviewerIssues],
        staticIssues: [...currentStaticIssues],
        pass: false,
      },
    };

    let repairThreadId: string | null = null;
    let repairSummary = "";
    try {
      const repairPrompt = buildRepairPrompt({
        sourceTaskId: args.sourceTaskId,
        taskId: args.taskId,
        targetSkillDirName: args.targetSkillDirName,
        reviewerIssues: currentReviewerIssues,
        staticIssues: currentStaticIssues,
        originErrorCombo: args.originErrorCombo,
      });
      const repairResult = await runWithRetries(
        `repair ${args.runId}/${args.taskId} attempt ${attempt}`,
        () => runRepairAttempt(candidatePath, repairPrompt),
        1,
      );
      repairThreadId = repairResult.repairThreadId;
      repairSummary = repairResult.result.summary;
    } catch (error) {
      repairSummary = error instanceof Error ? error.message : String(error);
    }

    const evaluation = await evaluateCandidateTask(args.run, args.taskId, candidatePath, args.client);
    currentReviewerIssues = evaluation.reviewerIssues;
    currentStaticIssues = evaluation.staticIssues;
    attempts.push({
      attempt,
      requestedTaskIds: [args.taskId],
      requestedIssuesByTaskId,
      repairThreadId,
      repairSummary,
      reviewThreadId: evaluation.reviewThreadId,
      evaluationByTaskId: {
        [args.taskId]: {
          reviewerIssues: [...currentReviewerIssues],
          staticIssues: [...currentStaticIssues],
          pass: currentReviewerIssues.length === 0 && currentStaticIssues.length === 0,
        },
      },
    });
  }

  const status: "pass" | "fail" = currentReviewerIssues.length === 0 && currentStaticIssues.length === 0 ? "pass" : "fail";
  const outputPath = status === "pass" ? passPath : failPath;
  await copyFiltered(candidatePath, outputPath, {
    excludeFiles: new Set(["REPAIR.json", "REREVIEW.json"]),
  });
  const changedFiles = await diffChangedFiles(args.sourceInputPath, candidatePath);
  const record: RepairRecord = {
    sourceTaskId: args.sourceTaskId,
    targetSkillDirName: args.targetSkillDirName,
    runId: args.runId,
    taskId: args.taskId,
    sourceFailPath: args.sourceInputPath,
    sourceScratchDraftPath: args.sourceScratchDraftPath,
    candidatePath,
    outputPath,
    status,
    issueCategories: categorizeIssues(args.baselineReviewerIssues, args.baselineStaticIssues),
    originalReviewerIssues: [...args.originalReviewerIssues],
    originalStaticIssues: [...args.originalStaticIssues],
    baselineReviewerIssues: [...args.baselineReviewerIssues],
    baselineStaticIssues: [...args.baselineStaticIssues],
    finalReviewerIssues: [...currentReviewerIssues],
    finalStaticIssues: [...currentStaticIssues],
    changedFiles,
    attempts,
    ...(args.originErrorCombo ? { originErrorCombo: args.originErrorCombo } : {}),
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

async function loadJsonIfExists<T>(targetPath: string): Promise<T | null> {
  if (!(await pathExists(targetPath))) {
    return null;
  }
  return JSON.parse(await readText(targetPath)) as T;
}

async function updateReviewerRereviewSummary(newRecords: RereviewRecord[]): Promise<void> {
  const summaryPath = path.join(REVIEWER_REREVIEW_ROOT, "summary.json");
  const existing = (await loadJsonIfExists<{
    generatedAt: string;
    inputSummary: string;
    outputRoot: string;
    mode: string;
    dryRun: boolean;
    concurrency: number;
    retries: number;
    runCount: number;
    taskCount: number;
    counts: { pass: number; fail: number; runsWithReviewError: number };
    runs: Array<{
      runId: string;
      sourceTaskId: string;
      targetSkillDirName: string;
      familyObservationIssues: string[];
      passCount: number;
      failCount: number;
    }>;
    tasks: RereviewRecord[];
  }>(summaryPath)) ?? {
    generatedAt: nowIso(),
    inputSummary: path.join(UNPUBLISHED_ROOT, "summary.json"),
    outputRoot: REVIEWER_REREVIEW_ROOT,
    mode: "per-skill reviewer rereview",
    dryRun: false,
    concurrency: MAX_CONCURRENT,
    retries: REVIEW_RETRIES,
    runCount: 0,
    taskCount: 0,
    counts: {
      pass: 0,
      fail: 0,
      runsWithReviewError: 0,
    },
    runs: [],
    tasks: [],
  };

  const tasks = mergeByKey(existing.tasks, newRecords, (record) => `${record.runId}\t${record.taskId}`);
  const runMap = new Map<string, {
    runId: string;
    sourceTaskId: string;
    targetSkillDirName: string;
    familyObservationIssues: string[];
    passCount: number;
    failCount: number;
  }>();
  for (const task of tasks) {
    const current = runMap.get(task.runId) ?? {
      runId: task.runId,
      sourceTaskId: task.sourceTaskId,
      targetSkillDirName: task.targetSkillDirName,
      familyObservationIssues: [...task.familyObservationIssues],
      passCount: 0,
      failCount: 0,
    };
    if (task.status === "pass") {
      current.passCount += 1;
    } else {
      current.failCount += 1;
    }
    current.familyObservationIssues = [...task.familyObservationIssues];
    runMap.set(task.runId, current);
  }

  const summary = {
    ...existing,
    generatedAt: nowIso(),
    concurrency: MAX_CONCURRENT,
    retries: REVIEW_RETRIES,
    runCount: runMap.size,
    taskCount: tasks.length,
    counts: {
      pass: tasks.filter((task) => task.status === "pass").length,
      fail: tasks.filter((task) => task.status === "fail").length,
      runsWithReviewError: 0,
    },
    runs: Array.from(runMap.values()).sort((a, b) => a.runId.localeCompare(b.runId)),
    tasks: tasks.sort((a, b) => a.outputPath.localeCompare(b.outputPath)),
  };
  await writeJson(summaryPath, summary);
}

async function updateRepairSummary(args: {
  summaryPath: string;
  outputRoot: string;
  inputSummary: string;
  tempWorkRoot: string;
  newRecords: RepairRecord[];
  includeOriginCounts: boolean;
}): Promise<void> {
  const existing = (await loadJsonIfExists<{
    generatedAt: string;
    inputSummary: string;
    outputRoot: string;
    tempWorkRoot: string;
    taskCount: number;
    runCount: number;
    concurrency: number;
    maxRepairAttempts: number;
    counts: Record<string, number>;
    runs: Array<{
      runId: string;
      sourceTaskId: string;
      targetSkillDirName: string;
      passCount: number;
      failCount: number;
    }>;
    tasks: RepairRecord[];
  }>(args.summaryPath)) ?? {
    generatedAt: nowIso(),
    inputSummary: args.inputSummary,
    outputRoot: args.outputRoot,
    tempWorkRoot: args.tempWorkRoot,
    taskCount: 0,
    runCount: 0,
    concurrency: MAX_CONCURRENT,
    maxRepairAttempts: MAX_REPAIR_ATTEMPTS,
    counts: {
      pass: 0,
      fail: 0,
    },
    runs: [],
    tasks: [],
  };

  const tasks = mergeByKey(existing.tasks, args.newRecords, (record) => `${record.runId}\t${record.taskId}`);
  const runMap = new Map<string, {
    runId: string;
    sourceTaskId: string;
    targetSkillDirName: string;
    passCount: number;
    failCount: number;
  }>();
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

  const counts: Record<string, number> = {
    pass: tasks.filter((task) => task.status === "pass").length,
    fail: tasks.filter((task) => task.status === "fail").length,
  };
  if (args.includeOriginCounts) {
    counts.static_origin = tasks.filter((task) => task.originErrorCombo === "static").length;
    counts.reviewer__static_origin = tasks.filter((task) => task.originErrorCombo === "reviewer__static").length;
  }

  const summary = {
    ...existing,
    generatedAt: nowIso(),
    tempWorkRoot: args.tempWorkRoot,
    concurrency: MAX_CONCURRENT,
    maxRepairAttempts: MAX_REPAIR_ATTEMPTS,
    taskCount: tasks.length,
    runCount: runMap.size,
    counts,
    runs: Array.from(runMap.values()).sort((a, b) => a.runId.localeCompare(b.runId)),
    tasks: tasks.sort((a, b) => a.outputPath.localeCompare(b.outputPath)),
  };
  await writeJson(args.summaryPath, summary);
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
  await ensureDir(OVERLAY_ROOT);
  await ensureDir(REVIEWER_WORK_ROOT);
  await ensureDir(STATIC_WORK_ROOT);

  log(`collecting unpublished tasks with run prefix ${RUN_ID_PREFIX}`);
  const reviewerTasks = await collectComboTasks("reviewer");
  const staticTasks = await collectComboTasks("static");
  const reviewerMap = new Map(reviewerTasks.map((record) => [record.key, record]));
  const staticMap = new Map(staticTasks.map((record) => [record.key, record]));
  const overlapKeys = new Set(Array.from(reviewerMap.keys()).filter((key) => staticMap.has(key)));
  const reviewerOnlyTasks = reviewerTasks.filter((record) => !overlapKeys.has(record.key));
  const staticAllTasks = staticTasks;

  if (LIMIT_TASKS !== null) {
    reviewerOnlyTasks.splice(LIMIT_TASKS);
    staticAllTasks.splice(LIMIT_TASKS);
  }

  log(`reviewer-only tasks=${reviewerOnlyTasks.length}, static tasks=${staticAllTasks.length}, overlap=${overlapKeys.size}`);
  if (RUN_ID_PREFIX === "20260322" && LIMIT_RUNS === null && LIMIT_TASKS === null) {
    if (reviewerOnlyTasks.length !== 81 || staticAllTasks.length !== 41 || overlapKeys.size !== 6) {
      throw new Error(
        `unexpected task counts for 20260322 batch: reviewerOnly=${reviewerOnlyTasks.length}, static=${staticAllTasks.length}, overlap=${overlapKeys.size}`,
      );
    }
  }

  const allRelevantRuns = Array.from(
    new Set([...reviewerOnlyTasks, ...staticAllTasks].map((record) => `${record.runId}\t${record.sourceTaskId}\t${record.targetSkillDirName}`)),
  )
    .sort((a, b) => a.localeCompare(b))
    .slice(0, LIMIT_RUNS ?? Number.MAX_SAFE_INTEGER);

  log(`loading ${allRelevantRuns.length} run contexts`);
  const runContexts = new Map<string, RunContext>();
  for (const item of allRelevantRuns) {
    const [runId, sourceTaskId, targetSkillDirName] = item.split("\t");
    const context = await loadRunContext(runId, sourceTaskId, targetSkillDirName);
    runContexts.set(runId, context);
  }

  const reviewClient = new CodexTaskBuilderClient();
  const runIds = Array.from(runContexts.keys()).sort((a, b) => a.localeCompare(b));
  log(`rereviewing ${runIds.length} runs with concurrency=${MAX_CONCURRENT}`);
  const runEvaluationsArray = await runPool(runIds, MAX_CONCURRENT, async (runId, index) => {
    log(`rereview run ${index + 1}/${runIds.length}: ${runId}`);
    const evaluation = await evaluateRun(runContexts.get(runId) as RunContext, reviewClient);
    log(`finished rereview run ${index + 1}/${runIds.length}: ${runId}`);
    return [runId, evaluation] as const;
  });
  const runEvaluations = new Map<string, RunEvaluation>(runEvaluationsArray);

  const rereviewRecords: RereviewRecord[] = [];
  for (const task of reviewerOnlyTasks) {
    const existing = await loadExistingRereviewRecord(task.sourceTaskId, task.taskId);
    if (existing) {
      rereviewRecords.push(existing);
      continue;
    }

    const run = runContexts.get(task.runId);
    const evaluation = runEvaluations.get(task.runId);
    if (!run || !evaluation) {
      throw new Error(`missing evaluation for ${task.runId}`);
    }
    const newReviewerIssues = [...(evaluation.reviewerIssuesByTaskId.get(task.taskId) ?? [])];
    const newStaticIssues = [...(evaluation.staticIssuesByTaskId.get(task.taskId) ?? [])];
    const status: "pass" | "fail" = newReviewerIssues.length === 0 && newStaticIssues.length === 0 ? "pass" : "fail";
    const record: RereviewRecord = {
      sourceTaskId: task.sourceTaskId,
      targetSkillDirName: task.targetSkillDirName,
      runId: task.runId,
      taskId: task.taskId,
      sourceTaskPath: task.sourcePath,
      outputPath: path.join(REVIEWER_REREVIEW_ROOT, status, task.sourceTaskId, task.taskId),
      status,
      oldReviewerIssues: run.runSummary.issues.filter((issue) => issue.startsWith(`reviewer:${task.taskId} `)),
      oldFamilyObservationIssues: [...run.originalFamilyObservationIssues],
      newReviewerIssues,
      newStaticIssues,
      familyObservationIssues: [...evaluation.familyObservationIssues],
      reviewThreadId: evaluation.reviewThreadId,
    };
    await writeRereviewRecord(record, task.sourcePath);
    rereviewRecords.push(record);
  }
  await updateReviewerRereviewSummary(rereviewRecords);
  log(`wrote reviewer rereview outputs for ${rereviewRecords.length} tasks`);

  const reviewerFailInputs = rereviewRecords.filter((record) => record.status === "fail");
  log(`repairing reviewer fail tasks: ${reviewerFailInputs.length}`);
  const reviewerRepairRecords = await runPool(reviewerFailInputs, MAX_CONCURRENT, async (record, index) => {
    log(`reviewer repair ${index + 1}/${reviewerFailInputs.length}: ${record.sourceTaskId}/${record.taskId}`);
    const run = runContexts.get(record.runId);
    if (!run) {
      throw new Error(`missing run context for ${record.runId}`);
    }
    const repairRecord = await processRepairTask({
      sourceTaskId: record.sourceTaskId,
      targetSkillDirName: record.targetSkillDirName,
      runId: record.runId,
      taskId: record.taskId,
      sourceInputPath: path.join(REVIEWER_REREVIEW_ROOT, "fail", record.sourceTaskId, record.taskId),
      sourceScratchDraftPath: path.join(run.workspace.draftsDir, record.taskId),
      candidateRoot: path.join(REVIEWER_FIXED_ROOT, "candidate"),
      passRoot: path.join(REVIEWER_FIXED_ROOT, "pass"),
      failRoot: path.join(REVIEWER_FIXED_ROOT, "fail"),
      run,
      baselineReviewerIssues: [...record.newReviewerIssues],
      baselineStaticIssues: [...record.newStaticIssues],
      originalReviewerIssues: run.originalReviewerIssuesByTaskId.get(record.taskId) ?? [],
      originalStaticIssues: run.originalStaticIssuesByTaskId.get(record.taskId) ?? [],
      client: reviewClient,
    });
    log(`finished reviewer repair ${index + 1}/${reviewerFailInputs.length}: ${record.sourceTaskId}/${record.taskId} -> ${repairRecord.status}`);
    return repairRecord;
  });
  await updateRepairSummary({
    summaryPath: path.join(REVIEWER_FIXED_ROOT, "summary.json"),
    outputRoot: REVIEWER_FIXED_ROOT,
    inputSummary: path.join(REVIEWER_REREVIEW_ROOT, "summary.json"),
    tempWorkRoot: REVIEWER_WORK_ROOT,
    newRecords: reviewerRepairRecords,
    includeOriginCounts: false,
  });
  log(`wrote reviewer fixed outputs for ${reviewerRepairRecords.length} tasks`);

  log(`repairing static/combo tasks: ${staticAllTasks.length}`);
  const staticRepairRecords = await runPool(staticAllTasks, MAX_CONCURRENT, async (task, index) => {
    log(`static repair ${index + 1}/${staticAllTasks.length}: ${task.sourceTaskId}/${task.taskId}`);
    const run = runContexts.get(task.runId);
    const evaluation = runEvaluations.get(task.runId);
    if (!run || !evaluation) {
      throw new Error(`missing run evaluation for ${task.runId}`);
    }
    const originErrorCombo = overlapKeys.has(task.key) ? "reviewer__static" : "static";
    const repairRecord = await processRepairTask({
      sourceTaskId: task.sourceTaskId,
      targetSkillDirName: task.targetSkillDirName,
      runId: task.runId,
      taskId: task.taskId,
      sourceInputPath: task.sourcePath,
      sourceScratchDraftPath: path.join(run.workspace.draftsDir, task.taskId),
      candidateRoot: path.join(STATIC_COMBO_FIXED_ROOT, "candidate"),
      passRoot: path.join(STATIC_COMBO_FIXED_ROOT, "pass"),
      failRoot: path.join(STATIC_COMBO_FIXED_ROOT, "fail"),
      run,
      baselineReviewerIssues: [...(evaluation.reviewerIssuesByTaskId.get(task.taskId) ?? [])],
      baselineStaticIssues: [...(evaluation.staticIssuesByTaskId.get(task.taskId) ?? [])],
      originalReviewerIssues: run.originalReviewerIssuesByTaskId.get(task.taskId) ?? [],
      originalStaticIssues: run.originalStaticIssuesByTaskId.get(task.taskId) ?? [],
      originErrorCombo,
      client: reviewClient,
    });
    log(`finished static repair ${index + 1}/${staticAllTasks.length}: ${task.sourceTaskId}/${task.taskId} -> ${repairRecord.status}`);
    return repairRecord;
  });
  await updateRepairSummary({
    summaryPath: path.join(STATIC_COMBO_FIXED_ROOT, "summary.json"),
    outputRoot: STATIC_COMBO_FIXED_ROOT,
    inputSummary: path.join(UNPUBLISHED_ROOT, "summary.json"),
    tempWorkRoot: STATIC_WORK_ROOT,
    newRecords: staticRepairRecords,
    includeOriginCounts: true,
  });
  log(`wrote static/combo fixed outputs for ${staticRepairRecords.length} tasks`);

  const finalSummary = {
    reviewerRereview: {
      total: rereviewRecords.length,
      pass: rereviewRecords.filter((record) => record.status === "pass").length,
      fail: rereviewRecords.filter((record) => record.status === "fail").length,
    },
    reviewerFixed: {
      total: reviewerRepairRecords.length,
      pass: reviewerRepairRecords.filter((record) => record.status === "pass").length,
      fail: reviewerRepairRecords.filter((record) => record.status === "fail").length,
    },
    staticComboFixed: {
      total: staticRepairRecords.length,
      pass: staticRepairRecords.filter((record) => record.status === "pass").length,
      fail: staticRepairRecords.filter((record) => record.status === "fail").length,
      static_origin: staticRepairRecords.filter((record) => record.originErrorCombo === "static").length,
      reviewer__static_origin: staticRepairRecords.filter((record) => record.originErrorCombo === "reviewer__static").length,
    },
  };
  console.log(JSON.stringify(finalSummary, null, 2));
}

void main().catch((error) => {
  const message = error instanceof Error ? error.stack ?? error.message : String(error);
  console.error(message);
  process.exitCode = 1;
});
