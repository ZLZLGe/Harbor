import csv
import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path("/root")

MANIFEST_PATH = ROOT / "conference_manifest.json"
SEAT_MAP_PATH = ROOT / "room_seat_map.csv"
SCHEDULE_PATH = ROOT / "meeting_schedule.json"
CHECKIN_PATH = ROOT / "checkin_log.csv"
TIMELINE_PATH = ROOT / "room_state_timeline.json"
MATRIX_PATH = ROOT / "seat_usage_csr.npz"


def load_json(path: Path):
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def load_seat_map(path: Path):
    rows = []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        for row in reader:
            rows.append(row)
    return rows


def load_checkins(path: Path):
    rows = []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append(
                {
                    "attendee_id": row["attendee_id"],
                    "meeting_id": row["meeting_id"],
                    "seat_id": row["seat_id"],
                    "slot_start": int(row["slot_start"]),
                    "slot_end": int(row["slot_end"]),
                }
            )
    return rows


def seat_positions(seat_map, empty_token):
    positions = {}
    for row_idx, row in enumerate(seat_map):
        for col_idx, cell in enumerate(row):
            if cell != empty_token:
                positions[cell] = (row_idx, col_idx)
    return positions


def expected_timeline(manifest, schedule, checkins):
    meeting_by_slot = {}
    for item in schedule:
        for slot_idx in range(int(item["start_slot"]), int(item["end_slot"])):
            assert slot_idx not in meeting_by_slot, "同一时隙最多只能有一个会议"
            meeting_by_slot[slot_idx] = item

    timeline = []
    for slot_idx in range(int(manifest["slot_count"])):
        occupied = sorted(
            row["seat_id"]
            for row in checkins
            if row["slot_start"] <= slot_idx < row["slot_end"]
        )
        meeting = meeting_by_slot.get(slot_idx)
        occupied_count = len(occupied)

        if meeting is None:
            state = "Vacant" if occupied_count == 0 else "Reset"
            meeting_id = None
            meeting_title = None
        else:
            reserved = int(meeting["reserved_seats"])
            if occupied_count > reserved:
                state = "Overflow"
            elif slot_idx == int(meeting["start_slot"]) or occupied_count < reserved:
                state = "Check-In"
            else:
                state = "In Session"
            meeting_id = meeting["meeting_id"]
            meeting_title = meeting["title"]

        timeline.append(
            {
                "slot_idx": slot_idx,
                "window": manifest["slot_windows"][slot_idx],
                "state": state,
                "meeting_id": meeting_id,
                "meeting_title": meeting_title,
                "occupied_count": occupied_count,
                "occupied_seat_ids": occupied,
            }
        )
    return timeline


def load_dense_slot(npz_data, slot_idx, shape):
    data_key = f"slot_{slot_idx}_data"
    indices_key = f"slot_{slot_idx}_indices"
    indptr_key = f"slot_{slot_idx}_indptr"

    assert data_key in npz_data, f"缺少 {data_key}"
    assert indices_key in npz_data, f"缺少 {indices_key}"
    assert indptr_key in npz_data, f"缺少 {indptr_key}"

    data = npz_data[data_key]
    indices = npz_data[indices_key]
    indptr = npz_data[indptr_key]

    assert indptr.shape == (shape[0] + 1,), f"{indptr_key} 长度错误"
    assert np.all(indptr[1:] >= indptr[:-1]), f"{indptr_key} 必须单调不降"
    assert int(indptr[-1]) == len(indices) == len(data), f"{slot_idx} 的 CSR 长度不一致"
    if len(indices):
        assert int(indices.min()) >= 0
        assert int(indices.max()) < shape[1]
    if len(data):
        assert set(np.unique(data).tolist()) <= {1, True}, f"{slot_idx} 的 data 必须是二值 1/True"

    dense = np.zeros(shape, dtype=bool)
    for row_idx in range(shape[0]):
        start = int(indptr[row_idx])
        end = int(indptr[row_idx + 1])
        if end > start:
            dense[row_idx, indices[start:end]] = True
    return dense


def expected_dense(shape, positions, occupied_seat_ids):
    dense = np.zeros(shape, dtype=bool)
    for seat_id in occupied_seat_ids:
        row_idx, col_idx = positions[seat_id]
        dense[row_idx, col_idx] = True
    return dense


