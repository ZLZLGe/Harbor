from badgecodec.swipe import load_badge_batch, parse_badge_swipe


def test_parse_badge_swipe():
    event = parse_badge_swipe("B-17;Door-2;allow;2026-03-01T08:00:00Z")
    assert event["badge_id"] == "B-17"
    assert event["action"] == "allow"


def test_load_badge_batch():
    events = load_badge_batch(b"B-17;Door-2;allow;2026-03-01T08:00:00Z\nB-18;Door-9;deny;2026-03-01T08:01:00Z\n")
    assert len(events) == 2
