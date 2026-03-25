#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def load_request(path: str | Path) -> dict[str, object]:
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def load_friendships(path: str | Path) -> list[tuple[int, int]]:
    friendships: list[tuple[int, int]] = []
    with Path(path).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            friendships.append((int(row["user_id"]), int(row["friend_id"])))
    return friendships


def build_dense_matrix(num_users: int, friendships: list[tuple[int, int]]) -> list[list[int]]:
    adjacency = [[0] * num_users for _ in range(num_users)]
    for user_id, friend_id in friendships:
        adjacency[user_id][friend_id] = 1
        adjacency[friend_id][user_id] = 1
    return adjacency


def recommend_for_user(adjacency: list[list[int]], user_id: int, top_n: int) -> list[dict[str, int]]:
    num_users = len(adjacency)
    ranked: list[tuple[int, int]] = []

    for candidate_user_id in range(num_users):
        if candidate_user_id == user_id or adjacency[user_id][candidate_user_id]:
            continue

        mutual_friend_count = 0
        for mutual_user_id in range(num_users):
            if adjacency[user_id][mutual_user_id] and adjacency[candidate_user_id][mutual_user_id]:
                mutual_friend_count += 1

        if mutual_friend_count > 0:
            ranked.append((candidate_user_id, mutual_friend_count))

    ranked.sort(key=lambda item: (-item[1], item[0]))
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

    friendships = load_friendships(edges_path)
    adjacency = build_dense_matrix(num_users, friendships)

    return {
        "graph": {
            "num_users": num_users,
            "num_friendships": len(friendships),
            "top_n": top_n,
        },
        "recommendations": [
            {
                "user_id": user_id,
                "recommendations": recommend_for_user(adjacency, user_id, top_n),
            }
            for user_id in target_user_ids
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Dense baseline for social graph recommendations.")
    parser.add_argument("--edges", required=True)
    parser.add_argument("--targets", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    report = build_report(args.edges, args.targets)
    with Path(args.output).open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=True)


if __name__ == "__main__":
    main()
