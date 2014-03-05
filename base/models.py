from django.db import models
from django.contrib import auth
from django.conf import settings
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.utils.hashcompat import sha_constructor

import datetime
import re

import icalendar
from django.utils import simplejson

# ICS output
import icalendar

import schedr.util

from random import randint

regex_email_suffix = re.compile(r'@(.*)$')

class FeedbackManager(models.Manager):
    def random(self):
        n = self.count()
        return self.all()[randint(0, n-1)]

class Feedback(models.Model):
    text = models.TextField(max_length=140)
    author = models.CharField(max_length=32, blank=True)
    title = models.CharField(max_length=32, blank=True)
    url = models.URLField(blank=True)

    objects = FeedbackManager()

    def __unicode__(self):
        return self.text

class SchoolManager(models.Manager):
    def from_email(self, email):
        suffix = regex_email_suffix.search(email).group(1)
        for school in self.all():
            if suffix.endswith(school.email_suffix):
                return school
        raise School.DoesNotExist()

class School(models.Model):
    name = models.CharField(max_length=128)
    title = models.CharField(max_length=128)
    full_title = models.CharField(max_length=128)
    email_suffix = models.CharField(max_length=256)
    active = models.BooleanField()
    visible = models.BooleanField()
    last_updated = models.DateTimeField(auto_now=True, auto_now_add=True)

    objects = SchoolManager()

    def __unicode__(self):
        return self.title

    def __json__(self):
        return {'name': self.name, 'title': self.title, 'full_title': self.full_title, 'email_suffix': self.email_suffix}

    def get_absolute_url(self):
        return "/%s/" % self.name

    def user_count(self):
        return SchedrUser.objects.filter(school=self, is_active=True).count()

class Term(models.Model):
    name = models.CharField("Name", max_length=128, help_text="Term name for URLs")
    year = models.IntegerField("Year")
    course_start = models.DateField("First day of classes", blank=True, null=True)
    course_end = models.DateField("Last day of classes", blank=True, null=True)
    final_start = models.DateField("First day of finals", blank=True, null=True)
    final_end = models.DateField("Last day of finals", blank=True, null=True)
    active = models.BooleanField("Active", help_text="Importers will update this term")
    visible = models.BooleanField("Visible", help_text="Users can view this term")
    finals_visible = models.BooleanField("Final exams visible", help_text="Users can view final exams for this term")

    def get_absolute_url(self):
        return "/%s/%s/" % (self.school_name, self.name)

    def __unicode__(self):
        return "%s %i" % (self.TERMS[self.semester][1], self.year)

    class Meta:
        permissions = (('see_invisible', 'Can see invisible terms'),)
        abstract = True
        ordering = ['year', 'semester']

class MajorManager(models.Manager):
    def to_json(self):
#        return '{' + ",".join(["%i: \"%s\"" % (major.id, major.title) for major in self.order_by('title')]) + '}'
        return "{%s}" % ",".join(map(lambda x: "%i: \"%s\"" % (x.id, x.title), self.order_by("title")))

    def import_object(self, name, title=None):
        try:
            m = self.get(name=name)
        except:
            m = self.model(name=name)

        if title is not None:
            m.title = title

        m.save()

        return m

class Major(models.Model):
    title = models.CharField("Title", max_length=50, help_text="Long name of major (ex. Engineering)")

    def __unicode__(self):
        return self.name

    def json(self, term, num='', geneds=()):
        genedargs = {}
        for g in geneds:
            genedargs[str("gened_%s" % g)] = True
        return "\"%s\": {%s}" % (self.name, ",".join(map(lambda x: x.json(), self.course_set.filter(number__startswith=num, term=term, **genedargs))))

    objects = MajorManager()

    class Meta:
        ordering = ["name"]
        abstract = True

class CourseManager(models.Manager):
    def import_object(self, term, major, number, title=None, **genedargs):
        try:
            c = self.get(term=term, major=major, number=number)
        except:
            c = self.model(term=term, major=major, number=number)

        if title is not None:
            c.title = title

        for key, value in genedargs.items():
            setattr(c, key, value)

        c.save()
        return c

