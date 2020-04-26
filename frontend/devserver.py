#!/usr/bin/env python3
import os
import requests
from flask import Flask, request, send_from_directory, Response

url_to_proxy = "https://lainon.life"

server = Flask(__name__)


@server.route("/")
def handle_root():
    return send_from_directory("_site", "index.html")


@server.route("/<path:_>")
def handle_request(_):
    path = request.path

    if os.path.exists("_site" + path):
        server.logger.info("serving locally: " + path)
        return send_from_directory("_site", path[1:])

    # try to proxy not existing files
    server.logger.info("proxying: " + path)
    response = requests.get(url_to_proxy + path)

    if response.status_code != 200:
        # replicate the status code of the remote server
        flask_response = Response()
        flask_response.status_code = response.status_code
        return flask_response

    # send files
    mime = response.headers["content-type"]
    flask_response = Response(response.content, mimetype=mime)
    flask_response.status_code = response.status_code
    return flask_response


server.run()
