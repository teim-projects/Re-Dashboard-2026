from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, redirect
from django.db import connection
from django.contrib.auth.decorators import login_required
from django.db.utils import ProgrammingError
from collections import defaultdict
from datetime import datetime, date, timedelta
import json
import re

def normalize(col):
    """Normalize column name for comparison"""
    return re.sub(r'[^a-z0-9]+', '_', col.lower()).strip('_')

def _pick(col_map, *candidates):
    """Match candidate names against actual columns (case/space/dot insensitive)."""
    for cand in candidates:
        cand_norm = normalize(cand)
        for k, v in col_map.items():
            if normalize(k) == cand_norm:
                return v
    return None

@login_required
def wind_dashboard(request):
    """
    Executive Overview Dashboard for Wind Fleet
    Implements 12 Priority Visuals - Section 1: Executive Overview
    """
    user = request.user.username.lower()
    is_admin = request.user.is_superuser or user == 'admin'

    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        all_tables = [r[0] for r in cursor.fetchall()]

    if is_admin:
        gen_tables = [t for t in all_tables if t.endswith('_wind') and 'breakdown' not in t]
        bd_tables = [t for t in all_tables if 'breakdown' in t and t.endswith('_wind_breakdowndata')]
    else:
        gen_tables = [t for t in all_tables if t.startswith(user + '_') and t.endswith('_wind')]
        bd_tables = [t for t in all_tables if t.startswith(user + '_') and 'breakdown' in t]

    total_gen = 0.0
    ma_list = []
    plf_list = []
    wtg_set = set()
    total_downtime = 0.0
    zero_gen_wtgs = set()

    wtg_gens = defaultdict(float)
    wtg_ma_dict = defaultdict(list)
    wtg_plf_dict = defaultdict(list)
    monthly_gen = defaultdict(float)
    oem_gen = defaultdict(float)
    heatmap_matrix = defaultdict(lambda: defaultdict(float))
    all_months = set()

    for gt in gen_tables:
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{gt}`")
            cols = [r[0] for r in cursor.fetchall()]
        col_map = {normalize(c): c for c in cols}

        wtg_col = _pick(col_map, "location_no", "turbine_id", "wtg", "wtg_no", "loc_no", "wec", "location")
        gen_col = _pick(col_map, "wtg_production_kwh", "gen_kwh_day", "gen_kwh", "generation", "kwh")
        date_col = _pick(col_map, "date", "gen_date")
        ma_col = _pick(col_map, "wtg_availability", "machine_availability", "actual_ma", "corrected_ma")
        plf_col = _pick(col_map, "plf_wtg_efficiency", "plf", "monthly_plf")

        oem_name = "OEM"
        gt_lower = gt.lower()
        if "senvion" in gt_lower: oem_name = "Senvion"
        elif "regen" in gt_lower: oem_name = "Regen"
        elif "gamesa" in gt_lower: oem_name = "Gamesa"
        elif "inox" in gt_lower: oem_name = "Inox"
        elif "suzlon" in gt_lower: oem_name = "Suzlon"
        elif "windworld" in gt_lower: oem_name = "Windworld"

        if not wtg_col or not gen_col:
            continue

        with connection.cursor() as cursor:
            cursor.execute(f"""
                SELECT `{wtg_col}`, 
                       SUM(CAST(`{gen_col}` AS DECIMAL(15,2))) as s_gen,
                       AVG(CAST(`{ma_col}` AS DECIMAL(10,2))) as avg_ma,
                       AVG(CAST(`{plf_col}` AS DECIMAL(10,2))) as avg_plf
                FROM `{gt}`
                WHERE `{wtg_col}` IS NOT NULL AND `{wtg_col}` != ''
                GROUP BY `{wtg_col}`
            """)
            for w, g, ma, plf in cursor.fetchall():
                wtg_name = str(w).strip()
                wtg_set.add(wtg_name)
                g_val = float(g or 0)
                wtg_gens[wtg_name] += g_val
                oem_gen[oem_name] += g_val
                total_gen += g_val
                if ma is not None:
                    ma_val = float(ma)
                    if 0 <= ma_val <= 100:
                        wtg_ma_dict[wtg_name].append(ma_val)
                        ma_list.append(ma_val)
                if plf is not None:
                    plf_val = float(plf)
                    if 0 <= plf_val <= 100:
                        wtg_plf_dict[wtg_name].append(plf_val)
                        plf_list.append(plf_val)
                if g_val == 0:
                    zero_gen_wtgs.add(wtg_name)

        if date_col and gen_col:
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    SELECT SUBSTRING(`{date_col}`, 1, 7) as ym, SUM(CAST(`{gen_col}` AS DECIMAL(15,2)))
                    FROM `{gt}`
                    WHERE `{date_col}` IS NOT NULL AND `{date_col}` != ''
                    GROUP BY ym
                    ORDER BY ym ASC
                """)
                for ym, g in cursor.fetchall():
                    if ym and len(ym) == 7:
                        monthly_gen[ym] += float(g or 0)
                        all_months.add(ym)

        # Heatmap (Turbine vs Monthly availability)
        if date_col and ma_col:
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    SELECT `{wtg_col}`, SUBSTRING(`{date_col}`, 1, 7) as ym, AVG(CAST(`{ma_col}` AS DECIMAL(10,2)))
                    FROM `{gt}`
                    WHERE `{date_col}` IS NOT NULL AND `{date_col}` != ''
                    GROUP BY `{wtg_col}`, ym
                """)
                for w, ym, ma in cursor.fetchall():
                    if ma is not None and ym and len(ym) == 7:
                        heatmap_matrix[str(w).strip()][ym] = round(float(ma), 1)

    # Breakdown Downtime
    extended_breakdowns = []
    for bdt in bd_tables:
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{bdt}`")
            cols = [r[0] for r in cursor.fetchall()]
        col_map = {normalize(c): c for c in cols}
        dur_col = _pick(col_map, "total_duration", "duration", "hours")
        loc_col = _pick(col_map, "location", "loc_no", "location_no", "wtg", "wtg_no")
        err_col = _pick(col_map, "error_description", "error_details", "error_code", "cause")
        date_col = _pick(col_map, "date", "gen_date")
        act_col = _pick(col_map, "action_taken_remark", "action_taken", "remark")

        if dur_col:
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT SUM(CAST(`{dur_col}` AS DECIMAL(15,2))) FROM `{bdt}`")
                res = cursor.fetchone()[0]
                if res: total_downtime += float(res)

        if loc_col and err_col and dur_col:
            with connection.cursor() as cursor:
                act_sel = f", `{act_col}`" if act_col else ", ''"
                cursor.execute(f"""
                    SELECT `{loc_col}`, `{date_col}`, TRIM(`{err_col}`), CAST(`{dur_col}` AS DECIMAL(15,2)) {act_sel}
                    FROM `{bdt}`
                    WHERE CAST(`{dur_col}` AS DECIMAL(15,2)) >= 10.0
                    ORDER BY CAST(`{dur_col}` AS DECIMAL(15,2)) DESC
                    LIMIT 8
                """)
                for r in cursor.fetchall():
                    extended_breakdowns.append({
                        "wtg": r[0],
                        "date": str(r[1])[:10] if r[1] else "",
                        "cause": ' '.join(str(r[2]).split()),
                        "duration": float(r[3] or 0),
                        "action": r[4] if len(r) > 4 else ""
                    })

    # Calculations
    avg_fleet_ma = (sum(ma_list) / len(ma_list)) if ma_list else 0.0
    avg_fleet_plf = (sum(plf_list) / len(plf_list)) if plf_list else 0.0
    underperforming_wtgs = [w for w, g in wtg_gens.items() if wtg_ma_dict.get(w) and (sum(wtg_ma_dict[w])/len(wtg_ma_dict[w])) < 90.0]

    sorted_wtgs = sorted([{"wtg": k, "generation": round(v, 2)} for k, v in wtg_gens.items()], key=lambda x: x["generation"], reverse=True)
    top_10 = sorted_wtgs[:10]
    bottom_10 = sorted(sorted_wtgs[-10:], key=lambda x: x["generation"])
    top_25 = sorted_wtgs[:25]

    sorted_months = sorted(monthly_gen.keys())
    recent_months = sorted_months[-24:] if len(sorted_months) > 24 else sorted_months
    monthly_labels = recent_months
    monthly_values = [round(monthly_gen[m], 2) for m in recent_months]

    # OEM comparison
    oem_labels = list(oem_gen.keys())
    oem_values = [round(oem_gen[k], 2) for k in oem_labels]

    # Heatmap summary (Top 12 WTGs x recent 6 months)
    recent_6_months = sorted_months[-6:] if len(sorted_months) >= 6 else sorted_months
    heatmap_series = []
    top_wtg_names = [d["wtg"] for d in top_10]
    for w in top_wtg_names:
        row_data = []
        for m in recent_6_months:
            row_data.append({"x": m, "y": heatmap_matrix[w].get(m, round(avg_fleet_ma, 1))})
        heatmap_series.append({"name": w, "data": row_data})

    context = {
        "total_generation": round(total_gen, 2),
        "fleet_ma": round(avg_fleet_ma, 2),
        "fleet_plf": round(avg_fleet_plf, 2),
        "total_downtime": round(total_downtime, 1),
        "wtg_count": len(wtg_set),
        "zero_gen_count": len(zero_gen_wtgs),
        "underperforming_count": len(underperforming_wtgs),
        "top_10": top_10,
        "bottom_10": bottom_10,
        "top_25": top_25,
        "all_wtgs": sorted_wtgs,
        "top_10_json": json.dumps(top_10),
        "bottom_10_json": json.dumps(bottom_10),
        "top_25_json": json.dumps(top_25),
        "all_wtgs_json": json.dumps(sorted_wtgs),
        "monthly_trend_json": json.dumps({"labels": monthly_labels, "values": monthly_values}),
        "oem_comparison_json": json.dumps({"labels": oem_labels, "values": oem_values}),
        "heatmap_series_json": json.dumps(heatmap_series),
        "recent_months": recent_6_months,
        "extended_breakdowns": extended_breakdowns,
    }
    return render(request, 'wind_dashboard.html', context)

@login_required
def wind_summary1(request):
    table_name = "installation_summary_wind"
    data = {
        "capacity_by_state": [],
        "land_type_by_state": [],
        "wtg_generation": [],
        "power_sale": [],
    }
    table_exists = True  # flag for SweetAlert

    # Logged-in user → match against `customer` column
    customer = request.user.username

    try:
        with connection.cursor() as cursor:
            # Capacity by state (only this customer)
            cursor.execute(f"""
                SELECT state, SUM(capacity_mw) AS total_capacity
                FROM `{table_name}`
                WHERE customer = %s
                GROUP BY state
            """, [customer])
            data["capacity_by_state"] = cursor.fetchall()

            # Land type by state
            cursor.execute(f"""
                SELECT state, land, COUNT(*) AS land_count
                FROM `{table_name}`
                WHERE customer = %s
                GROUP BY state, land
            """, [customer])
            data["land_type_by_state"] = cursor.fetchall()

            # Estimated generation WTG wise
            cursor.execute(f"""
                SELECT wtg_location_no, avg_estimate_gen_kwh
                FROM `{table_name}`
                WHERE customer = %s
            """, [customer])
            data["wtg_generation"] = cursor.fetchall()

            # Power sale by state
            cursor.execute(f"""
                SELECT power_sale_details, state
                FROM `{table_name}`
                WHERE customer = %s
            """, [customer])
            data["power_sale"] = cursor.fetchall()

    except ProgrammingError:
        # Table not found → just return empty tables, no error
        table_exists = False

    return render(request, "wind_summary1.html", {
        "data": data,
        "table_exists": table_exists,
        "table_name": table_name
    })

import json
from django.shortcuts import render
from django.db import connection
from django.db.utils import ProgrammingError
from django.contrib.auth.decorators import login_required
import json
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db import connection
import json
@login_required
def wind_installation_summary2(request):
    # --- List of possible table names
    possible_tables = [
        "installation_summary_wind",
        "installation_summary_windmil",
        "installation_summary_W",
        "installation_summary_Wind",
        "installation_summary_WIND"
    ]

    # --- Get existing tables from database
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        db_tables = [row[0] for row in cursor.fetchall()]

    # --- Find first table that exists
    table_name = next((t for t in possible_tables if t in db_tables), None)

    # --- If no table exists, return empty response
    if not table_name:
        return render(request, "wind_installation_summary2.html", {
            "data": json.dumps({
                "power_sale_labels": [],
                "power_sale_counts": [],
                "land_labels": [],
                "land_counts": [],
            }),
            "wtg_locations": [],
            "oem_breakup": [],
            "no_data": True,
            "no_data_msg": "No installation summary data available."
        })

    # --- Current logged-in user name (match against `customer` column)
    customer = request.user.username

    # --- Data containers
    data = {
        "power_sale_labels": [],
        "power_sale_counts": [],
        "land_labels": [],
        "land_counts": [],
    }
    wtg_locations = []
    oem_breakup = []

    with connection.cursor() as cursor:
        # Power Sale
        cursor.execute(f"""
            SELECT 
                CASE 
                    WHEN power_sale_details = 'Private PPA' THEN 'Captive'
                    WHEN power_sale_details IN ('SECI', 'State Grid') THEN 'Sale FB'
                    ELSE 'Other'
                END AS category,
                COUNT(*) AS cnt
            FROM `{table_name}`
            WHERE customer = %s
            GROUP BY category
        """, [customer])
        for row in cursor.fetchall():
            data["power_sale_labels"].append(row[0])
            data["power_sale_counts"].append(row[1])

        # Land
        cursor.execute(f"""
            SELECT land, COUNT(*)
            FROM `{table_name}`
            WHERE customer = %s
            GROUP BY land
        """, [customer])
        for row in cursor.fetchall():
            data["land_labels"].append(row[0])
            data["land_counts"].append(row[1])

        # WTG Locations (top 10 by estimated generation)
        cursor.execute(f"""
            SELECT wtg_location_no, avg_estimate_gen_kwh
            FROM `{table_name}`
            WHERE customer = %s
            ORDER BY avg_estimate_gen_kwh DESC
            LIMIT 10
        """, [customer])
        wtg_locations = cursor.fetchall()

        # OEM Breakup
        cursor.execute(f"""
            SELECT capacity_mw, firm, make, COUNT(*)
            FROM `{table_name}`
            WHERE customer = %s
            GROUP BY capacity_mw, firm, make
        """, [customer])
        oem_breakup = cursor.fetchall()

    # --- Handle case: table exists but no rows
    no_data = (
        len(data["power_sale_labels"]) == 0 and
        len(data["land_labels"]) == 0 and
        len(wtg_locations) == 0 and
        len(oem_breakup) == 0
    )

    return render(request, "wind_installation_summary2.html", {
        "data": json.dumps(data),
        "wtg_locations": wtg_locations,
        "oem_breakup": oem_breakup,
        "no_data": no_data,
        "no_data_msg": "No installation summary records found." if no_data else ""
    })

from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
import json
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from accounts.models import Provider, EnergyType

import json
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
import json
from collections import defaultdict
from django.http import HttpResponse
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
import re
import json
from collections import defaultdict
from django.http import HttpResponse
from django.db import connection
from django.contrib.auth.decorators import login_required

import json
import re
from collections import defaultdict
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required


import json
import re
from collections import defaultdict
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required


def normalize(col):
    """Normalize column name for comparison"""
    return re.sub(r'[^a-z0-9]+', '_', col.lower()).strip('_')


def _pick(col_map, *candidates):
    """Match candidate names against actual columns (case/space/dot insensitive)."""
    for cand in candidates:
        cand_norm = normalize(cand)
        for k, v in col_map.items():
            if normalize(k) == cand_norm:
                return v
    return None


import json
import re
from collections import defaultdict
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required


def normalize(col):
    """Normalize column name for comparison"""
    return re.sub(r'[^a-z0-9]+', '_', col.lower()).strip('_')


def _pick(col_map, *candidates):
    """Match candidate names against actual columns (case/space/dot insensitive)."""
    for cand in candidates:
        cand_norm = normalize(cand)
        for k, v in col_map.items():
            if normalize(k) == cand_norm:
                return v
    return None


@login_required
def wind_generation_kwh(request):
    """
    Generation Analysis (kWh)
    Implements Priority Visuals:
    - Visual #1: Generation KPI Cards
    - Visual #2: Monthly / Daily Generation Line Chart
    - Visual #3: Top 10 / Bottom 10 Turbine Ranking Horizontal Bar Chart
    - Visual #5: Manufacturer-wise Generation Bar Chart
    - Full Data Table with sorting, searching, pagination & export
    """
    user = request.user.username.lower()
    is_admin = request.user.is_superuser or user == 'admin'

    if request.GET.get("clear_filters"):
        request.session.pop("wind_filters", None)

    saved = request.session.get("wind_filters", {})

    def get_or_saved_list(key):
        vals = request.GET.getlist(key)
        return vals if vals else saved.get(key, [])

    date_from = request.GET.get("date_from") or saved.get("date_from")
    date_to   = request.GET.get("date_to")   or saved.get("date_to")

    providers = get_or_saved_list("provider")
    customers = get_or_saved_list("customer")
    states    = get_or_saved_list("state")
    sites     = get_or_saved_list("site")
    wtgs      = get_or_saved_list("wtg")

    request.session["wind_filters"] = {
        "date_from": date_from,
        "date_to": date_to,
        "provider": providers,
        "customer": customers,
        "state": states,
        "site": sites,
        "wtg": wtgs,
    }
    request.session.modified = True

    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        db_tables = [r[0] for r in cursor.fetchall()]

    if is_admin:
        table_names = [t for t in db_tables if t.endswith('_wind') and 'breakdown' not in t]
    else:
        table_names = [t for t in db_tables if t.startswith(user + "_") and t.endswith("_wind")]

    if not table_names:
        return render(request, "wind_generation_kwh.html", {
            "chart_data": "[]",
            "top_10_json": "[]",
            "bottom_10_json": "[]",
            "top_25_json": "[]",
            "all_wtgs_json": "[]",
            "monthly_trend_json": "{}",
            "oem_comparison_json": "{}",
            "table_data": [],
            "total_generation": 0,
            "avg_generation": 0,
            "wtg_count": 0,
            "top_wtg": None,
            "bottom_wtg": None,
            "providers": [], "customers": [], "states": [], "sites": [], "wtgs": [],
            "selected_providers": providers, "selected_customers": customers,
            "selected_states": states, "selected_sites": sites, "selected_wtgs": wtgs,
            "date_from": date_from, "date_to": date_to,
            "no_data": True,
            "no_data_msg": "No wind generation data found."
        })

    wtg_sum = defaultdict(float)
    monthly_sum = defaultdict(float)
    oem_sum = defaultdict(float)
    wtg_oem_map = {}
    distincts = {k: set() for k in ["providers", "customers", "states", "sites", "wtgs"]}

    earliest_date = None
    latest_date = None

    for table_name in table_names:
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
            cols = [r[0] for r in cursor.fetchall()]
        col_map = {normalize(c): c for c in cols}

        wtg_col = _pick(col_map, "location_no", "turbine_id", "wtg", "wtg_no", "loc_no", "wec", "location")
        gen_col = _pick(col_map, "wtg_production_kwh", "gen_kwh_day", "gen_kwh", "generation", "kwh")
        date_col = _pick(col_map, "date", "gen_date")
        provider_col = _pick(col_map, "provider", "oem")
        customer_col = _pick(col_map, "customer", "customer_name")
        state_col = _pick(col_map, "state")
        site_col = _pick(col_map, "site", "wind_farm_name")

        if not wtg_col or not gen_col:
            continue

        oem_name = "Unknown OEM"
        t_lower = table_name.lower()
        if "senvion" in t_lower: oem_name = "Senvion"
        elif "regen" in t_lower: oem_name = "Regen"
        elif "gamesa" in t_lower: oem_name = "Gamesa"
        elif "inox" in t_lower: oem_name = "Inox"
        elif "suzlon" in t_lower: oem_name = "Suzlon"
        elif "windworld" in t_lower: oem_name = "Windworld"

        if date_col and (not date_from or not date_to):
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT MIN(`{date_col}`), MAX(`{date_col}`) FROM `{table_name}` WHERE `{date_col}` IS NOT NULL AND `{date_col}` != ''")
                d_min, d_max = cursor.fetchone()
                if d_min and (not earliest_date or str(d_min) < str(earliest_date)):
                    earliest_date = str(d_min)[:10]
                if d_max and (not latest_date or str(d_max) > str(latest_date)):
                    latest_date = str(d_max)[:10]

        base_conditions, base_params = [], []
        if date_from and date_to and date_col:
            base_conditions.append(f"`{date_col}` BETWEEN %s AND %s")
            base_params.extend([date_from, date_to])

        def add_in_filter(col, values, conds, parms):
            if col and values:
                placeholders = ",".join(["%s"] * len(values))
                conds.append(f"`{col}` IN ({placeholders})")
                parms.extend(values)

        add_in_filter(provider_col, providers, base_conditions, base_params)
        add_in_filter(customer_col, customers, base_conditions, base_params)
        add_in_filter(state_col, states, base_conditions, base_params)
        add_in_filter(site_col, sites, base_conditions, base_params)
        add_in_filter(wtg_col, wtgs, base_conditions, base_params)

        cond_wtg = list(base_conditions)
        params_wtg = list(base_params)
        cond_wtg.append(f"`{wtg_col}` IS NOT NULL AND `{wtg_col}` != ''")
        where_wtg = f"WHERE {' AND '.join(cond_wtg)}"

        query = f"""
            SELECT `{wtg_col}`, SUM(CAST(`{gen_col}` AS DECIMAL(15,2)))
            FROM `{table_name}`
            {where_wtg}
            GROUP BY `{wtg_col}`
        """
        with connection.cursor() as cursor:
            cursor.execute(query, params_wtg)
            for w, g in cursor.fetchall():
                wtg_key = str(w).strip()
                val = float(g or 0)
                wtg_sum[wtg_key] += val
                oem_sum[oem_name] += val
                wtg_oem_map[wtg_key] = oem_name

        if date_col:
            cond_m = list(base_conditions)
            params_m = list(base_params)
            cond_m.append(f"`{date_col}` IS NOT NULL AND `{date_col}` != ''")
            where_m = f"WHERE {' AND '.join(cond_m)}"

            m_query = f"""
                SELECT SUBSTRING(`{date_col}`, 1, 7) AS ym, SUM(CAST(`{gen_col}` AS DECIMAL(15,2)))
                FROM `{table_name}`
                {where_m}
                GROUP BY ym
                ORDER BY ym ASC
            """
            with connection.cursor() as cursor:
                cursor.execute(m_query, params_m)
                for ym, g in cursor.fetchall():
                    if ym and len(ym) == 7:
                        monthly_sum[ym] += float(g or 0)

        def dist(col):
            if not col: return []
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT DISTINCT `{col}` FROM `{table_name}` WHERE `{col}` IS NOT NULL AND `{col}` != '' ORDER BY `{col}`")
                return [str(r[0]) for r in cursor.fetchall()]

        distincts["providers"].update(dist(provider_col))
        distincts["customers"].update(dist(customer_col))
        distincts["states"].update(dist(state_col))
        distincts["sites"].update(dist(site_col))
        distincts["wtgs"].update(dist(wtg_col))

    all_wtgs = sorted([{"wtg": k, "generation": round(v, 2), "oem": wtg_oem_map.get(k, "OEM")} for k, v in wtg_sum.items()], key=lambda x: x["generation"], reverse=True)
    total_generation = sum(wtg_sum.values())
    wtg_count = len(all_wtgs)
    avg_generation = (total_generation / wtg_count) if wtg_count > 0 else 0

    top_10 = all_wtgs[:10]
    bottom_10 = sorted(all_wtgs[-10:], key=lambda x: x["generation"])
    top_25 = all_wtgs[:25]

    table_data = []
    for rank, d in enumerate(all_wtgs, 1):
        share = (d["generation"] / total_generation * 100) if total_generation > 0 else 0
        diff_avg = ((d["generation"] - avg_generation) / avg_generation * 100) if avg_generation > 0 else 0
        status = "Optimal" if d["generation"] >= avg_generation else ("Underperforming" if d["generation"] < (avg_generation * 0.7) else "Normal")
        table_data.append({
            "rank": rank,
            "wtg_no": d["wtg"],
            "oem": d["oem"],
            "generation": d["generation"],
            "share": round(share, 2),
            "diff_avg": round(diff_avg, 1),
            "status": status
        })

    sorted_months = sorted(monthly_sum.keys())
    monthly_labels = sorted_months[-36:] if len(sorted_months) > 36 else sorted_months
    monthly_values = [round(monthly_sum[m], 2) for m in monthly_labels]

    oem_labels = list(oem_sum.keys())
    oem_values = [round(oem_sum[k], 2) for k in oem_labels]

    return render(request, "wind_generation_kwh.html", {
        "chart_data": json.dumps(all_wtgs),
        "top_10_json": json.dumps(top_10),
        "bottom_10_json": json.dumps(bottom_10),
        "top_25_json": json.dumps(top_25),
        "all_wtgs_json": json.dumps(all_wtgs),
        "monthly_trend_json": json.dumps({"labels": monthly_labels, "values": monthly_values}),
        "oem_comparison_json": json.dumps({"labels": oem_labels, "values": oem_values}),
        "table_data": table_data,
        "total_generation": round(total_generation, 2),
        "avg_generation": round(avg_generation, 2),
        "wtg_count": wtg_count,
        "top_wtg": top_10[0] if top_10 else None,
        "bottom_wtg": bottom_10[0] if bottom_10 else None,

        "providers": sorted(distincts["providers"]),
        "customers": sorted(distincts["customers"]),
        "states": sorted(distincts["states"]),
        "sites": sorted(distincts["sites"]),
        "wtgs": sorted(distincts["wtgs"]),

        "selected_providers": providers,
        "selected_customers": customers,
        "selected_states": states,
        "selected_sites": sites,
        "selected_wtgs": wtgs,

        "date_from": date_from or earliest_date,
        "date_to": date_to or latest_date,
    })

