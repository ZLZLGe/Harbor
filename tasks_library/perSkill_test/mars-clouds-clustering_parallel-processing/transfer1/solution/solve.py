#!/usr/bin/env python3
import csv
from itertools import product
from pathlib import Path

from joblib import Parallel, delayed


def load_routes(path):
    routes = []
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            routes.append(
                {
                    "route_id": row["route_id"],
                    "distance_km": float(row["distance_km"]),
                    "elevation_gain": float(row["elevation_gain"]),
                    "rock_density": float(row["rock_density"]),
                    "criticality": float(row["criticality"]),
                }
            )
    return routes


def route_targets(route):
    opt_interval = 18.0 + route["distance_km"] * 0.45 + route["rock_density"] * 6.0
    opt_crew = 2.0 + min(2.0, route["criticality"] * 0.7)
    opt_drone = 0.15 + min(0.55, route["rock_density"] * 0.9)
    return opt_interval, opt_crew, opt_drone


def evaluate_policy(policy, routes):
    inspect_interval, crew_size, drone_share = policy
    total_score = 0.0
    total_delay = 0.0

    for route in routes:
        opt_interval, opt_crew, opt_drone = route_targets(route)
        coverage = max(
            0.0,
            100.0
            - abs(inspect_interval - opt_interval) * 3.0
            - abs(crew_size - opt_crew) * 8.0
            - abs(drone_share - opt_drone) * 22.0,
        )
        delay = (
            route["distance_km"] * (1.2 - crew_size * 0.12)
            + route["elevation_gain"] * 0.03
            + route["rock_density"] * 4.0
            + abs(inspect_interval - opt_interval) * 0.8
            + abs(drone_share - opt_drone) * 10.0
        )
        total_score += coverage * route["criticality"] - delay * 0.4
        total_delay += delay

    return {
        "inspect_interval": int(inspect_interval),
        "crew_size": int(crew_size),
        "drone_share": round(float(drone_share), 1),
        "total_score": round(total_score, 4),
        "total_delay": round(total_delay, 4),
    }


def main():
    routes = load_routes(Path("/root/data/routes.csv"))

    policies = list(product([15, 20, 25, 30], [2, 3, 4], [0.1, 0.3, 0.5, 0.7]))
    rows = Parallel(n_jobs=-1, backend="loky")(
        delayed(evaluate_policy)(policy, routes) for policy in policies
    )

    rows.sort(
        key=lambda x: (
            -x["total_score"],
            x["total_delay"],
            x["inspect_interval"],
            x["crew_size"],
            x["drone_share"],
        )
    )
    top_rows = rows[:6]

    output_path = Path("/outputs/transfer1_route_rankings.csv")
    with output_path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "rank",
                "inspect_interval",
                "crew_size",
                "drone_share",
                "total_score",
                "total_delay",
            ],
        )
        writer.writeheader()
        for idx, row in enumerate(top_rows, start=1):
            out = dict(row)
            out["rank"] = idx
            writer.writerow(out)


if __name__ == "__main__":
    main()
