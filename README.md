# polprevTOTVS

**Mapeador de Acessos e Privilégios — Protheus**

Ferramenta para mapear os acessos de um usuário do Protheus ERP, listando menus, rotinas, funcionalidades de browse e privilégios configurados. Gera relatório JSON, script SQL para criação de regras e dashboard HTML interativo.

---

## Funcionalidades

| Opção | Descrição |
|-------|-----------|
| **1. Mapear acessos** | Conecta ao banco, descobre a estrutura das tabelas, mapeia menus, rotinas e funcionalidades do usuário. Gera `output/{login}_access.json` |
| **2. Mapear + Privilégios** | Além do mapeamento, gera script SQL para criar um novo grupo de privilégios (`SYS_RULES`) baseado nos acessos do usuário. Gera `output/{login}_privileges.sql` |
| **3. Mapear + Dashboard** | Mapeia e gera dashboard HTML com gráficos, árvore de menu e tabela pesquisável. Gera `output/dashboard.html` |
| **4. Menu canônico por módulo** | Gera SQL para criar um menu único por módulo em `MPMENU_*` com todas as rotinas do módulo e vincular usuários em `SYS_USR_MODULE`. Gera `output/canonical_menus.sql` |
| **Ferramentas > Analisar telemetria** | Confronta o uso real de rotinas coletado em métricas Prometheus com o JSON exportado de usuários/acessos. Gera `output/telemetry_analysis.json` e `output/telemetry_analysis.html` |

### Destaques do mapeamento

- **Módulos**: apenas módulos com `USR_ACESSO = 'T'` (permitidos)
- **Rotinas**: apenas itens ativos (`I_STATUS = '1'`) com função associada
- **Funcionalidades de Browse**: parse do `I_ACCESS` (10 posições) e cross-reference com `RL__MENUOPER` do `SYS_RULES_FEATURES`
- **Overrides de perfil**: leitura do `MP_SYSTEM_PROFILE` (ACBROWSE) para bloqueios por usuário — pastas com status `D` desabilitam toda a subárvore
- **Privilégios**: mapeamento de regras por grupo (`SYS_RULES_GRP_RULES`) e por usuário (`SYS_RULES_USR_RULES`)
- **Acesso efetivo**: o relatório separa rotina presente no menu de rotina efetivamente liberada, considerando privilégio explícito, Grupo Default e bloqueios por `ACBROWSE`
- **Códigos SYS_USR_ACCESS**: o relatório lista os códigos ativos do usuário em `SYS_USR_ACCESS` quando a tabela existir, usando `USR_ACESSO = 'T'`

### Semântica do relatório

- `menus` e `routines_summary` continuam mostrando a estrutura encontrada para o usuário.
- `in_menu = true` indica apenas que a rotina foi localizada em algum menu vinculado ao usuário.
- `effective_access` indica a decisão final de acesso da rotina:
  - `PERMITIDO`
  - `NEGADO`
  - `NAO_PERMITIDO`
  - `SEM_REGRA`
- `decision_source` identifica a regra que venceu a consolidação.
- `denial_reason` explica o motivo principal quando a rotina não está liberada, por exemplo `GROUP_DEFAULT`, `NO_EXPLICIT_RULE` ou `ACBROWSE`.
- Quando o usuário pertence ao `Grupo Default` (`*`), rotinas sem privilégio explícito passam a ser tratadas como `NAO_PERMITIDO`.
- `access_codes` lista os códigos ativos de `SYS_USR_ACCESS` para diagnóstico operacional do usuário.
- `SYS_USR_ACCESS` ainda nao altera o `effective_access` de rotina. Ele permanece como camada diagnóstica separada, porque seus códigos representam permissões sistêmicas e não a matriz de privilégio por rotina/menu.

### Fontes do acesso

- **Acesso efetivo por rotina**: determinado pela consolidacao entre menu, `SYS_RULES*`, grupos, `Grupo Default` e bloqueios de `ACBROWSE`.
- **Acesso sistêmico do usuário**: representado por códigos ativos em `SYS_USR_ACCESS`, como permissões operacionais do cadastro do usuário.
- Esses dois conceitos aparecem no mesmo relatório, mas não se substituem:
  - `effective_access` responde se a rotina ficou liberada ou não.
  - `access_codes` responde quais códigos sistêmicos estão ativos para o usuário.

