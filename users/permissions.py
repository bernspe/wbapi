from django.contrib.auth.models import Group
from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.username == request.user.username


class IsStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        g = Group.objects.get(name='Staff')
        u=request.user
        return g in u.groups.all()

