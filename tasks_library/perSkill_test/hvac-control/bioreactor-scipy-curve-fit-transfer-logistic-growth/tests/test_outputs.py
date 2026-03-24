#!/usr/bin/env python3

import json
import math
import os

import numpy as np


ROOT_DIR = "/root"
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_PATH = os.path.join(ROOT_DIR, "bioreactor_growth_fit.json")
INPUT_PATH = os.path.join(ROOT_DIR, "bioreactor_batch_run.json")
VERIFICATION_PATH = os.path.join(TESTS_DIR, "verification_params.json")


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def logistic_model(time_hr, carrying_capacity, growth_rate, midpoint_time):
    return carrying_capacity / (1.0 + np.exp(-growth_rate * (time_hr - midpoint_time)))


def inverse_logistic(target_od, carrying_capacity, growth_rate, midpoint_time):
    return midpoint_time - math.log(carrying_capacity / target_od - 1.0) / growth_rate


class TestReportStructure:
    def test_required_fields_present(self):
        report = load_json(REPORT_PATH)

        for field in [
            "batch_id",
            "input_file",
            "reactor_volume_l",
            "target_harvest_od600",
            "latest_recommended_od600",
            "samples_used",
            "fit_model",
            "harvest_forecast",
        ]:
            assert field in report, f"missing '{field}'"

        for field in [
            "initial_od600",
            "carrying_capacity_od600",
            "growth_rate_per_hr",
            "midpoint_time_hr",
            "lag_adjusted_onset_hr",
            "max_growth_rate_od600_per_hr",
            "rmse_od600",
            "r_squared",
        ]:
            assert field in report["fit_model"], f"missing fit_model field '{field}'"

        for field in [
            "time_to_target_od600_hr",
            "time_to_latest_recommended_od600_hr",
            "harvest_window_start_hr",
            "harvest_window_end_hr",
            "predicted_window_width_hr",
        ]:
            assert field in report["harvest_forecast"], f"missing harvest_forecast field '{field}'"

    def test_metadata_matches_input(self):
        report = load_json(REPORT_PATH)
        batch = load_json(INPUT_PATH)

        assert report["batch_id"] == batch["batch_id"]
        assert report["input_file"] == "bioreactor_batch_run.json"
        assert abs(report["reactor_volume_l"] - batch["reactor_volume_l"]) <= 1e-9
        assert abs(report["target_harvest_od600"] - batch["target_harvest_od600"]) <= 1e-9
        assert (
            abs(report["latest_recommended_od600"] - batch["latest_recommended_od600"]) <= 1e-9
        )
        assert report["samples_used"] == len(batch["observations"])


class TestFitAccuracy:
    def test_parameters_close_to_reference(self):
        report = load_json(REPORT_PATH)
        truth = load_json(VERIFICATION_PATH)

        fit = report["fit_model"]

        carrying_capacity_error = abs(
            fit["carrying_capacity_od600"] - truth["carrying_capacity_od600"]
        ) / truth["carrying_capacity_od600"]
        growth_rate_error = abs(
            fit["growth_rate_per_hr"] - truth["growth_rate_per_hr"]
        ) / truth["growth_rate_per_hr"]
        midpoint_error = abs(fit["midpoint_time_hr"] - truth["midpoint_time_hr"])

        assert carrying_capacity_error <= 0.08
        assert growth_rate_error <= 0.10
        assert midpoint_error <= 0.8

    def test_fit_quality_is_reasonable(self):
        report = load_json(REPORT_PATH)
        fit = report["fit_model"]

        assert fit["rmse_od600"] <= 0.03
        assert fit["r_squared"] >= 0.998


class TestDerivedMetrics:
    def test_fit_metrics_match_model_equations(self):
        report = load_json(REPORT_PATH)
        batch = load_json(INPUT_PATH)

        fit = report["fit_model"]
        forecast = report["harvest_forecast"]

        carrying_capacity = fit["carrying_capacity_od600"]
        growth_rate = fit["growth_rate_per_hr"]
        midpoint_time = fit["midpoint_time_hr"]

        expected_initial = float(
            logistic_model(np.array([0.0]), carrying_capacity, growth_rate, midpoint_time)[0]
        )
        expected_lag = midpoint_time - 2.0 / growth_rate
        expected_max_growth = carrying_capacity * growth_rate / 4.0
        expected_target_time = inverse_logistic(
            report["target_harvest_od600"], carrying_capacity, growth_rate, midpoint_time
        )
        expected_latest_time = inverse_logistic(
            report["latest_recommended_od600"], carrying_capacity, growth_rate, midpoint_time
        )

        assert abs(fit["initial_od600"] - expected_initial) <= 1e-6
        assert abs(fit["lag_adjusted_onset_hr"] - expected_lag) <= 1e-6
        assert abs(fit["max_growth_rate_od600_per_hr"] - expected_max_growth) <= 1e-6
        assert abs(forecast["time_to_target_od600_hr"] - expected_target_time) <= 1e-6
        assert abs(forecast["time_to_latest_recommended_od600_hr"] - expected_latest_time) <= 1e-6
        assert abs(forecast["harvest_window_start_hr"] - expected_target_time) <= 1e-6
        assert abs(forecast["harvest_window_end_hr"] - expected_latest_time) <= 1e-6
        assert abs(
            forecast["predicted_window_width_hr"]
            - (forecast["harvest_window_end_hr"] - forecast["harvest_window_start_hr"])
        ) <= 1e-6

        assert report["samples_used"] == len(batch["observations"])

    def test_rmse_and_r_squared_match_observations(self):
        report = load_json(REPORT_PATH)
        batch = load_json(INPUT_PATH)

        fit = report["fit_model"]
        times = np.array([row["time_hr"] for row in batch["observations"]], dtype=float)
        observed = np.array([row["od600"] for row in batch["observations"]], dtype=float)
        predicted = logistic_model(
            times,
            fit["carrying_capacity_od600"],
            fit["growth_rate_per_hr"],
            fit["midpoint_time_hr"],
        )

        residuals = observed - predicted
        rmse = float(np.sqrt(np.mean(residuals ** 2)))
        ss_res = float(np.sum(residuals ** 2))
        ss_tot = float(np.sum((observed - np.mean(observed)) ** 2))
        r_squared = float(1.0 - ss_res / ss_tot)

        assert abs(fit["rmse_od600"] - rmse) <= 1e-6
        assert abs(fit["r_squared"] - r_squared) <= 1e-6


class TestHarvestForecast:
    def test_forecast_close_to_reference(self):
        report = load_json(REPORT_PATH)
        truth = load_json(VERIFICATION_PATH)
        forecast = report["harvest_forecast"]

        assert abs(forecast["time_to_target_od600_hr"] - truth["time_to_target_od600_hr"]) <= 0.6
        assert (
            abs(
                forecast["time_to_latest_recommended_od600_hr"]
                - truth["time_to_latest_recommended_od600_hr"]
            )
            <= 0.6
        )
        assert abs(forecast["predicted_window_width_hr"] - truth["predicted_window_width_hr"]) <= 0.7

    def test_window_is_ordered_and_positive(self):
        report = load_json(REPORT_PATH)
        forecast = report["harvest_forecast"]

        assert forecast["time_to_target_od600_hr"] < forecast["time_to_latest_recommended_od600_hr"]
        assert forecast["harvest_window_start_hr"] < forecast["harvest_window_end_hr"]
        assert forecast["predicted_window_width_hr"] > 0.0
