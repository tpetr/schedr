from schedr.util import Memoize
import re, math
from itertools import izip
from datetime import time, timedelta, datetime
from sets import Set
from schedr import util
import os
import urllib2, cookielib
from BeautifulSoup import BeautifulSoup, BeautifulStoneSoup
from schedr.mit.models import Term, Major, Course, Section, Location
from schedr.base.models import School
import string
from sgmllib import SGMLParser

def terms():
    return {}

major_regex = re.compile(r'^([0-9A-Z]{1,3})-(.*)$')
dt1_regex = re.compile(r'^([A-Z]+)([0-9.]+)-([0-9.]+)')
dt2_regex = re.compile(r'^([A-Z]+)([0-9.]+)')
dt3_regex = re.compile(r'^([A-Z]+) EVE \(([0-9.]+)-([0-9.]+) PM\)')

class MajorParser(SGMLParser):
    def __init__(self):
        SGMLParser.__init__(self)
        self.capture = False
        self.data = ''
        self.majors = {}

    def reset(self):
        SGMLParser.reset(self)
        self.capture = False
        self.data = ''
        self.majors = {}

    def start_a(self, attrs):
        href = ''
        for k, v in attrs:
            if k == 'href':
                href = v
                break
        if len(href) > 0 and href[0] == '#':
            self.capture = True

    def end_a(self):
        if self.capture:
            for line in self.data.split('\n'):
                match = major_regex.match(line.strip())
                if match:
                    self.majors[match.group(1)] = match.group(2)
            self.capture = False
            self.data = ''

    def handle_data(self, data):
        if self.capture:
            self.data = self.data + data

def majors():
    agent = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookielib.LWPCookieJar()))
    request = urllib2.Request("http://web.mit.edu/registrar/www/schedules/csbindex.shtml")
    mp = MajorParser()
    mp.feed(agent.open(request).read())
    return mp.majors

hour_regex = re.compile(r'(\d+)\.?(\d+)?')

def create_current_term():
    t = Term(name="spring2009", year=2009, semester=Term.SPRING)
    t.save()
    return t

def get_attr(name, attrs):
    for k,v in attrs:
        if k == name:
            return v
    return ''

section_regex = re.compile(r'^(.*?)\.(.*?)\t(.*?)\t\t(.*?)\t\t(.*)$')

