from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required

















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
import os
import re
import traceback
import pandas as pd
import os
import re
import traceback
import pandas as pd
import numpy as np
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.db import connection
from django.contrib.auth.models import User
from django.utils.timezone import now
from accounts.models import Provider, EnergyType, ProviderColumnMapping
from accounts.breakdown_mapping import canonicalize_breakdown_dataframe
from accounts.breakdown_ingestion import insert_canonical_breakdown_rows
from .models import UploadMetadata



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
import os
import re
import traceback
import pandas as pd
import os
import re
import traceback
import pandas as pd
import numpy as np
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.db import connection
from django.contrib.auth.models import User
from django.utils.timezone import now
from accounts.models import Provider, EnergyType
from .models import UploadMetadata

# =================== HELPERS =================== #

import pandas as pd, numpy as np, os, re, traceback
from datetime import datetime, date
from django.core.files.storage import FileSystemStorage
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import connection
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
from core.models import UploadMetadata


# ---------------- HELPERS ---------------- #

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
def upload_files(request):
    energy_types = EnergyType.objects.all()
    providers = Provider.objects.all()

    # Fetch DB tables
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        db_tables = [r[0] for r in cursor.fetchall()]

    expected_tables = build_expected_upload_tables(
        db_tables,
        User.objects.all(),
        providers,
        energy_types,
    )

    if request.method == "POST":
        table_name = request.POST.get("provider", "").strip()
        provider_name = request.POST.get("provider_name", "").strip()
        data_file = request.FILES.get("data_file")

        if not table_name or not data_file or not provider_name:
            messages.error(request, "❌ Table, file, and provider are required.")
            return redirect("upload_files")

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

                df.columns = [clean_col(c) for c in df.columns]

                # ----------------- NORMALIZATION -----------------
                for col in df.columns:
                    col_l = col.lower().strip()

                    if (
                        (("start" in col_l or "end" in col_l) and "time" in col_l)
                        or col_l.endswith("_datetime")
                    ):
                        df[col] = pd.to_datetime(df[col], errors="coerce")
                        continue

                    # Date column
                    if any(k in col_l for k in ["date", "gen_date", "dt"]):
                        df[col] = df[col].apply(normalize_date)
                        df[col] = df[col].apply(lambda x: x.strftime("%Y-%m-%d") if isinstance(x, (datetime, date)) else x)
                        continue

                    # Percentage fields (PLF, Availability, Grid OK)
                    if any(k in col_l for k in ["plf", "percentage", "%", "availability", "avail", "grid_ok", "grid_okay"]):
                        df[col] = df[col].apply(normalize_percentage)
                        continue

                    # Time fields
                    if any(k in col_l for k in ["hrs", "hour", "time", "duration"]):
                        df[col] = df[col].apply(normalize_hours)
                        continue

                # Remove invalids
                df = df.replace({
                    pd.NaT: None, "": None, "nan": None, "NaN": None,
                    np.nan: None, np.inf: None, -np.inf: None
                })
                df = df.astype(object).where(pd.notnull(df), None)

                # -------- TABLE ROUTING --------
                sheet_lower = sheet_name.lower()

                if "breakdown" in sheet_lower:
                    target_table = f"{table_name}_breakdowndata"
                elif "month" in sheet_lower or "monthly" in sheet_lower:
                    target_table = f"{table_name}_monthly"
                else:
                    target_table = table_name

                if target_table not in db_tables:
                    continue

                # -------- FETCH TABLE COLUMNS --------
                with connection.cursor() as cursor:
                    cursor.execute(f"SHOW COLUMNS FROM `{target_table}`")
                    table_columns = [c[0].lower() for c in cursor.fetchall()]

                # -------- APPLY BREAKDOWN HEADER MAPPING OR STANDARD COLUMN FIX --------
                alias_map = {
                      "loaction": "location",
                      "loc": "location",
                      "location_": "location",
                      "location ": "location",
                      }
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
                        df.rename(columns=lambda c: c.lower(), inplace=True)
                else:
                    df.rename(columns=lambda c: alias_map.get(c.lower(), c.lower()), inplace=True)

                # ---------------------------------------------------------------------
                # ⭐ FIX: SOLAR MERGED COLUMN SPLIT MUST RUN BEFORE VALID COLUMN FILTER
                # ---------------------------------------------------------------------
                if "solar" in table_name.lower():
                    merge_cols = [
                        "weather_condition_breakdown_details",
                        "weather_condition__breakdown_details",
                        "breakdown_details_weather_condition",
                        "breakdown_details__weather_condition"
                    ]

                    for mc in merge_cols:
                        if mc in df.columns:
                            df["weather_condition"] = df[mc].apply(
                                lambda x: x if isinstance(x, str) and not any(ch.isdigit() for ch in x) else "Nil"
                            )
                            df["breakdown_details"] = df[mc].apply(
                                lambda x: x if isinstance(x, str) and any(ch.isdigit() for ch in x) else "Nil"
                            )
                            df.drop(columns=[mc], errors="ignore")

                # ---------------- VALID COLUMN FILTER (run AFTER split) ----------------
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

                # Metadata
                parts = table_name.split("_")
                uploaded_by = parts[0]
                energy_type = parts[-1].replace("_", " ").title()

                if "uploaded_by" in table_columns:
                    df["uploaded_by"] = uploaded_by
                if "provider" in table_columns:
                    df["provider"] = provider_name
                if "energy_type" in table_columns:
                    df["energy_type"] = energy_type
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

                # ---------------- UPSERT FOR SOLAR ----------------
                is_solar = "solar" in table_name.lower()

                final_cols = list(df.columns)
                columns = ", ".join(f"`{c}`" for c in final_cols)
                placeholders = ", ".join(["%s"] * len(final_cols))

                if is_solar:
                    update_cols = [c for c in final_cols if c not in ["date", "site", "location"]]
                    update_clause = ", ".join([f"`{c}`=VALUES(`{c}`)" for c in update_cols])

                    sql = f"""
                        INSERT INTO `{target_table}` ({columns})
                        VALUES ({placeholders})
                        ON DUPLICATE KEY UPDATE {update_clause};
                    """
                else:
                    sql = f"""
                        INSERT INTO `{target_table}` ({columns})
                        VALUES ({placeholders});
                    """

                values = [tuple(sanitize_value(v) for v in row) for row in df.values]

                with connection.cursor() as cursor:
                    cursor.executemany(sql, values)
                    inserted = cursor.rowcount

                if inserted > 0:
                    UploadMetadata.objects.update_or_create(
                        table_name=target_table,
                        defaults={"last_modified": now()},
                    )
                    uploaded_sheets.append(f"{sheet_name} → {inserted} rows")

            if uploaded_sheets:
                messages.success(request, f"✅ Uploaded Successfully: {', '.join(uploaded_sheets)}")
            else:
                messages.error(request, "❌ No valid sheets uploaded. Check structure.")

        except Exception as e:
            messages.error(request, f"❌ Upload failed: {str(e)}")
        finally:
            fs.delete(filename)

        return redirect("upload_files")

    return render(request, "upload_files.html", {
        "expected_tables": expected_tables,
        "providers": providers,
        "energy_types": energy_types,
        "staff_users": User.objects.filter(is_superuser=False),
    })


