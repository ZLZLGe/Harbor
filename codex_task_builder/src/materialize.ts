import path from "node:path";
import type { FamilyPlan } from "./schema.js";
import type { FamilyWorkspace } from "./workspace.js";
import { INTEGRATED_TASKS_ROOT, copyDir, pathExists } from "./utils.js";

export type PublishResult = {
  published: boolean;
  familyDir: string;
  taskDirs: string[];
  reason?: string;
};

export async function publishFamily(
  workspace: FamilyWorkspace,
  familyPlan: FamilyPlan,
  outputRoot = INTEGRATED_TASKS_ROOT,
): Promise<PublishResult> {
  const familyDir = path.join(outputRoot, familyPlan.sourceTaskId);
  if (await pathExists(familyDir)) {
    return {
      published: false,
      familyDir,
      taskDirs: [],
      reason: "目标 family 目录已存在，按配置跳过发布",
    };
  }

  const publishedTaskDirs: string[] = [];
  for (const task of familyPlan.derivedTasks) {
    const sourceDraftDir = path.join(workspace.draftsDir, task.derivedTaskId);
    const targetTaskDir = path.join(familyDir, task.derivedTaskId);
    await copyDir(sourceDraftDir, targetTaskDir);
    publishedTaskDirs.push(targetTaskDir);
  }

  return {
    published: true,
    familyDir,
    taskDirs: publishedTaskDirs,
  };
}
