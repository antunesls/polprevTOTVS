import json
import re
import urllib.request
import urllib.error
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import src.config as llm_cfg
from src.tier3 import routine_code

C = {
    "reset": "\033[0m",  "cyan": "\033[96m",
    "green": "\033[92m", "yellow": "\033[93m",
    "red": "\033[91m",   "dim": "\033[2m",
}

MAX_PROMPT_ROUTINES = None
RETRY_PROMPT_ROUTINES = 150
MAX_ROUTINE_DESC_LEN = 60

_UUID_PATTERN = re.compile(r'^([A-Za-z0-9]+)_([A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12})$')

if os.name == "nt":
    os.system("")


def build_prompt(users_data, max_routines=MAX_PROMPT_ROUTINES, min_users=None):
    routines_map = {}
    for u in users_data:
        for routine in u.get("routines", []):
            code = routine_code(routine)
            if not code:
                continue
            desc = ""
            permissions = []
            if isinstance(routine, dict):
                desc = str(routine.get("description") or "").strip()
                permissions = sorted(str(p).strip() for p in routine.get("permissions", []) if str(p).strip())
            elif " - " in str(routine):
                desc = str(routine).split(" - ", 1)[1].strip()
            if code not in routines_map:
                routines_map[code] = {"desc": desc, "users": 0, "profiles": {}}
            elif desc and not routines_map[code]["desc"]:
                routines_map[code]["desc"] = desc
            routines_map[code]["users"] += 1
            profile_key = tuple(permissions)
            routines_map[code]["profiles"][profile_key] = routines_map[code]["profiles"].get(profile_key, 0) + 1

    prefix_groups = {}
    residue = {}
    for code, info in routines_map.items():
        m = _UUID_PATTERN.match(code)
        if m:
            prefix_key = m.group(1) + "_*"
            if prefix_key not in prefix_groups:
                prefix_groups[prefix_key] = {"codes": [], "users": 0, "profiles": {}}
            prefix_groups[prefix_key]["codes"].append(code)
            prefix_groups[prefix_key]["users"] += info["users"]
            for profile, count in info.get("profiles", {}).items():
                prefix_groups[prefix_key]["profiles"][profile] = prefix_groups[prefix_key]["profiles"].get(profile, 0) + count
            desc_value = info.get("desc", "").strip()
            if desc_value and not prefix_groups[prefix_key].get("desc"):
                prefix_groups[prefix_key]["desc"] = desc_value
        else:
            residue[code] = info

    for group_name, group_info in prefix_groups.items():
        n = len(group_info["codes"])
        group_info["desc"] = f"({n} variacoes) {group_info.get('desc', '')}"
        residue[group_name] = group_info

    routines_map = residue
    total_all_routines = len(routines_map)

    if min_users is not None and min_users > 1:
        routines_map = {code: info for code, info in routines_map.items() if info["users"] >= min_users}

    sorted_routines = sorted(
        routines_map.items(),
        key=lambda item: (-item[1]["users"], item[0]),
    )
    total_routines = len(sorted_routines)
    limited_routines = sorted_routines if max_routines is None else sorted_routines[:max_routines]

    entries = []
    for code, info in limited_routines:
        desc_value = info["desc"][:MAX_ROUTINE_DESC_LEN].strip()
        desc = f" - {desc_value}" if desc_value else ""
        entries.append(f"{code}{desc} | usuarios_com_acesso: {info['users']}")
        profiles = []
        for profile, count in sorted(info.get("profiles", {}).items(), key=lambda item: (-item[1], item[0]))[:4]:
            label = ", ".join(profile) if profile else "sem permissao explicita"
            profiles.append(f"{label}: {count} usuarios")
        if profiles:
            entries.append("  Perfis de permissao: " + " | ".join(profiles))

    routines_block = "\n".join(entries)
    limit_notice = ""
    if min_users is not None and min_users > 1:
        limit_notice = (
            f"\nCatalogo filtrado: apenas rotinas com >= {min_users} usuarios "
            f"({total_routines} de {total_all_routines} rotinas)."
        )
    if max_routines is not None and total_routines > max_routines:
        limit_notice += (
            f"\nCatalogo limitado as {max_routines} rotinas mais recorrentes "
            f"de um total de {total_routines}, para respeitar o limite de contexto da LLM."
        )

    prompt = f"""Voce e um analista de sistemas ERP Protheus (TOTVS) especializado em privilegios por camada organizacional.

Catalogo de rotinas do sistema com codigo, descricao e quantidade de usuarios que acessam cada rotina.{limit_notice}
Cada rotina e um codigo como MATA010, FINA020, COMSV001, etc.

Sua tarefa: montar CONJUNTOS FUNCIONAIS DE ROTINAS relacionadas entre si.
Este e o TERCEIRO NIVEL da camada organizacional: pacotes reutilizaveis de rotinas por dominio funcional.

DICA DE CLASSIFICACAO POR PREFIXO:
O prefixo da rotina (primeiros 4 caracteres) indica dominio funcional e modulo. Use isso como forte evidencia ao agrupar rotinas, especialmente quando a descricao for curta ou generica.
- Prefixos terminados em "R" geralmente indicam RELATORIOS (ex: FINR = relatorios financeiros, MATR = relatorios de materiais/compras/estoque, FISR = relatorios fiscais, CTBR = relatorios contabeis).
- Prefixos terminados em "A" geralmente indicam CADASTROS (ex: MATA = cadastros de materiais, FINA = cadastros financeiros).
- Prefixos terminados em "C" geralmente indicam CONSULTAS (ex: MATC = consultas de materiais).
- Prefixos terminados em "M" geralmente indicam MOVIMENTACOES (ex: MATM = movimentacoes de materiais).
- Prefixos terminados em "E" geralmente indicam ENTRADAS.
Rotinas com o mesmo prefixo pertencem ao mesmo modulo e tem alta afinidade funcional entre si.

REGRAS:
1. Priorize o assunto/objetivo da rotina e sua descricao. A quantidade de usuarios e apenas evidencia auxiliar, nao o criterio principal.
2. Para cada conjunto, sugira um nome no formato P_CJ_{{ROTULO}} baseado no DOMINIO FUNCIONAL das rotinas.
   Ex: P_CJ_ETIQUETAS, P_CJ_SEPARACAO_PEDIDO, P_CJ_CADASTRO_PRODUTO, P_CJ_RELATORIOS_FISCAIS.
3. Cada conjunto deve ter NO MINIMO 2 rotinas relacionadas. Nao gere conjunto com 1 rotina.
4. Uma mesma rotina PODE aparecer em MAIS DE UM conjunto, desde que esteja relacionada ao dominio funcional de ambos.
5. Nao crie conjuntos genericos demais como P_CJ_DIVERSOS ou P_CJ_GERAL.
6. Em "routines", liste codigos de rotinas reais da lista abaixo. NAO invente codigos.
7. NAO crie conjuntos baseados em departamentos, cargos ou areas organizacionais. Exemplos proibidos: P_CJ_PCP, P_CJ_COMPRAS, P_CJ_QUALIDADE, P_CJ_CONTROLADORIA, P_CJ_FERRAMENTARIA.
8. NAO use justificativas como "usuarios do departamento" ou "rotinas do departamento".
9. Quando uma permissao for relevante, responda a rotina como objeto: {{"code":"MATA010","permissions":["Visualizar","Alterar"]}}.
10. Permissoes maiores cobrem menores: quem tem Visualizar e Alterar cobre conjunto que exige apenas Visualizar.
11. O campo "users" deve ser uma lista vazia; o sistema recalculara os usuarios automaticamente.
12. No maximo 12 conjuntos no total.
13. No maximo 20 rotinas por conjunto.
14. Prefira JSON compacto e encerre a resposta logo apos fechar o objeto final.

Catalogo de rotinas:
{routines_block}

IMPORTANTE: Responda EXCLUSIVAMENTE com JSON puro, sem markdown:

{{
  "clusters": [
    {{
      "name": "P_CJ_ETIQUETAS",
      "reason": "Rotinas relacionadas a impressao, reimpressao e manutencao de etiquetas",
      "routines": [{{"code": "ETQ001", "permissions": ["Visualizar"]}}, {{"code": "ETQ002", "permissions": ["Visualizar", "Alterar"]}}],
      "users": []
    }}
  ],
  "unclustered": []
}}"""
    return {"prompt": prompt, "prefix_groups": prefix_groups}


