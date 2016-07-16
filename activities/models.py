#!/usr/bin/python
# -*- coding: utf-8 -*-

# import os

from django.db import models
from django.contrib.auth.models import User


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
	distance = models.IntegerField("Distance offset", default=0, blank=True, null=False)
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
	name = models.CharField('Name', max_length=200)
	comment = models.TextField('Kommentar', blank=True)
	sport = models.ForeignKey(Sport, blank=True, null=True)
	equipment = models.ManyToManyField(Equipment, blank=True)
	user = models.ForeignKey(User, null=True, blank=True)
	track = models.ForeignKey(Track, null=True, blank=True)

	cadence_avg = models.IntegerField('Trittfrequenz avg', blank=True, null=True)
	cadence_max = models.IntegerField('Trittfrequenz max', blank=True, null=True)
	calories = models.IntegerField('Kalorien', blank=True, null=True)
	calorie_formula = models.ForeignKey(CalorieFormula, verbose_name='Kalorienformel', null=True, blank=True)
	distance = models.DecimalField('Distanz', max_digits=7, decimal_places=3, blank=True, null=True)
	elevation_gain = models.IntegerField('Positiver Höhenunterschied', blank=True, null=True)
	elevation_loss = models.IntegerField('Negativer Höhenunterschied', blank=True, null=True)
	elevation_min = models.IntegerField('Höhe max', blank=True, null=True)
	elevation_max = models.IntegerField('Höhe min', blank=True, null=True)
	hf_max = models.IntegerField('HF max', blank=True, null=True)
	hf_avg = models.IntegerField('HF avg', blank=True, null=True)
	public = models.BooleanField('Öffentlich', default=False)
	speed_max = models.DecimalField('Geschwindigkeit max', max_digits=4, decimal_places=1, blank=True, null=True)
	speed_avg = models.DecimalField('Geschwindigkeit avg', max_digits=4, decimal_places=1, blank=True, null=True)
	speed_avg_movement = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
	time_elapsed = models.IntegerField('Gesamtzeit', blank=True, null=True)
	time_movement = models.IntegerField('Zeit in Bewegung', blank=True, null=True)

	weather_stationname = models.CharField('Wetterstation', max_length=200, blank=True, null=True)
	weather_temp = models.DecimalField('Temperatur', max_digits=3, decimal_places=1, blank=True, null=True)
	weather_rain = models.DecimalField('Niederschlag', max_digits=3, decimal_places=1, blank=True, null=True)
	weather_hum = models.IntegerField('Luftfeuchtigkeit', blank=True, null=True)
	weather_windspeed = models.DecimalField('Windgeschwindigkeit', max_digits=4, decimal_places=1, blank=True, null=True)
	weather_winddir = models.CharField('Windrichtung', max_length=20, blank=True, null=True)

	def __unicode__(self):
		return self.name

	class Meta:
		def __init__(self):
			pass

		abstract = True


class Activity(ActivityBaseClass):
	date = models.DateTimeField('Datum')
	event = models.ForeignKey(Event)
	time = models.IntegerField('Dauer')

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
