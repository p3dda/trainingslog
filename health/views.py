import time
import datetime
import logging

from collections import  namedtuple

from django.http import HttpResponseForbidden, HttpResponse, HttpResponseBadRequest

from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.utils import simplejson
from django.core import serializers

from health.models import Desease, Weight, Goal, Pulse
from health.utils import parsefloat


@login_required
def show_weight(request):
	today = datetime.date.today()
	goals = Goal.objects.filter(user=request.user).filter(due_date__gt=today).order_by('due_date')
	if len(goals)>0:
		goal = goals[0]
		ymin = goal.target_weight
		ymax = goal.target_weight
	else:
		goal = None
		ymin = 1000
		ymax = 0
	weights = Weight.objects.filter(user=request.user).order_by('-date', '-id')
	for weight in weights:
		if weight.weight < ymin:
			ymin = weight.weight
		if weight.weight > ymax:
			ymax = weight.weight
			
	if goal and len(weights)>0:
		goal_distance = weights[0].weight - goal.target_weight
	else:
		goal_distance = 0
	
	return render_to_response('health/weight.html', {'goal': goal, 'goal_distance': goal_distance, 'ymin': str(int(ymin)-1), 'ymax': str(int(ymax)+1), 'username': request.user})

@login_required
def add_weight(request):
	logging.debug("add_weight called")
	try:
		if request.method == 'POST':
			logging.debug("add_weight post request with items %s" % repr(request.POST.items()))
			datestring=request.POST.get('date')
			try:
				weight = str(parsefloat(request.POST.get('weight')))
			except ValueError, exc:
				logging.exception("Exception occured in add_weight: %s" % exc)
				result = {'success': False, 'msg': "Ungueltiges Gewicht: %s" % request.POST.get('weight')}
				return HttpResponse(simplejson.dumps(result))
			try:
				d = datetime.datetime.strptime(datestring, "%d.%m.%Y")
				date = datetime.date(year=d.year, month=d.month, day=d.day)
			except ValueError, exc:
				try:
					d = datetime.datetime.strptime(datestring, "%Y-%m-%d")
					date = datetime.date(year=d.year, month=d.month, day=d.day)
				except ValueError, exc:
					logging.exception("Exception occured in add_weight: %s" % exc)
					result = {'success': False, 'msg': "Ungueltiges Datum: %s" % datestring}
					return HttpResponse(simplejson.dumps(result))
	
			new_weight = Weight(date=date, weight=weight, user=request.user)
			new_weight.save()
			result = {'success': True}
			return HttpResponse(simplejson.dumps(result))
		else:
			return HttpResponseBadRequest()
	except Exception, exc:
		logging.exception("Exception occured in add_weight: %s" % exc)
		result = {'success': False, 'msg': "Fehler aufgetreten: %s" % str(exc)}
		return HttpResponse(simplejson.dumps(result))
	 
@login_required
def add_weightgoal(request):
	try:
		if request.method == 'POST':
			logging.debug("add_weightgoal post request with items %s" % repr(request.POST.items()))
			datestring = ""
			try:
				datestring=request.POST.get('date')
				d = datetime.datetime.strptime(datestring, "%d.%m.%Y")
			except Exception, exc:
				logging.exception("Exception occured in add_weight: %s" % exc)
				result = {'success': False, 'msg': "Ungueltiges Datum: %s" % datestring}
				return HttpResponse(simplejson.dumps(result))
			try:
				weight = str(parsefloat(request.POST.get('weight')))
			except ValueError, exc:
				logging.exception("Exception occured in add_weight: %s" % exc)
				result = {'success': False, 'msg': "Ungueltiges Gewicht: %s" % request.POST.get('weight')}
				return HttpResponse(simplejson.dumps(result))
			
			due_date = datetime.date(year=d.year, month=d.month, day=d.day)
			date = datetime.date.today()
			new_goal = Goal(date=date, due_date=due_date, target_weight=weight, user=request.user)
			new_goal.save()
			result = {'success': True}
			return HttpResponse(simplejson.dumps(result))
		else:
			return HttpResponseBadRequest()
	except Exception, exc:
		logging.exception("Exception occured in add_weightgoal: %s" % exc)
		result = {'success': False, 'msg': "Fehler aufgetreten: %s" % str(exc)}
		return HttpResponse(simplejson.dumps(result))

@login_required
def add_desease(request):
	logging.debug("add_desease called")
	try:
		if request.method == 'POST':
			if request.POST.has_key('update_id'):
				desease = Desease.objects.get(pk=int(request.POST.get('update_id')))
				# If selected_by_id desease does not belong to current user, create new desease
				if desease.user != request.user:
					desease = Desease(user = request.user)
			else:
				desease = Desease(user = request.user)

			
			logging.debug("add_desease post request with items %s" % repr(request.POST.items()))
			startdate_string = request.POST.get('start_date')
			enddate_string = request.POST.get('end_date')
			name = request.POST.get('name')
			comment = request.POST.get('comment')
			try:
				sd = datetime.datetime.strptime(startdate_string, "%d.%m.%Y")
				startdate = datetime.date(year=sd.year, month=sd.month, day=sd.day)
			except ValueError, exc:
				logging.exception("Exception occured in add_desease: %s" % exc)
				result = {'success': False, 'msg': "Ungueltiges Datum: %s" % startdate_string}
				return HttpResponse(simplejson.dumps(result))
			try:
				ed = datetime.datetime.strptime(enddate_string, "%d.%m.%Y")
				enddate = datetime.date(year=ed.year, month=ed.month, day=ed.day)
			except ValueError, exc:
				logging.exception("Exception occured in add_desease: %s" % exc)
				result = {'success': False, 'msg': "Ungueltiges Datum: %s" % enddate_string}
				return HttpResponse(simplejson.dumps(result))
	
			desease.start_date=startdate
			desease.end_date=enddate
			desease.comment=comment
			desease.name=name
			desease.save()
			result = {'success': True}
			return HttpResponse(simplejson.dumps(result))
		else:
			return HttpResponseBadRequest()
	except Exception, exc:
		logging.exception("Exception occured in add_desease: %s" % exc)
		result = {'success': False, 'msg': "Fehler aufgetreten: %s" % str(exc)}
		return HttpResponse(simplejson.dumps(result))

