from schedr.util import PeopleSoft9, PeopleSoftParser, parse_shortcut
import re, math
from datetime import time, datetime, date, timedelta
from sets import Set
from schedr.umass.models import Term, Major, Course, LocationImport, Instructor, Location, Section
from schedr import util
import os
from glob import glob
from sgmllib import SGMLParser
from schedr import settings
from schedr.util import RMPParser
import urllib2, cookielib

from schedr.parsers import PullParser, StartTag, EndTag, Tag

RE_COURSE = re.compile(r'^(.*?) (.*?) (.*)$')
RE_SID = re.compile(r'^(.*?)-(.*?)\((.*?)\)$')
RE_STATUS = re.compile(r'^/cs/heproda/cache/PS_CS_STATUS_(.*?)_ICN_1.gif$')

def parse_dt(str):
    if str == 'TBA': return None
    days, start, junk, end = str.split(' ')
    s = datetime.strptime(start, '%I:%M%p').time()
    e = datetime.strptime(end, '%I:%M%p').time()
    return (s, e, 'Mo' in str, 'Tu' in str, 'We' in str, 'Th' in str, 'Fr' in str)

def current_term():
    dt = datetime.now()
    term_id = (dt.year - 1900) * 10
    if dt.month > 1 and dt.month < 7:
        term_id = term_id + 3
    else:
        term_id = term_id + 7
    return term_id

class SPIRE(PeopleSoft9):
    regex_expand = re.compile(r"<a name='\$ICField106\$hviewall\$(\d+)'.*?>View All")

    def __init__(self, debug=False):
        PeopleSoft9.__init__(self, "https://spire.umass.edu/psp/heproda/EMPLOYEE/HRMS/", "https://spire.umass.edu/psc/heproda/EMPLOYEE/HRMS/c/COMMUNITY_ACCESS.CLASS_SEARCH.GBL", icsid=True, debug=debug)

    def login(self, username="GUEST", password="GUEST"):
        return PeopleSoft9.login(self, username, password)

    def student_page(self):
        return self.get(url='https://spire.umass.edu/psc/heproda/EMPLOYEE/HRMS/c/SA_LEARNER_SERVICES.SSS_STUDENT_CENTER.GBL?FolderPath=PORTAL_ROOT_OBJECT.HCCC_ACADEMIC_RECORDS.HC_SSS_STUDENT_CENTER&IsFolder=false&IgnoreParamTempl=FolderPath%2cIsFolder&PortalActualURL=https%3a%2f%2fspire.umass.edu%2fpsc%2fheproda%2fEMPLOYEE%2fHRMS%2fc%2fSA_LEARNER_SERVICES.SSS_STUDENT_CENTER.GBL&PortalContentURL=https%3a%2f%2fspire.umass.edu%2fpsc%2fheproda%2fEMPLOYEE%2fHRMS%2fc%2fSA_LEARNER_SERVICES.SSS_STUDENT_CENTER.GBL&PortalContentProvider=HRMS&PortalCRefLabel=Student%20Center&PortalRegistryName=EMPLOYEE&PortalServletURI=https%3a%2f%2fspire.umass.edu%2fpsp%2fheproda%2f&PortalURI=https%3a%2f%2fspire.umass.edu%2fpsc%2fheproda%2f&PortalHostNode=HRMS&NoCrumbs=yes')

    def select_current_term(self):
        return self.select_term(current_term())

    def select_term(self, term_id):
        #return PeopleSoft9.select_term(self, term_id, {'UM_DERIVED_SA_UM_TERM_DESCR': term_id, 'CLASS_SRCH_WRK2_SSR_CLS_SRCH_TYPE$53$': '06', 'CLASS_SRCH_WRK2_SSR_CLS_SRCH_TYPE$53$$rad': '06'})
        self.term_id = term_id
        self.status = self.SEARCH_QUERY

    def browse_term(self, term_id):
        str = PeopleSoft9.browse_term(self, term_id, {'UM_DERIVED_SA_UM_TERM_DESCR': term_id, 'CLASS_SRCH_WRK2_SSR_CLS_SRCH_TYPE$53$': '04', 'CLASS_SRCH_WRK2_SSR_CLS_SRCH_TYPE$53$$rad': '04'})
        return str

    def view_section(self, id, p={}):
        return PeopleSoft9.view_section(self, id, p)

    def search(self, major, course='', expand=True):
        str = PeopleSoft9.search(self, {
		'ICType': 'Panel',
		'ICElementNum': '0',
		'ICXPos': '0', 'IXYPos': '0',
		'ICAction': 'CLASS_SRCH_WRK2_SSR_PB_CLASS_SRCH$144$',
		'ICFocus': '',
		'ICSaveWarningFilter': '0',
		'ICChanged': '-1',
		'ICResubmit': '0',
                'ICModalWidget': '0',
                'ICZoomGrid': '0',
                'ICZoomGridRt': '0',
                'ICModalLongClosed': '0',
                'ICActionPrompt': 'false',
                'ICTypeAheadID': '',
                'ICFind': '',
                'ICAddCount': '',
		'UM_DERIVED_SA_UM_TERM_DESCR': self.term_id,
		'CLASS_SRCH_WRK2_SUBJECT$68$': major,
		'CLASS_SRCH_WRK2_SSR_EXACT_MATCH1': 'E',
		'CLASS_SRCH_WRK2_CATALOG_NBR$76$': '',
		'CLASS_SRCH_WRK2_ACAD_CAREER': '',
		'CLASS_SRCH_WRK2_SSR_OPEN_ONLY$chk': 'N',
		'CLASS_SRCH_WRK2_SESSION_CODE$126$': 'U1',
		'CLASS_SRCH_WRK2_CLASS_NBR$128$': '',
		'CLASS_SRCH_WRK2_INCLUDE_CLASS_DAYS': 'I',
		'CLASS_SRCH_WRK2_SSR_EXACT_MATCH2': 'E'
	})

        if expand:
            for id in self.regex_expand.findall(str):
                str = self.expand(id)

        return str

    def expand(self, id):
        return self.request({'ICAction': '$ICField106$hviewall$' + id})

