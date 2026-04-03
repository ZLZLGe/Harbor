import { promises as fs } from "node:fs";
import path from "node:path";
import type { GenerationUnit, SkillInfo } from "./discovery.js";
import type { DerivedTaskPlan } from "./schema.js";
import { buildTaskBuilderBrief, relativeDraftPath } from "./prompts.js";
import {
  HARBOR_BUILDER_SKILL_ROOT,
  RAW_ROOT,
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
  builderRefsDir: string;
  harborBuilderRefDir: string;
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

async function copyBuilderRefs(targetDir: string): Promise<void> {
  if (!(await pathExists(HARBOR_BUILDER_SKILL_ROOT))) {
    throw new Error(`builder harbor skill 不存在: ${HARBOR_BUILDER_SKILL_ROOT}`);
  }
  await copyDir(HARBOR_BUILDER_SKILL_ROOT, targetDir);
}

export async function createFamilyWorkspace(
  unit: GenerationUnit,
  options: {
    rawRoot?: string;
    runId?: string;
  } = {},
): Promise<FamilyWorkspace> {
  const sourceTask = unit.sourceTask;
  const runId = options.runId ?? makeRunId(`${sourceTask.sourceTaskId}-${unit.scopeSlug}`);
  const rawRoot = options.rawRoot ?? RAW_ROOT;
  const rootDir = path.join(rawRoot, runId, sourceTask.sourceTaskId, unit.scopeSlug);
  const sourceTaskDir = path.join(rootDir, "source_task");
  const builderRefsDir = path.join(rootDir, "builder_refs");
  const harborBuilderRefDir = path.join(builderRefsDir, "harbor");
  const draftsDir = path.join(rootDir, "drafts");
  const artifactsDir = path.join(rootDir, "artifacts");
  const briefPath = path.join(rootDir, "TASK_BUILDER_BRIEF.md");

  await ensureDir(rootDir);
  await ensureDir(draftsDir);
  await ensureDir(artifactsDir);
  await copyScopedSourceTask(unit, sourceTaskDir);
  await ensureDir(builderRefsDir);
  await copyBuilderRefs(harborBuilderRefDir);
  await writeText(briefPath, `${buildTaskBuilderBrief(unit)}\n`);
  await writeJson(path.join(artifactsDir, "generation-unit.json"), unit);

  return {
    runId,
    sourceTaskId: sourceTask.sourceTaskId,
    skillMode: unit.skillMode,
    targetSkill: unit.targetSkill,
    scopeSlug: unit.scopeSlug,
    rootDir,
    sourceTaskDir,
    builderRefsDir,
    harborBuilderRefDir,
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

  await writeJson(path.join(draftDir, "plan.json"), plan);
  return draftDir;
}

export async function findLatestWorkspaceForSource(
  sourceTaskId: string,
  options: {
    rawRoot?: string;
    scopeSlug?: string;
  } = {},
): Promise<FamilyWorkspace | null> {
  const rawRoot = options.rawRoot ?? RAW_ROOT;
  if (!(await pathExists(rawRoot))) {
    return null;
  }

  const runDirs = await fs.readdir(rawRoot, { withFileTypes: true });
  const candidates: Array<{ rootDir: string; mtimeMs: number }> = [];

  for (const runDir of runDirs) {
    if (!runDir.isDirectory()) {
      continue;
    }
    const sourceDir = path.join(rawRoot, runDir.name, sourceTaskId);
    if (!(await pathExists(sourceDir))) {
      continue;
    }
    const scopeDirs = await fs.readdir(sourceDir, { withFileTypes: true });
    for (const scopeDir of scopeDirs) {
      if (!scopeDir.isDirectory()) {
        continue;
      }
      if (options.scopeSlug && scopeDir.name !== options.scopeSlug) {
        continue;
      }
      const candidateRoot = path.join(sourceDir, scopeDir.name);
      const stat = await fs.stat(candidateRoot);
      candidates.push({ rootDir: candidateRoot, mtimeMs: stat.mtimeMs });
    }
  }

  candidates.sort((a, b) => b.mtimeMs - a.mtimeMs);
  const latest = candidates[0];
  if (!latest) {
    return null;
  }

  const runId = path.basename(path.dirname(path.dirname(latest.rootDir)));
  const scopeSlug = path.basename(latest.rootDir);
  const artifactsDir = path.join(latest.rootDir, "artifacts");
  const generationUnitPath = path.join(artifactsDir, "generation-unit.json");

  let skillMode: "all" | "per-skill" = "all";
  let targetSkill: SkillInfo | null = null;
  if (await pathExists(generationUnitPath)) {
    const raw = await fs.readFile(generationUnitPath, "utf-8");
    const unit = JSON.parse(raw) as { skillMode?: "all" | "per-skill"; targetSkill?: SkillInfo | null };
    skillMode = unit.skillMode ?? "all";
    targetSkill = unit.targetSkill ?? null;
  }

  return {
    runId,
    sourceTaskId,
    skillMode,
    targetSkill,
    scopeSlug,
    rootDir: latest.rootDir,
    sourceTaskDir: path.join(latest.rootDir, "source_task"),
    builderRefsDir: path.join(latest.rootDir, "builder_refs"),
    harborBuilderRefDir: path.join(latest.rootDir, "builder_refs", "harbor"),
    draftsDir: path.join(latest.rootDir, "drafts"),
    artifactsDir,
    briefPath: path.join(latest.rootDir, "TASK_BUILDER_BRIEF.md"),
  };
}