class RegistrarParser(SGMLParser):
    def __init__(self, term, verbose=False):
        SGMLParser.__init__(self)
        self.inside_pre = False
        self.inside_a = False
        self.term = term
        self.verbose = verbose
        self.major = Major.objects.all()[0]

    def start_pre(self, attrs):
        self.inside_pre = True
    def end_pre(self):
        self.inside_pre = False
    def start_a(self, attrs):
        self.inside_a = True
    def end_a(self):
        self.inside_a = False

    def parse_double_dt(self, str):
        match = dt1_regex.match(str)
        if match is None:
            return None
    
        days = match.group(1)
        start = parse_time(match.group(2))
        end = parse_time(match.group(3))
        return (days, start, end)

    def parse_single_dt(self, str):
        match = dt2_regex.match(str)
        if match is None:
            return None
        days = match.group(1)
        start = parse_time(match.group(2))
        end = datetime.now().replace(hour=start.hour, minute=start.minute, second=start.second, microsecond=start.microsecond) + timedelta(hours=1)
        end = end.time()
        return (days, start, end)

    def parse_eve_dt(self, str):
        match = dt3_regex.match(str)
        if match is None:
            return None
        days = match.group(1)
        start = parse_time(match.group(2), True)
        end = parse_time(match.group(3), True)
        return (days, start, end)

    def parse_dt(self, str, loc=None, room=None):
        data = self.parse_double_dt(str)
        if data is None:
            data = self.parse_single_dt(str)
        if data is None:
            data = self.parse_eve_dt(str)
        if data is None:
            return {}
        results = {}
        if 'M' in data[0]:
            results['mon_start'] = data[1]
            results['mon_end'] = data[2]
            results['mon_location'] = loc
            results['mon_room'] = room
        if 'T' in data[0]:
            results['tue_start'] = data[1]
            results['tue_end'] = data[2]
            results['tue_location'] = loc
            results['tue_room'] = room
        if 'W' in data[0]:
            results['wed_start'] = data[1]
            results['wed_end'] = data[2]
            results['wed_location'] = loc
            results['wed_room'] = room
        if 'R' in data[0]:
            results['thu_start'] = data[1]
            results['thu_end'] = data[2]
            results['thu_location'] = loc
            results['thu_room'] = room
        if 'F' in data[0]:
            results['fri_start'] = data[1]
            results['fri_end'] = data[2]
            results['fri_location'] = loc
            results['fri_room'] = room
        return results

    def parse_location(self, data):
        if '-' not in data:
            return None, None
        print "parse_location got: '%s'" % data
        b, r = data.split('-')
        try:
            loc = Location.objects.get(name=b)
        except Location.DoesNotExist:
            return None, None
        return loc, r

    def handle_data(self, data):
        if not self.inside_pre or self.inside_a:
            return
        for line in data.split('\n'):
            line = line.strip()
            match = section_regex.match(line)
            if match:
                major, number, group, location, dt = match.groups()
                if self.major.name != major:
                    try:
                        self.major = Major.objects.get(name=major)
                    except Major.DoesNotExist:
                        print "Unknown major: %s (%s)" % (major, line)
                        continue

                if self.verbose:
                    pass
                    #print "Importing %s.%s" % (self.major, number)
                course = Course.objects.import_object(term=self.term, major=self.major, number=number)
                

                type = group[0]
                if type == 'L':
                    section_type = Section.LEC
                elif type == 'R':
                    section_type = Section.REC
                elif type == 'Q':
                    continue
                elif type == 'P':
                    continue
                elif type == 'B':
                    section_type = Section.LAB
                elif type == '0':
                    continue

                if location == '':
                    loc, room = None, None
                else:
                    loc, room = self.parse_location(location)

                dt_args = self.parse_dt(dt, loc, room)
                section_tba = dt.startswith('*TO BE ARRANGED')

                Section.objects.import_object(course=course, school_id="%s.%s%s" % (major, number, group), type=section_type, **dt_args)
 
                
        

class WebSISParser(SGMLParser):
    PRE = 0
    COURSE_NUMBER = 1
    COURSE_TITLE = 2
    BLAH = 3

    def __init__(self):
        SGMLParser.__init__(self)
        self.capture = False
        self.data = ''
        self.state = WebSISParser.COURSE_NUMBER
        self.current_course_number = ''
        self.current_course_title = ''
        self.inside_p = False
        self.major = Major.objects.all()[0]
        self.course = None
        
    def __reset__(self):
        self.capture = False
        self.data = ''
        self.state = WebSISParser.PRE
        self.inside_p = False
        self.current_course_number = ''
        self.current_course_title = ''

    def start_p(self, attrs):
        self.inside_p = True

    def start_b(self, attrs):
        if not self.inside_p:
            return

        if self.state == WebSISParser.COURSE_NUMBER:
            self.capture = True
        elif self.state == WebSISParser.COURSE_TITLE:
            self.capture = True

    def end_b(self):
        if self.capture:
            if self.state == WebSISParser.COURSE_NUMBER:
                self.current_course_number = self.data
                try:
                    m, n = self.current_course_number.split('.')
                    if self.major.name.lower() != m.lower():
                        try:
                            self.major = Major.objects.get(name=m)
                        except Major.DoesNotExist:
                            self.course = None
                            return
                    try:
                        self.course = Course.objects.get(major=self.major, number=n)
                    except Course.DoesNotExist:
                        self.course = None
                        return 
                    print "got %s, %s" % (m, n)
                except:
                    print "Error: %s" % self.data
                self.state = WebSISParser.COURSE_TITLE
            elif self.state == WebSISParser.COURSE_TITLE:
                if self.course:
                    self.course.title = self.data
                    self.course.save()
                print "got course title %s" % self.current_course_title
                self.state = WebSISParser.BLAH
            self.capture = False
            self.data = ''

    def end_p(self):
        self.inside_p = False
        self.state = WebSISParser.COURSE_NUMBER

    def handle_data(self, data):
        if self.capture:
            self.data = self.data + data

