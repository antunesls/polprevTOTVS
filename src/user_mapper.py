from src.database import get_connection, fetch_dicts, fetch_all
from src.discovery import column_exists, get_columns_list
import struct


BROWSE_FEATURES = [
    "Pesquisar", "Visualizar", "Incluir", "Alterar", "Excluir",
    "Cod.Barra", "Copiar", "Retornar", "Prep.Doc.Saida", "Extra",
]


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

    def find_user(self, login):
        pk_candidates = ["USR_ID", "ID"]
        pk = self.resolve_col("SYS_USR", pk_candidates)
        login_candidates = ["USR_CODIGO", "USR_LOGIN", "LOGIN", "USR_USERNAME", "USR_COD"]
        login_col = self.resolve_col("SYS_USR", login_candidates)

        if not pk or not login_col:
            print("  \033[93m[!]\033[0m Nao foi possivel identificar colunas em SYS_USR")
            return None

        rows = fetch_dicts(self.conn,
            f"SELECT {pk}, {login_col} FROM SYS_USR WHERE {login_col} = ?",
            (login,))
        if not rows:
            print(f"  \033[93m[!]\033[0m Usuario '\033[1m{login}\033[0m' nao encontrado em SYS_USR")
            return None

        user = rows[0]
        print(f"  \033[92m[OK]\033[0m Usuario: \033[1m{user[login_col].strip()}\033[0m (ID: {user[pk]})")
        return {"id": user[pk], "login": user[login_col], "pk_col": pk}

    def map_menu_modules(self, user_id):
        usr_col = self.resolve_col("SYS_USR_MODULE", ["USR_ID", "UMD_USR_ID", "USM_USR_ID"])
        menu_col = self.resolve_col("SYS_USR_MODULE", ["USR_MODULO", "USR_CODMOD", "UMD_MENU_ID", "MENU_ID", "USM_MENU_ID"])
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

        grp_ids = [g["group_id"] for g in group_ids]

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
            data = bytes(row.get("P_DEFS") or b"")
            if not data or len(data) < 6:
                continue
            entries = self._parse_acbrowse(data)
            if prog not in overrides:
                overrides[prog] = {}
            overrides[prog].update(entries)

        return overrides

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

        # build name->permission map for ACBROWSE entries
        acbrowse_map = {}
        for prog, entries in acbrowse_overrides.items():
            for name, perm in entries.items():
                key = name.strip()
                acbrowse_map[key] = perm

        def _get_ancestor_status(item_id, by_id):
            cur = by_id.get(item_id)
            while cur:
                father = cur.get("father_id")
                if not father:
                    return None
                cur = by_id.get(father)
                if not cur:
                    return None
                desc = (cur.get("description") or "").strip()
                if desc in acbrowse_map and acbrowse_map[desc] == "D":
                    return "DISABLED"
                if desc in acbrowse_map and acbrowse_map[desc] in ("E", "D"):
                    return "ENABLED" if acbrowse_map[desc] == "E" else "DISABLED"
            return None

        # build a flat lookup (item_id -> item) for ancestor walking
        all_items_by_id = {}
        for menu in menu_tree:
            for item in menu.get("items", []):
                iid = item.get("item_id", "")
                if iid:
                    all_items_by_id[iid] = item

        def _get_effective_permission(item):
            desc = (item.get("description") or "").strip()
            func = (item.get("function_code") or "").strip()

            ancestor = _get_ancestor_status(item.get("item_id", ""), all_items_by_id)
            folder_status = ancestor

            if desc in acbrowse_map and acbrowse_map[desc] in ("D", "E"):
                folder_status = "DISABLED" if acbrowse_map[desc] == "D" else "ENABLED"

            override_str = None
            if func and func in acbrowse_map:
                ov = acbrowse_map[func]
                if ov not in ("D", "E"):
                    override_str = ov
            elif desc in acbrowse_map:
                ov = acbrowse_map[desc]
                if ov not in ("D", "E"):
                    override_str = ov

            return folder_status, override_str

        print(f"\n  {C}[3/4]{R} Mapeando grupos e privilegios...")
        groups = self.map_user_groups(user["id"])
        group_ids = [g["group_id"] for g in groups]
        group_privileges = self.map_group_privileges(group_ids)
        direct_privileges = self.map_user_privileges_direct(user["id"])

        all_privileges = dict(group_privileges)
        for func, features in direct_privileges.items():
            if func not in all_privileges:
                all_privileges[func] = {}
            all_privileges[func].update(features)

        def translate_access(value):
            mapping = {"1": "PERMITIDO", "3": "BLOQUEADO", "S": "PERMITIDO", "N": "BLOQUEADO",
                       "Y": "PERMITIDO", "T": "PERMITIDO", "True": "PERMITIDO"}
            return mapping.get(str(value).strip().upper(), str(value))

        print(f"\n  {C}[4/4]{R} Consolidando relatorio...")
        routines_flat = []
        seen = set()
        for menu in menu_tree:
            for item in menu.get("items", []):
                func = item.get("function_code", "")
                if not func or func in seen:
                    continue
                seen.add(func)
                priv_for_func = all_privileges.get(func, {})

                translated_features = {}
                for feat, info in priv_for_func.items():
                    translated_features[feat] = {
                        "access": translate_access(info["access"]),
                        "access_raw": info["access"],
                        "rule_name": info["rule_name"],
                        "menu_oper": info.get("menu_oper"),
                        "menu_def": info.get("menu_def", ""),
                    }

                browse_features_available = item.get("browse_features", {})
                acbrowse_status, acbrowse_override = _get_effective_permission(item)
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
                            if fmo is not None and abs(fmo - menu_oper) < 0.001:
                                op_features.append({
                                    "name": fname.strip() if fname else "",
                                    "action": (finfo.get("menu_def") or "").strip(),
                                    "granted": translate_access(finfo["access"]),
                                    "access_raw": finfo["access"],
                                })
                        browse_permissions.append({
                            "pos": pos,
                            "menu_oper": int(menu_oper),
                            "available": avail,
                            "features": op_features,
                        })

                routines_flat.append({
                    "routine": func,
                    "description": item.get("description", ""),
                    "menu_name": menu.get("menu_name", ""),
                    "module": menu.get("module", ""),
                    "features": translated_features,
                    "has_explicit_privilege": len(priv_for_func) > 0,
                    "browse_permissions": browse_permissions,
                    "disabled_by_acbrowse": disabled_by_acbrowse,
                    "acbrowse_status": acbrowse_status,
                })

        report = {
            "user": login,
            "user_id": user["id"],
            "total_menus": len(menu_tree),
            "total_routines": len(routines_flat),
            "groups": groups,
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
