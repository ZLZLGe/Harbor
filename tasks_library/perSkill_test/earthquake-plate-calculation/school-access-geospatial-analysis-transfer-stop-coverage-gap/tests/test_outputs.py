import csv
import json
import math
import os
import unittest


BUFFER_RADIUS_M = 400.0
MINIMUM_STOP_TARGET = 3
METRIC_CRS = "EPSG:32618"


def resolve_path(*candidates: str) -> str:
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    raise FileNotFoundError(f"None of the candidate paths exist: {candidates}")


def load_csv_rows(path: str):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def compute_expected_audit():
    schools_path = resolve_path("/root/school_locations.csv", "school_locations.csv")
    stops_path = resolve_path("/root/bus_stops.csv", "bus_stops.csv")
    schools = load_csv_rows(schools_path)
    stops = load_csv_rows(stops_path)

    audit = []
    for school in schools:
        sx = float(school["easting_m"])
        sy = float(school["northing_m"])
        count = 0
        for stop in stops:
            tx = float(stop["easting_m"])
            ty = float(stop["northing_m"])
            if math.hypot(tx - sx, ty - sy) <= BUFFER_RADIUS_M:
                count += 1

        audit.append(
            {
                "school_id": school["school_id"],
                "school_name": school["school_name"],
                "reachable_stop_count": count,
                "coverage_gap": max(0, MINIMUM_STOP_TARGET - count),
            }
        )

    audit.sort(
        key=lambda row: (
            -row["coverage_gap"],
            row["reachable_stop_count"],
            row["school_id"],
        )
    )
    return audit


class TestSchoolStopCoverage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        output_path = resolve_path(
            "/root/school_stop_coverage.json",
            "school_stop_coverage.json",
        )
        with open(output_path, encoding="utf-8") as f:
            cls.result = json.load(f)

        cls.expected_audit = compute_expected_audit()
        cls.expected_worst_school = cls.expected_audit[0]

    def test_top_level_fields(self):
        required_fields = [
            "metric_crs",
            "buffer_radius_m",
            "minimum_stop_target",
            "worst_school",
            "school_audit",
        ]
        for field in required_fields:
            self.assertIn(field, self.result, f"Missing required field: {field}")

    def test_fixed_parameters(self):
        self.assertEqual(self.result["metric_crs"], METRIC_CRS)
        self.assertEqual(self.result["buffer_radius_m"], 400)
        self.assertEqual(self.result["minimum_stop_target"], MINIMUM_STOP_TARGET)

    def test_worst_school_matches_reference(self):
        self.assertEqual(self.result["worst_school"], self.expected_worst_school)

    def test_school_audit_matches_reference(self):
        self.assertEqual(self.result["school_audit"], self.expected_audit)

    def test_expected_worst_school_identity(self):
        self.assertEqual(self.expected_worst_school["school_id"], "SCH-104")
        self.assertEqual(self.expected_worst_school["school_name"], "Riverside Preparatory")
        self.assertEqual(self.expected_worst_school["reachable_stop_count"], 0)
        self.assertEqual(self.expected_worst_school["coverage_gap"], 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
