from __future__ import annotations

import csv
import importlib.util
import subprocess
import sys
from pathlib import Path


SCALA_FILE = Path("/root/SupportTopicReport.scala")
PYTHON_REFERENCE = Path("/root/support_topic_report.py")
DEFAULT_TICKETS = Path("/root/tickets.tsv")
DEFAULT_STOPWORDS = Path("/root/stopwords.txt")


def load_reference_module():
    spec = importlib.util.spec_from_file_location("support_topic_report_ref", PYTHON_REFERENCE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def compile_scala(build_dir: Path) -> None:
    assert SCALA_FILE.exists(), "缺少 /root/SupportTopicReport.scala"
    source_text = SCALA_FILE.read_text(encoding="utf-8")
    assert "package " not in source_text, "不应包含 package 声明"

    compile_proc = subprocess.run(
        ["scalac", "-d", str(build_dir), str(SCALA_FILE)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert compile_proc.returncode == 0, compile_proc.stderr or compile_proc.stdout


def run_scala_report(build_dir: Path, tickets_path: Path, stopwords_path: Path, output_path: Path) -> str:
    run_proc = subprocess.run(
        [
            "scala",
            "-cp",
            str(build_dir),
            "SupportTopicReport",
            str(tickets_path),
            str(stopwords_path),
            str(output_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert run_proc.returncode == 0, run_proc.stderr or run_proc.stdout
    return output_path.read_text(encoding="utf-8")


def expected_report(module, tickets_path: Path, stopwords_path: Path) -> str:
    tickets = module.load_tickets(str(tickets_path))
    stopwords = module.load_stopwords(str(stopwords_path))
    return "\n".join(module.build_report_lines(tickets, stopwords)) + "\n"


def write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["ticket_id", "queue", "agent", "status", "subject", "body"],
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerows(rows)


def test_support_topic_report_matches_reference_on_default_and_custom_inputs(tmp_path: Path):
    module = load_reference_module()
    build_dir = tmp_path / "scala-build"
    build_dir.mkdir()
    compile_scala(build_dir)

    default_output = tmp_path / "default-report.txt"
    actual_default = run_scala_report(build_dir, DEFAULT_TICKETS, DEFAULT_STOPWORDS, default_output)
    assert actual_default == expected_report(module, DEFAULT_TICKETS, DEFAULT_STOPWORDS)

    custom_tickets = tmp_path / "custom-tickets.tsv"
    custom_stopwords = tmp_path / "custom-stopwords.txt"
    custom_output = tmp_path / "custom-report.txt"

    write_tsv(
        custom_tickets,
        [
            {
                "ticket_id": "X-1",
                "queue": "bot",
                "agent": "Iris",
                "status": "open",
                "subject": "Login loop after password reset",
                "body": "Password email never arrives and login loop stays active.",
            },
            {
                "ticket_id": "X-2",
                "queue": "bot",
                "agent": "Mika",
                "status": "pending",
                "subject": "Email delay on reset flow",
                "body": "Reset email delay blocks login and password recovery.",
            },
            {
                "ticket_id": "X-3",
                "queue": "orders",
                "agent": "Iris",
                "status": "solved",
                "subject": "Address correction request",
                "body": "Courier needs address update before parcel handoff.",
            },
            {
                "ticket_id": "X-4",
                "queue": "orders",
                "agent": "Nora",
                "status": "open",
                "subject": "Address update failed",
                "body": "Courier address update was not applied to the parcel.",
            },
            {
                "ticket_id": "X-5",
                "queue": "orders",
                "agent": "Mika",
                "status": "open",
                "subject": "Refund after parcel delay",
                "body": "Parcel delay requires refund review from courier support.",
            },
        ],
    )
    custom_stopwords.write_text("and\nafter\nbefore\nfrom\nnever\nneeds\nthe\nwas\n", encoding="utf-8")

    actual_custom = run_scala_report(build_dir, custom_tickets, custom_stopwords, custom_output)
    assert actual_custom == expected_report(module, custom_tickets, custom_stopwords)
