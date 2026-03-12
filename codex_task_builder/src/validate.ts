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
  scope: "family" | "static" | "runtime";
  message: string;
  taskId?: string;
};

export function validateFamilyStructure(familyPlan: FamilyPlan): ValidationIssue[] {
  const issues: ValidationIssue[] = [];
  const ids = familyPlan.derivedTasks.map((task) => task.derivedTaskId);
  const outputs = familyPlan.derivedTasks.map((task) => task.primaryOutputFile);
  const similarCount = familyPlan.derivedTasks.filter((task) => task.taskRole === "similar").length;
  const transferCount = familyPlan.derivedTasks.filter((task) => task.taskRole === "transfer").length;

  if (new Set(ids).size !== ids.length) {
    issues.push({ scope: "family", message: "derivedTaskId 存在重复" });
  }
  if (new Set(outputs).size !== outputs.length) {
    issues.push({ scope: "family", message: "primaryOutputFile 存在重复" });
  }
  if (similarCount !== 1 || transferCount !== 3) {
    issues.push({ scope: "family", message: "family 角色布局不是 1 个 similar + 3 个 transfer" });
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

export async function validateReviewerResult(review: ReviewResult): Promise<ValidationIssue[]> {
  const issues: ValidationIssue[] = [];
  if (!review.pass) {
    issues.push({
      scope: "family",
      message: `reviewer 判定失败: ${review.issues.join("; ") || "未提供原因"}`,
    });
  }
  return issues;
}

export async function runRuntimeValidation(
  workspace: FamilyWorkspace,
  plan: DerivedTaskPlan,
): Promise<ValidationIssue[]> {
  const issues: ValidationIssue[] = [];
  const taskDir = path.join(workspace.draftsDir, plan.derivedTaskId);
  const environmentDir = path.join(taskDir, "environment");
  const solutionDir = path.join(taskDir, "solution");
  const testsDir = path.join(taskDir, "tests");
  const logsDir = path.join(workspace.artifactsDir, "runtime-logs", plan.derivedTaskId);
  await ensureDir(logsDir);

  const dockerCheck = await runCommand("bash", ["-lc", "command -v docker >/dev/null 2>&1"]);
  if (dockerCheck.code !== 0) {
    return [
      {
        scope: "runtime",
        taskId: plan.derivedTaskId,
        message: "当前环境未检测到 docker，无法执行运行校验",
      },
    ];
  }

  const imageTag = `harbor-task-builder-${slugify(workspace.runId)}-${slugify(plan.derivedTaskId)}`;
  const buildResult = await runCommand("docker", ["build", "-t", imageTag, "."], {
    cwd: environmentDir,
  });
  await writeText(path.join(logsDir, "docker-build.log"), `${buildResult.stdout}${buildResult.stderr}`);
  if (buildResult.code !== 0) {
    issues.push({
      scope: "runtime",
      taskId: plan.derivedTaskId,
      message: "docker build 失败，详见 artifacts/runtime-logs",
    });
    return issues;
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
      "chmod +x /solution/solve.sh /tests/test.sh && /solution/solve.sh && /tests/test.sh",
    ],
    {
      cwd: workspace.rootDir,
    },
  );

  await writeText(path.join(logsDir, "docker-run.log"), `${runResult.stdout}${runResult.stderr}`);
  if (runResult.code !== 0) {
    issues.push({
      scope: "runtime",
      taskId: plan.derivedTaskId,
      message: "solution/test 运行失败，详见 artifacts/runtime-logs",
    });
  }

  return issues;
}
