from bisect import bisect_left
from datetime import timedelta
from math import isfinite
import re

import pandas as pd


RISK_TIERS = (
    "CRITICAL_RECURRENCE",
    "HIGH_RECURRENCE_RISK",
    "MODERATE_RECURRENCE",
    "NORMAL",
)
_RISK_TIER_PRIORITY = {
    risk_tier: priority
    for priority, risk_tier in enumerate(reversed(RISK_TIERS))
}


def natural_sort_key(value):
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part.casefold())
        for part in re.split(r"(\d+)", str(value))
    )


def filter_recurrence_events(events, selected_filters):
    filtered = events
    for field, selected_value in selected_filters.items():
        if not selected_value:
            continue
        if selected_value == "__missing__":
            if field not in filtered.columns:
                continue
            missing = filtered[field].isna() | (
                filtered[field].astype(str).str.strip() == ""
            )
            filtered = filtered[missing]
            continue
        if field not in filtered.columns:
            filtered = filtered.iloc[0:0]
            continue
        filtered = filtered[
            filtered[field].astype(str).str.strip() == selected_value
        ]
    return filtered


def summarize_wtg_risk(events):
    """Assign each WTG its highest event risk tier and summarize risky events."""
    tier_counts = {risk_tier: 0 for risk_tier in RISK_TIERS}
    risky_event_counts = {}
    highest_tier_by_wtg = {}
    wtg_labels = {}

    for _, row in events.iterrows():
        asset = row.get("loc_no")
        risk_tier = row.get("risk_tier")
        if asset is None or pd.isna(asset) or risk_tier not in _RISK_TIER_PRIORITY:
            continue
        machine = str(asset)
        machine_key = machine.strip().casefold()
        if not machine_key:
            continue
        wtg_labels.setdefault(machine_key, machine.strip())
        current_tier = highest_tier_by_wtg.get(machine_key)
        if (
            current_tier is None
            or _RISK_TIER_PRIORITY[risk_tier] > _RISK_TIER_PRIORITY[current_tier]
        ):
            highest_tier_by_wtg[machine_key] = risk_tier
        if risk_tier != "NORMAL":
            risky_event_counts[machine_key] = risky_event_counts.get(machine_key, 0) + 1

    for risk_tier in highest_tier_by_wtg.values():
        tier_counts[risk_tier] += 1

    top_wtgs = sorted(
        (
            (wtg_labels[machine_key], count)
            for machine_key, count in risky_event_counts.items()
        ),
        key=lambda item: (-item[1], natural_sort_key(item[0])),
    )[:10]
    return tier_counts, top_wtgs


def summarize_risk_groups(events, group_by):
    """Count distinct WTGs by their highest tier within each selected group."""
    grouped_wtg_tiers = {}
    group_labels = {}
    for _, row in events.iterrows():
        asset = row.get("loc_no")
        risk_tier = row.get("risk_tier")
        if asset is None or pd.isna(asset) or risk_tier not in _RISK_TIER_PRIORITY:
            continue

        group_value = row.get(group_by)
        if group_value is None or pd.isna(group_value) or not str(group_value).strip():
            group_label = "Unknown"
        else:
            group_label = str(group_value).strip()
        machine = str(asset).strip()
        if not machine:
            continue
        group_key = group_label.casefold()
        machine_key = machine.casefold()
        group_labels.setdefault(group_key, group_label)

        key = (group_key, machine_key)
        current_tier = grouped_wtg_tiers.get(key)
        if (
            current_tier is None
            or _RISK_TIER_PRIORITY[risk_tier] > _RISK_TIER_PRIORITY[current_tier]
        ):
            grouped_wtg_tiers[key] = risk_tier

    grouped_counts = {}
    for (group_key, _), risk_tier in grouped_wtg_tiers.items():
        if group_key not in grouped_counts:
            grouped_counts[group_key] = {tier: 0 for tier in RISK_TIERS}
        grouped_counts[group_key][risk_tier] += 1

    return [
        {
            "label": group_labels[group_key],
            "total": sum(tier_counts.values()),
            **tier_counts,
        }
        for group_key, tier_counts in sorted(
            grouped_counts.items(),
            key=lambda item: natural_sort_key(group_labels[item[0]]),
        )
    ]


