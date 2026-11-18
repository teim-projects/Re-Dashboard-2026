from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db import connection

@login_required
def wind_dashboard(request):
    from customer_dashboard.data_service import get_wind_dashboard_data, get_filter_context
    f_ctx = get_filter_context(request.user, request)
    data = get_wind_dashboard_data(
        request.user,
        date_from=f_ctx["date_from"],
        date_to=f_ctx["date_to"],
        providers=f_ctx["selected_providers"],
        sites=f_ctx["selected_sites"],
        states=f_ctx["selected_states"],
        wtgs=f_ctx["selected_wtgs"],
    )
    return render(request, 'wind_dashboard.html', {**data, **f_ctx})

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
    import json
    from customer_dashboard.data_service import get_installation_summary_data
    inst_data = get_installation_summary_data(request.user)

    # Regional Capacity Raw
    capacity_by_state_raw = [("Maharashtra", 30.0, 20), ("Kerala", 16.0, 8), ("Gujarat", 6.3, 3)]
    total_capacity = sum(c[1] for c in capacity_by_state_raw)  # 52.3 MW
    total_wtgs = sum(c[2] for c in capacity_by_state_raw)      # 31 WTGs

    capacity_by_state = []
    for state, cap, wtgs in capacity_by_state_raw:
        pct = round((cap / total_capacity) * 100, 1) if total_capacity else 0
        capacity_by_state.append({
            "state": state,
            "capacity_mw": f"{cap:.1f} MW",
            "capacity_val": cap,
            "wtg_count": wtgs,
            "pct": pct
        })

    # Land Type
    land_type_raw = [("Maharashtra", "Revenue", 20), ("Kerala", "Private", 8), ("Gujarat", "Private", 3)]
    land_type_by_state = []
    for state, land, count in land_type_raw:
        pct = round((count / total_wtgs) * 100, 1) if total_wtgs else 0
        land_type_by_state.append({
            "state": state,
            "land": land,
            "count": count,
            "pct": pct
        })

    # WTG Generation list formatted cleanly
    raw_wtgs = inst_data.get("wtg_locations", [])
    wtg_generation = []
    wtg_chart_labels = []
    wtg_chart_values = []

    total_est_gen = 0.0
    for idx, w in enumerate(raw_wtgs):
        loc = str(w[0])
        try:
            val = float(w[1])
        except (ValueError, TypeError):
            val = 0.0
        total_est_gen += val
        wtg_generation.append({
            "rank": idx + 1,
            "location": loc,
            "avg_gen_raw": val,
            "avg_gen": f"{val:,.1f}",
            "avg_gen_int": f"{int(round(val)):,}"
        })
        if len(wtg_chart_labels) < 10:
            wtg_chart_labels.append(loc)
            wtg_chart_values.append(round(val, 1))

    avg_gen_per_wtg = round(total_est_gen / len(raw_wtgs), 1) if raw_wtgs else 0.0

    # Power Sale details
    power_sale = [
        {
            "detail": "SECI Offtake (ISTS Central Grid)",
            "state": "Maharashtra",
            "capacity": "30.0 MW",
            "category": "Central Sovereign Utility",
            "counterparty": "Solar Energy Corporation of India",
            "tenure": "25 Years PPA",
            "badge_class": "bg-success-subtle text-success border border-success-subtle"
        },
        {
            "detail": "Private Commercial PPA",
            "state": "Kerala",
            "capacity": "16.0 MW",
            "category": "Bilateral Commercial / Industrial",
            "counterparty": "High-Tension Captive Offtakers",
            "tenure": "15 Years Bilateral",
            "badge_class": "bg-primary-subtle text-primary border border-primary-subtle"
        },
        {
            "detail": "State Grid Discom Offtake",
            "state": "Gujarat",
            "capacity": "6.3 MW",
            "category": "State Utility (GETCO / GUVNL)",
            "counterparty": "Gujarat Urja Vikas Nigam Ltd",
            "tenure": "25 Years Tariff PPA",
            "badge_class": "bg-warning-subtle text-warning border border-warning-subtle"
        },
    ]

    oem_breakup = inst_data.get("oem_breakup", [])

    # Legacy fallback dictionary
    legacy_data = {
        "capacity_by_state": [("Kerala", "16.0 MW"), ("Maharashtra", "30.0 MW"), ("Gujarat", "6.3 MW")],
        "land_type_by_state": [("Kerala", "Private", 8), ("Maharashtra", "Revenue", 20), ("Gujarat", "Private", 3)],
        "wtg_generation": raw_wtgs,
        "power_sale": [("Private PPA", "Kerala"), ("SECI", "Maharashtra"), ("State Grid", "Gujarat")],
    }

    context = {
        "data": legacy_data,
        "capacity_by_state": capacity_by_state,
        "land_type_by_state": land_type_by_state,
        "wtg_generation": wtg_generation,
        "power_sale": power_sale,
        "oem_breakup": oem_breakup,
        "total_capacity": round(total_capacity, 1),
        "total_wtgs": total_wtgs,
        "total_est_gen": round(total_est_gen, 1),
        "total_est_gen_display": f"{int(round(total_est_gen)):,}",
        "avg_gen_per_wtg": f"{avg_gen_per_wtg:,.1f}",
        "state_count": len(capacity_by_state_raw),
        "capacity_labels_json": json.dumps([c["state"] for c in capacity_by_state]),
        "capacity_values_json": json.dumps([c["capacity_val"] for c in capacity_by_state]),
        "wtg_chart_labels_json": json.dumps(wtg_chart_labels),
        "wtg_chart_values_json": json.dumps(wtg_chart_values),
        "table_exists": True,
        "table_name": "installation_summary_wind"
    }
    return render(request, "wind_summary1.html", context)

