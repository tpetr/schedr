import urllib, urllib2, cookielib, re

from Queue import Queue
from threading import Thread

from sgmllib import SGMLParser

# PDF output
import colorsys
from reportlab.pdfgen import canvas
from reportlab.lib import pagesizes
from cStringIO import StringIO

from datetime import timedelta, time, datetime

import os,sys
import httplib2

def send_push_notification(event, desc):
    args = {'application': 'Schedr', 'event': event, 'description': desc}
    h = httplib2.Http(timeout=15)
    h.force_exception_to_status_code = True
    h.add_credentials('tpetr', 'amshdkajsdhkasjdhaksjdhaksjdhaksjdhaksjdhaskdjhask')
    rsp, content = h.request('https://prowl.weks.net/api/add_notification.php?' + urllib.urlencode(args))
    return rsp == 200
    

def get_attr(attrs, name):
    for k,v in attrs:
        if k == name:
            return v
    return ''

class Parser(SGMLParser):
    def __init__(self, existing_sections=None, diagnostics=False, verbose=False):
        SGMLParser.__init__(self)
        self.diagnostics = diagnostics
        self.verbose = verbose
        self.data = ''
        self.capture = False
        self.existing_sections = existing_sections
        
    def reset(self):
        SGMLParser.reset(self)
        self.data = ''
        self.capture = False

    def handle_data(self, data):
        if self.capture:
            self.data = self.data + data

