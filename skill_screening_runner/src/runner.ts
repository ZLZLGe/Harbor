import path from "node:path";
import { SkillScreeningCodexClient } from "./codex.js";
import { discoverSkills, discoverSubcategories } from "./discovery.js";
import {
  finalizeBatchRunArtifacts,
  finalizeRunArtifacts,
  loadExistingResult,
  prepareBatchOutputLayout,
  prepareOutputLayout,
  writeFailureArtifacts,
  writeSkillArtifacts,
} from "./output.js";
import { DEFAULT_PROMPT_PATH, DEFAULT_SCHEMA_PATH, buildScreeningPrompt } from "./prompt.js";
import { normalizeAndValidateScreeningResult, type ScreeningResult } from "./schema.js";
import type {
  BatchRunOptions,
  DiscoveredSkill,
  FailureRecord,
  RetainedSkillSource,
  SingleRunOptions,
  SkillScreeningRunResult,
} from "./types.js";
import { compactErrorMessage, pathExists, sanitizeFileComponent } from "./utils.js";

async function runWithConcurrency<T>(
  items: readonly T[],
  jobs: number,
  worker: (item: T, index: number) => Promise<void>,
): Promise<void> {
  const concurrency = Math.max(1, Math.min(jobs, items.length || 1));
  let nextIndex = 0;

  await Promise.all(
    Array.from({ length: concurrency }, async () => {
      while (true) {
        const currentIndex = nextIndex;
        nextIndex += 1;
        if (currentIndex >= items.length) {
          return;
        }
        await worker(items[currentIndex] as T, currentIndex);
      }
    }),
  );
}

type ResolvedAssets = {
  promptPath: string;
  schemaPath: string;
};

type SingleSubcategoryRunResult = {
  summary: Awaited<ReturnType<typeof finalizeRunArtifacts>>["summary"];
  manifest: Awaited<ReturnType<typeof finalizeRunArtifacts>>["manifest"];
  discoveredSkills: DiscoveredSkill[];
  results: ScreeningResult[];
  failures: FailureRecord[];
  resumedResults: number;
};

async function resolveAssets(options: { promptPath?: string; schemaPath?: string }): Promise<ResolvedAssets> {
  const promptPath = path.resolve(options.promptPath ?? DEFAULT_PROMPT_PATH);
  const schemaPath = path.resolve(options.schemaPath ?? DEFAULT_SCHEMA_PATH);

  if (!(await pathExists(promptPath))) {
    throw new Error(`prompt 文件不存在: ${promptPath}`);
  }
  if (!(await pathExists(schemaPath))) {
    throw new Error(`schema 文件不存在: ${schemaPath}`);
  }

  return {
    promptPath,
    schemaPath,
  };
}

function buildBatchSubcategoryOutputDir(categorySlug: string, subcategorySlug: string): string {
  return sanitizeFileComponent(`${categorySlug}__${subcategorySlug}`);
}

function collectRetainedSkillSources(args: {
  discoveredSkills: DiscoveredSkill[];
  results: ScreeningResult[];
}): RetainedSkillSource[] {
  const keptSkillDirectories = new Set(
    args.results.filter((result) => result.decision === "keep").map((result) => result.skill_dir),
  );

  return args.discoveredSkills
    .filter((skill) => keptSkillDirectories.has(skill.directoryName))
    .map((skill) => ({
      categorySlug: skill.categorySlug,
      subcategorySlug: skill.subcategorySlug,
      skillDir: skill.directoryName,
      absolutePath: skill.absolutePath,
    }));
}

