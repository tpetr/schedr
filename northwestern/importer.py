from schedr.util import PeopleSoft9, PeopleSoftParser, parse_shortcut
import re, math
from datetime import time, datetime
from sets import Set
from schedr.northwestern.models import Term, Major, Course, LocationImport, Instructor, Location, Section
from schedr import util
import os
from glob import glob
from sgmllib import SGMLParser

from schedr import settings

import urllib

class_regex = re.compile(r'^.*? (.*?) - (.*)[ ]*.?$')
classclean_regex = re.compile(r'\r?\n')
section_regex = re.compile(r'^(.*?) (.*?) ?\((.*?)\)$')
section2_regex = re.compile(r'^/cs/s9prod/cache/PS_CS_STATUS_(.*?)_ICN_1\.gif$')
time_regex = re.compile(r'^(.*?) (\d+):(\d+)([APM]{2}) - (\d+):(\d+)([APM]{2})$')
student_regex = re.compile(r'^(\d{4})\d(\d{3})$')
student2_regex = re.compile(r'\((\d+)\)', re.MULTILINE)

class CAESAR(PeopleSoft9):
    def __init__(self):
        PeopleSoft9.__init__(self, "https://ses.ent.northwestern.edu/psp/s9prod/", "https://ses.ent.northwestern.edu/psc/s9prod/EMPLOYEE/HRMS/c/SA_LEARNER_SERVICES.CLASS_SEARCH.GBL", "https://ses.ent.northwestern.edu/psc/s9prod/EMPLOYEE/HRMS/c/SA_LEARNER_SERVICES.CLASS_SEARCH.GBL?pslnkid=NW_SS_SA_CLASS_SEARCH&FolderPath=PORTAL_ROOT_OBJECT.NW_SS_SA_CLASS_SEARCH&IsFolder=false&IgnoreParamTempl=FolderPath%2cIsFolder&PortalActualURL=https%3a%2f%2fses.ent.northwestern.edu%2fpsc%2fs9prod%2fEMPLOYEE%2fHRMS%2fc%2fSA_LEARNER_SERVICES.CLASS_SEARCH.GBL%3fpslnkid%3dNW_SS_SA_CLASS_SEARCH&PortalContentURL=https%3a%2f%2fses.ent.northwestern.edu%2fpsc%2fs9prod%2fEMPLOYEE%2fHRMS%2fc%2fSA_LEARNER_SERVICES.CLASS_SEARCH.GBL%3fpslnkid%3dNW_SS_SA_CLASS_SEARCH&PortalContentProvider=HRMS&PortalCRefLabel=Search%20for%20Classes&PortalRegistryName=EMPLOYEE&PortalServletURI=https%3a%2f%2fses.ent.northwestern.edu%2fpsp%2fs9prod%2f&PortalURI=https%3a%2f%2fses.ent.northwestern.edu%2fpsc%2fs9prod%2f&PortalHostNode=HRMS&NoCrumbs=yes", icsid=True)

    def login(self, username='WEBGUEST', password='WEBGUEST1'):
        return PeopleSoft9.login(self, username, password)

    def student_page(self):
        return self.get(url='https://ses.ent.northwestern.edu/psc/caesar/EMPLOYEE/HRMS/c/SA_LEARNER_SERVICES.SSS_STUDENT_CENTER.GBL?pslnkid=NW_SS_STUDENT_CENTER&FolderPath=PORTAL_ROOT_OBJECT.NW_SS_STUDENT_CENTER&IsFolder=false&IgnoreParamTempl=FolderPath,IsFolder&PortalActualURL=https://ses.ent.northwestern.edu/psc/caesar/EMPLOYEE/HRMS/c/SA_LEARNER_SERVICES.SSS_STUDENT_CENTER.GBL?pslnkid=NW_SS_STUDENT_CENTER&PortalContentURL=https://ses.ent.northwestern.edu/psc/caesar/EMPLOYEE/HRMS/c/SA_LEARNER_SERVICES.SSS_STUDENT_CENTER.GBL?pslnkid=NW_SS_STUDENT_CENTER&PortalContentProvider=HRMS&PortalCRefLabel=Student Center&PortalRegistryName=EMPLOYEE&PortalServletURI=https://ses.ent.northwestern.edu/psp/caesar/&PortalURI=https://ses.ent.northwestern.edu/psc/caesar/&PortalHostNode=HRMS&NoCrumbs=yes')

    def select_term(self, term_id):
        self.term_id = term_id
        self.status = self.SEARCH_QUERY

    def search(self, major, course=''):
        return PeopleSoft9.search(self, {'ICAction': 'CLASS_SRCH_WRK2_SSR_PB_CLASS_SRCH', 'CLASS_SRCH_WRK2_INSTITUTION$46$': 'NWUNV', 'CLASS_SRCH_WRK2_STRM$49$': self.term_id, 'CLASS_SRCH_WRK2_SUBJECT$62$': major, 'CLASS_SRCH_WRK2_CATALOG_NBR$70$': course, 'CLASS_SRCH_WRK2_SSR_EXACT_MATCH1': 'E', 'CLASS_SRCH_WRK2_ACAD_CAREER': '', 'CLASS_SRCH_WRK2_SSR_OPEN_ONLY$chk': 'N', 'NW_DERIVED_SS2_CRSE_ATTR': '', 'NW_DERIVED_SS2_CRSE_ATTR_VALUE': '', 'CLASS_SRCH_WRK2_MEETING_TIME_START': '', 'CLASS_SRCH_WRK2_MEETING_TIME_END': '', 'CLASS_SRCH_WRK2_INCLUDE_CLASS_DAYS': 'J', 'CLASS_SRCH_WRK2_MON%$chk': 'Y', 'CLASS_SRCH_WRK2_MON': 'Y', 'CLASS_SRCH_WRK2_TUES$chk': 'Y', 'CLASS_SRCH_WRK2_TUES': 'Y', 'CLASS_SRCH_WRK2_WED$chk': 'Y', 'CLASS_SRCH_WRK2_WED': 'Y', 'CLASS_SRCH_WRK2_THURS$chk': 'Y', 'CLASS_SRCH_WRK2_THURS': 'Y', 'CLASS_SRCH_WRK2_FRI$chk': 'Y', 'CLASS_SRCH_WRK2_FRI': 'Y', 'CLASS_SRCH_WRK2_SAT$chk': 'Y', 'CLASS_SRCH_WRK2_SAT': 'Y', 'CLASS_SRCH_WRK2_SUN$chk': 'Y', 'CLASS_SRCH_WRK2_SUN': 'Y', 'CLASS_SRCH_WRK2_SSR_EXACT_MATCH2': 'E', 'CLASS_SRCH_WRK2_LAST_NAME': '', 'CLASS_SRCH_WRK2_CLASS_NBR$111$': '', 'CLASS_SRCH_WRK2_DESCR': '', 'CLASS_SRCH_WRK2_SSR_COMPONENT': '', 'CLASS_SRCH_WRK2_SESSION_CODE$123$': '', 'CLASS_SRCH_WRK2_CAMPUS': '', 'CLASS_SRCH_WRK2_LOCATION': ''})

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
    c = CAESAR()
    c.login(username, password)
    str = c.student_page()
    c.logout()

    sp = StudentParser()
    sp.feed(str)
    sp.close()

    return [Section.objects.get(school_id=sid) for sid in sp.section_ids]

