import { spawn } from "node:child_process";
import { promises as fs } from "node:fs";
import path from "node:path";

export const REPO_ROOT = "/home/levi/Harbor";
export const SOURCE_TASKS_ROOT = path.join(REPO_ROOT, "tasks_library", "skillsbench", "tasks");
export const INTEGRATED_TASKS_ROOT = path.join(REPO_ROOT, "tasks_library", "integrated_tasks");
export const RUNS_ROOT = path.join(REPO_ROOT, "codex_task_builder_runs");
export const SCRATCH_ROOT = path.join(RUNS_ROOT, "scratch");

export type CommandResult = {
  code: number;
  stdout: string;
  stderr: string;
};

export async function ensureDir(dirPath: string): Promise<void> {
  await fs.mkdir(dirPath, { recursive: true });
}

export async function pathExists(targetPath: string): Promise<boolean> {
  try {
    await fs.access(targetPath);
    return true;
  } catch {
    return false;
  }
}

export async function readText(filePath: string): Promise<string> {
  return fs.readFile(filePath, "utf-8");
}

export async function writeText(filePath: string, content: string): Promise<void> {
  await ensureDir(path.dirname(filePath));
  await fs.writeFile(filePath, content, "utf-8");
}

export async function writeJson(filePath: string, value: unknown): Promise<void> {
  await writeText(filePath, `${JSON.stringify(value, null, 2)}\n`);
}

export async function copyDir(source: string, target: string): Promise<void> {
  await ensureDir(path.dirname(target));
  await fs.cp(source, target, { recursive: true, force: true });
}

export async function copyFile(source: string, target: string): Promise<void> {
  await ensureDir(path.dirname(target));
  await fs.copyFile(source, target);
}

export function makeRunId(sourceTaskId: string): string {
  const stamp = new Date().toISOString().replace(/[-:TZ.]/g, "").slice(0, 14);
  const suffix = Math.random().toString(36).slice(2, 8);
  return `${stamp}-${slugify(sourceTaskId)}-${suffix}`;
}

export function slugify(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .replace(/-{2,}/g, "-");
}

export function dedent(text: string): string {
  const lines = text.replace(/^\n/, "").split("\n");
  const indents = lines
    .filter((line) => line.trim().length > 0)
    .map((line) => line.match(/^ */)?.[0].length ?? 0);
  const trim = indents.length > 0 ? Math.min(...indents) : 0;
  return lines.map((line) => line.slice(trim)).join("\n").trimEnd();
}

export function parseJsonWithFallback<T>(raw: string): T {
  try {
    return JSON.parse(raw) as T;
  } catch {
    const fenced = raw.match(/```(?:json)?\s*([\s\S]*?)```/i);
    if (fenced) {
      return JSON.parse(fenced[1]) as T;
    }
    throw new Error(`无法解析结构化输出: ${raw}`);
  }
}

export async function runCommand(
  command: string,
  args: string[],
  options: {
    cwd?: string;
    env?: NodeJS.ProcessEnv;
  } = {},
): Promise<CommandResult> {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd: options.cwd,
      env: options.env,
      stdio: ["ignore", "pipe", "pipe"],
    });

    let stdout = "";
    let stderr = "";

    child.stdout.on("data", (chunk: Buffer | string) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk: Buffer | string) => {
      stderr += chunk.toString();
    });
    child.on("error", reject);
    child.on("close", (code) => {
      resolve({
        code: code ?? 1,
        stdout,
        stderr,
      });
    });
  });
}

export async function listDirectories(root: string): Promise<string[]> {
  const entries = await fs.readdir(root, { withFileTypes: true });
  return entries
    .filter((entry) => entry.isDirectory())
    .map((entry) => path.join(root, entry.name))
    .sort((a, b) => a.localeCompare(b));
}

export function formatIssueList(issues: string[]): string {
  return issues.map((issue) => `- ${issue}`).join("\n");
}
