#!/usr/bin/env python

import os
import sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'schedr.settings'
sys.path.append('/home/tpetr/')
sys.path.append('/home/tpetr/schedr/')

from datetime import datetime
from schedr.base.models import SchedrUser
from schedr.api.models import Application
from django.utils import simplejson
from django.utils.hashcompat import sha_constructor
from oauth_provider.models import Token
import schedr
import urllib2, urllib

from schedr.api.utils import push_data

users = {}
user_to_token = {}
courses = {}
sections = {}
section_days = {}
section_to_course = {}
locations = {}

def cache_course(c):
    if courses.has_key(c.id): return c.id
    courses[c.id] = "['%s','%s']" % (c, c.title)
    return c.id

def cache_section(s):
    if sections.has_key(s.id): return s.id
    cid = cache_course(s.course)
    section_to_course[s.id] = cid
    data = {'cid': cid, 'sid': s.school_id}
    if s.tba: data['tba'] = 1

    days = []

    d = []
    if s.mon_start:
        d.append(s.mon_start.strftime("%H:%M:%S"))
        d.append(s.mon_end.strftime("%H:%M:%S"))
        if s.mon_location:
            d.append(cache_location(s.mon_location))
            d.append(s.mon_room)
    days.append(d)

    d = []
    if s.tue_start:
        d.append(s.tue_start.strftime("%H:%M:%S"))
        d.append(s.tue_end.strftime("%H:%M:%S"))
        if s.tue_location:
            d.append(cache_location(s.tue_location))
            d.append(s.tue_room)
    days.append(d)

    d = []
    if s.wed_start:
        d.append(s.wed_start.strftime("%H:%M:%S"))
        d.append(s.wed_end.strftime("%H:%M:%S"))
        if s.wed_location:
            d.append(cache_location(s.wed_location))
            d.append(s.wed_room)
    days.append(d)

    d = []
    if s.thu_start:
        d.append(s.thu_start.strftime("%H:%M:%S"))
        d.append(s.thu_end.strftime("%H:%M:%S"))
        if s.thu_location:
            d.append(cache_location(s.thu_location))
            d.append(s.thu_room)
    days.append(d)

    d = []
    if s.fri_start:
        d.append(s.fri_start.strftime("%H:%M:%S"))
        d.append(s.fri_end.strftime("%H:%M:%S"))
        if s.fri_location:
            d.append(cache_location(s.fri_location))
            d.append(s.fri_room)
    days.append(d)

    data['days'] = days
    section_days[s.id] = days

    sections[s.id] = simplejson.dumps(data)

    return s.id

def cache_location(loc):
    if locations.has_key(loc.id): return loc.id
    locations[loc.id] = "['%s','%s']" % (loc.name, loc.title)
    return loc.id

verbose = '-v' in sys.argv

apps = Application.objects.filter(push_enabled=True)

if verbose: print "Collecting section data"
for app in apps:
    for token in Token.objects.filter(consumer=app.consumer, token_type=Token.ACCESS, is_approved=True, user__schedruser__updated=True): #app.users.filter(schedruser__updated=True, is_active=True):
        user = token.user
        school = getattr(schedr, user.schedruser.school.name)
        if not users.has_key(user.id):
            if verbose: print "   %s" % user
            if not users.has_key(user.id): users[user.id] = []
            user_to_token[user.id] = token.key
            for ud in school.models.UserData.objects.filter(user=user):
                users[user.id].append(cache_section(ud.section))
            su = user.schedruser
            su.updated = False
            su.save()

if len(users) == 0:
    if verbose: print "No new data to push"
else:
    for app in apps:
        data = {}
        app_courses = {}
        app_locations = {}
        updated = False
        for user in app.users.all():
            if users[user.id] is None: continue
            updated = True
            data[user_to_token[user.id]] = []
            for sid in users[user.id]:
                cid = section_to_course[sid]
                if not app_courses.has_key(cid): app_courses[cid] = courses[cid]
                for d in section_days[sid]:
                    if len(d) < 3: continue
                    if not app_locations.has_key(d[2]): app_locations[d[2]] = locations[d[2]]
                data[user_to_token[user.id]].append(sections[sid])
        if updated:
            json_users = "{" + ','.join(["'%s':[%s]" % (k, ','.join(v)) for k, v in data.items()]) + "}"
            json_courses = "{"+ ','.join(["%s:%s" % (k, v) for k, v in app_courses.items()]) + "}"
            json_locations = "{"+ ','.join(["%s:%s" % (k, v) for k, v in app_locations.items()]) + "}"
            json_data = "[%s,%s,%s]" % (json_users, json_courses, json_locations)
            if verbose:
                print "Pushing: %s" % json_data
            response = push_data(app, json_data)
            if verbose:
                print "Pushed: %s" % response.read()
        
