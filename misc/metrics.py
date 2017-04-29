#!/usr/bin/env python3

# Radio and server metrics, for pretty graphs at https://lainon.life/graphs/.

from datetime import datetime
from influxdb import InfluxDBClient
import json, os, psutil, time, urllib

def snapshot_icecast():
    """Return a snapshot of the icecast listener status."""

    f = urllib.request.urlopen("http://localhost:8000/status-json.xsl")
    stats = json.loads(f.read().decode("utf8"))

    snapshot = []
    for src in stats["icestats"]["source"]:
        snapshot.append({
            "channel": src["server_name"][:-6],
            "format": src["server_name"][-4:][:-1],
            "listeners": src["listeners"]
        })

    formats  = {stream["format"]  for stream in snapshot}
    channels = {stream["channel"] for stream in snapshot}

    return snapshot, formats, channels


def icecast_metrics_list():
    """Return a list of icecast metrics, or the empty list if it fails."""

    try:
        snapshot, formats, channels = snapshot_icecast()
    except:
        return []

    return [
        {"measurement": "format_listeners", "time": now, "fields": {
            fmt: sum([stream["listeners"] for stream in snapshot if stream["format"] == fmt]) for fmt in formats
        }},
        {"measurement": "channel_listeners", "time": now, "fields": {
            ch: sum([stream["listeners"] for stream in snapshot if stream["channel"] == ch]) for ch in channels
        }}
    ]


def network_metrics():
    """Get the current upload, in bytes, since last boot."""

    psinfo = psutil.net_io_counters(pernic=True)["eno1"]
    return {
        "up":   psinfo[0],
        "down": psinfo[1]
    }


def cpu_metrics():
    """Get the percentage usage of every cpu."""

    cpus = psutil.cpu_percent(percpu=True)
    return {"core{}".format(n): percent for n, percent in enumerate(cpus)}


def disk_metrics():
    """Get the disk usage, in bytes."""

    statinfo = os.statvfs("/")
    return {"used": statinfo.f_frsize * (statinfo.f_blocks - statinfo.f_bfree)}


def memory_metrics():
    """Get the RAM and swap usage, in bytes."""

    vminfo = psutil.virtual_memory()
    swinfo = psutil.swap_memory()

    return {
        "vm_used":    vminfo[3],
        "vm_buffers": vminfo[7],
        "vm_cached":  vminfo[8],
        "swap_used":  swinfo[1],
        "vm_used_no_buffers_cache": vminfo[3] - vminfo[7] - vminfo[8]
    }


def gather_metrics(now):
    """Gather metrics to send to InfluxDB."""

    metrics = icecast_metrics_list()
    metrics.extend([
        {"measurement": "network", "time": now, "fields": network_metrics()},
        {"measurement": "disk",    "time": now, "fields": disk_metrics()},
        {"measurement": "cpu",     "time": now, "fields": cpu_metrics()},
        {"measurement": "memory",  "time": now, "fields": memory_metrics()}
    ])

    return metrics


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
