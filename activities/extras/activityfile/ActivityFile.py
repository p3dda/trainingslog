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

GPX_HEADER = """<gpx xmlns="http://www.topografix.com/GPX/1/1"
	creator="https://github.com/p3dda/trainingslog"
	version="1.1"
	xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
	xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">
"""



class ActivityFile:
	def __init__(self, track, request=None):
		self.track = track
		self.request = request
		self.activity = None
		self.laps = None
		self.track_data={'alt': [], 'cad': [], 'hf': [], 'pos': [], 'speed_gps': [], 'speed_foot': [], 'stance_time': [], 'vertical_oscillation': []}
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
		self.activity.speed_max = str(speed_max)
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


class TCXFile(ActivityFile):
	#TCX_NS="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"
	TCX_NS = "{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}"
	xmlns = "{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}"
	xmlactextns = "{http://www.garmin.com/xmlschemas/ActivityExtension/v2}"
	xml_instance = "{http://www.w3.org/2001/XMLSchema-instance}"

	class MyHandler(sax.handler.ContentHandler):
		def __init__(self, w):
			self.time = ""
			self.lat = ""
			self.lon = ""
			self.alt = ""
			self.content = ""
			self.w = w
			self.min_lat = 1000.0
			self.max_lat = 0
			self.min_lon = 1000.0
			self.max_lon = 0

			self.gpsfixes = 0

		def startDocument(self):
			self.w(GPX_HEADER)

		def endDocument(self):
			self.w(' <bounds minlat="%s" minlon="%s" maxlat="%s" maxlon="%s"/>\n' % (self.min_lat, self.min_lon, self.max_lat, self.max_lon))
			self.w('</gpx>\n')

		def startElement(self, name, attrs):

			self.content = ""
			if name == 'Track':
				self.w(' <trk>\n  <trkseg>\n')




		def characters(self, content):
			self.content = self.content + saxutils.escape(content)

	#    def endElementNS(fname, qname, attrs):
	#        (ns, name) = fname

		def endElement(self, name):
			if name == 'Track':
				self.w('  </trkseg>\n </trk>\n')
			elif name == 'Trackpoint':
				try:
					if float(self.lat) < self.min_lat:
						self.min_lat = float(self.lat)
					if float(self.lat) > self.max_lat:
						self.max_lat = float(self.lat)
					if float(self.lon) < self.min_lon:
						self.min_lon = float(self.lon)
					if float(self.lon) > self.max_lon:
						self.max_lon = float(self.lon)
				except ValueError:
					pass
				else:
					if self.lon and self.lat:
						self.w('   <trkpt lat="%s" lon="%s">\n' % (self.lat, self.lon))
						if self.alt:
							self.w('    <ele>%s</ele>\n' % self.alt)
						if self.time:
							self.w('    <time>%s</time>\n' % self.time)
						self.w('   </trkpt>\n')
						sys.stdout.flush()
						self.gpsfixes += 1
			elif name == 'LatitudeDegrees':
				self.lat = self.content
			elif name == 'LongitudeDegrees':
				self.lon = self.content
			elif name == 'AltitudeMeters':
				self.alt = self.content
			elif name == 'Time':
				self.time = self.content


	def __init__(self, track, request=None):
		ActivityFile.__init__(self, track, request)
		track.trackfile.open()
		self.xmltree = ElementTree(file = track.trackfile)
		track.trackfile.close()
		#logging.debug("Trackfile %r closed" % tcxfile.trackfile)

		self.parse_trackpoints()

	def to_gpx(self):
		logging.debug("convert called with track %s" % self.track.trackfile)
		try:
			with open(self.track.trackfile.path+".gpx", 'w') as f:
				logging.debug("Opened gpx file %s for write" % self.track.trackfile.path+".gpx")
				w = f.write
				handler = self.MyHandler(w)
				sax.parse(self.track.trackfile.path, handler)

			# do not keep empty gpx files (occurs when having .tcx recordings without GPS enabled)
			if handler.gpsfixes == 0:
				gpxfile = self.track.trackfile.path+".gpx"
				os.remove(gpxfile)
		except Exception, msg:
			logging.debug("Exception occured in convert: %s" % msg)

	def parse_file(self):
		self.laps = []
		self.position_start = None
		self.date = None
		self.time_start = None
		self.time_end = None

		self.track.trackfile.open()
		xmltree = ElementTree(file = self.track.trackfile)
		self.track.trackfile.close()

		# take only first activity from file
		xmlactivity = xmltree.find(self.TCX_NS + "Activities")[0]

		lap_date = None

		for xmllap in xmlactivity.findall(self.TCX_NS + "Lap"):
			lap_date = dateutil.parser.parse(xmllap.get("StartTime"))
			if self.date == None:
				self.date = lap_date

			time = int(float(xmllap.find(self.TCX_NS+"TotalTimeSeconds").text))
			if xmllap.find(self.TCX_NS+"DistanceMeters") is None:
				logging.debug("DistanceMeters not present in Lap data")
				distance=None
			else:
				distance = str(float(xmllap.find(self.TCX_NS+"DistanceMeters").text)/1000)
			if xmllap.find(self.TCX_NS+"MaximumSpeed") is None:
				logging.debug("MaximumSpeed is None")
				speed_max = None
			else:
				logging.debug("MaximumSpeed xml is %r" % xmllap.find(self.TCX_NS+"MaximumSpeed"))
				speed_max = str(float(xmllap.find(self.TCX_NS+"MaximumSpeed").text)*3.6)	# Given as meters per second in tcx file
				logging.debug("speed_max is %s" % speed_max)
			if xmllap.find(self.TCX_NS+"Calories") is not None:
				calories = int(xmllap.find(self.TCX_NS+"Calories").text)
			else:
				calories = None
			try:
				hf_avg = int(xmllap.find(self.TCX_NS+"AverageHeartRateBpm").find(self.TCX_NS+"Value").text)
				logging.debug("Found hf_avg: %s" % hf_avg)
			except AttributeError:
				hf_avg = None
				logging.debug("Not found hf_avg")
			try:
				hf_max = int(xmllap.find(self.TCX_NS+"MaximumHeartRateBpm").find(self.TCX_NS+"Value").text)
				logging.debug("Found hf_max: %s" % hf_max)
			except AttributeError:
				hf_max = None
				logging.debug("Not found hf_max")
			try:
				cadence_avg = int(xmllap.find(self.TCX_NS+"Cadence").text)
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

			for xmltrack in xmllap.findall(self.TCX_NS + "Track"):
				for xmltp in xmltrack.findall(self.TCX_NS + "Trackpoint"):
					if not self.position_start:
						xmlpos = xmltp.find(self.TCX_NS + "Position")
						if xmlpos is not None:
							if xmlpos.find(self.TCX_NS + "LatitudeDegrees") is not None and xmlpos.find( self.TCX_NS + "LongitudeDegrees") is not None:
								lat = float(xmlpos.find(self.TCX_NS + "LatitudeDegrees").text)
								lon = float(xmlpos.find(self.TCX_NS + "LongitudeDegrees").text)
								self.position_start = (lat, lon)

					if not self.time_start and xmltp.find(self.TCX_NS + "Time") is not None:
						self.time_start = dateutil.parser.parse(xmltp.find(self.TCX_NS + "Time").text)

					if xmltp.find(self.TCX_NS + "AltitudeMeters") is not None:
						elev = int(round(float(xmltp.find(self.TCX_NS + "AltitudeMeters").text)))
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

					if xmltp.find(self.TCX_NS + "Cadence") != None:
						cadence = int(xmltp.find(self.TCX_NS + "Cadence").text)
						if cadence > cadence_max:
							cadence_max = cadence

				# Get timestamp from last trackpoint in this track
				xmltp = xmltrack.findall(self.TCX_NS + "Trackpoint")[-1]
				if xmltp.find(self.TCX_NS + "Time") is not None:
					self.time_end = dateutil.parser.parse(xmltp.find(self.TCX_NS + "Time").text)

			lap = Lap(
					date = lap_date,
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

			self.laps.append(lap)

	def parse_trackpoints(self):
		# take only first activity from file
		xmlactivity = self.xmltree.find(self.xmlns + "Activities")[0]

		alt_data=[]
		cad_data=[]
		hf_data=[]
		pos_data=[]
		speed_gps_data=[]
		speed_foot_data=[]
		#logging.debug("Parsing TCX Track file in first activity")
		first_lap = xmlactivity.find(self.xmlns + "Lap")
		start_time = dateutil.parser.parse(first_lap.get("StartTime"))
		offset_time = 0 # used to remove track sequences from plot where no movement has occured
		last_lap_distance = 0 # used to add distance to laps starting with distance 0
		last_distance = None
		last_lat_lon = None

		for xmllap in xmlactivity.findall(self.xmlns+"Lap"):
			distance_offset = 0
			# check if lap starts with distance 0
			if len(xmllap.findall(self.xmlns+"Track/"+self.xmlns+"Trackpoint")) == 0:
				continue		# skip empty laps
			xmltp = xmllap.findall(self.xmlns+"Track/"+self.xmlns+"Trackpoint")[0]
			if hasattr(xmltp.find(self.xmlns + "DistanceMeters"),"text"):
				distance = float(xmltp.find(self.xmlns + "DistanceMeters").text)
				if distance < last_lap_distance:
					distance_offset = last_lap_distance

			for xmltp in xmllap.findall(self.xmlns+"Track/"+self.xmlns+"Trackpoint"):
				distance=alt=cad=hf=trackpoint_time=None

				if hasattr(xmltp.find(self.xmlns + "DistanceMeters"),"text"):
					distance = float(xmltp.find(self.xmlns + "DistanceMeters").text)
					distance = distance + distance_offset
				elif xmltp.find(self.xmlns + "Position"):
						xmltp_pos = xmltp.find(self.xmlns + "Position")
						lat = float(xmltp_pos.find(self.xmlns + "LatitudeDegrees").text)
						lon =  float(xmltp_pos.find(self.xmlns + "LongitudeDegrees").text)
						if last_lat_lon is None:
							last_lat_lon = (lat, lon)
							last_distance = 0
							continue
						else:
							distance = last_distance + activities.utils.latlon_distance(last_lat_lon, (lat, lon))
							last_lat_lon = (lat, lon)
				else:
					continue
				if not hasattr(xmltp.find(self.xmlns + "Time"),"text"):
					continue

				delta = dateutil.parser.parse(xmltp.find(self.xmlns + "Time").text)-start_time
				trackpoint_time = ((delta.seconds + 86400 * delta.days)-offset_time) * 1000

				# Find sections with speed < 0.5m/s (no real movement, remove duration of this section from timeline)
				if last_distance:
					delta_dist = distance - last_distance
					delta_time = (trackpoint_time - self.track_by_distance[last_distance]["trackpoint_time"]) / 1000
					if delta_time > 0 and (delta_dist / delta_time) < 0.5:
						offset_time += delta_time
						trackpoint_time = ((delta.seconds + 86400 * delta.days)-offset_time) * 1000
				last_distance = distance

				if not self.track_by_distance.has_key(distance):
					self.track_by_distance[distance]={}
				self.track_by_distance[distance]["trackpoint_time"]=trackpoint_time


				# Get altitude
				if hasattr(xmltp.find(self.xmlns + "AltitudeMeters"),"text"):
					alt = float(xmltp.find(self.xmlns + "AltitudeMeters").text)
					self.track_by_distance[distance]["alt"]=alt
	#				alt_data.append((trackpoint_time,alt))
					alt_data.append((distance,trackpoint_time,alt))
				# Get Cadence data (from Bike cadence sensor)
				if hasattr(xmltp.find(self.xmlns + "Cadence"),"text"):
					cad = int(xmltp.find(self.xmlns + "Cadence").text)
					self.track_by_distance[distance]["cad"]=cad
	#				cad_data.append((trackpoint_time,cad))
					cad_data.append((distance,trackpoint_time,cad))

				# Locate heart rate in beats per minute
				hrt=xmltp.find(self.xmlns + "HeartRateBpm")
				if not hrt is None:
					if hasattr(xmltp.find(self.xmlns + "HeartRateBpm/"+ self.xmlns+ "Value"),"text"):
						hf = int(xmltp.find(self.xmlns + "HeartRateBpm/"+ self.xmlns+ "Value").text)
						self.track_by_distance[distance]["hf"]=hf
	#					hf_data.append((trackpoint_time,hf))
						hf_data.append((distance,trackpoint_time,hf))

				# Locate time stamps for speed calculation based on GPS
				if hasattr(xmltp.find(self.xmlns + "Time"),"text"):
					track_time = dateutil.parser.parse(xmltp.find(self.xmlns + "Time").text)
					self.track_by_distance[distance]["gps"]=track_time
					speed_gps_data.append((distance,track_time))
				# Get position coordinates
				pos = xmltp.find(self.xmlns + "Position")
				if not pos is None:
					if hasattr(pos.find(self.xmlns + "LatitudeDegrees"), "text") and hasattr(pos.find(self.xmlns + "LongitudeDegrees"), "text"):
						lat = float(pos.find(self.xmlns + "LatitudeDegrees").text)
						lon = float(pos.find(self.xmlns + "LongitudeDegrees").text)
						pos_data.append((lat, lon))

				# Search for Garmin Trackpoint Extensions TPX, carrying RunCadence data from Footpods
				ext=xmltp.find(self.xmlns + "Extensions")
				#logging.debug("Found Activity Extensions")
				if not ext is None:
					xmltpx=ext.find(self.xmlactextns+"TPX")
					# currenlty supported Footpod sensor
					if not xmltpx is None and xmltpx.get("CadenceSensor")=="Footpod":
						if hasattr(xmltpx.find(self.xmlactextns+"Speed"),"text"):
							speed=float(xmltpx.find(self.xmlactextns+"Speed").text)
							self.track_by_distance[distance]["speed_footpod"]=speed
							speed_foot_data.append((distance,trackpoint_time,speed))
						if hasattr(xmltpx.find(self.xmlactextns+"RunCadence"),"text"):
							# Only copy cadence data if no other Cadence data (from bike) is present
							if cad is None:
								cad = int(xmltpx.find(self.xmlactextns+"RunCadence").text)
								self.track_by_distance[distance]["cad"]=cad
								cad_data.append((distance,trackpoint_time,cad))
					#TODO: Watts sensors ???
				last_lap_distance = distance

		#logging.debug("Found a total time of %s seconds without movement (speed < 0.5m/s)" % offset_time)
		self.track_data["alt"]=alt_data
		self.track_data["cad"]=cad_data
		self.track_data["hf"]=hf_data
		self.track_data["pos"]=pos_data
		self.track_data["speed_gps"]=speed_gps_data
		self.track_data["speed_foot"]=speed_foot_data

class FITFile(ActivityFile):

	def __init__(self, track, request=None):
		ActivityFile.__init__(self, track, request)
		#logging.debug("Trackfile %r closed" % tcxfile.trackfile)

		self.fitfile = fitparse.FitFile(
			self.track.trackfile,
			data_processor=fitparse.StandardUnitsDataProcessor(),
			check_crc=False
		)

		self.parse_trackpoints()

	def to_gpx(self):
		gps_fixes = 0
		gps_no_fixes = 0
		try:
			with open(self.track.trackfile.path+".gpx", 'w') as gpx_file:
				logging.debug("Opened gpx file %s for write" % self.track.trackfile.path+".gpx")
				gpx_file.write(GPX_HEADER)

				# start gpx track
				gpx_file.write(' <trk>\n  <trkseg>\n')

				for p in self.get_pos():
					(lat, lon) = p
					if lat is None or lon is None:
						gps_no_fixes += 1
						continue
					else:
						gps_fixes += 1
					gpx_file.write('   <trkpt lat="%s" lon="%s"> </trkpt>\n' % p)

				# end gpx track
				gpx_file.write('  </trkseg>\n </trk>')
				gpx_file.write('</gpx>\n')
		except Exception, msg:
			logging.debug("Exception occured in convert: %s" % msg)

	def parse_file(self):
		self.laps = []
		self.position_start = None
		self.date = None
		self.time_start = None
		self.time_end = None
		self.position_start = None

		for message in self.fitfile.get_messages(name="session"):
			self.position_start = (message.get_value("start_position_lat"), message.get_value("start_position_long"))
			self.time_start = message.get_value("start_time")
			self.time_end = message.get_value("timestamp")

		lap_altitude = []
		for message in self.fitfile.get_messages():
			if message.name == "record":
				lap_altitude.append(message.get_value('altitude'))
			elif message.name == "lap":
				lap = Lap()
				lap.date = message.get_value("start_time").replace(tzinfo=utc)
				lap.time = message.get_value("total_timer_time")
				lap.distance = message.get_value("total_distance")/1000
				lap.elevation_gain = message.get_value("total_ascent")
				lap.elevation_loss = message.get_value("total_descent")
				if lap.elevation_gain == None:
					lap.elevation_gain = 0
				if lap.elevation_loss == None:
					lap.elevation_loss = 0

				if message.get_value("avg_running_cadence") is not None:
					lap.cadence_avg = message.get_value("avg_running_cadence") * 2	# TODO: if activity type is not running, take bike cadence
				if message.get_value("max_running_cadence") is not None:
					lap.cadence_max = message.get_value("max_running_cadence") * 2

				lap.calories = message.get_value("total_calories")
				lap.hf_avg = message.get_value("avg_heart_rate")
				lap.hf_max = message.get_value("max_heart_rate")

				if len(lap_altitude) > 0:
					lap.elevation_max = max(lap_altitude)
					lap.elevation_min = min(lap_altitude)
				lap_altitude = []

				max_speed = message.get("max_speed")
				if max_speed.units == "m/s":
					lap.speed_max = (max_speed.value * 3600.0) / 1000
				elif max_speed.units == "km/h":
					lap.speed_max = max_speed.value
				else:
					raise RuntimeError("Unknown speed unit: %s" % max_speed.units)
				avg_speed = message.get("avg_speed")
				if avg_speed is not None:
					if avg_speed.units == "m/s":
						lap.speed_avg = (avg_speed.value * 3600.0) / 1000
					elif max_speed.units == "km/h":
						lap.speed_avg = avg_speed.value
					else:
						raise RuntimeError("Unknown speed unit: %s" % max_speed.units)

				self.laps.append(lap)

	def parse_trackpoints(self):
		alt_data=[]
		cad_data=[]
		hf_data=[]
		pos_data=[]
		speed_gps_data=[]
		speed_foot_data=[]
		stance_time_data = []
		vertical_oscillation_data = []

		offset_time = 0 # used to remove track sequences from plot where no movement has occured
		last_distance = None

		for message in self.fitfile.get_messages(name="session"):
			start_time = message.get_value("start_time")
			total_strides = message.get_value("total_strides")
			if total_strides is not None:
				total_strides *= 2 				# TODO: At least when running with FR620, check with cycling
			total_distance = message.get_value("total_distance")

			if total_distance is not None and total_distance is not None and total_strides > 0:
				self.detail_entries["avg_stride_len"] = total_distance / total_strides

			if message.get_value("avg_stance_time") is not None:
				self.detail_entries["avg_stance_time"] = message.get_value("avg_stance_time")
			if message.get_value("avg_vertical_oscillation") is not None:
				self.detail_entries["avg_vertical_oscillation"] = message.get_value("avg_vertical_oscillation")
			if message.get_value("total_training_effect") is not None:
				self.detail_entries["total_training_effect"] = message.get_value("total_training_effect")

		for message in self.fitfile.get_messages(name='record'):
			distance = message.get_value("distance")
			if distance is not None:
				distance *= 1000 	# convert from km -> m
			delta = message.get_value('timestamp')-start_time
			trackpoint_time = ((delta.seconds + 86400 * delta.days)-offset_time) * 1000

 			# Find sections with speed < 0.5m/s (no real movement, remove duration of this section from timeline)
			if last_distance is not None and distance is not None:
				delta_dist = distance - last_distance
				delta_time = (trackpoint_time - self.track_by_distance[last_distance]["trackpoint_time"]) / 1000
				if delta_time > 0 and (delta_dist / delta_time) < 0.5:
					offset_time += delta_time
					trackpoint_time = ((delta.seconds + 86400 * delta.days)-offset_time) * 1000
			last_distance = distance

			if not self.track_by_distance.has_key(distance):
				self.track_by_distance[distance]={}
			self.track_by_distance[distance]["trackpoint_time"]=trackpoint_time

			# Get altitude
			alt = message.get_value("altitude")
			if alt is not None:
				self.track_by_distance[distance]["alt"]=alt
				alt_data.append((distance,trackpoint_time,alt))

# 			# Get Cadence data (from Bike cadence sensor)
			cad = message.get_value("cadence")
			if cad is not None:
				self.track_by_distance[distance]["cad"]=cad
				cad_data.append((distance,trackpoint_time,cad))

# 			# Get heart rate in beats per minute
			hf = message.get_value("heart_rate")
			if hf is not None:
				self.track_by_distance[distance]["hf"]=hf
				hf_data.append((distance,trackpoint_time,hf))
#
# 			# Get time stamps for speed calculation based on GPS
			track_time = message.get_value("timestamp")
			self.track_by_distance[distance]["gps"]=track_time
			speed_gps_data.append((distance,track_time))

# 			# Get position coordinates
			lat = message.get_value("position_lat")
			lon = message.get_value("position_long")
			if lat is not None and lon is not None:
				pos_data.append((lat, lon))

			stance_time = message.get_value("stance_time")
			if stance_time is not None:
				stance_time_data.append((distance, trackpoint_time, stance_time))
				self.track_by_distance[distance]["stance_time"] = stance_time

			vertical_oscillation = message.get_value("vertical_oscillation")
			if vertical_oscillation is not None:
				vertical_oscillation_data.append((distance, trackpoint_time, vertical_oscillation))
				self.track_by_distance[distance]["vertical_oscillation"] = vertical_oscillation

		#logging.debug("Found a total time of %s seconds without movement (speed < 0.5m/s)" % offset_time)
		self.track_data["alt"]=alt_data
		self.track_data["cad"]=cad_data
		self.track_data["hf"]=hf_data
		self.track_data["pos"]=pos_data
		self.track_data["speed_gps"]=speed_gps_data
		self.track_data["speed_foot"]=speed_foot_data
		self.track_data["stance_time"]=stance_time_data
		self.track_data["vertical_oscillation"]=vertical_oscillation_data
