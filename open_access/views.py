from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from .models import CalculationRecord


def open_access(request):
    return redirect('calculator')


def calculate_open_access(params):
    """
    Computes Open Access calculation across Part 1, Part 2, and Part 3.
    Supports both Wind and Solar plant types.
    """
    plant_type = params.get("plant_type", "wind")
    if plant_type not in ["wind", "solar"]:
        plant_type = "wind"

    # -----------------------------
    # PART 1: Existing DISCOM Tariff
    # -----------------------------
    contract_demand = params.get("contract_demand", 0.0)
    unit_msedcl = params.get("unit_msedcl", 0.0)
    duty_from_bill = params.get("duty_from_bill", 486181.4)
    if duty_from_bill is None or duty_from_bill == "":
        duty_from_bill = 486181.4
    else:
        try:
            duty_from_bill = float(duty_from_bill)
        except ValueError:
            duty_from_bill = 486181.4

    # Part 1 Electricity Duty per unit = duty_from_bill / unit_msedcl
    if unit_msedcl and unit_msedcl > 0:
        part1_duty = duty_from_bill / unit_msedcl
    else:
        part1_duty = params.get("part1_duty", 0.0)

    wheeling_charge = params.get("wheeling_charge", 0.81)
    energy_charge = params.get("energy_charge", 8.44)
    fac_charge = params.get("fac_charge", 0.35)
    tose_charge = params.get("tose_charge", 0.27)

    # Total excluding contract demand = Wheeling + Energy + FAC + TOSE + Electricity Duty
    total_discom_tariff = wheeling_charge + energy_charge + fac_charge + tose_charge + part1_duty

    # -----------------------------
    # PART 2: With Open Access
    # -----------------------------
    present_discom_tariff = total_discom_tariff
    expected_escalation = params.get("expected_escalation", 0.0)
    project_capacity = params.get("project_capacity", "")
    wind_generation = params.get("wind_generation", 0.0)
    annual_degradation = params.get("annual_degradation", 0.0)

    # 5) Proposed Power Tariff
    proposed_power_tariff = params.get("proposed_power_tariff", 3.50)

    # 6) Transmission Losses (@3.28%) = 5th * 3.28%
    transmission_losses = proposed_power_tariff * 0.0328

    # 7) Wheeling Losses (@7.5%) = 5th * 7.5%
    wheeling_losses = proposed_power_tariff * 0.075

    # 8) Transmission Charges
    transmission_charges = params.get("transmission_charges", 0.0)

    # 9) Wheeling Charges
    oa_wheeling_charges = params.get("oa_wheeling_charges", 0.81)

    # 10) Additional Sur-Charges & CSS & TOSE = 0 + 2.07 + from part 1 TOSE (Only for Wind, exempt/0 for Solar)
    if plant_type == "solar":
        css_from_bill = 0.0
        additional_surcharges_css_tose = 0.0
    else:
        css_from_bill = params.get("css_from_bill", 2.07)
        if css_from_bill is None or css_from_bill == "":
            css_from_bill = 2.07
        else:
            try:
                css_from_bill = float(css_from_bill)
            except ValueError:
                css_from_bill = 2.07

        if "additional_surcharges_css_tose" in params and params.get("use_explicit_css"):
            additional_surcharges_css_tose = params.get("additional_surcharges_css_tose", tose_charge + 2.07)
        else:
            additional_surcharges_css_tose = css_from_bill + tose_charge

    # 11) Electricity Duty for Open Access = oa_duty_amount / wind_generation (Only for Wind, exempt/0 for Solar)
    if plant_type == "solar":
        oa_duty_amount = 0.0
        electricity_duty = 0.0
    else:
        oa_duty_amount = params.get("oa_duty_amount", 250018.35)
        if oa_duty_amount is None or oa_duty_amount == "":
            oa_duty_amount = 250018.35
        else:
            try:
                oa_duty_amount = float(oa_duty_amount)
            except ValueError:
                oa_duty_amount = 250018.35

        if wind_generation and wind_generation > 0 and oa_duty_amount > 0:
            electricity_duty = oa_duty_amount / wind_generation
        else:
            electricity_duty = params.get("electricity_duty", 0.0)

    # 12) Scheduling & Operating Charges = (16450 / wind_generation) + (27918.99 / wind_generation)
    if wind_generation and wind_generation > 0:
        scheduling_operating_charges = (16450.0 / wind_generation) + (27918.99 / wind_generation)
    else:
        scheduling_operating_charges = 0.0

    # 13) Net Tariff for Client = 5th to 12th sum
    net_tariff_client = (
        proposed_power_tariff
        + transmission_losses
        + wheeling_losses
        + transmission_charges
        + oa_wheeling_charges
        + additional_surcharges_css_tose
        + electricity_duty
        + scheduling_operating_charges
    )

    # -----------------------------
    # PART 3: Wind Plant Generation & Buyer Savings
    # -----------------------------
    # 1) Estimated Generation
    try:
        estimated_generation = float(params["p3_estimated_generation"]) if params.get("p3_estimated_generation") not in ["", None] else wind_generation
    except (ValueError, TypeError):
        estimated_generation = wind_generation

    # 2) Assured Generation = 70% of Estimated Generation
    try:
        assured_generation = float(params["p3_assured_generation"]) if params.get("p3_assured_generation") not in ["", None] else estimated_generation * 0.70
    except (ValueError, TypeError):
        assured_generation = estimated_generation * 0.70

    # 3) Existing DISCOM tariff = Part 1 total excluding contract demand
    try:
        existing_discom_tariff = float(params["p3_existing_tariff"]) if params.get("p3_existing_tariff") not in ["", None] else total_discom_tariff
    except (ValueError, TypeError):
        existing_discom_tariff = total_discom_tariff

    # 4) REL Base Tariff = Part 2 5th value
    try:
        rel_base_tariff = float(params["p3_rel_base_tariff"]) if params.get("p3_rel_base_tariff") not in ["", None] else proposed_power_tariff
    except (ValueError, TypeError):
        rel_base_tariff = proposed_power_tariff

    # 5) Scheduling & System operation (+ CSS & TOSE for Wind)
    if plant_type == "solar":
        default_sched_css = scheduling_operating_charges
    else:
        default_sched_css = additional_surcharges_css_tose + scheduling_operating_charges

    try:
        scheduling_css_tose = float(params["p3_scheduling_css_tose"]) if params.get("p3_scheduling_css_tose") not in ["", None] else default_sched_css
    except (ValueError, TypeError):
        scheduling_css_tose = default_sched_css

    # 6) Wheeling charges = Part 1 / Part 2 9th
    try:
        p3_wheeling_charges = float(params["p3_wheeling_charges"]) if params.get("p3_wheeling_charges") not in ["", None] else oa_wheeling_charges
    except (ValueError, TypeError):
        p3_wheeling_charges = oa_wheeling_charges

    # 7) Wheeling losses @ 7.50% = Part 2 7th
    try:
        p3_wheeling_losses = float(params["p3_wheeling_losses"]) if params.get("p3_wheeling_losses") not in ["", None] else wheeling_losses
    except (ValueError, TypeError):
        p3_wheeling_losses = wheeling_losses

    # 8) Transmission charges = Part 2 8th
    try:
        p3_transmission_charges = float(params["p3_transmission_charges"]) if params.get("p3_transmission_charges") not in ["", None] else transmission_charges
    except (ValueError, TypeError):
        p3_transmission_charges = transmission_charges

    # 9) Transmission losses @ 3.28% = Part 2 6th
    try:
        p3_transmission_losses = float(params["p3_transmission_losses"]) if params.get("p3_transmission_losses") not in ["", None] else transmission_losses
    except (ValueError, TypeError):
        p3_transmission_losses = transmission_losses

    # 10) Electricity duty = Part 2 11th (Exempt / 0 for Solar)
    if plant_type == "solar":
        p3_electricity_duty = 0.0
    else:
        try:
            p3_electricity_duty = float(params["p3_electricity_duty"]) if params.get("p3_electricity_duty") not in ["", None] else electricity_duty
        except (ValueError, TypeError):
            p3_electricity_duty = electricity_duty

    # Round Part 3 components to 4 decimal places for exact match with screen inputs
    rel_base_tariff = round(rel_base_tariff, 4)
    scheduling_css_tose = round(scheduling_css_tose, 4)
    p3_wheeling_charges = round(p3_wheeling_charges, 4)
    p3_wheeling_losses = round(p3_wheeling_losses, 4)
    p3_transmission_charges = round(p3_transmission_charges, 4)
    p3_transmission_losses = round(p3_transmission_losses, 4)
    p3_electricity_duty = round(p3_electricity_duty, 4)
    existing_discom_tariff = round(existing_discom_tariff, 4)

    # 11) Delivered Tariff to Buyer = addition of 4th to 10th of Part 3
    delivered_tariff = round(
        rel_base_tariff
        + scheduling_css_tose
        + p3_wheeling_charges
        + p3_wheeling_losses
        + p3_transmission_charges
        + p3_transmission_losses
        + p3_electricity_duty,
        4
    )

    # 12) Estimated Savings due to Plant (INR) = 1st * (3rd - 11th)
    per_unit_savings = round(existing_discom_tariff - delivered_tariff, 4)
    estimated_savings = round(estimated_generation * per_unit_savings, 2)
    assured_savings = round(assured_generation * per_unit_savings, 2)
    monthly_savings = round(estimated_savings / 12.0, 2) if estimated_savings else 0.0

    return {
        "plant_type": plant_type,
        # Part 1
        "contract_demand": round(contract_demand, 2) if contract_demand else "",
        "unit_msedcl": round(unit_msedcl, 2) if unit_msedcl else "",
        "duty_from_bill": round(duty_from_bill, 2),
        "part1_duty": round(part1_duty, 4),
        "wheeling_charge": round(wheeling_charge, 4),
        "energy_charge": round(energy_charge, 4),
        "fac_charge": round(fac_charge, 4),
        "tose_charge": round(tose_charge, 4),
        "total_discom_tariff": round(total_discom_tariff, 4),

        # Part 2
        "present_discom_tariff": round(present_discom_tariff, 4),
        "expected_escalation": round(expected_escalation, 2),
        "project_capacity": project_capacity,
        "wind_generation": round(wind_generation, 2),
        "annual_degradation": round(annual_degradation, 2),
        "proposed_power_tariff": round(proposed_power_tariff, 4),
        "transmission_losses": round(transmission_losses, 4),
        "wheeling_losses": round(wheeling_losses, 4),
        "transmission_charges": round(transmission_charges, 4),
        "oa_wheeling_charges": round(oa_wheeling_charges, 4),
        "css_from_bill": round(css_from_bill, 4),
        "additional_surcharges_css_tose": round(additional_surcharges_css_tose, 4),
        "oa_duty_amount": round(oa_duty_amount, 2),
        "electricity_duty": round(electricity_duty, 4),
        "scheduling_operating_charges": round(scheduling_operating_charges, 4),
        "net_tariff_client": round(net_tariff_client, 4),

        # Part 3
        "estimated_generation": round(estimated_generation, 2),
        "assured_generation": round(assured_generation, 2),
        "existing_discom_tariff": round(existing_discom_tariff, 4),
        "rel_base_tariff": round(rel_base_tariff, 4),
        "scheduling_css_tose": round(scheduling_css_tose, 4),
        "p3_wheeling_charges": round(p3_wheeling_charges, 4),
        "p3_wheeling_losses": round(p3_wheeling_losses, 4),
        "p3_transmission_charges": round(p3_transmission_charges, 4),
        "p3_transmission_losses": round(p3_transmission_losses, 4),
        "p3_electricity_duty": round(p3_electricity_duty, 4),
        "delivered_tariff": round(delivered_tariff, 4),
        "per_unit_savings": round(per_unit_savings, 4),
        "estimated_savings": round(estimated_savings, 2),
        "assured_savings": round(assured_savings, 2),
        "monthly_savings": round(monthly_savings, 2),
    }


