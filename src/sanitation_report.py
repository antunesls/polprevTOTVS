import json
import os
from src.config import OUTPUT_DIR
from src.protheus_api import create_api


def fetch_sanitation_data():
    api = create_api()
    return api.collect_all_sanitation_data()


def generate_sanitation_html(data=None, output_path=None):
    if data is None:
        data = fetch_sanitation_data()

    if output_path is None:
        output_path = os.path.join(OUTPUT_DIR, "saneamento_privilegios.html")

    totals = data.get("totals", {})
    menus_wp = data.get("menusWithPrivileges", {})
    users_wo = data.get("usersWithoutPrivileges", {})
    users_exclusive = data.get("usersWithPrivilegesExclusive", {})
    users_profile = data.get("usersWithPrivilegesOnProfile", {})

    def _safe_items(data, key="items"):
        if isinstance(data, dict):
            items = data.get(key, [])
            if isinstance(items, list):
                return items
        return []

    def _card(title, value, subtitle, color="#00d4ff"):
        v = value
        if isinstance(v, (int, float)):
            v = str(v)
        elif v is None:
            v = "-"
        return f"""<div class="card">
    <div class="count" style="color:{color}">{v}</div>
    <div class="label">{subtitle}</div>
    <div class="title">{title}</div>
</div>"""

    def _render_table(title, items, columns):
        if not items:
            return f"<h3>{title}</h3><p style='color:#666'>Nenhum registro encontrado.</p>"

        rows = ""
        for item in items:
            cells = ""
            for col in columns:
                val = item.get(col, "")
                if isinstance(val, dict):
                    val = json.dumps(val, ensure_ascii=False)[:120]
                cells += f"<td>{val}</td>"
            rows += f"<tr>{cells}</tr>"

        return f"""
        <h3>{title} ({len(items)} registros)</h3>
        <table>
            <thead><tr>{''.join(f'<th>{c}</th>' for c in columns)}</tr></thead>
            <tbody>{rows}</tbody>
        </table>"""

    totals_value = totals.get("total", totals.get("count",
                  totals.get("qtd", "?"))) if not totals.get("_error") else "ERRO"

    cards_html = ""
    cards_html += _card("Total de Inconsistencias", totals_value, "Problemas detectados", "#f44336")

    mwp_items = _safe_items(menus_wp)
    cards_html += _card("Menus com Privilegios", len(mwp_items), "Menus que possuem privilegios", "#ff9800")

    uwo_items = _safe_items(users_wo)
    cards_html += _card("Usuarios sem Privilegios", len(uwo_items), "Sem nenhum privilegio atribuido", "#f44336")

    ue_items = _safe_items(users_exclusive)
    cards_html += _card("Privilegios Exclusivos", len(ue_items), "Fora de perfil/grupo", "#e91e63")

    up_items = _safe_items(users_profile)
    cards_html += _card("Privilegios por Perfil", len(up_items), "Herdados de perfil", "#4caf50")

    has_error = any(d.get("_error") for d in data.values() if isinstance(d, dict))

    error_banner = ""
    if has_error:
        error_banner = """<div class="error-banner">
            Alguns endpoints retornaram erro. Verifique a conexao com o appserver e o token JWT.
        </div>"""

    tables_html = ""

    mwp_columns = []
    if mwp_items:
        mwp_columns = list(mwp_items[0].keys())[:6]
    if mwp_columns:
        tables_html += _render_table("Menus com Privilegios", mwp_items, mwp_columns)

    uwo_columns = []
    if uwo_items:
        uwo_columns = list(uwo_items[0].keys())[:5]
    if uwo_columns:
        tables_html += _render_table("Usuarios sem Privilegios", uwo_items, uwo_columns)

    ue_columns = []
    if ue_items:
        ue_columns = list(ue_items[0].keys())[:5]
    if ue_columns:
        tables_html += _render_table("Usuarios com Privilegios Exclusivos", ue_items, ue_columns)

    up_columns = []
    if up_items:
        up_columns = list(up_items[0].keys())[:5]
    if up_columns:
        tables_html += _render_table("Usuarios com Privilegios por Perfil", up_items, up_columns)

    raw_totals = json.dumps(totals, indent=2, ensure_ascii=False) if not totals.get("_error") else "{}"

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Saneamento de Privilegios - Protheus</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background:#1a1a2e; color:#eee; padding:20px; }}
h1 {{ color:#00d4ff; margin-bottom:8px; }}
h2 {{ color:#aaa; font-weight:400; margin-bottom:24px; font-size:1rem; }}
h3 {{ margin:24px 0 10px; color:#00d4ff; }}
.summary {{ display:flex; gap:16px; margin-bottom:30px; flex-wrap:wrap; }}
.card {{ background:#16213e; border:1px solid #0f3460; border-radius:8px; padding:16px 24px; text-align:center; min-width:140px; }}
.card .count {{ font-size:2rem; font-weight:bold; }}
.card .label {{ color:#888; font-size:0.8rem; margin-top:4px; }}
.card .title {{ color:#aaa; font-size:0.75rem; margin-top:2px; }}
table {{ width:100%; border-collapse:collapse; margin:10px 0 25px; background:#16213e; border-radius:8px; overflow:hidden; }}
th {{ background:#0f3460; padding:10px 12px; text-align:left; font-size:0.8rem; color:#00d4ff; text-transform:uppercase; }}
td {{ padding:8px 12px; border-bottom:1px solid #0f3460; font-size:0.8rem; max-width:300px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
tr:hover {{ background:#1a2744; }}
.error-banner {{ background:#4a1525; border:1px solid #f44336; border-radius:8px; padding:12px 20px; margin-bottom:20px; color:#f44336; font-size:0.9rem; }}
.raw-data {{ background:#0d1117; border-radius:8px; padding:16px; margin-top:30px; }}
.raw-data pre {{ color:#8b949e; font-size:0.75rem; overflow-x:auto; white-space:pre-wrap; word-break:break-all; }}
.footer {{ color:#555; font-size:0.7rem; text-align:center; margin-top:40px; }}
</style>
</head>
<body>
<h1>Saneamento de Privilegios</h1>
<h2>Dados oficiais da API REST do Protheus Framework</h2>
{error_banner}
<div class="summary">
{cards_html}
</div>
{tables_html}
<div class="raw-data">
    <h3 style="color:#00d4ff;margin-top:0">Dados Brutos - sanitation/totals</h3>
    <pre>{raw_totals}</pre>
</div>
<div class="footer">polprevTOTVS - Saneamento de Privilegios</div>
</body>
</html>"""

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path


def print_sanitation_summary(data):
    C = {
        "reset": "\033[0m", "bold": "\033[1m", "dim": "\033[2m",
        "red": "\033[91m", "green": "\033[92m", "yellow": "\033[93m",
        "blue": "\033[94m", "cyan": "\033[96m",
    }

    print(f"\n  {C['cyan']}{C['bold']}[SANITATION]{C['reset']}")

    for key, result in data.items():
        if result.get("_error"):
            if result.get("_conn_refused"):
                print(f"  {C['red']}[ERRO]{C['reset']} {key}: Conexao recusada pelo appserver")
            else:
                print(f"  {C['yellow']}[AVISO]{C['reset']} {key}: HTTP {result.get('_status')}")
            continue

        items = result.get("items", []) if isinstance(result, dict) else []
        count = len(items) if isinstance(items, list) else 0

        if isinstance(result, dict) and not items:
            count = result.get("total", result.get("count", result.get("qtd", "?")))

        color = C["green"] if count == 0 else C["yellow"]
        print(f"  {color}[{count}]{C['reset']} {key}")
