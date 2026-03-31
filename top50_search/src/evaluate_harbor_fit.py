from __future__ import annotations

from pathlib import Path
from typing import Iterable
import re

import yaml

DEFAULT_RULES_PATH = Path(__file__).resolve().parents[1] / "configs" / "harbor_fit_rules.yaml"

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


def evaluate_skill_bundle(bundle_dir: Path | str) -> dict:
    """Evaluate a skill bundle against Harbor fit rules and return axis insights."""

    text = read_bundle_text(bundle_dir)
    text_lower = text.lower()
    axes = load_rules()
    results: dict[str, dict] = {}
    for axis_name, axis_config in axes.items():
        results[axis_name] = _evaluate_axis(axis_config, text_lower)

    selected = all(entry["score"] > 0 for entry in results.values())
    return {"selected": selected, **results}
