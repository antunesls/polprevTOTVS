# Offline Transact And Organizational Dashboard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** Ensure `SYS_RULES_TRANSACT` is available in offline mode exports/imports and make the organizational SQL flow also generate the final dashboards.

**Architecture:** Fix the offline data pipeline first so `SYS_RULES_TRANSACT` is exported into `export.json` and therefore available during SQLite-based offline discovery. Then extend the organizational SQL flow to reuse the existing organizational dashboard generation path after SQL creation, instead of leaving dashboard generation exclusive to the analysis-only flow.

**Tech Stack:** Python, unittest/pytest, offline JSON export/import, existing HTML generators in `src/html_report.py` and `src/department_html_report.py`.

---

### Task 1: Cover offline export/import of SYS_RULES_TRANSACT

**Files:**
- Modify: `src/data_exporter.py`
- Test: `tests/test_offline_org_flow.py`

**Step 1: Write the failing test**

```python
def test_export_includes_sys_rules_transact_table():
    ...
```

**Step 2: Run test to verify it fails**

Run: `$env:PYTHONPATH='.'; .venv\Scripts\pytest.exe tests/test_offline_org_flow.py::OfflineExportTest -v`
Expected: FAIL because `SYS_RULES_TRANSACT` is not exported.

**Step 3: Write minimal implementation**

Add `SYS_RULES_TRANSACT` to `TABLES_TO_EXPORT` in `src/data_exporter.py`.

**Step 4: Run test to verify it passes**

Run: `$env:PYTHONPATH='.'; .venv\Scripts\pytest.exe tests/test_offline_org_flow.py::OfflineExportTest -v`
Expected: PASS.

### Task 2: Cover dashboard generation in organizational SQL flow

**Files:**
- Modify: `run.py`
- Test: `tests/test_offline_org_flow.py`

**Step 1: Write the failing test**

```python
def test_batch_organizational_sql_flow_generates_dashboards_after_sql():
    ...
```

**Step 2: Run test to verify it fails**

Run: `$env:PYTHONPATH='.'; .venv\Scripts\pytest.exe tests/test_offline_org_flow.py::OrganizationalDashboardFlowTest -v`
Expected: FAIL because the SQL flow currently ends without generating HTML dashboards.

**Step 3: Write minimal implementation**

Refactor the existing dashboard generation block into a reusable helper and call it from the organizational SQL flow after SQL creation.

**Step 4: Run test to verify it passes**

Run: `$env:PYTHONPATH='.'; .venv\Scripts\pytest.exe tests/test_offline_org_flow.py::OrganizationalDashboardFlowTest -v`
Expected: PASS.

### Task 3: Full verification

**Files:**
- Test: `tests/test_offline_org_flow.py`
- Test: `tests/test_file_logger.py`
- Test: `tests/test_llm_fallback.py`
- Test: `tests/test_privilege_sql.py`
- Test: `tests/test_tier3.py`
- Test: `tests/test_html_report.py`

**Step 1: Run focused tests**

Run: `$env:PYTHONPATH='.'; .venv\Scripts\pytest.exe tests/test_offline_org_flow.py -v`
Expected: PASS.

**Step 2: Run regression suite**

Run: `$env:PYTHONPATH='.'; .venv\Scripts\pytest.exe tests/test_offline_org_flow.py tests/test_file_logger.py tests/test_llm_fallback.py tests/test_privilege_sql.py tests/test_tier3.py tests/test_html_report.py -v`
Expected: PASS.