regex_cd_title = re.compile(r'^(.*?) +(.*?) - (.*)$')

class ExtraCourseDataParser(SGMLParser):
    def __init__(self, term, verbose=False):
        SGMLParser.__init__(self)
        self.data = ''
        self.capture = False
        self.current_course_title = ''
        self.current_credits = ''
        self.current_desc = ''
        self.status = 0
        self.major = Major.objects.all()[0]
        self.term = term
        self.verbose = verbose

    def parse_course(self):
        data = self.current_course_title.split(' ')
        try: 
            if self.major.name != data[0]:
                self.major = Major.objects.get(name=data[0])
            course = Course.objects.get(term=self.term, major=self.major, number=data[1])
        except:
            print "Error: %s" % data
            return
        if self.verbose:
            print "%s - Credits: %s" % (course, self.current_credits)
        if self.current_credits == '1.5':
            self.current_credits = '2'
            print "Decimal!"
        elif self.current_credits == '0.5':
            self.current_credits = '1'
            print "decimal!"
        cred = self.current_credits.split(' - ')
        if len(cred) == 0:
            course.credits = None
            course.credits_max = None
        elif len(cred) == 1:
            course.credits = cred[0]
            course.credits_max = None
        elif len(cred) == 2:
            course.credits = cred[0]
            course.credits_max = cred[1]
        print "   Desc: %s" % self.current_desc
        course.description = self.current_desc
        #course.save()

    def start_span(self, attrs):
        if get_attr(attrs, 'class') == 'PALEVEL0SECONDARY':
            self.capture = True
            self.status = 0 
        elif self.status == 1 and get_attr(attrs, 'class') == 'PSEDITBOX_DISPONLY':
            self.capture = True
        elif self.status == 2 and get_attr(attrs, 'class') == 'PSLONGEDITBOX':
            self.capture = True

    def end_span(self):
        if self.capture:
            if self.status == 0:
                self.current_course_title = self.data.strip()
                self.status = -1
            elif self.status == 1:
                self.current_credits = self.data.strip()
                self.status = -1
            elif self.status == 2:
                self.current_desc = self.data.strip()
                self.parse_course()
                self.status = -1
            self.data = ''
            self.capture = False

    def start_label(self, attrs):
        if get_attr(attrs, 'for') == 'SSR_CLS_DTL_WRK_UNITS_RANGE':
            self.status = 1

    def start_table(self, attrs):
        if get_attr(attrs, 'width') == '537' and get_attr(attrs, 'id') == 'ACE_width':
            self.status = 2
    

    def handle_data(self, data):
        if self.capture:
            self.data = self.data + data

