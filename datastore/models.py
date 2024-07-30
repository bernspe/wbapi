import json
import uuid

from django.db import models

from wbapi import settings
from wbapi.settings import ICF_STRUCT_DIR


# Create your models here.

class Survey(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    redirect = models.CharField(max_length=30, null=True, blank=True)
    redirect_id = models.CharField(max_length=50,null=True,blank=True)
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
    redirect_id = models.CharField(max_length=50, null=True, blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='my_patientdata', on_delete=models.SET_NULL, null=True,
                              blank=True)
    cellparent = models.ForeignKey('datastore.CellData', related_name='cell_content', on_delete=models.CASCADE,
                                         null=True, blank=True)
    type = models.CharField(max_length=20,null=True, blank=True)
    data = models.JSONField(null=True, blank=True)
    status = models.SmallIntegerField(default=0)
    # status values 0: Wartet, 1-9: Aktiv, 10: Finished
    REQUIRED_FIELDS = []

    def makeICF(self):
        result = {}
        if self.type == 'ICF':
            if 'ICF_Selection' in self.data.keys():
                da = self.data['ICF_Selection'].split(',')
                if len(da) > 0:
                    result = result | {k: '' for k in da}
            if ('Start' in self.data.keys()) | ('ICF_Base' in self.data.keys()):
                if 'Start' in self.data.keys():
                    da = self.data['Start'].split(';')
                if 'ICF_Base' in self.data.keys():
                    da = self.data['ICF_Base'].split(';')
                if len(da) > 0:
                    result = result | {k.split('.')[0]: k.split('.')[1] for k in da}
        if self.type == 'CORESETS':
            if 'Coresets' in self.data.keys():
                da = self.data['Coresets']
                if len(da) > 0:
                    with open(ICF_STRUCT_DIR + '/coresets.json') as fp:
                        coresets = json.load(fp)
                    if coresets:
                        for cs in da:
                            result = result | {k: '' for k in coresets[cs]['items']}

        if self.type == 'WHODAS_SCREEN':
            if 'WHODAS' in self.data.keys():
                d = self.data['WHODAS']
                if len(d) > 0:
                    da = d.split(',')
                    with open(ICF_STRUCT_DIR + '/whodas12_de.json') as fp:
                        whodas = json.load(fp)
                    if whodas:
                        whodas = list(whodas.values())
                        for idx, x in enumerate(da):
                            if int(x) > 0:
                                icf_list = whodas[idx]['l'].split(',')
                                result = result | {k: x for k in icf_list}

        if self.type == 'WHODAS_CONTEXT':
            if 'ENV' in self.data.keys():
                d = self.data['ENV']
                if len(d) > 0:
                    da = d.split(',')
                    with open(ICF_STRUCT_DIR + '/env_factors_de.json') as fp:
                        env = json.load(fp)
                    if env:
                        env = list(env.values())
                        for idx, x in enumerate(da):
                            if int(x) != 4:
                                icf_list = env[idx]['l'].split(',')
                                result = result | {k: x for k in icf_list}
        return result


DATA_HANDLING_CHOICES =(
    ("SEPARATE","SEPARATE"),
    ("MERGE","MERGE"),
)
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
    data_handling = models.CharField(max_length=10,choices=DATA_HANDLING_CHOICES, default="SEPARATE")
    icf_store = models.JSONField(null=True, blank=True)
    status = models.CharField(max_length=10, default='open')
    data = models.JSONField(null=True, blank=True)

    REQUIRED_FIELDS = []
