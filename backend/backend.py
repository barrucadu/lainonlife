#!/usr/bin/env python3

"""Backend Services.

Usage:
  backend.py serve   [--http-dir=PATH] [--channels=FILE] PORT
  backend.py newuser USER
  backend.py newpass USER
  backend.py ban     USER
  backend.py unban   USER
  backend.py promote USER
  backend.py demote  USER
  backend (-h | --help)

Options:
  --http-dir=PATH   Path of the web files       [default: /srv/http]
  --channels=FILE   Channel configuration file  [default: channels.json]
  -h --help         Show this text

Warning: TinyDB does not support concurrent access from multiple
processes, so it is not safe to execute any of these commands
(including "serve") concurrently.

"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from collections import namedtuple
from docopt import docopt
from flask import Flask, make_response, redirect, request, send_file, render_template
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from mpd import MPDClient

import atexit
import json
import os
import random
import requests as make_requests
import time

import database as db


app = Flask(__name__)
args = docopt(__doc__)

bg_scheduler = BackgroundScheduler()
bg_scheduler.start()

playlist_update_counter = 0

atexit.register(lambda: bg_scheduler.shutdown())


# List of channels, populated with MPD client instances as playlists
# are requested and storage of cached playlist responses.
channels = {}

# needed for cookie generation
app.config["SECRET_KEY"] = "YouShouldProbablyChangeThis"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

DEFAULT_LIVESTREAM_INFO = {
    'active': False,
    'current_dj': None,
    'last_played': [],
    'CHANNEL': 'cyberia',
}

# namedtuple definition has to happen before loading
LivestreamTrack = namedtuple('LivestreamTrack', ['artist', 'title', 'first_seen'])

LIVESTREAM_INFO = db.load_pickle(DEFAULT_LIVESTREAM_INFO)
# outside of save/load so you can fiddle without deleting the savedata each time
LIVESTREAM_INFO['STREAM_DELAY'] = 7  # this is what i got from testing
# according to icecast docs it varies with burst-on-connect/burst-size

# be safe with our savedata
atexit.register(lambda: db.save_pickle(LIVESTREAM_INFO))


def in_http_dir(path):
    """Return a path in the HTTP directory."""

    return os.path.join(args["--http-dir"], path)


def random_file_from(dname, cont=None):
    """Serve a random file from a directory, excluding hidden files and index.html."""

    files = [f for f in os.listdir(dname) if not f.startswith('.') and not f == "index.html"]
    if not files:
        return send_file(in_http_dir("404.html")), 404

    fname = random.choice(files)
    if not cont:
        return send_file(os.path.join(dname, fname), cache_timeout=0)

    return cont(fname)


def get_playlist_info(client, beforeNum=5, afterNum=5):
    status = client.status()
    song = int(status["song"])
    pllen = int(status["playlistlength"])

    def songsIn(fromPos, toPos):
        minId = max(0, min(pllen, fromPos))
        maxId = max(0, min(pllen, toPos))
        return client.playlistinfo("{}:{}".format(minId, maxId))

    def sanitise(song):
        good_fields = ["artist", "albumartist", "album", "track", "time", "date", "title"]
        return {t: song[t] for t in good_fields if t in song}

    pinfo = {
        "before":  list(map(sanitise, songsIn(song-beforeNum, song))),
        "current": list(map(sanitise, client.playlistinfo(song)))[0],
        "after":   list(map(sanitise, songsIn(song+1, song+afterNum+1))),
        "elapsed": status["elapsed"],
        "stream_data": {"live": False}
    }
    pinfo["before"].reverse()

    return pinfo


def update_mpd_info(channel):
    global channels
    try:
        channels[channel]["client"].ping()
    except:
        try:
            channels[channel]["client"] = MPDClient()
            channels[channel]["client"].connect(channels[channel]["mpdHost"],
                                                channels[channel]["mpdPort"])
            channels[channel]["client"].ping()
        except Exception as e:
            print(e)
            channels[channel]["cache"] = ("Could not connect to MPD.", 500)
            return
    # okay, client (re-)connected
    p_info = get_playlist_info(channels[channel]["client"])
    channels[channel]["cache"] = (p_info, 200)


def update_livestream_info():
    global channels

    # get current track info
    req_url = "http://127.0.0.1:8000/status-json.xsl"
    try:
        req_info = json.loads(make_requests.get(req_url).content.decode('utf-8'))
    except Exception as e:
        print(e)
        channels[LIVESTREAM_INFO['CHANNEL']]["cache"] = ("Could not connect to stream.", 500)
        return

    status_metadata = {
        'artist': '',
        'title': '',
        'album': '🎵 L I V E S T R E A M 🎵'
    }

    stream_data = {
        'dj_name': '',
        'dj_pic': '',
        'stream_desc': '',
        'live': LIVESTREAM_INFO['active']
    }

    # fill in with streamer info
    if stream_data['live']:
        dj_info = db.get_dj_info(LIVESTREAM_INFO['current_dj'])
        if dj_info is not None:
            for k in dj_info:
                if k in stream_data:
                    stream_data[k] = dj_info[k]
            if 'stream_title' in dj_info and len(dj_info['stream_title']) > 0:
                status_metadata['album'] = dj_info['stream_title']

    # get the current metadata from icecast
    sources = req_info['icestats']['source']
    for source in sources:
        if LIVESTREAM_INFO['CHANNEL'] in source['listenurl']:
            # if no server_type then fallback is active, if we're
            # streaming the server_type starts with audio a regular
            # mpd source's type is application/ogg
            if 'server_type' in source and 'audio' in source['server_type']:
                for k in status_metadata:
                    if k in source:
                        status_metadata[k] = source[k].strip()
                break

    # if no last track or it's not the same as the last track append
    if len(LIVESTREAM_INFO['last_played']) == 0 or \
       LIVESTREAM_INFO['last_played'][-1].title != status_metadata['title']:
        newest_track = LivestreamTrack(status_metadata['artist'],
                                       status_metadata['title'],
                                       time.time() + LIVESTREAM_INFO['STREAM_DELAY'])
        LIVESTREAM_INFO['last_played'].append(newest_track)
        # we only want 5 last tracks + current
        if len(LIVESTREAM_INFO['last_played']) > 6:
            LIVESTREAM_INFO['last_played'].pop(0)

    time_now = time.time()

    pinfo = {
        'current': status_metadata,
        'elapsed': int(time_now - LIVESTREAM_INFO['last_played'][-1].first_seen),
        'before': [],
        'stream_data': stream_data
    }

    # populate before, radio expects tracks in most recent to oldest order
    # and their times need to be calculated because we don't know exact tracklengths
    indices = range(len(LIVESTREAM_INFO['last_played']) - 2, -1, -1)
    for i in indices:
        track = LIVESTREAM_INFO['last_played'][i]
        track_after = LIVESTREAM_INFO['last_played'][i + 1]
        prev_metadata = {
            'artist': track.artist,
            'title': track.title,
            'time': (track_after.first_seen - track.first_seen)
        }
        pinfo['before'].append(prev_metadata)

    channels[LIVESTREAM_INFO['CHANNEL']]["cache"] = (pinfo, 200)


def playlist_info_update_task():
    global channels, playlist_update_counter
    for channel in channels:
        if LIVESTREAM_INFO['active'] and channel == LIVESTREAM_INFO['CHANNEL']:
            playlist_update_counter = (playlist_update_counter + 1) % 5
            if playlist_update_counter == 1:
                update_livestream_info()
            else:
                continue
        else:
            update_mpd_info(channel)


bg_scheduler.add_job(
    func=playlist_info_update_task,
    trigger=IntervalTrigger(seconds=1),
    id='playlist_update',
    name='Update [channel].json\'s',
    replace_existing=True)


def playlist_for(channel):
    """Return the playlist of the given channel, as JSON."""
    global channels

    pinfo = channels[channel]["cache"]

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
    fields = ["artist", "album", "url", "notes"]
    if "artist" in request.form and "album" in request.form:
        save_form({t: request.form[t] for t in fields if t in request.form}, suffix="request")

    return send_file(in_http_dir("thankyou.html"))


@app.route("/playlist/<channel>.json", methods=["GET"])
def playlist(channel):
    global channels

    if channel in channels:
        return playlist_for(channel)

    return send_file(in_http_dir("404.html")), 404


@app.route("/webm.html", methods=["GET"])
def webm():
    tpl = '''
<!DOCTYPE html>
<html>
  <head>
    <title>{0}</title>
    <meta charset="UTF-8">
    <link rel="stylesheet" type="text/css" href="/css/webm.css">
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


@app.route("/dj/start_streaming")
@login_required
def streaming_page():
    if LIVESTREAM_INFO['current_dj'] is None:
        LIVESTREAM_INFO['current_dj'] = current_user.id
        LIVESTREAM_INFO['active'] = True
        LIVESTREAM_INFO['last_played'] = []
        return 'Switched over to stream.'
    return 'Someone else is already streaming!'


@app.route("/dj/stop_streaming")
@login_required
def streaming_over_page():
    if LIVESTREAM_INFO['current_dj'] == current_user.id or current_user.is_admin:
        LIVESTREAM_INFO['active'] = False
        LIVESTREAM_INFO['last_played'] = []
        LIVESTREAM_INFO['current_dj'] = None
        return 'Switchec back to regular programming.'
    return 'You are not streaming!'


@login_manager.user_loader
def load_user(user_id):
    return db.DJUser.get(user_id)


@app.route('/dj/login', methods=['GET', 'POST'])
def login():
    back_to_login = send_file(in_http_dir("login.html"))
    if request.method == 'GET':
        return back_to_login

    username = request.form['username']
    password = request.form['password']

    check_user = db.DJUser.get(username)
    if (check_user is not None):
        if (check_user.password == password):
            login_user(check_user)
            next_page = request.args.get('next')
            if next_page in ['/admin']:
                return redirect(next_page)
            return redirect('/dj')
    return back_to_login


@app.route("/dj/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route("/admin", methods=['GET', 'POST'])
@login_required
def admin_page():
    if not current_user.is_admin:
        return redirect("/")
    if request.method == 'GET':
        user_status = db.get_a_list(['banned', 'admin'])
        return render_template("admin.html", all_users=user_status)
    else:
        username = request.form['username']
        new_user = db.make_user(username)
        if new_user is None:
            return '{} already exists!'.format(username)
        else:
            return '{} created, with password "{}".'.format(*new_user)


@app.route("/dj")
@login_required
def dj_home_page():
    dj_info = db.get_dj_info(current_user.id)
    djin = [('your display name', 'dj_name'),
            ('dj pic url (optional)', 'dj_pic'),
            ('stream title (optional)', 'stream_title')]

    if dj_info is None:
        return 'Whoops, your account no longer exists!'

    return render_template("dj_page.html", livestream_info=LIVESTREAM_INFO,
                           dj_info_dict=dj_info, dj_info_names=djin,
                           current_desc=dj_info['stream_desc'])


@app.route("/dj/edit_dj_info", methods=['GET', 'POST'])
@login_required
def dj_edit_page():
    if request.method == 'GET':
        dj_info = db.get_dj_info(current_user.id)
        djin = [('your display name', 'dj_name'),
                ('dj pic url (optional)', 'dj_pic'),
                ('edit your stream title (optional)', 'stream_title')]

        if dj_info is None:
            return 'Whoops, your account no longer exists!'

        return render_template("dj_page_edit.html", livestream_info=LIVESTREAM_INFO,
                               dj_info_dict=dj_info, dj_info_names=djin,
                               current_desc=dj_info['stream_desc'])
    else:
        did_it_work = db.update_dj_info(current_user.id, request.form.to_dict())
        if did_it_work:
            return redirect('/dj')
        else:
            return 'You have been B&.'


@app.route("/dj/password_change_form", methods=['GET', 'POST'])
@login_required
def change_pass_page():
    if request.method == 'GET':
        return render_template("change_password.html")
    else:
        current_pass = request.form['current_pass']
        new_pass = request.form['new_pass']
        double_check = request.form['double_check']
        if current_user.password == current_pass:
            if new_pass == double_check:
                db.change_password(current_user.id, new_pass)
                logout_user()
                return 'Password changed, now log in again.'
        return redirect('/dj/password_change_form')


@app.route("/admin/ban/<username>")
@login_required
def ban_user(username=None):
    if not current_user.is_admin:
        return redirect("/")
    if username is not None:
        if username == current_user.id:
            return 'Don\'t ban yourself.'
        check_user = db.DJUser.get(username)
        if check_user.is_admin:
            return 'You can\'t ban an admin.'
        ban_result = db.update_dj_status(username, 'banned', True)
        if ban_result is not None:
            return '{} is now banned.'.format(username)
    return '{} doesn\'t exist.'.format(username)


@app.route("/admin/unban/<username>")
@login_required
def unban_user(username=None):
    if not current_user.is_admin:
        return redirect("/")
    if username is not None:
        ban_result = db.update_dj_status(username, 'banned', False)
        if ban_result is not None:
            return '{} is now unbanned.'.format(username)
    return '{} doesn\'t exist.'.format(username)


# only the superadmin account can make other people admins
@app.route("/admin/promote/<username>")
@login_required
def promote_user(username=None):
    if current_user.id != 'superadmin':
        return redirect("/")
    if username is not None:
        admin_result = db.update_dj_status(username, 'admin', True)
        if admin_result is not None:
            return '{} is now an admin.'.format(username)
    return '{} doesn\'t exist.'.format(username)


@app.route("/admin/demote/<username>")
@login_required
def demote_user(username=None):
    if current_user.id != 'superadmin':
        return redirect("/")
    if username is not None:
        if username == current_user.id:
            return 'You can\'t revoke your own admin privileges.'
        admin_result = db.update_dj_status(username, 'admin', False)
        if admin_result is not None:
            return '{} is no longer an admin.'.format(username)
    return '{} doesn\'t exist.'.format(username)


@app.route("/admin/reset_password/<username>")
@login_required
def password_reset(username=None):
    if not current_user.is_admin:
        return redirect("/")
    if username is not None:
        if current_user.id != 'superadmin':
            check_user = db.DJUser.get(username)
            if check_user.is_admin and check_user.id != current_user.id:
                return 'You can\'t reset another admin\'s password.'
        new_pass = db.change_password(username)
        if new_pass is not None:
            return '{}\'s new password is "{}".'.format(username, new_pass)
    return '{} doesn\'t exist.'.format(username)


if __name__ == "__main__":
    if args['serve']:
        try:
            try:
                with open(args["--channels"], "r") as f:
                    channels = json.loads(f.read())
                    for c in channels.keys():
                        if "mpdHost" in channels[c] and "mpdPort" in channels[c]:
                            channels[c]["client"] = None
                            channels[c]["cache"] = ("Not connected to MPD yet.", 500)
                        else:
                            del channels[c]
            except:
                raise Exception("--channels must be a channel configuration file")

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
            db.make_superadmin()
            app.run(port=args["PORT"])
        except:
            print("could not bind to port")
            exit(2)

    elif args['newuser']:
        new_user = db.make_user(args['USER'])
        if new_user is None:
            print('User "{}" already exists!'.format(username))
            exit(1)

        print('User "{}" created with password "{}".'.format(*new_user))

    elif args['newpass']:
        new_pass = db.change_password(args['USER'])
        print('Changed password to "{}".'.format(new_pass))

    elif args['ban']:
        if args['USER'] == 'superadmin':
            print('Cannot ban the superadmin!')
            exit(1)

        ban_result = db.update_dj_status(args['USER'], 'banned', True)
        if ban_result is not None:
            print('User "{}" is now banned.'.format(args['USER']))

    elif args['unban']:
        ban_result = db.update_dj_status(args['USER'], 'banned', False)
        if ban_result is not None:
            print('User "{}" is now unbanned.'.format(args['USER']))

    elif args['promote']:
        ban_result = db.update_dj_status(args['USER'], 'admin', True)
        if ban_result is not None:
            print('User "{}" is now an admin.'.format(args['USER']))

    elif args['demote']:
        if args['USER'] == 'superadmin':
            print('Cannot demote the superadmin!')
            exit(1)

        ban_result = db.update_dj_status(args['USER'], 'admin', False)
        if ban_result is not None:
            print('User "{}" is no longer an admin.'.format(args['USER']))
