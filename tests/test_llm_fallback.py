import unittest
import tempfile
from io import StringIO
from contextlib import redirect_stdout
from unittest.mock import patch

import run
import src.llm_categorizer as llm_categorizer
from src.organizational_privileges import OrganizationalPrivilegeGenerator


SCHEMA = {}


class FakeOrganizationalPrivilegeGenerator(OrganizationalPrivilegeGenerator):
    def _get_max_id(self, table, pk_col):
        return 0


class LlmFallbackTest(unittest.TestCase):
    def test_regex_fallback_recovers_routines_when_json_parse_fails(self):
        original_api_key = llm_categorizer.llm_cfg.LLM_API_KEY
        original_call_openrouter = llm_categorizer.call_openrouter
        try:
            llm_categorizer.llm_cfg.LLM_API_KEY = "test-key"
            llm_categorizer.call_openrouter = lambda prompt: '{"clusters":[{"name":"P_CJ_ETIQUETAS","reason":"Rotinas de etiquetas","routines":["ETQ001","ETQ002"],"users":["joao"]}],"unclustered":[]}'

            with patch("src.llm_categorizer.extract_json", return_value=None):
                result = llm_categorizer.suggest_clusters([
                    {"user": "joao", "routines": [
                        {"code": "ETQ001", "description": "Impressao de etiqueta", "permissions": ["Visualizar"]},
                        {"code": "ETQ002", "description": "Reimpressao de etiqueta", "permissions": ["Visualizar"]},
                    ]}
                ])
        finally:
            llm_categorizer.call_openrouter = original_call_openrouter
            llm_categorizer.llm_cfg.LLM_API_KEY = original_api_key

        self.assertEqual(result["clusters"][0]["name"], "P_CJ_ETIQUETAS")
        self.assertEqual(result["clusters"][0]["routines"], ["ETQ001", "ETQ002"])


class ManualNamingTest(unittest.TestCase):
    def test_manual_name_suggestion_prefers_description_terms_over_code_prefixes(self):
        reports = [
            {
                "user": "joao",
                "user_depto": "COMERCIAL",
                "routines_summary": [
                    {"routine": "MATA010", "description": "Cadastro de Produtos"},
                    {"routine": "MATA035", "description": "Grupo de Produtos"},
                    {"routine": "MATA036", "description": "Tipo de Produtos"},
                ],
            },
            {
                "user": "maria",
                "user_depto": "MARKETING",
                "routines_summary": [
                    {"routine": "MATA010", "description": "Cadastro de Produtos"},
                    {"routine": "MATA035", "description": "Grupo de Produtos"},
                    {"routine": "MATA036", "description": "Tipo de Produtos"},
                ],
            },
        ]
        generator = FakeOrganizationalPrivilegeGenerator(reports, SCHEMA, "TESTE", conn=None)

        suggested = generator._suggest_manual_cluster_name(["MATA010", "MATA035", "MATA036"])

        self.assertEqual(suggested, "P_CJ_PRODUTOS")


class BatchRunLlmGateTest(unittest.TestCase):
    def test_batch_run_does_not_require_option_7_preview_before_trying_llm(self):
        class StopConnection:
            def __enter__(self):
                raise RuntimeError("stop-after-gate")

            def __exit__(self, exc_type, exc, tb):
                return False

        original_empresa_name = run.cfg.EMPRESA_NAME
        original_llm_api_key = run.cfg.LLM_API_KEY
        original_saved_clusters = run._saved_llm_clusters
        try:
            run.cfg.EMPRESA_NAME = "TESTE"
            run.cfg.LLM_API_KEY = "test-key"
            run._saved_llm_clusters = None

            with patch("run.input", side_effect=AssertionError("input should not be called")), \
                 patch("run.get_connection", return_value=StopConnection()), \
                 patch("run.os.makedirs"), \
                 patch("run.section"), \
                 patch("run.spin"), \
                 patch("run.ok"), \
                 patch("run.fail"), \
                 patch("run.warn"), \
                 patch("run.info"):
                run.run_batch_organizational("2")
        finally:
            run.cfg.EMPRESA_NAME = original_empresa_name
            run.cfg.LLM_API_KEY = original_llm_api_key
            run._saved_llm_clusters = original_saved_clusters


