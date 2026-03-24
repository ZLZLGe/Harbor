#!/bin/bash
set -euo pipefail

APP_DIR="${APP_DIR:-/app}"

cat > "${APP_DIR}/build_boundary_report.json" <<'EOF'
{
  "repo_focus": {
    "repository": "/app/packaging_backend_repo",
    "summary": "This repository is a minimal Python packaging backend. The most fragile boundaries cluster around pyproject.toml loading, backend config normalization, entry-point metadata normalization, and the final assembly of build requests used by wheel and metadata hooks."
  },
  "important_files": [
    {
      "path": "packager_backend/config.py",
      "priority": "high",
      "reason": "It is the first boundary for malformed pyproject.toml data and frontend config_settings. It validates build-system identity and coerces several user-controlled backend options."
    },
    {
      "path": "packager_backend/build_backend.py",
      "priority": "high",
      "reason": "It merges pyproject data, backend config, editable flags, metadata paths, and wheel parameters into a single build request. Hook entry points depend on it directly."
    },
    {
      "path": "packager_backend/metadata.py",
      "priority": "medium",
      "reason": "It rewrites entry-point tables and dynamic version state, so malformed metadata can propagate into wheel names and dist-info directories."
    }
  ],
  "boundary_candidates": [
    {
      "qualname": "packager_backend.build_backend.collect_build_request",
      "file": "packager_backend/build_backend.py",
      "priority": 1,
      "build_stage": "request-assembly",
      "inputs": [
        "pyproject.toml content",
        "config_settings from the frontend",
        "metadata_directory",
        "editable flag",
        "wheel_directory"
      ],
      "failure_modes": [
        "malformed or missing build-system/project tables",
        "tool.packager-backend.local-version has the wrong type",
        "editable builds requested without editable in requested-targets",
        "unexpected interaction between config_settings and metadata normalization"
      ],
      "existing_test_refs": [
        "tests/test_backend.py::test_collect_build_request_reads_project_tables",
        "tests/test_backend.py::test_collect_build_request_rejects_editable_without_target"
      ],
      "why_it_matters": "This function sits on the build boundary where repository metadata and frontend parameters converge. A malformed pyproject.toml, backend table, or config_settings payload can all reach it before any artifact is produced.",
      "suggested_probes": [
        "truncated pyproject.toml sections",
        "tool.packager-backend values with nested tables or arrays instead of strings",
        "config_settings with mixed scalar and sequence requested-targets",
        "editable true combined with conflicting build targets"
      ]
    },
    {
      "qualname": "packager_backend.config.normalize_config_settings",
      "file": "packager_backend/config.py",
      "priority": 2,
      "build_stage": "frontend-config-normalization",
      "inputs": [
        "package-dir",
        "include-tests",
        "editable-mode",
        "tag-override",
        "requested-targets"
      ],
      "failure_modes": [
        "unexpected config_settings types",
        "empty strings or empty target lists",
        "unsupported target names",
        "boolean-like values passed as strings"
      ],
      "existing_test_refs": [
        "tests/test_config.py::test_normalize_config_settings_handles_sequence_targets",
        "tests/test_config.py::test_normalize_config_settings_rejects_unknown_target",
        "tests/test_backend.py::test_get_requires_for_build_wheel_adds_conditional_dependencies"
      ],
      "why_it_matters": "Frontends pass config_settings as loosely typed mappings, so this function is exposed to malformed backend configuration before later hooks can reject or sanitize it.",
      "suggested_probes": [
        "requested-targets passed as integers, tuples with duplicates, or empty lists",
        "include-tests set to strings such as true or yes",
        "tag-override passed as arrays or bytes",
        "editable-mode values outside compat/strict"
      ]
    },
    {
      "qualname": "packager_backend.config.load_pyproject",
      "file": "packager_backend/config.py",
      "priority": 3,
      "build_stage": "pyproject-load",
      "inputs": [
        "pyproject.toml bytes interpreted as UTF-8 text"
      ],
      "failure_modes": [
        "malformed TOML syntax",
        "missing build-system table",
        "unexpected build-backend value",
        "shape confusion between dict-like and non-dict values"
      ],
      "existing_test_refs": [
        "tests/test_config.py::test_load_pyproject_accepts_expected_backend"
      ],
      "why_it_matters": "Every backend hook depends on this parser. It is the earliest place where broken pyproject.toml structure can abort the build or surface inconsistent exceptions.",
      "suggested_probes": [
        "invalid TOML tokens",
        "duplicate sections",
        "build-system declared as strings or arrays",
        "non-UTF-8 or truncated file content"
      ]
    },
    {
      "qualname": "packager_backend.metadata.normalize_entry_points",
      "file": "packager_backend/metadata.py",
      "priority": 4,
      "build_stage": "metadata-normalization",
      "inputs": [
        "project.entry-points table"
      ],
      "failure_modes": [
        "entry-point groups stored as non-mappings",
        "missing module:function separators",
        "empty command names",
        "ordering-sensitive metadata differences"
      ],
      "existing_test_refs": [
        "tests/test_metadata.py::test_normalize_entry_points_sorts_each_group",
        "tests/test_metadata.py::test_normalize_entry_points_rejects_invalid_target",
        "tests/test_backend.py::test_collect_build_request_reads_project_tables"
      ],
      "why_it_matters": "Entry-point metadata is user-controlled project configuration that flows into build artifacts. Invalid project.entry-points content can trigger backend failures late in the build pipeline.",
      "suggested_probes": [
        "nested entry-point groups",
        "non-string command names",
        "targets without module:function syntax",
        "very large entry-point tables"
      ]
    },
    {
      "qualname": "packager_backend.metadata.coerce_dynamic_version",
      "file": "packager_backend/metadata.py",
      "priority": 5,
      "build_stage": "version-resolution",
      "inputs": [
        "project.version",
        "project.dynamic",
        "project.dynamic-version-base",
        "tool.packager-backend.local-version"
      ],
      "failure_modes": [
        "dynamic version declared without base version",
        "unexpected local-version types",
        "empty version strings",
        "version strings that flow into invalid wheel names"
      ],
      "existing_test_refs": [
        "tests/test_metadata.py::test_coerce_dynamic_version_uses_suffix",
        "tests/test_backend.py::test_prepare_metadata_for_build_wheel_formats_dist_info",
        "tests/test_backend.py::test_build_wheel_uses_tag_override"
      ],
      "why_it_matters": "Version resolution feeds both dist-info paths and wheel file names. Mis-normalized version metadata can break several hooks at once.",
      "suggested_probes": [
        "dynamic without version in the dynamic list",
        "empty dynamic-version-base",
        "local-version containing separators or whitespace",
        "project.version values that are not strings"
      ]
    }
  ],
  "existing_tests": {
    "covered_paths": [
      "tests/test_config.py covers the happy path for load_pyproject and several normalize_config_settings branches.",
      "tests/test_metadata.py covers entry-point sorting, one invalid entry-point target, and a dynamic version suffix case.",
      "tests/test_backend.py covers build request assembly, editable target validation, metadata naming, wheel tag override, and conditional dependency calculation."
    ],
    "gaps": [
      "No test exercises malformed pyproject.toml syntax, truncated files, or non-UTF-8 content.",
      "There is no coverage for tool.packager-backend being present with the wrong table shape or for local-version using non-string types.",
      "config_settings is only tested with clean booleans and simple lists, not with frontend-style mixed scalar payloads.",
      "The hooks are not stressed with unusual metadata_directory or wheel_directory values, conflicting requested-target combinations, or oversized entry-point tables."
    ]
  },
  "top_priorities": [
    {
      "qualname": "packager_backend.build_backend.collect_build_request",
      "priority": 1,
      "why_priority_is_high": "It combines pyproject.toml parsing, backend table extraction, config normalization, version coercion, entry-point shaping, and editable-build policy in one place.",
      "current_gap": "Existing tests only cover one well-formed project and a single editable error. They do not explore malformed backend tables, incompatible config_settings shapes, or mixed failure causes.",
      "input_directions": [
        "mutate build-system and tool.packager-backend tables together",
        "vary editable flag and requested-targets combinations",
        "inject malformed entry-points and dynamic version metadata in the same file"
      ]
    },
    {
      "qualname": "packager_backend.config.normalize_config_settings",
      "priority": 2,
      "why_priority_is_high": "Build frontends often pass loosely typed config_settings mappings, so this function is an exposed coercion boundary with multiple type-sensitive branches.",
      "current_gap": "Tests do not cover stringified booleans, empty package-dir values, duplicated targets, numeric tag overrides, or foreign container types.",
      "input_directions": [
        "mix scalars, lists, tuples, and unexpected mapping values",
        "exercise empty and duplicate requested-targets",
        "probe invalid editable-mode values together with strict mode dependency resolution"
      ]
    },
    {
      "qualname": "packager_backend.config.load_pyproject",
      "priority": 3,
      "why_priority_is_high": "It is the first parser boundary for pyproject.toml and determines whether later build hooks operate on trusted structure.",
      "current_gap": "Coverage only proves the accepted path. It does not check malformed TOML, missing build-system, alternate build-backend strings, or corrupted text encodings.",
      "input_directions": [
        "mutate section headers and key-value delimiters",
        "remove required build-system fields",
        "supply unexpected scalar types for build-system entries"
      ]
    }
  ]
}
EOF
