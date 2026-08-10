from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Dataset, Dashboard, Widget, UserProfile
from .services import DatasetEngine
import pandas as pd

class AnalyticsModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.profile = UserProfile.objects.create(user=self.user, role='admin')
        self.dataset = Dataset.objects.create(
            name='Test Telemetry Dataset',
            file_type='sample',
            is_sample=True,
            row_count=100
        )
        self.dashboard = Dashboard.objects.create(
            title='Test Dashboard',
            dataset=self.dataset,
            created_by=self.user
        )

    def test_dataset_creation(self):
        self.assertEqual(self.dataset.name, 'Test Telemetry Dataset')
        self.assertTrue(self.dataset.is_sample)

    def test_dashboard_creation(self):
        self.assertEqual(self.dashboard.title, 'Test Dashboard')
        self.assertEqual(self.dashboard.created_by, self.user)

    def test_schema_inference(self):
        df = pd.DataFrame({
            'Board': ['GTPT106', 'GTPT118'],
            'Power': [10.5, 12.0],
            'Timestamp': ['2026-08-10 10:00:00', '2026-08-10 10:01:00']
        })
        schema = DatasetEngine.infer_column_schema(df)
        self.assertEqual(len(schema), 3)
        self.assertEqual(schema[0]['name'], 'Board')
        self.assertEqual(schema[1]['type'], 'numeric')

class AnalyticsAuthViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='john', password='secretpassword')

    def test_login_required_redirect(self):
        response = self.client.get(reverse('analytics:index'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_successful_login(self):
        response = self.client.post(reverse('analytics:login'), {
            'action': 'login',
            'username': 'john',
            'password': 'secretpassword'
        })
        self.assertEqual(response.status_code, 302)

    def test_registration_with_matching_passwords(self):
        response = self.client.post(reverse('analytics:login'), {
            'action': 'register',
            'username': 'newuser',
            'password': 'newpassword123',
            'confirm_password': 'newpassword123',
            'email': 'newuser@example.com'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='newuser').exists())