class CourseDataParser(SGMLParser):
    def __init__(self, verbose=False):
        SGMLParser.__init__(self)
        self.data = ''
        self.capture = False
        self.longedit = False
        self.disponly = False
        self.palevel = False
        self.credits = ''
        self.prereq = ''
        self.desc = ''
        self.major = ''
        self.number = ''
        self.title = ''

    def start_label(self, attrs):
        self.capture = True

    def end_label(self):
        if self.capture:
            self.label = self.data.strip()
            self.data = ''
            self.capture = False

    def start_span(self, attrs):
        if get_attr(attrs, 'class') == 'PSLONGEDITBOX':
            self.capture = True
            self.longedit = True
        elif get_attr(attrs, 'class') == 'PSEDITBOX_DISPONLY':
            self.capture = True
            self.disponly = True
        elif get_attr(attrs, 'class') == 'PALEVEL0SECONDARY':
            self.capture = True
            self.palevel = True

    def end_span(self):
        if self.capture:
            if self.longedit:
                self.desc = self.data.strip().replace('\r', ' ')
                self.longedit = False
            elif self.disponly:
                if self.label == 'Units':
                    self.credits = self.data.strip()
                elif self.label == 'Enrollment Requirement':
                    self.prereq = self.data.strip()
                self.disponly = False
            elif self.palevel:
                m = regex_cd_title.match(self.data.strip())
                if m:
                    self.major = m.group(1)
                    self.number = m.group(2)
                    self.title = m.group(3)
                else:
                    self.major, self.number, self.title = None, None, None
                self.palevel = False
            self.data = ''
            self.capture = False

    def handle_data(self, data):
        if self.capture:
            self.data = self.data + data

regex_courseid = re.compile(r'id=\'DERIVED_CLSRCH_COURSE_TITLE_LONG\$(\d+)')
regex_credits = re.compile(r'^(\d+) - (\d+)$')

def parse_extra_course_data(verbose=False):
    from schedr.parse import PullParser, StartTag
    from glob import glob
    for term in Term.objects.filter(active=True):
        print "Doing %s" % term
        for major in Major.objects.all():
            print "ma: %s" % major
            for course in Course.objects.filter(major=major, term=term).exclude(desc_id=None):
                if not os.path.exists("/home/tpetr/cache/schedr/umass/%s/%s/%s.html" % (term.school_id, major.name, course.desc_id)):
                    continue
                print course
                fp = open("/home/tpetr/cache/schedr/umass/%s/%s/%s.html" % (term.school_id, major.name, course.desc_id), "r")
                p = PullParser(fp)
                for label in p.tags(StartTag('label', {'class': 'PSEDITBOXLABEL'})):
                    if label['for'] == 'SSR_CLS_DTL_WRK_UNITS_RANGE':
                        span = p.seek(StartTag('span', {'class': 'PSEDITBOX_DISPONLY'}))
                        str_credits = p.get_text().strip()
                        print "Credits: %s" % str_credits

                for span in p.tags(StartTag('td', {'class': 'PAGROUPBOXLABELLEVEL1'})):
                    type = p.get_text().lower()
                    if type == 'description':
                        blah = p.seek(StartTag('span', {'class': 'PSLONGEDITBOX'}))
                        str_desc = p.get_text().strip()
                        print "DESC: %s" % desc
                        course.description = desc
                        #course.save()
                fp.close()
            break
        break

title_regex = re.compile(r'Final Exam Schedule for (.*?) (\d+)$')
final_date_regex = re.compile(r'^[A-Za-z]+ (\d+)/(\d+)$')

