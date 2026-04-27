import hashlib
import json
import re
from pathlib import Path

import requests

OUTPUT_ROOT = Path("/outputs")
SKILL_PATH = OUTPUT_ROOT / "lesson_skill" / "SKILL.md"
REPORT_PATH = OUTPUT_ROOT / "capture_report.json"
SESSION_ROOT = Path("/workspace/session_bundle")
ENV_SKILL_PATH = Path("/workspace/environment/skills/update-skills/SKILL.md")
API_ROOT = "http://127.0.0.1:8080"

EXPECTED_INPUT_SHA256 = {
    "incident_manifest.json": "c688c5fb545ae1102d3ad675729df7cb2ebe24cf7da670c89f35cee0a68dffc5",
    "tickets/TCK-1842.json": "a2e51043fed7ec984c06baca6d7465b415f8699d9794a892f40525591fe61f98",
    "reviews/reviewer_notes.md": "588363eff127d00e2121535a6f820ffbc6da06101fc14a0f5acbef24fe2c3c62",
    "logs/publish_ci.log": "85084c15096d93e26fe3fb40bc1e0a7f05bdf0f0fa21bc640910f163c5477cb4",
    "metadata/lms_snapshot.json": "f3b48ff5983d97f5730dc37d2cf3a8b70572607ee4936861be29c1e593d9595a",
    "metadata/course_contract.json": "220421caf4b9b587e370a7edb23f2f58a3648e3e5a312f5f982851337a480394",
    "style_guides/course_quality_playbook.md": "718960137522a98377925b6ecbbb3bb09d178526bf6cee65ddfed7b9ca293e7c",
    "repository_inventory.json": "3349ba025df4dea5a0772c91eb9dbec5e0cdb0ab31c2f5359d27b98ef3193571",
}

EXPECTED_SKILL_SHA256 = "f5c7bb3ed56fb261788f2f96d0e4a8f65ac354683d928cfe9fb1b961d74955d2"

SECTION_NAMES = [
    "When to Use",
    "Evidence Reviewed",
    "Procedure",
    "Quality Checks",
    "Example",
]

ONE_OFF_IDENTIFIERS = [
    "TCK-1842",
    "BIO-201",
    "cell-transport-module-03",
    "lms-build-7781",
    "module03_transport",
    "module03_quiz",
    "2026-04-18",
    "Foundations of Cell Biology",
]

FORBIDDEN_BYPASS_PATTERNS = [
    "skip validation",
    "skip the validation",
    "ignore metadata",
    "delete failing",
    "remove failing",
    "mock service",
    "disable checks",
    "turn off checks",
    "hidden answer",
]

EDUCATION_CONCEPT_GROUPS = {
    "course_structure": {"course", "lesson", "module", "prerequisite"},
    "assessment_alignment": {"assessment", "quiz", "rubric", "learning objective"},
    "publishing_chain": {"metadata", "lms", "publishing", "release"},
    "accessibility_media": {"accessibility", "transcript", "caption", "learner-facing"},
    "review_evidence": {"review", "ci log", "style guide", "ticket", "evidence"},
}

