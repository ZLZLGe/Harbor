def parse_badge_swipe(payload: str) -> dict[str, str]:
    """Parse a single swipe line into a structured record."""
    badge_id, door_id, action, timestamp = payload.split(";")
    return {
        "badge_id": badge_id.strip(),
        "door_id": door_id.strip(),
        "action": action.strip(),
        "timestamp": timestamp.strip(),
    }


def load_badge_batch(blob: bytes) -> list[dict[str, str]]:
    """Decode newline-delimited swipe events coming from edge devices."""
    events = []
    for line in blob.decode("utf-8").splitlines():
        line = line.strip()
        if line:
            events.append(parse_badge_swipe(line))
    return events


def summarize_actions(events: list[dict[str, str]]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for event in events:
        summary[event["action"]] = summary.get(event["action"], 0) + 1
    return summary