class PeopleSoftParser(Parser):
    days = (('Th', 'thu'), ('M', 'mon'), ('T', 'tue'), ('W', 'wed'), ('F', 'fri'))

    regex_time = re.compile(r'^(.*?) (\d+):(\d+)([APM]{2}) - (\d+):(\d+)([APM]{2})$')
    regex_course = re.compile(r'^.*? (.*?) - (.*?)[ \r\n.]*$', re.M)
    regex_section = re.compile(r'^[A-Z0-9]+-(.*?)\((\d+)\)$')
    regex_status = re.compile(r'/PS_CS_STATUS_(.*?)_ICN_1.gif$')

    STATUS_IMAGE_ATTR = 'class'
    STATUS_IMAGE_VALUE = 'SSSIMAGECENTER'
    SECTION_TABLE_CLASS = 'PSLEVEL1SCROLLAREABODY'
    DT_TABLE_ID = 'SSR_CLSRCH_MTG1$scroll$'
    COURSE_SPAN_CLASS = 'SSSHYPERLINKBOLD'
    SECTION_LINK_ID = 'DERIVED_CLSRCH_SSR_CLASSNAME_LONG$'

    def __init__(self, term, major, course_model, section_model, instructor_model, unknown_locations=None, imports={}, *args, **kwargs):
        Parser.__init__(self, *args, **kwargs)
        self.term = term
        self.major = major
        self.course_model = course_model
        self.section_model = section_model
        self.instructor_model = instructor_model
        self.unknown_locations = unknown_locations
        self.imports = imports

        self.doing_gened = False
        self.gened_string = ''

        self.dt_col = 0
        self.inside_course_span = False
        self.inside_section_table = False
        self.inside_dt_table = False
        self.iniside_dt_cell = False
        self.inside_section_link = False
        self.skip_section_links = False
        self.first_section_id = None

        self.section_string = ''

        self.course = None
        self.section = None

        self.course_is_tba = False
        self.course_isnt_tba = False
        self.course_is_closed = False
        self.course_isnt_closed = False

    def reset(self):
        Parser.reset(self)
        self.dt_col = 0
        self.inside_course_span = False
        self.inside_section_table = False
        self.inside_dt_table = False
        self.inside_dt_cell = False
        self.inside_section_link = False
        self.skip_section_links = False
        self.first_section_id = None

        self.course_is_tba = False
        self.course_isnt_tba = False
        self.course_is_closed = False
        self.course_isnt_closed = False

    def parse_time(self, hour, minute, ampm):
        hour = int(hour)
        minute = int(minute)
        if ampm == 'PM' and hour != 12:
            hour = hour + 12
        return time(hour, minute)

    def parse_days(self, str):
        results = []
        for a, b in self.days:
            if a in str:
                str = str.replace(a, '')
                results.append(b)
        return results

    def parse_dt(self, str, loc=None, room=None):
        if str is None or str == '' or str == 'TBA':
            self.course_is_tba = True
            return {}

        self.course_isnt_tba = True

        results = {}
        m = self.regex_time.match(str)
        if not m:
            raise Exception("regex_time not match: %s" % str)
             
        start = self.parse_time(m.group(2), m.group(3), m.group(4))
        end = self.parse_time(m.group(5), m.group(6), m.group(7))
        
        for d in self.parse_days(m.group(1)):
            results['%s_start' % d] = start
            results['%s_end' % d] = end
            results['%s_location' % d] = loc
            results['%s_room' % d] = room

        return results

    def parse_status(self, str):
        if self.regex_status is not None:
            str = self.regex_status.search(str).group(1)
        str = str.lower()
        if not self.statuses.has_key(str) and self.verbose:
            print "Unknown status: '%s'" % str
        
        s = self.statuses.get(str, self.section_model.OPEN)
        if s == self.section_model.OPEN:
            self.course_isnt_closed = True
        else:
            self.course_is_closed = True
        return s

    def parse_location(self, str):
        if str is None or str == 'TBA':
            return (None, None)

        letter = str[0:1].lower()

        try:
            for li, p in self.imports[letter]:
                m = p.match(str)
                if m is None:
                    continue
                if li.location is None:
                    return (None, None)
                else:
                    return (li.location, li.room % m.groupdict())
        except KeyError:
            pass

        if self.unknown_locations is not None:
            self.unknown_locations.append((str, self.course))

        return (None, None)

    def parse_instructors(self, str):
        return [self.instructor_model.objects.import_object(name=ins) for ins in str.replace('\r', '').replace('\n', '').replace('<br>', '').replace(r'</br>', '').split(', ')]

    def parse_type(self, str):
        if not self.types.has_key(str) and self.verbose:
            print "Unknown type: '%s'" % str
        return self.types.get(str, self.section_model.LEC)

    def parse_course(self):
        match = self.regex_course.match(self.course_string)
        if match is None:
            raise Exception("Course span regex faile for: '%s'" % self.course_string)

        number, title = match.groups()

        title = title.replace('\r', '').replace('\n', '')

        gened_data = self.parse_gened(self.gened_string)

        if self.diagnostics:
            print "Course: %s %s - %s" % (self.major.name, number, title)
        else:
            self.course = self.course_model.objects.import_object(term=self.term, major=self.major, number=number, title=title, **gened_data)
            if self.verbose:
                print "Course: %s" % self.course

    def parse_group(self, str, type):
        return (None, None)

    def parse_gened(self, str):
        return {}

    def parse_section(self):
        try:
            type_str, school_id = self.regex_section.match(self.section_string).groups()
        except:
            print "Error with section regex: '%s'" % self.section_string
            return
        status = self.parse_status(self.section_status)
        type = self.parse_type(type_str)
        group, group_literal = self.parse_group(self.section_string, type)

        instructors = set()
        dt_args = {'mon_start': None, 'mon_end': None, 'mon_location': None, 'mon_room': None, 'tue_start': None, 'tue_end': None, 'tue_room': None, 'tue_location': None, 'wed_start': None, 'wed_end': None, 'wed_room': None, 'wed_location': None, 'thu_start': None, 'thu_end': None, 'wed_room': None, 'wed_location': None, 'fri_start': None, 'fri_end': None, 'fri_room': None, 'fri_location': None}

        for span_time, span_loc, span_ins in self.dt_array:
            for name in self.parse_instructors(span_ins):
                instructors.add(name)
            loc, room = self.parse_location(span_loc)
            dt_args.update(self.parse_dt(span_time, loc, room))
        if self.diagnostics:
            print "Section: %s %s %s" % (type, school_id, dt_args)
        else:
            try:
                s = self.section_model.objects.import_object(course=self.course, type=type, school_id=school_id, instructors=instructors, status=status, **dt_args)
            except Exception, e:
                s = self.section_model.objects.get(school_id=school_id)
            if group is not None:
                s.group = group
                s.group_literal = group_literal
                s.save()
            if self.existing_sections is not None:
                try:
                    self.existing_sections.remove(s.school_id)
                except:
                    pass
            if self.verbose:
                print "Section: %s" % s
            if self.course.major.name == 'ENGLWRIT':
                print "%s - %s" % (s, dt_args)

    def start_table(self, attrs):
        if get_attr(attrs, 'class') == self.SECTION_TABLE_CLASS:
            if self.course is not None:
                if not self.course_is_tba and self.course_isnt_tba:
                    self.course.tba = 0
                elif self.course_is_tba and self.course_isnt_tba:
                    self.course.tba = 1
                elif self.course_is_tba and not self.course_isnt_tba:
                    self.course.tba = 2
                if not self.course_is_closed and self.course_isnt_closed:
                    self.course.closed = 0
                elif self.course_is_closed and self.course_isnt_closed:
                    self.course.closed = 1
                elif self.course_is_closed and not self.course_isnt_closed:
                    self.course.closed = 2
                #if self.first_section_id is not None:
                #    self.course.desc_id = self.first_section_id
                self.course.save()
            self.skip_section_links = False
            self.parse_course()
            self.inside_section_table = True
        elif get_attr(attrs, 'id').startswith(self.DT_TABLE_ID):
            self.inside_dt_table = True
            self.dt_array = []
        elif get_attr(attrs, 'id') == 'ACE_width' and get_attr(attrs, 'class') == 'PABACKGROUNDINVISIBLE':
            self.gened_string = None

    def start_span(self, attrs):
        cls = get_attr(attrs, 'class')
        if cls == self.COURSE_SPAN_CLASS:
            self.capture = True
            self.inside_course_span = True
        elif cls == 'PSEDITBOX_DISPONLY' and self.inside_section_table == False:
            self.capture = True
            self.doing_gened = True

    def start_td(self, attrs):
        if self.inside_dt_table:
            self.capture = True
            self.inside_dt_cell = True

    def start_a(self, attrs):
        if self.inside_section_table and get_attr(attrs, 'id').startswith(self.SECTION_LINK_ID):
            if not self.skip_section_links:
                self.first_section_id = get_attr(attrs, 'id').split('$')[1]
                self.skip_section_links = True
            self.capture = True
            self.inside_section_link = True

    def start_img(self, attrs):
        if self.inside_section_table and get_attr(attrs, self.STATUS_IMAGE_ATTR).startswith(self.STATUS_IMAGE_VALUE):
            self.section_status = get_attr(attrs, 'src')

    def end_a(self):
        if self.capture and self.inside_section_link:
            self.section_string = self.data.strip()
            self.inside_section_link = False
            self.data = ''
            self.capture = False

    def end_td(self):
        if self.capture and self.inside_dt_cell:
            if self.dt_col == 0:
                self.dt_string = self.data.strip()
            elif self.dt_col == 1:
                self.loc_string = self.data.strip()
            elif self.dt_col == 2:
                self.ins_string = self.data.strip()
            elif self.dt_col == 3:
                self.dt_array.append((self.dt_string, self.loc_string, self.ins_string))
            self.dt_col = self.dt_col + 1
            self.inside_dt_cell = False
            self.capture = False
            self.data = ''

    def start_tr(self, attrs):
        if self.inside_dt_table:
            self.dt_col = 0
            self.dt_string = None
            self.loc_string = None
            self.ins_string = None

    def end_tr(self):
        if self.inside_dt_table and self.dt_string is not None:
            self.dt_array.append((self.dt_string, self.loc_string, self.ins_string))

    def end_span(self):
        if self.capture:
            if self.doing_gened:
                self.gened_string = self.data.strip()
                self.doing_gened = False
                self.capture = False
                self.data = ''
            elif self.inside_course_span:
                self.course_string = self.data.strip().replace('\n', '')
                self.inside_course_span = False
                self.capture = False
                self.data = ''

    def end_table(self):
        if self.inside_dt_table:
            self.parse_section()
        self.inside_dt_table = False