class LlmProgressOutputTest(unittest.TestCase):
    def test_suggest_clusters_reports_input_size_and_retry_attempt(self):
        original_api_key = llm_categorizer.llm_cfg.LLM_API_KEY
        original_call_openrouter = llm_categorizer.call_openrouter
        calls = []

        def fake_call(prompt):
            calls.append(prompt)
            if len(calls) == 1:
                return '{"clusters":[{"name":"P_CJ_COMPRAS","reason":"Rotinas de compras","routines":["MATA010","MATA020"],"users":[]'
            return '{"clusters":[{"name":"P_CJ_COMPRAS","reason":"Rotinas de compras","routines":["MATA010","MATA020"],"users":[]}],"unclustered":[]}'

        try:
            llm_categorizer.llm_cfg.LLM_API_KEY = "test-key"
            llm_categorizer.call_openrouter = fake_call
            output = StringIO()
            with redirect_stdout(output):
                llm_categorizer.suggest_clusters([
                    {"user": "joao", "routines": [
                        {"code": "MATA010", "description": "Pedido de compra", "permissions": ["Visualizar"]},
                        {"code": "MATA020", "description": "Cotacao de compra", "permissions": ["Visualizar"]},
                    ]}
                ])
        finally:
            llm_categorizer.call_openrouter = original_call_openrouter
            llm_categorizer.llm_cfg.LLM_API_KEY = original_api_key

        text = output.getvalue()
        self.assertIn("Entrada:", text)
        self.assertIn("usuarios | 2 rotinas unicas | >= 2 usuarios: 0 | catalogo enviado: 0", text)
        self.assertIn("Tentativa 1/2", text)
        self.assertIn("Tentativa 2/2", text)

    def test_try_llm_clustering_reports_reason_before_jaccard_when_no_valid_clusters_survive(self):
        reports = [
            {
                "user": "joao",
                "user_depto": "COMERCIAL",
                "routines_summary": [
                    {"routine": "MATA010", "description": "Cadastro de Produtos"},
                    {"routine": "MATA020", "description": "Pedido de Compra"},
                ],
            },
            {
                "user": "maria",
                "user_depto": "MARKETING",
                "routines_summary": [
                    {"routine": "MATA010", "description": "Cadastro de Produtos"},
                    {"routine": "MATA020", "description": "Pedido de Compra"},
                ],
            },
        ]
        generator = FakeOrganizationalPrivilegeGenerator(reports, SCHEMA, "TESTE", conn=None)
        output = StringIO()
        import src.config as cfg
        original_api_key = cfg.LLM_API_KEY

        try:
            cfg.LLM_API_KEY = "test-key"
            with patch("src.llm_categorizer.suggest_clusters", return_value={"clusters": [{"name": "P_CJ_INVALIDO", "routines": ["ROT999"], "users": []}], "unclustered": []}):
                with redirect_stdout(output):
                    result = generator._try_llm_clustering()
        finally:
            cfg.LLM_API_KEY = original_api_key

        self.assertIsNone(result)
        text = output.getvalue()
        self.assertIn("LLM retornou 1 conjuntos brutos", text)
        self.assertIn("Validacao local: 0 conjuntos aproveitados | 1 descartados", text)
        self.assertIn("Alternando para modo manual (Jaccard)", text)


class SqlProgressOutputTest(unittest.TestCase):
    def test_generate_sql_reports_input_summary_and_table_counters(self):
        reports = [
            {
                "user": "joao",
                "user_depto": "COMERCIAL",
                "routines_summary": [
                    {"routine": "MATA010", "description": "Cadastro de Produtos", "features": {"Visualizar": {"access_raw": "1", "menu_oper": 2, "menu_def": "A010VIS"}}},
                    {"routine": "MATA020", "description": "Pedido de Compra", "features": {"Visualizar": {"access_raw": "1", "menu_oper": 2, "menu_def": "A020VIS"}}},
                ],
            },
            {
                "user": "maria",
                "user_depto": "COMERCIAL",
                "routines_summary": [
                    {"routine": "MATA010", "description": "Cadastro de Produtos", "features": {"Visualizar": {"access_raw": "1", "menu_oper": 2, "menu_def": "A010VIS"}}},
                    {"routine": "MATA020", "description": "Pedido de Compra", "features": {"Visualizar": {"access_raw": "1", "menu_oper": 2, "menu_def": "A020VIS"}}},
                ],
            },
        ]
        schema = {
            "SYS_RULES": [{"COLUMN_NAME": "RL__ID"}, {"COLUMN_NAME": "RL__CODIGO"}, {"COLUMN_NAME": "RL__DESCRI"}, {"COLUMN_NAME": "RUL_TYPE"}],
            "SYS_RULES_FEATURES": [{"COLUMN_NAME": "RL__ITEM"}, {"COLUMN_NAME": "RL__ID"}, {"COLUMN_NAME": "RL__ROTINA"}, {"COLUMN_NAME": "RL__DESMDEF"}, {"COLUMN_NAME": "RL__ACESSO"}, {"COLUMN_NAME": "RL__MENUOPER"}, {"COLUMN_NAME": "RL__MENUDEF"}],
            "SYS_RULES_TRANSACT": [{"COLUMN_NAME": "RL__ID"}, {"COLUMN_NAME": "RL__ROTINA"}, {"COLUMN_NAME": "RL__DESROT"}, {"COLUMN_NAME": "RL__ACESSO"}, {"COLUMN_NAME": "RL__CHKSUM"}, {"COLUMN_NAME": "D_E_L_E_T_"}],
            "SYS_RULES_USR_RULES": [{"COLUMN_NAME": "USER_ID"}, {"COLUMN_NAME": "USR_RL_ID"}],
        }
        generator = FakeOrganizationalPrivilegeGenerator(reports, schema, "TESTE", conn=None)
        generator.tier1_routines = {"MATA010", "MATA020"}
        output = StringIO()

        with patch("src.organizational_privileges.OUTPUT_DIR", tempfile.gettempdir()):
            with redirect_stdout(output):
                generator._generate_sql()

        text = output.getvalue()
        self.assertIn("Entrada para o SQL:", text)
        self.assertIn("Tier 1: 1 regra geral", text)
        self.assertIn("SYS_RULES:", text)
        self.assertIn("SYS_RULES_FEATURES:", text)
        self.assertIn("SYS_RULES_TRANSACT:", text)
        self.assertIn("SYS_RULES_USR_RULES:", text)


