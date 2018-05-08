#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Import activities as email attachment from IMAP folder
"""

import email
import email.header
import imaplib
import logging
import os
import shutil
import tempfile
import traceback

from django.conf import settings as django_settings
from django.core.files.base import File
import django.core.mail

from activities.models import Track
from activities.extras.activityfile import ActivityFile

import libs.crypto.cipher


class IMAPSyncException(Exception):
	pass


PARAMS_REQUIRED = 'sync_imap_host', 'sync_imap_user', 'sync_imap_password'

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

	@staticmethod
	def _decode_header(header):
		"""Decode MIME-Encoded Email header
		@param header: Encoded Email header
		@return: Decoded header as string
		"""
		dh = email.header.decode_header(header)
		default_charset = 'ASCII'
		return ' '.join([ unicode(t[0], t[1] or default_charset) for t in dh ])

	def run(self):
		"""
		IMAP import plugin main
		"""
		# profile = self.user.profile
		if 'sync_imap_enable' in self.user.params and self.user.params['sync_imap_enable']:
			logging.debug("IMAP sync is enabled for user %s" % self.user.username)
			missing_param = False
			for param in PARAMS_REQUIRED:
				if param not in self.user.params:
					logging.warning("Missing parameter in userprofile: %s", param)
					missing_param = True

			if missing_param:
				return

			self.imapclient = imaplib.IMAP4_SSL(self.user.params['sync_imap_host'])
			result = self.imapclient.login(self.user.params['sync_imap_user'], self.cipher.decrypt(self.user.params['sync_imap_password']))
			if result[0] != 'OK':
				raise IMAPSyncException('IMAP login failed: %s' % result)

			if 'sync_imap_mailbox' in self.user.params:
				mailbox = self.user.params['sync_imap_mailbox']
			else:
				mailbox = 'INBOX'
			result = self.imapclient.select(mailbox)
			if result[0] != 'OK':
				raise IMAPSyncException('IMAP failed to select mailbox %s: %s' % (self.user.params['sync_imap_mailbox'], result))

			typ, data = self.imapclient.search(None, 'ALL')

			for num in data[0].split():
				_, mail_raw = self.imapclient.fetch(num, '(RFC822)')
				mail = email.message_from_string(mail_raw[0][1])
				(result, num_act, num_files) = self.process_email(mail)
				if result:
					logging.debug("EMail imported successfully, imported %s/%s activities. Mark as deleted" % (num_act, num_files))
					self.imapclient.store(num, '+FLAGS', '\\Deleted')

					self.send_import_confirm("IMAP Sync", ['pedda@p3dda.net'], num_act, num_files)
				else:
					self.send_import_fail("IMAP Sync", ['pedda@p3dda.net'], num_act, num_files)

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
		num_files = 0
		logging.debug("Parsing email: From: %s, Subject: %s, Date: %s" % (mail["From"], mail["Subject"], mail["Date"]))
		if not mail.is_multipart():
			logging.debug("Mail has no attachment, skip")
			return

		tmpdirname = tempfile.mkdtemp()
		for part in mail.walk():
			ctype = part.get_content_type()
			filename = part.get_filename()
			if ctype == 'application/octet-stream' and filename:
				num_files += 1
				logging.debug("Found .fit attachment with filename %s" % filename)
				# Call file import
				if not mail["Subject"]:
					name = 'IMAP Import'
				else:
					name = self._decode_header(mail["Subject"]) + " " + filename

				tmpfile = os.path.join(tmpdirname, part.get_filename())
				with open(tmpfile, 'wb') as f:
					f.write(part.get_payload(decode=True))

				result = self.import_file(tmpfile, name)
				if result:
					num_act += 1
		shutil.rmtree(tmpdirname)

		return (num_files==num_act, num_act, num_files)

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

	def send_import_confirm(self, title, to, num_activities, num_files):
		subject = "Trainingslog %s" % title
		if 'sync_imap_mailbox' not in self.user.params:
			mailbox = 'INBOX'
		else:
			mailbox = self.user.params['sync_imap_mailbox']
		body = """
Trainingslog Activity Import

User %(user)s
Processed email for IMAP Account %(email)s@%(host)s/%(maildir)s
Successfully imported %(num_activities)s/%(num_files)s Activities
"""\
		% {
			'user': self.user.username, 'email': self.user.params['sync_imap_user'], 'host': self.user.params['sync_imap_host'],
			'maildir': mailbox, 'num_activities': num_activities, 'num_files': num_files
		}
		django.core.mail.send_mail(subject, body, django_settings.EMAIL_FROM, to)

	def send_import_fail(self, title, to, num_activities, num_files):
		subject = "Trainingslog %s" % title
		if 'sync_imap_mailbox' not in self.user.params:
			mailbox = 'INBOX'
		else:
			mailbox = self.user.params['sync_imap_mailbox']
		body = """
Trainingslog Activity Import failed

User %(user)s
Processed email for IMAP Account %(email)s@%(host)s/%(maildir)s
Partially imported %(num_activities)s/%(num_files)s Activities
"""\
		% {
			'user': self.user.username, 'email': self.user.params['sync_imap_user'], 'host': self.user.params['sync_imap_host'],
			'maildir': mailbox, 'num_activities': num_activities, 'num_files': num_files
		}
		django.core.mail.send_mail(subject, body, django_settings.EMAIL_FROM, to)
