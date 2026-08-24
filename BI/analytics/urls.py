from django.urls import path
from . import views
from . import api_views

app_name = 'analytics'

urlpatterns = [
    # Main Application & Auth Portal
    path('', views.index_view, name='index'),
    path('health/', views.health_check_view, name='health_check'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('favicon.ico', views.favicon_view, name='favicon'),
    path('export/<int:dashboard_id>/', views.export_dashboard_view, name='export_dashboard'),
    path('export-csv/<int:dataset_id>/', views.export_csv_view, name='export_csv'),
    path('export-excel/<int:dataset_id>/', views.export_excel_view, name='export_excel'),
    path('export-pdf/<int:dashboard_id>/', views.export_executive_pdf_view, name='export_executive_pdf'),

    # Authentication APIs
    path('api/auth/register/', api_views.auth_register_api, name='api_auth_register'),
    path('api/auth/login/', api_views.auth_login_api, name='api_auth_login'),
    path('api/auth/logout/', api_views.auth_logout_api, name='api_auth_logout'),
    path('api/auth/me/', api_views.auth_me_api, name='api_auth_me'),

    # REST APIs
    path('api/datasets/', api_views.datasets_list_api, name='api_datasets_list'),
    path('api/datasets/append-main/', api_views.dataset_append_data_api, name='api_dataset_append_main'),
    path('api/datasets/<int:dataset_id>/append-data/', api_views.dataset_append_data_api, name='api_dataset_append_data'),
    path('api/datasets/mongodb/', api_views.mongodb_dataset_api, name='api_mongodb_dataset'),
    path('api/mongodb/collections/', api_views.mongodb_collections_api, name='api_mongodb_collections'),
    path('api/mongodb/push_json/', api_views.mongodb_push_json_api, name='api_mongodb_push_json'),
    path('api/datasets/<int:dataset_id>/', api_views.dataset_detail_api, name='api_dataset_detail'),
    path('api/datasets/<int:dataset_id>/chat/', api_views.dataset_chat_api, name='api_dataset_chat'),
    path('api/datasets/<int:dataset_id>/rows/', api_views.dataset_rows_api, name='api_dataset_rows'),
    path('api/datasets/<int:dataset_id>/filter-values/', api_views.dataset_filter_values_api, name='api_dataset_filter_values'),
    path('api/datasets/<int:dataset_id>/auto-dashboard/', api_views.auto_dashboard_api, name='api_auto_dashboard'),
    path('api/datasets/<int:dataset_id>/anomalies/', api_views.dataset_anomalies_api, name='api_dataset_anomalies'),
    path('api/datasets/<int:dataset_id>/clean/', api_views.clean_dataset_api, name='api_clean_dataset'),
    path('api/datasets/<int:dataset_id>/measures/', api_views.add_measure_api, name='api_add_measure'),
    path('api/datasets/<int:dataset_id>/forecast/', api_views.dataset_forecast_api, name='api_dataset_forecast'),
    path('api/datasets/<int:dataset_id>/nl-formula/', api_views.nl_formula_api, name='api_nl_formula'),
    path('api/datasets/<int:dataset_id>/schedule-etl/', api_views.schedule_etl_api, name='api_schedule_etl'),
    path('api/datasets/join/', api_views.join_datasets_api, name='api_join_datasets'),


    path('api/dashboards/<int:dashboard_id>/share/', api_views.dashboard_share_api, name='api_dashboard_share'),
    path('api/datasets/<int:dataset_id>/share/', api_views.dataset_share_api, name='api_dataset_share'),
    path('api/datasets/<int:dataset_id>/schedules/', api_views.scheduled_refresh_api, name='api_scheduled_refresh'),
    path('api/schedules/<int:schedule_id>/run/', api_views.run_scheduled_refresh_api, name='api_run_scheduled_refresh'),
    path('api/audit-logs/', api_views.audit_logs_api, name='api_audit_logs'),

    # Enterprise Expansion APIs
    path('api/widgets/<int:widget_id>/smart-narrative/', api_views.smart_narrative_api, name='api_smart_narrative'),
    path('api/datasets/sql-connect/', api_views.sql_connect_api, name='api_sql_connect'),
    path('api/datasets/rest-ingest/', api_views.rest_ingest_api, name='api_rest_ingest'),
    path('api/datasets/<int:dataset_id>/what-if/', api_views.what_if_scenario_api, name='api_what_if_scenario'),
    path('api/datasets/<int:dataset_id>/rfm-clustering/', api_views.rfm_clustering_api, name='api_rfm_clustering'),
    path('api/widgets/<int:widget_id>/drill-through/', api_views.drill_through_api, name='api_drill_through'),
    path('api/datasets/<int:dataset_id>/rls-rules/', api_views.rls_rules_api, name='api_rls_rules'),
    path('api/datasets/<int:dataset_id>/dax-eval/', api_views.dax_eval_api, name='api_dax_eval'),
    path('api/widgets/<int:widget_id>/alerts/', api_views.kpi_alerts_api, name='api_kpi_alerts'),
    path('api/widgets/<int:widget_id>/comments/', api_views.widget_comments_api, name='api_widget_comments'),

    # Enterprise Architecture & Production Readiness APIs
    path('api/datasets/<int:dataset_id>/quality-report/', api_views.data_quality_report_api, name='api_data_quality_report'),
    path('api/datasets/<int:dataset_id>/schema-drift/', api_views.schema_drift_api, name='api_schema_drift'),
    path('api/datasets/<int:dataset_id>/versions/', api_views.dataset_versions_api, name='api_dataset_versions'),
    path('api/dashboards/<int:dashboard_id>/bookmarks/', api_views.dashboard_bookmarks_api, name='api_dashboard_bookmarks'),
    path('api/dashboards/<int:dashboard_id>/revisions/', api_views.dashboard_revisions_api, name='api_dashboard_revisions'),
    path('api/dashboards/<int:dashboard_id>/publish-state/', api_views.dashboard_publish_state_api, name='api_dashboard_publish_state'),
    path('api/auth/2fa/', api_views.two_factor_auth_api, name='api_two_factor_auth'),
    path('api/widgets/<int:widget_id>/lttb-downsample/', api_views.lttb_downsample_api, name='api_lttb_downsample'),
    path('metrics/', api_views.prometheus_metrics_api, name='prometheus_metrics'),

    path('api/dashboards/', api_views.dashboards_api, name='api_dashboards_list'),
    path('api/dashboards/<int:dashboard_id>/', api_views.dashboard_detail_api, name='api_dashboard_detail'),
    path('api/dashboards/<int:dashboard_id>/widgets/', api_views.widgets_api, name='api_widgets_list'),
    path('api/dashboards/<int:dashboard_id>/add-chart/', api_views.add_chart_from_chat_api, name='api_add_chart_chat'),
    path('api/dashboards/<int:dashboard_id>/export-template/', api_views.dashboard_export_template_api, name='api_export_template'),
    path('api/dashboards/import-template/', api_views.dashboard_import_template_api, name='api_import_template'),
    path('api/widgets/<int:widget_id>/', api_views.widget_detail_api, name='api_widget_detail'),
    path('api/docs/', api_views.api_docs_api, name='api_docs'),
]

