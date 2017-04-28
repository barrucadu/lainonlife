#!/usr/bin/env python3

# Radio and server metrics, for pretty graphs at https://lainon.life/graphs/.

from datetime import datetime
from influxdb import InfluxDBClient
import json, os, psutil, time, urllib

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


def get_format_list(snapshot):
    """Return the list of formats in a snapshot."""

    return {stream["format"] for stream in snapshot}


def get_channel_list(snapshot):
    """Return the list of channels in a snapshot."""

    return {stream["channel"] for stream in snapshot}


def get_upload_download():
    """Get the current upload, in bytes, since last boot."""

    psinfo = psutil.net_io_counters(pernic=True)["eno1"]
    return psinfo[0], psinfo[1]


def get_disk_used():
    """Get the disk usage, in bytes."""

    statinfo = os.statvfs("/")
    return statinfo.f_frsize * (statinfo.f_blocks - statinfo.f_bfree)


def get_format_listeners(snapshot, fmt):
    """Get the number of listeners on a specific format, across all channels."""

    return sum([stream["listeners"] for stream in snapshot if stream["format"] == fmt])


def get_channel_listeners(snapshot, channel):
    """Get the number of listeners on a specific channel, across all formats."""

    return sum([stream["listeners"] for stream in snapshot if stream["channel"] == channel])


def gather_metrics(now):
    """Gather metrics to send to InfluxDB."""

    snapshot = snapshot_icecast()
    formats  = get_format_list(snapshot)
    channels = get_channel_list(snapshot)
    up, down = get_upload_download()

    return [
        {"measurement": "network", "time": now, "fields": {
            "upload":   up,
            "download": down
        }},
        {"measurement": "disk", "time": now, "fields": {
            "used": get_disk_used(),
        }},
        {"measurement": "format_listeners", "time": now, "fields": {
            fmt: get_format_listeners(snapshot, fmt) for fmt in formats
        }},
        {"measurement": "channel_listeners", "time": now, "fields": {
            ch: get_channel_listeners(snapshot, ch) for ch in channels
        }}
    ]


if __name__ == "__main__":
    client = InfluxDBClient()

    # Ensure the database exists
    client.create_database("lainon.life")

    # We do this all in the same process to avoid the overhead of
    # launching a python interpreter every 30s, which appears to mess
    # with psutil's reporting of CPU usage.
    while True:
        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        print("Sending report for {}".format(now))
        metrics = gather_metrics(now)
        client.write_points(metrics, database="lainon.life")
        time.sleep(30)
