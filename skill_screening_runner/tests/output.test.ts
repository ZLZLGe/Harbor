import test from "node:test";
import assert from "node:assert/strict";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import {
  buildBatchSummary,
  buildSummary,
  finalizeBatchRunArtifacts,
  finalizeRunArtifacts,
  loadExistingResult,
  prepareBatchOutputLayout,
  prepareOutputLayout,
} from "../src/output.js";
import type { DiscoveredSkill, DiscoveredSubcategory, FailureRecord, RetainedSkillSource } from "../src/types.js";
import type { ScreeningResult } from "../src/schema.js";

const discoveredSkills: DiscoveredSkill[] = [
  {
    categorySlug: "development",
    subcategorySlug: "backend",
    directoryName: "01__alpha-skill",
    skillId: "alpha-skill",
    absolutePath: "/tmp/fake/01__alpha-skill",
    relativePath: "development/backend/01__alpha-skill",
    rank: 1,
  },
  {
    categorySlug: "development",
    subcategorySlug: "backend",
    directoryName: "02__beta-skill",
    skillId: "beta-skill",
    absolutePath: "/tmp/fake/02__beta-skill",
    relativePath: "development/backend/02__beta-skill",
    rank: 2,
  },
];

const results: ScreeningResult[] = [
  {
    category_slug: "development",
    subcategory_slug: "backend",
    skill_dir: "01__alpha-skill",
    skill_id: "alpha-skill",
    decision: "keep",
    confidence: "high",
    summary: "good fit",
    harbor_task_adaptation_summary: "taskable",
    skill_benefit_rationale: "adds structure",
    positive_signals: ["clear workflow"],
    blocking_issues: [],
    input_synthesis_feasibility: {
      judgment: "feasible",
      rationale: "inputs can be synthesized",
    },
    container_feasibility: {
      judgment: "feasible",
      rationale: "fits a standard containerized Harbor task",
    },
    files_reviewed: ["SKILL.md"],
    uncertainties: [],
    capability_archetype: "backend_patterns",
    representativeness: "high",
    harbor_taskability: "high",
    seed_reuse_signals: ["report_json", "workflow_checklist"],
    drop_reason_category: "not_applicable",
  },
  {
    category_slug: "development",
    subcategory_slug: "backend",
    skill_dir: "02__beta-skill",
    skill_id: "beta-skill",
    decision: "drop",
    confidence: "medium",
    summary: "too broad",
    harbor_task_adaptation_summary: "hard to bound",
    skill_benefit_rationale: "theme only",
    positive_signals: [],
    blocking_issues: ["task scope too broad"],
    input_synthesis_feasibility: {
      judgment: "risky",
      rationale: "would need heavy invention",
    },
    container_feasibility: {
      judgment: "risky",
      rationale: "would require careful isolation of external integrations",
    },
    files_reviewed: ["README.md"],
    uncertainties: ["repo is sparse"],
    capability_archetype: "backend_patterns",
    representativeness: "low",
    harbor_taskability: "low",
    seed_reuse_signals: [],
    drop_reason_category: "too_broad",
  },
];

const failures: FailureRecord[] = [];

const discoveredSubcategories: DiscoveredSubcategory[] = [
  {
    categorySlug: "development",
    subcategorySlug: "backend",
    absolutePath: "/mnt/e/skill_all/development/backend",
    relativePath: "development/backend",
  },
  {
    categorySlug: "tools",
    subcategorySlug: "cli-tools",
    absolutePath: "/mnt/e/skill_all/tools/cli-tools",
    relativePath: "tools/cli-tools",
  },
];

async function makeSingleFixture(): Promise<{
  rootDir: string;
  discoveredSkills: DiscoveredSkill[];
}> {
  const rootDir = await fs.mkdtemp(path.join(os.tmpdir(), "skill-screening-output-"));
  const sourceDir = path.join(rootDir, "source", "development", "backend");
  const alphaDir = path.join(sourceDir, "01__alpha-skill");
  const betaDir = path.join(sourceDir, "02__beta-skill");

  await fs.mkdir(alphaDir, { recursive: true });
  await fs.mkdir(betaDir, { recursive: true });
  await fs.writeFile(path.join(alphaDir, "SKILL.md"), "# alpha\n", "utf8");
  await fs.writeFile(path.join(betaDir, "README.md"), "beta\n", "utf8");

  return {
    rootDir,
    discoveredSkills: [
      {
        ...discoveredSkills[0]!,
        absolutePath: alphaDir,
      },
      {
        ...discoveredSkills[1]!,
        absolutePath: betaDir,
      },
    ],
  };
}

