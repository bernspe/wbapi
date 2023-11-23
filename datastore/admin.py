from django.contrib import admin

from datastore.models import Survey, SurveyObjection
from django.utils.translation import gettext_lazy as _


# Register your models here.

class SurveyAdmin(admin.ModelAdmin):
    list_display = ['created','type','score']
    list_filter = ['created']


class IcfCodeListFilter(admin.SimpleListFilter):
    title = _("ICF Code")

    # Parameter for the filter that will be used in the URL query.
    parameter_name = "icf_code"
    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        templist = list(set([o.data['icf_code'] for o in qs])) # sort and remove duplicates
        return [(o, _(o)) for o in templist]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(data__isnull=False,data__icf_code=self.value())
        else:
            return queryset

class SurveyObjectionAdmin(admin.ModelAdmin):
    list_display = ['id','icf_code']
    list_filter = [IcfCodeListFilter]

    def icf_code(self, obj):
        d=obj.data
        if d:
            return d['icf_code']
        else:
            return '-'


admin.site.register(Survey, SurveyAdmin)
admin.site.register(SurveyObjection,SurveyObjectionAdmin)
