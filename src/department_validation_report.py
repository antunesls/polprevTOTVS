import os


def _escape_html(value):
    text = str(value or "")
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _slug_department(value):
    text = str(value or "SEM_DEPARTAMENTO").strip() or "SEM_DEPARTAMENTO"
    invalid = '<>:"/\\|?*'
    for char in invalid:
        text = text.replace(char, "_")
    return text.upper()


def _allowed_routines(report):
    has_group_default = any(
        str(group.get("group_id") or "").strip() == "*" or str(group.get("group_name") or "").strip() == "*"
        for group in report.get("groups", [])
    )

    routines = []
    for routine in report.get("routines_summary", []):
        effective_access = str(routine.get("effective_access") or "").strip().upper()
        in_menu = bool(routine.get("in_menu"))
        disabled_by_acbrowse = bool(routine.get("disabled_by_acbrowse"))

        allowed = (effective_access == "PERMITIDO")
        if not allowed and not has_group_default:
            allowed = effective_access == "SEM_REGRA" and in_menu and not disabled_by_acbrowse

        if not allowed:
            continue

        permissions = []
        for name, info in (routine.get("features") or {}).items():
            if str((info or {}).get("access") or "").strip().upper() == "PERMITIDO":
                permissions.append(str(name).strip())
        if not permissions:
            available_ops = []
            unavailable_count = 0
            browse_permissions = routine.get("browse_permissions", []) or []
            browse_names = {
                1: "Pesquisar",
                2: "Visualizar",
                3: "Incluir",
                4: "Alterar",
                5: "Excluir",
                6: "Cod.Barra",
                7: "Copiar",
                8: "Retornar",
                9: "Prep.Doc.Saida",
                10: "Extra",
            }
            for item in browse_permissions:
                menu_oper = int(item.get("menu_oper") or 0)
                if item.get("available"):
                    if menu_oper in browse_names:
                        available_ops.append(browse_names[menu_oper])
                else:
                    unavailable_count += 1
            if available_ops and unavailable_count > 0:
                permissions = available_ops
        if not permissions:
            permissions.append("Acesso a rotina")
        routines.append({
            "routine": str(routine.get("routine") or "").strip(),
            "description": str(routine.get("description") or "").strip(),
            "menu_name": str(routine.get("menu_name") or "").strip(),
            "module": str(routine.get("module") or "").strip(),
            "permissions": permissions,
        })
    return routines


def _grouped_reports(reports):
    grouped = {}
    for report in reports or []:
        dept = str(report.get("user_depto") or "").strip() or "SEM_DEPARTAMENTO"
        grouped.setdefault(dept, []).append(report)
    return grouped


def _render_user_page(report):
    allowed = _allowed_routines(report)
    groups = [str(group.get("group_name") or group.get("group_id") or "").strip() for group in report.get("groups", []) if str(group.get("group_name") or group.get("group_id") or "").strip()]
    access_codes = []
    for item in report.get("access_codes", []):
        code = str(item.get("code") or "").strip()
        if not code:
            continue
        desc = str(item.get("description") or "").strip()
        access_codes.append(f"{code} - {desc}" if desc else code)

    header = [
        f"<h2>{_escape_html(report.get('user_name') or report.get('user') or '')}</h2>",
        f"<div class=\"meta\"><strong>Login:</strong> {_escape_html(report.get('user') or '')}</div>",
        f"<div class=\"meta\"><strong>Departamento:</strong> {_escape_html(report.get('user_depto') or 'SEM_DEPARTAMENTO')}</div>",
        f"<div class=\"meta\"><strong>Grupos:</strong> {_escape_html(', '.join(groups) if groups else 'Nenhum grupo informado')}</div>",
        f"<div class=\"meta\"><strong>Codigos SYS_USR_ACCESS:</strong> {_escape_html(', '.join(access_codes) if access_codes else 'Nenhum codigo ativo')}</div>",
        f"<div class=\"meta\"><strong>Rotinas liberadas:</strong> {len(allowed)}</div>",
    ]

    if not allowed:
        body = '<div class="empty">Nenhuma permissao liberada encontrada</div>'
    else:
        rows = []
        for routine in allowed:
            rows.append(
                "<tr>"
                f"<td>{_escape_html(routine['routine'])}</td>"
                f"<td>{_escape_html(routine['description'])}</td>"
                f"<td>{_escape_html(', '.join(routine['permissions']))}</td>"
                f"<td>{_escape_html(routine['menu_name'])}</td>"
                f"<td>{_escape_html(routine['module'])}</td>"
                "</tr>"
            )
        body = (
            "<table><thead><tr><th>Rotina</th><th>Descricao</th><th>Permissoes</th><th>Menu</th><th>Modulo</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>"
        )

    return f"<section class=\"user-page\">{''.join(header)}{body}</section>"


def _render_department_html(department, reports, empresa_name=""):
    total_allowed = sum(len(_allowed_routines(report)) for report in reports)
    user_pages = "".join(_render_user_page(report) for report in sorted(reports, key=lambda item: str(item.get("user_name") or item.get("user") or "").upper()))
    title = f"RELATORIO DE VALIDACAO - {department}"
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_escape_html(title)}</title>
<style>
* {{ box-sizing: border-box; }}
body {{ font-family: Arial, sans-serif; color: #222; margin: 0; background: #f5f6f8; }}
.cover {{ padding: 32px; background: #fff; border-bottom: 1px solid #d0d7de; }}
.cover h1 {{ margin: 0 0 10px; font-size: 26px; }}
.cover .meta {{ margin: 4px 0; color: #444; }}
.user-page {{ background: #fff; margin: 18px auto; width: 210mm; min-height: 297mm; padding: 18mm 16mm; box-shadow: 0 2px 8px rgba(0,0,0,0.08); page-break-after: always; }}
.user-page h2 {{ margin: 0 0 14px; font-size: 22px; }}
.user-page .meta {{ margin: 6px 0; font-size: 13px; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 18px; }}
th, td {{ border: 1px solid #d0d7de; padding: 8px 10px; text-align: left; vertical-align: top; font-size: 12px; }}
th {{ background: #f1f3f5; }}
.empty {{ margin-top: 18px; padding: 12px; border: 1px dashed #d0d7de; color: #666; background: #fafbfc; }}
@media print {{
  body {{ background: #fff; }}
  .cover {{ page-break-after: always; }}
  .user-page {{ margin: 0; width: auto; min-height: auto; box-shadow: none; }}
}}
</style>
</head>
<body>
<section class="cover">
  <h1>{_escape_html(title)}</h1>
  <div class="meta"><strong>Empresa:</strong> {_escape_html(empresa_name or 'EMPRESA')}</div>
  <div class="meta"><strong>Departamento:</strong> {_escape_html(department)}</div>
  <div class="meta"><strong>Usuarios:</strong> {len(reports)}</div>
  <div class="meta"><strong>Rotinas liberadas:</strong> {total_allowed}</div>
</section>
{user_pages}
</body>
</html>"""


def generate_department_validation_reports(reports, output_dir, empresa_name=""):
    os.makedirs(output_dir, exist_ok=True)
    output_paths = []
    for department, department_reports in sorted(_grouped_reports(reports).items()):
        file_name = f"{_slug_department(department)}.html"
        output_path = os.path.join(output_dir, file_name)
        html = _render_department_html(department, department_reports, empresa_name)
        with open(output_path, "w", encoding="utf-8") as handle:
            handle.write(html)
        output_paths.append(output_path)
    return output_paths
