import json
import os


def _stylesheet():
    return """<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',system-ui,sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh}
.header{background:#1e293b;border-bottom:1px solid #334155;padding:12px 20px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px}
.header h1{font-size:16px;color:#38bdf8}
.header .info{font-size:10px;color:#94a3b8}
.btn{padding:6px 14px;border:none;border-radius:6px;font-size:11px;font-weight:600;cursor:pointer}
.btn-b{background:#1d4ed8;color:#fff}.btn-b:hover{background:#2563eb}
.btn-g{background:#166534;color:#fff}.btn-g:hover{background:#15803d}
.btn-r{background:#991b1b;color:#fff}.btn-s{background:#334155;color:#cbd5e1}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;padding:14px 20px}
.kpi{background:#1e293b;border:1px solid #334155;border-radius:8px;padding:14px;text-align:center}
.kpi .v{font-size:24px;font-weight:800}.kpi .l{font-size:10px;color:#94a3b8;margin-top:2px;text-transform:uppercase;letter-spacing:.5px}
.toolbar{padding:0 20px 10px;display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.toolbar select,.toolbar input{background:#1e293b;border:1px solid #334155;border-radius:5px;padding:6px 10px;color:#e2e8f0;font-size:11px}
.toolbar input:focus,.toolbar select:focus{outline:none;border-color:#38bdf8}
.spacer{flex:1}
.table-wrap{padding:0 20px 20px;overflow-x:auto}
table{width:100%;border-collapse:collapse;background:#1e293b;border-radius:8px;overflow:hidden}
th{text-align:left;padding:10px 12px;font-size:10px;color:#94a3b8;text-transform:uppercase;background:#0f172a;border-bottom:2px solid #334155;cursor:pointer;position:sticky;top:0;z-index:1}
td{padding:8px 12px;font-size:12px;border-bottom:1px solid #1e293b;vertical-align:top}
tbody tr:hover{background:#1e3a5f}tr.del td{opacity:.4;text-decoration:line-through}
.expand-row{display:none}.expand-row.open{display:table-row}
.expand-row td{background:#0f172a;padding:14px 20px}
.badge{display:inline-block;padding:2px 7px;border-radius:3px;font-size:9px;font-weight:700}
.bd-ok{background:#14532d;color:#22c55e}.bd-new{background:#7c2d12;color:#f97316}.bd-part{background:#713f12;color:#eab308}.bd-del{background:#450a0a;color:#ef4444}.bd-exc{background:#3b0764;color:#a855f7}
.rule-link{color:#38bdf8;cursor:pointer;font-weight:600}.rule-link:hover{text-decoration:underline}
.chip{display:inline-block;margin:2px 3px;padding:2px 7px;border-radius:10px;font-size:10px;background:#1e293b;border:1px solid #334155}
.ftag{display:inline-block;margin:1px;padding:2px 6px;border-radius:3px;font-size:9px;font-family:monospace}
.ft-ok{background:#14532d;color:#86efac}.ft-mis{background:#713f12;color:#fde047}.ft-exc{background:#3b0764;color:#c084fc}
.modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:100;align-items:center;justify-content:center}
.modal-overlay.show{display:flex}
.modal{background:#1e293b;border:2px solid #334155;border-radius:12px;width:680px;max-height:85vh;overflow:auto;padding:24px}
.modal h2{color:#38bdf8;margin-bottom:16px;font-size:16px}
.modal .row{display:flex;gap:10px;margin:6px 0;align-items:center}
.modal input,.modal select{background:#0f172a;border:1px solid #334155;border-radius:5px;padding:6px 10px;color:#e2e8f0;font-size:11px;flex:1}
.modal .sec{margin:14px 0;padding-top:10px;border-top:1px solid #334155}
.modal .sec h3{font-size:12px;color:#94a3b8;margin-bottom:6px;text-transform:uppercase}
.toast{position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:#22c55e;color:#fff;padding:8px 16px;border-radius:6px;font-size:11px;z-index:200;opacity:0;transition:.3s}.toast.show{opacity:1}
.fab{position:fixed;bottom:24px;right:24px;width:48px;height:48px;border-radius:50%;background:#1d4ed8;color:#fff;font-size:24px;border:none;cursor:pointer;box-shadow:0 4px 16px rgba(29,78,216,.4);z-index:50}
</style>"""


