from __future__ import annotations

import json
import sys
from pathlib import Path


REGISTRY_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("source_registry.json")


def summarize(text: str) -> list[str]:
    lowered = text.lower()
    cues = []
    if "tradeoff" in lowered or "tradeoffs" in lowered:
        cues.append("mentions tradeoffs directly")
    if "short" in lowered and "paragraph" in lowered:
        cues.append("favors short paragraphs")
    if "direct" in lowered:
        cues.append("uses direct, compact statements")
    if "specific" in lowered or "concrete" in lowered:
        cues.append("prefers concrete details over slogans")
    if "operator" in lowered or "builder" in lowered:
        cues.append("keeps an operator-oriented point of view")
    return cues


def main() -> None:
    payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    docs = payload["documents"]
    voice_docs = [doc for doc in docs if doc["kind"] == "voice_sample"]
    for doc in voice_docs:
        body = "\n".join(line["text"] for line in doc["lines"])
        cues = summarize(body)
        print(f"{doc['doc_id']}:")
        for cue in cues:
            print(f"- {cue}")


if __name__ == "__main__":
    main()