async function runSingleSubcategoryScreening(
  options: SingleRunOptions,
  client: SkillScreeningCodexClient,
  assets: ResolvedAssets,
  materializeRetainedSkills: boolean,
): Promise<SingleSubcategoryRunResult> {
  const discoveredSkills = await discoverSkills(options.subcategoryDir);
  const selectedSkills = options.limit ? discoveredSkills.slice(0, options.limit) : discoveredSkills;
  const layout = await prepareOutputLayout(options.outputDir, options.overwrite);

  const results: ScreeningResult[] = [];
  const failures: FailureRecord[] = [];
  let resumedResults = 0;
  const startedAt = new Date().toISOString();

  await runWithConcurrency(selectedSkills, options.jobs, async (skill) => {
    if (options.resume) {
      const existingResult = await loadExistingResult(layout, skill);
      if (existingResult) {
        results.push(existingResult);
        resumedResults += 1;
        return;
      }
    }

    let prompt = "";
    let rawResponse = "";
    try {
      prompt = await buildScreeningPrompt({
        skill,
        promptPath: assets.promptPath,
        schemaPath: assets.schemaPath,
      });

      const run = await client.screenSkill(skill.absolutePath, prompt);
      rawResponse = run.raw;
      const result = normalizeAndValidateScreeningResult(run.parsed, skill);
      results.push(result);
      await writeSkillArtifacts({
        layout,
        skill,
        result,
        prompt,
        rawResponse: rawResponse,
      });
    } catch (error) {
      const failure: FailureRecord = {
        category_slug: skill.categorySlug,
        subcategory_slug: skill.subcategorySlug,
        skill_dir: skill.directoryName,
        skill_id: skill.skillId,
        skill_path: skill.absolutePath,
        error: compactErrorMessage(error),
        timestamp: new Date().toISOString(),
      };
      failures.push(failure);
      await writeFailureArtifacts({
        layout,
        skill,
        failure,
        prompt,
        rawResponse,
      });
    }
  });

  const finishedAt = new Date().toISOString();
  const finalized = await finalizeRunArtifacts({
    layout,
    options,
    discoveredSkills: selectedSkills,
    results,
    failures,
    resumedResults,
    startedAt,
    finishedAt,
    promptPath: assets.promptPath,
    schemaPath: assets.schemaPath,
    exportRetainedSkills: materializeRetainedSkills,
  });

  return {
    ...finalized,
    discoveredSkills: selectedSkills,
    results,
    failures,
    resumedResults,
  };
}

async function runBatchSkillScreening(
  options: BatchRunOptions,
  client: SkillScreeningCodexClient,
  assets: ResolvedAssets,
): Promise<SkillScreeningRunResult> {
  const discoveredSubcategories = await discoverSubcategories(options.inputDir);
  const batchLayout = await prepareBatchOutputLayout(options.outputDir, options.overwrite);
  const subcategorySummaries: Awaited<ReturnType<typeof finalizeRunArtifacts>>["summary"][] = [];
  const allResults: ScreeningResult[] = [];
  const allFailures: FailureRecord[] = [];
  const retainedSkillSources: RetainedSkillSource[] = [];
  let resumedResults = 0;
  const startedAt = new Date().toISOString();

  for (const subcategory of discoveredSubcategories) {
    const subcategoryOutputDir = path.join(
      batchLayout.rootDir,
      buildBatchSubcategoryOutputDir(subcategory.categorySlug, subcategory.subcategorySlug),
    );

    const singleResult = await runSingleSubcategoryScreening(
      {
        mode: "single",
        subcategoryDir: subcategory.absolutePath,
        outputDir: subcategoryOutputDir,
        model: options.model,
        jobs: options.jobs,
        limit: options.limit,
        resume: options.resume,
        overwrite: false,
        promptPath: options.promptPath,
        schemaPath: options.schemaPath,
      },
      client,
      assets,
      false,
    );

    subcategorySummaries.push(singleResult.summary);
    allResults.push(...singleResult.results);
    allFailures.push(...singleResult.failures);
    retainedSkillSources.push(
      ...collectRetainedSkillSources({
        discoveredSkills: singleResult.discoveredSkills,
        results: singleResult.results,
      }),
    );
    resumedResults += singleResult.resumedResults;
  }

  const finishedAt = new Date().toISOString();
  const finalized = await finalizeBatchRunArtifacts({
    layout: batchLayout,
    options,
    discoveredSubcategories,
    subcategorySummaries,
    results: allResults,
    failures: allFailures,
    resumedResults,
    startedAt,
    finishedAt,
    promptPath: assets.promptPath,
    schemaPath: assets.schemaPath,
    retainedSkillSources,
  });

  return {
    mode: "batch",
    ...finalized,
  };
}

export async function runSkillScreening(options: SingleRunOptions | BatchRunOptions): Promise<SkillScreeningRunResult> {
  const assets = await resolveAssets(options);
  const client = new SkillScreeningCodexClient({ model: options.model });

  if (options.mode === "batch") {
    return runBatchSkillScreening(options, client, assets);
  }

  const result = await runSingleSubcategoryScreening(options, client, assets, true);
  return {
    mode: "single",
    summary: result.summary,
    manifest: result.manifest,
  };
}
