import path from "node:path";
import { RAW_ROOT, RUNS_ROOT, ensureDir, writeText } from "./utils.js";
import { promises as fs } from "node:fs";

export type ManifestEntry = {
  timestamp: string;
  runId: string;
  sourceTaskId: string;
  phase: string;
  status: "started" | "completed" | "failed" | "skipped";
  derivedTaskId?: string;
  threadId?: string | null;
  draftDir?: string;
  publishedDir?: string;
  issues?: string[];
  metadata?: Record<string, unknown>;
};

export function resolveRunsRoot(options: { rawRoot: string; runsRoot?: string | null }): string {
  const explicitRunsRoot = options.runsRoot?.trim();
  if (explicitRunsRoot) {
    return explicitRunsRoot;
  }
  return options.rawRoot === RAW_ROOT ? RUNS_ROOT : path.dirname(options.rawRoot);
}

export function buildManifestPath(runsRoot: string): string {
  return path.join(runsRoot, "manifest.jsonl");
}

export function buildRunSummaryPath(runsRoot: string, runId: string): string {
  return path.join(runsRoot, `${runId}.json`);
}

export async function appendManifest(
  entry: Omit<ManifestEntry, "timestamp">,
  runsRoot: string = RUNS_ROOT,
): Promise<void> {
  await ensureDir(runsRoot);
  const line = `${JSON.stringify({
    timestamp: new Date().toISOString(),
    ...entry,
  })}\n`;
  await fs.appendFile(buildManifestPath(runsRoot), line, "utf-8");
}

export async function writeRunSummary(runId: string, summary: unknown, runsRoot: string = RUNS_ROOT): Promise<void> {
  const summaryPath = buildRunSummaryPath(runsRoot, runId);
  await writeText(summaryPath, `${JSON.stringify(summary, null, 2)}\n`);
}
