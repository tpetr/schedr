from schedr.util import Agent
import re, math
from datetime import time, datetime, date, timedelta
from sets import Set
from schedr.amherst.models import Term, Major, Course, Instructor, Location, Section, Final
from schedr import util
import os
from glob import glob
from sgmllib import SGMLParser
from schedr import settings
from schedr.util import RMPParser
import urllib, urllib2, cookielib

viewstate_regex = re.compile(r'<input type="hidden" name="__VIEWSTATE" value="(.*?)" />')

class Registrar(Agent):
    def __init__(self, debug=False):
        Agent.__init__(self)
        self.post_url = 'https://catalog.amherst.edu/amherst/frmCourseSearch.aspx?FormTableName=CourseSearch'
        self.debug = debug

    def get(self, params={}, url=None):
        if url == None:
            url = self.get_url
       
        if self.debug:
            print "GET  %s?%s" % (url, urllib.urlencode(params)) 

        request = urllib2.Request(url + '?' + urllib.urlencode(params))
        str = self.agent.open(request).read()
        return str

    def post(self, params={}, url=None):
        if url == None:
            url = self.post_url
        
        if self.debug:
            print "POST %s?%s" % (url, urllib.urlencode(params))

        request = urllib2.Request(url, urllib.urlencode(params))
        str = self.agent.open(request).read()
        return str
    

    def login(self, username="GUEST", password="GUEST"):
        self.get(url='https://catalog.amherst.edu/amherst/frmstudentsdefaults.aspx', params={'FormTableName': 'CourseSearch'})
        str = self.get(url='https://catalog.amherst.edu/amherst/frmCourseSearch.aspx?FormTableName=CourseSearch')
        m = viewstate_regex.search(str)
        if m:
            self.viewstate = m.group(1)
        return str

    def select_current_term(self):
        print "select_current_term not implemented"
        return ''

    def select_term(self, term_id):
        self.term_id = term_id
        return self.post({'__EVENTTARGET': 'Cmbsemester', '__EVENTARGUMENT': '', '__VIEWSTATE': self.viewstate, 'Cmbsemester': term_id})

    def search(self, major, course=''):
        str = self.post({'__VIEWSTATE': self.viewstate, 'CmbDept': major, 'txtdescription': '', 'txtCourseName' : '', 'txtCoursecode': '', 'txtfacultyname': '', 'FromTime': '', 'ToTime': '', 'ChListDays': '', 'ImgSearch.x': '25', 'ImgSearch.y': '9'})
        m = viewstate_regex.search(str)
        if m:
            self.viewstate = m.group(1)
        return str

def get_attr(attrs, name):
    for k,v in attrs:
        if k == name:
            return v
    return ''

class MajorParser(SGMLParser):
    def __init__(self):
        SGMLParser.__init__(self)
        self.data = ''
        self.capture = False
        self.inside_select = False
        self.majors = {}

    def start_select(self, attrs):
        self.inside_select = get_attr(attrs, 'id') == 'CmbDept'

    def end_select(self):
        self.inside_select = False

    def start_option(self, attrs):
        if not self.inside_select:
            return
        self.current_name = get_attr(attrs, 'value')
        self.capture = self.current_name != ''

    def end_option(self):
        if self.inside_select and self.capture:
            self.majors[self.current_name] = self.data.strip()
            self.data = ''
            self.capture = False

    def handle_data(self, data):
        if self.capture:
            self.data = self.data + data

class TermParser(SGMLParser):
    def __init__(self):
        SGMLParser.__init__(self)
        self.data = ''
        self.capture = False
        self.inside_select = False
        self.current_id = ''
        self.terms = {}

    def start_select(self, attrs):
        self.inside_select = get_attr(attrs, 'id') == 'Cmbsemester'

    def end_select(self):
        self.inside_select = False

    def start_option(self, attrs):
        if self.inside_select:
            self.current_id = get_attr(attrs, 'value')
            self.capture = True

    def end_option(self):
        if self.capture and self.inside_select:
            years, sem = self.data.split('-')
            year = years[0:2]
            self.terms[self.current_id] = {'year': 2000 + int(year), 'sem': sem}
            self.data = ''
            self.capture = False
            

    def handle_data(self, data):
        if self.capture:
            self.data = self.data + data

def majors():
    r = Registrar()
    mp = MajorParser()
    mp.feed(r.login())
    mp.close()
    return mp.majors

def terms():
    r = Registrar()
    r.login()
    str = r.get(url='https://catalog.amherst.edu/amherst/frmStudentTop.aspx')
    tp = TermParser()
    tp.feed(str)
    tp.close()
    return tp.terms

dt_regex = re.compile(r'^\[(.*?)\](.*?) (.*?)-(.*?)$')
time1_regex = re.compile(r'^(\d+)([APM]{2})$')
time2_regex = re.compile(r'^(\d+):(\d+)([APM]{2})$')

