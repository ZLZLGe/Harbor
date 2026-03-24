import json
from pathlib import Path

INPUT_FILE = Path("/root/data/extreme_bodyweight_audit_input.json")
OUTPUT_FILE = Path("/root/data/bodyweight_clamp_audit.json")

MALE_COEFFICIENTS = (-0.0000010930, 0.0007391293, -0.1918759221, 24.0900756, -307.75076)
FEMALE_COEFFICIENTS = (-0.0000010706, 0.0005158568, -0.1126655495, 13.6175032, -57.96288)

TOP_LEVEL_KEYS = ["meet_id", "audit_batch", "summary", "entries"]
SUMMARY_KEYS = [
    "athlete_count",
    "adjusted_count",
    "floor_adjustment_count",
    "cap_adjustment_count",
    "unchanged_count",
]
ENTRY_KEYS = [
    "athlete_id",
    "lifter_name",
    "sex",
    "original_bodyweight_kg",
    "applied_bodyweight_kg",
    "adjustment",
    "total_kg",
    "dots",
]


def clamp_bodyweight(sex: str, bodyweight: float) -> float:
    if sex == "M":
        return max(40.0, min(210.0, bodyweight))
    return max(40.0, min(150.0, bodyweight))


def calculate_dots(sex: str, bodyweight: float, total: float) -> float:
    adjusted = clamp_bodyweight(sex, bodyweight)
    if sex == "M":
        a, b, c, d, e = MALE_COEFFICIENTS
    else:
        a, b, c, d, e = FEMALE_COEFFICIENTS

    denominator = a * adjusted**4 + b * adjusted**3 + c * adjusted**2 + d * adjusted + e
    return round(total * (500.0 / denominator), 3)


def expected_report():
    payload = json.loads(INPUT_FILE.read_text(encoding="utf-8"))
    entries = []
    summary = {
        "athlete_count": 0,
        "adjusted_count": 0,
        "floor_adjustment_count": 0,
        "cap_adjustment_count": 0,
        "unchanged_count": 0,
    }

    for athlete in payload["athletes"]:
        sex = athlete["profile"]["sex"]
        original_bodyweight = float(athlete["weigh_in"]["bodyweight_kg"])
        lifts = athlete["best_lifts_kg"]
        total = round(float(lifts["squat"]) + float(lifts["bench"]) + float(lifts["deadlift"]), 3)
        applied_bodyweight = clamp_bodyweight(sex, original_bodyweight)

        if applied_bodyweight > original_bodyweight:
            adjustment = "floor_to_min"
        elif applied_bodyweight < original_bodyweight:
            adjustment = "cap_to_max"
        else:
            adjustment = "none"

        summary["athlete_count"] += 1
        if adjustment == "none":
            summary["unchanged_count"] += 1
        else:
            summary["adjusted_count"] += 1
            if adjustment == "floor_to_min":
                summary["floor_adjustment_count"] += 1
            else:
                summary["cap_adjustment_count"] += 1

        entries.append(
            {
                "athlete_id": athlete["athlete_id"],
                "lifter_name": athlete["profile"]["lifter_name"],
                "sex": sex,
                "original_bodyweight_kg": original_bodyweight,
                "applied_bodyweight_kg": applied_bodyweight,
                "adjustment": adjustment,
                "total_kg": total,
                "dots": calculate_dots(sex, original_bodyweight, total),
            }
        )

    return {
        "meet_id": payload["meet_id"],
        "audit_batch": payload["audit_batch"],
        "summary": summary,
        "entries": entries,
    }


def assert_float(actual, expected, label):
    assert isinstance(actual, (int, float)), f"{label} 应为数字，实际是 {type(actual)}"
    assert round(float(actual), 3) == round(float(expected), 3), f"{label} 不匹配: {actual} != {expected}"


def main():
    assert OUTPUT_FILE.exists(), f"缺少输出文件: {OUTPUT_FILE}"

    actual = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
    expected = expected_report()

    assert list(actual.keys()) == TOP_LEVEL_KEYS, f"顶层字段错误: {list(actual.keys())}"
    assert actual["meet_id"] == expected["meet_id"]
    assert actual["audit_batch"] == expected["audit_batch"]

    assert list(actual["summary"].keys()) == SUMMARY_KEYS, f"summary 字段错误: {list(actual['summary'].keys())}"
    assert actual["summary"] == expected["summary"], f"summary 不匹配: {actual['summary']} != {expected['summary']}"

    assert isinstance(actual["entries"], list), "entries 必须是数组"
    assert len(actual["entries"]) == len(expected["entries"]), "entries 条数不匹配"

    for idx, (actual_entry, expected_entry) in enumerate(zip(actual["entries"], expected["entries"]), start=1):
        assert list(actual_entry.keys()) == ENTRY_KEYS, f"第 {idx} 条记录字段错误: {list(actual_entry.keys())}"

        for key in ["athlete_id", "lifter_name", "sex", "adjustment"]:
            assert actual_entry[key] == expected_entry[key], f"第 {idx} 条记录的 {key} 不匹配"

        for key in ["original_bodyweight_kg", "applied_bodyweight_kg", "total_kg", "dots"]:
            assert_float(actual_entry[key], expected_entry[key], f"第 {idx} 条记录的 {key}")

    rows = {row["athlete_id"]: row for row in actual["entries"]}
    assert rows["M-001"]["adjustment"] == "floor_to_min"
    assert_float(rows["M-001"]["applied_bodyweight_kg"], 40.0, "M-001 applied_bodyweight_kg")
    assert rows["M-003"]["adjustment"] == "cap_to_max"
    assert_float(rows["M-003"]["applied_bodyweight_kg"], 210.0, "M-003 applied_bodyweight_kg")
    assert rows["F-003"]["adjustment"] == "cap_to_max"
    assert_float(rows["F-003"]["applied_bodyweight_kg"], 150.0, "F-003 applied_bodyweight_kg")
    assert rows["F-004"]["adjustment"] == "none"
    assert_float(rows["F-004"]["applied_bodyweight_kg"], 150.0, "F-004 applied_bodyweight_kg")
    assert_float(rows["F-002"]["dots"], 523.324, "F-002 dots")

    print("all tests passed")


if __name__ == "__main__":
    main()
