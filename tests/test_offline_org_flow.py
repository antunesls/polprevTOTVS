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


class WizardMapeamentoTest(unittest.TestCase):
    def test_wizard_asks_reuse_or_delete_and_respects_choice(self):
        with patch("run.cfg.PRIVILEGE_MODE", "per_user"), \
             patch("run.cfg.EMPRESA_NAME", "TESTE"), \
             patch("run.cls"), \
             patch("run.run_batch", return_value=None) as mock_batch, \
             patch("run.run_batch_organizational", return_value=None) as mock_batch_org, \
             patch("run.OUTPUT_DIR", tempfile.gettempdir()):
            with patch("builtins.input", side_effect=[
                "",       # ETAPA 1: ENTER = batch
                "N",      # ETAPA 2: gerar SQL? nao
                "N",      # ETAPA 4: gerar menu? nao
                "N",      # ETAPA 6: gerar dashboard? nao
                "N",      # NEW: apagar arquivos? nao (reusar)
                "S",      # confirmacao
            ]):
                run.wizard_mapeamento("usr001")

            mock_batch.assert_called_once_with(gen_priv=False, rule_name="", gen_dash=False, gen_menu=False, menu_link_mode="replace")
            mock_batch_org.assert_not_called()

    def test_wizard_asks_reuse_or_delete_delete_mode(self):
        with patch("run._clear_generated_mapping_files", return_value=[]) as mock_clear:
            with patch("run.cfg.PRIVILEGE_MODE", "per_user"), \
                 patch("run.cfg.EMPRESA_NAME", "TESTE"), \
                 patch("run.cls"), \
                 patch("run.run_batch", return_value=None), \
                 patch("run.run_batch_organizational", return_value=None):
                with patch("builtins.input", side_effect=[
                    "",       # ETAPA 1: ENTER = batch
                    "N",      # ETAPA 2: gerar SQL? nao
                    "N",      # ETAPA 4: gerar menu? nao
                    "N",      # ETAPA 6: gerar dashboard? nao
                    "S",      # NEW: apagar arquivos? sim
                    "S",      # confirmacao
                ]):
                    run.wizard_mapeamento("usr001")

                mock_clear.assert_called_once()


class OrganizationalDashboardFlowTest(unittest.TestCase):
    def test_clear_generated_mapping_files_removes_only_generated_artifacts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            generated_files = [
                "joao_access.json",
                "joao_dashboard.html",
                "joao_privileges.sql",
                "joao_canonical_menus.sql",
                "canonical_menus.sql",
                "camadas_TESTE.html",
                "camadas_departamentos_TESTE.html",
                "clusters_TESTE.html",
                "clusters_TESTE.json",
                "TESTE_organizacional.sql",
            ]
            preserved_files = [
                "export.json",
                "export.sql",
                "clean_privileges.sql",
                "manual.txt",
            ]

            for file_name in generated_files + preserved_files:
                Path(output_dir, file_name).write_text("conteudo", encoding="utf-8")
            Path(output_dir, "logs").mkdir()
            Path(output_dir, "logs", "session.log").write_text("log", encoding="utf-8")

            with patch("run.OUTPUT_DIR", tmpdir):
                removed = run._clear_generated_mapping_files()

            self.assertEqual(sorted(removed), sorted(str(Path(output_dir, file_name)) for file_name in generated_files))
            for file_name in generated_files:
                self.assertFalse(Path(output_dir, file_name).exists())
            for file_name in preserved_files:
                self.assertTrue(Path(output_dir, file_name).exists())
            self.assertTrue(Path(output_dir, "logs", "session.log").exists())

    def test_load_reports_from_files_reuses_existing_access_files_without_cleanup(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir, "joao_access.json")
            report_path.write_text(
                '{"user":"joao","routines_summary":[{"routine":"MATA010"}]}',
                encoding="utf-8",
            )

            with patch("run.OUTPUT_DIR", tmpdir):
                reports = run._load_reports_from_files()

            self.assertEqual([report["user"] for report in reports], ["joao"])
            self.assertTrue(report_path.exists())

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
                  patch("src.html_report.generate_cluster_html") as cluster_helper, \
                  patch("src.department_html_report.generate_department_html") as dept_helper, \
                  patch("src.html_admin.generate_admin_html") as admin_helper, \
                  patch("src.html_kanban.generate_kanban_html") as kanban_helper, \
                  patch("src.html_tree.generate_tree_html") as tree_helper, \
                  patch("webbrowser.open"), \
                  patch("run.generate_department_validation_reports") as validation_helper:
                mock_get_connection.return_value.__enter__.return_value = object()
                mock_get_connection.return_value.__exit__.return_value = False

                run.run_batch_organizational("2")

                admin_helper.assert_called_once()
                cluster_helper.assert_not_called()
                dept_helper.assert_not_called()
                validation_helper.assert_not_called()
                kanban_helper.assert_not_called()
                tree_helper.assert_not_called()

    def test_main_menu_option_triggers_department_validation_report(self):
        with patch("run.cfg.PRIVILEGE_MODE", "organizational_layer"), \
             patch("run.menu", side_effect=["6", "0"]), \
             patch("run.wait_enter"), \
             patch("run.cls"), \
             patch("run.run_department_validation_only") as report_helper:
            run.main()

        report_helper.assert_called_once()