@login_required
def wind_generation_hours(request):
    username = request.user.username.lower()
    is_admin = request.user.is_superuser or username == "admin"

    if request.GET.get("clear_filters"):
        request.session.pop("wind_filters", None)

    saved = request.session.get("wind_filters", {})
    def get_or_saved_list(key):
        vals = request.GET.getlist(key)
        return vals if vals else saved.get(key, [])

    date_from = request.GET.get("date_from") or saved.get("date_from")
    date_to   = request.GET.get("date_to")   or saved.get("date_to")
    providers = get_or_saved_list("provider")
    customers = get_or_saved_list("customer")
    states    = get_or_saved_list("state")
    sites     = get_or_saved_list("site")
    wtgs      = get_or_saved_list("wtg")

    request.session["wind_filters"] = {
        "date_from": date_from, "date_to": date_to,
        "provider": providers, "customer": customers,
        "state": states, "site": sites, "wtg": wtgs,
    }
    request.session.modified = True

    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES")
        db_tables = [row[0] for row in cursor.fetchall()]

    if is_admin:
        table_names = [t for t in db_tables if t.endswith("_wind") and not t.endswith("_breakdowndata")]
    else:
        table_names = [t for t in db_tables if t.startswith(username + "_") and t.endswith("_wind") and not t.endswith("_breakdowndata")]

    def _normalize(s):
        return s.lower().replace(" ", "").replace("_", "").replace(".", "").replace("(", "").replace(")", "").replace("%", "")

    def _pick(cmap, *candidates):
        for cand in candidates:
            c_norm = _normalize(cand)
            if c_norm in cmap:
                return cmap[c_norm]
        return None

    if not date_from or not date_to:
        min_dates, max_dates = [], []
        for t in table_names:
            with connection.cursor() as cursor:
                cursor.execute(f"SHOW COLUMNS FROM `{t}`")
                cols = {c[0].lower(): c[0] for c in cursor.fetchall()}
                col_norm = {_normalize(c): c for c in cols.values()}
                dcol = _pick(col_norm, "date", "gen_date", "reading_date", "day_date")
                if dcol:
                    cursor.execute(f"SELECT MIN(`{dcol}`), MAX(`{dcol}`) FROM `{t}` WHERE `{dcol}` IS NOT NULL")
                    row = cursor.fetchone()
                    if row and row[0] and row[1]:
                        min_dates.append(str(row[0]))
                        max_dates.append(str(row[1]))
        if min_dates and max_dates:
            date_from = date_from or min(min_dates)
            date_to = date_to or max(max_dates)

    wtg_hrs_list = defaultdict(list)
    wtg_meta = {}
    monthly_hrs = defaultdict(list)
    distincts = {"providers": set(), "customers": set(), "states": set(), "sites": set(), "wtgs": set()}

    for t in table_names:
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{t}`")
            cols = [c[0] for c in cursor.fetchall()]
        col_norm = {_normalize(c): c for c in cols}

        wtg_col = _pick(col_norm, "location_no", "turbine_id", "loc_no", "wec", "wtg", "wtg_no", "locno", "turbine")
        date_col = _pick(col_norm, "date", "gen_date", "reading_date", "day_date")
        hrs_col = _pick(col_norm, "production_hours", "gen_hours", "operating_hours", "ohrs", "genhrs", "generationhours")
        oem_col = _pick(col_norm, "provider", "oem", "oemprovider", "oem_name")
        site_col = _pick(col_norm, "site", "sitename", "location", "plant", "park")
        state_col = _pick(col_norm, "state", "statename", "st")
        month_col = _pick(col_norm, "month", "mon")

        if not wtg_col or not hrs_col:
            continue

        select_cols = [f"`{wtg_col}`", f"`{hrs_col}`"]
        if date_col: select_cols.append(f"`{date_col}`")
        if oem_col: select_cols.append(f"`{oem_col}`")
        if site_col: select_cols.append(f"`{site_col}`")
        if state_col: select_cols.append(f"`{state_col}`")
        if month_col: select_cols.append(f"`{month_col}`")

        where_conds = [f"`{wtg_col}` IS NOT NULL AND `{wtg_col}` != ''"]
        params = []
        if date_col and date_from and date_to:
            where_conds.append(f"`{date_col}` BETWEEN %s AND %s")
            params.extend([date_from, date_to])

        def add_in(col, vals):
            if col and vals:
                q = ",".join(["%s"] * len(vals))
                where_conds.append(f"`{col}` IN ({q})")
                params.extend(vals)

        add_in(oem_col, providers)
        add_in(state_col, states)
        add_in(site_col, sites)
        add_in(wtg_col, wtgs)

        where_clause = " WHERE " + " AND ".join(where_conds)
        sql = f"SELECT {', '.join(select_cols)} FROM `{t}` {where_clause}"

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()

        idx = {c.strip("`"): i for i, c in enumerate(select_cols)}

        for r in rows:
            wtg_val = str(r[idx[wtg_col]]).strip()
            if not wtg_val or wtg_val.lower() in ("none", "total", "all wtg"):
                continue

            val = None
            if r[idx[hrs_col]] not in (None, ""):
                try: val = float(r[idx[hrs_col]])
                except: pass

            if val is not None and val > 0:
                wtg_hrs_list[wtg_val].append(val)

            if wtg_val not in wtg_meta:
                wtg_meta[wtg_val] = {
                    "oem": str(r[idx[oem_col]]).strip() if oem_col and r[idx[oem_col]] else ("Senvion" if "senvion" in t else ("Regen" if "regen" in t else "Wind")),
                    "site": str(r[idx[site_col]]).strip() if site_col and r[idx[site_col]] else "Site-1",
                    "state": str(r[idx[state_col]]).strip() if state_col and r[idx[state_col]] else "Default"
                }

            m_key = None
            if date_col and r[idx[date_col]]:
                m_key = str(r[idx[date_col]])[:7]
            elif month_col and r[idx[month_col]]:
                m_key = str(r[idx[month_col]]).strip()

            if m_key and val is not None and val > 0:
                monthly_hrs[m_key].append(val)

        def add_distinct(col, key):
            if not col: return
            with connection.cursor() as cur:
                cur.execute(f"SELECT DISTINCT `{col}` FROM `{t}` WHERE `{col}` IS NOT NULL AND `{col}` != ''")
                for r_ in cur.fetchall():
                    distincts[key].add(str(r_[0]).strip())

        add_distinct(oem_col, "providers")
        add_distinct(state_col, "states")
        add_distinct(site_col, "sites")
        add_distinct(wtg_col, "wtgs")

    wtg_data = []
    for w, vals in wtg_hrs_list.items():
        tot_hrs = round(sum(vals), 2)
        daily_avg = round(tot_hrs / len(vals), 2) if vals else 0.0
        util_pct = round((daily_avg / 24.0) * 100.0, 1) if daily_avg else 0.0
        meta = wtg_meta.get(w, {"oem": "Wind", "site": "-", "state": "-"})
        wtg_data.append({
            "wtg": w,
            "total_hrs": tot_hrs,
            "daily_avg": daily_avg,
            "util_pct": util_pct,
            "oem": meta["oem"],
            "site": meta["site"],
            "state": meta["state"],
            "status": "Optimal" if daily_avg >= 20.0 else ("Moderate" if daily_avg >= 15.0 else "Low")
        })

    wtg_data.sort(key=lambda x: x["total_hrs"], reverse=True)
    for rank, item in enumerate(wtg_data, 1):
        item["rank"] = rank

    fleet_tot_hrs = sum(d["total_hrs"] for d in wtg_data)
    fleet_daily_avg = round(sum(d["daily_avg"] for d in wtg_data) / len(wtg_data), 2) if wtg_data else 0.0
    fleet_util = round((fleet_daily_avg / 24.0) * 100.0, 1) if fleet_daily_avg else 0.0
    max_wtg = wtg_data[0] if wtg_data else {"wtg": "-", "total_hrs": 0}

    sorted_months = sorted(monthly_hrs.keys())[-12:]
    month_series = [round(sum(monthly_hrs[m]), 1) for m in sorted_months]

    context = {
        "kpi_total_hrs": fleet_tot_hrs,
        "kpi_daily_avg": fleet_daily_avg,
        "kpi_util_factor": fleet_util,
        "kpi_max_wtg": max_wtg["wtg"],
        "kpi_max_val": max_wtg["total_hrs"],
        "kpi_total_wtgs": len(wtg_data),

        "table_data": wtg_data,
        "all_wtgs_json": json.dumps(wtg_data),

        "monthly_cats_json": json.dumps(sorted_months),
        "monthly_gen_json": json.dumps(month_series),

        # Filters
        "date_from": date_from,
        "date_to": date_to,
        "providers": sorted(distincts["providers"]),
        "states": sorted(distincts["states"]),
        "sites": sorted(distincts["sites"]),
        "wtgs": sorted(distincts["wtgs"]),
        "selected_providers": providers,
        "selected_states": states,
        "selected_sites": sites,
        "selected_wtgs": wtgs,
    }

    return render(request, "wind_genration_hovers.html", context)


def _pick(col_map, *candidates):
    """Return actual-cased column name if it matches any of the candidates"""
    for c in candidates:
        lc = c.lower()
        if lc in col_map:
            return col_map[lc]
    return None


@login_required
def wind_avg_genration(request):
    username = request.user.username.lower()
    is_admin = request.user.is_superuser or username == "admin"

    if request.GET.get("clear_filters"):
        request.session.pop("wind_filters", None)

    saved = request.session.get("wind_filters", {})
    def get_or_saved_list(key):
        vals = request.GET.getlist(key)
        return vals if vals else saved.get(key, [])

    date_from = request.GET.get("date_from") or saved.get("date_from")
    date_to   = request.GET.get("date_to")   or saved.get("date_to")
    providers = get_or_saved_list("provider")
    customers = get_or_saved_list("customer")
    states    = get_or_saved_list("state")
    sites     = get_or_saved_list("site")
    wtgs      = get_or_saved_list("wtg")

    request.session["wind_filters"] = {
        "date_from": date_from, "date_to": date_to,
        "provider": providers, "customer": customers,
        "state": states, "site": sites, "wtg": wtgs,
    }
    request.session.modified = True

    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES")
        db_tables = [row[0] for row in cursor.fetchall()]

    if is_admin:
        table_names = [t for t in db_tables if t.endswith("_wind") and not t.endswith("_breakdowndata")]
    else:
        table_names = [t for t in db_tables if t.startswith(username + "_") and t.endswith("_wind") and not t.endswith("_breakdowndata")]

    def _normalize(s):
        return s.lower().replace(" ", "").replace("_", "").replace(".", "").replace("(", "").replace(")", "").replace("%", "")

    def _pick(cmap, *candidates):
        for cand in candidates:
            c_norm = _normalize(cand)
            if c_norm in cmap:
                return cmap[c_norm]
        return None

    if not date_from or not date_to:
        min_dates, max_dates = [], []
        for t in table_names:
            with connection.cursor() as cursor:
                cursor.execute(f"SHOW COLUMNS FROM `{t}`")
                cols = {c[0].lower(): c[0] for c in cursor.fetchall()}
                col_norm = {_normalize(c): c for c in cols.values()}
                dcol = _pick(col_norm, "date", "gen_date", "reading_date", "day_date")
                if dcol:
                    cursor.execute(f"SELECT MIN(`{dcol}`), MAX(`{dcol}`) FROM `{t}` WHERE `{dcol}` IS NOT NULL")
                    row = cursor.fetchone()
                    if row and row[0] and row[1]:
                        min_dates.append(str(row[0]))
                        max_dates.append(str(row[1]))
        if min_dates and max_dates:
            date_from = date_from or min(min_dates)
            date_to = date_to or max(max_dates)

    wtg_gen_list = defaultdict(list)
    wtg_meta = {}
    monthly_gen = defaultdict(list)
    distincts = {"providers": set(), "customers": set(), "states": set(), "sites": set(), "wtgs": set()}

    for t in table_names:
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{t}`")
            cols = [c[0] for c in cursor.fetchall()]
        col_norm = {_normalize(c): c for c in cols}

        wtg_col = _pick(col_norm, "location_no", "turbine_id", "loc_no", "wec", "wtg", "wtg_no", "locno", "turbine")
        date_col = _pick(col_norm, "date", "gen_date", "reading_date", "day_date")
        gen_col = _pick(col_norm, "wtg_production_kwh", "gen_kwh_day", "generation_kwh", "genkwh", "units")
        plf_col = _pick(col_norm, "plf_wtg_efficiency", "plf", "monthly_plf", "cf")
        oem_col = _pick(col_norm, "provider", "oem", "oemprovider", "oem_name")
        site_col = _pick(col_norm, "site", "sitename", "location", "plant", "park")
        state_col = _pick(col_norm, "state", "statename", "st")
        month_col = _pick(col_norm, "month", "mon")

        if not wtg_col or not gen_col:
            continue

        select_cols = [f"`{wtg_col}`", f"`{gen_col}`"]
        if plf_col: select_cols.append(f"`{plf_col}`")
        if date_col: select_cols.append(f"`{date_col}`")
        if oem_col: select_cols.append(f"`{oem_col}`")
        if site_col: select_cols.append(f"`{site_col}`")
        if state_col: select_cols.append(f"`{state_col}`")
        if month_col: select_cols.append(f"`{month_col}`")

        where_conds = [f"`{wtg_col}` IS NOT NULL AND `{wtg_col}` != ''"]
        params = []
        if date_col and date_from and date_to:
            where_conds.append(f"`{date_col}` BETWEEN %s AND %s")
            params.extend([date_from, date_to])

        def add_in(col, vals):
            if col and vals:
                q = ",".join(["%s"] * len(vals))
                where_conds.append(f"`{col}` IN ({q})")
                params.extend(vals)

        add_in(oem_col, providers)
        add_in(state_col, states)
        add_in(site_col, sites)
        add_in(wtg_col, wtgs)

        where_clause = " WHERE " + " AND ".join(where_conds)
        sql = f"SELECT {', '.join(select_cols)} FROM `{t}` {where_clause}"

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()

        idx = {c.strip("`"): i for i, c in enumerate(select_cols)}

        for r in rows:
            wtg_val = str(r[idx[wtg_col]]).strip()
            if not wtg_val or wtg_val.lower() in ("none", "total", "all wtg"):
                continue

            gval = None
            if r[idx[gen_col]] not in (None, ""):
                try: gval = float(r[idx[gen_col]])
                except: pass

            pval = None
            if plf_col and r[idx[plf_col]] not in (None, ""):
                try: pval = float(r[idx[plf_col]])
                except: pass

            if gval is not None and gval > 0:
                wtg_gen_list[wtg_val].append({"gen": gval, "plf": pval})

            if wtg_val not in wtg_meta:
                wtg_meta[wtg_val] = {
                    "oem": str(r[idx[oem_col]]).strip() if oem_col and r[idx[oem_col]] else ("Senvion" if "senvion" in t else ("Regen" if "regen" in t else "Wind")),
                    "site": str(r[idx[site_col]]).strip() if site_col and r[idx[site_col]] else "Site-1",
                    "state": str(r[idx[state_col]]).strip() if state_col and r[idx[state_col]] else "Default"
                }

            m_key = None
            if date_col and r[idx[date_col]]:
                m_key = str(r[idx[date_col]])[:7]
            elif month_col and r[idx[month_col]]:
                m_key = str(r[idx[month_col]]).strip()

            if m_key and gval is not None and gval > 0:
                monthly_gen[m_key].append(gval)

        def add_distinct(col, key):
            if not col: return
            with connection.cursor() as cur:
                cur.execute(f"SELECT DISTINCT `{col}` FROM `{t}` WHERE `{col}` IS NOT NULL AND `{col}` != ''")
                for r_ in cur.fetchall():
                    distincts[key].add(str(r_[0]).strip())

        add_distinct(oem_col, "providers")
        add_distinct(state_col, "states")
        add_distinct(site_col, "sites")
        add_distinct(wtg_col, "wtgs")

    wtg_data = []
    for w, recs in wtg_gen_list.items():
        gen_vals = [x["gen"] for x in recs]
        tot_kwh = sum(gen_vals)
        daily_avg = round(tot_kwh / len(gen_vals), 2) if gen_vals else 0.0
        tot_mwh = round(tot_kwh / 1000.0, 2)
        plf_vals = [x["plf"] for x in recs if x["plf"] is not None]
        avg_plf = round(sum(plf_vals) / len(plf_vals), 2) if plf_vals else round((daily_avg / (2000.0 * 24.0)) * 100.0, 1)
        meta = wtg_meta.get(w, {"oem": "Wind", "site": "-", "state": "-"})
        wtg_data.append({
            "wtg": w,
            "daily_avg": daily_avg,
            "total_mwh": tot_mwh,
            "plf": avg_plf,
            "oem": meta["oem"],
            "site": meta["site"],
            "state": meta["state"],
            "status": "High" if daily_avg >= 10000 else ("Medium" if daily_avg >= 6000 else "Low")
        })

    wtg_data.sort(key=lambda x: x["daily_avg"], reverse=True)
    for rank, item in enumerate(wtg_data, 1):
        item["rank"] = rank

    fleet_daily_avg = round(sum(d["daily_avg"] for d in wtg_data) / len(wtg_data), 2) if wtg_data else 0.0
    fleet_total_mwh = sum(d["total_mwh"] for d in wtg_data)
    fleet_plf = round(sum(d["plf"] for d in wtg_data) / len(wtg_data), 2) if wtg_data else 0.0
    peak_wtg = wtg_data[0] if wtg_data else {"wtg": "-", "daily_avg": 0}

    sorted_months = sorted(monthly_gen.keys())[-12:]
    month_series = [round(sum(monthly_gen[m]) / len(monthly_gen[m]), 2) if monthly_gen[m] else 0.0 for m in sorted_months]

    context = {
        "kpi_daily_avg": fleet_daily_avg,
        "kpi_peak_wtg": peak_wtg["wtg"],
        "kpi_peak_val": peak_wtg["daily_avg"],
        "kpi_total_mwh": fleet_total_mwh,
        "kpi_fleet_plf": fleet_plf,
        "kpi_total_wtgs": len(wtg_data),

        "table_data": wtg_data,
        "all_wtgs_json": json.dumps(wtg_data),

        "monthly_cats_json": json.dumps(sorted_months),
        "monthly_avg_json": json.dumps(month_series),

        # Filters
        "date_from": date_from,
        "date_to": date_to,
        "providers": sorted(distincts["providers"]),
        "states": sorted(distincts["states"]),
        "sites": sorted(distincts["sites"]),
        "wtgs": sorted(distincts["wtgs"]),
        "selected_providers": providers,
        "selected_states": states,
        "selected_sites": sites,
        "selected_wtgs": wtgs,
    }

    return render(request, "wind_avg_genration.html", context)


def _pick(col_map, *candidates):
    def normalize(name):
        return (
            name.lower()
            .replace(".", "")
            .replace("%", "")
            .replace(" ", "")
            .replace("_", "")
            .strip()
        )
    for c in candidates:
        norm_c = normalize(c)
        for actual in col_map:
            if normalize(actual) == norm_c:
                return col_map[actual]
    return None


def parse_date_like(v):
    if isinstance(v, date):
        return v
    if isinstance(v, datetime):
        return v.date()

    formats = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d-%b-%Y", "%d.%m.%Y")
    for fmt in formats:
        try:
            return datetime.strptime(str(v).strip(), fmt).date()
        except:
            continue

    try:
        parts = str(v).replace("/", "-").replace(".", "-").split("-")
        if len(parts) == 3:
            if len(parts[0]) == 4:
                return date(int(parts[0]), int(parts[1]), int(parts[2]))
            else:
                return date(int(parts[2]), int(parts[1]), int(parts[0]))
    except:
        pass

    return None


def to_hours(value):
    try:
        val = float(value)
        if 0 <= val <= 24:
            return val
        if 24 < val <= 1440:
            return val / 60.0
    except:
        return 0.0
    return 0.0


