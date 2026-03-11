import { promises as fs } from "node:fs";
import path from "node:path";
import type { SourceTask } from "./discovery.js";
import type { DerivedTaskPlan } from "./schema.js";
import { buildTaskBuilderBrief, relativeDraftPath } from "./prompts.js";
import {
  SCRATCH_ROOT,
  copyDir,
  ensureDir,
  makeRunId,
  pathExists,
  writeJson,
  writeText,
} from "./utils.js";

export type FamilyWorkspace = {
  runId: string;
  sourceTaskId: string;
  rootDir: string;
  sourceTaskDir: string;
  draftsDir: string;
  artifactsDir: string;
  briefPath: string;
};

export async function createFamilyWorkspace(
  sourceTask: SourceTask,
  options: {
    scratchRoot?: string;
    runId?: string;
  } = {},
): Promise<FamilyWorkspace> {
  const runId = options.runId ?? makeRunId(sourceTask.sourceTaskId);
  const scratchRoot = options.scratchRoot ?? SCRATCH_ROOT;
  const rootDir = path.join(scratchRoot, runId, sourceTask.sourceTaskId);
  const sourceTaskDir = path.join(rootDir, "source_task");
  const draftsDir = path.join(rootDir, "drafts");
  const artifactsDir = path.join(rootDir, "artifacts");
  const briefPath = path.join(rootDir, "TASK_BUILDER_BRIEF.md");

  await ensureDir(rootDir);
  await ensureDir(draftsDir);
  await ensureDir(artifactsDir);
  await copyDir(sourceTask.sourceDir, sourceTaskDir);
  await writeText(briefPath, `${buildTaskBuilderBrief(sourceTask)}\n`);
  await writeJson(path.join(artifactsDir, "source-task.json"), sourceTask);

  return {
    runId,
    sourceTaskId: sourceTask.sourceTaskId,
    rootDir,
    sourceTaskDir,
    draftsDir,
    artifactsDir,
    briefPath,
  };
}

export async function prepareDraftSkeleton(
  workspace: FamilyWorkspace,
  sourceTask: SourceTask,
  plan: DerivedTaskPlan,
): Promise<string> {
  const draftDir = path.join(workspace.rootDir, relativeDraftPath(plan.derivedTaskId));
  await ensureDir(path.join(draftDir, "environment"));
  await ensureDir(path.join(draftDir, "solution"));
  await ensureDir(path.join(draftDir, "tests"));

  const sourceSkillsDir = path.join(sourceTask.environmentDir, "skills");
  if (await pathExists(sourceSkillsDir)) {
    await copyDir(sourceSkillsDir, path.join(draftDir, "environment", "skills"));
  }

  await writeJson(path.join(draftDir, "PLAN.json"), plan);
  return draftDir;
}

export async function findLatestWorkspaceForSource(
  sourceTaskId: string,
  scratchRoot = SCRATCH_ROOT,
): Promise<FamilyWorkspace | null> {
  if (!(await pathExists(scratchRoot))) {
    return null;
  }

  const runDirs = await fs.readdir(scratchRoot, { withFileTypes: true });
  const candidates: Array<{ path: string; mtimeMs: number }> = [];

  for (const runDir of runDirs) {
    if (!runDir.isDirectory()) {
      continue;
    }
    const candidateRoot = path.join(scratchRoot, runDir.name, sourceTaskId);
    if (!(await pathExists(candidateRoot))) {
      continue;
    }
    const stat = await fs.stat(candidateRoot);
    candidates.push({ path: candidateRoot, mtimeMs: stat.mtimeMs });
  }

  candidates.sort((a, b) => b.mtimeMs - a.mtimeMs);
  const latest = candidates[0];
  if (!latest) {
    return null;
  }

  const runId = path.basename(path.dirname(latest.path));
  return {
    runId,
    sourceTaskId,
    rootDir: latest.path,
    sourceTaskDir: path.join(latest.path, "source_task"),
    draftsDir: path.join(latest.path, "drafts"),
    artifactsDir: path.join(latest.path, "artifacts"),
    briefPath: path.join(latest.path, "TASK_BUILDER_BRIEF.md"),
  };
}
