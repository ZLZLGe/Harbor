import json
import math
from pathlib import Path

import numpy as np


OUTPUT_PATH = Path("/root/coincident_trigger.json")
DATA_PATH = Path("/root/data/coincident_inputs.npz")
REQUIRED_KEYS = {"template_id", "event_time", "h1_peak_snr", "l1_peak_snr"}


def _load_expected():
    data = np.load(DATA_PATH)
    sample_rate_hz = float(data["sample_rate_hz"])
    gps_start = float(data["gps_start"])
    h1_strain = data["h1_strain"]
    l1_strain = data["l1_strain"]
    template_ids = data["template_ids"]
    templates = data["templates"]
    template_length = int(templates.shape[1])

    best = None
    for template_id, template in zip(template_ids, templates):
        h1_series = np.correlate(h1_strain, template, mode="valid")
        l1_series = np.correlate(l1_strain, template, mode="valid")

        h1_index = int(np.abs(h1_series).argmax())
        l1_index = int(np.abs(l1_series).argmax())
        h1_peak = float(np.abs(h1_series[h1_index]))
        l1_peak = float(np.abs(l1_series[l1_index]))

        h1_peak_time = gps_start + (h1_index + template_length / 2.0) / sample_rate_hz
        l1_peak_time = gps_start + (l1_index + template_length / 2.0) / sample_rate_hz
        event_time = float((h1_peak_time + l1_peak_time) / 2.0)
        network_snr = float(np.hypot(h1_peak, l1_peak))

        candidate = {
            "template_id": str(template_id),
            "event_time": event_time,
            "h1_peak_snr": h1_peak,
            "l1_peak_snr": l1_peak,
        }
        if best is None or network_snr > best[0] or (
            network_snr == best[0] and candidate["template_id"] < best[1]["template_id"]
        ):
            best = (network_snr, candidate)

    return best[1], set(str(x) for x in template_ids)


def test_output_exists():
    assert OUTPUT_PATH.exists(), f"missing output file: {OUTPUT_PATH}"


def test_output_schema_and_values():
    content = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    assert isinstance(content, dict), "output must be a JSON object"
    assert REQUIRED_KEYS.issubset(content), f"missing required keys: {sorted(REQUIRED_KEYS - set(content))}"

    expected, allowed_template_ids = _load_expected()

    assert isinstance(content["template_id"], str), "template_id must be a string"
    assert content["template_id"] in allowed_template_ids, "template_id must come from template_ids"

    for key in ("event_time", "h1_peak_snr", "l1_peak_snr"):
        assert isinstance(content[key], (int, float)), f"{key} must be numeric"
        assert math.isfinite(content[key]), f"{key} must be finite"

    assert content["h1_peak_snr"] >= 0.0
    assert content["l1_peak_snr"] >= 0.0

    assert content["template_id"] == expected["template_id"]
    assert math.isclose(content["event_time"], expected["event_time"], rel_tol=0.0, abs_tol=1e-6)
    assert math.isclose(content["h1_peak_snr"], expected["h1_peak_snr"], rel_tol=0.0, abs_tol=1e-6)
    assert math.isclose(content["l1_peak_snr"], expected["l1_peak_snr"], rel_tol=0.0, abs_tol=1e-6)
