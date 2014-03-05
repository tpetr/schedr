from schedr.util import UMassAdmin, PeopleSoftParser, parse_shortcut
import re, math
from datetime import time, datetime, date, timedelta
from sets import Set
from schedr import util
import os
from glob import glob
from sgmllib import SGMLParser
from schedr import settings
from schedr.util import RMPParser
import urllib2, cookielib

def current_term():
    dt = datetime.now()
    term_id = (dt.year - 1900) * 10
    if dt.month > 1 and dt.month < 7:
        term_id = term_id + 3
    else:
        term_id = term_id + 7
    return term_id

class ISIS(UMassAdmin):
    def institution(self):
        return 'UMLOW'

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
        for major in Major.objects.all():
            cp = ExtraCourseDataParser(verbose=verbose, term=term)
            for course in Course.objects.filter(major=major, term=term).exclude(desc_id=None):
                if not os.path.exists("/home/tpetr/cache/schedr/umass/%s/%s/%s.html" % (term.school_id, major.name, course.desc_id)):
                    continue
                print course
                fp = open("/home/tpetr/cache/schedr/umass/%s/%s/%s.html" % (term.school_id, major.name, course.desc_id), "r")
                cp.feed(fp.read())
                fp.close()
            cp.close()

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
        self.inside_row = False
        self.col = 0
        self.capture = False
        self.data = ''

    def reset(self):
        SGMLParser.reset(self)
        self.majors = {}
        self.inside_row = False
        self.capture = False
        self.col = 0
        self.data = ''

    def start_tr(self, attrs):
        self.inside_row = True
        self.col = 0

    def end_tr(self):
        self.inside_row = False

    def start_a(self, attrs):
        if self.inside_row and get_attr(attrs, 'class').startswith('PSHYPERLINK'):
            self.capture = True;

    def end_a(self):
        if self.capture:
            if self.col == 0:
                self.sa = self.data.strip()
            elif self.col == 1:
                self.majors[self.sa] = self.data.strip()
            self.col = self.col + 1
            self.capture = False
            self.data = ''

    def handle_data(self, data):
        if self.capture:
            self.data = self.data + data

def majors():
    s = ISIS()
    s.login()
    s.select_term('1910')
    s.request({'ICAction': 'CLASS_SRCH_WRK2_SUBJECT$prompt'})
    s.request({'ICAction': '#ICSearch'})
    str = s.request({'ICAction': '#ICViewAll'})
    str = str.replace('<! ', '<!-- ', 1)
    s.logout()
    m = MajorParser()
    m.feed(str)
    m.close()
    return m.majors
    
def import_majors():
    for name, title in majors().items():
        Major.objects.import_object(name=name, title=title)

