from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.core.urlresolvers import reverse
from schedr.base.models import School
from django.template import Context, loader, RequestContext
from django.views.decorators.cache import cache_page
from django.utils.hashcompat import sha_constructor
from django.shortcuts import render_to_response
from schedr.base.models import SchedrUser
from schedr.base.decorators import schedr_users_only


import colorsys

import calendar as cal
from django.utils import simplejson as json
import icalendar
from reportlab.pdfgen import canvas
from reportlab.lib import pagesizes
import datetime
from urllib import quote

from django.core.mail import EmailMessage
from django.template.loader import render_to_string

email_to = ['trpetr@gmail.com']

def js_error(request, school, term_name):
    msg = EmailMessage('[Schedr] JS Exception: %s (%s)' % (request.REQUEST.get('msg', '(blank)'), request.user.username), render_to_string('emails/js_exception.html', {'request': request, 'school': school, 'term_name': term_name, 'msg': request.REQUEST.get('msg', None), 'url': request.REQUEST.get('url', None), 'num': request.REQUEST.get('num', '???'), 'useragent': request.META.get('HTTP_USER_AGENT', '???'), 'data': request.REQUEST.get('data', '-- blank --')}), 'no-reply@schedr.com', email_to)
    msg.content_subtype = 'html'
    msg.send()
    return HttpResponse("OK")

def track(request, track_name, MajorTrack, template_name='umass/tracks/%s.html'):
    try:
        mt = MajorTrack.objects.get(name=track_name)
    except MajorTrack.DoesNotExist:
        raise Http404()

#    results = ([], [], [], [], [], [], [], [])
#    for rq in mt.requiredcourse_set.all():
#        results[rq.semester].append(rq)
#
#    data = []
#
#    i = False
#    while not i:
#        row = []
#        i = True
#        for a in results:
#            if len(a) > 0:
#                i = False
#                row.append(a.pop(0))
#            else:
#                row.append(None)
#        data.append(row)
    return render_to_response(template_name % mt.name, {'mt': mt, 'user': request.user})
    

def share(request):
    return HttpResponse()

def index(request, school, Term):
    if school.name == 'northwestern':
        tname = 'spring2010'
    elif school.name == 'umass':
        tname = 'fall2010'
    else:
        tname = 'fall2010'
#    newest_term = Term.objects.filter(visible=True)[0]
    return HttpResponseRedirect('/%s/%s/' % (school.name, tname))

def finalize(request, school, term_name, Term, UserData, template_name):
    try:
        term = Term.objects.get(name=term_name)
    except Term.DoesNotExist:
        return HttpResponseRedirect('/%s/' % school.name)

    if (not request.user.is_authenticated()) or (request.user.schedruser.school != school):
	return HttpResponseRedirect('/account/login?next=/%s/%s/register' % (school.name, term.name))

    courses = {}
    for ud in UserData.objects.filter(user=request.user.schedruser, section__course__term=term):
        if courses.has_key(ud.section.course):
            courses[ud.section.course].append(ud.section)
        else:
            courses[ud.section.course] = [ud.section]

    return render_to_response(template_name, {'term': term, 'school': school, 'courses': courses, 'user': request.user})

@schedr_users_only
def calendar(request, school, term_name, Term, Major, Section, UserData, template_name='school/base/calendar.html', import_tab=False, geneds=None):
#    if not request.user.is_superuser:
#        return render_to_response('brb.html', {})
    try:
        term = Term.objects.get(name=term_name)
    except Term.DoesNotExist:
        return HttpResponseRedirect('/' + school.name + '/')

    if request.user.schedruser.school != school:
        return HttpResponseRedirect("/account/login?next=/%s/%s/" % (school.name, term.name))

    terms = Term.objects.filter(visible=True)

    for t in terms:
        if t == term:
            t.current = True

    request.user.schedruser.last_useragent = request.META['HTTP_USER_AGENT'];
    request.user.schedruser.last_view = datetime.datetime.now()
    request.user.schedruser.save()

    trident = "MSIE" in request.META['HTTP_USER_AGENT'] or "Trident" in request.META['HTTP_USER_AGENT']

    return render_to_response(template_name, {'school': school, 'terms': terms, 'term': term, 'user': request.user, 'majors': Major.objects.all(), 'data': request.user.schedruser.saved_data(term, school, Section, UserData), 'import_tab': import_tab, 'geneds': geneds, 'trident': trident})


