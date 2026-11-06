from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


 
class EnergyType(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    energy_types = models.ManyToManyField(EnergyType)
    password_updated_at = models.DateTimeField(default=timezone.now) 

    def __str__(self):
        return self.user.username + " - " + ", ".join([et.name for et in self.energy_types.all()])

from django.db import models

class Provider(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name




class UserProvider(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'provider')

    def __str__(self):
        return f"{self.user.username} ↔ {self.provider.name}"


# accounts/models.py
from django.db import models
from django.contrib.auth.models import User

class DSMData(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    customer_name = models.CharField(max_length=100)
    pooling_station = models.CharField(max_length=100)
    energy_type = models.CharField(max_length=20)
    date_time_block = models.DateTimeField()
    forecasted_schedule_mal = models.FloatField()
    avc = models.FloatField(null=True, blank=True)
    generation = models.FloatField()
    green_gen_scada = models.FloatField(null=True, blank=True)
    green_gen_meter = models.FloatField(null=True, blank=True)
    sems_provisional = models.FloatField(null=True, blank=True)
    sem_final = models.FloatField(null=True, blank=True)
    deviation_generation = models.FloatField(null=True, blank=True)
    deviation_scada = models.FloatField(null=True, blank=True)
    deviation_gen_meter = models.FloatField(null=True, blank=True)
    deviation_sems_provisional = models.FloatField(null=True, blank=True)
    deviation_sem_final = models.FloatField(null=True, blank=True)
    error_in_percent = models.FloatField(null=True, blank=True)
    

    class Meta:
        db_table = "dsm_data"





from django.db import models
from django.contrib.auth.models import User

class DSMResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    total_dsm = models.FloatField()
    next_month_dsm = models.FloatField(null=True, blank=True)

    mae = models.FloatField(null=True, blank=True)
    rmse = models.FloatField(null=True, blank=True)
    r2 = models.FloatField(null=True, blank=True)

    forecast_total = models.FloatField(null=True, blank=True)
    forecast_avg = models.FloatField(null=True, blank=True)
    forecast_max = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} | {self.created_at.strftime('%d-%m-%Y %H:%M')}"