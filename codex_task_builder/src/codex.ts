import { promises as fs } from "node:fs";
import path from "node:path";
import { Codex, type ThreadOptions } from "@openai/codex-sdk";
import { z } from "zod";
import type { GenerationUnit } from "./discovery.js";
import type { DerivedTaskPlan, FamilyPlan, ReviewResult, WriterSummary } from "./schema.js";
import {
  familyPlanJsonSchema,
  familyPlanSchema,
  reviewResultJsonSchema,
  reviewResultSchema,
  writerSummaryJsonSchema,
  writerSummarySchema,
} from "./schema.js";
import { parseJsonWithFallback, pathExists } from "./utils.js";
import { buildFamilyPlannerPrompt, buildReviewerPrompt, buildTaskWriterPrompt, relativeDraftPath } from "./prompts.js";
import type { FamilyWorkspace } from "./workspace.js";

type StructuredRunResult<T> = {
  data: T;
  threadId: string | null;
  raw: string;
};

const writerSummaryPartialSchema = z
  .object({
    derivedTaskId: z.string().optional(),
    draftRelativePath: z.string().optional(),
    primaryOutputFile: z.string().optional(),
    filesWritten: z.array(z.string()).optional(),
    summary: z.string().optional(),
  })
  .passthrough();

function toPosixPath(value: string): string {
  return value.split(path.sep).join(path.posix.sep);
}

function compactErrorMessage(error: unknown, maxLength = 200): string {
  const message = error instanceof Error ? error.message : String(error);
  return message.length > maxLength ? `${message.slice(0, maxLength)}...` : message;
}

async function listFilesRecursively(
  dirPath: string,
  options: {
    rootRelativePrefix: string;
    ignoreDirNames?: Set<string>;
    ignorePathPrefixes?: string[];
    ignoreFileExtensions?: Set<string>;
    ignoreFileNames?: Set<string>;
    limit?: number;
  },
): Promise<string[]> {
  const results: string[] = [];
  const ignoreDirNames = options.ignoreDirNames ?? new Set<string>();
  const ignorePathPrefixes = options.ignorePathPrefixes ?? [];
  const ignoreFileExtensions = options.ignoreFileExtensions ?? new Set<string>();
  const ignoreFileNames = options.ignoreFileNames ?? new Set<string>();
  const limit = options.limit ?? 200;

  async function walk(currentDir: string, relativeDir: string): Promise<void> {
    if (results.length >= limit) {
      return;
    }
    const entries = await fs.readdir(currentDir, { withFileTypes: true });
    for (const entry of entries) {
      if (results.length >= limit) {
        return;
      }
      if (entry.isDirectory() && ignoreDirNames.has(entry.name)) {
        continue;
      }
      const relativePath = relativeDir ? path.join(relativeDir, entry.name) : entry.name;
      const posixRelativePath = toPosixPath(relativePath);
      if (ignorePathPrefixes.some((prefix) => posixRelativePath.startsWith(prefix))) {
        continue;
      }
      const fullPath = path.join(currentDir, entry.name);
      if (entry.isDirectory()) {
        await walk(fullPath, relativePath);
        continue;
      }
      if (!entry.isFile()) {
        continue;
      }
      if (ignoreFileNames.has(entry.name)) {
        continue;
      }
      const extension = path.extname(entry.name);
      if (extension && ignoreFileExtensions.has(extension)) {
        continue;
      }
      results.push(path.posix.join(options.rootRelativePrefix, posixRelativePath));
    }
  }

  await walk(dirPath, "");
  return results.sort((a, b) => a.localeCompare(b));
}

async function inferWriterFilesWritten(
  workspace: FamilyWorkspace,
  derivedTaskId: string,
  draftRelativePathValue: string,
): Promise<string[]> {
  const draftRelativePathNormalized = draftRelativePathValue || relativeDraftPath(derivedTaskId);
  const draftDir = path.join(workspace.rootDir, draftRelativePathNormalized);

  const required: string[] = [
    "task.toml",
    "instruction.md",
    path.posix.join("environment", "Dockerfile"),
    path.posix.join("solution", "solve.sh"),
    path.posix.join("tests", "test.sh"),
    path.posix.join("tests", "test_outputs.py"),
  ];

  const filesWritten: string[] = [];
  const prefix = toPosixPath(draftRelativePathNormalized);
  for (const rel of required) {
    if (await pathExists(path.join(draftDir, rel))) {
      filesWritten.push(path.posix.join(prefix, rel));
    }
  }

  const envDir = path.join(draftDir, "environment");
  if (await pathExists(envDir)) {
    const envFiles = await listFilesRecursively(envDir, {
      rootRelativePrefix: path.posix.join(prefix, "environment"),
      ignoreDirNames: new Set(["skills", "__pycache__", ".pytest_cache"]),
      ignoreFileExtensions: new Set([".pyc"]),
      ignoreFileNames: new Set(["Dockerfile"]),
      limit: 60,
    });
    filesWritten.push(...envFiles);
  }

  const unique = Array.from(new Set(filesWritten));
  if (unique.length > 0) {
    return unique;
  }

  return required.map((rel) => path.posix.join(prefix, rel));
}

