import os
import re
import subprocess


WORKSPACE = "/app/workspace"
JAVA_PATH = os.path.join(
    WORKSPACE, "src/main/java/campaignaudit/query/CampaignAttributionLagAudit.java"
)
OUTPUT_PATH = os.path.join(WORKSPACE, "campaign_attribution_sla.txt")
LINE_RE = re.compile(
    r"^campaign=(?P<campaign>[A-Za-z0-9_-]+) "
    r"unattributed=(?P<unattributed>\d+) "
    r"p95_valid_click_lag_micros=(?P<p95>-?\d+)$"
)


def test_maven_build():
    if os.path.isfile(JAVA_PATH):
        with open(JAVA_PATH, "r", encoding="utf-8") as handle:
            print(
                "\n=== Content of CampaignAttributionLagAudit.java ===\n"
                f"{handle.read()}\n=== End of CampaignAttributionLagAudit.java ===\n"
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
        "-c campaignaudit.query.CampaignAttributionLagAudit "
        "/app/workspace/target/CampaignAttributionLagAudit-jar-with-dependencies.jar "
        "--impression_input /app/workspace/data/campaign_impressions.csv.gz "
        "--click_input /app/workspace/data/campaign_clicks.csv.gz "
        "--output /app/workspace/campaign_attribution_sla.txt",
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
        campaign = match.group("campaign")
        assert campaign not in parsed, f"Duplicate output for campaign {campaign}"
        parsed[campaign] = {
            "unattributed": int(match.group("unattributed")),
            "p95": int(match.group("p95")),
        }

    print(f"Parsed SLA report: {parsed}")

    assert parsed == {
        "aurora": {"unattributed": 1, "p95": 9000000},
        "blaze": {"unattributed": 0, "p95": 12000000},
        "comet": {"unattributed": 2, "p95": -1},
        "drift": {"unattributed": 0, "p95": 10000000},
    }

    assert "orphan" not in parsed, "Clicks without impressions must not create campaign output"
