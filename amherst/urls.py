from django.conf.urls.defaults import *
from schedr.amherst.models import Term, Major, Course, Section, Location, UserData, Final
from schedr.base.models import School
from schedr.amherst import settings, importer
from schedr.accounts import views as account_views

school = School.objects.get(name='amherst')

urlpatterns = patterns('schedr.school.views',
    (r'^$', 'index', {'school': school, 'Term': Term}),
    (r'^login$', account_views.login, {'template_name': 'accounts/login_school.html', 'school': school, 'default_redirect': '/home'}),
    (r'^save$', 'save', {'Section': Section, 'UserData': UserData}),
    (r'^course/(?P<course_id>\d+)?', 'course', {'Course': Course, 'Section': Section, 'school': school}),
    (r'^import$', 'import_student', {'school': school, 'importer': importer, 'UserData': UserData}),
    (r'^(?P<user_code>[0-9a-f]{40})(?P<term_id>\d+)/$', 'public', {'school': school, 'Term': Term, 'UserData': UserData, 'Section': Section, 'template_name': 'school/umass/public.html'}),
    (r'^(?P<user_code>[0-9a-f]{40})(?P<term_id>\d+)/pdf$', 'pdf_course', {'school': school, 'Term': Term, 'UserData': UserData}),
    (r'^(?P<user_code>[0-9a-f]{40})(?P<term_id>\d+)/pdf-exams$', 'pdf_exam', {'school': school, 'Term': Term, 'Final': Final, 'UserData': UserData}),
    (r'^(?P<user_code>[0-9a-f]{40})(?P<term_id>\d+)/ics$', 'ics', {'school': school, 'Term': Term, 'UserData': UserData}),
    (r'^(?P<term_name>.*?\d{4})/$', 'calendar', {'school': school, 'template_name': 'school/amherst/calendar.html', 'Term': Term, 'Major': Major, 'Section': Section, 'UserData': UserData, 'import_tab': settings.STUDENT_IMPORT, 'geneds': settings.GENEDS}),
    (r'^(?P<term_name>.*?\d{4})/share$', 'share', {'school': school, 'Term': Term}),
    (r'^(?P<term_name>.*?\d{4})/search/$', 'search', {'Term': Term, 'Major': Major, 'Course': Course, 'allow_geneds': True}),
    (r'^(?P<term_name>.*?\d{4})/search/(?P<major_id>\d+)$', 'search', {'Term': Term, 'Major': Major, 'Course': Course, 'allow_geneds': True}),
    (r'^(?P<term_name>.*?\d{4})/search/(?P<major_id>\d*)/(?P<course_number>.*?)$', 'search', {'Term': Term, 'Major': Major, 'Course': Course, 'allow_geneds': True}),
    (r'^courses/(?P<term_name>.*?\d{4})/(?P<major_name>.*?)/(?P<course_number>.*?)$', 'course_listing', {'Term': Term, 'Major': Major, 'Course': Course, 'Section': Section, 'school': school}),
    (r'^locations/(?P<location_name>.*?)$', 'location_listing', {'Location': Location, 'school': school}),
)
