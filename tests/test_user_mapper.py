import unittest

from src.user_mapper import UserMapper


class FakeUserMapper(UserMapper):
    def __init__(self, menu_tree=None, groups=None, group_privileges=None, direct_privileges=None, acbrowse=None, access_codes=None):
        super().__init__({}, None)
        self._menu_tree = menu_tree or []
        self._groups = groups or []
        self._group_privileges = group_privileges or {}
        self._direct_privileges = direct_privileges or {}
        self._acbrowse = acbrowse or {}
        self._access_codes = access_codes or []

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


if __name__ == "__main__":
    unittest.main()
