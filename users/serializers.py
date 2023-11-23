import uuid
from datetime import date

from django.contrib.auth.models import Group
from django.db.models import BooleanField
from rest_framework import serializers

from datastore.models import Survey, PatientData
from users.models import User


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ('name',)


class UserSerializer(serializers.ModelSerializer):
    groups = GroupSerializer(many=True)
    lastpost = serializers.SerializerMethodField('getlastpost')

    class Meta:
        model = User
        fields = '__all__'

    def getlastpost(self, user):
        if user.groups.filter(name='survey').exists():
            last_survey = Survey.objects.filter(owner=user).last()
            # obtaining serializer wont work due to circular imports
            if last_survey:
                return {'id':last_survey.id, 'type': last_survey.type, 'created':last_survey.created}
        if user.groups.filter(name='patient').exists():
            last_patient_rec = PatientData.objects.filter(owner=user).last()
            if last_patient_rec:
                return {'id':last_patient_rec.id}


class ShortUserSerializer(serializers.ModelSerializer):
    class Meta:
        model=User
        fields = ('age_group','sex','avatar','geolocation')


class StaffUserSerializer(serializers.ModelSerializer):
    groups = GroupSerializer(many=True)

    class Meta:
        model = User
        fields = '__all__'


class RegisterSerializer(serializers.ModelSerializer):
    testuser = BooleanField
    def update(self, instance, validated_data):
        validated_data.pop('password',None)
        instance.save()
        return instance

    def validate(self, data):
        try:
            username=data.get('username')
            if not username:
                username = str(uuid.uuid4())
                data.update({'username': username})
            user = User.objects.filter(username=username)
            if (len(user) > 0):
                raise serializers.ValidationError(("Username or email already exists"))
        except User.DoesNotExist:
            pass
        return data

    def create(self, validated_data, instance=None):
        user = User.objects.create(**validated_data)
        password=validated_data['password']
        user.set_password(password)
        try:
            dob=date.fromisoformat(password) # try to get the date from YYYY-MM-DD
            user.date_of_birth=dob
            g = Group.objects.get(name='patient')
            user.groups.add(g)
        except:
            g = Group.objects.get(name='survey')
            user.groups.add(g)
        user.save()
        return user

    class Meta:
        model = User
        fields = '__all__'

