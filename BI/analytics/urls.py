from django.urls import path
from . import views
from . import api_views

app_name = 'analytics'

urlpatterns = [
    # Main Application & Auth Portal
    path('', views.index_view, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('favicon.ico', views.favicon_view, name='favicon'),
    path('export/<int:dashboard_id>/', views.export_dashboard_view, name='export_dashboard'),
    path('export-csv/<int:dataset_id>/', views.export_csv_view, name='export_csv'),

    # Authentication APIs
    path('api/auth/register/', api_views.auth_register_api, name='api_auth_register'),
    path('api/auth/login/', api_views.auth_login_api, name='api_auth_login'),
    path('api/auth/logout/', api_views.auth_logout_api, name='api_auth_logout'),
    path('api/auth/me/', api_views.auth_me_api, name='api_auth_me'),

    # REST APIs
    path('api/datasets/', api_views.datasets_list_api, name='api_datasets_list'),
    path('api/datasets/mongodb/', api_views.mongodb_dataset_api, name='api_mongodb_dataset'),
    path('api/mongodb/collections/', api_views.mongodb_collections_api, name='api_mongodb_collections'),
    path('api/mongodb/push_json/', api_views.mongodb_push_json_api, name='api_mongodb_push_json'),
    path('api/datasets/<int:dataset_id>/', api_views.dataset_detail_api, name='api_dataset_detail'),
    path('api/datasets/<int:dataset_id>/rows/', api_views.dataset_rows_api, name='api_dataset_rows'),
    path('api/datasets/<int:dataset_id>/filter-values/', api_views.dataset_filter_values_api, name='api_dataset_filter_values'),

    path('api/dashboards/', api_views.dashboards_api, name='api_dashboards_list'),
    path('api/dashboards/<int:dashboard_id>/', api_views.dashboard_detail_api, name='api_dashboard_detail'),
    path('api/dashboards/<int:dashboard_id>/widgets/', api_views.widgets_api, name='api_widgets_list'),
    path('api/widgets/<int:widget_id>/', api_views.widget_detail_api, name='api_widget_detail'),
    path('api/docs/', api_views.api_docs_api, name='api_docs'),
]
