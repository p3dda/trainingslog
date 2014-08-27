"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
import json
import os
from decimal import Decimal
from activities.models import Activity, ActivityTemplate, CalorieFormula, Equipment, Event, Sport, Track, Lap
import activities.utils
from activities.extras.activityfile import ActivityFile
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

	def test_pace_to_speed(self):
		"""
		Tests utils.pace_to_speed method
		"""
		speed = activities.utils.pace_to_speed("7:30")
		self.assertEqual(speed, 8.0)
		speed = activities.utils.pace_to_speed(7.5)
		self.assertEqual(speed, 8.0)

	def test_speed_to_pace(self):
		"""
		Tests utils.speed_to_pace method
		"""
		speed = activities.utils.speed_to_pace(8)
		self.assertEqual(speed, "7:30")

	def test_seconds_to_time(self):
		"""
		Tests utils.second_to_time method
		"""
		time = activities.utils.seconds_to_time(2)
		self.assertEqual(time, "0:02")

		time = activities.utils.seconds_to_time(2, force_hour=True)
		self.assertEqual(time, "0:00:02")

		time = activities.utils.seconds_to_time(3602, force_hour=True)
		self.assertEqual(time, "1:00:02")


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

		act_track = ActivityFile.ActivityFile(act.track)
		self.assertEqual(len(act_track.track_data["hf"]), 804)
		self.assertEqual(len(act_track.track_data["cad"]), 0)
		self.assertEqual(len(act_track.track_by_distance), 796)

		url = "/activities/1/"
		response = self.client.get(url)
		self.assertEqual(response.status_code, 200)

		url = "/activities/1/?p=plots"
		response = self.client.get(url)
		self.assertEqual(response.status_code, 200)
		jsondata = json.loads(response.content)
		self.assertIsInstance(jsondata, dict)
		pdata = jsondata["plot_data"]
		ddata = jsondata["details_data"]

		self.assertIsInstance(pdata, dict)
		self.assertTrue(pdata.has_key('altitude'))
		self.assertEqual(len(pdata['altitude']), 804)
		self.assertTrue(pdata.has_key('cadence'))
		self.assertEqual(pdata['cadence'], [])
		self.assertTrue(pdata.has_key('speed'))
		self.assertTrue(pdata.has_key('speed_foot'))

		self.assertIsInstance(ddata, dict)
		self.assertEqual(ddata, {})

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
		self.assertTrue(os.path.isfile(act.track.trackfile.path + ".gpx"))

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

	def test_tcx_communicator_plugin(self):
		"""
		Tests tcx file import and parsing with gps
		"""
		url="/activities/"
		self.client.login(username='test1', password='test1')

		with open(os.path.join(django_settings.PROJECT_ROOT, 'examples', 'bike.tcx'), 'r') as tcxfile:
			tcx_content = tcxfile.read()

		response = self.client.post(url, {'content': tcx_content, 'filename': 'test.tcx'})
		self.assertEqual(response.status_code, 200)

		act=Activity.objects.get(pk=1)
		self.assertTrue(os.path.isfile(act.track.trackfile.path + ".gpx"))
		self.assertEqual(act.time_elapsed, 7723)
		self.assertEqual(act.time, 4857)


	def test_fit_run(self):
		"""
		Tests fit file import and parsing with gps and cadence
		"""
		url="/activities/"
		self.client.login(username='test1', password='test1')

		testfile = open(os.path.join(django_settings.PROJECT_ROOT, 'examples', '16MileLongRun.FIT'), 'r')
		response = self.client.post(url, {'trackfile': testfile})
		self.assertEqual(response.status_code, 302)
		act = Activity.objects.get(pk=1)
		self.assertTrue(os.path.isfile(act.track.trackfile.path + ".gpx"))

		laps = Lap.objects.filter(activity = act)
		self.assertEqual(len(laps), 24)
		self.assertEqual(act.distance, Decimal('26.049'))
		self.assertEqual(act.time, 6939)
		self.assertEqual(act.time_elapsed, 7135)

		act_track = ActivityFile.ActivityFile(act.track)
		self.assertEqual(len(act_track.track_data["hf"]), 6940)
		self.assertEqual(len(act_track.track_data["cad"]), 6940)
		self.assertEqual(len(act_track.track_by_distance), 6928)

		self.assertEqual(act.elevation_min, 9)	# FIXME: Garmin Connect reports 25; seems as if they filter spikes
		self.assertEqual(act.elevation_max, 68)	# FIXME: Garmin Connect reports 69; altitude is a float, do we floor?
		self.assertEqual(act.cadence_avg, 174)
		self.assertEqual(act.cadence_max, 214)

		url = "/activities/1/"
		response = self.client.get(url)
		self.assertEqual(response.status_code, 200)

		url = "/activities/1/?p=plots"
		response = self.client.get(url)
		self.assertEqual(response.status_code, 200)
		jsondata = json.loads(response.content)

		self.assertIsInstance(jsondata, dict)
		pdata=jsondata["plot_data"]
		ddata = jsondata["details_data"]
		self.assertTrue(pdata.has_key('altitude'))
		self.assertEqual(len(pdata['altitude']), 6940)
		self.assertTrue(pdata.has_key('cadence'))
		self.assertNotEqual(pdata['cadence'], [])
		self.assertTrue(pdata.has_key('speed'))
		self.assertTrue(pdata.has_key('speed_foot'))

		self.assertIsInstance(ddata, dict)
		self.assertEqual(ddata["avg_stance_time"], 240.6)

	def test_fit_nogps_upload(self):
		"""
		Tests tcx file upload and parsing without gps
		"""
		#url = reverse("activity.views.list_activities")
		url="/activities/"

		self.client.login(username='test1', password='test1')

		resp = self.client.get(url, {"id": 1})
		self.assertEqual(resp.status_code, 200)

		testfile = open(os.path.join(django_settings.PROJECT_ROOT, 'examples', 'bike_nogps.fit'), 'r')
		response = self.client.post(url, {'trackfile': testfile})
		self.assertEqual(response.status_code, 302)

		act=Activity.objects.get(pk=1)
		self.assertEqual(act.time_elapsed, 3285)
		self.assertEqual(act.weather_stationname, None)
		self.assertEqual(act.cadence_avg, 83)
		self.assertEqual(act.cadence_max, 111)

		act.delete()

		testfile = open(os.path.join(django_settings.PROJECT_ROOT, 'examples', 'bike_nogps_nospeed.fit'), 'r')
		response = self.client.post(url, {'trackfile': testfile})
		self.assertEqual(response.status_code, 302)

		act=Activity.objects.get(pk=1)
		self.assertEqual(act.distance, Decimal('0'))
		self.assertEqual(act.time, 4365)
		self.assertEqual(act.time_movement, None)
		self.assertEqual(act.speed_avg, Decimal('0'))
		self.assertEqual(act.speed_avg_movement, None)
		self.assertEqual(act.time_elapsed, 5023)
		self.assertEqual(act.cadence_avg, 90)
		self.assertEqual(act.cadence_max, 125)

		laps = Lap.objects.filter(activity = act)
		self.assertEqual(len(laps), 15)
		lap = laps[1]

		self.assertEqual(lap.distance, Decimal('0'))
		self.assertEqual(lap.speed_avg, Decimal('0'))
		self.assertEqual(lap.speed_max, Decimal('0'))
		act.delete()


	def test_gpx(self):
		"""
		Tests gpx file import and parsing with gps
		"""
		url="/activities/"
		self.client.login(username='test1', password='test1')

		testfile = open(os.path.join(django_settings.PROJECT_ROOT, 'examples', 'test.gpx'), 'r')
		response = self.client.post(url, {'trackfile': testfile})
		self.assertEqual(response.status_code, 302)

		act=Activity.objects.get(pk=1)
		self.assertTrue(os.path.isfile(act.track.trackfile.path + ".gpx"))

		self.assertEqual(act.time_elapsed, 12068)
		self.assertEqual(act.time, 9983)
		self.assertEqual(act.distance, Decimal('10.076'))
		self.assertEqual(act.elevation_min, 1005)
		self.assertEqual(act.elevation_max, 1519)
		self.assertEqual(act.elevation_gain, 674)
		self.assertEqual(act.elevation_loss, 170)
		self.assertEqual(act.speed_avg, Decimal('3.6'))
		self.assertEqual(act.speed_max, Decimal('6.1'))

		act.delete()
