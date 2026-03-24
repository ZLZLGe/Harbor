import csv
import json
from pathlib import Path

import numpy as np


def load_case(config_path):
    return json.loads(Path(config_path).read_text(encoding="utf-8"))


def load_schedule(csv_path):
    with Path(csv_path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            {
                "time_s": float(row["time_s"]),
                "loads": np.array(
                    [float(row["active_load_pu"]), float(row["reactive_load_pu"])],
                    dtype=float,
                ),
            }
            for row in reader
        ]


def nominal_reference(case):
    operating_point = case["nominal_operating_point"]
    return (
        np.array(operating_point["reference_state"], dtype=float),
        np.array(operating_point["reference_input"], dtype=float),
    )


def dynamics(state, control, case):
    params = case["model_parameters"]
    _, reference_input = nominal_reference(case)
    delta_f_hz, delta_v_pu = np.asarray(state, dtype=float)
    active_load_pu, reactive_load_pu = np.asarray(control, dtype=float)

    voltage_ratio = (params["nominal_voltage_pu"] + delta_v_pu) / params["nominal_voltage_pu"]
    active_term = (
        active_load_pu
        * voltage_ratio ** params["active_voltage_exponent"]
        * (1.0 + params["active_frequency_coupling"] * delta_f_hz)
    )
    reactive_term = (
        reactive_load_pu
        * voltage_ratio ** params["reactive_voltage_exponent"]
        * (1.0 + params["reactive_frequency_coupling"] * delta_f_hz)
    )

    return np.array(
        [
            (
                -delta_f_hz
                - params["active_droop_gain"] * (active_term - reference_input[0])
            )
            / params["tau_frequency"],
            (
                -delta_v_pu
                - params["reactive_droop_gain"] * (reactive_term - reference_input[1])
            )
            / params["tau_voltage"],
        ],
        dtype=float,
    )
