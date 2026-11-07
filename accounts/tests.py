from django.test import SimpleTestCase
import pandas as pd
from types import SimpleNamespace
from unittest.mock import patch

from accounts.breakdown_mapping import canonicalize_breakdown_dataframe
from accounts.breakdown_event_category import (
    normalize_event_category,
    resolve_event_category,
)
from accounts.breakdown_classification import build_catalog_matcher
from accounts.breakdown_ingestion import (
    deduplicate_breakdown_dataframe,
    enqueue_breakdown_classification_jobs,
)
from accounts.models import BreakdownClassificationJob
from accounts.views import _clean_structure_header, _suggest_breakdown_mapping


class MappingRecord:
    def __init__(self, source_header, canonical_header):
        self.source_header = source_header
        self.canonical_header = canonical_header


class BreakdownStructureMappingTests(SimpleTestCase):
    def test_oem_category_shorthands_are_normalized(self):
        self.assertEqual(normalize_event_category("pm"), "SCHEDULED")
        self.assertEqual(
            normalize_event_category("gf"),
            "EXTERNAL_FORCE_MAJEURE",
        )
        self.assertEqual(normalize_event_category("maj"), "FORCED_MAJOR")
        self.assertEqual(normalize_event_category("u"), "UNSCHEDULED")
        self.assertIsNone(normalize_event_category("unknown"))

    def test_category_fallback_uses_taxonomy_then_remark_then_duration(self):
        self.assertEqual(
            resolve_event_category(None, "MXA10", "annual inspection", 1),
            "EXTERNAL_FORCE_MAJEURE",
        )
        self.assertEqual(
            resolve_event_category(None, "MDK20", "preventive gearbox inspection", 15),
            "SCHEDULED",
        )
        self.assertEqual(
            resolve_event_category(None, "MDK20", "gearbox failure", 1),
            "FORCED_MAJOR",
        )
        self.assertEqual(
            resolve_event_category(None, "OTHER", "equipment trip", 12),
            "FORCED_MAJOR",
        )
        self.assertEqual(
            resolve_event_category(None, "OTHER", "equipment trip", 2),
            "UNSCHEDULED",
        )

    def test_mapped_canonical_event_category_is_preserved(self):
        self.assertEqual(
            resolve_event_category(
                "SCHEDULED", "MXA10", "grid outage", 20
            ),
            "SCHEDULED",
        )

    def test_provider_category_is_normalized_during_mapping(self):
        dataframe = pd.DataFrame({
            "event_date": ["2026-01-01", "2026-01-02"],
            "wtg": ["WTG-1", "WTG-2"],
            "remarks": ["scheduled maintenance", "grid fault"],
            "category_code": ["PM", "GF"],
        })
        mappings = [
            MappingRecord("event_date", "gen_date"),
            MappingRecord("wtg", "loc_no"),
            MappingRecord("remarks", "breakdown_remarks"),
            MappingRecord("category_code", "event_category"),
        ]

        result, _ = canonicalize_breakdown_dataframe(dataframe, mappings)

        self.assertEqual(
            result["event_category"].tolist(),
            ["SCHEDULED", "EXTERNAL_FORCE_MAJEURE"],
        )

    def test_enqueue_is_idempotent_for_reused_record_ids(self):
        manager = BreakdownClassificationJob.objects
        with (
            patch.object(manager, "bulk_create") as bulk_create,
            patch.object(manager, "filter") as filter_jobs,
        ):
            enqueue_breakdown_classification_jobs("provider_breakdowndata", [1, 2])

        jobs = bulk_create.call_args.args[0]
        self.assertEqual([job.record_id for job in jobs], [1, 2])
        self.assertTrue(bulk_create.call_args.kwargs["ignore_conflicts"])
        filter_jobs.assert_called_once_with(
            table_name="provider_breakdowndata",
            record_id__in=[1, 2],
        )
        filter_jobs.return_value.update.assert_called_once()
        self.assertEqual(
            filter_jobs.return_value.update.call_args.kwargs["status"],
            BreakdownClassificationJob.Status.PENDING,
        )

    def test_provider_headers_are_normalized_and_suggested(self):
        headers = [
            _clean_structure_header(name)
            for name in (
                "Date", "WTG No.", "Site Name", "State Name",
                "Breakdown Remarks", "Unused notes",
            )
        ]

        self.assertEqual(
            _suggest_breakdown_mapping(headers),
            {
                "date": "gen_date",
                "wtg_no": "loc_no",
                "site_name": "site",
                "state_name": "state",
                "breakdown_remarks": "breakdown_remarks",
            },
        )

    def test_state_value_is_canonicalized_for_recurrence_grouping(self):
        dataframe = pd.DataFrame({
            "event_date": ["2026-01-01"],
            "wtg": ["WTG-1"],
            "remarks": ["Gearbox issue"],
            "state_name": ["State A"],
        })
        mappings = [
            MappingRecord("event_date", "gen_date"),
            MappingRecord("wtg", "loc_no"),
            MappingRecord("remarks", "breakdown_remarks"),
            MappingRecord("state_name", "state"),
        ]

        result, _ = canonicalize_breakdown_dataframe(dataframe, mappings)

        self.assertEqual(result.loc[0, "state"], "State A")

    def test_only_one_source_header_is_auto_mapped_to_each_field(self):
        self.assertEqual(
            _suggest_breakdown_mapping(["date", "gen_date", "loc_no", "remarks"]),
            {
                "date": "gen_date",
                "loc_no": "loc_no",
                "remarks": "breakdown_remarks",
            },
        )

    def test_internal_taxonomy_fields_are_not_auto_mapped(self):
        self.assertNotIn(
            "rds_code",
            _suggest_breakdown_mapping(["rds_code"]).values(),
        )

    def test_multiple_remarks_and_asset_columns_are_concatenated(self):
        dataframe = pd.DataFrame({
            "event_date": ["2026-01-01"],
            "wtg": ["WTG-3"],
            "loc": ["SITE-1"],
            "description": ["Gearbox"],
            "remarks": ["Oil temperature high"],
        })
        mappings = [
            MappingRecord("event_date", "gen_date"),
            MappingRecord("wtg", "loc_no"),
            MappingRecord("loc", "loc_no"),
            MappingRecord("description", "breakdown_remarks"),
            MappingRecord("remarks", "breakdown_remarks"),
        ]

        result, _ = canonicalize_breakdown_dataframe(dataframe, mappings)

        self.assertEqual(result.loc[0, "loc_no"], "WTG-3_SITE-1")
        self.assertEqual(
            result.loc[0, "breakdown_remarks"],
            "Gearbox_Oil temperature high",
        )

    def test_exact_duplicate_breakdown_rows_are_removed_case_insensitively(self):
        dataframe = pd.DataFrame([
            {
                "provider_id": 1,
                "site": "Wind Farm A",
                "gen_date": pd.Timestamp("2026-10-01"),
                "loc_no": "WTG-1",
                "breakdown_remarks": " Gearbox  oil leak ",
            },
            {
                "provider_id": 1,
                "site": "wind farm a",
                "gen_date": pd.Timestamp("2026-10-01"),
                "loc_no": "wtg-1",
                "breakdown_remarks": "gearbox oil leak",
            },
        ])

        unique_rows, duplicate_count = deduplicate_breakdown_dataframe(dataframe)

        self.assertEqual(len(unique_rows), 1)
        self.assertEqual(duplicate_count, 1)

    def test_classifier_selects_matching_rds_catalog_entry(self):
        catalog = [
            SimpleNamespace(
                system_name="Drive Train",
                standard_component="Gearbox oil filter pump",
                description="Lubrication pump and inline oil filter",
                rds_code="MDK30",
            ),
            SimpleNamespace(
                system_name="Electrical System",
                standard_component="Power converter",
                description="IGBT stack and grid choke",
                rds_code="MSA10",
            ),
        ]
        match = build_catalog_matcher(catalog)

        entry, confidence = match("Gearbox lubrication oil filter pump failure")

        self.assertEqual(entry.rds_code, "MDK30")
        self.assertGreater(confidence, 0.25)

    def test_classifier_uses_catalog_keywords_as_high_precision_rules(self):
        catalog = [
            SimpleNamespace(
                system_name="Grid & Environmental",
                system_code="MXA",
                subsystem_name="",
                standard_component="External Grid Line Outage",
                description="Utility substation failure and load shedding",
                canonical_keywords="external grid failure, utility substation",
                rds_code="MXA10",
            ),
            SimpleNamespace(
                system_name="Drive Train",
                system_code="MDK",
                subsystem_name="",
                standard_component="Gearbox",
                description="Gearbox lubrication system",
                canonical_keywords="gearbox oil filter",
                rds_code="MDK20",
            ),
        ]
        match = build_catalog_matcher(catalog)

        entry, confidence = match("external grid failure reported")

        self.assertEqual(entry.rds_code, "MXA10")
        self.assertGreaterEqual(confidence, 0.89)

    def test_specific_catalog_keyword_outranks_a_broader_keyword(self):
        catalog = [
            SimpleNamespace(
                system_name="Drive Train",
                system_code="MDK",
                subsystem_name="",
                standard_component="Gearbox",
                description="High speed shaft and planetary stage",
                canonical_keywords="gearbox, high speed shaft",
                rds_code="MDK20",
            ),
            SimpleNamespace(
                system_name="Drive Train",
                system_code="MDK",
                subsystem_name="",
                standard_component="Gearbox Oil Filter and Pump",
                description="Inline oil filter and lubrication pump",
                canonical_keywords="oil filter, lubrication pump, oil inlet temperature",
                rds_code="MDK30",
            ),
        ]
        match = build_catalog_matcher(catalog)

        entry, _ = match("GBX oil filter lubrication pump")

        self.assertEqual(entry.rds_code, "MDK30")

    def test_classifier_expands_abbreviations_in_remark(self):
        catalog = [
            SimpleNamespace(
                system_name="Grid & Environmental",
                system_code="MXA",
                subsystem_name="",
                standard_component="External Grid Line Outage",
                description="Utility substation failure and load shedding",
                canonical_keywords="external grid fault",
                rds_code="MXA10",
            ),
            SimpleNamespace(
                system_name="Drive Train",
                system_code="MDK",
                subsystem_name="",
                standard_component="Gearbox",
                description="Gearbox lubrication system",
                canonical_keywords="gearbox oil filter",
                rds_code="MDK20",
            ),
        ]
        match = build_catalog_matcher(catalog)

        entry, confidence = match("GF utility stopped")

        self.assertEqual(entry.rds_code, "MXA10")
        self.assertGreater(confidence, 0)

    def test_low_score_still_returns_the_best_catalog_candidate(self):
        catalog = [
            SimpleNamespace(
                system_name="Drive Train",
                system_code="MDK",
                subsystem_name="",
                standard_component="Gearbox",
                description="Gearbox oil filter",
                canonical_keywords="gearbox oil filter",
                rds_code="MDK20",
            ),
            SimpleNamespace(
                system_name="Electrical System",
                system_code="MSA",
                subsystem_name="",
                standard_component="Power converter",
                description="IGBT stack and grid choke",
                canonical_keywords="power converter",
                rds_code="MSA10",
            ),
        ]
        match = build_catalog_matcher(catalog)

        entry, confidence = match("unrelated log text")

        self.assertIsNotNone(entry)
        self.assertIn(entry.rds_code, {"MDK20", "MSA10"})
        self.assertLess(confidence, 0.25)

    def test_domain_rules_disambiguate_catalog_components(self):
        catalog_data = {
            "MDA10": ("Rotor System", "Rotor Blade and Blade Bearing", "rotor blade, blade bearing"),
            "MDA20": ("Rotor System", "Pitch Motor and Drive", "pitch motor, pitch system"),
            "MDK10": ("Drive Train", "Main Shaft and Main Bearing", "main shaft, main bearing"),
            "MDK20": ("Drive Train", "Gearbox and Mechanical Brake", "gearbox, mechanical brake"),
            "MDK30": ("Drive Train", "Gearbox Oil Filter and Pump", "oil filter, lubrication pump"),
            "MDE10": ("Generator System", "Generator Stator and Winding", "stator winding, slip ring"),
            "MDE20": ("Generator System", "Generator DE and NDE Bearing", "generator bearing, NDE bearing"),
            "MDE30": ("Generator System", "Generator Cooling Fan", "generator cooling fan"),
            "MDY10": ("Yaw System", "Yaw Motor and Drive", "yaw motor, yaw drive"),
            "MDY20": ("Yaw System", "Yaw Bearing and Brake", "yaw bearing, yaw brake"),
            "MHD10": ("Hydraulic System", "Hydraulic Power Unit", "hydraulic pressure, HPU"),
            "MSA10": ("Electrical System", "Power Converter and IGBT", "power converter, IGBT"),
            "MSA20": ("Electrical System", "Internal Feeder and Protection Relay", "circuit breaker, protection relay"),
            "MSA30": ("Electrical System", "Main Transformer and Busbar", "main transformer, busbar"),
            "MKC10": ("Control and Safety", "Main PLC and Wind Sensors", "main PLC, anemometer"),
            "MXA10": ("Grid and Environmental", "External Grid Outage", "external grid failure, grid outage"),
            "UMD10": ("Tower and Structure", "Tower and Foundation", "tower shell, foundation"),
        }
        catalog = [
            SimpleNamespace(
                rds_code=code,
                system_code=code[:3],
                system_name=system,
                subsystem_name="",
                standard_component=component,
                description=keywords,
                canonical_keywords=keywords,
            )
            for code, (system, component, keywords) in catalog_data.items()
        ]
        match = build_catalog_matcher(catalog)
        expected_matches = {
            "generator DE bearing replacement": "MDE20",
            "generator stator winding fault": "MDE10",
            "pitch motor alarm": "MDA20",
            "GBX oil filter blocked": "MDK30",
            "mechanical brake issue": "MDK20",
            "external grid outage": "MXA10",
            "circuit breaker trip": "MSA20",
            "main transformer fault": "MSA30",
        }

        for remark, expected_code in expected_matches.items():
            with self.subTest(remark=remark):
                entry, confidence = match(remark)

                self.assertEqual(entry.rds_code, expected_code)
                self.assertEqual(confidence, 0.95)
