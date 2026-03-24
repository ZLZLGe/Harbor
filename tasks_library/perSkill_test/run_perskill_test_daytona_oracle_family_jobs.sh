#!/usr/bin/env bash
set -euo pipefail

export LC_ALL=C

REPO_ROOT="/home/levi/Harbor"
SOURCE_ROOT="$REPO_ROOT/tasks_library/perSkill_test"
JOBS_ROOT_BASE="$SOURCE_ROOT/jobs"

AGENT_NAME="${AGENT_NAME:-oracle}"
ENV_NAME="${ENV_NAME:-daytona}"
BATCH_NAME="${BATCH_NAME:-perSkill-test-daytona-oracle-family-$(date +%Y%m%d-%H%M%S)}"
START_FAMILY="${START_FAMILY:-}"
N_FAMILIES="${N_FAMILIES:-}"
N_CONCURRENT="${N_CONCURRENT:-2}"
MAX_MEMORY_MB="${MAX_MEMORY_MB:-4096}"
MAX_STORAGE_MB="${MAX_STORAGE_MB:-10240}"
DRY_RUN="${DRY_RUN:-0}"

HARBOR_DEFAULT_MEMORY_MB=2048
HARBOR_DEFAULT_STORAGE_MB=10240

JOBS_BATCH_ROOT=""
REPORTS_DIR=""
FAMILY_RUNS_TSV=""
SKIPPED_RESOURCE_LIMITS_TSV=""
CLASSIFICATION_TSV=""
SUMMARY_JSON=""

declare -a HARBOR_ARGS=()
declare -a FAMILY_NAMES=()
declare -a FAMILY_DIRS=()

usage() {
  cat <<'EOF'
Usage:
  bash /home/levi/Harbor/tasks_library/perSkill_test/run_perskill_test_daytona_oracle_family_jobs.sh [options] [-- <extra harbor args>]

Purpose:
  Run Harbor oracle validation family-by-family for:
    /home/levi/Harbor/tasks_library/perSkill_test

  Each family is run as its own Harbor dataset:
    harbor run -p <family_dir> -a oracle -e daytona ...

  Harbor jobs are written under:
    /home/levi/Harbor/tasks_library/perSkill_test/jobs/<batch-name>/<family-name>

  Batch reports are written under:
    /home/levi/Harbor/tasks_library/perSkill_test/jobs/<batch-name>/reports

Options:
  --start-family <NAME>       Start from this exact family name.
  --n-families <N>            Only select the first N families by order.
  --n-concurrent <N>          Daytona concurrency passed to harbor run.
  --max-memory-mb <N>         Skip tasks with effective memory above this limit.
  --max-storage-mb <N>        Skip tasks with effective storage above this limit.
  --batch-name <NAME>         Batch name.
  --job-name <NAME>           Alias of --batch-name.
  --dry-run                   Print selected families and commands without running Harbor.
  --help, -h                  Show this help message.

Environment defaults:
  AGENT_NAME=oracle
  ENV_NAME=daytona
  BATCH_NAME=perSkill-test-daytona-oracle-family-<timestamp>
  START_FAMILY=<from first family>
  N_FAMILIES=<all selected families>
  N_CONCURRENT=2
  MAX_MEMORY_MB=4096
  MAX_STORAGE_MB=10240
  DRY_RUN=0
EOF
}

die() {
  echo "Error: $*" >&2
  exit 1
}

require_value() {
  local flag="$1"
  local value="${2-}"
  [[ -n "$value" ]] || die "Missing value after $flag"
}

is_positive_integer() {
  [[ "$1" =~ ^[1-9][0-9]*$ ]]
}

collect_task_names() {
  local family_dir="$1"
  local -n out_names="$2"

  out_names=()
  while IFS= read -r -d '' child_dir; do
    if [[ -f "$child_dir/task.toml" ]]; then
      out_names+=("$(basename "$child_dir")")
    fi
  done < <(find "$family_dir" -mindepth 1 -maxdepth 1 -type d -print0 | sort -z)
}

