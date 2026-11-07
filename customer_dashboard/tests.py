import pandas as pd

from django.test import SimpleTestCase
from django.contrib.auth.models import AnonymousUser, User
from django.http import Http404
from django.test import RequestFactory

from customer_dashboard.views import (
    _breakdown_column,
    _duration_hours_from_bounds,
    _user_breakdown_tables,
    breakdown_classification_results,
    parse_time_to_hours,
)
from customer_dashboard.ml_utils import (
    BreakdownMLAnalyzer,
    detect_extended_breakdowns,
)
from customer_dashboard.recurrence_risk import (
    analyze_recurrence_risk,
    filter_recurrence_events,
    summarize_recurrence_details,
    summarize_risk_groups,
    summarize_wtg_risk,
)


class BreakdownClassificationResultsAccessTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_customer_cannot_access_classification_summary(self):
        request = self.factory.get(
            "/customer/breakdown-classification/",
            {"table": "customer_provider_wind_breakdowndata"},
        )
        request.user = User(username="customer", is_staff=False)

        with self.assertRaises(Http404):
            breakdown_classification_results(request)

    def test_anonymous_user_is_redirected_to_login(self):
        request = self.factory.get(
            "/customer/breakdown-classification/",
            {"table": "customer_provider_wind_breakdowndata"},
        )
        request.user = AnonymousUser()

        response = breakdown_classification_results(request)

        self.assertEqual(response.status_code, 302)


class BreakdownMLAnalyzerSchemaTests(SimpleTestCase):
    def test_analysis_uses_canonical_headers_and_attaches_taxonomy(self):
        analyzer = BreakdownMLAnalyzer(similarity_threshold=0.6, days_window=8)
        analyzer.load_dataframe(pd.DataFrame([
            {
                "gen_date": "2025-01-01",
                "loc_no": "WTG-1",
                "breakdown_remarks": "gearbox oil temperature high",
                "rds_code": "MDK20",
                "system_name": "Drivetrain",
                "subsystem_name": "Gearbox",
                "standard_component": "Gearbox",
                "classification_processed_at": "2025-02-01",
            },
            {
                "gen_date": "2025-01-03",
                "loc_no": "WTG-1",
                "breakdown_remarks": "gearbox oil temperature high",
                "rds_code": "MDK20",
                "system_name": "Drivetrain",
                "subsystem_name": "Gearbox",
                "standard_component": "Gearbox",
                "classification_processed_at": "2025-02-03",
            },
        ]))

        alerts = analyzer.detect_repetitions()

        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["date"], "2025-01-03")
        self.assertEqual(alerts[0]["rds_code"], "MDK20")
        self.assertEqual(alerts[0]["subsystem_name"], "Gearbox")

    def test_taxonomy_metadata_does_not_change_remark_similarity(self):
        analyzer = BreakdownMLAnalyzer(similarity_threshold=0.6, days_window=8)
        analyzer.load_dataframe(pd.DataFrame([
            {
                "gen_date": "2025-01-01",
                "loc_no": "WTG-1",
                "breakdown_remarks": "component failure repeated",
                "rds_code": "MDK20",
            },
            {
                "gen_date": "2025-01-03",
                "loc_no": "WTG-1",
                "breakdown_remarks": "component failure repeated",
                "rds_code": "MDA20",
            },
        ]))

        alerts = analyzer.detect_repetitions()

        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["rds_code"], "MDA20")


