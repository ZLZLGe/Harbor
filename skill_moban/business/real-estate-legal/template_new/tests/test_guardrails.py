from __future__ import annotations

import os
import subprocess
from pathlib import Path

from common import MEMO_PATH, ONE_PAGER_PATH, stale_markers


def test_input_data_was_not_modified() -> None:
    data_root = Path(os.environ.get("TASK_DATA_ROOT", "/root/data"))
    expected_data_hash_path = Path(os.environ.get("TASK_DATA_HASH_PATH", "/opt/noticeflow-data.sha256"))

    current_data = subprocess.check_output(
        f"find {data_root} -type f -print0 | sort -z | xargs -0 sha256sum",
        shell=True,
        text=True,
    )
    expected_data = expected_data_hash_path.read_text(encoding="utf-8")
    assert current_data == expected_data, "Input data under /root/data was modified"


def test_outputs_do_not_carry_stale_markers() -> None:
    combined = MEMO_PATH.read_text(encoding="utf-8") + "\n" + ONE_PAGER_PATH.read_text(encoding="utf-8")
    for marker in stale_markers():
        assert marker not in combined, f"Found stale marker in investor-facing output: {marker}"
