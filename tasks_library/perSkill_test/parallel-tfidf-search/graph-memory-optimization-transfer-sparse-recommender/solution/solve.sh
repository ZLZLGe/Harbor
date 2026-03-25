#!/bin/bash
set -euo pipefail

cat > /root/workspace/graph_recommender_solution.py <<'PY'
#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


def load_request(path: str | Path) -> dict[str, object]:
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def load_sparse_graph(path: str | Path, num_users: int) -> tuple[list[list[int]], int]:
    neighbors: list[list[int]] = [[] for _ in range(num_users)]
    num_friendships = 0

    with Path(path).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            user_id = int(row["user_id"])
            friend_id = int(row["friend_id"])
            neighbors[user_id].append(friend_id)
            neighbors[friend_id].append(user_id)
            num_friendships += 1

    return neighbors, num_friendships


def recommend_for_user(neighbors: list[list[int]], user_id: int, top_n: int) -> list[dict[str, int]]:
    direct_friends = set(neighbors[user_id])
    candidate_counts: Counter[int] = Counter()

    for mutual_user_id in direct_friends:
        for candidate_user_id in neighbors[mutual_user_id]:
            if candidate_user_id == user_id or candidate_user_id in direct_friends:
                continue
            candidate_counts[candidate_user_id] += 1

    ranked = sorted(candidate_counts.items(), key=lambda item: (-item[1], item[0]))
    return [
        {
            "candidate_user_id": candidate_user_id,
            "mutual_friend_count": mutual_friend_count,
        }
        for candidate_user_id, mutual_friend_count in ranked[:top_n]
    ]


def build_report(edges_path: str | Path, targets_path: str | Path) -> dict[str, object]:
    request = load_request(targets_path)
    num_users = int(request["num_users"])
    top_n = int(request["top_n"])
    target_user_ids = [int(user_id) for user_id in request["target_user_ids"]]

    neighbors, num_friendships = load_sparse_graph(edges_path, num_users)
    recommendations = []
    for user_id in target_user_ids:
        recommendations.append(
            {
                "user_id": user_id,
                "recommendations": recommend_for_user(neighbors, user_id, top_n),
            }
        )

    return {
        "graph": {
            "num_users": num_users,
            "num_friendships": num_friendships,
            "top_n": top_n,
        },
        "recommendations": recommendations,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Sparse social graph recommender.")
    parser.add_argument("--edges", required=True)
    parser.add_argument("--targets", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    report = build_report(args.edges, args.targets)
    with Path(args.output).open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=True)


if __name__ == "__main__":
    main()
PY

chmod +x /root/workspace/graph_recommender_solution.py
