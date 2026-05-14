from __future__ import annotations

from pathlib import Path

from conftest import (
    BRIEF_PATH,
    CLAIM_CATALOG_PATH,
    OUTPUT_FILES,
    OUTPUT_ROOT,
    SOURCE_PACKET_PATH,
    assert_claim_tokens_present,
    build_claim_catalog,
    claim_map,
    expected_context,
    first_meaningful_line,
    load_json,
    make_alternate_input_copy,
    manifest_entry,
    normalize_space,
    numbered_blocks,
    parse_brief,
    read_text,
    run_pack,
)


def test_formal_build_produces_required_outputs() -> None:
    result = run_pack()
    assert result.returncode == 0, result.stderr or result.stdout
    assert {path.name for path in OUTPUT_ROOT.iterdir()} == set(OUTPUT_FILES)
    for name in OUTPUT_FILES:
        assert (OUTPUT_ROOT / name).exists(), f"Missing output {name}"
    manifest = load_json(OUTPUT_ROOT / "manifest.json")
    assert isinstance(manifest.get("outputs"), list)


def test_shipped_claim_catalog_matches_data_snapshot() -> None:
    expected_catalog = build_claim_catalog()
    shipped_catalog = load_json(CLAIM_CATALOG_PATH)
    assert shipped_catalog["metric_years"] == expected_catalog["metric_years"]
    assert shipped_catalog["countries"] == expected_catalog["countries"]

    shipped_map = claim_map(shipped_catalog)
    expected_map = claim_map(expected_catalog)
    assert set(shipped_map) == set(expected_map)

    for claim_id, expected_claim in expected_map.items():
        shipped_claim = shipped_map[claim_id]
        assert shipped_claim["statement"] == expected_claim["statement"]
        assert shipped_claim["metric_value"] == expected_claim["metric_value"]
        assert shipped_claim["verification_tokens"] == expected_claim["verification_tokens"]
        assert shipped_claim["source_files"] == expected_claim["source_files"]


def test_manifest_schema_and_contract_alignment() -> None:
    result = run_pack()
    assert result.returncode == 0, result.stderr or result.stdout

    context = expected_context()
    brief = context["brief"]
    shipped_claims = claim_map(context["shipped_catalog"])
    manifest = load_json(OUTPUT_ROOT / "manifest.json")

    assert manifest["campaign_slug"] == brief["campaign_slug"]
    assert manifest["publisher"] == brief["publisher"]
    if "audience" in manifest:
        assert manifest["audience"] == brief["audience"]
    if "primary_angle" in manifest:
        assert manifest["primary_angle"] == brief["primary_angle"]
    if "key_years" in manifest:
        assert manifest["key_years"] == context["shipped_catalog"]["metric_years"]
    if "source_files" in manifest:
        assert set(manifest["source_files"]).issuperset({"brief/project_brief.md", "brief/source_packet.md", "data/claim_catalog.json"})
    actual_output_files = {(entry.get("file") or entry.get("output_file")) for entry in manifest["outputs"]}
    assert set(brief["required_claims_by_output"]).issubset(actual_output_files)

    allowed_sources = set(brief["source_files"])
    for filename, required_claim_ids in brief["required_claims_by_output"].items():
        entry = manifest_entry(manifest, filename)
        assert entry["claim_ids"] == required_claim_ids
        assert set(entry["source_files"]).issubset(allowed_sources)
        assert "data/claim_catalog.json" in entry["source_files"]
        assert "brief/project_brief.md" in entry["source_files"]
        assert "brief/source_packet.md" in entry["source_files"]
        expected_claim_sources = {
            source_file
            for claim_id in required_claim_ids
            for source_file in shipped_claims[claim_id]["source_files"]
        }
        assert expected_claim_sources.issubset(set(entry["source_files"]))


