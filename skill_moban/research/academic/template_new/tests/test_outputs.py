import json
import re
from pathlib import Path

import bibtexparser
import requests

ANSWER_DIR = Path("/root/answer")
MATRIX_PATH = ANSWER_DIR / "evidence_matrix.json"
BIB_PATH = ANSWER_DIR / "references.bib"
NOTE_PATH = ANSWER_DIR / "literature_note.md"
GATEWAY = "http://127.0.0.1:8765"

EXPECTED_DECISIONS = {
    "C01": "supported",
    "C02": "supported",
    "C03": "supported",
    "C04": "wrong_citation",
    "C05": "overstated",
    "C06": "overstated",
    "C07": "out_of_scope",
    "C08": "unsupported",
    "C09": {"wrong_citation", "unsupported"},
    "C10": "supported",
    "C11": "out_of_scope",
    "C12": "overstated",
}

REQUIRED_TITLES = {
    "retrieval-augmented generation for knowledge-intensive nlp tasks",
    "realm: retrieval-augmented language model pre-training",
    "dense passage retrieval for open-domain question answering",
    "leveraging passage retrieval with generative models for open domain question answering",
    "precise zero-shot dense retrieval without relevance labels",
}

REJECTED_MARKERS = {
    "lewis2020rag_duplicate": "duplicate",
    "chen2024universalragcure": "fake_or_unverified",
    "smith2022qa": "fake_or_unverified",
    "broken_source": "malformed",
    "singhal2023medpalm": "outside_scope",
    "vaswani2017attention": "outside_scope",
}

FORBIDDEN_TITLE_FRAGMENTS = [
    "universal retrieval cures hallucination",
    "question answering with neural networks: a complete solution",
    "large language models encode clinical knowledge",
    "attention is all you need",
]


def load_matrix():
    assert MATRIX_PATH.exists(), "Missing /root/answer/evidence_matrix.json"
    return json.loads(MATRIX_PATH.read_text(encoding="utf-8"))


def load_bib_entries():
    assert BIB_PATH.exists(), "Missing /root/answer/references.bib"
    parser = bibtexparser.bparser.BibTexParser(common_strings=True)
    return bibtexparser.loads(BIB_PATH.read_text(encoding="utf-8"), parser=parser).entries


def norm(text):
    return re.sub(r"\s+", " ", str(text).replace("{", "").replace("}", "")).strip().lower()


def test_gateway_snapshot_is_available_and_unchanged():
    health = requests.get(f"{GATEWAY}/health", timeout=5).json()
    assert health["ok"] is True
    assert health["snapshot_id"] == "academic-rag-qa-20260426"
    assert health["paper_count"] == 7


def test_required_output_files_exist_and_are_nonempty():
    for path in [MATRIX_PATH, BIB_PATH, NOTE_PATH]:
        assert path.exists(), f"Missing required output: {path}"
        assert path.stat().st_size > 80, f"Output is unexpectedly small: {path}"


def test_evidence_matrix_schema_and_claim_coverage():
    matrix = load_matrix()
    assert set(matrix) == {"claims", "source_assessments", "rejected_sources"}
    assert isinstance(matrix["claims"], list)
    assert isinstance(matrix["source_assessments"], list)
    assert isinstance(matrix["rejected_sources"], list)
    claim_ids = [claim.get("claim_id") for claim in matrix["claims"]]
    assert sorted(claim_ids) == sorted(EXPECTED_DECISIONS)
    assert len(claim_ids) == len(set(claim_ids)), "Each claim must appear exactly once"

    for claim in matrix["claims"]:
        assert claim["decision"] in {"supported", "overstated", "unsupported", "wrong_citation", "out_of_scope"}
        assert isinstance(claim.get("evidence_keys"), list)
        assert isinstance(claim.get("rationale"), str) and len(claim["rationale"].split()) >= 8
        if claim["decision"] in {"supported", "unsupported", "out_of_scope"}:
            assert claim.get("corrected_claim") is None
        if claim["decision"] in {"overstated", "wrong_citation"}:
            assert isinstance(claim.get("corrected_claim"), str)
            assert len(claim["corrected_claim"].split()) >= 10