class FinalExamParser(SGMLParser):
    def __init__(self, verbose=False, unknown_locations=None):
        SGMLParser.__init__(self)
        self.row = 0
        self.col = 0
        self.capture = False
        self.data = ''
        self.current_major_name = ''
        self.current_course_number = ''
        self.current_section_group = ''
        self.current_final_date = ''
        self.current_final_time = ''
        self.current_final_loc = ''
        self.verbose = verbose
        self.unknown_locations = unknown_locations

    def start_title(self, attrs):
        self.capture = True

    def end_title(self):
        m = title_regex.match(self.data.strip())
        if m:
            name = m.group(1).lower() + m.group(2)
            try:
                self.term = Term.objects.get(name=name)
            except:
                print "Unknown term: %s" % name
                return

    def start_table(self, attrs):
        if (get_attr(attrs, 'cellspacing') == '0' and get_attr(attrs, 'cellpadding') == '2' and get_attr(attrs, 'border') == '1'):
            self.row = 0
            self.col = 0
            self.inside_table = True

    def end_table(self):
        self.inside_table = False

    def start_td(self, attrs):
        if self.inside_table:
            self.capture = True

    def end_td(self):
        if self.capture:
            if self.row > 0:
                if self.col == 0:
                    self.current_major_name = self.data.strip()
                elif self.col == 1:
                    self.current_course_number = self.data.strip()
                elif self.col == 2:
                    self.current_section_group = self.data.strip()
                elif self.col == 3:
                    self.current_final_date = self.data.strip()
                elif self.col == 4:
                    self.current_final_time = self.data.strip()
                elif self.col == 5:
                    self.current_final_loc = self.data.strip()
            self.col = self.col + 1
            if self.col == 7:
                if self.row > 0:
                    self.parse_final()
                self.row = self.row + 1
                self.col = 0
            self.data = ''
            self.capture = False

    def handle_data(self, data):
        if self.capture:
            self.data = self.data + data

    def parse_date(self, str):
        m = final_date_regex.match(str)
        if m:
            return date(self.term.year, int(m.group(1)), int(m.group(2)))
        return None

    def parse_time(self, str):
        h, m = str.split(':')
        h = int(h)
        if h < 8:
            h = h + 12
        m = int(m)
        return time(h, m)

    def parse_location(self, str):
        if str == 'BOYDGYM':
            str = 'BOYD Gym'
        elif str == 'BOWK AUD':
            str = 'STK Bowker Auditorium'
        loc, room = str.split(' ',1)
        try:
            l = Location.objects.get(name=loc)
        except:
            if self.unknown_locations:
                self.unknown_locations.append(str)
            if verbose:
                print "Unknown location: %s" % loc
            l = None
        return (l, room)

    def parse_final(self):
        g = self.current_section_group
        try:
            course = Course.objects.get(major__name=self.current_major_name, number=self.current_course_number)
        except:
            print "No such course: %s %s" % (self.current_major_name, self.current_course_number)
            return

        final_date = self.parse_date(self.current_final_date)
        final_start = self.parse_time(self.current_final_time)
        final_end = time(final_start.hour + 2, final_start.minute)

        final_loc, final_room = self.parse_location(self.current_final_loc)

        f = Final.objects.import_object(course=course, group_literal=self.current_section_group, date=final_date, start=final_start, end=final_end, location=final_loc, room=final_room)

        if g.isdigit(): 
            g = "0%s" % g
        sections = Section.objects.filter(course__major__name=self.current_major_name, course__number=self.current_course_number, group_literal=g).exclude(type=Section.DIS)
        if len(sections) == 0:
            g = self.current_section_group
            sections = Section.objects.filter(course__major__name=self.current_major_name, course__number=self.current_course_number, group_literal=g).exclude(type=Section.DIS)

        if len(sections) > 0:
            f.section = sections[0]
            f.save()

        if self.verbose:
            print "%s" % f

        return f
        
        

def parse_finals(verbose=False, unknown_locations=None):
    agent = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookielib.LWPCookieJar()))
    request = urllib2.Request("http://www.umass.edu/registrar/Student/exams/AllDepts.html")
    f = FinalExamParser(verbose=verbose, unknown_locations=unknown_locations)
    f.feed(agent.open(request).read())
    return f

student_regex = re.compile(r'^(\d{4})\d(\d{3})$')
student2_regex = re.compile(r'\((\d+)\)', re.MULTILINE)

def get_attr(attrs, name):
    for k,v in attrs:
        if k == name:
            return v
    return ''

def get_attrs(attrs, *args):
    results = []
    for arg in args:
        for k, v in attrs:
            if k == arg:
                results.append(v)
                break;
        results.append('')
    return tuple(results)

class StudentParser(SGMLParser):
    def __init__(self):
        SGMLParser.__init__(self)
        self.inside_table = False
        self.capture = False
        self.data = ''
        self.section_ids = []

    def reset(self):
        SGMLParser.reset(self)
        self.inside_table = False
        self.capture = False
        self.data = ''
        self.section_ids = []

    def start_table(self, attrs):
        self.inside_table = get_attr(attrs, 'id') == 'STDNT_WEEK_SCHD$scroll$0'

    def end_table(self):
        self.inside_table = False

    def start_span(self, attrs):
        self.capture = self.inside_table and get_attr(attrs, 'class') == 'PSHYPERLINKDISABLED'

    def end_span(self):
        if self.capture:
            match = student2_regex.search(self.data)
            if match:
                self.section_ids.append(match.group(1))
            self.data = ''
            self.capture = False

    def handle_data(self, data):
        if self.capture:
            self.data = self.data + data

def import_student(username, password):
    match = student_regex.match(username)
    if match is not None:
        username = "A%s%s" % (match.group(1), match.group(2))

    s = SPIRE()
    s.login(username, password)
    str = s.student_page()
    s.logout()

    sp = StudentParser()
    sp.feed(str)
    sp.close()

    return [Section.objects.get(school_id=sid) for sid in sp.section_ids]

def create_current_term():
    dt = datetime.now()
    term_id = (dt.year - 1900) * 10
    sem = 0
    semstr = ''
    if dt.month > 1 and dt.month < 7:
        term_id = term_id + 3
        semstr = 'spring'
        sem = Term.SPRING
    else:
        term_id = term_id + 7
        semstr = 'fall'
        sem = Term.FALL

    t = Term(name="%s%i" % (semstr, dt.year), year=dt.year, semester=sem, school_id=term_id)
    t.save()
    return t

