#!/usr/bin/env python3

"""Backend Services.

Usage:
  backend.py [--http-dir=PATH] [--mpd-host=HOST] PORT
  backend.py (-h | --help)

Options:
  --http-dir=PATH   Path of the web files   [default: /srv/http]
  --mpd-host=HOST   Hostname of MPD         [default: localhost]
  -h --help         Show this text

"""

from docopt import docopt
from flask import Flask, make_response, redirect, request, send_file, render_template
from mpd import MPDClient
import json, os, random, time

### all of these are added dependencies by puss, stdlib
# import threading  # uncomment this if you want stream to start after current song ends
import requests as make_requests
from collections import namedtuple
import signal
from datetime import datetime, timedelta

# new requirement
from flask_login import LoginManager, login_required, login_user, logout_user, current_user

import database as db


app  = Flask(__name__)
args = docopt(__doc__)

# List of channels, populated with MPD client instances as playlists
# are requested.
channels = {"everything": {"port": 6600, "client": None},
            "cyberia":    {"port": 6601, "client": None},
            "swing":      {"port": 6602, "client": None},
            "cafe":       {"port": 6603, "client": None}}

# needed for cookie generation
app.config["SECRET_KEY"] = "YouShouldProbablyChangeThis"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

DEFAULT_LIVESTREAM_INFO = {
    'active': False,
    'current_dj': None,
    'last_played': [],
    'PORT': 6601
}

# namedtuple definition has to happen before loading
LivestreamTrack = namedtuple('LivestreamTrack', ['artist', 'title', 'first_seen'])

LIVESTREAM_INFO = db.load_pickle(DEFAULT_LIVESTREAM_INFO)


# be safe with our savedata
def handle_shutdown(*args):
    db.save_pickle(LIVESTREAM_INFO)
    exit(1)


def handle_imminent_shutdown(*args):
    pickle_path = os.path.join(db.SAVEDATA_PATH, 'livestream_save.pickle')
    os.remove(pickle_path)  # something went terribly wrong so better to get rid of our savedata
    exit(2)


signal.signal(signal.SIGRTMIN, handle_imminent_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)


def in_http_dir(path):
    """Return a path in the HTTP directory."""

    return os.path.join(args["--http-dir"], path)


def random_file_from(dname, cont=None):
    """Serve a random file from a directory."""

    files = [f for f in os.listdir(dname) if not f.startswith('.')]
    if not files:
        return send_file(in_http_dir("404.html")), 404

    fname = random.choice(files)
    if not cont:
        return send_file(os.path.join(dname, fname), cache_timeout = 0)

    return cont(fname)


def get_playlist_info(client, beforeNum, afterNum, current_only=False):
    status = client.status()
    song   = int(status["song"])
    pllen  = int(status["playlistlength"])

    songsIn  = lambda fromPos, toPos: client.playlistinfo("{}:{}".format(max(0, min(pllen, fromPos)), max(0, min(pllen, toPos))))
    sanitise = lambda song: {t: song[t] for t in ["artist", "albumartist", "album", "track", "time", "date", "title"] if t in song}
    if current_only:
        pinfo = {
            "current": list(map(sanitise, client.playlistinfo(song)))[0],
            "elapsed": status["elapsed"]
        }
    else:
        pinfo = {
            "before":  list(map(sanitise, songsIn(song-beforeNum, song))),
            "current": list(map(sanitise, client.playlistinfo(song)))[0],
            "after":   list(map(sanitise, songsIn(song+1, song+afterNum+1))),
            "elapsed": status["elapsed"]
        }
        pinfo["before"].reverse()

    return pinfo


def playlist_for(channel, beforeNum=5, afterNum=5):
    """Return the playlist of the given MPD instance, as JSON."""
    if (channel == LIVESTREAM_INFO['PORT']) and LIVESTREAM_INFO['active']:
        pinfo = get_livestream_info()
    else:
        try:
            client = MPDClient()
            client.connect(args["--mpd-host"], channel)
        except:
            return "Could not connect to MPD.", 500

        pinfo = get_playlist_info(client, beforeNum, afterNum)
        pinfo['stream_data'] = {'live': False}

    resp = make_response(json.dumps(pinfo), 200)
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
    if "artist" in request.form and "album" in request.form:
        save_form({t: request.form[t] for t in ["artist", "album", "url", "notes"] if t in request.form}, suffix="request")

    return send_file(in_http_dir("thankyou.html"))


