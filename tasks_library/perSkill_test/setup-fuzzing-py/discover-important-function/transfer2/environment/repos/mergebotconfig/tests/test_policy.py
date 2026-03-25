from mergebotconfig.policy import load_policy_document, parse_rule_block, parse_schedule


def test_parse_rule_block_rejects_duplicate_env_keys():
    try:
        parse_rule_block("ENV=prod\nENV=shadow")
    except ValueError as exc:
        assert "duplicate env key" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_parse_schedule_rejects_invalid_minute():
    try:
        parse_schedule("10:61")
    except ValueError as exc:
        assert "minute out of range" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_load_policy_document_ignores_blank_rules_and_preserves_order():
    document = load_policy_document("allow\n\n\nnotify")
    assert document["rules"] == ["allow"]
    assert document["count"] == 2
