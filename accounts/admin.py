from django.contrib import admin
from .models import UserProfile, EnergyType
from .models import RDSCatalog
# Register your models here.

admin.site.register(UserProfile)
admin.site.register(EnergyType)
admin.site.register(RDSCatalog)