class Course(models.Model):
    GENED_LIST = None
    term = models.ForeignKey('Term')
    major = models.ForeignKey('Major')
    number = models.CharField(max_length=8)
    title = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    credits = models.IntegerField(blank=True, null=True)

    morning = models.BooleanField(default=False, blank=True)
    afternoon = models.BooleanField(default=False, blank=True)
    evening = models.BooleanField(default=False, blank=True)

    def credits_array(self):
        return [self.credits]

    TBA_NONE = 0
    TBA_SOME = 1
    TBA_ALL = 2
    TBA_CHOICES = ((TBA_NONE, 'None'), (TBA_SOME, 'Some'), (TBA_ALL, 'All'))
    tba = models.IntegerField(default=TBA_NONE, choices=TBA_CHOICES)

    CLOSED_NONE = 0
    CLOSED_SOME = 1
    CLOSED_ALL = 2
    CLOSED_CHOICES = ((CLOSED_NONE, 'None'), (CLOSED_SOME, 'Some'), (CLOSED_ALL, 'All'))
    closed = models.IntegerField(default=CLOSED_NONE, choices=CLOSED_CHOICES)

    def get_absolute_url(self):
        return "/%s/courses/%s/%s/%s" % (self.school_name, self.term.name, self.major.name, self.number)

    def name(self):
        return "%s %s" % (self.major.name, self.number)

    def __unicode__(self):
        return self.name()

    def geneds(self):
        return '';

    def json(self):
        return "[%i,\"%s\",%i,%i,\"%s\",\"%s\"]" % (self.id, self.number, self.tba, self.closed, self.title.replace('"', '\\"'), self.credits)

    objects = CourseManager()

    class Meta:
        ordering = ["major", "number"]
        abstract = True

class MajorTrack(models.Model):
    major = models.ForeignKey('Major', blank=True, null=True)
    name = models.CharField(max_length=16)
    title = models.CharField(max_length=128)

    class Meta:
        abstract = True

class RequiredCourse(models.Model):
    track = models.ForeignKey('MajorTrack')
    semester = models.IntegerField()
    course = models.ForeignKey('Course')

    def __unicode__(self):
        return "%s" % self.course

    class Meta:
        ordering = ['course']
        abstract = True

class FinalManager(models.Manager):
    def import_object(self, course, group_literal, date=None, start=None, end=None, location=None, room=None):
        try:
            f = self.get(course=course, group_literal=group_literal)
        except:
            f = self.model(course=course, group_literal=group_literal)
        if date is not None:
            f.date = date
        if start is not None:
            f.start = start
        if end is not None:
            f.end = end 
        if location is not None:
            f.location = location
        if room is not None:
            f.room = room
        f.save()
        return f

class Final(models.Model):
    course = models.ForeignKey('Course')
    section = models.ForeignKey('Section', blank=True, null=True)
    group_literal = models.CharField(max_length=3)
    date = models.DateField()
    start = models.TimeField()
    end = models.TimeField()
    location = models.ForeignKey('Location', blank=True, null=True)
    room = models.CharField(max_length=32)

    objects = FinalManager()

    def __unicode__(self):
        return "%s (%s) - %s %s" % (self.course, self.group_literal, self.date, self.start)
    
    class Meta:
        ordering = ['course']
        abstract = True

class LocationManager(models.Manager):
    def import_object(self, name, title=None):
        try:
            loc = self.get(name=name)
        except:
            loc = self.model(name=name)

        if title is not None:
            loc.title = title

        loc.save()
        return loc

class Location(models.Model):
    title = models.CharField(max_length=128)
    room_url = models.CharField(max_length=256, blank=True, null=True)

    objects = LocationManager()

    def __unicode__(self):
        return self.title

    class Meta:
        abstract = True
        ordering = ['name']

class LocationImportManager(models.Manager):
    def import_object(self, regex, location, room=None):
        try:
            li = self.get(regex=regex, location=location)
        except:
            li = self.model(regex=regex, location=location)

        li.room = room
        li.save()
        return li
        
