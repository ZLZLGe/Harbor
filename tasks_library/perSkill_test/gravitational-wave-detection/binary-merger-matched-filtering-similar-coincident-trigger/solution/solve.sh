#!/bin/bash
set -euo pipefail

python3 - <<'PY'
import json
from pathlib import Path

import numpy as np

data = np.load("/root/data/coincident_inputs.npz")
sample_rate_hz = float(data["sample_rate_hz"])
gps_start = float(data["gps_start"])
h1_strain = data["h1_strain"]
l1_strain = data["l1_strain"]
template_ids = data["template_ids"]
templates = data["templates"]
template_length = int(templates.shape[1])


def peak_snr(strain, template):
    series = np.correlate(strain, template, mode="valid")
    peak_index = int(np.abs(series).argmax())
    peak_value = float(np.abs(series[peak_index]))
    peak_time = gps_start + (peak_index + template_length / 2.0) / sample_rate_hz
    return peak_value, peak_time


best = None
for template_id, template in zip(template_ids, templates):
    h1_peak_snr, h1_peak_time = peak_snr(h1_strain, template)
    l1_peak_snr, l1_peak_time = peak_snr(l1_strain, template)
    network_snr = float(np.hypot(h1_peak_snr, l1_peak_snr))
    candidate = {
        "template_id": str(template_id),
        "event_time": float((h1_peak_time + l1_peak_time) / 2.0),
        "h1_peak_snr": h1_peak_snr,
        "l1_peak_snr": l1_peak_snr,
    }
    if best is None or network_snr > best[0] or (
        network_snr == best[0] and candidate["template_id"] < best[1]["template_id"]
    ):
        best = (network_snr, candidate)

Path("/root/coincident_trigger.json").write_text(
    json.dumps(best[1], indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY
