from django.db import models
from schedr import base
from schedr.northwestern import settings

class Term(base.models.Term):
    SPRING = 0
    SUMMER = 1
    FALL = 2
    WINTER = 3
    TERMS = (
        (SPRING, 'Spring'),
        (SUMMER, 'Summer'),
        (FALL, 'Fall'),
        (WINTER, 'Winter'),
    )
    semester = models.IntegerField(choices=TERMS)
    school_id = models.IntegerField(unique=True)
    school_name = settings.NAME

    class Meta:
        ordering = ['-school_id']

class Major(base.models.Major):
    name = models.CharField("Name", max_length=8, help_text="Short name of major (ex. ENGIN)", unique=True)
    nu_school_id = models.IntegerField()
    nu_dept_id = models.IntegerField()

class Course(base.models.Course):
    school_name = settings.NAME

    GENED_LIST = ('FAL', 'HSV', 'SBS', 'A-I', 'A-II', 'A-III', 'A-IV', 'A-V', 'A-VI')

    gened_FAL = models.BooleanField(default=False, blank=True)
    gened_HSV = models.BooleanField(default=False, blank=True)
    gened_SBS = models.BooleanField(default=False, blank=True)
    gened_A1 = models.BooleanField(default=False, blank=True)
    gened_A2 = models.BooleanField(default=False, blank=True)
    gened_A3 = models.BooleanField(default=False, blank=True)
    gened_A4 = models.BooleanField(default=False, blank=True)
    gened_A5 = models.BooleanField(default=False, blank=True)
    gened_A6 = models.BooleanField(default=False, blank=True)

    # WCAS
    gened_WCAS_EV = models.BooleanField("Ethics & Values", default=False, blank=True)
    gened_WCAS_FS = models.BooleanField("Formal Studies", default=False, blank=True)
    gened_WCAS_HS = models.BooleanField("Historical Studies", default=False, blank=True)
    gened_WCAS_I = models.BooleanField("Interdisciplinary", default=False, blank=True)
    gened_WCAS_LFA = models.BooleanField("Literature & Fine Arts", default=False, blank=True)
    gened_WCAS_NS = models.BooleanField("Natural Sciences", default=False, blank=True)
    gened_WCAS_SBS = models.BooleanField("Social & Behaviorial Sciences", default=False, blank=True)

    def geneds(self):
        list = []
        if self.gened_FAL:
            list.append('FAL')
        if self.gened_HSV:
            list.append('HSV')
        if self.gened_SBS:
            list.append('SBS')
        if self.gened_A1:
            list.append('A-I')
        if self.gened_A2:
            list.append('A-II')
        if self.gened_A3:
            list.append('A-III')
        if self.gened_A4:
            list.append('A-IV')
        if self.gened_A5:
            list.append('A-V')
        if self.gened_A6:
            list.append('A-VI')
        return ','.join(list)

    #def json(self):
    #    return "[%i,\"%s\",%i,\"%s\",\"%s\"]" % (self.id, self.number, self.tba, self.title.replace('"', '\\"'), self.geneds())


class Location(base.models.Location):
    name = models.CharField(max_length=4, unique=True)
    school_id = models.IntegerField(blank=True, null=True)

class LocationImport(base.models.LocationImport):
    pass

class Instructor(base.models.Instructor):
    pass

class Section(base.models.Section):
    school_id = models.CharField("School ID", max_length=5, unique=True)
    group = 1

class UserData(base.models.UserData):
    user = models.ForeignKey('base.SchedrUser', related_name="%(class)s_related_northwestern")
