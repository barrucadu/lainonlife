from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from mpd import MPDClient

import atexit
import datetime
import influxdb


def start_stream_monitor(channelsjson, influxdbcfg):
    """Start monitoring the streams."""

    # Cached channel data
    channels = {}
    for c in channelsjson.keys():
        if "mpd_host" in channelsjson[c] and "mpd_port" in channelsjson[c]:
            channels[c] = channelsjson[c]
            channels[c]["client"] = None
            channels[c]["cache"] = ("Not connected to MPD yet.", 500)

    # Update caches regularly
    bg_scheduler = BackgroundScheduler()
    bg_scheduler.start()

    playlist_update_counter = 0

    influx_client = influxdb.InfluxDBClient(
        host=influxdbcfg["host"],
        port=influxdbcfg["port"],
        username=influxdbcfg["user"],
        password=influxdbcfg["pass"],
        database=influxdbcfg["db"],
    )

    def playlist_info_update_task():
        nonlocal channels, playlist_update_counter, influx_client

        for channel in channels:
            update_mpd_info(channel, channels[channel], influx_client)

    bg_scheduler.add_job(
        func=playlist_info_update_task,
        trigger=IntervalTrigger(seconds=1),
        id="playlist_update",
        name="Update [channel].json's",
        replace_existing=True,
    )

    # Shut down cleanly
    atexit.register(lambda: bg_scheduler.shutdown())

    # Return the state which will be mutated by the bg_scheduler
    return channels


###############################################################################
# MPD


def get_playlist_info(client, beforeNum=5, afterNum=5):
    status = client.status()
    song = int(status["song"])
    pllen = int(status["playlistlength"])

    def songsIn(fromPos, toPos):
        minId = max(0, min(pllen, fromPos))
        maxId = max(0, min(pllen, toPos))
        return client.playlistinfo("{}:{}".format(minId, maxId))

    def sanitise(song):
        good_fields = [
            "artist",
            "albumartist",
            "album",
            "track",
            "time",
            "date",
            "title",
        ]
        return {t: song[t] for t in good_fields if t in song}

    pinfo = {
        "before": list(map(sanitise, songsIn(song - beforeNum, song))),
        "current": list(map(sanitise, client.playlistinfo(song)))[0],
        "after": list(map(sanitise, songsIn(song + 1, song + afterNum + 1))),
        "elapsed": status["elapsed"],
    }
    pinfo["before"].reverse()

    return pinfo


def get_channel_listeners(channel, client):
    startTime = (datetime.datetime.now() - datetime.timedelta(hours=12)).replace(
        microsecond=0
    )

    try:
        max_res = client.query(
            "select max({}) from channel_listeners where time >= '{}Z'".format(
                channel, startTime.isoformat()
            )
        )
        last_res = client.query(
            "select {} as last from channel_listeners order by time desc limit 1".format(
                channel
            )
        )

        return {
            "peak": max_res.get_points().__next__()["max"],
            "current": last_res.get_points().__next__()["last"],
        }
    except Exception as e:
        # If there's an error just say there's only one listener (ie,
        # the current one)
        print(f"error talking to influxdb: {e.args[0]}")
        return {"peak": 1, "current": 1}


def update_mpd_info(channel, mpd, influx_client):
    try:
        mpd["client"].ping()
    except Exception:
        try:
            mpd["client"] = MPDClient()
            mpd["client"].connect(mpd["mpd_host"], mpd["mpd_port"])
            mpd["client"].ping()
        except Exception as e:
            print(e)
            mpd["cache"] = ("Could not connect to MPD.", 500)

    # okay, client (re-)connected
    report = get_playlist_info(mpd["client"])
    report["listeners"] = get_channel_listeners(channel, influx_client)

    mpd["cache"] = (report, 200)
