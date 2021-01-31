#!/usr/bin/env python3

import json
import os

# local imports
import stream as stream
import web as web


if __name__ == "__main__":
    http_dir = os.getenv("HTTP_DIR", "/srv/http")
    icecast = os.getenv("ICECAST", "http://localhost:8000")
    prometheus = os.getenv("PROMETHEUS", "http://localhost:9090")

    try:
        try:
            with open(os.getenv("CONFIG", "config.json"), "r") as f:
                config = json.loads(f.read())
        except FileNotFoundError:
            raise Exception("$CONFIG must be a site configuration file")
        except json.decoder.JSONDecodeError:
            raise Exception("$CONFIG must be a site configuration file")
        try:
            port = int(os.getenv("PORT", "3000"))
        except ValueError:
            raise Exception("$PORT must be an integer between 1 and 65535")
        if port < 1 or port > 65535:
            raise Exception("$PORT must be an integer between 1 and 65535")
        if not os.path.isdir(http_dir):
            raise Exception("$HTTP_DIR must be a directory")
    except Exception as e:
        print(e.args[0])
        exit(1)

    try:
        channels = stream.start_stream_monitor(config["channels"], prometheus)
        web.serve(
            port=port,
            httpdir=http_dir,
            icecast=icecast,
            channels=channels,
        )
    except Exception as e:
        print(f"could not bind to port: {e.args[0]}")
        exit(2)
