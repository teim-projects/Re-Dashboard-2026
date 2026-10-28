from django.db import models

 








from django.db import models

# Create your models here.

from django.db import models

class BreakdownReport(models.Model):
    gen_date = models.DateField()
    loc_no = models.CharField(max_length=50)
    breakdown_remarks = models.TextField()

    def __str__(self):
        return f"{self.loc_no} - {self.gen_date}"

