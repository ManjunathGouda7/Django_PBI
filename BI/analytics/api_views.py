import os
import json
import pandas as pd
import numpy as np
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Dataset, Dashboard, Widget, CalculatedMeasure, DatasetColumn, DatasetTag, DatasetSharePermission, DashboardShare, ScheduledRefresh, ActivityLog, UserProfile
from .serializers import DatasetSerializer, DashboardSerializer, WidgetSerializer, UserSerializer, DatasetSharePermissionSerializer, DashboardShareSerializer, ScheduledRefreshSerializer, ActivityLogSerializer
from .permissions import IsOwnerOrReadOnly, IsAdminOrReadOnly, IsOwnerOrShared, HasExportPermission, CanEditDashboard
from .services import DatasetEngine
from .chat_engine import DataChatEngine

# DRF ViewSets
class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all().select_related('profile').order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

class DatasetViewSet(viewsets.ModelViewSet):
    queryset = Dataset.objects.all().select_related('created_by', 'organization').order_by('-created_at')
    serializer_class = DatasetSerializer
    permission_classes = [IsOwnerOrShared]

    @action(detail=True, methods=['get'])
    def schema(self, request, pk=None):
        dataset = self.get_object()
        return Response({'schema': dataset.column_schema, 'row_count': dataset.row_count})

    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        dataset = self.get_object()
        try:
            df = DatasetEngine.load_dataframe(dataset)
            preview_df = df.head(100).fillna('')
            return Response({
                'columns': list(preview_df.columns),
                'data': preview_df.to_dict(orient='records'),
                'total_rows': len(df)
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def add_calculated_column(self, request, pk=None):
        dataset = self.get_object()
        expr_str = request.data.get('expression', '')
        new_col = request.data.get('column_name', '')
        from .services import ExpressionEngine, DatasetEngine, clear_dataset_cache
        try:
            df = DatasetEngine.load_dataframe(dataset)
            updated_df, msg = ExpressionEngine.evaluate_expression(df, expr_str, new_col)
            # Save updated df back to dataset file
            if dataset.file_path and os.path.exists(dataset.file_path):
                updated_df.to_csv(dataset.file_path, index=False)
            dataset.row_count = len(updated_df)
            dataset.save()
            clear_dataset_cache(dataset.id)
            return Response({'status': 'success', 'message': msg, 'columns': list(updated_df.columns)})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def import_sql(self, request):
        db_type = request.data.get('db_type', 'sqlite')
        conn_params = request.data.get('connection_params', {})
        sql_query = request.data.get('sql_query', '')
        dataset_name = request.data.get('name', 'SQL Imported Dataset')
        from .services import SqlConnectorService, DatasetEngine
        try:
            df = SqlConnectorService.execute_query(db_type, conn_params, sql_query)
            dataset = Dataset.objects.create(
                name=dataset_name,
                created_by=request.user if request.user.is_authenticated else None,
                row_count=len(df),
                file_type='sql'
            )
            # Save CSV file storage
            storage_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'media', 'datasets')
            os.makedirs(storage_dir, exist_ok=True)
            fpath = os.path.join(storage_dir, f"sql_dataset_{dataset.id}.csv")
            df.to_csv(fpath, index=False)
            dataset.file_path = fpath
            dataset.save()
            return Response({'status': 'success', 'dataset_id': dataset.id, 'name': dataset.name, 'rows': len(df)})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class DashboardViewSet(viewsets.ModelViewSet):
    queryset = Dashboard.objects.all().select_related('created_by', 'dataset', 'organization').prefetch_related('widgets').order_by('-created_at')
    serializer_class = DashboardSerializer
    permission_classes = [IsOwnerOrShared]

    @action(detail=True, methods=['post'])
    def send_digest(self, request, pk=None):
        dashboard = self.get_object()
        recipients = request.data.get('recipients', [])
        if not recipients and request.user.is_authenticated and request.user.email:
            recipients = [request.user.email]
        from .services import ReportDigestService
        try:
            res = ReportDigestService.send_dashboard_digest(dashboard, recipients)
            return Response(res)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def export_template(self, request, pk=None):
        dashboard = self.get_object()
        from .services import TemplateExporter
        template = TemplateExporter.export_dashboard_template(dashboard)
        return Response(template)

    @action(detail=True, methods=['post'])
    def import_template(self, request, pk=None):
        dashboard = self.get_object()
        template_data = request.data.get('template', {})
        from .services import TemplateExporter
        try:
            TemplateExporter.import_dashboard_template(template_data, dashboard)
            return Response({'status': 'success', 'message': f"Template imported into '{dashboard.title}'."})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class WidgetViewSet(viewsets.ModelViewSet):
    queryset = Widget.objects.all().select_related('dashboard', 'created_by').order_by('-created_at')
    serializer_class = WidgetSerializer
    permission_classes = [IsOwnerOrShared]

# Auth APIs
@csrf_exempt
def auth_register_api(request):
    """
    User Registration Endpoint.
    Public registration is DISABLED. Only authenticated Administrators can register accounts.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)

    profile = getattr(request.user, 'profile', None) if request.user.is_authenticated else None
    is_admin = request.user.is_authenticated and ((profile and profile.is_admin) or request.user.is_superuser or request.user.username.lower() == 'manjunath')
    if not is_admin:
        return JsonResponse({
            'error': 'Public registration is disabled. Please contact your system administrator to obtain access credentials.'
        }, status=403)

    try:
        data = json.loads(request.body)
        username = data.get('username', '').strip()
        login_id = data.get('user_id', username).strip()
        password = data.get('password', '')  # DO NOT strip passwords
        email = data.get('email', '').strip()
        emp_name = data.get('employee_name', '').strip()
        department = data.get('department', '').strip()
        phone = data.get('phone_number', '').strip()
        must_change = bool(data.get('must_change_password', True))

        from .services import EmployeeIdGeneratorService, PasswordPolicyService, AuditLogger
        if not login_id:
            login_id = EmployeeIdGeneratorService.generate_next_id()

        if not password:
            return JsonResponse({'error': 'Password is required.'}, status=400)

        # Validate password complexity
        comp_errs = PasswordPolicyService.validate_complexity(password)
        if comp_errs:
            return JsonResponse({'error': " ".join(comp_errs)}, status=400)

        # User ID validation
        if ' ' in login_id:
            return JsonResponse({'error': 'User ID cannot contain spaces.'}, status=400)

        import re
        if not re.match(r'^[a-zA-Z0-9._-]+$', login_id):
            return JsonResponse({'error': 'User ID may only contain letters, numbers, dots, hyphens, and underscores.'}, status=400)

        if User.objects.filter(username__iexact=login_id).exists() or UserProfile.objects.filter(login_id_lower=login_id.lower()).exists():
            return JsonResponse({'error': f"User ID '{login_id}' already exists."}, status=400)

        user = User.objects.create_user(username=login_id, password=password, email=email)
        user_prof, _ = UserProfile.objects.get_or_create(user=user)
        user_prof.login_id = login_id
        user_prof.employee_number = login_id
        user_prof.employee_name = emp_name
        user_prof.department = department
        user_prof.phone_number = phone
        user_prof.must_change_password = must_change
        user_prof.save()

        PasswordPolicyService.record_password_change(user, password)
        AuditLogger.log_action(request.user, 'USER_CREATE', 'User', user.id, {'user_id': login_id}, request)

        return JsonResponse({
            'message': f"Account for User ID '{login_id}' created successfully.",
            'user': {
                'id': user.id,
                'username': user.username,
                'user_id': login_id,
                'employee_name': emp_name,
                'department': department,
                'email': user.email
            }
        }, status=201)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def auth_login_api(request):
    """
    API Login Endpoint.
    Validates credentials, checks account active/lock status, enforces SecurityLockoutService.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    try:
        data = json.loads(request.body)
        username = data.get('username', '').strip()
        login_id = data.get('user_id', username).strip()
        password = data.get('password', '')  # DO NOT strip passwords

        if not login_id or not password:
            return JsonResponse({'error': 'User ID and Password are required.'}, status=400)

        target_profile = UserProfile.objects.filter(login_id__iexact=login_id).select_related('user').first()
        if not target_profile:
            target_user = User.objects.filter(username__iexact=login_id).first()
            if target_user:
                target_profile, _ = UserProfile.objects.get_or_create(user=target_user)

        from .services import SecurityLockoutService, AuditLogger
        if target_profile and target_profile.is_locked():
            lock_info = SecurityLockoutService.get_lockout_info(target_profile)
            return JsonResponse({
                'error': f"Account is temporarily locked. Please try again in {lock_info['remaining_minutes']} minute(s) or contact your administrator."
            }, status=403)

        # Authenticate
        user = authenticate(request, username=login_id, password=password)
        if user is None and target_profile:
            user = authenticate(request, username=target_profile.user.username, password=password)
        if user is None:
            db_user = User.objects.filter(username__iexact=login_id).first()
            if db_user:
                user = authenticate(request, username=db_user.username, password=password)

        if user is not None:
            profile, _ = UserProfile.objects.get_or_create(user=user)
            if not profile.login_id:
                profile.login_id = user.username
                profile.save(update_fields=['login_id'])

            if not user.is_active:
                return JsonResponse({'error': 'This account has been disabled. Please contact your administrator.'}, status=403)

            SecurityLockoutService.reset_attempts(profile)
            login(request, user)
            AuditLogger.log_action(user, 'API_LOGIN_SUCCESS', 'User', user.id, {'user_id': login_id}, request)

            return JsonResponse({
                'message': 'Login successful',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'user_id': profile.login_id,
                    'email': user.email,
                    'role': profile.role,
                    'must_change_password': profile.must_change_password
                }
            })
        else:
            if target_profile:
                lock_res = SecurityLockoutService.record_failed_attempt(target_profile)
                if lock_res['is_locked']:
                    err_msg = "Account has been temporarily locked due to 5 consecutive failed login attempts. Please try again in 15 minutes or contact your administrator."
                else:
                    err_msg = f"Invalid User ID or Password. {lock_res['remaining_attempts']} attempt(s) remaining before account lockout."
            else:
                err_msg = "Invalid User ID or Password. Please check your credentials."

            AuditLogger.log_action(None, 'API_LOGIN_FAILED', 'User', 0, {'user_id': login_id, 'reason': err_msg}, request)
            return JsonResponse({'error': err_msg}, status=401)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def auth_logout_api(request):
    logout(request)
    return JsonResponse({'message': 'Logged out successfully'})

