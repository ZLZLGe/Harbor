#!/bin/bash
set -euo pipefail

python3 - <<'PY'
from pathlib import Path

path = Path("/root/rankbench/rankbench/objective.py")
text = path.read_text(encoding="utf-8")
old = """    \"\"\"Return the per-example loss from the paper's length-normalized BT objective.\"\"\"\n    raise NotImplementedError(\"Implement Eq. (4) and Eq. (6) from the paper PDF.\")\n"""
new = """    \"\"\"Return the per-example loss from the paper's length-normalized BT objective.\"\"\"\n    chosen_sums = _masked_sums(chosen_token_logps, chosen_lengths)\n    rejected_sums = _masked_sums(rejected_token_logps, rejected_lengths)\n\n    chosen_rewards = beta * chosen_sums / chosen_lengths\n    rejected_rewards = beta * rejected_sums / rejected_lengths\n    logits = chosen_rewards - rejected_rewards - gamma\n    return np.logaddexp(0.0, -logits)\n"""

if old not in text:
    raise SystemExit("target block not found in objective.py")

path.write_text(text.replace(old, new), encoding="utf-8")
PY

PYTHONPATH=/root/rankbench python3 /root/rankbench/scripts/run_fixed_case.py
