#!/usr/bin/env python

import os
import sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'schedr.settings'
sys.path.append('/home/tpetr/')
sys.path.append('/home/tpetr/schedr')

from schedr.umass import importer
importer.load_course_descriptions()
