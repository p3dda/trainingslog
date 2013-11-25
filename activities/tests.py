"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

import os
from decimal import Decimal
from activities.models import Activity, ActivityTemplate, CalorieFormula, Equipment, Event, Sport, Track, Lap

import django.test.client
from django.core.urlresolvers import reverse
from django.test import TestCase

from django.conf import settings as django_settings

class ActivityTest(TestCase):
	fixtures = ['activities_testdata.json', 'activities_tests_authdata.json']
	def setUp(self):
		self.client = django.test.client.Client()
	def tearDown(self):
		for act in Activity.objects.all():
			act.delete()

	def test_calformula_model(self):
		"""
		Tests calorieformula __unicode__ method
		"""
		cf = CalorieFormula.objects.get(pk=1)
		self.assertEqual(cf.__unicode__(), cf.name)

	def test_tcx_nogps_upload(self):
		"""
		Tests tcx file upload and parsing without gps
		"""
		#url = reverse("activity.views.list_activities")
		url="/activities/"

		self.client.login(username='test1', password='test1')

		resp = self.client.get(url, {"id": 1})
		self.assertEqual(resp.status_code, 200)

		testfile = open(os.path.join(django_settings.PROJECT_ROOT, 'examples', 'nogps.tcx'), 'r')
		response = self.client.post(url, {'trackfile': testfile})
		self.assertEqual(response.status_code, 302)

		nogps_act=Activity.objects.get(pk=1)
		self.assertEqual(nogps_act.time_elapsed, 7549)
		self.assertEqual(nogps_act.elevation_min, None)
		self.assertEqual(nogps_act.elevation_max, None)
		self.assertEqual(nogps_act.elevation_gain, None)
		self.assertEqual(nogps_act.elevation_loss, None)
		self.assertEqual(nogps_act.distance, Decimal('0'))

		nogps_act.delete()

	def test_tcx_withgps(self):
		"""
		Tests tcx file import and parsing with gps
		"""
		url="/activities/"
		self.client.login(username='test1', password='test1')

		testfile = open(os.path.join(django_settings.PROJECT_ROOT, 'examples', 'run.tcx'), 'r')
		response = self.client.post(url, {'trackfile': testfile})
		self.assertEqual(response.status_code, 302)

		act=Activity.objects.get(pk=1)
		self.assertEqual(act.time_elapsed, 4246)
		self.assertEqual(act.time, 4079)
		self.assertEqual(act.distance, Decimal('11.759'))
		self.assertEqual(act.elevation_min, 41)
		self.assertEqual(act.elevation_max, 74)
		self.assertEqual(act.elevation_gain, 346)
		self.assertEqual(act.elevation_loss, 347)

		act.delete()

	def test_tcx_bike(self):
		"""
		Tests tcx file import and parsing with gps
		"""
		url="/activities/"
		self.client.login(username='test1', password='test1')

		testfile = open(os.path.join(django_settings.PROJECT_ROOT, 'examples', 'bike.tcx'), 'r')
		response = self.client.post(url, {'trackfile': testfile})
		self.assertEqual(response.status_code, 302)

		act=Activity.objects.get(pk=1)
		self.assertEqual(act.time_elapsed, 7723)
		self.assertEqual(act.time, 4857)
		self.assertEqual(act.distance, Decimal('25.508'))
		self.assertEqual(act.elevation_min, 53)
		self.assertEqual(act.elevation_max, 113)
		self.assertEqual(act.elevation_gain, 76)
		self.assertEqual(act.elevation_loss, 134)
		self.assertEqual(act.cadence_avg, 74)
		self.assertEqual(act.cadence_max, 118)
		self.assertEqual(act.hf_avg, 97)
		self.assertEqual(act.hf_max, 162)
		self.assertEqual(act.speed_avg, Decimal('18.9'))
		self.assertEqual(act.speed_max, Decimal('48.1'))

		act.delete()

