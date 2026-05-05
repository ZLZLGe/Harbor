from pathlib import Path

from common import ACCESS_LOG, CHECKSUM_DIR, CLI_PATH, DATA_DIR, EXPECTED_OUTPUT_FILES, OUTPUT_DIR, PAPRIKA_DATA_DIR, SKILLS_DIR, checksum_manifest, expected_outputs, hash_file, read_access_log


EMPTY_SHA256_STDOUT = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  -"


def test_visible_inputs_unchanged():
    expected = (CHECKSUM_DIR / "paprika-input.sha256").read_text(encoding="utf-8")
    actual = checksum_manifest(DATA_DIR)
    assert actual == expected


def test_paprika_seed_unchanged():
    expected = (CHECKSUM_DIR / "paprika-seed.sha256").read_text(encoding="utf-8")
    actual = checksum_manifest(PAPRIKA_DATA_DIR)
    assert actual == expected


def test_paprika_cli_unchanged():
    expected = (CHECKSUM_DIR / "paprika-cli.sha256").read_text(encoding="utf-8").split()[0]
    assert hash_file(CLI_PATH) == expected


def test_shipped_skill_payload_unchanged_or_absent():
    expected = (CHECKSUM_DIR / "paprika-skills.sha256").read_text(encoding="utf-8").strip()
    actual = checksum_manifest(SKILLS_DIR, exclude_prefixes=(".system/",)).strip() if SKILLS_DIR.exists() else ""
    if expected == EMPTY_SHA256_STDOUT and actual == "":
        return
    assert actual == expected


def test_no_extra_top_level_outputs():
    actual = {path.name for path in OUTPUT_DIR.iterdir()}
    assert actual == EXPECTED_OUTPUT_FILES


def test_paprika_workflow_log():
    brief, expected_manifest, _, _, _ = expected_outputs()
    entries = read_access_log()
    assert entries, f"Expected Paprika access log at {ACCESS_LOG}"
    argv_list = [entry["argv"] for entry in entries]

    def is_cli_call(argv, command):
        return (
            len(argv) >= 2
            and Path(argv[0]).name == "paprika"
            and argv[1] == command
        )

    assert any(
        is_cli_call(argv, "meals")
        and "--json" in argv
        for argv in argv_list
    ), "Missing Paprika CLI meal-plan query"

    for meal in expected_manifest["meals"]:
        assert any(
            is_cli_call(argv, "recipe")
            and meal["recipe_uid"] in argv
            and "--json" in argv
            for argv in argv_list
        ), f"Missing Paprika CLI recipe detail query for {meal['recipe_uid']}"

    assert any(
        is_cli_call(argv, "groceries")
        and "--all" in argv
        and "--json" in argv
        for argv in argv_list
    ), "Missing Paprika CLI grocery carryover review"