append_families() {
  local root="$1"
  local start_family="${2-}"
  local start_matched=0

  [[ -d "$root" ]] || die "Input root does not exist: $root"

  while IFS= read -r -d '' family_dir; do
    local family_name task_names=()
    family_name="$(basename "$family_dir")"

    if [[ "$family_name" == "jobs" ]]; then
      continue
    fi

    if [[ -n "$start_family" && "$start_matched" -eq 0 ]]; then
      if [[ "$family_name" == "$start_family" ]]; then
        start_matched=1
      else
        continue
      fi
    fi

    collect_task_names "$family_dir" task_names
    if [[ "${#task_names[@]}" -eq 0 ]]; then
      die "No task directories with task.toml found under family: $family_dir"
    fi

    FAMILY_NAMES+=("$family_name")
    FAMILY_DIRS+=("$family_dir")
  done < <(find "$root" -mindepth 1 -maxdepth 1 -type d -print0 | sort -z)

  if [[ -n "$start_family" && "$start_matched" -eq 0 ]]; then
    die "Start family not found under $root: $start_family"
  fi
}

print_command() {
  local -n cmd_ref="$1"
  for arg in "${cmd_ref[@]}"; do
    printf ' %q' "$arg"
  done
  printf '\n'
}

compute_family_task_sets() {
  local family_dir="$1"
  local -n out_all="$2"
  local -n out_resource_limited="$3"
  local -n out_run="$4"
  local -n out_resource_memory="$5"
  local -n out_resource_storage="$6"
  local -n out_resource_reason="$7"
  local task_report

  task_report="$(
    python3 - \
      "$family_dir" \
      "$MAX_MEMORY_MB" \
      "$MAX_STORAGE_MB" \
      "$HARBOR_DEFAULT_MEMORY_MB" \
      "$HARBOR_DEFAULT_STORAGE_MB" <<'PY'
import math
import sys
import tomllib
from pathlib import Path

family_dir = Path(sys.argv[1])
max_memory_mb = int(sys.argv[2])
max_storage_mb = int(sys.argv[3])
default_memory_mb = int(sys.argv[4])
default_storage_mb = int(sys.argv[5])


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def parse_size_to_mb(value, field_name: str, task_file: Path) -> int:
    if isinstance(value, bool):
        fail(f"Invalid boolean for {field_name} in {task_file}")

    if isinstance(value, (int, float)):
        numeric_value = float(value)
        if not math.isfinite(numeric_value) or numeric_value < 0:
            fail(f"Invalid numeric value for {field_name} in {task_file}: {value!r}")
        return int(numeric_value)

    if isinstance(value, str):
        size_str = value.strip().upper()
        if not size_str:
            fail(f"Empty string for {field_name} in {task_file}")

        try:
            if size_str.endswith("G"):
                return int(float(size_str[:-1]) * 1024)
            if size_str.endswith("M"):
                return int(float(size_str[:-1]))
            if size_str.endswith("K"):
                return int(float(size_str[:-1]) / 1024)
        except ValueError:
            fail(f"Invalid size format for {field_name} in {task_file}: {value!r}")

        fail(
            f"Invalid size unit for {field_name} in {task_file}: {value!r}. "
            "Expected suffix K, M, or G."
        )

    fail(f"Unsupported value for {field_name} in {task_file}: {value!r}")


def resolve_effective_mb(env: dict, mb_field: str, legacy_field: str, default_mb: int, task_file: Path) -> int:
    if mb_field in env and env[mb_field] is not None:
        return parse_size_to_mb(env[mb_field], mb_field, task_file)
    if legacy_field in env and env[legacy_field] is not None:
        return parse_size_to_mb(env[legacy_field], legacy_field, task_file)
    return default_mb


for task_dir in sorted(path for path in family_dir.iterdir() if path.is_dir()):
    task_file = task_dir / "task.toml"
    if not task_file.is_file():
        continue

    with open(task_file, "rb") as handle:
        data = tomllib.load(handle)

    env = data.get("environment", {})
    if not isinstance(env, dict):
        fail(f"Expected [environment] table in {task_file}")

    memory_mb = resolve_effective_mb(env, "memory_mb", "memory", default_memory_mb, task_file)
    storage_mb = resolve_effective_mb(env, "storage_mb", "storage", default_storage_mb, task_file)

    over_memory = memory_mb > max_memory_mb
    over_storage = storage_mb > max_storage_mb
    if over_memory and over_storage:
        limit_reason = "memory_and_storage_limit_exceeded"
    elif over_memory:
        limit_reason = "memory_limit_exceeded"
    elif over_storage:
        limit_reason = "storage_limit_exceeded"
    else:
        limit_reason = ""

    print(f"{task_dir.name}\t{memory_mb}\t{storage_mb}\t{limit_reason}")
PY
  )" || die "Failed to parse task resources for family: $family_dir"

  out_all=()
  out_resource_limited=()
  out_run=()
  out_resource_memory=()
  out_resource_storage=()
  out_resource_reason=()

  if [[ -z "$task_report" ]]; then
    return
  fi

  while IFS=$'\t' read -r task_name effective_memory_mb effective_storage_mb limit_reason; do
    [[ -n "$task_name" ]] || continue

    out_all+=("$task_name")

    if [[ -n "$limit_reason" ]]; then
      out_resource_limited+=("$task_name")
      out_resource_memory["$task_name"]="$effective_memory_mb"
      out_resource_storage["$task_name"]="$effective_storage_mb"
      out_resource_reason["$task_name"]="$limit_reason"
    else
      out_run+=("$task_name")
    fi
  done <<< "$task_report"
}

