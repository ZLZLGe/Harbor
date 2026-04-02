import { z } from "zod";
import type { DiscoveredSkill } from "./types.js";

const stringArraySchema = z.array(z.string().min(1));

const decisionSchema = z.enum(["keep", "drop"]);
const confidenceSchema = z.enum(["low", "medium", "high"]);
const judgmentSchema = z.enum(["feasible", "risky", "not_feasible"]);
const levelSchema = z.enum(["low", "medium", "high"]);
const dropReasonSchema = z.enum([
  "not_applicable",
  "not_verifiable",
  "container_unfriendly",
  "too_external",
  "too_broad",
  "no_skill_advantage",
  "ops_only",
  "insufficient_signal",
  "unknown",
]);

const feasibilitySchema = z
  .object({
    judgment: judgmentSchema,
    rationale: z.string().min(1),
  })
  .strict();

export const screeningResultSchema = z
  .object({
    category_slug: z.string().min(1),
    subcategory_slug: z.string().min(1),
    skill_dir: z.string().min(1),
    skill_id: z.string().min(1),
    decision: decisionSchema,
    confidence: confidenceSchema,
    summary: z.string().min(1),
    harbor_task_adaptation_summary: z.string().min(1),
    skill_benefit_rationale: z.string().min(1),
    positive_signals: stringArraySchema,
    blocking_issues: stringArraySchema,
    input_synthesis_feasibility: feasibilitySchema,
    container_feasibility: feasibilitySchema,
    files_reviewed: stringArraySchema.min(1),
    uncertainties: stringArraySchema,
    capability_archetype: z.string().min(1),
    representativeness: levelSchema,
    harbor_taskability: levelSchema,
    seed_reuse_signals: stringArraySchema,
    drop_reason_category: dropReasonSchema,
  })
  .strict()
  .superRefine((value, ctx) => {
    if (value.decision === "keep" && value.drop_reason_category !== "not_applicable") {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["drop_reason_category"],
        message: "decision=keep 时 drop_reason_category 必须为 not_applicable",
      });
    }
    if (value.decision === "drop" && value.drop_reason_category === "not_applicable") {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["drop_reason_category"],
        message: "decision=drop 时必须提供具体的 drop_reason_category",
      });
    }
    if (value.decision === "keep" && value.container_feasibility.judgment === "not_feasible") {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["container_feasibility", "judgment"],
        message: "container_feasibility=not_feasible 时不能判为 keep",
      });
    }
    if (value.decision === "drop" && value.container_feasibility.judgment === "not_feasible" && value.drop_reason_category !== "container_unfriendly") {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["drop_reason_category"],
        message: "container_feasibility=not_feasible 时 drop_reason_category 必须为 container_unfriendly",
      });
    }
  });

export type ScreeningResult = z.infer<typeof screeningResultSchema>;

export const screeningResultJsonSchema = {
  type: "object",
  additionalProperties: false,
  required: [
    "category_slug",
    "subcategory_slug",
    "skill_dir",
    "skill_id",
    "decision",
    "confidence",
    "summary",
    "harbor_task_adaptation_summary",
    "skill_benefit_rationale",
    "positive_signals",
    "blocking_issues",
    "input_synthesis_feasibility",
    "container_feasibility",
    "files_reviewed",
    "uncertainties",
    "capability_archetype",
    "representativeness",
    "harbor_taskability",
    "seed_reuse_signals",
    "drop_reason_category",
  ],
  properties: {
    category_slug: { type: "string" },
    subcategory_slug: { type: "string" },
    skill_dir: { type: "string" },
    skill_id: { type: "string" },
    decision: { type: "string", enum: ["keep", "drop"] },
    confidence: { type: "string", enum: ["low", "medium", "high"] },
    summary: { type: "string" },
    harbor_task_adaptation_summary: { type: "string" },
    skill_benefit_rationale: { type: "string" },
    positive_signals: {
      type: "array",
      items: { type: "string" },
    },
    blocking_issues: {
      type: "array",
      items: { type: "string" },
    },
    input_synthesis_feasibility: {
      type: "object",
      additionalProperties: false,
      required: ["judgment", "rationale"],
      properties: {
        judgment: { type: "string", enum: ["feasible", "risky", "not_feasible"] },
        rationale: { type: "string" },
      },
    },
    container_feasibility: {
      type: "object",
      additionalProperties: false,
      required: ["judgment", "rationale"],
      properties: {
        judgment: { type: "string", enum: ["feasible", "risky", "not_feasible"] },
        rationale: { type: "string" },
      },
    },
    files_reviewed: {
      type: "array",
      items: { type: "string" },
    },
    uncertainties: {
      type: "array",
      items: { type: "string" },
    },
    capability_archetype: { type: "string" },
    representativeness: { type: "string", enum: ["low", "medium", "high"] },
    harbor_taskability: { type: "string", enum: ["low", "medium", "high"] },
    seed_reuse_signals: {
      type: "array",
      items: { type: "string" },
    },
    drop_reason_category: {
      type: "string",
      enum: [
        "not_applicable",
        "not_verifiable",
        "container_unfriendly",
        "too_external",
        "too_broad",
        "no_skill_advantage",
        "ops_only",
        "insufficient_signal",
        "unknown",
      ],
    },
  },
} as const;

function normalizeRecord(value: unknown, skill: DiscoveredSkill, allowLegacyContainerFeasibility: boolean): ScreeningResult {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("screening structured output 必须是对象");
  }

  const record = value as Record<string, unknown>;
  const normalized = {
    ...record,
    category_slug: skill.categorySlug,
    subcategory_slug: skill.subcategorySlug,
    skill_dir: skill.directoryName,
    skill_id: skill.skillId,
    container_feasibility:
      record.container_feasibility ??
      (allowLegacyContainerFeasibility
        ? {
            judgment: "risky",
            rationale: "legacy result loaded before container_feasibility was introduced",
          }
        : undefined),
    drop_reason_category:
      typeof record.drop_reason_category === "string"
        ? record.drop_reason_category
        : record.decision === "keep"
          ? "not_applicable"
          : "unknown",
  };

  return screeningResultSchema.parse(normalized);
}

export function normalizeAndValidateScreeningResult(value: unknown, skill: DiscoveredSkill): ScreeningResult {
  return normalizeRecord(value, skill, false);
}

export function normalizeAndValidateLoadedScreeningResult(value: unknown, skill: DiscoveredSkill): ScreeningResult {
  return normalizeRecord(value, skill, true);
}
