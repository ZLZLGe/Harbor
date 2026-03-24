import { createHash } from "node:crypto";
import { promises as fs } from "node:fs";
import path from "node:path";

import { Codex } from "@openai/codex-sdk";

import {
  copyDir,
  ensureDir,
  parseJsonWithFallback,
  pathExists,
  readText,
  runCommand,
  slugify,
  writeJson,
  writeText,
} from "../src/utils.ts";

const REPO_ROOT = "/home/levi/Harbor";
const DEFAULT_CLASSIFICATION_TSVS = [
  path.join(
    REPO_ROOT,
    "tasks_library",
    "perSkill_unpublished_oracle_classified",
    "Daytona_runtime_20260324_0503",
    "reports",
    "classification.tsv",
  ),
  path.join(
    REPO_ROOT,
    "tasks_library",
    "perSkill_unpublished_oracle_classified",
    "Daytona_20260324_0435",
    "reports",
    "classification.tsv",
  ),
];
const DEFAULT_TARGET_ROOTS = [
  path.join(REPO_ROOT, "tasks_library", "perSkill_unpublished_static_combo_fixed", "pass"),
  path.join(REPO_ROOT, "tasks_library", "perSkill_unpublished_reviewer_rereview", "pass"),
  path.join(REPO_ROOT, "tasks_library", "perSkill_unpublished_reviewer_fixed", "pass"),
  path.join(REPO_ROOT, "tasks_library", "perSkill_unpublished", "runtime__runtime-harbor-run"),
];
const RUNS_ROOT = path.join(
  REPO_ROOT,
  "codex_task_builder",
  "tmp",
  "reward_file_not_found_batch_repair_runs",
);
const DEFAULT_CONCURRENCY = 20;
const DEFAULT_MAX_ATTEMPTS = 3;
const MAX_STDOUT_CHARS = 14_000;
const MAX_PROMPT_STDOUT_CHARS = 8_000;
const REPAIR_SCHEMA = {
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

type Options = {
  classificationTsvs: string[];
  targetRoots: string[];
  concurrency: number;
  maxAttempts: number;
  runId: string;
  dryRun: boolean;
  taskLimit: number | null;
};

type TsvRow = Record<string, string>;

type RootKind = "runtime" | "pass";

type FailureBucket =
  | "missing_reward_write"
  | "network_install_failure"
  | "missing_uv_env_after_install"
  | "python_dependency_missing"
  | "tests_failed_before_reward_write"
  | "no_stdout"
  | "other_stdout";

type RepairTurnResult = {
  summary: string;
  changedFiles: string[];
};

type TaskRecord = {
  key: string;
  taskPath: string;
  taskId: string;
  taskPathHash: string;
  targetRoot: string;
  rootKind: RootKind;
  family: string;
  skillDirName: string | null;
  runtimeRunId: string | null;
  sourceTaskId: string;
  classificationSources: string[];
  inputRootIds: string[];
  trialDirs: string[];
  trialResultPaths: string[];
  jobDirs: string[];
  exceptionTypes: string[];
  failureReasons: string[];
  exceptionMessage: string;
  stdoutExcerpt: string;
  failureBucket: FailureBucket;
  taskRelativePath: string;
};

type PrecheckIssue = {
  severity: "critical" | "warning";
  code: string;
  message: string;
};

type PrecheckResult = {
  issues: PrecheckIssue[];
  criticalIssueCount: number;
  warningCount: number;
  shellSyntaxOk: boolean;
  solveSyntaxOk: boolean | null;
  tomlValid: boolean;
  pythonCompileOk: boolean;
  pythonCompileFailures: string[];
  hasLogsDirMkdir: boolean;
  hasRewardWrite: boolean;
  rewardWriteOccurrences: number;
  hasSetE: boolean;
  hasPipefail: boolean;
  hasSetPlusE: boolean;
  hasPipeStatus: boolean;
  hasTestStatusHandling: boolean;
  hasInlineTestCondition: boolean;
  hasPytestInvocation: boolean;
  hasDirectTestOutputsInvocation: boolean;
  hasPipedTestCommand: boolean;
  hasRuntimeInstallSteps: boolean;
  runtimeInstallPatterns: string[];
  issueCodes: string[];
};

type CandidateRecord = {
  label: string;
  attempt: number;
  snapshotPath: string;
  summary: string;
  changedFiles: string[];
  precheck: PrecheckResult;
  repairThreadId: string | null;
};

type AttemptRecord = {
  attempt: number;
  promptPath: string;
  snapshotPath: string;
  repairThreadId: string | null;
  summary: string;
  changedFiles: string[];
  precheck: PrecheckResult;
};

type TaskRunRecord = {
  taskPath: string;
  targetRoot: string;
  rootKind: RootKind;
  family: string;
  taskId: string;
  failureBucket: FailureBucket;
  promoted: boolean;
  promotedWithIssues: boolean;
  bestLabel: string;
  bestAttempt: number;
  baseline: CandidateRecord;
  best: CandidateRecord;
  attempts: AttemptRecord[];
  workspaceRoot: string;
  writebackPath: string;
};

function nowIso(): string {
  return new Date().toISOString();
}

function log(message: string): void {
  console.log(`[${nowIso()}] ${message}`);
}

function sha1(value: string): string {
  return createHash("sha1").update(value).digest("hex");
}

function truncateText(value: string, maxChars: number): string {
  if (value.length <= maxChars) {
    return value;
  }
  return `${value.slice(0, maxChars)}\n...[truncated ${value.length - maxChars} chars]`;
}

function parseArgs(argv: string[]): Options {
  const classificationTsvs: string[] = [];
  const targetRoots: string[] = [];
  let concurrency = DEFAULT_CONCURRENCY;
  let maxAttempts = DEFAULT_MAX_ATTEMPTS;
  let runId = `rfnf-repair-${new Date().toISOString().replace(/[-:TZ.]/g, "").slice(0, 14)}`;
  let dryRun = false;
  let taskLimit: number | null = null;

  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === "--classification-tsv") {
      classificationTsvs.push(argv[index + 1] ?? "");
      index += 1;
      continue;
    }
    if (token === "--target-root") {
      targetRoots.push(argv[index + 1] ?? "");
      index += 1;
      continue;
    }
    if (token === "--concurrency") {
      concurrency = Number(argv[index + 1] ?? `${DEFAULT_CONCURRENCY}`);
      index += 1;
      continue;
    }
    if (token === "--max-attempts") {
      maxAttempts = Number(argv[index + 1] ?? `${DEFAULT_MAX_ATTEMPTS}`);
      index += 1;
      continue;
    }
    if (token === "--run-id") {
      runId = argv[index + 1] ?? runId;
      index += 1;
      continue;
    }
    if (token === "--task-limit") {
      taskLimit = Number(argv[index + 1] ?? "0");
      index += 1;
      continue;
    }
    if (token === "--dry-run") {
      dryRun = true;
      continue;
    }
  }

  return {
    classificationTsvs: classificationTsvs.filter((value) => value.trim().length > 0).length > 0
      ? classificationTsvs.filter((value) => value.trim().length > 0)
      : [...DEFAULT_CLASSIFICATION_TSVS],
    targetRoots: targetRoots.filter((value) => value.trim().length > 0).length > 0
      ? targetRoots.filter((value) => value.trim().length > 0)
      : [...DEFAULT_TARGET_ROOTS],
    concurrency: Number.isFinite(concurrency) && concurrency > 0 ? concurrency : DEFAULT_CONCURRENCY,
    maxAttempts: Number.isFinite(maxAttempts) && maxAttempts >= 0 ? maxAttempts : DEFAULT_MAX_ATTEMPTS,
    runId,
    dryRun,
    taskLimit: taskLimit !== null && Number.isFinite(taskLimit) && taskLimit > 0 ? taskLimit : null,
  };
}

