#!/usr/bin/env python


# Create your views here.
from base64 import b64decode
import json
import copy
import datetime
import itertools
import json
import os
import tempfile
import time
import traceback
import logging

from activities.models import Activity, ActivityTemplate, CalorieFormula, Equipment, Event, Sport, Track, Lap
from activities.forms import EquipmentForm
import activities.forms
from activities.utils import activities_summary, int_or_none, str_float_or_none, pace_to_speed, speed_to_pace, seconds_to_time
from activities.extras.activityfile import ActivityFile
from activities.django_datatables_view.base_datatable_view import BaseDatatableView

from health.models import Desease, Weight, Goal

from django.http import Http404, HttpResponseForbidden, HttpResponseRedirect, HttpResponse, HttpResponseBadRequest
from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core import serializers
from django.db.models import Sum
from django.core.files.base import File
from django.conf import settings as django_settings


@login_required
def add_calformula(request):
	if request.method == 'POST':
		if 'update_id' in request.POST:
			calformula = CalorieFormula.objects.get(pk=int(request.POST.get('update_id')))
			# If selected_by_id object does not belong to current user, create new activity
			if calformula.user != request.user:
				calformula = CalorieFormula(user=request.user)
		else:
			calformula = CalorieFormula(user=request.user)

		calformula.name = request.POST.get('name')
		calformula.weight_dist_factor = request.POST.get('weight_dist_factor')
		calformula.weight_time_factor = request.POST.get('weight_time_factor')
		calformula.save()
		return HttpResponse(json.dumps((True, )))
	else:
		return HttpResponseBadRequest


@login_required
def delete_calformula(request):
	if request.method == 'POST':
		calformula = CalorieFormula.objects.get(pk=int(request.POST.get('id')))
		if calformula.user == request.user:
			calformula.delete()
			return HttpResponse(json.dumps((True, )))
		else:
			return HttpResponse(json.dumps((False, "Permission denied")))


@login_required
def get_calformula(request):

	calformula = CalorieFormula.objects.get(pk=int(request.GET.get('id')))
	if calformula.user == request.user or calformula.public:
		return HttpResponse(serializers.serialize('json', [calformula]), content_type='application/json')
	else:
		return HttpResponseForbidden()


@login_required
def add_sport(request):
	if request.method == 'POST':
		if 'update_id' in request.POST:
			sport = Sport.objects.get(pk=int(request.POST.get('update_id')))
			# If selected_by_id activity does not belong to current user, create new activity
			if sport.user != request.user:
				sport = Sport(user=request.user)
		else:
			sport = Sport(user=request.user)

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
		return HttpResponse(json.dumps((True, )))
	else:
		return HttpResponseBadRequest


@login_required
def get_sport(request):
	sport_id = request.GET.get('id')

	sport = Sport.objects.get(pk=int(sport_id))
	if sport.user == request.user:
		return HttpResponse(serializers.serialize('json', [sport]), content_type='application/json')
	else:
		return HttpResponseForbidden()


@login_required
def delete_sport(request):
	if request.method == 'POST':
		try:
			sport = Sport.objects.get(id=int(request.POST.get('id')))
		except Sport.DoesNotExist:
			return HttpResponse(json.dumps((False, 'DoesNotExist')))
		if sport.user == request.user:
			sport.delete()
			return HttpResponse(json.dumps((True, )))
		else:
			return HttpResponse(json.dumps((False, "Permission denied")))


@login_required
def add_event(request):
	if request.method == 'POST':
		if 'update_id' in request.POST:
			event = Event.objects.get(pk=int(request.POST.get('update_id')))
			# If selected_by_id activity does not belong to current user, create new activity
			if event.user != request.user:
				event = Event(user=request.user)
		else:
			event = Event(user=request.user)

		event.name = request.POST.get('name')
		event.save()
		return HttpResponse(json.dumps((True, )))
	else:
		return HttpResponseBadRequest