class TermParser(SGMLParser):
    def __init__(self):
        SGMLParser.__init__(self)
        self.terms = {}
        self.inside_terms = False
        self.current_id = None
        self.capture = False
        self.data = ''
        self.term_regex = re.compile(r'^\n?(\d{4}) (.*)$')

    def reset(self):
        SGMLParser.reset(self)
        self.terms = {}
        self.inside_terms = False
        self.current_id = None
        self.capture = False
        self.data = ''

    def start_select(self, attrs):
        self.inside_terms = get_attr(attrs, 'id') == 'UM_DERIVED_SA_UM_TERM_DESCR'

    def end_select(self):
        self.inside_terms = False

    def start_option(self, attrs):
        if self.inside_terms:
            self.current_id = get_attr(attrs, 'value')
            self.capture = True

    def end_option(self):
        if self.capture and self.current_id != '':
            match = self.term_regex.match(self.data)
            if match:
                self.terms[self.current_id] = {'year': int(match.group(1)), 'sem': match.group(2)}
            self.data = ''
            self.capture = False
    
    def handle_data(self, data):
        if self.capture:
            self.data = self.data + data

def terms():
    s = SPIRE()
    str = s.login()
    s.logout()
    t = TermParser()
    t.feed(str)
    t.close()
    return t.terms
   
class MajorParser(SGMLParser):
    def __init__(self):
        SGMLParser.__init__(self)
        self.majors = {}
        self.inside_majors = False
        self.current_name = None
        self.major_regex = re.compile(r'\n?[^ ]+[ ]+(.*)$')
        self.capture = False
        self.data = ''

    def reset(self):
        SGMLParser.reset(self)
        self.majors = {}
        self.inside_majors = False
        self.current_name = None
        self.capture = False
        self.data = ''

    def start_select(self, attrs):
        print "start_select: %r" % (attrs,)
        self.inside_majors = get_attr(attrs, 'id') == 'CLASS_SRCH_WRK2_SUBJECT$68$'
        print "inside_majors = %s" % self.inside_majors

    def end_select(self):
        self.inside_majors = False

    def start_option(self, attrs):
        print "start_option"
        if self.inside_majors:
            print "start_option inside majors!"
            self.current_name = get_attr(attrs, 'value')
            self.capture = True

    def end_option(self):
        if self.capture and self.current_name != '':
            match = self.major_regex.match(self.data)
            if match:
                self.majors[self.current_name] = match.group(1)
            self.data = ''
            self.capture = False

    def handle_data(self, data):
        if self.capture:
            self.data = self.data + data

def majors():
    s = SPIRE()
    str = s.login()
    s.logout()
    results = {}
    fp = open("/tmp/blah.html", "w")
    fp.write(str)
    fp.close()

    fp = open("/tmp/blah.html", "r")
    p = PullParser(fp)
    if p.seek(StartTag('select', eq={'id': 'CLASS_SRCH_WRK2_SUBJECT$68$'})):
        print "found select"
        for opt in p.tags(StartTag('option'), until=EndTag('select')):
            val = opt['value']
            if val:
                results[val] = p.get_text()

    p.close()
    return results
    
def import_majors():
    for name, title in majors().items():
        Major.objects.import_object(name=name, title=title)

def import_locations():
    from schedr.umass import data
    for name in data.LOCATIONS:
	loc = Location.objects.import_object(name=name, title=data.LOCATIONS[name]['title'])
        if data.LOCATIONS[name].has_key('map'):
            lat, lng, zoom = data.LOCATIONS[name]['map']
            loc.lat = lat
            loc.lng = lng
            loc.zoom = zoom
            loc.save()
	for regex, room in data.LOCATIONS[name]['imports']:
            LocationImport.objects.import_object(regex=regex, location=loc, room=room)
                

def cache_callback(term, major, data):
    if data.find('The search returns no results that match the criteria specified.') > -1:
        return
    filename = "/home/tpetr/cache/schedr/umass/%s-%s.html" % (term.school_id, major.name)
    fp = open(filename, "w")
    fp.write(data)
    fp.close()


def parse_rmp():
    from schedr.umass import data

    rmp = RMPParser()

    for filename in glob("/home/tpetr/cache/schedr/umass/rmp/*.html"):
        fp = open(filename, "r")
        rmp.feed(fp.read())
        fp.close()

    for name, rating_id, rating in rmp.instructors:
        if rating == '':
            continue
        if rating_id == '751115':
            name = 'Francoise Hamlin'
        elif rating_id == '920907':
            name = 'Adrian Espinola-Rocha'
        name = data.INSTRUCTOR_NICKNAMES.get(name, name)


        print "%s (%s) %s" % (name, rating_id, rating)
      
        try:
            ins = Instructor.objects.get(name=name)
        except Instructor.DoesNotExist:
            continue
        ins.rating_id = rating_id
        ins.rating = rating
        ins.save()

