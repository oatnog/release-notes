import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'relnotes.settings'

sys.path.append('/local/home/a/Source/release-notes')

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()