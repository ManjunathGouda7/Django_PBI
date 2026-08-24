# BI/analytics/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid
from datetime import datetime

class Organization(models.Model):
    """Multi-tenant organization"""
    name = models.CharField(max_length=255)
    domain = models.CharField(max_length=255, unique=True)
    logo = models.CharField(max_length=500, null=True, blank=True)
    plan = models.CharField(max_length=50, choices=[
        ('free', 'Free'),
        ('basic', 'Basic'),
        ('pro', 'Professional'),
        ('enterprise', 'Enterprise')
    ], default='free')
    settings = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name

class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('admin', 'Administrator'),
        ('analyst', 'Data Analyst'),
        ('viewer', 'Report Viewer'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    login_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='admin')
    totp_secret = models.CharField(max_length=64, blank=True, null=True)
    is_totp_enabled = models.BooleanField(default=False)
    failed_login_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    def is_locked(self):
        if self.locked_until and self.locked_until > timezone.now():
            return True
        return False

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

class DatasetTag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=20, default='#00A4EF')

    def __str__(self):
        return self.name

class DatasetColumn(models.Model):
    dataset = models.ForeignKey('Dataset', on_delete=models.CASCADE, related_name='columns', null=True, blank=True)
    name = models.CharField(max_length=255)
    data_type = models.CharField(max_length=50, default='string')
    distinct_count = models.IntegerField(default=0)
    null_count = models.IntegerField(default=0)
    min_value = models.CharField(max_length=255, blank=True, null=True)
    max_value = models.CharField(max_length=255, blank=True, null=True)
    sample_values = models.JSONField(default=list, blank=True)

class DatasetSharePermission(models.Model):
    PERMISSION_LEVELS = (
        ('view', 'View Only'),
        ('edit', 'Can Edit'),
        ('admin', 'Full Control'),
    )
    dataset = models.ForeignKey('Dataset', on_delete=models.CASCADE, related_name='share_permissions', null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dataset_shares', null=True, blank=True)
    email = models.EmailField(blank=True, null=True)
    permission_level = models.CharField(max_length=20, choices=PERMISSION_LEVELS, default='view')
    can_export = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        target = self.user.username if self.user else self.email
        return f"{self.dataset.name if self.dataset else 'All'} - {target} ({self.permission_level})"

class DashboardShare(models.Model):
    PERMISSION_LEVELS = (
        ('view', 'View Only'),
        ('edit', 'Can Edit'),
        ('admin', 'Full Control'),
    )
    dashboard = models.ForeignKey('Dashboard', on_delete=models.CASCADE, related_name='shares', null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dashboard_shares', null=True, blank=True)
    email = models.EmailField(blank=True, null=True)
    permission_level = models.CharField(max_length=20, choices=PERMISSION_LEVELS, default='view')
    can_export = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        target = self.user.username if self.user else self.email
        return f"{self.dashboard.title if self.dashboard else 'All'} - {target} ({self.permission_level})"

class ScheduledRefresh(models.Model):
    FREQUENCY_CHOICES = (
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
    )
    dataset = models.ForeignKey('Dataset', on_delete=models.CASCADE, related_name='schedules', null=True, blank=True)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='daily')
    is_active = models.BooleanField(default=True)
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.dataset.name if self.dataset else 'Unknown'} ({self.frequency})"


