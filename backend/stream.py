from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from collections import namedtuple
from mpd import MPDClient

import atexit
import datetime
import influxdb
import json
import requests as make_requests
import time

# local imports
import database as db

LivestreamTrack = namedtuple('LivestreamTrack', ['artist', 'title', 'first_seen'])


def start_stream_monitor(channelsjson, influxdbcfg):
    """Start monitoring the streams."""

    # Cached channel data
    channels = {}
    for c in channelsjson.keys():
        if "mpd_host" in channelsjson[c] and "mpd_port" in channelsjson[c]:
            channels[c] = channelsjson[c]
            channels[c]["client"] = None
            channels[c]["cache"]  = ("Not connected to MPD yet.", 500)

    # Cached livestream data
    livestream = db.load_pickle({
        'active':      False,
        'current_dj':  None,
        'last_played': [],
        'CHANNEL':     'cyberia',
    })
    livestream['STREAM_DELAY'] = 7

    # Update caches regularly
    bg_scheduler = BackgroundScheduler()
    bg_scheduler.start()

    playlist_update_counter = 0

    influx_client = influxdb.InfluxDBClient(
        host=influxdbcfg["host"],
        port=influxdbcfg["port"],
        username=influxdbcfg["user"],
        password=influxdbcfg["pass"],
        database=influxdbcfg["db"])

    def playlist_info_update_task():
        nonlocal channels, livestream, playlist_update_counter, influx_client

        for channel in channels:
            if livestream['active'] and channel == livestream['CHANNEL']:
                playlist_update_counter = (playlist_update_counter + 1) % 5
                if playlist_update_counter == 1:
                    update_livestream_info(channels, livestream)
                else:
                    continue
            else:
                update_mpd_info(channel, channels[channel], influx_client)

    bg_scheduler.add_job(func=playlist_info_update_task,
                         trigger=IntervalTrigger(seconds=1),
                         id='playlist_update',
                         name='Update [channel].json\'s',
                         replace_existing=True)

    # Shut down cleanly
    atexit.register(lambda: bg_scheduler.shutdown())
    atexit.register(lambda: db.save_pickle(livestream))

    # Return the state which will be mutated by the bg_scheduler
    return channels, livestream


###############################################################################
# MPD

def get_playlist_info(client, beforeNum=5, afterNum=5):
    status = client.status()
    song   = int(status["song"])
    pllen  = int(status["playlistlength"])

    def songsIn(fromPos, toPos):
        minId = max(0, min(pllen, fromPos))
        maxId = max(0, min(pllen, toPos))
        return client.playlistinfo("{}:{}".format(minId, maxId))

    def sanitise(song):
        good_fields = ["artist", "albumartist", "album", "track", "time", "date", "title"]
        return {t: song[t] for t in good_fields if t in song}

    pinfo = {
        "before":  list(map(sanitise, songsIn(song - beforeNum, song))),
        "current": list(map(sanitise, client.playlistinfo(song)))[0],
        "after":   list(map(sanitise, songsIn(song + 1, song + afterNum + 1))),
        "elapsed": status["elapsed"],
    }
    pinfo["before"].reverse()

    return pinfo


def get_channel_listeners(channel, client):
    startTime = (datetime.datetime.now() - datetime.timedelta(hours=12)).replace(microsecond=0)

    max_res  = client.query(
        'select max({}) from channel_listeners where time >= \'{}Z\''
        .format(channel, startTime.isoformat()))
    last_res = client.query(
        'select {} as last from channel_listeners order by time desc limit 1'
        .format(channel))

    try:
        return {
            "peak":    max_res.get_points().__next__()['max'],
            "current": last_res.get_points().__next__()['last']
        }
    except:
        # If there's an error just say there's only one listener (ie,
        # the current one)
        print("error: {} {}".format(max_res, last_res))
        return {"peak": 1, "current": 1}


def update_mpd_info(channel, mpd, influx_client):
    try:
        mpd["client"].ping()
    except:
        try:
            mpd["client"] = MPDClient()
            mpd["client"].connect(mpd["mpd_host"], mpd["mpd_port"])
            mpd["client"].ping()
        except Exception as e:
            print(e)
            mpd['cache'] = ("Could not connect to MPD.", 500)

    # okay, client (re-)connected
    report = get_playlist_info(mpd["client"])
    report["stream_data"] = {"live": False}
    report["listeners"] = get_channel_listeners(channel, influx_client)

    mpd['cache'] = (report, 200)


###############################################################################
# Icecast

def update_livestream_info(channels, livestream):
    # get current track info
    req_url = "http://127.0.0.1:8000/status-json.xsl"
    try:
        req_info = json.loads(make_requests.get(req_url).content.decode('utf-8'))
    except Exception as e:
        print(e)
        channels[livestream['CHANNEL']]["cache"] = ("Could not connect to stream.", 500)
        return

    status_metadata = {
        'artist': '',
        'title': '',
        'album': '🎵 L I V E S T R E A M 🎵',
        'listeners': {
            'current': 0
        }
    }

    stream_data = {
        'dj_name': '',
        'dj_pic': '',
        'stream_desc': '',
        'live': livestream['active']
    }

    current_listeners = 0

    # fill in with streamer info
    if stream_data['live']:
        dj_info = db.get_dj_info(livestream['current_dj'])
        if dj_info is not None:
            for k in dj_info:
                if k in stream_data:
                    stream_data[k] = dj_info[k]
            if 'stream_title' in dj_info and len(dj_info['stream_title']) > 0:
                status_metadata['album'] = dj_info['stream_title']

    # get the current metadata from icecast
    sources = req_info['icestats']['source']
    for source in sources:
        if livestream['CHANNEL'] in source['listenurl']:
            # if no server_type then fallback is active, if we're
            # streaming the server_type starts with audio a regular
            # mpd source's type is application/ogg
            if 'server_type' in source and 'audio' in source['server_type']:
                current_listeners += int(source['listeners'].strip())
                for k in ['artist', 'album', 'title']:
                    if k in source:
                        status_metadata[k] = source[k].strip()
                break

    # if no last track or it's not the same as the last track append
    if len(livestream['last_played']) == 0 or \
       livestream['last_played'][-1].title != status_metadata['title']:
        newest_track = LivestreamTrack(status_metadata['artist'],
                                       status_metadata['title'],
                                       time.time() + livestream['STREAM_DELAY'])
        livestream['last_played'].append(newest_track)
        # we only want 5 last tracks + current
        if len(livestream['last_played']) > 6:
            livestream['last_played'].pop(0)

    time_now = time.time()

    pinfo = {
        'current': status_metadata,
        'elapsed': int(time_now - livestream['last_played'][-1].first_seen),
        'before': [],
        'stream_data': stream_data,
        'listeners': {'current': current_listeners}
    }

    # populate before, radio expects tracks in most recent to oldest order
    # and their times need to be calculated because we don't know exact tracklengths
    indices = range(len(livestream['last_played']) - 2, -1, -1)
    for i in indices:
        track = livestream['last_played'][i]
        track_after = livestream['last_played'][i + 1]
        prev_metadata = {
            'artist': track.artist,
            'title': track.title,
            'time': (track_after.first_seen - track.first_seen)
        }
        pinfo['before'].append(prev_metadata)

    channels[livestream['CHANNEL']]["cache"] = (pinfo, 200)
