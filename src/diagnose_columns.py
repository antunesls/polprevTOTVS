import pyodbc
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import DB_CONFIG, SCHEMA_TABLES, OUTPUT_DIR


CANDIDATES = {
    "SYS_USR": {
        "pk": ["USR_ID", "ID"],
        "login_col": ["USR_CODIGO", "USR_LOGIN", "LOGIN", "USR_USERNAME", "USR_COD"],
    },
    "SYS_USR_MODULE": {
        "usr_col": ["USR_ID", "UMD_USR_ID", "USM_USR_ID"],
        "menu_col": ["USR_MODULO", "USR_CODMOD", "UMD_MENU_ID", "MENU_ID", "USM_MENU_ID"],
        "del_col": ["D_E_L_E_T_"],
    },
    "SYS_USR_GROUPS": {
        "usr_col": ["USR_ID", "USG_USR_ID", "USG_USER_ID"],
        "grp_col": ["USR_GRUPO", "USG_GRP_ID", "GRP_ID", "USG_GROUP_ID"],
        "del_col": ["D_E_L_E_T_"],
    },
    "SYS_USR_ACCESS": {
    },
    "SYS_GRP_GROUP": {
        "grp_name": ["GR__NOME", "GRP_NAME", "NAME", "GROUP_NAME"],
        "grp_pk": ["GR__ID", "GRP_ID", "ID"],
    },
    "SYS_RULES": {
        "rules_pk": ["RL__ID", "RUL_ID", "ID"],
        "rules_name": ["RL__CODIGO", "RUL_NAME", "NAME", "RULES_NAME"],
        "rules_type": ["RUL_TYPE", "TYPE", "RULES_TYPE"],
        "rules_desc": ["RL__DESCRI", "RUL_DESCRIPTION", "DESCRIPTION", "RULES_DESC"],
    },
    "SYS_RULES_FEATURES": {
        "fet_pk": ["RL__ITEM", "FET_ID", "ID", "RFE_ID"],
        "fet_rul": ["RL__ID", "FET_RUL_ID", "RUL_ID", "RFE_RUL_ID"],
        "fet_func": ["RL__ROTINA", "FET_FUNCTION", "FUNCTION", "RFE_FUNCTION", "RFE_ROTINA"],
        "fet_feat": ["RL__DESMDEF", "FET_FEATURE", "FEATURE", "RFE_FEATURE", "RFE_DESMDEF"],
        "fet_access": ["RL__ACESSO", "FET_ACCESS", "ACCESS", "RFE_ACCESS", "RFE_ACESSO"],
        "fet_del": ["D_E_L_E_T_"],
    },
    "SYS_RULES_BUTTONS": {
    },
    "SYS_RULES_GRP_RULES": {
        "gr_col": ["GROUP_ID", "GRR_GRP_ID", "GRP_ID", "RGR_GRP_ID"],
        "rul_col": ["GR__RL_ID", "GRR_RUL_ID", "RUL_ID", "RGR_RUL_ID"],
    },
    "SYS_RULES_USR_RULES": {
        "usr_col": ["USER_ID", "URR_USR_ID", "USR_ID", "RUR_USR_ID"],
        "rul_col": ["USR_RL_ID", "URR_RUL_ID", "RUL_ID", "RUR_RUL_ID"],
    },
    "MPMENU_MENU": {
        "m_pk": ["M_ID", "ID"],
        "m_name": ["M_NAME", "NAME"],
        "m_module": ["M_MODULE", "MODULE"],
        "m_del": ["D_E_L_E_T_"],
    },
    "MPMENU_ITEM": {
        "i_pk": ["I_ID", "ID"],
        "i_menu": ["I_ID_MENU", "ID_MENU", "I_MENU_ID"],
        "i_func": ["I_ID_FUNC", "ID_FUNC", "I_FUNC_ID"],
        "i_father": ["I_FATHER", "FATHER", "I_PARENT"],
        "i_del": ["D_E_L_E_T_"],
    },
    "MPMENU_FUNCTION": {
        "f_pk": ["F_ID", "ID"],
        "f_func": ["F_FUNCTION", "FUNCTION", "F_ROTINA"],
    },
    "MPMENU_I18N": {
        "n_parent": ["N_PAREN_ID", "PAREN_ID", "I18N_PAREN_ID"],
        "n_lang": ["N_LANG", "LANG"],
        "n_desc": ["N_DESC", "DESC", "DESCRIPTION"],
        "n_del": ["D_E_L_E_T_"],
    },
}


def build_conn_str():
    return (
        f"DRIVER={{{DB_CONFIG['driver']}}};"
        f"SERVER={DB_CONFIG['server']};"
        f"DATABASE={DB_CONFIG['database']};"
        f"UID={DB_CONFIG['username']};"
        f"PWD={DB_CONFIG['password']};"
    )


