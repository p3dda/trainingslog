# encoding: utf-8
from django import forms
from activities.models import Activity, Equipment, Event

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