def cache_rmp(verbose=False):
    try:
        os.makedirs("/home/tpetr/cache/schedr/umass/rmp/")
    except:
        pass
    rmp = util.RateMyProfessors(1513, '/home/tpetr/cache/schedr/umass/rmp/')

    rmp.cache_all()
    
def cache_data(callback=None, threads=1, verbose=False):
    if callback is None:
        callback = cache_callback

    try:
        os.makedirs("/home/tpetr/cache/schedr/umass/")
    except:
        pass

    if verbose:
        print "Caching UMass Amherst data to /home/tpetr/cache/schedr/umass/"
    start = datetime.now()
    #util.cache_threaded(Term, Major, SPIRE, callback, threads=threads, verbose=verbose)
    s = SPIRE()
    s.login()
    for t in Term.objects.filter(active=True):
        s.select_term(t.school_id)
        for m in Major.objects.all():
            if verbose: print m.name
            fp = open("/home/tpetr/cache/schedr/umass/%s-%s.html" % (t.school_id, m.name), "w")
            fp.write(s.search(m.name))
            fp.close()
    s.logout()
    end = datetime.now()
    if verbose:
        print "Time: %s" % (end-start)

regex_cids = re.compile(r'\$ICField44\$scroll\$\d+.*?DERIVED_CLSRCH_SSR_CLASSNAME_LONG\$(\d+)')

def get_course_desc_ids(verbose=False):
    from schedr.parse import PullParser, StartTag
    s = SPIRE()
    s.login()
    for t in Term.objects.filter(active=True):
        s.select_term(t.school_id)
        for m in Major.objects.all():
            fp = open("/tmp/desc.html", "w")
            fp.write(s.search(m.name, expand=False))
            fp.close()
            fp = open("/tmp/desc.html", "r")
            p = PullParser(fp)
            p.seek(StartTag('table', {'id': '$ICField97$scroll$0'}))
            for span in p.tags(StartTag('span', {'class': 'SSSHYPERLINKBOLD'})):
                cstr = span.get_text()
                a = p.seek(StartTag('a', startswith={'id': 'DERIVED_CLSRCH_SSR_CLASSNAME_LONG$'}))
                try:
                    c = Course.objects.get(term=t, major=m, number=cstr.split(' ')[1])
                    print c
                    desc_id = a['id'].split('$')[1]
                    c.desc_id = desc_id
                    c.save()
                except Course.DoesNotExist: pass
            fp.close()
    s.logout
        
    
def load_course_descriptions():
    s = SPIRE()
    s.login()
    from schedr.parse import PullParser, StartTag
    re_course = re.compile(r'^.*? (.*?) - .*$') 
    re_course2 = re.compile(r'^.*? +(.*?) ')
    for t in Term.objects.filter(active=True):
        s.select_term(t.school_id)
        print "Term: %s" % t
        for m in Major.objects.all():
            str = s.search(m.name, expand=False)
            fp = open("/tmp/blah.html", "w")
            fp.write(str)
            fp.close()

            fp = open("/tmp/blah.html", "r")
            p = PullParser(fp)

            if not p.seek(StartTag('table', startswith={'id': '$ICField97$scroll$'})):
                print "No courses"
                fp.close()
                continue

            for span in p.tags(StartTag('span', {'class': 'SSSHYPERLINKBOLD'})):
                mat = re_course2.match(p.get_text())
                if not mat:
                    print "SHIT!"
                    continue
                try:
                    c = Course.objects.get(major=m, number=mat.group(1), term=t)
                except Course.DoesNotExist:
                    print "!!! %s %s does not exist" % (m, mat.group(1))
                    continue

                if c.description != '':
                    print "Skipping %s" % c
                    continue
                
                link = p.seek(StartTag('a', startswith={'id': 'DERIVED_CLSRCH_SSR_CLASSNAME_LONG$'}))
                id = link['id'].split('$')[1]
                
                str2 = s.view_section(id)
                fp2 = open("/tmp/blah2.html", "w")
                fp2.write(str2)
                fp2.close()

                fp2 = open("/tmp/blah2.html", "r")
                p2 = PullParser(fp2)

                p2.seek(StartTag('span', {'class': 'PALEVEL0SECONDARY'}))
                m1 = re_course.match(p2.get_text())
                if not m1: raise Exception("Can't match re_course")
                num = m1.group(1)
                try:
                    c = Course.objects.get(term=t, major=m, number=num)
                except Course.DoesNotExist: continue
                print c

                c.desc_id = id

                p2.seek(StartTag('label', {'for': 'SSR_CLS_DTL_WRK_UNITS_RANGE'}))
                p2.seek(StartTag('span', {'class': 'PSEDITBOX_DISPONLY'}))
                credits = p2.get_text()
                if ' - ' in credits:
                    blah = credits.split(' - ')
                    c.credits = int(round(float(blah[0])))
                    c.credits_max = int(round(float(blah[1])))
                    c.save()
                else:
                    c.credits = int(round(float(credits)))
                    c.credits_max = None
                    c.save()

                if p2.seek(StartTag('label', {'for': 'UM_DERIVED_SA_UM_GENED'})):
                    p2.seek(StartTag('span', {'class': 'PSEDITBOX_DISPONLY'}))
                    geneds = p2.get_text().strip()
                    if geneds != '':
                        for g in geneds.split(' '):
                            setattr(c, 'gened_%s' % g, True)
                        c.save()

                for td in p2.tags(StartTag('td', {'class': 'PAGROUPBOXLABELLEVEL1'})):
                    if p2.get_text() != 'Description': continue
                    p2.seek(StartTag('span', {'class': 'PSLONGEDITBOX'}))
                    c.description = p2.get_text()
                    c.save()
                    break

                fp2.close()
            fp.close()
    s.logout()
    

