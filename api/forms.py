from django import forms
from django.contrib.auth import authenticate
import schedr
from django.forms import ModelForm
from schedr.api.models import Application
from oauth_provider.utils import initialize_server_request
from oauth_provider.models import Token

class ApiMethodForm(forms.Form):
    consumer_key = forms.CharField(max_length=40, help_text='Your Schedr consumer key')

    def clean_consumer_key(self):
        try:
            return Application.objects.get(consumer__key=self.cleaned_data['consumer_key'])
        except Application.DoesNotExist:
            raise forms.ValidationError('Unknown consumer key')

    def clean(self):
        if not self.errors:
            # check for stuff
            pass
        return self.cleaned_data

class OAuthApiMethodForm(forms.Form):
    token = forms.ModelChoiceField(queryset=Token.objects.all(), help_text='Valid OAuth token')

from base.models import School

class GetSchoolForm(ApiMethodForm):
    school = forms.CharField(max_length=20, help_text='School name (ex. umass)')

    def clean_school(self):
        try:
            return School.objects.get(name=self.cleaned_data['school'], visible=True)
        except School.DoesNotExist:
            raise forms.ValidationError('Unknown school')

class GetUserInfoForm(OAuthApiMethodForm):
    pass

class TestPushForm(ApiMethodForm):
    pass