class DescSchoolParser(SGMLParser):
    def __init__(self):
        SGMLParser.__init__(self)
        self.regex = re.compile(r'/cdesc/course-list\.cgi\?.*?school_id=(\d+)')
        self.schools = []

    def reset(self):
        SGMLParser.reset(self)
        self.schools = []

    def start_a(self, attrs):
        m = self.regex.match(get_attr(attrs, 'href'))
        if m:
            self.schools.append(m.group(1))

class DescDeptParser(SGMLParser):
    def __init__(self):
        SGMLParser.__init__(self)
        self.regex = re.compile(r'/cdesc/course-list\.cgi\?.*?dept_id=(\d+)')
        self.depts = []

    def reset(self):
        SGMLParser.reset(self)
        self.depts = []

    def start_a(self, attrs):
        m = self.regex.match(get_attr(attrs, 'href'))
        if m:
            self.depts.append(m.group(1))
        
class DescClassParser(SGMLParser):
    def __init__(self):
        SGMLParser.__init__(self)
        self.regex = re.compile(r'course-desc\.cgi\?.*?course_id=(\d+)')
        self.classes = []

    def reset(self):
        SGMLParser.reset(self)
        self.classes = []

    def start_a(self, attrs):
        m = self.regex.match(get_attr(attrs, 'href'))
        if m:
            self.classes.append(m.group(1))

