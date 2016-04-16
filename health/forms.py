from django import forms

import health.models


class GoalForm(forms.ModelForm):
	class Meta:
		model = health.models.Goal
		fields = ['due_date', 'target_weight']


class WeightForm(forms.ModelForm):
	class Meta:
		model = health.models.Weight
		fields = ['weight', 'body_fat', 'body_water', 'bones_weight', 'muscles_weight', 'date']


class PulseForm(forms.ModelForm):
	class Meta:
		model = health.models.Pulse
		fields = ['date', 'rest', 'maximum']


class DeseaseForm(forms.ModelForm):
	class Meta:
		model = health.models.Desease
		fields = ['start_date', 'end_date', 'name', 'comment']
