from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", "/app/output"))
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "/app/data"))
OUTPUT_PATH = OUTPUT_ROOT / "opportunity_report.json"


def load_output_json() -> dict[str, Any]:
    return json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
