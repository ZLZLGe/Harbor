from quotaflags.policy import load_quota_policy, parse_quota_override


def test_load_quota_policy():
    policies = load_quota_policy("ops=10:20\nfinance=20:40")
    assert policies["ops"]["soft"] == 10


def test_parse_quota_override():
    user, delta = parse_quota_override("user-a:+15")
    assert (user, delta) == ("user-a", 15)
