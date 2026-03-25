import json
from collections import defaultdict
from pathlib import Path

from obspy import read, read_inventory


OUTPUT_PATH = Path("/root/network_availability.json")
INVENTORY_PATH = "/root/data/network_inventory.xml"
WAVEFORM_PATH = "/root/data/network_window.mseed"


def load_output():
    assert OUTPUT_PATH.exists(), "missing /root/network_availability.json"
    with OUTPUT_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def response_complete(channel):
    response = channel.response
    if response is None or response.instrument_sensitivity is None:
        return False
    return response.instrument_sensitivity.value is not None


def build_expected():
    inventory = read_inventory(INVENTORY_PATH)
    stream = read(WAVEFORM_PATH)
    network = inventory.networks[0]

    grouped_traces = defaultdict(list)
    for trace in stream:
        grouped_traces[
            (
                trace.stats.network,
                trace.stats.station,
                trace.stats.location,
                trace.stats.channel,
            )
        ].append(trace)

    stations = []
    channel_reports = []

    for station in sorted(network.stations, key=lambda item: item.code):
        station_channels = []
        for channel in sorted(station.channels, key=lambda item: (item.location_code or "", item.code)):
            key = (network.code, station.code, channel.location_code or "", channel.code)
            traces = grouped_traces.get(key, [])
            report = {
                "trace_id": f"{network.code}.{station.code}.{channel.location_code or ''}.{channel.code}",
                "location": channel.location_code or "",
                "channel": channel.code,
                "sample_rate_hz": float(traces[0].stats.sampling_rate if traces else channel.sample_rate),
                "trace_count": len(traces),
                "coverage_seconds": float(sum(trace.stats.npts / trace.stats.sampling_rate for trace in traces)),
                "has_waveform_data": bool(traces),
                "response_complete": response_complete(channel),
            }
            station_channels.append(report)
            channel_reports.append(report)

        stations.append(
            {
                "station": station.code,
                "channel_count": len(station_channels),
                "channels_with_waveforms": sum(1 for item in station_channels if item["has_waveform_data"]),
                "total_coverage_seconds": float(sum(item["coverage_seconds"] for item in station_channels)),
                "channels": station_channels,
            }
        )

    return {
        "network": network.code,
        "stations": stations,
        "summary": {
            "channel_count": len(channel_reports),
            "channels_with_waveforms": sum(1 for item in channel_reports if item["has_waveform_data"]),
            "channels_missing_response": sum(1 for item in channel_reports if not item["response_complete"]),
            "total_coverage_seconds": float(sum(item["coverage_seconds"] for item in channel_reports)),
        },
    }


def assert_close(left, right, tol=1e-6):
    assert abs(left - right) <= tol, f"{left} != {right}"


def test_output_contract_and_values():
    result = load_output()
    expected = build_expected()

    assert set(result.keys()) == {"network", "stations", "summary"}
    assert result["network"] == expected["network"]
    assert isinstance(result["stations"], list) and result["stations"], "stations must be a non-empty list"
    assert set(result["summary"].keys()) == {
        "channel_count",
        "channels_with_waveforms",
        "channels_missing_response",
        "total_coverage_seconds",
    }

    assert [station["station"] for station in result["stations"]] == [
        station["station"] for station in expected["stations"]
    ], "stations must be sorted by station code and match the inventory"

    for actual_station, expected_station in zip(result["stations"], expected["stations"], strict=True):
        assert set(actual_station.keys()) == {
            "station",
            "channel_count",
            "channels_with_waveforms",
            "total_coverage_seconds",
            "channels",
        }
        assert actual_station["station"] == expected_station["station"]
        assert actual_station["channel_count"] == expected_station["channel_count"]
        assert actual_station["channels_with_waveforms"] == expected_station["channels_with_waveforms"]
        assert_close(actual_station["total_coverage_seconds"], expected_station["total_coverage_seconds"])

        actual_channels = actual_station["channels"]
        expected_channels = expected_station["channels"]
        assert [item["trace_id"] for item in actual_channels] == [
            item["trace_id"] for item in expected_channels
        ], "channels must be sorted by (location, channel) and match the inventory"

        for actual_channel, expected_channel in zip(actual_channels, expected_channels, strict=True):
            assert set(actual_channel.keys()) == {
                "trace_id",
                "location",
                "channel",
                "sample_rate_hz",
                "trace_count",
                "coverage_seconds",
                "has_waveform_data",
                "response_complete",
            }
            assert actual_channel["trace_id"] == expected_channel["trace_id"]
            assert actual_channel["location"] == expected_channel["location"]
            assert actual_channel["channel"] == expected_channel["channel"]
            assert actual_channel["trace_count"] == expected_channel["trace_count"]
            assert actual_channel["has_waveform_data"] == expected_channel["has_waveform_data"]
            assert actual_channel["response_complete"] == expected_channel["response_complete"]
            assert_close(actual_channel["sample_rate_hz"], expected_channel["sample_rate_hz"])
            assert_close(actual_channel["coverage_seconds"], expected_channel["coverage_seconds"])

    assert result["summary"]["channel_count"] == expected["summary"]["channel_count"]
    assert result["summary"]["channels_with_waveforms"] == expected["summary"]["channels_with_waveforms"]
    assert result["summary"]["channels_missing_response"] == expected["summary"]["channels_missing_response"]
    assert_close(result["summary"]["total_coverage_seconds"], expected["summary"]["total_coverage_seconds"])


def test_dataset_has_both_missing_data_and_missing_response_cases():
    expected = build_expected()
    channels = [
        channel
        for station in expected["stations"]
        for channel in station["channels"]
    ]

    assert any(not channel["has_waveform_data"] for channel in channels), "task data must include at least one inventory-only channel"
    assert any(not channel["response_complete"] for channel in channels), "task data must include at least one channel with incomplete response metadata"
