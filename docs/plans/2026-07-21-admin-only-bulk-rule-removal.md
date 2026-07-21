# Admin Only Bulk Rule Removal Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** Deixar apenas o dashboard admin na geração organizacional e adicionar remoção em massa de vínculos de regras no Admin Panel.

**Architecture:** A geração de dashboards será centralizada em `_generate_org_dashboards()` produzindo somente `camadas_admin.html`. O Admin Panel manterá a regra atual de soft delete apenas em `SYS_RULES_USR_RULES`; regras novas marcadas como removidas simplesmente não entram nos inserts.

**Tech Stack:** Python `unittest`, HTML/JavaScript gerado por string em `src/html_admin.py`, CLI `run.py`.

---

### Task 1: Admin HTML Bulk Removal Tests

**Files:**
- Modify: `tests/test_html_report.py`
- Modify: `src/html_admin.py`

**Step 1: Write failing tests**

Add tests for `generate_admin_html()` asserting the generated HTML contains:
- `Remover Selecionadas`
- `Desfazer Selecionadas`
- `bulkMarkSelected`
- SQL removal restricted to `SYS_RULES_USR_RULES`

**Step 2: Run focused test**

Run: `$env:PYTHONIOENCODING='utf-8'; python -m unittest tests.test_html_report`

Expected: FAIL until buttons/functions exist.

**Step 3: Implement minimal admin JS/UI**

In `src/html_admin.py`:
- Add two toolbar buttons calling `bulkMarkSelected(true)` and `bulkMarkSelected(false)`.
- Add `bulkMarkSelected(marked)` that confirms removal, marks selected rules, clears selection, and re-renders.
- Keep `genSQL()` behavior: removed existing rules generate only `UPDATE SYS_RULES_USR_RULES`; removed new rules generate no SQL.

**Step 4: Re-run focused test**

Run: `$env:PYTHONIOENCODING='utf-8'; python -m unittest tests.test_html_report`

Expected: OK.

### Task 2: Disable Non-Admin Dashboards

**Files:**
- Modify: `run.py`
- Modify: `tests/test_offline_org_flow.py`

**Step 1: Write failing tests**

Update `test_batch_organizational_sql_flow_calls_dashboard_generation_after_sql` to assert:
- `generate_admin_html` is called once.
- `generate_cluster_html`, `generate_department_html`, `generate_kanban_html`, `generate_tree_html`, and `generate_department_validation_reports` are not called.

**Step 2: Run focused test**

Run: `$env:PYTHONIOENCODING='utf-8'; python -m unittest tests.test_offline_org_flow`

Expected: FAIL because current flow generates all dashboards.

**Step 3: Implement admin-only generation**

In `_generate_org_dashboards()`:
- Keep building consolidated inventory.
- Generate only `camadas_admin.html` with `generate_admin_html()`.
- Open only admin HTML in browser.
- Remove calls to cluster, department, kanban, tree, and department validation reports.

In `run_organizational_analysis()` direct path:
- Replace direct cluster/department dashboard generation with `_generate_org_dashboards()` so behavior remains consistent.

**Step 4: Re-run focused test**

Run: `$env:PYTHONIOENCODING='utf-8'; python -m unittest tests.test_offline_org_flow`

Expected: OK.

### Task 3: Full Verification

**Files:**
- All touched files.

**Step 1: Run focused tests**

Run: `$env:PYTHONIOENCODING='utf-8'; python -m unittest tests.test_html_report tests.test_offline_org_flow`

Expected: OK.

**Step 2: Run full suite**

Run: `$env:PYTHONIOENCODING='utf-8'; python -m unittest discover tests`

Expected: OK.

**Step 3: Review diff**

Run: `git diff -- run.py src/html_admin.py tests/test_html_report.py tests/test_offline_org_flow.py docs/plans/2026-07-21-admin-only-bulk-rule-removal.md`

Expected: Only admin-only generation, bulk removal UI/JS, tests, and plan changed.
