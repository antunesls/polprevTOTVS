import tempfile
import unittest
from pathlib import Path


class DepartmentValidationReportTest(unittest.TestCase):
    def _build_reports(self):
        return [
            {
                "user": "joao",
                "user_name": "Joao da Silva",
                "user_depto": "COMERCIAL",
                "groups": [{"group_name": "VENDEDORES"}],
                "access_codes": [{"code": "112", "enabled": True, "description": "Gerar rel. no servidor"}],
                "routines_summary": [
                    {
                        "routine": "MATA410",
                        "description": "Pedido de Venda",
                        "menu_name": "SIGAFAT",
                        "module": "FAT",
                        "effective_access": "PERMITIDO",
                        "features": {
                            "Visualizar": {"access": "PERMITIDO"},
                            "Alterar": {"access": "PERMITIDO"},
                        },
                    },
                    {
                        "routine": "MATA411",
                        "description": "Liberacao de Pedido",
                        "menu_name": "SIGAFAT",
                        "module": "FAT",
                        "effective_access": "NEGADO",
                        "features": {"Visualizar": {"access": "NEGADO"}},
                    },
                ],
            },
            {
                "user": "maria",
                "user_name": "Maria Souza",
                "user_depto": "COMERCIAL",
                "groups": [{"group_name": "VENDEDORES"}],
                "access_codes": [],
                "routines_summary": [
                    {
                        "routine": "MATA420",
                        "description": "Consulta de Clientes",
                        "menu_name": "SIGAFAT",
                        "module": "FAT",
                        "effective_access": "SEM_REGRA",
                        "features": {},
                    }
                ],
            },
            {
                "user": "ana",
                "user_name": "Ana Lima",
                "user_depto": "CONTROLADORIA",
                "groups": [],
                "access_codes": [],
                "routines_summary": [
                    {
                        "routine": "FINA050",
                        "description": "Contas a Pagar",
                        "menu_name": "SIGAFIN",
                        "module": "FIN",
                        "effective_access": "PERMITIDO",
                        "features": {"Visualizar": {"access": "PERMITIDO"}},
                    }
                ],
            },
        ]

    def test_generates_one_html_per_department_with_one_page_per_user(self):
        from src.department_validation_report import generate_department_validation_reports

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = generate_department_validation_reports(self._build_reports(), tmpdir, "TESTE")

            self.assertEqual(sorted(Path(p).name for p in paths), ["COMERCIAL.html", "CONTROLADORIA.html"])

            comercial_html = Path(tmpdir, "COMERCIAL.html").read_text(encoding="utf-8")
            self.assertIn("Joao da Silva", comercial_html)
            self.assertIn("Maria Souza", comercial_html)
            self.assertIn("page-break-after: always", comercial_html)

    def test_lists_only_effectively_allowed_routines(self):
        from src.department_validation_report import generate_department_validation_reports

        with tempfile.TemporaryDirectory() as tmpdir:
            generate_department_validation_reports(self._build_reports(), tmpdir, "TESTE")
            html = Path(tmpdir, "COMERCIAL.html").read_text(encoding="utf-8")

        self.assertIn("MATA410", html)
        self.assertNotIn("MATA411", html)
        self.assertNotIn("MATA420", html)
        self.assertIn("Visualizar, Alterar", html)

    def test_sem_regra_user_without_group_default_is_listed_as_allowed(self):
        from src.department_validation_report import generate_department_validation_reports

        reports = [
            {
                "user": "cristia",
                "user_name": "Andrea Cristina Rocha Vieira",
                "user_depto": "COMPRAS",
                "groups": [{"group_name": "Alteracao de pedido"}],
                "access_codes": [],
                "routines_summary": [
                    {
                        "routine": "COMR015",
                        "description": "Aval. Fornecedor",
                        "menu_name": "COMPRAS_COMPRAS",
                        "module": "",
                        "in_menu": True,
                        "effective_access": "SEM_REGRA",
                        "disabled_by_acbrowse": False,
                        "features": {},
                    },
                    {
                        "routine": "COMR016",
                        "description": "Bloqueada Perfil",
                        "menu_name": "COMPRAS_COMPRAS",
                        "module": "",
                        "in_menu": True,
                        "effective_access": "SEM_REGRA",
                        "disabled_by_acbrowse": True,
                        "features": {},
                    },
                ],
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            generate_department_validation_reports(reports, tmpdir, "TESTE")
            html = Path(tmpdir, "COMPRAS.html").read_text(encoding="utf-8")

        self.assertIn("COMR015", html)
        self.assertNotIn("COMR016", html)

    def test_renders_empty_message_for_user_without_allowed_routines(self):
        from src.department_validation_report import generate_department_validation_reports

        with tempfile.TemporaryDirectory() as tmpdir:
            generate_department_validation_reports(self._build_reports(), tmpdir, "TESTE")
            html = Path(tmpdir, "COMERCIAL.html").read_text(encoding="utf-8")

        self.assertIn("Nenhuma permissao liberada encontrada", html)

    def test_renders_access_codes_and_groups_for_user(self):
        from src.department_validation_report import generate_department_validation_reports

        with tempfile.TemporaryDirectory() as tmpdir:
            generate_department_validation_reports(self._build_reports(), tmpdir, "TESTE")
            html = Path(tmpdir, "COMERCIAL.html").read_text(encoding="utf-8")

        self.assertIn("VENDEDORES", html)
        self.assertIn("112 - Gerar rel. no servidor", html)


if __name__ == "__main__":
    unittest.main()