def calculator_view(request):
    selected_plant_type = request.GET.get("plant_type", "wind")
    if selected_plant_type not in ["wind", "solar"]:
        selected_plant_type = "wind"

    default_data = {
        "plant_type": selected_plant_type,
        # Part 1
        "contract_demand": "",
        "unit_msedcl": "",
        "duty_from_bill": 486181.4,
        "part1_duty": 0.0,
        "wheeling_charge": 0.81,
        "energy_charge": 8.44,
        "fac_charge": 0.35,
        "tose_charge": 0.27,
        # Part 2
        "expected_escalation": 0.0,
        "project_capacity": "",
        "wind_generation": "",
        "annual_degradation": 0.0,
        "proposed_power_tariff": 3.50,
        "transmission_charges": 0.0,
        "oa_wheeling_charges": 0.81,
        "css_from_bill": 2.07,
        "oa_duty_amount": 250018.35,
        "electricity_duty": 0.0,
    }

    context = {"input": default_data, "result": None}

    # Initialize a baseline calculation for defaults
    calc_params = {}
    for k, v in default_data.items():
        if k in ["contract_demand", "unit_msedcl", "wind_generation", "project_capacity"] and (v == "" or v is None):
            calc_params[k] = 0.0 if k != "project_capacity" else ""
        else:
            try:
                calc_params[k] = float(v)
            except (ValueError, TypeError):
                calc_params[k] = v

    initial_result = calculate_open_access(calc_params)
    context["result"] = initial_result

    if request.method == "POST":
        data = {}
        data["plant_type"] = request.POST.get("plant_type", "wind")
        if data["plant_type"] not in ["wind", "solar"]:
            data["plant_type"] = "wind"

        for key, def_val in default_data.items():
            if key == "plant_type":
                continue
            val = request.POST.get(key, "").strip()
            if key == "project_capacity":
                data[key] = val
            elif key in ["contract_demand", "unit_msedcl", "wind_generation"]:
                try:
                    data[key] = float(val) if val else 0.0
                except ValueError:
                    data[key] = 0.0
            else:
                try:
                    data[key] = float(val) if val else float(def_val)
                except ValueError:
                    data[key] = float(def_val) if isinstance(def_val, (int, float)) else 0.0

        if request.POST.get("additional_surcharges_css_tose"):
            try:
                data["additional_surcharges_css_tose"] = float(request.POST.get("additional_surcharges_css_tose"))
                data["use_explicit_css"] = True
            except ValueError:
                pass

        # Part 3 overrides if provided by user
        p3_field_keys = [
            "p3_estimated_generation",
            "p3_assured_generation",
            "p3_existing_tariff",
            "p3_rel_base_tariff",
            "p3_scheduling_css_tose",
            "p3_wheeling_charges",
            "p3_wheeling_losses",
            "p3_transmission_charges",
            "p3_transmission_losses",
            "p3_electricity_duty",
        ]
        for p3k in p3_field_keys:
            val = request.POST.get(p3k, "").strip()
            if val != "":
                try:
                    data[p3k] = float(val)
                except ValueError:
                    pass

        result = calculate_open_access(data)
        context["input"] = data
        context["result"] = result

        if "save_result" in request.POST and request.user.is_authenticated:
            CalculationRecord.objects.create(
                user=request.user,
                plant_type=result.get("plant_type", "wind"),
                contract_demand=result["contract_demand"] if result["contract_demand"] != "" else 0.0,
                unit_msedcl=result["unit_msedcl"] if result["unit_msedcl"] != "" else 0.0,
                duty_from_bill=result["duty_from_bill"],
                part1_duty=result["part1_duty"],
                wheeling_charge=result["wheeling_charge"],
                energy_charge=result["energy_charge"],
                fac_charge=result["fac_charge"],
                tose_charge=result["tose_charge"],
                total_discom_tariff=result["total_discom_tariff"],

                present_discom_tariff=result["present_discom_tariff"],
                expected_escalation=result["expected_escalation"],
                project_capacity=result["project_capacity"],
                wind_generation=result["wind_generation"],
                annual_degradation=result["annual_degradation"],
                proposed_power_tariff=result["proposed_power_tariff"],
                transmission_losses=result["transmission_losses"],
                wheeling_losses=result["wheeling_losses"],
                transmission_charges=result["transmission_charges"],
                oa_wheeling_charges=result["oa_wheeling_charges"],
                css_from_bill=result["css_from_bill"],
                additional_surcharges_css_tose=result["additional_surcharges_css_tose"],
                oa_duty_amount=result["oa_duty_amount"],
                electricity_duty=result["electricity_duty"],
                scheduling_operating_charges=result["scheduling_operating_charges"],
                net_tariff_client=result["net_tariff_client"],

                estimated_generation=result["estimated_generation"],
                assured_generation=result["assured_generation"],
                p3_existing_tariff=result["existing_discom_tariff"],
                rel_base_tariff=result["rel_base_tariff"],
                scheduling_css_tose=result["scheduling_css_tose"],
                p3_wheeling_charges=result["p3_wheeling_charges"],
                p3_wheeling_losses=result["p3_wheeling_losses"],
                p3_transmission_charges=result["p3_transmission_charges"],
                p3_transmission_losses=result["p3_transmission_losses"],
                p3_electricity_duty=result["p3_electricity_duty"],
                delivered_tariff=result["delivered_tariff"],
                per_unit_savings=result["per_unit_savings"],
                estimated_savings=result["estimated_savings"],
                assured_savings=result["assured_savings"],
            )

            messages.success(request, f"{result.get('plant_type', 'wind').capitalize()} Open Access calculation saved successfully!")
            return redirect("calculation_history")

    return render(request, "calculator.html", context)


