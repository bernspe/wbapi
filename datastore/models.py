import uuid

from django.db import models

from wbapi import settings

# Create your models here.

class Survey(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    redirect = models.CharField(max_length=30, null=True, blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='my_survey', on_delete=models.SET_NULL, null=True,
                              blank=True)
    cellparent = models.ForeignKey('datastore.CellData', related_name='surveydata', on_delete=models.SET_NULL,
                                         null=True, blank=True)
    type = models.CharField(max_length=20,null=True, blank=True)
    data = models.JSONField(null=True, blank=True)
    status = models.SmallIntegerField(default=0)
    # status values 0: Wartet, 1-9: Aktiv, 10: Finished
    score = models.SmallIntegerField(default=0)
    REQUIRED_FIELDS = []

class SurveyObjection(models.Model):
    related_survey = models.ForeignKey(Survey,related_name='objection', on_delete=models.CASCADE, null=True, blank=True)
    data = models.JSONField(null=True, blank=True)


class PatientData(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    redirect = models.CharField(max_length=30,null=True, blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='my_patientdata', on_delete=models.SET_NULL, null=True,
                              blank=True)
    cellparent = models.ForeignKey('datastore.CellData', related_name='cell_content', on_delete=models.CASCADE,
                                         null=True, blank=True)
    type = models.CharField(max_length=20,null=True, blank=True)
    data = models.JSONField(null=True, blank=True)
    status = models.SmallIntegerField(default=0)
    # status values 0: Wartet, 1-9: Aktiv, 10: Finished
    REQUIRED_FIELDS = []

class CellData(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='my_celldata', on_delete=models.SET_NULL, null=True,
                              blank=True)
    sharedwith = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='celldata', null=True, blank=True)
    owner_institution = models.ForeignKey('users.Institution', related_name='celldata', on_delete=models.SET_NULL,
                                         null=True, blank=True)
    searchfield = models.CharField(max_length=128,null=True, blank=True)
    icf_store = models.JSONField(null=True, blank=True)
    status = models.CharField(max_length=10, default='open')
    data = models.JSONField(null=True, blank=True)

    REQUIRED_FIELDS = []
