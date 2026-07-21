import unittest

from src.tier3 import apply_department_canonicalization, build_department_analysis, build_department_common_routines, build_equivalent_profile_groups, build_tier4_users, load_existing_rules, match_profile_to_existing_rules, normalize_tier3_sets, routine_permissions, user_routine_items


class Tier3FunctionalSetsTest(unittest.TestCase):
    def setUp(self):
        self.reports = [
            {
                "user": "joao",
                "user_name": "Joao",
                "user_depto": "EXPEDICAO",
                "routines_summary": [
                    {"routine": "ETQ001", "description": "Impressao de etiqueta", "features": {
                        "Visualizar": {"access": "PERMITIDO"},
                        "Alterar": {"access": "PERMITIDO"},
                    }},
                    {"routine": "ETQ002", "description": "Reimpressao de etiqueta"},
                    {"routine": "WMS010", "description": "Separacao"},
                ],
            },
            {
                "user": "maria",
                "user_name": "Maria",
                "user_depto": "EXPEDICAO",
                "routines_summary": [
                    {"routine": "ETQ001", "description": "Impressao de etiqueta", "features": {
                        "Visualizar": {"access": "PERMITIDO"},
                    }},
                    {"routine": "WMS020", "description": "Conferencia"},
                ],
            },
        ]

    def test_extracts_only_allowed_routine_permissions(self):
        routine = {
            "routine": "MATA010",
            "features": {
                "Visualizar": {"access": "PERMITIDO"},
                "Alterar": {"access": "PERMITIDO"},
                "Excluir": {"access": "BLOQUEADO"},
            },
        }

        self.assertEqual(routine_permissions(routine), ["Alterar", "Visualizar"])

    def test_normalizes_functional_sets_and_derives_users_from_routines(self):
        raw_sets = [
            {
                "name": "etiquetas",
                "reason": "Rotinas de etiquetas",
                "routines": ["ETQ001 - Impressao de etiqueta", "ETQ002"],
                "users": ["usuario_inventado"],
            },
            {
                "name": "P_CJ_INVALIDO",
                "reason": "Conjunto com uma rotina deve ser ignorado",
                "routines": ["WMS010"],
            },
        ]

        result = normalize_tier3_sets(raw_sets, self.reports)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "P_CJ_ETIQUETAS")
        self.assertEqual(result[0]["routines"], ["ETQ001", "ETQ002"])
        self.assertEqual(result[0]["users"], ["joao"])

    def test_tier3_discards_cluster_with_no_user_covering_all_items(self):
        result = normalize_tier3_sets(
            [{"name": "P_CJ_MISTO", "routines": ["ETQ002", "WMS020"]}],
            self.reports,
        )

        self.assertEqual(result, [])

    def test_discards_routines_with_required_permissions_that_no_user_covers(self):
        result = normalize_tier3_sets(
            [{
                "name": "P_CJ_PEDIDOS_COMPRA",
                "routines": [
                    {"code": "ETQ001", "permissions": ["Excluir"]},
                    "ETQ002",
                    "WMS010",
                ],
            }],
            self.reports,
        )

        self.assertEqual(result[0]["routines"], ["ETQ002", "WMS010"])
        self.assertEqual(result[0]["users"], ["joao"])

    def test_discards_set_when_filtering_invalid_items_leaves_less_than_two_routines(self):
        result = normalize_tier3_sets(
            [{
                "name": "P_CJ_ORCAMENTO",
                "routines": [
                    {"code": "ETQ001", "permissions": ["Excluir"]},
                    "ETQ002",
                ],
            }],
            self.reports,
        )

        self.assertEqual(result, [])

    def test_routine_can_belong_to_more_than_one_functional_set(self):
        raw_sets = [
            {"name": "P_CJ_ETIQUETAS", "routines": ["ETQ001", "ETQ002"]},
            {"name": "P_CJ_SEPARACAO", "routines": ["ETQ001", "WMS010"]},
        ]

        result = normalize_tier3_sets(raw_sets, self.reports)

        self.assertEqual([c["routines"] for c in result], [["ETQ001", "ETQ002"], ["ETQ001", "WMS010"]])

    def test_tier4_uses_tier3_routines_only_when_user_has_the_routine(self):
        tier3_sets = normalize_tier3_sets(
            [{"name": "P_CJ_ETIQUETAS", "routines": ["ETQ001", "ETQ002"]}],
            self.reports,
        )

        tier4 = build_tier4_users(self.reports, tier1_common=set(), tier2_routines_map={}, tier3_sets=tier3_sets)

        by_login = {row["login"]: row for row in tier4}
        self.assertEqual(by_login["joao"]["exclusive_routines"], ["WMS010"])
        self.assertEqual(by_login["maria"]["exclusive_routines"], ["ETQ001", "WMS020"])

    def test_rejects_sets_named_after_departments_or_department_reasons(self):
        raw_sets = [
            {
                "name": "P_CJ_EXPEDICAO",
                "reason": "Usuarios do departamento de Expedicao com rotinas comuns",
                "routines": ["ETQ001", "WMS010"],
            },
            {
                "name": "P_CJ_ETIQUETAS",
                "reason": "Rotinas de impressao e reimpressao de etiquetas",
                "routines": ["ETQ001", "ETQ002"],
            },
        ]

        result = normalize_tier3_sets(raw_sets, self.reports)

        self.assertEqual([group["name"] for group in result], ["P_CJ_ETIQUETAS"])

    def test_permission_superset_covers_required_permissions(self):
        tier3_sets = normalize_tier3_sets(
            [{"name": "P_CJ_ETIQUETAS", "routines": [{"code": "ETQ001", "permissions": ["Visualizar"]}, "ETQ002"]}],
            self.reports,
        )

        self.assertEqual(tier3_sets[0]["users"], ["joao"])
        self.assertEqual(tier3_sets[0]["routines"][0], {"code": "ETQ001", "permissions": ["Visualizar"]})

    def test_missing_required_permission_does_not_cover_user(self):
        tier3_sets = normalize_tier3_sets(
            [{"name": "P_CJ_ETIQUETAS", "routines": [{"code": "ETQ001", "permissions": ["Visualizar", "Alterar"]}, "ETQ002"]}],
            self.reports,
        )

        self.assertEqual(tier3_sets[0]["users"], ["joao"])

    def test_tier4_reports_remaining_permissions_when_partially_covered(self):
        tier3_sets = normalize_tier3_sets(
            [{"name": "P_CJ_ETIQUETAS", "routines": [{"code": "ETQ001", "permissions": ["Visualizar"]}, "ETQ002"]}],
            self.reports,
        )

        tier4 = build_tier4_users(self.reports, tier1_common=set(), tier2_routines_map={}, tier3_sets=tier3_sets)

        by_login = {row["login"]: row for row in tier4}
        self.assertIn("ETQ001: Alterar", by_login["joao"]["exclusive_routines"])

    def test_user_routine_items_include_permissions_for_dashboard(self):
        result = user_routine_items(self.reports[0])

        self.assertEqual(result[0], {"code": "ETQ001", "permissions": ["Alterar", "Visualizar"]})
        self.assertEqual(result[1], {"code": "ETQ002", "permissions": []})

    def test_user_routine_items_ignore_non_effective_routines(self):
        report = {
            "user": "joao",
            "routines_summary": [
                {"routine": "MATA010", "effective_access": "PERMITIDO", "features": {"Visualizar": {"access": "PERMITIDO"}}},
                {"routine": "MATA020", "effective_access": "NAO_PERMITIDO", "features": {"Visualizar": {"access": "PERMITIDO"}}},
                {"routine": "MATA030", "effective_access": "NEGADO", "features": {"Visualizar": {"access": "PERMITIDO"}}},
            ],
        }

        self.assertEqual(user_routine_items(report), [{"code": "MATA010", "permissions": ["Visualizar"]}])

    def test_builds_equivalent_profile_groups_from_same_residual_access(self):
        reports = [
            {
                "user": "maria",
                "user_name": "Maria",
                "user_depto": "CONTROLADORIA",
                "routines_summary": [
                    {"routine": "FINA001", "features": {"Visualizar": {"access": "PERMITIDO"}}},
                    {"routine": "FINA100", "features": {"Visualizar": {"access": "PERMITIDO"}}},
                    {"routine": "FINA200", "features": {"Alterar": {"access": "PERMITIDO"}, "Visualizar": {"access": "PERMITIDO"}}},
                ],
            },
            {
                "user": "vitor",
                "user_name": "Vitor",
                "user_depto": "CONTROLADORIA",
                "routines_summary": [
                    {"routine": "FINA001", "features": {"Visualizar": {"access": "PERMITIDO"}}},
                    {"routine": "FINA100", "features": {"Visualizar": {"access": "PERMITIDO"}}},
                    {"routine": "FINA200", "features": {"Visualizar": {"access": "PERMITIDO"}, "Alterar": {"access": "PERMITIDO"}}},
                ],
            },
            {
                "user": "ana",
                "user_name": "Ana",
                "user_depto": "CONTROLADORIA",
                "routines_summary": [
                    {"routine": "FINA001", "features": {"Visualizar": {"access": "PERMITIDO"}}},
                    {"routine": "FINA100", "features": {"Visualizar": {"access": "PERMITIDO"}}},
                ],
            },
        ]

        groups = build_equivalent_profile_groups(
            reports,
            tier1_common=set(),
            tier2_routines_map={"CONTROLADORIA": {"FINA001"}},
        )

        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["name"], "P_PF_CONTROLADORI_01")
        self.assertEqual(groups[0]["users"], ["maria", "vitor"])
        self.assertEqual(groups[0]["routines"], [
            {"code": "FINA100", "permissions": ["Visualizar"]},
            {"code": "FINA200", "permissions": ["Alterar", "Visualizar"]},
        ])

    def test_equivalent_profile_groups_reduce_tier4_exclusives(self):
        reports = [
            {
                "user": "maria",
                "user_depto": "CONTROLADORIA",
                "routines_summary": [
                    {"routine": "FINA001"},
                    {"routine": "FINA100"},
                    {"routine": "FINA200"},
                ],
            },
            {
                "user": "vitor",
                "user_depto": "CONTROLADORIA",
                "routines_summary": [
                    {"routine": "FINA001"},
                    {"routine": "FINA100"},
                    {"routine": "FINA200"},
                ],
            },
        ]
        tier2 = {"CONTROLADORIA": {"FINA001"}}
        groups = build_equivalent_profile_groups(reports, set(), tier2)

        tier4 = build_tier4_users(reports, tier1_common=set(), tier2_routines_map=tier2, tier3_sets=groups)

        self.assertEqual([row["exclusive_count"] for row in tier4], [0, 0])

    def test_normalize_preserves_equivalent_profile_groups(self):
        raw_sets = [{
            "name": "P_PF_CONTROLADORI_01",
            "type": "equivalent_profile",
            "reason": "Perfil residual identico no departamento CONTROLADORIA",
            "routines": ["ETQ001", "ETQ002"],
        }]

        result = normalize_tier3_sets(raw_sets, self.reports)

        self.assertEqual(result[0]["name"], "P_PF_CONTROLADORI_01")
        self.assertEqual(result[0]["type"], "equivalent_profile")

    def test_normalize_preserves_reuse_metadata_from_loaded_clusters(self):
        raw_sets = [{
            "name": "P_CJ_ETIQUETAS",
            "reason": "Rotinas de etiquetas",
            "routines": ["ETQ001", "ETQ002"],
            "reuses_existing_rule": "P_EXISTENTE",
            "rule_status_label": "Reaproveita P_EXISTENTE",
        }]

        result = normalize_tier3_sets(raw_sets, self.reports)

        self.assertEqual(result[0]["reuses_existing_rule"], "P_EXISTENTE")
        self.assertEqual(result[0]["rule_status_label"], "Reaproveita P_EXISTENTE")

    def test_build_department_analysis_groups_equal_profiles_and_reduces_tier4(self):
        reports = [
            {
                "user": "maria",
                "user_name": "Maria",
                "user_depto": "CONTROLADORIA",
                "routines_summary": [{"routine": "FINA001"}, {"routine": "FINA100"}, {"routine": "FINA200"}],
            },
            {
                "user": "vitor",
                "user_name": "Vitor",
                "user_depto": "CONTROLADORIA",
                "routines_summary": [{"routine": "FINA001"}, {"routine": "FINA100"}, {"routine": "FINA200"}],
            },
            {
                "user": "ana",
                "user_name": "Ana",
                "user_depto": "CONTROLADORIA",
                "routines_summary": [{"routine": "FINA001"}],
            },
        ]

        result = build_department_analysis(reports)

        dept = result["CONTROLADORIA"]
        self.assertEqual(dept["total_users"], 3)
        self.assertEqual(dept["profile_groups"][0]["users"], ["maria", "vitor"])
        by_login = {row["login"]: row for row in dept["tier4_users"]}
        self.assertEqual(by_login["maria"]["exclusive_count"], 0)
        self.assertEqual(by_login["vitor"]["exclusive_count"], 0)
        self.assertEqual(by_login["ana"]["exclusive_count"], 0)

    def test_build_department_analysis_marks_single_user_department_as_ineligible(self):
        reports = [
            {
                "user": "joao",
                "user_name": "Joao",
                "user_depto": "COMERCIAL",
                "routines_summary": [{"routine": "MATA010"}],
            },
        ]

        result = build_department_analysis(reports)

        dept = result["COMERCIAL"]
        self.assertEqual(dept["total_users"], 1)
        self.assertFalse(dept["eligible_for_department_profile"])
        self.assertEqual(dept["min_users_required"], 2)
        self.assertEqual(dept["skip_reason"], "MIN_USERS")

    def test_build_department_analysis_attaches_global_clusters_by_department_users(self):
        reports = [
            {
                "user": "maria",
                "user_name": "Maria",
                "user_depto": "CONTROLADORIA",
                "routines_summary": [{"routine": "FINA001"}],
            },
            {
                "user": "vitor",
                "user_name": "Vitor",
                "user_depto": "CONTROLADORIA",
                "routines_summary": [{"routine": "FINA001"}],
            },
            {
                "user": "ana",
                "user_name": "Ana",
                "user_depto": "COMPRAS",
                "routines_summary": [{"routine": "MATA010"}],
            },
        ]

        global_clusters = [
            {"name": "P_CJ_GLOBAL", "users": ["maria"], "routines": ["FINA100"], "reuses_existing_rule": "P_EXISTENTE"},
            {"name": "P_CJ_COMPRAS", "users": ["ana"], "routines": ["MATA010"]},
        ]

        result = build_department_analysis(reports, global_clusters=global_clusters)

        controladoria = result["CONTROLADORIA"]
        self.assertEqual(controladoria["global_created_sets"][0]["name"], "P_CJ_GLOBAL")
        self.assertEqual(controladoria["global_reused_sets"][0]["reuses_existing_rule"], "P_EXISTENTE")
        compras = result["COMPRAS"]
        self.assertEqual(compras["global_created_sets"][0]["name"], "P_CJ_COMPRAS")

    def test_build_department_common_routines_ignores_single_user_departments_by_default(self):
        reports = [
            {
                "user": "joao",
                "user_name": "Joao",
                "user_depto": "COMERCIAL",
                "routines_summary": [{"routine": "MATA010"}, {"routine": "MATA020"}],
            },
            {
                "user": "maria",
                "user_name": "Maria",
                "user_depto": "COMERCIAL",
                "routines_summary": [{"routine": "MATA010"}],
            },
            {
                "user": "ana",
                "user_name": "Ana",
                "user_depto": "CONTROLADORIA",
                "routines_summary": [{"routine": "FINA001"}],
            },
        ]

        result = build_department_common_routines(reports)

        self.assertEqual(result, {"COMERCIAL": {"MATA010"}})

    def test_build_department_common_routines_can_include_single_user_departments(self):
        reports = [
            {
                "user": "joao",
                "user_name": "Joao",
                "user_depto": "COMERCIAL",
                "routines_summary": [{"routine": "MATA010"}, {"routine": "MATA020"}],
            },
            {
                "user": "maria",
                "user_name": "Maria",
                "user_depto": "COMERCIAL",
                "routines_summary": [{"routine": "MATA010"}],
            },
            {
                "user": "ana",
                "user_name": "Ana",
                "user_depto": "CONTROLADORIA",
                "routines_summary": [{"routine": "FINA001"}],
            },
        ]

        result = build_department_common_routines(reports, min_users=1)

        self.assertEqual(result, {"COMERCIAL": {"MATA010"}, "CONTROLADORIA": {"FINA001"}})

    def test_logs_descartados_with_reason(self):
        from io import StringIO
        from contextlib import redirect_stdout

        raw_sets = [
            {
                "name": "P_CJ_EXPEDICAO",
                "reason": "DEPARTAMENTO",
                "routines": ["ETQ001", "WMS010"],
            },
            {
                "name": "P_CJ_SEM_PERMISSAO",
                "reason": "Conjunto invalido",
                "routines": [
                    {"code": "ETQ001", "permissions": ["Excluir"]},
                    {"code": "WMS010", "permissions": ["Excluir"]},
                ],
            },
            {
                "name": "P_CJ_MISTO_SEM_USERS",
                "reason": "Rotinas existem mas usuarios nao cobrem todas",
                "routines": ["ETQ002", "WMS020"],
            },
        ]

        output = StringIO()
        with redirect_stdout(output):
            normalize_tier3_sets(raw_sets, self.reports)

        text = output.getvalue()
        self.assertIn("[DESCARTADO] P_CJ_EXPEDICAO: baseado em departamento", text)
        self.assertIn("[DESCARTADO] P_CJ_SEM_PERMISSAO", text)
        self.assertIn("permissoes nao cobertas", text)
        self.assertIn("[DESCARTADO] P_CJ_MISTO_SEM_USERS: nenhuma rotina/permissao amarra usuarios ao conjunto", text)


