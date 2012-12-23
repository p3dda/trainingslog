import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

path=os.path.join(os.path.dirname(__file__),"..")
if path not in sys.path:
	sys.path.append(path)

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
