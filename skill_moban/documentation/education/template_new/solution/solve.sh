#!/usr/bin/env bash
set -euo pipefail

mkdir -p /outputs/lesson_skill

if ! curl -fsS http://127.0.0.1:8080/health >/dev/null 2>&1; then
  python /opt/knowledge_service.py >/tmp/knowledge_service.log 2>&1 &
  sleep 0.3
fi

cat > /outputs/lesson_skill/SKILL.md <<'EOF'
---
name: course-publishing-contract-review
description: Use when an educational release needs a reusable evidence-backed review across course metadata, learner-facing assets, accessibility artifacts, and assessments.
---

# Course Publishing Contract Review

Use this skill to capture and apply durable lessons from course-production incidents where a release looked technically complete but the learner-facing course experience was inconsistent. The goal is to convert incident evidence into a repeatable review workflow that future curriculum, documentation, and education agents can use across courses.

## When to Use

- Use this skill when a course, lesson, or module release has conflicting metadata, captions, transcripts, assessment rubrics, review comments, or publishing status.
- Use it when CI logs show green file checks but skipped parity, contract, or learner-facing validation jobs.
- Use it when reviewer comments indicate that learning objectives, prerequisites, LMS ordering, accessibility artifacts, or quiz expectations may have drifted apart.
- Use it when the learning is multi-step and evidence-driven enough to deserve a standalone skill rather than a short repository instruction.

## Evidence Reviewed

- `/workspace/session_bundle/tickets/TCK-1842.json`: learner support reported that the module order, caption wording, transcript, and quiz rubric sent conflicting instructions to learners.
- `/workspace/session_bundle/reviews/reviewer_notes.md`: the reviewer identified that course metadata, learner-facing assets, accessibility artifacts, reviewer comments, and assessment rubrics must be treated as a linked publishing contract.
- `/workspace/session_bundle/logs/publish_ci.log`: the release passed asset and JSON checks, but `contract-crosscheck` and `caption-transcript-diff` were skipped during the emergency release.
- `/workspace/session_bundle/metadata/lms_snapshot.json`: LMS metadata showed the published module order and an old rubric criterion that no longer matched the current learning objective.
- `/workspace/session_bundle/metadata/course_contract.json`: the contract required prerequisite order, caption/transcript parity, rubric alignment, and accessibility review before publishing.
- `/workspace/session_bundle/style_guides/course_quality_playbook.md`: the playbook says to use a standalone skill when a future agent needs a multi-step process with evidence gathering, decision points, and examples.
- `/workspace/session_bundle/repository_inventory.json`: the repository inventory showed existing instructions for short learnings and narrower course-quality or video-accessibility skills that do not cover this distinct publishing-contract capture workflow.
- `/workspace/environment/skills/update-skills/SKILL.md`: the provided process skill defines the skill-vs-instruction-vs-learning decision workflow, the requirement to check existing files, and the quality check to avoid duplication.
- `http://127.0.0.1:8080/incidents/TCK-1842`: the local incident API confirmed skipped CI warnings and the need to capture a reusable linked-contract review.
- `http://127.0.0.1:8080/courses/BIO-201/contract`: the local course API confirmed module ordering drift, caption/transcript risk, and rubric/objective mismatch.
- `http://127.0.0.1:8080/repository/inventory`: the local repository inventory API confirmed why adding a brief learning or updating an existing narrow skill would duplicate or misplace the new workflow.

## Procedure

1. Identify the current learner-facing contract before editing content: collect course metadata, lesson/module order, learning objectives, prerequisites, captions, transcripts, assessment prompts, rubrics, reviewer comments, style guide rules, and CI logs.
2. Compare the release artifacts against that contract. Cross-check LMS metadata with prerequisite order, transcript text with caption text, rubric criteria with learning objectives, and accessibility status with the actual parity checks.
3. When CI is green, inspect warnings and skipped jobs before trusting the release. If a contract, caption-transcript, accessibility, or rubric alignment check was skipped, document it as unresolved evidence rather than treating the pipeline as approval.
4. Validate the incident through at least one direct file source and one service or manifest source when a local knowledge API is available. Use the API to confirm that file-level observations are not stale snapshots.
5. Check existing skills and instructions before creating a new capture. If an existing instruction only holds short learnings, or an existing skill covers only asset checklists or video accessibility, document why this publishing-contract workflow is distinct and avoid duplicating their scope.
6. Decide whether to add a learning to an existing instruction, update an existing skill, create a new instruction, or create a new skill. Use a skill when the prevention path needs evidence gathering, ordered checks, decision points, and examples; use a short instruction only for a small automatic rule.
7. Document the reusable workflow in terms of course, lesson, module, assessment, rubric, transcript, caption, metadata, LMS, publishing, review, and accessibility concepts. Keep ticket IDs and build IDs in evidence notes, not in the general procedure.
8. Verify the final capture against future transfer scenarios before saving it: a video lesson caption/transcript mismatch, a quiz rubric drifting from learning objectives, and LMS module metadata contradicting prerequisite order.

## Quality Checks

- Evidence check: every important claim should cite a real ticket, review note, CI log, metadata file, style guide, or local API endpoint.
- Generality check: the skill name, description, procedure, quality checks, and example should help future courses and modules, not just one ticket, course ID, build ID, or exact file path.
- Specificity check: the procedure should include concrete actions such as identify, compare, cross-check, validate, document, update, and verify.
- Decision check: explain why a standalone skill is warranted when the learning requires a multi-step workflow; explain why a one-line instruction or patch note would be too weak.
- Duplication check: confirm the capture does not belong as a brief learning in an existing instruction and does not duplicate an existing narrower skill.
- Transfer check: confirm that the workflow covers at least two future education scenarios, such as caption/transcript mismatch, assessment rubric drift from learning objectives, or LMS metadata publishing drift.
- Guardrail check: never replace the real publishing chain with a fake summary, delete input evidence, modify provided skills, or bypass local service validation.