test("buildSummary aggregates counts and high-signal keep lists", () => {
  const summary = buildSummary({
    subcategoryDir: "/mnt/e/skill_all/development/backend",
    outputDir: "/mnt/e/skill_screening_runs/development__backend",
    discoveredSkills,
    results,
    failures,
    resumedResults: 1,
    retainedSkillsDir: "/mnt/e/skill_screening_runs/development__backend/retained_skills",
    retainedSkillsCount: 1,
  });

  assert.equal(summary.decision_counts.keep, 1);
  assert.equal(summary.decision_counts.drop, 1);
  assert.equal(summary.retained_skills_count, 1);
  assert.equal(summary.archetype_counts[0]?.capability_archetype, "backend_patterns");
  assert.equal(summary.drop_reason_counts[0]?.name, "too_broad");
  assert.equal(summary.high_representativeness_keep_skills.length, 1);
  assert.equal(summary.high_harbor_taskability_keep_skills.length, 1);
});

test("buildBatchSummary aggregates across multiple subcategories", () => {
  const secondaryResults: ScreeningResult[] = [
    {
      category_slug: "tools",
      subcategory_slug: "cli-tools",
      skill_dir: "01__cli-skill",
      skill_id: "cli-skill",
      decision: "keep",
      confidence: "medium",
      summary: "good cli fit",
      harbor_task_adaptation_summary: "taskable",
      skill_benefit_rationale: "adds cli structure",
      positive_signals: ["explicit commands"],
      blocking_issues: [],
      input_synthesis_feasibility: {
        judgment: "feasible",
        rationale: "easy to synthesize",
      },
      container_feasibility: {
        judgment: "feasible",
        rationale: "the task can run entirely inside a container",
      },
      files_reviewed: ["README.md"],
      uncertainties: [],
      capability_archetype: "cli_workflows",
      representativeness: "medium",
      harbor_taskability: "high",
      seed_reuse_signals: ["command_sequences"],
      drop_reason_category: "not_applicable",
    },
  ];

  const backendSummary = buildSummary({
    subcategoryDir: "/mnt/e/skill_all/development/backend",
    outputDir: "/mnt/e/skill_screening_runs/development__backend",
    discoveredSkills,
    results,
    failures,
    resumedResults: 1,
    retainedSkillsDir: null,
    retainedSkillsCount: 0,
  });

  const cliSummary = buildSummary({
    subcategoryDir: "/mnt/e/skill_all/tools/cli-tools",
    outputDir: "/mnt/e/skill_screening_runs/tools__cli-tools",
    discoveredSkills: [
      {
        categorySlug: "tools",
        subcategorySlug: "cli-tools",
        directoryName: "01__cli-skill",
        skillId: "cli-skill",
        absolutePath: "/tmp/fake-cli/01__cli-skill",
        relativePath: "tools/cli-tools/01__cli-skill",
        rank: 1,
      },
    ],
    results: secondaryResults,
    failures,
    resumedResults: 0,
    retainedSkillsDir: null,
    retainedSkillsCount: 0,
  });

  const batchSummary = buildBatchSummary({
    inputDir: "/mnt/e/skill_all",
    outputDir: "/mnt/e/skill_screening_runs/all",
    discoveredSubcategories,
    subcategorySummaries: [cliSummary, backendSummary],
    results: [...results, ...secondaryResults],
    failures,
    resumedResults: 1,
    retainedSkillsDir: "/mnt/e/skill_screening_runs/all/retained_skills",
    retainedSkillsCount: 2,
  });

  assert.equal(batchSummary.retained_skills_count, 2);
  assert.equal(batchSummary.total_subcategories_discovered, 2);
  assert.equal(batchSummary.total_subcategories_processed, 2);
  assert.equal(batchSummary.total_results, 3);
  assert.equal(batchSummary.decision_counts.keep, 2);
  assert.equal(batchSummary.decision_counts.drop, 1);
  assert.equal(batchSummary.subcategories[0]?.category_slug, "development");
  assert.equal(batchSummary.subcategories[1]?.subcategory_slug, "cli-tools");
});