def cache_extra_data(verbose=False):
    s = SPIRE()
    s.login()
    from schedr.parse import PullParser, StartTag
    for t in Term.objects.filter(active=True):
        try:
            os.makedirs("/home/tpetr/cache/schedr/umass/%s/" % t.school_id)
        except:
            pass

        s.select_term(t.school_id)
        print "Term: %s" % t

        for m in Major.objects.all():
            try:
                os.makedirs("/home/tpetr/cache/schedr/umass/%s/%s/" % (t.school_id, m.name))
            except:
                pass

            print "   Major: %s" % m
            str = s.search(m.name, expand=False)

            fp = open("/tmp/blah.html", "w")
            fp.write(str)
            fp.close()

            fp = open("/tmp/blah.html", "r")
            p = PullParser(fp)

            if not p.seek(StartTag('table', startswith={'id': '$ICField97$scroll$'})):
                print "No courses"
                fp.close()
                break

            for span in p.tags(StartTag('span', {'class': 'SSSHYPERLINKBOLD'})):
                link = p.seek(StartTag('a', startswith={'id': 'DERIVED_CLSRCH_SSR_CLASSNAME_LONG$'}))
                id = link['id'].split('$')[1]
    

            for c in Course.objects.filter(term=t, major=m, description='').exclude(desc_id=None):
                print "      %s" % c
                fp = open("/home/tpetr/cache/schedr/umass/%s/%s/%s.html" % (t.school_id, m.name, c.desc_id), "w")
                fp.write(s.view_section(c.desc_id))
                fp.close()
                print "         Wrote: %s" % c.desc_id
            break

    s.logout()

class SPIREParser(PeopleSoftParser):
    days = (('Th', 'thu'), ('Mo', 'mon'), ('Tu', 'tue'), ('We', 'wed'), ('Fr', 'fri'))
    statuses = {'open': Section.OPEN, 'closed': Section.CLOSED, 'cancelled': Section.CANCELLED, 'waitlist': Section.WAITLIST}
    types = {'LEC': Section.LEC, 'DIS': Section.DIS, 'Discussion 01': Section.DIS, 'LAB': Section.LAB, 'PRA': Section.PCM, 'IND': Section.IND, 'Individualized Study': Section.IND, 'SEM': Section.SEM, 'DST': Section.DST, 'Dissertation/Thesis': Section.DST, 'STU': Section.STU, 'STS': Section.STS}

    regex_section = re.compile(r'^.*?-(.*?)\((.*?)\)$', re.M)
    regex_course = re.compile(r'^.*? (.*?) (.*)$', re.M)

    regex_group1 = re.compile(r'^([A-Z])L?\d+$')
    regex_group2 = re.compile(r'^([A-Z])$')
    regex_group3 = re.compile(r'^([A-Z])D\d+$')
    regex_group4 = re.compile(r'^([A-Z])L\d+$')

    STATUS_IMAGE_ATTR = 'class'
    STATUS_IMAGE_VALUE = 'SSSIMAGECENTER'

    SECTION_TABLE_CLASS = 'PSLEVEL1SCROLLAREABODYWBO'

    def __init__(self, major=None, *args, **kwargs):
        if major is None:
            major = Major.objects.all()[0]
        PeopleSoftParser.__init__(self, major=major, course_model=Course, section_model=Section, instructor_model=Instructor, *args, **kwargs)

