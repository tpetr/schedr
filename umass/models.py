from django.db import models
from schedr import base
from django.contrib import auth
from schedr.base.models import SchedrUser
from schedr.umass import settings

class Term(base.models.Term):
    FALL = 2
    SUMMER = 1
    SPRING = 0 
    WINTER = 3
    TERMS = (
        (FALL, 'Fall'),
        (SUMMER, 'Summer'),
        (SPRING, 'Spring'),
        (WINTER, 'Winter'),
    )
    semester = models.IntegerField(choices=TERMS)
    school_id = models.IntegerField(unique=True)
    school_name = settings.NAME

class Major(base.models.Major):
    name = models.CharField("Name", max_length=8, help_text="Short name of major (ex. ENGIN)", unique=True)


class Course(base.models.Course):
    school_name = settings.NAME
    desc_id = models.IntegerField(blank=True, null=True)
    GENED_LIST = ('AL', 'AT', 'BS', 'CW', 'HS', 'PS', 'R1', 'R2', 'SB', 'SI', 'G', 'U', 'I')
    credits_max = models.IntegerField(blank=True, null=True)
    def credits_array(self):
        return [self.credits, self.credits_max]
    def credits_str(self):
        if self.credits is None:
            return ''
        if self.credits_max is None:
            return self.credits
        return "%s-%s" % (self.credits, self.credits_max)
    gened_AL = models.BooleanField(default=False, blank=True)
    gened_AT = models.BooleanField(default=False, blank=True)
    gened_BS = models.BooleanField(default=False, blank=True)
    gened_CW = models.BooleanField(default=False, blank=True)
    gened_HS = models.BooleanField(default=False, blank=True)
    gened_PS = models.BooleanField(default=False, blank=True)
    gened_R1 = models.BooleanField(default=False, blank=True)
    gened_R2 = models.BooleanField(default=False, blank=True)
    gened_SB = models.BooleanField(default=False, blank=True)
    gened_SI = models.BooleanField(default=False, blank=True)
    gened_G  = models.BooleanField(default=False, blank=True)
    gened_U  = models.BooleanField(default=False, blank=True)
    gened_I  = models.BooleanField(default=False, blank=True)
    def geneds(self):
        list = []
        if self.gened_AL:
            list.append('AL')
        if self.gened_AT:
            list.append('AT')
        if self.gened_BS:
            list.append('BS')
        if self.gened_CW:
            list.append('CW')
        if self.gened_HS:
            list.append('HS')
        if self.gened_PS:
            list.append('PS')
        if self.gened_R1:
            list.append('R1')
        if self.gened_R2:
            list.append('R2')
        if self.gened_SB:
            list.append('SB')
        if self.gened_SI:
            list.append('SI')
        if self.gened_G:
            list.append('G')
        if self.gened_U:
            list.append('U')
        if self.gened_I:
            list.append('I')
        return ','.join(list)

    def json(self):
        return "[%i,\"%s\",%i,%i,\"%s\",\"%s\",\"%s\"]" % (self.id, self.number, self.tba, self.closed, self.title.replace('"', '\\"'), self.geneds(), self.credits_str())

class MajorTrack(base.models.MajorTrack):
    pass

class RequiredCourse(base.models.RequiredCourse):
    pass

class Final(base.models.Final):
    pass

class Instructor(base.models.Instructor):
    pass

class Location(base.models.Location):
    name = models.CharField(max_length=4, unique=True)
    lat = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    lng = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    zoom = models.IntegerField(default=4, blank=True, null=True)

class LocationImport(base.models.LocationImport):
    pass

class Section(base.models.Section):
    group = models.CharField(max_length=5, default="1")
    group_literal = models.CharField(max_length=5, blank=True, null=True)
    school_id = models.CharField("School ID", max_length=5, unique=True)

class UserData(base.models.UserData):
    user = models.ForeignKey("base.SchedrUser", related_name="%(class)s_related_umass")
