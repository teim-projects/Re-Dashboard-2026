from django.db import models
from django.contrib.auth.models import User

class CalculationRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # --- Input Fields (same as your form) ---
    total_units = models.FloatField()
    contract_demand = models.FloatField()
    billed_demand = models.FloatField()
    demand_rate = models.FloatField()

    wheeling_rate = models.FloatField()
    energy_rate = models.FloatField()

    tod_a_units = models.FloatField()
    tod_b_units = models.FloatField()
    tod_c_units = models.FloatField()
    tod_d_units = models.FloatField()

    tod_c_rate = models.FloatField()
    tod_d_rate = models.FloatField()

    fac_rate = models.FloatField()
    duty_percent = models.FloatField()
    tax_sale_rate = models.FloatField()

    incremental_rebate = models.FloatField()
    prompt_discount = models.FloatField()

    oa_percent = models.FloatField()
    oa_energy_rate = models.FloatField()
    oa_transmission_rate = models.FloatField()
    oa_wheeling_rate = models.FloatField()
    oa_loss_rate = models.FloatField()
    oa_sldc_fixed = models.FloatField()

    # --- Output Fields (results) ---
    total_only_msedcl = models.FloatField()
    total_msedcl_after = models.FloatField()
    total_oa_charges = models.FloatField()
    total_after_oa = models.FloatField()
    savings = models.FloatField()
    monthly_saving = models.FloatField()
    yearly_saving = models.FloatField()
    per_unit_saving = models.FloatField()

    oa_units = models.FloatField()
    msedcl_units_after = models.FloatField()

    # --- Auto fields ---
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.created_at.date()}"
