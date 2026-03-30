from __future__ import annotations

from pathlib import Path
import os
import subprocess
import time

import psycopg2
import pytest


WORKSPACE = Path("/workspace")
ENV_DIR = WORKSPACE / "environment"
ANSWER = WORKSPACE / "answer" / "worker_queue_patch.sql"
RESET_SCRIPT = ENV_DIR / "bin" / "reset-worker-queue-db.sh"
READY_PROBE = ENV_DIR / "probes" / "ready_claim_probe.sql"
BACKLOG_PROBE = ENV_DIR / "probes" / "tenant_backlog_probe.sql"
DATABASE = "worker_queue"


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


def apply_candidate() -> None:
    result = run_command(
        ["psql", "-X", "-v", "ON_ERROR_STOP=1", "-d", DATABASE, "-f", str(ANSWER)]
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr


def connect_as(user: str):
    return psycopg2.connect(
        dbname=DATABASE,
        user=user,
        host=os.environ["PGHOST"],
        port=os.environ["PGPORT"],
    )


def fetch_scalar(sql: str) -> str:
    result = run_command(["psql", "-X", "-A", "-t", "-d", DATABASE, "-c", sql])
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    return result.stdout.strip()


def snapshot_seed_state() -> dict[str, object]:
    with connect_as("postgres") as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                  count(*) AS total_jobs,
                  count(*) FILTER (WHERE status = 'pending') AS pending_jobs,
                  count(*) FILTER (WHERE status = 'processing') AS processing_jobs,
                  count(*) FILTER (WHERE status = 'completed') AS completed_jobs,
                  count(*) FILTER (WHERE status = 'failed') AS failed_jobs,
                  sum(priority) AS total_priority,
                  sum(attempts) AS total_attempts
                FROM queue_jobs
                """
            )
            summary = cur.fetchone()

            cur.execute(
                """
                SELECT tenant_slug, status, count(*)
                FROM queue_jobs
                GROUP BY tenant_slug, status
                ORDER BY tenant_slug, status
                """
            )
            by_tenant = cur.fetchall()

            cur.execute(
                """
                SELECT
                  id,
                  tenant_slug,
                  status,
                  priority,
                  attempts,
                  to_char(run_at AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS')
                FROM queue_jobs
                WHERE id BETWEEN 1 AND 8
                ORDER BY id
                """
            )
            sample_rows = cur.fetchall()

    return {
        "summary": summary,
        "by_tenant": by_tenant,
        "sample_rows": sample_rows,
    }


def explain_as_worker(query_path: Path, tenant: str) -> str:
    with connect_as("queue_worker") as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT set_config('app.current_tenant_id', %s, false)", (tenant,))
            cur.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)\n{query_path.read_text()}")
            rows = cur.fetchall()
    return "\n".join(row[0] for row in rows)


def prepare_candidate_database() -> None:
    reset_database()
    apply_candidate()


@pytest.fixture
def candidate_database():
    prepare_candidate_database()


def test_output_file_exists():
    assert ANSWER.exists(), f"Missing output file: {ANSWER}"


def test_patch_does_not_change_seeded_rows_when_applied():
    reset_database()
    baseline = snapshot_seed_state()
    apply_candidate()
    candidate = snapshot_seed_state()
    assert candidate == baseline


def test_claim_function_uses_skip_locked(candidate_database):
    definition = fetch_scalar(
        "SELECT pg_get_functiondef('claim_next_job(text)'::regprocedure);"
    )
    assert "SKIP LOCKED" in definition.upper()


def test_queue_jobs_has_rls_enabled_and_forced(candidate_database):
    flags = fetch_scalar(
        """
        SELECT relrowsecurity::text || ',' || relforcerowsecurity::text
        FROM pg_class
        WHERE oid = 'queue_jobs'::regclass
        """
    )
    assert flags == "true,true"


def test_worker_role_only_sees_rows_for_its_tenant(candidate_database):
    with connect_as("queue_worker") as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT set_config('app.current_tenant_id', %s, false)", ("tenant_alpha",))
            cur.execute("SELECT DISTINCT tenant_slug FROM queue_jobs ORDER BY tenant_slug")
            assert cur.fetchall() == [("tenant_alpha",)]

            cur.execute("SELECT set_config('app.current_tenant_id', %s, false)", ("tenant_beta",))
            cur.execute("SELECT DISTINCT tenant_slug FROM queue_jobs ORDER BY tenant_slug")
            assert cur.fetchall() == [("tenant_beta",)]


def test_worker_role_can_update_own_rows_but_not_other_tenants(candidate_database):
    with connect_as("queue_worker") as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT set_config('app.current_tenant_id', %s, false)", ("tenant_alpha",))
            cur.execute(
                "UPDATE queue_jobs SET locked_by = 'scratch-alpha' WHERE id = 1 RETURNING id"
            )
            assert cur.fetchall() == [(1,)]

            cur.execute(
                "UPDATE queue_jobs SET locked_by = 'scratch-alpha' WHERE id = 3 RETURNING id"
            )
            assert cur.fetchall() == []
        conn.rollback()


def test_claim_function_returns_due_job_for_current_tenant(candidate_database):
    with connect_as("queue_worker") as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT set_config('app.current_tenant_id', %s, false)", ("tenant_beta",))
            cur.execute("SELECT * FROM claim_next_job(%s)", ("beta-worker",))
            row = cur.fetchone()
            assert row[0] == 3
            assert row[1] == "tenant_beta"
        conn.rollback()


def test_concurrent_claims_do_not_block_and_claim_distinct_jobs(candidate_database):
    conn1 = connect_as("queue_worker")
    conn2 = connect_as("queue_worker")

    try:
        with conn1.cursor() as cur1, conn2.cursor() as cur2:
            cur1.execute("SELECT set_config('app.current_tenant_id', %s, false)", ("tenant_alpha",))
            cur2.execute("SELECT set_config('app.current_tenant_id', %s, false)", ("tenant_alpha",))

            cur1.execute("SELECT * FROM claim_next_job(%s)", ("worker-1",))
            first = cur1.fetchone()

            cur2.execute("SET LOCAL statement_timeout = '1000ms'")
            started = time.monotonic()
            cur2.execute("SELECT * FROM claim_next_job(%s)", ("worker-2",))
            elapsed = time.monotonic() - started
            second = cur2.fetchone()

            assert first[0] == 1
            assert second[0] == 2
            assert first[0] != second[0]
            assert elapsed < 1.0
    finally:
        conn1.rollback()
        conn2.rollback()
        conn1.close()
        conn2.close()


def test_ready_claim_probe_avoids_seq_scan(candidate_database):
    plan = explain_as_worker(READY_PROBE, "tenant_alpha")
    assert "Seq Scan on queue_jobs" not in plan
    assert any(token in plan for token in ("Index Scan", "Index Only Scan", "Bitmap Heap Scan"))


def test_tenant_backlog_probe_avoids_seq_scan(candidate_database):
    plan = explain_as_worker(BACKLOG_PROBE, "tenant_alpha")
    assert "Seq Scan on queue_jobs" not in plan
    assert any(token in plan for token in ("Index Scan", "Index Only Scan", "Bitmap Heap Scan"))
