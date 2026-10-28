 
# Create your models here.
from django.db import models

class UploadMetadata(models.Model):
    table_name = models.CharField(max_length=255, unique=True)
    last_modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.table_name} - {self.last_modified}"
from django.db import models
from django.contrib.auth.models import User


class PreventiveMaintenanceData(models.Model):
    # ✅ Only the foreign key field (for linking users)
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column="user_id")

    class Meta:
        db_table = "preventive_maintenance_data"
        managed = False  # 🔥 Important: Django won't touch this table

    def __str__(self):
        return f"PreventiveMaintenanceData (User: {self.user.username})"
