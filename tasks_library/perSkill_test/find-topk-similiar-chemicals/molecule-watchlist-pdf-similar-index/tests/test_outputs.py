import json
from pathlib import Path


OUTPUT_PATH = Path("/root/workspace/watchlist_hits.json")
WATCHLIST_PATH = Path("/root/data/watchlist.txt")

EXPECTED = {
    "Caffeine": {
        "found": True,
        "pages": [1, 2],
        "occurrence_count": 2,
        "page_positions": [
            {"page": 1, "positions": [3]},
            {"page": 2, "positions": [3]},
        ],
    },
    "Citric acid": {
        "found": True,
        "pages": [1, 3],
        "occurrence_count": 2,
        "page_positions": [
            {"page": 1, "positions": [5]},
            {"page": 3, "positions": [1]},
        ],
    },
    "Vanillin": {
        "found": True,
        "pages": [2, 3],
        "occurrence_count": 2,
        "page_positions": [
            {"page": 2, "positions": [6]},
            {"page": 3, "positions": [3]},
        ],
    },
    "Acetone": {
        "found": True,
        "pages": [1, 2],
        "occurrence_count": 3,
        "page_positions": [
            {"page": 1, "positions": [1, 4]},
            {"page": 2, "positions": [5]},
        ],
    },
    "Sucralose": {
        "found": False,
        "pages": [],
        "occurrence_count": 0,
        "page_positions": [],
    },
    "Lactic acid": {
        "found": True,
        "pages": [2, 3],
        "occurrence_count": 2,
        "page_positions": [
            {"page": 2, "positions": [2]},
            {"page": 3, "positions": [5]},
        ],
    },
}


def test_output_file_exists():
    assert OUTPUT_PATH.exists(), "缺少 /root/workspace/watchlist_hits.json"


def test_output_schema_and_values():
    watchlist = [
        line.strip()
        for line in WATCHLIST_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    data = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))

    assert isinstance(data, list), "输出必须是 JSON 数组"
    assert len(data) == len(watchlist), "输出数组长度必须与监测名单一致"

    seen = []
    for item, molecule in zip(data, watchlist):
        assert isinstance(item, dict), "数组元素必须是对象"
        for key in ["molecule", "found", "pages", "occurrence_count", "page_positions"]:
            assert key in item, f"缺少字段: {key}"

        assert item["molecule"] == molecule, "输出顺序必须与监测名单一致"
        seen.append(item["molecule"])

        expected = EXPECTED[molecule]
        assert item["found"] is expected["found"]
        assert item["pages"] == expected["pages"]
        assert item["occurrence_count"] == expected["occurrence_count"]
        assert item["page_positions"] == expected["page_positions"]

    assert seen == watchlist
