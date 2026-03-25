from __future__ import annotations

import csv
import importlib.util
import subprocess
import sys
import textwrap
from pathlib import Path


SCALA_FILE = Path("/root/TelemetryIncidentRollups.scala")
PYTHON_REFERENCE = Path("/root/telemetry_incident_rollups.py")
DEFAULT_ALERTS = Path("/root/alerts.csv")
DEFAULT_RULES = Path("/root/window_rules.conf")

HARNESS_SOURCE = textwrap.dedent(
    """
    import TelemetryIncidentRollups._

    object TelemetryHarness {
      def main(args: Array[String]): Unit = {
        val alerts = loadAlerts(args(0))
        val config = loadWindowConfig(args(1))
        val incidents = rollupIncidents(alerts, config)
        renderIncidentLines(incidents).foreach(println)
        buildServiceDigest(incidents, config.severityRank).foreach(println)
      }
    }
    """
)


def load_reference_module():
    spec = importlib.util.spec_from_file_location("telemetry_incident_rollups_ref", PYTHON_REFERENCE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def compile_scala(build_dir: Path) -> None:
    assert SCALA_FILE.exists(), "缺少 /root/TelemetryIncidentRollups.scala"
    source_text = SCALA_FILE.read_text(encoding="utf-8")
    assert "package " not in source_text, "不应包含 package 声明"

    harness_file = build_dir / "TelemetryHarness.scala"
    harness_file.write_text(HARNESS_SOURCE, encoding="utf-8")

    compile_proc = subprocess.run(
        [
            "scalac",
            "-d",
            str(build_dir),
            str(SCALA_FILE),
            str(harness_file),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert compile_proc.returncode == 0, compile_proc.stderr or compile_proc.stdout


def run_scala(build_dir: Path, alerts_path: Path, rules_path: Path) -> list[str]:
    run_proc = subprocess.run(
        [
            "scala",
            "-cp",
            str(build_dir),
            "TelemetryHarness",
            str(alerts_path),
            str(rules_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert run_proc.returncode == 0, run_proc.stderr or run_proc.stdout
    return [line.strip() for line in run_proc.stdout.splitlines() if line.strip()]


def expected_lines(module, alerts_path: Path, rules_path: Path) -> list[str]:
    alerts = module.load_alerts(str(alerts_path))
    config = module.load_window_config(str(rules_path))
    incidents = module.rollup_incidents(alerts, config)
    return module.render_incident_lines(incidents) + module.build_service_digest(incidents, config.severity_rank)


def write_alerts_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["service", "severity", "started_at", "ended_at", "source", "alert_code"],
        )
        writer.writeheader()
        writer.writerows(rows)


def test_telemetry_rollups_match_reference_on_default_and_custom_inputs(tmp_path: Path):
    module = load_reference_module()
    build_dir = tmp_path / "scala-build"
    build_dir.mkdir()
    compile_scala(build_dir)

    actual_default = run_scala(build_dir, DEFAULT_ALERTS, DEFAULT_RULES)
    assert actual_default == expected_lines(module, DEFAULT_ALERTS, DEFAULT_RULES)

    custom_alerts = tmp_path / "custom-alerts.csv"
    custom_rules = tmp_path / "custom-rules.conf"

    write_alerts_csv(
        custom_alerts,
        [
            {
                "service": "catalog",
                "severity": "warning",
                "started_at": "2026-03-10T08:00:00Z",
                "ended_at": "2026-03-10T08:03:00Z",
                "source": "edge-a",
                "alert_code": "lat-2",
            },
            {
                "service": "catalog",
                "severity": "warning",
                "started_at": "2026-03-10T08:09:00Z",
                "ended_at": "2026-03-10T08:10:00Z",
                "source": "edge-b",
                "alert_code": "lat-3",
            },
            {
                "service": "catalog",
                "severity": "info",
                "started_at": "2026-03-10T09:00:00Z",
                "ended_at": "2026-03-10T09:01:00Z",
                "source": "edge-a",
                "alert_code": "cfg-1",
            },
            {
                "service": "auth",
                "severity": "critical",
                "started_at": "2026-03-10T10:00:00Z",
                "ended_at": "2026-03-10T10:01:00Z",
                "source": "login-1",
                "alert_code": "auth-9",
            },
            {
                "service": "auth",
                "severity": "critical",
                "started_at": "2026-03-10T10:04:00Z",
                "ended_at": "2026-03-10T10:05:00Z",
                "source": "login-1",
                "alert_code": "auth-10",
            },
        ],
    )

    custom_rules.write_text(
        textwrap.dedent(
            """
            default_merge_gap_minutes=8
            severity_rank=critical,warning,info

            [auth]
            merge_gap_minutes=5
            page_threshold=3
            summary_prefix=rapid
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    actual_custom = run_scala(build_dir, custom_alerts, custom_rules)
    assert actual_custom == expected_lines(module, custom_alerts, custom_rules)
