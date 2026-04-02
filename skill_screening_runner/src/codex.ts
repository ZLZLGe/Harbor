import { Codex, type ThreadOptions } from "@openai/codex-sdk";
import type { CodexScreeningRun } from "./types.js";
import { screeningResultJsonSchema } from "./schema.js";
import { parseJsonWithFallback } from "./utils.js";

type SkillScreeningCodexClientOptions = {
  model?: string;
};

export class SkillScreeningCodexClient {
  private readonly codex: Codex;
  private readonly threadBaseOptions: ThreadOptions;

  constructor(options: SkillScreeningCodexClientOptions = {}) {
    this.codex = new Codex({
      codexPathOverride: process.env.CODEX_PATH,
    });

    const sandboxMode = "danger-full-access";
    const networkAccessEnabled = process.env.SKILL_SCREENING_NETWORK_ACCESS !== "0";
    const modelReasoningEffort = process.env.SKILL_SCREENING_REASONING_EFFORT === "low" ? "low" : "high";

    this.threadBaseOptions = {
      model: options.model ?? process.env.SKILL_SCREENING_MODEL,
      sandboxMode,
      networkAccessEnabled,
      approvalPolicy: "never",
      skipGitRepoCheck: true,
      modelReasoningEffort,
    };
  }

  async screenSkill(workingDirectory: string, prompt: string): Promise<CodexScreeningRun> {
    const thread = this.codex.startThread({
      ...this.threadBaseOptions,
      workingDirectory,
    });

    const turn = await thread.run(prompt, {
      outputSchema: screeningResultJsonSchema,
    });

    return {
      parsed: parseJsonWithFallback(turn.finalResponse),
      raw: turn.finalResponse,
      threadId: thread.id,
    };
  }
}
