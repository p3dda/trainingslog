# Create your views here.
from base64 import b64decode
import json
import copy
import datetime
import dateutil.parser
import os
import tempfile
import time
import traceback
import urllib2
import logging

found_xml_parser=False

try:
	if not found_xml_parser:
		from elementtree.ElementTree import ElementTree
except ImportError, msg:
	pass
else:
	found_xml_parser=True

try:
	if not found_xml_parser:
		from xml.etree.ElementTree import ElementTree
except ImportError, msg:
	pass
else:
	found_xml_parser=True

if not found_xml_parser:
	raise ImportError("No valid XML parsers found. Please install a Python XML parser")

from activities.extras import tcx2gpx
from activities.models import Activity, ActivityTemplate, CalorieFormula, Equipment, Event, Sport, Track, Lap
from activities.forms import ActivityForm,  EventForm, EquipmentForm
from activities.utils import activities_summary, int_or_none, float_or_none, str_float_or_none, pace_to_speed, speed_to_pace, seconds_to_time, TCXTrack


from health.models import Desease, Weight, Goal

from django.http import Http404, HttpResponseForbidden, HttpResponseRedirect, HttpResponse, HttpResponseBadRequest
from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.context_processors import csrf
from django.utils import simplejson
from django.utils import timezone
from django.core import serializers
from django.contrib.auth.models import User
from django.db.models import Sum
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.core.files.base import File
from django.core.files.temp import NamedTemporaryFile
from django.conf import settings as django_settings

@login_required
def add_calformula(request):
	if request.method == 'POST':
		print "In POST request"
		
		if request.POST.has_key('update_id'):
			calformula = CalorieFormula.objects.get(pk=int(request.POST.get('update_id')))
			# If selected_by_id object does not belong to current user, create new activity
			if calformula.user != request.user:
				calformula = CalorieFormula(user = request.user)
		else:
			calformula = CalorieFormula(user = request.user)

		calformula.name = request.POST.get('name')
		calformula.weight_dist_factor = request.POST.get('weight_dist_factor')
		calformula.weight_time_factor = request.POST.get('weight_time_factor')
		calformula.save()
		return HttpResponse(simplejson.dumps((True, )))
	else:
		return HttpResponseBadRequest

@login_required
def delete_calformula(request):
	if request.method == 'POST':
		print "In POST request"
		print request.POST.items()
		
		calformula = CalorieFormula.objects.get(pk=int(request.POST.get('id')))
		if calformula.user == request.user:
			calformula.delete()
			return HttpResponse(simplejson.dumps((True, )))
		else:
			return HttpResponse(simplejson.dumps((False, "Permission denied")))

@login_required
def get_calformula(request):

	calformula = CalorieFormula.objects.get(pk=int(request.GET.get('id')))
	if calformula.user == request.user or calformula.public:
		return HttpResponse(serializers.serialize('json', [calformula]), mimetype='application/json');
	else:
		return HttpResponseForbidden()

@login_required
def add_sport(request):
	if request.method == 'POST':
		print "In POST request"
		
		if request.POST.has_key('update_id'):
			sport = Sport.objects.get(pk=int(request.POST.get('update_id')))
			# If selected_by_id activity does not belong to current user, create new activity
			if sport.user != request.user:
				sport = Sport(user = request.user)
		else:
			sport = Sport(user = request.user)

		sport.name = request.POST.get('name')
		
		calorie_formula_id = int(request.POST.get('calformula'))
		if calorie_formula_id != -1:
			sport.calorie_formula = CalorieFormula.objects.get(pk=int(request.POST.get('calformula')))
		else:
			sport.calorie_formula = None
		
		sport.color = request.POST.get('color')
		if request.POST.get('speed_as_pace') == '0':
			sport.speed_as_pace = False
		else:
			sport.speed_as_pace = True
		sport.save()
		return HttpResponse(simplejson.dumps((True, )))
	else:
		return HttpResponseBadRequest

@login_required
def get_sport(request):
	sport_id = request.GET.get('id');
	
	sport = Sport.objects.get(pk=int(sport_id))
	if sport.user == request.user:
		return HttpResponse(serializers.serialize('json', [sport]), mimetype='application/json');
	else:
		return HttpResponseForbidden()

@login_required
def delete_sport(request):
	if request.method == 'POST':
		print "In POST request"
		print request.POST.items()
		
		sport = Sport.objects.get(id=int(request.POST.get('id')))
		if sport.user == request.user:
			sport.delete()
			return HttpResponse(simplejson.dumps((True, )))
		else:
			return HttpResponse(simplejson.dumps((False, "Permission denied")))

