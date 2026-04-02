import test from "node:test";
import assert from "node:assert/strict";
import { buildRunOptionsFromArgv } from "../src/cli.js";

test("buildRunOptionsFromArgv parses single-subcategory mode", () => {
  const options = buildRunOptionsFromArgv([
    "--subcategory-dir",
    "/mnt/e/skill_all/development/backend",
    "--output-dir",
    "/mnt/e/skill_screening_runs/development__backend",
    "--jobs",
    "6",
  ]);

  assert.equal(options.mode, "single");
  assert.equal(options.subcategoryDir, "/mnt/e/skill_all/development/backend");
  assert.equal(options.outputDir, "/mnt/e/skill_screening_runs/development__backend");
  assert.equal(options.jobs, 6);
});

test("buildRunOptionsFromArgv parses batch mode", () => {
  const options = buildRunOptionsFromArgv([
    "--input-dir",
    "/mnt/e/skill_all/development",
    "--output-dir",
    "/mnt/e/skill_screening_runs/development",
    "--limit",
    "3",
    "--resume",
  ]);

  assert.equal(options.mode, "batch");
  assert.equal(options.inputDir, "/mnt/e/skill_all/development");
  assert.equal(options.limit, 3);
  assert.equal(options.resume, true);
});

test("buildRunOptionsFromArgv rejects mixing single and batch inputs", () => {
  assert.throws(
    () =>
      buildRunOptionsFromArgv([
        "--input-dir",
        "/mnt/e/skill_all",
        "--subcategory-dir",
        "/mnt/e/skill_all/development/backend",
        "--output-dir",
        "/mnt/e/skill_screening_runs/all",
      ]),
    /不能同时使用/,
  );
});

test("buildRunOptionsFromArgv requires one input mode", () => {
  assert.throws(
    () =>
      buildRunOptionsFromArgv([
        "--output-dir",
        "/mnt/e/skill_screening_runs/all",
      ]),
    /必须提供 --input-dir 或 --subcategory-dir/,
  );
});
