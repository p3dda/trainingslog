# encoding: utf-8
from django import forms
from django.conf import settings as django_settings
from activities.models import Activity, Equipment, Event
import libs.crypto.cipher
import django.core.exceptions


class UserProfileForm(forms.Form):
	PARAMS = [
		('sync_imap_enable', forms.BooleanField(required=False), False),
		('sync_imap_host', forms.CharField(required=False), None),
		('sync_imap_user', forms.CharField(required=False), None),
		('sync_imap_password', forms.CharField(required=False, widget=forms.PasswordInput), None),
		('sync_imap_mailbox', forms.CharField(required=False), None),
		('sync_garminconnect_enable', forms.BooleanField(required=False), False),
		('sync_garminconnect_username', forms.CharField(required=False), None),
		('sync_garminconnect_password', forms.CharField(required=False, widget=forms.PasswordInput), None),
		('frontend_garminplugin_enable', forms.BooleanField(required=False), True)
	]

	def __init__(self, user, *args, **kw):
		self.user = user
		self.cipher = libs.crypto.cipher.AESCipher(django_settings.ENCRYPTION_KEY)

		super(UserProfileForm, self).__init__(*args, **kw)

		for (param, formtype, required) in self.PARAMS:
			self.fields[param] = formtype
			if param in self.user.params:
				# if param in ['sync.imap.enable', 'sync.garminconnect.enable']:
				# 	value = self.user.params[param] == 'True'
				if param in ['sync_imap_password', 'sync_garminconnect_password']:
					value = ''
				else:
					value = self.user.params[param]
				self.fields[param].initial = value

	def save(self, *args, **kw):
		for param in self.changed_data:
			value = self.cleaned_data.get(param)
			if value is not None:
				if param in ['sync_imap_password', 'sync_garminconnect_password']:
					self.user.params[param] = self.cipher.encrypt(value)
				else:
					self.user.params[param] = value

	def clean(self):
		cleaned_data = super(UserProfileForm, self).clean()

		for field in ['sync_imap_password', 'sync_garminconnect_password']:
			if len(self.cleaned_data[field]) == 0:
				try:
					self.cleaned_data[field] = self.user.params[field]
				except django.core.exceptions.ObjectDoesNotExist:
					pass

		for field in ['sync_imap_enable', 'sync_garminconnect_enable']:
			if cleaned_data[field] is not True:
				cleaned_data[field] = False
		return cleaned_data


class ActivityForm(forms.ModelForm):
	class Meta:
		def __init__(self):
			pass

		model = Activity
		fields = ('name', 'comment', 'date', 'event', 'sport', 'equipment', 'cadence_avg', 'cadence_max',
				'calories', 'distance', 'elevation_gain', 'elevation_loss', 'elevation_min', 'elevation_max',
				'hf_max', 'hf_avg', 'speed_max', 'speed_avg', 'speed_avg_movement',
				'time', 'time_elapsed', 'time_movement')


class EquipmentForm(forms.ModelForm):
	class Meta:
		def __init__(self):
			pass

		model = Equipment
		fields = ('name', 'description')


class EventForm(forms.ModelForm):
	class Meta:
		def __init__(self):
			pass

		model = Event
		fields = ('name', )
