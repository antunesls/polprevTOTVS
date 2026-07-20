import json
import os


def generate_kanban_html(consolidated_inventory, output_path, empresa_name="BOSAL"):
    rules = consolidated_inventory.get("rules", []) if consolidated_inventory else []
    data_json = json.dumps(rules, indent=2, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Kanban — Regras {empresa_name}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:#0a0a1a;color:#d4d4e0;height:100vh;display:flex;flex-direction:column;overflow:hidden}}
.hdr{{background:#12122a;border-bottom:1px solid #2a2a4a;padding:10px 20px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px}}
.hdr h1{{font-size:16px;background:linear-gradient(135deg,#6366f1,#a855f7);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.hdr .st{{font-size:10px;color:#7f8ca0}}.hdr .btns{{display:flex;gap:5px;flex-wrap:wrap}}
.btn{{padding:5px 10px;border:none;border-radius:5px;font-size:10px;font-weight:600;cursor:pointer}}
.btn-p{{background:#4f46e5;color:#fff}}.btn-g{{background:#166534;color:#fff}}.btn-s{{background:#334155;color:#cbd5e1}}.btn-r{{background:#991b1b;color:#fff}}
.tbar{{background:#12122a;border-bottom:1px solid #2a2a4a;padding:8px 20px;display:flex;gap:8px;align-items:center;flex-wrap:wrap}}
.tbar select,.tbar input{{background:#1a1a3a;border:1px solid #2a2a4a;border-radius:5px;padding:5px 8px;color:#d4d4e0;font-size:10px}}
.board{{flex:1;display:flex;gap:12px;padding:14px 20px;overflow-x:auto;overflow-y:hidden}}
.col{{min-width:260px;max-width:320px;background:#12122a;border-radius:12px;border:2px solid #2a2a4a;display:flex;flex-direction:column;flex-shrink:0}}
.col-h{{padding:12px 14px;border-bottom:1px solid #2a2a4a;display:flex;align-items:center;justify-content:space-between}}
.col-t{{font-size:13px;font-weight:700}}.col-c{{font-size:10px;background:#2a2a4a;padding:1px 8px;border-radius:8px}}
.col-b{{flex:1;overflow-y:auto;padding:8px;display:flex;flex-direction:column;gap:6px;min-height:80px}}
.col-b.drag-over{{background:rgba(99,102,241,.06)}}
.c-manter{{border-color:#14532d}}.c-manter .col-t{{color:#22c55e}}
.c-comp{{border-color:#713f12}}.c-comp .col-t{{color:#eab308}}
.c-criar{{border-color:#7c2d12}}.c-criar .col-t{{color:#f97316}}
.c-del{{border-color:#450a0a}}.c-del .col-t{{color:#ef4444}}
.card{{background:#1a1a3a;border-radius:10px;padding:12px;cursor:grab;border:1px solid #2a2a4a;transition:.12s;user-select:none}}
.card:hover{{border-color:#6366f1;transform:translateY(-1px);box-shadow:0 3px 12px rgba(99,102,241,.1)}}
.card:active{{cursor:grabbing}}.card.dragging{{opacity:.3}}
.cr{{display:flex;align-items:center;justify-content:space-between;margin-bottom:6px}}
.cn{{font-size:12px;font-weight:700;color:#e0e0e0}}.ct{{font-size:8px;color:#7f8ca0;background:#2a2a4a;padding:1px 5px;border-radius:3px}}
.cb{{font-size:8px;padding:2px 5px;border-radius:3px;font-weight:700}}
.cb-ok{{background:#14532d;color:#22c55e}}.cb-part{{background:#713f12;color:#eab308}}.cb-new{{background:#7c2d12;color:#f97316}}
.cm{{font-size:9px;color:#7f8ca0;margin:4px 0}}
.crts{{font-size:9px;color:#94a3b8;display:flex;flex-wrap:wrap;gap:2px;max-height:60px;overflow:hidden}}
.ctag{{font-size:8px;padding:1px 4px;border-radius:3px;font-family:monospace}}
.ct-ok{{background:#14532d;color:#86efac}}.ct-mis{{background:#713f12;color:#fde047}}.ct-exc{{background:#3b0764;color:#c084fc}}
.cf{{display:flex;justify-content:space-between;align-items:center;margin-top:6px;padding-top:6px;border-top:1px solid #2a2a4a}}
.cus{{display:flex;gap:2px}}.cav{{width:20px;height:20px;border-radius:50%;background:linear-gradient(135deg,#6366f1,#a855f7);display:flex;align-items:center;justify-content:center;font-size:8px;font-weight:700;color:#fff}}
.cav-more{{background:#2a2a4a;color:#7f8ca0}}.ca button{{background:none;border:none;color:#7f8ca0;cursor:pointer;font-size:10px;padding:2px 4px}}
.ca button:hover{{color:#ef4444}}
.modal-overlay{{display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:100;align-items:center;justify-content:center}}
.modal-overlay.show{{display:flex}}
.modal{{background:#12122a;border:2px solid #2a2a4a;border-radius:12px;width:600px;max-height:82vh;overflow:auto;padding:22px}}
.modal h2{{color:#818cf8;font-size:15px;margin-bottom:14px}}.modal h3{{font-size:11px;color:#7f8ca0;margin:14px 0 6px}}
.modal .row{{display:flex;gap:8px;margin:6px 0;align-items:center}}
.modal input,.modal select{{background:#1a1a3a;border:1px solid #2a2a4a;border-radius:5px;padding:5px 8px;color:#d4d4e0;font-size:10px}}
.modal button{{padding:6px 12px;border:none;border-radius:5px;font-size:10px;font-weight:600;cursor:pointer;margin-right:6px}}
.toast{{position:fixed;bottom:16px;left:50%;transform:translateX(-50%);background:#22c55e;color:#fff;padding:8px 16px;border-radius:6px;font-size:11px;z-index:200;opacity:0;transition:.3s}}.toast.show{{opacity:1}}
</style>
</head>
<body>
<div class="hdr"><div><h1>Kanban de Privilégios — {empresa_name}</h1><div class="st">Gerado automaticamente — {len(rules)} regras</div></div>
<div class="btns"><button class="btn btn-s" onclick="saveJSON()">💾 Salvar</button><button class="btn btn-p" onclick="addRule()">+ Regra</button><button class="btn btn-g" onclick="genSQL()">⚡ SQL</button><button class="btn btn-g" onclick="downloadSQL()">⬇ .sql</button></div></div>
<div class="tbar"><select id="fTier" onchange="renderB()"><option value="">Todos tiers</option></select><input type="text" id="fSearch" placeholder="Buscar..." oninput="renderB()" style="width:160px"></div>
<div class="board" id="board"></div>
<div class="modal-overlay" id="mo"><div class="modal" id="mc"></div></div>
<div id="toast" class="toast"></div>

<script id="rules-data" type="application/json">{data_json}</script>
<script>
let rules=JSON.parse(document.getElementById('rules-data').textContent).map(r=>({{...r,_marked_for_delete:r._marked_for_delete||false}}));
let sqlCache='';

function init(){{
  let tiers=[...new Set(rules.map(r=>r.tier))].sort();
  document.getElementById('fTier').innerHTML='<option value="">Todos tiers</option>'+tiers.map(t=>'<option>'+t+'</option>').join('');
  renderB();
}}
function renderB(){{
  let fd=rules.filter(r=>{{let t=document.getElementById('fTier').value,q=(document.getElementById('fSearch').value||'').toLowerCase();if(t&&r.tier!==t)return false;if(q&&!r.rule_name.toLowerCase().includes(q)&&!r.routines.some(rt=>rt.routine.toLowerCase().includes(q)))return false;return true}});
  let cols={{manter:[],complementar:[],criar:[],removido:[]}};
  fd.forEach(r=>{{if(r._marked_for_delete)cols.removido.push(r);else if(r.action==='MANTER')cols.manter.push(r);else if(r.action==='COMPLEMENTAR')cols.complementar.push(r);else cols.criar.push(r)}});
  document.getElementById('board').innerHTML=[{{k:'manter',t:'Sem Alteração',c:'c-manter'}},{{k:'complementar',t:'Complementar',c:'c-comp'}},{{k:'criar',t:'Criar Novo',c:'c-criar'}},{{k:'removido',t:'Removidos',c:'c-del'}}].map(function(col){{return'<div class="col '+col.c+'"><div class="col-h"><span class="col-t">'+col.t+'</span><span class="col-c">'+cols[col.k].length+'</span></div><div class="col-b" data-col="'+col.k+'" ondragover="dover(event)" ondragleave="dleave(event)" ondrop="drop(event,this.dataset.col)">'+cols[col.k].map(function(r){{return card(r)}}).join('')+'</div></div>'}}).join('');
  let m=rules.filter(r=>!r._marked_for_delete&&r.action!=='MANTER').length,d=rules.filter(r=>r._marked_for_delete).length;
  document.querySelector('.st').textContent=rules.length+' regras | '+m+' pendentes | '+d+' removidas';
}}
function card(r){{
  let idx=rules.indexOf(r),mis=r.routines.reduce((s,rt)=>s+rt.features.filter(f=>f.status==='FALTANTE').length,0),tot=r.routines.reduce((s,rt)=>s+rt.features.length,0),bd=r.action==='MANTER'?'cb-ok':r.action==='COMPLEMENTAR'?'cb-part':'cb-new';
  let h='';h+='<div class="card" draggable="true" data-idx="'+idx+'" ondragstart="dstart(event)" ondragend="dend(event)" onclick="openModal('+idx+')">';h+='<div class="cr"><span class="cn">'+esc(r.rule_name)+'</span><span class="ct">'+esc(r.tier)+'</span></div>';h+='<span class="cb '+bd+'">'+r.action+'</span>'+(r.has_excess?' <span class="cb" style="background:#3b0764;color:#c084fc">EXCEDENTE</span>':'');h+='<div class="cm">'+r.routines.length+' rot '+String.fromCharCode(183)+' '+(mis>0?'<span style="color:#f97316">'+mis+' falt.</span>':tot+' ok')+'</div>';h+='<div class="crts">';r.routines.slice(0,4).forEach(function(rt){{rt.features.slice(0,2).forEach(function(f){{h+='<span class="ctag ct-'+(f.status==='EXISTENTE'?'ok':f.status==='FALTANTE'?'mis':'exc')+'">'+esc(rt.routine)+':'+esc(f.feature||'?')+'</span>'}})}});h+='</div>';h+='<div class="cf"><div class="cus">';r.users.slice(0,3).forEach(function(u){{h+='<div class="cav" title="'+esc(u.login||u.user_id)+'">'+esc((u.login||u.user_id||'?').slice(0,2).toUpperCase())+'</div>'}});if(r.users.length>3)h+='<div class="cav cav-more"></div>';h+='</div><div class="ca"><button onclick="event.stopPropagation();delRule('+idx+')">x</button></div></div></div>';return h}}
function drop(e,col){{e.preventDefault();e.currentTarget.classList.remove('drag-over');let idx=parseInt(e.dataTransfer.getData('text/plain'));if(col==='removido'){{rules[idx]._marked_for_delete=!rules[idx]._marked_for_delete}}else{{rules[idx]._marked_for_delete=false;if(col==='manter')rules[idx].action='MANTER';else if(col==='complementar')rules[idx].action='COMPLEMENTAR';else rules[idx].action='CRIAR'}}renderB()}}
function delRule(i){{rules[i]._marked_for_delete=!rules[i]._marked_for_delete;renderB()}}
function dstart(e){{e.target.classList.add('dragging');e.dataTransfer.setData('text/plain',e.target.dataset.idx)}}
function dend(e){{e.target.classList.remove('dragging')}}
function dover(e){{e.preventDefault();e.currentTarget.classList.add('drag-over')}}
function dleave(e){{e.currentTarget.classList.remove('drag-over')}}
function openModal(i){{let r=rules[i],mis=r.routines.reduce((s,rt)=>s+rt.features.filter(f=>f.status==='FALTANTE').length,0);document.getElementById('mc').innerHTML='<h2>'+esc(r.rule_name)+' <span class="cb '+(r.action==='MANTER'?'cb-ok':r.action==='COMPLEMENTAR'?'cb-part':'cb-new')+'">'+r.action+'</span></h2><div class="row"><label style="font-size:10px;width:50px">Nome:</label><input id="en" value="'+esc(r.rule_name)+'"><label style="font-size:10px;width:40px">Tier:</label><select id="et">'+['EXISTENTE','TIER2','TIER3','TIER4'].map(t=>'<option '+(r.tier===t?'selected':'')+'>'+t+'</option>').join('')+'</select></div><h3>Rotinas — '+(mis>0?'<span style="color:#f97316">'+mis+' falt.</span>':'<span style="color:#22c55e">ok</span>')+'</h3>'+r.routines.map(rt=>'<div style="margin:4px 0;font-size:10px"><strong style="color:#38bdf8">'+esc(rt.routine)+'</strong> '+rt.features.map(f=>'<span class="ctag ct-'+(f.status==='EXISTENTE'?'ok':f.status==='FALTANTE'?'mis':'exc')+'">'+esc(f.feature||'')+'</span>').join('')+'</div>').join('')+'<h3>Usuários ('+r.users.length+')</h3><div style="display:flex;gap:4px;flex-wrap:wrap">'+r.users.map(u=>'<span class="cav" style="width:auto;border-radius:8px;padding:2px 8px;font-size:9px">'+esc(u.login||u.user_id)+' <span style="cursor:pointer;color:#ef4444" onclick="this.parentElement.remove()">×</span></span>').join('')+'</div><div class="row"><input id="enu" placeholder="login"><button class="btn btn-p" onclick="addUsr('+i+')">+</button></div><div style="margin-top:14px"><button class="btn btn-p" onclick="saveM('+i+')">Salvar</button><button class="btn btn-r" onclick="delRule('+i+');closeM()">Remover</button><button class="btn btn-s" onclick="closeM()">Fechar</button></div>';document.getElementById('mo').classList.add('show')}}
function addUsr(i){{let v=document.getElementById('enu').value.trim();if(v){{rules[i].users.push({{user_id:v,login:v}});openModal(i)}}}}
function saveM(i){{let r=rules[i];r.rule_name=document.getElementById('en').value.trim().toUpperCase()||r.rule_name;r.tier=document.getElementById('et').value;closeM();renderB()}}
function closeM(){{document.getElementById('mo').classList.remove('show')}}
function addRule(){{let n=prompt('Nome:'),t=prompt('Tier:','TIER3');if(!n)return;rules.push({{rule_id:null,rule_name:n.toUpperCase(),source:'NOVO',tier:(t||'TIER3').toUpperCase(),action:'CRIAR',has_excess:false,users:[],groups:[],routines:[],_marked_for_delete:false}});renderB();st('Regra criada')}}

function genSQL(){{let t=rules.filter(r=>!r._marked_for_delete&&r.action!=='MANTER'),d=rules.filter(r=>r._marked_for_delete);let ls=[];ls.push('-- DELTA SQL — '+new Date().toISOString().slice(0,10));ls.push('-- Pendentes: '+t.length+' | Deletes: '+d.length);ls.push('');ls.push('BEGIN TRANSACTION');ls.push('');if(d.length){{ls.push('-- ATENCAO: SOFT DELETES abaixo');ls.push('')}}let s=1;t.forEach(r=>{{let rid=r.rule_id||('A'+String(s++).padStart(5,'0'));if(r.source==='NOVO')ls.push('INSERT INTO SYS_RULES (RL__ID, RL__CODIGO) VALUES ('+q(rid)+', '+q(r.rule_name)+');');else ls.push('-- '+r.rule_name);r.routines.forEach(rt=>rt.features.filter(f=>f.status==='FALTANTE').forEach(f=>ls.push('INSERT INTO SYS_RULES_FEATURES (RL__ID, RL__ROTINA, RL__DESMDEF, RL__ACESSO) VALUES ('+q(rid)+', '+q(rt.routine)+', '+q(f.feature||'')+', '+q('1')+');')));if(r.source==='NOVO')r.routines.forEach(rt=>ls.push('INSERT INTO SYS_RULES_TRANSACT (RL__ID, RL__ROTINA) VALUES ('+q(rid)+', '+q(rt.routine)+');'));r.users.forEach(u=>ls.push('INSERT INTO SYS_RULES_USR_RULES (USER_ID, USR_RL_ID) VALUES ('+q(u.user_id||'')+', '+q(rid)+');'));ls.push('')}});d.forEach(r=>{{if(r.rule_id)ls.push('UPDATE SYS_RULES_USR_RULES SET D_E_L_E_T_ = '+q('*')+' WHERE USR_RL_ID = '+q(r.rule_id)+'; -- '+r.rule_name)}});ls.push('COMMIT');sqlCache=ls.join(String.fromCharCode(10));st('SQL gerado')}}
function q(v){{return String.fromCharCode(39)+String(v||'')+String.fromCharCode(39)}}
function downloadSQL(){{if(!sqlCache)genSQL();let b=new Blob([sqlCache],{{type:'text/plain'}});let a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='delta.sql';a.click()}}
function saveJSON(){{let o={{rules:rules.filter(r=>!r._marked_for_delete),deleted_bindings:rules.filter(r=>r._marked_for_delete&&r.rule_id).map(r=>({{rule_name:r.rule_name,rule_id:r.rule_id}}))}};let b=new Blob([JSON.stringify(o)],{{type:'application/json'}});let a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='regras_ajustadas.json';a.click();st('Salvo')}}
function st(m){{let t=document.getElementById('toast');t.textContent=m;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),2000)}}
function esc(s){{let d=document.createElement('div');d.textContent=(s||'').toString();return d.innerHTML.split(String.fromCharCode(39)).join('&#39;')}}
window.onload=init;
</script>
</body>
</html>"""

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path
