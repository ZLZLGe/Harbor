import csv
import os


def test_outputs() -> None:
    workspace_root = os.environ.get("WORKSPACE_ROOT", "/app/workspace")
    output_path = os.path.join(workspace_root, "output", "spatial_report.csv")
    assert os.path.exists(output_path), f"缺少输出文件: {output_path}"

    with open(output_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        actual = list(reader)
        headers = reader.fieldnames

    expected_headers = ["tile_id", "pop_density", "population_band", "relief_index"]
    expected = [
        {"tile_id": "G-02", "pop_density": "7500.000", "population_band": "medium", "relief_index": "0.340"},
        {"tile_id": "G-04", "pop_density": "6250.000", "population_band": "medium", "relief_index": "0.560"},
        {"tile_id": "G-03", "pop_density": "5000.000", "population_band": "low", "relief_index": "0.080"},
        {"tile_id": "G-01", "pop_density": "4000.000", "population_band": "low", "relief_index": "0.120"},
    ]

    assert headers == expected_headers, f"输出列不匹配: {headers}"
    assert actual == expected, f"输出内容不匹配.\nactual={actual}\nexpected={expected}"
