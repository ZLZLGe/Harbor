import json
import os
import re
from pathlib import Path


APP_ROOT = Path(os.environ.get("APP_ROOT", "/app"))
REPORT = APP_ROOT / "triage" / "flake_report.json"
NOTES = APP_ROOT / "triage" / "reproduction_notes.md"
DIFF = APP_ROOT / "triage" / "recommended_fix.diff"
TRACE = APP_ROOT / ".trace" / "commands.jsonl"


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_trace():
    assert TRACE.exists(), "missing command trace; reproduction workflow was not run"
    return [json.loads(line) for line in TRACE.read_text(encoding="utf-8").splitlines() if line.strip()]


def find_event(events, kind, **filters):
    for i, event in enumerate(events):
        if event.get("kind") != kind:
            continue
        if all(event.get(k) == v for k, v in filters.items()):
            return i, event
    raise AssertionError(f"missing trace event kind={kind} filters={filters}")


def find_optional_event(events, kind, **filters):
    try:
        return find_event(events, kind, **filters)
    except AssertionError:
        return None, None


def test_report_outputs():
    assert REPORT.exists(), "missing /app/triage/flake_report.json"
    assert NOTES.exists(), "missing /app/triage/reproduction_notes.md"
    assert DIFF.exists(), "missing /app/triage/recommended_fix.diff"
    report = load_json(REPORT)
    assert report["suite"] == "checkout"
    assert report["test_file"] == "test/checkout/e2e.spec.ts"
    assert report["test_title"] == "checkout applies saved shipping method after address edit"
    assert "Timed out 5000ms" in report["ci_error"]
    assert report["dev_reproduction"] == "pass"
    assert report["prod_reproduction"] == "fail"
    assert report["classification"] == "prod_bundle_regression"
    assert report["root_cause"].strip()
    assert report["recommended_fix"].strip()
    assert isinstance(report["commands_run"], list)
    assert any("pnpm dev checkout" in cmd for cmd in report["commands_run"])
    assert any("pnpm dev:prod checkout" in cmd for cmd in report["commands_run"])


def test_reproduction_trace_sequence():
    events = load_trace()
    assert not any(event["kind"] == "playwright-full-suite" for event in events), "solver ran full suite instead of exact failing test"

    first_lsof, _ = find_event(events, "lsof")
    dev_i, dev = find_event(events, "dev-server", suite="checkout", mode="dev")
    dev_test_i, dev_test = find_event(events, "playwright-target", mode="dev", suite="checkout")
    prepare_i, _ = find_event(events, "prepare-prod")
    prod_lsof_i = next((i for i, e in enumerate(events) if e["kind"] == "lsof" and dev_test_i < i), None)
    assert prod_lsof_i is not None, "port 3000 was not cleared after dev reproduction and before prod server"
    prod_i, prod = find_event(events, "prod-server", suite="checkout", mode="prod")
    prod_test_i, prod_test = find_event(events, "playwright-target", mode="prod", suite="checkout")

    assert first_lsof < dev_i, "port 3000 must be cleared before dev server"
    dev_curl_i, _ = find_optional_event(events[dev_i + 1 : dev_test_i], "curl")
    if dev_curl_i is not None:
        assert dev_i < dev_i + 1 + dev_curl_i < dev_test_i, "dev readiness probe must happen before dev test"
    assert dev_i < dev_test_i, "dev server must start before dev targeted test"
    assert dev_test["return_code"] == 0, "dev targeted reproduction should pass"
    assert dev_test_i < prod_lsof_i < prod_i, "prod server must start only after clearing the dev server"
    assert dev_test_i < prepare_i < prod_i, "prod preparation must happen before prod server starts"
    prod_curl_i, _ = find_optional_event(events[prod_i + 1 : prod_test_i], "curl")
    if prod_curl_i is not None:
        assert prod_i < prod_i + 1 + prod_curl_i < prod_test_i, "prod readiness probe must happen before prod test"
    assert prod_i < prod_test_i, "prod server must start before prod targeted test"
    assert prod_test["return_code"] != 0, "prod targeted reproduction should fail"


def test_notes_and_diff_are_behavioral_not_disable():
    notes = NOTES.read_text(encoding="utf-8").lower()
    for phrase in ["ci details", "dev", "production", "classification", "recommended"]:
        assert phrase in notes, f"notes missing {phrase}"
    diff = DIFF.read_text(encoding="utf-8")
    assert diff.startswith("--- ") or "\n--- " in diff, "recommended_fix.diff must be unified diff"
    assert "test/checkout/e2e.spec.ts" in diff
    lowered = diff.lower()
    banned = ["test.skip", ".skip(", "fixme", "timeout: 30000", "timeout: 60000"]
    assert not any(token in lowered for token in banned), "diff disables or papers over the flaky test"
    assert any(token in diff for token in ["toBeVisible", "waitForFunction", "toHaveText"]), "diff must keep a real condition-based assertion"


def test_inputs_not_modified():
    failed = load_json(APP_ROOT / "ci-logs" / "failed-run.json")
    assert failed["run_id"] == 74291
    test_file = (APP_ROOT / "repo" / "test" / "checkout" / "e2e.spec.ts").read_text(encoding="utf-8")
    assert "checkout applies saved shipping method after address edit" in test_file


def run_all():
    tests = [
        test_report_outputs,
        test_reproduction_trace_sequence,
        test_notes_and_diff_are_behavioral_not_disable,
        test_inputs_not_modified,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")


if __name__ == "__main__":
    run_all()
