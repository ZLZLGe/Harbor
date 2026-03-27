#!/usr/bin/env python3
import json
from pathlib import Path

import numpy as np
from qutip import (
    basis,
    concurrence,
    entropy_vn,
    expect,
    mesolve,
    qeye,
    sigmam,
    sigmax,
    sigmay,
    sigmaz,
    tensor,
)


def load_problem(path="/root/entanglement_cases.json"):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _rounded(value):
    return round(float(np.real_if_close(value)), 6)


def _initial_state(kind):
    zero = basis(2, 0)
    one = basis(2, 1)
    if kind == "phi_plus":
        ket = (tensor(zero, zero) + tensor(one, one)).unit()
    elif kind == "psi_plus":
        ket = (tensor(zero, one) + tensor(one, zero)).unit()
    elif kind == "partial":
        ket = (0.92 * tensor(zero, zero) + 0.39 * tensor(one, one)).unit()
    else:
        raise ValueError(f"unknown initial state: {kind}")
    return ket.proj()


def _operators():
    sx1 = tensor(sigmax(), qeye(2))
    sx2 = tensor(qeye(2), sigmax())
    sy1 = tensor(sigmay(), qeye(2))
    sy2 = tensor(qeye(2), sigmay())
    sz1 = tensor(sigmaz(), qeye(2))
    sz2 = tensor(qeye(2), sigmaz())
    sm1 = tensor(sigmam(), qeye(2))
    sm2 = tensor(qeye(2), sigmam())
    total_excitation = sm1.dag() * sm1 + sm2.dag() * sm2
    return sx1, sx2, sy1, sy2, sz1, sz2, sm1, sm2, total_excitation


def analyze_case(case, tlist):
    sx1, sx2, sy1, sy2, sz1, sz2, sm1, sm2, total_excitation = _operators()
    rho0 = _initial_state(case["initial_state"])
    hamiltonian = (
        case["exchange_j"] * (sx1 * sx2 + sy1 * sy2)
        + 0.5 * case["detuning"] * (sz1 - sz2)
    )
    collapse_ops = [
        np.sqrt(case["gamma_relax"]) * sm1,
        np.sqrt(case["gamma_relax"]) * sm2,
    ]
    if case["gamma_dephase"] > 0:
        collapse_ops.extend(
            [
                np.sqrt(case["gamma_dephase"]) * sz1,
                np.sqrt(case["gamma_dephase"]) * sz2,
            ]
        )
    result = mesolve(hamiltonian, rho0, tlist, collapse_ops)
    states = result.states
    conc = np.asarray([concurrence(state) for state in states], dtype=float)
    entropies = np.asarray([entropy_vn(state.ptrace(0), base=np.e) for state in states], dtype=float)
    excitations = np.asarray([expect(total_excitation, state) for state in states], dtype=float)

    half_target = 0.5 * conc[0]
    half_index = next(index for index, value in enumerate(conc) if value <= half_target)

    return {
        "case_id": case["case_id"],
        "initial_concurrence": _rounded(conc[0]),
        "final_concurrence": _rounded(conc[-1]),
        "min_concurrence": _rounded(np.min(conc)),
        "half_life_time": _rounded(tlist[half_index]),
        "max_entropy_qubit_a": _rounded(np.max(entropies)),
        "mean_total_excitation": _rounded(np.mean(excitations)),
    }


def build_report(problem):
    grid = problem["time_grid"]
    tlist = np.linspace(grid["start"], grid["stop"], grid["points"])
    cases = [analyze_case(case, tlist) for case in problem["cases"]]
    ranking = [
        item["case_id"]
        for item in sorted(
            cases,
            key=lambda item: (-item["final_concurrence"], -item["max_entropy_qubit_a"], item["case_id"]),
        )
    ]
    return {
        "time_grid": grid,
        "cases": cases,
        "ranking_by_final_concurrence": ranking,
    }


def save_report(report, path):
    Path(path).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