append_skipped_resource_rows() {
  local family_name="$1"
  local family_dir="$2"
  local -n resource_limited_ref="$3"
  local -n resource_memory_ref="$4"
  local -n resource_storage_ref="$5"
  local -n resource_reason_ref="$6"

  for task_name in "${resource_limited_ref[@]}"; do
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
      "$family_name" \
      "$task_name" \
      "$family_dir/$task_name" \
      "${resource_memory_ref[$task_name]}" \
      "${resource_storage_ref[$task_name]}" \
      "${resource_reason_ref[$task_name]}" >> "$SKIPPED_RESOURCE_LIMITS_TSV"
  done
}

append_family_run_row() {
  local family_name="$1"
  local family_dir="$2"
  local jobs_root="$3"
  local family_job_dir="$4"
  local total_count="$5"
  local skipped_resource_count="$6"
  local run_count="$7"
  local status="$8"
  local harbor_exit_code="$9"

  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$family_name" \
    "$family_dir" \
    "$jobs_root" \
    "$family_job_dir" \
    "$total_count" \
    "$skipped_resource_count" \
    "$run_count" \
    "$status" \
    "$harbor_exit_code" >> "$FAMILY_RUNS_TSV"
}

analyze_family_results() {
  local family_name="$1"
  local family_dir="$2"
  local family_job_dir="$3"
  local harbor_exit_code="$4"
  shift 4
  local -a task_names=("$@")

  if [[ "${#task_names[@]}" -eq 0 ]]; then
    return
  fi

  python3 - \
    "$CLASSIFICATION_TSV" \
    "$family_name" \
    "$family_dir" \
    "$family_job_dir" \
    "$harbor_exit_code" \
    "${task_names[@]}" <<'PY'
import csv
import json
import math
import sys
from collections import Counter
from pathlib import Path

classification_path, family_name, family_dir, family_job_dir, harbor_exit_code, *selected_task_names = sys.argv[1:]
family_dir = Path(family_dir)
family_job_dir = Path(family_job_dir)
harbor_exit_code = int(harbor_exit_code)


def sanitize_tsv(value):
    if value is None:
        return ""
    return str(value).replace("\t", " ").replace("\r", " ").replace("\n", " ")


def parse_reward(payload):
    verifier_result = payload.get("verifier_result")
    if not isinstance(verifier_result, dict):
        return None
    rewards = verifier_result.get("rewards")
    if not isinstance(rewards, dict):
        return None
    reward = rewards.get("reward")
    if isinstance(reward, bool):
        return None
    if isinstance(reward, (int, float)):
        reward = float(reward)
    elif isinstance(reward, str):
        try:
            reward = float(reward)
        except ValueError:
            return None
    else:
        return None
    return reward if math.isfinite(reward) else None


selected_tasks = {
    task_name: family_dir / task_name
    for task_name in selected_task_names
}

if not selected_tasks:
    raise SystemExit(0)

family_task_dirs = {
    path.name: path
    for path in family_dir.iterdir()
    if path.is_dir() and (path / "task.toml").is_file()
}

candidates = {}
duplicate_counts = Counter()

if family_job_dir.is_dir():
    for trial_dir in sorted(path for path in family_job_dir.iterdir() if path.is_dir()):
        result_path = trial_dir / "result.json"
        if not result_path.is_file():
            continue

        try:
            payload = json.loads(result_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        task_name = payload.get("task_name")
        if not isinstance(task_name, str) or not task_name:
            continue
        if task_name not in family_task_dirs:
            continue
        if task_name not in selected_tasks:
            continue

        duplicate_counts[task_name] += 1
        candidate = {
            "trial_dir": trial_dir,
            "result_path": result_path,
            "payload": payload,
            "mtime": result_path.stat().st_mtime,
        }
        existing = candidates.get(task_name)
        if existing is None or candidate["mtime"] >= existing["mtime"]:
            candidates[task_name] = candidate

classification_rows = []

for task_name in sorted(selected_tasks):
    task_dir = selected_tasks[task_name]
    candidate = candidates.get(task_name)

    bucket = "fail"
    reward_text = ""
    exception_type = ""
    failure_reason = ""
    parse_error = ""
    trial_result_path = ""
    trial_dir = ""
    trial_result_count = duplicate_counts.get(task_name, 0)

    if candidate is None:
        failure_reason = "missing_result"
    else:
        trial_result_path = str(candidate["result_path"])
        trial_dir = str(candidate["trial_dir"])
        payload = candidate["payload"]

        result_task_name = payload.get("task_name")
        if not isinstance(result_task_name, str) or not result_task_name:
            failure_reason = "missing_task_name"
        elif result_task_name not in family_task_dirs:
            failure_reason = "task_name_not_found_in_family"
        else:
            exception_info = payload.get("exception_info")
            if exception_info is not None:
                failure_reason = "exception"
                if isinstance(exception_info, dict) and isinstance(exception_info.get("exception_type"), str):
                    exception_type = exception_info["exception_type"]
            else:
                reward = parse_reward(payload)
                if reward is None:
                    failure_reason = "missing_reward"
                else:
                    reward_text = f"{reward:g}"
                    if reward == 1.0:
                        bucket = "pass"
                    else:
                        failure_reason = "reward_not_one"

    classification_rows.append(
        [
            sanitize_tsv(family_name),
            sanitize_tsv(task_name),
            sanitize_tsv(bucket),
            sanitize_tsv(reward_text),
            sanitize_tsv(exception_type),
            sanitize_tsv(failure_reason),
            sanitize_tsv(parse_error),
            sanitize_tsv(trial_result_path),
            sanitize_tsv(trial_dir),
            sanitize_tsv(task_dir),
            sanitize_tsv(trial_result_count),
            sanitize_tsv(harbor_exit_code),
            sanitize_tsv(family_job_dir),
        ]
    )

with open(classification_path, "a", encoding="utf-8", newline="") as handle:
    writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
    writer.writerows(classification_rows)
PY
}

write_summary() {
  python3 - \
    "$FAMILY_RUNS_TSV" \
    "$CLASSIFICATION_TSV" \
    "$SKIPPED_RESOURCE_LIMITS_TSV" \
    "$SUMMARY_JSON" \
    "$BATCH_NAME" \
    "$SOURCE_ROOT" \
    "$JOBS_BATCH_ROOT" \
    "$N_CONCURRENT" \
    "$MAX_MEMORY_MB" \
    "$MAX_STORAGE_MB" \
    "$START_FAMILY" <<'PY'
import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone

(
    family_runs_path,
    classification_path,
    skipped_resource_limits_path,
    summary_path,
    batch_name,
    source_root,
    jobs_root,
    n_concurrent,
    max_memory_mb,
    max_storage_mb,
    start_family,
) = sys.argv[1:]

with open(family_runs_path, "r", encoding="utf-8", newline="") as handle:
    family_runs = list(csv.DictReader(handle, delimiter="\t"))

with open(classification_path, "r", encoding="utf-8", newline="") as handle:
    classification_rows = list(csv.DictReader(handle, delimiter="\t"))

with open(skipped_resource_limits_path, "r", encoding="utf-8", newline="") as handle:
    skipped_resource_limit_rows = list(csv.DictReader(handle, delimiter="\t"))

family_status_counts = Counter(row["status"] for row in family_runs)
selected_task_count = sum(int(row["total_task_count"]) for row in family_runs)
run_task_count = sum(int(row["run_task_count"]) for row in family_runs)
bucket_counts = Counter(row["bucket"] for row in classification_rows)
failure_reason_counts = Counter(
    row["failure_reason"] for row in classification_rows if row["bucket"] == "fail"
)
resource_limit_reason_counts = Counter(
    row["reason"] for row in skipped_resource_limit_rows
)
family_harbor_failure_count = sum(
    1 for row in family_runs
    if row["status"] == "ran" and int(row["harbor_exit_code"]) != 0
)

summary = {
    "batch_name": batch_name,
    "source_root": source_root,
    "jobs_root": jobs_root,
    "daytona_concurrency": int(n_concurrent),
    "max_memory_mb": int(max_memory_mb),
    "max_storage_mb": int(max_storage_mb),
    "start_family": start_family,
    "selected_family_count": len(family_runs),
    "run_family_count": family_status_counts.get("ran", 0),
    "skipped_no_eligible_tasks_family_count": family_status_counts.get("skipped_no_eligible_tasks", 0),
    "selected_task_count": selected_task_count,
    "run_task_count": run_task_count,
    "skipped_resource_limit_task_count": len(skipped_resource_limit_rows),
    "pass_count": bucket_counts.get("pass", 0),
    "fail_count": bucket_counts.get("fail", 0),
    "failure_reason_counts": dict(failure_reason_counts),
    "resource_limit_reason_counts": dict(resource_limit_reason_counts),
    "family_harbor_failure_count": family_harbor_failure_count,
    "generated_at": datetime.now(timezone.utc).isoformat(),
}

with open(summary_path, "w", encoding="utf-8") as handle:
    json.dump(summary, handle, indent=2, sort_keys=True)
    handle.write("\n")
PY
}

while (($# > 0)); do
  case "$1" in
    --start-family)
      require_value "$1" "${2-}"
      START_FAMILY="$2"
      shift 2
      ;;
    --n-families)
      require_value "$1" "${2-}"
      N_FAMILIES="$2"
      shift 2
      ;;
    --n-concurrent)
      require_value "$1" "${2-}"
      N_CONCURRENT="$2"
      shift 2
      ;;
    --max-memory-mb)
      require_value "$1" "${2-}"
      MAX_MEMORY_MB="$2"
      shift 2
      ;;
    --max-storage-mb)
      require_value "$1" "${2-}"
      MAX_STORAGE_MB="$2"
      shift 2
      ;;
    --batch-name|--job-name)
      require_value "$1" "${2-}"
      BATCH_NAME="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    --)
      shift
      HARBOR_ARGS=("$@")
      break
      ;;
    *)
      die "Unknown argument: $1"
      ;;
  esac
