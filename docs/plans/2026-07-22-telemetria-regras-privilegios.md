# Telemetria em Regras e Privilegios Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** Fazer a analise e geracao de regras/privilegios considerar a telemetria de uso real, descartando rotinas sem uso quando configurado.

**Architecture:** A telemetria sera aplicada como filtro reutilizavel sobre `routines_summary`, antes dos algoritmos de Tiers e antes dos geradores SQL. O comportamento antigo sera preservado quando nenhum arquivo/filtro de telemetria for informado.

**Tech Stack:** Python `unittest`, parser Prometheus existente em `src/telemetry_analyzer.py`, geradores atuais em `src/privilege_generator.py`, `src/tier3.py` e fluxos em `run.py`.

---

### Task 1: Contexto dos Geradores

**Files:**
- Inspect: `run.py`
- Inspect: `src/privilege_generator.py`
- Inspect: `src/tier3.py`
- Inspect: `src/organizational_privileges.py`

**Steps:**
1. Localizar onde `routines_summary` e `user_routine_items` alimentam os geradores.
2. Confirmar pontos de menor impacto para aplicar filtro.
3. Nao alterar comportamento antes dos testes.

### Task 2: Testes do Filtro

**Files:**
- Modify: `tests/test_telemetry_analyzer.py`

**Steps:**
1. Escrever teste falhando para `filter_reports_by_telemetry` descartando rotina sem uso.
2. Escrever teste falhando preservando rotina com chamadas acima do corte minimo.
3. Executar `python -m unittest tests.test_telemetry_analyzer` e confirmar falha por funcao ausente.

### Task 3: Implementar Filtro Reutilizavel

**Files:**
- Modify: `src/telemetry_analyzer.py`

**Steps:**
1. Implementar `routine_call_counts(metrics)`.
2. Implementar `filter_reports_by_telemetry(reports, metrics_path=None, metrics=None, min_calls=1)`.
3. Retornar copia dos reports com `routines_summary` filtrado.
4. Adicionar metadados `_telemetry_filter` com total removido por usuario e total geral.
5. Rodar testes.

### Task 4: Integrar no SQL por Usuario

**Files:**
- Modify: `src/privilege_generator.py`
- Test: `tests/test_privilege_sql.py` ou novo teste minimo

**Steps:**
1. Permitir que o report ja venha filtrado, sem alterar assinatura publica.
2. Garantir que rotinas removidas pela telemetria nao gerem `SYS_RULES_FEATURES` nem `SYS_RULES_TRANSACT`.
3. Testar com report contendo uma rotina usada e uma sem uso.

### Task 5: Integrar no Fluxo Organizacional

**Files:**
- Modify: `run.py`
- Modify: `src/tier3.py` se necessario
- Test: `tests/test_tier3.py` ou `tests/test_telemetry_analyzer.py`

**Steps:**
1. Adicionar pergunta no wizard organizacional: usar telemetria para filtrar regras?
2. Usar default `output/metrics_20260722_bosal.json` quando existir.
3. Aplicar filtro nos `all_reports` antes de Tiers 1-4 e antes da geracao SQL.
4. Exibir resumo de rotinas removidas.

### Task 6: Documentacao e Verificacao

**Files:**
- Modify: `README.md`

**Steps:**
1. Documentar que a telemetria pode ser usada como filtro ativo.
2. Executar `python -m unittest tests.test_telemetry_analyzer`.
3. Executar `python -m unittest discover -s tests`.
4. Executar `python -m py_compile run.py src\telemetry_analyzer.py src\privilege_generator.py`.
