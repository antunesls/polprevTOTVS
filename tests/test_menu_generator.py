import unittest

from src.menu_generator import CanonicalMenuGenerator


SCHEMA = {
    "MPMENU_MENU": [
        {"COLUMN_NAME": "M_ID", "CHARACTER_MAXIMUM_LENGTH": None},
        {"COLUMN_NAME": "M_NAME", "CHARACTER_MAXIMUM_LENGTH": 30},
        {"COLUMN_NAME": "M_MODULE", "CHARACTER_MAXIMUM_LENGTH": 15},
        {"COLUMN_NAME": "D_E_L_E_T_", "CHARACTER_MAXIMUM_LENGTH": 1},
    ],
    "MPMENU_ITEM": [
        {"COLUMN_NAME": "I_ID", "CHARACTER_MAXIMUM_LENGTH": None},
        {"COLUMN_NAME": "I_ID_MENU", "CHARACTER_MAXIMUM_LENGTH": None},
        {"COLUMN_NAME": "I_ID_FUNC", "CHARACTER_MAXIMUM_LENGTH": None},
        {"COLUMN_NAME": "I_FATHER", "CHARACTER_MAXIMUM_LENGTH": None},
        {"COLUMN_NAME": "I_TP_MENU", "CHARACTER_MAXIMUM_LENGTH": 1},
        {"COLUMN_NAME": "I_STATUS", "CHARACTER_MAXIMUM_LENGTH": 1},
        {"COLUMN_NAME": "I_ACCESS", "CHARACTER_MAXIMUM_LENGTH": 10},
        {"COLUMN_NAME": "D_E_L_E_T_", "CHARACTER_MAXIMUM_LENGTH": 1},
    ],
    "MPMENU_FUNCTION": [
        {"COLUMN_NAME": "F_ID", "CHARACTER_MAXIMUM_LENGTH": None},
        {"COLUMN_NAME": "F_FUNCTION", "CHARACTER_MAXIMUM_LENGTH": 10},
    ],
    "MPMENU_I18N": [
        {"COLUMN_NAME": "N_PAREN_ID", "CHARACTER_MAXIMUM_LENGTH": None},
        {"COLUMN_NAME": "N_LANG", "CHARACTER_MAXIMUM_LENGTH": 1},
        {"COLUMN_NAME": "N_DESC", "CHARACTER_MAXIMUM_LENGTH": 60},
        {"COLUMN_NAME": "D_E_L_E_T_", "CHARACTER_MAXIMUM_LENGTH": 1},
    ],
    "SYS_USR_MODULE": [
        {"COLUMN_NAME": "USR_ID", "CHARACTER_MAXIMUM_LENGTH": None},
        {"COLUMN_NAME": "USR_MODULO", "CHARACTER_MAXIMUM_LENGTH": 15},
        {"COLUMN_NAME": "USR_ACESSO", "CHARACTER_MAXIMUM_LENGTH": 1},
        {"COLUMN_NAME": "D_E_L_E_T_", "CHARACTER_MAXIMUM_LENGTH": 1},
    ],
}


def build_reports():
    return [
        {
            "user": "usr001",
            "user_id": "000001",
            "routines_summary": [
                {"routine": "MATA010", "description": "Produtos", "module": "SIGACOM"},
                {"routine": "MATA020", "description": "Clientes", "module": "SIGACOM"},
                {"routine": "MATA010", "description": "Produtos", "module": "SIGACOM"},
                {"routine": "FINA010", "description": "Titulos", "module": "SIGAFIN"},
            ],
        },
        {
            "user": "usr002",
            "user_id": "000002",
            "routines_summary": [
                {"routine": "MATA020", "description": "Clientes", "module": "SIGACOM"},
                {"routine": "MATA030", "description": "Fornecedores", "module": "SIGACOM"},
                {"routine": "FINA010", "description": "Titulos", "module": "SIGAFIN"},
            ],
        },
    ]