@login_required
def get_event(request):
	event_id = request.GET.get('id')

	event = Event.objects.get(pk=int(event_id))
	if event.user == request.user:
		return HttpResponse(serializers.serialize('json', [event]), content_type='application/json')
	else:
		return HttpResponseForbidden()


def delete_event(request):
	if request.method == 'POST':
		event = Event.objects.get(id=int(request.POST.get('id')))
		if event.user == request.user:
			event.delete()
			return HttpResponse(json.dumps((True, )))
		else:
			return HttpResponse(json.dumps((False, "Permission denied")))


@login_required
def add_equipment(request):
	if request.method == 'POST':
		if 'update_id' in request.POST:
			equipment = Equipment.objects.get(pk=int(request.POST.get('update_id')))
			# If selected_by_id activity does not belong to current user, create new activity
			if equipment.user != request.user:
				equipment = Equipment(user=request.user)
		else:
			equipment = Equipment(user=request.user)

		equipment.name = request.POST.get('name')
		equipment.description = request.POST.get('description')

		if request.POST.get('distance') != "":
			equipment.distance = request.POST.get('distance')

		if request.POST.get('archived') == '0':
			equipment.archived = False
		else:
			equipment.archived = True

		equipment.save()
		return HttpResponse(json.dumps((True, )))
	else:
		return HttpResponseBadRequest


@login_required
def get_equipment(request):
	equipment_id = request.GET.get('id')

	equipment = Equipment.objects.get(pk=int(equipment_id))
	if equipment.user == request.user:
		return HttpResponse(serializers.serialize('json', [equipment]), content_type='application/json')
	else:
		return HttpResponseForbidden()


def delete_equipment(request):
	if request.method == 'POST':
		equipment = Equipment.objects.get(id=int(request.POST.get('id')))
		if equipment.user == request.user:
			equipment.delete()
			return HttpResponse(json.dumps((True, )))
		else:
			return HttpResponse(json.dumps((False, "Permission denied")))


@login_required
def list_event(request):
	return render_to_response('activities/event_list.html', {})


@login_required
def get_events(request):
	event_list = Event.objects.filter(user=request.user)
	return HttpResponse(serializers.serialize('json', event_list), content_type='application/json')