@login_required
def wind_Grid_Availability_and_Machine(request):
    username = request.user.username.lower()
    is_admin = request.user.is_superuser or username == "admin"

    if request.GET.get("clear_filters"):
        request.session.pop("wind_filters", None)

    saved = request.session.get("wind_filters", {})
    def get_or_saved_list(key):
        vals = request.GET.getlist(key)
        return vals if vals else saved.get(key, [])

    date_from = request.GET.get("date_from") or saved.get("date_from")
    date_to   = request.GET.get("date_to")   or saved.get("date_to")
    providers = get_or_saved_list("provider")
    customers = get_or_saved_list("customer")
    states    = get_or_saved_list("state")
    sites     = get_or_saved_list("site")
    wtgs      = get_or_saved_list("wtg")

    request.session["wind_filters"] = {
        "date_from": date_from, "date_to": date_to,
        "provider": providers, "customer": customers,
        "state": states, "site": sites, "wtg": wtgs,
    }
    request.session.modified = True

    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES")
        db_tables = [row[0] for row in cursor.fetchall()]

    if is_admin:
        table_names = [t for t in db_tables if t.endswith("_wind") and not t.endswith("_breakdowndata")]
    else:
        table_names = [t for t in db_tables if t.startswith(username + "_") and t.endswith("_wind") and not t.endswith("_breakdowndata")]

    def _normalize(s):
        return s.lower().replace(" ", "").replace("_", "").replace(".", "").replace("(", "").replace(")", "").replace("%", "")

    def _pick(cmap, *candidates):
        for cand in candidates:
            c_norm = _normalize(cand)
            if c_norm in cmap:
                return cmap[c_norm]
        return None

    if not date_from or not date_to:
        min_dates, max_dates = [], []
        for t in table_names:
            with connection.cursor() as cursor:
                cursor.execute(f"SHOW COLUMNS FROM `{t}`")
                cols = {c[0].lower(): c[0] for c in cursor.fetchall()}
                col_norm = {_normalize(c): c for c in cols.values()}
                dcol = _pick(col_norm, "date", "gen_date", "reading_date", "day_date")
                if dcol:
                    cursor.execute(f"SELECT MIN(`{dcol}`), MAX(`{dcol}`) FROM `{t}` WHERE `{dcol}` IS NOT NULL")
                    row = cursor.fetchone()
                    if row and row[0] and row[1]:
                        min_dates.append(str(row[0]))
                        max_dates.append(str(row[1]))
        if min_dates and max_dates:
            date_from = date_from or min(min_dates)
            date_to = date_to or max(max_dates)

    wtg_ma_list = defaultdict(list)
    wtg_int_list = defaultdict(list)
    wtg_ext_list = defaultdict(list)
    wtg_meta = {}
    monthly_ma = defaultdict(list)
    monthly_int = defaultdict(list)
    monthly_ext = defaultdict(list)
    distincts = {"providers": set(), "customers": set(), "states": set(), "sites": set(), "wtgs": set()}

    for t in table_names:
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{t}`")
            cols = [c[0] for c in cursor.fetchall()]
        col_norm = {_normalize(c): c for c in cols}

        wtg_col = _pick(col_norm, "location_no", "turbine_id", "loc_no", "wec", "wtg", "wtg_no", "locno", "turbine")
        date_col = _pick(col_norm, "date", "gen_date", "reading_date", "day_date")
        ma_col = _pick(col_norm, "wtg_availability", "machine_availability", "actual_ma", "corrected_ma", "ma")
        int_col = _pick(col_norm, "int_grid_availability", "internal_grid_availability", "iga", "internalgridavailability")
        ext_col = _pick(col_norm, "ext_grid_availability", "external_grid_availability", "ega", "externalgridavailability", "ga")
        oem_col = _pick(col_norm, "provider", "oem", "oemprovider", "oem_name")
        site_col = _pick(col_norm, "site", "sitename", "location", "plant", "park")
        state_col = _pick(col_norm, "state", "statename", "st")
        month_col = _pick(col_norm, "month", "mon")

        if not wtg_col:
            continue

        select_cols = [f"`{wtg_col}`"]
        if ma_col: select_cols.append(f"`{ma_col}`")
        if int_col: select_cols.append(f"`{int_col}`")
        if ext_col: select_cols.append(f"`{ext_col}`")
        if date_col: select_cols.append(f"`{date_col}`")
        if oem_col: select_cols.append(f"`{oem_col}`")
        if site_col: select_cols.append(f"`{site_col}`")
        if state_col: select_cols.append(f"`{state_col}`")
        if month_col: select_cols.append(f"`{month_col}`")

        where_conds = [f"`{wtg_col}` IS NOT NULL AND `{wtg_col}` != ''"]
        params = []
        if date_col and date_from and date_to:
            where_conds.append(f"`{date_col}` BETWEEN %s AND %s")
            params.extend([date_from, date_to])

        def add_in(col, vals):
            if col and vals:
                q = ",".join(["%s"] * len(vals))
                where_conds.append(f"`{col}` IN ({q})")
                params.extend(vals)

        add_in(oem_col, providers)
        add_in(state_col, states)
        add_in(site_col, sites)
        add_in(wtg_col, wtgs)

        where_clause = " WHERE " + " AND ".join(where_conds)
        sql = f"SELECT {', '.join(select_cols)} FROM `{t}` {where_clause}"

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()

        idx = {c.strip("`"): i for i, c in enumerate(select_cols)}

        for r in rows:
            wtg_val = str(r[idx[wtg_col]]).strip()
            if not wtg_val or wtg_val.lower() in ("none", "total", "all wtg"):
                continue

            mval, ival, eval_ = None, None, None
            if ma_col and r[idx[ma_col]] not in (None, ""):
                try: mval = float(r[idx[ma_col]])
                except: pass
            if int_col and r[idx[int_col]] not in (None, ""):
                try: ival = float(r[idx[int_col]])
                except: pass
            if ext_col and r[idx[ext_col]] not in (None, ""):
                try: eval_ = float(r[idx[ext_col]])
                except: pass

            if mval is not None and mval > 0: wtg_ma_list[wtg_val].append(mval)
            if ival is not None and ival > 0: wtg_int_list[wtg_val].append(ival)
            if eval_ is not None and eval_ > 0: wtg_ext_list[wtg_val].append(eval_)

            if wtg_val not in wtg_meta:
                wtg_meta[wtg_val] = {
                    "oem": str(r[idx[oem_col]]).strip() if oem_col and r[idx[oem_col]] else ("Senvion" if "senvion" in t else ("Regen" if "regen" in t else "Wind")),
                    "site": str(r[idx[site_col]]).strip() if site_col and r[idx[site_col]] else "Site-1",
                    "state": str(r[idx[state_col]]).strip() if state_col and r[idx[state_col]] else "Default"
                }

            m_key = None
            if date_col and r[idx[date_col]]:
                m_key = str(r[idx[date_col]])[:7]
            elif month_col and r[idx[month_col]]:
                m_key = str(r[idx[month_col]]).strip()

            if m_key:
                if mval is not None and mval > 0: monthly_ma[m_key].append(mval)
                if ival is not None and ival > 0: monthly_int[m_key].append(ival)
                if eval_ is not None and eval_ > 0: monthly_ext[m_key].append(eval_)

        def add_distinct(col, key):
            if not col: return
            with connection.cursor() as cur:
                cur.execute(f"SELECT DISTINCT `{col}` FROM `{t}` WHERE `{col}` IS NOT NULL AND `{col}` != ''")
                for r_ in cur.fetchall():
                    distincts[key].add(str(r_[0]).strip())

        add_distinct(oem_col, "providers")
        add_distinct(state_col, "states")
        add_distinct(site_col, "sites")
        add_distinct(wtg_col, "wtgs")

    all_wtgs = sorted(set(list(wtg_ma_list.keys()) + list(wtg_int_list.keys()) + list(wtg_ext_list.keys())))
    wtg_data = []
    for w in all_wtgs:
        m_avg = round(sum(wtg_ma_list[w]) / len(wtg_ma_list[w]), 2) if wtg_ma_list[w] else 0.0
        i_avg = round(sum(wtg_int_list[w]) / len(wtg_int_list[w]), 2) if wtg_int_list[w] else 0.0
        e_avg = round(sum(wtg_ext_list[w]) / len(wtg_ext_list[w]), 2) if wtg_ext_list[w] else 0.0
        c_avg = round((m_avg * i_avg * e_avg) / 10000.0, 2) if (m_avg and i_avg and e_avg) else max(m_avg, i_avg, e_avg)
        meta = wtg_meta.get(w, {"oem": "Wind", "site": "-", "state": "-"})
        wtg_data.append({
            "wtg": w,
            "ma": m_avg,
            "int_ga": i_avg,
            "ext_ga": e_avg,
            "comb_ga": c_avg,
            "oem": meta["oem"],
            "site": meta["site"],
            "state": meta["state"],
            "status": "Optimal" if c_avg >= 95.0 else ("Moderate" if c_avg >= 90.0 else "Low")
        })

    wtg_data.sort(key=lambda x: x["comb_ga"], reverse=True)
    for rank, item in enumerate(wtg_data, 1):
        item["rank"] = rank

    fleet_ma = round(sum(d["ma"] for d in wtg_data) / len(wtg_data), 2) if wtg_data else 0.0
    fleet_int = round(sum(d["int_ga"] for d in wtg_data) / len(wtg_data), 2) if wtg_data else 0.0
    fleet_ext = round(sum(d["ext_ga"] for d in wtg_data) / len(wtg_data), 2) if wtg_data else 0.0
    fleet_comb = round(sum(d["comb_ga"] for d in wtg_data) / len(wtg_data), 2) if wtg_data else 0.0

    sorted_months = sorted(set(list(monthly_ma.keys()) + list(monthly_int.keys()) + list(monthly_ext.keys())))[-12:]
    month_ma_series = [round(sum(monthly_ma[m]) / len(monthly_ma[m]), 2) if monthly_ma[m] else 0.0 for m in sorted_months]
    month_int_series = [round(sum(monthly_int[m]) / len(monthly_int[m]), 2) if monthly_int[m] else 0.0 for m in sorted_months]
    month_ext_series = [round(sum(monthly_ext[m]) / len(monthly_ext[m]), 2) if monthly_ext[m] else 0.0 for m in sorted_months]

    context = {
        "kpi_fleet_ma": fleet_ma,
        "kpi_fleet_int": fleet_int,
        "kpi_fleet_ext": fleet_ext,
        "kpi_fleet_comb": fleet_comb,
        "kpi_total_wtgs": len(wtg_data),

        "table_data": wtg_data,
        "all_wtgs_json": json.dumps(wtg_data),

        "monthly_cats_json": json.dumps(sorted_months),
        "monthly_ma_json": json.dumps(month_ma_series),
        "monthly_int_json": json.dumps(month_int_series),
        "monthly_ext_json": json.dumps(month_ext_series),

        # Filters
        "date_from": date_from,
        "date_to": date_to,
        "providers": sorted(distincts["providers"]),
        "states": sorted(distincts["states"]),
        "sites": sorted(distincts["sites"]),
        "wtgs": sorted(distincts["wtgs"]),
        "selected_providers": providers,
        "selected_states": states,
        "selected_sites": sites,
        "selected_wtgs": wtgs,
    }

    return render(request, "wind_Grid_Availability_and_Machine.html", context)


def _pick(col_map, *candidates):
    """Find actual column name from possible variants with normalization."""
    def normalize(name):
        return (
            name.lower()
            .replace(".", "")
            .replace("%", "")
            .replace(" ", "")
            .replace("_", "")
            .strip()
        )
    for c in candidates:
        norm_c = normalize(c)
        for actual in col_map:
            if normalize(actual) == norm_c:
                return col_map[actual]
    return None


def parse_date_like(v):
    """Return a date object or None."""
    if v is None:
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    formats = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d-%b-%Y", "%d.%m.%Y", "%Y/%m/%d")
    s = str(v).strip()
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            continue
    # try smart split (Y-M-D or D-M-Y)
    try:
        parts = s.replace("/", "-").replace(".", "-").split("-")
        if len(parts) == 3:
            if len(parts[0]) == 4:  # yyyy-mm-dd
                return datetime(int(parts[0]), int(parts[1]), int(parts[2])).date()
            else:  # dd-mm-yyyy
                return datetime(int(parts[2]), int(parts[1]), int(parts[0])).date()
    except Exception:
        pass
    return None


def parse_hours(value):
    """Convert Operating Hours into float hours. Accepts 'HH:MM:SS', numeric, etc."""
    if value is None or value == "":
        return 0.0
    try:
        if isinstance(value, (int, float)):
            return float(value)
        s = str(value).strip()
        # some spreadsheets show "00:00" or "24:00:00"
        parts = s.split(":")
        if len(parts) == 3:
            h, m, sec = parts
            return float(h) + float(m) / 60.0 + float(sec) / 3600.0
        elif len(parts) == 2:
            h, m = parts
            return float(h) + float(m) / 60.0
        else:
            # try direct float
            return float(s)
    except Exception:
        return 0.0


def safe_float(v):
    """Try to coerce value to float, return 0.0 on failure."""
    try:
        if v is None or v == "":
            return 0.0
        return float(v)
    except Exception:
        return 0.0


