#!/usr/bin/env python

import os
import sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'schedr.settings'
sys.path.append('/home/tpetr/')

import pickle

from schedr.base.models import SchedrUser, School
import schedr

file = open(sys.argv[1], "rb")
data = pickle.load(file)
file.close()

school = School.objects.all()[0]

for user in data:
    try:
        u = SchedrUser.objects.get(email=user['email'])
        print "Already exists: %s" % user['email']
        continue
    except SchedrUser.DoesNotExist:
        pass

    if school.name != user['school']:
        school = School.objects.get(name=user['school'])
    
    try:
        u = SchedrUser(username=user['email'], email=user['email'], password=user['password'], first_name=user['first_name'], code=user['code'], date_joined=user['date_joined'], last_login=user['last_login'], last_feedback=user['last_feedback'], school=school);
        u.save()
    except:
        continue

    smod = getattr(schedr, user['school'])
    UserData = smod.models.UserData
    Section = smod.models.Section

    for sid in user['sections']:
        try:
            sec = Section.objects.get(school_id=sid)
            ud = UserData(user=u, section=sec)
            ud.save()
        except:
            print "   Error with %s" % sid

    print "Added: %s" % user['email']