def parse_shortcut(term_model, major_model, section_model, parser, school_name, cache_dir, verbose=False, unknown_locations=None, imports={}):
    if school_name == '':
        raise Exception("Invalid school name")

    existing = set([s.school_id for s in section_model.objects.filter(course__term__active=True)])
    if verbose:
        print "Starting with %i sections" % len(existing)

    start = datetime.now()
    for term in term_model.objects.filter(active=True):
        p = parser(term=term, unknown_locations=unknown_locations, verbose=verbose, imports=imports, existing_sections=existing)
        for major in major_model.objects.all():
            filename = '%s/schedr/%s/%s-%s.html' % (cache_dir, school_name, term.school_id, major.name)
            if os.path.exists(filename):
                if verbose:
                    print "%s - %s" % (term, major.name)
                p.major = major
                file = open(filename, 'r')
                for line in file:
                    p.feed(line)
                file.close()
                p.close()
                p.reset()

    cancel_count = 0

    for sid in existing:
        s = section_model.objects.get(school_id=sid)
        if s.status != section_model.CANCELLED:
            cancel_count = cancel_count + 1
            s.status = section_model.CANCELLED
            s.save()

    if verbose:
        print "Marked %i sections as Cancelled" % cancel_count

    end = datetime.now()
    if verbose:
        print "Time: %s" % (end-start)
 
class Rect:
    def __init__(self, l, t, r, b):
        self.left = l
        self.top = t
        self.right = r
        self.bottom = b
        self.width = r - l
        self.height = t - b

def calc_font_size(p, str, width, font='Helvetica', size=12):
    while (p.stringWidth(str, font, size) > width):
        size = size - 1
    return size

def generate_exam_pdf(term, title, finals, footer=''):
    buffer = StringIO()

    size = pagesizes.landscape(pagesizes.letter)
    p = canvas.Canvas(buffer, size)
    p.setFont("Helvetica", 12)

    p.setTitle("%s Final Exams" % term)
        

    width, height = size
    xmargin = width/50
    ymargin = height/50

    # Draw term (Spring 2009) on the top left
    p.setFontSize(20)
    p.drawString(xmargin, height-ymargin-15, "%s Final Exams" % term)

    # Draw title on top right
    p.setFontSize(16)
    p.drawRightString(width-xmargin, height-ymargin-15, title)

    p.setFontSize(12)

    # Compute colors for courses
    h_inc = 1.0 / float(len(finals))
    color_map = {}
    i = 0

    # Compute the minimum and maximum hours 
    min_hour, max_hour = 11, 15
    courses = set()
    for f in finals:
        if f.start.hour < min_hour:
            min_hour = f.start.hour

        if f.end.minute == 0 and f.end.hour > max_hour:
            max_hour = f.end.hour
        elif f.end.minute > 0 and f.end.hour >= max_hour:
            max_hour = f.end.hour + 1
        color_map[f] = colorsys.hsv_to_rgb(h_inc * i, 0.25, 1)
        i = i + 1

    cal_rect = Rect(xmargin, height - ymargin - 45, width - xmargin, ymargin + 20)
    cal_rect2 = Rect(xmargin, height - ymargin - 45, width - xmargin - 35, ymargin + 20)

    # Draw weekdays and vertical markers
    days = (term.final_end - term.final_start).days + 1
    offset = 0;
    d = term.final_start
    p.setStrokeColorRGB(.5,.5,.5)
    for offset in xrange(days):
        p.line(cal_rect2.left + ((cal_rect2.width / days) * offset), cal_rect2.top, cal_rect2.left + ((cal_rect2.width / days) * offset), cal_rect2.top - cal_rect2.height)
        p.drawCentredString(cal_rect2.left + (cal_rect2.width / (days * 2)) + ((cal_rect2.width / days) * offset), height - ymargin - 40, d.strftime("%a %m/%d"))
        d = d + timedelta(1)
    p.line(cal_rect2.left + cal_rect2.width, cal_rect2.top, cal_rect2.left + cal_rect2.width, cal_rect2.top - cal_rect2.height)

    # Compute height of one hour on the pdf
    hour_height = cal_rect.height / (max_hour-min_hour)


    # Draw the horizontal hour markers
    for hour in xrange(max_hour-min_hour):
        if hour == 0:
            p.setStrokeColorRGB(0,0,0)
        else:
            p.setStrokeColorRGB(.5,.5,.5)
        p.line(cal_rect.left, cal_rect.top - (hour * hour_height), cal_rect.right, cal_rect.top - (hour * hour_height)) 
        p.setFontSize(18)
        h = hour + min_hour
        if h > 12:
            h = h - 12
        p.drawRightString(cal_rect.right - 15, cal_rect.top - 15 - (hour * hour_height), "%i" % h)
        p.setFontSize(10)
        p.drawRightString(cal_rect.right, cal_rect.top - 15 - (hour * hour_height), "AM" if (hour + min_hour) < 12 else "PM")
    p.line(cal_rect.left, cal_rect.bottom, cal_rect.right, cal_rect.bottom)
    p.setFontSize(12)

    p.setStrokeColorRGB(0,0,0)

    # Draw the sections
    for f in finals:
        index = (f.date - term.final_start).days
        
        mstart = ((f.start.hour - min_hour) * 60) + f.start.minute
        mend = ((f.end.hour - min_hour) * 60) + f.end.minute
        xstart = mstart * hour_height / 60
        xend = mend * hour_height / 60
        p.setFillColorRGB(*color_map[f])
        p.roundRect(cal_rect2.left + (index * (cal_rect2.width/days)) + 1, cal_rect2.top - xend, (cal_rect2.width/days) - 2, xend-xstart, 10, fill=1)
        p.setFillColorRGB(0, 0, 0)
        h = (xend-xstart-12)/3
        p.setFontSize(10)
        p.drawCentredString(cal_rect2.left + (cal_rect2.width/(days*2)) + (index * (cal_rect2.width/days)), cal_rect2.top - xstart - 10, f.start.strftime("%I:%M %p"))
        p.setFont("Helvetica-Bold", calc_font_size(p, "%s" % f.course, (cal_rect2.width/days)-2, 'Helvetica-Bold'))
        p.drawCentredString(cal_rect2.left + (cal_rect2.width/(days*2)) + (index * (cal_rect2.width/days)), cal_rect2.top - xstart - 10 - h, "%s" % f.course)
        if f.location is None:
            loc_str = 'TBA'
        else:
            loc_str = "%s %s" % (f.location.name, f.room)
        p.setFont("Helvetica", calc_font_size(p, loc_str, (cal_rect2.width/days)-2, 'Helvetica'))
        p.drawCentredString(cal_rect2.left + (cal_rect2.width/(days*2)) + (index * (cal_rect2.width/days)), cal_rect2.top - xstart - 10 - (h*2), loc_str)
        p.setFontSize(10)
        p.drawCentredString(cal_rect2.left + (cal_rect2.width/(days*2)) + (index * (cal_rect2.width/days)), cal_rect2.top - xstart - 10 - (h*3), f.end.strftime("%I:%M %p"))
        p.setFontSize(12)

    if footer != '':
        p.drawCentredString(width / 2, ymargin + 2, footer)
    
    p.showPage()
    p.save()
    return buffer



