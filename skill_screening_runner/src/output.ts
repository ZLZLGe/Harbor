import { promises as fs } from "node:fs";
import path from "node:path";
import type {
  BatchOutputLayout,
  BatchResultIndexEntry,
  BatchRunManifest,
  BatchScreeningSummary,
  BatchSubcategorySummaryEntry,
  DiscoveredSubcategory,
  FailureRecord,
  OutputLayout,
  RetainedSkillSource,
  ResultIndexEntry,
  SingleRunManifest,
  SingleRunOptions,
  ScreeningSummary,
} from "./types.js";
import type { DiscoveredSkill } from "./types.js";
import { normalizeAndValidateLoadedScreeningResult, type ScreeningResult } from "./schema.js";
import {
  compareNumbersDescending,
  compareStringsAscending,
  pathExists,
  sanitizeFileComponent,
  writeJsonFile,
} from "./utils.js";

function buildArtifactBaseName(skill: DiscoveredSkill): string {
  return sanitizeFileComponent(skill.directoryName);
}

function buildBatchRetainedArtifactBaseName(skill: RetainedSkillSource): string {
  return sanitizeFileComponent(`${skill.categorySlug}__${skill.subcategorySlug}__${skill.skillDir}`);
}

export async function prepareOutputLayout(outputDir: string, overwrite: boolean): Promise<OutputLayout> {
  const rootDir = path.resolve(outputDir);
  if (overwrite && (await pathExists(rootDir))) {
    await fs.rm(rootDir, { recursive: true, force: true });
  }

  const skillsDir = path.join(rootDir, "skills");
  const logsDir = path.join(rootDir, "logs");
  await fs.mkdir(skillsDir, { recursive: true });
  await fs.mkdir(logsDir, { recursive: true });

  return {
    rootDir,
    skillsDir,
    logsDir,
    retainedSkillsDir: path.join(rootDir, "retained_skills"),
    manifestPath: path.join(rootDir, "run_manifest.json"),
    summaryPath: path.join(rootDir, "summary.json"),
    keepIndexPath: path.join(rootDir, "keep_index.json"),
    dropIndexPath: path.join(rootDir, "drop_index.json"),
    failuresPath: path.join(rootDir, "failures.json"),
  };
}

export async function prepareBatchOutputLayout(outputDir: string, overwrite: boolean): Promise<BatchOutputLayout> {
  const rootDir = path.resolve(outputDir);
  if (overwrite && (await pathExists(rootDir))) {
    await fs.rm(rootDir, { recursive: true, force: true });
  }

  await fs.mkdir(rootDir, { recursive: true });

  return {
    rootDir,
    retainedSkillsDir: path.join(rootDir, "retained_skills"),
    manifestPath: path.join(rootDir, "batch_manifest.json"),
    summaryPath: path.join(rootDir, "batch_summary.json"),
    keepIndexPath: path.join(rootDir, "batch_keep_index.json"),
    dropIndexPath: path.join(rootDir, "batch_drop_index.json"),
    failuresPath: path.join(rootDir, "batch_failures.json"),
  };
}

export async function loadExistingResult(layout: OutputLayout, skill: DiscoveredSkill): Promise<ScreeningResult | null> {
  const resultPath = path.join(layout.skillsDir, `${buildArtifactBaseName(skill)}.json`);
  if (!(await pathExists(resultPath))) {
    return null;
  }

  const raw = await fs.readFile(resultPath, "utf8");
  try {
    return normalizeAndValidateLoadedScreeningResult(JSON.parse(raw), skill);
  } catch {
    return null;
  }
}

export async function writeSkillArtifacts(args: {
  layout: OutputLayout;
  skill: DiscoveredSkill;
  result: ScreeningResult;
  prompt: string;
  rawResponse: string;
}): Promise<void> {
  const baseName = buildArtifactBaseName(args.skill);
  await writeJsonFile(path.join(args.layout.skillsDir, `${baseName}.json`), args.result);
  await fs.writeFile(path.join(args.layout.logsDir, `${baseName}.prompt.md`), args.prompt, "utf8");
  await fs.writeFile(path.join(args.layout.logsDir, `${baseName}.raw.txt`), `${args.rawResponse.trim()}\n`, "utf8");
}

