from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Iterable
import re

import yaml
from top20_search.src import openai_review_client

DEFAULT_RULES_PATH = Path(__file__).resolve().parents[1] / "configs" / "harbor_fit_rules.yaml"
DEFAULT_BUCKET_REVIEW_RULES_PATH = Path(__file__).resolve().parents[1] / "configs" / "bucket_review_rules.yaml"
SHARED_BUCKET_RULE_KEY = "_shared"

TOKEN_CLUES: dict[str, list[str]] = {
    "data_objective_clarity": [
        "data objective clarity",
        "objective clarity",
        "data quality",
        "data contracts",
        "validation rules",
    ],
    "schema_scope": [
        "schema scope",
        "schema boundaries",
        "schema boundary",
        "schema constraints",
        "schema expectations",
        "expectation suite",
        "dbt tests",
    ],
    "data_engineering_ownership": [
        "data engineering ownership",
        "data engineering team owns",
        "data pipelines",
        "dataset",
        "datasets",
        "table",
        "tables",
        "great expectations",
        "dbt",
    ],
    "registry_or_session_focus": ["registry", "session focus", "catalog entry"],
    "installation_or_publication_flow": ["installation", "publication flow", "install skill"],
    "deterministic_configuration": [
        "deterministic configuration",
        "versioned files",
        "same validation runs",
        "ci/cd",
        "checkpoint",
        "checkpoints",
    ],
    "resource_specified": [
        "explicitly specified resources",
        "specified resources",
        "datasets",
        "datasource",
        "datasource settings",
        "expectation suite",
        "test configuration",
    ],
    "vague_exploration": ["vague exploration", "vague_exploration"],
    "marketplace_or_dispatcher_dependency": [
        "marketplace",
        "dispatcher dependency",
        "external deployment orchestrator",
    ],
    "explicit_thresholds": [
        "explicit thresholds",
        "allowed threshold",
        "range checks",
        "null checks",
        "uniqueness checks",
        "expect_",
    ],
    "automated_checks": [
        "automated checks",
        "automated check",
        "validation checks",
        "dbt tests",
        "ci/cd",
        "automatically",
        "checkpoint",
        "checkpoints",
    ],
    "heuristic_judgment": [
        "heuristic judgment",
        "heuristic judgments",
        "heuristic_judgment",
    ],
    "exploratory_only": ["exploratory only", "exploratory-only", "exploratory_only"],
}

NEGATION_PATTERNS = (
    re.compile(r"\bnot\b"),
    re.compile(r"\bno\b"),
    re.compile(r"\bnever\b"),
    re.compile(r"\bwithout\b"),
    re.compile(r"\bdoes\s+not\b"),
    re.compile(r"\bdoesn't\b"),
    re.compile(r"\bis\s+not\b"),
    re.compile(r"\bisn't\b"),
)


def _is_negated(text: str, idx: int) -> bool:
    sentence_start = 0
    for boundary in (".", "!", "?", "\n"):
        pos = text.rfind(boundary, 0, idx)
        if pos + 1 > sentence_start:
            sentence_start = pos + 1
    segment = text[sentence_start:idx]
    return any(pattern.search(segment) for pattern in NEGATION_PATTERNS)


def _contains_positive_clue(clue: str, text_lower: str) -> bool:
    start = 0
    while True:
        idx = text_lower.find(clue, start)
        if idx == -1:
            return False
        if not _is_negated(text_lower, idx):
            return True
        start = idx + len(clue)
    return False


def load_rules(path: Path | str = DEFAULT_RULES_PATH) -> dict[str, dict]:
    """Load Harbor fit axes from the provided config path."""

    rules_path = Path(path)
    if not rules_path.exists():
        raise FileNotFoundError(f"Harbor fit rules not found at {rules_path}")

    with rules_path.open(encoding="utf-8") as stream:
        payload = yaml.safe_load(stream)

    if not isinstance(payload, dict):
        raise ValueError("Harbor fit rules must be a mapping")

    harbor_rules = payload.get("harbor_fit_rules")
    if not isinstance(harbor_rules, dict):
        raise ValueError("'harbor_fit_rules' key is required")

    validated: dict[str, dict] = {}
    for axis in ("capability_boundary", "environment_reproducibility", "verifier_stability"):
        axis_entry = harbor_rules.get(axis)
        if not isinstance(axis_entry, dict):
            raise ValueError(f"Harbor axis {axis} must be defined")
        validated[axis] = axis_entry

    return validated


