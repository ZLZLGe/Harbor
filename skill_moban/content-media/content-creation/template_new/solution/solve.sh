#!/bin/bash
set -euo pipefail

cat > /app/workspace/build_content_pack.py <<'PY'
#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


OUTPUT_ORDER = [
    "core_angle.md",
    "x_thread.md",
    "linkedin_post.md",
    "newsletter.md",
    "short_video_script.md",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", required=True)
    parser.add_argument("--output-root", required=True)
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_brief(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if not match:
        raise SystemExit("project_brief.md is missing the JSON contract block")
    return json.loads(match.group(1))


def claim_map(catalog: dict) -> dict[str, dict]:
    return {claim["id"]: claim for claim in catalog["claims"]}


def first_sentence(text: str) -> str:
    sentence = text.split(".")[0].strip()
    return sentence + "." if sentence and not sentence.endswith(".") else sentence


def first_meaningful_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        return stripped
    return ""


def union_sources(claims: list[dict]) -> list[str]:
    ordered = ["brief/project_brief.md", "brief/source_packet.md", "data/claim_catalog.json"]
    seen = set(ordered)
    for claim in claims:
        for source in claim["source_files"]:
            if source not in seen:
                ordered.append(source)
                seen.add(source)
    return ordered


def build_core_angle(brief: dict, claims: list[dict]) -> str:
    return "\n".join(
        [
            "# Core Angle",
            "",
            "Primary angle:",
            brief["primary_angle"],
            "",
            "Audience hook:",
            "For operators and strategists, the regional average hides three different system stories. "
            + " ".join(claim["statement"] for claim in claims),
            "",
            "Claims in scope:",
            *[f"- {claim['id']}" for claim in claims],
            "",
            "Why this pack works:",
            "Canada gives the clean-share lead, Mexico gives the gas-heavy counterpoint, and the United States supplies the scale line that keeps the regional comparison grounded.",
            "",
        ]
    )


def build_x_thread(claims: list[dict]) -> str:
    openers = [
        "Canada is the clean-share outlier in this North America snapshot.",
        "Canada's mix also has a source line that explains why the clean-share lead holds.",
        "Mexico is the regional counterpoint if you look at fuel dependence.",
        "The emissions line keeps the story broader than power mix alone.",
        "The United States changes the picture once you switch from share to scale.",
    ]
    closers = [
        "That is the clearest opening contrast in the set.",
        "It anchors the clean-share story in a source the reader can picture.",
        "It is the sharpest gas-reliance signal in the three-country comparison.",
        "It adds a system-wide contrast that belongs in the same package.",
        "Clean-share lag and clean-power scale can both be true at once.",
    ]
    lines = []
    for idx, claim in enumerate(claims, start=1):
        lines.append(f"{idx}. {openers[idx - 1]} {claim['statement']} {closers[idx - 1]}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def build_linkedin_post(claims: list[dict]) -> str:
    return "\n".join(
        [
            "Headline: North America is running three different power stories at once",
            "",
            "If you flatten the region into one average, you miss the point. "
            + claims[0]["statement"],
            "",
            claims[1]["statement"] + " " + claims[1]["why_it_matters"],
            "",
            claims[2]["statement"] + " That scale point is what turns the comparison from a niche power mix note into an operations story.",
            "",
            "Question to carry forward: when your planning model says North America, which of these three grid stories is it actually describing?",
            "",
        ]
    )


def build_newsletter(claims: list[dict]) -> str:
    gdp_claim, clean_share_claim, gas_claim, co2_claim, scale_claim = claims
    return "\n".join(
        [
            "Subject: Three grid stories are hiding inside one North America headline",
            "Preview: Canada leans clean, Mexico leans gas, and the United States still operates at a different order of magnitude.",
            "",
            "The latest snapshot works best when you resist the regional average. "
            + gdp_claim["statement"],
            "",
            "## 1. The clean-share leader",
            clean_share_claim["statement"] + " " + clean_share_claim["why_it_matters"],
            "",
            "## 2. The gas-heavy counterpoint",
            gas_claim["statement"] + " " + gas_claim["why_it_matters"],
            "",
            "## 3. The scale line you still need",
            scale_claim["statement"] + " " + co2_claim["statement"],
            "",
            "If this comparison belongs in your watchlist, keep an eye on whether future releases narrow the clean-share gap or deepen the split.",
            "",
        ]
    )


def build_video_script(claims: list[dict]) -> str:
    clean_share_claim, gas_claim, co2_claim, scale_claim = claims
    beats = [
        (
            "Map of North America with three callouts.",
            "One region on a map can still hold three very different power stories in the latest data.",
        ),
        (
            clean_share_claim["visual"],
            clean_share_claim["statement"],
        ),
        (
            gas_claim["visual"],
            gas_claim["statement"],
        ),
        (
            co2_claim["visual"],
            co2_claim["statement"],
        ),
        (
            scale_claim["visual"],
            scale_claim["statement"],
        ),
        (
            "Closing comparison slide with three summary labels.",
            "Put together, the clean-share lead, the gas-heavy counterpoint, and the U.S. scale line are the comparison to watch.",
        ),
    ]
    lines = []
    for idx, (visual, line) in enumerate(beats, start=1):
        lines.append(f"{idx}.")
        lines.append(f"Visual: {visual}")
        lines.append(f"Line: {line}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def write_output(path: Path, text: str) -> None:
    path.write_text(text.strip() + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    input_root = Path(args.input_root)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    brief = parse_brief(input_root / "brief" / "project_brief.md")
    catalog = load_json(input_root / "data" / "claim_catalog.json")
    claims = claim_map(catalog)

    outputs: dict[str, str] = {}
    outputs["core_angle.md"] = build_core_angle(brief, [claims[claim_id] for claim_id in brief["required_claims_by_output"]["core_angle.md"]])
    outputs["x_thread.md"] = build_x_thread([claims[claim_id] for claim_id in brief["required_claims_by_output"]["x_thread.md"]])
    outputs["linkedin_post.md"] = build_linkedin_post([claims[claim_id] for claim_id in brief["required_claims_by_output"]["linkedin_post.md"]])
    outputs["newsletter.md"] = build_newsletter([claims[claim_id] for claim_id in brief["required_claims_by_output"]["newsletter.md"]])
    outputs["short_video_script.md"] = build_video_script([claims[claim_id] for claim_id in brief["required_claims_by_output"]["short_video_script.md"]])

    for filename, body in outputs.items():
        write_output(output_root / filename, body)

    manifest_outputs = []
    ctas = {
        "core_angle.md": "",
        "x_thread.md": "Close with a question that invites comparison.",
        "linkedin_post.md": "End with a planning question for readers.",
        "newsletter.md": "Invite the reader to keep the comparison on their watchlist.",
        "short_video_script.md": "Close with a short synthesis line.",
    }
    platforms = {
        "core_angle.md": "strategy-note",
        "x_thread.md": "x-thread",
        "linkedin_post.md": "linkedin-post",
        "newsletter.md": "newsletter",
        "short_video_script.md": "short-video-script",
    }
    for filename in OUTPUT_ORDER:
        required = [claims[claim_id] for claim_id in brief["required_claims_by_output"][filename]]
        if filename == "linkedin_post.md":
            opening_line = first_meaningful_line(outputs[filename].split("\n", 1)[1])
        elif filename == "newsletter.md":
            opening_line = first_meaningful_line(outputs[filename].split("Preview:", 1)[1])
        elif filename == "short_video_script.md":
            opening_line = next((line.strip() for line in outputs[filename].splitlines() if line.strip().startswith("Line:")), "")
        else:
            opening_line = first_sentence(first_meaningful_line(outputs[filename]))
        manifest_outputs.append(
            {
                "file": filename,
                "platform": platforms[filename],
                "claim_ids": brief["required_claims_by_output"][filename],
                "source_files": union_sources(required),
                "opening_line": opening_line,
                "cta": ctas[filename],
            }
        )

    manifest = {
        "campaign_slug": brief["campaign_slug"],
        "publisher": brief["publisher"],
        "audience": brief["audience"],
        "primary_angle": brief["primary_angle"],
        "key_years": catalog["metric_years"],
        "source_files": brief["source_files"],
        "outputs": manifest_outputs,
        "notes": [
            "All public-facing drafts are grounded in the bundled claim catalog.",
            "Claim ids are kept in the manifest and left out of the public drafts.",
        ],
    }
    (output_root / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY

chmod 755 /app/workspace/build_content_pack.py
python3 /app/workspace/build_content_pack.py --input-root /app/input --output-root /app/output
