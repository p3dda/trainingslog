from xml import sax
from xml.sax import saxutils
import os
import datetime
import json
import logging
import sys
import traceback
import urllib2

from django.core.files.temp import NamedTemporaryFile
from django.core.files.base import File
import dateutil
from django.conf import settings as django_settings
from django.utils.timezone import utc

import activities.utils
from activities.models import Activity, Event, Sport, Lap
from libs.fitparse import fitparse



GPX_HEADER = """<gpx xmlns="http://www.topografix.com/GPX/1/1"
	creator="https://github.com/p3dda/trainingslog"
	version="1.1"
	xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
	xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">
"""

class ActivityFileMeta(type):
	def __init__(cls, name, bases, dct):
		if not hasattr(cls, 'registry'):
			cls.registry = {}
		if 'filetypes' in dct:
			if dct['filetypes'] is not None:
				for filetype in dct['filetypes']:
					cls.registry[filetype] = cls
		super(ActivityFileMeta, cls).__init__(name, bases, dct)

	def __call__(cls, *args, **kwargs):
		track = args[0]
		filetype = os.path.splitext(track.trackfile.name)[1][1:].lower()

		if filetype in cls.registry:
			# # select correct subclass for switch vendor
			sw_cls = cls.registry[filetype]
		else:
			raise NotImplementedError('Filetype %s is not supported' % filetype)
		return super(ActivityFileMeta, sw_cls).__call__(*args, **kwargs)


ActivityFileMetaclass = ActivityFileMeta('ActivityFileMetaclass', (object, ), {})

