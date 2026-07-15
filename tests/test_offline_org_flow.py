import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run
from src.data_exporter import generate_export_sql


class OfflineExportTest(unittest.TestCase):
    def test_export_includes_sys_rules_transact_table(self):
        schema = {
            "SYS_RULES_TRANSACT": [
                {"COLUMN_NAME": "RL__ID"},
                {"COLUMN_NAME": "RL__ROTINA"},
                {"COLUMN_NAME": "RL__DESROT"},
            ]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.data_exporter.OUTPUT_DIR", tmpdir):
                path = generate_export_sql(schema)
                sql = Path(path).read_text(encoding="utf-8")

        self.assertIn("SYS_RULES_TRANSACT", sql)


class OrganizationalDashboardFlowTest(unittest.TestCase):
    def test_batch_organizational_sql_flow_calls_dashboard_generation_after_sql(self):
        reports = [
            {
                "user": "joao",
                "user_name": "Joao",
                "user_depto": "COMERCIAL",
                "total_routines": 1,
                "routines_summary": [
                    {"routine": "MATA010", "description": "Cadastro de Produtos", "features": {"Visualizar": {"access_raw": "1", "menu_oper": 2, "menu_def": "A010VIS"}}},
                ],
            },
            {
                "user": "maria",
                "user_name": "Maria",
                "user_depto": "COMERCIAL",
                "total_routines": 1,
                "routines_summary": [
                    {"routine": "MATA010", "description": "Cadastro de Produtos", "features": {"Visualizar": {"access_raw": "1", "menu_oper": 2, "menu_def": "A010VIS"}}},
                ],
            },
        ]

        class FakeMapper:
            def __init__(self, schema, conn):
                pass

            def list_non_blocked_users(self):
                return [{"login": "joao", "id": "1"}, {"login": "maria", "id": "2"}]

            def build_full_report(self, login):
                return next(rep for rep in reports if rep["user"] == login)

        class FakeGen:
            def __init__(self, all_reports, schema, empresa_name, conn):
                self.reports = all_reports
                self.tier1_routines = {"MATA010"}
                self.tier2_routines = {"COMERCIAL": {"MATA010"}}
                self.tier3_routines = {}
                self.tier4_routines = {}

            def generate_interactive(self, llm_clusters=None):
                return None

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("run.OUTPUT_DIR", tmpdir), \
                 patch("run.cfg.EMPRESA_NAME", "TESTE"), \
                 patch("run.get_connection") as mock_get_connection, \
                 patch("run.discover_columns_for_tables", return_value={}), \
                 patch("run.print_schema_summary"), \
                 patch("run.UserMapper", FakeMapper), \
                 patch("src.organizational_privileges.OrganizationalPrivilegeGenerator", FakeGen), \
                 patch("run._generate_org_dashboards") as dashboard_helper:
                mock_get_connection.return_value.__enter__.return_value = object()
                mock_get_connection.return_value.__exit__.return_value = False

                run.run_batch_organizational("2")

                dashboard_helper.assert_called_once()


if __name__ == "__main__":
    unittest.main()
