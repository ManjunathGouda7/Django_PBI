from django.contrib import admin
from django.utils.html import format_html
from .models import Dataset, Dashboard, Widget, CalculatedMeasure, Organization, ActivityLog

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'domain', 'plan', 'is_active', 'created_at')
    list_filter = ('plan', 'is_active')
    search_fields = ('name', 'domain')

@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'file_type', 'row_count', 'status', 'is_sample', 'created_at')
    list_filter = ('file_type', 'status', 'is_sample', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('row_count', 'column_schema', 'size_mb', 'created_at', 'updated_at')

@admin.register(Dashboard)
class DashboardAdmin(admin.ModelAdmin):
    list_display = ('title', 'dataset', 'theme', 'status', 'view_count', 'created_at')
    list_filter = ('theme', 'status', 'created_at')
    search_fields = ('title', 'description')

@admin.register(Widget)
class WidgetAdmin(admin.ModelAdmin):
    list_display = ('title', 'dashboard', 'visual_type', 'x_axis', 'y_axis', 'created_at')
    list_filter = ('visual_type', 'aggregation', 'created_at')
    search_fields = ('title', 'x_axis', 'y_axis')

@admin.register(CalculatedMeasure)
class CalculatedMeasureAdmin(admin.ModelAdmin):
    list_display = ('name', 'dataset', 'formula', 'created_at')
    search_fields = ('name', 'formula')

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action_type', 'resource_type', 'timestamp')
    list_filter = ('action_type', 'timestamp')
    search_fields = ('resource_type',)