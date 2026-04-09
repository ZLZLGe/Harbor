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
import { appendManifest, resolveRunsRoot, writeRunSummary, type ManifestEntry } from "./manifest.js";
import { buildMaterializedTaskDir, sanitizeAndCopyTask } from "./materialize.js";
import { applyPublishedFamilyState, inspectPublishedFamily, selectExecutableUnits } from "./published.js";
import type { DerivedTaskPlan, FamilyPlan, WriterSummary } from "./schema.js";
import { flattenFamilyPlan } from "./schema.js";
import {
  buildSkillEffectBucketRoot,
  buildSkillEffectIssues,
  runSkillEffectEvaluation,
  runSkillEffectPreflight,
  type SkillEffectBucket,
  type SkillEffectEvaluationResult,
} from "./skill_effect.js";
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
  skillEffectResults: Array<{
    derivedTaskId: string;
    bucket: SkillEffectBucket;
    repairRequired: boolean;
    withSkillPassed: boolean;
    withSkillReward: number | null;
    withSkillSummary: string;
    noSkillPassed: boolean;
    noSkillReward: number | null;
    noSkillSummary: string;
  }>;
  skillEffectBucketCounts: Partial<Record<SkillEffectBucket, number>>;
  workspace?: FamilyWorkspace;
};

type TaskCycleState = {
  plan: DerivedTaskPlan;
  draftDir: string;
  writerSummary: WriterSummary;
  repairThreadId: string | null;
  repairRoundsUsed: number;
  runtimeAttemptCount: number;
  skillEffectAttemptCount: number;
  lastMutatedCycle: number | null;
  runtimePassedCycle: number | null;
  skillEffectAcceptedCycle: number | null;
  reviewerIssues: ValidationIssue[];
  staticIssues: ValidationIssue[];
  runtimeIssues: ValidationIssue[];
  skillEffectIssues: ValidationIssue[];
  runtimeEvidence?: RuntimeEvidence;
  skillEffectEvaluation?: SkillEffectEvaluationResult;
  skillEffectResultPath?: string;
  passed: boolean;
};