class SharedResidualPromotionTest(unittest.TestCase):
    def setUp(self):
        self.reports = [
            {
                "user": "AGALATTI",
                "user_depto": "FINANCEIRO",
                "routines_summary": [
                    {"routine": "MATA010", "features": {"Visualizar": {"access": "PERMITIDO"}}},
                    {"routine": "FINR355", "features": {"Visualizar": {"access": "PERMITIDO"}, "Alterar": {"access": "PERMITIDO"}}},
                    {"routine": "FINR120", "features": {"Visualizar": {"access": "PERMITIDO"}}},
                    {"routine": "FINR220", "features": {"Visualizar": {"access": "PERMITIDO"}}},
                    {"routine": "FINR480", "features": {"Visualizar": {"access": "PERMITIDO"}}},
                ],
            },
            {
                "user": "JDASILVA",
                "user_depto": "FINANCEIRO",
                "routines_summary": [
                    {"routine": "MATA010", "features": {"Visualizar": {"access": "PERMITIDO"}}},
                    {"routine": "FINR355", "features": {"Visualizar": {"access": "PERMITIDO"}, "Alterar": {"access": "PERMITIDO"}}},
                    {"routine": "FINR120", "features": {"Visualizar": {"access": "PERMITIDO"}}},
                    {"routine": "FINR220", "features": {"Visualizar": {"access": "PERMITIDO"}}},
                    {"routine": "FINR480", "features": {"Visualizar": {"access": "PERMITIDO"}}},
                ],
            },
            {
                "user": "PTALASSO",
                "user_depto": "FINANCEIRO",
                "routines_summary": [
                    {"routine": "MATA010", "features": {"Visualizar": {"access": "PERMITIDO"}}},
                    {"routine": "FINR355", "features": {"Visualizar": {"access": "PERMITIDO"}}},
                    {"routine": "FINR120", "features": {"Visualizar": {"access": "PERMITIDO"}}},
                    {"routine": "FINR220", "features": {"Visualizar": {"access": "PERMITIDO"}}},
                ],
            },
        ]

    def test_promotes_shared_residuals_to_tier3(self):
        generator = FakeOrganizationalPrivilegeGenerator(self.reports, SCHEMA, "TESTE", conn=None)

        generator.tier1_routines = {"MATA010"}
        generator.tier2_routines = {}
        generator.tier3_routines = {}
        generator._compute_tier4()

        self.assertIn("AGALATTI", generator.tier4_routines)
        self.assertIn("FINR355", generator.tier4_routines["AGALATTI"])

        generator._promote_shared_residual_clusters(min_users=2, min_routines=2, user_overlap_threshold=0.70)

        self.assertTrue(any("REL_FINANC" in name for name in generator.tier3_routines))
        self.assertTrue(any("FINR355" in str(r) for info in generator.tier3_routines.values() for r in info["routines"]))

        for name, info in generator.tier3_routines.items():
            if "REL_FINANC" in name:
                self.assertIn("FINR355",
                    str(info["routines"]))
                self.assertTrue(len(info["members"]) >= 2)
                self.assertTrue(len(info["routines"]) >= 2)
                self.assertIn("AGALATTI", info["members"])
                self.assertIn("JDASILVA", info["members"])
                self.assertNotIn("FINR355", info["members"])
                self.assertNotIn("FINR120", info["members"])
                self.assertNotIn("FINR220", info["members"])

    def test_promoted_members_are_real_users_not_routines(self):
        generator = FakeOrganizationalPrivilegeGenerator(self.reports, SCHEMA, "TESTE", conn=None)

        generator.tier1_routines = {"MATA010"}
        generator.tier2_routines = {}
        generator.tier3_routines = {}
        generator._compute_tier4()

        generator._promote_shared_residual_clusters(min_users=2, min_routines=2, user_overlap_threshold=0.70)

        valid_users = {rep["user"] for rep in self.reports}
        for name, info in generator.tier3_routines.items():
            for member in info["members"]:
                self.assertIn(member, valid_users,
                    f"{name}: '{member}' nao e um usuario valido (pode ser rotina/ID)")

    def test_does_not_promote_single_routine(self):
        reports = [
            {
                "user": "AGALATTI",
                "user_depto": "FINANCEIRO",
                "routines_summary": [
                    {"routine": "MATA010", "features": {"Visualizar": {"access": "PERMITIDO"}}},
                    {"routine": "FINR355", "features": {"Visualizar": {"access": "PERMITIDO"}}},
                ],
            },
            {
                "user": "JDASILVA",
                "user_depto": "FINANCEIRO",
                "routines_summary": [
                    {"routine": "MATA010", "features": {"Visualizar": {"access": "PERMITIDO"}}},
                    {"routine": "FINR355", "features": {"Visualizar": {"access": "PERMITIDO"}}},
                ],
            },
        ]

        generator = FakeOrganizationalPrivilegeGenerator(reports, SCHEMA, "TESTE", conn=None)
        generator.tier1_routines = {"MATA010"}
        generator.tier2_routines = {}
        generator.tier3_routines = {}
        generator._compute_tier4()

        generator._promote_shared_residual_clusters(min_users=2, min_routines=2, user_overlap_threshold=0.70)

        self.assertEqual(len(generator.tier3_routines), 0)
        self.assertIn("AGALATTI", generator.tier4_routines)

    def test_promotion_reduces_tier4(self):
        generator = FakeOrganizationalPrivilegeGenerator(self.reports, SCHEMA, "TESTE", conn=None)

        generator.tier1_routines = {"MATA010"}
        generator.tier2_routines = {}
        generator.tier3_routines = {}
        generator._compute_tier4()

        initial_tier4_count = sum(len(r) for r in generator.tier4_routines.values())
        self.assertGreater(initial_tier4_count, 0)

        generator._promote_shared_residual_clusters(min_users=2, min_routines=2, user_overlap_threshold=0.70)

        if generator.tier3_routines:
            final_tier4_count = sum(len(r) for r in generator.tier4_routines.values())
            self.assertLessEqual(final_tier4_count, initial_tier4_count)


