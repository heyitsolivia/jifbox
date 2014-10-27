# JIFBOX

*Pronounced GIF-box*

JIFBOX is a web-based animated GIF photobooth.


## Deploy

[![Deploy](https://www.herokucdn.com/deploy/button.png)](https://heroku.com/deploy?template=https://github.com/sunlightlabs/jifbox)

Click the button above to deploy on a new [Heroku](https://heroku.com) instance. You will be prompted for configuration values.

## Services

JIFBOX will automatically send the animated GIFs to various services, if you so choose. Support for each service must be enabled individually.

### Dropbox

Upload generated GIFs to a Dropbox folder. Requires **DROPBOX_KEY** and **DROPBOX_SECRET** to be set and Dropbox to be connected via the admin screen.

### Tumblr

Post generated GIFs to a Tumblr blog. Requires **TUMBLR_KEY** and **TUMBLR_SECRET** to be set and Tumblr to be connected via the admin screen.