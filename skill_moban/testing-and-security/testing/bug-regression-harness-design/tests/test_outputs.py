import json
import os
from collections import OrderedDict
from pathlib import Path


EXPECTED = [
    OrderedDict(
        [
            ("ticket_id", "BUG-101"),
            ("test_layer", "API"),
            ("test_pattern", "setupTestServer + supertest"),
            ("key_location", "packages/cli/test/integration/"),
            ("parity_check", "sandbox+production"),
            ("artifact", "bug-check-suite::bug-101::sandbox-production-contract"),
            ("fix_hint", "align sandbox and production assertions in packages/cli/test/integration/"),
        ]
    ),
    OrderedDict(
        [
            ("ticket_id", "BUG-102"),
            ("test_layer", "integration"),
            ("test_pattern", "WorkflowRunner + DI container"),
            ("key_location", "packages/cli/src/__tests__/"),
            ("parity_check", "single-path"),
            ("artifact", "failing-test::bug-102::execution-engine-regression"),
            ("fix_hint", "replay the workflow fixture and patch the stacktrace path in packages/cli/src/__tests__/"),
        ]
    ),
    OrderedDict(
        [
            ("ticket_id", "BUG-103"),
            ("test_layer", "unit"),
            ("test_pattern", "NodeTestHarness + nock"),
            ("key_location", "packages/nodes-base/nodes/*/test/"),
            ("parity_check", "single-path"),
            ("artifact", "failing-test::bug-103::node-operation-regression"),
            ("fix_hint", "stub Stripe with deterministic fixtures before fixing packages/nodes-base/nodes/*/test/"),
        ]
    ),
    OrderedDict(
        [
            ("ticket_id", "BUG-104"),
            ("test_layer", "UI"),
            ("test_pattern", "Vue Test Utils + Pinia"),
            ("key_location", "packages/frontend/editor-ui/src/**/__tests__/"),
            ("parity_check", "single-path"),
            ("artifact", "failing-test::bug-104::editor-ui-regression"),
            ("fix_hint", "lock the credential drawer interaction contract in packages/frontend/editor-ui/src/**/__tests__/"),
        ]
    ),
    OrderedDict(
        [
            ("ticket_id", "BUG-105"),
            ("test_layer", "E2E"),
            ("test_pattern", "Test containers + composables"),
            ("key_location", "packages/testing/playwright/"),
            ("parity_check", "single-path"),
            ("artifact", "bug-check-suite::bug-105::playwright-path-suite"),
            ("fix_hint", "lock the canvas run interaction contract in packages/testing/playwright/"),
        ]
    ),
    OrderedDict(
        [
            ("ticket_id", "BUG-106"),
            ("test_layer", "unit"),
            ("test_pattern", "NodeTestHarness assertBinaryData"),
            ("key_location", "packages/core/nodes-testing/"),
            ("parity_check", "single-path"),
            ("artifact", "failing-test::bug-106::binary-data-regression"),
            ("fix_hint", "replay the workflow fixture and preserve the corrected behavior in packages/core/nodes-testing/"),
        ]
    ),
]

EXPECTED_KEYS = [
    "ticket_id",
    "test_layer",
    "test_pattern",
    "key_location",
    "parity_check",
    "artifact",
    "fix_hint",
]


def main() -> None:
    workspace_root = Path(os.environ.get("WORKSPACE_ROOT", "/app/workspace"))
    output_path = workspace_root / "output" / "regression_harness.json"
    assert output_path.exists(), f"缺少输出文件: {output_path}"

    with output_path.open("r", encoding="utf-8") as f:
        payload = json.load(f, object_pairs_hook=OrderedDict)

    assert isinstance(payload, list), "输出根结构必须为数组"
    assert [item["ticket_id"] for item in payload] == sorted(item["ticket_id"] for item in payload), (
        "ticket_id 必须按升序排序"
    )

    for item in payload:
        assert list(item.keys()) == EXPECTED_KEYS, f"字段顺序不匹配: {list(item.keys())}"
        for value in item.values():
            if isinstance(value, str):
                assert value.strip() == value, f"字符串存在首尾空格: {value!r}"
                assert value not in {"", "null", "None", "N/A"}, f"出现空值表达: {value!r}"

    assert payload == EXPECTED, f"输出内容不匹配.\nactual={payload}\nexpected={EXPECTED}"


if __name__ == "__main__":
    main()