### Analise de telemetria

A ferramenta pode confrontar um arquivo de telemetria de rotinas com o export offline de usuarios/acessos. O arquivo usado como exemplo e `output/metrics_20260722_bosal.json`; apesar da extensao, o conteudo segue o formato Prometheus text.

Entradas padrao:

- `output/metrics_20260722_bosal.json`: metricas `protheus_routine_calls_total` e `protheus_routine_user_calls_total`.
- `output/JSON_F52E2B61-18A1-11d1-B105-00805F49916B1_BOSAL_3.json`: export das tabelas Protheus para montar os acessos efetivos dos usuarios.

Saidas geradas:

- `output/telemetry_analysis.json`: dados estruturados da analise.
- `output/telemetry_analysis.html`: dashboard com top rotinas, top usuarios por rotina, rotinas liberadas sem uso e uso sem acesso efetivo mapeado.

A lista `unused_allowed_routines` indica rotinas com acesso efetivo mapeado, mas sem uso na telemetria, servindo como candidata a descarte na criacao de novas regras. A lista `used_without_effective_access` mostra usuarios que executaram rotinas sem permissao efetiva correspondente no mapeamento, servindo como ponto de auditoria.

Quando `output/metrics_20260722_bosal.json` existir, a criacao de regras e privilegios passa a usar a telemetria como filtro ativo: rotinas sem chamadas na telemetria sao removidas dos scripts de regras (`SYS_RULES_FEATURES` e `SYS_RULES_TRANSACT`) e dos calculos organizacionais de Tiers. O corte padrao e `min_calls = 1`, ou seja, uma rotina precisa ter pelo menos uma chamada registrada para entrar em nova regra.

---

## Arquitetura

```
polprevTOTVS/
├── run.py                          # CLI principal (menu interativo, ASCII art, spinner)
├── polprevTOTVS.ps1                # Script PowerShell para setup (venv + execução)
├── requirements.txt                # pyodbc>=5.0.0
├── src/
│   ├── __init__.py
│   ├── config.py                   # DB_CONFIG, SCHEMA_TABLES, OUTPUT_DIR
│   ├── database.py                 # Conexão MSSQL, fetch_dicts, fetch_all
│   ├── discovery.py                # Descoberta de colunas via INFORMATION_SCHEMA
│   ├── user_mapper.py              # Mapeamento principal (menus, rotinas, privilégios, ACBROWSE)
│   ├── privilege_generator.py      # Geração de script SQL para SYS_RULES
│   ├── menu_generator.py           # Geração de menu canônico por módulo e vínculos
│   ├── dashboard.py                # Geração de dashboard HTML (Chart.js)
│   └── diagnose_columns.py         # Diagnóstico de colunas vs candidatos
├── tools/                          # Utilitários manuais e scripts auxiliares
│   ├── analyze_acbrowse.py         # Inspeção ad hoc de overrides ACBROWSE
│   ├── check_disabled.py           # Checagem pontual de permissões em relatório JSON
│   └── gen_dab_config.py           # Geração manual de config do Data API Builder
└── output/                         # (gerado) Relatórios e dashboard
    ├── {login}_access.json
    ├── {login}_privileges.sql
    └── dashboard.html
```

---

## Tabelas utilizadas

