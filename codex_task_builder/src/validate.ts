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

export type RuntimeFailureKind = "docker-preflight" | "docker-build" | "docker-run";

export type DockerPreflightResult = {
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

export async function validateDraftStatic(
  draftDir: string,
  plan: DerivedTaskPlan,
  writerSummary: WriterSummary,
): Promise<ValidationIssue[]> {
  const issues: ValidationIssue[] = [];
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

  if (!(await pathExists(path.join(draftDir, "environment", "skills")))) {
    issues.push({
      scope: "static",
      taskId: plan.derivedTaskId,
      message: "缺少 environment/skills 目录",
    });
  }

  const taskTomlPath = path.join(draftDir, "task.toml");
  if (await pathExists(taskTomlPath)) {
    const taskToml = await readText(taskTomlPath);
    const idMatch = taskToml.match(/^\s*id\s*=\s*"([^"]+)"/m);
    const nameMatch = taskToml.match(/^\s*name\s*=\s*"([^"]+)"/m);
    const metadataId = idMatch?.[1];
    const metadataName = nameMatch?.[1] ?? "";

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

  if (writerSummary.primaryOutputFile !== plan.primaryOutputFile) {
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

function runtimeIssue(taskId: string, message: string): ValidationIssue {
  return {
    scope: "runtime",
    taskId,
    message,
  };
}

export async function runDockerPreflight(): Promise<DockerPreflightResult> {
  const dockerCheck = await runCommand("bash", ["-lc", "command -v docker >/dev/null 2>&1"]);
  if (dockerCheck.code !== 0) {
    return {
      ok: false,
      summary: "当前环境未检测到 docker",
      details: ["command -v docker 失败"],
    };
  }

  const dockerInfo = await runCommand("docker", ["info"]);
  if (dockerInfo.code !== 0) {
    const summary = compactOutputSummary(`${dockerInfo.stdout}\n${dockerInfo.stderr}`);
    return {
      ok: false,
      summary: `docker info 失败: ${summary}`,
      details: ["docker info 返回非零退出码", summary],
    };
  }

  const smokeBuild = await runCommand("bash", [
    "-lc",
    "docker build --pull -q - <<'EOF'\nFROM busybox:1.36\nRUN true\nEOF",
  ]);
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
    summary: "docker preflight 通过",
    details: [],
  };
}

export async function runRuntimeValidation(
  workspace: FamilyWorkspace,
  plan: DerivedTaskPlan,
): Promise<RuntimeValidationResult> {
  const issues: ValidationIssue[] = [];
  const taskDir = path.join(workspace.draftsDir, plan.derivedTaskId);
  const environmentDir = path.join(taskDir, "environment");
  const solutionDir = path.join(taskDir, "solution");
  const testsDir = path.join(taskDir, "tests");
  const logsDir = path.join(workspace.artifactsDir, "runtime-logs", plan.derivedTaskId);
  await ensureDir(logsDir);

  const dockerCheck = await runCommand("bash", ["-lc", "command -v docker >/dev/null 2>&1"]);
  if (dockerCheck.code !== 0) {
    return {
      issues: [runtimeIssue(plan.derivedTaskId, "docker/WSL 环境失败，详见 artifacts/runtime-logs")],
      failureKind: "docker-preflight",
    };
  }

  const imageTag = `harbor-task-builder-${slugify(workspace.runId)}-${slugify(plan.derivedTaskId)}`;
  const buildResult = await runCommand("docker", ["build", "-t", imageTag, "."], {
    cwd: environmentDir,
  });
  await writeText(path.join(logsDir, "docker-build.log"), `${buildResult.stdout}${buildResult.stderr}`);
  if (buildResult.code !== 0) {
    const combinedOutput = `${buildResult.stdout}\n${buildResult.stderr}`;
    issues.push(
      runtimeIssue(
        plan.derivedTaskId,
        isDockerEnvironmentFailure(combinedOutput)
          ? "docker/WSL 环境失败，详见 artifacts/runtime-logs"
          : "docker build 失败，详见 artifacts/runtime-logs",
      ),
    );
    return {
      issues,
      failureKind: "docker-build",
    };
  }

  const containerName = `harbor-task-builder-${slugify(workspace.runId)}-${slugify(plan.derivedTaskId)}-${Date.now()}`;
  const runResult = await runCommand(
    "docker",
    [
      "run",
      "--name",
      containerName,
      "-v",
      `${solutionDir}:/solution:ro`,
      "-v",
      `${testsDir}:/tests:ro`,
      "-v",
      `${logsDir}:/logs`,
      imageTag,
      "bash",
      "-lc",
      "bash /solution/solve.sh && bash /tests/test.sh",
    ],
    {
      cwd: workspace.rootDir,
    },
  );

  await writeText(path.join(logsDir, "docker-run.log"), `${runResult.stdout}${runResult.stderr}`);
  if (runResult.code !== 0) {
    issues.push(runtimeIssue(plan.derivedTaskId, "solution/test 运行失败，详见 artifacts/runtime-logs"));
    return {
      issues,
      failureKind: "docker-run",
    };
  }

  return {
    issues,
  };
}
