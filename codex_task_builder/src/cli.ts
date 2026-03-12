import path from "node:path";
import { promises as fs } from "node:fs";
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
  runRuntimeValidation,
  validateDraftStatic,
  validateFamilyStructure,
  validateReviewerResult,
  type ValidationIssue,
} from "./validate.js";

type Options = Record<string, string | boolean>;

type FamilyExecutionResult = {
  sourceTaskId: string;
  runId?: string;
  status: "completed" | "failed" | "skipped";
  issues: string[];
  publishedDir?: string;
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
    skipExistingFamily: boolean;
  },
): Promise<FamilyExecutionResult> {
  const targetFamilyDir = path.join(options.outputRoot, sourceTask.sourceTaskId);
  if (options.skipExistingFamily && (await pathExists(targetFamilyDir))) {
    await appendManifest({
      runId: "skipped-existing",
      sourceTaskId: sourceTask.sourceTaskId,
      phase: "publish",
      status: "skipped",
      issues: ["目标 family 目录已存在，按配置跳过"],
    });
    return {
      sourceTaskId: sourceTask.sourceTaskId,
      status: "skipped",
      issues: ["目标 family 目录已存在，按配置跳过"],
    };
  }

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
  const writerSummaries: WriterSummary[] = [];
  const validationIssues: ValidationIssue[] = validateFamilyStructure(familyPlan);
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

  for (const plan of familyPlan.derivedTasks) {
    const draftDir = await prepareDraftSkeleton(workspace, sourceTask, plan);
    const writerResult = await codex.writeTask(sourceTask, workspace, plan);
    writerSummaries.push(writerResult.data);
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
  validationIssues.push(...(await validateReviewerResult(reviewResult.data)));
  await writeJson(path.join(workspace.artifactsDir, "review-result.json"), reviewResult.data);
  await writeJson(path.join(workspace.artifactsDir, "review-result.raw.json"), {
    threadId: reviewResult.threadId,
    raw: reviewResult.raw,
  });
  await appendManifest({
    runId: workspace.runId,
    sourceTaskId: sourceTask.sourceTaskId,
    phase: "reviewer",
    status: reviewResult.data.pass ? "completed" : "failed",
    threadId: reviewResult.threadId,
    issues: reviewResult.data.issues,
  });

  for (const plan of familyPlan.derivedTasks) {
    const writerSummary = writerSummaries.find((summary) => summary.derivedTaskId === plan.derivedTaskId);
    if (!writerSummary) {
      validationIssues.push({
        scope: "static",
        taskId: plan.derivedTaskId,
        message: "缺少 writer summary",
      });
      continue;
    }
    const draftDir = path.join(workspace.draftsDir, plan.derivedTaskId);
    validationIssues.push(...(await validateDraftStatic(draftDir, plan, writerSummary)));
  }

  if (validationIssues.length === 0) {
    for (const plan of familyPlan.derivedTasks) {
      validationIssues.push(...(await runRuntimeValidation(workspace, plan)));
    }
  }

  if (validationIssues.length > 0) {
    const issues = sortIssues(validationIssues);
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
      workspace,
    });
    return {
      sourceTaskId: sourceTask.sourceTaskId,
      runId: workspace.runId,
      status: "failed",
      issues,
    };
  }

  const publishResult = await publishFamily(workspace, familyPlan, options.outputRoot);
  if (!publishResult.published) {
    await appendManifest({
      runId: workspace.runId,
      sourceTaskId: sourceTask.sourceTaskId,
      phase: "publish",
      status: "skipped",
      issues: [publishResult.reason ?? "发布被跳过"],
    });
    return {
      sourceTaskId: sourceTask.sourceTaskId,
      runId: workspace.runId,
      status: "skipped",
      issues: [publishResult.reason ?? "发布被跳过"],
    };
  }

  await appendManifest({
    runId: workspace.runId,
    sourceTaskId: sourceTask.sourceTaskId,
    phase: "publish",
    status: "completed",
    publishedDir: publishResult.familyDir,
  });
  await writeRunSummary(workspace.runId, {
    sourceTaskId: sourceTask.sourceTaskId,
    status: "completed",
    publishedDir: publishResult.familyDir,
    workspace,
  });

  return {
    sourceTaskId: sourceTask.sourceTaskId,
    runId: workspace.runId,
    status: "completed",
    issues: [],
    publishedDir: publishResult.familyDir,
  };
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
            skipExistingFamily: true,
          }),
        );
      } catch (error) {
        results.push({
          sourceTaskId: current.sourceTaskId,
          status: "failed",
          issues: [error instanceof Error ? error.message : String(error)],
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
        skipExistingFamily: true,
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
