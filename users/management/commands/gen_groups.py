"""
Create permission groups
Create permissions (read only) to models for a set of groups
"""
import logging

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission

grouppermdict= {
    'testuser': [
        'datastore.add_survey',
        'datastore.change_survey',
        'datastore.delete_survey',
        'datastore.view_survey',
        'datastore.add_patientdata',
        'datastore.change_patientdata',
        'datastore.delete_patientdata',
        'datastore.view_patientdata',
        'auth.view_permission',
        'oauth2_provider.add_accesstoken',
        'oauth2_provider.delete_accesstoken',
        'oauth2_provider.view_accesstoken',
        'users.change_user',
        'users.delete_user',
        'users.view_user'
    ],
    'survey': [
        'datastore.add_survey',
        'datastore.change_survey',
        'datastore.delete_survey',
        'datastore.view_survey',
        'auth.view_permission',
        'oauth2_provider.add_accesstoken',
        'oauth2_provider.delete_accesstoken',
        'oauth2_provider.view_accesstoken',
        'users.change_user',
        'users.delete_user',
        'users.view_user'
    ],
    'patient': [
        'datastore.add_patientdata',
        'datastore.change_patientdata',
        'datastore.delete_patientdata',
        'datastore.view_patientdata',
        'auth.view_permission',
        'oauth2_provider.add_accesstoken',
        'oauth2_provider.delete_accesstoken',
        'oauth2_provider.view_accesstoken',
        'users.change_user',
        'users.delete_user',
        'users.view_user'
    ],
    'scientist': [
        'datastore.view_survey',
        'datastore.view_patientdata',
        'auth.view_permission',
        'oauth2_provider.add_accesstoken',
        'oauth2_provider.delete_accesstoken',
        'oauth2_provider.view_accesstoken',
        'users.change_user',
        'users.delete_user',
        'users.view_user'
    ],
    'medworker': [
        'datastore.view_survey',
        'datastore.view_patientdata',
        'users.view_user',
        'auth.view_permission',
        'oauth2_provider.add_accesstoken',
        'oauth2_provider.delete_accesstoken',
        'oauth2_provider.view_accesstoken',
        'users.change_user',
        'users.delete_user',
        'users.view_user'
    ]

}

class Command(BaseCommand):
    help = 'Creates read only default permission groups for users'

    def handle(self, *args, **options):
        for k,v in grouppermdict.items():
            new_group, created = Group.objects.get_or_create(name=k)
            for permission in v:
                app_label=permission.split('.')[0]
                model_name=permission.rsplit('_')[-1]
                permstring=permission.split('.')[1]
                print('Getting Content Type for app {} and model {} with permstring {}'.format(app_label,model_name,permstring))
                content_type = ContentType.objects.get(app_label=app_label, model=model_name)
                print("Creating {}".format(permission))
                try:
                    model_add_perm = Permission.objects.get(codename=permstring, content_type=content_type)
                except Permission.DoesNotExist:
                    logging.warning("**** Permission not found with name '{}'.".format(permission))
                    continue

                new_group.permissions.add(model_add_perm)

        print("Created default group and permissions.")