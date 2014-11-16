#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Sync activities with garmin connect API
"""
import cookielib
import logging
import re
import requests
import tempfile
import time
import urllib2

from django.core.management.base import BaseCommand, CommandError
from activities.models import User


class Command(BaseCommand):
	args = 'username garmin_user garmin_pass'
	help = 'Sync users activities with Garmin Connect API'

	def __init__(self, *args, **kwargs):
		super(Command, self).__init__(*args, **kwargs)
		self.session = None
		rate_lock_path = tempfile.gettempdir() + "/gc_rate.lock"
		# Ensure the rate lock file exists (...the easy way)
		open(rate_lock_path, "a").close()
		self._rate_lock = open(rate_lock_path, "r+")

	def handle(self, *args, **options):
		cj = cookielib.CookieJar()
		opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))

		if len(args) != 3:
			CommandError("Invalid number of parameters")

		users = [User.objects.get(username=args[0]), ]

		print "Args: %s" % repr(args)
		for user in users:
			logging.debug("GarminConnect sync for user %s" % user.username)
			self.session = None

			self.username = args[1]  # FIXME: Take from user profile later
			self.password = args[2]
			self.session = self._get_session(email=self.username, password=self.password)

			list = self.DownloadActivityList()
			print "List is %s" % list

	def _get_session(self, record=None, email=None, password=None, skip_cache=False):
#		from tapiriik.auth.credential_storage import CredentialStore
		# cached = self._sessionCache.Get(record.ExternalID if record else email)
		# if cached and not skip_cache:
		# 		return cached
		# if record:
		# 	#  longing for C style overloads...
		# 	password = CredentialStore.Decrypt(record.ExtendedAuthorization["Password"])
		# 	email = CredentialStore.Decrypt(record.ExtendedAuthorization["Email"])

		session = requests.Session()
		self._rate_limit()
		gcPreResp = session.get("http://connect.garmin.com/", allow_redirects=False)
		# New site gets this redirect, old one does not
		if gcPreResp.status_code == 200:
			self._rate_limit()
			gcPreResp = session.get("https://connect.garmin.com/signin", allow_redirects=False)
			req_count = int(re.search("j_id(\d+)", gcPreResp.text).groups(1)[0])
			params = {"login": "login", "login:loginUsernameField": email, "login:password": password, "login:signInButton": "Sign In"}
			auth_retries = 3 # Did I mention Garmin Connect is silly?
			for retries in range(auth_retries):
				params["javax.faces.ViewState"] = "j_id%d" % req_count
				req_count += 1
				self._rate_limit()
				resp = session.post("https://connect.garmin.com/signin", data=params, allow_redirects=False)
				if resp.status_code >= 500 and resp.status_code < 600:
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
		elif gcPreResp.status_code == 302:
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
				"service": "http://connect.garmin.com/post-auth/login",
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
			preResp = session.get("https://sso.garmin.com/sso/login", params=params)
			if preResp.status_code != 200:
				raise CommandError("SSO prestart error %s %s" % (preResp.status_code, preResp.text))
			data["lt"] = re.search("name=\"lt\"\s+value=\"([^\"]+)\"", preResp.text).groups(1)[0]

			ssoResp = session.post("https://sso.garmin.com/sso/login", params=params, data=data, allow_redirects=False)
			if ssoResp.status_code != 200:
				raise CommandError("SSO error %s %s" % (ssoResp.status_code, ssoResp.text))

			ticket_match = re.search("ticket=([^']+)'", ssoResp.text)
			if not ticket_match:
				raise CommandError("Invalid login")
			ticket = ticket_match.groups(1)[0]

			# ...AND WE'RE NOT DONE YET!

			self._rate_limit()
			gcRedeemResp1 = session.get("http://connect.garmin.com/post-auth/login", params={"ticket": ticket}, allow_redirects=False)
			if gcRedeemResp1.status_code != 302:
				raise CommandError("GC redeem 1 error %s %s" % (gcRedeemResp1.status_code, gcRedeemResp1.text))

			self._rate_limit()
			gcRedeemResp2 = session.get(gcRedeemResp1.headers["location"], allow_redirects=False)
			if gcRedeemResp2.status_code != 302:
				raise CommandError("GC redeem 2 error %s %s" % (gcRedeemResp2.status_code, gcRedeemResp2.text))

		else:
			raise CommandError("Unknown GC prestart response %s %s" % (gcPreResp.status_code, gcPreResp.text))

		# self._sessionCache.Set(record.ExternalID if record else email, session)

		# session.headers.update(self._obligatory_headers)

		return session

	def DownloadActivityList(self, exhaustive=False):
		#http://connect.garmin.com/proxy/activity-search-service-1.0/json/activities?&start=0&limit=50
		#session = self._get_session(record=serviceRecord)
		page = 1
		pageSz = 100
		activities = []
		exclusions = []
		while True:
			logging.debug("Req with " + str({"start": (page - 1) * pageSz, "limit": pageSz}))
			self._rate_limit()

			retried_auth = False
			while True:
				res = self.session.get("http://connect.garmin.com/proxy/activity-search-service-1.0/json/activities", params={"start": (page - 1) * pageSz, "limit": pageSz})
				# It's 10 PM and I have no clue why it's throwing these errors, maybe we just need to log in again?
				if res.status_code == 403 and not retried_auth:
					retried_auth = True
					session = self._get_session(email=self.username, password=self.password)
				else:
					break
			try:
				res = res.json["results"]
			except ValueError:
				res_txt = res.text # So it can capture in the log message
				raise CommandError("Parse failure in GC list resp: %s" % res.status_code)
			if "activities" not in res:
				break  # No activities on this page - empty account.
			for act in res["activities"]:
				act = act["activity"]
				print act['activityId']
				print act['device']

			# TODO: Check if we already have activity with such ID, or activity matching timestamp
			# If not, check if we can download and import activity file from
			# http://connect.garmin.com/proxy/download-service/files/activity/<activityId> (original) or
			# http://connect.garmin.com/proxy/activity-service-1.1/tcx/activity/<activityId>?full=true

			# FIXME: Check if we are long enough in the past on GC; if so, break here
			break

	def _rate_limit(self):
		import fcntl, struct, time
		min_period = 1  # I appear to been banned from Garmin Connect while determining this.
		print("Waiting for lock")
		fcntl.flock(self._rate_lock,fcntl.LOCK_EX)
		try:
			print("Have lock")
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

			print("Rate limited for %f" % wait_time)
		finally:
			fcntl.flock(self._rate_lock,fcntl.LOCK_UN)
