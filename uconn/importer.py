from schedr.util import PeopleSoft9, PeopleSoftParser, parse_shortcut
import re, math
from datetime import time, datetime, date, timedelta
from sets import Set
from schedr.uconn.models import Term, Major, Course, LocationImport, Instructor, Location, Section
from schedr import util
import os
from glob import glob
from sgmllib import SGMLParser
from schedr import settings
from schedr.util import RMPParser
import urllib2, cookielib

def get_attr(attrs, name):
    for k,v in attrs:
        if k == name:
            return v
    return ''

class StudentAdmin(PeopleSoft9):
    regex_expand = re.compile(r"<a name='\$ICField104\$hviewall\$(\d+)'")
    def __init__(self, debug=False):
        PeopleSoft9.__init__(self, "https://student.studentadmin.uconn.edu/psp/CSGUE/EMPLOYEE/HRMS/", 'https://student.studentadmin.uconn.edu/psc/CSGUE/EMPLOYEE/HRMS/c/COMMUNITY_ACCESS.CLASS_SEARCH.GBL', 'https://student.studentadmin.uconn.edu/psc/CSGUE/EMPLOYEE/HRMS/c/COMMUNITY_ACCESS.CLASS_SEARCH.GBL?PORTALPARAM_PTCNAV=HC_CLASS_SEARCH_GBL&EOPP.SCNode=HRMS&EOPP.SCPortal=EMPLOYEE&EOPP.SCName=CO_EMPLOYEE_SELF_SERVICE&EOPP.SCLabel=Self%20Service&EOPP.SCPTfname=CO_EMPLOYEE_SELF_SERVICE&FolderPath=PORTAL_ROOT_OBJECT.CO_EMPLOYEE_SELF_SERVICE.HC_CLASS_SEARCH_GBL&IsFolder=false&PortalActualURL=https%3a%2f%2fstudent.studentadmin.uconn.edu%2fpsc%2fCSGUE%2fEMPLOYEE%2fHRMS%2fc%2fCOMMUNITY_ACCESS.CLASS_SEARCH.GBL&PortalContentURL=https%3a%2f%2fstudent.studentadmin.uconn.edu%2fpsc%2fCSGUE%2fEMPLOYEE%2fHRMS%2fc%2fCOMMUNITY_ACCESS.CLASS_SEARCH.GBL&PortalContentProvider=HRMS&PortalCRefLabel=Class%20Search&PortalRegistryName=EMPLOYEE&PortalServletURI=https%3a%2f%2fstudent.studentadmin.uconn.edu%2fpsp%2fCSGUE%2f&PortalURI=https%3a%2f%2fstudent.studentadmin.uconn.edu%2fpsc%2fCSGUE%2f&PortalHostNode=HRMS&NoCrumbs=yes', icsid=True, debug=debug, login=False)

    def login(self, username="GUEST", password="GUEST"):
        return PeopleSoft9.login(self, username, password)

    def student_page(self):
        return ''

    def select_current_term(self):
        dt = datetime.now()
        term_id = (dt.year - 1900) * 10
        if dt.month > 1 and dt.month < 7:
            term_id = term_id + 3
        else:
            term_id = term_id + 5
        return self.select_term(term_id)

    def select_term(self, term_id):
        self.term_id = term_id
        self.status = self.SEARCH_QUERY

    def search(self, major, course='', expand=True):
        str = PeopleSoft9.search(self, {'ICAction': 'CLASS_SRCH_WRK2_SSR_PB_CLASS_SRCH', 'CLASS_SRCH_WRK2_INSTITUTION$47$': 'UCONN', 'CLASS_SRCH_WRK2_STRM$50$': self.term_id, 'CLASS_SRCH_WRK2_SUBJECT$63$': major, 'CLASS_SRCH_WRK2_CATALOG_NBR$71$': '', 'CLASS_SRCH_WRK2_SSR_EXACT_MATCH1': 'E', 'CLASS_SRCH_WRK2_CAMPUS': 'STORR', 'CLASS_SRCH_WRK2_ACAD_CAREER': '', 'CLASS_SRCH_WRK2_SSR_OPEN_ONLY$chk': 'N', 'CLASS_SRCH_WRK2_OEE_IND$75$$chk': 'N', 'CLASS_SRCH_WRK2_MEETING_TIME_START': '', 'CLASS_SRCH_WRK2_MEETING_TIME_END': '', 'CLASS_SRCH_WRK2_INCLUDE_CLASS_DAYS': 'I', 'CLASS_SRCH_WRK2_MON$chk': '', 'CLASS_SRCH_WRK2_TUES$chk': '', 'CLASS_SRCH_WRK2_WED$chk': '', 'CLASS_SRCH_WRK2_THURS$chk': '', 'CLASS_SRCH_WRK2_FRI$chk': '', 'CLASS_SRCH_WRK2_SAT$chk': '', 'CLASS_SRCH_WRK2_SUN$chk': '', 'CLASS_SRCH_WRK2_SSR_EXACT_MATCH2': 'E', 'CLASS_SRCH_WRK2_LAST_NAME': '', 'CLASS_SRCH_WRK2_CLASS_NBR$110$': '', 'CLASS_SRCH_WRK2_DESCR': '', 'CLASS_SRCH_WRK2_UNITS_MINIMUM': '', 'CLASS_SRCH_WRK2_UNITS_MAXIMUM': '', 'CLASS_SRCH_WRK2_SSR_COMPONENT': '', 'CLASS_SRCH_WRK2_SESSION_CODE$122$': '', 'CLASS_SRCH_WRK2_INSTRUCTION_MODE': '', 'CLASS_SRCH_WRK2_LOCATION': ''})

        if 'Your search will return over 50' in str:
            str = self.request({'ICAction': '#ICSave'})

        if self.expand:
            for id in self.regex_expand.findall(str):
                str = self.expand(id)

        return str

    def expand(self, id):
        return self.request({'ICAction': '$ICField104$hviewall$' + id})

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
        term_id = term_id + 5
        semstr = 'fall'
        sem = Term.FALL

    t = Term(name='%s%i' % (semstr, dt.year), year=dt.year, semester=sem, school_id=term_id)
    t.save()
    return t

