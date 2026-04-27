from __future__ import annotations

import csv
import importlib.util
import json
import math
import os
import shutil
import sys
from pathlib import Path

import pandas as pd
import pytest
from rdkit import Chem
from rdkit.Chem import Crippen, Descriptors, Lipinski, QED, rdMolDescriptors


WORKSPACE = Path(os.environ.get("WORKSPACE", "/root/workspace"))
DATA_DIR = WORKSPACE / "data"
OUTPUT_DIR = WORKSPACE / "output"
SOLUTION = WORKSPACE / "solution.py"
REQUIRED_COLUMNS = [
    "rank",
    "candidate_id",
    "compound_name",
    "canonical_smiles",
    "series",
    "activity_nM",
    "pActivity",
    "mw",
    "logp",
    "hbd",
    "hba",
    "tpsa",
    "rotatable_bonds",
    "qed",
    "rule_flags",
    "safety_flags",
    "triage_score",
    "recommendation",
    "rationale",
]


@pytest.fixture(scope="session")
def run_report():
    assert SOLUTION.exists(), "solution.py must exist in /root/workspace"
    spec = importlib.util.spec_from_file_location("solution", SOLUTION)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["solution"] = module
    spec.loader.exec_module(module)
    assert hasattr(module, "build_lead_triage_report")
    result = module.build_lead_triage_report(str(DATA_DIR), str(OUTPUT_DIR))
    assert isinstance(result, dict)
    return result


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def parent_mol(smiles: str):
    mol = Chem.MolFromSmiles(str(smiles))
    if mol is None:
        return None
    frags = Chem.GetMolFrags(mol, asMols=True, sanitizeFrags=True)
    return max(frags, key=lambda m: (m.GetNumHeavyAtoms(), Descriptors.MolWt(m)))


def convert_to_nm(value: float, unit: str) -> float:
    unit_norm = unit.lower().replace("µ", "u")
    if unit_norm == "nm":
        return value
    if unit_norm == "um":
        return value * 1000.0
    if unit_norm == "mm":
        return value * 1_000_000.0
    raise AssertionError(f"unexpected unit {unit}")


def expected_activity_by_candidate() -> dict[str, float]:
    target = "MAPK14"
    grouped: dict[str, list[dict]] = {}
    for line in (DATA_DIR / "activity_records.jsonl").read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        if record["target"] != target:
            continue
        grouped.setdefault(record["candidate_id"], []).append(record)
    expected = {}
    for cid, records in grouped.items():
        exact = [r for r in records if r["relation"] in {"=", "~"}]
        upper = [r for r in records if r["relation"] in {"<", "<="}]
        lower = [r for r in records if r["relation"] in {">", ">="}]
        if exact:
            terms = []
            weights = []
            for record in exact:
                endpoint_weight = 0.65 if record["endpoint"].upper() == "EC50" else 1.0
                weight = float(record["confidence_score"]) * endpoint_weight
                terms.append(math.log(convert_to_nm(float(record["value"]), record["unit"])) * weight)
                weights.append(weight)
            expected[cid] = math.exp(sum(terms) / sum(weights))
        elif upper:
            expected[cid] = min(convert_to_nm(float(r["value"]), r["unit"]) for r in upper) * 0.8
        elif lower:
            expected[cid] = min(convert_to_nm(float(r["value"]), r["unit"]) for r in lower) * 2.0
    return expected


def test_output_contract_and_parseability(run_report):
    for filename in ["lead_triage.csv", "lead_triage.json", "excluded_candidates.csv", "method_notes.md"]:
        assert (OUTPUT_DIR / filename).exists(), f"missing {filename}"
    rows = read_csv_rows(OUTPUT_DIR / "lead_triage.csv")
    assert rows, "lead_triage.csv should not be empty"
    assert list(rows[0].keys()) == REQUIRED_COLUMNS
    ranks = [int(row["rank"]) for row in rows]
    assert ranks == list(range(1, len(rows) + 1))
    scores = [float(row["triage_score"]) for row in rows]
    assert scores == sorted(scores, reverse=True)
    assert all(0.0 <= score <= 100.0 for score in scores)
    assert {row["recommendation"] for row in rows} <= {"advance", "backup", "deprioritize", "exclude"}

    report = json.loads((OUTPUT_DIR / "lead_triage.json").read_text(encoding="utf-8"))
    assert set(report) >= {"target", "selected_candidates", "excluded_candidates", "summary", "method"}
    assert report["target"].startswith("MAPK14")
    assert report["summary"]["n_input_candidates"] == 12
    assert report["summary"]["n_advance"] >= 2


def test_rdkit_descriptors_and_canonical_parents(run_report):
    candidates = pd.read_csv(DATA_DIR / "candidates.csv").set_index("candidate_id")
    rows = read_csv_rows(OUTPUT_DIR / "lead_triage.csv")
    seen_smiles = set()
    for row in rows:
        cid = row["candidate_id"]
        mol = parent_mol(candidates.loc[cid, "smiles"])
        assert mol is not None
        canonical = Chem.MolToSmiles(mol, isomericSmiles=False, canonical=True)
        assert row["canonical_smiles"] == canonical
        assert canonical not in seen_smiles
        seen_smiles.add(canonical)
        assert abs(float(row["mw"]) - Descriptors.MolWt(mol)) < 0.05
        assert abs(float(row["logp"]) - Crippen.MolLogP(mol)) < 0.05
        assert int(row["hbd"]) == Lipinski.NumHDonors(mol)
        assert int(row["hba"]) == Lipinski.NumHAcceptors(mol)
        assert abs(float(row["tpsa"]) - rdMolDescriptors.CalcTPSA(mol)) < 0.05
        assert int(row["rotatable_bonds"]) == Lipinski.NumRotatableBonds(mol)
        assert abs(float(row["qed"]) - QED.qed(mol)) < 0.01


