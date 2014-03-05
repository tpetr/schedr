import datetime
import random
import re
import sha

from django.conf import settings
from django.db import models
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from schedr.base.models import SchedrUser

from django.core.mail import EmailMessage

from util import send_push_notification

SHA1_RE = re.compile('^[a-f0-9]{40}$')


class RegistrationManager(models.Manager):
    """
    Custom manager for the ``RegistrationProfile`` model.
    
    The methods defined here provide shortcuts for account creation
    and activation (including generation and emailing of activation
    keys), and for cleaning out expired inactive accounts.
    
    """
    def activate_user(self, activation_key):
        if SHA1_RE.search(activation_key):
            try:
                reg = self.get(activation_key=activation_key)
            except self.model.DoesNotExist:
                return False
            if not reg.activation_key_expired():
                user = reg.user
                user.is_active = True
                user.save()
                reg.delete()
                send_push_notification('New User', "%s\n%s\n%s" % (user.email, user.username, user.first_name))
                to = ['trpetr@gmail.com']
                if user.schedruser.school.name == 'northwestern':
                    to.append('reiterandrew@gmail.com')
                msg = EmailMessage("[Schedr User] Activated %s" % user.email, render_to_string("emails/activate.html", {'user': user}), 'no-reply@schedr.com', to)
                msg.content_subtype = 'html'
                msg.send()
                return user
        return False
    
    def create_inactive_user(self, username, password, email,
                             send_email=True, profile_callback=None, first_name='', last_name='', graduation_year=None):
        new_user = SchedrUser.objects.create_user(username, email, password, first_name, last_name)
        new_user.is_active = False
        new_user.graduation_year = graduation_year
        new_user.save()
        
        reg = self.create_pending_registration(new_user)
        
        if profile_callback is not None:
            profile_callback(user=new_user)
        
        if send_email:
            from django.core.mail import EmailMultiAlternatives
            subject = render_to_string('accounts/activation_email_subject.txt', {})
            subject = ''.join(subject.splitlines())
            text_content = render_to_string('accounts/activation_email.txt', { 'activation_key': reg.activation_key, 'expiration_days': settings.ACCOUNT_ACTIVATION_DAYS, 'user': new_user})
            html_content = render_to_string('accounts/activation_email.html', { 'activation_key': reg.activation_key, 'expiration_days': settings.ACCOUNT_ACTIVATION_DAYS, 'user': new_user})
            msg = EmailMultiAlternatives(subject, text_content, 'no-reply@schedr.com', [new_user.email])
            msg.attach_alternative(html_content, "text/html")
            msg.send()

        return new_user
    
    def create_pending_registration(self, user):
        salt = sha.new(str(random.random())).hexdigest()[:5]
        activation_key = sha.new(salt+user.username).hexdigest()
        return self.create(user=user,
                           activation_key=activation_key)
        
    def delete_expired_users(self):
        count = 0
        for reg in self.all():
            if reg.activation_key_expired():
                user = reg.user
                if not user.is_active:
                    user.delete()
                reg.delete()
                count = count + 1
        return count

class PendingRegistration(models.Model):
    user = models.ForeignKey(User, unique=True, verbose_name=_('user'))
    activation_key = models.CharField(_('activation key'), max_length=40)
    
    objects = RegistrationManager()
    
    class Meta:
        verbose_name = _('registration profile')
        verbose_name_plural = _('registration profiles')
    
    def __unicode__(self):
        return self.user.email
    
    def activation_key_expired(self):
        expiration_date = datetime.timedelta(days=settings.ACCOUNT_ACTIVATION_DAYS)
        return (self.user.date_joined + expiration_date <= datetime.datetime.now())
    activation_key_expired.boolean = True
