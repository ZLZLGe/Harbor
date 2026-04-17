import hashlib
import importlib.util
import os
from pathlib import Path

import requests


WORKSPACE_ROOT = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))
HIDDEN_SERVICE_ROOT = Path(os.environ.get("HIDDEN_SERVICE_ROOT", "/opt/academic-api-hidden"))


def _sha256(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _ascii_strings(path: Path, min_len: int = 4) -> list[str]:
    data = path.read_bytes()
    chunks: list[str] = []
    current: list[str] = []
    for byte in data:
        if 32 <= byte <= 126:
            current.append(chr(byte))
        elif len(current) >= min_len:
            chunks.append("".join(current))
            current = []
        else:
            current = []
    if len(current) >= min_len:
        chunks.append("".join(current))
    return chunks


def test_protected_inputs_are_unchanged():
    expected = {
        str(WORKSPACE_ROOT / "review_protocol.md"): "dd776017e8b75dc7e6725ff4138b5351841b243148f7067db054f7cbdb974c23",
        str(WORKSPACE_ROOT / "build_submission.py"): "9ea2bd855e368a22fdbcc86381cb7a6b2a1f29d4bad18e1abd38636a0114acca",
        str(WORKSPACE_ROOT / "data" / "candidate_records.csv"): "73bd406dd01fe717bd978f01c574341496236474263e8327be75b105cec9aa4c",
        str(WORKSPACE_ROOT / "data" / "publication_cache.json"): "4f1129387262b7d5d6809de53d55138bd7c6fa79dc70497579dd5077e22c42d4",
    }

    for path, checksum in expected.items():
        assert _sha256(path) == checksum, f"Protected input changed: {path}"


def test_summary_and_tables_still_exist_as_real_deliverables():
    assert (WORKSPACE_ROOT / "included_studies.csv").exists()
    assert (WORKSPACE_ROOT / "references.bib").exists()
    assert (WORKSPACE_ROOT / "summary.md").exists()
    assert len((WORKSPACE_ROOT / "summary.md").read_text(encoding="utf-8").split()) >= 40


def test_hidden_service_source_is_not_solver_readable():
    module_path = WORKSPACE_ROOT / "build_submission.py"
    spec = importlib.util.spec_from_file_location("workspace_build_submission", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ensure_service()

    assert (HIDDEN_SERVICE_ROOT / "server.py").exists() is False
    assert (HIDDEN_SERVICE_ROOT / "service_entry.py").exists() is False
    assert (HIDDEN_SERVICE_ROOT / "service_entry.pyc").exists() is False
    assert (HIDDEN_SERVICE_ROOT / "review_snapshot.bin").exists() is False
    assert (HIDDEN_SERVICE_ROOT / "data" / "review_snapshot.json").exists() is False

    hidden_binary = HIDDEN_SERVICE_ROOT / "academic-api-server"
    assert hidden_binary.exists()
    assert hidden_binary.read_bytes()[:2] != b"#!"


def test_hidden_service_binaries_do_not_leak_canonical_strings():
    hidden_launcher = HIDDEN_SERVICE_ROOT / "academic-api-server"
    assert hidden_launcher.exists(), f"Hidden service artifact missing: {hidden_launcher}"
    output = "\n".join(_ascii_strings(hidden_launcher))
    for forbidden in [
        "study_001",
        "study_002",
        "study_003",
        "study_004",
        "10.1186/s12986-021-00613-9",
        "10.1001/jamanetworkopen.2023.39337",
        "10.1016/j.diabres.2024.111893",
        "10.1007/s00125-023-06045-9",
        "Che et al. 2021",
        "Pavlou et al. 2023",
        "Parr et al. 2024",
        "Trico et al. 2024",
    ]:
        assert forbidden not in output, f"Hidden service leaked canonical data via strings: {forbidden}"


def test_hidden_service_does_not_expose_protocol_mapping():
    module_path = WORKSPACE_ROOT / "build_submission.py"
    spec = importlib.util.spec_from_file_location("workspace_build_submission", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ensure_service()

    response = requests.get("http://127.0.0.1:8123/protocol", timeout=2)
    assert response.status_code == 404
