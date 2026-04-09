import hashlib
from pathlib import Path


def _sha256(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_hidden_dashboard_simulator_not_modified():
    expected = {
        "/services/api-simulator/src/server.ts": "a169c7dc10af41b2c28754c2fdbb4cdd60f84bfcc57e88d85aae258348901292",
        "/services/api-simulator/data/analytics_snapshot.json": "62182698bee81e108ca755692aad00e6514f7b86d9d22be60d0102059a3b7693",
    }

    for path, checksum in expected.items():
        assert _sha256(path) == checksum, f"Protected input changed: {path}"


def test_solver_input_surface_does_not_expose_incident_artifacts():
    assert not Path("/root/incident_ticket.md").exists()
    assert not Path("/root/session_replay_notes.md").exists()
    assert not Path("/root/console_excerpt.log").exists()
    assert not Path("/root/runtime_observations.md").exists()
    assert not Path("/root/quality_manifest.json").exists()
    assert not Path("/root/analytics_snapshot.json").exists()
    assert not Path("/root/upstream_source_notice.md").exists()
    assert not Path("/root/network_home.har").exists()
    assert not Path("/root/network_compare.har").exists()
    assert not Path("/root/trace_home.json").exists()
    assert not Path("/root/trace_compare.json").exists()


def test_repository_layout_does_not_use_generic_assets_bucket():
    repo_root = Path(__file__).resolve().parents[1]
    assert not (repo_root / "environment" / "assets").exists()
