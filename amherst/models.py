from django.db import models
from schedr import base
from django.contrib import auth
from schedr.base.models import SchedrUser
from schedr.umass import settings

class Term(base.models.Term):
    FALL = 0
    SUMMER = 1
    SPRING = 2
    WINTER = 3
    TERMS = (
        (FALL, 'Fall'),
        (SPRING, 'Spring'),
    )
    semester = models.IntegerField(choices=TERMS)
    school_id = models.CharField(max_length=6)
    school_name = settings.NAME

class Major(base.models.Major):
    name = models.CharField("Name", max_length=4, help_text="Short name of major (ex. ENGIN)", unique=True)

class Course(base.models.Course):
    school_name = settings.NAME

class Final(base.models.Final):
    pass

class Instructor(base.models.Instructor):
    pass

class Location(base.models.Location):
    class Meta:
        ordering = ['title']

class Section(base.models.Section):
    group = 1
    school_id = models.CharField("School ID", max_length=20, unique=True)

class UserData(base.models.UserData):
    user = models.ForeignKey("base.SchedrUser", related_name="%(class)s_related_amherst")
