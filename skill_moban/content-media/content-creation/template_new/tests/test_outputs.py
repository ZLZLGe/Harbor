from __future__ import annotations

import csv
import json
import re
from pathlib import Path


INPUT_DIR = Path("/root/brandroom/input")
OUTPUT_DIR = Path("/root/brandroom/output")
VOICE_PATH = OUTPUT_DIR / "voice_profile.json"
PACK_PATH = OUTPUT_DIR / "content_pack.json"
AUDIT_PATH = OUTPUT_DIR / "audit_report.json"

REQUIRED_CHANNELS = {
    "launch_blog_opening",
    "linkedin_post",
    "x_thread",
    "customer_email",
    "changelog_note",
}

GENERIC_PHRASES = [
    "clear and concise",
    "friendly and professional",
    "engaging and informative",
    "compelling content",
    "tailored to the audience",
    "brand personality",
]

BANNED_PHRASES = [
    "in today's rapidly evolving landscape",
    "rapidly evolving landscape",
    "game-changing",
    "revolutionary",
    "excited to announce",
    "unlock your potential",
    "no fluff",
    "seamless",
    "ai-powered",
    "not x, just y",
]

FORBIDDEN_CLAIMS = [
    "guaranteed compliance",
    "replaces legal review",
    "supports every cms",
    "10x",
    "fully autonomous publishing",
    "automatically sends campaigns",
]

VOICE_TERMS = [
    "operator",
    "handoff",
    "runbook",
    "decision log",
    "receipt",
    "receipts",
    "review path",
    "before publication",
    "claim drift",
    "quiet",
    "boring",
    "sharp edge",
    "specifics",
    "mechanisms",
]


