#!/usr/bin/env python3

import json
import os
import sys

sys.path.insert(0, "/root/workspace")

from solid_state_stoichiometry import balance_solid_state_reactions


INPUT_PATH = "/root/reaction_specs/solid_state_reactions.json"

EXPECTED = {
    "batio3_from_carbonate": {
        "equation": "BaCO3 + TiO2 -> BaTiO3 + CO2",
        "precursors": {"BaCO3": 1, "TiO2": 1},
        "target": {"BaTiO3": 1},
        "byproducts": {"CO2": 1},
    },
    "licoo2_from_lithium_carbonate": {
        "equation": "6 Li2CO3 + 4 Co3O4 + O2 -> 12 LiCoO2 + 6 CO2",
        "precursors": {"Li2CO3": 6, "Co3O4": 4, "O2": 1},
        "target": {"LiCoO2": 12},
        "byproducts": {"CO2": 6},
    },
    "limn2o4_with_oxygen_release": {
        "equation": "2 Li2CO3 + 8 MnO2 -> 4 LiMn2O4 + 2 CO2 + O2",
        "precursors": {"Li2CO3": 2, "MnO2": 8},
        "target": {"LiMn2O4": 4},
        "byproducts": {"CO2": 2, "O2": 1},
    },
    "ybco_123_route": {
        "equation": "2 Y2O3 + 8 BaCO3 + 12 CuO + O2 -> 4 YBa2Cu3O7 + 8 CO2",
        "precursors": {"Y2O3": 2, "BaCO3": 8, "CuO": 12, "O2": 1},
        "target": {"YBa2Cu3O7": 4},
        "byproducts": {"CO2": 8},
    },
    "lafeo3_direct_combination": {
        "equation": "La2O3 + Fe2O3 -> 2 LaFeO3",
        "precursors": {"La2O3": 1, "Fe2O3": 1},
        "target": {"LaFeO3": 2},
        "byproducts": {},
    },
}


def _load_spec():
    with open(INPUT_PATH, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return {reaction["reaction_id"]: reaction for reaction in data["reactions"]}


def _species_list(reaction_spec):
    return reaction_spec["precursors"], [reaction_spec["target"]], reaction_spec["byproducts"]


def main():
    reaction_specs = _load_spec()
    result = balance_solid_state_reactions(INPUT_PATH)

    total_checks = 0
    passed_checks = 0
    failures = []

    total_checks += 1
    if set(result.get("reactions", {})) != set(EXPECTED):
        failures.append("reaction id set mismatch")
    else:
        passed_checks += 1

    for reaction_id, expected in EXPECTED.items():
        total_checks += 1
        actual = result["reactions"].get(reaction_id)
        if actual is None:
            failures.append(f"{reaction_id}: missing reaction output")
            continue

        if actual["normalized_equation"] == expected["equation"]:
            passed_checks += 1
        else:
            failures.append(f"{reaction_id}: equation mismatch")

        total_checks += 1
        if actual["coefficients"]["precursors"] == expected["precursors"]:
            passed_checks += 1
        else:
            failures.append(f"{reaction_id}: precursor coefficients mismatch")

        total_checks += 1
        if actual["coefficients"]["target"] == expected["target"]:
            passed_checks += 1
        else:
            failures.append(f"{reaction_id}: target coefficient mismatch")

        total_checks += 1
        if actual["coefficients"]["byproducts"] == expected["byproducts"]:
            passed_checks += 1
        else:
            failures.append(f"{reaction_id}: byproduct coefficients mismatch")

        total_checks += 1
        balance = actual["element_balance"]
        keys = list(balance)
        if keys == sorted(keys) and all(entry["balanced"] for entry in balance.values()):
            passed_checks += 1
        else:
            failures.append(f"{reaction_id}: balance table ordering or flags mismatch")

        total_checks += 1
        reaction_spec = reaction_specs[reaction_id]
        precursor_species, target_species, byproduct_species = _species_list(reaction_spec)

        left_totals = {}
        for species in precursor_species:
            coefficient = actual["coefficients"]["precursors"][species["name"]]
            for element, count in species["elements"].items():
                left_totals[element] = left_totals.get(element, 0) + coefficient * count

        right_totals = {}
        for species in target_species + byproduct_species:
            if species["name"] in actual["coefficients"]["target"]:
                coefficient = actual["coefficients"]["target"][species["name"]]
            else:
                coefficient = actual["coefficients"]["byproducts"][species["name"]]
            for element, count in species["elements"].items():
                right_totals[element] = right_totals.get(element, 0) + coefficient * count

        if left_totals == right_totals and all(
            balance[element]["left"] == left_totals[element] and balance[element]["right"] == right_totals[element]
            for element in sorted(left_totals)
        ):
            passed_checks += 1
        else:
            failures.append(f"{reaction_id}: element totals do not match reported balance")

    score = passed_checks / total_checks if total_checks else 0.0

    print("=" * 80)
    print("Transfer task: solid-state stoichiometry")
    print("=" * 80)
    print(f"Checks passed: {passed_checks}/{total_checks}")
    if failures:
        print("Failures:")
        for failure in failures:
            print(f"- {failure}")

    os.makedirs("/logs/verifier", exist_ok=True)
    with open("/logs/verifier/reward.txt", "w", encoding="utf-8") as handle:
        handle.write(f"{score:.2f}\n")

    return 0 if score == 1.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