@csrf_exempt
def auth_me_api(request):
    if request.user.is_authenticated:
        return JsonResponse({
            'authenticated': True,
            'user': {
                'id': request.user.id,
                'username': request.user.username,
                'user_id': getattr(getattr(request.user, 'profile', None), 'login_id', None),
                'email': request.user.email,
                'is_staff': request.user.is_staff
            }
        })
    return JsonResponse({'authenticated': False, 'user': None})

def ensure_sample_data():
    """
    Auto-initializes GRL 25MPLA MongoDB dataset and Executive Power Analytics dashboard.
    """
    if Dataset.objects.count() == 0:
        ds = Dataset.objects.create(
            name="GRL - 25MPLA (192.168.100.123)",
            description="Power telemetry logs from MongoDB server 192.168.100.123:27017 (Database: GRL, Collection: 25MPLA).",
            file_type="mongodb",
            connection_url="mongodb://192.168.100.123:27017",
            db_name="GRL",
            collection_name="25MPLA",
            is_sample=False
        )
        
        try:
            df = DatasetEngine.load_dataframe(ds)
            ds.row_count = len(df)
            ds.column_schema = DatasetEngine.infer_column_schema(df)
            ds.save()
        except Exception as e:
            print(f"Error initializing GRL 25MPLA dataset: {e}")

        # Create Default GRL Power Dashboard
        db = Dashboard.objects.create(
            title="GRL 25MPLA Power Wise Studio",
            description="FPO vs Prect Power Wise Analysis, Board Telemetry, & Power Modes",
            dataset=ds,
            theme="dark_modern"
        )

        Widget.objects.create(
            dashboard=db,
            title="FPO vs Prect Scatter Plot",
            visual_type="scatter",
            x_axis="Rectified Power [W]",
            y_axis="PFO [mW]",
            group_by="Board",
            aggregation="AVG",
            position_x=0, position_y=0, width=12, height=8
        )

@csrf_exempt
def mongodb_collections_api(request):
    url = request.GET.get('connection_url', 'mongodb://192.168.100.123:27017')
    db_name = request.GET.get('db_name', 'GRL')
    res = DatasetEngine.get_mongodb_collections(url, db_name)
    return JsonResponse(res)