## Example

Wrong:

"Remember to check the captions next time." This is too narrow because it ignores course metadata, publishing order, assessment alignment, accessibility review, and the evidence trail that explains why the release failed.

Corrected:

"Before publishing a lesson or module, compare LMS metadata and prerequisite order with learner-facing media, transcript and caption parity, current learning objectives, assessment prompts, quiz rubrics, reviewer comments, and CI warnings. If any artifact disagrees with the course contract, document the evidence and resolve the mismatch before release." This version transfers to video lessons, quiz updates, localized courses, and accessibility reviews.
EOF

cat > /outputs/capture_report.json <<'EOF'
{
  "decision": "skill",
  "skill_name": "course-publishing-contract-review",
  "incident_summary": "A course release passed basic asset checks but shipped with inconsistent LMS ordering, caption and transcript wording, and quiz rubric alignment. Learners saw conflicting instructions because the release was reviewed as separate files instead of one learner-facing publishing contract.",
  "root_cause": "The release owner trusted green CI status even though contract cross-check and caption-transcript diff jobs were skipped. The team lacked a reusable workflow for comparing course metadata, accessibility artifacts, assessments, reviewer comments, and learning objectives before publishing.",
  "evidence": [
    {
      "source": "/workspace/session_bundle/tickets/TCK-1842.json",
      "finding": "Learner support reported conflicting module order, caption wording, transcript wording, and quiz rubric expectations."
    },
    {
      "source": "/workspace/session_bundle/reviews/reviewer_notes.md",
      "finding": "The reviewer recommended treating metadata, learner-facing assets, accessibility artifacts, reviewer comments, and rubrics as a linked publishing contract."
    },
    {
      "source": "/workspace/session_bundle/logs/publish_ci.log",
      "finding": "The publish pipeline passed asset checks while contract-crosscheck and caption-transcript-diff were skipped."
    },
    {
      "source": "/workspace/session_bundle/metadata/lms_snapshot.json",
      "finding": "The LMS snapshot showed module ordering drift and an old rubric criterion for the published lesson."
    },
    {
      "source": "/workspace/session_bundle/metadata/course_contract.json",
      "finding": "The course contract required prerequisite order, caption transcript parity, rubric alignment, and accessibility review."
    },
    {
      "source": "/workspace/session_bundle/style_guides/course_quality_playbook.md",
      "finding": "The playbook says standalone skills are appropriate for multi-step processes with evidence gathering, decision points, and examples."
    },
    {
      "source": "/workspace/session_bundle/repository_inventory.json",
      "finding": "The repository inventory showed existing instructions for short learnings and narrower course-quality or video-accessibility skills that would not own this distinct publishing-contract workflow."
    },
    {
      "source": "/workspace/environment/skills/update-skills/SKILL.md",
      "finding": "The provided process skill requires checking existing skills and instructions, choosing between learning, instruction, and skill capture, and avoiding duplicated knowledge."
    },
    {
      "source": "http://127.0.0.1:8080/incidents/TCK-1842",
      "finding": "The incident API confirmed skipped CI warnings and recommended capturing a reusable linked course publishing contract review."
    },
    {
      "source": "http://127.0.0.1:8080/courses/BIO-201/contract",
      "finding": "The course contract API confirmed module order drift, caption transcript risk, and rubric mismatch."
    },
    {
      "source": "http://127.0.0.1:8080/repository/inventory",
      "finding": "The repository inventory API confirmed the distinction between adding a brief learning, updating a narrow existing skill, and creating a new multi-step skill."
    }
  ],
  "reusable_principles": [
    "Treat course metadata, learner-facing assets, accessibility artifacts, review notes, and assessments as one publishing workflow rather than isolated files.",
    "A green CI result is not enough when important course contract, caption transcript, accessibility, or rubric alignment checks were skipped.",
    "Keep incident identifiers in the evidence trail, while writing the skill procedure in reusable terms for future course and lesson releases.",
    "Use a standalone skill when prevention requires a multi-step evidence workflow with decision points and transfer examples."
  ],
  "rejected_alternatives": [
    {
      "alternative": "short repository instruction",
      "reason": "A one-line instruction would not capture the multi-step evidence workflow, skill versus instruction decision, service cross-check, and transfer examples needed for future releases."
    },
    {
      "alternative": "add learning to existing instruction",
      "reason": "The repository learning instruction is intended for one to four sentence refinements, while this incident requires an invoked workflow with evidence collection, decision points, examples, and duplication checks."
    },
    {
      "alternative": "update existing course-quality skill",
      "reason": "The existing course-quality and video-accessibility skills are narrower asset review workflows and do not own the broader skill-vs-instruction capture decision or linked publishing-contract process."
    },
    {
      "alternative": "one-off patch note",
      "reason": "A patch note would only summarize this incident and would not help future agents identify caption transcript mismatch, assessment rubric drift, or LMS metadata publishing drift."
    },
    {
      "alternative": "CI-only remediation",
      "reason": "CI warnings were part of the evidence, but the durable learning also requires reviewer comments, style guide rules, course metadata, accessibility artifacts, and learner-facing assessment checks."
    }
  ]
}
EOF