export async function writeFailureArtifacts(args: {
  layout: OutputLayout;
  skill: DiscoveredSkill;
  failure: FailureRecord;
  prompt: string;
  rawResponse?: string;
}): Promise<void> {
  const baseName = buildArtifactBaseName(args.skill);
  await fs.writeFile(path.join(args.layout.logsDir, `${baseName}.prompt.md`), args.prompt, "utf8");
  await fs.writeFile(path.join(args.layout.logsDir, `${baseName}.error.txt`), `${args.failure.error}\n`, "utf8");
  if (args.rawResponse && args.rawResponse.trim()) {
    await fs.writeFile(path.join(args.layout.logsDir, `${baseName}.raw.txt`), `${args.rawResponse.trim()}\n`, "utf8");
  }
}

async function rebuildDirectory(targetDir: string): Promise<void> {
  await fs.rm(targetDir, { recursive: true, force: true });
  await fs.mkdir(targetDir, { recursive: true });
}

async function syncRetainedSkillsDirectory(args: {
  retainedSkillsDir: string;
  retainedSkills: Array<{ absolutePath: string; targetName: string }>;
}): Promise<number> {
  await rebuildDirectory(args.retainedSkillsDir);

  const retainedSkills = [...args.retainedSkills].sort((left, right) =>
    compareStringsAscending(left.targetName, right.targetName),
  );

  for (const retainedSkill of retainedSkills) {
    await fs.cp(retainedSkill.absolutePath, path.join(args.retainedSkillsDir, retainedSkill.targetName), {
      recursive: true,
    });
  }

  return retainedSkills.length;
}

function toIndexEntry(result: ScreeningResult): ResultIndexEntry {
  return {
    skill_dir: result.skill_dir,
    skill_id: result.skill_id,
    decision: result.decision,
    confidence: result.confidence,
    capability_archetype: result.capability_archetype,
    representativeness: result.representativeness,
    harbor_taskability: result.harbor_taskability,
    drop_reason_category: result.drop_reason_category,
    summary: result.summary,
  };
}

function toBatchIndexEntry(result: ScreeningResult): BatchResultIndexEntry {
  return {
    category_slug: result.category_slug,
    subcategory_slug: result.subcategory_slug,
    ...toIndexEntry(result),
  };
}

function compareConfidenceLevel(left: "low" | "medium" | "high", right: "low" | "medium" | "high"): number {
  const levelWeight = {
    high: 3,
    medium: 2,
    low: 1,
  } as const;

  return levelWeight[right] - levelWeight[left];
}

function sortIndexEntries(entries: ResultIndexEntry[]): ResultIndexEntry[] {
  return [...entries].sort((left, right) => {
    const representativenessDelta = compareConfidenceLevel(left.representativeness, right.representativeness);
    if (representativenessDelta !== 0) {
      return representativenessDelta;
    }
    const taskabilityDelta = compareConfidenceLevel(left.harbor_taskability, right.harbor_taskability);
    if (taskabilityDelta !== 0) {
      return taskabilityDelta;
    }
    return compareStringsAscending(left.skill_dir, right.skill_dir);
  });
}

function sortBatchIndexEntries(entries: BatchResultIndexEntry[]): BatchResultIndexEntry[] {
  return [...entries].sort((left, right) => {
    const representativenessDelta = compareConfidenceLevel(left.representativeness, right.representativeness);
    if (representativenessDelta !== 0) {
      return representativenessDelta;
    }
    const taskabilityDelta = compareConfidenceLevel(left.harbor_taskability, right.harbor_taskability);
    if (taskabilityDelta !== 0) {
      return taskabilityDelta;
    }
    const categoryDelta = compareStringsAscending(left.category_slug, right.category_slug);
    if (categoryDelta !== 0) {
      return categoryDelta;
    }
    const subcategoryDelta = compareStringsAscending(left.subcategory_slug, right.subcategory_slug);
    if (subcategoryDelta !== 0) {
      return subcategoryDelta;
    }
    return compareStringsAscending(left.skill_dir, right.skill_dir);
  });
}

