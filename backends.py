from django.contrib.auth.models import User
from django.contrib.auth.backends import ModelBackend
from django.utils.hashcompat import sha_constructor
from schedr.base.models import SchedrUser

class SchedrUserBackend(ModelBackend):
    def authenticate(self, email=None, username=None, password=None):
        try:
            if email:
                user = User.objects.get(email=email)
            else:
                user = User.objects.get(username=username)

            algo, salt, hash = user.password.split('$')

            if algo == 'schedr':
                if sha_constructor(password + salt).hexdigest() == hash:
                    return user
            elif user.check_password(password):
                return user
        except User.DoesNotExist:
            pass
        return None

class EmailBackend(ModelBackend):
    def authenticate(self, email=None, password=None):
        try:
            user = User.objects.get(email=email)
            algo, salt, hash = user.password.split('$')
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            return None

class EmailPrefixBackend(EmailBackend):
    pass
