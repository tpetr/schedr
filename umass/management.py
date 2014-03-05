from django.db.models import signals
from schedr.base.models import School, SchedrUser
from schedr.umass import models as umass_app
from schedr.umass.models import Major, Term, Location
from schedr.umass import settings, importer
from schedr import settings as site_settings

def setup_school_umass(app, created_models, verbosity, **kwargs):
    if School in created_models:
        if verbosity >= 2:
            print "Creating %s school object" % settings.TITLE
        s = School(name=settings.NAME, title=settings.TITLE, full_title=settings.FULL_TITLE, email_suffix=settings.EMAIL_SUFFIX, active=True)
        if site_settings.DEBUG:
           s.visible = True
        s.save()

    if Major in created_models:
        importer.import_majors()

    if Location in created_models:
        importer.import_locations()

    if Term in created_models:
        t = importer.create_current_term()
        t.active = True
        if site_settings.DEBUG:
            t.visible = True
        t.save()

    if site_settings.DEBUG and SchedrUser in created_models:
        user = SchedrUser.objects.create_user("test@%s" % (settings.EMAIL_SUFFIX), "test")
        user.school = s
        user.save()

signals.post_syncdb.connect(setup_school_umass, sender=umass_app)
