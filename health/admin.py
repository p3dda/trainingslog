from health.models import Weight, Goal, Pulse
from django.contrib import admin


class WeightAdmin(admin.ModelAdmin):
	list_display = ('weight', 'date', 'user')

	def save_model(self, request, obj, form, change):
		if not change:
			obj.user = request.user
		obj.save()

	def get_queryset(self, request):
		if request.user.is_superuser:
			return Weight.objects.all()
		return Weight.objects.filter(user=request.user)

	def has_change_permission(self, request, obj=None):
		has_class_permission = super(WeightAdmin, self).has_change_permission(request, obj)
		if not has_class_permission:
			return False
		if obj is not None and not request.user.is_superuser and request.user != obj.user:
			return False
		return True


class GoalAdmin(admin.ModelAdmin):
	list_display = ('target_weight', 'date', 'due_date', 'user')

	def save_model(self, request, obj, form, change):
		if not change:
			obj.user = request.user
		obj.save()

	def get_queryset(self, request):
		if request.user.is_superuser:
			return Goal.objects.all()
		return Goal.objects.filter(user=request.user)

	def has_change_permission(self, request, obj=None):
		has_class_permission = super(GoalAdmin, self).has_change_permission(request, obj)
		if not has_class_permission:
			return False
		if obj is not None and not request.user.is_superuser and request.user != obj.user:
			return False
		return True


class PulseAdmin(admin.ModelAdmin):
	list_display = ('rest', 'maximum', 'date', 'user')

	def save_model(self, request, obj, form, change):
		if not change:
			obj.user = request.user
		obj.save()

	def get_queryset(self, request):
		if request.user.is_superuser:
			return Pulse.objects.all()
		return Pulse.objects.filter(user=request.user)

	def has_change_permission(self, request, obj=None):
		has_class_permission = super(PulseAdmin, self).has_change_permission(request, obj)
		if not has_class_permission:
			return False
		if obj is not None and not request.user.is_superuser and request.user != obj.user:
			return False
		return True
admin.site.register(Weight, WeightAdmin)
admin.site.register(Goal, GoalAdmin)
admin.site.register(Pulse, PulseAdmin)
