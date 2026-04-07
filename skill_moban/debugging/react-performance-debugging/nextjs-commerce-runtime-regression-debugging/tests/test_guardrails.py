import hashlib
from pathlib import Path


def _sha256(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_hidden_catalog_simulator_not_modified():
    expected = {
        "/services/api-simulator/src/server.ts": "a16c6f606d78805ff887e2a5acbbbce8b8b2137d2dd9c0a2a24ba84c84a3fe6c",
        "/services/api-simulator/data/books_snapshot.json": "cd008d49b28c2217e1d27da22ab53db7a5a17433bf22684cf8b4112633774556",
    }

    for path, checksum in expected.items():
        assert _sha256(path) == checksum, f"Protected input changed: {path}"


def test_solver_input_surface_does_not_expose_incident_artifacts():
    assert not Path("/root/incident_ticket.md").exists()
    assert not Path("/root/session_replay_notes.md").exists()
    assert not Path("/root/console_excerpt.log").exists()
    assert not Path("/root/runtime_observations.md").exists()
    assert not Path("/root/quality_manifest.json").exists()
    assert not Path("/root/books_snapshot.json").exists()
    assert not Path("/root/upstream_source_notice.md").exists()
    assert not Path("/root/network_home.har").exists()
    assert not Path("/root/network_compare.har").exists()
    assert not Path("/root/trace_home.json").exists()
    assert not Path("/root/trace_compare.json").exists()


def test_repository_layout_does_not_use_generic_assets_bucket():
    repo_root = Path(__file__).resolve().parents[1]
    assert not (repo_root / "environment" / "assets").exists()