test("finalizeRunArtifacts copies kept skills into retained_skills and rebuilds the directory", async (t) => {
  const fixture = await makeSingleFixture();
  t.after(async () => {
    await fs.rm(fixture.rootDir, { recursive: true, force: true });
  });

  const outputDir = path.join(fixture.rootDir, "run");
  const layout = await prepareOutputLayout(outputDir, false);
  await fs.mkdir(path.join(layout.retainedSkillsDir, "stale-skill"), { recursive: true });
  await fs.writeFile(path.join(layout.retainedSkillsDir, "stale-skill", "old.txt"), "stale\n", "utf8");

  const finalized = await finalizeRunArtifacts({
    layout,
    options: {
      mode: "single",
      subcategoryDir: path.join(fixture.rootDir, "source", "development", "backend"),
      outputDir,
      jobs: 1,
      resume: false,
      overwrite: false,
    },
    discoveredSkills: fixture.discoveredSkills,
    results,
    failures,
    resumedResults: 0,
    startedAt: "2026-01-01T00:00:00.000Z",
    finishedAt: "2026-01-01T00:05:00.000Z",
    promptPath: "/tmp/prompt.md",
    schemaPath: "/tmp/schema.json",
  });

  await assert.rejects(
    async () => fs.access(path.join(layout.retainedSkillsDir, "stale-skill")),
    /ENOENT/,
  );
  const retainedSkillPath = path.join(layout.retainedSkillsDir, "01__alpha-skill", "SKILL.md");
  const retainedText = await fs.readFile(retainedSkillPath, "utf8");
  assert.match(retainedText, /alpha/);
  await assert.rejects(
    async () => fs.access(path.join(layout.retainedSkillsDir, "02__beta-skill")),
    /ENOENT/,
  );
  assert.equal(finalized.summary.retained_skills_count, 1);
  assert.equal(finalized.summary.retained_skills_dir, layout.retainedSkillsDir);
  assert.equal(finalized.manifest.counts.retained, 1);
});

test("loadExistingResult backfills container feasibility for legacy result files", async (t) => {
  const fixture = await makeSingleFixture();
  t.after(async () => {
    await fs.rm(fixture.rootDir, { recursive: true, force: true });
  });

  const outputDir = path.join(fixture.rootDir, "legacy-run");
  const layout = await prepareOutputLayout(outputDir, false);
  await fs.writeFile(
    path.join(layout.skillsDir, "01__alpha-skill.json"),
    `${JSON.stringify({
      decision: "keep",
      confidence: "high",
      summary: "legacy keep",
      harbor_task_adaptation_summary: "legacy",
      skill_benefit_rationale: "legacy",
      positive_signals: ["signal"],
      blocking_issues: [],
      input_synthesis_feasibility: {
        judgment: "feasible",
        rationale: "legacy",
      },
      files_reviewed: ["SKILL.md"],
      uncertainties: [],
      capability_archetype: "backend_patterns",
      representativeness: "high",
      harbor_taskability: "high",
      seed_reuse_signals: ["pattern"],
      drop_reason_category: "not_applicable",
    }, null, 2)}\n`,
    "utf8",
  );

  const loaded = await loadExistingResult(layout, fixture.discoveredSkills[0]!);
  assert.ok(loaded);
  assert.equal(loaded?.container_feasibility.judgment, "risky");
});

