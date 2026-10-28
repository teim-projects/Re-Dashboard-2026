from django.shortcuts import render

# Create your views here.

def open_access(request):
    return render(request,'open_access.html')



from django.shortcuts import render
def calculate_bills(params):
    """
    params is a dict of floats taken from the form.
    Returns a dict with all calculated values.
    """

    # ----- Common inputs -----
    total_units = params["total_units"]            # kWh
    contract_demand = params["contract_demand"]    # kVA
    billed_demand = params["billed_demand"]        # kVA used for charges (75% of contract)
    demand_rate = params["demand_rate"]            # Rs/kVA
    
    wheeling_rate = params["wheeling_rate"]        # Rs/kWh
    energy_rate = params["energy_rate"]            # Rs/kWh
    tod_c_rate = params["tod_c_rate"]              # Rs/kWh (usually -3.5)
    tod_d_rate = params["tod_d_rate"]              # Rs/kWh (usually +3.5)
    tod_a_units = params["tod_a_units"]            # kWh in Zone A
    tod_b_units = params["tod_b_units"]            # kWh in Zone B
    tod_c_units = params["tod_c_units"]            # kWh in Zone C
    tod_d_units = params["tod_d_units"]            # kWh in Zone D
    
    fac_rate = params["fac_rate"]                  # Rs/kWh
    duty_percent = params["duty_percent"] / 100.0  # to fraction
    tax_sale_rate = params["tax_sale_rate"]        # Rs/kWh
    
    incremental_rebate = params["incremental_rebate"]  # Rs (negative)
    prompt_discount = params["prompt_discount"]        # Rs (negative)

    # ----- OA related inputs -----
    oa_percent = params["oa_percent"] / 100.0
    oa_energy_rate = params["oa_energy_rate"]
    oa_transmission_rate = params["oa_transmission_rate"]
    oa_wheeling_rate = params["oa_wheeling_rate"]
    oa_loss_rate = params["oa_loss_rate"]
    oa_sldc_fixed = params["oa_sldc_fixed"]

    # =======================
    # 1) ONLY MSEDCL BILL - EXACT EXCEL FORMULAS
    # =======================
    
    # Calculate each component EXACTLY as per Excel
    demand_charges_only = billed_demand * demand_rate  # E11 = B10 * B11 = 600 * 267 = 160,200
    
    energy_only = total_units * energy_rate  # E13 = B13 * C7 = 14.03 * 50,728 = 711,714
    wheeling_only = total_units * wheeling_rate  # E12 = B12 * C7 = 0.74 * 50,728 = 37,539
    
    # TOD charges (only Zone C & D as per Excel)
    tod_c_only = tod_c_units * tod_c_rate  # E25 = C25 * B25 = 18,868 * (-3.5) = -66,038
    tod_d_only = tod_d_units * tod_d_rate  # E26 = C26 * B26 = 21,337 * 3.5 = 74,680
    tod_total_only = tod_c_only + tod_d_only  # E14 = 8,642 (but Excel shows 8,660 due to rounding)
    
    fac_only = 0.0  # E15 = 0 (FAC is not applied)
    tax_sale_only = total_units * tax_sale_rate  # E17 = B17 * C7 = 0.19 * 50,728 = 9,638
    
    # Electricity Duty as per Excel E16 = (E11+E12+E13+E14+E15+E17) * B16
    duty_base_only = (
        demand_charges_only +  # E11
        energy_only +          # E13  
        wheeling_only +        # E12
        tod_total_only +       # E14
        fac_only +             # E15
        tax_sale_only          # E17
    )
    
    duty_only = duty_base_only * duty_percent  # E16 = duty_base * 21%
    
    # FINAL MSEDCL TOTAL - EXACT EXCEL FORMULA E32 = SUM(E10:E21)
    total_only_msedcl = (
        demand_charges_only +    # E11 = 160,200
        energy_only +            # E13 = 711,714
        wheeling_only +          # E12 = 37,539
        tod_total_only +         # E14 = 8,642
        fac_only +               # E15 = 0
        duty_only +              # E16 = Duty
        tax_sale_only +          # E17 = 9,638
        incremental_rebate +     # E19 = -9,657
        prompt_discount          # E20 = -9,085
    )
    
    unit_rate_only = total_only_msedcl / total_units if total_units else 0

    # =======================
    # 2) AFTER OPEN ACCESS - EXACT EXCEL FORMULAS
    # =======================

    # Calculate OA and remaining MSEDCL units (as per Excel J4, J5)
    oa_units = total_units * oa_percent  # J4 = Total Units × OA% = 50,728 × 58% = 29,422
    msedcl_units_after = total_units - oa_units  # J5 = Total Units - OA Units = 50,728 - 29,422 = 21,337

    # MSEDCL charges after OA - Excel columns I, J, L
    demand_charges_after = billed_demand * demand_rate  # L11 = I11 * I10 = 267 × 600 = 160,200
    
    # Energy charges for remaining MSEDCL units
    energy_after = msedcl_units_after * energy_rate  # L13 = I13 * J5 = 14.03 × 21,337 = 299,358
    
    # Wheeling charges for remaining MSEDCL units  
    wheeling_after = msedcl_units_after * wheeling_rate  # L12 = I12 * J5 = 0.74 × 21,337 = 15,789
    
    # TOD charges after OA - Only Zone D remains (as per Excel row 31)
    tod_d_after = tod_d_units * tod_d_rate  # L14 = C31 * B31 = 21,337 × 3.5 = 74,680
    tod_total_after = tod_d_after  # Only Zone D contributes
    
    # FAC charges for remaining MSEDCL units
    fac_after = msedcl_units_after * fac_rate  # L15 = I15 * J5 = 0.50 × 21,337 = 10,669
    
    # Tax on sale for remaining MSEDCL units
    tax_sale_after = msedcl_units_after * tax_sale_rate  # L17 = I17 * J5 = 0.19 × 21,337 = 4,054
    
    # Duty after OA - Excel formula: (L11+L12+L13+L14+L15+L17) * I16
    duty_base_after = (
        demand_charges_after +  # L11
        energy_after +          # L13
        wheeling_after +        # L12  
        tod_total_after +       # L14
        fac_after +             # L15
        tax_sale_after          # L17
    )
    duty_after = duty_base_after * duty_percent  # L16 = duty_base × 21%
    
    # No rebates in OA scenario as per Excel
    incremental_rebate_after = 0
    prompt_discount_after = 0

    # MSEDCL TOTAL BILL AMOUNT AFTER OA (Excel L19)
    total_msedcl_after = (
        demand_charges_after +  # L11
        energy_after +          # L13
        wheeling_after +        # L12
        tod_total_after +       # L14
        fac_after +             # L15
        duty_after +            # L16
        tax_sale_after +        # L17
        incremental_rebate_after + 
        prompt_discount_after
    )

    # OPEN ACCESS CHARGES (Excel L21-L25)
    oa_energy_cost = oa_units * oa_energy_rate  # L4 = J4 * K4 = 29,422 × 4.5 = 132,260
    
    # Transmission charges (Excel L21)
    oa_transmission = oa_units * oa_transmission_rate  # L21 = J4 * I21 = 29,422 × 1.14 = 33,506
    
    # Wheeling Charges (Excel L22)  
    oa_wheeling = oa_units * oa_wheeling_rate  # L22 = J4 * I22 = 29,422 × 0.74 = 21,749
    
    # Losses (Excel L23)
    oa_losses = oa_units * oa_loss_rate  # L23 = J4 * I23 = 29,422 × 0.59 = 17,341
    
    # Operating Charges (Excel L24) - fixed amount
    oa_operating = oa_sldc_fixed  # L24 = 15,450

    # TOTAL OPEN ACCESS CHARGES (Excel L25)
    total_oa_charges = (
        oa_transmission +
        oa_wheeling +
        oa_losses +
        oa_operating
    )

    # Total Bill from OA (Excel L26) = MSEDCL Bill + OA Charges + OA Energy Cost
    total_after_oa = total_msedcl_after + total_oa_charges + oa_energy_cost
    
    unit_rate_after = total_after_oa / total_units if total_units else 0

    # Savings calculation
    savings = total_only_msedcl - total_after_oa
    per_unit_saving = savings / total_units if total_units else 0
    monthly_saving = savings
    yearly_saving = savings * 12

    return {
        "total_only_msedcl": round(total_only_msedcl, 2),
        "unit_rate_only": round(unit_rate_only, 2),
        "total_msedcl_after": round(total_msedcl_after, 2),
        "total_oa_charges": round(total_oa_charges, 2),
        "oa_energy_cost": round(oa_energy_cost, 2),
        "total_after_oa": round(total_after_oa, 2),
        "unit_rate_after": round(unit_rate_after, 2),
        "savings": round(savings, 2),
        "per_unit_saving": round(per_unit_saving, 2),
        "monthly_saving": round(monthly_saving, 2),
        "yearly_saving": round(yearly_saving, 2),
        "oa_units": round(oa_units, 0),
        "msedcl_units_after": round(msedcl_units_after, 0),
    } 



