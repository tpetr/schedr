"""
Forms and validation code for user registration.

"""


from django import forms
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User

from schedr.accounts.models import PendingRegistration
from schedr.base.models import School

from django.contrib.auth import authenticate
from django.template.loader import render_to_string
from django.conf import settings

import re
alnum_re = re.compile(r'^\w+$')


# I put this on all required fields, because it's easier to pick up
# on them with CSS or JavaScript if they have a class of "required"
# in the HTML. Your mileage may vary. If/when Django ticket #3515
# lands in trunk, this will no longer be necessary.
attrs_dict = { 'class': 'required' }

regex_username = re.compile('^(.*)@')

email_re = re.compile(r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*" + r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-011\013\014\016-\177])*"' + r')@(?:[A-Z0-9-]+\.)+[A-Z]{2,6}$', re.IGNORECASE)


class FlexibleAuthenticationForm(forms.Form):
    name = forms.CharField(widget=forms.TextInput(attrs=dict(attrs_dict, maxlength=75)), label=_("Username or Email address"))
    password = forms.CharField(label=_("Password"), widget=forms.PasswordInput)

    def __init__(self, request=None, school=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super(FlexibleAuthenticationForm, self).__init__(*args, **kwargs)

    def clean(self):
        name = self.cleaned_data.get('name')
        password = self.cleaned_data.get('password')

        if name and password:
            if email_re.match(name):
                self.user_cache = authenticate(email=name, password=password)
            else:
                self.user_cache = authenticate(username=name, password=password)
            if self.user_cache is None:
                raise forms.ValidationError(_("Invalid login. Did you register yet?"))
            elif not self.user_cache.is_active:
                raise forms.ValidationError(_("Your account has not been activated yet. Please check your email."))

        if self.request:
            if not self.request.session.test_cookie_worked():
                raise forms.ValidationError(_("Cookies are required for logging in."))

        return self.cleaned_data

    def get_user_id(self):
        if self.user_cache:
            return self.user_cache.id
        return None

    def get_user(self):
        return self.user_cache

class EmailAuthenticationForm(forms.Form):
    email = forms.EmailField(widget=forms.TextInput(attrs=dict(attrs_dict, maxlength=75)), label=_("Email Address"))
    password = forms.CharField(label=_("Password"), widget=forms.PasswordInput)
    
    def __init__(self, request=None, school=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super(EmailAuthenticationForm, self).__init__(*args, **kwargs)

    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')

        if email and password:
            self.user_cache = authenticate(email=email, password=password)
            if self.user_cache is None:
                raise forms.ValidationError(_("Invalid email address or password. Did you register yet?"))
            elif not self.user_cache.is_active:
                raise forms.ValidationError(_("This account is inactive."))

        if self.request:
            if not self.request.session.test_cookie_worked():
                raise forms.ValidationError(_("Cookies are required for logging in."))

        return self.cleaned_data

    def get_user_id(self):
        if self.user_cache:
            return self.user_cache.id
        return None

    def get_user(self):
        return self.user_cache

class ResendActivationForm(forms.Form):
    email = forms.EmailField(widget=forms.TextInput(attrs=dict(attrs_dict, maxlength=75)), label=_(u'Email address'))

    def clean_email(self):
        if not self.cleaned_data['email'].endswith('.edu'):
            raise forms.ValidationError(_(u'School emails only'))

        try:
            self.user = User.objects.get(email=self.cleaned_data['email'])
        except User.DoesNotExist:
            raise forms.ValidationError('No such user')

        try:
            self.reg = PendingRegistration.objects.get(user=self.user)
        except PendingRegistration.DoesNotExist:
            raise forms.ValidationError('User already activated')

        return self.cleaned_data['email']

    def save(self):
        from django.core.mail import EmailMultiAlternatives
        subject = render_to_string('accounts/activation_email_subject.txt', {})
        subject = ''.join(subject.splitlines())
        text_content = render_to_string('accounts/activation_email.txt', { 'activation_key': self.reg.activation_key, 'expiration_days': settings.ACCOUNT_ACTIVATION_DAYS, 'user': self.user})
        html_content = render_to_string('accounts/activation_email.html', { 'activation_key': self.reg.activation_key, 'expiration_days': settings.ACCOUNT_ACTIVATION_DAYS, 'user': self.user})
        msg = EmailMultiAlternatives(subject, text_content, 'no-reply@schedr.com', [self.user.email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()

class RegistrationForm(forms.Form):
    full_name = forms.CharField(max_length=128, widget=forms.TextInput(attrs=attrs_dict), label=_(u'Full name'), required=False)
    username = forms.CharField(max_length=30, widget=forms.TextInput(attrs=attrs_dict), label=_(u'Username'))
    email = forms.EmailField(widget=forms.TextInput(attrs=dict(attrs_dict,
                                                               maxlength=75)),
                             label=_(u'School email address'))
    graduation_year = forms.IntegerField(widget=forms.TextInput(attrs=dict(attrs_dict, maxlength=4)), label=_(u'Graduation year'), required=False)
    password1 = forms.CharField(widget=forms.PasswordInput(attrs=attrs_dict, render_value=False),
                                label=_(u'Password'))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs=attrs_dict, render_value=False),
                                label=_(u'Password (again)'))

    def clean_graduation_year(self):
        if self.cleaned_data['graduation_year'] is None:
            return self.cleaned_data['graduation_year']

        if self.cleaned_data.get('graduation_year', '') != '':
            year = int(self.cleaned_data.get('graduation_year', '1900'))
            if (year < 2005 or year > 2015) and (year != 0):
                raise forms.ValidationException('Invalid year')
        return self.cleaned_data.get('graduation_year', '')

    def clean_full_name(self):
        return self.cleaned_data.get('full_name', '').strip()

    def clean_username(self):
        if not alnum_re.search(self.cleaned_data['username']):
            raise forms.ValidationError(_(u'Usernames can only contain letters, numbers, and underscores'))
        try:
            user = User.objects.get(username__iexact=self.cleaned_data['username'])
        except User.DoesNotExist:
            return self.cleaned_data['username']
        raise forms.ValidationError(_(u'Already taken'))
    
    def clean_email(self):
	if not self.cleaned_data['email'].endswith('.edu'):
            raise forms.ValidationError(_(u'School emails only'))
        # check email suffix
        try:
            school = School.objects.from_email(self.cleaned_data['email'])
        except School.DoesNotExist:
            raise forms.ValidationError(_(u'School not supported yet'))

        # check for existing user
        try:
            user = User.objects.get(email__iexact=self.cleaned_data['email'])
        except User.DoesNotExist:
            return self.cleaned_data['email']
        raise forms.ValidationError(_(u'In use'))

    def clean_password2(self):
        if 'password1' in self.cleaned_data and 'password2' in self.cleaned_data and self.cleaned_data['password1'] != self.cleaned_data['password2']:
            raise forms.ValidationError(_(u'Passwords don\'t match'))

    def save(self, profile_callback=None):
        names = self.cleaned_data['full_name'].split(' ', 1)
        try:
            first_name = names[0]
        except:
            first_name = ''
        try:
            last_name = names[1]
        except:
            last_name = ''
        return PendingRegistration.objects.create_inactive_user(username=self.cleaned_data['username'],
                                                                password=self.cleaned_data['password1'],
                                                                email=self.cleaned_data['email'],
								first_name=first_name,
								last_name=last_name,
                                                                graduation_year=self.cleaned_data['graduation_year'],
                                                                profile_callback=profile_callback)
