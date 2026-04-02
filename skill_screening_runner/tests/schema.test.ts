import test from "node:test";
import assert from "node:assert/strict";
import { normalizeAndValidateLoadedScreeningResult, normalizeAndValidateScreeningResult } from "../src/schema.js";
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

test("normalizeAndValidateScreeningResult injects stable path metadata", () => {
  const result = normalizeAndValidateScreeningResult(
    {
      decision: "keep",
      confidence: "high",
      summary: "good fit",
      harbor_task_adaptation_summary: "taskable",
      skill_benefit_rationale: "useful",
      positive_signals: ["signal"],
      blocking_issues: [],
      input_synthesis_feasibility: {
        judgment: "feasible",
        rationale: "inputs can be synthesized",
      },
      container_feasibility: {
        judgment: "feasible",
        rationale: "works in a standard container",
      },
      files_reviewed: ["SKILL.md"],
      uncertainties: [],
      capability_archetype: "api_design",
      representativeness: "high",
      harbor_taskability: "high",
      seed_reuse_signals: ["json_output"],
      drop_reason_category: "not_applicable",
    },
    skill,
  );

  assert.equal(result.category_slug, "development");
  assert.equal(result.subcategory_slug, "backend");
  assert.equal(result.skill_dir, "01__alpha-skill");
  assert.equal(result.skill_id, "alpha-skill");
});

test("normalizeAndValidateScreeningResult rejects invalid drop reason for keep", () => {
  assert.throws(() => {
    normalizeAndValidateScreeningResult(
      {
        decision: "keep",
        confidence: "high",
        summary: "bad",
        harbor_task_adaptation_summary: "bad",
        skill_benefit_rationale: "bad",
        positive_signals: [],
        blocking_issues: [],
        input_synthesis_feasibility: {
          judgment: "feasible",
          rationale: "ok",
        },
        container_feasibility: {
          judgment: "feasible",
          rationale: "ok",
        },
        files_reviewed: ["SKILL.md"],
        uncertainties: [],
        capability_archetype: "api_design",
        representativeness: "high",
        harbor_taskability: "high",
        seed_reuse_signals: [],
        drop_reason_category: "too_broad",
      },
      skill,
    );
  });
});

test("normalizeAndValidateScreeningResult rejects keep when container feasibility is not feasible", () => {
  assert.throws(() => {
    normalizeAndValidateScreeningResult(
      {
        decision: "keep",
        confidence: "medium",
        summary: "bad",
        harbor_task_adaptation_summary: "bad",
        skill_benefit_rationale: "bad",
        positive_signals: [],
        blocking_issues: ["requires host privileges"],
        input_synthesis_feasibility: {
          judgment: "feasible",
          rationale: "inputs can be synthesized",
        },
        container_feasibility: {
          judgment: "not_feasible",
          rationale: "requires a GUI session and host-level systemd",
        },
        files_reviewed: ["SKILL.md"],
        uncertainties: [],
        capability_archetype: "host_bound_ops",
        representativeness: "low",
        harbor_taskability: "low",
        seed_reuse_signals: [],
        drop_reason_category: "not_applicable",
      },
      skill,
    );
  }, /container_feasibility=not_feasible 时不能判为 keep/);
});

test("normalizeAndValidateLoadedScreeningResult backfills legacy container feasibility for old results", () => {
  const result = normalizeAndValidateLoadedScreeningResult(
    {
      decision: "keep",
      confidence: "high",
      summary: "legacy",
      harbor_task_adaptation_summary: "legacy",
      skill_benefit_rationale: "legacy",
      positive_signals: ["signal"],
      blocking_issues: [],
      input_synthesis_feasibility: {
        judgment: "feasible",
        rationale: "legacy",
      },
      files_reviewed: ["SKILL.md"],
      uncertainties: [],
      capability_archetype: "api_design",
      representativeness: "high",
      harbor_taskability: "high",
      seed_reuse_signals: ["json_output"],
      drop_reason_category: "not_applicable",
    },
    skill,
  );

  assert.equal(result.container_feasibility.judgment, "risky");
  assert.match(result.container_feasibility.rationale, /legacy result loaded before container_feasibility was introduced/);
});