class Dataset(models.Model):
    FILE_TYPES = (
        ('csv', 'CSV File'),
        ('excel', 'Excel Spreadsheet'),
        ('sample', 'Built-in Sample Data'),
        ('mongodb', 'MongoDB Database Server'),
        ('postgres', 'PostgreSQL'),
        ('mysql', 'MySQL'),
        ('sqlserver', 'SQL Server'),
        ('snowflake', 'Snowflake Warehouse'),
        ('rest_api', 'REST API Endpoint'),
        ('json', 'JSON File'),
    )
    
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('processing', 'Processing'),
        ('ready', 'Ready'),
        ('error', 'Error'),
        ('archived', 'Archived'),
    )

    # Basic Info
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to='datasets/%Y/%m/%d/', blank=True, null=True)
    file_type = models.CharField(max_length=20, choices=FILE_TYPES, default='csv')
    
    # MongoDB Connection
    connection_url = models.CharField(max_length=500, blank=True, null=True)
    db_name = models.CharField(max_length=100, blank=True, null=True)
    collection_name = models.CharField(max_length=100, blank=True, null=True)
    
    # SQL Connection
    host = models.CharField(max_length=255, blank=True, null=True)
    port = models.IntegerField(blank=True, null=True)
    database_name = models.CharField(max_length=100, blank=True, null=True)
    username = models.CharField(max_length=100, blank=True, null=True)
    password = models.CharField(max_length=255, blank=True, null=True)
    
    # Metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    row_count = models.IntegerField(default=0)
    size_mb = models.FloatField(default=0)
    column_schema = models.JSONField(default=dict)
    is_sample = models.BooleanField(default=False)
    
    # Data Quality
    data_quality_score = models.FloatField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    missing_values = models.JSONField(default=dict, blank=True)
    duplicate_count = models.IntegerField(default=0)
    outlier_count = models.IntegerField(default=0)
    
    # Refresh Settings
    refresh_schedule = models.CharField(max_length=50, blank=True, null=True)
    last_refresh = models.DateTimeField(null=True, blank=True)
    next_refresh = models.DateTimeField(null=True, blank=True)
    refresh_status = models.CharField(max_length=20, choices=[
        ('idle', 'Idle'),
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed')
    ], default='idle')
    refresh_error = models.TextField(blank=True, null=True)
    
    # Ownership
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='datasets')
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True)
    is_public = models.BooleanField(default=False)
    tags = models.JSONField(default=list, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    
    # Versioning
    version = models.IntegerField(default=1)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['created_by', 'is_public']),
            models.Index(fields=['file_type', 'status']),
            models.Index(fields=['refresh_status', 'next_refresh']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.row_count} rows)"
    
    @property
    def owner(self):
        return self.created_by

    def save(self, *args, **kwargs):
        if self.file:
            try:
                self.size_mb = self.file.size / (1024 * 1024)
            except:
                pass
        super().save(*args, **kwargs)

class Dashboard(models.Model):
    THEME_CHOICES = (
        ('dark_modern', 'Dark Modern'),
        ('powerbi_yellow', 'Power BI Classic'),
        ('cyberpunk', 'Cyberpunk Neon'),
        ('emerald', 'Teal & Emerald'),
        ('clean_light', 'Clean Slate Light'),
        ('monochrome', 'Monochrome'),
    )
    
    LAYOUT_CHOICES = (
        ('grid', 'Grid Layout'),
        ('freeform', 'Freeform'),
        ('story', 'Story Mode'),
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='dashboards', db_index=True)
    theme = models.CharField(max_length=50, choices=THEME_CHOICES, default='dark_modern')
    layout_type = models.CharField(max_length=20, choices=LAYOUT_CHOICES, default='grid')
    layout_config = models.JSONField(default=dict, blank=True)
    
    # Dashboard Settings
    auto_refresh_interval = models.IntegerField(default=0)
    filter_global = models.JSONField(default=dict, blank=True)
    parameters = models.JSONField(default=dict, blank=True)
    bookmarks = models.JSONField(default=list, blank=True)
    
    # Sharing
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='dashboards')
    is_public = models.BooleanField(default=False)
    share_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    view_count = models.IntegerField(default=0)
    favorite_count = models.IntegerField(default=0)
    
    # Status
    is_template = models.BooleanField(default=False)
    template_category = models.CharField(max_length=100, blank=True, null=True)
    tags = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=[
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived')
    ], default='draft')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    last_viewed_at = models.DateTimeField(null=True, blank=True)
    
    # Versioning
    version = models.IntegerField(default=1)
    version_history = models.JSONField(default=list, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_by', 'status']),
            models.Index(fields=['is_public', 'view_count']),
        ]
    
    def __str__(self):
        return f"{self.title} (v{self.version})"
    
    @property
    def owner(self):
        return self.created_by

    def save(self, *args, **kwargs):
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

