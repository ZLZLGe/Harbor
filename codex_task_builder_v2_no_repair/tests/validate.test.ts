import assert from "node:assert/strict";
import os from "node:os";
import path from "node:path";
import { promises as fs } from "node:fs";
import { normalizeReviewResultFromRaw } from "../src/codex.js";
import type { GenerationUnit, SkillInfo, SourceTask } from "../src/discovery.js";
import { inspectPublishedFamily, selectExecutableUnits } from "../src/published.js";
import { flattenFamilyPlan, type DerivedTaskPlan, type FamilyPlan } from "../src/schema.js";
import { runStreamingCommand } from "../src/utils.js";
import { sanitizeAndCopyTask } from "../src/materialize.js";
import {
  buildHarborRuntimeCommand,
  resolveRuntimeEnvironment,
  runRuntimePreflight,
  validateDockerfileBaseImages,
  validateDraftStatic,
  validateFamilyPlan,
  validateTaskPlans,
} from "../src/validate.js";

const sourceTaskId = "weighted-gdp-calc";
const xlsxSkill: SkillInfo = {
  name: "XLSX",
  dirName: "xlsx",
  relativeDir: "xlsx",
  skillMdPath: "/tmp/source-task/environment/skills/xlsx/SKILL.md",
};
const pythonSkill: SkillInfo = {
  name: "Python",
  dirName: "python",
  relativeDir: "python",
  skillMdPath: "/tmp/source-task/environment/skills/python/SKILL.md",
};
const perSkillSourceTask: SourceTask = {
  sourceTaskId,
  sourceDir: "/tmp/source-task",
  taskTomlPath: "/tmp/source-task/task.toml",
  instructionPath: "/tmp/source-task/instruction.md",
  environmentDir: "/tmp/source-task/environment",
  solutionDir: "/tmp/source-task/solution",
  testsDir: "/tmp/source-task/tests",
  skillsDir: "/tmp/source-task/environment/skills",
  metadata: {
    id: sourceTaskId,
    name: "Weighted GDP Calc",
    difficulty: "medium",
    category: "energy-analysis",
    tags: ["xlsx", "analysis"],
  },
  skills: [xlsxSkill],
};
const allSkillSourceTask: SourceTask = {
  ...perSkillSourceTask,
  skills: [xlsxSkill, pythonSkill],
};
const perSkillUnit: GenerationUnit = {
  sourceTask: perSkillSourceTask,
  skillMode: "per-skill",
  targetSkill: xlsxSkill,
  scopeSlug: "xlsx",
  scopeLabel: "XLSX",
  similarCount: 1,
  transferCount: 1,
  pendingSimilarOrdinals: [1],
  pendingTransferOrdinals: [1],
  finalFamilyDir: "/tmp/final/weighted-gdp-calc/xlsx",
  publishedTasks: [],
};
const allSkillUnit: GenerationUnit = {
  sourceTask: allSkillSourceTask,
  skillMode: "all",
  targetSkill: null,
  scopeSlug: "all-skills",
  scopeLabel: "All skills",
  similarCount: 1,
  transferCount: 1,
  pendingSimilarOrdinals: [1],
  pendingTransferOrdinals: [1],
  finalFamilyDir: "/tmp/final/weighted-gdp-calc/all-skills",
  publishedTasks: [],
};