def generate_course_pdf(term, title, sections, footer=''):
    buffer = StringIO()

    size = pagesizes.portrait(pagesizes.letter)
    p = canvas.Canvas(buffer, size)
    p.setFont("Helvetica", 12)

    p.setTitle("%s" % term)
        

    width, height = size
    xmargin = width/50
    ymargin = height/50

    # Draw term (Spring 2009) on the top left
    p.setFontSize(20)
    p.drawString(xmargin, height-ymargin-15, "%s" % term)

    # Draw title on top right
    p.setFontSize(16)
    p.drawRightString(width-xmargin, height-ymargin-15, title)

    p.setFontSize(12)

    # Compute the minimum and maximum hours 
    min_hour, max_hour = 11, 15
    courses = set()
    for section in sections:
        courses.add(section.course)
        for day, start, end in section.day_times():
            if start.hour < min_hour:
                min_hour = start.hour

            if end.minute == 0 and end.hour > max_hour:
                max_hour = end.hour
            elif end.minute > 0 and end.hour >= max_hour:
                max_hour = end.hour + 1

    # Compute colors for courses
    if len(courses) > 0:
        h_inc = 1.0 / float(len(courses))
        color_map = {}
        i = 0
        for course in courses:
            color_map[course] = colorsys.hsv_to_rgb(h_inc * i, 0.25, 1)
            i = i + 1

    cal_rect = Rect(xmargin, height - ymargin - 35, width - xmargin, ymargin + 15)
    cal_rect2 = Rect(xmargin, height - ymargin - 35, width - xmargin - 35, ymargin + 15)

    # Draw weekdays
    for offset, day in ((0, 'Mon'), (1, 'Tue'), (2, 'Wed'), (3, 'Thu'), (4, 'Fri')):
        p.drawCentredString(cal_rect2.left + (cal_rect2.width / 10) + ((cal_rect2.width / 5) * offset), height - ymargin - 33, day)

    # Compute height of one hour on the pdf
    hour_height = cal_rect.height / (max_hour-min_hour)

    # Draw the hour markers
    for hour in xrange(max_hour-min_hour):
        p.line(cal_rect.left, cal_rect.top - (hour * hour_height), cal_rect.right, cal_rect.top - (hour * hour_height)) 
        p.setFontSize(18)
        h = hour + min_hour
        if h > 12:
            h = h - 12
        p.drawRightString(cal_rect.right - 15, cal_rect.top - 15 - (hour * hour_height), "%i" % h)
        p.setFontSize(10)
        p.drawRightString(cal_rect.right, cal_rect.top - 15 - (hour * hour_height), "AM" if (hour + min_hour) < 12 else "PM")
    p.line(cal_rect.left, cal_rect.bottom, cal_rect.right, cal_rect.bottom)
    p.setFontSize(12)

    # Draw the sections
    for section in sections:
        index = 0
        for index, start, end, loc, room in section.day_times_with_locs():
            mstart = ((start.hour - min_hour) * 60) + start.minute
            mend = ((end.hour - min_hour) * 60) + end.minute
            xstart = mstart * hour_height / 60
            xend = mend * hour_height / 60
            p.setFillColorRGB(*color_map[section.course])
            p.roundRect(cal_rect2.left + (index * (cal_rect2.width/5)) + 1, cal_rect2.top - xend, (cal_rect2.width/5) - 2, xend-xstart, 10, fill=1)
            p.setFillColorRGB(0, 0, 0)
            h = (xend-xstart-12)/4
            p.setFontSize(10)
            p.drawCentredString(cal_rect2.left + (cal_rect2.width/10) + (index * (cal_rect2.width/5)), cal_rect2.top - xstart - 10, start.strftime("%I:%M %p"))
            p.setFont("Helvetica-Bold", calc_font_size(p, "%s" % section.course, (cal_rect2.width/5)-2, 'Helvetica-Bold'))
            p.drawCentredString(cal_rect2.left + (cal_rect2.width/10) + (index * (cal_rect2.width/5)), cal_rect2.top - xstart - 10 - h, "%s" % section.course)
            p.setFont("Helvetica-Bold", calc_font_size(p, section.get_type_long(), (cal_rect2.width/5)-2, 'Helvetica-Bold'))
            p.drawCentredString(cal_rect2.left + (cal_rect2.width/10) + (index * (cal_rect2.width/5)), cal_rect2.top - xstart - 10 - (h*2), section.get_type_long())
            if loc is None:
                loc_str = 'TBA'
            else:
                loc_str = "%s %s" % (loc.name, room)
            p.setFont("Helvetica", calc_font_size(p, loc_str, (cal_rect2.width/5)-2, 'Helvetica'))
            p.drawCentredString(cal_rect2.left + (cal_rect2.width/10) + (index * (cal_rect2.width/5)), cal_rect2.top - xstart - 10 - (h*3), loc_str)
            p.setFontSize(10)
            p.drawCentredString(cal_rect2.left + (cal_rect2.width/10) + (index * (cal_rect2.width/5)), cal_rect2.top - xstart - 10 - (h*4), end.strftime("%I:%M %p"))
            p.setFontSize(12)

    if footer != '':
        p.drawCentredString(width / 2, ymargin, footer)
    
    p.showPage()
    p.save()
    return buffer

    

