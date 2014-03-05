from django.conf.urls.defaults import *
from schedr.uri.models import Term, Major, Course, Section, Location, UserData, Final
from schedr.base.models import School
from schedr.uri import settings
from schedr.accounts import views as account_views

school = School.objects.get(name='uri')

urlpatterns = patterns('schedr.school.views',
    (r'^$', 'index', {'school': school, 'Term': Term}),
    (r'^save$', 'save_old', {'Section': Section, 'UserData': UserData}),
    (r'^login$', account_views.login, {'template_name': 'accounts/login_school.html', 'school': school, 'default_redirect': '/home'}),
    (r'^course/(?P<course_id>\d+)$', 'course', {'Course': Course, 'Section': Section, 'school': school}),
    (r'^course/(?P<course_id>\d+)/desc$', 'course_desc', {'Course': Course}),
    (r'^(?P<user_code>[0-9a-f]{40})(?P<term_id>\d+)/$', 'public', {'school': school, 'Term': Term, 'UserData': UserData, 'Section': Section, 'template_name': 'school/uri/public.html'}),
    (r'^(?P<user_code>[0-9a-f]{40})(?P<term_id>\d+)/pdf$', 'pdf_course', {'school': school, 'Term': Term, 'UserData': UserData}),
    (r'^(?P<user_code>[0-9a-f]{40})(?P<term_id>\d+)/pdf-exams$', 'pdf_exam', {'school': school, 'Term': Term, 'Final': Final, 'UserData': UserData}),
    (r'^(?P<user_code>[0-9a-f]{40})(?P<term_id>\d+)/ics$', 'ics', {'school': school, 'Term': Term, 'UserData': UserData}),
    (r'^(?P<term_name>.*?\d{4})/$', 'calendar', {'school': school, 'template_name': 'school/uri/calendar.html', 'Term': Term, 'Major': Major, 'Section': Section, 'UserData': UserData, 'import_tab': settings.STUDENT_IMPORT, 'geneds': settings.GENEDS}),
    (r'^(?P<term_name>.*?\d{4})/save$', 'save', {'Section': Section, 'UserData': UserData, 'Term': Term}),
    (r'^(?P<term_name>.*?\d{4})/register$', 'finalize', {'template_name': 'school/uri/register.html', 'Term': Term, 'school': school, 'UserData': UserData}),
    (r'^(?P<term_name>.*?\d{4})/search/$', 'search', {'Term': Term, 'Major': Major, 'Course': Course, 'allow_geneds': True}),
    (r'^(?P<term_name>.*?\d{4})/search/(?P<major_id>\d+)$', 'search', {'Term': Term, 'Major': Major, 'Course': Course, 'allow_geneds': True}),
    (r'^(?P<term_name>.*?\d{4})/search/(?P<major_id>\d*)/(?P<course_number>.*?)$', 'search', {'Term': Term, 'Major': Major, 'Course': Course, 'allow_geneds': True}),
    (r'^courses/(?P<term_name>.*?\d{4})/(?P<major_name>.*?)/(?P<course_number>.*?)$', 'course_listing', {'Term': Term, 'Major': Major, 'Course': Course, 'Section': Section, 'school': school}),
    (r'^locations/(?P<location_name>.*?)$', 'location_listing', {'Location': Location, 'school': school}),
)
