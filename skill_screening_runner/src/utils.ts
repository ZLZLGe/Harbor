import { promises as fs } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const MODULE_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

export function compactErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  if (typeof error === "string") {
    return error;
  }
  try {
    return JSON.stringify(error);
  } catch {
    return String(error);
  }
}

export function sanitizeFileComponent(value: string): string {
  return value.replace(/[^A-Za-z0-9._-]+/g, "_");
}

export function parsePositiveInteger(rawValue: string, label: string): number {
  const value = Number(rawValue);
  if (!Number.isInteger(value) || value < 1) {
    throw new Error(`${label} 必须是正整数，收到: ${rawValue}`);
  }
  return value;
}

export async function pathExists(targetPath: string): Promise<boolean> {
  try {
    await fs.access(targetPath);
    return true;
  } catch {
    return false;
  }
}

export function parseJsonWithFallback(text: string): unknown {
  const trimmed = text.trim();
  const candidates = new Set<string>();
  if (trimmed) {
    candidates.add(trimmed);
  }

  const fencedMatches = trimmed.match(/```(?:json)?\s*([\s\S]*?)```/gi);
  if (fencedMatches) {
    for (const block of fencedMatches) {
      const inner = block.replace(/```(?:json)?/i, "").replace(/```$/, "").trim();
      if (inner) {
        candidates.add(inner);
      }
    }
  }

  const firstBrace = trimmed.indexOf("{");
  const lastBrace = trimmed.lastIndexOf("}");
  if (firstBrace >= 0 && lastBrace > firstBrace) {
    candidates.add(trimmed.slice(firstBrace, lastBrace + 1));
  }

  for (const candidate of candidates) {
    try {
      return JSON.parse(candidate);
    } catch {
      // Try the next candidate.
    }
  }

  throw new Error("structured output 不是合法 JSON");
}

export function uniqueStrings(values: string[]): string[] {
  return Array.from(new Set(values));
}

export async function writeJsonFile(targetPath: string, value: unknown): Promise<void> {
  await fs.writeFile(targetPath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

export function compareNumbersDescending(left: number, right: number): number {
  return right - left;
}

export function compareStringsAscending(left: string, right: string): number {
  return left.localeCompare(right, "en");
}

export function toPosixRelative(rootDir: string, absolutePath: string): string {
  return path.relative(rootDir, absolutePath).split(path.sep).join(path.posix.sep);
}
