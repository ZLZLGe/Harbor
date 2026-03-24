# packaging-backend-repo

This repository contains a minimal Python packaging backend used for build-planning experiments.
The code intentionally concentrates around `pyproject.toml` parsing, backend option normalization,
entry-point metadata shaping, and build request assembly.

The tests focus on happy paths plus a few selected validation checks.
They do not try to exhaust malformed TOML, conflicting config settings, or unusual build parameter combinations.
