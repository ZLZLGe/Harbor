#!/usr/bin/env python3
import csv
import json
from pathlib import Path

import numpy as np
from qutip import destroy, displace, expect, mesolve, thermal_dm


FIELDNAMES = [
    "case_id",
    "n_initial",
    "n_final",
    "half_decay_time",
    "integrated_photon_number",
    "final_x_expectation",
    "max_abs_x",
]


def load_problem(path="/root/relaxation_cases.json"):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _rounded(value):
    return round(float(np.real_if_close(value)), 6)


def _time_grid(problem):
    grid = problem["time_grid"]
    return np.linspace(grid["start"], grid["stop"], grid["points"])


def _initial_state(case):
    dim = case["hilbert_dim"]
    alpha = complex(case["alpha_real"], case["alpha_imag"])
    displaced = displace(dim, alpha)
    thermal = thermal_dm(dim, case["initial_thermal_n"])
    return displaced * thermal * displaced.dag()


def analyze_case(case, tlist):
    dim = case["hilbert_dim"]
    a = destroy(dim)
    n_op = a.dag() * a
    x_op = a + a.dag()
    rho0 = _initial_state(case)
    hamiltonian = case["detuning"] * n_op
    c_ops = [
        np.sqrt(case["kappa"] * (case["bath_thermal_n"] + 1.0)) * a,
    ]
    if case["bath_thermal_n"] > 0:
        c_ops.append(np.sqrt(case["kappa"] * case["bath_thermal_n"]) * a.dag())
    result = mesolve(hamiltonian, rho0, tlist, c_ops, e_ops=[n_op, x_op])
    n_values = np.asarray(result.expect[0], dtype=float)
    x_values = np.asarray(result.expect[1], dtype=float)

    n_initial = n_values[0]
    n_target = case["bath_thermal_n"]
    midpoint = n_target + 0.5 * (n_initial - n_target)
    half_index = next(index for index, value in enumerate(n_values) if value <= midpoint)

    return {
        "case_id": case["case_id"],
        "n_initial": _rounded(n_initial),
        "n_final": _rounded(n_values[-1]),
        "half_decay_time": _rounded(tlist[half_index]),
        "integrated_photon_number": _rounded(np.trapz(n_values, tlist)),
        "final_x_expectation": _rounded(x_values[-1]),
        "max_abs_x": _rounded(np.max(np.abs(x_values))),
    }


def build_rows(problem):
    tlist = _time_grid(problem)
    rows = [analyze_case(case, tlist) for case in problem["cases"]]
    return sorted(rows, key=lambda row: row["case_id"])


def save_rows(rows, path):
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
