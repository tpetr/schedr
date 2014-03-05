from schedr.uri.models import Term, Major, Course, Section, Instructor, Location, LocationImport, Final
from django.contrib import admin

class TermAdmin(admin.ModelAdmin):
    list_display = ('semester', 'year', 'name', 'active', 'visible', 'finals_visible')
    list_filter = ['year', 'active', 'visible', 'finals_visible']

class MajorAdmin(admin.ModelAdmin):
    list_display = ('name', 'title')

class CourseAdmin(admin.ModelAdmin):
    list_display = ('major', 'number', 'title', 'tba', 'closed', 'credits', 'credits_max')
    list_filter = ['major']
    search_fields = ['number']

class SectionAdmin(admin.ModelAdmin):
    list_display = ('school_id', 'course', 'group', 'type', 'tba')
    search_fields = ['school_id']

class FinalAdmin(admin.ModelAdmin):
    list_display = ('course', 'section', 'date', 'start', 'end')

class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'title', 'lat', 'lng', 'zoom')

class InstructorAdmin(admin.ModelAdmin):
    list_display = ('name', 'rating', 'rating_id')
    search_fields = ['name']

admin.site.register(Term, TermAdmin)
admin.site.register(Major, MajorAdmin)
admin.site.register(Course, CourseAdmin)
admin.site.register(Section, SectionAdmin)
admin.site.register(Final, FinalAdmin)
admin.site.register(Instructor, InstructorAdmin)
admin.site.register(Location, LocationAdmin)
admin.site.register(LocationImport)