def load_bucket_review_rules(path: Path | str = DEFAULT_BUCKET_REVIEW_RULES_PATH) -> dict[str, dict]:
    """Load the shared Harbor rubric used by every bucket."""

    rules_path = Path(path)
    if not rules_path.exists():
        raise FileNotFoundError(f"Bucket review rules not found at {rules_path}")

    with rules_path.open(encoding="utf-8") as stream:
        payload = yaml.safe_load(stream)

    if not isinstance(payload, dict):
        raise ValueError("Bucket review rules must be a mapping")

    raw_rules = payload.get("bucket_review_rules")
    if not isinstance(raw_rules, dict):
        raise ValueError("'bucket_review_rules' key is required")

    shared_rule = raw_rules.get(SHARED_BUCKET_RULE_KEY)
    if not isinstance(shared_rule, Mapping):
        raise ValueError(f"bucket review rules must define a '{SHARED_BUCKET_RULE_KEY}' mapping")

    normalized_shared = _normalize_bucket_rule(
        SHARED_BUCKET_RULE_KEY,
        shared_rule,
        allow_missing_bucket_summary=True,
    )
    for key, value in raw_rules.items():
        bucket_name = str(key)
        if bucket_name == SHARED_BUCKET_RULE_KEY:
            continue
        if not isinstance(value, Mapping):
            raise ValueError(f"bucket review rule for '{bucket_name}' must be a mapping")
    return {SHARED_BUCKET_RULE_KEY: normalized_shared}


def _normalize_rule_items(
    bucket_name: str,
    field_name: str,
    items: object,
    *,
    allow_required: bool,
) -> list[dict[str, object]]:
    if not isinstance(items, list):
        raise ValueError(f"{field_name} for '{bucket_name}' must be a list")

    normalized_items: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            raise ValueError(f"{field_name}[{index}] for '{bucket_name}' must be a mapping")
        rule_id = str(item.get("id") or "").strip()
        rule_text = str(item.get("text") or "").strip()
        if not rule_id:
            raise ValueError(f"{field_name}[{index}] for '{bucket_name}' missing id")
        if not rule_text:
            raise ValueError(f"{field_name}[{index}] for '{bucket_name}' missing text")
        if rule_id in seen_ids:
            raise ValueError(f"{field_name} for '{bucket_name}' contains duplicate id '{rule_id}'")
        seen_ids.add(rule_id)
        normalized_rule: dict[str, object] = {"id": rule_id, "text": rule_text}
        if allow_required:
            normalized_rule["required"] = bool(item.get("required", False))
        normalized_items.append(normalized_rule)
    return normalized_items


def _normalize_string_list(bucket_name: str, field_name: str, value: object) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"{field_name} for '{bucket_name}' must be a list[str]")
    return [item.strip() for item in value if item.strip()]


def _normalize_bucket_rule(
    bucket_name: str,
    rule: Mapping[str, object],
    *,
    allow_missing_bucket_summary: bool = False,
) -> dict[str, object]:
    normalized_rule = dict(rule)
    keep_rules = _normalize_rule_items(
        bucket_name,
        "keep_rules",
        normalized_rule.get("keep_rules"),
        allow_required=True,
    )
    drop_rules = _normalize_rule_items(
        bucket_name,
        "drop_rules",
        normalized_rule.get("drop_rules"),
        allow_required=False,
    )
    normalized_rule["keep_rules"] = keep_rules
    normalized_rule["drop_rules"] = drop_rules
    normalized_rule["enabled"] = bool(normalized_rule.get("enabled", False))
    normalized_rule["preferred_model"] = str(normalized_rule.get("preferred_model") or "gpt-5.4-mini")
    normalized_rule["max_markdown_files"] = int(normalized_rule.get("max_markdown_files", 6))
    normalized_rule["max_total_characters"] = int(normalized_rule.get("max_total_characters", 24000))
    normalized_rule["bucket_summary"] = str(normalized_rule.get("bucket_summary") or "").strip()
    normalized_rule["topic_keywords"] = _normalize_string_list(bucket_name, "topic_keywords", normalized_rule.get("topic_keywords"))
    normalized_rule["anti_keywords"] = _normalize_string_list(bucket_name, "anti_keywords", normalized_rule.get("anti_keywords"))

    if not allow_missing_bucket_summary and not normalized_rule["bucket_summary"]:
        raise ValueError(f"bucket review rule for '{bucket_name}' missing bucket_summary")

    return normalized_rule


