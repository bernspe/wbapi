import io
import json
import re
from datetime import datetime, timezone
from PIL import Image
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.files import File
from django.core.files.base import ContentFile

from django.db import transaction
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from oauth2_provider.settings import oauth2_settings
from oauth2_provider.views.mixins import OAuthLibMixin
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import api_view, action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from oauth2_provider.models import AccessToken, RefreshToken

from geodata.funcs import import_geo_files, get_city_from_geolocation
from users.models import User
from users.permissions import IsOwner, IsStaff
from users.serializers import RegisterSerializer, UserSerializer, StaffUserSerializer
from wbapi import settings
from wbapi.settings import geolocation_df, BASE_DIR


def hasExpired(expiry):
    present = datetime.now().replace(tzinfo=timezone.utc)
    return present > expiry
# Create your views here.


class UserViewSet(viewsets.ModelViewSet):
    """
    A viewset for viewing and editing user instances.
    """
    queryset = User.objects.all()
    authentication_classes = [OAuth2Authentication]

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action == 'list':
            permission_classes = [permissions.IsAdminUser]
        else:
            permission_classes = [IsAuthenticated, IsOwner | IsStaff]
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.request.user.is_staff | self.request.user.is_superuser:
            return StaffUserSerializer
        return UserSerializer

    def partial_update(self, request, pk=None, **kwargs):
        user=User.objects.get(username=pk)
        serializer = self.get_serializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    serializer.save()
                    if 'geolocation' in request.data.keys():
                        d = request.data['geolocation']
                        lon = d['longitude']
                        lat = d['latitude']
                        ort,plz=get_city_from_geolocation(BASE_DIR,lon,lat,geolocation_df=geolocation_df)
                        user.geolocation={**d, 'ort':ort,'plz':plz}
                        user.save()
                    return Response(serializer.data, status=status.HTTP_200_OK)
            except Exception as e:
                return Response(data={"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None, **kwargs):
        queryset = User.objects.all()
        user = get_object_or_404(queryset, pk=pk)
        if request.user == user:
            serializer = UserSerializer(user)
        elif request.user.is_staff | request.user.is_admin:
            serializer = StaffUserSerializer(user)
        else:
            serializer = UserSerializer(user)
        return Response(serializer.data)

    @action(methods=['post'],detail=True)
    def setgroup(self,request, pk=None):
        try:
            user=User.objects.get(username=pk)
            g_name = request.data.get('group')
            if (g_name=='patient') | (g_name=='survey'):
                g = Group.objects.get(name=g_name)
                user.groups.clear()
                user.groups.add(g)
                ga = user.groups.all()
                return Response(data={"groups": [x.name for x in ga]}, status=status.HTTP_200_OK)
            else:
                return Response(data={"error": "wrong group spec"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(data={"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['post'], detail=True)
    def updateavatar(self, request, pk=None):
        try:
            user=User.objects.get(username=pk)
            avatarFile = request.FILES.get('avatar')
            im = Image.open(avatarFile)  # Catch original
            source_image = im.convert('RGB')
            source_image.thumbnail((250, 250), Image.ANTIALIAS)  # Resize to size
            output = io.BytesIO()
            source_image.save(output, format='JPEG')  # Save resize image to bytes
            output.seek(0)
            content_file = ContentFile(output.read())  # Read output and create ContentFile in memory
            file = File(content_file)
            random_name = pk+'_avatar.jpeg'
            user.avatar_img.save(random_name, file, save=True)
        except Exception as e:
            return Response(data={"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(data={"avatar":str(user.avatar)}, status=status.HTTP_200_OK)


class UserRegister(OAuthLibMixin, APIView): ##CsrfExemptMixin,
    """
    Registering Users at OAuth Server
    """
    permission_classes = (permissions.AllowAny,)
    server_class = oauth2_settings.OAUTH2_SERVER_CLASS
    validator_class = oauth2_settings.OAUTH2_VALIDATOR_CLASS
    oauthlib_backend_class = oauth2_settings.OAUTH2_BACKEND_CLASS

    def post(self, request):
        data = request.data
        data = data.dict()
        serializer = RegisterSerializer(data=data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    user = serializer.save()
                    if not ('username' in request.data.keys()):
                        request.POST._mutable = True
                        request.POST['username']=user.username
                    if 'testuser' in request.data.keys():
                        g = Group.objects.get(name='testuser')
                        user.groups.add(g)
                        user.save()
                    url, headers, body, token_status = self.create_token_response(request)
                    jbody=json.loads(body)
                    if token_status != 200:
                       raise Exception(jbody.get("error", ""))
                    return Response({**jbody, 'username': user.username}, status=token_status)
            except Exception as e:
                return Response(data={"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@csrf_exempt
@api_view(['GET'])
def get_login_requirements(request, format=None):
    """
    retrieves the necessary login credentials for specific username
    :param username
    :param format:
    :return: password requirements
    """
    username = request.GET.get('username')
    try:
        user=User.objects.get(username=username)
        gnames=[g.name for g in user.groups.all()]
        requirement='none'
        for req in user.PASSWORD_REQUIREMENTS:
            if req[0] in gnames:
                requirement=req[1]
        return Response(data={'credentials': requirement})
    except Exception as e:
        return Response(data={"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['GET'])
def check_token(request, format=None):
    """
    Retrieves User Profile from registered token
    :param Bearer token in Header is sufficient
    :param format:
    :return: User object
    """
    app_tk = request.META["HTTP_AUTHORIZATION"]
    m = re.search('(Bearer)(\s)(.*)', app_tk)

    app_tk = m.group(3)
    try:
        # search oauth2 token db to find user
        acc_tk = AccessToken.objects.get(token=app_tk)
        if hasExpired(acc_tk.expires):
            return Response({'error': 'Token has expired. Please log in again.'}, status=status.HTTP_400_BAD_REQUEST)
    except:
        return Response({'error': 'User not found.'}, status=status.HTTP_400_BAD_REQUEST)
    user = acc_tk.user
    user.last_login=datetime.now(timezone.utc)
    user.save()
    serializer = UserSerializer(user)
    return Response(serializer.data, status=status.HTTP_200_OK)