class LocationImport(models.Model):
    regex = models.CharField(max_length=255)
    location = models.ForeignKey('Location', blank=True, null=True)
    room = models.CharField(max_length=128, default="%(room)s", blank=True, null=True)

    objects = LocationImportManager()

    def __unicode__(self):
        return self.regex

    class Meta:
        abstract = True

class InstructorManager(models.Manager):
    def import_object(self, name, rating=None, rating_id=None):
        try:
            ins = self.get(name=name)
        except:
            ins = self.model(name=name)

        if rating is not None:
            ins.rating = rating

        if rating_id is not None:
            ins.rating_id = rating_id

        ins.save()
        return ins

class Instructor(models.Model):
    name = models.CharField(max_length=128, unique=True)
    rating = models.FloatField(null=True, blank=True)
    rating_id = models.IntegerField(null=True, blank=True)

    objects = InstructorManager()

    def __unicode__(self):
        return self.name

    class Meta:
        abstract = True
        ordering = ['name']

class SectionManager(models.Manager):
    def import_object(self, course, school_id, type, status=None, instructors=None, **kwargs):
        try:
            s = self.get(course=course, school_id=school_id)
        except:
            s = self.model(course=course, school_id=school_id)

        if school_id in ('36327', '36328', '36329', '36330'):
            return s

        s.type = type

        if status is not None:
            s.status = status

        s.tba = True

        for day in ['mon', 'tue', 'wed', 'thu', 'fri']:
            if not kwargs.has_key("%s_start" % day):
                continue
            setattr(s, "%s_start" % day, kwargs["%s_start" % day])
            setattr(s, "%s_end" % day, kwargs["%s_end" % day])
            setattr(s, "%s_location" % day, kwargs.get("%s_location" % day, None))
            setattr(s, "%s_room" % day, kwargs.get("%s_room" % day, None))
            s.tba = False

        s.save()

        if instructors is not None:
            s.instructors.clear()
            for ins in instructors:
                s.instructors.add(ins)

        s.save()
        return s
            
