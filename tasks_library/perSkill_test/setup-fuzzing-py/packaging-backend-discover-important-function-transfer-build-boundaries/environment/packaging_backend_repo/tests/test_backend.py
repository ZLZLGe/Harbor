from pathlib import Path

import pytest

from packager_backend.build_backend import build_wheel, collect_build_request, get_requires_for_build_wheel, prepare_metadata_for_build_wheel
from packager_backend.config import ConfigurationError


def _write_pyproject(path: Path) -> None:
    path.write_text(
        """
[build-system]
requires = []
build-backend = "packager_backend.build_backend"

[project]
name = "demo-app"
dynamic = ["version"]
dynamic-version-base = "1.2.3"

[project.entry-points.console_scripts]
demo = "demo.cli:main"

[tool.packager-backend]
local-version = "nightly"
""".strip(),
        encoding="utf-8",
    )


def test_collect_build_request_reads_project_tables(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_pyproject(tmp_path / "pyproject.toml")
    monkeypatch.chdir(tmp_path)

    request = collect_build_request(
        pyproject_path=tmp_path / "pyproject.toml",
        wheel_directory=tmp_path / "dist",
        metadata_directory=tmp_path / "meta",
        config_settings={"requested-targets": ["wheel", "editable"], "editable-mode": "strict"},
        editable=True,
    )

    assert request["version"] == "1.2.3+nightly"
    assert request["entry_points"]["console_scripts"] == ["demo = demo.cli:main"]


def test_prepare_metadata_for_build_wheel_formats_dist_info(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_pyproject(tmp_path / "pyproject.toml")
    monkeypatch.chdir(tmp_path)

    dist_info = prepare_metadata_for_build_wheel("meta")
    assert dist_info == "demo-app-1.2.3+nightly.dist-info"


def test_build_wheel_uses_tag_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_pyproject(tmp_path / "pyproject.toml")
    monkeypatch.chdir(tmp_path)

    wheel_name = build_wheel("dist", {"tag-override": "py312-manylinux_x86_64"})
    assert wheel_name == "demo_app-1.2.3+nightly-py312-manylinux_x86_64.whl"


def test_collect_build_request_rejects_editable_without_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_pyproject(tmp_path / "pyproject.toml")
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ConfigurationError):
        collect_build_request(
            pyproject_path=tmp_path / "pyproject.toml",
            wheel_directory=tmp_path / "dist",
            metadata_directory=None,
            config_settings={"requested-targets": ["wheel"]},
            editable=True,
        )


def test_get_requires_for_build_wheel_adds_conditional_dependencies() -> None:
    requirements = get_requires_for_build_wheel({"include-tests": True, "editable-mode": "strict"})
    assert requirements == ["pytest>=8", "editables>=0.5"]