def build_expected_upload_tables(db_tables, users, providers, energy_types):
    existing_tables = {table.lower() for table in db_tables}
    expected_tables = []
    seen_table_names = set()

    for user in users:
        for provider in providers:
            for energy_type in energy_types:
                provider_slug = re.sub(
                    r"[^a-z0-9_]+",
                    "_",
                    provider.name.strip().lower().replace(" ", "_"),
                ).strip("_")
                energy_slug = re.sub(
                    r"[^a-z0-9_]+",
                    "_",
                    energy_type.name.strip().lower().replace(" ", "_"),
                ).strip("_")
                base_name = f"{user.username.lower()}_{provider_slug}_{energy_slug}"
                breakdown_name = f"{base_name}_breakdowndata"
                if not ({base_name, breakdown_name} & existing_tables):
                    continue
                if base_name in seen_table_names:
                    continue

                seen_table_names.add(base_name)
                expected_tables.append({
                    "name": base_name,
                    "label": (
                        f"{user.username} - {provider.name} - {energy_type.name}"
                    ),
                })

    return expected_tables

































































































































from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.db import connection
from django.contrib.auth.models import User
from accounts.models import EnergyType
import os, re, pandas as pd, numpy as np
from datetime import datetime, date


# -------------------- TABLE NAMES --------------------
PM_TABLE_NAME = "preventive_maintenance_data"
PM_WTG_TABLE = "preventive_maintenance_with_wtg"


# -------------------- HELPERS --------------------
def clean_col(col: str) -> str:
    return re.sub(r"\W+", "_", str(col).strip()).lower().strip("_")

def normalize_date(val):
    if val is None or str(val).strip().lower() in ["", "nan", "nat"]:
        return None
    try:
        if isinstance(val, (datetime, pd.Timestamp)):
            return val.date()
        if isinstance(val, date):
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
            h = float(parts[0]) if parts[0] else 0
            m = float(parts[1]) if len(parts) > 1 and parts[1] else 0
            sec = float(parts[2]) if len(parts) > 2 and parts[2] else 0
            return h + m/60 + sec/3600
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


# -------------------- TABLE CREATION --------------------
def _ensure_pm_table_and_columns(dynamic_cols, use_user_id=True):
    """Ensure preventive_maintenance_data exists with all necessary columns"""
    fixed_cols = ["energy_type", "checkpoints_period", "mw", "description"]
    if use_user_id:
        fixed_cols.insert(0, "user_id")
        fixed_cols.insert(1, "username")

    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        tables = [r[0] for r in cursor.fetchall()]

        if PM_TABLE_NAME not in tables:
            all_cols = []
            for c in dynamic_cols:
                all_cols.append(f"`{c}` TEXT")

            for col in fixed_cols:
                if col == "user_id":
                    all_cols.append("`user_id` INT")
                elif col == "username":
                    all_cols.append("`username` TEXT")
                else:
                    all_cols.append(f"`{col}` TEXT")

            create_sql = f"""
                CREATE TABLE `{PM_TABLE_NAME}` (
                    `id` INT AUTO_INCREMENT PRIMARY KEY,
                    {", ".join(all_cols)},
                    CONSTRAINT fk_pm_user FOREIGN KEY (`user_id`) 
                        REFERENCES `auth_user`(`id`) 
                        ON DELETE CASCADE
                );
            """
            cursor.execute(create_sql)
            return

        cursor.execute(f"SHOW COLUMNS FROM `{PM_TABLE_NAME}`;")
        existing = {r[0].lower() for r in cursor.fetchall()}

        for c in dynamic_cols:
            if c.lower() not in existing:
                cursor.execute(f"ALTER TABLE `{PM_TABLE_NAME}` ADD COLUMN `{c}` TEXT;")

        for col in fixed_cols:
            if col.lower() not in existing:
                if col == "user_id":
                    cursor.execute(f"ALTER TABLE `{PM_TABLE_NAME}` ADD COLUMN `user_id` INT;")
                    try:
                        cursor.execute(f"""
                            ALTER TABLE `{PM_TABLE_NAME}`
                            ADD CONSTRAINT fk_pm_user FOREIGN KEY (`user_id`)
                            REFERENCES `auth_user`(`id`)
                            ON DELETE CASCADE;
                        """)
                    except Exception:
                        pass
                elif col == "username":
                    cursor.execute(f"ALTER TABLE `{PM_TABLE_NAME}` ADD COLUMN `username` TEXT;")
                else:
                    cursor.execute(f"ALTER TABLE `{PM_TABLE_NAME}` ADD COLUMN `{col}` TEXT;")

def ensure_wtg_table():
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
                    completed_on DATETIME,   -- ✅ FIX
                    FOREIGN KEY (user_id) REFERENCES auth_user(id)
                        ON DELETE CASCADE
                );
            """)


        # 🧹 Drop any old constraints that might conflict
        for idx in ["unique_wtg_checkpoint", "unique_wtg_checkpoint_per_unit"]:
            try:
                cursor.execute(f"ALTER TABLE `{PM_WTG_TABLE}` DROP INDEX {idx};")
            except Exception:
                pass

        # ✅ Add final unique key per WTG + period + MW
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


# -------------------- SYNC HELPERS --------------------
def sync_new_checkpoints_to_wtgs(user):
    """Sync new checkpoints to all existing WTGs for this user"""
    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT DISTINCT wtg_no, site, state, energy_type, mw
            FROM `{PM_WTG_TABLE}` WHERE username = %s
        """, [user.username])
        wtgs = cursor.fetchall()

        if not wtgs:
            return

        cursor.execute(f"""
            SELECT energy_type, mw, checkpoints_period, category, sub_category, duration
            FROM `{PM_TABLE_NAME}` WHERE username = %s
        """, [user.username])
        checkpoints = cursor.fetchall()

        if not checkpoints:
            return

        inserted = 0
        for wtg_no, site, state, energy_type, mw in wtgs:
            for energy_type_b, mw_b, period, category, sub_category, duration in checkpoints:
                try:
                    cursor.execute(f"""
                        INSERT IGNORE INTO `{PM_WTG_TABLE}`
                        (user_id, username, wtg_no, site, state, energy_type, mw,
                         checkpoints_period, category, sub_category, duration, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Pending')
                    """, [user.id, user.username, wtg_no, site, state,
                          energy_type_b, mw_b, period, category, sub_category, duration])
                    inserted += cursor.rowcount
                except Exception:
                    continue

        print(f"✅ Synced {inserted} new checkpoints for {user.username}")