done

if [[ -n "$N_FAMILIES" ]] && ! is_positive_integer "$N_FAMILIES"; then
  die "--n-families must be a positive integer"
fi

is_positive_integer "$N_CONCURRENT" || die "--n-concurrent must be a positive integer"
is_positive_integer "$MAX_MEMORY_MB" || die "--max-memory-mb must be a positive integer"
is_positive_integer "$MAX_STORAGE_MB" || die "--max-storage-mb must be a positive integer"
[[ "$DRY_RUN" == "0" || "$DRY_RUN" == "1" ]] || die "DRY_RUN must be 0 or 1"

[[ -d "$SOURCE_ROOT" ]] || die "Source root does not exist: $SOURCE_ROOT"
command -v python3 >/dev/null 2>&1 || die "python3 is not available in PATH"
command -v harbor >/dev/null 2>&1 || die "harbor is not available in PATH"

JOBS_BATCH_ROOT="$JOBS_ROOT_BASE/$BATCH_NAME"
REPORTS_DIR="$JOBS_BATCH_ROOT/reports"
FAMILY_RUNS_TSV="$REPORTS_DIR/family_runs.tsv"
SKIPPED_RESOURCE_LIMITS_TSV="$REPORTS_DIR/skipped_resource_limits.tsv"
CLASSIFICATION_TSV="$REPORTS_DIR/classification.tsv"
SUMMARY_JSON="$REPORTS_DIR/summary.json"

