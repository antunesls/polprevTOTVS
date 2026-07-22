import html
import io
import json
import os
import re
from collections import defaultdict
from contextlib import redirect_stdout

from src.config import OUTPUT_DIR, SCHEMA_TABLES


METRIC_RE = re.compile(r"^(?P<name>[a-zA-Z_:][a-zA-Z0-9_:]*)\{(?P<labels>.*)\}\s+(?P<value>[-+0-9.eE]+)\s*$")
LABEL_RE = re.compile(r'([a-zA-Z_][a-zA-Z0-9_]*)="((?:[^"\\]|\\.)*)"')


def normalize_routine_code(value):
    text = str(value or "").strip().upper()
    if text.endswith("()"):
        text = text[:-2]
    return text.strip()


def normalize_user_code(value):
    return str(value or "").strip().upper()


def _parse_labels(raw_labels):
    labels = {}
    for match in LABEL_RE.finditer(raw_labels or ""):
        labels[match.group(1)] = match.group(2).replace('\\"', '"').replace('\\\\', '\\')
    return labels


def _int_calls(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def load_prometheus_metrics(metrics_path):
    routine_totals = {}
    routine_users = defaultdict(dict)

    with open(metrics_path, "r", encoding="utf-8-sig") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            match = METRIC_RE.match(line)
            if not match:
                continue

            metric_name = match.group("name")
            labels = _parse_labels(match.group("labels"))
            routine = normalize_routine_code(labels.get("routine"))
            if not routine:
                continue

            calls = _int_calls(match.group("value"))
            module = str(labels.get("module") or "").strip()

            if metric_name == "protheus_routine_calls_total":
                item = routine_totals.setdefault(routine, {"routine": routine, "module": module, "calls": 0})
                item["calls"] += calls
                if module and not item.get("module"):
                    item["module"] = module
            elif metric_name == "protheus_routine_user_calls_total":
                user = normalize_user_code(labels.get("user"))
                if not user:
                    continue
                user_item = routine_users[routine].setdefault(
                    user,
                    {
                        "user": user,
                        "user_name": str(labels.get("user_name") or "").strip(),
                        "module": module,
                        "calls": 0,
                    },
                )
                user_item["calls"] += calls
                if module and not user_item.get("module"):
                    user_item["module"] = module

    return {
        "routine_totals": routine_totals,
        "routine_users": {routine: dict(users) for routine, users in routine_users.items()},
    }


def routine_call_counts(metrics):
    counts = defaultdict(int)
    for routine, item in (metrics or {}).get("routine_totals", {}).items():
        counts[normalize_routine_code(routine)] += _int_calls(item.get("calls"))
    for routine, users in (metrics or {}).get("routine_users", {}).items():
        routine_code = normalize_routine_code(routine)
        if counts.get(routine_code, 0) > 0:
            continue
        counts[routine_code] += sum(_int_calls(user_info.get("calls")) for user_info in (users or {}).values())
    return dict(counts)


def filter_reports_by_telemetry(reports, metrics_path=None, metrics=None, min_calls=1):
    if metrics is None and metrics_path:
        metrics = load_prometheus_metrics(metrics_path)
    if metrics is None:
        return list(reports or []), {
            "enabled": False,
            "min_calls": int(min_calls),
            "reports": len(reports or []),
            "removed_routines": 0,
        }

    calls_by_routine = routine_call_counts(metrics)
    filtered_reports = []
    removed_total = 0

    for original_report in reports or []:
        kept = []
        removed = []
        for routine_info in original_report.get("routines_summary", []) or []:
            routine = normalize_routine_code(routine_info.get("routine"))
            calls = calls_by_routine.get(routine, 0)
            routine_copy = dict(routine_info)
            if calls >= int(min_calls):
                routine_copy["telemetry_calls"] = calls
                kept.append(routine_copy)
            else:
                removed.append(routine)
        filtered_report = {key: value for key, value in original_report.items() if key != "routines_summary"}
        filtered_report["routines_summary"] = kept
        filtered_report["total_routines"] = len(kept)
        filtered_report["_telemetry_filter"] = {
            "enabled": True,
            "min_calls": int(min_calls),
            "removed_count": len(removed),
            "removed_routines": removed,
        }
        removed_total += len(removed)
        filtered_reports.append(filtered_report)

    return filtered_reports, {
        "enabled": True,
        "min_calls": int(min_calls),
        "reports": len(filtered_reports),
        "removed_routines": removed_total,
    }


def _allowed_access_value(value):
    return str(value or "").strip().upper() in ("PERMITIDO", "SEM_REGRA")


def _build_allowed_access(reports):
    allowed_by_user = defaultdict(dict)
    allowed_by_routine = defaultdict(dict)

    for report in reports or []:
        user = normalize_user_code(report.get("user"))
        if not user:
            continue
        user_name = str(report.get("user_name") or "").strip()
        user_depto = str(report.get("user_depto") or "").strip()
        for routine_info in report.get("routines_summary", []) or []:
            routine = normalize_routine_code(routine_info.get("routine"))
            if not routine or not _allowed_access_value(routine_info.get("effective_access")):
                continue
            item = {
                "routine": routine,
                "description": str(routine_info.get("description") or "").strip(),
                "user": user,
                "user_name": user_name,
                "user_depto": user_depto,
                "effective_access": str(routine_info.get("effective_access") or "").strip(),
            }
            allowed_by_user[user][routine] = item
            allowed_by_routine[routine][user] = item

    return allowed_by_user, allowed_by_routine


def analyze_telemetry(metrics_path, reports=None, output_json_path=None, output_html_path=None):
    metrics = load_prometheus_metrics(metrics_path)
    allowed_by_user, allowed_by_routine = _build_allowed_access(reports or [])

    routine_totals = metrics["routine_totals"]
    routine_users = metrics["routine_users"]
    used_routines = set(routine_totals.keys()) | set(routine_users.keys())

    top_routines = sorted(routine_totals.values(), key=lambda item: (-item["calls"], item["routine"]))
    top_users_by_routine = {}
    for routine, users in routine_users.items():
        top_users_by_routine[routine] = sorted(users.values(), key=lambda item: (-item["calls"], item["user"]))

    unused_allowed_routines = []
    for routine, users in allowed_by_routine.items():
        if routine in used_routines:
            continue
        sample = next(iter(users.values()))
        unused_allowed_routines.append(
            {
                "routine": routine,
                "description": sample.get("description", ""),
                "allowed_users": sorted(users.keys()),
                "allowed_users_count": len(users),
            }
        )
    unused_allowed_routines.sort(key=lambda item: (-item["allowed_users_count"], item["routine"]))

    used_without_effective_access = []
    for routine, users in routine_users.items():
        for user, user_usage in users.items():
            if routine in allowed_by_user.get(user, {}):
                continue
            used_without_effective_access.append(
                {
                    "routine": routine,
                    "module": user_usage.get("module", ""),
                    "user": user,
                    "user_name": user_usage.get("user_name", ""),
                    "calls": user_usage.get("calls", 0),
                }
            )
    used_without_effective_access.sort(key=lambda item: (-item["calls"], item["routine"], item["user"]))

    result = {
        "summary": {
            "metrics_file": metrics_path,
            "reports_count": len(reports or []),
            "routines_used": len(used_routines),
            "routine_user_pairs_used": sum(len(users) for users in routine_users.values()),
            "allowed_routines": len(allowed_by_routine),
            "unused_allowed_routines": len(unused_allowed_routines),
            "used_without_effective_access": len(used_without_effective_access),
        },
        "top_routines": top_routines,
        "top_users_by_routine": top_users_by_routine,
        "unused_allowed_routines": unused_allowed_routines,
        "used_without_effective_access": used_without_effective_access,
    }

    if output_json_path:
        os.makedirs(os.path.dirname(output_json_path) or ".", exist_ok=True)
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

    if output_html_path:
        generate_telemetry_html(result, output_html_path)

    return result


def build_reports_from_export(export_json_path, progress=None):
    from src.data_importer import import_and_set_offline
    from src.database import get_connection
    from src.discovery import discover_columns_for_tables
    from src.user_mapper import UserMapper

    if not import_and_set_offline(export_json_path):
        return []

    with get_connection() as conn:
        schema = discover_columns_for_tables(SCHEMA_TABLES, conn)
        mapper = UserMapper(schema, conn)
        users = mapper.list_non_blocked_users()
        reports = []
        for index, user in enumerate(users, start=1):
            login = str(user.get("login") or "").strip()
            if not login:
                continue
            if progress:
                progress(index, len(users), login)
            with redirect_stdout(io.StringIO()):
                report = mapper.build_full_report(login)
            if report:
                reports.append(report)
        return reports


def analyze_export_telemetry(metrics_path, export_json_path, output_dir=OUTPUT_DIR, progress=None):
    reports = build_reports_from_export(export_json_path, progress=progress)
    output_json_path = os.path.join(output_dir, "telemetry_analysis.json")
    output_html_path = os.path.join(output_dir, "telemetry_analysis.html")
    return analyze_telemetry(metrics_path, reports=reports, output_json_path=output_json_path, output_html_path=output_html_path)


def _table_rows(items, columns, limit=None):
    rows = []
    for item in (items or [])[:limit]:
        cells = "".join(f"<td>{html.escape(str(item.get(col, '')))}</td>" for col in columns)
        rows.append(f"<tr>{cells}</tr>")
    return "\n".join(rows) or f"<tr><td colspan=\"{len(columns)}\">Nenhum registro encontrado</td></tr>"


def generate_telemetry_html(result, output_path):
    summary = result.get("summary", {})
    top_users_rows = []
    for routine, users in result.get("top_users_by_routine", {}).items():
        for user in users[:5]:
            top_users_rows.append({"routine": routine, **user})

    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Analise de Telemetria Protheus</title>
<style>
body {{ font-family: Segoe UI, Arial, sans-serif; background: #111827; color: #e5e7eb; margin: 0; padding: 24px; }}
h1 {{ margin-bottom: 4px; }}
.muted {{ color: #9ca3af; }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin: 20px 0; }}
.card {{ background: #1f2937; border: 1px solid #374151; border-radius: 10px; padding: 16px; }}
.card strong {{ display: block; font-size: 28px; color: #38bdf8; }}
table {{ width: 100%; border-collapse: collapse; margin: 14px 0 26px; background: #1f2937; border-radius: 10px; overflow: hidden; }}
th, td {{ padding: 9px 10px; border-bottom: 1px solid #374151; text-align: left; font-size: 13px; }}
th {{ background: #0f172a; color: #93c5fd; }}
tr:hover {{ background: #263244; }}
</style>
</head>
<body>
<h1>Analise de Telemetria Protheus</h1>
<div class="muted">Arquivo: {html.escape(str(summary.get('metrics_file', '')))}</div>
<div class="cards">
  <div class="card"><span>Rotinas usadas</span><strong>{summary.get('routines_used', 0)}</strong></div>
  <div class="card"><span>Usuarios x rotinas</span><strong>{summary.get('routine_user_pairs_used', 0)}</strong></div>
  <div class="card"><span>Rotinas liberadas</span><strong>{summary.get('allowed_routines', 0)}</strong></div>
  <div class="card"><span>Liberadas sem uso</span><strong>{summary.get('unused_allowed_routines', 0)}</strong></div>
  <div class="card"><span>Uso sem acesso efetivo</span><strong>{summary.get('used_without_effective_access', 0)}</strong></div>
</div>

<h2>Top rotinas</h2>
<table><thead><tr><th>routine</th><th>module</th><th>calls</th></tr></thead><tbody>
{_table_rows(result.get('top_routines', []), ['routine', 'module', 'calls'], limit=50)}
</tbody></table>

<h2>Top usuarios por rotina</h2>
<table><thead><tr><th>routine</th><th>user</th><th>user_name</th><th>module</th><th>calls</th></tr></thead><tbody>
{_table_rows(top_users_rows, ['routine', 'user', 'user_name', 'module', 'calls'], limit=200)}
</tbody></table>

<h2>Candidatas a descarte na criacao de regras</h2>
<table><thead><tr><th>routine</th><th>description</th><th>allowed_users_count</th><th>allowed_users</th></tr></thead><tbody>
{_table_rows(result.get('unused_allowed_routines', []), ['routine', 'description', 'allowed_users_count', 'allowed_users'], limit=200)}
</tbody></table>

<h2>Uso sem acesso efetivo mapeado</h2>
<table><thead><tr><th>routine</th><th>module</th><th>user</th><th>user_name</th><th>calls</th></tr></thead><tbody>
{_table_rows(result.get('used_without_effective_access', []), ['routine', 'module', 'user', 'user_name', 'calls'], limit=200)}
</tbody></table>
</body>
</html>"""

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    return output_path
