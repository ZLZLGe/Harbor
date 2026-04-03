import path from "node:path";
import { promises as fs } from "node:fs";
import { CodexTaskBuilderClient } from "./codex.js";
import {
  buildGenerationUnits,
  collectEnvironmentAssetPaths,
  discoverSourceTaskById,
  discoverSourceTasks,
  type GenerationUnit,
  type SkillMode,
  type SourceTask,
} from "./discovery.js";
import { appendManifest, writeRunSummary } from "./manifest.js";
import { buildMaterializedTaskDir, sanitizeAndCopyTask } from "./materialize.js";
import { applyPublishedFamilyState, inspectPublishedFamily, selectExecutableUnits } from "./published.js";
import type { DerivedTaskPlan, FamilyPlan, WriterSummary } from "./schema.js";
import { flattenFamilyPlan } from "./schema.js";
import {
  FINAL_TASKS_ROOT,
  QUARANTINE_ROOT,
  RAW_ROOT,
  SOURCE_TASKS_ROOT,
  ensureDir,
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
  resolveRuntimeEnvironment,
  runRuntimePreflight,
  runRuntimeValidation,
  validateDraftStatic,
  validateFamilyPlan,
  validateReviewerResult,
  validateTaskPlans,
  type RuntimeEnvironment,
  type RuntimeEvidence,
  type ValidationIssue,
} from "./validate.js";

type Options = Record<string, string | boolean>;

type FamilyExecutionResult = {
  sourceTaskId: string;
  skillMode: SkillMode;
  scopeSlug: string;
  targetSkillDirName?: string;
  targetSkillName?: string;
  runtimeEnvironment?: RuntimeEnvironment;
  runId?: string;
  status: "completed" | "failed";
  issues: string[];
  familyObservationIssues: string[];
  publishedTaskIds: string[];
  quarantinedTaskIds: string[];
  workspace?: FamilyWorkspace;
};

type TaskCycleState = {
  plan: DerivedTaskPlan;
  draftDir: string;
  writerSummary: WriterSummary;
  reviewerIssues: ValidationIssue[];
  staticIssues: ValidationIssue[];
  runtimeIssues: ValidationIssue[];
  runtimeEvidence?: RuntimeEvidence;
  passed: boolean;
};

