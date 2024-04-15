import datetime
# Create your models here.
import os
import uuid

from django.contrib.auth.models import AbstractUser
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.utils.translation import gettext_lazy as _

from wbapi import settings
from wbapi.settings import DEFAULT_EXPIRY


def get_default_expiry():
    return datetime.datetime.now(datetime.timezone.utc) +  datetime.timedelta(days=DEFAULT_EXPIRY)

class OverwriteStorage(FileSystemStorage):
    def get_available_name(self, name, max_length=None):
        # If the filename already exists, remove it as if it was a true file system
        if self.exists(name):
            os.remove(os.path.join(settings.MEDIA_ROOT, name))
        return name

# Create your models here.
class User(AbstractUser):
    AGE_GROUP_CHOICES = [
        ("AG0","?"),
        ("AG1","<12"),
        ("AG2","12-17"),
        ("AG3","18-25"),
        ("AG4","26-35"),
        ("AG5","36-50"),
        ("AG6","51-70"),
        ("AG7",">70")
    ]
    PASSWORD_REQUIREMENTS = [
        ('survey','none'),
        ('patient','date_of_birth'),
        ('scientist','password'),
        ('medworker','password')
    ]
    date_of_birth = models.DateField(_('date of birth'), null=True, blank=True)
    age_group = models.CharField(max_length=3, choices=AGE_GROUP_CHOICES,default="AG0")
    sex = models.CharField(_('sex'), max_length=10, null=True, blank=True)
    username = models.CharField(_('username'), max_length=100, unique=True, primary_key=True, default=str(uuid.uuid4()))
    date_joined = models.DateTimeField(_('date joined'), auto_now_add=True)
    last_login = models.DateTimeField(_('last login'), null=True, blank=True)

    institution_link = models.ForeignKey('Institution', related_name='employee', on_delete=models.CASCADE, null=True,
                                         blank=True)
    allows_payment_data = models.BooleanField(default=False)
    emailtoken = models.CharField(_('email token'), max_length=6, blank=True)
    is_emailvalidated = models.BooleanField(default=False)
    additional_flags = models.JSONField(blank=True, null=True)
    avatar = models.JSONField(null=True, blank=True)
    avatar_img = models.ImageField(upload_to='avatars/', null=True, blank=True, storage=OverwriteStorage)
    geolocation = models.JSONField(null=True, blank=True)

    REQUIRED_FIELDS = []


class Institution(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    expires = models.DateTimeField(default=get_default_expiry())
    name = models.CharField(_('name'), max_length=100, unique=True, blank=False, null=False)
    logo_url = models.URLField(max_length=200, blank=True, null=True)
    codename = models.CharField(_('codename'), max_length=100, unique=True, blank=True, null=True) # erlaubt das automatische Anmelden in der Institution für Benutzer, die dieses Suffix in ihrer eMail tragen
    data = models.JSONField(null=True, blank=True)

    def has_expired(self):
        present = datetime.datetime.now().replace(tzinfo=datetime.timezone.utc)
        return present > self.expires