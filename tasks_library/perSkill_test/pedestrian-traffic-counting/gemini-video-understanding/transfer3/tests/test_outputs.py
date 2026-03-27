import json

INPUT_PATH = "/root/scene_alerts.json"
OUTPUT_PATH = "/root/transfer3_alerts.md"


def ts_key(ts: str) -> tuple[int, int]:
    mm, ss = ts.split(":", 1)
    return int(mm), int(ss)


def expected_markdown() -> str:
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        payload = json.load(f)

    chunks = ["# Pedestrian Safety Alert Digest"]
    for video in sorted(payload.get("videos", []), key=lambda item: item["video"]):
        events = video["events"]
        total_events = len(events)

        alert_events = 0
        max_wait = -1
        max_wait_ts = "00:00"
        crossings_red = 0

        for e in events:
            waiting = int(e["pedestrians_waiting"])
            crossing = int(e["pedestrians_crossing"])
            signal = e["signal"]

            if waiting >= 10 or (signal == "RED" and crossing > 0):
                alert_events += 1

            if waiting > max_wait or (waiting == max_wait and ts_key(e["timestamp"]) < ts_key(max_wait_ts)):
                max_wait = waiting
                max_wait_ts = e["timestamp"]

            if signal == "RED":
                crossings_red += crossing

        chunks.extend(
            [
                "",
                f"## {video['video']}",
                f"- total_events: {total_events}",
                f"- alert_events: {alert_events}",
                f"- highest_waiting: {max_wait} at {max_wait_ts}",
                f"- crossings_during_red: {crossings_red}",
            ]
        )

    return "\n".join(chunks).rstrip() + "\n"


def test_transfer3_markdown_exact():
    with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
        actual = f.read()
    assert actual == expected_markdown()
