#!/bin/bash
set -euo pipefail

mkdir -p /root/workspace

python3 - <<'PY'
import json
import time

import pubchempy as pcp
from rdkit import Chem
from rdkit import DataStructs
from rdkit.Chem import AllChem
from rdkit import RDLogger

RDLogger.DisableLog("rdApp.*")

INPUT_PATH = "/root/vendor_catalog.json"
OUTPUT_PATH = "/root/workspace/analogue_ranking.json"
FINGERPRINT_GENERATOR = AllChem.GetMorganGenerator(
    radius=2,
    fpSize=2048,
    includeChirality=True,
)


def resolve_compound(query_name, retries=3):
    last_error = None
    for attempt in range(retries):
        try:
            compounds = pcp.get_compounds(query_name, "name")
            if not compounds:
                raise ValueError(f"PubChem returned no compound for {query_name!r}")
            compound = compounds[0]
            smiles = compound.isomeric_smiles or compound.canonical_smiles
            if not smiles:
                raise ValueError(f"No usable SMILES for {query_name!r}")
            canonical_name = compound.iupac_name or query_name
            return {
                "cid": compound.cid,
                "canonical_name": canonical_name,
                "smiles": smiles,
            }
        except Exception as exc:
            last_error = exc
            time.sleep(1 + attempt)
    raise RuntimeError(f"Failed to resolve {query_name!r}") from last_error


def fingerprint_from_smiles(smiles):
    molecule = Chem.MolFromSmiles(smiles)
    if molecule is None:
        raise ValueError(f"Invalid SMILES: {smiles}")
    return FINGERPRINT_GENERATOR.GetFingerprint(molecule)


with open(INPUT_PATH, "r", encoding="utf-8") as handle:
    payload = json.load(handle)

lead = resolve_compound(payload["lead_input_name"])
lead_fp = fingerprint_from_smiles(lead["smiles"])

ranking = []
for candidate in payload["candidates"]:
    resolved = resolve_compound(candidate["listing_name"])
    candidate_fp = fingerprint_from_smiles(resolved["smiles"])
    similarity = DataStructs.TanimotoSimilarity(lead_fp, candidate_fp)
    ranking.append(
        {
            "vendor_sku": candidate["vendor_sku"],
            "supplier": candidate["supplier"],
            "input_name": candidate["listing_name"],
            "cid": resolved["cid"],
            "canonical_name": resolved["canonical_name"],
            "similarity": similarity,
        }
    )

ranking.sort(
    key=lambda item: (
        -item["similarity"],
        item["canonical_name"].casefold(),
        item["vendor_sku"],
    )
)
ranking = ranking[: payload["top_k"]]

for index, item in enumerate(ranking, start=1):
    item["rank"] = index
    item["similarity"] = round(item["similarity"], 6)

result = {
    "lead_input_name": payload["lead_input_name"],
    "lead_cid": lead["cid"],
    "lead_canonical_name": lead["canonical_name"],
    "ranking": ranking,
}

with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
    json.dump(result, handle, indent=2, ensure_ascii=True)
    handle.write("\n")
PY
