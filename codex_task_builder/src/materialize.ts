import path from "node:path";
import type { DerivedTaskPlan } from "./schema.js";
import type { FamilyWorkspace } from "./workspace.js";
import { INTEGRATED_TASKS_ROOT, copyDir, ensureDir, pathExists } from "./utils.js";

export type PublishedTaskResult = {
  derivedTaskId: string;
  status: "completed" | "skipped-existing-task";
  taskDir: string;
  reason?: string;
};

export type PublishResult = {
  familyDir: string;
  taskResults: PublishedTaskResult[];
};

export async function publishFamily(
  workspace: FamilyWorkspace,
  sourceTaskId: string,
  tasks: DerivedTaskPlan[],
  outputRoot = INTEGRATED_TASKS_ROOT,
): Promise<PublishResult> {
  const familyDir = path.join(outputRoot, sourceTaskId);
  const taskResults: PublishedTaskResult[] = [];

  if (tasks.length === 0) {
    return {
      familyDir,
      taskResults,
    };
  }

  await ensureDir(familyDir);

  for (const task of tasks) {
    const sourceDraftDir = path.join(workspace.draftsDir, task.derivedTaskId);
    const targetTaskDir = path.join(familyDir, task.derivedTaskId);
    if (await pathExists(targetTaskDir)) {
      taskResults.push({
        derivedTaskId: task.derivedTaskId,
        status: "skipped-existing-task",
        taskDir: targetTaskDir,
        reason: "目标任务目录已存在，按配置跳过发布",
      });
      continue;
    }
    await copyDir(sourceDraftDir, targetTaskDir);
    taskResults.push({
      derivedTaskId: task.derivedTaskId,
      status: "completed",
      taskDir: targetTaskDir,
    });
  }

  return {
    familyDir,
    taskResults,
  };
}
