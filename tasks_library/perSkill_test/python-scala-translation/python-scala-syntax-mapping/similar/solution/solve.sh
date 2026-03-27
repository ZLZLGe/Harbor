#!/bin/bash
set -euo pipefail

mkdir -p /outputs

python3 - <<'PY'
import json
from pathlib import Path

input_path = Path('/root/mapping_cases.json')
output_path = Path('/outputs/syntax_mapping_reference.json')

cases = json.loads(input_path.read_text(encoding='utf-8'))

mapping = {
    "x = 5": "val x = 5",
    "x: int = 5": "val x: Int = 5",
    "x, y = 1, 2": "val (x, y) = (1, 2)",
    "if x > 0: positive elif x < 0: negative else: zero": "val result = if (x > 0) \"positive\" else if (x < 0) \"negative\" else \"zero\"",
    "for i in range(10): print(i)": "for (i <- 0 until 10) println(i)",
    "evens = [x for x in numbers if x % 2 == 0]": "val evens = numbers.filter(_ % 2 == 0)",
    "f\"Hello, {name}!\"": "s\"Hello, $name!\"",
    "ready and not blocked": "ready && !blocked"
}

result = []
for item in cases:
    result.append({
        "case_id": item["case_id"],
        "category": item["category"],
        "python": item["python"],
        "scala": mapping[item["python"]]
    })

output_path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
PY