def test_desc():
    m = Major.objects.all()[0]
    t = Term.objects.get(name='fall2009')
    dsp = DescSchoolParser()
    ddp = DescDeptParser()
    dcp = DescClassParser()
    dp = DescParser()
    r = urllib.urlopen('http://aquavite.northwestern.edu/cdesc/course-list.cgi?quarter=F09&pagetype=s')
    dsp.feed(r.read())
    dsp.close()
    for school_id in dsp.schools:
        print "school_id = %s" % school_id
        ddp.reset()
        rd = urllib.urlopen('http://aquavite.northwestern.edu/cdesc/course-list.cgi?school_id=%s&quarter=F09&pagetype=d' % school_id)
        ddp.feed(rd.read())
        ddp.close()
        for dept_id in ddp.depts:
            print "   dept_id = %s" % dept_id
            dcp.reset()
            rc = urllib.urlopen('http://aquavite.northwestern.edu/cdesc/course-list.cgi?dept_id=%s&school_id=%s&quarter=F09&pagetype=c' % (dept_id, school_id))
            dcp.feed(rc.read())
            dcp.close()
            for class_id in dcp.classes:
                print "      class_id = %s" % class_id
                dp.reset()
                r2 = urllib.urlopen('http://aquavite.northwestern.edu/cdesc/course-desc.cgi?course_id=%s&dept_id=%s&school_id=%s&quarter=F09' % (class_id, dept_id, school_id))
                dp.feed(r2.read())
                dp.close()
                if m.name != dp.major_name:
                    try:
                        m = Major.objects.get(name=dp.major_name)
                    except Major.DoesNotExist:
                        print "Unknown major: '%s'" % dp.major_name
                        continue
                try:
                    c = Course.objects.get(major=m, term=t, number=dp.course_number)
                except Course.DoesNotExist:
                    print "Unknown course: %s %s" % (dp.major_name, dp.course_number)
                c.description = dp.description
                c.save()
                print "%s - %s" % (c, dp.description)

desc_regex = re.compile(r'^Course Description for .*?\n([^ ]+) .*? ([^ ]+):', re.MULTILINE)

class DescParser(SGMLParser):
    def __init__(self):
        SGMLParser.__init__(self)
        self.data = ''
        self.capture = False
        self.inside_desc = False
        self.inside_title = False
        self.major_name = ''
        self.course_number = ''
        self.description = ''

    def reset(self):
        SGMLParser.reset(self)
        self.data = ''
        self.capture = False
        self.inside_desc = False
        self.inside_title = False
        self.major_name = ''
        self.course_number = ''
        self.description = ''

    def start_h3(self, attrs):
        self.capture = True
        self.inside_title = True

    def end_h3(self):
        if self.capture and self.inside_title:
            m = desc_regex.match(self.data.strip())
            if m: 
                self.major_name, self.course_number = m.groups()
            self.data = ''
            self.capture = False

    def start_b(self, attrs):
        self.capture = True

    def end_b(self):
        if self.capture:
            if self.data.strip() == 'COURSE DESCRIPTION:':
                self.inside_desc = True
            else:
                self.capture = False
            self.data = ''

    def start_br(self, attrs):
        if self.capture:
            self.data = self.data + "\n"

    def start_p(self, attrs):
        if self.inside_desc:
            self.description = self.data.strip()
            self.data = '' 
            self.capture = False
            self.inside_desc = False

    def handle_data(self, data):
        if self.capture:
            self.data = self.data + data

class CalendarParser(SGMLParser):
    def __init__(self, target_term):
        SGMLParser.__init__(self)
        self.data = ''
        self.capture = False




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
        id = ''
        for key, value in attrs:
            if key == 'id':
                id = value
                break

        if id == 'CLASS_SRCH_WRK2_STRM$49$':
            self.inside_terms = True

    def end_select(self):
        self.inside_terms = False

    def start_option(self, attrs):
        value = ''
        for key, val in attrs:
            if key == 'value':
                value = val
                break

        if self.inside_terms:
            self.current_id = value
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
    s = CAESAR()
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
        self.major_regex = re.compile(r'^.*? - (.*)$')
        self.capture = False
        self.data = ''
        self.unknown_locations = []

    def reset(self):
        SGMLParser.reset(self)
        self.majors = {}
        self.inside_majors = False
        self.current_name = None
        self.capture = False
        self.data = ''

    def start_select(self, attrs):
        id = ''
        for key, value in attrs:
            if key == 'id':
                id = value
                break

        if id == 'CLASS_SRCH_WRK2_SUBJECT$62$':
            self.inside_majors = True

    def end_select(self):
        self.inside_majors = False

    def start_option(self, attrs):
        value = ''
        for key, val in attrs:
            if key == 'value':
                value = val
                break

        if self.inside_majors:
            self.current_name = value
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
    s = CAESAR()
    str = s.login()
    s.logout()
    m = MajorParser()
    m.feed(str)
    m.close()
    return m.majors
    
