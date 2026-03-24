from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET


OUTPUT_PATH = Path("/root/hydrophone_inventory.xml")
NS = {"sx": "http://www.fdsn.org/xml/station/1"}


EXPECTED_CHANNELS = {
    ("HB", "PIER1", "10", "BDH"): {
        "latitude": "37.8082",
        "longitude": "-122.3985",
        "elevation": "4.0",
        "depth": "12.5",
        "azimuth": "0.0",
        "dip": "-90.0",
        "sample_rate": "100.0",
        "start": "2019-07-04T18:59:59.998300Z",
        "end": "2019-07-04T19:18:00.000000Z",
    },
    ("HB", "PIER1", "20", "BDH"): {
        "latitude": "37.8082",
        "longitude": "-122.3985",
        "elevation": "4.0",
        "depth": "27.0",
        "azimuth": "0.0",
        "dip": "-90.0",
        "sample_rate": "100.0",
        "start": "2019-07-04T19:07:30.000000Z",
        "end": "2019-07-04T19:59:59.998300Z",
    },
    ("HB", "MIDBK", "00", "BDH"): {
        "latitude": "37.8041",
        "longitude": "-122.3856",
        "elevation": "0.0",
        "depth": "18.0",
        "azimuth": "0.0",
        "dip": "-90.0",
        "sample_rate": "100.0",
        "start": "2019-07-04T19:12:00.000000Z",
        "end": "2019-07-04T19:47:15.000000Z",
    },
    ("HB", "OUTER", "00", "BDH"): {
        "latitude": "37.8127",
        "longitude": "-122.4098",
        "elevation": "-1.5",
        "depth": "32.0",
        "azimuth": "0.0",
        "dip": "-90.0",
        "sample_rate": "100.0",
        "start": "2019-07-04T19:25:45.000000Z",
        "end": "2019-07-04T19:40:30.000000Z",
    },
}


def load_inventory_root():
    assert OUTPUT_PATH.exists(), "Missing /root/hydrophone_inventory.xml"
    return ET.parse(OUTPUT_PATH).getroot()


def child_text(node, tag):
    child = node.find(f"sx:{tag}", NS)
    assert child is not None, f"Missing {tag}"
    return child.text


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def test_stationxml_has_expected_hierarchy():
    root = load_inventory_root()
    assert root.tag.endswith("FDSNStationXML")

    networks = root.findall("sx:Network", NS)
    assert len(networks) == 1

    network = networks[0]
    assert network.attrib["code"] == "HB"
    assert parse_time(network.attrib["startDate"]) == parse_time("2019-07-04T18:59:59.998300Z")
    assert parse_time(network.attrib["endDate"]) == parse_time("2019-07-04T19:59:59.998300Z")

    stations = network.findall("sx:Station", NS)
    station_codes = [station.attrib["code"] for station in stations]
    assert station_codes == ["MIDBK", "OUTER", "PIER1"]


def test_station_metadata_and_omissions():
    root = load_inventory_root()
    station_map = {
        station.attrib["code"]: station
        for station in root.findall("sx:Network/sx:Station", NS)
    }

    assert "INLET" not in station_map

    pier = station_map["PIER1"]
    assert parse_time(pier.attrib["startDate"]) == parse_time("2019-07-04T18:59:59.998300Z")
    assert parse_time(pier.attrib["endDate"]) == parse_time("2019-07-04T19:59:59.998300Z")
    assert float(child_text(pier, "Latitude")) == 37.8082
    assert float(child_text(pier, "Longitude")) == -122.3985
    assert float(child_text(pier, "Elevation")) == 4.0
    site = pier.find("sx:Site/sx:Name", NS)
    assert site is not None
    assert site.text == "Pier Alpha Array"


def test_channel_metadata_matches_expected_values():
    root = load_inventory_root()
    found = {}

    for network in root.findall("sx:Network", NS):
        network_code = network.attrib["code"]
        for station in network.findall("sx:Station", NS):
            station_code = station.attrib["code"]
            for channel in station.findall("sx:Channel", NS):
                key = (
                    network_code,
                    station_code,
                    channel.attrib["locationCode"],
                    channel.attrib["code"],
                )
                found[key] = {
                    "latitude": float(child_text(channel, "Latitude")),
                    "longitude": float(child_text(channel, "Longitude")),
                    "elevation": float(child_text(channel, "Elevation")),
                    "depth": float(child_text(channel, "Depth")),
                    "azimuth": float(child_text(channel, "Azimuth")),
                    "dip": float(child_text(channel, "Dip")),
                    "sample_rate": float(child_text(channel, "SampleRate")),
                    "start": parse_time(channel.attrib["startDate"]),
                    "end": parse_time(channel.attrib["endDate"]),
                }

    expected = {}
    for key, value in EXPECTED_CHANNELS.items():
        expected[key] = {
            "latitude": float(value["latitude"]),
            "longitude": float(value["longitude"]),
            "elevation": float(value["elevation"]),
            "depth": float(value["depth"]),
            "azimuth": float(value["azimuth"]),
            "dip": float(value["dip"]),
            "sample_rate": float(value["sample_rate"]),
            "start": parse_time(value["start"]),
            "end": parse_time(value["end"]),
        }

    assert found == expected