@login_required
def get_desease(request):
	desease_id = request.GET.get('id', '')
	desease = Desease.objects.get(pk=int(desease_id))
	if desease.user == request.user:
		return HttpResponse(serializers.serialize('json', [desease]), mimetype='application/json')
	else:
		return HttpResponseForbidden()
	
@login_required
def get_data(request):
	timespan = request.GET.get('timespan', '')
	today = datetime.date.today()

	try:
		timespan = int(timespan)
	except ValueError:
		timespan = -1
	
	pulse_max_list= []
	pulse_rest_list = []
	weight_list = []
	weight_weekly_list = []

	pulses = Pulse.objects.filter(user=request.user).order_by('date', 'id')
	weights = Weight.objects.filter(user=request.user).order_by('date', 'id')
	if timespan != -1:
		start_date = datetime.datetime.today() - datetime.timedelta(days=timespan)
		weights = weights.filter(date__gte = start_date)
		pulses = pulses.filter(date__gte = start_date)
	
	# calculating weekly averages
	weekly_weights = {}
	week = namedtuple("Week", ["year", "week"])
	
	for weight in weights:
		w = week(year=weight.date.year, week=weight.date.isocalendar()[1])
		if w not in weekly_weights:
			weekly_weights[w] = []
		weekly_weights[w].append(weight.weight) 
	weeks = weekly_weights.keys()
	weeks.sort()
	for week in weeks:
		weight_values = weekly_weights[week]
		weight_weekly_list.append([time.mktime(time.strptime("%s %s 1" % (week.year, week.week), "%Y %W %w"))*1000, float(sum(weight_values)/len(weight_values))])

	# building detailed weight_list
	for weight in weights:
		weight_list.append([time.mktime(weight.date.timetuple())*1000, float(weight.weight)])
	
	for pulse in pulses:
		if pulse.rest:
			pulse_rest_list.append([time.mktime(pulse.date.timetuple())*1000, pulse.rest])
		if pulse.maximum:
			pulse_max_list.append([time.mktime(pulse.date.timetuple())*1000, pulse.maximum])
	
	goal_data = []
	if len(weights)>0 and len(pulses)>0:
		first_date = min(weights[0].date, pulses[0].date)
		
		last_date = max(weights[len(weights)-1].date, pulses[len(pulses)-1].date)

		goals = Goal.objects.filter(user=request.user).filter(due_date__gt=today).order_by('due_date')
		if len(goals)>0:
			goal = goals[0]
			goal_data = [[time.mktime(first_date.timetuple())*1000, int(goal.target_weight)], [time.mktime(last_date.timetuple())*1000, int(goal.target_weight)]]

	return HttpResponse(simplejson.dumps({"weight_list": weight_list, "weight_weekly_list": weight_weekly_list, "pulse_min_list": pulse_rest_list, "pulse_max_list": pulse_max_list, "goal_data": goal_data}))

@login_required
def add_pulse(request):
	try:
		if request.method == 'POST':
			datestring=request.POST.get('date')
			logging.debug("add_pulse post request with items %s" % repr(request.POST.items()))
			if not ("rest" in request.POST or "maximum" in request.POST):
				logging.error("Received neither rest nor maximum pulse")
				return HttpResponse(simplejson.dumps({"success": False, 'msg': "Keine Pulswerte uebermittelt"}))
			else:
				try:
					d = datetime.datetime.strptime(datestring, "%d.%m.%Y")
					date = datetime.date(year=d.year, month=d.month, day=d.day)
				except ValueError, exc:
					try:
						d = datetime.datetime.strptime(datestring, "%Y-%m-%d")
						date = datetime.date(year=d.year, month=d.month, day=d.day)
					except ValueError, exc:
						logging.exception("Exception occured in add_pulse: %s" % exc)
						result = {'success': False, 'msg': "Ungueltiges Datum: %s" % datestring}
						return HttpResponse(simplejson.dumps(result))
				
				new_pulse = Pulse(user=request.user, date = date)
				if "rest" in request.POST:
					new_pulse.rest = request.POST.get("rest")
				if "maximum" in request.POST:
					new_pulse.maximum = request.POST.get("maximum")
				new_pulse.save()
				return HttpResponse(simplejson.dumps({"success": True }))
		else:
			return HttpResponseBadRequest()
	except Exception, exc:
		logging.exception("Exception occured in add_pulse: %s" % exc)
		result = {'success': False, 'msg': "Fehler aufgetreten:: %s" % exc}
		return HttpResponse(simplejson.dumps(result))
