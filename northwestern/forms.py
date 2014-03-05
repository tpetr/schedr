from django import forms
from schedr.northwestern.importer import CAESAR
from django.utils.translation import ugettext_lazy as _

class CAESARLoginForm(forms.Form):
    netid = forms.CharField(max_length=128, widget=forms.TextInput(), label=_(u'NetID'))
    pwd = forms.CharField(max_length=128, widget=forms.PasswordInput(), label=_(u'Password'))

    def clean(self):
        c = CAESAR()
        str = c.login(self.cleaned_data['netid'], self.cleaned_data['pwd'])
	if "Class Search" not in str:
            raise forms.ValidationException('Invalid NetID or password')
        return self.cleaned_data
