#!/usr/bin/env python

import os
import sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'schedr.settings'
sys.path.append('/home/tpetr/')

import pickle
from datetime import datetime

from schedr.base.models import SchedrUser

data = SchedrUser.objects.export()
dt = datetime.now()

file = open("users_%s.pickle" % dt.strftime("%Y-%m-%d"), "wb")
pickle.dump(data, file, pickle.HIGHEST_PROTOCOL)
file.close()

print "Exported %i users" % len(data)