function countDecisions(results: ScreeningResult[]): { keep: number; drop: number } {
  return {
    keep: results.filter((result) => result.decision === "keep").length,
    drop: results.filter((result) => result.decision === "drop").length,
  };
}

function buildArchetypeCounts(results: ScreeningResult[]) {
  const archetypeMap = new Map<string, { total: number; keep: number; drop: number }>();
  for (const result of results) {
    const current = archetypeMap.get(result.capability_archetype) ?? { total: 0, keep: 0, drop: 0 };
    current.total += 1;
    if (result.decision === "keep") {
      current.keep += 1;
    } else {
      current.drop += 1;
    }
    archetypeMap.set(result.capability_archetype, current);
  }

  return Array.from(archetypeMap.entries())
    .map(([capabilityArchetype, counts]) => ({
      capability_archetype: capabilityArchetype,
      total_count: counts.total,
      keep_count: counts.keep,
      drop_count: counts.drop,
    }))
    .sort((left, right) => {
      if (left.total_count !== right.total_count) {
        return compareNumbersDescending(left.total_count, right.total_count);
      }
      return compareStringsAscending(left.capability_archetype, right.capability_archetype);
    });
}

function buildDropReasonCounts(results: ScreeningResult[]) {
  const dropReasonMap = new Map<string, number>();
  for (const result of results) {
    if (result.decision !== "drop") {
      continue;
    }
    const current = dropReasonMap.get(result.drop_reason_category) ?? 0;
    dropReasonMap.set(result.drop_reason_category, current + 1);
  }

  return Array.from(dropReasonMap.entries())
    .map(([name, count]) => ({ name, count }))
    .sort((left, right) => {
      if (left.count !== right.count) {
        return compareNumbersDescending(left.count, right.count);
      }
      return compareStringsAscending(left.name, right.name);
    });
}

function collectRetainedSkillSources(discoveredSkills: DiscoveredSkill[], results: ScreeningResult[]): RetainedSkillSource[] {
  const keptSkillDirectories = new Set(
    results.filter((result) => result.decision === "keep").map((result) => result.skill_dir),
  );

  return discoveredSkills
    .filter((skill) => keptSkillDirectories.has(skill.directoryName))
    .map((skill) => ({
      categorySlug: skill.categorySlug,
      subcategorySlug: skill.subcategorySlug,
      skillDir: skill.directoryName,
      absolutePath: skill.absolutePath,
    }));
}

export function buildSummary(args: {
  subcategoryDir: string;
  outputDir: string;
  discoveredSkills: DiscoveredSkill[];
  results: ScreeningResult[];
  failures: FailureRecord[];
  resumedResults: number;
  retainedSkillsDir: string | null;
  retainedSkillsCount: number;
}): ScreeningSummary {
  const [firstSkill] = args.discoveredSkills;
  const categorySlug = firstSkill?.categorySlug ?? "";
  const subcategorySlug = firstSkill?.subcategorySlug ?? path.basename(args.subcategoryDir);

  const decisionCounts = countDecisions(args.results);
  const keepEntries = sortIndexEntries(args.results.filter((result) => result.decision === "keep").map(toIndexEntry));

  return {
    category_slug: categorySlug,
    subcategory_slug: subcategorySlug,
    subcategory_dir: path.resolve(args.subcategoryDir),
    output_dir: path.resolve(args.outputDir),
    retained_skills_dir: args.retainedSkillsDir ? path.resolve(args.retainedSkillsDir) : null,
    retained_skills_count: args.retainedSkillsCount,
    total_skills_discovered: args.discoveredSkills.length,
    total_results: args.results.length,
    total_failures: args.failures.length,
    resumed_results: args.resumedResults,
    decision_counts: decisionCounts,
    archetype_counts: buildArchetypeCounts(args.results),
    drop_reason_counts: buildDropReasonCounts(args.results),
    high_representativeness_keep_skills: keepEntries.filter((entry) => entry.representativeness === "high"),
    high_harbor_taskability_keep_skills: keepEntries.filter((entry) => entry.harbor_taskability === "high"),
    generated_at: new Date().toISOString(),
  };
}