class Importer:
    def __init__(self, verbose=False):
        self.verbose = verbose

    def cache_data():
        raise Exception("Not implemented yet")

    def import_all():
        raise Exception("Not implemented yet")

    def create_current_term():
        raise Exception("Not implemented yet")

    def terms():
        raise Exception("Not implemented yet")

    def majors():
        raise Exception("Not implemented yet")

    def import_majors(self):
        raise Exception("Not implemented yet")

    def import_major(self, Major, name, title=None):
        if self.verbose:
            print "import_major(%s, %s)" % (name, title)

        try:
            m = Major.objects.get(name=name)
        except Major.DoesNotExist:
            m = Major(name=name)

        if title is not None:
            m.title = title

        m.save()

        return m

    def import_course(self, Course, major, term, number, title=None):
        if self.verbose:
            print "import_course(%s, %s, %s, %s)" % (major, term, number, title)

        try:
            c = Course.objects.get(term=term, major=major, number=number)
        except Course.DoesNotExist:
            c = Course(term=term, major=major, number=number)

        if title is not None:
            c.title = title

        c.save()
        return c

    def import_section(self, Section, course, school_id, **kwargs):
        if self.verbose:
            print "import_section(%s, %s, %s)" % (course, school_id, kwargs)

        try:
            s = Section.objects.get(course=course, school_id=school_id)
        except Section.DoesNotExist:
            s = Section(course=course, school_id=school_id)

        if kwargs.has_key('mon_start'):
            l.mon_start = kwargs['mon_start']
        if kwargs.has_key('mon_end'):
            l.mon_end = kwargs['mon_end']
        if kwargs.has_key('mon_location'):
            l.mon_location = kwargs['mon_location']
        if kwargs.has_key('mon_room'):
            l.mon_room = kwargs['mon_room']

        if kwargs.has_key('tue_start'):
            l.tue_start = kwargs['tue_start']
        if kwargs.has_key('tue_end'):
            l.tue_end = kwargs['tue_end']
        if kwargs.has_key('tue_location'):
            l.tue_location = kwargs['tue_location']
        if kwargs.has_key('tue_room'):
            l.tue_room = kwargs['tue_room']

        if kwargs.has_key('wed_start'):
            l.wed_start = kwargs['wed_start']
        if kwargs.has_key('wed_end'):
            l.wed_end = kwargs['wed_end']
        if kwargs.has_key('wed_location'):
            l.wed_location = kwargs['wed_location']
        if kwargs.has_key('wed_room'):
            l.wed_room = kwargs['wed_room']

        if kwargs.has_key('thu_start'):
            l.thu_start = kwargs['thu_start']
        if kwargs.has_key('thu_end'):
            l.thu_end = kwargs['thu_end']
        if kwargs.has_key('thu_location'):
            l.thu_location = kwargs['thu_location']
        if kwargs.has_key('thu_room'):
            l.thu_room = kwargs['thu_room']

        if kwargs.has_key('fri_start'):
            l.fri_start = kwargs['fri_start']
        if kwargs.has_key('fri_end'):
            l.fri_end = kwargs['fri_end']
        if kwargs.has_key('fri_location'):
            l.fri_location = kwargs['fri_location']
        if kwargs.has_key('fri_room'):
            l.fri_room = kwargs['fri_room']

        l.save()
        return l

    def import_location(self, Location, name, title=None):
        if self.verbose:
            print "import_location(%s, %s)" % (name, title)

        try:
            l = Location.objects.get(name=name)
        except Location.DoesNotExist:
            l = Location(name=name)

        if title is not None:
            l.title = title

        l.save()
        return l
        
    def import_instructor(self, Instructor, name, **kwargs):
        if self.verbose:
            print "import_instructor(%s, %s)" % (name, kwargs)

        try:
            i = Instructor.objects.get(name=name)
        except Instructor.DoesNotExist:
            i = Instructor(name=name)

        if kwargs.has_key('rating'):
            i.rating = kwargs['rating']
        if kwargs.has_key('rating_id'):
            i.rating_id = kwargs['rating_id']

        i.save()
        return i

