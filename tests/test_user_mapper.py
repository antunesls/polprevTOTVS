import unittest
from unittest.mock import patch

from src.user_mapper import UserMapper


class FakeUserMapper(UserMapper):
    def __init__(self, menu_tree=None, groups=None, group_privileges=None, direct_privileges=None, acbrowse=None, access_codes=None, existing_privilege_sets=None):
        super().__init__({}, None)
        self._menu_tree = menu_tree or []
        self._groups = groups or []
        self._group_privileges = group_privileges or {}
        self._direct_privileges = direct_privileges or {}
        self._acbrowse = acbrowse or {}
        self._access_codes = access_codes or []
        self._existing_privilege_sets = existing_privilege_sets or []

    def find_user(self, login):
        return {"id": "000001", "login": login, "depto": "TI", "name": "Usuario Teste"}

    def map_menu_modules(self, user_id):
        return (["SIGACOM"], "USR_MODULO")

    def map_menu_tree(self, menu_ids, join_column=None):
        return self._menu_tree

    def map_system_profile(self, user_id):
        return self._acbrowse

    def map_user_groups(self, user_id):
        return self._groups

    def map_group_privileges(self, group_ids):
        return self._group_privileges

    def map_user_privileges_direct(self, user_id):
        return self._direct_privileges

    def map_user_access_codes(self, user_id):
        return self._access_codes

    def map_existing_privilege_sets(self):
        return self._existing_privilege_sets


class TrackingUserMapper(FakeUserMapper):
    def __init__(self, reports_by_login, routine_menu_map):
        super().__init__()
        self._reports_by_login = reports_by_login
        self._routine_menu_map = routine_menu_map

    def resolve_col(self, table, candidates):
        mapping = {
            ("MPMENU_FUNCTION", "F_ID"): "F_ID",
            ("MPMENU_FUNCTION", "F_FUNCTION"): "F_FUNCTION",
            ("MPMENU_ITEM", "I_ID_MENU"): "I_ID_MENU",
            ("MPMENU_ITEM", "I_ID_FUNC"): "I_ID_FUNC",
            ("SYS_USR_MODULE", "USR_ID"): "USR_ID",
            ("SYS_USR_MODULE", "USR_ARQMENU"): "USR_ARQMENU",
        }
        for candidate in candidates:
            key = (table, candidate)
            if key in mapping:
                return mapping[key]
        return candidates[0]

    def build_full_report(self, login):
        return self._reports_by_login[login]


class SchemaAwareUserMapper(UserMapper):
    def __init__(self):
        super().__init__({}, object())

    def resolve_col(self, table, candidates):
        return candidates[0]


class UserMapperBlockedUsersTest(unittest.TestCase):
    def test_list_non_blocked_users_excludes_msblql_blocked_and_deleted_users(self):
        mapper = SchemaAwareUserMapper()

        def fake_fetch_dicts(conn, query, params=()):
            self.assertIn("USR_MSBLQL <> ?", query)
            self.assertIn("D_E_L_E_T_ = ?", query)
            self.assertEqual(list(params), ["1", " "])
            return [
                {"USR_ID": "000001", "USR_CODIGO": "joao", "USR_DEPTO": "TI", "USR_NOME": "Joao"},
            ]

        with patch("src.user_mapper.fetch_dicts", side_effect=fake_fetch_dicts):
            users = mapper.list_non_blocked_users()

        self.assertEqual(users, [{"id": "000001", "login": "joao", "depto": "TI", "name": "Joao"}])

    def test_map_routine_users_excludes_blocked_users_before_building_reports(self):
        reports_by_login = {
            "joao": {"user": "joao", "routines_summary": [{"routine": "MATA010", "effective_access": "PERMITIDO"}]},
        }
        mapper = TrackingUserMapper(reports_by_login, {"MATA010": ["SIGACOM"]})
        built_reports = []

        def fake_build_full_report(login):
            built_reports.append(login)
            return reports_by_login[login]

        def fake_fetch_dicts(conn, query, params=()):
            if "FROM MPMENU_FUNCTION" in query:
                return [{"F_ID": "10"}]
            if "FROM MPMENU_ITEM" in query:
                return [{"I_ID_MENU": "SIGACOM"}]
            if "FROM SYS_USR_MODULE" in query:
                return [{"USR_ID": "1"}, {"USR_ID": "2"}]
            if "FROM SYS_USR" in query:
                self.assertIn("USR_MSBLQL <> ?", query)
                self.assertIn("D_E_L_E_T_ = ?", query)
                self.assertEqual(list(params)[-2:], ["1", " "])
                return [{"USR_ID": "1", "USR_CODIGO": "joao"}]
            return []

        with patch("src.user_mapper.fetch_dicts", side_effect=fake_fetch_dicts):
            with patch.object(TrackingUserMapper, "build_full_report", side_effect=fake_build_full_report):
                result = mapper.map_routine_users("MATA010")

        self.assertEqual(result["user_ids"], ["1"])
        self.assertEqual(built_reports, ["joao"])


