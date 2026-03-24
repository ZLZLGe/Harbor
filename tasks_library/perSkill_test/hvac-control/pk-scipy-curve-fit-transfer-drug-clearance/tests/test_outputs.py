#!/usr/bin/env python3

import json
import math
import os


ROOT_DIR = "/root"
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_PATH = os.path.join(ROOT_DIR, "pk_decay_summary.json")
CASE_PATH = os.path.join(ROOT_DIR, "iv_bolus_case.json")
VERIFICATION_PATH = os.path.join(TESTS_DIR, "verification_params.json")


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def decay_model(time_hr, c0, elimination_rate):
    return c0 * math.exp(-elimination_rate * time_hr)


class TestReportStructure:
    def test_required_fields_present(self):
        report = load_json(REPORT_PATH)

        for field in [
            "case_id",
            "drug_name",
            "input_file",
            "dose_mg",
            "samples_used",
            "fit_model",
            "discharge_summary",
        ]:
            assert field in report, f"missing '{field}'"

        for field in [
            "initial_concentration_mg_per_l",
            "elimination_rate_per_hr",
            "half_life_hr",
            "auc_0_inf_mg_h_per_l",
            "rmse_mg_per_l",
        ]:
            assert field in report["fit_model"], f"missing fit_model field '{field}'"

        for field in [
            "volume_of_distribution_l",
            "clearance_l_per_hr",
            "discharge_time_hr",
            "subtherapeutic_floor_mg_per_l",
            "predicted_concentration_at_discharge_mg_per_l",
            "time_to_fall_below_floor_hr",
            "dose_due_before_discharge",
        ]:
            assert field in report["discharge_summary"], f"missing discharge_summary field '{field}'"

    def test_metadata_matches_input_case(self):
        report = load_json(REPORT_PATH)
        case = load_json(CASE_PATH)

        assert report["case_id"] == case["case_id"]
        assert report["drug_name"] == case["drug_name"]
        assert report["input_file"] == "iv_bolus_case.json"
        assert abs(report["dose_mg"] - case["dose_mg"]) <= 1e-9
        assert report["samples_used"] == len(case["samples"])
        assert abs(
            report["discharge_summary"]["volume_of_distribution_l"]
            - case["volume_of_distribution_l"]
        ) <= 1e-9
        assert abs(
            report["discharge_summary"]["discharge_time_hr"] - case["discharge_time_hr"]
        ) <= 1e-9
        assert abs(
            report["discharge_summary"]["subtherapeutic_floor_mg_per_l"]
            - case["subtherapeutic_floor_mg_per_l"]
        ) <= 1e-9


class TestFitAccuracy:
    def test_parameters_close_to_reference(self):
        report = load_json(REPORT_PATH)
        truth = load_json(VERIFICATION_PATH)

        c0 = report["fit_model"]["initial_concentration_mg_per_l"]
        elimination_rate = report["fit_model"]["elimination_rate_per_hr"]
        half_life = report["fit_model"]["half_life_hr"]
        clearance = report["discharge_summary"]["clearance_l_per_hr"]

        assert (
            abs(c0 - truth["initial_concentration_mg_per_l"])
            / truth["initial_concentration_mg_per_l"]
            <= 0.06
        )
        assert (
            abs(elimination_rate - truth["elimination_rate_per_hr"])
            / truth["elimination_rate_per_hr"]
            <= 0.08
        )
        assert abs(half_life - truth["half_life_hr"]) / truth["half_life_hr"] <= 0.08
        assert abs(clearance - truth["clearance_l_per_hr"]) / truth["clearance_l_per_hr"] <= 0.10

    def test_fit_quality_is_reasonable(self):
        report = load_json(REPORT_PATH)
        rmse = report["fit_model"]["rmse_mg_per_l"]

        assert rmse <= 0.25
        assert rmse > 0.0


class TestDerivedMetrics:
    def test_derived_values_are_consistent(self):
        report = load_json(REPORT_PATH)

        c0 = report["fit_model"]["initial_concentration_mg_per_l"]
        elimination_rate = report["fit_model"]["elimination_rate_per_hr"]
        half_life = report["fit_model"]["half_life_hr"]
        auc_0_inf = report["fit_model"]["auc_0_inf_mg_h_per_l"]

        volume = report["discharge_summary"]["volume_of_distribution_l"]
        clearance = report["discharge_summary"]["clearance_l_per_hr"]
        discharge_time = report["discharge_summary"]["discharge_time_hr"]
        floor = report["discharge_summary"]["subtherapeutic_floor_mg_per_l"]
        predicted_at_discharge = report["discharge_summary"][
            "predicted_concentration_at_discharge_mg_per_l"
        ]
        time_to_floor = report["discharge_summary"]["time_to_fall_below_floor_hr"]

        expected_half_life = math.log(2.0) / elimination_rate
        expected_auc = c0 / elimination_rate
        expected_clearance = elimination_rate * volume
        expected_discharge = decay_model(discharge_time, c0, elimination_rate)
        expected_time_to_floor = math.log(c0 / floor) / elimination_rate

        assert abs(half_life - expected_half_life) <= 0.02
        assert abs(auc_0_inf - expected_auc) <= 0.05
        assert abs(clearance - expected_clearance) <= 0.02
        assert abs(predicted_at_discharge - expected_discharge) <= 0.02
        assert abs(time_to_floor - expected_time_to_floor) <= 0.05

    def test_rmse_matches_input_samples(self):
        report = load_json(REPORT_PATH)
        case = load_json(CASE_PATH)

        c0 = report["fit_model"]["initial_concentration_mg_per_l"]
        elimination_rate = report["fit_model"]["elimination_rate_per_hr"]

        squared_errors = []
        for sample in case["samples"]:
            predicted = decay_model(sample["time_hr"], c0, elimination_rate)
            squared_errors.append(
                (sample["plasma_concentration_mg_per_l"] - predicted) ** 2
            )

        rmse = math.sqrt(sum(squared_errors) / len(squared_errors))
        assert abs(report["fit_model"]["rmse_mg_per_l"] - rmse) <= 0.01


class TestDischargeRecommendation:
    def test_discharge_threshold_logic(self):
        report = load_json(REPORT_PATH)
        truth = load_json(VERIFICATION_PATH)

        predicted_at_discharge = report["discharge_summary"][
            "predicted_concentration_at_discharge_mg_per_l"
        ]
        time_to_floor = report["discharge_summary"]["time_to_fall_below_floor_hr"]
        discharge_time = report["discharge_summary"]["discharge_time_hr"]
        dose_due = report["discharge_summary"]["dose_due_before_discharge"]

        assert (
            abs(predicted_at_discharge - truth["predicted_concentration_at_discharge_mg_per_l"])
            / truth["predicted_concentration_at_discharge_mg_per_l"]
            <= 0.12
        )
        assert abs(time_to_floor - truth["time_to_fall_below_floor_hr"]) <= 0.8
        assert predicted_at_discharge < report["discharge_summary"]["subtherapeutic_floor_mg_per_l"]
        assert time_to_floor < discharge_time
        assert dose_due is True
