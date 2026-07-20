import unittest

from src.consolidated_inventory import build_consolidated_inventory


class ConsolidatedInventoryTest(unittest.TestCase):
    def setUp(self):
        self.reports = [
            {
                "user": "joao",
                "user_id": "000001",
                "user_name": "Joao",
                "user_depto": "RH",
                "routines_summary": [
                    {
                        "routine": "TAFA062",
                        "description": "Apur. Impostos",
                        "features": {
                            "Visualizar": {"access": "PERMITIDO", "access_raw": "1", "menu_oper": 2, "menu_def": "A062VIS"},
                            "Alterar": {"access": "PERMITIDO", "access_raw": "1", "menu_oper": 4, "menu_def": "A062ALT"},
                        },
                    },
                ],
            },
            {
                "user": "maria",
                "user_id": "000002",
                "user_name": "Maria",
                "user_depto": "RH",
                "routines_summary": [
                    {"routine": "TAFA062", "description": "Apur. Impostos", "features": {}},
                ],
            },
            {
                "user": "ana",
                "user_id": "000003",
                "user_name": "Ana",
                "user_depto": "FISCAL",
                "routines_summary": [
                    {"routine": "MATA010", "description": "Produtos", "features": {}},
                ],
            },
        ]

        self.existing_rules = {
            "P_TAF_RH": {"TAFA062": {"Visualizar"}},
            "P_RH": {"TAFA062": {"Visualizar", "Alterar"}},
            "P_COMPRAS": {"MATA110": set()},
        }

        self.existing_links = {
            "P_TAF_RH": {
                "linked_users": [{"user_id": "000001", "login": "joao"}],
                "linked_groups": [{"group_id": "10", "group_name": "RH"}],
            },
            "P_RH": {
                "linked_users": [{"user_id": "000001", "login": "joao"}, {"user_id": "000002", "login": "maria"}],
                "linked_groups": [],
            },
        }

        self.tier1_routines = set()
        self.tier2_routines = {"RH": {"TAFA062"}}
        self.tier3_routines = {
            "P_CJ_APURACAO": {
                "routines": [{"code": "TAFA062", "permissions": ["Visualizar", "Alterar"]}],
                "members": ["joao", "maria"],
                "reuses_existing_rule": "P_RH",
            },
            "P_CJ_NOVO": {
                "routines": [{"code": "MATA010", "permissions": []}],
                "members": ["ana"],
            },
        }
        self.tier4_routines = {}

    def _reports(self):
        return [dict(r) for r in self.reports]

    def test_inventory_includes_all_existing_rules_even_unused(self):
        result = build_consolidated_inventory(
            self._reports(), self.existing_rules, self.existing_links,
            self.tier1_routines, self.tier2_routines, self.tier3_routines, self.tier4_routines,
        )

        rule_names = {rule["rule_name"] for rule in result["rules"]}
        self.assertIn("P_TAF_RH", rule_names)
        self.assertIn("P_RH", rule_names)
        self.assertIn("P_COMPRAS", rule_names)

    def test_existing_rule_without_action_is_marked_as_maintain(self):
        result = build_consolidated_inventory(
            self._reports(), self.existing_rules, self.existing_links,
            self.tier1_routines, self.tier2_routines, self.tier3_routines, self.tier4_routines,
        )

        rule = next(r for r in result["rules"] if r["rule_name"] == "P_COMPRAS")
        self.assertEqual(rule["source"], "EXISTENTE")
        self.assertEqual(rule["action"], "MANTER")

    def test_new_tier_rule_is_marked_as_create(self):
        result = build_consolidated_inventory(
            self._reports(), self.existing_rules, self.existing_links,
            self.tier1_routines, self.tier2_routines, self.tier3_routines, self.tier4_routines,
        )

        rule = next(r for r in result["rules"] if r["rule_name"] == "P_CJ_NOVO")
        self.assertEqual(rule["source"], "NOVO")
        self.assertEqual(rule["action"], "CRIAR")

    def test_reused_rule_marks_features_as_existing_or_missing(self):
        result = build_consolidated_inventory(
            self._reports(), self.existing_rules, self.existing_links,
            self.tier1_routines, self.tier2_routines, self.tier3_routines, self.tier4_routines,
        )

        rule = next(r for r in result["rules"] if r["rule_name"] == "P_RH")
        routine = next(rt for rt in rule["routines"] if rt["routine"] == "TAFA062")
        features_by_name = {f["feature"]: f for f in routine["features"]}
        self.assertEqual(features_by_name["Visualizar"]["status"], "EXISTENTE")
        self.assertEqual(features_by_name["Alterar"]["status"], "EXISTENTE")
        self.assertEqual(rule["action"], "MANTER")

    def test_existing_rule_truly_covers_all_required_permissions(self):
        result = build_consolidated_inventory(
            self._reports(), self.existing_rules, self.existing_links,
            self.tier1_routines, self.tier2_routines, self.tier3_routines, self.tier4_routines,
        )

        rule = next(r for r in result["rules"] if r["rule_name"] == "P_RH")
        self.assertFalse(rule["has_excess"])

    def test_tier2_department_rule_is_marked_as_new(self):
        result = build_consolidated_inventory(
            self._reports(), {"P_TAF_RH": {"TAFA062": {"Visualizar"}}}, self.existing_links,
            self.tier1_routines, self.tier2_routines, self.tier3_routines, self.tier4_routines,
        )

        p_rh = next((r for r in result["rules"] if r["rule_name"] == "P_RH"), None)
        self.assertIsNotNone(p_rh, "P_RH deve existir como regra do departamento RH")
        self.assertEqual(p_rh["source"], "NOVO")
        self.assertEqual(p_rh["action"], "CRIAR")

    def test_deleted_bindings_list_is_initially_empty(self):
        result = build_consolidated_inventory(
            self._reports(), self.existing_rules, self.existing_links,
            self.tier1_routines, self.tier2_routines, self.tier3_routines, self.tier4_routines,
        )

        self.assertEqual(result["deleted_bindings"], [])

    def test_tier2_rule_merges_into_existing_rule_instead_of_duplicating(self):
        existing = {"P_RH": {"TAFA062": {"Visualizar", "Alterar"}}}
        links = {"P_RH": {"linked_users": [{"user_id": "000001", "login": "joao"}], "linked_groups": []}}
        result = build_consolidated_inventory(
            self._reports(), existing, links,
            self.tier1_routines, self.tier2_routines, self.tier3_routines, self.tier4_routines,
        )

        rh_rules = [r for r in result["rules"] if r["rule_name"] == "P_RH"]
        self.assertEqual(len(rh_rules), 1, "P_RH nao deve aparecer duplicada")
        rule = rh_rules[0]
        self.assertEqual(rule["source"], "EXISTENTE")
        self.assertIn(rule["action"], ("MANTER", "COMPLEMENTAR"))


if __name__ == "__main__":
    unittest.main()