FUTURE_SCENARIOS = {
    "caption_transcript_mismatch": {"transcript", "caption", "learner-facing", "accessibility"},
    "quiz_rubric_objective_drift": {"rubric", "assessment", "learning objective", "review"},
    "lms_module_order_drift": {"metadata", "lms", "module", "publishing"},
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def norm(text) -> str:
    return re.sub(r"\s+", " ", str(text).lower()).strip()


def load_skill_text() -> str:
    assert SKILL_PATH.exists(), "Missing /outputs/lesson_skill/SKILL.md"
    text = SKILL_PATH.read_text(encoding="utf-8")
    assert len(text) > 1200, "Skill draft is too short to contain a reusable procedure"
    return text


def load_report() -> dict:
    assert REPORT_PATH.exists(), "Missing /outputs/capture_report.json"
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


def parse_frontmatter(text: str) -> dict:
    assert text.startswith("---\n"), "SKILL.md must start with YAML frontmatter"
    end = text.find("\n---", 4)
    assert end != -1, "SKILL.md frontmatter must be closed with ---"
    fields = {}
    for line in text[4:end].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip().strip('"').strip("'")
    return fields


def section_text(text: str, section: str) -> str:
    pattern = rf"^## {re.escape(section)}\s*$"
    match = re.search(pattern, text, flags=re.MULTILINE)
    assert match, f"Missing section ## {section}"
    next_match = re.search(r"^## .+$", text[match.end():], flags=re.MULTILINE)
    end = match.end() + next_match.start() if next_match else len(text)
    content = text[match.end():end].strip()
    assert len(content) >= 80, f"Section ## {section} is too thin"
    return content


def general_sections_text(text: str) -> str:
    return "\n\n".join(section_text(text, name) for name in ["When to Use", "Procedure", "Quality Checks", "Example"])


def source_to_text(source: str) -> str:
    if source.startswith("http://127.0.0.1:8080/"):
        response = requests.get(source, timeout=5)
        assert response.status_code == 200, f"Evidence API source is not reachable: {source}"
        return json.dumps(response.json(), ensure_ascii=False)

    if source == "/workspace/environment/skills/update-skills/SKILL.md" or source.endswith("environment/skills/update-skills/SKILL.md"):
        assert ENV_SKILL_PATH.exists(), "Required process skill evidence is missing"
        return ENV_SKILL_PATH.read_text(encoding="utf-8")

    rel = source
    for prefix in ["/workspace/session_bundle/", "session_bundle/"]:
        if rel.startswith(prefix):
            rel = rel[len(prefix):]
    path = SESSION_ROOT / rel
    assert path.exists(), f"Evidence file source does not exist: {source}"
    return path.read_text(encoding="utf-8")


def meaningful_tokens(text: str):
    stop = {
        "the", "and", "for", "with", "that", "this", "from", "into", "using", "should",
        "must", "were", "was", "are", "not", "one", "two", "course", "lesson"
    }
    return {
        token
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{3,}", text.lower())
        if token not in stop
    }


def test_protected_inputs_and_skill_copy_are_unchanged():
    for relative, expected in EXPECTED_INPUT_SHA256.items():
        path = SESSION_ROOT / relative
        assert path.exists(), f"Missing protected input file: {relative}"
        assert sha256(path) == expected, f"Protected input was modified: {relative}"

    assert ENV_SKILL_PATH.exists(), "Missing provided process skill /workspace/environment/skills/update-skills/SKILL.md"
    assert sha256(ENV_SKILL_PATH) == EXPECTED_SKILL_SHA256, "Provided update-skills skill copy was modified"


def test_local_knowledge_service_is_available():
    health = requests.get(f"{API_ROOT}/health", timeout=5).json()
    assert health["ok"] is True
    assert health["snapshot_id"] == "course-learning-capture-20260426"
    incident = requests.get(f"{API_ROOT}/incidents/TCK-1842", timeout=5).json()
    assert incident["ticket"]["ticket_id"] == "TCK-1842"
    assert any("SKIPPED" in warning for warning in incident["ci_warnings"])
    inventory = requests.get(f"{API_ROOT}/repository/inventory", timeout=5).json()
    assert inventory["snapshot_id"] == "repo-conventions-education-20260426"
    assert len(inventory["existing_instructions"]) >= 2
    assert len(inventory["existing_skills"]) >= 2


def test_skill_frontmatter_sections_and_report_schema():
    text = load_skill_text()
    fields = parse_frontmatter(text)
    assert set(fields) >= {"name", "description"}
    assert re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", fields["name"]), "Skill name must be lowercase-hyphenated"
    assert 8 <= len(fields["description"].split()) <= 35, "Description must be a concise use-case sentence"
    assert "TCK-1842" not in fields["name"] + fields["description"]
    assert "BIO-201" not in fields["name"] + fields["description"]
    for section in SECTION_NAMES:
        section_text(text, section)

    report = load_report()
    assert report["decision"] == "skill"
    assert report["skill_name"] == fields["name"]
    assert isinstance(report.get("incident_summary"), str) and len(report["incident_summary"].split()) >= 12
    assert isinstance(report.get("root_cause"), str) and len(report["root_cause"].split()) >= 12
    assert isinstance(report.get("evidence"), list) and len(report["evidence"]) >= 5
    assert isinstance(report.get("reusable_principles"), list) and len(report["reusable_principles"]) >= 3
    assert isinstance(report.get("rejected_alternatives"), list) and len(report["rejected_alternatives"]) >= 2


def test_evidence_sources_are_real_and_findings_are_grounded():
    report = load_report()
    sources = {item.get("source", "") for item in report["evidence"]}
    assert any(source.startswith("http://127.0.0.1:8080/") for source in sources), "At least one evidence item must use the local API"
    assert any(not source.startswith("http") for source in sources), "At least one evidence item must cite a session bundle file"
    assert any("repository_inventory" in source or "/repository/inventory" in source for source in sources), "Evidence must include repository convention inventory"
    assert any(source == "/workspace/environment/skills/update-skills/SKILL.md" or source.endswith("environment/skills/update-skills/SKILL.md") for source in sources), "Evidence must cite the provided update-skills process skill"

    for item in report["evidence"]:
        source = item.get("source")
        finding = item.get("finding", "")
        assert source and isinstance(finding, str) and len(finding.split()) >= 5
        source_text = source_to_text(source)
        overlap = meaningful_tokens(finding) & meaningful_tokens(source_text)
        assert len(overlap) >= 2, f"Finding is not grounded in cited evidence: {source}"

    skill_evidence = section_text(load_skill_text(), "Evidence Reviewed")
    assert "http://127.0.0.1:8080" in skill_evidence
    assert "/workspace/session_bundle" in skill_evidence or "tickets/" in skill_evidence or "reviews/" in skill_evidence


def test_generalization_score_is_high_enough():
    text = load_skill_text()
    general = general_sections_text(text)
    general_norm = norm(general)

    score = 0
    one_off_hits = sum(general.count(identifier) for identifier in ONE_OFF_IDENTIFIERS)
    if one_off_hits <= 2:
        score += 2

    covered_groups = 0
    for terms in EDUCATION_CONCEPT_GROUPS.values():
        if any(term in general_norm for term in terms):
            covered_groups += 1
    assert covered_groups >= 4, "Skill must cover multiple reusable education-production concepts"
    score += min(2, covered_groups // 2)

    procedure = section_text(text, "Procedure")
    steps = [line for line in procedure.splitlines() if re.match(r"\s*(?:[-*]|\d+[.)])\s+", line)]
    assert len(steps) >= 4, "Procedure needs at least four actionable steps"
    procedure_norm = norm(procedure)
    action_hits = sum(verb in procedure_norm for verb in ["identify", "gather", "compare", "cross-check", "validate", "document", "record", "update", "verify", "resolve"])
    decision_hits = sum(term in procedure_norm for term in [" if ", " when ", " before ", " after ", " only if ", "treat "])
    input_hits = sum(term in procedure_norm for term in ["course metadata", "release metadata", "review comments", "reviewer notes", "ci logs", "ci warnings", "style guide", "learner-facing", "rubric", "transcript"])
    if action_hits >= 4 and decision_hits >= 2 and input_hits >= 3:
        score += 2

    quality = section_text(text, "Quality Checks")
    quality_norm = norm(quality)
    check_lines = [line for line in quality.splitlines() if re.match(r"\s*(?:[-*]|\d+[.)])\s+", line)]
    if len(check_lines) >= 4 and "evidence" in quality_norm and ("general" in quality_norm or "future" in quality_norm or "workflow" in quality_norm):
        score += 2
    report_norm = norm(REPORT_PATH.read_text(encoding="utf-8"))
    assert (
        "existing instruction" in general_norm
        or "existing skill" in general_norm
        or "duplicat" in general_norm
        or "existing instruction" in report_norm
        or "existing skill" in report_norm
        or "duplicat" in report_norm
        or "learnings.instructions.md" in report_norm
    ), "The output must include an existing-file or duplication check from the update-skills workflow"

    scenario_hits = 0
    for terms in FUTURE_SCENARIOS.values():
        if len([term for term in terms if term in general_norm]) >= 3:
            scenario_hits += 1
    if scenario_hits >= 2:
        score += 2

    assert score >= 8, f"Generalization score too low: {score}/10"


def test_example_contains_wrong_and_corrected_transferable_pattern():
    example = section_text(load_skill_text(), "Example")
    example_norm = norm(example)
    assert re.search(r"\b(wrong|bad)\b", example_norm), "Example must include a wrong/bad approach"
    assert re.search(r"\b(corrected|better|good)\b", example_norm), "Example must include a corrected/better approach"
    assert "BIO-201" not in example and "TCK-1842" not in example, "Example should be transferable, not tied to the incident ID"
    assert any(term in example_norm for term in ["course", "lesson", "module"])
    assert any(term in example_norm for term in ["metadata", "lms", "publishing"])
    assert any(term in example_norm for term in ["rubric", "assessment", "learning objective"])


def test_rejected_alternatives_and_decision_rationale_match_update_skill_workflow():
    report = load_report()
    alternatives = " ".join(
        f"{item.get('alternative', '')} {item.get('reason', '')}"
        for item in report["rejected_alternatives"]
    ).lower()
    assert "instruction" in alternatives, "Report should explain why a short instruction was insufficient"
    assert "existing instruction" in alternatives or "learning" in alternatives, "Report should address adding a learning to an existing instruction"
    assert (
        "existing skill" in alternatives
        or "update existing" in alternatives
        or "course-quality-checks" in alternatives
        or "video-accessibility-review" in alternatives
        or "nearest skill" in alternatives
    ), "Report should address updating an existing skill"
    principles = (" ".join(report["reusable_principles"]) + " " + alternatives).lower()
    assert "multi-step" in principles or "workflow" in principles
    assert "evidence" in principles
    assert "future" in principles or "reusable" in principles or "recur" in principles or "across" in principles


def test_guardrails_no_bypass_language_or_fake_workflow():
    combined = norm(load_skill_text() + "\n" + REPORT_PATH.read_text(encoding="utf-8"))
    for pattern in FORBIDDEN_BYPASS_PATTERNS:
        assert pattern not in combined, f"Forbidden bypass language found: {pattern}"
    assert "replace the real workflow with" not in combined
    assert "delete input files" not in combined