def sync_existing_checkpoints_to_new_wtg(user, wtg_no, site, state):
    """When new WTG is registered, copy all existing checkpoints for that user."""
    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT energy_type, mw, checkpoints_period, category, sub_category, duration
            FROM `{PM_TABLE_NAME}` WHERE username = %s
        """, [user.username])
        checkpoints = cursor.fetchall()

        if not checkpoints:
            print(f"⚠️ No checkpoints found for {user.username}")
            return

        inserted = 0
        for energy_type, mw, period, category, sub_category, duration in checkpoints:
            try:
                cursor.execute(f"""
                    INSERT IGNORE INTO `{PM_WTG_TABLE}`
                    (user_id, username, wtg_no, site, state, energy_type, mw,
                     checkpoints_period, category, sub_category, duration, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Pending')
                """, [user.id, user.username, wtg_no, site, state,
                      energy_type, mw, period, category, sub_category, duration])
                inserted += cursor.rowcount
            except Exception:
                continue

        print(f"✅ {inserted} checkpoints synced for new WTG '{wtg_no}'")


# -------------------- MAIN UPLOAD VIEW --------------------
@login_required
def upload_preventive_maintenance(request):
    customers = User.objects.filter(is_superuser=False).order_by("username")
    energy_types = EnergyType.objects.all().order_by("name")

    # ------------------ MANUAL ENTRY ------------------ #
    if request.method == "POST" and request.POST.get("manual_entry") == "1":
        try:
            form_user_id = int(request.POST.get("user_id"))
            user_obj = User.objects.get(id=form_user_id)
            username = user_obj.username
            energy_type_id = request.POST.get("energy_type")
            energy_type = EnergyType.objects.get(id=energy_type_id).name

            checkpoints_period = request.POST.get("checkpoints_period")
            mw = request.POST.get("mw")
            description = request.POST.get("description")

            # --- Get multiple row inputs ---
            categories = request.POST.getlist("category[]")
            sub_categories = request.POST.getlist("sub_category[]")
            durations = request.POST.getlist("duration[]")

            # --- Ensure table exists ---
            _ensure_pm_table_and_columns(["category", "sub_category", "duration"], use_user_id=True)
            ensure_wtg_table()

            sql = f"""
                INSERT INTO `{PM_TABLE_NAME}`
                (user_id, username, energy_type, category, sub_category, duration, checkpoints_period, mw, description)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            inserted = 0
            with connection.cursor() as cursor:
                for cat, sub, dur in zip(categories, sub_categories, durations):
                    if not cat.strip():
                        continue
                    cursor.execute(sql, (
                        form_user_id, username, energy_type,
                        cat.strip(), sub.strip(), dur.strip() or "0",
                        checkpoints_period, mw, description
                    ))
                    inserted += 1

            # ✅ Auto-sync newly added checkpoints to WTG table
            sync_new_checkpoints_to_wtgs(user_obj)

            messages.success(request, f"✅ Added {inserted} manual records for {username} and synced to WTGs.")
        except Exception as e:
            messages.error(request, f"❌ Manual entry failed: {e}")
        return redirect("upload_preventive_maintenance")

    # ------------------ FILE UPLOAD ------------------ #
    if request.method == "POST" and "data_file" in request.FILES:
        form_user_id = request.POST.get("user_id")
        form_energy_type_id = request.POST.get("energy_type")
        form_checkpoints = request.POST.get("checkpoints_period", "").strip()
        form_mw = request.POST.get("mw", "").strip()
        form_description = request.POST.get("description", "").strip()

        if not form_user_id or not form_energy_type_id:
            messages.error(request, "Please select both user and energy type.")
            return redirect("upload_preventive_maintenance")

        try:
            form_user_id = int(form_user_id)
            user_obj = User.objects.get(id=form_user_id)
            form_username = user_obj.username
            form_energy_type = EnergyType.objects.get(id=form_energy_type_id).name
        except Exception as e:
            messages.error(request, f"Invalid user or energy type: {e}")
            return redirect("upload_preventive_maintenance")

        fs = FileSystemStorage()
        uploaded = request.FILES["data_file"]
        fname = fs.save(uploaded.name, uploaded)
        fpath = fs.path(fname)

        try:
            ext = os.path.splitext(fname)[1].lower()
            if ext == ".csv":
                df = pd.read_csv(fpath)
            elif ext in [".xlsx", ".xlsm", ".xls"]:
                engine = "openpyxl" if ext != ".xls" else "xlrd"
                df = pd.read_excel(fpath, engine=engine, sheet_name=0)
            elif ext == ".ods":
                df = pd.read_excel(fpath, engine="odf", sheet_name=0)
            else:
                messages.error(request, f"Unsupported file type: {ext}")
                return redirect("upload_preventive_maintenance")

            if df is None or df.empty:
                messages.error(request, "Uploaded file is empty.")
                return redirect("upload_preventive_maintenance")

            df.columns = [clean_col(c) for c in df.columns]
            for col in df.columns:
                lc = col.lower()
                if any(k in lc for k in ["date", "gen_date", "dt"]):
                    df[col] = df[col].apply(normalize_date)
                    df[col] = df[col].apply(lambda x: x.strftime("%Y-%m-%d") if isinstance(x, (datetime, date)) else x)
                elif any(k in lc for k in ["hrs", "hour", "time", "duration"]):
                    df[col] = df[col].apply(normalize_hours)

            df = df.replace({pd.NaT: None, "": None, "nan": None, "NaN": None})
            df = df.astype(object).where(pd.notnull(df), None)
            df = df.replace({np.nan: None, np.inf: None, -np.inf: None})

            _ensure_pm_table_and_columns(dynamic_cols=list(df.columns), use_user_id=True)
            ensure_wtg_table()

            df["user_id"] = form_user_id
            df["username"] = form_username
            df["energy_type"] = form_energy_type
            df["checkpoints_period"] = form_checkpoints
            df["mw"] = form_mw
            df["description"] = form_description

            with connection.cursor() as cursor:
                cursor.execute(f"SHOW COLUMNS FROM `{PM_TABLE_NAME}`;")
                table_columns = [r[0] for r in cursor.fetchall()]
            valid_cols = [c for c in df.columns if c in table_columns]
            df = df[valid_cols]

            cols_sql = ", ".join(f"`{c}`" for c in df.columns)
            placeholders = ", ".join(["%s"] * len(df.columns))
            sql = f"INSERT INTO `{PM_TABLE_NAME}` ({cols_sql}) VALUES ({placeholders})"
            values = [tuple(sanitize_value(v) for v in row) for row in df.values]

            with connection.cursor() as cursor:
                cursor.executemany(sql, values)
                inserted = cursor.rowcount

            # ✅ Sync new checkpoints to WTG
            sync_new_checkpoints_to_wtgs(user_obj)

            messages.success(request, f"✅ Inserted {inserted} rows and synced to WTGs.")
        except Exception as e:
            messages.error(request, f"❌ Upload failed: {e}")
        finally:
            fs.delete(fname)

        return redirect("upload_preventive_maintenance")

    # ------------------ GET PAGE ------------------ #
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        tables = [r[0] for r in cursor.fetchall()]
    table_exists = PM_TABLE_NAME in tables

    return render(request, "upload_preventive_maintenance.html", {
        "customers": customers,
        "energy_types": energy_types,
        "pm_table_name": PM_TABLE_NAME,
        "table_exists": table_exists,
    })


def index_page(request):
  return render(request, 'index.html')


from datetime import timedelta
from django.utils.timezone import now
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.contrib.auth.models import User
from django.db.models import Count
import json
from collections import defaultdict
from accounts.models import UserProfile, EnergyType, Provider


@login_required
def dashboard(request):
    user = request.user

    if user.is_superuser:
        # --- Customer stats ---
        total_customers = UserProfile.objects.count()
        active_customers = User.objects.filter(is_active=True).count()
        inactive_customers = User.objects.filter(is_active=False).count()

        # --- Energy stats ---
        total_energy = EnergyType.objects.count()
        energy_data = (
            EnergyType.objects.annotate(total=Count("userprofile"))
            .values("name", "total")
        )
        energy_labels = [e["name"] for e in energy_data]
        energy_values = [e["total"] for e in energy_data]

        # --- Provider stats ---
        total_providers = Provider.objects.count()

        # --- User Registrations (last 6 months, grouped by username) ---
        today = now().date()
        six_months_ago = today - timedelta(days=180)
        users = User.objects.filter(date_joined__gte=six_months_ago)

        months = [
            (today - timedelta(days=i * 30)).strftime("%b %Y")
            for i in range(6, -1, -1)
        ]

        user_data = defaultdict(lambda: [0] * len(months))
        for u in users:
            month_label = u.date_joined.strftime("%b %Y")
            if month_label in months:
                idx = months.index(month_label)
                user_data[u.username][idx] += 1

        colors = [
            "#36A2EB", "#FF6384", "#4BC0C0", "#9966FF", "#FF9F40",
            "#28a745", "#e83e8c", "#20c997", "#6f42c1", "#fd7e14"
        ]
        datasets = []
        for i, (username, values) in enumerate(user_data.items()):
            datasets.append({
                "label": username,
                "data": values,
                "borderColor": colors[i % len(colors)],
                "backgroundColor": colors[i % len(colors)] + "33",
                "fill": True,
                "tension": 0.3,
                "pointRadius": 5,
                "pointHoverRadius": 8
            })

        context = {
            "total_customers": total_customers,
            "active_customers": active_customers,
            "inactive_customers": inactive_customers,
            "total_energy": total_energy,
            "energy_labels": json.dumps(energy_labels),
            "energy_values": json.dumps(energy_values),
            "total_providers": total_providers,
            "registration_labels": json.dumps(months),
            "registration_datasets": json.dumps(datasets),
        }
        return render(request, "tracking_dashboard.html", context)

    # Normal user dashboard
    return render(request, "wind_dashboard.html")


@login_required
def modify_data(request):
  return render(request,'modify_data.html')

@login_required
def manage_user(request):
   return render(request, 'manageUsers.html')

@login_required
def client_info(request):
   return render(request, 'client_info.html')
 
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.utils.text import slugify
from django.contrib.auth.models import User


 

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.contrib.auth.models import User
from accounts.models import Provider, EnergyType
 
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.contrib.auth.models import User
from accounts.models import Provider, EnergyType
from datetime import datetime


@login_required
def modify_data(request):
    users = User.objects.filter(is_superuser=False)

    # Fetch all actual tables from DB
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        db_tables = [row[0] for row in cursor.fetchall()]

    # Match pattern: username_provider_energytype
    expected_tables = []
    for table in db_tables:
        parts = table.split('_')
        if len(parts) >= 3:
            username = parts[0]
            provider_slug = '_'.join(parts[1:-1])
            energy_type_slug = parts[-1]

            if Provider.objects.filter(name__iexact=provider_slug.replace('_', ' ')).exists() and \
               EnergyType.objects.filter(name__iexact=energy_type_slug.replace('_', ' ')).exists():
                expected_tables.append({
                    'name': table,
                    'label': f"{username} - {provider_slug.replace('_', ' ').title()} - {energy_type_slug.title()}"
                })

    if request.method == "POST":
        user_id = request.POST.get("user_id")
        table_name = request.POST.get("table_name")
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")

        if not all([user_id, table_name, start_date, end_date]):
            messages.error(request, "❌ All fields are required.")
            return redirect("modify_data")

        try:
            # Validate input dates
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()

            if start_date_obj > end_date_obj:
                messages.error(request, "⚠️ Start date cannot be after End date.")
                return redirect("modify_data")

            # 🔑 Detect correct date column
            with connection.cursor() as cursor:
                cursor.execute(f"SHOW COLUMNS FROM `{table_name}`;")
                columns = [row[0].lower() for row in cursor.fetchall()]

            date_col = None
            for candidate in ["gen_date", "date", "Date"]:
                if candidate.lower() in columns:
                    date_col = candidate
                    break

            if not date_col:
                messages.error(request, "❌ No valid date column found in the selected table.")
                return redirect("modify_data")

            # Perform delete
            with connection.cursor() as cursor:
                delete_sql = f"""
                    DELETE FROM `{table_name}`
                    WHERE uploaded_by = (
                        SELECT username FROM auth_user WHERE id = %s
                    )
                    AND `{date_col}` BETWEEN %s AND %s
                """
                cursor.execute(delete_sql, [user_id, start_date, end_date])
                if cursor.rowcount == 0:
                    messages.warning(request, "⚠️ No records matched the criteria.")
                else:
                    messages.success(request, f"✅ {cursor.rowcount} record(s) deleted successfully.")

        except Exception as e:
            messages.error(request, f"❌ Error: {str(e)}")
        return redirect("modify_data")

    return render(request, "modify_data.html", {
        "users": users,
        "expected_tables": expected_tables
    })

from django.utils.text import slugify
from accounts.models import UserProfile  # already linked to User
from django.contrib.auth.models import User

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.core.files.storage import FileSystemStorage
from django.db import connection
from django.utils.text import slugify
from django.contrib.auth.models import User

import pandas as pd

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.db import connection
from django.shortcuts import render, redirect
from django.utils.text import slugify
from django.contrib.auth.models import User
from accounts.models import EnergyType  # make sure this import is correct

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.utils.text import slugify
from django.db import connection
import pandas as pd

from django.contrib.auth.models import User
from accounts.models import EnergyType


from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.utils.text import slugify
from django.db import connection
import pandas as pd
from django.contrib.auth.models import User
from accounts.models import EnergyType

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.utils.text import slugify
from django.db import connection
import pandas as pd
from accounts.models import EnergyType

@login_required
def upload_installation_summary(request):
    energy_types = EnergyType.objects.all()

    if request.method == 'POST':
        energy_type_id = request.POST.get('energy_type')
        file = request.FILES.get('file')

        if not energy_type_id or not file:
            messages.error(request, "All fields are required.")
            return redirect('upload_installation_summary')

        try:
            energy_type = EnergyType.objects.get(id=energy_type_id)
        except EnergyType.DoesNotExist:
            messages.error(request, "Invalid energy type.")
            return redirect('upload_installation_summary')

        fs = FileSystemStorage()
        filename = fs.save(file.name, file)
        file_path = fs.path(filename)

        try:
            # Read only the headers (ignore data rows)
            if filename.endswith('.csv'):
                df = pd.read_csv(file_path, nrows=0)
            else:
                df = pd.read_excel(file_path, nrows=0)

            # Normalize headers
            user_columns = [col.strip().replace(' ', '_').lower() for col in df.columns]

            # Prepend 'customer' (from request.user) and 'energy_type'
            final_columns = ['customer', 'energy_type'] + user_columns

            # Table name based on energy type
            table_name = f"installation_summary_{slugify(energy_type.name)}"

            with connection.cursor() as cursor:
                columns_sql = ", ".join([f"`{col}` TEXT" for col in final_columns])
                cursor.execute(f"CREATE TABLE IF NOT EXISTS `{table_name}` ({columns_sql})")

            messages.success(request, f"✅ Structure created successfully for table `{table_name}`.")

        except Exception as e:
            messages.error(request, f"❌ Upload failed: {str(e)}")

        finally:
            fs.delete(filename)

        return redirect('upload_installation_summary')

    return render(request, 'upload_installation_summary.html', {
        'energy_types': energy_types,
    })

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.utils.text import slugify
from django.db import connection
import pandas as pd

from django.contrib.auth.models import User
from accounts.models import EnergyType

@login_required
def upload_installation_data(request):
    customers = User.objects.filter(is_superuser=False)
    energy_types = EnergyType.objects.all()

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        energy_type_id = request.POST.get('energy_type')
        file = request.FILES.get('file')

        if not user_id or not energy_type_id or not file:
            messages.error(request, "All fields are required.")
            return redirect('upload_installation_data')

        try:
            user = User.objects.get(id=user_id)
            energy_type = EnergyType.objects.get(id=energy_type_id)
        except (User.DoesNotExist, EnergyType.DoesNotExist):
            messages.error(request, "Invalid user or energy type.")
            return redirect('upload_installation_data')

        fs = FileSystemStorage()
        filename = fs.save(file.name, file)
        file_path = fs.path(filename)

        try:
            # ==========================
            #  READ FILE
            # ==========================
            if filename.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)

            # Add metadata
            df['uploaded_by'] = request.user.username
            df['customer'] = user.username
            df['energy_type'] = energy_type.name

            # Clean column names
            df.columns = [col.strip().replace(' ', '_').lower() for col in df.columns]

            # ==========================
            #  FIX EMPTY CELLS COMPLETELY
            # ==========================
            df = df.replace({np.nan: None, pd.NaT: None})
            df = df.where(pd.notnull(df), None)
            df = df.astype(object)

            # Table name
            table_name = f"installation_summary_{slugify(energy_type.name)}"

            # Get DB columns
            with connection.cursor() as cursor:
                cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
                db_columns = [row[0] for row in cursor.fetchall()]

            # Validate columns
            missing_cols = set(db_columns) - set(df.columns)
            if missing_cols:
                messages.error(request, f"Uploaded file is missing columns: {', '.join(missing_cols)}")
                return redirect('upload_installation_data')

            # Match DB column order
            df = df[db_columns]

            # ==========================
            #  INSERT INTO MYSQL
            # ==========================
            with connection.cursor() as cursor:
                for _, row in df.iterrows():
                    data = [None if (x is np.nan or x == '' or x is pd.NaT) else x for x in row.values]

                    columns = ", ".join(f"`{c}`" for c in db_columns)
                    placeholders = ", ".join(["%s"] * len(data))

                    cursor.execute(
                        f"INSERT INTO `{table_name}` ({columns}) VALUES ({placeholders})",
                        data
                    )

            messages.success(request, f"✅ Data uploaded successfully into `{table_name}`.")

        except Exception as e:
            messages.error(request, f"❌ Upload failed: {str(e)}")

        finally:
            fs.delete(filename)

        return redirect('upload_installation_data')

    return render(request, 'upload_installation_data.html', {
        'customers': customers,
        'energy_types': energy_types,
    })


