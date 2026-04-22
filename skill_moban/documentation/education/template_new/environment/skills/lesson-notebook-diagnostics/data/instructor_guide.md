# Instructor Guide: New Analyst Workshop

## What we're analyzing

Open with the lesson goal from `lesson_brief.md`: learners should turn one workshop snapshot into a trustworthy beginner analysis. Remind the group that we are using `learner_events.csv`, `quiz_attempts.csv`, and `quiz_items.csv`, so this is a bounded teaching exercise rather than a causal evaluation.

## Understand the event data

Pause on the event names before anyone computes a rate. Use `reference_docs/glossary.md` to explain `session_started`, `lesson_completed`, `practice_opened`, and `practice_submitted`. Coaching note: if learners jump straight into percentages, bring them back to grain and event meaning first.

## Build the session funnel

Ask learners to compute the funnel with unique learners, not event rows. Use `metric_definitions.yaml` and `reference_docs/facilitation_notes.md` to call out why raw counts would inflate the story. Coaching note: ask which step loses the most learners and how they would explain that clearly.

## Compare quiz outcomes

Switch from event progress to assessment outcomes. Emphasize that `quiz_pass_rate` is learner-level even though `quiz_attempts.csv` is attempt-level. Then use `quiz_items.csv` to surface which topics still create the most confusion. In this snapshot, `Retry behavior` has the highest error rate, so topic-level diagnostics help explain why overall pass rate alone is not enough.

## Spot metric definition traps

Explicitly compare the correct definitions for `completion_rate`, `practice_submission_rate`, `quiz_pass_rate`, and `retry_rate` with the most common failure modes. Use `reference_docs/glossary.md`, `reference_docs/facilitation_notes.md`, and the misconceptions from `quiz_items.csv` to make the traps concrete.

## Practice

Have learners answer three prompts: explain the biggest funnel drop, defend the learner-level quiz pass definition, and choose one misconception topic to reteach. Coaching note: if answers drift into unsupported claims, ask them to name the source file that supports each statement.

## Wrap up

Close by tying the bundle together: the notebook, guide, manifest, and source map should all tell the same story. Reinforce that `metric_definitions.yaml` controls the metric language, while `learner_events.csv`, `quiz_attempts.csv`, and `quiz_items.csv` provide the evidence.