class Section(models.Model):
    course = models.ForeignKey('Course')

    objects = SectionManager()

    mon_start = models.TimeField("Monday start", blank=True, null=True)
    mon_end = models.TimeField("Monday end", blank=True, null=True)
    mon_location = models.ForeignKey('Location', blank=True, null=True, verbose_name="Monday location", related_name="%(class)s_related_mon")
    mon_room = models.CharField("Monday room", max_length=32, blank=True, null=True)

    tue_start = models.TimeField("Tuesday start", blank=True, null=True)
    tue_end = models.TimeField("Tuesday end", blank=True, null=True)
    tue_location = models.ForeignKey('Location', blank=True, null=True, verbose_name="Tuesday location", related_name="%(class)s_related_tue")
    tue_room = models.CharField("Tuesday room", max_length=32, blank=True, null=True)

    wed_start = models.TimeField("Wednesday start", blank=True, null=True)
    wed_end = models.TimeField("Wednesday end", blank=True, null=True)
    wed_location = models.ForeignKey('Location', blank=True, null=True, verbose_name="Wednesday location", related_name="%(class)s_related_wed")
    wed_room = models.CharField("Wednesday room", max_length=32, blank=True, null=True)

    thu_start = models.TimeField("Thursday start", blank=True, null=True)
    thu_end = models.TimeField("Thursday end", blank=True, null=True)
    thu_location = models.ForeignKey('Location', blank=True, null=True, verbose_name="Thursday location", related_name="%(class)s_related_thu")
    thu_room = models.CharField("Thursday room", max_length=32, blank=True, null=True)

    fri_start = models.TimeField("Friday start", blank=True, null=True)
    fri_end = models.TimeField("Friday end", blank=True, null=True)
    fri_location = models.ForeignKey('Location', blank=True, null=True, verbose_name="Friday location", related_name="%(class)s_related_fri")
    fri_room = models.CharField("Friday room", max_length=32, blank=True, null=True)

    def day_times(self):
        results = []
        if self.mon_start:
            results.append((0, self.mon_start, self.mon_end))
        if self.tue_start:
            results.append((1, self.tue_start, self.tue_end))
        if self.wed_start:
            results.append((2, self.wed_start, self.wed_end))
        if self.thu_start:
            results.append((3, self.thu_start, self.thu_end))
        if self.fri_start:
            results.append((4, self.fri_start, self.fri_end))
        return results

    def day_times_with_locs(self):
        results = []
        if self.mon_start:
            results.append((0, self.mon_start, self.mon_end, self.mon_location, self.mon_room))
        if self.tue_start:
            results.append((1, self.tue_start, self.tue_end, self.tue_location, self.tue_room))
        if self.wed_start:
            results.append((2, self.wed_start, self.wed_end, self.wed_location, self.wed_room))
        if self.thu_start:
            results.append((3, self.thu_start, self.thu_end, self.thu_location, self.thu_room))
        if self.fri_start:
            results.append((4, self.fri_start, self.fri_end, self.fri_location, self.fri_room))
        return results

    def times_dict(self):
        results = {}
        if self.mon_start:
            results['Mon'] = [self.mon_start.strftime('%H:%M:%S'), self.mon_end.strftime('%H:%M:%S')]
        if self.tue_start:
            results['Tue'] = [self.tue_start.strftime('%H:%M:%S'), self.tue_end.strftime('%H:%M:%S')]
        if self.wed_start:
            results['Wed'] = [self.wed_start.strftime('%H:%M:%S'), self.wed_end.strftime('%H:%M:%S')]
        if self.thu_start:
            results['Thu'] = [self.thu_start.strftime('%H:%M:%S'), self.thu_end.strftime('%H:%M:%S')]
        if self.fri_start:
            results['Fri'] = [self.fri_start.strftime('%H:%M:%S'), self.fri_end.strftime('%H:%M:%S')]
        return results

    tba = models.BooleanField("TBA", default=False)
    
    instructors = models.ManyToManyField('Instructor', blank=True, null=True, verbose_name="Instructors")

    OPEN = 0
    CLOSED = 1
    WAITLIST = 2
    CANCELLED = 3
    SECTION_STATUS = ((OPEN, 'Open'), (CLOSED, 'Closed'), (WAITLIST, 'Waitlist'), (CANCELLED, 'Cancelled'))
    status = models.IntegerField(choices=SECTION_STATUS, default=OPEN)

    LEC = 0
    DIS = 1
    LAB = 2
    PCM = 3
    IND = 4
    SEM = 5
    DST = 6
    STU = 7
    REC = 8
    GEN = 9
    LD = 10
    STS = 11
    SECTION_TYPE = ((LEC, 'Lecture'), (DIS, 'Discussion'), (LAB, 'Laboratory'), (PCM, 'Practicum'), (IND, 'Independent Study'), (SEM, 'Seminar'), (DST, 'Dissertation'), (STU, 'Studio'), (REC, 'Recitation'), (GEN, 'General'), (LD, 'L/D'), (STS, 'Studio / Skills'))
    SECTION_TYPE_SHORT = ((LEC, 'LEC'), (DIS, 'DIS'), (LAB, 'LAB'), (PCM, 'PCM'), (IND, 'IND'), (SEM, 'SEM'), (DST, 'DST'), (STU, 'STU'), (REC, 'REC'), (GEN, 'GEN'), (LD, 'L/D'), (STS, 'STS'))
    SECTION_TYPE_DICT = dict([(b, a) for a, b in SECTION_TYPE_SHORT])
    
    type = models.IntegerField(choices=SECTION_TYPE, default=LEC)

    def get_type_short(self):
        return self.SECTION_TYPE_SHORT[self.type][1]

    def get_type_long(self):
        return self.SECTION_TYPE[self.type][1]

    def __unicode__(self):
        return "%s %s (%s)" % (self.course, self.SECTION_TYPE[self.type][1], self.school_id)

    def to_pdf(self, canvas, x, y, w, h):
        canvas.roundRect(x, y, w, h, 5)        

    def to_ics(self):
        results = []
        if self.tba:
            return results

        if self.course.term.course_start is None:
            return results

        course_start = datetime.datetime.combine(self.course.term.course_start, datetime.time())
        course_end = self.course.term.course_end

        index = 0;
        for day in ['mon', 'tue', 'wed', 'thu', 'fri']:
            start_date = course_start + datetime.timedelta((index - course_start.weekday()) % 7)
            index = index + 1
            if getattr(self, "%s_start" % day, None) is None:
                continue
            event = icalendar.Event()
            event.add('summary', "%s %s (%s)" % (self.course.name(), self.get_type_short(), self.school_id))
            event.add('description', "%s (%s)" % (self.course.title, ', '.join([ins.name for ins in self.instructors.all()])))
            event.add('UID', '%s%s@%s.schedr.com' % (self.school_id, day, self.course.school_name))
            event.add('dtstamp', datetime.datetime.now())
            start = getattr(self, "%s_start" % day)
            end = getattr(self, "%s_end" % day)
            location = getattr(self, "%s_location" % day)
            room = getattr(self, "%s_room" % day)
            if location is None:
                event.add('location', 'TBA')
            elif room is None:
                event.add('location', location)
            else:
                event.add('location', "%s %s" % (location, room))
