from __future__ import annotations

import csv
import importlib.util
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

import pytest
from rdkit import Chem, DataStructs
from rdkit.Chem import Crippen, Descriptors, Lipinski, QED, rdFingerprintGenerator, rdMolDescriptors
try:
    from rdkit.Chem import inchi as rdkit_inchi
except ImportError:  # pragma: no cover - fallback for stripped builds
    rdkit_inchi = None
from rdkit.Chem.MolStandardize import rdMolStandardize


TASK_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = Path(os.environ.get("TASK_DATA_ROOT", "/root/data"))
DEFAULT_SOLUTION_PATH = Path(os.environ.get("SOLUTION_PATH", "/root/workspace/solution.py"))
CHOOSER = rdMolStandardize.LargestFragmentChooser()
UNCHARGER = rdMolStandardize.Uncharger()
SHORTLIST_FIELDS = (
    "rank",
    "compound_id",
    "canonical_smiles",
    "inchikey",
    "molecular_weight",
    "logp",
    "tpsa",
    "hbd",
    "hba",
    "rotatable_bonds",
    "qed",
    "max_similarity_to_actives",
    "alerts",
    "decision",
)
REJECT_FIELDS = (
    "compound_id",
    "canonical_smiles",
    "decision",
)
LEAD_LIKE_FIELDS = (
    "molecular_weight",
    "logp",
    "tpsa",
    "hbd",
    "hba",
    "rotatable_bonds",
)


def _round(value: float, precision: int) -> float:
    return round(float(value), precision)


def normalize_mol(mol: Chem.Mol) -> Chem.Mol:
    mol = Chem.Mol(mol)
    mol = rdMolStandardize.Cleanup(mol)
    mol = CHOOSER.choose(mol)
    mol = UNCHARGER.uncharge(mol)
    return mol


def default_library_dir() -> Path:
    candidate = DEFAULT_DATA_ROOT / "library"
    if candidate.exists():
        return candidate
    return TASK_ROOT / "environment" / "data" / "library"


def default_reference_dir() -> Path:
    candidate = DEFAULT_DATA_ROOT / "reference"
    if candidate.exists():
        return candidate
    return TASK_ROOT / "environment" / "data" / "reference"


def solution_path() -> Path:
    return DEFAULT_SOLUTION_PATH


def load_solution_module(path: Path | None = None):
    target = solution_path() if path is None else path
    spec = importlib.util.spec_from_file_location("solver_solution", target)
    assert spec is not None and spec.loader is not None, f"unable to load solution from {target}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def build_solution_output(
    library_dir: Path | None = None,
    reference_dir: Path | None = None,
    *,
    top_k: int = 20,
    path: Path | None = None,
) -> dict[str, Any]:
    library_dir = default_library_dir() if library_dir is None else library_dir
    reference_dir = default_reference_dir() if reference_dir is None else reference_dir
    module = load_solution_module(path=path)
    return module.build_leadlike_shortlist(
        str(library_dir),
        str(reference_dir / "actives.csv"),
        str(reference_dir / "rules.json"),
        str(reference_dir / "scoring.json"),
        top_k=top_k,
    )


def shortlist_projection(row: dict[str, Any]) -> dict[str, Any]:
    projected = {field: row[field] for field in SHORTLIST_FIELDS}
    projected["alerts"] = sorted(projected["alerts"])
    return projected


def rejected_projection(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "compound_id": row["compound_id"],
        "canonical_smiles": row["canonical_smiles"],
        "alerts": sorted(row["alerts"]),
        "decision": row["decision"],
    }


def _expected_reason_tokens(row: dict[str, Any]) -> set[str]:
    tokens = {f"alert:{alert.lower()}" for alert in row["alerts"]}
    lowered_reasons = [str(reason).lower() for reason in row["reasons"]]
    for field in LEAD_LIKE_FIELDS:
        if any(field in reason for reason in lowered_reasons):
            tokens.add(f"field:{field}")
    return tokens


