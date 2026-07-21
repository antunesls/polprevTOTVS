def _routine_code(item):
    if isinstance(item, dict):
        return str(item.get("code") or item.get("routine") or "").strip().upper()
    return str(item or "").strip().upper()


def _routine_permissions_from_features(features):
    if not features:
        return set()
    perms = set()
    for name, info in (features or {}).items():
        if str((info or {}).get("access", "")).strip().upper() == "PERMITIDO":
            perms.add(str(name or "").strip())
    return perms


def _derive_feature_row(feature_name, feature_info, status):
    return {
        "feature": str(feature_name or "").strip(),
        "access": str(feature_info.get("access_raw", feature_info.get("access", "1"))),
        "menu_oper": feature_info.get("menu_oper"),
        "menu_def": str(feature_info.get("menu_def", "") or "").strip(),
        "status": status,
    }


def _merge_feature_list(existing_features, proposed_features):
    existing_map = {}
    for feat in existing_features or []:
        key = str(feat.get("feature") or "").strip()
        if key:
            existing_map[key] = dict(feat)
            existing_map[key]["status"] = "EXISTENTE"

    merged = {}
    for feat_name, feat_info in (proposed_features or {}).items():
        c_name = str(feat_name or "").strip()
        if not c_name:
            continue
        merged[c_name] = _derive_feature_row(c_name, feat_info, "FALTANTE")
        if c_name in existing_map:
            merged[c_name]["status"] = "EXISTENTE"

    for key, feat in existing_map.items():
        if key not in merged:
            feat_copy = dict(feat)
            feat_copy["status"] = "EXCEDENTE"
            merged[key] = feat_copy

    return list(merged.values())


