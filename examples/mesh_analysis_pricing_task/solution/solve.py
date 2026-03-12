import json
import re
import sys
from pathlib import Path


TASK_ROOT = Path(__file__).resolve().parents[1]
SKILL_SCRIPTS = TASK_ROOT / "environment" / "skills" / "mesh-analysis" / "scripts"
INPUT_STL = TASK_ROOT / "environment" / "scan_input.stl"
PRICE_TABLE = TASK_ROOT / "environment" / "material_price_table.md"
OUTPUT_PATH = TASK_ROOT / "output" / "pricing_report.json"

sys.path.insert(0, str(SKILL_SCRIPTS))

from mesh_tool import MeshAnalyzer  # noqa: E402


def load_price_table(path: Path) -> dict[int, float]:
    mapping: dict[int, float] = {}
    pattern = re.compile(r"\|\s*\*\*(\d+)\*\*\s*\|[^|]*\|\s*([0-9]+(?:\.[0-9]+)?)\s*\|")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.search(line)
        if match:
            material_id = int(match.group(1))
            unit_price = float(match.group(2))
            mapping[material_id] = unit_price
    return mapping


def main() -> None:
    analyzer = MeshAnalyzer(str(INPUT_STL))
    report = analyzer.analyze_largest_component()
    price_table = load_price_table(PRICE_TABLE)

    material_id = report["main_part_material_id"]
    if material_id not in price_table:
        raise KeyError(f"Unknown material id: {material_id}")

    estimated_cost = report["main_part_volume"] * price_table[material_id]
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(
            {
                "main_part_estimated_cost": estimated_cost,
                "material_id": material_id,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