def summarize_recurrence_details(events, reference_date):
    """Build WTG, subsystem, and rolling-window recurrence dashboard summaries."""
    turbine_data = {}
    subsystem_tier_by_turbine = {}
    subsystem_labels = {}
    profile_wtgs = {
        "2+ failures / 30 days": set(),
        "3+ failures / 90 days": set(),
        "4+ failures / 365 days": set(),
        "TBF <= 7 days": set(),
    }

    def text_value(value, fallback):
        if value is None or pd.isna(value) or not str(value).strip():
            return fallback
        return str(value).strip()

    def count_value(value):
        numeric = pd.to_numeric(value, errors="coerce")
        return int(numeric) if pd.notna(numeric) else 0

    for _, row in events.iterrows():
        asset = row.get("loc_no")
        risk_tier = row.get("risk_tier")
        event_start = row.get("event_start")
        if asset is None or pd.isna(asset) or risk_tier not in _RISK_TIER_PRIORITY:
            continue
        machine = str(asset).strip()
        if not machine:
            continue

        site = text_value(row.get("site"), "Unknown")
        key = (site.casefold(), machine.casefold())
        turbine = turbine_data.setdefault(key, {
            "wtg": machine,
            "site": site,
            "risk_tier": "NORMAL",
            "breakdowns_90d": 0,
            "components": {},
        })
        if (
            _RISK_TIER_PRIORITY[risk_tier]
            > _RISK_TIER_PRIORITY[turbine["risk_tier"]]
        ):
            turbine["risk_tier"] = risk_tier

        if (
            reference_date is not None
            and not pd.isna(reference_date)
            and not pd.isna(event_start)
            and event_start >= reference_date - timedelta(days=90)
        ):
            turbine["breakdowns_90d"] += 1

        subsystem = text_value(
            row.get("subsystem_name"),
            text_value(row.get("system_name"), "Unknown"),
        )
        component = text_value(
            row.get("standard_component"),
            text_value(row.get("rds_code"), subsystem),
        )

        subsystem_key = subsystem.casefold()
        subsystem_labels.setdefault(subsystem_key, subsystem)
        subsystem_turbine_key = (subsystem_key, key)
        current_subsystem_tier = subsystem_tier_by_turbine.get(subsystem_turbine_key)
        if current_subsystem_tier is None or (
            _RISK_TIER_PRIORITY[risk_tier]
            > _RISK_TIER_PRIORITY[current_subsystem_tier]
        ):
            subsystem_tier_by_turbine[subsystem_turbine_key] = risk_tier

        if risk_tier != "NORMAL":
            component_key = component.casefold()
            candidate = turbine["components"].setdefault(component_key, {
                "name": component,
                "risk_tier": risk_tier,
                "event_count": 0,
            })
            candidate["event_count"] += 1
            if (
                _RISK_TIER_PRIORITY[risk_tier]
                > _RISK_TIER_PRIORITY[candidate["risk_tier"]]
            ):
                candidate["risk_tier"] = risk_tier

            if count_value(row.get("failures_last_30d")) >= 2:
                profile_wtgs["2+ failures / 30 days"].add(key)
            if count_value(row.get("failures_last_90d")) >= 3:
                profile_wtgs["3+ failures / 90 days"].add(key)
            if count_value(row.get("failures_last_365d")) >= 4:
                profile_wtgs["4+ failures / 365 days"].add(key)
            tbf_days = row.get("tbf_days")
            if not pd.isna(tbf_days) and float(tbf_days) <= 7:
                profile_wtgs["TBF <= 7 days"].add(key)

    top_wtgs = []
    for turbine in turbine_data.values():
        if turbine["risk_tier"] == "NORMAL":
            continue
        components = sorted(
            turbine["components"].values(),
            key=lambda component: (
                -_RISK_TIER_PRIORITY[component["risk_tier"]],
                -component["event_count"],
                natural_sort_key(component["name"]),
            ),
        )
        top_wtgs.append({
            "wtg": turbine["wtg"],
            "site": turbine["site"],
            "breakdowns_90d": turbine["breakdowns_90d"],
            "risk_tier": turbine["risk_tier"],
            "component": components[0]["name"] if components else "Unclassified",
        })
    top_wtgs.sort(
        key=lambda turbine: (
            -_RISK_TIER_PRIORITY[turbine["risk_tier"]],
            -turbine["breakdowns_90d"],
            natural_sort_key(turbine["site"]),
            natural_sort_key(turbine["wtg"]),
        )
    )
    top_wtgs = top_wtgs[:15]

    subsystem_counts = {}
    for (subsystem_key, _), risk_tier in subsystem_tier_by_turbine.items():
        if risk_tier == "NORMAL":
            continue
        subsystem = subsystem_counts.setdefault(subsystem_key, {
            "CRITICAL_RECURRENCE": 0,
            "HIGH_RECURRENCE_RISK": 0,
            "MODERATE_RECURRENCE": 0,
        })
        subsystem[risk_tier] += 1
    subsystem_data = [
        {
            **counts,
            "label": subsystem_labels[key],
            "total": sum(counts.values()),
        }
        for key, counts in sorted(
            subsystem_counts.items(),
            key=lambda item: (
                -sum(item[1].values()),
                natural_sort_key(subsystem_labels[item[0]]),
            ),
        )[:10]
    ]

    profile_data = [
        {"label": label, "count": len(wtgs)}
        for label, wtgs in profile_wtgs.items()
    ]
    return top_wtgs, subsystem_data, profile_data


