import { promises as fs } from "node:fs";
import path from "node:path";
import type { DerivedTaskPlan, FamilyPlan, ReviewResult, WriterSummary } from "./schema.js";
import type { FamilyWorkspace } from "./workspace.js";
import {
  ensureDir,
  pathExists,
  readText,
  runCommand,
  slugify,
  writeText,
} from "./utils.js";

export type ValidationIssue = {
  scope: "family" | "reviewer" | "static" | "runtime";
  message: string;
  taskId?: string;
};

export type RuntimeEnvironment = "daytona" | "docker";

export type RuntimeFailureKind = "harbor-preflight" | "harbor-run" | "harbor-reward";

export type RuntimePreflightResult = {
  ok: boolean;
  summary: string;
  details: string[];
};

export type RuntimeValidationResult = {
  issues: ValidationIssue[];
  failureKind?: RuntimeFailureKind;
};

export type ReviewValidationResult = {
  taskIssuesById: Map<string, ValidationIssue[]>;
  familyObservationIssues: ValidationIssue[];
};

type CommandRunner = typeof runCommand;

export function validateFamilyStructure(familyPlan: FamilyPlan): ValidationIssue[] {
  const issues: ValidationIssue[] = [];
  const ids = familyPlan.derivedTasks.map((task) => task.derivedTaskId);
  const outputs = familyPlan.derivedTasks.map((task) => task.primaryOutputFile);

  if (new Set(ids).size !== ids.length) {
    issues.push({ scope: "family", message: "derivedTaskId 存在重复" });
  }
  if (new Set(outputs).size !== outputs.length) {
    issues.push({ scope: "family", message: "primaryOutputFile 存在重复" });
  }

  if (familyPlan.skillMode === "per-skill") {
    if (!familyPlan.targetSkillDirName || !familyPlan.targetSkillName) {
      issues.push({ scope: "family", message: "per-skill family 缺少 target skill 元数据" });
    }

    const targetSkillSlug = familyPlan.targetSkillDirName ? slugify(familyPlan.targetSkillDirName) : null;
    for (const task of familyPlan.derivedTasks) {
      if (task.targetSkillDirName !== familyPlan.targetSkillDirName) {
        issues.push({
          scope: "family",
          taskId: task.derivedTaskId,
          message: "derived task 的 targetSkillDirName 与 family 不一致",
        });
      }
      if (task.targetSkillName !== familyPlan.targetSkillName) {
        issues.push({
          scope: "family",
          taskId: task.derivedTaskId,
          message: "derived task 的 targetSkillName 与 family 不一致",
        });
      }
      if (targetSkillSlug && !task.derivedTaskId.includes(targetSkillSlug)) {
        issues.push({
          scope: "family",
          taskId: task.derivedTaskId,
          message: `per-skill 任务的 derivedTaskId 未包含目标 skill slug，期望包含 ${targetSkillSlug}`,
        });
      }
    }
  }

  return issues;
}

export function collectFamilyObservationIssues(familyPlan: FamilyPlan): ValidationIssue[] {
  const issues: ValidationIssue[] = [];
  const similarCount = familyPlan.derivedTasks.filter((task) => task.taskRole === "similar").length;
  const transferCount = familyPlan.derivedTasks.filter((task) => task.taskRole === "transfer").length;

  if (similarCount !== 1 || transferCount !== 3) {
    issues.push({
      scope: "family",
      message: "family 角色布局不是 1 个 similar + 3 个 transfer",
    });
  }

  for (const task of familyPlan.derivedTasks) {
    if (task.taskRole === "similar" && !task.derivedTaskId.includes("-similar-")) {
      issues.push({
        scope: "family",
        taskId: task.derivedTaskId,
        message: "similar 任务的 derivedTaskId 未包含 -similar-",
      });
    }
    if (task.taskRole === "transfer" && !task.derivedTaskId.includes("-transfer-")) {
      issues.push({
        scope: "family",
        taskId: task.derivedTaskId,
        message: "transfer 任务的 derivedTaskId 未包含 -transfer-",
      });
    }
  }

  return issues;
}

