import csv
from collections import Counter, defaultdict
from pathlib import Path


PREDICTIONS_FILE = Path("/root/repeater_template_matches.csv")
REFERENCE_FILE = Path(__file__).with_name("reference_matches.csv")
CANDIDATE_MANIFEST = Path("/root/repeaters/candidate_manifest.csv")
REQUIRED_COLUMNS = ["template_id", "file_name", "phase", "pick_idx", "score"]


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def parse_int(value: str) -> int:
    return int(value)


def parse_float(value: str) -> float:
    return float(value)


def main() -> None:
    if not PREDICTIONS_FILE.exists():
        raise AssertionError(f"missing predictions file: {PREDICTIONS_FILE}")

    with PREDICTIONS_FILE.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        columns = list(reader.fieldnames or [])

    if columns != REQUIRED_COLUMNS:
        raise AssertionError(f"unexpected columns: {columns}")

    reference_rows = load_csv(REFERENCE_FILE)
    candidate_rows = load_csv(CANDIDATE_MANIFEST)
    known_candidates = {row["file_name"] for row in candidate_rows}
    reference_by_key = {
        (row["file_name"], row["phase"]): {
            "template_id": row["template_id"],
            "pick_idx": parse_int(row["pick_idx"]),
            "score": parse_float(row["score"]),
        }
        for row in reference_rows
    }

    if len(rows) != len(reference_rows):
        raise AssertionError(f"unexpected number of output rows: {len(rows)}")

    matched_files = sorted({row["file_name"] for row in reference_rows})
    predicted_files = sorted({row["file_name"] for row in rows})
    if predicted_files != matched_files:
        raise AssertionError(f"predicted file set mismatch: {predicted_files}")

    grouped = defaultdict(list)
    template_counts = Counter()

    for row in rows:
        template_id = row["template_id"].strip()
        file_name = row["file_name"].strip()
        phase = row["phase"].strip()
        pick_idx = parse_int(row["pick_idx"])
        score = parse_float(row["score"])

        if file_name not in known_candidates:
            raise AssertionError(f"unknown candidate file: {file_name}")
        if phase not in {"P", "S"}:
            raise AssertionError(f"unexpected phase: {phase}")
        if not 0 <= score <= 1:
            raise AssertionError(f"score out of range for {file_name} {phase}: {score}")

        grouped[file_name].append((phase, template_id, pick_idx, score))

        reference = reference_by_key.get((file_name, phase))
        if reference is None:
            raise AssertionError(f"unexpected match row for {file_name} {phase}")
        if template_id != reference["template_id"]:
            raise AssertionError(f"wrong template for {file_name} {phase}: {template_id}")
        if abs(pick_idx - reference["pick_idx"]) > 3:
            raise AssertionError(
                f"pick_idx drift too large for {file_name} {phase}: {pick_idx} vs {reference['pick_idx']}"
            )
        if abs(score - reference["score"]) > 0.06:
            raise AssertionError(f"score drift too large for {file_name} {phase}: {score} vs {reference['score']}")

    for file_name, items in grouped.items():
        if len(items) != 2:
            raise AssertionError(f"{file_name} must have exactly two rows")
        phase_map = {phase: (template_id, pick_idx, score) for phase, template_id, pick_idx, score in items}
        if set(phase_map) != {"P", "S"}:
            raise AssertionError(f"{file_name} must contain one P and one S")

        p_template, p_idx, p_score = phase_map["P"]
        s_template, s_idx, s_score = phase_map["S"]
        if p_template != s_template:
            raise AssertionError(f"{file_name} P/S rows must share template_id")
        if abs(p_score - s_score) > 1e-9:
            raise AssertionError(f"{file_name} P/S rows must share the same score")
        if not p_idx < s_idx:
            raise AssertionError(f"{file_name} must have P before S")
        if p_score < 0.25:
            raise AssertionError(f"{file_name} score is too weak to be a confident repeater")
        template_counts[p_template] += 1

    if template_counts != Counter({"TPL_A": 2, "TPL_B": 2, "TPL_C": 2}):
        raise AssertionError(f"unexpected template coverage: {template_counts}")


if __name__ == "__main__":
    main()