async function makeDraftFixture(
  plan: DerivedTaskPlan,
  options: {
    withPlanJson?: boolean;
    dockerfile?: string;
    metadataName?: string;
    metadataDescription?: string;
    instructionText?: string;
    skillDirNames?: string[];
    solveSh?: string;
    testSh?: string;
    testOutputsPy?: string;
    extraFiles?: Record<string, string>;
  } = {},
): Promise<string> {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), "codex-validate-test-"));
  for (const skillDirName of options.skillDirNames ?? ["xlsx"]) {
    await fs.mkdir(path.join(root, "environment", "skills", skillDirName), { recursive: true });
  }
  await fs.mkdir(path.join(root, "solution"), { recursive: true });
  await fs.mkdir(path.join(root, "tests"), { recursive: true });

  if (options.withPlanJson !== false) {
    await fs.writeFile(path.join(root, "plan.json"), `${JSON.stringify(plan, null, 2)}\n`, "utf-8");
  }

  await fs.writeFile(
    path.join(root, "task.toml"),
    `version = "1.0"

[metadata]
id = "${plan.derivedTaskId}"
name = "${options.metadataName ?? "Transfer 1 | Test Fixture"}"
description = "${options.metadataDescription ?? "Fixture task for validateDraftStatic."}"
author_name = "Test Author"
author_email = "test@example.com"
difficulty = "${plan.difficulty}"
category = "${plan.category}"
tags = ["xlsx", "fixture"]
primary_output_file = "${plan.primaryOutputFile}"
source_task_id = "${sourceTaskId}"
task_role = "${plan.taskRole}"

[environment]
cpus = 2
memory_mb = 2048
storage_mb = 5120
gpus = 0
`,
    "utf-8",
  );
  await fs.writeFile(path.join(root, "instruction.md"), options.instructionText ?? "fixture\n", "utf-8");
  await fs.writeFile(
    path.join(root, "environment", "Dockerfile"),
    options.dockerfile ?? "FROM ubuntu:24.04\nWORKDIR /root\nCOPY skills /root/.codex/skills\n",
    "utf-8",
  );
  await fs.writeFile(path.join(root, "solution", "solve.sh"), options.solveSh ?? "#!/bin/bash\n", "utf-8");
  await fs.writeFile(path.join(root, "tests", "test.sh"), options.testSh ?? "#!/bin/bash\n", "utf-8");
  await fs.writeFile(path.join(root, "tests", "test_outputs.py"), options.testOutputsPy ?? "print('ok')\n", "utf-8");
  for (const [relativePath, content] of Object.entries(options.extraFiles ?? {})) {
    const fullPath = path.join(root, relativePath);
    await fs.mkdir(path.dirname(fullPath), { recursive: true });
    await fs.writeFile(fullPath, content, "utf-8");
  }

  return root;
}

async function collectStaticIssueMessages(
  unit: GenerationUnit,
  plan: DerivedTaskPlan,
  options: {
    withPlanJson?: boolean;
    dockerfile?: string;
    metadataName?: string;
    metadataDescription?: string;
    instructionText?: string;
    skillDirNames?: string[];
    solveSh?: string;
    testSh?: string;
    testOutputsPy?: string;
    extraFiles?: Record<string, string>;
  } = {},
): Promise<string[]> {
  const draftDir = await makeDraftFixture(plan, options);
  try {
    const issues = await validateDraftStatic(draftDir, plan, unit);
    return issues.map((issue) => issue.message);
  } finally {
    await fs.rm(draftDir, { recursive: true, force: true });
  }
}

const plan: DerivedTaskPlan = {
  derivedTaskId: "transfer1",
  taskRole: "transfer",
  roleOrdinal: 1,
  title: "Transfer 1 | 发电机组热耗率组合分析",
  goal: "Complete the workbook.",
  primaryOutputFile: "power_fleet_heat_rate.xlsx",
  difficulty: "medium",
  category: "energy-analysis",
  skillBenefitRationale: "Uses xlsx formulas.",
  sourceTaskId,
  skillMode: "per-skill",
  targetSkillDirName: "xlsx",
  targetSkillName: "XLSX",
};
const allModePlan: DerivedTaskPlan = {
  ...plan,
  derivedTaskId: "similar1",
  taskRole: "similar",
  roleOrdinal: 1,
  title: "Similar 1",
  primaryOutputFile: "all-skills-output.txt",
  skillMode: "all",
  targetSkillDirName: "",
  targetSkillName: "",
};

