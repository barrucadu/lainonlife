from flask import Blueprint, Flask
from flask import (
    current_app,
    make_response,
    send_file,
)

import json
import os
import random
import requests

blueprint = Blueprint("site", __name__)


def serve(
    port=3000, httpdir="/srv/http", icecast="http://localhost:8000/", channels={}
):
    """Run the web server."""

    app = Flask(__name__)

    app.config["http_dir"] = httpdir
    app.config["channels"] = channels
    app.config["icecast"] = icecast

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


@blueprint.route("/playlist/<channel>.json", methods=["GET"])
def playlist(channel):
    if channel in current_app.config["channels"]:
        return playlist_for(channel)

    return send_file(in_http_dir("404.html")), 404


@blueprint.route("/metrics", methods=["GET"])
def metrics():
    response = make_response("\n".join(get_listener_metrics()), 200)
    response.mimetype = "text/plain"
    return response


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


def get_listener_metrics():
    def line(channel, fmt, count):
        return f'listeners{{channel="{channel}",format="{fmt}"}} {count}'

    f = requests.get(f"{current_app.config['icecast']}/status-json.xsl")
    f.raise_for_status()
    icecast_metrics = f.json()

    prometheus_metrics = [
        "# HELP listeners Listener count",
        "# TYPE listeners gauge",
    ]
    for channel in current_app.config["channels"]:
        for source in icecast_metrics["icestats"]["source"]:
            if "server_name" not in source:
                continue
            for fmt in ["mp3", "ogg"]:
                if source["server_name"] == f"[mpd] {channel} ({fmt})":
                    prometheus_metrics.append(
                        line(channel, fmt, source.get("listeners", 0))
                    )
    return prometheus_metrics
