"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
import json
import os
from decimal import Decimal
from activities.models import Activity, CalorieFormula, Lap
import activities.utils
from activities.extras.activityfile import ActivityFile
import django.test.client
from django.test import TestCase

from django.conf import settings as django_settings
from django.core.urlresolvers import reverse


class ActivityTest(TestCase):
	fixtures = ['activities_testdata.json', 'activities_tests_authdata.json']

	def setUp(self):
		self.client = django.test.client.Client()

	# def tearDown(self):
	# 	Activity.objects.all().delete

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
		url = "/activities/"

		self.client.login(username='test1', password='test1')

		resp = self.client.get(url, {"id": 1})
		self.assertEqual(resp.status_code, 200)

		testfile = open(os.path.join(django_settings.PROJECT_ROOT, 'examples', 'nogps.tcx'), 'r')
		response = self.client.post(url, {'trackfile': testfile})
		self.assertEqual(response.status_code, 302)

		nogps_act = Activity.objects.get(pk=1)
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
		url = "/activities/"
		self.client.login(username='test1', password='test1')

		testfile = open(os.path.join(django_settings.PROJECT_ROOT, 'examples', 'run.tcx'), 'r')
		response = self.client.post(url, {'trackfile': testfile})
		self.assertEqual(response.status_code, 302)

		act = Activity.objects.get(pk=1)
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
		self.assertTrue('altitude' in pdata)
		self.assertEqual(len(pdata['altitude']), 804)
		self.assertTrue('cadence' in pdata)
		self.assertEqual(pdata['cadence'], [])
		self.assertTrue('speed' in pdata)
		self.assertTrue('speed_foot' in pdata)

		self.assertIsInstance(ddata, dict)
		self.assertEqual(ddata, {})

		act.delete()

	def test_tcx_bike(self):
		"""
		Tests tcx file import and parsing with gps
		"""
		url = "/activities/"
		self.client.login(username='test1', password='test1')

		testfile = open(os.path.join(django_settings.PROJECT_ROOT, 'examples', 'bike.tcx'), 'r')
		response = self.client.post(url, {'trackfile': testfile})
		self.assertEqual(response.status_code, 302)

		act = Activity.objects.get(pk=1)
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

		summary = activities.utils.activities_summary(Activity.objects.all())
		self.assertEqual(summary['total_time'], act.time)
		self.assertEqual(summary['total_distance'], float(act.distance))
		self.assertEqual(summary['total_calories'], act.calories)
		self.assertEqual(summary['total_elev_gain'], act.elevation_gain)
		self.assertEqual(summary['total_time_str'], activities.utils.seconds_to_time(act.time))
		act.delete()

	def test_tcx_communicator_plugin(self):
		"""
		Tests tcx file import and parsing with gps
		"""
		url = "/activities/"
		self.client.login(username='test1', password='test1')

		with open(os.path.join(django_settings.PROJECT_ROOT, 'examples', 'bike.tcx'), 'r') as tcxfile:
			tcx_content = tcxfile.read()

		response = self.client.post(url, {'content': tcx_content, 'filename': 'test.tcx'})
		self.assertEqual(response.status_code, 200)

		act = Activity.objects.get(pk=1)
		self.assertTrue(os.path.isfile(act.track.trackfile.path + ".gpx"))
		self.assertEqual(act.time_elapsed, 7723)
		self.assertEqual(act.time, 4857)

	def test_fit_bike(self):
		"""
		Tests fit file import and parsing with gps and cadence
		"""
		url = "/activities/"
		self.client.login(username='test1', password='test1')

		testfile = open(os.path.join(django_settings.PROJECT_ROOT, 'examples', 'bike_powermeter.fit'), 'r')
		response = self.client.post(url, {'trackfile': testfile})
		self.assertEqual(response.status_code, 302)
		act = Activity.objects.get(pk=1)
		self.assertTrue(os.path.isfile(act.track.trackfile.path + ".gpx"))

		laps = Lap.objects.filter(activity=act)
		self.assertEqual(len(laps), 5)
		self.assertEqual(act.distance, Decimal('77.248'))
		self.assertEqual(act.time, 9309)
		self.assertEqual(act.time_elapsed, 10895)

		act_track = ActivityFile.ActivityFile(act.track)
		self.assertEqual(len(act_track.track_data["hf"]), 9327)
		self.assertEqual(len(act_track.track_data["cad"]), 9214)
		self.assertEqual(len(act_track.track_data["power"]), 9335)
		self.assertEqual(len(act_track.track_by_distance), 9271)

		self.assertEqual(act.elevation_min, 52)
		self.assertEqual(act.elevation_max, 237)
		self.assertEqual(act.cadence_avg, 91)
		self.assertEqual(act.cadence_max, 123)

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
		self.assertTrue('altitude' in pdata)
		self.assertEqual(len(pdata['altitude']), 9343)
		self.assertTrue('cadence' in pdata)
		self.assertNotEqual(pdata['cadence'], [])
		self.assertTrue('speed' in pdata)
		self.assertTrue('power' in pdata)
		self.assertNotEqual(pdata['power'], [])
		self.assertIsInstance(ddata, dict)
		self.assertEqual(ddata["training_stress_score"], 123.7)
		self.assertEqual(ddata["normalized_power"], 208)

	def test_fit_run(self):
		"""
		Tests fit file import and parsing with gps and cadence
		"""
		url = "/activities/"
		self.client.login(username='test1', password='test1')

		testfile = open(os.path.join(django_settings.PROJECT_ROOT, 'examples', '16MileLongRun.FIT'), 'r')
		response = self.client.post(url, {'trackfile': testfile})
		self.assertEqual(response.status_code, 302)
		act = Activity.objects.get(pk=1)
		self.assertTrue(os.path.isfile(act.track.trackfile.path + ".gpx"))

		laps = Lap.objects.filter(activity=act)
		self.assertEqual(len(laps), 24)
		self.assertEqual(act.distance, Decimal('26.049'))
		self.assertEqual(act.time, 6939)
		self.assertEqual(act.time_elapsed, 7135)

		act_track = ActivityFile.ActivityFile(act.track)
		self.assertEqual(len(act_track.track_data["hf"]), 6940)
		self.assertEqual(len(act_track.track_data["cad"]), 6940)
		self.assertEqual(len(act_track.track_by_distance), 6928)

		self.assertEqual(act.elevation_min, 9)   # FIXME: Garmin Connect reports 25; seems as if they filter spikes
		self.assertEqual(act.elevation_max, 68)  # FIXME: Garmin Connect reports 69; altitude is a float, do we floor?
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
		pdata = jsondata["plot_data"]
		ddata = jsondata["details_data"]
		self.assertTrue('altitude' in pdata)
		self.assertEqual(len(pdata['altitude']), 6940)
		self.assertTrue('cadence' in pdata)
		self.assertNotEqual(pdata['cadence'], [])
		self.assertTrue('speed' in pdata)
		self.assertTrue('speed_foot' in pdata)

		self.assertIsInstance(ddata, dict)
		self.assertEqual(ddata["avg_stance_time"], 240.6)

	def test_fit_nogps_upload(self):
		"""
		Tests tcx file upload and parsing without gps
		"""
		url = "/activities/"

		self.client.login(username='test1', password='test1')

		resp = self.client.get(url, {"id": 1})
		self.assertEqual(resp.status_code, 200)

		testfile = open(os.path.join(django_settings.PROJECT_ROOT, 'examples', 'bike_nogps.fit'), 'r')
		response = self.client.post(url, {'trackfile': testfile})
		self.assertEqual(response.status_code, 302)

		act = Activity.objects.get(pk=1)
		self.assertEqual(act.time_elapsed, 3285)
		self.assertEqual(act.weather_stationname, None)
		self.assertEqual(act.cadence_avg, 83)
		self.assertEqual(act.cadence_max, 111)

		act.delete()

		testfile = open(os.path.join(django_settings.PROJECT_ROOT, 'examples', 'bike_nogps_nospeed.fit'), 'r')
		response = self.client.post(url, {'trackfile': testfile})
		self.assertEqual(response.status_code, 302)

		act = Activity.objects.get(pk=2)
		self.assertEqual(act.distance, Decimal('0'))
		self.assertEqual(act.time, 4365)
		self.assertEqual(act.time_movement, None)
		self.assertEqual(act.speed_avg, Decimal('0'))
		self.assertEqual(act.speed_avg_movement, None)
		self.assertEqual(act.time_elapsed, 5023)
		self.assertEqual(act.cadence_avg, 90)
		self.assertEqual(act.cadence_max, 125)

		laps = Lap.objects.filter(activity=act)
		self.assertEqual(len(laps), 15)
		lap = laps[1]

		self.assertEqual(lap.distance, Decimal('0'))
		self.assertEqual(lap.speed_avg, Decimal('0'))
		self.assertEqual(lap.speed_max, Decimal('0'))
		act.delete()

	def test_fit_wahoo_bike(self):
		"""
		Tests wahoo fit file parsing
		"""
		url = "/activities/"
		self.client.login(username='test1', password='test1')

		testfile = open(os.path.join(django_settings.PROJECT_ROOT, 'examples', 'wahoo_elemnt_bike.fit'), 'r')
		response = self.client.post(url, {'trackfile': testfile})
		self.assertEqual(response.status_code, 302)
		act = Activity.objects.get(pk=1)
		self.assertTrue(os.path.isfile(act.track.trackfile.path + ".gpx"))

		laps = Lap.objects.filter(activity=act)
		self.assertEqual(len(laps), 3)
		self.assertEqual(act.distance, Decimal('60.768'))
		self.assertEqual(act.time, 7600)
		self.assertEqual(act.time_elapsed, 9940)

		act_track = ActivityFile.ActivityFile(act.track)
		self.assertEqual(len(act_track.track_data["hf"]), 7532)
		self.assertEqual(len(act_track.track_data["cad"]), 7433)
		self.assertEqual(len(act_track.track_data["power"]), 7533)
		self.assertEqual(len(act_track.track_by_distance), 7448)
		self.assertLess(max(act_track.track_by_distance.keys()), act.distance * 1000)

		self.assertEqual(act.elevation_min, 38)
		self.assertEqual(act.elevation_max, 261)
		self.assertEqual(act.cadence_avg, 72)
		self.assertEqual(act.cadence_max, 130)

		url = "/activities/1/"
		response = self.client.get(url)
		self.assertEqual(response.status_code, 200)

		url = "/activities/1/?p=plots"
		response = self.client.get(url)
		self.assertEqual(response.status_code, 200)
		jsondata = json.loads(response.content)

		self.assertIsInstance(jsondata, dict)
		ddata = jsondata["details_data"]
		self.assertIsInstance(ddata, dict)
		self.assertEqual(ddata["training_stress_score"], 115.3)
		self.assertEqual(ddata["normalized_power"], 216)

	def test_fit_wahoo_bike1(self):
		"""
		Tests wahoo fit file parsing
		"""
		url = "/activities/"
		self.client.login(username='test1', password='test1')

		testfile = open(os.path.join(django_settings.PROJECT_ROOT, 'examples', 'wahoo_elemnt_bike1.fit'), 'r')
		response = self.client.post(url, {'trackfile': testfile})
		self.assertEqual(response.status_code, 302)
		act = Activity.objects.get(pk=1)
		self.assertTrue(os.path.isfile(act.track.trackfile.path + ".gpx"))

		laps = Lap.objects.filter(activity=act)
		self.assertEqual(len(laps), 2)
		# self.assertEqual(act.distance, Decimal('60.768'))
		# self.assertEqual(act.time, 7600)
		# self.assertEqual(act.time_elapsed, 9940)
		#
		# act_track = ActivityFile.ActivityFile(act.track)
		# self.assertEqual(len(act_track.track_data["hf"]), 7532)
		# self.assertEqual(len(act_track.track_data["cad"]), 7433)
		# self.assertEqual(len(act_track.track_data["power"]), 7533)
		# self.assertEqual(len(act_track.track_by_distance), 7448)
		# self.assertLess(max(act_track.track_by_distance.keys()), act.distance * 1000)
		#
		# self.assertEqual(act.elevation_min, 38)
		# self.assertEqual(act.elevation_max, 261)
		# self.assertEqual(act.cadence_avg, 72)
		# self.assertEqual(act.cadence_max, 130)
		#
		# url = "/activities/1/"
		# response = self.client.get(url)
		# self.assertEqual(response.status_code, 200)
		#
		# url = "/activities/1/?p=plots"
		# response = self.client.get(url)
		# self.assertEqual(response.status_code, 200)
		# jsondata = json.loads(response.content)
		#
		# self.assertIsInstance(jsondata, dict)
		# ddata = jsondata["details_data"]
		# self.assertIsInstance(ddata, dict)
		# self.assertEqual(ddata["training_stress_score"], 115.3)
		# self.assertEqual(ddata["normalized_power"], 216)

	def test_vivofit_upload(self):
		"""
		Tests tcx file upload and parsing without gps
		"""
		url = "/activities/"

		self.client.login(username='test1', password='test1')

		resp = self.client.get(url, {"id": 1})
		self.assertEqual(resp.status_code, 200)

		testfile = open(os.path.join(django_settings.PROJECT_ROOT, 'examples', 'vivofit.fit'), 'r')
		response = self.client.post(url, {'trackfile': testfile})
		self.assertEqual(response.status_code, 302)

		act = Activity.objects.get(pk=1)
		self.assertEqual(act.time_elapsed, 4090)

		act.delete()

	def test_gpx(self):
		"""
		Tests gpx file import and parsing with gps
		"""
		url = "/activities/"
		self.client.login(username='test1', password='test1')

		testfile = open(os.path.join(django_settings.PROJECT_ROOT, 'examples', 'test.gpx'), 'r')
		response = self.client.post(url, {'trackfile': testfile})
		self.assertEqual(response.status_code, 302)

		act = Activity.objects.get(pk=1)
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

	def test_utils(self):
		"""
		Test helper methods from activities.utils module
		"""
		origin = (50.72000, 7.08000)  # Bonn
		destination = (50.03300, 8.56700)  # Frankfurt
		self.assertEqual(int(activities.utils.latlon_distance(origin, destination)), 130206)

		self.assertEqual(activities.utils.int_or_none(5), 5)
		self.assertEqual(activities.utils.int_or_none(2.4), 2)
		self.assertEqual(activities.utils.int_or_none("foo"), None)

		self.assertEqual(activities.utils.float_or_none(5), 5.0)
		self.assertEqual(activities.utils.float_or_none(2.4), 2.4)
		self.assertEqual(activities.utils.float_or_none("foo"), None)

		self.assertEqual(activities.utils.str_float_or_none(5), "5.0")
		self.assertEqual(activities.utils.str_float_or_none(2.4), "2.4")
		self.assertEqual(activities.utils.str_float_or_none("foo"), None)

		self.assertEqual(activities.utils.time_to_seconds("1:30:25"), 5425)
		self.assertEqual(activities.utils.time_to_seconds("1:30"), 90)

		self.assertEqual(activities.utils.seconds_to_time(1825), "30:25")
		self.assertEqual(activities.utils.seconds_to_time(1825, force_hour=True), "0:30:25")


