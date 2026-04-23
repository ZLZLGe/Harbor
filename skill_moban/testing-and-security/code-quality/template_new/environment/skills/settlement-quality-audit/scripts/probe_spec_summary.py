from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable


TEXT_SUFFIXES = {
    ".md",
    ".txt",
    ".rst",
    ".json",
    ".jsonl",
    ".yaml",
    ".yml",
    ".proto",
    ".sql",
    ".http",
    ".sh",
    ".py",
    ".ts",
    ".js",
    ".java",
    ".kt",
    ".go",
    ".rb",
    ".php",
}
SKIP_PARTS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build",
    ".next",
}
INVARIANT_PATTERNS = {
    "idempotency": re.compile(r"\b(idempotent|idempotency|dedupe|duplicate retry|safe retry)\b", re.I),
    "state_machine": re.compile(r"\b(state|status|transition|terminal|pending|settled|failed|reversed|cancelled|refunded)\b", re.I),
    "money_semantics": re.compile(r"\b(amount|currency|gross|net|fee|fees|tax|balance)\b", re.I),
    "reconciliation": re.compile(r"\b(reconcile|reconciliation|ledger|posting|journal)\b", re.I),
    "gateway_contract": re.compile(r"\b(gateway|contract|openapi|swagger|schema|proto|callback|webhook)\b", re.I),
}
BUCKET_RULES = {
    "specs": ("spec", "readme", "design", "adr", "requirement", "settlement", "reconcile"),
    "contracts": ("openapi", "swagger", "contract", "gateway", "api", "route", "http", "proto"),
    "schemas": ("schema", "dto", "model", "payload", "response", "request", "avsc"),
    "incidents": ("incident", "postmortem", "trace", "replay", "timeline", "failure", "outage"),
    "tests_and_fixtures": ("test", "fixture", "sample", "snapshot", "golden", "case"),
}


def default_environment_root() -> Path:
    workspace_root = Path("/app/workspace")
    gateway_root = Path("/services/settlement-gateway")
    if workspace_root.exists() or gateway_root.exists():
        return Path("/")
    return Path(__file__).resolve().parents[3]


def scan_roots(root: Path) -> list[Path]:
    preferred = [
        Path("/app/workspace"),
        Path("/services/settlement-gateway"),
        root / "workspace",
        root / "settlement-gateway",
    ]
    existing = [path for path in preferred if path.exists()]
    return existing or [root]


def iter_files(root: Path) -> Iterable[Path]:
    for scan_root in scan_roots(root):
        for path in scan_root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in SKIP_PARTS for part in path.parts):
                continue
            if path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            try:
                if path.stat().st_size > 512 * 1024:
                    continue
            except OSError:
                continue
            yield path


def bucket_for(path: Path) -> str:
    lowered = str(path).lower()
    for bucket, needles in BUCKET_RULES.items():
        if any(needle in lowered for needle in needles):
            return bucket
    return "other"


def score_file(path: Path) -> int:
    lowered = str(path).lower()
    score = 0
    for needles in BUCKET_RULES.values():
        for needle in needles:
            if needle in lowered:
                score += 2
    if path.name.lower() in {"readme.md", "openapi.yaml", "openapi.yml", "swagger.yaml", "swagger.yml"}:
        score += 4
    if "settlement" in lowered or "gateway" in lowered:
        score += 3
    return score


def read_excerpt(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return "(unreadable)"

    if path.suffix.lower() == ".json":
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            keys = ", ".join(list(payload.keys())[:8])
            return f"json keys: {keys}" if keys else "json object"
        if isinstance(payload, list):
            return f"json list length: {len(payload)}"

    for line in text.splitlines():
        stripped = line.strip(" #-*`\t")
        if len(stripped) >= 10:
            return stripped[:140]
    return "(no high-signal excerpt)"


def collect_signals(path: Path) -> Counter[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return Counter()

    signals = Counter()
    for label, pattern in INVARIANT_PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            signals[label] += len(matches)
    return signals


def summarize(root: Path, limit: int) -> dict:
    files = list(iter_files(root))
    ranked = sorted(files, key=lambda path: (-score_file(path), str(path)))
    buckets: dict[str, list[dict[str, object]]] = defaultdict(list)
    invariant_hits = Counter()

    for path in ranked:
        bucket = bucket_for(path)
        if len(buckets[bucket]) >= limit:
            continue
        signals = collect_signals(path)
        invariant_hits.update(signals)
        buckets[bucket].append(
            {
                "path": str(path.relative_to(root)),
                "score": score_file(path),
                "excerpt": read_excerpt(path),
                "signals": {key: value for key, value in signals.items() if value},
            }
        )

    missing = [bucket for bucket in ("specs", "contracts", "schemas", "incidents") if not buckets.get(bucket)]
    return {
        "root": str(root),
        "file_count": len(files),
        "buckets": buckets,
        "invariant_hits": dict(invariant_hits.most_common()),
        "missing_buckets": missing,
    }


def print_report(report: dict) -> None:
    print(f"environment_root: {report['root']}")
    print(f"candidate_text_files: {report['file_count']}")
    print()

    bucket_order = ["specs", "contracts", "schemas", "incidents", "tests_and_fixtures", "other"]
    for bucket in bucket_order:
        entries = report["buckets"].get(bucket, [])
        if not entries:
            continue
        print(f"[{bucket}]")
        for entry in entries:
            print(f"- {entry['path']} (score={entry['score']})")
            print(f"  excerpt: {entry['excerpt']}")
            if entry["signals"]:
                compact = ", ".join(f"{key}={value}" for key, value in entry["signals"].items())
                print(f"  signals: {compact}")
        print()

    invariant_hits = report["invariant_hits"]
    if invariant_hits:
        compact = ", ".join(f"{key}={value}" for key, value in invariant_hits.items())
        print(f"invariant_signal_totals: {compact}")
    else:
        print("invariant_signal_totals: none")

    missing = report["missing_buckets"]
    if missing:
        print(f"gaps: missing evidence buckets -> {', '.join(missing)}")
    else:
        print("gaps: none")


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize settlement-relevant specs, contracts, and fixtures.")
    parser.add_argument("--root", type=Path, default=default_environment_root(), help="Environment root to scan.")
    parser.add_argument("--limit", type=int, default=8, help="Max files to show per bucket.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of text.")
    args = parser.parse_args()

    report = summarize(args.root, args.limit)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return
    print_report(report)


if __name__ == "__main__":
    main()
