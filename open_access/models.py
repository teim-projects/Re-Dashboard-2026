from django.db import models
from django.contrib.auth.models import User

class CalculationRecord(models.Model):
    PLANT_TYPE_CHOICES = (
        ("wind", "Wind"),
        ("solar", "Solar"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    plant_type = models.CharField(max_length=20, choices=PLANT_TYPE_CHOICES, default="wind", help_text="Plant Type (Wind or Solar)")

    # --- Part 1: Existing Tariff / DISCOM Inputs ---
    contract_demand = models.FloatField(default=0.0, blank=True, null=True, help_text="Contract Demand (kVA)")
    unit_msedcl = models.FloatField(default=0.0, blank=True, null=True, help_text="Unit @ MSEDCL Tariff (kWh)")
    duty_from_bill = models.FloatField(default=486181.4, help_text="Electricity Duty from bill")
    part1_duty = models.FloatField(default=0.0, help_text="Electricity Duty per unit in Part 1 (Rs/kWh)")
    wheeling_charge = models.FloatField(default=0.81, help_text="Wheeling Charges (Rs/kWh)")
    energy_charge = models.FloatField(default=8.44, help_text="Energy Charges (Rs/kWh)")
    fac_charge = models.FloatField(default=0.35, help_text="FAC Charges (Rs/kWh)")
    tose_charge = models.FloatField(default=0.27, help_text="TOSE Charges (Rs/kWh)")
    total_discom_tariff = models.FloatField(default=9.87, help_text="Total excluding contract demand (Rs/kWh)")

    # --- Part 2: Open Access Inputs & Calculations ---
    present_discom_tariff = models.FloatField(default=9.87)
    expected_escalation = models.FloatField(default=0.0, help_text="Expected yearly escalation (%)")
    project_capacity = models.CharField(max_length=100, default="", blank=True, help_text="Project Capacity")
    wind_generation = models.FloatField(default=0.0, help_text="Wind Generation (kWh)")
    annual_degradation = models.FloatField(default=0.0, help_text="Annual degradation (%)")
    proposed_power_tariff = models.FloatField(default=3.50, help_text="Proposed Power Tariff (Rs/kWh)")
    transmission_losses = models.FloatField(default=0.0, help_text="Transmission Losses @ 3.28%")
    wheeling_losses = models.FloatField(default=0.0, help_text="Wheeling Losses @ 7.5%")
    transmission_charges = models.FloatField(default=0.0, help_text="Transmission Charges (Rs/kWh)")
    oa_wheeling_charges = models.FloatField(default=0.81, help_text="Wheeling Charges (Rs/kWh)")
    css_from_bill = models.FloatField(default=2.07, help_text="Additional surcharge & CSS from bill")
    additional_surcharges_css_tose = models.FloatField(default=2.34, help_text="Additional Sur-Charges & CSS & TOSE")
    oa_duty_amount = models.FloatField(default=250018.35, help_text="Electricity Duty Amount for Open Access (Rs)")
    electricity_duty = models.FloatField(default=0.0, help_text="Electricity Duty per unit (Rs/kWh)")
    scheduling_operating_charges = models.FloatField(default=0.0, help_text="Scheduling & Operating Charges (Rs/kWh)")
    net_tariff_client = models.FloatField(default=0.0, help_text="Net Tariff for Client (Rs/kWh)")

    # --- Part 3: Plant Generation & Savings ---
    estimated_generation = models.FloatField(default=0.0, help_text="Estimated Generation (kWh)")
    assured_generation = models.FloatField(default=0.0, help_text="Assured Generation @ 70% (kWh)")
    p3_existing_tariff = models.FloatField(default=9.87, help_text="Part 3 Existing DISCOM Tariff (Rs/kWh)")
    rel_base_tariff = models.FloatField(default=3.50, help_text="Part 3 REL Base Tariff (Rs/kWh)")
    scheduling_css_tose = models.FloatField(default=2.34, help_text="Part 3 Scheduling + CSS & TOSE (Rs/kWh)")
    p3_wheeling_charges = models.FloatField(default=0.81, help_text="Part 3 Wheeling Charges (Rs/kWh)")
    p3_wheeling_losses = models.FloatField(default=0.2625, help_text="Part 3 Wheeling Losses (Rs/kWh)")
    p3_transmission_charges = models.FloatField(default=0.0, help_text="Part 3 Transmission Charges (Rs/kWh)")
    p3_transmission_losses = models.FloatField(default=0.1148, help_text="Part 3 Transmission Losses (Rs/kWh)")
    p3_electricity_duty = models.FloatField(default=0.0, help_text="Part 3 Electricity Duty (Rs/kWh)")
    delivered_tariff = models.FloatField(default=0.0, help_text="Delivered Tariff to Buyer (Rs/kWh)")
    per_unit_savings = models.FloatField(default=0.0, help_text="Per Unit Savings (Rs/kWh)")
    estimated_savings = models.FloatField(default=0.0, help_text="Estimated Savings due to REL Wind Plant (INR)")
    assured_savings = models.FloatField(default=0.0, help_text="Assured Savings (INR)")

    # --- Timestamps ---
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