class TestFilesExist:
    def test_outputs_exist(self):
        assert TIMELINE_PATH.exists(), "缺少 /root/room_state_timeline.json"
        assert MATRIX_PATH.exists(), "缺少 /root/seat_usage_csr.npz"


class TestTimelineOutput:
    @pytest.fixture(scope="class")
    def manifest(self):
        return load_json(MANIFEST_PATH)

    @pytest.fixture(scope="class")
    def schedule(self):
        return load_json(SCHEDULE_PATH)

    @pytest.fixture(scope="class")
    def checkins(self):
        return load_checkins(CHECKIN_PATH)

    @pytest.fixture(scope="class")
    def output(self):
        return load_json(TIMELINE_PATH)

    def test_top_level_schema(self, manifest, output):
        assert isinstance(output, dict), "room_state_timeline.json 根节点必须是 object"
        assert output["room_id"] == manifest["room_id"]
        assert output["seat_matrix_shape"] == manifest["seat_matrix_shape"]
        assert output["seat_matrix_path"] == manifest["seat_matrix_path"]
        assert isinstance(output["timeline"], list)
        assert len(output["timeline"]) == int(manifest["slot_count"])

    def test_each_slot_item_is_valid(self, manifest, output):
        allowed_states = set(manifest["allowed_states"])
        for slot_idx, item in enumerate(output["timeline"]):
            assert item["slot_idx"] == slot_idx
            assert item["window"] == manifest["slot_windows"][slot_idx]
            assert item["state"] in allowed_states
            assert isinstance(item["occupied_seat_ids"], list)
            assert item["occupied_seat_ids"] == sorted(item["occupied_seat_ids"])
            assert len(set(item["occupied_seat_ids"])) == len(item["occupied_seat_ids"])
            assert item["occupied_count"] == len(item["occupied_seat_ids"])

    def test_timeline_semantics(self, manifest, schedule, checkins, output):
        assert output["timeline"] == expected_timeline(manifest, schedule, checkins)


class TestSeatMatrixOutput:
    @pytest.fixture(scope="class")
    def manifest(self):
        return load_json(MANIFEST_PATH)

    @pytest.fixture(scope="class")
    def seat_map(self):
        return load_seat_map(SEAT_MAP_PATH)

    @pytest.fixture(scope="class")
    def checkins(self):
        return load_checkins(CHECKIN_PATH)

    @pytest.fixture(scope="class")
    def output(self):
        return load_json(TIMELINE_PATH)

    @pytest.fixture(scope="class")
    def npz_data(self):
        return np.load(MATRIX_PATH, allow_pickle=False)

    def test_csr_schema(self, manifest, npz_data):
        assert "shape" in npz_data, "NPZ 缺少 shape"
        assert "slots" in npz_data, "NPZ 缺少 slots"
        assert tuple(int(v) for v in npz_data["shape"]) == tuple(manifest["seat_matrix_shape"])
        assert np.array_equal(npz_data["slots"], np.arange(int(manifest["slot_count"])))

    def test_dense_matrices_match_timeline(self, manifest, seat_map, output, npz_data):
        shape = tuple(int(v) for v in manifest["seat_matrix_shape"])
        positions = seat_positions(seat_map, manifest["empty_seat_token"])

        for item in output["timeline"]:
            expected = expected_dense(shape, positions, item["occupied_seat_ids"])
            actual = load_dense_slot(npz_data, item["slot_idx"], shape)
            assert np.array_equal(actual, expected), f"slot {item['slot_idx']} 的座位矩阵与 timeline 不一致"

    def test_empty_cells_never_marked(self, manifest, seat_map, npz_data):
        shape = tuple(int(v) for v in manifest["seat_matrix_shape"])
        empty_cells = [
            (row_idx, col_idx)
            for row_idx, row in enumerate(seat_map)
            for col_idx, cell in enumerate(row)
            if cell == manifest["empty_seat_token"]
        ]

        for slot_idx in range(int(manifest["slot_count"])):
            dense = load_dense_slot(npz_data, slot_idx, shape)
            for row_idx, col_idx in empty_cells:
                assert not dense[row_idx, col_idx], f"slot {slot_idx} 的走道单元不应被占用"
