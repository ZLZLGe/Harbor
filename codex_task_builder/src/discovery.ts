import { promises as fs } from "node:fs";
import path from "node:path";
import { SOURCE_TASKS_ROOT, listDirectories, pathExists, readText } from "./utils.js";

export type TaskMetadata = {
  id?: string;
  name?: string;
  difficulty?: string;
  category?: string;
  tags: string[];
};

export type SkillInfo = {
  name: string;
  dirName: string;
  relativeDir: string;
  skillMdPath: string;
};

export type SkillMode = "all" | "per-skill";

export type SourceTask = {
  sourceTaskId: string;
  sourceDir: string;
  taskTomlPath: string;
  instructionPath: string;
  environmentDir: string;
  solutionDir: string;
  testsDir: string;
  skillsDir: string;
  metadata: TaskMetadata;
  skills: SkillInfo[];
};

export type GenerationUnit = {
  sourceTask: SourceTask;
  skillMode: SkillMode;
  targetSkill: SkillInfo | null;
  scopeSlug: string;
  scopeLabel: string;
};

function extractTomlValue(text: string, key: string): string | undefined {
  const match = text.match(new RegExp(`^\\s*${key}\\s*=\\s*"([^"]+)"`, "m"));
  return match?.[1];
}

function extractTomlTags(text: string): string[] {
  const match = text.match(/^\s*tags\s*=\s*\[(.*?)\]/ms);
  if (!match) {
    return [];
  }
  return match[1]
    .split(",")
    .map((part) => part.trim().replace(/^"|"$/g, ""))
    .filter(Boolean);
}

async function parseSkillName(skillMdPath: string, fallback: string): Promise<string> {
  const raw = await readText(skillMdPath);
  const frontmatterName = raw.match(/^name:\s*"?(.*?)"?$/m)?.[1];
  const yamlFrontmatterName = raw.match(/^---[\s\S]*?^name:\s*"?(.*?)"?$/m)?.[1];
  return (frontmatterName ?? yamlFrontmatterName ?? fallback).trim();
}

async function discoverSkills(skillsDir: string): Promise<SkillInfo[]> {
  if (!(await pathExists(skillsDir))) {
    return [];
  }
  const dirs = await listDirectories(skillsDir);
  const skills: SkillInfo[] = [];
  for (const dir of dirs) {
    const skillMdPath = path.join(dir, "SKILL.md");
    if (!(await pathExists(skillMdPath))) {
      continue;
    }
    const dirName = path.basename(dir);
    skills.push({
      name: await parseSkillName(skillMdPath, dirName),
      dirName,
      relativeDir: path.relative(skillsDir, dir),
      skillMdPath,
    });
  }
  return skills.sort((a, b) => a.name.localeCompare(b.name));
}

export async function discoverSourceTaskById(
  sourceTaskId: string,
  sourceRoot = SOURCE_TASKS_ROOT,
): Promise<SourceTask> {
  const sourceDir = path.join(sourceRoot, sourceTaskId);
  const taskTomlPath = path.join(sourceDir, "task.toml");
  const instructionPath = path.join(sourceDir, "instruction.md");
  const environmentDir = path.join(sourceDir, "environment");
  const solutionDir = path.join(sourceDir, "solution");
  const testsDir = path.join(sourceDir, "tests");
  const skillsDir = path.join(environmentDir, "skills");

  const taskToml = await readText(taskTomlPath);
  const metadata: TaskMetadata = {
    id: extractTomlValue(taskToml, "id"),
    name: extractTomlValue(taskToml, "name"),
    difficulty: extractTomlValue(taskToml, "difficulty"),
    category: extractTomlValue(taskToml, "category"),
    tags: extractTomlTags(taskToml),
  };

  return {
    sourceTaskId,
    sourceDir,
    taskTomlPath,
    instructionPath,
    environmentDir,
    solutionDir,
    testsDir,
    skillsDir,
    metadata,
    skills: await discoverSkills(skillsDir),
  };
}

export async function discoverSourceTasks(sourceRoot = SOURCE_TASKS_ROOT): Promise<SourceTask[]> {
  const dirs = await listDirectories(sourceRoot);
  const tasks: SourceTask[] = [];
  for (const dir of dirs) {
    const sourceTaskId = path.basename(dir);
    tasks.push(await discoverSourceTaskById(sourceTaskId, sourceRoot));
  }
  return tasks;
}

export function buildGenerationUnits(sourceTask: SourceTask, skillMode: SkillMode): GenerationUnit[] {
  if (skillMode === "all") {
    return [
      {
        sourceTask,
        skillMode,
        targetSkill: null,
        scopeSlug: "all-skills",
        scopeLabel: "All skills",
      },
    ];
  }

  if (sourceTask.skills.length === 0) {
    throw new Error(`source task ${sourceTask.sourceTaskId} 没有可用 skills，无法使用 per-skill 模式`);
  }

  return sourceTask.skills.map((skill) => ({
    sourceTask,
    skillMode,
    targetSkill: skill,
    scopeSlug: skill.dirName,
    scopeLabel: skill.name,
  }));
}

export function getVisibleSkills(unit: GenerationUnit): SkillInfo[] {
  return unit.targetSkill ? [unit.targetSkill] : unit.sourceTask.skills;
}

export async function collectEnvironmentAssetPaths(sourceTask: SourceTask): Promise<string[]> {
  const assets: string[] = [];
  async function walk(currentDir: string): Promise<void> {
    const entries = await fs.readdir(currentDir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(currentDir, entry.name);
      if (fullPath.startsWith(sourceTask.skillsDir)) {
        continue;
      }
      if (entry.isDirectory()) {
        await walk(fullPath);
      } else {
        assets.push(path.relative(sourceTask.environmentDir, fullPath));
      }
    }
  }
  if (await pathExists(sourceTask.environmentDir)) {
    await walk(sourceTask.environmentDir);
  }
  return assets.sort((a, b) => a.localeCompare(b));
}
