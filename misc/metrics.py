#!/usr/bin/env python3

# Radio and server metrics, for pretty graphs at https://lainon.life/graphs/.

from datetime import datetime
from influxdb import InfluxDBClient
import json
import psutil
import time
import urllib

def snapshot_icecast():
    """Return a snapshot of the icecast listener status."""

    f = urllib.request.urlopen("http://localhost:8000/status-json.xsl")
    stats = json.loads(f.read().decode("utf8"))

    channels = []
    for src in stats["icestats"]["source"]:
        channels.append({
            "channel": src["server_name"][:-6],
            "format": src["server_name"][-4:][:-1],
            "listeners": src["listeners"]
        })
    return channels


def get_up_rate(secs=5):
    """Get the current upload speed in B/s. Blocks for the duration.

    Keyword arguments:
    secs -- number of seconds to gather data for (default: 5)
    """

    then = time.time()
    up0  = psutil.net_io_counters(pernic=False)[0]
    time.sleep(secs)
    now = time.time()
    up1 = psutil.net_io_counters(pernic=False)[0]

    return (up1 - up0) / (now - then)


def get_format_listeners(snapshot, fmt):
    """Get the number of listeners on a specific format, across all channels."""

    listeners = 0
    for stream in snapshot:
        if stream["format"] == fmt:
            listeners += stream["listeners"]
    return listeners


def get_channel_listeners(snapshot, channel):
    """Get the number of listeners on a specific channel, across all formats."""

    listeners = 0
    for stream in snapshot:
        if stream["channel"] == channel:
            listeners += stream["listeners"]
    return listeners


if __name__ == "__main__":
    client = InfluxDBClient()

    # Ensure the database exists
    client.create_database("lainon.life")

    # Gather the metrics
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    snapshot = snapshot_icecast()
    metrics = [
        {"measurement": "upload_rate", "time": now, "fields": {
            "value": get_up_rate()
        }},
        {"measurement": "format_listeners", "time": now, "fields": {
            "ogg": get_format_listeners(snapshot, "ogg"),
            "mp3": get_format_listeners(snapshot, "mp3")
        }},
        {"measurement": "channel_listeners", "time": now, "fields": {
            "everything": get_channel_listeners(snapshot, "everything"),
        }}
    ]

    # Write the metrics
    client.write_points(metrics, database="lainon.life")