class Widget(models.Model):
    VISUAL_TYPES = (
        ('bar', 'Bar Chart'),
        ('column', 'Column Chart'),
        ('line', 'Line Chart'),
        ('pie', 'Pie Chart'),
        ('donut', 'Donut Chart'),
        ('area', 'Area Chart'),
        ('scatter', 'Scatter Plot'),
        ('kpi', 'KPI Card'),
        ('table', 'Aggregated Matrix Table'),
        ('gauge', 'Gauge Target Chart'),
        ('slicer', 'Category Slicer'),
        ('treemap', 'Treemap'),
        ('heatmap', 'Heatmap'),
        ('funnel', 'Funnel Chart'),
        ('waterfall', 'Waterfall Chart'),
        ('radar', 'Radar Chart'),
        ('boxplot', 'Box Plot'),
        ('histogram', 'Histogram'),
    )
    
    AGGREGATIONS = (
        ('SUM', 'Sum'),
        ('AVG', 'Average'),
        ('COUNT', 'Count'),
        ('COUNT_DISTINCT', 'Count Distinct'),
        ('MIN', 'Minimum'),
        ('MAX', 'Maximum'),
        ('MEDIAN', 'Median'),
        ('STD', 'Standard Deviation'),
    )

    dashboard = models.ForeignKey(Dashboard, on_delete=models.CASCADE, related_name='widgets', db_index=True)
    title = models.CharField(max_length=255, default='New Visual')
    visual_type = models.CharField(max_length=50, choices=VISUAL_TYPES, default='scatter')
    
    # Data Configuration
    x_axis = models.CharField(max_length=255, blank=True, null=True)
    y_axis = models.CharField(max_length=255, blank=True, null=True)
    y_axis_secondary = models.CharField(max_length=255, blank=True, null=True)
    aggregation = models.CharField(max_length=20, choices=AGGREGATIONS, default='SUM')
    group_by = models.CharField(max_length=255, blank=True, null=True)
    sort_by = models.CharField(max_length=255, blank=True, null=True)
    sort_order = models.CharField(max_length=4, choices=[('ASC', 'Ascending'), ('DESC', 'Descending')], default='DESC')
    limit = models.IntegerField(default=0)
    
    # Filtering
    filter_config = models.JSONField(default=dict, blank=True)
    parameter_mapping = models.JSONField(default=dict, blank=True)
    
    # Styling
    format_config = models.JSONField(default=dict, blank=True)
    color_scheme = models.CharField(max_length=50, blank=True, null=True)
    show_legend = models.BooleanField(default=True)
    show_labels = models.BooleanField(default=True)
    show_tooltips = models.BooleanField(default=True)
    
    # Position
    position_x = models.IntegerField(default=0)
    position_y = models.IntegerField(default=0)
    width = models.IntegerField(default=6)
    height = models.IntegerField(default=4)
    
    # Advanced
    custom_css = models.TextField(blank=True, null=True)
    custom_js = models.TextField(blank=True, null=True)
    drilldown_config = models.JSONField(default=dict, blank=True)
    actions = models.JSONField(default=list, blank=True)
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Status
    is_visible = models.BooleanField(default=True)
    is_locked = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['position_y', 'position_x']
        indexes = [
            models.Index(fields=['dashboard', 'visual_type']),
            models.Index(fields=['created_by']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.visual_type})"

class CalculatedMeasure(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='measures')
    name = models.CharField(max_length=100)
    formula = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} = {self.formula}"

class ActivityLog(models.Model):
    """Audit trail for all actions"""
    ACTION_TYPES = (
        ('CREATE', 'Create'),
        ('READ', 'Read'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('EXPORT', 'Export'),
        ('SHARE', 'Share'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('REFRESH', 'Refresh Data'),
        ('VIEW', 'View'),
    )
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True)
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    resource_type = models.CharField(max_length=50)
    resource_id = models.IntegerField()
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['resource_type', 'resource_id']),
        ]
    
    def __str__(self):
        return f"{self.user} - {self.action_type} - {self.resource_type}"

