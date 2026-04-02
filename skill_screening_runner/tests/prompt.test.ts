import test from "node:test";
import assert from "node:assert/strict";
import { buildScreeningPrompt } from "../src/prompt.js";
import type { DiscoveredSkill } from "../src/types.js";

const skill: DiscoveredSkill = {
  categorySlug: "development",
  subcategorySlug: "backend",
  directoryName: "01__alpha-skill",
  skillId: "alpha-skill",
  absolutePath: "/tmp/fake/01__alpha-skill",
  relativePath: "development/backend/01__alpha-skill",
  rank: 1,
};

test("buildScreeningPrompt includes autonomous local exploration instructions", async () => {
  const prompt = await buildScreeningPrompt({ skill });
  assert.match(prompt, /先递归探索目标目录/);
  assert.match(prompt, /允许联网/);
  assert.match(prompt, /不要执行任何删除操作/);
  assert.match(prompt, /字段名必须保持 schema 中定义的英文 key/);
  assert.match(prompt, /结构化枚举值必须保持 schema 规定的英文合法值/);
  assert.match(prompt, /其余解释性文本必须使用简体中文/);
  assert.match(prompt, /容器环境/);
  assert.match(prompt, /container_feasibility/);
  assert.match(prompt, /GUI|宿主机特权/);
  assert.match(prompt, /capability_archetype.*英文 slug/);
  assert.match(prompt, /target_skill_dir: `\/tmp\/fake\/01__alpha-skill`/);
  assert.ok(!prompt.includes("{{SNAPSHOT_NOTES}}"));
  assert.ok(!prompt.includes("{{DIRECTORY_TREE}}"));
  assert.ok(!prompt.includes("{{FOCUS_FILES}}"));
});
