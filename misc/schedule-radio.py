#!/usr/bin/env python3

# Radio scheduling program!  Takes a port number, and does the following:
#  1. Sets the play order to normal, looping.
#  2. Clears all music before the cursor position in the playlist.
#  3. Appends a roughly four-hour block of music to the end of the playlist in this format:
#     a. A transition track
#     b. A full album
#     c. Enough random tracks to make up the difference.
#     d. A full album
#
# The new segment may be a little shorter or longer if an exact fit is not possible, but in practice
# it will be close.
#
# Why do this?  Listening to entire albums in order is nice, as tracks in an album often build off
# each other.  On the other hand, variety is also nice!

from mpd import MPDClient
from random import shuffle
import sys

def pick_transition(client):
    """Picks a transition track."""

    all_transitions = list(filter(lambda t: "directory" not in t, client.listall("transitions")))

    shuffle(all_transitions)

    transition = all_transitions[0]["file"]
    transition_dur = int(client.count("file", transition)["playtime"])

    return transition, transition_dur


def pick_albums(client, dur, tries=3):
    """Attempts to pick two albums which fit into a two-hour slot.

    Keyword arguments:
    tries -- the number of attempts before giving up and returning a pair of albums over the duration limit (default: 3)
    """

    albums = client.list("album")
    all_albums = list(filter(lambda a: a not in ["", "Lainchan Radio Transitions"], albums))

    def helper(tries):
        shuffle(all_albums)

        album1 = all_albums[0]
        album2 = all_albums[1]

        album1_dur = int(client.count("album", album1)["playtime"])
        album2_dur = int(client.count("album", album2)["playtime"])

        # If it's over two hours, and we have remaining tries, try again!
        if tries > 0 and album1_dur + album2_dur > dur:
            return helper(tries-1)
        return album1, album2, album1_dur, album2_dur

    return helper(tries)


def pick_tracks(client, album1, album2, dur):
    """Attempts to pick a list of tracks to fill the given time.

    Radio transitions and the two chosen albums are excluded from the list.

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
        if album in [album1, album2, "Lainchan Radio Transitions"] or duration > remaining:
            continue
        else:
            chosen.append(t)
            remaining = remaining - duration

    return chosen, dur - remaining


def schedule_radio(client, target_dur=4*60*60):
    """Schedule music.

    Keyword arguments:
    target_dur -- the target duration to fill.
    """

    # Pick a transition and two albums
    transition, transition_dur = pick_transition(client)
    album1, album2, album1_dur, album2_dur = pick_albums(client, target_dur)

    # Determine how much time is remaining in the two-hour slot
    time_remaining = target_dur - transition_dur - album1_dur - album2_dur

    # Pick a list of tracks to fill the gap
    tracks, tracks_dur = pick_tracks(client, album1, album2, time_remaining)

    # Some stats first
    print("Transition: {} ({}s)".format(transition, transition_dur))
    print("Album 1: {} ({}s)".format(album1, album1_dur))
    print("Album 2: {} ({}s)".format(album2, album2_dur))
    print("Tracks: #{} ({}s)".format(len(tracks), tracks_dur))
    print()
    print("Target duration: {}s".format(target_dur))
    print("Actual duration: {}s".format(transition_dur + album1_dur + album2_dur + tracks_dur))
    print("Difference: {}s".format(time_remaining - tracks_dur))

    # Set playback to in-order repeat
    client.random(0)
    client.repeat(1)

    # Add tracks
    client.add(transition)
    client.findadd("album", album1)
    for t in tracks:
        client.add(t)
    client.findadd("album", album2)

    # Delete up to the current track
    status = client.status()
    if "song" in status:
        client.delete((0,int(status["song"])))


if __name__ == "__main__":
    try:
        port = int(sys.argv[1])
    except:
        print("USAGE: schedule-radio.py <port number>")
        exit(1)

    try:
        client = MPDClient()
        client.connect("localhost", port)
    except:
        print("Could not connect to MPD.")
        exit(2)

    schedule_radio(client)
