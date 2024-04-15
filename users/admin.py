from django.contrib import admin
from django import forms
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.utils.safestring import mark_safe

from users.models import User, Institution


class UserChangeForm(forms.ModelForm):
    """A form for updating users. Includes all the fields on
    the user, but replaces the password field with admin's
    disabled password hash display field.
    """

    password = ReadOnlyPasswordHashField()

    class Meta:
        model = User
        fields = ["email", "password", "date_of_birth",'age_group', "is_active", 'avatar', 'geolocation', "is_staff"]


class UserAdmin(UserAdmin):
    form = UserChangeForm
    list_filter = ['institution_link']
    search_fields = ['last_name','email']
    list_display = ['avatar_thumb','first_name','last_name','email','date_of_birth','date_joined','get_groups','institution','is_staff']
    readonly_fields = ('date_joined','avatar_preview',)
    fieldsets = (
            (None, {'fields': ('username','date_of_birth','age_group','sex', 'avatar_preview','geolocation', 'groups','date_joined')}),
    )

    def get_groups(self, obj):
        return "\n".join([p.name for p in obj.groups.all()])

    def geo(self,obj):
        if obj.geolocation:
            #return obj.geolocation
            return 'x (lon): '+str(obj.geolocation['longitude'])+', y (lat): '+str(obj.geolocation['latitude'])
        else:
            return '-'

    def avatar_preview(self, obj):
        if obj.avatar:
            return mark_safe(
                '<img src="{0}" width="150" height="150" style="object-fit:contain" />'.format(obj.avatar['svg']))
        else:
            return '(No image)'

    def avatar_thumb(self, obj):
        if obj.avatar:
            return mark_safe(
                '<img src="{0}" width="50" height="50" style="object-fit:contain" />'.format(obj.avatar['svg']))
        else:
            return '(No image)'

    def institution(self, obj):
        i = obj.institution_link
        if i:
            return i.name
        else:
            return ''

    avatar_preview.short_description = 'Preview'

class InstitutionAdmin(admin.ModelAdmin):
    list_display = ['name', 'created', 'expires']
    list_filter = ['created','expires']
    readonly_fields = ('id',)

# Now register the new UserAdmin...
admin.site.register(User, UserAdmin)
admin.site.register(Institution, InstitutionAdmin)