[[ ! -e "$JOBS_BATCH_ROOT" ]] || die "Target batch output already exists: $JOBS_BATCH_ROOT"

append_families "$SOURCE_ROOT" "$START_FAMILY"

family_count="${#FAMILY_DIRS[@]}"
[[ "$family_count" -gt 0 ]] || die "No families were selected"

if [[ -n "$N_FAMILIES" && "$family_count" -gt "$N_FAMILIES" ]]; then
  FAMILY_NAMES=("${FAMILY_NAMES[@]:0:$N_FAMILIES}")
  FAMILY_DIRS=("${FAMILY_DIRS[@]:0:$N_FAMILIES}")
  family_count="${#FAMILY_DIRS[@]}"
fi

echo "Batch name: $BATCH_NAME"
echo "Source root: $SOURCE_ROOT"
echo "Jobs batch root: $JOBS_BATCH_ROOT"
echo "Harbor agent/environment: $AGENT_NAME / $ENV_NAME"
echo "Daytona concurrency: $N_CONCURRENT"
echo "Max allowed memory_mb: $MAX_MEMORY_MB"
echo "Max allowed storage_mb: $MAX_STORAGE_MB"
echo "Selected families: $family_count"
echo "Start family: ${START_FAMILY:-<from beginning>}"
if [[ -n "$N_FAMILIES" ]]; then
  echo "Family limit: $N_FAMILIES"