#    def parse_gened(self, str):
#        res = {}
#        if str is None: return res
#        for g in str.split(' '):
#            res["gened_%s" % g] = True
#        return res

    def parse_group(self, str, type):
        str = str.split(' ')[0]
        group = 1
        m = None
        if type == Section.LEC:
            m = self.regex_group1.match(str)
            if m is None:
                m = self.regex_group2.match(str)
        elif type == Section.DIS:
            m = self.regex_group3.match(str)
        elif type == Section.LAB:
            m = self.regex_group4.match(str)

        if m != None:
            group = m.group(1)

        return (group, str)
        
def parse_data(verbose=False, unknown_locations=None):
    parse_shortcut(school_name='umass', cache_dir='/home/tpetr/cache', term_model=Term, major_model=Major, section_model=Section, parser=SPIREParser, verbose=verbose, unknown_locations=unknown_locations, imports=generate_location_imports())
    for c in Course.objects.filter(title__contains='\r'):
        c.title = c.title.replace('\r', '')
        c.save()

def generate_location_imports():
    imports = {}
    for li in LocationImport.objects.all():
        letter = li.regex[1:2].lower()
        if not imports.has_key(letter):
            imports[letter] = []
        try:
            imports[letter].append((li, re.compile(li.regex, re.IGNORECASE)))
        except:
            raise Exception("Invalid location import regex: %s", li.regex);

    return imports


def parse_subject(subject, term_id=None, agent=None):
    if agent is None:
        agent = SPIRE()
        agent.login()

    if term_id is not None: agent.select_term(term_id)
    r = agent.search(subject, expand=True)

    fp = open("/tmp/blah.html", "w")
    fp.write(r)
    fp.close()

    r = open("/tmp/blah.html", "r")

    p = PullParser(r)
        
    if not p.seek(StartTag('table', eq={'id': '$ICField97$scroll$0'})):
        r.close()
        #raise Exception("Couldnt find ICField97!")
        raise StopIteration
        
    course_index = 0
        
    for course_name in p.tags(StartTag('span', eq={'class': 'SSSHYPERLINKBOLD'})):
        m = RE_COURSE.match(p.get_text())
        if m is None: continue
        c = m.groups() + (course_index * 10, [])
            
        course_index += 1;
                
        for sid in p.tags(StartTag('a', startswith={'id': 'DERIVED_CLSRCH_SSR_CLASSNAME_LONG$'}), until=StartTag('a', startswith={'id': 'DERIVED_CLSRCH_SSR_EXPAND_COLLAP2$'})):
            m = RE_SID.match(p.get_text())
            if m is None: continue
                
            group, type, school_id = m.groups()
            stat = p.seek(Tag('img', startswith={'class': 'SSSIMAGECENTER'}))
            m = RE_STATUS.match(stat['src'])
            if m is None: continue
            status = m.group(1)
                
            section = (type, school_id, set(), [])
            col = 0
            for box in p.tags(StartTag('span', eq={'class': 'PSLONGEDITBOX'}), until=EndTag('table')):
                strr = p.get_text(endat=(3,'span'))
                if col == 0:
                    mt = parse_dt(strr)
                    col += 1
                elif col == 1:
                    loc = strr
                    col += 1
                elif col == 2:
                    for name in strr.replace("\r", "").split(', \n'):
                        section[-2].add(name)
                    section[-1].append((mt, loc))
                    col = 0
            c[-1].append(section)
        yield c
    r.close()
    raise StopIteration

def import_subject(subject, term_id=None, agent=None):
    if agent is None:
        agent = SPIRE()
        agent.login()

    m = Major.objects.get(name=subject)
    t = Term.objects.get(school_id=term_id)

    for c in parse_subject(subject, term_id, agent):
        (major_name, course_number, course_title, course_index, sections) = c
        try:
            course = Course.objects.get(term=t, major=m, number=course_number)
            course.title = course_title
            course.desc_id = course_index
        except Course.DoesNotExist:
            course = Course(term=t, major=m, number=course_number, title=course_title, desc_id=course_index)
        course.save()

        for s in sections:
            (type_str, school_id, instructors, times) = s
            print "%r" % (s,)
            try:
                section = Section.objects.get(course=course, school_id=school_id)
            except Section.DoesNotExist:
                section = Section(course=course, school_id=school_id)

            section.tba = len(times) == 0
            section.type = Section.SECTION_TYPE_DICT.get(type_str, Section.LEC)

            section.save()
            
        course.save()
        print "%r" % course



