from django.shortcuts import render
from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from django.db.models import Q
from datastore.models import Survey, SurveyObjection
from datastore.permissions import IsSurvey
from datastore.serializers import SurveySerializer, PatientSerializer, ShortSurveySerializer, SurveyObjectionSerializer
from users.models import User


# Create your views here.



class SurveyView(viewsets.ModelViewSet):
    serializer_class = SurveySerializer
    authentication_classes = [OAuth2Authentication]
    permission_classes = [DjangoModelPermissions]
    queryset = Survey.objects.all()

    def get_queryset(self):
        return self.queryset

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(methods=['get'], detail=False)
    def getshortlist(self,request):
        try:
            users_w_surveys = User.objects.filter(survey__isnull=False, avatar__isnull=False)
            surveylist1 = [u.survey.order_by('score').last().id for u in users_w_surveys]
            surveylist2 = Survey.objects.filter(id__in=surveylist1, score__gt=0).order_by('score')
            serializer = ShortSurveySerializer(surveylist2, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(data={"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=False)
    def getlast(self,request):
        try:
            user = request.user
            survey_type=request.GET.get('type','WHODAS_ICF')
            survey = Survey.objects.filter(owner=user, type=survey_type).order_by('created').last()
            serializer = SurveySerializer(survey, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(data={"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['post'], detail=True)
    def makeobjection(self,request, pk=None):
        try:
            if pk is not None:
                survey = Survey.objects.get(id=pk)
                data = request.data['data']
                so = SurveyObjection.objects.create(related_survey=survey, data=data)
                serializer = SurveyObjectionSerializer(so, many=False)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(data={}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(data={"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PatientView(viewsets.ModelViewSet):
    serializer_class = PatientSerializer
    authentication_classes = [OAuth2Authentication]
    permission_classes = [DjangoModelPermissions]
    queryset = Survey.objects.all()

    def get_queryset(self):
        if self.action == 'list':
            user = self.request.user
            showall= user.groups.filter(name='scientist').exists() | user.groups.filter(name='medworker').exists() | user.is_staff
            if showall:
                return self.queryset.all()
            else:
                return self.queryset.filter(owner=user)
        else:
            return self.queryset

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)