const reviewTaskPlans: DerivedTaskPlan[] = [
  {
    ...plan,
    derivedTaskId: "similar1",
    taskRole: "similar",
    roleOrdinal: 1,
    title: "Similar 1",
    primaryOutputFile: "similar1.xlsx",
  },
  {
    ...plan,
    derivedTaskId: "transfer1",
    taskRole: "transfer",
    roleOrdinal: 1,
    title: "Transfer 1",
    primaryOutputFile: "transfer1.xlsx",
  },
];

{
  const familyPlan: FamilyPlan = {
    sourceTaskId,
    skillMode: "per-skill",
    targetSkillDirName: "xlsx",
    targetSkillName: "XLSX",
    familyTheme: "Energy workbook tasks",
    similarTasks: [
      {
        title: "Similar 1",
        goal: "A",
        primaryOutputFile: "similar1.xlsx",
        difficulty: "medium",
        category: "energy-analysis",
        skillBenefitRationale: "A",
      },
    ],
    transferTasks: [
      {
        title: "Transfer 1",
        goal: "B",
        primaryOutputFile: "transfer1.xlsx",
        difficulty: "medium",
        category: "energy-analysis",
        skillBenefitRationale: "B",
      },
      {
        title: "Transfer 2",
        goal: "C",
        primaryOutputFile: "transfer2.xlsx",
        difficulty: "medium",
        category: "energy-analysis",
        skillBenefitRationale: "C",
      },
    ],
  };

  assert.deepEqual(
    validateFamilyPlan(familyPlan, {
      sourceTaskId,
      skillMode: "per-skill",
      similarCount: 1,
      transferCount: 2,
      targetSkillDirName: "xlsx",
      targetSkillName: "XLSX",
    }),
    [],
  );

  const taskPlans = flattenFamilyPlan(familyPlan);
  assert.equal(taskPlans[0]?.derivedTaskId, "similar1");
  assert.equal(taskPlans[1]?.derivedTaskId, "transfer1");
  assert.deepEqual(validateTaskPlans(taskPlans, { similarOrdinals: [1], transferOrdinals: [1, 2] }), []);

  const brokenPlans = [...taskPlans];
  brokenPlans[0] = { ...brokenPlans[0], derivedTaskId: "custom-similar" };
  assert.match(
    validateTaskPlans(brokenPlans, { similarOrdinals: [1], transferOrdinals: [1, 2] })[0]?.message ?? "",
    /similar1/,
  );

  const partialTaskPlans = flattenFamilyPlan(familyPlan, {
    similarOrdinals: [2],
    transferOrdinals: [1, 3],
  });
  assert.equal(partialTaskPlans[0]?.derivedTaskId, "similar2");
  assert.equal(partialTaskPlans[1]?.derivedTaskId, "transfer1");
  assert.equal(partialTaskPlans[2]?.derivedTaskId, "transfer3");
  assert.deepEqual(validateTaskPlans(partialTaskPlans, { similarOrdinals: [2], transferOrdinals: [1, 3] }), []);
}

{
  const issues = await collectStaticIssueMessages(perSkillUnit, plan);
  assert.ok(!issues.includes("缺少必备文件: plan.json"));
}

{
  const issues = await collectStaticIssueMessages(perSkillUnit, plan, { withPlanJson: false });
  assert.ok(issues.includes("缺少必备文件: plan.json"));
}

{
  const issues = await collectStaticIssueMessages(perSkillUnit, plan, { metadataName: "Transfer 1 | 中文任务" });
  assert.ok(issues.includes("task.toml metadata.name 必须使用英文描述，不能包含中文"));
}

{
  const issues = await collectStaticIssueMessages(perSkillUnit, plan, { metadataDescription: "这里是中文描述" });
  assert.ok(issues.includes("task.toml metadata.description 必须使用英文描述，不能包含中文"));
}

{
  const issues = await collectStaticIssueMessages(perSkillUnit, plan, { instructionText: "请完成这个任务。\n" });
  assert.ok(issues.includes("instruction.md 必须使用英文描述，不能包含中文"));
}

