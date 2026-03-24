#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
import csv
import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Set, Tuple

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
OUT_DIR = os.environ.get("OUT_DIR", "/app/output")
os.makedirs(OUT_DIR, exist_ok=True)

LOTS_PATH = os.path.join(DATA_DIR, "iqc_supplier_lots.csv")
CODEBOOK_PATH = os.path.join(DATA_DIR, "material_defect_codebook.json")
OUT_PATH = os.path.join(OUT_DIR, "iqc_supplier_reason_map.json")
UNKNOWN = "UNKNOWN"

TOKEN_RE = re.compile(r"[^a-z0-9\u4e00-\u9fff\+\.-]+", re.IGNORECASE)
SPLIT_RE = re.compile(r"\s*[;；]+\s*")


def s(value: Any) -> str:
    return "" if value is None else str(value).strip()


def token_set(text: str) -> Set[str]:
    return {part for part in TOKEN_RE.split(s(text).lower()) if part}


def jaccard(left: Set[str], right: Set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def clip(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


@dataclass(frozen=True)
class Entry:
    code: str
    label: str
    categories: Set[str]
    stages: Set[str]
    keyword_phrases: Tuple[str, ...]
    keywords: Set[str]
    label_tokens: Set[str]


def load_entries() -> List[Entry]:
    with open(CODEBOOK_PATH, "r", encoding="utf-8") as f:
        payload = json.load(f)
    out: List[Entry] = []
    for row in payload["entries"]:
        out.append(
            Entry(
                code=row["code"],
                label=row["standard_label"],
                categories={s(x) for x in row["allowed_categories"] if s(x)},
                stages={s(x) for x in row["allowed_stages"] if s(x)},
                keyword_phrases=tuple(s(x).lower() for x in row.get("keywords", []) if s(x)),
                keywords=token_set(" ".join(row.get("keywords", []))),
                label_tokens=token_set(row["standard_label"]),
            )
        )
    return out


def load_lots() -> List[Dict[str, str]]:
    with open(LOTS_PATH, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def split_segments(text: str) -> List[str]:
    parts = [part.strip() for part in SPLIT_RE.split(s(text)) if part.strip()]
    return parts if parts else [s(text)]


def category_ok(entry: Entry, category: str) -> bool:
    return category in entry.categories


def stage_ok(entry: Entry, stage: str) -> bool:
    return stage in entry.stages


def score_entry(entry: Entry, category: str, stage: str, segment: str, lot_hint: str) -> Tuple[float, Dict[str, Any]]:
    seg_tokens = token_set(segment)
    segment_lower = s(segment).lower()
    key_overlap = jaccard(seg_tokens, entry.keywords)
    label_overlap = jaccard(seg_tokens, entry.label_tokens)
    phrase_hits = sum(1 for phrase in entry.keyword_phrases if phrase and phrase in segment_lower)
    phrase_overlap = phrase_hits / max(1, len(entry.keyword_phrases))
    category_hit = 1.0 if category_ok(entry, category) else 0.0
    stage_hit = 1.0 if stage_ok(entry, stage) else 0.0
    lot_boost = 1.0 if lot_hint == entry.code else 0.0

    score = (
        0.35 * key_overlap
        + 0.28 * phrase_overlap
        + 0.10 * label_overlap
        + 0.17 * category_hit
        + 0.10 * stage_hit
        + 0.05 * lot_boost
    )
    return clip(score), {
        "key_overlap": key_overlap,
        "phrase_overlap": phrase_overlap,
        "label_overlap": label_overlap,
        "category_hit": category_hit,
        "stage_hit": stage_hit,
        "lot_boost": lot_boost,
    }


def base_known_code(segment: str, category: str, stage: str, entries: List[Entry]) -> str:
    scored: List[Tuple[float, str]] = []
    for entry in entries:
        if not category_ok(entry, category):
            continue
        if not stage_ok(entry, stage):
            continue
        score, _ = score_entry(entry, category, stage, segment, "")
        scored.append((score, entry.code))
    scored.sort(reverse=True)
    if not scored:
        return ""
    best_score, best_code = scored[0]
    if best_score < 0.40:
        return ""
    return best_code


def build_lot_hints(rows: List[Dict[str, str]], entries: List[Entry]) -> Dict[str, str]:
    hints: Dict[str, Dict[str, int]] = {}
    for row in rows:
        lot = s(row["supplier_lot"])
        category = s(row["item_category"])
        stage = s(row["inspection_stage"])
        for segment in split_segments(row["defect_remark"]):
            code = base_known_code(segment, category, stage, entries)
            if not code:
                continue
            hints.setdefault(lot, {})
            hints[lot][code] = hints[lot].get(code, 0) + 1

    resolved: Dict[str, str] = {}
    for lot, counts in hints.items():
        ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        if ranked and ranked[0][1] >= 1:
            resolved[lot] = ranked[0][0]
    return resolved


def calibrate_confidence(score: float, unknown: bool) -> float:
    if unknown:
        return round(clip(0.26 + 0.36 * score, 0.0, 0.54), 4)
    return round(clip(0.63 + 0.30 * score, 0.63, 0.97), 4)


def build_rationale(category: str, stage: str, lot: str, code: str, metrics: Dict[str, Any]) -> str:
    bits = [
        f"category={category}",
        f"stage={stage}",
        f"lot={lot}",
    ]
    if code != UNKNOWN:
        bits.append(f"code={code}")
    bits.append(f"kw={metrics['key_overlap']:.3f}")
    bits.append(f"phrase={metrics['phrase_overlap']:.3f}")
    if metrics["lot_boost"] > 0:
        bits.append("lot_hint=1")
    return " | ".join(bits)


entries = load_entries()
rows = load_lots()
lot_hints = build_lot_hints(rows, entries)
label_map = {entry.code: entry.label for entry in entries}

lots_out = []
for row in rows:
    inspection_id = s(row["inspection_id"])
    category = s(row["item_category"])
    stage = s(row["inspection_stage"])
    lot = s(row["supplier_lot"])
    segments_out = []

    for index, segment in enumerate(split_segments(row["defect_remark"]), start=1):
        ranked: List[Tuple[float, Entry, Dict[str, Any]]] = []
        for entry in entries:
            score, metrics = score_entry(entry, category, stage, segment, lot_hints.get(lot, ""))
            ranked.append((score, entry, metrics))
        ranked.sort(key=lambda item: (item[0], item[2]["key_overlap"], item[1].code), reverse=True)
        best_score, best_entry, best_metrics = ranked[0]

        if not category_ok(best_entry, category) or not stage_ok(best_entry, stage):
            pred_code = UNKNOWN
            pred_label = ""
            unknown = True
        elif best_score < 0.32:
            pred_code = UNKNOWN
            pred_label = ""
            unknown = True
        else:
            pred_code = best_entry.code
            pred_label = label_map[pred_code]
            unknown = False

        segments_out.append(
            {
                "segment_id": f"{inspection_id}-S{index}",
                "span_text": segment,
                "pred_code": pred_code,
                "pred_label": pred_label,
                "confidence": calibrate_confidence(best_score, unknown),
                "rationale": build_rationale(category, stage, lot, pred_code, best_metrics),
            }
        )

    lots_out.append(
        {
            "inspection_id": inspection_id,
            "supplier_id": s(row["supplier_id"]),
            "supplier_lot": lot,
            "material_code": s(row["material_code"]),
            "item_category": category,
            "inspection_stage": stage,
            "inspector_id": s(row["inspector_id"]),
            "sample_size": int(s(row["sample_size"]) or "0"),
            "defect_remark": s(row["defect_remark"]),
            "normalized_reasons": segments_out,
        }
    )

with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump({"lots": lots_out}, f, ensure_ascii=False, indent=2)

print(f"[solver] wrote {OUT_PATH} lots={len(lots_out)}")
PY