class Memoize:
    def __init__(self, func):
        self.func = func
        self.data = {}

    def __call__(self, *args):
        if not self.data.has_key(args):
            self.data[args] = self.func(*args)
        return self.data[args]

def cache_threaded(Term, Major, Agent, callback, threads=6, verbose=False):
    q = Queue()
    agents = []

    if verbose:
        print "Caching with %i threads..." % threads

    def cache_worker(agent):
        while True:
            (term, major) = q.get()
            agent.select_term(term.school_id)
            callback(term, major, agent.search(major=major.name))
            if verbose:
                print "   Cached %s (%s)" % (major, term)
            q.task_done()

    for i in range(threads):
        a = Agent(debug=True)
        a.login()
        agents.append(a)
        t = Thread(target=cache_worker, args=(a,))
        t.setDaemon(True)
        t.start()

    for term in Term.objects.filter(active=True):
        for major in Major.objects.all():
            q.put((term, major))

    q.join()

    for a in agents:
        a.logout()
            

class Agent:
    def __init__(self):
        self.agent = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookielib.LWPCookieJar()))

rmp_regex = re.compile(r'^(.*), (.*)$')
rmp2_regex = re.compile(r'^ShowRatings\.jsp\?tid=(\d+)$')

class RMPParser(SGMLParser):
    def __init__(self):
        SGMLParser.__init__(self)
        self.capture = False
        self.data = ''
        self.inside_table = False
        self.inside_row = False
        self.col = 0
        self.current_name = ''
        self.current_rating = ''
        self.instructors = []

    def reset(self):
        SGMLParser.reset(self)
        self.capture = False
        self.data = ''
        self.inside_table = False
        self.inside_row = False
        self.col = 0
        self.current_name = ''
        self.current_rating = ''
        self.instructors = []

    def convert_codepoint(self, cp):
        print "codepoint: %s" % cp

    def start_table(self, attrs):
        id = ''
        for key, value in attrs:
            if key == 'id':
                id = value
                break
        if id == 'rmp_table':
            self.inside_table = True

    def end_table(self):
        self.inside_table = False

    def start_tr(self, attrs):
        if not self.inside_table:
            return
        cls = ''
        for key, value in attrs:
            if key == 'class':
                cls = value
                break
        if cls == 'table_headers':
            return
        self.inside_row = True
        self.col = 0

    def end_tr(self):
        self.inside_row = False

    def start_td(self, attrs):
        if self.inside_row and (self.col == 3 or self.col == 6):
            self.capture = True

    def end_td(self):
        if self.capture:
            if self.col == 3:
                self.current_name = self.data
            elif self.col == 6:
                self.current_rating = self.data
                match = rmp_regex.match(self.current_name)
                if match:
                    name = "%s %s" % (match.group(2), match.group(1))
                    self.instructors.append((name, self.current_id, self.current_rating))
                self.current_name = ''
                self.current_rating = ''
                self.current_id = ''
                
            self.data = ''
            self.capture = False
        if self.inside_row:
            self.col = self.col + 1

    def start_a(self, attrs):
        if self.col != 3:
            return
        href = ''
        for key, value in attrs:
            if key == 'href':
                href = value
                break
        match = rmp2_regex.match(href)
        if match:
            self.current_id = match.group(1)

    def handle_data(self, data):
        if self.capture:
            self.data = self.data + data


class RateMyProfessors:
    def __init__(self, school_id, path):
        self.school_id = school_id
        self.agent = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookielib.LWPCookieJar()))

        try:
            os.makedirs(path)
        except:
            pass

        self.path = path
        self.data = {}
        self.rmp_regex = re.compile(r'^<a href="ShowRatings\.jsp\?tid=(\d+)">(.*?)</a>, (.*)$')

    def cache_letter(self, letter):
        request = urllib2.Request("http://www.ratemyprofessors.com/SelectTeacher.jsp?the_dept=All&sid=%i&orderby=TLName&letter=%s" % (self.school_id, letter));
        fp = open("%s/%s.html" % (self.path, letter), "w")
        fp.write(self.agent.open(request).read())
        fp.close()        

    def cache_all(self):
        import string
        for letter in string.ascii_uppercase:
            self.cache_letter(letter)

    def parse(self, filename, callback=None):
        from BeautifulSoup import BeautifulSoup, BeautifulStoneSoup, SoupStrainer
        rmp_table = SoupStrainer('table', {'id': 'rmp_table'})
        fp = open(filename, "r")
        html = BeautifulSoup(fp, parseOnlyThese=rmp_table)
        fp.close()

        table = html.find(name="table", id="rmp_table")
        for row in table.findAll(name="tr"):
            if row.get('class', '') == 'table_headers':
                continue
            cols = row.findAll(name='td')
            match = self.rmp_regex.match(cols[3].renderContents())
            if match is None:
                continue
            ins_id = int(match.group(1))
            ins_name = "%s %s" % (match.group(3), match.group(2))
            ins_rating = None
            if (int(cols[5].renderContents()) > 0):
                ins_rating = cols[6].renderContents()

            if callback is not None:
                callback(ins_name, ins_id, ins_rating)
    
    

