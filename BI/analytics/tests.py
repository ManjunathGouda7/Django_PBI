import os
import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Dataset, Dashboard, Widget, UserProfile, DatasetColumn
from .services import DatasetEngine
import pandas as pd

class AnalyticsModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user, defaults={'role': 'admin'})
        self.profile.role = 'admin'
        self.profile.save()
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
            'user_id': 'john',
            'password': 'secretpassword'
        })
        self.assertEqual(response.status_code, 302)

    def test_login_with_admin_assigned_user_id(self):
        self.user.profile.login_id = 'secret-john'
        self.user.profile.save()
        response = self.client.post(reverse('analytics:login'), {
            'user_id': 'secret-john',
            'password': 'secretpassword'
        })
        self.assertEqual(response.status_code, 302)

    def test_invalid_credentials_fails(self):
        response = self.client.post(reverse('analytics:login'), {
            'user_id': 'unknown_user',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid User ID or Password')

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

    def test_health_check_endpoint(self):
        url = reverse('analytics:health_check')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'healthy')
        self.assertTrue(data['db_ok'])
        self.assertTrue(data['cache_ok'])

class EnterpriseArchitectureAndReadinessTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='archuser', password='password123')
        self.dataset = Dataset.objects.create(name='Arch DS', file_type='sample', is_sample=True, created_by=self.user)
        self.dashboard = Dashboard.objects.create(title='Arch DB', dataset=self.dataset, created_by=self.user)
        self.widget = Widget.objects.create(dashboard=self.dashboard, title='Arch Widget', x_axis='Station', y_axis='Power', visual_type='bar')

        # Inject test dataframe
        from .services import _df_cache
        self.df_test = pd.DataFrame({
            'Station': ['St_1', 'St_2', 'St_1', 'St_2'],
            'Timestamp': ['2026-08-01', '2026-08-02', '2026-08-03', '2026-08-04'],
            'Power': [120.5, 250.0, 180.2, 310.4]
        })
        _df_cache[self.dataset.id] = self.df_test

    def test_two_factor_auth_engine(self):
        from .services import TwoFactorAuthEngine
        secret = TwoFactorAuthEngine.generate_base32_secret()
        self.assertEqual(len(secret), 16)
        code = TwoFactorAuthEngine.generate_totp_code(secret)
        self.assertEqual(len(code), 6)
        self.assertTrue(TwoFactorAuthEngine.verify_totp_code(secret, code))

    def test_security_lockout_service(self):
        from .services import SecurityLockoutService
        from .models import UserProfile
        profile, _ = UserProfile.objects.get_or_create(user=self.user)
        for _ in range(5):
            SecurityLockoutService.record_failed_attempt(profile)
        self.assertTrue(profile.is_locked())
        SecurityLockoutService.reset_attempts(profile)
        self.assertFalse(profile.is_locked())

    def test_schema_drift_detector(self):
        from .services import SchemaDriftDetector
        new_df = pd.DataFrame({'Station': ['A'], 'NewCol': [123]})
        drift = SchemaDriftDetector.detect_drift(self.dataset, new_df)
        self.assertTrue(drift['has_drift'])
        self.assertIn('NewCol', drift['added_columns'])

    def test_data_quality_engine(self):
        from .services import DataQualityEngine
        report = DataQualityEngine.generate_quality_report(self.dataset, self.df_test)
        self.assertTrue(report.health_score > 0)
        self.assertEqual(report.total_rows, 4)

    def test_lttb_downsampler(self):
        from .services import LTTBDownsampler
        points = [(i, float(i**2)) for i in range(100)]
        downsampled = LTTBDownsampler.downsample(points, threshold=20)
        self.assertEqual(len(downsampled), 20)

    def test_data_import_pipeline(self):
        from .services import DataImportPipeline
        res = DataImportPipeline.ingest_dataframe(self.dataset, self.df_test, user=self.user)
        self.assertEqual(res['status'], 'success')
        self.assertEqual(res['rows'], 4)

    def test_dashboard_bookmarks_and_revisions_api(self):
        self.client.force_login(self.user)
        url_bm = reverse('analytics:api_dashboard_bookmarks', kwargs={'dashboard_id': self.dashboard.id})
        res_bm = self.client.post(url_bm, data='{"name": "Q3 View", "state": {"slicer": "Station_1"}}', content_type='application/json')
        self.assertEqual(res_bm.status_code, 200)

        url_rev = reverse('analytics:api_dashboard_revisions', kwargs={'dashboard_id': self.dashboard.id})
        res_rev = self.client.post(url_rev, data='{"action": "snapshot", "change_summary": "Initial baseline"}', content_type='application/json')
        self.assertEqual(res_rev.status_code, 200)

    def test_csv_cache_mtime_invalidation(self):
        import tempfile
        import time
        from .services import DatasetEngine

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("Board,Power\nGTPT101,10.0\n")
            temp_path = f.name

        try:
            from django.core.files import File
            with open(temp_path, 'rb') as f_obj:
                ds = Dataset.objects.create(
                    name="Temp CSV DS",
                    file_type="csv",
                    file=File(f_obj, name="temp.csv")
                )

            df1 = DatasetEngine.load_dataframe(ds)
            self.assertEqual(len(df1), 1)
            self.assertEqual(float(df1.iloc[0]['Power']), 10.0)

            time.sleep(0.1)

            # Update file on disk
            real_path = ds.file.path
            with open(real_path, 'w') as f:
                f.write("Board,Power\nGTPT101,10.0\nGTPT102,25.5\n")

            df2 = DatasetEngine.load_dataframe(ds)
            self.assertEqual(len(df2), 2)
            self.assertEqual(float(df2.iloc[1]['Power']), 25.5)

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_dashboard_dataset_switch_api(self):
        self.client.force_login(self.user)
        new_ds = Dataset.objects.create(name='New Switch DS', file_type='sample', is_sample=True, created_by=self.user)
        url = reverse('analytics:api_dashboard_detail', kwargs={'dashboard_id': self.dashboard.id})
        res = self.client.put(url, data=json.dumps({'dataset_id': new_ds.id}), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        self.dashboard.refresh_from_db()
        self.assertEqual(self.dashboard.dataset.id, new_ds.id)

    def test_dataset_delete_api(self):
        self.client.force_login(self.user)
        del_ds = Dataset.objects.create(name='Delete Target DS', file_type='sample', is_sample=True, created_by=self.user)
        url = reverse('analytics:api_dataset_detail', kwargs={'dataset_id': del_ds.id})
        res = self.client.delete(url)
        self.assertEqual(res.status_code, 200)
        self.assertFalse(Dataset.objects.filter(id=del_ds.id).exists())

    def test_public_registration_disabled(self):
        url = reverse('analytics:api_auth_register')
        res = self.client.post(url, data=json.dumps({
            'user_id': 'hacker.user',
            'password': 'password123'
        }), content_type='application/json')
        self.assertEqual(res.status_code, 403)
        self.assertIn('Public registration is disabled', res.json()['error'])

    def test_manjunath_sole_admin_rights(self):
        # Manjunath user
        manju_user = User.objects.create_user(username='Manjunath', password='password123')
        manju_profile = UserProfile.objects.get(user=manju_user)
        self.assertTrue(manju_profile.is_admin)
        self.assertEqual(manju_profile.get_role_display(), 'Administrator')

        # Other standard user
        regular_user = User.objects.create_user(username='john.doe', password='password123')
        regular_profile = UserProfile.objects.get(user=regular_user)
        self.assertFalse(regular_profile.is_admin)
        self.assertEqual(regular_profile.get_role_display(), 'User')

    def test_lockout_after_five_failed_attempts(self):
        test_user = User.objects.create_user(username='lockuser', password='correct_pwd')
        UserProfile.objects.get_or_create(user=test_user, defaults={'login_id': 'lockuser'})

        login_url = reverse('analytics:login')
        # 5 failed attempts
        for _ in range(5):
            res = self.client.post(login_url, {'user_id': 'lockuser', 'password': 'wrong_pwd'})
            self.assertEqual(res.status_code, 200)

        profile = UserProfile.objects.get(user=test_user)
        self.assertTrue(profile.is_locked())

        # Attempt with correct password should be blocked due to lock
        res = self.client.post(login_url, {'user_id': 'lockuser', 'password': 'correct_pwd'})
        self.assertIn('Account is temporarily locked', res.content.decode())

    def test_password_with_spaces_preserved(self):
        space_pwd = " leading and trailing "
        space_user = User.objects.create_user(username='spaceuser', password=space_pwd)
        UserProfile.objects.get_or_create(user=space_user, defaults={'login_id': 'spaceuser'})

        login_url = reverse('analytics:login')
        res = self.client.post(login_url, {'user_id': 'spaceuser', 'password': space_pwd})
        self.assertEqual(res.status_code, 302)  # Redirects to index

    def test_must_change_password_flow(self):
        temp_user = User.objects.create_user(username='tempuser', password='temppassword')
        profile, _ = UserProfile.objects.get_or_create(user=temp_user, defaults={'login_id': 'tempuser', 'must_change_password': True})
        profile.must_change_password = True
        profile.save()

        # Login redirects to change-password
        login_url = reverse('analytics:login')
        res = self.client.post(login_url, {'user_id': 'tempuser', 'password': 'temppassword'})
        self.assertEqual(res.status_code, 302)
        self.assertIn('change-password', res.url)

        # Accessing index directly redirects to change-password
        self.client.force_login(temp_user)
        res_idx = self.client.get(reverse('analytics:index'))
        self.assertEqual(res_idx.status_code, 302)
        self.assertIn('change-password', res_idx.url)

        # Change password
        ch_url = reverse('analytics:change_password')
        res_change = self.client.post(ch_url, {
            'new_password': 'NewSecurePassword99!',
            'confirm_password': 'NewSecurePassword99!'
        })
        self.assertEqual(res_change.status_code, 302)

        profile.refresh_from_db()
        self.assertFalse(profile.must_change_password)

    def test_auto_employee_user_id_generation(self):
        from .services import EmployeeIdGeneratorService
        gen_id1 = EmployeeIdGeneratorService.generate_next_id()
        self.assertTrue(gen_id1.startswith('EMP-'))

    def test_password_complexity_rules(self):
        from .services import PasswordPolicyService
        # Simple password fails
        errs = PasswordPolicyService.validate_complexity('simple')
        self.assertTrue(len(errs) > 0)

        # Complex password passes
        errs2 = PasswordPolicyService.validate_complexity('ComplexPass99!')
        self.assertEqual(len(errs2), 0)

    def test_security_dashboard_access_and_unlock(self):
        admin_user = User.objects.create_user(username='Manjunath', password='ComplexPass99!', is_superuser=True)
        admin_profile, _ = UserProfile.objects.get_or_create(user=admin_user, defaults={'login_id': 'Manjunath'})
        admin_profile.login_id = 'Manjunath'
        admin_profile.save()
        self.client.force_login(admin_user)

        target_user = User.objects.create_user(username='targetlock', password='ComplexPass99!')
        target_profile = UserProfile.objects.get(user=target_user)
        target_profile.status = 'locked'
        target_profile.failed_login_attempts = 5
        target_profile.save()

        sec_url = reverse('analytics:security_dashboard')
        res = self.client.get(sec_url)
        self.assertEqual(res.status_code, 200)

        # Admin unlocks target
        res_post = self.client.post(sec_url, {'action': 'unlock', 'user_id': target_profile.id})
        self.assertEqual(res_post.status_code, 200)
        target_profile.refresh_from_db()
        self.assertEqual(target_profile.status, 'active')
        self.assertEqual(target_profile.failed_login_attempts, 0)

    def test_outlier_detection_iqr(self):
        from .services import OutlierDetectionService
        import pandas as pd
        df = pd.DataFrame({'val': [10, 12, 11, 13, 12, 11, 1000]})  # 1000 is outlier
        df_res, summary = OutlierDetectionService.process_telemetry_dataframe(df, numeric_cols=['val'], method='iqr')
        self.assertEqual(summary['outlier_count'], 1)
        self.assertTrue(df_res['_is_outlier'].iloc[-1])

    def test_data_validation_boundary_rules(self):
        from .services import DataValidationService
        import pandas as pd
        df = pd.DataFrame({
            'PFO [mW]': [100.0, 2500.0],  # 2500 violates 1000 max bound
            'Rectified Power [W]': [5.0, 10.0]
        })
        df_clean, report = DataValidationService.validate_and_clean_dataframe(df)
        self.assertEqual(report['boundary_violations_flagged'], 1)

    def test_expression_engine_formula_evaluation(self):
        from .services import ExpressionEngine
        import pandas as pd
        df = pd.DataFrame({'a': [10, 20], 'b': [2, 4]})
        updated_df, msg = ExpressionEngine.evaluate_expression(df, "[a] / [b]", "ratio")
        self.assertIn("ratio", updated_df.columns)
        self.assertEqual(updated_df['ratio'].iloc[0], 5.0)

    def test_sql_connector_service_sqlite(self):
        from .services import SqlConnectorService
        ok, msg = SqlConnectorService.test_connection('sqlite', {'database': ':memory:'})
        self.assertTrue(ok)

    def test_template_exporter(self):
        from .services import TemplateExporter
        ds = Dataset.objects.create(name="Template DS")
        db = Dashboard.objects.create(title="Template Test DB", dataset=ds)
        Widget.objects.create(dashboard=db, title="W1", visual_type="scatter")
        tmpl = TemplateExporter.export_dashboard_template(db)
        self.assertEqual(tmpl['dashboard_title'], "Template Test DB")
        self.assertEqual(tmpl['visuals_count'], 1)

    def test_report_digest_service(self):
        from .services import ReportDigestService
        ds = Dataset.objects.create(name="Digest DS")
        db = Dashboard.objects.create(title="Digest Test DB", dataset=ds)
        res = ReportDigestService.send_dashboard_digest(db, ['test@example.com'])
        self.assertEqual(res['status'], 'success')












