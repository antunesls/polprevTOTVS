import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