{
  const issues = await collectStaticIssueMessages(perSkillUnit, plan, {
    dockerfile: "FROM ubuntu:24.04\nCOPY skills /root/.codex/skills\n",
  });
  assert.ok(issues.includes("environment/Dockerfile 必须显式声明 WORKDIR"));
}

{
  const issues = await collectStaticIssueMessages(perSkillUnit, plan, {
    dockerfile: "FROM ubuntu:24.04\nWORKDIR /app/workspace\nCOPY skills /root/.codex/skills\n",
  });
  assert.ok(!issues.includes("environment/Dockerfile 必须显式声明 WORKDIR"));
}

{
  const issues = await collectStaticIssueMessages(perSkillUnit, plan, {
    dockerfile: "FROM ubuntu:24.04\nWORKDIR /root\nCOPY . /root\nCOPY skills /root/.codex/skills\n",
  });
  assert.ok(
    issues.includes("environment/Dockerfile 存在宽泛 COPY/ADD，会把整个 environment/ 上下文一并带入容器，属于实验污染"),
  );
}

{
  const issues = await collectStaticIssueMessages(perSkillUnit, plan, {
    dockerfile: "FROM ubuntu:24.04\nWORKDIR /root\nCOPY . /root/\nCOPY skills /root/.codex/skills\n",
  });
  assert.ok(
    issues.includes("environment/Dockerfile 存在宽泛 COPY/ADD，会把整个 environment/ 上下文一并带入容器，属于实验污染"),
  );
}

{
  const issues = await collectStaticIssueMessages(perSkillUnit, plan, {
    dockerfile: "FROM ubuntu:24.04\nWORKDIR /root\nADD . /root\nCOPY skills /root/.codex/skills\n",
  });
  assert.ok(
    issues.includes("environment/Dockerfile 存在宽泛 COPY/ADD，会把整个 environment/ 上下文一并带入容器，属于实验污染"),
  );
}

{
  const issues = await collectStaticIssueMessages(perSkillUnit, plan, {
    dockerfile:
      "FROM ubuntu:24.04\nWORKDIR /root\nCOPY --chown=root:root . /root\nCOPY skills /root/.codex/skills\n",
  });
  assert.ok(
    issues.includes("environment/Dockerfile 存在宽泛 COPY/ADD，会把整个 environment/ 上下文一并带入容器，属于实验污染"),
  );
}

{
  const issues = await collectStaticIssueMessages(perSkillUnit, plan, {
    dockerfile:
      "FROM ubuntu:24.04\nWORKDIR /root\nCOPY skills /root/environment/skills\nCOPY skills /root/.codex/skills\n",
  });
  assert.ok(
    issues.includes(
      "environment/Dockerfile 把 skills 复制到了普通运行时路径 /root/environment/skills；这会把 skill 内容暴露到非 agent skill 路径，破坏有技能/无技能对照",
    ),
  );
}

{
  const issues = await collectStaticIssueMessages(perSkillUnit, plan, {
    dockerfile: "FROM ubuntu:24.04\nWORKDIR /root\nCOPY skills /app/skills\nCOPY skills /root/.codex/skills\n",
  });
  assert.ok(
    issues.includes(
      "environment/Dockerfile 把 skills 复制到了普通运行时路径 /app/skills；这会把 skill 内容暴露到非 agent skill 路径，破坏有技能/无技能对照",
    ),
  );
}

{
  const issues = await collectStaticIssueMessages(perSkillUnit, plan, {
    dockerfile:
      "FROM ubuntu:24.04\nWORKDIR /root\nCOPY skills /root/.claude/skills\nCOPY skills /root/.codex/skills\n",
  });
  assert.ok(!issues.some((issue) => issue.includes("普通运行时路径")));
}

{
  const issues = await collectStaticIssueMessages(perSkillUnit, plan, { skillDirNames: ["python"] });
  assert.ok(issues.includes("environment/skills 缺少预期 skill 目录: xlsx"));
  assert.ok(issues.includes("environment/skills 存在非预期 skill 目录: python"));
}

