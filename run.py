#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
import time
import threading
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database import get_connection, build_connection_string
from src.discovery import discover_columns_for_tables, print_schema_summary
from src.config import SCHEMA_TABLES, OUTPUT_DIR, DB_CONFIG, load_user_config, save_user_config
import src.config as cfg
from src.user_mapper import UserMapper
from src.privilege_generator import PrivilegeGenerator, save_report_json
from src.dashboard import generate_html
from src.tier3 import build_department_analysis, build_equivalent_profile_groups, build_tier4_users, load_existing_rules, normalize_tier3_sets, routine_permissions, user_routine_items


C = {
    "reset": "\033[0m",   "bold": "\033[1m",
    "dim": "\033[2m",     "red": "\033[91m",
    "green": "\033[92m",  "yellow": "\033[93m",
    "blue": "\033[94m",   "cyan": "\033[96m",
    "magenta": "\033[95m","white": "\033[97m",
}
if os.name == "nt":
    os.system("")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SPINNER_CHARS = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


BANNER_LINES = [
    "  ██████╗  ██████╗ ██╗     ██████╗ ██████╗ ███████╗██╗   ██╗  ",
    "  ██╔══██╗██╔═══██╗██║     ██╔══██╗██╔══██╗██╔════╝██║   ██║  ",
    "  ██████╔╝██║   ██║██║     ██████╔╝██████╔╝█████╗  ██║   ██║  ",
    "  ██╔═══╝ ██║   ██║██║     ██╔═══╝ ██╔══██╗██╔══╝  ╚██╗ ██╔╝  ",
    "  ██║     ╚██████╔╝███████╗██║     ██║  ██║███████╗ ╚████╔╝   ",
    "  ╚═╝      ╚═════╝ ╚══════╝╚═╝     ╚═╝  ╚═╝╚══════╝  ╚═══╝    ",
    "                                                        ",
    "     ████████╗ ██████╗ ████████╗██╗   ██╗███████╗       ",
    "     ╚══██╔══╝██╔═══██╗╚══██╔══╝██║   ██║██╔════╝       ",
    "        ██║   ██║   ██║   ██║   ██║   ██║███████╗       ",
    "        ██║   ██║   ██║   ██║   ╚██╗ ██╔╝╚════██║       ",
    "        ██║   ╚██████╔╝   ██║    ╚████╔╝ ███████║       ",
    "        ╚═╝    ╚═════╝    ╚═╝     ╚═══╝  ╚══════╝       ",
    "                                                        ",
    "        Mapeador de Acessos e Privilegios - Protheus      ",
    "                                                        ",
]
W = max(len(line.rstrip("\n")) for line in BANNER_LINES)
_aligned = [f"║{line.ljust(W)}║" for line in BANNER_LINES]
_joined = "\n".join(_aligned)

BANNER = f"""{C["cyan"]}{C["bold"]}
╔{'═' * W}╗
{_joined}
╚{'═' * W}╝
{C["reset"]}"""


def cls():
    os.system("cls" if os.name == "nt" else "clear")


def wait_enter():
    print(f"\n  {C['dim']}{'─' * 54}{C['reset']}")
    input(f"  {C['dim']}Pressione ENTER para voltar ao menu...{C['reset']}")


def _spin_worker(stop_event, prefix):
    i = 0
    while not stop_event.is_set():
        sys.stdout.write(f"\r  {prefix} {C['cyan']}{SPINNER_CHARS[i % len(SPINNER_CHARS)]}{C['reset']}")
        sys.stdout.flush()
        time.sleep(0.08)
        i += 1


def spin_text(prefix, text):
    stop = threading.Event()
    t = threading.Thread(target=_spin_worker, args=(stop, f"{C['cyan']}[{prefix}]{C['reset']}"))
    t.daemon = True
    t.start()
    return stop, prefix


def spin_stop(stop_event, prefix, text, ok=True):
    stop_event.set()
    time.sleep(0.12)
    icon = f"{C['green']}OK{C['reset']}" if ok else f"{C['red']}ERRO{C['reset']}"
    sys.stdout.write(f"\r  {C['cyan']}[{prefix}]{C['reset']} {icon}  {text}\n")
    sys.stdout.flush()


def run_export():
    section("EXPORTAR DADOS")
    spin("Conectando ao banco MSSQL...", 0.6)
    try:
        with get_connection() as conn:
            ok("Conectado com sucesso!")

            section("DISCOVERY")
            spin("Descobrindo estrutura das tabelas...", 1.0)
            schema = discover_columns_for_tables(SCHEMA_TABLES, conn)
            ok()
            print_schema_summary(schema)

            section("GERANDO SQL")
            from src.data_exporter import generate_export_sql
            filepath = generate_export_sql(schema)
            ok()
            success(f"Script SQL salvo em: {C['bold']}{filepath}{C['reset']}")
            print()
            info("Instrucoes:")
            info("  1. Abra o arquivo export.sql no SSMS")
            info("  2. Execute contra o banco Protheus")
            info("  3. Salve o resultado (coluna unica) como export.json")
            info("  4. Opcao 6 no menu para importar o JSON")
    except Exception as e:
        fail(str(e))
        warn("Verifique conexao e credenciais.")


def run_import():
    section("IMPORTAR DADOS")
    default_path = os.path.join(OUTPUT_DIR, "export.json")
    json_path = input(f"  Caminho do arquivo JSON [{default_path}]: ").strip()
    if not json_path:
        json_path = default_path

    if not os.path.exists(json_path):
        error(f"Arquivo nao encontrado: {json_path}")
        return

    from src.data_importer import import_and_set_offline
    if import_and_set_offline(json_path):
        info(f"Modo offline ativo. Pronto para processar.")
        print()
        info("Proximos passos:")
        info("  - Opcao 1: Mapear acessos de um usuario")
        info("  - Opcao 2: Mapear + Gerar script de privilegios")
        info("  - Opcao 3: Mapear + Gerar dashboard HTML")
        info("  - O processamento usara os dados importados (sem conexao ao banco)")
    else:
        error("Falha ao importar dados.")


def run_clean_privileges():
    section("LIMPAR TABELAS DE PRIVILEGIOS")

    lines = []
    lines.append("-- ==============================================")
    lines.append("-- Script de limpeza - Tabelas de Privilegios")
    lines.append("-- ATENCAO: Remove TODOS os registros de privilegios")
    lines.append("-- ==============================================")
    lines.append("")
    lines.append("BEGIN TRANSACTION")
    lines.append("")
    lines.append("DELETE FROM SYS_RULES_USR_RULES;")
    lines.append("DELETE FROM SYS_RULES_GRP_RULES;")
    lines.append("DELETE FROM SYS_RULES_FEATURES;")
    lines.append("DELETE FROM SYS_RULES;")
    lines.append("")
    lines.append("COMMIT")
    lines.append("")

    sql_content = "\n".join(lines)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, "clean_privileges.sql")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(sql_content)

    success(f"Script de limpeza salvo em: {C['bold']}{filepath}{C['reset']}")
    print()
    info("Ordem de execucao recomendada:")
    info("  1. Execute clean_privileges.sql no SSMS")
    info(f"  2. Execute {cfg.EMPRESA_NAME}_organizacional.sql")


def show_offline_banner():
    D = C["dim"]; R = C["reset"]; G = C["green"]
    print(f"  {D}─── {G}MODO OFFLINE{D} ─── Dados carregados do export.json ───{R}")
    print()


def wizard_box(title, subtitle=None):
    cls()
    print(BANNER)
    from src.database import is_offline
    if is_offline():
        show_offline_banner()
    CY = C["cyan"]; R = C["reset"]; B = C["bold"]; D = C["dim"]
    print(f"  {CY}{chr(0x2550) * 56}{R}")
    print(f"  {CY}  {B}{title}{R}")
    if subtitle:
        print(f"  {CY}  {D}{subtitle}{R}")
    print(f"  {CY}{chr(0x2550) * 56}{R}")
    print()


def wizard_step(step, total, text):
    CY = C["cyan"]; B = C["bold"]; R = C["reset"]
    print(f"  {CY}[ETAPA {step}/{total}]{R} {B}{text}{R}")
    print()


def wizard_summary(title, items):
    CY = C["cyan"]; B = C["bold"]; D = C["dim"]; R = C["reset"]
    print(f"  {CY}{chr(0x2500) * 56}{R}")
    print(f"  {B}{title}{R}")
    print(f"  {CY}{chr(0x2500) * 56}{R}")
    for label, value in items:
        print(f"  {D}{label}:{R} {value}")
    print(f"  {CY}{chr(0x2500) * 56}{R}")
    print()


def wizard_prompt_yn(question, default="N"):
    B = C["bold"]; D = C["dim"]; R = C["reset"]
    val = input(f"  {B}{question}{R} (S/N) [{D}{default}{R} | X = cancelar]: ").strip().upper()
    if val == "X":
        return None
    if val == "S":
        return True
    if val == "N":
        return False
    return default.upper() == "S"


# ══════════════════════════════════════════════
# WIZARD — Mapeamento de Acessos
# ══════════════════════════════════════════════

def wizard_mapeamento(current_login="usr001"):
    B = C["bold"]; D = C["dim"]; R = C["reset"]; G = C["green"]; Y = C["yellow"]; CY = C["cyan"]; RD = C["red"]

    login = current_login
    batch = False
    gen_priv = False
    rule_name = ""
    gen_dash = False

    wizard_box("WIZARD — Mapeamento de Acessos", "Passo a passo para mapear usuarios e gerar artefatos")

    # ETAPA 1 — Usuario
    while True:
        wizard_box("WIZARD — Mapeamento de Acessos")
        wizard_step(1, 5, "Qual usuario deseja mapear?")
        info("Digite o login do usuario ou ENTER para mapear TODOS os usuarios.")
        print()
        val = input(f"  {B}Usuario{R} [{D}{login} | ENTER = TODOS | X = cancelar{R}]: ").strip()
        if val.upper() == "X":
            info("Wizard cancelado.")
            return current_login
        if val:
            login = val
            batch = False
        else:
            batch = True
        break

    # ETAPA 2 — Gerar privilegios?
    while True:
        wizard_box("WIZARD — Mapeamento de Acessos")
        wizard_step(2, 5, "Gerar script de privilegios (SQL)?")
        info("Gera script SQL com INSERTs para a tabela SYS_RULES.")
        print()
        result = wizard_prompt_yn("Gerar script SQL?", "N")
        if result is None:
            info("Wizard cancelado.")
            return login
        gen_priv = result
        break

    # ETAPA 3 — Nome da regra
    if gen_priv:
        if batch:
            default_rule = "ACESSOS_BATCH"
        else:
            default_rule = f"ACESSOS_{login.upper()[:8]}"
        while True:
            wizard_box("WIZARD — Mapeamento de Acessos")
            wizard_step(3, 5, "Nome do grupo de regras")
            info("Identificador do grupo de regras no Protheus (max 10 caracteres).")
            print()
            val = input(f"  {B}Nome da regra{R} [{D}{default_rule} | X = cancelar{R}]: ").strip()
            if val.upper() == "X":
                info("Wizard cancelado.")
                return login
            if val:
                rule_name = val
            else:
                rule_name = default_rule
            break
    else:
        rule_name = ""

    # ETAPA 4 — Dashboard?
    step_disp = "4/5" if gen_priv else "3/5"
    step_num = 4 if gen_priv else 3
    while True:
        wizard_box("WIZARD — Mapeamento de Acessos")
        wizard_step(step_num, 5, "Gerar dashboard HTML?")
        info("Gera um dashboard grafico com a arvore de menus e permissoes.")
        print()
        result = wizard_prompt_yn("Gerar dashboard?", "N")
        if result is None:
            info("Wizard cancelado.")
            return login
        gen_dash = result
        break

    # ETAPA 5 — Confirmacao
    while True:
        wizard_box("WIZARD — Mapeamento de Acessos")
        wizard_step(5, 5, "Confirmacao")

        user_disp = login if not batch else f"{Y}TODOS (batch){R}"
        priv_disp = f"{G}SIM{R} ({rule_name})" if gen_priv else f"{D}NAO{R}"
        dash_disp = f"{G}SIM{R}" if gen_dash else f"{D}NAO{R}"

        wizard_summary("Resumo da operacao", [
            ("Usuario       ", user_disp),
            ("Gerar SQL     ", priv_disp),
            ("Gerar Dashboard", dash_disp),
        ])

        val = input(f"  {B}[S]{R} Executar  {D}[E]{R} Refazer  {D}[X]{R} Cancelar\n  {B}Opcao:{R} ").strip().upper()

        if val == "X":
            info("Wizard cancelado.")
            return login
        if val == "S":
            break
        if val == "E":
            return wizard_mapeamento(login)

    # EXECUTAR
    cls()
    print(BANNER)

    if batch:
        run_batch(gen_priv=gen_priv, rule_name=rule_name, gen_dash=gen_dash)
    else:
        report, schema, login_result = run_mapping(login)
        if report:
            if gen_priv:
                run_generate_privileges(report, schema, login_result, rule_name=rule_name)
            if gen_dash:
                run_dashboard(login_result)

    return login