def generate_admin_html(consolidated_inventory, output_path, empresa_name="BOSAL"):
    rules = consolidated_inventory.get("rules", []) if consolidated_inventory else []
    data_json = json.dumps(rules, indent=2, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Admin Panel — Regras {empresa_name}</title>
{_stylesheet()}
</head>
<body>
<div class="header"><div><h1>Regras Organizacionais — {empresa_name}</h1><div class="info">Gerado automaticamente — {len(rules)} regras</div></div>
<div style="display:flex;gap:6px;flex-wrap:wrap">
<button class="btn btn-s" onclick="saveJSON()">💾 Salvar JSON</button>
<button class="btn btn-b" onclick="addRule()">+ Nova Regra</button>
<button class="btn btn-g" onclick="genSQL()">⚡ Gerar SQL</button>
<button class="btn btn-g" onclick="downloadSQL()">⬇ Download .sql</button>
</div></div>

<div class="kpis" id="kpis"></div>
<div class="toolbar">
<select id="fAction" onchange="render()"><option value="">Todas ações</option><option value="MANTER">MANTER</option><option value="CRIAR">CRIAR</option><option value="COMPLEMENTAR">COMPLEMENTAR</option></select>
<select id="fTier" onchange="render()"><option value="">Todos tiers</option></select>
<select id="fSource" onchange="render()"><option value="">EXISTENTE + NOVO</option><option value="EXISTENTE">EXISTENTE</option><option value="NOVO">NOVO</option></select>
<input type="text" id="fSearch" placeholder="Buscar regra ou rotina..." oninput="render()" style="width:200px">
<span class="spacer"></span><span style="font-size:10px;color:#94a3b8" id="selInfo"></span>
</div>

<div class="table-wrap"><table><thead><tr>
<th style="width:20px"><input type="checkbox" onchange="toggleAll(this)"></th>
<th onclick="sort('rule_name')">Regra ▾</th><th onclick="sort('tier')">Tier</th><th onclick="sort('action')">Ação</th>
<th>Usuários</th><th>Rotinas</th><th>Delta</th><th style="width:60px"></th>
</tr></thead><tbody id="tb"></tbody></table></div>

<button class="fab" onclick="addRule()" title="Nova regra">+</button>
<div id="toast" class="toast"></div>
<div class="modal-overlay" id="mo"><div class="modal" id="mc"></div></div>

<script id="rules-data" type="application/json">{data_json}</script>
<script>
let rules=JSON.parse(document.getElementById('rules-data').textContent).map(r=>({{...r,_marked_for_delete:r._marked_for_delete||false}}));
let selected=new Set(),sortCol='',sortAsc=true,sqlCache='';

function init(){{
  let tiers=[...new Set(rules.map(r=>r.tier))].sort();
  document.getElementById('fTier').innerHTML='<option value="">Todos tiers</option>'+tiers.map(t=>'<option value="'+t+'">'+t+'</option>').join('');
  refresh();
}}
function refresh(){{updateKPIs();render()}}
function updateKPIs(){{
  let t=rules.length,e=rules.filter(r=>r.source==='EXISTENTE'&&!r._marked_for_delete).length,n=rules.filter(r=>r.source==='NOVO'&&!r._marked_for_delete).length,m=rules.filter(r=>r.action==='MANTER'&&!r._marked_for_delete).length,c=rules.filter(r=>r.action==='COMPLEMENTAR'&&!r._marked_for_delete).length,cr=rules.filter(r=>r.action==='CRIAR'&&!r._marked_for_delete).length,d=rules.filter(r=>r._marked_for_delete).length;
  document.getElementById('kpis').innerHTML='<div class="kpi"><div class="v" style="color:#38bdf8">'+t+'</div><div class="l">Total</div></div><div class="kpi"><div class="v" style="color:#22c55e">'+e+'</div><div class="l">Existentes</div></div><div class="kpi"><div class="v" style="color:#f97316">'+n+'</div><div class="l">Novas</div></div><div class="kpi"><div class="v" style="color:#22c55e">'+m+'</div><div class="l">MANTER</div></div><div class="kpi"><div class="v" style="color:#eab308">'+c+'</div><div class="l">COMPLEMENTAR</div></div><div class="kpi"><div class="v" style="color:#f97316">'+cr+'</div><div class="l">CRIAR</div></div><div class="kpi"><div class="v" style="color:#ef4444">'+d+'</div><div class="l">Removidas</div></div>';
  document.getElementById('selInfo').textContent=selected.size+' selecionadas';
}}
function render(){{
  let fd=rules.filter(r=>{{let a=document.getElementById('fAction').value,t=document.getElementById('fTier').value,s=document.getElementById('fSource').value,q=(document.getElementById('fSearch').value||'').toLowerCase();if(a&&r.action!==a)return false;if(t&&r.tier!==t)return false;if(s&&r.source!==s)return false;if(q&&!r.rule_name.toLowerCase().includes(q)&&!r.routines.some(rt=>rt.routine.toLowerCase().includes(q)))return false;return true}});
  document.getElementById('tb').innerHTML=fd.map(r=>{{
    let idx=rules.indexOf(r),tot=r.routines.reduce((s,rt)=>s+rt.features.length,0),mis=r.routines.reduce((s,rt)=>s+rt.features.filter(f=>f.status==='FALTANTE').length,0),bd=r._marked_for_delete?'bd-del':r.action==='MANTER'?'bd-ok':r.action==='CRIAR'?'bd-new':'bd-part',users=r.users.slice(0,3).map(u=>'<span class="chip">'+esc(u.login||u.user_id)+'</span>').join('')+(r.users.length>3?' <span class="chip">+'+r.users.slice(3).length+'</span>':'');
    return'<tr class="'+(r._marked_for_delete?'del':'')+'" onclick="toggleExpand('+idx+')"><td onclick="event.stopPropagation()"><input type="checkbox" '+(selected.has(idx)?'checked':'')+' onchange="tgl('+idx+')"></td><td><span class="rule-link">'+esc(r.rule_name)+'</span>'+(r.has_excess?' <span class="badge bd-exc">EXCEDENTE</span>':'')+'</td><td>'+esc(r.tier)+'</td><td><span class="badge '+bd+'">'+(r._marked_for_delete?'REMOVIDO':r.action)+'</span></td><td>'+users+'</td><td>'+r.routines.length+' rotinas / '+tot+' features</td><td>'+(mis>0?'<span style="color:#f97316;font-weight:700">'+mis+' falt.</span>':'<span style="color:#22c55e">—</span>')+'</td><td><button class="btn btn-r" style="padding:2px 6px;font-size:9px" onclick="event.stopPropagation();delRule('+idx+')">'+(r._marked_for_delete?'↩':'✕')+'</button></td></tr><tr class="expand-row" id="ex-'+idx+'"><td colspan="8"><div style="display:flex;flex-wrap:wrap;gap:6px">'+r.routines.map(rt=>'<div style="margin:4px 0"><strong style="font-size:11px;color:#38bdf8">'+esc(rt.routine)+'</strong><br>'+rt.features.map(f=>'<span class="ftag ft-'+(f.status==='EXISTENTE'?'ok':f.status==='FALTANTE'?'mis':'exc')+'">'+esc(f.feature||'?')+'</span>').join('')+'</div>').join('')+'</div><div style="margin-top:8px;display:flex;gap:6px"><button class="btn btn-b" style="font-size:9px;padding:3px 8px" onclick="event.stopPropagation();openModal('+idx+')">Editar</button></div></td></tr>';
  }}).join('');
  updateKPIs();
}}
function toggleExpand(i){{document.getElementById('ex-'+i).classList.toggle('open')}}
function tgl(i){{selected.has(i)?selected.delete(i):selected.add(i);render()}}
function toggleAll(cb){{if(cb.checked)rules.forEach((_,i)=>selected.add(i));else selected.clear();render()}}
function delRule(i){{rules[i]._marked_for_delete=!rules[i]._marked_for_delete;render()}}
function sort(col){{if(sortCol===col)sortAsc=!sortAsc;else{{sortCol=col;sortAsc=true}}rules.sort((a,b)=>{{let va=(a[col]||'').toString().toLowerCase(),vb=(b[col]||'').toString().toLowerCase();return sortAsc?va.localeCompare(vb):vb.localeCompare(va)}});render()}}

function removeRoutineRow(el,ruleIdx,routineIdx){{var row=el.closest('.row');if(row)row.remove();rules[ruleIdx].routines.splice(routineIdx,1)}}
function openModal(i){{let r=rules[i];let h='';h+='<h2>'+esc(r.rule_name)+'</h2>';h+='<div class="row"><label style="font-size:10px;width:60px">Nome:</label><input id="edName" value="'+esc(r.rule_name)+'"></div>';h+='<div class="row"><label style="font-size:10px;width:60px">Desc:</label><input id="edDesc" value="'+esc(r.rule_description||'')+'"></div>';h+='<div class="row"><label style="font-size:10px;width:60px">Tier:</label><select id="edTier">';['EXISTENTE','TIER2','TIER3','TIER4'].forEach(function(t){{h+='<option '+(r.tier===t?'selected':'')+'>'+t+'</option>'}});h+='</select>';h+='<label style="font-size:10px;width:60px">Acao:</label><select id="edAction">';['MANTER','CRIAR','COMPLEMENTAR'].forEach(function(a){{h+='<option '+(r.action===a?'selected':'')+'>'+a+'</option>'}});h+='</select></div>';h+='<div class="sec"><h3>Usuarios ('+r.users.length+')</h3><div style="display:flex;gap:4px;flex-wrap:wrap">';r.users.forEach(function(u){{h+='<span class="chip">'+esc(u.login||u.user_id)+' <span style="cursor:pointer;color:#ef4444" onclick="var p=this.parentElement;if(p)p.remove()">x</span></span>'}});h+='</div><div class="row" style="margin-top:8px"><input id="edNewUser" placeholder="login"><button class="btn btn-b" onclick="addUsr('+i+')">+</button></div></div>';h+='<div class="sec"><h3>Rotinas ('+r.routines.length+')</h3>';r.routines.forEach(function(rt,ri){{h+='<div class="row"><span style="font-size:11px;color:#38bdf8;min-width:80px">'+esc(rt.routine)+'</span><span style="font-size:9px;color:#64748b">'+esc(rt.description||'')+'</span><span style="font-size:9px;color:#f97316">'+rt.features.filter(function(f){{return f.status==='FALTANTE'}}).length+' falt.</span><button class="btn btn-r" style="padding:2px 6px;font-size:9px;margin-left:auto" onclick="removeRoutineRow(this,'+i+','+ri+')">x</button></div>'}});h+='<div class="row"><input id="edNewRt" placeholder="codigo"><button class="btn btn-b" onclick="addRt('+i+')">+</button></div></div>';h+='<div style="margin-top:16px"><button class="btn btn-g" onclick="saveModal('+i+')">Salvar</button> <button class="btn btn-s" onclick="closeModal()">Cancelar</button></div>';document.getElementById('mc').innerHTML=h;document.getElementById('mo').classList.add('show')}}
function addUsr(i){{let v=document.getElementById('edNewUser').value.trim();if(v){{rules[i].users.push({{user_id:v,login:v}});openModal(i)}}}}
function addRt(i){{let v=document.getElementById('edNewRt').value.trim();if(v){{rules[i].routines.push({{routine:v.toUpperCase(),description:'',features:[{{feature:'Acesso',access:'1',menu_oper:0,menu_def:'',status:'FALTANTE'}}],status:'FALTANTE'}});openModal(i)}}}}
function saveModal(i){{let r=rules[i];r.rule_name=document.getElementById('edName').value.trim().toUpperCase()||r.rule_name;r.rule_description=document.getElementById('edDesc').value.trim();r.tier=document.getElementById('edTier').value;r.action=document.getElementById('edAction').value;closeModal();render()}}
function closeModal(){{document.getElementById('mo').classList.remove('show')}}
function addRule(){{let n=prompt('Nome da regra (ex: P_NOVO):');if(!n)return;let t=prompt('Tier (EXISTENTE/TIER2/TIER3/TIER4):','TIER3');rules.push({{rule_id:null,rule_name:n.toUpperCase(),rule_description:'',source:'NOVO',tier:(t||'TIER3').toUpperCase(),action:'CRIAR',has_excess:false,users:[],groups:[],routines:[],_marked_for_delete:false}});render();toast('Regra criada')}}

function genSQL(){{let t=selected.size>0?[...selected].map(i=>rules[i]).filter(r=>!r._marked_for_delete):rules.filter(r=>!r._marked_for_delete&&r.action!=='MANTER');let d=selected.size>0?[...selected].map(i=>rules[i]).filter(r=>r._marked_for_delete):rules.filter(r=>r._marked_for_delete);let ls=[];ls.push('-- ==============================================');ls.push('-- DELTA SQL — '+new Date().toISOString().slice(0,10));ls.push('-- Pendentes: '+t.length+' | Soft deletes: '+d.length);ls.push('-- ==============================================');ls.push('');if(d.length){{ls.push('-- ATENCAO: Este script contem SOFT DELETES. Revise antes de executar.');ls.push('')}}ls.push('BEGIN TRANSACTION');ls.push('');let s=1;t.forEach(r=>{{let rid=r.rule_id||('A'+String(s++).padStart(5,'0'));if(r.source==='NOVO'){{ls.push('INSERT INTO SYS_RULES (RL__ID, RL__CODIGO) VALUES ('+q(rid)+', '+q(r.rule_name)+');');ls.push('')}}else{{ls.push('-- '+r.rule_name+' — complementos');ls.push('')}}r.routines.forEach(rt=>rt.features.filter(f=>f.status==='FALTANTE').forEach(f=>ls.push('INSERT INTO SYS_RULES_FEATURES (RL__ID, RL__ROTINA, RL__DESMDEF, RL__ACESSO) VALUES ('+q(rid)+', '+q(rt.routine)+', '+q(f.feature||'')+', '+q(f.access||'1')+');')));if(r.source==='NOVO')r.routines.forEach(rt=>ls.push('INSERT INTO SYS_RULES_TRANSACT (RL__ID, RL__ROTINA, RL__DESROT, RL__ACESSO, RL__CHKSUM, D_E_L_E_T_) VALUES ('+q(rid)+', '+q(rt.routine)+', '+q((rt.description||'').slice(0,40))+', '+q('1')+', '+q('')+', '+q(' ')+');'));r.users.forEach(u=>ls.push('INSERT INTO SYS_RULES_USR_RULES (USER_ID, USR_RL_ID) VALUES ('+q(u.user_id||'')+', '+q(rid)+');'));ls.push('')}});if(d.length){{d.forEach(r=>{{if(r.rule_id)ls.push('UPDATE SYS_RULES_USR_RULES SET D_E_L_E_T_ = '+q('*')+' WHERE USR_RL_ID = '+q(r.rule_id)+'; -- '+r.rule_name)}})}}ls.push('COMMIT');sqlCache=ls.join(String.fromCharCode(10));toast('SQL gerado: '+t.length+' pendentes')}}
function q(v){{return String.fromCharCode(39)+String(v||'')+String.fromCharCode(39)}}
function downloadSQL(){{if(!sqlCache)genSQL();let b=new Blob([sqlCache],{{type:'text/plain'}});let a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='delta.sql';a.click()}}
function saveJSON(){{let o={{rules:rules.filter(r=>!r._marked_for_delete),deleted_bindings:rules.filter(r=>r._marked_for_delete&&r.rule_id).map(r=>({{rule_name:r.rule_name,rule_id:r.rule_id,table:'SYS_RULES_USR_RULES'}}))}};let b=new Blob([JSON.stringify(o,null,2)],{{type:'application/json'}});let a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='regras_ajustadas.json';a.click();toast('JSON salvo')}}
function toast(m){{let t=document.getElementById('toast');t.textContent=m;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),2000)}}
function esc(s){{let d=document.createElement('div');d.textContent=(s||'').toString();return d.innerHTML.split(String.fromCharCode(39)).join('&#39;')}}
window.onload=init;
</script>
</body>
</html>"""

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path
