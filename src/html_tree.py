import json
import os


def generate_tree_html(consolidated_inventory, output_path, empresa_name="BOSAL"):
    rules = consolidated_inventory.get("rules", []) if consolidated_inventory else []
    data_json = json.dumps(rules, indent=2, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Split Panel — Regras {empresa_name}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:#0c0c1d;color:#d4d4e0;height:100vh;display:flex;flex-direction:column;overflow:hidden}}
.hdr{{background:#12122a;border-bottom:1px solid #2a2a4a;padding:10px 18px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px}}
.hdr h1{{font-size:15px;color:#818cf8}}.hdr .st{{font-size:10px;color:#7f8ca0}}.hdr .btns{{display:flex;gap:5px;flex-wrap:wrap}}
.btn{{padding:5px 10px;border:none;border-radius:5px;font-size:10px;font-weight:600;cursor:pointer}}
.btn-b{{background:#4f46e5;color:#fff}}.btn-g{{background:#166534;color:#fff}}.btn-s{{background:#334155;color:#cbd5e1}}.btn-r{{background:#991b1b;color:#fff}}
.main{{flex:1;display:flex;overflow:hidden}}
.tree{{width:260px;min-width:200px;background:#0f0f2a;border-right:1px solid #2a2a4a;display:flex;flex-direction:column;overflow:hidden}}
.tree-in{{padding:8px 10px;border-bottom:1px solid #2a2a4a}}
.tree-in input{{width:100%;padding:6px 8px;border-radius:5px;border:1px solid #2a2a4a;background:#1a1a3a;color:#d4d4e0;font-size:10px;outline:none}}
.tree-in input:focus{{border-color:#4f46e5}}
.tree-body{{flex:1;overflow-y:auto;padding:6px 0}}
.tg{{margin-bottom:2px}}
.tgh{{padding:7px 12px;font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:.4px;cursor:pointer;display:flex;align-items:center;gap:5px}}
.tgh:hover{{color:#d4d4e0}}.tgh .ar{{font-size:8px;transition:.2s}}.tgh .ar.open{{transform:rotate(90deg)}}
.tgc{{font-size:8px;background:#2a2a4a;padding:1px 5px;border-radius:5px;margin-left:auto}}
.tgi{{display:none}}.tgi.open{{display:block}}
.ti{{padding:5px 12px 5px 24px;font-size:10px;cursor:pointer;display:flex;align-items:center;gap:6px;border-left:2px solid transparent}}
.ti:hover{{background:#1a1a3a}}.ti.sel{{background:#1a1a3a;border-left-color:#4f46e5}}
.dot{{width:7px;height:7px;border-radius:50%;flex-shrink:0}}
.dot-ok{{background:#22c55e}}.dot-part{{background:#eab308}}.dot-new{{background:#f97316}}.dot-del{{background:#ef4444}}

.detail{{flex:1;display:flex;flex-direction:column;overflow:hidden;background:#12122a}}
.detail-empty{{flex:1;display:flex;align-items:center;justify-content:center;color:#4a4a6a;font-size:13px}}
.detail-body{{flex:1;overflow-y:auto;padding:20px 24px;display:none}}
.detail-body.active{{display:block}}
.dh{{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:16px}}
.dt{{font-size:18px;font-weight:800;color:#e0e0e0}}.ds{{font-size:11px;color:#7f8ca0;margin-top:2px}}
.db{{display:inline-block;padding:3px 10px;border-radius:4px;font-size:10px;font-weight:700}}
.db-ok{{background:#14532d;color:#22c55e}}.db-part{{background:#713f12;color:#eab308}}.db-new{{background:#7c2d12;color:#f97316}}
.sec{{margin:18px 0}}.sec h3{{font-size:12px;color:#94a3b8;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px;padding-bottom:4px;border-bottom:1px solid #2a2a4a}}
.rt-row{{display:flex;align-items:center;gap:6px;padding:6px 0;border-bottom:1px solid #1a1a3a}}
.rt-code{{font-family:'Fira Code',monospace;font-size:12px;color:#38bdf8;min-width:90px}}
.rt-desc{{font-size:10px;color:#64748b;min-width:120px}}
.ft-list{{display:flex;flex-wrap:wrap;gap:3px;flex:1}}
.ft{{font-size:9px;padding:2px 6px;border-radius:3px;font-family:monospace}}
.ft-ok{{background:#14532d;color:#86efac}}.ft-ok::before{{content:'✓ '}}
.ft-mis{{background:#713f12;color:#fde047}}.ft-mis::before{{content:'+ '}}
.ft-exc{{background:#3b0764;color:#c084fc}}.ft-exc::before{{content:'⚠ '}}

.user-row{{display:flex;align-items:center;gap:4px;margin:3px 0}}
.user-chip{{display:flex;align-items:center;gap:4px;padding:3px 8px;background:#1a1a3a;border:1px solid #2a2a4a;border-radius:6px;font-size:10px}}
.user-chip button{{background:none;border:none;color:#ef4444;cursor:pointer;font-size:12px;line-height:1}}
.missing-box{{border:1px solid #713f12;border-radius:6px;padding:10px 12px;margin:10px 0;background:#1a1a12}}
.missing-box h4{{color:#eab308;font-size:11px;margin-bottom:4px}}
.missing-box div{{font-family:'Fira Code',monospace;font-size:10px;color:#fde047;margin:2px 0}}

.sql-panel{{width:360px;min-width:280px;background:#0a0a1a;border-left:2px solid #2a2a4a;display:flex;flex-direction:column}}
.sql-h{{padding:10px 14px;border-bottom:1px solid #2a2a4a;display:flex;align-items:center;justify-content:space-between}}
.sql-h h3{{font-size:12px;color:#818cf8}}.sql-h span{{font-size:9px;color:#7f8ca0}}
.sql-body{{flex:1;overflow:auto;padding:10px 14px}}
.sql-body pre{{font-family:'Fira Code',monospace;font-size:10px;color:#94a3b8;white-space:pre-wrap;line-height:1.5}}
.sql-body .kw{{color:#818cf8}}.sql-body .cm{{color:#4a5a6a}}.sql-body .tb{{color:#38bdf8}}.sql-body .wn{{color:#ef4444}}
.sql-foot{{padding:8px 14px;border-top:1px solid #2a2a4a;display:flex;gap:6px}}
.sql-foot button{{flex:1;padding:6px;border:none;border-radius:5px;font-size:9px;font-weight:600;cursor:pointer}}
.toast{{position:fixed;bottom:16px;left:50%;transform:translateX(-50%);background:#22c55e;color:#fff;padding:8px 16px;border-radius:6px;font-size:11px;z-index:200;opacity:0;transition:.3s}}.toast.show{{opacity:1}}
</style>
</head>
<body>
<div class="hdr"><div><h1>Revisão de Privilégios — {empresa_name}</h1><div class="st">Gerado automaticamente — {len(rules)} regras</div></div>
<div class="btns"><button class="btn btn-s" onclick="saveJSON()">💾 Salvar</button><button class="btn btn-b" onclick="addRule()">+ Regra</button><button class="btn btn-g" onclick="genSQL()">⚡ SQL</button><button class="btn btn-g" onclick="downloadSQL()">⬇ .sql</button></div></div>
<div class="main">
<div class="tree"><div class="tree-in"><input type="text" id="ts" placeholder="🔍 Buscar..." oninput="renderTree()"></div><div class="tree-body" id="treeBody"></div></div>
<div class="detail"><div class="detail-empty" id="de">Selecione uma regra na árvore</div><div class="detail-body" id="db"></div></div>
<div class="sql-panel"><div class="sql-h"><h3>Preview SQL Delta</h3><span id="sqlCount"></span></div><div class="sql-body"><pre id="sqlPrev"><span class="cm">-- Clique em "SQL" para gerar o delta</span></pre></div><div class="sql-foot"><button class="btn btn-s" onclick="navigator.clipboard.writeText((document.getElementById('sqlPrev').textContent||'').replace(/<[^>]+>/g,''))">📋 Copiar</button><button class="btn btn-g" onclick="downloadSQL()">⬇ Download</button></div></div>
</div>
<div id="toast" class="toast"></div>

<script id="rules-data" type="application/json">{data_json}</script>
<script>
let rules=JSON.parse(document.getElementById('rules-data').textContent).map(r=>({{...r,_marked_for_delete:r._marked_for_delete||false}}));
let selIdx=null,sqlCache='';

function gtg(t){{if(t==='EXISTENTE')return'Existentes';if(t==='TIER2')return'Tier 2 — Departamentos';if(t==='TIER3')return'Tier 3 — Conjuntos';if(t==='TIER4')return'Tier 4 — Individuais';return'Outros'}}
function renderTree(){{
  let q=(document.getElementById('ts').value||'').toLowerCase(),grp={{}};
  rules.forEach((r,i)=>{{if(q&&!r.rule_name.toLowerCase().includes(q)&&!r.routines.some(rt=>rt.routine.toLowerCase().includes(q)||(rt.description||'').toLowerCase().includes(q)))return;let g=gtg(r.tier);grp[g]=grp[g]||[];grp[g].push({{...r,_i:i}})}});
  document.getElementById('treeBody').innerHTML=Object.entries(grp).map(([n,it])=>{{let d={{MANTER:'dot-ok',COMPLEMENTAR:'dot-part',CRIAR:'dot-new'}};return'<div class="tg"><div class="tgh" onclick="this.querySelector(\'.ar\').classList.toggle(\'open\');this.nextElementSibling.classList.toggle(\'open\')"><span class="ar open">▶</span>'+esc(n)+'<span class="tgc">'+it.length+'</span></div><div class="tgi open">'+it.map(r=>'<div class="ti'+(selIdx===r._i?' sel':'')+'" onclick="select('+r._i+')"><span class="dot '+(d[r.action]||'dot-ok')+'"></span>'+esc(r.rule_name)+(r._marked_for_delete?' <span style="color:#ef4444;font-size:8px">DEL</span>':'')+'</div>').join('')+'</div></div>'}}).join('')
}}
function select(i){{selIdx=i;renderTree();renderDetail()}}
function renderDetail(){{
  if(selIdx===null){{document.getElementById('de').style.display='flex';document.getElementById('db').classList.remove('active');return}}
  document.getElementById('de').style.display='none';document.getElementById('db').classList.add('active');
  let r=rules[selIdx],mis=r.routines.reduce((s,rt)=>s+rt.features.filter(f=>f.status==='FALTANTE').length,0),exc=r.routines.reduce((s,rt)=>s+rt.features.filter(f=>f.status==='EXCEDENTE').length,0),bd=r.action==='MANTER'?'db-ok':r.action==='COMPLEMENTAR'?'db-part':'db-new';
  document.getElementById('db').innerHTML='<div class="dh"><div><div class="dt">'+esc(r.rule_name)+'</div><div class="ds">'+esc(r.tier)+' | '+(r.rule_description||'')+(r.rule_id?' | ID: '+r.rule_id:'')+'</div></div><span class="db '+bd+'">'+(r._marked_for_delete?'REMOVIDO':r.action)+'</span></div>'+(exc>0?'<div class="missing-box" style="border-color:#3b0764"><h4 style="color:#c084fc">⚠ '+exc+' features extras</h4></div>':'')+(mis>0?'<div class="missing-box"><h4>'+mis+' complementos necessários</h4>'+r.routines.flatMap(rt=>rt.features.filter(f=>f.status==='FALTANTE').map(f=>'<div>'+esc(rt.routine)+' → '+esc(f.feature||'')+'</div>')).join('')+'</div>':'')+(mis===0&&r.action==='MANTER'?'<div class="missing-box" style="border-color:#14532d"><h4 style="color:#22c55e">✓ Completo</h4></div>':'')+'<div class="sec"><h3>Rotinas ('+r.routines.length+')</h3>'+r.routines.map(rt=>'<div class="rt-row"><span class="rt-code">'+esc(rt.routine)+'</span><span class="rt-desc">'+esc(rt.description||'')+'</span><div class="ft-list">'+rt.features.map(f=>'<span class="ft ft-'+(f.status==='EXISTENTE'?'ok':f.status==='FALTANTE'?'mis':'exc')+'">'+esc(f.feature||'')+'</span>').join('')+'</div></div>').join('')+'</div><div class="sec"><h3>Usuários ('+r.users.length+')</h3>'+r.users.map(u=>'<div class="user-row"><span class="user-chip">'+esc(u.login||u.user_id)+' <button onclick="rmUsr('+selIdx+',\''+esc(u.login||u.user_id)+'\')">×</button></span></div>').join('')+'<div class="user-row"><input id="nu" placeholder="login" style="background:#1a1a3a;border:1px solid #2a2a4a;border-radius:4px;padding:3px 6px;color:#d4d4e0;font-size:10px;width:120px"><button class="btn btn-b" style="padding:3px 8px;font-size:9px" onclick="addUsr('+selIdx+')">+</button></div></div><div style="display:flex;gap:8px;margin-top:16px"><button class="btn btn-r" onclick="delRule('+selIdx+')">'+(r._marked_for_delete?'↩ Desfazer':'✕ Remover')+'</button><button class="btn btn-b" onclick="refreshSQL()">Atualizar SQL</button><button class="btn btn-s" onclick="editName('+selIdx+')">✎ Renomear</button></div>';
}}
function rmUsr(i,login){{rules[i].users=rules[i].users.filter(u=>(u.login||u.user_id)!==login);renderDetail()}}
function addUsr(i){{let v=document.getElementById('nu').value.trim();if(v){{rules[i].users.push({{user_id:v,login:v}});renderDetail()}}}}
function delRule(i){{rules[i]._marked_for_delete=!rules[i]._marked_for_delete;renderDetail();renderTree();refreshSQL()}}
function editName(i){{let n=prompt('Novo nome:',rules[i].rule_name);if(n){{rules[i].rule_name=n.toUpperCase();renderTree();renderDetail()}}}}
function addRule(){{let n=prompt('Nome:'),t=prompt('Tier:','TIER3');if(!n)return;rules.push({{rule_id:null,rule_name:n.toUpperCase(),source:'NOVO',tier:(t||'TIER3').toUpperCase(),action:'CRIAR',has_excess:false,users:[],groups:[],routines:[],_marked_for_delete:false}});renderTree();st('Regra criada')}}

function refreshSQL(){{
  let t=rules.filter(r=>!r._marked_for_delete&&r.action!=='MANTER'),d=rules.filter(r=>r._marked_for_delete);
  let ls=[];ls.push('<span class="cm">-- DELTA SQL — '+new Date().toISOString().slice(0,10)+'</span>');ls.push('<span class="cm">-- Pendentes: '+t.length+' | Deletes: '+d.length+'</span>');ls.push('');ls.push('<span class="kw">BEGIN TRANSACTION</span>');ls.push('');if(d.length){{ls.push('<span class="wn">-- ATENCAO: SOFT DELETES abaixo</span>');ls.push('')}}
  let s=1;t.forEach(r=>{{let rid=r.rule_id||('A'+String(s++).padStart(5,'0'));if(r.source==='NOVO')ls.push('<span class="kw">INSERT INTO</span> <span class="tb">SYS_RULES</span> (RL__ID, RL__CODIGO) <span class="kw">VALUES</span> ('+q(rid)+', '+q(r.rule_name)+');');else ls.push('<span class="cm">-- '+r.rule_name+' — complementos</span>');
    r.routines.forEach(rt=>rt.features.filter(f=>f.status==='FALTANTE').forEach(f=>ls.push('<span class="kw">INSERT INTO</span> <span class="tb">SYS_RULES_FEATURES</span> (RL__ID, RL__ROTINA, RL__DESMDEF, RL__ACESSO) <span class="kw">VALUES</span> ('+q(rid)+', '+q(rt.routine)+', '+q(f.feature||'')+', '+q('1')+');')));
    if(r.source==='NOVO')r.routines.forEach(rt=>ls.push('<span class="kw">INSERT INTO</span> <span class="tb">SYS_RULES_TRANSACT</span> (RL__ID, RL__ROTINA, RL__DESROT) <span class="kw">VALUES</span> ('+q(rid)+', '+q(rt.routine)+', '+q((rt.description||'').slice(0,40))+');'));
    r.users.forEach(u=>ls.push('<span class="kw">INSERT INTO</span> <span class="tb">SYS_RULES_USR_RULES</span> (USER_ID, USR_RL_ID) <span class="kw">VALUES</span> ('+q(u.user_id||'')+', '+q(rid)+');'));ls.push('')}});
  d.forEach(r=>{{if(r.rule_id)ls.push('<span class="wn">UPDATE SYS_RULES_USR_RULES SET D_E_L_E_T_ = '+q('*')+' WHERE USR_RL_ID = '+q(r.rule_id)+'; -- '+r.rule_name+'</span>')}});
  ls.push('<span class="kw">COMMIT</span>');document.getElementById('sqlPrev').innerHTML=ls.join(String.fromCharCode(10));document.getElementById('sqlCount').textContent=t.length+' pend. | '+d.length+' del.';
}}
function q(v){{return String.fromCharCode(39)+String(v||'')+String.fromCharCode(39)}}
function genSQL(){{refreshSQL();st('SQL atualizado')}}
function downloadSQL(){{refreshSQL();let t=(document.getElementById('sqlPrev').textContent||'').replace(/<[^>]+>/g,'');let b=new Blob([t],{{type:'text/plain'}});let a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='delta.sql';a.click()}}
function saveJSON(){{let o={{rules:rules.filter(r=>!r._marked_for_delete),deleted_bindings:rules.filter(r=>r._marked_for_delete&&r.rule_id).map(r=>({{rule_name:r.rule_name,rule_id:r.rule_id}}))}};let b=new Blob([JSON.stringify(o)],{{type:'application/json'}});let a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='regras_ajustadas.json';a.click();st('Salvo')}}
function st(m){{let t=document.getElementById('toast');t.textContent=m;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),2000)}}
function esc(s){{let d=document.createElement('div');d.textContent=(s||'').toString();return d.innerHTML.split(String.fromCharCode(39)).join('&#39;')}}
window.onload=function(){{renderTree();refreshSQL()}};
</script>
</body>
</html>"""

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path
