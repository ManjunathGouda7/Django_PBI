import json
import pandas as pd
import numpy as np
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Dataset, Dashboard, Widget, CalculatedMeasure, DatasetColumn, DatasetTag, DatasetSharePermission
from .serializers import DatasetSerializer, DashboardSerializer, WidgetSerializer, UserSerializer
from .permissions import IsOwnerOrReadOnly, IsAdminOrReadOnly
from .services import DatasetEngine

# DRF ViewSets
class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class DatasetViewSet(viewsets.ModelViewSet):
    queryset = Dataset.objects.all().order_by('-created_at')
    serializer_class = DatasetSerializer
    permission_classes = [IsOwnerOrReadOnly]

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

class DashboardViewSet(viewsets.ModelViewSet):
    queryset = Dashboard.objects.all().order_by('-created_at')
    serializer_class = DashboardSerializer
    permission_classes = [IsOwnerOrReadOnly]

class WidgetViewSet(viewsets.ModelViewSet):
    queryset = Widget.objects.all().order_by('-created_at')
    serializer_class = WidgetSerializer
    permission_classes = [IsOwnerOrReadOnly]

# Auth APIs
@csrf_exempt
def auth_register_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        data = json.loads(request.body)
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        email = data.get('email', '').strip()

        if not username or not password:
            return JsonResponse({'error': 'Username and password required'}, status=400)
        if User.objects.filter(username=username).exists():
            return JsonResponse({'error': 'Username already exists'}, status=400)

        user = User.objects.create_user(username=username, password=password, email=email)
        login(request, user)
        return JsonResponse({
            'message': 'Registration successful',
            'user': {'id': user.id, 'username': user.username, 'email': user.email}
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def auth_login_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        data = json.loads(request.body)
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return JsonResponse({
                'message': 'Login successful',
                'user': {'id': user.id, 'username': user.username, 'email': user.email}
            })
        else:
            return JsonResponse({'error': 'Invalid username or password'}, status=401)
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
            theme="powerbi_classic"
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
        if not name or not file_obj:
            return JsonResponse({'error': 'Name and file are required.'}, status=400)

        file_type = 'csv' if file_obj.name.endswith('.csv') else 'excel'
        dataset = Dataset.objects.create(
            name=name,
            file=file_obj,
            file_type=file_type,
            is_sample=False
        )

        try:
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
            dataset.delete()
            return JsonResponse({'error': f'Failed to process file: {str(e)}'}, status=400)

def dataset_detail_api(request, dataset_id):
    dataset = get_object_or_404(Dataset, pk=dataset_id)
    return JsonResponse({
        'id': dataset.id,
        'name': dataset.name,
        'description': dataset.description,
        'row_count': dataset.row_count,
        'file_type': dataset.file_type,
        'column_schema': dataset.column_schema
    })

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
            db.save()
            return JsonResponse({'message': 'Dashboard updated'})
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