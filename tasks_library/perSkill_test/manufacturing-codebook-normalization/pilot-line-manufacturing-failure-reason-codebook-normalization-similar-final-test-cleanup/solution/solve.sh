#!/usr/bin/env bash
set -euo pipefail

DATA_DIR="${DATA_DIR:-/app/data}"
OUT_DIR="${OUT_DIR:-/app/output}"
mkdir -p "${OUT_DIR}"

python3 - <<'PY'
import hashlib
import json
import os
import re
from difflib import SequenceMatcher

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
OUT_DIR = os.environ.get("OUT_DIR", "/app/output")

EVENTS_PATH = os.path.join(DATA_DIR, "pilot_line_events.jsonl")
CODEBOOK_PATH = os.path.join(DATA_DIR, "reason_codebooks.json")
OUTPUT_PATH = os.path.join(OUT_DIR, "final_test_reason_map.json")

TOKEN_RE = re.compile(r"[a-z]+[0-9]*|[0-9]+|[\u4e00-\u9fff]+", re.IGNORECASE)
SPLIT_RE = re.compile(r"\s*(?:;|；)\s*")
UNKNOWN = "UNKNOWN"


def text(value):
    return "" if value is None else str(value).strip()


def token_set(value):
    return {part for part in TOKEN_RE.findall(text(value).lower()) if part}


def score_overlap(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def stable_jitter(*parts):
    raw = "|".join(text(part) for part in parts).encode("utf-8")
    return (int(hashlib.md5(raw).hexdigest(), 16) % 17 - 8) / 1000.0


def split_segments(raw_reason_text):
    raw = text(raw_reason_text)
    if not raw:
        return [""]
    parts = [part.strip() for part in SPLIT_RE.split(raw) if part and part.strip()]
    return parts if len(parts) > 1 else [raw]


with open(CODEBOOK_PATH, "r", encoding="utf-8") as f:
    codebooks = json.load(f)["products"]

entries_by_product = {}
labels = {}

for product in codebooks:
    pid = text(product["product_id"])
    entries = []
    label_map = {}
    for entry in product["entries"]:
        label = text(entry["standard_label"])
        keyword_list = [text(item).lower() for item in entry.get("keywords_examples", []) if text(item)]
        keywords = " ".join(keyword_list)
        all_tokens = token_set(label) | token_set(keywords) | token_set(entry.get("category", ""))
        entries.append(
            {
                "code": text(entry["code"]),
                "label": label,
                "stations": {text(x) for x in entry.get("station_scope", []) if text(x)},
                "tokens": all_tokens,
                "keywords": keyword_list,
            }
        )
        label_map[text(entry["code"])] = label
    entries_by_product[pid] = entries
    labels[pid] = label_map

records = []
with open(EVENTS_PATH, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            records.append(json.loads(line))

out_records = []

for record in records:
    pid = text(record["product_id"])
    station = text(record["station"])
    raw_reason_text = text(record["raw_reason_text"])
    segments = split_segments(raw_reason_text)
    mapped_segments = []

    for idx, span in enumerate(segments, start=1):
        span_tokens = token_set(span)
        best = None
        best_score = -1.0
        best_overlap = 0.0
        best_phrase_hit = 0.0

        for entry in entries_by_product[pid]:
            station_ok = (not entry["stations"]) or (station in entry["stations"])
            overlap = score_overlap(span_tokens, entry["tokens"])
            seq = SequenceMatcher(None, text(span).lower(), entry["label"].lower()).ratio()
            context = score_overlap(
                token_set(record.get("test_item", "")) | token_set(record.get("symptom_code", "")),
                entry["tokens"],
            )
            span_lower = text(span).lower()
            phrase_hit = 1.0 if any(
                keyword and len(keyword) >= 4 and keyword in span_lower
                for keyword in entry["keywords"]
            ) else 0.0
            score = 0.40 * overlap + 0.15 * seq + 0.10 * context + 0.35 * phrase_hit
            if not station_ok:
                score -= 0.35
            if score > best_score:
                best = entry
                best_score = score
                best_overlap = overlap
                best_phrase_hit = phrase_hit

        is_unknown = best is None or best_score < 0.24 or (best_overlap < 0.05 and best_phrase_hit < 1.0)

        if is_unknown:
            pred_code = UNKNOWN
            pred_label = ""
        else:
            pred_code = best["code"]
            pred_label = best["label"]

        jitter = stable_jitter(record["event_id"], idx, span, station, record.get("symptom_code", ""))
        if is_unknown:
            confidence = max(0.18, min(0.54, 0.28 + 0.25 * max(best_score, 0.0) + 0.10 * best_overlap + jitter))
            rationale = (
                f"station={station} | item={text(record.get('test_item'))} | symptom={text(record.get('symptom_code'))} "
                f"| weak_match score={best_score:.3f} ov={best_overlap:.3f}"
            )
        else:
            confidence = max(0.58, min(0.96, 0.62 + 0.16 * best_overlap + 0.18 * best_score + 0.04 * best_phrase_hit + jitter))
            rationale = (
                f"station={station} | item={text(record.get('test_item'))} | symptom={text(record.get('symptom_code'))} "
                f"| code={pred_code} | ov={best_overlap:.3f} | score={best_score:.3f}"
            )

        mapped_segments.append(
            {
                "segment_id": f"{text(record['event_id'])}-S{idx}",
                "span_text": span,
                "pred_code": pred_code,
                "pred_label": pred_label,
                "confidence": round(float(confidence), 4),
                "rationale": rationale[:180],
            }
        )

    out_records.append(
        {
            "event_id": text(record["event_id"]),
            "product_id": pid,
            "station": station,
            "engineer_id": text(record.get("engineer_id")),
            "test_item": text(record.get("test_item")),
            "symptom_code": text(record.get("symptom_code")),
            "raw_reason_text": raw_reason_text,
            "reason_segments": mapped_segments,
        }
    )

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump({"records": out_records}, f, ensure_ascii=False, indent=2)

print(f"wrote {OUTPUT_PATH} with {len(out_records)} records")
PY
