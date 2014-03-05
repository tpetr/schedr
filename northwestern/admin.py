from schedr.northwestern.models import Term, Major, Course, Section, Instructor, Location, LocationImport
from django.contrib import admin

class TermAdmin(admin.ModelAdmin):
    list_display = ('semester', 'year', 'name', 'active', 'visible', 'finals_visible')
    list_filter = ['year', 'active', 'visible', 'finals_visible']

class MajorAdmin(admin.ModelAdmin):
    list_display = ('name', 'title')

class CourseAdmin(admin.ModelAdmin):
    list_display = ('major', 'number', 'term', 'title', 'tba')
    list_filter = ['major']
    search_fields = ['number']

class SectionAdmin(admin.ModelAdmin):
    list_display = ('school_id', 'course', 'type', 'tba')
    search_fields = ['school_id']

class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'title', 'room_url')

admin.site.register(Term, TermAdmin)
admin.site.register(Major, MajorAdmin)
admin.site.register(Course, CourseAdmin)
admin.site.register(Section, SectionAdmin)
admin.site.register(Instructor)
admin.site.register(Location, LocationAdmin)
admin.site.register(LocationImport)