@login_required
def create_equipment(request):
	form = EquipmentForm()
	if request.method == 'POST':
		form = EquipmentForm(request.POST)
		if form.is_valid():
			equ = form.save(commit=False)
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
		is_saved = False
		newtrack = None
		if len(request.FILES) > 0:
			# This is a direct manual file upload
			logging.debug("Creating activity from file upload")
			try:
				newtrack = Track(trackfile=request.FILES['trackfile'])
				newtrack.save()
				filename, fileextension = os.path.splitext(newtrack.trackfile.path)
				newtrack.filetype = fileextension.lower()[1:]
				activityfile = ActivityFile.ActivityFile(newtrack, request)
				newtrack.save()
				is_saved = True
				activityfile.import_activity()
				activity = activityfile.get_activity()
				activity.save()
			except Exception as msg:
				logging.error("Exception occured in import with message %s" % msg)
				raise
				if is_saved:
					newtrack.delete()
				for line in traceback.format_exc().splitlines():
					logging.error(line.strip())
				return HttpResponse(json.dumps({'success': False, 'msg': str(msg)}))
			else:
				return HttpResponseRedirect('/activities/%i/?edit=1' % activity.pk)
		elif 'content' in request.POST:
			# This is a Garmin Communicator plugin upload
			logging.debug("Creating activity from text upload")
			try:
				content = request.POST['content']
				newtrack = Track()
				tmpfile = tempfile.NamedTemporaryFile(mode="w", delete=False)

				if content.splitlines()[0].startswith("<?xml"):
					filename = "%s.tcx" % datetime.datetime.now().strftime("%d.%m.%y %H-%M-%S")
					newtrack.filetype = "tcx"
					tmpfilename = tmpfile.name

					tmpfile.write(content)

					# create new trackfile
				elif ".fit" in content.splitlines()[0].lower():
					filename = "%s.fit" % datetime.datetime.now().strftime("%d.%m.%y %H-%M-%S")
					newtrack.filetype = "fit"
					tmpfilename = tmpfile.name

					for line in content.splitlines()[1:]:
						tmpfile.write(b64decode(line))
				else:
					raise RuntimeError("Received unknown filetype from garmin communicator plugin")
				tmpfile.close()

				newtrack.trackfile.save(filename, File(open(tmpfilename, 'r')))
				is_saved = True
				logging.debug("Filename: %s" % filename)

				activityfile = ActivityFile.ActivityFile(newtrack, request)
				activityfile.import_activity()
				activity = activityfile.get_activity()
				activity.save()
				tmpfile.close()
				os.remove(tmpfilename)
				return HttpResponse(json.dumps({'success': True, 'redirect_to': '/activities/%i/?edit=1' % activity.pk}))
			except Exception, exc:
				logging.error("Exception raised in importtrack: %s" % str(exc))
				if is_saved:
					newtrack.delete()
				for line in traceback.format_exc().splitlines():
					logging.error(line.strip())
				return HttpResponse(json.dumps({'success': False, 'msg': str(exc)}))

		else:
			logging.error("Missing upload data")
	else:
		# render list of activities

		# collect data required for activity form
		events = Event.objects.filter(user=request.user)
		equipments = Equipment.objects.filter(user=request.user).filter(archived=False)
		sports = Sport.objects.filter(user=request.user)
		calformulas = CalorieFormula.objects.filter(user=request.user) | CalorieFormula.objects.filter(public=True).order_by('public', 'name')
		activitytemplates = ActivityTemplate.objects.filter(user=request.user)

		# get list of activities
		# activities = Activity.objects.select_related('sport').filter(user=request.user)

		try:
			garmin_keys = django_settings.GARMIN_KEYS
		except AttributeError:
			garmin_keys = False

		weight = Weight.objects.filter(user=request.user).order_by('-date')
		if len(weight) > 0:
			weight = weight[0]
		else:
			weight = None

		return render_to_response('activities/activity_list.html', {'username': request.user, 'equipments': equipments, 'events': events, 'sports': sports, 'calformulas': calformulas, 'weight': weight, 'activitytemplates': activitytemplates, 'garmin_keys': garmin_keys})


@login_required
def get_activity(request):
	act_id = request.GET.get('id')
	template = request.GET.get('template')

	if template == 'true':
		activity = ActivityTemplate.objects.get(pk=int(act_id))
	else:
		activity = Activity.objects.select_related('track').get(pk=int(act_id))

	if activity.user == request.user:
		data = serializers.serialize('json', [activity])
		result = {"activity": data}

		if activity.track and activity.track.preview_img:
			# build absolute URL with domain part for preview image
			# https seems not to be supported by facebook
			result['preview_img'] = activity.track.preview_img.url

		return HttpResponse(json.dumps(result), content_type='application/json')
	else:
		return HttpResponseForbidden()


@login_required
def delete_activity(request):
	if request.method == 'POST':
		act_id = int_or_none(request.POST.get('id'))
		tmpl_id = int_or_none(request.POST.get('tmpl_id'))

		if act_id:
			try:
				act = Activity.objects.get(id=act_id)
			except Activity.DoesNotExist:
				return HttpResponse(json.dumps({'success': False, 'msg': 'DoesNotExist'}))
		elif tmpl_id:
			try:
				act = ActivityTemplate.objects.get(id=tmpl_id)
			except ActivityTemplate.DoesNotExist:
				return HttpResponse(json.dumps({'success': False, 'msg': 'DoesNotExist'}))
		else:
			return HttpResponse(json.dumps({'success': False, 'msg': "Missing ID"}))

		if act.user == request.user:
			act.delete()
			return HttpResponse(json.dumps({'success': True}))
		else:
			return HttpResponse(json.dumps({'success': False, 'msg': "Permission denied"}))


