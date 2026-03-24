from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
import tomllib


class ConfigurationError(ValueError):
    """Raised when pyproject data or build settings are invalid."""


@dataclass
class BackendOptions:
    package_dir: str
    include_tests: bool
    editable_mode: str
    tag_override: str | None
    requested_targets: tuple[str, ...]


def load_pyproject(pyproject_path: Path) -> dict[str, Any]:
    """Load pyproject.toml and enforce the build backend table shape."""
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    build_system = data.get("build-system")
    if not isinstance(build_system, dict):
        raise ConfigurationError("build-system table is required")

    backend = build_system.get("build-backend")
    if backend != "packager_backend.build_backend":
        raise ConfigurationError(f"unexpected build backend: {backend!r}")

    return data


def extract_backend_table(document: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return the backend config table from tool.packager-backend."""
    tool_table = document.get("tool", {})
    if not isinstance(tool_table, Mapping):
        raise ConfigurationError("tool table must be a mapping")

    backend_table = tool_table.get("packager-backend", {})
    if not isinstance(backend_table, Mapping):
        raise ConfigurationError("tool.packager-backend must be a table")

    return backend_table


def normalize_config_settings(config_settings: Mapping[str, object] | None) -> BackendOptions:
    """Normalize config settings passed by build frontends."""
    settings = dict(config_settings or {})

    package_dir = settings.get("package-dir", "src")
    if not isinstance(package_dir, str) or not package_dir:
        raise ConfigurationError("package-dir must be a non-empty string")

    include_tests = settings.get("include-tests", False)
    if not isinstance(include_tests, bool):
        raise ConfigurationError("include-tests must be a boolean")

    editable_mode = settings.get("editable-mode", "compat")
    if editable_mode not in {"compat", "strict"}:
        raise ConfigurationError("editable-mode must be compat or strict")

    tag_override = settings.get("tag-override")
    if tag_override is not None and not isinstance(tag_override, str):
        raise ConfigurationError("tag-override must be a string when provided")

    requested_targets_raw = settings.get("requested-targets", ("wheel",))
    if isinstance(requested_targets_raw, str):
        requested_targets = (requested_targets_raw,)
    elif isinstance(requested_targets_raw, (list, tuple)):
        requested_targets = tuple(requested_targets_raw)
    else:
        raise ConfigurationError("requested-targets must be a string or sequence")

    if not requested_targets:
        raise ConfigurationError("requested-targets cannot be empty")

    for target in requested_targets:
        if target not in {"wheel", "sdist", "editable"}:
            raise ConfigurationError(f"unknown build target: {target!r}")

    return BackendOptions(
        package_dir=package_dir,
        include_tests=include_tests,
        editable_mode=editable_mode,
        tag_override=tag_override,
        requested_targets=tuple(str(target) for target in requested_targets),
    )
