Source URL: https://newsletter.posthog.com/p/what-we-wish-we-knew-before-building
Title: What we wish we knew before building agent features
Document kind: anchor_article

# Why this packet exists

This note condenses the anchor article into line-addressable working notes for a content team.
The source article argues that agent features fail when teams treat them like a thin chat layer on top of the product.
It frames agents as a product surface that needs product access, observable loops, and clear limits.

## Core observations

Teams often start with a polished demo and only later discover the agent has no durable context.
When the agent cannot see the same objects, history, and workflows as the user, it produces shallow help.
That gap makes the feature look clever in a launch clip and brittle in everyday work.
The article pushes teams to ask what data, permissions, and feedback loops an agent needs before asking how the UI should look.

## Product access and state

An agent should be able to inspect the same underlying entities that matter to the task.
Examples include users, sessions, issues, experiments, alerts, and historical decisions.
If the model only receives a narrow prompt window, the team is forcing judgment into a tiny slice of the product.
The source warns that missing context shows up as repeated clarification questions and weak follow-through.
State also matters after the first answer.
If the agent cannot keep track of what already happened, it resets the conversation and burns trust.

## Scope and launch shape

The article recommends starting with one narrow loop that matters enough to repeat.
It prefers a constrained workflow over a broad assistant that tries to handle every question.
The first useful loop should connect input, action, and a measurable outcome.
Good early targets are tasks where the user already knows what a strong result looks like.
Bad early targets are vague brainstorming prompts that never touch the product.

## Human review and trust

The article does not treat human review as failure.
It treats review as a normal part of the product when the cost of a wrong action is high.
Users need to see what the agent plans to do, what it already did, and where confidence is low.
Trust improves when the product exposes the reasoning path, the data touched, and the remaining uncertainty.

## Feedback loops

Shipping the first version is only the start of the work.
The team needs instrumentation for task completion, abandonment, edits, retries, and handoffs.
Qualitative review matters too, because many early failures are obvious to users but invisible in a single success metric.
The article stresses that a silent miss is more damaging than an explicit fallback.
It also argues that adoption should be measured inside the existing product loop, not as a vanity feature click.

## Editorial takeaways

Write about agents as part of the product, not as a detached magic layer.
Favor concrete product constraints over inflated language.
Use examples that connect context access, action, review, and measurement.