export class CodexTaskBuilderClient {
  private readonly codex: Codex;
  private readonly threadBaseOptions: ThreadOptions;

  constructor() {
    this.codex = new Codex({
      codexPathOverride: process.env.CODEX_PATH,
    });

    this.threadBaseOptions = {
      model: process.env.CODEX_TASK_BUILDER_MODEL,
      sandboxMode: "workspace-write",
      approvalPolicy: "never",
      skipGitRepoCheck: true,
      networkAccessEnabled: process.env.CODEX_TASK_BUILDER_NETWORK_ACCESS === "1",
      modelReasoningEffort: "high",
    };
  }

  private makeThread(workingDirectory: string) {
    return this.codex.startThread({
      ...this.threadBaseOptions,
      workingDirectory,
    });
  }

  async planFamily(unit: GenerationUnit, workspace: FamilyWorkspace): Promise<StructuredRunResult<FamilyPlan>> {
    const thread = this.makeThread(workspace.rootDir);
    const turn = await thread.run(buildFamilyPlannerPrompt(unit), {
      outputSchema: familyPlanJsonSchema,
    });
    const parsed = familyPlanSchema.parse(parseJsonWithFallback<FamilyPlan>(turn.finalResponse));
    return {
      data: parsed,
      threadId: thread.id,
      raw: turn.finalResponse,
    };
  }

  async writeTask(
    unit: GenerationUnit,
    workspace: FamilyWorkspace,
    plan: DerivedTaskPlan,
  ): Promise<StructuredRunResult<WriterSummary>> {
    const thread = this.makeThread(workspace.rootDir);
    const turn = await thread.run(buildTaskWriterPrompt(unit, plan), {
      outputSchema: writerSummaryJsonSchema,
    });

    let parsedValue: unknown | null = null;
    let parseFailure: string | null = null;
    try {
      parsedValue = parseJsonWithFallback<unknown>(turn.finalResponse);
    } catch (error) {
      parseFailure = compactErrorMessage(error);
    }

    if (parsedValue) {
      const strict = writerSummarySchema.safeParse(parsedValue);
      if (strict.success) {
        return {
          data: strict.data,
          threadId: thread.id,
          raw: turn.finalResponse,
        };
      }
    }

    const partial = parsedValue ? writerSummaryPartialSchema.safeParse(parsedValue) : null;
    const derivedTaskId = partial?.success && partial.data.derivedTaskId ? partial.data.derivedTaskId : plan.derivedTaskId;
    const draftRelativePathValue =
      partial?.success && partial.data.draftRelativePath
        ? partial.data.draftRelativePath
        : relativeDraftPath(derivedTaskId);
    const primaryOutputFile =
      partial?.success && partial.data.primaryOutputFile ? partial.data.primaryOutputFile : plan.primaryOutputFile;
    const filesWritten =
      partial?.success && partial.data.filesWritten && partial.data.filesWritten.length > 0
        ? partial.data.filesWritten
        : await inferWriterFilesWritten(workspace, derivedTaskId, draftRelativePathValue);
    const summary =
      partial?.success && partial.data.summary
        ? partial.data.summary
        : `writer structured output 未通过校验${parseFailure ? `（${parseFailure}）` : ""}，已回退为从磁盘推断 filesWritten`;

    const parsed: WriterSummary = {
      derivedTaskId,
      draftRelativePath: draftRelativePathValue,
      primaryOutputFile,
      filesWritten,
      summary,
    };
    return {
      data: parsed,
      threadId: thread.id,
      raw: turn.finalResponse,
    };
  }

  async reviewFamily(
    unit: GenerationUnit,
    workspace: FamilyWorkspace,
    familyPlan: FamilyPlan,
  ): Promise<StructuredRunResult<ReviewResult>> {
    const thread = this.makeThread(workspace.rootDir);
    const turn = await thread.run(buildReviewerPrompt(unit, familyPlan), {
      outputSchema: reviewResultJsonSchema,
    });
    const parsed = reviewResultSchema.parse(parseJsonWithFallback<ReviewResult>(turn.finalResponse));
    return {
      data: parsed,
      threadId: thread.id,
      raw: turn.finalResponse,
    };
  }
}
