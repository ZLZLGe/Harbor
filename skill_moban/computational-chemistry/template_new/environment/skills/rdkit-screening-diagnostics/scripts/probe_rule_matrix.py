from __future__ import annotations

import json
import sys
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import Crippen, Descriptors, Lipinski, rdMolDescriptors
from rdkit.Chem.MolStandardize import rdMolStandardize


CHOOSER = rdMolStandardize.LargestFragmentChooser()
UNCHARGER = rdMolStandardize.Uncharger()


def normalize(mol: Chem.Mol) -> Chem.Mol:
    mol = rdMolStandardize.Cleanup(mol)
    mol = CHOOSER.choose(mol)
    mol = UNCHARGER.uncharge(mol)
    return mol


def iter_mols(library_dir: Path):
    for path in sorted(library_dir.iterdir()):
        if path.suffix.lower() == ".smi":
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                smiles, compound_id = line.split()[:2]
                mol = Chem.MolFromSmiles(smiles)
                if mol is not None:
                    yield compound_id, normalize(mol)
        elif path.suffix.lower() == ".sdf":
            for mol in Chem.SDMolSupplier(str(path), removeHs=False):
                if mol is not None:
                    yield mol.GetProp("compound_id"), normalize(mol)


def descriptor_map(mol: Chem.Mol) -> dict[str, float | int]:
    return {
        "molecular_weight": round(Descriptors.MolWt(mol), 4),
        "logp": round(Crippen.MolLogP(mol), 4),
        "tpsa": round(rdMolDescriptors.CalcTPSA(mol), 4),
        "hbd": Lipinski.NumHDonors(mol),
        "hba": Lipinski.NumHAcceptors(mol),
        "rotatable_bonds": Lipinski.NumRotatableBonds(mol),
    }


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: probe_rule_matrix.py <library_dir> <rules_json>", file=sys.stderr)
        return 2

    library_dir = Path(argv[1])
    rules = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
    alert_patterns = {item["name"]: Chem.MolFromSmarts(item["smarts"]) for item in rules["alerts"]}

    for compound_id, mol in iter_mols(library_dir):
        row = descriptor_map(mol)
        checks = {}
        for field, contract in rules["lead_like"].items():
            checks[field] = row[field] <= contract["value"]
        alerts = sorted(name for name, patt in alert_patterns.items() if mol.HasSubstructMatch(patt))
        print(
            json.dumps(
                {
                    "compound_id": compound_id,
                    "canonical_smiles": Chem.MolToSmiles(mol, isomericSmiles=True),
                    "checks": checks,
                    "alerts": alerts,
                }
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
