#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
import datetime
import json
from django.core.urlresolvers import reverse
from django.test import TestCase, Client
from health.models import Weight, Goal
from django.contrib.auth.models import User
from health.utils import parsefloat


class HealthTest(TestCase):
	fixtures = ['health_views_testdata.json', 'health_views_testhealthdata.json']

	def setUp(self):
		self.c = Client()
		self.c.login(username='test1', password='test1')

	def test_weight_model(self):
		"""
		Tests that 1 + 1 always equals 2.
		"""
		w = Weight.objects.get(pk=1)
		self.assertEqual(w.__unicode__(), "73.6")

	def test_desease_get_view(self):
		url = reverse("health.views.get_desease")

		resp = self.c.get(url, {"id": 1})
		self.assertEqual(resp.status_code, 200)
		self.assertIn("Erkältung".decode('utf-8'), resp.content.decode('unicode_escape'))

		resp = self.c.get(url, {"id": 2})
		self.assertEqual(resp.status_code, 403)

	def test_add_desease_view(self):
		url = reverse("health.views.add_desease")

		resp = self.c.get(url)
		self.assertEqual(resp.status_code, 400)

		start_date = "01.01.2014"
		end_date = "03.01.2014"
		name = "Husten"
		comment = ""
		resp = self.c.post(url, data={'start_date': start_date, "end_date": end_date, 'name': name, 'comment': comment})
		self.assertEqual(resp.status_code, 200)
		response = json.loads(resp.content)
		self.assertTrue(response["success"])

		start_date = "01.2014"
		end_date = "03.01.2014"
		resp = self.c.post(url, data={'start_date': start_date, "end_date": end_date, 'name': name, 'comment': comment})
		self.assertEqual(resp.status_code, 200)
		response = json.loads(resp.content)
		self.assertFalse(response["success"])

		start_date = "01.01.2014"
		end_date = "03.2014"
		resp = self.c.post(url, data={'start_date': start_date, "end_date": end_date, 'name': name, 'comment': comment})
		self.assertEqual(resp.status_code, 200)
		response = json.loads(resp.content)
		self.assertFalse(response["success"])

	def test_show_weight_view(self):
		url = reverse("health.views.show_weight")

		resp = self.c.get(url)
		self.assertEqual(resp.status_code, 200)
		self.assertNotIn("td_goal_distance", resp.content)

		g = Goal.objects.create(
			date = datetime.datetime.today(),
			user = User.objects.get(pk=2),
			due_date = datetime.timedelta(days=1) + datetime.datetime.today(),
			target_weight = 70.0
		)
		g.save()

		resp = self.c.get(url)
		self.assertEqual(resp.status_code, 200)
		content = resp.content
		self.assertIn("td_goal_distance", resp.content)

	def test_add_weight_view(self):
		url = reverse("health.views.add_weight")

		resp = self.c.get(url)
		self.assertEqual(resp.status_code, 400)

		datestring = "01.01.2014"
		weight = "71"

		resp = self.c.post(url, data={'date': datestring, 'weight': weight})
		self.assertEqual(resp.status_code, 200)
		response = json.loads(resp.content)
		self.assertTrue(response["success"])

		datestring = "01.2014"
		weight = "71"
		resp = self.c.post(url, data={'date': datestring, 'weight': weight})
		self.assertEqual(resp.status_code, 200)
		response = json.loads(resp.content)
		self.assertFalse(response["success"])

		datestring = "01.01.2014"
		weight = "71c"
		resp = self.c.post(url, data={'date': datestring, 'weight': weight})
		self.assertEqual(resp.status_code, 200)
		response = json.loads(resp.content)
		self.assertFalse(response["success"])

	def test_add_weightgoal_view(self):
		url = reverse("health.views.add_weightgoal")

		resp = self.c.get(url)
		self.assertEqual(resp.status_code, 400)

		datestring = "01.02.2014"
		weight = "70"
		resp = self.c.post(url, data={'date': datestring, 'weight': weight})
		self.assertEqual(resp.status_code, 200)
		response = json.loads(resp.content)
		self.assertTrue(response["success"])

		datestring = "02.2014"
		weight = "71"
		resp = self.c.post(url, data={'date': datestring, 'weight': weight})
		self.assertEqual(resp.status_code, 200)
		response = json.loads(resp.content)
		self.assertFalse(response["success"])

		datestring = "01.01.2014"
		weight = "71c"
		resp = self.c.post(url, data={'date': datestring, 'weight': weight})
		self.assertEqual(resp.status_code, 200)
		response = json.loads(resp.content)
		self.assertFalse(response["success"])

	def test_add_pulse_view(self):
		url = reverse("health.views.add_pulse")

		resp = self.c.get(url)
		self.assertEqual(resp.status_code, 400)

		datestring = "01.02.2014"
		rest = "70"
		resp = self.c.post(url, data={'date': datestring, 'rest': rest})
		self.assertEqual(resp.status_code, 200)
		response = json.loads(resp.content)
		self.assertTrue(response["success"])

		datestring = "02.2014"
		rest = "70"
		resp = self.c.post(url, data={'date': datestring, 'rest': rest})
		self.assertEqual(resp.status_code, 200)
		response = json.loads(resp.content)
		self.assertFalse(response["success"])

		datestring = "01.01.2014"
		rest = "71c"
		resp = self.c.post(url, data={'date': datestring, 'rest': rest})
		self.assertEqual(resp.status_code, 200)
		response = json.loads(resp.content)
		self.assertFalse(response["success"])

	def test_get_data_view(self):
		url = reverse("health.views.get_data")

		resp = self.c.get(url)
		self.assertEqual(resp.status_code, 200)
		data = json.loads(resp.content)
		self.assertIsInstance(data, dict)


	def test_health_utils(self):
		s="1.2"
		self.assertEqual(1.2, parsefloat(s))

		s="1,234.567.890"
		self.assertEqual(1.234567890, parsefloat(s))

		s="NoFloat"
		self.assertRaises(ValueError, parsefloat, s)
		