# ══════════════════════════════════════════════
# WIZARD — Exportar Dados
# ══════════════════════════════════════════════

def wizard_export():
    B = C["bold"]; D = C["dim"]; R = C["reset"]; G = C["green"]

    wizard_box("WIZARD — Exportar Dados", "Gerar script SQL para extracao offline")

    # ETAPA 1 — Confirmacao
    while True:
        wizard_box("WIZARD — Exportar Dados")
        wizard_step(1, 2, "Confirmar exportacao")
        info("Sera gerado um script SQL para extrair todas as tabelas do schema.")
        info("Execute o script no SSMS e salve o resultado como export.json.")
        print()
        result = wizard_prompt_yn("Confirmar exportacao?", "S")
        if result is None:
            info("Wizard cancelado.")
            return
        if not result:
            info("Exportacao cancelada.")
            return
        break

    # ETAPA 2 — Executar
    wizard_box("WIZARD — Exportar Dados")
    wizard_step(2, 2, "Executando...")
    run_export()


# ══════════════════════════════════════════════
# WIZARD — Importar Dados
# ══════════════════════════════════════════════

def wizard_import():
    B = C["bold"]; D = C["dim"]; R = C["reset"]; G = C["green"]

    wizard_box("WIZARD — Importar Dados", "Carregar dados offline (export.json)")

    default_path = os.path.join(OUTPUT_DIR, "export.json")
    json_path = default_path

    # ETAPA 1 — Caminho do arquivo
    while True:
        wizard_box("WIZARD — Importar Dados")
        wizard_step(1, 2, "Caminho do arquivo JSON")
        info("Arquivo export.json gerado pela opcao de exportacao.")
        print()
        val = input(f"  {B}Caminho{R} [{D}{default_path} | X = cancelar{R}]: ").strip()
        if val.upper() == "X":
            info("Wizard cancelado.")
            return
        if val:
            json_path = val
        elif not os.path.exists(json_path):
            error(f"Arquivo padrao nao encontrado: {json_path}")
            continue
        if not os.path.exists(json_path):
            error(f"Arquivo nao encontrado: {json_path}")
            continue
        break

    # ETAPA 2 — Confirmar e executar
    while True:
        wizard_box("WIZARD — Importar Dados")
        wizard_step(2, 2, "Confirmacao")
        wizard_summary("Resumo da operacao", [
            ("Arquivo", f"{G}{json_path}{R}"),
        ])
        val = input(f"  {B}[S]{R} Importar  {D}[E]{R} Alterar caminho  {D}[X]{R} Cancelar\n  {B}Opcao:{R} ").strip().upper()
        if val == "X":
            info("Wizard cancelado.")
            return
        if val == "S":
            break
        if val == "E":
            return wizard_import()

    cls()
    print(BANNER)
    section("IMPORTAR DADOS")
    from src.data_importer import import_and_set_offline
    if import_and_set_offline(json_path):
        info("Modo offline ativo. Pronto para processar.")
        print()
        info("Proximos passos:")
        info("  - Opcao 1: Mapear acessos de um usuario")
    else:
        error("Falha ao importar dados.")


# ══════════════════════════════════════════════
# WIZARD — Limpar Tabelas
# ══════════════════════════════════════════════

def wizard_clean():
    B = C["bold"]; D = C["dim"]; R = C["reset"]; G = C["green"]; RD = C["red"]

    wizard_box("WIZARD — Limpar Tabelas", "Gerar script DELETE para tabelas de privilegios")

    # ETAPA 1 — Confirmacao com alerta
    while True:
        wizard_box("WIZARD — Limpar Tabelas")
        wizard_step(1, 2, "Confirmacao — ATENCAO!")
        warn("Esta operacao gera um script SQL que remove TODOS os registros")
        warn("das tabelas de privilegios (SYS_RULES, SYS_RULES_USR_RULES,")
        warn("SYS_RULES_GRP_RULES, SYS_RULES_FEATURES).")
        print()
        result = wizard_prompt_yn("Confirmar geracao do script de limpeza?", "N")
        if result is None:
            info("Wizard cancelado.")
            return
        if not result:
            info("Limpeza cancelada.")
            return
        break

    # ETAPA 2 — Executar
    wizard_box("WIZARD — Limpar Tabelas")
    wizard_step(2, 2, "Executando...")
    run_clean_privileges()


# ══════════════════════════════════════════════
# WIZARD — Analise Organizacional
# ══════════════════════════════════════════════

def wizard_org_analysis():
    B = C["bold"]; D = C["dim"]; R = C["reset"]; G = C["green"]

    wizard_box("WIZARD — Analise Organizacional", "Mapeia usuarios e analisa camadas (Tiers 1-4)")

    # ETAPA 1 — Fonte dos dados
    while True:
        wizard_box("WIZARD — Analise Organizacional")
        wizard_step(1, 2, "Fonte dos dados")
        info("Escolha como obter os dados dos usuarios.")
        print()
        print(f"  {B}[M]{R} Mapear do banco (completo)")
        print(f"     {D}Conecta ao SQL Server e mapeia todos os usuarios{R}")
        print()
        print(f"  {B}[R]{R} Reusar arquivos mapeados (rapido)")
        print(f"     {D}Carrega os *_access.json ja existentes na pasta output/{R}")
        print()
        val = input(f"  {B}Opcao{R} [X = cancelar]: ").strip().upper()
        if val == "X":
            info("Wizard cancelado.")
            return
        if val in ("M", "R"):
            break
        error("Opcao invalida. Use M ou R.")

    # ETAPA 2 — Confirmar e executar
    while True:
        wizard_box("WIZARD — Analise Organizacional")
        wizard_step(2, 2, "Confirmacao")
        fonte_disp = f"{G}Banco SQL Server{R}" if val == "M" else f"{G}Arquivos output/{R}"
        wizard_summary("Resumo da operacao", [
            ("Fonte dos dados", fonte_disp),
            ("Empresa        ", f"{G}{cfg.EMPRESA_NAME}{R}"),
        ])
        action = input(f"  {B}[S]{R} Executar  {D}[E]{R} Alterar  {D}[X]{R} Cancelar\n  {B}Opcao:{R} ").strip().upper()
        if action == "X":
            info("Wizard cancelado.")
            return
        if action == "S":
            break
        if action == "E":
            return wizard_org_analysis()

    cls()
    print(BANNER)
    if val == "R":
        all_reports = _load_reports_from_files()
        if not all_reports:
            error("Nenhum arquivo *_access.json encontrado em output/.")
            return
        print(f"  {C['green']}Carregados {len(all_reports)} relatorios.{C['reset']}")
        _run_org_analysis_with_reports(all_reports)
    else:
        run_organizational_analysis()