| # | Tabela | Descrição | Uso no projeto |
|---|--------|-----------|----------------|
| 1 | `SYS_USR` | Usuários do sistema | Buscar usuário por `USR_CODIGO`, obter `USR_ID` |
| 2 | `SYS_USR_MODULE` | Módulos/menus atribuídos ao usuário | Filtrar por `USR_ACESSO = 'T'` para obter módulos permitidos; `USR_MODULO` → `M_MODULE` |
| 3 | `SYS_USR_ACCESS` | Códigos de acesso por usuário | Diagnóstico dos códigos ativos (`USR_CODACESSO`) com `USR_ACESSO = 'T'`; não altera `effective_access` |
| 4 | `SYS_USR_GROUPS` | Associação usuário → grupo | Obter `USR_GRUPO` para buscar privilégios do grupo |
| 5 | `SYS_GRP_GROUP` | Grupos de usuários | Nome do grupo (`GR__NOME`) via `GR__ID` |
| 6 | `SYS_RULES` | Regras de privilégio | `RL__CODIGO` (nome), `RL__DESCRI` (descrição) |
| 7 | `SYS_RULES_FEATURES` | Funcionalidades por rotina | `RL__MENUOPER` (nº da operação), `RL__DESMDEF` (nome da feature), `RL__ACESSO` (1=permitido, 3=negado), `RL__MENUDEF` (função interna) |
| 8 | `SYS_RULES_BUTTONS` | Botões das regras | Não usado ativamente no mapeamento |
| 9 | `SYS_RULES_GRP_RULES` | Associação grupo → regra | `GROUP_ID` → `GR__RL_ID` |
| 10 | `SYS_RULES_USR_RULES` | Associação usuário → regra | `USER_ID` → `USR_RL_ID` |
| 11 | `MPMENU_MENU` | Menus do sistema | `M_ID`, `M_NAME`, `M_MODULE` — join com `USR_MODULO` |
| 12 | `MPMENU_ITEM` | Itens de menu | `I_TP_MENU` (1=pasta, 2=browse), `I_ACCESS` (10 posições de features), `I_STATUS` (1=ativo), `I_ID_FUNC` → `F_ID` |
| 13 | `MPMENU_FUNCTION` | Funções/rotinas | `F_ID` → `F_FUNCTION` (ex: MATA010) |
| 14 | `MPMENU_I18N` | Descrições internacionalizadas | `N_DESC` (descrição), `N_LANG` (idioma), `N_PAREN_ID` → `I_ID` |
| 15 | `MP_SYSTEM_PROFILE` | Perfil do sistema | `P_TYPE = 'ACBROWSE'` — overrides de funcionalidades por usuário em `P_DEFS` (binário) |

### Menu canônico por módulo

- O wizard pode gerar um **menu único por módulo** contendo todas as rotinas encontradas naquele módulo.
- O script cria registros em `MPMENU_MENU`, `MPMENU_ITEM` e `MPMENU_I18N`.
- Os vínculos em `SYS_USR_MODULE` podem ser gerados em dois modos:
  - `substituir`: remove os vínculos existentes do mesmo módulo antes de incluir o canônico
  - `adicionar`: mantém os vínculos atuais e adiciona o canônico quando ainda não existir
- A exibição final das rotinas continua sendo controlada por privilégios (`SYS_RULES*`) e pelo perfil `ACBROWSE`.

### Colunas principais por tabela

**SYS_USR:** `USR_ID`, `USR_CODIGO`, `USR_NOME`, `D_E_L_E_T_`, `R_E_C_N_O_`

**SYS_USR_MODULE:** `USR_ID`, `USR_ACESSO`, `USR_MODULO`, `USR_CODMOD`, `D_E_L_E_T_`

**SYS_USR_GROUPS:** `USR_ID`, `USR_GRUPO`, `D_E_L_E_T_`

**SYS_GRP_GROUP:** `GR__ID`, `GR__NOME`, `GR__CODIGO`

**SYS_RULES:** `RL__ID`, `RL__CODIGO`, `RL__DESCRI`

**SYS_RULES_FEATURES:** `RL__ID`, `RL__ROTINA`, `RL__ITEM`, `RL__ACESSO`, `RL__MENUOPER`, `RL__DESMDEF`, `RL__MENUDEF`

**SYS_RULES_GRP_RULES:** `GROUP_ID`, `GR__RL_ID`

**SYS_RULES_USR_RULES:** `USER_ID`, `USR_RL_ID`

**MPMENU_MENU:** `M_ID`, `M_NAME`, `M_MODULE`

**MPMENU_ITEM:** `I_ID`, `I_ID_MENU`, `I_FATHER`, `I_ID_FUNC`, `I_TP_MENU`, `I_ACCESS`, `I_STATUS`

**MPMENU_FUNCTION:** `F_ID`, `F_FUNCTION`