def test_claim_decisions_match_evidence():
    claims = {claim["claim_id"]: claim for claim in load_matrix()["claims"]}
    for claim_id, expected in EXPECTED_DECISIONS.items():
        if isinstance(expected, set):
            assert claims[claim_id]["decision"] in expected
        else:
            assert claims[claim_id]["decision"] == expected

    c04_text = norm(claims["C04"]["corrected_claim"]) + " " + norm(claims["C04"]["rationale"])
    assert "clinical safety" in c04_text
    assert "not" in c04_text or "does not" in c04_text
    c05_text = norm(claims["C05"]["corrected_claim"]) + " " + norm(claims["C05"]["rationale"])
    assert "zero-shot" in c05_text
    assert "every retrieval domain" in c05_text or "universal" in c05_text
    assert "does not" in c05_text or "not" in c05_text
    c06_text = norm(claims["C06"]["corrected_claim"]) + " " + norm(claims["C06"]["rationale"])
    assert "hallucination" in c06_text or "faithfulness" in c06_text
    assert "not" in c06_text or "does not" in c06_text
    assert "med-palm" in norm(claims["C07"]["rationale"]) or "clinical" in norm(claims["C07"]["rationale"])
    assert "human" in norm(claims["C08"]["rationale"])
    c09_text = norm(claims["C09"].get("corrected_claim")) + " " + norm(claims["C09"]["rationale"])
    assert "supervised" in c09_text
    assert "zero-shot" in c09_text
    assert "same" in c09_text or "different" in c09_text or "do not" in c09_text
    assert "latent" in norm(claims["C10"]["rationale"])
    assert "transformer" in norm(claims["C11"]["rationale"])
    c11_text = norm(claims["C11"]["rationale"])
    assert (
        "outside" in c11_text
        or "out of scope" in c11_text
        or "not a retrieval-augmented" in c11_text
        or "not a core in-scope" in c11_text
        or "scope excludes" in c11_text
    )
    c12_text = norm(claims["C12"]["corrected_claim"]) + " " + norm(claims["C12"]["rationale"])
    assert "retrieval coverage" in c12_text
    assert "limitation" in c12_text or "depends" in c12_text


def test_clean_bibliography_contains_only_accepted_in_scope_sources():
    entries = load_bib_entries()
    assert len(entries) == 5, f"Expected exactly 5 accepted bibliography entries, got {len(entries)}"
    titles = {norm(entry.get("title", "")) for entry in entries}
    assert REQUIRED_TITLES <= titles

    all_bib = norm(BIB_PATH.read_text(encoding="utf-8"))
    for fragment in FORBIDDEN_TITLE_FRAGMENTS:
        assert fragment not in all_bib
    assert "10.0000/fake" not in all_bib
    assert "10.1234/ijaias" not in all_bib

    for entry in entries:
        assert entry.get("ID"), "Each BibTeX entry needs a citation key"
        assert entry.get("author"), f"Missing author in {entry.get('ID')}"
        assert entry.get("year") and entry["year"].isdigit(), f"Missing numeric year in {entry.get('ID')}"
        assert entry.get("title"), f"Missing title in {entry.get('ID')}"
        assert entry.get("doi") or entry.get("eprint") or entry.get("url"), f"Missing stable identifier in {entry.get('ID')}"


def test_evidence_keys_resolve_to_bibliography_entries():
    entries = load_bib_entries()
    bib_keys = {entry["ID"] for entry in entries}
    matrix = load_matrix()
    for claim in matrix["claims"]:
        for key in claim["evidence_keys"]:
            assert key in bib_keys, f"{claim['claim_id']} cites missing bibliography key {key}"

    claims = {claim["claim_id"]: claim for claim in matrix["claims"]}
    assert claims["C01"]["evidence_keys"]
    assert claims["C02"]["evidence_keys"]
    assert claims["C03"]["evidence_keys"]
    assert claims["C04"]["evidence_keys"]
    assert claims["C05"]["evidence_keys"]
    assert claims["C07"]["evidence_keys"] == []
    assert claims["C09"]["evidence_keys"]
    assert claims["C10"]["evidence_keys"] == ["guu2020realm"]
    assert claims["C11"]["evidence_keys"] == []
    assert claims["C12"]["evidence_keys"]


