#!/usr/bin/env python3

"""Backend Services.

Usage:
  backend.py serve   [--http-dir=PATH] [--config=FILE] PORT
  backend.py newuser USER
  backend.py newpass USER
  backend.py ban     USER
  backend.py unban   USER
  backend.py promote USER
  backend.py demote  USER
  backend (-h | --help)

Options:
  --http-dir=PATH   Path of the web files    [default: /srv/http]
  --config=FILE     Site configuration file  [default: config.json]
  -h --help         Show this text

Warning: TinyDB does not support concurrent access from multiple
processes, so it is not safe to execute any of these commands
(including "serve") concurrently.

"""

from docopt import docopt

import json
import os

# local imports
import database as db
import stream as stream
import web as web


def command_serve(args):
    """Start the web server."""

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
        db.make_superadmin()
        channels, livestream = stream.start_stream_monitor(
            config["channels"], config["influxdb"]
        )
        web.serve(
            port=args["PORT"],
            httpdir=args["--http-dir"],
            channels=channels,
            livestream=livestream,
        )
    except Exception as e:
        print(f"could not bind to port: {e.args[0]}")
        exit(2)


def command_newuser(args):
    """Create a new user."""

    new_user = db.make_user(args["USER"])
    if new_user is None:
        print('User "{}" already exists!'.format(args["USER"]))
        exit(1)

    print('User "{}" created with password "{}".'.format(*new_user))


def command_newpass(args):
    """Change the password of a user."""

    new_pass = db.change_password(args["USER"])
    print('Changed password to "{}".'.format(new_pass))


def command_ban(args):
    """Ban a user."""

    if args["USER"] == "superadmin":
        print("Cannot ban the superadmin!")
        exit(1)

    res = db.update_dj_status(args["USER"], "banned", True)
    if res is not None:
        print('User "{}" is now banned.'.format(args["USER"]))


def command_unban(args):
    """Unban a user."""

    res = db.update_dj_status(args["USER"], "banned", False)
    if res is not None:
        print('User "{}" is now unbanned.'.format(args["USER"]))


def command_promote(args):
    """Promote a user to admin."""

    res = db.update_dj_status(args["USER"], "admin", True)
    if res is not None:
        print('User "{}" is now an admin.'.format(args["USER"]))


def command_demote(args):
    """Demote an admin to user."""

    if args["USER"] == "superadmin":
        print("Cannot demote the superadmin!")
        exit(1)

    res = db.update_dj_status(args["USER"], "admin", False)
    if res is not None:
        print('User "{}" is no longer an admin.'.format(args["USER"]))


if __name__ == "__main__":
    args = docopt(__doc__)

    if args["serve"]:
        command_serve(args)
    elif args["newuser"]:
        command_newuser(args)
    elif args["newpass"]:
        command_newpass(args)
    elif args["ban"]:
        command_ban(args)
    elif args["unban"]:
        command_unban(args)
    elif args["promote"]:
        command_promote(args)
    elif args["demote"]:
        command_demote(args)
