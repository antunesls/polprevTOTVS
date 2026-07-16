# Relatorio de Auditoria de Acessos Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `executing-plans` to implement this plan task-by-task.

---
goal: Adicionar um relatorio consolidado de auditoria de acessos por departamento com validacao visual por usuario
version: 1.0
date_created: 2026-07-15
last_updated: 2026-07-15
owner: OpenCode
status: Planned
tags: feature, audit, report, access, html
---

# Introduction

![Status: Planned](https://img.shields.io/badge/status-Planned-blue)

Este plano descreve a implementacao de um novo relatorio consolidado de auditoria de acessos no projeto `polprevTOTVS`. O objetivo e gerar um artefato HTML unico, filtravel por departamento, com evidencias por usuario e bloco de validacao gerencial no proprio relatorio, adequado para envio aos responsaveis dos departamentos e uso em auditoria.

## 1. Requirements & Constraints

- **REQ-001**: O relatorio deve ser consolidado por departamento.
- **REQ-002**: O relatorio deve conter validacao visual por usuario com os status `Pendente`, `Aprovado` e `Ajustar`.
- **REQ-003**: O relatorio deve disponibilizar campos de `observacao`, `responsavel` e `data` para cada usuario.
- **REQ-004**: A lista de rotinas deve aparecer resumida por padrao e expandivel por usuario.
- **REQ-005**: O relatorio deve ser adequado para navegacao em tela e impressao em PDF.
- **REQ-006**: O relatorio deve explicitar a origem dos dados, a data/hora de geracao e a quantidade de usuarios/departamentos processados.
- **REQ-007**: O relatorio deve funcionar sem backend adicional.
- **REQ-008**: O relatorio deve ser gerado a partir dos arquivos `output/*_access.json` ja produzidos pelo projeto.
- **REQ-009**: O relatorio deve permitir filtro por departamento e por status de validacao.
- **REQ-010**: O relatorio deve destacar usuarios com situacoes de atencao, como ausencia de grupo ou rotinas sem privilegio explicito.
- **CON-001**: Nao deve haver nova consulta ao banco para gerar esse artefato.
- **CON-002**: A implementacao nao deve alterar o comportamento dos dashboards e relatorios existentes.
- **CON-003**: A implementacao deve reutilizar os campos serializados por `src/privilege_generator.py::save_report_json`.
- **CON-004**: A persistencia da validacao sera local no navegador, usando `localStorage`.
- **CON-005**: O relatorio deve continuar util mesmo quando houver usuarios sem departamento preenchido.
- **GUD-001**: Reutilizar o padrao de HTML autocontido adotado em `src/department_html_report.py`, `src/sanitation_report.py` e `src/dashboard.py`.
- **GUD-002**: Reutilizar o padrao de menu e mensagens CLI adotado em `run.py`.
- **PAT-001**: Agrupar usuarios por `user_depto`, com fallback explicito para `SEM_DEPARTAMENTO`.
- **PAT-002**: Manter ordenacao deterministica de departamentos, usuarios e rotinas.
- **SEC-001**: Nao exibir segredos ou configuracoes sensiveis no relatorio.
- **RSK-001**: `localStorage` nao substitui trilha formal de auditoria institucional.
- **ASM-001**: Os JSONs de entrada possuem os campos `user`, `user_name`, `user_depto`, `groups`, `total_routines` e `routines_summary`.

## 2. Implementation Steps

### Implementation Phase 1

- **GOAL-001**: Definir e consolidar a estrutura de dados do relatorio de auditoria.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Mapear exatamente os campos consumidos dos arquivos `output/*_access.json` com base em `src/user_mapper.py` e `src/privilege_generator.py`. |  |  |
| TASK-002 | Definir a estrutura consolidada por departamento, com fallback `SEM_DEPARTAMENTO`. |  |  |
| TASK-003 | Definir a estrutura de resumo por usuario com login, nome, grupos, total de rotinas, rotinas com privilegio explicito e bloqueios por perfil. |  |  |
| TASK-004 | Definir KPIs globais e KPIs por departamento. |  |  |

### Implementation Phase 2

- **GOAL-002**: Criar o novo gerador de relatorio de auditoria.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-005 | Criar o arquivo `src/audit_access_report.py`. |  |  |
| TASK-006 | Implementar funcao para localizar e carregar todos os arquivos `output/*_access.json`. |  |  |
| TASK-007 | Implementar normalizacao e consolidacao dos dados por departamento e por usuario. |  |  |
| TASK-008 | Implementar calculo de KPIs globais, KPIs por departamento e indicadores de atencao. |  |  |
| TASK-009 | Implementar geracao do HTML autocontido com CSS e JavaScript inline. |  |  |
| TASK-010 | Definir nome padrao de saida como `output/relatorio_auditoria_acessos.html`. |  |  |

### Implementation Phase 3

- **GOAL-003**: Implementar a interface HTML orientada para auditoria.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-011 | Adicionar cabecalho com empresa, data/hora de geracao, quantidade de arquivos analisados, departamentos e usuarios. |  |  |
| TASK-012 | Adicionar legenda explicando o objetivo e os criterios do relatorio. |  |  |
| TASK-013 | Adicionar filtros por departamento e por status de validacao. |  |  |
| TASK-014 | Adicionar cards de KPI no topo do relatorio. |  |  |
| TASK-015 | Exibir resumo por departamento com totais e pendencias. |  |  |
| TASK-016 | Exibir cada usuario com evidencias minimas para auditoria. |  |  |
| TASK-017 | Implementar detalhe expansivel por usuario para exibir rotinas, descricao, modulo, privilegio explicito e bloqueio por perfil. |  |  |
| TASK-018 | Implementar botoes `Expandir todos`, `Recolher todos` e `Modo impressao`. |  |  |

### Implementation Phase 4

- **GOAL-004**: Implementar a validacao visual do gestor no proprio HTML.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-019 | Adicionar bloco de validacao por usuario com status `Pendente`, `Aprovado` e `Ajustar`. |  |  |
| TASK-020 | Adicionar campos `observacao`, `responsavel` e `data`. |  |  |
| TASK-021 | Persistir a validacao em `localStorage` com chave estavel baseada no login do usuario. |  |  |
| TASK-022 | Recarregar automaticamente os dados salvos ao abrir o relatorio. |  |  |
| TASK-023 | Destacar visualmente usuarios pendentes e usuarios marcados para ajuste. |  |  |

### Implementation Phase 5

- **GOAL-005**: Integrar a nova funcionalidade ao CLI existente.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-024 | Adicionar nova opcao de menu em `run.py` para gerar o relatorio consolidado de auditoria. |  |  |
| TASK-025 | Implementar validacao para garantir a existencia de `output/*_access.json` antes da geracao. |  |  |
| TASK-026 | Exibir mensagens de sucesso e falha no padrao do projeto. |  |  |
| TASK-027 | Abrir o HTML gerado automaticamente no navegador, se o fluxo atual do projeto justificar essa experiencia. |  |  |

### Implementation Phase 6

- **GOAL-006**: Cobrir a funcionalidade com testes automatizados e documentacao.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-028 | Adicionar teste novo em `tests/test_html_report.py` ou criar `tests/test_audit_access_report.py`. |  |  |
| TASK-029 | Validar em teste o agrupamento por departamento. |  |  |
| TASK-030 | Validar em teste a presenca de filtros, KPIs e campos de validacao. |  |  |
| TASK-031 | Validar em teste o fallback `SEM_DEPARTAMENTO`. |  |  |
| TASK-032 | Validar em teste a presenca do detalhe expansivel por usuario. |  |  |
| TASK-033 | Atualizar `README.md` com a nova opcao e o nome do arquivo gerado. |  |  |

## 3. Alternatives

- **ALT-001**: Gerar um arquivo separado por departamento.
Motivo para nao escolher: aumenta a quantidade de artefatos e reduz a visao executiva consolidada.

- **ALT-002**: Gerar apenas um CSV ou planilha.
Motivo para nao escolher: reduz legibilidade, piora a experiencia de validacao e perde o valor de apresentacao para auditoria.

- **ALT-003**: Consultar banco ou API em tempo real.
Motivo para nao escolher: aumenta o acoplamento operacional e foge do padrao atual do projeto de reutilizar os JSONs ja gerados.

- **ALT-004**: Persistir aprovacoes em arquivo externo ou banco.
Motivo para nao escolher neste primeiro ciclo: amplia o escopo funcional e exige definicao formal de governanca e rastreabilidade institucional.

## 4. Dependencies

- **DEP-001**: `run.py`
- **DEP-002**: `src/user_mapper.py`
- **DEP-003**: `src/privilege_generator.py`
- **DEP-004**: `src/department_html_report.py`
- **DEP-005**: `src/sanitation_report.py`
- **DEP-006**: `src/dashboard.py`
- **DEP-007**: `tests/test_html_report.py`
- **DEP-008**: Diretorio `output/` com arquivos `*_access.json`

## 5. Files

- **FILE-001**: `docs/plans/2026-07-15-relatorio-auditoria-acessos-design.md` - este documento de planejamento
- **FILE-002**: `src/audit_access_report.py` - novo gerador do relatorio consolidado de auditoria
- **FILE-003**: `run.py` - integracao da nova opcao no menu
- **FILE-004**: `tests/test_html_report.py` ou `tests/test_audit_access_report.py` - testes da funcionalidade
- **FILE-005**: `README.md` - documentacao de uso

## 6. Testing

- **TEST-001**: Gerar HTML com usuarios de mais de um departamento e validar o agrupamento correto.
- **TEST-002**: Validar a presenca dos KPIs globais no HTML gerado.
- **TEST-003**: Validar a presenca do filtro por departamento.
- **TEST-004**: Validar a presenca do filtro por status de validacao.
- **TEST-005**: Validar a presenca dos status `Pendente`, `Aprovado` e `Ajustar`.
- **TEST-006**: Validar a presenca dos campos `observacao`, `responsavel` e `data`.
- **TEST-007**: Validar o fallback `SEM_DEPARTAMENTO`.
- **TEST-008**: Validar a presenca do detalhe expansivel por usuario.
- **TEST-009**: Validar o nome e a geracao do arquivo `output/relatorio_auditoria_acessos.html`.

Comandos previstos de verificacao:

```bash
python -m pytest tests/test_html_report.py -v
```

ou

```bash
python -m pytest tests/test_audit_access_report.py -v
```

## 7. Risks & Assumptions

- **RISK-001**: JSONs antigos no diretorio `output/` podem misturar bases de datas diferentes.
- **RISK-002**: `localStorage` e persistencia local por navegador, nao institucional.
- **RISK-003**: Alguns arquivos de entrada podem nao possuir todos os campos esperados.
- **RISK-004**: O relatorio pode crescer bastante em bases com muitos usuarios e rotinas.
- **ASSUMPTION-001**: O usuario executara o mapeamento antes de gerar o relatorio consolidado de auditoria.
- **ASSUMPTION-002**: O relatorio sera consumido em navegador moderno com suporte a `localStorage`.
- **ASSUMPTION-003**: O envio ao responsavel do departamento sera feito como HTML ou PDF gerado a partir do HTML.

## 8. Related Specifications / Further Reading

- `README.md`
- `src/user_mapper.py`
- `src/privilege_generator.py`
- `src/department_html_report.py`
- `src/sanitation_report.py`
- `src/dashboard.py`

## Gap Analysis

- ✅ Relatorio consolidado por departamento: coberto pelo plano.
- ✅ Validacao visual por usuario: coberta pelo plano.
- ✅ Campos de observacao, responsavel e data: cobertos pelo plano.
- ✅ Lista de rotinas resumida com expansao por usuario: coberta pelo plano.
- ✅ Layout adequado para impressao/PDF e uso em auditoria: coberto pelo plano.
- ✅ Integracao ao CLI existente: coberta pelo plano.
- ⚠️ Persistencia institucional da aprovacao: nao coberta neste primeiro ciclo.
Justificativa: a abordagem definida usa `localStorage`, suficiente para validacao local no HTML, mas insuficiente como trilha formal persistida em backend ou arquivo controlado.
