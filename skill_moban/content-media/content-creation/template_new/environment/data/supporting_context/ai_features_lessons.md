Source URL: https://newsletter.posthog.com/p/what-weve-learned-about-building
Title: Lessons from shipping AI features
Document kind: supporting_context

# Working notes

This source focuses on operational lessons after AI features reach users.
It keeps returning to instrumentation, adoption, and iteration speed.

## Measurement lessons

A launch metric alone does not show whether the feature is helping.
The team needs to inspect retries, edits after generation, acceptance rates, and drop-off points.
Session review and product analytics help explain where the feature felt helpful and where it stalled.
The source also notes that support conversations and internal dogfooding uncover issues faster than dashboard summaries alone.

## Rollout lessons

Small launches create faster learning loops than broad availability.
The source favors tightening the task, gathering examples, and expanding only after the failure modes are legible.
It treats adoption as a product question, not a prompt-tuning question.
If users do not return to the feature, the team should inspect workflow fit before changing the model.

## Team lessons

AI product work needs engineers, product, and design to share the same evidence.
The source warns against separating model evaluation from the rest of product development.
It also pushes teams to record what changed between iterations so they can connect product edits to user outcomes.

## Content-use implications

This packet supports writing about instrumentation, dogfooding, staged rollout, and adoption review.
It does not support announcing benchmark wins, customer counts, or precise conversion lift.
