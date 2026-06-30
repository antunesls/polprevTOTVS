#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
import time
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database import get_connection
from src.discovery import discover_columns_for_tables, print_schema_summary
from src.config import SCHEMA_TABLES, OUTPUT_DIR
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


def menu():
    cls()
    print(BANNER)
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
            login_input = input(f"  {C['bold']}Usuario{C['reset']} [{C['dim']}{current_login}{C['reset']}]: ").strip()
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
            print(f"\n  {C['red']}Opcao invalida!{C['reset']}\n")


if __name__ == "__main__":
    main()
