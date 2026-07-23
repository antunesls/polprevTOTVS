import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import src.config as cfg
from src.config import OUTPUT_DIR
from src.discovery import column_exists
from src.database import fetch_all, fetch_dicts
from src.privilege_generator import extract_auto_rule_sequence, format_auto_rule_id, save_report_json
from src.tier3 import apply_department_canonicalization, build_department_common_routines, load_existing_rules, match_profile_to_existing_rules, normalize_tier3_sets, routine_code, routine_permissions

C = {
    "reset": "\033[0m",   "bold": "\033[1m",
    "dim": "\033[2m",     "red": "\033[91m",
    "green": "\033[92m",  "yellow": "\033[93m",
    "blue": "\033[94m",   "cyan": "\033[96m",
    "magenta": "\033[95m","white": "\033[97m",
}
if os.name == "nt":
    os.system("")

CLUSTER_SIMILARITY_THRESHOLD = cfg.CLUSTER_SIMILARITY_THRESHOLD
MIN_CLUSTER_SIZE = cfg.MIN_CLUSTER_SIZE
MANUAL_NAME_STOPWORDS = {
    "DE", "DA", "DO", "DAS", "DOS", "E", "EM", "PARA", "COM", "SEM", "POR",
    "ROTINA", "ROTINAS", "CADASTRO", "CONSULTA", "PROCESSO", "PROCESSOS", "RELATORIO", "RELATORIOS",
    "SISTEMA", "GERAL", "CONTROLE", "MANUTENCAO",
}

PREFIX_DOMAIN_LABELS = {
    "FINR": "REL_FINANC",
    "MATR": "REL_MAT",
    "FISR": "REL_FISCAL",
    "CTBR": "REL_CONTAB",
    "FATR": "REL_FAT",
    "PONR": "REL_PONTO",
    "ESPR": "REL_ESTOQUE",
    "CRMR": "REL_CRM",
    "RSCR": "REL_RECURSOS",
    "CPLR": "REL_COMPLIANCE",
}


def _prefix_domain_label(prefix):
    prefix_upper = str(prefix or "").upper()
    if prefix_upper in PREFIX_DOMAIN_LABELS:
        return PREFIX_DOMAIN_LABELS[prefix_upper]
    if len(prefix_upper) >= 4 and prefix_upper[3] == "R":
        return f"REL_{prefix_upper[:3]}"
    if len(prefix_upper) >= 4 and prefix_upper[3] == "A":
        return f"CAD_{prefix_upper[:3]}"
    if len(prefix_upper) >= 4 and prefix_upper[3] == "C":
        return f"CONS_{prefix_upper[:3]}"
    if len(prefix_upper) >= 4 and prefix_upper[3] == "M":
        return f"MOV_{prefix_upper[:3]}"
    return prefix_upper[:4]


def _load_routine_user_metrics():
    metrics_path = os.path.join(OUTPUT_DIR, "metrics_20260722_bosal.json")
    if not os.path.exists(metrics_path):
        return None
    try:
        from src.telemetry_analyzer import load_prometheus_metrics
        metrics = load_prometheus_metrics(metrics_path)
        return metrics.get("routine_users", {})
    except Exception:
        return None