function pushTaskIssue(
  taskIssuesById: Map<string, ValidationIssue[]>,
  taskId: string,
  issue: ValidationIssue,
): void {
  const issues = taskIssuesById.get(taskId) ?? [];
  issues.push(issue);
  taskIssuesById.set(taskId, issues);
}

type ParsedTaskMetadata = {
  stringValues: Map<string, string>;
  arrayValues: Map<string, string[]>;
};

function extractMetadataSection(taskToml: string): string[] {
  const lines = taskToml.split(/\r?\n/);
  const sectionLines: string[] = [];
  let inMetadata = false;

  for (const line of lines) {
    const trimmed = line.trim();
    if (/^\[[^\]]+\]$/.test(trimmed)) {
      if (trimmed === "[metadata]") {
        inMetadata = true;
        continue;
      }
      if (inMetadata) {
        break;
      }
    }

    if (inMetadata) {
      sectionLines.push(line);
    }
  }

  return sectionLines;
}

function parseTomlStringArray(rawValue: string): string[] | null {
  const trimmed = rawValue.trim();
  if (!trimmed.startsWith("[") || !trimmed.endsWith("]")) {
    return null;
  }

  const values: string[] = [];
  const valuePattern = /"([^"]*)"/g;
  for (const match of trimmed.matchAll(valuePattern)) {
    values.push(match[1] ?? "");
  }
  return values;
}

function parseTaskMetadata(taskToml: string): ParsedTaskMetadata {
  const stringValues = new Map<string, string>();
  const arrayValues = new Map<string, string[]>();
  const lines = extractMetadataSection(taskToml);

  let pendingArrayKey: string | null = null;
  let pendingArrayValue = "";

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) {
      continue;
    }

    if (pendingArrayKey) {
      pendingArrayValue += trimmed;
      if (trimmed.includes("]")) {
        const parsed = parseTomlStringArray(pendingArrayValue);
        if (parsed) {
          arrayValues.set(pendingArrayKey, parsed);
        }
        pendingArrayKey = null;
        pendingArrayValue = "";
      }
      continue;
    }

    const entryMatch = trimmed.match(/^([A-Za-z0-9_]+)\s*=\s*(.+)$/);
    if (!entryMatch) {
      continue;
    }

    const [, key, rawValue] = entryMatch;
    const value = rawValue.trim();

    if (value.startsWith("\"")) {
      const stringMatch = value.match(/^"([^"]*)"$/);
      if (stringMatch) {
        stringValues.set(key, stringMatch[1] ?? "");
      }
      continue;
    }

    if (value.startsWith("[")) {
      if (value.includes("]")) {
        const parsed = parseTomlStringArray(value);
        if (parsed) {
          arrayValues.set(key, parsed);
        }
      } else {
        pendingArrayKey = key;
        pendingArrayValue = value;
      }
    }
  }

  return {
    stringValues,
    arrayValues,
  };
}

function normalizeRelativePathForComparison(value: string): string {
  const normalized = value.replace(/\\/g, "/");
  return normalized.startsWith("./") ? normalized.slice(2) : normalized;
}

function matchesBlueprintPrimaryOutputFile(
  plan: DerivedTaskPlan,
  writerPrimaryOutputFile: string,
): boolean {
  if (writerPrimaryOutputFile === plan.primaryOutputFile) {
    return true;
  }

  if (plan.primaryOutputFile.includes("/") || plan.primaryOutputFile.includes("\\")) {
    return false;
  }

  const expectedDraftOutputPath = path.posix.join(
    "drafts",
    plan.derivedTaskId,
    "environment",
    plan.primaryOutputFile,
  );

  return normalizeRelativePathForComparison(writerPrimaryOutputFile) === expectedDraftOutputPath;
}

