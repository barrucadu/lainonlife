import os
import pickle
import random
import re

from tinydb import TinyDB, Query

# save/load livestream related data

SAVEDATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'savedata')
if not os.path.exists(SAVEDATA_PATH):
    os.mkdir(SAVEDATA_PATH)


def save_pickle(savedata):
    pickle_path = os.path.join(SAVEDATA_PATH, 'livestream_save.pickle')
    with open(pickle_path, 'wb') as file_handle:
        pickle.dump(savedata, file_handle, protocol=pickle.HIGHEST_PROTOCOL)


def load_pickle(default):
    pickle_path = os.path.join(SAVEDATA_PATH, 'livestream_save.pickle')
    if not os.path.exists(pickle_path):
        return default
    else:
        with open(pickle_path, 'rb') as file_handle:
            return pickle.load(file_handle)


# our tinydb
THE_DB = TinyDB(os.path.join(SAVEDATA_PATH, 'db.json'))

# for url checking
# slightly modified from https://stackoverflow.com/a/7160778
url_regex = re.compile(r'^(?:http)s?://'  # http:// or https://
                       r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
                       r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
                       r'(?::\d+)?'  # optional port
                       r'(?:/?|[/?]\S+)$', re.IGNORECASE)


def validate_url(url):
    if len(url) == 0:
        return True
    return url_regex.match(url) is not None


def get_ban_list():
    all_user_info = THE_DB.all()
    tor = []
    for user in all_user_info:
        if user['id'] != 'admin':
            banned = False
            if 'banned' in user:
                banned = user['banned']
            tor.append((user['id'], banned))

    return tor


def make_user(username):
    check_query = Query()
    check_if_user_exists = THE_DB.search(check_query.id == username)
    if (len(check_if_user_exists) > 0):
        return
    password = "%032x" % random.getrandbits(128)
    new_user = {
        'id': username,
        'password': password,
        'banned': False,
        'dj_name': username,
        'dj_pic': '',
        'stream_title': '',
        'stream_desc': '',
    }

    THE_DB.insert(new_user)
    return (username, password)


def get_dj_info(username):
    check_query = Query()
    check_if_user_exists = THE_DB.search(check_query.id == username)
    if (len(check_if_user_exists) == 0):
        return
    return check_if_user_exists[0]


def update_dj_info(username, form_dict):
    check_query = Query()
    check_if_user_exists = THE_DB.search(check_query.id == username)
    if (len(check_if_user_exists) == 0):
        return False
    # only put in proper picture urls
    if 'dj_pic' in form_dict:
        if not validate_url(form_dict['dj_pic']):
            del form_dict['dj_pic']
    THE_DB.update(form_dict, check_query.id == username)
    return True


def change_password(username, new_pass=None):
    check_query = Query()
    check_if_user_exists = THE_DB.search(check_query.id == username)
    if (len(check_if_user_exists) == 0):
        return
    if new_pass is None:
        new_pass = "%032x" % random.getrandbits(128)
    THE_DB.update({'password': new_pass}, check_query.id == username)
    return new_pass


def ban_user(username, new_ban_status):
    check_query = Query()
    check_if_user_exists = THE_DB.search(check_query.id == username)
    if (len(check_if_user_exists) == 0):
        return
    THE_DB.update({'banned': new_ban_status}, check_query.id == username)
    return new_ban_status


class DJUser(object):
    def __init__(self, username, password):
        self.id = username
        self.password = password

    @property
    def is_active(self):
        # check ban status
        check_ban = Query()
        check_ban_res = THE_DB.search(check_ban.id == self.id)
        if len(check_ban_res) == 0:
            return False
        if 'banned' not in check_ban_res[0]:
            return True
        return not check_ban_res[0]['banned']

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    def __eq__(self, other):
        '''
        Checks the equality of two `DJUser` objects using `get_id`.
        '''
        if isinstance(other, DJUser):
            return self.get_id() == other.get_id()
        return False

    def __ne__(self, other):
        '''
        Checks the inequality of two `DJUser` objects using `get_id`.
        '''
        return not self.__eq__(other)

    @classmethod
    def get(cls, u_id):
        user_query = Query()
        db_res = THE_DB.search(user_query.id == u_id)
        if len(db_res) > 0:
            found_user = DJUser(db_res[0]['id'], db_res[0]['password'])
        else:
            found_user = None
        return found_user


if __name__ == '__main__':
    new_admin = make_user('admin')
    if new_admin is not None:
        print('your admin account is now setup')
        print('user', new_admin[0])
        print('pass', new_admin[1])
    else:
        new_pass = change_password('admin')
        print('resetting admin password\nit is now', new_pass)
