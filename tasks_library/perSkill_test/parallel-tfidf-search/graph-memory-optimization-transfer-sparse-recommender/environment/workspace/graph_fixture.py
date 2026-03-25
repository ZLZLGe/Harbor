#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from pathlib import Path


def build_edges(num_users: int, seed: int) -> list[tuple[int, int]]:
    rng = random.Random(seed)
    community_size = 48
    communities = [
        list(range(start, min(start + community_size, num_users)))
        for start in range(0, num_users, community_size)
    ]
    edges: set[tuple[int, int]] = set()

    for members in communities:
        size = len(members)
        if size < 2:
            continue

        local_offsets = [1, 2, 3]
        for index, user_id in enumerate(members):
            for offset in local_offsets:
                if offset >= size:
                    continue
                friend_id = members[(index + offset) % size]
                edges.add((min(user_id, friend_id), max(user_id, friend_id)))

            extra_links = 2 if size >= 8 else 1
            for _ in range(extra_links):
                friend_id = rng.choice(members)
                if friend_id != user_id:
                    edges.add((min(user_id, friend_id), max(user_id, friend_id)))

    for community_index in range(len(communities) - 1):
        left_members = communities[community_index]
        right_members = communities[community_index + 1]
        bridge_count = max(2, min(len(left_members), len(right_members)) // 6)

        for bridge_index in range(bridge_count):
            left_user_id = left_members[(bridge_index * 7 + seed + community_index) % len(left_members)]
            right_user_id = right_members[(bridge_index * 11 + seed + community_index) % len(right_members)]
            edges.add((min(left_user_id, right_user_id), max(left_user_id, right_user_id)))

            if rng.random() < 0.35:
                left_user_id = rng.choice(left_members)
                right_user_id = rng.choice(right_members)
                edges.add((min(left_user_id, right_user_id), max(left_user_id, right_user_id)))

    return sorted(edges)


def choose_targets(num_users: int, num_targets: int) -> list[int]:
    if num_targets >= num_users:
        return list(range(num_users))

    stride = max(1, math.floor(num_users / num_targets))
    targets: list[int] = []
    candidate = stride // 2

    while len(targets) < num_targets:
        user_id = min(num_users - 1, candidate)
        if not targets or user_id != targets[-1]:
            targets.append(user_id)
        candidate += stride

    return targets[:num_targets]


def write_graph_fixture(
    edges_path: str | Path,
    targets_path: str | Path,
    num_users: int,
    seed: int,
    top_n: int = 6,
    num_targets: int = 32,
) -> None:
    friendships = build_edges(num_users, seed)
    target_user_ids = choose_targets(num_users, num_targets)

    edges_path = Path(edges_path)
    targets_path = Path(targets_path)
    edges_path.parent.mkdir(parents=True, exist_ok=True)
    targets_path.parent.mkdir(parents=True, exist_ok=True)

    with edges_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["user_id", "friend_id"])
        writer.writeheader()
        for user_id, friend_id in friendships:
            writer.writerow({"user_id": user_id, "friend_id": friend_id})

    with targets_path.open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "num_users": num_users,
                "top_n": top_n,
                "target_user_ids": target_user_ids,
            },
            handle,
            indent=2,
            ensure_ascii=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic social graph fixtures.")
    parser.add_argument("--edges-output", required=True)
    parser.add_argument("--targets-output", required=True)
    parser.add_argument("--num-users", type=int, required=True)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--top-n", type=int, default=6)
    parser.add_argument("--num-targets", type=int, default=32)
    args = parser.parse_args()

    write_graph_fixture(
        edges_path=args.edges_output,
        targets_path=args.targets_output,
        num_users=args.num_users,
        seed=args.seed,
        top_n=args.top_n,
        num_targets=args.num_targets,
    )


if __name__ == "__main__":
    main()