def _run_org_analysis_with_reports(all_reports):
    global _saved_llm_clusters
    G = C["green"]; CY = C["cyan"]; D = C["dim"]; B = C["bold"]; Y = C["yellow"]; R = C["reset"]

    zero_routine_users = []
    filtered_reports = []
    for rep in all_reports:
        if len(rep.get("routines_summary", [])) == 0:
            zero_routine_users.append(rep["user"])
        else:
            filtered_reports.append(rep)
    if zero_routine_users:
        print(f"  {Y}[FILTRO]{R} {len(zero_routine_users)} usuarios sem rotinas ignorados.")
    if not filtered_reports:
        warn("Nenhum usuario com rotinas encontrado. Abortando.")
        return
    all_reports = filtered_reports

    section("TIER 1 — GERAL")
    all_sets = []
    for rep in all_reports:
        rset = set(r["routine"] for r in rep.get("routines_summary", []) if r.get("routine"))
        all_sets.append(rset)
    tier1_common = all_sets[0].copy()
    for s in all_sets[1:]:
        tier1_common &= s
    print(f"  Rotinas comuns a TODOS ({len(all_reports)} usuarios): {G}{len(tier1_common)}{R}")

    tier1_routines = []
    routines_details = {}
    for rep in all_reports:
        for r in rep.get("routines_summary", []):
            code = r.get("routine", "")
            if code not in routines_details:
                routines_details[code] = r.get("description", "")
    for code in sorted(tier1_common):
        tier1_routines.append({"code": code, "desc": routines_details.get(code, "")})

    section("TIER 2 — DEPARTAMENTOS")
    dept_users = {}
    for rep in all_reports:
        dept = rep.get("user_depto", "").strip()
        if not dept:
            dept = "SEM_DEPARTAMENTO"
        if dept not in dept_users:
            dept_users[dept] = []
        dept_users[dept].append(rep)
    tier2_data = []
    for dept_name in sorted(dept_users.keys()):
        reps = dept_users[dept_name]
        if len(reps) < 2:
            continue
        d_sets = []
        for rep in reps:
            rset = set(r["routine"] for r in rep.get("routines_summary", []) if r.get("routine"))
            d_sets.append(rset)
        common = d_sets[0].copy()
        for s in d_sets[1:]:
            common &= s
        if common:
            dept_routines = []
            for code in sorted(common):
                dept_routines.append({"code": code, "desc": routines_details.get(code, "")})
            tier2_data.append({
                "depto": dept_name,
                "routines": dept_routines,
                "users": [r["user"] for r in reps],
            })
            print(f"  {G}{dept_name}{R}: {len(reps)} usuarios, {len(common)} rotinas comuns")
    print(f"  Departamentos com rotinas comuns: {G}{len(tier2_data)}{R}")

    section("TIER 3 — PERFIS E CONJUNTOS FUNCIONAIS")
    tier3_clusters = []
    tier2_routines_map = {}
    for d in tier2_data:
        tier2_routines_map[d["depto"]] = set(r["code"] for r in d["routines"])
    profile_groups = build_equivalent_profile_groups(all_reports, tier1_common, tier2_routines_map)
    if profile_groups:
        tier3_clusters.extend(profile_groups)
        print(f"  Perfis equivalentes automaticos: {G}{len(profile_groups)}{R}")
    users_data = []
    for rep in all_reports:
        routines = []
        for r in rep.get("routines_summary", []):
            code = r.get("routine", "")
            desc = r.get("description", "")
            if code:
                routines.append({"code": code, "description": desc, "permissions": routine_permissions(r)})
        users_data.append({"user": rep["user"], "routines": routines})
    if cfg.LLM_API_KEY:
        from src.llm_categorizer import suggest_clusters
        llm_result = suggest_clusters(users_data)
        if llm_result and llm_result.get("clusters"):
            tier3_clusters.extend(normalize_tier3_sets(llm_result.get("clusters", []), all_reports))
        else:
            warn("LLM nao retornou conjuntos funcionais validos.")
    else:
        info("Sem LLM configurada. Tier 3 vazio — ajuste manualmente no dashboard.")
    tier3_users = set()
    for c in tier3_clusters:
        tier3_users.update(c.get("users", []))
    tier3_unclustered = sorted(set(rep["user"] for rep in all_reports) - tier3_users)

    section("TIER 4 — EXCLUSIVO POR USUARIO")
    tier4_users = build_tier4_users(all_reports, tier1_common, tier2_routines_map, tier3_clusters)
    exclusive_count = sum(1 for u in tier4_users if u["exclusive_count"] > 0)
    print(f"  Usuarios com rotinas exclusivas: {G}{exclusive_count}{R}")

    section("DASHBOARD")
    users_detail = {}
    user_routines_raw = {}
    user_dept_map = {}
    for rep in all_reports:
        login = rep["user"]
        top_routines = []
        for r in rep.get("routines_summary", [])[:20]:
            code = r.get("routine", "")
            desc = r.get("description", "")
            top_routines.append(f"{code} - {desc}" if desc else code)
        users_detail[login] = {
            "name": rep.get("user_name", login),
            "login": login,
            "depto": rep.get("user_depto", "") or "SEM_DEPARTAMENTO",
            "total_routines": rep.get("total_routines", 0),
            "all_routines": top_routines,
        }
        user_routines_raw[login] = user_routine_items(rep)
        user_dept_map[login] = rep.get("user_depto", "").strip() or "SEM_DEPARTAMENTO"
    html_path = os.path.join(OUTPUT_DIR, f"camadas_{cfg.EMPRESA_NAME}.html")
    from src.html_report import generate_cluster_html
    generate_cluster_html(
        {"routines": tier1_routines, "total_users": len(all_reports), "empresa": cfg.EMPRESA_NAME},
        tier2_data, tier3_clusters, tier3_unclustered,
        {"users": tier4_users},
        users_detail, user_routines_raw, user_dept_map,
        html_path, cfg.EMPRESA_NAME,
    )
    dept_html_path = os.path.join(OUTPUT_DIR, f"camadas_departamentos_{cfg.EMPRESA_NAME}.html")
    from src.department_html_report import generate_department_html
    try:
        with get_connection() as rules_conn:
            existing_rules = load_existing_rules(rules_conn)
    except Exception:
        existing_rules = None
    generate_department_html(
        build_department_analysis(all_reports, existing_rules=existing_rules),
        dept_html_path, cfg.EMPRESA_NAME,
    )
    import webbrowser
    webbrowser.open(f"file://{os.path.abspath(html_path)}")
    print(f"  {G}Dashboard gerado:{R} {html_path}")
    print(f"  {G}Dashboard por departamento gerado:{R} {dept_html_path}")
    print(f"  {CY}O navegador foi aberto com as 4 camadas.{R}")
    print()
    json_path = os.path.join(OUTPUT_DIR, f"clusters_{cfg.EMPRESA_NAME}.json")
    print(f"  {CY}{chr(0x2554)}{'═' * 54}{chr(0x2557)}{R}")
    print(f"  {CY}{chr(0x2551)}{R} {B}[C]{R} Carregar JSON de {OUTPUT_DIR}/clusters_{cfg.EMPRESA_NAME}.json")
    print(f"  {CY}{chr(0x2551)}{R} {B}[V]{R} Voltar (descartar tudo)")
    print(f"  {CY}{chr(0x255A)}{'═' * 54}{chr(0x255D)}{R}")
    action2 = input(f"  Opcao: ").strip().upper()
    if action2 == "V":
        info("Conjuntos funcionais descartados.")
        return
    if action2 == "C":
        if not os.path.exists(json_path):
            warn(f"Arquivo nao encontrado: {json_path}")
            return
        with open(json_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        tier3_saved = loaded.get("tier3", loaded).get("clusters", loaded.get("clusters", []))
        if not tier3_saved:
            warn("JSON nao contem conjuntos funcionais do Tier 3.")
            return
        _saved_llm_clusters = tier3_saved
        ok(f"{len(tier3_saved)} conjuntos funcionais carregados. Use opcao 3 para gerar o SQL.")
    else:
        warn("Opcao invalida. Conjuntos funcionais descartados.")


# ══════════════════════════════════════════════
# WIZARD — Gerar SQL Organizacional
# ══════════════════════════════════════════════

def wizard_org_sql():
    B = C["bold"]; D = C["dim"]; R = C["reset"]; G = C["green"]

    wizard_box("WIZARD — Gerar SQL Organizacional", "Carrega JSON ajustado e gera script INSERTs SYS_RULES")

    json_path = os.path.join(OUTPUT_DIR, f"clusters_{cfg.EMPRESA_NAME}.json")

    # ETAPA 1 — Confirmar arquivo
    while True:
        wizard_box("WIZARD — Gerar SQL Organizacional")
        wizard_step(1, 2, "Confirmar arquivo de conjuntos")
        info(f"Arquivo esperado: {D}{json_path}{R}")
        if not os.path.exists(json_path):
            warn(f"Arquivo nao encontrado: {json_path}")
            info("Execute a opcao 2 (Analise Organizacional) primeiro.")
            return
        print()
        val = input(f"  {B}Confirmar arquivo?{R} (S/N) [S | X = cancelar]: ").strip().upper()
        if val == "X":
            info("Wizard cancelado.")
            return
        if val == "N":
            info("Operacao cancelada.")
            return
        break

    # ETAPA 2 — Executar
    wizard_box("WIZARD — Gerar SQL Organizacional")
    wizard_step(2, 2, "Executando...")
    run_generate_org_sql()


def wizard_ferramentas():
    B = C["bold"]; D = C["dim"]; W = C["white"]; RD = C["red"]; R = C["reset"]
    while True:
        cls()
        print(BANNER)
        from src.database import is_offline
        if is_offline():
            show_offline_banner()
        L = C["cyan"]; CY = C["cyan"]
        BOX = 52
        def row(text):
            import re
            v = re.sub(r"\033\[[0-9;]*m", "", text)
            pad = BOX - len(v)
            return f"  {text}{' ' * pad}{L}║{R}"
        print(f"  {L}╔{'═' * BOX}╗{R}")
        print(row(f"{L}║{R}  {B}FERRAMENTAS{R}"))
        print(row(f"{L}║{R}  {D}{'─' * (BOX - 3)}{R}"))
        print(row(f"{L}║{R}  {B}1{R} │ {W}Exportar dados (SQL){R}"))
        print(row(f"{L}║{R}    │ {D}Gerar query para extracao offline{R}"))
        print(row(f"{L}║{R}  {B}2{R} │ {W}Importar dados (JSON){R}"))
        print(row(f"{L}║{R}    │ {D}Carregar export.json p/ modo offline{R}"))
        print(row(f"{L}║{R}  {B}3{R} │ {W}Limpar tabelas de privilegios{R}"))
        print(row(f"{L}║{R}    │ {D}Script DELETE p/ SYS_RULES e relacionadas{R}"))
        print(row(f"{L}║{R}  {B}0{R} │ {RD}Voltar{R}"))
        print(f"  {L}╚{'═' * BOX}╝{R}")
        print()
        sub = input(f"  {B}Opcao:{R} ").strip()
        cls()
        if sub == "0":
            break
        elif sub == "1":
            wizard_export()
        elif sub == "2":
            wizard_import()
        elif sub == "3":
            wizard_clean()
        else:
            print(f"\n  {C['red']}Opcao invalida!{C['reset']}\n")


def menu_camadas_org():
    B = C["bold"]; D = C["dim"]; W = C["white"]; RD = C["red"]; R = C["reset"]
    while True:
        cls()
        print(BANNER)
        from src.database import is_offline
        if is_offline():
            show_offline_banner()
        L = C["cyan"]
        BOX = 52
        def row(text):
            import re
            v = re.sub(r"\033\[[0-9;]*m", "", text)
            pad = BOX - len(v)
            return f"  {text}{' ' * pad}{L}║{R}"
        print(f"  {L}╔{'═' * BOX}╗{R}")
        print(row(f"{L}║{R}  {B}CAMADAS ORGANIZACIONAIS{R}"))
        print(row(f"{L}║{R}  {D}{'─' * (BOX - 3)}{R}"))
        print(row(f"{L}║{R}  {B}1{R} │ {W}Analisar camadas (Tiers 1-4){R}"))
        print(row(f"{L}║{R}    │ {D}Wizard: mapeia TODOS → Dashboard 4 tiers{R}"))
        print(row(f"{L}║{R}  {B}2{R} │ {W}Gerar SQL organizacional{R}"))
        print(row(f"{L}║{R}    │ {D}Wizard: JSON ajustado → Script SYS_RULES{R}"))
        print(row(f"{L}║{R}  {B}3{R} │ {W}Wizard Organizacional{R}"))
        print(row(f"{L}║{R}    │ {D}Configurar modo por camada (passo a passo){R}"))
        print(row(f"{L}║{R}  {B}0{R} │ {RD}Voltar{R}"))
        print(f"  {L}╚{'═' * BOX}╝{R}")
        print()
        sub = input(f"  {B}Opcao:{R} ").strip()
        cls()
        if sub == "0":
            break
        elif sub == "1":
            wizard_org_analysis()
        elif sub == "2":
            wizard_org_sql()
        elif sub == "3":
            wizard_organizacional()
        else:
            print(f"\n  {C['red']}Opcao invalida!{C['reset']}\n")


def menu():
    cls()
    print(BANNER)
    from src.database import is_offline
    if is_offline():
        show_offline_banner()
    L = C["cyan"]; R = C["reset"]; B = C["bold"]; D = C["dim"]; W = C["white"]; RD = C["red"]; G = C["green"]
    BOX = 52
    def row(text):
        import re
        v = re.sub(r"\033\[[0-9;]*m", "", text)
        pad = BOX - len(v)
        return f"  {text}{' ' * pad}{L}║{R}"

    is_org = (cfg.PRIVILEGE_MODE == "organizational_layer")

    print(f"  {L}╔{'═' * BOX}╗{R}")
    print(row(f"{L}║{R}  {B}1{R} │ {W}Mapear acessos de usuarios (Wizard){R}"))
    print(row(f"{L}║{R}    │ {D}Relatorio JSON + SQL + Dashboard{R}"))

    print(row(f"{L}║{R}  {B}2{R} │ {W}Ferramentas{R}"))
    print(row(f"{L}║{R}    │ {D}Exportar, importar e limpar tabelas{R}"))

    if is_org:
        print(row(f"{L}║{R}  {B}3{R} │ {W}Camadas organizacionais{R}"))
        print(row(f"{L}║{R}    │ {D}Analisar, gerar SQL e configurar modo{R}"))

    print(row(f"{L}║{R}  {D}{'─' * (BOX - 3)}{R}"))
    print(row(f"{L}║{R}  {B}4{R} │ {W}Parametrizacao{R}"))
    print(row(f"{L}║{R}    │ {D}Configurar banco, LLM e preferencias{R}"))

    print(row(f"{L}║{R}  {B}5{R} │ {W}Validacao API (Protheus){R}"))
    print(row(f"{L}║{R}    │ {D}Saneamento e validacao cruzada via API{R}"))

    if is_org:
        print(row(f"{L}║{R}  {D}{'─' * (BOX - 3)}{R}"))
        print(row(f"{L}║{R}  {D}  Modo: {G}CAMADA ORGANIZACIONAL{R}"))
        print(row(f"{L}║{R}    │ Empresa: {G}{cfg.EMPRESA_NAME}{R}  |  LLM: {G}{'ON' if cfg.LLM_API_KEY else 'OFF'}{R}"))

    print(row(f"{L}║{R}  {B}0{R} │ {RD}Sair{R}"))
    print(f"  {L}╚{'═' * BOX}╝{R}")
    print()
    return input(f"  {B}Opcao:{R} ").strip()


def section(header):
    print(f"\n  {C['cyan']}{C['bold']}[{header}]{C['reset']}", end="", flush=True)


def ok(text=""):
    print(f" {C['green']}OK{C['reset']}  {text}")


def fail(text=""):
    print(f" {C['red']}FALHA{C['reset']}  {text}")


def info(text):
    print(f"  {C['dim']}{text}{C['reset']}")


def warn(text):
    print(f"  {C['yellow']}⚠ {text}{C['reset']}")


def success(text):
    print(f"  {C['green']}✓ {text}{C['reset']}")


def error(text):
    print(f"  {C['red']}✗ {text}{C['reset']}")


def run_mapping(login):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    section("CONEXAO")
    spin("Conectando ao banco MSSQL...", 0.6)
    try:
        with get_connection() as conn:
            ok("Conectado com sucesso!")

            section("DISCOVERY")
            spin("Descobrindo estrutura das tabelas...", 1.0)
            schema = discover_columns_for_tables(SCHEMA_TABLES, conn)
            ok()
            print_schema_summary(schema)

            section("MAPEAMENTO")
            info(f"Usuario: {C['bold']}{login}{C['reset']}")
            mapper = UserMapper(schema, conn)
            report = mapper.build_full_report(login)

            if report is None:
                print()
                error("Falha ao mapear usuario. Verifique o login e a conexao.")
                return None, None, login

            report["_conn"] = conn

            section("SALVANDO")
            spin("Gerando relatorio JSON...", 0.4)
            json_path = save_report_json(report, login)
            ok()
            success(f"Relatorio salvo em: {C['bold']}{json_path}{C['reset']}")

            return report, schema, login

    except Exception as e:
        fail(str(e))
        warn("Verifique:")
        info("  - SQL Server esta rodando?")
        info("  - ODBC Driver 17 instalado?")
        info("  - Credenciais corretas?")
        return None, None, login


def run_generate_privileges(report, schema, login, rule_name=None):
    if report is None:
        warn("Sem dados de mapeamento. Execute a opcao 1 primeiro.")
        return

    section("PRIVILEGIOS")
    info("Gerando script SQL...")
    if rule_name is None:
        default_rule = f"ACESSOS_{login.upper()[:8]}"
        rule_name = input(f"  {C['bold']}Nome do grupo de regras [{C['dim']}{default_rule}{C['reset']}]:{C['reset']} ").strip()
        if not rule_name:
            rule_name = default_rule

    generator = PrivilegeGenerator(report, schema)
    sql = generator.generate_sql(rule_name)
    sql_path = generator.save_sql(sql, f"{login}_privileges.sql")

    ok()
    success(f"Script SQL salvo em: {C['bold']}{sql_path}{C['reset']}")

    routines_count = len(report.get("routines_summary", []))
    routines_with_priv = sum(1 for r in report.get("routines_summary", []) if r.get("has_explicit_privilege"))

    print()
    print(f"  {C['cyan']}{'─' * 45}{C['reset']}")
    print(f"  Rotinas no script .............. {routines_count}")
    print(f"  Com privilegio explicito ....... {C['green']}{routines_with_priv}{C['reset']}")
    print(f"  Sem privilegio (revisar) ....... {C['yellow']}{routines_count - routines_with_priv}{C['reset']}")
    print(f"  {C['cyan']}{'─' * 45}{C['reset']}")


def run_dashboard(login):
    json_path = os.path.join(OUTPUT_DIR, f"{login}_access.json")
    if not os.path.exists(json_path):
        warn(f"Arquivo JSON nao encontrado: {json_path}. Execute a opcao 1 ou 3 primeiro.")
        return

    section("DASHBOARD")
    spin("Gerando dashboard HTML...", 0.6)
    html_path = generate_html(json_path)
    ok()
    success(f"Dashboard salvo em: {C['bold']}{html_path}{C['reset']}")
    info(f"Abra o arquivo no navegador para visualizar.")


def spin(text, duration=1.0):
    i = 0
    end = time.time() + duration
    while time.time() < end:
        sys.stdout.write(f"\r  {C['cyan']}{SPINNER_CHARS[i % len(SPINNER_CHARS)]}{C['reset']} {text}")
        sys.stdout.flush()
        time.sleep(0.08)
        i += 1


def run_batch(choice=None, gen_priv=False, rule_name="", gen_dash=False):
    if choice is not None:
        gen_priv = (choice == "2")
        gen_dash = (choice == "3")
        rule_name = ""

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    section("CONEXAO")
    spin("Conectando ao banco MSSQL...", 0.6)
    try:
        with get_connection() as conn:
            ok("Conectado com sucesso!")

            section("DISCOVERY")
            spin("Descobrindo estrutura das tabelas...", 1.0)
            schema = discover_columns_for_tables(SCHEMA_TABLES, conn)
            ok()
            print_schema_summary(schema)

            section("BATCH")
            mapper = UserMapper(schema, conn)
            users = mapper.list_non_blocked_users()

            if not users:
                warn("Nenhum usuario nao bloqueado encontrado.")
                return

            success_count = 0
            fail_count = 0
            total = len(users)

            print(f"\n  {C['cyan']}{chr(0x250C)}{'─' * 45}{chr(0x2510)}{C['reset']}")

            for i, user in enumerate(users, 1):
                login = user["login"]
                login_display = login if login else f"ID_{user['id']}"
                print(f"\n  {C['cyan']}[{i}/{total}]{C['reset']} \033[1m{login_display}\033[0m")

                try:
                    report = mapper.build_full_report(login)
                    if report is None:
                        error(f"Falha ao mapear usuario")
                        fail_count += 1
                        continue

                    report["_conn"] = conn

                    json_path = save_report_json(report, login)
                    info(f"  JSON salvo: {json_path}")

                    if gen_priv:
                        default_rule = rule_name if rule_name else f"ACESSOS_{login.upper()[:8]}"
                        generator = PrivilegeGenerator(report, schema)
                        sql = generator.generate_sql(default_rule)
                        sql_path = generator.save_sql(sql, f"{login}_privileges.sql")
                        info(f"  Script SQL: {sql_path}")

                    if gen_dash:
                        html_path = generate_html(json_path)
                        per_user_html = os.path.join(OUTPUT_DIR, f"{login}_dashboard.html")
                        if os.path.exists(html_path):
                            os.replace(html_path, per_user_html)
                        info(f"  Dashboard: {per_user_html}")

                    success_count += 1

                except Exception as e:
                    error(f"Erro: {e}")
                    fail_count += 1

            print(f"\n  {C['cyan']}{chr(0x2514)}{'─' * 45}{chr(0x2518)}{C['reset']}")
            print()
            summary_ok = f"{C['green']}Sucesso: {success_count}{C['reset']}"
            summary_fail = f"{C['red']}Falhas: {fail_count}{C['reset']}"
            print(f"  Processados: {total} | {summary_ok} | {summary_fail}")

    except Exception as e:
        fail(str(e))
        warn("Verifique:")
        info("  - SQL Server esta rodando?")
        info("  - ODBC Driver 17 instalado?")
        info("  - Credenciais corretas?")


def menu_parametrizacao():
    while True:
        cls()
        print(BANNER)
        L = C["cyan"]; R = C["reset"]; B = C["bold"]; D = C["dim"]; W = C["white"]; G = C["green"]; Y = C["yellow"]; RD = C["red"]
        BOX = 55

        def row(text):
            import re
            v = re.sub(r"\033\[[0-9;]*m", "", text)
            pad = BOX - len(v)
            return f"  {text}{' ' * pad}{L}║{R}"

        server_disp = DB_CONFIG["server"][:28]
        db_disp = DB_CONFIG["database"][:28]
        user_disp = DB_CONFIG["username"][:28]
        pass_disp = "****"
        driver_disp = DB_CONFIG["driver"][:28]
        mode_disp = "POR USUARIO" if cfg.PRIVILEGE_MODE == "per_user" else "POR CAMADA ORGANIZACIONAL"
        empresa_disp = cfg.EMPRESA_NAME[:28] if cfg.EMPRESA_NAME else "(nao definido)"
        llm_key_disp = "****" if cfg.LLM_API_KEY else "(nao definido)"
        llm_model_disp = cfg.LLM_MODEL[:28] if cfg.LLM_MODEL else "(nao definido)"
        llm_url_disp = cfg.LLM_BASE_URL[:28] if cfg.LLM_BASE_URL else "(nao definido)"

        from src.config import API_CONFIG
        api_url_disp = API_CONFIG["base_url"][:28] if API_CONFIG["base_url"] else "(nao definido)"
        api_token_disp = "****" if API_CONFIG["bearer_token"] else "(nao definido)"
        api_tenant_disp = API_CONFIG["tenant_id"][:28] if API_CONFIG["tenant_id"] else "(nao definido)"
        api_db_disp = API_CONFIG["erp_database"][:28] if API_CONFIG["erp_database"] else "(nao definido)"

        print(f"  {L}╔{'═' * BOX}╗{R}")
        print(row(f"{L}║{R}  {B}PARAMETRIZACAO{R}"))
        print(row(f"{L}║{R}  {D}{'─' * (BOX - 3)}{R}"))
        print(row(f"{L}║{R}  {B}1{R} │ {W}Servidor ..........{R} [{D}{server_disp}{R}]"))
        print(row(f"{L}║{R}  {B}2{R} │ {W}Banco de dados ....{R} [{D}{db_disp}{R}]"))
        print(row(f"{L}║{R}  {B}3{R} │ {W}Usuario ...........{R} [{D}{user_disp}{R}]"))
        print(row(f"{L}║{R}  {B}4{R} │ {W}Senha .............{R} [{D}{pass_disp}{R}]"))
        print(row(f"{L}║{R}  {B}5{R} │ {W}Driver ODBC .......{R} [{D}{driver_disp}{R}]"))
        if cfg.PRIVILEGE_MODE == "organizational_layer":
            print(row(f"{L}║{R}  {D}{'─' * (BOX - 3)}{R}"))
            print(row(f"{L}║{R}  {B}5{{N}}{R} │ {W}Nome da empresa ...{R} [{D}{empresa_disp}{R}]"))
            print(row(f"{L}║{R}  {D}{'─' * (BOX - 3)}{R}"))
            print(row(f"{L}║{R}  {B}5{{A}}{R} │ {W}LLM API Key .......{R} [{D}{llm_key_disp}{R}]"))
            print(row(f"{L}║{R}  {B}5{{B}}{R} │ {W}LLM Model .........{R} [{D}{llm_model_disp}{R}]"))
            print(row(f"{L}║{R}  {B}5{{C}}{R} │ {W}LLM Base URL ......{R} [{D}{llm_url_disp}{R}]"))
        print(row(f"{L}║{R}  {D}{'─' * (BOX - 3)}{R}"))
        print(row(f"{L}║{R}  {B}6{R} │ {W}Modo de privilegio{R} [{G}{mode_disp}{R}]"))
        print(row(f"{L}║{R}  {D}{'─' * (BOX - 3)}{R}"))
        print(row(f"{L}║{R}  {B}7{R} │ {W}Testar conexao{R}"))
        print(row(f"{L}║{R}  {B}8{R} │ {W}Salvar configuracoes{R}"))
        print(row(f"{L}║{R}  {D}{'─' * (BOX - 3)}{R}"))
        print(row(f"{L}║{R}  {B}--- API Protheus ---{R}"))
        print(row(f"{L}║{R}  {B}A{R} │ {W}Base URL ..........{R} [{D}{api_url_disp}{R}]"))
        print(row(f"{L}║{R}  {B}B{R} │ {W}Bearer Token ......{R} [{D}{api_token_disp}{R}]"))
        print(row(f"{L}║{R}  {B}C{R} │ {W}Tenant ID .........{R} [{D}{api_tenant_disp}{R}]"))
        print(row(f"{L}║{R}  {B}D{R} │ {W}Banco (x-erp-db) ..{R} [{D}{api_db_disp}{R}]"))
        print(row(f"{L}║{R}  {B}E{R} │ {W}Testar API ........{R}"))
        print(row(f"{L}║{R}  {B}0{R} │ {RD}Voltar{R}"))
        print(f"  {L}╚{'═' * BOX}╝{R}")
        print()

        try:
            sub = input(f"  {B}Opcao:{R} ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        cls()

        if sub == "0":
            break

        elif sub == "1":
            val = input(f"  Servidor [{DB_CONFIG['server']}]: ").strip()
            if val:
                DB_CONFIG["server"] = val
                success(f"Servidor alterado para: {val}")

        elif sub == "2":
            val = input(f"  Banco de dados [{DB_CONFIG['database']}]: ").strip()
            if val:
                DB_CONFIG["database"] = val
                success(f"Banco alterado para: {val}")

        elif sub == "3":
            val = input(f"  Usuario [{DB_CONFIG['username']}]: ").strip()
            if val:
                DB_CONFIG["username"] = val
                success(f"Usuario alterado para: {val}")

        elif sub == "4":
            val = input(f"  Senha [****]: ").strip()
            if val:
                DB_CONFIG["password"] = val
                success("Senha alterada.")

        elif sub == "5":
            val = input(f"  Driver ODBC [{DB_CONFIG['driver']}]: ").strip()
            if val:
                DB_CONFIG["driver"] = val
                success(f"Driver alterado para: {val}")

        elif sub == "5N":
            val = input(f"  Nome da empresa [{cfg.EMPRESA_NAME}]: ").strip()
            if val:
                cfg.EMPRESA_NAME = val
                success(f"Empresa alterada para: {val}")

        elif sub == "5A":
            val = input(f"  LLM API Key [{cfg.LLM_API_KEY[:8] + '...' if cfg.LLM_API_KEY else '(vazio)'}]: ").strip()
            if val:
                cfg.LLM_API_KEY = val
                success("LLM API Key alterada.")

        elif sub == "5B":
            val = input(f"  LLM Model [{cfg.LLM_MODEL}]: ").strip()
            if val:
                cfg.LLM_MODEL = val
                success(f"LLM Model alterado para: {val}")

        elif sub == "5C":
            val = input(f"  LLM Base URL [{cfg.LLM_BASE_URL}]: ").strip()
            if val:
                cfg.LLM_BASE_URL = val
                success(f"LLM Base URL alterada para: {val}")

        elif sub == "6":
            if cfg.PRIVILEGE_MODE == "per_user":
                cfg.PRIVILEGE_MODE = "organizational_layer"
            else:
                cfg.PRIVILEGE_MODE = "per_user"
            mode_label = "POR USUARIO" if cfg.PRIVILEGE_MODE == "per_user" else "POR CAMADA ORGANIZACIONAL"
            success(f"Modo alterado para: {mode_label}")

        elif sub == "7":
            spin("Testando conexao...", 0.6)
            try:
                import pyodbc
                conn_str = build_connection_string()
                test_conn = pyodbc.connect(conn_str, timeout=5)
                test_conn.close()
                ok()
                success("Conexao estabelecida com sucesso!")
            except Exception as e:
                fail()
                error(str(e))

        elif sub == "8":
            save_user_config()
            success(f"Configuracoes salvas em config_user.json")

        elif sub.upper() == "A":
            from src.config import API_CONFIG
            val = input(f"  Base URL [{API_CONFIG['base_url']}]: ").strip()
            if val:
                API_CONFIG["base_url"] = val
                success(f"Base URL alterada para: {val}")

        elif sub.upper() == "B":
            from src.config import API_CONFIG
            val = input(f"  Bearer Token [****]: ").strip()
            if val:
                API_CONFIG["bearer_token"] = val
                success("Bearer Token atualizado.")

        elif sub.upper() == "C":
            from src.config import API_CONFIG
            val = input(f"  Tenant ID [{API_CONFIG['tenant_id']}]: ").strip()
            if val:
                API_CONFIG["tenant_id"] = val
                success(f"Tenant ID alterado para: {val}")

        elif sub.upper() == "D":
            from src.config import API_CONFIG
            val = input(f"  Banco x-erp-database [{API_CONFIG['erp_database']}]: ").strip()
            if val:
                API_CONFIG["erp_database"] = val
                success(f"Banco API alterado para: {val}")

        elif sub.upper() == "E":
            from src.config import API_CONFIG
            if not API_CONFIG["bearer_token"]:
                warn("Bearer Token nao configurado. Configure primeiro (opcao B).")
            else:
                spin("Testando API...", 0.6)
                ok_status, msg = _test_api_connection()
                if ok_status:
                    ok()
                    success(msg)
                else:
                    fail()
                    error(msg)

        else:
            print(f"\n  {C['red']}Opcao invalida!{C['reset']}\n")

        if sub != "0":
            wait_enter()


def wizard_organizacional():
    cls()
    print(BANNER)
    L = C["cyan"]; R = C["reset"]; B = C["bold"]; D = C["dim"]
    W = C["white"]; G = C["green"]; Y = C["yellow"]; RD = C["red"]; CY = C["cyan"]

    print(f"  {CY}{chr(0x2550) * 56}{R}")
    print(f"  {CY}  {B}WIZARD — Modo Organizacional{R}")
    print(f"  {CY}  {D}Configure privilegios por camada (passo a passo){R}")
    print(f"  {CY}{chr(0x2550) * 56}{R}")
    print()
    info("Este wizard vai configurar:")
    info("  1. Nome da empresa (obrigatorio)")
    info("  2. Metodo de agrupamento (LLM ou Jaccard)")
    info("  3. Parametros do metodo escolhido")
    print()
    info(f"{D}A qualquer momento digite 'X' para cancelar.{R}")
    wait_enter()

    # etapa 1: nome da empresa
    while True:
        cls()
        print(BANNER)
        print(f"  {CY}{chr(0x2550) * 56}{R}")
        print(f"  {CY}  {B}ETAPA 1/4 — Nome da Empresa{R}")
        print(f"  {CY}{chr(0x2550) * 56}{R}")
        print()
        info("Identificador usado nos nomes das regras (ex: P_POLPREV).")
        info("Use um nome curto, sem espacos ou caracteres especiais.")
        print()

        current = cfg.EMPRESA_NAME if cfg.EMPRESA_NAME else ""
        prompt = f"  {B}Nome da empresa{R}"
        if current:
            prompt += f" [{G}{current}{R}]"
        prompt += ": "

        val = input(prompt).strip()
        if val.upper() == "X":
            info("Wizard cancelado.")
            return
        if val:
            cfg.EMPRESA_NAME = val.upper().replace(" ", "_")
        elif not cfg.EMPRESA_NAME:
            error("Nome da empresa e obrigatorio.")
            wait_enter()
            continue

        success(f"Empresa: {G}{cfg.EMPRESA_NAME}{R}")
        wait_enter()
        break

    # etapa 2: metodo de agrupamento
    clustering_method = "llm" if cfg.LLM_API_KEY else "jaccard"
    while True:
        cls()
        print(BANNER)
        print(f"  {CY}{chr(0x2550) * 56}{R}")
        print(f"  {CY}  {B}ETAPA 2/4 — Metodo de Agrupamento{R}")
        print(f"  {CY}{chr(0x2550) * 56}{R}")
        print()
        info("Como agrupar usuarios com rotinas similares?")
        print()
        print(f"  {B}[L]{R} {W}LLM (OpenRouter){R}")
        print(f"     {D}IA analisa dominios funcionais e sugere conjuntos de rotinas.{R}")
        print(f"     {D}Requer API Key gratuita do OpenRouter.{R}")
        print()
        print(f"  {B}[J]{R} {W}Jaccard (Manual){R}")
        print(f"     {D}Algoritmo de similaridade entre conjuntos de rotinas.{R}")
        print(f"     {D}Nao requer API externa, funciona offline.{R}")
        print()

        current_method = "LLM" if cfg.LLM_API_KEY else "Jaccard"
        val = input(f"  {B}Metodo{R} [{G}{current_method}{R} | X = cancelar]: ").strip().upper()

        if val == "X":
            info("Wizard cancelado.")
            return
        if val == "L":
            clustering_method = "llm"
            break
        if val == "J":
            clustering_method = "jaccard"
            break
        if not val:
            break

    # etapa 3: parametros do metodo
    if clustering_method == "llm":
        while True:
            cls()
            print(BANNER)
            print(f"  {CY}{chr(0x2550) * 56}{R}")
            print(f"  {CY}  {B}ETAPA 3/4 — LLM API Key{R}")
            print(f"  {CY}{chr(0x2550) * 56}{R}")
            print()
            info("Chave de API do OpenRouter (gratuita).")
            info(f"Obtenha em: {D}https://openrouter.ai/keys{R}")
            print()

            current_disp = "****" if cfg.LLM_API_KEY else "(vazio)"
            val = input(f"  {B}API Key{R} [{D}{current_disp}{R} | X = cancelar]: ").strip()

            if val.upper() == "X":
                info("Wizard cancelado.")
                return
            if val:
                cfg.LLM_API_KEY = val
                success("API Key configurada.")
            elif not cfg.LLM_API_KEY:
                error("API Key e obrigatoria para o metodo LLM.")
                wait_enter()
                continue

            wait_enter()
            break

        cls()
        print(BANNER)
        print(f"  {CY}{chr(0x2550) * 56}{R}")
        print(f"  {CY}  {B}ETAPA 4/4 — LLM Model e URL{R}")
        print(f"  {CY}{chr(0x2550) * 56}{R}")
        print()
        info("Modelo LLM para analise de conjuntos funcionais.")
        info(f"{D}Recomendado: openai/gpt-4o-mini (custo baixo){R}")
        print()

        val = input(f"  {B}Modelo{R} [{G}{cfg.LLM_MODEL}{R} | ENTER = manter | X = cancelar]: ").strip()
        if val.upper() == "X":
            info("Wizard cancelado.")
            return
        if val:
            cfg.LLM_MODEL = val

        print()
        val = input(f"  {B}Base URL{R} [{D}{cfg.LLM_BASE_URL}{R} | ENTER = manter]: ").strip()
        if val.upper() == "X":
            info("Wizard cancelado.")
            return
        if val:
            cfg.LLM_BASE_URL = val

        wait_enter()

    else:
        import src.organizational_privileges as org_priv

        while True:
            cls()
            print(BANNER)
            print(f"  {CY}{chr(0x2550) * 56}{R}")
            print(f"  {CY}  {B}ETAPA 3/4 — Threshold de Similaridade{R}")
            print(f"  {CY}{chr(0x2550) * 56}{R}")
            print()
            info("Limiar de similaridade Jaccard para formar conjuntos no modo manual.")
            info(f"{D}0.0 = tudo agrupado | 1.0 = nada agrupado{R}")
            info(f"{D}Recomendado: 0.4 (agrupamento moderado){R}")
            print()

            current = str(org_priv.CLUSTER_SIMILARITY_THRESHOLD)
            val = input(f"  {B}Threshold{R} [{G}{current}{R} | ENTER = manter | X = cancelar]: ").strip()

            if val.upper() == "X":
                info("Wizard cancelado.")
                return
            if val:
                try:
                    t = float(val)
                    if 0.0 <= t <= 1.0:
                        org_priv.CLUSTER_SIMILARITY_THRESHOLD = t
                        success(f"Threshold: {G}{t}{R}")
                        break
                    else:
                        error("Valor deve estar entre 0.0 e 1.0.")
                        wait_enter()
                except ValueError:
                    error("Valor invalido. Use um numero (ex: 0.4).")
                    wait_enter()
            else:
                break

        cls()
        print(BANNER)
        print(f"  {CY}{chr(0x2550) * 56}{R}")
        print(f"  {CY}  {B}ETAPA 4/4 — Tamanho Minimo do Conjunto Manual{R}")
        print(f"  {CY}{chr(0x2550) * 56}{R}")
        print()
        info("Numero minimo de usuarios para formar um conjunto no modo manual.")
        info(f"{D}Recomendado: 2{R}")
        print()

        current = str(org_priv.MIN_CLUSTER_SIZE)
        val = input(f"  {B}Tamanho minimo{R} [{G}{current}{R} | ENTER = manter | X = cancelar]: ").strip()

        if val.upper() == "X":
            info("Wizard cancelado.")
            return
        if val:
            try:
                s = int(val)
                if s >= 1:
                    org_priv.MIN_CLUSTER_SIZE = s
                    success(f"Tamanho minimo: {G}{s}{R}")
                else:
                    error("Valor deve ser maior ou igual a 1.")
            except ValueError:
                error("Valor invalido. Use um numero inteiro (ex: 2).")

        wait_enter()

    # etapa final: confirmacao
    while True:
        cls()
        print(BANNER)
        print(f"  {CY}{chr(0x2550) * 56}{R}")
        print(f"  {CY}  {B}CONFIRMACAO{R}")
        print(f"  {CY}{chr(0x2550) * 56}{R}")
        print()

        method_disp = "LLM (OpenRouter)" if clustering_method == "llm" else "Jaccard (Manual)"
        key_disp = "****" if cfg.LLM_API_KEY else "(nao definido)"

        import src.organizational_privileges as org_priv

        print(f"  {B}Empresa.......:{R} {G}{cfg.EMPRESA_NAME}{R}")
        print(f"  {B}Modo..........:{R} {G}POR CAMADA ORGANIZACIONAL{R}")
        print(f"  {B}Agrupamento...:{R} {G}{method_disp}{R}")
        if clustering_method == "llm":
            print(f"  {B}LLM API Key...:{R} {D}{key_disp}{R}")
            print(f"  {B}LLM Model.....:{R} {D}{cfg.LLM_MODEL}{R}")
            print(f"  {B}LLM Base URL..:{R} {D}{cfg.LLM_BASE_URL}{R}")
        else:
            print(f"  {B}Threshold.....:{R} {D}{org_priv.CLUSTER_SIMILARITY_THRESHOLD}{R}")
            print(f"  {B}Tam. minimo...:{R} {D}{org_priv.MIN_CLUSTER_SIZE}{R}")
        print()
        print(f"  {CY}{chr(0x2500) * 56}{R}")
        print()
        print(f"  {B}[S]{R} Salvar e ativar  {D}[E]{R} Editar etapa  {D}[X]{R} Cancelar")
        action = input(f"  {B}Opcao:{R} ").strip().upper()

        if action == "X":
            info("Wizard cancelado. Nada foi salvo.")
            return

        if action == "S":
            cfg.PRIVILEGE_MODE = "organizational_layer"
            save_user_config()
            print()
            success("Configuracao salva com sucesso!")
            success(f"Modo ativo: {G}POR CAMADA ORGANIZACIONAL{R}")
            print()
            info("Proximos passos:")
            info("  - Opcao 2: Gerar script de privilegios organizacional")
            if cfg.LLM_API_KEY:
                info("  - Opcao 7: Pre-visualizar conjuntos funcionais via LLM")
            return

        if action == "E":
            print()
            print(f"  {B}Editar:{R}")
            print(f"  {D}[1]{R} Nome da empresa")
            print(f"  {D}[2]{R} Metodo de agrupamento")
            if clustering_method == "llm":
                print(f"  {D}[A]{R} LLM API Key")
                print(f"  {D}[M]{R} LLM Model / URL")
            else:
                print(f"  {D}[T]{R} Threshold")
                print(f"  {D}[N]{R} Tamanho minimo")
            step = input(f"  {B}Etapa:{R} ").strip().upper()

            if step == "1":
                val = input(f"  {B}Nome da empresa{R} [{G}{cfg.EMPRESA_NAME}{R}]: ").strip()
                if val:
                    cfg.EMPRESA_NAME = val.upper().replace(" ", "_")
                    success(f"Empresa: {cfg.EMPRESA_NAME}")

            elif step == "2":
                print(f"  {B}[L]{R} LLM  {D}[J]{R} Jaccard")
                val = input(f"  {B}Metodo{R} [{G}{'LLM' if clustering_method == 'llm' else 'Jaccard'}{R}]: ").strip().upper()
                if val == "L":
                    clustering_method = "llm"
                elif val == "J":
                    clustering_method = "jaccard"

            elif step == "A" and clustering_method == "llm":
                val = input(f"  {B}LLM API Key{R} [****]: ").strip()
                if val:
                    cfg.LLM_API_KEY = val
                    success("API Key atualizada.")

            elif step == "M" and clustering_method == "llm":
                val = input(f"  {B}LLM Model{R} [{cfg.LLM_MODEL}]: ").strip()
                if val:
                    cfg.LLM_MODEL = val
                val = input(f"  {B}LLM Base URL{R} [{cfg.LLM_BASE_URL}]: ").strip()
                if val:
                    cfg.LLM_BASE_URL = val

            elif step == "T" and clustering_method == "jaccard":
                val = input(f"  {B}Threshold{R} [{org_priv.CLUSTER_SIMILARITY_THRESHOLD}]: ").strip()
                if val:
                    try:
                        org_priv.CLUSTER_SIMILARITY_THRESHOLD = float(val)
                    except ValueError:
                        pass

            elif step == "N" and clustering_method == "jaccard":
                val = input(f"  {B}Tamanho minimo{R} [{org_priv.MIN_CLUSTER_SIZE}]: ").strip()
                if val:
                    try:
                        org_priv.MIN_CLUSTER_SIZE = int(val)
                    except ValueError:
                        pass

            wait_enter()


_saved_llm_clusters = None


def run_llm_preview():
    global _saved_llm_clusters

    if not cfg.LLM_API_KEY:
        warn("LLM API Key nao configurada. Configure em Parametrizacao.")
        return

    if not cfg.EMPRESA_NAME:
        warn("Nome da empresa nao definido. Configure em Parametrizacao.")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    section("CONEXAO")
    spin("Conectando ao banco MSSQL...", 0.6)
    try:
        with get_connection() as conn:
            ok("Conectado com sucesso!")

            section("DISCOVERY")
            spin("Descobrindo estrutura das tabelas...", 1.0)
            schema = discover_columns_for_tables(SCHEMA_TABLES, conn)
            ok()
            print_schema_summary(schema)

            section("MAPEANDO USUARIOS")
            mapper = UserMapper(schema, conn)
            users = mapper.list_non_blocked_users()

            if not users:
                warn("Nenhum usuario nao bloqueado encontrado.")
                return

            total = len(users)
            all_reports = []
            fail_count = 0

            for i, user_info in enumerate(users, 1):
                login = user_info["login"]
                login_display = login if login else f"ID_{user_info['id']}"
                print(f"\r  {C['cyan']}[{i}/{total}]{C['reset']} \033[1m{login_display}\033[0m", end="", flush=True)

                try:
                    report = mapper.build_full_report(login)
                    if report is None:
                        fail_count += 1
                        continue
                    report["_conn"] = conn
                    json_path = save_report_json(report, login)
                    all_reports.append(report)
                except Exception as e:
                    error(f"Erro ao mapear {login_display}: {e}")
                    fail_count += 1

            print()
            success_count = len(all_reports)
            print(f"  Mapeados: {C['green']}{success_count}{C['reset']} | Falhas: {C['red']}{fail_count}{C['reset']}")

            if not all_reports:
                warn("Nenhum relatorio gerado. Abortando.")
                return

            zero_routine_users = []
            filtered_reports = []
            for rep in all_reports:
                routines_count = len(rep.get("routines_summary", []))
                if routines_count == 0:
                    zero_routine_users.append(rep["user"])
                else:
                    filtered_reports.append(rep)

            if zero_routine_users:
                print(f"  {C['yellow']}[FILTRO]{C['reset']} {len(zero_routine_users)} usuarios sem rotinas ignorados:")
                print(f"         {', '.join(zero_routine_users[:10])}{'...' if len(zero_routine_users) > 10 else ''}")

            if not filtered_reports:
                warn("Nenhum usuario com rotinas encontrado. Abortando.")
                return

            all_reports = filtered_reports

            from src.llm_categorizer import suggest_clusters, build_prompt

            users_data = []
            for rep in all_reports:
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

            print(f"\n  {C['cyan']}[LLM]{C['reset']} Enviando {len(users_data)} usuarios para analise...")
            llm_result = suggest_clusters(users_data)

            if not llm_result or not llm_result.get("clusters"):
                warn("LLM nao retornou conjuntos funcionais validos. Use opcao 2 para modo manual (Jaccard).")
                return

            llm_clusters = normalize_tier3_sets(llm_result.get("clusters", []), all_reports)
            clustered_users = set()
            for c in llm_clusters:
                clustered_users.update(c.get("users", []))
            unclustered_list = sorted(set(rep["user"] for rep in all_reports) - clustered_users)

            users_detail = {}
            user_routines_raw = {}
            user_dept_map = {}
            for rep in all_reports:
                login = rep["user"]
                top_routines = []
                for r in rep.get("routines_summary", [])[:20]:
                    code = r.get("routine", "")
                    desc = r.get("description", "")
                    top_routines.append(f"{code} - {desc}" if desc else code)
                users_detail[login] = {
                    "name": rep.get("user_name", login),
                    "login": login,
                    "depto": rep.get("user_depto", ""),
                    "total_routines": rep.get("total_routines", 0),
                    "top_routines": top_routines,
                    "all_routines": top_routines,
                }
                user_routines_raw[login] = user_routine_items(rep)
                user_dept_map[login] = rep.get("user_depto", "").strip() or "SEM_DEPARTAMENTO"

            html_path = os.path.join(OUTPUT_DIR, f"clusters_{cfg.EMPRESA_NAME}.html")
            from src.html_report import generate_cluster_html
            generate_cluster_html(
                {"routines": [], "total_users": len(all_reports), "empresa": cfg.EMPRESA_NAME},
                [],
                llm_clusters,
                unclustered_list,
                {"users": []},
                users_detail,
                user_routines_raw,
                user_dept_map,
                html_path,
                cfg.EMPRESA_NAME,
            )

            import webbrowser
            webbrowser.open(f"file://{os.path.abspath(html_path)}")
            print(f"\n  {C['green']}HTML gerado:{C['reset']} {html_path}")
            print(f"  {C['cyan']}O navegador foi aberto para ajuste dos conjuntos funcionais.{C['reset']}")
            print()
            print(f"  {C['bold']}No navegador:{C['reset']}")
            print(f"    - Arraste rotinas para os conjuntos funcionais")
            print(f"    - Duplo clique no nome do conjunto para renomear")
            print(f"    - Clique no x da rotina para remove-la do conjunto")
            print(f"    - Clique em {C['bold']}Salvar JSON{C['reset']} e salve na pasta output/")
            print(f"    - Renomeie o arquivo para clusters_{cfg.EMPRESA_NAME}.json")
            print()
            json_path = os.path.join(OUTPUT_DIR, f"clusters_{cfg.EMPRESA_NAME}.json")

            print(f"  {C['cyan']}╔{'═' * 54}╗{C['reset']}")
            print(f"  {C['cyan']}║{C['reset']} {C['bold']}[C]{C['reset']} Carregar JSON de {OUTPUT_DIR}/clusters_{cfg.EMPRESA_NAME}.json")
            print(f"  {C['cyan']}║{C['reset']} {C['bold']}[P]{C['reset']} Colar JSON manualmente (Ctrl+V)")
            print(f"  {C['cyan']}║{C['reset']} {C['bold']}[V]{C['reset']} Voltar (descartar tudo)")
            print(f"  {C['cyan']}╚{'═' * 54}╝{C['reset']}")
            action = input(f"  Opcao: ").strip().upper()

            if action == "V":
                info("Conjuntos funcionais descartados.")
                return

            if action == "P":
                print()
                print(f"  Cole o JSON (termine com Ctrl+Z + Enter no Windows, ou Ctrl+D no Linux):")
                print()
                lines = []
                try:
                    while True:
                        line = input()
                        lines.append(line)
                except EOFError:
                    pass
                json_str = "\n".join(lines)
                try:
                    loaded = json.loads(json_str)
                    llm_clusters = loaded.get("tier3", loaded).get("clusters", loaded.get("clusters", []))
                    if not llm_clusters:
                        warn("JSON nao contem conjuntos funcionais do Tier 3. Abortando.")
                        return
                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump(loaded, f, indent=2, ensure_ascii=False)
                    ok(f"JSON salvo em {json_path}")
                except json.JSONDecodeError:
                    warn("JSON invalido. Abortando.")
                    return

            elif action == "C":
                if not os.path.exists(json_path):
                    warn(f"Arquivo nao encontrado: {json_path}")
                    print(f"  Salve o JSON do navegador nesta pasta primeiro.")
                    return
                with open(json_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                llm_clusters = loaded.get("tier3", loaded).get("clusters", loaded.get("clusters", []))
                if not llm_clusters:
                    warn("Arquivo JSON nao contem conjuntos funcionais do Tier 3. Abortando.")
                    return
                llm_clusters = normalize_tier3_sets(llm_clusters, all_reports)
                ok(f"{len(llm_clusters)} conjuntos funcionais carregados de {json_path}")
            else:
                warn("Opcao invalida. Conjuntos funcionais descartados.")
                return

            llm_clusters = normalize_tier3_sets(llm_clusters, all_reports)

            G = C["green"]; CY = C["cyan"]; Y = C["yellow"]; R = C["reset"]; D = C["dim"]; B = C["bold"]
            print()
            for idx, c in enumerate(llm_clusters, 1):
                name = c.get("name", f"CONJUNTO_{idx}")
                reason = c.get("reason", "")
                users_list = c.get("users", [])
                routines_list = c.get("routines", c.get("common_routines", []))

                print(f"  {CY}{chr(0x250C)}{'─' * 52}{chr(0x2510)}{R}")
                print(f"  {CY}{chr(0x2502)}{R} {B}Conjunto #{idx}: {G}{name}{R}")
                if reason:
                    print(f"  {CY}{chr(0x2502)}{R} {D}Motivo: {reason}{R}")
                print(f"  {CY}{chr(0x2502)}{R} Usuarios ({len(users_list)}): {', '.join(users_list[:6])}{'...' if len(users_list) > 6 else ''}")
                print(f"  {CY}{chr(0x2502)}{R} Rotinas relacionadas: {len(routines_list)}")
                sample = routines_list[:6]
                print(f"  {CY}{chr(0x2502)}{R}   Ex: {', '.join(sample)}{'...' if len(routines_list) > 6 else ''}")
                print(f"  {CY}{chr(0x2514)}{'─' * 52}{chr(0x2518)}{R}")

            print()
            print(f"  {B}[G]{R} Gerar SQL completo (4 tiers) com estes conjuntos")
            print(f"  {B}[E]{R} Editar nomes antes de gerar")
            print(f"  {B}[V]{R} Voltar (nao gerar nada)")
            action = input(f"  Opcao: ").strip().upper()

            if action == "V":
                info("Conjuntos funcionais descartados.")
                return

            if action == "E":
                print(f"\n  {B}Edicao de nomes:{R}")
                for idx, c in enumerate(llm_clusters):
                    name = c.get("name", f"CONJUNTO_{idx}")
                    users_list = c.get("users", [])
                    val = input(f"  Conjunto #{idx} ({', '.join(users_list[:3])}...) [{name}]: ").strip()
                    if val:
                        c["name"] = val.upper()

            _saved_llm_clusters = llm_clusters
            info(f"Conjuntos funcionais salvos ({len(llm_clusters)}). Use opcao 2 para gerar o SQL.")

    except Exception as e:
        fail(str(e))


def _load_reports_from_files():
    output_dir = OUTPUT_DIR
    if not os.path.isdir(output_dir):
        return []
    reports = []
    for fname in sorted(os.listdir(output_dir)):
        if not fname.endswith('_access.json'):
            continue
        fpath = os.path.join(output_dir, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                rep = json.load(f)
            if 'user' not in rep or 'routines_summary' not in rep:
                continue
            reports.append(rep)
        except Exception:
            continue
    return reports


def run_organizational_analysis():
    global _saved_llm_clusters

    if not cfg.EMPRESA_NAME:
        warn("Nome da empresa nao definido. Configure em Parametrizacao -> Nome da empresa.")
        return

    if not cfg.LLM_API_KEY:
        warn("LLM nao configurada. O Tier 3 sera gerado por Jaccard (sem LLM).")
        print(f"  {C['dim']}Configure LLM em Parametrizacao para sugestoes automaticas.{C['reset']}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    cls()
    print(BANNER)
    G = C["green"]; CY = C["cyan"]; D = C["dim"]; B = C["bold"]; Y = C["yellow"]; R = C["reset"]
    print(f"  {CY}{chr(0x2500) * 56}{R}")
    print(f"  {CY}  {B}FONTE DOS DADOS{R}")
    print(f"  {CY}  {D}Escolha como obter os dados dos usuarios{R}")
    print(f"  {CY}{chr(0x2500) * 56}{R}")
    print()
    print(f"  {B}[M]{R} Mapear do banco (completo)")
    print(f"     {D}Conecta ao SQL Server e mapeia todos os usuarios{D}")
    print()
    print(f"  {B}[R]{R} Reusar arquivos mapeados (rapido)")
    print(f"     {D}Carrega os *_access.json ja existentes na pasta output/{D}")
    print()
    print(f"  {B}[V]{R} Voltar")
    print()
    action = input(f"  Opcao: ").strip().upper()

    if action == "V":
        return

    if action == "R":
        all_reports = _load_reports_from_files()
        if not all_reports:
            warn("Nenhum arquivo *_access.json encontrado em output/. Execute o mapeamento primeiro.")
            return
        print(f"  {C['green']}Carregados {len(all_reports)} relatorios da pasta output/{C['reset']}")
        schema = None
    elif action == "M":
        all_reports = None
        schema = None
    else:
        warn("Opcao invalida.")
        return

    if all_reports is None:
        section("CONEXAO")
        spin("Conectando ao banco MSSQL...", 0.6)
        try:
            with get_connection() as conn:
                ok("Conectado com sucesso!")

                section("DISCOVERY")
                spin("Descobrindo estrutura das tabelas...", 1.0)
                schema = discover_columns_for_tables(SCHEMA_TABLES, conn)
                ok()
                print_schema_summary(schema)

                section("MAPEANDO USUARIOS")
                mapper = UserMapper(schema, conn)
                users = mapper.list_non_blocked_users()

                if not users:
                    warn("Nenhum usuario nao bloqueado encontrado.")
                    return

                total = len(users)
                all_reports = []
                fail_count = 0

                for i, user_info in enumerate(users, 1):
                    login = user_info["login"]
                    login_display = login if login else f"ID_{user_info['id']}"
                    print(f"\r  {C['cyan']}[{i}/{total}]{C['reset']} \033[1m{login_display}\033[0m", end="", flush=True)

                    try:
                        report = mapper.build_full_report(login)
                        if report is None:
                            fail_count += 1
                            continue
                        report["_conn"] = conn
                        json_path = save_report_json(report, login)
                        all_reports.append(report)
                    except Exception as e:
                        error(f"Erro ao mapear {login_display}: {e}")
                        fail_count += 1

                print()
                success_count = len(all_reports)
                print(f"  Mapeados: {C['green']}{success_count}{C['reset']} | Falhas: {C['red']}{fail_count}{C['reset']}")
        except Exception as e:
            fail(str(e))
            return

    if not all_reports:
        warn("Nenhum relatorio gerado. Abortando.")
        return

    zero_routine_users = []
    filtered_reports = []
    for rep in all_reports:
        if len(rep.get("routines_summary", [])) == 0:
            zero_routine_users.append(rep["user"])
        else:
            filtered_reports.append(rep)

    if zero_routine_users:
        print(f"  {C['yellow']}[FILTRO]{C['reset']} {len(zero_routine_users)} usuarios sem rotinas ignorados.")

    if not filtered_reports:
        warn("Nenhum usuario com rotinas encontrado. Abortando.")
        return

    all_reports = filtered_reports

    section("TIER 1 — GERAL")
    all_sets = []
    for rep in all_reports:
        rset = set(r["routine"] for r in rep.get("routines_summary", []) if r.get("routine"))
        all_sets.append(rset)
    tier1_common = all_sets[0].copy()
    for s in all_sets[1:]:
        tier1_common &= s
    print(f"  Rotinas comuns a TODOS ({len(all_reports)} usuarios): {C['green']}{len(tier1_common)}{C['reset']}")

    tier1_routines = []
    routines_details = {}
    for rep in all_reports:
        for r in rep.get("routines_summary", []):
            code = r.get("routine", "")
            if code not in routines_details:
                routines_details[code] = r.get("description", "")
    for code in sorted(tier1_common):
        tier1_routines.append({"code": code, "desc": routines_details.get(code, "")})

    section("TIER 2 — DEPARTAMENTOS")
    dept_users = {}
    for rep in all_reports:
        dept = rep.get("user_depto", "").strip()
        if not dept:
            dept = "SEM_DEPARTAMENTO"
        if dept not in dept_users:
            dept_users[dept] = []
        dept_users[dept].append(rep)

    tier2_data = []
    for dept_name in sorted(dept_users.keys()):
        reps = dept_users[dept_name]
        if len(reps) < 2:
            continue
        d_sets = []
        for rep in reps:
            rset = set(r["routine"] for r in rep.get("routines_summary", []) if r.get("routine"))
            d_sets.append(rset)
        common = d_sets[0].copy()
        for s in d_sets[1:]:
            common &= s
        if common:
            dept_routines = []
            for code in sorted(common):
                dept_routines.append({"code": code, "desc": routines_details.get(code, "")})
            tier2_data.append({
                "depto": dept_name,
                "routines": dept_routines,
                "users": [r["user"] for r in reps],
            })
            print(f"  {C['green']}{dept_name}{C['reset']}: {len(reps)} usuarios, {len(common)} rotinas comuns")
    print(f"  Departamentos com rotinas comuns: {C['green']}{len(tier2_data)}{C['reset']}")

    section("TIER 3 — PERFIS E CONJUNTOS FUNCIONAIS")
    tier3_clusters = []
    tier3_unclustered = []

    tier2_routines_map = {}
    for d in tier2_data:
        tier2_routines_map[d["depto"]] = set(r["code"] for r in d["routines"])

    profile_groups = build_equivalent_profile_groups(all_reports, tier1_common, tier2_routines_map)
    if profile_groups:
        tier3_clusters.extend(profile_groups)
        print(f"  Perfis equivalentes automaticos: {C['green']}{len(profile_groups)}{C['reset']}")

    users_data = []
    for rep in all_reports:
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

    if cfg.LLM_API_KEY:
        from src.llm_categorizer import suggest_clusters
        llm_result = suggest_clusters(users_data)
        if llm_result and llm_result.get("clusters"):
            tier3_clusters.extend(normalize_tier3_sets(llm_result.get("clusters", []), all_reports))
        else:
            warn("LLM nao retornou conjuntos funcionais validos.")
    else:
        info("Sem LLM configurada. Tier 3 vazio — ajuste manualmente no dashboard.")

    tier3_users = set()
    for c in tier3_clusters:
        tier3_users.update(c.get("users", []))
    tier3_unclustered = sorted(set(rep["user"] for rep in all_reports) - tier3_users)

    section("TIER 4 — EXCLUSIVO POR USUARIO")
    tier4_users = build_tier4_users(all_reports, tier1_common, tier2_routines_map, tier3_clusters)

    exclusive_count = sum(1 for u in tier4_users if u["exclusive_count"] > 0)
    print(f"  Usuarios com rotinas exclusivas: {C['green']}{exclusive_count}{C['reset']}")

    section("DASHBOARD")
    users_detail = {}
    user_routines_raw = {}
    user_dept_map = {}
    for rep in all_reports:
        login = rep["user"]
        top_routines = []
        for r in rep.get("routines_summary", [])[:20]:
            code = r.get("routine", "")
            desc = r.get("description", "")
            top_routines.append(f"{code} - {desc}" if desc else code)
        users_detail[login] = {
            "name": rep.get("user_name", login),
            "login": login,
            "depto": rep.get("user_depto", "") or "SEM_DEPARTAMENTO",
            "total_routines": rep.get("total_routines", 0),
            "all_routines": top_routines,
        }
        user_routines_raw[login] = user_routine_items(rep)
        user_dept_map[login] = rep.get("user_depto", "").strip() or "SEM_DEPARTAMENTO"

    html_path = os.path.join(OUTPUT_DIR, f"camadas_{cfg.EMPRESA_NAME}.html")
    from src.html_report import generate_cluster_html
    generate_cluster_html(
        {"routines": tier1_routines, "total_users": len(all_reports), "empresa": cfg.EMPRESA_NAME},
        tier2_data,
        tier3_clusters,
        tier3_unclustered,
        {"users": tier4_users},
        users_detail,
        user_routines_raw,
        user_dept_map,
        html_path,
        cfg.EMPRESA_NAME,
    )

    dept_html_path = os.path.join(OUTPUT_DIR, f"camadas_departamentos_{cfg.EMPRESA_NAME}.html")
    from src.department_html_report import generate_department_html
    try:
        with get_connection() as rules_conn:
            existing_rules = load_existing_rules(rules_conn)
    except Exception:
        existing_rules = None
    generate_department_html(
        build_department_analysis(all_reports, existing_rules=existing_rules),
        dept_html_path,
        cfg.EMPRESA_NAME,
    )

    import webbrowser
    webbrowser.open(f"file://{os.path.abspath(html_path)}")
    print(f"  {C['green']}Dashboard gerado:{C['reset']} {html_path}")
    print(f"  {C['green']}Dashboard por departamento gerado:{C['reset']} {dept_html_path}")
    print(f"  {C['cyan']}O navegador foi aberto com as 4 camadas.{C['reset']}")
    print()
    print(f"  {C['bold']}No navegador:{C['reset']}")
    print(f"    - Aba TIER 1: rotinas comuns a todos")
    print(f"    - Aba TIER 2: rotinas por departamento")
    print(f"    - Aba TIER 3: revise conjuntos funcionais de rotinas")
    print(f"    - Aba TIER 4: exclusivas (recalcula ao mexer Tier 3)")
    print(f"    - Clique em {C['bold']}Salvar JSON{C['reset']} e salve na pasta output/")
    print()

    json_path = os.path.join(OUTPUT_DIR, f"clusters_{cfg.EMPRESA_NAME}.json")
    print(f"  {C['cyan']}╔{'═' * 54}╗{C['reset']}")
    print(f"  {C['cyan']}║{C['reset']} {C['bold']}[C]{C['reset']} Carregar JSON de {OUTPUT_DIR}/clusters_{cfg.EMPRESA_NAME}.json")
    print(f"  {C['cyan']}║{C['reset']} {C['bold']}[V]{C['reset']} Voltar (descartar tudo)")
    print(f"  {C['cyan']}╚{'═' * 54}╝{C['reset']}")
    action2 = input(f"  Opcao: ").strip().upper()

    if action2 == "V":
        info("Conjuntos funcionais descartados.")
        return

    if action2 == "C":
        if not os.path.exists(json_path):
            warn(f"Arquivo nao encontrado: {json_path}")
            print(f"  Salve o JSON do navegador primeiro e renomeie para clusters_{cfg.EMPRESA_NAME}.json")
            return
        with open(json_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        tier3_saved = loaded.get("tier3", loaded).get("clusters", loaded.get("clusters", []))
        if not tier3_saved:
            warn("JSON nao contem conjuntos funcionais do Tier 3.")
            return
        _saved_llm_clusters = tier3_saved
        ok(f"{len(tier3_saved)} conjuntos funcionais carregados. Use opcao 3 para gerar o SQL.")
    else:
        warn("Opcao invalida. Conjuntos funcionais descartados.")
        return


def run_generate_org_sql():
    global _saved_llm_clusters

    if not cfg.EMPRESA_NAME:
        warn("Nome da empresa nao definido. Configure em Parametrizacao -> Nome da empresa.")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    json_path = os.path.join(OUTPUT_DIR, f"clusters_{cfg.EMPRESA_NAME}.json")
    if not os.path.exists(json_path):
        warn(f"Arquivo de conjuntos funcionais nao encontrado: {json_path}")
        info("Execute a opcao 2 primeiro para gerar e ajustar os conjuntos funcionais.")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)

    tier3_clusters = loaded.get("tier3", {}).get("clusters", loaded.get("clusters", []))
    if not tier3_clusters:
        warn("JSON nao contem conjuntos funcionais do Tier 3.")
        return

    print(f"  {C['green']}Conjuntos funcionais carregados:{C['reset']} {len(tier3_clusters)}")
    for c in tier3_clusters:
        routines = c.get("routines", c.get("common_routines", []))
        print(f"    {c.get('name', '?')}: {len(c.get('users', []))} usuarios, {len(routines)} rotinas")

    section("GERANDO SQL")
    spin("Conectando ao banco MSSQL...", 0.6)
    try:
        with get_connection() as conn:
            ok("Conectado com sucesso!")

            spin("Descobrindo estrutura das tabelas...", 1.0)
            schema = discover_columns_for_tables(SCHEMA_TABLES, conn)
            ok()
            print_schema_summary(schema)

            mapper = UserMapper(schema, conn)
            users = mapper.list_non_blocked_users()

            if not users:
                warn("Nenhum usuario nao bloqueado encontrado.")
                return

            total = len(users)
            all_reports = []
            fail_count = 0

            for i, user_info in enumerate(users, 1):
                login = user_info["login"]
                login_display = login if login else f"ID_{user_info['id']}"
                print(f"\r  {C['cyan']}[{i}/{total}]{C['reset']} \033[1m{login_display}\033[0m", end="", flush=True)
                try:
                    report = mapper.build_full_report(login)
                    if report is None:
                        fail_count += 1
                        continue
                    report["_conn"] = conn
                    all_reports.append(report)
                except Exception as e:
                    error(f"Erro ao mapear {login_display}: {e}")
                    fail_count += 1

            print()
            success_count = len(all_reports)
            print(f"  Mapeados: {C['green']}{success_count}{C['reset']} | Falhas: {C['red']}{fail_count}{C['reset']}")

            if not all_reports:
                warn("Nenhum relatorio gerado. Abortando.")
                return

            zero_routine_users = [rep["user"] for rep in all_reports if len(rep.get("routines_summary", [])) == 0]
            all_reports = [rep for rep in all_reports if len(rep.get("routines_summary", [])) > 0]
            if zero_routine_users:
                print(f"  {C['yellow']}[FILTRO]{C['reset']} {len(zero_routine_users)} usuarios sem rotinas ignorados.")

            tier3_clusters = normalize_tier3_sets(tier3_clusters, all_reports)

            from src.organizational_privileges import OrganizationalPrivilegeGenerator
            gen = OrganizationalPrivilegeGenerator(all_reports, schema, cfg.EMPRESA_NAME, conn)
            gen.generate_interactive(llm_clusters=tier3_clusters)

    except Exception as e:
        fail(str(e))


def run_batch_organizational(choice):
    global _saved_llm_clusters
    from src.organizational_privileges import OrganizationalPrivilegeGenerator

    if not cfg.EMPRESA_NAME:
        warn("Nome da empresa nao definido. Configure em Parametrizacao -> Nome da empresa.")
        return

    if cfg.LLM_API_KEY and _saved_llm_clusters is None:
        info(f"LLM configurada mas nenhum conjunto funcional pre-definido.")
        info(f"Use opcao {C['bold']}7{C['reset']} primeiro para pre-visualizar a analise da LLM.")
        info(f"Ou continue para usar o modo manual (Jaccard).")
        print()
        cont = input(f"  Continuar com modo manual? (S/n): ").strip().upper()
        if cont == "N":
            return

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    section("CONEXAO")
    spin("Conectando ao banco MSSQL...", 0.6)
    try:
        with get_connection() as conn:
            ok("Conectado com sucesso!")

            section("DISCOVERY")
            spin("Descobrindo estrutura das tabelas...", 1.0)
            schema = discover_columns_for_tables(SCHEMA_TABLES, conn)
            ok()
            print_schema_summary(schema)

            section("BATCH ORGANIZACIONAL")
            mapper = UserMapper(schema, conn)
            users = mapper.list_non_blocked_users()

            if not users:
                warn("Nenhum usuario nao bloqueado encontrado.")
                return

            total = len(users)
            print(f"\n  {C['cyan']}{chr(0x250C)}{'─' * 45}{chr(0x2510)}{C['reset']}")
            print(f"  {C['cyan']}{chr(0x2502)}{C['reset']} {C['bold']}Mapeando {total} usuarios...{C['reset']}")

            all_reports = []
            fail_count = 0

            for i, user_info in enumerate(users, 1):
                login = user_info["login"]
                login_display = login if login else f"ID_{user_info['id']}"
                print(f"\r  {C['cyan']}[{i}/{total}]{C['reset']} \033[1m{login_display}\033[0m", end="", flush=True)

                try:
                    report = mapper.build_full_report(login)
                    if report is None:
                        fail_count += 1
                        continue

                    report["_conn"] = conn
                    json_path = save_report_json(report, login)

                    all_reports.append(report)

                except Exception as e:
                    error(f"Erro ao mapear {login_display}: {e}")
                    fail_count += 1

            print()
            success_count = len(all_reports)
            print(f"  Mapeados: {C['green']}{success_count}{C['reset']} | Falhas: {C['red']}{fail_count}{C['reset']}")

            if not all_reports:
                warn("Nenhum relatorio gerado. Abortando.")
                return

            zero_routine_users = []
            filtered_reports = []
            for rep in all_reports:
                if len(rep.get("routines_summary", [])) == 0:
                    zero_routine_users.append(rep["user"])
                else:
                    filtered_reports.append(rep)
            if zero_routine_users:
                print(f"  {C['yellow']}[FILTRO]{C['reset']} {len(zero_routine_users)} usuarios sem rotinas ignorados.")
            if not filtered_reports:
                warn("Nenhum usuario com rotinas. Abortando.")
                return
            all_reports = filtered_reports

            print(f"\n  {C['cyan']}{chr(0x2502)}{C['reset']} {C['bold']}Analisando camadas organizacionais...{C['reset']}")

            if _saved_llm_clusters is not None:
                _saved_llm_clusters = normalize_tier3_sets(_saved_llm_clusters, all_reports)

            gen = OrganizationalPrivilegeGenerator(all_reports, schema, cfg.EMPRESA_NAME, conn)
            gen.generate_interactive(llm_clusters=_saved_llm_clusters)
            _saved_llm_clusters = None

    except Exception as e:
        fail(str(e))
        warn("Verifique:")
        info("  - SQL Server esta rodando?")
        info("  - ODBC Driver 17 instalado?")
        info("  - Credenciais corretas?")


def wizard_sanitation():
    B = C["bold"]; D = C["dim"]; R = C["reset"]; G = C["green"]; Y = C["yellow"]; CY = C["cyan"]; RD = C["red"]

    wizard_box("WIZARD — Saneamento de Privilegios", "Consulta APIs oficiais do Protheus Framework")

    from src.config import API_CONFIG
    if not API_CONFIG["bearer_token"]:
        warn("Token JWT nao configurado. Configure na opcao 4 (Parametrizacao).")
        return

    while True:
        wizard_box("WIZARD — Saneamento de Privilegios")
        wizard_step(1, 2, "Confirmar consulta")
        info("Serao consultados 6 endpoints de saneamento do Protheus:")
        info("  - Totais de inconsistencias")
        info("  - Menus com privilegios")
        info("  - Usuarios sem privilegios")
        info("  - Usuarios com privilegios exclusivos")
        info("  - Usuarios com privilegios por perfil")
        print()
        result = wizard_prompt_yn("Executar consulta de saneamento?", "S")
        if result is None:
            info("Wizard cancelado.")
            return
        if result:
            break
        info("Operacao cancelada.")
        return

    cls()
    print(BANNER)
    section("SANITATION API")

    try:
        from src.sanitation_report import fetch_sanitation_data, generate_sanitation_html, print_sanitation_summary

        spin_text("Consultando endpoints de saneamento...", "")
        data = fetch_sanitation_data()
        ok("Consulta concluida!")

        has_error = any(d.get("_error") for d in data.values() if isinstance(d, dict))
        if has_error:
            warn("Alguns endpoints retornaram erro. O appserver pode estar offline ou o token expirado.")

        print_sanitation_summary(data)

        section("HTML")
        spin("Gerando dashboard HTML...", 0.6)
        html_path = generate_sanitation_html(data)
        ok()
        success(f"Dashboard de saneamento salvo em: {B}{html_path}{R}")
        info(f"Abra o arquivo no navegador para visualizar.")

        if not has_error:
            import webbrowser
            webbrowser.open(f"file://{os.path.abspath(html_path)}")

    except Exception as e:
        fail(str(e))
        warn("Verifique se o appserver esta rodando e o token JWT e valido.")


def wizard_validation():
    B = C["bold"]; D = C["dim"]; R = C["reset"]; G = C["green"]; Y = C["yellow"]; CY = C["cyan"]; RD = C["red"]

    wizard_box("WIZARD — Validacao Cruzada", "Compara dados SQL Server vs API REST do Protheus")

    from src.config import API_CONFIG
    if not API_CONFIG["bearer_token"]:
        warn("Token JWT nao configurado. Configure na opcao 4 (Parametrizacao).")
        return

    login = "usr001"
    while True:
        wizard_box("WIZARD — Validacao Cruzada")
        wizard_step(1, 3, "Qual usuario validar?")
        info("Digite o login do usuario ou ENTER para validar TODOS.")
        print()
        val = input(f"  {B}Usuario{R} [{D}{login} | ENTER = TODOS | X = cancelar{R}]: ").strip()
        if val.upper() == "X":
            info("Wizard cancelado.")
            return
        break

    cls()
    print(BANNER)

    section("CONEXAO")
    spin("Conectando ao banco MSSQL...", 0.6)
    try:
        from src.database import get_connection
        with get_connection() as conn:
            ok("Conectado com sucesso!")

            from src.discovery import discover_columns_for_tables, print_schema_summary
            from src.user_mapper import UserMapper
            from src.api_validator import APIValidator, generate_validation_html

            section("DISCOVERY")
            spin("Descobrindo estrutura das tabelas...", 1.0)
            schema = discover_columns_for_tables(SCHEMA_TABLES, conn)
            ok()
            print_schema_summary(schema)

            mapper = UserMapper(schema, conn)

            section("USUARIOS SQL")
            if val:
                sql_users = [mapper.find_user(val)] if mapper.find_user(val) else []
            else:
                sql_users = mapper.list_non_blocked_users()
            ok(f"{len(sql_users)} usuarios encontrados via SQL")

            section("API")
            spin_text("Testando conexao com API...", "")
            api_ok, api_msg = _test_api_connection()
            ok(f"API: {api_msg}")
            if not api_ok:
                warn("Validacao parcial — API indisponivel.")
                return

            section("VALIDACAO")
            info("Comparando usuarios SQL vs API...")
            validator = APIValidator(mapper, schema)
            report = validator.run_full_validation(sql_users)

            json_path = validator.save_report()
            ok(f"Relatorio JSON: {json_path}")

            section("HTML")
            spin("Gerando dashboard HTML...", 0.6)
            html_path = generate_validation_html(report)
            ok()
            success(f"Dashboard de validacao salvo em: {B}{html_path}{R}")

            total = report["summary"]["total_divergences"]
            if total == 0:
                success("Nenhuma divergencia encontrada entre SQL e API!")
            else:
                warn(f"{total} divergencias encontradas. Verifique o dashboard.")

            import webbrowser
            webbrowser.open(f"file://{os.path.abspath(html_path)}")

    except Exception as e:
        fail(str(e))


def _test_api_connection():
    try:
        from src.protheus_api import create_api
        api = create_api()
        return api.test_connection()
    except Exception as e:
        return False, str(e)


def menu_validacao_api():
    B = C["bold"]; D = C["dim"]; W = C["white"]; RD = C["red"]; R = C["reset"]
    while True:
        cls()
        print(BANNER)
        from src.database import is_offline
        if is_offline():
            show_offline_banner()
        L = C["cyan"]
        BOX = 52
        def row(text):
            import re
            v = re.sub(r"\033\[[0-9;]*m", "", text)
            pad = BOX - len(v)
            return f"  {text}{' ' * pad}{L}║{R}"

        from src.config import API_CONFIG
        api_status = f"{C['green']}CONFIGURADO{R}" if API_CONFIG["bearer_token"] else f"{C['red']}NAO CONFIGURADO{R}"

        print(f"  {L}╔{'═' * BOX}╗{R}")
        print(row(f"{L}║{R}  {B}VALIDACAO API (Protheus Framework){R}"))
        print(row(f"{L}║{R}  {D}{'─' * (BOX - 3)}{R}"))
        print(row(f"{L}║{R}  {B}1{R} │ {W}Saneamento de Privilegios{R}"))
        print(row(f"{L}║{R}    │ {D}Consultar APIs de saneamento do framework{R}"))
        print(row(f"{L}║{R}  {B}2{R} │ {W}Validacao Cruzada SQL vs API{R}"))
        print(row(f"{L}║{R}    │ {D}Comparar dados do banco com a API oficial{R}"))
        print(row(f"{L}║{R}  {B}3{R} │ {W}Testar Conexao API{R}"))
        print(row(f"{L}║{R}    │ {D}Verificar se o appserver responde{R}"))
        print(row(f"{L}║{R}  {D}{'─' * (BOX - 3)}{R}"))
        print(row(f"{L}║{R}  {D}  Status: {api_status}{R}"))
        print(row(f"{L}║{R}  {B}0{R} │ {RD}Voltar{R}"))
        print(f"  {L}╚{'═' * BOX}╝{R}")
        print()
        sub = input(f"  {B}Opcao:{R} ").strip()
        cls()
        if sub == "0":
            break
        elif sub == "1":
            wizard_sanitation()
        elif sub == "2":
            wizard_validation()
        elif sub == "3":
            ok_status, msg = _test_api_connection()
            if ok_status:
                success(msg)
            else:
                error(msg)
            wait_enter()
        else:
            print(f"\n  {C['red']}Opcao invalida!{C['reset']}\n")


def main():
    current_login = "usr001"
    first_run = True
    is_org = (cfg.PRIVILEGE_MODE == "organizational_layer")

    while True:
        if not first_run:
            wait_enter()
        first_run = False

        try:
            choice = menu()
        except (EOFError, KeyboardInterrupt):
            cls()
            print(f"\n  {C['yellow']}Saindo...{C['reset']}\n")
            break

        cls()

        if choice == "0":
            print(f"\n  {C['yellow']}Saindo...{C['reset']}\n")
            break

        elif choice == "1":
            current_login = wizard_mapeamento(current_login)

        elif choice == "2":
            wizard_ferramentas()

        elif choice == "3":
            if is_org:
                menu_camadas_org()
            else:
                print(f"\n  {C['red']}Opcao invalida!{C['reset']}\n")

        elif choice == "4":
            menu_parametrizacao()

        elif choice == "5":
            menu_validacao_api()

        else:
            print(f"\n  {C['red']}Opcao invalida!{C['reset']}\n")


if __name__ == "__main__":
    load_user_config()
    main()