export function buildBatchSummary(args: {
  inputDir: string;
  outputDir: string;
  discoveredSubcategories: DiscoveredSubcategory[];
  subcategorySummaries: ScreeningSummary[];
  results: ScreeningResult[];
  failures: FailureRecord[];
  resumedResults: number;
  retainedSkillsDir: string;
  retainedSkillsCount: number;
}): BatchScreeningSummary {
  const sortedSubcategorySummaries = [...args.subcategorySummaries].sort((left, right) => {
    const categoryDelta = compareStringsAscending(left.category_slug, right.category_slug);
    if (categoryDelta !== 0) {
      return categoryDelta;
    }
    return compareStringsAscending(left.subcategory_slug, right.subcategory_slug);
  });

  const subcategories: BatchSubcategorySummaryEntry[] = sortedSubcategorySummaries.map((summary) => ({
    category_slug: summary.category_slug,
    subcategory_slug: summary.subcategory_slug,
    subcategory_dir: summary.subcategory_dir,
    output_dir: summary.output_dir,
    total_skills_discovered: summary.total_skills_discovered,
    total_results: summary.total_results,
    total_failures: summary.total_failures,
    resumed_results: summary.resumed_results,
    decision_counts: summary.decision_counts,
  }));

  return {
    input_dir: path.resolve(args.inputDir),
    output_dir: path.resolve(args.outputDir),
    retained_skills_dir: path.resolve(args.retainedSkillsDir),
    retained_skills_count: args.retainedSkillsCount,
    total_subcategories_discovered: args.discoveredSubcategories.length,
    total_subcategories_processed: subcategories.length,
    total_skills_discovered: subcategories.reduce((sum, entry) => sum + entry.total_skills_discovered, 0),
    total_results: args.results.length,
    total_failures: args.failures.length,
    resumed_results: args.resumedResults,
    decision_counts: countDecisions(args.results),
    archetype_counts: buildArchetypeCounts(args.results),
    drop_reason_counts: buildDropReasonCounts(args.results),
    subcategories,
    generated_at: new Date().toISOString(),
  };
}

export async function finalizeRunArtifacts(args: {
  layout: OutputLayout;
  options: SingleRunOptions;
  discoveredSkills: DiscoveredSkill[];
  results: ScreeningResult[];
  failures: FailureRecord[];
  resumedResults: number;
  startedAt: string;
  finishedAt: string;
  promptPath: string;
  schemaPath: string;
  exportRetainedSkills?: boolean;
}): Promise<{ manifest: SingleRunManifest; summary: ScreeningSummary }> {
  const keepIndex = sortIndexEntries(args.results.filter((result) => result.decision === "keep").map(toIndexEntry));
  const dropIndex = sortIndexEntries(args.results.filter((result) => result.decision === "drop").map(toIndexEntry));
  const retainedSkillSources = collectRetainedSkillSources(args.discoveredSkills, args.results);
  const shouldExportRetainedSkills = args.exportRetainedSkills ?? true;
  let retainedSkillsCount = 0;
  if (shouldExportRetainedSkills) {
    retainedSkillsCount = await syncRetainedSkillsDirectory({
      retainedSkillsDir: args.layout.retainedSkillsDir,
      retainedSkills: retainedSkillSources.map((skill) => ({
        absolutePath: skill.absolutePath,
        targetName: sanitizeFileComponent(skill.skillDir),
      })),
    });
  } else {
    await fs.rm(args.layout.retainedSkillsDir, { recursive: true, force: true });
  }

  const summary = buildSummary({
    subcategoryDir: args.options.subcategoryDir,
    outputDir: args.options.outputDir,
    discoveredSkills: args.discoveredSkills,
    results: args.results,
    failures: args.failures,
    resumedResults: args.resumedResults,
    retainedSkillsDir: shouldExportRetainedSkills ? args.layout.retainedSkillsDir : null,
    retainedSkillsCount,
  });

  const manifest: SingleRunManifest = {
    tool_name: "skill_screening_runner",
    version: 1,
    mode: "single",
    started_at: args.startedAt,
    finished_at: args.finishedAt,
    options: {
      subcategory_dir: path.resolve(args.options.subcategoryDir),
      output_dir: path.resolve(args.options.outputDir),
      model: args.options.model ?? process.env.SKILL_SCREENING_MODEL ?? null,
      jobs: args.options.jobs,
      limit: args.options.limit ?? null,
      resume: args.options.resume,
      overwrite: args.options.overwrite,
      prompt_path: args.promptPath,
      schema_path: args.schemaPath,
    },
    counts: {
      discovered: args.discoveredSkills.length,
      results: args.results.length,
      failures: args.failures.length,
      resumed: args.resumedResults,
      retained: retainedSkillsCount,
    },
  };

  await writeJsonFile(args.layout.keepIndexPath, keepIndex);
  await writeJsonFile(args.layout.dropIndexPath, dropIndex);
  await writeJsonFile(args.layout.failuresPath, args.failures);
  await writeJsonFile(args.layout.summaryPath, summary);
  await writeJsonFile(args.layout.manifestPath, manifest);

  return { manifest, summary };
}

