import io
import json
import re
from datetime import datetime, timezone, timedelta
import random

from PIL import Image
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.files import File
from django.core.files.base import ContentFile

from django.db import transaction
from django.shortcuts import render
from django.template.loader import get_template
from django.views.decorators.csrf import csrf_exempt
from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from oauth2_provider.settings import oauth2_settings
from oauth2_provider.views.mixins import OAuthLibMixin
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.generics import get_object_or_404, UpdateAPIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from oauth2_provider.models import AccessToken, RefreshToken
from oauth2_provider.oauth2_validators import Application
from oauth2_provider.views import TokenView as TV
from users.models import User, Institution
from users.permissions import IsOwner, IsStaff, IsMyInstitution, IsVerwaltung
from users.serializers import RegisterSerializer, UserSerializer, StaffUserSerializer, ForgotPasswordSerializer, \
    ChangePasswordSerializer, InstitutionSerializer


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
            permission_classes = [IsAuthenticated, IsOwner]
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
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
                        #ort,plz=get_city_from_geolocation(BASE_DIR,lon,lat,geolocation_df=geolocation_df)
                        #user.geolocation={**d, 'ort':ort,'plz':plz}
                        user.geolocation = {**d}
                        user.save()
                    return Response(serializer.data, status=status.HTTP_200_OK)
            except Exception as e:
                return Response(data={"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None, **kwargs):
        queryset = User.objects.all()
        user = get_object_or_404(queryset, pk=pk)
        serializer = self.get_serializer(user)
        return Response(serializer.data)


    @action(methods=['post'], detail=True)
    @permission_classes([IsAuthenticated])
    def set_new_email(self, request, pk=None):
        """
        Set new EMail after checking token
        :param
        :return: user object
        """
        data = request.data
        emailtoken = data['emailtoken']
        email=data['email']
        if len(emailtoken) > 0:
            try:
                user = User.objects.get(username=pk, emailtoken=emailtoken)
                # check if email already exists
                email_try = User.objects.filter(email=email)
                if len(email_try)>0:
                    return Response({'error': 'Email already in use'},
                                    status=status.HTTP_400_BAD_REQUEST)
                serializer = UserSerializer(user, data=data, partial=True)
                if serializer.is_valid():
                    with transaction.atomic():
                        serializer.save(is_emailvalidated=True)
                        return Response(data={'new_email': email}, status=status.HTTP_200_OK)
                else:
                    return Response({'error': 'User not found or Emailtoken not valid'},
                                    status=status.HTTP_400_BAD_REQUEST)
            except:
                return Response({'error': 'User not found or Emailtoken not valid'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'error': 'No email or emailtoken provided'}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=True)
    @permission_classes([IsAuthenticated])
    def email_user(self, request, pk=None):
        user = User.objects.get(username=pk)
        to_email = request.GET.get('email',None)
        emailtype = request.GET.get('type',None)
        emailfolder = request.GET.get('folder','user')
        add_info = request.GET.get('add_info','')
        if emailtype:
            try:
                t = get_template(emailfolder+'/'+emailtype+'.html')
                ts = str(datetime.now(timezone.utc))
                user.email_user('ICFx Mail: '+emailtype+ '(' + ts+')', t.render(context={
                    'Firstname': user.first_name, 'random': str(random.randint(0, 9)), 'add_info':add_info}),to_email)
                return Response({'username': user.username}, status=status.HTTP_200_OK)
            except Exception as e:
                return Response(data={"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(data={"error": "Email Type not specified"}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=True)
    @permission_classes([IsAuthenticated])
    def email_user_token(self, request, pk=None):
        """
        Send 6-char token via email to user upon request
        :param
        :return: username
        """
        try:
            user = User.objects.get(username=pk)
            serializer = UserSerializer(user, data=request.data,
                                        partial=True)  # set partial=True to update a data partially
            if serializer.is_valid():
                with transaction.atomic():
                    token = user.create_email_token()
                    serializer.save(emailtoken=token, is_emailvalidated=False)
                    t = get_template('user/email-token.html')
                    ts = str(datetime.now(timezone.utc))
                    user.email_user('EMail Token' + ts, t.render(context={
                        'Firstname': user.first_name,
                        'token': token}))
                    return Response({'username': user.username}, status=status.HTTP_200_OK)
            else:
                Response({'error': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)
        except:
            return Response({'error': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)


    @action(methods=['post'],detail=True)
    def setgroup(self,request, pk=None):
        try:
            user = User.objects.get(username=pk)
            g_name = request.data.get('group')
            g_replace = request.data.get('replace')
            g,created = Group.objects.get_or_create(name=g_name)
            if created:
                if g_name=='patient':
                    perms = Permission.objects.filter(group=Group.objects.get(name='patient'))
                elif g_name=='misc':
                    perms = Permission.objects.filter(group=Group.objects.get(name='testuser'))
                else:
                    perms=Permission.objects.filter(group=Group.objects.get(name='medworker'))
                for p in perms:
                    g.permissions.add(p)
            if g_replace:
                user.groups.clear()

            user.groups.add(g)
            ga = user.groups.all()
            return Response(data={"groups": [x.name for x in ga]}, status=status.HTTP_200_OK)
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
                    if 'codename' in request.data.keys():
                        cn = request.POST['codename']
                        if len(cn)>3:
                            institution = Institution.objects.filter(codename=cn)
                            if len(institution) > 0:
                                i = institution.first()
                                user.institution_link = i # den Benutzer der gefundendenen Institution zubuchen
                                user.groups.add(
                                    Group.objects.get(name__exact='medworker'))  # Leserechte vergeben
                                user.groups.remove(Group.objects.get(name__exact='patient'))
                                user.save()
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

class TokenView(TV):
    """
    Get OAuth Access Token from Login with email or refreshToken or username
    """
    def create_token_response(self, request):
        request.POST._mutable = True
        email = request.POST.pop('email', None)
        username = request.POST.pop('username',None)
        print('Requesting user: %s'%username)
        refresh_token = request.POST.pop('refresh_token',None)
        if type(refresh_token)==list:
            refresh_token=refresh_token[0]
        if username:
            user=get_user_model().objects.get(username=username[0])
            request.POST['username'] = username[0]
        if email:
            username = get_user_model().objects.filter(email__iexact=email[0]).values_list('username', flat=True).last() # iexact = case insensitive
            request.POST['username'] = username
        if refresh_token:
            try:
                rt=RefreshToken.objects.get(token__exact=refresh_token)
                user=rt.user
                rt.revoke()
                request.POST['username'] = user.username
                client_id=request.POST.get('client_id')
                application = Application.objects.get(client_id=client_id)
                scope=request.POST.get('scope')
                present = datetime.now().replace(tzinfo=timezone.utc)
                expires = present + timedelta(seconds=oauth2_settings.ACCESS_TOKEN_EXPIRE_SECONDS)
                acc_token=AccessToken.objects.create(user=user, application=application, expires=expires, token=common.generate_token(), scope=scope )
                r_token=RefreshToken.objects.create(user=user, application=application,access_token=acc_token,token=common.generate_token())
                request.POST['refresh_token']=str(r_token)
                #rt.access_token=acc_token
                #rt.save()
                #acc_token.save()
            except Exception as e:
                print(e)
        return super(TokenView, self).create_token_response(request)

class ChangePasswordView(UpdateAPIView):
        """
        An endpoint for changing password.
        """
        serializer_class = ChangePasswordSerializer
        model = User
        permission_classes = (IsAuthenticated,)

        def get_object(self, queryset=None):
            obj = self.request.user
            return obj

        def update(self, request, *args, **kwargs):
            self.object = self.get_object()
            serializer = self.get_serializer(data=request.data)

            if serializer.is_valid():
                # Check old password
                if not self.object.check_password(serializer.data.get("old_password")):
                    return Response({"old_password": ["Wrong password."]}, status=status.HTTP_400_BAD_REQUEST)
                # set_password also hashes the password that the user will get
                self.object.set_password(serializer.data.get("new_password"))
                self.object.save()
                response = {
                    'status': 'success',
                    'code': status.HTTP_200_OK,
                    'message': 'Password updated successfully',
                    'data': []
                }

                return Response(response)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



@csrf_exempt
@api_view(['GET'])
def forgot_password(request):
    """
    Send 6-char token via email to user upon request
    :param
    :return: username
    """
    try:
        email = request.GET.get('email')
        user = get_user_model().objects.get(email__iexact=email)
        serializer = UserSerializer(user, data=request.data, partial=True)  # set partial=True to update a data partially
        if serializer.is_valid():
            with transaction.atomic():
                token = user.create_email_token()
                serializer.save(emailtoken=token,is_emailvalidated=False)
                t = get_template('user/email-forgotpassword.html')
                ts=str(datetime.now(timezone.utc))
                user.email_user('Passwort vergessen. '+ts, t.render(context={
                    'Firstname': user.first_name,
                    'token': token}))
                return Response({'username':user.username}, status=status.HTTP_200_OK)
        else:
            Response({'error': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)
    except:
        return Response({'error':'User not found'},status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['POST'])
def set_new_password(request):
    """
    Set new Password and Refreshes Expiry
    :param
    :return: username
    """
    data=request.data
    username = data['username']
    emailtoken=data['emailtoken']
    if ((len(username)>0) & (len(emailtoken)>0)):
        try:
            user = User.objects.get(username=username, emailtoken=emailtoken)
            serializer=ForgotPasswordSerializer(user, data=data, partial=True)
            if serializer.is_valid():
                with transaction.atomic():
                    serializer.save()
                    return Response(data={'new_password':'OK'},status=status.HTTP_200_OK)
            else:
                return Response({'error': 'User not found or Emailtoken not valid'}, status=status.HTTP_400_BAD_REQUEST)
        except:
            return Response({'error': 'User not found or Emailtoken not valid'}, status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response({'error': 'No Username or emailtoken provided'}, status=status.HTTP_400_BAD_REQUEST)



class InstitutionViewSet(viewsets.ModelViewSet):
    """
    A viewset for viewing and editing institution instances.
    """
    queryset = Institution.objects.all()
    authentication_classes = [OAuth2Authentication]
    serializer_class = InstitutionSerializer

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action == 'list':
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsAuthenticated, IsMyInstitution, IsVerwaltung]
        return [permission() for permission in permission_classes]

    def create(self, request, *args, **kwargs):
        data = request.data
        user = request.user
        serializer = InstitutionSerializer(data=data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    inst = serializer.save()
                    user.institution_link=inst
                    user.save()
                    return Response(serializer.data, status=status.HTTP_200_OK)
            except Exception as e:
                return Response(data={"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None, *args, **kwargs):
        inst=Institution.objects.get(id=pk)
        user = request.user
        serializer = self.get_serializer(inst, data=request.data, partial=True)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    user.institution_link=inst
                    user.save()
                    serializer.save()
                    return Response(serializer.data, status=status.HTTP_200_OK)
            except Exception as e:
                return Response(data={"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=True)
    def checkcodename(self, request, pk=None):
        """
        checkt, ob der gesendete codename zur Institution bereits gehört, oder ob er verfügbar (=unique) ist
        :param request: codename
        :param pk: institution
        :return: 200, wenn o.a. true, ansonsten 400
        """
        try:
            cn = request.GET.get('codename',None)
            inst = Institution.objects.get(id=pk)
            cn_belongs_to_this_institution = inst.codename==cn
            if cn_belongs_to_this_institution:
                return Response(status=status.HTTP_200_OK)
            else:
                i = Institution.objects.filter(codename=cn)
                if len(i)==0:
                    return Response(status=status.HTTP_200_OK)
                else:
                    return Response(status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(data={"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
