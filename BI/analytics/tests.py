from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Dataset, Dashboard, Widget, UserProfile, DatasetColumn
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

class NewFeaturesModelAndSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='modeluser', password='password123')
        self.dataset = Dataset.objects.create(
            name='Schema Test Dataset',
            file_type='sample',
            is_sample=True,
            created_by=self.user
        )
        self.dashboard = Dashboard.objects.create(
            title='Schema Test Dashboard',
            dataset=self.dataset,
            created_by=self.user
        )

    def test_dataset_column_relationship(self):
        col = DatasetColumn.objects.create(
            dataset=self.dataset,
            name='TestCol',
            data_type='numeric',
            distinct_count=5
        )
        self.assertEqual(self.dataset.columns.count(), 1)
        self.assertEqual(self.dataset.columns.first().name, 'TestCol')

    def test_owner_property_alias(self):
        self.assertEqual(self.dataset.owner, self.user)
        self.assertEqual(self.dashboard.owner, self.user)

    def test_dashboard_share_model_and_serializer(self):
        from .models import DashboardShare
        from .serializers import DashboardShareSerializer
        share = DashboardShare.objects.create(
            dashboard=self.dashboard,
            user=self.user,
            permission_level='edit',
            can_export=True
        )
        serializer = DashboardShareSerializer(share)
        self.assertEqual(serializer.data['permission_level'], 'edit')
        self.assertEqual(serializer.data['shared_username'], 'modeluser')

    def test_scheduled_refresh_model_and_serializer(self):
        from .models import ScheduledRefresh
        from .serializers import ScheduledRefreshSerializer
        schedule = ScheduledRefresh.objects.create(
            dataset=self.dataset,
            frequency='daily',
            created_by=self.user
        )
        serializer = ScheduledRefreshSerializer(schedule)
        self.assertEqual(serializer.data['frequency'], 'daily')
        self.assertEqual(serializer.data['created_by_username'], 'modeluser')

class UploadValidationAndPermissionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='validatoruser', password='password123')

    def test_validate_file_extension(self):
        from .services import DatasetValidator
        self.assertTrue(DatasetValidator.validate_file_extension('data.csv'))
        self.assertTrue(DatasetValidator.validate_file_extension('report.xlsx'))
        self.assertTrue(DatasetValidator.validate_file_extension('telemetry.json'))
        with self.assertRaises(ValueError):
            DatasetValidator.validate_file_extension('malicious.exe')

    def test_sanitize_columns(self):
        from .services import DatasetValidator
        df = pd.DataFrame({'<script>alert(1)</script>Col': [1, 2], 'Normal': [3, 4]})
        clean_df = DatasetValidator.sanitize_columns(df)
        self.assertIn('alert(1)Col', clean_df.columns)
        self.assertNotIn('<script>alert(1)</script>Col', clean_df.columns)

    def test_export_permission(self):
        from .models import Dataset, DatasetSharePermission
        from .permissions import HasExportPermission
        dataset = Dataset.objects.create(name='Private DS', created_by=self.user)
        perm = HasExportPermission()

        class DummyRequest:
            user = self.user

        req = DummyRequest()
        self.assertTrue(perm.has_object_permission(req, None, dataset))

class AsyncTasksAndAuditLogTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='taskuser', password='password123')
        self.dataset = Dataset.objects.create(
            name='Task DS',
            file_type='sample',
            is_sample=True,
            created_by=self.user
        )

    def test_async_process_dataset_upload_task(self):
        from .tasks import async_process_dataset_upload_task
        res = async_process_dataset_upload_task(self.dataset.id)
        self.assertEqual(res['status'], 'success')
        self.dataset.refresh_from_db()
        self.assertEqual(self.dataset.status, 'ready')

    def test_async_run_scheduled_refresh_task(self):
        from .models import ScheduledRefresh
        from .tasks import async_run_scheduled_refresh_task
        schedule = ScheduledRefresh.objects.create(dataset=self.dataset, frequency='daily', created_by=self.user)
        res = async_run_scheduled_refresh_task(schedule.id)
        self.assertEqual(res['status'], 'success')

    def test_audit_logger(self):
        from .services import AuditLogger
        from .models import ActivityLog
        log = AuditLogger.log_action(self.user, 'CREATE', 'Dataset', self.dataset.id, {'name': 'Task DS'})
        self.assertIsNotNone(log)
        self.assertEqual(ActivityLog.objects.filter(resource_type='Dataset').count(), 1)

class DashboardSharingAndScheduledRefreshAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='apiuser', password='password123')
        self.dataset = Dataset.objects.create(name='API DS', file_type='sample', is_sample=True, created_by=self.user)
        self.dashboard = Dashboard.objects.create(title='API DB', dataset=self.dataset, created_by=self.user)

    def test_dashboard_share_api(self):
        url = reverse('analytics:api_dashboard_share', kwargs={'dashboard_id': self.dashboard.id})
        response = self.client.post(
            url,
            data=f'{{"user_id": {self.user.id}, "permission_level": "edit", "can_export": true}}',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')

    def test_scheduled_refresh_api(self):
        url = reverse('analytics:api_scheduled_refresh', kwargs={'dataset_id': self.dataset.id})
        response = self.client.post(
            url,
            data='{"frequency": "hourly"}',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')

    def test_audit_logs_api(self):
        from .services import AuditLogger
        AuditLogger.log_action(self.user, 'VIEW', 'Dashboard', self.dashboard.id)
        url = reverse('analytics:api_audit_logs')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertTrue(len(data['audit_logs']) > 0)

class EnterpriseExpansionFeatureTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='entuser', password='password123')
        self.dataset = Dataset.objects.create(name='Ent DS', file_type='sample', is_sample=True, created_by=self.user)
        self.dashboard = Dashboard.objects.create(title='Ent DB', dataset=self.dataset, created_by=self.user)
        self.widget = Widget.objects.create(dashboard=self.dashboard, title='Ent Widget', x_axis='Station', y_axis='Power', visual_type='bar')

        # Inject test dataframe with Power column into cache
        from .services import _df_cache
        df_test = pd.DataFrame({
            'Station': ['St_1', 'St_2', 'St_1', 'St_2'],
            'Timestamp': ['2026-08-01', '2026-08-02', '2026-08-03', '2026-08-04'],
            'Power': [120.5, 250.0, 180.2, 310.4]
        })
        _df_cache[self.dataset.id] = df_test

    def test_smart_narrative_engine(self):
        from .services import DatasetEngine, SmartNarrativeEngine
        df = DatasetEngine.load_dataframe(self.dataset)
        bullets = SmartNarrativeEngine.generate_widget_narrative(df, self.widget)
        self.assertTrue(len(bullets) >= 1)
        self.assertIn("Power", bullets[0])

    def test_sql_and_rest_connectors(self):
        from .services import SQLDatabaseConnector
        df_sql = SQLDatabaseConnector.execute_live_query('sqlite', 'local', 0, '', '', '', 'SELECT 1 as val;')
        self.assertEqual(len(df_sql), 1)
        self.assertEqual(df_sql['val'].iloc[0], 1)

    def test_what_if_and_rfm_clustering(self):
        from .services import DatasetEngine, WhatIfScenarioEngine, CustomerSegmentationEngine
        df = DatasetEngine.load_dataframe(self.dataset)
        df_sim, metrics = WhatIfScenarioEngine.simulate_scenario(df, [{'column': 'Power', 'multiplier': 1.10}])
        self.assertIn('Power', metrics)
        self.assertTrue(metrics['Power']['simulated_total'] > metrics['Power']['baseline_total'])

        segments = CustomerSegmentationEngine.rfm_clustering(df, 'Station', 'Timestamp', 'Power', n_clusters=2)
        self.assertTrue(len(segments) > 0)
        self.assertIn('cluster', segments[0])

    def test_rls_and_dax_parser(self):
        from .models import RowLevelSecurityRule
        from .services import DatasetEngine, RowLevelSecurityEngine, DAXFormulaParser
        rule = RowLevelSecurityRule.objects.create(dataset=self.dataset, user=self.user, column_name='Station', operator='eq', filter_value='St_1')
        df = DatasetEngine.load_dataframe(self.dataset)
        df_rls = RowLevelSecurityEngine.apply_rls_filters(df, self.dataset, self.user)
        self.assertTrue(len(df_rls) <= len(df))

        val_sum = DAXFormulaParser.evaluate_formula(df, "SUM(Power)")
        self.assertTrue(isinstance(val_sum, float))

    def test_kpi_alerts_and_comments_api(self):
        url_alert = reverse('analytics:api_kpi_alerts', kwargs={'widget_id': self.widget.id})
        res_alert = self.client.post(url_alert, data='{"metric_column": "Power", "condition": "gt", "threshold_value": 100}', content_type='application/json')
        self.assertEqual(res_alert.status_code, 200)

        self.client.force_login(self.user)
        url_comm = reverse('analytics:api_widget_comments', kwargs={'widget_id': self.widget.id})
        res_comm = self.client.post(url_comm, data='{"comment_text": "Check outlier peak", "pin_x": 50, "pin_y": 50}', content_type='application/json')
        self.assertEqual(res_comm.status_code, 200)
        self.assertEqual(res_comm.json()['status'], 'success')








