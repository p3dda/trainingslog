from settings import *

GARMIN_KEYS = (('https://trainingslog.p3dda.net', '987bf2eb69a9d25af6417b91ce0e9068'),
				('http://trainingslog.p3dda.net', '2132e836528038daf9b480ce51119471'))

logging.basicConfig(level=logging.DEBUG,
	format='%(levelname)s %(module)s %(process)d %(thread)d %(message)s',
	filename='django.log',
	filemode='a+')
