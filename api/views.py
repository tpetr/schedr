from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django import forms
from schedr.api import methods
from schedr.api.decorators import api_method, oauth_api_method
from schedr.api.models import Application
from oauth_provider.models import Token

from django.contrib.auth.decorators import login_required

from oauth_provider.decorators import oauth_required
from oauth_provider.utils import initialize_server_request

@login_required
def index(request):
    apps = Application.objects.filter(admin=request.user)
    api_methods = [{'name': m, 'doc': getattr(methods, m).__doc__} for m in dir(methods) if isinstance(getattr(methods, m), api_method)]
    oauth_methods = [{'name': m, 'doc': getattr(methods, m).__doc__} for m in dir(methods) if isinstance(getattr(methods, m), oauth_api_method)]
    return render_to_response('api/index.html', {'user': request.user, 'api_methods': api_methods, 'oauth_methods': oauth_methods, 'apps': apps})

def call(request, method):
    try:
        method_view = getattr(methods, method)
    except AttributeError:
        raise Http404('Unknown method')
    else:
        return method_view(request)

@login_required
def list(request):
    api_method_list = [{'name': m, 'doc': getattr(methods, m).__doc__} for m in dir(methods) if getattr(methods, m).__class__ is api_method]
    oauth_method_list = [{'name': m, 'doc': getattr(methods, m).__doc__} for m in dir(methods) if getattr(methods, m).__class__ is oauth_api_method]
    
    return render_to_response('api/list.html', {'api_methods': api_method_list, 'oauth_methods': oauth_method_list, 'user': request.user})

@login_required
def doc(request, method):
    try:
        method_view = getattr(methods, method)
    except AttributeError:
        raise Http404('Unknown method')

    def field_type(f):
        if isinstance(f, forms.IntegerField): return 'Integer'
        elif isinstance(f, forms.CharField): return 'String'

    fields = [{'name': name, 'desc': field.help_text, 'required': field.required, 'type': field_type(field)} for name, field in method_view.form.base_fields.items()]

    return render_to_response('api/doc.html', {'method': method, 'fields': fields, 'doc': method_view.__doc__, 'user': request.user})


def authorize(request, token, callback, params):
    app = Application.objects.get(consumer=token.consumer)
    return render_to_response('oauth/authorize.html', {'app': app, 'user': request.user, 'params': params})

def authorize_complete(request):
    token = Token.objects.get(key = request.REQUEST['oauth_token'])

    app = Application.objects.get(consumer=token.consumer)

    if int(request.POST['authorize_access']) == 0:
        return HttpResponseRedirect(app.url)

    app.users.add(request.user)

    return HttpResponseRedirect("%s?oauth_token=%s" % (app.success_url, token.key))

@oauth_required
def oauth_test(request):
    token = Token.objects.get(key=request.REQUEST['oauth_token'], token_type=Token.ACCESS)
    return HttpResponse("OAuth test OK, user = %s" % token.user.email)
