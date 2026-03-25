#!/usr/bin/env python3

from __future__ import annotations

import csv
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

sys.path.insert(0, "/root/workspace")

from graph_fixture import write_graph_fixture


SOLUTION_PATH = Path("/root/workspace/graph_recommender_solution.py")
BASELINE_PATH = Path("/root/workspace/social_graph_baseline.py")
SAMPLE_EDGES_PATH = Path("/root/workspace/sample_friendships.csv")
SAMPLE_TARGETS_PATH = Path("/root/workspace/sample_targets.json")
MEMORY_LIMIT_MB = 180
USAGE_WRAPPER = """
import json
import resource
import subprocess
import sys

completed = subprocess.run(sys.argv[1:], capture_output=True, text=True)
print(json.dumps({
    "returncode": completed.returncode,
    "stdout": completed.stdout,
    "stderr": completed.stderr,
    "max_rss_kb": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
}))
"""


def load_request(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_friendships(path: Path) -> list[tuple[int, int]]:
    friendships: list[tuple[int, int]] = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            friendships.append((int(row["user_id"]), int(row["friend_id"])))
    return friendships


def oracle_report(edges_path: Path, targets_path: Path) -> dict[str, object]:
    request = load_request(targets_path)
    num_users = int(request["num_users"])
    top_n = int(request["top_n"])
    target_user_ids = [int(user_id) for user_id in request["target_user_ids"]]

    neighbors: list[list[int]] = [[] for _ in range(num_users)]
    friendships = load_friendships(edges_path)
    for user_id, friend_id in friendships:
        neighbors[user_id].append(friend_id)
        neighbors[friend_id].append(user_id)

    recommendations = []
    for user_id in target_user_ids:
        direct_friends = set(neighbors[user_id])
        candidate_counts: Counter[int] = Counter()

        for mutual_user_id in direct_friends:
            for candidate_user_id in neighbors[mutual_user_id]:
                if candidate_user_id == user_id or candidate_user_id in direct_friends:
                    continue
                candidate_counts[candidate_user_id] += 1

        ranked = sorted(candidate_counts.items(), key=lambda item: (-item[1], item[0]))[:top_n]
        recommendations.append(
            {
                "user_id": user_id,
                "recommendations": [
                    {
                        "candidate_user_id": candidate_user_id,
                        "mutual_friend_count": mutual_friend_count,
                    }
                    for candidate_user_id, mutual_friend_count in ranked
                ],
            }
        )

    return {
        "graph": {
            "num_users": num_users,
            "num_friendships": len(friendships),
            "top_n": top_n,
        },
        "recommendations": recommendations,
    }


def run_script(script_path: Path, edges_path: Path, targets_path: Path, output_path: Path) -> dict[str, object]:
    subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--edges",
            str(edges_path),
            "--targets",
            str(targets_path),
            "--output",
            str(output_path),
        ],
        check=True,
    )
    with output_path.open(encoding="utf-8") as handle:
        return json.load(handle)


def run_with_usage(script_path: Path, edges_path: Path, targets_path: Path, output_path: Path) -> tuple[dict[str, object], float]:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            USAGE_WRAPPER,
            sys.executable,
            str(script_path),
            "--edges",
            str(edges_path),
            "--targets",
            str(targets_path),
            "--output",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["returncode"] == 0, payload["stderr"]

    with output_path.open(encoding="utf-8") as handle:
        report = json.load(handle)
    return report, float(payload["max_rss_kb"]) / 1024


def assert_contract(report: dict[str, object], request: dict[str, object]) -> None:
    assert set(report) == {"graph", "recommendations"}

    graph = report["graph"]
    assert isinstance(graph, dict)
    assert set(graph) == {"num_users", "num_friendships", "top_n"}
    assert graph["num_users"] == request["num_users"]
    assert graph["top_n"] == request["top_n"]
    assert isinstance(graph["num_friendships"], int)

    recommendations = report["recommendations"]
    assert isinstance(recommendations, list)
    assert len(recommendations) == len(request["target_user_ids"])
    for expected_user_id, row in zip(request["target_user_ids"], recommendations):
        assert set(row) == {"user_id", "recommendations"}
        assert row["user_id"] == expected_user_id
        assert isinstance(row["recommendations"], list)
        assert len(row["recommendations"]) <= int(request["top_n"])
        for recommendation in row["recommendations"]:
            assert set(recommendation) == {"candidate_user_id", "mutual_friend_count"}
            assert isinstance(recommendation["candidate_user_id"], int)
            assert isinstance(recommendation["mutual_friend_count"], int)
            assert recommendation["mutual_friend_count"] > 0


def test_solution_file_exists():
    assert SOLUTION_PATH.exists(), "missing /root/workspace/graph_recommender_solution.py"


def test_sample_fixture_matches_oracle(tmp_path: Path):
    output_path = tmp_path / "sample_report.json"
    produced = run_script(SOLUTION_PATH, SAMPLE_EDGES_PATH, SAMPLE_TARGETS_PATH, output_path)
    expected = oracle_report(SAMPLE_EDGES_PATH, SAMPLE_TARGETS_PATH)

    assert produced == expected
    assert_contract(produced, load_request(SAMPLE_TARGETS_PATH))


def test_matches_baseline_on_small_generated_fixture(tmp_path: Path):
    edges_path = tmp_path / "small_friendships.csv"
    targets_path = tmp_path / "small_targets.json"
    baseline_output = tmp_path / "baseline_report.json"
    solution_output = tmp_path / "solution_report.json"

    write_graph_fixture(edges_path, targets_path, num_users=320, seed=17, top_n=5, num_targets=18)

    expected = run_script(BASELINE_PATH, edges_path, targets_path, baseline_output)
    produced = run_script(SOLUTION_PATH, edges_path, targets_path, solution_output)
    assert produced == expected


def test_large_fixture_correctness_and_contract(tmp_path: Path):
    edges_path = tmp_path / "large_friendships.csv"
    targets_path = tmp_path / "large_targets.json"
    output_path = tmp_path / "large_report.json"

    write_graph_fixture(edges_path, targets_path, num_users=14000, seed=29, top_n=6, num_targets=40)

    produced = run_script(SOLUTION_PATH, edges_path, targets_path, output_path)
    expected = oracle_report(edges_path, targets_path)

    assert produced == expected
    assert_contract(produced, load_request(targets_path))


def test_memory_budget_on_large_fixture(tmp_path: Path):
    edges_path = tmp_path / "memory_friendships.csv"
    targets_path = tmp_path / "memory_targets.json"
    output_path = tmp_path / "memory_report.json"

    write_graph_fixture(edges_path, targets_path, num_users=28000, seed=41, top_n=6, num_targets=72)

    report, rss_mb = run_with_usage(SOLUTION_PATH, edges_path, targets_path, output_path)
    assert rss_mb <= MEMORY_LIMIT_MB, f"peak RSS {rss_mb:.1f} MB exceeds {MEMORY_LIMIT_MB} MB"
    assert_contract(report, load_request(targets_path))