@login_required
def calculation_history(request):
    per_page = request.GET.get("per_page", 10)
    try:
        per_page = int(per_page)
    except (ValueError, TypeError):
        per_page = 10

    plant_type_filter = request.GET.get("plant_type", "all")
    all_records = CalculationRecord.objects.filter(user=request.user)
    if plant_type_filter in ["wind", "solar"]:
        all_records = all_records.filter(plant_type=plant_type_filter)
    all_records = all_records.order_by("-created_at")

    paginator = Paginator(all_records, per_page)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "calculation_history.html",
        {
            "page_obj": page_obj,
            "records": page_obj.object_list,
            "per_page": per_page,
            "plant_type_filter": plant_type_filter,
        },
    )


@login_required
def delete_record(request, pk):
    record = get_object_or_404(CalculationRecord, id=pk, user=request.user)
    record.delete()
    messages.success(request, "Record deleted successfully!")
    return redirect("calculation_history")


@login_required
def record_details(request, pk):
    record = get_object_or_404(CalculationRecord, id=pk, user=request.user)

    data = {
        "plant_type": record.plant_type,
        "plant_type_display": record.get_plant_type_display(),
        "created_at": record.created_at.strftime("%d %b, %Y %H:%M"),
        # Part 1
        "contract_demand": record.contract_demand if record.contract_demand else "N/A",
        "unit_msedcl": f"{record.unit_msedcl:,.2f}" if record.unit_msedcl else "N/A",
        "duty_from_bill": f"₹ {record.duty_from_bill:,.2f}",
        "part1_duty": f"{record.part1_duty:.4f}",
        "wheeling_charge": f"{record.wheeling_charge:.4f}",
        "energy_charge": f"{record.energy_charge:.4f}",
        "fac_charge": f"{record.fac_charge:.4f}",
        "tose_charge": f"{record.tose_charge:.4f}",
        "total_discom_tariff": f"{record.total_discom_tariff:.4f}",

        # Part 2
        "present_discom_tariff": f"{record.present_discom_tariff:.4f}",
        "expected_escalation": f"{record.expected_escalation:.2f}%",
        "project_capacity": record.project_capacity or "N/A",
        "wind_generation": f"{record.wind_generation:,.2f}",
        "annual_degradation": f"{record.annual_degradation:.2f}%",
        "proposed_power_tariff": f"{record.proposed_power_tariff:.4f}",
        "transmission_losses": f"{record.transmission_losses:.4f}",
        "wheeling_losses": f"{record.wheeling_losses:.4f}",
        "transmission_charges": f"{record.transmission_charges:.4f}",
        "oa_wheeling_charges": f"{record.oa_wheeling_charges:.4f}",
        "css_from_bill": f"{record.css_from_bill:.4f}",
        "additional_surcharges_css_tose": f"{record.additional_surcharges_css_tose:.4f}",
        "oa_duty_amount": f"₹ {record.oa_duty_amount:,.2f}",
        "electricity_duty": f"{record.electricity_duty:.4f}",
        "scheduling_operating_charges": f"{record.scheduling_operating_charges:.4f}",
        "net_tariff_client": f"{record.net_tariff_client:.4f}",

        # Part 3
        "estimated_generation": f"{record.estimated_generation:,.2f}",
        "assured_generation": f"{record.assured_generation:,.2f}",
        "p3_existing_tariff": f"{record.p3_existing_tariff:.4f}",
        "rel_base_tariff": f"{record.rel_base_tariff:.4f}",
        "scheduling_css_tose": f"{record.scheduling_css_tose:.4f}",
        "p3_wheeling_charges": f"{record.p3_wheeling_charges:.4f}",
        "p3_wheeling_losses": f"{record.p3_wheeling_losses:.4f}",
        "p3_transmission_charges": f"{record.p3_transmission_charges:.4f}",
        "p3_transmission_losses": f"{record.p3_transmission_losses:.4f}",
        "p3_electricity_duty": f"{record.p3_electricity_duty:.4f}",
        "delivered_tariff": f"{record.delivered_tariff:.4f}",
        "per_unit_savings": f"{record.per_unit_savings:.4f}",
        "estimated_savings": f"{record.estimated_savings:,.2f}",
        "assured_savings": f"{record.assured_savings:,.2f}",
        "monthly_savings": f"{(record.estimated_savings / 12.0):,.2f}",
    }

    return JsonResponse(data)