@login_required
def wind_drill_down(request):
    """
    Turbine-Level Detail View (Drill Down)
    Implements Priority Visual #12:
    - Single-turbine selection from full fleet
    - Turbine lifetime & period KPIs (Generation, MA %, PLF %, Operating Hours, Downtime Hours)
    - Time-series generation trend for selected turbine
    - Operational loss breakdown (Machine vs Grid vs Lull vs Service)
    - Detailed historical breakdown log for the turbine
    """
    user = request.user.username.lower()
    is_admin = request.user.is_superuser or user == 'admin'

    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        all_tables = [r[0] for r in cursor.fetchall()]

    if is_admin:
        gen_tables = [t for t in all_tables if t.endswith('_wind') and not t.endswith('_breakdowndata')]
        bd_tables = [t for t in all_tables if t.endswith('_wind_breakdowndata')]
    else:
        gen_tables = [t for t in all_tables if t.startswith(user + '_') and t.endswith('_wind') and not t.endswith('_breakdowndata')]
        bd_tables = [t for t in all_tables if t.startswith(user + '_') and t.endswith('_wind_breakdowndata')]

    def _normalize(s):
        return s.lower().replace(" ", "").replace("_", "").replace(".", "").replace("(", "").replace(")", "").replace("%", "")

    def _pick(cmap, *candidates):
        for cand in candidates:
            c_norm = _normalize(cand)
            if c_norm in cmap:
                return cmap[c_norm]
        return None

    all_wtgs = set()
    wtg_oem_map = {}

    # Discover all WTGs
    for gt in gen_tables:
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{gt}`")
            cols = [r[0] for r in cursor.fetchall()]
        col_norm = {_normalize(c): c for c in cols}
        wtg_col = _pick(col_norm, "location_no", "turbine_id", "wtg", "wtg_no", "loc_no", "wec", "location")
        oem_col = _pick(col_norm, "provider", "oem")
        if wtg_col:
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT DISTINCT `{wtg_col}` FROM `{gt}` WHERE `{wtg_col}` IS NOT NULL AND `{wtg_col}` != ''")
                for r in cursor.fetchall():
                    w_name = str(r[0]).strip()
                    if w_name and w_name.lower() not in ("none", "total", "all wtg"):
                        all_wtgs.add(w_name)
                        oem = "Senvion" if "senvion" in gt.lower() else ("Regen" if "regen" in gt.lower() else "OEM")
                        wtg_oem_map[w_name] = oem

    sorted_wtg_list = sorted(list(all_wtgs))
    selected_wtg = request.GET.get("selected_wtg", "").strip()
    if not selected_wtg and sorted_wtg_list:
        selected_wtg = sorted_wtg_list[0]

    # Metrics for selected turbine
    wtg_total_gen = 0.0
    wtg_ma_list = []
    wtg_plf_list = []
    wtg_oh = 0.0
    wtg_iga_list = []
    wtg_ega_list = []
    gen_time_series = []

    loss_breakdown = {
        "Machine Fault": 0.0,
        "Internal Grid": 0.0,
        "External Grid": 0.0,
        "Lull / Low Wind": 0.0,
        "Scheduled Service": 0.0
    }

    for gt in gen_tables:
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{gt}`")
            cols = [r[0] for r in cursor.fetchall()]
        col_norm = {_normalize(c): c for c in cols}

        wtg_col = _pick(col_norm, "location_no", "turbine_id", "wtg", "wtg_no", "loc_no", "wec", "location")
        gen_col = _pick(col_norm, "wtg_production_kwh", "gen_kwh_day", "gen_kwh", "generation", "kwh")
        date_col = _pick(col_norm, "date", "gen_date", "reading_date")
        ma_col = _pick(col_norm, "wtg_availability", "machine_availability", "actual_ma", "corrected_ma")
        plf_col = _pick(col_norm, "plf_wtg_efficiency", "plf", "monthly_plf")
        oh_col = _pick(col_norm, "production_hours", "gen_hours", "operating_hours")
        iga_col = _pick(col_norm, "int_grid_availability", "internal_grid_availability")
        ega_col = _pick(col_norm, "ext_grid_availability", "external_grid_availability")

        lull_col = _pick(col_norm, "lull_hrs", "lull_hours")
        mf_col = _pick(col_norm, "machine_fault_hrs", "unscheduled_services")
        igf_col = _pick(col_norm, "internal_grid_down_time", "internal_grid_fault_hrs")
        egf_col = _pick(col_norm, "external_grid_down_time", "external_grid_fault_sd_hrs")
        serv_col = _pick(col_norm, "scheduled_services", "machine_shutdown_hrs")

        if not wtg_col or not selected_wtg:
            continue

        with connection.cursor() as cursor:
            cursor.execute(f"""
                SELECT SUM(CAST(`{gen_col}` AS DECIMAL(15,2))) as s_gen,
                       AVG(CAST(`{ma_col}` AS DECIMAL(10,2))) as avg_ma,
                       AVG(CAST(`{plf_col}` AS DECIMAL(10,2))) as avg_plf
                       {f", SUM(CAST(`{oh_col}` AS DECIMAL(15,2)))" if oh_col else ", 0"}
                       {f", AVG(CAST(`{iga_col}` AS DECIMAL(10,2)))" if iga_col else ", 0"}
                       {f", AVG(CAST(`{ega_col}` AS DECIMAL(10,2)))" if ega_col else ", 0"}
                       {f", SUM(CAST(`{lull_col}` AS DECIMAL(15,2)))" if lull_col else ", 0"}
                       {f", SUM(CAST(`{mf_col}` AS DECIMAL(15,2)))" if mf_col else ", 0"}
                       {f", SUM(CAST(`{igf_col}` AS DECIMAL(15,2)))" if igf_col else ", 0"}
                       {f", SUM(CAST(`{egf_col}` AS DECIMAL(15,2)))" if egf_col else ", 0"}
                       {f", SUM(CAST(`{serv_col}` AS DECIMAL(15,2)))" if serv_col else ", 0"}
                FROM `{gt}`
                WHERE REPLACE(LOWER(`{wtg_col}`), ' ', '') = REPLACE(LOWER(%s), ' ', '')
            """, [selected_wtg])
            row = cursor.fetchone()
            if row and row[0] is not None:
                wtg_total_gen += float(row[0] or 0)
                if row[1] is not None: wtg_ma_list.append(float(row[1]))
                if row[2] is not None: wtg_plf_list.append(float(row[2]))
                if row[3] is not None: wtg_oh += float(row[3] or 0)
                if row[4] is not None: wtg_iga_list.append(float(row[4]))
                if row[5] is not None: wtg_ega_list.append(float(row[5]))
                loss_breakdown["Lull / Low Wind"] += float(row[6] or 0)
                loss_breakdown["Machine Fault"] += float(row[7] or 0)
                loss_breakdown["Internal Grid"] += float(row[8] or 0)
                loss_breakdown["External Grid"] += float(row[9] or 0)
                loss_breakdown["Scheduled Service"] += float(row[10] or 0)

        # Monthly trajectory for this turbine
        if date_col and gen_col:
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    SELECT SUBSTRING(`{date_col}`, 1, 7) as ym, SUM(CAST(`{gen_col}` AS DECIMAL(15,2)))
                    FROM `{gt}`
                    WHERE REPLACE(LOWER(`{wtg_col}`), ' ', '') = REPLACE(LOWER(%s), ' ', '')
                      AND `{date_col}` IS NOT NULL AND `{date_col}` != ''
                    GROUP BY ym
                    ORDER BY ym ASC
                """, [selected_wtg])
                for ym, g in cursor.fetchall():
                    if ym and len(ym) == 7:
                        gen_time_series.append({"x": str(ym), "y": round(float(g or 0), 2)})

    # Query breakdown events for this turbine
    turbine_breakdowns = []
    total_turbine_downtime = 0.0

    for bdt in bd_tables:
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{bdt}`")
            cols = [r[0] for r in cursor.fetchall()]
        col_norm = {_normalize(c): c for c in cols}

        loc_col = _pick(col_norm, "location", "loc_no", "location_no", "wtg", "wtg_no")
        err_col = _pick(col_norm, "error_description", "error_details", "error_code", "cause")
        dur_col = _pick(col_norm, "total_duration", "duration", "hours")
        date_col = _pick(col_norm, "date", "gen_date")
        act_col = _pick(col_norm, "action_taken_remark", "action_taken", "remark")

        if loc_col and err_col and dur_col:
            with connection.cursor() as cursor:
                act_sel = f", `{act_col}`" if act_col else ", ''"
                cursor.execute(f"""
                    SELECT `{date_col}`, TRIM(`{err_col}`), CAST(`{dur_col}` AS DECIMAL(15,2)) {act_sel}
                    FROM `{bdt}`
                    WHERE REPLACE(LOWER(`{loc_col}`), ' ', '') = REPLACE(LOWER(%s), ' ', '')
                    ORDER BY CAST(`{dur_col}` AS DECIMAL(15,2)) DESC
                    LIMIT 100
                """, [selected_wtg])
                for r in cursor.fetchall():
                    d_val = float(r[2] or 0)
                    total_turbine_downtime += d_val
                    turbine_breakdowns.append({
                        "date": str(r[0])[:10] if r[0] else "-",
                        "cause": ' '.join(str(r[1]).split()) if r[1] else "Trip",
                        "duration": d_val,
                        "action": r[3] if len(r) > 3 and r[3] else "Restored to normal operation."
                    })

    avg_ma = (sum(wtg_ma_list) / len(wtg_ma_list)) if wtg_ma_list else 0.0
    avg_plf = (sum(wtg_plf_list) / len(wtg_plf_list)) if wtg_plf_list else 0.0
    avg_iga = (sum(wtg_iga_list) / len(wtg_iga_list)) if wtg_iga_list else 0.0
    avg_ega = (sum(wtg_ega_list) / len(wtg_ega_list)) if wtg_ega_list else 0.0

    if sum(loss_breakdown.values()) == 0 and total_turbine_downtime > 0:
        loss_breakdown["Machine Fault"] = round(total_turbine_downtime * 0.45, 1)
        loss_breakdown["Internal Grid"] = round(total_turbine_downtime * 0.20, 1)
        loss_breakdown["External Grid"] = round(total_turbine_downtime * 0.25, 1)
        loss_breakdown["Scheduled Service"] = round(total_turbine_downtime * 0.10, 1)

    return render(request, "wind_drill_down.html", {
        "selected_wtg": selected_wtg,
        "selected_oem": wtg_oem_map.get(selected_wtg, "OEM"),
        "wtg_list": sorted_wtg_list,
        "total_gen": round(wtg_total_gen, 2),
        "avg_ma": round(avg_ma, 2),
        "avg_plf": round(avg_plf, 2),
        "operating_hours": round(wtg_oh, 1),
        "total_downtime": round(total_turbine_downtime, 1),
        "avg_iga": round(avg_iga, 2),
        "avg_ega": round(avg_ega, 2),
        "generation_series_json": json.dumps(gen_time_series),
        "loss_categories_json": json.dumps(list(loss_breakdown.keys())),
        "loss_values_json": json.dumps([round(v, 1) for v in loss_breakdown.values()]),
        "breakdown_events": turbine_breakdowns
    })


@login_required
def wind_Avg_Machine_Availability(request):
    username = request.user.username.lower()
    is_admin = request.user.is_superuser or username == "admin"

    # Clear filters
    if request.GET.get("clear_filters"):
        request.session.pop("wind_filters", None)

    saved = request.session.get("wind_filters", {})
    def get_or_saved_list(key):
        vals = request.GET.getlist(key)
        return vals if vals else saved.get(key, [])

    date_from = request.GET.get("date_from") or saved.get("date_from")
    date_to   = request.GET.get("date_to")   or saved.get("date_to")
    providers = get_or_saved_list("provider")
    customers = get_or_saved_list("customer")
    states    = get_or_saved_list("state")
    sites     = get_or_saved_list("site")
    wtgs      = get_or_saved_list("wtg")

    request.session["wind_filters"] = {
        "date_from": date_from, "date_to": date_to,
        "provider": providers, "customer": customers,
        "state": states, "site": sites, "wtg": wtgs,
    }
    request.session.modified = True

    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES")
        db_tables = [row[0] for row in cursor.fetchall()]

    if is_admin:
        table_names = [t for t in db_tables if t.endswith("_wind") and not t.endswith("_breakdowndata")]
    else:
        table_names = [t for t in db_tables if t.startswith(username + "_") and t.endswith("_wind") and not t.endswith("_breakdowndata")]

    def _normalize(s):
        return s.lower().replace(" ", "").replace("_", "").replace(".", "").replace("(", "").replace(")", "").replace("%", "")

    def _pick(cmap, *candidates):
        for cand in candidates:
            c_norm = _normalize(cand)
            if c_norm in cmap:
                return cmap[c_norm]
        return None

    if not date_from or not date_to:
        min_dates, max_dates = [], []
        for t in table_names:
            with connection.cursor() as cursor:
                cursor.execute(f"SHOW COLUMNS FROM `{t}`")
                cols = {c[0].lower(): c[0] for c in cursor.fetchall()}
                col_norm = {_normalize(c): c for c in cols.values()}
                dcol = _pick(col_norm, "date", "gen_date", "reading_date", "day_date")
                if dcol:
                    cursor.execute(f"SELECT MIN(`{dcol}`), MAX(`{dcol}`) FROM `{t}` WHERE `{dcol}` IS NOT NULL")
                    row = cursor.fetchone()
                    if row and row[0] and row[1]:
                        min_dates.append(str(row[0]))
                        max_dates.append(str(row[1]))
        if min_dates and max_dates:
            date_from = date_from or min(min_dates)
            date_to = date_to or max(max_dates)

    wtg_ma_list = defaultdict(list)
    wtg_meta = {}
    monthly_ma = defaultdict(list)
    distincts = {"providers": set(), "customers": set(), "states": set(), "sites": set(), "wtgs": set()}

    for t in table_names:
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{t}`")
            cols = [c[0] for c in cursor.fetchall()]
        col_norm = {_normalize(c): c for c in cols}

        wtg_col = _pick(col_norm, "location_no", "turbine_id", "loc_no", "wec", "wtg", "wtg_no", "locno", "turbine")
        date_col = _pick(col_norm, "date", "gen_date", "reading_date", "day_date")
        ma_col = _pick(col_norm, "wtg_availability", "machine_availability", "actual_ma", "corrected_ma", "ma")
        oem_col = _pick(col_norm, "provider", "oem", "oemprovider", "oem_name")
        site_col = _pick(col_norm, "site", "sitename", "location", "plant", "park")
        state_col = _pick(col_norm, "state", "statename", "st")
        month_col = _pick(col_norm, "month", "mon")

        if not wtg_col or not ma_col:
            continue

        select_cols = [f"`{wtg_col}`", f"`{ma_col}`"]
        if date_col: select_cols.append(f"`{date_col}`")
        if oem_col: select_cols.append(f"`{oem_col}`")
        if site_col: select_cols.append(f"`{site_col}`")
        if state_col: select_cols.append(f"`{state_col}`")
        if month_col: select_cols.append(f"`{month_col}`")

        where_conds = [f"`{wtg_col}` IS NOT NULL AND `{wtg_col}` != ''"]
        params = []
        if date_col and date_from and date_to:
            where_conds.append(f"`{date_col}` BETWEEN %s AND %s")
            params.extend([date_from, date_to])

        def add_in(col, vals):
            if col and vals:
                q = ",".join(["%s"] * len(vals))
                where_conds.append(f"`{col}` IN ({q})")
                params.extend(vals)

        add_in(oem_col, providers)
        add_in(state_col, states)
        add_in(site_col, sites)
        add_in(wtg_col, wtgs)

        where_clause = " WHERE " + " AND ".join(where_conds)
        sql = f"SELECT {', '.join(select_cols)} FROM `{t}` {where_clause}"

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()

        idx = {c.strip("`"): i for i, c in enumerate(select_cols)}

        for r in rows:
            wtg_val = str(r[idx[wtg_col]]).strip()
            if not wtg_val or wtg_val.lower() in ("none", "total", "all wtg"):
                continue

            val = None
            if r[idx[ma_col]] not in (None, ""):
                try: val = float(r[idx[ma_col]])
                except: pass

            if val is not None and val > 0:
                wtg_ma_list[wtg_val].append(val)

            if wtg_val not in wtg_meta:
                wtg_meta[wtg_val] = {
                    "oem": str(r[idx[oem_col]]).strip() if oem_col and r[idx[oem_col]] else ("Senvion" if "senvion" in t else ("Regen" if "regen" in t else "Wind")),
                    "site": str(r[idx[site_col]]).strip() if site_col and r[idx[site_col]] else "Site-1",
                    "state": str(r[idx[state_col]]).strip() if state_col and r[idx[state_col]] else "Default"
                }

            m_key = None
            if date_col and r[idx[date_col]]:
                m_key = str(r[idx[date_col]])[:7]
            elif month_col and r[idx[month_col]]:
                m_key = str(r[idx[month_col]]).strip()

            if m_key and val is not None and val > 0:
                monthly_ma[m_key].append(val)

        def add_distinct(col, key):
            if not col: return
            with connection.cursor() as cur:
                cur.execute(f"SELECT DISTINCT `{col}` FROM `{t}` WHERE `{col}` IS NOT NULL AND `{col}` != ''")
                for r_ in cur.fetchall():
                    distincts[key].add(str(r_[0]).strip())

        add_distinct(oem_col, "providers")
        add_distinct(state_col, "states")
        add_distinct(site_col, "sites")
        add_distinct(wtg_col, "wtgs")

    wtg_data = []
    for w, vals in wtg_ma_list.items():
        avg_ma = round(sum(vals) / len(vals), 2)
        meta = wtg_meta.get(w, {"oem": "Wind", "site": "-", "state": "-"})
        delta_target = round(avg_ma - 95.0, 2)
        wtg_data.append({
            "wtg": w,
            "ma": avg_ma,
            "delta_target": delta_target,
            "oem": meta["oem"],
            "site": meta["site"],
            "state": meta["state"],
            "status": "Target Met" if avg_ma >= 95.0 else "Below Target"
        })

    wtg_data.sort(key=lambda x: x["ma"], reverse=True)
    for rank, item in enumerate(wtg_data, 1):
        item["rank"] = rank

    fleet_ma = round(sum(d["ma"] for d in wtg_data) / len(wtg_data), 2) if wtg_data else 0.0
    best_wtg = wtg_data[0] if wtg_data else {"wtg": "-", "ma": 0}
    worst_wtg = wtg_data[-1] if wtg_data else {"wtg": "-", "ma": 0}
    compliance_cnt = sum(1 for d in wtg_data if d["ma"] >= 95.0)
    compliance_pct = round((compliance_cnt / len(wtg_data) * 100), 1) if wtg_data else 0.0

    sorted_months = sorted(monthly_ma.keys())[-12:]
    month_series = [round(sum(monthly_ma[m]) / len(monthly_ma[m]), 2) for m in sorted_months]

    context = {
        "kpi_fleet_ma": fleet_ma,
        "kpi_best_wtg": best_wtg["wtg"],
        "kpi_best_val": best_wtg["ma"],
        "kpi_worst_wtg": worst_wtg["wtg"],
        "kpi_worst_val": worst_wtg["ma"],
        "kpi_compliance_cnt": compliance_cnt,
        "kpi_compliance_pct": compliance_pct,
        "kpi_total_wtgs": len(wtg_data),

        "table_data": wtg_data,
        "all_wtgs_json": json.dumps(wtg_data),

        "monthly_cats_json": json.dumps(sorted_months),
        "monthly_ma_json": json.dumps(month_series),

        # Filters
        "date_from": date_from,
        "date_to": date_to,
        "providers": sorted(distincts["providers"]),
        "states": sorted(distincts["states"]),
        "sites": sorted(distincts["sites"]),
        "wtgs": sorted(distincts["wtgs"]),
        "selected_providers": providers,
        "selected_states": states,
        "selected_sites": sites,
        "selected_wtgs": wtgs,
    }

    return render(request, "wind_Avg_Machine_Availability.html", context)


def clean_col(col: str) -> str:
    return re.sub(r'\W+', '_', str(col).strip()).lower().strip('_')


def normalize_date(val):
    """Convert any date-like value to proper YYYY-MM-DD date."""
    if val is None or str(val).strip().lower() in ["", "nan", "nat"]:
        return None
    try:
        if isinstance(val, (datetime, pd.Timestamp)):
            return val.date()
        if isinstance(val, date):  # ✅ handle pure date
            return val
        if isinstance(val, (int, float)):
            return (datetime(1899, 12, 30) + pd.to_timedelta(val, unit='D')).date()
        parsed = pd.to_datetime(str(val), errors='coerce')
        if pd.notna(parsed):
            return parsed.date()
        return None
    except Exception:
        return None


def normalize_hours(val):
    """Convert time strings or day-hour formats into float hours."""
    if val is None or str(val).strip().lower() in ["", "nan", "nat"]:
        return 0.0
    try:
        if isinstance(val, (int, float)):
            return float(val)
        s = str(val).strip().replace(".", ":")
        if "day" in s:
            parts = s.split()
            days = float(parts[0])
            h, m, sec = [float(x) for x in parts[-1].split(":")]
            return days * 24 + h + m / 60 + sec / 3600
        if ":" in s:
            parts = s.split(":")
            h, m = float(parts[0]), float(parts[1]) if len(parts) > 1 else 0
            sec = float(parts[2]) if len(parts) > 2 else 0
            return h + m / 60 + sec / 3600
        return float(s)
    except Exception:
        return 0.0


def sanitize_value(val):
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except Exception:
        pass
    if isinstance(val, (np.floating, float)) and (np.isnan(val) or np.isinf(val)):
        return None
    if str(val).strip().lower() in ["nan", "nat", "none", ""]:
        return None
    return val


def detect_header_row(df):
    """Detect first row that looks like a real header, skip meta rows like 'WEC Wise Report'."""
    for i, row in df.iterrows():
        row_values = [str(x).strip().lower() for x in row.values if pd.notna(x)]
        if not row_values:
            continue
        if any("wec wise report" in val for val in row_values):
            continue
        keywords = ["date", "wec", "generation"]
        if any(kw in val for val in row_values for kw in keywords):
            return i
    return 0


def read_excel_multi(file_path, ext):
    """Read multi-sheet Excel, CSV, or HTML-based XLS and skip meta header rows."""
    def find_data_start(df):
        """Return the index where data header starts (e.g. contains DATE/WEC)."""
        for i, row in df.iterrows():
            joined = " ".join(str(x).lower() for x in row if pd.notna(x))
            if "date" in joined and "wec" in joined:
                return i
        return 0

    if ext == ".csv":
        df_preview = pd.read_csv(file_path, header=None)
        start_row = find_data_start(df_preview)
        df = pd.read_csv(file_path, header=start_row)
        return {"main": df}

    # --- Detect HTML disguised as .xls ---
    with open(file_path, "rb") as f:
        start_bytes = f.read(100).lower()
        if b"<html" in start_bytes or b"<table" in start_bytes:
            df_all = pd.read_html(file_path)[0]
            start_row = find_data_start(df_all)
            df = df_all.iloc[start_row:].reset_index(drop=True)
            df.columns = [clean_col(c) for c in df.iloc[0]]
            df = df[1:]  # drop header row from data
            return {"main": df}

    # --- Regular Excel / XLSX ---
    if ext in [".xlsx", ".xlsm"]:
        sheets = pd.read_excel(file_path, sheet_name=None, engine="openpyxl", header=None)
    elif ext == ".xls":
        sheets = pd.read_excel(file_path, sheet_name=None, engine="xlrd", header=None)
    else:
        raise Exception("Unsupported format")

    cleaned_sheets = {}
    for sheet_name, df in sheets.items():
        start_row = find_data_start(df)
        df = pd.read_excel(
            file_path,
            sheet_name=sheet_name,
            engine="openpyxl" if ext != ".xls" else "xlrd",
            header=start_row,
        )
        cleaned_sheets[sheet_name] = df
    return cleaned_sheets

# =================== MAIN VIEW =================== #
def normalize_percentage(val):
    """Correctly normalize PLF, Plant Availability, Grid OK values from Excel."""
    if val is None or str(val).strip() in ["", "nan", "None"]:
        return None

    s = str(val).strip()

    # 1️⃣ Direct % format (e.g., "18.99%")
    if s.endswith("%"):
        try:
            return float(s.replace("%", "").strip())
        except:
            return None

    # 2️⃣ Do NOT convert times like "00:00"
    if ":" in s:
        return s

    try:
        f = float(s)

        # 3️⃣ Excel stores 100% as 1.0 → convert to 100
        if f == 1:
            return 100.0

        # 4️⃣ Excel stores percentages as decimals (0.1899 → 18.99)
        if 0 < f < 1:
            return round(f * 100, 4)

        # 5️⃣ Already in correct integer/float form
        return round(f, 4)

    except:
        return None



@login_required
def customer_upload(request):
    username = request.user.username.lower()
    providers = Provider.objects.all()
    energy_types = EnergyType.objects.all()

    # =====================================================
    # FETCH LOGGED-IN USER TABLES
    # =====================================================
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        db_tables = [row[0] for row in cursor.fetchall()]

    user_tables = []
    for table in db_tables:
        if table.startswith(username + "_"):
            parts = table.split("_")
            provider_slug = "_".join(parts[1:-1])
            energy_slug = parts[-1]
            label = f"{username} - {provider_slug.replace('_',' ').title()} - {energy_slug.title()}"
            user_tables.append({"name": table, "label": label})

    # =====================================================
    # POST REQUEST (UPLOAD)
    # =====================================================
    if request.method == "POST":
        table_name = request.POST.get("table_name", "").strip()
        provider_name = request.POST.get("provider_name", "").strip()
        energy_type_name = request.POST.get("energy_type", "").title()
        data_file = request.FILES.get("data_file")

        if not table_name or not provider_name or not data_file:
            messages.error(request, "❌ Table, provider and file are required.")
            return redirect("customer_upload")

        fs = FileSystemStorage()
        filename = fs.save(data_file.name, data_file)
        file_path = fs.path(filename)

        try:
            ext = os.path.splitext(filename)[1].lower()
            sheets = read_excel_multi(file_path, ext)
            uploaded_sheets = []

            for sheet_name, df in sheets.items():

                if df.empty:
                    continue

                # ----- CLEAN COLUMNS -----
                df.columns = [clean_col(c) for c in df.columns]

                # =====================================================
                # NORMALIZATION
                # =====================================================
                for col in df.columns:
                    col_l = col.lower().strip()

                    if any(k in col_l for k in ["date", "gen_date", "generation_date", "dt"]):
                        df[col] = df[col].apply(normalize_date)
                        df[col] = df[col].apply(
                            lambda x: x.strftime("%Y-%m-%d")
                            if isinstance(x, (datetime, date)) else x
                        )
                        continue

                    if any(k in col_l for k in ["plf", "availability", "grid", "%", "gf", "pa"]):
                        df[col] = df[col].apply(normalize_percentage)
                        continue

                    if any(k in col_l for k in ["hr", "hour", "hrs", "duration", "time"]):
                        df[col] = df[col].apply(normalize_hours)
                        continue

                # =====================================================
                # SANITIZE
                # =====================================================
                df = df.replace({
                    pd.NaT: None,
                    np.nan: None,
                    "": None,
                    "nan": None,
                    "NaN": None,
                    np.inf: None,
                    -np.inf: None
                })
                df = df.dropna(how="all")

                # =====================================================
                # TARGET TABLE
                # =====================================================
                sname = sheet_name.lower()
                if "breakdown" in sname:
                    target_table = f"{table_name}_breakdowndata"
                elif "month" in sname or "monthly" in sname:
                    target_table = f"{table_name}_monthly"
                else:
                    target_table = table_name

                if target_table not in db_tables:
                    continue

                # =====================================================
                # GET TABLE COLUMNS
                # =====================================================
                with connection.cursor() as cursor:
                    cursor.execute(f"SHOW COLUMNS FROM `{target_table}`")
                    table_columns = [c[0].lower() for c in cursor.fetchall()]

                alias_map = {
                    "loaction": "location",
                    "loc": "location",
                    "location ": "location",
                }
                df.rename(columns=lambda c: alias_map.get(c.lower(), c.lower()), inplace=True)

                # =====================================================
                # FILTER VALID COLUMNS
                # =====================================================
                valid_cols = [c for c in df.columns if c in table_columns]
                df = df[valid_cols]

                # =====================================================
                # ADD METADATA
                # =====================================================
                if "uploaded_by" in table_columns:
                    df["uploaded_by"] = username
                if "provider" in table_columns:
                    df["provider"] = provider_name
                if "energy_type" in table_columns:
                    df["energy_type"] = energy_type_name

                # =====================================================
                # 🔥 SOLAR SAFETY: DROP NULLS + DEDUPE
                # =====================================================
                is_solar = "solar" in table_name.lower()

                if is_solar:
                    required = ["date", "site", "location"]
                    existing = [c for c in required if c in df.columns]

                    if len(existing) == 3:
                        df = df.dropna(subset=existing)
                        df = df.drop_duplicates(subset=existing, keep="last")
                    else:
                        messages.error(
                            request,
                            f"❌ Solar table missing required columns: {required}"
                        )
                        continue

                if df.empty:
                    continue

                # =====================================================
                # UPSERT / INSERT
                # =====================================================
                final_cols = list(df.columns)
                col_sql = ", ".join(f"`{c}`" for c in final_cols)
                placeholder_sql = ", ".join(["%s"] * len(final_cols))

                if is_solar:
                    update_cols = [
                        c for c in final_cols
                        if c not in ["date", "site", "location"]
                    ]
                    update_clause = ", ".join(
                        f"`{c}` = VALUES(`{c}`)" for c in update_cols
                    )
                    sql = f"""
                        INSERT INTO `{target_table}` ({col_sql})
                        VALUES ({placeholder_sql})
                        ON DUPLICATE KEY UPDATE {update_clause};
                    """
                else:
                    sql = f"""
                        INSERT INTO `{target_table}` ({col_sql})
                        VALUES ({placeholder_sql});
                    """

                values = [
                    tuple(sanitize_value(v) for v in row)
                    for row in df.values
                ]

                with connection.cursor() as cursor:
                    cursor.executemany(sql, values)
                    affected = cursor.rowcount

                if affected > 0:
                    UploadMetadata.objects.update_or_create(
                        table_name=target_table,
                        defaults={"last_modified": now()},
                    )
                    uploaded_sheets.append(f"{sheet_name} → {affected} rows")

            if uploaded_sheets:
                messages.success(request, "✔ Upload Success:\n" + "\n".join(uploaded_sheets))
            else:
                messages.error(request, "❌ No sheets uploaded. Check Excel format.")

        except Exception as e:
            traceback.print_exc()
            messages.error(request, f"❌ Upload failed: {e}")

        finally:
            fs.delete(filename)

        return redirect("customer_upload")

    return render(request, "customer_upload.html", {
        "user_tables": user_tables,
        "providers": providers,
        "energy_types": energy_types,
    })

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import connection
from datetime import datetime

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import connection
from datetime import datetime

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import connection
from datetime import datetime



@login_required
def wind_wtg_plf(request):
    """
    Availability & Efficiency Analysis (PLF)
    Implements 12 Priority Visuals:
    - Visual #4: Turbine Availability Heatmap (Month vs WTG)
    - Visual #6: Machine Availability vs PLF Scatter Plot (Outlier Detection)
    - Visual #7: Internal vs External Grid Availability Chart
    - Summary KPI cards & Full Data Table
    """
    user = request.user.username.lower()
    is_admin = request.user.is_superuser or user == 'admin'

    if request.GET.get("clear_filters"):
        request.session.pop("wind_filters", None)

    saved = request.session.get("wind_filters", {})

    def get_or_saved_list(key):
        vals = request.GET.getlist(key)
        return vals if vals else saved.get(key, [])

    date_from = request.GET.get("date_from") or saved.get("date_from")
    date_to   = request.GET.get("date_to")   or saved.get("date_to")

    providers = get_or_saved_list("provider")
    customers = get_or_saved_list("customer")
    states    = get_or_saved_list("state")
    sites     = get_or_saved_list("site")
    wtgs      = get_or_saved_list("wtg")

    request.session["wind_filters"] = {
        "date_from": date_from,
        "date_to": date_to,
        "provider": providers,
        "customer": customers,
        "state": states,
        "site": sites,
        "wtg": wtgs,
    }
    request.session.modified = True

    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        all_tables = [r[0] for r in cursor.fetchall()]

    if is_admin:
        gen_tables = [t for t in all_tables if t.endswith('_wind') and 'breakdown' not in t]
    else:
        gen_tables = [t for t in all_tables if t.startswith(user + '_') and t.endswith('_wind')]

    scatter_points = []
    heatmap_matrix = defaultdict(lambda: defaultdict(float))
    all_months = set()
    int_grid_vals = []
    ext_grid_vals = []
    table_rows = []
    distincts = {k: set() for k in ["providers", "customers", "states", "sites", "wtgs"]}

    earliest_date = None
    latest_date = None

    for gt in gen_tables:
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{gt}`")
            cols = [r[0] for r in cursor.fetchall()]
        col_map = {normalize(c): c for c in cols}

        wtg_col = _pick(col_map, "location_no", "turbine_id", "wtg", "wtg_no", "loc_no", "wec", "location")
        gen_col = _pick(col_map, "wtg_production_kwh", "gen_kwh_day", "gen_kwh", "generation", "kwh")
        date_col = _pick(col_map, "date", "gen_date")
        ma_col = _pick(col_map, "wtg_availability", "machine_availability", "actual_ma", "corrected_ma")
        plf_col = _pick(col_map, "plf_wtg_efficiency", "plf", "monthly_plf")
        iga_col = _pick(col_map, "int_grid_availability", "internal_grid_availability")
        ega_col = _pick(col_map, "ext_grid_availability", "external_grid_availability")
        provider_col = _pick(col_map, "provider", "oem")
        customer_col = _pick(col_map, "customer", "customer_name")
        state_col = _pick(col_map, "state")
        site_col = _pick(col_map, "site", "wind_farm_name")

        oem_name = "Unknown OEM"
        gt_lower = gt.lower()
        if "senvion" in gt_lower: oem_name = "Senvion"
        elif "regen" in gt_lower: oem_name = "Regen"
        elif "gamesa" in gt_lower: oem_name = "Gamesa"
        elif "inox" in gt_lower: oem_name = "Inox"
        elif "suzlon" in gt_lower: oem_name = "Suzlon"
        elif "windworld" in gt_lower: oem_name = "Windworld"

        if not wtg_col or not plf_col:
            continue

        if date_col and (not date_from or not date_to):
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT MIN(`{date_col}`), MAX(`{date_col}`) FROM `{gt}` WHERE `{date_col}` IS NOT NULL AND `{date_col}` != ''")
                d_min, d_max = cursor.fetchone()
                if d_min and (not earliest_date or str(d_min) < str(earliest_date)):
                    earliest_date = str(d_min)[:10]
                if d_max and (not latest_date or str(d_max) > str(latest_date)):
                    latest_date = str(d_max)[:10]

        base_conditions, base_params = [], []
        if date_from and date_to and date_col:
            base_conditions.append(f"`{date_col}` BETWEEN %s AND %s")
            base_params.extend([date_from, date_to])

        def add_in_filter(col, values, conds, parms):
            if col and values:
                placeholders = ",".join(["%s"] * len(values))
                conds.append(f"`{col}` IN ({placeholders})")
                parms.extend(values)

        add_in_filter(provider_col, providers, base_conditions, base_params)
        add_in_filter(customer_col, customers, base_conditions, base_params)
        add_in_filter(state_col, states, base_conditions, base_params)
        add_in_filter(site_col, sites, base_conditions, base_params)
        add_in_filter(wtg_col, wtgs, base_conditions, base_params)

        cond_wtg = list(base_conditions)
        parms_wtg = list(base_params)
        cond_wtg.append(f"`{wtg_col}` IS NOT NULL AND `{wtg_col}` != ''")
        where_wtg = f"WHERE {' AND '.join(cond_wtg)}"

        iga_select = f", AVG(CAST(`{iga_col}` AS DECIMAL(10,2)))" if iga_col else ", 0"
        ega_select = f", AVG(CAST(`{ega_col}` AS DECIMAL(10,2)))" if ega_col else ", 0"
        gen_select = f", SUM(CAST(`{gen_col}` AS DECIMAL(15,2)))" if gen_col else ", 0"

        with connection.cursor() as cursor:
            cursor.execute(f"""
                SELECT `{wtg_col}`, 
                       AVG(CAST(`{plf_col}` AS DECIMAL(10,2))) as avg_plf,
                       AVG(CAST(`{ma_col}` AS DECIMAL(10,2))) as avg_ma
                       {iga_select}
                       {ega_select}
                       {gen_select}
                FROM `{gt}`
                {where_wtg}
                GROUP BY `{wtg_col}`
            """, parms_wtg)
            for w, plf, ma, iga, ega, gen in cursor.fetchall():
                wtg_key = str(w).strip()
                p_val = round(float(plf or 0), 2)
                m_val = round(float(ma or 0), 2)
                i_val = round(float(iga or 0), 2)
                e_val = round(float(ega or 0), 2)
                g_val = round(float(gen or 0), 2)

                scatter_points.append({
                    "wtg": wtg_key,
                    "x": m_val,
                    "y": p_val,
                    "oem": oem_name
                })
                table_rows.append({
                    "wtg_no": wtg_key,
                    "oem": oem_name,
                    "plf": p_val,
                    "ma": m_val,
                    "iga": i_val,
                    "ega": e_val,
                    "generation": g_val
                })
                if iga: int_grid_vals.append(i_val)
                if ega: ext_grid_vals.append(e_val)

        if date_col and ma_col:
            cond_hm = list(base_conditions)
            parms_hm = list(base_params)
            cond_hm.append(f"`{date_col}` IS NOT NULL AND `{date_col}` != ''")
            where_hm = f"WHERE {' AND '.join(cond_hm)}"

            with connection.cursor() as cursor:
                cursor.execute(f"""
                    SELECT `{wtg_col}`, SUBSTRING(`{date_col}`, 1, 7) as ym, AVG(CAST(`{ma_col}` AS DECIMAL(10,2)))
                    FROM `{gt}`
                    {where_hm}
                    GROUP BY `{wtg_col}`, ym
                """, parms_hm)
                for w, ym, ma in cursor.fetchall():
                    if ym and len(ym) == 7 and ma is not None:
                        heatmap_matrix[str(w).strip()][ym] = round(float(ma), 1)
                        all_months.add(ym)

        def dist(col):
            if not col: return []
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT DISTINCT `{col}` FROM `{gt}` WHERE `{col}` IS NOT NULL AND `{col}` != '' ORDER BY `{col}`")
                return [str(r[0]) for r in cursor.fetchall()]

        distincts["providers"].update(dist(provider_col))
        distincts["customers"].update(dist(customer_col))
        distincts["states"].update(dist(state_col))
        distincts["sites"].update(dist(site_col))
        distincts["wtgs"].update(dist(wtg_col))

    sorted_plf = sorted(scatter_points, key=lambda x: x["y"], reverse=True)
    avg_fleet_plf = (sum(d["y"] for d in scatter_points) / len(scatter_points)) if scatter_points else 0
    avg_fleet_ma = (sum(d["x"] for d in scatter_points) / len(scatter_points)) if scatter_points else 0
    avg_iga = (sum(int_grid_vals) / len(int_grid_vals)) if int_grid_vals else 0
    avg_ega = (sum(ext_grid_vals) / len(ext_grid_vals)) if ext_grid_vals else 0

    top_10 = sorted_plf[:10]
    bottom_10 = sorted(sorted_plf[-10:], key=lambda x: x["y"])

    sorted_months = sorted(all_months)
    recent_12_months = sorted_months[-12:] if len(sorted_months) >= 12 else sorted_months
    heatmap_series = []
    for d in sorted_plf:
        w = d["wtg"]
        row_data = []
        for m in recent_12_months:
            row_data.append({"x": m, "y": heatmap_matrix[w].get(m, round(avg_fleet_ma, 1))})
        heatmap_series.append({"name": w, "data": row_data})

    table_rows.sort(key=lambda x: x["plf"], reverse=True)
    for rank, r in enumerate(table_rows, 1):
        r["rank"] = rank
        if r["plf"] >= avg_fleet_plf:
            r["status"] = "High Yield"
        elif r["plf"] < (avg_fleet_plf * 0.75):
            r["status"] = "Low PLF"
        else:
            r["status"] = "Normal"

    return render(request, "wind_wtg_plf.html", {
        "scatter_data_json": json.dumps(scatter_points),
        "heatmap_series_json": json.dumps(heatmap_series),
        "recent_months": recent_12_months,
        "grid_comparison_json": json.dumps({
            "labels": ["Internal Grid Availability", "External Grid Availability"],
            "values": [round(avg_iga, 2), round(avg_ega, 2)]
        }),
        "top_10_json": json.dumps(top_10),
        "bottom_10_json": json.dumps(bottom_10),
        "fleet_avg_plf": round(avg_fleet_plf, 2),
        "fleet_avg_ma": round(avg_fleet_ma, 2),
        "avg_iga": round(avg_iga, 2),
        "avg_ega": round(avg_ega, 2),
        "top_plf_wtg": top_10[0] if top_10 else None,
        "bottom_plf_wtg": bottom_10[0] if bottom_10 else None,
        "wtg_count": len(scatter_points),
        "table_data": table_rows,

        "providers": sorted(distincts["providers"]),
        "customers": sorted(distincts["customers"]),
        "states": sorted(distincts["states"]),
        "sites": sorted(distincts["sites"]),
        "wtgs": sorted(distincts["wtgs"]),

        "selected_providers": providers,
        "selected_customers": customers,
        "selected_states": states,
        "selected_sites": sites,
        "selected_wtgs": wtgs,

        "date_from": date_from or earliest_date,
        "date_to": date_to or latest_date,
    })

@login_required
def wind_Grid_Availability(request):
    username = request.user.username.lower()
    is_admin = request.user.is_superuser or username == "admin"

    # Clear filters
    if request.GET.get("clear_filters"):
        request.session.pop("wind_filters", None)

    saved = request.session.get("wind_filters", {})
    def get_or_saved_list(key):
        vals = request.GET.getlist(key)
        return vals if vals else saved.get(key, [])

    date_from = request.GET.get("date_from") or saved.get("date_from")
    date_to   = request.GET.get("date_to")   or saved.get("date_to")
    providers = get_or_saved_list("provider")
    customers = get_or_saved_list("customer")
    states    = get_or_saved_list("state")
    sites     = get_or_saved_list("site")
    wtgs      = get_or_saved_list("wtg")

    request.session["wind_filters"] = {
        "date_from": date_from, "date_to": date_to,
        "provider": providers, "customer": customers,
        "state": states, "site": sites, "wtg": wtgs,
    }
    request.session.modified = True

    # Tables
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES")
        db_tables = [row[0] for row in cursor.fetchall()]

    if is_admin:
        table_names = [t for t in db_tables if t.endswith("_wind") and not t.endswith("_breakdowndata")]
    else:
        table_names = [t for t in db_tables if t.startswith(username + "_") and t.endswith("_wind") and not t.endswith("_breakdowndata")]

    def _normalize(s):
        return s.lower().replace(" ", "").replace("_", "").replace(".", "").replace("(", "").replace(")", "").replace("%", "")

    def _pick(cmap, *candidates):
        for cand in candidates:
            c_norm = _normalize(cand)
            if c_norm in cmap:
                return cmap[c_norm]
        return None

    # Auto date if not specified
    if not date_from or not date_to:
        min_dates, max_dates = [], []
        for t in table_names:
            with connection.cursor() as cursor:
                cursor.execute(f"SHOW COLUMNS FROM `{t}`")
                cols = {c[0].lower(): c[0] for c in cursor.fetchall()}
                col_norm = {_normalize(c): c for c in cols.values()}
                dcol = _pick(col_norm, "date", "gen_date", "reading_date", "day_date")
                if dcol:
                    cursor.execute(f"SELECT MIN(`{dcol}`), MAX(`{dcol}`) FROM `{t}` WHERE `{dcol}` IS NOT NULL")
                    row = cursor.fetchone()
                    if row and row[0] and row[1]:
                        min_dates.append(str(row[0]))
                        max_dates.append(str(row[1]))
        if min_dates and max_dates:
            date_from = date_from or min(min_dates)
            date_to = date_to or max(max_dates)

    wtg_int_list = defaultdict(list)
    wtg_ext_list = defaultdict(list)
    wtg_meta = {}
    monthly_int = defaultdict(list)
    monthly_ext = defaultdict(list)
    distincts = {"providers": set(), "customers": set(), "states": set(), "sites": set(), "wtgs": set()}

    for t in table_names:
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{t}`")
            cols = [c[0] for c in cursor.fetchall()]
        col_norm = {_normalize(c): c for c in cols}

        wtg_col = _pick(col_norm, "location_no", "turbine_id", "loc_no", "wec", "wtg", "wtg_no", "locno", "turbine")
        date_col = _pick(col_norm, "date", "gen_date", "reading_date", "day_date")
        int_col = _pick(col_norm, "int_grid_availability", "internal_grid_availability", "iga", "internalgridavailability")
        ext_col = _pick(col_norm, "ext_grid_availability", "external_grid_availability", "ega", "externalgridavailability", "ga")
        oem_col = _pick(col_norm, "provider", "oem", "oemprovider", "oem_name")
        site_col = _pick(col_norm, "site", "sitename", "location", "plant", "park")
        state_col = _pick(col_norm, "state", "statename", "st")
        month_col = _pick(col_norm, "month", "mon")

        if not wtg_col:
            continue

        select_cols = [f"`{wtg_col}`"]
        if int_col: select_cols.append(f"`{int_col}`")
        if ext_col: select_cols.append(f"`{ext_col}`")
        if date_col: select_cols.append(f"`{date_col}`")
        if oem_col: select_cols.append(f"`{oem_col}`")
        if site_col: select_cols.append(f"`{site_col}`")
        if state_col: select_cols.append(f"`{state_col}`")
        if month_col: select_cols.append(f"`{month_col}`")

        where_conds = [f"`{wtg_col}` IS NOT NULL AND `{wtg_col}` != ''"]
        params = []
        if date_col and date_from and date_to:
            where_conds.append(f"`{date_col}` BETWEEN %s AND %s")
            params.extend([date_from, date_to])

        def add_in(col, vals):
            if col and vals:
                q = ",".join(["%s"] * len(vals))
                where_conds.append(f"`{col}` IN ({q})")
                params.extend(vals)

        add_in(oem_col, providers)
        add_in(state_col, states)
        add_in(site_col, sites)
        add_in(wtg_col, wtgs)

        where_clause = " WHERE " + " AND ".join(where_conds)
        sql = f"SELECT {', '.join(select_cols)} FROM `{t}` {where_clause}"

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()

        idx = {c.strip("`"): i for i, c in enumerate(select_cols)}

        for r in rows:
            wtg_val = str(r[idx[wtg_col]]).strip()
            if not wtg_val or wtg_val.lower() in ("none", "total", "all wtg"):
                continue

            ival, eval_ = None, None
            if int_col and r[idx[int_col]] not in (None, ""):
                try: ival = float(r[idx[int_col]])
                except: pass
            if ext_col and r[idx[ext_col]] not in (None, ""):
                try: eval_ = float(r[idx[ext_col]])
                except: pass

            if ival is not None and ival > 0:
                wtg_int_list[wtg_val].append(ival)
            if eval_ is not None and eval_ > 0:
                wtg_ext_list[wtg_val].append(eval_)

            if wtg_val not in wtg_meta:
                wtg_meta[wtg_val] = {
                    "oem": str(r[idx[oem_col]]).strip() if oem_col and r[idx[oem_col]] else ("Senvion" if "senvion" in t else ("Regen" if "regen" in t else "Wind")),
                    "site": str(r[idx[site_col]]).strip() if site_col and r[idx[site_col]] else "Site-1",
                    "state": str(r[idx[state_col]]).strip() if state_col and r[idx[state_col]] else "Default"
                }

            m_key = None
            if date_col and r[idx[date_col]]:
                m_key = str(r[idx[date_col]])[:7]
            elif month_col and r[idx[month_col]]:
                m_key = str(r[idx[month_col]]).strip()

            if m_key:
                if ival is not None and ival > 0: monthly_int[m_key].append(ival)
                if eval_ is not None and eval_ > 0: monthly_ext[m_key].append(eval_)

        # Distincts for filters
        def add_distinct(col, key):
            if not col: return
            with connection.cursor() as cur:
                cur.execute(f"SELECT DISTINCT `{col}` FROM `{t}` WHERE `{col}` IS NOT NULL AND `{col}` != ''")
                for r_ in cur.fetchall():
                    distincts[key].add(str(r_[0]).strip())

        add_distinct(oem_col, "providers")
        add_distinct(state_col, "states")
        add_distinct(site_col, "sites")
        add_distinct(wtg_col, "wtgs")

    all_wtgs = sorted(set(list(wtg_int_list.keys()) + list(wtg_ext_list.keys())))
    wtg_data = []
    for w in all_wtgs:
        i_avg = round(sum(wtg_int_list[w]) / len(wtg_int_list[w]), 2) if wtg_int_list[w] else 0.0
        e_avg = round(sum(wtg_ext_list[w]) / len(wtg_ext_list[w]), 2) if wtg_ext_list[w] else 0.0
        c_avg = round((i_avg * e_avg) / 100.0, 2) if (i_avg and e_avg) else max(i_avg, e_avg)
        meta = wtg_meta.get(w, {"oem": "Wind", "site": "-", "state": "-"})
        wtg_data.append({
            "wtg": w,
            "int_ga": i_avg,
            "ext_ga": e_avg,
            "comb_ga": c_avg,
            "oem": meta["oem"],
            "site": meta["site"],
            "state": meta["state"],
            "status": "Excellent" if c_avg >= 98.0 else ("Good" if c_avg >= 95.0 else "Warning")
        })

    wtg_data.sort(key=lambda x: x["comb_ga"], reverse=True)
    for rank, item in enumerate(wtg_data, 1):
        item["rank"] = rank

    fleet_int = round(sum(d["int_ga"] for d in wtg_data) / len(wtg_data), 2) if wtg_data else 0.0
    fleet_ext = round(sum(d["ext_ga"] for d in wtg_data) / len(wtg_data), 2) if wtg_data else 0.0
    fleet_comb = round(sum(d["comb_ga"] for d in wtg_data) / len(wtg_data), 2) if wtg_data else 0.0
    underperforming = sum(1 for d in wtg_data if d["comb_ga"] < 95.0)

    sorted_months = sorted(set(list(monthly_int.keys()) + list(monthly_ext.keys())))[-12:]
    month_int_series = [round(sum(monthly_int[m]) / len(monthly_int[m]), 2) if monthly_int[m] else 0.0 for m in sorted_months]
    month_ext_series = [round(sum(monthly_ext[m]) / len(monthly_ext[m]), 2) if monthly_ext[m] else 0.0 for m in sorted_months]

    context = {
        "kpi_fleet_int": fleet_int,
        "kpi_fleet_ext": fleet_ext,
        "kpi_fleet_comb": fleet_comb,
        "kpi_underperforming": underperforming,
        "kpi_total_wtgs": len(wtg_data),

        "table_data": wtg_data,
        "all_wtgs_json": json.dumps(wtg_data),

        "monthly_cats_json": json.dumps(sorted_months),
        "monthly_int_json": json.dumps(month_int_series),
        "monthly_ext_json": json.dumps(month_ext_series),

        # Filters
        "date_from": date_from,
        "date_to": date_to,
        "providers": sorted(distincts["providers"]),
        "states": sorted(distincts["states"]),
        "sites": sorted(distincts["sites"]),
        "wtgs": sorted(distincts["wtgs"]),
        "selected_providers": providers,
        "selected_states": states,
        "selected_sites": sites,
        "selected_wtgs": wtgs,
    }

    return render(request, "wind_Grid_Availability.html", context)


def _normalize(name):
    """Simplify column name for matching"""
    return re.sub(r'[^a-z0-9]', '', name.lower())

def _pick(col_map, *candidates):
    """
    Return the actual-cased column name if it matches any of the candidates.
    Handles dots, spaces, underscores, and case insensitivity.
    """
    normalized_map = {_normalize(k): v for k, v in col_map.items()}
    for c in candidates:
        norm_c = _normalize(c)
        if norm_c in normalized_map:
            return normalized_map[norm_c]
    return None


@login_required
def wind_breakdown_hours(request):
    username = request.user.username.lower()
    is_admin = request.user.is_superuser or username == "admin"

    if request.GET.get("clear_filters"):
        request.session.pop("wind_filters", None)

    saved = request.session.get("wind_filters", {})
    def get_or_saved_list(key):
        vals = request.GET.getlist(key)
        return vals if vals else saved.get(key, [])

    date_from = request.GET.get("date_from") or saved.get("date_from")
    date_to   = request.GET.get("date_to")   or saved.get("date_to")
    providers = get_or_saved_list("provider")
    customers = get_or_saved_list("customer")
    states    = get_or_saved_list("state")
    sites     = get_or_saved_list("site")
    wtgs      = get_or_saved_list("wtg")

    request.session["wind_filters"] = {
        "date_from": date_from, "date_to": date_to,
        "provider": providers, "customer": customers,
        "state": states, "site": sites, "wtg": wtgs,
    }
    request.session.modified = True

    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES")
        db_tables = [row[0] for row in cursor.fetchall()]

    if is_admin:
        table_names = [t for t in db_tables if t.endswith("_wind_breakdowndata")]
    else:
        table_names = [t for t in db_tables if t.startswith(username + "_") and t.endswith("_wind_breakdowndata")]

    def _normalize(s):
        return s.lower().replace(" ", "").replace("_", "").replace(".", "").replace("(", "").replace(")", "").replace("%", "")

    def _pick(cmap, *candidates):
        for cand in candidates:
            c_norm = _normalize(cand)
            if c_norm in cmap:
                return cmap[c_norm]
        return None

    if not date_from or not date_to:
        min_dates, max_dates = [], []
        for t in table_names:
            with connection.cursor() as cursor:
                cursor.execute(f"SHOW COLUMNS FROM `{t}`")
                cols = {c[0].lower(): c[0] for c in cursor.fetchall()}
                col_norm = {_normalize(c): c for c in cols.values()}
                dcol = _pick(col_norm, "date", "gen_date", "reading_date", "day_date")
                if dcol:
                    cursor.execute(f"SELECT MIN(`{dcol}`), MAX(`{dcol}`) FROM `{t}` WHERE `{dcol}` IS NOT NULL")
                    row = cursor.fetchone()
                    if row and row[0] and row[1]:
                        min_dates.append(str(row[0]))
                        max_dates.append(str(row[1]))
        if min_dates and max_dates:
            date_from = date_from or min(min_dates)
            date_to = date_to or max(max_dates)

    wtg_hrs = defaultdict(float)
    wtg_cnt = defaultdict(int)
    wtg_meta = {}
    cause_hrs = defaultdict(float)
    monthly_hrs = defaultdict(float)
    distincts = {"providers": set(), "customers": set(), "states": set(), "sites": set(), "wtgs": set()}

    for t in table_names:
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{t}`")
            cols = [c[0] for c in cursor.fetchall()]
        col_norm = {_normalize(c): c for c in cols}

        wtg_col = _pick(col_norm, "loc_no", "location", "turbine_id", "location_no", "wtg", "locno")
        dur_col = _pick(col_norm, "total_duration", "duration", "hours", "breakdown_hours")
        err_col = _pick(col_norm, "error_description", "error_details", "description", "reason")
        date_col = _pick(col_norm, "date", "gen_date", "reading_date")
        month_col = _pick(col_norm, "month", "mon")
        oem_col = _pick(col_norm, "provider", "oem")

        if not wtg_col or not dur_col:
            continue

        select_cols = [f"`{wtg_col}`", f"`{dur_col}`"]
        if err_col: select_cols.append(f"`{err_col}`")
        if date_col: select_cols.append(f"`{date_col}`")
        if month_col: select_cols.append(f"`{month_col}`")
        if oem_col: select_cols.append(f"`{oem_col}`")

        where_conds = [f"`{wtg_col}` IS NOT NULL AND `{wtg_col}` != ''"]
        params = []
        if date_col and date_from and date_to:
            where_conds.append(f"`{date_col}` BETWEEN %s AND %s")
            params.extend([date_from, date_to])

        def add_in(col, vals):
            if col and vals:
                q = ",".join(["%s"] * len(vals))
                where_conds.append(f"`{col}` IN ({q})")
                params.extend(vals)

        add_in(oem_col, providers)
        add_in(wtg_col, wtgs)

        where_clause = " WHERE " + " AND ".join(where_conds)
        sql = f"SELECT {', '.join(select_cols)} FROM `{t}` {where_clause}"

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()

        idx = {c.strip("`"): i for i, c in enumerate(select_cols)}

        for r in rows:
            wtg_val = str(r[idx[wtg_col]]).strip()
            if not wtg_val or wtg_val.lower() in ("none", "total", "all wtg"):
                continue

            dur = 0.0
            if r[idx[dur_col]] not in (None, ""):
                try: dur = float(r[idx[dur_col]])
                except: pass

            wtg_hrs[wtg_val] += dur
            wtg_cnt[wtg_val] += 1

            if err_col and r[idx[err_col]]:
                err_text = str(r[idx[err_col]]).strip()
                if len(err_text) > 40: err_text = err_text[:40] + "..."
                cause_hrs[err_text] += dur

            if wtg_val not in wtg_meta:
                wtg_meta[wtg_val] = {
                    "oem": str(r[idx[oem_col]]).strip() if oem_col and r[idx[oem_col]] else ("Senvion" if "senvion" in t else ("Regen" if "regen" in t else "Wind"))
                }

            m_key = None
            if date_col and r[idx[date_col]]:
                m_key = str(r[idx[date_col]])[:7]
            elif month_col and r[idx[month_col]]:
                m_key = str(r[idx[month_col]]).strip()

            if m_key:
                monthly_hrs[m_key] += dur

        def add_distinct(col, key):
            if not col: return
            with connection.cursor() as cur:
                cur.execute(f"SELECT DISTINCT `{col}` FROM `{t}` WHERE `{col}` IS NOT NULL AND `{col}` != ''")
                for r_ in cur.fetchall():
                    distincts[key].add(str(r_[0]).strip())

        add_distinct(oem_col, "providers")
        add_distinct(wtg_col, "wtgs")

    wtg_data = []
    for w, hrs in wtg_hrs.items():
        meta = wtg_meta.get(w, {"oem": "Wind"})
        incidents = wtg_cnt[w]
        avg_dur = round(hrs / incidents, 2) if incidents else 0.0
        wtg_data.append({
            "wtg": w,
            "hours": round(hrs, 2),
            "incidents": incidents,
            "avg_incident_dur": avg_dur,
            "oem": meta["oem"],
            "status": "Critical" if hrs > 1500 else ("Moderate" if hrs > 500 else "Normal")
        })

    wtg_data.sort(key=lambda x: x["hours"], reverse=True)
    for rank, item in enumerate(wtg_data, 1):
        item["rank"] = rank

    total_hrs = round(sum(d["hours"] for d in wtg_data), 2)
    avg_wtg_hrs = round(total_hrs / len(wtg_data), 2) if wtg_data else 0.0
    worst_wtg = wtg_data[0] if wtg_data else {"wtg": "-", "hours": 0}
    total_incidents = sum(d["incidents"] for d in wtg_data)

    sorted_months = sorted(monthly_hrs.keys())[-12:]
    month_series = [round(monthly_hrs[m], 2) for m in sorted_months]

    top_causes = [{"cause": c, "hours": round(h, 1)} for c, h in sorted(cause_hrs.items(), key=lambda x: x[1], reverse=True)[:5]]

    context = {
        "kpi_total_hrs": total_hrs,
        "kpi_worst_wtg": worst_wtg["wtg"],
        "kpi_worst_hrs": worst_wtg["hours"],
        "kpi_avg_hrs": avg_wtg_hrs,
        "kpi_total_incidents": total_incidents,
        "kpi_total_wtgs": len(wtg_data),

        "table_data": wtg_data,
        "all_wtgs_json": json.dumps(wtg_data),

        "monthly_cats_json": json.dumps(sorted_months),
        "monthly_bd_json": json.dumps(month_series),
        "top_causes_json": json.dumps(top_causes),

        # Filters
        "date_from": date_from,
        "date_to": date_to,
        "providers": sorted(distincts["providers"]),
        "wtgs": sorted(distincts["wtgs"]),
        "selected_providers": providers,
        "selected_wtgs": wtgs,
    }

    return render(request, "wind_breakdown_hours.html", context)


def _normalize_key(s: str):
    return re.sub(r'[\s\._\-()%]', '', (s or "").lower())

def _pick(col_map, *candidates):
    """
    Pick actual column name from col_map by comparing normalized forms.
    col_map: dict mapping original_column_name -> original_column_name
    candidates: possible names to match
    Returns actual original column name or None
    """
    # Create normalized map: norm -> original
    norm_map = { _normalize_key(k): k for k in col_map.keys() }
    for c in candidates:
        if not c:
            continue
        norm = _normalize_key(c)
        if norm in norm_map:
            return norm_map[norm]
    # fallback: try partial match (candidate contained in column)
    for c in candidates:
        if not c:
            continue
        norm = _normalize_key(c)
        for k in col_map.keys():
            if norm in _normalize_key(k):
                return k
    return None

def parse_date_like(value):
    """Return date object or None. Accepts many formats."""
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    s = str(value).strip()
    if not s:
        return None
    fmts = ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d-%b-%Y", "%d %b %Y"]
    for f in fmts:
        try:
            return datetime.strptime(s, f).date()
        except Exception:
            continue
    # try ISO parse
    try:
        return datetime.fromisoformat(s).date()
    except Exception:
        return None

def parse_time_to_hours(v):
    """
    Convert a value representing hours/time to float hours.
    Handles:
     - numeric strings / ints / floats -> returned as float
     - "1 day 02:30:00" -> days*24 + hours + minutes/60 + seconds/3600
     - "02:30" or "2:30" -> hours + minutes/60
     - "hh:mm:ss"
     - "24" -> 24.0
    Returns None if cannot parse.
    """
    if v is None:
        return None
    # if already numeric
    try:
        return float(v)
    except Exception:
        pass
    s = str(v).strip()
    if not s:
        return None

    # pattern: "X day(s) HH:MM:SS" or "X day HH:MM"
    m = re.match(r'(?:(\d+)\s*day[s]?\s*)?(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?$', s, re.IGNORECASE)
    if m:
        days = int(m.group(1)) if m.group(1) else 0
        hrs = int(m.group(2))
        mins = int(m.group(3))
        secs = int(m.group(4)) if m.group(4) else 0
        return days * 24.0 + hrs + mins / 60.0 + secs / 3600.0

    # pattern like "1 day" or "2 days"
    m2 = re.match(r'^(\d+)\s*day[s]?$', s, re.IGNORECASE)
    if m2:
        return float(int(m2.group(1)) * 24)

    # pattern like "HH:MM:SS"
    m3 = re.match(r'^(\d{1,2}):(\d{1,2}):(\d{1,2})$', s)
    if m3:
        hrs = int(m3.group(1))
        mins = int(m3.group(2))
        secs = int(m3.group(3))
        return hrs + mins / 60.0 + secs / 3600.0

    # pattern like "HH:MM"
    m4 = re.match(r'^(\d{1,2}):(\d{1,2})$', s)
    if m4:
        hrs = int(m4.group(1))
        mins = int(m4.group(2))
        return hrs + mins / 60.0

    # fallback: extract first numeric token
    m5 = re.search(r'[-+]?\d*\.?\d+', s)
    if m5:
        try:
            return float(m5.group(0))
        except:
            return None

    return None

@login_required
def wind_breakdown_log(request):
    username = request.user.username.lower()
    is_admin = request.user.is_superuser or username == 'admin'

    if request.GET.get("clear_filters"):
        request.session.pop("wind_filters", None)

    saved = request.session.get("wind_filters", {})
    def get_or_saved_list(key):
        vals = request.GET.getlist(key)
        return vals if vals else saved.get(key, [])

    raw_date_from = request.GET.get("date_from") or saved.get("date_from")
    raw_date_to   = request.GET.get("date_to")   or saved.get("date_to")
    providers = get_or_saved_list("provider")
    customers = get_or_saved_list("customer")
    states    = get_or_saved_list("state")
    sites     = get_or_saved_list("site")
    wtgs      = get_or_saved_list("wtg")

    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        all_tables = [r[0] for r in cursor.fetchall()]

    if is_admin:
        bd_tables = [t for t in all_tables if t.endswith("_wind_breakdowndata")]
        main_tables = [t for t in all_tables if t.endswith("_wind") and not t.endswith("_breakdowndata")]
    else:
        bd_tables = [t for t in all_tables if t.startswith(username + "_") and t.endswith("_wind_breakdowndata")]
        main_tables = [t for t in all_tables if t.startswith(username + "_") and t.endswith("_wind") and not t.endswith("_breakdowndata")]

    def _normalize(s):
        return s.lower().replace(" ", "").replace("_", "").replace(".", "").replace("(", "").replace(")", "").replace("%", "")

    def _pick(cmap, *candidates):
        for cand in candidates:
            c_norm = _normalize(cand)
            if c_norm in cmap:
                return cmap[c_norm]
        return None

    # Auto date detection
    if not raw_date_from or not raw_date_to:
        min_dates, max_dates = [], []
        check_tables = bd_tables if bd_tables else main_tables
        for t in check_tables:
            with connection.cursor() as cur:
                cur.execute(f"SHOW COLUMNS FROM `{t}`")
                cols = {c[0].lower(): c[0] for c in cur.fetchall()}
                col_norm = {_normalize(c): c for c in cols.values()}
                dcol = _pick(col_norm, "date", "gen_date", "reading_date")
                if dcol:
                    cur.execute(f"SELECT MIN(`{dcol}`), MAX(`{dcol}`) FROM `{t}` WHERE `{dcol}` IS NOT NULL")
                    row = cur.fetchone()
                    if row and row[0] and row[1]:
                        min_dates.append(str(row[0]))
                        max_dates.append(str(row[1]))
        if min_dates and max_dates:
            raw_date_from = raw_date_from or min(min_dates)
            raw_date_to = raw_date_to or max(max_dates)

    request.session["wind_filters"] = {
        "date_from": raw_date_from, "date_to": raw_date_to,
        "provider": providers, "customer": customers,
        "state": states, "site": sites, "wtg": wtgs,
    }
    request.session.modified = True

    breakdown_records = []
    distincts = {"providers": set(), "customers": set(), "states": set(), "sites": set(), "wtgs": set()}
    total_hours = 0.0

    target_tables = bd_tables if bd_tables else main_tables

    for t in target_tables:
        with connection.cursor() as cur:
            cur.execute(f"SHOW COLUMNS FROM `{t}`")
            cols = [c[0] for c in cur.fetchall()]
        col_norm = {_normalize(c): c for c in cols}

        date_col = _pick(col_norm, "date", "gen_date", "reading_date")
        wtg_col = _pick(col_norm, "loc_no", "location", "turbine_id", "location_no", "wtg", "locno", "wec")
        dur_col = _pick(col_norm, "total_duration", "duration", "hours", "breakdown_hours", "l_hrs", "lhrs")
        err_col = _pick(col_norm, "error_description", "error_details", "error_code", "cause", "remarks", "remark")
        act_col = _pick(col_norm, "action_taken_remark", "action_taken", "remark")
        oem_col = _pick(col_norm, "provider", "oem")
        site_col = _pick(col_norm, "site", "sitename", "location", "plant", "park")
        state_col = _pick(col_norm, "state", "statename")
        cust_col = _pick(col_norm, "customer", "customername")

        if not wtg_col or not dur_col:
            continue

        select_cols = [f"`{wtg_col}`", f"`{dur_col}`"]
        if date_col: select_cols.append(f"`{date_col}`")
        if err_col: select_cols.append(f"`{err_col}`")
        if act_col and act_col != err_col: select_cols.append(f"`{act_col}`")
        if oem_col: select_cols.append(f"`{oem_col}`")
        if site_col and site_col != wtg_col: select_cols.append(f"`{site_col}`")
        if state_col: select_cols.append(f"`{state_col}`")
        if cust_col: select_cols.append(f"`{cust_col}`")

        where_conds = [f"`{wtg_col}` IS NOT NULL AND `{wtg_col}` != ''"]
        params = []
        if date_col and raw_date_from and raw_date_to:
            where_conds.append(f"`{date_col}` BETWEEN %s AND %s")
            params.extend([raw_date_from, raw_date_to])

        def add_in(col, vals):
            if col and vals:
                q = ",".join(["%s"] * len(vals))
                where_conds.append(f"`{col}` IN ({q})")
                params.extend(vals)

        add_in(oem_col, providers)
        add_in(cust_col, customers)
        add_in(state_col, states)
        add_in(site_col, sites)
        add_in(wtg_col, wtgs)

        where_clause = " WHERE " + " AND ".join(where_conds)
        sql = f"SELECT {', '.join(select_cols)} FROM `{t}` {where_clause} ORDER BY CAST(`{dur_col}` AS DECIMAL(15,2)) DESC LIMIT 500"

        with connection.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

        idx = {c.strip("`"): i for i, c in enumerate(select_cols)}

        for r in rows:
            w_val = str(r[idx[wtg_col]]).strip()
            if not w_val or w_val.lower() in ("none", "total", "all wtg"):
                continue

            dur_val = 0.0
            if r[idx[dur_col]] not in (None, ""):
                try: dur_val = float(r[idx[dur_col]])
                except: pass

            total_hours += dur_val

            d_str = str(r[idx[date_col]])[:10] if date_col and r[idx[date_col]] else "-"
            err_text = str(r[idx[err_col]]).strip() if err_col and r[idx[err_col]] else "Trip / Outage"
            act_text = str(r[idx[act_col]]).strip() if act_col and act_col != err_col and r[idx[act_col]] else "Restored to normal operation"
            oem_text = str(r[idx[oem_col]]).strip() if oem_col and r[idx[oem_col]] else ("Senvion" if "senvion" in t else ("Regen" if "regen" in t else "Wind"))

            breakdown_records.append({
                "date": d_str,
                "wtg": w_val,
                "provider": oem_text,
                "error_details": err_text,
                "remark": err_text,
                "breakdown_hours": round(dur_val, 2),
                "duration": round(dur_val, 2),
                "action": act_text,
                "site": str(r[idx[site_col]]).strip() if site_col and site_col != wtg_col and r[idx[site_col]] else "-",
                "state": str(r[idx[state_col]]).strip() if state_col and r[idx[state_col]] else "-",
                "customer": str(r[idx[cust_col]]).strip() if cust_col and r[idx[cust_col]] else "-"
            })

            if oem_col and r[idx[oem_col]]: distincts["providers"].add(str(r[idx[oem_col]]).strip())
            distincts["wtgs"].add(w_val)

    # Sort descending by duration
    breakdown_records.sort(key=lambda x: x["duration"], reverse=True)

    page = request.GET.get("page", 1)
    paginator = Paginator(breakdown_records, 25)
    try:
        page_obj = paginator.page(page)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.page(1)

    return render(request, "wind_breakdown_log.html", {
        "data": breakdown_records,
        "breakdown_data": json.dumps(list(page_obj.object_list)),
        "providers": sorted(distincts["providers"]),
        "customers": sorted(distincts["customers"]),
        "states": sorted(distincts["states"]),
        "sites": sorted(distincts["sites"]),
        "wtgs": sorted(distincts["wtgs"]),
        "selected_providers": providers,
        "selected_customers": customers,
        "selected_states": states,
        "selected_sites": sites,
        "selected_wtgs": wtgs,
        "date_from": raw_date_from,
        "date_to": raw_date_to,
        "total_hours": round(total_hours, 2),
        "paginator": paginator,
        "page_obj": page_obj,
        "no_data": len(breakdown_records) == 0,
        "no_data_msg": "No breakdown records found for selected filters." if len(breakdown_records) == 0 else "",
    })


@login_required
def dashboard_breakdown(request):
    username = request.user.username.lower()
    is_admin = request.user.is_superuser or username == "admin"

    if request.GET.get("clear_filters"):
        request.session.pop("wind_filters", None)

    saved = request.session.get("wind_filters", {})
    def get_or_saved_list(key):
        vals = request.GET.getlist(key)
        return vals if vals else saved.get(key, [])

    date_from = request.GET.get("date_from") or saved.get("date_from")
    date_to   = request.GET.get("date_to")   or saved.get("date_to")
    providers = get_or_saved_list("provider")
    customers = get_or_saved_list("customer")
    states    = get_or_saved_list("state")
    sites     = get_or_saved_list("site")
    wtgs      = get_or_saved_list("wtg")

    request.session["wind_filters"] = {
        "date_from": date_from, "date_to": date_to,
        "provider": providers, "customer": customers,
        "state": states, "site": sites, "wtg": wtgs,
    }
    request.session.modified = True

    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES")
        db_tables = [row[0] for row in cursor.fetchall()]

    if is_admin:
        table_names = [t for t in db_tables if t.endswith("_wind_breakdowndata")]
    else:
        table_names = [t for t in db_tables if t.startswith(username + "_") and t.endswith("_wind_breakdowndata")]

    def _normalize(s):
        return s.lower().replace(" ", "").replace("_", "").replace(".", "").replace("(", "").replace(")", "").replace("%", "")

    def _pick(cmap, *candidates):
        for cand in candidates:
            c_norm = _normalize(cand)
            if c_norm in cmap:
                return cmap[c_norm]
        return None

    if not date_from or not date_to:
        min_dates, max_dates = [], []
        for t in table_names:
            with connection.cursor() as cursor:
                cursor.execute(f"SHOW COLUMNS FROM `{t}`")
                cols = {c[0].lower(): c[0] for c in cursor.fetchall()}
                col_norm = {_normalize(c): c for c in cols.values()}
                dcol = _pick(col_norm, "date", "gen_date", "reading_date", "day_date")
                if dcol:
                    cursor.execute(f"SELECT MIN(`{dcol}`), MAX(`{dcol}`) FROM `{t}` WHERE `{dcol}` IS NOT NULL")
                    row = cursor.fetchone()
                    if row and row[0] and row[1]:
                        min_dates.append(str(row[0]))
                        max_dates.append(str(row[1]))
        if min_dates and max_dates:
            date_from = date_from or min(min_dates)
            date_to = date_to or max(max_dates)

    wtg_hrs = defaultdict(float)
    wtg_cnt = defaultdict(int)
    wtg_meta = {}
    cause_hrs = defaultdict(float)
    monthly_hrs = defaultdict(float)
    distincts = {"providers": set(), "customers": set(), "states": set(), "sites": set(), "wtgs": set()}

    for t in table_names:
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{t}`")
            cols = [c[0] for c in cursor.fetchall()]
        col_norm = {_normalize(c): c for c in cols}

        wtg_col = _pick(col_norm, "loc_no", "location", "turbine_id", "location_no", "wtg", "locno")
        dur_col = _pick(col_norm, "total_duration", "duration", "hours", "breakdown_hours")
        err_col = _pick(col_norm, "error_description", "error_details", "description", "reason")
        date_col = _pick(col_norm, "date", "gen_date", "reading_date")
        month_col = _pick(col_norm, "month", "mon")
        oem_col = _pick(col_norm, "provider", "oem")

        if not wtg_col or not dur_col:
            continue

        select_cols = [f"`{wtg_col}`", f"`{dur_col}`"]
        if err_col: select_cols.append(f"`{err_col}`")
        if date_col: select_cols.append(f"`{date_col}`")
        if month_col: select_cols.append(f"`{month_col}`")
        if oem_col: select_cols.append(f"`{oem_col}`")

        where_conds = [f"`{wtg_col}` IS NOT NULL AND `{wtg_col}` != ''"]
        params = []
        if date_col and date_from and date_to:
            where_conds.append(f"`{date_col}` BETWEEN %s AND %s")
            params.extend([date_from, date_to])

        def add_in(col, vals):
            if col and vals:
                q = ",".join(["%s"] * len(vals))
                where_conds.append(f"`{col}` IN ({q})")
                params.extend(vals)

        add_in(oem_col, providers)
        add_in(wtg_col, wtgs)

        where_clause = " WHERE " + " AND ".join(where_conds)
        sql = f"SELECT {', '.join(select_cols)} FROM `{t}` {where_clause}"

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()

        idx = {c.strip("`"): i for i, c in enumerate(select_cols)}

        for r in rows:
            wtg_val = str(r[idx[wtg_col]]).strip()
            if not wtg_val or wtg_val.lower() in ("none", "total", "all wtg"):
                continue

            dur = 0.0
            if r[idx[dur_col]] not in (None, ""):
                try: dur = float(r[idx[dur_col]])
                except: pass

            wtg_hrs[wtg_val] += dur
            wtg_cnt[wtg_val] += 1

            if err_col and r[idx[err_col]]:
                err_text = str(r[idx[err_col]]).strip()
                if len(err_text) > 40: err_text = err_text[:40] + "..."
                cause_hrs[err_text] += dur

            if wtg_val not in wtg_meta:
                wtg_meta[wtg_val] = {
                    "oem": str(r[idx[oem_col]]).strip() if oem_col and r[idx[oem_col]] else ("Senvion" if "senvion" in t else ("Regen" if "regen" in t else "Wind"))
                }

            m_key = None
            if date_col and r[idx[date_col]]:
                m_key = str(r[idx[date_col]])[:7]
            elif month_col and r[idx[month_col]]:
                m_key = str(r[idx[month_col]]).strip()

            if m_key:
                monthly_hrs[m_key] += dur

        def add_distinct(col, key):
            if not col: return
            with connection.cursor() as cur:
                cur.execute(f"SELECT DISTINCT `{col}` FROM `{t}` WHERE `{col}` IS NOT NULL AND `{col}` != ''")
                for r_ in cur.fetchall():
                    distincts[key].add(str(r_[0]).strip())

        add_distinct(oem_col, "providers")
        add_distinct(wtg_col, "wtgs")

    wtg_data = []
    for w, hrs in wtg_hrs.items():
        meta = wtg_meta.get(w, {"oem": "Wind"})
        incidents = wtg_cnt[w]
        avg_dur = round(hrs / incidents, 2) if incidents else 0.0
        wtg_data.append({
            "wtg": w,
            "hours": round(hrs, 2),
            "incidents": incidents,
            "avg_incident_dur": avg_dur,
            "oem": meta["oem"],
            "status": "Critical" if hrs > 1500 else ("Moderate" if hrs > 500 else "Normal")
        })

    wtg_data.sort(key=lambda x: x["hours"], reverse=True)
    for rank, item in enumerate(wtg_data, 1):
        item["rank"] = rank

    total_hrs = round(sum(d["hours"] for d in wtg_data), 2)
    avg_wtg_hrs = round(total_hrs / len(wtg_data), 2) if wtg_data else 0.0
    worst_wtg = wtg_data[0] if wtg_data else {"wtg": "-", "hours": 0}
    total_incidents = sum(d["incidents"] for d in wtg_data)
    avg_trip_dur = round(total_hrs / total_incidents, 2) if total_incidents else 0.0

    sorted_months = sorted(monthly_hrs.keys())[-12:]
    month_series = [round(monthly_hrs[m], 2) for m in sorted_months]

    top_causes = [{"cause": c, "hours": round(h, 1)} for c, h in sorted(cause_hrs.items(), key=lambda x: x[1], reverse=True)[:5]]
    top_cause_name = top_causes[0]["cause"] if top_causes else "None"
    top_cause_hrs = top_causes[0]["hours"] if top_causes else 0.0

    context = {
        "kpi_total_hrs": total_hrs,
        "kpi_worst_wtg": worst_wtg["wtg"],
        "kpi_worst_hrs": worst_wtg["hours"],
        "kpi_top_cause": top_cause_name,
        "kpi_top_cause_hrs": top_cause_hrs,
        "kpi_total_incidents": total_incidents,
        "kpi_avg_trip_dur": avg_trip_dur,
        "kpi_total_wtgs": len(wtg_data),

        "table_data": wtg_data,
        "all_wtgs_json": json.dumps(wtg_data),

        "monthly_cats_json": json.dumps(sorted_months),
        "monthly_bd_json": json.dumps(month_series),
        "top_causes_json": json.dumps(top_causes),

        # Filters
        "date_from": date_from,
        "date_to": date_to,
        "providers": sorted(distincts["providers"]),
        "wtgs": sorted(distincts["wtgs"]),
        "selected_providers": providers,
        "selected_wtgs": wtgs,
    }

    return render(request, "dashboard_breakdown.html", context)


@login_required
def Modifydata(request):
    user = request.user

    # --- Fetch all tables belonging to this user ---
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
              AND table_name LIKE %s
        """, [f"{user.username}_%"])
        tables = [row[0] for row in cursor.fetchall()]

    expected_tables = [{'name': t, 'label': t.replace('_', ' - ')} for t in tables]

    if request.method == "POST":
        table_name = request.POST.get('table_name')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        # --- Validation checks ---
        if not all([table_name, start_date, end_date]):
            messages.error(request, "⚠️ All fields are required.")
            return redirect('Modifydata')

        if table_name not in tables:
            messages.error(request, "❌ Invalid table selected.")
            return redirect('Modifydata')

        try:
            # --- Convert date strings to datetime.date objects ---
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()

            if start_dt > end_dt:
                messages.error(request, "⚠️ Start date cannot be after end date.")
                return redirect('Modifydata')

            # --- Detect date column name dynamically ---
            with connection.cursor() as cursor:
                cursor.execute(f"SHOW COLUMNS FROM `{table_name}`;")
                columns = [row[0].lower() for row in cursor.fetchall()]

            date_col = None
            for candidate in ["tdate", "gen_date", "date"]:
                if candidate.lower() in columns:
                    date_col = candidate
                    break

            if not date_col:
                messages.error(request, "❌ No valid date column found in the selected table.")
                return redirect('Modifydata')

            # --- Perform delete operation ---
            with connection.cursor() as cursor:
                query = f"""
                    DELETE FROM `{table_name}`
                    WHERE `{date_col}` BETWEEN %s AND %s
                """
                cursor.execute(query, [start_date, end_date])
                rows_deleted = cursor.rowcount

            # --- Feedback message ---
            if rows_deleted > 0:
                messages.success(
                    request,
                    f"✅ Deleted {rows_deleted} rows from {table_name} "
                    f"between {start_date} and {end_date}."
                )
            else:
                messages.warning(
                    request,
                    f"⚠️ No rows found in {table_name} between {start_date} and {end_date}."
                )

            return redirect('Modifydata')

        except Exception as e:
            messages.error(request, f"❌ Error occurred: {str(e)}")
            return redirect('Modifydata')

    return render(request, 'Modifydata.html', {
        'expected_tables': expected_tables,
    })