class ExtendedBreakdownDetectionTests(SimpleTestCase):
    def test_flags_duration_above_prior_component_p90(self):
        history = pd.DataFrame([
            {
                "gen_date": f"2025-01-{day:02d}",
                "loc_no": "WTG-1",
                "duration_hours": duration,
                "rds_code": "MDK20",
                "standard_component": "Gearbox",
            }
            for day, duration in enumerate(range(1, 11), start=1)
        ] + [
            {
                "gen_date": "2025-02-01",
                "loc_no": "WTG-1",
                "duration_hours": 11,
                "rds_code": "MDK20",
                "standard_component": "Gearbox",
            },
            {
                "gen_date": "2025-02-02",
                "loc_no": "WTG-2",
                "duration_hours": 100,
                "rds_code": "MDK20",
                "standard_component": "Gearbox",
            },
        ])

        alerts = detect_extended_breakdowns(history.iloc[10:11], history)

        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["component"], "Gearbox")
        self.assertEqual(alerts[0]["duration_hours"], 11)
        self.assertEqual(alerts[0]["p90_hours"], 9.1)
        self.assertEqual(alerts[0]["excess_hours"], 1.9)

    def test_uses_component_specific_history_and_ignores_first_event(self):
        history = pd.DataFrame([
            {
                "gen_date": "2025-01-01",
                "loc_no": "WTG-1",
                "duration_hours": 2,
                "standard_component": "Pitch Motor",
            },
            {
                "gen_date": "2025-01-02",
                "loc_no": "WTG-1",
                "duration_hours": 3,
                "standard_component": "Pitch Motor",
            },
            {
                "gen_date": "2025-01-03",
                "loc_no": "WTG-1",
                "duration_hours": 20,
                "standard_component": "Gearbox",
            },
            {
                "gen_date": "2025-01-04",
                "loc_no": "WTG-1",
                "duration_hours": 4,
                "standard_component": "Pitch Motor",
            },
        ])

        alerts = detect_extended_breakdowns(history.iloc[[0, 3]], history)

        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["date"], "2025-01-04")
        self.assertEqual(alerts[0]["component"], "Pitch Motor")


