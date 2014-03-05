from schedr.api.decorators import api_method, oauth_api_method
from django.http import HttpResponse

from base.models import School

from django.utils import simplejson

from api import utils

@api_method
def get_school(request, form):
    "Returns information about a particular school in JSON form."
    school = form.cleaned_data['school']
    return HttpResponse(simplejson.dumps(school.__json__()))

@api_method
def test_push(request, form):
    "Pushes test data. Client must be logged in as app admin!"
    app = form.cleaned_data['consumer_key']
    if request.user != app.admin:
        return HttpResponse("Must be logged in as admin user", status=404)

    r = HttpResponse()

    data = "test"

    r.write("Pushing: %s<br>" % data);
    resp = utils.push_data(app, data)
    r.write("Response: %s" % resp.read())
    
    return r
        


from oauth_provider.models import Token

@oauth_api_method
def get_user_info(request, form, user):
    "Returns authenticated user info in JSON form."
    return HttpResponse("info: %s" % user.username)
