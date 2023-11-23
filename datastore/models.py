import uuid

from django.db import models

from wbapi import settings

# Create your models here.

class Survey(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='survey', on_delete=models.CASCADE, null=True,
                              blank=True)
    type = models.CharField(max_length=12,null=True, blank=True)
    data = models.JSONField(null=True, blank=True)
    score = models.SmallIntegerField(default=0)

class SurveyObjection(models.Model):
    related_survey = models.ForeignKey(Survey,related_name='objection', on_delete=models.CASCADE, null=True, blank=True)
    data = models.JSONField(null=True, blank=True)


class PatientData(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='patientdata', on_delete=models.CASCADE, null=True,
                              blank=True)
    type = models.CharField(max_length=12,null=True, blank=True)
    data = models.JSONField(null=True, blank=True)