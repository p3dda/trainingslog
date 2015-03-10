from activities.models import Activity
from activities.models import Equipment
from activities.models import Event
from activities.models import Sport
from django.contrib import admin


class ActivityAdmin(admin.ModelAdmin):
	list_display = ('name', 'user')

	def save_model(self, request, obj, form, change):
		if not change:
			obj.user = request.user
		obj.save()

	def queryset(self, request):
		if request.user.is_superuser:
			return Activity.objects.all()
		return Activity.objects.filter(user=request.user)

	def has_change_permission(self, request, obj=None):
		has_class_permission = super(ActivityAdmin, self).has_change_permission(request, obj)
		if not has_class_permission:
			return False
		if obj is not None and not request.user.is_superuser and request.user != obj.user:
			return False
		return True


class EquipmentAdmin(admin.ModelAdmin):
	list_display = ('name', 'user')

	def save_model(self, request, obj, form, change):
		if not change:
			obj.user = request.user
		obj.save()

	def queryset(self, request):
		if request.user.is_superuser:
			return Equipment.objects.all()
		return Equipment.objects.filter(user=request.user)

	def has_change_permission(self, request, obj=None):
		has_class_permission = super(EquipmentAdmin, self).has_change_permission(request, obj)
		if not has_class_permission:
			return False
		if obj is not None and not request.user.is_superuser and request.user != obj.user:
			return False
		return True


class SportAdmin(admin.ModelAdmin):
	list_display = ('name', 'color', 'user', 'speed_as_pace')

	def save_model(self, request, obj, form, change):
		if not change:
			obj.user = request.user
		obj.save()

	def queryset(self, request):
		if request.user.is_superuser:
			return Sport.objects.all()
		return Sport.objects.filter(user=request.user)

	def has_change_permission(self, request, obj=None):
		has_class_permission = super(SportAdmin, self).has_change_permission(request, obj)
		if not has_class_permission:
			return False
		if obj is not None and not request.user.is_superuser and request.user != obj.user:
			return False
		return True


class EventAdmin(admin.ModelAdmin):
	list_display = ('name', 'user')

	def save_model(self, request, obj, form, change):
		if not change:
			obj.user = request.user
		obj.save()

	def queryset(self, request):
		if request.user.is_superuser:
			return Event.objects.all()
		return Event.objects.filter(user=request.user)

	def has_change_permission(self, request, obj=None):
		has_class_permission = super(EventAdmin, self).has_change_permission(request, obj)
		if not has_class_permission:
			return False
		if obj is not None and not request.user.is_superuser and request.user != obj.user:
					return False
		return True


admin.site.register(Activity, ActivityAdmin)
admin.site.register(Equipment, EquipmentAdmin)
admin.site.register(Event, EventAdmin)
admin.site.register(Sport, SportAdmin)