@login_required
def add_event(request):
	if request.method == 'POST':
		print "In POST request"

		if request.POST.has_key('update_id'):
			event = Event.objects.get(pk=int(request.POST.get('update_id')))
			# If selected_by_id activity does not belong to current user, create new activity
			if event.user != request.user:
				event = Event(user = request.user)
		else:
			event = Event(user = request.user)

		event.name = request.POST.get('name')
		event.save()
		return HttpResponse(simplejson.dumps((True, )))
	else:
		return HttpResponseBadRequest

@login_required
def get_event(request):
	event_id = request.GET.get('id');
	
	event = Event.objects.get(pk=int(event_id))
	if event.user == request.user:
		return HttpResponse(serializers.serialize('json', [event]), mimetype='application/json');
	else:
		return HttpResponseForbidden()

def delete_event(request):
	if request.method == 'POST':
		print "In POST request"
		print request.POST.items()
		
		event = Event.objects.get(id=int(request.POST.get('id')))
		if event.user == request.user:
			event.delete()
			return HttpResponse(simplejson.dumps((True, )))
		else:
			return HttpResponse(simplejson.dumps((False, "Permission denied")))

@login_required
def add_equipment(request):
	if request.method == 'POST':
		print "In POST request"

		if request.POST.has_key('update_id'):
			equipment = Equipment.objects.get(pk=int(request.POST.get('update_id')))
			# If selected_by_id activity does not belong to current user, create new activity
			if equipment.user != request.user:
				equipment = Equipment(user = request.user)
		else:
			equipment = Equipment(user = request.user)
		
		equipment.name = request.POST.get('name')
		equipment.description = request.POST.get('description')
		
		if request.POST.get('distance') != "":
			equipment.distance = request.POST.get('distance')
			
		if request.POST.get('archived') == '0':
			equipment.archived = False
		else:
			equipment.archived = True

		equipment.save()
		return HttpResponse(simplejson.dumps((True, )))
	else:
		return HttpResponseBadRequest

@login_required
def get_equipment(request):
	equipment_id = request.GET.get('id');
	
	equipment = Equipment.objects.get(pk=int(equipment_id))
	if equipment.user == request.user:
		return HttpResponse(serializers.serialize('json', [equipment]), mimetype='application/json');
	else:
		return HttpResponseForbidden()

def delete_equipment(request):
	if request.method == 'POST':
		print "In POST request"
		print request.POST.items()
		
		equipment = Equipment.objects.get(id=int(request.POST.get('id')))
		if equipment.user == request.user:
			equipment.delete()
			return HttpResponse(simplejson.dumps((True, )))
		else:
			return HttpResponse(simplejson.dumps((False, "Permission denied")))

@login_required
def list_event(request):
	return render_to_response('activities/event_list.html', {})

@login_required
def get_events(request):
	event_list = Event.objects.filter(user=request.user)
	return HttpResponse(serializers.serialize('json', event_list), mimetype='application/json')

@login_required
def create_equipment(request):
	form = EquipmentForm()
	if request.method == 'POST':
		form = EquipmentForm(request.POST)
		if form.is_valid():
			equ = form.save(commit = False)
			equ.user = request.user
			equ.save()
			return HttpResponseRedirect('/equipments/')
	return render_to_response('activities/equipment_form.html', {'form': form, 'username': request.user})


@login_required
def list_equipment(request):
	equ_list = Equipment.objects.filter(user=request.user)
	return render_to_response('activities/equipment_list.html', {'equipment_list': equ_list, 'username': request.user})