type ExecuteFamilyOptions = {
  runsRoot: string;
  rawRoot: string;
  finalRoot: string;
  quarantineRoot: string;
  runtimeEnvironment: RuntimeEnvironment;
  maxRepairRounds: number;
  skillEffectEnabled: boolean;
  skillEffectModel: string;
  skillEffectApiKey: string;
  skillEffectBaseUrl?: string;
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

function getFlagOption(options: Options, key: string): boolean {
  return options[key] === true;
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

function recordSkillEffectBucketCount(
  counts: Partial<Record<SkillEffectBucket, number>>,
  bucket: SkillEffectBucket,
): void {
  counts[bucket] = (counts[bucket] ?? 0) + 1;
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

async function repairTaskDraft(
  codex: CodexTaskBuilderClient,
  unit: GenerationUnit,
  workspace: FamilyWorkspace,
  taskState: TaskCycleState,
  cycle: number,
  runsRoot: string,
): Promise<void> {
  const repairResult = await codex.repairTask({
    unit,
    workspace,
    plan: taskState.plan,
    reviewerIssues: issueMessages(taskState.reviewerIssues),
    staticIssues: issueMessages(taskState.staticIssues),
    runtimeIssues: issueMessages(taskState.runtimeIssues),
    skillEffectIssues: issueMessages(taskState.skillEffectIssues),
    runtimeDir: taskState.runtimeEvidence?.runtimeDir,
    runtimeLogRoot: taskState.runtimeEvidence?.runtimeLogRoot,
    runtimeLogIndexPath: taskState.runtimeEvidence?.runtimeLogIndexPath,
    runtimeLogPath: taskState.runtimeEvidence?.logFilePath,
    runtimeResultPath: taskState.runtimeEvidence?.resultPath,
    jobLogPath: taskState.runtimeEvidence?.jobLogPath,
    trialLogPath: taskState.runtimeEvidence?.trialLogPath,
    verifierStdoutPath: taskState.runtimeEvidence?.verifierStdoutPath,
    rewardPath: taskState.runtimeEvidence?.rewardPath,
    artifactManifestPath: taskState.runtimeEvidence?.artifactManifestPath,
    skillEffectResultPath: taskState.skillEffectResultPath,
    skillEffectBucket: taskState.skillEffectEvaluation?.bucket,
    withSkillLogRoot: taskState.skillEffectEvaluation?.withSkill.evidence.logsDir,
    withSkillResultPath: taskState.skillEffectEvaluation?.withSkill.evidence.resultPath,
    withSkillRewardPath: taskState.skillEffectEvaluation?.withSkill.evidence.rewardPath,
    withSkillTrajectoryPath: taskState.skillEffectEvaluation?.withSkill.evidence.trajectoryPath,
    noSkillLogRoot: taskState.skillEffectEvaluation?.noSkill.evidence.logsDir,
    noSkillResultPath: taskState.skillEffectEvaluation?.noSkill.evidence.resultPath,
    noSkillRewardPath: taskState.skillEffectEvaluation?.noSkill.evidence.rewardPath,
    noSkillTrajectoryPath: taskState.skillEffectEvaluation?.noSkill.evidence.trajectoryPath,
    threadId: taskState.repairThreadId,
  });
  taskState.repairThreadId = repairResult.threadId;
  taskState.repairRoundsUsed += 1;
  taskState.lastMutatedCycle = cycle;
  taskState.runtimePassedCycle = null;
  taskState.skillEffectAcceptedCycle = null;
  taskState.passed = false;
  await writeJson(
    path.join(workspace.artifactsDir, `${taskState.plan.derivedTaskId}.repair.${taskState.repairRoundsUsed}.json`),
    repairResult.data,
  );
  await writeJson(
    path.join(workspace.artifactsDir, `${taskState.plan.derivedTaskId}.repair.${taskState.repairRoundsUsed}.raw.json`),
    {
      threadId: repairResult.threadId,
      raw: repairResult.raw,
    },
  );
  await appendManifest(
    {
      runId: workspace.runId,
      sourceTaskId: workspace.sourceTaskId,
      derivedTaskId: taskState.plan.derivedTaskId,
      phase: "repair",
      status: "completed",
      threadId: repairResult.threadId,
      draftDir: taskState.draftDir,
      issues: [
        ...issueMessages(taskState.reviewerIssues),
        ...issueMessages(taskState.staticIssues),
        ...issueMessages(taskState.runtimeIssues),
        ...issueMessages(taskState.skillEffectIssues),
      ],
    },
    runsRoot,
  );
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
  const appendRunManifest = (entry: Omit<ManifestEntry, "timestamp">) => appendManifest(entry, options.runsRoot);
  const writeWorkspaceSummary = (summary: unknown) => writeRunSummary(workspace.runId, summary, options.runsRoot);

  await appendRunManifest({
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

    await appendRunManifest({
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
      await writeWorkspaceSummary({
        sourceTaskId: unit.sourceTask.sourceTaskId,
        status: "failed",
        issues,
        runsRoot: options.runsRoot,
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
        skillEffectResults: [],
        skillEffectBucketCounts: {},
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
      await appendRunManifest({
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
        repairThreadId: null,
        repairRoundsUsed: 0,
        runtimeAttemptCount: 0,
        skillEffectAttemptCount: 0,
        lastMutatedCycle: null,
        runtimePassedCycle: null,
        skillEffectAcceptedCycle: null,
        reviewerIssues: [],
        staticIssues: [],
        runtimeIssues: [],
        skillEffectIssues: [],
        passed: false,
      });
    }

    const familyObservationIssues = new Set(initialFamilyObservationIssues.map((issue) => issue.message));
    for (let cycle = 0; cycle <= options.maxRepairRounds; cycle += 1) {
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

      let repairedThisCycle = false;
      let allPassedThisCycle = true;

      for (const plan of taskPlans) {
        const taskState = taskStates.get(plan.derivedTaskId);
        if (!taskState) {
          throw new Error(`缺少 task state: ${plan.derivedTaskId}`);
        }

        taskState.reviewerIssues = reviewValidation.taskIssuesById.get(plan.derivedTaskId) ?? [];
        taskState.staticIssues = await validateDraftStatic(taskState.draftDir, plan, unit);
        taskState.runtimeIssues = [];
        taskState.skillEffectIssues = [];
        taskState.passed = false;

        const preRuntimeIssues = [...taskState.reviewerIssues, ...taskState.staticIssues];
        await appendRunManifest({
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
          taskState.skillEffectEvaluation = undefined;
          taskState.skillEffectResultPath = undefined;
          taskState.skillEffectAcceptedCycle = null;
          allPassedThisCycle = false;
          if (taskState.repairRoundsUsed < options.maxRepairRounds) {
            await repairTaskDraft(codex, unit, workspace, taskState, cycle, options.runsRoot);
            repairedThisCycle = true;
          }
          continue;
        }

        const runtimeStillValid =
          taskState.runtimePassedCycle !== null &&
          (taskState.lastMutatedCycle === null || taskState.lastMutatedCycle <= taskState.runtimePassedCycle);
        const skillEffectStillValid =
          taskState.skillEffectAcceptedCycle !== null &&
          (taskState.lastMutatedCycle === null || taskState.lastMutatedCycle <= taskState.skillEffectAcceptedCycle);
        if (runtimeStillValid && (!options.skillEffectEnabled || skillEffectStillValid)) {
          taskState.passed = true;
          continue;
        }

        if (!runtimeStillValid) {
          taskState.runtimeEvidence = undefined;
          taskState.skillEffectEvaluation = undefined;
          taskState.skillEffectResultPath = undefined;
          taskState.skillEffectAcceptedCycle = null;
          const attemptIndex = taskState.runtimeAttemptCount + 1;
          const runtimeResult = await runRuntimeValidation(
            workspace,
            plan,
            options.runtimeEnvironment,
            cycle,
            attemptIndex,
          );
          taskState.runtimeAttemptCount = attemptIndex;
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

          if (!runtimeResult.passed) {
            allPassedThisCycle = false;
            await appendRunManifest({
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

            if (taskState.repairRoundsUsed < options.maxRepairRounds) {
              await repairTaskDraft(codex, unit, workspace, taskState, cycle, options.runsRoot);
              repairedThisCycle = true;
            }
            continue;
          }

          taskState.runtimePassedCycle = cycle;
        }

        if (!options.skillEffectEnabled) {
          taskState.passed = true;
          continue;
        }

        if (skillEffectStillValid) {
          taskState.passed = true;
          continue;
        }

        const skillEffectAttemptIndex = taskState.skillEffectAttemptCount + 1;
        const skillEffectResult = await runSkillEffectEvaluation({
          workspace,
          plan,
          runtimeEnvironment: options.runtimeEnvironment,
          cycle,
          attemptIndex: skillEffectAttemptIndex,
          draftTaskDir: taskState.draftDir,
          modelName: options.skillEffectModel,
          apiKey: options.skillEffectApiKey,
          baseUrl: options.skillEffectBaseUrl,
        });
        taskState.skillEffectAttemptCount = skillEffectAttemptIndex;
        taskState.skillEffectEvaluation = skillEffectResult;
        taskState.skillEffectIssues = buildSkillEffectIssues(plan.derivedTaskId, skillEffectResult);
        taskState.skillEffectAcceptedCycle = skillEffectResult.repairRequired ? null : cycle;
        taskState.skillEffectResultPath = path.join(
          workspace.artifactsDir,
          `${plan.derivedTaskId}.skill-effect.cycle-${cycle}.attempt-${skillEffectAttemptIndex}.json`,
        );
        await writeJson(taskState.skillEffectResultPath, skillEffectResult);
        await writeJson(path.join(workspace.artifactsDir, `${plan.derivedTaskId}.skill-effect.cycle-${cycle}.json`), skillEffectResult);
        await appendRunManifest({
          runId: workspace.runId,
          sourceTaskId: unit.sourceTask.sourceTaskId,
          derivedTaskId: plan.derivedTaskId,
          phase: "skill-effect",
          status: skillEffectResult.repairRequired ? "failed" : "completed",
          draftDir: taskState.draftDir,
          issues: issueMessages(taskState.skillEffectIssues),
          metadata: {
            ...buildScopeMetadata(unit, options.runtimeEnvironment),
            cycle,
            skillEffectAttempt: skillEffectAttemptIndex,
            skillEffectBucket: skillEffectResult.bucket,
          },
        });

        if (!skillEffectResult.repairRequired) {
          taskState.passed = true;
          continue;
        }

        allPassedThisCycle = false;
        if (taskState.repairRoundsUsed < options.maxRepairRounds) {
          await repairTaskDraft(codex, unit, workspace, taskState, cycle, options.runsRoot);
          repairedThisCycle = true;
        }
      }

      if (allPassedThisCycle) {
        break;
      }

      if (!repairedThisCycle) {
        break;
      }
    }

    const publishedTaskIds: string[] = [];
    const quarantinedTaskIds: string[] = [];
    const finalIssues: string[] = [];
    const skillEffectResults: FamilyExecutionResult["skillEffectResults"] = [];
    const skillEffectBucketCounts: Partial<Record<SkillEffectBucket, number>> = {};

    for (const plan of taskPlans) {
      const taskState = taskStates.get(plan.derivedTaskId);
      if (!taskState) {
        continue;
      }

      if (taskState.skillEffectEvaluation) {
        skillEffectResults.push({
          derivedTaskId: plan.derivedTaskId,
          bucket: taskState.skillEffectEvaluation.bucket,
          repairRequired: taskState.skillEffectEvaluation.repairRequired,
          withSkillPassed: taskState.skillEffectEvaluation.withSkill.passed,
          withSkillReward: taskState.skillEffectEvaluation.withSkill.evidence.reward ?? null,
          withSkillSummary: taskState.skillEffectEvaluation.withSkill.evidence.summary,
          noSkillPassed: taskState.skillEffectEvaluation.noSkill.passed,
          noSkillReward: taskState.skillEffectEvaluation.noSkill.evidence.reward ?? null,
          noSkillSummary: taskState.skillEffectEvaluation.noSkill.evidence.summary,
        });
        recordSkillEffectBucketCount(skillEffectBucketCounts, taskState.skillEffectEvaluation.bucket);
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
        await appendRunManifest({
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

        if (taskState.skillEffectEvaluation) {
          const bucketResult = await sanitizeAndCopyTask({
            sourceDraftDir: taskState.draftDir,
            sourceTaskId: unit.sourceTask.sourceTaskId,
            scopeSlug: unit.scopeSlug,
            taskName: plan.derivedTaskId,
            rawRoot: options.rawRoot,
            targetRoot: buildSkillEffectBucketRoot(options.finalRoot, taskState.skillEffectEvaluation.bucket),
          });
          await appendRunManifest({
            runId: workspace.runId,
            sourceTaskId: unit.sourceTask.sourceTaskId,
            derivedTaskId: plan.derivedTaskId,
            phase: "skill-effect-bucket",
            status: "completed",
            draftDir: taskState.draftDir,
            publishedDir: bucketResult.targetTaskDir,
            metadata: {
              ...buildScopeMetadata(unit, options.runtimeEnvironment),
              skillEffectBucket: taskState.skillEffectEvaluation.bucket,
              publishDisposition: bucketResult.disposition,
              bucketTarget: "final",
            },
          });
        }
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
        ...issueMessages(taskState.skillEffectIssues),
      );
      await appendRunManifest({
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
          ...issueMessages(taskState.skillEffectIssues),
        ],
        metadata: {
          ...buildScopeMetadata(unit, options.runtimeEnvironment),
          publishDisposition: quarantineResult.disposition,
        },
      });

      if (taskState.skillEffectEvaluation) {
        const bucketResult = await sanitizeAndCopyTask({
          sourceDraftDir: taskState.draftDir,
          sourceTaskId: unit.sourceTask.sourceTaskId,
          scopeSlug: unit.scopeSlug,
          taskName: plan.derivedTaskId,
          rawRoot: options.rawRoot,
          targetRoot: buildSkillEffectBucketRoot(options.quarantineRoot, taskState.skillEffectEvaluation.bucket),
        });
        await appendRunManifest({
          runId: workspace.runId,
          sourceTaskId: unit.sourceTask.sourceTaskId,
          derivedTaskId: plan.derivedTaskId,
          phase: "skill-effect-bucket",
          status: "failed",
          draftDir: taskState.draftDir,
          publishedDir: bucketResult.targetTaskDir,
          metadata: {
            ...buildScopeMetadata(unit, options.runtimeEnvironment),
            skillEffectBucket: taskState.skillEffectEvaluation.bucket,
            publishDisposition: bucketResult.disposition,
            bucketTarget: "quarantine",
          },
        });
      }
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
      skillEffectResults,
      skillEffectBucketCounts,
      runsRoot: options.runsRoot,
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
    await writeWorkspaceSummary(summary);

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
      skillEffectResults,
      skillEffectBucketCounts,
      workspace,
    };
  } catch (error) {
    const message = error instanceof Error ? error.stack ?? error.message : String(error);
    await appendRunManifest({
      runId: workspace.runId,
      sourceTaskId: unit.sourceTask.sourceTaskId,
      phase: "family",
      status: "failed",
      issues: [message],
      metadata: buildScopeMetadata(unit, options.runtimeEnvironment),
    });
    await writeWorkspaceSummary({
      sourceTaskId: unit.sourceTask.sourceTaskId,
      status: "failed",
      issues: [message],
      runsRoot: options.runsRoot,
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
      skillEffectResults: [],
      skillEffectBucketCounts: {},
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
  await ensureDir(options.runsRoot);
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
  const skillEffectEnabled = !getFlagOption(options, "skip-skill-effect-gate");
  const skillEffectModel = getStringOption(options, "skill-effect-model", "openai/gpt-5.4")!;
  const rawRoot = getStringOption(options, "raw-root", RAW_ROOT)!;
  const runsRoot = resolveRunsRoot({
    rawRoot,
    runsRoot: getStringOption(options, "runs-root"),
  });
  const executeOptions: ExecuteFamilyOptions = {
    runsRoot,
    rawRoot,
    finalRoot: getStringOption(
      options,
      "final-root",
      getStringOption(options, "output-root", FINAL_TASKS_ROOT),
    )!,
    quarantineRoot: getStringOption(options, "quarantine-root", QUARANTINE_ROOT)!,
    runtimeEnvironment,
    maxRepairRounds: getNumberOption(options, "max-repair-rounds", 2),
    skillEffectEnabled,
    skillEffectModel,
    skillEffectApiKey: process.env.OPENAI_API_KEY?.trim() ?? "",
    skillEffectBaseUrl: process.env.OPENAI_BASE_URL?.trim() || undefined,
  };
  await ensureRoots(executeOptions);

  const preflight = await runRuntimePreflight(runtimeEnvironment);
  if (!preflight.ok) {
    throw new Error(preflight.summary);
  }

  if (executeOptions.skillEffectEnabled) {
    const skillEffectPreflight = await runSkillEffectPreflight(runtimeEnvironment);
    if (!skillEffectPreflight.ok) {
      throw new Error(skillEffectPreflight.summary);
    }
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
          runsRoot: executeOptions.runsRoot,
          rawRoot: executeOptions.rawRoot,
          finalRoot: executeOptions.finalRoot,
          quarantineRoot: executeOptions.quarantineRoot,
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

  const skillEffectBucketCounts: Partial<Record<SkillEffectBucket, number>> = {};
  for (const result of results) {
    for (const [bucket, count] of Object.entries(result.skillEffectBucketCounts)) {
      const typedBucket = bucket as SkillEffectBucket;
      skillEffectBucketCounts[typedBucket] = (skillEffectBucketCounts[typedBucket] ?? 0) + (count ?? 0);
    }
  }

  const summary = {
    runtimeEnvironment,
    unitCount: results.length,
    discoveredUnitCount: loaded.discoveredUnitCount,
    successCount: results.filter((result) => result.status === "completed").length,
    failedCount: results.filter((result) => result.status === "failed").length,
    skippedCount: loaded.skippedCount,
    publishedTaskCount: results.reduce((sum, result) => sum + result.publishedTaskIds.length, 0),
    quarantinedTaskCount: results.reduce((sum, result) => sum + result.quarantinedTaskIds.length, 0),
    skillEffectEnabled: executeOptions.skillEffectEnabled,
    skillEffectModel: executeOptions.skillEffectModel,
    skillEffectBucketCounts,
    runsRoot: executeOptions.runsRoot,
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
