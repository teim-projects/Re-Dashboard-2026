from django.shortcuts import render

def wind_dashboard(request):
    return render(request, 'wind_dashboard.html')  # Wind Dashboard

from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.db.utils import ProgrammingError

from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
from django.db.utils import ProgrammingError

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
    user = request.user.username.lower()

    # ---------------------------------------------------
    # CLEAR FILTERS (RESET GLOBAL FILTER SESSION)
    # ---------------------------------------------------
    if request.GET.get("clear_filters"):
        request.session.pop("wind_filters", None)

    # ---------------------------------------------------
    # RESTORE SAVED FILTERS
    # ---------------------------------------------------
    saved = request.session.get("wind_filters", {})

    def get_or_saved_list(key):
        vals = request.GET.getlist(key)
        return vals if vals else saved.get(key, [])

    date_from = request.GET.get("date_from") or saved.get("date_from")
    date_to   = request.GET.get("date_to")   or saved.get("date_to")

    providers = get_or_saved_list("provider")
    uploaded_by = get_or_saved_list("uploaded_by")
    customers = get_or_saved_list("customer")
    states    = get_or_saved_list("state")
    sites     = get_or_saved_list("site")
    wtgs      = get_or_saved_list("wtg")

    # ---------------------------------------------------
    # AUTO DATE RANGE (3 YEARS)
    # ---------------------------------------------------
    from datetime import date, timedelta
    if not date_from and not date_to:
        today = date.today()
        auto_from = today - timedelta(days=3 * 365)
        date_from = auto_from.strftime("%Y-%m-%d")
        date_to = today.strftime("%Y-%m-%d")

    # ---------------------------------------------------
    # SAVE FILTERS BACK TO SESSION (GLOBAL)
    # ---------------------------------------------------
    request.session["wind_filters"] = {
        "date_from": date_from,
        "date_to": date_to,
        "provider": providers,
        "uploaded_by": uploaded_by,
        "customer": customers,
        "state": states,
        "site": sites,
        "wtg": wtgs,
    }
    request.session.modified = True

    # ---------------------------------------------------
    # FIND USER WIND TABLES
    # ---------------------------------------------------
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        db_tables = [r[0] for r in cursor.fetchall()]

    table_names = [t for t in db_tables if t.startswith(user + "_") and t.endswith("_wind")]

    if not table_names:
        return render(request, "wind_generation_kwh.html", {
            "chart_data": "[]",
            "table_data": [],
            "total_generation": 0,
            "providers": [], "customers": [], "states": [], "sites": [], "wtgs": [],
            "selected_providers": providers,
            "selected_customers": customers,
            "selected_states": states,
            "selected_sites": sites,
            "selected_wtgs": wtgs,
            "date_from": date_from, "date_to": date_to,
            "no_data": True,
            "no_data_msg": "No wind generation data found."
        })

    # ---------------------------------------------------
    # PROCESS GENERATION (kWh)
    # ---------------------------------------------------
    from collections import defaultdict
    wtg_sum = defaultdict(float)
    distincts = {k: set() for k in ["providers", "customers", "states", "sites", "wtgs"]}

    for table_name in table_names:
        # Read schema
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
            cols = [r[0] for r in cursor.fetchall()]
        col_map = {normalize(c): c for c in cols}

        # Flexible mapping
        wtg_col = _pick(col_map, "wtg", "wtg_no", "loc_no", "wec")
        gen_col = _pick(col_map, "gen_kwh_day", "gen_kwh", "generation", "kwh")
        date_col = _pick(col_map, "gen_date", "date")
        provider_col = _pick(col_map, "provider", "oem")
        customer_col = _pick(col_map, "customer", "customer_name")
        state_col = _pick(col_map, "state")
        site_col = _pick(col_map, "site", "wind_farm_name")

        if not wtg_col or not gen_col:
            continue

        # Build conditions
        conditions, params = [], []

        if date_from and date_to:
            conditions.append(f"`{date_col}` BETWEEN %s AND %s")
            params.extend([date_from, date_to])

        def add_in(col, values):
            if col and values:
                placeholders = ",".join(["%s"] * len(values))
                conditions.append(f"`{col}` IN ({placeholders})")
                params.extend(values)

        add_in(provider_col, providers)
        add_in(customer_col, customers)
        add_in(state_col, states)
        add_in(site_col, sites)
        add_in(wtg_col, wtgs)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
            SELECT `{wtg_col}`, SUM(`{gen_col}`)
            FROM `{table_name}`
            {where_clause}
            GROUP BY `{wtg_col}`
        """

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        for w, g in rows:
            wtg_sum[str(w)] += float(g or 0)

        # Distinct filter values
        def dist(col):
            if not col: return []
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT DISTINCT `{col}` FROM `{table_name}` ORDER BY `{col}`")
                return [str(r[0]) for r in cursor.fetchall()]

        distincts["providers"].update(dist(provider_col))
        distincts["customers"].update(dist(customer_col))
        distincts["states"].update(dist(state_col))
        distincts["sites"].update(dist(site_col))
        distincts["wtgs"].update(dist(wtg_col))

    # Final output
    chart_data = [{"wtg": k, "generation": v} for k, v in wtg_sum.items()]
    chart_data.sort(key=lambda x: x["generation"], reverse=True)

    table_data = [{"wtg_no": d["wtg"], "generation": d["generation"]} for d in chart_data]

    return render(request, "wind_generation_kwh.html", {
        "chart_data": json.dumps(chart_data),
        "table_data": table_data,
        "total_generation": sum(wtg_sum.values()),

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

        "date_from": date_from,
        "date_to": date_to,
    })

from collections import defaultdict
from datetime import datetime, date  # ✅ keep original classes
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
import json

def _pick(col_map, *candidates):
    """Return actual-cased column name if it matches any candidate"""
    for c in candidates:
        lc = c.lower()
        if lc in col_map:
            return col_map[lc]
    return None

def parse_date_like(v):
    """Parse date/datetime strings or objects into date object (SAFE)"""
    # ✅ DO NOT overwrite 'date' or 'datetime'
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if v is None:
        return None

    s = str(v).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d-%b-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except:
            continue
    return None  # ✅ return None if no format matches






def parse_hours(val):
    """Convert numeric or hh:mm:ss style strings to float hours"""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)

    s = str(val).strip()
    if " " in s:
        parts = s.split(" ")
        try:
            days = int(parts[0])
        except:
            days = 0
        hms = parts[1] if len(parts) > 1 else "0:0:0"
    else:
        days = 0
        hms = s

    try:
        hms_parts = [int(p) for p in hms.split(":")]
    except:
        hms_parts = [0, 0, 0]

    hours = days * 24 + hms_parts[0] + hms_parts[1] / 60 + hms_parts[2] / 3600
    return hours

def parse_hours(val):
    """Convert numeric or hh:mm:ss style strings to float hours"""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)

    s = str(val).strip()
    if " " in s:
        parts = s.split(" ")
        try:
            days = int(parts[0])
        except:
            days = 0
        hms = parts[1] if len(parts) > 1 else "0:0:0"
    else:
        days = 0
        hms = s

    try:
        hh, mm, ss = map(int, hms.split(":"))
    except:
        hh, mm, ss = 0, 0, 0

    return days * 24 + hh + mm / 60 + ss / 3600


def parse_date_like(val):
    """Parse DB date formats safely"""
    if isinstance(val, date):
        return val
    try:
        return datetime.strptime(str(val), "%Y-%m-%d").date()
    except:
        try:
            return datetime.strptime(str(val), "%d-%m-%Y").date()
        except:
            return None


@login_required
def wind_generation_hours(request):
    user = request.user.username.lower()

    # ---------------------------------------------------
    # CLEAR FILTERS
    # ---------------------------------------------------
    if request.GET.get("clear_filters"):
        request.session.pop("wind_filters", None)

    # ---------------------------------------------------
    # RESTORE FILTERS FROM SESSION (GLOBAL)
    # ---------------------------------------------------
    saved = request.session.get("wind_filters", {})

    def get_or_saved_list(key):
        vals = request.GET.getlist(key)
        return vals if vals else saved.get(key, [])

    date_from = request.GET.get("date_from") or saved.get("date_from")
    date_to   = request.GET.get("date_to")   or saved.get("date_to")

    providers = get_or_saved_list("provider")
    uploaded_by = get_or_saved_list("uploaded_by")
    customers = get_or_saved_list("customer")
    states    = get_or_saved_list("state")
    sites     = get_or_saved_list("site")
    wtgs      = get_or_saved_list("wtg")

    # ---------------------------------------------------
    # AUTO DEFAULT DATE RANGE (3 YEARS)
    # ---------------------------------------------------
    if not date_from and not date_to:
        today = date.today()
        auto_from = today - timedelta(days=3*365)
        date_from = auto_from.strftime("%Y-%m-%d")
        date_to   = today.strftime("%Y-%m-%d")

    # ---------------------------------------------------
    # SAVE FILTERS BACK INTO SESSION (GLOBAL)
    # ---------------------------------------------------
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

    # ---------------------------------------------------
    # GET WIND TABLES FOR USER
    # ---------------------------------------------------
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        db_tables = [row[0] for row in cursor.fetchall()]

    table_names = [
        t for t in db_tables
        if t.startswith(user + "_") and t.endswith("_wind")
    ]

    if not table_names:
        return render(request, "wind_genration_hovers.html", {
            "chart_data": "[]",
            "table_data": [],
            "years": [],
            "total_hours": 0,

            "providers": [], "customers": [], "states": [], "sites": [], "wtgs": [],
            "selected_providers": providers,
            "selected_customers": customers,
            "selected_states": states,
            "selected_sites": sites,
            "selected_wtgs": wtgs,

            "date_from": date_from,
            "date_to": date_to,

            "no_data": True,
            "no_data_msg": "No wind data found."
        })

    # ---------------------------------------------------
    # PROCESS HOURS DATA
    # ---------------------------------------------------
    from collections import defaultdict

    wtg_year_hours = defaultdict(float)
    distincts = {k: set() for k in ["providers", "customers", "states", "sites", "wtgs"]}
    years_set = set()
    total_hours = 0.0

    for table_name in table_names:

        # Load schema
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
            cols = [r[0] for r in cursor.fetchall()]
        col_map = {normalize(c): c for c in cols}

        # Dynamic column names
        date_col = _pick(col_map, "date", "gen_date", "reading_date", "day_date")
        wtg_col = _pick(col_map, "wtg", "wtg_no", "loc_no", "wec")

        genhrs_col = _pick(col_map, "genhrs", "gen_hours", "generationhours")
        ohrs_col   = _pick(col_map, "ohrs", "operatinghours")
        loss_col   = _pick(col_map, "lhrs", "loss", "losshrs")

        provider_col = _pick(col_map, "provider", "oem")
        customer_col = _pick(col_map, "customer", "client")
        state_col    = _pick(col_map, "state")
        site_col     = _pick(col_map, "site")

        if not date_col or not wtg_col:
            continue

        # Build filter conditions
        conditions, params = [], []

        if date_from and date_to:
            conditions.append(f"`{date_col}` BETWEEN %s AND %s")
            params.extend([date_from, date_to])

        def add_in(col, values):
            if col and values:
                placeholders = ",".join(["%s"] * len(values))
                conditions.append(f"`{col}` IN ({placeholders})")
                params.extend(values)

        add_in(provider_col, providers)
        add_in(customer_col, customers)
        add_in(state_col, states)
        add_in(site_col, sites)
        add_in(wtg_col, wtgs)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # Choose hours expression
        if ohrs_col and loss_col:
            hour_expr = f"(`{ohrs_col}` - `{loss_col}`)"
        elif genhrs_col:
            hour_expr = f"`{genhrs_col}`"
        elif ohrs_col:
            hour_expr = f"`{ohrs_col}`"
        else:
            continue

        # Main query
        query = f"""
            SELECT `{date_col}`, `{wtg_col}`, SUM({hour_expr})
            FROM `{table_name}`
            {where_clause}
            GROUP BY `{date_col}`, `{wtg_col}`
        """

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        # Process rows
        for d_val, wtg_val, hrs in rows:
            d_obj = parse_date_like(d_val)
            if not d_obj:
                continue

            year = d_obj.year
            years_set.add(year)

            wtg_name = str(wtg_val)
            hour_val = float(hrs or 0)

            wtg_year_hours[(wtg_name, year)] += hour_val
            total_hours += hour_val

        # Distinct values
        def distinct_list(col):
            if not col:
                return []
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT DISTINCT `{col}` FROM `{table_name}` ORDER BY `{col}`")
                return [str(r[0]) for r in cursor.fetchall() if r[0]]

        distincts["providers"].update(distinct_list(provider_col))
        distincts["customers"].update(distinct_list(customer_col))
        distincts["states"].update(distinct_list(state_col))
        distincts["sites"].update(distinct_list(site_col))
        distincts["wtgs"].update(distinct_list(wtg_col))

    # Fill missing years
    for wtg in distincts["wtgs"]:
        for yr in years_set:
            wtg_year_hours.setdefault((wtg, yr), 0.0)

    # Prepare chart data
    chart_data = [
        {"wtg": w, "year": y, "hours": round(v, 2)}
        for (w, y), v in sorted(wtg_year_hours.items(), key=lambda x: (x[0][1], x[0][0]))
    ]

    table_data = [
        {"wtg_no": w, "year": y, "hours": round(v, 2)}
        for (w, y), v in wtg_year_hours.items()
    ]

    context = {
        "chart_data": json.dumps(chart_data),
        "table_data": table_data,
        "years": sorted(years_set),
        "total_hours": round(total_hours, 2),

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

        "date_from": date_from,
        "date_to": date_to,

        "no_data": len(chart_data) == 0,
        "no_data_msg": "No generation hour data found." if len(chart_data) == 0 else ""
    }

    return render(request, "wind_genration_hovers.html", context)









from collections import defaultdict
from django.http import HttpResponse
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
import json
from collections import defaultdict
from django.http import HttpResponse
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required


def _pick(col_map, *candidates):
    """Return actual-cased column name if it matches any of the candidates"""
    for c in candidates:
        lc = c.lower()
        if lc in col_map:
            return col_map[lc]
    return None


@login_required
def wind_avg_genration(request):
    user = request.user.username.lower()

    # ---------------------------------------------------
    # CLEAR GLOBAL FILTERS
    # ---------------------------------------------------
    if request.GET.get("clear_filters"):
        request.session.pop("wind_filters", None)

    # ---------------------------------------------------
    # RESTORE FILTERS (GLOBAL SESSION)
    # ---------------------------------------------------
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

    # ---------------------------------------------------
    # AUTO DATE RANGE = LAST 1 YEAR
    # ---------------------------------------------------
    from datetime import date, timedelta
    if not date_from and not date_to:
        today = date.today()
        auto_from = today - timedelta(days=365)
        date_from = auto_from.strftime("%Y-%m-%d")
        date_to   = today.strftime("%Y-%m-%d")

    # ---------------------------------------------------
    # SAVE FILTERS BACK TO SESSION
    # ---------------------------------------------------
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

    # ---------------------------------------------------
    # FIND ALL <username>_*_wind TABLES
    # ---------------------------------------------------
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        db_tables = [row[0] for row in cursor.fetchall()]

    table_names = [
        t for t in db_tables
        if t.startswith(user + "_") and t.endswith("_wind")
    ]

    if not table_names:
        context = {
            "gen_chart_data": "[]",
            "op_chart_data": "[]",
            "overall_gen_avg": 0,
            "overall_op_avg": 0,

            "providers": [], "customers": [], "states": [], "sites": [], "wtgs": [],
            "selected_providers": providers,
            "selected_customers": customers,
            "selected_states": states,
            "selected_sites": sites,
            "selected_wtgs": wtgs,

            "date_from": date_from,
            "date_to": date_to,

            "no_data": True,
            "no_data_msg": "No generation data found."
        }
        return render(request, "wind_avg_genration.html", context)

    # ---------------------------------------------------
    # CALCULATION STORAGE
    # ---------------------------------------------------
    from collections import defaultdict
    gen_avg = defaultdict(list)
    op_avg  = defaultdict(list)

    distincts = {
        "providers": set(), "customers": set(), "states": set(),
        "sites": set(), "wtgs": set()
    }

    # ---------------------------------------------------
    # PROCESS EACH USER TABLE
    # ---------------------------------------------------
    for table_name in table_names:

        # Read schema
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
            cols = [r[0] for r in cursor.fetchall()]
        col_map = {normalize(c): c for c in cols}

        # Flexible dynamic column mapping
        wtg_col  = _pick(col_map, "wtg","wtg_no","loc_no","wec","turbine","turbineno")
        gen_col  = _pick(col_map, "genhrs","gen_hours","generationhours","o_hrs")
        op_col   = _pick(col_map, "ohrs","o_hrs","operatinghours")
        date_col = _pick(col_map, "date","gen_date","reading_date","day_date")

        provider_col = _pick(col_map, "provider","oem")
        customer_col = _pick(col_map, "customer","client","customername")
        state_col    = _pick(col_map, "state")
        site_col     = _pick(col_map, "site","windfarmname","sitename")

        if not wtg_col:
            continue

        # ---------------------------------------------------
        # BUILD FILTER CONDITIONS
        # ---------------------------------------------------
        conditions, params = [], []

        if date_from and date_to:
            conditions.append(f"`{date_col}` BETWEEN %s AND %s")
            params.extend([date_from, date_to])

        def add_in(col, values):
            if col and values:
                q = ",".join(["%s"] * len(values))
                conditions.append(f"`{col}` IN ({q})")
                params.extend(values)

        add_in(provider_col, providers)
        add_in(customer_col, customers)
        add_in(state_col, states)
        add_in(site_col, sites)
        add_in(wtg_col, wtgs)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # ---------------------------------------------------
        # AVG GENERATION HOURS
        # ---------------------------------------------------
        if gen_col:
            q = f"""
                SELECT `{wtg_col}`, AVG(`{gen_col}`)
                FROM `{table_name}`
                {where_clause}
                GROUP BY `{wtg_col}`
            """
            with connection.cursor() as cursor:
                cursor.execute(q, params)
                for w, v in cursor.fetchall():
                    gen_avg[str(w)].append(float(v or 0))

        # ---------------------------------------------------
        # AVG OPERATING HOURS
        # ---------------------------------------------------
        if op_col:
            q = f"""
                SELECT `{wtg_col}`, AVG(`{op_col}`)
                FROM `{table_name}`
                {where_clause}
                GROUP BY `{wtg_col}`
            """
            with connection.cursor() as cursor:
                cursor.execute(q, params)
                for w, v in cursor.fetchall():
                    op_avg[str(w)].append(float(v or 0))

        # ---------------------------------------------------
        # DISTINCT FILTER VALUES
        # ---------------------------------------------------
        def distinct_list(col):
            if not col: return []
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT DISTINCT `{col}` FROM `{table_name}` ORDER BY `{col}`")
                return [str(r[0]) for r in cursor.fetchall() if r[0]]

        distincts["providers"].update(distinct_list(provider_col))
        distincts["customers"].update(distinct_list(customer_col))
        distincts["states"].update(distinct_list(state_col))
        distincts["sites"].update(distinct_list(site_col))
        distincts["wtgs"].update(distinct_list(wtg_col))

    # ---------------------------------------------------
    # PREPARE FINAL CHART DATA
    # ---------------------------------------------------
    gen_final = {w: sum(v)/len(v) for w, v in gen_avg.items() if v}
    op_final  = {w: sum(v)/len(v) for w, v in op_avg.items() if v}

    gen_chart = [{"wtg": w, "hours": round(h, 2)} for w, h in gen_final.items()]
    op_chart  = [{"wtg": w, "hours": round(h, 2)} for w, h in op_final.items()]

    gen_chart.sort(key=lambda x: x["hours"], reverse=True)
    op_chart.sort(key=lambda x: x["hours"], reverse=True)

    # ---------------------------------------------------
    # CONTEXT
    # ---------------------------------------------------
    context = {
        "gen_chart_data": json.dumps(gen_chart),
        "op_chart_data": json.dumps(op_chart),

        "overall_gen_avg": round(sum(d["hours"] for d in gen_chart) / len(gen_chart), 2)
                            if gen_chart else 0,
        "overall_op_avg": round(sum(d["hours"] for d in op_chart) / len(op_chart), 2)
                            if op_chart else 0,

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

        "date_from": date_from,
        "date_to": date_to,
    }

    return render(request, "wind_avg_genration.html", context)



from collections import defaultdict
from datetime import datetime, date
from django.http import HttpResponse
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
import json

from collections import defaultdict
from datetime import datetime, date, timedelta
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
import json


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
    user = request.user.username.lower()

    # ---------------------------------------------------
    # CLEAR FILTERS RESET
    # ---------------------------------------------------
    if request.GET.get("clear_filters"):
        request.session.pop("wind_filters", None)

    # ---------------------------------------------------
    # RESTORE FILTERS FROM SESSION
    # ---------------------------------------------------
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

    # ---------------------------------------------------
    # AUTO DATE RANGE = LAST 1 YEAR
    # ---------------------------------------------------
    from datetime import date, timedelta
    if not date_from and not date_to:
        today = date.today()
        auto_from = today - timedelta(days=365)
        date_from = auto_from.strftime("%Y-%m-%d")
        date_to   = today.strftime("%Y-%m-%d")

    # ---------------------------------------------------
    # SAVE FILTERS BACK TO SESSION
    # ---------------------------------------------------
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

    # ---------------------------------------------------
    # FIND ALL USER WIND TABLES
    # ---------------------------------------------------
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        db_tables = [row[0] for row in cursor.fetchall()]

    table_names = [
        t for t in db_tables
        if t.startswith(user + "_") and t.endswith("_wind")
    ]

    if not table_names:
        return render(request, "wind_Grid_Availability_and_Machine.html", {
            "grid_chart_data": "[]",
            "availability_chart_data": "[]",
            "plf_yearly_data": "[]",
            "plf_monthly_data": "{}",

            "providers": [], "customers": [], "states": [], "sites": [], "wtgs": [],
            "selected_providers": providers,
            "selected_customers": customers,
            "selected_states": states,
            "selected_sites": sites,
            "selected_wtgs": wtgs,

            "date_from": date_from,
            "date_to": date_to,

            "no_data": True,
            "no_data_msg": "No wind tables found."
        })

    # ---------------------------------------------------
    # ACCUMULATORS
    # ---------------------------------------------------
    distincts = {"providers": set(), "customers": set(), "states": set(),
                 "sites": set(), "wtgs": set()}

    year_failure_hours = defaultdict(list)
    month_failure_hours = defaultdict(list)
    year_plf = defaultdict(list)
    month_plf = defaultdict(list)

    # ---------------------------------------------------
    # PROCESS EACH TABLE
    # ---------------------------------------------------
    for table in table_names:

        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{table}`")
            cols = [row[0] for row in cursor.fetchall()]
        col_map = {normalize(c): c for c in cols}

        date_col = _pick(col_map, "date","gen_date","reading_date","day_date","gen_date")
        gf_col   = _pick(col_map, "gf","gridfailure","grid_fail","failurehours")
        ga_col   = _pick(col_map, "ga","gridavailability")
        gia_col  = _pick(col_map, "gia","gridinternalavailability")

        plf_day_col = _pick(col_map, "plf","plf_day","cf","capacityfactor")

        provider_col = _pick(col_map, "provider","oem")
        customer_col = _pick(col_map, "customer","client")
        state_col    = _pick(col_map, "state")
        site_col     = _pick(col_map, "site","windfarmname")
        wtg_col      = _pick(col_map, "wtg","wtgno","locno","wec")

        if not date_col:
            continue

        # ---------------------------------------------------
        # DISTINCT FILTERS
        # ---------------------------------------------------
        def add_distinct(col, key):
            if not col: return
            with connection.cursor() as c:
                c.execute(f"SELECT DISTINCT `{col}` FROM `{table}`")
                for r in c.fetchall():
                    if r[0]:
                        distincts[key].add(str(r[0]).strip())

        add_distinct(provider_col, "providers")
        add_distinct(customer_col, "customers")
        add_distinct(state_col, "states")
        add_distinct(site_col, "sites")
        add_distinct(wtg_col, "wtgs")

        # ---------------------------------------------------
        # WHERE CLAUSE
        # ---------------------------------------------------
        conditions, params = [], []

        if date_from:
            conditions.append(f"`{date_col}` >= %s")
            params.append(date_from)

        if date_to:
            conditions.append(f"`{date_col}` <= %s")
            params.append(date_to)

        def filter_in(col, values):
            if col and values:
                q = ",".join(["%s"] * len(values))
                conditions.append(f"`{col}` IN ({q})")
                params.extend(values)

        filter_in(provider_col, providers)
        filter_in(customer_col, customers)
        filter_in(state_col, states)
        filter_in(site_col, sites)
        filter_in(wtg_col, wtgs)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # ---------------------------------------------------
        # RUN QUERY
        # ---------------------------------------------------
        select_cols = [date_col]
        for c in [gf_col, ga_col, gia_col, plf_day_col]:
            if c:
                select_cols.append(c)

        query = f"""
            SELECT {','.join(f'`{c}`' for c in select_cols)}
            FROM `{table}`
            {where_clause}
        """

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        idx = {c: i for i, c in enumerate(select_cols)}

        # ---------------------------------------------------
        # PROCESS ROWS
        # ---------------------------------------------------
        for r in rows:
            d = parse_date_like(r[idx[date_col]])
            if not d:
                continue

            year = d.year
            month = d.strftime("%Y-%m")

            # FAILURE HOURS
            hrs = 0
            if gf_col and r[idx.get(gf_col)] not in (None, ""):
                hrs = to_hours(r[idx[gf_col]])
            elif ga_col:
                try:
                    ga = float(r[idx[ga_col]])
                    hrs = (100 - ga) * 24 / 100
                except:
                    hrs = 0
            elif gia_col:
                try:
                    gia = float(r[idx[gia_col]])
                    hrs = (100 - gia) * 24 / 100
                except:
                    hrs = 0

            year_failure_hours[year].append(hrs)
            month_failure_hours[month].append(hrs)

            # PLF
            if plf_day_col and r[idx.get(plf_day_col)] not in (None, ""):
                try:
                    val = float(r[idx[plf_day_col]])
                    year_plf[year].append(val)
                    month_plf[month].append(val)
                except:
                    pass

    # ---------------------------------------------------
    # FINAL JSON DATA
    # ---------------------------------------------------
    grid_chart_data = [
        {"year": y, "avg_failure": round(sum(v)/len(v), 2)}
        for y, v in year_failure_hours.items()
    ]

    availability_chart_data = []
    for m, v in month_failure_hours.items():
        avg_f = round(sum(v)/len(v), 2)
        avg_av = round(100 - avg_f, 2)
        machine = min(100, avg_av + 2)

        availability_chart_data.append({
            "month": m,
            "grid_availability": avg_av,
            "machine_availability": machine
        })

    plf_yearly = [
        {"year": y, "avg_plf": round(sum(v)/len(v), 2)}
        for y, v in year_plf.items()
    ]

    plf_monthly_wrapped = defaultdict(list)
    for m, v in month_plf.items():
        y = m.split("-")[0]
        plf_monthly_wrapped[y].append({
            "month": m,
            "avg_plf": round(sum(v)/len(v), 2)
        })

    # ---------------------------------------------------
    # RENDER PAGE
    # ---------------------------------------------------
    return render(request, "wind_Grid_Availability_and_Machine.html", {
        "grid_chart_data": json.dumps(grid_chart_data),
        "availability_chart_data": json.dumps(availability_chart_data),
        "plf_yearly_data": json.dumps(plf_yearly),
        "plf_monthly_data": json.dumps(plf_monthly_wrapped),

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

        "date_from": date_from,
        "date_to": date_to,

        "no_data": False,
    })

from collections import defaultdict
from datetime import datetime, date
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
import json


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
    user = request.user.username.lower()

    # ---------------------------------------------------
    # CLEAR FILTERS
    # ---------------------------------------------------
    if request.GET.get("clear_filters"):
        request.session.pop("wind_filters", None)

    # ---------------------------------------------------
    # RESTORE GLOBAL FILTERS
    # ---------------------------------------------------
    saved = request.session.get("wind_filters", {})

    def get_or_saved_list(key):
        vals = request.GET.getlist(key)
        return vals if vals else saved.get(key, [])

    date_from = request.GET.get("date_from") or saved.get("date_from")
    date_to   = request.GET.get("date_to")   or saved.get("date_to")

    selected_providers = get_or_saved_list("provider")
    selected_customers = get_or_saved_list("customer")
    selected_states    = get_or_saved_list("state")
    selected_sites     = get_or_saved_list("site")
    selected_wtgs      = get_or_saved_list("wtg")

    # ---------------------------------------------------
    # AUTO DATE RANGE: LAST 1 YEAR
    # ---------------------------------------------------
    from datetime import date, timedelta
    if not date_from and not date_to:
        today = date.today()
        auto_from = today - timedelta(days=365)
        date_from = auto_from.strftime("%Y-%m-%d")
        date_to   = today.strftime("%Y-%m-%d")

    # ---------------------------------------------------
    # SAVE FILTERS BACK TO SESSION
    # ---------------------------------------------------
    request.session["wind_filters"] = {
        "date_from": date_from,
        "date_to": date_to,
        "provider": selected_providers,
        "customer": selected_customers,
        "state": selected_states,
        "site": selected_sites,
        "wtg": selected_wtgs,
    }
    request.session.modified = True

    # ---------------------------------------------------
    # FIND ALL USER TABLES
    # ---------------------------------------------------
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        tables = [row[0] for row in cursor.fetchall()]

    table_names = [
        t for t in tables
        if t.startswith(user + "_") and t.endswith("_wind")
    ]

    if not table_names:
        return render(request, "wind_drill_down.html", {
            "site_gen_data": "[]",
            "ma_data": "[]",
            "ga_data": "[]",
            "oh_data": "[]",
            "providers": [], "customers": [], "states": [],
            "sites": [], "wtgs": [],
            "selected_providers": selected_providers,
            "selected_customers": selected_customers,
            "selected_states": selected_states,
            "selected_sites": selected_sites,
            "selected_wtgs": selected_wtgs,
            "date_from": date_from, 
            "date_to": date_to,
            "no_data": True,
            "no_data_msg": "No wind tables found for your account."
        })

    # ---------------------------------------------------
    # ACCUMULATORS
    # ---------------------------------------------------
    site_gen = defaultdict(float)
    ma_by_wec = defaultdict(list)
    ga_by_wec = defaultdict(list)
    oh_by_wec = defaultdict(float)

    providers_set = set()
    customers_set = set()
    states_set = set()
    sites_set = set()
    wtgs_set = set()

    # ---------------------------------------------------
    # PROCESS EVERY WIND TABLE
    # ---------------------------------------------------
    for table in table_names:

        # Load schema
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{table}`")
            cols = [row[0] for row in cursor.fetchall()]
        col_map = {normalize(c): c for c in cols}

        # Flexible dynamic mapping
        date_col = _pick(col_map, "date", "gen_date", "reading_date", "day_date")
        site_col = _pick(col_map, "site", "location", "plant", "park", "windfarmname")
        wec_col  = _pick(col_map, "wec", "wtg", "loc_no", "locno", "wtgno")

        gen_col = _pick(col_map, "generation", "gen", "genkwh", "gen_kwh_day", "gen(kwh)")
        ma_col  = _pick(col_map, "ma", "machineavailability")
        ga_col  = _pick(col_map, "ga", "gridavailability", "gia")

        oh_col = _pick(col_map, "ohrs", "ophrs", "operatinghours")

        provider_col = _pick(col_map, "provider", "oem")
        customer_col = _pick(col_map, "customer", "customername", "client")
        state_col    = _pick(col_map, "state")

        if not date_col:
            continue

        # ---------------------------------------------------
        # BUILD WHERE CLAUSE
        # ---------------------------------------------------
        conditions, params = [], []

        if date_from:
            conditions.append(f"`{date_col}` >= %s")
            params.append(date_from)

        if date_to:
            conditions.append(f"`{date_col}` <= %s")
            params.append(date_to)

        def add_filter(col, values):
            if col and values:
                q = ",".join(["%s"] * len(values))
                conditions.append(f"`{col}` IN ({q})")
                params.extend(values)

        add_filter(provider_col, selected_providers)
        add_filter(customer_col, selected_customers)
        add_filter(state_col, selected_states)
        add_filter(site_col, selected_sites)
        add_filter(wec_col, selected_wtgs)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # ---------------------------------------------------
        # SELECT ONLY REQUIRED COLUMNS
        # ---------------------------------------------------
        select_cols = [
            c for c in 
            [date_col, site_col, wec_col, gen_col, ma_col, ga_col, oh_col,
             provider_col, customer_col, state_col]
            if c
        ]
        select_clause = ", ".join(f"`{c}`" for c in select_cols)

        query = f"SELECT {select_clause} FROM `{table}` {where_clause}"

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        idx = {col: i for i, col in enumerate(select_cols)}

        def val(row, column):
            return row[idx[column]] if column in idx else None

        # ---------------------------------------------------
        # ROW PROCESSING
        # ---------------------------------------------------
        for row in rows:

            d = parse_date_like(val(row, date_col))
            if not d:
                continue

            site_val = val(row, site_col) or "Unknown"
            wec_val  = val(row, wec_col) or "Unknown"

            # Distinct sets
            if provider_col and val(row, provider_col): providers_set.add(str(val(row, provider_col)))
            if customer_col and val(row, customer_col): customers_set.add(str(val(row, customer_col)))
            if state_col and val(row, state_col): states_set.add(str(val(row, state_col)))
            if site_col and val(row, site_col): sites_set.add(str(val(row, site_col)))
            if wec_col and val(row, wec_col): wtgs_set.add(str(val(row, wec_col)))

            # Generation
            try:
                site_gen[site_val] += float(val(row, gen_col) or 0)
            except:
                pass

            # Machine Availability
            if ma_col and val(row, ma_col) not in (None, ""):
                ma_by_wec[wec_val].append(safe_float(val(row, ma_col)))

            # Grid Availability
            if ga_col and val(row, ga_col) not in (None, ""):
                ga_by_wec[wec_val].append(safe_float(val(row, ga_col)))

            # Operating Hours
            if oh_col and val(row, oh_col) not in (None, ""):
                oh_by_wec[wec_val] += safe_float(val(row, oh_col))

    # ---------------------------------------------------
    # FINAL OUTPUT DATA
    # ---------------------------------------------------
    site_gen_data = [{"site": k, "generation": v} for k, v in site_gen.items()]
    ma_data = [{"wec": k, "ma": sum(v)/len(v)} for k, v in ma_by_wec.items()]
    ga_data = [{"wec": k, "ga": sum(v)/len(v)} for k, v in ga_by_wec.items()]
    oh_data = [{"wec": k, "hours": v} for k, v in oh_by_wec.items()]

    # ---------------------------------------------------
    # CONTEXT TO TEMPLATE
    # ---------------------------------------------------
    return render(request, "wind_drill_down.html", {
        "site_gen_data": json.dumps(site_gen_data),
        "ma_data": json.dumps(ma_data),
        "ga_data": json.dumps(ga_data),
        "oh_data": json.dumps(oh_data),

        "providers": sorted(providers_set),
        "customers": sorted(customers_set),
        "states": sorted(states_set),
        "sites": sorted(sites_set),
        "wtgs": sorted(wtgs_set),

        "selected_providers": selected_providers,
        "selected_customers": selected_customers,
        "selected_states": selected_states,
        "selected_sites": selected_sites,
        "selected_wtgs": selected_wtgs,

        "date_from": date_from,
        "date_to": date_to,
        "no_data": False,
    })


from collections import defaultdict
from datetime import datetime, date
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
import json


def _pick(col_map, *candidates):
    """Return the actual column name if it matches any of the candidates"""
    for c in candidates:
        lc = c.lower()
        if lc in col_map:
            return col_map[lc]
    return None


def parse_date_like(v):
    """Parse various date formats to datetime.date"""
    if isinstance(v, datetime): 
        return v.date()
    if isinstance(v, date): 
        return v
    if v is None: 
        return None
    s = str(v).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d-%b-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except:
            continue
    return None

from collections import defaultdict
from django.db import connection
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render
import json

@login_required
def wind_Avg_Machine_Availability(request):
    user = request.user.username.lower()

    # ---------------------------------------------------
    # CLEAR FILTERS
    # ---------------------------------------------------
    if request.GET.get("clear_filters"):
        request.session.pop("wind_filters", None)

    # ---------------------------------------------------
    # RESTORE SESSION FILTERS
    # ---------------------------------------------------
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

    # ---------------------------------------------------
    # AUTO DATE RANGE = LAST 1 YEAR
    # ---------------------------------------------------
    from datetime import date, timedelta
    if not date_from and not date_to:
        today = date.today()
        auto_from = today - timedelta(days=365)
        date_from = auto_from.strftime("%Y-%m-%d")
        date_to   = today.strftime("%Y-%m-%d")

    # ---------------------------------------------------
    # SAVE FILTERS BACK TO SESSION
    # ---------------------------------------------------
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

    # ---------------------------------------------------
    # FIND ALL USER WIND TABLES
    # ---------------------------------------------------
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        db_tables = [row[0] for row in cursor.fetchall()]

    table_names = [
        t for t in db_tables
        if t.startswith(user + "_") and t.endswith("_wind")
    ]

    if not table_names:
        return render(request, "wind_Avg_Machine_Availability.html", {
            "chart_data": "[]",
            "table_data": [],

            "providers": [], "customers": [], "states": [], "sites": [], "wtgs": [],
            "selected_providers": providers,
            "selected_customers": customers,
            "selected_states": states,
            "selected_sites": sites,
            "selected_wtgs": wtgs,

            "date_from": date_from,
            "date_to": date_to,

            "no_data": True,
            "no_data_msg": "No wind tables found for your account.",
            "overall_avg_ma": 0,
            "paginator": None,
            "table_page": None
        })

    # ---------------------------------------------------
    # ACCUMULATORS
    # ---------------------------------------------------
    wtg_ma = defaultdict(list)
    distincts = {
        "providers": set(), "customers": set(), "states": set(),
        "sites": set(), "wtgs": set()
    }

    # ---------------------------------------------------
    # PROCESS EACH WIND TABLE
    # ---------------------------------------------------
    for table_name in table_names:

        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
            cols = [r[0] for r in cursor.fetchall()]
        col_map = {normalize(c): c for c in cols}

        # Dynamic column mapping
        date_col = _pick(col_map, "date", "gen_date", "reading_date", "day_date")
        wtg_col = _pick(col_map, "wec", "wtg", "loc_no", "locno", "turbine")
        ohrs_col = _pick(col_map, "ohrs", "operatinghours", "o_hours")
        loss_col = _pick(col_map, "lhrs", "losshrs", "loss_hours")
        ma_col = _pick(col_map, "ma", "machineavailability", "m/c avail.%", "mc_avail")

        provider_col = _pick(col_map, "provider","oem")
        customer_col = _pick(col_map, "customer","consumer","client")
        state_col    = _pick(col_map, "state","statename")
        site_col     = _pick(col_map, "site","sitename","plant")

        if not date_col or not wtg_col:
            continue

        # ---------------------------------------------------
        # BUILD WHERE CLAUSE
        # ---------------------------------------------------
        conditions, params = [], []

        if date_from and date_to:
            conditions.append(f"`{date_col}` BETWEEN %s AND %s")
            params.extend([date_from, date_to])
        elif date_from:
            conditions.append(f"`{date_col}` >= %s")
            params.append(date_from)
        elif date_to:
            conditions.append(f"`{date_col}` <= %s")
            params.append(date_to)

        def add_in(col, values):
            if col and values:
                q = ",".join(["%s"] * len(values))
                conditions.append(f"`{col}` IN ({q})")
                params.extend(values)

        add_in(provider_col, providers)
        add_in(customer_col, customers)
        add_in(state_col, states)
        add_in(site_col, sites)
        add_in(wtg_col, wtgs)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # ---------------------------------------------------
        # MACHINE AVAILABILITY EXPRESSION
        # ---------------------------------------------------
        if ma_col:
            expr = f"`{ma_col}`"
        elif ohrs_col and loss_col:
            expr = f"(CASE WHEN `{ohrs_col}` > 0 THEN ((`{ohrs_col}`-`{loss_col}`)/`{ohrs_col}`)*100 ELSE 0 END)"
        else:
            continue

        # ---------------------------------------------------
        # QUERY
        # ---------------------------------------------------
        query = f"""
            SELECT `{wtg_col}`, AVG({expr}) AS avg_ma
            FROM `{table_name}`
            {where_clause}
            GROUP BY `{wtg_col}`
        """

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        for wtg_val, ma in rows:
            if not wtg_val:
                continue
            wtg_ma[str(wtg_val)].append(float(ma or 0))

        # ---------------------------------------------------
        # DISTINCT VALUES FOR FILTERS
        # ---------------------------------------------------
        def distinct_list(col):
            if not col:
                return []
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT DISTINCT `{col}` FROM `{table_name}` ORDER BY `{col}`")
                return [str(r[0]) for r in cursor.fetchall() if r[0]]

        distincts["providers"].update(distinct_list(provider_col))
        distincts["customers"].update(distinct_list(customer_col))
        distincts["states"].update(distinct_list(state_col))
        distincts["sites"].update(distinct_list(site_col))
        distincts["wtgs"].update(distinct_list(wtg_col))

    # ---------------------------------------------------
    # FINAL DATA PREPARATION
    # ---------------------------------------------------
    chart_data = [
        {"x": wtg, "y": round(sum(vals) / len(vals), 2)}
        for wtg, vals in wtg_ma.items()
    ]

    table_data = [
        {"wtg_no": wtg, "avg_ma": round(sum(vals) / len(vals), 2)}
        for wtg, vals in wtg_ma.items()
    ]

    # ---------------------------------------------------
    # PAGINATION
    # ---------------------------------------------------
    from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
    page = request.GET.get("page", 1)
    paginator = Paginator(table_data, 10)
    try:
        table_page = paginator.page(page)
    except PageNotAnInteger:
        table_page = paginator.page(1)
    except EmptyPage:
        table_page = paginator.page(paginator.num_pages)

    # ---------------------------------------------------
    # OVERALL AVERAGE MACHINE AVAILABILITY
    # ---------------------------------------------------
    all_vals = [v for arr in wtg_ma.values() for v in arr]
    overall_avg_ma = round(sum(all_vals)/len(all_vals), 2) if all_vals else 0

    # ---------------------------------------------------
    # SEND TO TEMPLATE
    # ---------------------------------------------------
    return render(request, "wind_Avg_Machine_Availability.html", {
        "chart_data": json.dumps(chart_data),
        "table_data": table_data,
        "table_page": table_page,
        "paginator": paginator,

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

        "date_from": date_from,
        "date_to": date_to,

        "overall_avg_ma": overall_avg_ma,

        "no_data": len(chart_data) == 0,
        "no_data_msg": "No Machine Availability data found for selected filters."
    })



from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.db import connection
from django.contrib.auth.models import User
from django.utils.timezone import now

import os
import re
import traceback
import pandas as pd
import numpy as np

import os, re, traceback
import pandas as pd
import numpy as np
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.db import connection
from django.contrib.auth.models import User
from django.utils.timezone import now



from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.db import connection
from django.contrib.auth.models import User
from django.utils.timezone import now

import os
import re
import traceback
import pandas as pd
import numpy as np

import os, re, traceback
import pandas as pd
import numpy as np
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.db import connection
from django.contrib.auth.models import User
from django.utils.timezone import now

import os, re, traceback
import pandas as pd
import numpy as np
from datetime import datetime, date
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.db import connection
from django.utils.timezone import now
from accounts.models import Provider, EnergyType
from accounts.models import ProviderColumnMapping
from accounts.breakdown_mapping import canonicalize_breakdown_dataframe
from accounts.breakdown_ingestion import (
    ensure_breakdown_deduplication,
    insert_canonical_breakdown_rows,
)
from core.models import UploadMetadata


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

                    if (
                        (("start" in col_l or "end" in col_l) and "time" in col_l)
                        or col_l.endswith("_datetime")
                    ):
                        df[col] = pd.to_datetime(df[col], errors="coerce")
                        continue

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
                    target_table = (
                        table_name
                        if table_name.lower().endswith("_breakdowndata")
                        else f"{table_name}_breakdowndata"
                    )
                elif "month" in sname or "monthly" in sname:
                    target_table = f"{table_name}_monthly"
                else:
                    target_table = table_name

                if target_table not in db_tables:
                    continue

                has_canonical_mapping = False
                mapping_owner = None
                if "breakdowndata" in target_table.lower():
                    configured_mappings = list(
                        ProviderColumnMapping.objects.filter(
                            table_name=target_table
                        ).order_by("id")
                    )
                    if configured_mappings:
                        has_canonical_mapping = True
                        mapping_owner = configured_mappings[0]
                        try:
                            df, _ = canonicalize_breakdown_dataframe(
                                df, configured_mappings
                            )
                        except ValueError as error:
                            messages.error(
                                request,
                                f"Breakdown sheet '{sheet_name}': {error}",
                            )
                            continue
                    else:
                        legacy_aliases = {
                            "loaction": "location",
                            "loc": "location",
                            "location ": "location",
                        }
                        df.rename(
                            columns=lambda column: legacy_aliases.get(
                                column.lower(), column.lower()
                            ),
                            inplace=True,
                        )
                else:
                    alias_map = {
                        "loaction": "location",
                        "loc": "location",
                        "location ": "location",
                    }
                    df.rename(columns=lambda c: alias_map.get(c.lower(), c.lower()), inplace=True)

                # =====================================================
                # GET TABLE COLUMNS
                # =====================================================
                if has_canonical_mapping:
                    ensure_breakdown_deduplication(target_table)
                with connection.cursor() as cursor:
                    cursor.execute(f"SHOW COLUMNS FROM `{target_table}`")
                    table_columns = [c[0].lower() for c in cursor.fetchall()]

                # =====================================================
                # FILTER VALID COLUMNS
                # =====================================================
                valid_cols = [c for c in df.columns if c in table_columns]
                df = df[valid_cols]
                if has_canonical_mapping:
                    required_fields = ["gen_date", "loc_no", "breakdown_remarks"]
                    df = df.dropna(subset=required_fields)
                    if df.empty:
                        messages.error(
                            request,
                            f"Breakdown sheet '{sheet_name}' has no rows with a date, "
                            "machine ID, and remarks.",
                        )
                        continue

                # =====================================================
                # ADD METADATA
                # =====================================================
                if "uploaded_by" in table_columns:
                    df["uploaded_by"] = username
                if "provider" in table_columns:
                    df["provider"] = provider_name
                if "energy_type" in table_columns:
                    df["energy_type"] = energy_type_name
                if mapping_owner and "user_id" in table_columns:
                    df["user_id"] = mapping_owner.user_id
                if mapping_owner and "provider_id" in table_columns:
                    df["provider_id"] = mapping_owner.provider_id

                if has_canonical_mapping:
                    inserted, duplicates = insert_canonical_breakdown_rows(
                        target_table, df
                    )
                    if inserted:
                        UploadMetadata.objects.update_or_create(
                            table_name=target_table,
                            defaults={"last_modified": now()},
                        )
                    uploaded_sheets.append(
                        f"{sheet_name} → {inserted} new rows queued for classification; "
                        f"{duplicates} duplicates discarded"
                    )
                    continue

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


@login_required
def breakdown_classification_results(request):
    from django.http import Http404

    if not request.user.is_staff:
        raise Http404("Breakdown classification results not found.")

    table_name = request.GET.get("table", "").strip()
    if not re.fullmatch(r"[a-zA-Z0-9_]+_breakdowndata", table_name, re.IGNORECASE):
        raise Http404("Breakdown table not found.")

    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES")
        existing_tables = {row[0].lower() for row in cursor.fetchall()}
        if table_name.lower() not in existing_tables:
            raise Http404("Breakdown table not found.")

        cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
        columns = {row[0].lower() for row in cursor.fetchall()}
        required_columns = {
            "rds_code",
            "system_name",
            "standard_component",
            "classification_status",
        }
        if required_columns - columns:
            return render(request, "breakdown_classification_results.html", {
                "table_name": table_name,
                "setup_missing": True,
                "base_template": "base.html",
            })

        cursor.execute(
            "SELECT COALESCE(`rds_code`, 'UNCATEGORIZED'), "
            "COALESCE(`system_name`, 'Unclassified'), "
            "COALESCE(`standard_component`, 'Unmapped'), COUNT(*) "
            f"FROM `{table_name}` "
            "WHERE `classification_status` IN ('CLASSIFIED', 'LOW_CONFIDENCE') "
            "GROUP BY `rds_code`, `system_name`, `standard_component` "
            "ORDER BY COUNT(*) DESC, `rds_code`, `system_name`, `standard_component`"
        )
        mapping_summary = [
            {
                "rds_code": row[0],
                "system_name": row[1],
                "standard_component": row[2],
                "record_count": row[3],
            }
            for row in cursor.fetchall()
        ]
    total_records = sum(item["record_count"] for item in mapping_summary)
    max_count = max((item["record_count"] for item in mapping_summary), default=0)
    for item in mapping_summary:
        item["bar_width"] = round(item["record_count"] * 100 / max_count) if max_count else 0

    return render(request, "breakdown_classification_results.html", {
        "table_name": table_name,
        "mapping_summary": mapping_summary,
        "total_records": total_records,
        "base_template": "base.html",
    })

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import connection
from datetime import datetime, timedelta, time as datetime_time

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
    username = request.user.username.lower()

    # ---------------------------------------------------
    # CLEAR FILTERS
    # ---------------------------------------------------
    if request.GET.get("clear_filters"):
        request.session.pop("wind_filters", None)

    # ---------------------------------------------------
    # RESTORE SESSION FILTERS
    # ---------------------------------------------------
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

    # ---------------------------------------------------
    # AUTO DATE RANGE = LAST 1 YEAR
    # ---------------------------------------------------
    from datetime import date, timedelta
    if not date_from and not date_to:
        today = date.today()
        auto_from = today - timedelta(days=365)
        date_from = auto_from.strftime("%Y-%m-%d")
        date_to   = today.strftime("%Y-%m-%d")

    # ---------------------------------------------------
    # SAVE FILTERS BACK INTO SESSION
    # ---------------------------------------------------
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

    # ---------------------------------------------------
    # FIND ALL WIND TABLES
    # ---------------------------------------------------
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES")
        db_tables = [row[0] for row in cursor.fetchall()]

    table_names = [
        t for t in db_tables
        if t.startswith(username + "_") and t.endswith("_wind")
    ]

    # ---------------------------------------------------
    # ACCUMULATORS
    # ---------------------------------------------------
    plf_data = defaultdict(list)
    provider_plf_data = defaultdict(list)

    distincts = {
        "providers": set(),
        "customers": set(),
        "states": set(),
        "sites": set(),
        "wtgs": set(),
    }

    # ---------------------------------------------------
    # PROCESS EACH TABLE
    # ---------------------------------------------------
    for table in table_names:

        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{table}`")
            cols = [c[0] for c in cursor.fetchall()]
        col_map = {normalize(c): c for c in cols}

        # column mapping
        wtg_col      = _pick(col_map, "wec", "loc_no", "wtg", "wtg_no", "turbine", "turbineno", "locno")
        plf_col      = _pick(col_map, "cf", "plf", "plf_day", "%plf_day", "capacityfactor")
        date_col     = _pick(col_map, "date", "gen_date", "reading_date", "day_date")
        customer_col = _pick(col_map, "customername", "customer", "consumer", "client")
        state_col    = _pick(col_map, "state", "statename", "st")
        site_col     = _pick(col_map, "site", "sitename", "location", "plant", "park")
        provider_col = _pick(col_map, "provider", "oem", "oemprovider", "oem_name")

        if not (wtg_col and plf_col):
            continue

        # ---------------------------------------------------
        # WHERE CLAUSE
        # ---------------------------------------------------
        conditions, params = [], []

        if date_col:
            if date_from and date_to:
                conditions.append(f"`{date_col}` BETWEEN %s AND %s")
                params.extend([date_from, date_to])
            elif date_from:
                conditions.append(f"`{date_col}` >= %s")
                params.append(date_from)
            elif date_to:
                conditions.append(f"`{date_col}` <= %s")
                params.append(date_to)

        def add_in(col, values):
            if col and values:
                q = ",".join(["%s"] * len(values))
                conditions.append(f"`{col}` IN ({q})")
                params.extend(values)

        add_in(provider_col, providers)
        add_in(customer_col, customers)
        add_in(state_col, states)
        add_in(site_col, sites)
        add_in(wtg_col, wtgs)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # ---------------------------------------------------
        # WTG-WISE PLF
        # ---------------------------------------------------
        query_wtg = f"""
            SELECT `{wtg_col}`, AVG(`{plf_col}`)
            FROM `{table}`
            {where_clause}
            GROUP BY `{wtg_col}`
        """
        with connection.cursor() as cursor:
            cursor.execute(query_wtg, params)
            rows = cursor.fetchall()

        for wtg, avg_plf in rows:
            if wtg and avg_plf is not None:
                plf_data[str(wtg)].append(float(avg_plf))

        # ---------------------------------------------------
        # PROVIDER-WISE PLF
        # ---------------------------------------------------
        if provider_col:
            query_provider = f"""
                SELECT `{provider_col}`, AVG(`{plf_col}`)
                FROM `{table}`
                {where_clause}
                GROUP BY `{provider_col}`
            """
            with connection.cursor() as cursor:
                cursor.execute(query_provider, params)
                prov_rows = cursor.fetchall()

            for prov, avg_plf in prov_rows:
                if prov and avg_plf is not None:
                    provider_plf_data[str(prov)].append(float(avg_plf))

        # ---------------------------------------------------
        # DISTINCT VALUES
        # ---------------------------------------------------
        def distinct_list(col):
            if not col:
                return []
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT DISTINCT `{col}` FROM `{table}` ORDER BY `{col}`")
                return [str(r[0]).strip() for r in cursor.fetchall() if r[0]]

        distincts["providers"].update(distinct_list(provider_col))
        distincts["customers"].update(distinct_list(customer_col))
        distincts["states"].update(distinct_list(state_col))
        distincts["sites"].update(distinct_list(site_col))
        distincts["wtgs"].update(distinct_list(wtg_col))

    # ---------------------------------------------------
    # FINAL DATA PREP
    # ---------------------------------------------------
    plf_final = {wtg: sum(v) / len(v) for wtg, v in plf_data.items()}
    plf_chart_data = [{"x": k, "y": round(v, 2)} for k, v in plf_final.items()]
    plf_chart_data.sort(key=lambda x: x["y"], reverse=True)

    provider_final = {prov: sum(v) / len(v) for prov, v in provider_plf_data.items()}
    provider_chart_data = [{"x": k, "y": round(v, 2)} for k, v in provider_final.items()]
    provider_chart_data.sort(key=lambda x: x["y"], reverse=True)

    # ---------------------------------------------------
    # CONTEXT
    # ---------------------------------------------------
    return render(request, "wind_wtg_plf.html", {
        "plf_wtg_data": json.dumps(plf_chart_data),
        "plf_provider_data": json.dumps(provider_chart_data),

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

        "date_from": date_from,
        "date_to": date_to,
    })


from collections import defaultdict
from datetime import datetime, date, timedelta
from django.db import connection
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render
import json
import re


def to_float(value):
    """
    Safely convert database values to float.
    Handles '', None, '-', 'NA', etc.
    """
    try:
        if value in (None, "", "-", "NA", "null", "NULL"):
            return 0
        return float(value)
    except:
        return 0


def _pick(col_map, *candidates):
    """Return the actual column name if it matches any of the candidates"""
    for c in candidates:
        if not c:
            continue
        lc = c.lower()
        if lc in col_map:
            return col_map[lc]
    return None

def parse_date_like(v):
    """Parse various date formats to datetime.date (returns ISO string for SQL)."""
    if v is None:
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, datetime):
        return v.date().isoformat()
    s = str(v).strip()
    if not s:
        return None
    fmts = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%d-%b-%Y", "%d %b %Y")
    for fmt in fmts:
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except Exception:
            continue
    # As fallback, try ISO-like or dateutil style by slicing
    try:
        return datetime.fromisoformat(s).date().isoformat()
    except Exception:
        return None

def parse_numeric(v):
    """Safe numeric parsing. Handles numbers, strings like '24' or '24.0', and '1 day 00:00:00' (returns hours)."""
    if v is None:
        return None
    # If already numeric
    try:
        return float(v)
    except Exception:
        pass
    s = str(v).strip()
    if s == "":
        return None
    # handle "1 day 00:00:00" or "0 days 12:00:00"
    m = re.match(r'(?:(\d+)\s*day[s]?\s*)?(\d{1,2}):(\d{2})(?::(\d{2}))?', s)
    if m:
        days = int(m.group(1)) if m.group(1) else 0
        hrs = int(m.group(2))
        mins = int(m.group(3))
        secs = int(m.group(4)) if m.group(4) else 0
        total_hours = days * 24 + hrs + (mins / 60.0) + (secs / 3600.0)
        return float(total_hours)
    # handle values like "24 Hrs", "24.0"
    m2 = re.search(r'[-+]?\d*\.?\d+', s)
    if m2:
        try:
            return float(m2.group(0))
        except:
            return None
    return None



@login_required
def wind_Grid_Availability(request):
    user = request.user.username.lower()

    # ----------------------------------------------------
    # HANDLE CLEAR FILTER BUTTON
    # ----------------------------------------------------
    if request.GET.get("clear_filters"):
        request.session.pop("wind_filters", None)

    # ----------------------------------------------------
    # RESTORE SAVED FILTERS FROM SESSION
    # ----------------------------------------------------
    saved = request.session.get("wind_filters", {})

    def get_or_saved_list(key):
        vals = request.GET.getlist(key)
        return vals if vals else saved.get(key, [])

    # --- Date handling (1-year auto)
    date_from = request.GET.get("date_from") or saved.get("date_from")
    date_to   = request.GET.get("date_to") or saved.get("date_to")

    from datetime import date, timedelta
    if not date_from and not date_to:
        today = date.today()
        auto_from = today - timedelta(days=365)      # ← 1 YEAR AUTO
        date_from = auto_from.strftime("%Y-%m-%d")
        date_to   = today.strftime("%Y-%m-%d")

    # --- Other filters persistent
    providers = get_or_saved_list("provider")
    customers = get_or_saved_list("customer")
    states    = get_or_saved_list("state")
    sites     = get_or_saved_list("site")
    wtgs      = get_or_saved_list("wtg")

    # ----------------------------------------------------
    # SAVE FILTERS BACK INTO SESSION
    # ----------------------------------------------------
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

    # ----------------------------------------------------
    # FETCH USER WIND TABLES
    # ----------------------------------------------------
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        tables = [row[0] for row in cursor.fetchall()]

    table_names = [
        t for t in tables
        if t.startswith(user + "_") and t.endswith("_wind")
    ]

    if not table_names:
        return render(request, "wind_Grid_Availability.html", {
            "ext_data": [], "int_data": [],
            "ext_json": "[]", "int_json": "[]",
            "overall_ext": 0, "overall_int": 0,
            "providers": [], "customers": [], "states": [], "sites": [], "wtgs": [],
            "selected_providers": providers, "selected_customers": customers,
            "selected_states": states, "selected_sites": sites, "selected_wtgs": wtgs,
            "date_from": date_from, "date_to": date_to,
            "no_data": True,
            "no_data_msg": "No wind tables found for your account.",
            "paginator": None,
            "table_page": None
        })

    # ----------------------------------------------------
    # DATA STRUCTURES
    # ----------------------------------------------------
    ext_avl = defaultdict(list)
    int_avl = defaultdict(list)

    distincts = {
        "providers": set(),
        "customers": set(),
        "states": set(),
        "sites": set(),
        "wtgs": set(),
    }

    # ----------------------------------------------------
    # PROCESS EACH TABLE
    # ----------------------------------------------------
    for table in table_names:

        # Load columns
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{table}`;")
            cols = [row[0] for row in cursor.fetchall()]

        col_map = {c.lower(): c for c in cols}

        # Column picking helper
        def _pick(cmap, *candidates):
            for cand in candidates:
                if cand.lower() in cmap:
                    return cmap[cand.lower()]
            return None

        # Identify flexible column names
        date_col = _pick(col_map, "date", "gen_date", "reading_date", "day_date")
        wtg_col  = _pick(col_map, "wec", "wtg", "loc_no", "locno", "wtgno", "turbine")

        ext_col  = _pick(col_map, "ga", "externalgridavailability", "ega")
        int_col  = _pick(col_map, "gia", "internalgridavailability", "iga")

        gf_col   = _pick(col_map, "gf", "gridfailure", "grid_failure_hrs")
        fm_col   = _pick(col_map, "fm", "forcemajeure")
        s_col    = _pick(col_map, "s", "shutdown")
        u_col    = _pick(col_map, "u", "unknown")
        opr_col  = _pick(col_map, "ohrs", "operatinghours", "opr_hrs")
        gen_hrs  = _pick(col_map, "genhrs", "generationhours")

        provider_col = _pick(col_map, "provider", "oem")
        customer_col = _pick(col_map, "customer", "customername")
        state_col    = _pick(col_map, "state", "statename")
        site_col     = _pick(col_map, "site", "plant", "location")

        if not date_col or not wtg_col:
            continue

        # ----------------------------------------------------
        # BUILD FILTER CONDITIONS
        # ----------------------------------------------------
        conditions, params = [], []

        # DATE
        if date_from and date_to:
            conditions.append(f"`{date_col}` BETWEEN %s AND %s")
            params += [date_from, date_to]

        # MULTI FILTERS
        def add_in(col, values):
            if col and values:
                placeholders = ",".join(["%s"] * len(values))
                conditions.append(f"`{col}` IN ({placeholders})")
                params.extend(values)

        add_in(provider_col, providers)
        add_in(customer_col, customers)
        add_in(state_col, states)
        add_in(site_col, sites)
        add_in(wtg_col, wtgs)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # ----------------------------------------------------
        # SELECT NEEDED COLUMNS
        # ----------------------------------------------------
        select_cols = [wtg_col]
        for c in [ext_col, int_col, gf_col, fm_col, s_col, u_col, opr_col, gen_hrs]:
            if c:
                select_cols.append(c)

        query = f"""
            SELECT {','.join(f'`{c}`' for c in select_cols)}
            FROM `{table}`
            {where_clause}
        """

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        idx = {col: i for i, col in enumerate(select_cols)}

        # ----------------------------------------------------
        # PROCESS EACH ROW
        # ----------------------------------------------------
        for row in rows:
            wtg = row[idx[wtg_col]]
            if not wtg:
                continue

            wtg = str(wtg)

            # Try direct GA/GIA first
            ext_val = float(row[idx.get(ext_col)]) if ext_col and row[idx.get(ext_col)] not in (None, "") else None
            int_val = float(row[idx.get(int_col)]) if int_col and row[idx.get(int_col)] not in (None, "") else None

            # If missing → compute from GF/FM/S/U
            if ext_val is None or int_val is None:
                gf = to_float(row[idx.get(gf_col)]) if gf_col else 0
                fm = to_float(row[idx.get(fm_col)]) if fm_col else 0
                s_  = to_float(row[idx.get(s_col)]) if s_col else 0
                u_  = to_float(row[idx.get(u_col)]) if u_col else 0
                opr = to_float(row[idx.get(opr_col)]) if opr_col else None

                if opr is None and gen_hrs:
                    opr = to_float(row[idx.get(gen_hrs)])

                if ext_val is None and gf and opr:
                    ext_val = round(100 - (gf / opr) * 100, 2)

                if int_val is None and opr:
                    int_val = round(100 - ((fm + s_ + u_) / opr) * 100, 2)

            if ext_val is None:
                ext_val = 0
            if int_val is None:
                int_val = 0

            ext_avl[wtg].append(ext_val)
            int_avl[wtg].append(int_val)

        # DISTINCT VALUES
        def distinct_list(col):
            if not col:
                return []
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT DISTINCT `{col}` FROM `{table}` ORDER BY `{col}`")
                return [str(r[0]) for r in cursor.fetchall() if r[0]]

        distincts["providers"].update(distinct_list(provider_col))
        distincts["customers"].update(distinct_list(customer_col))
        distincts["states"].update(distinct_list(state_col))
        distincts["sites"].update(distinct_list(site_col))
        distincts["wtgs"].update(distinct_list(wtg_col))

    # ----------------------------------------------------
    # PREPARE FINAL DATA
    # ----------------------------------------------------
    ext_data = [
        {"wtg": k, "value": round(sum(v)/len(v), 2)}
        for k, v in ext_avl.items()
    ]

    int_data = [
        {"wtg": k, "value": round(sum(v)/len(v), 2)}
        for k, v in int_avl.items()
    ]

    overall_ext = round(sum([x["value"] for x in ext_data]) / len(ext_data), 2) if ext_data else 0
    overall_int = round(sum([x["value"] for x in int_data]) / len(int_data), 2) if int_data else 0

    # Table pagination
    combined_table = []
    all_wtgs = sorted(set([d["wtg"] for d in ext_data] + [d["wtg"] for d in int_data]))
    for w in all_wtgs:
        e = next((x["value"] for x in ext_data if x["wtg"] == w), 0)
        i = next((x["value"] for x in int_data if x["wtg"] == w), 0)
        combined_table.append({"wtg": w, "ext": e, "int": i})

    page = request.GET.get("page", 1)
    paginator = Paginator(combined_table, 10)
    try:
        table_page = paginator.page(page)
    except Exception:
        table_page = paginator.page(1)

    # ----------------------------------------------------
    # RENDER
    # ----------------------------------------------------
    return render(request, "wind_Grid_Availability.html", {
        "ext_data": ext_data,
        "int_data": int_data,
        "ext_json": json.dumps(ext_data),
        "int_json": json.dumps(int_data),
        "overall_ext": overall_ext,
        "overall_int": overall_int,

        # DISTINCT FILTERS
        "providers": sorted(distincts["providers"]),
        "customers": sorted(distincts["customers"]),
        "states": sorted(distincts["states"]),
        "sites": sorted(distincts["sites"]),
        "wtgs": sorted(distincts["wtgs"]),

        # SELECTED FILTERS
        "selected_providers": providers,
        "selected_customers": customers,
        "selected_states": states,
        "selected_sites": sites,
        "selected_wtgs": wtgs,

        # DATE FILTERS
        "date_from": date_from,
        "date_to": date_to,

        # TABLE
        "paginator": paginator,
        "table_page": table_page,

        "no_data": (not ext_data and not int_data),
        "no_data_msg": (
            "No grid availability records found for selected filters."
            if (not ext_data and not int_data) else ""
        )
    })





from collections import defaultdict
from datetime import datetime
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
import json, re

# ---------- Improved Column Picker ----------
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


def _user_breakdown_tables(tables, username):
    username_prefix = f"{username.strip().lower()}_"
    return [
        table for table in tables
        if table.lower().startswith(username_prefix)
        and (
            table.lower().endswith("_wind")
            or table.lower().endswith("_breakdowndata")
        )
    ]


def _breakdown_column(columns, *candidates):
    normalized_columns = {_normalize(column): column for column in columns}
    for candidate in candidates:
        actual = normalized_columns.get(_normalize(candidate))
        if actual:
            return actual
    return None


def _duration_hours_from_bounds(start, end):
    if start is None or end is None:
        return None
    try:
        if isinstance(start, datetime_time) and isinstance(end, datetime_time):
            start_at = datetime.combine(datetime.today().date(), start)
            end_at = datetime.combine(datetime.today().date(), end)
            if end_at < start_at:
                end_at += timedelta(days=1)
        else:
            start_at = start if isinstance(start, datetime) else datetime.fromisoformat(str(start))
            end_at = end if isinstance(end, datetime) else datetime.fromisoformat(str(end))
        elapsed = (end_at - start_at).total_seconds() / 3600
        return elapsed if elapsed >= 0 else None
    except (TypeError, ValueError):
        return None


@login_required
def wind_breakdown_hours(request):
    user = request.user.username.lower()

    # ----------------------------------------------------
    # CLEAR FILTERS
    # ----------------------------------------------------
    if request.GET.get("clear_filters"):
        request.session.pop("wind_filters", None)

    # ----------------------------------------------------
    # RESTORE SAVED FILTERS
    # ----------------------------------------------------
    def get_or_saved_list(key):
        return request.GET.getlist(key)

    # --- DATE (all history unless the user selects a range)
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")

    # --- OTHER FILTERS (persistent)
    providers = get_or_saved_list("provider")
    uploaded_by = get_or_saved_list("uploaded_by")
    customers = get_or_saved_list("customer")
    states    = get_or_saved_list("state")
    sites     = get_or_saved_list("site")
    wtgs      = get_or_saved_list("wtg")

    # ----------------------------------------------------
    # SAVE SESSION FILTERS BACK
    # ----------------------------------------------------
    request.session["wind_filters"] = {
        "date_from": date_from,
        "date_to": date_to,
        "provider": providers,
        "uploaded_by": uploaded_by,
        "customer": customers,
        "state": states,
        "site": sites,
        "wtg": wtgs,
    }
    request.session.modified = True

    # ----------------------------------------------------
    # FETCH USER TABLES
    # ----------------------------------------------------
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        tables = [row[0] for row in cursor.fetchall()]
    table_names = _user_breakdown_tables(tables, user)

    if not table_names:
        return render(request, "wind_breakdown_hours.html", {
            "chart_data": json.dumps([]),
            "table_data": [],
            "total_breakdown": 0,
            "providers": [], "customers": [], "states": [], "sites": [], "wtgs": [],
            "uploaded_by_options": [],
            "selected_providers": providers,
            "selected_uploaded_by": uploaded_by,
            "selected_customers": customers,
            "selected_states": states,
            "selected_sites": sites,
            "selected_wtgs": wtgs,
            "date_from": date_from,
            "date_to": date_to,
            "no_data": True,
            "no_data_msg": "No wind or breakdown tables found for your account.",
        })

    # ----------------------------------------------------
    # PROCESS DATA
    # ----------------------------------------------------
    breakdown_hours = defaultdict(float)
    total_breakdown = 0.0

    distincts = {
        "providers": set(),
        "uploaded_by": set(),
        "customers": set(),
        "states": set(),
        "sites": set(),
        "wtgs": set(),
    }

    for table_name in table_names:

        # Load schema
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{table_name}`;")
            cols = [r[0] for r in cursor.fetchall()]
        wtg_col = _breakdown_column(
            cols, "loc_no", "wec", "locno", "wtg", "wtg_no", "turbine"
        )
        date_col = _breakdown_column(
            cols, "gen_date", "date", "reading_date", "day_date"
        )
        duration_col = _breakdown_column(
            cols, "duration_hrs", "duration_hours", "breakdown_hours", "duration"
        )
        start_col = _breakdown_column(
            cols, "start_time", "breakdown_start", "start_datetime"
        )
        end_col = _breakdown_column(
            cols, "end_time", "breakdown_end", "end_datetime"
        )
        genhrs_col = _breakdown_column(
            cols, "genhrs", "generationhours", "gen_hours"
        )
        ohrs_col = _breakdown_column(
            cols, "ohrs", "operatinghours", "opr_hrs"
        )
        loss_col = _breakdown_column(
            cols, "lhrs", "losshrs", "loss_hours", "l_hrs"
        )

        provider_col = _breakdown_column(cols, "provider", "oem")
        uploaded_by_col = _breakdown_column(
            cols, "uploaded_by", "uploaded_user", "uploader", "username"
        )
        customer_col = _breakdown_column(
            cols, "customername", "customer", "client"
        )
        state_col = _breakdown_column(cols, "state", "statename")
        site_col = _breakdown_column(cols, "site", "sitename", "location")

        if not wtg_col:
            continue

        # ----------------------------------------------------
        # BUILD WHERE CLAUSE
        # ----------------------------------------------------
        conditions, params = [], []

        if date_col and date_from:
            conditions.append(f"`{date_col}` >= %s")
            params.append(date_from)
        if date_col and date_to:
            conditions.append(f"`{date_col}` < DATE_ADD(%s, INTERVAL 1 DAY)")
            params.append(date_to)

        def add_in(col, values):
            values = [v for v in values if v]
            if col and values:
                placeholders = ",".join(["%s"] * len(values))
                conditions.append(f"`{col}` IN ({placeholders})")
                params.extend(values)

        add_in(provider_col, providers)
        add_in(uploaded_by_col, uploaded_by)
        add_in(customer_col, customers)
        add_in(state_col, states)
        add_in(site_col, sites)
        add_in(wtg_col, wtgs)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # ----------------------------------------------------
        # BREAKDOWN EXPRESSION
        # ----------------------------------------------------
        if duration_col and start_col and end_col:
            expr = (
                f"CASE WHEN COALESCE(`{duration_col}`, 0) = 0 "
                f"AND `{start_col}` IS NOT NULL AND `{end_col}` IS NOT NULL "
                f"THEN GREATEST(TIMESTAMPDIFF(SECOND, `{start_col}`, `{end_col}`) / 3600, 0) "
                f"ELSE COALESCE(`{duration_col}`, 0) END"
            )
        elif duration_col:
            expr = f"COALESCE(`{duration_col}`, 0)"
        elif start_col and end_col:
            expr = (
                f"GREATEST(TIMESTAMPDIFF(SECOND, `{start_col}`, `{end_col}`) / 3600, 0)"
            )
        elif loss_col:
            expr = f"`{loss_col}`"
        elif genhrs_col and ohrs_col:
            expr = f"(`{ohrs_col}` - `{genhrs_col}`)"
        else:
            continue

        # ----------------------------------------------------
        # RUN QUERY
        # ----------------------------------------------------
        query = f"""
            SELECT `{wtg_col}`, SUM({expr})
            FROM `{table_name}`
            {where_clause}
            GROUP BY `{wtg_col}`
        """

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        for wtg, hrs in rows:
            if not wtg:
                continue
            hrs_val = float(hrs or 0)
            breakdown_hours[str(wtg)] += hrs_val
            total_breakdown += hrs_val

        # DISTINCT VALUES
        def distinct_list(col):
            if not col:
                return []
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT DISTINCT `{col}` FROM `{table_name}` ORDER BY `{col}`")
                return [str(r[0]) for r in cursor.fetchall() if r[0]]

        distincts["providers"].update(distinct_list(provider_col))
        distincts["uploaded_by"].update(distinct_list(uploaded_by_col))
        distincts["customers"].update(distinct_list(customer_col))
        distincts["states"].update(distinct_list(state_col))
        distincts["sites"].update(distinct_list(site_col))
        distincts["wtgs"].update(distinct_list(wtg_col))

    # ----------------------------------------------------
    # FINAL OUTPUT
    # ----------------------------------------------------
    chart_data = [
        {"wtg": k, "breakdown": round(v, 2)}
        for k, v in breakdown_hours.items()
    ]
    chart_data.sort(key=lambda x: x["breakdown"], reverse=True)

    table_data = [
        {"wtg_no": k, "breakdown": round(v, 2)}
        for k, v in breakdown_hours.items()
    ]

    return render(request, "wind_breakdown_hours.html", {
        "chart_data": json.dumps(chart_data),
        "table_data": table_data,
        "total_breakdown": round(total_breakdown, 2),

        "providers": sorted(distincts["providers"]),
        "uploaded_by_options": sorted(distincts["uploaded_by"]),
        "customers": sorted(distincts["customers"]),
        "states": sorted(distincts["states"]),
        "sites": sorted(distincts["sites"]),
        "wtgs": sorted(distincts["wtgs"]),

        "selected_providers": providers,
        "selected_uploaded_by": uploaded_by,
        "selected_customers": customers,
        "selected_states": states,
        "selected_sites": sites,
        "selected_wtgs": wtgs,

        "date_from": date_from,
        "date_to": date_to,

        "no_data": not bool(chart_data),
        "no_data_msg": "No breakdown data found for the selected filters."
                      if not chart_data else "",
    })



























# views.py
import json
import re
from collections import defaultdict
from datetime import datetime, date
from django.db import connection
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

# -------------------------
# Helpers
# -------------------------
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
    user = request.user.username.lower()

    # -----------------------------
    # HANDLE CLEAR FILTER BUTTON
    # -----------------------------
    if request.GET.get("clear_filters"):
        request.session.pop("wind_filters", None)

    # -----------------------------
    # RESTORE SAVED FILTERS
    # -----------------------------
    def get_or_saved_list(key):
        return request.GET.getlist(key)

    raw_date_from = request.GET.get("date_from", "")
    raw_date_to = request.GET.get("date_to", "")

    providers = get_or_saved_list("provider")
    uploaded_by = get_or_saved_list("uploaded_by")
    customers = get_or_saved_list("customer")
    states    = get_or_saved_list("state")
    sites     = get_or_saved_list("site")
    wtgs      = get_or_saved_list("wtg")

    # Save back to session
    request.session["wind_filters"] = {
        "date_from": raw_date_from,
        "date_to": raw_date_to,
        "provider": providers,
        "uploaded_by": uploaded_by,
        "customer": customers,
        "state": states,
        "site": sites,
        "wtg": wtgs,
    }
    request.session.modified = True

    # Convert dates
    date_from = parse_date_like(raw_date_from)
    date_to = parse_date_like(raw_date_to)

    # -----------------------------
    # FIND ALL USER WIND TABLES
    # -----------------------------
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        tables = [row[0] for row in cursor.fetchall()]

    table_names = _user_breakdown_tables(tables, user)

    if not table_names:
        return render(request, "wind_breakdown_log.html", {
            "data": [],
            "breakdown_data": "[]",
            "providers": [], "customers": [], "states": [], "sites": [], "wtgs": [],
            "uploaded_by_options": [],
            "selected_providers": providers, "selected_customers": customers,
            "selected_uploaded_by": uploaded_by,
            "selected_states": states, "selected_sites": sites, "selected_wtgs": wtgs,
            "date_from": raw_date_from, "date_to": raw_date_to,
            "no_data": True, "no_data_msg": "No wind or breakdown tables found.",
            "total_hours": 0, "paginator": None, "page_obj": None
        })

    # -----------------------------
    # CANDIDATE COLUMN NAMES
    # -----------------------------
    date_candidates = [
        "gen_date", "date", "gen date", "generation date", "gen. date"
    ]
    site_candidates = ["site", "sitename", "plant", "location", "park"]
    wec_candidates = [
        "loc_no", "wec", "wtg", "loc no", "loc.no", "wecno", "wtgno", "locno"
    ]
    lhrs_candidates = ["l.hrs", "lhrs", "loss hours", "loss_hrs", "breakdown hrs"]
    duration_candidates = [
        "duration_hrs", "duration_hours", "breakdown_hours", "duration"
    ]
    start_candidates = ["start_time", "breakdown_start", "start_datetime"]
    end_candidates = ["end_time", "breakdown_end", "end_datetime"]
    genhrs_candidates = ["gen hrs", "generation hours", "gen_hours", "gen_hrs"]
    oprhrs_candidates = ["opr hrs", "ohrs", "operatinghours", "o_hours", "ophrs"]
    remarks_candidates = [
        "breakdown_remarks", "remarks", "remark", "comment", "reason", "note"
    ]

    provider_candidates = ["provider", "oem", "company"]
    uploaded_by_candidates = [
        "uploaded_by", "uploaded_user", "uploader", "username"
    ]
    customer_candidates = ["customer", "customer name", "client"]
    state_candidates = ["state", "statename"]

    breakdown_records = []
    providers_set = set()
    uploaded_by_set = set()
    customers_set = set()
    states_set = set()
    sites_set = set()
    wtgs_set = set()

    total_hours = 0.0

    # -----------------------------
    # PROCESS TABLES
    # -----------------------------
    for table in table_names:
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{table}`;")
            cols = [r[0] for r in cursor.fetchall()]
        date_col = _breakdown_column(cols, *date_candidates)
        if not date_col:
            continue

        wec_col = _breakdown_column(cols, *wec_candidates)
        site_col = _breakdown_column(cols, *site_candidates)
        duration_col = _breakdown_column(cols, *duration_candidates)
        start_col = _breakdown_column(cols, *start_candidates)
        end_col = _breakdown_column(cols, *end_candidates)
        lhrs_col = _breakdown_column(cols, *lhrs_candidates)
        gen_col = _breakdown_column(cols, *genhrs_candidates)
        opr_col = _breakdown_column(cols, *oprhrs_candidates)
        remarks_col = _breakdown_column(cols, *remarks_candidates)

        provider_col = _breakdown_column(cols, *provider_candidates)
        uploaded_by_col = _breakdown_column(cols, *uploaded_by_candidates)
        customer_col = _breakdown_column(
            cols, *customer_candidates, "customername", "client"
        )
        state_col = _breakdown_column(cols, *state_candidates, "statename")

        # WHERE CLAUSE
        conditions, params = [], []

        if date_from:
            conditions.append(f"`{date_col}` >= %s"); params.append(date_from.isoformat())
        if date_to:
            conditions.append(f"`{date_col}` < DATE_ADD(%s, INTERVAL 1 DAY)")
            params.append(date_to.isoformat())

        def add_in(col, vals):
            if col and vals:
                placeholders = ",".join(["%s"] * len(vals))
                conditions.append(f"`{col}` IN ({placeholders})")
                params.extend(vals)

        add_in(provider_col, providers)
        add_in(uploaded_by_col, uploaded_by)
        add_in(customer_col, customers)
        add_in(state_col, states)
        add_in(site_col, sites)
        add_in(wec_col, wtgs)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # SELECT
        select_cols = [c for c in [
            date_col, site_col, wec_col, duration_col, start_col, end_col,
            lhrs_col, gen_col, opr_col,
            remarks_col, provider_col, uploaded_by_col, customer_col, state_col
        ] if c]

        q = f"SELECT {', '.join(f'`{c}`' for c in select_cols)} FROM `{table}` {where_clause}"

        with connection.cursor() as cursor:
            cursor.execute(q, params)
            rows = cursor.fetchall()

        idx = {c: i for i, c in enumerate(select_cols)}

        for row in rows:
            d = parse_date_like(row[idx[date_col]])
            if not d:
                continue

            # Process hours
            lhrs_val = (
                parse_time_to_hours(row[idx[duration_col]])
                if duration_col else None
            )
            if lhrs_val is None and lhrs_col:
                lhrs_val = parse_time_to_hours(row[idx[lhrs_col]])
            if (lhrs_val is None or lhrs_val == 0) and start_col and end_col:
                elapsed_hours = _duration_hours_from_bounds(
                    row[idx[start_col]], row[idx[end_col]]
                )
                if elapsed_hours is not None:
                    lhrs_val = elapsed_hours
            gen_val = parse_time_to_hours(row[idx.get(gen_col)]) if gen_col else None
            opr_val = parse_time_to_hours(row[idx.get(opr_col)]) if opr_col else None

            if lhrs_val is None and gen_val is not None and opr_val is not None:
                calc = opr_val - gen_val
                lhrs_val = calc if calc >= 0 else 0

            if lhrs_val is None and not duration_col and not lhrs_col:
                lhrs_val = 0
            if lhrs_val is None:
                lhrs_val = 0

            # Build record
            rec = {
                "date": d.strftime("%d-%m-%Y"),
                "state": row[idx.get(state_col)] if state_col else "",
                "site": row[idx.get(site_col)] if site_col else "",
                "wtg": row[idx.get(wec_col)] if wec_col else "",
                "provider": row[idx.get(provider_col)] if provider_col else "",
                "uploaded_by": row[idx.get(uploaded_by_col)] if uploaded_by_col else "",
                "customer": row[idx.get(customer_col)] if customer_col else "",
                "remark": row[idx.get(remarks_col)] if remarks_col else "",
                "breakdown_hours": round(float(lhrs_val), 3)
            }

            breakdown_records.append(rec)

            # Collect distincts
            if provider_col and row[idx.get(provider_col)]: providers_set.add(str(row[idx.get(provider_col)]))
            if uploaded_by_col and row[idx.get(uploaded_by_col)]:
                uploaded_by_set.add(str(row[idx.get(uploaded_by_col)]))
            if customer_col and row[idx.get(customer_col)]: customers_set.add(str(row[idx.get(customer_col)]))
            if state_col and row[idx.get(state_col)]: states_set.add(str(row[idx.get(state_col)]))
            if site_col and row[idx.get(site_col)]: sites_set.add(str(row[idx.get(site_col)]))
            if wec_col and row[idx.get(wec_col)]: wtgs_set.add(str(row[idx.get(wec_col)]))

            total_hours += float(lhrs_val)

    # SORT BY DATE
    breakdown_records.sort(key=lambda x: datetime.strptime(x["date"], "%d-%m-%Y"))

    # PAGINATION
    page = request.GET.get("page", 1)
    paginator = Paginator(breakdown_records, 25)
    try:
        page_obj = paginator.page(page)
    except:
        page_obj = paginator.page(1)

    return render(request, "wind_breakdown_log.html", {
        "data": page_obj.object_list,
        "breakdown_data": json.dumps(page_obj.object_list),
        "providers": sorted(providers_set),
        "uploaded_by_options": sorted(uploaded_by_set),
        "customers": sorted(customers_set),
        "states": sorted(states_set),
        "sites": sorted(sites_set),
        "wtgs": sorted(wtgs_set),
        "selected_providers": providers,
        "selected_uploaded_by": uploaded_by,
        "selected_customers": customers,
        "selected_states": states,
        "selected_sites": sites,
        "selected_wtgs": wtgs,
        "date_from": raw_date_from,
        "date_to": raw_date_to,
        "total_hours": round(total_hours, 3),
        "paginator": paginator,
        "page_obj": page_obj,
        "no_data": len(breakdown_records) == 0,
        "no_data_msg": "No data found for selected filters." if len(breakdown_records) == 0 else "",
    })






import json
import re
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db import connection
import json
import re
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db import connection


@login_required
def dashboard_breakdown(request):
    user = request.user.username.lower()

    # --- Find user's latest table
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        db_tables = [row[0] for row in cursor.fetchall()]
    table_names = [t for t in db_tables if t.startswith(user + "_") and t.endswith("_wind")]

    if not table_names:
        return render(request, "dashboard_breakdown.html", {"error": "No data table found for this user."})

    table_name = sorted(table_names)[-1]

    # --- Get table columns
    with connection.cursor() as cursor:
        cursor.execute(f"SHOW COLUMNS FROM `{table_name}`;")
        cols = [r[0] for r in cursor.fetchall()]
    col_map = {c.lower(): c for c in cols}

    def _pick(col_map, *candidates):
        def normalize(s):
            return s.lower().replace(" ", "").replace(".", "").replace("_", "").replace("(", "").replace(")", "")
        norm_map = {normalize(k): k for k in col_map.keys()}
        for c in candidates:
            nc = normalize(c)
            if nc in norm_map:
                return norm_map[nc]
        return None

    # --- Auto map required columns
    col_oem = _pick(col_map, "oem", "provider", "manufacturer", "make", "client")
    col_customer = _pick(col_map, "customer name", "customer", "client")
    col_state = _pick(col_map, "state")
    col_site = _pick(col_map, "site", "location")
    col_wtg = _pick(col_map, "wtg", "loc no", "loc_no", "turbine", "wec")
    col_date = _pick(col_map, "date", "reading date", "entry date", "gen date", "generation date")

    # --- Handle breakdown columns (Suzlon vs WindWorld)
    col_gf = _pick(col_map, "gf", "grid failure")
    col_fm = _pick(col_map, "fm", "force majeure")
    col_s = _pick(col_map, "s", "schedule", "scheduled services", "gs", "grid shutdown")
    col_u = _pick(col_map, "u", "unscheduled services", "unscheduled", "uptime", "avail")

    if not any([col_gf, col_fm, col_s, col_u]):
        has_breakdown = False
    else:
        has_breakdown = True

    # --- Filters
    f_provider = request.GET.get("provider")
    f_customer = request.GET.get("customer")
    f_state = request.GET.get("state")
    f_site = request.GET.get("site")
    f_wtg = request.GET.get("wtg")
    f_date_from = request.GET.get("date_from")
    f_date_to = request.GET.get("date_to")

    filters = []
    params = []
    if f_provider and col_oem:
        filters.append(f"`{col_oem}` = %s")
        params.append(f_provider)
    if f_customer and col_customer:
        filters.append(f"`{col_customer}` = %s")
        params.append(f_customer)
    if f_state and col_state:
        filters.append(f"`{col_state}` = %s")
        params.append(f_state)
    if f_site and col_site:
        filters.append(f"`{col_site}` = %s")
        params.append(f_site)
    if f_wtg and col_wtg:
        filters.append(f"`{col_wtg}` = %s")
        params.append(f_wtg)
    if f_date_from and f_date_to and col_date:
        filters.append(f"`{col_date}` BETWEEN %s AND %s")
        params.extend([f_date_from, f_date_to])

    where_clause = "WHERE " + " AND ".join(filters) if filters else ""

    # --- Distincts for dropdown filters
    with connection.cursor() as cursor:
        distincts = {}
        for name, col in [
            ("providers", col_oem),
            ("customers", col_customer),
            ("states", col_state),
            ("sites", col_site),
            ("wtgs", col_wtg),
        ]:
            if col:
                cursor.execute(f"SELECT DISTINCT `{col}` FROM `{table_name}` ORDER BY `{col}`;")
                distincts[name] = [r[0] for r in cursor.fetchall() if r[0]]
            else:
                distincts[name] = []

    # --- Data aggregation
    with connection.cursor() as cursor:
        if has_breakdown:
            # ✅ Suzlon-style data
            cursor.execute(f"""
                SELECT `{col_oem}`, `{col_wtg}`,
                       SUM(`{col_gf}`), SUM(`{col_fm}`), SUM(`{col_s}`), SUM(`{col_u}`)
                FROM `{table_name}` {where_clause}
                GROUP BY `{col_oem}`, `{col_wtg}`;
            """, params)
            treemap_data = [
                {"oem": r[0] or "Unknown", "wtg": r[1],
                 "gf": r[2] or 0, "fm": r[3] or 0, "s": r[4] or 0, "u": r[5] or 0}
                for r in cursor.fetchall()
            ]

            cursor.execute(f"""
                SELECT SUM(`{col_gf}`), SUM(`{col_fm}`), SUM(`{col_s}`), SUM(`{col_u}`)
                FROM `{table_name}` {where_clause};
            """, params)
            totals = cursor.fetchone()
            summary = {
                "total_gf": totals[0] or 0,
                "total_fm": totals[1] or 0,
                "total_s": totals[2] or 0,
                "total_u": totals[3] or 0,
            }

        else:
            # --- WindWorld-style data with remarks ---
            col_remarks = _pick(col_map, "remarks", "remark", "observation", "comments", "remark(s)")
            treemap_data = []
            summary = {"total_gf": 0, "total_fm": 0, "total_s": 0, "total_u": 0}

            if col_remarks:
                def extract_hours(text):
                    if not text:
                        return 0
                    text = str(text).lower()
                    total = 0.0
                    for h, m in re.findall(r'(\d{1,2})[:](\d{1,2})\s*hrs?', text):
                        total += int(h) + int(m) / 60.0
                    if total == 0:
                        for h in re.findall(r'(\d{1,3})\s*hrs?\b', text):
                            total += int(h)
                    return round(total, 2)

                read_oem_col = col_oem or col_customer or list(col_map.keys())[0]
                select_col_for_label = col_customer if col_customer else read_oem_col

                cursor.execute(f"""
                    SELECT `{select_col_for_label}`, `{col_wtg}`, `{col_remarks}`
                    FROM `{table_name}` {where_clause};
                """, params)
                rows = cursor.fetchall()

                # --- Build raw list
                for label, wtg_val, remarks in rows:
                    gf = fm = s = u = 0.0
                    if remarks:
                        rtext = str(remarks).lower()

                        # Grid Failure / Breakdown
                        if any(k in rtext for k in ["bd", "breakdown", "grid feeding error", "gf"]):
                            hrs = extract_hours(rtext)
                            gf += hrs if hrs else 1
                            summary["total_gf"] += hrs if hrs else 1

                        # Force Majeure
                        if any(k in rtext for k in ["fm", "force majeure"]):
                            hrs = extract_hours(rtext)
                            fm += hrs if hrs else 1
                            summary["total_fm"] += hrs if hrs else 1

                        # Scheduled / Grid Shutdown
                        if any(k in rtext for k in ["gs", "shutdown", "grid shutdown", "schedule", "s"]):
                            hrs = extract_hours(rtext)
                            s += hrs if hrs else 1
                            summary["total_s"] += hrs if hrs else 1

                        # Unscheduled / Maintenance
                        if any(k in rtext for k in ["pm", "maintenance", "visual maintenance", "preventive maintenance"]):
                            hrs = extract_hours(rtext)
                            u += hrs if hrs else 1
                            summary["total_u"] += hrs if hrs else 1

                    treemap_data.append({
                        "oem": label or "Unknown",
                        "wtg": wtg_val,
                        "gf": round(gf, 2),
                        "fm": round(fm, 2),
                        "s": round(s, 2),
                        "u": round(u, 2),
                    })

                # ✅ Aggregate by WTG to avoid duplicate treemap blocks
                agg_map = {}
                for entry in treemap_data:
                    key = (entry["oem"], entry["wtg"])
                    if key not in agg_map:
                        agg_map[key] = entry
                    else:
                        agg_map[key]["gf"] += entry["gf"]
                        agg_map[key]["fm"] += entry["fm"]
                        agg_map[key]["s"] += entry["s"]
                        agg_map[key]["u"] += entry["u"]

                treemap_data = list(agg_map.values())

            else:
                # --- Simple fallback (if no remarks)
                cursor.execute(f"""
                    SELECT `{col_customer}`, `{col_wtg}`, SUM(`generation`)
                    FROM `{table_name}` {where_clause}
                    GROUP BY `{col_customer}`, `{col_wtg}`;
                """, params)
                treemap_data = [
                    {"oem": r[0] or "Unknown", "wtg": r[1],
                     "gf": 0, "fm": 0, "s": 0, "u": 0, "generation": r[2] or 0}
                    for r in cursor.fetchall()
                ]
                summary = {"total_gf": 0, "total_fm": 0, "total_s": 0, "total_u": 0}

    # --- Context for template
    context = {
        "table_name": table_name,
        "treemap_data": json.dumps(treemap_data),
        "donut_data": json.dumps(treemap_data),
        "summary": summary,
        **distincts,
        "filters": {
            "provider": f_provider,
            "customer": f_customer,
            "state": f_state,
            "site": f_site,
            "wtg": f_wtg,
            "date_from": f_date_from,
            "date_to": f_date_to,
        },
    }

    return render(request, "dashboard_breakdown.html", context)














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

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import connection
  # ✅ safer import


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
from .ml_utils import BreakdownMLAnalyzer, detect_extended_breakdowns
from .recurrence_risk import (
    RISK_TIERS,
    analyze_recurrence_risk,
    filter_recurrence_events,
    natural_sort_key,
    summarize_recurrence_details,
    summarize_risk_groups,
    summarize_wtg_risk,
)


@login_required
def breakdown_analysis(request):
    return _breakdown_analysis(request)


@login_required
def recurrence_risk(request):
    return _breakdown_analysis(request, recurrence_only=True)


def _display_recurrence_filter_value(value):
    if value is None or pd.isna(value) or not str(value).strip():
        return "Unknown"
    return str(value).strip()


def _breakdown_analysis(request, recurrence_only=False):
    username = request.user.username.lower().strip()
    btype = "recurrence" if recurrence_only else request.GET.get("btype", "repetitive")
    table_name = None

    # -----------------------------------------------
    # 1️⃣ FETCH ALL TABLES
    # -----------------------------------------------
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        all_rows = cursor.fetchall()

    all_tables = [str(r[0]).strip().lower() for r in all_rows]

    # Filter only this user's breakdown tables
    user_break_tables = [
        t for t in all_tables
        if t.startswith(username + "_") and "breakdowndata" in t
    ]

    if not user_break_tables:
        return render(request, "breakdown_analysis.html", {
            "alerts": [],
            "chart_data": {},
            "error_msg": f"No breakdown table found for user '{username}'.",
            "btype": btype
        })

    table_name = sorted(user_break_tables)[-1]  # Latest table

    # -----------------------------------------------
    # 2️⃣ LOAD CANONICAL BREAKDOWN FIELDS
    # -----------------------------------------------
    header_aliases = {
        "gen_date": ("gen_date", "date", "generation_date", "breakdown_date"),
        "loc_no": (
            "loc_no", "location_no", "wtg", "wtg_no", "wec", "machine",
            "asset_id", "machine_id",
        ),
        "breakdown_remarks": (
            "breakdown_remarks",
            "remarks",
            "remark",
            "breakdown_details",
            "description",
        ),
    }
    optional_header_aliases = {
        "provider": ("provider", "oem", "oem_provider", "manufacturer"),
        "site": ("site", "site_name", "plant", "plant_name", "location"),
        "state": ("state", "state_name", "statename"),
        "rds_code": ("rds_code", "rds_pp_code", "equipment_code"),
        "system_name": ("system_name", "system"),
        "subsystem_name": ("subsystem_name", "subsystem"),
        "standard_component": (
            "standard_component", "component", "equipment_component"
        ),
        "classification_status": ("classification_status",),
        "duration_hrs": (
            "duration_hrs", "duration_hours", "breakdown_hours", "duration",
            "hours", "lhrs", "loss_hours", "loss_hrs",
        ),
        "start_time": ("start_time", "breakdown_start", "start_datetime"),
        "end_time": ("end_time", "breakdown_end", "end_datetime"),
    }

    with connection.cursor() as cursor:
        cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
        table_columns = [str(row[0]).strip() for row in cursor.fetchall()]

    normalized_columns = {
        column.strip().lower().replace(".", "").replace(" ", "_"): column
        for column in table_columns
    }
    selected_columns = {}
    for canonical, aliases in header_aliases.items():
        actual = next(
            (normalized_columns[alias] for alias in aliases if alias in normalized_columns),
            None,
        )
        if actual:
            selected_columns[canonical] = actual

    missing_headers = set(header_aliases) - set(selected_columns)
    if missing_headers:
        return render(request, "breakdown_analysis.html", {
            "alerts": [],
            "chart_data": {},
            "error_msg": (
                f"Table '{table_name}' is missing required breakdown headers: "
                f"{', '.join(sorted(missing_headers))}."
            ),
            "btype": btype
        })

    for column, aliases in optional_header_aliases.items():
        actual = next(
            (normalized_columns[alias] for alias in aliases if alias in normalized_columns),
            None,
        )
        if actual:
            selected_columns[column] = actual

    select_parts = [
        f"`{actual.replace('`', '``')}` AS `{canonical}`"
        for canonical, actual in selected_columns.items()
    ]
    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT {', '.join(select_parts)} FROM `{table_name}`"
        )
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]

    if not rows:
        return render(request, "breakdown_analysis.html", {
            "alerts": [],
            "chart_data": {},
            "error_msg": f"Table '{table_name}' has no data.",
            "btype": btype
        })

    df = pd.DataFrame(rows, columns=columns)
    df["gen_date"] = pd.to_datetime(df["gen_date"], errors="coerce")
    if "duration_hrs" in df:
        durations = df["duration_hrs"].map(parse_time_to_hours)
    else:
        durations = pd.Series(float("nan"), index=df.index)
    durations = pd.to_numeric(durations, errors="coerce")
    if "start_time" in df and "end_time" in df:
        derived_durations = df.apply(
            lambda row: _duration_hours_from_bounds(
                row["start_time"], row["end_time"]
            ),
            axis=1,
        )
        durations = durations.where(
            durations.notna() & (durations > 0), derived_durations
        )
    df["duration_hours"] = pd.to_numeric(durations, errors="coerce")
    if btype == "recurrence":
        df = analyze_recurrence_risk(df)
        from accounts.models import RDSCatalog

        for field in ("subsystem_name", "system_name", "standard_component"):
            if field not in df:
                df[field] = pd.NA
            df[field] = df[field].replace("", pd.NA)
        rds_codes = df["rds_code"].dropna().astype(str).str.strip().unique()
        catalog = {
            code: {
                "subsystem_name": subsystem,
                "system_name": system,
                "standard_component": component,
            }
            for code, subsystem, system, component in RDSCatalog.objects.filter(
                rds_code__in=rds_codes
            ).values_list(
                "rds_code",
                "subsystem_name",
                "system_name",
                "standard_component",
            )
        }
        for field in ("subsystem_name", "system_name", "standard_component"):
            mapped_values = df["rds_code"].map(
                lambda code: catalog.get(str(code).strip(), {}).get(field)
            )
            df[field] = df[field].where(df[field].notna(), mapped_values)
        recurrence_reference_date = df["event_start"].max()
    else:
        recurrence_reference_date = None
    wtg_options = sorted(df["loc_no"].dropna().astype(str).unique().tolist())
    history_df = df.copy()

    # -----------------------------------------------
    # 4️⃣ GET FILTERS (Including NEW Breakdown Type)
    # -----------------------------------------------
    if btype == "recurrence":
        recurrence_filter_fields = ("provider", "site", "state", "loc_no")
        recurrence_filter_labels = {
            "provider": "OEM / Provider",
            "site": "Site name",
            "state": "State name",
            "loc_no": "WTG number",
        }
        selected_recurrence_filters = {
            field: request.GET.get(field, "").strip()
            for field in recurrence_filter_fields
        }
        recurrence_filter_options = {}
        for field in recurrence_filter_fields:
            values = (
                df[field].dropna().astype(str).str.strip()
                if field in df.columns
                else pd.Series(dtype=str)
            )
            values = [value for value in values.unique().tolist() if value]
            values.sort(key=natural_sort_key)
            has_missing_values = (
                field not in df.columns
                or df[field].isna().any()
                or (df[field].astype(str).str.strip() == "").any()
            )
            if has_missing_values:
                values.insert(0, "__missing__")
            recurrence_filter_options[field] = values
        severity_filter = ""
        wtg_filter = ""
        date_from = ""
        date_to = ""
    else:
        severity_filter = request.GET.get("severity", "")
        wtg_filter = request.GET.get("wtg", "")
        date_from = request.GET.get("from", "")
        date_to = request.GET.get("to", "")

    # -----------------------------------------------
    # 5️⃣ APPLY FILTERS
    # -----------------------------------------------
    if btype == "recurrence":
        df = filter_recurrence_events(df, selected_recurrence_filters)

    if btype != "recurrence" and wtg_filter:
        df = df[df["loc_no"].astype(str) == wtg_filter]

    if btype != "recurrence" and date_from:
        parsed_date_from = pd.to_datetime(date_from, errors="coerce")
        if pd.isna(parsed_date_from):
            return render(request, "breakdown_analysis.html", {
                "alerts": [],
                "chart_data": {},
                "error_msg": "The start date filter is invalid.",
                "btype": btype,
            })
        df = df[df["gen_date"] >= parsed_date_from.normalize()]

    if btype != "recurrence" and date_to:
        parsed_date_to = pd.to_datetime(date_to, errors="coerce")
        if pd.isna(parsed_date_to):
            return render(request, "breakdown_analysis.html", {
                "alerts": [],
                "chart_data": {},
                "error_msg": "The end date filter is invalid.",
                "btype": btype,
            })
        df = df[df["gen_date"] < parsed_date_to.normalize() + pd.Timedelta(days=1)]

    if df.empty:
        return render(request, "breakdown_analysis.html", {
            "alerts": [],
            "chart_data": {},
            "error_msg": "No data for selected filters.",
            "btype": btype,
            "wtg_options": wtg_options,
            "recurrence_filter_fields": (
                recurrence_filter_fields if btype == "recurrence" else []
            ),
            "recurrence_filter_labels": (
                recurrence_filter_labels if btype == "recurrence" else {}
            ),
            "recurrence_filter_options": (
                recurrence_filter_options if btype == "recurrence" else {}
            ),
            "selected_recurrence_filters": (
                selected_recurrence_filters if btype == "recurrence" else {}
            ),
            "risk_cards": [],
            "risk_group_data": [],
            "top_wtgs": [],
            "subsystem_risk_data": [],
            "recurrence_profile_data": [],
            "recurrence_reference_date": (
                recurrence_reference_date.strftime("%Y-%m-%d")
                if recurrence_reference_date is not None
                and pd.notna(recurrence_reference_date)
                else None
            ),
        })

    # -----------------------------------------------
    # 6️⃣ EXTENDED BREAKDOWN MODE (COMPONENT-WISE P90)
    # -----------------------------------------------
    if btype == "recurrence":
        severity_labels = {
            "CRITICAL_RECURRENCE": "Critical",
            "HIGH_RECURRENCE_RISK": "High",
            "MODERATE_RECURRENCE": "Medium",
            "NORMAL": "Low",
        }
        risk_labels = {
            "CRITICAL_RECURRENCE": "Critical recurrence",
            "HIGH_RECURRENCE_RISK": "High recurrence risk",
            "MODERATE_RECURRENCE": "Moderate recurrence",
            "NORMAL": "Normal",
        }
        tier_counts, _ = summarize_wtg_risk(df)
        risk_group_data = summarize_risk_groups(df, "provider")
        top_wtgs, subsystem_risk_data, recurrence_profile_data = (
            summarize_recurrence_details(df, recurrence_reference_date)
        )
        risk_cards = [
            {
                "key": risk_tier,
                "label": risk_labels[risk_tier],
                "count": tier_counts[risk_tier],
                "style": {
                    "CRITICAL_RECURRENCE": "critical",
                    "HIGH_RECURRENCE_RISK": "high",
                    "MODERATE_RECURRENCE": "moderate",
                    "NORMAL": "normal",
                }[risk_tier],
            }
            for risk_tier in RISK_TIERS
        ]
        alerts = []
        for _, row in df.iterrows():
            event_start = row["event_start"]
            if pd.isna(event_start):
                continue
            risk_tier = row["risk_tier"] or "NORMAL"
            if severity_filter and risk_tier != severity_filter:
                continue
            machine = str(row["loc_no"])
            code = row.get("rds_code")
            code = None if pd.isna(code) else str(code)
            remark = row.get("breakdown_remarks")
            remark = "" if pd.isna(remark) else str(remark)
            taxonomy = {
                field: None if pd.isna(row.get(field)) else str(row.get(field))
                for field in ("system_name", "subsystem_name", "standard_component")
            }
            tbf_days = row.get("tbf_days")
            alerts.append({
                "machine": machine,
                "provider_label": _display_recurrence_filter_value(row.get("provider")),
                "site_label": _display_recurrence_filter_value(row.get("site")),
                "state_label": _display_recurrence_filter_value(row.get("state")),
                "severity": severity_labels[risk_tier],
                "risk_tier": risk_tier,
                "risk_label": risk_labels[risk_tier],
                "date": event_start.strftime("%Y-%m-%d"),
                "message": remark,
                "rds_code": code,
                **taxonomy,
                "tbf_days": round(float(tbf_days), 2) if pd.notna(tbf_days) else None,
                "cumulative_failure_count": int(row["cumulative_failure_count"]),
                "failures_last_30d": int(row["failures_last_30d"]),
                "failures_last_90d": int(row["failures_last_90d"]),
                "failures_last_365d": int(row["failures_last_365d"]),
                "mtbf_days": round(float(row["mtbf_days"]), 2)
                if pd.notna(row["mtbf_days"]) else None,
            })
        alerts.sort(
            key=lambda alert: (
                natural_sort_key(alert["provider_label"]),
                natural_sort_key(alert["site_label"]),
                natural_sort_key(alert["state_label"]),
                natural_sort_key(alert["machine"]),
                alert["date"],
            )
        )

        chart_data = {}
        for alert in alerts:
            chart_data[alert["machine"]] = chart_data.get(alert["machine"], 0) + 1

        affected_wtgs = len(chart_data)
        most_repetitive_wtg = max(chart_data, key=chart_data.get) if chart_data else None
        most_repetitions = chart_data.get(most_repetitive_wtg, 0)
        request.session["bd_alerts"] = alerts
        return render(request, "breakdown_analysis.html", {
            "alerts": alerts,
            "chart_data": chart_data,
            "error_msg": None,
            "severity_filter": severity_filter,
            "wtg_filter": wtg_filter,
            "date_from": "",
            "date_to": "",
            "total_alerts": len(alerts),
            "affected_wtgs": affected_wtgs,
            "repetition_rate": 0,
            "most_repetitive_wtg": most_repetitive_wtg,
            "most_repetitions": most_repetitions,
            "wtg_options": wtg_options,
            "dynamic_table": table_name,
            "btype": btype,
            "risk_cards": risk_cards,
            "recurrence_filter_fields": recurrence_filter_fields,
            "recurrence_filter_labels": recurrence_filter_labels,
            "recurrence_filter_options": recurrence_filter_options,
            "selected_recurrence_filters": selected_recurrence_filters,
            "risk_group_data": risk_group_data,
            "top_wtgs": top_wtgs,
            "subsystem_risk_data": subsystem_risk_data,
            "recurrence_profile_data": recurrence_profile_data,
            "recurrence_reference_date": (
                recurrence_reference_date.strftime("%Y-%m-%d")
                if pd.notna(recurrence_reference_date)
                else None
            ),
        })

    if btype == "extended":
        alerts = detect_extended_breakdowns(df, history_df)
        chart_data = {}
        for alert in alerts:
            machine = alert["machine"]
            chart_data[machine] = chart_data.get(machine, 0) + 1
        total_alerts = len(alerts)
        affected_wtgs = len(chart_data)
        most_repetitive_wtg = None
        most_repetitions = 0
        if chart_data:
            most_repetitive_wtg, most_repetitions = max(
                chart_data.items(), key=lambda item: item[1]
            )
        request.session["bd_alerts"] = alerts
        return render(request, "breakdown_analysis.html", {
            "alerts": alerts,
            "chart_data": chart_data,
            "error_msg": None,
            "severity_filter": severity_filter,
            "wtg_filter": wtg_filter,
            "date_from": date_from,
            "date_to": date_to,
            "total_alerts": total_alerts,
            "affected_wtgs": affected_wtgs,
            "repetition_rate": 0,
            "most_repetitive_wtg": most_repetitive_wtg,
            "most_repetitions": most_repetitions,
            "wtg_options": wtg_options,
            "dynamic_table": table_name,
            "btype": btype,
        })

    # -----------------------------------------------
    # 7️⃣ REPETITIVE BREAKDOWN MODE (NORMAL ML MODEL)
    # -----------------------------------------------
    analyzer = BreakdownMLAnalyzer(similarity_threshold=0.60, days_window=8)
    analyzer.load_dataframe(df)
    alerts = analyzer.detect_repetitions()

    if severity_filter:
        alerts = [a for a in alerts if a["severity"] == severity_filter]

    # Chart + KPIs
    chart_data = {}
    for a in alerts:
        machine = str(a.get("machine", "Unknown"))
        chart_data[machine] = chart_data.get(machine, 0) + 1

    total_alerts = len(alerts)
    affected_wtgs = len(chart_data)
    repetition_rate = round((total_alerts / affected_wtgs) * 100, 2) if affected_wtgs else 0

    most_repetitive_wtg = None
    most_repetitions = 0
    if chart_data:
        most_repetitive_wtg, most_repetitions = max(chart_data.items(), key=lambda x: x[1])

    # -----------------------------------------------
    # 8️⃣ RENDER REPETITIVE BREAKDOWN DASHBOARD
    # -----------------------------------------------
    request.session["bd_alerts"] = alerts
    return render(request, "breakdown_analysis.html", {
        "alerts": alerts,
        "chart_data": chart_data,
        "error_msg": None,

        "severity_filter": severity_filter,
        "wtg_filter": wtg_filter,
        "date_from": date_from,
        "date_to": date_to,

        "total_alerts": total_alerts,
        "affected_wtgs": affected_wtgs,
        "repetition_rate": repetition_rate,

        "most_repetitive_wtg": most_repetitive_wtg,
        "most_repetitions": most_repetitions,
        "wtg_options": wtg_options,

        "dynamic_table": table_name,
        "btype": btype  # NEW
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