def build_department_prompt(department_names):
    entries = "\n".join(f"- {name}" for name in department_names if str(name).strip())
    return f"""Voce e um analista de dados organizacionais.

Sua tarefa: identificar nomes de departamentos que representam o MESMO departamento, mas foram digitados com pequenas variacoes.

REGRAS:
1. Una apenas departamentos com alta confianca de equivalencia.
2. Considere variacoes de acento, espacos, siglas e nome extenso quando forem claramente o mesmo departamento.
3. NAO una departamentos apenas por semelhanca superficial.
4. Se houver duvida, nao una.
5. Use confianca de 0 a 1.
6. Responda apenas grupos com confianca alta o suficiente para automacao.
7. O campo aliases deve listar nomes exatamente como vieram da lista.

Departamentos:
{entries}

Responda EXCLUSIVAMENTE com JSON puro, sem markdown:

{{
  "groups": [
    {{
      "canonical": "RECURSOS HUMANOS",
      "aliases": ["RH", "RECURSOS HUMANOS"],
      "confidence": 0.95,
      "reason": "Sigla e nome extenso do mesmo departamento"
    }}
  ]
}}"""


def call_openrouter(prompt):
    if not llm_cfg.LLM_API_KEY or not llm_cfg.LLM_BASE_URL:
        return None

    url = llm_cfg.LLM_BASE_URL.rstrip("/") + "/chat/completions"

    payload = json.dumps({
        "model": llm_cfg.LLM_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 16384,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {llm_cfg.LLM_API_KEY}",
    }

    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            content = body["choices"][0]["message"]["content"]
            return content
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"  {C['red']}Erro HTTP {e.code}: {err_body[:300]}{C['reset']}")
        if e.code == 400 and "maximum context length" in err_body.lower():
            print(f"  {C['yellow']}A lista enviada para a LLM excedeu o contexto do modelo.{C['reset']}")
            print(f"  {C['yellow']}Reduza a quantidade de usuarios mapeados ou aumente LLM_MIN_ROUTINE_USERS para filtrar mais rotinas.{C['reset']}")
        return None
    except Exception as e:
        print(f"  {C['red']}Erro ao consultar LLM: {e}{C['reset']}")
        return None