test("finalizeBatchRunArtifacts copies retained skills into a single deduplicated root directory", async (t) => {
  const rootDir = await fs.mkdtemp(path.join(os.tmpdir(), "skill-screening-batch-output-"));
  t.after(async () => {
    await fs.rm(rootDir, { recursive: true, force: true });
  });

  const backendSource = path.join(rootDir, "source", "development", "backend", "03__api-design");
  const frontendSource = path.join(rootDir, "source", "development", "frontend", "03__api-design");
  await fs.mkdir(backendSource, { recursive: true });
  await fs.mkdir(frontendSource, { recursive: true });
  await fs.writeFile(path.join(backendSource, "SKILL.md"), "backend api\n", "utf8");
  await fs.writeFile(path.join(frontendSource, "SKILL.md"), "frontend api\n", "utf8");

  const batchLayout = await prepareBatchOutputLayout(path.join(rootDir, "batch-run"), false);
  const retainedSkillSources: RetainedSkillSource[] = [
    {
      categorySlug: "development",
      subcategorySlug: "backend",
      skillDir: "03__api-design",
      absolutePath: backendSource,
    },
    {
      categorySlug: "development",
      subcategorySlug: "frontend",
      skillDir: "03__api-design",
      absolutePath: frontendSource,
    },
  ];

  const backendSummary = buildSummary({
    subcategoryDir: "/mnt/e/skill_all/development/backend",
    outputDir: path.join(batchLayout.rootDir, "development__backend"),
    discoveredSkills: [
      {
        categorySlug: "development",
        subcategorySlug: "backend",
        directoryName: "03__api-design",
        skillId: "api-design",
        absolutePath: backendSource,
        relativePath: "development/backend/03__api-design",
        rank: 3,
      },
    ],
    results: [
      {
        ...results[0]!,
        skill_dir: "03__api-design",
        skill_id: "api-design",
      },
    ],
    failures,
    resumedResults: 0,
    retainedSkillsDir: null,
    retainedSkillsCount: 0,
  });

  const frontendSummary = buildSummary({
    subcategoryDir: "/mnt/e/skill_all/development/frontend",
    outputDir: path.join(batchLayout.rootDir, "development__frontend"),
    discoveredSkills: [
      {
        categorySlug: "development",
        subcategorySlug: "frontend",
        directoryName: "03__api-design",
        skillId: "api-design",
        absolutePath: frontendSource,
        relativePath: "development/frontend/03__api-design",
        rank: 3,
      },
    ],
    results: [
      {
        ...results[0]!,
        subcategory_slug: "frontend",
        skill_dir: "03__api-design",
        skill_id: "api-design",
      },
    ],
    failures,
    resumedResults: 0,
    retainedSkillsDir: null,
    retainedSkillsCount: 0,
  });

  const finalized = await finalizeBatchRunArtifacts({
    layout: batchLayout,
    options: {
      inputDir: "/mnt/e/skill_all/development",
      outputDir: batchLayout.rootDir,
      jobs: 2,
      resume: false,
      overwrite: false,
    },
    discoveredSubcategories: [
      {
        categorySlug: "development",
        subcategorySlug: "backend",
        absolutePath: "/mnt/e/skill_all/development/backend",
        relativePath: "development/backend",
      },
      {
        categorySlug: "development",
        subcategorySlug: "frontend",
        absolutePath: "/mnt/e/skill_all/development/frontend",
        relativePath: "development/frontend",
      },
    ],
    subcategorySummaries: [backendSummary, frontendSummary],
    results: [
      {
        ...results[0]!,
        skill_dir: "03__api-design",
        skill_id: "api-design",
      },
      {
        ...results[0]!,
        subcategory_slug: "frontend",
        skill_dir: "03__api-design",
        skill_id: "api-design",
      },
    ],
    failures,
    resumedResults: 0,
    startedAt: "2026-01-01T00:00:00.000Z",
    finishedAt: "2026-01-01T00:10:00.000Z",
    promptPath: "/tmp/prompt.md",
    schemaPath: "/tmp/schema.json",
    retainedSkillSources,
  });

  const backendCopy = await fs.readFile(
    path.join(batchLayout.retainedSkillsDir, "development__backend__03__api-design", "SKILL.md"),
    "utf8",
  );
  const frontendCopy = await fs.readFile(
    path.join(batchLayout.retainedSkillsDir, "development__frontend__03__api-design", "SKILL.md"),
    "utf8",
  );
  assert.match(backendCopy, /backend api/);
  assert.match(frontendCopy, /frontend api/);
  assert.equal(finalized.summary.retained_skills_count, 2);
  assert.equal(finalized.summary.retained_skills_dir, batchLayout.retainedSkillsDir);
  assert.equal(finalized.manifest.counts.retained, 2);
});
