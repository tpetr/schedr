from datetime import datetime
from django.utils.hashcompat import sha_constructor
import urllib, urllib2

def push_data(app, data):
    if not app.push_enabled: return

    sig = sha_constructor("%s&%s" % (app.push_secret, data)).hexdigest()

    request = urllib2.Request(url=app.push_url, data=data, headers={'Schedr-Signature': sig, 'Content-Type': 'application/octet-stream'})
    response = urllib2.urlopen(request)

    app.last_push = datetime.now()
    app.save()

    return response
