"""
Views which allow users to create and activate accounts.

"""


from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext

from schedr.accounts.forms import RegistrationForm, EmailAuthenticationForm, ResendActivationForm
from schedr.accounts.models import PendingRegistration

from schedr.base.models import School, SchedrUser
from django.contrib.auth.models import User

from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.sites.models import Site, RequestSite
from django.views.decorators.cache import never_cache
import re
alnum_re = re.compile(r'^\w+$')

def field_available(request, field):
    value = request.GET[field]
    d = {}
    d[field] = value
    try:
        SchedrUser.objects.get(**d)
        return HttpResponse('0')
    except SchedrUser.DoesNotExist:
        return HttpResponse('1')

def login(request, school=None, template_name='accounts/login.html', redirect_field_name=REDIRECT_FIELD_NAME, default_redirect='', authentication_form=EmailAuthenticationForm):
    redirect_to = request.REQUEST.get(redirect_field_name, default_redirect)
    if request.method == "POST":
        form = authentication_form(data=request.POST, school=school)
        if form.is_valid():
            # Light security check -- make sure redirect_to isn't garbage.
            if not redirect_to or '//' in redirect_to or ' ' in redirect_to:
                redirect_to = settings.LOGIN_REDIRECT_URL
            from django.contrib.auth import login
            login(request, form.get_user())
            if request.session.test_cookie_worked():
                request.session.delete_test_cookie()
            return HttpResponseRedirect(redirect_to)
    else:
        form = authentication_form(request)
    request.session.set_test_cookie()
    if Site._meta.installed:
        current_site = Site.objects.get_current()
    else:
        current_site = RequestSite(request)
    return render_to_response(template_name, {'form': form, redirect_field_name: redirect_to, 'site_name': current_site.name, 'school': school}, context_instance=RequestContext(request))


def activate(request, activation_key,
             template_name='accounts/activate.html',
             extra_context=None):
    activation_key = activation_key.lower() # Normalize before trying anything with it.
    account = PendingRegistration.objects.activate_user(activation_key)
    if extra_context is None:
        extra_context = {}
    context = RequestContext(request)
    for key, value in extra_context.items():
        context[key] = callable(value) and value() or value
    return render_to_response(template_name,
                              { 'account': account,
                                'expiration_days': settings.ACCOUNT_ACTIVATION_DAYS },
                              context_instance=context)

def resend_activation(request, template_name='accounts/resend_activation.html', success_url=None):
    if request.method == 'POST':
        form = ResendActivationForm(data=request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(success_url or 'http://www.schedr.com/account/register/complete/');
    else:
        form = ResendActivationForm()

    return render_to_response(template_name, {'form': form}, context_instance=RequestContext(request))

def register(request, success_url=None,
             form_class=RegistrationForm, profile_callback=None,
             template_name='accounts/registration_form.html',
             extra_context=None):
    if request.method == 'POST':
        form = form_class(data=request.POST, files=request.FILES)
        if form.is_valid():
            new_user = form.save(profile_callback=profile_callback)
            # success_url needs to be dynamically generated here; setting a
            # a default value using reverse() will cause circular-import
            # problems with the default URLConf for this application, which
            # imports this file.
            return HttpResponseRedirect(success_url or reverse('registration_complete'))
    else:
        form = form_class()
    
    if extra_context is None:
        extra_context = {}
    context = RequestContext(request)
    for key, value in extra_context.items():
        context[key] = callable(value) and value() or value

    return render_to_response(template_name,
                              { 'form': form, 'school_json': ','.join(["'%s': '%s'" % (s.email_suffix, s.title) for s in School.objects.filter(visible=True)])},
                              context_instance=context)