def test2(verbose=False):
    agent = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookielib.LWPCookieJar()))
    request = urllib2.Request("http://web.mit.edu/registrar/www/schedules/csbindex.shtml")
    rp = RegistrarParser(Term.objects.all()[0], verbose=verbose)
    rp.feed(agent.open(request).read())
    return rp

def parse_locations():
    agent = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookielib.LWPCookieJar()))
    request = urllib2.Request("http://whereis.mit.edu/map-jpg?expanded=bldgname")
    rp = LocationParser()
    rp.feed(agent.open(request).read())
    return rp
    
 

def parse_time(str, force_pm=False):
    match = hour_regex.match(str)
    if match is None:
        return None

    h = int(match.group(1))
    if force_pm or (h < 7):
        h = h + 12

    if match.group(2) is None:
        m = 0
    else:
        m = int(match.group(2))

    return time(h, m)
    




    
location_regex = re.compile(r'^(\d+)-(\d+)$')    
def parse_location(str):
    match = location_regex.match(str)
    if match is None:
        return (None, None)
    try:
        loc = Location.objects.get(name=match.group(1))
        print "got: %s" % loc
    except Location.DoesNotExist:
        return (None, None)
    return (loc, match.group(2))

def import_locations():
    agent = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookielib.LWPCookieJar()))
    request = urllib2.Request("http://whereis.mit.edu/map-jpg?expanded=bldgname")
    str = agent.open(request).read()
    html = BeautifulSoup(str)

    list = html.find('select', id='buildingbyname')
    for element in list.findAll('option'):
        title = element.renderContents()
        if title == 'Stata Center Garage':
            continue
        name = element['value']
        import_location(name=name, title=title)

class LocationParser(SGMLParser):
    def __init__(self):
        SGMLParser.__init__(self)
        self.data = ''
        self.capture = ''
        self.inside_select = False

    def start_select(self, attrs):
        self.inside_select = (get_attr('id', attrs) == 'buildingbyname')

    def start_option(self, attrs):
        if self.inside_select:
            self.current_id = get_attr('value', attrs)
            self.capture = True
    def end_option(self):
        if self.capture:
            try:
                loc = Location.objects.get(name=self.current_id)
            except Location.DoesNotExist:
                loc = Location(name=self.current_id)
            loc.title = self.data
            print "imported %s - %s" % (self.current_id, self.data)
            loc.save()
            self.data = ''
            self.capture = False

    def handle_data(self, data):
        if self.capture:
            self.data = self.data + data

def import_location(name, title):
    try:
        l = Location.objects.get(name=name)
    except Location.DoesNotExist:
        l = Location(name=name)
    l.title = title
    l.save()
    return l

def cache_data(verbose=False):
    agent = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookielib.LWPCookieJar()))

    try:
        os.makedirs("/home/tpetr/cache/schedr/mit/")
    except: 
        pass

    for major in Major.objects.all():
        for letter in string.lowercase:
            request = urllib2.Request("http://student.mit.edu/catalog/m%s%s.html" % (major.name, letter))
            try:
                web = agent.open(request)
                file = open("/home/tpetr/cache/schedr/mit/%s%s.html" % (major.name, letter), "w")
                file.write(web.read())
                file.close()
                if verbose:
                    print "wrote %s%s.html" % (major.name, letter)
            except urllib2.HTTPError:
                break

title_regex = re.compile(r'^([0-9A-Z]+\.[0-9A-Z]*?)J?$')
title2_regex = re.compile(r'^([0-9A-Z]+)\.([0-9A-Z]*?)J?[\-?][0-9A-Z]+\.([0-9A-Z]{1,3})J?$')
title3_regex = re.compile(r'^([0-9A-Z]+)\.([0-9A-Z]*?)J?[\-?]([0-9A-Z].*)J?$')


def parse_course_number(str):
    str = str.upper()
    results = []
    for number in str.split(', '):
        match = title2_regex.match(number)
        if match is None:
            match = title3_regex.match(number)
        if match is None:
            match = title_regex.match(number)
            if match is None:
                return []
            results.append(match.group(1))
        else:
            print "got range"
            for n in xrange(int(match.group(2)), int(match.group(3))+1):
                results.append("%s.%s" % (match.group(1), n))
    return results

            
course_title_regex = re.compile(r'^(.*?)(<br />.*)?$')

