from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from rdkit import Chem, DataStructs
from rdkit.Chem import Crippen, Descriptors, Lipinski, QED, rdFingerprintGenerator, rdMolDescriptors
try:
    from rdkit.Chem import inchi as rdkit_inchi
except ImportError:  # pragma: no cover - fallback for stripped builds
    rdkit_inchi = None
from rdkit.Chem.MolStandardize import rdMolStandardize


CHOOSER = rdMolStandardize.LargestFragmentChooser()
UNCHARGER = rdMolStandardize.Uncharger()


def _round(value: float, precision: int) -> float:
    return round(float(value), precision)


def _normalize_mol(mol: Chem.Mol) -> Chem.Mol:
    mol = Chem.Mol(mol)
    mol = rdMolStandardize.Cleanup(mol)
    mol = CHOOSER.choose(mol)
    mol = UNCHARGER.uncharge(mol)
    return mol


def _iter_library_records(library_dir: Path) -> list[tuple[str, Chem.Mol]]:
    records: list[tuple[str, Chem.Mol]] = []
    for path in sorted(library_dir.iterdir()):
        suffix = path.suffix.lower()
        if suffix == ".sdf":
            for mol in Chem.SDMolSupplier(str(path), removeHs=False):
                if mol is None:
                    continue
                compound_id = mol.GetProp("compound_id") if mol.HasProp("compound_id") else mol.GetProp("_Name")
                records.append((compound_id, mol))
        elif suffix == ".smi":
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                smiles, compound_id = line.split()[:2]
                mol = Chem.MolFromSmiles(smiles)
                if mol is None:
                    continue
                records.append((compound_id, mol))
    return records


def _load_actives(actives_csv: Path) -> list[Chem.Mol]:
    with actives_csv.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        mols = []
        for row in reader:
            mol = Chem.MolFromSmiles(row["smiles"])
            if mol is None:
                continue
            mols.append(_normalize_mol(mol))
    return mols


def _build_fp_generator(scoring: dict[str, Any]):
    cfg = scoring["fingerprint"]
    return rdFingerprintGenerator.GetMorganGenerator(
        radius=int(cfg["radius"]),
        fpSize=int(cfg["n_bits"]),
        includeChirality=bool(cfg["include_chirality"]),
    )


def _descriptor_row(mol: Chem.Mol, precision: int) -> dict[str, Any]:
    inchikey = None
    if hasattr(Chem, "MolToInchiKey"):
        inchikey = Chem.MolToInchiKey(mol)
    elif rdkit_inchi is not None and hasattr(rdkit_inchi, "MolToInchiKey"):
        inchikey = rdkit_inchi.MolToInchiKey(mol)
    else:
        inchikey = Chem.MolToSmiles(mol, isomericSmiles=True)
    return {
        "canonical_smiles": Chem.MolToSmiles(mol, isomericSmiles=True),
        "inchikey": inchikey,
        "molecular_weight": _round(Descriptors.MolWt(mol), precision),
        "logp": _round(Crippen.MolLogP(mol), precision),
        "tpsa": _round(rdMolDescriptors.CalcTPSA(mol), precision),
        "hbd": Lipinski.NumHDonors(mol),
        "hba": Lipinski.NumHAcceptors(mol),
        "rotatable_bonds": Lipinski.NumRotatableBonds(mol),
        "qed": _round(QED.qed(mol), precision),
    }


def _decision_reasons(row: dict[str, Any], rules: dict[str, Any]) -> tuple[list[str], list[str]]:
    reasons: list[str] = []
    alerts: list[str] = []
    for alert in rules["alerts"]:
        pattern = Chem.MolFromSmarts(alert["smarts"])
        if row["_mol"].HasSubstructMatch(pattern):
            alerts.append(alert["name"])
            if alert.get("blocking", False):
                reasons.append(f"alert:{alert['name']}")
    for field, contract in rules["lead_like"].items():
        value = row[field]
        limit = contract["value"]
        if contract["op"] == "<=" and value > limit:
            reasons.append(f"{field}>{limit}")
    return sorted(alerts), reasons


def _sort_key(row: dict[str, Any], shortlist_order: list[dict[str, str]]):
    key: list[Any] = []
    for rule in shortlist_order:
        value = row[rule["field"]]
        key.append(-value if rule["direction"] == "desc" else value)
    return tuple(key)


def build_leadlike_shortlist(
    library_dir: str,
    actives_csv: str,
    rules_json: str,
    scoring_json: str,
    top_k: int = 20,
) -> dict[str, Any]:
    library_path = Path(library_dir)
    rules = json.loads(Path(rules_json).read_text(encoding="utf-8"))
    scoring = json.loads(Path(scoring_json).read_text(encoding="utf-8"))
    precision = int(scoring["float_precision"])

    records = _iter_library_records(library_path)
    active_mols = _load_actives(Path(actives_csv))
    fpgen = _build_fp_generator(scoring)
    active_fps = [fpgen.GetFingerprint(mol) for mol in active_mols]

    grouped: dict[str, list[tuple[str, Chem.Mol]]] = {}
    for compound_id, mol in records:
        normalized = _normalize_mol(mol)
        dedupe_key = Chem.MolToSmiles(normalized, isomericSmiles=True)
        grouped.setdefault(dedupe_key, []).append((compound_id, normalized))

    keep_rows: list[dict[str, Any]] = []
    reject_rows: list[dict[str, Any]] = []

    for dedupe_key, members in grouped.items():
        representative = min(compound_id for compound_id, _ in members)
        mol = members[0][1]
        row = _descriptor_row(mol, precision)
        row["compound_id"] = representative
        row["_mol"] = mol
        row["max_similarity_to_actives"] = _round(
            max(DataStructs.TanimotoSimilarity(fpgen.GetFingerprint(mol), fp) for fp in active_fps),
            precision,
        )
        row["alerts"], reasons = _decision_reasons(row, rules)
        if reasons:
            reject_rows.append(
                {
                    "compound_id": representative,
                    "canonical_smiles": row["canonical_smiles"],
                    "alerts": row["alerts"],
                    "reasons": reasons,
                    "decision": "reject",
                }
            )
        else:
            keep_rows.append(
                {
                    "compound_id": representative,
                    "canonical_smiles": row["canonical_smiles"],
                    "inchikey": row["inchikey"],
                    "molecular_weight": row["molecular_weight"],
                    "logp": row["logp"],
                    "tpsa": row["tpsa"],
                    "hbd": row["hbd"],
                    "hba": row["hba"],
                    "rotatable_bonds": row["rotatable_bonds"],
                    "qed": row["qed"],
                    "max_similarity_to_actives": row["max_similarity_to_actives"],
                    "alerts": row["alerts"],
                    "decision": "keep",
                }
            )

    keep_rows.sort(key=lambda row: _sort_key(row, scoring["shortlist_order"]))
    reject_rows.sort(key=lambda row: row["compound_id"])

    shortlist = []
    for rank, row in enumerate(keep_rows[:top_k], start=1):
        entry = dict(row)
        entry["rank"] = rank
        shortlist.append(entry)

    return {
        "summary": {
            "n_input_records": len(records),
            "n_standardized_candidates": len(grouped),
            "n_keep": len(keep_rows),
            "n_reject": len(reject_rows),
        },
        "shortlist": shortlist,
        "rejected_compounds": reject_rows,
    }
