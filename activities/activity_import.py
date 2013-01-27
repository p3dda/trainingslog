#!/usr/bin/env python

import dateutil
import logging

from activities.extras import tcx2gpx
from activities.models import Activity, Event, Sport, Lap
from activities.preview import create_preview

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

def importtrack_from_tcx(request, newtrack):
	"""
	Process garmin tcx file import
	"""
	logging.debug("importtrack called")

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
			speed_max = None
		else:
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
	
	# FIXME: Values should be None instead of 0 / 65535 if no values found in XML file
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
		logging.debug("Lap speed_max is %s" % lap.speed_max)
		if lap.speed_max is not None:
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