@login_required
def list_activities(request):
	if request.method == 'POST':
		if len(request.FILES)>0:
			logging.debug("Creating activity from tcx file upload");
			try:
				try:
					newtrack = Track(trackfile=request.FILES['trackfile'])
				except Exception:
					print "Exception occured in file upload"
					raise
			
				newtrack.save()

				activity = importtrack(request, newtrack)
				return HttpResponseRedirect('/activities/%i/?edit=1' % activity.pk)
			except Exception, exc:
				print "Exception raised in importtrack"
				raise
				#return HttpResponse(simplejson.dumps((False, )))
		elif request.POST.has_key('content'):
			logging.debug("Creating activity from text upload");
			try:
				filename = "%s.tcx" % datetime.datetime.now().strftime("%d.%m.%y %H-%M-%S")
				newtrack = Track()

				tmpfile = tempfile.NamedTemporaryFile(mode="w", delete=False)
				tmpfilename = tmpfile.name

				content = request.POST['content']
				tmpfile.write(content)
				tmpfile.close()

				#create tcx file 
				newtrack.trackfile.save(filename, File(open(tmpfilename, 'r')))

				logging.debug("Filename: %s" % filename)
	
				activity = importtrack(request, newtrack)
				tmpfile.close()
				os.remove(tmpfilename)
				return HttpResponse(simplejson.dumps({'success': True, 'redirect_to': '/activities/%i/?edit=1' % activity.pk}))
			except Exception, exc:
				logging.debug( "Exception raised in importtrack: %s" %str(exc))
				for line in traceback.format_exc().splitlines():
					logging.debug(line.strip())
				
				return HttpResponse(simplejson.dumps({'success': False, 'msg': str(exc)}))
			
		else:
			logging.error("Missing upload data");
	else:
		events = Event.objects.filter(user=request.user)
		equipments = Equipment.objects.filter(user=request.user).filter(archived=False)
		sports = Sport.objects.filter(user=request.user)
		calformulas = CalorieFormula.objects.filter(user=request.user) | CalorieFormula.objects.filter(public=True).order_by('public', 'name')
		activitytemplates = ActivityTemplate.objects.filter(user=request.user)
		
		try:
			garmin_keys = django_settings.GARMIN_KEYS
		except AttributeError:
			garmin_keys = False
			
		weight = Weight.objects.filter(user=request.user).order_by('-date')
		if len(weight)>0:
			weight = weight[0]
		else:
			weight = None

		return render_to_response('activities/activity_list.html', {'username': request.user, 'equipments': equipments, 'events': events, 'sports': sports, 'calformulas': calformulas, 'weight': weight, 'activitytemplates': activitytemplates, 'garmin_keys': garmin_keys})

@login_required
def get_activities(request):
	act_list = []
	for activity in Activity.objects.filter(user=request.user):
		act_list.append({'id': activity.id, 'name': activity.name, 'sport': activity.sport.name, 'date': activity.date.strftime("%d.%m.%Y %H:%M"), 'duration': str(datetime.timedelta(days=0,seconds=activity.time))})
	return HttpResponse(simplejson.dumps(act_list))

@login_required
def get_activity(request):
	act_id = request.GET.get('id');
	template = request.GET.get('template')
	
	if template == 'true':
		activity = ActivityTemplate.objects.get(pk=int(act_id))
	else:
		activity = Activity.objects.get(pk=int(act_id))

	if activity.user == request.user:
		return HttpResponse(serializers.serialize('json', [activity]), mimetype='application/json');
#		return HttpResponse(simplejson.dumps(activity))
	else:
		return HttpResponseForbidden()

@login_required
def new_activity(request):
	if request.method == 'POST':
		form = ActivityForm(request.POST)
		if form.is_valid():
			act = form.save(commit = False)
			act.user = request.user
			act.save()
			return HttpResponseRedirect('/activities/')
	else:
		form = ActivityForm()
		
	return render_to_response('activities/activity_new.html', {'form': form, 'username': request.user})

@login_required
def delete_activity(request):
	if request.method == 'POST':
		print "In POST request"
		print request.POST.items()
		
		act = Activity.objects.get(id=int(request.POST.get('id')))
		if act.user == request.user:
			act.delete()
			return HttpResponse(simplejson.dumps({'success': True}))
		else:
			return HttpResponse(simplejson.dumps({'success': False, 'msg': "Permission denied"}))
		