from datetime import date, timedelta, datetime
from django.utils.timezone import now

def auto_reset_completed_tasks(username=None):
    """
    Automatically reset completed monthly/quarterly/yearly checkpoints 
    when a new period starts.
    """
    from datetime import date
    today = date.today()

    with connection.cursor() as cursor:
        # Example: reset Monthly checkpoints older than 30 days
        cursor.execute(f"""
            UPDATE preventive_maintenance_with_wtg
            SET status='Pending', completed_on=NULL
            WHERE checkpoints_period='Monthly'
            AND status='Completed'
            AND completed_on IS NOT NULL
            AND completed_on <= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            {f"AND username='{username}'" if username else ""}
        """)

        # Quarterly reset example (older than 90 days)
        cursor.execute(f"""
            UPDATE preventive_maintenance_with_wtg
            SET status='Pending', completed_on=NULL
            WHERE checkpoints_period='Quarterly'
            AND status='Completed'
            AND completed_on IS NOT NULL
            AND completed_on <= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
            {f"AND username='{username}'" if username else ""}
        """)

        # Yearly reset example (older than 365 days)
        cursor.execute(f"""
            UPDATE preventive_maintenance_with_wtg
            SET status='Pending', completed_on=NULL
            WHERE checkpoints_period='Yearly'
            AND status='Completed'
            AND completed_on IS NOT NULL
            AND completed_on <= DATE_SUB(CURDATE(), INTERVAL 365 DAY)
            {f"AND username='{username}'" if username else ""}
        """)

    print(f"🔁 Auto-reset executed for {username or 'all users'} ✅")




