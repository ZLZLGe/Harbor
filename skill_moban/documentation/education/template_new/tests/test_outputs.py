from __future__ import annotations

from conftest import (
    FINAL_PACKAGE_PATH,
    GUIDE_PATH,
    MANIFEST_PATH,
    NOTEBOOK_PATH,
    REQUIRED_SECTION_TITLES,
    SOURCE_MAP_PATH,
    VALID_SOURCE_FILES,
    accepted_metric_formats,
    cell_output_text,
    compute_reference_metrics,
    execute_notebook,
    extract_headings,
    find_required_heading_positions,
    load_final_package,
    load_guide_text,
    load_manifest,
    load_metric_definitions,
    load_notebook,
    load_source_map,
    markdown_section_text,
    run_build,
    substantive_output_cells,
)


def test_a_required_outputs_exist_and_parse() -> None:
    for path in [NOTEBOOK_PATH, GUIDE_PATH, MANIFEST_PATH, SOURCE_MAP_PATH]:
        assert path.exists(), path
        assert path.stat().st_size > 0

    notebook = load_notebook()
    manifest = load_manifest()
    source_map = load_source_map()
    guide = load_guide_text()

    assert notebook["nbformat"] == 4
    assert isinstance(manifest["lesson_info"], dict)
    assert isinstance(manifest["sections"], list)
    assert isinstance(manifest["key_metrics"], list)
    assert isinstance(source_map["sections"], list)
    assert guide.strip().startswith("# ")


def test_b_build_script_succeeds_and_writes_final_package() -> None:
    completed, payload = run_build()
    assert completed.returncode == 0, completed.stderr
    assert FINAL_PACKAGE_PATH.exists()
    assert payload["validation_passed"] is True
    assert payload["section_count"] == len(REQUIRED_SECTION_TITLES)
    assert payload["metric_count"] >= 4


def test_c_manifest_and_source_map_match_required_structure() -> None:
    manifest = load_manifest()
    source_map = load_source_map()

    assert [section["title"] for section in manifest["sections"]] == REQUIRED_SECTION_TITLES
    assert [section["title"] for section in source_map["sections"]] == REQUIRED_SECTION_TITLES

    for section in manifest["sections"]:
        assert isinstance(section["learning_goal"], str)
        assert section["learning_goal"].strip()
        assert isinstance(section["uses_files"], list)
        assert section["uses_files"]
        assert set(section["uses_files"]).issubset(VALID_SOURCE_FILES)
        assert isinstance(section["has_exercise"], bool)

    claim_count = 0
    for section in source_map["sections"]:
        assert set(section["sources"]).issubset(VALID_SOURCE_FILES)
        assert isinstance(section["claims"], list)
        claim_count += len(section["claims"])
        for claim in section["claims"]:
            assert claim["claim_id"].strip()
            assert claim["statement"].strip()
            assert set(claim["source_files"]).issubset(VALID_SOURCE_FILES)
    assert claim_count >= 7


def test_d_notebook_and_guide_contain_required_sections_in_order() -> None:
    notebook = load_notebook()
    guide_text = load_guide_text()

    notebook_headings = extract_headings(notebook)
    positions = find_required_heading_positions(notebook_headings)
    assert all(position >= 0 for position in positions), notebook_headings
    assert positions == sorted(positions)

    guide_headings = []
    for line in guide_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            guide_headings.append(stripped.lstrip("#").strip())
    assert REQUIRED_SECTION_TITLES == [heading for heading in guide_headings if heading in REQUIRED_SECTION_TITLES]


def test_e_notebook_reads_real_inputs_and_executes() -> None:
    notebook = load_notebook()
    code = "\n".join(cell.source for cell in notebook.cells if cell.cell_type == "code")
    for required in [
        "learner_events.csv",
        "quiz_attempts.csv",
        "quiz_items.csv",
        "metric_definitions.yaml",
    ]:
        assert required in code

    executed = execute_notebook()
    output_cells = substantive_output_cells(executed)
    assert len(output_cells) >= 3
    assert any("image/png" in output.get("data", {}) for cell in output_cells for output in cell.get("outputs", [])) or any(
        "text/html" in output.get("data", {}) for cell in output_cells for output in cell.get("outputs", [])
    )


def test_f_metrics_and_misconception_analysis_appear_in_bundle() -> None:
    executed = execute_notebook()
    notebook_text = "\n".join(cell.source for cell in executed.cells)
    output_text = "\n".join(cell_output_text(cell) for cell in executed.cells if cell.cell_type == "code")
    guide_text = load_guide_text()
    manifest = load_manifest()

    valid_metric_names = {item["name"] for item in load_metric_definitions()["metrics"]}
    manifest_metric_names = {item["name"] for item in manifest["key_metrics"]}
    assert manifest_metric_names.issubset(valid_metric_names)
    assert len(manifest_metric_names) >= 4

    for metric_name in manifest_metric_names:
        assert metric_name in notebook_text or metric_name in output_text or metric_name in guide_text

    reference = compute_reference_metrics()
    for metric_name in ["completion_rate", "quiz_pass_rate", "retry_rate"]:
        formats = accepted_metric_formats(reference[metric_name])
        assert any(value in output_text or value in notebook_text for value in formats), (
            metric_name,
            formats,
        )

    assert reference["top_misconception_topic"] in notebook_text or reference["top_misconception_topic"] in output_text
    assert reference["top_misconception_topic"] in guide_text


def test_g_sources_practice_and_claims_exist() -> None:
    notebook = load_notebook()
    notebook_text = "\n".join(cell.source for cell in notebook.cells)
    guide_text = load_guide_text()
    source_map = load_source_map()
    practice_text = markdown_section_text(notebook, "Practice")

    for source_name in [
        "lesson_brief.md",
        "learner_events.csv",
        "quiz_attempts.csv",
        "quiz_items.csv",
        "metric_definitions.yaml",
    ]:
        assert source_name in notebook_text
        assert source_name in guide_text or source_name in "\n".join(
            "\n".join(section["sources"]) for section in source_map["sections"]
        )

    practice_lines = [
        line.strip()
        for line in practice_text.splitlines()
        if line.strip() and line.strip() not in {"# Practice", "## Practice", "### Practice"}
    ]
    prompt_like_lines = [
        line
        for line in practice_lines
        if line.endswith("?")
        or line.startswith(("Q1", "Q2", "Q3", "1.", "2.", "3.", "-", "*"))
    ]
    assert len(practice_text.strip()) >= 120
    assert len(prompt_like_lines) >= 3
    for required_source in ["learner_events.csv", "metric_definitions.yaml", "quiz_items.csv"]:
        assert required_source in practice_text
    assert sum(len(section["claims"]) for section in source_map["sections"]) >= 7


def test_h_final_package_matches_bundle_counts() -> None:
    _, payload = run_build()
    source_map = load_source_map()
    manifest = load_manifest()

    assert payload["claim_count"] == sum(len(section["claims"]) for section in source_map["sections"])
    assert payload["metric_count"] == len(manifest["key_metrics"])
    assert payload["notebook_file"].endswith("student_lesson.ipynb")
    assert payload["guide_file"].endswith("instructor_guide.md")