@login_required
def add_activity(request):
	if request.method == 'POST':
		logging.debug("In add_activity post request with parameters %s" % repr(request.POST.items()))
		is_template = request.POST.get('is_template')
		if is_template == 'true':
			act = ActivityTemplate(user = request.user)
		else:
			if request.POST.has_key('update_id'):
				act = Activity.objects.get(pk=int(request.POST.get('update_id')))
				# If selected_by_id activity does not belong to current user, create new activity
				if act.user != request.user:
					act = Activity(user = request.user)
			else:
				act = Activity(user = request.user)
		
		try:	
			act.name = request.POST.get('name')
			act.comment = request.POST.get('comment')
			act.cadence_avg = int_or_none(request.POST.get('cadence_avg'))
			act.cadence_max = int_or_none(request.POST.get('cadence_max'))
			act.calories = int_or_none(request.POST.get('calories'))
			act.distance = str_float_or_none(request.POST.get('distance'))
	
			act.elevation_gain = int_or_none(request.POST.get('elevation_gain'))
			act.elevation_loss = int_or_none(request.POST.get('elevation_loss'))
			act.elevation_min = int_or_none(request.POST.get('elevation_min'))
			act.elevation_max = int_or_none(request.POST.get('elevation_max'))
			act.hf_max = int_or_none(request.POST.get('hr_max'))
			act.hf_avg = int_or_none(request.POST.get('hr_avg'))
			act.time = int_or_none(request.POST.get('time'))
			act.time_elapsed = int_or_none(request.POST.get('time_elapsed'))
			act.time_movement = int_or_none(request.POST.get('time_movement'))
				
			event = Event.objects.get(pk=int(request.POST.get('event')))
			sport = Sport.objects.get(pk=int(request.POST.get('sport')))
			act.event = event
			act.sport = sport
			
			if sport.speed_as_pace:
				if request.POST.get('speed_max') != 'null':
					act.speed_max = str(pace_to_speed(request.POST.get('speed_max')))
				if request.POST.get('speed_avg') != 'null':
					act.speed_avg = str(pace_to_speed(request.POST.get('speed_avg')))
				if request.POST.get('speed_avg_movement') != 'null':
					act.speed_avg_movement = str(pace_to_speed(request.POST.get('speed_avg_movement')))
			else:
				if request.POST.get('speed_max') != 'null':
					act.speed_max = str_float_or_none(request.POST.get('speed_max'))
				if request.POST.get('speed_avg') != 'null':
					act.speed_avg = str_float_or_none(request.POST.get('speed_avg'))
				if request.POST.get('speed_avg_movement') != 'null':
					act.speed_avg_movement = str_float_or_none(request.POST.get('speed_avg_movement'))
	
			equipment_list = request.POST.get('equipment').split(" ")

			datestring = request.POST.get('date') + " " + request.POST.get('datetime')
			try:
				date = datetime.datetime.strptime(datestring, "%d.%m.%Y %H:%M")
			except ValueError:
				try:
					date = datetime.datetime.strptime(datestring, "%d.%m.%Y %H:%M:%S")
				except ValueError:
					if request.POST.get('is_template'):
						date = None
	
			act.date = date
			
			if request.POST.get('public') == '0':
				act.public = False
			else:
				act.public = True
	
			calorie_formula_id = int(request.POST.get('calformula'))
			if calorie_formula_id != -1:
				act.calorie_formula = CalorieFormula.objects.get(pk=int(request.POST.get('calformula')))
			else:
				act.calorie_formula = None
		except Exception, exc:
			logging.exception("Exception occured in add_activits")
			return HttpResponse(simplejson.dumps({'success': False, 'msg': "Fehler aufgetreten: %s" % str(exc)}))
			
		new_act = act.save()

		for eq in equipment_list:
			if eq != '':
				act.equipment.add(Equipment.objects.get(pk=int(eq)))
				print Equipment.objects.get(pk=int(eq))
		
		act.save()
		return HttpResponse(simplejson.dumps({'success': True}))
	else:
		return HttpResponseBadRequest
	