@schedr_users_only
def import_student(request, school, importer, UserData):
    if request.user.schedruser.school != school:
        raise Http404('wrong school')

    term = None

    try:
        username = request.POST['username']
        password = request.POST['password']
        sections = importer.import_student(username, password)
        term = sections[0].course.term
    except:
        response = HttpResponseRedirect(request.META.get('HTTP_REFERER', 'http://www.schedr.com/%s/' % school.name))
        response.set_cookie('schedr_message', quote('Unable to import schedule<br>Invalid username or password'), 5)
        return response

    if len(sections) == 0:
        if term:
            response = HttpResponseRedirect('http://www.schedr.com/%s/%s/' % (school.name, term.name))
        else:
            response = HttpResponseRedirect('http://www.schedr.com/%s/' % (school.name))
        response = HttpResponseRedirect('/%s/' % (school.name))
        response.set_cookie('schedr_message', quote('Unable to import schedule<br>Invalid username or password'), 5)
        return response

    term = sections[0].course.term

    UserData.objects.filter(user=request.user.schedruser, section__course__term=term).delete()
    for section in sections:
        ud = UserData(user=request.user.schedruser, section=section)
        ud.save()

    response = HttpResponseRedirect(term.get_absolute_url())
    response.set_cookie('schedr_message', quote("Imported %s successfully!" % term), 5)
    return response

def search(request, Term, Major, Course, term_name, major_id='', course_number='', allow_geneds=False, max_results=200):
    try:
        term = Term.objects.get(name=term_name)
    except Term.DoesNotExist:
        raise Http404("No such term")

    searchargs = {}
    if allow_geneds and request.GET.get('gened', '') != '':
        for gened in request.GET['gened'].split(','):
            searchargs[str("gened_%s" % gened)] = True

    if request.GET.get('times', '') != '':
        searchargs['morning'] = False
	searchargs['afternoon'] = False
	searchargs['evening'] = False
        for letter in request.GET['times']:
            if letter == 'M':
                searchargs['morning'] = True
            elif letter == 'A':
                searchargs['afternoon'] = True
            elif letter == 'E':
                searchargs['evening'] = True
            

    if major_id == '':
        majors = Major.objects.all()
    else:
        try:
            majors = [Major.objects.get(id=major_id)]
        except Major.DoesNotExist:
            majors = []

    more_results = False

    jm = []
    for major in majors:
        jc = []
        for course in major.course_set.filter(term=term, number__startswith=course_number, **searchargs):
            jc.append(course.json())
            max_results = max_results - 1
            if max_results == 0:
                more_results = True
                break
        if len(jc) > 0:
            jm.append("\"%s\":[%s]" % (major.name, ','.join(jc)))
        if max_results == 0:
            break

    data = "{\"response\":{%s},\"more\":%s}" % (','.join(jm), 'true' if more_results else 'false')

    response = HttpResponse(data, mimetype="application/json")
#    response['Expires'] = (datetime.datetime.now() + datetime.timedelta(1)).strftime("%a, %d %b %Y %H:%M:%S %Z")
    return response

def course_desc(request, course_id, Course):
    try:
        course = Course.objects.get(id=course_id)
    except:
        raise Http404()

    response = HttpResponse(course.description)
    response['Expires'] = (datetime.datetime.now() + datetime.timedelta(1)).strftime("%a, %d %b %Y %H:%M:%S %Z")
    return response

def course(request, course_id, school, Course, Section):
    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        raise Http404("No such Course")

    c = {}
    ins = {}
    loc = {}
    
    for s in Section.objects.filter(course=course):
        s.export(c, ins, loc)

    data = {'response': {'courses': {course_id: {'name': course.name(), 'title': course.title, 'url': course.get_absolute_url(), 'sec': c, 'credits': course.credits_array()}}, 'ins': ins, 'loc': loc}}
    
    return HttpResponse(json.dumps(data), mimetype="application/json")

def save_old(request, Section, UserData, user=None):
    if user is None:
        user = request.user

    if not user.is_authenticated():
        return HttpResponse('Need to login', status=401)

    if request.method == 'POST':
        terms = set()
        sections = []
        for section_id in json.loads(request.POST['data']):
            s = Section.objects.get(id=section_id)
            sections.append(s)
            terms.add(s.course.term_id)
        UserData.objects.filter(user=user, section__course__term__id__in=terms).delete()
        for section in sections:
            ud = UserData(user=user.schedruser, section=section)
            ud.save()
        user.schedruser.updated = True
        user.schedruser.save()
        return HttpResponse('', status=200)
    return HttpResponse('Invalid data', status=400)

def save(request, term_name, Section, UserData, Term, user=None):
    if user is None:
        user = request.user

    if not user.is_authenticated():
        return HttpResponse('Need to login', status=401)

    try:
        term = Term.objects.get(name=term_name)
    except Term.DoesNotExist:
        return HttpResponse(status=404)
   
    if request.method == 'POST':
        sections = []
        for section_id in json.loads(request.POST['data']):
            try:
                s = Section.objects.get(id=section_id)
                sections.append(s)
            except Section.DoesNotExist:
                pass
        UserData.objects.filter(user=user, section__course__term=term).delete()
        for section in sections:
            ud = UserData(user=user.schedruser, section=section)
            ud.save()
	user.schedruser.updated = True
        user.schedruser.last_useragent = request.META['HTTP_USER_AGENT']
        user.schedruser.save()
        return HttpResponse('', status=200)
    return HttpResponse('Invalid data', status=400)