export async function validateDraftStatic(
  draftDir: string,
  plan: DerivedTaskPlan,
  sourceTaskId: string,
  writerSummary: WriterSummary,
): Promise<ValidationIssue[]> {
  const issues: ValidationIssue[] = [];
  const skillsDir = path.join(draftDir, "environment", "skills");
  const requiredFiles = [
    "task.toml",
    "instruction.md",
    path.join("environment", "Dockerfile"),
    path.join("solution", "solve.sh"),
    path.join("tests", "test.sh"),
    path.join("tests", "test_outputs.py"),
  ];

  for (const relativePath of requiredFiles) {
    if (!(await pathExists(path.join(draftDir, relativePath)))) {
      issues.push({
        scope: "static",
        taskId: plan.derivedTaskId,
        message: `缺少必备文件: ${relativePath}`,
      });
    }
  }

  if (!(await pathExists(skillsDir))) {
    issues.push({
      scope: "static",
      taskId: plan.derivedTaskId,
      message: "缺少 environment/skills 目录",
    });
  } else if (plan.targetSkillDirName) {
    const skillDirNames = (await fs.readdir(skillsDir, { withFileTypes: true }))
      .filter((entry) => entry.isDirectory())
      .map((entry) => entry.name)
      .sort((a, b) => a.localeCompare(b));

    if (skillDirNames.length !== 1) {
      issues.push({
        scope: "static",
        taskId: plan.derivedTaskId,
        message: `per-skill 任务必须且只能包含 1 个 skill，当前检测到 ${skillDirNames.length} 个`,
      });
    }

    if (skillDirNames[0] !== plan.targetSkillDirName) {
      issues.push({
        scope: "static",
        taskId: plan.derivedTaskId,
        message: `per-skill 任务的唯一 skill 应为 ${plan.targetSkillDirName}，当前为 ${skillDirNames[0] ?? "missing"}`,
      });
    }
  }

  const taskTomlPath = path.join(draftDir, "task.toml");
  if (await pathExists(taskTomlPath)) {
    const taskToml = await readText(taskTomlPath);
    const metadata = parseTaskMetadata(taskToml);
    const metadataId = metadata.stringValues.get("id");
    const metadataName = metadata.stringValues.get("name") ?? "";
    const metadataDescription = metadata.stringValues.get("description");
    const metadataAuthorName = metadata.stringValues.get("author_name");
    const metadataAuthorEmail = metadata.stringValues.get("author_email");
    const metadataDifficulty = metadata.stringValues.get("difficulty");
    const metadataCategory = metadata.stringValues.get("category");
    const metadataPrimaryOutputFile = metadata.stringValues.get("primary_output_file");
    const metadataSourceTaskId = metadata.stringValues.get("source_task_id");
    const metadataTaskRole = metadata.stringValues.get("task_role");
    const metadataTags = metadata.arrayValues.get("tags");

    if (metadataId !== plan.derivedTaskId) {
      issues.push({
        scope: "static",
        taskId: plan.derivedTaskId,
        message: `task.toml metadata.id=${metadataId ?? "missing"} 与目录名不一致`,
      });
    }

    if (plan.taskRole === "similar" && !metadataName.includes("Similar")) {
      issues.push({
        scope: "static",
        taskId: plan.derivedTaskId,
        message: "similar 任务的 metadata.name 未显式包含 Similar",
      });
    }

    if (plan.taskRole === "transfer" && !metadataName.includes("Transfer")) {
      issues.push({
        scope: "static",
        taskId: plan.derivedTaskId,
        message: "transfer 任务的 metadata.name 未显式包含 Transfer",
      });
    }

    const nonEmptyMetadataFields = [
      ["description", metadataDescription],
      ["author_name", metadataAuthorName],
      ["author_email", metadataAuthorEmail],
      ["difficulty", metadataDifficulty],
      ["category", metadataCategory],
    ] as const;

    for (const [fieldName, value] of nonEmptyMetadataFields) {
      if (!value || value.trim().length === 0) {
        issues.push({
          scope: "static",
          taskId: plan.derivedTaskId,
          message: `task.toml metadata.${fieldName} 缺失或为空`,
        });
      }
    }

    if (metadataPrimaryOutputFile !== plan.primaryOutputFile) {
      issues.push({
        scope: "static",
        taskId: plan.derivedTaskId,
        message: `task.toml metadata.primary_output_file=${metadataPrimaryOutputFile ?? "missing"} 与 blueprint 不一致`,
      });
    }

    if (metadataSourceTaskId !== sourceTaskId) {
      issues.push({
        scope: "static",
        taskId: plan.derivedTaskId,
        message: `task.toml metadata.source_task_id=${metadataSourceTaskId ?? "missing"} 与 sourceTaskId 不一致`,
      });
    }

    if (metadataTaskRole !== plan.taskRole) {
      issues.push({
        scope: "static",
        taskId: plan.derivedTaskId,
        message: `task.toml metadata.task_role=${metadataTaskRole ?? "missing"} 与 blueprint 不一致`,
      });
    }

    if (!metadataTags || metadataTags.length === 0) {
      issues.push({
        scope: "static",
        taskId: plan.derivedTaskId,
        message: "task.toml metadata.tags 缺失或为空数组",
      });
    }
  }

  const dockerfilePath = path.join(draftDir, "environment", "Dockerfile");
  if (await pathExists(dockerfilePath)) {
    const dockerfile = await readText(dockerfilePath);
    if (!dockerfile.includes("COPY skills /root/.codex/skills")) {
      issues.push({
        scope: "static",
        taskId: plan.derivedTaskId,
        message: "environment/Dockerfile 未保留 COPY skills /root/.codex/skills",
      });
    }
  }

  if (!matchesBlueprintPrimaryOutputFile(plan, writerSummary.primaryOutputFile)) {
    issues.push({
      scope: "static",
      taskId: plan.derivedTaskId,
      message: "writer 返回的 primaryOutputFile 与 blueprint 不一致",
    });
  }

  return issues;
}

