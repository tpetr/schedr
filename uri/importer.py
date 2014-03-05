from schedr.util import PeopleSoft9, PeopleSoftParser, parse_shortcut
import re, math
from datetime import time, datetime, date, timedelta
from sets import Set
from schedr.uri.models import Term, Major, Course, LocationImport, Instructor, Location, Section
from schedr import util
import os
from glob import glob
from sgmllib import SGMLParser
from schedr import settings
from schedr.util import RMPParser
import urllib2, cookielib

class_regex = re.compile(r'^.*? (.*?) - (.*)[ ]*.?$')
classclean_regex = re.compile(r'\r?\n')
section_regex = re.compile(r'^(.*?) (.*?) ?\((.*?)\)$')
section2_regex = re.compile(r'^/cs/heproda/cache/PS_CS_STATUS_(.*?)_ICN_1\.gif$')
time_regex = re.compile(r'^(.*?) (\d+):(\d+)([APM]{2}) - (\d+):(\d+)([APM]{2})$')

class eCampus(PeopleSoft9):
    def __init__(self, debug=False):
        PeopleSoft9.__init__(self, "https://ecampus.uri.edu:7016/psc/sa_crse_cat/EMPLOYEE/HRMS/", "https://ecampus.uri.edu:7016/psc/sa_crse_cat/EMPLOYEE/HRMS/c/COMMUNITY_ACCESS.CLASS_SEARCH.GBL", 'https://ecampus.uri.edu:7016/psc/sa_crse_cat/EMPLOYEE/HRMS/c/COMMUNITY_ACCESS.CLASS_SEARCH.GBL?PortalActualURL=https%3a%2f%2fecampus.uri.edu%3a7016%2fpsc%2fsa_crse_cat%2fEMPLOYEE%2fHRMS%2fc%2fCOMMUNITY_ACCESS.CLASS_SEARCH.GBL&PortalContentURL=https%3a%2f%2fecampus.uri.edu%3a7016%2fpsc%2fsa_crse_cat%2fEMPLOYEE%2fHRMS%2fc%2fCOMMUNITY_ACCESS.CLASS_SEARCH.GBL&PortalContentProvider=HRMS&PortalCRefLabel=Class%20Search%2fBrowse%20Catalog&PortalRegistryName=EMPLOYEE&PortalServletURI=https%3a%2f%2fecampus.uri.edu%3a7016%2fpsp%2fsa_crse_cat%2f&PortalURI=https%3a%2f%2fecampus.uri.edu%3a7016%2fpsc%2fsa_crse_cat%2f&PortalHostNode=HRMS&NoCrumbs=yes', icsid=True, debug=debug, login=False)

    def login(self, username="GUEST", password="GUEST"):
        return PeopleSoft9.login(self, username, password)

    def student_page(self):
        return ''

    def select_current_term(self):
        dt = datetime.now()
        term_id = (dt.year - 1800) * 10
        if dt.month > 1 and dt.month < 7:
            term_id = term_id + 1
        else:
            term_id = term_id + 9
        return self.select_term(term_id)

    def select_term(self, term_id):
        return PeopleSoft9.select_term(self, term_id, {'ICAction': 'CLASS_SRCH_WRK2_SSR_PB_SRCH$55$', 'CLASS_SRCH_WRK2_INSTITUTION$45$': 'URIPS', 'CLASS_SRCH_WRK2_STRM$47$': term_id, 'CLASS_SRCH_WRK2_SSR_CLS_SRCH_TYPE$56$': '06', 'CLASS_SRCH_WRK2_SSR_CLS_SRCH_TYPE$56$$rad': '06'})

    def browse_term(self, term_id):
        return PeopleSoft9.select_term(self, term_id, {'ICAction': 'CLASS_SRCH_WRK2_SSR_PB_SRCH$55$', 'CLASS_SRCH_WRK2_INSTITUTION$45$': 'URIPS', 'CLASS_SRCH_WRK2_STRM$47$': term_id, 'CLASS_SRCH_WRK2_SSR_CLS_SRCH_TYPE$56$': '04', 'CLASS_SRCH_WRK2_SSR_CLS_SRCH_TYPE$56$$rad': '04'})

    def view_section(self, id, p={}):
        # unverified
        return PeopleSoft9.view_section(self, id, p)

    def search(self, major, course='', expand=True):
        str = PeopleSoft9.search(self, {'ICAction': 'CLASS_SRCH_WRK2_SSR_PB_CLASS_SRCH', 'CLASS_SRCH_WRK2_SUBJECT': major, 'CLASS_SRCH_WRK2_SSR_EXACT_MATCH1': 'C', 'CLASS_SRCH_WRK2_CATALOG_NBR$47$': course, 'CLASS_SRCH_WRK2_ACAD_CAREER': 'UGRD', 'CLASS_SRCH_WRK2_SSR_OPEN_ONLY$chk': 'N', 'CLASS_SRCH_WRK2_OEE_IND$chk': 'N', 'CLASS_SRCH_WRK2_MEETING_TIME_START': '', 'CLASS_SRCH_WRK2_MEETING_TIME_END': '', 'CLASS_SRCH_WRK2_INCLUDE_CLASS_DAYS': 'I', 'CLASS_SRCH_WRK2_MON$chk': '', 'CLASS_SRCH_WRK2_TUES$chk': '', 'CLASS_SRCH_WRK2_WED$chk': '', 'CLASS_SRCH_WRK2_THURS$chk': '', 'CLASS_SRCH_WRK2_FRI$chk': '', 'CLASS_SRCH_WRK2_SAT$chk': '', 'CLASS_SRCH_WRK2_SUN$chk': '', 'CLASS_SRCH_WRK2_SSR_EXACT_MATCH2': 'E', 'CLASS_SRCH_WRK2_LAST_NAME': '', 'CLASS_SRCH_WRK2_CLASS_NBR': '', 'CLASS_SRCH_WRK2_DESCR': '', 'CLASS_SRCH_WRK2_SSR_COMPONENT': '', 'CLASS_SRCH_WRK2_SESSION_CODE': '', 'CLASS_SRCH_WRK2_INSTRUCTION_MODE': '', 'CLASS_SRCH_WRK2_CAMPUS': '', 'CLASS_SRCH_WRK2_LOCATION': ''})

        if 'Your search will return over 50' in str:
            str = self.request({'ICAction': '#ICSave'})

        return str

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
        course.description = self.current_desc
        course.save()

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
    from glob import glob
    for term in Term.objects.filter(active=True):
        cp = ExtraCourseDataParser(verbose=verbose, term=term)
        for filename in glob("/home/tpetr/cache/schedr/uri/%s/*/*.html" % term.school_id):
            fp = open(filename, "r")
            cp.feed(fp.read())
            fp.close()
        cp.close()

