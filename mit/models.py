from django.db import models
from schedr import base
from django.contrib import auth
from schedr.base.models import SchedrUser, School
from schedr.mit import settings

class Event(base.models.Event):
    pass

class Term(base.models.Term):
    FALL = 0
    SUMMER = 1
    SPRING = 2
    WINTER = 3
    TERMS = (
        (FALL, 'Fall'),
        (SUMMER, 'Summer'),
        (SPRING, 'Spring'),
        (WINTER, 'Winter'),
    )
    semester = models.IntegerField(choices=TERMS)
    school_name = settings.NAME

class Major(base.models.Major):
    name = models.CharField("Major Name", max_length=3, unique=True)

class Course(base.models.Course):
    school_name = settings.NAME
    BIO = 0
    CHEM = 1
    ILAB = 2
    REST = 3
    CALC1 = 4
    CALC2 = 5
    PHYS1 = 6
    PHYS2 = 7
    REQS_LIST = (
        (BIO, 'Biology'),
        (CHEM, 'Chemistry'),
        (ILAB, 'Institute LAB'),
        (REST, 'REST'),
        (CALC1, 'Calculus 1'),
        (CALC2, 'Calculus 2'),
        (PHYS1, 'Physics 1'),
        (PHYS2, 'Physics 2'),
    )
    reqs = models.IntegerField("Requirements", choices=REQS_LIST, blank=True, null=True)
    group = None
    group_literal = None
    school_name = settings.NAME

    def __unicode__(self):
        return "%s.%s" % (self.major.name, self.number)

    def name(self):
        return "%s.%s" % (self.major.name, self.number)

    def get_absolute_url(self):
        return "/%s/courses/%s/%s.%s" % (self.school_name, self.term.name, self.major.name, self.number)
     

class Instructor(base.models.Instructor):
    pass

class Location(base.models.Location):
    name = models.CharField(max_length=6, unique=True)

class Section(base.models.Section):
    group = 1
    school_id = models.CharField("School ID", max_length=16)
    def __unicode__(self):
        return "%s" % self.school_id

class UserData(base.models.UserData):
    user = models.ForeignKey("base.SchedrUser", related_name="%(class)s_related_mit")
