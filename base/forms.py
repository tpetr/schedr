from django import forms
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from django.contrib.auth.models import User

from schedr.base.models import School

from django.template.loader import render_to_string

import re
regex_email_suffix = re.compile('@(.*)$')

alnum_re = re.compile(r'^\w+$')

# I put this on all required fields, because it's easier to pick up
# on them with CSS or JavaScript if they have a class of "required"
# in the HTML. Your mileage may vary. If/when Django ticket #3515
# lands in trunk, this will no longer be necessary.
attrs_dict = { 'class': 'required' }

class FullnameForm(forms.Form):
    fullname = forms.CharField(max_length=128, widget=forms.TextInput(), required=False)

    def clean_fullname(self):
        return self.cleaned_data['fullname'].strip()

    def save(self, user):
        if self.cleaned_data['fullname'] == '':
            user.first_name = ''
            user.last_name = ''
        else:
            names = self.cleaned_data['fullname'].split(' ', 1)
            user.first_name = names[0]
            if len(names) > 1:
                user.last_name = names[1]
            else:
                user.last_name = ''
        user.save()

class UsernameForm(forms.Form):
    username = forms.CharField(max_length=30, widget=forms.TextInput(attrs=attrs_dict), required=True)

    def clean_username(self):
        self.cleaned_data['username'] = self.cleaned_data['username'].strip()
        if not alnum_re.search(self.cleaned_data['username']):
            raise forms.ValidationError(_(u'Usernames can only contain letters, numbers, and underscores'))
        try:
            user = User.objects.get(username__iexact=self.cleaned_data['username'])
        except User.DoesNotExist:
            return self.cleaned_data['username']
        raise forms.ValidationError(_(u'Already taken'))
    
    def save(self, user):
        user.username = self.cleaned_data['username']
        user.save()

class InviteForm(forms.Form):
    user_name = forms.CharField(widget=forms.TextInput(attrs=dict(attrs_dict, maxlength=75)), label=_(u'Your name'))
    invite_name = forms.CharField(widget=forms.TextInput(attrs=dict(attrs_dict, maxlength=75)), label=_(u'Friend\'s name'))
    invite_email = forms.EmailField(widget=forms.TextInput(attrs=dict(attrs_dict, maxlength=75)), label=_(u'Friend\'s email address'))
    share = forms.BooleanField(widget=forms.CheckboxInput(), required=False)

    def clean_invite_email(self):
        try:
            User.objects.get(email=self.cleaned_data['invite_email'])
            raise forms.ValidationError(_(u'User is already registered'))
        except User.DoesNotExist:
            return self.cleaned_data['invite_email']
    
    def send(self):
        from django.core.mail import send_mail
        subject = render_to_string('invites/invite_email_subject.txt', {'name': self.cleaned_data['user_name']})
        subject = ''.join(subject.splitlines())
        message = render_to_string('invites/invite_email.txt', {'invite_name': self.cleaned_data['invite_name'], 'name': self.cleaned_data['user_name']})
        send_mail(subject, message, settings.NO_REPLY_EMAIL, [self.cleaned_data['invite_email']])
        return True

class CourseCommentForm(forms.Form):
    anonymous = forms.BooleanField(widget=forms.CheckboxInput(), required=False)
    text = forms.CharField(widget=forms.Textarea(attrs={'class': 'required', 'maxlength': 140}))

    def save(self, user, course, CourseComment):
        import datetime
        c = CourseComment(course=course, user=user, anonymous=self.cleaned_data['anonymous'], posted_on=datetime.datetime.now(), text=self.cleaned_data['text'])
        c.save()
        return c

class FeedbackForm(forms.Form):
    anonymous = forms.BooleanField(widget=forms.CheckboxInput(), required=False)
    text = forms.CharField(widget=forms.Textarea(attrs={'class': 'required', 'maxlength': 140}))

    def clean_text(self):
        if len(self.cleaned_data['text']) > 140:
            raise forms.ValidationError(_(u'Comment must be a maximum of 140 characters!'))
        return self.cleaned_data['text']

    def save(self, user, school):
        import datetime
        f = Feedback(text=self.cleaned_data['text'], user=user, school=school, anonymous=self.cleaned_data['anonymous'], posted_on=datetime.datetime.now());
        f.save();
        return f;
