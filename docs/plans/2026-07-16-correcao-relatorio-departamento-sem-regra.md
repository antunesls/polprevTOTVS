# Correcao Relatorio Departamento Sem Regra Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** Corrigir o relatorio por departamento para que usuarios fora do Grupo Default tenham suas rotinas operacionalmente liberadas exibidas mesmo quando nao houver privilegio explicito no JSON.

**Architecture:** O ajuste deve ocorrer no filtro do relatorio print-first em `src/department_validation_report.py`. A regra deve distinguir usuarios com Grupo Default dos usuarios no modelo tradicional do Protheus, tratando `SEM_REGRA` como liberado apenas quando a rotina estiver no menu e nao estiver bloqueada por `ACBROWSE`.

**Tech Stack:** Python, unittest/pytest, HTML generator dedicado do relatorio por departamento e JSONs de acesso consolidados pelo `UserMapper`.

---

### Task 1: Cobrir o caso de usuario sem Grupo Default

**Files:**
- Modify: `tests/test_department_validation_report.py`

**Step 1: Write the failing test**

```python
def test_sem_regra_user_without_group_default_is_listed_as_allowed():
    assert "COMR015" in html
```

**Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest.exe tests/test_department_validation_report.py -v`
Expected: FAIL porque o relatorio hoje considera apenas `effective_access = PERMITIDO`.

**Step 3: Write minimal implementation**

```python
if routine["effective_access"] == "SEM_REGRA" and not has_group_default:
    include = True
```

**Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest.exe tests/test_department_validation_report.py -v`
Expected: PASS mantendo o bloqueio para usuarios com Grupo Default.

**Step 5: Commit**

```bash
git add tests/test_department_validation_report.py src/department_validation_report.py
git commit -m "fix: include menu-allowed routines in department report"
```

### Task 2: Validar o caso real e documentar a regra

**Files:**
- Modify: `README.md`

**Step 1: Write the failing test**

Nao se aplica.

**Step 2: Run test to verify it fails**

Nao se aplica.

**Step 3: Write minimal implementation**

```markdown
- fora do Grupo Default, `SEM_REGRA` em rotina de menu sem bloqueio por perfil entra no relatorio gerencial.
```

**Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest.exe tests/test_department_validation_report.py tests/test_offline_org_flow.py -v`
Expected: PASS e documentacao coerente.

**Step 5: Commit**

```bash
git add README.md
git commit -m "docs: clarify department report access rule"
```