from django.db import connection
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from accounts.models import EnergyType, User  # Adjust imports to match your project

@login_required
@csrf_exempt
def manage_installation_data(request):
    customers = User.objects.filter(is_superuser=False)
    energy_types = EnergyType.objects.all()
    installation_entries = []

    if request.method == 'POST' and 'delete_entry' in request.POST:
        user_id = request.POST.get('user_id')
        energy_type_id = request.POST.get('energy_type_id')

        try:
            user = User.objects.get(id=user_id)
            energy_type = EnergyType.objects.get(id=energy_type_id)
            table_name = f"installation_summary_{slugify(energy_type.name)}"

            with connection.cursor() as cursor:
                cursor.execute(f"DELETE FROM `{table_name}` WHERE customer = %s", [user.username])
            messages.success(request, f"✅ Installation data for '{user.username}' deleted.")
        except Exception as e:
            messages.error(request, f"⚠️ Failed to delete installation: {str(e)}")

        return redirect('manage_installation_data')

    # List all installations grouped by customer and energy type
    for e_type in energy_types:
        table_name = f"installation_summary_{slugify(e_type.name)}"
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT DISTINCT customer FROM `{table_name}`"
                )
                rows = cursor.fetchall()
                for row in rows:
                    customer_username = row[0]
                    user = User.objects.filter(username=customer_username).first()
                    if user:
                        installation_entries.append({
                            'user': user,
                            'energy_type': e_type,
                        })
        except Exception:
            continue  # skip tables that don't exist or are invalid

    return render(request, 'manage_installation_data.html', {
        'installation_entries': installation_entries,
    })

 

