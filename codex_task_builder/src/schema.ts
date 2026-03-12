import { z } from "zod";

export const taskRoleSchema = z.enum(["similar", "transfer"]);

export const derivedTaskPlanSchema = z.object({
  derivedTaskId: z.string().min(1),
  taskRole: taskRoleSchema,
  title: z.string().min(1),
  goal: z.string().min(1),
  primaryOutputFile: z.string().min(1),
  difficulty: z.string().min(1),
  category: z.string().min(1),
  skillBenefitRationale: z.string().min(1),
});

export const familyPlanSchema = z.object({
  sourceTaskId: z.string().min(1),
  familyTheme: z.string().min(1),
  derivedTasks: z.array(derivedTaskPlanSchema).length(4),
});

export const writerSummarySchema = z.object({
  derivedTaskId: z.string().min(1),
  draftRelativePath: z.string().min(1),
  primaryOutputFile: z.string().min(1),
  filesWritten: z.array(z.string().min(1)).min(1),
  summary: z.string().min(1),
});

export const reviewerTaskResultSchema = z.object({
  derivedTaskId: z.string().min(1),
  pass: z.boolean(),
  issues: z.array(z.string()),
  visibilityPass: z.boolean(),
  skillBenefitPass: z.boolean(),
  testabilityPass: z.boolean(),
});

export const familyObservationsSchema = z.object({
  issues: z.array(z.string()),
  diversityPass: z.boolean(),
  roleLayoutPass: z.boolean(),
});

export const reviewResultSchema = z.object({
  taskResults: z.array(reviewerTaskResultSchema).min(1),
  familyObservations: familyObservationsSchema,
});

export type DerivedTaskPlan = z.infer<typeof derivedTaskPlanSchema>;
export type FamilyPlan = z.infer<typeof familyPlanSchema>;
export type WriterSummary = z.infer<typeof writerSummarySchema>;
export type ReviewerTaskResult = z.infer<typeof reviewerTaskResultSchema>;
export type FamilyObservations = z.infer<typeof familyObservationsSchema>;
export type ReviewResult = z.infer<typeof reviewResultSchema>;

export const familyPlanJsonSchema = {
  type: "object",
  additionalProperties: false,
  required: ["sourceTaskId", "familyTheme", "derivedTasks"],
  properties: {
    sourceTaskId: { type: "string" },
    familyTheme: { type: "string" },
    derivedTasks: {
      type: "array",
      minItems: 4,
      maxItems: 4,
      items: {
        type: "object",
        additionalProperties: false,
        required: [
          "derivedTaskId",
          "taskRole",
          "title",
          "goal",
          "primaryOutputFile",
          "difficulty",
          "category",
          "skillBenefitRationale",
        ],
        properties: {
          derivedTaskId: { type: "string" },
          taskRole: { type: "string", enum: ["similar", "transfer"] },
          title: { type: "string" },
          goal: { type: "string" },
          primaryOutputFile: { type: "string" },
          difficulty: { type: "string" },
          category: { type: "string" },
          skillBenefitRationale: { type: "string" },
        },
      },
    },
  },
} as const;

export const writerSummaryJsonSchema = {
  type: "object",
  additionalProperties: false,
  required: ["derivedTaskId", "draftRelativePath", "primaryOutputFile", "filesWritten", "summary"],
  properties: {
    derivedTaskId: { type: "string" },
    draftRelativePath: { type: "string" },
    primaryOutputFile: { type: "string" },
    filesWritten: {
      type: "array",
      minItems: 1,
      items: { type: "string" },
    },
    summary: { type: "string" },
  },
} as const;

export const reviewResultJsonSchema = {
  type: "object",
  additionalProperties: false,
  required: ["taskResults", "familyObservations"],
  properties: {
    taskResults: {
      type: "array",
      minItems: 1,
      items: {
        type: "object",
        additionalProperties: false,
        required: [
          "derivedTaskId",
          "pass",
          "issues",
          "visibilityPass",
          "skillBenefitPass",
          "testabilityPass",
        ],
        properties: {
          derivedTaskId: { type: "string" },
          pass: { type: "boolean" },
          issues: {
            type: "array",
            items: { type: "string" },
          },
          visibilityPass: { type: "boolean" },
          skillBenefitPass: { type: "boolean" },
          testabilityPass: { type: "boolean" },
        },
      },
    },
    familyObservations: {
      type: "object",
      additionalProperties: false,
      required: ["issues", "diversityPass", "roleLayoutPass"],
      properties: {
        issues: {
          type: "array",
          items: { type: "string" },
        },
        diversityPass: { type: "boolean" },
        roleLayoutPass: { type: "boolean" },
      },
    },
  },
} as const;
