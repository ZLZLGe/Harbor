import csv
import math
import os
from collections import defaultdict
from pathlib import Path

INPUT_FILE = Path(os.environ.get("TASK_INPUT_FILE", "/root/data/bench_nationals_results.csv"))
OUTPUT_FILE = Path(os.environ.get("TASK_OUTPUT_FILE", "/root/data/bench_goodlift_ranking.csv"))

EXPECTED_HEADERS = [
    "OverallRank",
    "ClassRank",
    "ScoringClass",
    "LifterName",
    "Province",
    "Sex",
    "Equipment",
    "Event",
    "BodyweightKg",
    "Best3BenchKg",
    "Goodlift",
]

PARAMETERS = {
    ("B", "M", "Raw"): (320.98041, 281.40258, 0.01008),
    ("B", "M", "Single-ply"): (381.22073, 733.79378, 0.02398),
    ("B", "F", "Raw"): (142.40398, 442.52671, 0.04724),
    ("B", "F", "Single-ply"): (221.82209, 357.00377, 0.02937),
}


def calculate_goodlift(sex: str, equipment: str, event: str, bodyweight: float, total: float) -> float:
    if bodyweight < 35.0 or total == 0.0:
        return 0.0

    sex_key = "F" if sex == "F" else "M"
    a, b, c = PARAMETERS[(event, sex_key, equipment)]
    denominator = a - b * math.exp(-c * bodyweight)
    return round(total * max(0.0, 100.0 / denominator), 2)


def load_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def sort_key(row):
    return (-row["GoodliftValue"], -float(row["Best3BenchKg"]), row["LifterName"])


def build_expected_rows():
    rows = load_csv(INPUT_FILE)

    for row in rows:
        row["GoodliftValue"] = calculate_goodlift(
            row["Sex"],
            row["Equipment"],
            row["Event"],
            float(row["BodyweightKg"]),
            float(row["Best3BenchKg"]),
        )
        row["ScoringClass"] = f'{row["Sex"]}|{row["Equipment"]}|{row["Event"]}'

    class_groups = defaultdict(list)
    for row in rows:
        class_groups[row["ScoringClass"]].append(row)

    for items in class_groups.values():
        items.sort(key=sort_key)
        for rank, row in enumerate(items, start=1):
            row["ClassRank"] = str(rank)

    rows.sort(key=sort_key)

    expected = []
    for overall_rank, row in enumerate(rows, start=1):
        expected.append(
            {
                "OverallRank": str(overall_rank),
                "ClassRank": row["ClassRank"],
                "ScoringClass": row["ScoringClass"],
                "LifterName": row["LifterName"],
                "Province": row["Province"],
                "Sex": row["Sex"],
                "Equipment": row["Equipment"],
                "Event": row["Event"],
                "BodyweightKg": row["BodyweightKg"],
                "Best3BenchKg": row["Best3BenchKg"],
                "Goodlift": f'{row["GoodliftValue"]:.2f}',
            }
        )

    return expected


def test_output_exists():
    assert OUTPUT_FILE.exists(), f"缺少输出文件: {OUTPUT_FILE}"


def test_headers_and_row_count():
    output_rows = load_csv(OUTPUT_FILE)
    assert output_rows, "输出 CSV 不能为空"
    assert list(output_rows[0].keys()) == EXPECTED_HEADERS
    assert len(output_rows) == len(load_csv(INPUT_FILE))


def test_output_matches_expected_ranking():
    output_rows = load_csv(OUTPUT_FILE)
    assert output_rows == build_expected_rows()


def test_low_bodyweight_rows_score_zero():
    output_rows = {row["LifterName"]: row for row in load_csv(OUTPUT_FILE)}
    assert output_rows["Wu Min"]["Goodlift"] == "0.00"
    assert output_rows["Gao Lei"]["Goodlift"] == "0.00"


def test_class_rank_restarts_within_each_scoring_class():
    output_rows = load_csv(OUTPUT_FILE)
    seen = defaultdict(list)
    for row in output_rows:
        seen[row["ScoringClass"]].append(int(row["ClassRank"]))

    for ranks in seen.values():
        assert ranks == list(range(1, len(ranks) + 1))


def test_published_style_reference_value_is_correct():
    output_rows = {row["LifterName"]: row for row in load_csv(OUTPUT_FILE)}
    assert output_rows["He Jing"]["Goodlift"] == "96.78"


if __name__ == "__main__":
    for name, value in sorted(globals().items()):
        if name.startswith("test_") and callable(value):
            value()
    print("all tests passed")
