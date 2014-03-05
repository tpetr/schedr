from schedr.api.models import Application
from django.contrib import admin
from django.http import Http404
from django.contrib.auth.models import User

from oauth_provider.models import Consumer

from datetime import datetime

class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'user_count', 'push_enabled', 'created_on')

    def queryset(self, request):
        qs = super(ApplicationAdmin, self).queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(admin=request.user)

    def save_model(self, request, obj, form, change):
        if change:
            if not (request.user.is_superuser or request.user == obj.admin):
                raise Http404("not owner")
        else:
            c = Consumer.objects.create_consumer(obj.name, request.user)
            c.save()
            
            obj.admin = request.user
            obj.consumer = c
            obj.push_secret = User.objects.make_random_password(length=16)
            obj.last_push = datetime.now()
        obj.save()

admin.site.register(Application, ApplicationAdmin)