type ExecuteFamilyOptions = {
  rawRoot: string;
  finalRoot: string;
  quarantineRoot: string;
  runtimeEnvironment: RuntimeEnvironment;
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

function getSkillModeOption(options: Options): SkillMode {
  const value = getStringOption(options, "skill-mode", "all");
  if (value === "all" || value === "per-skill") {
    return value;
  }
  throw new Error(`不支持的 --skill-mode: ${value}`);
}

function issueMessages(issues: ValidationIssue[]): string[] {
  return issues.map((issue) => `${issue.scope}${issue.taskId ? `:${issue.taskId}` : ""} ${issue.message}`);
}

function uniqueStrings(values: string[]): string[] {
  return Array.from(new Set(values));
}

function buildOrdinalRange(count: number): number[] {
  return Array.from({ length: Math.max(0, count) }, (_, index) => index + 1);
}

function resolvePendingOrdinals(unit: {
  similarCount: number;
  transferCount: number;
  pendingSimilarOrdinals?: number[];
  pendingTransferOrdinals?: number[];
}): { similarOrdinals: number[]; transferOrdinals: number[] } {
  const similarOrdinals =
    Array.isArray(unit.pendingSimilarOrdinals) ? unit.pendingSimilarOrdinals : buildOrdinalRange(unit.similarCount);
  const transferOrdinals =
    Array.isArray(unit.pendingTransferOrdinals) ? unit.pendingTransferOrdinals : buildOrdinalRange(unit.transferCount);
  return {
    similarOrdinals,
    transferOrdinals,
  };
}

function normalizeFamilyPlan(unit: GenerationUnit, familyPlan: FamilyPlan): FamilyPlan {
  return {
    ...familyPlan,
    sourceTaskId: unit.sourceTask.sourceTaskId,
    skillMode: unit.skillMode,
    targetSkillDirName: unit.targetSkill?.dirName ?? "",
    targetSkillName: unit.targetSkill?.name ?? "",
  };
}

function buildScopeMetadata(
  unit: GenerationUnit,
  runtimeEnvironment?: RuntimeEnvironment,
): Record<string, unknown> {
  return {
    skillMode: unit.skillMode,
    scopeSlug: unit.scopeSlug,
    targetSkillDirName: unit.targetSkill?.dirName,
    targetSkillName: unit.targetSkill?.name,
    similarCount: unit.similarCount,
    transferCount: unit.transferCount,
    pendingSimilarOrdinals: unit.pendingSimilarOrdinals,
    pendingTransferOrdinals: unit.pendingTransferOrdinals,
    finalFamilyDir: unit.finalFamilyDir,
    publishedTaskIds: unit.publishedTasks.map((task) => task.derivedTaskId),
    ...(runtimeEnvironment ? { runtimeEnvironment } : {}),
  };
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

async function rerunReview(
  sourceTaskId: string,
  options: {
    rawRoot: string;
    scopeSlug?: string;
  },
): Promise<void> {
  const workspace = await findLatestWorkspaceForSource(sourceTaskId, {
    rawRoot: options.rawRoot,
    scopeSlug: options.scopeSlug,
  });
  if (!workspace) {
    throw new Error(`未找到 source task ${sourceTaskId} 的 workspace`);
  }

  const unitPath = path.join(workspace.artifactsDir, "generation-unit.json");
  const familyPlanPath = path.join(workspace.artifactsDir, "family-plan.json");
  if (!(await pathExists(unitPath))) {
    throw new Error(`generation-unit.json 不存在: ${unitPath}`);
  }
  if (!(await pathExists(familyPlanPath))) {
    throw new Error(`family-plan.json 不存在: ${familyPlanPath}`);
  }

  const unit = JSON.parse(await readText(unitPath)) as GenerationUnit;
  const familyPlan = JSON.parse(await readText(familyPlanPath)) as FamilyPlan;
  const taskPlans = flattenFamilyPlan(familyPlan, resolvePendingOrdinals(unit));
  const codex = new CodexTaskBuilderClient();
  const reviewResult = await codex.reviewFamily(unit, workspace, familyPlan, taskPlans);
  console.log(JSON.stringify(reviewResult.data, null, 2));
}

async function executeFamilyGeneration(
  unit: GenerationUnit,
  options: ExecuteFamilyOptions,
): Promise<FamilyExecutionResult> {
  const pendingOrdinals = resolvePendingOrdinals(unit);
  const workspace = await createFamilyWorkspace(unit, {
    rawRoot: options.rawRoot,
  });
  const codex = new CodexTaskBuilderClient();

  await appendManifest({
    runId: workspace.runId,
    sourceTaskId: unit.sourceTask.sourceTaskId,
    phase: "workspace",
    status: "completed",
    metadata: { rootDir: workspace.rootDir, ...buildScopeMetadata(unit, options.runtimeEnvironment) },
  });

  try {
    const familyPlanResult = await codex.planFamily(unit, workspace);
    const plannerIssues = validateFamilyPlan(familyPlanResult.data, {
      sourceTaskId: unit.sourceTask.sourceTaskId,
      skillMode: unit.skillMode,
      similarCount: pendingOrdinals.similarOrdinals.length,
      transferCount: pendingOrdinals.transferOrdinals.length,
      targetSkillDirName: unit.targetSkill?.dirName,
      targetSkillName: unit.targetSkill?.name,
    });
    const normalizedFamilyPlan = normalizeFamilyPlan(unit, familyPlanResult.data);
    const taskPlans = flattenFamilyPlan(normalizedFamilyPlan, pendingOrdinals);
    const taskPlanIssues = validateTaskPlans(taskPlans, {
      similarOrdinals: pendingOrdinals.similarOrdinals,
      transferOrdinals: pendingOrdinals.transferOrdinals,
    });
    const initialFamilyObservationIssues = collectFamilyObservationIssues(taskPlans, {
      similarCount: pendingOrdinals.similarOrdinals.length,
      transferCount: pendingOrdinals.transferOrdinals.length,
    });
    const blockingIssues = [...plannerIssues, ...taskPlanIssues, ...initialFamilyObservationIssues];

    await writeJson(path.join(workspace.artifactsDir, "family-plan.json"), normalizedFamilyPlan);
    await writeJson(path.join(workspace.artifactsDir, "family-plan.raw.json"), {
      threadId: familyPlanResult.threadId,
      raw: familyPlanResult.raw,
    });

    await appendManifest({
      runId: workspace.runId,
      sourceTaskId: unit.sourceTask.sourceTaskId,
      phase: "planner",
      status: blockingIssues.length === 0 ? "completed" : "failed",
      threadId: familyPlanResult.threadId,
      issues: issueMessages(blockingIssues),
      metadata: buildScopeMetadata(unit, options.runtimeEnvironment),
    });

    if (blockingIssues.length > 0) {
      const issues = issueMessages(blockingIssues);
      await writeRunSummary(workspace.runId, {
        sourceTaskId: unit.sourceTask.sourceTaskId,
        status: "failed",
        issues,
        workspace,
      });
      return {
        sourceTaskId: unit.sourceTask.sourceTaskId,
        skillMode: unit.skillMode,
        scopeSlug: unit.scopeSlug,
        targetSkillDirName: unit.targetSkill?.dirName,
        targetSkillName: unit.targetSkill?.name,
        runtimeEnvironment: options.runtimeEnvironment,
        runId: workspace.runId,
        status: "failed",
        issues,
        familyObservationIssues: issues,
        publishedTaskIds: [],
        quarantinedTaskIds: [],
        workspace,
      };
    }

    const taskStates = new Map<string, TaskCycleState>();
    for (const plan of taskPlans) {
      const draftDir = await prepareDraftSkeleton(workspace, plan);
      const writerResult = await codex.writeTask(unit, workspace, plan);
      await writeJson(path.join(workspace.artifactsDir, `${plan.derivedTaskId}.writer.json`), writerResult.data);
      await writeJson(path.join(workspace.artifactsDir, `${plan.derivedTaskId}.writer.raw.json`), {
        threadId: writerResult.threadId,
        raw: writerResult.raw,
      });
      await appendManifest({
        runId: workspace.runId,
        sourceTaskId: unit.sourceTask.sourceTaskId,
        derivedTaskId: plan.derivedTaskId,
        phase: "writer",
        status: "completed",
        threadId: writerResult.threadId,
        draftDir,
        metadata: buildScopeMetadata(unit, options.runtimeEnvironment),
      });

      taskStates.set(plan.derivedTaskId, {
        plan,
        draftDir,
        writerSummary: writerResult.data,
        reviewerIssues: [],
        staticIssues: [],
        runtimeIssues: [],
        passed: false,
      });
    }

    const familyObservationIssues = new Set(initialFamilyObservationIssues.map((issue) => issue.message));
    const cycle = 0;
    const reviewResult = await codex.reviewFamily(unit, workspace, normalizedFamilyPlan, taskPlans);
    const reviewValidation = validateReviewerResult(taskPlans, reviewResult.data, {
      similarCount: pendingOrdinals.similarOrdinals.length,
      transferCount: pendingOrdinals.transferOrdinals.length,
    });
    await writeJson(path.join(workspace.artifactsDir, `review-result.round-${cycle}.json`), reviewResult.data);
    await writeJson(path.join(workspace.artifactsDir, `review-result.round-${cycle}.raw.json`), {
      threadId: reviewResult.threadId,
      raw: reviewResult.raw,
    });

    for (const issue of reviewValidation.familyObservationIssues) {
      familyObservationIssues.add(issue.message);
    }

    for (const plan of taskPlans) {
      const taskState = taskStates.get(plan.derivedTaskId);
      if (!taskState) {
        throw new Error(`缺少 task state: ${plan.derivedTaskId}`);
      }

      taskState.reviewerIssues = reviewValidation.taskIssuesById.get(plan.derivedTaskId) ?? [];
      taskState.staticIssues = await validateDraftStatic(taskState.draftDir, plan, unit);
      taskState.runtimeIssues = [];
      taskState.passed = false;

      const preRuntimeIssues = [...taskState.reviewerIssues, ...taskState.staticIssues];
      await appendManifest({
        runId: workspace.runId,
        sourceTaskId: unit.sourceTask.sourceTaskId,
        derivedTaskId: plan.derivedTaskId,
        phase: "validate",
        status: preRuntimeIssues.length === 0 ? "completed" : "failed",
        draftDir: taskState.draftDir,
        issues: issueMessages(preRuntimeIssues),
        metadata: {
          ...buildScopeMetadata(unit, options.runtimeEnvironment),
          cycle,
        },
      });

      if (preRuntimeIssues.length > 0) {
        taskState.runtimeEvidence = undefined;
        continue;
      }

      taskState.runtimeEvidence = undefined;
      const attemptIndex = 1;
      const runtimeResult = await runRuntimeValidation(
        workspace,
        plan,
        options.runtimeEnvironment,
        cycle,
        attemptIndex,
      );
      taskState.runtimeIssues = runtimeResult.issues;
      taskState.runtimeEvidence = runtimeResult.evidence;
      await writeJson(
        path.join(workspace.artifactsDir, `${plan.derivedTaskId}.runtime.cycle-${cycle}.attempt-${attemptIndex}.json`),
        {
          passed: runtimeResult.passed,
          failureKind: runtimeResult.failureKind,
          issues: issueMessages(runtimeResult.issues),
          evidence: runtimeResult.evidence,
        },
      );
      await writeJson(path.join(workspace.artifactsDir, `${plan.derivedTaskId}.runtime.cycle-${cycle}.json`), {
        passed: runtimeResult.passed,
        failureKind: runtimeResult.failureKind,
        issues: issueMessages(runtimeResult.issues),
        evidence: runtimeResult.evidence,
      });

      if (runtimeResult.passed) {
        taskState.passed = true;
        continue;
      }

      await appendManifest({
        runId: workspace.runId,
        sourceTaskId: unit.sourceTask.sourceTaskId,
        derivedTaskId: plan.derivedTaskId,
        phase: "validate",
        status: "failed",
        draftDir: taskState.draftDir,
        issues: issueMessages(runtimeResult.issues),
        metadata: {
          ...buildScopeMetadata(unit, options.runtimeEnvironment),
          cycle,
          runtimeAttempt: attemptIndex,
          runtimeFailureKind: runtimeResult.failureKind,
        },
      });
    }

    const publishedTaskIds: string[] = [];
    const quarantinedTaskIds: string[] = [];
    const finalIssues: string[] = [];

    for (const plan of taskPlans) {
      const taskState = taskStates.get(plan.derivedTaskId);
      if (!taskState) {
        continue;
      }

      if (taskState.passed) {
        const materializeResult = await sanitizeAndCopyTask({
          sourceDraftDir: taskState.draftDir,
          sourceTaskId: unit.sourceTask.sourceTaskId,
          scopeSlug: unit.scopeSlug,
          taskName: plan.derivedTaskId,
          rawRoot: options.rawRoot,
          targetRoot: options.finalRoot,
        });
        publishedTaskIds.push(plan.derivedTaskId);
        await appendManifest({
          runId: workspace.runId,
          sourceTaskId: unit.sourceTask.sourceTaskId,
          derivedTaskId: plan.derivedTaskId,
          phase: "publish",
          status: "completed",
          draftDir: taskState.draftDir,
          publishedDir: materializeResult.targetTaskDir,
          metadata: {
            ...buildScopeMetadata(unit, options.runtimeEnvironment),
            publishDisposition: materializeResult.disposition,
          },
        });
        continue;
      }

      const quarantineResult = await sanitizeAndCopyTask({
        sourceDraftDir: taskState.draftDir,
        sourceTaskId: unit.sourceTask.sourceTaskId,
        scopeSlug: unit.scopeSlug,
        taskName: plan.derivedTaskId,
        rawRoot: options.rawRoot,
        targetRoot: options.quarantineRoot,
      });
      quarantinedTaskIds.push(plan.derivedTaskId);
      finalIssues.push(
        ...issueMessages(taskState.reviewerIssues),
        ...issueMessages(taskState.staticIssues),
        ...issueMessages(taskState.runtimeIssues),
      );
      await appendManifest({
        runId: workspace.runId,
        sourceTaskId: unit.sourceTask.sourceTaskId,
        derivedTaskId: plan.derivedTaskId,
        phase: "publish",
        status: "failed",
        draftDir: taskState.draftDir,
        publishedDir: quarantineResult.targetTaskDir,
        issues: [
          ...issueMessages(taskState.reviewerIssues),
          ...issueMessages(taskState.staticIssues),
          ...issueMessages(taskState.runtimeIssues),
        ],
        metadata: {
          ...buildScopeMetadata(unit, options.runtimeEnvironment),
          publishDisposition: quarantineResult.disposition,
        },
      });
    }

    const status: FamilyExecutionResult["status"] = quarantinedTaskIds.length === 0 ? "completed" : "failed";
    const summary = {
      sourceTaskId: unit.sourceTask.sourceTaskId,
      skillMode: unit.skillMode,
      scopeSlug: unit.scopeSlug,
      targetSkillDirName: unit.targetSkill?.dirName,
      targetSkillName: unit.targetSkill?.name,
      runtimeEnvironment: options.runtimeEnvironment,
      status,
      issues: uniqueStrings(finalIssues),
      familyObservationIssues: Array.from(familyObservationIssues.values()).sort((a, b) => a.localeCompare(b)),
      publishedTaskIds,
      quarantinedTaskIds,
      workspace,
      finalDirs: publishedTaskIds.map((taskId) =>
        buildMaterializedTaskDir({
          targetRoot: options.finalRoot,
          sourceTaskId: unit.sourceTask.sourceTaskId,
          scopeSlug: unit.scopeSlug,
          taskName: taskId,
        }),
      ),
      quarantineDirs: quarantinedTaskIds.map((taskId) =>
        buildMaterializedTaskDir({
          targetRoot: options.quarantineRoot,
          sourceTaskId: unit.sourceTask.sourceTaskId,
          scopeSlug: unit.scopeSlug,
          taskName: taskId,
        }),
      ),
    };
    await writeRunSummary(workspace.runId, summary);

    return {
      sourceTaskId: unit.sourceTask.sourceTaskId,
      skillMode: unit.skillMode,
      scopeSlug: unit.scopeSlug,
      targetSkillDirName: unit.targetSkill?.dirName,
      targetSkillName: unit.targetSkill?.name,
      runtimeEnvironment: options.runtimeEnvironment,
      runId: workspace.runId,
      status,
      issues: summary.issues,
      familyObservationIssues: summary.familyObservationIssues,
      publishedTaskIds,
      quarantinedTaskIds,
      workspace,
    };
  } catch (error) {
    const message = error instanceof Error ? error.stack ?? error.message : String(error);
    await appendManifest({
      runId: workspace.runId,
      sourceTaskId: unit.sourceTask.sourceTaskId,
      phase: "family",
      status: "failed",
      issues: [message],
      metadata: buildScopeMetadata(unit, options.runtimeEnvironment),
    });
    await writeRunSummary(workspace.runId, {
      sourceTaskId: unit.sourceTask.sourceTaskId,
      status: "failed",
      issues: [message],
      workspace,
    });
    return {
      sourceTaskId: unit.sourceTask.sourceTaskId,
      skillMode: unit.skillMode,
      scopeSlug: unit.scopeSlug,
      targetSkillDirName: unit.targetSkill?.dirName,
      targetSkillName: unit.targetSkill?.name,
      runtimeEnvironment: options.runtimeEnvironment,
      runId: workspace.runId,
      status: "failed",
      issues: [message],
      familyObservationIssues: [],
      publishedTaskIds: [],
      quarantinedTaskIds: [],
      workspace,
    };
  }
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

async function loadUnitsForCommand(
  options: Options,
  finalRoot: string,
): Promise<{
  units: GenerationUnit[];
  discoveredUnitCount: number;
  skippedCount: number;
}> {
  const sourceRoot = getStringOption(options, "source-root", SOURCE_TASKS_ROOT)!;
  const skillMode = getSkillModeOption(options);
  const similarCount = getNumberOption(options, "similar-count", 1);
  const transferCount = getNumberOption(options, "transfer-count", 3);

  if (similarCount < 0 || transferCount < 0) {
    throw new Error("similar-count 和 transfer-count 不能小于 0");
  }
  if (similarCount + transferCount === 0) {
    throw new Error("similar-count 和 transfer-count 不能同时为 0");
  }

  const sourceTaskId = getStringOption(options, "source-task-id");
  const scopeSkillDir = getStringOption(options, "target-skill-dir");
  const hydrateUnits = async (units: GenerationUnit[]): Promise<GenerationUnit[]> =>
    Promise.all(
      units.map(async (unit) => {
        const publishedState = await inspectPublishedFamily(unit, finalRoot);
        return applyPublishedFamilyState(unit, publishedState);
      }),
    );

  if (sourceTaskId) {
    const sourceTask = await discoverSourceTaskById(sourceTaskId, sourceRoot);
    let units = buildGenerationUnits(sourceTask, {
      skillMode,
      similarCount,
      transferCount,
    });
    if (scopeSkillDir) {
      units = units.filter((unit) => unit.targetSkill?.dirName === scopeSkillDir);
    }
    const hydratedUnits = await hydrateUnits(units);
    const limit = getNumberOption(options, "limit", 0);
    const selected = selectExecutableUnits(hydratedUnits, limit);
    return {
      units: selected.executableUnits,
      discoveredUnitCount: hydratedUnits.length,
      skippedCount: selected.skippedCount,
    };
  }

  const sourceTasks = await discoverSourceTasks(sourceRoot);
  let units = sourceTasks.flatMap((sourceTask) =>
    buildGenerationUnits(sourceTask, {
      skillMode,
      similarCount,
      transferCount,
    }),
  );
  if (scopeSkillDir) {
    units = units.filter((unit) => unit.targetSkill?.dirName === scopeSkillDir);
  }
  const hydratedUnits = await hydrateUnits(units);
  const limit = getNumberOption(options, "limit", 0);
  const selected = selectExecutableUnits(hydratedUnits, limit);
  return {
    units: selected.executableUnits,
    discoveredUnitCount: hydratedUnits.length,
    skippedCount: selected.skippedCount,
  };
}

async function ensureRoots(options: ExecuteFamilyOptions): Promise<void> {
  await ensureDir(options.rawRoot);
  await ensureDir(options.finalRoot);
  await ensureDir(options.quarantineRoot);
}

async function main(): Promise<void> {
  const { command, options } = parseArgs(process.argv.slice(2));
  const sourceRoot = getStringOption(options, "source-root", SOURCE_TASKS_ROOT)!;

  if (command === "inventory") {
    await inventory(sourceRoot);
    return;
  }

  if (command === "review") {
    const sourceTaskId = getStringOption(options, "source-task-id");
    if (!sourceTaskId) {
      throw new Error("review 命令需要 --source-task-id");
    }
    await rerunReview(sourceTaskId, {
      rawRoot: getStringOption(options, "raw-root", RAW_ROOT)!,
      scopeSlug: getStringOption(options, "scope-slug"),
    });
    return;
  }

  if (command !== "generate-family" && command !== "batch") {
    throw new Error(`不支持的命令: ${command ?? "(missing)"}`);
  }

  const runtimeEnvironment = resolveRuntimeEnvironment();
  const executeOptions: ExecuteFamilyOptions = {
    rawRoot: getStringOption(options, "raw-root", RAW_ROOT)!,
    finalRoot: getStringOption(
      options,
      "final-root",
      getStringOption(options, "output-root", FINAL_TASKS_ROOT),
    )!,
    quarantineRoot: getStringOption(options, "quarantine-root", QUARANTINE_ROOT)!,
    runtimeEnvironment,
  };
  await ensureRoots(executeOptions);

  const preflight = await runRuntimePreflight(runtimeEnvironment);
  if (!preflight.ok) {
    throw new Error(preflight.summary);
  }

  const loaded = await loadUnitsForCommand(options, executeOptions.finalRoot);
  const units = loaded.units;
  if (units.length === 0) {
    console.log(
      JSON.stringify(
        {
          status: "empty",
          units: 0,
          discoveredUnitCount: loaded.discoveredUnitCount,
          skippedCount: loaded.skippedCount,
        },
        null,
        2,
      ),
    );
    return;
  }

  const concurrency = getNumberOption(options, "concurrency", command === "generate-family" ? 1 : 2);
  const results = await runPool(units, concurrency, async (unit, index) => {
    console.log(
      `[${index + 1}/${units.length}] 开始 ${unit.sourceTask.sourceTaskId}/${unit.scopeSlug} pending-similar=${unit.pendingSimilarOrdinals.length}/${unit.similarCount} pending-transfer=${unit.pendingTransferOrdinals.length}/${unit.transferCount}`,
    );
    const result = await executeFamilyGeneration(unit, executeOptions);
    console.log(
      `[${index + 1}/${units.length}] 完成 ${unit.sourceTask.sourceTaskId}/${unit.scopeSlug} status=${result.status}`,
    );
    return result;
  });

  const summary = {
    runtimeEnvironment,
    unitCount: results.length,
    discoveredUnitCount: loaded.discoveredUnitCount,
    successCount: results.filter((result) => result.status === "completed").length,
    failedCount: results.filter((result) => result.status === "failed").length,
    skippedCount: loaded.skippedCount,
    publishedTaskCount: results.reduce((sum, result) => sum + result.publishedTaskIds.length, 0),
    quarantinedTaskCount: results.reduce((sum, result) => sum + result.quarantinedTaskIds.length, 0),
    rawRoot: executeOptions.rawRoot,
    finalRoot: executeOptions.finalRoot,
    quarantineRoot: executeOptions.quarantineRoot,
    results,
  };
  console.log(JSON.stringify(summary, null, 2));
}

void main().catch((error) => {
  const message = error instanceof Error ? error.stack ?? error.message : String(error);
  console.error(message);
  process.exitCode = 1;
});
