import json
import os


def generate_department_html(department_analysis, output_path, empresa_name=""):
    data_json = json.dumps(department_analysis or {}, indent=2, ensure_ascii=False)
    title = f"CAMADAS POR DEPARTAMENTO - {empresa_name or 'EMPRESA'}"

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #1a1a2e; color: #e0e0e0; min-height: 100vh; }}
.header {{ background: #16213e; border-bottom: 2px solid #0f3460; padding: 16px 24px; }}
.header h1 {{ color: #e94560; font-size: 20px; margin-bottom: 6px; }}
.header .info {{ color: #8da2b5; font-size: 12px; }}
.toolbar {{ background: #111a33; border-bottom: 1px solid #0f3460; padding: 14px 24px; display: flex; align-items: center; gap: 12px; }}
label {{ color: #8da2b5; font-size: 12px; font-weight: 700; text-transform: uppercase; }}
select {{ background: #1a1a2e; color: #e0e0e0; border: 1px solid #1a5276; border-radius: 6px; padding: 8px 12px; min-width: 280px; }}
.content {{ padding: 20px 24px; }}
.summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 18px; }}
.card {{ background: #16213e; border: 1px solid #0f3460; border-radius: 10px; padding: 14px; }}
.kpi {{ color: #e94560; font-size: 24px; font-weight: 800; }}
.kpi-label {{ color: #8da2b5; font-size: 11px; margin-top: 4px; }}
.section-title {{ color: #7fb3d3; font-size: 15px; margin: 18px 0 10px; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 12px; }}
.profile {{ background: #16213e; border: 1px solid #0f3460; border-radius: 10px; overflow: hidden; }}
.profile-header {{ padding: 12px 14px; border-bottom: 1px solid #0f3460; }}
.profile-name {{ color: #e94560; font-weight: 800; font-size: 14px; }}
.profile-meta {{ color: #8da2b5; font-size: 11px; margin-top: 4px; }}
.tags {{ padding: 10px 14px; max-height: 160px; overflow-y: auto; }}
.tag {{ display: inline-block; background: #0f3460; color: #7fb3d3; border-radius: 8px; padding: 2px 7px; font-family: monospace; font-size: 10px; margin: 2px; }}
.users {{ padding: 10px 14px; border-top: 1px solid #0f3460; }}
.user {{ display: inline-block; background: #1a1a2e; border: 1px solid #2c3e50; color: #ecf0f1; border-radius: 10px; padding: 3px 8px; font-size: 11px; margin: 2px; }}
table {{ width: 100%; border-collapse: collapse; background: #16213e; border: 1px solid #0f3460; border-radius: 10px; overflow: hidden; }}
th, td {{ padding: 8px 10px; border-bottom: 1px solid #1c2833; font-size: 12px; text-align: left; vertical-align: top; }}
th {{ color: #8da2b5; text-transform: uppercase; font-size: 10px; background: #111a33; }}
.zero {{ color: #27ae60; font-weight: 700; }}
.exclusive {{ color: #e74c3c; font-family: monospace; font-size: 11px; }}
.reuse-badge {{ display: inline-block; background: #27ae60; color: #fff; border-radius: 4px; padding: 1px 6px; font-size: 9px; font-weight: 800; margin-left: 6px; }}
.new-badge {{ display: inline-block; background: #e67e22; color: #fff; border-radius: 4px; padding: 1px 6px; font-size: 9px; font-weight: 800; margin-left: 6px; }}
.empty {{ color: #4a5a6a; font-style: italic; padding: 12px; }}
</style>
</head>
<body>
<div class="header">
  <h1>{title}</h1>
  <div class="info" id="header-info">Carregando...</div>
</div>
<div class="toolbar">
  <label for="department-select">Departamento</label>
  <select id="department-select" onchange="renderDepartment()"></select>
</div>
<div class="content" id="content"></div>
<script id="department-data" type="application/json">{data_json}</script>
<script>
const DATA = JSON.parse(document.getElementById('department-data').textContent);
const departments = Object.keys(DATA).sort();

function init() {{
  const select = document.getElementById('department-select');
  select.innerHTML = departments.map(dept => '<option value="' + escapeAttr(dept) + '">' + escapeHtml(dept) + '</option>').join('');
  document.getElementById('header-info').textContent = departments.length + ' departamentos analisados';
  renderDepartment();
}}

function renderDepartment() {{
  const dept = document.getElementById('department-select').value;
  const data = DATA[dept];
  const content = document.getElementById('content');
  if (!data) {{
    content.innerHTML = '<div class="empty">Nenhum departamento selecionado</div>';
    return;
  }}
  const tier4Open = (data.tier4_users || []).filter(row => row.exclusive_count > 0).length;
  let html = '';
  html += '<div class="summary">'
    + kpi(data.total_users || 0, 'Usuarios')
    + kpi(data.total_routines || 0, 'Rotinas distintas')
    + kpi((data.profile_groups || []).length, 'Perfis equivalentes')
    + kpi(tier4Open, 'Usuarios com sobras')
    + '</div>';
  html += '<h2 class="section-title">Perfis Equivalentes</h2>';
  html += renderProfiles(data.profile_groups || []);
  html += '<h2 class="section-title">Tier 4 - Sobras Individuais</h2>';
  html += renderTier4(data.tier4_users || []);
  content.innerHTML = html;
}}

function kpi(value, label) {{
  return '<div class="card"><div class="kpi">' + value + '</div><div class="kpi-label">' + escapeHtml(label) + '</div></div>';
}}

function renderProfiles(groups) {{
  if (!groups.length) return '<div class="empty">Nenhum perfil equivalente encontrado neste departamento</div>';
  return '<div class="grid">' + groups.map(group => {{
    const routines = group.routines || [];
    const shown = routines.slice(0, 80);
    let ruleBadge = '';
    if (group.reuses_existing_rule) {{
      ruleBadge = '<span class="reuse-badge" title="Regra existente no SYS_RULES">Reaproveita ' + escapeHtml(group.reuses_existing_rule) + '</span>';
    }} else {{
      ruleBadge = '<span class="new-badge" title="Nova regra necessaria">Nova regra</span>';
    }}
    return '<div class="profile">'
      + '<div class="profile-header"><div class="profile-name">' + escapeHtml(group.name || '') + ruleBadge + '</div>'
      + '<div class="profile-meta">' + (group.users || []).length + ' usuarios | ' + routines.length + ' rotinas</div></div>'
      + '<div class="tags">' + shown.map(r => '<span class="tag">' + escapeHtml(routineLabel(r)) + '</span>').join('') + (routines.length > shown.length ? '<span class="tag">+' + (routines.length - shown.length) + '</span>' : '') + '</div>'
      + '<div class="users">' + (group.users || []).map(u => '<span class="user">' + escapeHtml(u) + '</span>').join('') + '</div>'
      + '</div>';
  }}).join('') + '</div>';
}}

function renderTier4(rows) {{
  if (!rows.length) return '<div class="empty">Nenhum usuario no departamento</div>';
  let html = '<table><thead><tr><th>Usuario</th><th>Total</th><th>Exclusivas</th><th>Rotinas</th></tr></thead><tbody>';
  rows.forEach(row => {{
    html += '<tr><td>' + escapeHtml(row.name || row.login || '') + '<div style="color:#8da2b5;font-size:10px">' + escapeHtml(row.login || '') + '</div></td>'
      + '<td>' + (row.total_routines || 0) + '</td>';
    if ((row.exclusive_count || 0) === 0) {{
      html += '<td class="zero">0</td><td></td>';
    }} else {{
      html += '<td>' + row.exclusive_count + '</td><td>' + (row.exclusive_routines || []).map(r => '<span class="exclusive">' + escapeHtml(r) + '</span>').join(', ') + '</td>';
    }}
    html += '</tr>';
  }});
  return html + '</tbody></table>';
}}

function routineCode(item) {{
  if (item && typeof item === 'object') return String(item.code || item.routine || '').trim();
  return String(item || '').split(' - ')[0].trim();
}}

function routineLabel(item) {{
  if (item && typeof item === 'object') {{
    const desc = item.desc ? ' - ' + item.desc : '';
    const perms = Array.isArray(item.permissions) && item.permissions.length ? ' [' + item.permissions.join(', ') + ']' : '';
    return routineCode(item) + desc + perms;
  }}
  return routineCode(item);
}}

function escapeHtml(str) {{
  const div = document.createElement('div');
  div.textContent = str == null ? '' : String(str);
  return div.innerHTML;
}}

function escapeAttr(str) {{
  return String(str || '').replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}}

init();
</script>
</body>
</html>"""

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path
