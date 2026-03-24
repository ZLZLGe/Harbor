from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .config import BackendOptions, ConfigurationError, extract_backend_table, load_pyproject, normalize_config_settings
from .metadata import coerce_dynamic_version, normalize_entry_points


def collect_build_request(
    pyproject_path: Path,
    wheel_directory: Path,
    config_settings: Mapping[str, object] | None,
    metadata_directory: Path | None = None,
    editable: bool = False,
) -> dict[str, Any]:
    """Gather normalized project metadata and build settings before writing artifacts."""
    document = load_pyproject(pyproject_path)
    project_table = document.get("project", {})
    if not isinstance(project_table, Mapping):
        raise ConfigurationError("project table must be present")

    backend_table = extract_backend_table(document)
    options = normalize_config_settings(config_settings)

    local_suffix = backend_table.get("local-version")
    if local_suffix is not None and not isinstance(local_suffix, str):
        raise ConfigurationError("tool.packager-backend.local-version must be a string")

    version = coerce_dynamic_version(project_table, local_suffix)
    entry_points = normalize_entry_points(project_table)

    if editable and "editable" not in options.requested_targets:
        raise ConfigurationError("editable builds require the editable target to be requested")

    return {
        "name": project_table.get("name"),
        "version": version,
        "package_dir": options.package_dir,
        "include_tests": options.include_tests,
        "editable_mode": options.editable_mode,
        "tag_override": options.tag_override,
        "requested_targets": list(options.requested_targets),
        "entry_points": entry_points,
        "wheel_directory": str(wheel_directory),
        "metadata_directory": str(metadata_directory) if metadata_directory else None,
    }


def prepare_metadata_for_build_wheel(
    metadata_directory: str,
    config_settings: Mapping[str, object] | None = None,
) -> str:
    """Prepare metadata and return the dist-info directory name."""
    request = collect_build_request(
        pyproject_path=Path("pyproject.toml"),
        wheel_directory=Path("."),
        metadata_directory=Path(metadata_directory),
        config_settings=config_settings,
    )
    name = request["name"]
    version = request["version"]
    if not isinstance(name, str) or not isinstance(version, str):
        raise ConfigurationError("name and version must resolve to strings")
    return f"{name}-{version}.dist-info"


def build_wheel(
    wheel_directory: str,
    config_settings: Mapping[str, object] | None = None,
    metadata_directory: str | None = None,
) -> str:
    """Create a deterministic wheel file name from the normalized request."""
    request = collect_build_request(
        pyproject_path=Path("pyproject.toml"),
        wheel_directory=Path(wheel_directory),
        metadata_directory=Path(metadata_directory) if metadata_directory else None,
        config_settings=config_settings,
    )
    name = str(request["name"]).replace("-", "_")
    version = str(request["version"]).replace("-", "_")
    tag = request["tag_override"] or "py3-none-any"
    return f"{name}-{version}-{tag}.whl"


def get_requires_for_build_wheel(config_settings: Mapping[str, object] | None = None) -> list[str]:
    """Return conditional backend requirements derived from config settings."""
    options: BackendOptions = normalize_config_settings(config_settings)
    requirements: list[str] = []
    if options.include_tests:
        requirements.append("pytest>=8")
    if options.editable_mode == "strict":
        requirements.append("editables>=0.5")
    return requirements
