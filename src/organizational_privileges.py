import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import OUTPUT_DIR
from src.discovery import column_exists
from src.database import fetch_all, fetch_dicts
from src.privilege_generator import save_report_json

C = {
    "reset": "\033[0m",   "bold": "\033[1m",
    "dim": "\033[2m",     "red": "\033[91m",
    "green": "\033[92m",  "yellow": "\033[93m",
    "blue": "\033[94m",   "cyan": "\033[96m",
    "magenta": "\033[95m","white": "\033[97m",
}
if os.name == "nt":
    os.system("")

CLUSTER_SIMILARITY_THRESHOLD = 0.4
MIN_CLUSTER_SIZE = 2


class OrganizationalPrivilegeGenerator:
    def __init__(self, all_reports, schema, empresa_name, conn):
        self.reports = all_reports
        self.schema = schema
        self.empresa_name = empresa_name
        self.conn = conn
        self._resolved_cols = {}

        self.tier1_routines = set()
        self.tier2_routines = {}
        self.tier3_routines = {}
        self.tier4_routines = {}

        self.new_rule_id = None
        self.next_feat_id = None

    def _resolve_col(self, table, candidates):
        return column_exists(self.schema, table, candidates)

    def _sanitize(self, value):
        if value is None:
            return "NULL"
        if isinstance(value, (int, float)):
            return str(value)
        escaped = str(value).replace("'", "''")
        return f"'{escaped}'"

    def _get_max_id(self, table, pk_col):
        if not pk_col:
            return None
        try:
            _, rows = fetch_all(self.conn, f"SELECT MAX({pk_col}) FROM {table}")
            if rows and rows[0][0] is not None:
                return int(rows[0][0])
        except Exception:
            pass
        return None

    def _user_routine_set(self, report):
        return set(r["routine"] for r in report.get("routines_summary", []) if r.get("routine"))

    def _routine_features(self, report, routine_name):
        for r in report.get("routines_summary", []):
            if r.get("routine") == routine_name:
                return r.get("features", {})
        return {}

    def generate_interactive(self):
        G = C["green"]; CY = C["cyan"]; Y = C["yellow"]; B = C["bold"]; R = C["reset"]; D = C["dim"]; W = C["white"]

        print(f"\n  {CY}{B}[TIER 1]{R} Privilegio geral da empresa ({self.empresa_name})")
        self._compute_tier1()

        print(f"\n  {CY}{B}[TIER 2]{R} Privilegios por departamento")
        self._compute_tier2()

        print(f"\n  {CY}{B}[TIER 3]{R} Conjuntos cross-departamento (clustering)")
        self._compute_tier3_interactive()

        print(f"\n  {CY}{B}[TIER 4]{R} Privilegios exclusivos por usuario")
        self._compute_tier4()

        print(f"\n  {CY}{B}[GERANDO SQL]{R}")
        self._generate_sql()

    def _compute_tier1(self):
        G = C["green"]; R = C["reset"]; D = C["dim"]; B = C["bold"]

        all_sets = [self._user_routine_set(rep) for rep in self.reports]
        if not all_sets:
            print(f"  {D}Nenhum usuario com rotinas.{R}")
            return

        common = all_sets[0].copy()
        for s in all_sets[1:]:
            common &= s

        self.tier1_routines = common
        print(f"  Rotinas comuns a {G}{len(self.reports)}{R} usuarios: {G}{len(common)}{R}")
        if common:
            sample = sorted(common)[:8]
            print(f"  {D}Ex: {', '.join(sample)}{'...' if len(common) > 8 else ''}{R}")

    def _compute_tier2(self):
        G = C["green"]; R = C["reset"]; D = C["dim"]; Y = C["yellow"]; B = C["bold"]

        dept_users = defaultdict(list)
        for rep in self.reports:
            dept = rep.get("user_depto", "").strip()
            if not dept:
                dept = "SEM_DEPARTAMENTO"
            dept_users[dept].append(rep)

        print(f"  Departamentos encontrados: {G}{len(dept_users)}{R}")

        for dept, reps in sorted(dept_users.items()):
            if len(reps) < 2:
                print(f"  {D}{dept}: {len(reps)} usuario (pulando - minimo 2){R}")
                continue

            all_sets = [self._user_routine_set(rep) for rep in reps]
            common = all_sets[0].copy()
            for s in all_sets[1:]:
                common &= s

            if common:
                self.tier2_routines[dept] = common
                users_list = [r["user"] for r in reps]
                print(f"  {G}{dept}{R}: {len(reps)} usuarios, {len(common)} rotinas comuns")
                print(f"    {D}Usuarios: {', '.join(users_list[:5])}{'...' if len(users_list) > 5 else ''}{R}")
            else:
                print(f"  {Y}{dept}{R}: {len(reps)} usuarios, {D}sem rotinas comuns{R}")

    def _compute_tier3_interactive(self):
        G = C["green"]; CY = C["cyan"]; Y = C["yellow"]; R = C["reset"]; D = C["dim"]; B = C["bold"]; W = C["white"]

        user_routines = {}
        user_dept = {}
        for rep in self.reports:
            u = rep["user"]
            user_routines[u] = self._user_routine_set(rep)
            user_dept[u] = rep.get("user_depto", "").strip()

        users_all = list(user_routines.keys())
        n = len(users_all)

        parent = {u: u for u in users_all}
        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        pairs_checked = 0
        for i in range(n):
            for j in range(i + 1, n):
                ua, ub = users_all[i], users_all[j]
                if user_dept.get(ua) == user_dept.get(ub):
                    continue
                set_a = user_routines[ua]
                set_b = user_routines[ub]
                if not set_a or not set_b:
                    continue
                intersection = set_a & set_b
                union_size = len(set_a | set_b)
                if union_size == 0:
                    continue
                simil = len(intersection) / union_size
                pairs_checked += 1
                if simil >= CLUSTER_SIMILARITY_THRESHOLD:
                    union(ua, ub)

        clusters_map = defaultdict(set)
        for u in users_all:
            root = find(u)
            clusters_map[root].add(u)

        clusters = []
        for root, members in clusters_map.items():
            if len(members) >= MIN_CLUSTER_SIZE:
                common = user_routines[next(iter(members))].copy()
                for m in members:
                    common &= user_routines[m]
                if common:
                    clusters.append({
                        "members": sorted(members),
                        "common_routines": sorted(common),
                        "depts": sorted(set(user_dept.get(m, "") for m in members)),
                    })

        if not clusters:
            print(f"  {D}Nenhum cluster cross-departamento detectado.{R}")
            return

        print(f"\n  {G}Clusters detectados: {len(clusters)}{R}")
        print(f"  {D}Threshold de similaridade: {CLUSTER_SIMILARITY_THRESHOLD} | Pares analisados: {pairs_checked}{R}")
        print()

        for idx, cl in enumerate(clusters, 1):
            prefix_counts = Counter()
            for rt in cl["common_routines"]:
                prefix = rt[:4] if not rt[0].isdigit() else rt[:5]
                prefix_counts[prefix] += 1
            suggested_prefix = prefix_counts.most_common(1)[0][0] if prefix_counts else "CONJUNTO"

            print(f"  {CY}{chr(0x250C)}{'─' * 50}{chr(0x2510)}{R}")
            print(f"  {CY}{chr(0x2502)}{R} {B}Cluster #{idx}{R}")
            print(f"  {CY}{chr(0x2502)}{R} Usuarios: {', '.join(cl['members'][:8])}{'...' if len(cl['members']) > 8 else ''}")
            print(f"  {CY}{chr(0x2502)}{R} Departamentos: {', '.join(cl['depts'])}")
            print(f"  {CY}{chr(0x2502)}{R} Rotinas comuns: {len(cl['common_routines'])}")
            sample = cl["common_routines"][:6]
            print(f"  {CY}{chr(0x2502)}{R}   Ex: {', '.join(sample)}{'...' if len(cl['common_routines']) > 6 else ''}")
            print(f"  {CY}{chr(0x2502)}{R} Sugestao de nome: {G}P_CJ_{suggested_prefix}{R}")
            print(f"  {CY}{chr(0x2514)}{'─' * 50}{chr(0x2518)}{R}")

            default_name = f"P_CJ_{suggested_prefix}"
            name_input = input(f"  Nome do conjunto [{default_name}] (vazio = pular): ").strip()

            if not name_input and default_name:
                name_input = default_name
            elif not name_input:
                print(f"  {Y}Pulado.{R}\n")
                continue

            name_input = name_input.upper()
            self.tier3_routines[name_input] = {
                "routines": set(cl["common_routines"]),
                "members": cl["members"],
            }
            print(f"  {G}Criado: {name_input}{R}\n")

    def _compute_tier4(self):
        G = C["green"]; Y = C["yellow"]; R = C["reset"]; D = C["dim"]; B = C["bold"]

        covered_tier123 = self.tier1_routines.copy()
        for dept, routines in self.tier2_routines.items():
            covered_tier123 |= routines
        for name, info in self.tier3_routines.items():
            covered_tier123 |= info["routines"]

        total_exclusive = 0
        for rep in self.reports:
            user = rep["user"]
            user_routines = self._user_routine_set(rep)
            dept = rep.get("user_depto", "").strip()
            dept_common = self.tier2_routines.get(dept, set())
            tier3_for_user = set()
            for info in self.tier3_routines.values():
                if user in info["members"]:
                    tier3_for_user |= info["routines"]

            covered_user = self.tier1_routines | dept_common | tier3_for_user
            exclusive = user_routines - covered_user

            if exclusive:
                self.tier4_routines[user] = exclusive
                total_exclusive += 1

        print(f"  Usuarios com rotinas exclusivas: {G}{total_exclusive}{R}")
        if total_exclusive:
            for user, routines in sorted(self.tier4_routines.items()):
                print(f"  {D}{user}: {len(routines)} rotinas exclusivas{R}")

    def _generate_sql(self):
        G = C["green"]; CY = C["cyan"]; R = C["reset"]; D = C["dim"]; B = C["bold"]; Y = C["yellow"]

        rules_pk = self._resolve_col("SYS_RULES", ["RL__ID", "RUL_ID", "ID"])
        rules_name = self._resolve_col("SYS_RULES", ["RL__CODIGO", "RUL_NAME", "NAME", "RULES_NAME"])
        rules_type = self._resolve_col("SYS_RULES", ["RUL_TYPE", "TYPE", "RULES_TYPE"])
        rules_desc = self._resolve_col("SYS_RULES", ["RL__DESCRI", "RUL_DESCRIPTION", "DESCRIPTION", "RULES_DESC"])

        max_id = self._get_max_id("SYS_RULES", rules_pk)
        self.new_rule_id = (max_id or 0) + 1

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
        self.next_feat_id = (feat_max_id or 0) + 1

        lines = []
        lines.append("-- ==============================================")
        lines.append("-- Script de privilegios - Modo Camada Organizacional")
        lines.append(f"-- Empresa: {self.empresa_name}")
        lines.append(f"-- Usuarios processados: {len(self.reports)}")
        lines.append(f"-- Tiers: Empresa, Departamento, Conjunto, Usuario")
        lines.append("-- ==============================================")
        lines.append("")
        lines.append("BEGIN TRANSACTION")
        lines.append("")

        lines.append("-- ==============================================")
        lines.append("-- TIER 1: PRIVILEGIO GERAL DA EMPRESA")
        lines.append(f"-- Nome da regra: P_{self.empresa_name}")
        lines.append("-- ==============================================")
        lines.append("")
        if self.tier1_routines:
            self._append_rule(lines, f"P_{self.empresa_name}",
                f"Privilegio geral - {self.empresa_name}",
                rules_pk, rules_name, rules_type, rules_desc)
            for routine in sorted(self.tier1_routines):
                self._append_features(lines, routine,
                    fet_pk, fet_rul, fet_func, fet_feat, fet_access, fet_menuoper, fet_menudef)
        else:
            lines.append("-- Nenhuma rotina comum a todos os usuarios")
            lines.append("")

        lines.append("-- ==============================================")
        lines.append("-- TIER 2: PRIVILEGIOS POR DEPARTAMENTO")
        lines.append("-- ==============================================")
        lines.append("")
        if self.tier2_routines:
            for dept in sorted(self.tier2_routines.keys()):
                routines = self.tier2_routines[dept]
                safe_dept = dept.upper().replace(" ", "_")[:20]
                rule_name = f"P_{safe_dept}"
                lines.append(f"-- Departamento: {dept} ({len(routines)} rotinas)")
                self._append_rule(lines, rule_name,
                    f"Privilegio departamento - {dept}",
                    rules_pk, rules_name, rules_type, rules_desc)
                for routine in sorted(routines):
                    self._append_features(lines, routine,
                        fet_pk, fet_rul, fet_func, fet_feat, fet_access, fet_menuoper, fet_menudef)
        else:
            lines.append("-- Nenhum departamento com rotinas comuns")
            lines.append("")

        lines.append("-- ==============================================")
        lines.append("-- TIER 3: CONJUNTOS CROSS-DEPARTAMENTO")
        lines.append("-- ==============================================")
        lines.append("")
        if self.tier3_routines:
            for group_name in sorted(self.tier3_routines.keys()):
                info = self.tier3_routines[group_name]
                members_str = ", ".join(sorted(info["members"])[:6])
                lines.append(f"-- Conjunto: {group_name}")
                lines.append(f"-- Membros: {members_str}")
                self._append_rule(lines, group_name,
                    f"Conjunto cross-departamento - {group_name}",
                    rules_pk, rules_name, rules_type, rules_desc)
                for routine in sorted(info["routines"]):
                    self._append_features(lines, routine,
                        fet_pk, fet_rul, fet_func, fet_feat, fet_access, fet_menuoper, fet_menudef)
        else:
            lines.append("-- Nenhum conjunto cross-departamento")
            lines.append("")

        lines.append("-- ==============================================")
        lines.append("-- TIER 4: PRIVILEGIOS EXCLUSIVOS POR USUARIO")
        lines.append("-- ==============================================")
        lines.append("")
        if self.tier4_routines:
            for user in sorted(self.tier4_routines.keys()):
                routines = self.tier4_routines[user]
                safe_user = user.upper()[:20]
                rule_name = f"P_{safe_user}"
                lines.append(f"-- Usuario: {user} ({len(routines)} rotinas exclusivas)")
                self._append_rule(lines, rule_name,
                    f"Privilegio exclusivo - {user}",
                    rules_pk, rules_name, rules_type, rules_desc)
                for routine in sorted(routines):
                    self._append_features(lines, routine,
                        fet_pk, fet_rul, fet_func, fet_feat, fet_access, fet_menuoper, fet_menudef)
        else:
            lines.append("-- Nenhum usuario com rotinas exclusivas")
            lines.append("")

        lines.append("COMMIT")
        lines.append("")
        lines.append(f"-- Total de regras criadas: {self.new_rule_id - max_id - 1}")
        lines.append(f"-- Total de features inseridas: {self.next_feat_id - feat_max_id - 1}")
        lines.append("-- ATENCAO: Verifique os valores antes de executar em producao!")

        sql_content = "\n".join(lines)
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        filename = f"{self.empresa_name}_organizacional.sql"
        filepath = os.path.join(OUTPUT_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(sql_content)

        print(f"  {G}Script SQL salvo em: {B}{filepath}{R}")
        print(f"  Regras criadas: {G}{self.new_rule_id - max_id - 1}{R}")
        print(f"  Features inseridas: {G}{self.next_feat_id - feat_max_id - 1}{R}")

    def _append_rule(self, lines, rule_name, rule_desc,
                     rules_pk, rules_name, rules_type, rules_desc):
        insert_cols = []
        insert_vals = []
        if rules_pk:
            insert_cols.append(rules_pk)
            insert_vals.append(str(self.new_rule_id))
        if rules_name:
            insert_cols.append(rules_name)
            insert_vals.append(self._sanitize(rule_name))
        if rules_desc:
            insert_cols.append(rules_desc)
            insert_vals.append(self._sanitize(rule_desc))
        if rules_type:
            insert_cols.append(rules_type)
            insert_vals.append("' '")
        lines.append(f"INSERT INTO SYS_RULES ({', '.join(insert_cols)})")
        lines.append(f"VALUES ({', '.join(insert_vals)});")
        lines.append("")
        self.new_rule_id += 1

    def _append_features(self, lines, routine_name,
                         fet_pk, fet_rul, fet_func, fet_feat, fet_access, fet_menuoper, fet_menudef):
        features = None
        for rep in self.reports:
            for r in rep.get("routines_summary", []):
                if r.get("routine") == routine_name:
                    feats = r.get("features", {})
                    if feats:
                        features = feats
                        break
            if features:
                break

        if not features:
            lines.append(f"-- {routine_name}: sem features definidas, pulando")
            lines.append("")
            return

        for feat_name, feat_info in features.items():
            access_value = feat_info.get("access_raw", "1")
            menu_oper = feat_info.get("menu_oper")
            menu_def = (feat_info.get("menu_def") or "").strip()
            insert_cols = []
            insert_vals = []

            if fet_pk:
                insert_cols.append(fet_pk)
                insert_vals.append(str(self.next_feat_id))
                self.next_feat_id += 1
            if fet_rul:
                insert_cols.append(fet_rul)
                insert_vals.append(str(self.new_rule_id - 1))
            if fet_func:
                insert_cols.append(fet_func)
                insert_vals.append(self._sanitize(routine_name))
            if fet_feat:
                insert_cols.append(fet_feat)
                insert_vals.append(self._sanitize(feat_name))
            if fet_access:
                insert_cols.append(fet_access)
                insert_vals.append(self._sanitize(access_value))
            if fet_menuoper and menu_oper is not None:
                insert_cols.append(fet_menuoper)
                insert_vals.append(str(int(menu_oper)))
            if fet_menudef and menu_def:
                insert_cols.append(fet_menudef)
                insert_vals.append(self._sanitize(menu_def))

            comment = f"-- {routine_name} | {feat_name}"
            lines.append(comment)
            lines.append(f"INSERT INTO SYS_RULES_FEATURES ({', '.join(insert_cols)})")
            lines.append(f"VALUES ({', '.join(insert_vals)});")
        lines.append("")
