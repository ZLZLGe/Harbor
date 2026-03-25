import csv
from pathlib import Path


OUTPUT_FILE = Path("/app/workspace/scoreboard_rankings.csv")
EXPECTED_ROWS = [
    {
        "rank": "1",
        "team": "COBRAS",
        "wins": "2",
        "losses": "1",
        "points_for": "262",
        "points_against": "257",
        "net_point_diff": "5",
    },
    {
        "rank": "2",
        "team": "FALCONS",
        "wins": "2",
        "losses": "1",
        "points_for": "247",
        "points_against": "242",
        "net_point_diff": "5",
    },
    {
        "rank": "3",
        "team": "LYNX",
        "wins": "1",
        "losses": "2",
        "points_for": "242",
        "points_against": "247",
        "net_point_diff": "-5",
    },
    {
        "rank": "4",
        "team": "ORBITS",
        "wins": "1",
        "losses": "2",
        "points_for": "249",
        "points_against": "254",
        "net_point_diff": "-5",
    },
]


def read_rows() -> list[dict[str, str]]:
    with OUTPUT_FILE.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        assert reader.fieldnames == [
            "rank",
            "team",
            "wins",
            "losses",
            "points_for",
            "points_against",
            "net_point_diff",
        ], f"unexpected header: {reader.fieldnames}"
        return rows


def test_output_file_exists():
    assert OUTPUT_FILE.exists(), f"missing output file: {OUTPUT_FILE}"


def test_csv_matches_expected_rankings():
    rows = read_rows()
    assert rows == EXPECTED_ROWS


def test_ranking_rules_and_point_math():
    rows = read_rows()
    assert [row["rank"] for row in rows] == ["1", "2", "3", "4"]

    parsed = []
    for row in rows:
        wins = int(row["wins"])
        losses = int(row["losses"])
        points_for = int(row["points_for"])
        points_against = int(row["points_against"])
        net_point_diff = int(row["net_point_diff"])

        assert wins + losses == 3, f"each team should have 3 matches: {row}"
        assert net_point_diff == points_for - points_against, f"net diff mismatch: {row}"

        parsed.append(
            {
                "team": row["team"],
                "wins": wins,
                "net_point_diff": net_point_diff,
            }
        )

    sorted_rows = sorted(parsed, key=lambda item: (-item["wins"], -item["net_point_diff"], item["team"]))
    assert [row["team"] for row in parsed] == [row["team"] for row in sorted_rows]
