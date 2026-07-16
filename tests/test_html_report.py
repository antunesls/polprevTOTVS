import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch

from src.dashboard import generate_html
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


if __name__ == "__main__":
    unittest.main()