export function validateReviewerResult(familyPlan: FamilyPlan, review: ReviewResult): ReviewValidationResult {
  const taskIssuesById = new Map<string, ValidationIssue[]>();
  const familyObservationIssues = [...collectFamilyObservationIssues(familyPlan)];
  const expectedTaskIds = new Set(familyPlan.derivedTasks.map((task) => task.derivedTaskId));
  const seenTaskIds = new Set<string>();

  for (const taskId of expectedTaskIds) {
    taskIssuesById.set(taskId, []);
  }

  for (const taskResult of review.taskResults) {
    if (!expectedTaskIds.has(taskResult.derivedTaskId)) {
      familyObservationIssues.push({
        scope: "family",
        message: `reviewer 返回了未知任务结果: ${taskResult.derivedTaskId}`,
      });
      continue;
    }

    seenTaskIds.add(taskResult.derivedTaskId);
    const issueParts = [...taskResult.issues];
    if (!taskResult.visibilityPass) {
      issueParts.push("visibilityPass=false");
    }
    if (!taskResult.skillBenefitPass) {
      issueParts.push("skillBenefitPass=false");
    }
    if (!taskResult.testabilityPass) {
      issueParts.push("testabilityPass=false");
    }

    if (!taskResult.pass || issueParts.length > 0) {
      pushTaskIssue(taskIssuesById, taskResult.derivedTaskId, {
        scope: "reviewer",
        taskId: taskResult.derivedTaskId,
        message: issueParts.join("; ") || "reviewer 判定失败，但未提供原因",
      });
    }
  }

  for (const taskId of expectedTaskIds) {
    if (!seenTaskIds.has(taskId)) {
      pushTaskIssue(taskIssuesById, taskId, {
        scope: "reviewer",
        taskId,
        message: "reviewer 未返回该任务的审查结果",
      });
    }
  }

  if (!review.familyObservations.diversityPass) {
    familyObservationIssues.push({
      scope: "family",
      message: "reviewer 认为 transfer 多样性不足",
    });
  }
  if (!review.familyObservations.roleLayoutPass) {
    familyObservationIssues.push({
      scope: "family",
      message: "reviewer 认为 family 角色布局不理想",
    });
  }
  for (const issue of review.familyObservations.issues) {
    familyObservationIssues.push({
      scope: "family",
      message: issue,
    });
  }

  return {
    taskIssuesById,
    familyObservationIssues,
  };
}