def import_majors():
    for name, title in majors().items():
        Major.objects.import_object(name=name, title=title)

def import_locations():
    from schedr.northwestern import data
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
    filename = "/home/tpetr/cache/schedr/northwestern/%s-%s.html" % (term.school_id, major.name)
    fp = open(filename, "w")
    fp.write(data)
    fp.close()


def import_rmp():
    from schedr.northwestern import data

    def rmp_callback(name, id, rating):
        if data.INSTRUCTOR_NICKNAMES.has_key(name):
            name = data.INSTRUCTOR_NICKNAMES[name]

        try:
            ins = Instructor.objects.get(name=name)
        except Instructor.DoesNotExist:
            return

        ins.rating_id = id
        ins.rating = rating
        ins.save()

    rmp = util.RateMyProfessors(1513, '/home/tpetr/cache/schedr/northwestern/rmp/')
    for filename in glob("/home/tpetr/cache/schedr/northwestern/rmp/*.html"):
        rmp.parse(filename, rmp_callback)

def cache_rmp(verbose=False):
    try:
        os.makedirs("/home/tpetr/cache/schedr/northwestern/rmp/")
    except:
        pass
    rmp = util.RateMyProfessors(1513, '/home/tpetr/cache/schedr/northwestern/rmp/')

    rmp.cache_all()
    
def cache_data(callback=None, threads=6, verbose=False):
    if callback is None:
        callback = cache_callback

    try:
        os.makedirs("/home/tpetr/cache/schedr/northwestern/")
    except:
        pass

    if verbose:
        print "Caching Northwestern data to /home/tpetr/cache/schedr/northwestern/"
    start = datetime.now()
#    util.cache_threaded(Term, Major, CAESAR, callback, threads=threads, verbose=verbose)
    c = CAESAR()
    c.login()
    for term in Term.objects.filter(active=True):
        c.select_term(term.school_id)
        for major in Major.objects.all():
            if verbose:
                print major.name
            fp = open("/home/tpetr/cache/schedr/northwestern/%s-%s.html" % (term.school_id, major.name), "w")
            fp.write(c.search(major.name))
            fp.close()
    c.logout() 
    end = datetime.now()
    if verbose:
        print "Time: %s" % (end-start)

def get_attrs(attrs, *args):
    results = []
    for arg in args:
        for k, v in attrs:
            if k == arg:
                results.append(v)
                break;
        results.append('')
    return tuple(results)

def get_attr(attrs, name):
    for k,v in attrs:
        if k == name:
            return v
    return ''

regex_cids = re.compile(r'\$ICField104\$scroll\$\d+.*?DERIVED_CLSRCH_SSR_CLASSNAME_LONG\$(\d+)')

class ExtraParser(SGMLParser):
    def __init__(self, *args, **kwargs):
        SGMLParser.__init__(self, *args, **kwargs)
        self.inside_table = False
        self.found_link = False
        self.ids = []

    def reset(self):
        SGMLParser.reset(self)
        self.inside_table = False
        self.found_link = False
        self.ids = []

    def start_table(self, attrs):
        if get_attr(attrs, 'id').startswith('$ICField104$scroll$'):
            self.inside_table = True
            self.found_link = False

    def start_a(self, attrs):
        if self.inside_table and not self.found_link and get_attr(attrs, 'id').startswith('DERIVED_CLSRCH_SSR_CLASSNAME_LONG$'):
            self.ids.append(get_attr(attrs, 'id').split('$')[1])
            self.found_link = True


def cache_extra_data(verbose=False):
    c = CAESAR()
    c.login()
    ep = ExtraParser()
    for t in Term.objects.filter(active=True):
        try:
            os.makedirs("/home/tpetr/cache/schedr/northwestern/%s/" % t.school_id)
        except:
            pass

        c.select_term(t.school_id)
        print "Term: %s" % t

        for m in Major.objects.all():
            try:
                os.makedirs("/home/tpetr/cache/schedr/northwestern/%s/%s/" % (t.school_id, m.name))
            except:
                pass
            print "   Major: %s" % m
            ep.feed(c.search(major=m.name))

            for id in ep.ids:
                fp = open("/home/tpetr/cache/schedr/northwestern/%s/%s/%s.html" % (t.school_id, m.name, id), "w")
                fp.write(c.view_section(id))
                fp.close()
                print "      Wrote: %s" % id
            ep.reset()
    c.logout()

