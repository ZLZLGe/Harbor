#!/bin/bash
set -euo pipefail

python3 <<'PY'
import itertools
import json
from pathlib import Path

DATA_DIR = Path("/app/data")
OUTPUT_DIR = Path("/app/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "secure_hub_runbook_verdict.json"


def load_json(name):
    return json.loads((DATA_DIR / name).read_text())


incident = load_json("incident_memo.json")
topology = load_json("topology_snapshot.json")
observations = load_json("propagation_observations.json")
steps = load_json("runbook_candidates.json")
rules = load_json("azure_platform_rules.json")

preferences = {item["asn"]: item["prefer_via"] for item in topology["preferences"]}


def find_cycle(pref_map):
    for start in sorted(pref_map):
        order = []
        seen = {}
        current = start
        while current in pref_map:
            if current in seen:
                cycle = order[seen[current]:]
                return sorted(cycle)
            seen[current] = len(order)
            order.append(current)
            current = pref_map[current]
    return []


cycle = find_cycle(preferences)
route_leak_ids = sorted(
    observation["observation_id"]
    for observation in observations
    if observation["learned_from_relationship"] in {"provider", "peer"}
    and observation["exported_to_relationship"] in {"provider", "peer"}
)

forbidden = set(rules["forbidden_action_types"])
cycle_fixers = set(rules["cycle_break_action_types"])
leak_fixers = set(rules["leak_block_action_types"])

step_results = []
allowed_effective_steps = []

for step in sorted(steps, key=lambda item: item["step_id"]):
    action_type = step["action_type"]
    azure_allowed = action_type not in forbidden
    breaks_cycle = action_type in cycle_fixers and bool(cycle)
    blocks_leak = action_type in leak_fixers and bool(route_leak_ids)

    if not azure_allowed:
        verdict = "prohibited"
    elif breaks_cycle and blocks_leak:
        verdict = "full_fix"
    elif breaks_cycle:
        verdict = "cycle_only"
    elif blocks_leak:
        verdict = "leak_only"
    else:
        verdict = "no_effect"

    result = {
        "step_id": step["step_id"],
        "title": step["title"],
        "azure_allowed": azure_allowed,
        "breaks_preference_cycle": breaks_cycle,
        "blocks_route_leak": blocks_leak,
        "verdict": verdict,
    }
    step_results.append(result)
    if azure_allowed and verdict != "no_effect":
        allowed_effective_steps.append(result)

preferred_step_ids = sorted(
    result["step_id"]
    for result in step_results
    if result["verdict"] == "full_fix"
)

fallback_step_sets = []
full_fix_present = bool(preferred_step_ids)
if rules["selection_policy"]["allow_multi_step_fallbacks"]:
    for combo_size in range(2, len(allowed_effective_steps) + 1):
        combo_sets = []
        for combo in itertools.combinations(allowed_effective_steps, combo_size):
            step_ids = sorted(item["step_id"] for item in combo)
            covers_cycle = any(item["breaks_preference_cycle"] for item in combo)
            covers_leak = any(item["blocks_route_leak"] for item in combo)
            if covers_cycle and covers_leak:
                if full_fix_present and any(item["verdict"] == "full_fix" for item in combo):
                    continue
                combo_sets.append(step_ids)
        if combo_sets:
            fallback_step_sets = sorted(combo_sets, key=lambda ids: ",".join(ids))
            break

avoid_step_ids = sorted(
    result["step_id"]
    for result in step_results
    if result["verdict"] in {"prohibited", "no_effect"}
)

output = {
    "incident_findings": {
        "oscillation_detected": bool(cycle),
        "preference_cycle": cycle,
        "route_leak_detected": bool(route_leak_ids),
        "route_leak_ids": route_leak_ids,
    },
    "step_results": step_results,
    "execution_recommendation": {
        "preferred_step_ids": preferred_step_ids,
        "fallback_step_sets": fallback_step_sets,
        "avoid_step_ids": avoid_step_ids,
        "verdict": "prefer_single_allowed_full_fix" if preferred_step_ids else "use_allowed_fallback_set",
    },
}

OUTPUT_FILE.write_text(json.dumps(output, indent=2) + "\n")
PY