function compactOutputSummary(text: string): string {
  const lines = text
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
  if (lines.length === 0) {
    return "未提供错误输出";
  }
  return lines.slice(0, 3).join(" | ").slice(0, 400);
}

function isDockerEnvironmentFailure(output: string): boolean {
  return /cannot allocate memory|error getting credentials|no valid drivers found|utilacceptvsock|cannot connect to the docker daemon|permission denied while trying to connect/i.test(
    output,
  );
}

function readEnvValue(env: NodeJS.ProcessEnv, key: string): string | null {
  const raw = env[key];
  if (typeof raw !== "string") {
    return null;
  }

  const trimmed = raw.trim();
  return trimmed.length > 0 ? trimmed : null;
}

export function resolveRuntimeEnvironment(env: NodeJS.ProcessEnv = process.env): RuntimeEnvironment {
  const rawValue = readEnvValue(env, "CODEX_TASK_BUILDER_RUNTIME_ENV");
  if (!rawValue) {
    return "daytona";
  }

  const normalized = rawValue.toLowerCase();
  if (normalized === "daytona" || normalized === "docker") {
    return normalized;
  }

  throw new Error(
    `不支持的 CODEX_TASK_BUILDER_RUNTIME_ENV: ${rawValue}；仅支持 daytona 或 docker`,
  );
}

export function buildHarborRuntimeCommand(options: {
  taskDir: string;
  logsDir: string;
  jobName: string;
  runtimeEnvironment: RuntimeEnvironment;
}): string[] {
  return [
    "harbor",
    "run",
    "-p",
    options.taskDir,
    "-a",
    "oracle",
    "-e",
    options.runtimeEnvironment,
    "--force-build",
    "--jobs-dir",
    options.logsDir,
    "--job-name",
    options.jobName,
  ];
}

function runtimeIssue(taskId: string, message: string): ValidationIssue {
  return {
    scope: "runtime",
    taskId,
    message,
  };
}

function shellEscape(value: string): string {
  return `'${value.replace(/'/g, `'\"'\"'`)}'`;
}

async function findLatestTrialResultPath(jobDir: string): Promise<string | null> {
  if (!(await pathExists(jobDir))) {
    return null;
  }

  const entries = await fs.readdir(jobDir, { withFileTypes: true });
  const candidates: Array<{ path: string; mtimeMs: number }> = [];

  for (const entry of entries) {
    if (!entry.isDirectory()) {
      continue;
    }
    const resultPath = path.join(jobDir, entry.name, "result.json");
    if (!(await pathExists(resultPath))) {
      continue;
    }
    const stat = await fs.stat(resultPath);
    candidates.push({ path: resultPath, mtimeMs: stat.mtimeMs });
  }

  candidates.sort((a, b) => b.mtimeMs - a.mtimeMs);
  return candidates[0]?.path ?? null;
}

function parseFiniteNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function extractPrimaryReward(rewards: unknown): number | null {
  if (!rewards || typeof rewards !== "object") {
    return null;
  }
  const record = rewards as Record<string, unknown>;
  if ("reward" in record) {
    return parseFiniteNumber(record.reward);
  }

  const numericValues: number[] = [];
  for (const value of Object.values(record)) {
    const parsed = parseFiniteNumber(value);
    if (parsed !== null) {
      numericValues.push(parsed);
    }
  }

  if (numericValues.length === 1) {
    return numericValues[0] ?? null;
  }

  return null;
}

