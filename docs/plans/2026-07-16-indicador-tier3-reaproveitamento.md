# Indicador Tier3 Reaproveitamento Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** Exibir no dashboard principal do Tier 3 um indicador visual informando se cada conjunto reaproveita uma regra existente ou se uma nova regra sera criada.

**Architecture:** O campo `reuses_existing_rule` ja e calculado no backend e precisa apenas ser renderizado no HTML do Tier 3 principal. A implementacao deve adicionar badges visuais no cabecalho do cluster, preservando essa informacao no render e na exportacao do JSON ajustado.

**Tech Stack:** Python, unittest/pytest, HTML gerado por `src/html_report.py`.

---

### Task 1: Cobrir o indicador do Tier 3 com teste

**Files:**
- Modify: `tests/test_html_report.py`

**Step 1: Write the failing test**

```python
def test_tier3_html_shows_reuse_or_new_rule_badges():
    assert "Reaproveita P_COMPRAS" in html
    assert "Nova regra" in html
```

**Step 2: Run test to verify it fails**

Run: `.venv\Scripts\pytest.exe tests/test_html_report.py -v`
Expected: FAIL porque o Tier 3 principal ainda nao renderiza esse badge.

**Step 3: Write minimal implementation**

```python
badge = '<span class="reuse-badge">Reaproveita ...</span>'
```

**Step 4: Run test to verify it passes**

Run: `.venv\Scripts\pytest.exe tests/test_html_report.py -v`
Expected: PASS com os indicadores no HTML.

**Step 5: Commit**

```bash
git add tests/test_html_report.py src/html_report.py
git commit -m "feat: show tier3 rule status badges"
```
