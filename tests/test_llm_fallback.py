import unittest
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()
