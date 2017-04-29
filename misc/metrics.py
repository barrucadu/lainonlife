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


def get_upload_download():
    """Get the current upload, in bytes, since last boot."""

    psinfo = psutil.net_io_counters(pernic=True)["eno1"]
    return psinfo[0], psinfo[1]


def get_cpu_percents():
    """Get the percentage usage of every cpu."""

    return psutil.cpu_percent(percpu=True)


def get_disk_used():
    """Get the disk usage, in bytes."""

    statinfo = os.statvfs("/")
    return statinfo.f_frsize * (statinfo.f_blocks - statinfo.f_bfree)


def get_memory_used():
    """Get the RAM and swap usage, in bytes."""

    vminfo = psutil.virtual_memory()
    swinfo = psutil.swap_memory()

    return vminfo[3], vminfo[7], vminfo[8], swinfo[1]


def get_format_listeners(snapshot, fmt):
    """Get the number of listeners on a specific format, across all channels."""

    return sum([stream["listeners"] for stream in snapshot if stream["format"] == fmt])


def get_channel_listeners(snapshot, channel):
    """Get the number of listeners on a specific channel, across all formats."""

    return sum([stream["listeners"] for stream in snapshot if stream["channel"] == channel])


def gather_metrics(now):
    """Gather metrics to send to InfluxDB."""

    # Getting the icecast metrics may fail, as it sometimes produces
    # invalid json.
    try:
        snapshot, formats, channels = snapshot_icecast()
        metrics = [
            {"measurement": "format_listeners", "time": now, "fields": {
                fmt: get_format_listeners(snapshot, fmt) for fmt in formats
            }},
            {"measurement": "channel_listeners", "time": now, "fields": {
                ch: get_channel_listeners(snapshot, ch) for ch in channels
            }}
        ]
    except:
        metrics = []

    # The system metrics (shouldn't crash!)
    up, down = get_upload_download()
    cpus = get_cpu_percents()
    vmused, vmbuf, vmcache, swused = get_memory_used()

    metrics.extend([
        {"measurement": "network", "time": now, "fields": {
            "upload":   up,
            "download": down
        }},
        {"measurement": "disk", "time": now, "fields": {
            "used": get_disk_used(),
        }},
        {"measurement": "cpu", "time": now, "fields": {
            "core{}".format(n): percent for n, percent in enumerate(cpus)
        }},
        {"measurement": "memory", "time": now, "fields": {
            "vm_used":    vmused,
            "vm_used_no_buffers_cache": vmused - vmbuf - vmcache,
            "vm_buffers": vmbuf,
            "vm_cached":  vmcache,
            "swap_used":  swused
        }}
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
