import json
import struct
import zlib
from pathlib import Path


OUTPUT_PATH = Path("/app/output/crosswalk_direction_counts.json")
INPUT_ROOT = Path("/app/crosswalk_sequences")

BACKGROUND_COLORS = {
    (188, 198, 205),
    (73, 79, 86),
    (140, 146, 153),
    (245, 246, 248),
    (232, 210, 120),
    (90, 52, 31),
    (45, 108, 66),
}

LEFT_SIDE_MAX_X = 34
RIGHT_SIDE_MIN_X = 126
CROSSWALK_MIN_X = 42
CROSSWALK_MAX_X = 118


def read_png_pixels(path: Path) -> list[list[tuple[int, int, int]]]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"Unsupported PNG signature: {path}")

    pos = 8
    width = None
    height = None
    idat_chunks: list[bytes] = []

    while pos < len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        pos += 4
        chunk_type = data[pos:pos + 4]
        pos += 4
        chunk_data = data[pos:pos + length]
        pos += length
        pos += 4  # skip CRC

        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, compression, flt, interlace = struct.unpack(
                ">IIBBBBB", chunk_data
            )
            if bit_depth != 8 or color_type != 2 or compression != 0 or flt != 0 or interlace != 0:
                raise ValueError(f"Unsupported PNG format: {path}")
        elif chunk_type == b"IDAT":
            idat_chunks.append(chunk_data)
        elif chunk_type == b"IEND":
            break

    if width is None or height is None:
        raise ValueError(f"Missing IHDR chunk: {path}")

    raw = zlib.decompress(b"".join(idat_chunks))
    stride = 1 + width * 3
    rows: list[list[tuple[int, int, int]]] = []
    for row_index in range(height):
        row = raw[row_index * stride:(row_index + 1) * stride]
        filter_type = row[0]
        if filter_type != 0:
            raise ValueError(f"Unsupported PNG filter {filter_type} in {path}")
        pixels = [tuple(row[i:i + 3]) for i in range(1, len(row), 3)]
        rows.append(pixels)
    return rows


def extract_centroids(frame_path: Path) -> dict[tuple[int, int, int], float]:
    rows = read_png_pixels(frame_path)
    totals: dict[tuple[int, int, int], list[int]] = {}
    for row in rows:
        for x, color in enumerate(row):
            if color in BACKGROUND_COLORS:
                continue
            if color not in totals:
                totals[color] = [0, 0]
            totals[color][0] += x
            totals[color][1] += 1
    return {color: total_x / count for color, (total_x, count) in totals.items()}


def count_completed_crossings(frame_paths: list[Path]) -> tuple[int, int]:
    tracks: dict[tuple[int, int, int], list[float]] = {}
    for frame_path in frame_paths:
        for color, centroid_x in extract_centroids(frame_path).items():
            tracks.setdefault(color, []).append(centroid_x)

    left_to_right = 0
    right_to_left = 0
    for xs in tracks.values():
        if min(xs) >= CROSSWALK_MIN_X or max(xs) <= CROSSWALK_MAX_X:
            continue
        if xs[0] <= LEFT_SIDE_MAX_X and xs[-1] >= RIGHT_SIDE_MIN_X and xs[-1] > xs[0]:
            left_to_right += 1
        elif xs[0] >= RIGHT_SIDE_MIN_X and xs[-1] <= LEFT_SIDE_MAX_X and xs[-1] < xs[0]:
            right_to_left += 1
    return left_to_right, right_to_left


def load_expected_results() -> tuple[list[str], dict[str, dict[str, int]]]:
    index = json.loads((INPUT_ROOT / "clip_index.json").read_text(encoding="utf-8"))
    expected_order = []
    expected_counts = {}

    for item in index["videos"]:
        video_id = item["video_id"]
        frame_dir = INPUT_ROOT / item["frames_dir"]
        frame_paths = [frame_dir / name for name in item["frame_files"]]
        left_to_right, right_to_left = count_completed_crossings(frame_paths)
        expected_order.append(video_id)
        expected_counts[video_id] = {
            "left_to_right": left_to_right,
            "right_to_left": right_to_left,
        }

    return expected_order, expected_counts


def test_output_file_exists():
    assert OUTPUT_PATH.exists(), "缺少输出文件 /app/output/crosswalk_direction_counts.json"


def test_output_schema_and_values():
    data = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    expected_order, expected_counts = load_expected_results()

    assert isinstance(data, dict), "输出必须是 JSON 对象"
    assert set(data.keys()) == {"videos"}, "顶层只能包含 videos"
    videos = data["videos"]
    assert isinstance(videos, list), "videos 必须是数组"
    assert len(videos) == len(expected_order), f"videos 必须包含 {len(expected_order)} 条记录"

    actual_order = []
    for item in videos:
        assert isinstance(item, dict), "videos 中的每一项都必须是对象"
        assert set(item.keys()) == {"video_id", "left_to_right", "right_to_left"}, (
            "每条记录只能包含 video_id、left_to_right、right_to_left"
        )
        video_id = item["video_id"]
        actual_order.append(video_id)
        assert video_id in expected_counts, f"未知 video_id: {video_id}"
        for key in ("left_to_right", "right_to_left"):
            value = item[key]
            assert isinstance(value, int), f"{video_id}.{key} 必须是整数"
            assert value >= 0, f"{video_id}.{key} 必须是非负整数"
            assert value == expected_counts[video_id][key], (
                f"{video_id}.{key} 错误，期望 {expected_counts[video_id][key]}，实际 {value}"
            )

    assert actual_order == expected_order, (
        f"videos 顺序错误，期望 {expected_order}，实际 {actual_order}"
    )
