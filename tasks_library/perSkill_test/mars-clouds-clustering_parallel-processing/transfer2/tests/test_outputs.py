#!/usr/bin/env python3
import json
from itertools import product
from pathlib import Path

OUTPUT = Path("/outputs/transfer2_zone_plan.json")
ZONES = Path("/root/data/zones.json")


def eval_policy(zone, policy):
    vent_rate, humidifier_level, reheat_level = policy

    predicted_temp = 20.0 + reheat_level * 1.4 - vent_rate * 0.8 + zone["thermal_mass"] * 0.1
    predicted_humidity = 40.0 + humidifier_level * 8.0 - vent_rate * 3.0 + zone["occupancy"] * 0.6

    temp_error = abs(predicted_temp - zone["target_temp"])
    humidity_error = abs(predicted_humidity - zone["target_humidity"])

    comfort = max(0.0, 100.0 - temp_error * 6.0 - humidity_error * 2.0)
    energy = (
        vent_rate * 4.0
        + humidifier_level * 3.0
        + reheat_level * 5.0
        + zone["occupancy"] * 0.2
        + zone["thermal_mass"] * 0.15
    )
    utility = comfort - energy * 1.7

    return {
        "policy": {
            "vent_rate": int(vent_rate),
            "humidifier_level": int(humidifier_level),
            "reheat_level": int(reheat_level),
        },
        "comfort": round(comfort, 4),
        "energy": round(energy, 4),
        "utility": round(utility, 4),
    }


def pick_best(zone):
    policies = product([1, 2, 3, 4], [0, 1, 2, 3], [0, 1, 2])
    scored = [eval_policy(zone, policy) for policy in policies]
    scored.sort(
        key=lambda x: (
            -x["utility"],
            x["energy"],
            x["policy"]["vent_rate"],
            x["policy"]["humidifier_level"],
            x["policy"]["reheat_level"],
        )
    )
    best = scored[0]
    return {
        "zone_id": zone["zone_id"],
        "selected_policy": best["policy"],
        "comfort": best["comfort"],
        "energy": best["energy"],
        "utility": best["utility"],
    }


def expected_output():
    zones = json.loads(ZONES.read_text())
    selected = [pick_best(zone) for zone in zones]
    selected.sort(key=lambda x: x["zone_id"])

    mean_comfort = round(sum(z["comfort"] for z in selected) / len(selected), 4)
    mean_energy = round(sum(z["energy"] for z in selected) / len(selected), 4)
    mean_utility = round(sum(z["utility"] for z in selected) / len(selected), 4)

    return {
        "zones": selected,
        "fleet_summary": {
            "mean_comfort": mean_comfort,
            "mean_energy": mean_energy,
            "mean_utility": mean_utility,
        },
    }


def main():
    assert OUTPUT.exists(), "missing /outputs/transfer2_zone_plan.json"
    actual = json.loads(OUTPUT.read_text())
    expected = expected_output()
    assert actual == expected, f"zone plan mismatch\nexpected={expected}\nactual={actual}"


if __name__ == "__main__":
    main()