class FakeCanonicalMenuGenerator(CanonicalMenuGenerator):
    def _get_max_id(self, table, pk_col):
        return 0

    def _load_existing_function_ids(self):
        return {"MATA010": 10}


class CanonicalMenuGeneratorTest(unittest.TestCase):
    def test_build_module_catalog_groups_routines_and_users(self):
        generator = FakeCanonicalMenuGenerator(build_reports(), SCHEMA)

        catalog = generator.build_module_catalog()

        self.assertEqual(["SIGACOM", "SIGAFIN"], sorted(catalog.keys()))
        self.assertEqual(["000001", "000002"], catalog["SIGACOM"]["user_ids"])
        self.assertEqual(["MATA010", "MATA020", "MATA030"], [r["routine"] for r in catalog["SIGACOM"]["routines"]])
        self.assertEqual(["FINA010"], [r["routine"] for r in catalog["SIGAFIN"]["routines"]])

    def test_generate_sql_replace_mode_creates_menu_and_replaces_user_links(self):
        generator = FakeCanonicalMenuGenerator(build_reports(), SCHEMA)

        sql = generator.generate_sql(link_mode="replace")

        self.assertIn("SIGACOM_CANONICO", sql)
        self.assertIn("INSERT INTO MPMENU_MENU", sql)
        self.assertIn("INSERT INTO MPMENU_ITEM", sql)
        self.assertIn("INSERT INTO MPMENU_I18N", sql)
        self.assertIn("DELETE FROM SYS_USR_MODULE WHERE USR_ID = '000001' AND USR_MODULO = 'SIGACOM'", sql)
        self.assertIn("DELETE FROM SYS_USR_MODULE WHERE USR_ID = '000002' AND USR_MODULO = 'SIGACOM'", sql)
        self.assertIn("VALUES ('000001', 'SIGACOM', 'T', ' ')", sql)
        self.assertIn("VALUES ('000002', 'SIGACOM', 'T', ' ')", sql)

    def test_generate_sql_add_mode_preserves_existing_links(self):
        generator = FakeCanonicalMenuGenerator(build_reports(), SCHEMA)

        sql = generator.generate_sql(link_mode="add")

        self.assertNotIn("DELETE FROM SYS_USR_MODULE", sql)
        self.assertIn("IF NOT EXISTS (SELECT 1 FROM SYS_USR_MODULE WHERE USR_ID = '000001' AND USR_MODULO = 'SIGACOM')", sql)

    def test_generate_sql_reuses_existing_function_id_and_creates_missing_ones(self):
        generator = FakeCanonicalMenuGenerator(build_reports(), SCHEMA)

        sql = generator.generate_sql(link_mode="add")

        self.assertNotIn("INSERT INTO MPMENU_FUNCTION (F_ID, F_FUNCTION)\nVALUES (10, 'MATA010');", sql)
        self.assertIn("INSERT INTO MPMENU_FUNCTION (F_ID, F_FUNCTION)", sql)
        self.assertIn("VALUES (1, 'MATA020');", sql)
        self.assertIn("VALUES (2, 'MATA030');", sql)

    def test_generate_sql_handles_hex_function_ids(self):
        class HexIdGenerator(CanonicalMenuGenerator):
            def _get_max_id(self, table, pk_col):
                return 0

            def _load_existing_function_ids(self):
                return {"MATA010": "2DEB775480FBED11812CB82A72DC1A84"}

        generator = HexIdGenerator(build_reports(), SCHEMA)
        sql = generator.generate_sql(link_mode="add")

        self.assertIn("INSERT INTO MPMENU_FUNCTION (F_ID, F_FUNCTION)", sql)
        self.assertIn("'2DEB775480FBED11812CB82A72DC1A84'", sql)
        self.assertNotIn("INSERT INTO MPMENU_FUNCTION (F_ID, F_FUNCTION)\nVALUES (1, 'MATA020');", sql)


if __name__ == "__main__":
    unittest.main()