class ScopedAdminFlowTest(unittest.TestCase):
    def _build_reports(self):
        return [
            {
                "user": "joao", "user_id": "001", "user_name": "Joao",
                "user_depto": "COMERCIAL", "total_routines": 2,
                "routines_summary": [
                    {"routine": "MATA010", "description": "Produtos", "features": {"Visualizar": {"access_raw": "1", "menu_oper": 2, "menu_def": "A010VIS"}}},
                    {"routine": "MATA020", "description": "Clientes", "features": {}},
                ],
            },
            {
                "user": "maria", "user_id": "002", "user_name": "Maria",
                "user_depto": "COMERCIAL", "total_routines": 3,
                "routines_summary": [
                    {"routine": "MATA010", "description": "Produtos", "features": {"Visualizar": {"access_raw": "1", "menu_oper": 2, "menu_def": "A010VIS"}}},
                    {"routine": "MATA030", "description": "Fornecedores", "features": {}},
                    {"routine": "MATA040", "description": "Transportadoras", "features": {}},
                ],
            },
        ]

    def test_scoped_admin_user_generates_admin_html_for_single_user(self):
        reports = self._build_reports()

        class FakeMapper:
            def build_full_report(self, login):
                rep = next((r for r in reports if r["user"] == login), None)
                rep_copy = dict(rep)
                rep_copy["_conn"] = object()
                return rep_copy

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("run.OUTPUT_DIR", tmpdir), \
                 patch("run.cfg.EMPRESA_NAME", "TESTE"), \
                 patch("run.get_connection") as mock_conn, \
                 patch("run.discover_columns_for_tables", return_value={}), \
                 patch("run.print_schema_summary"), \
                 patch("run.UserMapper", return_value=FakeMapper()), \
                 patch("run.load_existing_rules", return_value={}), \
                 patch("run._load_existing_links", return_value={}), \
                 patch("src.html_admin.generate_admin_html") as admin_helper, \
                 patch("webbrowser.open"):
                mock_conn.return_value.__enter__.return_value = object()
                mock_conn.return_value.__exit__.return_value = False

                result = run.run_scoped_admin("user", "joao")

            self.assertIsNotNone(result)
            admin_helper.assert_called_once()
            inventory = admin_helper.call_args[0][0]
            rules = inventory.get("rules", [])
            self.assertGreaterEqual(len(rules), 1)
            rule_names = [r["rule_name"] for r in rules]
            self.assertIn("P_JOAO", rule_names)

    def test_scoped_admin_department_generates_tier2_and_tier4(self):
        reports = self._build_reports()

        class FakeMapper:
            def list_non_blocked_users(self):
                return [
                    {"login": "joao", "id": "001", "depto": "COMERCIAL"},
                    {"login": "maria", "id": "002", "depto": "COMERCIAL"},
                ]

            def build_full_report(self, login):
                rep = next((r for r in reports if r["user"] == login), None)
                rep_copy = dict(rep)
                rep_copy["_conn"] = object()
                return rep_copy

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("run.OUTPUT_DIR", tmpdir), \
                 patch("run.cfg.EMPRESA_NAME", "TESTE"), \
                 patch("run.get_connection") as mock_conn, \
                 patch("run.discover_columns_for_tables", return_value={}), \
                 patch("run.print_schema_summary"), \
                 patch("run.UserMapper", return_value=FakeMapper()), \
                 patch("run.load_existing_rules", return_value={}), \
                 patch("run._load_existing_links", return_value={}), \
                 patch("src.html_admin.generate_admin_html") as admin_helper, \
                 patch("webbrowser.open"):
                mock_conn.return_value.__enter__.return_value = object()
                mock_conn.return_value.__exit__.return_value = False

                result = run.run_scoped_admin("department", "COMERCIAL")

            self.assertIsNotNone(result)
            admin_helper.assert_called_once()
            inventory = admin_helper.call_args[0][0]
            rules = inventory.get("rules", [])
            self.assertGreaterEqual(len(rules), 1)

            rule_names = [r["rule_name"] for r in rules]
            tiers = {r["rule_name"]: r.get("tier") for r in rules}

            self.assertIn("P_COMERCIAL", rule_names)
            self.assertEqual(tiers.get("P_COMERCIAL"), "TIER2")

            tier4_rules = [r for r in rules if r.get("tier") == "TIER4"]
            for r in tier4_rules:
                self.assertTrue(r["rule_name"].startswith("P_"))

    def test_scoped_admin_department_common_routine_not_in_tier4(self):
        reports = [
            {
                "user": "joao", "user_id": "001", "user_name": "Joao",
                "user_depto": "FINANCEIRO", "total_routines": 1,
                "routines_summary": [
                    {"routine": "FINA010", "description": "Titulos", "features": {}},
                ],
            },
            {
                "user": "maria", "user_id": "002", "user_name": "Maria",
                "user_depto": "FINANCEIRO", "total_routines": 1,
                "routines_summary": [
                    {"routine": "FINA010", "description": "Titulos", "features": {}},
                ],
            },
        ]

        class FakeMapper:
            def list_non_blocked_users(self):
                return [
                    {"login": "joao", "id": "001", "depto": "FINANCEIRO"},
                    {"login": "maria", "id": "002", "depto": "FINANCEIRO"},
                ]

            def build_full_report(self, login):
                rep = next((r for r in reports if r["user"] == login), None)
                rep_copy = dict(rep)
                rep_copy["_conn"] = object()
                return rep_copy

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("run.OUTPUT_DIR", tmpdir), \
                 patch("run.cfg.EMPRESA_NAME", "TESTE"), \
                 patch("run.get_connection") as mock_conn, \
                 patch("run.discover_columns_for_tables", return_value={}), \
                 patch("run.print_schema_summary"), \
                 patch("run.UserMapper", return_value=FakeMapper()), \
                 patch("run.load_existing_rules", return_value={}), \
                 patch("run._load_existing_links", return_value={}), \
                 patch("src.html_admin.generate_admin_html") as admin_helper, \
                 patch("webbrowser.open"):
                mock_conn.return_value.__enter__.return_value = object()
                mock_conn.return_value.__exit__.return_value = False

                result = run.run_scoped_admin("department", "FINANCEIRO")

            self.assertIsNotNone(result)
            admin_helper.assert_called_once()
            inventory = admin_helper.call_args[0][0]
            rules = inventory.get("rules", [])
            rule_names = [r["rule_name"] for r in rules]
            tiers = {r["rule_name"]: r.get("tier") for r in rules}

            self.assertIn("P_FINANCEIRO", rule_names)
            self.assertEqual(tiers.get("P_FINANCEIRO"), "TIER2")
            self.assertNotIn("TIER4", [r.get("tier") for r in rules])

    def test_ask_org_scope_returns_user_for_u(self):
        with patch("builtins.input", return_value="U"):
            result = run._ask_org_scope("joao")
        self.assertEqual(result, "user")

    def test_ask_org_scope_returns_department_for_d(self):
        with patch("builtins.input", return_value="D"):
            result = run._ask_org_scope("joao")
        self.assertEqual(result, "department")

    def test_ask_org_scope_returns_all_for_t(self):
        with patch("builtins.input", return_value="T"):
            result = run._ask_org_scope("joao")
        self.assertEqual(result, "all")

    def test_ask_org_scope_returns_none_for_x(self):
        with patch("builtins.input", return_value="X"):
            result = run._ask_org_scope("joao")
        self.assertIsNone(result)

    def test_wizard_org_mode_user_scope_calls_scoped_admin(self):
        with patch("run.cfg.PRIVILEGE_MODE", "organizational_layer"), \
             patch("run.cfg.EMPRESA_NAME", "TESTE"), \
             patch("run.cls"), \
             patch("run.run_batch", return_value=None), \
             patch("run.run_batch_organizational", return_value=None) as mock_batch_org, \
             patch("run.run_scoped_admin", return_value="/tmp/joao_admin.html") as mock_scoped, \
             patch("run.run_mapping", return_value=({"user": "joao", "_conn": object(), "user_depto": "COMERCIAL", "routines_summary": []}, {}, "joao")):
            with patch("builtins.input", side_effect=[
                "joao",    # ETAPA 1: usuario joao
                "S",       # ETAPA 2: gerar SQL
                "N",       # ETAPA 4: gerar menu
                "N",       # ETAPA 6: gerar dashboard
                "N",       # ETAPA 7: reusar
                "S",       # ETAPA 8: confirmacao
            ]), patch("run._ask_org_scope", return_value="user") as mock_scope:
                run.wizard_mapeamento("usr001")

            mock_scope.assert_called_once_with("joao")
            mock_scoped.assert_called_once()
            call_args = mock_scoped.call_args
            self.assertEqual(call_args[0][0], "user")
            self.assertEqual(call_args[0][1], "joao")
            mock_batch_org.assert_not_called()

    def test_wizard_org_mode_department_scope_maps_user_then_department(self):
        with patch("run.cfg.PRIVILEGE_MODE", "organizational_layer"), \
             patch("run.cfg.EMPRESA_NAME", "TESTE"), \
             patch("run.cls"), \
             patch("run.run_batch", return_value=None), \
             patch("run.run_batch_organizational", return_value=None) as mock_batch_org, \
             patch("run.run_scoped_admin", return_value="/tmp/COMERCIAL_admin.html") as mock_scoped, \
             patch("run.run_mapping", return_value=({"user": "maria", "_conn": object(), "user_depto": "COMERCIAL", "routines_summary": [{"routine": "MATA010"}]}, {}, "maria")):
            with patch("builtins.input", side_effect=[
                "maria",   # ETAPA 1: usuario maria
                "S",       # ETAPA 2: gerar SQL
                "N",       # ETAPA 4: gerar menu
                "N",       # ETAPA 6: gerar dashboard
                "N",       # ETAPA 7: reusar
                "S",       # ETAPA 8: confirmacao
            ]), patch("run._ask_org_scope", return_value="department") as mock_scope:
                run.wizard_mapeamento("usr001")

            mock_scope.assert_called_once_with("maria")
            mock_scoped.assert_called_once()
            call_args = mock_scoped.call_args
            self.assertEqual(call_args[0][0], "department")
            self.assertEqual(call_args[0][1], "COMERCIAL")
            mock_batch_org.assert_not_called()


