import datetime
# Create your models here.
import os
import uuid

from django.contrib.auth.models import AbstractUser
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.utils.translation import gettext_lazy as _

from wbapi import settings
from wbapi.settings import DEFAULT_EXPIRY, EMAIL_HOST_USER, EMAIL_HOST, EMAIL_HOST_PASSWORD, DKIM_PRIVATE_KEY_FILE, \
    DKIM_SELECTOR, EMAIL_FROM

import htmlmin
from django.contrib.auth.models import AbstractUser

import smtplib
import dkim
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def get_default_expiry():
    return datetime.datetime.now(datetime.timezone.utc) +  datetime.timedelta(days=DEFAULT_EXPIRY)

class OverwriteStorage(FileSystemStorage):
    def get_available_name(self, name, max_length=None):
        # If the filename already exists, remove it as if it was a true file system
        if self.exists(name):
            os.remove(os.path.join(settings.MEDIA_ROOT, name))
        return name


def send_email(
    to_email,
    sender_email,
    subject,
    message_html,
    dkim_private_key_path=DKIM_PRIVATE_KEY_FILE,
    dkim_selector=DKIM_SELECTOR,
):

    # the `email` library assumes it is working with string objects.
    # the `dkim` library assumes it is working with byte objects.
    # this function performs the acrobatics to make them both happy.
    message_text='Diese Email kann nur als HTML angezeigt werden. Bitte aktivieren Sie HTML in den EMail-Einstellungen.'
    if isinstance(message_text, bytes):
        # needed for Python 3.
        message_text = message_text.decode()

    if isinstance(message_html, bytes):
        # needed for Python 3.
        message_html = message_html.decode()

    sender_domain = sender_email.split("@")[-1]

    msg = MIMEMultipart("alternative")
    msg.attach(MIMEText(message_text, "plain"))
    msg.attach(MIMEText(message_html, "html"))
    msg["To"] = to_email
    msg["From"] = sender_email
    msg["Subject"] = subject
    msg_data = msg.as_bytes()

    if dkim_private_key_path and dkim_selector:
        # the dkim library uses regex on byte strings so everything
        # needs to be encoded from strings to bytes.
        with open(dkim_private_key_path) as fh:
            dkim_private_key = fh.read()
        headers = [b"To", b"From", b"Subject"]
        sig = dkim.sign(
            message=msg_data,
            selector=str(dkim_selector).encode(),
            domain=sender_domain.encode(),
            privkey=dkim_private_key.encode(),
            include_headers=headers,
        )
        # add the dkim signature to the email message headers.
        # decode the signature back to string_type because later on
        # the call to msg.as_string() performs it's own bytes encoding...
        msg["DKIM-Signature"] = sig[len("DKIM-Signature: ") :].decode()
        msg_data = msg.as_bytes()

    with smtplib.SMTP_SSL(EMAIL_HOST) as s:
        s.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
        s.sendmail(sender_email, [to_email], msg_data)
        s.quit()
    return msg

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

    def email_user(self, subject, message, to_email, from_email=EMAIL_FROM, **kwargs):
        '''
        Sends an email to this User.
        '''
        msg_minified=htmlmin.minify(message)
        email = to_email or self.email
        send_email(email,from_email,subject,msg_minified)

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