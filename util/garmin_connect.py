#!/usr/bin/env python

#import pytz
from datetime import datetime, timedelta
import requests
#import os
#import math
import logging
import json
import re
import shutil
#import random
import tempfile
#from urllib.parse import urlencode

logger = logging.getLogger(__name__)

GC_USER = "FIXME"
GC_PASS = "FIXME"

class GarminConnectService(object):
	ID = "garminconnect"
	DisplayName = "Garmin Connect"
	DisplayAbbreviation = "GC"
	#AuthenticationType = ServiceAuthenticationType.UsernamePassword
	#RequiresExtendedAuthorizationDetails = True
	#PartialSyncRequiresTrigger = len(GARMIN_CONNECT_USER_WATCH_ACCOUNTS) > 0
	#PartialSyncTriggerPollInterval = timedelta(minutes=20)
	#PartialSyncTriggerPollMultiple = len(GARMIN_CONNECT_USER_WATCH_ACCOUNTS.keys())

	ConfigurationDefaults = {
		"WatchUserKey": None,
		"WatchUserLastID": 0
	}
	#
	# _activityMappings = {
	# 	"running": ActivityType.Running,
	# 	"cycling": ActivityType.Cycling,
	# 	"mountain_biking": ActivityType.MountainBiking,
	# 	"walking": ActivityType.Walking,
	# 	"hiking": ActivityType.Hiking,
	# 	"resort_skiing_snowboarding": ActivityType.DownhillSkiing,
	# 	"cross_country_skiing": ActivityType.CrossCountrySkiing,
	# 	"skate_skiing": ActivityType.CrossCountrySkiing,  # Well, it ain't downhill?
	# 	"backcountry_skiing_snowboarding": ActivityType.CrossCountrySkiing,  # ish
	# 	"skating": ActivityType.Skating,
	# 	"swimming": ActivityType.Swimming,
	# 	"rowing": ActivityType.Rowing,
	# 	"elliptical": ActivityType.Elliptical,
	# 	"fitness_equipment": ActivityType.Gym,
	# 	"mountaineering": ActivityType.Climbing,
	# 	"all": ActivityType.Other,  # everything will eventually resolve to this
	# 	"multi_sport": ActivityType.Other  # Most useless type? You decide!
	# }

	_obligatory_headers = {
		"Referer": "http://FIXME"
	}

	def __init__(self):
		# rawHierarchy = requests.get("https://connect.garmin.com/proxy/activity-service-1.2/json/activity_types", headers=self._obligatory_headers).text
		rate_lock_path = tempfile.gettempdir() + "/gc_rate.lock"
		# Ensure the rate lock file exists (...the easy way)
		open(rate_lock_path, "a").close()
		self._rate_lock = open(rate_lock_path, "r+")
		self.service_record = None
		self.session = None

	def _rate_limit(self):
		import fcntl, struct, time

		min_period = 1  # I appear to been banned from Garmin Connect while determining this.
		fcntl.flock(self._rate_lock, fcntl.LOCK_EX)
		try:
			self._rate_lock.seek(0)
			last_req_start = self._rate_lock.read()
			if not last_req_start:
				last_req_start = 0
			else:
				last_req_start = float(last_req_start)

			wait_time = max(0, min_period - (time.time() - last_req_start))
			time.sleep(wait_time)

			self._rate_lock.seek(0)
			self._rate_lock.write(str(time.time()))
			self._rate_lock.flush()
		finally:
			fcntl.flock(self._rate_lock, fcntl.LOCK_UN)

	def _get_session(self, email=None, password=None, force=False):
		if self.session is not None and force is False:
			return
		email = GC_USER
		password = GC_PASS

		self.session = requests.Session()

		# JSIG CAS, cool I guess.
		# Not quite OAuth though, so I'll continue to collect raw credentials.
		# Commented stuff left in case this ever breaks because of missing parameters...
		data = {
			"username": email,
			"password": password,
			"_eventId": "submit",
			"embed": "true",
			# "displayNameRequired": "false"
		}
		params = {
			"service": "https://connect.garmin.com/post-auth/login",
			# "redirectAfterAccountLoginUrl": "http://connect.garmin.com/post-auth/login",
			# "redirectAfterAccountCreationUrl": "http://connect.garmin.com/post-auth/login",
			# "webhost": "olaxpw-connect00.garmin.com",
			"clientId": "GarminConnect",
			# "gauthHost": "https://sso.garmin.com/sso",
			# "rememberMeShown": "true",
			# "rememberMeChecked": "false",
			"consumeServiceTicket": "false",
			# "id": "gauth-widget",
			# "embedWidget": "false",
			# "cssUrl": "https://static.garmincdn.com/com.garmin.connect/ui/src-css/gauth-custom.css",
			# "source": "http://connect.garmin.com/en-US/signin",
			# "createAccountShown": "true",
			# "openCreateAccount": "false",
			# "usernameShown": "true",
			# "displayNameShown": "false",
			# "initialFocus": "true",
			# "locale": "en"
		}
		# I may never understand what motivates people to mangle a perfectly good protocol like HTTP in the ways they do...
		preResp = self.session.get("https://sso.garmin.com/sso/login", params=params)
		if preResp.status_code != 200:
			raise RuntimeError("SSO prestart error %s %s" % (preResp.status_code, preResp.text))
		data["lt"] = re.search("name=\"lt\"\s+value=\"([^\"]+)\"", preResp.text).groups(1)[0]

		ssoResp = self.session.post("https://sso.garmin.com/sso/login", params=params, data=data, allow_redirects=False)
		if ssoResp.status_code != 200 or "temporarily unavailable" in ssoResp.text:
			raise RuntimeError("SSO error %s %s" % (ssoResp.status_code, ssoResp.text))

		ticket_match = re.search("ticket=([^']+)'", ssoResp.text)
		if not ticket_match:
			raise RuntimeError("Invalid login")
		ticket = ticket_match.groups(1)[0]

		# ...AND WE'RE NOT DONE YET!

		self._rate_limit()
		gcRedeemResp = self.session.get("https://connect.garmin.com/post-auth/login", params={"ticket": ticket}, allow_redirects=False)
		if gcRedeemResp.status_code != 302:
			raise RuntimeError("GC redeem-start error %s %s" % (gcRedeemResp.status_code, gcRedeemResp.text))

		# There are 6 redirects that need to be followed to get the correct cookie
		# ... :(
		expected_redirect_count = 6
		current_redirect_count = 1
		while True:
			self._rate_limit()
			gcRedeemResp = self.session.get(gcRedeemResp.headers["location"], allow_redirects=False)

			if current_redirect_count >= expected_redirect_count and gcRedeemResp.status_code != 200:
				raise RuntimeError("GC redeem %d/%d error %s %s" % (current_redirect_count, expected_redirect_count, gcRedeemResp.status_code, gcRedeemResp.text))
			if gcRedeemResp.status_code == 200 or gcRedeemResp.status_code == 404:
				break
			current_redirect_count += 1
			if current_redirect_count > expected_redirect_count:
				break

		# self._sessionCache.Set(record.ExternalID if record else email, session)

		self.session.headers.update(self._obligatory_headers)

	def Authorize(self, email=GC_USER, password=GC_PASS):
		self._get_session(email=email, password=password)
		# TODO: http://connect.garmin.com/proxy/userprofile-service/socialProfile/ has the proper immutable user ID, not that anyone ever changes this one...
		self._rate_limit()
		username_data = self.session.get("http://connect.garmin.com/user/username")
		# print("authorized user_name data is %s" % username_data.text)
		username_dict = json.loads(username_data.text)
		assert "username" in username_dict
		username = username_dict["username"]
		# print("user_name is %s" % username)

		if not len(username):
			raise RuntimeError("Unable to retrieve username")
		self.service_record = (username, {}, {"Email": email, "Password": password})

	def UserUploadedActivityURL(self, uploadId):
		return "https://connect.garmin.com/modern/activity/%d" % uploadId

	def DownloadActivityList(self, exhaustive=False):
		# http://connect.garmin.com/proxy/activity-search-service-1.0/json/activities?&start=0&limit=50
		act_ids = []
		# session = self._get_session()
		page = 1
		pageSz = 20
		activities = []
		exclusions = []
		while True:
			logger.debug("Req with " + str({"start": (page - 1) * pageSz, "limit": pageSz}))
			self._rate_limit()

			retried_auth = False
			while True:
				#res = session.get("https://connect.garmin.com/modern/proxy/activity-search-service-1.0/json/activities", params={"start": (page - 1) * pageSz, "limit": pageSz})
				res = self.session.get("https://connect.garmin.com/modern/proxy/activity-search-service-1.1/json/activities", params={"limit": pageSz, "start": (page-1)*pageSz, "beginTimestamp>": "2015-04-20T03:00:00"})
				# It's 10 PM and I have no clue why it's throwing these errors, maybe we just need to log in again?
				if res.status_code in [500, 403] and not retried_auth:
					logger.debug("Retrying auth w/o cache")
					retried_auth = True
					self._get_session(skip_cache=True)
				else:
					break
			try:
				res_dict = json.loads(res.text)
				assert "results" in res_dict
				res = res_dict["results"]
			except ValueError:
				res_txt = res.text  # So it can capture in the log message
				raise RuntimeError("Parse failure in GC list resp: %s - %s" % (res.status_code, res.text))
			if "activities" not in res:
				break  # No activities on this page - empty account.
			logger.debug("Found %i activities" % len(res["activities"]))
			for act in res["activities"]:
			 	act = act["activity"]
				print "found activity id", act["activityId"]
				act_ids.append(int(act["activityId"]))
			# 	# activity = UploadedActivity()
			#
			# 	# Don't really know why sumSampleCountTimestamp doesn't appear in swim activities - they're definitely timestamped...
			# 	activity.Stationary = "sumSampleCountSpeed" not in act and "sumSampleCountTimestamp" not in act
			# 	activity.GPS = "endLatitude" in act
			#
			# 	activity.Private = act["privacy"]["key"] == "private"
			#
			# 	try:
			# 		activity.TZ = pytz.timezone(act["activityTimeZone"]["key"])
			# 	except pytz.exceptions.UnknownTimeZoneError:
			# 		activity.TZ = pytz.FixedOffset(float(act["activityTimeZone"]["offset"]) * 60)
			#
			# 	logger.debug("Name " + act["activityName"]["value"] + ":")
			# 	if len(act["activityName"]["value"].strip()) and act["activityName"]["value"] != "Untitled":  # This doesn't work for internationalized accounts, oh well.
			# 		activity.Name = act["activityName"]["value"]
			#
			# 	if len(act["activityDescription"]["value"].strip()):
			# 		activity.Notes = act["activityDescription"]["value"]
			#
			# 	# beginTimestamp/endTimestamp is in UTC
			# 	activity.StartTime = pytz.utc.localize(datetime.utcfromtimestamp(float(act["beginTimestamp"]["millis"]) / 1000))
			# 	if "sumElapsedDuration" in act:
			# 		activity.EndTime = activity.StartTime + timedelta(0, round(float(act["sumElapsedDuration"]["value"])))
			# 	elif "sumDuration" in act:
			# 		activity.EndTime = activity.StartTime + timedelta(minutes=float(act["sumDuration"]["minutesSeconds"].split(":")[0]), seconds=float(act["sumDuration"]["minutesSeconds"].split(":")[1]))
			# 	else:
			# 		activity.EndTime = pytz.utc.localize(datetime.utcfromtimestamp(float(act["endTimestamp"]["millis"]) / 1000))
			# 	logger.debug("Activity s/t " + str(activity.StartTime) + " on page " + str(page))
			# 	activity.AdjustTZ()
			#
			# 	if "sumDistance" in act and float(act["sumDistance"]["value"]) != 0:
			# 		activity.Stats.Distance = ActivityStatistic(self._unitMap[act["sumDistance"]["uom"]], value=float(act["sumDistance"]["value"]))
			#
			# 	if "device" in act and act["device"]["key"] != "unknown":
			# 		devId = DeviceIdentifier.FindMatchingIdentifierOfType(DeviceIdentifierType.GC, {"Key": act["device"]["key"]})
			# 		ver_split = act["device"]["key"].split(".")
			# 		ver_maj = None
			# 		ver_min = None
			# 		if len(ver_split) == 4:
			# 			# 2.90.0.0
			# 			ver_maj = int(ver_split[0])
			# 			ver_min = int(ver_split[1])
			# 		activity.Device = Device(devId, verMaj=ver_maj, verMin=ver_min)
			#
			# 	activity.Type = self._resolveActivityType(act["activityType"]["key"])
			#
			# 	activity.CalculateUID()
			#
			# 	activity.ServiceData = {"ActivityID": int(act["activityId"])}
			#
			# 	activities.append(activity)
			logger.debug("Finished page " + str(page) + " of " + str(res["search"]["totalPages"]))
			if not exhaustive or int(res["search"]["totalPages"]) == page:
				break
			else:
				page += 1
		return act_ids

	def _downloadActivitySummary(self, activity):
		activityID = activity.ServiceData["ActivityID"]
		# session = self._get_session()
		self._rate_limit()
		res = self.session.get("https://connect.garmin.com/modern/proxy/activity-service-1.3/json/activity/" + str(activityID))

		try:
			raw_data = res.json()
		except ValueError:
			raise RuntimeError("Failure downloading activity summary %s:%s" % (res.status_code, res.text))

	def DownloadActivityFile(self, act_id):
		# session = self._get_session()
		tmpfile = tempfile.NamedTemporaryFile(mode="wb", delete=False)
		tmpfilename = tmpfile.name
		tmpdirname = tempfile.mkdtemp()
		self._rate_limit()
		response = self.session.get("%s/%s" % ("http://connect.garmin.com/proxy/download-service/files/activity", act_id))
		if response.ok:
			shutil.copyfileobj(response.raw, tmpfile)
		else:
			raise RuntimeError("Failed to download file from Garmin Connect for activity %s" % act_id)
		tmpfile.close()

	def DownloadActivity(self, activity):
		# First, download the summary stats and lap stats
		self._downloadActivitySummary( activity)

		if len(activity.Laps) == 1:
			activity.Stats = activity.Laps[0].Stats  # They must be identical to pass the verification

		if activity.Stationary:
			# Nothing else to download
			return activity

		# https://connect.garmin.com/proxy/activity-service-1.3/json/activityDetails/####
		activityID = activity.ServiceData["ActivityID"]
		# session = self._get_session()
		self._rate_limit()
		res = self.session.get("https://connect.garmin.com/modern/proxy/activity-service-1.3/json/activityDetails/" + str(activityID) + "?maxSize=999999999")
		try:
			raw_data = res.json()["com.garmin.activity.details.json.ActivityDetails"]
		except ValueError:
			raise RuntimeError("Activity data parse error for %s: %s" % (res.status_code, res.text))

		if "measurements" not in raw_data:
			activity.Stationary = True  # We were wrong, oh well
			return activity

		# attrs_map = {}
		#
		# def _map_attr(gc_key, wp_key, units, in_location=False, is_timestamp=False):
		# 	attrs_map[gc_key] = {
		# 		"key": wp_key,
		# 		"to_units": units,
		# 		"in_location": in_location,  # Blegh
		# 		"is_timestamp": is_timestamp  # See above
		# 	}
		#
		# _map_attr("directSpeed", "Speed", ActivityStatisticUnit.MetersPerSecond)
		# _map_attr("sumDistance", "Distance", ActivityStatisticUnit.Meters)
		# _map_attr("directHeartRate", "HR", ActivityStatisticUnit.BeatsPerMinute)
		# _map_attr("directBikeCadence", "Cadence", ActivityStatisticUnit.RevolutionsPerMinute)
		# _map_attr("directDoubleCadence", "RunCadence", ActivityStatisticUnit.StepsPerMinute)  # 2*x mystery solved
		# _map_attr("directAirTemperature", "Temp", ActivityStatisticUnit.DegreesCelcius)
		# _map_attr("directPower", "Power", ActivityStatisticUnit.Watts)
		# _map_attr("directElevation", "Altitude", ActivityStatisticUnit.Meters, in_location=True)
		# _map_attr("directLatitude", "Latitude", None, in_location=True)
		# _map_attr("directLongitude", "Longitude", None, in_location=True)
		# _map_attr("directTimestamp", "Timestamp", None, is_timestamp=True)
		#
		# # Figure out which metrics we'll be seeing in this activity
		# attrs_indexed = {}
		# attr_count = len(raw_data["measurements"])
		# for measurement in raw_data["measurements"]:
		# 	key = measurement["key"]
		# 	if key in attrs_map:
		# 		if attrs_map[key]["to_units"]:
		# 			attrs_map[key]["from_units"] = self._unitMap[measurement["unit"]]
		# 			if attrs_map[key]["to_units"] == attrs_map[key]["from_units"]:
		# 				attrs_map[key]["to_units"] = attrs_map[key]["from_units"] = None
		# 		attrs_indexed[measurement["metricsIndex"]] = attrs_map[key]
		#
		# # Process the data frames
		# frame_idx = 0
		# active_lap_idx = 0
		# for frame in raw_data["metrics"]:
		# 	wp = Waypoint()
		# 	for idx, attr in attrs_indexed.items():
		# 		value = frame["metrics"][idx]
		# 		target_obj = wp
		# 		if attr["in_location"]:
		# 			if not wp.Location:
		# 				wp.Location = Location()
		# 			target_obj = wp.Location
		#
		# 		# Handle units
		# 		if attr["is_timestamp"]:
		# 			value = pytz.utc.localize(datetime.utcfromtimestamp(value / 1000))
		# 		elif attr["to_units"]:
		# 			value = ActivityStatistic.convertValue(value, attr["from_units"], attr["to_units"])
		#
		# 		# Write the value (can't use __dict__ because __slots__)
		# 		setattr(target_obj, attr["key"], value)
		#
		# 	# Fix up lat/lng being zero (which appear to represent missing coords)
		# 	if wp.Location and wp.Location.Latitude == 0 and wp.Location.Longitude == 0:
		# 		wp.Location.Latitude = None
		# 		wp.Location.Longitude = None
		# 	# Please visit a physician before complaining about this
		# 	if wp.HR == 0:
		# 		wp.HR = None
		# 	# Bump the active lap if required
		# 	while (active_lap_idx < len(activity.Laps) - 1 and  # Not the last lap
		# 				   activity.Laps[active_lap_idx + 1].StartTime <= wp.Timestamp):
		# 		active_lap_idx += 1
		# 	activity.Laps[active_lap_idx].Waypoints.append(wp)
		# 	frame_idx += 1

		return activity

	# def UploadActivity(self, serviceRecord, activity):
	# 	# /proxy/upload-service-1.1/json/upload/.fit
	# 	fit_file = FITIO.Dump(activity)
	# 	files = {"data": ("tap-sync-" + str(os.getpid()) + "-" + activity.UID + ".fit", fit_file)}
	# 	session = self._get_session(record=serviceRecord)
	# 	self._rate_limit()
	# 	res = session.post("https://connect.garmin.com/proxy/upload-service-1.1/json/upload/.fit", files=files)
	# 	res = res.json()["detailedImportResult"]
	#
	# 	if len(res["successes"]) == 0:
	# 		raise APIException("Unable to upload activity %s" % res)
	# 	if len(res["successes"]) > 1:
	# 		raise APIException("Uploaded succeeded, resulting in too many activities")
	# 	actid = res["successes"][0]["internalId"]
	#
	# 	name = activity.Name  # Capture in logs
	# 	notes = activity.Notes
	# 	encoding_headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}  # GC really, really needs this part, otherwise it throws obscure errors like "Invalid signature for signature method HMAC-SHA1"
	# 	warnings = []
	# 	try:
	# 		if activity.Name and activity.Name.strip():
	# 			self._rate_limit()
	# 			res = session.post("https://connect.garmin.com/proxy/activity-service-1.2/json/name/" + str(actid), data=urlencode({"value": activity.Name}).encode("UTF-8"), headers=encoding_headers)
	# 			try:
	# 				res = res.json()
	# 			except:
	# 				raise APIWarning("Activity name request failed - %s" % res.text)
	# 			if "display" not in res or res["display"]["value"] != activity.Name:
	# 				raise APIWarning("Unable to set activity name")
	# 	except APIWarning as e:
	# 		warnings.append(e)
	#
	# 	try:
	# 		if activity.Notes and activity.Notes.strip():
	# 			self._rate_limit()
	# 			res = session.post("https://connect.garmin.com/proxy/activity-service-1.2/json/description/" + str(actid), data=urlencode({"value": activity.Notes}).encode("UTF-8"), headers=encoding_headers)
	# 			try:
	# 				res = res.json()
	# 			except:
	# 				raise APIWarning("Activity notes request failed - %s" % res.text)
	# 			if "display" not in res or res["display"]["value"] != activity.Notes:
	# 				raise APIWarning("Unable to set activity notes")
	# 	except APIWarning as e:
	# 		warnings.append(e)
	#
	# 	try:
	# 		if activity.Type not in [ActivityType.Running, ActivityType.Cycling, ActivityType.Other]:
	# 			# Set the legit activity type - whatever it is, it's not supported by the TCX schema
	# 			acttype = [k for k, v in self._reverseActivityMappings.items() if v == activity.Type]
	# 			if len(acttype) == 0:
	# 				raise APIWarning("GarminConnect does not support activity type " + activity.Type)
	# 			else:
	# 				acttype = acttype[0]
	# 			self._rate_limit()
	# 			res = session.post("https://connect.garmin.com/proxy/activity-service-1.2/json/type/" + str(actid), data={"value": acttype})
	# 			res = res.json()
	# 			if "activityType" not in res or res["activityType"]["key"] != acttype:
	# 				raise APIWarning("Unable to set activity type")
	# 	except APIWarning as e:
	# 		warnings.append(e)
	#
	# 	try:
	# 		if activity.Private:
	# 			self._rate_limit()
	# 			res = session.post("https://connect.garmin.com/proxy/activity-service-1.2/json/privacy/" + str(actid), data={"value": "private"})
	# 			res = res.json()
	# 			if "definition" not in res or res["definition"]["key"] != "private":
	# 				raise APIWarning("Unable to set activity privacy")
	# 	except APIWarning as e:
	# 		warnings.append(e)
	#
	# 	if len(warnings):
	# 		raise APIWarning(str(warnings))  # Meh
	# 	return actid

	def _user_watch_user(self):
		return "FIXME"
		# if not serviceRecord.GetConfiguration()["WatchUserKey"]:
		# 	user_key = random.choice(list(GARMIN_CONNECT_USER_WATCH_ACCOUNTS.keys()))
		# 	logger.info("Assigning %s a new watch user %s" % (serviceRecord.ExternalID, user_key))
		# 	serviceRecord.SetConfiguration({"WatchUserKey": user_key})
		# 	return GARMIN_CONNECT_USER_WATCH_ACCOUNTS[user_key]
		# else:
		# 	return GARMIN_CONNECT_USER_WATCH_ACCOUNTS[serviceRecord.GetConfiguration()["WatchUserKey"]]

	def SubscribeToPartialSyncTrigger(self):
		# PUT http://connect.garmin.com/proxy/userprofile-service/connection/request/cpfair
		# (the poll worker finishes the connection)
		user_name = GC_USER
		logger.info("Requesting connection to %s " % user_name)
		self._rate_limit()
		resp = self.session.put("https://connect.garmin.com/proxy/userprofile-service/connection/request/%s" % user_name)
		print "response is", resp.status_code, resp.text
		return
		try:
			assert resp.status_code == 200
			assert resp.json()["requestStatus"] == "Created"
		except:
			raise RuntimeError("Connection request failed with user watch account %s: %s %s" % (user_name, resp.status_code, resp.text))
		else:
			self.service_record.SetConfiguration({"WatchConnectionID": resp.json()["id"]})

		self.service_record.SetPartialSyncTriggerSubscriptionState(True)

	def UnsubscribeFromPartialSyncTrigger(self):
		# GET http://connect.garmin.com/proxy/userprofile-service/socialProfile/connections to get the ID
		# {"fullName":null,"userConnections":[{"userId":5754439,"displayName":"TapiirikAPITEST","fullName":null,"location":null,"profileImageUrlMedium":null,"profileImageUrlSmall":null,"connectionRequestId":1566024,"userConnectionStatus":2,"userRoles":["ROLE_CONNECTUSER","ROLE_FITNESS_USER"],"userPro":false}]}
		# PUT http://connect.garmin.com/proxy/userprofile-service/connection/end/1904201
		# Unfortunately there's no way to delete a pending request - the poll worker will do this from the other end
		# session = self._get_session(email=GC_USER, password=GC_PASS, skip_cache=True)
		if "WatchConnectionID" in self.service_record.GetConfiguration():
			self._rate_limit()
			dc_resp = self.session.put("https://connect.garmin.com/modern/proxy/userprofile-service/connection/end/%s" % self.service_record.GetConfiguration()["WatchConnectionID"])
			if dc_resp.status_code != 200:
				raise RuntimeError("Error disconnecting user watch accunt %s from %s: %s %s" % (GC_USER, self.service_record.ExternalID, dc_resp.status_code, dc_resp.text))

			self.service_record.SetConfiguration({"WatchUserKey": None, "WatchConnectionID": None})
			self.service_record.SetPartialSyncTriggerSubscriptionState(False)
		else:
			# I broke Garmin Connect by having too many connections per account, so I can no longer query the connection list
			# All the connection request emails are sitting unopened in an email inbox, though, so I'll be backfilling the IDs from those
			raise RuntimeError("Did not store connection ID")

	def ShouldForcePartialSyncTrigger(self):
		# The poll worker can't see private activities.
		return self.service_record.GetConfiguration()["sync_private"]


	def PollPartialSyncTrigger(self, multiple_index):
		# TODO: ensure the appropriate users are connected
		# GET http://connect.garmin.com/modern/proxy/userprofile-service/connection/pending to get ID
		# [{"userId":6244126,"displayName":"tapiriik-sync-ulukhaktok","fullName":"tapiriik sync ulukhaktok","profileImageUrlSmall":null,"connectionRequestId":1904086,"requestViewed":true,"userRoles":["ROLE_CONNECTUSER"],"userPro":false}]
		# PUT http://connect.garmin.com/proxy/userprofile-service/connection/accept/1904086
		# ...later...
		# GET http://connect.garmin.com/proxy/activitylist-service/activities/comments/subscriptionFeed?start=1&limit=10

		# First, accept any pending connections
		# watch_user_key = sorted(list(GARMIN_CONNECT_USER_WATCH_ACCOUNTS.keys()))[multiple_index]
		# watch_user = GARMIN_CONNECT_USER_WATCH_ACCOUNTS[watch_user_key]

		#session = self._get_session(email=GC_USER, password=GC_PASS, skip_cache=True)

		# Then, check for users with new activities
		self._rate_limit()
		watch_activities_resp = self.session.get("https://connect.garmin.com/modern/proxy/activitylist-service/activities/subscriptionFeed?limit=1000")
		print "watch activities is", watch_activities_resp
		return
		try:
			watch_activities = watch_activities_resp.json()
		except ValueError:
			raise Exception("Could not parse new activities list: %s %s" % (watch_activities_resp.status_code, watch_activities_resp.text))
		print "watch_activities are", watch_activities
		#
		# active_user_pairs = [(x["ownerDisplayName"], x["activityId"]) for x in watch_activities["activityList"]]
		# active_user_pairs.sort(key=lambda x: x[1])  # Highest IDs last (so they make it into the dict, supplanting lower IDs where appropriate)
		# active_users = dict(active_user_pairs)
		#
		# active_user_recs = [ServiceRecord(x) for x in db.connections.find({"ExternalID": {"$in": list(active_users.keys())}, "Service": "garminconnect"}, {"Config": 1, "ExternalID": 1, "Service": 1})]
		#
		# if len(active_user_recs) != len(active_users.keys()):
		# 	logger.warning("Mismatch %d records found for %d active users" % (len(active_user_recs), len(active_users.keys())))
		#
		# to_sync_ids = []
		# for active_user_rec in active_user_recs:
		# 	last_active_id = active_user_rec.GetConfiguration()["WatchUserLastID"]
		# 	this_active_id = active_users[active_user_rec.ExternalID]
		# 	if this_active_id > last_active_id:
		# 		to_sync_ids.append(active_user_rec.ExternalID)
		# 		active_user_rec.SetConfiguration({"WatchUserLastID": this_active_id, "WatchUserKey": watch_user_key})
		#
		# self._rate_limit()
		# pending_connections_resp = session.get("https://connect.garmin.com/modern/proxy/userprofile-service/connection/pending")
		# try:
		# 	pending_connections = pending_connections_resp.json()
		# except ValueError:
		# 	logger.error("Could not parse pending connection requests: %s %s" % (pending_connections_resp.status_code, pending_connections_resp.text))
		# else:
		# 	valid_pending_connections_external_ids = [x["ExternalID"] for x in db.connections.find({"Service": "garminconnect", "ExternalID": {"$in": [x["displayName"] for x in pending_connections]}}, {"ExternalID": 1})]
		# 	logger.info("Accepting %d, denying %d connection requests for %s" % (len(valid_pending_connections_external_ids), len(pending_connections) - len(valid_pending_connections_external_ids), watch_user_key))
		# 	for pending_connect in pending_connections:
		# 		if pending_connect["displayName"] in valid_pending_connections_external_ids:
		# 			self._rate_limit()
		# 			connect_resp = session.put("https://connect.garmin.com/modern/proxy/userprofile-service/connection/accept/%s" % pending_connect["connectionRequestId"])
		# 			if connect_resp.status_code != 200:
		# 				logger.error("Error accepting request on watch account %s: %s %s" % (watch_user["Name"], connect_resp.status_code, connect_resp.text))
		# 		else:
		# 			self._rate_limit()
		# 			ignore_resp = session.put("https://connect.garmin.com/modern/proxy/userprofile-service/connection/decline/%s" % pending_connect["connectionRequestId"])

		# return to_sync_ids

	def RevokeAuthorization(self):
		# nothing to do here...
		pass

	def DeleteCachedData(self):
		# nothing cached...
		pass

	def DeleteActivity(self, uploadId):
		#session = self._get_session()
		self._rate_limit()
		del_res = self.session.delete("https://connect.garmin.com/modern/proxy/activity-service/activity/%d" % uploadId)
		del_res.raise_for_status()

logging.basicConfig(level=logging.DEBUG,
					format='%(levelname)s %(module)s %(process)d %(thread)d %(message)s',
					filename='/vagrant/django.log',
					filemode='a+')

if __name__ == '__main__':
	gc = GarminConnectService()
	gc.Authorize()
	act_ids = gc.DownloadActivityList()
	print "found activities", act_ids
	#print "Download file for act_id", act_ids[0]
	gc.DownloadActivityFile(act_ids[0])
	#gc = gc.SubscribeToPartialSyncTrigger()