@app.route("/playlist/<channel>.json", methods=["GET"])
def playlist(channel):
    global channels

    if channel in channels:
        try:
            channels[channel]["client"].ping()
        except:
            try:
                channels[channel]["client"] = MPDClient()
                channels[channel]["client"].connect(args["--mpd-host"], channels[channel]["port"])
                channels[channel]["client"].ping()
            except:
                return "Could not connect to MPD.", 500
        return playlist_for(channel)

    return send_file(in_http_dir("404.html")), 404


@app.route("/webm.html", methods=["GET"])
def webm():
    tpl= '''
<!DOCTYPE html>
<html>
  <head>
    <title>{0}</title>
    <meta charset="UTF-8">
    <link rel="stylesheet" type="text/css" href="/webm.css">
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


# streaming stuff begins
# streaming overrides cyberia? (configure this in DEFAULT_LIVESTREAM_INFO)

@app.route("/schedule.json", methods=["GET"])
def schedule():
    dt = datetime.today()
    start = dt - timedelta(days=dt.weekday())
    end = start + timedelta(days=6)
    week_of = "{} - {}".format(start.strftime('%b %d'), end.strftime('%b %d'))
    sched_info = {'week_of': week_of}
    sched_path = os.path.join(db.SAVEDATA_PATH, 'schedule.txt')
    if os.path.exists(sched_path):
        with open(sched_path, 'r', encoding='utf-8') as sched_file:
            sched_lines = sched_file.read()
            sched_lines = sched_lines.split('\n')
            sched_lines = [line for line in sched_lines if not line.startswith('//')]
            sched_info['dailies'] = sched_lines
    resp = make_response(json.dumps(sched_info), 200)
    resp.headers["Content-Type"] = "application/json"
    return resp


def start_streaming():
    # right now, this immediately stop the stream if you call actually_start_streaming instead
    # this can wait for current track to finish playing if you uncomment below instead 
    actually_start_streaming()
    return

    # try:
    #     client = MPDClient()
    #     client.connect(args["--mpd-host"], LIVESTREAM_INFO['PORT'])
    # except:
    #     print('couldn\'t connect to mpd')
    #     return

    # pinfo = get_playlist_info(client, 0, 0, True)
    # wait_for_how_long = float(pinfo['current']['time']) - float(pinfo['elapsed'])
    # threading.Timer(wait_for_how_long, actually_start_streaming).start()


def actually_start_streaming():
    # need to remake the client otherwise
    # mpd.ConnectionError: Connection lost while reading line
    try:
        client = MPDClient()
        client.connect(args["--mpd-host"], LIVESTREAM_INFO['PORT'])
    except:
        print('couldn\'t connect to mpd')
        return

    client.pause(1)

    c_outputs = client.outputs()
    stop_ids = [c['outputid'] for c in c_outputs if 'cyberia' in c['outputname']]
    for o_id in stop_ids:
        client.disableoutput(o_id)

    LIVESTREAM_INFO['active'] = True
    LIVESTREAM_INFO['last_played'] = []


def stop_streaming():
    if not LIVESTREAM_INFO['active']:
        return
    try:
        client = MPDClient()
        client.connect(args["--mpd-host"], LIVESTREAM_INFO['PORT'])
    except:
        print('couldn\'t connect to mpd')
        return
    c_outputs = client.outputs()
    start_ids = [c['outputid'] for c in c_outputs if 'cyberia' in c['outputname']]
    for o_id in start_ids:
        client.enableoutput(o_id)
    client.pause(0)

    LIVESTREAM_INFO['active'] = False
    LIVESTREAM_INFO['last_played'] = []
    LIVESTREAM_INFO['current_dj'] = None


@app.route("/dj/start_streaming")
@login_required
def streaming_page():
    if LIVESTREAM_INFO['current_dj'] is None:
        LIVESTREAM_INFO['current_dj'] = current_user.id
        start_streaming()
        return_text = "stream started, you can connect to icecast now"
        # return_text = "you should be able to connect to icecast as soon as the currently playing track ends"
    else:
        return_text = 'someone else is already streaming..'
    return return_text


# maybe this should happen automatically if playlist update doesn't work for 30 seconds?
@app.route("/dj/stop_streaming")
@login_required
def streaming_over_page():
    if (LIVESTREAM_INFO['current_dj'] == current_user.id) or (current_user.id == 'admin'):
        stop_streaming()
        return_text = 'stream ended'
    else:
        return_text = 'nop'
    return return_text


def get_livestream_info():
    # get current track info
    req_url = "http://54.208.6.108:8000/status-json.xsl"  # temp dev
    # req_url = "/radio/status-json.xsl"
    try:
        req_info = json.loads(make_requests.get(req_url).content.decode('utf-8'))
    except Exception as e:
        print(e)
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

    if 'source' not in req_info['icestats']:
        # nothing streaming yet
        return {'current': status_metadata, 'elapsed': 0, 'stream_data': stream_data}

    sources = req_info['icestats']['source']
    for source in sources:
        if 'cyberia' in source['listenurl']:
            for k in status_metadata:
                if k in source:
                    status_metadata[k] = source[k].strip()
            break

    # if no last track or it's not the same as the last track append
    if (len(LIVESTREAM_INFO['last_played']) == 0) or (LIVESTREAM_INFO['last_played'][-1].title != status_metadata['title']):
        newest_track = LivestreamTrack(status_metadata['artist'], status_metadata['title'], time.time())
        LIVESTREAM_INFO['last_played'].append(newest_track)
        # we only want 5 last tracks + current
        if (len(LIVESTREAM_INFO['last_played']) > 6):
            LIVESTREAM_INFO['last_played'].pop(0)

    time_now = time.time()

    pinfo = {
        'current': status_metadata,
        'elapsed': int(time_now - LIVESTREAM_INFO['last_played'][-1].first_seen),
        'before': [],
        # "after":
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

    return pinfo


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
    if (current_user.id != 'admin'):
        return redirect("/")
    if request.method == 'GET':
        user_ban_info = db.get_ban_list()
        return render_template("admin.html", all_users=user_ban_info)
    else:
        username = request.form['username']
        new_user = db.make_user(username)
        if new_user is None:
            return 'error, {} already exists'.format(username)
        else:
            return 'success, {} created, their password is {}'.format(*new_user)


@app.route("/dj")
@login_required
def dj_home_page():
    dj_info = db.get_dj_info(current_user.id)
    djin = [('your display name', 'dj_name'), ('dj pic url (optional)', 'dj_pic'), ('stream title (optional)', 'stream_title')]
    if dj_info is None:
        return 'something went wrong'
    return render_template("dj_page.html", livestream_info=LIVESTREAM_INFO,
                           dj_info_dict=dj_info, dj_info_names=djin,
                           current_desc=dj_info['stream_desc'])


@app.route("/dj/edit_dj_info", methods=['GET', 'POST'])
@login_required
def dj_edit_page():
    if request.method == 'GET':
        dj_info = db.get_dj_info(current_user.id)
        djin = [('your display name', 'dj_name'), ('dj pic url (optional)', 'dj_pic'), ('edit your stream title (optional)', 'stream_title')]
        if dj_info is None:
            return 'something went wrong'
        return render_template("dj_page_edit.html", livestream_info=LIVESTREAM_INFO,
                               dj_info_dict=dj_info, dj_info_names=djin,
                               current_desc=dj_info['stream_desc'])
    else:
        did_it_work = db.update_dj_info(current_user.id, request.form.to_dict())
        if did_it_work:
            return redirect('/dj')
        else:
            return 'whoops, something went wrong'


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
                return 'successfully changed your password, you\'ll need to log back in'
        return redirect('/dj/password_change_form')


@app.route("/admin/ban/<username>")
@login_required
def ban_user(username=None):
    if (current_user.id != 'admin'):
        return redirect("/")
    if username is not None:
        ban_result = db.ban_user(username, True)
        if ban_result is not None:
            return '{} is now banned'.format(username)
    return 'nothing happened'


@app.route("/admin/unban/<username>")
@login_required
def unban_user(username=None):
    if (current_user.id != 'admin'):
        return redirect("/")
    if username is not None:
        ban_result = db.ban_user(username, False)
        if ban_result is not None:
            return '{} is now unbanned'.format(username)
    return 'nothing happened'


if __name__ == "__main__":
    try:
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
        app.run(port=args["PORT"])
    except:
        print("could not bind to port")
        exit(2)
