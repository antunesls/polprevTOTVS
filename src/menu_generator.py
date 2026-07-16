import os

from src.config import OUTPUT_DIR
from src.discovery import column_exists, column_max_length, get_columns_list


class CanonicalMenuGenerator:
    def __init__(self, reports, schema, conn=None):
        self.reports = reports or []
        self.schema = schema
        self.conn = conn

    def _sanitize(self, value):
        if value is None:
            return "NULL"
        if isinstance(value, (int, float)):
            return str(value)
        return f"'{str(value).replace("'", "''")}'"

    def _resolve_col(self, table, candidates):
        return column_exists(self.schema, table, candidates)

    def _fit_column_value(self, table, column_name, value):
        text = "" if value is None else str(value)
        max_length = column_max_length(self.schema, table, column_name)
        if max_length:
            return text[:max_length]
        return text

    def _menu_name_for_module(self, module_name):
        menu_col = self._resolve_col("MPMENU_MENU", ["M_NAME", "NAME"])
        base_name = f"{module_name}_CANONICO"
        return self._fit_column_value("MPMENU_MENU", menu_col, base_name)

    def _get_max_id(self, table, pk_col):
        if not self.conn or not pk_col:
            return 0
        try:
            cursor = self.conn.cursor()
            cursor.execute(f"SELECT MAX({pk_col}) FROM {table}")
            row = cursor.fetchone()
            if row and row[0] is not None:
                return int(row[0])
        except Exception:
            return 0
        return 0

    def _load_existing_function_ids(self):
        f_pk = self._resolve_col("MPMENU_FUNCTION", ["F_ID", "ID"])
        f_func = self._resolve_col("MPMENU_FUNCTION", ["F_FUNCTION", "FUNCTION", "F_ROTINA"])
        if not self.conn or not f_pk or not f_func:
            return {}
        try:
            cursor = self.conn.cursor()
            cursor.execute(f"SELECT {f_pk}, {f_func} FROM MPMENU_FUNCTION")
            rows = cursor.fetchall()
        except Exception:
            return {}
        return {str(row[1]).strip(): int(row[0]) for row in rows if row[1] is not None}

    def build_module_catalog(self):
        modules = {}
        for report in self.reports:
            user_id = str(report.get("user_id", "")).strip()
            for routine_info in report.get("routines_summary", []):
                module_name = str(routine_info.get("module", "")).strip()
                routine_code = str(routine_info.get("routine", "")).strip()
                if not module_name or not routine_code:
                    continue

                bucket = modules.setdefault(module_name, {"user_ids": set(), "routines": {}})
                if user_id:
                    bucket["user_ids"].add(user_id)

                if routine_code not in bucket["routines"]:
                    bucket["routines"][routine_code] = {
                        "routine": routine_code,
                        "description": str(routine_info.get("description", "")).strip(),
                    }

        result = {}
        for module_name, data in modules.items():
            result[module_name] = {
                "module": module_name,
                "menu_name": self._menu_name_for_module(module_name),
                "user_ids": sorted(data["user_ids"]),
                "routines": sorted(data["routines"].values(), key=lambda item: item["routine"]),
            }
        return result

    def generate_sql(self, link_mode="replace"):
        catalog = self.build_module_catalog()
        lines = [
            "-- ==============================================",
            "-- Script de criacao de menus canonicos por modulo",
            f"-- Modulos processados: {len(catalog)}",
            "-- ==============================================",
            "",
            "BEGIN TRANSACTION",
            "",
        ]

        m_pk = self._resolve_col("MPMENU_MENU", ["M_ID", "ID"])
        m_name = self._resolve_col("MPMENU_MENU", ["M_NAME", "NAME"])
        m_module = self._resolve_col("MPMENU_MENU", ["M_MODULE", "MODULE"])
        m_del = self._resolve_col("MPMENU_MENU", ["D_E_L_E_T_"])
        i_pk = self._resolve_col("MPMENU_ITEM", ["I_ID", "ID"])
        i_menu = self._resolve_col("MPMENU_ITEM", ["I_ID_MENU", "ID_MENU", "I_MENU_ID"])
        i_func = self._resolve_col("MPMENU_ITEM", ["I_ID_FUNC", "ID_FUNC", "I_FUNC_ID"])
        i_father = self._resolve_col("MPMENU_ITEM", ["I_FATHER", "FATHER", "I_PARENT"])
        i_tp_menu = self._resolve_col("MPMENU_ITEM", ["I_TP_MENU", "TP_MENU"])
        i_status = self._resolve_col("MPMENU_ITEM", ["I_STATUS", "STATUS"])
        i_access = self._resolve_col("MPMENU_ITEM", ["I_ACCESS", "ACCESS"])
        i_del = self._resolve_col("MPMENU_ITEM", ["D_E_L_E_T_"])
        f_pk = self._resolve_col("MPMENU_FUNCTION", ["F_ID", "ID"])
        f_func = self._resolve_col("MPMENU_FUNCTION", ["F_FUNCTION", "FUNCTION", "F_ROTINA"])
        n_parent = self._resolve_col("MPMENU_I18N", ["N_PAREN_ID", "PAREN_ID", "I18N_PAREN_ID"])
        n_lang = self._resolve_col("MPMENU_I18N", ["N_LANG", "LANG"])
        n_desc = self._resolve_col("MPMENU_I18N", ["N_DESC", "DESC", "DESCRIPTION"])
        n_del = self._resolve_col("MPMENU_I18N", ["D_E_L_E_T_"])
        u_usr = self._resolve_col("SYS_USR_MODULE", ["USR_ID", "UMD_USR_ID", "USM_USR_ID"])
        u_mod = self._resolve_col("SYS_USR_MODULE", ["USR_MODULO", "USR_CODMOD", "UMD_MENU_ID", "MENU_ID", "USM_MENU_ID"])
        u_access = self._resolve_col("SYS_USR_MODULE", ["USR_ACESSO", "ACESSO"])
        u_del = self._resolve_col("SYS_USR_MODULE", ["D_E_L_E_T_"])

        next_menu_id = self._get_max_id("MPMENU_MENU", m_pk)
        next_item_id = self._get_max_id("MPMENU_ITEM", i_pk)
        next_func_id = self._get_max_id("MPMENU_FUNCTION", f_pk)
        existing_functions = self._load_existing_function_ids()

        for module_name in sorted(catalog.keys()):
            module_data = catalog[module_name]
            next_menu_id += 1
            menu_id = next_menu_id
            menu_name = module_data["menu_name"]

            lines.append(f"-- Modulo {module_name}")
            lines.extend(self._build_insert_menu_lines(menu_id, menu_name, module_name, m_pk, m_name, m_module, m_del))

            for routine in module_data["routines"]:
                routine_code = routine["routine"]
                description = routine["description"]
                if routine_code not in existing_functions:
                    next_func_id += 1
                    existing_functions[routine_code] = next_func_id
                    lines.extend(self._build_insert_function_lines(existing_functions[routine_code], routine_code, f_pk, f_func))

                next_item_id += 1
                item_id = next_item_id
                lines.extend(
                    self._build_insert_item_lines(
                        item_id,
                        menu_id,
                        existing_functions[routine_code],
                        i_pk,
                        i_menu,
                        i_func,
                        i_father,
                        i_tp_menu,
                        i_status,
                        i_access,
                        i_del,
                    )
                )
                lines.extend(self._build_insert_i18n_lines(item_id, description or routine_code, n_parent, n_lang, n_desc, n_del))

            lines.extend(self._build_user_link_lines(module_name, module_data["user_ids"], link_mode, u_usr, u_mod, u_access, u_del))
            lines.append("")

        lines.append("COMMIT")
        return "\n".join(lines)

    def _build_insert_menu_lines(self, menu_id, menu_name, module_name, m_pk, m_name, m_module, m_del):
        insert_cols = []
        insert_vals = []
        where = []
        if m_name:
            where.append(f"{m_name} = {self._sanitize(menu_name)}")
        if m_module:
            where.append(f"{m_module} = {self._sanitize(module_name)}")
        if m_pk:
            insert_cols.append(m_pk)
            insert_vals.append(str(menu_id))
        if m_name:
            insert_cols.append(m_name)
            insert_vals.append(self._sanitize(menu_name))
        if m_module:
            insert_cols.append(m_module)
            insert_vals.append(self._sanitize(module_name))
        if m_del:
            insert_cols.append(m_del)
            insert_vals.append(self._sanitize(" "))
        lines = []
        if insert_cols and where:
            lines.append(f"IF NOT EXISTS (SELECT 1 FROM MPMENU_MENU WHERE {' AND '.join(where)})")
            lines.append(f"INSERT INTO MPMENU_MENU ({', '.join(insert_cols)})")
            lines.append(f"VALUES ({', '.join(insert_vals)});")
        return lines

    def _build_insert_function_lines(self, func_id, routine_code, f_pk, f_func):
        if not f_pk or not f_func:
            return []
        return [
            f"IF NOT EXISTS (SELECT 1 FROM MPMENU_FUNCTION WHERE {f_func} = {self._sanitize(routine_code)})",
            f"INSERT INTO MPMENU_FUNCTION ({f_pk}, {f_func})",
            f"VALUES ({func_id}, {self._sanitize(routine_code)});",
        ]

    def _build_insert_item_lines(self, item_id, menu_id, func_id, i_pk, i_menu, i_func, i_father, i_tp_menu, i_status, i_access, i_del):
        insert_cols = []
        insert_vals = []
        where = []
        if i_menu:
            where.append(f"{i_menu} = {menu_id}")
        if i_func:
            where.append(f"{i_func} = {func_id}")
        if i_pk:
            insert_cols.append(i_pk)
            insert_vals.append(str(item_id))
        if i_menu:
            insert_cols.append(i_menu)
            insert_vals.append(str(menu_id))
        if i_func:
            insert_cols.append(i_func)
            insert_vals.append(str(func_id))
        if i_father:
            insert_cols.append(i_father)
            insert_vals.append("NULL")
        if i_tp_menu:
            insert_cols.append(i_tp_menu)
            insert_vals.append(self._sanitize("2"))
        if i_status:
            insert_cols.append(i_status)
            insert_vals.append(self._sanitize("1"))
        if i_access:
            insert_cols.append(i_access)
            insert_vals.append(self._sanitize("xxxxxxxxxx"))
        if i_del:
            insert_cols.append(i_del)
            insert_vals.append(self._sanitize(" "))
        lines = []
        if insert_cols and where:
            lines.append(f"IF NOT EXISTS (SELECT 1 FROM MPMENU_ITEM WHERE {' AND '.join(where)})")
            lines.append(f"INSERT INTO MPMENU_ITEM ({', '.join(insert_cols)})")
            lines.append(f"VALUES ({', '.join(insert_vals)});")
        return lines

    def _build_insert_i18n_lines(self, item_id, description, n_parent, n_lang, n_desc, n_del):
        insert_cols = []
        insert_vals = []
        where = []
        if n_parent:
            where.append(f"{n_parent} = {item_id}")
        if n_lang:
            where.append(f"{n_lang} = '1'")
        if n_parent:
            insert_cols.append(n_parent)
            insert_vals.append(str(item_id))
        if n_lang:
            insert_cols.append(n_lang)
            insert_vals.append(self._sanitize("1"))
        if n_desc:
            insert_cols.append(n_desc)
            insert_vals.append(self._sanitize(self._fit_column_value("MPMENU_I18N", n_desc, description)))
        if n_del:
            insert_cols.append(n_del)
            insert_vals.append(self._sanitize(" "))
        lines = []
        if insert_cols and where:
            lines.append(f"IF NOT EXISTS (SELECT 1 FROM MPMENU_I18N WHERE {' AND '.join(where)})")
            lines.append(f"INSERT INTO MPMENU_I18N ({', '.join(insert_cols)})")
            lines.append(f"VALUES ({', '.join(insert_vals)});")
        return lines

    def _build_user_link_lines(self, module_name, user_ids, link_mode, u_usr, u_mod, u_access, u_del):
        if not u_usr or not u_mod:
            return []
        lines = []
        insert_cols = [u_usr, u_mod]
        if u_access:
            insert_cols.append(u_access)
        if u_del:
            insert_cols.append(u_del)

        for user_id in user_ids:
            if link_mode == "replace":
                lines.append(f"DELETE FROM SYS_USR_MODULE WHERE {u_usr} = {self._sanitize(user_id)} AND {u_mod} = {self._sanitize(module_name)};")
            lines.append(
                f"IF NOT EXISTS (SELECT 1 FROM SYS_USR_MODULE WHERE {u_usr} = {self._sanitize(user_id)} AND {u_mod} = {self._sanitize(module_name)})"
            )
            insert_vals = [self._sanitize(user_id), self._sanitize(module_name)]
            if u_access:
                insert_vals.append(self._sanitize("T"))
            if u_del:
                insert_vals.append(self._sanitize(" "))
            lines.append(f"INSERT INTO SYS_USR_MODULE ({', '.join(insert_cols)})")
            lines.append(f"VALUES ({', '.join(insert_vals)});")
        return lines

    def save_sql(self, sql_content, filename="canonical_menus.sql"):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        filepath = os.path.join(OUTPUT_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as file_handle:
            file_handle.write(sql_content)
        return filepath
