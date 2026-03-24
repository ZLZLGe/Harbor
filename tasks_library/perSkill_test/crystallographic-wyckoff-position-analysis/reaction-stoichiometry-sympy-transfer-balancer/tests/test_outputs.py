#!/usr/bin/env python3

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path


EXPECTED = {
    "combustion_ethane": {
        "reactants": ["C2H6", "O2"],
        "products": ["CO2", "H2O"],
        "elements": ["C", "H", "O"],
        "stoichiometry_matrix": [
            [2, 0, -1, 0],
            [6, 0, 0, -2],
            [0, 2, -2, -1],
        ],
        "nullspace_basis": ["1", "7/2", "2", "3"],
        "integer_coefficients": [2, 7, 4, 6],
        "balanced_equation": "2 C2H6 + 7 O2 -> 4 CO2 + 6 H2O",
    },
    "pyrite_roasting": {
        "reactants": ["FeS2", "O2"],
        "products": ["Fe2O3", "SO2"],
        "elements": ["Fe", "O", "S"],
        "stoichiometry_matrix": [
            [1, 0, -2, 0],
            [0, 2, -3, -2],
            [2, 0, 0, -1],
        ],
        "nullspace_basis": ["1", "11/4", "1/2", "2"],
        "integer_coefficients": [4, 11, 2, 8],
        "balanced_equation": "4 FeS2 + 11 O2 -> 2 Fe2O3 + 8 SO2",
    },
    "permanganate_hcl": {
        "reactants": ["KMnO4", "HCl"],
        "products": ["KCl", "MnCl2", "H2O", "Cl2"],
        "elements": ["Cl", "H", "K", "Mn", "O"],
        "stoichiometry_matrix": [
            [0, 1, -1, -2, 0, -2],
            [0, 1, 0, 0, -2, 0],
            [1, 0, -1, 0, 0, 0],
            [1, 0, 0, -1, 0, 0],
            [4, 0, 0, 0, -1, 0],
        ],
        "nullspace_basis": ["1", "8", "1", "1", "4", "5/2"],
        "integer_coefficients": [2, 16, 2, 2, 8, 5],
        "balanced_equation": "2 KMnO4 + 16 HCl -> 2 KCl + 2 MnCl2 + 8 H2O + 5 Cl2",
    },
    "thermite": {
        "reactants": ["Al", "Fe2O3"],
        "products": ["Al2O3", "Fe"],
        "elements": ["Al", "Fe", "O"],
        "stoichiometry_matrix": [
            [1, 0, -2, 0],
            [0, 2, 0, -1],
            [0, 3, -3, 0],
        ],
        "nullspace_basis": ["1", "1/2", "1/2", "1"],
        "integer_coefficients": [2, 1, 1, 2],
        "balanced_equation": "2 Al + Fe2O3 -> Al2O3 + 2 Fe",
    },
    "phosphate_reduction": {
        "reactants": ["Ca3(PO4)2", "SiO2", "C"],
        "products": ["P4", "CaSiO3", "CO"],
        "elements": ["C", "Ca", "O", "P", "Si"],
        "stoichiometry_matrix": [
            [0, 0, 1, 0, 0, -1],
            [3, 0, 0, 0, -1, 0],
            [8, 2, 0, 0, -3, -1],
            [2, 0, 0, -4, 0, 0],
            [0, 1, 0, 0, -1, 0],
        ],
        "nullspace_basis": ["1", "3", "5", "1/2", "3", "5"],
        "integer_coefficients": [2, 6, 10, 1, 6, 10],
        "balanced_equation": "2 Ca3(PO4)2 + 6 SiO2 + 10 C -> P4 + 6 CaSiO3 + 10 CO",
    },
    "double_replacement": {
        "reactants": ["Na3PO4", "MgCl2"],
        "products": ["NaCl", "Mg3(PO4)2"],
        "elements": ["Cl", "Mg", "Na", "O", "P"],
        "stoichiometry_matrix": [
            [0, 2, -1, 0],
            [0, 1, 0, -3],
            [3, 0, -1, 0],
            [4, 0, 0, -8],
            [1, 0, 0, -2],
        ],
        "nullspace_basis": ["1", "3/2", "3", "1/2"],
        "integer_coefficients": [2, 3, 6, 1],
        "balanced_equation": "2 Na3PO4 + 3 MgCl2 -> 6 NaCl + Mg3(PO4)2",
    },
}


def load_module():
    solution_path = Path("/root/workspace/reaction_balancer.py")
    if not solution_path.exists():
        raise FileNotFoundError(f"Missing solution file: {solution_path}")

    spec = importlib.util.spec_from_file_location("reaction_balancer", solution_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_reward(score: float) -> None:
    os.makedirs("/logs/verifier", exist_ok=True)
    Path("/logs/verifier/reward.txt").write_text(f"{score:.2f}\n")


def main() -> int:
    total_checks = 0
    passed_checks = 0

    try:
        module = load_module()
        result = module.balance_reaction_cases("/root/data/reaction_cases.json")
        total_checks += 1
        if result != EXPECTED:
            print("Function output mismatch.")
            print("Expected:")
            print(json.dumps(EXPECTED, indent=2, sort_keys=True))
            print("Got:")
            print(json.dumps(result, indent=2, sort_keys=True))
            write_reward(0.0)
            return 1
        passed_checks += 1

        subprocess.run([sys.executable, "/root/workspace/reaction_balancer.py"], check=True)
        total_checks += 1
        output_path = Path("/root/workspace/reaction_balancer_results.json")
        if not output_path.exists():
            print("Missing output JSON file.")
            write_reward(0.0)
            return 1

        written = json.loads(output_path.read_text())
        if written != EXPECTED:
            print("Direct-execution JSON mismatch.")
            print("Expected:")
            print(json.dumps(EXPECTED, indent=2, sort_keys=True))
            print("Got:")
            print(json.dumps(written, indent=2, sort_keys=True))
            write_reward(0.0)
            return 1
        passed_checks += 1

    except Exception as exc:
        print(f"Test execution failed: {exc}")
        write_reward(0.0)
        return 1

    score = passed_checks / total_checks if total_checks else 0.0
    print(f"Passed {passed_checks}/{total_checks} checks.")
    write_reward(score)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
