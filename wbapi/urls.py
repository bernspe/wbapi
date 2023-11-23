"""
URL configuration for wbapi project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from datastore.views import SurveyView
from users.views import UserRegister, check_token, get_login_requirements, UserViewSet

router = DefaultRouter()
router.register(r'surveys', SurveyView, 'survey')
router.register(r'users', UserViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path("admin/", admin.site.urls),
    path('loginrequirements/',get_login_requirements),
    path('userinfo/', check_token),
    path('o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    path('register/', UserRegister.as_view()),
    path('datastore/', include(router.urls))
]
