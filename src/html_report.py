import json
import os


def generate_cluster_html(tier1, tier2, tier3_clusters, unclustered, tier4, users_detail, user_routines_raw, user_dept, output_path, empresa_name=""):
    data = {
        "tier1": tier1,
        "tier2": tier2,
        "tier3": {
            "clusters": tier3_clusters,
            "unclustered": list(unclustered) if unclustered else [],
        },
        "tier4": tier4,
        "users_detail": users_detail,
        "user_routines_raw": user_routines_raw,
        "user_dept": user_dept,
    }

    data_json = json.dumps(data, indent=2, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Camadas Organizacionais - {empresa_name or 'LLM'}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #1a1a2e; color: #e0e0e0; height: 100vh; display: flex; flex-direction: column; }}

.header {{ background: #16213e; padding: 12px 24px; display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #0f3460; box-shadow: 0 2px 8px rgba(0,0,0,0.3); }}
.header h1 {{ font-size: 16px; color: #e94560; }}
.header .info {{ font-size: 11px; color: #8899aa; }}
.btn {{ background: #0f3460; color: #e0e0e0; border: 1px solid #1a5276; padding: 8px 18px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600; transition: all 0.2s; }}
.btn:hover {{ background: #1a5276; border-color: #2980b9; }}
.btn.save {{ background: #27ae60; border-color: #2ecc71; color: #fff; }}
.btn.save:hover {{ background: #2ecc71; }}

.tabs {{ display: flex; background: #16213e; border-bottom: 2px solid #0f3460; padding: 0 16px; gap: 0; }}
.tab {{ padding: 10px 20px; cursor: pointer; font-size: 13px; font-weight: 600; color: #7f8c8d; border-bottom: 3px solid transparent; transition: all 0.2s; white-space: nowrap; }}
.tab:hover {{ color: #e0e0e0; }}
.tab.active {{ color: #e94560; border-bottom-color: #e94560; }}
.tab .badge {{ background: #0f3460; padding: 1px 8px; border-radius: 10px; font-size: 10px; margin-left: 4px; }}
.tab.active .badge {{ background: #e94560; color: #fff; }}

.main {{ flex: 1; overflow: hidden; display: flex; flex-direction: column; }}

.tab-content {{ display: none; flex: 1; overflow-y: auto; padding: 16px 24px; }}
.tab-content.active {{ display: flex; flex-direction: column; }}

/* Tier 1 */
.tier1-card {{ background: #16213e; border: 1px solid #0f3460; border-radius: 10px; padding: 20px; margin-bottom: 12px; }}
.tier1-card h3 {{ color: #27ae60; font-size: 15px; margin-bottom: 8px; }}
.tier1-routines {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 4px; }}
.tier1-routine {{ background: #1a1a2e; border: 1px solid #2c3e50; border-radius: 4px; padding: 6px 10px; font-size: 12px; font-family: monospace; color: #e0e0e0; }}

/* Tier 2 */
.depto-card {{ background: #16213e; border: 1px solid #0f3460; border-radius: 10px; padding: 16px; margin-bottom: 10px; }}
.depto-header {{ display: flex; align-items: center; justify-content: space-between; cursor: pointer; }}
.depto-header h4 {{ color: #3498db; font-size: 14px; }}
.depto-stats {{ font-size: 11px; color: #7f8c8d; }}
.depto-body {{ display: none; margin-top: 12px; }}
.depto-body.open {{ display: block; }}
.depto-body .routines-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 4px; }}
.depto-body .user-tag {{ display: inline-block; background: #0f3460; color: #7fb3d3; padding: 2px 8px; border-radius: 10px; font-size: 10px; margin: 2px; }}

/* Tier 3 */
.tier3-layout {{ display: flex; flex: 1; gap: 16px; overflow: hidden; }}
.tier3-sidebar {{ width: 260px; min-width: 220px; background: #16213e; border: 1px solid #0f3460; border-radius: 10px; display: flex; flex-direction: column; }}
.tier3-sidebar-header {{ padding: 10px 14px; border-bottom: 1px solid #0f3460; }}
.tier3-sidebar-header input {{ width: 100%; padding: 8px 10px; border-radius: 6px; border: 1px solid #1a5276; background: #1a1a2e; color: #e0e0e0; font-size: 12px; outline: none; }}
.tier3-sidebar-header input:focus {{ border-color: #2980b9; }}
.tier3-sidebar-count {{ font-size: 10px; color: #7f8c8d; margin-top: 4px; }}
.unassigned-pool {{ flex: 1; overflow-y: auto; padding: 8px; }}
.unassigned-pool.drag-over {{ background: rgba(233, 69, 96, 0.08); }}

.tier3-clusters {{ flex: 1; overflow-x: auto; overflow-y: auto; display: flex; gap: 12px; align-items: flex-start; padding: 0 4px; }}

.cluster-column {{ min-width: 240px; max-width: 320px; background: #16213e; border-radius: 10px; border: 2px solid #0f3460; display: flex; flex-direction: column; box-shadow: 0 4px 12px rgba(0,0,0,0.2); }}
.cluster-column.drag-over {{ border-color: #e94560; background: rgba(233, 69, 96, 0.06); }}

.cluster-header {{ padding: 10px 14px; border-bottom: 1px solid #0f3460; }}
.cluster-name {{ font-size: 14px; font-weight: 700; color: #e94560; padding: 3px 6px; border-radius: 4px; margin: -3px -6px; cursor: default; }}
.cluster-name:hover {{ background: rgba(233, 69, 96, 0.1); }}
.cluster-reason {{ font-size: 10px; color: #7f8c8d; margin-top: 3px; font-style: italic; }}
.cluster-count {{ font-size: 10px; color: #7f8c8d; margin-top: 2px; }}

.cluster-common {{ padding: 6px 14px; border-bottom: 1px solid #0f3460; max-height: 120px; overflow-y: auto; }}
.cluster-common-title {{ font-size: 9px; color: #7f8c8d; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 3px; }}
.tag {{ background: #0f3460; color: #7fb3d3; padding: 1px 6px; border-radius: 8px; font-size: 10px; font-family: monospace; display: inline-block; margin: 1px; }}

.cluster-body {{ flex: 1; overflow-y: auto; padding: 6px; }}
.cluster-body.drag-over {{ background: rgba(233, 69, 96, 0.08); }}

.user-card {{ background: #1a1a2e; border: 1px solid #2c3e50; border-radius: 8px; padding: 8px 10px; margin-bottom: 4px; cursor: grab; transition: all 0.15s; user-select: none; }}
.user-card:hover {{ border-color: #2980b9; box-shadow: 0 2px 8px rgba(41, 128, 185, 0.2); }}
.user-card:active {{ cursor: grabbing; }}
.user-card.dragging {{ opacity: 0.4; border-style: dashed; }}

.user-card .user-name {{ font-size: 12px; font-weight: 600; color: #ecf0f1; }}
.user-card .user-login {{ font-size: 10px; color: #7f8c8d; font-family: monospace; }}
.user-card .user-depto {{ font-size: 9px; color: #f39c12; }}
.user-card .user-meta {{ display: flex; justify-content: space-between; align-items: center; margin-top: 3px; }}
.user-card .user-routine-count {{ font-size: 9px; color: #3498db; }}

.empty-hint {{ color: #4a5a6a; font-size: 11px; text-align: center; padding: 16px; font-style: italic; }}

/* Tier 4 */
.tier4-stats {{ font-size: 12px; color: #7f8c8d; margin-bottom: 12px; }}
.tier4-table {{ width: 100%; border-collapse: collapse; }}
.tier4-table th {{ text-align: left; padding: 8px 12px; font-size: 11px; color: #7f8c8d; text-transform: uppercase; border-bottom: 2px solid #0f3460; background: #16213e; position: sticky; top: 0; }}
.tier4-table td {{ padding: 8px 12px; font-size: 12px; border-bottom: 1px solid #1c2833; }}
.tier4-table tr:hover {{ background: rgba(41, 128, 185, 0.05); }}
.tier4-user-name {{ color: #ecf0f1; font-weight: 600; }}
.tier4-user-depto {{ color: #f39c12; font-size: 10px; }}
.tier4-routines {{ font-family: monospace; font-size: 11px; color: #95a5a6; }}
.tier4-count {{ color: #3498db; font-size: 11px; }}
.tier4-zero {{ color: #27ae60; font-size: 11px; }}

.toast {{ position: fixed; bottom: 24px; right: 24px; background: #27ae60; color: #fff; padding: 12px 24px; border-radius: 8px; font-size: 13px; font-weight: 600; opacity: 0; transform: translateY(20px); transition: all 0.3s; pointer-events: none; z-index: 1000; }}
.toast.show {{ opacity: 1; transform: translateY(0); }}

@media (max-width: 900px) {{
    .tier3-layout {{ flex-direction: column; }}
    .tier3-sidebar {{ width: 100%; max-height: 30vh; }}
}}

::-webkit-scrollbar {{ width: 6px; height: 6px; }}
::-webkit-scrollbar-track {{ background: #1a1a2e; }}
::-webkit-scrollbar-thumb {{ background: #2c3e50; border-radius: 3px; }}
</style>
</head>
<body>

<div class="header">
    <div>
        <h1>CAMADAS ORGANIZACIONAIS - {empresa_name or 'BOSAL'}</h1>
        <div class="info" id="header-info">Carregando...</div>
    </div>
    <div style="display: flex; gap: 8px;">
        <button class="btn" onclick="resetAll()">Recarregar LLM</button>
        <button class="btn save" onclick="saveAll()">Salvar JSON</button>
    </div>
</div>

<div class="tabs">
    <div class="tab active" data-tab="tier1" onclick="switchTab('tier1')">TIER 1<span class="badge" id="badge-tier1">Geral</span></div>
    <div class="tab" data-tab="tier2" onclick="switchTab('tier2')">TIER 2<span class="badge" id="badge-tier2">Deptos</span></div>
    <div class="tab" data-tab="tier3" onclick="switchTab('tier3')">TIER 3<span class="badge" id="badge-tier3">Perfis/CJ</span></div>
    <div class="tab" data-tab="tier4" onclick="switchTab('tier4')">TIER 4<span class="badge" id="badge-tier4">Usuarios</span></div>
</div>

<div class="main">
    <div class="tab-content active" id="tab-tier1">
        <div id="tier1-content"></div>
    </div>
    <div class="tab-content" id="tab-tier2">
        <div id="tier2-content"></div>
    </div>
    <div class="tab-content" id="tab-tier3">
        <div class="tier3-layout">
            <div class="tier3-sidebar">
                <div class="tier3-sidebar-header">
                    <input type="text" id="search-input" placeholder="Buscar rotina..." oninput="filterRoutines()">
                    <div class="tier3-sidebar-count" id="sidebar-count"></div>
                </div>
                <div class="unassigned-pool" id="unassigned-pool"
                    ondragover="handleDragOver(event)"
                    ondragleave="handleDragLeave(event)"
                    ondrop="handleDropUnassigned(event)"></div>
            </div>
            <div class="tier3-clusters" id="clusters-area"></div>
        </div>
    </div>
    <div class="tab-content" id="tab-tier4">
        <div id="tier4-content"></div>
    </div>
</div>

<div class="toast" id="toast"></div>

<script id="cluster-data" type="application/json">{data_json}</script>

<script>
const DATA = JSON.parse(document.getElementById('cluster-data').textContent);

const TIER1_ROUTINES = DATA.tier1.routines.map(r => r.code);
const TIER2_DATA = DATA.tier2;
const TIER3_ORIG = JSON.parse(JSON.stringify(DATA.tier3));
let tier3Clusters = DATA.tier3.clusters.map(c => ({{
    name: c.name,
    reason: c.reason || '',
    type: c.type || '',
    routines: [...(c.routines || c.common_routines || [])],
    users: [...(c.users || [])],
}}));
let tier3Unassigned = [...DATA.tier3.unclustered];
const USERS_DETAIL = DATA.users_detail;
const USER_ROUTINES = DATA.user_routines_raw;
const USER_DEPT = DATA.user_dept;
const ALL_ROUTINES = uniqueRoutineItems(Object.values(USER_ROUTINES).flat())
    .sort((a, b) => routineLabel(a).localeCompare(routineLabel(b)));
const MIN_ROUTINE_SEARCH = 2;
const MAX_ROUTINE_RESULTS = 100;
const ROUTINE_USER_COUNT = buildRoutineUserCount();

let dragging = null;
let activeTab = 'tier1';
let routineSearchTimer = null;

function switchTab(tabId) {{
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.querySelector('.tab[data-tab="' + tabId + '"]').classList.add('active');
    document.getElementById('tab-' + tabId).classList.add('active');
    activeTab = tabId;
    if (tabId === 'tier3') renderTier3();
    if (tabId === 'tier4') renderTier4();
    updateBadges();
}}

function updateBadges() {{
    document.getElementById('badge-tier1').textContent = TIER1_ROUTINES.length + ' rotinas';
    document.getElementById('badge-tier2').textContent = TIER2_DATA.length + ' deptos';
    document.getElementById('badge-tier3').textContent = tier3Clusters.length + ' conjuntos';
    document.getElementById('badge-tier4').textContent = 'Usuarios';
    document.getElementById('header-info').textContent =
        Object.keys(USERS_DETAIL).length + ' usuarios | ' + tier3Clusters.length + ' perfis/conjuntos (Tier 3)';
}}

function init() {{
    updateBadges();
    renderTier1();
    renderTier2();
    renderTier3();
    renderTier4();
}}

// ---- TIER 1 ----
function renderTier1() {{
    const el = document.getElementById('tier1-content');
    const routines = DATA.tier1.routines;
    if (routines.length === 0) {{
        el.innerHTML = '<div class="empty-hint">Nenhuma rotina comum a todos os usuarios</div>';
        return;
    }}
    let html = '<div class="tier1-card">';
    html += '<h3>' + routines.length + ' rotinas comuns a TODOS os ' + DATA.tier1.total_users + ' usuarios</h3>';
    html += '<div style="font-size:11px;color:#7f8c8d;margin:4px 0 10px 0;">';
    html += 'Estas rotinas serao concedidas no nivel GERAL da empresa (P_' + escapeHtml(DATA.tier1.empresa || 'EMPRESA') + ')</div>';
    html += '<div class="tier1-routines">';
    routines.forEach(r => {{
        html += '<div class="tier1-routine"><span style="color:#27ae60">' + escapeHtml(r.code) + '</span> - ' + escapeHtml(r.desc || '') + '</div>';
    }});
    html += '</div></div>';
    el.innerHTML = html;
}}

// ---- TIER 2 ----
function renderTier2() {{
    const el = document.getElementById('tier2-content');
    if (TIER2_DATA.length === 0) {{
        el.innerHTML = '<div class="empty-hint">Nenhum departamento com rotinas comuns</div>';
        return;
    }}
    let html = '';
    TIER2_DATA.forEach((dept, idx) => {{
        html += '<div class="depto-card">';
        html += '<div class="depto-header" onclick="toggleDepto(' + idx + ')">';
        html += '<h4>' + escapeHtml(dept.depto || 'SEM DEPTO') + '</h4>';
        html += '<div class="depto-stats">' + dept.routines.length + ' rotinas comuns | ' + dept.users.length + ' usuarios</div>';
        html += '</div>';
        html += '<div class="depto-body" id="depto-body-' + idx + '">';
        html += '<div style="margin-bottom:8px;">';
        dept.users.forEach(u => {{
            html += '<span class="user-tag">' + escapeHtml(u) + '</span>';
        }});
        html += '</div>';
        html += '<div class="routines-grid">';
        dept.routines.forEach(r => {{
            html += '<div class="tier1-routine"><span style="color:#3498db">' + escapeHtml(r.code) + '</span> - ' + escapeHtml(r.desc || '') + '</div>';
        }});
        html += '</div>';
        html += '</div></div>';
    }});
    el.innerHTML = html;
}}

function toggleDepto(idx) {{
    const body = document.getElementById('depto-body-' + idx);
    if (body) body.classList.toggle('open');
}}

// ---- TIER 3 (conjuntos funcionais por rotina) ----
function renderTier3() {{
    if (activeTab !== 'tier3') return;
    renderClusters();
    renderRoutinePool();
}}

function renderClusters() {{
    const container = document.getElementById('clusters-area');
    container.innerHTML = '';
    tier3Clusters = tier3Clusters.filter(cluster => {{
        cluster.users = deriveClusterUsers(cluster);
        return cluster.users.length > 0;
    }});
    tier3Clusters.forEach((cluster, idx) => {{
        const column = document.createElement('div');
        column.className = 'cluster-column';
        column.setAttribute('data-cluster-idx', idx);
        column.addEventListener('dragover', handleDragOver);
        column.addEventListener('dragleave', handleDragLeave);
        column.addEventListener('drop', (e) => handleDropCluster(e, idx));

        let reasonHtml = '';
        if (cluster.reason) {{
            let shortReason = cluster.reason.length > 120 ? cluster.reason.substring(0, 117) + '...' : cluster.reason;
            reasonHtml = '<div class="cluster-reason" title="' + escapeHtml(cluster.reason) + '">' + escapeHtml(shortReason) + '</div>';
        }}

        let commonTags = '';
        let routines = (cluster.routines || []).filter(r => r && routineCode(r));
        if (routines.length > 0) {{
            let shown = routines.slice(0, 40);
            commonTags = '<div class="cluster-common">'
                + '<div class="cluster-common-title">Rotinas (' + routines.length + ')</div>'
                + '<div>' + shown.map((r, rIdx) => '<span class="tag" title="Clique para remover" data-routine-idx="' + rIdx + '" onclick="removeRoutineFromElement(' + idx + ', this)">' + escapeHtml(routineLabel(r)) + ' x</span>').join('') + '</div>'
                + '</div>';
        }}

        column.innerHTML =
            '<div class="cluster-header">'
            + '<div class="cluster-name" id="cluster-name-' + idx + '" ondblclick="editClusterName(' + idx + ')" title="Duplo clique para renomear">' + escapeHtml(cluster.name) + '</div>'
            + reasonHtml
            + '<div class="cluster-count">' + cluster.users.length + ' usuarios aderentes</div>'
            + '</div>'
            + commonTags
            + '<div class="cluster-body" id="cluster-body-' + idx + '">' + renderUserCards(cluster.users) + '</div>';
        container.appendChild(column);
    }});
}}

function deriveClusterUsers(cluster) {{
    const requiredItems = cluster.routines || [];
    if (requiredItems.length === 0) return [];
    return Object.keys(USER_ROUTINES).filter(login => {{
        const userItems = USER_ROUTINES[login] || [];
        return requiredItems.every(required => userItems.some(userItem => userCoversRoutineItem(userItem, required)));
    }}).sort();
}}

function routineCode(item) {{
    if (item && typeof item === 'object') return String(item.code || item.routine || '').trim();
    return String(item || '').split(' - ')[0].trim();
}}

function routinePermissions(item) {{
    if (item && typeof item === 'object' && Array.isArray(item.permissions)) {{
        return item.permissions.map(p => String(p || '').trim()).filter(Boolean).sort();
    }}
    return [];
}}

function routineSignature(item) {{
    return routineCode(item) + '|' + routinePermissions(item).join('|');
}}

function uniqueRoutineItems(items) {{
    const bySignature = new Map();
    (items || []).forEach(item => {{
        const code = routineCode(item);
        if (!code) return;
        const signature = routineSignature(item);
        if (!bySignature.has(signature)) bySignature.set(signature, item);
    }});
    return Array.from(bySignature.values());
}}

function buildRoutineUserCount() {{
    const counts = new Map();
    Object.values(USER_ROUTINES).forEach(list => {{
        const seen = new Set();
        (list || []).forEach(item => {{
            const signature = routineSignature(item);
            if (signature && !seen.has(signature)) seen.add(signature);
        }});
        seen.forEach(signature => counts.set(signature, (counts.get(signature) || 0) + 1));
    }});
    return counts;
}}

function routineLabel(item) {{
    if (item && typeof item === 'object') {{
        const permissions = routinePermissions(item);
        const perms = permissions.length ? ' [' + permissions.join(', ') + ']' : '';
        return routineCode(item) + perms;
    }}
    return routineCode(item);
}}

function sameRoutineItem(a, b) {{
    return routineSignature(a) === routineSignature(b);
}}

function userCoversRoutineItem(userItem, requiredItem) {{
    if (routineCode(userItem) !== routineCode(requiredItem)) return false;
    const required = routinePermissions(requiredItem);
    if (required.length === 0) return true;
    const userPermissions = routinePermissions(userItem);
    if (userPermissions.length === 0 && !(userItem && typeof userItem === 'object')) return true;
    return required.every(permission => userPermissions.includes(permission));
}}

function remainingPermissions(userItem, coveredPermissions) {{
    const userPermissions = routinePermissions(userItem);
    return userPermissions.filter(permission => !coveredPermissions.includes(permission));
}}

function parseRoutinePayload(value) {{
    try {{
        return JSON.parse(value);
    }} catch (e) {{
        return value;
    }}
}}

function renderUserCards(userLogins) {{
    if (!userLogins || userLogins.length === 0) return '<div class="empty-hint">Arraste rotinas para este conjunto</div>';
    return userLogins.map(login => {{
        const detail = USERS_DETAIL[login] || {{}};
        const name = detail.name || login;
        const depto = detail.depto || '';
        const totalRoutines = detail.total_routines || 0;
        let deptoHtml = depto ? '<div class="user-depto">' + escapeHtml(depto) + '</div>' : '';
        return (
            '<div class="user-card" data-user="' + escapeAttr(login) + '">'
            + '<div class="user-name">' + escapeHtml(name) + '</div>'
            + '<div class="user-login">' + escapeHtml(login) + '</div>'
            + deptoHtml
            + '<div class="user-meta"><div class="user-routine-count">' + totalRoutines + ' rotinas</div></div>'
            + '</div>'
        );
    }}).join('');
}}

function renderRoutinePool() {{
    const pool = document.getElementById('unassigned-pool');
    const search = (document.getElementById('search-input').value || '').toLowerCase();
    if (search.length < MIN_ROUTINE_SEARCH) {{
        document.getElementById('sidebar-count').textContent = 'Rotinas: ' + ALL_ROUTINES.length;
        pool.innerHTML = '<div class="empty-hint">Digite ao menos 2 caracteres para buscar rotinas</div>';
        return;
    }}
    let filtered = ALL_ROUTINES.filter(r => routineLabel(r).toLowerCase().includes(search));
    let shown = filtered.slice(0, MAX_ROUTINE_RESULTS);
    document.getElementById('sidebar-count').textContent = 'Rotinas: ' + ALL_ROUTINES.length
        + ' | encontradas: ' + filtered.length
        + (filtered.length > MAX_ROUTINE_RESULTS ? ' | exibindo primeiras ' + MAX_ROUTINE_RESULTS : ' | exibindo ' + filtered.length);
    if (filtered.length === 0) {{
        pool.innerHTML = '<div class="empty-hint">Nenhum encontrado</div>';
    }} else {{
        pool.innerHTML = shown.map(routine => {{
            const userCount = ROUTINE_USER_COUNT.get(routineSignature(routine)) || 0;
            const payload = JSON.stringify(routine);
            return (
                '<div class="user-card" draggable="true" data-routine="' + escapeAttr(payload) + '"'
                + ' ondragstart="handleDragStart(event)" ondragend="handleDragEnd(event)">'
                + '<div class="user-name">' + escapeHtml(routineLabel(routine)) + '</div>'
                + '<div class="user-meta"><div class="user-routine-count">' + userCount + ' usuarios</div></div>'
                + '</div>'
            );
        }}).join('');
    }}
}}

function filterRoutines() {{
    clearTimeout(routineSearchTimer);
    routineSearchTimer = setTimeout(renderRoutinePool, 150);
}}

function handleDragStart(e) {{
    dragging = e.target.closest('.user-card');
    if (!dragging) return;
    dragging.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', dragging.getAttribute('data-routine'));
}}

function handleDragEnd(e) {{
    if (dragging) dragging.classList.remove('dragging');
    dragging = null;
    document.querySelectorAll('.drag-over').forEach(el => el.classList.remove('drag-over'));
}}

function handleDragOver(e) {{
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    let container = e.currentTarget;
    if (container.classList.contains('cluster-column')) {{
        container.querySelector('.cluster-body').classList.add('drag-over');
    }} else {{
        container.classList.add('drag-over');
    }}
}}

function handleDragLeave(e) {{
    let container = e.currentTarget;
    container.classList.remove('drag-over');
    if (container.classList.contains('cluster-column')) {{
        let body = container.querySelector('.cluster-body');
        if (body) body.classList.remove('drag-over');
    }}
}}

function handleDropCluster(e, idx) {{
    e.preventDefault();
    e.currentTarget.classList.remove('drag-over');
    let body = e.currentTarget.querySelector('.cluster-body');
    if (body) body.classList.remove('drag-over');
    let routine = parseRoutinePayload(e.dataTransfer.getData('text/plain'));
    if (!routine) return;
    addRoutineToCluster(routine, idx);
}}

function handleDropUnassigned(e) {{
    e.preventDefault();
    e.currentTarget.classList.remove('drag-over');
    return;
}}

function addRoutineToCluster(routine, targetClusterIdx) {{
    if (targetClusterIdx === null || targetClusterIdx === undefined) return;
    const cluster = tier3Clusters[targetClusterIdx];
    if (!cluster.routines.some(r => sameRoutineItem(r, routine))) {{
        cluster.routines.push(routine);
        cluster.routines.sort((a, b) => routineLabel(a).localeCompare(routineLabel(b)));
    }}
    renderTier3();
    renderTier4();
    updateBadges();
}}

function removeRoutineFromCluster(idx, routine) {{
    tier3Clusters[idx].routines = tier3Clusters[idx].routines.filter(r => !sameRoutineItem(r, routine));
    renderTier3();
    renderTier4();
    updateBadges();
}}

function removeRoutineFromElement(idx, el) {{
    const routineIdx = parseInt(el.getAttribute('data-routine-idx'), 10);
    const routine = (tier3Clusters[idx].routines || [])[routineIdx];
    removeRoutineFromCluster(idx, routine);
}}

function editClusterName(idx) {{
    const nameEl = document.getElementById('cluster-name-' + idx);
    const currentName = tier3Clusters[idx].name;
    const input = document.createElement('input');
    input.type = 'text';
    input.value = currentName;
    input.style.cssText = 'width:100%;background:#1a1a2e;color:#e94560;border:1px solid #e94560;border-radius:4px;padding:4px 8px;font-size:14px;font-weight:700;';
    input.addEventListener('blur', () => saveClusterName(idx, input));
    input.addEventListener('keydown', (e) => {{
        if (e.key === 'Enter') saveClusterName(idx, input);
        if (e.key === 'Escape') renderTier3();
    }});
    nameEl.innerHTML = '';
    nameEl.appendChild(input);
    input.focus();
    input.select();
}}

function saveClusterName(idx, input) {{
    let val = input.value.trim().toUpperCase();
    if (val) {{
        if (!val.startsWith('P_CJ_')) val = 'P_CJ_' + val;
        if (val.length > 20) val = val.substring(0, 20);
        tier3Clusters[idx].name = val;
    }}
    renderTier3();
}}

// ---- TIER 4 ----
function computeTier4() {{
    let tier2Map = {{}};
    TIER2_DATA.forEach(d => {{ tier2Map[d.depto] = d.routines.map(r => r.code); }});

    let tier3Map = {{}};
    tier3Clusters.forEach(c => {{
        c.users = deriveClusterUsers(c);
        c.users.forEach(u => {{
            if (!tier3Map[u]) tier3Map[u] = [];
            tier3Map[u].push(...c.routines);
        }});
    }});

    let results = [];
    Object.keys(USER_ROUTINES).forEach(login => {{
        let userRoutines = USER_ROUTINES[login] || [];
        let dept = USER_DEPT[login] || '';
        let covered = new Set(TIER1_ROUTINES);
        (tier2Map[dept] || []).forEach(r => covered.add(r));
        let coveredPermissions = {{}};
        (tier3Map[login] || []).forEach(item => {{
            const code = routineCode(item);
            const permissions = routinePermissions(item);
            if (permissions.length === 0) {{
                covered.add(code);
            }} else {{
                if (!coveredPermissions[code]) coveredPermissions[code] = [];
                permissions.forEach(permission => {{
                    if (!coveredPermissions[code].includes(permission)) coveredPermissions[code].push(permission);
                }});
            }}
        }});
        let exclusive = [];
        userRoutines.forEach(item => {{
            const code = routineCode(item);
            if (covered.has(code)) return;
            const partial = coveredPermissions[code] || [];
            if (partial.length > 0) {{
                const remaining = remainingPermissions(item, partial);
                if (remaining.length > 0) {{
                    remaining.forEach(permission => exclusive.push(code + ': ' + permission));
                }}
                return;
            }}
            exclusive.push(routineLabel(item));
        }});
        let detail = USERS_DETAIL[login] || {{}};
        results.push({{
            login: login,
            name: detail.name || login,
            dept: dept,
            total: userRoutines.length,
            exclusive: exclusive,
            exclusiveCount: exclusive.length,
        }});
    }});
    results.sort((a, b) => b.exclusiveCount - a.exclusiveCount || a.name.localeCompare(b.name));
    return results;
}}

function renderTier4() {{
    const el = document.getElementById('tier4-content');
    const data = computeTier4();
    let html = '<div class="tier4-stats">Rotinas que NAO foram cobertas pelos Tiers 1, 2 e 3 (exclusivas do usuario)</div>';
    html += '<table class="tier4-table"><thead><tr><th>Usuario</th><th>Depto</th><th>Total Rotinas</th><th>Exclusivas</th><th>Rotinas</th></tr></thead><tbody>';
    data.forEach(row => {{
        html += '<tr>';
        html += '<td><div class="tier4-user-name">' + escapeHtml(row.name) + '</div><div style="font-size:10px;color:#7f8c8d">' + escapeHtml(row.login) + '</div></td>';
        html += '<td><span class="tier4-user-depto">' + escapeHtml(row.dept) + '</span></td>';
        html += '<td class="tier4-count">' + row.total + '</td>';
        if (row.exclusiveCount === 0) {{
            html += '<td class="tier4-zero">0 (100% coberto)</td><td></td>';
        }} else {{
            html += '<td class="tier4-count">' + row.exclusiveCount + '</td>';
            html += '<td class="tier4-routines">' + row.exclusive.map(r => '<span style="color:#e74c3c">' + escapeHtml(r) + '</span>').join(', ') + '</td>';
        }}
        html += '</tr>';
    }});
    html += '</tbody></table>';
    el.innerHTML = html;
    document.getElementById('badge-tier4').textContent = data.filter(r => r.exclusiveCount > 0).length + ' com exclusivas';
}}

// ---- RESET / SAVE ----
function resetAll() {{
    if (!confirm('Voltar aos conjuntos funcionais originais da LLM? Alteracoes serao perdidas.')) return;
    tier3Clusters = TIER3_ORIG.clusters.map(c => ({{
        name: c.name, reason: c.reason || '', type: c.type || '', routines: [...(c.routines || c.common_routines || [])], users: [...(c.users || [])],
    }}));
    tier3Unassigned = [...TIER3_ORIG.unclustered];
    renderTier3();
    renderTier4();
    updateBadges();
    showToast('Conjuntos restaurados');
}}

function saveAll() {{
    let tier4Users = computeTier4().map(row => ({{ login: row.login, exclusive: row.exclusive }}));

    let output = {{
        tier1: {{ routines: TIER1_ROUTINES, total_users: DATA.tier1.total_users }},
        tier2: TIER2_DATA.map(d => ({{ depto: d.depto, routines: d.routines.map(r => r.code), users: d.users }})),
        tier3: {{
            clusters: tier3Clusters.map(c => ({{ name: c.name, reason: c.reason, type: c.type || '', routines: c.routines, users: deriveClusterUsers(c) }})),
            unclustered: Object.keys(USER_ROUTINES).filter(login => !tier3Clusters.some(c => deriveClusterUsers(c).includes(login))),
        }},
        tier4: tier4Users,
    }};

    let blob = new Blob([JSON.stringify(output, null, 2)], {{ type: 'application/json' }});
    let url = URL.createObjectURL(blob);
    let a = document.createElement('a');
    a.href = url;
    a.download = 'clusters_adjusted.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast('JSON salvo com os 4 tiers!');
}}

function showToast(msg) {{
    let t = document.getElementById('toast');
    t.textContent = msg;
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 2500);
}}

function escapeHtml(str) {{
    let div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}}

function escapeAttr(str) {{
    return (str || '').replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}}

init();
</script>
</body>
</html>"""

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path
