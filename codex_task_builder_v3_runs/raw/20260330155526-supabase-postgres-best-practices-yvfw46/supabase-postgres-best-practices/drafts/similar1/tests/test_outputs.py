from __future__ import annotations

from pathlib import Path
import re
import subprocess

import pytest


WORKSPACE = Path("/workspace")
ENV_DIR = WORKSPACE / "environment"
WORKLOAD_DIR = ENV_DIR / "workload"
ANSWER = WORKSPACE / "answer" / "support_dashboard_fix.sql"
RESET_SCRIPT = ENV_DIR / "bin" / "reset-support-db.sh"
DATABASE = "support_dashboard"

WORKLOAD_FILES = [
    "agent_load.sql",
    "enterprise_backlog.sql",
    "latest_customer_reply.sql",
]


def run_command(command: list[str], *, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        input=input_text,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )


def reset_database() -> None:
    result = run_command([str(RESET_SCRIPT)])
    assert result.returncode == 0, result.stdout + "\n" + result.stderr


def psql_sql(sql: str, *, tuples_only: bool = True) -> str:
    command = ["psql", "-X", "-v", "ON_ERROR_STOP=1", "-d", DATABASE]
    if tuples_only:
        command.extend(["-A", "-t"])
    command.extend(["-c", sql])
    result = run_command(command)
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    return result.stdout.strip()


def psql_file(file_path: Path) -> str:
    result = run_command(["psql", "-X", "-v", "ON_ERROR_STOP=1", "-d", DATABASE, "-A", "-t", "-f", str(file_path)])
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    return result.stdout.strip()


def explain_query(file_path: Path) -> str:
    query = file_path.read_text()
    sql = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)\n{query}"
    return psql_sql(sql)


def apply_candidate() -> None:
    result = run_command(
        ["psql", "-X", "-v", "ON_ERROR_STOP=1", "-d", DATABASE, "-f", str(ANSWER)]
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr


def table_counts() -> str:
    sql = """
    SELECT 'support_agents', count(*) FROM support_agents
    UNION ALL
    SELECT 'support_customers', count(*) FROM support_customers
    UNION ALL
    SELECT 'tickets', count(*) FROM tickets
    UNION ALL
    SELECT 'ticket_events', count(*) FROM ticket_events
    ORDER BY 1;
    """
    return psql_sql(sql)


def workload_results() -> dict[str, str]:
    return {name: psql_file(WORKLOAD_DIR / name) for name in WORKLOAD_FILES}


def collect_baseline_snapshot() -> dict[str, object]:
    reset_database()
    return {
        "counts": table_counts(),
        "workload": workload_results(),
    }


def collect_candidate_snapshot() -> dict[str, object]:
    reset_database()
    apply_candidate()
    return {
        "counts": table_counts(),
        "workload": workload_results(),
        "reply_view_kind": psql_sql(
            "SELECT relkind FROM pg_class WHERE oid = 'dashboard_latest_customer_reply'::regclass;"
        ),
        "agent_plan": explain_query(WORKLOAD_DIR / "agent_load.sql"),
        "backlog_plan": explain_query(WORKLOAD_DIR / "enterprise_backlog.sql"),
        "reply_plan": explain_query(WORKLOAD_DIR / "latest_customer_reply.sql"),
        "lookup_plan": explain_query(WORKLOAD_DIR / "reply_lookup_diagnostic.sql"),
    }


@pytest.fixture(scope="session")
def baseline() -> dict[str, object]:
    return collect_baseline_snapshot()


@pytest.fixture(scope="session")
def candidate() -> dict[str, object]:
    return collect_candidate_snapshot()


def test_output_file_exists():
    assert ANSWER.exists(), f"Missing output file: {ANSWER}"


def test_output_file_stays_within_allowed_scope():
    content = ANSWER.read_text().lower()
    assert "enable_seqscan" not in content, "Do not change planner settings"
    assert not re.search(r"\b(insert|update|delete|truncate)\b", content), "Do not change table data"
    assert "alter table" not in content, "Do not change table definitions"


def test_base_table_counts_are_unchanged(baseline: dict[str, object], candidate: dict[str, object]):
    assert candidate["counts"] == baseline["counts"]


def test_workload_results_are_preserved(baseline: dict[str, object], candidate: dict[str, object]):
    assert candidate["workload"] == baseline["workload"]


def test_rewritten_reply_object_is_still_a_view(candidate: dict[str, object]):
    assert candidate["reply_view_kind"] == "v"


def test_agent_load_plan_avoids_ticket_sequential_scan(candidate: dict[str, object]):
    assert "Seq Scan on tickets" not in candidate["agent_plan"]


def test_backlog_plan_avoids_ticket_sequential_scan(candidate: dict[str, object]):
    assert "Seq Scan on tickets" not in candidate["backlog_plan"]


def test_latest_reply_plan_avoids_large_table_sequential_scans(candidate: dict[str, object]):
    plan = candidate["reply_plan"]
    assert "Seq Scan on tickets" not in plan
    assert "Seq Scan on ticket_events" not in plan


def test_reply_lookup_uses_index_only_scan_without_heap_fetches(candidate: dict[str, object]):
    plan = candidate["lookup_plan"]
    assert "Index Only Scan" in plan
    assert "Heap Fetches: 0" in plan
