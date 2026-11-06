from django.contrib import admin
from .models import UserProfile, EnergyType
# Register your models here.

admin.site.register(UserProfile)
admin.site.register(EnergyType)