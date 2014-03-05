from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.template import Context, loader, RequestContext
from schedr.base.models import School, SchedrUser, Feedback
import time
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django.contrib.auth.decorators import login_required

from django.conf import settings

from django.shortcuts import render_to_response
from schedr.base.forms import UsernameForm, FullnameForm
from django.contrib.auth.forms import PasswordChangeForm
from urllib import quote
from schedr.accounts.forms import RegistrationForm

import random

def push_recv(request):
    fp = open("/tmp/test.txt", "w")
    fp.write("Get: %s\nPost: %s\nHeaders: %s" % (request.GET, request.POST, request.META))
    fp.close()
    return HttpResponse("OK!")

def robots(request):
    return HttpResponse(open('/home/tpetr/public_html/static/robots.txt').read(), 'text/plain')

def error(request):
    raise Exception("Test error")

def home(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect(request.user.schedruser.school.get_absolute_url())
    else:
        return HttpResponseRedirect("/")

def info(request):
    return render_to_response("info.html", {'user': request.user})

def help(request):
    return render_to_response("help.html", {'user': request.user})

def new_reg(request):
    if request.method == 'POST':
        form = RegistrationForm(data=request.POST)
        if form.is_valid():
            new_user = form.save()
            return HttpResponseRedirect(reverse('registration_complete'))
    else:
        form = RegistrationForm()

    context = RequestContext(request)

    return render_to_response("register.html", {'schools': School.objects.filter(visible=True), 'form': form}, context_instance=context)

#@cache_page(60)
def index(request, template_name="index.html"):
    if not request.META.get('HTTP_HOST', '').startswith('www'):
        return HttpResponseRedirect('https://www.schedr.com/')


    t = loader.get_template(template_name)
    
    #schools = cache.get('base.index.schools')
    #if schools == None:
    #    schools = []
    #    for school in School.objects.filter(visible=True):
    #        schools.append({'name': school.name, 'title': school.title})
    #    cache.set('base.index.schools', schools, 60 * 60 * 24)

    #feedback.append(Feedback.objects.get(id=26))
    feedback = cache.get('base.index.feedback')
    if feedback is None:
        feedback = Feedback.objects.random()
        cache.set('base.index.feedback', feedback, 600)

    schools = []

    c = Context({'schools': schools, 'user': request.user, 'feedback': feedback})
    return HttpResponse(t.render(c))

def feedback(request):
    if not request.user.is_authenticated():
        return HttpResponse(status=403)
    from django.core.mail import EmailMessage
    from django.template.loader import render_to_string
    msg = EmailMessage('[Schedr] Feedback from %s' % request.user.email, render_to_string("emails/feedback.html", {'user': request.user, 'message': request.POST.get('message', '(blank)')}), 'no-reply@schedr.com', ['trpetr@gmail.com'])
    msg.content_subtype = 'html'
    msg.send()
    return HttpResponse()

@login_required
def account(request):
    response = HttpResponse()
    t = loader.get_template('accounts/index.html')

    if request.method == 'POST':
        action = request.POST.get('action', '')
        if action == 'username':
            username_form = UsernameForm(data=request.POST)
            if username_form.is_valid():
                username_form.save(request.user)
                username_form = UsernameForm({'username': request.user.username})
                response.set_cookie('schedr_acct_message', quote('Username changed'), 2)
            password_form = PasswordChangeForm(user=request.user)
            fullname_form = FullnameForm({'fullname': ("%s %s" % (request.user.first_name, request.user.last_name)).strip()})
        elif action == 'password':
            password_form = PasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                password_form.save(request.user)
                password_form = PasswordChangeForm(user=request.user)
                response.set_cookie('schedr_acct_message', quote('Password changed'), 2)
            username_form = UsernameForm({'username': request.user.username})
            fullname_form = FullnameForm({'fullname': ("%s %s" % (request.user.first_name, request.user.last_name)).strip()})
        elif action == 'fullname':
            fullname_form = FullnameForm(data=request.POST)
            if fullname_form.is_valid():
                fullname_form.save(request.user)
                fullname_form = FullnameForm({'fullname': ("%s %s" % (request.user.first_name, request.user.last_name)).strip()})
                response.set_cookie('schedr_acct_message', quote('Full name changed'), 2)
            password_form = PasswordChangeForm(user=request.user)
            username_form = UsernameForm({'username': request.user.username})
    else:
        username_form = UsernameForm({'username': request.user.username})
        password_form = PasswordChangeForm(user=request.user)
        fullname_form = FullnameForm({'fullname': ("%s %s" % (request.user.first_name, request.user.last_name)).strip()})

    user = SchedrUser.objects.get(id=request.user.id)

    context = RequestContext(request, {'username_form': username_form, 'password_form': password_form, 'user': user, 'fullname_form': fullname_form})
    response.write(t.render(context))
    return response
