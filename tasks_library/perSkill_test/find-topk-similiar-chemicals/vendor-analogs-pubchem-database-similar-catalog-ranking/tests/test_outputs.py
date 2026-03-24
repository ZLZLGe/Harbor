#!/usr/bin/env python3
import json
import math
import os
import sys
import time
from pathlib import Path

import pubchempy as pcp
from rdkit import Chem
from rdkit import DataStructs
from rdkit.Chem import AllChem
from rdkit import RDLogger

RDLogger.DisableLog("rdApp.*")

INPUT_PATH = Path("/root/vendor_catalog.json")
OUTPUT_PATH = Path("/root/workspace/analogue_ranking.json")
REWARD_PATH = Path("/logs/verifier/reward.txt")
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


def build_expected_output():
    payload = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    lead = resolve_compound(payload["lead_input_name"])
    lead_fp = fingerprint_from_smiles(lead["smiles"])

    ranking = []
    for candidate in payload["candidates"]:
        resolved = resolve_compound(candidate["listing_name"])
        similarity = DataStructs.TanimotoSimilarity(
            lead_fp,
            fingerprint_from_smiles(resolved["smiles"]),
        )
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

    return {
        "lead_input_name": payload["lead_input_name"],
        "lead_cid": lead["cid"],
        "lead_canonical_name": lead["canonical_name"],
        "ranking": ranking,
    }


def assert_close(actual, expected, path):
    if not math.isclose(float(actual), float(expected), rel_tol=0.0, abs_tol=1e-6):
        raise AssertionError(f"{path} mismatch: expected {expected}, got {actual}")


def verify_output(actual, expected):
    if actual.get("lead_input_name") != expected["lead_input_name"]:
        raise AssertionError("lead_input_name mismatch")
    if actual.get("lead_cid") != expected["lead_cid"]:
        raise AssertionError("lead_cid mismatch")
    if actual.get("lead_canonical_name") != expected["lead_canonical_name"]:
        raise AssertionError("lead_canonical_name mismatch")

    actual_ranking = actual.get("ranking")
    if not isinstance(actual_ranking, list):
        raise AssertionError("ranking must be a list")
    if len(actual_ranking) != len(expected["ranking"]):
        raise AssertionError("ranking length mismatch")

    for idx, (actual_item, expected_item) in enumerate(zip(actual_ranking, expected["ranking"]), start=1):
        for field in ["rank", "vendor_sku", "supplier", "input_name", "cid", "canonical_name"]:
            if actual_item.get(field) != expected_item[field]:
                raise AssertionError(
                    f"ranking[{idx - 1}].{field} mismatch: expected {expected_item[field]!r}, got {actual_item.get(field)!r}"
                )
        if "similarity" not in actual_item:
            raise AssertionError(f"ranking[{idx - 1}].similarity missing")
        assert_close(actual_item["similarity"], expected_item["similarity"], f"ranking[{idx - 1}].similarity")


def write_reward(score):
    REWARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    REWARD_PATH.write_text(f"{score}\n", encoding="utf-8")


def main():
    if not OUTPUT_PATH.exists():
        raise AssertionError("analogue_ranking.json was not created")

    actual = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    expected = build_expected_output()
    verify_output(actual, expected)

    write_reward(1.0)
    print("Output matches the expected analogue ranking.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        write_reward(0.0)
        print(f"Verification failed: {exc}", file=sys.stderr)
        sys.exit(1)
