"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

import os

from activities.models import Activity, ActivityTemplate, CalorieFormula, Equipment, Event, Sport, Track, Lap

import django.test.client
from django.core.urlresolvers import reverse
from django.test import TestCase

from django.conf import settings as django_settings

class ActivityTest(TestCase):
	fixtures = ['activities_testdata.json', 'activities_tests_authdata.json']
	def setUp(self):
		self.client = django.test.client.Client()

	def test_calformula_model(self):
		"""
		Tests calorieformula __unicode__ method
		"""
		cf = CalorieFormula.objects.get(pk=1)
		self.assertEqual(cf.__unicode__(), cf.name)

	def test_tcx_upload(self):
		"""
		Tests tcx file upload and parsing
		"""
		#url = reverse("activity.views.list_activities")
		url="/activities/"

		self.client.login(username='test1', password='test1')

		resp = self.client.get(url, {"id": 1})
		self.assertEqual(resp.status_code, 200)

		testfile = open(os.path.join(django_settings.PROJECT_ROOT, 'examples', 'nogps.tcx'), 'r')
		response = self.client.post(url, {'trackfile': testfile})
		self.assertEqual(resp.status_code, 200)

		nogps_act=Activity.objects.get(pk=1)

		self.assertEqual(nogps_act.time_elapsed, 7549)
		self.assertEqual(nogps_act.elevation_min, None)
		print nogps_act.time_elapsed
		nogps_act.delete()