from django.http import HttpResponse
from django.utils.text import slugify
from django.db import connection
import pandas as pd
import io
from accounts.models import EnergyType
from django.contrib.auth.decorators import login_required

@login_required
def download_template(request):
    energy_type_id = request.GET.get('energy_type')

    if not energy_type_id:
        return HttpResponse("❌ Energy Type is required in query params.", status=400)

    try:
        energy_type = EnergyType.objects.get(id=energy_type_id)
    except EnergyType.DoesNotExist:
        return HttpResponse("❌ Invalid Energy Type.", status=400)

    table_name = f"installation_summary_{slugify(energy_type.name)}"

    try:
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
            columns = [row[0] for row in cursor.fetchall()]
    except Exception as e:
        return HttpResponse(f"❌ Table `{table_name}` not found or invalid: {str(e)}", status=500)

    exclude_columns = {'customer', 'energy_type'}
    user_columns = [col for col in columns if col not in exclude_columns]

    if not user_columns:
        return HttpResponse("❌ No user-uploaded columns found in this table.", status=500)

    df = pd.DataFrame(columns=user_columns)

    buffer = io.BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)

    response = HttpResponse(
        buffer,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{table_name}_template.xlsx"'
    return response


import os
import re
import traceback
import pandas as pd
import numpy as np

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























 
from django.db import connection, DatabaseError

from django.db import connection, DatabaseError
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from accounts.models import Provider, EnergyType
import re

from django.db import connection, DatabaseError
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
 
from .models import UploadMetadata  # ✅ import this
from django.db.utils import DatabaseError
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.shortcuts import render

from django.shortcuts import render
from django.db import connection, DatabaseError
from django.contrib.auth.decorators import login_required
 
from django.core.paginator import Paginator
from django.db import connection, DatabaseError
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from accounts.models import Provider, EnergyType
from core.models import UploadMetadata

from django.shortcuts import render
from django.db import connection, DatabaseError
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
 

from django.utils.dateparse import parse_date

@login_required
def client_info(request):
    client_data = []

    client_filter = request.GET.get('client', '').lower()
    oem_filter = request.GET.get('oem', '').lower()
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')

    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        all_tables = [row[0] for row in cursor.fetchall()]

    oem_names_set = set()

    for table in all_tables:
        parts = table.split('_')
        if len(parts) >= 3:
            username = parts[0]
            provider_slug = '_'.join(parts[1:-1])
            energy_type_slug = parts[-1]

            provider_name = provider_slug.replace('_', ' ').title()
            energy_type_name = energy_type_slug.replace('_', ' ').title()
            oem_names_set.add(provider_name)

            provider_exists = Provider.objects.filter(name__iexact=provider_name).exists()
            energy_exists = EnergyType.objects.filter(name__iexact=energy_type_name).exists()

            if provider_exists and energy_exists:
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(f"SHOW COLUMNS FROM `{table}`")
                        available_cols = [row[0] for row in cursor.fetchall()]

                    uploaded_by = 'uploaded_by' if 'uploaded_by' in available_cols else None

                    row_uploaded_by = None
                    if uploaded_by:
                        with connection.cursor() as cursor:
                            cursor.execute(f"SELECT `{uploaded_by}` FROM `{table}` LIMIT 1")
                            result = cursor.fetchone()
                            if result:
                                row_uploaded_by = result[0]

                    try:
                        metadata = UploadMetadata.objects.get(table_name=table)
                        last_modified = metadata.last_modified.strftime('%Y-%m-%d')
                    except UploadMetadata.DoesNotExist:
                        last_modified = None

                    client_name = f"{row_uploaded_by}_{energy_type_name}" if row_uploaded_by else "N/A"

                    # Apply filters
                    if client_filter and client_filter not in client_name.lower():
                        continue
                    if oem_filter and oem_filter not in provider_name.lower():
                        continue
                    if from_date and last_modified and last_modified < from_date:
                        continue
                    if to_date and last_modified and last_modified > to_date:
                        continue

                    client_data.append({
                        "client": client_name,
                        "oem": provider_name,
                        "generation": "N/A",
                        "breakdown": "N/A",
                        "last_modified": last_modified or "N/A",
                    })

                except DatabaseError as e:
                    print(f"⚠️ Skipping table `{table}` due to error: {e}")
                    continue

    # Sort data (optional)
    client_data.sort(key=lambda x: x['client'])

    paginator = Paginator(client_data, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'client_info.html', {
        'page_obj': page_obj,
        'unique_oems': sorted(oem_names_set)
    })


from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from core.models import UploadMetadata
from accounts.models import Provider
from django.db import connection

@login_required
def user_generation_info(request):
    user = request.user.username.lower()
  # logged-in user
    client_data = []

    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        all_tables = [row[0] for row in cursor.fetchall()]

    for table in all_tables:
        if table.startswith(f"{user}_"):  # ✅ only take current user's tables
            parts = table.split("_")
            if len(parts) >= 3:
                provider_slug = "_".join(parts[1:-1])
                energy_type_slug = parts[-1]

                provider_name = provider_slug.replace("_", " ").title()
                firm_name = user.replace("_", " ").title()

                try:
                    metadata = UploadMetadata.objects.get(table_name=table)
                    last_modified = metadata.last_modified.strftime('%a, %d %b %Y %H:%M:%S GMT')
                except UploadMetadata.DoesNotExist:
                    last_modified = "N/A"

                client_data.append({
                    "provider": provider_name,
                    "firm": firm_name,
                    "last_modified": last_modified
                })

    return render(request, "profile_info_user.html", {
        "client_data": client_data
    })


# ------------------------------------------------------------
# tracking_dashboard view (Fixed timedelta issue + clean logic)
# ------------------------------------------------------------

from datetime import datetime, timedelta   # ✅ Correct import
from collections import Counter, defaultdict
from calendar import month_abbr

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.contrib.auth.models import User
from django.utils.timezone import now

from accounts.models import UserProfile, EnergyType, Provider  # ✅ ensure these exist
import json

# ------------------------------------------------------------
# tracking_dashboard view (final fixed version)
# ------------------------------------------------------------

from datetime import datetime, timedelta
from collections import Counter, defaultdict
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.contrib.auth.models import User
from django.utils.timezone import now
from accounts.models import UserProfile, EnergyType, Provider
import json

# ------------------------------------------------------------
# tracking_dashboard view (Final version for your current models)
# ------------------------------------------------------------

from datetime import datetime, timedelta
from collections import defaultdict
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.contrib.auth.models import User
from django.utils.timezone import now
from accounts.models import UserProfile, EnergyType, Provider
import json

from datetime import timedelta
from collections import defaultdict
from django.utils.timezone import now
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.contrib.auth.models import User
from accounts.models import UserProfile, EnergyType, Provider
import json


from datetime import timedelta
from django.utils.timezone import now
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.contrib.auth.models import User
from accounts.models import UserProfile, EnergyType, Provider
import json


from datetime import timedelta
from django.utils.timezone import now
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.contrib.auth.models import User
from accounts.models import UserProfile, EnergyType, Provider
from django.db.models import Count
import json
from datetime import timedelta
from django.utils.timezone import now
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.contrib.auth.models import User
from accounts.models import UserProfile, EnergyType, Provider
from django.db.models import Count
import json
from django.utils.timezone import now
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.contrib.auth.models import User
from accounts.models import UserProfile, EnergyType, Provider
import json


@staff_member_required
def tracking_dashboard(request):
    """Admin dashboard showing customers, providers, and energy statistics."""
    today = now().date()
    start_date = today - timedelta(days=180)

    # --- Total counts ---
    total_customers = User.objects.filter(is_staff=False, is_superuser=False).count()
    total_providers = Provider.objects.count()
    total_energy = EnergyType.objects.count()

    # --- Active / Inactive customers ---
    # Since your UserProfile doesn’t have 'is_active', use User model
    active_customers = User.objects.filter(is_active=True, is_staff=False, is_superuser=False).count()
    inactive_customers = total_customers - active_customers if total_customers > 0 else 0

    # --- Energy distribution (Donut chart) ---
    energy_labels = []
    energy_values = []

    for et in EnergyType.objects.all():
        # Count how many UserProfiles are linked to this energy type
        count = UserProfile.objects.filter(energy_types=et).count()
        if count > 0:
            energy_labels.append(et.name)
            energy_values.append(count)

    # Handle no data case
    if not energy_labels:
        energy_labels = ["No Data"]
        energy_values = [1]

    context = {
        "total_customers": total_customers,
        "active_customers": active_customers,
        "inactive_customers": inactive_customers,
        "total_providers": total_providers,
        "total_energy": total_energy,
        "energy_labels": json.dumps(energy_labels),
        "energy_values": json.dumps(energy_values),
    }

    return render(request, "tracking_dashboard.html", context)





    from django.core.paginator import Paginator





from django.db.models import Q

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import connection
from datetime import datetime, date
import re

# Make sure PM_TABLE_NAME is defined somewhere globally like earlier:
PM_TABLE_NAME = "preventive_maintenance_data"


@login_required
def manage_preventive_maintenance(request):
    """
    Manage Preventive Maintenance:
    - Bulk delete by filters (preview -> confirm)
    - Manual edit/delete of single rows (table + modals)
    - Search + pagination
    """

    # --- helpers for building SQL ---
    def build_where_and_params(filters):
        where = " WHERE 1=1 "
        params = []
        if filters.get("username"):
            where += " AND username = %s "
            params.append(filters["username"])
        if filters.get("energy_type"):
            where += " AND energy_type = %s "
            params.append(filters["energy_type"])
        if filters.get("checkpoints_period"):
            where += " AND checkpoints_period = %s "
            params.append(filters["checkpoints_period"])
        if filters.get("mw"):
            # match exact or numeric; treat as string compare
            where += " AND mw = %s "
            params.append(filters["mw"])
        return where, params

    # --- get dropdown options (users, energy types, checkpoint periods) ---
    from django.contrib.auth import get_user_model
    User = get_user_model()
    staff_users = User.objects.filter(is_superuser=False).order_by("username")
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT DISTINCT energy_type FROM `{PM_TABLE_NAME}`")
        energy_types = [r[0] for r in cursor.fetchall()]
        cursor.execute(f"SELECT DISTINCT checkpoints_period FROM `{PM_TABLE_NAME}`")
        checkpoints_periods = [r[0] for r in cursor.fetchall()]

    # --- handle POST actions ---
    # 1) Single-row delete (manual)
    if request.method == "POST" and request.POST.get("delete_id"):
        delete_id = request.POST.get("delete_id")
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"DELETE FROM `{PM_TABLE_NAME}` WHERE id = %s", [delete_id])
                deleted = cursor.rowcount
            messages.success(request, f"✅ Record ID {delete_id} deleted successfully ({deleted} row(s)).")
        except Exception as e:
            messages.error(request, f"❌ Failed to delete record: {e}")
        return redirect("manage_preventive_maintenance")

    # 2) Single-row edit
    if request.method == "POST" and request.POST.get("edit_id"):
        edit_id = request.POST.get("edit_id")
        new_category = request.POST.get("edit_category", "").strip()
        new_sub_category = request.POST.get("edit_sub_category", "").strip()
        new_duration = request.POST.get("edit_duration", "").strip()
        new_description = request.POST.get("edit_description", "").strip()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""UPDATE `{PM_TABLE_NAME}`
                        SET category=%s, sub_category=%s, duration=%s, description=%s
                        WHERE id=%s""",
                    [new_category, new_sub_category, new_duration, new_description, edit_id]
                )
            messages.success(request, f"✅ Record ID {edit_id} updated successfully.")
        except Exception as e:
            messages.error(request, f"❌ Failed to update record: {e}")
        return redirect("manage_preventive_maintenance")

    # 3) Bulk preview (user clicked "Preview Delete")
    preview_count = None
    preview_filters = {}
    if request.method == "POST" and request.POST.get("preview_bulk"):
        # read filters from POST
        username = request.POST.get("bulk_username") or None
        energy_type = request.POST.get("bulk_energy_type") or None
        checkpoints_period = request.POST.get("bulk_checkpoints_period") or None
        mw = request.POST.get("bulk_mw") or None

        preview_filters = {
            "username": username,
            "energy_type": energy_type,
            "checkpoints_period": checkpoints_period,
            "mw": mw
        }
        where_clause, params = build_where_and_params(preview_filters)
        try:
            with connection.cursor() as cursor:
                sql = f"SELECT COUNT(*) FROM `{PM_TABLE_NAME}` {where_clause}"
                cursor.execute(sql, params)
                preview_count = cursor.fetchone()[0]
        except Exception as e:
            messages.error(request, f"❌ Preview failed: {e}")
            preview_count = None
        # render page with preview_count (modal will auto-open via template JS)
    # 4) Confirm bulk delete (user confirmed in modal)
    if request.method == "POST" and request.POST.get("confirm_bulk_delete"):
        username = request.POST.get("bulk_username_confirm") or None
        energy_type = request.POST.get("bulk_energy_type_confirm") or None
        checkpoints_period = request.POST.get("bulk_checkpoints_period_confirm") or None
        mw = request.POST.get("bulk_mw_confirm") or None

        filters = {
            "username": username,
            "energy_type": energy_type,
            "checkpoints_period": checkpoints_period,
            "mw": mw
        }
        where_clause, params = build_where_and_params(filters)
        try:
            with connection.cursor() as cursor:
                sql = f"DELETE FROM `{PM_TABLE_NAME}` {where_clause}"
                cursor.execute(sql, params)
                deleted = cursor.rowcount
            messages.success(request, f"🗑️ Bulk delete completed: {deleted} row(s) removed.")
        except Exception as e:
            messages.error(request, f"❌ Bulk delete failed: {e}")
        return redirect("manage_preventive_maintenance")

    # --- GET: show records (search + pagination) ---
    search = request.GET.get("search", "").strip()
    # fetch rows (we'll use fixed columns for PM)
    with connection.cursor() as cursor:
        sql = f"""
            SELECT id, user_id, username, energy_type, category, sub_category,
                   duration, checkpoints_period, mw, description
            FROM `{PM_TABLE_NAME}`
        """
        params = []
        if search:
            sql += " WHERE username LIKE %s OR category LIKE %s OR sub_category LIKE %s OR energy_type LIKE %s "
            sparam = f"%{search}%"
            params.extend([sparam, sparam, sparam, sparam])
        sql += " ORDER BY id DESC"
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        cols = [c[0] for c in cursor.description]

    data = [dict(zip(cols, r)) for r in rows]

    # pagination
    paginator = Paginator(data, 10)
    page = request.GET.get("page")
    records = paginator.get_page(page)

    # render template; include preview_count and preview_filters if any
    return render(request, "manage_preventive_maintenance.html", {
        "records": records,
        "search": search,
        "staff_users": staff_users,
        "energy_types": energy_types,
        "checkpoints_periods": checkpoints_periods,
        "preview_count": preview_count,
        "preview_filters": preview_filters,
    })


@login_required
def upload_dsm_data(request):

    DSM_TABLE_NAME = "dsm_data"

    # ---- Check DSM table exists ----
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        tables = [r[0] for r in cursor.fetchall()]
        table_exists = DSM_TABLE_NAME in tables

    if not table_exists:
        messages.error(request, "DSM table does not exist. Please create structure first.")
        return redirect("add_dsm_structure")

    if request.method == "POST" and "data_file" in request.FILES:

        provider = request.POST.get("provider")
        energy_type = request.POST.get("energy_type")
        uploaded_by = request.POST.get("uploaded_by")

        data_file = request.FILES["data_file"]

        if not provider or not energy_type or not uploaded_by:
            messages.error(request, "Please select provider, energy type, and uploaded by user.")
            return redirect("upload_dsm_data")

        # ---- Save temp file ----
        fs = FileSystemStorage()
        filename = fs.save(data_file.name, data_file)
        file_path = fs.path(filename)

        try:
            ext = os.path.splitext(filename)[1].lower()

            # ---- Read file based on extension ----
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
                messages.error(request, f"Unsupported file type: {ext}")
                return redirect("upload_dsm_data")

            if df.empty:
                messages.error(request, "Uploaded file contains no data.")
                return redirect("upload_dsm_data")

            # ---- Clean column names ----
            cleaned_cols = []
            seen = {}

            for col in df.columns:
                new_col = re.sub(r"\W+", "_", str(col).lower()).strip("_") or "col"
                if new_col in seen:
                    seen[new_col] += 1
                    new_col = f"{new_col}_{seen[new_col]}"
                else:
                    seen[new_col] = 0
                cleaned_cols.append(new_col)

            df.columns = cleaned_cols

            # ---- Add system columns ----
            df["username"] = uploaded_by
            df["provider"] = provider
            df["energy_type"] = energy_type
             

            # ---------------------------------------------------------
            # 🔥 FIX: Remove ALL NaN, NaT, NULL-like values
            # ---------------------------------------------------------
            df = df.replace({float("nan"): None})
            df = df.replace({pd.NA: None})
            df = df.replace({pd.NaT: None})
            df = df.astype(object).where(pd.notnull(df), None)

            # ---- Insert data ----
            cols = ", ".join([f"`{c}`" for c in df.columns])

            with connection.cursor() as cursor:
                for _, row in df.iterrows():
                    values = list(row.values)
                    placeholders = ", ".join(["%s"] * len(values))
                    sql = f"INSERT INTO `{DSM_TABLE_NAME}` ({cols}) VALUES ({placeholders})"
                    cursor.execute(sql, values)

            messages.success(request, f"✅ {len(df)} rows uploaded successfully!")

        except Exception as e:
            messages.error(request, f"❌ Upload failed: {e}")

        finally:
            fs.delete(filename)

        return redirect("upload_dsm_data")

    # ---- Dropdown lists ----
    providers = Provider.objects.all()
    energy_types = EnergyType.objects.all()
    staff_users = User.objects.filter(is_superuser=False)

    return render(request, "upload_dsm_data.html", {
        "providers": providers,
        "energy_types": energy_types,
        "staff_users": staff_users,
        "table_exists": table_exists,
    })












@login_required
def delete_dsm_data(request):

    DSM_TABLE_NAME = "dsm_data"

    # ---- Check if table exists ----
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        tables = [row[0] for row in cursor.fetchall()]
        table_exists = DSM_TABLE_NAME in tables

    if not table_exists:
        messages.error(request, "DSM table does not exist. Create structure first.")
        return redirect("add_dsm_structure")

    # ---- Dropdown values ----
    staff_users = User.objects.filter(is_superuser=False)
    energy_types = EnergyType.objects.all()
    providers = Provider.objects.all()

    if request.method == "POST":

        selected_user = request.POST.get("username")
        selected_energy = request.POST.get("energy_type")
        selected_provider = request.POST.get("provider")

        if not selected_user or not selected_energy:
            messages.error(request, "Please select user and energy type.")
            return redirect("delete_dsm_data")

        # ------- Build DELETE Query -------
        query = f"DELETE FROM `{DSM_TABLE_NAME}` WHERE 1=1 "
        params = []

        query += " AND username = %s "
        params.append(selected_user)

        query += " AND energy_type = %s "
        params.append(selected_energy)

        if selected_provider:
            query += " AND provider = %s "
            params.append(selected_provider)

        try:
            with connection.cursor() as cursor:
                cursor.execute(query, params)

            messages.success(request, f"🗑️ All DSM records deleted for: "
                                      f"{selected_user} → {selected_energy}"
                                      + (f" → {selected_provider}" if selected_provider else ""))

        except Exception as e:
            messages.error(request, f"❌ Delete failed: {e}")

        return redirect("delete_dsm_data")

    return render(request, "manage_dsm_data.html", {
        "staff_users": staff_users,
        "energy_types": energy_types,
        "providers": providers,
        "table_exists": table_exists,
    })
