from __future__ import annotations

import sys
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import rdmolops


def iter_smiles(library_dir: Path):
    for path in sorted(library_dir.iterdir()):
        if path.suffix.lower() == ".smi":
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                smiles, compound_id = line.split()[:2]
                yield compound_id, smiles
        elif path.suffix.lower() == ".sdf":
            supplier = Chem.SDMolSupplier(str(path), removeHs=False)
            for mol in supplier:
                if mol is None:
                    continue
                yield mol.GetProp("compound_id"), Chem.MolToSmiles(mol, isomericSmiles=True)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: probe_parse.py <library_dir>", file=sys.stderr)
        return 2

    library_dir = Path(argv[1])
    for compound_id, smiles in iter_smiles(library_dir):
        unsanitized = Chem.MolFromSmiles(smiles, sanitize=False)
        problems = rdmolops.DetectChemistryProblems(unsanitized) if unsanitized is not None else []
        sanitized = Chem.MolFromSmiles(smiles)
        canonical = None if sanitized is None else Chem.MolToSmiles(sanitized, isomericSmiles=True)
        fragments = 0 if sanitized is None else len(Chem.GetMolFrags(sanitized))
        print(
            f"{compound_id}\tparsed={sanitized is not None}\tfragments={fragments}\t"
            f"problems={len(problems)}\tcanonical={canonical}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