class ActivityViewsTest(TestCase):
	fixtures = ['activities_testdata.json', 'activities_tests_authdata.json', 'activities_tests_actdata']

	def setUp(self):
		self.client = django.test.client.Client()

	# def tearDown(self):
	# 	for act in Activity.objects.all():
	# 		act.delete()

	def test_view_get_report_data(self):
		url = reverse('activities.views.get_report_data')

		self.client.login(username='test1', password='test1')

		resp = self.client.get(url, {"startdate": 1325376000000, "enddate": 13885344000000})
		response = json.loads(resp.content)
		self.assertEqual(response, {})

		resp = self.client.get(url, {"startdate": 1325376000000, "enddate": 1388534400000, "mode": "sports", "param": "eyJldmVudHMiOiBbM10sICJzcG9ydHMiOiBbMiwgM119"})
		response = json.loads(resp.content)
		self.assertIn('Laufen', response)
		self.assertIn('Rennrad', response)
		self.assertIn('Schwimmen', response)
		self.assertEquals(response['Schwimmen'], {u'total_time': 0, u'total_calories': 0, u'color': u'#66ccff', u'num_activities': 0, u'total_time_str': u'0:00:00', u'total_distance': 0.0, u'total_elev_gain': 0})
		self.assertEquals(response['Laufen'], {u'total_time': 11018, u'total_calories': 2493, u'color': u'#cc6600', u'num_activities': 2, u'total_time_str': u'3:03:38', u'total_distance': 37.808, u'total_elev_gain': 896})

		resp = self.client.get(url, {"startdate": 1325376000000, "enddate": 1388534400000, "mode": "weeks"})
		response = json.loads(resp.content)
		self.assertEqual(response, {u'count': [], u'distance': [], u'calories': [], u'time': []})

		resp = self.client.get(url, {"startdate": 1325376000000, "enddate": 1388534400000, "mode": "weeks", "param": "eyJldmVudHMiOiBbM10sICJzcG9ydHMiOiBbMiwgM119"})
		response = json.loads(resp.content)
		resp_time_bike = response["time"][1]  # by-week list of bike times
		self.assertEqual(len(resp_time_bike["data"]), 106)  # covering 106 weeks
		self.assertEqual(resp_time_bike["data"][0][1], 0)   # no activity in week 0
		self.assertEqual(resp_time_bike["data"][87][1], 80)  # activity in week 87

	def test_get_activity(self):
		url = reverse('activities.views.get_activity')

		self.client.login(username='test1', password='test1')
		resp = self.client.get(url, {"id": 1, "template": False})
		response = json.loads(resp.content)

		self.assertIn('preview_img', response)
		self.assertIn('activity', response)
		act = json.loads(response['activity'])
		self.assertEqual(len(act), 1)
		self.assertEqual(act[0]['fields']['speed_avg'], '13.5')

	def test_get_detail(self):
		url = "/activities/2/"
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 200)  # public activity

		url = "/activities/1/"
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 403)  # private activity, forbidden

		# now with login
		self.client.login(username='test1', password='test1')
		url = "/activities/1/"
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 200)

		# non-existing activity
		url = "/activities/5/"
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 404)

		# bad get request
		url = "/activities/2/?p=foobar"
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 400)

	def test_get_calendar(self):
		self.client.login(username='test1', password='test1')
		url = reverse('activities.views.calendar')
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 200)

	def test_calender_get_events(self):
		self.client.login(username='test1', password='test1')
		url = reverse('activities.views.calendar_get_events')

		resp = self.client.get(url, {"start": 1325376000, "end": 1388534400, "sports": '[1, 2, 3]'})
		response = json.loads(resp.content)
		self.assertEqual(len(response), 6)
		self.assertEqual(response[0]["allDay"], False)
		self.assertEqual(response[0]["start"], '2013-10-31T15:58:00+00:00')
		self.assertEqual(response[0]["className"], 'fc_activity')

		self.assertEqual(response[3]["allDay"], True)
		self.assertEqual(response[3]["className"], 'fc-event-weeksummary')

	def test_get_sport(self):
		self.client.login(username='test1', password='test1')
		url = reverse('activities.views.get_sport')
		resp = self.client.get(url, {"id": 1})
		self.assertEqual(resp.status_code, 200)
		response = json.loads(resp.content)
		self.assertEqual(len(response), 1)
		self.assertEqual(response[0]['model'], 'activities.sport')
		self.assertEqual(response[0]['fields']['name'], 'Schwimmen')

		resp = self.client.get(url, {"id": 4})
		self.assertEqual(resp.status_code, 403)


