import { promises as fs } from "node:fs";
import path from "node:path";
import type { GenerationUnit, SkillInfo } from "./discovery.js";
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
  skillMode: "all" | "per-skill";
  targetSkill: SkillInfo | null;
  scopeSlug: string;
  rootDir: string;
  sourceTaskDir: string;
  draftsDir: string;
  artifactsDir: string;
  briefPath: string;
};

async function copyScopedSourceTask(unit: GenerationUnit, targetDir: string): Promise<void> {
  const sourceTask = unit.sourceTask;
  if (unit.skillMode === "all") {
    await copyDir(sourceTask.sourceDir, targetDir);
    return;
  }

  const sourceSkillsDir = path.join(sourceTask.environmentDir, "skills");
  const selectedSkillDir = unit.targetSkill
    ? path.join(sourceSkillsDir, unit.targetSkill.relativeDir)
    : null;

  await ensureDir(path.dirname(targetDir));
  await fs.cp(sourceTask.sourceDir, targetDir, {
    recursive: true,
    force: true,
    filter: (src) => {
      if (!selectedSkillDir) {
        return !src.startsWith(sourceSkillsDir);
      }
      if (!src.startsWith(sourceSkillsDir)) {
        return true;
      }
      return src === sourceSkillsDir || src === selectedSkillDir || src.startsWith(`${selectedSkillDir}${path.sep}`);
    },
  });
}

export async function createFamilyWorkspace(
  unit: GenerationUnit,
  options: {
    scratchRoot?: string;
    runId?: string;
  } = {},
): Promise<FamilyWorkspace> {
  const sourceTask = unit.sourceTask;
  const runId = options.runId ?? makeRunId(`${sourceTask.sourceTaskId}-${unit.scopeSlug}`);
  const scratchRoot = options.scratchRoot ?? SCRATCH_ROOT;
  const rootDir = path.join(scratchRoot, runId, sourceTask.sourceTaskId);
  const sourceTaskDir = path.join(rootDir, "source_task");
  const draftsDir = path.join(rootDir, "drafts");
  const artifactsDir = path.join(rootDir, "artifacts");
  const briefPath = path.join(rootDir, "TASK_BUILDER_BRIEF.md");

  await ensureDir(rootDir);
  await ensureDir(draftsDir);
  await ensureDir(artifactsDir);
  await copyScopedSourceTask(unit, sourceTaskDir);
  await writeText(briefPath, `${buildTaskBuilderBrief(unit)}\n`);
  await writeJson(path.join(artifactsDir, "source-task.json"), {
    sourceTask,
    skillMode: unit.skillMode,
    targetSkill: unit.targetSkill,
  });

  return {
    runId,
    sourceTaskId: sourceTask.sourceTaskId,
    skillMode: unit.skillMode,
    targetSkill: unit.targetSkill,
    scopeSlug: unit.scopeSlug,
    rootDir,
    sourceTaskDir,
    draftsDir,
    artifactsDir,
    briefPath,
  };
}

export async function prepareDraftSkeleton(
  workspace: FamilyWorkspace,
  plan: DerivedTaskPlan,
): Promise<string> {
  const draftDir = path.join(workspace.rootDir, relativeDraftPath(plan.derivedTaskId));
  await ensureDir(path.join(draftDir, "environment"));
  await ensureDir(path.join(draftDir, "solution"));
  await ensureDir(path.join(draftDir, "tests"));

  const sourceSkillsDir = path.join(workspace.sourceTaskDir, "environment", "skills");
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
  const artifactsDir = path.join(latest.path, "artifacts");
  const sourceTaskInfoPath = path.join(artifactsDir, "source-task.json");
  let skillMode: "all" | "per-skill" = "all";
  let targetSkill: SkillInfo | null = null;
  if (await pathExists(sourceTaskInfoPath)) {
    const sourceTaskInfoRaw = await fs.readFile(sourceTaskInfoPath, "utf-8");
    const sourceTaskInfo = JSON.parse(sourceTaskInfoRaw) as {
      skillMode?: "all" | "per-skill";
      targetSkill?: SkillInfo | null;
    };
    skillMode = sourceTaskInfo.skillMode ?? "all";
    targetSkill = sourceTaskInfo.targetSkill ?? null;
  }

  return {
    runId,
    sourceTaskId,
    skillMode,
    targetSkill,
    scopeSlug: targetSkill?.dirName ?? "all-skills",
    rootDir: latest.path,
    sourceTaskDir: path.join(latest.path, "source_task"),
    draftsDir: path.join(latest.path, "drafts"),
    artifactsDir,
    briefPath: path.join(latest.path, "TASK_BUILDER_BRIEF.md"),
  };
}
