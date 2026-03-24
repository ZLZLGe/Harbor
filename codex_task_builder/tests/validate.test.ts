import assert from "node:assert/strict";
import os from "node:os";
import path from "node:path";
import { promises as fs } from "node:fs";
import { validateDraftStatic } from "../src/validate.js";
import type { DerivedTaskPlan, WriterSummary } from "../src/schema.js";

const sourceTaskId = "weighted-gdp-calc";

async function makeDraftFixture(plan: DerivedTaskPlan): Promise<string> {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), "codex-validate-test-"));
  await fs.mkdir(path.join(root, "environment", "skills", "xlsx"), { recursive: true });
  await fs.mkdir(path.join(root, "solution"), { recursive: true });
  await fs.mkdir(path.join(root, "tests"), { recursive: true });

  await fs.writeFile(
    path.join(root, "task.toml"),
    `version = "1.0"

[metadata]
id = "${plan.derivedTaskId}"
name = "Transfer | Test Fixture"
description = "Fixture task for validateDraftStatic."
author_name = "Test Author"
author_email = "test@example.com"
difficulty = "${plan.difficulty}"
category = "${plan.category}"
tags = ["xlsx", "fixture"]
primary_output_file = "${plan.primaryOutputFile}"
source_task_id = "${sourceTaskId}"
task_role = "${plan.taskRole}"
`,
    "utf-8",
  );
  await fs.writeFile(path.join(root, "instruction.md"), "fixture\n", "utf-8");
  await fs.writeFile(
    path.join(root, "environment", "Dockerfile"),
    "FROM ubuntu:24.04\nCOPY skills /root/.codex/skills\n",
    "utf-8",
  );
  await fs.writeFile(path.join(root, "solution", "solve.sh"), "#!/bin/bash\n", "utf-8");
  await fs.writeFile(path.join(root, "tests", "test.sh"), "#!/bin/bash\n", "utf-8");
  await fs.writeFile(path.join(root, "tests", "test_outputs.py"), "print('ok')\n", "utf-8");

  return root;
}

async function collectIssues(plan: DerivedTaskPlan, writerPrimaryOutputFile: string): Promise<string[]> {
  const draftDir = await makeDraftFixture(plan);
  const writerSummary: WriterSummary = {
    derivedTaskId: plan.derivedTaskId,
    draftRelativePath: `drafts/${plan.derivedTaskId}`,
    primaryOutputFile: writerPrimaryOutputFile,
    filesWritten: [
      `drafts/${plan.derivedTaskId}/task.toml`,
      `drafts/${plan.derivedTaskId}/instruction.md`,
      `drafts/${plan.derivedTaskId}/environment/Dockerfile`,
      `drafts/${plan.derivedTaskId}/solution/solve.sh`,
      `drafts/${plan.derivedTaskId}/tests/test.sh`,
      `drafts/${plan.derivedTaskId}/tests/test_outputs.py`,
    ],
    summary: "fixture writer summary",
  };

  try {
    const issues = await validateDraftStatic(draftDir, plan, sourceTaskId, writerSummary);
    return issues.map((issue) => issue.message);
  } finally {
    await fs.rm(draftDir, { recursive: true, force: true });
  }
}

const workbookPlan: DerivedTaskPlan = {
  derivedTaskId: "power-fleet-xlsx-transfer-heat-rate",
  taskRole: "transfer",
  title: "Transfer | 发电机组热耗率组合分析",
  goal: "Complete the workbook.",
  primaryOutputFile: "power_fleet_heat_rate.xlsx",
  difficulty: "medium",
  category: "energy-analysis",
  skillBenefitRationale: "Uses xlsx formulas.",
  targetSkillDirName: "xlsx",
  targetSkillName: "xlsx",
};

const rootOutputPlan: DerivedTaskPlan = {
  ...workbookPlan,
  derivedTaskId: "clinic-ops-xlsx-transfer-shift-conflict-audit",
  primaryOutputFile: "/root/clinic_shift_conflicts.json",
};

{
  const issues = await collectIssues(
    workbookPlan,
    "drafts/power-fleet-xlsx-transfer-heat-rate/environment/power_fleet_heat_rate.xlsx",
  );
  assert.ok(!issues.includes("writer 返回的 primaryOutputFile 与 blueprint 不一致"));
}

{
  const issues = await collectIssues(workbookPlan, "power_fleet_heat_rate.xlsx");
  assert.ok(!issues.includes("writer 返回的 primaryOutputFile 与 blueprint 不一致"));
}

{
  const issues = await collectIssues(workbookPlan, "/root/power_fleet_heat_rate.xlsx");
  assert.ok(issues.includes("writer 返回的 primaryOutputFile 与 blueprint 不一致"));
}

{
  const issues = await collectIssues(
    workbookPlan,
    "drafts/power-fleet-xlsx-transfer-heat-rate/task.toml",
  );
  assert.ok(issues.includes("writer 返回的 primaryOutputFile 与 blueprint 不一致"));
}

{
  const issues = await collectIssues(
    rootOutputPlan,
    "drafts/clinic-ops-xlsx-transfer-shift-conflict-audit/environment/clinic_shift_conflicts.json",
  );
  assert.ok(issues.includes("writer 返回的 primaryOutputFile 与 blueprint 不一致"));
}

console.log("validate.test.ts passed");
