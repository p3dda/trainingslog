import os

from django.db import models
from django.contrib.auth.models import User

import libs.fields.encryptedfields


class UserProfile(models.Model):
	user = models.ForeignKey(User, unique=True)
	gc_username = models.CharField(max_length=200, null=True, blank=True)
	gc_password = libs.fields.encryptedfields.EncryptedCharField(max_length=100, null=True, blank=True)


User.profile = property(lambda u: UserProfile.objects.get_or_create(user=u)[0])


class CalorieFormula(models.Model):
	#
	# kcal = weight_dist_factor * weight * distance /(kg * km) + weight_time_factor * weight * time /(kg * h)
	name = models.CharField(max_length=200)
	weight_dist_factor = models.FloatField(default=0.0)
	weight_time_factor = models.FloatField(default=0.0)
	public = models.BooleanField(default=False)
	user = models.ForeignKey(User, null=True, blank=True)

	def __unicode__(self):
		return self.name

	class Meta:
		ordering = ["name"]


class Equipment(models.Model):
	name = models.CharField(max_length=200)
	description = models.TextField(blank=True)
	distance = models.IntegerField(default=0, blank=True, null=False)
	archived = models.BooleanField(default=False)

	user = models.ForeignKey(User, null=True, blank=True)

	def __unicode__(self):
		return self.name

	class Meta:
		ordering = ["name"]


class Event(models.Model):
	name = models.CharField(max_length=200)
	user = models.ForeignKey(User, null=True, blank=True)

	def __unicode__(self):
		return self.name

	class Meta:
		ordering = ["name"]


class Sport(models.Model):
	name = models.CharField(max_length=200)
	color = models.CharField(max_length=10)
	user = models.ForeignKey(User, null=True, blank=True)
	speed_as_pace = models.BooleanField(default=False)
	calorie_formula = models.ForeignKey(CalorieFormula, null=True, blank=True)

	def __unicode__(self):
		return self.name

	class Meta:
		ordering = ["name"]


class Track(models.Model):
	trackfile = models.FileField(upload_to='uploads/tracks/%Y/%m/%d')
	preview_img = models.FileField(upload_to='uploads/previews/%Y/%m/%d', null=True)
	filetype = models.CharField(max_length=10, null=True)  # FIXME: Need database update procedure; set default "tcx"

	def delete(self, *args, **kwargs):
		files = []
		if self.trackfile:
			files.append(self.trackfile.path)
			files.append(self.trackfile.path + ".gpx")

		if self.preview_img:
			files.append(self.preview_img.path)

		for f in files:
			if os.path.exists(f):
				try:
					os.remove(f)
				except OSError:
					pass

		models.Model.delete(self, *args, **kwargs)


class ActivityBaseClass(models.Model):
	name = models.CharField(max_length=200)
	comment = models.TextField(blank=True)
	sport = models.ForeignKey(Sport, blank=True, null=True)
	equipment = models.ManyToManyField(Equipment, blank=True)
	user = models.ForeignKey(User, null=True, blank=True)
	track = models.ForeignKey(Track, null=True, blank=True)

	cadence_avg = models.IntegerField(blank=True, null=True)
	cadence_max = models.IntegerField(blank=True, null=True)
	calories = models.IntegerField(blank=True, null=True)
	calorie_formula = models.ForeignKey(CalorieFormula, null=True, blank=True)
	distance = models.DecimalField(max_digits=7, decimal_places=3, blank=True, null=True)
	elevation_gain = models.IntegerField(blank=True, null=True)
	elevation_loss = models.IntegerField(blank=True, null=True)
	elevation_min = models.IntegerField(blank=True, null=True)
	elevation_max = models.IntegerField(blank=True, null=True)
	hf_max = models.IntegerField('hf_max', blank=True, null=True)
	hf_avg = models.IntegerField('hf_avg', blank=True, null=True)
	public = models.BooleanField(default=False)
	speed_max = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
	speed_avg = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
	speed_avg_movement = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
	time_elapsed = models.IntegerField(blank=True, null=True)
	time_movement = models.IntegerField(blank=True, null=True)

	weather_stationname = models.CharField(max_length=200, blank=True, null=True)
	weather_temp = models.DecimalField(max_digits=3, decimal_places=1, blank=True, null=True)
	weather_rain = models.DecimalField(max_digits=3, decimal_places=1, blank=True, null=True)
	weather_hum = models.IntegerField(blank=True, null=True)
	weather_windspeed = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
	weather_winddir = models.CharField(max_length=20, blank=True, null=True)

	def __unicode__(self):
		return self.name

	class Meta:
		def __init__(self):
			pass

		abstract = True


class Activity(ActivityBaseClass):
	date = models.DateTimeField('date')
	event = models.ForeignKey(Event)
	time = models.IntegerField()

	class Meta:
		def __init__(self):
			pass

		verbose_name_plural = "Activities"

	def delete(self, *args, **kwargs):
		if self.track:
			self.track.delete()

		ActivityBaseClass.delete(self, *args, **kwargs)


class ActivityTemplate(ActivityBaseClass):
	date = models.DateTimeField('date', blank=True, null=True)
	event = models.ForeignKey(Event, blank=True, null=True)
	time = models.IntegerField(blank=True, null=True)

	class Meta:
		def __init__(self):
			pass

		verbose_name_plural = "ActivityTemplates"


class Lap(models.Model):
	activity = models.ForeignKey(Activity)
	date = models.DateTimeField('date')
	time = models.IntegerField()
	distance = models.DecimalField(max_digits=6, decimal_places=3, blank=True, null=True)
	speed_max = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
	speed_avg = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
	cadence_max = models.IntegerField(blank=True, null=True)
	cadence_avg = models.IntegerField(blank=True, null=True)
	calories = models.IntegerField(blank=True, null=True)
	elevation_gain = models.IntegerField(blank=True, null=True)
	elevation_loss = models.IntegerField(blank=True, null=True)
	elevation_min = models.IntegerField(blank=True, null=True)
	elevation_max = models.IntegerField(blank=True, null=True)
	hf_max = models.IntegerField('hf_max', blank=True, null=True)
	hf_avg = models.IntegerField('hf_avg', blank=True, null=True)