def test_source_assessments_capture_methods_and_limitations():
    entries = load_bib_entries()
    bib_keys = {entry["ID"] for entry in entries}
    matrix = load_matrix()
    assessments = {item.get("bib_key"): item for item in matrix["source_assessments"]}
    assert set(assessments) == bib_keys

    allowed_roles = {"core_architecture", "retrieval_method", "generation_method", "out_of_scope_context"}
    expected_role = {
        "lewis2020rag": "core_architecture",
        "guu2020realm": "core_architecture",
        "karpukhin2020dpr": "retrieval_method",
        "izacard2021fid": "generation_method",
        "gao2023hyde": "retrieval_method",
    }
    expected_terms = {
        "lewis2020rag": [["sequence", "seq2seq"], ["retrieval"], ["faithfulness", "faithful", "hallucination"]],
        "guu2020realm": ["pre-training", "latent", "retrieval"],
        "karpukhin2020dpr": ["dual", "supervised", "dataset"],
        "izacard2021fid": ["fusion", "generation", "coverage"],
        "gao2023hyde": ["zero-shot", "hypothetical", "domain"],
    }

    for key, assessment in assessments.items():
        assert assessment["scope_role"] in allowed_roles
        assert assessment["scope_role"] == expected_role[key]
        assert assessment["human_participants"] is False
        assert isinstance(assessment.get("research_design"), str) and len(assessment["research_design"].split()) >= 6
        assert isinstance(assessment.get("main_contribution"), str) and len(assessment["main_contribution"].split()) >= 6
        limitations = assessment.get("methodological_limitations")
        assert isinstance(limitations, list) and len(limitations) >= 2
        text = norm(" ".join([assessment["research_design"], assessment["main_contribution"], " ".join(limitations)]))
        for term_group in expected_terms[key]:
            terms = term_group if isinstance(term_group, list) else [term_group]
            assert any(term in text for term in terms)


def test_rejected_sources_cover_noise_records_with_reasons():
    rejected = load_matrix()["rejected_sources"]
    found = {}
    for item in rejected:
        marker = norm(item.get("input_key_or_title", ""))
        reason = item.get("reason")
        for expected_marker, expected_reason in REJECTED_MARKERS.items():
            if expected_marker in marker:
                found[expected_marker] = reason
                assert reason == expected_reason
    assert set(found) == set(REJECTED_MARKERS)


def test_literature_note_has_required_academic_synthesis():
    note = NOTE_PATH.read_text(encoding="utf-8")
    note_norm = norm(note)
    for section in [
        "## Research Question",
        "## Evidence Synthesis",
        "## Methodological Caveats",
        "## Research Gaps",
        "## References",
    ]:
        assert section in note

    bib_keys = {entry["ID"] for entry in load_bib_entries()}
    cited_keys = set(re.findall(r"\[([A-Za-z0-9_:-]+)\]", note))
    assert len(cited_keys & bib_keys) >= 5
    assert "open-domain" in note_norm
    assert "retrieval" in note_norm
    assert "benchmark" in note_norm or "evaluation" in note_norm
    assert "hallucination" in note_norm or "faithfulness" in note_norm
    assert "domain" in note_norm
    assert "retrieval-side" in note_norm or "retrieval side" in note_norm
    assert "generation-side" in note_norm or "generation side" in note_norm
    assert "evaluation-side" in note_norm or "evaluation side" in note_norm

    for fragment in FORBIDDEN_TITLE_FRAGMENTS:
        assert fragment not in note_norm