class TermParser(SGMLParser):
    def __init__(self):
        SGMLParser.__init__(self)
        self.capture = False
        self.data = ''
        self.inside_select = False
        self.terms = {}

    def start_select(self, attrs):
        self.inside_select = get_attr(attrs, 'id') == 'CLASS_SRCH_WRK2_STRM$50$'

    def end_select(self):
        self.inside_select = False

    def start_option(self, attrs):
        if self.inside_select:
            self.capture = True

    def end_option(self):
        if self.capture:
            self.data = self.data.strip()
            if self.data != '':
                print "data: '%s'" % self.data
                term_id, temp, sem, year = self.data.split(' ')
                self.terms[term_id] = {'year': int(year), 'sem': sem}
            self.data = ''
            self.capture = False

    def handle_data(self, data):
        if self.capture:
            self.data = self.data + data

def terms():
    sa = StudentAdmin()
    str = sa.login()
    sa.logout()
    t = TermParser()
    t.feed(str)
    t.close()
    return t.terms

class MajorParser(SGMLParser):
    def __init__(self):
        SGMLParser.__init__(self)
        self.capture = False
        self.data = ''
        self.inside_select = False
        self.majors = {}

    def start_select(self, attrs):
        self.inside_select = get_attr(attrs, 'id') == 'CLASS_SRCH_WRK2_SUBJECT$63$'

    def end_select(self):
        self.inside_select = False

    def start_option(self, attrs):
        if self.inside_select:
            self.capture = True

    def end_option(self):
        if self.capture:
            self.data = self.data.strip()
            if self.data != '':
                name, title = self.data.split(' - ', 1)
                self.majors[name] = title
            self.data = ''
            self.capture = False

    def handle_data(self, data):
        if self.capture:
            self.data = self.data + data

def majors():
    sa = StudentAdmin()
    str = sa.login()
    sa.logout()
    m = MajorParser()
    m.feed(str)
    m.close()
    return m.majors

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
    filename = "/home/tpetr/cache/schedr/uconn/%s-%s.html" % (term.school_id, major.name)
    fp = open(filename, "w")
    fp.write(data)
    fp.close()


def parse_rmp():
    from schedr.uconn import data

    rmp = RMPParser()

    for filename in glob("/home/tpetr/cache/schedr/uconn/rmp/*.html"):
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
        os.makedirs("/home/tpetr/cache/schedr/uconn/rmp/")
    except:
        pass
    rmp = util.RateMyProfessors(1513, '/home/tpetr/cache/schedr/uconn/rmp/')

    rmp.cache_all()
    
def cache_data(callback=None, threads=6, verbose=False):
    if callback is None:
        callback = cache_callback

    try:
        os.makedirs("/home/tpetr/cache/schedr/uconn/")
    except:
        pass

    if verbose:
        print "Caching URI data to /home/tpetr/cache/schedr/uconn/"
    start = datetime.now()
    util.cache_threaded(Term, Major, StudentAdmin, callback, threads=threads, verbose=verbose)
    end = datetime.now()
    if verbose:
        print "Time: %s" % (end-start)

regex_cids = re.compile(r'\$ICField65\$scroll\$\d+.*?DERIVED_CLSRCH_SSR_CLASSNAME_LONG\$(\d+)')

def cache_extra_data(verbose=False):
    s = eCampus()
    s.login()
    for t in Term.objects.filter(active=True):
        try:
            os.makedirs("/home/tpetr/cache/schedr/uconn/%s/" % t.school_id)
        except:
            pass

        s.select_term(t.school_id)
        print "Term: %s" % t

        for m in Major.objects.all():
            try:
                os.makedirs("/home/tpetr/cache/schedr/uconn/%s/%s/" % (t.school_id, m.name))
            except:
                pass

            print "   Major: %s" % m

            ids = regex_cids.findall(s.search(major=m.name, expand=False).replace('\n', '').replace('\r', ''))

            for id in ids:
                fp = open("/home/tpetr/cache/schedr/uconn/%s/%s/%s.html" % (t.school_id, m.name, id), "w")
                fp.write(s.view_section(id))
                fp.close()
                print "      Wrote: %s" % id

    s.logout()

class StudentAdminParser(PeopleSoftParser):
    SECTION_TABLE_CLASS = 'PSLEVEL1SCROLLAREABODY'

    def __init__(self, major=None, *args, **kwargs):
        if major is None:
            major = Major.objects.all()[0]
        PeopleSoftParser.__init__(self, major=major, course_model=Course, section_model=Section, instructor_model=Instructor, *args, **kwargs)

def parse_data(verbose=False, unknown_locations=None):
    parse_shortcut(school_name='uconn', cache_dir='/home/tpetr/cache', term_model=Term, major_model=Major, parser=StudentAdminParser, verbose=verbose, unknown_locations=unknown_locations, imports=generate_location_imports())

def generate_location_imports():
    imports = {}
    for li in LocationImport.objects.all():
        letter = li.regex[1:2].lower()
        if not imports.has_key(letter):
            imports[letter] = []
        imports[letter].append((li, re.compile(li.regex, re.IGNORECASE)))

    return imports
