from __future__ import annotations

from typing import Any, Mapping

from .config import ConfigurationError


def normalize_entry_points(project_table: Mapping[str, Any]) -> dict[str, list[str]]:
    """Normalize project.entry-points into sorted lists of entry definitions."""
    entry_points = project_table.get("entry-points", {})
    if not isinstance(entry_points, Mapping):
        raise ConfigurationError("project.entry-points must be a table")

    normalized: dict[str, list[str]] = {}
    for group_name, group_entries in entry_points.items():
        if not isinstance(group_entries, Mapping):
            raise ConfigurationError(f"entry point group {group_name!r} must be a table")

        rendered: list[str] = []
        for command_name, target in group_entries.items():
            if not isinstance(command_name, str) or not command_name:
                raise ConfigurationError("entry point command names must be non-empty strings")
            if not isinstance(target, str) or ":" not in target:
                raise ConfigurationError(f"entry point target for {command_name!r} is invalid")
            rendered.append(f"{command_name} = {target}")

        normalized[str(group_name)] = sorted(rendered)

    return normalized


def coerce_dynamic_version(project_table: Mapping[str, Any], local_suffix: str | None) -> str:
    """Resolve either a static version or a dynamic version template."""
    version = project_table.get("version")
    if isinstance(version, str) and version:
        return version

    dynamic = project_table.get("dynamic", [])
    if "version" not in dynamic:
        raise ConfigurationError("project.version is missing and not declared dynamic")

    base_version = project_table.get("dynamic-version-base")
    if not isinstance(base_version, str) or not base_version:
        raise ConfigurationError("dynamic-version-base must be provided for dynamic versions")

    if local_suffix:
        return f"{base_version}+{local_suffix}"
    return base_version
