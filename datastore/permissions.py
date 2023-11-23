from django.contrib.auth.models import Group
from rest_framework import permissions


class IsSurvey(permissions.BasePermission):
    def has_permission(self, request, view):
        g = Group.objects.get(name='survey')
        u=request.user
        return g in u.groups.all()