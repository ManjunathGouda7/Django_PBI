import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.utils.http import url_has_allowed_host_and_scheme
from django.http import HttpResponse
from .models import Dashboard, Dataset, UserProfile

logger = logging.getLogger(__name__)

@login_required(login_url='/login/')
def index_view(request):
    """
    Main Power BI Studio single page application shell (Requires Authentication).
    """
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    role = profile.role if profile else 'admin'
    return render(request, 'analytics/index.html', {
        'user_role': role,
        'user_role_display': profile.get_role_display() if profile else 'Administrator'
    })

def login_view(request):
    """
    Handles secure user login and registration stored in DB.
    Validates redirect targets to prevent Open Redirect vulnerabilities.
    """
    if request.user.is_authenticated:
        return redirect('analytics:index')

    error_msg = None
    success_msg = None

    if request.method == 'POST':
        action = request.POST.get('action', 'login')
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        email = request.POST.get('email', '').strip()
        role = request.POST.get('role', 'admin').strip()

        if action == 'register':
            if not username or not password:
                error_msg = "Username and password are required."
            elif password != confirm_password:
                error_msg = "Passwords do not match. Please re-enter your passwords."
            elif User.objects.filter(username=username).exists():
                error_msg = f"Username '{username}' is already taken. Please choose another."
            else:
                user = User.objects.create_user(username=username, password=password, email=email)
                UserProfile.objects.create(user=user, role=role)
                login(request, user)
                logger.info(f"New user registered and logged in: {username}")
                return redirect('analytics:index')

        elif action == 'login':
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                logger.info(f"User authenticated successfully: {username}")
                next_url = request.GET.get('next', '/')
                if not url_has_allowed_host_and_scheme(url=next_url, allowed_hosts={request.get_host()}):
                    next_url = '/'
                return redirect(next_url)
            else:
                logger.warning(f"Failed login attempt for username: {username}")
                error_msg = "Invalid username or password. Please check your credentials."

    return render(request, 'analytics/login.html', {
        'error_msg': error_msg,
        'success_msg': success_msg
    })

def logout_view(request):
    """
    Logs out user and redirects to login portal.
    """
    if request.user.is_authenticated:
        logger.info(f"User logged out: {request.user.username}")
    logout(request)
    return redirect('analytics:login')

def export_dashboard_view(request, dashboard_id):
    """
    Printable export template for a dashboard.
    """
    dashboard = get_object_or_404(Dashboard, pk=dashboard_id)
    return render(request, 'analytics/export_pdf.html', {'dashboard': dashboard})

def favicon_view(request):
    """
    Returns Power BI chart SVG favicon to eliminate /favicon.ico 404 logs.
    """
    svg_icon = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" rx="20" fill="#00A4EF"/><path d="M25 75V45h15v30H25zm22 0V25h15v50H47zm22 0V35h15v40H69z" fill="#ffffff"/></svg>'
    return HttpResponse(svg_icon, content_type="image/svg+xml")

def export_csv_view(request, dataset_id):
    """
    Downloads active dataset telemetry records as a CSV file.
    """
    dataset = get_object_or_404(Dataset, pk=dataset_id)
    from .services import DatasetEngine
    df = DatasetEngine.load_dataframe(dataset)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{dataset.name}_telemetry.csv"'
    df.to_csv(path_or_buf=response, index=False)
    return response

def export_excel_view(request, dataset_id):
    """
    Downloads multi-sheet formatted Excel workbook (.xlsx).
    """
    dataset = get_object_or_404(Dataset, pk=dataset_id)
    from .analytics_advanced import ExcelExporter
    return ExcelExporter.generate_excel_workbook(dataset)

