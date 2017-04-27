#!/usr/bin/env python3

# Backend services.

from flask import Flask, request, send_file
import os, random, sys, time

app = Flask(__name__)


def random_file_from(dname):
    """Serve a random file from a directory."""

    fname = random.choice(os.listdir(dname))
    return send_file(os.path.join(dname, fname), cache_timeout = 0)


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
