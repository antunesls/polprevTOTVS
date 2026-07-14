import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.config import SCHEMA_TABLES
from src.diagnose_columns import CANDIDATES
from src.organizational_privileges import OrganizationalPrivilegeGenerator
from src.privilege_generator import PrivilegeGenerator


SCHEMA = {
    "SYS_RULES": [
        {"COLUMN_NAME": "RL__ID"},
        {"COLUMN_NAME": "RL__CODIGO"},
        {"COLUMN_NAME": "RL__DESCRI"},
        {"COLUMN_NAME": "RUL_TYPE"},
    ],
    "SYS_RULES_FEATURES": [
        {"COLUMN_NAME": "RL__ITEM"},
        {"COLUMN_NAME": "RL__ID"},
        {"COLUMN_NAME": "RL__ROTINA"},
        {"COLUMN_NAME": "RL__DESMDEF"},
        {"COLUMN_NAME": "RL__ACESSO"},
        {"COLUMN_NAME": "RL__MENUOPER"},
        {"COLUMN_NAME": "RL__MENUDEF"},
    ],
    "SYS_RULES_TRANSACT": [
        {"COLUMN_NAME": "RL__ID"},
        {"COLUMN_NAME": "RL__ROTINA"},
        {"COLUMN_NAME": "RL__DESROT"},
        {"COLUMN_NAME": "RL__ACESSO"},
        {"COLUMN_NAME": "RL__CHKSUM"},
        {"COLUMN_NAME": "D_E_L_E_T_"},
    ],
    "SYS_RULES_USR_RULES": [
        {"COLUMN_NAME": "USER_ID"},
        {"COLUMN_NAME": "USR_RL_ID"},
    ],
}


def build_report():
    return {
        "user": "usr001",
        "user_id": "000001",
        "user_depto": "CONTROLADORIA",
        "total_routines": 1,
        "routines_summary": [
            {
                "routine": "MATA010",
                "description": "Produtos",
                "has_explicit_privilege": True,
                "features": {
                    "Visualizar": {
                        "access": "PERMITIDO",
                        "access_raw": "1",
                        "menu_oper": 2,
                        "menu_def": "A010VIS",
                    }
                },
            }
        ],
    }


class FakePrivilegeGenerator(PrivilegeGenerator):
    def _get_max_id(self, table, pk_col):
        return 0


class FakeOrganizationalPrivilegeGenerator(OrganizationalPrivilegeGenerator):
    def _get_max_id(self, table, pk_col):
        return 0


class PrivilegeSqlGenerationTest(unittest.TestCase):
    def test_generate_sql_uses_alphanumeric_rule_id_and_transact_rows(self):
        generator = FakePrivilegeGenerator(build_report(), SCHEMA)

        sql = generator.generate_sql("P_AUTO_TESTE")

        self.assertIn("VALUES ('A00001'", sql)
        self.assertIn("INSERT INTO SYS_RULES_TRANSACT", sql)
        self.assertIn("'MATA010'", sql)
        self.assertIn("'Produtos'", sql)
        self.assertIn("'A00001'", sql)


class SchemaDiscoveryTest(unittest.TestCase):
    def test_schema_candidates_include_rules_transact(self):
        self.assertIn("SYS_RULES_TRANSACT", SCHEMA_TABLES)
        self.assertIn("SYS_RULES_TRANSACT", CANDIDATES)
        self.assertIn("RL__ID", CANDIDATES["SYS_RULES_TRANSACT"]["rules_transact_rul"])


class OrganizationalSqlTest(unittest.TestCase):
    def test_organizational_sql_reuses_same_alphanumeric_rule_id_everywhere(self):
        report = build_report()
        report["routines_summary"][0]["has_explicit_privilege"] = False
        reports = [report]

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.organizational_privileges.OUTPUT_DIR", tmpdir):
                generator = FakeOrganizationalPrivilegeGenerator(reports, SCHEMA, "TESTE", conn=None)
                generator.tier1_routines = {"MATA010"}
                generator._generate_sql()

                sql = Path(tmpdir, "TESTE_organizacional.sql").read_text(encoding="utf-8")

        self.assertIn("'A00001'", sql)
        self.assertIn("INSERT INTO SYS_RULES_TRANSACT", sql)
        self.assertIn("VALUES ('usr001', 'A00001');", sql)


if __name__ == "__main__":
    unittest.main()
