Source URL: https://newsletter.posthog.com/p/the-golden-rules-of-agent-first-product
Title: Golden rules for agent-first product work
Document kind: supporting_context

# Working notes

This source frames agent-first work as product design, not prompt decoration.
It recommends beginning with the task loop and only then selecting model behavior.

## Rule set

Give the agent direct access to the tools and records that already drive the workflow.
Keep the user in a product surface where they can inspect state, edit inputs, and step in.
Avoid hiding the main product behind a chat box when the task already has a better interface.
Treat memory as product state that must be visible, inspectable, and correctable.
If the model needs structured context every time, build the structure into the product layer.

## Failure patterns

Many teams bolt on an agent before deciding what counts as success.
That creates a feature with unclear boundaries, partial permissions, and no stable fallback.
Another pattern is asking the model to bridge gaps that should have been solved in the data model.
The source argues that agents magnify product sharp edges instead of hiding them.

## Design habits

Choose one operational loop and make it end to end.
Define the stopping point, the handoff point, and the review point.
Log which tools were called and which context objects were used.
Build for recovery because the first run will often be incomplete.
The article also favors explicit user-visible plans over hidden autonomy.

## Content-use implications

For outward-facing writing, the source supports claims about access, state, review, and recoverability.
It does not support claims about full autonomy or universal task coverage.