def _reason_tokens(row: dict[str, Any]) -> set[str]:
    tokens = set()
    lowered_reasons = [str(reason).strip().lower() for reason in row["reasons"]]
    for alert in row["alerts"]:
        alert_name = alert.lower()
        if any(alert_name in reason and "alert" in reason for reason in lowered_reasons):
            tokens.add(f"alert:{alert_name}")
    for field in LEAD_LIKE_FIELDS:
        if any(field in reason for reason in lowered_reasons):
            tokens.add(f"field:{field}")
    return tokens


def assert_reason_semantics(actual: dict[str, Any], expected: dict[str, Any]) -> None:
    assert isinstance(actual["reasons"], list)
    assert actual["reasons"], f"{actual['compound_id']} must include at least one rejection reason"
    missing_tokens = _expected_reason_tokens(expected) - _reason_tokens(actual)
    assert not missing_tokens, f"{actual['compound_id']} is missing semantic rejection causes: {sorted(missing_tokens)}"

    for reason in actual["reasons"]:
        assert isinstance(reason, str)
        assert reason.strip(), f"{actual['compound_id']} contains an empty rejection reason"


def assert_output_matches_reference_behavior(actual: dict[str, Any], expected: dict[str, Any]) -> None:
    assert actual["summary"] == expected["summary"]

    actual_shortlist = [shortlist_projection(row) for row in actual["shortlist"]]
    expected_shortlist = [shortlist_projection(row) for row in expected["shortlist"]]
    assert actual_shortlist == expected_shortlist

    actual_rejected = sorted(actual["rejected_compounds"], key=lambda row: row["compound_id"])
    expected_rejected = sorted(expected["rejected_compounds"], key=lambda row: row["compound_id"])
    assert len(actual_rejected) == len(expected_rejected)

    for actual_row, expected_row in zip(actual_rejected, expected_rejected):
        assert rejected_projection(actual_row) == rejected_projection(expected_row)
        assert_reason_semantics(actual_row, expected_row)


def iter_library_records(library_dir: Path) -> list[tuple[str, Chem.Mol]]:
    records: list[tuple[str, Chem.Mol]] = []
    for path in sorted(library_dir.iterdir()):
        if path.suffix.lower() == ".sdf":
            for mol in Chem.SDMolSupplier(str(path), removeHs=False):
                if mol is None:
                    continue
                compound_id = mol.GetProp("compound_id") if mol.HasProp("compound_id") else mol.GetProp("_Name")
                records.append((compound_id, mol))
        elif path.suffix.lower() == ".smi":
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                smiles, compound_id = line.split()[:2]
                mol = Chem.MolFromSmiles(smiles)
                assert mol is not None, f"failed to parse {compound_id}"
                records.append((compound_id, mol))
    return records


def load_reference_inputs(reference_dir: Path) -> tuple[dict[str, Any], dict[str, Any], list[Chem.Mol]]:
    rules = json.loads((reference_dir / "rules.json").read_text(encoding="utf-8"))
    scoring = json.loads((reference_dir / "scoring.json").read_text(encoding="utf-8"))
    with (reference_dir / "actives.csv").open("r", encoding="utf-8", newline="") as handle:
        active_rows = list(csv.DictReader(handle))
    actives = [normalize_mol(Chem.MolFromSmiles(row["smiles"])) for row in active_rows]
    return rules, scoring, actives


def descriptor_row(mol: Chem.Mol, *, precision: int) -> dict[str, Any]:
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


