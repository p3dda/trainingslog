import logging
from django.utils.timezone import utc

from activities.models import Lap
from libs.fitparse import fitparse

from ActivityFile import ActivityFile

GPX_HEADER = """<gpx xmlns="http://www.topografix.com/GPX/1/1"
	creator="https://github.com/p3dda/trainingslog"
	version="1.1"
	xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
	xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">
"""


class FITFile(ActivityFile):
	filetypes = ["fit"]

	def __init__(self, track, request=None, user=None, activityname="Garmin Import"):
		ActivityFile.__init__(self, track, request, user, activityname)
		# logging.debug("Trackfile %r closed" % tcxfile.trackfile)

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
			with open(self.track.trackfile.path + ".gpx", 'w') as gpx_file:
				logging.debug("Opened gpx file %s for write" % self.track.trackfile.path + ".gpx")
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
			if message.get_value("start_position_lat") is not None and message.get_value("start_position_long") is not None:
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
				lap.distance = message.get_value("total_distance")
				if lap.distance is None:
					lap.distance = 0
				else:
					lap.distance /= 1000
				lap.elevation_gain = message.get_value("total_ascent")
				lap.elevation_loss = message.get_value("total_descent")
				if lap.elevation_gain is None:
					lap.elevation_gain = 0
				if lap.elevation_loss is None:
					lap.elevation_loss = 0

				lap.cadence_avg = message.get_value("avg_cadence")
				lap.cadence_max = message.get_value("max_cadence")
				if message.get_value("sport") == 'running':
					if lap.cadence_avg is not None:
						lap.cadence_avg *= 2
					if lap.cadence_max is not None:
						lap.cadence_max *= 2

				lap.calories = message.get_value("total_calories")
				lap.hf_avg = message.get_value("avg_heart_rate")
				lap.hf_max = message.get_value("max_heart_rate")

				if len(lap_altitude) > 0:
					lap.elevation_max = max(lap_altitude)
					lap.elevation_min = min(lap_altitude)
				lap_altitude = []

				max_speed = message.get("max_speed")
				if max_speed.value:
					if max_speed.units == "m/s":
						lap.speed_max = (max_speed.value * 3600.0) / 1000
					elif max_speed.units == "km/h":
						lap.speed_max = max_speed.value
					else:
						raise RuntimeError("Unknown speed unit: %s" % max_speed.units)
				else:
					lap.speed_max = 0

				avg_speed = message.get("avg_speed")
				if avg_speed.value:
					if avg_speed:
						if avg_speed.units == "m/s":
							lap.speed_avg = (avg_speed.value * 3600.0) / 1000
						elif max_speed.units == "km/h":
							lap.speed_avg = avg_speed.value
						else:
							raise RuntimeError("Unknown speed unit: %s" % max_speed.units)
				else:
					lap.speed_avg = 0

				self.laps.append(lap)

	def parse_trackpoints(self):
		alt_data = []
		cad_data = []
		hf_data = []
		pos_data = []
		speed_gps_data = []
		speed_foot_data = []
		stance_time_data = []
		temperature_data = []
		vertical_oscillation_data = []

		offset_distance = 0
		offset_time = 0  # used to remove track sequences from plot where no movement has occured
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
				# check if distance is less than from last trackpoint (new lap starting with distance 0 when merging fit files)
				if (distance + offset_distance) < last_distance:
					offset_distance = last_distance
				distance += offset_distance

			delta = message.get_value('timestamp') - start_time
			trackpoint_time = ((delta.seconds + 86400 * delta.days) - offset_time) * 1000

			# Find sections with speed < 0.5m/s (no real movement, remove duration of this section from timeline)
			if last_distance is not None and distance is not None:
				delta_dist = distance - last_distance
				delta_time = (trackpoint_time - self.track_by_distance[last_distance]["trackpoint_time"]) / 1000
				if delta_time > 0 and (delta_dist / delta_time) < 0.5:
					offset_time += delta_time
					trackpoint_time = ((delta.seconds + 86400 * delta.days) - offset_time) * 1000
			last_distance = distance
			if distance is not None:
				if distance not in self.track_by_distance:
					self.track_by_distance[distance] = {}
				self.track_by_distance[distance]["trackpoint_time"] = trackpoint_time

			# Get altitude
			alt = message.get_value("altitude")
			if alt is not None:
				if distance is not None:
					self.track_by_distance[distance]["alt"] = alt
				alt_data.append((distance, trackpoint_time, alt))

			# 			# Get Cadence data (from Bike cadence sensor)
			cad = message.get_value("cadence")
			if cad is not None:
				if distance is not None:
					self.track_by_distance[distance]["cad"] = cad
				cad_data.append((distance, trackpoint_time, cad))

			temperature = message.get_value("temperature")
			if temperature is not None:
				if distance is not None:
					self.track_by_distance[distance]["temperature"] = temperature
				temperature_data.append((distance, trackpoint_time, temperature))

			# 			# Get heart rate in beats per minute
			hf = message.get_value("heart_rate")
			if hf is not None:
				if distance is not None:
					self.track_by_distance[distance]["hf"] = hf
				hf_data.append((distance, trackpoint_time, hf))
			#
			# 			# Get time stamps for speed calculation based on GPS
			track_time = message.get_value("timestamp")
			if distance is not None:
				self.track_by_distance[distance]["gps"] = track_time
			speed_gps_data.append((distance, track_time))

			# 			# Get position coordinates
			lat = message.get_value("position_lat")
			lon = message.get_value("position_long")
			if lat is not None and lon is not None:
				pos_data.append((lat, lon))

			stance_time = message.get_value("stance_time")
			if stance_time is not None:
				stance_time_data.append((distance, trackpoint_time, stance_time))
				if distance is not None:
					self.track_by_distance[distance]["stance_time"] = stance_time

			vertical_oscillation = message.get_value("vertical_oscillation")
			if vertical_oscillation is not None:
				vertical_oscillation_data.append((distance, trackpoint_time, vertical_oscillation))
				if distance is not None:
					self.track_by_distance[distance]["vertical_oscillation"] = vertical_oscillation

		# logging.debug("Found a total time of %s seconds without movement (speed < 0.5m/s)" % offset_time)
		self.track_data["alt"] = alt_data
		self.track_data["cad"] = cad_data
		self.track_data["hf"] = hf_data
		self.track_data["pos"] = pos_data
		self.track_data["speed_gps"] = speed_gps_data
		self.track_data["speed_foot"] = speed_foot_data
		self.track_data["stance_time"] = stance_time_data
		self.track_data["temperature"] = temperature_data
		self.track_data["vertical_oscillation"] = vertical_oscillation_data
