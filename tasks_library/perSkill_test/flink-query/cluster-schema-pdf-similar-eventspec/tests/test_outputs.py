import json
from pathlib import Path


OUTPUT_PATH = Path("/app/artifacts/cluster_event_schema.json")


EXPECTED_JOB_FIELDS = [
    "timestamp",
    "missing_info",
    "job_id",
    "event_type",
    "user_name",
    "scheduling_class",
    "job_name",
    "logical_job_name",
]

EXPECTED_TASK_FIELDS = [
    "timestamp",
    "missing_info",
    "job_id",
    "task_index",
    "machine_id",
    "event_type",
    "user_name",
    "scheduling_class",
    "priority",
    "cpu_request",
    "ram_request",
    "local_disk_space_request",
    "different_machine_constraint",
]

EXPECTED_EVENT_CODES = [
    (0, "SUBMIT"),
    (1, "SCHEDULE"),
    (2, "EVICT"),
    (3, "FAIL"),
    (4, "FINISH"),
    (5, "KILL"),
    (6, "LOST"),
    (7, "UPDATE_PENDING"),
    (8, "UPDATE_RUNNING"),
]


def load_output():
    assert OUTPUT_PATH.is_file(), f"Missing output file: {OUTPUT_PATH}"
    with OUTPUT_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def test_top_level_shape():
    data = load_output()
    assert set(data.keys()) == {
        "source_document",
        "document_title",
        "time_semantics",
        "event_type_codes",
        "job_events",
        "task_events",
    }
    assert data["source_document"] == "input/cluster_schema.pdf"
    assert data["document_title"] == "Google cluster-usage traces: format + schema"


def test_time_semantics():
    data = load_output()
    time_semantics = data["time_semantics"]
    assert time_semantics["unit"] == "microseconds"
    assert "600 seconds before the beginning of the trace period" in time_semantics["base_reference"]
    assert "nearest second" in time_semantics["usage_measurement_precision"]
    assert "reported in microseconds" in time_semantics["usage_measurement_reporting"]

    special_values = time_semantics["special_values"]
    assert special_values == [
        {
            "value": "0",
            "meaning": "Represents events that occurred before the trace window.",
        },
        {
            "value": "2^63-1",
            "meaning": "Represents events that occur after the end of the trace window.",
        },
    ]


def test_event_codes():
    data = load_output()
    event_codes = data["event_type_codes"]
    assert [(item["code"], item["name"]) for item in event_codes] == EXPECTED_EVENT_CODES
    meanings = {item["name"]: item["meaning"] for item in event_codes}
    assert "eligible for scheduling" in meanings["SUBMIT"]
    assert "first time any task of the job is scheduled" in meanings["SCHEDULE"]
    assert "higher priority work" in meanings["EVICT"]
    assert "task failure" in meanings["FAIL"]
    assert "completed normally" in meanings["FINISH"]
    assert "cancelled by a user" in meanings["KILL"]
    assert "termination record was missing" in meanings["LOST"]
    assert "waiting to be scheduled" in meanings["UPDATE_PENDING"]
    assert "already scheduled" in meanings["UPDATE_RUNNING"]


def test_job_fields():
    data = load_output()
    job_events = data["job_events"]
    assert job_events["field_count"] == 8
    fields = job_events["fields"]
    assert len(fields) == 8
    assert [field["position"] for field in fields] == list(range(1, 9))
    assert [field["name"] for field in fields] == EXPECTED_JOB_FIELDS

    meanings = {field["name"]: field["meaning"] for field in fields}
    assert "microseconds" in meanings["timestamp"]
    assert "synthesized records" in meanings["missing_info"]
    assert "64-bit identifier" in meanings["job_id"]
    assert "transition code" in meanings["event_type"]
    assert "base64-encoded hash" in meanings["user_name"]
    assert "3 is more latency-sensitive" in meanings["scheduling_class"]
    assert "hashed job name" in meanings["job_name"]
    assert "same program" in meanings["logical_job_name"]


def test_task_fields():
    data = load_output()
    task_events = data["task_events"]
    assert task_events["field_count"] == 13
    fields = task_events["fields"]
    assert len(fields) == 13
    assert [field["position"] for field in fields] == list(range(1, 14))
    assert [field["name"] for field in fields] == EXPECTED_TASK_FIELDS

    meanings = {field["name"]: field["meaning"] for field in fields}
    assert "parent job" in meanings["job_id"]
    assert "0-based task index" in meanings["task_index"]
    assert "scheduled when a machine is present" in meanings["machine_id"]
    assert "transition code" in meanings["event_type"]
    assert "base64-encoded hash" in meanings["user_name"]
    assert "3 is more latency-sensitive" in meanings["scheduling_class"]
    assert "larger numbers are generally more important" in meanings["priority"]
    assert "CPU cores" in meanings["cpu_request"]
    assert "RAM" in meanings["ram_request"]
    assert "local disk space" in meanings["local_disk_space_request"]
    assert "different machine" in meanings["different_machine_constraint"]