class ExistingRulesTest(unittest.TestCase):
    def test_load_existing_rules_from_conn(self):
        import sqlite3
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("CREATE TABLE SYS_RULES ([RL__ID] TEXT,[RL__CODIGO] TEXT)")
        conn.execute("INSERT INTO SYS_RULES VALUES ('1','P_COMPRAS')")
        conn.execute("INSERT INTO SYS_RULES VALUES ('2','P_VENDAS')")
        conn.execute("CREATE TABLE SYS_RULES_FEATURES ([RL__ID] TEXT,[RL__ROTINA] TEXT,[RL__DESMDEF] TEXT,[RL__ACESSO] TEXT,[RL__MENUOPER] TEXT,[RL__MENUDEF] TEXT)")
        conn.execute("INSERT INTO SYS_RULES_FEATURES VALUES ('1','MATA020','Visualizar','1','2','A020Vis')")
        conn.execute("INSERT INTO SYS_RULES_FEATURES VALUES ('1','MATA020','Alterar','1','4','A020Alt')")
        conn.execute("INSERT INTO SYS_RULES_FEATURES VALUES ('2','MATA030','Visualizar','1','2','A030Vis')")

        result = load_existing_rules(conn)

        self.assertIn("P_COMPRAS", result)
        self.assertEqual(result["P_COMPRAS"]["MATA020"], {"Visualizar", "Alterar"})
        self.assertIn("P_VENDAS", result)
        conn.close()

    def test_load_existing_rules_accepts_alternative_rule_id_columns(self):
        import sqlite3
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("CREATE TABLE SYS_RULES ([RUL_ID] TEXT,[RUL_NAME] TEXT)")
        conn.execute("INSERT INTO SYS_RULES VALUES ('1','P_COMPRAS')")
        conn.execute("CREATE TABLE SYS_RULES_FEATURES ([FET_RUL_ID] TEXT,[FET_FUNCTION] TEXT,[FET_FEATURE] TEXT,[FET_ACCESS] TEXT)")
        conn.execute("INSERT INTO SYS_RULES_FEATURES VALUES ('1','MATA020','Visualizar','1')")

        result = load_existing_rules(conn)

        self.assertEqual(result["P_COMPRAS"]["MATA020"], {"Visualizar"})
        conn.close()

    def test_match_detects_exact_overlap_with_permissions(self):
        existing = {
            "P_COMPRAS": {"MATA020": {"Alterar", "Visualizar"}, "MATA061": {"Visualizar"}},
        }
        routines = [
            {"code": "MATA020", "permissions": ["Alterar", "Visualizar"]},
            {"code": "MATA061", "permissions": ["Visualizar"]},
        ]

        self.assertEqual(match_profile_to_existing_rules(routines, existing), "P_COMPRAS")

    def test_match_returns_none_when_no_rule_covers_every_item(self):
        existing = {"P_COMPRAS": {"MATA020": {"Visualizar"}}}
        routines = [
            {"code": "MATA020", "permissions": ["Alterar", "Visualizar"]},
        ]

        self.assertIsNone(match_profile_to_existing_rules(routines, existing))

    def test_match_handles_string_routines(self):
        existing = {"P_ESTOQUE": {"MATA010": set()}}
        routines = ["MATA010"]

        self.assertEqual(match_profile_to_existing_rules(routines, existing), "P_ESTOQUE")

    def test_match_detects_superset_existing_rule_covering_profile(self):
        existing = {
            "P_FULL": {"MATA010": {"Alterar", "Excluir", "Visualizar"}},
        }
        routines = [
            {"code": "MATA010", "permissions": ["Visualizar"]},
        ]

        self.assertEqual(match_profile_to_existing_rules(routines, existing), "P_FULL")

    def test_department_analysis_tags_profiles_with_reuses_existing_rule(self):
        reports = [
            {
                "user": "maria",
                "user_name": "Maria",
                "user_depto": "CONTROLADORIA",
                "routines_summary": [
                    {"routine": "FINA001", "features": {"Visualizar": {"access": "PERMITIDO"}}},
                    {"routine": "FINA100", "features": {"Visualizar": {"access": "PERMITIDO"}}},
                ],
            },
            {
                "user": "vitor",
                "user_name": "Vitor",
                "user_depto": "CONTROLADORIA",
                "routines_summary": [
                    {"routine": "FINA001", "features": {"Visualizar": {"access": "PERMITIDO"}}},
                    {"routine": "FINA100", "features": {"Visualizar": {"access": "PERMITIDO"}}},
                ],
            },
            {
                "user": "ana",
                "user_name": "Ana",
                "user_depto": "CONTROLADORIA",
                "routines_summary": [
                    {"routine": "FINA001", "features": {"Visualizar": {"access": "PERMITIDO"}}},
                ],
            },
        ]
        existing_rules = {
            "P_CONTROLADORIA": {"FINA100": {"Visualizar"}},
        }

        result = build_department_analysis(reports, existing_rules=existing_rules)

        dept = result["CONTROLADORIA"]
        group = dept["profile_groups"][0]
        self.assertEqual(group["reuses_existing_rule"], "P_CONTROLADORIA")


