import test from "node:test";
import assert from "node:assert/strict";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { discoverSkills, discoverSubcategories } from "../src/discovery.js";

const FIXTURE_SUBCATEGORY_DIR = path.resolve("test_fixtures/development/backend");

async function createBatchFixture(): Promise<{
  rootDir: string;
  categoryDir: string;
  subcategoryDir: string;
}> {
  const rootDir = await fs.mkdtemp(path.join(os.tmpdir(), "skill-screening-discovery-"));
  const categoryDir = path.join(rootDir, "development");
  const subcategoryDir = path.join(categoryDir, "backend");

  await fs.mkdir(path.join(subcategoryDir, "01__alpha-skill"), { recursive: true });
  await fs.mkdir(path.join(categoryDir, "frontend", "01__ui-skill"), { recursive: true });
  await fs.mkdir(path.join(rootDir, "tools", "cli-tools", "01__cli-skill"), { recursive: true });

  await fs.writeFile(path.join(subcategoryDir, "01__alpha-skill", "SKILL.md"), "# alpha\n", "utf8");
  await fs.writeFile(path.join(categoryDir, "frontend", "01__ui-skill", "README.md"), "frontend\n", "utf8");
  await fs.writeFile(path.join(rootDir, "tools", "cli-tools", "01__cli-skill", "README.md"), "cli\n", "utf8");

  return {
    rootDir,
    categoryDir,
    subcategoryDir,
  };
}

test("discoverSkills returns direct child skill directories with parsed metadata", async () => {
  const skills = await discoverSkills(FIXTURE_SUBCATEGORY_DIR);
  assert.equal(skills.length, 2);
  assert.equal(skills[0]?.categorySlug, "development");
  assert.equal(skills[0]?.subcategorySlug, "backend");
  assert.equal(skills[0]?.directoryName, "01__alpha-skill");
  assert.equal(skills[0]?.skillId, "alpha-skill");
  assert.equal(skills[0]?.rank, 1);
});

test("discoverSubcategories accepts the root skill directory", async (t) => {
  const fixture = await createBatchFixture();
  t.after(async () => {
    await fs.rm(fixture.rootDir, { recursive: true, force: true });
  });

  const subcategories = await discoverSubcategories(fixture.rootDir);
  assert.deepEqual(
    subcategories.map((entry) => entry.relativePath),
    ["development/backend", "development/frontend", "tools/cli-tools"],
  );
});

test("discoverSubcategories accepts a single category directory", async (t) => {
  const fixture = await createBatchFixture();
  t.after(async () => {
    await fs.rm(fixture.rootDir, { recursive: true, force: true });
  });

  const subcategories = await discoverSubcategories(fixture.categoryDir);
  assert.deepEqual(
    subcategories.map((entry) => entry.relativePath),
    ["development/backend", "development/frontend"],
  );
});

test("discoverSubcategories rejects a subcategory directory", async (t) => {
  const fixture = await createBatchFixture();
  t.after(async () => {
    await fs.rm(fixture.rootDir, { recursive: true, force: true });
  });

  await assert.rejects(async () => discoverSubcategories(fixture.subcategoryDir), /请改用 --subcategory-dir/);
});