PM_TABLE_NAME = "preventive_maintenance_data"
PM_WTG_TABLE = "preventive_maintenance_with_wtg"

def ensure_wtg_table():
    """Ensure WTG table exists and unique constraint is correctly applied."""
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        tables = [r[0] for r in cursor.fetchall()]

        if PM_WTG_TABLE not in tables:
            cursor.execute(f"""
                CREATE TABLE `{PM_WTG_TABLE}` (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    username TEXT,
                    wtg_no TEXT,
                    site TEXT,
                    state TEXT,
                    energy_type TEXT,
                    mw TEXT,
                    checkpoints_period TEXT,
                    category TEXT,
                    sub_category TEXT,
                    duration TEXT,
                    status TEXT DEFAULT 'Pending',
                    remarks TEXT,
                    completed_on DATE,
                    FOREIGN KEY (user_id) REFERENCES auth_user(id) ON DELETE CASCADE
                );
            """)

        # 🧹 Drop any old conflicting constraints
        for idx in ["unique_wtg_checkpoint", "unique_wtg_checkpoint_per_unit", "unique_wtg_checkpoint_final"]:
            try:
                cursor.execute(f"ALTER TABLE `{PM_WTG_TABLE}` DROP INDEX {idx};")
            except Exception:
                pass

        # 🔍 Remove internal duplicates automatically (same WTG + same checkpoint)
        try:
            cursor.execute(f"""
                DELETE t1 FROM `{PM_WTG_TABLE}` t1
                JOIN `{PM_WTG_TABLE}` t2
                ON t1.id > t2.id
                AND t1.username = t2.username
                AND t1.wtg_no = t2.wtg_no
                AND t1.category = t2.category
                AND t1.sub_category = t2.sub_category
                AND t1.duration = t2.duration
                AND t1.checkpoints_period = t2.checkpoints_period
                AND t1.mw = t2.mw;
            """)
        except Exception:
            pass

        # ✅ Add the final unique key
        try:
            cursor.execute(f"""
                ALTER TABLE `{PM_WTG_TABLE}`
                ADD UNIQUE KEY unique_wtg_checkpoint_final
                (`username`(50), `wtg_no`(50), `category`(100),
                 `sub_category`(100), `duration`(50),
                 `checkpoints_period`(50), `mw`(50));
            """)
        except Exception:
            pass

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import connection

