from flask import Blueprint, Flask
from flask import (
    current_app,
    make_response,
    request,
    send_file,
)

import json
import os
import random
import time

blueprint = Blueprint("site", __name__)


def serve(port=3000, httpdir="/srv/http", channels={}):
    """Run the web server."""

    app = Flask(__name__)

    app.config["http_dir"] = httpdir
    app.config["channels"] = channels

    app.register_blueprint(blueprint)

    # blueprints cannot handle 404 or 405 errors, so stick this on the
    # app directly.
    @app.errorhandler(404)
    def page_not_found(error):
        return send_file(in_http_dir("404.html"))

    return app.run(port=port)


###############################################################################
# The basic site


@blueprint.route("/background", methods=["GET"])
def background():
    return random_file_from(in_http_dir("backgrounds"))


@blueprint.route("/upload/bump", methods=["POST"])
def upload_bump():
    if "file" in request.files:
        save_file(request.files["file"])

    if "url" in request.form:
        save_form({"url": request.form["url"]}, suffix="url")

    return send_file(in_http_dir("thankyou.html"))


@blueprint.route("/upload/request", methods=["POST"])
def upload_request():
    fields = ["artist", "album", "url", "notes", "channel"]
    if "artist" in request.form and "album" in request.form:
        save_form(
            {t: request.form[t] for t in fields if t in request.form}, suffix="request"
        )

    return send_file(in_http_dir("thankyou.html"))


@blueprint.route("/playlist/<channel>.json", methods=["GET"])
def playlist(channel):
    if channel in current_app.config["channels"]:
        return playlist_for(channel)

    return send_file(in_http_dir("404.html")), 404


###############################################################################
# Utility functions


def in_http_dir(path):
    """Return a path in the HTTP directory."""

    return os.path.join(current_app.config["http_dir"], path)


def random_file_from(dname, cont=None):
    """Serve a random file from a directory, excluding hidden files and index.html."""

    files = [
        f for f in os.listdir(dname) if not f.startswith(".") and not f == "index.html"
    ]
    if not files:
        return send_file(in_http_dir("404.html")), 404

    fname = random.choice(files)
    if not cont:
        return send_file(os.path.join(dname, fname), cache_timeout=0)

    return cont(fname)


def playlist_for(channel):
    """Return the playlist of the given channel, as JSON."""

    pinfo = current_app.config["channels"][channel]["cache"]
    resp = make_response(json.dumps(pinfo[0]), pinfo[1])
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
        with open(
            os.path.join(in_http_dir("upload"), "{}-{}".format(fname, suffix)), "w"
        ) as f:
            for k, v in fm.items():
                if v:
                    f.write("{}: {}\n".format(k, v))
