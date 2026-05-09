# PRD to Plan

Break a PRD into a phased implementation plan using vertical slices (tracer bullets). Output is a Markdown file in `./plans/`.

## Process

### 1\. Confirm the PRD is in context

The PRD should already be in the conversation. If it isn't, ask the user to paste it or point you to the file.

### 2\. Explore the codebase

If you have not already explored the codebase, do so to understand the current architecture, existing patterns, and integration layers.

### 3\. Identify durable architectural decisions

Before slicing, identify high-level decisions that are unlikely to change throughout implementation:

* Route structures / URL patterns
* Database schema shape
* Key data models
* Authentication / authorization approach
* Third-party service boundaries

These go in the plan header so every phase can reference them.

### 4\. Draft vertical slices

Break the PRD into **tracer bullet** phases. Each phase is a thin vertical slice that cuts through ALL integration layers end-to-end, NOT a horizontal slice of one layer.

### 5\. Quiz the user

Present the proposed breakdown as a numbered list. For each phase show:

* **Title**: short descriptive name
* **User stories covered**: which user stories from the PRD this addresses

Ask the user:

* Does the granularity feel right? (too coarse / too fine)
* Should any phases be merged or split further?

Iterate until the user approves the breakdown.

### 6\. Write the plan file

Create `./plans/` if it doesn't exist. Write the plan as a Markdown file named after the feature (e.g. `./plans/user-onboarding.md`). Use the template below.

> Source PRD: 

## Architectural decisions

Durable decisions that apply across all phases:

* **Routes**: ...
* **Schema**: ...
* **Key models**: ...
* (add/remove sections as appropriate)

---

## Phase 1: 

**User stories**: 

### What to build

A concise description of this vertical slice. Describe the end-to-end behavior, not layer-by-layer implementation.

### Acceptance criteria

* Criterion 1
* Criterion 2
* Criterion 3

---

## Phase 2: 

**User stories**: 

### What to build

...

### Acceptance criteria

* ...
