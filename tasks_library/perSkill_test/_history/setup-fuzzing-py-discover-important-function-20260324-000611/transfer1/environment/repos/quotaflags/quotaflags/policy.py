def load_quota_policy(raw: str) -> dict[str, dict[str, int]]:
    """Load a text quota policy where each line is team=soft:hard."""
    policies: dict[str, dict[str, int]] = {}
    for line in raw.splitlines():
        if not line.strip():
            continue
        team, limits = line.split("=")
        soft, hard = limits.split(":")
        policies[team.strip()] = {"soft": int(soft), "hard": int(hard)}
    return policies


def parse_quota_override(raw: str) -> tuple[str, int]:
    """Parse a single user override directive like user-a:+15."""
    user, delta = raw.split(":")
    return user.strip(), int(delta)


def quota_gap(policy: dict[str, int]) -> int:
    return policy["hard"] - policy["soft"]