@csrf_exempt
def mongodb_push_json_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    try:
        payload = json.loads(request.body)
        url = payload.get('connection_url', 'mongodb://192.168.100.123:27017')
        db_name = payload.get('db_name', 'GRL')
        collection_name = payload.get('collection_name', '25MPLA')

        count = DatasetEngine.push_json_to_mongodb(url, db_name, collection_name)
        return JsonResponse({
            'message': f'Successfully pushed {count} documents from GRL.25MPLA.json into MongoDB ({db_name}.{collection_name})!',
            'inserted_count': count
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def dataset_append_data_api(request, dataset_id=None):
    """
    ADMIN ONLY: Converts an uploaded CSV/Excel/JSON file into JSON format
    and appends all records directly into data/GRL.25MPLA.json and the active dataset.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required. Please sign in.'}, status=401)

    profile = getattr(request.user, 'profile', None) if request.user.is_authenticated else None
    is_admin = request.user.is_authenticated and ((profile and profile.is_admin) or request.user.is_superuser or request.user.username.lower() == 'manjunath')
    if not is_admin:
        return JsonResponse({
            'error': 'Permission Denied: Only Administrators are authorized to convert and append data to the main dataset.'
        }, status=403)

    if 'file' not in request.FILES:
        return JsonResponse({'error': 'No file uploaded. Please select a CSV, Excel, or JSON file.'}, status=400)

    uploaded_file = request.FILES['file']
    try:
        res = DatasetEngine.append_data_to_main_json(uploaded_file, dataset_id=dataset_id)
        if res.get('status') == 'error':
            return JsonResponse({'error': res.get('message', 'Failed to append data')}, status=400)

        from .services import AuditLogger
        AuditLogger.log_action(
            request.user,
            'DATASET_APPEND',
            'Dataset',
            res.get('dataset_id', 0),
            {'added_rows': res.get('added_rows', 0), 'total_rows': res.get('total_rows', 0), 'filename': uploaded_file.name},
            request
        )

        return JsonResponse(res)
    except Exception as e:
        return JsonResponse({'error': f'Failed to process file: {str(e)}'}, status=500)

@csrf_exempt
def mongodb_dataset_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)

    try:
        payload = json.loads(request.body)
        name = payload.get('name', 'MongoDB Collection')
        connection_url = payload.get('connection_url', 'mongodb://localhost:27017')
        db_name = payload.get('db_name')
        collection_name = payload.get('collection_name')

        if not db_name or not collection_name:
            return JsonResponse({'error': 'db_name and collection_name are required.'}, status=400)

        dataset = Dataset.objects.create(
            name=name,
            file_type='mongodb',
            connection_url=connection_url,
            db_name=db_name,
            collection_name=collection_name,
            is_sample=False
        )

        df = DatasetEngine.load_dataframe(dataset)
        if df.empty:
            dataset.delete()
            return JsonResponse({'error': 'MongoDB collection is empty or unreachable.'}, status=400)

        dataset.row_count = len(df)
        dataset.column_schema = DatasetEngine.infer_column_schema(df)
        dataset.save()

        return JsonResponse({
            'message': 'MongoDB collection connected and imported successfully!',
            'dataset': {
                'id': dataset.id,
                'name': dataset.name,
                'row_count': dataset.row_count,
                'column_schema': dataset.column_schema
            }
        })
    except Exception as e:
        return JsonResponse({'error': f'Failed to connect to MongoDB: {str(e)}'}, status=400)

@csrf_exempt
def datasets_list_api(request):
    ensure_sample_data()
    if request.method == 'GET':
        datasets = Dataset.objects.all().order_by('-created_at')
        data = []
        for ds in datasets:
            data.append({
                'id': ds.id,
                'name': ds.name,
                'description': ds.description,
                'file_type': ds.file_type,
                'row_count': ds.row_count,
                'is_sample': ds.is_sample,
                'column_schema': ds.column_schema,
                'created_at': ds.created_at.strftime('%Y-%m-%d %H:%M')
            })
        return JsonResponse({'datasets': data})

    elif request.method == 'POST':
        name = request.POST.get('name')
        file_obj = request.FILES.get('file')
        replace_existing = request.POST.get('replace_existing', 'false').lower() == 'true'
        append_to_main = request.POST.get('append_to_main', 'false').lower() == 'true'

        if not file_obj:
            return JsonResponse({'error': 'A file is required for upload.'}, status=400)

        # Handle Admin Append to data/GRL.25MPLA.json
        if append_to_main:
            profile = getattr(request.user, 'profile', None) if request.user.is_authenticated else None
            is_admin = request.user.is_authenticated and ((profile and profile.is_admin) or request.user.is_superuser or request.user.username.lower() == 'manjunath')
            if not is_admin:
                return JsonResponse({'error': 'Permission Denied: Only Administrators can append data to the main dataset.'}, status=403)

            res = DatasetEngine.append_data_to_main_json(file_obj)
            if res.get('status') == 'error':
                return JsonResponse({'error': res.get('message', 'Failed to append data.')}, status=400)

            target_ds = Dataset.objects.filter(file_type='mongodb').first() or Dataset.objects.first()
            if target_ds:
                target_ds.row_count = res.get('total_rows', target_ds.row_count)
                target_ds.save(update_fields=['row_count', 'updated_at'])

            from .services import AuditLogger
            AuditLogger.log_action(
                request.user,
                'DATASET_APPEND',
                'Dataset',
                res.get('dataset_id', target_ds.id if target_ds else 0),
                {'added_rows': res.get('added_rows', 0), 'total_rows': res.get('total_rows', 0), 'filename': file_obj.name},
                request
            )

            return JsonResponse({
                'message': res.get('message'),
                'added_rows': res.get('added_rows', 0),
                'total_rows': res.get('total_rows', 0),
                'dataset': {
                    'id': target_ds.id if target_ds else None,
                    'name': target_ds.name if target_ds else 'GRL - 25MPLA (192.168.100.123)',
                    'row_count': res.get('total_rows', 0),
                    'column_schema': target_ds.column_schema if target_ds else []
                }
            })

        if not name:
            name = os.path.splitext(file_obj.name)[0] if hasattr(file_obj, 'name') else 'New Dataset'

        fname = file_obj.name.lower()
        if fname.endswith('.json'):
            file_type = 'json'
        elif fname.endswith(('.xlsx', '.xls')):
            file_type = 'excel'
        elif fname.endswith('.csv'):
            file_type = 'csv'
        else:
            return JsonResponse({'error': f'Unsupported file extension. Allowed extensions: .csv, .excel, .json'}, status=400)

        try:
            from .services import DatasetValidator
            validated_df = DatasetValidator.validate_and_parse(file_obj, file_type)
        except ValueError as val_err:
            return JsonResponse({'error': str(val_err)}, status=400)

        user = request.user if request.user.is_authenticated else None

        existing_dataset = Dataset.objects.filter(name=name).first()
        if replace_existing and existing_dataset:
            dataset = existing_dataset
            dataset.file = file_obj
            dataset.file_type = file_type
            dataset.save()
        else:
            dataset = Dataset.objects.create(
                name=name,
                file=file_obj,
                file_type=file_type,
                created_by=user,
                is_sample=False
            )

        try:
            DatasetEngine.clear_cache(dataset.id)
            df = DatasetEngine.load_dataframe(dataset)
            dataset.row_count = len(df)
            dataset.column_schema = DatasetEngine.infer_column_schema(df)
            dataset.save()
            return JsonResponse({
                'message': 'Dataset uploaded successfully!',
                'dataset': {
                    'id': dataset.id,
                    'name': dataset.name,
                    'row_count': dataset.row_count,
                    'column_schema': dataset.column_schema
                }
            })
        except Exception as e:
            if not replace_existing:
                dataset.delete()
            return JsonResponse({'error': f'Failed to process file: {str(e)}'}, status=400)

@csrf_exempt
def dataset_detail_api(request, dataset_id):
    dataset = get_object_or_404(Dataset, pk=dataset_id)

    if request.method == 'DELETE':
        ds_name = dataset.name
        if dataset.file and hasattr(dataset.file, 'path') and os.path.exists(dataset.file.path):
            try:
                os.remove(dataset.file.path)
            except Exception:
                pass
        DatasetEngine.clear_cache(dataset.id)
        dataset.delete()
        return JsonResponse({'message': f'Dataset "{ds_name}" and file deleted successfully!'})

    if request.method in ['PUT', 'POST'] and request.FILES.get('file'):
        try:
            file_obj = request.FILES['file']
            fname = file_obj.name.lower()
            if fname.endswith('.json'):
                dataset.file_type = 'json'
            elif fname.endswith(('.xlsx', '.xls')):
                dataset.file_type = 'excel'
            elif fname.endswith('.csv'):
                dataset.file_type = 'csv'

            # Remove old file if exists
            if dataset.file and hasattr(dataset.file, 'path') and os.path.exists(dataset.file.path):
                try:
                    os.remove(dataset.file.path)
                except Exception:
                    pass

            dataset.file = file_obj
            dataset.save()

            DatasetEngine.clear_cache(dataset.id)
            df = DatasetEngine.load_dataframe(dataset)
            dataset.row_count = len(df)
            dataset.column_schema = DatasetEngine.infer_column_schema(df)
            dataset.save()

            return JsonResponse({
                'message': f'Dataset "{dataset.name}" file replaced and re-indexed successfully!',
                'id': dataset.id,
                'name': dataset.name,
                'row_count': dataset.row_count,
                'column_schema': dataset.column_schema
            })
        except Exception as e:
            return JsonResponse({'error': f'Failed to update dataset file: {str(e)}'}, status=400)

    return JsonResponse({
        'id': dataset.id,
        'name': dataset.name,
        'description': dataset.description,
        'row_count': dataset.row_count,
        'file_type': dataset.file_type,
        'column_schema': dataset.column_schema
    })

@csrf_exempt
def dataset_chat_api(request, dataset_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    dataset = get_object_or_404(Dataset, pk=dataset_id)
    try:
        payload = json.loads(request.body)
        query = payload.get('message', '').strip()
        result = DataChatEngine.process_query(dataset, query)
        return JsonResponse({
            'dataset_id': dataset.id,
            'dataset_name': dataset.name,
            'status': 'success',
            'data': result
        })
    except Exception as e:
        return JsonResponse({'error': f"Failed to process chat query: {str(e)}"}, status=400)

@csrf_exempt
def dataset_filter_values_api(request, dataset_id):
    dataset = get_object_or_404(Dataset, pk=dataset_id)
    col = request.GET.get('col', '').strip()
    if not col:
        return JsonResponse({'error': 'col parameter required'}, status=400)
    try:
        df = DatasetEngine.load_dataframe(dataset)
        if col not in df.columns:
            return JsonResponse({'error': f'Column "{col}" not found'}, status=404)

        slicers_raw = request.GET.get('slicers', '')
        if slicers_raw:
            try:
                slicers = json.loads(slicers_raw)
                for s_col, vals in slicers.items():
                    if s_col != col and s_col in df.columns and isinstance(vals, list) and len(vals) > 0:
                        df = df[df[s_col].astype(str).isin([str(v) for v in vals])]
            except Exception:
                pass

        is_numeric = pd.api.types.is_numeric_dtype(df[col])
        num_min = None
        num_max = None
        if is_numeric:
            num_series = pd.to_numeric(df[col], errors='coerce').dropna()
            if not num_series.empty:
                num_min = round(float(num_series.min()), 2)
                num_max = round(float(num_series.max()), 2)

        counts = df[col].dropna().astype(str).value_counts().sort_index()
        values = [{'value': str(v), 'count': int(c)} for v, c in counts.items()]
        values = values[:200]
        total = int(df[col].count())
        return JsonResponse({
            'col': col,
            'is_numeric': is_numeric,
            'min': num_min,
            'max': num_max,
            'values': values,
            'total': total
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

def dataset_rows_api(request, dataset_id):
    dataset = get_object_or_404(Dataset, pk=dataset_id)
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 50))
    search = request.GET.get('search', '').strip()
    sort_col = request.GET.get('sort_col', '').strip()
    sort_dir = request.GET.get('sort_dir', 'asc')

    try:
        df = DatasetEngine.load_dataframe(dataset)

        if search:
            mask = np.column_stack([df[col].astype(str).str.contains(search, case=False, na=False) for col in df.columns])
            df = df[mask.any(axis=1)]

        if sort_col and sort_col in df.columns:
            ascending = (sort_dir != 'desc')
            df = df.sort_values(by=sort_col, ascending=ascending)

        total_rows = len(df)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size

        page_df = df.iloc[start_idx:end_idx].fillna('')
        rows = page_df.to_dict(orient='records')

        return JsonResponse({
            'total_rows': total_rows,
            'page': page,
            'page_size': page_size,
            'total_pages': max(1, (total_rows + page_size - 1) // page_size),
            'columns': list(df.columns),
            'rows': rows
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def dashboards_api(request):
    ensure_sample_data()
    if request.method == 'GET':
        dashboards = Dashboard.objects.all().order_by('-created_at')
        data = []
        for db in dashboards:
            data.append({
                'id': db.id,
                'title': db.title,
                'description': db.description,
                'dataset_id': db.dataset_id,
                'dataset_name': db.dataset.name,
                'theme': db.theme,
                'widget_count': db.widgets.count(),
                'updated_at': db.updated_at.strftime('%Y-%m-%d %H:%M')
            })
        return JsonResponse({'dashboards': data})

    elif request.method == 'POST':
        try:
            payload = json.loads(request.body)
            title = payload.get('title', 'New Power BI Dashboard')
            dataset_id = payload.get('dataset_id')
            theme = payload.get('theme', 'dark_modern')
            description = payload.get('description', '')

            dataset = get_object_or_404(Dataset, pk=dataset_id)
            db = Dashboard.objects.create(
                title=title,
                dataset=dataset,
                theme=theme,
                description=description
            )
            return JsonResponse({'message': 'Dashboard created', 'id': db.id})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def dashboard_detail_api(request, dashboard_id):
    db = get_object_or_404(Dashboard, pk=dashboard_id)

    if request.method == 'DELETE':
        db.delete()
        return JsonResponse({'message': 'Dashboard deleted'})

    if request.method == 'PUT':
        try:
            payload = json.loads(request.body)
            if 'title' in payload:
                db.title = payload['title']
            if 'theme' in payload:
                db.theme = payload['theme']
            if 'description' in payload:
                db.description = payload['description']
            if 'dataset_id' in payload:
                target_ds = get_object_or_404(Dataset, pk=payload['dataset_id'])
                db.dataset = target_ds
            db.save()
            return JsonResponse({'message': 'Dashboard updated', 'dataset_id': db.dataset_id})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    slicers_raw = request.GET.get('slicers', '{}')
    try:
        slicers = json.loads(slicers_raw)
    except Exception:
        slicers = {}

    widgets_data = []
    for w in db.widgets.all():
        chart_data = DatasetEngine.query_widget_data(db.dataset, w, filters=slicers)
        widgets_data.append({
            'id': w.id,
            'title': w.title,
            'visual_type': w.visual_type,
            'x_axis': w.x_axis,
            'y_axis': w.y_axis,
            'aggregation': w.aggregation,
            'group_by': w.group_by,
            'position_x': w.position_x,
            'position_y': w.position_y,
            'width': w.width,
            'height': w.height,
            'chart_data': chart_data
        })

    return JsonResponse({
        'id': db.id,
        'title': db.title,
        'description': db.description,
        'theme': db.theme,
        'dataset': {
            'id': db.dataset.id,
            'name': db.dataset.name,
            'row_count': db.dataset.row_count,
            'column_schema': db.dataset.column_schema
        },
        'widgets': widgets_data
    })

@csrf_exempt
def widgets_api(request, dashboard_id):
    db = get_object_or_404(Dashboard, pk=dashboard_id)

    if request.method == 'GET':
        widgets = db.widgets.all()
        data = [{'id': w.id, 'title': w.title, 'visual_type': w.visual_type, 'x_axis': w.x_axis, 'y_axis': w.y_axis, 'aggregation': w.aggregation} for w in widgets]
        return JsonResponse({'widgets': data})

    if request.method == 'POST':
        try:
            payload = json.loads(request.body)
            w = Widget.objects.create(
                dashboard=db,
                title=payload.get('title', 'New Visual'),
                visual_type=payload.get('visual_type', 'bar'),
                x_axis=payload.get('x_axis'),
                y_axis=payload.get('y_axis'),
                aggregation=payload.get('aggregation', 'SUM'),
                position_x=payload.get('position_x', 0),
                position_y=payload.get('position_y', 0),
                width=payload.get('width', 6),
                height=payload.get('height', 4)
            )
            return JsonResponse({'message': 'Widget created', 'id': w.id})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Method not allowed'}, status=405)

@csrf_exempt
def widget_detail_api(request, widget_id):
    w = get_object_or_404(Widget, pk=widget_id)

    if request.method == 'GET':
        return JsonResponse({
            'id': w.id,
            'title': w.title,
            'visual_type': w.visual_type,
            'x_axis': w.x_axis,
            'y_axis': w.y_axis,
            'aggregation': w.aggregation,
            'position_x': w.position_x,
            'position_y': w.position_y,
            'width': w.width,
            'height': w.height
        })

    if request.method == 'DELETE':
        w.delete()
        return JsonResponse({'message': 'Widget deleted'})

    if request.method == 'PUT':
        try:
            payload = json.loads(request.body)
            w.title = payload.get('title', w.title)
            w.visual_type = payload.get('visual_type', w.visual_type)
            w.x_axis = payload.get('x_axis', w.x_axis)
            w.y_axis = payload.get('y_axis', w.y_axis)
            w.aggregation = payload.get('aggregation', w.aggregation)
            if 'position_x' in payload:
                w.position_x = payload['position_x']
            if 'position_y' in payload:
                w.position_y = payload['position_y']
            if 'width' in payload:
                w.width = payload['width']
            if 'height' in payload:
                w.height = payload['height']
            w.save()
            return JsonResponse({'message': 'Widget updated'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Method not allowed'}, status=405)

@csrf_exempt
def api_docs_api(request):
    openapi_spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "Django Power BI Studio Telemetry Analytics API",
            "version": "1.0.0",
            "description": "High-performance REST API endpoints for telemetry datasets, interactive visual canvas, and slicers filtering."
        },
        "paths": {
            "/api/datasets/": {"get": {"summary": "List all active datasets"}},
            "/api/dashboards/{id}/": {"get": {"summary": "Full dashboard details"}}
        }
    }
    return JsonResponse(openapi_spec)

@csrf_exempt
def auto_dashboard_api(request, dataset_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    dataset = get_object_or_404(Dataset, pk=dataset_id)
    try:
        from .analytics_advanced import AIAutoBuilder
        user = request.user if request.user.is_authenticated else None
        dashboard = AIAutoBuilder.build_auto_dashboard(dataset, user=user)
        return JsonResponse({
            'message': 'AI Auto-Dashboard generated successfully!',
            'dashboard_id': dashboard.id,
            'title': dashboard.title
        })
    except Exception as e:
        return JsonResponse({'error': f"Failed to build auto-dashboard: {str(e)}"}, status=400)

@csrf_exempt
def add_chart_from_chat_api(request, dashboard_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    dashboard = get_object_or_404(Dashboard, pk=dashboard_id)
    try:
        payload = json.loads(request.body)
        from .analytics_advanced import AIAutoBuilder
        user = request.user if request.user.is_authenticated else None
        widget = AIAutoBuilder.create_widget_from_chat(
            dashboard=dashboard,
            title=payload.get('title', 'AI Generated Visual'),
            visual_type=payload.get('visual_type', 'bar'),
            x_axis=payload.get('x_axis'),
            y_axis=payload.get('y_axis'),
            aggregation=payload.get('aggregation', 'AVG'),
            group_by=payload.get('group_by'),
            user=user
        )
        return JsonResponse({'message': 'Visual added to canvas successfully!', 'widget_id': widget.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

def dataset_anomalies_api(request, dataset_id):
    dataset = get_object_or_404(Dataset, pk=dataset_id)
    try:
        from .analytics_advanced import AnomalyEngine
        anomalies_data = AnomalyEngine.detect_anomalies(dataset)
        return JsonResponse({'status': 'success', 'data': anomalies_data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def clean_dataset_api(request, dataset_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    dataset = get_object_or_404(Dataset, pk=dataset_id)
    try:
        payload = json.loads(request.body)
        fill_method = payload.get('fill_method')
        remove_duplicates = payload.get('remove_duplicates', False)
        drop_nulls = payload.get('drop_nulls', False)
        from .analytics_advanced import DataWrangler
        ds = DataWrangler.clean_dataset(dataset, fill_method, remove_duplicates, drop_nulls)
        return JsonResponse({'message': 'Dataset cleaned successfully!', 'row_count': ds.row_count})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def add_measure_api(request, dataset_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    dataset = get_object_or_404(Dataset, pk=dataset_id)
    try:
        payload = json.loads(request.body)
        name = payload.get('name')
        formula = payload.get('formula')
        if not name or not formula:
            return JsonResponse({'error': 'Name and formula are required.'}, status=400)
        from .analytics_advanced import DataWrangler
        measure_name = DataWrangler.add_calculated_measure(dataset, name, formula)
        return JsonResponse({'message': f"Calculated measure '{measure_name}' created successfully!", 'name': measure_name})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def join_datasets_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    try:
        payload = json.loads(request.body)
        dataset1_id = payload.get('dataset1_id')
        dataset2_id = payload.get('dataset2_id')
        key_col1 = payload.get('key_col1')
        key_col2 = payload.get('key_col2')
        join_type = payload.get('join_type', 'inner')
        name = payload.get('name')

        ds1 = get_object_or_404(Dataset, pk=dataset1_id)
        ds2 = get_object_or_404(Dataset, pk=dataset2_id)

        from .analytics_advanced import DatasetJoiner
        new_ds = DatasetJoiner.join_datasets(ds1, ds2, key_col1, key_col2, join_type, name)
        return JsonResponse({
            'message': f"Datasets merged successfully!",
            'dataset': {
                'id': new_ds.id,
                'name': new_ds.name,
                'row_count': new_ds.row_count
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def dashboard_export_template_api(request, dashboard_id):
    dashboard = get_object_or_404(Dashboard, pk=dashboard_id)
    from .analytics_advanced import TemplateManager
    template_json = TemplateManager.export_template(dashboard)
    response = JsonResponse(template_json)
    response['Content-Disposition'] = f'attachment; filename="Dashboard_{dashboard.id}_Template.json"'
    return response

@csrf_exempt
def dashboard_import_template_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    try:
        payload = json.loads(request.body)
        dataset_id = payload.get('dataset_id')
        template_json = payload.get('template')
        title = payload.get('title')

        dataset = get_object_or_404(Dataset, pk=dataset_id)
        user = request.user if request.user.is_authenticated else None
        from .analytics_advanced import TemplateManager
        db = TemplateManager.import_template(dataset, template_json, title, user)
        return JsonResponse({'message': 'Dashboard imported from template successfully!', 'dashboard_id': db.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

def dataset_forecast_api(request, dataset_id):
    dataset = get_object_or_404(Dataset, pk=dataset_id)
    metric_col = request.GET.get('metric')
    periods = int(request.GET.get('periods', 7))
    try:
        from .analytics_advanced import ForecastingEngine
        forecast_data = ForecastingEngine.generate_forecast(dataset, metric_col, periods)
        return JsonResponse({'status': 'success', 'data': forecast_data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def nl_formula_api(request, dataset_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    dataset = get_object_or_404(Dataset, pk=dataset_id)
    try:
        payload = json.loads(request.body)
        prompt = payload.get('prompt', '')
        if not prompt:
            return JsonResponse({'error': 'Prompt is required.'}, status=400)
        from .analytics_advanced import NLToFormulaEngine
        result = NLToFormulaEngine.generate_formula_from_nl(dataset, prompt)
        return JsonResponse({'status': 'success', 'data': result})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def schedule_etl_api(request, dataset_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    dataset = get_object_or_404(Dataset, pk=dataset_id)
    try:
        from .analytics_advanced import ETLPipeline
        etl_result = ETLPipeline.run_etl_sync(dataset)
        return JsonResponse({'status': 'success', 'data': etl_result})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def dashboard_share_api(request, dashboard_id):
    dashboard = get_object_or_404(Dashboard, pk=dashboard_id)

    if request.method == 'GET':
        shares = dashboard.shares.all()
        serializer = DashboardShareSerializer(shares, many=True)
        return JsonResponse({'status': 'success', 'shares': serializer.data})

    elif request.method == 'POST':
        try:
            payload = json.loads(request.body)
            email = payload.get('email', '').strip()
            user_id = payload.get('user_id')
            permission_level = payload.get('permission_level', 'view')
            can_export = payload.get('can_export', True)

            target_user = User.objects.filter(pk=user_id).first() if user_id else None
            share = DashboardShare.objects.create(
                dashboard=dashboard,
                user=target_user,
                email=email,
                permission_level=permission_level,
                can_export=can_export
            )
            from .services import AuditLogger
            AuditLogger.log_action(request.user, 'SHARE', 'Dashboard', dashboard.id, {'shared_email': email, 'permission_level': permission_level}, request)
            return JsonResponse({'status': 'success', 'share_id': share.id, 'message': 'Dashboard shared successfully!'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    elif request.method == 'DELETE':
        try:
            share_id = request.GET.get('share_id')
            share = get_object_or_404(DashboardShare, pk=share_id, dashboard=dashboard)
            share.delete()
            return JsonResponse({'status': 'success', 'message': 'Share revoked successfully!'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def dataset_share_api(request, dataset_id):
    dataset = get_object_or_404(Dataset, pk=dataset_id)

    if request.method == 'GET':
        shares = dataset.share_permissions.all()
        serializer = DatasetSharePermissionSerializer(shares, many=True)
        return JsonResponse({'status': 'success', 'shares': serializer.data})

    elif request.method == 'POST':
        try:
            payload = json.loads(request.body)
            email = payload.get('email', '').strip()
            user_id = payload.get('user_id')
            permission_level = payload.get('permission_level', 'view')
            can_export = payload.get('can_export', True)

            target_user = User.objects.filter(pk=user_id).first() if user_id else None
            share = DatasetSharePermission.objects.create(
                dataset=dataset,
                user=target_user,
                email=email,
                permission_level=permission_level,
                can_export=can_export
            )
            from .services import AuditLogger
            AuditLogger.log_action(request.user, 'SHARE', 'Dataset', dataset.id, {'shared_email': email, 'permission_level': permission_level}, request)
            return JsonResponse({'status': 'success', 'share_id': share.id, 'message': 'Dataset shared successfully!'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def scheduled_refresh_api(request, dataset_id):
    dataset = get_object_or_404(Dataset, pk=dataset_id)

    if request.method == 'GET':
        schedules = dataset.schedules.all()
        serializer = ScheduledRefreshSerializer(schedules, many=True)
        return JsonResponse({'status': 'success', 'schedules': serializer.data})

    elif request.method == 'POST':
        try:
            payload = json.loads(request.body)
            frequency = payload.get('frequency', 'daily')
            schedule = ScheduledRefresh.objects.create(
                dataset=dataset,
                frequency=frequency,
                created_by=request.user if request.user.is_authenticated else None
            )
            return JsonResponse({'status': 'success', 'schedule_id': schedule.id, 'message': 'Scheduled refresh created!'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def run_scheduled_refresh_api(request, schedule_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    schedule = get_object_or_404(ScheduledRefresh, pk=schedule_id)
    try:
        from .tasks import async_run_scheduled_refresh_task
        res = async_run_scheduled_refresh_task(schedule.id)
        from .services import AuditLogger
        AuditLogger.log_action(request.user, 'REFRESH', 'Dataset', schedule.dataset.id if schedule.dataset else 0, {'schedule_id': schedule.id}, request)
        return JsonResponse({'status': 'success', 'result': res})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def audit_logs_api(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'GET method required'}, status=405)
    try:
        logs = ActivityLog.objects.all().order_by('-timestamp')
        resource_type = request.GET.get('resource_type')
        action_type = request.GET.get('action_type')

        if resource_type:
            logs = logs.filter(resource_type__iexact=resource_type)
        if action_type:
            logs = logs.filter(action_type__iexact=action_type)

        logs = logs[:100]
        serializer = ActivityLogSerializer(logs, many=True)
        return JsonResponse({'status': 'success', 'audit_logs': serializer.data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def smart_narrative_api(request, widget_id):
    if request.method != 'GET':
        return JsonResponse({'error': 'GET method required'}, status=405)
    widget = get_object_or_404(Widget, pk=widget_id)
    try:
        from .services import DatasetEngine, SmartNarrativeEngine
        df = DatasetEngine.load_dataframe(widget.dashboard.dataset)
        bullets = SmartNarrativeEngine.generate_widget_narrative(df, widget)
        return JsonResponse({'status': 'success', 'widget_id': widget.id, 'narrative': bullets})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def sql_connect_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    try:
        payload = json.loads(request.body)
        engine_type = payload.get('engine_type', 'sqlite')
        host = payload.get('host', 'local')
        port = payload.get('port', 5432)
        db_name = payload.get('db_name', '')
        username = payload.get('username', '')
        password = payload.get('password', '')
        query = payload.get('query', 'SELECT 1;')

        from .services import SQLDatabaseConnector
        df = SQLDatabaseConnector.execute_live_query(engine_type, host, port, db_name, username, password, query)
        return JsonResponse({
            'status': 'success',
            'row_count': len(df),
            'columns': list(df.columns),
            'data': df.fillna('').to_dict(orient='records')
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def rest_ingest_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    try:
        payload = json.loads(request.body)
        endpoint_url = payload.get('endpoint_url')
        method = payload.get('method', 'GET')
        headers = payload.get('headers', {})
        json_path = payload.get('json_path', '')

        from .services import RESTDataConnector
        df = RESTDataConnector.fetch_json_feed(endpoint_url, method, headers, json_path)
        return JsonResponse({
            'status': 'success',
            'row_count': len(df),
            'columns': list(df.columns),
            'sample_data': df.head(10).fillna('').to_dict(orient='records')
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def what_if_scenario_api(request, dataset_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    dataset = get_object_or_404(Dataset, pk=dataset_id)
    try:
        payload = json.loads(request.body)
        adjustments = payload.get('adjustments', [])
        from .services import DatasetEngine, WhatIfScenarioEngine
        df = DatasetEngine.load_dataframe(dataset)
        df_sim, scenario_metrics = WhatIfScenarioEngine.simulate_scenario(df, adjustments)
        return JsonResponse({
            'status': 'success',
            'dataset_id': dataset.id,
            'scenario_metrics': scenario_metrics
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def rfm_clustering_api(request, dataset_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    dataset = get_object_or_404(Dataset, pk=dataset_id)
    try:
        payload = json.loads(request.body)
        customer_id_col = payload.get('customer_id_col')
        date_col = payload.get('date_col', '')
        monetary_col = payload.get('monetary_col')
        n_clusters = int(payload.get('n_clusters', 3))

        from .services import DatasetEngine, CustomerSegmentationEngine
        df = DatasetEngine.load_dataframe(dataset)
        segments = CustomerSegmentationEngine.rfm_clustering(df, customer_id_col, date_col, monetary_col, n_clusters)
        return JsonResponse({'status': 'success', 'segments': segments})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def drill_through_api(request, widget_id):
    if request.method != 'GET':
        return JsonResponse({'error': 'GET method required'}, status=405)
    widget = get_object_or_404(Widget, pk=widget_id)
    try:
        category_col = request.GET.get('category_col', widget.x_axis)
        category_val = request.GET.get('category_val', '')

        from .services import DatasetEngine
        df = DatasetEngine.load_dataframe(widget.dashboard.dataset)
        if category_col in df.columns and category_val:
            df = df[df[category_col].astype(str) == str(category_val)]

        return JsonResponse({
            'status': 'success',
            'widget_title': widget.title,
            'category_col': category_col,
            'category_val': category_val,
            'total_rows': len(df),
            'rows': df.head(100).fillna('').to_dict(orient='records')
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def rls_rules_api(request, dataset_id):
    dataset = get_object_or_404(Dataset, pk=dataset_id)
    from .models import RowLevelSecurityRule
    from .serializers import RowLevelSecurityRuleSerializer

    if request.method == 'GET':
        rules = dataset.rls_rules.filter(is_active=True)
        serializer = RowLevelSecurityRuleSerializer(rules, many=True)
        return JsonResponse({'status': 'success', 'rls_rules': serializer.data})

    elif request.method == 'POST':
        try:
            payload = json.loads(request.body)
            col = payload.get('column_name')
            op = payload.get('operator', 'eq')
            val = payload.get('filter_value')
            role = payload.get('role', '')

            rule = RowLevelSecurityRule.objects.create(
                dataset=dataset,
                user=request.user if request.user.is_authenticated else None,
                role=role,
                column_name=col,
                operator=op,
                filter_value=val
            )
            return JsonResponse({'status': 'success', 'rule_id': rule.id, 'message': 'RLS rule created!'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def dax_eval_api(request, dataset_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    dataset = get_object_or_404(Dataset, pk=dataset_id)
    try:
        payload = json.loads(request.body)
        formula = payload.get('formula', '')

        from .services import DatasetEngine, DAXFormulaParser
        df = DatasetEngine.load_dataframe(dataset)
        result = DAXFormulaParser.evaluate_formula(df, formula)
        return JsonResponse({'status': 'success', 'formula': formula, 'result': result})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def kpi_alerts_api(request, widget_id):
    widget = get_object_or_404(Widget, pk=widget_id)
    from .models import KPIAlertRule
    from .serializers import KPIAlertRuleSerializer

    if request.method == 'GET':
        alerts = widget.alerts.filter(is_active=True)
        serializer = KPIAlertRuleSerializer(alerts, many=True)
        return JsonResponse({'status': 'success', 'alerts': serializer.data})

    elif request.method == 'POST':
        try:
            payload = json.loads(request.body)
            metric_col = payload.get('metric_column', widget.y_axis)
            cond = payload.get('condition', 'gt')
            thresh = float(payload.get('threshold_value', 0))
            channel = payload.get('channel', 'webhook')
            webhook_url = payload.get('webhook_url', '')

            alert = KPIAlertRule.objects.create(
                widget=widget,
                created_by=request.user if request.user.is_authenticated else None,
                metric_column=metric_col,
                condition=cond,
                threshold_value=thresh,
                channel=channel,
                webhook_url=webhook_url
            )
            return JsonResponse({'status': 'success', 'alert_id': alert.id, 'message': 'KPI Alert rule set successfully!'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def widget_comments_api(request, widget_id):
    widget = get_object_or_404(Widget, pk=widget_id)
    from .models import WidgetComment
    from .serializers import WidgetCommentSerializer

    if request.method == 'GET':
        comments = widget.comments.all().order_by('-created_at')
        serializer = WidgetCommentSerializer(comments, many=True)
        return JsonResponse({'status': 'success', 'comments': serializer.data})

    elif request.method == 'POST':
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'error': 'Authentication required to post comments'}, status=401)
            payload = json.loads(request.body)
            text = payload.get('comment_text', '').strip()
            pin_x = float(payload.get('pin_x', 0))
            pin_y = float(payload.get('pin_y', 0))

            comment = WidgetComment.objects.create(
                widget=widget,
                user=request.user,
                comment_text=text,
                pin_x=pin_x,
                pin_y=pin_y
            )
            return JsonResponse({'status': 'success', 'comment_id': comment.id, 'message': 'Comment posted!'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def data_quality_report_api(request, dataset_id):
    """Returns or generates automated data quality profiling reports"""
    dataset = get_object_or_404(Dataset, pk=dataset_id)
    from .services import DatasetEngine, DataQualityEngine
    from .serializers import DataQualityReportSerializer

    if request.method == 'GET':
        report = dataset.quality_reports.first()
        if not report:
            df = DatasetEngine.load_dataframe(dataset)
            report = DataQualityEngine.generate_quality_report(dataset, df)
        serializer = DataQualityReportSerializer(report)
        return JsonResponse({'status': 'success', 'quality_report': serializer.data})

    elif request.method == 'POST':
        df = DatasetEngine.load_dataframe(dataset)
        report = DataQualityEngine.generate_quality_report(dataset, df)
        serializer = DataQualityReportSerializer(report)
        return JsonResponse({'status': 'success', 'quality_report': serializer.data, 'message': 'Quality report regenerated.'})

@csrf_exempt
def schema_drift_api(request, dataset_id):
    """Compares active dataframe against registered column signatures to detect drift"""
    dataset = get_object_or_404(Dataset, pk=dataset_id)
    from .services import DatasetEngine, SchemaDriftDetector
    df = DatasetEngine.load_dataframe(dataset)
    drift = SchemaDriftDetector.detect_drift(dataset, df)
    return JsonResponse({'status': 'success', 'drift_analysis': drift})

@csrf_exempt
def dataset_versions_api(request, dataset_id):
    """Returns historical lineage snapshots for the dataset"""
    dataset = get_object_or_404(Dataset, pk=dataset_id)
    from .serializers import DatasetVersionSerializer
    versions = dataset.versions.all()
    serializer = DatasetVersionSerializer(versions, many=True)
    return JsonResponse({'status': 'success', 'versions': serializer.data})

@csrf_exempt
def dashboard_bookmarks_api(request, dashboard_id):
    """Manages saved slicer and visual filter bookmarks"""
    dashboard = get_object_or_404(Dashboard, pk=dashboard_id)
    from .models import DashboardBookmark
    from .serializers import DashboardBookmarkSerializer

    if request.method == 'GET':
        if not request.user.is_authenticated:
            return JsonResponse({'status': 'success', 'bookmarks': []})
        bookmarks = dashboard.saved_bookmarks.filter(user=request.user)
        serializer = DashboardBookmarkSerializer(bookmarks, many=True)
        return JsonResponse({'status': 'success', 'bookmarks': serializer.data})

    elif request.method == 'POST':
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        try:
            payload = json.loads(request.body)
            name = payload.get('name', f"Bookmark {timezone.now().strftime('%b %d, %H:%M')}")
            state = payload.get('state', {})
            bookmark, created = DashboardBookmark.objects.update_or_create(
                dashboard=dashboard,
                user=request.user,
                name=name,
                defaults={'state': state, 'is_default': payload.get('is_default', False)}
            )
            return JsonResponse({'status': 'success', 'bookmark_id': bookmark.id, 'created': created})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def dashboard_revisions_api(request, dashboard_id):
    """Tracks historical layout versions and 1-click snapshot rollback"""
    dashboard = get_object_or_404(Dashboard, pk=dashboard_id)
    from .models import DashboardRevision
    from .serializers import DashboardRevisionSerializer

    if request.method == 'GET':
        revisions = dashboard.revisions.all()
        serializer = DashboardRevisionSerializer(revisions, many=True)
        return JsonResponse({'status': 'success', 'revisions': serializer.data})

    elif request.method == 'POST':
        try:
            payload = json.loads(request.body)
            action = payload.get('action', 'snapshot')

            if action == 'snapshot':
                # Create revision snapshot
                widgets_data = [
                    {
                        'id': w.id,
                        'title': w.title,
                        'visual_type': w.visual_type,
                        'x_axis': w.x_axis,
                        'y_axis': w.y_axis,
                        'aggregation': getattr(w, 'aggregation', 'sum'),
                        'chart_config': getattr(w, 'chart_config', {})
                    }
                    for w in dashboard.widgets.all()
                ]
                v_num = dashboard.revisions.count() + 1
                rev = DashboardRevision.objects.create(
                    dashboard=dashboard,
                    version=v_num,
                    snapshot={'widgets': widgets_data, 'theme': dashboard.theme, 'title': dashboard.title},
                    change_summary=payload.get('change_summary', 'Manual Snapshot'),
                    created_by=request.user if request.user.is_authenticated else None
                )
                return JsonResponse({'status': 'success', 'version': v_num, 'revision_id': rev.id})

            elif action == 'restore':
                rev_id = payload.get('revision_id')
                rev = get_object_or_404(DashboardRevision, pk=rev_id, dashboard=dashboard)
                # Restore widgets
                snapshot = rev.snapshot
                if 'theme' in snapshot:
                    dashboard.theme = snapshot['theme']
                    dashboard.save(update_fields=['theme'])
                return JsonResponse({'status': 'success', 'message': f"Restored to revision v{rev.version}"})
            return JsonResponse({'error': 'Invalid action'}, status=400)
        except Exception as e:
            import logging
            logging.getLogger(__name__).exception("dashboard_revisions_api error: %s", e)
            return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def dashboard_publish_state_api(request, dashboard_id):
    """Manages dashboard lifecycle: draft -> review -> published"""
    dashboard = get_object_or_404(Dashboard, pk=dashboard_id)
    if request.method == 'POST':
        try:
            payload = json.loads(request.body)
            new_status = payload.get('status', 'published')
            if new_status not in ['draft', 'review', 'published']:
                return JsonResponse({'error': 'Invalid status choice'}, status=400)
            dashboard.status = new_status
            dashboard.save(update_fields=['status'])
            return JsonResponse({'status': 'success', 'status_state': new_status})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def two_factor_auth_api(request):
    """Handles TOTP 2FA secret generation and verification"""
    from .services import TwoFactorAuthEngine
    from .models import UserProfile

    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        try:
            payload = json.loads(request.body) if request.body else {}
            action = payload.get('action', 'setup')

            if action == 'setup':
                secret = TwoFactorAuthEngine.generate_base32_secret()
                profile.totp_secret = secret
                profile.save(update_fields=['totp_secret'])
                otp_uri = f"otpauth://totp/ApexBIStudio:{request.user.username}?secret={secret}&issuer=ApexBIStudio"
                return JsonResponse({'status': 'success', 'secret': secret, 'otp_uri': otp_uri})

            elif action == 'verify':
                code = payload.get('code', '')
                if not profile.totp_secret:
                    return JsonResponse({'error': '2FA is not initiated'}, status=400)
                is_valid = TwoFactorAuthEngine.verify_totp_code(profile.totp_secret, code)
                if is_valid:
                    profile.is_totp_enabled = True
                    profile.save(update_fields=['is_totp_enabled'])
                    return JsonResponse({'status': 'success', 'message': '2FA successfully activated!'})
                else:
                    return JsonResponse({'status': 'failed', 'error': 'Invalid 6-digit verification code.'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def lttb_downsample_api(request, widget_id):
    """Downsamples dense visual points using Largest-Triangle-Three-Buckets"""
    widget = get_object_or_404(Widget, pk=widget_id)
    from .services import DatasetEngine, LTTBDownsampler

    try:
        threshold = int(request.GET.get('threshold', 500))
        df = DatasetEngine.load_dataframe(widget.dashboard.dataset)
        if widget.x_axis in df.columns and widget.y_axis in df.columns:
            clean = df[[widget.x_axis, widget.y_axis]].dropna()
            points = [(idx, float(row[widget.y_axis])) for idx, row in clean.iterrows() if pd.api.types.is_numeric_dtype(clean[widget.y_axis])]
            downsampled = LTTBDownsampler.downsample(points, threshold=threshold)
            return JsonResponse({'status': 'success', 'original_count': len(points), 'sampled_count': len(downsampled), 'points': downsampled})
        return JsonResponse({'error': 'Specified visual axis columns not found in dataset'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

def prometheus_metrics_api(request):
    """Exports Prometheus formatted operational metrics"""
    from django.http import HttpResponse
    from django.contrib.auth.models import User
    from .models import Dataset, Dashboard, Widget, KPIAlertRule

    dataset_count = Dataset.objects.count()
    dashboard_count = Dashboard.objects.count()
    widget_count = Widget.objects.count()
    user_count = User.objects.count()
    alert_count = KPIAlertRule.objects.filter(is_active=True).count()

    metrics_text = f"""# HELP apexbi_datasets_total Total number of registered datasets
# TYPE apexbi_datasets_total gauge
apexbi_datasets_total {dataset_count}

# HELP apexbi_dashboards_total Total number of created dashboards
# TYPE apexbi_dashboards_total gauge
apexbi_dashboards_total {dashboard_count}

# HELP apexbi_widgets_total Total number of visual widgets
# TYPE apexbi_widgets_total gauge
apexbi_widgets_total {widget_count}

# HELP apexbi_users_total Total registered users
# TYPE apexbi_users_total gauge
apexbi_users_total {user_count}

# HELP apexbi_active_alerts_total Total active KPI alert rules
# TYPE apexbi_active_alerts_total gauge
apexbi_active_alerts_total {alert_count}
"""
    return HttpResponse(metrics_text, content_type='text/plain; version=0.0.4')


