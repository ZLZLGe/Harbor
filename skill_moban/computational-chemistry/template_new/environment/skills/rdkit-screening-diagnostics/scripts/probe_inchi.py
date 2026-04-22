from __future__ import annotations

import json
import sys
from pathlib import Path

from rdkit import Chem


def first_mol(library_dir: Path):
    for path in sorted(library_dir.iterdir()):
        if path.suffix.lower() == ".smi":
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                smiles, compound_id = line.split()[:2]
                mol = Chem.MolFromSmiles(smiles)
                if mol is not None:
                    return compound_id, mol
        elif path.suffix.lower() == ".sdf":
            for mol in Chem.SDMolSupplier(str(path), removeHs=False):
                if mol is not None:
                    return mol.GetProp("compound_id"), mol
    return None, None


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: probe_inchi.py <library_dir>", file=sys.stderr)
        return 2

    library_dir = Path(argv[1])
    compound_id, mol = first_mol(library_dir)
    inchi_module = getattr(Chem, "inchi", None)
    result = {
        "has_chem_mol_to_inchikey": hasattr(Chem, "MolToInchiKey"),
        "has_inchi_module": inchi_module is not None,
        "inchi_module_available_flag": None if inchi_module is None else getattr(inchi_module, "INCHI_AVAILABLE", None),
        "has_inchi_module_mol_to_inchikey": False if inchi_module is None else hasattr(inchi_module, "MolToInchiKey"),
        "sample_compound_id": compound_id,
        "sample_canonical_smiles": None if mol is None else Chem.MolToSmiles(mol, isomericSmiles=True),
        "sample_inchikey": None,
    }

    if compound_id is not None and mol is not None:
        if hasattr(Chem, "MolToInchiKey"):
            try:
                result["sample_inchikey"] = Chem.MolToInchiKey(mol)
            except Exception as exc:  # pragma: no cover - probe output only
                result["sample_inchikey"] = f"error:{type(exc).__name__}"
        elif inchi_module is not None and hasattr(inchi_module, "MolToInchiKey"):
            try:
                result["sample_inchikey"] = inchi_module.MolToInchiKey(mol)
            except Exception as exc:  # pragma: no cover - probe output only
                result["sample_inchikey"] = f"error:{type(exc).__name__}"

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
