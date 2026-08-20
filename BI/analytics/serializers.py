from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Organization, UserProfile, Dataset, Dashboard, Widget,
    CalculatedMeasure, DatasetColumn, DatasetTag, DatasetSharePermission,
    DashboardShare, ScheduledRefresh, ActivityLog,
    RowLevelSecurityRule, KPIAlertRule, WidgetComment
)

class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = '__all__'

class UserProfileSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'role', 'role_display']

class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joined', 'profile']
        read_only_fields = ['id', 'date_joined']

class DatasetColumnSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatasetColumn
        fields = '__all__'

class DatasetTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatasetTag
        fields = '__all__'

class DatasetSharePermissionSerializer(serializers.ModelSerializer):
    shared_username = serializers.CharField(source='user.username', read_only=True, default=None)

    class Meta:
        model = DatasetSharePermission
        fields = '__all__'
        read_only_fields = ['created_at']

class DashboardShareSerializer(serializers.ModelSerializer):
    shared_username = serializers.CharField(source='user.username', read_only=True, default=None)

    class Meta:
        model = DashboardShare
        fields = '__all__'
        read_only_fields = ['created_at']

class ScheduledRefreshSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, default=None)

    class Meta:
        model = ScheduledRefresh
        fields = '__all__'
        read_only_fields = ['created_at', 'last_run', 'next_run']

class RowLevelSecurityRuleSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True, default=None)

    class Meta:
        model = RowLevelSecurityRule
        fields = '__all__'
        read_only_fields = ['created_at']

class KPIAlertRuleSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, default=None)

    class Meta:
        model = KPIAlertRule
        fields = '__all__'
        read_only_fields = ['created_at', 'last_triggered']

class WidgetCommentSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = WidgetComment
        fields = '__all__'
        read_only_fields = ['created_at', 'user']

class DatasetSerializer(serializers.ModelSerializer):
    columns = DatasetColumnSerializer(many=True, read_only=True)
    share_permissions = DatasetSharePermissionSerializer(many=True, read_only=True)
    schedules = ScheduledRefreshSerializer(many=True, read_only=True)
    rls_rules = RowLevelSecurityRuleSerializer(many=True, read_only=True)
    owner_username = serializers.SerializerMethodField()

    class Meta:
        model = Dataset
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'size_mb']

    def get_owner_username(self, obj):
        return obj.created_by.username if obj.created_by else 'System'

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        return super().create(validated_data)

class WidgetSerializer(serializers.ModelSerializer):
    alerts = KPIAlertRuleSerializer(many=True, read_only=True)
    comments = WidgetCommentSerializer(many=True, read_only=True)

    class Meta:
        model = Widget
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

class DashboardSerializer(serializers.ModelSerializer):
    widgets = WidgetSerializer(many=True, read_only=True)
    shares = DashboardShareSerializer(many=True, read_only=True)
    dataset_name = serializers.CharField(source='dataset.name', read_only=True)
    owner_username = serializers.SerializerMethodField()

    class Meta:
        model = Dashboard
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'share_token']

    def get_owner_username(self, obj):
        return obj.created_by.username if obj.created_by else 'System'

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        return super().create(validated_data)

class CalculatedMeasureSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalculatedMeasure
        fields = '__all__'

class ActivityLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True, default='Anonymous')

    class Meta:
        model = ActivityLog
        fields = '__all__'
        read_only_fields = ['timestamp']

class DashboardBookmarkSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        from .models import DashboardBookmark
        model = DashboardBookmark
        fields = '__all__'
        read_only_fields = ['created_at', 'user']

class DashboardRevisionSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        from .models import DashboardRevision
        model = DashboardRevision
        fields = '__all__'
        read_only_fields = ['created_at', 'created_by']

class DatasetVersionSerializer(serializers.ModelSerializer):
    class Meta:
        from .models import DatasetVersion
        model = DatasetVersion
        fields = '__all__'
        read_only_fields = ['created_at']

class DataQualityReportSerializer(serializers.ModelSerializer):
    class Meta:
        from .models import DataQualityReport
        model = DataQualityReport
        fields = '__all__'
        read_only_fields = ['created_at']

class DatasetAccessInviteSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        from .models import DatasetAccessInvite
        model = DatasetAccessInvite
        fields = '__all__'
        read_only_fields = ['created_at', 'invite_token', 'created_by', 'is_used']



