#!/usr/bin/env python3

"""Radio scheduling program.

Usage:
  album_times.py [--host=HOST] PORT

Options:
  --host=HOST  Hostname of MPD [default: localhost]
  -h --help    Show this text

Prints out the last scheduling time of every album.
"""

from datetime import datetime
from docopt import docopt
from mpd import MPDClient


def album_sticker_get(client, album, sticker):
    """Gets a sticker associated with an album."""

    # I am pretty sure that MPD only implements stickers for songs, so
    # the sticker gets attached to the first song in the album.
    tracks = client.find("album", album)
    if len(tracks) == 0:
        return

    return client.sticker_get("song", tracks[0]["file"], "album_" + sticker)


def list_albums(client):
    """Lists albums sorted by last play timestamp."""

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
        except ValueError:
            last_scheduled = 0

        # Put the album into the appropriate bucket
        if last_scheduled in albums_by_last_scheduled:
            albums_by_last_scheduled[last_scheduled].append(album)
        else:
            albums_by_last_scheduled[last_scheduled] = [album]
            last_scheduled_times.append(last_scheduled)

    # Pick the 10 oldest times
    last_scheduled_times.sort()
    for last_scheduled in last_scheduled_times:
        dt = datetime.utcfromtimestamp(last_scheduled)
        albums = albums_by_last_scheduled[last_scheduled]
        print("{}: {}".format(dt.strftime('%Y-%m-%d %H:%M:%S'), albums))


if __name__ == "__main__":
    args = docopt(__doc__)

    try:
        args["PORT"] = int(args["PORT"])
    except ValueError:
        print("PORT must be an integer")
        exit(1)

    try:
        client = MPDClient()
        client.connect(args["--host"], args["PORT"])
    except Exception as e:
        print(f"could not connect to MPD: {e.args[0]}")
        exit(2)

    list_albums(client)
