from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import Dataset, Dashboard, Widget, CalculatedMeasure, Organization, ActivityLog, UserProfile

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name = 'User Profile & User ID'
    verbose_name_plural = 'User Profile & User ID'
    fields = ('login_id', 'role', 'is_totp_enabled', 'failed_login_attempts', 'locked_until')
    extra = 0

try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'get_login_id', 'email', 'get_role', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'profile__login_id')

    def get_login_id(self, obj):
        profile = getattr(obj, 'profile', None)
        return profile.login_id if (profile and profile.login_id) else obj.username
    get_login_id.short_description = 'User ID'

    def get_role(self, obj):
        profile = getattr(obj, 'profile', None)
        return profile.get_role_display() if profile else ('Administrator' if obj.is_superuser else 'Analyst')
    get_role.short_description = 'Role'

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('login_id', 'user', 'role', 'is_totp_enabled')
    list_filter = ('role', 'is_totp_enabled')
    search_fields = ('login_id', 'user__username', 'user__email')
    autocomplete_fields = ('user',)

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