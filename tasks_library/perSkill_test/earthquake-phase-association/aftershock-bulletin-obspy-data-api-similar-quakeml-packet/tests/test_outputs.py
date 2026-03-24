from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET


OUTPUT_XML = Path("/root/aftershock_catalog.xml")
EXPECTED = [
    ("2019-07-04T19:03:02.540000", 14),
    ("2019-07-04T19:20:01.230000", 12),
    ("2019-07-04T19:27:40.760000", 12),
    ("2019-07-04T19:47:50.200000", 11),
]


def _read_catalog():
    assert OUTPUT_XML.exists(), f"missing output file: {OUTPUT_XML}"
    root = ET.parse(OUTPUT_XML).getroot()
    ns = {"q": "http://quakeml.org/xmlns/bed/1.2"}
    events = []
    for event in root.findall(".//q:event", ns):
        origin = event.find("q:origin", ns)
        assert origin is not None, "each event must contain one origin"
        time_value = origin.findtext("q:time/q:value", namespaces=ns)
        assert time_value, "origin time is missing"
        station_count_text = origin.findtext(
            "q:quality/q:usedStationCount",
            namespaces=ns,
        )
        assert station_count_text is not None, "usedStationCount is missing"
        events.append((datetime.fromisoformat(time_value.replace('Z', '')), int(station_count_text)))
    return events


def test_quakeml_event_times_and_support_counts():
    events = _read_catalog()
    expected = [(datetime.fromisoformat(ts), count) for ts, count in EXPECTED]
    assert events == expected


def test_filtered_candidates_are_not_present():
    events = _read_catalog()
    actual_times = {event_time.isoformat(timespec="microseconds") for event_time, _ in events}
    assert "2019-07-04T19:00:09.670000" not in actual_times
    assert "2019-07-04T19:39:49.720000" not in actual_times
    assert "2019-07-04T19:59:43.370000" not in actual_times
