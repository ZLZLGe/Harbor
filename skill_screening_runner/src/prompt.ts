import { promises as fs } from "node:fs";
import path from "node:path";
import type { DiscoveredSkill } from "./types.js";
import { MODULE_ROOT } from "./utils.js";

export const DEFAULT_PROMPT_PATH = path.join(MODULE_ROOT, "assets", "single-skill-screening-prompt.md");
export const DEFAULT_SCHEMA_PATH = path.join(MODULE_ROOT, "assets", "output-schema.json");

const DEFAULT_HARBOR_SKILL_PATH = "/home/levi/.codex/skills/harbor/SKILL.md";
const DEFAULT_HARBOR_TASK_FORMAT_PATH = "/home/levi/.codex/skills/harbor/references/task-format.md";
const DEFAULT_BUILDER_PROMPTS_PATH = "/home/levi/Harbor/codex_task_builder_v3/src/prompts.ts";

type BuildPromptArgs = {
  skill: DiscoveredSkill;
  promptPath?: string;
  schemaPath?: string;
};

function replacePlaceholders(template: string, values: Record<string, string>): string {
  return template.replace(/\{\{([A-Z0-9_]+)\}\}/g, (_match, key: string) => values[key] ?? "");
}

export async function buildScreeningPrompt(args: BuildPromptArgs): Promise<string> {
  const promptTemplatePath = path.resolve(args.promptPath ?? DEFAULT_PROMPT_PATH);
  const schemaPath = path.resolve(args.schemaPath ?? DEFAULT_SCHEMA_PATH);
  const template = await fs.readFile(promptTemplatePath, "utf8");

  return replacePlaceholders(template, {
    CATEGORY_SLUG: args.skill.categorySlug,
    SUBCATEGORY_SLUG: args.skill.subcategorySlug,
    SKILL_DIR_NAME: args.skill.directoryName,
    SKILL_ID: args.skill.skillId,
    TARGET_SKILL_DIR: args.skill.absolutePath,
    OUTPUT_SCHEMA_PATH: schemaPath,
    HARBOR_SKILL_PATH: DEFAULT_HARBOR_SKILL_PATH,
    HARBOR_TASK_FORMAT_PATH: DEFAULT_HARBOR_TASK_FORMAT_PATH,
    BUILDER_PROMPTS_PATH: DEFAULT_BUILDER_PROMPTS_PATH,
  });
}
