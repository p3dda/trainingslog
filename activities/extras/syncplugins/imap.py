#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Import activities as email attachment from IMAP folder
"""

import email
import imaplib
import logging
import os
import shutil
import tempfile
import traceback

from django.conf import settings as django_settings
from django.core.files.base import File

from activities.models import Track
from activities.extras.activityfile import ActivityFile

import libs.crypto.cipher


class IMAPSyncException(Exception):
	pass


class IMAPSync(object):
	def __init__(self, user):
		"""
		IMAPSync __init__ method
		@param user: django user instance
		"""
		self.user = user
		self.imapclient = None
		logging.debug("Initialize IMAP sync for user %s" % self.user.username)
		self.cipher = libs.crypto.cipher.AESCipher(django_settings.ENCRYPTION_KEY)

	def run(self):
		"""
		IMAP import plugin main
		"""
		# profile = self.user.profile
		if 'sync.imap.enable' in self.user.params and self.user.params['sync.imap.enable']:
			logging.debug("IMAP sync is enabled for user %s" % self.user.username)

			self.imapclient = imaplib.IMAP4(self.user.params['sync.imap.host'])
			result = self.imapclient.login(self.user.params['sync.imap.user'], self.cipher.decrypt(self.user.params['sync.imap.password']))
			if result[0] != 'OK':
				raise IMAPSyncException('IMAP login failed: %s' % result)

			result = self.imapclient.select(self.user.params['sync.imap.mailbox'])
			if result[0] != 'OK':
				raise IMAPSyncException('IMAP failed to select mailbox %s: %s' % (self.user.params['sync.imap.mailbox'], result))

			typ, data = self.imapclient.search(None, 'ALL')

			num_processed = 0
			num_activities = 0
			for num in data[0].split():
				_, mail_raw = self.imapclient.fetch(num, '(RFC822)')
				mail = email.message_from_string(mail_raw[0][1])
				(result, num_act) = self.process_email(mail)
				if result:
					logging.debug("EMail imported successfully, mark as deleted")
					num_processed += 1
					num_activities += num_act
					self.imapclient.store(num, '+FLAGS', '\\Deleted')

			# TODO: Send confirmation mail with number of processed emails and imported activities
			self.imapclient.expunge()
		else:
			logging.debug("IMAP sync is not enabled for user %s" % self.user.username)
			return
		return

	def process_email(self, mail):
		"""
		Process raw email and import activities from attached files
		@param mail: email as string
		@return: Tuple: (success, num) Boolean success flag and number of imported activities
		"""
		email_success = False
		num_act = 0
		logging.debug("Parsing email: From: %s, Subject: %s, Date: %s" % (mail["From"], mail["Subject"], mail["Date"]))
		if not mail.is_multipart():
			logging.debug("Mail has no attachment, skip")
			return

		tmpdirname = tempfile.mkdtemp()
		for part in mail.walk():
			ctype = part.get_content_type()
			filename = part.get_filename()
			if ctype == 'application/octet-stream' and filename:
				logging.debug("Found .fit attachment with filename %s" % filename)
				# Call file import
				if not mail["Subject"]:
					name = 'IMAP Import'
				else:
					name = mail["Subject"]

				tmpfile = os.path.join(tmpdirname, part.get_filename())
				with open(tmpfile, 'wb') as f:
					f.write(part.get_payload(decode=True))

				result = self.import_file(tmpfile, name)
				if result:
					email_success = True
					num_act += 1
		shutil.rmtree(tmpdirname)

		return (email_success, num_act)

	def import_file(self, actfile, name):
		is_saved = False
		newtrack = Track()
		_, fileextension = os.path.splitext(actfile)
		newtrack.filetype = fileextension.lower()[1:]
		newtrack.trackfile.save(actfile, File(open(actfile), 'r'))
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

		return True