def detail(request, activity_id):
	param = request.GET.get('p', False)
	act = get_object_or_404(Activity, id=activity_id)
	
	public = True
	if request.user.is_authenticated():
		if act.user==request.user:
			public = False
		else:
			if act.public:
				public = True
			else:
				return HttpResponseForbidden()
	else:
		# Do something for anonymous users.
		if act.public:
			public = True
		else:
			return HttpResponseForbidden()

	try:
		fb_app_id = django_settings.FACEBOOK_APP_ID
	except AttributeError:
		fb_app_id = False

	if act.track:
		tcx = act.track.trackfile
		
		#check if preview image is missing
		if not act.track.preview_img:
			logging.debug("No preview image found")
			create_preview(act.track)

		# build absolute URL with domain part for preview image
		# https seems not to be supported by facebook
		if act.track.preview_img:
			preview_img = request.build_absolute_uri(act.track.preview_img.url).replace("https://", "http://")
		else:
			preview_img = None
			
	else:
		tcx = None
		preview_img = None
	
	if not param:
		# no parameter given, reply with activity detail template
		
		if act.sport.speed_as_pace:
			print "Speed_as_pace"
			if act.speed_max:
				act.speed_max = speed_to_pace(act.speed_max)
			if act.speed_avg:
				act.speed_avg = speed_to_pace(act.speed_avg)
			if act.speed_avg_movement:
				act.speed_avg_movement = speed_to_pace(act.speed_avg_movement)
			speed_unit = "min/km"
		else:
			speed_unit = "km/h"
		
		act.time = seconds_to_time(act.time, force_hour=True)
		if act.time_movement:
			act.time_movement = seconds_to_time(act.time_movement)
		if act.time_elapsed:
			act.time_elapsed = seconds_to_time(act.time_elapsed)
		
		laps = Lap.objects.filter(activity = act).order_by('id')
		for lap in laps:
			lap.time = seconds_to_time(lap.time)
			if act.sport.speed_as_pace:
				if lap.speed_max:
					lap.speed_max = speed_to_pace(lap.speed_max)
				if lap.speed_avg:
					lap.speed_avg = speed_to_pace(lap.speed_avg)
	
		if not public:
	
			if request.GET.get('edit', '0')=='1':
				edit=1
			else:
				edit=0
			
			events = Event.objects.filter(user=request.user)
			equipments = Equipment.objects.filter(user=request.user).filter(archived=False)
			sports = Sport.objects.filter(user=request.user)
			calformulas =  CalorieFormula.objects.filter(user=request.user) | CalorieFormula.objects.filter(public=True).order_by('public', 'name')
			activitytemplates = ActivityTemplate.objects.filter(user=request.user)
			weight = Weight.objects.filter(user=request.user).order_by('-date')
			if len(weight)>0:
				weight = weight[0]
			else:
				weight = None
			
			return render_to_response('activities/detail.html', {'activity': act, 'username': request.user, 'speed_unit': speed_unit, 'equipments': equipments, 'events': events, 'sports': sports, 'calformulas': calformulas, 'activitytemplates': activitytemplates, 'weight': weight, 'laps': laps, 'edit': edit, 'tcx': tcx, 'public': public, 'full_url': request.build_absolute_uri(), 'preview_img': preview_img, 'fb_app_id': fb_app_id})
		else:
			return render_to_response('activities/detail.html', {'activity': act, 'speed_unit': speed_unit, 'laps': laps, 'tcx': tcx, 'public': public})
	if param == 'plots':
		if act.track:
			tcxtrack = TCXTrack(act.track)
			
			data = {'altitude': tcxtrack.get_alt(),
					'cadence': tcxtrack.get_cad(),
					'hf': tcxtrack.get_hf(),
					'speed': tcxtrack.get_speed(act.sport.speed_as_pace),
					'speed_foot': tcxtrack.get_speed_foot(act.sport.speed_as_pace)
					}
			
			return HttpResponse(json.dumps(data, sort_keys=True, indent=4),content_type="text/plain")
	
	# last resort
	return Http404()

@login_required
def calendar(request):
	events = Event.objects.filter(user=request.user)
	equipments = Equipment.objects.filter(user=request.user).filter(archived=False)
	sports = Sport.objects.filter(user=request.user)
	calformulas =  CalorieFormula.objects.filter(user=request.user) | CalorieFormula.objects.filter(public=True).order_by('public', 'name')
	weight = Weight.objects.filter(user=request.user).order_by('-date')
	activitytemplates = ActivityTemplate.objects.filter(user=request.user)
	
	if len(weight)>0:
		weight = weight[0]
	else:
		weight = None

	return render_to_response('activities/calendar.html', {'username': request.user, 'equipments': equipments, 'events': events, 'sports': sports, 'calformulas': calformulas, 'weight': weight, 'activitytemplates': activitytemplates})

@login_required
def reports(request):
	events = Event.objects.filter(user=request.user)
	sports = Sport.objects.filter(user=request.user)
	return render_to_response('activities/reports.html', {'username': request.user, 'events': events, 'sports': sports})