class Tier3PromptTest(unittest.TestCase):
    def test_prompt_is_routine_catalog_not_department_user_grouping(self):
        from src.llm_categorizer import build_prompt

        prompt = build_prompt([
            {
                "user": "joao",
                "department": "EXPEDICAO",
                "routines": ["ETQ001 - Impressao de etiqueta", "WMS010 - Separacao"],
            }
        ])

        self.assertIn("Catalogo de rotinas", prompt)
        self.assertIn("ETQ001 - Impressao de etiqueta", prompt)
        self.assertNotIn("Departamento: EXPEDICAO", prompt)
        self.assertNotIn("Usuario: joao", prompt)

    def test_prompt_limits_large_routine_catalog(self):
        from src.llm_categorizer import build_prompt

        users_data = []
        for user_idx in range(3):
            routines = []
            for routine_idx in range(4000):
                routines.append(f"ROT{routine_idx:05d} - Descricao longa da rotina {routine_idx}")
            users_data.append({"user": f"u{user_idx}", "routines": routines})

        prompt = build_prompt(users_data, max_routines=500)

        self.assertIn("Catalogo limitado as 500 rotinas", prompt)
        self.assertLess(len(prompt), 70000)

    def test_prompt_includes_permission_profiles(self):
        from src.llm_categorizer import build_prompt

        prompt = build_prompt([
            {"user": "joao", "routines": [{"code": "MATA010", "description": "Cadastro", "permissions": ["Visualizar", "Alterar"]}]},
            {"user": "maria", "routines": [{"code": "MATA010", "description": "Cadastro", "permissions": ["Visualizar"]}]},
        ])

        self.assertIn("MATA010 - Cadastro", prompt)
        self.assertIn("Perfis de permissao", prompt)
        self.assertIn("Alterar, Visualizar: 1 usuarios", prompt)
        self.assertIn("Visualizar: 1 usuarios", prompt)

    def test_suggest_clusters_preserves_routine_permissions(self):
        import src.llm_categorizer as llm_categorizer

        original_api_key = llm_categorizer.llm_cfg.LLM_API_KEY
        original_call_openrouter = llm_categorizer.call_openrouter
        try:
            llm_categorizer.llm_cfg.LLM_API_KEY = "test-key"
            llm_categorizer.call_openrouter = lambda prompt: '{"clusters":[{"name":"P_CJ_PRODUTO","reason":"Cadastro de produto","routines":[{"code":"MATA010","permissions":["Visualizar"]},"MATA035"],"users":[]}],"unclustered":[]}'

            result = llm_categorizer.suggest_clusters([
                {"user": "joao", "routines": [
                    {"code": "MATA010", "description": "Produtos", "permissions": ["Visualizar", "Alterar"]},
                    {"code": "MATA035", "description": "Grupo", "permissions": ["Visualizar"]},
                ]}
            ])
        finally:
            llm_categorizer.call_openrouter = original_call_openrouter
            llm_categorizer.llm_cfg.LLM_API_KEY = original_api_key

        self.assertEqual(
            result["clusters"][0]["routines"],
            [{"code": "MATA010", "permissions": ["Visualizar"]}, "MATA035"],
        )

    def test_suggest_clusters_retries_with_smaller_catalog_when_response_is_truncated(self):
        import src.llm_categorizer as llm_categorizer

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

            result = llm_categorizer.suggest_clusters([
                {"user": "joao", "routines": [
                    {"code": "MATA010", "description": "Pedido de compra", "permissions": ["Visualizar"]},
                    {"code": "MATA020", "description": "Cotacao de compra", "permissions": ["Visualizar"]},
                ]}
            ])
        finally:
            llm_categorizer.call_openrouter = original_call_openrouter
            llm_categorizer.llm_cfg.LLM_API_KEY = original_api_key

        self.assertEqual(len(calls), 2)
        self.assertEqual(result["clusters"][0]["name"], "P_CJ_COMPRAS")

    def test_compact_prompt_requests_fewer_sets_and_routines(self):
        from src.llm_categorizer import build_prompt

        prompt = build_prompt([
            {"user": "joao", "routines": [
                {"code": "MATA010", "description": "Pedido de compra", "permissions": ["Visualizar"]},
                {"code": "MATA020", "description": "Cotacao de compra", "permissions": ["Visualizar"]},
            ]}
        ], max_routines=150)

        self.assertIn("No maximo 12 conjuntos", prompt)
        self.assertIn("No maximo 20 rotinas por conjunto", prompt)

    def test_build_prompt_filters_routines_by_min_users(self):
        from src.llm_categorizer import build_prompt

        prompt = build_prompt([
            {"user": "joao", "routines": [
                {"code": "MATA010", "description": "Compartilhada por 2"},
                {"code": "MATA020", "description": "Compartilhada por 2"},
            ]},
            {"user": "maria", "routines": [
                {"code": "MATA010", "description": "Compartilhada por 2"},
                {"code": "MATA020", "description": "Compartilhada por 2"},
                {"code": "MATA040", "description": "So maria usa"},
            ]},
        ], min_users=2)

        self.assertIn("Catalogo filtrado: apenas rotinas com >= 2 usuarios (2 de 3 rotinas)", prompt)
        self.assertIn("MATA010", prompt)
        self.assertIn("MATA020", prompt)
        self.assertNotIn("MATA040", prompt)

    def test_build_prompt_without_min_users_includes_all(self):
        from src.llm_categorizer import build_prompt

        prompt = build_prompt([
            {"user": "joao", "routines": [{"code": "MATA010"}]},
            {"user": "maria", "routines": [{"code": "MATA010"}, {"code": "MATA040"}]},
        ])

        self.assertNotIn("Catalogo filtrado", prompt)
        self.assertIn("MATA040", prompt)

    def test_prompt_includes_prefix_domain_hints(self):
        from src.llm_categorizer import build_prompt

        prompt = build_prompt([
            {"user": "joao", "routines": [
                {"code": "FINR355", "description": "Relatorio financeiro"},
                {"code": "MATR010", "description": "Relatorio de materiais"},
            ]},
            {"user": "maria", "routines": [
                {"code": "FINR355", "description": "Relatorio financeiro"},
            ]},
        ], min_users=1)

        self.assertIn("DICA DE CLASSIFICACAO POR PREFIXO", prompt)
        self.assertIn("FINR", prompt)
        self.assertIn("MATR", prompt)
        self.assertIn("FISR", prompt)
        self.assertIn("CTBR", prompt)
        self.assertIn("relatorios financeiros", prompt)
        self.assertIn("relatorios de materiais", prompt)
        self.assertIn("relatorios fiscais", prompt)
        self.assertIn("relatorios contabeis", prompt)