def _strip_markdown_fences(text):
    lines = text.split("\n")
    if not lines:
        return text
    first = lines[0].strip()
    if first.startswith("```"):
        lines = lines[1:]
    last = lines[-1].strip()
    if last == "```":
        lines = lines[:-1]
    return "\n".join(lines)


def _find_json_bounds(text):
    start = text.find("{")
    if start == -1:
        return None, None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return start, i + 1
    return start, len(text)


def _repair_json(json_str):
    try:
        return json.loads(json_str), json_str
    except json.JSONDecodeError:
        pass

    repaired = re.sub(r",\s*([}\]])", r"\1", json_str)

    open_braces = repaired.count("{") - repaired.count("}")
    open_brackets = repaired.count("[") - repaired.count("]")

    if open_braces > 0 or open_brackets > 0:
        in_string = False
        escape = False
        for i in range(len(repaired) - 1, -1, -1):
            ch = repaired[i]
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch in "{[:":
                break
            if ch == ",":
                repaired = repaired[:i] + repaired[i + 1:]
                break

        repaired += "]" * open_brackets
        repaired += "}" * open_braces

    return json.loads(repaired), repaired


def extract_json(text):
    if not text:
        return None
    text = _strip_markdown_fences(text.strip())

    start, end = _find_json_bounds(text)
    if start is None:
        return None

    result = _try_parse(text[start:end])
    if isinstance(result, dict) and "clusters" in result:
        return result

    candidates = _find_top_level_jsons(text)
    for candidate in reversed(candidates):
        result = _try_parse(candidate)
        if isinstance(result, dict) and "clusters" in result:
            return result

    if result is not None:
        return result
    for candidate in reversed(candidates):
        result = _try_parse(candidate)
        if result is not None:
            return result

    return None


def _find_top_level_jsons(text):
    candidates = []
    lines = text.split("\n")
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("{"):
            block = "\n".join(lines[i:])
            s, e = _find_json_bounds(block)
            if s is not None:
                candidates.append(block[s:e])
    return candidates


def _try_parse(json_str):
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass
    try:
        result, _ = _repair_json(json_str)
        return result
    except (json.JSONDecodeError, ValueError):
        return None


def _expand_prefix_codes(result, prefix_groups):
    if not prefix_groups or not result:
        return
    for cluster in result.get("clusters", []) or []:
        routines = cluster.get("routines", [])
        if not routines:
            continue
        expanded = []
        for raw in routines:
            code = routine_code(raw)
            group_info = prefix_groups.get(code, {})
            if group_info and "codes" in group_info:
                for orig_code in group_info["codes"]:
                    expanded.append(orig_code)
            else:
                expanded.append(raw)
        cluster["routines"] = expanded


