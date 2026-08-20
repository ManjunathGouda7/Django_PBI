from rest_framework import permissions
from .models import DatasetSharePermission, DashboardShare

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    Read permissions are allowed to any request for public items.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        owner = getattr(obj, 'created_by', getattr(obj, 'owner', None))
        return owner == request.user if owner else True

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Allow admins full access, others read-only.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)

class IsOwnerOrShared(permissions.BasePermission):
    """
    Allow owner full access, shared users permission-based access, and public viewing.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return getattr(obj, 'is_public', False) or getattr(obj, 'is_sample', False)

        owner = getattr(obj, 'created_by', getattr(obj, 'owner', None))
        if owner == request.user or request.user.is_staff:
            return True

        if getattr(obj, 'is_public', False) or getattr(obj, 'is_sample', False):
            if request.method in permissions.SAFE_METHODS:
                return True

        # Check explicit shares
        if hasattr(obj, 'shares'): # DashboardShare
            share = obj.shares.filter(user=request.user).first()
            if not share and request.user.email:
                share = obj.shares.filter(email=request.user.email).first()
            if share:
                if request.method in permissions.SAFE_METHODS:
                    return True
                return share.permission_level in ('edit', 'admin')

        if hasattr(obj, 'share_permissions'): # DatasetSharePermission
            share = obj.share_permissions.filter(user=request.user).first()
            if not share and request.user.email:
                share = obj.share_permissions.filter(email=request.user.email).first()
            if share:
                if request.method in permissions.SAFE_METHODS:
                    return True
                return share.permission_level in ('edit', 'admin')

        return False

class HasExportPermission(permissions.BasePermission):
    """
    Check if the user has permission to export data from a Dataset or Dashboard.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        owner = getattr(obj, 'created_by', getattr(obj, 'owner', None))
        if owner == request.user or request.user.is_staff:
            return True

        # Check explicit share export flags
        if hasattr(obj, 'shares'):
            share = obj.shares.filter(user=request.user).first()
            if not share and request.user.email:
                share = obj.shares.filter(email=request.user.email).first()
            if share:
                return share.can_export

        if hasattr(obj, 'share_permissions'):
            share = obj.share_permissions.filter(user=request.user).first()
            if not share and request.user.email:
                share = obj.share_permissions.filter(email=request.user.email).first()
            if share:
                return share.can_export

        # Public/sample default export allowed if authenticated
        return getattr(obj, 'is_public', False) or getattr(obj, 'is_sample', False)

class CanEditDashboard(permissions.BasePermission):
    """
    Check if user can edit dashboard layout and widgets.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        if obj.created_by == request.user or request.user.is_staff:
            return True

        share = obj.shares.filter(user=request.user).first()
        if not share and request.user.email:
            share = obj.shares.filter(email=request.user.email).first()
        
        return bool(share and share.permission_level in ('edit', 'admin'))