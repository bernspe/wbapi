import uuid
from datetime import date

from django.contrib.auth.models import Group
from django.db.models import BooleanField
from rest_framework import serializers

from datastore.models import Survey, PatientData
from users.models import User, Institution

class InstitutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Institution
        fields = '__all__'

class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ('name',)


class UserSerializer(serializers.ModelSerializer):
    groups = GroupSerializer(many=True)
    institution_link = InstitutionSerializer(many=False)
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


class ICFDataUserSerializer(serializers.ModelSerializer):
    groups = GroupSerializer(many=True)
    class Meta:
        model=User
        fields = ('first_name','last_name','avatar','groups')

class StaffUserSerializer(serializers.ModelSerializer):
    groups = GroupSerializer(many=True)

    class Meta:
        model = User
        fields = '__all__'


class RegisterSerializer(serializers.ModelSerializer):

    def update(self, instance, validated_data):
        validated_data.pop('password',None)
        instance.save()
        return instance

    def validate(self, data):
        try:
            email = data.get('email')
            if email:
                data.update({'email': email.lower()})
            username=data.get('username')
            if not username:
                if not email:
                    raise serializers.ValidationError(("Neither username nor email provided"))
                username = str(uuid.uuid4())
                data.update({'username': username})
            user = User.objects.filter(username=username)
            email = User.objects.filter(email=email)
            if (len(user) > 0) | (len(email) > 0):
                raise serializers.ValidationError(("Username or email already exists"))
        except User.DoesNotExist:
            pass
        return data

    def create(self, validated_data, instance=None):
        """
        Jeder neu angemeldete Benutzer wird automatisch der Patient-Gruppe zugeordnet
        """
        user = User.objects.create(**validated_data)
        user.set_password(validated_data['password'])
        user.groups.add(Group.objects.get(name__exact='patient'))
        user.save()
        return user

    class Meta:
        model = User
        fields = '__all__'


class ChangePasswordSerializer(serializers.Serializer):
    model = User

    """
    Serializer for password change endpoint.
    """
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

class ForgotPasswordSerializer(serializers.ModelSerializer):
    def update(self, instance, validated_data):
        instance.set_password(validated_data['password'])
        instance.is_emailvalidated=True
        instance.emailtoken=''
        instance.save()
        return instance

    def validate(self, data):
        token = data.get('emailtoken')
        user = User.objects.filter(username=data.get('username'), emailtoken=token)
        if (len(user)==0):
            raise serializers.ValidationError({"emailtoken": "Emailtoken do not match or user does not exist"})
        return data

    class Meta:
        model = User
        fields = ('username','password','emailtoken','is_emailvalidated')