def get_table_schemas(conn):
    schemas = {}
    cursor = conn.cursor()
    for table in SCHEMA_TABLES:
        try:
            cursor.execute("""
                SELECT TABLE_SCHEMA, COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = ?
                ORDER BY ORDINAL_POSITION
            """, (table,))
            rows = cursor.fetchall()
            if rows:
                schema_name = rows[0][0]
                columns = [(r[1], r[2], r[3]) for r in rows]
                schemas[table] = {"schema": schema_name, "columns": columns}
            else:
                schemas[table] = None
        except Exception as e:
            schemas[table] = {"error": str(e)}
    return schemas


def color_text(text, color):
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "bold": "\033[1m",
        "reset": "\033[0m",
    }
    return f"{colors.get(color, '')}{text}{colors['reset']}"


def diagnose(use_colors=True):
    C = lambda t, c: color_text(t, c) if use_colors else t

    print(C("=" * 65, "bold"))
    print(C("  DIAGNOSTICO DE COLUNAS DO BANCO vs CANDIDATOS DO PROJETO", "bold"))
    print(C("=" * 65, "bold"))
    print(f"  Server  : {DB_CONFIG['server']}")
    print(f"  Database: {DB_CONFIG['database']}")
    print()

    conn_str = build_conn_str()
    try:
        conn = pyodbc.connect(conn_str, timeout=10)
        print(C("  [CONEXAO] Conectado com sucesso!", "green"))
    except Exception as e:
        print(C(f"  [CONEXAO] FALHA: {e}", "red"))
        return

    try:
        real_schemas = get_table_schemas(conn)

        total_candidates = 0
        total_matched = 0

        for table in SCHEMA_TABLES:
            info = real_schemas.get(table)
            candidates_for_table = CANDIDATES.get(table, {})

            if info is None:
                print(C(f"\n  TABLE: {table}  [AUSENTE - nao encontrada no banco]", "red"))
                continue

            if "error" in info:
                print(C(f"\n  TABLE: {table}  [ERRO: {info['error']}]", "red"))
                continue

            schema_name = info["schema"]
            real_cols = [c[0] for c in info["columns"]]
            real_cols_upper = [c.upper() for c in real_cols]

            print(C(f"\n  TABLE: {table}  (schema: {schema_name}, {len(real_cols)} colunas)", "bold"))

            for col in info["columns"]:
                col_name, col_type, col_len = col
                len_str = f"({col_len})" if col_len else ""
                print(f"    {col_name:30s}  {col_type}{len_str}")

            if not candidates_for_table:
                print(C("    (sem candidatos definidos no projeto)", "yellow"))
                continue

            all_candidates = []
            for role, names in candidates_for_table.items():
                for name in names:
                    all_candidates.append((role, name))

            matched_roles = set()
            for role, candidate in all_candidates:
                total_candidates += 1
                found = False
                for real_col in real_cols:
                    if candidate.upper() == real_col.upper():
                        found = True
                        total_matched += 1
                        matched_roles.add(role)
                        break

            print()
            for role, names in candidates_for_table.items():
                role_matched = role in matched_roles
                icon = C("[OK]", "green") if role_matched else C("[!!]", "red")
                if role_matched:
                    matched_name = None
                    for name in names:
                        if name.upper() in real_cols_upper:
                            matched_name = name
                            break
                    print(f"    {icon} {role:16s} -> {matched_name}")
                else:
                    candidates_str = " | ".join(names)
                    print(f"    {icon} {role:16s} -> ({candidates_str})  {C('NENHUM candidato encontrado!', 'red')}")

        print()
        print(C("=" * 65, "bold"))
        print(C("  RESUMO", "bold"))
        print(f"  Total de candidatos: {total_candidates}")
        print(f"  Candidatos com match: {C(str(total_matched), 'green')}")
        print(f"  Candidatos sem match: {C(str(total_candidates - total_matched), 'red')}")
        print(C("=" * 65, "bold"))

        if total_candidates > total_matched:
            print()
            print(C("  [ATENCAO] Existem candidatos sem correspondencia no banco.", "yellow"))
            print(C("  Os arquivos user_mapper.py e privilege_generator.py precisam ser ajustados.", "yellow"))

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        report = {
            "server": DB_CONFIG["server"],
            "database": DB_CONFIG["database"],
            "tables": {},
        }
        for table in SCHEMA_TABLES:
            info = real_schemas.get(table)
            if info is None:
                report["tables"][table] = {"status": "absent"}
            elif "error" in info:
                report["tables"][table] = {"status": "error", "error": info["error"]}
            else:
                real_cols = [{"name": c[0], "type": c[1], "length": c[2]} for c in info["columns"]]
                real_cols_upper = [c[0].upper() for c in info["columns"]]
                candidates_status = {}
                for role, names in CANDIDATES.get(table, {}).items():
                    resolved = None
                    for name in names:
                        if name.upper() in real_cols_upper:
                            resolved = name
                            break
                    candidates_status[role] = {"candidates": names, "resolved": resolved}
                report["tables"][table] = {
                    "status": "found",
                    "schema": info["schema"],
                    "real_columns": real_cols,
                    "candidates": candidates_status,
                }

        json_path = os.path.join(OUTPUT_DIR, "diagnose_columns.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n  Relatorio JSON salvo em: {json_path}")

    finally:
        conn.close()


if __name__ == "__main__":
    diagnose()
