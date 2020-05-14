#!/usr/bin/env python3

"""Radio and server metrics, for pretty graphs at https://lainon.life/graphs/.

Usage:
  metrics.py [--icecast-host=HOST]
             [--icecast-port=PORT]
             [--influxdb-host=HOST]
             [--influxdb-port=PORT]
             [--influxdb-user=USER]
             [--influxdb-pass=PASS]
             [--influxdb-name=NAME]
  metrics.py (-h | --help)

Options:
  --icecast-host=HOST   Hostname of the Icecast HTTP server [default: localhost]
  --icecast-port=PORT   Port of the Icecast HTTP server     [default: 8000]

  --influxdb-host=HOST  Hostname of the InfluxDB API server [default: localhost]
  --influxdb-port=PORT  Port of the InfluxDB API server     [default: 8086]
  --influxdb-user=USER  Username of the InfluxDB API server [default: root]
  --influxdb-pass=PASS  Password of the InfluxDB API server [default: root]
  --influxdb-name=NAME  Name of the InfluxDB database       [default: lainon.life]

  -h --help             Show this text
"""

from datetime import datetime
from docopt import docopt
from influxdb import InfluxDBClient

import json
import os
import psutil
import subprocess
import time
import urllib


def snapshot_icecast(host, port):
    """Return a snapshot of the icecast listener status."""

    f = urllib.request.urlopen("http://{}:{}/status-json.xsl".format(host, port))
    stats = json.loads(f.read().decode("utf8"))

    snapshot = []
    for src in stats["icestats"]["source"]:
        if "server_name" in src and "listeners" in src:
            snapshot.append(
                {
                    "channel": src["server_name"][:-6].replace("[mpd] ", ""),
                    "format": src["server_name"][-4:][:-1],
                    "listeners": src["listeners"],
                }
            )

    formats = {stream["format"] for stream in snapshot}
    channels = {stream["channel"] for stream in snapshot}

    return snapshot, formats, channels


def icecast_metrics_list(now, host, port):
    """Return a list of icecast metrics, or the empty list if it fails."""

    try:
        snapshot, formats, channels = snapshot_icecast(host, port)
    except Exception:
        return []

    return [
        {
            "measurement": "format_listeners",
            "time": now,
            "fields": {
                fmt: sum(
                    [
                        stream["listeners"]
                        for stream in snapshot
                        if stream["format"] == fmt
                    ]
                )
                for fmt in formats
            },
        },
        {
            "measurement": "channel_listeners",
            "time": now,
            "fields": {
                ch: sum(
                    [
                        stream["listeners"]
                        for stream in snapshot
                        if stream["channel"] == ch
                    ]
                )
                for ch in channels
            },
        },
    ]


def network_metrics():
    """Get the current upload, in bytes, since last boot."""

    psinfo = psutil.net_io_counters(pernic=True)

    return {
        "{}_{}".format(iface, way): ifinfo[n]
        for iface, ifinfo in psinfo.items()
        for way, n in {"up": 0, "down": 1}.items()
    }


def cpu_metrics():
    """Get the percentage usage of every cpu."""

    cpus = psutil.cpu_percent(percpu=True)
    return {"core{}".format(n): percent for n, percent in enumerate(cpus)}


def disk_metrics():
    """Get the disk usage, in bytes."""

    def add_usage(ms, dus, dname):
        try:
            for i, val in enumerate(dus):
                if val.decode("utf-8") == dname:
                    ms[dname] = int(dus[i - 1])
        except Exception:
            pass

    # Overall disk usage
    statinfo = os.statvfs("/")
    metrics = {"used": statinfo.f_frsize * (statinfo.f_blocks - statinfo.f_bfree)}

    # Per-directory disk usage
    dirs = ["/home", "/nix", "/srv", "/tmp", "/var"]
    argv = ["du", "-s", "-b"]
    argv.extend(dirs)  # why doesn't python have an expression variant of this!?
    dus = subprocess.check_output(argv).split()
    for dname in dirs:
        add_usage(metrics, dus, dname)

    return metrics


def memory_metrics():
    """Get the RAM and swap usage, in bytes."""

    vminfo = psutil.virtual_memory()
    swinfo = psutil.swap_memory()

    return {
        "vm_used": vminfo[3],
        "vm_buffers": vminfo[7],
        "vm_cached": vminfo[8],
        "swap_used": swinfo[1],
        "vm_used_no_buffers_cache": vminfo[3] - vminfo[7] - vminfo[8],
    }


def gather_metrics(now, icecastHost, icecastPort):
    """Gather metrics to send to InfluxDB."""

    metrics = icecast_metrics_list(now, icecastHost, icecastPort)
    metrics.extend(
        [
            {"measurement": "network", "time": now, "fields": network_metrics()},
            {"measurement": "disk", "time": now, "fields": disk_metrics()},
            {"measurement": "cpu", "time": now, "fields": cpu_metrics()},
            {"measurement": "memory", "time": now, "fields": memory_metrics()},
        ]
    )

    return metrics


if __name__ == "__main__":
    args = docopt(__doc__)

    try:
        try:
            args["--icecast-port"] = int(args["--icecast-port"])
        except ValueError:
            raise Exception("--icecast-port must be an integer")
        try:
            args["--influxdb-port"] = int(args["--influxdb-port"])
        except ValueError:
            raise Exception("--influxdb-port must be an integer")
    except Exception as e:
        print(e.args[0])
        exit(1)

    client = InfluxDBClient(
        host=args["--influxdb-host"],
        port=args["--influxdb-port"],
        username=args["--influxdb-user"],
        password=args["--influxdb-pass"],
    )

    # Ensure the database exists
    client.create_database(args["--influxdb-name"])

    # We do this all in the same process to avoid the overhead of
    # launching a python interpreter every 30s, which appears to mess
    # with psutil's reporting of CPU usage.
    while True:
        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        print("Sending report for {}".format(now))
        metrics = gather_metrics(now, args["--icecast-host"], args["--icecast-port"])
        client.write_points(metrics, database=args["--influxdb-name"])
        time.sleep(30)
