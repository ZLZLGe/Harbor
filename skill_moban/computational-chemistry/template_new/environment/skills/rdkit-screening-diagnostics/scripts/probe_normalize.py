from __future__ import annotations

import sys
from pathlib import Path

from rdkit import Chem
from rdkit.Chem.MolStandardize import rdMolStandardize


CHOOSER = rdMolStandardize.LargestFragmentChooser()
UNCHARGER = rdMolStandardize.Uncharger()


def normalize(mol: Chem.Mol) -> Chem.Mol:
    mol = rdMolStandardize.Cleanup(mol)
    mol = CHOOSER.choose(mol)
    mol = UNCHARGER.uncharge(mol)
    return mol


def iter_raw(library_dir: Path):
    for path in sorted(library_dir.iterdir()):
        if path.suffix.lower() == ".smi":
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                smiles, compound_id = line.split()[:2]
                yield compound_id, smiles
        elif path.suffix.lower() == ".sdf":
            for mol in Chem.SDMolSupplier(str(path), removeHs=False):
                if mol is None:
                    continue
                yield mol.GetProp("compound_id"), Chem.MolToSmiles(mol, isomericSmiles=True)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: probe_normalize.py <library_dir>", file=sys.stderr)
        return 2

    library_dir = Path(argv[1])
    for compound_id, smiles in iter_raw(library_dir):
        mol = Chem.MolFromSmiles(smiles)
        normalized = normalize(mol)
        print(
            f"{compound_id}\traw={smiles}\tcanonical={Chem.MolToSmiles(mol, isomericSmiles=True)}\t"
            f"normalized={Chem.MolToSmiles(normalized, isomericSmiles=True)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
