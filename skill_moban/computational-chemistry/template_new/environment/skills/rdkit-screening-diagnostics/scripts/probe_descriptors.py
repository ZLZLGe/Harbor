from __future__ import annotations

import json
import sys
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import Crippen, Descriptors, Lipinski, QED, rdMolDescriptors


def iter_mols(library_dir: Path):
    for path in sorted(library_dir.iterdir()):
        if path.suffix.lower() == ".smi":
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                smiles, compound_id = line.split()[:2]
                mol = Chem.MolFromSmiles(smiles)
                if mol is not None:
                    yield compound_id, mol
        elif path.suffix.lower() == ".sdf":
            for mol in Chem.SDMolSupplier(str(path), removeHs=False):
                if mol is not None:
                    yield mol.GetProp("compound_id"), mol


def descriptor_row(compound_id: str, mol: Chem.Mol) -> dict[str, object]:
    return {
        "compound_id": compound_id,
        "canonical_smiles": Chem.MolToSmiles(mol, isomericSmiles=True),
        "molecular_weight": round(Descriptors.MolWt(mol), 4),
        "exact_molecular_weight": round(Descriptors.ExactMolWt(mol), 4),
        "logp": round(Crippen.MolLogP(mol), 4),
        "tpsa": round(rdMolDescriptors.CalcTPSA(mol), 4),
        "hbd": Lipinski.NumHDonors(mol),
        "hba": Lipinski.NumHAcceptors(mol),
        "rotatable_bonds": Lipinski.NumRotatableBonds(mol),
        "qed": round(QED.qed(mol), 4),
    }


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: probe_descriptors.py <library_dir>", file=sys.stderr)
        return 2

    library_dir = Path(argv[1])
    rows = [descriptor_row(compound_id, mol) for compound_id, mol in iter_mols(library_dir)]
    print(json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
