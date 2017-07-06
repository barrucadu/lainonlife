#!/usr/bin/env python3

"""Radio scheduling program.

Usage:
  schedule.py [--host=HOST] PORT

Options:
  --host=HOST  Hostname of MPD [default: localhost]
  -h --help    Show this text

Takes a port number, and does the following:

1. Sets the play order to normal, looping.
2. Clears all music before the cursor position in the playlist.
3. Appends a roughly three-hour block of music to the end of the playlist in this format:
   a. A transition track
   b. A full album
   c. Enough random tracks to make up the difference.

The new segment may be a little shorter if an exact fit is not possible, but in practice it will
be close.

Why do this?  Listening to entire albums in order is nice, as tracks in an album often build off
each other.  On the other hand, variety is also nice!

"""

from docopt import docopt
from mpd import MPDClient
from random import shuffle
from time import time


def album_sticker_get(client, album, sticker):
    """Gets a sticker associated with an album."""

    # I am pretty sure that MPD only implements stickers for songs, so
    # the sticker gets attached to the first song in the album.
    tracks = client.find("album", album)
    if len(tracks) == 0:
        return

    return client.sticker_get("song", tracks[0]["file"], "album_" + sticker)


def album_sticker_set(client, album, sticker, val):
    """Sets a sticker associated with an album."""

    # I am pretty sure that MPD only implements stickers for songs, so
    # the sticker gets attached to the first song in the album.
    tracks = client.find("album", album)
    if len(tracks) == 0:
        return

    return client.sticker_set("song", tracks[0]["file"], "album_" + sticker, val)


def pick_transition(client):
    """Picks a transition track."""

    all_transitions = list(filter(lambda t: "directory" not in t, client.listall("transitions")))

    shuffle(all_transitions)

    transition = all_transitions[0]["file"]
    transition_dur = int(client.count("file", transition)["playtime"])

    return transition, transition_dur


def pick_album(client, dur):
    """Picks a random album which fits in the duration."""

    # Get all albums
    albums = client.list("album")
    all_albums = list(filter(lambda a: a not in ["", "Lainchan Radio Transitions"], albums))

    # Group albums by when they were last scheduled
    albums_by_last_scheduled = {}
    last_scheduled_times = []
    for album in all_albums:
        # Get the last scheduled time, defaulting to 0
        try:
            last_scheduled = int(album_sticker_get(client, album, "last_scheduled"))
        except:
            last_scheduled = 0

        # Put the album into the appropriate bucket
        if last_scheduled in albums_by_last_scheduled:
            albums_by_last_scheduled[last_scheduled].append(album)
        else:
            albums_by_last_scheduled[last_scheduled] = [album]
            last_scheduled_times.append(last_scheduled)

    # Pick the 10 oldest times
    last_scheduled_times.sort()
    least_recently_scheduled_albums = []
    for last_scheduled in last_scheduled_times[:10]:
        least_recently_scheduled_albums.extend(albums_by_last_scheduled[last_scheduled])

    # Pick the album to play out of the 10 oldest times
    shuffle(least_recently_scheduled_albums)
    for album in least_recently_scheduled_albums:
        album_dur = int(client.count("album", album)["playtime"])
        if album_dur <= dur:
            return album, album_dur

    # Really, this should never be reached.  We have enough variety in music.
    album = all_albums[0]
    album_dur = int(client.count("album", album)["playtime"])
    return album, album_dur


def pick_tracks(client, chosen_album, dur):
    """Attempts to pick a list of tracks to fill the given time.

    Radio transitions and the chosen album are excluded from the list.

    Because retrieving and operating over the list of all tracks is expensive, this does not try
    more than once.  It uses the simple greedy algorithm, and so may exceed the limit.
    """

    all_tracks = client.list("file")

    shuffle(all_tracks)

    chosen = []
    remaining = dur
    for t in all_tracks:
        album = client.list("album", "file", t)[0]
        duration = int(client.count("file", t)["playtime"])
        if album in [chosen_album, "Lainchan Radio Transitions"] or duration > remaining:
            continue
        else:
            chosen.append(t)
            remaining = remaining - duration

    return chosen, dur - remaining


def schedule_radio(client, target_dur=3*60*60):
    """Schedule music.

    Keyword arguments:
    target_dur -- the target duration to fill.
    """

    # Pick a transition and two albums
    transition, transition_dur = pick_transition(client)
    album, album_dur = pick_album(client, target_dur)

    # Determine how much time is remaining in the two-hour slot
    time_remaining = target_dur - transition_dur - album_dur

    # Pick a list of tracks to fill the gap
    tracks, tracks_dur = pick_tracks(client, album, time_remaining)

    # Some stats first
    print("Transition: {} ({}s)".format(transition, transition_dur))
    print("Album: {} ({}s)".format(album, album_dur))
    print("Tracks: #{} ({}s)".format(len(tracks), tracks_dur))
    print()
    print("Target duration: {}s".format(target_dur))
    print("Actual duration: {}s".format(transition_dur + album_dur + tracks_dur))
    print("Difference: {}s".format(time_remaining - tracks_dur))

    # Set playback to in-order repeat
    client.random(0)
    client.repeat(1)

    # Add tracks
    client.add(transition)
    client.findadd("album", album)
    for t in tracks:
        client.add(t)

    # Update the last_scheduled time of the album
    album_sticker_set(client, album, "last_scheduled", int(time()))

    # Delete up to the current track, minus 10 tracks (for the web
    # playlist)
    status = client.status()
    if "song" in status:
        client.delete((0, max(0, int(status["song"]) - 10)))


if __name__ == "__main__":
    args = docopt(__doc__)

    try:
        args["PORT"] = int(args["PORT"])
    except:
        print("PORT must be an integer")
        exit(1)

    try:
        client = MPDClient()
        client.connect(args["--host"], args["PORT"])
    except:
        print("could not connect to MPD")
        exit(2)

    client.update()
    schedule_radio(client)
