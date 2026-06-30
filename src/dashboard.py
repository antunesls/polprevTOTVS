import json
import os
from collections import Counter
from src.config import OUTPUT_DIR


def build_tree(items):
    by_id = {}
    children = {}
    roots = []

    for item in items:
        item_id = item["item_id"]
        item["_children"] = []
        by_id[item_id] = item
        children.setdefault(item_id, [])

    for item in items:
        father = item.get("father_id", "")
        if father and father in by_id and father != item["item_id"]:
            children.setdefault(father, []).append(item)
        elif not father or father not in by_id:
            roots.append(item)
        elif father == item["item_id"]:
            roots.append(item)

    for father_id, kids in children.items():
        if father_id in by_id:
            by_id[father_id]["_children"] = kids

    return roots


def _render_tree(nodes, level=0):
    html = ""
    indent = "  " * level
    for node in nodes:
        func = (node.get("function_code") or "").strip()
        desc = (node.get("description") or "").strip()
        has_func = bool(func)
        has_kids = bool(node.get("_children"))

        cls = "tree-func" if has_func else "tree-folder"
        icon = "&#9881;" if has_func else "&#128193;"

        html += f'{indent}<li class="{cls}">\n'
        html += f'{indent}  <span class="tree-toggle">{icon}</span>\n'
        html += f'{indent}  <span class="tree-label">'
        if has_func:
            html += f'<code>{func}</code>'
        if desc:
            html += f' <small>{desc}</small>'
        html += '</span>\n'

        if has_kids:
            html += f'{indent}  <ul>\n'
            html += _render_tree(node["_children"], level + 2)
            html += f'{indent}  </ul>\n'

        html += f'{indent}</li>\n'
    return html


def generate_html(report_path):
    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    user = report.get("user", "?")
    user_id = report.get("user_id", "?")
    total_menus = report.get("total_menus", 0)
    total_routines = report.get("total_routines", 0)
    groups = report.get("groups", [])
    menus = report.get("menus", [])
    routines = report.get("routines_summary", [])
    privileges = report.get("privileges_raw", {})

    items_with_func = sum(1 for r in routines if r.get("routine", "").strip())
    items_no_func = total_routines - items_with_func
    groups_count = len(groups)

    prefix_counts = Counter()
    for r in routines:
        code = r.get("routine", "").strip()
        if code:
            prefix = code[:4] if not code[0].isdigit() else code[:5]
            prefix_counts[prefix] += 1
    top_prefixes = prefix_counts.most_common(15)

    pr_yes = sum(1 for r in routines if r.get("has_explicit_privilege"))
    pr_no = total_routines - pr_yes

    acbrowse_disabled_count = sum(1 for r in routines if r.get("disabled_by_acbrowse", False))
    saldo = total_routines - acbrowse_disabled_count

    tree_roots = []
    for menu in menus:
        if menu.get("items"):
            tree_roots.extend(build_tree(menu["items"]))

    tree_html = _render_tree(tree_roots)

    table_rows = ""
    browse_routines_count = 0
    acbrowse_disabled_count = 0
    for i, r in enumerate(routines):
        code = (r.get("routine") or "").strip()
        desc = (r.get("description") or "").strip()
        menu_name = (r.get("menu_name") or "").strip()
        priv = "SIM" if r.get("has_explicit_privilege") else "NAO"
        disabled = r.get("disabled_by_acbrowse", False)
        if disabled:
            acbrowse_disabled_count += 1

        status_html = '<span class="status-ok">OK</span>'
        if disabled:
            status_html = '<span class="status-blocked">BLOQ</span>'

        browse_html = ""
        bp = r.get("browse_permissions", [])
        if bp:
            browse_routines_count += 1
            parts = []
            for op in bp:
                if not op.get("available"):
                    parts.append(f'<span class="bp-off">{op["menu_oper"]}</span>')
                    continue
                feats = op.get("features", [])
                if not feats:
                    parts.append(f'<span class="bp-avail">{op["menu_oper"]}</span>')
                else:
                    granted = any(f.get("granted") == "PERMITIDO" for f in feats)
                    cls = "bp-granted" if granted else "bp-blocked"
                    parts.append(f'<span class="{cls}">{op["menu_oper"]}</span>')
            browse_html = "".join(parts)

        tr_class = ' class="row-disabled"' if disabled else ""
        table_rows += (
            f'<tr{tr_class}><td>{code}</td><td>{desc}</td>'
            f'<td>{menu_name}</td><td>{status_html}</td>'
            f'<td class="priv-{"yes" if priv=="SIM" else "no"}">{priv}</td>'
            f'<td class="browse-cell">{browse_html}</td></tr>\n'
        )

    html = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>polprevTOTVS - Dashboard de Acessos</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: 'Segoe UI', system-ui, sans-serif; background:#0d1117; color:#c9d1d9; padding:24px; }}