{
  const issues = await collectStaticIssueMessages(allSkillUnit, allModePlan, { skillDirNames: ["xlsx"] });
  assert.ok(issues.includes("environment/skills 缺少预期 skill 目录: python"));
}

{
  const issues = await collectStaticIssueMessages(allSkillUnit, allModePlan, {
    skillDirNames: ["xlsx", "python", "rogue"],
  });
  assert.ok(issues.includes("environment/skills 存在非预期 skill 目录: rogue"));
}

{
  const issues = await collectStaticIssueMessages(perSkillUnit, plan, {
    solveSh: '#!/bin/bash\npython3 /root/.codex/skills/xlsx/recalc.py /tmp/output.xlsx\n',
  });
  assert.ok(
    issues.some((issue) => issue.startsWith("solution/solve.sh 直接依赖 skill 模块或路径（")),
  );
}

{
  const issues = await collectStaticIssueMessages(perSkillUnit, plan, {
    testOutputsPy: 'import sys\nsys.path.insert(0, "/app/skills/xlsx/scripts")\nprint("ok")\n',
  });
  assert.ok(
    issues.some((issue) => issue.startsWith("tests/test_outputs.py 直接依赖 skill 模块或路径（")),
  );
}

{
  const issues = await collectStaticIssueMessages(perSkillUnit, plan, {
    extraFiles: {
      [path.join("solution", "helper.py")]: 'import sys\nsys.path.insert(0, "/app/skills/xlsx/scripts")\n',
    },
  });
  assert.ok(
    issues.some((issue) => issue.startsWith("solution/helper.py 直接依赖 skill 模块或路径（")),
  );
}

{
  const issues = await collectStaticIssueMessages(perSkillUnit, plan, {
    extraFiles: {
      [path.join("tests", "helpers", "skill_loader.py")]: 'import sys\nsys.path.insert(0, "/app/skills/xlsx/scripts")\n',
    },
  });
  assert.ok(
    issues.some((issue) => issue.startsWith("tests/helpers/skill_loader.py 直接依赖 skill 模块或路径（")),
  );
}

{
  const normalized = normalizeReviewResultFromRaw(
    reviewTaskPlans,
    JSON.stringify({
      taskResults: [
        {
          pass: false,
          issues: ["instruction must be in English"],
          testabilityPass: false,
        },
        {
          derivedTaskId: "transfer1",
          pass: true,
          issues: [],
        },
      ],
      familyObservations: ["family note"],
    }),
  );
  assert.equal(normalized.taskResults[0]?.derivedTaskId, "similar1");
  assert.equal(normalized.taskResults[0]?.visibilityPass, false);
  assert.equal(normalized.taskResults[1]?.derivedTaskId, "transfer1");
  assert.equal(normalized.taskResults[1]?.skillBenefitPass, true);
  assert.equal(normalized.familyObservations.diversityPass, false);
  assert.ok(
    normalized.familyObservations.issues.some((issue) => issue.includes("familyObservations 返回成数组")),
  );
}

{
  const normalized = normalizeReviewResultFromRaw(reviewTaskPlans, "not-json");
  assert.equal(normalized.taskResults.length, reviewTaskPlans.length);
  assert.ok(normalized.taskResults.every((taskResult) => taskResult.pass === false));
  assert.equal(normalized.familyObservations.diversityPass, false);
}

assert.deepEqual(validateDockerfileBaseImages("FROM ubuntu:24.04\n"), []);
assert.deepEqual(validateDockerfileBaseImages("FROM ghcr.io/acme/demo:latest\n"), []);
assert.deepEqual(validateDockerfileBaseImages("FROM scratch\n"), []);
assert.ok(
  validateDockerfileBaseImages("FROM localhost:5000/private/demo:latest\n").some((issue) =>
    issue.includes("私有或本地 registry"),
  ),
);
assert.ok(
  validateDockerfileBaseImages("FROM registry.internal/demo:latest\n").some((issue) =>
    issue.includes("私有或本地 registry"),
  ),
);

