#!/usr/bin/env python3

"""Backend Services.

Usage:
  backend.py [--http-dir=PATH] [--mpd-host=HOST] PORT
  backend.py (-h | --help)

Options:
  --http-dir=PATH   Path of the web files   [default: /srv/http]
  --mpd-host=HOST   Hostname of MPD         [default: localhost]
  -h --help         Show this text

"""

from docopt import docopt
from flask import Flask, make_response, redirect, request, send_file
from mpd import MPDClient
import json, os, random, time

app  = Flask(__name__)
args = docopt(__doc__)

# List of channels, populated with MPD client instances as playlists
# are requested.
channels = {"everything": {"port": 6600, "client": None},
            "cyberia":    {"port": 6601, "client": None},
            "swing":      {"port": 6602, "client": None},
            "cafe":       {"port": 6603, "client": None}}


def in_http_dir(path):
    """Return a path in the HTTP directory."""

    return os.path.join(args["--http-dir"], path)


def random_file_from(dname, cont=None):
    """Serve a random file from a directory."""

    files = [f for f in os.listdir(dname) if not f.startswith('.')]
    if not files:
        return send_file(in_http_dir("404.html")), 404

    fname = random.choice(files)
    if not cont:
        return send_file(os.path.join(dname, fname), cache_timeout = 0)

    return cont(fname)


def playlist_for(channel, beforeNum=5, afterNum=5):
    """Return the playlist of the given MPD instance, as JSON."""

    client = channels[channel]["client"]
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
    pinfo["before"].reverse()

    resp = make_response(json.dumps(pinfo), 200)
    resp.headers["Content-Type"] = "application/json"
    return resp


def save_file(fp, suffix="file"):
    """Save a file to the uploads directory."""

    fname = str(time.time())
    if fp and fp.filename:
        fp.save(os.path.join(in_http_dir("upload"), "{}-{}".format(fname, suffix)))


def save_form(fm, suffix="form"):
    """Save a form to the uploads directory."""

    fname = str(time.time())
    if fm:
        with open(os.path.join(in_http_dir("upload"), "{}-{}".format(fname, suffix)), "w") as f:
            for k, v in fm.items():
                if v:
                    f.write("{}: {}\n".format(k, v))


@app.route("/background", methods=["GET"])
def background():
    return random_file_from(in_http_dir("backgrounds"))


@app.route("/upload/bump", methods=["POST"])
def upload_bump():
    if "file" in request.files:
        save_file(request.files["file"])

    if "url" in request.form:
        save_form({"url": request.form["url"]}, suffix="url")

    return send_file(in_http_dir("thankyou.html"))


@app.route("/upload/request", methods=["POST"])
def upload_request():
    if "artist" in request.form and "album" in request.form:
        save_form({t: request.form[t] for t in ["artist", "album", "url", "notes"] if t in request.form}, suffix="request")

    return send_file(in_http_dir("thankyou.html"))


@app.route("/playlist/<channel>.json", methods=["GET"])
def playlist(channel):
    global channels

    if channel in channels:
        try:
            channels[channel]["client"].ping()
        except:
            try:
                channels[channel]["client"] = MPDClient()
                channels[channel]["client"].connect(args["--mpd-host"], channels[channel]["port"])
                channels[channel]["client"].ping()
            except:
                return "Could not connect to MPD.", 500
        return playlist_for(channel)

    return send_file(in_http_dir("404.html")), 404


@app.route("/webm.html", methods=["GET"])
def webm():
    tpl= '''
<!DOCTYPE html>
<html>
  <head>
    <title>{0}</title>
    <meta charset="UTF-8">
    <link rel="stylesheet" type="text/css" href="/webm.css">
  </head>
  <body>
    <a href="/webms/{1}">
      <video autoplay loop src="/webms/{1}">
        Your browser does not support HTML5 video.
      </video>
    </a>
  </body>
</html>
        '''
    return random_file_from(in_http_dir("webms"), lambda webm: tpl.format(webm[:-5], webm))


@app.route("/radio.html")
def redirect_radio():
    # This is in here so that I didn't need to edit the nginx config
    # and restart it, kicking everyone off the stream.  A downside of
    # proxying Icecast through nginx...
    return redirect("/")


@app.errorhandler(404)
def page_not_found(error):
    return send_file(in_http_dir("404.html"))


if __name__ == "__main__":
    try:
        try:
            args["PORT"] = int(args["PORT"])
        except:
            raise Exception("PORT must be an integer between 1 and 65535")
        if args["PORT"] < 1 or args["PORT"] > 65535:
            raise Exception("PORT must be an integer between 1 and 65535")
        if not os.path.isdir(args["--http-dir"]):
            raise Exception("--http-dir must be a directory")
    except Exception as e:
        print(e.args[0])
        exit(1)

    try:
        app.run(port=args["PORT"])
    except:
        print("could not bind to port")
        exit(2)
