import assert from "node:assert/strict";
import { buildTaskWriterPrompt } from "../src/prompts.js";
import type { DerivedTaskPlan } from "../src/schema.js";
import type { GenerationUnit, SourceTask, SkillInfo } from "../src/discovery.js";

const pdfSkill: SkillInfo = {
  name: "PDF",
  dirName: "pdf",
  relativeDir: "pdf",
  skillMdPath: "/tmp/pdf/SKILL.md",
};

const sourceTask: SourceTask = {
  sourceTaskId: "pdf-excel-diff",
  sourceDir: "/tmp/source-task",
  taskTomlPath: "/tmp/source-task/task.toml",
  instructionPath: "/tmp/source-task/instruction.md",
  environmentDir: "/tmp/source-task/environment",
  solutionDir: "/tmp/source-task/solution",
  testsDir: "/tmp/source-task/tests",
  skillsDir: "/tmp/source-task/environment/skills",
  metadata: {
    id: "pdf-excel-diff",
    name: "PDF Excel Diff",
    difficulty: "medium",
    category: "document",
    tags: ["pdf", "diff"],
  },
  skills: [pdfSkill],
};

const unit: GenerationUnit = {
  sourceTask,
  skillMode: "per-skill",
  targetSkill: pdfSkill,
  scopeSlug: "pdf",
  scopeLabel: "PDF",
};

const plan: DerivedTaskPlan = {
  derivedTaskId: "clinic-pdf-similar-form-fill",
  taskRole: "similar",
  title: "Clinic PDF Similar Form Fill",
  goal: "Fill a clinic PDF form from supplied records.",
  primaryOutputFile: "/root/output/filled.pdf",
  difficulty: "medium",
  category: "document",
  skillBenefitRationale: "Requires the PDF skill to inspect and update the form correctly.",
  targetSkillDirName: "pdf",
  targetSkillName: "PDF",
};

const prompt = buildTaskWriterPrompt(unit, plan);

assert.match(prompt, /写作前必须先检查当前 workspace 的 drafts\/ 目录：/);
assert.match(prompt, new RegExp(`把 drafts/${plan.derivedTaskId}/ 视为当前任务目录`));
assert.match(prompt, /把 drafts\/ 下其他已经有内容的 sibling task 目录视为之前已经生成好的任务/);
assert.match(prompt, /优先阅读：[\s\S]*PLAN\.json[\s\S]*instruction\.md[\s\S]*task\.toml/);
assert.match(prompt, /如有必要，再补充检查：[\s\S]*tests\/test_outputs\.py[\s\S]*environment\/ 下的输入资产/);
assert.match(prompt, /任务场景或叙事/);
assert.match(prompt, /输入资产类型、结构或素材来源/);
assert.match(prompt, /输出物的语义目标/);
assert.match(prompt, /测试判定方式/);
assert.match(prompt, /你不能修改 blueprint 中已经固定的核心约束：derivedTaskId、taskRole、primaryOutputFile、source_task_id，以及当前 skill scope/);
assert.match(prompt, /如果 drafts\/ 中还没有其他已生成 sibling tasks，就按正常流程继续写当前任务/);

console.log("prompts.test.ts passed");