@login_required
def get_report_data(request):
	data = {}
	
	startdate_timestamp = request.GET.get('startdate', '')
	enddate_timestamp = request.GET.get('enddate', '')
	mode = request.GET.get('mode', '')
	param_b64 = request.GET.get('param', None)
	if param_b64:
		param = json.loads(b64decode(param_b64))
		event_pks = param["events"]
		sport_pks = param["sports"]
	else:
		event_pks = []
		sport_pks = []
	try:
		start_date = timezone.make_aware(timezone.datetime.utcfromtimestamp(int(startdate_timestamp)/1000), timezone.get_default_timezone())
		end_date = timezone.make_aware(timezone.datetime.utcfromtimestamp(int(enddate_timestamp)/1000), timezone.get_default_timezone())
	except ValueError:
		return HttpResponse(simplejson.dumps((False, "Invalid timestamps")))

	events_filter = []
	for event_pk in event_pks:
		events_filter.append(Event.objects.get(pk=int(event_pk)))
	sports_filter = []
	for sport_pk in sport_pks:
		sports_filter.append(Sport.objects.get(pk=int(sport_pk)))

	if mode == "sports":
		sports = Sport.objects.filter(user=request.user)
		for sport in sports:
			total_time = 0
			activities = Activity.objects.filter(sport=sport, user=request.user, event__in=events_filter, sport__in=sports_filter)
			activities = activities.filter(date__gte = start_date, date__lte = end_date)
	
			data[sport.name] = activities_summary(activities)
			data[sport.name]['color'] = sport.color
			
	elif mode == "weeks":
		sports = Sport.objects.filter(user=request.user)
		data = {'time': [],
				'distance': [],
				'calories': [],
				'count': []}
		
		for sport in sports:
			sport_data = {}
			sport_data['label'] = sport.name
			sport_data['color'] = sport.color
			sport_data['data'] = []
			
			sport_distance = copy.deepcopy(sport_data)
			sport_time = copy.deepcopy(sport_data)
			sport_calories = copy.deepcopy(sport_data)
			sport_count = copy.deepcopy(sport_data)
			
			activities = Activity.objects.filter(sport=sport, user=request.user, event__in=events_filter, sport__in=sports_filter).order_by('date')
			if len(activities)>0:
				activities = activities.filter(date__gte = start_date, date__lte = end_date)
				
				# days ago to last monday
				delta = datetime.timedelta(days = (start_date.timetuple().tm_wday) % 7)
				week_start = timezone.make_aware(datetime.datetime(year=start_date.year, month=start_date.month, day=start_date.day) - delta, timezone.get_default_timezone())

				while week_start < end_date:
					week_activities = activities.filter(date__gte=week_start, date__lt=(week_start+datetime.timedelta(days=7)))
					summary = activities_summary(week_activities)
					sport_time['data'].append([time.mktime(week_start.timetuple())*1000, summary['total_time'] / 60])
					sport_distance['data'].append([time.mktime(week_start.timetuple())*1000, summary['total_distance']])
					sport_calories['data'].append([time.mktime(week_start.timetuple())*1000, summary['total_calories']])
					sport_count['data'].append([time.mktime(week_start.timetuple())*1000, len(week_activities)])

					week_start = week_start + datetime.timedelta(days=7)

				data['calories'].append(sport_calories)
				data['distance'].append(sport_distance)
				data['time'].append(sport_time)
				data['count'].append(sport_count)
			
	return HttpResponse(simplejson.dumps(data))

@login_required
def calendar_get_events(request):
	events = []
	
	start_datetime = datetime.datetime.fromtimestamp(float(request.GET.get('start')))
	end_datetime = datetime.datetime.fromtimestamp(float(request.GET.get('end')))
	start_date = datetime.date.fromtimestamp(float(request.GET.get('start')))
	end_date = datetime.date.fromtimestamp(float(request.GET.get('end')))
	activity_list = Activity.objects.filter(user=request.user).filter(date__gte=str(start_datetime)).filter(date__lt=str(end_datetime))
	desease_list = Desease.objects.filter(user=request.user).filter(end_date__gt=start_date).filter(start_date__lt=end_date)
	weight_list = Weight.objects.filter(user=request.user).filter(date__gt=start_date).filter(date__lt=end_date)
	weightgoal_list = Goal.objects.filter(user=request.user).filter(due_date__gt=start_date).filter(due_date__lt=end_date)
	
	for activity in activity_list:
		if activity.distance:
			events.append({'title': "%s\n%.2fkm\n%s" % (activity.name, activity.distance, str(datetime.timedelta(seconds=activity.time))), 
						'allDay': False, 'start': activity.date.isoformat(), 
						'end': (activity.date + datetime.timedelta(days=0, seconds=activity.time)).isoformat(), 'url': "/activities/%s" % activity.id, 'color': activity.sport.color, 'className': 'fc_activity'})
		else:
			events.append({'title': "%s\n%s" % (activity.name, str(datetime.timedelta(seconds=activity.time))), 
						'allDay': False, 'start': activity.date.isoformat(), 
						'end': (activity.date + datetime.timedelta(days=0, seconds=activity.time)).isoformat(), 'url': "/activities/%s" % activity.id, 'color': activity.sport.color, 'className': 'fc_activity'})

	for weight in weight_list:
		events.append({'title': "%.1f kg" % weight.weight, 'allDay': True, 'start': weight.date.isoformat(), 'className': 'fc_weight'})
	
	for weight in weightgoal_list:
		events.append({'title': "Ziel: %.1f kg" % weight.target_weight, 'allDay': True, 'start': weight.due_date.isoformat(), 'className': 'fc_weightgoal'})
		
	for desease in desease_list:
		events.append({'title': desease.name, 'allDay': True, 'start': desease.start_date.isoformat(), 'end': desease.end_date.isoformat(), 'desease_id': desease.pk, 'color': '#ff0000', 'className': 'fc_desease'})
	
	return HttpResponse(simplejson.dumps(events))

