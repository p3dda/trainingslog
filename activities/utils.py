import datetime
import math

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


def latlon_distance(origin, destination):
	"""Calculate distance between two gps coordinates
	@param origin: Origin gps coordinates (lat, lon)
	@type origin: tuple
	@param destination: Destination gps coordinates (lat, lon)
	@type destination: tuple
	@return: distance (meters)
	@rtype: float
	"""
	lat1, lon1 = origin
	lat2, lon2 = destination
	radius = 6371000  # m

	dlat = math.radians(lat2 - lat1)
	dlon = math.radians(lon2 - lon1)
	a = math.sin(dlat / 2) * math.sin(dlat / 2) + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) * math.sin(dlon / 2)
	c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
	d = radius * c

	return d


def activities_summary(activities):
	"""returns summary dictionary for list of activities
	@param activities: list of Activities
	@type activities: array
	@return: Summary dictionary
	@rtype: dict
	"""
	summary = dict(num_activities=len(activities),
				total_distance=0.0,
				total_time=0,
				total_elev_gain=0,
				total_calories=0)

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
	return min(x for x, y in sample), sum(y for x, y in sample) / len(sample)


def int_or_none(val):
	try:
		return int(val)
	except (ValueError, TypeError):
		return None


def float_or_none(val):
	try:
		return float(val)
	except (ValueError, TypeError):
		return None


def str_float_or_none(val):
	ret = float_or_none(val)
	if ret is not None:
		return str(ret)
	else:
		return None


def time_to_seconds(t_string):
	"""Converts time string to seconds
	"""
	fields = t_string.split(':')
	if len(fields) == 3:
		seconds = int(fields[0]) * 3600 + int(fields[1]) * 60 + int(fields[2])
	elif len(fields) == 2:
		seconds = int(fields[0]) * 60 + int(fields[1])
	else:
		seconds = 0
	return seconds


def seconds_to_time(seconds, force_hour=False):
	"""Converts seconds to time string
	@param seconds: Number of seconds
	@type seconds: integer
	@param force_hour: Force hour even if seconds < 3600
	@type force_hour: boolean
	@return time_string
	"""
	hours = int(seconds / 3600)
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
	if isinstance(val, basestring):
		seconds = time_to_seconds(val)
	elif isinstance(val, float):
		seconds = val * 60
	else:
		raise ValueError("Bad value for pace_to_speed conversion: %s with type %s" % (val, type(val)))
	speed = 3600.0 / seconds
	return speed


def speed_to_pace(speed):
	"""Converts speed (km/h) float to pace [min/km] (mm:ss)
	"""
	seconds = 3600 / speed
	return seconds_to_time(seconds)
