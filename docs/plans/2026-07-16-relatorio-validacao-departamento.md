# Relatorio Validacao Departamento Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** Gerar um relatorio HTML por departamento, pronto para impressao/PDF, com uma pagina por usuario e somente as permissoes efetivamente liberadas.

**Architecture:** O relatorio deve ser gerado a partir de `all_reports`, agrupando usuarios por departamento e filtrando somente rotinas com `effective_access = PERMITIDO`. O HTML sera print-first, com quebra de pagina por usuario, e sera gerado em um arquivo separado por departamento sem substituir os dashboards existentes.

**Tech Stack:** Python, unittest/pytest, geradores HTML existentes em `src/department_html_report.py`, `src/dashboard.py` e fluxo CLI em `run.py`.

---

### Task 1: Cobrir o novo relatorio com testes

**Files:**
- Create: `tests/test_department_validation_report.py`
- Test: `tests/test_department_validation_report.py`

**Step 1: Write the failing test**

```python
def test_generates_one_page_per_user_with_only_allowed_routines():
    paths = generate_department_validation_reports(reports, output_dir, "TESTE")
    assert "MATA010" in html
    assert "MATA020" not in html
```

**Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest.exe tests/test_department_validation_report.py -v`
Expected: FAIL porque o modulo ainda nao existe.

**Step 3: Write minimal implementation**

```python
def generate_department_validation_reports(reports, output_dir, empresa_name=""):
    return []
```

**Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest.exe tests/test_department_validation_report.py -v`
Expected: PASS cobrindo agrupamento, quebra de pagina e filtro por `effective_access`.

**Step 5: Commit**

```bash
git add tests/test_department_validation_report.py src/department_validation_report.py
git commit -m "test: cover department validation report"
```

### Task 2: Implementar o gerador HTML por departamento

**Files:**
- Create: `src/department_validation_report.py`
- Test: `tests/test_department_validation_report.py`

**Step 1: Write the failing test**

```python
def test_users_without_allowed_routines_render_empty_message():
    assert "Nenhuma permissao liberada encontrada" in html
```

**Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest.exe tests/test_department_validation_report.py::DepartmentValidationReportTest -v`
Expected: FAIL pela ausencia da mensagem/estrutura HTML.

**Step 3: Write minimal implementation**

```python
@media print { .user-page { page-break-after: always; } }
```

**Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest.exe tests/test_department_validation_report.py -v`
Expected: PASS com um HTML por departamento em `output/departamentos`.

**Step 5: Commit**

```bash
git add src/department_validation_report.py tests/test_department_validation_report.py
git commit -m "feat: add printable department validation report"
```

### Task 3: Integrar ao fluxo principal

**Files:**
- Modify: `run.py`
- Test: `tests/test_offline_org_flow.py`

**Step 1: Write the failing test**

```python
def test_batch_organizational_generates_department_validation_report():
    dashboard_helper.assert_called_once()
```

**Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest.exe tests/test_offline_org_flow.py -v`
Expected: FAIL porque o novo gerador ainda nao e chamado.

**Step 3: Write minimal implementation**

```python
generate_department_validation_reports(all_reports, os.path.join(OUTPUT_DIR, "departamentos"), cfg.EMPRESA_NAME)
```

**Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest.exe tests/test_offline_org_flow.py -v`
Expected: PASS com os arquivos sendo gerados junto aos dashboards organizacionais.

**Step 5: Commit**

```bash
git add run.py tests/test_offline_org_flow.py
git commit -m "feat: generate printable reports by department"
```

### Task 4: Documentar uso do novo relatorio

**Files:**
- Modify: `README.md`

**Step 1: Write the failing test**

Nao se aplica.

**Step 2: Run test to verify it fails**

Nao se aplica.

**Step 3: Write minimal implementation**

```markdown
- `output/departamentos/{DEPARTAMENTO}.html`: relatorio por usuario pronto para PDF.
```

**Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest.exe tests/test_department_validation_report.py tests/test_offline_org_flow.py tests/test_html_report.py -v`
Expected: PASS e README coerente com o fluxo implementado.

**Step 5: Commit**

```bash
git add README.md
git commit -m "docs: describe printable department reports"
```
