from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from mpd import MPDClient

import atexit
import requests


def start_stream_monitor(channelsjson, prometheus):
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

    def playlist_info_update_task():
        nonlocal channels, playlist_update_counter, prometheus

        listeners = get_channel_listeners(channels, prometheus)
        for channel in channels:
            update_mpd_info(channel, channels[channel], listeners[channel])

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


def get_channel_listeners(channels, prometheus):
    out = {channel: {"peak": 1, "current": 1} for channel in channels}

    try:
        r = requests.get(
            f"{prometheus}api/v1/query", params={"query": "sum(listeners) by (channel)"}
        )
        r.raise_for_status()
        current = r.json()

        r = requests.get(
            f"{prometheus}api/v1/query",
            params={"query": "max_over_time(sum(listeners) by (channel)[12h:1m])"},
        )
        r.raise_for_status()
        peak = r.json()

        for channel in channels:
            for stat in current["data"]["result"]:
                if stat["metric"]["channel"] == channel:
                    out[channel]["current"] = stat["value"][1]
            for stat in peak["data"]["result"]:
                if stat["metric"]["channel"] == channel:
                    out[channel]["peak"] = stat["value"][1]
    except Exception as e:
        print(f"error talking to prometheus: {e.args[0]}")

    return out


def update_mpd_info(channel, mpd, listeners):
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
    report["listeners"] = listeners

    mpd["cache"] = (report, 200)
