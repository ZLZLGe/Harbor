from __future__ import annotations

from pathlib import Path

from conftest import BASELINE_ROOT, INPUT_ROOT, OUTPUT_FILES, OUTPUT_ROOT, SKILL_ROOT, current_hash_lines, run_pack


def test_input_files_are_unchanged() -> None:
    expected_input = (BASELINE_ROOT / "input.sha256").read_text(encoding="utf-8")
    assert current_hash_lines(INPUT_ROOT) == expected_input


def test_output_inventory_is_restricted() -> None:
    result = run_pack()
    assert result.returncode == 0, result.stderr or result.stdout
    assert {path.name for path in OUTPUT_ROOT.iterdir()} == set(OUTPUT_FILES)


def test_outputs_do_not_contain_placeholder_or_verifier_strings() -> None:
    result = run_pack()
    assert result.returncode == 0, result.stderr or result.stdout
    for name in OUTPUT_FILES:
        text = (OUTPUT_ROOT / name).read_text(encoding="utf-8").lower()
        for token in ["placeholder", "verifier", "todo", "tbd", "/tests", "/root/.codex/skills", "runtime check"]:
            assert token not in text


def test_with_skill_logs_are_consistent_if_present() -> None:
    skill_path = SKILL_ROOT / "SKILL.md"
    agent_log = Path("/logs/agent/codex.txt")
    if not skill_path.exists() or not agent_log.exists():
        return
    log_text = agent_log.read_text(encoding="utf-8", errors="ignore")
    if "content-engine" not in log_text:
        return
    assert str(skill_path) in log_text
