import os
import re
import subprocess


WORKSPACE = "/app/workspace"
JAVA_PATH = os.path.join(
    WORKSPACE, "src/main/java/pipelinesla/query/PipelineCloseoutSlaRollup.java"
)
OUTPUT_PATH = os.path.join(WORKSPACE, "pipeline_sla_rollup.txt")
LINE_RE = re.compile(
    r"^pipeline=(?P<pipeline>[a-z-]+) "
    r"longest_backlog_micros=(?P<duration>\d+) "
    r"backlog_task_count=(?P<backlog>\d+) "
    r"failed_task_count=(?P<failed>\d+)$"
)


def test_maven_build():
    if os.path.isfile(JAVA_PATH):
        with open(JAVA_PATH, "r", encoding="utf-8") as handle:
            print(
                "\n=== Content of PipelineCloseoutSlaRollup.java ===\n"
                f"{handle.read()}\n=== End of PipelineCloseoutSlaRollup.java ===\n"
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
        "-c pipelinesla.query.PipelineCloseoutSlaRollup "
        "/app/workspace/target/PipelineCloseoutSlaRollup-jar-with-dependencies.jar "
        "--task_input /app/workspace/data/pipeline_task_lifecycle.csv.gz "
        "--close_input /app/workspace/data/pipeline_close_events.csv.gz "
        "--output /app/workspace/pipeline_sla_rollup.txt",
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
        pipeline_id = match.group("pipeline")
        assert pipeline_id not in parsed, f"Duplicate output for pipeline {pipeline_id}"
        parsed[pipeline_id] = {
            "longest_backlog_micros": int(match.group("duration")),
            "backlog_task_count": int(match.group("backlog")),
            "failed_task_count": int(match.group("failed")),
        }

    print(f"Parsed pipeline SLA rollup: {parsed}")

    assert parsed == {
        "batch-alpha": {
            "longest_backlog_micros": 31000000,
            "backlog_task_count": 3,
            "failed_task_count": 1,
        },
        "etl-epsilon": {
            "longest_backlog_micros": 0,
            "backlog_task_count": 0,
            "failed_task_count": 1,
        },
        "ml-gamma": {
            "longest_backlog_micros": 30000000,
            "backlog_task_count": 3,
            "failed_task_count": 1,
        },
        "stream-beta": {
            "longest_backlog_micros": 12000000,
            "backlog_task_count": 2,
            "failed_task_count": 2,
        },
    }

    assert "ops-delta" not in parsed, "Pipelines without a close event must not produce output"