class IgnoredGroupFilterTest(unittest.TestCase):
    def _make_report(self, user, groups):
        return {"user": user, "groups": groups, "routines_summary": [{"routine": "MATA010"}]}

    def test_removes_user_with_ignored_group_id(self):
        with patch("run.cfg.IGNORED_USER_GROUP_IDS", ["000000"]):
            reports = [
                self._make_report("admin", [{"group_id": "000000", "group_name": "Administradores"}]),
                self._make_report("joao", [{"group_id": "000123", "group_name": "Financeiro"}]),
            ]
            result = run._filter_ignored_group_users(reports)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["user"], "joao")

    def test_removes_user_when_any_group_matches_ignored_list(self):
        with patch("run.cfg.IGNORED_USER_GROUP_IDS", ["000000", "000999"]):
            reports = [
                self._make_report("maria", [
                    {"group_id": "000123", "group_name": "Financeiro"},
                    {"group_id": "000999", "group_name": "Externo"},
                ]),
                self._make_report("joao", [{"group_id": "000123", "group_name": "Financeiro"}]),
            ]
            result = run._filter_ignored_group_users(reports)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["user"], "joao")

    def test_filter_is_case_and_whitespace_insensitive(self):
        with patch("run.cfg.IGNORED_USER_GROUP_IDS", ["  000000  "]):
            reports = [
                self._make_report("admin", [{"group_id": " 000000 ", "group_name": "Admin"}]),
                self._make_report("joao", [{"group_id": "000123", "group_name": "Financeiro"}]),
            ]
            result = run._filter_ignored_group_users(reports)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["user"], "joao")

    def test_does_not_filter_by_group_name(self):
        with patch("run.cfg.IGNORED_USER_GROUP_IDS", ["000000"]):
            reports = [
                self._make_report("admin", [{"group_id": "000123", "group_name": "000000"}]),
                self._make_report("joao", [{"group_id": "000123", "group_name": "Financeiro"}]),
            ]
            result = run._filter_ignored_group_users(reports)
            self.assertEqual(len(result), 2)

    def test_empty_ignored_list_keeps_all_users(self):
        with patch("run.cfg.IGNORED_USER_GROUP_IDS", []):
            reports = [
                self._make_report("admin", [{"group_id": "000000", "group_name": "Administradores"}]),
                self._make_report("joao", [{"group_id": "000123", "group_name": "Financeiro"}]),
            ]
            result = run._filter_ignored_group_users(reports)
            self.assertEqual(len(result), 2)

    def test_user_with_no_groups_is_kept(self):
        with patch("run.cfg.IGNORED_USER_GROUP_IDS", ["000000"]):
            reports = [
                self._make_report("admin", [{"group_id": "000000", "group_name": "Administradores"}]),
                self._make_report("semgrupo", []),
            ]
            result = run._filter_ignored_group_users(reports)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["user"], "semgrupo")


if __name__ == "__main__":
    unittest.main()