class ActivityFile(ActivityFileMetaclass):
	filetypes = None

	def __init__(self, track, request=None):
		self.track = track
		self.request = request
		self.activity = None
		self.laps = None
		self.track_data={'alt': [], 'cad': [], 'hf': [], 'pos': [], 'speed_gps': [], 'speed_foot': [], 'stance_time': [], 'temperature': [], 'vertical_oscillation': []}
		self.track_by_distance={}
		self.detail_entries = {}
		self.position_start = None

	def get_activity(self):
		return self.activity

	def get_laps(self):
		return self.laps

	def to_gpx(self):
		#TODO: Port .fit implementation and use for all file types
		raise NotImplementedError

	def set_weather(self):
		try:
			wunderground_key = django_settings.WUNDERGROUND_KEY
		except AttributeError:
			logging.debug("Wunderground key is not configured, cannot load weather data")
			return None
		try:
			(lat, lon) = self.position_start

			logging.debug("Getting weather data for position %r %r" % (lat,lon))
			weather_url = "http://api.wunderground.com/api/%s/geolookup/q/%s,%s.json" % (wunderground_key, lat, lon)
			f = urllib2.urlopen(weather_url)
			json_string = f.read()
			parsed_geolookup = json.loads(json_string)
			if len(parsed_geolookup["location"]["nearby_weather_stations"]["pws"]["station"]) > 0:
				weather_station = parsed_geolookup["location"]["nearby_weather_stations"]["pws"]["station"][0]
				logging.debug("Found nearby weather station %r" % weather_station)
				weather_url = "http://api.wunderground.com/api/%s/history_%s/q/pws:%s.json" % (wunderground_key, self.activity.date.strftime("%Y%m%d"), weather_station["id"])
			elif len(parsed_geolookup["location"]["nearby_weather_stations"]["airport"]["station"]) > 0:
				weather_station = parsed_geolookup["location"]["nearby_weather_stations"]["airport"]["station"][0]
				logging.debug("Found nearby airport station %r" % weather_station)
				weather_url = "http://api.wunderground.com/api/%s/history_%s/q/%s.json" % (wunderground_key, self.activity.date.strftime("%Y%m%d"), weather_station["icao"])
			else:
				logging.error("Did not found any nearby weather stations for  %r %r" % (lat,lon))
				raise(Exception, "Did not find any nearby weather stations for  %r %r" % (lat,lon))

			logging.debug("Fetching wheather information from url %s" % weather_url)
			self.activity.weather_stationname = weather_station["city"]

			f = urllib2.urlopen(weather_url)
			json_string = f.read(f)
			weather_observations = json.loads(json_string)["history"]["observations"]

			for observation in weather_observations:
				obs_date = datetime.datetime(year = int(observation["utcdate"]["year"]), month = int(observation["utcdate"]["mon"]), day = int(observation["utcdate"]["mday"]), hour = int(observation["utcdate"]["hour"]), minute = int(observation["utcdate"]["min"])).replace(tzinfo=utc)
				if obs_date >= self.activity.date:
					self.activity.weather_temp = observation["tempm"]
					logging.debug("Weather temperature is %r" % observation["tempm"])
					self.activity.weather_hum = observation["hum"]
					logging.debug("Weather hum is %r" % observation["hum"])
					self.activity.weather_winddir = observation["wdire"]
					logging.debug("Weather winddir is %r" % observation["wdire"])
					self.activity.weather_windspeed = observation["wspdm"]
					logging.debug("Weather windspeed is %r" % observation["wspdm"])
					if float(observation["precip_ratem"])>=0:
						self.activity.weather_rain = observation["precip_ratem"]
						logging.debug("Weather rain is %r" % observation["precip_ratem"])
					else:
						self.activity.weather_rain = None
					break
		except Exception, exc:
			logging.error("Failed to load weather data: %s" % exc)
			for line in traceback.format_exc(sys.exc_info()[2]).splitlines():
				logging.error(line)
			return None



	def import_activity(self):
		# create new activity from file
		# Event/sport is only dummy for now, make selection after import
		events = Event.objects.filter(user=self.request.user) #FIXME: there must always be a event and sport definied
		sports = Sport.objects.filter(user=self.request.user)

		if events is None or len(events)==0:
			raise RuntimeError("There must be a event type defined. Please define one first.")
		if sports is None or len(sports)==0:
			raise RuntimeError("There must be a sport type defined. Please define one first.")

		event = events[0]
		sport = sports[0]

		self.activity = Activity(name="Garmin Import")
		self.activity.user = self.request.user
		self.activity.event = event
		self.activity.sport = sport
		self.activity.track = self.track

		# fetch details data from file
		self.parse_file()
		self.calc_totals()

		if self.position_start is not None:
			self.set_weather()

		self.activity.save()

		for lap in self.laps:
			lap.activity = self.activity
			lap.save()

		# generate preview image for track
		self.create_preview()
		if len(self.get_pos()) > 0:
			self.to_gpx()			# create gpx file from track


	def calc_totals(self):
		"""
		Calculate overall sums and averages from lap data
		"""
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

		for lap in self.laps:
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

		if cadence_avg==0 or cadence_avg is None:
			self.activity.cadence_avg = None
		else:
			self.activity.cadence_avg = int(cadence_avg / time_sum)
		if cadence_max==0:
			self.activity.cadence_max = None
		else:
			self.activity.cadence_max = cadence_max
		self.activity.calories = calories_sum
		if speed_max:
			self.activity.speed_max = str(speed_max)
		else:
			self.activity.speed_max = None
		if hf_avg==0 or hf_avg is None:
			self.activity.hf_avg = None
		else:
			self.activity.hf_avg = int(hf_avg / time_sum)
		if hf_max==0:
			self.activity.hf_max = None
		else:
			self.activity.hf_max = hf_max
		self.activity.distance = str(distance_sum)
		self.activity.elevation_min = elev_min
		self.activity.elevation_max = elev_max
		self.activity.elevation_gain = elev_gain
		self.activity.elevation_loss = elev_loss
		self.activity.time = time_sum
		self.activity.date = self.laps[0].date
		self.activity.speed_avg = str(float(self.activity.distance) * 3600 / self.activity.time)

		if self.time_start and self.time_end:	# FIXME: This is not set in fit activities
			logging.debug("First and last trackpoint timestamps in track are %s and %s" % (self.time_start, self.time_end))
			self.activity.time_elapsed = (self.time_end - self.time_start).days * 86400 + (self.time_end - self.time_start).seconds

	def parse_file(self):
		"""Parse trackfile
		@return Dictionary
		"""
		raise NotImplementedError

	def create_preview(self):
		logging.debug("Creating preview image for track")
		if self.track:
			pos_list = self.get_pos(90)

			if len(pos_list) > 1:
				gmap_coords = []
				for (lat, lon) in pos_list:
					if lat is not None and lon is not None:
						gmap_coords.append("%s,%s" % (round(lat, 4), round(lon, 4)))
				gmap_path = "|".join(gmap_coords)

				url = "http://maps.google.com/maps/api/staticmap?size=480x480&path=color:0xff0000ff|"+gmap_path+"&sensor=true"
				logging.debug("Fetching file from %s" % url)
				logging.debug("Length of url is %s chars" % len(url))
				try:
					img_temp = NamedTemporaryFile(delete=True)
					img_temp.write(urllib2.urlopen(url).read())
					img_temp.flush()
					name=os.path.splitext(os.path.split(self.track.trackfile.name)[1])[0]
					logging.debug("Saving as %s.jpg" % name)

					self.track.preview_img.save("%s.jpg" % name, File(img_temp), save=True)
				except urllib2.URLError, exc:
					logging.error("Exception occured when creating preview image: %s" % exc)
			else:
				logging.debug("Track has no GPS position data, not creating preview image")
			# TODO: Maybe load fallback image as preview_image

	def get_alt(self):
		"""Returns list of (distance, altitude) tuples with optional given max length
		@returns (distance, altitude) tuples
		@rtype: list
		"""
		return self.track_data["alt"]

	def get_cad(self):
		"""Returns list of (distance, cadence) tuples with optional given max length
		@returns (distance, cadence) tuples
		@rtype: list
		"""
		return self.track_data["cad"]


	def get_hf(self):
		"""Returns list of (distance, heartrate) tuples with optional given max length
		@returns (distance, heartrate) tuples
		@rtype: list
		"""
		return self.track_data["hf"]

	def get_temperature(self):
		"""Returns list of (distance, temperature) tuples with optional given max length
		@returns (distance, temperature) tuples
		@rtype: list
		"""
		return self.track_data["temperature"]

	def get_pos(self, samples=-1):
		"""Returns list of (lat, lon) tuples with trackpoint gps coordinates
		@param samples: Max number of samples
		@type samples: int
		@returns (lat, lon) tuples
		@rtype: list
		"""
		if self.track_data.has_key("pos"):
			if samples > 0:
				if len(self.track_data["pos"]) > samples:
					sample_size = len(self.track_data["pos"]) / samples
					return self.track_data["pos"][0::sample_size]
			return self.track_data["pos"]
		else:
			return []

	def get_speed(self, pace=False):
		"""Returns list of (distance, trackpoint_time, speed) triples
		@param pace: Return speed as pace
		@type pace: boolean
		@returns (distance, heartrate) tuples
		@rtype: list
		"""

		MAX_OFFSET=10
		MAX_OFFSET_AVG=20
		MAX_DIST=100.0
		MAX_DIST_AVG=100.0
		speed_data=[]

		# Get all distances recorded, which are keys
		dist_points=self.track_by_distance.keys()
		# Sort them
		dist_points.sort()

		speed_avg=0.0
		count_avg=0

		# Go through all distances in the sorted list
		for i in range(0,len(dist_points)):
			# get the current (fixed) position, for which we calculate the speed from GPS time information
			fix_pos=dist_points[i]
			# if no GPS time recorded, skip the current fix_pos
			if not self.track_by_distance[fix_pos].has_key("gps"):
				continue
			if fix_pos is None:
				continue
			min_pos=i-MAX_OFFSET

			if min_pos<0:
				min_pos=0

			speed=count=0
			# Go through previous points and calculate speed using all the previous positions
			for pos in range(i,min_pos,-1):
				if i==fix_pos:
					continue
				new_pos=dist_points[pos]
				if not self.track_by_distance[new_pos].has_key("gps"):
					continue
				dist_diff=fix_pos-new_pos
				if dist_diff>MAX_DIST:
					break
				#logging.debug("Current fix_pos num %i is %f and new_pos num %i is %f" % (i,fix_pos,pos,new_pos))
				assert dist_diff>=0
				time_diff=self.track_by_distance[fix_pos]["gps"]-self.track_by_distance[new_pos]["gps"]
				time_diff_s=time_diff.seconds + time_diff.days*24*3600 #FIXME: month and year changes are not calculated here
				if time_diff_s > 0 and dist_diff > 0:
					speed += dist_diff / time_diff_s
					count+=1
			# if we have at least one position, store it as gps_speed
			if count>0:
				speed=speed/count
				self.track_by_distance[fix_pos]["gps_speed"]=speed
				count_avg+=1
				speed_avg += speed
		if count_avg>0:
			speed_avg=speed_avg/count_avg
		else:
			speed_avg=speed_avg

		max_speedchange_avg=speed_avg/3.6 # This value is currently determined for running events. Might not be a fixed value but dependent from speed_avg

		#logging.debug("Speed average is %f m/s for %i data points using %f as max_speedchange_avg" % (speed_avg,count_avg,max_speedchange_avg))

		# now average over all speed using speed info in forward and backward direction
		for i in range(0,len(dist_points)):
			fix_pos=dist_points[i]
			if not self.track_by_distance[fix_pos].has_key("gps"):
				continue
			if fix_pos is None:
				continue

			min_pos=i-MAX_OFFSET_AVG
			max_pos=i+MAX_OFFSET_AVG
			if min_pos<0:
				min_pos=0
			if max_pos>=len(dist_points):
				max_pos=len(dist_points)-1
			speed=count=0
			if self.track_by_distance[fix_pos].has_key("gps_speed"):
				cur_speed=self.track_by_distance[fix_pos]["gps_speed"]
			else:
				cur_speed=None
			for pos in range(min_pos,max_pos):
				new_pos=dist_points[pos]
				if not self.track_by_distance[new_pos].has_key("gps_speed"):
					continue
				# If we reached the maximum difference in distance, skip these points
				if new_pos-fix_pos>MAX_DIST_AVG:
					break
				if abs(new_pos-fix_pos)>MAX_DIST_AVG:
					continue
				if cur_speed is not None:
					if abs(cur_speed-self.track_by_distance[new_pos]["gps_speed"])>max_speedchange_avg:
						continue

				speed=speed+self.track_by_distance[new_pos]["gps_speed"]
				count += 1
			if count>0:
				speed /= count
				if pace:
					speed = 1000.0/60.00/speed # convert to min/km
				else:
					speed *= 3.6# convert to km/h

				speed_data.append((fix_pos,self.track_by_distance[fix_pos]["trackpoint_time"],speed))
		return speed_data


	def get_speed_foot(self, pace=False):
		"""
		Returns list of triples, containing distance, trackpoint_time and speed read from footpod
		@param pace: return speed as pace
		@type pace: boolean
		@return: list
		"""
		speed_data = []
		for (distance,trackpoint_time,speed) in self.track_data["speed_foot"]:
			if pace:
				if speed==0:
					speed=0
				else:
					speed = 60 / (speed*3.6)
			else:
				speed *= 3.6
				if pace and speed> 20:
					continue
			speed_data.append((distance,trackpoint_time,speed))
		return speed_data

	def get_speed_gps(self, pace=False):
		"""
		Returns list of triples, containing distance, trackpoint_time and speed (gps-based)
		@param pace: return speed as pace
		@type pace: boolean
		@return: list
		"""
		return self.get_speed(pace)

	def get_stance_time(self):
		"""Returns list of (distance, stance_time) tuples
		@returns (distance, stance_time) tuples
		@rtype: list
		"""
		return self.track_data["stance_time"]

	def get_vertical_oscillation(self):
		"""Returns list of (distance, vertical_oscillation) tuples
		@returns (distance, vertical_oscillation) tuples
		@rtype: list
		"""
		return self.track_data["vertical_oscillation"]

	def get_detail_entries(self):
		""" Returns dict containing title and value for additional entries in activity detail view
		@returns dict
		"""
		return self.detail_entries