class RecurrenceRiskAnalysisTests(SimpleTestCase):
    def test_orders_events_imputes_missing_end_and_calculates_rolling_risk(self):
        events = pd.DataFrame([
            {
                "gen_date": "2025-01-20",
                "loc_no": "WTG-1",
                "provider": "OEM A",
                "site": "Site A",
                "state": "State A",
                "rds_code": "MDK20",
                "start_time": "2025-01-20 10:00",
                "duration_hours": 24,
                "breakdown_remarks": "second",
            },
            {
                "gen_date": "2025-01-01",
                "loc_no": "WTG-1",
                "provider": "OEM A",
                "site": "Site A",
                "state": "State A",
                "rds_code": "MDK20",
                "start_time": "2025-01-01 10:00",
                "end_time": "2025-01-02 10:00",
                "duration_hours": 24,
                "breakdown_remarks": "first",
            },
            {
                "gen_date": "2025-01-24",
                "loc_no": "WTG-1",
                "provider": "OEM A",
                "site": "Site A",
                "state": "State A",
                "rds_code": "MDK20",
                "start_time": "2025-01-24 10:00",
                "end_time": "2025-01-24 12:00",
                "duration_hours": 2,
                "breakdown_remarks": "third",
            },
        ])

        result = analyze_recurrence_risk(events)

        self.assertEqual(result.loc[0, "risk_tier"], "HIGH_RECURRENCE_RISK")
        self.assertEqual(result.loc[0, "tbf_days"], 18)
        self.assertEqual(result.loc[0, "event_end"].day, 21)
        self.assertEqual(result.loc[2, "failures_last_90d"], 3)
        self.assertEqual(result.loc[2, "risk_tier"], "CRITICAL_RECURRENCE")
        self.assertEqual(result.loc[2, "cumulative_failure_count"], 3)

    def test_long_term_and_uncategorized_risk_rules(self):
        events = pd.DataFrame([
            {
                "gen_date": f"2025-{month:02d}-01",
                "loc_no": "WTG-1",
                "rds_code": code,
                "breakdown_remarks": "failure",
            }
            for month, code in (
                (1, "MDA10"),
                (5, "MDA10"),
                (9, "MDA10"),
                (12, "MDA10"),
                (12, "UNCATEGORIZED"),
            )
        ])

        result = analyze_recurrence_risk(events)

        self.assertEqual(result.loc[3, "failures_last_365d"], 4)
        self.assertEqual(result.loc[3, "risk_tier"], "MODERATE_RECURRENCE")
        self.assertEqual(result.loc[4, "risk_tier"], "NORMAL")

    def test_same_code_on_different_assets_has_independent_history(self):
        events = pd.DataFrame([
            {
                "gen_date": f"2025-01-0{day}",
                "loc_no": machine,
                "rds_code": "MDK20",
                "breakdown_remarks": "failure",
            }
            for machine, day in (("WTG-1", 1), ("WTG-2", 2))
        ])

        result = analyze_recurrence_risk(events)

        self.assertEqual(result["cumulative_failure_count"].tolist(), [1, 1])
        self.assertEqual(result["failures_last_30d"].tolist(), [1, 1])

    def test_short_tbf_is_high_risk_even_when_failure_starts_are_over_30_days_apart(self):
        events = pd.DataFrame([
            {
                "gen_date": "2025-01-01",
                "loc_no": "WTG-1",
                "rds_code": "MDK20",
                "start_time": "2025-01-01 10:00",
                "duration_hours": 25 * 24,
                "breakdown_remarks": "first",
            },
            {
                "gen_date": "2025-02-01",
                "loc_no": "WTG-1",
                "rds_code": "MDK20",
                "start_time": "2025-02-01 10:00",
                "duration_hours": 1,
                "breakdown_remarks": "second",
            },
        ])

        result = analyze_recurrence_risk(events)

        self.assertEqual(result.loc[1, "failures_last_30d"], 1)
        self.assertEqual(result.loc[1, "tbf_days"], 6)
        self.assertEqual(result.loc[1, "risk_tier"], "HIGH_RECURRENCE_RISK")

    def test_summary_counts_each_wtg_once_at_its_highest_risk_tier(self):
        events = pd.DataFrame([
            {"loc_no": "WTG-1", "risk_tier": "NORMAL"},
            {"loc_no": "WTG-1", "risk_tier": "HIGH_RECURRENCE_RISK"},
            {"loc_no": "WTG-1", "risk_tier": "CRITICAL_RECURRENCE"},
            {"loc_no": "WTG-2", "risk_tier": "MODERATE_RECURRENCE"},
            {"loc_no": "WTG-3", "risk_tier": "NORMAL"},
        ])

        tier_counts, top_wtgs = summarize_wtg_risk(events)

        self.assertEqual(tier_counts, {
            "CRITICAL_RECURRENCE": 1,
            "HIGH_RECURRENCE_RISK": 0,
            "MODERATE_RECURRENCE": 1,
            "NORMAL": 1,
        })
        self.assertEqual(top_wtgs, [("WTG-1", 2), ("WTG-2", 1)])

    def test_group_summary_counts_each_asset_once_per_selected_group(self):
        events = pd.DataFrame([
            {
                "loc_no": "WTG-1",
                "provider": "OEM A",
                "risk_tier": "NORMAL",
            },
            {
                "loc_no": "WTG-1",
                "provider": "OEM A",
                "risk_tier": "CRITICAL_RECURRENCE",
            },
            {
                "loc_no": "WTG-2",
                "provider": "OEM A",
                "risk_tier": "HIGH_RECURRENCE_RISK",
            },
            {
                "loc_no": "WTG-3",
                "provider": "OEM B",
                "risk_tier": "MODERATE_RECURRENCE",
            },
        ])

        grouped = summarize_risk_groups(events, "provider")

        self.assertEqual(grouped, [
            {
                "label": "OEM A",
                "total": 2,
                "CRITICAL_RECURRENCE": 1,
                "HIGH_RECURRENCE_RISK": 1,
                "MODERATE_RECURRENCE": 0,
                "NORMAL": 0,
            },
            {
                "label": "OEM B",
                "total": 1,
                "CRITICAL_RECURRENCE": 0,
                "HIGH_RECURRENCE_RISK": 0,
                "MODERATE_RECURRENCE": 1,
                "NORMAL": 0,
            },
        ])

    def test_recurrence_details_rank_wtgs_and_summarize_subsystems_and_windows(self):
        events = pd.DataFrame([
            {
                "loc_no": "WTG-1",
                "site": "Site A",
                "event_start": pd.Timestamp("2025-03-01"),
                "risk_tier": "CRITICAL_RECURRENCE",
                "subsystem_name": "Gearbox",
                "system_name": "Drivetrain",
                "standard_component": "Bearing",
                "failures_last_30d": 2,
                "failures_last_90d": 3,
                "failures_last_365d": 4,
                "tbf_days": 5,
            },
            {
                "loc_no": "WTG-2",
                "site": "Site B",
                "event_start": pd.Timestamp("2024-11-01"),
                "risk_tier": "HIGH_RECURRENCE_RISK",
                "subsystem_name": "",
                "system_name": "Drivetrain",
                "standard_component": "Gearbox",
                "failures_last_30d": 0,
                "failures_last_90d": 2,
                "failures_last_365d": 2,
                "tbf_days": 8,
            },
            {
                "loc_no": "WTG-3",
                "site": "Site C",
                "event_start": pd.Timestamp("2025-02-28"),
                "risk_tier": "NORMAL",
                "subsystem_name": "Generator",
                "standard_component": "Generator",
                "failures_last_30d": 0,
                "failures_last_90d": 1,
                "failures_last_365d": 1,
                "tbf_days": None,
            },
        ])

        top_wtgs, subsystem_data, profile_data = summarize_recurrence_details(
            events, pd.Timestamp("2025-03-01")
        )

        self.assertEqual(top_wtgs, [{
            "wtg": "WTG-1",
            "site": "Site A",
            "breakdowns_90d": 1,
            "risk_tier": "CRITICAL_RECURRENCE",
            "component": "Bearing",
        }, {
            "wtg": "WTG-2",
            "site": "Site B",
            "breakdowns_90d": 0,
            "risk_tier": "HIGH_RECURRENCE_RISK",
            "component": "Gearbox",
        }])
        self.assertEqual(subsystem_data, [{
            "label": "Drivetrain",
            "total": 1,
            "CRITICAL_RECURRENCE": 0,
            "HIGH_RECURRENCE_RISK": 1,
            "MODERATE_RECURRENCE": 0,
        }, {
            "label": "Gearbox",
            "total": 1,
            "CRITICAL_RECURRENCE": 1,
            "HIGH_RECURRENCE_RISK": 0,
            "MODERATE_RECURRENCE": 0,
        }])
        self.assertEqual(
            [item["count"] for item in profile_data],
            [1, 1, 1, 1],
        )

    def test_multiple_recurrence_filters_combine_together(self):
        events = pd.DataFrame([
            {
                "provider": "OEM A",
                "site": "Site 1",
                "state": "State 1",
                "loc_no": "WTG-1",
            },
            {
                "provider": "OEM A",
                "site": "Site 2",
                "state": "State 1",
                "loc_no": "WTG-2",
            },
            {
                "provider": "OEM B",
                "site": "Site 1",
                "state": "State 2",
                "loc_no": "WTG-3",
            },
        ])

        filtered = filter_recurrence_events(events, {
            "provider": "OEM A",
            "site": "Site 1",
            "state": "State 1",
            "loc_no": "WTG-1",
        })

        self.assertEqual(filtered["loc_no"].tolist(), ["WTG-1"])

    def test_unknown_filter_includes_blank_and_missing_column_values(self):
        events = pd.DataFrame([
            {"provider": None, "loc_no": "WTG-1"},
            {"provider": "", "loc_no": "WTG-2"},
            {"provider": "OEM A", "loc_no": "WTG-3"},
        ])

        filtered = filter_recurrence_events(events, {"provider": "__missing__"})

        self.assertEqual(filtered["loc_no"].tolist(), ["WTG-1", "WTG-2"])
        self.assertEqual(
            filter_recurrence_events(
                events.drop(columns=["provider"]),
                {"state": "__missing__"},
            )["loc_no"].tolist(),
            ["WTG-1", "WTG-2", "WTG-3"],
        )


