#!/usr/bin/env python3

# Backend services.

from flask import Flask, make_response, request, send_file
from mpd import MPDClient
import json, os, random, sys, time

app = Flask(__name__)


def random_file_from(dname):
    """Serve a random file from a directory."""

    files = [f for f in os.listdir(dname) if not f.startswith('.')]
    if not files:
        return send_file("/srv/http/404.html"), 404

    fname = random.choice(files)
    return send_file(os.path.join(dname, fname), cache_timeout = 0)



def playlist_for(port, beforeNum=5, afterNum=5):
    """Return the playlist of the given MPD instance, as JSON."""

    try:
        client = MPDClient()
        client.connect("localhost", port)
    except:
        return "This should not have happened.", 500

    status = client.status()
    song   = int(status["song"])
    pllen  = int(status["playlistlength"])

    songsIn  = lambda fromPos, toPos: client.playlistinfo("{}:{}".format(max(0, min(pllen, fromPos)), max(0, min(pllen, toPos))))
    sanitise = lambda song: {t: song[t] for t in ["artist", "albumartist", "album", "track", "time", "date", "title"] if t in song}
    pinfo    = {
        "before":  list(map(sanitise, songsIn(song-beforeNum, song))),
        "current": list(map(sanitise, client.playlistinfo(song)))[0],
        "after":   list(map(sanitise, songsIn(song+1, song+afterNum+1))),
        "elapsed": status["elapsed"]
    }

    resp = make_response(json.dumps(pinfo), 200)
    resp.headers["Content-Type"] = "application/json"
    return resp


@app.route("/background", methods=["GET"])
def background():
    return random_file_from("/srv/http/backgrounds")


@app.route("/transition.mp3", methods=["GET"])
def transition():
    return random_file_from("/srv/radio/music/transitions")


@app.route("/upload/voice", methods=["POST"])
def upload_voice():
    fname = str(time.time())

    if "file" in request.files:
        f = request.files["file"]
        if f and f.filename:
            f.save(os.path.join("/srv/http/upload", fname + "-file"))

    if "url" in request.form:
        u = request.form["url"]
        if u:
            with open(os.path.join("/srv/http/upload", fname + "-url"), "w") as f:
                f.write(u)

    return send_file("/srv/http/thankyou.html")


@app.route("/playlist/<channel>.json", methods=["GET"])
def playlist(channel):
    # TODO: have some way of figuring this out automatically.  Check
    # systemd unit names?  Feels hacky...
    if channel == "everything":
        return playlist_for(6600)
    elif channel == "cyberia":
        return playlist_for(6601)
    elif channel == "swing":
        return playlist_for(6602)

    return send_file("/srv/http/404.html"), 404


@app.errorhandler(404)
def page_not_found(error):
    return send_file("/srv/http/404.html")


if __name__ == "__main__":
    try:
        port = int(sys.argv[1])
    except:
        print("USAGE: backend.py <port number>")
        exit(1)

    app.run(port=port)
