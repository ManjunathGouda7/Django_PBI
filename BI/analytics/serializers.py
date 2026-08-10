from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Dataset, Dashboard, Widget, CalculatedMeasure, DatasetColumn, DatasetTag, DatasetSharePermission

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joined']
        read_only_fields = ['id', 'date_joined']

class DatasetColumnSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatasetColumn
        fields = '__all__'

class DatasetTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatasetTag
        fields = '__all__'

class DatasetSerializer(serializers.ModelSerializer):
    columns = DatasetColumnSerializer(many=True, read_only=True)
    tags = DatasetTagSerializer(many=True, read_only=True)
    owner_username = serializers.CharField(source='owner.username', read_only=True)

    class Meta:
        model = Dataset
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'owner']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['owner'] = request.user
        return super().create(validated_data)

class WidgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Widget
        fields = '__all__'
        read_only_fields = ['created_at']

class DashboardSerializer(serializers.ModelSerializer):
    widgets = WidgetSerializer(many=True, read_only=True)
    dataset_name = serializers.CharField(source='dataset.name', read_only=True)
    owner_username = serializers.CharField(source='owner.username', read_only=True)

    class Meta:
        model = Dashboard
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'owner']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['owner'] = request.user
        return super().create(validated_data)

class CalculatedMeasureSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalculatedMeasure
        fields = '__all__'