def import_titles():
    import glob
    wsp = WebSISParser()
    for filename in glob.iglob("/home/tpetr/cache/schedr/mit/*.html"):
        file = open(filename, "r")
        wsp.feed(file.read())
        file.close()

def import_major(name, title=None):
    try:
        major = Major.objects.get(name=name)
    except Major.DoesNotExist:
        major = Major(name=name)

    if title is not None:
        major.title = title
    
    major.save()
    return major

def import_majors():
    data = majors()
    for major in data:
        import_major(name=major, title=data[major])

def import_all():
    term = Term.objects.all()[0]

    import_majors()

    agent = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookielib.LWPCookieJar()))
    request = urllib2.Request("http://web.mit.edu/registrar/www/schedules/csbindex.shtml")
    str = agent.open(request).read()
    html = BeautifulSoup(str)

    titles = import_titles()

    pre = html.find('pre')
    course_regex = re.compile(r'^(.*?)\.(.*?)\t([LR].*?)\t\t(.*?)\t\t(.*)\r$', re.MULTILINE)
    current_major = Major.objects.all()[0]
    for match in course_regex.finditer(pre.renderContents()):
        major_name = match.group(1)
        if (current_major.name != major_name):
            current_major = Major.objects.get(name=major_name)

        course_number = match.group(2)
        course_name = "%s.%s" % (major_name, course_number)
        course = import_course(major=current_major, term=term, number=course_number, title=titles.get(course_name, course_name))

        data = parse_dt(match.group(5))

        loc = parse_location(match.group(4))

        dt = {}
        if data is not None:
            for day in data[0]:
                if day == 'M':
                    key = 'mon'
                elif day == 'T':
                    key = 'tue'
                elif day == 'W':
                    key = 'wed'
                elif day == 'R':
                    key = 'thu'
                elif day == 'F':
                    key = 'fri'
                dt["%s_start" % key] = data[1]
                dt["%s_end" % key] = data[2]
                dt["%s_location" % key] = loc[0]
                dt["%s_room" % key] = loc[1]

        type = Section.LEC
        if match.group(3)[0] == 'R':
            type = Section.DIS
        section = import_section(course=course, type=type, school_id="%s.%s.%s" % (match.group(1), match.group(2), match.group(3)), **dt)
        
        print "major = %s, course = %s, section = %s" % (current_major.title, course, section)
    return {}

def import_course(term, major, number, title):
    try:
        c = Course.objects.get(term=term, major=major, number=number)
    except Course.DoesNotExist:
        c = Course(term=term, major=major, number=number)
    c.title = title
    c.save()
    return c

def import_section(course, type, school_id, **kwargs):
    try:
        s = Section.objects.get(school_id=school_id)
    except Section.DoesNotExist:
        s = Section(course=course, type=type, school_id=school_id)

    tba = True

    if kwargs.get("mon_start", None) is not None:
        s.mon_start = kwargs["mon_start"]
        s.mon_end = kwargs["mon_end"]
        s.mon_location = kwargs["mon_location"]
        s.mon_room = kwargs["mon_room"]
        tba = False

    if kwargs.get("tue_start", None) is not None:
        s.tue_start = kwargs["tue_start"]
        s.tue_end = kwargs["tue_end"]
        s.tue_location = kwargs["tue_location"]
        s.tue_room = kwargs["tue_room"]
        tba = False

    if kwargs.get("wed_start", None) is not None:
        s.wed_start = kwargs["wed_start"]
        s.wed_end = kwargs["wed_end"]
        s.wed_location = kwargs["wed_location"]
        s.wed_room = kwargs["wed_room"]
        tba = False

    if kwargs.get("thu_start", None) is not None:
        s.thu_start = kwargs["thu_start"]
        s.thu_end = kwargs["thu_end"]
        s.thu_location = kwargs["thu_location"]
        s.thu_room = kwargs["thu_room"]
        tba = False

    if kwargs.get("fri_start", None) is not None:
        s.fri_start = kwargs["fri_start"]
        s.fri_end = kwargs["fri_end"]
        s.fri_location = kwargs["fri_location"]
        s.fri_room = kwargs["fri_room"]
        tba = False

    s.tba = tba

    s.save()
    return s
