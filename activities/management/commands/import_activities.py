#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Import activities from external sources
"""
import logging


from django.core.management.base import BaseCommand
from activities.models import User

import activities.extras.syncplugins.imap


class Command(BaseCommand):
	help = 'Sync users activities configured external sources'

	def handle(self, *args, **options):
		for user in User.objects.all():
			try:
				logging.debug("Call sync handlers for user %s" % user.username)

				plugin = activities.extras.syncplugins.imap.IMAPSync(user)
				plugin.run()
			except Exception as msg:
				logging.error("Import failed for user %s with message %s" % (user.username, msg))