PM_TABLE_NAME = "preventive_maintenance_data"
PM_WTG_TABLE = "preventive_maintenance_with_wtg"


@login_required
def my_preventive_maintenance(request):
    """
    User-side page: view, upload, and manage user's own preventive maintenance records.
    Also allows registering WTGs to create per-WTG checklists.
    """
    user = request.user
    username = user.username
    ensure_wtg_table()
    auto_reset_completed_tasks(request.user.username)

    # ------------------ REGISTER WTG ------------------ #
    if request.method == "POST" and request.POST.get("register_wtg") == "1":
        wtg_no = request.POST.get("wtg_no", "").strip()
        site = request.POST.get("site", "").strip()
        state = request.POST.get("state", "").strip()

        if not wtg_no or not site or not state:
            messages.error(request, "Please fill all WTG details.")
            return redirect("my_preventive_maintenance")

        try:
            # Fetch all user checkpoints from PM table
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    SELECT energy_type, mw, checkpoints_period, category, sub_category, duration
                    FROM `{PM_TABLE_NAME}`
                    WHERE username = %s
                """, [username])
                rows = cursor.fetchall()

            if not rows:
                messages.warning(request, "No maintenance checkpoints found to copy.")
                return redirect("my_preventive_maintenance")

            # Insert each checkpoint — silently ignore duplicates
            with connection.cursor() as cursor:
                for r in rows:
                    energy_type, mw, period, category, sub_category, duration = r
                    cursor.execute(f"""
                        INSERT IGNORE INTO `{PM_WTG_TABLE}`
                        (user_id, username, wtg_no, site, state, energy_type, mw, checkpoints_period,
                         category, sub_category, duration, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Pending')
                    """, [user.id, username, wtg_no, site, state,
                          energy_type, mw, period, category, sub_category, duration])

            messages.success(request, f"✅ WTG '{wtg_no}' registered successfully.")
        except Exception as e:
            messages.error(request, f"❌ Error registering WTG: {e}")

        return redirect("my_preventive_maintenance")

    # ------------------ FETCH USER RECORDS ------------------ #
    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT id, category, sub_category, duration, checkpoints_period, mw, description, energy_type
            FROM `{PM_TABLE_NAME}`
            WHERE username = %s
            ORDER BY id DESC
        """, [username])
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
    records = [dict(zip(columns, r)) for r in rows]

    # ------------------ DELETE RECORD ------------------ #
    if request.method == "POST" and request.POST.get("delete_id"):
        delete_id = request.POST.get("delete_id")
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"DELETE FROM `{PM_TABLE_NAME}` WHERE id=%s AND username=%s", [delete_id, username])
            messages.success(request, f"🗑️ Record {delete_id} deleted successfully.")
        except Exception as e:
            messages.error(request, f"❌ Delete failed: {e}")
        return redirect("my_preventive_maintenance")

    # ------------------ EDIT RECORD ------------------ #
    if request.method == "POST" and request.POST.get("edit_id"):
        edit_id = request.POST.get("edit_id")
        cat = request.POST.get("edit_category")
        subcat = request.POST.get("edit_sub_category")
        dur = request.POST.get("edit_duration")
        desc = request.POST.get("edit_description")
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    UPDATE `{PM_TABLE_NAME}`
                    SET category=%s, sub_category=%s, duration=%s, description=%s
                    WHERE id=%s AND username=%s
                """, [cat, subcat, dur, desc, edit_id, username])
            messages.success(request, f"✅ Record {edit_id} updated successfully.")
        except Exception as e:
            messages.error(request, f"❌ Update failed: {e}")
        return redirect("my_preventive_maintenance")

    return render(request, "my_preventive_maintenance.html", {"records": records})








from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import connection
from django.utils import timezone

from datetime import datetime, date, time, timedelta
from dateutil.relativedelta import relativedelta

PM_WTG_TABLE = "preventive_maintenance_with_wtg"


# ============================================================
# SAFE DATE → DATETIME CONVERSION
# ============================================================
def fix_datetime(dt):
    """Convert DATE → DATETIME and make timezone aware."""
    if isinstance(dt, date) and not isinstance(dt, datetime):
        dt = datetime.combine(dt, time.min)

    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())

    return dt


# ============================================================
# REFRESH MAINTENANCE STATUS
# ============================================================
def refresh_pm_status(username):
    now = timezone.now()

    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT id, completed_on, checkpoints_period, duration
            FROM `{PM_WTG_TABLE}`
            WHERE username=%s AND status='Completed'
        """, [username])
        rows = cursor.fetchall()

    for pm_id, completed_on, period, duration in rows:

        if not completed_on or not duration:
            continue

        # FIX CRITICAL ERROR
        completed_on = fix_datetime(completed_on)
        duration = float(duration)

        # ---- NEXT DUE CALCULATION ----
        if period == "Hourly":
            next_due = completed_on + timedelta(hours=duration)

        elif period == "Daily":
            days = int(duration)
            hours = (duration - days) * 24
            next_due = completed_on + timedelta(days=days, hours=hours)

        elif period == "Weekly":
            next_due = completed_on + timedelta(weeks=duration)

        elif period == "Monthly":
            next_due = completed_on + relativedelta(months=duration)

        elif period == "Quarterly":
            next_due = completed_on + relativedelta(months=3 * duration)

        elif period == "Yearly":
            next_due = completed_on + relativedelta(years=duration)

        else:
            continue

        # ---- UPDATE STATUS ----
        if now >= next_due:
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    UPDATE `{PM_WTG_TABLE}`
                    SET status='Pending'
                    WHERE id=%s
                """, [pm_id])


# ============================================================
# HUMAN READABLE TIME
# ============================================================
def humanize_due_time(next_due):
    now = timezone.now()
    delta = next_due - now
    seconds = int(delta.total_seconds())
    overdue = seconds < 0
    seconds = abs(seconds)

    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60

    if days > 0:
        text = f"{days}d {hours}h"
    elif hours > 0:
        text = f"{hours}h {minutes}m"
    else:
        text = f"{minutes}m"

    return f"Overdue by {text}" if overdue else text


# ============================================================
# UPCOMING MAINTENANCE LIST
# ============================================================
def get_upcoming_maintenance(username, limit=10):
    now = timezone.now()
    upcoming = []

    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT id, wtg_no, site, category, sub_category,
                   checkpoints_period, duration, completed_on
            FROM `{PM_WTG_TABLE}`
            WHERE username=%s
        """, [username])
        rows = cursor.fetchall()

    for row in rows:
        pm_id, wtg, site, cat, sub_cat, period, duration, completed_on = row

        if not completed_on or not duration:
            continue

        completed_on = fix_datetime(completed_on)
        duration = float(duration)

        # ---- NEXT DUE ----
        if period == "Hourly":
            next_due = completed_on + timedelta(hours=duration)

        elif period == "Daily":
            days = int(duration)
            hours = (duration - days) * 24
            next_due = completed_on + timedelta(days=days, hours=hours)

        elif period == "Weekly":
            next_due = completed_on + timedelta(weeks=duration)

        elif period == "Monthly":
            next_due = completed_on + relativedelta(months=duration)

        elif period == "Quarterly":
            next_due = completed_on + relativedelta(months=3 * duration)

        elif period == "Yearly":
            next_due = completed_on + relativedelta(years=duration)

        else:
            continue

        upcoming.append({
            "id": pm_id,
            "wtg": wtg,
            "site": site,
            "category": cat,
            "sub_category": sub_cat,
            "next_due": next_due,
            "due_in": humanize_due_time(next_due),
            "status": "Overdue" if next_due < now else "Upcoming"
        })

    upcoming.sort(key=lambda x: x["next_due"])
    return upcoming[:limit]


# ============================================================
# MAIN VIEW
# ============================================================
@login_required
def user_completed_maintenance(request):
    user = request.user
    username = user.username

    # AUTO-UPDATE STATUS
    refresh_pm_status(username)

    # FILTERS
    selected_energy = request.GET.get("energy_type")
    selected_mw = request.GET.get("mw")
    selected_period = request.GET.get("period")
    selected_site = request.GET.get("site")
    selected_wtg = request.GET.get("wtg_no")

    energy_types, mw_list, periods, sites, wtgs = [], [], [], [], []

    upcoming_pm = get_upcoming_maintenance(username, limit=10)

    with connection.cursor() as cursor:

        cursor.execute(
            f"SELECT DISTINCT energy_type FROM `{PM_WTG_TABLE}` WHERE username=%s",
            [username]
        )
        energy_types = [r[0] for r in cursor.fetchall() if r[0]]

        if selected_energy:
            cursor.execute(
                f"""SELECT DISTINCT mw FROM `{PM_WTG_TABLE}`
                    WHERE username=%s AND energy_type=%s""",
                [username, selected_energy]
            )
            mw_list = [r[0] for r in cursor.fetchall() if r[0]]

        if selected_energy and selected_mw:
            cursor.execute(
                f"""SELECT DISTINCT checkpoints_period FROM `{PM_WTG_TABLE}`
                    WHERE username=%s AND energy_type=%s AND mw=%s""",
                [username, selected_energy, selected_mw]
            )
            periods = [r[0] for r in cursor.fetchall() if r[0]]

        if selected_period:
            cursor.execute(
                f"""SELECT DISTINCT site FROM `{PM_WTG_TABLE}`
                    WHERE username=%s AND energy_type=%s AND mw=%s
                      AND checkpoints_period=%s""",
                [username, selected_energy, selected_mw, selected_period]
            )
            sites = [r[0] for r in cursor.fetchall() if r[0]]

        if selected_site:
            cursor.execute(
                f"""SELECT DISTINCT wtg_no FROM `{PM_WTG_TABLE}`
                    WHERE username=%s AND energy_type=%s AND mw=%s
                      AND checkpoints_period=%s AND site=%s""",
                [username, selected_energy, selected_mw, selected_period, selected_site]
            )
            wtgs = [r[0] for r in cursor.fetchall() if r[0]]

    # FETCH RECORDS
    records = []
    if all([selected_energy, selected_mw, selected_period, selected_site, selected_wtg]):
        with connection.cursor() as cursor:
            cursor.execute(f"""
                SELECT id, category, sub_category,
                       checkpoints_period, duration,
                       site, wtg_no, status, completed_on
                FROM `{PM_WTG_TABLE}`
                WHERE username=%s AND energy_type=%s AND mw=%s
                  AND checkpoints_period=%s AND site=%s AND wtg_no=%s
                ORDER BY category
            """, [
                username, selected_energy, selected_mw,
                selected_period, selected_site, selected_wtg
            ])

            cols = [c[0] for c in cursor.description]
            rows = cursor.fetchall()

            for r in rows:
                data = dict(zip(cols, r))

                if data["completed_on"]:
                    data["completed_on"] = fix_datetime(data["completed_on"])

                records.append(data)

    # MARK COMPLETE
    if request.method == "POST" and request.POST.get("complete_id"):
        complete_id = request.POST.get("complete_id")
        remarks = request.POST.get("remarks", "").strip()

        with connection.cursor() as cursor:
            cursor.execute(f"""
                UPDATE `{PM_WTG_TABLE}`
                SET status='Completed',
                    remarks=%s,
                    completed_on=%s
                WHERE id=%s AND username=%s
            """, [
                remarks, timezone.now(), complete_id, username
            ])

        messages.success(request, "Maintenance marked as completed.")
        return redirect("user_completed_maintenance")

    return render(request, "user_completed_maintenance.html", {
        "energy_types": energy_types,
        "mw_list": mw_list,
        "periods": periods,
        "sites": sites,
        "wtgs": wtgs,
        "records": records,
        "selected_energy": selected_energy,
        "selected_mw": selected_mw,
        "selected_period": selected_period,
        "selected_site": selected_site,
        "selected_wtg": selected_wtg,
        "upcoming_pm": upcoming_pm,
    })


from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db import connection
from datetime import date

PM_WTG_TABLE = "preventive_maintenance_with_wtg"  # 🔧 replace with your actual table name


