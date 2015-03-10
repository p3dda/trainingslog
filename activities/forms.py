# encoding: utf-8
from django import forms
from activities.models import Activity, Equipment, Event

class UserProfileForm(forms.Form):
	PARAMS = [
		('sync.imap.enable', forms.BooleanField(required=False)),
		('sync.imap.host', forms.CharField(required=False)),
		('sync.imap.user', forms.CharField(required=False)),
		('sync.imap.password', forms.CharField(required=False, widget=forms.PasswordInput)),
		('sync.imap.mailbox', forms.CharField(required=False)),
		('sync.garminconnect.enable', forms.BooleanField(required=False)),
		('sync.garminconnect.username', forms.CharField(required=False)),
		('sync.garminconnect.password', forms.CharField(required=False, widget=forms.PasswordInput))
	]

	def __init__(self, user, *args, **kw):
		self.user = user
		super(UserProfileForm, self).__init__(*args, **kw)

		for (param, formtype) in self.PARAMS:
			self.fields[param] = formtype
			if param in self.user.params:
				if param in ['sync.imap.enable', 'sync.garminconnect.enable']:
					value = self.user.params[param] == 'True'
				else:
					value = self.user.params[param]
				print("KVP: %s:%s" % (param, repr(value)))
				self.fields[param].initial = value


	def save(self, *args, **kw):
		for param in self.changed_data:
			value = self.cleaned_data.get(param)
			print("KVP: %s:%s" % (param, repr(value)))
			if value is not None:
				self.user.params[param] = value

	def clean(self):
		cleaned_data = super(UserProfileForm, self).clean()

		for field in ['sync.imap.password', 'sync.garminconnect.password']:
			if len(self.cleaned_data[field]) == 0:
				self.cleaned_data[field] = self.user.params[field]

		for field in ['sync.imap.enable', 'sync.garminconnect.enable']:
			if cleaned_data[field] != True:
				print("Cleanup boolean value %s:%s to be False" % (field, repr(cleaned_data[field])))
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
