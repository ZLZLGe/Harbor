#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import io
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import numpy as np
from obspy import Stream, Trace, UTCDateTime
from obspy.core.event import Catalog, Event, EventDescription, Magnitude, Origin, ResourceIdentifier
from obspy.core.inventory import Channel, Inventory, Network, Site, Station


def parse_time(value: str | None) -> UTCDateTime | None:
    if value in (None, "", "open"):
        return None
    return UTCDateTime(value)


def normalize_location(value: str | None) -> str | None:
    if value is None:
        return None
    if value == "--":
        return ""
    return value


def matches_pattern(value: str, pattern: str | None) -> bool:
    if pattern in (None, "", "*"):
        return True
    return fnmatch.fnmatchcase(value, pattern)


def record_active(record_start: str | None, record_end: str | None, query_start: UTCDateTime | None, query_end: UTCDateTime | None) -> bool:
    start = parse_time(record_start)
    end = parse_time(record_end)
    if query_start is not None and end is not None and end < query_start:
        return False
    if query_end is not None and start is not None and start > query_end:
        return False
    return True


def build_inventory(dataset: dict[str, object], params: dict[str, list[str]]) -> Inventory:
    query_network = params.get("network", [None])[0]
    query_station = params.get("station", [None])[0]
    query_channel = params.get("channel", [None])[0]
    query_start = parse_time(params.get("starttime", [None])[0])
    query_end = parse_time(params.get("endtime", [None])[0])

    networks: dict[str, Network] = {}
    for station_record in dataset.get("stations", []):
        network_code = station_record["network"]
        station_code = station_record["station"]
        if not matches_pattern(network_code, query_network):
            continue
        if not matches_pattern(station_code, query_station):
            continue

        station_obj = Station(
            code=station_code,
            latitude=float(station_record["latitude"]),
            longitude=float(station_record["longitude"]),
            elevation=float(station_record.get("elevation_m", 0.0)),
            creation_date=parse_time(station_record.get("start_date")),
            site=Site(name=station_record.get("site_name", station_code)),
        )

        for channel_record in station_record.get("channels", []):
            if not matches_pattern(channel_record["code"], query_channel):
                continue
            if not record_active(channel_record.get("start_date"), channel_record.get("end_date"), query_start, query_end):
                continue
            channel = Channel(
                code=channel_record["code"],
                location_code=channel_record.get("location", ""),
                latitude=float(station_record["latitude"]),
                longitude=float(station_record["longitude"]),
                elevation=float(station_record.get("elevation_m", 0.0)),
                depth=float(channel_record.get("depth_m", 0.0)),
                azimuth=float(channel_record.get("azimuth_deg", 0.0)),
                dip=float(channel_record.get("dip_deg", -90.0)),
                sample_rate=float(channel_record["sample_rate_hz"]),
                start_date=parse_time(channel_record.get("start_date")),
                end_date=parse_time(channel_record.get("end_date")),
            )
            station_obj.channels.append(channel)

        if not station_obj.channels:
            continue

        network_obj = networks.setdefault(
            network_code,
            Network(code=network_code, stations=[], description=station_record.get("network_name", network_code)),
        )
        network_obj.stations.append(station_obj)

    return Inventory(networks=list(networks.values()), source=dataset.get("source", "Local Archive Mirror"))


def build_catalog(dataset: dict[str, object], params: dict[str, list[str]]) -> Catalog:
    query_start = parse_time(params.get("starttime", [None])[0])
    query_end = parse_time(params.get("endtime", [None])[0])
    query_min_mag = params.get("minmagnitude", [None])[0]
    query_event_id = params.get("eventid", [None])[0]
    min_mag = float(query_min_mag) if query_min_mag not in (None, "") else None

    events = []
    for event_record in dataset.get("events", []):
        if query_event_id and event_record["event_id"] != query_event_id:
            continue
        event_time = parse_time(event_record["time"])
        if query_start is not None and event_time < query_start:
            continue
        if query_end is not None and event_time > query_end:
            continue
        if min_mag is not None and float(event_record["magnitude"]) < min_mag:
            continue

        origin = Origin(
            time=event_time,
            latitude=float(event_record["latitude"]),
            longitude=float(event_record["longitude"]),
            depth=float(event_record["depth_km"]) * 1000.0,
        )
        magnitude = Magnitude(mag=float(event_record["magnitude"]), magnitude_type=event_record.get("magnitude_type", "Mw"))
        event = Event(resource_id=ResourceIdentifier(f"smi:local/{event_record['event_id']}"))
        event.origins = [origin]
        event.magnitudes = [magnitude]
        event.preferred_origin_id = origin.resource_id
        event.preferred_magnitude_id = magnitude.resource_id
        event.event_descriptions = [EventDescription(text=event_record["place"])]
        events.append(event)

    return Catalog(events=events)


def build_stream(dataset: dict[str, object], params: dict[str, list[str]]) -> Stream:
    query_network = params.get("network", [None])[0]
    query_station = params.get("station", [None])[0]
    query_location = normalize_location(params.get("location", [None])[0])
    query_channel = params.get("channel", [None])[0]
    query_start = parse_time(params.get("starttime", [None])[0])
    query_end = parse_time(params.get("endtime", [None])[0])

    traces = []
    for waveform_record in dataset.get("waveforms", []):
        location_code = normalize_location(waveform_record.get("location", "")) or ""
        if not matches_pattern(waveform_record["network"], query_network):
            continue
        if not matches_pattern(waveform_record["station"], query_station):
            continue
        if not matches_pattern(location_code, query_location):
            continue
        if not matches_pattern(waveform_record["channel"], query_channel):
            continue
        if not record_active(waveform_record["starttime"], waveform_record.get("endtime"), query_start, query_end):
            continue

        trace = Trace(data=np.asarray(waveform_record["data"], dtype=np.float32))
        trace.stats.network = waveform_record["network"]
        trace.stats.station = waveform_record["station"]
        trace.stats.location = location_code
        trace.stats.channel = waveform_record["channel"]
        trace.stats.starttime = parse_time(waveform_record["starttime"])
        trace.stats.sampling_rate = float(waveform_record["sampling_rate_hz"])
        traces.append(trace)

    return Stream(traces=traces)


class Handler(BaseHTTPRequestHandler):
    dataset: dict[str, object] = {}

    def log_message(self, format: str, *args: object) -> None:
        return

    def send_xml(self, payload: bytes) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/xml")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def send_mseed(self, payload: bytes) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/vnd.fdsn.mseed")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/healthz":
            payload = b"ok\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        params = parse_qs(parsed.query, keep_blank_values=True)
        if parsed.path == "/fdsnws/dataselect/1/query":
            stream = build_stream(self.dataset, params)
            buffer = io.BytesIO()
            stream.write(buffer, format="MSEED")
            self.send_mseed(buffer.getvalue())
            return

        if parsed.path == "/fdsnws/station/1/query":
            inventory = build_inventory(self.dataset, params)
            buffer = io.BytesIO()
            inventory.write(buffer, format="STATIONXML")
            self.send_xml(buffer.getvalue())
            return

        if parsed.path == "/fdsnws/event/1/query":
            catalog = build_catalog(self.dataset, params)
            buffer = io.BytesIO()
            catalog.write(buffer, format="QUAKEML")
            self.send_xml(buffer.getvalue())
            return

        self.send_response(404)
        self.end_headers()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--port", type=int, default=18080)
    args = parser.parse_args()

    Handler.dataset = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
