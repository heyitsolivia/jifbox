import datetime
import os

import requests

try:
    from urlparse import urlparse       # python 2.x
except:
    from urllib.parse import urlparse   # python 3.x

from dropbox.client import DropboxClient, DropboxOAuth2Flow
from flask import (Flask, abort, current_app, flash, jsonify, redirect,
    render_template, request, session, url_for)
from flask.ext.login import (LoginManager, UserMixin,
    current_user, login_user, logout_user)
from functools import wraps
from pymongo import MongoClient
from rauth import OAuth1Service

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')
BASIC_PASSWORD = os.environ.get('BASIC_PASSWORD')

SECRET_KEY = os.environ.get('SECRET_KEY')


DEFAULT_SETTINGS = {
    'frame_delay': 255,
    'frames': 10,
    'snap_delay': 500,
}


#
# MongoDB configuration
#

mongo_url = os.environ.get('MONGOHQ_URL')
mongo_conn = MongoClient(mongo_url)

mongo_params = urlparse(mongo_url)

mongo = mongo_conn[mongo_params.path.strip('/')]

if mongo_params.username and mongo_params.password:
    mongo.authenticate(mongo_params.username, mongo_params.password)

tumblr_host = os.environ.get('TUMBLR_HOSTNAME')

#
# services
#

class Service(object):

    def __init__(self):
        self.register()

    def register(self):
        self._config = mongo.services.find_one({'service_id': self.service_id})
        if not self._config:
            doc = {
                'service_id': self.service_id,
            }
            doc_id = mongo.services.save(doc)
            self._config = mongo.services.find_one(doc_id)

    def __delitem__(self, key):
        if key in self._config:
            del self._config[key]
            self.save()

    def __getitem__(self, key):
        return self._config.get(key)

    def __setitem__(self, key, value):
        self._config[key] = value
        self.save()

    def save(self):
        mongo.services.save(self._config)

    def process(self, payload):
        raise NotImplementedError('process must be implemented by services')


class DropboxService(Service):

    service_id = 'dropbox'

    def __init__(self):
        super(DropboxService, self).__init__()
        self.client_key = os.environ.get('DROPBOX_KEY')
        self.client_secret = os.environ.get('DROPBOX_SECRET')

        access_token = os.environ.get('DROPBOX_TOKEN')
        if access_token:
            self['access_token'] = access_token

    @property
    def is_available(self):
        return bool(self.client_key and self.client_secret)

    @property
    def is_enabled(self):
        return bool(self['access_token'])

    def process(self, payload):
        client = DropboxClient(self['access_token'])
        path = "%s/%s" % (payload['timestamp'].date().isoformat(), payload['filename'])
        meta = client.put_file(path, payload['data'], overwrite=False)
        return meta


class TumblrService(Service):

    service_id = 'tumblr'

    def __init__(self):
        super(TumblrService, self).__init__()
        self.client_key = os.environ.get('TUMBLR_KEY')
        self.client_secret = os.environ.get('TUMBLR_SECRET')
        self.hostname = os.environ.get('TUMBLR_HOSTNAME')

    @property
    def is_available(self):
        return bool(self.client_key and self.client_secret and self.hostname)

    @property
    def is_enabled(self):
        return bool(self['access_token'])

    def process(self, payload):

        flow = tumblr_auth_flow()
        client = flow.get_session(self['access_token'])

        params = {
            'type': 'photo',
            'state': 'published',
        }

        resp = client.post('post', params=params, data={}, header_auth=True)

        headers = {
            'Authorization': resp.request.headers['authorization']
        }

        files = {k: (None, v) for k, v in params.items()}
        files['data'] = (payload['filename'], payload['data'], 'image/gif')

        resp = requests.post(
            'https://api.tumblr.com/v2/blog/%s/post' % self.hostname,
            files=files,
            headers=headers)
        
        meta = resp.json()
        return meta


# pseudoservice for storing config info
class JIFBOXService(Service):
    service_id = 'jifbox'
    is_available = False
    is_enabled = False

    def __init__(self):
        super(JIFBOXService, self).__init__()

        settings = DEFAULT_SETTINGS.copy()
        settings.update(self.settings)
        self['settings'] = settings

    @property
    def settings(self):
        return self['settings'] or {}

    def update_settings(self, new_settings):
        current_settings = self.settings
        current_settings.update(new_settings)
        self['settings'] = current_settings


jifbox = JIFBOXService()

services = {
    'dropbox': DropboxService(),
    'tumblr': TumblrService(),
}


#
# Dropbox stuff
#

def dropbox_auth_flow():
    dropbox = services['dropbox']
    redirect_uri = url_for('dropbox_callback', _external=True)
    flow = DropboxOAuth2Flow(dropbox.client_key, dropbox.client_secret,
        redirect_uri, session, 'dropbox-auth-csrf-token')
    return flow


#
# Tumblr stuff
#

def tumblr_auth_flow(request_token=None, request_secret=None):
    ts = services['tumblr']
    flow = OAuth1Service(
        name='tumblr',
        consumer_key=ts.client_key,
        consumer_secret=ts.client_secret,
        request_token_url='http://www.tumblr.com/oauth/request_token',
        access_token_url='http://www.tumblr.com/oauth/access_token',
        authorize_url='http://www.tumblr.com/oauth/authorize',
        base_url='https://api.tumblr.com/v2/blog/%s/' % ts.hostname)
    return flow


