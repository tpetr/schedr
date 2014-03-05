from django.http import HttpResponseRedirect

def restrict_school(function, user, school):
    if (user.school != school):
        return HttpResponseRedirect("/account/login?next=/%s/spring2009/" % (user.school.name))
    return function()