def _to_datetime(value):
    if value is None or pd.isna(value):
        return None
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(parsed):
        return None
    return parsed.to_pydatetime()


def _to_hours(value):
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed) or not isfinite(float(parsed)) or float(parsed) < 0:
        return None
    return float(parsed)


def _component_code(value):
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def analyze_recurrence_risk(events):
    """Enrich breakdown events with chronological recurrence metrics and risk tiers."""
    result = events.copy()
    metric_names = (
        "event_start",
        "event_end",
        "previous_start",
        "previous_end",
        "previous_remark",
        "tbf_days",
        "cumulative_failure_count",
        "failures_last_30d",
        "failures_last_90d",
        "failures_last_365d",
        "mtbf_days",
        "risk_tier",
    )
    for metric in metric_names:
        result[metric] = None

    start_times = []
    end_times = []
    for _, row in result.iterrows():
        start = _to_datetime(row.get("start_time"))
        if start is None:
            start = _to_datetime(row.get("gen_date"))
        end = _to_datetime(row.get("end_time"))
        if end is None and start is not None:
            duration = _to_hours(row.get("duration_hours", row.get("duration_hrs")))
            if duration is not None:
                end = start + timedelta(hours=duration)
        start_times.append(start)
        end_times.append(end)

    component_groups = {}
    for position, (_, row) in enumerate(result.iterrows()):
        start = start_times[position]
        if start is None:
            result.iloc[position, result.columns.get_loc("risk_tier")] = "NORMAL"
            continue

        site = row.get("site")
        asset = row.get("loc_no")
        code = _component_code(row.get("rds_code"))
        site_key = "" if site is None or pd.isna(site) else str(site).strip().casefold()
        asset_key = "" if asset is None or pd.isna(asset) else str(asset).strip().casefold()
        code_key = code.casefold()
        if not asset_key or not code_key:
            result.iloc[position, result.columns.get_loc("risk_tier")] = "NORMAL"
            continue

        component_groups.setdefault((site_key, asset_key, code_key), []).append(position)

    for positions in component_groups.values():
        positions.sort(key=lambda position: (start_times[position], position))
        ordered_starts = [start_times[position] for position in positions]
        mean_tbf_values = []

        for offset, position in enumerate(positions):
            row = result.iloc[position]
            code_key = _component_code(row.get("rds_code")).casefold()
            start = start_times[position]
            end = end_times[position]
            previous_position = positions[offset - 1] if offset else None
            previous_end = end_times[previous_position] if previous_position is not None else None
            previous_start = (
                start_times[previous_position] if previous_position is not None else None
            )
            previous_remark = (
                result.iloc[previous_position].get("breakdown_remarks")
                if previous_position is not None
                else None
            )
            tbf_days = (
                (start - previous_end).total_seconds() / 86400
                if previous_end is not None
                else None
            )
            if tbf_days is not None and tbf_days >= 0:
                mean_tbf_values.append(tbf_days)

            failure_counts = {}
            for window_days in (30, 90, 365):
                first_in_window = bisect_left(
                    ordered_starts,
                    start - timedelta(days=window_days),
                    0,
                    offset + 1,
                )
                failure_counts[window_days] = offset + 1 - first_in_window

            if (
                code_key in {"uncategorized", "uncategorised", "unknown", "unmapped"}
            ):
                risk_tier = "NORMAL"
            elif failure_counts[90] >= 3:
                risk_tier = "CRITICAL_RECURRENCE"
            elif failure_counts[30] >= 2 or (tbf_days is not None and tbf_days <= 7):
                risk_tier = "HIGH_RECURRENCE_RISK"
            elif failure_counts[365] >= 4:
                risk_tier = "MODERATE_RECURRENCE"
            else:
                risk_tier = "NORMAL"

            metrics = {
                "event_start": start,
                "event_end": end,
                "previous_start": previous_start,
                "previous_end": previous_end,
                "previous_remark": previous_remark,
                "tbf_days": tbf_days,
                "cumulative_failure_count": offset + 1,
                "failures_last_30d": failure_counts[30],
                "failures_last_90d": failure_counts[90],
                "failures_last_365d": failure_counts[365],
                "mtbf_days": (
                    sum(mean_tbf_values) / len(mean_tbf_values)
                    if mean_tbf_values
                    else None
                ),
                "risk_tier": risk_tier,
            }
            for metric, value in metrics.items():
                result.iloc[position, result.columns.get_loc(metric)] = value

    return result