class RegistrarParser(SGMLParser):
    def __init__(self, term):
        SGMLParser.__init__(self)
        self.data = ''
        self.capture = False
        self.inside_table = False
        self.row = -1
        self.col = 5
        self.term = term

    def start_table(self, attrs):
        self.inside_table = get_attr(attrs, 'id') == 'DgrdCourse'
        self.row = -1
        self.col = 5

    def end_table(self):
        self.inside_table = False

    def start_td(self, attrs):
        if not self.inside_table:
            return

        self.capture = self.row > 0 and self.col > 1

    def end_td(self):
        if not self.inside_table:
            return
        if self.capture:
            if self.col == 2:
                self.current_section_id = self.data.strip()
            elif self.col == 3:
                self.current_course_title = self.data.strip()
            elif self.col == 4:
                self.current_section_instructors = self.data.strip()
            elif self.col == 5:
                self.current_section_dt = self.data.strip()
            self.data = ''
            self.capture = False
        self.col = self.col + 1
        if self.col > 5:
            if self.row > 0:
                self.current_section_has_tba = False
                self.current_section_has_time = False
                major_name, course_number, group = self.current_section_id.split('-')
                major = Major.objects.get(name=major_name)
                course = Course.objects.import_object(term=self.term, major=major, number=course_number, title=self.current_course_title)
                print "Course: %s" % course
                instructors = []
                if self.current_section_instructors != '':
                    instructors = [Instructor.objects.import_object(name=n.strip()) for n in self.current_section_instructors.split(',')]
                    for ins in instructors:
                        print "   ins: %s" % ins
                if self.current_section_dt != '':
                    for type in self.current_section_dt.split(','):
                        m = dt_regex.match(type.strip())
                        section_school_id = "%s-%s-%s%s" % (major_name, course_number, group, m.group(1))
                        type = self.parse_type(m.group(1))
                        print "type = %s" % type
                        print "group2 = %s" % m.group(2)
                        dt_args = {}
                        if m:
                            dt_args = self.parse_dt(m.group(2), m.group(3), m.group(4))
                            print "dt_args: %s" % dt_args
                        else:
                            self.current_section_has_tba = True
                        s = Section.objects.import_object(course=course, type=type, school_id=section_school_id, instructors=instructors, **dt_args)
                        print "Section: %s" % s
                else:
                    self.current_section_has_tba = True
                if not self.current_section_has_tba and self.current_section_has_time:
                    course.tba = 0
                elif self.current_section_has_tba and self.current_section_has_time:
                    course.tba = 1
                elif self.current_section_has_tba and not self.current_section_has_time:
                    course.tba = 2
                course.save()
                
            self.col = 0
            self.row = self.row + 1

    def parse_type(self, str):
        if str == 'L/D':
            return Section.LD
        elif str == 'LEC':
            return Section.LEC
        elif str == 'DIS':
            return Section.DIS
        else:
            print "Unknown type: %s" % str
        return Section.LEC

    def parse_time(self, str):
        m = time2_regex.match(str)
        if m:
            hour, minute, ampm = m.groups()
        else:
            m = time1_regex.match(str)
            if m:
                hour, ampm = m.groups()
                minute = 0
        hour = int(hour)
        minute = int(minute)
        if (ampm == 'PM') and (hour != 12):
            hour = hour + 12
        return time(hour, minute)

    def parse_dt(self, str_days, str_start, str_end, loc=None, room=None):
        if str_days is None or str_days == '':
            self.current_section_has_tba = True
            return {}

        self.current_section_has_time = True

        results = {}
        start = self.parse_time(str_start)
        end = self.parse_time(str_end)

        days = {'M': ('mon'), 'T': ('tue'), 'W': ('wed'), 'TH': ('thu'), 'F': ('fri'), 'MW': ('mon', 'wed'), 'MWF': ('mon', 'wed', 'fri'), 'TTH': ('tue', 'thu'), 'TH': ('thu'), 'WF': ('wed', 'fri'), 'MTWTHF': ('mon', 'tue', 'wed', 'thu', 'fri'), 'MWTHF': ('mon', 'wed', 'thu', 'fri')}
        if not days.has_key(str_days):
            print "Unknown day: %s" % str_days
            return

        for day in days[str_days]:
            results['%s_start' % day] = start
            results['%s_end' % day] = end
            results['%s_location' % day] = loc
            results['%s_room' % day] = room

        return results

    def handle_data(self, data):
        if self.capture:
            self.data = self.data + data
        
def test():
    r = Registrar()
    r.login()
    rp = RegistrarParser(Term.objects.all()[0])
    for m in Major.objects.all():
        print "Doing %s" % m
        str = r.search(m.name)
        rp.feed(str)
    rp.close()
    return rp
    

def import_majors():
    for name, title in majors().items():
        Major.objects.import_object(name=name, title=title)
