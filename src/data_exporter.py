import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import SCHEMA_TABLES, OUTPUT_DIR
from src.discovery import discover_columns_for_tables, get_columns_list

TABLES_TO_EXPORT = [
    ("SYS_USR", "D_E_L_E_T_ = ' '"),
    ("SYS_USR_MODULE", "D_E_L_E_T_ = ' '"),
    ("SYS_USR_GROUPS", "D_E_L_E_T_ = ' '"),
    ("SYS_USR_ACCESS", "D_E_L_E_T_ = ' '"),
    ("SYS_GRP_GROUP", None),
    ("SYS_RULES", None),
    ("SYS_RULES_FEATURES", "D_E_L_E_T_ = ' '"),
    ("SYS_RULES_TRANSACT", "D_E_L_E_T_ = ' '"),
    ("SYS_RULES_BUTTONS", None),
    ("SYS_RULES_GRP_RULES", None),
    ("SYS_RULES_USR_RULES", None),
    ("MPMENU_MENU", "D_E_L_E_T_ = ' '"),
    ("MPMENU_ITEM", "D_E_L_E_T_ = ' ' AND I_STATUS = '1'"),
    ("MPMENU_FUNCTION", None),
    ("MPMENU_I18N", "D_E_L_E_T_ = ' '"),
    ("MP_SYSTEM_PROFILE", "P_TYPE = 'ACBROWSE' AND D_E_L_E_T_ = ' '"),
]


def generate_export_sql(schema):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    lines = []
    lines.append("-- ==============================================")
    lines.append("-- polprevTOTVS - Script de exportacao de dados")
    lines.append("-- Execute este script no SQL Server Management Studio")
    lines.append("-- Salve o resultado (coluna unica JSON) como output/export.json")
    lines.append("-- ==============================================")
    lines.append("")
    lines.append("SELECT ")

    subqueries = []
    for table, filter_clause in TABLES_TO_EXPORT:
        cols = get_columns_list(schema, table)
        if not cols:
            subqueries.append(f"  NULL AS {table}")
            continue

        cols_escaped = ", ".join(f"[{c}]" for c in cols)

        if filter_clause:
            sql = f"  (SELECT {cols_escaped} FROM {table} WHERE {filter_clause} FOR JSON AUTO) AS {table}"
        else:
            sql = f"  (SELECT {cols_escaped} FROM {table} FOR JSON AUTO) AS {table}"

        subqueries.append(sql)

    lines.append(",\n".join(subqueries))
    lines.append("FOR JSON PATH, WITHOUT_ARRAY_WRAPPER")

    sql_content = "\n".join(lines) + "\n"

    filepath = os.path.join(OUTPUT_DIR, "export.sql")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(sql_content)

    return filepath