header {{ text-align:center; margin-bottom:32px; }}
header h1 {{ font-size:28px; color:#58a6ff; }}
header p {{ color:#8b949e; margin-top:4px; }}

.kpi-grid {{ display:grid; grid-template-columns: repeat(5,1fr); gap:16px; margin-bottom:32px; }}
.kpi-card {{ background:#161b22; border:1px solid #30363d; border-radius:12px; padding:20px; text-align:center; }}
.kpi-card .kpi-value {{ font-size:36px; font-weight:700; }}
.kpi-card .kpi-label {{ font-size:13px; color:#8b949e; margin-top:4px; }}
.kpi-card.c1 .kpi-value {{ color:#58a6ff; }}
.kpi-card.c2 .kpi-value {{ color:#3fb950; }}
.kpi-card.c3 .kpi-value {{ color:#d2991d; }}
.kpi-card.c4 .kpi-value {{ color:#f78166; }}
.kpi-card.c5 .kpi-value {{ color:#bc8cff; }}

.charts-grid {{ display:grid; grid-template-columns: 1fr 1fr; gap:24px; margin-bottom:32px; }}
.chart-box {{ background:#161b22; border:1px solid #30363d; border-radius:12px; padding:20px; }}
.chart-box h3 {{ font-size:15px; color:#8b949e; margin-bottom:16px; text-align:center; }}
.chart-box canvas {{ max-height:320px; }}

.section {{ background:#161b22; border:1px solid #30363d; border-radius:12px; padding:20px; margin-bottom:24px; }}
.section h2 {{ font-size:18px; color:#58a6ff; margin-bottom:16px; }}

.tree {{ list-style:none; }}
.tree li {{ position:relative; margin:4px 0 4px 24px; }}
.tree li::before {{ content:""; position:absolute; top:10px; left:-18px; width:12px; height:1px; background:#30363d; }}
.tree li::after {{ content:""; position:absolute; top:-4px; left:-18px; width:1px; height:calc(100% + 4px); background:#30363d; }}
.tree li:last-child::after {{ display:none; }}
.tree-func > .tree-label code {{ color:#3fb950; background:#0d2818; padding:2px 6px; border-radius:4px; font-size:13px; }}
.tree-folder > .tree-label, .tree-func > .tree-label {{ font-size:14px; }}
.tree-folder > .tree-label small {{ color:#8b949e; }}
.tree-toggle {{ cursor:pointer; margin-right:6px; user-select:none; }}
.tree .tree li {{ display:none; }}
.tree .tree.open > li {{ display:block; }}

.search-bar {{ margin-bottom:16px; display:flex; gap:12px; }}
.search-bar input {{ flex:1; background:#0d1117; border:1px solid #30363d; border-radius:8px; padding:10px 16px; color:#c9d1d9; font-size:14px; }}
.search-bar input:focus {{ outline:none; border-color:#58a6ff; }}

table {{ width:100%; border-collapse:collapse; }}
th {{ text-align:left; padding:10px 12px; border-bottom:2px solid #30363d; font-size:13px; color:#8b949e; cursor:pointer; user-select:none; }}
td {{ padding:8px 12px; border-bottom:1px solid #21262d; font-size:13px; }}
tr:hover {{ background:#1c2129; }}
.priv-yes {{ color:#3fb950; font-weight:600; }}
.priv-no {{ color:#8b949e; }}

.browse-cell {{ white-space:nowrap; }}
.browse-cell span {{ display:inline-block; width:20px; height:20px; line-height:20px; text-align:center; border-radius:4px; margin:1px; font-size:10px; font-weight:600; }}
.bp-off {{ background:#161b22; color:#30363d; }}
.bp-avail {{ background:#1d2d1d; color:#56d364; }}
.bp-granted {{ background:#0d2818; color:#3fb950; }}
.bp-blocked {{ background:#2d1d1d; color:#ff7b72; }}

.status-ok {{ background:#0d2818; color:#3fb950; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600; }}
.status-blocked {{ background:#2d1d1d; color:#ff7b72; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600; }}
.row-disabled {{ opacity:0.5; }}
.row-disabled:hover {{ opacity:0.7; background:#1c2129; }}

.footer {{ text-align:center; color:#484f58; font-size:12px; margin-top:32px; }}
</style>
</head>
<body>

<header>
  <h1>polprevTOTVS</h1>
  <p>Dashboard de Acessos &mdash; Usuario <strong>{user}</strong> (ID: {user_id})</p>
</header>

<div class="kpi-grid">
  <div class="kpi-card c1"><div class="kpi-value">{total_menus}</div><div class="kpi-label">Menus Acessiveis</div></div>
  <div class="kpi-card c2"><div class="kpi-value">{total_routines}</div><div class="kpi-label">Rotinas Mapeadas</div></div>
  <div class="kpi-card c3"><div class="kpi-value">{saldo}</div><div class="kpi-label">Rotinas Permitidas</div></div>
  <div class="kpi-card c4"><div class="kpi-value">{groups_count}</div><div class="kpi-label">Grupos</div></div>
  <div class="kpi-card c5"><div class="kpi-value">{acbrowse_disabled_count}</div><div class="kpi-label">Bloqueadas (Perfil)</div></div>
</div>

<div class="charts-grid">
  <div class="chart-box">
    <h3>Top Prefixos de Funcoes</h3>
    <canvas id="barChart"></canvas>
  </div>
  <div class="chart-box">
    <h3>Acessiveis vs Bloqueadas</h3>
    <canvas id="pieChart"></canvas>
  </div>
</div>

<div class="section">
  <h2>Arvore de Menu</h2>
  <ul class="tree open">{tree_html}  </ul>
</div>

<div class="section">
  <h2>Tabela de Rotinas ({total_routines})</h2>
  <div class="search-bar">
    <input type="text" id="tableFilter" placeholder="Buscar por rotina, descricao ou menu..." oninput="filterTable()">
  </div>
  <table id="routinesTable">
    <thead>
      <tr>
        <th onclick="sortTable(0)">Rotina &#9650;</th>
        <th onclick="sortTable(1)">Descricao</th>
        <th onclick="sortTable(2)">Menu</th>
        <th onclick="sortTable(3)">Status</th>
        <th onclick="sortTable(4)">Privilegio</th>
        <th onclick="sortTable(5)">Browse OPs</th>
      </tr>
    </thead>
    <tbody>
{table_rows}    </tbody>
  </table>
</div>

<div class="footer">
  polprevTOTVS &mdash; Gerado automaticamente<br>
  Rotinas com privilegio explicito: {pr_yes} | Sem privilegio: {pr_no} | Com Browse: {browse_routines_count} | Bloqueadas (ACBROWSE): {acbrowse_disabled_count}
</div>

<script>
new Chart(document.getElementById('barChart'), {{
  type: 'bar',
  data: {{
    labels: {json.dumps([p[0] for p in top_prefixes])},
    datasets: [{{
      label: 'Quantidade',
      data: {json.dumps([p[1] for p in top_prefixes])},
      backgroundColor: ['#58a6ff','#3fb950','#d2991d','#f78166','#bc8cff','#56d4dd','#ff7b72','#79c0ff','#a5d6ff','#ffa198','#d2a8ff','#ffc966','#e3b341','#8b949e','#6e7681'],
      borderRadius: 6,
    }}]
  }},
  options: {{
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ grid: {{ color: '#21262d' }}, ticks: {{ color: '#8b949e' }} }},
      y: {{ grid: {{ display: false }}, ticks: {{ color: '#8b949e' }} }}
    }}
  }}
}});

new Chart(document.getElementById('pieChart'), {{
  type: 'doughnut',
  data: {{
    labels: ['Acessiveis', 'Bloqueadas (Perfil)'],
    datasets: [{{
      data: [{saldo}, {acbrowse_disabled_count}],
      backgroundColor: ['#3fb950', '#f78166'],
      borderColor: '#161b22',
      borderWidth: 3,
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{
      legend: {{ position: 'bottom', labels: {{ color: '#8b949e' }} }}
    }}
  }}
}});

document.querySelectorAll('.tree-toggle').forEach(el => {{
  el.addEventListener('click', () => {{
    const li = el.parentElement;
    const ul = li.querySelector('ul');
    if (ul) {{
      ul.classList.toggle('open');
      el.textContent = ul.classList.contains('open') ? '▼' : '▶';
    }}
  }});
}});

document.querySelectorAll('.tree ul').forEach(ul => {{
  const parentLi = ul.parentElement;
  if (!ul.classList.contains('open')) {{
    ul.classList.add('open');
    const toggle = parentLi.querySelector('.tree-toggle');
    if (toggle && toggle.textContent !== '▼') toggle.textContent = '▼';
  }}
}});

function filterTable() {{
  const q = document.getElementById('tableFilter').value.toLowerCase();
  const rows = document.querySelectorAll('#routinesTable tbody tr');
  rows.forEach(row => {{
    const text = row.textContent.toLowerCase();
    row.style.display = text.includes(q) ? '' : 'none';
  }});
}}

function sortTable(col) {{
  const tbody = document.querySelector('#routinesTable tbody');
  const rows = Array.from(tbody.rows);
  const asc = !tbody.dataset.sortAsc || tbody.dataset.sortCol != col;
  rows.sort((a, b) => {{
    const va = a.cells[col].textContent.trim();
    const vb = b.cells[col].textContent.trim();
    return asc ? va.localeCompare(vb) : vb.localeCompare(va);
  }});
  rows.forEach(r => tbody.appendChild(r));
  tbody.dataset.sortAsc = asc;
  tbody.dataset.sortCol = col;
}}
</script>

</body>
</html>'''

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, "dashboard.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path
