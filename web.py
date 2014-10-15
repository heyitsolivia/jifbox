import os

from dropbox.client import DropboxClient, DropboxOAuth2Flow
from flask import Flask, abort, flash, redirect, render_template, session, url_for

#
# Dropbox configuration
#

DROPBOX_KEY = os.environ.get('DROPBOX_KEY')
DROPBOX_SECRET = os.environ.get('DROPBOX_SECRET')

def dropbox_auth_flow():
    redirect_uri = url_for('dropbox_callback', _external=True)
    flow = DropboxOAuth2Flow(DROPBOX_KEY, DROPBOX_SECRET,
        redirect_uri, session, 'dropbox-auth-csrf-token')
    return flow


#
# the app
#

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('jifbox.html')


@app.route('/settings')
def settings():

    context = {}

    context['DROPBOX_AVAILABLE'] = DROPBOX_KEY and DROPBOX_SECRET
    context['DROPBOX_AUTHED'] = False  # see if access_token is available


@app.route('/settings/dropbox/auth')
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

    # save access_token

    return redirect(url_for('home'))


@app.route('/settings/dropbox/logout')
def dropbox_logout():
    # delete Dropbox access_token
    return redirect(url_for('settings'))


if __name__ == '__main__':
    app.run(debug=True, port=8000)