class OrganizationalPrivilegeGenerator:
    def __init__(self, all_reports, schema, empresa_name, conn):
        self.reports = apply_department_canonicalization(all_reports)
        self.schema = schema
        self.empresa_name = empresa_name
        self.conn = conn
        self._resolved_cols = {}
        self._routine_user_metrics = _load_routine_user_metrics()
        self._existing_rules = load_existing_rules(self.conn) or {}

        self.tier1_routines = set()
        self.tier2_routines = {}
        self.tier3_routines = {}
        self.tier4_routines = {}

        self.new_rule_id = None
        self._total_features = 0
        self._total_transacts = 0
        self._total_user_rule_links = 0

    def _resolve_col(self, table, candidates):
        return column_exists(self.schema, table, candidates)

    def _fit_column_value(self, table, column_name, value):
        from src.discovery import column_max_length
        text = "" if value is None else str(value)
        max_length = column_max_length(self.schema, table, column_name)
        if max_length:
            return text[:max_length]
        return text

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
                try:
                    return int(rows[0][0])
                except (TypeError, ValueError):
                    return None
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

    def _routine_description(self, routine_name):
        for report in self.reports:
            for routine in report.get("routines_summary", []):
                if routine.get("routine") == routine_name:
                    return str(routine.get("description", "")).strip()
        return ""

    def _suggest_manual_cluster_name(self, common_routines):
        token_counts = Counter()
        for routine_name in common_routines:
            description = self._routine_description(routine_name)
            for token in re.findall(r"[A-Z0-9À-ÿ]+", description.upper()):
                if len(token) < 4 or token in MANUAL_NAME_STOPWORDS or token.isdigit():
                    continue
                token_counts[token] += 1

        if token_counts:
            label = token_counts.most_common(1)[0][0]
            return f"P_CJ_{label}"[:20]

        prefix_counts = Counter()
        for routine_name in common_routines:
            if not routine_name:
                continue
            prefix = routine_name[:4] if not routine_name[0].isdigit() else routine_name[:5]
            prefix_counts[prefix] += 1
        suggested_prefix = prefix_counts.most_common(1)[0][0] if prefix_counts else "CONJUNTO"
        return f"P_CJ_{suggested_prefix}"[:20]

    def generate_interactive(self, llm_clusters=None):
        G = C["green"]; CY = C["cyan"]; Y = C["yellow"]; B = C["bold"]; R = C["reset"]; D = C["dim"]; W = C["white"]

        print(f"\n  {CY}{B}[TIER 1]{R} Privilegio geral da empresa ({self.empresa_name})")
        self._compute_tier1()

        print(f"\n  {CY}{B}[TIER 2]{R} Privilegios por departamento")
        self._compute_tier2()

        print(f"\n  {CY}{B}[TIER 3]{R} Conjuntos funcionais de rotinas")
        self._compute_tier3_interactive(llm_clusters=llm_clusters)

        print(f"\n  {CY}{B}[TIER 4]{R} Privilegios exclusivos por usuario")
        self._compute_tier4()

        print(f"\n  {CY}{B}[PROMOCAO RESIDUAIS]{R} Rotinas compartilhadas -> TIER3")
        self._promote_shared_residual_clusters()

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
        min_users = cfg.department_min_users()
        common_by_dept = build_department_common_routines(self.reports, min_users=min_users)

        for dept, reps in sorted(dept_users.items()):
            if len(reps) < min_users:
                print(f"  {D}{dept}: {len(reps)} usuario (pulando - minimo {min_users}){R}")
                continue

            common = common_by_dept.get(dept, set())

            if common:
                self.tier2_routines[dept] = common
                users_list = [r["user"] for r in reps]
                print(f"  {G}{dept}{R}: {len(reps)} usuarios, {len(common)} rotinas comuns")
                print(f"    {D}Usuarios: {', '.join(users_list[:5])}{'...' if len(users_list) > 5 else ''}{R}")
            else:
                print(f"  {Y}{dept}{R}: {len(reps)} usuarios, {D}sem rotinas comuns{R}")

    def _compute_tier3_interactive(self, llm_clusters=None):
        G = C["green"]; CY = C["cyan"]; Y = C["yellow"]; R = C["reset"]; D = C["dim"]; B = C["bold"]; W = C["white"]

        if llm_clusters is not None:
            print(f"  {G}Usando {len(llm_clusters)} conjuntos funcionais pre-definidos.{R}")
            self._review_llm_clusters(llm_clusters, auto_accept=True)
            return

        llm_result = self._try_llm_clustering()
        if llm_result:
            self._review_llm_clusters(llm_result, auto_accept=False)
            return

        self._jaccard_clustering()

    def _try_llm_clustering(self):
        from src.config import LLM_API_KEY
        if not LLM_API_KEY:
            return None

        G = C["green"]; CY = C["cyan"]; Y = C["yellow"]; R = C["reset"]; D = C["dim"]

        users_data = []
        for rep in self.reports:
            routines = []
            for r in rep.get("routines_summary", []):
                code = r.get("routine", "")
                desc = r.get("description", "")
                if code:
                    routines.append({"code": code, "description": desc, "permissions": routine_permissions(r)})
            users_data.append({
                "user": rep["user"],
                "routines": routines,
            })

        from src.llm_categorizer import suggest_clusters
        llm_result = suggest_clusters(users_data)

        if not llm_result or not llm_result.get("clusters"):
            return None

        raw_clusters = llm_result.get("clusters", [])
        print(f"  {D}LLM retornou {len(raw_clusters)} conjuntos brutos{R}")

        clusters = normalize_tier3_sets(raw_clusters, self.reports, routine_user_metrics=self._routine_user_metrics)
        if self._routine_user_metrics:
            total_assigned = sum(len(c.get("users", [])) for c in clusters)
            print(f"  {D}Telemetria por usuario ativa: {len(self._routine_user_metrics)} rotinas com dados de uso{R}")
        print(f"  {D}Validacao local: {len(clusters)} conjuntos aproveitados | {max(len(raw_clusters) - len(clusters), 0)} descartados{R}")
        if not clusters:
            print(f"  {Y}LLM retornou conjuntos, mas todos foram descartados na validacao local. Alternando para modo manual (Jaccard).{R}")
            return None
        all_users_set = set(rep["user"] for rep in self.reports)
        clustered_users = set()
        for c in clusters:
            clustered_users |= set(c.get("users", []))

        unclustered = llm_result.get("unclustered", [])
        unclustered_set = set(unclustered) | (all_users_set - clustered_users)

        if unclustered_set:
            print(f"  {D}Usuarios sem conjunto funcional: {', '.join(sorted(unclustered_set)[:10])}{R}")

        return clusters

    def _review_llm_clusters(self, llm_clusters, auto_accept=False):
        G = C["green"]; CY = C["cyan"]; Y = C["yellow"]; R = C["reset"]; D = C["dim"]; B = C["bold"]
        existing_rules = None
        if self.conn is not None:
            try:
                from src.tier3 import load_existing_rules, match_profile_to_existing_rules
                existing_rules = load_existing_rules(self.conn)
            except Exception:
                existing_rules = None

        print()
        for idx, c in enumerate(llm_clusters, 1):
            name = c.get("name", f"CLUSTER_{idx}")
            reason = c.get("reason", "")
            users = c.get("users", [])
            routines = c.get("routines", c.get("common_routines", []))

            print(f"  {CY}{chr(0x250C)}{'─' * 52}{chr(0x2510)}{R}")
            print(f"  {CY}{chr(0x2502)}{R} {B}Conjunto #{idx}: {G}{name}{R}")
            if reason:
                print(f"  {CY}{chr(0x2502)}{R} {D}Motivo: {reason}{R}")
            print(f"  {CY}{chr(0x2502)}{R} Usuarios ({len(users)}): {', '.join(users[:8])}{'...' if len(users) > 8 else ''}")
            print(f"  {CY}{chr(0x2502)}{R} Rotinas relacionadas: {len(routines)}")
            sample = routines[:6]
            sample_labels = [routine_code(item) for item in sample]
            print(f"  {CY}{chr(0x2502)}{R}   Ex: {', '.join(sample_labels)}{'...' if len(routines) > 6 else ''}")
            print(f"  {CY}{chr(0x2514)}{'─' * 52}{chr(0x2518)}{R}")

        print()
        if not auto_accept:
            print(f"  {B}[A]{R} Aceitar todos  {D}[E]{R} Editar nomes  {D}[M]{R} Modo manual (Jaccard)  {D}[X]{R} Cancelar")
            action = input(f"  Opcao: ").strip().upper()

            if action == "X":
                print(f"  {Y}Cancelado. Conjuntos nao foram criados.{R}")
                return

            if action == "M":
                print(f"  {Y}Alternando para modo manual (Jaccard)...{R}")
                self._jaccard_clustering()
                return

            if action == "E":
                llm_clusters = self._edit_llm_clusters(llm_clusters)
                if not llm_clusters:
                    return

        for c in llm_clusters:
            users = c.get("users", [])
            if not users:
                name = (c.get("name") or "").strip().upper()
                print(f"  {Y}Conjunto {name} ignorado: nenhum usuario vinculado{R}")
                continue

            name = (c.get("name") or "").strip().upper()
            if not name.startswith("P_CJ_") and not name.startswith("P_PF_"):
                name = f"P_CJ_{name}"
            if len(name) > 20:
                name = name[:20]

            if not c.get("reuses_existing_rule") and existing_rules:
                try:
                    from src.tier3 import match_profile_to_existing_rules
                    reused_rule = match_profile_to_existing_rules(c.get("routines", c.get("common_routines", [])), existing_rules)
                except Exception:
                    reused_rule = None
                if reused_rule:
                    c["reuses_existing_rule"] = reused_rule
                    c["rule_status_label"] = f"Reaproveita {reused_rule}"

            self.tier3_routines[name] = {
                "routines": list(c.get("routines", c.get("common_routines", []))),
                "members": c.get("users", []),
            }
            if c.get("reuses_existing_rule"):
                self.tier3_routines[name]["reuses_existing_rule"] = c["reuses_existing_rule"]
            label = "Criado"
            if c.get("reuses_existing_rule"):
                label = f"Reaproveitando {c['reuses_existing_rule']}"
            print(f"  {G}{label}: {name}{R}")

    def _edit_llm_clusters(self, llm_clusters):
        G = C["green"]; Y = C["yellow"]; R = C["reset"]; D = C["dim"]; B = C["bold"]

        print(f"\n  {B}Edicao de nomes dos conjuntos funcionais:{R}")
        print(f"  {D}Digite o novo nome ou ENTER para manter / 'p' para pular{R}")
        print()

        result = []
        for idx, c in enumerate(llm_clusters, 1):
            name = c.get("name", f"CLUSTER_{idx}")
            users = c.get("users", [])
            val = input(f"  Conjunto #{idx} ({', '.join(users[:3])}...) [{name}]: ").strip()
            if val.lower() == "p":
                continue
            if val:
                c["name"] = val.upper()
            result.append(c)

        return result

    def _jaccard_clustering(self):
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
                    members = sorted(members)
                    if self._routine_user_metrics:
                        from src.tier3 import _user_has_any_telemetry
                        members = [m for m in members if _user_has_any_telemetry(m, sorted(common), self._routine_user_metrics)]
                    if len(members) >= MIN_CLUSTER_SIZE:
                        clusters.append({
                            "members": members,
                            "common_routines": sorted(common),
                            "depts": sorted(set(user_dept.get(m, "") for m in members)),
                        })

        if not clusters:
            print(f"  {D}Nenhum conjunto manual detectado por similaridade.{R}")
            return

        print(f"\n  {G}Conjuntos manuais detectados: {len(clusters)}{R}")
        print(f"  {D}Threshold de similaridade: {CLUSTER_SIMILARITY_THRESHOLD} | Pares analisados: {pairs_checked}{R}")
        print()

        for idx, cl in enumerate(clusters, 1):
            default_name = self._suggest_manual_cluster_name(cl["common_routines"])

            print(f"  {CY}{chr(0x250C)}{'─' * 50}{chr(0x2510)}{R}")
            print(f"  {CY}{chr(0x2502)}{R} {B}Conjunto #{idx}{R}")
            print(f"  {CY}{chr(0x2502)}{R} Usuarios: {', '.join(cl['members'][:8])}{'...' if len(cl['members']) > 8 else ''}")
            print(f"  {CY}{chr(0x2502)}{R} Departamentos: {', '.join(cl['depts'])}")
            print(f"  {CY}{chr(0x2502)}{R} Rotinas relacionadas: {len(cl['common_routines'])}")
            sample = cl["common_routines"][:6]
            print(f"  {CY}{chr(0x2502)}{R}   Ex: {', '.join(sample)}{'...' if len(cl['common_routines']) > 6 else ''}")
            print(f"  {CY}{chr(0x2502)}{R} Sugestao de nome: {G}{default_name}{R}")
            print(f"  {CY}{chr(0x2514)}{'─' * 50}{chr(0x2518)}{R}")

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
            covered_tier123.update(routine_code(item) for item in info["routines"])

        total_exclusive = 0
        for rep in self.reports:
            user = rep["user"]
            user_routines = self._user_routine_set(rep)
            dept = rep.get("user_depto", "").strip()
            dept_common = self.tier2_routines.get(dept, set())
            tier3_for_user = set()
            for info in self.tier3_routines.values():
                if user in info["members"]:
                    tier3_for_user |= set(routine_code(r) for r in info["routines"])

            covered_user = self.tier1_routines | dept_common | tier3_for_user
            exclusive = user_routines - covered_user

            if exclusive:
                self.tier4_routines[user] = exclusive
                total_exclusive += 1

        print(f"  Usuarios com rotinas exclusivas: {G}{total_exclusive}{R}")
        if total_exclusive:
            for user, routines in sorted(self.tier4_routines.items()):
                print(f"  {D}{user}: {len(routines)} rotinas exclusivas{R}")

    def _promote_shared_residual_clusters(self, min_users=2, min_routines=2, user_overlap_threshold=0.70):
        G = C["green"]; Y = C["yellow"]; R = C["reset"]; D = C["dim"]; B = C["bold"]; CY = C["cyan"]

        if not self.tier4_routines:
            return

        domain_prefixes = {}
        for routine in sorted(set().union(*self.tier4_routines.values())):
            prefix = routine[:4] if not routine or not routine[0].isdigit() else routine[:5]
            domain_prefixes.setdefault(prefix, []).append(routine)

        promoted_count = 0
        for prefix, routines in sorted(domain_prefixes.items()):
            if len(routines) < min_routines:
                continue

            routine_users = {}
            for rt in routines:
                routine_users[rt] = sorted(
                    user for user, rt_set in self.tier4_routines.items() if rt in rt_set
                )

            candidates = []
            for i in range(len(routines)):
                for j in range(i + 1, len(routines)):
                    rt_a, rt_b = routines[i], routines[j]
                    users_a = set(routine_users[rt_a])
                    users_b = set(routine_users[rt_b])
                    if len(users_a) < min_users or len(users_b) < min_users:
                        continue
                    union_size = len(users_a | users_b)
                    if union_size == 0:
                        continue
                    overlap = len(users_a & users_b) / union_size
                    if overlap >= user_overlap_threshold:
                        common_users = users_a & users_b
                        candidates.append((rt_a, rt_b, sorted(common_users), overlap))

            if not candidates:
                continue

            promoted_routines = set()
            promoted_users_map = {}
            for rt_a, rt_b, common, overlap in sorted(candidates, key=lambda c: (-len(c[2]), -c[3])):
                if rt_a in promoted_routines and rt_b in promoted_routines:
                    existing = set()
                    for u in promoted_users_map.values():
                        existing |= u
                    new_common = set(common) - existing
                    if len(new_common) < min_users:
                        continue

                promoted_routines.add(rt_a)
                promoted_routines.add(rt_b)
                for u in common:
                    promoted_users_map.setdefault(u, set()).update([rt_a, rt_b])

            if len(promoted_routines) < min_routines:
                continue

            domain_label = _prefix_domain_label(prefix)
            name = f"P_CJ_{domain_label}"[:20]
            counter = 1
            base_name = name
            while name in self.tier3_routines:
                name = f"{base_name[:17]}_{counter:02d}"[:20]
                counter += 1

            valid_users = {rep["user"] for rep in self.reports}

            all_users = sorted(u for u in promoted_users_map.keys() if u in valid_users)
            if self._routine_user_metrics:
                from src.tier3 import _user_has_any_telemetry
                all_users = [u for u in all_users if _user_has_any_telemetry(u, list(promoted_routines), self._routine_user_metrics)]
            if len(all_users) < min_users:
                print(f"  {D}Residuais {prefix}: apenas {len(all_users)} usuario(s), ignorado{R}")
                continue

            routines_out = []
            for rt in sorted(promoted_routines):
                perms_union = set()
                for user in all_users:
                    for rep in self.reports:
                        if rep.get("user") == user:
                            perms_union |= set(routine_permissions(
                                {"routine": rt, "features": self._routine_features(rep, rt)}
                            ))
                            break
                routines_out.append(
                    {"code": rt, "permissions": sorted(perms_union)}
                    if perms_union
                    else rt
                )

            existing_match = match_profile_to_existing_rules(routines_out, self._existing_rules)
            stored_name = name
            if existing_match:
                stored_name = existing_match
                print(f"  {G}Reaproveitando {existing_match}: {name} ({len(all_users)} usuarios, {len(promoted_routines)} rotinas){R}")
            else:
                print(f"  {G}Promovido {domain_label}: {name} ({len(all_users)} usuarios, {len(promoted_routines)} rotinas){R}")

            self.tier3_routines[stored_name] = {
                "routines": routines_out,
                "members": all_users,
            }
            sample = sorted(promoted_routines)[:6]
            print(f"    {D}Rotinas: {', '.join(sample)}{'...' if len(promoted_routines) > 6 else ''}{R}")
            promoted_count += 1

        singles_promoted = 0
        already_promoted = set()
        for info in self.tier3_routines.values():
            for raw in info.get("routines", []):
                already_promoted.add(routine_code(raw))

        counted_routines = set()
        for user_rt_set in self.tier4_routines.values():
            counted_routines.update(user_rt_set)

        for rt in sorted(counted_routines):
            if rt in already_promoted:
                continue

            users = sorted(
                user for user, user_rt_set in self.tier4_routines.items()
                if rt in user_rt_set
            )
            if self._routine_user_metrics:
                from src.tier3 import _user_has_any_telemetry
                users = [u for u in users if _user_has_any_telemetry(u, [rt], self._routine_user_metrics)]
            if len(users) < min_users:
                continue

            prefix = rt[:4] if not rt or not rt[0].isdigit() else rt[:5]
            domain_label = _prefix_domain_label(prefix)
            rt_safe = rt[:15].replace(" ", "_")
            name = f"P_CJ_{rt_safe}"[:20]
            counter = 1
            base_name = name
            while name in self.tier3_routines:
                name = f"{base_name[:17]}_{counter:02d}"[:20]
                counter += 1

            perms_union = set()
            for user in users:
                for rep in self.reports:
                    if rep.get("user") == user:
                        perms_union |= set(routine_permissions(
                            {"routine": rt, "features": self._routine_features(rep, rt)}
                        ))
                        break

            routines_out = [
                {"code": rt, "permissions": sorted(perms_union)}
                if perms_union
                else rt
            ]

            existing_match = match_profile_to_existing_rules(routines_out, self._existing_rules)
            stored_name = name
            if existing_match:
                stored_name = existing_match
                print(f"  {G}Reaproveitando {existing_match}: {name} ({len(users)} usuarios, rotina {rt}){R}")
            else:
                print(f"  {G}Promovido individual {domain_label}: {name} ({len(users)} usuarios, rotina {rt}){R}")

            self.tier3_routines[stored_name] = {
                "routines": routines_out,
                "members": users,
            }
            singles_promoted += 1

        if promoted_count or singles_promoted:
            self.tier4_routines = {}
            self._compute_tier4()
            total = promoted_count + singles_promoted
            detail = f" ({promoted_count} pares + {singles_promoted} individuais)" if promoted_count and singles_promoted else ""
            print(f"  {G}{total} conjuntos promovidos de residuais compartilhados para TIER3{detail}{R}")

    def _generate_sql(self):
        G = C["green"]; CY = C["cyan"]; R = C["reset"]; D = C["dim"]; B = C["bold"]; Y = C["yellow"]
        start_rule_seq = self.new_rule_seq if hasattr(self, "new_rule_seq") else None
        self._total_features = 0
        self._total_transacts = 0
        self._total_user_rule_links = 0

        reused_tier3 = sum(1 for info in self.tier3_routines.values() if info.get("reuses_existing_rule"))
        print(f"  {D}Entrada para o SQL:{R}")
        print(f"  {D}  - Usuarios processados: {len(self.reports)}{R}")
        print(f"  {D}  - Tier 1: {1 if self.tier1_routines else 0} regra geral{R}")
        print(f"  {D}  - Tier 2: {len(self.tier2_routines)} regras por departamento{R}")
        print(f"  {D}  - Tier 3: {len(self.tier3_routines)} conjuntos funcionais{R}")
        if reused_tier3:
            print(f"  {D}    - {reused_tier3} reaproveitam regras existentes{R}")
        print(f"  {D}  - Tier 4: {len(self.tier4_routines)} regras exclusivas por usuario{R}")
        print(f"  {D}Gerando INSERTs em SYS_RULES, SYS_RULES_FEATURES, SYS_RULES_TRANSACT e SYS_RULES_USR_RULES...{R}")

        rules_pk = self._resolve_col("SYS_RULES", ["RL__ID", "RUL_ID", "ID"])
        rules_name = self._resolve_col("SYS_RULES", ["RL__CODIGO", "RUL_NAME", "NAME", "RULES_NAME"])
        rules_type = self._resolve_col("SYS_RULES", ["RUL_TYPE", "TYPE", "RULES_TYPE"])
        rules_desc = self._resolve_col("SYS_RULES", ["RL__DESCRI", "RUL_DESCRIPTION", "DESCRIPTION", "RULES_DESC"])

        max_id = self._get_max_id("SYS_RULES", rules_pk)
        self.new_rule_seq = extract_auto_rule_sequence(max_id) + 1
        self.new_rule_id = None
        start_rule_seq = self.new_rule_seq

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

        trn_rul = self._resolve_col("SYS_RULES_TRANSACT", ["RL__ID", "RUL_ID", "ID"])
        trn_func = self._resolve_col("SYS_RULES_TRANSACT", ["RL__ROTINA", "FUNCTION", "ROTINA"])
        trn_desc = self._resolve_col("SYS_RULES_TRANSACT", ["RL__DESROT", "DESCRIPTION", "DESROT"])
        trn_access = self._resolve_col("SYS_RULES_TRANSACT", ["RL__ACESSO", "ACCESS"])
        trn_checksum = self._resolve_col("SYS_RULES_TRANSACT", ["RL__CHKSUM", "CHKSUM"])
        trn_del = self._resolve_col("SYS_RULES_TRANSACT", ["D_E_L_E_T_"])

        usr_usr_col = self._resolve_col("SYS_RULES_USR_RULES",
            ["USER_ID", "USR_ID", "URR_USR_ID", "RUR_USR_ID"])
        usr_rul_col = self._resolve_col("SYS_RULES_USR_RULES",
            ["USR_RL_ID", "RUL_ID", "URR_RUL_ID", "RUR_RUL_ID"])

        login_to_user_id = {
            rep["user"]: str(rep.get("user_id") or rep["user"]).strip() or rep["user"]
            for rep in self.reports
            if rep.get("user")
        }
        all_users = sorted(set(login_to_user_id.values()))

        dept_users = {}
        for rep in self.reports:
            dept = rep.get("user_depto", "").strip()
            if not dept:
                dept = "SEM_DEPARTAMENTO"
            dept_users.setdefault(dept, []).append(login_to_user_id.get(rep["user"], rep["user"]))

        bindings = []

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
            bindings.append((self.new_rule_id, all_users, f"P_{self.empresa_name}"))
            for routine in sorted(self.tier1_routines):
                self._append_features(lines, routine,
                    fet_pk, fet_rul, fet_func, fet_feat, fet_access, fet_menuoper, fet_menudef,
                    trn_rul, trn_func, trn_desc, trn_access, trn_checksum, trn_del)
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
                bindings.append((self.new_rule_id, dept_users.get(dept, []), rule_name))
                for routine in sorted(routines):
                    self._append_features(lines, routine,
                        fet_pk, fet_rul, fet_func, fet_feat, fet_access, fet_menuoper, fet_menudef,
                        trn_rul, trn_func, trn_desc, trn_access, trn_checksum, trn_del)
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
                reused = info.get("reuses_existing_rule")
                lines.append(f"-- Conjunto: {group_name}")
                lines.append(f"-- Membros: {members_str}")
                if reused:
                    lines.append(f"-- REGRA EXISTENTE: {reused} (INSERT ignorado)")
                else:
                    self._append_rule(lines, group_name,
                        f"Conjunto cross-departamento - {group_name}",
                        rules_pk, rules_name, rules_type, rules_desc)
                    bindings.append((self.new_rule_id, [login_to_user_id.get(user, user) for user in sorted(info["members"])], group_name))
                if not reused:
                    for routine in sorted(info["routines"], key=lambda item: routine_code(item)):
                        self._append_features(lines, routine,
                            fet_pk, fet_rul, fet_func, fet_feat, fet_access, fet_menuoper, fet_menudef,
                            trn_rul, trn_func, trn_desc, trn_access, trn_checksum, trn_del)
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
                bindings.append((self.new_rule_id, [login_to_user_id.get(user, user)], rule_name))
                for routine in sorted(routines):
                    self._append_features(lines, routine,
                        fet_pk, fet_rul, fet_func, fet_feat, fet_access, fet_menuoper, fet_menudef,
                        trn_rul, trn_func, trn_desc, trn_access, trn_checksum, trn_del)
        else:
            lines.append("-- Nenhum usuario com rotinas exclusivas")
            lines.append("")

        lines.append("-- ==============================================")
        lines.append("-- VINCULACAO USUARIOS AS REGRAS")
        lines.append("-- ==============================================")
        lines.append("")
        if usr_usr_col and usr_rul_col and bindings:
            for rule_id, users, rule_name in bindings:
                lines.append(f"-- {rule_name} ({len(users)} usuarios)")
                for user in sorted(users):
                    lines.append(f"INSERT INTO SYS_RULES_USR_RULES ({usr_usr_col}, {usr_rul_col})")
                    lines.append(f"VALUES ({self._sanitize(user)}, {self._sanitize(rule_id)});")
                    self._total_user_rule_links += 1
                lines.append("")
        elif not bindings:
            lines.append("-- Nenhuma vinculacao gerada (sem regras criadas)")
            lines.append("")
        else:
            lines.append("-- Colunas de vinculacao nao encontradas em SYS_RULES_USR_RULES")
            lines.append("")

        lines.append("COMMIT")
        lines.append("")
        total_rules = self.new_rule_seq - start_rule_seq
        lines.append(f"-- Total de regras criadas: {total_rules}")
        lines.append(f"-- Total de features inseridas: {self._total_features}")
        lines.append("-- ATENCAO: Verifique os valores antes de executar em producao!")

        sql_content = "\n".join(lines)
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        filename = f"{self.empresa_name}_organizacional.sql"
        filepath = os.path.join(OUTPUT_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(sql_content)

        print(f"  {G}Script SQL salvo em: {B}{filepath}{R}")
        print(f"  {D}SQL gerado com sucesso:{R}")
        print(f"  {D}  - SYS_RULES: {total_rules} inserts{R}")
        print(f"  {D}  - SYS_RULES_FEATURES: {self._total_features} inserts{R}")
        print(f"  {D}  - SYS_RULES_TRANSACT: {self._total_transacts} inserts{R}")
        print(f"  {D}  - SYS_RULES_USR_RULES: {self._total_user_rule_links} inserts{R}")

    def _append_rule(self, lines, rule_name, rule_desc,
                     rules_pk, rules_name, rules_type, rules_desc):
        insert_cols = []
        insert_vals = []
        self.new_rule_id = format_auto_rule_id(self.new_rule_seq)
        if rules_pk:
            insert_cols.append(rules_pk)
            insert_vals.append(self._sanitize(self.new_rule_id))
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
        self.new_rule_seq += 1

    def _append_features(self, lines, routine_name,
                         fet_pk, fet_rul, fet_func, fet_feat, fet_access, fet_menuoper, fet_menudef,
                         trn_rul, trn_func, trn_desc, trn_access, trn_checksum, trn_del):
        required_permissions = set()
        if isinstance(routine_name, dict):
            required_permissions = set(routine_name.get("permissions", []) or [])
        routine_name = routine_code(routine_name)
        features = None
        description = ""
        for rep in self.reports:
            for r in rep.get("routines_summary", []):
                if r.get("routine") == routine_name:
                    feats = r.get("features", {})
                    description = r.get("description", "")
                    if feats:
                        features = feats
                        break
            if features:
                break

        if not features:
            features = {"": {"access_raw": "", "menu_oper": 0, "menu_def": ""}}
            feat_item = 0
        else:
            feat_item = 1

        self._append_transact(lines, self.new_rule_id, routine_name, description, features,
            trn_rul, trn_func, trn_desc, trn_access, trn_checksum, trn_del)

        for feat_name, feat_info in features.items():
            if required_permissions and feat_name not in required_permissions:
                continue
            access_value = feat_info.get("access_raw", "1")
            menu_oper = feat_info.get("menu_oper")
            menu_def = (feat_info.get("menu_def") or "").strip()
            insert_cols = []
            insert_vals = []

            if fet_pk:
                insert_cols.append(fet_pk)
                insert_vals.append(str(feat_item))
            if fet_rul:
                insert_cols.append(fet_rul)
                insert_vals.append(self._sanitize(self.new_rule_id))
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
                insert_vals.append(str(int(float(menu_oper))))
            if fet_menudef and menu_def:
                insert_cols.append(fet_menudef)
                insert_vals.append(self._sanitize(menu_def))

            comment = f"-- {routine_name} | {feat_name}"
            lines.append(comment)
            lines.append(f"INSERT INTO SYS_RULES_FEATURES ({', '.join(insert_cols)})")
            lines.append(f"VALUES ({', '.join(insert_vals)});")
            feat_item += 1
            self._total_features += 1
        lines.append("")

    def _append_transact(self, lines, rule_id, routine_name, description, features,
                         trn_rul, trn_func, trn_desc, trn_access, trn_checksum, trn_del):
        insert_cols = []
        insert_vals = []
        if trn_rul:
            insert_cols.append(trn_rul)
            insert_vals.append(self._sanitize(rule_id))
        if trn_func:
            insert_cols.append(trn_func)
            insert_vals.append(self._sanitize(routine_name))
        if trn_desc:
            insert_cols.append(trn_desc)
            insert_vals.append(self._sanitize(self._fit_column_value("SYS_RULES_TRANSACT", trn_desc, description)))
        if trn_access:
            access_value = "1"
            for feat_info in (features or {}).values():
                candidate = str(feat_info.get("access_raw", "")).strip()
                if candidate:
                    access_value = candidate
                    break
            insert_cols.append(trn_access)
            insert_vals.append(self._sanitize(access_value))
        if trn_checksum:
            insert_cols.append(trn_checksum)
            insert_vals.append(self._sanitize(""))
        if trn_del:
            insert_cols.append(trn_del)
            insert_vals.append(self._sanitize(" "))
        if insert_cols:
            lines.append(f"INSERT INTO SYS_RULES_TRANSACT ({', '.join(insert_cols)})")
            lines.append(f"VALUES ({', '.join(insert_vals)});")
            self._total_transacts += 1


def generate_delta_sql(inventory, schema, empresa_name):
    from src.discovery import column_exists
    from src.privilege_generator import extract_auto_rule_sequence, format_auto_rule_id

    def _resolve(table, candidates):
        return column_exists(schema, table, candidates)

    def _sanitize(value):
        if value is None:
            return "NULL"
        if isinstance(value, (int, float)):
            return str(value)
        return "'" + str(value).replace("'", "''") + "'"

    rules = inventory.get("rules", []) or []
    deleted_bindings = inventory.get("deleted_bindings", []) or []

    rules_pk = _resolve("SYS_RULES", ["RL__ID", "RUL_ID", "ID"])
    rules_name = _resolve("SYS_RULES", ["RL__CODIGO", "RUL_NAME", "NAME", "RULES_NAME"])
    rules_type = _resolve("SYS_RULES", ["RUL_TYPE", "TYPE", "RULES_TYPE"])
    rules_desc = _resolve("SYS_RULES", ["RL__DESCRI", "RUL_DESCRIPTION", "DESCRIPTION", "RULES_DESC"])

    fet_pk = _resolve("SYS_RULES_FEATURES", ["RL__ITEM", "FET_ID", "ID", "RFE_ID"])
    fet_rul = _resolve("SYS_RULES_FEATURES", ["RL__ID", "FET_RUL_ID", "RUL_ID", "RFE_RUL_ID"])
    fet_func = _resolve("SYS_RULES_FEATURES", ["RL__ROTINA", "FET_FUNCTION", "FUNCTION", "RFE_FUNCTION", "RFE_ROTINA"])
    fet_feat = _resolve("SYS_RULES_FEATURES", ["RL__DESMDEF", "FET_FEATURE", "FEATURE", "RFE_FEATURE", "RFE_DESMDEF"])
    fet_access = _resolve("SYS_RULES_FEATURES", ["RL__ACESSO", "FET_ACCESS", "ACCESS", "RFE_ACCESS", "RFE_ACESSO"])
    fet_menuoper = _resolve("SYS_RULES_FEATURES", ["RL__MENUOPER", "MENUOPER"])
    fet_menudef = _resolve("SYS_RULES_FEATURES", ["RL__MENUDEF", "MENUDEF"])

    trn_rul = _resolve("SYS_RULES_TRANSACT", ["RL__ID", "RUL_ID", "ID"])
    trn_func = _resolve("SYS_RULES_TRANSACT", ["RL__ROTINA", "FUNCTION", "ROTINA"])
    trn_desc = _resolve("SYS_RULES_TRANSACT", ["RL__DESROT", "DESCRIPTION", "DESROT"])
    trn_access = _resolve("SYS_RULES_TRANSACT", ["RL__ACESSO", "ACCESS"])
    trn_checksum = _resolve("SYS_RULES_TRANSACT", ["RL__CHKSUM", "CHKSUM"])
    trn_del = _resolve("SYS_RULES_TRANSACT", ["D_E_L_E_T_"])

    usr_usr_col = _resolve("SYS_RULES_USR_RULES", ["USER_ID", "USR_ID", "URR_USR_ID", "RUR_USR_ID"])
    usr_rul_col = _resolve("SYS_RULES_USR_RULES", ["USR_RL_ID", "RUL_ID", "URR_RUL_ID", "RUR_RUL_ID"])

    rule_seq = 1
    feat_item = 1
    total_features = 0
    total_transacts = 0
    total_user_links = 0
    total_deletes = 0

    lines = []
    lines.append("-- ==============================================")
    lines.append("-- Script de privilegios DELTA")
    lines.append(f"-- Empresa: {empresa_name}")
    lines.append("-- Gerado a partir do inventario consolidado")
    lines.append("-- ==============================================")
    lines.append("")

    has_deletes = bool(deleted_bindings) or any(r.get("_marked_for_delete") for r in rules)
    if has_deletes:
        lines.append("-- ⚠️  ATENCAO  ⚠️")
        lines.append("-- Este script contem comandos de SOFT DELETE (D_E_L_E_T_ = '*').")
        lines.append("-- Revise cuidadosamente antes de executar em producao.")
        lines.append("")

    lines.append("BEGIN TRANSACTION")
    lines.append("")

    new_rule_id = None

    for rule in rules:
        if rule.get("_marked_for_delete"):
            lines.append(f"-- REGRA MARCADA PARA REMOCAO: {rule.get('rule_name', '')}")
            lines.append("-- (soft delete nao implementado automaticamente para regras inteiras)")
            lines.append("")
            continue

        action = rule.get("action", "MANTER")
        source = rule.get("source", "")

        if action == "MANTER" and source == "EXISTENTE":
            lines.append(f"-- Regra existente sem alteracoes: {rule.get('rule_name', '')}")
            if rule.get("has_excess"):
                lines.append(f"-- ALERTA: regra concede acessos extras alem do necessario")
            lines.append("")
            continue

        if action in ("CRIAR", "COMPLEMENTAR"):
            if action == "CRIAR":
                new_rule_id = format_auto_rule_id(rule_seq)
                rule_seq += 1
                insert_cols = []
                insert_vals = []
                if rules_pk:
                    insert_cols.append(rules_pk)
                    insert_vals.append(_sanitize(new_rule_id))
                if rules_name:
                    insert_cols.append(rules_name)
                    insert_vals.append(_sanitize(rule.get("rule_name", "")))
                if rules_desc:
                    insert_cols.append(rules_desc)
                    insert_vals.append(_sanitize(rule.get("rule_description", "")))
                if rules_type:
                    insert_cols.append(rules_type)
                    insert_vals.append("' '")
                lines.append(f"-- NOVA REGRA: {rule.get('rule_name', '')}")
                lines.append(f"INSERT INTO SYS_RULES ({', '.join(insert_cols)})")
                lines.append(f"VALUES ({', '.join(insert_vals)});")
                lines.append("")
            else:
                lines.append(f"-- REGRA EXISTENTE: {rule.get('rule_name', '')} — apenas complementos abaixo")
                lines.append("")
                new_rule_id = rule.get("rule_id", "")

            for rt in rule.get("routines", []) or []:
                rt_code = rt.get("routine", "")
                rt_desc = rt.get("description", "")
                features = rt.get("features", []) or []
                missing_features = [f for f in features if f.get("status") == "FALTANTE"]

                if missing_features and action == "COMPLEMENTAR":
                    lines.append(f"-- Complemento: {rt_code}")
                    trn_cols = []
                    trn_vals = []
                    if trn_rul:
                        trn_cols.append(trn_rul)
                        trn_vals.append(_sanitize(new_rule_id))
                    if trn_func:
                        trn_cols.append(trn_func)
                        trn_vals.append(_sanitize(rt_code))
                    if trn_desc:
                        trn_cols.append(trn_desc)
                        trn_vals.append(_sanitize(rt_desc[:40] if rt_desc else ""))
                    if trn_access:
                        trn_cols.append(trn_access)
                        trn_vals.append(_sanitize("1"))
                    if trn_checksum:
                        trn_cols.append(trn_checksum)
                        trn_vals.append(_sanitize(""))
                    if trn_del:
                        trn_cols.append(trn_del)
                        trn_vals.append(_sanitize(" "))
                    if trn_cols:
                        lines.append(f"INSERT INTO SYS_RULES_TRANSACT ({', '.join(trn_cols)})")
                        lines.append(f"VALUES ({', '.join(trn_vals)});")
                        total_transacts += 1

                elif action == "CRIAR":
                    trn_cols = []
                    trn_vals = []
                    if trn_rul:
                        trn_cols.append(trn_rul)
                        trn_vals.append(_sanitize(new_rule_id))
                    if trn_func:
                        trn_cols.append(trn_func)
                        trn_vals.append(_sanitize(rt_code))
                    if trn_desc:
                        trn_cols.append(trn_desc)
                        trn_vals.append(_sanitize(rt_desc[:40] if rt_desc else ""))
                    if trn_access:
                        trn_cols.append(trn_access)
                        trn_vals.append(_sanitize("1"))
                    if trn_checksum:
                        trn_cols.append(trn_checksum)
                        trn_vals.append(_sanitize(""))
                    if trn_del:
                        trn_cols.append(trn_del)
                        trn_vals.append(_sanitize(" "))
                    if trn_cols:
                        lines.append(f"-- {rt_code} | {rt_desc}")
                        lines.append(f"INSERT INTO SYS_RULES_TRANSACT ({', '.join(trn_cols)})")
                        lines.append(f"VALUES ({', '.join(trn_vals)});")
                        total_transacts += 1

                for feat in features:
                    if action == "COMPLEMENTAR" and feat.get("status") != "FALTANTE":
                        continue
                    insert_cols = []
                    insert_vals = []
                    if fet_pk:
                        insert_cols.append(fet_pk)
                        insert_vals.append(str(feat_item))
                    if fet_rul:
                        insert_cols.append(fet_rul)
                        insert_vals.append(_sanitize(new_rule_id))
                    if fet_func:
                        insert_cols.append(fet_func)
                        insert_vals.append(_sanitize(rt_code))
                    if fet_feat:
                        insert_cols.append(fet_feat)
                        insert_vals.append(_sanitize(feat.get("feature", "")))
                    if fet_access:
                        insert_cols.append(fet_access)
                        insert_vals.append(_sanitize(str(feat.get("access", "1"))))
                    if fet_menuoper and feat.get("menu_oper") is not None:
                        insert_cols.append(fet_menuoper)
                        insert_vals.append(str(int(float(feat.get("menu_oper", 0)))))
                    if fet_menudef and feat.get("menu_def"):
                        insert_cols.append(fet_menudef)
                        insert_vals.append(_sanitize(feat.get("menu_def", "")))
                    lines.append(f"-- {rt_code} | {feat.get('feature', '')}")
                    lines.append(f"INSERT INTO SYS_RULES_FEATURES ({', '.join(insert_cols)})")
                    lines.append(f"VALUES ({', '.join(insert_vals)});")
                    feat_item += 1
                    total_features += 1
                lines.append("")

            for user in rule.get("users", []) or []:
                login = user.get("login", user.get("user_id", ""))
                uid = user.get("user_id", login)
                lines.append(f"-- Vinculo: {login}")
                lines.append(f"INSERT INTO SYS_RULES_USR_RULES ({usr_usr_col}, {usr_rul_col})")
                lines.append(f"VALUES ({_sanitize(uid)}, {_sanitize(new_rule_id)});")
                total_user_links += 1
            lines.append("")

    if deleted_bindings:
        lines.append("-- ==============================================")
        lines.append("-- SOFT DELETES (vinculos removidos)")
        lines.append("-- ==============================================")
        lines.append("")
        for bind in deleted_bindings:
            lines.append(f"-- Removendo: {bind.get('rule_name', '')} | user {bind.get('user_id', '')}")
            lines.append(f"UPDATE {bind.get('table', 'SYS_RULES_USR_RULES')} SET D_E_L_E_T_ = '*' WHERE USER_ID = {_sanitize(bind.get('user_id', ''))};")
            total_deletes += 1
        lines.append("")

    lines.append("COMMIT")
    lines.append("")
    lines.append(f"-- Total de regras novas criadas: {rule_seq - 1}")
    lines.append(f"-- Total de features inseridas: {total_features}")
    lines.append(f"-- Total de transacts inseridas: {total_transacts}")
    lines.append(f"-- Total de vinculos de usuario: {total_user_links}")
    if total_deletes:
        lines.append(f"-- Total de soft deletes: {total_deletes}")
    lines.append("-- ATENCAO: Verifique os valores antes de executar em producao!")

    return "\n".join(lines)
