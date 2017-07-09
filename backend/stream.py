from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from collections import namedtuple
from mpd import MPDClient

import atexit
import json
import requests as make_requests
import time

# local imports
import database as db

LivestreamTrack = namedtuple('LivestreamTrack', ['artist', 'title', 'first_seen'])


def start_stream_monitor(channelsjson):
    """Start monitoring the streams."""

    # Cached channel data
    channels = {}
    for c in channelsjson.keys():
        if "mpdHost" in channelsjson[c] and "mpdPort" in channelsjson[c]:
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

    def playlist_info_update_task():
        nonlocal channels, livestream, playlist_update_counter

        for channel in channels:
            if livestream['active'] and channel == livestream['CHANNEL']:
                playlist_update_counter = (playlist_update_counter + 1) % 5
                if playlist_update_counter == 1:
                    update_livestream_info(channels, livestream)
                else:
                    continue
            else:
                update_mpd_info(channels[channel])

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
        "stream_data": {"live": False}
    }
    pinfo["before"].reverse()

    return pinfo


def update_mpd_info(channel):
    try:
        channel["client"].ping()
    except:
        try:
            channel["client"] = MPDClient()
            channel["client"].connect(channel["mpdHost"], channel["mpdPort"])
            channel["client"].ping()
        except Exception as e:
            print(e)
            channel["cache"] = ("Could not connect to MPD.", 500)
            return

    # okay, client (re-)connected
    p_info = get_playlist_info(channel["client"])
    channel["cache"] = (p_info, 200)


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
        'album': '🎵 L I V E S T R E A M 🎵'
    }

    stream_data = {
        'dj_name': '',
        'dj_pic': '',
        'stream_desc': '',
        'live': livestream['active']
    }

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
                for k in status_metadata:
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
        'stream_data': stream_data
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
