def routine_code(value):
    if value is None:
        return ""
    if isinstance(value, dict):
        return str(value.get("code") or value.get("routine") or "").strip().upper()
    return str(value).split(" - ", 1)[0].strip().upper()


def _permission_name(value):
    return str(value or "").strip()


def routine_permissions(routine):
    permissions = []
    for name, info in (routine.get("features") or {}).items():
        access = str((info or {}).get("access", "")).strip().upper()
        if access == "PERMITIDO":
            perm = _permission_name(name)
            if perm and perm not in permissions:
                permissions.append(perm)
    return sorted(permissions)


def user_routine_items(report):
    items = []
    for routine in report.get("routines_summary", []):
        code = routine_code(routine.get("routine"))
        if code:
            items.append({"code": code, "permissions": routine_permissions(routine)})
    return items


def _routine_item_signature(item):
    return (routine_code(item), tuple(_normalize_required_permissions(item)))


def _profile_group_name(dept, index):
    label = _normalized_label(dept) or "SEM_DEPTO"
    prefix = "P_PF_"
    suffix = f"_{index:02d}"
    return f"{prefix}{label[:20 - len(prefix) - len(suffix)]}{suffix}"


def build_equivalent_profile_groups(reports, tier1_common, tier2_routines_map, min_users=2, existing_rules=None, routine_details=None):
    groups = {}
    tier1_codes = set(routine_code(code) for code in (tier1_common or set()))
    tier2_by_dept = {
        dept: set(routine_code(code) for code in (codes or set()))
        for dept, codes in (tier2_routines_map or {}).items()
    }

    for report in reports or []:
        login = report.get("user")
        if not login:
            continue
        dept = report.get("user_depto", "").strip() or "SEM_DEPARTAMENTO"
        covered_codes = tier1_codes | tier2_by_dept.get(dept, set())
        residual_items = []
        for item in user_routine_items(report):
            code = routine_code(item)
            if code and code not in covered_codes:
                residual_items.append(item)
        signature = tuple(sorted(_routine_item_signature(item) for item in residual_items))
        if not signature:
            continue
        groups.setdefault((dept, signature), []).append(login)

    result = []
    counters = {}
    for (dept, signature), users in sorted(groups.items(), key=lambda item: (item[0][0], item[1])):
        users = sorted(users)
        if len(users) < min_users:
            continue
        counters[dept] = counters.get(dept, 0) + 1
        routines = []
        for code, permissions in signature:
            item = {"code": code, "permissions": list(permissions)}
            if routine_details and code in routine_details and routine_details[code]:
                item["desc"] = routine_details[code]
            if item["permissions"] or item.get("desc"):
                routines.append(item)
            else:
                routines.append(code)
        entry = {
            "name": _profile_group_name(dept, counters[dept]),
            "reason": f"Perfil residual identico no departamento {dept}",
            "routines": routines,
            "users": users,
            "type": "equivalent_profile",
        }
        if existing_rules:
            existing_match = match_profile_to_existing_rules(routines, existing_rules)
            if existing_match:
                entry["reuses_existing_rule"] = existing_match
        result.append(entry)

    return result


def _routine_details_map(reports):
    details = {}
    for report in reports or []:
        for routine in report.get("routines_summary", []):
            code = routine_code(routine.get("routine"))
            if code and code not in details:
                details[code] = routine.get("description", "")
    return details


def build_department_analysis(reports, existing_rules=None):
    by_dept = {}
    for report in reports or []:
        dept = report.get("user_depto", "").strip() or "SEM_DEPARTAMENTO"
        by_dept.setdefault(dept, []).append(report)

    result = {}
    for dept, dept_reports in sorted(by_dept.items()):
        routine_sets = [_routine_sets_by_user([report]).get(report.get("user"), set()) for report in dept_reports]
        dept_common = set.intersection(*routine_sets) if routine_sets else set()
        tier2_map = {dept: dept_common}
        details = _routine_details_map(dept_reports)
        profile_groups = build_equivalent_profile_groups(dept_reports, set(), tier2_map, existing_rules=existing_rules, routine_details=details)
        tier4_users = build_tier4_users(dept_reports, tier1_common=set(), tier2_routines_map=tier2_map, tier3_sets=profile_groups)
        all_routines = set()
        for routines in routine_sets:
            all_routines.update(routines)

        result[dept] = {
            "total_users": len(dept_reports),
            "total_routines": len(all_routines),
            "users": sorted(report.get("user") for report in dept_reports if report.get("user")),
            "tier1": [{"code": code, "desc": details.get(code, "")} for code in sorted(dept_common)],
            "profile_groups": profile_groups,
            "tier4_users": tier4_users,
        }

    return result


def _routine_sets_by_user(reports):
    result = {}
    for rep in reports:
        login = rep.get("user")
        if not login:
            continue
        result[login] = set(
            routine_code(r.get("routine"))
            for r in rep.get("routines_summary", [])
            if routine_code(r.get("routine"))
        )
    return result