def suggest_clusters(users_data):
    G = C["green"]; CY = C["cyan"]; Y = C["yellow"]; R = C["reset"]; D = C["dim"]; RD = C["red"]

    if not llm_cfg.LLM_API_KEY:
        return None

    print(f"\n  {CY}Consultando LLM ({llm_cfg.LLM_MODEL})...{R}")
    unique_routines = {
        routine_code(r)
        for user in users_data
        for r in user.get("routines", [])
        if routine_code(r)
    }

    routines_user_count = {}
    for user in users_data:
        for r in user.get("routines", []):
            code = routine_code(r)
            if code:
                routines_user_count[code] = routines_user_count.get(code, 0) + 1
    min_users = llm_cfg.LLM_MIN_ROUTINE_USERS
    filtered_routine_count = sum(1 for c in routines_user_count.values() if c >= min_users)

    response_text = None
    result = None
    prefix_groups = {}
    attempt_limits = (MAX_PROMPT_ROUTINES, MAX_PROMPT_ROUTINES, MAX_PROMPT_ROUTINES, RETRY_PROMPT_ROUTINES)
    for attempt_idx, prompt_limit in enumerate(attempt_limits, 1):
        sent = filtered_routine_count if prompt_limit is None else min(prompt_limit, filtered_routine_count)
        print(f"  {D}Entrada: {len(users_data)} usuarios | {len(unique_routines)} rotinas unicas | >= {min_users} usuarios: {filtered_routine_count} | catalogo enviado: {sent}{R}")
        print(f"  {D}Tentativa {attempt_idx}/{len(attempt_limits)}{R}")
        prompt_result = build_prompt(users_data, max_routines=prompt_limit, min_users=min_users)
        prefix_groups = prompt_result.get("prefix_groups", {})
        response_text = call_openrouter(prompt_result["prompt"])

        is_last = (attempt_idx == len(attempt_limits))
        is_reduced_next = (attempt_idx < len(attempt_limits) and attempt_limits[attempt_idx] is not None and (attempt_limits[attempt_idx - 1] is None or attempt_limits[attempt_idx] < attempt_limits[attempt_idx - 1]))

        if not response_text:
            if is_last:
                return None
            if is_reduced_next:
                print(f"  {Y}LLM nao retornou resposta. Tentando novamente com catalogo reduzido...{R}")
            else:
                print(f"  {Y}LLM nao retornou resposta. Tentando novamente...{R}")
            continue

        if not response_text.strip().endswith("}"):
            print(f"  {Y}AVISO: Resposta da LLM parece truncada (nao termina com '}}').{R}")
            print(f"  {Y}       Isso ocorre quando max_tokens e insuficiente para tantos usuarios.{R}")
            print(f"  {D}Resposta (ultimos 200 chars): ...{response_text.strip()[-200:]}{R}")
            if not is_last:
                if is_reduced_next:
                    print(f"  {Y}Tentando novamente com catalogo reduzido ({RETRY_PROMPT_ROUTINES} rotinas)...{R}")
                else:
                    print(f"  {Y}Tentando novamente...{R}")
                continue

        result = extract_json(response_text)
        if result:
            break
        if not is_last:
            if is_reduced_next:
                print(f"  {Y}LLM retornou JSON invalido. Tentando novamente com catalogo reduzido...{R}")
            else:
                print(f"  {Y}LLM retornou JSON invalido. Tentando novamente...{R}")

    if not result:
        print(f"  {Y}LLM retornou formato JSON invalido.{R}")
        print(f"  {D}Resposta bruta (primeiros 500 chars):{R}")
        print(f"  {D}{response_text[:500]}{R}")

        result = _fallback_regex_extract(response_text, users_data)
        if result:
            print(f"  {G}Fallback regex extraiu {len(result.get('clusters', []))} conjuntos.{R}")
        else:
            print(f"  {RD}Fallback regex tambem falhou. Use modo manual (Jaccard).{R}")
            return None

    _expand_prefix_codes(result, prefix_groups)

    clusters = result.get("clusters", [])

    user_routines = {}
    valid_routines = set()
    for u in users_data:
        codes = set(routine_code(r) for r in u.get("routines", []) if routine_code(r))
        user_routines[u["user"]] = codes
        valid_routines.update(codes)

    print(f"  {G}LLM sugeriu {len(clusters)} conjuntos funcionais{R}")

    if len(clusters) == 0 and response_text:
        print(f"  {Y}DEBUG: Resposta bruta (primeiros 800 chars):{R}")
        print(f"  {D}{response_text[:800]}{R}")

    validated = []
    for c in clusters:
        name = (c.get("name") or "").strip().upper()
        if not name.startswith("P_CJ_"):
            name = f"P_CJ_{name}"
        if len(name) > 20:
            name = name[:20]

        routines = []
        routine_codes = set()
        for raw in c.get("routines", c.get("common_routines", [])):
            code = routine_code(raw)
            if code and code in valid_routines and code not in routine_codes:
                routine_codes.add(code)
                permissions = []
                if isinstance(raw, dict):
                    permissions = sorted(str(p).strip() for p in raw.get("permissions", []) if str(p).strip())
                routines.append({"code": code, "permissions": permissions} if permissions else code)

        if len(routine_codes) < 2:
            print(f"  {Y}[ALERTA] Conjunto {name} ignorado: menos de 2 rotinas validas.{R}")
            continue

        routine_set = routine_codes
        users = sorted(u for u, codes in user_routines.items() if codes & routine_set)

        validated.append({
            "name": name,
            "reason": c.get("reason", ""),
            "routines": routines,
            "users": users,
        })

    return {
        "clusters": validated,
        "unclustered": [],
    }