class CAESARParser(PeopleSoftParser):
    statuses = {'open': Section.OPEN, 'closed': Section.CLOSED, 'cancelled': Section.CANCELLED, 'waitlist': Section.WAITLIST}
    types = {'LEC': Section.LEC, 'DIS': Section.DIS, 'LAB': Section.LAB}
    regex_section = re.compile(r'^[0-9A-Z]+-(.*?)\((\d+)\)$')

    SECTION_TABLE_CLASS = 'PSLEVEL1SCROLLAREABODY'

    def __init__(self, major=None, *args, **kwargs):
        if major is None:
            major = Major.objects.all()[0]
        PeopleSoftParser.__init__(self, major=major, course_model=Course, section_model=Section, instructor_model=Instructor, *args, **kwargs)

def test_parse():
    from schedr.parse import PullParser, StartTag, EndTag
    fp = open("/home/tpetr/cache/schedr/northwestern/4370-CHEM_ENG.html", "r")
    major = Major.objects.get(name='CHEM_ENG')
    t = Term.objects.get(name='winter2010')
    p = PullParser(fp)

    re_course = re.compile(r'^.*? (.*?) - (.*?)$')
    re_section = re.compile(r'^[0-9A-Z]+-(.*?)\((\d+)\)$')
    section_types = {'LEC': Section.LEC, 'DIS': Section.DIS, 'LAB': Section.LAB}

    if not p.seek(StartTag('table', startswith={'id': '$ICField96$scroll$'})):
        print "no classes"
        fp.close()
        return

    for span in p.tags(StartTag('span', {'class': 'SSSHYPERLINKBOLD'})):
        m = re_course.match(p.get_text())
        if not m: raise Exception("course regex failed!")
        course_number, course_title = m.groups()
        
        c = Course.objects.import_object(term=t, major=major, number=course_number, title=course_title)
        c.save()
        print c

        for link in p.tags(StartTag('a', startswith={'id': 'DERIVED_CLSRCH_SSR_CLASSNAME_LONG$'}), until=StartTag('table', {'class': 'PABACKGROUNDINVISIBLEWBO'})):
            m2 = re_section.match(p.get_text())
            if not m2: raise Exception("section regex failed")
            section_type, section_school_id = m2.groups()
            img = p.seek(StartTag('img', {'class': 'SSSIMAGECENTER'}))
            section_status = img['alt'].lower()
            table2 = p.seek(StartTag('table', startswith={'id': 'SSR_CLSRCH_MTG1$scroll$'}))
            p.seek(StartTag('tr'))
            dt_args = {}
            for tr in p.tags(StartTag('tr'), until=EndTag('table')):
                p.seek(StartTag('span'))
                dt_str = p.get_text()
                dt_days, dt_start, blah, dt_end = dt_str.split(' ')
                start = datetime.strptime(dt_start, "%I:%M%p").time()
                end = datetime.strptime(dt_end, "%I:%M%p").time()
                if 'Mo' in dt_str: dt_args['mon_start'] = start; dt_args['mon_end'] = end;
                if 'Tu' in dt_str: dt_args['tue_start'] = start; dt_args['tue_end'] = end;
                if 'We' in dt_str: dt_args['wed_start'] = start; dt_args['wed_end'] = end;
                if 'Th' in dt_str: dt_args['thu_start'] = start; dt_args['thu_end'] = end;
                if 'Fr' in dt_str: dt_args['fri_start'] = start; dt_args['fri_end'] = end;
                p.seek(StartTag('span'))
                loc_str = p.get_text()
                p.seek(StartTag('span'))
                ins_str = p.get_text()
                print "   loc=%s, ins=%s" % (loc_str, ins_str)
            print "dt_args = %s" % dt_args
            print "type: %s, id: %s, status=%s" % (section_type, section_school_id, section_status)
            try:
                type = section_types[section_type]
            except:
                print "Unknown type: %s" % section_type
                type = section_types['LEC']

            status = Section.OPEN

            s = Section.objects.import_object(course=c, type=type, school_id=section_school_id, section_status=status, **dt_args)
            print s
    fp.close()


def parse_data(verbose=False, unknown_locations=None):
    parse_shortcut(school_name='northwestern', cache_dir='/home/tpetr/cache', term_model=Term, major_model=Major, section_model=Section, parser=CAESARParser, verbose=verbose, unknown_locations=unknown_locations, imports=generate_location_imports())

def generate_location_imports():
    imports = {}
    for li in LocationImport.objects.all():
        letter = li.regex[1:2].lower()
        if not imports.has_key(letter):
            imports[letter] = []
        imports[letter].append((li, re.compile(li.regex, re.IGNORECASE)))

    return imports
