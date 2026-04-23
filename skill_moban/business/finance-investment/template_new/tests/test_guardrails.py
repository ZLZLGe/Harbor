from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path


DATA_ROOT = Path(os.environ.get("FINANCE_DATA_ROOT", "/app/data"))
OUTPUT_ROOT = Path(os.environ.get("FINANCE_OUTPUT_ROOT", "/app/output"))
HASH_PATH = Path(os.environ.get("PUBLIC_DATA_HASH_PATH", "/opt/public-data-reference.sha256"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_public_input_files_are_unchanged() -> None:
    assert HASH_PATH.exists()
    result = subprocess.run(
        ["sha256sum", "-c", str(HASH_PATH)],
        cwd="/",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    assert result.returncode == 0, result.stdout


def test_public_data_sources_are_present_and_nontrivial() -> None:
    required = [
        DATA_ROOT / "reference" / "company_universe.csv",
        DATA_ROOT / "reference" / "methodology.md",
        DATA_ROOT / "reference" / "source_manifest.json",
        DATA_ROOT / "fred" / "DGS10.csv",
        DATA_ROOT / "prices" / "SPY.csv",
    ]
    required.extend((DATA_ROOT / "sec_companyfacts").glob("*.json"))
    required.extend((DATA_ROOT / "prices").glob("*.csv"))
    assert len(list((DATA_ROOT / "sec_companyfacts").glob("*.json"))) >= 7
    assert len(list((DATA_ROOT / "prices").glob("*.csv"))) >= 8
    for path in required:
        assert path.exists(), path
        assert path.stat().st_size > 100, path


def test_outputs_do_not_contain_placeholders_or_nonfinite_tokens() -> None:
    blocked_phrases = ["todo", "placeholder", "lorem ipsum", "unknown", "not available"]
    for path in [
        OUTPUT_ROOT / "financial_metrics.csv",
        OUTPUT_ROOT / "quality_risk_scores.csv",
        OUTPUT_ROOT / "valuation.json",
        OUTPUT_ROOT / "investment_ranking.json",
        OUTPUT_ROOT / "research_memo.md",
    ]:
        text = path.read_text(encoding="utf-8").lower()
        for token in blocked_phrases:
            assert token not in text
        assert not re.search(r"(?<![a-z])nan(?![a-z])", text)
        assert not re.search(r"(?<![a-z])inf(?![a-z])", text)


def test_json_outputs_have_no_extra_top_level_substitution_payloads() -> None:
    valuation = json.loads((OUTPUT_ROOT / "valuation.json").read_text(encoding="utf-8"))
    ranking = json.loads((OUTPUT_ROOT / "investment_ranking.json").read_text(encoding="utf-8"))
    assert set(valuation) == {"as_of_date", "risk_free_rate", "securities"}
    assert set(ranking) == {"top_pick", "avoid_or_trim", "ranking"}
    assert isinstance(valuation["securities"], list) and len(valuation["securities"]) == 7
    assert isinstance(ranking["ranking"], list) and len(ranking["ranking"]) == 7