@login_required
def add_activity(request):
	if request.method == 'POST':
		logging.debug("In add_activity post request with parameters %s" % repr(request.POST.items()))
		is_template = request.POST.get('is_template')
		if is_template == 'true':
			if 'update_id' in request.POST:
				act = ActivityTemplate.objects.get(pk=int(request.POST.get('update_id')))
				# If selected_by_id activityTemplate does not belong to current user, create new activityTemplate
				if act.user != request.user:
					act = ActivityTemplate(user=request.user)
			else:
				act = ActivityTemplate(user=request.user)
		else:
			if 'update_id' in request.POST:
				act = Activity.objects.get(pk=int(request.POST.get('update_id')))
				# If selected_by_id activity does not belong to current user, create new activity
				if act.user != request.user:
					act = Activity(user=request.user)
			else:
				act = Activity(user=request.user)

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
				if request.POST.get('speed_max') != u'':
					act.speed_max = str(pace_to_speed(request.POST.get('speed_max')))
				if request.POST.get('speed_avg') != u'':
					act.speed_avg = str(pace_to_speed(request.POST.get('speed_avg')))
				if request.POST.get('speed_avg_movement') != u'':
					act.speed_avg_movement = str(pace_to_speed(request.POST.get('speed_avg_movement')))
			else:
				if request.POST.get('speed_max') != u'':
					act.speed_max = str_float_or_none(request.POST.get('speed_max'))
				if request.POST.get('speed_avg') != u'':
					act.speed_avg = str_float_or_none(request.POST.get('speed_avg'))
				if request.POST.get('speed_avg_movement') != u'':
					act.speed_avg_movement = str_float_or_none(request.POST.get('speed_avg_movement'))

			equipment_list = request.POST.get('equipment').split(" ")

			datestring = request.POST.get('date') + " " + request.POST.get('datetime')
			try:
				date = datetime.datetime.strptime(datestring, "%d.%m.%Y %H:%M")
			except ValueError:
				try:
					date = datetime.datetime.strptime(datestring, "%d.%m.%Y %H:%M:%S")
				except ValueError:
					try:
						date = datetime.datetime.strptime(datestring, "%Y-%m-%d %H:%M")
					except ValueError:
						if request.POST.get('is_template'):
							date = None
						else:
							return HttpResponse(json.dumps(dict(success=False, msg="Fehler aufgetreten: Ungueltiges Datum %s" % str(datestring))))

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

			act.weather_stationname = request.POST.get('weather_stationname')
			act.weather_temp = str_float_or_none(request.POST.get('weather_temp'))
			act.weather_rain = str_float_or_none(request.POST.get('weather_rain'))
			act.weather_hum = int_or_none(request.POST.get('weather_hum'))
			act.weather_windspeed = str_float_or_none(request.POST.get('weather_windspeed'))
			act.weather_winddir = request.POST.get('weather_winddir')
			if act.weather_winddir == "":
				act.weather_winddir = None
			logging.debug("Saving weather data as stationname: %s, temp: %s, rain: %s, hum: %s, windspeed: %s, winddir: %s" % (act.weather_stationname, act.weather_temp, act.weather_rain, act.weather_hum, act.weather_windspeed, act.weather_winddir))

		except Exception, exc:
			logging.exception("Exception occured in add_activits")
			return HttpResponse(json.dumps({'success': False, 'msg': "Fehler aufgetreten: %s" % str(exc)}))

		act.save()

		eq_list = [Equipment.objects.get(pk=int(eq)) for eq in equipment_list if eq]
		act.equipment = eq_list

		act.save()
		return HttpResponse(json.dumps({'success': True}))
	else:
		return HttpResponseBadRequest


