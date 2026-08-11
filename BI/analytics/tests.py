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

class DataChatEngineTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='chatuser', password='password123')
        self.dataset = Dataset.objects.create(
            name='Chat Test Dataset',
            file_type='sample',
            is_sample=True,
            row_count=100
        )

    def test_chat_engine_summary_query(self):
        from .chat_engine import DataChatEngine
        res = DataChatEngine.process_query(self.dataset, "Summarize this dataset")
        self.assertIn("Dataset Summary", res['response'])
        self.assertTrue(len(res['kpis']) > 0)
        self.assertIsNotNone(res['table'])

    def test_chat_engine_health_query(self):
        from .chat_engine import DataChatEngine
        res = DataChatEngine.process_query(self.dataset, "Show missing values and data health")
        self.assertIn("Data Health & Quality Report", res['response'])

    def test_chat_api_endpoint(self):
        url = reverse('analytics:api_dataset_chat', kwargs={'dataset_id': self.dataset.id})
        response = self.client.post(
            url,
            data='{"message": "Show top 5 records"}',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('data', data)

class EnterpriseAdvancedTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='advuser', password='password123')
        self.dataset = Dataset.objects.create(
            name='Advanced Test Dataset',
            file_type='sample',
            is_sample=True,
            row_count=100
        )

    def test_auto_dashboard_builder(self):
        url = reverse('analytics:api_auto_dashboard', kwargs={'dataset_id': self.dataset.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('dashboard_id', data)
        db = Dashboard.objects.get(pk=data['dashboard_id'])
        self.assertTrue(db.widgets.count() >= 3)

    def test_anomaly_detection(self):
        url = reverse('analytics:api_dataset_anomalies', kwargs={'dataset_id': self.dataset.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')

    def test_excel_export(self):
        url = reverse('analytics:export_excel', kwargs={'dataset_id': self.dataset.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    def test_template_export_and_import(self):
        from .analytics_advanced import AIAutoBuilder, TemplateManager
        db = AIAutoBuilder.build_auto_dashboard(self.dataset, user=self.user)
        template_json = TemplateManager.export_template(db)
        self.assertIn('widgets', template_json)
        imported_db = TemplateManager.import_template(self.dataset, template_json, title="Imported Test", user=self.user)
        self.assertEqual(imported_db.title, "Imported Test")
        self.assertEqual(imported_db.widgets.count(), db.widgets.count())

    def test_time_series_forecasting(self):
        url = reverse('analytics:api_dataset_forecast', kwargs={'dataset_id': self.dataset.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('forecast', data['data'])

    def test_nl_formula_generator(self):
        url = reverse('analytics:api_nl_formula', kwargs={'dataset_id': self.dataset.id})
        response = self.client.post(
            url,
            data='{"prompt": "Calculate percentage ratio of PFO to Power"}',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('formula', data['data'])

    def test_etl_sync_pipeline(self):
        url = reverse('analytics:api_schedule_etl', kwargs={'dataset_id': self.dataset.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['data']['status'], 'SUCCESS')

    def test_executive_pdf_export_view(self):
        db = Dashboard.objects.create(title="PDF Test DB", dataset=self.dataset, created_by=self.user)
        url = reverse('analytics:export_executive_pdf', kwargs={'dashboard_id': db.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Executive Telemetry Report", response.content)

    def test_load_dataframe_chunks(self):
        from .services import DatasetEngine
        chunks = list(DatasetEngine.load_dataframe_chunks(self.dataset, chunksize=2))
        self.assertTrue(len(chunks) >= 1)

    def test_formula_security_sanitizer(self):
        from .analytics_advanced import DataWrangler
        self.assertTrue(DataWrangler.validate_formula_security("Power * 1.15", ["Power", "PFO_mW"]))
        with self.assertRaises(ValueError):
            DataWrangler.validate_formula_security("__import__('os').system('ls')", ["Power"])





