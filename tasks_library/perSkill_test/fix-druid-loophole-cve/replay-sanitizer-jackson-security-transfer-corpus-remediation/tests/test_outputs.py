import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


WORKSPACE = Path(os.getenv("WORKSPACE", "/workspace"))
REPO_DIR = WORKSPACE / "replay-sanitizer"
INPUT_ROOT = WORKSPACE / "historical-corpus"
OUTPUT_FILE = WORKSPACE / "output" / "replay-remediation-manifest.json"
PRISTINE_REPO = Path("/opt/task-assets/replay-sanitizer-pristine")
JAR_PATH = REPO_DIR / "target" / "replay-sanitizer-1.0-SNAPSHOT.jar"


def build_project():
  subprocess.run(
      ["mvn", "-q", "-DskipTests", "package"],
      cwd=REPO_DIR,
      check=True,
      stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT,
      text=True,
      timeout=180,
  )
  assert JAR_PATH.exists(), "built jar not found"


def run_sanitizer(input_root: Path, output_path: Path):
  subprocess.run(
      ["java", "-jar", str(JAR_PATH), str(input_root), str(output_path)],
      cwd=REPO_DIR,
      check=True,
      stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT,
      text=True,
      timeout=60,
  )


def load_manifest(path: Path):
  with path.open() as handle:
    return json.load(handle)


def assert_manifest_shape(manifest: dict):
  required_top_level = {
      "batchId",
      "scannedSampleCount",
      "safeReplayCount",
      "quarantinedCount",
      "safeReplays",
      "quarantinedSamples",
  }
  assert required_top_level.issubset(manifest.keys()), f"missing manifest fields: {required_top_level - set(manifest.keys())}"

  for entry in manifest["safeReplays"]:
    assert {"sampleId", "capturedAt", "method", "path", "dataset", "filterType", "normalizedBody"}.issubset(entry.keys())

  for entry in manifest["quarantinedSamples"]:
    assert {"sampleId", "sourceFile", "reasons"}.issubset(entry.keys())


def test_output_file_exists_and_matches_contract():
  assert OUTPUT_FILE.exists(), "required manifest file was not created"
  manifest = load_manifest(OUTPUT_FILE)
  assert_manifest_shape(manifest)

  assert manifest["batchId"] == "historical-replay-batch-2024-11"
  assert manifest["scannedSampleCount"] == 6
  assert manifest["safeReplayCount"] == 3
  assert manifest["quarantinedCount"] == 3

  safe_ids = [entry["sampleId"] for entry in manifest["safeReplays"]]
  assert safe_ids == ["hist-101", "hist-102", "hist-103"]

  safe_by_id = {entry["sampleId"]: entry for entry in manifest["safeReplays"]}
  assert safe_by_id["hist-101"]["method"] == "POST"
  assert safe_by_id["hist-101"]["filterType"] == "selector"
  assert safe_by_id["hist-101"]["normalizedBody"]["filter"]["dimension"] == "region"
  assert safe_by_id["hist-102"]["normalizedBody"]["note"] == "month-end replay"
  assert safe_by_id["hist-103"]["method"] == "GET"

  quarantined_ids = [entry["sampleId"] for entry in manifest["quarantinedSamples"]]
  assert quarantined_ids == ["hist-201", "hist-202", "hist-203"]

  quarantined_by_id = {entry["sampleId"]: entry for entry in manifest["quarantinedSamples"]}
  assert quarantined_by_id["hist-201"]["reasons"] == ["empty-key"]
  assert quarantined_by_id["hist-202"]["reasons"] == ["type-directive"]
  assert quarantined_by_id["hist-203"]["reasons"] == ["script-like-type"]


def test_project_was_modified_from_pristine_source():
  pristine = (PRISTINE_REPO / "src/main/java/com/harbor/replay/ReplaySanitizerService.java").read_text()
  current = (REPO_DIR / "src/main/java/com/harbor/replay/ReplaySanitizerService.java").read_text()
  assert pristine != current, "source changes were not applied to the sanitizer"


def test_sanitizer_rejects_additional_structural_risks():
  build_project()

  with tempfile.TemporaryDirectory() as tmpdir:
    temp_root = Path(tmpdir) / "corpus"
    shutil.copytree(INPUT_ROOT, temp_root)
    requests_dir = temp_root / "requests"

    (requests_dir / "hist-extra-101.json").write_text(
        json.dumps({
            "sampleId": "hist-extra-101",
            "capturedAt": "2024-12-01T00:00:00Z",
            "request": {
                "method": "post",
                "path": "/v1/reports/query",
                "body": {
                    "dataset": "daily_summary",
                    "filter": {
                        "type": "selector",
                        "dimension": "region",
                        "value": "na"
                    },
                    "limit": 10
                }
            }
        }),
        encoding="utf-8",
    )

    (requests_dir / "hist-extra-201.json").write_text(
        json.dumps({
            "sampleId": "hist-extra-201",
            "capturedAt": "2024-12-01T00:05:00Z",
            "request": {
                "method": "post",
                "path": "/v1/reports/query",
                "body": {
                    "dataset": "daily_summary",
                    "payload": {
                        "@type": "com.example.BadThing"
                    }
                }
            }
        }),
        encoding="utf-8",
    )

    (requests_dir / "hist-extra-202.json").write_text(
        json.dumps({
            "sampleId": "hist-extra-202",
            "capturedAt": "2024-12-01T00:10:00Z",
            "request": {
                "method": "post",
                "path": "/v1/templates/render",
                "body": {
                    "dataset": "template_jobs",
                    "steps": [
                        {
                            "template": {
                                "type": "groovy",
                                "script": "println('boom')"
                            }
                        }
                    ]
                }
            }
        }),
        encoding="utf-8",
    )

    (requests_dir / "hist-extra-203.json").write_text(
        '{"sampleId":"hist-extra-203","capturedAt":"2024-12-01T00:15:00Z","request":{"method":"post","path":"/broken","body":{"dataset":"x",}}}',
        encoding="utf-8",
    )

    temp_output = Path(tmpdir) / "manifest.json"
    run_sanitizer(temp_root, temp_output)

    manifest = load_manifest(temp_output)
    assert_manifest_shape(manifest)
    assert manifest["scannedSampleCount"] == 10
    assert manifest["safeReplayCount"] == 4
    assert manifest["quarantinedCount"] == 6

    quarantined_by_id = {entry["sampleId"]: entry["reasons"] for entry in manifest["quarantinedSamples"]}
    assert quarantined_by_id["hist-extra-201"] == ["type-directive"]
    assert quarantined_by_id["hist-extra-202"] == ["script-like-type"]
    assert quarantined_by_id["hist-extra-203"] == ["invalid-json"]

    safe_ids = [entry["sampleId"] for entry in manifest["safeReplays"]]
    assert "hist-extra-101" in safe_ids


def test_manifest_lists_are_sorted():
  manifest = load_manifest(OUTPUT_FILE)
  assert_manifest_shape(manifest)

  safe_ids = [entry["sampleId"] for entry in manifest["safeReplays"]]
  quarantined_ids = [entry["sampleId"] for entry in manifest["quarantinedSamples"]]
  assert safe_ids == sorted(safe_ids)
  assert quarantined_ids == sorted(quarantined_ids)