def detail(request, activity_id):
	param = request.GET.get('p', False)
	act = get_object_or_404(Activity, id=activity_id)

	if request.user.is_authenticated():
		if act.user == request.user:
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

	if not param:
		# no parameter given, reply with activity detail template

		if act.sport.speed_as_pace:
			if act.speed_max:
				act.speed_max = speed_to_pace(act.speed_max)
			if act.speed_avg:
				act.speed_avg = speed_to_pace(act.speed_avg)
			if act.speed_avg_movement:
				act.speed_avg_movement = speed_to_pace(act.speed_avg_movement)
			speed_unit = "min/km"
		else:
			speed_unit = "km/h"

		if act.track:
			trackfile = act.track.trackfile

			if os.path.isfile(trackfile.path + ".gpx"):
				gpx_url = trackfile.url + ".gpx"
			else:
				gpx_url = None

			# check if preview image is missing
			if not act.track.preview_img:
				logging.debug("No preview image found")
				actfile = ActivityFile.ActivityFile(act.track, request)
				actfile.create_preview()

			# build absolute URL with domain part for preview image
			# https seems not to be supported by facebook
			if act.track.preview_img:
				preview_img = request.build_absolute_uri(act.track.preview_img.url).replace("https://", "http://")
			else:
				preview_img = None

			plots = [
				{"name": "hf", "dataname": "hf", "label": "HF", "label_short": "HF", "color": "#FF0000", "rounding": 0, "unit": "/ Minute", "unit_short": "/ min."},
				{"name": "speed", "dataname": "speed", "label": "Geschwindigkeit", "label_short": "Geschw.", "color": "#0070A3", "rounding": 1, "unit": speed_unit, "unit_short": speed_unit},
				{"name": "alt", "dataname": "altitude", "label": "Hoehe", "label_short": "Hoehe", "color": "#00FF00", "rounding": 0, "unit": "m", "unit_short": "m"},
				{"name": "cad", "dataname": "cadence", "label": "Trittfrequenz", "label_short": "Trittfreq.", "color": "#FFBF00", "rounding": 0, "unit": "/ Minute", "unit_short": "/ min."},
				{"name": "stance_time", "dataname": "stance_time", "label": "Bodenkontaktzeit", "label_short": "Bodenkontaktzeit", "color": "rgb(152, 117, 178)", "rounding": 0, "unit": "Millisekunden", "unit_short": "ms"},
				{"name": "vertical_oscillation", "dataname": "vertical_oscillation", "label": "Vertikale Bewegung", "label_short": "Vert. Bewegung", "color": "rgb(152, 117, 178)", "rounding": 0, "unit": "mm", "unit_short": "mm"},
				{"name": "temperature", "dataname": "temperature", "label": "Temperatur", "label_short": "Temperatur", "color": "#FFBF00", "rounding": 1, "unit": "C", "unit_short": "C"}
			]

		else:
			trackfile = None
			gpx_url = None
			preview_img = None
			plots = []

		act.time = seconds_to_time(act.time, force_hour=True)
		if act.time_movement:
			act.time_movement = seconds_to_time(act.time_movement)
		if act.time_elapsed:
			act.time_elapsed = seconds_to_time(act.time_elapsed)

		laps = Lap.objects.filter(activity=act).order_by('id')
		for lap in laps:
			lap.time = seconds_to_time(lap.time)
			if act.sport.speed_as_pace:
				if lap.speed_max:
					lap.speed_max = speed_to_pace(lap.speed_max)
				if lap.speed_avg:
					lap.speed_avg = speed_to_pace(lap.speed_avg)

		if not public:
			if request.GET.get('edit', '0') == '1':
				edit = 1
			else:
				edit = 0

			events = Event.objects.filter(user=request.user)
			equipments = Equipment.objects.filter(user=request.user).filter(archived=False)
			sports = Sport.objects.filter(user=request.user)
			calformulas = CalorieFormula.objects.filter(user=request.user) | CalorieFormula.objects.filter(public=True).order_by('public', 'name')
			activitytemplates = ActivityTemplate.objects.filter(user=request.user)
			weight = Weight.objects.filter(user=request.user).order_by('-date')
			if len(weight) > 0:
				weight = weight[0]
			else:
				weight = None

			return render_to_response('activities/detail.html', {'activity': act, 'username': request.user, 'speed_unit': speed_unit, 'equipments': equipments, 'events': events, 'sports': sports, 'calformulas': calformulas, 'activitytemplates': activitytemplates, 'weight': weight, 'laps': laps, 'edit': edit, 'tcx': trackfile, 'gpx_url': gpx_url, 'public': public, 'full_url': request.build_absolute_uri(), 'preview_img': preview_img, 'fb_app_id': fb_app_id, 'plots': plots})
		else:
			return render_to_response('activities/detail.html', {'activity': act, 'speed_unit': speed_unit, 'laps': laps, 'tcx': trackfile, 'gpx_url': gpx_url, 'public': public, 'plots': plots})
	if param == 'plots':
		if act.track:
			track = ActivityFile.ActivityFile(act.track)

			data = {'altitude': track.get_alt(),
					'cadence': track.get_cad(),
					'hf': track.get_hf(),
					'pos': track.get_pos(),
					'speed': track.get_speed(act.sport.speed_as_pace),
					'speed_foot': track.get_speed_foot(act.sport.speed_as_pace),
					'stance_time': track.get_stance_time(),
					'vertical_oscillation': track.get_vertical_oscillation(),
					'temperature': track.get_temperature()}

			details_data = track.get_detail_entries()

			return HttpResponse(json.dumps({"plot_data": data, "details_data": details_data}, sort_keys=True, indent=4), content_type="text/plain")

	# last resort
	return Http404()


