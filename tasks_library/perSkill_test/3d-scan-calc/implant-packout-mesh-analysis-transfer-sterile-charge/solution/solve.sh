#!/bin/bash
set -e

python3 - <<'PY'
import csv
import json
import math
import sys
import tomllib

sys.path.append("/root/.codex/skills/mesh-analysis/scripts")

from mesh_tool import MeshAnalyzer


def load_profiles():
    profiles = {}
    with open("/root/implant_material_profiles.tsv", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            profiles[int(row["material_id"])] = {
                "fill_multiplier": float(row["fill_multiplier"]),
                "base_handling_fee_usd": float(row["base_handling_fee_usd"]),
            }
    return profiles


def choose_pouch(fill_volume_ml, capacities):
    for pouch_name, capacity in sorted(capacities.items(), key=lambda item: item[1]):
        if fill_volume_ml <= capacity:
            return pouch_name
    return "large"


analyzer = MeshAnalyzer("/root/implant_segment.stl")
report = analyzer.analyze_largest_component()

profiles = load_profiles()
with open("/root/sterile_packout_policy.toml", "rb") as handle:
    policy = tomllib.load(handle)

material_id = report["main_part_material_id"]
volume_cm3 = report["main_part_volume"] / 1000.0
profile = profiles[material_id]

fill_volume_ml = volume_cm3 * profile["fill_multiplier"] + policy["fill"]["baseline_fill_ml"]
pouch_size = choose_pouch(fill_volume_ml, policy["pouch_capacity_ml"])
pad_count = math.ceil(fill_volume_ml / policy["pads"]["ml_per_pad"])
charge = profile["base_handling_fee_usd"] + (
    math.ceil(fill_volume_ml / policy["pricing"]["charge_step_ml"])
    * policy["pricing"]["charge_per_step_usd"]
)

result = {
    "material_id": material_id,
    "implant_volume_cm3": volume_cm3,
    "sterile_fill_volume_ml": fill_volume_ml,
    "pouch_size": pouch_size,
    "absorbent_pad_count": pad_count,
    "sterile_packout_charge_usd": charge,
}

with open("/root/sterile_packout.json", "w") as handle:
    json.dump(result, handle, indent=2)
PY
