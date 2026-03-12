import path from "node:path";
import { RUNS_ROOT, ensureDir, writeText } from "./utils.js";
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

export const MANIFEST_PATH = path.join(RUNS_ROOT, "manifest.jsonl");

export async function appendManifest(entry: Omit<ManifestEntry, "timestamp">): Promise<void> {
  await ensureDir(RUNS_ROOT);
  const line = `${JSON.stringify({
    timestamp: new Date().toISOString(),
    ...entry,
  })}\n`;
  await fs.appendFile(MANIFEST_PATH, line, "utf-8");
}

export async function writeRunSummary(runId: string, summary: unknown): Promise<void> {
  const summaryPath = path.join(RUNS_ROOT, `${runId}.json`);
  await writeText(summaryPath, `${JSON.stringify(summary, null, 2)}\n`);
}