class ActivityViewsDeleteTest(TestCase):
	fixtures = ['activities_testdata.json', 'activities_tests_authdata.json', 'activities_tests_actdata']

	def setUp(self):
		self.client = django.test.client.Client()

	def test_delete_activity(self):
		url = reverse('activities.views.delete_activity')
		self.client.login(username='test1', password='test1')

		# Delete activity
		resp = self.client.post(url, {'id': 1})
		response = json.loads(resp.content)
		self.assertDictEqual(response, {'success': True})

		# Try to delete activity again
		resp = self.client.post(url, {'id': 1})
		response = json.loads(resp.content)
		self.assertDictEqual(response, {'success': False, 'msg': 'DoesNotExist'})

		# Try to delete foreign activity
		resp = self.client.post(url, {'id': 4})
		response = json.loads(resp.content)
		self.assertDictEqual(response, {'success': False, 'msg': "Permission denied"})

		# Try to delete without ID
		resp = self.client.post(url, {})
		response = json.loads(resp.content)
		self.assertDictEqual(response, {'success': False, 'msg': 'Missing ID'})

	def test_delete_sport(self):
		url = reverse('activities.views.delete_sport')
		self.client.login(username='test1', password='test1')

		# Delete sport
		resp = self.client.post(url, {'id': 1})
		response = json.loads(resp.content)
		self.assertEqual(response, [True])

		# Try to delete sport again
		resp = self.client.post(url, {'id': 1})
		response = json.loads(resp.content)
		self.assertEqual(response, [False, 'DoesNotExist'])

		# Try to delete foreign sport
		resp = self.client.post(url, {'id': 4})
		response = json.loads(resp.content)
		self.assertEqual(response, [False, "Permission denied"])
