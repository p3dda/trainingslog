#!/usr/bin/env python

import datetime
import dateutil
import json
import logging
import sys
import traceback
import urllib2

from django.conf import settings as django_settings
from django.utils.timezone import utc

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
	
	activity = Activity(name="Garmin Import")
	activity.user = request.user
	activity.event = event
	activity.sport = sport
	activity.track = newtrack
	
	date = None
	laps = []
	time_start = None
	time_end = None
	position_start = None

	for xmllap in xmlactivity.findall(xmlns + "Lap"):
		date = dateutil.parser.parse(xmllap.get("StartTime"))
		time = int(float(xmllap.find(xmlns+"TotalTimeSeconds").text))
		if xmllap.find(xmlns+"DistanceMeters") is None:
			logging.debug("DistanceMeters not present in Lap data")
			distance=None
		else:
			distance = str(float(xmllap.find(xmlns+"DistanceMeters").text)/1000)
		if xmllap.find(xmlns+"MaximumSpeed") is None:
			logging.debug("MaximumSpeed is None")
			speed_max = None
		else:
			logging.debug("MaximumSpeed xml is %r" % xmllap.find(xmlns+"MaximumSpeed"))
			speed_max = str(float(xmllap.find(xmlns+"MaximumSpeed").text)*3.6)	# Given as meters per second in tcx file
			logging.debug("speed_max is %s" % speed_max)
		if xmllap.find(xmlns+"Calories") is not None:
			calories = int(xmllap.find(xmlns+"Calories").text)
		else:
			calories = None
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

		if time != 0 and distance is not None:
			speed_avg = str(float(distance)*3600 / time)
		else:
			speed_avg = None
		
		cadence_max = None
		elev_min = None
		elev_max = None
		elev_gain = None
		elev_loss = None
		last_elev = None

		for xmltrack in xmllap.findall(xmlns + "Track"):
			for xmltp in xmltrack.findall(xmlns + "Trackpoint"):
				if not position_start:
					xmlpos = xmltp.find(xmlns + "Position")
					if xmlpos is not None:
						if xmlpos.find(xmlns + "LatitudeDegrees") is not None and xmlpos.find( xmlns + "LongitudeDegrees") is not None:
							lat = float(xmlpos.find(xmlns + "LatitudeDegrees").text)
							lon = float(xmlpos.find(xmlns + "LongitudeDegrees").text)
							position_start = (lat, lon)
				
				if not time_start and xmltp.find(xmlns + "Time") is not None:
					time_start = dateutil.parser.parse(xmltp.find(xmlns + "Time").text)
					
				if xmltp.find(xmlns + "AltitudeMeters") is not None:
					elev = int(round(float(xmltp.find(xmlns + "AltitudeMeters").text)))
				else:
					elev = last_elev
				
				if elev != last_elev:
					if elev_max is not None:
						if elev > elev_max:
							elev_max = elev
					else:
						elev_max = elev

					if elev_min is not None:
						if elev < elev_min:
							elev_min = elev
					else:
						elev_min = elev

					if last_elev:
						if elev > last_elev:
							if elev_gain is None:
								elev_gain = elev - last_elev
							else:
								elev_gain += elev - last_elev
						else:
							if elev_loss is None:
								elev_loss = last_elev - elev
							else:
								elev_loss += last_elev - elev
					last_elev = elev
				
				if xmltp.find(xmlns + "Cadence") != None:
					cadence = int(xmltp.find(xmlns + "Cadence").text)
					if cadence > cadence_max:
						cadence_max = cadence
			
			# Get timestamp from last trackpoint in this track
			xmltp = xmltrack.findall(xmlns + "Trackpoint")[-1]
			if xmltp.find(xmlns + "Time") is not None:
				time_end = dateutil.parser.parse(xmltp.find(xmlns + "Time").text)
		
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
	
	cadence_avg = None
	cadence_max = None
	calories_sum = None
	distance_sum = None
	elev_min = None
	elev_max = None
	elev_gain = None
	elev_loss = None
	hf_avg = None
	hf_max = None
	speed_max = None
	time_sum = 0
	for lap in laps:
		if lap.calories:
			if calories_sum is None:
				calories_sum = lap.calories
			else:
				calories_sum = calories_sum + lap.calories
		if lap.distance:
			if distance_sum is None:
				distance_sum = float(lap.distance)
			else:
				distance_sum += float(lap.distance)
		time_sum = time_sum + lap.time

		if lap.elevation_max > elev_max or elev_max is None:
			elev_max = lap.elevation_max
		if lap.elevation_min < elev_min or elev_min is None:
			elev_min = lap.elevation_min

		if lap.elevation_gain is not None:
			if elev_gain is None:
				elev_gain = lap.elevation_gain
			else:
				elev_gain = elev_gain + lap.elevation_gain
		if lap.elevation_loss is not None:
			if elev_loss is None:
				elev_loss = lap.elevation_loss
			else:
				elev_loss = elev_loss + lap.elevation_loss
		
		if lap.hf_max > hf_max:
			hf_max = lap.hf_max
			logging.debug("New global hf_max: %s" % hf_max)
		logging.debug("Lap speed_max is %s" % lap.speed_max)
		if lap.speed_max is not None:
			if float(lap.speed_max) > speed_max:
				speed_max = float(lap.speed_max)
				logging.debug("New global speed_max: %s" % speed_max)
		
		if lap.cadence_max > cadence_max or cadence_max is None:
			cadence_max = lap.cadence_max
		
		if lap.cadence_avg:
			if cadence_avg is None:
				cadence_avg = lap.time * lap.cadence_avg
			else:
				cadence_avg = cadence_avg + lap.time * lap.cadence_avg
		if lap.hf_avg:
			if hf_avg is None:
				hf_avg = lap.time * lap.hf_avg
			else:
				hf_avg = hf_avg + lap.time * lap.hf_avg

	try:
		wunderground_key = django_settings.WUNDERGROUND_KEY
	except AttributeError:
		wunderground_key = False
	
	if wunderground_key and position_start and date:
		try:
			(lat, lon) = position_start
			logging.debug("Getting weather data for position %r %r" % (lat,lon))
			weather_url = "http://api.wunderground.com/api/%s/geolookup/q/%s,%s.json" % (wunderground_key, lat, lon)
			f = urllib2.urlopen(weather_url)
			json_string = f.read()
			parsed_geolookup = json.loads(json_string)
			if len(parsed_geolookup["location"]["nearby_weather_stations"]["pws"]["station"]) > 0:
				weather_station = parsed_geolookup["location"]["nearby_weather_stations"]["pws"]["station"][0]
				logging.debug("Found nearby weather station %r" % weather_station)
				weather_url = "http://api.wunderground.com/api/%s/history_%s/q/pws:%s.json" % (wunderground_key, date.strftime("%Y%m%d"), weather_station["id"])
			elif len(parsed_geolookup["location"]["nearby_weather_stations"]["airport"]["station"]) > 0:
				weather_station = parsed_geolookup["location"]["nearby_weather_stations"]["airport"]["station"][0]
				logging.debug("Found nearby airport station %r" % weather_station)
				weather_url = "http://api.wunderground.com/api/%s/history_%s/q/%s.json" % (wunderground_key, date.strftime("%Y%m%d"), weather_station["icao"])
			else:
				logging.error("Did not found any nearby weather stations for  %r %r" % (lat,lon))
				raise(Exception, "Did not find any nearby weather stations for  %r %r" % (lat,lon))

			logging.debug("Fetching wheather information from url %s" % weather_url)
			activity.weather_stationname = weather_station["city"]
		
			f = urllib2.urlopen(weather_url)
			json_string = f.read(f)
			weather_observations = json.loads(json_string)["history"]["observations"]
			
			for observation in weather_observations:
				obs_date = datetime.datetime(year = int(observation["utcdate"]["year"]), month = int(observation["utcdate"]["mon"]), day = int(observation["utcdate"]["mday"]), hour = int(observation["utcdate"]["hour"]), minute = int(observation["utcdate"]["min"])).replace(tzinfo=utc)
				if obs_date >= date:
					activity.weather_temp = observation["tempm"]
					logging.debug("Weather temperature is %r" % observation["tempm"])
					activity.weather_hum = observation["hum"]
					logging.debug("Weather hum is %r" % observation["hum"])
					activity.weather_winddir = observation["wdire"]
					logging.debug("Weather winddir is %r" % observation["wdire"])
					activity.weather_windspeed = observation["wspdm"]
					logging.debug("Weather windspeed is %r" % observation["wspdm"])
					if float(observation["precip_ratem"])>=0:
						activity.weather_rain = observation["precip_ratem"]
						logging.debug("Weather rain is %r" % observation["precip_ratem"])
					else:
						activity.weather_rain = None
					break
		except Exception, exc:
			logging.error("Failed to load weather data: %s" % exc)
			for line in traceback.format_exc(sys.exc_info()[2]).splitlines():
				logging.error(line)
	else:
		if not position_start:
			logging.debug("Do not fetch weather data due to missing position data")
		if not wunderground_key:
			logging.debug("Do not fetch weather data due to missing wunderground key")

	if cadence_avg==0 or cadence_avg is None:
		activity.cadence_avg = None
	else:	
		activity.cadence_avg = int(cadence_avg / time_sum)
	if cadence_max==0:
		activity.cadence_max = None
	else:
		activity.cadence_max = cadence_max
	activity.calories = calories_sum
	activity.speed_max = str(speed_max)
	if hf_avg==0:
		activity.hf_avg = None
	else:
		activity.hf_avg = int(hf_avg / time_sum)
	if hf_max==0:
		activity.hf_max = None
	else:
		activity.hf_max = hf_max
	activity.distance = str(distance_sum)
	activity.elevation_min = elev_min
	activity.elevation_max = elev_max
	activity.elevation_gain = elev_gain
	activity.elevation_loss = elev_loss
	activity.time = time_sum
	activity.date = laps[0].date
	activity.speed_avg = str(float(activity.distance) * 3600 / activity.time)
	
	if time_start and time_end:
		logging.debug("First and last trackpoint timestamps in track are %s and %s" % (time_start, time_end))
		activity.time_elapsed = (time_end - time_start).days * 86400 + (time_end - time_start).seconds

	activity.save()

	for lap in laps:
		lap.activity = activity
		lap.save()
	
	# generate preview image for track
	create_preview(activity.track)

	return activity