function parseTsv(text: string): TsvRow[] {
  const lines = text.split(/\r?\n/).filter((line) => line.length > 0);
  if (lines.length === 0) {
    return [];
  }
  const header = lines[0].split("\t");
  const rows: TsvRow[] = [];
  for (const line of lines.slice(1)) {
    const cells = line.split("\t");
    const row: TsvRow = {};
    for (let index = 0; index < header.length; index += 1) {
      row[header[index] as string] = cells[index] ?? "";
    }
    rows.push(row);
  }
  return rows;
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function firstMatchIndex(value: string, pattern: RegExp): number {
  const match = pattern.exec(value);
  return match?.index ?? -1;
}

function compareNumberTuples(left: number[], right: number[]): number {
  const max = Math.max(left.length, right.length);
  for (let index = 0; index < max; index += 1) {
    const l = left[index] ?? 0;
    const r = right[index] ?? 0;
    if (l < r) {
      return -1;
    }
    if (l > r) {
      return 1;
    }
  }
  return 0;
}

function detectRuntimeInstallPatterns(scriptText: string): string[] {
  const patterns = new Set<string>();
  if (/\bapt-get\s+install\b/.test(scriptText)) {
    patterns.add("apt-get install");
  }
  if (/\bpip3?\s+install\b/.test(scriptText) || /\bpython3?\s+-m\s+pip\s+install\b/.test(scriptText)) {
    patterns.add("pip install");
  }
  if (/curl\s+-LsSf\s+https:\/\/astral\.sh\/uv/.test(scriptText)) {
    patterns.add("curl uv installer");
  }
  if (/\buvx\b/.test(scriptText)) {
    patterns.add("uvx");
  }
  if (/source\s+["']?\$HOME\/\.local\/bin\/env/.test(scriptText) || /source\s+\$HOME\/\.local\/bin\/env/.test(scriptText)) {
    patterns.add("source $HOME/.local/bin/env");
  }
  return Array.from(patterns).sort((a, b) => a.localeCompare(b));
}

function findVerifierLogVars(scriptText: string): string[] {
  const variableNames = new Set<string>();
  for (const line of scriptText.split(/\r?\n/)) {
    const match = line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)=(["'])?\/logs\/verifier\2\s*$/);
    if (match?.[1]) {
      variableNames.add(match[1]);
    }
  }
  return Array.from(variableNames).sort((a, b) => a.localeCompare(b));
}

function buildVerifierLogMkdirPatterns(scriptText: string): RegExp[] {
  const patterns = [/mkdir\s+-p\s+\/logs\/verifier\b/];
  for (const variableName of findVerifierLogVars(scriptText)) {
    patterns.push(new RegExp(`mkdir\\s+-p\\s+["']?\\$\\{?${escapeRegExp(variableName)}\\}?["']?`));
  }
  return patterns;
}

function classifyFailureBucket(stdoutText: string, testScriptText: string): FailureBucket {
  if (!/reward\.(?:txt|json)/.test(testScriptText)) {
    return "missing_reward_write";
  }
  if (!stdoutText.trim()) {
    return "no_stdout";
  }
  if (/Resolving timed out|Temporary failure resolving|Could not resolve/i.test(stdoutText)) {
    return "network_install_failure";
  }
  if (/\/root\/\.local\/bin\/env: No such file or directory/.test(stdoutText)) {
    return "missing_uv_env_after_install";
  }
  if (/ModuleNotFoundError|No module named\b/i.test(stdoutText)) {
    return "python_dependency_missing";
  }
  if (/FAILED|AssertionError|=== FAILURES ===|short test summary info/i.test(stdoutText)) {
    return "tests_failed_before_reward_write";
  }
  return "other_stdout";
}

async function listRelativeFiles(rootDir: string): Promise<string[]> {
  const results: string[] = [];

  async function walk(currentDir: string, relativeDir: string): Promise<void> {
    const entries = await fs.readdir(currentDir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(currentDir, entry.name);
      const relativePath = relativeDir ? path.posix.join(relativeDir, entry.name) : entry.name;
      if (entry.isDirectory()) {
        if (entry.name === "__pycache__") {
          continue;
        }
        await walk(fullPath, relativePath);
        continue;
      }
      if (entry.isFile()) {
        results.push(relativePath);
      }
    }
  }

  if (!(await pathExists(rootDir))) {
    return [];
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
  const sourceFiles = new Set(await listRelativeFiles(sourceRoot));
  const candidateFiles = new Set(await listRelativeFiles(candidateRoot));
  const allFiles = new Set([...sourceFiles, ...candidateFiles]);
  const changed: string[] = [];

  for (const relativePath of Array.from(allFiles).sort((a, b) => a.localeCompare(b))) {
    const sourceText = await readFileOrNull(path.join(sourceRoot, relativePath));
    const candidateText = await readFileOrNull(path.join(candidateRoot, relativePath));
    if (sourceText !== candidateText) {
      changed.push(relativePath);
    }
  }

  return changed;
}

async function replaceDir(sourceDir: string, targetDir: string): Promise<void> {
  await fs.rm(targetDir, { recursive: true, force: true }).catch(() => {});
  await copyDir(sourceDir, targetDir);
}

async function writeJsonl(filePath: string, rows: unknown[]): Promise<void> {
  const content = rows.map((row) => JSON.stringify(row)).join("\n");
  await writeText(filePath, content.length > 0 ? `${content}\n` : "");
}

async function readJsonIfExists<T>(filePath: string): Promise<T | null> {
  if (!(await pathExists(filePath))) {
    return null;
  }
  const raw = await readText(filePath);
  return parseJsonWithFallback<T>(raw);
}

function deriveTaskLocation(taskPath: string, targetRoot: string): {
  rootKind: RootKind;
  family: string;
  taskRelativePath: string;
  skillDirName: string | null;
  runtimeRunId: string | null;
} {
  const relativePath = path.relative(targetRoot, taskPath);
  const parts = relativePath.split(path.sep).filter((value) => value.length > 0);
  const family = parts[0] ?? "unknown-family";
  const rootKind: RootKind = targetRoot.endsWith(`runtime__runtime-harbor-run`) ? "runtime" : "pass";
  return {
    rootKind,
    family,
    taskRelativePath: relativePath,
    skillDirName: rootKind === "runtime" ? (parts[1] ?? null) : null,
    runtimeRunId: rootKind === "runtime" ? (parts[2] ?? null) : null,
  };
}

async function collectRewardFileNotFoundTasks(options: Options): Promise<TaskRecord[]> {
  const byTaskPath = new Map<string, TaskRecord>();

  for (const classificationTsv of options.classificationTsvs) {
    const rows = parseTsv(await readText(classificationTsv));
    for (const row of rows) {
      const failureReason = row.failure_reason ?? "";
      const exceptionType = row.exception_type ?? "";
      if (failureReason !== "RewardFileNotFoundError" && exceptionType !== "RewardFileNotFoundError") {
        continue;
      }

      const taskPath = row.task_dir || row.task_path || row.resolved_task_path || "";
      if (!taskPath) {
        continue;
      }

      const normalizedTaskPath = path.resolve(taskPath);
      const matchedRoot = options.targetRoots.find((root) => {
        const normalizedRoot = path.resolve(root);
        return normalizedTaskPath === normalizedRoot || normalizedTaskPath.startsWith(`${normalizedRoot}${path.sep}`);
      });
      if (!matchedRoot) {
        continue;
      }

      const testScriptPath = path.join(normalizedTaskPath, "tests", "test.sh");
      const testScriptText = (await pathExists(testScriptPath)) ? await readText(testScriptPath) : "";
      const trialDir = row.trial_dir || "";
      const trialResultPath = row.trial_result_path || (trialDir ? path.join(trialDir, "result.json") : "");
      const resultJson = trialResultPath ? await readJsonIfExists<Record<string, unknown>>(trialResultPath) : null;
      const stdoutPath = trialDir ? path.join(trialDir, "verifier", "test-stdout.txt") : "";
      const stdoutText = stdoutPath && (await pathExists(stdoutPath)) ? await readText(stdoutPath) : "";
      const exceptionInfo = resultJson?.exception_info as Record<string, unknown> | undefined;
      const exceptionMessage = typeof exceptionInfo?.exception_message === "string"
        ? exceptionInfo.exception_message
        : "";
      const location = deriveTaskLocation(normalizedTaskPath, matchedRoot);
      const taskId = path.basename(normalizedTaskPath);
      const sourceTaskId = row.family_name || location.family;
      const failureBucket = classifyFailureBucket(stdoutText, testScriptText);

      const existing = byTaskPath.get(normalizedTaskPath);
      if (existing) {
        existing.classificationSources.push(classificationTsv);
        if (row.input_root_id) {
          existing.inputRootIds.push(row.input_root_id);
        }
        if (trialDir) {
          existing.trialDirs.push(trialDir);
        }
        if (trialResultPath) {
          existing.trialResultPaths.push(trialResultPath);
        }
        if (row.job_dir) {
          existing.jobDirs.push(row.job_dir);
        }
        if (exceptionType) {
          existing.exceptionTypes.push(exceptionType);
        }
        if (failureReason) {
          existing.failureReasons.push(failureReason);
        }
        if (!existing.exceptionMessage && exceptionMessage) {
          existing.exceptionMessage = exceptionMessage;
        }
        if (!existing.stdoutExcerpt && stdoutText) {
          existing.stdoutExcerpt = truncateText(stdoutText, MAX_STDOUT_CHARS);
        }
        continue;
      }

      const taskRecord: TaskRecord = {
        key: normalizedTaskPath,
        taskPath: normalizedTaskPath,
        taskId,
        taskPathHash: sha1(normalizedTaskPath).slice(0, 12),
        targetRoot: path.resolve(matchedRoot),
        rootKind: location.rootKind,
        family: location.family,
        skillDirName: location.skillDirName,
        runtimeRunId: location.runtimeRunId,
        sourceTaskId,
        classificationSources: [classificationTsv],
        inputRootIds: row.input_root_id ? [row.input_root_id] : [],
        trialDirs: trialDir ? [trialDir] : [],
        trialResultPaths: trialResultPath ? [trialResultPath] : [],
        jobDirs: row.job_dir ? [row.job_dir] : [],
        exceptionTypes: exceptionType ? [exceptionType] : [],
        failureReasons: failureReason ? [failureReason] : [],
        exceptionMessage,
        stdoutExcerpt: truncateText(stdoutText, MAX_STDOUT_CHARS),
        failureBucket,
        taskRelativePath: location.taskRelativePath,
      };
      byTaskPath.set(normalizedTaskPath, taskRecord);
    }
  }

  let tasks = Array.from(byTaskPath.values()).sort((left, right) => left.taskPath.localeCompare(right.taskPath));
  if (options.taskLimit !== null) {
    tasks = tasks.slice(0, options.taskLimit);
  }
  return tasks;
}

async function bashSyntaxCheck(filePath: string): Promise<{ ok: boolean; message: string }> {
  const result = await runCommand("bash", ["-n", filePath]);
  return {
    ok: result.code === 0,
    message: result.code === 0 ? "ok" : (result.stderr || result.stdout || `bash -n failed for ${filePath}`).trim(),
  };
}

async function tomlSyntaxCheck(filePath: string): Promise<{ ok: boolean; message: string }> {
  const result = await runCommand(
    "python3",
    [
      "-c",
      "import sys, tomllib; tomllib.load(open(sys.argv[1], 'rb'))",
      filePath,
    ],
  );
  return {
    ok: result.code === 0,
    message: result.code === 0 ? "ok" : (result.stderr || result.stdout || `toml parse failed for ${filePath}`).trim(),
  };
}

async function pythonCompileCheck(taskDir: string): Promise<{ ok: boolean; failures: string[] }> {
  const relativeFiles = await listRelativeFiles(taskDir);
  const pythonFiles = relativeFiles
    .filter((relativePath) => relativePath.endsWith(".py"))
    .map((relativePath) => path.join(taskDir, relativePath));
  if (pythonFiles.length === 0) {
    return { ok: true, failures: [] };
  }

  const result = await runCommand("python3", ["-m", "py_compile", ...pythonFiles]);
  if (result.code === 0) {
    return { ok: true, failures: [] };
  }

  const output = (result.stderr || result.stdout || "python compile failed").trim();
  return {
    ok: false,
    failures: [truncateText(output, 2_000)],
  };
}

async function runPrecheck(taskDir: string, task: TaskRecord): Promise<PrecheckResult> {
  const issues: PrecheckIssue[] = [];
  const testScriptPath = path.join(taskDir, "tests", "test.sh");
  const solveScriptPath = path.join(taskDir, "solution", "solve.sh");
  const taskTomlPath = path.join(taskDir, "task.toml");

  let shellSyntaxOk = true;
  let solveSyntaxOk: boolean | null = null;
  let tomlValid = true;
  let pythonCompileOk = true;
  let pythonCompileFailures: string[] = [];

  if (!(await pathExists(testScriptPath))) {
    issues.push({
      severity: "critical",
      code: "missing_test_script",
      message: "tests/test.sh is missing.",
    });
  }

  const testScriptText = (await pathExists(testScriptPath)) ? await readText(testScriptPath) : "";

  if (await pathExists(testScriptPath)) {
    const shellCheck = await bashSyntaxCheck(testScriptPath);
    shellSyntaxOk = shellCheck.ok;
    if (!shellCheck.ok) {
      issues.push({
        severity: "critical",
        code: "test_script_shell_syntax",
        message: shellCheck.message,
      });
    }
  }

  if (await pathExists(solveScriptPath)) {
    const solveCheck = await bashSyntaxCheck(solveScriptPath);
    solveSyntaxOk = solveCheck.ok;
    if (!solveCheck.ok) {
      issues.push({
        severity: "critical",
        code: "solve_script_shell_syntax",
        message: solveCheck.message,
      });
    }
  }

  if (await pathExists(taskTomlPath)) {
    const tomlCheck = await tomlSyntaxCheck(taskTomlPath);
    tomlValid = tomlCheck.ok;
    if (!tomlCheck.ok) {
      issues.push({
        severity: "critical",
        code: "invalid_task_toml",
        message: tomlCheck.message,
      });
    }
  }

  const pyCompile = await pythonCompileCheck(taskDir);
  pythonCompileOk = pyCompile.ok;
  pythonCompileFailures = pyCompile.failures;
  if (!pyCompile.ok) {
    issues.push({
      severity: "critical",
      code: "python_compile_failed",
      message: pyCompile.failures.join("\n"),
    });
  }

  const mkdirPatterns = buildVerifierLogMkdirPatterns(testScriptText);
  const mkdirIndices = mkdirPatterns.map((pattern) => firstMatchIndex(testScriptText, pattern)).filter((value) => value >= 0);
  const hasLogsDirMkdir = mkdirIndices.length > 0;
  const hasRewardWrite = /reward\.(?:txt|json)/.test(testScriptText);
  const rewardWriteOccurrences = testScriptText.match(/reward\.(?:txt|json)/g)?.length ?? 0;
  const hasSetE = /(^|\n)\s*set\s+-[^\n]*e/.test(testScriptText);
  const hasPipefail = /pipefail/.test(testScriptText);
  const hasSetPlusE = /(^|\n)\s*set\s+\+e\b/.test(testScriptText);
  const hasPipeStatus = /PIPESTATUS\[0\]/.test(testScriptText);
  const hasPytestInvocation = /\bpytest\b/.test(testScriptText);
  const hasDirectTestOutputsInvocation = /\/tests\/test_outputs\.py/.test(testScriptText);
  const hasInlineTestCondition = /if\s+.+(?:pytest|\/tests\/test_outputs\.py).+;\s*then/s.test(testScriptText);
  const hasExitCapture = /\b[A-Za-z_][A-Za-z0-9_]*\s*=\s*\$\?/.test(testScriptText) || hasPipeStatus;
  const hasTestStatusHandling = hasInlineTestCondition || hasExitCapture;
  const hasPipedTestCommand = testScriptText
    .split(/\r?\n/)
    .some((line) => /(?:pytest|\/tests\/test_outputs\.py)/.test(line) && line.includes("|"));
  const runtimeInstallPatterns = detectRuntimeInstallPatterns(testScriptText);
  const hasRuntimeInstallSteps = runtimeInstallPatterns.length > 0;

  const mkdirIndex = mkdirIndices.length > 0 ? Math.min(...mkdirIndices) : -1;
  const earliestTestIndex = (() => {
    const indices = [
      firstMatchIndex(testScriptText, /\bpytest\b/),
      firstMatchIndex(testScriptText, /python3?\s+\/tests\/test_outputs\.py/),
      firstMatchIndex(testScriptText, /python3?\s+-m\s+pytest\b/),
      firstMatchIndex(testScriptText, /\buvx\b/),
    ].filter((value) => value >= 0);
    return indices.length > 0 ? Math.min(...indices) : -1;
  })();

  if (!hasLogsDirMkdir) {
    issues.push({
      severity: "critical",
      code: "missing_logs_dir_mkdir",
      message: "tests/test.sh does not create /logs/verifier with mkdir -p.",
    });
  } else if (earliestTestIndex >= 0 && mkdirIndex > earliestTestIndex) {
    issues.push({
      severity: "critical",
      code: "logs_dir_created_too_late",
      message: "tests/test.sh creates /logs/verifier after the test command starts.",
    });
  }

  if (!hasRewardWrite) {
    issues.push({
      severity: "critical",
      code: "missing_reward_write",
      message: "tests/test.sh does not write reward.txt or reward.json.",
    });
  }

  if ((hasPytestInvocation || hasDirectTestOutputsInvocation) && !hasTestStatusHandling) {
    issues.push({
      severity: "critical",
      code: "missing_test_status_handling",
      message: "tests/test.sh runs tests but does not explicitly capture or branch on the test exit status.",
    });
  }

  const unsafeSetEPath =
    hasSetE &&
    (hasPytestInvocation || hasDirectTestOutputsInvocation) &&
    !hasSetPlusE &&
    !hasInlineTestCondition &&
    !/(\|\|\s*true|\|\|\s*:) /.test(testScriptText.replace(/\n/g, " "));
  if (unsafeSetEPath) {
    issues.push({
      severity: "critical",
      code: "set_e_without_guard",
      message: "set -e is present around the test command without a local guard that ensures reward writing still happens on failure.",
    });
  }

  if (hasSetE && hasPipefail && hasPipedTestCommand && !hasSetPlusE && !hasInlineTestCondition) {
    issues.push({
      severity: "critical",
      code: "pipefail_pipeline_without_guard",
      message: "A piped test command runs under set -e + pipefail without a local guard, so the script can exit before reward is written.",
    });
  }

  if (hasRuntimeInstallSteps) {
    issues.push({
      severity: "warning",
      code: "runtime_install_steps_in_verifier",
      message: `tests/test.sh still performs runtime installation steps: ${runtimeInstallPatterns.join(", ")}.`,
    });
  }

  switch (task.failureBucket) {
    case "missing_reward_write":
      if (!hasRewardWrite) {
        issues.push({
          severity: "critical",
          code: "unresolved_original_missing_reward_write",
          message: "The original RewardFileNotFound failure maps directly to a missing reward write, and that remains unresolved.",
        });
      }
      break;
    case "tests_failed_before_reward_write":
      if (!hasRewardWrite || !hasTestStatusHandling || unsafeSetEPath || (hasPipefail && hasPipedTestCommand && !hasSetPlusE)) {
        issues.push({
          severity: "critical",
          code: "unresolved_original_test_failure_path",
          message: "The original trial showed tests failing before reward was written, and the verifier wrapper still has an unsafe failure path.",
        });
      } else {
        issues.push({
          severity: "warning",
          code: "original_trial_failed_runtime_behavior_unverified",
          message: "The original trial had failing tests; local precheck cannot confirm the new runtime behavior without Harbor execution.",
        });
      }
      break;
    case "network_install_failure":
      if (hasRuntimeInstallSteps) {
        issues.push({
          severity: "warning",
          code: "unresolved_network_install_risk",
          message: "The original verifier failed during runtime installation, and tests/test.sh still contains network-dependent install steps.",
        });
      }
      break;
    case "missing_uv_env_after_install":
      if (/source\s+["']?\$HOME\/\.local\/bin\/env/.test(testScriptText) || /curl\s+-LsSf\s+https:\/\/astral\.sh\/uv/.test(testScriptText)) {
        issues.push({
          severity: "warning",
          code: "unresolved_uv_env_risk",
          message: "The original verifier failed after a runtime uv install, and tests/test.sh still uses the same uv bootstrap pattern.",
        });
      }
      break;
    case "python_dependency_missing":
      if (hasRuntimeInstallSteps) {
        issues.push({
          severity: "warning",
          code: "runtime_dependency_resolution_still_in_verifier",
          message: "The original failure mentioned missing Python dependencies, and dependency resolution is still deferred to tests/test.sh.",
        });
      }
      break;
    case "no_stdout":
      if (!hasRewardWrite || !hasTestStatusHandling) {
        issues.push({
          severity: "critical",
          code: "unresolved_no_stdout_reward_flow",
          message: "The original verifier produced no stdout and the local reward flow is still incomplete.",
        });
      }
      break;
    case "other_stdout":
      if (issues.length === 0) {
        issues.push({
          severity: "warning",
          code: "original_failure_not_explained_by_static_precheck",
          message: "The original RewardFileNotFound failure is not fully explained by local precheck, so the runtime cause may still remain.",
        });
      }
      break;
  }

  const uniqueIssues = new Map<string, PrecheckIssue>();
  for (const issue of issues) {
    const key = `${issue.severity}:${issue.code}:${issue.message}`;
    if (!uniqueIssues.has(key)) {
      uniqueIssues.set(key, issue);
    }
  }
  const dedupedIssues = Array.from(uniqueIssues.values());

  return {
    issues: dedupedIssues,
    criticalIssueCount: dedupedIssues.filter((issue) => issue.severity === "critical").length,
    warningCount: dedupedIssues.filter((issue) => issue.severity === "warning").length,
    shellSyntaxOk,
    solveSyntaxOk,
    tomlValid,
    pythonCompileOk,
    pythonCompileFailures,
    hasLogsDirMkdir,
    hasRewardWrite,
    rewardWriteOccurrences,
    hasSetE,
    hasPipefail,
    hasSetPlusE,
    hasPipeStatus,
    hasTestStatusHandling,
    hasInlineTestCondition,
    hasPytestInvocation,
    hasDirectTestOutputsInvocation,
    hasPipedTestCommand,
    hasRuntimeInstallSteps,
    runtimeInstallPatterns,
    issueCodes: dedupedIssues.map((issue) => issue.code),
  };
}

function scoreCandidate(candidate: CandidateRecord): number[] {
  return [
    candidate.precheck.criticalIssueCount,
    candidate.precheck.warningCount,
    candidate.changedFiles.length,
    candidate.attempt,
  ];
}

function isCandidateBetter(candidate: CandidateRecord, best: CandidateRecord): boolean {
  return compareNumberTuples(scoreCandidate(candidate), scoreCandidate(best)) < 0;
}

function buildIssueBlock(issues: PrecheckIssue[]): string {
  if (issues.length === 0) {
    return "- none";
  }
  return issues
    .map((issue) => `- [${issue.severity}] ${issue.code}: ${issue.message}`)
    .join("\n");
}

function buildRepairPrompt(task: TaskRecord, baseline: CandidateRecord): string {
  const runtimeLocationBlock = task.rootKind === "runtime"
    ? [
      `- skill dir: ${task.skillDirName ?? "unknown"}`,
      `- runtime run id: ${task.runtimeRunId ?? "unknown"}`,
    ].join("\n")
    : "- pass-root task";
  const stdoutBlock = task.stdoutExcerpt.trim().length > 0
    ? `\nVerifier stdout excerpt:\n\`\`\`\n${truncateText(task.stdoutExcerpt, MAX_PROMPT_STDOUT_CHARS)}\n\`\`\`\n`
    : "\nVerifier stdout excerpt:\n```text\n<empty>\n```\n";

  return [
    "You are repairing one Harbor task copy that previously failed with RewardFileNotFoundError.",
    "Only modify files inside the current task directory. Do not edit any repository code outside this task. Do not add metadata files or helper scripts outside the task.",
    "Preserve the task's identity and intent. Prefer the smallest change that removes the RewardFileNotFound cause.",
    "",
    "Task identity:",
    `- target root: ${task.targetRoot}`,
    `- task path: ${task.taskPath}`,
    `- source task id: ${task.sourceTaskId}`,
    `- family: ${task.family}`,
    `- task id: ${task.taskId}`,
    runtimeLocationBlock,
    "",
    "Observed original failure:",
    `- failure bucket: ${task.failureBucket}`,
    `- exception message: ${task.exceptionMessage || "<missing>"}`,
    `- classification sources: ${task.classificationSources.join(", ") || "<missing>"}`,
    stdoutBlock.trimEnd(),
    "",
    "Current local precheck issues for this candidate:",
    buildIssueBlock(baseline.precheck.issues),
    "",
    "Harbor oracle constraints you must satisfy:",
    "- For RewardFileNotFound, default to fixing only `tests/test.sh` and, if needed, `environment/Dockerfile`. Only touch solution files, task logic, or task assets if a verifier-wrapper-only fix would still be insufficient.",
    "- tests/test.sh must run `mkdir -p /logs/verifier` before any verifier log, ctrf, or reward write.",
    "- Do not just run pytest or python test_outputs.py and exit. Explicitly capture or branch on the test status.",
    "- If set -e or pipefail is present, ensure a failing test still reaches reward writing. Use a local `set +e` region or an equivalent guarded pattern if needed.",
    "- tests/test.sh must always write `/logs/verifier/reward.txt` or `/logs/verifier/reward.json` on both pass and fail paths.",
    "- Prefer this order: create logs dir, run tests and capture status, write reward, copy optional artifacts, exit with the captured status.",
    "- Avoid runtime dependency installation in tests/test.sh. If a dependency is truly required, move it to environment/Dockerfile when possible.",
    "- Keep the task deterministic and local. Do not introduce online APIs, online models, or unstable external services.",
    "",
    "Allowed files to edit:",
    "- tests/test.sh",
    "- tests/test_outputs.py",
    "- solution/solve.sh",
    "- environment/Dockerfile",
    "- environment/* input assets if absolutely necessary",
    "- task.toml",
    "- instruction.md",
    "",
    "Return strict JSON:",
    "{",
    '  "summary": "short repair summary",',
    '  "changedFiles": ["relative/path1", "relative/path2"]',
    "}",
  ].join("\n");
}

function makeRepairCodex(): Codex {
  return new Codex({
    codexPathOverride: process.env.CODEX_PATH,
    config: {
      sandbox_workspace_write: {
        network_access: true,
      },
    },
  });
}

async function runRepairAttempt(candidateDir: string, prompt: string): Promise<{
  repairThreadId: string | null;
  result: RepairTurnResult;
}> {
  const codex = makeRepairCodex();
  const thread = codex.startThread({
    workingDirectory: candidateDir,
    sandboxMode: "workspace-write",
    approvalPolicy: "never",
    skipGitRepoCheck: true,
    networkAccessEnabled: true,
    model: process.env.CODEX_TASK_BUILDER_MODEL,
    modelReasoningEffort: "high",
  });

  const turn = await thread.run(prompt, {
    outputSchema: REPAIR_SCHEMA,
  });
  return {
    repairThreadId: thread.id,
    result: parseJsonWithFallback<RepairTurnResult>(turn.finalResponse),
  };
}

async function runWithRetries<T>(label: string, action: () => Promise<T>, retries: number): Promise<T> {
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

async function processTask(task: TaskRecord, runRoot: string, maxAttempts: number): Promise<TaskRunRecord> {
  const workspaceSlug = `${slugify(task.family)}-${slugify(task.taskId)}-${task.taskPathHash}`;
  const workspaceRoot = path.join(runRoot, "workspaces", workspaceSlug);
  const baselineSnapshot = path.join(workspaceRoot, "baseline");
  const bestSnapshot = path.join(workspaceRoot, "best");
  const candidateDir = path.join(workspaceRoot, "candidate");
  const attemptsRoot = path.join(workspaceRoot, "attempts");

  await ensureDir(workspaceRoot);
  await ensureDir(attemptsRoot);
  await replaceDir(task.taskPath, baselineSnapshot);
  await replaceDir(task.taskPath, bestSnapshot);
  await replaceDir(task.taskPath, candidateDir);

  const baselinePrecheck = await runPrecheck(baselineSnapshot, task);
  const baselineChangedFiles = await diffChangedFiles(task.taskPath, baselineSnapshot);
  const baselineCandidate: CandidateRecord = {
    label: "baseline",
    attempt: 0,
    snapshotPath: baselineSnapshot,
    summary: "original task state",
    changedFiles: baselineChangedFiles,
    precheck: baselinePrecheck,
    repairThreadId: null,
  };

  const attempts: AttemptRecord[] = [];
  let best = baselineCandidate;

  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    await replaceDir(best.snapshotPath, candidateDir);

    const prompt = buildRepairPrompt(task, best);
    const promptPath = path.join(attemptsRoot, `attempt-${attempt}.prompt.txt`);
    await writeText(promptPath, `${prompt}\n`);

    let repairThreadId: string | null = null;
    let repairSummary = "";
    let changedFiles: string[] = [];

    try {
      const repairResult = await runWithRetries(
        `repair ${task.taskId} attempt ${attempt}`,
        () => runRepairAttempt(candidateDir, prompt),
        1,
      );
      repairThreadId = repairResult.repairThreadId;
      repairSummary = repairResult.result.summary;
      changedFiles = repairResult.result.changedFiles;
    } catch (error) {
      repairSummary = error instanceof Error ? error.message : String(error);
    }

    const precheck = await runPrecheck(candidateDir, task);
    const actualChangedFiles = await diffChangedFiles(task.taskPath, candidateDir);
    const snapshotPath = path.join(attemptsRoot, `attempt-${attempt}`);
    await replaceDir(candidateDir, snapshotPath);

    const candidate: CandidateRecord = {
      label: `attempt-${attempt}`,
      attempt,
      snapshotPath,
      summary: repairSummary,
      changedFiles: actualChangedFiles.length > 0 ? actualChangedFiles : changedFiles,
      precheck,
      repairThreadId,
    };
    attempts.push({
      attempt,
      promptPath,
      snapshotPath,
      repairThreadId,
      summary: repairSummary,
      changedFiles: candidate.changedFiles,
      precheck,
    });

    if (isCandidateBetter(candidate, best)) {
      best = candidate;
      await replaceDir(candidate.snapshotPath, bestSnapshot);
    }

    if (best.precheck.criticalIssueCount === 0 && best.precheck.warningCount === 0) {
      break;
    }
  }

  const promoted = best.label !== "baseline";
  const promotedWithIssues = promoted && (best.precheck.criticalIssueCount > 0 || best.precheck.warningCount > 0);
  if (promoted) {
    await replaceDir(best.snapshotPath, task.taskPath);
  }

  return {
    taskPath: task.taskPath,
    targetRoot: task.targetRoot,
    rootKind: task.rootKind,
    family: task.family,
    taskId: task.taskId,
    failureBucket: task.failureBucket,
    promoted,
    promotedWithIssues,
    bestLabel: best.label,
    bestAttempt: best.attempt,
    baseline: baselineCandidate,
    best,
    attempts,
    workspaceRoot,
    writebackPath: task.taskPath,
  };
}

function summarizeTasks(tasks: TaskRecord[]): {
  totalTasks: number;
  byTargetRoot: Record<string, number>;
  byFailureBucket: Record<string, number>;
} {
  const byTargetRoot = Object.fromEntries(tasks.map((task) => [task.targetRoot, 0]));
  const byFailureBucket: Record<string, number> = {};

  for (const task of tasks) {
    byTargetRoot[task.targetRoot] = (byTargetRoot[task.targetRoot] ?? 0) + 1;
    byFailureBucket[task.failureBucket] = (byFailureBucket[task.failureBucket] ?? 0) + 1;
  }

  return {
    totalTasks: tasks.length,
    byTargetRoot,
    byFailureBucket,
  };
}

function summarizeRuns(taskRuns: TaskRunRecord[]): {
  totalTasks: number;
  promoted: number;
  promotedWithIssues: number;
  baselineRetained: number;
  byFailureBucket: Record<string, number>;
} {
  const byFailureBucket: Record<string, number> = {};
  for (const run of taskRuns) {
    byFailureBucket[run.failureBucket] = (byFailureBucket[run.failureBucket] ?? 0) + 1;
  }
  return {
    totalTasks: taskRuns.length,
    promoted: taskRuns.filter((run) => run.promoted).length,
    promotedWithIssues: taskRuns.filter((run) => run.promotedWithIssues).length,
    baselineRetained: taskRuns.filter((run) => !run.promoted).length,
    byFailureBucket,
  };
}

async function main(): Promise<void> {
  const options = parseArgs(process.argv.slice(2));
  const runRoot = path.join(RUNS_ROOT, options.runId);
  const reportsRoot = path.join(runRoot, "reports");
  await ensureDir(reportsRoot);

  log(`collecting RewardFileNotFound tasks for run ${options.runId}`);
  const tasks = await collectRewardFileNotFoundTasks(options);
  const taskSummary = summarizeTasks(tasks);

  const manifest = {
    generatedAt: nowIso(),
    runId: options.runId,
    dryRun: options.dryRun,
    concurrency: options.concurrency,
    maxAttempts: options.maxAttempts,
    classificationTsvs: options.classificationTsvs,
    targetRoots: options.targetRoots,
    taskSummary,
  };
  await writeJson(path.join(runRoot, "manifest.json"), manifest);
  await writeJsonl(
    path.join(runRoot, "tasks.jsonl"),
    tasks.map((task) => ({
      taskPath: task.taskPath,
      targetRoot: task.targetRoot,
      rootKind: task.rootKind,
      family: task.family,
      taskId: task.taskId,
      sourceTaskId: task.sourceTaskId,
      skillDirName: task.skillDirName,
      runtimeRunId: task.runtimeRunId,
      failureBucket: task.failureBucket,
      exceptionMessage: task.exceptionMessage,
      classificationSources: task.classificationSources,
      trialDirs: task.trialDirs,
    })),
  );

  log(`found ${tasks.length} RewardFileNotFound tasks`);
  if (options.dryRun) {
    await writeJson(path.join(reportsRoot, "summary.json"), {
      ...manifest,
      mode: "dry-run",
    });
    console.log(JSON.stringify({
      runId: options.runId,
      dryRun: true,
      totalTasks: taskSummary.totalTasks,
      byTargetRoot: taskSummary.byTargetRoot,
      byFailureBucket: taskSummary.byFailureBucket,
    }, null, 2));
    return;
  }

  if (!process.env.OPENAI_API_KEY) {
    throw new Error("OPENAI_API_KEY is not set. Codex SDK repair cannot run.");
  }

  log(`repairing ${tasks.length} tasks with concurrency=${options.concurrency}, maxAttempts=${options.maxAttempts}`);
  const taskRuns = await runPool(tasks, options.concurrency, async (task, index) => {
    log(`task ${index + 1}/${tasks.length}: ${task.taskPath}`);
    const result = await processTask(task, runRoot, options.maxAttempts);
    log(`finished ${index + 1}/${tasks.length}: ${task.taskId} -> ${result.bestLabel}`);
    return result;
  });

  const runSummary = summarizeRuns(taskRuns);
  await writeJson(path.join(reportsRoot, "summary.json"), {
    generatedAt: nowIso(),
    runId: options.runId,
    dryRun: false,
    concurrency: options.concurrency,
    maxAttempts: options.maxAttempts,
    taskSummary,
    runSummary,
  });
  await writeJsonl(
    path.join(reportsRoot, "tasks.jsonl"),
    taskRuns.map((run) => ({
      taskPath: run.taskPath,
      targetRoot: run.targetRoot,
      rootKind: run.rootKind,
      family: run.family,
      taskId: run.taskId,
      failureBucket: run.failureBucket,
      promoted: run.promoted,
      promotedWithIssues: run.promotedWithIssues,
      bestLabel: run.bestLabel,
      bestAttempt: run.bestAttempt,
      baselineScore: scoreCandidate(run.baseline),
      bestScore: scoreCandidate(run.best),
      bestIssues: run.best.precheck.issues,
      changedFiles: run.best.changedFiles,
      attempts: run.attempts.map((attempt) => ({
        attempt: attempt.attempt,
        repairThreadId: attempt.repairThreadId,
        summary: attempt.summary,
        changedFiles: attempt.changedFiles,
        score: [
          attempt.precheck.criticalIssueCount,
          attempt.precheck.warningCount,
          attempt.changedFiles.length,
          attempt.attempt,
        ],
        issues: attempt.precheck.issues,
      })),
      workspaceRoot: run.workspaceRoot,
      writebackPath: run.writebackPath,
    })),
  );
  await writeText(
    path.join(reportsRoot, "promoted.tsv"),
    [
      ["task_path", "promoted", "promoted_with_issues", "best_label", "best_attempt", "writeback_path"].join("\t"),
      ...taskRuns.map((run) => [
        run.taskPath,
        run.promoted ? "1" : "0",
        run.promotedWithIssues ? "1" : "0",
        run.bestLabel,
        `${run.bestAttempt}`,
        run.writebackPath,
      ].join("\t")),
    ].join("\n") + "\n",
  );

  console.log(JSON.stringify({
    runId: options.runId,
    dryRun: false,
    totalTasks: taskSummary.totalTasks,
    promoted: runSummary.promoted,
    promotedWithIssues: runSummary.promotedWithIssues,
    baselineRetained: runSummary.baselineRetained,
    byTargetRoot: taskSummary.byTargetRoot,
    byFailureBucket: taskSummary.byFailureBucket,
  }, null, 2));
}

void main().catch((error) => {
  const message = error instanceof Error ? error.stack ?? error.message : String(error);
  console.error(message);
  process.exitCode = 1;
});
