#!/usr/bin/env python3

import jinja2
import json
import os
import sys


def amount(currency, num):
    return "{}{:.2f}".format(currency, num)


def mkdirp(path):
    sofar = ""
    bits = path.split("/")[:-1]
    for b in bits:
        sofar = sofar + b + "/"
        try:
            os.mkdir(sofar)
        except FileExistsError:
            pass


def rules_with_config(channels, config, out_dir="_site/", tpl_dir="templates/"):
    tpl_global_vars = {
        "channels": channels,
        "default_channel": config["default_channel"],
        "icecast_status_url": config["icecast_status_url"],
        "icecast_stream_url_base": config["icecast_stream_url_base"],
        "server_cost": amount(
            config["currency_symbol"],
            config["server_cost"]
        ),
    }

    def jinja2_for_dir(dir_name):
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader([dir_name, tpl_dir], followlinks=True),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True
        )
        env.globals = tpl_global_vars
        return env

    def rule(dir_name, router):
        try:
            files = os.listdir(dir_name)
        except FileNotFoundError:
            return
        for fname0 in files:
            fname = dir_name + "/" + fname0
            if fname[0] == ".":
                continue
            if fname[-4:] == ".tpl":
                env  = jinja2_for_dir(dir_name)
                tpl  = env.get_template(fname0)
                dest = out_dir + "/" + router(fname[:-4])
                mkdirp(dest)
                tpl.stream().dump(dest)
            else:
                try:
                    with open(fname, "rb") as inf:
                        dest = out_dir + "/" + router(fname)
                        mkdirp(dest)
                        with open(dest, "wb") as outf:
                            outf.write(inf.read())
                except IsADirectoryError:
                    rule(fname, router)

    return rule


if __name__ == "__main__":
    try:
        with open(sys.argv[1], "r") as f:
            config = json.loads(f.read())
    except:
        print("usage: build.py <config.json>")
        exit(1)

    rule = rules_with_config(config["channels"].keys(), config["template"])
    rule("js", lambda x: x)
    rule("css", lambda x: x)
    rule("pages", lambda x: x[6:])
    rule("static", lambda x: x[7:])
    rule("font-awesome/css", lambda x: x[13:])
    rule("font-awesome/fonts", lambda x: x[13:])
