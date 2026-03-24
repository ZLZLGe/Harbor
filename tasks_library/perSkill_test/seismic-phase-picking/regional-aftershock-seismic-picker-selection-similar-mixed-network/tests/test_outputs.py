import csv
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean


PREDICTIONS_FILE = Path("/root/mixed_network_picks.csv")
MANIFEST_FILE = Path("/root/campaign/trace_manifest.csv")
REFERENCE_FILE = Path(__file__).with_name("reference_labels.csv")
REQUIRED_COLUMNS = ["trace_id", "phase", "pick_idx", "confidence", "method"]


def load_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def parse_int(value: str) -> int:
    parsed = int(value)
    return parsed


def parse_float(value: str) -> float:
    return float(value)


def main() -> None:
    if not PREDICTIONS_FILE.exists():
        raise AssertionError(f"missing predictions file: {PREDICTIONS_FILE}")

    pred_columns, pred_rows = load_csv(PREDICTIONS_FILE)
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in pred_columns]
    if missing_columns:
        raise AssertionError(f"missing required columns: {missing_columns}")

    _, manifest_rows = load_csv(MANIFEST_FILE)
    _, reference_rows = load_csv(REFERENCE_FILE)

    manifest_ids = {row["trace_id"] for row in manifest_rows}
    cohort_by_trace = {row["trace_id"]: row["cohort"] for row in manifest_rows}
    reference = {
        row["trace_id"]: {"p_idx": parse_int(row["p_idx"]), "s_idx": parse_int(row["s_idx"])}
        for row in reference_rows
    }

    if len(pred_rows) != len(manifest_ids) * 2:
        raise AssertionError("each trace_id must contribute exactly one P row and one S row")

    seen_pairs = set()
    methods_by_trace = defaultdict(set)
    picks = {}

    for row in pred_rows:
        trace_id = row["trace_id"]
        phase = row["phase"]
        key = (trace_id, phase)

        if trace_id not in manifest_ids:
            raise AssertionError(f"unexpected trace_id: {trace_id}")
        if phase not in {"P", "S"}:
            raise AssertionError(f"unexpected phase value: {phase}")
        if key in seen_pairs:
            raise AssertionError(f"duplicate prediction row for {trace_id} {phase}")

        pick_idx = parse_int(row["pick_idx"])
        confidence = parse_float(row["confidence"])
        method = row["method"].strip()

        if not 0 <= pick_idx < 12000:
            raise AssertionError(f"pick_idx out of range for {trace_id} {phase}: {pick_idx}")
        if not 0.0 <= confidence <= 1.0:
            raise AssertionError(f"confidence out of range for {trace_id} {phase}: {confidence}")
        if not method:
            raise AssertionError(f"empty method for {trace_id} {phase}")

        seen_pairs.add(key)
        methods_by_trace[trace_id].add(method)
        picks[key] = pick_idx

    for trace_id in manifest_ids:
        if (trace_id, "P") not in picks or (trace_id, "S") not in picks:
            raise AssertionError(f"incomplete picks for {trace_id}")
        if len(methods_by_trace[trace_id]) != 1:
            raise AssertionError(f"P/S rows for {trace_id} must share the same method")

    trace_level_methods = Counter(next(iter(methods)) for methods in methods_by_trace.values())
    if len(trace_level_methods) < 2:
        raise AssertionError("the batch must use at least two distinct methods")
    if min(trace_level_methods.values()) < 3:
        raise AssertionError("each method should be used on at least three traces")

    p_errors = []
    s_errors = []
    cohort_s_errors = defaultdict(list)

    for trace_id in manifest_ids:
        ref = reference[trace_id]
        p_error = abs(picks[(trace_id, "P")] - ref["p_idx"])
        s_error = abs(picks[(trace_id, "S")] - ref["s_idx"])
        p_errors.append(p_error)
        s_errors.append(s_error)
        cohort_s_errors[cohort_by_trace[trace_id]].append(s_error)

    if max(p_errors) > 2:
        raise AssertionError(f"P picks drift too far from the centered window: max error {max(p_errors)}")
    if mean(p_errors) > 1.0:
        raise AssertionError(f"P mean absolute error too high: {mean(p_errors):.2f}")

    if max(s_errors) > 18:
        raise AssertionError(f"S picks have an error above 18 samples: {max(s_errors)}")
    if mean(s_errors) > 16.0:
        raise AssertionError(f"S mean absolute error too high: {mean(s_errors):.2f}")
    if sum(error <= 15 for error in s_errors) < 7:
        raise AssertionError("at least seven S picks must be within 15 samples")

    for cohort, errors in cohort_s_errors.items():
        if mean(errors) > 16.5:
            raise AssertionError(f"{cohort} cohort S mean absolute error too high: {mean(errors):.2f}")


if __name__ == "__main__":
    main()
