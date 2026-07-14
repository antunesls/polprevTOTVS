# LLM Fallback Root Cause And Manual Naming Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** Discover why Tier 3 falls back from LLM clustering to manual Jaccard clustering, fix the root cause, and ensure the manual naming suggestion uses routine descriptions instead of routine-code prefixes.

**Architecture:** Start by testing and instrumenting the LLM decision path in `src/organizational_privileges.py` and `src/llm_categorizer.py` so the exact discard reason is visible and reproducible. Then fix the real rejection path first, and only after that change the Jaccard/manual naming heuristic to derive labels from routine descriptions.

**Tech Stack:** Python, unittest/pytest, current OpenRouter integration, existing CLI/Tier 3 generators.

---

### Task 1: Reproduce the fallback decision with tests

**Files:**
- Create: `tests/test_llm_fallback.py`
- Modify: `src/organizational_privileges.py`
- Modify: `src/llm_categorizer.py`

**Step 1: Write the failing test**

```python
def test_try_llm_clustering_reports_why_llm_result_is_rejected():
    ...
```

**Step 2: Run test to verify it fails**

Run: `$env:PYTHONPATH='.'; .venv\Scripts\pytest.exe tests/test_llm_fallback.py -v`
Expected: FAIL because the code currently falls back silently when clusters are discarded or empty.

**Step 3: Write minimal implementation**

Add deterministic tests that simulate:
- empty `clusters`
- invalid/filtered-out clusters
- accepted clusters

**Step 4: Run test to verify it passes**

Run: `$env:PYTHONPATH='.'; .venv\Scripts\pytest.exe tests/test_llm_fallback.py -v`
Expected: PASS.

### Task 2: Surface the root-cause evidence in the LLM path

**Files:**
- Modify: `src/llm_categorizer.py`
- Modify: `src/organizational_privileges.py`
- Test: `tests/test_llm_fallback.py`

**Step 1: Write the failing test**

```python
def test_try_llm_clustering_keeps_llm_mode_when_valid_clusters_exist():
    ...
```

**Step 2: Run test to verify it fails**

Run: `$env:PYTHONPATH='.'; .venv\Scripts\pytest.exe tests/test_llm_fallback.py::LlmClusteringDecisionTest -v`
Expected: FAIL if valid LLM output is still discarded or opaque.

**Step 3: Write minimal implementation**

Make the code explicitly distinguish between:
- API/HTTP failure
- JSON parse failure
- zero clusters from model
- clusters rejected after validation/normalization

**Step 4: Run test to verify it passes**

Run: `$env:PYTHONPATH='.'; .venv\Scripts\pytest.exe tests/test_llm_fallback.py::LlmClusteringDecisionTest -v`
Expected: PASS.

### Task 3: Fix the manual naming heuristic to use descriptions

**Files:**
- Modify: `src/organizational_privileges.py`
- Test: `tests/test_llm_fallback.py`

**Step 1: Write the failing test**

```python
def test_manual_cluster_name_suggestion_prefers_description_terms_over_code_prefixes():
    ...
```

**Step 2: Run test to verify it fails**

Run: `$env:PYTHONPATH='.'; .venv\Scripts\pytest.exe tests/test_llm_fallback.py::ManualNamingTest -v`
Expected: FAIL because the code currently suggests `P_CJ_MATA`, `P_CJ_COMS`, etc.

**Step 3: Write minimal implementation**

Add a small description-based label extractor for manual/Jaccard clusters.

**Step 4: Run test to verify it passes**

Run: `$env:PYTHONPATH='.'; .venv\Scripts\pytest.exe tests/test_llm_fallback.py::ManualNamingTest -v`
Expected: PASS.

### Task 4: Full verification

**Files:**
- Test: `tests/test_llm_fallback.py`
- Test: `tests/test_privilege_sql.py`
- Test: `tests/test_tier3.py`
- Test: `tests/test_html_report.py`

**Step 1: Run the focused fallback tests**

Run: `$env:PYTHONPATH='.'; .venv\Scripts\pytest.exe tests/test_llm_fallback.py -v`
Expected: PASS.

**Step 2: Run the regression suite**

Run: `$env:PYTHONPATH='.'; .venv\Scripts\pytest.exe tests/test_llm_fallback.py tests/test_privilege_sql.py tests/test_tier3.py tests/test_html_report.py -v`
Expected: PASS.