export async function runRuntimePreflight(
  runtimeEnvironment: RuntimeEnvironment,
  env: NodeJS.ProcessEnv = process.env,
  commandRunner: CommandRunner = runCommand,
): Promise<RuntimePreflightResult> {
  const details: string[] = [];

  const harborCheck = await commandRunner("bash", ["-lc", "command -v harbor >/dev/null 2>&1"], { env });
  if (harborCheck.code !== 0) {
    return {
      ok: false,
      summary: "当前环境未检测到 harbor CLI",
      details: ["command -v harbor 失败"],
    };
  }

  const harborVersion = await commandRunner("bash", ["-lc", "harbor --version"], { env });
  if (harborVersion.code !== 0) {
    const summary = compactOutputSummary(`${harborVersion.stdout}\n${harborVersion.stderr}`);
    return {
      ok: false,
      summary: `harbor --version 失败: ${summary}`,
      details: ["harbor --version 返回非零退出码", summary],
    };
  }
  details.push(`runtime environment: ${runtimeEnvironment}`);
  details.push(`harbor --version: ${compactOutputSummary(`${harborVersion.stdout}\n${harborVersion.stderr}`)}`);

  if (runtimeEnvironment === "daytona") {
    if (!readEnvValue(env, "DAYTONA_API_KEY")) {
      return {
        ok: false,
        summary: "当前环境未设置 DAYTONA_API_KEY",
        details: ["DAYTONA_API_KEY 缺失或为空"],
      };
    }

    return {
      ok: true,
      summary: "harbor + daytona preflight 通过",
      details,
    };
  }

  const dockerCheck = await commandRunner("bash", ["-lc", "command -v docker >/dev/null 2>&1"], { env });
  if (dockerCheck.code !== 0) {
    return {
      ok: false,
      summary: "当前环境未检测到 docker",
      details: ["command -v docker 失败"],
    };
  }

  const dockerInfo = await commandRunner("docker", ["info"], { env });
  if (dockerInfo.code !== 0) {
    const summary = compactOutputSummary(`${dockerInfo.stdout}\n${dockerInfo.stderr}`);
    return {
      ok: false,
      summary: `docker info 失败: ${summary}`,
      details: ["docker info 返回非零退出码", summary],
    };
  }

  const smokeBuild = await commandRunner("bash", [
    "-lc",
    "docker build --pull -q - <<'EOF'\nFROM busybox:1.36\nRUN true\nEOF",
  ], { env });
  if (smokeBuild.code !== 0) {
    const summary = compactOutputSummary(`${smokeBuild.stdout}\n${smokeBuild.stderr}`);
    return {
      ok: false,
      summary: `docker build preflight 失败: ${summary}`,
      details: ["docker build preflight 返回非零退出码", summary],
    };
  }

  return {
    ok: true,
    summary: "harbor + docker preflight 通过",
    details,
  };
}