class DepartmentCanonicalizationTest(unittest.TestCase):
    def test_canonicalizes_obvious_department_variants_without_llm(self):
        reports = [
            {"user": "joao", "user_depto": " Controladoria ", "routines_summary": []},
            {"user": "maria", "user_depto": "controladOria", "routines_summary": []},
            {"user": "ana", "user_depto": "Controlad\u00f4ria", "routines_summary": []},
        ]

        result = apply_department_canonicalization(reports)

        self.assertEqual([row["user_depto"] for row in result], ["CONTROLADORIA", "CONTROLADORIA", "CONTROLADORIA"])
        self.assertEqual(result[0]["user_depto_original"], " Controladoria ")
        self.assertEqual(result[0]["department_merge_source"], "deterministic")

    def test_applies_llm_alias_only_when_confidence_is_high(self):
        reports = [
            {"user": "joao", "user_depto": "RH", "routines_summary": []},
            {"user": "maria", "user_depto": "Recursos Humanos", "routines_summary": []},
            {"user": "ana", "user_depto": "Recursos Humanos", "routines_summary": []},
        ]

        result = apply_department_canonicalization(
            reports,
            llm_result={
                "groups": [
                    {
                        "canonical": "RECURSOS HUMANOS",
                        "aliases": ["RH", "Recursos Humanos"],
                        "confidence": 0.95,
                    }
                ]
            },
        )

        self.assertEqual([row["user_depto"] for row in result], ["RECURSOS HUMANOS", "RECURSOS HUMANOS", "RECURSOS HUMANOS"])
        self.assertEqual(result[0]["department_merge_source"], "llm")
        self.assertEqual(result[0]["user_depto_normalized"], "RH")

    def test_does_not_apply_llm_alias_below_confidence_threshold(self):
        reports = [
            {"user": "joao", "user_depto": "RH", "routines_summary": []},
            {"user": "maria", "user_depto": "Recursos Humanos", "routines_summary": []},
        ]

        result = apply_department_canonicalization(
            reports,
            llm_result={
                "groups": [
                    {
                        "canonical": "RECURSOS HUMANOS",
                        "aliases": ["RH", "Recursos Humanos"],
                        "confidence": 0.90,
                    }
                ]
            },
        )

        self.assertEqual([row["user_depto"] for row in result], ["RH", "RECURSOS HUMANOS"])
        self.assertEqual(result[0]["department_merge_source"], "deterministic")

    def test_build_department_analysis_uses_canonical_department_names(self):
        reports = apply_department_canonicalization([
            {
                "user": "joao",
                "user_name": "Joao",
                "user_depto": "RH",
                "routines_summary": [{"routine": "FINA001"}],
            },
            {
                "user": "maria",
                "user_name": "Maria",
                "user_depto": "Recursos Humanos",
                "routines_summary": [{"routine": "FINA001"}],
            },
        ], llm_result={
            "groups": [
                {
                    "canonical": "RECURSOS HUMANOS",
                    "aliases": ["RH", "Recursos Humanos"],
                    "confidence": 0.95,
                }
            ]
        })

        result = build_department_analysis(reports)

        self.assertIn("RECURSOS HUMANOS", result)
        self.assertEqual(result["RECURSOS HUMANOS"]["total_users"], 2)
        self.assertNotIn("RH", result)


if __name__ == "__main__":
    unittest.main()
