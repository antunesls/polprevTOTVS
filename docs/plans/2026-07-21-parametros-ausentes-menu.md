# Parametros Ausentes No Menu Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** Exibir e permitir alterar no menu de parametrizacao os parâmetros que já existem na configuração, mas não aparecem na UI.

**Architecture:** A configuração continuará centralizada em `src/config.py`. O menu interativo `menu_parametrizacao()` em `run.py` exibirá e alterará os valores, e `save_user_config()`/`load_user_config()` persistirão também os parâmetros organizacionais de cluster.

**Tech Stack:** Python `unittest`, configuração JSON (`config_user.json`), CLI textual em `run.py`.

---

### Task 1: Persistence Tests

**Files:**
- Modify: `tests/test_config.py`
- Modify: `src/config.py`

**Step 1: Write failing test**

Add a test that saves and reloads:
- `cluster_similarity_threshold`
- `min_cluster_size`
- `ignore_single_user_departments`
- API extended fields: `enabled`, `bearer_token`, `erp_database`, `erp_module`, `verify_ssl`, `timeout`
- log fields: `file_logging_enabled`, `log_dir`

**Step 2: Run test**

Run: `$env:PYTHONIOENCODING='utf-8'; python -m unittest tests.test_config`
Expected: FAIL until missing fields are persisted/restored.

### Task 2: Menu Visibility Test

**Files:**
- Modify: `tests/test_config.py`
- Modify: `run.py`

**Step 1: Write failing test**

Patch `run.input` to return `0`, set `cfg.PRIVILEGE_MODE = "organizational_layer"`, capture stdout, and assert menu contains:
- `Min. depto`
- `Threshold Jaccard`
- `Tam. conjunto`
- `Bearer Token`
- `ERP Database`
- `ERP Modulo`
- `Verify SSL`
- `Timeout API`
- `API ativa`
- `Log arquivo`
- `Diretorio logs`

**Step 2: Run test**

Run: `$env:PYTHONIOENCODING='utf-8'; python -m unittest tests.test_config`
Expected: FAIL until menu displays the options.

### Task 3: Implementation

**Files:**
- Modify: `src/config.py`
- Modify: `run.py`

**Step 1: Persist organizational cluster params**

Add defaults in `src/config.py`:
- `CLUSTER_SIMILARITY_THRESHOLD = 0.4`
- `MIN_CLUSTER_SIZE = 2`

Save/load both values. When loading, also sync `src.organizational_privileges.CLUSTER_SIMILARITY_THRESHOLD` and `MIN_CLUSTER_SIZE` if that module is available.

**Step 2: Add menu display and handlers**

In `menu_parametrizacao()`:
- Display organizational options when mode is organizational.
- Add handlers to toggle `IGNORE_SINGLE_USER_DEPARTMENTS`, set threshold, set min cluster size.
- Display and handle API extended fields.
- Display and handle log options.

**Step 3: Keep changes minimal**

Do not change processing rules besides saving/loading and exposing parameters.

### Task 4: Verification

Run:
- `$env:PYTHONIOENCODING='utf-8'; python -m unittest tests.test_config`
- `$env:PYTHONIOENCODING='utf-8'; python -m unittest discover tests`

Expected: both OK.