class PeopleSoft(Agent):
    OFFLINE = 0
    TERM_SELECT = 1
    SEARCH_QUERY = 2
    SEARCH_RESULTS = 3
    BROWSE_LETTER = 4
    BROWSE_RESULTS = 5
    BROWSE_COURSE = 6

    REQUEST_PARAMS = {'ICType': 'Panel', 'ICElementNum': 0, 'ICChanged': -1, 'ICResubmit': 0}
    LOGOUT_PARAMS = {'cmd': 'logout'}
    statenum = 0
    
    def __init__(self, get_url, post_url, start_url=None, icsid=False, debug=False):
	Agent.__init__(self)
        self.get_url = get_url
        self.post_url = post_url
        self.start_url = start_url
        self.statenum = 0
        self.status = self.OFFLINE
        if icsid:
            self.icsid_regex = re.compile(r"name='ICSID' value='(.*?)'", re.IGNORECASE)
            self.use_icsid = True
        else:
            self.use_icsid = False
        self.debug = debug

    def __get_icsid(self, str):
        m = self.icsid_regex.search(str)
        try:
            if m.group(1) != None:
                self.icsid = m.group(1)
        except Exception:
            pass

    def login(self):
        str = None
        if self.start_url != None:
            str = self.get(url=self.start_url)
        self.status = self.TERM_SELECT
        return str
    
    def state(self):
        self.statenum = self.statenum + 1
        return {'ICStateNum': self.statenum}
    
    def close_search(self, params={}):
        p = self.CLOSE_SEARCH_PARAMS.copy()
        p.update(params)
        str = self.request(p)
        self.status = self.TERM_SELECT
        return str

    def new_search(self, params={}):
        p = self.NEW_SEARCH_PARAMS.copy()
        p.update(params)
        str = self.request(p)
        self.status = self.SEARCH_QUERY
        return str
    
    def get(self, params={}, url=None):
        if url == None:
            url = self.get_url
       
        if self.debug:
            print "GET  %s?%s" % (url, urllib.urlencode(params)) 

        request = urllib2.Request(url + '?' + urllib.urlencode(params))
        request.add_header('User-Agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US) AppleWebKit/533.4 (KHTML, like Gecko) Chrome/5.0.375.125 Safari/533.4')
        str = self.agent.open(request).read()
        if self.use_icsid:
            self.__get_icsid(str)
        return str
    
    def post(self, params={}, url=None):
        if url == None:
            url = self.post_url
        
        if self.debug:
            print "POST %s?%s" % (url, urllib.urlencode(params))

        request = urllib2.Request(url, urllib.urlencode(params))
        request.add_header('User-Agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US) AppleWebKit/533.4 (KHTML, like Gecko) Chrome/5.0.375.125 Safari/533.4')
        str = self.agent.open(request).read()
        if self.use_icsid:
            self.__get_icsid(str)
        return str
    
    def request(self, params, url=None):
        p = self.REQUEST_PARAMS.copy()
        p.update(self.state())
        if self.use_icsid:
            p['ICSID'] = self.icsid
        p.update(params)
        return self.post(p, url);

    def browse_term(self, term_id, params):
        if self.status == self.OFFLINE: 
            return None

        str = self.request(params)
        self.current_term_id = term_id
        self.status = self.BROWSE_LETTER
        return str

    def browse_letter(self, letter, params):
        self.current_letter = letter
        str = self.request(params)
        self.status = self.BROWSE_RESULTS
        return str

    def browse_course(self, id, params):
        str = self.request(params)
        self.status = self.BROWSE_COURSE
	self.request({'ICAction': 'CLASS_SRCH_WRK2_SSR_PB_BACK$36$'})
        return str

    def view_section(self, id, params):
        str = self.request(params)
        self.request({'ICAction': 'CLASS_SRCH_WRK2_SSR_PB_BACK'})
        return str
    
    def select_term(self, term_id, params):
        if self.status == self.OFFLINE:
            return None
        
        if (self.status == self.SEARCH_QUERY) or (self.status == self.SEARCH_RESULTS):
            self.close_search()

        str = self.request(params)
        
        self.current_term_id = term_id
        self.status = self.SEARCH_QUERY
        
        return str
        
    
    def search(self, params):
        if self.status == self.OFFLINE:
            return None
        
        if self.status == self.TERM_SELECT:
            return None
        
        if self.status == self.SEARCH_RESULTS:
            self.new_search()

        str = self.request(params)
        self.status = self.SEARCH_RESULTS
        
        return str
    
    
    def logout(self, params={}):
        if self.status == self.OFFLINE:
            return
        
        p = self.LOGOUT_PARAMS.copy()
        p.update(params)

        str = self.get(p)
        self.status = self.OFFLINE
        return str