def parse_review_payload(payload: dict, *, model_name: str = "gpt-5.4-mini") -> dict:
    """Normalize and validate structured review payload from model output."""

    required = {"selected", "decision", "summary", "matched_keep_rules", "matched_drop_rules", "confidence"}
    missing = sorted(required.difference(payload))
    if missing:
        raise ValueError(f"review payload missing fields: {missing}")

    selected = payload["selected"]
    if not isinstance(selected, bool):
        raise ValueError("review payload field 'selected' must be a bool")

    decision = payload["decision"]
    if decision not in {"keep", "drop"}:
        raise ValueError("review payload field 'decision' must be one of: keep, drop")

    summary = payload["summary"]
    if not isinstance(summary, str):
        raise ValueError("review payload field 'summary' must be a str")

    matched_keep_rules = payload["matched_keep_rules"]
    if not isinstance(matched_keep_rules, list) or any(not isinstance(item, str) for item in matched_keep_rules):
        raise ValueError("review payload field 'matched_keep_rules' must be a list[str]")

    matched_drop_rules = payload["matched_drop_rules"]
    if not isinstance(matched_drop_rules, list) or any(not isinstance(item, str) for item in matched_drop_rules):
        raise ValueError("review payload field 'matched_drop_rules' must be a list[str]")

    confidence = payload["confidence"]
    if confidence not in {"low", "medium", "high"}:
        raise ValueError("review payload field 'confidence' must be one of: low, medium, high")

    return {
        "selected": selected,
        "decision": decision,
        "summary": summary,
        "matched_keep_rules": matched_keep_rules,
        "matched_drop_rules": matched_drop_rules,
        "confidence": confidence,
        "model": model_name,
        "raw_response_id": str(payload.get("raw_response_id", "")),
    }


def _required_keep_rule_ids(bucket_rule: Mapping[str, object]) -> set[str]:
    keep_rules = bucket_rule.get("keep_rules")
    if not isinstance(keep_rules, list):
        return set()
    return {
        str(rule.get("id"))
        for rule in keep_rules
        if isinstance(rule, Mapping) and bool(rule.get("required")) and str(rule.get("id") or "").strip()
    }


def _finalize_review_result(review: dict[str, object], bucket_rule: Mapping[str, object]) -> dict[str, object]:
    required_keep_rules = _required_keep_rule_ids(bucket_rule)
    matched_keep_rules = {
        str(item).strip()
        for item in review.get("matched_keep_rules", [])
        if isinstance(item, str) and item.strip()
    }
    matched_drop_rules = [
        str(item).strip()
        for item in review.get("matched_drop_rules", [])
        if isinstance(item, str) and item.strip()
    ]
    missing_required_keep_rules = sorted(required_keep_rules.difference(matched_keep_rules))
    final_selected = bool(review.get("selected")) and not matched_drop_rules and not missing_required_keep_rules

    finalized = dict(review)
    finalized["model_selected"] = bool(review.get("selected"))
    finalized["selected"] = final_selected
    finalized["decision"] = "keep" if final_selected else "drop"
    finalized["missing_required_keep_rules"] = missing_required_keep_rules
    return finalized


def read_bundle_text(bundle_dir: Path | str) -> str:
    """Concatenate all Markdown documentation under the skill bundle directory."""

    base_dir = Path(bundle_dir)
    if not base_dir.exists():
        raise FileNotFoundError(f"Bundle directory not found: {base_dir}")
    if not base_dir.is_dir():
        raise ValueError(f"Expected a directory for bundle_dir, got: {bundle_dir}")

    contents: list[str] = []
    for path in sorted(base_dir.rglob("*.md")):
        contents.append(path.read_text(encoding="utf-8"))
    return "\n".join(contents)


def select_bundle_markdown(
    bundle_dir: Path | str,
    *,
    max_files: int,
    max_total_characters: int,
) -> tuple[list[str], str]:
    """Select markdown files from bundle with SKILL.md priority and size limits."""

    base_dir = Path(bundle_dir)
    if not base_dir.exists():
        raise FileNotFoundError(f"Bundle directory not found: {base_dir}")
    if not base_dir.is_dir():
        raise ValueError(f"Expected a directory for bundle_dir, got: {bundle_dir}")

    markdown_paths = sorted(base_dir.rglob("*.md"))
    ordered_paths = sorted(
        markdown_paths,
        key=lambda path: (0 if path.name == "SKILL.md" else 1, len(path.parts), path.as_posix()),
    )

    selected_files: list[str] = []
    chunks: list[str] = []
    total_characters = 0

    for path in ordered_paths:
        rel_path = path.relative_to(base_dir).as_posix()
        content = path.read_text(encoding="utf-8")
        candidate = f"# FILE: {rel_path}\n\n{content}\n"

        if len(selected_files) >= max_files:
            break
        if total_characters + len(candidate) > max_total_characters:
            if not selected_files and max_total_characters > 0:
                truncated_candidate = f"# FILE: {rel_path}\n\n{content[:max_total_characters]}\n"
                selected_files.append(rel_path)
                chunks.append(truncated_candidate)
                total_characters = max_total_characters
            break

        selected_files.append(rel_path)
        chunks.append(candidate)
        total_characters += len(candidate)

    return selected_files, "\n".join(chunks)


