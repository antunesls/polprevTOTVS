# Automatic Rule ID And Transact Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** Generate automatic privilege rules with alphanumeric `RL__ID` values like `A000001` consistently across `SYS_RULES`, `SYS_RULES_FEATURES`, and `SYS_RULES_TRANSACT`.

**Architecture:** Keep the existing SQL generators and add a shared rule-id formatting strategy inside each generator path so all related inserts reuse the same textual `RL__ID`. Extend schema discovery to include `SYS_RULES_TRANSACT`, then emit transaction rows per routine using the mapped description/access fields.

**Tech Stack:** Python, unittest/pytest, current SQL string builders in `src/privilege_generator.py` and `src/organizational_privileges.py`.

---

### Task 1: Add regression tests for automatic rule IDs

**Files:**
- Create: `tests/test_privilege_sql.py`
- Modify: `src/privilege_generator.py`

**Step 1: Write the failing test**

```python
def test_generate_sql_uses_alphanumeric_rule_id_and_transact_rows():
    ...
```

**Step 2: Run test to verify it fails**

Run: `$env:PYTHONPATH='.'; .venv\Scripts\pytest.exe tests/test_privilege_sql.py -v`
Expected: FAIL because the generator still emits numeric `RL__ID` and does not write `SYS_RULES_TRANSACT`.

**Step 3: Write minimal implementation**

Add rule-id formatting and transact row generation to `PrivilegeGenerator.generate_sql()`.

**Step 4: Run test to verify it passes**

Run: `$env:PYTHONPATH='.'; .venv\Scripts\pytest.exe tests/test_privilege_sql.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/test_privilege_sql.py src/privilege_generator.py
git commit -m "feat: generate automatic rule transact rows"
```

### Task 2: Extend schema discovery for SYS_RULES_TRANSACT

**Files:**
- Modify: `src/config.py`
- Modify: `src/diagnose_columns.py`
- Test: `tests/test_privilege_sql.py`

**Step 1: Write the failing test**

```python
def test_schema_candidates_include_rules_transact():
    ...
```

**Step 2: Run test to verify it fails**

Run: `$env:PYTHONPATH='.'; .venv\Scripts\pytest.exe tests/test_privilege_sql.py::SchemaDiscoveryTest -v`
Expected: FAIL because `SYS_RULES_TRANSACT` is absent.

**Step 3: Write minimal implementation**

Add `SYS_RULES_TRANSACT` to `SCHEMA_TABLES` and register the candidate columns in `CANDIDATES`.

**Step 4: Run test to verify it passes**

Run: `$env:PYTHONPATH='.'; .venv\Scripts\pytest.exe tests/test_privilege_sql.py::SchemaDiscoveryTest -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/config.py src/diagnose_columns.py tests/test_privilege_sql.py
git commit -m "feat: discover rules transact schema"
```

### Task 3: Mirror the same behavior in organizational SQL generation

**Files:**
- Modify: `src/organizational_privileges.py`
- Test: `tests/test_privilege_sql.py`

**Step 1: Write the failing test**

```python
def test_organizational_sql_reuses_same_alphanumeric_rule_id_everywhere():
    ...
```

**Step 2: Run test to verify it fails**

Run: `$env:PYTHONPATH='.'; .venv\Scripts\pytest.exe tests/test_privilege_sql.py::OrganizationalSqlTest -v`
Expected: FAIL because the organizational generator still uses numeric IDs and has no transact inserts.

**Step 3: Write minimal implementation**

Port the same rule-id and transact logic into `OrganizationalPrivilegeGenerator`.

**Step 4: Run test to verify it passes**

Run: `$env:PYTHONPATH='.'; .venv\Scripts\pytest.exe tests/test_privilege_sql.py::OrganizationalSqlTest -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/organizational_privileges.py tests/test_privilege_sql.py
git commit -m "feat: align organizational sql rule ids"
```

### Task 4: Full verification

**Files:**
- Test: `tests/test_privilege_sql.py`
- Test: `tests/test_tier3.py`
- Test: `tests/test_html_report.py`

**Step 1: Run the focused SQL tests**

Run: `$env:PYTHONPATH='.'; .venv\Scripts\pytest.exe tests/test_privilege_sql.py -v`
Expected: PASS.

**Step 2: Run the broader regression suite**

Run: `$env:PYTHONPATH='.'; .venv\Scripts\pytest.exe tests/test_privilege_sql.py tests/test_tier3.py tests/test_html_report.py -v`
Expected: PASS.

**Step 3: Inspect output assumptions**

Confirm generated SQL includes:
- `INSERT INTO SYS_RULES`
- `INSERT INTO SYS_RULES_FEATURES`
- `INSERT INTO SYS_RULES_TRANSACT`
- same `A000001` identifier across related inserts

**Step 4: Commit**

```bash
git add tests/test_privilege_sql.py src/config.py src/diagnose_columns.py src/privilege_generator.py src/organizational_privileges.py
git commit -m "feat: generate automatic alphanumeric rule ids"
```