@login_required
def settings(request):
	event_list = Event.objects.filter(user=request.user)
	equipment_list = Equipment.objects.filter(user=request.user).filter(archived=False)
	equipment_archived_list = Equipment.objects.filter(user=request.user).filter(archived=True)
	sport_list = Sport.objects.filter(user=request.user)
	calformula_list = CalorieFormula.objects.filter(user=request.user) | CalorieFormula.objects.filter(public=True).order_by('public', 'name')
	
	for equipment in equipment_list:
		print equipment
		equipment.time = 0
		activity_distance = Activity.objects.filter(user=request.user, equipment=equipment).aggregate(Sum('distance'))
		activity_time = Activity.objects.filter(user=request.user, equipment=equipment).aggregate(Sum('time'))
		try:
			equipment.distance = equipment.distance + activity_distance['distance__sum']
		except TypeError, exc:
			logging.exception("Exception occured in settings")

		try:
			equipment.time = equipment.time + activity_time['time__sum']
		except TypeError, exc:
			logging.exception("Exception occured in settings")

		if activity_time > 0:
			equipment.speed = round(float(activity_distance['distance__sum']) * 3600.0 / activity_time['time__sum'], 2)
		else:
			equipment.speed = "-"

		equipment.time = seconds_to_time(equipment.time, force_hour=True)
		
	
	return render_to_response('activities/settings.html', {'calformula_list': calformula_list, 'event_list': event_list, 'equipment_list': equipment_list, 'equipment_archived_list': equipment_archived_list, 'sport_list': sport_list, 'username': request.user})
	