@login_required
def calendar(request):
	events = Event.objects.filter(user=request.user)
	equipments = Equipment.objects.filter(user=request.user).filter(archived=False)
	sports = Sport.objects.filter(user=request.user)
	calformulas = CalorieFormula.objects.filter(user=request.user) | CalorieFormula.objects.filter(public=True).order_by('public', 'name')
	weight = Weight.objects.filter(user=request.user).order_by('-date')
	activitytemplates = ActivityTemplate.objects.filter(user=request.user)

	if len(weight) > 0:
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
		start_date = timezone.make_aware(timezone.datetime.utcfromtimestamp(int(startdate_timestamp) / 1000), timezone.get_default_timezone())
		end_date = timezone.make_aware(timezone.datetime.utcfromtimestamp(int(enddate_timestamp) / 1000), timezone.get_default_timezone()).replace(hour=23, minute=59, second=59)
		# make shure we include the current day
		logging.debug("Time range is from %s (%s) to %s (%s)" % (start_date, startdate_timestamp, end_date, enddate_timestamp))
	except ValueError:
		return HttpResponse(json.dumps((False, "Invalid timestamps")))

	logging.debug("Filter activities between %s and %s" % (start_date, end_date))
	events_filter = []
	for event_pk in event_pks:
		events_filter.append(Event.objects.get(pk=int(event_pk)))
	sports_filter = []
	for sport_pk in sport_pks:
		sports_filter.append(Sport.objects.get(pk=int(sport_pk)))

	if mode == "sports":
		sports = Sport.objects.filter(user=request.user)
		for sport in sports:
			activities = Activity.objects.filter(sport=sport, user=request.user, event__in=events_filter, sport__in=sports_filter)
			activities = activities.filter(date__gte=start_date, date__lte=end_date)

			data[sport.name] = activities_summary(activities)
			data[sport.name]['color'] = sport.color

	elif mode == "weeks":
		sports = Sport.objects.filter(user=request.user)
		data = {'time': [],
				'distance': [],
				'calories': [],
				'count': []}

		for sport in sports:
			sport_data = {'label': sport.name, 'color': sport.color, 'data': []}

			sport_distance = copy.deepcopy(sport_data)
			sport_time = copy.deepcopy(sport_data)
			sport_calories = copy.deepcopy(sport_data)
			sport_count = copy.deepcopy(sport_data)

			activities = Activity.objects.filter(sport=sport, user=request.user, event__in=events_filter, sport__in=sports_filter).order_by('date')
			if len(activities) > 0:
				activities = activities.filter(date__gte=start_date, date__lte=end_date)

				# days ago to last monday
				delta = datetime.timedelta(days=start_date.timetuple().tm_wday % 7)
				week_start = timezone.make_aware(datetime.datetime(year=start_date.year, month=start_date.month, day=start_date.day) - delta, timezone.get_default_timezone())

				while week_start <= end_date:
					week_activities = activities.filter(date__gte=week_start, date__lt=(week_start + datetime.timedelta(days=7)))
					summary = activities_summary(week_activities)
					sport_time['data'].append([time.mktime(week_start.timetuple()) * 1000, summary['total_time'] / 60])
					sport_distance['data'].append([time.mktime(week_start.timetuple()) * 1000, summary['total_distance']])
					sport_calories['data'].append([time.mktime(week_start.timetuple()) * 1000, summary['total_calories']])
					sport_count['data'].append([time.mktime(week_start.timetuple()) * 1000, len(week_activities)])

					week_start = week_start + datetime.timedelta(days=7)

				data['calories'].append(sport_calories)
				data['distance'].append(sport_distance)
				data['time'].append(sport_time)
				data['count'].append(sport_count)

	return HttpResponse(json.dumps(data))