def build_consolidated_inventory(
    reports,
    existing_rules,
    existing_links,
    tier1_routines,
    tier2_routines,
    tier3_routines,
    tier4_routines,
    rule_name_to_id=None,
):
    existing_rules = existing_rules or {}
    existing_links = existing_links or {}
    tier1_routines = tier1_routines or set()
    tier2_routines = tier2_routines or {}
    tier3_routines = tier3_routines or {}
    tier4_routines = tier4_routines or {}
    rule_name_to_id = rule_name_to_id or {}

    user_id_to_login = {}
    valid_logins = set()
    for rep in reports or []:
        uid = str(rep.get("user_id") or rep.get("user") or "").strip()
        login = str(rep.get("user") or "").strip()
        if uid and login:
            user_id_to_login[uid] = login
        if login:
            valid_logins.add(login)

    rules = []

    orphaned_bindings = {}

    for rule_name, routine_map in sorted((existing_rules or {}).items()):
        links = existing_links.get(rule_name, {})
        raw_linked_users = links.get("linked_users", []) or []
        filtered_users = []
        for u in raw_linked_users:
            user_login = str(u.get("login", "") or "").strip()
            if user_login in valid_logins:
                filtered_users.append(u)
            else:
                orphaned_bindings.setdefault(rule_name, []).append(user_login or str(u.get("user_id", "")))

        routines_out = []
        for routine_code_name in sorted(routine_map.keys()):
            features_out = _merge_feature_list(None, None)
            for feat_name in sorted(routine_map[routine_code_name] or []):
                features_out.append({
                    "feature": str(feat_name or "").strip(),
                    "access": "1",
                    "menu_oper": None,
                    "menu_def": "",
                    "status": "EXISTENTE",
                })
            if not features_out:
                features_out = []
            routines_out.append({
                "routine": routine_code_name,
                "description": "",
                "features": features_out,
                "status": "COMPLETO",
            })

        rules.append({
            "rule_id": rule_name_to_id.get(rule_name),
            "rule_name": rule_name,
            "rule_description": "",
            "source": "EXISTENTE",
            "tier": "EXISTENTE",
            "action": "MANTER",
            "has_excess": any(
                f.get("status") == "EXCEDENTE"
                for rt in routines_out
                for f in (rt.get("features") or [])
            ),
            "users": sorted(filtered_users, key=lambda u: str(u.get("login", ""))),
            "groups": sorted(links.get("linked_groups", []) or [], key=lambda g: str(g.get("group_name", ""))),
            "routines": routines_out,
        })

    for rep in reports or []:
        login = str(rep.get("user") or "").strip()
        if not login or login not in tier4_routines:
            continue
        routines_set = tier4_routines[login]
        rule_name = f"P_{login.upper()}"[:20]
        routines_out = []
        for rt_code in sorted(routines_set):
            features = {}
            for r in rep.get("routines_summary", []):
                if _routine_code(r.get("routine")) == rt_code:
                    features = r.get("features", {})
                    break
            feature_rows = _merge_feature_list(
                [],
                {k: v for k, v in (features or {}).items() if str((v or {}).get("access", "")).strip().upper() == "PERMITIDO"},
            )
            for feat in feature_rows:
                feat["status"] = "FALTANTE"
            routines_out.append({
                "routine": rt_code,
                "description": "",
                "features": feature_rows,
                "status": "FALTANTE",
            })

        if routines_out:
            existing = next((r for r in rules if r["rule_name"] == rule_name), None)
            user_entry = {"user_id": rep.get("user_id", login), "login": login}
            if existing:
                existing_routines = {rt["routine"] for rt in existing.get("routines", [])}
                for rt_out in routines_out:
                    if rt_out["routine"] not in existing_routines:
                        existing.setdefault("routines", []).append(rt_out)
                        existing["action"] = "COMPLEMENTAR"
                existing_users = {u.get("login", "") for u in existing.get("users", [])}
                if login not in existing_users:
                    existing.setdefault("users", []).append(user_entry)
                    existing["action"] = "COMPLEMENTAR"
            else:
                rules.append({
                    "rule_id": None,
                    "rule_name": rule_name,
                    "rule_description": f"Privilegio exclusivo - {login}",
                    "source": "NOVO",
                    "tier": "TIER4",
                    "action": "CRIAR",
                    "has_excess": False,
                    "users": [user_entry],
                    "groups": [],
                    "routines": routines_out,
                })

    covered_dept_rules = set()
    for dept_name, routines_set in sorted(tier2_routines.items()):
        dept_reports = [rep for rep in (reports or []) if str(rep.get("user_depto") or "").strip() == dept_name]
        dept_users = sorted({rep.get("user") for rep in dept_reports if rep.get("user")})
        safe_dept = dept_name.upper().replace(" ", "_")[:20]
        rule_name = f"P_{safe_dept}"
        covered_dept_rules.add(rule_name)

        routines_out = []
        for rt_code in sorted(routines_set):
            features = {}
            for rep in dept_reports:
                for r in rep.get("routines_summary", []):
                    if _routine_code(r.get("routine")) == rt_code:
                        features = r.get("features", {})
                        break
                if features:
                    break
            feature_rows = _merge_feature_list(
                [],
                {k: v for k, v in (features or {}).items() if str((v or {}).get("access", "")).strip().upper() == "PERMITIDO"},
            )
            for feat in feature_rows:
                feat["status"] = "FALTANTE"
            routines_out.append({
                "routine": rt_code,
                "description": "",
                "features": feature_rows,
                "status": "FALTANTE",
            })

        dept_user_list = [
            {"user_id": rep.get("user_id", login), "login": login}
            for login in dept_users
            for rep in (dept_reports or [])
            if rep.get("user") == login
        ]

        existing = next((r for r in rules if r["rule_name"] == rule_name), None)
        if existing:
            existing["tier"] = "TIER2"
            existing_routines = {rt["routine"] for rt in existing.get("routines", [])}
            existing_users = {u.get("login", "") for u in existing.get("users", [])}
            for rt_out in routines_out:
                if rt_out["routine"] not in existing_routines:
                    existing.setdefault("routines", []).append(rt_out)
                    existing["action"] = "COMPLEMENTAR"
                else:
                    existing_rt = next((r for r in existing["routines"] if r["routine"] == rt_out["routine"]), None)
                    if existing_rt:
                        for f in rt_out.get("features", []):
                            if not any(ef["feature"] == f["feature"] for ef in existing_rt.get("features", [])):
                                existing_rt.setdefault("features", []).append(f)
                                existing["action"] = "COMPLEMENTAR"
            for u in dept_user_list:
                if u.get("login", "") not in existing_users:
                    existing.setdefault("users", []).append(u)
                    existing["action"] = "COMPLEMENTAR"
        else:
            rules.append({
                "rule_id": None,
                "rule_name": rule_name,
                "rule_description": f"Privilegio departamento - {dept_name}",
                "source": "NOVO",
                "tier": "TIER2",
                "action": "CRIAR",
                "has_excess": False,
                "users": dept_user_list,
                "groups": [],
                "routines": routines_out,
            })

    for group_name, info in sorted(tier3_routines.items()):
        reused_rule = info.get("reuses_existing_rule")
        members = sorted(info.get("members", []) or [])
        if not members:
            continue

        routines_in = info.get("routines", []) or []

        routines_out = []
        for raw in routines_in:
            rt_code = _routine_code(raw)
            perms = set()
            if isinstance(raw, dict):
                perms = set(raw.get("permissions", []) or [])
            features = {}
            for rep in reports or []:
                for r in rep.get("routines_summary", []):
                    if _routine_code(r.get("routine")) == rt_code:
                        features = r.get("features", {})
                        break
                if features:
                    break

            feature_rows = _merge_feature_list(
                [],
                {k: v for k, v in (features or {}).items() if str((v or {}).get("access", "")).strip().upper() == "PERMITIDO"},
            )
            for feat in feature_rows:
                feat["status"] = "FALTANTE"

            routines_out.append({
                "routine": rt_code,
                "description": "",
                "features": feature_rows,
                "status": "FALTANTE",
            })

        member_list = []
        for member in members:
            for rep in reports or []:
                if rep.get("user") == member:
                    member_list.append({
                        "user_id": rep.get("user_id", member),
                        "login": member,
                    })
                    break
            else:
                member_list.append({"user_id": member, "login": member})

        if reused_rule:
            matching_existing = next((r for r in rules if r["rule_name"] == reused_rule), None)
            if matching_existing:
                if matching_existing["source"] == "EXISTENTE":
                    matching_existing["tier"] = "TIER3"
                    if matching_existing["action"] != "COMPLEMENTAR":
                        matching_existing["action"] = "MANTER"
                else:
                    matching_existing["action"] = matching_existing.get("action") or "COMPLEMENTAR"
                for rt_out in routines_out:
                    existing_rt = next(
                        (r for r in matching_existing.get("routines", []) if r["routine"] == rt_out["routine"]),
                        None,
                    )
                    if existing_rt:
                        for feat_out in rt_out.get("features", []):
                            existing_feat = next(
                                (f for f in existing_rt.get("features", []) if f["feature"] == feat_out["feature"]),
                                None,
                            )
                            if existing_feat:
                                continue
                            existing_rt.setdefault("features", []).append(dict(feat_out, **{"status": "FALTANTE"}))
                            matching_existing["action"] = "COMPLEMENTAR"
                    else:
                        matching_existing.setdefault("routines", []).append(rt_out)
                        matching_existing["action"] = "COMPLEMENTAR"

                existing_members = {u.get("login", "") for u in matching_existing.get("users", [])}
                for mb in member_list:
                    if mb["login"] not in existing_members:
                        matching_existing.setdefault("users", []).append(mb)
                        matching_existing["action"] = "COMPLEMENTAR"
                continue

        rules.append({
            "rule_id": None,
            "rule_name": group_name,
            "rule_description": f"Conjunto cross-departamento - {group_name}",
            "source": "NOVO",
            "tier": "TIER3",
            "action": "CRIAR",
            "has_excess": False,
            "users": member_list,
            "groups": [],
            "routines": routines_out,
        })

    for rule in rules:
        rule["routines"] = sorted(rule["routines"], key=lambda r: r["routine"])
        rule["users"] = sorted(rule["users"], key=lambda u: str(u.get("login", "")))
        rule["groups"] = sorted(rule["groups"], key=lambda g: str(g.get("group_name", "")))

    rules.sort(key=lambda r: (
        0 if r["source"] == "EXISTENTE" else 1,
        0 if r["action"] == "CRIAR" else 1 if r["action"] == "COMPLEMENTAR" else 2,
        str(r.get("rule_name", "")),
        str(r.get("tier", "")),
    ))

    if orphaned_bindings:
        print(f"  [AVISO] Vinculos orfaos ignorados (usuarios nao estao nos relatorios atuais):")
        for rule_name, users in sorted(orphaned_bindings.items()):
            print(f"    - {rule_name}: {', '.join(users)}")

    return {
        "rules": rules,
        "deleted_bindings": [],
        "orphaned_bindings": orphaned_bindings,
    }