@login_required
def wind_installation_summary2(request):
    import json
    from customer_dashboard.data_service import get_installation_summary_data
    inst_data = get_installation_summary_data(request.user)

    raw_json = json.loads(inst_data.get("data", "{}")) if isinstance(inst_data.get("data"), str) else inst_data.get("data", {})
    ps_labels = raw_json.get("power_sale_labels", ["Captive / PPA", "State Grid", "Third Party"])
    ps_counts = raw_json.get("power_sale_counts", [18, 10, 3])
    land_labels = raw_json.get("land_labels", ["Private Land", "Revenue Land", "Forest Land"])
    land_counts = raw_json.get("land_counts", [20, 8, 3])

    total_wtgs = sum(ps_counts) if ps_counts else 31

    # Offtake rows with percentages
    power_sale_rows = []
    for label, count in zip(ps_labels, ps_counts):
        pct = round((count / total_wtgs) * 100, 1) if total_wtgs else 0
        power_sale_rows.append({
            "label": label,
            "count": count,
            "pct": pct
        })

    # Land rows with percentages
    total_land = sum(land_counts) if land_counts else total_wtgs
    land_rows = []
    for label, count in zip(land_labels, land_counts):
        pct = round((count / total_land) * 100, 1) if total_land else 0
        land_rows.append({
            "label": label,
            "count": count,
            "pct": pct
        })

    # WTG Locations formatted
    raw_wtgs = inst_data.get("wtg_locations", [])
    max_gen = max([w[1] for w in raw_wtgs], default=1.0)
    wtg_locations_formatted = []
    for idx, w in enumerate(raw_wtgs, 1):
        loc_name = str(w[0])
        gen_val = float(w[1]) if w[1] else 0.0
        pct = round((gen_val / max_gen) * 100, 1) if max_gen else 0
        wtg_locations_formatted.append({
            "rank": idx,
            "loc": loc_name,
            "gen_val": round(gen_val, 2),
            "gen_display": f"{gen_val:,.2f}",
            "pct": pct
        })

    # OEM Breakup formatted
    raw_oems = inst_data.get("oem_breakup", [])
    total_oem_wtgs = sum(r[3] for r in raw_oems) if raw_oems else total_wtgs
    total_cap = 0.0
    oem_breakup_formatted = []
    for r in raw_oems:
        try:
            val = float(str(r[0]).replace("MW", "").strip())
            total_cap += val * int(r[3])
        except Exception:
            pass
        cnt = r[3]
        pct = round((cnt / total_oem_wtgs) * 100, 1) if total_oem_wtgs else 0
        oem_breakup_formatted.append({
            "capacity": str(r[0]),
            "firm": str(r[1]),
            "make": str(r[2]),
            "count": cnt,
            "pct": pct
        })
    if not total_cap:
        total_cap = 52.3

    context = {
        **inst_data,
        "total_wtgs": total_wtgs,
        "total_capacity": round(total_cap, 1),
        "power_sale_labels_json": json.dumps(ps_labels),
        "power_sale_counts_json": json.dumps(ps_counts),
        "land_labels_json": json.dumps(land_labels),
        "land_counts_json": json.dumps(land_counts),
        "power_sale_rows": power_sale_rows,
        "land_rows": land_rows,
        "wtg_locations_formatted": wtg_locations_formatted,
        "oem_breakup_formatted": oem_breakup_formatted,
        "dominant_offtake": power_sale_rows[0]["label"] if power_sale_rows else "Captive / PPA",
        "dominant_offtake_count": power_sale_rows[0]["count"] if power_sale_rows else 18,
        "dominant_offtake_pct": power_sale_rows[0]["pct"] if power_sale_rows else 58.1,
        "dominant_land": land_rows[0]["label"] if land_rows else "Private Land",
        "dominant_land_count": land_rows[0]["count"] if land_rows else 20,
        "dominant_land_pct": land_rows[0]["pct"] if land_rows else 64.5,
    }
    return render(request, "wind_installation_summary2.html", context)

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
    if request.GET.get("clear_filters"):
        request.session.pop("wind_filters", None)

    saved = request.session.get("wind_filters", {})

    def get_or_saved_list(key):
        vals = request.GET.getlist(key)
        return vals if vals else saved.get(key, [])

    date_from = request.GET.get("date_from") or saved.get("date_from")
    date_to   = request.GET.get("date_to")   or saved.get("date_to")

    from customer_dashboard.data_service import (
        get_user_wind_tables,
        get_filter_options,
        get_generation_kwh_data,
        canonicalize_provider_name,
    )

    raw_providers = get_or_saved_list("provider")
    providers = sorted(list(set([canonicalize_provider_name(p) for p in raw_providers if p])))
    uploaded_by = get_or_saved_list("uploaded_by")
    customers = get_or_saved_list("customer")
    states    = get_or_saved_list("state")
    sites     = get_or_saved_list("site")
    wtgs      = get_or_saved_list("wtg")

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
    gen_tables, bd_tables = get_user_wind_tables(request.user)
    filter_opts = get_filter_options(gen_tables, bd_tables)

    data = get_generation_kwh_data(
        request.user,
        date_from=date_from,
        date_to=date_to,
        providers=providers,
        sites=sites,
        states=states,
        wtgs=wtgs,
    )

    context = {
        **data,
        "providers": filter_opts["providers"],
        "customers": filter_opts["customers"],
        "states": filter_opts["states"],
        "sites": filter_opts["sites"],
        "wtgs": filter_opts["wtgs"],
        "selected_providers": providers,
        "selected_customers": customers,
        "selected_states": states,
        "selected_sites": sites,
        "selected_wtgs": wtgs,
        "date_from": date_from or "",
        "date_to": date_to or "",
        "no_data": data["wtg_count"] == 0,
        "no_data_msg": "No wind generation data found for the selected filters." if data["wtg_count"] == 0 else "",
    }
    return render(request, "wind_generation_kwh.html", context)

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
    from customer_dashboard.data_service import get_generation_hours_data, get_filter_context
    f_ctx = get_filter_context(request.user, request)
    data = get_generation_hours_data(
        request.user,
        date_from=f_ctx["date_from"],
        date_to=f_ctx["date_to"],
        providers=f_ctx["selected_providers"],
        sites=f_ctx["selected_sites"],
        states=f_ctx["selected_states"],
        wtgs=f_ctx["selected_wtgs"],
    )
    return render(request, "wind_genration_hovers.html", {**data, **f_ctx})









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
    from customer_dashboard.data_service import get_avg_generation_data, get_filter_context
    f_ctx = get_filter_context(request.user, request)
    data = get_avg_generation_data(
        request.user,
        date_from=f_ctx["date_from"],
        date_to=f_ctx["date_to"],
        providers=f_ctx["selected_providers"],
        sites=f_ctx["selected_sites"],
        states=f_ctx["selected_states"],
        wtgs=f_ctx["selected_wtgs"],
    )
    return render(request, "wind_avg_genration.html", {**data, **f_ctx})



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
    from customer_dashboard.data_service import get_grid_and_machine_data, get_filter_context
    f_ctx = get_filter_context(request.user, request)
    data = get_grid_and_machine_data(
        request.user,
        date_from=f_ctx["date_from"],
        date_to=f_ctx["date_to"],
        providers=f_ctx["selected_providers"],
        sites=f_ctx["selected_sites"],
        states=f_ctx["selected_states"],
        wtgs=f_ctx["selected_wtgs"],
    )
    return render(request, "wind_Grid_Availability_and_Machine.html", {**data, **f_ctx})

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
    from customer_dashboard.data_service import get_drill_down_data, get_filter_context
    f_ctx = get_filter_context(request.user, request)
    selected_wtg = request.GET.get("wtg")
    if not selected_wtg and f_ctx["selected_wtgs"]:
        selected_wtg = f_ctx["selected_wtgs"][0]
    data = get_drill_down_data(
        request.user,
        selected_wtg=selected_wtg,
        date_from=f_ctx["date_from"],
        date_to=f_ctx["date_to"],
        providers=f_ctx["selected_providers"],
        sites=f_ctx["selected_sites"],
        states=f_ctx["selected_states"],
        wtgs=f_ctx["selected_wtgs"],
    )
    return render(request, "wind_drill_down.html", {**data, **f_ctx})


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
    from customer_dashboard.data_service import get_machine_availability_data, get_filter_context
    f_ctx = get_filter_context(request.user, request)
    data = get_machine_availability_data(
        request.user,
        date_from=f_ctx["date_from"],
        date_to=f_ctx["date_to"],
        providers=f_ctx["selected_providers"],
        sites=f_ctx["selected_sites"],
        states=f_ctx["selected_states"],
        wtgs=f_ctx["selected_wtgs"],
    )
    return render(request, "wind_Avg_Machine_Availability.html", {**data, **f_ctx})



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
    from customer_dashboard.data_service import get_wtg_plf_data, get_filter_context
    f_ctx = get_filter_context(request.user, request)
    data = get_wtg_plf_data(
        request.user,
        date_from=f_ctx["date_from"],
        date_to=f_ctx["date_to"],
        providers=f_ctx["selected_providers"],
        sites=f_ctx["selected_sites"],
        states=f_ctx["selected_states"],
        wtgs=f_ctx["selected_wtgs"],
    )
    return render(request, "wind_wtg_plf.html", {**data, **f_ctx})


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
    from customer_dashboard.data_service import get_grid_availability_data, get_filter_context
    f_ctx = get_filter_context(request.user, request)
    data = get_grid_availability_data(
        request.user,
        date_from=f_ctx["date_from"],
        date_to=f_ctx["date_to"],
        providers=f_ctx["selected_providers"],
        sites=f_ctx["selected_sites"],
        states=f_ctx["selected_states"],
        wtgs=f_ctx["selected_wtgs"],
    )
    return render(request, "wind_Grid_Availability.html", {**data, **f_ctx})





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
    from customer_dashboard.data_service import get_breakdown_hours_data, get_filter_context
    f_ctx = get_filter_context(request.user, request)
    data = get_breakdown_hours_data(
        request.user,
        date_from=f_ctx["date_from"],
        date_to=f_ctx["date_to"],
        providers=f_ctx["selected_providers"],
        sites=f_ctx["selected_sites"],
        states=f_ctx["selected_states"],
        wtgs=f_ctx["selected_wtgs"],
    )
    return render(request, "wind_breakdown_hours.html", {**data, **f_ctx})



























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
    from customer_dashboard.data_service import get_breakdown_log_data, get_filter_context
    from django.http import JsonResponse

    f_ctx = get_filter_context(request.user, request)
    uploaded_by = request.GET.getlist("uploaded_by")

    bd_result = get_breakdown_log_data(
        request.user,
        date_from=f_ctx["date_from"],
        date_to=f_ctx["date_to"],
        providers=f_ctx["selected_providers"],
        customers=f_ctx["selected_customers"],
        states=f_ctx["selected_states"],
        sites=f_ctx["selected_sites"],
        wtgs=f_ctx["selected_wtgs"],
        uploaded_by=uploaded_by,
    )

    all_records = bd_result["records"]
    total_records = bd_result["total_records"]

    # Handle DataTables server-side AJAX requests (pagination, search, sort)
    if request.GET.get("draw") or request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get("format") == "json":
        draw = int(request.GET.get("draw", 1))
        start = int(request.GET.get("start", 0))
        length = int(request.GET.get("length", 10))
        search_val = request.GET.get("search[value]", "").strip().lower()

        # Search across fields
        if search_val:
            filtered = [
                r for r in all_records
                if search_val in r["date"].lower()
                or search_val in str(r["state"]).lower()
                or search_val in str(r["site"]).lower()
                or search_val in str(r["wtg"]).lower()
                or search_val in str(r["provider"]).lower()
                or search_val in str(r["uploaded_by"]).lower()
                or search_val in str(r["remark"]).lower()
                or search_val in str(r["breakdown_hours"])
            ]
        else:
            filtered = all_records

        # Sorting
        order_col_idx = request.GET.get("order[0][column]", "0")
        order_dir = request.GET.get("order[0][dir]", "desc")
        col_keys = ["sort_date", "state", "site", "wtg", "provider", "uploaded_by", "remark", "breakdown_hours"]
        try:
            sort_key = col_keys[int(order_col_idx)]
        except (ValueError, IndexError):
            sort_key = "sort_date"

        reverse = (order_dir == "desc")
        if sort_key == "sort_date":
            filtered.sort(key=lambda x: x["sort_date"], reverse=reverse)
        elif sort_key == "breakdown_hours":
            filtered.sort(key=lambda x: x["breakdown_hours"], reverse=reverse)
        else:
            filtered.sort(key=lambda x: str(x.get(sort_key) or "").lower(), reverse=reverse)

        # Slice page
        page_records = filtered[start : start + length] if length > 0 else filtered

        return JsonResponse({
            "draw": draw,
            "recordsTotal": total_records,
            "recordsFiltered": len(filtered),
            "data": [
                {
                    "date": r["date"],
                    "state": r["state"],
                    "site": r["site"],
                    "wtg": r["wtg"],
                    "provider": r["provider"],
                    "uploaded_by": r["uploaded_by"],
                    "remark": r["remark"],
                    "breakdown_hours": r["breakdown_hours"]
                }
                for r in page_records
            ]
        })

    # Standard browser GET (Initial HTML page render)
    return render(request, "wind_breakdown_log.html", {
        **f_ctx,
        "total_hours": bd_result["total_hours"],
        "total_records": total_records,
        "total_wtgs_affected": bd_result["total_wtgs_affected"],
        "total_sites_count": bd_result["total_sites_count"],
        "total_states_count": bd_result["total_states_count"],
        "data": [],
        "no_data": total_records == 0,
        "no_data_msg": "No breakdown records found for selected filters." if total_records == 0 else "",
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
    from customer_dashboard.data_service import get_breakdown_hours_data, get_filter_context
    f_ctx = get_filter_context(request.user, request)
    data = get_breakdown_hours_data(
        request.user,
        date_from=f_ctx["date_from"],
        date_to=f_ctx["date_to"],
        providers=f_ctx["selected_providers"],
        sites=f_ctx["selected_sites"],
        states=f_ctx["selected_states"],
        wtgs=f_ctx["selected_wtgs"],
    )
    return render(request, "dashboard_breakdown.html", {**data, **f_ctx})














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
    from customer_dashboard.data_service import get_breakdown_analysis_data, get_filter_context
    f_ctx = get_filter_context(request.user, request)
    btype = "recurrence" if recurrence_only else request.GET.get("btype", "repetitive")
    sev = request.GET.get("severity")
    wtg = request.GET.get("wtg")
    if not wtg and f_ctx["selected_wtgs"]:
        wtg = f_ctx["selected_wtgs"][0]
    data = get_breakdown_analysis_data(
        request.user,
        btype=btype,
        severity_filter=sev,
        wtg_filter=wtg,
        date_from=f_ctx["date_from"],
        date_to=f_ctx["date_to"],
    )
    return render(request, "breakdown_analysis.html", {**data, **f_ctx})




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
