#!/usr/bin/env python3
import re


def normalize_text(value: str) -> str:
    value = value or ""
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def canonical_study_design(record: dict) -> str:
    design_note = normalize_text(record["design_note"])
    if "systematic review" in design_note or record["source_type"] == "evidence_synthesis":
        return "systematic_review_meta_analysis"
    if "feasibility" in design_note:
        return "feasibility_rct"
    if "randomized" in design_note:
        return "parallel_rct"
    raise ValueError(f"Unable to derive study design for {record['study_id']}")


def canonical_population_scope(record: dict) -> str:
    population_note = normalize_text(record["population_note"])
    if "adolescent" in population_note:
        return "adolescents_with_type_2_diabetes"
    if "at risk of type 2 diabetes" in population_note or "prediabetes" in population_note:
        return "adults_at_risk_of_type_2_diabetes"
    if "adult" in population_note and "type 2 diabetes" in population_note:
        return "adults_with_type_2_diabetes"
    return "mixed_t2d_or_impaired_fasting_glucose"


def canonical_comparator_type(record: dict) -> str:
    comparator_note = normalize_text(record["comparator_note"])
    if "usual care" in comparator_note:
        return "usual_care_control"
    if "prolonged eating window" in comparator_note:
        return "prolonged_eating_window_control"
    if "dietitian" in comparator_note or "dietetic" in comparator_note:
        return "active_dietetic_guidance"
    if "mediterranean" in comparator_note or "conventional dieting" in comparator_note:
        return "active_mediterranean_diet"
    if "calorie restriction" in comparator_note and "standard care" in comparator_note:
        return "calorie_restriction_or_standard_care"
    if "calorie restriction" in comparator_note or "control" in comparator_note:
        return "calorie_restriction_or_control"
    if record["source_type"] == "evidence_synthesis":
        return "evidence_synthesis"
    raise ValueError(f"Unable to derive comparator type for {record['study_id']}")


def canonical_primary_outcome_direction(record: dict) -> str:
    outcome_note = normalize_text(record["outcome_note"])
    comparator_type = canonical_comparator_type(record)
    if "feasibility" in outcome_note or "exploratory" in outcome_note:
        return "exploratory_no_between_group_difference"
    if comparator_type in {"active_dietetic_guidance", "active_mediterranean_diet"} and (
        "non inferior" in outcome_note
        or "noninferior" in outcome_note
        or "comparable" in outcome_note
        or "similar" in outcome_note
        or "no additional metabolic benefit" in outcome_note
        or "no between group difference" in outcome_note
    ):
        return "similar_to_active_diet"
    return "benefit_vs_control"


def eligibility_reason(record: dict) -> str:
    if record["source_type"] != "primary_trial":
        return "not_primary_trial"
    population_scope = canonical_population_scope(record)
    if population_scope == "adolescents_with_type_2_diabetes":
        return "adolescent_population"
    if population_scope == "adults_at_risk_of_type_2_diabetes":
        return "at_risk_population"
    if population_scope != "adults_with_type_2_diabetes":
        return "population_out_of_scope"
    if canonical_study_design(record) == "feasibility_rct":
        return "feasibility_trial"
    if int(record["duration_weeks"]) < 12:
        return "follow_up_too_short"
    return "eligible"


def is_eligible(record: dict) -> bool:
    return eligibility_reason(record) == "eligible"


def canonical_row(record: dict) -> dict:
    return {
        "study_id": record["study_id"],
        "short_citation": record["short_citation"],
        "study_design": canonical_study_design(record),
        "population_scope": canonical_population_scope(record),
        "duration_weeks": str(int(record["duration_weeks"])),
        "comparator_type": canonical_comparator_type(record),
        "primary_outcome_direction": canonical_primary_outcome_direction(record),
    }