class UserMapperAccessMatrixTest(unittest.TestCase):
    def test_group_default_requires_explicit_permission(self):
        mapper = FakeUserMapper(
            menu_tree=[
                {
                    "menu_name": "SIGACOM",
                    "module": "COM",
                    "items": [
                        {"item_id": "1", "father_id": "", "function_code": "MATA010", "description": "Produtos", "browse_features": {}},
                        {"item_id": "2", "father_id": "", "function_code": "MATA020", "description": "Fornecedores", "browse_features": {}},
                    ],
                }
            ],
            groups=[{"group_id": "*", "group_name": "*"}],
            group_privileges={
                "MATA010": {
                    "Visualizar": {"access": "1", "rule_name": "DEFAULT_ALLOW", "rule_id": "A1", "menu_oper": 2, "menu_def": "A010VIS"}
                }
            },
        )

        report = mapper.build_full_report("usr001")
        by_routine = {row["routine"]: row for row in report["routines_summary"]}

        self.assertEqual(by_routine["MATA010"]["effective_access"], "PERMITIDO")
        self.assertEqual(by_routine["MATA020"]["effective_access"], "NAO_PERMITIDO")
        self.assertEqual(by_routine["MATA020"]["denial_reason"], "GROUP_DEFAULT")

    def test_denied_privilege_overrides_allowed_privilege(self):
        mapper = FakeUserMapper(
            menu_tree=[
                {
                    "menu_name": "SIGAFAT",
                    "module": "FAT",
                    "items": [
                        {"item_id": "1", "father_id": "", "function_code": "MATA410", "description": "Pedido de Venda", "browse_features": {}},
                    ],
                }
            ],
            group_privileges={
                "MATA410": {
                    "Visualizar": {"access": "1", "rule_name": "ALLOW", "rule_id": "A1", "menu_oper": 2, "menu_def": "A410VIS"}
                }
            },
            direct_privileges={
                "MATA410": {
                    "Visualizar": {"access": "3", "rule_name": "DIRECT_USER", "rule_id": "A2", "menu_oper": 2, "menu_def": "A410VIS"}
                }
            },
        )

        report = mapper.build_full_report("usr001")
        routine = report["routines_summary"][0]

        self.assertEqual(routine["effective_access"], "NEGADO")
        self.assertEqual(routine["features"]["Visualizar"]["access"], "NEGADO")
        self.assertEqual(routine["decision_source"], "DIRECT_USER")

    def test_menu_only_routine_is_not_effectively_allowed(self):
        mapper = FakeUserMapper(
            menu_tree=[
                {
                    "menu_name": "SIGAEST",
                    "module": "EST",
                    "items": [
                        {"item_id": "1", "father_id": "", "function_code": "MATA220", "description": "Saldo", "browse_features": {}},
                    ],
                }
            ]
        )

        report = mapper.build_full_report("usr001")
        routine = report["routines_summary"][0]

        self.assertTrue(routine["in_menu"])
        self.assertEqual(routine["effective_access"], "SEM_REGRA")
        self.assertEqual(routine["denial_reason"], "NO_EXPLICIT_RULE")

    def test_acbrowse_does_not_leak_between_programs(self):
        mapper = FakeUserMapper(
            menu_tree=[
                {
                    "menu_name": "SIGACOM",
                    "module": "COM",
                    "items": [
                        {"item_id": "1", "father_id": "", "function_code": "MATA010", "description": "Cadastros", "browse_features": {}},
                    ],
                },
                {
                    "menu_name": "SIGAFAT",
                    "module": "FAT",
                    "items": [
                        {"item_id": "2", "father_id": "", "function_code": "MATA410", "description": "Cadastros", "browse_features": {}},
                    ],
                },
            ],
            acbrowse={"SIGACOM": {"Cadastros": "D"}},
        )

        report = mapper.build_full_report("usr001")
        by_routine = {row["routine"]: row for row in report["routines_summary"]}

        self.assertTrue(by_routine["MATA010"]["disabled_by_acbrowse"])
        self.assertFalse(by_routine["MATA410"]["disabled_by_acbrowse"])

    def test_map_routine_users_filters_users_without_effective_access(self):
        reports_by_login = {
            "joao": {"user": "joao", "routines_summary": [{"routine": "MATA010", "effective_access": "PERMITIDO"}]},
            "maria": {"user": "maria", "routines_summary": [{"routine": "MATA010", "effective_access": "NAO_PERMITIDO"}]},
        }
        mapper = TrackingUserMapper(reports_by_login, {"MATA010": ["SIGACOM"]})

        def fake_fetch_dicts(conn, query, params=()):
            if "FROM MPMENU_FUNCTION" in query:
                return [{"F_ID": "10"}]
            if "FROM MPMENU_ITEM" in query:
                return [{"I_ID_MENU": "SIGACOM"}]
            if "FROM SYS_USR_MODULE" in query:
                return [{"USR_ID": "1"}, {"USR_ID": "2"}]
            if "FROM SYS_USR" in query:
                return [{"USR_ID": "1", "USR_CODIGO": "joao"}, {"USR_ID": "2", "USR_CODIGO": "maria"}]
            return []

        from unittest.mock import patch

        with patch("src.user_mapper.fetch_dicts", side_effect=fake_fetch_dicts):
            result = mapper.map_routine_users("MATA010")

        self.assertEqual(result["user_ids"], ["1"])

    def test_report_includes_active_sys_usr_access_codes(self):
        mapper = FakeUserMapper(
            menu_tree=[
                {
                    "menu_name": "SIGACOM",
                    "module": "COM",
                    "items": [
                        {"item_id": "1", "father_id": "", "function_code": "MATA010", "description": "Produtos", "browse_features": {}},
                    ],
                }
            ],
            access_codes=[
                {"code": "112", "enabled": True, "description": "Gerar rel. no servidor"},
                {"code": "121", "enabled": True, "description": "Usa impressora no server"},
            ],
        )

        report = mapper.build_full_report("usr001")

        self.assertEqual(report["access_codes"], [
            {"code": "112", "enabled": True, "description": "Gerar rel. no servidor"},
            {"code": "121", "enabled": True, "description": "Usa impressora no server"},
        ])

    def test_report_suggests_partial_reuse_with_missing_permissions(self):
        mapper = FakeUserMapper(
            menu_tree=[
                {
                    "menu_name": "SIGACOM",
                    "module": "COM",
                    "items": [
                        {"item_id": "1", "father_id": "", "function_code": "MATA010", "description": "Produtos", "browse_features": {}},
                    ],
                }
            ],
            group_privileges={
                "MATA010": {
                    "Visualizar": {"access": "1", "rule_name": "P_DESEJADO", "rule_id": "A9", "menu_oper": 2, "menu_def": "A010VIS"},
                    "Alterar": {"access": "1", "rule_name": "P_DESEJADO", "rule_id": "A9", "menu_oper": 4, "menu_def": "A010ALT"},
                }
            },
            existing_privilege_sets=[
                {
                    "rule_id": "A1",
                    "rule_name": "P_EXISTENTE",
                    "linked_users": [{"user_id": "000777", "login": "maria"}],
                    "linked_groups": [{"group_id": "10", "group_name": "COMPRAS"}],
                    "routines": [
                        {
                            "routine": "MATA010",
                            "features": [
                                {"feature": "Visualizar", "access": "1", "menu_oper": 2, "menu_def": "A010VIS"},
                            ],
                        }
                    ],
                }
            ],
        )

        report = mapper.build_full_report("usr001")

        recommendation = report["privilege_recommendations"]["suggested_base_rule"]
        self.assertEqual(recommendation["rule_name"], "P_EXISTENTE")
        self.assertEqual(recommendation["coverage_status"], "PARCIAL")
        self.assertEqual(recommendation["matched_permissions_count"], 1)
        self.assertEqual(recommendation["missing_permissions"], ["MATA010: Alterar"])
        self.assertEqual(recommendation["linked_groups"], [{"group_id": "10", "group_name": "COMPRAS"}])

    def test_report_flags_exact_reuse_with_excess_permissions(self):
        mapper = FakeUserMapper(
            menu_tree=[
                {
                    "menu_name": "SIGACOM",
                    "module": "COM",
                    "items": [
                        {"item_id": "1", "father_id": "", "function_code": "MATA010", "description": "Produtos", "browse_features": {}},
                    ],
                }
            ],
            group_privileges={
                "MATA010": {
                    "Visualizar": {"access": "1", "rule_name": "P_DESEJADO", "rule_id": "A9", "menu_oper": 2, "menu_def": "A010VIS"},
                }
            },
            existing_privilege_sets=[
                {
                    "rule_id": "A1",
                    "rule_name": "P_EXISTENTE_FULL",
                    "linked_users": [{"user_id": "000777", "login": "maria"}],
                    "linked_groups": [],
                    "routines": [
                        {
                            "routine": "MATA010",
                            "features": [
                                {"feature": "Visualizar", "access": "1", "menu_oper": 2, "menu_def": "A010VIS"},
                                {"feature": "Excluir", "access": "1", "menu_oper": 5, "menu_def": "A010DEL"},
                            ],
                        }
                    ],
                }
            ],
        )

        report = mapper.build_full_report("usr001")

        recommendation = report["privilege_recommendations"]["suggested_base_rule"]
        self.assertEqual(recommendation["rule_name"], "P_EXISTENTE_FULL")
        self.assertEqual(recommendation["coverage_status"], "EXATA")
        self.assertTrue(recommendation["has_excess_permissions"])
        self.assertEqual(recommendation["excess_permissions"], ["MATA010: Excluir"])

    def test_build_full_report_ignores_existing_privilege_inventory_failure(self):
        mapper = FakeUserMapper(
            menu_tree=[
                {
                    "menu_name": "SIGACOM",
                    "module": "COM",
                    "items": [
                        {"item_id": "1", "father_id": "", "function_code": "MATA010", "description": "Produtos", "browse_features": {}},
                    ],
                }
            ],
            group_privileges={
                "MATA010": {
                    "Visualizar": {"access": "1", "rule_name": "ALLOW", "rule_id": "A1", "menu_oper": 2, "menu_def": "A010VIS"}
                }
            },
        )

        with patch.object(FakeUserMapper, "map_existing_privilege_sets", side_effect=KeyError("RL__ID")):
            report = mapper.build_full_report("usr001")

        self.assertEqual(report["total_routines"], 1)
        self.assertEqual(report["routines_summary"][0]["effective_access"], "PERMITIDO")
        self.assertEqual(report["existing_privilege_sets"], [])
        self.assertIsNone(report["privilege_recommendations"]["suggested_base_rule"])

    def test_map_user_privileges_direct_reads_rule_id_from_selected_feature_rows(self):
        mapper = SchemaAwareUserMapper()

        def fake_fetch_dicts(conn, query, params=()):
            if "FROM SYS_RULES_USR_RULES" in query:
                return [{"USR_RL_ID": "A1"}]
            if "FROM SYS_RULES WHERE" in query:
                return [{"RL__ID": "A1", "RL__CODIGO": "P_EXISTENTE"}]
            if "FROM SYS_RULES_FEATURES" in query:
                self.assertIn("SELECT RL__ID,", query)
                return [{
                    "RL__ID": "A1",
                    "RL__ROTINA": "MATA010",
                    "RL__DESMDEF": "Visualizar",
                    "RL__ACESSO": "1",
                    "RL__MENUOPER": 2,
                    "RL__MENUDEF": "A010VIS",
                }]
            return []

        with patch("src.user_mapper.fetch_dicts", side_effect=fake_fetch_dicts):
            privileges = mapper.map_user_privileges_direct("000001")

        self.assertEqual(privileges["MATA010"]["Visualizar"]["rule_id"], "A1")
        self.assertEqual(privileges["MATA010"]["Visualizar"]["rule_name"], "P_EXISTENTE")


if __name__ == "__main__":
    unittest.main()