#
# the app
#

app = Flask(__name__)
app.secret_key = SECRET_KEY


# login stuff

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


class User(UserMixin):
    def __init__(self, is_admin=False):
        self.is_admin = is_admin

    @classmethod
    def admin_user(self):
        user = User(is_admin=True)
        user.id = 'admin'
        return user

    @classmethod
    def basic_user(self):
        user = User(is_admin=False)
        user.id = 'basic'
        return user


def login_maybe_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if current_app.login_manager._login_disabled:
            return func(*args, **kwargs)
        elif BASIC_PASSWORD and not current_user.is_authenticated():
            return current_app.login_manager.unauthorized()
        return func(*args, **kwargs)
    return decorated_view


def login_definitely_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if current_app.login_manager._login_disabled:
            return func(*args, **kwargs)
        elif not current_user.is_authenticated() or not getattr(current_user, 'is_admin', False):
            return current_app.login_manager.unauthorized()
        return func(*args, **kwargs)
    return decorated_view


@login_manager.user_loader
def load_user(user_id):
    if user_id == 'admin':
        return User.admin_user()
    elif user_id == 'basic':
        return User.basic_user()


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == 'POST':

        password = request.form.get('password')
        
        user = None

        if password == ADMIN_PASSWORD:
            user = User.admin_user()
            login_user(user)
            return redirect(url_for('settings'))

        elif password == BASIC_PASSWORD:
            user = User.basic_user()
            login_user(user)
            return redirect(url_for('index'))        

    return render_template('login.html')

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('index'))


# routes

@app.route('/')
@login_maybe_required
def index():
    context = {'tumblr_host': tumblr_host}
    return render_template('jifbox.html', **context)


@app.route('/giffed', methods=['POST'])
@login_maybe_required
def giffed():

    giffile = request.files['giffile']
    if not giffile:
        abort(500)
    gifdata = giffile.read()

    response = {
        'active_services': {},
        'inactive_services': [],
    }

    timestamp = datetime.datetime.utcnow()

    payload = {
        'filename': '%s.gif' % timestamp.isoformat(),
        'data': gifdata,
        'timestamp': timestamp,
    }

    for sid, service in services.items():
        if service.is_available and service.is_enabled:
            meta = service.process(payload)
            if meta:
                response['active_services'][sid] = meta
        else:
            response['inactive_services'].append(sid)

    return jsonify(response)


@app.route('/settings', methods=['GET', 'POST'])
@login_definitely_required
def settings():

    if request.method == 'POST':

        new_settings = {}
        current_settings = jifbox.settings

        for key, default_value in DEFAULT_SETTINGS.items():
            value = request.form.get(key) or current_settings.get(key) or default_value
            value = int(value)
            new_settings[key] = value

        jifbox.update_settings(new_settings)

        return redirect(url_for('settings'))

    context = {'services': services, 'settings': jifbox.settings}
    return render_template('settings.html', **context)


@app.route('/get-settings', methods=['GET'])
def gifsettings():
    return jsonify(jifbox.settings)


# Dropbox

@app.route('/settings/dropbox/auth')
@login_definitely_required
def dropbox_auth():
    flow = dropbox_auth_flow()
    return redirect(flow.start())


@app.route('/settings/dropbox/callback')
def dropbox_callback():

    try:
        access_token, user_id, url_state = get_auth_flow().finish(request.args)
    except DropboxOAuth2Flow.BadRequestException, e:
        abort(400)
    except DropboxOAuth2Flow.BadStateException, e:
        abort(400)
    except DropboxOAuth2Flow.CsrfException, e:
        abort(403)
    except DropboxOAuth2Flow.NotApprovedException, e:
        flash('Not approved?  Why not')
        return redirect(url_for('home'))
    except DropboxOAuth2Flow.ProviderException, e:
        app.logger.exception("Auth error" + e)
        abort(403)

    services['dropbox']['access_token'] = access_token

    return redirect(url_for('settings'))


@app.route('/settings/dropbox/logout')
@login_definitely_required
def dropbox_logout():
    del services['dropbox']['access_token']
    return redirect(url_for('settings'))


# Tumblr

@app.route('/settings/tumblr/auth')
@login_definitely_required
def tumblr_auth():

    service = services['tumblr']
    flow = tumblr_auth_flow()

    request_token, request_token_secret = flow.get_request_token()
    authorize_url = flow.get_authorize_url(request_token)

    service['request_token'] = request_token
    service['request_secret'] = request_token_secret

    return redirect(authorize_url)


@app.route('/settings/tumblr/callback')
def tumblr_callback():

    oauth_token = request.args.get('oauth_token')
    oauth_verifier = request.args.get('oauth_verifier')

    if oauth_token and oauth_verifier:

        service = services['tumblr']

        flow = tumblr_auth_flow()
        access_token = flow.get_access_token(
            service['request_token'],
            service['request_secret'],
            method='GET',
            data={
                'oauth_verifier': oauth_verifier,
            })

        service['access_token'] = list(access_token)

        del services['tumblr']['request_token']
        del services['tumblr']['request_secret']

    return redirect(url_for('settings'))


@app.route('/settings/tumblr/logout')
@login_definitely_required
def tumblr_logout():
    del services['tumblr']['access_token']
    return redirect(url_for('settings'))


#
# GET IT GIFFED!!!!!!!
#

if __name__ == '__main__':
    app.run(debug=True, port=8000)
