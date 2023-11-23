from rest_framework import serializers

from datastore.models import Survey, SurveyObjection
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
               if v['belongs'] == v['selected']:
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
        if data['type']=='WHODAS_ICF':
            d=data['data']
            if len(d)>0:
                all_count, hit_count, error_dict = check_survey(d)
                data['score']=int(hit_count/all_count*100)
                data['data']={**d, 'error_dict': error_dict}
            else:
                raise serializers.ValidationError("No Whodas Data sent")
        return data

    def create(self, validated_data):
        cr = Survey.objects.create(**validated_data)
        cr.save()
        return cr


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
        model = Survey
        fields = '__all__'