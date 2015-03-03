# encoding: utf-8
from django import forms
from activities.models import Activity, Equipment, Event, UserProfile, Dictionary


class UserProfileForm(forms.ModelForm):
	PARAMS = [
		('trainingslog.sync.imap.enable', forms.BooleanField),
		('trainingslog.sync.imap.host', forms.CharField),
		('trainingslog.sync.imap.user', forms.CharField),
		('trainingslog.sync.imap.password', forms.CharField),
		('trainingslog.sync.imap.mailbox', forms.CharField)
	]

	def __init__(self, user, *args, **kw):
		self.user = user
		super(UserProfileForm, self).__init__(*args, **kw)

		profile = self.user.profile
		# check if profile has dynamic parameters. If not, initialize
		if not profile.params:
			params = Dictionary()
			params.save()
			profile.params = params
			profile.save()

		self.fields['gc_username'].initial = profile.gc_username
		self.fields['gc_password'].initial = profile.gc_password

		for (param, formtype) in self.PARAMS:
			self.fields[param] = formtype()
			if param in profile.params:
				self.fields[param].initial = profile.params[param]

		# self.fields.keyOrder = [
		# 	'gc_username',
		# 	'gc_password',
		# ]

	def save(self, *args, **kw):
		profile = self.user.profile
		profile.gc_username = self.cleaned_data.get('gc_username', )
		profile.gc_password = self.cleaned_data.get('gc_password')

		for (param, _) in self.PARAMS:
			value = self.cleaned_data.get(param)
			profile.params[param] = value
		profile.save()

	class Meta:
		model = UserProfile
		exclude = ['user', 'params']
		widgets = {
			'gc_password': forms.PasswordInput()
		}


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