fi

if [[ "$DRY_RUN" == "1" ]]; then
  total_all_tasks=0
  total_resource_limited_tasks=0
  total_run_tasks=0
  run_family_count=0
  skipped_family_count=0

  for ((i = 0; i < family_count; i++)); do
    family_name="${FAMILY_NAMES[$i]}"
    family_dir="${FAMILY_DIRS[$i]}"
    family_job_dir="$JOBS_BATCH_ROOT/$family_name"
    all_task_names=()
    resource_limited_task_names=()
    run_task_names=()
    declare -A resource_task_memory=()
    declare -A resource_task_storage=()
    declare -A resource_task_reason=()
    compute_family_task_sets \
      "$family_dir" \
      all_task_names \
      resource_limited_task_names \
      run_task_names \
      resource_task_memory \
      resource_task_storage \
      resource_task_reason

    total_all_tasks=$((total_all_tasks + ${#all_task_names[@]}))
    total_resource_limited_tasks=$((total_resource_limited_tasks + ${#resource_limited_task_names[@]}))
    total_run_tasks=$((total_run_tasks + ${#run_task_names[@]}))

    if [[ "${#run_task_names[@]}" -eq 0 ]]; then
      skipped_family_count=$((skipped_family_count + 1))
    else
      run_family_count=$((run_family_count + 1))
    fi

    echo "  [$((i + 1))/$family_count] $family_name"
    echo "    total: ${#all_task_names[@]}, skipped_resource_limited: ${#resource_limited_task_names[@]}, to_run: ${#run_task_names[@]}"
    echo "    job_dir: $family_job_dir"
  done

  echo "Selected tasks before resource filtering: $total_all_tasks"
  echo "Tasks skipped because they exceed resource limits: $total_resource_limited_tasks"
  echo "Tasks to run now: $total_run_tasks"
  echo "Families to run now: $run_family_count"
  echo "Families skipped because no eligible tasks remain: $skipped_family_count"

  echo
  echo "Commands:"
  for ((i = 0; i < family_count; i++)); do
    family_name="${FAMILY_NAMES[$i]}"
    family_dir="${FAMILY_DIRS[$i]}"
    all_task_names=()
    resource_limited_task_names=()
    run_task_names=()
    declare -A resource_task_memory=()
    declare -A resource_task_storage=()
    declare -A resource_task_reason=()
    compute_family_task_sets \
      "$family_dir" \
      all_task_names \
      resource_limited_task_names \
      run_task_names \
      resource_task_memory \
      resource_task_storage \
      resource_task_reason

    if [[ "${#run_task_names[@]}" -eq 0 ]]; then
      printf '  # skip %q: no eligible tasks remain (resource_limited=%q)\n' \
        "$family_name" \
        "${#resource_limited_task_names[@]}"
      continue
    fi

    cmd=(
      harbor run
      -p "$family_dir"
      -a "$AGENT_NAME"
      -e "$ENV_NAME"
      --force-build
      --jobs-dir "$JOBS_BATCH_ROOT"
      --job-name "$family_name"
      --n-concurrent "$N_CONCURRENT"
    )

    for task_name in "${run_task_names[@]}"; do
      cmd+=(--task-name "$task_name")
    done

    if ((${#HARBOR_ARGS[@]} > 0)); then
      cmd+=("${HARBOR_ARGS[@]}")
    fi

    printf ' '
    print_command cmd
  done
  exit 0
fi

mkdir -p "$REPORTS_DIR"

printf 'family_name\tfamily_dir\tjobs_root\tjob_dir\ttotal_task_count\tskipped_resource_limit_count\trun_task_count\tstatus\tharbor_exit_code\n' > "$FAMILY_RUNS_TSV"
printf 'family_name\ttask_name\ttask_dir\teffective_memory_mb\teffective_storage_mb\treason\n' > "$SKIPPED_RESOURCE_LIMITS_TSV"
printf 'family_name\ttask_name\tbucket\treward\texception_type\tfailure_reason\tparse_error\ttrial_result_path\ttrial_dir\ttask_dir\ttrial_result_count\tharbor_exit_code\tjob_dir\n' > "$CLASSIFICATION_TSV"

overall_harbor_failed=0

for ((i = 0; i < family_count; i++)); do
  family_name="${FAMILY_NAMES[$i]}"
  family_dir="${FAMILY_DIRS[$i]}"
  family_job_dir="$JOBS_BATCH_ROOT/$family_name"

  all_task_names=()
  resource_limited_task_names=()
  run_task_names=()
  declare -A resource_task_memory=()
  declare -A resource_task_storage=()
  declare -A resource_task_reason=()
  compute_family_task_sets \
    "$family_dir" \
    all_task_names \
    resource_limited_task_names \
    run_task_names \
    resource_task_memory \
    resource_task_storage \
    resource_task_reason

  total_count="${#all_task_names[@]}"
  skipped_resource_count="${#resource_limited_task_names[@]}"
  run_count="${#run_task_names[@]}"

  echo
  echo "Running family [$((i + 1))/$family_count]: $family_name"
  echo "  total: $total_count, skipped_resource_limited: $skipped_resource_count, to_run: $run_count"

  append_skipped_resource_rows \
    "$family_name" \
    "$family_dir" \
    resource_limited_task_names \
    resource_task_memory \
    resource_task_storage \
    resource_task_reason

  if [[ "$run_count" -eq 0 ]]; then
    append_family_run_row \
      "$family_name" \
      "$family_dir" \
      "$JOBS_BATCH_ROOT" \
      "$family_job_dir" \
      "$total_count" \
      "$skipped_resource_count" \
      "$run_count" \
      "skipped_no_eligible_tasks" \
      "0"
    echo "  skipped: no eligible tasks remain after resource filtering"
    continue
  fi

  cmd=(
    harbor run
    -p "$family_dir"
    -a "$AGENT_NAME"
    -e "$ENV_NAME"
    --force-build
    --jobs-dir "$JOBS_BATCH_ROOT"
    --job-name "$family_name"
    --n-concurrent "$N_CONCURRENT"
  )

  for task_name in "${run_task_names[@]}"; do
    cmd+=(--task-name "$task_name")
  done

  if ((${#HARBOR_ARGS[@]} > 0)); then
    cmd+=("${HARBOR_ARGS[@]}")
  fi

  printf 'Command:'
  print_command cmd

  set +e
  "${cmd[@]}"
  harbor_exit_code=$?
  set -e

  if [[ "$harbor_exit_code" -ne 0 ]]; then
    overall_harbor_failed=1
  fi

  append_family_run_row \
    "$family_name" \
    "$family_dir" \
    "$JOBS_BATCH_ROOT" \
    "$family_job_dir" \
    "$total_count" \
    "$skipped_resource_count" \
    "$run_count" \
    "ran" \
    "$harbor_exit_code"

  analyze_family_results \
    "$family_name" \
    "$family_dir" \
    "$family_job_dir" \
    "$harbor_exit_code" \
    "${run_task_names[@]}"
done

write_summary

read -r selected_task_count run_task_count skipped_resource_limit_task_count pass_count fail_count family_harbor_failure_count skipped_family_count run_family_count < <(
  python3 - "$SUMMARY_JSON" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as handle:
    summary = json.load(handle)

print(
    int(summary.get("selected_task_count", 0)),
    int(summary.get("run_task_count", 0)),
    int(summary.get("skipped_resource_limit_task_count", 0)),
    int(summary.get("pass_count", 0)),
    int(summary.get("fail_count", 0)),
    int(summary.get("family_harbor_failure_count", 0)),
    int(summary.get("skipped_no_eligible_tasks_family_count", 0)),
    int(summary.get("run_family_count", 0)),
)
PY
)

echo
echo "Batch finished: $BATCH_NAME"
echo "Selected tasks before resource filtering: $selected_task_count"
echo "Tasks run: $run_task_count"
echo "Tasks skipped because they exceed resource limits: $skipped_resource_limit_task_count"
echo "Families run: $run_family_count"
echo "Families skipped because no eligible tasks remain: $skipped_family_count"
echo "Oracle pass tasks: $pass_count"
echo "Oracle fail tasks: $fail_count"
echo "Family harbor failures: $family_harbor_failure_count"
echo "Jobs root: $JOBS_BATCH_ROOT"
echo "Reports directory: $REPORTS_DIR"

if [[ "$overall_harbor_failed" -ne 0 || "$family_harbor_failure_count" -ne 0 || "$fail_count" -ne 0 ]]; then
  exit 1
fi
