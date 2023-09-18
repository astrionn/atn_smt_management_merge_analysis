from django.contrib import admin
from django.apps import apps
from smt_management_app.models import *

class ListAdminMixin(object):
    def __init__(self, model, admin_site):
        self.list_display = [field.name for field in model._meta.fields]
        super(ListAdminMixin, self).__init__(model, admin_site)

#make sure this is at the end of admin.py
models = apps.get_models()
for model in models:
    #print(model)
    if model.__module__ != 'smt_management_app.models': continue
    admin_class = type('AdminClass', (ListAdminMixin, admin.ModelAdmin), {})
    try:
        admin.site.register(model, admin_class)
    except admin.sites.AlreadyRegistered:
        pass
