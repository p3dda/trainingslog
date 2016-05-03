# encoding: utf-8
from django import forms
from activities.models import Activity, Equipment, Event, Sport


class ActivityForm(forms.ModelForm):
	def __init__(self, *args, **kwargs):
		user = kwargs.pop('user')
		super(ActivityForm, self).__init__(*args, **kwargs)
		self.fields['equipment'].queryset = Equipment.objects.filter(user=user)
		self.fields['equipment'].empty_label = '---'
		self.fields['sport'].queryset = Sport.objects.filter(user=user)
		self.fields['sport'].empty_label = '---'

	class Meta:
		model = Activity
		exclude = ['user', 'track']

		# fields = ('name', 'comment', 'date', 'event', 'sport', 'equipment', 'cadence_avg', 'cadence_max',
		# 		'calories', 'calorie_formula', 'distance', 'elevation_gain', 'elevation_loss', 'elevation_min', 'elevation_max',
		# 		'hf_max', 'hf_avg', 'speed_max', 'speed_avg', 'speed_avg_movement',
		# 		'time', 'time_elapsed', 'time_movement', 'public')


class EquipmentForm(forms.ModelForm):
	class Meta:
		def __init__(self):
			pass

		model = Equipment
		fields = ('name', 'description', 'distance')


class EventForm(forms.ModelForm):
	class Meta:
		def __init__(self):
			pass

		model = Event
		fields = ('name', )

class SportForm(forms.ModelForm):
	class Meta:
		def __init__(self):
			pass
		model = Sport
		fields = ('name', 'color', 'speed_as_pace', 'calorie_formula',)
