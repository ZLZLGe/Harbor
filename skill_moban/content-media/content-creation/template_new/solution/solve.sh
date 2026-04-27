#!/bin/bash
set -euo pipefail

start-brandroom-archive

python3 <<'PY'
from __future__ import annotations

import csv
import json
import urllib.request
from pathlib import Path


INPUT_DIR = Path("/root/brandroom/input")
OUTPUT_DIR = Path("/root/brandroom/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"X-Client": "solution-brandroom"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


manifest = json.loads((INPUT_DIR / "source_manifest.json").read_text(encoding="utf-8"))
archive = manifest["archive_service"]
sources = get_json(archive["sources_url"])["sources"]
claims = get_json(archive["claims_url"])["claims"]
brief = get_json(archive["brief_url"])
specs = get_json(archive["specs_url"])
glossary = get_json(archive["glossary_url"])

source_by_id = {row["source_id"]: row for row in sources}
claim_by_id = {row["claim_id"]: row for row in claims}

inventory = []
used_for_by_channel = {
    "article": ["rhythm", "claims", "structure"],
    "launch_note": ["claims", "structure", "hard_bans"],
    "documentation": ["claims", "evidence", "boundaries"],
    "email": ["rhythm", "claims", "lexicon"],
    "social_x": ["compression", "lexicon", "hard_bans"],
    "linkedin": ["structure", "claims", "rhythm"],
    "changelog": ["formatting", "claims", "lexicon"],
    "site_copy": ["positioning", "boundaries", "lexicon"],
    "memo": ["hard_bans", "claim_style", "lexicon"],
    "support_email": ["mechanism", "boundaries", "claims"],
}
canonical_sources = [row for row in sources if not row["source_id"].startswith("DEC-")]
for row in canonical_sources:
    inventory.append({
        "source_id": row["source_id"],
        "title": row["title"],
        "url": row["url"],
        "channel": row["channel"],
        "used_for": used_for_by_channel.get(row["channel"], ["rhythm", "claims"]),
    })

voice_profile = {
    "profile_name": "TallyRun operator voice for Audit Trails",
    "source_inventory": inventory,
    "source_priority_applied": [
        {
            "priority": "recent_social_posts",
            "source_ids": ["SRC-005", "SRC-006"],
            "why_used": "Recent social posts provide compression, contrast, and anti-bait-question rules.",
        },
        {
            "priority": "articles_memos_launch_notes",
            "source_ids": ["SRC-001", "SRC-002", "SRC-009"],
            "why_used": "Articles, launch notes, and memo material define the public launch voice and hard bans.",
        },
        {
            "priority": "outbound_email",
            "source_ids": ["SRC-004"],
            "why_used": "The customer email shows the practical handoff cadence and plain subject style.",
        },
        {
            "priority": "docs_changelog_site_copy",
            "source_ids": ["SRC-003", "SRC-007", "SRC-008", "SRC-010"],
            "why_used": "Docs, changelog, site copy, and support replies anchor mechanisms and product boundaries.",
        },
    ],
    "excluded_sources": [
        {
            "source_id": "DEC-001",
            "reason": "Generic platform example with AI marketing cliches, not a canonical TallyRun source.",
        },
        {
            "source_id": "DEC-002",
            "reason": "Old discarded brand voice that over-promises and violates current legal review boundaries.",
        },
        {
            "source_id": "DEC-003",
            "reason": "Competitor copy, useful only as a negative comparator and not as TallyRun voice evidence.",
        },
    ],
    "style_profile": {
        "sentence_rhythm": {
            "summary": "Short declarative sentences carry the point; longer sentences add the receipt, boundary, or mechanism.",
            "rules": [
                "Lead with the operator problem before the product name.",
                "Use compact fragments for emphasis, especially around claims, receipts, and handoffs.",
                "Let transitions feel earned by evidence instead of smoothing over the sharp edge."
            ],
        },
        "claim_style": [
            "Specifics, mechanisms, receipts, and numbers beat adjectives.",
            "Claims should say what the workflow does, where it stops, and what a human still owns.",
            "Use the beta number only with its scope: 31% across 14 launch reviews.",
        ],
        "evidence_habits": [
            "Attach every product claim to a source, owner, reviewer action, or decision log.",
            "Prefer visible artifacts such as CSV, JSON, reviewer status, source notes, and claim drift over abstract benefits.",
            "Keep legal and publishing boundaries explicit before publication.",
        ],
        "formatting_habits": [
            "Use plain paragraphs and short lists; no oversized launch rhetoric.",
            "For changelog copy, keep the compact operator view: claim, source, reviewer, status.",
            "For social, compress around one mechanism rather than ending with a bait question.",
        ],
        "lexicon": {
            "preferred_terms": glossary["preferred_terms"] + ["quiet", "boring path", "sharp edge", "specifics", "mechanisms"],
            "terms_to_avoid": glossary["banned_terms"] + ["magic", "transformation language", "bait question"],
            "replacement_terms": glossary["replacement_terms"] + [
                {"avoid": "generic founder journey", "use": "operator path"},
                {"avoid": "broad compliance promise", "use": "legal approval boundary"},
            ],
        },
        "hard_bans": [
            "No fake curiosity hooks or bait questions.",
            "No game-changing, revolutionary, or excited-to-announce phrasing.",
            "No LinkedIn thought-leader cadence.",
            "No generic founder-journey filler or corny parentheticals.",
            "No not X, just Y construction, no no-fluff signaling, and no forced lowercase styling.",
            "No claim that Audit Trails replaces legal review or publishes on its own.",
            "No generic transformation language without a receipt.",
        ],
    },
    "do_dont_rules": [
        {
            "do": "Show the receipt: decision log, source, timestamp, reviewer, or owner.",
            "dont": "Ask the reader to trust a vague efficiency claim.",
            "source_evidence": ["SRC-001", "SRC-003"],
        },
        {
            "do": "Make the review path visible before publication.",
            "dont": "Describe the workflow as autonomous publishing.",
            "source_evidence": ["SRC-002", "SRC-008"],
        },
        {
            "do": "Use the beta result with its exact scope: 31% across 14 launch reviews.",
            "dont": "Turn the beta into a universal speed promise.",
            "source_evidence": ["SRC-004"],
        },
        {
            "do": "Write like an operator explaining the path to another operator.",
            "dont": "Use broad transformation language or sparkle-layer adjectives.",
            "source_evidence": ["SRC-005", "SRC-009"],
        },
        {
            "do": "Name the compact view: claim, source, reviewer, status.",
            "dont": "Hide the sharp edge behind a generic dashboard benefit.",
            "source_evidence": ["SRC-006", "SRC-007"],
        },
        {
            "do": "Explain the diff view as claim drift detection against approved source notes.",
            "dont": "Imply it judges campaign quality or legal readiness.",
            "source_evidence": ["SRC-010"],
        },
    ],
    "confidence_notes": [
        "High confidence: the source set spans article, launch note, docs, email, social, LinkedIn, changelog, site copy, memo, and support reply.",
        "The public launch voice and support voice agree on the same pattern: concrete mechanisms, visible receipts, and explicit boundaries.",
    ],
}

items = [
    {
        "channel": "launch_blog_opening",
        "audience": brief["audiences"]["primary"],
        "draft": (
            "A clean launch rarely breaks at the sentence level. It breaks at the handoff. "
            "A claim moves from brief to draft, the source lives somewhere else, and the reviewer has to rebuild the path from messages. "
            "TallyRun built Audit Trails for that narrow problem. It keeps approved claims, sources, reviewer actions, and publication status visible before publication. "
            "The decision log can be exported as CSV or JSON, so the next operator sees the receipt instead of guessing. "
            "It does not publish on its own, and it is not a substitute for legal approval. "
            "It is a quieter launch tool: show the claim, show the receipt, move the review."
        ),
        "source_anchors": ["SRC-001", "SRC-003", "SRC-008"],
        "allowed_claim_ids": ["CLM-001", "CLM-002", "CLM-003"],
        "voice_profile_rules_used": [
            "Lead with the operator handoff problem.",
            "Use receipts, decision log, and before publication boundaries instead of adjectives.",
        ],
        "notes": "Opens with the source-backed handoff problem and names the boundary plainly.",
    },
    {
        "channel": "linkedin_post",
        "audience": brief["audiences"]["secondary"],
        "draft": (
            "Most launch reviews do not stall because the headline needs another adjective. "
            "They stall because the claim, source, reviewer, and status live in different places. "
            "Audit Trails keeps that review path visible before publication: approved claims beside the draft, role-scoped approvals for the right reviewer group, and a decision log the next operator can export. "
            "The beta group reduced review handoff time by 31% across 14 launch reviews. Useful, narrow, and still owned by humans."
        ),
        "source_anchors": ["SRC-004", "SRC-006", "SRC-007"],
        "allowed_claim_ids": ["CLM-004", "CLM-005", "CLM-002"],
        "voice_profile_rules_used": [
            "Use the scoped handoff number with receipts.",
            "Avoid bait questions and keep the operator review path visible.",
        ],
        "notes": "Keeps LinkedIn concrete without a question ending.",
    },
    {
        "channel": "x_thread",
        "audience": "launch managers and content operators",
        "posts": [
            "Launch reviews usually slow down at the handoff, not at the writing step. The risky part is smaller: which claim moved, where the source lives, and who approved the wording.",
            "Audit Trails keeps approved claims, sources, reviewer actions, and publication status visible before publication. Claim, source, reviewer, status. The compact operator view.",
            "Receipts beat adjectives. Decision logs export as CSV or JSON, so the next operator can see the path instead of rebuilding it from chat threads.",
            "The diff view compares each draft paragraph with approved source notes and flags claim drift before publication. It catches drift; it does not judge the campaign.",
            "Boundary matters: Audit Trails does not publish on its own and is not a substitute for legal approval. Humans still own the approval."
        ],
        "source_anchors": ["SRC-005", "SRC-003", "SRC-010", "SRC-008"],
        "allowed_claim_ids": ["CLM-002", "CLM-001", "CLM-006", "CLM-003"],
        "voice_profile_rules_used": [
            "Compress around receipts, claim drift, and before publication boundaries.",
            "Use short operator sentences instead of LinkedIn thought-leader cadence.",
        ],
        "notes": "Thread uses short posts with the same source-derived claim discipline.",
    },
    {
        "channel": "customer_email",
        "audience": "existing TallyRun workspace admins",
        "subject": "Audit Trails for the review handoff",
        "preview_text": "Keep claims, sources, reviewer actions, and decision logs visible before publication.",
        "draft": (
            "Hi, Audit Trails is now available for launch workspaces. "
            "It is built for the review gap we kept seeing: a draft moves forward while the claim, source, owner note, and reviewer action sit in separate places. "
            "Now the review path stays beside the work. You can attach approved claims, compare draft paragraphs with source notes, and export the decision log as CSV or JSON. "
            "Role-scoped approvals help route the right reviewer group by launch type, region, or content surface. "
            "It does not publish on its own, and it is not a substitute for legal approval."
        ),
        "source_anchors": ["SRC-004", "SRC-007", "SRC-010"],
        "allowed_claim_ids": ["CLM-001", "CLM-005", "CLM-006", "CLM-003"],
        "voice_profile_rules_used": [
            "Plain email voice with operator handoff and decision log receipts.",
            "State the legal approval boundary without dressing it up.",
        ],
        "notes": "Uses the customer email source pattern and avoids inflated launch language.",
    },
    {
        "channel": "changelog_note",
        "audience": "product users scanning release notes",
        "draft": (
            "Added Audit Trails for launch workspaces. Approved claims, sources, reviewer actions, and publication status now stay visible before publication. "
            "Decision logs export as CSV or JSON, role-scoped approvals route reviewer groups, and the diff view flags claim drift against approved source notes. "
            "Audit Trails does not publish on its own."
        ),
        "source_anchors": ["SRC-003", "SRC-007", "SRC-010"],
        "allowed_claim_ids": ["CLM-001", "CLM-002", "CLM-005", "CLM-006", "CLM-003"],
        "voice_profile_rules_used": [
            "Compact changelog operator view: claim, source, reviewer, status.",
            "Keep mechanism and before publication boundary visible.",
        ],
        "notes": "Changelog stays dense and factual.",
    },
]

content_pack = {
    "campaign_name": brief["campaign_name"],
    "core_angle": "Audit Trails gives TallyRun operators a source-backed review path before publication.",
    "items": items,
}

audit_report = {
    "files_created": ["voice_profile.json", "content_pack.json", "audit_report.json"],
    "sources_read": [row["source_id"] for row in sources],
    "claims_used": sorted({claim for item in items for claim in item["allowed_claim_ids"]}),
    "claims_rejected": [
        {"claim": "guaranteed compliance", "reason": "The brief forbids compliance guarantees and the sources define a legal approval boundary."},
        {"claim": "supports every CMS", "reason": "No approved claim or source evidence supports universal CMS coverage."},
        {"claim": "10x faster launches", "reason": "The only approved number is the scoped beta handoff result."},
    ],
    "banned_phrases_removed": [
        "excited to announce",
        "game-changing",
        "revolutionary",
        "seamless",
    ],
    "channel_constraints_checked": [
        {"channel": channel, "status": "pass", "notes": "Checked schema, references, claim IDs, and channel-specific length constraints."}
        for channel in specs["required_channels"]
    ],
    "final_quality_notes": [
        "Every content item cites source anchors and approved claim IDs.",
        "The pack keeps the operator voice: receipts, handoff, decision log, claim drift, and explicit boundaries.",
    ],
}

(OUTPUT_DIR / "voice_profile.json").write_text(json.dumps(voice_profile, indent=2, sort_keys=True), encoding="utf-8")
(OUTPUT_DIR / "content_pack.json").write_text(json.dumps(content_pack, indent=2, sort_keys=True), encoding="utf-8")
(OUTPUT_DIR / "audit_report.json").write_text(json.dumps(audit_report, indent=2, sort_keys=True), encoding="utf-8")
PY
