export type DiscoveredSkill = {
  categorySlug: string;
  subcategorySlug: string;
  directoryName: string;
  skillId: string;
  absolutePath: string;
  relativePath: string;
  rank: number | null;
};

export type DiscoveredSubcategory = {
  categorySlug: string;
  subcategorySlug: string;
  absolutePath: string;
  relativePath: string;
};

export type RetainedSkillSource = {
  categorySlug: string;
  subcategorySlug: string;
  skillDir: string;
  absolutePath: string;
};

export type BaseRunOptions = {
  outputDir: string;
  model?: string;
  jobs: number;
  limit?: number;
  resume: boolean;
  overwrite: boolean;
  promptPath?: string;
  schemaPath?: string;
};

export type SingleRunOptions = BaseRunOptions & {
  mode: "single";
  subcategoryDir: string;
};

export type BatchRunOptions = BaseRunOptions & {
  mode: "batch";
  inputDir: string;
};

export type RunOptions = SingleRunOptions | BatchRunOptions;

export type CodexScreeningRun = {
  parsed: unknown;
  raw: string;
  threadId: string | null;
};

export type FailureRecord = {
  category_slug: string;
  subcategory_slug: string;
  skill_dir: string;
  skill_id: string;
  skill_path: string;
  error: string;
  timestamp: string;
};

export type OutputLayout = {
  rootDir: string;
  skillsDir: string;
  logsDir: string;
  retainedSkillsDir: string;
  manifestPath: string;
  summaryPath: string;
  keepIndexPath: string;
  dropIndexPath: string;
  failuresPath: string;
};

export type BatchOutputLayout = {
  rootDir: string;
  retainedSkillsDir: string;
  manifestPath: string;
  summaryPath: string;
  keepIndexPath: string;
  dropIndexPath: string;
  failuresPath: string;
};

export type ResultIndexEntry = {
  skill_dir: string;
  skill_id: string;
  decision: "keep" | "drop";
  confidence: "low" | "medium" | "high";
  capability_archetype: string;
  representativeness: "low" | "medium" | "high";
  harbor_taskability: "low" | "medium" | "high";
  drop_reason_category:
    | "not_applicable"
    | "not_verifiable"
    | "container_unfriendly"
    | "too_external"
    | "too_broad"
    | "no_skill_advantage"
    | "ops_only"
    | "insufficient_signal"
    | "unknown";
  summary: string;
};

export type BatchResultIndexEntry = ResultIndexEntry & {
  category_slug: string;
  subcategory_slug: string;
};

export type SummaryBucket = {
  name: string;
  count: number;
};

export type ArchetypeBucket = {
  capability_archetype: string;
  total_count: number;
  keep_count: number;
  drop_count: number;
};

export type ScreeningSummary = {
  category_slug: string;
  subcategory_slug: string;
  subcategory_dir: string;
  output_dir: string;
  retained_skills_dir: string | null;
  retained_skills_count: number;
  total_skills_discovered: number;
  total_results: number;
  total_failures: number;
  resumed_results: number;
  decision_counts: {
    keep: number;
    drop: number;
  };
  archetype_counts: ArchetypeBucket[];
  drop_reason_counts: SummaryBucket[];
  high_representativeness_keep_skills: ResultIndexEntry[];
  high_harbor_taskability_keep_skills: ResultIndexEntry[];
  generated_at: string;
};

export type BatchSubcategorySummaryEntry = {
  category_slug: string;
  subcategory_slug: string;
  subcategory_dir: string;
  output_dir: string;
  total_skills_discovered: number;
  total_results: number;
  total_failures: number;
  resumed_results: number;
  decision_counts: {
    keep: number;
    drop: number;
  };
};

export type BatchScreeningSummary = {
  input_dir: string;
  output_dir: string;
  retained_skills_dir: string;
  retained_skills_count: number;
  total_subcategories_discovered: number;
  total_subcategories_processed: number;
  total_skills_discovered: number;
  total_results: number;
  total_failures: number;
  resumed_results: number;
  decision_counts: {
    keep: number;
    drop: number;
  };
  archetype_counts: ArchetypeBucket[];
  drop_reason_counts: SummaryBucket[];
  subcategories: BatchSubcategorySummaryEntry[];
  generated_at: string;
};

export type SingleRunManifest = {
  tool_name: string;
  version: number;
  mode: "single";
  started_at: string;
  finished_at: string;
  options: {
    subcategory_dir: string;
    output_dir: string;
    model: string | null;
    jobs: number;
    limit: number | null;
    resume: boolean;
    overwrite: boolean;
    prompt_path: string;
    schema_path: string;
  };
  counts: {
    discovered: number;
    results: number;
    failures: number;
    resumed: number;
    retained: number;
  };
};

export type BatchRunManifest = {
  tool_name: string;
  version: number;
  mode: "batch";
  started_at: string;
  finished_at: string;
  options: {
    input_dir: string;
    output_dir: string;
    model: string | null;
    jobs: number;
    limit: number | null;
    resume: boolean;
    overwrite: boolean;
    prompt_path: string;
    schema_path: string;
  };
  counts: {
    subcategories_discovered: number;
    subcategories_processed: number;
    discovered: number;
    results: number;
    failures: number;
    resumed: number;
    retained: number;
  };
};

export type RunManifest = SingleRunManifest | BatchRunManifest;

export type RunSummary = ScreeningSummary | BatchScreeningSummary;

export type SkillScreeningRunResult =
  | {
      mode: "single";
      summary: ScreeningSummary;
      manifest: SingleRunManifest;
    }
  | {
      mode: "batch";
      summary: BatchScreeningSummary;
      manifest: BatchRunManifest;
    };