class RowLevelSecurityRule(models.Model):
    """Enforces fine-grained Row-Level Security (RLS) data access rules per dataset"""
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='rls_rules')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    role = models.CharField(max_length=50, blank=True, null=True)
    column_name = models.CharField(max_length=100)
    operator = models.CharField(max_length=10, choices=[
        ('eq', 'Equals'),
        ('ne', 'Not Equals'),
        ('gt', 'Greater Than'),
        ('lt', 'Less Than'),
        ('in', 'In List'),
    ], default='eq')
    filter_value = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"RLS Rule for {self.dataset.name}: {self.column_name} {self.operator} {self.filter_value}"

class KPIAlertRule(models.Model):
    """Automated notification alert thresholds for KPI Cards and Widget Metrics"""
    widget = models.ForeignKey(Widget, on_delete=models.CASCADE, related_name='alerts')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    metric_column = models.CharField(max_length=100)
    condition = models.CharField(max_length=10, choices=[
        ('gt', 'Greater Than'),
        ('lt', 'Less Than'),
        ('eq', 'Equals'),
        ('gte', 'Greater Than or Equal'),
        ('lte', 'Less Than or Equal'),
    ], default='gt')
    threshold_value = models.FloatField()
    channel = models.CharField(max_length=20, choices=[
        ('email', 'Email Notification'),
        ('webhook', 'Generic Webhook'),
        ('slack', 'Slack Webhook'),
        ('teams', 'Microsoft Teams Webhook'),
    ], default='webhook')
    webhook_url = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    last_triggered = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Alert: {self.widget.title} ({self.metric_column} {self.condition} {self.threshold_value})"

class WidgetComment(models.Model):
    """Sticky notes and collaborative comment pins on dashboard widgets"""
    widget = models.ForeignKey(Widget, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment_text = models.TextField()
    pin_x = models.FloatField(default=0)
    pin_y = models.FloatField(default=0)
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.user.username} on {self.widget.title}"

class DashboardBookmark(models.Model):
    """Saved filter, slicer, and zoom state bookmarks for users"""
    dashboard = models.ForeignKey(Dashboard, on_delete=models.CASCADE, related_name='saved_bookmarks')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dashboard_bookmarks')
    name = models.CharField(max_length=150)
    state = models.JSONField(default=dict, help_text="Stores active slicer values, zoom, and visual states")
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('dashboard', 'user', 'name')

    def __str__(self):
        return f"{self.name} ({self.dashboard.title})"

class DashboardRevision(models.Model):
    """Historical layout snapshots for versioning and 1-click rollback"""
    dashboard = models.ForeignKey(Dashboard, on_delete=models.CASCADE, related_name='revisions')
    version = models.IntegerField(default=1)
    snapshot = models.JSONField(help_text="Full serialized widget layout and configuration snapshot")
    change_summary = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version']

    def __str__(self):
        return f"v{self.version} - {self.dashboard.title} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

class DatasetVersion(models.Model):
    """Historical schema and lineage tracking for datasets"""
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='versions')
    version_number = models.IntegerField(default=1)
    row_count = models.IntegerField(default=0)
    column_count = models.IntegerField(default=0)
    schema_signature = models.JSONField(default=dict, help_text="Column names, types, null stats")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version_number']

    def __str__(self):
        return f"{self.dataset.name} v{self.version_number} ({self.row_count} rows)"

class DataQualityReport(models.Model):
    """Automated data profiling & quality health scoring (0-100)"""
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='quality_reports')
    health_score = models.FloatField(default=100.0, help_text="Overall health index from 0 to 100")
    total_rows = models.IntegerField(default=0)
    total_columns = models.IntegerField(default=0)
    null_percentage = models.FloatField(default=0.0)
    duplicate_rows_count = models.IntegerField(default=0)
    outlier_count = models.IntegerField(default=0)
    column_metrics = models.JSONField(default=dict, help_text="Per-column completeness, drift, and uniqueness")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Health Score: {self.health_score:.1f}% for {self.dataset.name}"

class DatasetAccessInvite(models.Model):
    """Expiring, token-based invitation links for external dataset sharing"""
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='access_invites')
    invite_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    recipient_email = models.EmailField()
    permission_level = models.CharField(max_length=20, choices=[('view', 'View Only'), ('edit', 'Can Edit')], default='view')
    can_export = models.BooleanField(default=True)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Invite for {self.recipient_email} to {self.dataset.name}"