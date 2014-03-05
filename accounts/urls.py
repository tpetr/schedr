"""
URLConf for Django user registration and authentication.

Recommended usage is a call to ``include()`` in your project's root
URLConf to include this URLConf for any URL beginning with
``/accounts/``.

"""


from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template
from django.contrib.auth import views as auth_views

from schedr.accounts.views import activate, register, login, field_available, resend_activation

from schedr.accounts.forms import FlexibleAuthenticationForm


urlpatterns = patterns('',
                       url(r'^username_avail$', field_available, {'field': 'username'}),
                       url(r'^email_avail$', field_available, {'field': 'email'}),
                       # Activation keys get matched by \w+ instead of the more specific
                       # [a-fA-F0-9]{40} because a bad activation key should still get to the view;
                       # that way it can return a sensible "invalid key" message instead of a
                       # confusing 404.
                       url(r'^activate/resend/$', resend_activation, name='resend_activation'),
                       url(r'^activate/(?P<activation_key>\w+)/$',
                           activate,
                           name='registration_activate'),
                       url(r'^login/$',
                           login,
                           {'template_name': 'accounts/login.html', 'authentication_form': FlexibleAuthenticationForm, 'default_redirect': '/home'},
                           name='auth_login'),
                       url(r'^logout/$',
                           auth_views.logout,
                           {'template_name': 'accounts/logout.html'},
                           name='auth_logout'),
                       url(r'^password/change/$',
                           auth_views.password_change,
                           {'template_name': 'accounts/password_change.html'},
                           name='auth_password_change'),
                       url(r'^password/change/done/$',
                           auth_views.password_change_done,
                           {'template_name': 'accounts/password_change_done.html'},
                           name='auth_password_change_done'),
                       url(r'^password/reset/$',
                           auth_views.password_reset,
                           {'template_name': 'accounts/password_reset.html'},
                           name='auth_password_reset'),
                       url(r'^password/reset/confirm/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$',
                           auth_views.password_reset_confirm,
                           {'template_name': 'accounts/password_reset_confirm.html'},
                           name='auth_password_reset_confirm'),
                       url(r'^password/reset/complete/$',
                           auth_views.password_reset_complete,
                           {'template_name': 'accounts/password_reset_complete.html'},
                           name='auth_password_reset_complete'),
                       url(r'^password/reset/done/$',
                           auth_views.password_reset_done,
                           {'template_name': 'accounts/password_reset_success.html'},
                           name='auth_password_reset_done'),
                       url(r'^register/$',
                           register,
                           name='registration_register'),
                       url(r'^register/complete/$',
                           direct_to_template,
                           {'template': 'accounts/registration_complete.html'},
                           name='registration_complete'),
                       )