class PeopleSoft9(PeopleSoft):
    PRE_LOGIN_PARAMS = {'cmd': 'login'}
    LOGIN_PARAMS = {'timezoneOffset': 0}
    CLOSE_SEARCH_PARAMS = {'ICAction': 'CLASS_SRCH_WRK2_SSR_PB_CLOSE'}
    NEW_SEARCH_PARAMS = {'ICAction': 'CLASS_SRCH_WRK2_SSR_PB_NEW_SEARCH'}
    SEARCH_PARAMS = {'ICAction': 'CLASS_SRCH_WRK2_SSR_PB_CLASS_SRCH$77$'}
    SELECT_TERM_PARAMS = {'ICAction': 'CLASS_SRCH_WRK2_SSR_PB_SRCH$52$'}

    def __init__(self, get_url, post_url, start_url=None, icsid=False, login=True, debug=False):
        PeopleSoft.__init__(self, get_url, post_url, start_url, icsid, debug=debug)
        self.do_login = login

    def login(self, username, password):
        if self.status != self.OFFLINE:
            return

        if self.do_login:
            self.get(self.PRE_LOGIN_PARAMS)

            p = self.LOGIN_PARAMS.copy()
            p.update({'userid': username, 'pwd': password})
            str = self.post(p)

        r2 = PeopleSoft.login(self)
        if (r2 != None):
            str = r2

        return str

    def select_term(self, term_id, params):
        p = self.SELECT_TERM_PARAMS.copy()
        p.update(params)
        return PeopleSoft.select_term(self, term_id, p)

    def browse_term(self, term_id, params):
        p = self.SELECT_TERM_PARAMS.copy()
        p.update(params)
        return PeopleSoft.browse_term(self, term_id, p)

    def browse_letter(self, letter, params={}):
        p = {'ICAction': 'SSR_CLSRCH_WRK2_SSR_ALPHANUM_%s' % letter.upper(), 'DERIVED_CRSECAT_SSR_CRSECAT_DISP$rad': 20, 'DERIVED_CRSECAT_SSR_CRSECAT_DISP': 20}
        p.update(params)
        return PeopleSoft.browse_letter(self, letter, p)

    def browse_course(self, id, params={}):
        p = {'ICAction': 'DERIVED_CLSRCH_COURSE_TITLE_LONG$%s' % id, 'DERIVED_CRSECAT_SSR_CRSECAT_DISP$rad': 20, 'DERIVED_CRSECAT_SSR_CRSECAT_DISP': 20}
        p.update(params)
        return PeopleSoft.browse_course(self, id, p)

    def view_section(self, id, params={}):
        p = {'ICAction': 'DERIVED_CLSRCH_SSR_CLASSNAME_LONG$%s' % id}
        p.update(params)
        return PeopleSoft.view_section(self, id, p)

    def search(self, params):
        p = self.SEARCH_PARAMS.copy()
        p.update(params)
        return PeopleSoft.search(self, p)

class PeopleSoft8(PeopleSoft):
    PRE_LOGIN_PARAMS = {'cmd': 'start'}
    SELECT_TERM_PARAMS = {'ICAction': 'CLASS_SRCH_BASIC'}
    SEARCH_PARAMS = {'ICAction': 'CLASS_SRCH_WRK2_CLASS_SRCH_PB'}
    CLOSE_SEARCH_PARAMS = {'ICAction': 'CLASS_SRCH_WRK2_CLOSE_PB'}
    NEW_SEARCH_PARAMS = {'ICAction': 'CLASS_SRCH_WRK2_CLASS_BASIC_LINK'}

    def __init__(self, get_url, post_url, start_url=None):
        PeopleSoft.__init__(self, get_url, post_url, start_url)
        self.large_search_regex = re.compile(r'Your search will return')

    def login(self):
        if (self.status != self.OFFLINE):
            return
        
        str = self.get(self.PRE_LOGIN_PARAMS)

        r2 = PeopleSoft.login(self)
        if r2 != None:
            str = r2

        return str

    def select_term(self, term_id, **kwargs):
        p = self.SELECT_TERM_PARAMS.copy()
        p.update(kwargs)
        return PeopleSoft.select_term(self, term_id, **p)

    def search(self, **kwargs):
        p = self.SEARCH_PARAMS.copy()
        p.update(kwargs)
        str = PeopleSoft.search(self, **p)

        if self.large_search_regex.match(str) != None:
            str = self.__large_search()

        return str

    def __large_search(self):
        return self.request({'ICAction': '#ICOK'})
    

class UMassAdmin(PeopleSoft):
    INSTITUTIONS = ('UMBOS', 'UMDAR', 'UMLOW')
    def __init__(self):
        PeopleSoft.__init__(self, 'https://www-sa.umassadmin.net/servlets/iclientservlet/guest/', 'https://www-sa.umassadmin.net/servlets/iclientservlet/guest/?ICType=Panel&Menu=GUEST_ACCESS_UM&Market=GBL&PanelGroupName=CLASS_SEARCH')

    def institution(self):
        raise Exception("Must implement institution()")

    def login(self):
        #return PeopleSoft.login(self)
        self.get({'ICType': 'Panel', 'Menu': 'GUEST_ACCESS_UM', 'Market': 'GBL', 'PanelGroupName': 'GUEST_ACCESS_UM'})
        return self.request({'ICAction': '$ICField6'}, url='https://www-sa.umassadmin.net/servlets/iclientservlet/guest/?ICType=Panel&Menu=GUEST_ACCESS_UM&Market=GBL&PanelGroupName=GUEST_ACCESS_UM')

    def select_term(self, term_id):
        # Fall 2009 = 1910
        self.term_id = term_id
        return self.request({'ICAction': 'CLASS_SRCH_ADV', 'CLASS_SRCH_WRK2_INSTITUTION': self.institution(), 'CLASS_SRCH_WRK2_STRM': self.term_id})

    def search(self, major, course=''):
        return self.request({'ICAction': 'CLASS_SRCH_WRK2_CLASS_SRCH_PB', 'CLASS_SRCH_WRK2_SUBJECT': major, 'CLASS_SRCH_WRK2_CATALOG_NBR': course, 'CLASS_SRCH_WRK2_EXACT_MATCH1': 'E', 'CLASS_SRCH_WRK2_OEE_IND$chk': 'N', 'CLASS_SRCH_INCLUDE_CLASS_DAYS': 'J', 'CLASS_SRCH_WRK2_MON$chk': 'Y', 'CLASS_SRCH_WRK2_MON': 'Y', 'CLASS_SRCH_WRK2_TUE$chk': 'Y', 'CLASS_SRCH_WRK2_TUE': 'Y', 'CLASS_SRCH_WRK2_WED$chk': 'Y', 'CLASS_SRCH_WRK2_WED': 'Y', 'CLASS_SRCH_WRK2_THU$chk': 'Y', 'CLASS_SRCH_WRK2_THU': 'Y', 'CLASS_SRCH_WRK2_FRI$chk': 'Y', 'CLASS_SRCH_WRK2_FRI': 'Y'});