from .models import CalculationRecord
from django.contrib import messages

def calculator_view(request):

    default_data = {
        "tod_a_units": 8016,
        "tod_b_units": 2507,
        "tod_c_units": 18868,
        "tod_d_units": 21337,
        "total_units": 50728,
        "contract_demand": 356,
        "billed_demand": 267,
        "demand_rate": 600,
        "wheeling_rate": 0.74,
        "energy_rate": 14.03,
        "tod_c_rate": -3.5,
        "tod_d_rate": 3.5,
        "fac_rate": 0.50,
        "duty_percent": 21.0,
        "tax_sale_rate": 0.19,
        "incremental_rebate": -9657,
        "prompt_discount": -9085,
        "oa_percent": 58.0,
        "oa_energy_rate": 4.5,
        "oa_transmission_rate": 1.14,
        "oa_wheeling_rate": 0.74,
        "oa_loss_rate": 0.59,
        "oa_sldc_fixed": 15450,
    }

    context = {"input": default_data, "result": None}

    if request.method == "POST":
        data = {}
        for key in default_data.keys():
            value = request.POST.get(key, "")
            try:
                data[key] = float(value)
            except ValueError:
                data[key] = default_data[key]

        result = calculate_bills(data)
        context["input"] = data
        context["result"] = result

        if "save_result" in request.POST:
            CalculationRecord.objects.create(
                user=request.user,
                total_units=data["total_units"],
                contract_demand=data["contract_demand"],
                billed_demand=data["billed_demand"],
                demand_rate=data["demand_rate"],
                wheeling_rate=data["wheeling_rate"],
                energy_rate=data["energy_rate"],
                tod_a_units=data["tod_a_units"],
                tod_b_units=data["tod_b_units"],
                tod_c_units=data["tod_c_units"],
                tod_d_units=data["tod_d_units"],
                tod_c_rate=data["tod_c_rate"],
                tod_d_rate=data["tod_d_rate"],
                fac_rate=data["fac_rate"],
                duty_percent=data["duty_percent"],
                tax_sale_rate=data["tax_sale_rate"],
                incremental_rebate=data["incremental_rebate"],
                prompt_discount=data["prompt_discount"],
                oa_percent=data["oa_percent"],
                oa_energy_rate=data["oa_energy_rate"],
                oa_transmission_rate=data["oa_transmission_rate"],
                oa_wheeling_rate=data["oa_wheeling_rate"],
                oa_loss_rate=data["oa_loss_rate"],
                oa_sldc_fixed=data["oa_sldc_fixed"],

                total_only_msedcl=result["total_only_msedcl"],
                total_msedcl_after=result["total_msedcl_after"],
                total_oa_charges=result["total_oa_charges"],
                total_after_oa=result["total_after_oa"],
                savings=result["savings"],
                monthly_saving=result["monthly_saving"],
                yearly_saving=result["yearly_saving"],
                per_unit_saving=result["per_unit_saving"],
                oa_units=result["oa_units"],
                msedcl_units_after=result["msedcl_units_after"],
            )

            messages.success(request, "Calculation saved successfully!")
            return redirect("calculation_history")

    return render(request, "calculator.html", context)


