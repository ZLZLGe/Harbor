#!/usr/bin/env python3
import json
from pathlib import Path

import numpy as np
from qutip import basis, destroy, expect, qeye, sigmam, sigmaz, steadystate, tensor, wigner


def load_problem(path="/root/steady_state_cases.json"):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _float(value):
    return float(np.real_if_close(value))


def _rounded(value):
    return round(_float(value), 6)


def _build_case(case):
    cavity_dim = case["cavity_dim"]
    a = tensor(destroy(cavity_dim), qeye(2))
    sm = tensor(qeye(cavity_dim), sigmam())
    sz = tensor(qeye(cavity_dim), sigmaz())
    excited_proj = tensor(qeye(cavity_dim), basis(2, 1) * basis(2, 1).dag())

    hamiltonian = (
        case["delta_c"] * a.dag() * a
        + 0.5 * case["delta_q"] * sz
        + case["coupling_g"] * (a.dag() * sm + a * sm.dag())
        + case["drive"] * (a + a.dag())
    )

    collapse_ops = [
        np.sqrt(case["kappa"]) * a,
        np.sqrt(case["gamma"]) * sm,
    ]
    if case["pump"] > 0:
        collapse_ops.append(np.sqrt(case["pump"]) * sm.dag())
    if case["dephasing"] > 0:
        collapse_ops.append(np.sqrt(case["dephasing"]) * sz)

    rho_ss = steadystate(hamiltonian, collapse_ops, method="direct")
    cavity_state = rho_ss.ptrace(0)
    qubit_state = rho_ss.ptrace(1)
    return cavity_state, qubit_state


def analyze_case(case, grid):
    cavity_state, qubit_state = _build_case(case)
    cavity_dim = case["cavity_dim"]
    xvec = np.linspace(grid["min"], grid["max"], grid["points"])
    w = wigner(cavity_state, xvec, xvec)
    dx = xvec[1] - xvec[0]
    mid = len(xvec) // 2
    sample_indices = [0, len(xvec) // 4, mid, (3 * len(xvec)) // 4, len(xvec) - 1]

    return {
        "case_id": case["case_id"],
        "mean_photon": _rounded(expect(destroy(cavity_dim).dag() * destroy(cavity_dim), cavity_state)),
        "qubit_excitation": _rounded(expect(excited_proj := basis(2, 1) * basis(2, 1).dag(), qubit_state)),
        "wigner_center": _rounded(w[mid, mid]),
        "wigner_min": _rounded(np.min(w)),
        "wigner_max": _rounded(np.max(w)),
        "normalization": _rounded(np.sum(w) * dx * dx),
        "centerline_signature": [_rounded(w[mid, index]) for index in sample_indices],
    }


def build_report(problem):
    grid = problem["grid"]
    case_summaries = [analyze_case(case, grid) for case in problem["cases"]]
    ranking = [
        item["case_id"]
        for item in sorted(case_summaries, key=lambda item: (-item["mean_photon"], item["case_id"]))
    ]
    return {
        "grid": grid,
        "cases": case_summaries,
        "ranking_by_mean_photon": ranking,
    }


def save_report(report, path):
    Path(path).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