def suggest_department_aliases(department_names):
    if not llm_cfg.LLM_API_KEY:
        return None

    names = []
    seen = set()
    for name in department_names or []:
        value = str(name or "").strip()
        if value and value not in seen:
            names.append(value)
            seen.add(value)

    if len(names) < 2:
        return {"groups": []}

    print(f"\n  {C['cyan']}Consultando LLM para equivalencia de departamentos ({llm_cfg.LLM_MODEL})...{C['reset']}")
    response_text = call_openrouter(build_department_prompt(names))
    if not response_text:
        return None

    result = extract_json(response_text)
    if not isinstance(result, dict):
        print(f"  {C['yellow']}LLM retornou equivalencias de departamentos em formato invalido.{C['reset']}")
        return None

    groups = []
    valid_names = set(names)
    for group in result.get("groups", []) or []:
        canonical = str(group.get("canonical") or "").strip()
        aliases = []
        for alias in group.get("aliases", []) or []:
            alias_value = str(alias or "").strip()
            if alias_value and alias_value in valid_names and alias_value not in aliases:
                aliases.append(alias_value)
        if canonical and aliases:
            groups.append({
                "canonical": canonical,
                "aliases": aliases,
                "confidence": group.get("confidence", 0),
                "reason": group.get("reason", ""),
            })

    return {"groups": groups}


def _fallback_regex_extract(text, users_data):
    user_set = {u["user"] for u in users_data}
    result = {"clusters": [], "unclustered": []}

    patterns = [
        r'\{[^{}]*?"name"\s*:\s*"([^"]+)".*?"routines"\s*:\s*\[(.*?)\].*?"users"\s*:\s*\[(.*?)\].*?\}',
        r'"name"\s*:\s*"([^"]+)".*?"routines"\s*:\s*\[(.*?)\].*?"users"\s*:\s*\[(.*?)\]',
    ]

    found_users = set()
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.DOTALL):
            name = match.group(1).strip().upper()
            routines_str = match.group(2)
            users_str = match.group(3)
            users = re.findall(r'"([^"]+)"', users_str)
            valid_users = [u for u in users if u in user_set]
            routines = _extract_routines_from_fallback(routines_str)
            if valid_users or routines:
                result["clusters"].append({
                    "name": name if name.startswith("P_CJ_") else f"P_CJ_{name}",
                    "reason": "",
                    "users": valid_users,
                    "common_routines": routines,
                })
                found_users.update(valid_users)
        if result["clusters"]:
            break

    result["unclustered"] = list(user_set - found_users)
    return result if result["clusters"] else None


def _extract_routines_from_fallback(routines_str):
    routines = []
    for code in re.findall(r'"code"\s*:\s*"([^"]+)"', routines_str):
        normalized = routine_code(code)
        if normalized and normalized not in routines:
            routines.append(normalized)
    for code in re.findall(r'"([A-Z0-9#_]+)"', routines_str):
        normalized = routine_code(code)
        if normalized and normalized not in routines:
            routines.append(normalized)
    return routines
