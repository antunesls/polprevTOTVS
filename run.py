#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
import time
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database import get_connection, build_connection_string
from src.discovery import discover_columns_for_tables, print_schema_summary
from src.config import SCHEMA_TABLES, OUTPUT_DIR, DB_CONFIG, load_user_config, save_user_config
import src.config as cfg
from src.user_mapper import UserMapper
from src.privilege_generator import PrivilegeGenerator, save_report_json
from src.dashboard import generate_html


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


def show_offline_banner():
    D = C["dim"]; R = C["reset"]; G = C["green"]
    print(f"  {D}─── {G}MODO OFFLINE{D} ─── Dados carregados do export.json ───{R}")
    print()


def menu():
    cls()
    print(BANNER)
    from src.database import is_offline
    if is_offline():
        show_offline_banner()
    L = C["cyan"]; R = C["reset"]; B = C["bold"]; D = C["dim"]; W = C["white"]; RD = C["red"]
    BOX = 52
    def row(text):
        import re
        v = re.sub(r"\033\[[0-9;]*m", "", text)
        pad = BOX - len(v)
        return f"  {text}{' ' * pad}{L}║{R}"

    print(f"  {L}╔{'═' * BOX}╗{R}")
    print(row(f"{L}║{R}  {B}1{R} │ {W}Apenas mapear acessos do usuario{R}"))
    print(row(f"{L}║{R}    │ {D}Relatorio JSON com rotinas e permissoes{R}"))
    print(row(f"{L}║{R}  {B}2{R} │ {W}Mapear + Gerar grupo de privilegios{R}"))
    print(row(f"{L}║{R}    │ {D}Relatorio JSON + Script SQL p/ SYS_RULES{R}"))
    print(row(f"{L}║{R}  {B}3{R} │ {W}Mapear + Gerar dashboard HTML{R}"))
    print(row(f"{L}║{R}    │ {D}Relatorio JSON + Dashboard grafico{R}"))
    print(row(f"{L}║{R}  {B}4{R} │ {W}Parametrizacao{R}"))
    print(row(f"{L}║{R}    │ {D}Configurar banco e preferencias{R}"))
    print(row(f"{L}║{R}  {B}5{R} │ {W}Exportar dados (SQL){R}"))
    print(row(f"{L}║{R}    │ {D}Gerar query para extracao offline{R}"))
    print(row(f"{L}║{R}  {B}6{R} │ {W}Importar dados (JSON){R}"))
    print(row(f"{L}║{R}    │ {D}Carregar export.json p/ modo offline{R}"))
    if cfg.LLM_API_KEY and cfg.PRIVILEGE_MODE == "organizational_layer":
        print(row(f"{L}║{R}  {B}7{R} │ {W}Pre-visualizar LLM{R}"))
        print(row(f"{L}║{R}    │ {D}Analisar clusters antes de gerar{R}"))
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


def run_generate_privileges(report, schema, login):
    if report is None:
        warn("Sem dados de mapeamento. Execute a opcao 1 primeiro.")
        return

    section("PRIVILEGIOS")
    info("Gerando script SQL...")
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


