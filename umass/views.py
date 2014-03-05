from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.core.urlresolvers import reverse
from schedr.umass.models import Term, Major, Course, Section, Event, User, Location, CourseComment, UserData
from schedr.base.models import School
from schedr.school import views

def index(request, school, Term):
    return HttpResponseRedirect('/umass/spring2010/')