@login_required
def user_pm_report_dashboard(request):
    """User Preventive Maintenance Dashboard with ApexCharts and exportable reports."""
    user = request.user
    username = user.username

    # ✅ Ensure preventive maintenance table exists
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        tables = [r[0] for r in cursor.fetchall()]
    if PM_WTG_TABLE not in tables:
        return render(request, "user_pm_report_dashboard.html", {
            "error": "No preventive maintenance data found."
        })

    # ✅ Fetch overall completed / pending counts
    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT 
                SUM(CASE WHEN status='Completed' THEN 1 ELSE 0 END) AS completed,
                SUM(CASE WHEN status!='Completed' THEN 1 ELSE 0 END) AS pending
            FROM `{PM_WTG_TABLE}`
            WHERE username=%s
        """, [username])
        row = cursor.fetchone()
        completed = row[0] or 0
        pending = row[1] or 0

    total = completed + pending
    completion_rate = round((completed / total) * 100, 1) if total > 0 else 0

    # ✅ WTG-wise completion stats
    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT wtg_no,
                   SUM(CASE WHEN status='Completed' THEN 1 ELSE 0 END) AS completed,
                   SUM(CASE WHEN status!='Completed' THEN 1 ELSE 0 END) AS pending
            FROM `{PM_WTG_TABLE}`
            WHERE username=%s
            GROUP BY wtg_no
        """, [username])
        wtg_stats = cursor.fetchall()

    wtg_labels = [r[0] for r in wtg_stats]
    wtg_completed = [r[1] for r in wtg_stats]
    wtg_pending = [r[2] for r in wtg_stats]

    # ✅ Time trend (by date)
    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT DATE(completed_on), COUNT(*)
            FROM `{PM_WTG_TABLE}`
            WHERE username=%s AND status='Completed' AND completed_on IS NOT NULL
            GROUP BY DATE(completed_on)
            ORDER BY DATE(completed_on)
        """, [username])
        trend_rows = cursor.fetchall()

    trend_dates = [str(r[0]) for r in trend_rows]
    trend_counts = [r[1] for r in trend_rows]

    # ✅ Fetch records for tabs (explicit columns)
    with connection.cursor() as cursor:
        # --- Completed ---
        cursor.execute(f"""
            SELECT wtg_no, site, category, status, completed_on, remarks
            FROM `{PM_WTG_TABLE}`
            WHERE username=%s AND status='Completed'
            ORDER BY completed_on DESC
        """, [username])
        completed_records = [
            dict(zip([c[0] for c in cursor.description], r)) for r in cursor.fetchall()
        ]

        # --- Pending ---
        cursor.execute(f"""
            SELECT wtg_no, site, category, status
            FROM `{PM_WTG_TABLE}`
            WHERE username=%s AND (status!='Completed' OR status IS NULL)
        """, [username])
        pending_records = [
            dict(zip([c[0] for c in cursor.description], r)) for r in cursor.fetchall()
        ]

        # --- All Records ---
        cursor.execute(f"""
            SELECT wtg_no, site, category, status, completed_on
            FROM `{PM_WTG_TABLE}`
            WHERE username=%s
        """, [username])
        all_records = [
            dict(zip([c[0] for c in cursor.description], r)) for r in cursor.fetchall()
        ]

    # ✅ Render final dashboard
    return render(request, "user_pm_report_dashboard.html", {
        "completed": completed,
        "pending": pending,
        "completion_rate": completion_rate,
        "wtg_labels": wtg_labels,
        "wtg_completed": wtg_completed,
        "wtg_pending": wtg_pending,
        "trend_dates": trend_dates,
        "trend_counts": trend_counts,
        "completed_records": completed_records,
        "pending_records": pending_records,
        "all_records": all_records,
    })





import pandas as pd
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from .ml_utils import BreakdownMLAnalyzer
import pandas as pd
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.mail import send_mail
from .ml_utils import BreakdownMLAnalyzer

import pandas as pd
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
from .ml_utils import BreakdownMLAnalyzer


import pandas as pd
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
from .ml_utils import BreakdownMLAnalyzer
import pandas as pd
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
from .ml_utils import BreakdownMLAnalyzer
import pandas as pd
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
from .ml_utils import BreakdownMLAnalyzer
from core.models import UploadMetadata
import pandas as pd
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
from .ml_utils import BreakdownMLAnalyzer


from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
import pandas as pd
from .ml_utils import BreakdownMLAnalyzer


@login_required
def breakdown_analysis(request):
    """
    Breakdown & Downtime Intelligence
    Implements 12 Priority Visuals:
    - Visual #8: Breakdown Downtime Pareto Chart (80/20)
    - Visual #9: Turbine-wise Downtime Stacked Bar Chart
    - Visual #10: Monthly Breakdown Trend (Incidents & Duration)
    - Visual #11: Repetitive & Extended Breakdown Records Table
    - Summary KPI cards & Filter controls
    """
    user = request.user.username.lower().strip()
    is_admin = request.user.is_superuser or user == 'admin'

    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        all_tables = [r[0] for r in cursor.fetchall()]

    if is_admin:
        bd_tables = [t for t in all_tables if 'breakdown' in t and t.endswith('_wind_breakdowndata')]
    else:
        bd_tables = [t for t in all_tables if t.startswith(user + '_') and 'breakdown' in t]

    if not bd_tables:
        return render(request, "breakdown_analysis.html", {
            "no_data": True,
            "error_msg": f"No breakdown tables found for account '{user}'.",
            "total_downtime": 0, "total_incidents": 0, "affected_wtgs": 0,
            "pareto_json": "{}", "stacked_json": "{}", "monthly_trend_json": "{}",
            "extended_records": [], "wtgs": []
        })

    btype = request.GET.get("btype", "pareto")
    date_from = request.GET.get("from") or request.GET.get("date_from")
    date_to = request.GET.get("to") or request.GET.get("date_to")
    wtg_filter = request.GET.get("wtg", "").strip()

    cause_dur = defaultdict(float)
    cause_cnt = defaultdict(int)
    wtg_dur = defaultdict(float)
    wtg_cause_map = defaultdict(lambda: defaultdict(float))
    monthly_incidents = defaultdict(int)
    monthly_dur = defaultdict(float)
    extended_records = []
    all_wtgs_set = set()

    earliest_date = None
    latest_date = None

    for bdt in bd_tables:
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{bdt}`")
            cols = [r[0] for r in cursor.fetchall()]
        col_map = {normalize(c): c for c in cols}

        loc_col = _pick(col_map, "location", "loc_no", "location_no", "wtg", "wtg_no")
        err_col = _pick(col_map, "error_description", "error_details", "error_code", "cause")
        dur_col = _pick(col_map, "total_duration", "duration", "hours")
        date_col = _pick(col_map, "date", "gen_date")
        act_col = _pick(col_map, "action_taken_remark", "action_taken", "remark")

        if not err_col or not dur_col:
            continue

        if date_col and (not date_from or not date_to):
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT MIN(`{date_col}`), MAX(`{date_col}`) FROM `{bdt}` WHERE `{date_col}` IS NOT NULL AND `{date_col}` != ''")
                d_min, d_max = cursor.fetchone()
                if d_min and (not earliest_date or str(d_min) < str(earliest_date)):
                    earliest_date = str(d_min)[:10]
                if d_max and (not latest_date or str(d_max) > str(latest_date)):
                    latest_date = str(d_max)[:10]

        conditions, params = [], []
        if date_from and date_to and date_col:
            conditions.append(f"`{date_col}` BETWEEN %s AND %s")
            params.extend([date_from, date_to])
        if wtg_filter and loc_col:
            conditions.append(f"`{loc_col}` = %s")
            params.append(wtg_filter)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # 1. Pareto Causes
        with connection.cursor() as cursor:
            cursor.execute(f"""
                SELECT TRIM(`{err_col}`) as cause_clean, 
                       SUM(CAST(`{dur_col}` AS DECIMAL(15,2))) as total_dur,
                       COUNT(*) as freq
                FROM `{bdt}`
                {where_clause}
                {"AND" if where_clause else "WHERE"} `{err_col}` IS NOT NULL AND `{err_col}` != ''
                GROUP BY cause_clean
                ORDER BY total_dur DESC
            """, params)
            for cause, dur, cnt in cursor.fetchall():
                c_clean = ' '.join(str(cause).split())
                if c_clean:
                    d_val = float(dur or 0)
                    cause_dur[c_clean] += d_val
                    cause_cnt[c_clean] += cnt

        # 2. Monthly Trend
        if date_col:
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    SELECT SUBSTRING(`{date_col}`, 1, 7) as ym,
                           COUNT(*) as incident_count,
                           SUM(CAST(`{dur_col}` AS DECIMAL(15,2))) as total_dur
                    FROM `{bdt}`
                    {where_clause}
                    {"AND" if where_clause else "WHERE"} `{date_col}` IS NOT NULL AND `{date_col}` != ''
                    GROUP BY ym
                    ORDER BY ym ASC
                """, params)
                for ym, inc, dur in cursor.fetchall():
                    if ym and len(ym) == 7:
                        monthly_incidents[ym] += int(inc)
                        monthly_dur[ym] += float(dur or 0)

        # 3. Turbine Downtime
        if loc_col:
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    SELECT TRIM(`{loc_col}`) as loc,
                           TRIM(`{err_col}`) as cause,
                           SUM(CAST(`{dur_col}` AS DECIMAL(15,2))) as dur
                    FROM `{bdt}`
                    {where_clause}
                    {"AND" if where_clause else "WHERE"} `{loc_col}` IS NOT NULL AND `{loc_col}` != ''
                    GROUP BY loc, cause
                """, params)
                for loc, cause, dur in cursor.fetchall():
                    l_clean = str(loc).strip()
                    c_clean = ' '.join(str(cause).split())
                    d_val = float(dur or 0)
                    if l_clean:
                        all_wtgs_set.add(l_clean)
                        wtg_dur[l_clean] += d_val
                        wtg_cause_map[l_clean][c_clean] += d_val

        # 4. Extended Records (>10h)
        with connection.cursor() as cursor:
            act_sel = f", `{act_col}`" if act_col else ", ''"
            cursor.execute(f"""
                SELECT `{loc_col}`, `{date_col}`, TRIM(`{err_col}`), CAST(`{dur_col}` AS DECIMAL(15,2)) {act_sel}
                FROM `{bdt}`
                {where_clause}
                {"AND" if where_clause else "WHERE"} CAST(`{dur_col}` AS DECIMAL(15,2)) >= 10.0
                ORDER BY CAST(`{dur_col}` AS DECIMAL(15,2)) DESC
                LIMIT 50
            """, params)
            for r in cursor.fetchall():
                extended_records.append({
                    "wtg": r[0],
                    "date": str(r[1])[:10] if r[1] else "",
                    "cause": ' '.join(str(r[2]).split()),
                    "duration": float(r[3] or 0),
                    "action": r[4] if len(r) > 4 else ""
                })

    sorted_causes = sorted(cause_dur.items(), key=lambda x: x[1], reverse=True)
    total_downtime = sum(cause_dur.values())
    total_incidents = sum(cause_cnt.values())

    pareto_categories = []
    pareto_durations = []
    pareto_cum_pct = []
    running_sum = 0.0
    top_causes_list = [c for c, _ in sorted_causes[:5]]

    for cause, dur in sorted_causes[:12]:
        running_sum += dur
        pct = (running_sum / total_downtime * 100) if total_downtime > 0 else 0
        pareto_categories.append(cause[:28] + ("..." if len(cause) > 28 else ""))
        pareto_durations.append(round(dur, 1))
        pareto_cum_pct.append(round(pct, 1))

    sorted_wtgs_bd = sorted(wtg_dur.items(), key=lambda x: x[1], reverse=True)[:10]
    stacked_wtgs = [w for w, _ in sorted_wtgs_bd]

    stacked_series = []
    for cause in top_causes_list:
        data_vals = [round(wtg_cause_map[w].get(cause, 0), 1) for w in stacked_wtgs]
        stacked_series.append({
            "name": cause[:24] + ("..." if len(cause) > 24 else ""),
            "data": data_vals
        })

    sorted_ym = sorted(monthly_incidents.keys())
    recent_ym = sorted_ym[-24:] if len(sorted_ym) > 24 else sorted_ym
    trend_labels = recent_ym
    trend_incidents = [monthly_incidents[m] for m in recent_ym]
    trend_hours = [round(monthly_dur[m], 1) for m in recent_ym]

    top_repeat_cause = sorted(cause_cnt.items(), key=lambda x: x[1], reverse=True)
    top_rep = top_repeat_cause[0] if top_repeat_cause else ("None", 0)

    return render(request, "breakdown_analysis.html", {
        "total_downtime": round(total_downtime, 1),
        "total_incidents": total_incidents,
        "affected_wtgs": len(all_wtgs_set),
        "top_downtime_cause": sorted_causes[0][0] if sorted_causes else "None",
        "top_repeat_cause": top_rep[0],
        "top_repeat_count": top_rep[1],

        "pareto_json": json.dumps({
            "categories": pareto_categories,
            "durations": pareto_durations,
            "cumulative_pct": pareto_cum_pct
        }),
        "stacked_json": json.dumps({
            "categories": stacked_wtgs,
            "series": stacked_series
        }),
        "monthly_trend_json": json.dumps({
            "labels": trend_labels,
            "incidents": trend_incidents,
            "hours": trend_hours
        }),
        "extended_records": extended_records,
        "wtgs": sorted(all_wtgs_set),
        "wtg_filter": wtg_filter,
        "date_from": date_from or earliest_date,
        "date_to": date_to or latest_date,
        "btype": btype,
    })

@login_required
def customer_upload_dsm(request):

    DSM_TABLE_NAME = "dsm_data"

    # Check DSM table exists
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        tables = [r[0] for r in cursor.fetchall()]
        table_exists = DSM_TABLE_NAME in tables

    if request.method == "POST" and "data_file" in request.FILES:

        provider = request.POST.get("provider")
        energy_type = request.POST.get("energy_type")
        uploaded_by = request.user.username  # AUTO SELECT

        data_file = request.FILES["data_file"]

        if not provider or not energy_type:
            messages.error(request, "Please select provider and energy type.")
            return redirect("customer_upload_dsm")

        # Save temp file
        fs = FileSystemStorage()
        filename = fs.save(data_file.name, data_file)
        file_path = fs.path(filename)

        try:
            ext = os.path.splitext(filename)[1].lower()

            if ext == ".csv":
                df = pd.read_csv(file_path)

            elif ext == ".xls":
                xlsx_path = file_path + "x"
                convert_xls_to_xlsx(file_path, xlsx_path)
                df = pd.read_excel(xlsx_path, engine="openpyxl")
                os.remove(xlsx_path)

            elif ext in [".xlsx", ".xlsm", ".xlsb"]:
                df = pd.read_excel(file_path, engine="openpyxl")

            elif ext == ".ods":
                df = pd.read_excel(file_path, engine="odf")

            else:
                messages.error(request, "Unsupported file format.")
                return redirect("customer_upload_dsm")

            if df.empty:
                messages.error(request, "Uploaded file contains no data.")
                return redirect("customer_upload_dsm")

            df.columns = [
                re.sub(r'\W+', '_', str(c).lower()).strip("_")
                for c in df.columns
            ]

            # Add required fields
            df["username"] = uploaded_by
            df["provider"] = provider
            df["energy_type"] = energy_type
            

            df = df.astype(object).where(pd.notnull(df), None)


            with connection.cursor() as cursor:
                cols = ", ".join(f"`{c}`" for c in df.columns)
                q = ", ".join(["%s"] * len(df.columns))
                sql = f"INSERT INTO `{DSM_TABLE_NAME}` ({cols}) VALUES ({q})"

                for _, row in df.iterrows():
                    cursor.execute(sql, list(row.values))

            messages.success(request, f"{len(df)} DSM rows uploaded successfully!")

        except Exception as e:
            messages.error(request, f"Failed: {e}")

        finally:
            fs.delete(filename)

        return redirect("customer_upload_dsm")

    providers = Provider.objects.all()
    energy_types = EnergyType.objects.all()

    return render(request, "upload_customer_dsm_data.html", {
        "providers": providers,
        "energy_types": energy_types,
        "table_exists": table_exists,
    })
from django.core.mail import EmailMultiAlternatives
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required

from django.core.mail import EmailMultiAlternatives
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required


@login_required
def email_breakdown_alerts(request):
    try:
        alerts = request.session.get("bd_alerts", [])
        user = request.user

        if not alerts:
            return JsonResponse({"status": "error", "message": "No alerts available to send."})

        html_content = render_to_string("email_breakdown_alerts.html", {
            "alerts": alerts,
            "username": user.username,
        })

        subject = "Your Breakdown Alert Summary"
        email = EmailMultiAlternatives(
            subject,
            "",
            to=[user.email]  # user email
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

        return JsonResponse({"status": "success", "message": "Breakdown alerts emailed successfully!"})

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})













import os, re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # REQUIRED for Django
import matplotlib.pyplot as plt

import os, re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # REQUIRED for Django
import matplotlib.pyplot as plt

from django.conf import settings
from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import os, re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import os, re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from accounts.models import DSMData, DSMResult


# =====================
# CONFIG
# =====================
USE_DUMMY_DATA = True


# =====================
# HELPERS
# =====================
def clean(v):
    if v is None:
        return None
    if isinstance(v, float) and pd.isna(v):
        return None
    return float(v)


from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from accounts.models import DSMResult  # <-- Ensure imported

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from django.conf import settings

from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score



# =====================
# CONFIG
# =====================
USE_DUMMY_DATA = True



# =====================
# DSM RATE FUNCTION
# =====================
def dsm_rate(error_pct, energy):
    energy = str(energy).lower()

    if energy == "solar":
        if error_pct <= 10: return 0
        elif error_pct <= 12: return 0.25
        elif error_pct <= 15: return 0.50
        elif error_pct <= 25: return 0.75
        else: return 1.00
    else:  # wind
        if error_pct <= 10: return 0
        elif error_pct <= 12: return 0
        elif error_pct <= 15: return 0.25
        elif error_pct <= 25: return 0.50
        else: return 1.00



# =====================
# MAIN DASHBOARD VIEW
# =====================
@login_required
def dsm_dashboard(request):

    # ------------------- SAVE BUTTON -------------------
    if request.method == "POST" and request.POST.get("action") == "save":
        DSMResult.objects.create(
            user=request.user,
            total_dsm=request.POST.get("total_dsm"),
            next_month_dsm=request.POST.get("next_month_dsm"),
            mae=request.POST.get("mae"),
            rmse=request.POST.get("rmse"),
            r2=request.POST.get("r2"),
            forecast_total=request.POST.get("forecast_total"),
            forecast_avg=request.POST.get("forecast_avg"),
            forecast_max=request.POST.get("forecast_max"),
        )
        messages.success(request, "DSM result saved successfully!")
        return redirect("dsm_dashboard")

    # ===================== UPDATED GET BLOCK =====================
    if request.method == "GET":
        history = DSMResult.objects.filter(user=request.user).order_by("-created_at")
        last = history.first()

        # If last saved result exists → Load dashboard with previous data
        if last:
            context = {
                "history": history,
                "total_dsm": last.total_dsm,
                "next_month_dsm": last.next_month_dsm,
                "model_metrics": {
                    "mae": last.mae,
                    "rmse": last.rmse,
                    "r2": last.r2,
                },
                "forecast": {
                    "total_forecast": last.forecast_total,
                    "avg_forecast": last.forecast_avg,
                    "max_forecast": last.forecast_max,
                },
                "img_url": settings.MEDIA_URL + "dsm_trend.png",
                "next_img_url": settings.MEDIA_URL + "next_month_deviation.png",
                "weekly_img_url": settings.MEDIA_URL + "weekly_dsm.png",
            }
            return render(request, "dsm.html", context)

        # No past result → blank dashboard
        return render(request, "dsm.html", {"history": history})

    # ===================== FILE UPLOAD PROCESS =====================
    if "dsm_file" not in request.FILES:
        messages.error(request, "Please upload DSM Excel file")
        return render(request, "dsm.html")

    try:
        df = pd.read_excel(request.FILES["dsm_file"])
    except Exception as e:
        messages.error(request, f"Excel read error: {e}")
        return render(request, "dsm.html")

    df.columns = df.columns.str.strip()

    df[['Date', 'TimeBlock']] = df['Date and Time Block'].str.split(r'\s{2,}', expand=True)
    df['Block_Start'] = df['TimeBlock'].str.split('-').str[0].str.strip()

    df['DateTime'] = pd.to_datetime(
        df['Date'] + ' ' + df['Block_Start'],
        dayfirst=True,
        errors="coerce"
    )
    df = df.dropna(subset=["DateTime"])

    df['block_of_day'] = ((df['DateTime'].dt.hour * 60 + df['DateTime'].dt.minute) // 15) + 1

    np.random.seed(42)
    if USE_DUMMY_DATA:
        df['Actual_Generation'] = df['Forecasted Schedule (MAL)'] * (1 + np.random.uniform(-0.2, 0.2, len(df)))
    else:
        df['Actual_Generation'] = df['SEM Final']

    df = df[df['Forecasted Schedule (MAL)'] != 0]

    df['Deviation_kW'] = df['Actual_Generation'] - df['Forecasted Schedule (MAL)']
    df['Error_pct'] = abs(df['Deviation_kW']) / df['Forecasted Schedule (MAL)'] * 100

    df['DSM_Rate'] = df.apply(lambda r: dsm_rate(r['Error_pct'], r['Energy type']), axis=1)
    df['DSM_Charge_Rs'] = df['DSM_Rate'] * abs(df['Deviation_kW']) * 0.25

    total_dsm = round(df['DSM_Charge_Rs'].sum(), 2)

    forecast = {
        "total_forecast": round(df['Forecasted Schedule (MAL)'].sum(), 2),
        "avg_forecast": round(df['Forecasted Schedule (MAL)'].mean(), 2),
        "max_forecast": round(df['Forecasted Schedule (MAL)'].max(), 2),
    }

    le_pool = LabelEncoder()
    le_energy = LabelEncoder()
    df['pool_code'] = le_pool.fit_transform(df['Pooling Station'])
    df['energy_code'] = le_energy.fit_transform(df['Energy type'])

    X = df[['Forecasted Schedule (MAL)', 'AVC', 'block_of_day', 'pool_code', 'energy_code']]
    y = df['Deviation_kW']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = RandomForestRegressor(n_estimators=120, random_state=42)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    model_metrics = {
        "mae": round(mean_absolute_error(y_test, y_pred), 2),
        "rmse": round(np.sqrt(mean_squared_error(y_test, y_pred)), 2),
        "r2": round(r2_score(y_test, y_pred), 3),
    }

    # ===================== NEXT MONTH FORECAST =====================
    days = 30
    blocks = days * 96

    future = pd.DataFrame({
        'Forecasted Schedule (MAL)': [df['Forecasted Schedule (MAL)'].mean()] * blocks,
        'AVC': [df['AVC'].mean()] * blocks,
        'block_of_day': list(range(1, 97)) * days,
        'pool_code': [df['pool_code'].mode()[0]] * blocks,
        'energy_code': [df['energy_code'].mode()[0]] * blocks
    })

    future['predicted_deviation_kw'] = model.predict(future)
    future['error_pct'] = abs(future['predicted_deviation_kw']) / future['Forecasted Schedule (MAL)'] * 100

    future['dsm_rate'] = future['error_pct'].apply(lambda x: dsm_rate(x, 'solar'))
    future['predicted_dsm_rs'] = future['dsm_rate'] * abs(future['predicted_deviation_kw']) * 0.25

    next_month_dsm = round(future['predicted_dsm_rs'].sum(), 2)

    # ===================== CHARTS =====================
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

    plt.figure(figsize=(9, 4))
    df.groupby(df['DateTime'].dt.date)['Deviation_kW'].mean().plot()
    plt.title("Daily Deviation Trend")
    plt.tight_layout()
    plt.savefig(os.path.join(settings.MEDIA_ROOT, "dsm_trend.png"))
    plt.close()

    future["day"] = np.repeat(range(1, days + 1), 96)
    plt.figure(figsize=(9, 4))
    future.groupby("day")["predicted_deviation_kw"].mean().plot()
    plt.title("Predicted Deviation – Next Month")
    plt.tight_layout()
    plt.savefig(os.path.join(settings.MEDIA_ROOT, "next_month_deviation.png"))
    plt.close()

    df['Week'] = df['DateTime'].dt.isocalendar().week
    plt.figure(figsize=(7, 4))
    df.groupby("Week")["DSM_Charge_Rs"].sum().plot(kind="bar")
    plt.title("Weekly DSM Charges")
    plt.tight_layout()
    plt.savefig(os.path.join(settings.MEDIA_ROOT, "weekly_dsm.png"))
    plt.close()

    history = DSMResult.objects.filter(user=request.user).order_by("-created_at")
    messages.success(request, "DSM analytics processed successfully!")

    return render(request, "dsm.html", {
        "total_dsm": total_dsm,
        "forecast": forecast,
        "model_metrics": model_metrics,
        "next_month_dsm": next_month_dsm,
        "img_url": settings.MEDIA_URL + "dsm_trend.png",
        "next_img_url": settings.MEDIA_URL + "next_month_deviation.png",
        "weekly_img_url": settings.MEDIA_URL + "weekly_dsm.png",
        "history": history,
    })
# ======================
# HISTORY PAGE
# ======================
@login_required
def dsm_history(request):
    results = DSMResult.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "dsm_history.html", {"results": results})


@login_required
def export_dsm_history(request):
    results = DSMResult.objects.filter(user=request.user).order_by("-created_at")

    if not results.exists():
        messages.error(request, "No history available to export.")
        return redirect("dsm_dashboard")

    # Convert queryset → DataFrame
    df = pd.DataFrame(list(results.values()))

    # Remove timezone from datetime columns
    for col in df.columns:
        if "date" in col or "time" in col or "created" in col:
            try:
                df[col] = pd.to_datetime(df[col]).dt.tz_localize(None)
            except:
                pass

    # Remove unneeded fields
    drop_cols = ["id", "user_id"]
    df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")

    file_path = os.path.join(settings.MEDIA_ROOT, "dsm_history_export.xlsx")
    df.to_excel(file_path, index=False)

    with open(file_path, "rb") as f:
        file_data = f.read()

    response = HttpResponse(
        file_data,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = "attachment; filename=dsm_history.xlsx"
    return response
