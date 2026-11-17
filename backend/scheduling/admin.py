from django.contrib import admin

from .models import DayOff, TechnicianProfile, WeeklyShift


class ShiftInline(admin.TabularInline):
    model = WeeklyShift
    extra = 0


class DayOffInline(admin.TabularInline):
    model = DayOff
    extra = 0


@admin.register(TechnicianProfile)
class TechnicianProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "start_label", "zones_list")
    filter_horizontal = ("zones",)
    inlines = [ShiftInline, DayOffInline]

    @admin.display(description="المناطق")
    def zones_list(self, obj):
        return "، ".join(z.name for z in obj.zones.all())