#            start = datetime.time(start.hour, start.minute, start.second, start.microsecond, lt)
#            end = datetime.time(end.hour, end.minute, end.second, end.microsecond, lt)
#            sdt = datetime.datetime(start_date.year, start_date.month, start_date.day, start.hour, start.minute, start.second, start.microsecond)#, eastern)
#            edt = datetime.datetime(start_date.year, start_date.month, start_date.day, end.hour, end.minute, end.second, end.microsecond)#, eastern)
#            edt2 = datetime.datetime(course_end.year, course_end.month, course_end.day, end.hour, end.minute, end.second, end.microsecond)#, eastern)
#            if start.tzinfo is None:
#                sdt += datetime.timedelta(0, 0, 0, 0, 0, 4)
#                edt += datetime.timedelta(0, 0, 0, 0, 0, 4)
#                edt2 += datetime.timedelta(0, 0, 0, 0, 0, 4)
            event.add('dtstart', datetime.datetime.combine(start_date, start))
            event.add('dtend', datetime.datetime.combine(start_date, end))
            event.add('rrule', {'FREQ': ['WEEKLY'], 'UNTIL': [datetime.datetime.combine(course_end, end)]})

            results.append(event)
        return results

    def export(self, results={}, ins={}, loc={}, sel=False):
#        sec = {'school_id': self.school_id, 'sel': sel, 'tba': self.tba, 'ins': [ins.id for ins in self.instructors.all()]}
        sec = {'school_id': self.school_id, 'sel': sel, 'tba': self.tba, 'status': self.status, 'ins': map(lambda x: x.id, self.instructors.all()), 'dts': [], 'group': self.group}

