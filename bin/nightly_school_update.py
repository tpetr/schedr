#!/usr/bin/env python

import os
import sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'schedr.settings'
sys.path.append('/home/tpetr/')
sys.path.append('/home/tpetr/schedr')

from datetime import datetime
from schedr.base.models import School
from schedr.accounts.models import PendingRegistration

from django.core.mail import EmailMessage
from django.template.loader import render_to_string

schools = []

dt_start = datetime.now()
dt_all = datetime.now()

cache = '-nocache' not in sys.argv
parse = '-noparse' not in sys.argv
verbose = '-v' in sys.argv

if verbose and not cache:
    print " * Not caching data"
if verbose and not parse:
    print " * Not parsing data"

reg_cleared = PendingRegistration.objects.delete_expired_users()
if verbose:
    print "Cleared %i expired registrations" % reg_cleared

for school in School.objects.all():
    if verbose:
        print "Doing %s" % school.title
    importer = __import__('schedr.%s' % school.name, globals(), locals(), ['importer']).importer
    dt = datetime.now()
    if cache:
        if verbose:
            print "   Caching data"
        importer.cache_data()

    t_cache = datetime.now() - dt
    if verbose and cache:
        print "   Cache time: %s" % t_cache
    dt = datetime.now()
    
    locs = []
    if parse:
        if verbose:
            print "   Parsing data"
        importer.parse_data(unknown_locations=locs, verbose=verbose)
    t_parse = datetime.now() - dt
    if verbose:
        print "   Parse time: %s" % t_parse

    school.last_updated = datetime.now()
    school.save()
    
    schools.append({'school': school, 'cache_time': t_cache, 'parse_time': t_parse, 'locations': locs})

t_all = datetime.now() - dt_all

if verbose:
    print "Completed in %s" % t_all

dt = datetime.now()

msg = EmailMessage('[Schedr] Nightly Import - %s' % dt.strftime("%b %d"), render_to_string("emails/import.html", {'schools': schools, 'dt': dt_start, 'elapsed': t_all}), 'no-reply@schedr.com', ['trpetr@gmail.com'])
msg.content_subtype = 'html'
msg.send()
