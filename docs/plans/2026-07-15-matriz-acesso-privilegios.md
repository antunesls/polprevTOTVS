# Matriz de Acesso por Privilegios Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** Alinhar o mapeamento de acessos do projeto com a matriz real do Protheus, separando rotinas presentes no menu de rotinas efetivamente liberadas por privilegio, Grupo Default e ACBROWSE.

**Architecture:** A implementacao deve manter o relatorio completo de menu, mas introduzir uma camada deterministica de resolucao de acesso efetivo por rotina e por feature. Essa camada deve consolidar privilegios de grupo e de usuario com precedencia explicita, modelar o efeito do Grupo Default e expor o resultado para os consumidores downstream sem perder a visao diagnostica do menu.

**Tech Stack:** Python, unittest/pytest, relatorios JSON/HTML existentes em `src/user_mapper.py`, `src/tier3.py` e `src/dashboard.py`.

---

### Task 1: Cobrir a matriz de acesso com testes de regressao

**Files:**
- Create: `tests/test_user_mapper.py`
- Modify: `tests/test_tier3.py`
- Test: `tests/test_user_mapper.py`

**Step 1: Write the failing test**

```python
def test_group_default_requires_explicit_permission():
    report = mapper._build_routine_entry(...)
    assert report["effective_access"] == "NAO_PERMITIDO"
```

**Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest.exe tests/test_user_mapper.py -v`
Expected: FAIL com campos inexistentes como `effective_access` ou com decisao incorreta.

**Step 3: Write minimal implementation**

```python
def _resolve_effective_access(...):
    return {"effective_access": "NAO_PERMITIDO"}
```

**Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest.exe tests/test_user_mapper.py -v`
Expected: PASS nos cenarios de Grupo Default, conflito e menu sem privilegio.

**Step 5: Commit**

```bash
git add tests/test_user_mapper.py tests/test_tier3.py src/user_mapper.py
git commit -m "test: cover privilege access matrix"
```

### Task 2: Implementar o resolvedor de acesso efetivo

**Files:**
- Modify: `src/user_mapper.py`
- Test: `tests/test_user_mapper.py`

**Step 1: Write the failing test**

```python
def test_denied_overrides_allowed_and_not_permitted():
    result = mapper._merge_privilege_entries(entries)
    assert result["effective_access"] == "NEGADO"
```

**Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest.exe tests/test_user_mapper.py::test_denied_overrides_allowed_and_not_permitted -v`
Expected: FAIL porque o merge atual usa sobrescrita simples de dicionario.

**Step 3: Write minimal implementation**

```python
precedence = {"NEGADO": 3, "PERMITIDO": 2, "NAO_PERMITIDO": 1, "SEM_REGRA": 0}
```

**Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest.exe tests/test_user_mapper.py -v`
Expected: PASS com resolucao explicita de origem, motivo e acesso efetivo.

**Step 5: Commit**

```bash
git add src/user_mapper.py tests/test_user_mapper.py
git commit -m "feat: resolve effective access matrix"
```

### Task 3: Ajustar consumidores downstream

**Files:**
- Modify: `src/tier3.py`
- Modify: `src/dashboard.py`
- Test: `tests/test_tier3.py`
- Test: `tests/test_html_report.py`

**Step 1: Write the failing test**

```python
def test_tier3_ignores_routines_without_effective_permission():
    assert user_routine_items(report) == [{"code": "MATA010", "permissions": ["Visualizar"]}]
```

**Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest.exe tests/test_tier3.py -v`
Expected: FAIL porque `tier3` hoje considera qualquer rotina presente em `routines_summary`.

**Step 3: Write minimal implementation**

```python
if str(routine.get("effective_access", "")).upper() != "PERMITIDO":
    continue
```

**Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest.exe tests/test_tier3.py tests/test_html_report.py -v`
Expected: PASS com dashboard exibindo status coerente e tier3 consumindo so acesso efetivo.

**Step 5: Commit**

```bash
git add src/tier3.py src/dashboard.py tests/test_tier3.py tests/test_html_report.py
git commit -m "fix: consume effective routine access"
```

### Task 4: Atualizar documentacao do modelo de acesso

**Files:**
- Modify: `README.md`

**Step 1: Write the failing test**

Nao se aplica. Validacao sera por revisao textual do contrato documentado.

**Step 2: Run test to verify it fails**

Nao se aplica.

**Step 3: Write minimal implementation**

```markdown
- `routines_summary` passa a distinguir `in_menu` de `effective_access`.
```

**Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest.exe tests/test_user_mapper.py tests/test_tier3.py tests/test_privilege_sql.py tests/test_html_report.py -v`
Expected: PASS e README consistente com o comportamento implementado.

**Step 5: Commit**

```bash
git add README.md
git commit -m "docs: describe effective privilege matrix"
```
