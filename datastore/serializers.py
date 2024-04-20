from rest_framework import serializers

from datastore.models import Survey, SurveyObjection, CellData, PatientData
from users.serializers import ShortUserSerializer


def check_survey(survey):
    """
    Checks the survey
    :param survey: the Whodas survey {"1":{'d415':{'belongs': True, 'selected': False, 'deselected': True},...}}
    :return: number of total items, number of correct items, dict with erroneous items: {'1':['d415'...],..}
    """
    all_count=0
    hit_count=0
    error_dict={}
    for num,cont in survey.items():
        try:
            a = []
            for k,v in cont.items():
               if (any(v.values())) & (v['belongs'] == v['selected']):  # check if any value was selected and if the selection status equals the belong status
                   all_count += 1
                   hit_count += 1
               else:
                  all_count += 1
                  a.append(k)
            error_dict[num] = a
        except Exception as e:
            print('Failed silently, because ',e)

    return all_count, hit_count, error_dict

class SurveySerializer(serializers.ModelSerializer):
    class Meta:
        model = Survey
        fields = '__all__'

    def validate(self, data):
        if data['type']=='WHODAS_TRAIN':
            if 'data' in data.keys():
                d=data['data']
                if d is None:
                    return data
                if len(d)>0:
                    all_count, hit_count, error_dict = check_survey(d)
                    data['score']=int(hit_count/all_count*100)
                    data['data']={**d, 'error_dict': error_dict}
                    instance = getattr(self, 'instance', None)
                    if instance is not None:
                        instance.score = data['score']
                        instance.data = data['data']
                        instance.save()
                else:
                    return data
        return data

    def create(self, validated_data):
        cr = Survey.objects.create(**validated_data)
        cr.save()
        return cr

class SurveySerializerWOData(serializers.ModelSerializer):
    class Meta:
        model = Survey
        exclude = ['data']

class ShortSurveySerializer(serializers.ModelSerializer):
    shortuser = serializers.SerializerMethodField('getshortuser')
    class Meta:
        model = Survey
        fields = ['id','created','owner','shortuser','score']

    def getshortuser(self, survey):
        user=survey.owner
        if user:
            serializer = ShortUserSerializer(user, many=False)
            return serializer.data
        else:
            return None


class SurveyObjectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveyObjection
        fields = '__all__'

class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientData
        fields = '__all__'

class CellSerializer(serializers.ModelSerializer):
    cell_content = serializers.SerializerMethodField('get_cell_content')
    cell_survey = serializers.SerializerMethodField('get_cell_survey')
    class Meta:
        model = CellData
        fields = '__all__'

    def get_cell_content(self, celldata):
        c = celldata.cell_content.all()
        if c:
            serializer = PatientSerializer(c, many=True)
            return serializer.data
        else:
            return None

    def get_cell_survey(self, celldata):
        c = celldata.surveydata.all()
        if c:
            serializer = SurveySerializerWOData(c, many=True)
            return serializer.data
        else:
            return None


class CellSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = CellData
        fields = ['id','searchfield']