import random

import names
from django.shortcuts import render
from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response
from django.db.models import Q
from datastore.models import Survey, SurveyObjection, PatientData, CellData
from datastore.permissions import IsSurvey
from datastore.serializers import SurveySerializer, PatientSerializer, ShortSurveySerializer, SurveyObjectionSerializer, \
    CellSerializer, CellSearchSerializer, CellShortSerializer, PatientICFSerializer
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
        serializer.save(owner=self.request.user, data={})

    @action(methods=['get'], detail=False)
    def getshortlist(self,request):
        try:
            users_w_surveys = User.objects.filter(survey__isnull=False)
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
            survey_type=request.GET.get('type','WHODAS_TRAIN')
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
    queryset = PatientData.objects.all()

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
        serializer.save(owner=self.request.user, data={})

    @action(methods=['get'], detail=True)
    def getcompiledicf(self, request, pk=None):
        try:
            icf_item=PatientData.objects.get(id=pk, type='ICF')
            cell_parent = icf_item.cellparent
            input_types = ['CORESETS','WHODAS_SCREEN','WHODAS_CONTEXT']
            input_items = PatientData.objects.filter(cellparent=cell_parent, type__in=input_types)
            serializer = PatientICFSerializer([icf_item,*input_items], many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(data={"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class CellView(viewsets.ModelViewSet):
    serializer_class = CellSerializer
    authentication_classes = [OAuth2Authentication]
    permission_classes = [DjangoModelPermissions]
    queryset = CellData.objects.all()

    def get_queryset(self):
        if (self.action == 'list') | (self.action == 'search'):
            user = self.request.user
            institution = user.institution_link
            showall= user.groups.filter(name='scientist').exists() | user.groups.filter(name='medworker').exists()
            if showall:
                return self.queryset.filter(owner_institution=institution)
            else:
                return self.queryset.filter(Q(sharedwith=user) | Q(owner=user)).distinct()
        else:
            return self.queryset

    def list(self, request, *args, **kwargs):
        date = request.GET.get('date',None)
        status = request.GET.get('status',None)
        sort = request.GET.get('sort','last_modified')
        queryset = self.filter_queryset(self.get_queryset())
        if date is not None:
            queryset = queryset.filter(last_modified__date=date)
        if status is not None:
            queryset = queryset.filter(status=status)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = CellShortSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        queryset = queryset.order_by(sort)
        serializer = CellShortSerializer(queryset, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        # create random name
        firstName = names.get_first_name()
        lastName = names.get_last_name()
        rnumber = str(random.randint(111111,999999))
        serializer.save(owner=self.request.user, cell_content=[], searchfield=firstName+' '+lastName+' '+rnumber)

    @action(methods=['get'], detail=False)
    def search(self, request, pk=None):
        try:
            s = request.GET.get('search',None)
            if s:
                q = self.get_queryset()
                q = q.filter(searchfield__icontains=s)
                #res = [d.searchfield for d in q.all()]
                ser = CellSearchSerializer(q,many=True)
                return Response(ser.data, status=status.HTTP_200_OK)
            return Response(data=[], status=status.HTTP_200_OK)
        except Exception as e:
            return Response(data={"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=True)
    def share(self, request, pk=None):
        try:
            authcode = request.GET.get('authcode',None)
            itemid = request.GET.get('itemid',None)
            authorized = False
            if authcode:
                cp = CellData.objects.get(id=pk)
                    # possible_surveys = Survey.objects.filter(id=itemid).all()
                    # possible_patients = PatientData.objects.filter(id=itemid).all()
                    # cp = [s.cellparent for s in possible_surveys] + [s.cellparent for s in possible_patients]
                    # serializer = CellSerializer(cp, many=True)
                serializer = CellShortSerializer(cp,many=False, context={'request': request})
                u = request.user
                # searchfield validation
                if authcode in cp.searchfield:
                    cp.sharedwith.add(u)
                    cp.save()
                    authorized=True
                if authorized:
                    return Response(serializer.data, status=status.HTTP_200_OK)
                else:
                    return Response(status=status.HTTP_401_UNAUTHORIZED)
            else:
                return Response(status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            return Response(data={"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