def importtrack(request, newtrack):
	"""
	Process garmin tcx file import
	"""
	logging.debug("importtrack calles with request %r" % request)

	xmlns = "{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}"
	# create additional gpx file from track
	logging.debug("Calling tcx2gpx.convert with track object %s" % newtrack)
	tcx2gpx.convert(newtrack)

	newtrack.trackfile.open()
	xmltree = ElementTree(file = newtrack.trackfile)
	newtrack.trackfile.close()
	
	# take only first activity from file
	xmlactivity = xmltree.find(xmlns + "Activities")[0]

	# create new activity from file
	# Event/sport is only dummy for now, make selection after import
	events = Event.objects.filter(user=request.user) #FIXME: there must always be a event and sport definied
	sports = Sport.objects.filter(user=request.user)

	if events is None or len(events)==0:
		raise RuntimeError("There must be a event type defined. Please define one first.")
	if sports is None or len(sports)==0:
		raise RuntimeError("There must be a sport type defined. Please define one first.")

	event = events[0]
	sport = sports[0]
	
	activity = Activity(name="")
	activity.user = request.user
	activity.event = event
	activity.sport = sport
	activity.track = newtrack
	
	laps = []
	for xmllap in xmlactivity.findall(xmlns + "Lap"):
		date = dateutil.parser.parse(xmllap.get("StartTime"))
		time = int(float(xmllap.find(xmlns+"TotalTimeSeconds").text))
		distance = str(float(xmllap.find(xmlns+"DistanceMeters").text)/1000)
		if xmllap.find(xmlns+"MaximumSpeed") is None:
			logging.debug("MaximumSpeed is None")
		logging.debug("MaximumSpeed xml is %r" % xmllap.find(xmlns+"MaximumSpeed"))
		speed_max = str(float(xmllap.find(xmlns+"MaximumSpeed").text)*3.6)	# Given as meters per second in tcx file
		logging.debug("speed_max is %s" % speed_max)
		calories = int(xmllap.find(xmlns+"Calories").text)
		try:
			hf_avg = int(xmllap.find(xmlns+"AverageHeartRateBpm").find(xmlns+"Value").text)
			logging.debug("Found hf_avg: %s" % hf_avg)
		except AttributeError:
			hf_avg = None
			logging.debug("Not found hf_avg")
		try:
			hf_max = int(xmllap.find(xmlns+"MaximumHeartRateBpm").find(xmlns+"Value").text)
			logging.debug("Found hf_max: %s" % hf_max)
		except AttributeError:
			hf_max = None
			logging.debug("Not found hf_max")
		try:
			cadence_avg = int(xmllap.find(xmlns+"Cadence").text)
			logging.debug("Found average cadence: %s" % cadence_avg)
		except AttributeError:
			cadence_avg = None
			logging.debug("Not found average cadence")

		if time != 0:
			speed_avg = str(float(distance)*3600 / time)
		else:
			speed_avg = None
		
		cadence_max = 0
		elev_min = 65535
		elev_max = 0
		elev_gain = 0
		elev_loss = 0
		last_elev = None
		
		for xmltrack in xmllap.findall(xmlns + "Track"):
			for xmltp in xmltrack.findall(xmlns + "Trackpoint"):
				if xmltp.find(xmlns + "AltitudeMeters") != None:
					elev = int(round(float(xmltp.find(xmlns + "AltitudeMeters").text)))
				else:
					elev = last_elev
				
				if elev != last_elev:
					if elev > elev_max:
						elev_max = elev
					if elev < elev_min:
						elev_min = elev
					
					if last_elev:
						if elev > last_elev:
							elev_gain = elev_gain + (elev - last_elev)
						else:
							elev_loss = elev_loss + (last_elev - elev)
					last_elev = elev
				
				if xmltp.find(xmlns + "Cadence") != None:
					cadence = int(xmltp.find(xmlns + "Cadence").text)
					if cadence > cadence_max:
						cadence_max = cadence
		
		lap = Lap(
				date = date,
				time = time,
				distance = distance,
				elevation_gain = elev_gain,
				elevation_loss = elev_loss,
				elevation_min = elev_min,
				elevation_max = elev_max,
				speed_max = speed_max,
				speed_avg = speed_avg,
				cadence_avg = cadence_avg,
				cadence_max = cadence_max,
				calories = calories,
				hf_max = hf_max,
				hf_avg = hf_avg)

		laps.append(lap)

	cadence_avg = 0
	cadence_max = 0
	calories_sum = 0
	distance_sum = 0
	elev_min = 65535
	elev_max = 0
	elev_gain = 0
	elev_loss = 0
	hf_avg = 0
	hf_max = 0
	speed_max = 0
	time_sum = 0
	for lap in laps:
		calories_sum = calories_sum + lap.calories
		distance_sum = distance_sum + float(lap.distance)
		time_sum = time_sum + lap.time
		
		if lap.elevation_max > elev_max:
			elev_max = lap.elevation_max
		if lap.elevation_min < elev_min:
			elev_min = lap.elevation_min
		elev_gain = elev_gain + lap.elevation_gain
		elev_loss = elev_loss + lap.elevation_loss
		
		if lap.hf_max > hf_max:
			hf_max = lap.hf_max
			logging.debug("New global hf_max: %s" % hf_max)
		if float(lap.speed_max) > speed_max:
			speed_max = float(lap.speed_max)
			logging.debug("New global speed_max: %s" % speed_max)
		
		if lap.cadence_max > cadence_max:
			cadence_max = lap.cadence_max
		
		if lap.cadence_avg:
			cadence_avg = cadence_avg + lap.time * lap.cadence_avg
		if lap.hf_avg:
			hf_avg = hf_avg + lap.time * lap.hf_avg
		
		print hf_avg
		print cadence_avg
		
	activity.cadence_avg = int(cadence_avg / time_sum)
	activity.cadence_max = cadence_max
	activity.calories = calories_sum
	activity.speed_max = str(speed_max)
	activity.hf_avg = int(hf_avg / time_sum)
	activity.hf_max = hf_max
	activity.distance = str(distance_sum)
	activity.elevation_min = elev_min
	activity.elevation_max = elev_max
	activity.elevation_gain = elev_gain
	activity.elevation_loss = elev_loss
	activity.time = time_sum
	activity.date = laps[0].date
	activity.speed_avg = str(float(activity.distance) * 3600 / activity.time)
	activity.save()

	for lap in laps:
		lap.activity = activity
		lap.save()
	
	# generate preview image for track
	create_preview(activity.track)

	return activity

def create_preview(track):
	logging.debug("Creating preview image for track")
	if track:
		tcxtrack = TCXTrack(track)

		pos_list = tcxtrack.get_pos(100)
		gmap_coords = []
		for (lat, lon) in pos_list:
			gmap_coords.append("%s,%s" % (round(lat, 3), round(lon, 3)))
		gmap_path = "|".join(gmap_coords)
		
		url = "http://maps.google.com/maps/api/staticmap?size=480x480&path=color:0xff0000ff|"+gmap_path+"&sensor=true"
		logging.debug("Fetching file from %s" % url)
		try:
			img_temp = NamedTemporaryFile(delete=True)
			img_temp.write(urllib2.urlopen(url).read())
			img_temp.flush()
			name=os.path.splitext(os.path.split(track.trackfile.name)[1])[0]
			logging.debug("Saving as %s.jpg" % name)
			
			track.preview_img.save("%s.jpg" % name, File(img_temp), save=True)
		except urllib2.URLError, exc:
			logging.error("Exception occured when creating preview image: %s" % exc)