def test():
    e = eCampusParser(term=Term.objects.all()[0], major=Major.objects.get(name='MTH'), verbose=True)
    fp = open('/home/tpetr/cache/schedr/uri/2091-MTH.html', 'r')
    e.feed(fp.read())
    fp.close()
    return e
    
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
    s = eCampus()
    s.login(username, password)
    str = s.student_page()
    s.logout()

    sp = StudentParser()
    sp.feed(str)
    sp.close()

    return [Section.objects.get(school_id=sid) for sid in sp.section_ids]

def create_current_term():
    dt = datetime.now()
    term_id = (dt.year - 1800) * 10
    sem = 0
    semstr = ''
    if dt.month > 1 and dt.month < 7:
        term_id = term_id + 1
        semstr = 'spring'
        sem = Term.SPRING
    else:
        term_id = term_id + 9
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
        self.term_regex = re.compile(r'^(.*?) (\d{4})$')

    def reset(self):
        SGMLParser.reset(self)
        self.terms = {}
        self.inside_terms = False
        self.current_id = None
        self.capture = False
        self.data = ''

    def start_select(self, attrs):
        self.inside_terms = get_attr(attrs, 'id') == 'CLASS_SRCH_WRK2_STRM$47$'

    def end_select(self):
        self.inside_terms = False

    def start_option(self, attrs):
        if self.inside_terms:
            self.current_id = get_attr(attrs, 'value')
            self.capture = True

    def end_option(self):
        if self.capture and self.current_id != '':
            match = self.term_regex.match(self.data.strip())
            if match:
                self.terms[self.current_id] = {'year': int(match.group(2)), 'sem': match.group(1)}
            self.data = ''
            self.capture = False
    
    def handle_data(self, data):
        if self.capture:
            self.data = self.data + data

def terms():
    s = eCampus()
    str = s.login()
    s.logout()
    t = TermParser()
    t.feed(str)
    t.close()
    return t.terms
   
regex_major = re.compile(r'^([A-Z]{3})\s*(.*)$')

