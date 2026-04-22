from __future__ import annotations

import pytest

from conftest import assert_output_matches_reference_behavior, assert_reason_semantics, build_solution_output


def test_output_schema_and_summary_contract(expected_output) -> None:
    output = build_solution_output()

    assert set(output) == {"summary", "shortlist", "rejected_compounds"}
    assert output["summary"] == expected_output["summary"]
    assert isinstance(output["shortlist"], list)
    assert isinstance(output["rejected_compounds"], list)
    assert output["summary"]["n_input_records"] == 16
    assert output["summary"]["n_standardized_candidates"] == 14
    assert output["summary"]["n_keep"] == 8
    assert output["summary"]["n_reject"] == 6


def test_standardization_merges_salts_and_preserves_stereo() -> None:
    output = build_solution_output()
    shortlist_ids = [row["compound_id"] for row in output["shortlist"]]

    assert "LIB001_s_ibuprofen" in shortlist_ids
    assert "LIB002_s_ibuprofen_sodium" not in shortlist_ids
    assert "LIB003_r_ibuprofen" in shortlist_ids
    assert "LIB008_lidocaine" in shortlist_ids
    assert "LIB009_lidocaine_alt" not in shortlist_ids

    s_ibuprofen = next(row for row in output["shortlist"] if row["compound_id"] == "LIB001_s_ibuprofen")
    r_ibuprofen = next(row for row in output["shortlist"] if row["compound_id"] == "LIB003_r_ibuprofen")
    assert s_ibuprofen["canonical_smiles"] != r_ibuprofen["canonical_smiles"]
    assert s_ibuprofen["inchikey"] != r_ibuprofen["inchikey"]


def test_descriptor_values_and_alerts_on_representative_compounds() -> None:
    output = build_solution_output()
    shortlist = {row["compound_id"]: row for row in output["shortlist"]}
    rejected = {row["compound_id"]: row for row in output["rejected_compounds"]}

    naproxen = shortlist["LIB004_naproxen"]
    assert naproxen["molecular_weight"] == pytest.approx(230.2630)
    assert naproxen["logp"] == pytest.approx(3.0365)
    assert naproxen["qed"] == pytest.approx(0.8811)
    assert naproxen["alerts"] == []

    lidocaine = shortlist["LIB008_lidocaine"]
    assert lidocaine["tpsa"] == pytest.approx(32.3400)
    assert lidocaine["rotatable_bonds"] == 5
    assert lidocaine["alerts"] == []

    nitrobenzene = rejected["LIB012_nitrobenzene"]
    assert nitrobenzene["alerts"] == ["nitro_aromatic"]
    assert_reason_semantics(
        nitrobenzene,
        {
            "compound_id": "LIB012_nitrobenzene",
            "alerts": ["nitro_aromatic"],
            "reasons": ["alert:nitro_aromatic"],
        },
    )

    flurbiprofen = rejected["LIB006_flurbiprofen"]
    assert flurbiprofen["alerts"] == []
    assert_reason_semantics(
        flurbiprofen,
        {
            "compound_id": "LIB006_flurbiprofen",
            "alerts": [],
            "reasons": ["logp>3.5"],
        },
    )


def test_similarity_and_shortlist_order(expected_output) -> None:
    output = build_solution_output()

    actual_ids = [row["compound_id"] for row in output["shortlist"]]
    expected_ids = [row["compound_id"] for row in expected_output["shortlist"]]
    assert actual_ids == expected_ids
    assert actual_ids[:4] == [
        "LIB004_naproxen",
        "LIB005_ketoprofen",
        "LIB001_s_ibuprofen",
        "LIB003_r_ibuprofen",
    ]

    top_rows = {row["compound_id"]: row for row in output["shortlist"]}
    assert top_rows["LIB004_naproxen"]["max_similarity_to_actives"] == pytest.approx(1.0)
    assert top_rows["LIB005_ketoprofen"]["max_similarity_to_actives"] == pytest.approx(1.0)
    assert top_rows["LIB001_s_ibuprofen"]["max_similarity_to_actives"] == pytest.approx(1.0)
    assert top_rows["LIB003_r_ibuprofen"]["max_similarity_to_actives"] == pytest.approx(0.75)


def test_end_to_end_matches_reference_behavior(expected_output) -> None:
    output = build_solution_output()
    assert_output_matches_reference_behavior(output, expected_output)
