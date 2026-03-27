from sensorrules.config import load_sensor_config, validate_threshold_window


def test_load_sensor_config():
    config = load_sensor_config('{"name": "cold-room", "sensors": [{"name": "rack-a", "low": 1, "high": 4}]}')
    assert config["name"] == "cold-room"


def test_validate_threshold_window():
    problems = validate_threshold_window(
        {"sensors": [{"name": "rack-a", "low": 1, "high": 4}, {"name": "rack-b", "low": 5, "high": 2}]}
    )
    assert problems == ["rack-b"]
