import os
import re
import subprocess


WORKSPACE = "/app/workspace"
JAVA_PATH = os.path.join(
    WORKSPACE, "src/main/java/cdcquality/query/CdcDisorderQualityReport.java"
)
OUTPUT_PATH = os.path.join(WORKSPACE, "cdc_quality_report.txt")
LINE_RE = re.compile(
    r"^date=(?P<date>\d{4}-\d{2}-\d{2}) "
    r"table=(?P<table>[a-z_]+) "
    r"duplicate_suppressed=(?P<duplicate>\d+) "
    r"out_of_order_updates=(?P<out_of_order>\d+) "
    r"final_retained_records=(?P<retained>\d+)$"
)


def test_maven_build():
    if os.path.isfile(JAVA_PATH):
        with open(JAVA_PATH, "r", encoding="utf-8") as handle:
            print(
                "\n=== Content of CdcDisorderQualityReport.java ===\n"
                f"{handle.read()}\n=== End of CdcDisorderQualityReport.java ===\n"
            )

    result = subprocess.run(
        "cd /app/workspace && mvn clean package -q",
        shell=True,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Maven build failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_flink_job_runs():
    result = subprocess.run(
        "cd /opt/flink/bin && ./flink run -t local "
        "-c cdcquality.query.CdcDisorderQualityReport "
        "/app/workspace/target/CdcDisorderQualityReport-jar-with-dependencies.jar "
        "--cdc_input /app/workspace/data/disorder_cdc_events.csv.gz "
        "--output /app/workspace/cdc_quality_report.txt",
        shell=True,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Flink job failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_output_matches_expected():
    assert os.path.isfile(OUTPUT_PATH), f"Output file {OUTPUT_PATH} does not exist"

    with open(OUTPUT_PATH, "r", encoding="utf-8") as handle:
        lines = [line.strip() for line in handle if line.strip()]

    parsed = {}
    for line in lines:
        match = LINE_RE.match(line)
        assert match, f"Unexpected output line: {line}"
        key = (match.group("date"), match.group("table"))
        assert key not in parsed, f"Duplicate output row for {key}"
        parsed[key] = {
            "duplicate_suppressed": int(match.group("duplicate")),
            "out_of_order_updates": int(match.group("out_of_order")),
            "final_retained_records": int(match.group("retained")),
        }

    print(f"Parsed CDC report: {parsed}")

    expected = {
        ("2024-05-01", "disorder_case"): {
            "duplicate_suppressed": 1,
            "out_of_order_updates": 0,
            "final_retained_records": 1,
        },
        ("2024-05-01", "lab_result"): {
            "duplicate_suppressed": 1,
            "out_of_order_updates": 0,
            "final_retained_records": 2,
        },
        ("2024-05-01", "medication_order"): {
            "duplicate_suppressed": 0,
            "out_of_order_updates": 1,
            "final_retained_records": 0,
        },
        ("2024-05-02", "disorder_case"): {
            "duplicate_suppressed": 1,
            "out_of_order_updates": 1,
            "final_retained_records": 2,
        },
        ("2024-05-02", "lab_result"): {
            "duplicate_suppressed": 1,
            "out_of_order_updates": 2,
            "final_retained_records": 2,
        },
        ("2024-05-02", "medication_order"): {
            "duplicate_suppressed": 2,
            "out_of_order_updates": 0,
            "final_retained_records": 2,
        },
    }

    assert parsed == expected
