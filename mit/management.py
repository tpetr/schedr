from django.db.models import signals
from schedr.base.models import School, SchedrUser
from schedr.mit import models as mit_app
from schedr.mit.models import Major, Term
from schedr.mit import settings, importer
from schedr import settings as site_settings

def setup_school_mit(app, created_models, verbosity, **kwargs):
    if School in created_models:
        if verbosity >= 2:
            print "Creating %s school object" % settings.TITLE
        s = School(name=settings.NAME, title=settings.TITLE, email_suffix=settings.EMAIL_SUFFIX)
    
        if site_settings.DEBUG:
            s.active = True
            s.visible = True

        s.save()

    if Major in created_models:
        importer.import_majors()

    if Term in created_models:
        t = importer.create_current_term()
        if site_settings.DEBUG:
            t.active = True
            t.visible = True
        t.save()

    if site_settings.DEBUG:
        user = SchedrUser.objects.create_user("test@%s" % (settings.EMAIL_SUFFIX), "test")
        user.school = s
        user.save()

signals.post_syncdb.connect(setup_school_mit, sender=mit_app)