export async function runRuntimeValidation(
  workspace: FamilyWorkspace,
  plan: DerivedTaskPlan,
  runtimeEnvironment: RuntimeEnvironment,
  env: NodeJS.ProcessEnv = process.env,
  commandRunner: CommandRunner = runCommand,
): Promise<RuntimeValidationResult> {
  const issues: ValidationIssue[] = [];
  const taskDir = path.join(workspace.draftsDir, plan.derivedTaskId);
  const logsDir = path.join(workspace.artifactsDir, "runtime-logs", plan.derivedTaskId);
  await ensureDir(logsDir);

  const harborCheck = await commandRunner("bash", ["-lc", "command -v harbor >/dev/null 2>&1"], { env });
  if (harborCheck.code !== 0) {
    return {
      issues: [runtimeIssue(plan.derivedTaskId, `harbor runtime 环境失败（${runtimeEnvironment}），详见 artifacts/runtime-logs`)],
      failureKind: "harbor-preflight",
    };
  }

  if (runtimeEnvironment === "docker") {
    const dockerCheck = await commandRunner("bash", ["-lc", "command -v docker >/dev/null 2>&1"], { env });
    if (dockerCheck.code !== 0) {
      return {
        issues: [runtimeIssue(plan.derivedTaskId, "harbor runtime 环境失败（docker），详见 artifacts/runtime-logs")],
        failureKind: "harbor-preflight",
      };
    }
  } else if (!readEnvValue(env, "DAYTONA_API_KEY")) {
    return {
      issues: [runtimeIssue(plan.derivedTaskId, "harbor runtime 环境失败（daytona 缺少 DAYTONA_API_KEY），详见 artifacts/runtime-logs")],
      failureKind: "harbor-preflight",
    };
  }

  const jobName = `harbor-oracle-${slugify(workspace.runId)}-${slugify(plan.derivedTaskId)}`;
  const harborCommand = buildHarborRuntimeCommand({
    taskDir,
    logsDir,
    jobName,
    runtimeEnvironment,
  })
    .map(shellEscape)
    .join(" ");

  const runResult = await commandRunner("bash", ["-lc", harborCommand], {
    cwd: workspace.rootDir,
    env,
  });
  await writeText(path.join(logsDir, "harbor-run.log"), `${runResult.stdout}${runResult.stderr}`);

  const jobDir = path.join(logsDir, jobName);
  const trialResultPath = await findLatestTrialResultPath(jobDir);
  if (!trialResultPath) {
    const summary = compactOutputSummary(`${runResult.stdout}\n${runResult.stderr}`);
    issues.push(runtimeIssue(plan.derivedTaskId, `harbor run 未产出可解析的 trial result.json: ${summary}`));
    return {
      issues,
      failureKind: "harbor-run",
    };
  }

  const trialResultRaw = await readText(trialResultPath);
  let trialResult: unknown;
  try {
    trialResult = JSON.parse(trialResultRaw) as unknown;
  } catch {
    issues.push(runtimeIssue(plan.derivedTaskId, "harbor trial result.json 解析失败，详见 artifacts/runtime-logs"));
    return {
      issues,
      failureKind: "harbor-run",
    };
  }

  if (!trialResult || typeof trialResult !== "object") {
    issues.push(runtimeIssue(plan.derivedTaskId, "harbor trial result.json 结构异常，详见 artifacts/runtime-logs"));
    return {
      issues,
      failureKind: "harbor-run",
    };
  }

  const resultRecord = trialResult as Record<string, unknown>;
  const exceptionInfo = resultRecord.exception_info;
  if (exceptionInfo && typeof exceptionInfo === "object") {
    const exception = exceptionInfo as Record<string, unknown>;
    const exceptionType = typeof exception.exception_type === "string" ? exception.exception_type : "Unknown";
    const exceptionMessage =
      typeof exception.exception_message === "string"
        ? exception.exception_message.slice(0, 200)
        : "未提供 exception_message";
    issues.push(runtimeIssue(plan.derivedTaskId, `harbor oracle 运行异常: ${exceptionType}: ${exceptionMessage}`));
    return {
      issues,
      failureKind: "harbor-run",
    };
  }

  const verifierResult = resultRecord.verifier_result;
  const rewards = verifierResult && typeof verifierResult === "object" ? (verifierResult as Record<string, unknown>).rewards : null;
  const reward = extractPrimaryReward(rewards);
  if (reward === null) {
    issues.push(runtimeIssue(plan.derivedTaskId, "harbor verifier 未产出 reward（reward.txt/reward.json），详见 artifacts/runtime-logs"));
    return {
      issues,
      failureKind: "harbor-run",
    };
  }

  if (reward < 1.0) {
    issues.push(runtimeIssue(plan.derivedTaskId, `harbor verifier reward=${reward} < 1.0`));
    return {
      issues,
      failureKind: "harbor-reward",
    };
  }

  if (runResult.code !== 0) {
    const summary = compactOutputSummary(`${runResult.stdout}\n${runResult.stderr}`);
    issues.push(runtimeIssue(plan.derivedTaskId, `harbor run 返回非零退出码: ${summary}`));
    return {
      issues,
      failureKind: "harbor-run",
    };
  }

  return {
    issues,
  };
}
