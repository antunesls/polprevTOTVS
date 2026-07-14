import json
import os
from src.config import OUTPUT_DIR
from src.protheus_api import create_api


class APIValidator:
    def __init__(self, mapper, schema):
        self.mapper = mapper
        self.schema = schema
        self.api = create_api()
        self.divergences = {
            "users": [],
            "routines": [],
            "privileges": [],
            "menus": [],
        }

    def validate_users(self, sql_users):
        api_users = self.api.get_users()
        if api_users.get("_error"):
            self.divergences["users"].append({
                "type": "api_error",
                "message": f"API indisponivel: {api_users.get('_body', '')}",
            })
            return

        api_items = api_users.get("items", [])
        api_logins = set()
        for item in api_items:
            login = item.get("USR_CODIGO") or item.get("USR_LOGIN") or item.get("id", "")
            if login:
                api_logins.add(login.strip())

        sql_logins = set()
        for u in sql_users:
            login = u.get("login", "").strip()
            if login:
                sql_logins.add(login)

        only_sql = sql_logins - api_logins
        only_api = api_logins - sql_logins

        for login in sorted(only_sql):
            self.divergences["users"].append({
                "type": "only_sql",
                "login": login,
                "message": f"Usuario '{login}' encontrado apenas no SQL (nao na API)",
            })
        for login in sorted(only_api):
            self.divergences["users"].append({
                "type": "only_api",
                "login": login,
                "message": f"Usuario '{login}' encontrado apenas na API (nao no SQL)",
            })

    def validate_routine_users(self, routine):
        sql_data = self.mapper.map_routine_users(routine)
        sql_user_ids = set(sql_data.get("user_ids", []))

        api_data = self.api.get_function_users(routine, pageSize=999)
        if api_data.get("_error"):
            self.divergences["routines"].append({
                "type": "api_error",
                "routine": routine,
                "message": f"API indisponivel: {api_data.get('_body', '')}",
            })
            return

        api_items = api_data.get("items", [])
        api_user_ids = set()
        for item in api_items:
            uid = item.get("USR_ID") or item.get("id", "")
            if uid:
                api_user_ids.add(str(uid))

        only_sql = sql_user_ids - api_user_ids
        only_api = api_user_ids - sql_user_ids

        for uid in sorted(only_sql):
            self.divergences["routines"].append({
                "type": "only_sql",
                "routine": routine,
                "user_id": uid,
                "message": f"Usuario ID {uid} tem acesso a '{routine}' apenas no SQL",
            })
        for uid in sorted(only_api):
            self.divergences["routines"].append({
                "type": "only_api",
                "routine": routine,
                "user_id": uid,
                "message": f"Usuario ID {uid} tem acesso a '{routine}' apenas na API",
            })

    def validate_menu_def(self, routine):
        api_data = self.api.get_menu_def(routine)
        if api_data.get("_error"):
            self.divergences["menus"].append({
                "type": "api_error",
                "routine": routine,
                "message": f"API menudef indisponivel para '{routine}'",
            })
            return None
        return api_data

    def run_full_validation(self, sql_users, routines_to_check=None):
        self.divergences = {"users": [], "routines": [], "privileges": [], "menus": []}

        self.validate_users(sql_users)

        if routines_to_check:
            for routine in routines_to_check:
                self.validate_routine_users(routine)

        return self.divergences

    def save_report(self, filename="validation_report.json"):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        filepath = os.path.join(OUTPUT_DIR, filename)

        total = sum(len(v) for v in self.divergences.values())
        report = {
            "summary": {
                "total_divergences": total,
                "users": len(self.divergences["users"]),
                "routines": len(self.divergences["routines"]),
                "privileges": len(self.divergences["privileges"]),
                "menus": len(self.divergences["menus"]),
            },
            "divergences": self.divergences,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        return filepath


def generate_validation_html(report, output_path=None):
    if output_path is None:
        output_path = os.path.join(OUTPUT_DIR, "divergencias.html")

    summary = report.get("summary", {})
    divergences = report.get("divergences", {})

    users_div = divergences.get("users", [])
    routines_div = divergences.get("routines", [])
    privileges_div = divergences.get("privileges", [])
    menus_div = divergences.get("menus", [])

    def _badge(count, color):
        if count == 0:
            return f'<span style="background:#4caf50;color:#fff;padding:2px 8px;border-radius:4px">{count}</span>'
        return f'<span style="background:{color};color:#fff;padding:2px 8px;border-radius:4px;font-weight:bold">{count}</span>'

    def _render_table(title, items, columns):
        if not items:
            return f"<h3>{title} {_badge(0, '#4caf50')}</h3><p style='color:#666'>Nenhuma divergencia encontrada.</p>"

        rows = ""
        for item in items:
            cells = "".join(f"<td>{item.get(c, '')}</td>" for c in columns)
            rows += f"<tr>{cells}</tr>"

        return f"""
        <h3>{title} {_badge(len(items), '#f44336')}</h3>
        <table>
            <thead><tr>{''.join(f'<th>{c}</th>' for c in columns)}</tr></thead>
            <tbody>{rows}</tbody>
        </table>"""

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Validacao de Privilegios - SQL vs API</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background:#1a1a2e; color:#eee; padding:20px; }}
h1 {{ color:#00d4ff; margin-bottom:8px; }}
h2 {{ color:#aaa; font-weight:400; margin-bottom:24px; font-size:1rem; }}
h3 {{ margin:20px 0 10px; color:#00d4ff; }}
.summary {{ display:flex; gap:16px; margin-bottom:30px; flex-wrap:wrap; }}
.card {{ background:#16213e; border:1px solid #0f3460; border-radius:8px; padding:16px 24px; text-align:center; min-width:120px; }}
.card .count {{ font-size:2rem; font-weight:bold; }}
.card .label {{ color:#888; font-size:0.8rem; margin-top:4px; }}
.green {{ color:#4caf50; }}
.red {{ color:#f44336; }}
.yellow {{ color:#ff9800; }}
table {{ width:100%; border-collapse:collapse; margin:10px 0 25px; background:#16213e; border-radius:8px; overflow:hidden; }}
th {{ background:#0f3460; padding:10px 12px; text-align:left; font-size:0.85rem; color:#00d4ff; }}
td {{ padding:8px 12px; border-bottom:1px solid #0f3460; font-size:0.85rem; }}
tr:hover {{ background:#1a2744; }}
</style>
</head>
<body>
<h1>Validacao de Privilegios</h1>
<h2>Comparacao entre dados do SQL Server e API REST do Protheus</h2>

<div class="summary">
    <div class="card">
        <div class="count {'red' if summary.get('total_divergences', 0) else 'green'}">{summary.get('total_divergences', 0)}</div>
        <div class="label">Total Divergencias</div>
    </div>
    <div class="card">
        <div class="count {'red' if summary.get('users', 0) else 'green'}">{summary.get('users', 0)}</div>
        <div class="label">Usuarios</div>
    </div>
    <div class="card">
        <div class="count {'red' if summary.get('routines', 0) else 'green'}">{summary.get('routines', 0)}</div>
        <div class="label">Rotinas</div>
    </div>
    <div class="card">
        <div class="count {'red' if summary.get('privileges', 0) else 'green'}">{summary.get('privileges', 0)}</div>
        <div class="label">Privilegios</div>
    </div>
    <div class="card">
        <div class="count {'red' if summary.get('menus', 0) else 'green'}">{summary.get('menus', 0)}</div>
        <div class="label">Menus</div>
    </div>
</div>

{_render_table("Usuarios", users_div, ["type", "login", "message"])}
{_render_table("Rotinas", routines_div, ["type", "routine", "user_id", "message"])}
{_render_table("Privilegios", privileges_div, ["type", "privilege", "message"])}
{_render_table("Menus", menus_div, ["type", "routine", "message"])}

</body>
</html>"""

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path