{
  let heartbeatCount = 0;
  const result = await runStreamingCommand("bash", ["-lc", "sleep 0.08; echo ok"], {
    heartbeatIntervalMs: 10,
    onHeartbeat: () => {
      heartbeatCount += 1;
    },
  });
  assert.equal(result.code, 0);
  assert.match(result.stdout, /ok/);
  assert.ok(heartbeatCount > 0);
}

assert.equal(resolveRuntimeEnvironment({}), "daytona");
assert.equal(resolveRuntimeEnvironment({ CODEX_TASK_BUILDER_RUNTIME_ENV: "docker" }), "docker");
assert.equal(resolveRuntimeEnvironment({ CODEX_TASK_BUILDER_RUNTIME_ENV: "DAYTONA" }), "daytona");
assert.throws(
  () => resolveRuntimeEnvironment({ CODEX_TASK_BUILDER_RUNTIME_ENV: "modal" }),
  /CODEX_TASK_BUILDER_RUNTIME_ENV/,
);

{
  const command = buildHarborRuntimeCommand({
    taskDir: "/tmp/task",
    logsDir: "/tmp/logs",
    jobName: "job-1",
    runtimeEnvironment: "daytona",
  });
  assert.deepEqual(command, [
    "harbor",
    "run",
    "-p",
    "/tmp/task",
    "-a",
    "oracle",
    "-e",
    "daytona",
    "--force-build",
    "--jobs-dir",
    "/tmp/logs",
    "--job-name",
    "job-1",
  ]);
}

{
  const sourceDraftDir = await makeDraftFixture(plan);
  const rawRoot = await fs.mkdtemp(path.join(os.tmpdir(), "codex-materialize-raw-"));
  const finalRoot = await fs.mkdtemp(path.join(os.tmpdir(), "codex-materialize-final-"));
  const sourceTaskIdForMaterialize = "fixture-source-task";
  const scopeSlug = "xlsx";
  const taskName = "transfer1";
  const managedDraftDir = path.join(rawRoot, sourceTaskIdForMaterialize, scopeSlug, taskName);

  await fs.mkdir(path.dirname(managedDraftDir), { recursive: true });
  await fs.rename(sourceDraftDir, managedDraftDir);
  await fs.mkdir(path.join(managedDraftDir, "artifacts"), { recursive: true });
  await fs.writeFile(path.join(managedDraftDir, "artifacts", "debug.log"), "debug\n", "utf-8");
  await fs.writeFile(path.join(managedDraftDir, "notes.txt"), "scratch\n", "utf-8");

  try {
    const firstPublish = await sanitizeAndCopyTask({
      sourceDraftDir: managedDraftDir,
      sourceTaskId: sourceTaskIdForMaterialize,
      scopeSlug,
      taskName,
      rawRoot,
      targetRoot: finalRoot,
    });
    const targetDir = firstPublish.targetTaskDir;
    assert.equal(firstPublish.disposition, "created");

    assert.ok(await fs.stat(path.join(targetDir, "plan.json")));
    assert.ok(await fs.stat(path.join(targetDir, "environment")));
    await assert.rejects(fs.stat(path.join(targetDir, "artifacts", "debug.log")));
    await assert.rejects(fs.stat(path.join(targetDir, "notes.txt")));
    const secondPublish = await sanitizeAndCopyTask({
      sourceDraftDir: managedDraftDir,
      sourceTaskId: sourceTaskIdForMaterialize,
      scopeSlug,
      taskName,
      rawRoot,
      targetRoot: finalRoot,
    });
    assert.equal(secondPublish.disposition, "existing");
    assert.equal(secondPublish.targetTaskDir, targetDir);
  } finally {
    await fs.rm(rawRoot, { recursive: true, force: true });
    await fs.rm(finalRoot, { recursive: true, force: true });
  }
}

