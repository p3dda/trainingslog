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

from django.core.files.base import File

from activities.models import Track
from activities.extras.activityfile import ActivityFile


class IMAPSyncException(Exception):
	pass


class IMAPSync(object):
	def __init__(self, user):
		self.user = user
		self.imapclient = None
		logging.debug("Initialize IMAP sync for user %s" % self.user.username)

	def run(self):
		profile = self.user.profile
		if profile.params:
			if profile.params['trainingslog.sync.imap.enable'] == 'True':
				logging.debug("IMAP sync is enabled for user %s" % self.user.username)

				self.imapclient = imaplib.IMAP4(profile.params['trainingslog.sync.imap.host'])
				result = self.imapclient.login(profile.params['trainingslog.sync.imap.user'], profile.params['trainingslog.sync.imap.password'])
				if result[0] != 'OK':
					raise IMAPSyncException('IMAP login failed: %s' % result)

				result = self.imapclient.select(profile.params['trainingslog.sync.imap.mailbox'])
				if result[0] != 'OK':
					raise IMAPSyncException('IMAP failed to select mailbox %s: %s' % (profile.params['trainingslog.sync.imap.mailbox'], result))

				typ, data = self.imapclient.search(None, 'ALL')
				for num in data[0].split():
					_, mail_raw = self.imapclient.fetch(num, '(RFC822)')
					mail = email.message_from_string(mail_raw[0][1])
					result = self.process_email(mail)
					if result:
						logging.debug("EMail imported successfully, mark as deleted")
						self.imapclient.store(num, '+FLAGS', '\\Deleted')

				self.imapclient.expunge()
			else:
				logging.debug("IMAP sync is not enabled for user %s" % self.user.username)
				return
		else:
			logging.debug("IMAP sync is not enabled for user %s" % self.user.username)
		return

	def process_email(self, mail):
		email_success = False
		logging.debug("Parsing email: From: %s, Subject: %s, Date: %s" % (mail["From"], mail["Subject"], mail["Date"]))
		if not mail.is_multipart():
			logging.debug("Mail has no attachment, skip")
			return
		for part in mail.walk():
			ctype = part.get_content_type()
			filename = filename = part.get_filename()
			if ctype == 'application/octet-stream' and filename:
				logging.debug("Found .fit attachment with filename %s" % filename)
				# Call fit file import
				if not mail["Subject"]:
					name = 'IMAP Import'
				else:
					name = mail["Subject"]
				result = self.import_fit_file(part, name)
				if result:
					email_success = True
		return email_success

	def import_fit_file(self, part, name):
		tmpdirname = tempfile.mkdtemp()
		is_saved = False
		fitfile = os.path.join(tmpdirname, part.get_filename())
		open(fitfile, 'wb').write(part.get_payload(decode=True))
		newtrack = Track()
		_, fileextension = os.path.splitext(fitfile)
		newtrack.filetype = fileextension.lower()[1:]
		newtrack.trackfile.save(fitfile, File(open(fitfile), 'r'))

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

		shutil.rmtree(tmpdirname)
		return True
