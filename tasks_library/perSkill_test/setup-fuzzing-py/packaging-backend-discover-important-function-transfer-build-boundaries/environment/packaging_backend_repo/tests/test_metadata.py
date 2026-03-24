import pytest

from packager_backend.config import ConfigurationError
from packager_backend.metadata import coerce_dynamic_version, normalize_entry_points


def test_normalize_entry_points_sorts_each_group() -> None:
    normalized = normalize_entry_points(
        {
            "entry-points": {
                "console_scripts": {
                    "beta": "pkg.cli:beta",
                    "alpha": "pkg.cli:alpha",
                }
            }
        }
    )

    assert normalized["console_scripts"] == [
        "alpha = pkg.cli:alpha",
        "beta = pkg.cli:beta",
    ]


def test_normalize_entry_points_rejects_invalid_target() -> None:
    with pytest.raises(ConfigurationError):
        normalize_entry_points({"entry-points": {"console_scripts": {"tool": "pkg.cli"}}})


def test_coerce_dynamic_version_uses_suffix() -> None:
    version = coerce_dynamic_version(
        {"name": "demo", "dynamic": ["version"], "dynamic-version-base": "2.4.0"},
        "local123",
    )
    assert version == "2.4.0+local123"
