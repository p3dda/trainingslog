from django.db import models
from django.contrib.auth.models import User


class Weight(models.Model):
	date = models.DateField()
	user = models.ForeignKey(User, null=True, blank=True)
	weight = models.DecimalField(max_digits=4, decimal_places=1)
	body_fat = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
	body_water = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
	bones_weight = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
	muscles_weight = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)

	def __unicode__(self):
		return str(self.weight)


class Goal(models.Model):
	date = models.DateField()
	user = models.ForeignKey(User, null=True, blank=True)
	due_date = models.DateField()
	target_weight = models.DecimalField(max_digits=4, decimal_places=1)


class Pulse(models.Model):
	date = models.DateField()
	user = models.ForeignKey(User, null=True, blank=True)
	rest = models.IntegerField(null=True, blank=True)
	maximum = models.IntegerField(null=True, blank=True)


class Desease(models.Model):
	start_date = models.DateField()
	end_date = models.DateField()
	name = models.CharField(max_length=200)
	comment = models.TextField(blank=True)
	user = models.ForeignKey(User, null=True, blank=True)
