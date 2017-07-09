from flask import Blueprint, Flask
from flask import current_app, make_response, redirect, request, send_file, render_template
from flask_login import LoginManager, login_required, login_user, logout_user, current_user

import json
import os
import random
import time

import database as db

login_manager = LoginManager()
login_manager.login_view = 'site.login'

blueprint = Blueprint('site', __name__)


@login_manager.user_loader
def load_user(user_id):
    return db.DJUser.get(user_id)


def serve(port=3000, httpdir="/srv/http", channels={}, livestream={}, secret_key="ChangeMe"):
    """Run the web server."""

    app = Flask(__name__)

    app.config['http_dir']   = httpdir
    app.config['channels']   = channels
    app.config['livestream'] = livestream
    app.config['SECRET_KEY'] = secret_key

    login_manager.init_app(app)

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
        save_form({t: request.form[t] for t in fields if t in request.form}, suffix="request")

    return send_file(in_http_dir("thankyou.html"))


@blueprint.route("/playlist/<channel>.json", methods=["GET"])
def playlist(channel):
    if channel in current_app.config['channels']:
        return playlist_for(channel)

    return send_file(in_http_dir("404.html")), 404


@blueprint.route("/webm.html", methods=["GET"])
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


###############################################################################
# The DJ pages

@blueprint.route('/dj')
@login_required
def dj_home_page():
    dj_info = db.get_dj_info(current_user.id)
    djin = [('your display name', 'dj_name'),
            ('dj pic url (optional)', 'dj_pic'),
            ('stream title (optional)', 'stream_title')]

    if dj_info is None:
        return 'Whoops, your account no longer exists!'

    return render_template("dj_page.html", livestream_info=current_app.config['livestream'],
                           dj_info_dict=dj_info, dj_info_names=djin,
                           current_desc=dj_info['stream_desc'])


@blueprint.route("/dj/start_streaming")
@login_required
def streaming_page():
    if current_app.config['livestream']['current_dj'] is None:
        current_app.config['livestream']['current_dj'] = current_user.id
        current_app.config['livestream']['active'] = True
        current_app.config['livestream']['last_played'] = []
        return 'Switched over to stream.'
    return 'Someone else is already streaming!'


@blueprint.route("/dj/stop_streaming")
@login_required
def streaming_over_page():
    if current_app.config['livestream']['current_dj'] == current_user.id or \
       current_user.is_admin:
        current_app.config['livestream']['active'] = False
        current_app.config['livestream']['last_played'] = []
        current_app.config['livestream']['current_dj'] = None
        return 'Switched back to regular programming.'
    return 'You are not streaming!'


@blueprint.route('/dj/login', methods=['GET', 'POST'])
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


@blueprint.route('/dj/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')


@blueprint.route("/dj/edit_dj_info", methods=['GET', 'POST'])
@login_required
def dj_edit_page():
    if request.method == 'GET':
        dj_info = db.get_dj_info(current_user.id)
        djin = [('your display name', 'dj_name'),
                ('dj pic url (optional)', 'dj_pic'),
                ('edit your stream title (optional)', 'stream_title')]

        if dj_info is None:
            return 'Whoops, your account no longer exists!'

        return render_template("dj_page_edit.html",
                               livestream_info=current_app.config['livestream'],
                               dj_info_dict=dj_info,
                               dj_info_names=djin,
                               current_desc=dj_info['stream_desc'])
    else:
        did_it_work = db.update_dj_info(current_user.id, request.form.to_dict())
        if did_it_work:
            return redirect('/dj')
        else:
            return 'You have been B&.'


@blueprint.route("/dj/password_change_form", methods=['GET', 'POST'])
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


###############################################################################
# The admin pages

@blueprint.route("/admin", methods=['GET', 'POST'])
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


@blueprint.route("/admin/ban/<username>")
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


@blueprint.route("/admin/unban/<username>")
@login_required
def unban_user(username=None):
    if not current_user.is_admin:
        return redirect("/")
    if username is not None:
        ban_result = db.update_dj_status(username, 'banned', False)
        if ban_result is not None:
            return '{} is now unbanned.'.format(username)
    return '{} doesn\'t exist.'.format(username)


@blueprint.route("/admin/promote/<username>")
@login_required
def promote_user(username=None):
    if current_user.id != 'superadmin':
        return redirect("/")
    if username is not None:
        admin_result = db.update_dj_status(username, 'admin', True)
        if admin_result is not None:
            return '{} is now an admin.'.format(username)
    return '{} doesn\'t exist.'.format(username)


@blueprint.route("/admin/demote/<username>")
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


@blueprint.route("/admin/reset_password/<username>")
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


###############################################################################
# Utility functions

def in_http_dir(path):
    """Return a path in the HTTP directory."""

    return os.path.join(current_app.config['http_dir'], path)


def random_file_from(dname, cont=None):
    """Serve a random file from a directory, excluding hidden files and index.html."""

    files = [f for f in os.listdir(dname) if not f.startswith('.') and not f == "index.html"]
    if not files:
        return send_file(in_http_dir("404.html")), 404

    fname = random.choice(files)
    if not cont:
        return send_file(os.path.join(dname, fname), cache_timeout=0)

    return cont(fname)


def playlist_for(channel):
    """Return the playlist of the given channel, as JSON."""

    pinfo = current_app.config['channels'][channel]["cache"]
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
