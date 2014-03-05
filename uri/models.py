from django.db import models
from schedr import base
from django.contrib import auth
from schedr.base.models import SchedrUser
from schedr.uri import settings

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
    school_id = models.IntegerField(unique=True)
    school_name = settings.NAME

class Major(base.models.Major):
    name = models.CharField("Name", max_length=4, help_text="Short name of major (ex. ENGIN)", unique=True)

class Course(base.models.Course):
    school_name = settings.NAME
    credits_max = models.IntegerField(blank=True, null=True)
    def credits_array(self):
        return [self.credits, self.credits_max]
    def credits_str(self):
        if self.credits is None:
            return ''
        if self.credits_max is None:
            return self.credits
        return "%s-%s" % (self.credits, self.credits_max)

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
    user = models.ForeignKey("base.SchedrUser", related_name="%(class)s_related_uri")
