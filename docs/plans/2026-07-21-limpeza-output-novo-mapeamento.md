# Limpeza de Output em Novo Mapeamento Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** Remover artefatos gerados anteriormente quando o usuário escolher mapear novamente do banco, preservando-os quando escolher reutilizar mapeamentos.

**Architecture:** A limpeza ficará centralizada em uma função pequena em `run.py`, limitada a padrões conhecidos de arquivos gerados em `output/`. Os fluxos que escolhem `[M] Mapear do banco` chamarão essa função antes de gerar novos `*_access.json`; os fluxos `[R] Reusar arquivos mapeados` não chamarão a limpeza.

**Tech Stack:** Python `unittest`, `tempfile`, `pathlib`, CLI existente em `run.py`.

---

### Task 1: Regression Tests

**Files:**
- Modify: `tests/test_offline_org_flow.py`
- Test: `tests/test_offline_org_flow.py`

**Step 1: Write failing tests**

Add tests that create a temporary output folder with generated and non-generated files. Verify `_clear_generated_mapping_files()` removes generated artifacts and preserves `export.json`, `export.sql`, `clean_privileges.sql`, `logs/`, and unrelated files.

Add a second test proving `_load_reports_from_files()` still reuses existing `*_access.json` without cleanup.

**Step 2: Run test to verify it fails**

Run: `$env:PYTHONIOENCODING='utf-8'; python -m unittest tests.test_offline_org_flow`

Expected: FAIL because `_clear_generated_mapping_files` does not exist.

### Task 2: Minimal Cleanup Implementation

**Files:**
- Modify: `run.py`

**Step 1: Implement helper**

Create `_clear_generated_mapping_files()` near `_load_reports_from_files()`.

It should remove only files matching:
- `*_access.json`
- `*_dashboard.html`
- `*_privileges.sql`
- `*_canonical_menus.sql`
- `canonical_menus.sql`
- `camadas_*.html`
- `clusters_*.html`
- `clusters_*.json`
- `*_organizacional.sql`

It should ignore directories and missing output folders.

**Step 2: Wire mapped-from-bank paths**

Call `_clear_generated_mapping_files()` when the effective mapping path starts in:
- `run_organizational_analysis()` before connecting/mapping when `action == "M"`

Do not clean in `wizard_org_analysis()` because its `[M]` path delegates to `run_organizational_analysis()`, which asks the data source again. Cleaning there would delete files before the final source choice.

**Step 3: Run tests**

Run: `$env:PYTHONIOENCODING='utf-8'; python -m unittest tests.test_offline_org_flow`

Expected: OK.

### Task 3: Full Verification

**Files:**
- All touched files.

**Step 1: Run focused tests**

Run: `$env:PYTHONIOENCODING='utf-8'; python -m unittest tests.test_offline_org_flow`

Expected: OK.

**Step 2: Run full suite**

Run: `$env:PYTHONIOENCODING='utf-8'; python -m unittest discover tests`

Expected: OK.

**Step 3: Review diff**

Run: `git diff -- run.py tests/test_offline_org_flow.py docs/plans/2026-07-21-limpeza-output-novo-mapeamento.md`

Expected: Only plan, cleanup helper, call sites, and tests changed.