def location_listing(request, location_name, school, Location, template_name='listing/location.html'):
    try:
        loc = Location.objects.get(name=location_name)
    except Location.DoesNotExist:
        raise Http404('Invalid location')

    return render_to_response(template_name, {'location': loc, 'school': school, 'user': request.user})

def course_listing(request, term_name, major_name, course_number, school, Term, Major, Course, Section, template_name='listing/course.html'):
    try:
        term = Term.objects.get(name=term_name)
    except Term.DoesNotExist:
        raise Http404('Invalid term')

    try:
        major = Major.objects.get(name=major_name)
    except Major.DoesNotExist:
        raise Http404('Invalid major')

    try:
        course = Course.objects.get(major=major, term=term, number=course_number)
    except Course.DoesNotExist:
        raise Http404('Invalid course')


    c = {}
    ins = {}
    loc = {}
    
    tba = set()
    all_tba = True

    for s in Section.objects.filter(course=course):
        if s.tba:
            tba.add(s)
	else:
            all_tba = False
        s.export(c, ins, loc)

    data = {'courses': {course.id: {'name': course.name(), 'title': course.title, 'url': course.get_absolute_url(), 'sec': c}}, 'ins': ins, 'loc': loc}

    return render_to_response(template_name, {'course': course, 'all_tba': all_tba, 'tba': tba, 'data': json.dumps(data), 'school': school, 'user': request.user, 'term': term})
    
def public(request, user_code, school, term_id, Term, Section, UserData, template_name='school/base/public.html'):
    try:
        user = SchedrUser.objects.get(code=user_code)
    except SchedrUser.DoesNotExist:
        raise Http404("Invalid code")

    if user.school != school:
        raise Http404("Invalid code")

    try:
        term = Term.objects.get(id=term_id)
    except Term.DoesNotExist:
        raise Http404("Invalid code")

    ua = request.META.get('HTTP_USER_AGENT', '???')
    trident = "MSIE" in ua or "Trident" in ua

    return render_to_response(template_name, {'school': school, 'term': term, 'user': request.user, 'view_user': user, 'data': user.saved_data(term, school, Section, UserData), 'trident': trident})
    
def pdf_exam(request, user_code, term_id, school, Term, UserData, Final):
    try:
        user = SchedrUser.objects.get(code=user_code)
    except SchedrUser.DoesNotExist:
        raise Http404("Invalid code")

    if user.school != school:
        raise Http404("Invalid school")

    try:
        term = Term.objects.get(id=term_id)
    except Term.DoesNotExist:
        raise Http404("Invalid code")

    if not term.finals_visible:
        raise Http404("Finals not available yet")

    response = HttpResponse(mimetype='application/pdf')
    response['Content-Disposition'] = 'attachment; filename=%s-%s-exams.pdf' % (user.first_name, term.name)

    buffer = user.generate_exam_pdf(term, UserData, Final)
    if buffer is None:
        return HttpResponse("No finals! You are the freakin man!")
    response.write(buffer.getvalue())
    buffer.close()

    return response

def pdf_course(request, user_code, term_id, school, Term, UserData):
    try:
        user = SchedrUser.objects.get(code=user_code)
    except SchedrUser.DoesNotExist:
        raise Http404("Invalid code")

    if user.school != school:
        raise Http404("Invalid school")

    try:
        term = Term.objects.get(id = term_id)
    except Term.DoesNotExist:
        raise Http404("Invalid code")

    response = HttpResponse(mimetype='application/pdf')
    response['Content-Disposition'] = "attachment; filename=%s-%s.pdf" % (user.first_name, term.name)

    buffer = user.generate_course_pdf(term, UserData)
    response.write(buffer.getvalue())
    buffer.close()

    return response

def ics(request, user_code, term_id, school, Term, UserData):
    try:
        user = SchedrUser.objects.get(code=user_code)
    except SchedrUser.DoesNotExist:
        raise Http404("Invalid code")

    if user.school != school:
        raise Http404("Invalid school")

    try:
        term = Term.objects.get(id=term_id)
    except Term.DoesNotExist:
        raise Http404("Invalid code")

    response = HttpResponse(mimetype='text/calendar')
    filename = '%s-%s.ics' % (user.username, term.name)
    response['Filename'] = filename
    response['Content-Disposition'] = "attachment; filename=%s" % filename
    response.write(user.generate_ics(term, UserData))

    return response
