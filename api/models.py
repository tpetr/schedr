from django.db import models
from django.contrib.auth.models import User
from oauth_provider.models import Consumer
from django.utils.hashcompat import sha_constructor
from datetime import datetime

class ApplicationManager(models.Manager):
    def create_application(self, name, desc, url, admin, push_url=None):
        app = self.model(name=name, description=desc, url=url, admin=admin)
        if push_url:
            app.push_enabled = True
            app.push_url = push_url
        c = Consumer.objects.create_consumer(app.name, app.admin)
        c.save()
        self.consumer = c
        app.save()
        return app

class Application(models.Model):
    name = models.CharField(max_length=64)
    description = models.TextField()
    icon = models.ImageField(upload_to='img/apps/', blank=True, null=True)
    url = models.URLField(verify_exists=False)
    created_on = models.DateTimeField(auto_now_add=True)

    # oauth
    consumer = models.OneToOneField(Consumer, editable=False)
    success_url = models.URLField(verify_exists=False)

    # users
    admin = models.ForeignKey(User, related_name="%(class)s_related_admin", editable=False)
    users = models.ManyToManyField(User, related_name="%(class)s_related_users", blank=True, editable=False)

    # push data
    push_enabled = models.BooleanField(blank=True)
    push_url = models.URLField(verify_exists=False, blank=True)
    push_secret = models.CharField(max_length=16, unique=True, editable=False)
    last_push = models.DateTimeField(editable=False)

    objects = ApplicationManager()

    def user_count(self):
        return self.users.all().count()

    def __unicode__(self):
        return self.name