#	ins_ids = [inst.id for inst in self.instructors.all()]
        ins_ids = map(lambda x: x.id, self.instructors.all())
        sec['ins'] = ins_ids

        for id in ins_ids:
            if ins.get(id, None) == None:
		i = self.instructors.get(id=id)
                ins[id] = {'name': i.name, 'rating_id': i.rating_id, 'rating': i.rating}

        if self.mon_start != None:
            sec['Mon'] = {'start': self.mon_start.hour * 60 + self.mon_start.minute, 'end': self.mon_end.hour * 60 + self.mon_end.minute}
            dts = [0, self.mon_start.hour * 60 + self.mon_start.minute, self.mon_end.hour * 60 + self.mon_end.minute]
            if self.mon_location != None:
                dts.append(self.mon_location.id)
                dts.append(self.mon_room)
                sec['Mon']['loc'] = self.mon_location.id
                if loc.get(self.mon_location.id, None) == None:
                    loc[self.mon_location.id] = {'name': self.mon_location.name, 'title': self.mon_location.title}
                sec['Mon']['room'] = self.mon_room
            sec['dts'].append(dts)

        if self.tue_start != None:
            sec['Tue'] = {'start': self.tue_start.hour * 60 + self.tue_start.minute, 'end': self.tue_end.hour * 60 + self.tue_end.minute}
            dts = [1, self.tue_start.hour * 60 + self.tue_start.minute, self.tue_end.hour * 60 + self.tue_end.minute]
            if self.tue_location != None:
                dts.append(self.tue_location.id)
                dts.append(self.tue_room)
                sec['Tue']['loc'] = self.tue_location.id
                if loc.get(self.tue_location.id, None) == None:
                    loc[self.tue_location.id] = {'name': self.tue_location.name, 'title': self.tue_location.title}
                sec['Tue']['room'] = self.tue_room
            sec['dts'].append(dts)

        if self.wed_start != None:
            sec['Wed'] = {'start': self.wed_start.hour * 60 + self.wed_start.minute, 'end': self.wed_end.hour * 60 + self.wed_end.minute}
            dts = [2, self.wed_start.hour * 60 + self.wed_start.minute, self.wed_end.hour * 60 + self.wed_end.minute]
            if self.wed_location != None:
                dts.append(self.wed_location.id)
                dts.append(self.wed_room)
                sec['Wed']['loc'] = self.wed_location.id
                if loc.get(self.wed_location.id, None) == None:
                    loc[self.wed_location.id] = {'name': self.wed_location.name, 'title': self.wed_location.title}
                sec['Wed']['room'] = self.wed_room
            sec['dts'].append(dts)

        if self.thu_start != None:
            sec['Thu'] = {'start': self.thu_start.hour * 60 + self.thu_start.minute, 'end': self.thu_end.hour * 60 + self.thu_end.minute}
            dts = [3, self.thu_start.hour * 60 + self.thu_start.minute, self.thu_end.hour * 60 + self.thu_end.minute]
            if self.thu_location != None:
                dts.append(self.thu_location.id)
                dts.append(self.thu_room)
                sec['Thu']['loc'] = self.thu_location.id
                if loc.get(self.thu_location.id, None) == None:
                    loc[self.thu_location.id] = {'name': self.thu_location.name, 'title': self.thu_location.title}
                sec['Thu']['room'] = self.thu_room
            sec['dts'].append(dts)

        if self.fri_start != None:
            sec['Fri'] = {'start': self.fri_start.hour * 60 + self.fri_start.minute, 'end': self.fri_end.hour * 60 + self.fri_end.minute}
            dts = [4, self.fri_start.hour * 60 + self.fri_start.minute, self.fri_end.hour * 60 + self.fri_end.minute]
            if self.fri_location != None:
                sec['Fri']['loc'] = self.fri_location.id
                dts.append(self.fri_location.id)
                dts.append(self.fri_room)
                if loc.get(self.fri_location.id, None) == None:
                    loc[self.fri_location.id] = {'name': self.fri_location.name, 'title': self.fri_location.title}
                sec['Fri']['room'] = self.fri_room
            sec['dts'].append(dts);

        if results.get(self.group, None) == None:
            results[self.group] = {}

        if results[self.group].get(self.type_short(), None) == None:
            results[self.group][self.type_short()] = {}

        results[self.group][self.type_short()][self.id] = sec

    def type_short(self):
        return self.SECTION_TYPE_SHORT[self.type][1]

    def type_long(self):
        return self.SECTION_TYPE[self.type][1]

    class Meta:
        abstract = True

class SchedrUserManager(auth.models.UserManager):
    def create_user(self, username, email, password=None, first_name='', last_name=''):
        now = datetime.datetime.now()
        user = self.model(None, username, first_name, last_name, email.strip().lower(), 'placeholder', False, True, False, now, now)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.school = School.objects.from_email(email)
	user.code = sha_constructor("%s%s" % (user.id, datetime.datetime.now())).hexdigest()
        user.last_feedback = now - datetime.timedelta(27)
        user.save()
        return user

    def export(self):
        return [u.export() for u in self.all()]


