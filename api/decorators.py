from django.http import HttpResponse
from schedr.api import forms

from oauth.oauth import OAuthError
from django.utils.translation import ugettext as _
from oauth_provider.utils import initialize_server_request, send_oauth_error

try:
    from functools import update_wrapper
except ImportError:
    from django.utils.functional import update_wrapper

class api_method(object):
    def __init__(self, view):
        update_wrapper(self, view)
        self.view = view

        form_name = ''.join(n.capitalize() for n in self.__name__.split('_')) + 'Form'
        self.form = getattr(forms, form_name)

    def __call__(self, request):
        form = self.form(request.REQUEST)
        if form.is_valid():
            return self.view(request, form)
        else:
            return self.invalid_form(form)

    def invalid_form(self, form):
        return HttpResponse("Fail: %s" % form.errors)

class oauth_api_method(object):
    def __init__(self, view):
        update_wrapper(self, view)
        self.view = view

        form_name = ''.join(n.capitalize() for n in self.__name__.split('_')) + 'Form'
        self.form = getattr(forms, form_name)

    def __call__(self, request, *args, **kwargs):
        if self.is_valid_request(request):
            try:
                consumer, token, parameters = self.validate_token(request)
            except OAuthError, e:
                return send_oauth_error(e)

            if self.resource_name and token.resource.name != self.resource_name:
                return send_oauth_error(OAuthError(_('You are not allowed to access this resource.')))
            elif consumer and token:
                form = self.form(request.REQUEST)
                if form.is_valid():
                    return self.view(request, form, token.user)
                else:
                    return self.invalid_form(request, form)
        return send_oauth_error(OAuthError(_('Invalid request parameters.')))

    @staticmethod
    def is_valid_request(request):
        # first check the HTTP Authorization header
        # - this is the preferred way to pass parameters, according to the oauth spec.
        try:
            auth_params = request.META["HTTP_AUTHORIZATION"]
        except KeyError:
            in_auth = False
        else:
            in_auth = 'oauth_consumer_key' in auth_params \
                and 'oauth_token' in auth_params \
                and 'oauth_signature_method' in auth_params \
                and 'oauth_signature' in auth_params \
                and 'oauth_timestamp' in auth_params \
                and 'oauth_nonce' in auth_params

        # also try the request, which covers POST and GET
        req_params = request.REQUEST
        in_req = 'oauth_consumer_key' in req_params \
            and 'oauth_token' in req_params \
            and 'oauth_signature_method' in req_params \
            and 'oauth_signature' in req_params \
            and 'oauth_timestamp' in req_params \
            and 'oauth_nonce' in req_params

        return in_auth or in_req

    @staticmethod
    def validate_token(request):
        oauth_server, oauth_request = initialize_server_request(request)
        return oauth_server.verify_request(oauth_request)

    def invalid_form(self,  form):
        return HttpResponse("Fail: %s" % form.errors)
