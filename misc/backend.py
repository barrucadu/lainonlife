#!/usr/bin/env python3

# Backend services.

from flask import Flask, send_file
import os, random, sys

app = Flask(__name__)

@app.route("/background")
def background():
    fname = random.choice(os.listdir("/srv/http/backgrounds/"))
    return send_file("/srv/http/backgrounds/{}".format(fname), cache_timeout = 0)

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
