import { promises as fs } from "node:fs";
import path from "node:path";
import {
  FINAL_TASKS_ROOT,
  QUARANTINE_ROOT,
  RAW_ROOT,
  assertPathWithinRoots,
  copyDir,
  copyFile,
  ensureDir,
  pathExists,
} from "./utils.js";

const MATERIALIZE_ALLOWLIST = [
  "task.toml",
  "instruction.md",
  "plan.json",
  "environment",
  "solution",
  "tests",
] as const;

async function copySelectedEntry(sourcePath: string, targetPath: string): Promise<void> {
  if (!(await pathExists(sourcePath))) {
    return;
  }

  const stat = await fs.stat(sourcePath);
  if (stat.isDirectory()) {
    await copyDir(sourcePath, targetPath);
    return;
  }

  if (stat.isFile()) {
    await copyFile(sourcePath, targetPath);
  }
}

export function buildMaterializedTaskDir(args: {
  targetRoot: string;
  sourceTaskId: string;
  scopeSlug: string;
  taskName: string;
}): string {
  return path.join(args.targetRoot, args.sourceTaskId, args.scopeSlug, args.taskName);
}

export type MaterializeResult = {
  targetTaskDir: string;
  disposition: "created" | "existing";
};

export async function sanitizeAndCopyTask(args: {
  sourceDraftDir: string;
  sourceTaskId: string;
  scopeSlug: string;
  taskName: string;
  rawRoot?: string;
  targetRoot?: string;
}): Promise<MaterializeResult> {
  const targetRoot = args.targetRoot ?? FINAL_TASKS_ROOT;
  const rawRoot = args.rawRoot ?? RAW_ROOT;
  const targetTaskDir = buildMaterializedTaskDir({
    targetRoot,
    sourceTaskId: args.sourceTaskId,
    scopeSlug: args.scopeSlug,
    taskName: args.taskName,
  });

  assertPathWithinRoots(args.sourceDraftDir, [rawRoot, RAW_ROOT], "raw task");
  assertPathWithinRoots(targetTaskDir, [FINAL_TASKS_ROOT, QUARANTINE_ROOT, targetRoot], "发布目标");

  await ensureDir(path.dirname(targetTaskDir));
  if (await pathExists(targetTaskDir)) {
    return {
      targetTaskDir,
      disposition: "existing",
    };
  }

  await ensureDir(targetTaskDir);
  for (const relativePath of MATERIALIZE_ALLOWLIST) {
    await copySelectedEntry(path.join(args.sourceDraftDir, relativePath), path.join(targetTaskDir, relativePath));
  }

  return {
    targetTaskDir,
    disposition: "created",
  };
}
