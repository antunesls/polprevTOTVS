from src.database import get_connection, fetch_dicts, fetch_all
from src.discovery import column_exists, get_columns_list
import struct


BROWSE_FEATURES = [
    "Pesquisar", "Visualizar", "Incluir", "Alterar", "Excluir",
    "Cod.Barra", "Copiar", "Retornar", "Prep.Doc.Saida", "Extra",
]

USER_ACCESS_CODE_DESCRIPTIONS = {
    "112": "Gerar rel. no servidor",
    "121": "Usa impressora no server",
}


class UserMapper:
    def __init__(self, schema, conn):
        self.schema = schema
        self.conn = conn

    def resolve_col(self, table, candidates):
        return column_exists(self.schema, table, candidates)

    def safe_cols(self, table):
        return get_columns_list(self.schema, table)

    def build_select(self, table, wanted_cols):
        available = set(c.upper() for c in self.safe_cols(table))
        selected = [c for c in wanted_cols if c.upper() in available]
        return ", ".join(selected), selected

    def _normalize_access(self, value):
        c_value = str(value or "").strip().upper()

        if c_value in ("1", "S", "Y", "T", "TRUE", "PERMITIDO"):
            return "PERMITIDO"
        if c_value in ("3", "N", "NEGADO", "BLOQUEADO"):
            return "NEGADO"
        if c_value in ("2", "NAO_PERMITIDO", "NÃO_PERMITIDO", "NAO PERMITIDO", "NÃO PERMITIDO"):
            return "NAO_PERMITIDO"

        return "SEM_REGRA"

    def _access_rank(self, value):
        return {
            "NEGADO": 3,
            "PERMITIDO": 2,
            "NAO_PERMITIDO": 1,
            "SEM_REGRA": 0,
        }.get(self._normalize_access(value), 0)

    def _prefer_candidate(self, current, candidate):
        if current is None:
            return candidate

        n_current = self._normalize_access(current.get("access"))
        n_candidate = self._normalize_access(candidate.get("access"))

        if self._access_rank(n_candidate) > self._access_rank(n_current):
            return candidate
        if self._access_rank(n_candidate) < self._access_rank(n_current):
            return current
        if candidate.get("rule_name") == "DIRECT_USER":
            return candidate
        return current

    def _merge_privilege_maps(self, group_privileges, direct_privileges):
        privileges = {}

        for source in (group_privileges or {}, direct_privileges or {}):
            for func, features in source.items():
                privileges.setdefault(func, {})
                for feature, info in features.items():
                    privileges[func][feature] = self._prefer_candidate(privileges[func].get(feature), info)

        return privileges

    def _resolve_routine_access(self, translated_features, has_group_default, disabled_by_acbrowse):
        if disabled_by_acbrowse:
            return "NEGADO", "ACBROWSE", "ACBROWSE"

        best_access = "SEM_REGRA"
        best_source = ""
        best_reason = "NO_EXPLICIT_RULE"

        for info in translated_features.values():
            access = self._normalize_access(info.get("access"))
            if self._access_rank(access) > self._access_rank(best_access):
                best_access = access
                best_source = info.get("rule_name", "")
                best_reason = access

        if best_access == "SEM_REGRA" and has_group_default:
            return "NAO_PERMITIDO", "GROUP_DEFAULT", "GROUP_DEFAULT"

        return best_access, best_source, best_reason

    def find_user(self, login):
        pk_candidates = ["USR_ID", "ID"]
        pk = self.resolve_col("SYS_USR", pk_candidates)
        login_candidates = ["USR_CODIGO", "USR_LOGIN", "LOGIN", "USR_USERNAME", "USR_COD"]
        login_col = self.resolve_col("SYS_USR", login_candidates)
        depto_candidates = ["USR_DEPTO", "USR_DEPT", "DEPTO", "DEPARTMENT"]
        depto_col = self.resolve_col("SYS_USR", depto_candidates)
        name_candidates = ["USR_NOME", "USR_NAME", "NOME", "NAME", "USR_FULLNAME"]
        name_col = self.resolve_col("SYS_USR", name_candidates)

        if not pk or not login_col:
            print("  \033[93m[!]\033[0m Nao foi possivel identificar colunas em SYS_USR")
            return None

        select_cols = [pk, login_col]
        if depto_col:
            select_cols.append(depto_col)
        if name_col:
            select_cols.append(name_col)

        rows = fetch_dicts(self.conn,
            f"SELECT {', '.join(select_cols)} FROM SYS_USR WHERE {login_col} = ?",
            (login,))
        if not rows:
            print(f"  \033[93m[!]\033[0m Usuario '\033[1m{login}\033[0m' nao encontrado em SYS_USR")
            return None

        user = rows[0]
        depto_info = f" (Depto: {user[depto_col].strip()})" if depto_col and user.get(depto_col) and user[depto_col].strip() else ""
        name_info = f" - {user[name_col].strip()}" if name_col and user.get(name_col) and user[name_col].strip() else ""
        print(f"  \033[92m[OK]\033[0m Usuario{name_info}: \033[1m{user[login_col].strip()}\033[0m (ID: {user[pk]}){depto_info}")
        return {
            "id": user[pk],
            "login": user[login_col],
            "pk_col": pk,
            "depto": user.get(depto_col, "").strip() if depto_col else "",
            "name": user.get(name_col, "").strip() if name_col else "",
        }

    def list_non_blocked_users(self):
        pk_candidates = ["USR_ID", "ID"]
        pk = self.resolve_col("SYS_USR", pk_candidates)
        login_candidates = ["USR_CODIGO", "USR_LOGIN", "LOGIN", "USR_USERNAME", "USR_COD"]
        login_col = self.resolve_col("SYS_USR", login_candidates)
        block_candidates = ["USR_MSBLQL", "USR_BLOQUEIO", "USR_BLOCKED", "USR_STATUS", "USR_ATIVO"]
        block_col = self.resolve_col("SYS_USR", block_candidates)
        del_col = self.resolve_col("SYS_USR", ["D_E_L_E_T_"])
        depto_candidates = ["USR_DEPTO", "USR_DEPT", "DEPTO", "DEPARTMENT"]
        depto_col = self.resolve_col("SYS_USR", depto_candidates)
        name_candidates = ["USR_NOME", "USR_NAME", "NOME", "NAME", "USR_FULLNAME"]
        name_col = self.resolve_col("SYS_USR", name_candidates)

        if not pk or not login_col:
            print("  \033[93m[!]\033[0m Nao foi possivel identificar colunas em SYS_USR")
            return []

        select_cols = [pk, login_col]
        if depto_col:
            select_cols.append(depto_col)
        if name_col:
            select_cols.append(name_col)

        where = "1=1"
        params = []

        if block_col:
            where += f" AND {block_col} = ?"
            params.append("2")

        if del_col:
            where += f" AND {del_col} = ?"
            params.append(" ")

        rows = fetch_dicts(self.conn,
            f"SELECT {', '.join(select_cols)} FROM SYS_USR WHERE {where}",
            params)

        users = []
        for row in rows:
            users.append({
                "id": row[pk],
                "login": row[login_col].strip() if row[login_col] else "",
                "depto": row[depto_col].strip() if depto_col and row.get(depto_col) else "",
                "name": row[name_col].strip() if name_col and row.get(name_col) else "",
            })

        print(f"  \033[92m[OK]\033[0m Usuarios nao bloqueados encontrados: \033[1m{len(users)}\033[0m")
        return users

    def map_menu_modules(self, user_id):
        usr_col = self.resolve_col("SYS_USR_MODULE", ["USR_ID", "UMD_USR_ID", "USM_USR_ID"])
        menu_col = self.resolve_col("SYS_USR_MODULE", ["USR_ARQMENU", "USR_MODULO", "USR_CODMOD", "UMD_MENU_ID", "MENU_ID", "USM_MENU_ID"])
        access_col = self.resolve_col("SYS_USR_MODULE", ["USR_ACESSO", "ACESSO"])
        del_col = self.resolve_col("SYS_USR_MODULE", ["D_E_L_E_T_"])

        if not usr_col or not menu_col:
            print("  \033[93m[AVISO]\033[0m Tabela SYS_USR_MODULE nao encontrada ou colunas nao identificadas")
            return []

        where = f"{usr_col} = ?"
        params = [user_id]
        if access_col:
            where += f" AND {access_col} = ?"
            params.append("T")
        if del_col:
            where += f" AND {del_col} = ?"
            params.append(" ")

        rows = fetch_dicts(self.conn,
            f"SELECT {menu_col} FROM SYS_USR_MODULE WHERE {where}",
            params)

        menu_ids = [row[menu_col] for row in rows]
        print(f"  Menus diretos do usuario (ativos): {len(menu_ids)} encontrados")
        return menu_ids, menu_col

    def map_user_access_codes(self, user_id):
        usr_col = self.resolve_col("SYS_USR_ACCESS", ["USR_ID", "USA_USR_ID", "USER_ID"])
        code_col = self.resolve_col("SYS_USR_ACCESS", ["USR_CODACESSO", "USA_CODACESSO", "COD_ACESSO", "ACCESS_CODE"])
        enabled_col = self.resolve_col("SYS_USR_ACCESS", ["USR_ACESSO", "USA_ACESSO", "ACESSO", "ACCESS"])
        del_col = self.resolve_col("SYS_USR_ACCESS", ["D_E_L_E_T_"])

        if not usr_col or not code_col:
            return []

        where = f"{usr_col} = ?"
        params = [user_id]
        if enabled_col:
            where += f" AND {enabled_col} = ?"
            params.append("T")
        if del_col:
            where += f" AND {del_col} = ?"
            params.append(" ")

        rows = fetch_dicts(self.conn,
            f"SELECT {code_col}{', ' + enabled_col if enabled_col else ''} FROM SYS_USR_ACCESS WHERE {where}",
            params)

        result = []
        for row in rows:
            c_code = str(row.get(code_col) or "").strip()
            if not c_code:
                continue
            result.append({
                "code": c_code,
                "enabled": str(row.get(enabled_col) or "T").strip().upper() == "T" if enabled_col else True,
                "description": USER_ACCESS_CODE_DESCRIPTIONS.get(c_code, ""),
            })

        return sorted(result, key=lambda item: item["code"])

    def map_menu_tree(self, menu_ids, join_column=None):
        if not menu_ids:
            return []

        m_pk = self.resolve_col("MPMENU_MENU", ["M_ID", "ID"])
        m_name = self.resolve_col("MPMENU_MENU", ["M_NAME", "NAME"])
        m_module = self.resolve_col("MPMENU_MENU", ["M_MODULE", "MODULE"])
        m_del = self.resolve_col("MPMENU_MENU", ["D_E_L_E_T_"])

        if not m_pk:
            print("  [AVISO] Tabela MPMENU_MENU nao encontrada")
            return []

        use_module_join = (join_column == "USR_MODULO" and m_module is not None)
        join_col = m_module if use_module_join else m_pk

        base_cols = [m_pk, m_module] if use_module_join else [m_pk]
        if m_name:
            base_cols.append(m_name)

        placeholders = ",".join("?" for _ in menu_ids)
        where = f"{join_col} IN ({placeholders})"
        params = list(menu_ids)
        if m_del:
            where += f" AND {m_del} = ?"
            params.append(" ")
        if m_name:
            where += f" AND {m_name} NOT LIKE ?"
            params.append("#%")

        menus = fetch_dicts(self.conn,
            f"SELECT {', '.join(base_cols)} FROM MPMENU_MENU WHERE {where}",
            params)

        result = []
        for menu in menus:
            menu_data = {
                "menu_id": menu[m_pk],
                "menu_name": menu.get(m_name, "") if m_name else "",
                "module": menu.get(m_module, "") if m_module else "",
                "items": self._map_menu_items(menu[m_pk]),
            }
            item_count = len(menu_data["items"])
            print(f"  Menu '{menu_data['menu_name']}': {item_count} itens mapeados")
            result.append(menu_data)

        return result

    def _map_menu_items(self, menu_id):
        i_pk = self.resolve_col("MPMENU_ITEM", ["I_ID", "ID"])
        i_menu = self.resolve_col("MPMENU_ITEM", ["I_ID_MENU", "ID_MENU", "I_MENU_ID"])
        i_func = self.resolve_col("MPMENU_ITEM", ["I_ID_FUNC", "ID_FUNC", "I_FUNC_ID"])
        i_father = self.resolve_col("MPMENU_ITEM", ["I_FATHER", "FATHER", "I_PARENT"])
        i_status = self.resolve_col("MPMENU_ITEM", ["I_STATUS", "STATUS"])
        i_access = self.resolve_col("MPMENU_ITEM", ["I_ACCESS", "ACCESS"])
        i_tp_menu = self.resolve_col("MPMENU_ITEM", ["I_TP_MENU", "TP_MENU"])
        i_del = self.resolve_col("MPMENU_ITEM", ["D_E_L_E_T_"])

        f_pk = self.resolve_col("MPMENU_FUNCTION", ["F_ID", "ID"])
        f_func = self.resolve_col("MPMENU_FUNCTION", ["F_FUNCTION", "FUNCTION", "F_ROTINA"])

        n_parent = self.resolve_col("MPMENU_I18N", ["N_PAREN_ID", "PAREN_ID", "I18N_PAREN_ID"])
        n_lang = self.resolve_col("MPMENU_I18N", ["N_LANG", "LANG"])
        n_desc = self.resolve_col("MPMENU_I18N", ["N_DESC", "DESC", "DESCRIPTION"])
        n_del = self.resolve_col("MPMENU_I18N", ["D_E_L_E_T_"])

        if not i_pk or not i_menu:
            return []

        item_cols = [i_pk]
        if i_father:
            item_cols.append(i_father)
        if i_func:
            item_cols.append(i_func)
        if i_access:
            item_cols.append(i_access)
        if i_tp_menu:
            item_cols.append(i_tp_menu)

        where = f"{i_menu} = ?"
        params = [menu_id]
        if i_status:
            where += f" AND {i_status} = ?"
            params.append("1")
        if i_del:
            where += f" AND {i_del} = ?"
            params.append(" ")

        items = fetch_dicts(self.conn,
            f"SELECT {', '.join(item_cols)} FROM MPMENU_ITEM WHERE {where} ORDER BY {i_pk}",
            params)

        item_ids = [it[i_pk] for it in items]
        function_ids = [it[i_func] for it in items if i_func and it.get(i_func) is not None]

        functions_map = {}
        if function_ids and f_pk and f_func:
            placeholders = ",".join("?" for _ in function_ids)
            func_rows = fetch_dicts(self.conn,
                f"SELECT {f_pk}, {f_func} FROM MPMENU_FUNCTION WHERE {f_pk} IN ({placeholders})",
                function_ids)
            functions_map = {row[f_pk]: row.get(f_func, "") for row in func_rows}

        desc_map = {}
        if n_parent and n_lang and n_desc and item_ids:
            placeholders = ",".join("?" for _ in item_ids)
            desc_where = f"{n_parent} IN ({placeholders}) AND {n_lang} = ?"
            desc_params = list(item_ids) + ["1"]
            if n_del:
                desc_where += f" AND {n_del} = ?"
                desc_params.append(" ")
            desc_rows = fetch_dicts(self.conn,
                f"SELECT {n_parent}, {n_desc} FROM MPMENU_I18N WHERE {desc_where}",
                desc_params)
            desc_map = {row[n_parent]: row[n_desc] for row in desc_rows}

        result = []
        for item in items:
            item_id = item[i_pk]
            father_id = item.get(i_father) if i_father else None
            func_id = item.get(i_func) if i_func else None
            access_raw = (item.get(i_access) or "").strip() if i_access else ""
            tp_menu = (item.get(i_tp_menu) or "").strip() if i_tp_menu else ""

            func_code = functions_map.get(func_id, "") if func_id else ""
            description = desc_map.get(item_id, desc_map.get(father_id, ""))

            browse_features = {}
            if tp_menu == "2" and access_raw:
                for idx, feature_name in enumerate(BROWSE_FEATURES):
                    if idx < len(access_raw):
                        browse_features[feature_name] = (access_raw[idx] in ("x", "X", "1"))

            result.append({
                "item_id": item_id,
                "father_id": father_id,
                "function_code": func_code,
                "description": description,
                "tp_menu": tp_menu,
                "browse_features": browse_features,
            })

        return result

    def map_user_groups(self, user_id):
        usr_col = self.resolve_col("SYS_USR_GROUPS", ["USR_ID", "USG_USR_ID", "USG_USER_ID"])
        grp_col = self.resolve_col("SYS_USR_GROUPS", ["USR_GRUPO", "USG_GRP_ID", "GRP_ID", "USG_GROUP_ID"])
        del_col = self.resolve_col("SYS_USR_GROUPS", ["D_E_L_E_T_"])

        if not usr_col or not grp_col:
            print("  [AVISO] Tabela SYS_USR_GROUPS nao encontrada")
            return []

        where = f"{usr_col} = ?"
        params = [user_id]
        if del_col:
            where += f" AND {del_col} = ?"
            params.append(" ")

        rows = fetch_dicts(self.conn,
            f"SELECT {grp_col} FROM SYS_USR_GROUPS WHERE {where}",
            params)

        group_ids = [row[grp_col] for row in rows]

        grp_name = self.resolve_col("SYS_GRP_GROUP", ["GR__NOME", "GRP_NAME", "NAME", "GROUP_NAME"])
        grp_pk = self.resolve_col("SYS_GRP_GROUP", ["GR__ID", "GRP_ID", "ID"])

        groups = []
        if group_ids and grp_pk and grp_name:
            placeholders = ",".join("?" for _ in group_ids)
            grp_rows = fetch_dicts(self.conn,
                f"SELECT {grp_pk}, {grp_name} FROM SYS_GRP_GROUP WHERE {grp_pk} IN ({placeholders})",
                group_ids)
            groups = [{"group_id": row[grp_pk], "group_name": row[grp_name]} for row in grp_rows]

        print(f"  Grupos do usuario: {len(groups)} encontrados")
        return groups

    def map_group_privileges(self, group_ids):
        if not group_ids:
            return {}

        grp_ids = list(group_ids)

        gr_col = self.resolve_col("SYS_RULES_GRP_RULES", ["GROUP_ID", "GRR_GRP_ID", "GRP_ID", "RGR_GRP_ID"])
        rul_col = self.resolve_col("SYS_RULES_GRP_RULES", ["GR__RL_ID", "GRR_RUL_ID", "RUL_ID", "RGR_RUL_ID"])

        if not gr_col or not rul_col:
            print("  [AVISO] Tabela SYS_RULES_GRP_RULES nao encontrada")
            return {}

        placeholders = ",".join("?" for _ in grp_ids)
        gr_rules = fetch_dicts(self.conn,
            f"SELECT DISTINCT {rul_col} FROM SYS_RULES_GRP_RULES WHERE {gr_col} IN ({placeholders})",
            grp_ids)

        rule_ids = list(set(r[rul_col] for r in gr_rules))

        rul_pk = self.resolve_col("SYS_RULES", ["RL__ID", "RUL_ID", "ID"])
        rul_name = self.resolve_col("SYS_RULES", ["RL__CODIGO", "RUL_NAME", "NAME", "RULES_NAME"])

        rules_map = {}
        if rule_ids and rul_pk:
            placeholders = ",".join("?" for _ in rule_ids)
            rule_cols = [rul_pk]
            if rul_name:
                rule_cols.append(rul_name)
            rule_rows = fetch_dicts(self.conn,
                f"SELECT {', '.join(rule_cols)} FROM SYS_RULES WHERE {rul_pk} IN ({placeholders})",
                rule_ids)
            rules_map = {row[rul_pk]: row.get(rul_name, "") if rul_name else "" for row in rule_rows}

        fet_rul = self.resolve_col("SYS_RULES_FEATURES", ["RL__ID", "FET_RUL_ID", "RUL_ID", "RFE_RUL_ID"])
        fet_func = self.resolve_col("SYS_RULES_FEATURES",
            ["RL__ROTINA", "FET_FUNCTION", "FUNCTION", "RFE_FUNCTION", "RFE_ROTINA"])
        fet_feat = self.resolve_col("SYS_RULES_FEATURES",
            ["RL__DESMDEF", "FET_FEATURE", "FEATURE", "RFE_FEATURE", "RFE_DESMDEF"])
        fet_access = self.resolve_col("SYS_RULES_FEATURES",
            ["RL__ACESSO", "FET_ACCESS", "ACCESS", "RFE_ACCESS", "RFE_ACESSO"])
        fet_menuoper = self.resolve_col("SYS_RULES_FEATURES", ["RL__MENUOPER", "MENUOPER"])
        fet_menudef = self.resolve_col("SYS_RULES_FEATURES", ["RL__MENUDEF", "MENUDEF"])
        fet_del = self.resolve_col("SYS_RULES_FEATURES", ["D_E_L_E_T_"])

        privileges = {}
        if rule_ids and fet_rul and fet_func:
            placeholders = ",".join("?" for _ in rule_ids)
            feat_cols = [fet_rul, fet_func]
            if fet_feat:
                feat_cols.append(fet_feat)
            if fet_access:
                feat_cols.append(fet_access)
            if fet_menuoper:
                feat_cols.append(fet_menuoper)
            if fet_menudef:
                feat_cols.append(fet_menudef)

            feat_where = f"{fet_rul} IN ({placeholders})"
            feat_params = list(rule_ids)
            if fet_del:
                feat_where += f" AND {fet_del} = ?"
                feat_params.append(" ")

            feat_rows = fetch_dicts(self.conn,
                f"SELECT {', '.join(feat_cols)} FROM SYS_RULES_FEATURES WHERE {feat_where}",
                feat_params)

            for row in feat_rows:
                rule_name = rules_map.get(row[fet_rul], f"Rule_{row[fet_rul]}")
                func = row[fet_func]
                feature = row[fet_feat] if fet_feat else ""
                access = row[fet_access] if fet_access else "?"
                menu_oper = row[fet_menuoper] if fet_menuoper else None
                menu_def = row[fet_menudef] if fet_menudef else ""

                if func not in privileges:
                    privileges[func] = {}
                privileges[func][feature] = {
                    "access": access,
                    "rule_name": rule_name,
                    "rule_id": row[fet_rul],
                    "menu_oper": menu_oper,
                    "menu_def": menu_def,
                }

        print(f"  Privilegios mapeados: {len(privileges)} rotinas com features")
        return privileges

    def map_user_privileges_direct(self, user_id):
        usr_col = self.resolve_col("SYS_RULES_USR_RULES", ["USER_ID", "URR_USR_ID", "USR_ID", "RUR_USR_ID"])
        rul_col = self.resolve_col("SYS_RULES_USR_RULES", ["USR_RL_ID", "URR_RUL_ID", "RUL_ID", "RUR_RUL_ID"])

        if not usr_col or not rul_col:
            return {}

        placeholders = ",".join("?" for _ in [user_id])
        rows = fetch_dicts(self.conn,
            f"SELECT DISTINCT {rul_col} FROM SYS_RULES_USR_RULES WHERE {usr_col} = ?",
            (user_id,))

        rule_ids = list(set(r[rul_col] for r in rows))

        fet_rul = self.resolve_col("SYS_RULES_FEATURES", ["RL__ID", "FET_RUL_ID", "RUL_ID"])
        fet_func = self.resolve_col("SYS_RULES_FEATURES",
            ["RL__ROTINA", "FET_FUNCTION", "FUNCTION"])
        fet_feat = self.resolve_col("SYS_RULES_FEATURES",
            ["RL__DESMDEF", "FET_FEATURE", "FEATURE"])
        fet_access = self.resolve_col("SYS_RULES_FEATURES",
            ["RL__ACESSO", "FET_ACCESS", "ACCESS"])
        fet_menuoper = self.resolve_col("SYS_RULES_FEATURES", ["RL__MENUOPER", "MENUOPER"])
        fet_menudef = self.resolve_col("SYS_RULES_FEATURES", ["RL__MENUDEF", "MENUDEF"])

        privileges = {}
        if rule_ids and fet_rul and fet_func:
            placeholders = ",".join("?" for _ in rule_ids)
            feat_cols = [fet_func]
            if fet_feat:
                feat_cols.append(fet_feat)
            if fet_access:
                feat_cols.append(fet_access)
            if fet_menuoper:
                feat_cols.append(fet_menuoper)
            if fet_menudef:
                feat_cols.append(fet_menudef)

            feat_rows = fetch_dicts(self.conn,
                f"SELECT {', '.join(feat_cols)} FROM SYS_RULES_FEATURES WHERE {fet_rul} IN ({placeholders})",
                rule_ids)

            for row in feat_rows:
                func = row[fet_func]
                feature = row[fet_feat] if fet_feat else ""
                access = row[fet_access] if fet_access else "?"
                menu_oper = row[fet_menuoper] if fet_menuoper else None
                menu_def = row[fet_menudef] if fet_menudef else ""
                if func not in privileges:
                    privileges[func] = {}
                privileges[func][feature] = {
                    "access": access,
                    "rule_name": "DIRECT_USER",
                    "rule_id": None,
                    "menu_oper": menu_oper,
                    "menu_def": menu_def,
                }

        return privileges

    def map_system_profile(self, user_id):
        try:
            rows = fetch_dicts(self.conn,
                "SELECT RTRIM(P_NAME) AS P_NAME, RTRIM(P_PROG) AS P_PROG, "
                "RTRIM(P_TASK) AS P_TASK, RTRIM(P_TYPE) AS P_TYPE, P_DEFS "
                "FROM MP_SYSTEM_PROFILE "
                "WHERE RTRIM(P_NAME) = ? AND P_TYPE = 'ACBROWSE' AND D_E_L_E_T_ = ' '",
                (user_id,))
        except Exception:
            return {}

        overrides = {}
        for row in rows:
            prog = (row.get("P_PROG") or "").strip()
            data = self._to_bytes(row.get("P_DEFS"))
            if not data or len(data) < 6:
                continue
            entries = self._parse_acbrowse(data)
            if prog not in overrides:
                overrides[prog] = {}
            overrides[prog].update(entries)

        return overrides

    def _to_bytes(self, value):
        if value is None:
            return b""
        if isinstance(value, bytes):
            return value
        if isinstance(value, str):
            if not value.strip():
                return b""
            import base64
            try:
                return base64.b64decode(value)
            except Exception:
                return value.encode("latin-1")
        return bytes(value)

    def _parse_acbrowse(self, data):
        entries = {}
        pos = 0
        routine = None
        while pos + 5 <= len(data):
            typ = chr(data[pos]) if data[pos] < 128 else "?"
            val = struct.unpack_from("<I", data, pos + 1)[0]
            pos += 5
            if typ == "C":
                chunk = data[pos:pos + val]
                pos += val
                text = chunk.decode("ascii", errors="replace").rstrip("\0")
                if not routine:
                    routine = text
                else:
                    entries[routine] = text
                    routine = None
            elif typ == "A":
                pass
            elif typ in ("D", "E"):
                pass
            else:
                break
        return entries

    def map_routine_users(self, routine):
        f_pk = self.resolve_col("MPMENU_FUNCTION", ["F_ID", "ID"])
        f_func = self.resolve_col("MPMENU_FUNCTION", ["F_FUNCTION", "FUNCTION", "F_ROTINA"])
        if not f_func or not f_pk:
            return {"user_ids": [], "routine": routine, "error": "MPMENU_FUNCTION not found"}

        f_rows = fetch_dicts(self.conn,
            f"SELECT {f_pk} FROM MPMENU_FUNCTION WHERE {f_func} = ?",
            (routine,))
        if not f_rows:
            return {"user_ids": [], "routine": routine}

        func_id = f_rows[0][f_pk]

        i_menu = self.resolve_col("MPMENU_ITEM", ["I_ID_MENU", "ID_MENU", "I_MENU_ID"])
        i_func = self.resolve_col("MPMENU_ITEM", ["I_ID_FUNC", "ID_FUNC", "I_FUNC_ID"])

        if not i_func or not i_menu:
            return {"user_ids": [], "routine": routine, "error": "MPMENU_ITEM not found"}

        i_rows = fetch_dicts(self.conn,
            f"SELECT {i_menu} FROM MPMENU_ITEM WHERE {i_func} = ?",
            (func_id,))
        menu_ids = list(set(r[i_menu] for r in i_rows))
        if not menu_ids:
            return {"user_ids": [], "routine": routine}

        placeholders = ",".join("?" for _ in menu_ids)
        usr_col = self.resolve_col("SYS_USR_MODULE", ["USR_ID", "UMD_USR_ID"])
        menu_col = self.resolve_col("SYS_USR_MODULE", ["USR_ARQMENU", "USR_MODULO", "UMD_MENU_ID"])

        user_ids = set()
        if usr_col and menu_col:
            rows = fetch_dicts(self.conn,
                f"SELECT DISTINCT {usr_col} FROM SYS_USR_MODULE WHERE {menu_col} IN ({placeholders})",
                menu_ids)
            user_ids = set(str(r[usr_col]) for r in rows)

        if not user_ids:
            return {"user_ids": [], "routine": routine,
                    "function_id": func_id, "menu_ids": menu_ids}

        usr_pk = self.resolve_col("SYS_USR", ["USR_ID", "ID"])
        usr_login = self.resolve_col("SYS_USR", ["USR_CODIGO", "USR_LOGIN", "LOGIN", "USR_USERNAME", "USR_COD"])
        if not usr_pk or not usr_login:
            return {"user_ids": sorted(user_ids), "routine": routine,
                    "function_id": func_id, "menu_ids": menu_ids}

        placeholders = ",".join("?" for _ in user_ids)
        user_rows = fetch_dicts(self.conn,
            f"SELECT {usr_pk}, {usr_login} FROM SYS_USR WHERE {usr_pk} IN ({placeholders})",
            list(user_ids))

        allowed_user_ids = set()
        c_routine = str(routine or "").strip().upper()
        for row in user_rows:
            c_login = str(row.get(usr_login) or "").strip()
            if not c_login:
                continue
            report = self.build_full_report(c_login)
            if not report:
                continue
            for routine_info in report.get("routines_summary", []):
                if str(routine_info.get("routine") or "").strip().upper() != c_routine:
                    continue
                if str(routine_info.get("effective_access") or "").strip().upper() == "PERMITIDO":
                    allowed_user_ids.add(str(row.get(usr_pk)))
                    break

        return {"user_ids": sorted(allowed_user_ids), "routine": routine,
                "function_id": func_id, "menu_ids": menu_ids}

    def build_full_report(self, login):
        G = "\033[92m"; C = "\033[96m"; Y = "\033[93m"; D = "\033[2m"; B = "\033[1m"; R = "\033[0m"

        print(f"\n  {C}[1/4]{R} Buscando usuario '{B}{login}{R}'...")
        user = self.find_user(login)
        if not user:
            return None

        print(f"\n  {C}[2/4]{R} Mapeando menus do usuario...")
        menu_ids, menu_col = self.map_menu_modules(user["id"])
        menu_tree = self.map_menu_tree(menu_ids, menu_col)

        acbrowse_overrides = self.map_system_profile(user["id"])

        def _get_program_overrides(menu):
            c_menu_name = str(menu.get("menu_name") or "").strip()
            if c_menu_name and c_menu_name in acbrowse_overrides:
                return acbrowse_overrides[c_menu_name]
            return {}

        def _get_ancestor_status(item_id, by_id, program_overrides):
            cur = by_id.get(item_id)
            while cur:
                father = cur.get("father_id")
                if not father:
                    return None
                cur = by_id.get(father)
                if not cur:
                    return None
                desc = (cur.get("description") or "").strip()
                if desc in program_overrides and program_overrides[desc] == "D":
                    return "DISABLED"
                if desc in program_overrides and program_overrides[desc] in ("E", "D"):
                    return "ENABLED" if program_overrides[desc] == "E" else "DISABLED"
            return None

        # build a flat lookup (item_id -> item) for ancestor walking
        all_items_by_id = {}
        for menu in menu_tree:
            for item in menu.get("items", []):
                iid = item.get("item_id", "")
                if iid:
                    all_items_by_id[iid] = item

        def _get_effective_permission(item, program_overrides):
            desc = (item.get("description") or "").strip()
            func = (item.get("function_code") or "").strip()

            ancestor = _get_ancestor_status(item.get("item_id", ""), all_items_by_id, program_overrides)
            folder_status = ancestor

            if desc in program_overrides and program_overrides[desc] in ("D", "E"):
                folder_status = "DISABLED" if program_overrides[desc] == "D" else "ENABLED"

            override_str = None
            if func and func in program_overrides:
                ov = program_overrides[func]
                if ov not in ("D", "E"):
                    override_str = ov
            elif desc in program_overrides:
                ov = program_overrides[desc]
                if ov not in ("D", "E"):
                    override_str = ov

            return folder_status, override_str

        print(f"\n  {C}[3/4]{R} Mapeando grupos e privilegios...")
        groups = self.map_user_groups(user["id"])
        access_codes = self.map_user_access_codes(user["id"])
        group_ids = [g["group_id"] for g in groups]
        group_privileges = self.map_group_privileges(group_ids)
        direct_privileges = self.map_user_privileges_direct(user["id"])

        all_privileges = self._merge_privilege_maps(group_privileges, direct_privileges)
        has_group_default = any(
            str(group.get("group_id", "")).strip() == "*" or str(group.get("group_name", "")).strip() == "*"
            for group in groups
        )

        print(f"\n  {C}[4/4]{R} Consolidando relatorio...")
        routines_flat = []
        seen = set()
        for menu in menu_tree:
            program_overrides = _get_program_overrides(menu)
            for item in menu.get("items", []):
                func = item.get("function_code", "")
                if not func or func in seen:
                    continue
                seen.add(func)
                priv_for_func = all_privileges.get(func, {})

                translated_features = {}
                for feat, info in priv_for_func.items():
                    translated_features[feat] = {
                        "access": self._normalize_access(info["access"]),
                        "access_raw": info["access"],
                        "rule_name": info["rule_name"],
                        "menu_oper": info.get("menu_oper"),
                        "menu_def": info.get("menu_def", ""),
                    }

                browse_features_available = item.get("browse_features", {})
                acbrowse_status, acbrowse_override = _get_effective_permission(item, program_overrides)
                disabled_by_acbrowse = (acbrowse_status in ("D", "DISABLED"))

                if acbrowse_override and len(acbrowse_override) >= 10:
                    for pos in range(min(10, len(acbrowse_override))):
                        fname = BROWSE_FEATURES[pos] if pos < len(BROWSE_FEATURES) else f"OP{pos+1}"
                        if acbrowse_override[pos] == " ":
                            browse_features_available[fname] = False
                        elif acbrowse_override[pos] in ("x", "X"):
                            browse_features_available[fname] = True

                browse_permissions = []
                if browse_features_available:
                    for pos in range(10):
                        menu_oper = float(pos + 1)
                        avail = browse_features_available.get(BROWSE_FEATURES[pos], False) if pos < len(BROWSE_FEATURES) else False
                        if disabled_by_acbrowse:
                            avail = False
                        op_features = []
                        for fname, finfo in priv_for_func.items():
                            fmo = finfo.get("menu_oper")
                            if fmo is not None:
                                fmo = float(fmo)
                                if abs(fmo - menu_oper) < 0.001:
                                    op_features.append({
                                        "name": fname.strip() if fname else "",
                                        "action": (finfo.get("menu_def") or "").strip(),
                                        "granted": self._normalize_access(finfo["access"]),
                                        "access_raw": finfo["access"],
                                    })
                        browse_permissions.append({
                            "pos": pos,
                            "menu_oper": int(menu_oper),
                            "available": avail,
                            "features": op_features,
                        })

                effective_access, decision_source, denial_reason = self._resolve_routine_access(
                    translated_features,
                    has_group_default,
                    disabled_by_acbrowse,
                )

                routines_flat.append({
                    "routine": func,
                    "description": item.get("description", ""),
                    "menu_name": menu.get("menu_name", ""),
                    "module": menu.get("module", ""),
                    "in_menu": True,
                    "features": translated_features,
                    "has_explicit_privilege": len(priv_for_func) > 0,
                    "effective_access": effective_access,
                    "decision_source": decision_source,
                    "denial_reason": denial_reason,
                    "browse_permissions": browse_permissions,
                    "disabled_by_acbrowse": disabled_by_acbrowse,
                    "acbrowse_status": acbrowse_status,
                })

        for func, features in all_privileges.items():
            if func not in seen:
                seen.add(func)
                translated_features = {}
                for feat, info in features.items():
                    translated_features[feat] = {
                        "access": self._normalize_access(info["access"]),
                        "access_raw": info["access"],
                        "rule_name": info["rule_name"],
                        "menu_oper": info.get("menu_oper"),
                        "menu_def": info.get("menu_def", ""),
                    }
                effective_access, decision_source, denial_reason = self._resolve_routine_access(
                    translated_features,
                    has_group_default,
                    False,
                )
                routines_flat.append({
                    "routine": func,
                    "description": "",
                    "menu_name": "",
                    "module": "",
                    "in_menu": False,
                    "features": translated_features,
                    "has_explicit_privilege": True,
                    "effective_access": effective_access,
                    "decision_source": decision_source,
                    "denial_reason": denial_reason,
                    "browse_permissions": [],
                    "disabled_by_acbrowse": False,
                    "acbrowse_status": None,
                })

        report = {
            "user": login,
            "user_id": user["id"],
            "user_depto": user.get("depto", ""),
            "user_name": user.get("name", ""),
            "total_menus": len(menu_tree),
            "total_routines": len(routines_flat),
            "groups": groups,
            "access_codes": access_codes,
            "menus": menu_tree,
            "routines_summary": routines_flat,
            "privileges_raw": all_privileges,
        }

        routines_with_priv = sum(1 for r in routines_flat if r["has_explicit_privilege"])
        print(f"\n  {C}{D}{chr(0x250C)}{'─' * 45}{chr(0x2510)}{R}")
        print(f"  {C}{chr(0x2502)}{R} {B}RESUMO{R}")
        print(f"  {C}{chr(0x2502)}{R} Menus acessiveis .............. {G}{len(menu_tree)}{R}")
        print(f"  {C}{chr(0x2502)}{R} Rotinas mapeadas .............. {len(routines_flat)}")
        print(f"  {C}{chr(0x2502)}{R} Rotinas com privilegio ........ {G}{routines_with_priv}{R}")
        print(f"  {C}{chr(0x2502)}{R} Rotinas sem privilegio ........ {Y}{len(routines_flat) - routines_with_priv}{R}")
        print(f"  {C}{chr(0x2502)}{R} Grupos ........................ {len(groups)}")
        print(f"  {C}{D}{chr(0x2514)}{'─' * 45}{chr(0x2518)}{R}")

        return report
