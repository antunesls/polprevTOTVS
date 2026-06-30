import json
import urllib.request
import urllib.error
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

C = {
    "reset": "\033[0m",  "cyan": "\033[96m",
    "green": "\033[92m", "yellow": "\033[93m",
    "red": "\033[91m",   "dim": "\033[2m",
}

if os.name == "nt":
    os.system("")


def build_prompt(users_data):
    entries = []
    for u in users_data:
        routines_list = u.get("routines", [])
        routines_str = ", ".join(routines_list[:30])
        if len(routines_list) > 30:
            routines_str += f"... (+{len(routines_list) - 30})"
        dept = u.get("department", "")
        dept_str = f" | Departamento: {dept}" if dept else ""
        entries.append(
            f"Usuario: {u['user']}{dept_str}\n"
            f"Rotinas ({len(routines_list)}): {routines_str}"
        )

    users_block = "\n\n".join(entries)

    return f"""Voce e um analista de sistemas ERP Protheus (TOTVS).

Abaixo estao listados usuarios do sistema com suas respectivas rotinas (funcoes) acessiveis.
Cada rotina e um codigo como MATA010, FINA020, COMSV001, etc.

Sua tarefa:
1. Analise os padroes de rotinas entre usuarios de diferentes departamentos
2. Agrupe usuarios que compartilham conjuntos significativos de rotinas
3. Para cada grupo detectado, sugira um nome no formato P_CJ_{ROTULO} onde ROTULO
   e uma palavra curta (max 15 caracteres) que descreva a funcao do grupo.
   Exemplos: P_CJ_ESTOQUE, P_CJ_FINANCEIRO, P_CJ_FISCAL, P_CJ_COMPRAS
4. Usuarios que nao se encaixam em nenhum grupo devem ir em "unclustered"
5. Um usuario pode pertencer a mais de um grupo se fizer sentido

Usuarios e rotinas:
{users_block}

Retorne APENAS um JSON valido neste formato exato, sem texto adicional:
{{
  "clusters": [
    {{
      "name": "P_CJ_ESTOQUE",
      "reason": "Compartilham rotinas de controle de estoque e produtos",
      "users": ["usr005", "usr012"],
      "common_routines": ["MATA010", "MATA020"]
    }}
  ],
  "unclustered": ["usr099"]
}}"""


def call_openrouter(prompt):
    if not LLM_API_KEY or not LLM_BASE_URL:
        return None

    url = LLM_BASE_URL.rstrip("/") + "/chat/completions"

    payload = json.dumps({
        "model": LLM_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 4096,
    }).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LLM_API_KEY}",
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
        return None
    except Exception as e:
        print(f"  {C['red']}Erro ao consultar LLM: {e}{C['reset']}")
        return None


def extract_json(text):
    if not text:
        return None
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return None

    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


def suggest_clusters(users_data):
    G = C["green"]; CY = C["cyan"]; Y = C["yellow"]; R = C["reset"]; D = C["dim"]

    if not LLM_API_KEY:
        return None

    print(f"\n  {CY}Consultando LLM ({LLM_MODEL})...{R}")
    prompt = build_prompt(users_data)
    response_text = call_openrouter(prompt)

    if not response_text:
        return None

    result = extract_json(response_text)
    if not result:
        print(f"  {Y}LLM retornou formato invalido. Tentando fallback...{R}")
        return None

    clusters = result.get("clusters", [])
    unclustered = result.get("unclustered", [])

    print(f"  {G}LLM sugeriu {len(clusters)} clusters{R}")

    validated = []
    for c in clusters:
        name = (c.get("name") or "").strip().upper()
        if not name.startswith("P_CJ_"):
            name = f"P_CJ_{name}"
        if len(name) > 20:
            name = name[:20]

        validated.append({
            "name": name,
            "reason": c.get("reason", ""),
            "users": c.get("users", []),
            "common_routines": c.get("common_routines", []),
        })

    return {
        "clusters": validated,
        "unclustered": list(unclustered) if unclustered else [],
    }