def _routine_permissions_by_user(reports):
    result = {}
    for rep in reports:
        login = rep.get("user")
        if not login:
            continue
        result[login] = {}
        for routine in rep.get("routines_summary", []):
            code = routine_code(routine.get("routine"))
            if code:
                result[login][code] = set(routine_permissions(routine))
    return result


def _normalize_required_permissions(raw):
    if not isinstance(raw, dict):
        return []
    result = []
    for perm in raw.get("permissions", []) or []:
        value = _permission_name(perm)
        if value and value not in result:
            result.append(value)
    return sorted(result)


def _user_covers_item(user_permissions, item):
    code = item["code"]
    if code not in user_permissions:
        return False
    required = set(item.get("permissions", []))
    if not required:
        return True
    return required.issubset(user_permissions.get(code, set()))


def _any_user_covers_item(all_user_permissions, item):
    return any(_user_covers_item(user_permissions, item) for user_permissions in all_user_permissions.values())


def _normalize_name(name):
    value = (name or "CONJUNTO").strip().upper().replace(" ", "_")
    if value.startswith("P_PF_"):
        return value[:20]
    if not value.startswith("P_CJ_"):
        value = f"P_CJ_{value}"
    return value[:20]


def _normalized_label(value):
    return str(value or "").strip().upper().replace(" ", "_")


def _department_labels(reports):
    labels = set()
    for rep in reports:
        dept = _normalized_label(rep.get("user_depto"))
        if dept:
            labels.add(dept)
            labels.add(f"P_CJ_{dept}"[:20])
    return labels


def _is_department_based(item, normalized_name, department_labels):
    if item.get("type") == "equivalent_profile":
        return False

    if normalized_name in department_labels:
        return True

    reason = _normalized_label(item.get("reason"))
    if "DEPARTAMENTO" in reason or "USUARIOS_DO" in reason or "USUARIOS_DE" in reason:
        return True

    return False


def normalize_tier3_sets(raw_sets, reports):
    user_routines = _routine_sets_by_user(reports)
    user_permissions = _routine_permissions_by_user(reports)
    department_labels = _department_labels(reports)
    valid_routines = set()
    for routines in user_routines.values():
        valid_routines.update(routines)

    normalized = []
    for item in raw_sets or []:
        name = _normalize_name(item.get("name"))
        if _is_department_based(item, name, department_labels):
            continue

        source_routines = item.get("routines", item.get("common_routines", []))
        routines = []
        routine_items = []
        for raw in source_routines or []:
            code = routine_code(raw)
            if code and code in valid_routines and code not in routines:
                routine_item = {"code": code, "permissions": _normalize_required_permissions(raw)}
                if not _any_user_covers_item(user_permissions, routine_item):
                    continue
                routines.append(code)
                routine_items.append(routine_item if routine_item["permissions"] else code)

        if len(routines) < 2:
            continue

        users = []
        for login in sorted(user_routines.keys()):
            if all(
                _user_covers_item(
                    user_permissions.get(login, {}),
                    item if isinstance(item, dict) else {"code": item, "permissions": []},
                )
                for item in routine_items
            ):
                users.append(login)

        normalized.append({
            "name": name,
            "reason": item.get("reason", ""),
            "routines": routine_items,
            "users": users,
            **({"type": item.get("type")} if item.get("type") else {}),
        })

    return normalized


def build_tier4_users(reports, tier1_common, tier2_routines_map, tier3_sets):
    tier3_by_user = {}
    for group in tier3_sets or []:
        items = []
        for raw in group.get("routines", []):
            items.append(raw if isinstance(raw, dict) else {"code": routine_code(raw), "permissions": []})
        for login in group.get("users", []):
            tier3_by_user.setdefault(login, []).extend(items)

    tier4_users = []
    for rep in reports:
        login = rep["user"]
        user_routines = set(
            routine_code(r.get("routine"))
            for r in rep.get("routines_summary", [])
            if routine_code(r.get("routine"))
        )
        user_permissions = {
            routine_code(r.get("routine")): set(routine_permissions(r))
            for r in rep.get("routines_summary", [])
            if routine_code(r.get("routine"))
        }
        dept = rep.get("user_depto", "").strip() or "SEM_DEPARTAMENTO"

        covered = set(tier1_common or set())
        covered |= set(tier2_routines_map.get(dept, set()))
        covered_permissions = {}
        for raw in tier3_by_user.get(login, []):
            code = raw["code"]
            if code not in user_routines:
                continue
            required = set(raw.get("permissions", []))
            if not required:
                covered.add(code)
            else:
                covered_permissions.setdefault(code, set()).update(required & user_permissions.get(code, set()))

        exclusive = set(user_routines - covered)
        for code, perms in user_permissions.items():
            if code in covered:
                continue
            remaining = perms - covered_permissions.get(code, set())
            if covered_permissions.get(code) and remaining:
                for perm in sorted(remaining):
                    exclusive.add(f"{code}: {perm}")

        tier4_users.append({
            "login": login,
            "name": rep.get("user_name", login),
            "depto": dept,
            "total_routines": len(user_routines),
            "exclusive_routines": sorted(exclusive),
            "exclusive_count": len(exclusive),
        })

    return tier4_users