class SchedrUser(auth.models.User):
    code = models.CharField(max_length=40)
    school = models.ForeignKey(School)
    graduation_year = models.IntegerField(blank=True, null=True)
    updated = models.BooleanField(default=False)
    objects = SchedrUserManager()
    last_feedback = models.DateTimeField()
    last_useragent = models.CharField(max_length=255)
    last_view = models.DateTimeField(blank=True, null=True)

    class Meta:
        permissions = (
            ('view_beta', 'Can view beta site'),
        )

    def export(self):
        import schedr
        school = getattr(schedr, self.school.name)
        UserData = school.models.UserData
        return {'email': self.email, 'password': self.password, 'first_name': self.first_name, 'code': self.code, 'date_joined': self.date_joined, 'last_login': self.last_login, 'last_feedback': self.last_feedback, 'school': self.school.name, 'sections': [ud.section.school_id for ud in UserData.objects.filter(user=self)]}

    def generate_push_data(self):
        import schedr
        school = getattr(schedr, self.school.name)
        UserData = school.models.UserData
        results = {}
        for ud in UserData.objects.filter(user=self):
            if not results.has_key(ud.section.course.name()):
                results[ud.section.course.name()] = {}
            results[ud.section.course.name()][ud.section.get_type_short()] = ud.section.times_dict()
        return results

    def generate_ics(self, term, UserData):
        c = icalendar.Calendar()
#        c.add('prodid', '-//www.schedr.com//NONSGML Schedule//EN')
        c.add('VERSION', '2.0')
        c.add('METHOD', 'PUBLISH')
        c.add('X-ORIGINAL-URL', 'http://www.schedr.com/')
        c.add('X-WR-CALNAME', 'Schedr - %s' % self.username)
        c.add('X-WR-TIMEZONE', 'US/Eastern')
        for ud in UserData.objects.filter(user=self, section__course__term=term):
            for event in ud.section.to_ics():
                c.add_component(event)
        return c.as_string()
        

    def generate_course_pdf(self, term, UserData):
        return schedr.util.generate_course_pdf(term, self.email, [ud.section for ud in UserData.objects.filter(user=self, section__course__term=term)], "Print your course schedule for free at http://www.schedr.com/%s/" % self.school.name)

    def generate_exam_pdf(self, term, UserData, Final):
        finals = []
        unmatched = set()
        for ud in UserData.objects.filter(user=self, section__course__term=term).exclude(section__type=Section.DIS).exclude(section__type=Section.LAB):
            try:
                finals.append(Final.objects.get(section=ud.section))
                if ud.section.course in unmatched:
                    unmatched.remove(ud.section.course)
            except Final.DoesNotExist:
                unmatched.add(ud.section.course)

        for c in unmatched:
            f = Final.objects.filter(course=c)
            if len(f) > 0:
                finals.append(f[0])

        if len(finals) == 0:
            return None
                
        return schedr.util.generate_exam_pdf(term, self.email, finals, "Print your course and exam schedule for free at http://www.schedr.com/%s/" % self.school.name)

    def json(self):
        return '{"email":"%s", "name":"%s", "id":%i, "school":"%s"}' % (self.email, self.first_name, self.id, self.school.name)

    def saved_data(self, term, school, Section, UserData):
        ins = {}
        loc = {}
        courses = set()
        sections = []
        for ud in UserData.objects.filter(user=self, section__course__term=term):
            courses.add(ud.section.course)
            sections.append(ud.section)

        c = {}
        for course in courses:
            c[course.id] = {'name': course.name(), 'title': course.title, 'url': course.get_absolute_url(), 'sec': {}, 'credits': course.credits_array()}
            for section in Section.objects.filter(course=course):
                section.export(c[course.id]['sec'], ins, loc, section in sections)

        return simplejson.dumps({'courses': c, 'ins': ins, 'loc': loc})

class UserData(models.Model):
    section = models.ForeignKey("Section")
    def __unicode__(self):
        return "%s - %s" % (self.user, self.section)
    class Meta:
        abstract = True