def test_activity_normalization_and_censored_values(run_report):
    expected = expected_activity_by_candidate()
    rows = {row["candidate_id"]: row for row in read_csv_rows(OUTPUT_DIR / "lead_triage.csv")}
    for cid in ["KIN-001", "KIN-004", "KIN-007", "KIN-008", "KIN-010", "KIN-011", "KIN-012"]:
        assert cid in rows, f"{cid} should remain auditable in lead_triage.csv"
        got = float(rows[cid]["activity_nM"])
        assert abs(got - expected[cid]) <= max(0.5, expected[cid] * 0.01)
        assert abs(float(rows[cid]["pActivity"]) - (9 - math.log10(expected[cid]))) < 0.03
    assert float(rows["KIN-007"]["activity_nM"]) == pytest.approx(20.0, abs=0.1)
    assert float(rows["KIN-008"]["activity_nM"]) > 1_000_000


def test_exclusions_alerts_and_safety_logic(run_report):
    excluded = {row["candidate_id"]: row["reason"] for row in read_csv_rows(OUTPUT_DIR / "excluded_candidates.csv")}
    assert "invalid_structure" in excluded["KIN-009"]
    assert "duplicate_parent_of:KIN-001" in excluded["KIN-002"]
    assert "severe_hepatotoxicity" in excluded["KIN-003"]
    assert "black_box_bleeding" in excluded["KIN-006"]

    rows = {row["candidate_id"]: row for row in read_csv_rows(OUTPUT_DIR / "lead_triage.csv")}
    assert "reactive_michael_acceptor" in rows["KIN-007"]["rule_flags"]
    assert rows["KIN-007"]["recommendation"] != "advance"
    assert "catechol_assay_interference" in rows["KIN-005"]["rule_flags"]
    assert "cyp3a4_interaction" in rows["KIN-001"]["safety_flags"]
    assert rows["KIN-004"]["recommendation"] == "advance"
    assert rows["KIN-001"]["recommendation"] == "advance"


def test_ranking_uses_potency_risk_and_series_diversity(run_report):
    rows = read_csv_rows(OUTPUT_DIR / "lead_triage.csv")
    by_id = {row["candidate_id"]: row for row in rows}
    ranked_ids = [row["candidate_id"] for row in rows]
    assert ranked_ids.index("KIN-004") < ranked_ids.index("KIN-010")
    assert ranked_ids.index("KIN-001") < ranked_ids.index("KIN-005")
    assert by_id["KIN-011"]["recommendation"] in {"backup", "deprioritize"}
    assert by_id["KIN-008"]["recommendation"] == "deprioritize"
    selected_quinazolines = [
        row for row in rows
        if row["series"] == "quinazoline" and row["recommendation"] in {"advance", "backup"}
    ]
    assert len(selected_quinazolines) <= 3


def test_method_notes_are_specific(run_report):
    notes = (OUTPUT_DIR / "method_notes.md").read_text(encoding="utf-8").lower()
    for phrase in ["smiles", "largest", "nm", "censored", "qed", "safety", "series"]:
        assert phrase in notes


def test_guardrail_dynamic_candidate_is_scored_from_data(tmp_path):
    data_copy = tmp_path / "data"
    shutil.copytree(DATA_DIR, data_copy)
    candidates = pd.read_csv(data_copy / "candidates.csv")
    candidates.loc[len(candidates)] = {
        "candidate_id": "KIN-X99",
        "compound_name": "Dynamic clean pyrazolopyrimidine",
        "smiles": "COc1cc2ncnc(Nc3ccc(F)cc3)c2cc1OCCO",
        "series": "dynamic-series",
        "source_note": "verifier-added clean potent analog",
    }
    candidates.to_csv(data_copy / "candidates.csv", index=False)
    with (data_copy / "activity_records.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "candidate_id": "KIN-X99",
                    "assay_id": "DYNAMIC-MAPK14-001",
                    "target": "MAPK14",
                    "endpoint": "IC50",
                    "relation": "=",
                    "value": 8,
                    "unit": "nM",
                    "confidence_score": 9,
                    "assay_note": "dynamic verifier potency check",
                }
            )
            + "\n"
        )

    spec = importlib.util.spec_from_file_location("solution_dynamic", SOLUTION)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    dynamic_out = tmp_path / "out"
    module.build_lead_triage_report(str(data_copy), str(dynamic_out))
    rows = read_csv_rows(dynamic_out / "lead_triage.csv")
    by_id = {row["candidate_id"]: row for row in rows}
    assert "KIN-X99" in by_id
    assert by_id["KIN-X99"]["recommendation"] == "advance"
    assert int(by_id["KIN-X99"]["rank"]) <= 3
