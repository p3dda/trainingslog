from django.db import models
from django.contrib.auth.models import User


class Weight(models.Model):
	date = models.DateField(verbose_name='Datum')
	user = models.ForeignKey(User, null=True, blank=True)
	weight = models.DecimalField(max_digits=4, decimal_places=1, verbose_name='Gewicht')
	body_fat = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name='Koerperfett')
	body_water = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name='Wasseranteil')
	bones_weight = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name='Knochenmasse')
	muscles_weight = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name='Muskelmasse')

	def __unicode__(self):
		return str(self.weight)


class Goal(models.Model):
	date = models.DateField()
	user = models.ForeignKey(User, null=True, blank=True)
	due_date = models.DateField(verbose_name='Zieldatum')
	target_weight = models.DecimalField(max_digits=4, decimal_places=1, verbose_name='Zielgewicht')


class Pulse(models.Model):
	date = models.DateField(verbose_name='Datum')
	user = models.ForeignKey(User, null=True, blank=True)
	rest = models.IntegerField(null=True, blank=True, verbose_name='Ruhepuls')
	maximum = models.IntegerField(null=True, blank=True, verbose_name='Maximalpuls')


class Desease(models.Model):
	start_date = models.DateField(verbose_name='Beginn')
	end_date = models.DateField(verbose_name='Ende')
	name = models.CharField(max_length=200)
	comment = models.TextField(blank=True)
	user = models.ForeignKey(User, null=True, blank=True)
