from django.conf.urls import patterns, include, url
from django.conf.urls.static import static

from activities.views import ActivityListJson

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
import django.contrib.auth.views
from django.http import HttpResponse
from activities.models import Activity, Sport
import settings
admin.autodiscover()

urlpatterns = patterns('activities.views',
	url(r'^$', 'list_activities'),
	url(r'^activities/$', 'list_activities'),
	url(r'^activities/get/$', ActivityListJson.as_view(), name='activity_list_json'),
	url(r'^activities/get_json/$', 'get_activity'),
	url(r'^activities/(?P<activity_id>\d+)/$', 'detail'),
	url(r'^activities/delete/$', 'delete_activity'),
	url(r'^calformula/add/$', 'add_calformula'),
	url(r'^calformula/get/$', 'get_calformula'),
	url(r'^calformula/delete/$', 'delete_calformula'),
	url(r'^sports/add/$', 'add_sport'),
	url(r'^sports/delete/$', 'delete_sport'),
	url(r'^sports/get/$', 'get_sport'),
	url(r'^events/add/$', 'add_event'),
	url(r'^events/delete/$', 'delete_event'),
	url(r'^events/get/$', 'get_event'),
	url(r'^events/$', 'list_event'),
	url(r'^events/get/$', 'get_events'),
	url(r'^equipments/add/$', 'add_equipment'),
	url(r'^equipments/delete/$', 'delete_equipment'),
	url(r'^equipments/get/$', 'get_equipment'),
	url(r'^equipments/$', 'list_equipment'),
	url(r'^reports/$', 'reports'),
	url(r'^reports/get/$', 'get_report_data'),
	url(r'^calendar/$', 'calendar'),
	url(r'^calendar/events/$', 'calendar_get_events'),
	url(r'^settings/$', 'settings'),
	url(r'^forms/(?P<model>[a-z]+)(?:/(?P<itemid>\d+)/)?$', 'generic_form'),
)

urlpatterns += patterns('health.views',
	url(r'^health/$', 'show_weight'),
	url(r'^health/data/$', 'get_data'),
	url(r'^health/desease/add/$', 'add_desease'),
	url(r'^health/desease/get/$', 'get_desease'),
	url(r'^health/weights/add/$', 'add_weight'),
	url(r'^health/weightgoals/add/$', 'add_weightgoal'),
	url(r'^health/pulses/add/$', 'add_pulse'),
)

urlpatterns += patterns('',
url(r'^robots\.txt$', lambda r: HttpResponse("User-agent: *\nDisallow: /", content_type="text/plain"))
)

urlpatterns += patterns('',
	url(r'^admin/', include(admin.site.urls)),
	url(r'^accounts/login/$', 'django.contrib.auth.views.login', name='login'),
	url(r'^accounts/logout/$', 'django.contrib.auth.views.logout', {'next_page': "/activities/"}),
	url(r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
	url(r'^static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.STATIC_ROOT}),
)

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
