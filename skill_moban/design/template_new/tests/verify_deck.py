from __future__ import annotations

import sys
import traceback

from test_guardrails import (
    test_deck_has_no_external_runtime_dependencies,
    test_hidden_service_and_protected_inputs_unchanged,
    test_required_outputs_exist_in_expected_locations,
    test_solver_visible_workspace_does_not_include_hidden_golden_decks,
    test_submission_and_receipt_are_not_placeholder_payloads,
)
from test_outputs import (
    test_a_output_files_and_json_shapes_exist,
    test_b_submission_roles_and_source_refs_cover_contract,
    test_c_receipt_reports_clean_live_acceptance,
    test_d_final_deck_is_nonempty_html,
)
from test_rendering import (
    test_receipt_confirms_navigation_and_visual_contracts,
    test_submission_slide_manifest_matches_rendered_contract,
)


CHECKS = [
    test_hidden_service_and_protected_inputs_unchanged,
    test_required_outputs_exist_in_expected_locations,
    test_a_output_files_and_json_shapes_exist,
    test_b_submission_roles_and_source_refs_cover_contract,
    test_c_receipt_reports_clean_live_acceptance,
    test_d_final_deck_is_nonempty_html,
    test_submission_slide_manifest_matches_rendered_contract,
    test_receipt_confirms_navigation_and_visual_contracts,
    test_deck_has_no_external_runtime_dependencies,
    test_submission_and_receipt_are_not_placeholder_payloads,
    test_solver_visible_workspace_does_not_include_hidden_golden_decks,
]


def main() -> int:
    for check in CHECKS:
        try:
            check()
            print(f"PASS {check.__name__}")
        except Exception:
            print(f"FAIL {check.__name__}", file=sys.stderr)
            traceback.print_exc()
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
