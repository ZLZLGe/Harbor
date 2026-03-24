import csv
from pathlib import Path


OUTPUT_FILE = Path("/app/trays/germination_report.csv")
REWARD_FILE = Path("/logs/verifier/reward.txt")
EXPECTED = {
    "tray_amber": ["A2", "A5", "B1", "B4", "B8", "C3", "C6", "D2", "D5", "D7", "E4", "E8"],
    "tray_cedar": ["A1", "A8", "B3", "B6", "C2", "C5", "D4", "E1", "E7"],
    "tray_fallow": [],
    "tray_moss": ["A3", "A4", "A7", "B2", "B5", "B7", "C1", "C8", "D3", "D6", "D8", "E2", "E5", "E6"],
    "tray_slate": ["B1", "C4", "E8"],
}


def write_reward(value: float) -> None:
    REWARD_FILE.parent.mkdir(parents=True, exist_ok=True)
    REWARD_FILE.write_text(f"{value:.4f}\n", encoding="utf-8")


def test_outputs() -> None:
    try:
        assert OUTPUT_FILE.exists(), f"缺少输出文件: {OUTPUT_FILE}"

        with OUTPUT_FILE.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.reader(handle))

        assert rows, "CSV 为空"
        assert rows[0] == ["tray_id", "germinated_count", "germinated_cells"], (
            "表头必须严格为 ['tray_id', 'germinated_count', 'germinated_cells']"
        )

        data_rows = [row for row in rows[1:] if any(cell.strip() for cell in row)]
        expected_ids = sorted(EXPECTED)
        assert len(data_rows) == len(expected_ids), f"数据行数量不正确，实际 {len(data_rows)}，期望 {len(expected_ids)}"

        actual_ids = [row[0] for row in data_rows]
        assert actual_ids == expected_ids, f"数据行必须按 tray_id 升序排列，实际 {actual_ids}，期望 {expected_ids}"

        for row in data_rows:
            assert len(row) == 3, f"每行只能有三列，实际为 {row}"
            tray_id, germinated_count, germinated_cells = row
            expected_cells = EXPECTED[tray_id]

            assert germinated_count.isdigit(), f"{tray_id} 的 germinated_count 必须是非负整数，实际为 {germinated_count!r}"
            assert int(germinated_count) == len(expected_cells), (
                f"{tray_id} 的 germinated_count 不正确，实际 {germinated_count}，期望 {len(expected_cells)}"
            )

            expected_text = ";".join(expected_cells)
            assert germinated_cells == expected_text, (
                f"{tray_id} 的 germinated_cells 不正确，实际 {germinated_cells!r}，期望 {expected_text!r}"
            )

        write_reward(1.0)
    except Exception:
        write_reward(0.0)
        raise
