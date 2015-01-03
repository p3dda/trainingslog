#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Sync activities with garmin connect API
"""
import cookielib
import logging
import os
import re
import requests
import shutil
import tempfile
import time
import traceback
import urllib2
import zipfile
import fcntl

from django.core.management.base import BaseCommand, CommandError
from django.core.files.base import File
from activities.models import Activity, User, Track
from activities.extras.activityfile import ActivityFile


GARMIN_DOWNLOAD_BASE = "http://connect.garmin.com/proxy/download-service/files/activity"


class Command(BaseCommand):
	args = '[usernames]'
	help = 'Sync users activities with Garmin Connect API'

	def __init__(self, *args, **kwargs):
		super(Command, self).__init__(*args, **kwargs)
		self.session = None
		self.user = None
		self.username = None
		self.password = None

		rate_lock_path = tempfile.gettempdir() + "/gc_rate.lock"
		# Ensure the rate lock file exists (...the easy way)
		open(rate_lock_path, "a").close()
		self._rate_lock = open(rate_lock_path, "r+")

	def handle(self, *args, **options):
		cj = cookielib.CookieJar()
		urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))

		if len(args) > 0:
			users = User.objects.filter(username__in=args)
		else:
			users = User.objects.all()

		for self.user in users:
			self.username = self.user.profile.gc_username
			self.password = self.user.profile.gc_password

			logging.debug("GarminConnect sync for user %s", self.user.username)
			if self.username is None or self.password is None:
				logging.debug("Garmin credentials missing for user %s", self.user.username)
				continue

			self.session = None
			act_list = self.get_activity_list()

			import_list = []
			db_activites = Activity.objects.filter(user=self.user)
			for act in act_list:
				# garmin connect reports timestamp in millis and local timezone, convert to seconds since epoch UTC
				print repr(act)
				start_ts = int(act["activity"]["beginTimestamp"]["millis"]) / 1000 - int(act["activity"]["activityTimeZone"]["offset"]) * 3600
				imported = False
				for db_act in db_activites:
					db_start_ts = time.mktime(db_act.date.timetuple())
					if abs(db_start_ts - start_ts) < 300:
						# Found another activity within 5 minutes start time
						imported = True
						break
				if imported:
					logging.debug("Activity from %s already imported", act["activity"]["beginTimestamp"]["value"])
				else:
					import_list.append(act)
			print "Import %s new activities" % (len(import_list))

			for activity in import_list:
				print "Import activity ID %s with name %s from URL %s/%s" % (activity['activity']['activityId'], activity['activity']['activityName']['value'], GARMIN_DOWNLOAD_BASE, activity['activity']['activityId'])
				self.import_activity(activity['activity']['activityId'], activity['activity']['activityName']['value'])

	def import_activity(self, act_id, name):
		is_saved = False
		newtrack = Track()

		tmpfile = tempfile.NamedTemporaryFile(mode="wb", delete=False)
		tmpfilename = tmpfile.name
		tmpdirname = tempfile.mkdtemp()

		response = self.session.get("%s/%s" % (GARMIN_DOWNLOAD_BASE, act_id))
		if response.ok:
			shutil.copyfileobj(response.raw, tmpfile)
		else:
			raise RuntimeError("Failed to download file from Garmin Connect: %s/%s" % (GARMIN_DOWNLOAD_BASE, act_id))
		tmpfile.close()

		with zipfile.ZipFile(tmpfilename, 'r') as myzip:

			if len(myzip.namelist()) != 1:
				raise RuntimeError("Not exactly one file in downloaded archive from %s/%s" % (GARMIN_DOWNLOAD_BASE, act_id))
			fitfile = myzip.namelist()[0]
			myzip.extract(fitfile, tmpdirname)

			_, fileextension = os.path.splitext(fitfile)
			newtrack.filetype = fileextension.lower()[1:]
			newtrack.trackfile.save(fitfile, File(open("%s/%s" % (tmpdirname, fitfile), 'r')))

			is_saved = True
		try:
			activityfile = ActivityFile.ActivityFile(newtrack, user=self.user, activityname=name)
			activityfile.import_activity()
			activity = activityfile.get_activity()
			activity.save()
		except Exception, exc:
			logging.error("Exception raised in importtrack: %s", str(exc))
			if is_saved:
				newtrack.delete()
			for line in traceback.format_exc().splitlines():
				logging.error(line.strip())

		os.remove(tmpfile.name)
		shutil.rmtree(tmpdirname)

	def _get_session(self, email=None, password=None):
		session = requests.Session()
		self._rate_limit()
		gc_pre_resp = session.get("http://connect.garmin.com/", allow_redirects=False)
		# New site gets this redirect, old one does not
		if gc_pre_resp.status_code == 200:
			self._rate_limit()
			gc_pre_resp = session.get("https://connect.garmin.com/signin", allow_redirects=False)
			req_count = int(re.search(r"j_id(\d+)", gc_pre_resp.text).groups(1)[0])
			params = {"login": "login", "login:loginUsernameField": email, "login:password": password, "login:signInButton": "Sign In"}
			auth_retries = 3  # Did I mention Garmin Connect is silly?
			for retries in range(auth_retries):
				params["javax.faces.ViewState"] = "j_id%d" % req_count
				req_count += 1
				self._rate_limit()
				resp = session.post("https://connect.garmin.com/signin", data=params, allow_redirects=False)
				if 500 <= resp.status_code < 600:
					raise CommandError("Remote API failure")
				if resp.status_code != 302:  # yep
					if "errorMessage" in resp.text:
						if retries < auth_retries - 1:
							time.sleep(1)
							continue
						else:
							raise CommandError("Invalid login")
					else:
						raise CommandError("Mystery login error %s" % resp.text)
				break
		elif gc_pre_resp.status_code == 302:
			# JSIG CAS, cool I guess.
			# Not quite OAuth though, so I'll continue to collect raw credentials.
			# Commented stuff left in case this ever breaks because of missing parameters...
			data = {
				"username": email,
				"password": password,
				"_eventId": "submit",
				"embed": "true",
			}
			params = {
				"service": "http://connect.garmin.com/post-auth/login",
				"clientId": "GarminConnect",
				"consumeServiceTicket": "false",
			}
			# I may never understand what motivates people to mangle a perfectly good protocol like HTTP in the ways they do...
			pre_resp = session.get("https://sso.garmin.com/sso/login", params=params)
			if pre_resp.status_code != 200:
				raise CommandError("SSO prestart error %s %s" % (pre_resp.status_code, pre_resp.text))
			data["lt"] = re.search(r"name=\"lt\"\s+value=\"([^\"]+)\"", pre_resp.text).groups(1)[0]

			sso_resp = session.post("https://sso.garmin.com/sso/login", params=params, data=data, allow_redirects=False)
			if sso_resp.status_code != 200:
				raise CommandError("SSO error %s %s" % (sso_resp.status_code, sso_resp.text))

			ticket_match = re.search("ticket=([^']+)'", sso_resp.text)
			if not ticket_match:
				raise CommandError("Invalid login")
			ticket = ticket_match.groups(1)[0]

			# ...AND WE'RE NOT DONE YET!

			self._rate_limit()
			gc_redeem_resp1 = session.get("http://connect.garmin.com/post-auth/login", params={"ticket": ticket}, allow_redirects=False)
			if gc_redeem_resp1.status_code != 302:
				raise CommandError("GC redeem 1 error %s %s" % (gc_redeem_resp1.status_code, gc_redeem_resp1.text))

			self._rate_limit()
			gc_redeem_resp2 = session.get(gc_redeem_resp1.headers["location"], allow_redirects=False)
			if gc_redeem_resp2.status_code != 302:
				raise CommandError("GC redeem 2 error %s %s" % (gc_redeem_resp2.status_code, gc_redeem_resp2.text))

		else:
			raise CommandError("Unknown GC prestart response %s %s" % (gc_pre_resp.status_code, gc_pre_resp.text))

		return session

	def get_activity_list(self, page=1):
		#  http://connect.garmin.com/proxy/activity-search-service-1.0/json/activities?&start=0&limit=50
		#  session = self._get_session(record=serviceRecord)
		page_sz = 10
		res = None
		self.session = self._get_session(email=self.username, password=self.password)

		logging.debug("Req with " + str({"start": (page - 1) * page_sz, "limit": page_sz}))
		self._rate_limit()

		retried_auth = False
		while True:
			res = self.session.get("http://connect.garmin.com/proxy/activity-search-service-1.0/json/activities", params={"start": (page - 1) * page_sz, "limit": page_sz})
			# It's 10 PM and I have no clue why it's throwing these errors, maybe we just need to log in again?
			if res.status_code == 403 and not retried_auth:
				retried_auth = True
				self.session = self._get_session(email=self.username, password=self.password)
			else:
				break
		try:
			res = res.json["results"]
		except ValueError:
			raise CommandError("Parse failure in GC list resp: %s" % res.status_code)
		if "activities" not in res:
			return []  # No activities on this page - empty account.

		# TODO: Check if we already have activity with such ID, or activity matching timestamp
		# If not, check if we can download and import activity file from
		# http://connect.garmin.com/proxy/download-service/files/activity/<activityId> (original) or
		# http://connect.garmin.com/proxy/activity-service-1.1/tcx/activity/<activityId>?full=true

		return res["activities"]

	def _rate_limit(self):
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
