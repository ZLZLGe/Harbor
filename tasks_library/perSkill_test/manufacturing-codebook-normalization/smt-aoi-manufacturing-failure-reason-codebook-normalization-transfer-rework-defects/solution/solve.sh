#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
import csv
import json
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
OUT_DIR = os.environ.get("OUT_DIR", "/app/output")

CASES_PATH = os.path.join(DATA_DIR, "aoi_cases.jsonl")
CODEBOOK_PATH = os.path.join(DATA_DIR, "aoi_defect_codebook.csv")
OUT_PATH = os.path.join(OUT_DIR, "aoi_defect_map.json")

os.makedirs(OUT_DIR, exist_ok=True)

TOKEN_RE = re.compile(r"[^a-z0-9\u4e00-\u9fff]+", re.IGNORECASE)
COMP_RE = re.compile(r"\b([A-Z]{1,3}\d{1,4})\b", re.IGNORECASE)
SPLIT_RE = re.compile(r"\s*(?:;|；|\+|\band\b)\s*", re.IGNORECASE)


def norm_text(text: str) -> str:
    return (text or "").strip()


def lower_text(text: str) -> str:
    return norm_text(text).lower()


def token_set(text: str) -> Set[str]:
    return {p for p in TOKEN_RE.split(lower_text(text)) if p}


def jaccard(a: Set[str], b: Set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def split_segments(text: str) -> List[str]:
    raw = norm_text(text)
    if not raw:
        return [""]
    parts = [p.strip() for p in SPLIT_RE.split(raw) if p and p.strip()]
    return parts or [raw]


@dataclass(frozen=True)
class Entry:
    code: str
    label: str
    category: str
    allowed_stages: Set[str]
    keywords: List[str]
    token_bank: Set[str]


def load_codebook() -> Dict[str, Entry]:
    out: Dict[str, Entry] = {}
    with open(CODEBOOK_PATH, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            code = norm_text(row.get("code"))
            label = norm_text(row.get("standard_label"))
            category = norm_text(row.get("category"))
            allowed = {x.strip() for x in norm_text(row.get("allowed_stages")).split(";") if x.strip()}
            keywords = [x.strip().lower() for x in norm_text(row.get("keywords_examples")).split(",") if x.strip()]
            token_bank = token_set(label + " " + " ".join(keywords) + " " + category)
            out[code] = Entry(code, label, category, allowed, keywords, token_bank)
    return out


def score_entry(entry: Entry, stage: str, span: str) -> Tuple[float, Optional[str]]:
    if stage not in entry.allowed_stages:
        return -1.0, None

    span_l = lower_text(span)
    span_tokens = token_set(span)

    phrase_hits = [kw for kw in entry.keywords if kw and kw in span_l]
    token_score = jaccard(span_tokens, entry.token_bank)
    score = len(phrase_hits) * 0.75 + token_score * 0.6
    cue = phrase_hits[0] if phrase_hits else None
    return score, cue


def calibrate(score: float, known: bool) -> float:
    if not known:
        return round(min(0.55, 0.34 + max(score, 0.0) * 0.08), 4)
    return round(min(0.96, 0.62 + score * 0.11), 4)


def rationale(stage: str, span: str, code: str, cue: Optional[str], score: float) -> str:
    bits = [f"stage={stage}"]
    comp = COMP_RE.search(span or "")
    if comp:
        bits.append(f"comp={comp.group(1).upper()}")
    if cue:
        bits.append(f"cue={cue}")
    if code != "UNKNOWN":
        bits.append(f"code={code}")
    bits.append(f"score={score:.3f}")
    return " | ".join(bits)


codebook = load_codebook()

boards = []
with open(CASES_PATH, "r", encoding="utf-8") as f:
    for line in f:
        if norm_text(line):
            boards.append(json.loads(line))

result = {"boards": []}

for board in boards:
    board_id = norm_text(board.get("board_id"))
    stage = norm_text(board.get("process_stage"))
    remark = norm_text(board.get("remark_text"))
    spans = split_segments(remark)
    defects = []

    for idx, span in enumerate(spans, start=1):
        best_entry = None
        best_score = -1.0
        best_cue = None

        for entry in codebook.values():
            score, cue = score_entry(entry, stage, span)
            if score > best_score:
                best_entry = entry
                best_score = score
                best_cue = cue

        if best_entry is None or best_score < 0.72:
            pred_code = "UNKNOWN"
            pred_label = ""
            confidence = calibrate(best_score, False)
            rat = rationale(stage, span, pred_code, best_cue, max(best_score, 0.0))
        else:
            pred_code = best_entry.code
            pred_label = best_entry.label
            confidence = calibrate(best_score, True)
            rat = rationale(stage, span, pred_code, best_cue, best_score)

        defects.append(
            {
                "segment_id": f"{board_id}-S{idx}",
                "span_text": span,
                "pred_code": pred_code,
                "pred_label": pred_label,
                "confidence": confidence,
                "rationale": rat,
            }
        )

    result["boards"].append(
        {
            "board_id": board_id,
            "panel_id": norm_text(board.get("panel_id")),
            "product_family": norm_text(board.get("product_family")),
            "process_stage": stage,
            "line": norm_text(board.get("line")),
            "side": norm_text(board.get("side")),
            "operator_id": norm_text(board.get("operator_id")),
            "remark_text": remark,
            "defect_segments": defects,
        }
    )

with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
PY
