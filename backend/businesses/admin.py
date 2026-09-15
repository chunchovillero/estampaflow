from django.contrib import admin
from .models import Business,BusinessMembership,BusinessSetting,Plan,Subscription
admin.site.register((Business,BusinessMembership,BusinessSetting,Plan,Subscription))