from django.contrib.auth.decorators import login_required
from .models import CalculationRecord
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from django.core.paginator import Paginator

@login_required
def calculation_history(request):

    # --- Records per page filter ---
    per_page = request.GET.get("per_page", 5)
    try:
        per_page = int(per_page)
    except:
        per_page = 5

    # --- Fetch records ---
    all_records = CalculationRecord.objects.filter(user=request.user).order_by("-created_at")

    # --- Pagination ---
    paginator = Paginator(all_records, per_page)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "calculation_history.html", {
        "page_obj": page_obj,
        "records": page_obj.object_list,
        "per_page": per_page,
    })

@login_required
def delete_record(request, pk):
    record = get_object_or_404(CalculationRecord, id=pk, user=request.user)
    record.delete()
    messages.success(request, "Record deleted successfully!")
    return redirect("calculation_history")



from django.http import JsonResponse

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

@login_required
def record_details(request, pk):
    record = get_object_or_404(CalculationRecord, id=pk, user=request.user)

    data = {
        "created_at": record.created_at.strftime("%d %b, %Y %H:%M"),

        # Basic inputs
        "total_units": record.total_units,
        "contract_demand": record.contract_demand,
        "billed_demand": record.billed_demand,
        "demand_rate": record.demand_rate,

        # MSEDCL rates
        "wheeling_rate": record.wheeling_rate,
        "energy_rate": record.energy_rate,
        "fac_rate": record.fac_rate,
        "duty_percent": record.duty_percent,
        "tax_sale_rate": record.tax_sale_rate,

        # TOD
        "tod_a_units": record.tod_a_units,
        "tod_b_units": record.tod_b_units,
        "tod_c_units": record.tod_c_units,
        "tod_d_units": record.tod_d_units,
        "tod_c_rate": record.tod_c_rate,
        "tod_d_rate": record.tod_d_rate,

        # Rebates
        "incremental_rebate": record.incremental_rebate,
        "prompt_discount": record.prompt_discount,

        # OA inputs
        "oa_percent": record.oa_percent,
        "oa_energy_rate": record.oa_energy_rate,
        "oa_transmission_rate": record.oa_transmission_rate,
        "oa_wheeling_rate": record.oa_wheeling_rate,
        "oa_loss_rate": record.oa_loss_rate,
        "oa_sldc_fixed": record.oa_sldc_fixed,

        # Calculated results
        "total_only_msedcl": record.total_only_msedcl,
        "total_msedcl_after": record.total_msedcl_after,
        "total_oa_charges": record.total_oa_charges,
        "oa_energy_cost": record.oa_energy_cost if hasattr(record, "oa_energy_cost") else "",
        "total_after_oa": record.total_after_oa,
        "savings": record.savings,
        "monthly_saving": record.monthly_saving,
        "yearly_saving": record.yearly_saving,
        "per_unit_saving": record.per_unit_saving,
        "oa_units": record.oa_units,
        "msedcl_units_after": record.msedcl_units_after,
    }

    return JsonResponse(data)
