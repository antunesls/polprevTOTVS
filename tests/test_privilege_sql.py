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
        {"COLUMN_NAME": "RL__ID", "CHARACTER_MAXIMUM_LENGTH": None},
        {"COLUMN_NAME": "RL__CODIGO", "CHARACTER_MAXIMUM_LENGTH": 20},
        {"COLUMN_NAME": "RL__DESCRI", "CHARACTER_MAXIMUM_LENGTH": 60},
        {"COLUMN_NAME": "RUL_TYPE", "CHARACTER_MAXIMUM_LENGTH": 1},
    ],
    "SYS_RULES_FEATURES": [
        {"COLUMN_NAME": "RL__ITEM", "CHARACTER_MAXIMUM_LENGTH": None},
        {"COLUMN_NAME": "RL__ID", "CHARACTER_MAXIMUM_LENGTH": None},
        {"COLUMN_NAME": "RL__ROTINA", "CHARACTER_MAXIMUM_LENGTH": 10},
        {"COLUMN_NAME": "RL__DESMDEF", "CHARACTER_MAXIMUM_LENGTH": 40},
        {"COLUMN_NAME": "RL__ACESSO", "CHARACTER_MAXIMUM_LENGTH": 1},
        {"COLUMN_NAME": "RL__MENUOPER", "CHARACTER_MAXIMUM_LENGTH": None},
        {"COLUMN_NAME": "RL__MENUDEF", "CHARACTER_MAXIMUM_LENGTH": 20},
    ],
    "SYS_RULES_TRANSACT": [
        {"COLUMN_NAME": "RL__ID", "CHARACTER_MAXIMUM_LENGTH": None},
        {"COLUMN_NAME": "RL__ROTINA", "CHARACTER_MAXIMUM_LENGTH": 10},
        {"COLUMN_NAME": "RL__DESROT", "CHARACTER_MAXIMUM_LENGTH": 40},
        {"COLUMN_NAME": "RL__ACESSO", "CHARACTER_MAXIMUM_LENGTH": 1},
        {"COLUMN_NAME": "RL__CHKSUM", "CHARACTER_MAXIMUM_LENGTH": 32},
        {"COLUMN_NAME": "D_E_L_E_T_", "CHARACTER_MAXIMUM_LENGTH": 1},
    ],
    "SYS_RULES_USR_RULES": [
        {"COLUMN_NAME": "USER_ID", "CHARACTER_MAXIMUM_LENGTH": None},
        {"COLUMN_NAME": "USR_RL_ID", "CHARACTER_MAXIMUM_LENGTH": None},
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

    def test_generate_sql_truncates_transact_description_to_column_size(self):
        report = build_report()
        report["routines_summary"][0]["description"] = "Movimentos Bancarios - Agrupado por Bancos"
        generator = FakePrivilegeGenerator(report, SCHEMA)

        sql = generator.generate_sql("P_AUTO_TESTE")

        self.assertIn("'Movimentos Bancarios - Agrupado por Banc'", sql)
        self.assertNotIn("'Movimentos Bancarios - Agrupado por Bancos'", sql)


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
        self.assertIn("VALUES ('000001', 'A00001');", sql)

    def test_organizational_sql_truncates_transact_description_to_column_size(self):
        report = build_report()
        report["routines_summary"][0]["description"] = "Movimentos Bancarios - Agrupado por Bancos"
        report["routines_summary"][0]["has_explicit_privilege"] = False
        reports = [report]

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.organizational_privileges.OUTPUT_DIR", tmpdir):
                generator = FakeOrganizationalPrivilegeGenerator(reports, SCHEMA, "TESTE", conn=None)
                generator.tier1_routines = {"MATA010"}
                generator._generate_sql()

                sql = Path(tmpdir, "TESTE_organizacional.sql").read_text(encoding="utf-8")

        self.assertIn("'Movimentos Bancarios - Agrupado por Banc'", sql)
        self.assertNotIn("'Movimentos Bancarios - Agrupado por Bancos'", sql)

    def test_review_loaded_clusters_marks_reuse_from_existing_rules(self):
        report = build_report()
        reports = [report]
        generator = FakeOrganizationalPrivilegeGenerator(reports, SCHEMA, "TESTE", conn=object())
        generator.reports = reports

        clusters = [{
            "name": "P_CJ_EXISTENTE",
            "routines": [{"code": "MATA010", "permissions": ["Visualizar"]}],
            "users": ["usr001"],
        }]

        with patch("src.tier3.load_existing_rules", return_value={"P_EXISTENTE": {"MATA010": {"Visualizar"}}}):
            generator._review_llm_clusters(clusters, auto_accept=True)

        self.assertEqual(generator.tier3_routines["P_CJ_EXISTENTE"]["reuses_existing_rule"], "P_EXISTENTE")


class DeltaSqlTest(unittest.TestCase):
    def test_delta_sql_generates_inserts_for_new_rules_only(self):
        inventory = {
            "rules": [
                {
                    "rule_id": None, "rule_name": "P_NOVO", "rule_description": "Nova regra",
                    "source": "NOVO", "tier": "TIER3", "action": "CRIAR", "has_excess": False,
                    "users": [{"user_id": "000001", "login": "usr001"}],
                    "groups": [],
                    "routines": [
                        {
                            "routine": "MATA010", "description": "Produtos",
                            "features": [
                                {"feature": "Visualizar", "access": "1", "menu_oper": 2, "menu_def": "A010VIS", "status": "FALTANTE"}
                            ],
                            "status": "FALTANTE",
                        }
                    ],
                }
            ],
            "deleted_bindings": [],
        }

        from src.organizational_privileges import generate_delta_sql
        sql = generate_delta_sql(inventory, SCHEMA, "TESTE")

        self.assertIn("INSERT INTO SYS_RULES (", sql)
        self.assertIn("P_NOVO", sql)
        self.assertIn("INSERT INTO SYS_RULES_FEATURES", sql)
        self.assertIn("INSERT INTO SYS_RULES_TRANSACT", sql)
        self.assertIn("INSERT INTO SYS_RULES_USR_RULES", sql)

    def test_delta_sql_skips_maintain_rules(self):
        inventory = {
            "rules": [
                {
                    "rule_id": None, "rule_name": "P_MANTER", "rule_description": "",
                    "source": "EXISTENTE", "tier": "EXISTENTE", "action": "MANTER", "has_excess": False,
                    "users": [], "groups": [], "routines": [],
                }
            ],
            "deleted_bindings": [],
        }

        from src.organizational_privileges import generate_delta_sql
        sql = generate_delta_sql(inventory, SCHEMA, "TESTE")

        self.assertIn("Regra existente sem alteracoes", sql)
        self.assertNotIn("INSERT INTO SYS_RULES (", sql)

    def test_delta_sql_generates_only_complement_for_partial_rules(self):
        inventory = {
            "rules": [
                {
                    "rule_id": "A00001", "rule_name": "P_PARCIAL", "rule_description": "",
                    "source": "EXISTENTE", "tier": "TIER3", "action": "COMPLEMENTAR", "has_excess": False,
                    "users": [{"user_id": "000002", "login": "maria"}],
                    "groups": [],
                    "routines": [
                        {
                            "routine": "MATA010", "description": "Produtos",
                            "features": [
                                {"feature": "Visualizar", "access": "1", "menu_oper": 2, "menu_def": "A010VIS", "status": "EXISTENTE"},
                                {"feature": "Alterar", "access": "1", "menu_oper": 4, "menu_def": "A010ALT", "status": "FALTANTE"},
                            ],
                            "status": "PARCIAL",
                        }
                    ],
                }
            ],
            "deleted_bindings": [],
        }

        from src.organizational_privileges import generate_delta_sql
        sql = generate_delta_sql(inventory, SCHEMA, "TESTE")

        self.assertNotIn("INSERT INTO SYS_RULES (", sql)
        self.assertIn("REGRA EXISTENTE: P_PARCIAL", sql)
        self.assertIn("INSERT INTO SYS_RULES_FEATURES", sql)
        self.assertIn("INSERT INTO SYS_RULES_USR_RULES", sql)

    def test_delta_sql_generates_soft_deletes_with_warning(self):
        inventory = {
            "rules": [
                {
                    "rule_id": "A00001", "rule_name": "P_REMOVIDA", "rule_description": "",
                    "source": "EXISTENTE", "tier": "TIER3", "action": "MANTER", "has_excess": False,
                    "users": [], "groups": [], "routines": [],
                }
            ],
            "deleted_bindings": [
                {"rule_name": "P_REMOVIDA", "user_id": "000001", "table": "SYS_RULES_USR_RULES"}
            ],
        }

        from src.organizational_privileges import generate_delta_sql
        sql = generate_delta_sql(inventory, SCHEMA, "TESTE")

        self.assertIn("SOFT DELETE", sql)
        self.assertIn("ATENCAO", sql)
        self.assertIn("D_E_L_E_T_", sql)


if __name__ == "__main__":
    unittest.main()
