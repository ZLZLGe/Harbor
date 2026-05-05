#!/usr/bin/env bash
set -euo pipefail

app_root="${TASK_APP_ROOT:-/app}"
task_root="$app_root/workspace"
solution_root="$app_root/solution/fixed"

rm -rf "$task_root/chart" "$task_root/releases"
mkdir -p "$task_root/chart" "$task_root/releases"

cp -R "$solution_root/chart/." "$task_root/chart/"
cp -R "$solution_root/releases/." "$task_root/releases/"

chmod +x "$task_root/scripts/render_release.sh"