@login_required
def calendar_get_events(request):
	events = []
	summary = {}

	start_datetime = timezone.make_aware(datetime.datetime.fromtimestamp(float(request.GET.get('start'))), timezone.get_default_timezone())
	end_datetime = timezone.make_aware(datetime.datetime.fromtimestamp(float(request.GET.get('end'))), timezone.get_default_timezone())
	start_date = datetime.date.fromtimestamp(float(request.GET.get('start')))
	end_date = datetime.date.fromtimestamp(float(request.GET.get('end')))
	sportlist = request.GET.get('sports')
	sports = json.loads(sportlist)
	sports = [int(sport) for sport in sports]

	activity_list = Activity.objects.select_related('sport').filter(user=request.user).filter(date__gte=str(start_datetime)).filter(date__lt=str(end_datetime)).filter(sport__in=sports)
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

	for activity in activity_list:
		week = activity.date.isocalendar()[1]
		if week not in summary:
			summary[week] = {'distance': 0, 'calories': 0, 'time': 0}
		if activity.distance:
			summary[week]['distance'] += activity.distance
		if activity.calories:
			summary[week]['calories'] += activity.calories
		summary[week]['time'] += activity.time
		summary[week]['date'] = activity.date

	for week in summary:
		events.append({'title': "Distanz:\n%s km\n\nZeit\n%s\n\nKalorien\n%s kcal" %
			(summary[week]['distance'], str(datetime.timedelta(seconds=summary[week]['time'])), summary[week]['calories']),
			'allDay': True, 'type': 'week_summary', 'start': summary[week]['date'].isoformat(), 'end': summary[week]['date'].isoformat(),
			'className': 'fc-event-weeksummary'})

	return HttpResponse(json.dumps(events))


