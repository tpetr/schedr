from django.contrib.auth.decorators import user_passes_test
from schedr.base.models import SchedrUser

from django.http import HttpResponseRedirect
from django.utils.http import urlquote
from django.contrib.auth import REDIRECT_FIELD_NAME

def is_schedr_user(u):
    if not u.is_authenticated():
        return False
    try:
        return u.schedruser is not None
    except SchedrUser.DoesNotExist:
        return False

def schedr_users_only(function=None):
    def decorate(request, school, *args, **kwargs):
        if is_schedr_user(request.user):
            return function(request, school, *args, **kwargs)
        return HttpResponseRedirect("/account/login?%s=%s" % (REDIRECT_FIELD_NAME, urlquote(request.get_full_path())))
    return decorate

from django.core.cache import cache as djcache

def cache_chart(func, seconds=15):
    def decorate(*args):
        key = "%s.%s_%s" % (func.__module__, func.__name__, args)
        result = djcache.get(key)
        if result is None:
            result = func(*args)
            djcache.set(key, result, seconds)
        return result
    return decorate
