import json


def load_sensor_config(raw: str) -> dict[str, object]:
    """Load JSON sensor policy files with nested threshold settings."""
    config = json.loads(raw)
    config.setdefault("sensors", [])
    return config


def validate_threshold_window(config: dict[str, object]) -> list[str]:
    """Validate threshold windows before the policy is pushed to devices."""
    problems = []
    sensors = config.get("sensors", [])
    for item in sensors:
        low = item.get("low", 0)
        high = item.get("high", 0)
        if low >= high:
            problems.append(item["name"])
    return problems


def render_policy_name(config: dict[str, object]) -> str:
    return str(config.get("name", "unnamed"))