@login_required
def settings(request):
	events = Event.objects.filter(user=request.user)
	equipments = Equipment.objects.filter(user=request.user).filter(archived=False)
	equipments_archived = Equipment.objects.filter(user=request.user).filter(archived=True)
	sports = Sport.objects.filter(user=request.user)
	calformulas = CalorieFormula.objects.filter(user=request.user) | CalorieFormula.objects.filter(public=True).order_by('public', 'name')
	activitytemplates = ActivityTemplate.objects.filter(user=request.user)

	event_form = activities.forms.EventForm()
	equipment_form = activities.forms.EquipmentForm()

	for equipment in itertools.chain(equipments, equipments_archived):
		equipment.time = 0
		activity_distance = Activity.objects.filter(user=request.user, equipment=equipment).aggregate(Sum('distance'))
		activity_time = Activity.objects.filter(user=request.user, equipment=equipment).aggregate(Sum('time'))
		try:
			if activity_distance['distance__sum']:
				equipment.distance = equipment.distance + activity_distance['distance__sum']
		except TypeError, exc:
			logging.exception("Exception occured in settings: %s" % exc)

		try:
			if activity_time['time__sum']:
				equipment.time = equipment.time + activity_time['time__sum']
		except TypeError, exc:
			logging.exception("Exception occured in settings: %s" % exc)
			equipment.time = 0

		if activity_time > 0 and activity_distance['distance__sum']:
			logging.debug("Distance: %s" % activity_distance['distance__sum'])
			equipment.speed = str(float(activity_distance['distance__sum']) * 3600.0 / activity_time['time__sum'])
		else:
			equipment.speed = ""

		equipment.distance = str(equipment.distance)

	return render_to_response('activities/settings.html', {'activitytemplates': activitytemplates, 'calformulas': calformulas, 'events': events, 'equipments': equipments, 'equipments_archived': equipments_archived, 'sports': sports, 'username': request.user, 'event_form': event_form, 'equipment_form': equipment_form})


class ActivityListJson(BaseDatatableView):
	# define column names that will be used in sorting
	# order is important and should be same as order of columns
	# displayed by datatables. For non sortable columns use empty
	# value like ''
	columns = ['name', 'sport', 'date', 'time']
	order_columns = ['name', 'sport', 'date', 'time']

	# set max limit of records returned, this is used to protect our site if someone tries to attack our site
	# and make it return huge amount of data
	max_display_length = 500

	def get_initial_queryset(self):
		# return queryset used as base for futher sorting/filtering
		# these are simply objects displayed in datatable
		logging.debug("self.request.user")
		return Activity.objects.select_related('sport').filter(user=self.request.user)

	def filter_queryset(self, qs):
		# use request parameters to filter queryset

		# simple example:
		search = self.request.GET.get(u'search[value]', None)
		if search:
			qs = qs.filter(name__icontains=search)

		return qs

	def prepare_results(self, qs):
		# prepare list with output column data
		# queryset is already paginated here
		json_data = []
		for item in qs:
			# if self.request.is_mobile:
			# 	json_data.append(['<a href="/activities/%s/" data-ajax="false">%s</a>' % (item.id, item.name), item.date.isoformat(), item.time])
			# else:
			# 	json_data.append(['<a class="activityPopupTrigger" href="/activities/%s/" rel="%s" title="%s">%s</a>&nbsp;&nbsp;&nbsp;<img src="/media/img/edit-icon.png" alt="Bearbeiten" onclick="showActivityDialog(%s)"/><img src="/media/img/delete-icon.png" alt="L&ouml;schen" onclick="showActivityDeleteDialog(%s)"/>' % (item.id, item.id, item.name, item.name, item.id, item.id), item.sport.name, item.date.isoformat(), item.time])
			json_data.append(['<a class="activityPopupTrigger" href="/activities/%s/" rel="%s" title="%s">%s</a>&nbsp;&nbsp;&nbsp;<i class="material-icons" onclick="showActivityDialog(%s)">mode_edit</i><i class="material-icons" onclick="showActivityDeleteDialog(%s, \'%s\')">delete</i>' % (item.id, item.id, item.name, item.name, item.id, item.id, item.name), item.sport.name, item.date.isoformat(), item.time])

		return json_data
