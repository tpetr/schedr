from django.core.management.base import NoArgsCommand, CommandError
import os
from datetime import date

class Command(NoArgsCommand):
    help = "Publishes the current development javascript to all users"

    requires_model_validation = False

    def handle_noargs(self, **options):
	str = date.today().isoformat()

        # commit dev script
#	print "   Committing dev script..."
#        os.system('svn commit /home/tpetr/public_html/static/js/schedr_dev.js -m "publish_js"')
#	print ""

        # minify js
	print "   Minifying..."
        os.system('java -jar /home/tpetr/yuicompressor/yuicompressor.jar -o /home/tpetr/public_html/static/js/schedr_%s.js /home/tpetr/public_html/static/js/schedr_dev.js' % str)
        print ""

	# add new js to svn
#	print "   Adding 'schedr_%s.js' to svn..." % str 
#	os.system('svn add /home/tpetr/public_html/static/js/schedr_%s.js' % str)
#        os.system('svn commit /home/tpetr/public_html/static/js/schedr_%s.js -m "published from dev"' % str)