def run_batch(choice):
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

                    if choice == "2":
                        default_rule = f"ACESSOS_{login.upper()[:8]}"
                        generator = PrivilegeGenerator(report, schema)
                        sql = generator.generate_sql(default_rule)
                        sql_path = generator.save_sql(sql, f"{login}_privileges.sql")
                        info(f"  Script SQL: {sql_path}")

                    if choice == "3":
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
            print(row(f"{L}║{R}  {B}5{N}{R} │ {W}Nome da empresa ...{R} [{D}{empresa_disp}{R}]"))
            print(row(f"{L}║{R}  {D}{'─' * (BOX - 3)}{R}"))
            print(row(f"{L}║{R}  {B}5{A}{R} │ {W}LLM API Key .......{R} [{D}{llm_key_disp}{R}]"))
            print(row(f"{L}║{R}  {B}5{B}{R} │ {W}LLM Model .........{R} [{D}{llm_model_disp}{R}]"))
            print(row(f"{L}║{R}  {B}5{C}{R} │ {W}LLM Base URL ......{R} [{D}{llm_url_disp}{R}]"))
        print(row(f"{L}║{R}  {D}{'─' * (BOX - 3)}{R}"))
        print(row(f"{L}║{R}  {B}6{R} │ {W}Modo de privilegio{R} [{G}{mode_disp}{R}]"))
        print(row(f"{L}║{R}  {D}{'─' * (BOX - 3)}{R}"))
        print(row(f"{L}║{R}  {B}7{R} │ {W}Testar conexao{R}"))
        print(row(f"{L}║{R}  {B}8{R} │ {W}Salvar configuracoes{R}"))
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

        else:
            print(f"\n  {C['red']}Opcao invalida!{C['reset']}\n")

        if sub != "0":
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

            from src.llm_categorizer import suggest_clusters, build_prompt

            users_data = []
            for rep in all_reports:
                routines = []
                for r in rep.get("routines_summary", []):
                    code = r.get("routine", "")
                    desc = r.get("description", "")
                    if code:
                        routines.append(f"{code} - {desc}" if desc else code)
                users_data.append({
                    "user": rep["user"],
                    "department": rep.get("user_depto", ""),
                    "routines": routines,
                })

            print(f"\n  {C['cyan']}[LLM]{C['reset']} Enviando {len(users_data)} usuarios para analise...")
            llm_result = suggest_clusters(users_data)

            if not llm_result or not llm_result.get("clusters"):
                warn("LLM nao retornou clusters validos. Use opcao 2 para modo manual (Jaccard).")
                return

            llm_clusters = llm_result.get("clusters", [])

            G = C["green"]; CY = C["cyan"]; Y = C["yellow"]; R = C["reset"]; D = C["dim"]; B = C["bold"]
            print()
            for idx, c in enumerate(llm_clusters, 1):
                name = c.get("name", f"CLUSTER_{idx}")
                reason = c.get("reason", "")
                users_list = c.get("users", [])
                routines_list = c.get("common_routines", [])

                print(f"  {CY}{chr(0x250C)}{'─' * 52}{chr(0x2510)}{R}")
                print(f"  {CY}{chr(0x2502)}{R} {B}Cluster #{idx}: {G}{name}{R}")
                if reason:
                    print(f"  {CY}{chr(0x2502)}{R} {D}Motivo: {reason}{R}")
                print(f"  {CY}{chr(0x2502)}{R} Usuarios ({len(users_list)}): {', '.join(users_list[:6])}{'...' if len(users_list) > 6 else ''}")
                print(f"  {CY}{chr(0x2502)}{R} Rotinas comuns: {len(routines_list)}")
                sample = routines_list[:6]
                print(f"  {CY}{chr(0x2502)}{R}   Ex: {', '.join(sample)}{'...' if len(routines_list) > 6 else ''}")
                print(f"  {CY}{chr(0x2514)}{'─' * 52}{chr(0x2518)}{R}")

            print()
            print(f"  {B}[G]{R} Gerar SQL completo (4 tiers) com estes clusters")
            print(f"  {B}[E]{R} Editar nomes antes de gerar")
            print(f"  {B}[V]{R} Voltar (nao gerar nada)")
            action = input(f"  Opcao: ").strip().upper()

            if action == "V":
                info("Clusters descartados.")
                return

            if action == "E":
                print(f"\n  {B}Edicao de nomes:{R}")
                for idx, c in enumerate(llm_clusters):
                    name = c.get("name", f"CLUSTER_{idx}")
                    users_list = c.get("users", [])
                    val = input(f"  Cluster #{idx} ({', '.join(users_list[:3])}...) [{name}]: ").strip()
                    if val:
                        c["name"] = val.upper()

            _saved_llm_clusters = llm_clusters
            info(f"Clusters salvos ({len(llm_clusters)}). Use opcao 2 para gerar o SQL.")

    except Exception as e:
        fail(str(e))


def run_batch_organizational(choice):
    global _saved_llm_clusters
    from src.organizational_privileges import OrganizationalPrivilegeGenerator

    if not cfg.EMPRESA_NAME:
        warn("Nome da empresa nao definido. Configure em Parametrizacao -> Nome da empresa.")
        return

    if cfg.LLM_API_KEY and _saved_llm_clusters is None:
        info(f"LLM configurada mas nenhum cluster pre-definido.")
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

            print(f"\n  {C['cyan']}{chr(0x2502)}{C['reset']} {C['bold']}Analisando camadas organizacionais...{C['reset']}")

            gen = OrganizationalPrivilegeGenerator(all_reports, schema, cfg.EMPRESA_NAME, conn)
            gen.generate_interactive(llm_clusters=_saved_llm_clusters)
            _saved_llm_clusters = None

    except Exception as e:
        fail(str(e))
        warn("Verifique:")
        info("  - SQL Server esta rodando?")
        info("  - ODBC Driver 17 instalado?")
        info("  - Credenciais corretas?")


def main():
    report = None
    schema = None
    current_login = "usr001"
    first_run = True

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

        elif choice in ("1", "2", "3"):
            if choice == "2" and cfg.PRIVILEGE_MODE == "organizational_layer":
                run_batch_organizational(choice)
                continue

            login_input = input(f"  {C['bold']}Usuario{C['reset']} [{C['dim']}{current_login} | ENTER = TODOS{C['reset']}]: ").strip()
            if login_input:
                current_login = login_input

                if choice == "1":
                    report, schema, current_login = run_mapping(current_login)
                elif choice == "2":
                    report, schema, current_login = run_mapping(current_login)
                    if report:
                        run_generate_privileges(report, schema, current_login)
                elif choice == "3":
                    report, schema, current_login = run_mapping(current_login)
                    if report:
                        run_dashboard(current_login)
            else:
                run_batch(choice)

        elif choice == "4":
            menu_parametrizacao()

        elif choice == "5":
            run_export()

        elif choice == "6":
            run_import()

        elif choice == "7":
            run_llm_preview()

        else:
            print(f"\n  {C['red']}Opcao invalida!{C['reset']}\n")


if __name__ == "__main__":
    load_user_config()
    main()
