from pathlib import Path

import pytest

from packager_backend.config import ConfigurationError, extract_backend_table, load_pyproject, normalize_config_settings


def test_load_pyproject_accepts_expected_backend(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[build-system]
requires = []
build-backend = "packager_backend.build_backend"

[project]
name = "demo"
version = "1.0.0"
""".strip(),
        encoding="utf-8",
    )

    document = load_pyproject(pyproject)
    assert document["project"]["name"] == "demo"


def test_extract_backend_table_defaults_when_missing() -> None:
    table = extract_backend_table({"tool": {}})
    assert table == {}


def test_normalize_config_settings_handles_sequence_targets() -> None:
    options = normalize_config_settings(
        {
            "package-dir": "lib",
            "include-tests": True,
            "editable-mode": "strict",
            "requested-targets": ["wheel", "editable"],
        }
    )

    assert options.package_dir == "lib"
    assert options.include_tests is True
    assert options.requested_targets == ("wheel", "editable")


def test_normalize_config_settings_rejects_unknown_target() -> None:
    with pytest.raises(ConfigurationError):
        normalize_config_settings({"requested-targets": ["wheel", "zipapp"]})
