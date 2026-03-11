import { Codex, type ThreadOptions } from "@openai/codex-sdk";
import type { SourceTask } from "./discovery.js";
import type { DerivedTaskPlan, FamilyPlan, ReviewResult, WriterSummary } from "./schema.js";
import {
  familyPlanJsonSchema,
  familyPlanSchema,
  reviewResultJsonSchema,
  reviewResultSchema,
  writerSummaryJsonSchema,
  writerSummarySchema,
} from "./schema.js";
import { parseJsonWithFallback } from "./utils.js";
import { buildFamilyPlannerPrompt, buildReviewerPrompt, buildTaskWriterPrompt } from "./prompts.js";
import type { FamilyWorkspace } from "./workspace.js";

type StructuredRunResult<T> = {
  data: T;
  threadId: string | null;
  raw: string;
};

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

  async planFamily(sourceTask: SourceTask, workspace: FamilyWorkspace): Promise<StructuredRunResult<FamilyPlan>> {
    const thread = this.makeThread(workspace.rootDir);
    const turn = await thread.run(buildFamilyPlannerPrompt(sourceTask), {
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
    sourceTask: SourceTask,
    workspace: FamilyWorkspace,
    plan: DerivedTaskPlan,
  ): Promise<StructuredRunResult<WriterSummary>> {
    const thread = this.makeThread(workspace.rootDir);
    const turn = await thread.run(buildTaskWriterPrompt(sourceTask, plan), {
      outputSchema: writerSummaryJsonSchema,
    });
    const parsed = writerSummarySchema.parse(parseJsonWithFallback<WriterSummary>(turn.finalResponse));
    return {
      data: parsed,
      threadId: thread.id,
      raw: turn.finalResponse,
    };
  }

  async reviewFamily(
    sourceTask: SourceTask,
    workspace: FamilyWorkspace,
    familyPlan: FamilyPlan,
  ): Promise<StructuredRunResult<ReviewResult>> {
    const thread = this.makeThread(workspace.rootDir);
    const turn = await thread.run(buildReviewerPrompt(sourceTask, familyPlan), {
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
