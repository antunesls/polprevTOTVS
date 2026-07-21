import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch

from src.dashboard import generate_html
from src.html_admin import generate_admin_html
from src.html_report import generate_cluster_html


class DepartmentHtmlReportTest(unittest.TestCase):
    def test_generates_department_dashboard_with_selector_and_profile_groups(self):
        from src.department_html_report import generate_department_html

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "departamentos.html"
            generate_department_html(
                {
                    "CONTROLADORIA": {
                        "total_users": 2,
                        "total_routines": 3,
                        "profile_groups": [{"name": "P_PF_CONTROLADORI_01", "users": ["maria", "vitor"], "routines": ["FINA100"]}],
                        "tier4_users": [{"login": "maria", "exclusive_count": 0}, {"login": "vitor", "exclusive_count": 0}],
                    }
                },
                str(output_path),
                "TESTE",
            )

            html = output_path.read_text(encoding="utf-8")

        self.assertIn("CAMADAS POR DEPARTAMENTO - TESTE", html)
        self.assertIn("department-select", html)
        self.assertIn("P_PF_CONTROLADORI_01", html)
        self.assertIn("renderDepartment", html)

    def test_department_dashboard_lists_reused_existing_rules(self):
        from src.department_html_report import generate_department_html

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "departamentos.html"
            generate_department_html(
                {
                    "COMPRAS": {
                        "total_users": 2,
                        "total_routines": 3,
                        "profile_groups": [
                            {"name": "P_CJ_COMPRAS", "users": ["maria", "vitor"], "routines": ["MATA010"], "reuses_existing_rule": "P_COMPRAS"},
                            {"name": "P_CJ_NOVO", "users": ["ana"], "routines": ["MATA020"]},
                        ],
                        "tier4_users": [],
                    }
                },
                str(output_path),
                "TESTE",
            )

            html = output_path.read_text(encoding="utf-8")

        self.assertIn("Conjuntos preexistentes reaproveitados", html)
        self.assertIn("P_COMPRAS", html)
        self.assertIn("P_CJ_COMPRAS", html)


