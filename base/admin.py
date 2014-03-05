from schedr.base.models import School, SchedrUser, Feedback
from django.contrib import admin

class SchedrUserAdmin(admin.ModelAdmin):
    list_display = ('email', 'username', 'first_name', 'updated', 'last_view', 'last_login', 'date_joined', 'graduation_year', 'last_useragent')
    list_filter = ['school']
    ordering = ['-last_view']

admin.site.register(School)
admin.site.register(SchedrUser, SchedrUserAdmin)
admin.site.register(Feedback)