**MPMENU_I18N:** `N_PAREN_TP`, `N_PAREN_ID`, `N_LANG`, `N_DESC`

**MP_SYSTEM_PROFILE:** `P_NAME`, `P_PROG`, `P_TASK`, `P_TYPE`, `P_DEFS` (varbinary)

---

## Fluxo de mapeamento

```
┌──────────────────────────────────────────────────┐
│ 1. find_user(login)                              │
│    └─ SELECT USR_ID, USR_CODIGO FROM SYS_USR     │
│       WHERE USR_CODIGO = ?                       │
├──────────────────────────────────────────────────┤
│ 2. map_menu_modules(user_id)                     │
│    └─ SELECT USR_MODULO FROM SYS_USR_MODULE      │
│       WHERE USR_ID = ? AND USR_ACESSO = 'T'      │
├──────────────────────────────────────────────────┤
│ 3. map_menu_tree(menu_ids)                       │
│    └─ SELECT M_ID, M_NAME FROM MPMENU_MENU       │
│       WHERE M_MODULE IN (?)                      │
│    └─ _map_menu_items (MPMENU_ITEM +             │
│       MPMENU_FUNCTION + MPMENU_I18N)             │
│       └─ I_ACCESS → browse_features              │
├──────────────────────────────────────────────────┤
│ 4. map_user_groups(user_id)                      │
│    └─ SYS_USR_GROUPS → SYS_GRP_GROUP             │
├──────────────────────────────────────────────────┤
│ 5. map_group_privileges +                        │
│    map_user_privileges_direct                    │
│    └─ SYS_RULES_GRP_RULES → SYS_RULES →          │
│       SYS_RULES_FEATURES (RL__MENUOPER)           │
├──────────────────────────────────────────────────┤
│ 6. map_system_profile(user_id)                   │
│    └─ MP_SYSTEM_PROFILE (P_TYPE='ACBROWSE')     │
│       └─ Parse P_DEFS binário                    │
│       └─ D/E → status de pastas                  │
│       └─ "xxx xxxxxx" → override de features    │
├──────────────────────────────────────────────────┤
│ 7. Consolidar → routines_summary                 │
│    └─ I_ACCESS ∩ ACBROWSE ∩ RL__MENUOPER        │
│    └─ browse_permissions[] por rotina            │
│    └─ disabled_by_acbrowse flag                  │
└──────────────────────────────────────────────────┘
```

---

## Funcionalidades de Browse

As 10 posições do `I_ACCESS` correspondem às operações do menu (ordem de exibição padrão Protheus):

| Pos | OP | Nome padrão |
|-----|-----|-------------|
| 0 | 1 | Pesquisar |
| 1 | 2 | Visualizar |
| 2 | 3 | Incluir |
| 3 | 4 | Alterar |
| 4 | 5 | Excluir |
| 5 | 6 | Cod.Barra |
| 6 | 7 | Copiar |
| 7 | 8 | Retornar |
| 8 | 9 | Prep.Doc.Saida |
| 9 | 10 | Extra |

- `x` = disponível, ` ` (espaço) = indisponível
- O `RL__MENUOPER` em `SYS_RULES_FEATURES` faz o link numérico: `RL__MENUOPER = pos + 1`
- Overrides do `MP_SYSTEM_PROFILE` (ACBROWSE) sobrescrevem o `I_ACCESS` por usuário

---

## Dashboard HTML

O dashboard (`output/dashboard.html`) é autocontido e inclui:

- **6 KPI cards**: Menus, Rotinas, Rotinas Permitidas, Grupos, Bloqueadas, Códigos ativos
- **Gráfico de barras**: Top 15 prefixos de função (MATA, COMS, etc.)
- **Gráfico doughnut**: Acessíveis vs Bloqueadas (Perfil)
- **Árvore de menu**: Hierarquia colapsável com `father_id`
- **Tabela pesquisável**: 146 rotinas com Status, Privilégio e Browse OPs
- **Tema escuro**: Estilo GitHub Dark

## Relatorio por Departamento

O fluxo organizacional tambem gera relatorios HTML prontos para impressao/PDF em:

- `output/departamentos/{DEPARTAMENTO}.html`

Cada arquivo contem:

- 1 departamento por arquivo
- 1 pagina por usuario
- rotinas explicitamente `PERMITIDO`
- para usuarios fora do `Grupo Default`, tambem inclui rotinas em `SEM_REGRA` quando estiverem no menu e sem bloqueio por `ACBROWSE`, refletindo o modelo tradicional de negacao por excecao
- grupos e codigos ativos de `SYS_USR_ACCESS`

Para exportar em PDF, abra o HTML do departamento desejado no navegador e use `Ctrl+P` > `Salvar como PDF`.

---

## Como executar

```powershell
# Via PowerShell (cria .venv, instala dependências)
.\polprevTOTVS.ps1

# Ou manualmente
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

### Menu interativo

```
╔══════════════════════════════════════════╗
║  1 │ Apenas mapear acessos              ║
║  2 │ Mapear + Gerar privilégios         ║
║  3 │ Mapear + Dashboard HTML            ║
║  6 │ Relatório por departamento         ║
║  0 │ Sair                               ║
╚══════════════════════════════════════════╝

Opcao: 1

Usuario [usr001]: ← ENTER para padrão ou digite outro
```

No modo `organizational_layer`, a opção `6` gera apenas os arquivos em `output/departamentos/`, sem depender do dashboard interativo.

---

## Pré-requisitos

- **Python** 3.8+
- **pyodbc** 5.0+
- **ODBC Driver 17 for SQL Server** (ou superior)
- **Banco Protheus** com as tabelas de sistema acessíveis
- **Credenciais** configuradas em `src/config.py`

---

## Configuração

Editar `src/config.py`:

```python
DB_CONFIG = {
    "server": "localhost",
    "database": "TOTVS_2510",
    "username": "TOTVS12",
    "password": "TOTVS12",
    "driver": "ODBC Driver 17 for SQL Server",
}

OUTPUT_DIR = "output"

SCHEMA_TABLES = [
    "SYS_USR", "SYS_USR_MODULE", "SYS_USR_ACCESS", "SYS_USR_GROUPS",
    "SYS_GRP_GROUP", "SYS_RULES", "SYS_RULES_FEATURES", "SYS_RULES_BUTTONS",
    "SYS_RULES_GRP_RULES", "SYS_RULES_USR_RULES",
    "MPMENU_MENU", "MPMENU_ITEM", "MPMENU_FUNCTION", "MPMENU_I18N",
]
```

> **Nota:** `MP_SYSTEM_PROFILE` não está em `SCHEMA_TABLES` pois é consultada dinamicamente via SQL direto.

---

## Output

```
output/
├── usr001_access.json       # Relatório completo (rotinas, features, browse permissions)
├── usr001_privileges.sql    # Script SQL para criar regra no SYS_RULES
├── dashboard.html           # Dashboard gráfico interativo
└── departamentos/
    ├── COMERCIAL.html       # Relatório por usuário pronto para impressão/PDF
    └── CONTROLADORIA.html
```

### Estrutura do JSON

```json
{
  "user": "usr001",
  "user_id": "000002",
  "total_menus": 1,
  "total_routines": 146,
  "groups": [],
  "menus": [{ "menu_id": "...", "menu_name": "SIGACOM", "items": [...] }],
  "routines_summary": [
    {
      "routine": "MATA010",
      "description": "Produtos",
      "menu_name": "SIGACOM",
      "in_menu": true,
      "has_explicit_privilege": false,
      "effective_access": "NAO_PERMITIDO",
      "decision_source": "GROUP_DEFAULT",
      "denial_reason": "GROUP_DEFAULT",
      "disabled_by_acbrowse": true,
      "browse_permissions": [
        { "pos": 0, "menu_oper": 1, "available": false, "features": [] },
        ...
      ]
    }
  ],
  "privileges_raw": {}
}
```

---

## Diagnóstico de colunas

O script `src/diagnose_columns.py` compara os candidatos de colunas do projeto com as colunas reais do banco, gerando relatório de matches/mismatches:

```powershell
python src/diagnose_columns.py
```

Relatório salvo em `output/diagnose_columns.json`.