class HtmlReportPerformanceTest(unittest.TestCase):
    def test_routine_pool_uses_search_threshold_limit_and_precomputed_counts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "dashboard.html"
            generate_cluster_html(
                {"routines": [], "total_users": 2, "empresa": "TESTE"},
                [],
                [],
                [],
                {"users": []},
                {},
                {
                    "u1": [{"code": "MATA010", "permissions": ["Visualizar"]}],
                    "u2": [{"code": "MATA010", "permissions": ["Visualizar"]}],
                },
                {},
                str(output_path),
                "TESTE",
            )

            html = output_path.read_text(encoding="utf-8")

        self.assertIn("const MIN_ROUTINE_SEARCH = 2", html)
        self.assertIn("const MAX_ROUTINE_RESULTS = 100", html)
        self.assertIn("const ROUTINE_USER_COUNT = buildRoutineUserCount()", html)
        self.assertIn("Digite ao menos 2 caracteres", html)
        self.assertIn("clearTimeout(routineSearchTimer)", html)

    def test_tier3_html_shows_reuse_or_new_rule_badges(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "dashboard.html"
            generate_cluster_html(
                {"routines": [], "total_users": 2, "empresa": "TESTE"},
                [],
                [
                    {"name": "P_CJ_COMPRAS", "reason": "Grupo de compras", "routines": ["MATA010"], "users": ["u1"], "reuses_existing_rule": "P_COMPRAS"},
                    {"name": "P_CJ_NOVO", "reason": "Grupo novo", "routines": ["MATA020"], "users": ["u2"]},
                ],
                [],
                {"users": []},
                {"u1": {"name": "User 1", "login": "u1", "depto": "COMPRAS", "total_routines": 1}, "u2": {"name": "User 2", "login": "u2", "depto": "COMPRAS", "total_routines": 1}},
                {"u1": ["MATA010"], "u2": ["MATA020"]},
                {"u1": "COMPRAS", "u2": "COMPRAS"},
                str(output_path),
                "TESTE",
            )

            html = output_path.read_text(encoding="utf-8")

        self.assertIn("Reaproveita P_COMPRAS", html)
        self.assertIn("Nova regra", html)

    def test_tier3_html_filters_clusters_without_adherent_users_before_render(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "dashboard.html"
            generate_cluster_html(
                {"routines": [], "total_users": 1, "empresa": "TESTE"},
                [],
                [
                    {"name": "P_CJ_VALIDO", "routines": ["MATA010"], "users": ["u1"]},
                    {"name": "P_CJ_INVALIDO", "routines": ["MATA999"], "users": ["u1"]},
                ],
                [],
                {"users": []},
                {"u1": {"name": "User 1", "login": "u1", "depto": "COMPRAS", "total_routines": 1}},
                {"u1": [{"code": "MATA010", "permissions": []}]},
                {"u1": "COMPRAS"},
                str(output_path),
                "TESTE",
            )

            html = output_path.read_text(encoding="utf-8")

        self.assertIn('"name": "P_CJ_VALIDO"', html)
        self.assertNotIn('"name": "P_CJ_INVALIDO"', html)


class AdminDashboardHtmlTest(unittest.TestCase):
    def test_admin_dashboard_has_bulk_rule_removal_controls(self):
        inventory = {
            "rules": [
                {
                    "rule_id": "A1",
                    "rule_name": "P_EXISTENTE",
                    "source": "EXISTENTE",
                    "tier": "EXISTENTE",
                    "action": "MANTER",
                    "users": [{"user_id": "000001", "login": "joao"}],
                    "groups": [],
                    "routines": [],
                },
                {
                    "rule_id": None,
                    "rule_name": "P_NOVA",
                    "source": "NOVO",
                    "tier": "TIER3",
                    "action": "CRIAR",
                    "users": [{"user_id": "000002", "login": "maria"}],
                    "groups": [],
                    "routines": [],
                },
            ]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "admin.html"
            generate_admin_html(inventory, str(output_path), "TESTE")
            html = output_path.read_text(encoding="utf-8")

        self.assertIn("Remover Selecionadas", html)
        self.assertIn("Desfazer Selecionadas", html)
        self.assertIn("bulkMarkSelected", html)
        self.assertIn("SYS_RULES_USR_RULES SET D_E_L_E_T_", html)
        self.assertNotIn("SYS_RULES SET D_E_L_E_T_", html)
        self.assertNotIn("SYS_RULES_FEATURES SET D_E_L_E_T_", html)
        self.assertNotIn("SYS_RULES_TRANSACT SET D_E_L_E_T_", html)

    def test_admin_modal_shows_missing_features_for_complementar_rule(self):
        inventory = {
            "rules": [
                {
                    "rule_id": "A1",
                    "rule_name": "P_EXISTENTE",
                    "source": "EXISTENTE",
                    "tier": "TIER3",
                    "action": "COMPLEMENTAR",
                    "users": [{"user_id": "000001", "login": "joao"}],
                    "groups": [],
                    "routines": [
                        {
                            "routine": "MATA010",
                            "description": "Produtos",
                            "features": [
                                {"feature": "Visualizar", "access": "1", "menu_oper": 2, "menu_def": "A010VIS", "status": "EXISTENTE"},
                                {"feature": "Alterar", "access": "1", "menu_oper": 4, "menu_def": "A010ALT", "status": "FALTANTE"},
                                {"feature": "Excluir", "access": "1", "menu_oper": 5, "menu_def": "A010DEL", "status": "FALTANTE"},
                            ],
                        },
                        {
                            "routine": "FINA050",
                            "description": "Contas a Pagar",
                            "features": [
                                {"feature": "Incluir", "access": "1", "menu_oper": 3, "menu_def": "FIN050INC", "status": "FALTANTE"},
                            ],
                        },
                    ],
                },
            ]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "admin.html"
            generate_admin_html(inventory, str(output_path), "TESTE")
            html = output_path.read_text(encoding="utf-8")

        self.assertIn("Funções que serão adicionadas", html)
        self.assertIn("Alterar", html)
        self.assertIn("Excluir", html)
        self.assertIn("Incluir", html)
        self.assertIn("MATA010", html)
        self.assertIn("FINA050", html)


class UserDashboardHtmlTest(unittest.TestCase):
    def test_dashboard_uses_effective_access_status(self):
        report = {
            "user": "usr001",
            "user_id": "000001",
            "total_menus": 1,
            "total_routines": 2,
            "groups": [{"group_id": "*", "group_name": "*"}],
            "access_codes": [
                {"code": "112", "enabled": True, "description": "Gerar rel. no servidor"},
                {"code": "121", "enabled": True, "description": "Usa impressora no server"},
            ],
            "menus": [{"items": []}],
            "routines_summary": [
                {
                    "routine": "MATA010",
                    "description": "Produtos",
                    "menu_name": "SIGACOM",
                    "has_explicit_privilege": True,
                    "effective_access": "PERMITIDO",
                    "browse_permissions": [],
                    "disabled_by_acbrowse": False,
                },
                {
                    "routine": "MATA020",
                    "description": "Fornecedores",
                    "menu_name": "SIGACOM",
                    "has_explicit_privilege": False,
                    "effective_access": "NAO_PERMITIDO",
                    "denial_reason": "GROUP_DEFAULT",
                    "browse_permissions": [],
                    "disabled_by_acbrowse": False,
                },
            ],
            "privileges_raw": {},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "usr001_access.json"
            report_path.write_text(json.dumps(report), encoding="utf-8")

            with patch("src.dashboard.OUTPUT_DIR", tmpdir):
                output_path = generate_html(str(report_path))

            html = Path(output_path).read_text(encoding="utf-8")

        self.assertIn("LIBERADO", html)
        self.assertIn("NAO PERMITIDO", html)
        self.assertIn("Codigos SYS_USR_ACCESS", html)
        self.assertIn("Gerar rel. no servidor", html)
        self.assertIn("Usa impressora no server", html)
        self.assertIn(">2</div><div class=\"kpi-label\">Codigos ativos</div>", html)
        self.assertNotIn(">OK<", html)

    def test_dashboard_shows_privilege_reuse_recommendation(self):
        report = {
            "user": "usr001",
            "user_id": "000001",
            "total_menus": 1,
            "total_routines": 1,
            "groups": [{"group_id": "10", "group_name": "COMPRAS"}],
            "access_codes": [],
            "menus": [{"items": []}],
            "routines_summary": [
                {
                    "routine": "MATA010",
                    "description": "Produtos",
                    "menu_name": "SIGACOM",
                    "has_explicit_privilege": True,
                    "effective_access": "PERMITIDO",
                    "browse_permissions": [],
                    "disabled_by_acbrowse": False,
                },
            ],
            "privileges_raw": {},
            "privilege_recommendations": {
                "requested_permissions": ["MATA010: Visualizar", "MATA010: Alterar"],
                "suggested_base_rule": {
                    "rule_id": "A1",
                    "rule_name": "P_EXISTENTE",
                    "coverage_status": "PARCIAL",
                    "matched_permissions_count": 1,
                    "requested_permissions_count": 2,
                    "missing_permissions": ["MATA010: Alterar"],
                    "excess_permissions": ["MATA020: Excluir"],
                    "has_excess_permissions": True,
                    "linked_users": [{"user_id": "000777", "login": "maria"}],
                    "linked_groups": [{"group_id": "10", "group_name": "COMPRAS"}],
                },
                "exact_matches": [],
                "partial_matches": [],
            },
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "usr001_access.json"
            report_path.write_text(json.dumps(report), encoding="utf-8")

            with patch("src.dashboard.OUTPUT_DIR", tmpdir):
                output_path = generate_html(str(report_path))

            html = Path(output_path).read_text(encoding="utf-8")

        self.assertIn("Sugestao de Reaproveitamento", html)
        self.assertIn("P_EXISTENTE", html)
        self.assertIn("Cobertura parcial", html)
        self.assertIn("Reaproveitar e complementar", html)
        self.assertIn("MATA010: Alterar", html)
        self.assertIn("MATA020: Excluir", html)
        self.assertIn("COMPRAS", html)

    def test_dashboard_shows_exact_reuse_action_when_no_complement_is_needed(self):
        report = {
            "user": "usr001",
            "user_id": "000001",
            "total_menus": 1,
            "total_routines": 1,
            "groups": [],
            "access_codes": [],
            "menus": [{"items": []}],
            "routines_summary": [
                {
                    "routine": "MATA010",
                    "description": "Produtos",
                    "menu_name": "SIGACOM",
                    "has_explicit_privilege": True,
                    "effective_access": "PERMITIDO",
                    "browse_permissions": [],
                    "disabled_by_acbrowse": False,
                },
            ],
            "privileges_raw": {},
            "privilege_recommendations": {
                "requested_permissions": ["MATA010: Visualizar"],
                "suggested_base_rule": {
                    "rule_id": "A2",
                    "rule_name": "P_EXATO",
                    "coverage_status": "EXATA",
                    "matched_permissions_count": 1,
                    "requested_permissions_count": 1,
                    "missing_permissions": [],
                    "excess_permissions": [],
                    "has_excess_permissions": False,
                    "linked_users": [],
                    "linked_groups": [],
                },
                "exact_matches": [],
                "partial_matches": [],
            },
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "usr001_access.json"
            report_path.write_text(json.dumps(report), encoding="utf-8")

            with patch("src.dashboard.OUTPUT_DIR", tmpdir):
                output_path = generate_html(str(report_path))

            html = Path(output_path).read_text(encoding="utf-8")

        self.assertIn("Cobertura exata", html)
        self.assertIn("Reaproveitar sem ajuste", html)


if __name__ == "__main__":
    unittest.main()