def load_json(path: Path) -> dict:
    assert path.exists(), f"Missing {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def load_sources() -> dict[str, dict]:
    sources = {}
    with (INPUT_DIR / "source_corpus.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                row = json.loads(line)
                sources[row["source_id"]] = row
    return sources


def load_claims() -> dict[str, dict]:
    with (INPUT_DIR / "allowed_claims.csv").open(newline="", encoding="utf-8") as fh:
        return {row["claim_id"]: row for row in csv.DictReader(fh)}


def all_pack_text(pack: dict) -> str:
    parts = [pack.get("campaign_name", ""), pack.get("core_angle", "")]
    for item in pack.get("items", []):
        parts.extend(str(item.get(key, "")) for key in ["draft", "subject", "preview_text"])
        parts.extend(str(post) for post in item.get("posts", []))
    return "\n".join(parts)


def word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?", text))


def assert_valid_refs(ids: list[str], allowed: set[str], label: str) -> None:
    assert isinstance(ids, list) and ids, f"{label} must be a non-empty list"
    bad = sorted(set(ids) - allowed)
    assert not bad, f"Unknown {label}: {bad}"


def test_output_files_exist_and_parse() -> None:
    voice = load_json(VOICE_PATH)
    pack = load_json(PACK_PATH)
    audit = load_json(AUDIT_PATH)
    assert isinstance(voice, dict)
    assert isinstance(pack, dict)
    assert isinstance(audit, dict)
    assert audit.get("files_created") == ["voice_profile.json", "content_pack.json", "audit_report.json"]


def test_voice_profile_is_source_backed_and_operational() -> None:
    voice = load_json(VOICE_PATH)
    sources = load_sources()
    source_ids = set(sources)

    inventory = voice.get("source_inventory")
    assert isinstance(inventory, list) and len(inventory) >= 8, "source_inventory must cover at least 8 source samples"
    inventory_ids = {entry.get("source_id") for entry in inventory}
    assert inventory_ids <= source_ids
    assert len(inventory_ids) >= 8
    decoys = {sid for sid in source_ids if sid.startswith("DEC-")}
    assert not (inventory_ids & decoys), f"source_inventory must exclude comparator sources: {sorted(inventory_ids & decoys)}"

    channels = {entry.get("channel") for entry in inventory}
    assert {"article", "launch_note", "documentation", "email", "social_x", "linkedin", "changelog"} <= channels
    for entry in inventory:
        assert entry.get("title")
        assert entry.get("url", "").startswith("https://")
        used_for = entry.get("used_for")
        assert isinstance(used_for, list) and used_for

    priority = voice.get("source_priority_applied")
    assert isinstance(priority, list) and len(priority) >= 4, "source_priority_applied must group sources by priority"
    by_priority = {entry.get("priority"): entry for entry in priority}
    expected_priorities = {
        "recent_social_posts": {"SRC-005", "SRC-006"},
        "articles_memos_launch_notes": {"SRC-001", "SRC-002", "SRC-009"},
        "outbound_email": {"SRC-004"},
        "docs_changelog_site_copy": {"SRC-003", "SRC-007", "SRC-008", "SRC-010"},
    }
    assert set(by_priority) >= set(expected_priorities)
    for label, required_ids in expected_priorities.items():
        entry = by_priority[label]
        cited = set(entry.get("source_ids", []))
        assert cited <= source_ids, f"{label} contains unknown source IDs"
        assert not (cited & decoys), f"{label} includes comparator sources"
        if label == "docs_changelog_site_copy":
            assert len(cited & required_ids) >= 3, f"{label} missing priority sources"
        else:
            assert required_ids <= cited, f"{label} missing priority sources"
        assert isinstance(entry.get("why_used"), str) and len(entry["why_used"].split()) >= 5

    excluded = voice.get("excluded_sources")
    assert isinstance(excluded, list) and len(excluded) >= 3
    excluded_ids = {entry.get("source_id") for entry in excluded}
    assert decoys <= excluded_ids
    excluded_text = json.dumps(excluded, ensure_ascii=False).lower()
    assert "generic" in excluded_text
    assert any(term in excluded_text for term in ["old", "discarded", "retired", "legacy"])
    assert "competitor" in excluded_text

    style = voice.get("style_profile")
    assert isinstance(style, dict)
    for key in ["claim_style", "evidence_habits", "formatting_habits", "hard_bans"]:
        assert isinstance(style.get(key), list) and len(style[key]) >= 2, f"{key} needs concrete rules"
    hard_bans_text = " ".join(style.get("hard_bans", [])).lower()
    anti_patterns = [
        "fake curiosity",
        "bait question",
        "linkedin thought",
        "generic founder",
        "corny parenthetical",
        "not x, just y",
        "no fluff",
        "forced lowercase",
        "excited to share",
    ]
    assert sum(pattern in hard_bans_text for pattern in anti_patterns) >= 5, "hard_bans must name reusable voice anti-patterns"
    rhythm = style.get("sentence_rhythm")
    assert isinstance(rhythm, dict)
    assert rhythm.get("summary") and isinstance(rhythm.get("rules"), list) and len(rhythm["rules"]) >= 2
    lexicon = style.get("lexicon")
    assert isinstance(lexicon, dict)
    assert len(lexicon.get("preferred_terms", [])) >= 6
    assert len(lexicon.get("terms_to_avoid", [])) >= 5
    assert len(lexicon.get("replacement_terms", [])) >= 3

    rules = voice.get("do_dont_rules")
    assert isinstance(rules, list) and len(rules) >= 4
    for rule in rules:
        assert rule.get("do") and rule.get("dont")
        assert_valid_refs(rule.get("source_evidence"), source_ids, "source_evidence")

    combined = json.dumps(voice, ensure_ascii=False).lower()
    assert sum(term in combined for term in VOICE_TERMS) >= 8, "voice profile does not reflect the source corpus voice"
    assert sum(phrase in combined for phrase in GENERIC_PHRASES) <= 1, "voice profile is too generic"
    assert len(voice.get("confidence_notes", [])) >= 2


def test_content_pack_channels_and_references() -> None:
    voice = load_json(VOICE_PATH)
    pack = load_json(PACK_PATH)
    sources = load_sources()
    claims = load_claims()
    source_ids = set(sources)
    claim_ids = set(claims)

    assert pack.get("campaign_name") == "Audit Trails public launch"
    assert "Audit Trails" in (pack.get("campaign_name", "") + " " + all_pack_text(pack))
    items = pack.get("items")
    assert isinstance(items, list) and len(items) == len(REQUIRED_CHANNELS)
    by_channel = {item.get("channel"): item for item in items}
    assert set(by_channel) == REQUIRED_CHANNELS

    profile_text = json.dumps(voice, ensure_ascii=False).lower()
    for channel, item in by_channel.items():
        assert item.get("audience")
        assert_valid_refs(item.get("source_anchors"), source_ids, f"{channel} source_anchors")
        assert len(set(item["source_anchors"])) >= 2, f"{channel} needs at least two distinct source anchors"
        assert_valid_refs(item.get("allowed_claim_ids"), claim_ids, f"{channel} allowed_claim_ids")
        assert item.get("voice_profile_rules_used"), f"{channel} must link to voice profile rules"
        rules_text = " ".join(item["voice_profile_rules_used"]).lower()
        assert any(term in profile_text for term in rules_text.split() if len(term) > 6), f"{channel} rules are not connected to profile"

    assert 90 <= word_count(by_channel["launch_blog_opening"]["draft"]) <= 170
    assert "TallyRun" in by_channel["launch_blog_opening"]["draft"]
    assert "Audit Trails" in by_channel["launch_blog_opening"]["draft"]

    linkedin = by_channel["linkedin_post"]["draft"]
    assert 60 <= word_count(linkedin) <= 130
    assert not linkedin.strip().endswith("?"), "LinkedIn post must not end with a bait question"

    posts = by_channel["x_thread"].get("posts")
    assert isinstance(posts, list) and 4 <= len(posts) <= 6
    assert all(isinstance(post, str) and 30 <= len(post) <= 280 for post in posts)

    email = by_channel["customer_email"]
    assert email.get("subject") and len(email["subject"]) <= 72
    assert email.get("preview_text") and len(email["preview_text"]) <= 110
    assert 70 <= word_count(email["draft"]) <= 140

    assert 35 <= word_count(by_channel["changelog_note"]["draft"]) <= 90


def test_claim_safety_and_voice_quality() -> None:
    pack = load_json(PACK_PATH)
    text = all_pack_text(pack)
    lower = text.lower()

    for phrase in BANNED_PHRASES:
        assert phrase not in lower, f"banned generic phrase present: {phrase}"
    for claim in FORBIDDEN_CLAIMS:
        assert claim not in lower, f"forbidden claim present: {claim}"

    allowed_numbers = {"31", "14"}
    seen_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", text))
    assert seen_numbers <= allowed_numbers, f"unsupported numeric claims present: {sorted(seen_numbers - allowed_numbers)}"

    assert sum(term in lower for term in VOICE_TERMS) >= 6, "content does not reuse the source-derived voice"
    assert lower.count("audit trails") >= 4
    assert lower.count("before publication") >= 2
    assert "not a substitute for legal approval" in lower or "not a legal engine" in lower
    assert "does not publish on its own" in lower


def test_audit_report_covers_sources_claims_and_constraints() -> None:
    audit = load_json(AUDIT_PATH)
    sources = load_sources()
    claims = load_claims()

    assert_valid_refs(audit.get("sources_read"), set(sources), "sources_read")
    assert len(set(audit["sources_read"])) >= 8
    assert_valid_refs(audit.get("claims_used"), set(claims), "claims_used")
    assert len(set(audit["claims_used"])) >= 4

    rejected = audit.get("claims_rejected")
    assert isinstance(rejected, list) and len(rejected) >= 2
    rejected_text = json.dumps(rejected, ensure_ascii=False).lower()
    assert "legal" in rejected_text or "compliance" in rejected_text
    assert "cms" in rejected_text or "10x" in rejected_text or "autonomous" in rejected_text

    removed = audit.get("banned_phrases_removed")
    assert isinstance(removed, list) and len(removed) >= 3
    assert any("excited" in item.lower() for item in removed)
    assert any("game" in item.lower() or "revolutionary" in item.lower() for item in removed)

    checks = audit.get("channel_constraints_checked")
    assert isinstance(checks, list) and len(checks) >= 5
    checked_channels = {check.get("channel") for check in checks}
    assert REQUIRED_CHANNELS <= checked_channels
    assert all(check.get("status") == "pass" for check in checks)
    assert len(audit.get("final_quality_notes", [])) >= 2