def reference_output(
    library_dir: Path,
    reference_dir: Path,
    *,
    top_k: int = 20,
) -> dict[str, Any]:
    rules, scoring, actives = load_reference_inputs(reference_dir)
    precision = int(scoring["float_precision"])
    fpgen = rdFingerprintGenerator.GetMorganGenerator(
        radius=int(scoring["fingerprint"]["radius"]),
        fpSize=int(scoring["fingerprint"]["n_bits"]),
        includeChirality=bool(scoring["fingerprint"]["include_chirality"]),
    )
    active_fps = [fpgen.GetFingerprint(mol) for mol in actives]
    alert_patterns = {item["name"]: Chem.MolFromSmarts(item["smarts"]) for item in rules["alerts"]}

    records = iter_library_records(library_dir)
    grouped: dict[str, list[tuple[str, Chem.Mol]]] = {}
    for compound_id, mol in records:
        normalized = normalize_mol(mol)
        dedupe_key = Chem.MolToSmiles(normalized, isomericSmiles=True)
        grouped.setdefault(dedupe_key, []).append((compound_id, normalized))

    keep_rows: list[dict[str, Any]] = []
    reject_rows: list[dict[str, Any]] = []

    for dedupe_key, members in grouped.items():
        representative = min(compound_id for compound_id, _ in members)
        mol = members[0][1]
        row = descriptor_row(mol, precision=precision)
        row["compound_id"] = representative
        row["max_similarity_to_actives"] = _round(
            max(DataStructs.TanimotoSimilarity(fpgen.GetFingerprint(mol), active_fp) for active_fp in active_fps),
            precision,
        )
        alerts = sorted(name for name, patt in alert_patterns.items() if mol.HasSubstructMatch(patt))
        reasons = []
        for field, contract in rules["lead_like"].items():
            if contract["op"] == "<=" and row[field] > contract["value"]:
                reasons.append(f"{field}>{contract['value']}")
        for alert in alerts:
            reasons.append(f"alert:{alert}")

        if reasons:
            reject_rows.append(
                {
                    "compound_id": representative,
                    "canonical_smiles": row["canonical_smiles"],
                    "alerts": alerts,
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
                    "alerts": alerts,
                    "decision": "keep",
                }
            )

    def keep_sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
        key: list[Any] = []
        for item in scoring["shortlist_order"]:
            value = row[item["field"]]
            key.append(-value if item["direction"] == "desc" else value)
        return tuple(key)

    keep_rows.sort(key=keep_sort_key)
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


def build_shuffled_library_copy(source_dir: Path) -> Path:
    tmp_root = Path(tempfile.mkdtemp(prefix="leadlike-shuffle-"))
    target = tmp_root / "library"
    target.mkdir(parents=True, exist_ok=True)

    sdf_mols = []
    for mol in Chem.SDMolSupplier(str(source_dir / "catalog_core.sdf"), removeHs=False):
        if mol is not None:
            sdf_mols.append(mol)
    with Chem.SDWriter(str(target / "zzz_core.sdf")) as writer:
        for mol in reversed(sdf_mols):
            writer.write(mol)

    smi_lines = (source_dir / "supplemental.smi").read_text(encoding="utf-8").splitlines()
    (target / "aaa_extra.smi").write_text("\n".join(reversed(smi_lines)) + "\n", encoding="utf-8")
    (target / "mmm_vendors.csv").write_text(
        (source_dir / "vendors.csv").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return target


def build_metadata_swapped_copy(source_dir: Path) -> Path:
    tmp_root = Path(tempfile.mkdtemp(prefix="leadlike-metadata-"))
    target = tmp_root / "library"
    target.mkdir(parents=True, exist_ok=True)
    for name in ["catalog_core.sdf", "supplemental.smi"]:
        (target / name).write_bytes((source_dir / name).read_bytes())

    rows = []
    with (source_dir / "vendors.csv").open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(row)

    display_names = {row["compound_id"]: row["display_name"] for row in rows}
    display_names["LIB007_caffeine"], display_names["LIB012_nitrobenzene"] = (
        display_names["LIB012_nitrobenzene"],
        display_names["LIB007_caffeine"],
    )
    with (target / "vendors.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        for row in rows:
            row["display_name"] = display_names[row["compound_id"]]
            writer.writerow(row)
    return target


@pytest.fixture(scope="session")
def library_dir() -> Path:
    return default_library_dir()


@pytest.fixture(scope="session")
def reference_dir() -> Path:
    return default_reference_dir()


@pytest.fixture(scope="session")
def expected_output(library_dir: Path, reference_dir: Path) -> dict[str, Any]:
    return reference_output(library_dir, reference_dir)