export async function finalizeBatchRunArtifacts(args: {
  layout: BatchOutputLayout;
  options: { inputDir: string; outputDir: string; model?: string; jobs: number; limit?: number; resume: boolean; overwrite: boolean };
  discoveredSubcategories: DiscoveredSubcategory[];
  subcategorySummaries: ScreeningSummary[];
  results: ScreeningResult[];
  failures: FailureRecord[];
  resumedResults: number;
  startedAt: string;
  finishedAt: string;
  promptPath: string;
  schemaPath: string;
  retainedSkillSources: RetainedSkillSource[];
}): Promise<{ manifest: BatchRunManifest; summary: BatchScreeningSummary }> {
  const keepIndex = sortBatchIndexEntries(args.results.filter((result) => result.decision === "keep").map(toBatchIndexEntry));
  const dropIndex = sortBatchIndexEntries(args.results.filter((result) => result.decision === "drop").map(toBatchIndexEntry));
  const retainedSkillsCount = await syncRetainedSkillsDirectory({
    retainedSkillsDir: args.layout.retainedSkillsDir,
    retainedSkills: args.retainedSkillSources.map((skill) => ({
      absolutePath: skill.absolutePath,
      targetName: buildBatchRetainedArtifactBaseName(skill),
    })),
  });

  const summary = buildBatchSummary({
    inputDir: args.options.inputDir,
    outputDir: args.options.outputDir,
    discoveredSubcategories: args.discoveredSubcategories,
    subcategorySummaries: args.subcategorySummaries,
    results: args.results,
    failures: args.failures,
    resumedResults: args.resumedResults,
    retainedSkillsDir: args.layout.retainedSkillsDir,
    retainedSkillsCount,
  });

  const manifest: BatchRunManifest = {
    tool_name: "skill_screening_runner",
    version: 1,
    mode: "batch",
    started_at: args.startedAt,
    finished_at: args.finishedAt,
    options: {
      input_dir: path.resolve(args.options.inputDir),
      output_dir: path.resolve(args.options.outputDir),
      model: args.options.model ?? process.env.SKILL_SCREENING_MODEL ?? null,
      jobs: args.options.jobs,
      limit: args.options.limit ?? null,
      resume: args.options.resume,
      overwrite: args.options.overwrite,
      prompt_path: args.promptPath,
      schema_path: args.schemaPath,
    },
    counts: {
      subcategories_discovered: args.discoveredSubcategories.length,
      subcategories_processed: args.subcategorySummaries.length,
      discovered: summary.total_skills_discovered,
      results: args.results.length,
      failures: args.failures.length,
      resumed: args.resumedResults,
      retained: retainedSkillsCount,
    },
  };

  await writeJsonFile(args.layout.keepIndexPath, keepIndex);
  await writeJsonFile(args.layout.dropIndexPath, dropIndex);
  await writeJsonFile(args.layout.failuresPath, args.failures);
  await writeJsonFile(args.layout.summaryPath, summary);
  await writeJsonFile(args.layout.manifestPath, manifest);

  return { manifest, summary };
}
