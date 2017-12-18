import logging

import fitparse

from django.utils.timezone import utc

from activities.models import Lap
from ActivityFile import ActivityFile


class FITFile(ActivityFile):
	filetypes = ["fit"]

	def __init__(self, track, request=None):
		ActivityFile.__init__(self, track, request)
		# logging.debug("Trackfile %r closed" % tcxfile.trackfile)

		self.fitfile = fitparse.FitFile(
			self.track.trackfile,
			data_processor=fitparse.StandardUnitsDataProcessor(),
			check_crc=False
		)

		self.parse_trackpoints()

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
				if max_speed and max_speed.value:
					if max_speed.units == "m/s":
						lap.speed_max = (max_speed.value * 3600.0) / 1000
					elif max_speed.units == "km/h":
						lap.speed_max = max_speed.value
					else:
						raise RuntimeError("Unknown speed unit: %s" % max_speed.units)
				else:
					lap.speed_max = 0

				avg_speed = message.get("avg_speed")
				if avg_speed and avg_speed.value:
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
		detail_entry_list = ["avg_stance_time", "avg_vertical_oscillation", "total_training_effect", "normalized_power", "training_stress_score", "left_right_balance"]
		alt_data = []
		cad_data = []
		hf_data = []
		pos_data = []
		power_data = []
		speed_gps_data = []
		speed_foot_data = []
		stance_time_data = []
		temperature_data = []
		vertical_oscillation_data = []

		offset_distance = 0
		offset_time = 0  # used to remove track sequences from plot where no movement has occured
		last_distance = None

		is_wahoo = False

		for message in self.fitfile.get_messages(name="device_info"):
			manufacturer = message.get_value("manufacturer")
			if manufacturer == 'wahoo_fitness':
				is_wahoo = True

		for message in self.fitfile.get_messages(name="session"):
			start_time = message.get_value("start_time")
			total_strides = message.get_value("total_strides")
			if total_strides is not None:
				total_strides *= 2  # TODO: At least when running with FR620, check with cycling
			total_distance = message.get_value("total_distance")

			if total_distance is not None and total_distance is not None and total_strides > 0:
				self.detail_entries["avg_stride_len"] = total_distance / total_strides

			for detail_entry in detail_entry_list:
				if message.get_value(detail_entry) is not None:
					self.detail_entries[detail_entry] = message.get_value(detail_entry)

		for message in self.fitfile.get_messages(name='record'):
			distance = message.get_value("distance")
			if distance is not None:
				distance *= 1000 	# convert from km -> m
				# check if distance is less than from last trackpoint (new lap starting with distance 0 when merging fit files)
				if (distance + offset_distance) < last_distance:
					if is_wahoo:
						# skip wahoo out-of-order distance records
						continue
					offset_distance = last_distance - distance
				distance += offset_distance

			delta = message.get_value('timestamp') - start_time
			trackpoint_time = ((delta.seconds + 86400 * delta.days) - offset_time) * 1000

			# Find sections with speed < 0.5m/s (no real movement, remove duration of this section from timeline)
			if last_distance is not None and distance is not None and distance > 0:
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

			power = message.get_value("power")
			if power is not None:
				power_data.append((distance, trackpoint_time, power))
				if distance is not None:
					self.track_by_distance[distance]["power"] = power

		# logging.debug("Found a total time of %s seconds without movement (speed < 0.5m/s)" % offset_time)
		self.track_data["alt"] = alt_data
		self.track_data["cad"] = cad_data
		self.track_data["hf"] = hf_data
		self.track_data["pos"] = pos_data
		self.track_data["power"] = power_data
		self.track_data["speed_gps"] = speed_gps_data
		self.track_data["speed_foot"] = speed_foot_data
		self.track_data["stance_time"] = stance_time_data
		self.track_data["temperature"] = temperature_data
		self.track_data["vertical_oscillation"] = vertical_oscillation_data
