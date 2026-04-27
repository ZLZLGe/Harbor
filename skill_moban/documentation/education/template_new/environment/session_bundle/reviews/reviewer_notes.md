# Reviewer Notes

Incident: TCK-1842

The original review only checked that the video file, transcript file, and quiz JSON existed. It did not compare whether the revised learning objective still agreed with the quiz rubric and LMS module ordering.

Observed inconsistencies:

- LMS metadata listed `module_order: [1, 3, 2, 4]`, but the curriculum contract requires prerequisites before application lessons.
- Caption segment `00:04:12.500-00:04:19.300` still contained the pre-review wording about osmosis. The transcript had the corrected explanation.
- The quiz rubric used the old criterion "identifies a transport type" after the objective changed to "compares passive and active transport using evidence from the simulation."
- The accessibility review was marked complete before caption/transcript parity was checked.

Recommended durable learning:

Future agents should treat course metadata, learner-facing assets, accessibility artifacts, reviewer comments, and assessment rubrics as a linked publishing contract. A reusable skill is more appropriate than a short instruction because the prevention path is multi-step, evidence-driven, and likely to recur across courses.
