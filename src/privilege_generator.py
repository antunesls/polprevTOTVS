import json
import os
from src.config import OUTPUT_DIR


def extract_auto_rule_sequence(value):
    text = str(value or "").strip().upper()
    if not text:
        return 0
    if text.startswith("A") and text[1:].isdigit():
        return int(text[1:])
    if text.isdigit():
        return int(text)
    digits = "".join(ch for ch in text if ch.isdigit())
    return int(digits) if digits else 0


def format_auto_rule_id(sequence):
    return f"A{int(sequence):05d}"


class PrivilegeGenerator:
    def __init__(self, report, schema):
        self.report = report
        self.schema = schema

    def _sanitize(self, value):
        if value is None:
            return "NULL"
        if isinstance(value, (int, float)):
            return str(value)
        escaped = str(value).replace("'", "''")
        return f"'{escaped}'"

    def generate_sql(self, rule_name="ACESSOS_USR001"):
        lines = []
        lines.append("-- ==============================================")
        lines.append("-- Script de criacao de privilegios")
        lines.append(f"-- Baseado nos acessos do usuario: {self.report['user']}")
        lines.append(f"-- Rotinas mapeadas: {self.report['total_routines']}")
        lines.append("-- ==============================================")
        lines.append("")
        lines.append("BEGIN TRANSACTION")
        lines.append("")

        rules_pk = self._resolve_col("SYS_RULES", ["RL__ID", "RUL_ID", "ID"])
        rules_name = self._resolve_col("SYS_RULES", ["RL__CODIGO", "RUL_NAME", "NAME", "RULES_NAME"])
        rules_type = self._resolve_col("SYS_RULES", ["RUL_TYPE", "TYPE", "RULES_TYPE"])
        rules_desc = self._resolve_col("SYS_RULES", ["RL__DESCRI", "RUL_DESCRIPTION", "DESCRIPTION", "RULES_DESC"])

        new_rule_seq = self._next_auto_rule_sequence("SYS_RULES", rules_pk)
        new_rule_id = format_auto_rule_id(new_rule_seq)

        trn_rul = self._resolve_col("SYS_RULES_TRANSACT", ["RL__ID", "RUL_ID", "ID"])
        trn_func = self._resolve_col("SYS_RULES_TRANSACT", ["RL__ROTINA", "FUNCTION", "ROTINA"])
        trn_desc = self._resolve_col("SYS_RULES_TRANSACT", ["RL__DESROT", "DESCRIPTION", "DESROT"])
        trn_access = self._resolve_col("SYS_RULES_TRANSACT", ["RL__ACESSO", "ACCESS"])
        trn_checksum = self._resolve_col("SYS_RULES_TRANSACT", ["RL__CHKSUM", "CHKSUM"])
        trn_del = self._resolve_col("SYS_RULES_TRANSACT", ["D_E_L_E_T_"])

        insert_cols = []
        insert_vals = []
        if rules_pk:
            insert_cols.append(rules_pk)
            insert_vals.append(self._sanitize(new_rule_id))
        if rules_name:
            insert_cols.append(rules_name)
            insert_vals.append(self._sanitize(rule_name))
        if rules_desc:
            insert_cols.append(rules_desc)
            insert_vals.append(self._sanitize(f"Privilegios baseados nos acessos de {self.report['user']}"))
        if rules_type:
            insert_cols.append(rules_type)
            insert_vals.append("' '")

        if insert_cols:
            lines.append(f"-- Criar nova regra (SYS_RULES)")
            lines.append(f"INSERT INTO SYS_RULES ({', '.join(insert_cols)})")
            lines.append(f"VALUES ({', '.join(insert_vals)});")
            lines.append("")

        fet_pk = self._resolve_col("SYS_RULES_FEATURES",
            ["RL__ITEM", "FET_ID", "ID", "RFE_ID"])
        fet_rul = self._resolve_col("SYS_RULES_FEATURES",
            ["RL__ID", "FET_RUL_ID", "RUL_ID", "RFE_RUL_ID"])
        fet_func = self._resolve_col("SYS_RULES_FEATURES",
            ["RL__ROTINA", "FET_FUNCTION", "FUNCTION", "RFE_FUNCTION", "RFE_ROTINA"])
        fet_feat = self._resolve_col("SYS_RULES_FEATURES",
            ["RL__DESMDEF", "FET_FEATURE", "FEATURE", "RFE_FEATURE", "RFE_DESMDEF"])
        fet_access = self._resolve_col("SYS_RULES_FEATURES",
            ["RL__ACESSO", "FET_ACCESS", "ACCESS", "RFE_ACCESS", "RFE_ACESSO"])
        fet_menuoper = self._resolve_col("SYS_RULES_FEATURES", ["RL__MENUOPER", "MENUOPER"])
        fet_menudef = self._resolve_col("SYS_RULES_FEATURES", ["RL__MENUDEF", "MENUDEF"])

        feat_max_id = self._get_max_id("SYS_RULES_FEATURES", fet_pk)
        next_feat_id = (feat_max_id or 0) + 1
        generated_count = 0

        routines = self.report.get("routines_summary", [])
        routines_with_priv = [r for r in routines if r.get("has_explicit_privilege")]
        routines_without_priv = [r for r in routines if not r.get("has_explicit_privilege")]

        lines.append(f"-- Features para rotinas COM privilegio explicito ({len(routines_with_priv)} rotinas)")
        lines.append("")

        generated_transact = set()

        for routine in routines_with_priv:
            func = routine["routine"]
            features = routine.get("features", {})

            if not features:
                lines.append(f"-- {func}: sem features definidas, pulando")
                continue

            self._append_transact_row(
                lines, new_rule_id, routine, generated_transact,
                trn_rul, trn_func, trn_desc, trn_access, trn_checksum, trn_del,
            )

            for feat_name, feat_info in features.items():
                access_value = feat_info.get("access_raw", "1")
                menu_oper = feat_info.get("menu_oper")
                menu_def = (feat_info.get("menu_def") or "").strip()
                insert_cols = []
                insert_vals = []

                if fet_pk:
                    insert_cols.append(fet_pk)
                    insert_vals.append(str(next_feat_id))
                    next_feat_id += 1
                if fet_rul:
                    insert_cols.append(fet_rul)
                    insert_vals.append(self._sanitize(new_rule_id))
                if fet_func:
                    insert_cols.append(fet_func)
                    insert_vals.append(self._sanitize(func))
                if fet_feat:
                    insert_cols.append(fet_feat)
                    insert_vals.append(self._sanitize(feat_name))
                if fet_access:
                    insert_cols.append(fet_access)
                    insert_vals.append(self._sanitize(access_value))
                if fet_menuoper and menu_oper is not None:
                    insert_cols.append(fet_menuoper)
                    insert_vals.append(str(int(float(menu_oper))))
                if fet_menudef and menu_def:
                    insert_cols.append(fet_menudef)
                    insert_vals.append(self._sanitize(menu_def))

                comment = f"-- {func} | {feat_name} | OP={int(float(menu_oper)) if menu_oper is not None else '?'} | {feat_info.get('access', '?')}"
                lines.append(comment)
                lines.append(f"INSERT INTO SYS_RULES_FEATURES ({', '.join(insert_cols)})")
                lines.append(f"VALUES ({', '.join(insert_vals)});")
                lines.append("")
                generated_count += 1

        if routines_without_priv:
            lines.append(f"-- Rotinas SEM privilegio explicito ({len(routines_without_priv)} rotinas)")
            lines.append("-- (serao inseridas com features padrao: Incluir, Alterar, Excluir, Consultar)")
            lines.append("")
            for routine in routines_without_priv:
                func = routine.get("routine", "")
                desc = routine.get("description", "")
                if not func:
                    continue
                comment = f"-- {func}: {desc}"
                lines.append(comment)
                lines.append(f"-- (sem privilegio original definido, necessario revisar manualmente)")
                self._append_transact_row(
                    lines, new_rule_id, routine, generated_transact,
                    trn_rul, trn_func, trn_desc, trn_access, trn_checksum, trn_del,
                )
                lines.append("")

        lines.append("COMMIT")
        lines.append("")
        lines.append(f"-- Total de INSERTs gerados em SYS_RULES_FEATURES: {generated_count}")
        lines.append("-- ATENCAO: Verifique os valores antes de executar em producao!")

        return "\n".join(lines)

    def save_sql(self, sql_content, filename="privilege_inserts.sql"):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        filepath = os.path.join(OUTPUT_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(sql_content)
        return filepath

    def _resolve_col(self, table, candidates):
        from src.discovery import column_exists
        return column_exists(self.schema, table, candidates)

    def _get_max_id(self, table, pk_col):
        if not pk_col:
            return None
        try:
            from src.database import fetch_all
            _, rows = fetch_all(self.report.get("_conn"), f"SELECT MAX({pk_col}) FROM {table}")
            if rows and rows[0][0] is not None:
                try:
                    return int(rows[0][0])
                except (TypeError, ValueError):
                    return rows[0][0]
        except Exception:
            pass
        return None

    def _next_auto_rule_sequence(self, table, pk_col):
        conn = self.report.get("_conn")
        if conn and pk_col:
            try:
                from src.database import fetch_all
                _, rows = fetch_all(
                    conn,
                    f"SELECT MAX(CAST(SUBSTRING({pk_col}, 2, 5) AS INT)) FROM {table} WHERE {pk_col} LIKE 'A_____'",
                )
                if rows and rows[0][0] is not None:
                    return int(rows[0][0]) + 1
            except Exception:
                pass
        return extract_auto_rule_sequence(self._get_max_id(table, pk_col)) + 1

    def _append_transact_row(self, lines, rule_id, routine, generated_transact,
                            trn_rul, trn_func, trn_desc, trn_access, trn_checksum, trn_del):
        routine_code = str(routine.get("routine", "")).strip()
        if not routine_code or routine_code in generated_transact:
            return

        insert_cols = []
        insert_vals = []
        if trn_rul:
            insert_cols.append(trn_rul)
            insert_vals.append(self._sanitize(rule_id))
        if trn_func:
            insert_cols.append(trn_func)
            insert_vals.append(self._sanitize(routine_code))
        if trn_desc:
            insert_cols.append(trn_desc)
            insert_vals.append(self._sanitize(routine.get("description", "")))
        if trn_access:
            insert_cols.append(trn_access)
            insert_vals.append(self._sanitize(self._routine_access_value(routine)))
        if trn_checksum:
            insert_cols.append(trn_checksum)
            insert_vals.append(self._sanitize(""))
        if trn_del:
            insert_cols.append(trn_del)
            insert_vals.append(self._sanitize(" "))

        if insert_cols:
            lines.append(f"INSERT INTO SYS_RULES_TRANSACT ({', '.join(insert_cols)})")
            lines.append(f"VALUES ({', '.join(insert_vals)});")
            generated_transact.add(routine_code)

    def _routine_access_value(self, routine):
        features = routine.get("features", {}) or {}
        for feat_info in features.values():
            access_value = str(feat_info.get("access_raw", "")).strip()
            if access_value:
                return access_value
        return "1"


def save_report_json(report, login="usr001", filename=None):
    if filename is None:
        filename = f"{login}_access.json"
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, filename)
    serializable = {}
    for key, value in report.items():
        if key.startswith("_"):
            continue
        if isinstance(value, dict):
            cleaned = {}
            for k, v in value.items():
                try:
                    json.dumps({k: v})
                    cleaned[k] = v
                except (TypeError, ValueError):
                    cleaned[k] = str(v)
            serializable[key] = cleaned
        elif isinstance(value, list):
            serializable[key] = value
        else:
            serializable[key] = value

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2, ensure_ascii=False, default=str)
    return filepath