def test_outputs_cover_required_claims_and_platform_rules() -> None:
    result = run_pack()
    assert result.returncode == 0, result.stderr or result.stdout

    brief = parse_brief(BRIEF_PATH)
    claim_lookup = claim_map(load_json(CLAIM_CATALOG_PATH))

    core_text = read_text(OUTPUT_ROOT / "core_angle.md")
    assert_claim_tokens_present(core_text, [claim_lookup[claim_id] for claim_id in brief["required_claims_by_output"]["core_angle.md"]])

    thread_text = read_text(OUTPUT_ROOT / "x_thread.md")
    posts = numbered_blocks(thread_text)
    assert len(posts) == 5
    for post, claim_id in zip(posts, brief["required_claims_by_output"]["x_thread.md"], strict=True):
        assert_claim_tokens_present(post, [claim_lookup[claim_id]])
        assert "#" not in post

    linkedin_text = read_text(OUTPUT_ROOT / "linkedin_post.md")
    first_line = linkedin_text.splitlines()[0].strip()
    assert first_line
    assert not first_line.startswith("#")
    assert_claim_tokens_present(linkedin_text, [claim_lookup[claim_id] for claim_id in brief["required_claims_by_output"]["linkedin_post.md"]])

    newsletter_text = read_text(OUTPUT_ROOT / "newsletter.md")
    assert "Subject:" in newsletter_text
    assert "Preview:" in newsletter_text
    assert_claim_tokens_present(newsletter_text, [claim_lookup[claim_id] for claim_id in brief["required_claims_by_output"]["newsletter.md"]])

    video_text = read_text(OUTPUT_ROOT / "short_video_script.md")
    beats = numbered_blocks(video_text)
    assert len(beats) == 6
    for beat in beats:
        assert "Visual:" in beat
        assert "Line:" in beat
    assert_claim_tokens_present(video_text, [claim_lookup[claim_id] for claim_id in brief["required_claims_by_output"]["short_video_script.md"]])

    for path in [
        OUTPUT_ROOT / "core_angle.md",
        OUTPUT_ROOT / "x_thread.md",
        OUTPUT_ROOT / "linkedin_post.md",
        OUTPUT_ROOT / "newsletter.md",
        OUTPUT_ROOT / "short_video_script.md",
    ]:
        text = read_text(path).lower()
        for phrase in brief["banned_phrases"]:
            assert phrase not in text


def test_outputs_are_platform_distinct() -> None:
    result = run_pack()
    assert result.returncode == 0, result.stderr or result.stdout

    hooks = [
        first_meaningful_line(read_text(OUTPUT_ROOT / "core_angle.md")),
        numbered_blocks(read_text(OUTPUT_ROOT / "x_thread.md"))[0],
        first_meaningful_line(read_text(OUTPUT_ROOT / "linkedin_post.md").split("\n", 1)[1]),
        first_meaningful_line(read_text(OUTPUT_ROOT / "newsletter.md").split("Preview:", 1)[1]),
        next(line.strip() for line in read_text(OUTPUT_ROOT / "short_video_script.md").splitlines() if line.strip().startswith("Line:")),
    ]
    normalized_hooks = [normalize_space(hook).lower() for hook in hooks]
    assert len(set(normalized_hooks)) == len(normalized_hooks)

    body_texts = [
        read_text(OUTPUT_ROOT / "core_angle.md"),
        read_text(OUTPUT_ROOT / "x_thread.md"),
        read_text(OUTPUT_ROOT / "linkedin_post.md"),
        read_text(OUTPUT_ROOT / "newsletter.md"),
        read_text(OUTPUT_ROOT / "short_video_script.md"),
    ]
    assert len({normalize_space(text) for text in body_texts}) == len(body_texts)


def test_alternate_fixture_rerun_updates_content() -> None:
    result = run_pack()
    assert result.returncode == 0, result.stderr or result.stdout

    baseline_catalog = load_json(CLAIM_CATALOG_PATH)
    tmpdir, alt_root = make_alternate_input_copy()
    try:
        alt_output = Path(tmpdir.name) / "output"
        alt_result = run_pack(alt_root, alt_output)
        assert alt_result.returncode == 0, alt_result.stderr or alt_result.stdout

        alt_catalog = load_json(alt_root / "data" / "claim_catalog.json")
        alt_claim_lookup = claim_map(alt_catalog)
        base_claim_lookup = claim_map(baseline_catalog)
        brief = parse_brief(alt_root / "brief" / "project_brief.md")

        for filename in ["x_thread.md", "newsletter.md", "short_video_script.md", "manifest.json"]:
            assert (alt_output / filename).exists()

        alt_thread = read_text(alt_output / "x_thread.md")
        alt_newsletter = read_text(alt_output / "newsletter.md")
        alt_video = read_text(alt_output / "short_video_script.md")

        for claim_id in ["C02_US_GDP_SCALE", "C03_CANADA_CLEAN_SHARE", "C05_MEXICO_GAS_RELIANCE", "C06_MEXICO_LOWEST_CO2", "C07_US_CLEAN_SCALE"]:
            alt_claim = alt_claim_lookup[claim_id]
            base_claim = base_claim_lookup[claim_id]
            target_text = alt_newsletter if claim_id == "C02_US_GDP_SCALE" else f"{alt_thread}\n{alt_video}\n{alt_newsletter}"
            assert_claim_tokens_present(target_text, [alt_claim])
            base_metric = base_claim["metric_value"]
            if base_metric != alt_claim["metric_value"]:
                assert base_metric not in target_text

            manifest = load_json(alt_output / "manifest.json")
            if "key_years" in manifest:
                assert manifest["key_years"] == alt_catalog["metric_years"]
            actual_output_files = {(entry.get("file") or entry.get("output_file")) for entry in manifest["outputs"]}
            assert set(brief["required_claims_by_output"]).issubset(actual_output_files)
    finally:
        tmpdir.cleanup()