def load_existing_rules(conn):
    rules = {}
    try:
        from src.discovery import column_exists
        rul_pk_cols = ["RL__ID", "RUL_ID", "ID"]
        rul_name_cols = ["RL__CODIGO", "RUL_NAME", "NAME", "RULES_NAME"]
        fet_rul_cols = ["RL__ID", "FET_RUL_ID", "RUL_ID", "RFE_RUL_ID"]
        fet_func_cols = ["RL__ROTINA", "FET_FUNCTION", "FUNCTION", "RFE_FUNCTION", "RFE_ROTINA"]
        fet_feat_cols = ["RL__DESMDEF", "FET_FEATURE", "FEATURE", "RFE_FEATURE", "RFE_DESMDEF"]
        fet_access_cols = ["RL__ACESSO", "FET_ACCESS", "ACCESS", "RFE_ACCESS", "RFE_ACESSO"]
        fet_del_cols = ["D_E_L_E_T_"]

        from src.database import fetch_dicts

        rules_rows = fetch_dicts(conn, "SELECT * FROM SYS_RULES")
    except Exception:
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM SYS_RULES")
            rules_rows = [dict(zip([col[0] for col in cur.description], row)) for row in cur.fetchall()]
        except Exception:
            return rules

    rul_pk = None
    rul_name = None
    if rules_rows:
        for candidate in ["RL__ID", "RUL_ID", "ID"]:
            if candidate in rules_rows[0]:
                rul_pk = candidate
                break
        for candidate in ["RL__CODIGO", "RUL_NAME", "NAME", "RULES_NAME"]:
            if candidate in rules_rows[0]:
                rul_name = candidate
                break

    rule_ids = []
    for row in rules_rows:
        rid = str(row.get(rul_pk, "")).strip() if rul_pk else ""
        if rid:
            rule_ids.append(rid)

    if not rule_ids:
        return rules

    try:
        placeholders = ",".join("?" for _ in rule_ids)
        feat_rows = fetch_dicts(conn,
            f"SELECT * FROM SYS_RULES_FEATURES WHERE {fet_rul_cols[0] if 'RL__ID' in (feat_rows[0] if (feat_rows := [{}]) else {}) else 'RL__ID'} IN ({placeholders})",
            rule_ids)
    except Exception:
        return rules

    fet_rul = next((c for c in ["RL__ID", "FET_RUL_ID", "RUL_ID"] if feat_rows and c in feat_rows[0]), None)
    fet_func = next((c for c in ["RL__ROTINA", "FET_FUNCTION", "FUNCTION"] if feat_rows and c in feat_rows[0]), None)
    fet_feat = next((c for c in ["RL__DESMDEF", "FET_FEATURE", "FEATURE"] if feat_rows and c in feat_rows[0]), None)
    fet_access = next((c for c in ["RL__ACESSO", "FET_ACCESS", "ACCESS"] if feat_rows and c in feat_rows[0]), None)

    for row in feat_rows:
        rid = str(row.get(fet_rul, "")).strip() if fet_rul else ""
        rule_name = ""
        for rrow in rules_rows:
            if str(rrow.get(rul_pk, "")).strip() == rid:
                rule_name = str(rrow.get(rul_name, "")).strip() if rul_name else ""
                break
        if not rule_name:
            continue
        func = str(row.get(fet_func, "")).strip().upper() if fet_func else ""
        feature = str(row.get(fet_feat, "")).strip() if fet_feat else ""
        access = str(row.get(fet_access, "1") or "1").strip()
        if not func:
            continue
        if access == "1":
            rules.setdefault(rule_name, {}).setdefault(func, set()).add(feature)

    return rules


def match_profile_to_existing_rules(routines, existing_rules):
    profile_map = {}
    for raw in routines or []:
        code = routine_code(raw)
        permissions = set()
        if isinstance(raw, dict) and raw.get("permissions"):
            permissions = set(raw["permissions"])
        profile_map[code] = permissions

    for rule_name, rule_routines in existing_rules.items():
        if not rule_routines:
            continue
        covers = True
        for code, required_perms in profile_map.items():
            rule_perms = rule_routines.get(code, set())
            if not required_perms:
                if code not in rule_routines:
                    covers = False
                    break
            else:
                if not required_perms.issubset(rule_perms):
                    covers = False
                    break
        if covers:
            return rule_name

    return None
