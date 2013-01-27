import datetime
import dateutil.parser
import logging
import re
import time
from django.utils.timezone import utc

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


class TCXTrack:
	xmlns = "{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}"
	xmlactextns = "{http://www.garmin.com/xmlschemas/ActivityExtension/v2}"
	xml_instance = "{http://www.w3.org/2001/XMLSchema-instance}"

	def __init__(self, tcxfile):
		#logging.debug("Opening Trackfile %r" % tcxfile.trackfile)	
		tcxfile.trackfile.open()
		self.xmltree = ElementTree(file = tcxfile.trackfile)
		tcxfile.trackfile.close()
		#logging.debug("Trackfile %r closed" % tcxfile.trackfile)

		self.track_data={}
		self.track_by_distance={}
		self.parse_trackpoints()

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

		for xmltp in xmlactivity.findall(self.xmlns+"Lap/"+self.xmlns+"Track/"+self.xmlns+"Trackpoint"):
			distance=alt=cad=hf=trackpoint_time=None

			if not hasattr(xmltp.find(self.xmlns + "DistanceMeters"),"text"):
				continue
			if not hasattr(xmltp.find(self.xmlns + "Time"),"text"):
				continue

			distance = float(xmltp.find(self.xmlns + "DistanceMeters").text)
			delta = dateutil.parser.parse(xmltp.find(self.xmlns + "Time").text)-start_time
			trackpoint_time = (delta.seconds + 86400 * delta.days) * 1000
			
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

		self.track_data["alt"]=alt_data
		self.track_data["cad"]=cad_data
		self.track_data["hf"]=hf_data
		self.track_data["pos"]=pos_data
		self.track_data["speed_gps"]=speed_gps_data
		self.track_data["speed_foot"]=speed_foot_data
		
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
		if samples > 0:
			if len(self.track_data["pos"]) > samples:
				sample_size = len(self.track_data["pos"]) / samples
				return self.track_data["pos"][0::sample_size]			
		return self.track_data["pos"]
	
	def get_speed(self, pace=False):
		"""Returns list of (distance, heartrate) tuples with optional given max length
		@returns (distance, heartrate) tuples
		@rtype: list
		"""

		MAX_OFFSET=10
		MAX_OFFSET_AVG=20
		MAX_DIST=100.0
		MAX_DIST_AVG=100.0
		speed_data_pos=[]
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
					speed=speed+dist_diff/time_diff_s
					count+=1
			# if we have at least one position, store it as gps_speed
			if count>0:
				speed=speed/count
				self.track_by_distance[fix_pos]["gps_speed"]=speed
				count_avg+=1
				speed_avg=speed_avg+speed
		if count_avg>0:
			speed_avg=speed_avg/count_avg
		else:
			speed_avg=speed_avg

		max_speedchange_avg=speed_avg/3.6 # This value is currently determined for running events. Might not be a fixed value but dependent from speed_avg

		logging.debug("Speed average is %f m/s for %i data points using %f as max_speedchange_avg" % (speed_avg,count_avg,max_speedchange_avg))

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
				if cur_speed!=None:
					if abs(cur_speed-self.track_by_distance[new_pos]["gps_speed"])>max_speedchange_avg:
						continue

				speed=speed+self.track_by_distance[new_pos]["gps_speed"]
				count=count+1
			if count>0:
				speed=speed/count
				if pace:
					speed = 1000.0/60.00/speed # convert to min/km
				else:
					speed = speed*3.6 # convert to km/h
					
				speed_data.append((fix_pos,self.track_by_distance[fix_pos]["trackpoint_time"],speed))
		return speed_data

		
	def get_speed_foot(self, pace=False):
		speed_data = []
		for (distance,trackpoint_time,speed) in self.track_data["speed_foot"]:
			if pace:
				if speed==0:
					speed=0
				else:
					speed = 60 / (speed*3.6) 
			else:
				speed = speed * 3.6
				if pace and speed> 20:
					continue
			speed_data.append((distance,trackpoint_time,speed))
		return speed_data

	def get_speed_gps(self, pace=False):
		return get_speed(samples,pace)

def activities_summary(activities):
	"""returns summary dictionary for list of activities
	@param activities: list of Activities
	@type avtivities: array
	@return: Summary dictionary
	@rtype: dict
	"""
	summary=dict(num_activities = len(activities),
				total_distance = 0.0,
				total_time = 0,
				total_elev_gain = 0,
				total_calories = 0)
	
	for activity in activities:
		if activity.time:
			summary['total_time'] += activity.time
		if activity.distance:
			summary['total_distance'] += float(activity.distance)
		if activity.elevation_gain:
			summary['total_elev_gain'] += activity.elevation_gain
		if activity.calories:
			summary['total_calories'] += activity.calories
	
	summary['total_time_str'] = str(datetime.timedelta(days=0, seconds=summary['total_time']))
	return summary

def avg(sample):
	return (min(x for x, y in sample),sum(y for x,y in sample)/len(sample))

def int_or_none(val):
	try:
		return int(val)
	except ValueError:
		return None

def float_or_none(val):
	try:
		return float(val)
	except ValueError:
		return None

def str_float_or_none(val):
	ret = float_or_none(val)
	if ret:
		return str(ret)
	else:
		return None

def time_to_seconds(t_string):
	"""Converts time string to seconds
	"""
	fields = t_string.split(':')
	if len(fields)==3:
		seconds = int(fields[0])*3600 + int(fields[1])*60 + int(fields[2])
	elif len(fields)==2:
		seconds = int(fields[0])*60 + int(fields[1])
	else:
		seconds = 0
	return seconds

def seconds_to_time(seconds, force_hour=False):
	"""Converts seconds to time string
	@param seconds: Number of seconds
	@type seconds: string
	@param force_hour: Force hour even if seconds < 3600
	@type force_hour: boolean
	@return time_string
	"""
	hours = int(seconds/3600)
	minutes = int((seconds % 3600) / 60)
	seconds = (seconds % 60)
	
	if hours > 0 or force_hour:
		t_string = "%d:%02d:%02d" % (hours, minutes, seconds)
	else:
		t_string = "%d:%02d" % (minutes, seconds)
	return t_string

def pace_to_speed(val):
	"""Converts pace min/km (mm:ss) to speed (km/h)
	"""
	seconds = time_to_seconds(val)
	speed = 3600.0 / seconds
	return speed

def speed_to_pace(speed):
	"""Converts speed (km/h) float to pace [min/km] (mm:ss)
	"""
	seconds = 3600 / speed
	return seconds_to_time(seconds)
