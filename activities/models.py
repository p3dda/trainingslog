import os

from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
import django.core.exceptions

# import libs.fields.encryptedfields


class Parameters(models.Model):
	"""A model that represents a dictionary. This model implements most of the dictionary interface,
	allowing it to be used like a python dictionary.

	"""
	# name = models.CharField(max_length=255)
	content_type = models.ForeignKey(ContentType)
	object_id = models.PositiveIntegerField()
	content_object = generic.GenericForeignKey('content_type', 'object_id')

	@staticmethod
	def getDict(name):
		"""Get the Dictionary of the given name.

		"""
		df = Parameters.objects.select_related().get(name=name)

		return df

	def __getitem__(self, key):
		"""Returns the value of the selected key.

		"""
		return self.keyvaluepair_set.get(key=key).value

	def __setitem__(self, key, value):
		"""Sets the value of the given key in the Dictionary.

		"""
		try:
			kvp = self.keyvaluepair_set.get(key=key)

		except KeyValuePair.DoesNotExist:
			KeyValuePair.objects.create(container=self, key=key, value=value)

		else:
			kvp.value = value
			kvp.save()

	def __delitem__(self, key):
		"""Removed the given key from the Dictionary.

		"""
		try:
			kvp = self.keyvaluepair_set.get(key=key)

		except KeyValuePair.DoesNotExist:
			raise KeyError

		else:
			kvp.delete()

	def __len__(self):
		"""Returns the length of this Dictionary.

		"""
		return self.keyvaluepair_set.count()

	def iterkeys(self):
		"""Returns an iterator for the keys of this Dictionary.

		"""
		return iter(kvp.key for kvp in self.keyvaluepair_set.all())

	def itervalues(self):
		"""Returns an iterator for the keys of this Dictionary.

		"""
		return iter(kvp.value for kvp in self.keyvaluepair_set.all())

	__iter__ = iterkeys

	def iteritems(self):
		"""Returns an iterator over the tuples of this Dictionary.

		"""
		return iter((kvp.key, kvp.value) for kvp in self.keyvaluepair_set.all())

	def keys(self):
		"""Returns all keys in this Dictionary as a list.

		"""
		return [kvp.key for kvp in self.keyvaluepair_set.all()]

	def values(self):
		"""Returns all values in this Dictionary as a list.

		"""
		return [kvp.value for kvp in self.keyvaluepair_set.all()]

	def items(self):
		"""Get a list of tuples of key, value for the items in this Dictionary.
		This is modeled after dict.items().

		"""
		return [(kvp.key, kvp.value) for kvp in self.keyvaluepair_set.all()]

	def get(self, key, default=None):
		"""Gets the given key from the Dictionary. If the key does not exist, it
		returns default.

		"""
		try:
			return self[key]

		except KeyError:
			return default

	def has_key(self, key):
		"""Returns true if the Dictionary has the given key, false if not.

		"""
		return self.contains(key)

	def contains(self, key):
		"""Returns true if the Dictionary has the given key, false if not.

		"""
		try:
			self.keyvaluepair_set.get(key=key)
			return True

		except KeyValuePair.DoesNotExist:
			return False

	def clear(self):
		"""Deletes all keys in the Dictionary.

		"""
		self.keyvaluepair_set.all().delete()

	def __unicode__(self):
		"""Returns a unicode representation of the Dictionary.

		"""
		return unicode(self.asPyDict())

	def asPyDict(self):
		"""Get a python dictionary that represents this Dictionary object.
		This object is read-only.

		"""
		fieldDict = dict()

		for kvp in self.keyvaluepair_set.all():
			fieldDict[kvp.key] = kvp.value

		return fieldDict


class KeyValuePair(models.Model):
	"""A Key-Value pair with a pointer to the Dictionary that owns it.

	"""
	container = models.ForeignKey(Parameters, db_index=True)
	key = models.CharField(max_length=240, db_index=True)
	value = models.CharField(max_length=240, db_index=True)


def user_params_get_or_create(obj):
	try:
		return Parameters.objects.get(content_type__pk=ContentType.objects.get_for_model(obj).id, object_id=obj.id)
	except django.core.exceptions.ObjectDoesNotExist:
		params = Parameters(content_type=ContentType.objects.get_for_model(obj), object_id=obj.id)
		params.save()
		return params


User.params = property(lambda u: user_params_get_or_create(u))


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