class MajorParser(SGMLParser):
    def __init__(self):
        SGMLParser.__init__(self)
        self.majors = {}
        self.data = ''
        self.capture = False
        self.major_list = False

    def start_a(self, attrs):
        if get_attr(attrs, 'name') == 'coursecodes':
            self.major_list = True

    def start_p(self, attrs):
        if self.major_list and get_attr(attrs, 'class') == 'table':
            self.capture = True

    def end_p(self):
        if self.capture:
            m = regex_major.match(self.data.strip())
            if m:
                self.majors[m.group(1)] = m.group(2)
            self.data = ''
            self.capture = False

    def start_bt(self, attrs):
        self.major_list = False

    def handle_data(self, data):
        if self.capture:
            self.data = self.data + data


def majors():
    agent = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookielib.LWPCookieJar()))
    request = urllib2.Request("http://www.uri.edu/catalog/cataloghtml/courses/courses.html")
    m = MajorParser()
    m.feed(agent.open(request).read())
    m.close()
    return m.majors
    
def import_majors():
    for name, title in majors().items():
        Major.objects.import_object(name=name, title=title)

def import_locations():
    from schedr.uri import data
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
    filename = "/home/tpetr/cache/schedr/uri/%s-%s.html" % (term.school_id, major.name)
    fp = open(filename, "w")
    fp.write(data)
    fp.close()


def parse_rmp():
    from schedr.uri import data

    rmp = RMPParser()

    for filename in glob("/home/tpetr/cache/schedr/uri/rmp/*.html"):
        fp = open(filename, "r")
        rmp.feed(fp.read())
        fp.close()

    for name, rating_id, rating in rmp.instructors:
        if rating == '':
            continue
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
        os.makedirs("/home/tpetr/cache/schedr/uri/rmp/")
    except:
        pass
    rmp = util.RateMyProfessors(1513, '/home/tpetr/cache/schedr/uri/rmp/')

    rmp.cache_all()
    
def cache_data(callback=None, threads=6, verbose=False):
    if callback is None:
        callback = cache_callback

    try:
        os.makedirs("/home/tpetr/cache/schedr/uri/")
    except:
        pass

    if verbose:
        print "Caching URI data to /home/tpetr/cache/schedr/uri/"
    start = datetime.now()
    util.cache_threaded(Term, Major, eCampus, callback, threads=threads, verbose=verbose)
    end = datetime.now()
    if verbose:
        print "Time: %s" % (end-start)

regex_cids = re.compile(r'\$ICField65\$scroll\$\d+.*?DERIVED_CLSRCH_SSR_CLASSNAME_LONG\$(\d+)')

def cache_extra_data(verbose=False):
    s = eCampus()
    s.login()
    for t in Term.objects.filter(active=True):
        try:
            os.makedirs("/home/tpetr/cache/schedr/uri/%s/" % t.school_id)
        except:
            pass

        s.select_term(t.school_id)
        print "Term: %s" % t

        for m in Major.objects.all():
            try:
                os.makedirs("/home/tpetr/cache/schedr/uri/%s/%s/" % (t.school_id, m.name))
            except:
                pass

            print "   Major: %s" % m

            ids = regex_cids.findall(s.search(major=m.name, expand=False).replace('\n', '').replace('\r', ''))

            for id in ids:
                fp = open("/home/tpetr/cache/schedr/uri/%s/%s/%s.html" % (t.school_id, m.name, id), "w")
                fp.write(s.view_section(id))
                fp.close()
                print "      Wrote: %s" % id

    s.logout()

class eCampusParser(PeopleSoftParser):
    statuses = {'open': Section.OPEN, 'closed': Section.CLOSED, 'cancelled': Section.CANCELLED, 'waitlist': Section.WAITLIST}
    types = {'LEC': Section.LEC, 'DIS': Section.DIS, 'LAB': Section.LAB, 'IND': Section.IND}

    SECTION_TABLE_CLASS = 'PSLEVEL3GRID'

    def __init__(self, major=None, *args, **kwargs):
        if major is None:
            major = Major.objects.all()[0]
        PeopleSoftParser.__init__(self, major=major, course_model=Course, section_model=Section, instructor_model=Instructor, *args, **kwargs)


def parse_data(verbose=False, unknown_locations=None):
    parse_shortcut(school_name='uri', cache_dir='/home/tpetr/cache', term_model=Term, major_model=Major, section_model=Section, parser=eCampusParser, verbose=verbose, unknown_locations=unknown_locations, imports=generate_location_imports())

def generate_location_imports():
    imports = {}
    for li in LocationImport.objects.all():
        letter = li.regex[1:2].lower()
        if not imports.has_key(letter):
            imports[letter] = []
        imports[letter].append((li, re.compile(li.regex, re.IGNORECASE)))

    return imports
