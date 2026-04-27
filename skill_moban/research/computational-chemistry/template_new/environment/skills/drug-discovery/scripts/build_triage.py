from __future__ import annotations

from pathlib import Path
import runpy


SOLUTION_SOURCE = r'''from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd
from rdkit import Chem
from rdkit.Chem import Crippen, Descriptors, Lipinski, QED, rdMolDescriptors
from rdkit.Chem.Scaffolds import MurckoScaffold


OUTPUT_COLUMNS = [
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

MICHAEL_ACCEPTOR = Chem.MolFromSmarts("[C;H1,H2]=[C;H1,H2]C(=O)[N,O,S]")
CATECHOL = Chem.MolFromSmarts("c1cc([OX2H])c([OX2H])cc1")
COUMARIN = Chem.MolFromSmarts("O=c1oc2ccccc2cc1")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _parent_mol(smiles: str) -> Chem.Mol | None:
    mol = Chem.MolFromSmiles(str(smiles))
    if mol is None:
        return None
    frags = Chem.GetMolFrags(mol, asMols=True, sanitizeFrags=True)
    if frags:
        mol = max(frags, key=lambda m: (m.GetNumHeavyAtoms(), Descriptors.MolWt(m)))
    return mol


def _unit_to_nm(value: float, unit: str) -> float:
    unit_norm = unit.strip().lower().replace("µ", "u")
    if unit_norm in {"nm", "nanomolar"}:
        return value
    if unit_norm in {"um", "micromolar"}:
        return value * 1000.0
    if unit_norm in {"mm", "millimolar"}:
        return value * 1_000_000.0
    raise ValueError(f"unsupported activity unit: {unit}")


def _activity_summary(records: list[dict[str, Any]], target: str) -> dict[str, dict[str, Any]]:
    target_norm = target.split("/")[0].strip().upper()
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if str(record.get("target", "")).upper() != target_norm:
            continue
        relation = str(record.get("relation", "=")).strip()
        value_nm = _unit_to_nm(float(record["value"]), str(record.get("unit", "nM")))
        confidence = float(record.get("confidence_score", 5))
        endpoint = str(record.get("endpoint", "")).upper()
        endpoint_weight = 0.65 if endpoint == "EC50" else 1.0
        grouped[str(record.get("candidate_id", ""))].append(
            {
                "value_nM": value_nm,
                "relation": relation,
                "confidence": confidence,
                "weight": max(confidence, 1.0) * endpoint_weight,
            }
        )

    summaries: dict[str, dict[str, Any]] = {}
    for cid, rows in grouped.items():
        exact = [row for row in rows if row["relation"] in {"=", "~"}]
        upper = [row for row in rows if row["relation"] in {"<", "<="}]
        lower = [row for row in rows if row["relation"] in {">", ">="}]
        if exact:
            numerator = sum(math.log(row["value_nM"]) * row["weight"] for row in exact)
            denominator = sum(row["weight"] for row in exact)
            activity_nm = math.exp(numerator / denominator)
            confidence = sum(row["confidence"] for row in exact) / len(exact)
            relation_class = "exact"
        elif upper:
            best = min(upper, key=lambda row: row["value_nM"])
            activity_nm = best["value_nM"] * 0.8
            confidence = best["confidence"] * 0.85
            relation_class = "upper_bound"
        elif lower:
            best = min(lower, key=lambda row: row["value_nM"])
            activity_nm = best["value_nM"] * 2.0
            confidence = best["confidence"] * 0.65
            relation_class = "lower_bound"
        else:
            continue
        summaries[cid] = {
            "activity_nM": activity_nm,
            "pActivity": 9.0 - math.log10(max(activity_nm, 1e-12)),
            "confidence": confidence,
            "relation_class": relation_class,
            "n_records": len(rows),
        }
    return summaries


def _properties(mol: Chem.Mol) -> dict[str, float]:
    return {
        "mw": float(Descriptors.MolWt(mol)),
        "logp": float(Crippen.MolLogP(mol)),
        "hbd": float(Lipinski.NumHDonors(mol)),
        "hba": float(Lipinski.NumHAcceptors(mol)),
        "tpsa": float(rdMolDescriptors.CalcTPSA(mol)),
        "rotatable_bonds": float(Lipinski.NumRotatableBonds(mol)),
        "qed": float(QED.qed(mol)),
    }


def _rule_flags(mol: Chem.Mol, props: dict[str, float], profile: dict[str, Any]) -> list[str]:
    ranges = profile["property_ranges"]
    flags: list[str] = []
    if props["mw"] > ranges["mw"][1]:
        flags.append("mw_high")
    if props["mw"] < ranges["mw"][0]:
        flags.append("mw_low")
    if props["logp"] > ranges["logp"][1]:
        flags.append("logp_high")
    if props["logp"] < ranges["logp"][0]:
        flags.append("logp_low")
    if props["hbd"] > ranges["hbd"][1]:
        flags.append("hbd_high")
    if props["hba"] > ranges["hba"][1]:
        flags.append("hba_high")
    if props["tpsa"] > ranges["tpsa"][1]:
        flags.append("tpsa_high")
    if props["rotatable_bonds"] > ranges["rotatable_bonds"][1]:
        flags.append("rotatable_bonds_high")
    if props["qed"] < ranges["qed_min"]:
        flags.append("qed_low")
    if MICHAEL_ACCEPTOR is not None and mol.HasSubstructMatch(MICHAEL_ACCEPTOR):
        flags.append("reactive_michael_acceptor")
    if CATECHOL is not None and mol.HasSubstructMatch(CATECHOL):
        flags.append("catechol_assay_interference")
    if COUMARIN is not None and mol.HasSubstructMatch(COUMARIN):
        flags.append("coumarin_anticoagulant_like")
    return flags


def _safety_by_name(reports: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for report in reports:
        grouped[str(report.get("compound_name", "")).lower()].append(report)
    return grouped


def _safety_flags(compound_name: str, safety_index: dict[str, list[dict[str, Any]]]) -> list[str]:
    rows = safety_index.get(compound_name.lower(), [])
    flags = []
    for row in rows:
        category = str(row.get("event_category", "")).strip()
        if category:
            flags.append(category)
    return sorted(set(flags))


def _score(
    props: dict[str, float],
    activity: dict[str, Any] | None,
    rule_flags: list[str],
    safety_flags: list[str],
    profile: dict[str, Any],
) -> float:
    if activity is None:
        return 0.0
    cutoff = float(profile["activity_cutoff_nM"])
    backup = float(profile["backup_activity_cutoff_nM"])
    activity_nm = float(activity["activity_nM"])
    potency = max(
        0.0,
        min(
            40.0,
            40.0
            * (math.log10(backup) - math.log10(activity_nm))
            / (math.log10(backup) - math.log10(5.0)),
        ),
    )
    if activity_nm <= cutoff:
        potency += 8.0
    prop_score = max(0.0, 22.0 - 4.0 * len([f for f in rule_flags if f.endswith("_high") or f.endswith("_low")]))
    score = potency + prop_score + min(12.0, max(0.0, props["qed"] * 14.0)) + min(10.0, float(activity["confidence"]))
    if "reactive_michael_acceptor" in rule_flags:
        score -= 18.0
    if "catechol_assay_interference" in rule_flags:
        score -= 14.0
    if "coumarin_anticoagulant_like" in rule_flags:
        score -= 10.0
    score -= 8.0 * len(set(safety_flags) & set(profile.get("safety_penalty_categories", [])))
    score -= 30.0 * len(set(safety_flags) & set(profile.get("safety_exclusion_categories", [])))
    return round(max(0.0, min(100.0, score)), 3)


def build_lead_triage_report(
    data_dir: str = "/root/workspace/data",
    output_dir: str = "/root/workspace/output",
) -> dict:
    data_path = Path(data_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    candidates = pd.read_csv(data_path / "candidates.csv")
    profile = json.loads((data_path / "target_profile.json").read_text(encoding="utf-8"))
    activities = _activity_summary(_load_jsonl(data_path / "activity_records.jsonl"), profile["target"])
    safety_index = _safety_by_name(_load_jsonl(data_path / "safety_reports.jsonl"))

    excluded: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    seen_parent: dict[str, str] = {}

    for candidate in candidates.to_dict(orient="records"):
        cid = str(candidate["candidate_id"])
        name = str(candidate["compound_name"])
        mol = _parent_mol(str(candidate["smiles"]))
        if mol is None:
            excluded.append({"candidate_id": cid, "compound_name": name, "reason": "invalid_structure"})
            continue
        canonical = Chem.MolToSmiles(mol, isomericSmiles=False, canonical=True)
        if canonical in seen_parent:
            excluded.append({"candidate_id": cid, "compound_name": name, "reason": f"duplicate_parent_of:{seen_parent[canonical]}"})
            continue
        seen_parent[canonical] = cid

        props = _properties(mol)
        act = activities.get(cid)
        rules = _rule_flags(mol, props, profile)
        safety = _safety_flags(name, safety_index)
        score = _score(props, act, rules, safety, profile)
        hard_safety = set(safety) & set(profile.get("safety_exclusion_categories", []))
        if act is None:
            recommendation = "exclude"
            rationale = "no MAPK14 activity evidence"
        elif hard_safety:
            recommendation = "exclude"
            rationale = "hard safety exclusion: " + ",".join(sorted(hard_safety))
        elif act["activity_nM"] <= profile["activity_cutoff_nM"] and score >= 55 and not (
            {"reactive_michael_acceptor", "catechol_assay_interference", "logp_high", "rotatable_bonds_high"} & set(rules)
        ):
            recommendation = "advance"
            rationale = "potent MAPK14 activity with acceptable lead-like profile"
        elif act["activity_nM"] <= profile["backup_activity_cutoff_nM"] and score >= 38:
            recommendation = "backup"
            rationale = "usable potency but medicinal-chemistry or safety liabilities remain"
        else:
            recommendation = "deprioritize"
            rationale = "insufficient combined potency, property, or safety profile"

        if recommendation == "exclude":
            excluded.append({"candidate_id": cid, "compound_name": name, "reason": rationale})
            continue

        scaffold = MurckoScaffold.MurckoScaffoldSmiles(mol=mol, includeChirality=False) or canonical
        rows.append(
            {
                "candidate_id": cid,
                "compound_name": name,
                "canonical_smiles": canonical,
                "series": str(candidate["series"]),
                "activity_nM": round(float(act["activity_nM"]), 3),
                "pActivity": round(float(act["pActivity"]), 3),
                "mw": round(props["mw"], 3),
                "logp": round(props["logp"], 3),
                "hbd": int(props["hbd"]),
                "hba": int(props["hba"]),
                "tpsa": round(props["tpsa"], 3),
                "rotatable_bonds": int(props["rotatable_bonds"]),
                "qed": round(props["qed"], 3),
                "rule_flags": ";".join(rules),
                "safety_flags": ";".join(safety),
                "triage_score": score,
                "recommendation": recommendation,
                "rationale": rationale,
                "_scaffold": scaffold,
            }
        )

    rows.sort(key=lambda row: (-float(row["triage_score"]), float(row["activity_nM"]), row["candidate_id"]))
    shortlist_limit = int(profile.get("series_diversity", {}).get("max_shortlist_per_series", 99))
    series_counts: dict[str, int] = defaultdict(int)
    ranked_rows: list[dict[str, Any]] = []
    for row in rows:
        if row["recommendation"] in {"advance", "backup"} and series_counts[row["series"]] >= shortlist_limit:
            row = dict(row)
            row["recommendation"] = "deprioritize"
            row["rationale"] = "held back by series-diversity cap"
        if row["recommendation"] in {"advance", "backup"}:
            series_counts[row["series"]] += 1
        ranked_rows.append(row)

    for idx, row in enumerate(ranked_rows, start=1):
        row["rank"] = idx
        row.pop("_scaffold", None)

    pd.DataFrame(ranked_rows, columns=OUTPUT_COLUMNS).to_csv(output_path / "lead_triage.csv", index=False)
    pd.DataFrame(excluded, columns=["candidate_id", "compound_name", "reason"]).to_csv(output_path / "excluded_candidates.csv", index=False)
    report = {
        "target": profile["target"],
        "selected_candidates": [
            {"rank": row["rank"], "candidate_id": row["candidate_id"], "recommendation": row["recommendation"], "triage_score": row["triage_score"]}
            for row in ranked_rows
            if row["recommendation"] in {"advance", "backup"}
        ],
        "excluded_candidates": excluded,
        "summary": {
            "n_input_candidates": int(len(candidates)),
            "n_ranked_candidates": int(len(ranked_rows)),
            "n_excluded_candidates": int(len(excluded)),
            "n_advance": int(sum(row["recommendation"] == "advance" for row in ranked_rows)),
            "n_backup": int(sum(row["recommendation"] == "backup" for row in ranked_rows)),
        },
        "method": {
            "structure_standardization": "RDKit parsing, largest-fragment parent selection, canonical non-isomeric SMILES duplicate merge",
            "activity_normalization": "nM/uM/mM converted to nM; exact values use confidence-weighted geometric mean; censored values keep bound direction",
            "ranking": "combined MAPK14 potency, assay confidence, lead-like descriptors, QED, structural alerts, safety flags, and series diversity",
        },
    }
    (output_path / "lead_triage.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (output_path / "method_notes.md").write_text(
        "\n".join(
            [
                "# Method Notes",
                "",
                "SMILES were parsed with RDKit, salts were reduced to the largest organic parent fragment, and duplicate parent structures were excluded with traceable candidate IDs.",
                "Activity values were normalized to nM. Exact MAPK14 IC50/Ki/Kd records were aggregated by confidence-weighted geometric mean; EC50 records were down-weighted; censored bounds were not treated as exact averages.",
                "Ranking combined potency, assay confidence, Lipinski/Veber-style descriptors, QED, structural alerts, safety signal categories, and series diversity caps.",
                "Safety categories listed as hard exclusions in the target profile were excluded from the ranked lead table; penalty categories reduced score but remained auditable.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return report


if __name__ == "__main__":
    build_lead_triage_report()
'''


def main() -> None:
    solution_path = Path("/root/workspace/solution.py")
    solution_path.write_text(SOLUTION_SOURCE, encoding="utf-8")
    print(f"wrote {solution_path}")
    runpy.run_path(str(solution_path), run_name="__main__")


if __name__ == "__main__":
    main()
