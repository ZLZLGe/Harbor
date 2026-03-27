#!/usr/bin/env python3
import json
from pathlib import Path

import numpy as np
from qutip import basis, fidelity, qeye, sesolve, sigmax, sigmay, sigmaz


PROBE_ORDER = ["0", "1", "+", "-", "+i", "-i"]


def load_problem(path="/root/gate_cases.json"):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _rounded(value):
    return round(float(np.real_if_close(value)), 6)


def _state(label):
    zero = basis(2, 0)
    one = basis(2, 1)
    if label == "0":
        return zero
    if label == "1":
        return one
    if label == "+":
        return (zero + one).unit()
    if label == "-":
        return (zero - one).unit()
    if label == "+i":
        return (zero + 1j * one).unit()
    if label == "-i":
        return (zero - 1j * one).unit()
    raise ValueError(f"unknown probe label: {label}")


def _target_unitary(problem):
    if problem["target_gate"] != "rx_pi_over_2":
        raise ValueError(f"unsupported target gate: {problem['target_gate']}")
    return (-1j * (np.pi / 4.0) * sigmax()).expm()


def _apply_segments(initial_state, problem, candidate):
    state = initial_state
    drift = 0.5 * problem["drift_detuning"] * sigmaz()
    for segment in candidate["segments"]:
        hamiltonian = drift + segment["ux"] * sigmax() + segment["uy"] * sigmay()
        result = sesolve(hamiltonian, state, [0.0, segment["duration"]])
        state = result.states[-1]
    return state


def analyze_case(problem, candidate):
    target = _target_unitary(problem)
    probe_fidelities = {}
    fidelity_values = []
    for label in PROBE_ORDER:
        initial_state = _state(label)
        target_state = target * initial_state
        final_state = _apply_segments(initial_state, problem, candidate)
        value = float(fidelity(target_state, final_state))
        probe_fidelities[label] = _rounded(value)
        fidelity_values.append(value)

    min_fidelity = min(fidelity_values)
    return {
        "case_id": candidate["case_id"],
        "average_fidelity": _rounded(np.mean(fidelity_values)),
        "max_infidelity": _rounded(1.0 - min_fidelity),
        "total_duration": _rounded(sum(segment["duration"] for segment in candidate["segments"])),
        "probe_fidelities": probe_fidelities,
    }


def build_report(problem):
    candidates = [analyze_case(problem, candidate) for candidate in problem["cases"]]
    ranking = [
        item["case_id"]
        for item in sorted(
            candidates,
            key=lambda item: (
                -item["average_fidelity"],
                item["max_infidelity"],
                item["total_duration"],
                item["case_id"],
            ),
        )
    ]
    return {
        "target_gate": problem["target_gate"],
        "best_candidate": ranking[0],
        "candidates": candidates,
        "ranking": ranking,
    }


def save_report(report, path):
    Path(path).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