class PrefixDomainLabelTest(unittest.TestCase):
    def test_known_prefixes(self):
        from src.organizational_privileges import _prefix_domain_label

        self.assertEqual(_prefix_domain_label("FINR"), "REL_FINANC")
        self.assertEqual(_prefix_domain_label("MATR"), "REL_MAT")
        self.assertEqual(_prefix_domain_label("FISR"), "REL_FISCAL")
        self.assertEqual(_prefix_domain_label("CTBR"), "REL_CONTAB")

    def test_generic_r_prefix(self):
        from src.organizational_privileges import _prefix_domain_label

        self.assertEqual(_prefix_domain_label("ETQR"), "REL_ETQ")

    def test_generic_a_prefix(self):
        from src.organizational_privileges import _prefix_domain_label

        self.assertEqual(_prefix_domain_label("MATA"), "CAD_MAT")

    def test_generic_c_prefix(self):
        from src.organizational_privileges import _prefix_domain_label

        self.assertEqual(_prefix_domain_label("MATC"), "CONS_MAT")

    def test_generic_m_prefix(self):
        from src.organizational_privileges import _prefix_domain_label

        self.assertEqual(_prefix_domain_label("MATM"), "MOV_MAT")

    def test_unknown_prefix_fallback(self):
        from src.organizational_privileges import _prefix_domain_label

        self.assertEqual(_prefix_domain_label("XYZ1"), "XYZ1")


if __name__ == "__main__":
    unittest.main()
