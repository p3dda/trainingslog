from xml import sax
from xml.sax import saxutils
import os
import logging
import sys
import dateutil
import dateutil.parser

import activities.utils
from activities.models import Activity, Event, Sport, Lap
from ActivityFile import ActivityFile


found_xml_parser = False
try:
	if not found_xml_parser:
		from elementtree.ElementTree import ElementTree
except ImportError, msg:
	pass
else:
	found_xml_parser = True

try:
	if not found_xml_parser:
		from xml.etree.ElementTree import ElementTree
except ImportError, msg:
	pass
else:
	found_xml_parser = True

if not found_xml_parser:
	raise ImportError("No valid XML parsers found. Please install a Python XML parser")


class TCXFile(ActivityFile):
	filetypes = ["tcx"]

	# TCX_NS="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"
	TCX_NS = "{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}"
	xmlns = "{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}"
	xmlactextns = "{http://www.garmin.com/xmlschemas/ActivityExtension/v2}"
	xml_instance = "{http://www.w3.org/2001/XMLSchema-instance}"

	def __init__(self, track, request=None):
		ActivityFile.__init__(self, track, request)
		track.trackfile.open()
		self.xmltree = ElementTree(file=track.trackfile)
		track.trackfile.close()
		# logging.debug("Trackfile %r closed" % tcxfile.trackfile)

		self.parse_trackpoints()

	def parse_file(self):
		self.laps = []
		self.position_start = None
		self.date = None
		self.time_start = None
		self.time_end = None

		self.track.trackfile.open()
		xmltree = ElementTree(file=self.track.trackfile)
		self.track.trackfile.close()

		# take only first activity from file
		xmlactivity = xmltree.find(self.TCX_NS + "Activities")[0]

		lap_date = None

		for xmllap in xmlactivity.findall(self.TCX_NS + "Lap"):
			lap_date = dateutil.parser.parse(xmllap.get("StartTime"))
			if self.date is None:
				self.date = lap_date

			time = int(float(xmllap.find(self.TCX_NS + "TotalTimeSeconds").text))
			if xmllap.find(self.TCX_NS + "DistanceMeters") is None:
				logging.debug("DistanceMeters not present in Lap data")
				distance = None
			else:
				distance = str(float(xmllap.find(self.TCX_NS + "DistanceMeters").text) / 1000)
			if xmllap.find(self.TCX_NS + "MaximumSpeed") is None:
				logging.debug("MaximumSpeed is None")
				speed_max = None
			else:
				logging.debug("MaximumSpeed xml is %r" % xmllap.find(self.TCX_NS + "MaximumSpeed"))
				speed_max = str(float(xmllap.find(self.TCX_NS + "MaximumSpeed").text) * 3.6)  # Given as meters per second in tcx file
				logging.debug("speed_max is %s" % speed_max)
			if xmllap.find(self.TCX_NS + "Calories") is not None:
				calories = int(xmllap.find(self.TCX_NS + "Calories").text)
			else:
				calories = None
			try:
				hf_avg = int(xmllap.find(self.TCX_NS + "AverageHeartRateBpm").find(self.TCX_NS + "Value").text)
				logging.debug("Found hf_avg: %s" % hf_avg)
			except AttributeError:
				hf_avg = None
				logging.debug("Not found hf_avg")
			try:
				hf_max = int(xmllap.find(self.TCX_NS + "MaximumHeartRateBpm").find(self.TCX_NS + "Value").text)
				logging.debug("Found hf_max: %s" % hf_max)
			except AttributeError:
				hf_max = None
				logging.debug("Not found hf_max")
			try:
				cadence_avg = int(xmllap.find(self.TCX_NS + "Cadence").text)
				logging.debug("Found average cadence: %s" % cadence_avg)
			except AttributeError:
				cadence_avg = None
				logging.debug("Not found average cadence")

			if time != 0 and distance is not None:
				speed_avg = str(float(distance) * 3600 / time)
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
							if xmlpos.find(self.TCX_NS + "LatitudeDegrees") is not None and xmlpos.find(self.TCX_NS + "LongitudeDegrees") is not None:
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

					if xmltp.find(self.TCX_NS + "Cadence") is not None:
						cadence = int(xmltp.find(self.TCX_NS + "Cadence").text)
						if cadence > cadence_max:
							cadence_max = cadence

				# Get timestamp from last trackpoint in this track
				xmltp = xmltrack.findall(self.TCX_NS + "Trackpoint")[-1]
				if xmltp.find(self.TCX_NS + "Time") is not None:
					self.time_end = dateutil.parser.parse(xmltp.find(self.TCX_NS + "Time").text)

			speed_max = str(min(float(speed_max), 999.9))

			lap = Lap(
				date=lap_date,
				time=time,
				distance=distance,
				elevation_gain=elev_gain,
				elevation_loss=elev_loss,
				elevation_min=elev_min,
				elevation_max=elev_max,
				speed_max=speed_max,
				speed_avg=speed_avg,
				cadence_avg=cadence_avg,
				cadence_max=cadence_max,
				calories=calories,
				hf_max=hf_max,
				hf_avg=hf_avg)

			self.laps.append(lap)

	def parse_trackpoints(self):
		# take only first activity from file
		xmlactivity = self.xmltree.find(self.xmlns + "Activities")[0]

		alt_data = []
		cad_data = []
		hf_data = []
		pos_data = []
		speed_gps_data = []
		speed_foot_data = []
		# logging.debug("Parsing TCX Track file in first activity")
		first_lap = xmlactivity.find(self.xmlns + "Lap")
		start_time = dateutil.parser.parse(first_lap.get("StartTime"))
		offset_time = 0  # used to remove track sequences from plot where no movement has occured
		last_lap_distance = 0  # used to add distance to laps starting with distance 0
		last_distance = None
		last_lat_lon = None

		for xmllap in xmlactivity.findall(self.xmlns + "Lap"):
			distance_offset = 0
			# check if lap starts with distance 0
			if len(xmllap.findall(self.xmlns + "Track/" + self.xmlns + "Trackpoint")) == 0:
				continue		# skip empty laps
			xmltp = xmllap.findall(self.xmlns + "Track/" + self.xmlns + "Trackpoint")[0]
			if hasattr(xmltp.find(self.xmlns + "DistanceMeters"), "text"):
				distance = float(xmltp.find(self.xmlns + "DistanceMeters").text)
				if distance < last_lap_distance:
					distance_offset = last_lap_distance

			for xmltp in xmllap.findall(self.xmlns + "Track/" + self.xmlns + "Trackpoint"):
				distance = alt = cad = hf = trackpoint_time = None

				if hasattr(xmltp.find(self.xmlns + "DistanceMeters"), "text"):
					distance = float(xmltp.find(self.xmlns + "DistanceMeters").text)
					distance = distance + distance_offset
				elif xmltp.find(self.xmlns + "Position"):
					xmltp_pos = xmltp.find(self.xmlns + "Position")
					lat = float(xmltp_pos.find(self.xmlns + "LatitudeDegrees").text)
					lon = float(xmltp_pos.find(self.xmlns + "LongitudeDegrees").text)
					if last_lat_lon is None:
						last_lat_lon = (lat, lon)
						last_distance = 0
						continue
					else:
						distance = last_distance + activities.utils.latlon_distance(last_lat_lon, (lat, lon))
						last_lat_lon = (lat, lon)
				else:
					continue
				if not hasattr(xmltp.find(self.xmlns + "Time"), "text"):
					continue

				delta = dateutil.parser.parse(xmltp.find(self.xmlns + "Time").text) - start_time
				trackpoint_time = ((delta.seconds + 86400 * delta.days) - offset_time) * 1000

				# Find sections with speed < 0.5m/s (no real movement, remove duration of this section from timeline)
				if last_distance:
					delta_dist = distance - last_distance
					delta_time = (trackpoint_time - self.track_by_distance[last_distance]["trackpoint_time"]) / 1000
					if delta_time > 0 and (delta_dist / delta_time) < 0.5:
						offset_time += delta_time
						trackpoint_time = ((delta.seconds + 86400 * delta.days) - offset_time) * 1000
				last_distance = distance

				if distance not in self.track_by_distance:
					self.track_by_distance[distance] = {}
				self.track_by_distance[distance]["trackpoint_time"] = trackpoint_time

				# Get altitude
				if hasattr(xmltp.find(self.xmlns + "AltitudeMeters"), "text"):
					alt = float(xmltp.find(self.xmlns + "AltitudeMeters").text)
					self.track_by_distance[distance]["alt"] = alt
					# alt_data.append((trackpoint_time,alt))
					alt_data.append((distance, trackpoint_time, alt))
				# Get Cadence data (from Bike cadence sensor)
				if hasattr(xmltp.find(self.xmlns + "Cadence"), "text"):
					cad = int(xmltp.find(self.xmlns + "Cadence").text)
					self.track_by_distance[distance]["cad"] = cad
					# cad_data.append((trackpoint_time,cad))
					cad_data.append((distance, trackpoint_time, cad))

				# Locate heart rate in beats per minute
				hrt = xmltp.find(self.xmlns + "HeartRateBpm")
				if hrt is not None:
					if hasattr(xmltp.find(self.xmlns + "HeartRateBpm/" + self.xmlns + "Value"), "text"):
						hf = int(xmltp.find(self.xmlns + "HeartRateBpm/" + self.xmlns + "Value").text)
						self.track_by_distance[distance]["hf"] = hf
						# hf_data.append((trackpoint_time,hf))
						hf_data.append((distance, trackpoint_time, hf))

				# Locate time stamps for speed calculation based on GPS
				if hasattr(xmltp.find(self.xmlns + "Time"), "text"):
					track_time = dateutil.parser.parse(xmltp.find(self.xmlns + "Time").text)
					self.track_by_distance[distance]["gps"] = track_time
					speed_gps_data.append((distance, track_time))
				# Get position coordinates
				pos = xmltp.find(self.xmlns + "Position")
				if pos is not None:
					if hasattr(pos.find(self.xmlns + "LatitudeDegrees"), "text") and hasattr(pos.find(self.xmlns + "LongitudeDegrees"), "text"):
						lat = float(pos.find(self.xmlns + "LatitudeDegrees").text)
						lon = float(pos.find(self.xmlns + "LongitudeDegrees").text)
						pos_data.append((lat, lon))

				# Search for Garmin Trackpoint Extensions TPX, carrying RunCadence data from Footpods
				ext = xmltp.find(self.xmlns + "Extensions")
				# logging.debug("Found Activity Extensions")
				if ext is not None:
					xmltpx = ext.find(self.xmlactextns + "TPX")
					# currenlty supported Footpod sensor
					if xmltpx is not None and xmltpx.get("CadenceSensor") == "Footpod":
						if hasattr(xmltpx.find(self.xmlactextns + "Speed"), "text"):
							speed = float(xmltpx.find(self.xmlactextns + "Speed").text)
							self.track_by_distance[distance]["speed_footpod"] = speed
							speed_foot_data.append((distance, trackpoint_time, speed))
						if hasattr(xmltpx.find(self.xmlactextns + "RunCadence"), "text"):
							# Only copy cadence data if no other Cadence data (from bike) is present
							if cad is None:
								cad = int(xmltpx.find(self.xmlactextns + "RunCadence").text)
								self.track_by_distance[distance]["cad"] = cad
								cad_data.append((distance, trackpoint_time, cad))
							# TODO: Watts sensors ???
				last_lap_distance = distance

		# logging.debug("Found a total time of %s seconds without movement (speed < 0.5m/s)" % offset_time)
		self.track_data["alt"] = alt_data
		self.track_data["cad"] = cad_data
		self.track_data["hf"] = hf_data
		self.track_data["pos"] = pos_data
		self.track_data["speed_gps"] = speed_gps_data
		self.track_data["speed_foot"] = speed_foot_data
