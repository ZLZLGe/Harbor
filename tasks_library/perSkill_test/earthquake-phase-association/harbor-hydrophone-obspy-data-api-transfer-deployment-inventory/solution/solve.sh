#!/bin/bash

set -euo pipefail

python3 <<'PY'
from collections import defaultdict
from csv import DictReader
from pathlib import Path

from obspy import UTCDateTime, read
from obspy.core.inventory import Channel, Inventory, Network, Site, Station


OUTPUT_PATH = "/root/hydrophone_inventory.xml"
DATA_DIR = Path("/root/data/packets")
DEPLOYMENTS_PATH = Path("/root/data/deployments.csv")


def load_deployments():
    with DEPLOYMENTS_PATH.open(newline="") as handle:
        return list(DictReader(handle))


def load_streams():
    stream = None
    for packet in sorted(DATA_DIR.glob("*.mseed")):
        packet_stream = read(str(packet))
        stream = packet_stream if stream is None else stream + packet_stream
    return stream


def channel_key(row):
    return row["network"], row["station"], row["location"], row["channel"]


deployments = load_deployments()
stream = load_streams()

rows_by_station = defaultdict(list)
for row in deployments:
    rows_by_station[(row["network"], row["station"])].append(row)

stations_by_network = defaultdict(list)

for (network_code, station_code), station_rows in sorted(rows_by_station.items()):
    channel_objects = []
    first_row = station_rows[0]

    for row in sorted(station_rows, key=lambda item: (item["location"], item["channel"])):
        net, sta, loc, cha = channel_key(row)
        matching = stream.select(network=net, station=sta, location=loc, channel=cha)
        if len(matching) == 0:
            continue

        deployment_start = UTCDateTime(row["planned_start"])
        deployment_end = UTCDateTime(row["planned_end"])
        data_start = min(trace.stats.starttime for trace in matching)
        data_end = max(trace.stats.endtime for trace in matching)

        start_time = max(deployment_start, data_start)
        end_time = min(deployment_end, data_end)
        if start_time >= end_time:
            continue

        sample_rates = {round(float(trace.stats.sampling_rate), 9) for trace in matching}
        if len(sample_rates) != 1:
            raise ValueError(f"Inconsistent sample rates for {net}.{sta}.{loc}.{cha}")
        sample_rate = sample_rates.pop()

        channel_objects.append(
            Channel(
                code=cha,
                location_code=loc,
                latitude=float(row["latitude"]),
                longitude=float(row["longitude"]),
                elevation=float(row["elevation_m"]),
                depth=float(row["depth_m"]),
                azimuth=float(row["azimuth_deg"]),
                dip=float(row["dip_deg"]),
                sample_rate=sample_rate,
                start_date=start_time,
                end_date=end_time,
            )
        )

    if not channel_objects:
        continue

    channel_objects.sort(key=lambda item: (item.location_code, item.code))
    station_start = min(channel.start_date for channel in channel_objects)
    station_end = max(channel.end_date for channel in channel_objects)

    station = Station(
        code=station_code,
        latitude=float(first_row["latitude"]),
        longitude=float(first_row["longitude"]),
        elevation=float(first_row["elevation_m"]),
        site=Site(name=first_row["site_name"]),
        channels=channel_objects,
        start_date=station_start,
        end_date=station_end,
    )
    stations_by_network[network_code].append(station)


networks = []
for network_code, station_list in sorted(stations_by_network.items()):
    station_list.sort(key=lambda item: item.code)
    network_start = min(station.start_date for station in station_list)
    network_end = max(station.end_date for station in station_list)
    networks.append(
        Network(
            code=network_code,
            stations=station_list,
            start_date=network_start,
            end_date=network_end,
        )
    )


inventory = Inventory(networks=networks, source="OpenAI Codex")
inventory.write(OUTPUT_PATH, format="STATIONXML", validate=True)
PY
