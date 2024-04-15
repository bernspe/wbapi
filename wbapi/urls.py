
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from datastore.views import SurveyView, CellView, PatientView
from users.views import UserRegister, check_token, UserViewSet, InstitutionViewSet, TokenView
from wbapi import settings

router = DefaultRouter()
router.register(r'surveys', SurveyView, 'survey')
router.register(r'patients',PatientView)
router.register(r'cells', CellView)
router.register(r'users', UserViewSet)
router.register(r'institution',InstitutionViewSet)

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path('', include(router.urls)),
    path('userinfo/', check_token),
    path('o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    path('o/emailtoken/', TokenView.as_view()),
    path('register/', UserRegister.as_view()),
]