class BreakdownDashboardSchemaTests(SimpleTestCase):
    def test_selects_canonical_and_legacy_user_tables(self):
        tables = [
            "test_user_provider_wind_breakdowndata",
            "test_user_wind",
            "other_user_provider_wind_breakdowndata",
            "test_user_provider_solar",
        ]

        self.assertEqual(
            _user_breakdown_tables(tables, "test_user"),
            [
                "test_user_provider_wind_breakdowndata",
                "test_user_wind",
            ],
        )

    def test_resolves_canonical_breakdown_columns_case_insensitively(self):
        columns = [
            "GEN_DATE",
            "LOC_NO",
            "DURATION_HRS",
            "BREAKDOWN_REMARKS",
            "PROVIDER",
            "UPLOADED_BY",
        ]

        self.assertEqual(_breakdown_column(columns, "gen_date", "date"), "GEN_DATE")
        self.assertEqual(
            _breakdown_column(columns, "duration_hrs", "breakdown_hours"),
            "DURATION_HRS",
        )
        self.assertEqual(
            _breakdown_column(columns, "breakdown_remarks", "remarks"),
            "BREAKDOWN_REMARKS",
        )
        self.assertEqual(
            _breakdown_column(columns, "uploaded_by", "uploader"),
            "UPLOADED_BY",
        )

    def test_duration_hours_parse_as_numeric_hours(self):
        self.assertEqual(parse_time_to_hours("2.5"), 2.5)

    def test_missing_duration_can_be_derived_from_start_and_end(self):
        self.assertEqual(
            _duration_hours_from_bounds(
                pd.Timestamp("2025-01-01 10:00"),
                pd.Timestamp("2025-01-01 12:30"),
            ),
            2.5,
        )
