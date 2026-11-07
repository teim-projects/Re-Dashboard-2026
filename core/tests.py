from types import SimpleNamespace

from django.test import SimpleTestCase

from core.views import build_expected_upload_tables


class ExpectedUploadTablesTests(SimpleTestCase):
    def test_includes_base_name_when_only_breakdown_table_exists(self):
        tables = build_expected_upload_tables(
            ["testuser_provider_a_wind_breakdowndata"],
            [SimpleNamespace(username="testuser")],
            [SimpleNamespace(name="Provider A")],
            [SimpleNamespace(name="Wind")],
        )

        self.assertEqual(
            tables,
            [{
                "name": "testuser_provider_a_wind",
                "label": "testuser - Provider A - Wind",
            }],
        )

    def test_matches_provider_and_energy_names_containing_underscores(self):
        tables = build_expected_upload_tables(
            ["testuser_provider_name_wind_power"],
            [SimpleNamespace(username="testuser")],
            [SimpleNamespace(name="Provider Name")],
            [SimpleNamespace(name="Wind Power")],
        )

        self.assertEqual(len(tables), 1)
        self.assertEqual(tables[0]["name"], "testuser_provider_name_wind_power")

    def test_ignores_tables_without_a_matching_provider_and_energy_type(self):
        tables = build_expected_upload_tables(
            ["testuser_unknown_wind"],
            [SimpleNamespace(username="testuser")],
            [SimpleNamespace(name="Provider")],
            [SimpleNamespace(name="Wind")],
        )

        self.assertEqual(tables, [])
