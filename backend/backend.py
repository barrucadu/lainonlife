#!/usr/bin/env python3

"""Backend Services.

Usage:
  backend.py [--http-dir=PATH] [--config=FILE] PORT
  backend (-h | --help)

Options:
  --http-dir=PATH   Path of the web files    [default: /srv/http]
  --config=FILE     Site configuration file  [default: config.json]
  -h --help         Show this text

"""

from docopt import docopt

import json
import os

# local imports
import stream as stream
import web as web


if __name__ == "__main__":
    args = docopt(__doc__)

    try:
        try:
            with open(args["--config"], "r") as f:
                config = json.loads(f.read())
        except FileNotFoundError:
            raise Exception("--config must be a site configuration file")
        except json.decoder.JSONDecodeError:
            raise Exception("--config must be a site configuration file")
        try:
            args["PORT"] = int(args["PORT"])
        except ValueError:
            raise Exception("PORT must be an integer between 1 and 65535")
        if args["PORT"] < 1 or args["PORT"] > 65535:
            raise Exception("PORT must be an integer between 1 and 65535")
        if not os.path.isdir(args["--http-dir"]):
            raise Exception("--http-dir must be a directory")
    except Exception as e:
        print(e.args[0])
        exit(1)

    try:
        channels = stream.start_stream_monitor(config["channels"], config["influxdb"])
        web.serve(
            port=args["PORT"],
            httpdir=args["--http-dir"],
            channels=channels,
        )
    except Exception as e:
        print(f"could not bind to port: {e.args[0]}")
        exit(2)
