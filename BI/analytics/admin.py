from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import Dataset, Dashboard, Widget, CalculatedMeasure, Organization, ActivityLog, UserProfile

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name = 'User ID & Account Security Settings'
    verbose_name_plural = 'User ID & Account Security Settings'
    fields = ('login_id', 'must_change_password', 'failed_login_attempts', 'locked_until', 'is_totp_enabled')
    extra = 0

try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Single unified Admin screen for managing User ID, Password, Active status, and Lock status.
    Administrator rights are reserved for Manjunath.
    """
    inlines = (UserProfileInline,)
    list_display = ('username', 'get_login_id', 'email', 'get_role', 'get_lock_status', 'must_change_password_status', 'is_active')
    list_filter = ('is_active', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email', 'profile__login_id')

    def get_login_id(self, obj):
        profile = getattr(obj, 'profile', None)
        return profile.login_id if (profile and profile.login_id) else obj.username
    get_login_id.short_description = 'User ID'

    def get_role(self, obj):
        profile = getattr(obj, 'profile', None)
        if (profile and profile.is_admin) or obj.is_superuser or obj.username.lower() == 'manjunath':
            return format_html('<span style="color:#38bdf8; font-weight:bold;"><i class="fa fa-shield"></i> Administrator</span>')
        return format_html('<span style="color:#94a3b8;">User</span>')
    get_role.short_description = 'Access Level'

    def get_lock_status(self, obj):
        profile = getattr(obj, 'profile', None)
        if profile and profile.is_locked():
            return format_html('<span style="color:#ef4444; font-weight:bold;">🔒 Locked ({} tries)</span>', profile.failed_login_attempts)
        elif profile and profile.failed_login_attempts > 0:
            return format_html('<span style="color:#f59e0b;">⚠️ {} failed</span>', profile.failed_login_attempts)
        return format_html('<span style="color:#22c55e;">✓ Normal</span>')
    get_lock_status.short_description = 'Lock Status'

    def must_change_password_status(self, obj):
        profile = getattr(obj, 'profile', None)
        if profile and profile.must_change_password:
            return format_html('<span style="color:#f59e0b; font-weight:bold;">Yes (Pending)</span>')
        return format_html('<span style="color:#94a3b8;">No</span>')
    must_change_password_status.short_description = 'Reset on Next Login'

    def save_model(self, request, obj, form, change):
        is_new = obj.pk is None
        old_active = None
        if not is_new:
            orig = User.objects.filter(pk=obj.pk).first()
            old_active = orig.is_active if orig else None

        super().save_model(request, obj, form, change)

        profile, _ = UserProfile.objects.get_or_create(user=obj)
        if not profile.login_id:
            profile.login_id = obj.username
            profile.save(update_fields=['login_id'])

        from .services import AuditLogger
        if is_new:
            AuditLogger.log_action(request.user, 'USER_CREATE', 'User', obj.id, {
                'username': obj.username,
                'email': obj.email,
                'is_active': obj.is_active
            }, request)
        elif old_active is not None and old_active != obj.is_active:
            action = 'USER_ENABLE' if obj.is_active else 'USER_DISABLE'
            AuditLogger.log_action(request.user, action, 'User', obj.id, {
                'username': obj.username,
                'is_active': obj.is_active
            }, request)

    def save_formset(self, request, form, formset, change):
        super().save_formset(request, form, formset, change)
        from .services import AuditLogger
        if formset.model == UserProfile:
            for inline_form in formset.forms:
                if inline_form.has_changed():
                    changed = inline_form.changed_data
                    profile_obj = inline_form.instance
                    AuditLogger.log_action(request.user, 'USER_PROFILE_UPDATE', 'UserProfile', profile_obj.id, {
                        'user': profile_obj.user.username,
                        'changed_fields': changed,
                        'login_id': profile_obj.login_id,
                        'role': profile_obj.role,
                        'must_change_password': profile_obj.must_change_password
                    }, request)

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