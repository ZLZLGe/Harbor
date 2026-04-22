# Review Protocol

## Review Question

What is the effect of time-restricted eating interventions on glycaemic outcomes in adults with diagnosed type 2 diabetes?

## Inclusion Criteria

- Population: adults with diagnosed type 2 diabetes
- Study design: randomized controlled intervention study with at least 12 weeks of follow-up
- Intervention: time-restricted eating or closely related timed-feeding strategy
- Comparator: usual care, passive control, calorie restriction, or an active diet program
- Outcome focus: glycaemic outcomes relevant to diabetes management

## Exclusion Criteria

- Adolescents or pediatric populations
- Adults only at risk of type 2 diabetes, prediabetes cohorts, or mixed populations without diagnosed adult T2D as the direct target population
- Reviews, systematic reviews, meta-analyses, editorials, protocols, and other non-primary evidence syntheses
- Feasibility-only pilots outside the adult T2D scope

## Required Extraction Fields

The final `included_studies.csv` must contain these columns:

- `study_id`
- `short_citation`
- `study_design`
- `population_scope`
- `duration_weeks`
- `comparator_type`
- `primary_outcome_direction`

## Value Conventions

- `study_design`: use the canonical trial design label from the validated record
- `population_scope`: keep the exact canonical population label
- `duration_weeks`: integer intervention duration in weeks
- `comparator_type`: keep the exact canonical comparator label
- `primary_outcome_direction`:
  - `benefit_vs_control`: TRE showed glycaemic benefit relative to a passive control condition
  - `similar_to_active_diet`: TRE performed similarly to an active comparator diet rather than clearly outperforming it

## Summary Expectations

The final summary should describe only the final in-scope adult T2D evidence base. It must stay within the supported findings from the included trials, avoid unsupported superiority claims, and avoid pulling in evidence that does not satisfy the screening criteria above.
