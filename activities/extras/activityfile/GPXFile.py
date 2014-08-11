import shutil
from django.utils.timezone import utc

from libs.gpxpy import gpxpy
from activities.models import Lap
from ActivityFile import ActivityFile

class GPXFile(ActivityFile):
	filetypes = ["gpx"]

	def __init__(self, track, request=None):
		ActivityFile.__init__(self, track, request)
		self.gpxfile = gpxpy.parse(self.track.trackfile)
		self.parse_trackpoints()

	def to_gpx(self):
		shutil.copy(self.track.trackfile.path, self.track.trackfile.path+".gpx")

	def parse_file(self):
		self.laps = []
		self.position_start = None
		self.date = None
		self.time_start = None
		self.time_end = None
		self.position_start = None

		if len(self.gpxfile.tracks) >= 1:
			track = self.gpxfile.tracks[0]
		else:
			raise RuntimeError("No track found in gpx file")

		# this is start of activity, get timestamp and all other activity related data
		for segment in track.segments:
			# start of a lap
			lap = Lap()
			time_bounds = segment.get_time_bounds()
			moving_data = segment.get_moving_data(stopped_speed_threshold=0.5)
			up_down = segment.get_uphill_downhill()
			elev_min_max = segment.get_elevation_extremes()

			lap.date = time_bounds.start_time.replace(tzinfo=utc)
			lap.time = int(moving_data.moving_time)
			lap.distance = round(moving_data.moving_distance / 1000, 3)
			lap.elevation_gain = int(up_down.uphill)
			lap.elevation_loss = int(up_down.downhill)
			lap.elevation_min = int(elev_min_max.minimum)
			lap.elevation_max = int(elev_min_max.maximum)
			lap.speed_max = moving_data.max_speed
			if lap.time > 0:
				lap.speed_avg = lap.distance / lap.time
			lap.speed_avg = round(lap.speed_avg * 3.6, 1)
			lap.speed_max = round(lap.speed_max * 3.6, 1)

			self.laps.append(lap)

		self.time_start = track.segments[0].points[0].time
		self.time_end = track.segments[-1].points[-1].time
		start_point = track.segments[0].points[0]
		self.position_start = (start_point.latitude, start_point.longitude)

	def parse_trackpoints(self):
		alt_data=[]
		pos_data=[]
		speed_gps_data=[]

		offset_distance = 0
		offset_time = 0 # used to remove track sequences from plot where no movement has occured
		last_distance = None

		trackpoints = []
		if len(self.gpxfile.tracks) >= 1:
			track = self.gpxfile.tracks[0]
		else:
			raise RuntimeError("No track found in gpx file")
		for segment in track.segments:
			trackpoints += segment.points

		start_time = trackpoints[0].time
		last_point = None

		#for trackpoint in trackpoints:
		for tp_id, trackpoint in enumerate(trackpoints):
			if last_point is None:
				distance = 0
			else:
				distance = trackpoint.distance_3d(last_point)

			if distance is not None:
				# check if distance is less than from last trackpoint (new lap starting with distance 0 when merging fit files)
				if (distance + offset_distance) < last_distance:
					offset_distance = last_distance
				distance += offset_distance

			if trackpoint.time is not None:
				# calculate time difference from start_time in msec
				delta = trackpoint.time - start_time
				trackpoint_time = ((delta.seconds + 86400 * delta.days)-offset_time) * 1000
				last_known_time = trackpoint_time  # backup time for trackpoints without timestamp

				# Find sections with speed < 0.5m/s (no real movement, remove duration of this section from timeline)
				if last_distance is not None and distance is not None:
					delta_dist = distance - last_distance
					delta_time = (trackpoint_time - self.track_by_distance[last_distance]["trackpoint_time"]) / 1000
					if delta_time > 0 and (delta_dist / delta_time) < 0.5:
						offset_time += delta_time
						trackpoint_time = ((delta.seconds + 86400 * delta.days)-offset_time) * 1000  # recalculate difference from start_time
			else:
				# Trackpoint has no timestamp. Find next trackpoint with timestamp and assign average
				# delta timestamps to the trackpoints in between
				tp_without_time = 0
				avg_delta = 0
				for (sub_id, subtrackpoint) in enumerate(trackpoints[tp_id:]):
					if subtrackpoint.time is not None:
						# found next trackpoint with timestamp, calculate avg. time delta
						tp_without_time = sub_id
						tp_delta = (subtrackpoint.time - last_point.time)
						avg_delta = tp_delta / tp_without_time
						break
				for (sub_id, subtrackpoint) in enumerate(trackpoints[tp_id:tp_id+tp_without_time]):
					if subtrackpoint.time is None:
						# assign calculated timestamps
						subtrackpoint.time = last_point.time + avg_delta * (sub_id + 1)

			last_distance = distance
			if distance is not None:
				if not self.track_by_distance.has_key(distance):
					self.track_by_distance[distance]={}
				self.track_by_distance[distance]["trackpoint_time"]=trackpoint_time

			# Get altitude
			alt = trackpoint.elevation
			if alt is not None:
				if distance is not None:
					self.track_by_distance[distance]["alt"]=alt
				alt_data.append((distance,trackpoint_time,alt))

			# 			# Get time stamps for speed calculation based on GPS
			track_time = trackpoint.time
			if distance is not None:
				self.track_by_distance[distance]["gps"]=track_time
			speed_gps_data.append((distance,track_time))

			# 			# Get position coordinates
			lat = trackpoint.latitude
			lon = trackpoint.longitude
			if lat is not None and lon is not None:
				pos_data.append((lat, lon))

			last_point = trackpoint

		#logging.debug("Found a total time of %s seconds without movement (speed < 0.5m/s)" % offset_time)
		self.track_data["alt"]=alt_data
		self.track_data["pos"]=pos_data
		self.track_data["speed_gps"]=speed_gps_data

