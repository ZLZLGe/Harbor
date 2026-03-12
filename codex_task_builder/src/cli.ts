import path from "node:path";
import { CodexTaskBuilderClient } from "./codex.js";
import { collectEnvironmentAssetPaths, discoverSourceTaskById, discoverSourceTasks, type SourceTask } from "./discovery.js";
import { appendManifest, writeRunSummary } from "./manifest.js";
import { publishFamily } from "./materialize.js";
import type { DerivedTaskPlan, FamilyPlan, WriterSummary } from "./schema.js";
import {
  INTEGRATED_TASKS_ROOT,
  SOURCE_TASKS_ROOT,
  ensureDir,
  formatIssueList,
  makeRunId,
  pathExists,
  readText,
  writeJson,
} from "./utils.js";
import {
  createFamilyWorkspace,
  findLatestWorkspaceForSource,
  prepareDraftSkeleton,
  type FamilyWorkspace,
} from "./workspace.js";
import {
  collectFamilyObservationIssues,
  runDockerPreflight,
  runRuntimeValidation,
  validateDraftStatic,
  validateFamilyStructure,
  validateReviewerResult,
  type DockerPreflightResult,
  type RuntimeFailureKind,
  type ValidationIssue,
} from "./validate.js";

type Options = Record<string, string | boolean>;

type FamilyExecutionResult = {
  sourceTaskId: string;
  runId?: string;
  status: "completed" | "failed" | "skipped";
  issues: string[];
  familyObservationIssues: string[];
  publishedTaskIds: string[];
  skippedTaskIds: string[];
  failedTaskIds: string[];
  publishedDir?: string;
};

type TaskExecutionState = {
  derivedTaskId: string;
  draftDir: string;
  reviewerIssues: ValidationIssue[];
  staticIssues: ValidationIssue[];
  runtimeIssues: ValidationIssue[];
  runtimeFailureKind?: RuntimeFailureKind;
  validateIssues: ValidationIssue[];
  eligibleForPublish: boolean;
};

function parseArgs(argv: string[]): { command: string | undefined; options: Options } {
  const [command, ...rest] = argv;
  const options: Options = {};

  for (let index = 0; index < rest.length; index += 1) {
    const token = rest[index];
    if (!token.startsWith("--")) {
      continue;
    }
    const key = token.slice(2);
    const next = rest[index + 1];
    if (!next || next.startsWith("--")) {
      options[key] = true;
      continue;
    }
    options[key] = next;
    index += 1;
  }

  return { command, options };
}

function getStringOption(options: Options, key: string, fallback?: string): string | undefined {
  const value = options[key];
  if (typeof value === "string") {
    return value;
  }
  return fallback;
}

