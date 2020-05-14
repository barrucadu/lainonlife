import os
import pickle
import random

from tinydb import TinyDB, Query

# save/load livestream related data

SAVEDATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "savedata")
if not os.path.exists(SAVEDATA_PATH):
    os.mkdir(SAVEDATA_PATH)


def save_pickle(savedata):
    pickle_path = os.path.join(SAVEDATA_PATH, "livestream_save.pickle")
    with open(pickle_path, "wb") as file_handle:
        pickle.dump(savedata, file_handle, protocol=pickle.HIGHEST_PROTOCOL)


def load_pickle(default):
    pickle_path = os.path.join(SAVEDATA_PATH, "livestream_save.pickle")
    if not os.path.exists(pickle_path):
        return default
    else:
        with open(pickle_path, "rb") as file_handle:
            return pickle.load(file_handle)


# our tinydb
THE_DB = TinyDB(os.path.join(SAVEDATA_PATH, "db.json"))


def get_a_list(of_what):
    if not isinstance(of_what, list):
        of_what = [of_what]
    all_user_info = THE_DB.all()
    tor = []
    for user in all_user_info:
        insrt_row = []
        for w in of_what:
            found_what = False
            if w in user:
                found_what = user[w]
            insrt_row.append(found_what)
        tor.append((user["id"], insrt_row))

    return tor


def make_superadmin():
    new_admin = make_user("superadmin", True)
    if new_admin is not None:
        print('User "superadmin" created with password "{}".'.format(new_admin[1]))


def make_user(username, admin=False):
    check_query = Query()
    check_if_user_exists = THE_DB.search(check_query.id == username)
    if len(check_if_user_exists) > 0:
        return
    # generates a random 32 hex digit password
    password = "%032x" % random.getrandbits(128)
    new_user = {
        "id": username,
        "password": password,
        "banned": False,
        "admin": admin,
        "dj_name": username,
        "dj_pic": "",
        "stream_title": "",
        "stream_desc": "",
    }

    THE_DB.insert(new_user)
    return (username, password)


def get_dj_info(username):
    check_query = Query()
    check_if_user_exists = THE_DB.search(check_query.id == username)
    if len(check_if_user_exists) == 0:
        return
    return check_if_user_exists[0]


def update_dj_info(username, form_dict):
    check_query = Query()
    check_if_user_exists = THE_DB.search(check_query.id == username)
    if len(check_if_user_exists) == 0:
        return False
    # trust no one, even if someone modified their response we don't want them to
    # most of these require different levels of permission
    dont_touch = ["admin", "banned", "id", "password"]
    for k in dont_touch:
        if k in form_dict:
            del form_dict[k]
    THE_DB.update(form_dict, check_query.id == username)
    return True


def update_dj_status(username, status_key, new_status):
    check_query = Query()
    check_if_user_exists = THE_DB.search(check_query.id == username)
    if len(check_if_user_exists) == 0:
        return
    THE_DB.update({status_key: new_status}, check_query.id == username)
    return new_status


def change_password(username, new_pass=None):
    check_query = Query()
    check_if_user_exists = THE_DB.search(check_query.id == username)
    if len(check_if_user_exists) == 0:
        return
    if new_pass is None:
        # generates a random 32 hex digit password
        new_pass = "%032x" % random.getrandbits(128)
    THE_DB.update({"password": new_pass}, check_query.id == username)
    return new_pass


class DJUser(object):
    def __init__(self, username, password):
        self.id = username
        self.password = password

    def check_state(self, what_state):
        check = Query()
        check_res = THE_DB.search(check.id == self.id)
        if len(check_res) == 0:
            return False
        if what_state not in check_res[0]:
            return False
        return check_res[0][what_state]

    @property
    def is_active(self):
        return not self.check_state("banned")

    @property
    def is_admin(self):
        return self.check_state("admin")

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    def __eq__(self, other):
        if isinstance(other, DJUser):
            return self.get_id() == other.get_id()
        return False

    @classmethod
    def get(cls, u_id):
        user_query = Query()
        db_res = THE_DB.search(user_query.id == u_id)
        if len(db_res) > 0:
            found_user = DJUser(db_res[0]["id"], db_res[0]["password"])
        else:
            found_user = None
        return found_user