def _get_clues_for_token(token: str) -> list[str]:
    normalized = token.lower()
    hints = TOKEN_CLUES.get(normalized)
    if hints:
        return hints
    fallback = normalized.replace("_", " ").strip()
    if fallback:
        return [fallback]
    return []


def _match_signals(tokens: Iterable[str], text_lower: str) -> list[str]:
    matches: list[str] = []
    seen: set[str] = set()
    for raw_token in tokens:
        token = str(raw_token).strip().lower()
        if not token or token in seen:
            continue
        for clue in _get_clues_for_token(token):
            if clue and _contains_positive_clue(clue, text_lower):
                matches.append(token)
                seen.add(token)
                break
    return matches


def _evaluate_axis(axis_config: dict, text_lower: str) -> dict:
    positive_tokens = axis_config.get("positive_signals") or []
    negative_tokens = axis_config.get("negative_signals") or []
    positive_hits = _match_signals(positive_tokens, text_lower)
    negative_hits = _match_signals(negative_tokens, text_lower)
    score = len(positive_hits) - len(negative_hits)
    return {
        "description": axis_config.get("description", ""),
        "positive_hits": positive_hits,
        "negative_hits": negative_hits,
        "score": score,
    }


def _resolve_bucket_slug(bucket_slug: str | None) -> str:
    if bucket_slug:
        return bucket_slug
    return "data-quality"


def evaluate_skill_bundle(bundle_dir: Path | str, *, bucket_slug: str | None = None, review_client=None) -> dict:
    """Evaluate a skill bundle with bucket-specific structured review rules."""

    rules = load_bucket_review_rules()
    resolved_bucket_slug = _resolve_bucket_slug(bucket_slug)
    bucket_rule = rules.get(SHARED_BUCKET_RULE_KEY)
    if bucket_rule is None:
        raise ValueError("shared bucket review rules not configured")
    if not bucket_rule.get("enabled"):
        raise ValueError("shared bucket review rules not enabled")

    model_name = str(bucket_rule.get("preferred_model") or "gpt-5.4-mini")
    max_files = int(bucket_rule.get("max_markdown_files", 6))
    max_total_characters = int(bucket_rule.get("max_total_characters", 24000))

    bundle_files_used, bundle_text = select_bundle_markdown(
        bundle_dir,
        max_files=max_files,
        max_total_characters=max_total_characters,
    )
    if not bundle_files_used:
        raise ValueError(f"bundle markdown selection is empty for bucket {resolved_bucket_slug}")

    client = review_client or openai_review_client.request_structured_review
    try:
        prompt_rule = {
            "policy_summary": bucket_rule.get("summary", ""),
            "bucket_slug": resolved_bucket_slug,
            "keep_rules": bucket_rule.get("keep_rules", []),
            "drop_rules": bucket_rule.get("drop_rules", []),
            "required_keep_rule_ids": sorted(_required_keep_rule_ids(bucket_rule)),
            "review_instructions": bucket_rule.get("review_instructions", ""),
        }
        payload = client(
            model=model_name,
            system_prompt=(
                "You are a strict Harbor skill screener. "
                "Return JSON only. "
                "Use matched_keep_rules and matched_drop_rules to report rule ids, not free-form text. "
                "Only select a skill when every required keep rule is satisfied and no drop rule is triggered."
            ),
            user_prompt=(
                f"Bucket: {resolved_bucket_slug}\n"
                f"Rules: {yaml.safe_dump(prompt_rule, sort_keys=False)}\n\n"
                f"Bundle:\n{bundle_text}"
            ),
        )
    except openai_review_client.OpenAIReviewError as exc:
        raise ValueError(f"bucket review request failed for {resolved_bucket_slug}: {exc}") from exc

    result = _finalize_review_result(parse_review_payload(payload, model_name=model_name), bucket_rule)
    result["bundle_files_used"] = bundle_files_used
    return result