function getNumberOption(options: Options, key: string, fallback: number): number {
  const value = getStringOption(options, key);
  if (!value) {
    return fallback;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function sortIssues(issues: ValidationIssue[]): string[] {
  return issues.map((issue) => `${issue.scope}${issue.taskId ? `:${issue.taskId}` : ""} ${issue.message}`);
}

function collectRuntimeFailureKinds(taskStates: TaskExecutionState[]): Record<string, RuntimeFailureKind> {
  return Object.fromEntries(
    taskStates
      .filter((task) => task.runtimeFailureKind)
      .map((task) => [task.derivedTaskId, task.runtimeFailureKind as RuntimeFailureKind]),
  );
}

async function inventory(sourceRoot: string): Promise<void> {
  const tasks = await discoverSourceTasks(sourceRoot);
  const rows = await Promise.all(
    tasks.map(async (task) => ({
      sourceTaskId: task.sourceTaskId,
      difficulty: task.metadata.difficulty ?? null,
      category: task.metadata.category ?? null,
      skillNames: task.skills.map((skill) => skill.name),
      environmentAssets: await collectEnvironmentAssetPaths(task),
    })),
  );
  console.log(JSON.stringify(rows, null, 2));
}

async function executeFamilyGeneration(
  sourceTask: SourceTask,
  options: {
    outputRoot: string;
  },
): Promise<FamilyExecutionResult> {
  const workspace = await createFamilyWorkspace(sourceTask);
  await appendManifest({
    runId: workspace.runId,
    sourceTaskId: sourceTask.sourceTaskId,
    phase: "workspace",
    status: "completed",
    metadata: { rootDir: workspace.rootDir },
  });

  const codex = new CodexTaskBuilderClient();
  const familyPlanResult = await codex.planFamily(sourceTask, workspace);
  const familyPlan = familyPlanResult.data;
  const writerSummaries = new Map<string, WriterSummary>();
  const familyObservationIssues = sortIssues(collectFamilyObservationIssues(familyPlan));
  await writeJson(path.join(workspace.artifactsDir, "family-plan.json"), familyPlan);
  await writeJson(path.join(workspace.artifactsDir, "family-plan.raw.json"), {
    threadId: familyPlanResult.threadId,
    raw: familyPlanResult.raw,
  });

  await appendManifest({
    runId: workspace.runId,
    sourceTaskId: sourceTask.sourceTaskId,
    phase: "planner",
    status: "completed",
    threadId: familyPlanResult.threadId,
  });

  const blockingFamilyIssues = validateFamilyStructure(familyPlan);
  if (blockingFamilyIssues.length > 0) {
    const issues = sortIssues(blockingFamilyIssues);
    await appendManifest({
      runId: workspace.runId,
      sourceTaskId: sourceTask.sourceTaskId,
      phase: "validate",
      status: "failed",
      issues,
    });
    await writeRunSummary(workspace.runId, {
      sourceTaskId: sourceTask.sourceTaskId,
      status: "failed",
      issues,
      familyObservationIssues,
      publishedTaskIds: [],
      skippedTaskIds: [],
      failedTaskIds: familyPlan.derivedTasks.map((task) => task.derivedTaskId),
      workspace,
    });
    return {
      sourceTaskId: sourceTask.sourceTaskId,
      runId: workspace.runId,
      status: "failed",
      issues,
      familyObservationIssues,
      publishedTaskIds: [],
      skippedTaskIds: [],
      failedTaskIds: familyPlan.derivedTasks.map((task) => task.derivedTaskId),
    };
  }

  for (const plan of familyPlan.derivedTasks) {
    const draftDir = await prepareDraftSkeleton(workspace, sourceTask, plan);
    const writerResult = await codex.writeTask(sourceTask, workspace, plan);
    writerSummaries.set(plan.derivedTaskId, writerResult.data);
    await writeJson(path.join(workspace.artifactsDir, `${plan.derivedTaskId}.writer.json`), writerResult.data);
    await writeJson(path.join(workspace.artifactsDir, `${plan.derivedTaskId}.writer.raw.json`), {
      threadId: writerResult.threadId,
      raw: writerResult.raw,
    });
    await appendManifest({
      runId: workspace.runId,
      sourceTaskId: sourceTask.sourceTaskId,
      derivedTaskId: plan.derivedTaskId,
      phase: "writer",
      status: "completed",
      threadId: writerResult.threadId,
      draftDir,
    });
  }

  const reviewResult = await codex.reviewFamily(sourceTask, workspace, familyPlan);
  const reviewValidation = validateReviewerResult(familyPlan, reviewResult.data);
  const reviewerTaskFailures = Array.from(reviewValidation.taskIssuesById.values()).flat();
  const reviewerIssues = sortIssues(reviewerTaskFailures);
  const mergedFamilyObservationIssues = [
    ...new Set([...familyObservationIssues, ...sortIssues(reviewValidation.familyObservationIssues)]),
  ];
  const reviewerPassedTaskIds = familyPlan.derivedTasks
    .map((task) => task.derivedTaskId)
    .filter((taskId) => (reviewValidation.taskIssuesById.get(taskId) ?? []).length === 0);
  const reviewerFailedTaskIds = familyPlan.derivedTasks
    .map((task) => task.derivedTaskId)
    .filter((taskId) => (reviewValidation.taskIssuesById.get(taskId) ?? []).length > 0);
  await writeJson(path.join(workspace.artifactsDir, "review-result.json"), reviewResult.data);
  await writeJson(path.join(workspace.artifactsDir, "review-result.raw.json"), {
    threadId: reviewResult.threadId,
    raw: reviewResult.raw,
  });
  await appendManifest({
    runId: workspace.runId,
    sourceTaskId: sourceTask.sourceTaskId,
    phase: "reviewer",
    status: "completed",
    threadId: reviewResult.threadId,
    issues: [...reviewerIssues, ...mergedFamilyObservationIssues],
    metadata: {
      passedTaskIds: reviewerPassedTaskIds,
      failedTaskIds: reviewerFailedTaskIds,
      familyObservationIssues: mergedFamilyObservationIssues,
    },
  });

  for (const plan of familyPlan.derivedTasks) {
    const taskReviewerIssues = sortIssues(reviewValidation.taskIssuesById.get(plan.derivedTaskId) ?? []);
    await appendManifest({
      runId: workspace.runId,
      sourceTaskId: sourceTask.sourceTaskId,
      derivedTaskId: plan.derivedTaskId,
      phase: "reviewer",
      status: taskReviewerIssues.length > 0 ? "failed" : "completed",
      threadId: reviewResult.threadId,
      draftDir: path.join(workspace.draftsDir, plan.derivedTaskId),
      issues: taskReviewerIssues,
    });
  }

  const taskStates: TaskExecutionState[] = [];
  for (const plan of familyPlan.derivedTasks) {
    const draftDir = path.join(workspace.draftsDir, plan.derivedTaskId);
    const writerSummary = writerSummaries.get(plan.derivedTaskId);
    const reviewerIssuesForTask = reviewValidation.taskIssuesById.get(plan.derivedTaskId) ?? [];
    const staticIssues: ValidationIssue[] = [];

    if (!writerSummary) {
      staticIssues.push({
        scope: "static",
        taskId: plan.derivedTaskId,
        message: "缺少 writer summary",
      });
    } else {
      staticIssues.push(...(await validateDraftStatic(draftDir, plan, writerSummary)));
    }

    const runtimeValidation =
      reviewerIssuesForTask.length === 0 && staticIssues.length === 0
        ? await runRuntimeValidation(workspace, plan)
        : { issues: [] };
    const runtimeIssues = runtimeValidation.issues;
    const validateIssues = [...reviewerIssuesForTask, ...staticIssues, ...runtimeIssues];
    const eligibleForPublish = validateIssues.length === 0;

    taskStates.push({
      derivedTaskId: plan.derivedTaskId,
      draftDir,
      reviewerIssues: reviewerIssuesForTask,
      staticIssues,
      runtimeIssues,
      runtimeFailureKind: runtimeValidation.failureKind,
      validateIssues,
      eligibleForPublish,
    });

    await appendManifest({
      runId: workspace.runId,
      sourceTaskId: sourceTask.sourceTaskId,
      derivedTaskId: plan.derivedTaskId,
      phase: "validate",
      status: eligibleForPublish ? "completed" : "failed",
      draftDir,
      issues: sortIssues(validateIssues),
      metadata: runtimeValidation.failureKind ? { runtimeFailureKind: runtimeValidation.failureKind } : undefined,
    });
  }

  const failedValidationIssues = taskStates
    .filter((task) => task.validateIssues.length > 0)
    .flatMap((task) => sortIssues(task.validateIssues));
  const runtimeFailureKindsByTaskId = collectRuntimeFailureKinds(taskStates);
  await appendManifest({
    runId: workspace.runId,
    sourceTaskId: sourceTask.sourceTaskId,
    phase: "validate",
    status: "completed",
    issues: failedValidationIssues,
    metadata: {
      eligibleTaskIds: taskStates.filter((task) => task.eligibleForPublish).map((task) => task.derivedTaskId),
      ineligibleTaskIds: taskStates.filter((task) => !task.eligibleForPublish).map((task) => task.derivedTaskId),
      runtimeFailureKindsByTaskId,
    },
  });

  const eligiblePlans = familyPlan.derivedTasks.filter((plan) =>
    taskStates.some((task) => task.derivedTaskId === plan.derivedTaskId && task.eligibleForPublish),
  );
  const publishResult = await publishFamily(workspace, sourceTask.sourceTaskId, eligiblePlans, options.outputRoot);
  const publishResultsByTaskId = new Map(
    publishResult.taskResults.map((taskResult) => [taskResult.derivedTaskId, taskResult] as const),
  );

  const publishedTaskIds: string[] = [];
  const skippedTaskIds: string[] = [];
  const failedTaskIds: string[] = [];
  const publishFailureIssues: string[] = [];

  for (const taskState of taskStates) {
    if (!taskState.eligibleForPublish) {
      failedTaskIds.push(taskState.derivedTaskId);
      await appendManifest({
        runId: workspace.runId,
        sourceTaskId: sourceTask.sourceTaskId,
        derivedTaskId: taskState.derivedTaskId,
        phase: "publish",
        status: "failed",
        draftDir: taskState.draftDir,
        issues: sortIssues(taskState.validateIssues),
        metadata: taskState.runtimeFailureKind ? { runtimeFailureKind: taskState.runtimeFailureKind } : undefined,
      });
      continue;
    }

    const publishTaskResult = publishResultsByTaskId.get(taskState.derivedTaskId);
    if (!publishTaskResult) {
      failedTaskIds.push(taskState.derivedTaskId);
      publishFailureIssues.push(`publish:${taskState.derivedTaskId} publish 未返回该任务结果`);
      await appendManifest({
        runId: workspace.runId,
        sourceTaskId: sourceTask.sourceTaskId,
        derivedTaskId: taskState.derivedTaskId,
        phase: "publish",
        status: "failed",
        draftDir: taskState.draftDir,
        issues: ["publish 未返回该任务结果"],
        metadata: taskState.runtimeFailureKind ? { runtimeFailureKind: taskState.runtimeFailureKind } : undefined,
      });
      continue;
    }

    if (publishTaskResult.status === "completed") {
      publishedTaskIds.push(taskState.derivedTaskId);
      await appendManifest({
        runId: workspace.runId,
        sourceTaskId: sourceTask.sourceTaskId,
        derivedTaskId: taskState.derivedTaskId,
        phase: "publish",
        status: "completed",
        draftDir: taskState.draftDir,
        publishedDir: publishTaskResult.taskDir,
      });
      continue;
    }

    skippedTaskIds.push(taskState.derivedTaskId);
    await appendManifest({
      runId: workspace.runId,
      sourceTaskId: sourceTask.sourceTaskId,
      derivedTaskId: taskState.derivedTaskId,
      phase: "publish",
      status: "skipped",
      draftDir: taskState.draftDir,
      publishedDir: publishTaskResult.taskDir,
      issues: [publishTaskResult.reason ?? "目标任务目录已存在，按配置跳过发布"],
    });
  }

  const finalStatus: FamilyExecutionResult["status"] =
    publishedTaskIds.length > 0 ? "completed" : failedTaskIds.length > 0 ? "failed" : "skipped";
  const failedTaskIdSet = new Set(failedTaskIds);
  const failureIssues = taskStates
    .filter((task) => failedTaskIdSet.has(task.derivedTaskId))
    .flatMap((task) => sortIssues(task.validateIssues));
  const finalIssues = [...failureIssues, ...publishFailureIssues];

  await appendManifest({
    runId: workspace.runId,
    sourceTaskId: sourceTask.sourceTaskId,
    phase: "publish",
    status: finalStatus,
    publishedDir:
      publishedTaskIds.length > 0 || skippedTaskIds.length > 0 ? publishResult.familyDir : undefined,
    issues: finalIssues,
    metadata: {
      publishedTaskIds,
      skippedTaskIds,
      failedTaskIds,
      familyObservationIssues: mergedFamilyObservationIssues,
      runtimeFailureKindsByTaskId,
    },
  });
  await writeRunSummary(workspace.runId, {
    sourceTaskId: sourceTask.sourceTaskId,
    status: finalStatus,
    issues: finalIssues,
    familyObservationIssues: mergedFamilyObservationIssues,
    publishedDir:
      publishedTaskIds.length > 0 || skippedTaskIds.length > 0 ? publishResult.familyDir : undefined,
    publishedTaskIds,
    skippedTaskIds,
    failedTaskIds,
    runtimeFailureKindsByTaskId,
    workspace,
  });

  return {
    sourceTaskId: sourceTask.sourceTaskId,
    runId: workspace.runId,
    status: finalStatus,
    issues: finalIssues,
    familyObservationIssues: mergedFamilyObservationIssues,
    publishedTaskIds,
    skippedTaskIds,
    failedTaskIds,
    publishedDir:
      publishedTaskIds.length > 0 || skippedTaskIds.length > 0 ? publishResult.familyDir : undefined,
  };
}

async function buildBatchPreflightFailureResults(
  sourceTasks: SourceTask[],
  preflight: DockerPreflightResult,
): Promise<FamilyExecutionResult[]> {
  const results: FamilyExecutionResult[] = [];

  for (const sourceTask of sourceTasks) {
    const runId = makeRunId(`${sourceTask.sourceTaskId}-runtime-preflight`);
    const issues = [`runtime docker/WSL preflight 失败: ${preflight.summary}`];
    await appendManifest({
      runId,
      sourceTaskId: sourceTask.sourceTaskId,
      phase: "runtime-preflight",
      status: "failed",
      issues,
      metadata: {
        dockerPreflight: {
          passed: false,
          stderrSummary: preflight.summary,
          details: preflight.details,
        },
      },
    });
    await writeRunSummary(runId, {
      sourceTaskId: sourceTask.sourceTaskId,
      status: "failed",
      issues,
      familyObservationIssues: [],
      publishedTaskIds: [],
      skippedTaskIds: [],
      failedTaskIds: [],
      dockerPreflight: {
        passed: false,
        stderrSummary: preflight.summary,
        details: preflight.details,
      },
    });
    results.push({
      sourceTaskId: sourceTask.sourceTaskId,
      runId,
      status: "failed",
      issues,
      familyObservationIssues: [],
      publishedTaskIds: [],
      skippedTaskIds: [],
      failedTaskIds: [],
    });
  }

  return results;
}

async function reviewLatestRun(sourceTaskId: string, sourceRoot: string): Promise<void> {
  const workspace = await findLatestWorkspaceForSource(sourceTaskId);
  if (!workspace) {
    throw new Error(`未找到 ${sourceTaskId} 的 scratch workspace`);
  }

  const familyPlanPath = path.join(workspace.artifactsDir, "family-plan.json");
  if (!(await pathExists(familyPlanPath))) {
    throw new Error(`workspace 已找到，但 family-plan.json 还不存在，生成可能仍在进行中: ${workspace.rootDir}`);
  }

  const sourceTask = await discoverSourceTaskById(sourceTaskId, sourceRoot);
  const familyPlanRaw = await readText(familyPlanPath);
  const familyPlan = JSON.parse(familyPlanRaw) as FamilyPlan;
  const codex = new CodexTaskBuilderClient();
  const review = await codex.reviewFamily(sourceTask, workspace, familyPlan);
  await writeJson(path.join(workspace.artifactsDir, "review-result.json"), review.data);
  console.log(JSON.stringify(review.data, null, 2));
}

async function batchGenerate(sourceRoot: string, options: Options): Promise<void> {
  const allTasks = await discoverSourceTasks(sourceRoot);
  const match = getStringOption(options, "match");
  const limit = getNumberOption(options, "limit", allTasks.length);
  const familyConcurrency = getNumberOption(options, "family-concurrency", 2);
  const outputRoot = getStringOption(options, "output-root", INTEGRATED_TASKS_ROOT) ?? INTEGRATED_TASKS_ROOT;

  const filtered = allTasks
    .filter((task) => (match ? new RegExp(match).test(task.sourceTaskId) : true))
    .slice(0, limit);

  if (filtered.length > 0) {
    const preflight = await runDockerPreflight();
    if (!preflight.ok) {
      const results = await buildBatchPreflightFailureResults(filtered, preflight);
      console.log(JSON.stringify(results, null, 2));
      return;
    }
  }

  const results: FamilyExecutionResult[] = [];
  let nextIndex = 0;

  async function worker(): Promise<void> {
    while (nextIndex < filtered.length) {
      const current = filtered[nextIndex];
      nextIndex += 1;
      try {
        results.push(
          await executeFamilyGeneration(current, {
            outputRoot,
          }),
        );
      } catch (error) {
        results.push({
          sourceTaskId: current.sourceTaskId,
          status: "failed",
          issues: [error instanceof Error ? error.message : String(error)],
          familyObservationIssues: [],
          publishedTaskIds: [],
          skippedTaskIds: [],
          failedTaskIds: [],
        });
      }
    }
  }

  await Promise.all(Array.from({ length: Math.max(1, familyConcurrency) }, () => worker()));
  console.log(JSON.stringify(results, null, 2));
}

async function main(): Promise<void> {
  const { command, options } = parseArgs(process.argv.slice(2));
  const sourceRoot = getStringOption(options, "source-root", SOURCE_TASKS_ROOT) ?? SOURCE_TASKS_ROOT;
  const outputRoot = getStringOption(options, "output-root", INTEGRATED_TASKS_ROOT) ?? INTEGRATED_TASKS_ROOT;

  await ensureDir(sourceRoot);
  await ensureDir(outputRoot);

  switch (command) {
    case "inventory": {
      await inventory(sourceRoot);
      return;
    }
    case "generate-family": {
      const sourceTaskId = getStringOption(options, "source-task-id");
      if (!sourceTaskId) {
        throw new Error("generate-family 需要 --source-task-id");
      }
      const sourceTask = await discoverSourceTaskById(sourceTaskId, sourceRoot);
      const result = await executeFamilyGeneration(sourceTask, {
        outputRoot,
      });
      console.log(JSON.stringify(result, null, 2));
      if (result.issues.length > 0) {
        console.error(formatIssueList(result.issues));
      }
      return;
    }
    case "batch": {
      await batchGenerate(sourceRoot, options);
      return;
    }
    case "review": {
      const sourceTaskId = getStringOption(options, "source-task-id");
      if (!sourceTaskId) {
        throw new Error("review 需要 --source-task-id");
      }
      await reviewLatestRun(sourceTaskId, sourceRoot);
      return;
    }
    default:
      throw new Error("可用命令: inventory | generate-family | batch | review");
  }
}

void main().catch((error) => {
  const message = error instanceof Error ? error.stack ?? error.message : String(error);
  console.error(message);
  process.exitCode = 1;
});