{
  const finalRoot = await fs.mkdtemp(path.join(os.tmpdir(), "codex-published-final-"));
  const finalFamilyDir = path.join(finalRoot, sourceTaskId, "xlsx");
  await fs.mkdir(path.join(finalFamilyDir, "similar1"), { recursive: true });
  await fs.mkdir(path.join(finalFamilyDir, "transfer2"), { recursive: true });

  try {
    const state = await inspectPublishedFamily(
      {
        sourceTask: {
          sourceTaskId,
          sourceDir: "/tmp/source",
          taskTomlPath: "/tmp/source/task.toml",
          instructionPath: "/tmp/source/instruction.md",
          environmentDir: "/tmp/source/environment",
          solutionDir: "/tmp/source/solution",
          testsDir: "/tmp/source/tests",
          skillsDir: "/tmp/source/environment/skills",
          metadata: { tags: [] },
          skills: [],
        },
        scopeSlug: "xlsx",
        similarCount: 2,
        transferCount: 2,
      },
      finalRoot,
    );
    assert.equal(state.finalFamilyDir, finalFamilyDir);
    assert.deepEqual(
      state.publishedTasks.map((task) => task.derivedTaskId),
      ["similar1", "transfer2"],
    );
    assert.deepEqual(state.pendingSimilarOrdinals, [2]);
    assert.deepEqual(state.pendingTransferOrdinals, [1]);
  } finally {
    await fs.rm(finalRoot, { recursive: true, force: true });
  }
}

{
  const selected = selectExecutableUnits([
    {
      pendingSimilarOrdinals: [],
      pendingTransferOrdinals: [],
    },
    {
      pendingSimilarOrdinals: [1],
      pendingTransferOrdinals: [],
    },
    {
      pendingSimilarOrdinals: [],
      pendingTransferOrdinals: [2],
    },
  ]);
  assert.equal(selected.skippedCount, 1);
  assert.equal(selected.executableUnits.length, 2);

  const limited = selectExecutableUnits(
    [
      {
        pendingSimilarOrdinals: [],
        pendingTransferOrdinals: [],
      },
      {
        pendingSimilarOrdinals: [1],
        pendingTransferOrdinals: [],
      },
      {
        pendingSimilarOrdinals: [],
        pendingTransferOrdinals: [2],
      },
    ],
    1,
  );
  assert.equal(limited.skippedCount, 1);
  assert.equal(limited.executableUnits.length, 1);
}

{
  const harborOnlyRunner = async (command: string, args: string[]) => {
    if (command === "bash" && args[1] === "command -v harbor >/dev/null 2>&1") {
      return { code: 0, stdout: "", stderr: "" };
    }
    if (command === "bash" && args[1] === "harbor --version") {
      return { code: 0, stdout: "harbor 0.0.0\n", stderr: "" };
    }
    throw new Error(`Unexpected command: ${command} ${args.join(" ")}`);
  };

  const preflight = await runRuntimePreflight("daytona", {}, harborOnlyRunner);
  assert.equal(preflight.ok, false);
  assert.match(preflight.summary, /DAYTONA_API_KEY/);
}

{
  const dockerRunner = async (command: string, args: string[]) => {
    if (command === "bash" && args[1] === "command -v harbor >/dev/null 2>&1") {
      return { code: 0, stdout: "", stderr: "" };
    }
    if (command === "bash" && args[1] === "harbor --version") {
      return { code: 0, stdout: "harbor 0.0.0\n", stderr: "" };
    }
    if (command === "bash" && args[1] === "command -v docker >/dev/null 2>&1") {
      return { code: 0, stdout: "", stderr: "" };
    }
    if (command === "docker" && args[0] === "info") {
      return { code: 0, stdout: "docker info ok\n", stderr: "" };
    }
    throw new Error(`Unexpected command: ${command} ${args.join(" ")}`);
  };

  const preflight = await runRuntimePreflight("docker", {}, dockerRunner);
  assert.equal(preflight.ok, true);
  assert.match(preflight.summary, /harbor \+ docker preflight 通过/);
}

console.log("validate.test.ts passed");
