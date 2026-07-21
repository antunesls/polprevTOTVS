from src.database import get_connection, fetch_dicts, fetch_all
from src.discovery import column_exists, get_columns_list
import struct


BROWSE_FEATURES = [
    "Pesquisar", "Visualizar", "Incluir", "Alterar", "Excluir",
    "Cod.Barra", "Copiar", "Retornar", "Prep.Doc.Saida", "Extra",
]

USER_ACCESS_CODES = {
    "101": {
        "name": "Imprime param. relatórios",
        "description": "Define se os parâmetros utilizados na emissão do relatório serão impressos.",
        "functions": ["Acesso genérico para relatórios"],
    },
    "102": {
        "name": "Imprime param. telas",
        "description": "Define se os parâmetros utilizados nas telas serão impressos.",
        "functions": ["Acesso genérico para telas"],
    },
    "103": {
        "name": "Força Expurgo de Dados",
        "description": "Permite ao usuário forçar o expurgo de dados, independentemente dos parâmetros configurados.",
        "functions": ["Expurgo de Dados"],
    },
    "104": {
        "name": "Imprimir Rel. Direto na Impressora",
        "description": "Permite que o relatório seja impresso diretamente na impressora configurada, sem visualização prévia.",
        "functions": ["Acesso genérico para relatórios"],
    },
    "105": {
        "name": "Acessar ExecAuto em Background",
        "description": "Permite que o usuário execute rotinas ExecAuto em modo Background.",
        "functions": ["ExecAuto"],
    },
    "106": {
        "name": "Nova Regra para Rotina Nova",
        "description": "Cria automaticamente uma nova regra de acesso quando uma rotina nova é identificada no menu do usuário.",
        "functions": ["Configurador de Acessos"],
    },
    "107": {
        "name": "Edita Código de Regras",
        "description": "Permite ao usuário editar o código de identificação das regras de acesso.",
        "functions": ["Configurador de Acessos"],
    },
    "108": {
        "name": "Acesso as Configurações do SmartClient",
        "description": "Permite ao usuário acessar o menu de configurações do SmartClient.",
        "functions": ["SmartClient"],
    },
    "109": {
        "name": "Exportar Dicionário de Dados",
        "description": "Permite ao usuário exportar o Dicionário de Dados do sistema.",
        "functions": ["Dicionário de Dados"],
    },
    "110": {
        "name": "Força Acesso a um Ambiente Específico",
        "description": "Permite ao usuário forçar o acesso a um ambiente que não seja o seu ambiente padrão de login.",
        "functions": ["Ambiente"],
    },
    "111": {
        "name": "Libera a Troca de Interfaces",
        "description": "Permite ao usuário trocar entre o SmartClient e a interface Web, se disponível.",
        "functions": ["Interface"],
    },
    "112": {
        "name": "Gerar rel. no servidor",
        "description": "Permite que o relatório seja gerado no servidor de aplicação (AppServer) em vez de localmente no SmartClient.",
        "functions": ["Acesso genérico para relatórios"],
    },
    "113": {
        "name": "Acessar Módulo em Manutenção",
        "description": "Permite ao usuário acessar módulos que estão em manutenção, com acesso restrito.",
        "functions": ["Acesso genérico para módulos"],
    },
    "114": {
        "name": "Permite Planilhas com Infinitas Linhas",
        "description": "Permite ao usuário gerar planilhas sem limite de linhas.",
        "functions": ["Acesso genérico para planilhas/gráficos"],
    },
    "115": {
        "name": "Configurador de Perfil de Acesso",
        "description": "Permite ao usuário acessar o Configurador de Perfil de Acesso.",
        "functions": ["Configurador de Acessos"],
    },
    "116": {
        "name": "Permite envio de email de dentro do Protheus",
        "description": "Concede permissão para o usuário enviar e-mails a partir de rotinas do Protheus (Exceto rotinas de workflow).",
        "functions": ["E-mail"],
    },
    "117": {
        "name": "Permite Visualizar Relatórios (pdf) na própria tela",
        "description": "Permite ao usuário visualizar os relatórios em formato PDF na própria tela do SmartClient (Visualizador integrado).",
        "functions": ["Acesso genérico para relatórios"],
    },
    "118": {
        "name": "Abrir Arquivos - Ferramenta de Análise de Dados",
        "description": "Permite ao usuário abrir arquivos na Ferramenta de Análise de Dados.",
        "functions": ["Ferramenta de Análise de Dados"],
    },
    "119": {
        "name": "Libera Senha para Impressão - Espelhamento",
        "description": "Libera a solicitação de senha ao realizar impressão de espelhamento.",
        "functions": ["Acesso genérico para relatórios"],
    },
    "120": {
        "name": "Permite Carga de Dados via Planilha de Interface",
        "description": "Permite a carga de dados para tabelas Protheus via planilha de interface.",
        "functions": ["Acesso genérico para planilhas/gráficos"],
    },
    "121": {
        "name": "Usa impressora no server",
        "description": "Permite que o usuário utilize as impressoras registradas no servidor de aplicação para a emissão de relatórios.",
        "functions": ["Acesso genérico para relatórios"],
    },
    "122": {
        "name": "Exportar Dados para Planilha de Trabalho",
        "description": "Permite ao usuário exportar dados de grids/tabelas para uma planilha de trabalho.",
        "functions": ["Acesso genérico para planilhas/gráficos"],
    },
    "123": {
        "name": "Configurações Relatório B.I.",
        "description": "Permite ao usuário acessar as configurações de Relatórios de B.I.",
        "functions": ["Ferramentas de BI"],
    },
    "124": {
        "name": "Permite ao usuário iniciar o Protheus em Modo Administrador",
        "description": "Permite ao usuário iniciar o Protheus em Modo Administrador, concedendo poderes especiais.",
        "functions": ["Admin"],
    },
    "125": {
        "name": "Permite configurar Caminho Arquivos",
        "description": "Habilita o botão 'Caminho Arquivos' nas telas que permitem anexar arquivos.",
        "functions": ["Acesso genérico para arquivos/documentos"],
    },
    "126": {
        "name": "Permite configurar Arquivos",
        "description": "Habilita o botão 'Arquivos' nas telas que permitem anexar arquivos.",
        "functions": ["Acesso genérico para arquivos/documentos"],
    },
    "127": {
        "name": "Configurar Pasta de Trabalho",
        "description": "Permite ao usuário configurar a pasta de trabalho onde são salvos os arquivos de configuração local.",
        "functions": ["SmartClient"],
    },
    "128": {
        "name": "Permite Usar a Função Falar",
        "description": "Habilita a função 'Falar' no Protheus, que lê em voz alta mensagens e campos.",
        "functions": ["Acessibilidade"],
    },
    "129": {
        "name": "Acesso à Câmera",
        "description": "Permite ao usuário utilizar a câmera do dispositivo para captura de imagens.",
        "functions": ["Acesso genérico para câmera"],
    },
    "130": {
        "name": "Acesso Full Administrador do Protheus",
        "description": "Concede ao usuário acesso total de administrador do sistema, permitindo acessar todas as rotinas sem restrições de regras.",
        "functions": ["Admin"],
    },
    "131": {
        "name": "Permite reimpressão de etiquetas",
        "description": "Permite ao usuário reimprimir etiquetas de produtos.",
        "functions": ["Etiquetas/Código de Barras"],
    },
    "132": {
        "name": "Permite acesso ao Configurador de Acessos",
        "description": "Permite ao usuário acessar a tela principal do Configurador de Acessos.",
        "functions": ["Configurador de Acessos"],
    },
    "133": {
        "name": "Permite configurar arquivos para Download",
        "description": "Habilita o botão 'Download' nas telas que permitem anexar arquivos.",
        "functions": ["Acesso genérico para arquivos/documentos"],
    },
    "134": {
        "name": "Permite acesso ao Questionário do Protheus",
        "description": "Habilita o acesso à rotina de Questionário do Protheus (Perguntas e Respostas).",
        "functions": ["Configuração"],
    },
    "135": {
        "name": "Permite bloquear transmissões de NF-e",
        "description": "Permite ao usuário bloquear a transmissão de NF-e.",
        "functions": ["NF-e"],
    },
    "136": {
        "name": "Configurador de Regras por Usuário",
        "description": "Ao editar um usuário, habilita o botão 'Regras de Usuário' para configurar regras por usuário no módulo Configurador.",
        "functions": ["Cadastro de Usuários"],
    },
    "137": {
        "name": "Permite Implantação de Dicionário de Dados",
        "description": "Permite ao usuário realizar a implantação do dicionário de dados (criação/alteração de tabelas).",
        "functions": ["Dicionário de Dados"],
    },
    "138": {
        "name": "Permite Exclusão do Dicionário de Dados",
        "description": "Permite ao usuário excluir tabelas via Dicionário de Dados.",
        "functions": ["Dicionário de Dados"],
    },
    "139": {
        "name": "Permite Envio de Anexo de NF-e",
        "description": "Habilita o envio de arquivos anexos relacionados à NF-e.",
        "functions": ["NF-e"],
    },
    "140": {
        "name": "Acesso ao Cadastro de Parâmetros",
        "description": "Permite ao usuário acessar o Cadastro de Parâmetros (SX6).",
        "functions": ["Cadastro de Parâmetros"],
    },
    "141": {
        "name": "Visualiza rotinas Bloqueadas",
        "description": "Permite ao usuário visualizar rotinas que estão bloqueadas (em manutenção).",
        "functions": ["Acesso genérico para rotinas"],
    },
    "142": {
        "name": "Permite acessar cadastro de Exceção de Bloqueio",
        "description": "Permite ao usuário acessar o Cadastro de Exceção de Bloqueio.",
        "functions": ["Cadastro de Parâmetros"],
    },
    "143": {
        "name": "Acesso Admin - Workflow",
        "description": "Concede ao usuário acesso total às funcionalidades de Workflow.",
        "functions": ["Workflow"],
    },
    "144": {
        "name": "Permite Configurar Serviços Aguá/Prata",
        "description": "Permite ao usuário configurar os Serviços Aguá/Prata.",
        "functions": ["Serviços"],
    },
    "145": {
        "name": "Permite Configurar Serviços do Protheus",
        "description": "Permite ao usuário configurar os Serviços do Protheus.",
        "functions": ["Serviços"],
    },
    "146": {
        "name": "Permite realizar Backup de Base via Protheus",
        "description": "Permite ao usuário realizar backup de bases de dados através do Protheus.",
        "functions": ["Backup"],
    },
    "147": {
        "name": "Permite realizar Restore de Base via Protheus",
        "description": "Permite ao usuário realizar restauração de bases de dados através do Protheus.",
        "functions": ["Backup"],
    },
    "148": {
        "name": "Permite Configurar Serviços Nuvem",
        "description": "Permite ao usuário configurar os Serviços de Nuvem.",
        "functions": ["Serviços"],
    },
    "149": {
        "name": "Permite acessar ao Módulo EAD",
        "description": "Permite ao usuário acessar o Módulo de EAD (Ensino a Distância).",
        "functions": ["EAD"],
    },
    "150": {
        "name": "Permite Acesso Ao Café",
        "description": "Permite ao usuário acessar a plataforma social Café.",
        "functions": ["Café"],
    },
    "151": {
        "name": "Permite acessar outras Filiais",
        "description": "O usuário que possuir esse acesso não terá Restrição de Dados pela Estrutura de Grupo de Empresas (por Filial).",
        "functions": ["Restrição de Dados pela Estrutura de Grupo de Empresas"],
    },
    "152": {
        "name": "Permite Acesso ao T.E.S.T.E",
        "description": "Permite ao usuário acessar o ambiente T.E.S.T.E (TOTVS Exclusive System for Tests and Education).",
        "functions": ["T.E.S.T.E"],
    },
    "153": {
        "name": "Permite acessar Ações para Melhorias",
        "description": "Permite ao usuário acesso ao cadastro de Ações para Melhorias e Inovações (Sugestões).",
        "functions": ["Inovação"],
    },
    "154": {
        "name": "Permite Configurar Processos Eletrônicos (Workflow)",
        "description": "Permite ao usuário configurar processos eletrônicos (Workflow).",
        "functions": ["Workflow"],
    },
    "155": {
        "name": "Acessar Serviços Aguá/Prata",
        "description": "Permite ao usuário acessar os Serviços Aguá/Prata.",
        "functions": ["Serviços"],
    },
    "156": {
        "name": "Libera a troca de Usuário / Empresa / Filial",
        "description": "Permite que o usuário fure a trava que restringe o login a um usuário, empresa e filial fixa.",
        "functions": ["Admin"],
    },
    "157": {
        "name": "Permite acesso ao Ambiente de Desenvolvimento",
        "description": "Permite ao usuário acessar o Ambiente de Desenvolvimento (TDS).",
        "functions": ["Desenvolvimento"],
    },
    "158": {
        "name": "Permite Utilização de Rotinas Automáticas",
        "description": "Permite ao usuário executar rotinas automáticas programadas.",
        "functions": ["Rotinas Automáticas"],
    },
    "159": {
        "name": "Acesso ao Módulo Fiscal",
        "description": "Permite ao usuário total acesso ao Módulo Fiscal.",
        "functions": ["Módulo Fiscal"],
    },
    "160": {
        "name": "Permite Acesso à rotina de Log de Auditoria",
        "description": "Permite ao usuário acessar a rotina de Log de Auditoria do Protheus.",
        "functions": ["Log de Auditoria"],
    },
    "161": {
        "name": "Permite Uso do Dispositivo Móvel",
        "description": "Permite ao usuário acessar as funcionalidades através do Dispositivo Móvel.",
        "functions": ["Dispositivo Móvel"],
    },
    "162": {
        "name": "Permite Integração com o Google Maps",
        "description": "Permite ao usuário utilizar as funcionalidades de integração com o Google Maps (Geolocalização).",
        "functions": ["Geolocalização"],
    },
    "163": {
        "name": "Permite Acesso ao Gestão de Cópias (GIT)",
        "description": "Permite ao usuário acessar a ferramenta de Gestão de Cópias (Versionamento).",
        "functions": ["Desenvolvimento"],
    },
    "164": {
        "name": "Permite Acesso à Agenda do Protheus",
        "description": "Permite ao usuário acessar a Agenda do Protheus (Calendário de Tarefas).",
        "functions": ["Agenda"],
    },
    "165": {
        "name": "Permite Acesso ao 'Protheus News'",
        "description": "Permite ao usuário acessar o 'Protheus News' (Notícias e Atualizações).",
        "functions": ["Protheus News"],
    },
    "166": {
        "name": "Permite Acesso à anotações da ocorrencia de um chamado",
        "description": "Permite ao usuário acessar as anotações das ocorrências de um chamado.",
        "functions": ["Chamados"],
    },
    "167": {
        "name": "Permite Login Unificado",
        "description": "Permite ao usuário realizar Login Unificado com outros sistemas TOTVS.",
        "functions": ["Login"],
    },
    "168": {
        "name": "Permite Acesso ao TOTVS Digital",
        "description": "Permite ao usuário acessar o TOTVS Digital.",
        "functions": ["TOTVS Digital"],
    },
    "169": {
        "name": "Permite Acesso ao 'Bate Papo'",
        "description": "Permite ao usuário acessar o 'Bate Papo' (Chat interno).",
        "functions": ["Bate Papo"],
    },
    "170": {
        "name": "Permite habilitar a manutenção de mensagens",
        "description": "Permite ao usuário habilitar a manutenção de mensagens (MSG).",
        "functions": ["Configuração"],
    },
    "171": {
        "name": "Permite Acesso ao TOTVS Stream",
        "description": "Permite ao usuário acessar o TOTVS Stream.",
        "functions": ["TOTVS Stream"],
    },
    "172": {
        "name": "Permite que sejam feitas alterações na logomarca do sistema",
        "description": "Permite ao usuário alterar a logomarca do sistema.",
        "functions": ["Configuração"],
    },
    "173": {
        "name": "Permite Acesso ao TOTVS Analytics",
        "description": "Permite ao usuário acessar o TOTVS Analytics.",
        "functions": ["Ferramentas de BI"],
    },
    "174": {
        "name": "Permite Acesso ao TOTVS Cloud",
        "description": "Permite ao usuário acessar as configurações do TOTVS Cloud.",
        "functions": ["Cloud"],
    },
    "175": {
        "name": "Permite Remessa e Retorno - CNAB",
        "description": "Permite ao usuário realizar remessa e retorno CNAB.",
        "functions": ["CNAB"],
    },
    "176": {
        "name": "Permite Acesso à Central de Atendimento",
        "description": "Permite ao usuário acessar a Central de Atendimento ao Cliente.",
        "functions": ["Central de Atendimento"],
    },
    "177": {
        "name": "Permite Acesso ao Protheus Analytics (Antigo)",
        "description": "Permite ao usuário acessar o Protheus Analytics (versão anterior).",
        "functions": ["Ferramentas de BI"],
    },
    "178": {
        "name": "Habilita o Botão do Explorer",
        "description": "Habilita o botão do Explorer no Protheus.",
        "functions": ["SmartClient"],
    },
    "179": {
        "name": "Permite Acesso à atualização de Cadastros via Planilhas",
        "description": "Permite ao usuário realizar atualização de cadastros via importação de planilhas.",
        "functions": ["Acesso genérico para planilhas/gráficos"],
    },
    "180": {
        "name": "Permite Acesso ao 'Eventos do Protheus'",
        "description": "Permite ao usuário acessar a rotina de Eventos do Protheus.",
        "functions": ["Eventos"],
    },
    "181": {
        "name": "Permite Acesso ao 'Minhas Notificações'",
        "description": "Permite ao usuário acessar a central de 'Minhas Notificações'.",
        "functions": ["Notificações"],
    },
    "182": {
        "name": "Permite Acesso ao Protheus Data Lake",
        "description": "Permite ao usuário acessar e configurar o Data Lake.",
        "functions": ["Data Lake"],
    },
    "183": {
        "name": "Permite configurar abertura de Caminho de pastas",
        "description": "Permite ao usuário configurar a abertura de caminhos de pastas.",
        "functions": ["Configuração"],
    },
    "184": {
        "name": "Permite Acesso ao TOTVS Assinatura Eletrônica",
        "description": "Permite ao usuário utilizar a Assinatura Eletrônica.",
        "functions": ["Assinatura Eletrônica"],
    },
    "185": {
        "name": "Permite Acesso ao TOTVS Gestão de Contratos",
        "description": "Permite ao usuário acessar o Gestão de Contratos.",
        "functions": ["Contratos"],
    },
    "186": {
        "name": "Permite Acesso ao TOTVS Robô",
        "description": "Permite ao usuário acessar o TOTVS Robô (Automação).",
        "functions": ["Automação"],
    },
    "187": {
        "name": "Permite Acesso ao Monitoramento de Transações",
        "description": "Permite ao usuário acessar o Monitoramento de Transações.",
        "functions": ["Monitoramento"],
    },
    "188": {
        "name": "Visualiza Registros Excluídos (Lixeira)",
        "description": "Não possui mais sentido de uso e será retirado do sistema num futuro próximo. Permitia ao usuário visualizar registros excluídos (Lixeira).",
        "functions": ["Acesso genérico para registros"],
    },
    "189": {
        "name": "Permite Acesso a Rotinas de Auditoria do Protheus",
        "description": "Permite ao usuário acessar as rotinas de Auditoria do Protheus.",
        "functions": ["Auditoria"],
    },
    "190": {
        "name": "Permite Acesso ao 'Time Line'",
        "description": "Permite ao usuário acessar a timeline de atualizações.",
        "functions": ["Timeline"],
    },
    "191": {
        "name": "Permite Acesso ao 'Protheus Docs'",
        "description": "Permite ao usuário acessar o 'Protheus Docs' (Consultas).",
        "functions": ["Documentação"],
    },
    "192": {
        "name": "Acesso a Dados Pessoais",
        "description": "O usuário que tiver esse Acesso terá permissão para visualizar relatórios/rotinas com dados pessoais.",
        "functions": ["LGPD - Dados Pessoais"],
    },
    "193": {
        "name": "Acesso a Dados Sensíveis",
        "description": "O usuário que tiver esse Acesso terá permissão para visualizar relatórios/rotinas com dados sensíveis.",
        "functions": ["LGPD - Dados Sensíveis"],
    },
    "194": {
        "name": "Pode executar o migrador de versão/release",
        "description": "O usuário que tiver esse Acesso terá permissão para executar o migrador de versão/release.",
        "functions": ["Migrador de Versão/Release"],
    },
    "195": {
        "name": "Reabertura de estoque",
        "description": "O usuário que possuir esse acesso terá permissão para reabrir o fechamento de estoque.",
        "functions": ["Fechamento de Estoque"],
    },
    "196": {
        "name": "Filtro - Visualiza outras filiais",
        "description": "O usuário que possuir esse acesso não terá Restrição de Dados pela Estrutura de Grupo de Empresas (por Filial).",
        "functions": ["Restrição de Dados pela Estrutura de Grupo de Empresas"],
    },
    "197": {
        "name": "Filtro - Visualiza outras Unidades de Negócio",
        "description": "O usuário que possuir esse acesso não terá Restrição de Dados pela Estrutura de Grupo de Empresas (por Unidade de Negócio).",
        "functions": ["Restrição de Dados pela Estrutura de Grupo de Empresas"],
    },
    "198": {
        "name": "Filtro - Visualiza outras Empresas",
        "description": "O usuário que possuir esse acesso não terá Restrição de Dados pela Estrutura de Grupo de Empresas (por Empresa).",
        "functions": ["Restrição de Dados pela Estrutura de Grupo de Empresas"],
    },
}


def _normalize_access_code(value):
    c_code = str(value or "").strip()
    if "." in c_code:
        try:
            c_code = str(int(float(c_code)))
        except (ValueError, OverflowError):
            pass
    return c_code


class UserMapper:
    def __init__(self, schema, conn):
        self.schema = schema
        self.conn = conn

    def resolve_col(self, table, candidates):
        return column_exists(self.schema, table, candidates)

    def safe_cols(self, table):
        return get_columns_list(self.schema, table)

    def build_select(self, table, wanted_cols):
        available = set(c.upper() for c in self.safe_cols(table))
        selected = [c for c in wanted_cols if c.upper() in available]
        return ", ".join(selected), selected

    def _normalize_access(self, value):
        c_value = str(value or "").strip().upper()

        if c_value in ("1", "S", "Y", "T", "TRUE", "PERMITIDO"):
            return "PERMITIDO"
        if c_value in ("3", "N", "NEGADO", "BLOQUEADO"):
            return "NEGADO"
        if c_value in ("2", "NAO_PERMITIDO", "NÃO_PERMITIDO", "NAO PERMITIDO", "NÃO PERMITIDO"):
            return "NAO_PERMITIDO"

        return "SEM_REGRA"

    def _access_rank(self, value):
        return {
            "NEGADO": 3,
            "PERMITIDO": 2,
            "NAO_PERMITIDO": 1,
            "SEM_REGRA": 0,
        }.get(self._normalize_access(value), 0)

    def _prefer_candidate(self, current, candidate):
        if current is None:
            return candidate

        n_current = self._normalize_access(current.get("access"))
        n_candidate = self._normalize_access(candidate.get("access"))

        if self._access_rank(n_candidate) > self._access_rank(n_current):
            return candidate
        if self._access_rank(n_candidate) < self._access_rank(n_current):
            return current
        if candidate.get("binding_type") == "user":
            return candidate
        return current

    def _row_value(self, row, column_name, default=None):
        if not column_name:
            return default
        return row.get(column_name, default)

    def _apply_non_blocked_user_filter(self, where, params):
        block_col = self.resolve_col("SYS_USR", ["USR_MSBLQL", "USR_BLOQUEIO", "USR_BLOCKED", "USR_STATUS", "USR_ATIVO"])
        del_col = self.resolve_col("SYS_USR", ["D_E_L_E_T_"])

        if block_col:
            if block_col.upper() == "USR_ATIVO":
                where += f" AND {block_col} <> ?"
                params.append("2")
            else:
                where += f" AND {block_col} <> ?"
                params.append("1")

        if del_col:
            where += f" AND {del_col} = ?"
            params.append(" ")

        return where, params

    def _build_rule_map(self, rule_ids, include_deleted_filter=True):
        if not rule_ids:
            return {}

        rul_pk = self.resolve_col("SYS_RULES", ["RL__ID", "RUL_ID", "ID"])
        rul_name = self.resolve_col("SYS_RULES", ["RL__CODIGO", "RUL_NAME", "NAME", "RULES_NAME"])
        rul_desc = self.resolve_col("SYS_RULES", ["RL__DESCRI", "RUL_DESC", "DESCRIPTION"])

        if not rul_pk:
            return {}

        placeholders = ",".join("?" for _ in rule_ids)
        rule_cols = [rul_pk]
        if rul_name:
            rule_cols.append(rul_name)
        if rul_desc:
            rule_cols.append(rul_desc)

        rows = fetch_dicts(self.conn,
            f"SELECT {', '.join(rule_cols)} FROM SYS_RULES WHERE {rul_pk} IN ({placeholders})",
            list(rule_ids))

        rules_map = {}
        for row in rows:
            c_rule_id = self._row_value(row, rul_pk)
            if c_rule_id in (None, ""):
                continue
            rules_map[c_rule_id] = {
                "rule_id": c_rule_id,
                "rule_name": row.get(rul_name, "") if rul_name else "",
                "rule_description": row.get(rul_desc, "") if rul_desc else "",
            }

        return rules_map

    def _load_rule_features(self, rule_ids):
        fet_rul = self.resolve_col("SYS_RULES_FEATURES", ["RL__ID", "FET_RUL_ID", "RUL_ID", "RFE_RUL_ID"])
        fet_func = self.resolve_col("SYS_RULES_FEATURES",
            ["RL__ROTINA", "FET_FUNCTION", "FUNCTION", "RFE_FUNCTION", "RFE_ROTINA"])
        fet_feat = self.resolve_col("SYS_RULES_FEATURES",
            ["RL__DESMDEF", "FET_FEATURE", "FEATURE", "RFE_FEATURE", "RFE_DESMDEF"])
        fet_access = self.resolve_col("SYS_RULES_FEATURES",
            ["RL__ACESSO", "FET_ACCESS", "ACCESS", "RFE_ACCESS", "RFE_ACESSO"])
        fet_menuoper = self.resolve_col("SYS_RULES_FEATURES", ["RL__MENUOPER", "MENUOPER"])
        fet_menudef = self.resolve_col("SYS_RULES_FEATURES", ["RL__MENUDEF", "MENUDEF"])
        fet_del = self.resolve_col("SYS_RULES_FEATURES", ["D_E_L_E_T_"])

        if not rule_ids or not fet_rul or not fet_func:
            return []

        placeholders = ",".join("?" for _ in rule_ids)
        feat_cols = [fet_rul, fet_func]
        if fet_feat:
            feat_cols.append(fet_feat)
        if fet_access:
            feat_cols.append(fet_access)
        if fet_menuoper:
            feat_cols.append(fet_menuoper)
        if fet_menudef:
            feat_cols.append(fet_menudef)

        feat_where = f"{fet_rul} IN ({placeholders})"
        feat_params = list(rule_ids)
        if fet_del:
            feat_where += f" AND {fet_del} = ?"
            feat_params.append(" ")

        return fetch_dicts(self.conn,
            f"SELECT {', '.join(feat_cols)} FROM SYS_RULES_FEATURES WHERE {feat_where}",
            feat_params)

    def _flatten_privilege_map_permissions(self, privileges):
        permissions = set()

        for routine, features in (privileges or {}).items():
            for feature, info in (features or {}).items():
                if self._normalize_access(info.get("access")) != "PERMITIDO":
                    continue
                c_routine = str(routine or "").strip().upper()
                c_feature = str(feature or "").strip()
                if c_routine and c_feature:
                    permissions.add(f"{c_routine}: {c_feature}")

        return permissions

    def _flatten_rule_permissions(self, privilege_set):
        permissions = set()

        for routine_info in privilege_set.get("routines", []) or []:
            c_routine = str(routine_info.get("routine") or "").strip().upper()
            if not c_routine:
                continue
            for feature_info in routine_info.get("features", []) or []:
                if self._normalize_access(feature_info.get("access")) != "PERMITIDO":
                    continue
                c_feature = str(feature_info.get("feature") or "").strip()
                if c_feature:
                    permissions.add(f"{c_routine}: {c_feature}")

        return permissions

    def _analyze_existing_privilege_recommendations(self, all_privileges, existing_privilege_sets):
        requested_permissions = self._flatten_privilege_map_permissions(all_privileges)
        recommendations = []

        for privilege_set in existing_privilege_sets or []:
            rule_permissions = self._flatten_rule_permissions(privilege_set)
            matched_permissions = sorted(requested_permissions & rule_permissions)
            missing_permissions = sorted(requested_permissions - rule_permissions)
            excess_permissions = sorted(rule_permissions - requested_permissions)

            if not matched_permissions and requested_permissions:
                coverage_status = "NENHUMA"
            elif not missing_permissions:
                coverage_status = "EXATA"
            else:
                coverage_status = "PARCIAL"

            recommendations.append({
                "rule_id": privilege_set.get("rule_id"),
                "rule_name": privilege_set.get("rule_name", ""),
                "rule_description": privilege_set.get("rule_description", ""),
                "coverage_status": coverage_status,
                "matched_permissions_count": len(matched_permissions),
                "requested_permissions_count": len(requested_permissions),
                "matched_permissions": matched_permissions,
                "missing_permissions": missing_permissions,
                "excess_permissions": excess_permissions,
                "has_excess_permissions": len(excess_permissions) > 0,
                "linked_users": privilege_set.get("linked_users", []),
                "linked_groups": privilege_set.get("linked_groups", []),
            })

        recommendations.sort(key=lambda item: (
            0 if item["coverage_status"] == "EXATA" else 1 if item["coverage_status"] == "PARCIAL" else 2,
            -item["matched_permissions_count"],
            len(item["missing_permissions"]),
            len(item["excess_permissions"]),
            str(item.get("rule_name", "")),
        ))

        suggested = recommendations[0] if recommendations and recommendations[0]["coverage_status"] != "NENHUMA" else None

        return {
            "requested_permissions": sorted(requested_permissions),
            "suggested_base_rule": suggested,
            "exact_matches": [item for item in recommendations if item["coverage_status"] == "EXATA"],
            "partial_matches": [item for item in recommendations if item["coverage_status"] == "PARCIAL"],
        }

    def map_existing_privilege_sets(self):
        rul_pk = self.resolve_col("SYS_RULES", ["RL__ID", "RUL_ID", "ID"])
        rul_name = self.resolve_col("SYS_RULES", ["RL__CODIGO", "RUL_NAME", "NAME", "RULES_NAME"])
        rul_desc = self.resolve_col("SYS_RULES", ["RL__DESCRI", "RUL_DESC", "DESCRIPTION"])

        if not rul_pk:
            return []

        rule_cols = [rul_pk]
        if rul_name:
            rule_cols.append(rul_name)
        if rul_desc:
            rule_cols.append(rul_desc)

        rule_rows = fetch_dicts(self.conn, f"SELECT {', '.join(rule_cols)} FROM SYS_RULES")
        if not rule_rows:
            return []

        privilege_sets = {}
        for row in rule_rows:
            c_rule_id = self._row_value(row, rul_pk)
            if c_rule_id in (None, ""):
                continue
            privilege_sets[c_rule_id] = {
                "rule_id": c_rule_id,
                "rule_name": row.get(rul_name, "") if rul_name else "",
                "rule_description": row.get(rul_desc, "") if rul_desc else "",
                "linked_users": [],
                "linked_groups": [],
                "routines": [],
            }

        rule_ids = list(privilege_sets.keys())
        if not rule_ids:
            return []

        fet_rul = self.resolve_col("SYS_RULES_FEATURES", ["RL__ID", "FET_RUL_ID", "RUL_ID", "RFE_RUL_ID"])
        fet_func = self.resolve_col("SYS_RULES_FEATURES", ["RL__ROTINA", "FET_FUNCTION", "FUNCTION", "RFE_FUNCTION", "RFE_ROTINA"])
        fet_feat = self.resolve_col("SYS_RULES_FEATURES", ["RL__DESMDEF", "FET_FEATURE", "FEATURE", "RFE_FEATURE", "RFE_DESMDEF"])
        fet_access = self.resolve_col("SYS_RULES_FEATURES", ["RL__ACESSO", "FET_ACCESS", "ACCESS", "RFE_ACCESS", "RFE_ACESSO"])
        fet_menuoper = self.resolve_col("SYS_RULES_FEATURES", ["RL__MENUOPER", "MENUOPER"])
        fet_menudef = self.resolve_col("SYS_RULES_FEATURES", ["RL__MENUDEF", "MENUDEF"])

        feature_rows = self._load_rule_features(rule_ids)
        routines_map = {rule_id: {} for rule_id in rule_ids}
        for row in feature_rows:
            c_rule_id = self._row_value(row, fet_rul)
            c_routine = str(self._row_value(row, fet_func, "") or "").strip().upper()
            if c_rule_id not in routines_map or not c_routine:
                continue
            routines_map[c_rule_id].setdefault(c_routine, [])
            routines_map[c_rule_id][c_routine].append({
                "feature": str(self._row_value(row, fet_feat, "") or "").strip(),
                "access": self._row_value(row, fet_access, ""),
                "menu_oper": self._row_value(row, fet_menuoper),
                "menu_def": str(self._row_value(row, fet_menudef, "") or "").strip(),
            })

        for rule_id, routines in routines_map.items():
            privilege_sets[rule_id]["routines"] = [
                {"routine": routine, "features": features}
                for routine, features in sorted(routines.items())
            ]

        usr_col = self.resolve_col("SYS_RULES_USR_RULES", ["USER_ID", "URR_USR_ID", "USR_ID", "RUR_USR_ID"])
        usr_rul_col = self.resolve_col("SYS_RULES_USR_RULES", ["USR_RL_ID", "URR_RUL_ID", "RUL_ID", "RUR_RUL_ID"])
        usr_pk = self.resolve_col("SYS_USR", ["USR_ID", "ID"])
        usr_login = self.resolve_col("SYS_USR", ["USR_CODIGO", "USR_LOGIN", "LOGIN", "USR_USERNAME", "USR_COD"])
        if usr_col and usr_rul_col and usr_pk:
            rows = fetch_dicts(self.conn, f"SELECT {usr_col}, {usr_rul_col} FROM SYS_RULES_USR_RULES")
            user_ids = sorted({row.get(usr_col) for row in rows if row.get(usr_col)})
            user_map = {}
            if user_ids and usr_login:
                placeholders = ",".join("?" for _ in user_ids)
                where = f"{usr_pk} IN ({placeholders})"
                params = list(user_ids)
                where, params = self._apply_non_blocked_user_filter(where, params)
                user_rows = fetch_dicts(self.conn,
                    f"SELECT {usr_pk}, {usr_login} FROM SYS_USR WHERE {where}",
                    params)
                user_map = {row[usr_pk]: str(row.get(usr_login, "") or "").strip() for row in user_rows}
            for row in rows:
                c_rule_id = row.get(usr_rul_col)
                c_user_id = row.get(usr_col)
                if user_map and c_user_id not in user_map:
                    continue
                if c_rule_id in privilege_sets:
                    privilege_sets[c_rule_id]["linked_users"].append({
                        "user_id": c_user_id,
                        "login": user_map.get(c_user_id, ""),
                    })

        grp_col = self.resolve_col("SYS_RULES_GRP_RULES", ["GROUP_ID", "GRR_GRP_ID", "GRP_ID", "RGR_GRP_ID"])
        grp_rul_col = self.resolve_col("SYS_RULES_GRP_RULES", ["GR__RL_ID", "GRR_RUL_ID", "RUL_ID", "RGR_RUL_ID"])
        grp_pk = self.resolve_col("SYS_GRP_GROUP", ["GR__ID", "GRP_ID", "ID"])
        grp_name = self.resolve_col("SYS_GRP_GROUP", ["GR__NOME", "GRP_NAME", "NAME", "GROUP_NAME"])
        if grp_col and grp_rul_col and grp_pk:
            rows = fetch_dicts(self.conn, f"SELECT {grp_col}, {grp_rul_col} FROM SYS_RULES_GRP_RULES")
            group_ids = sorted({row.get(grp_col) for row in rows if row.get(grp_col)})
            group_map = {}
            if group_ids and grp_name:
                placeholders = ",".join("?" for _ in group_ids)
                group_rows = fetch_dicts(self.conn,
                    f"SELECT {grp_pk}, {grp_name} FROM SYS_GRP_GROUP WHERE {grp_pk} IN ({placeholders})",
                    group_ids)
                group_map = {row[grp_pk]: str(row.get(grp_name, "") or "").strip() for row in group_rows}
            for row in rows:
                c_rule_id = row.get(grp_rul_col)
                if c_rule_id in privilege_sets:
                    privilege_sets[c_rule_id]["linked_groups"].append({
                        "group_id": row.get(grp_col),
                        "group_name": group_map.get(row.get(grp_col), ""),
                    })

        return list(privilege_sets.values())

    def _merge_privilege_maps(self, group_privileges, direct_privileges):
        privileges = {}

        for source in (group_privileges or {}, direct_privileges or {}):
            for func, features in source.items():
                privileges.setdefault(func, {})
                for feature, info in features.items():
                    privileges[func][feature] = self._prefer_candidate(privileges[func].get(feature), info)

        return privileges

    def _resolve_routine_access(self, translated_features, has_group_default, disabled_by_acbrowse):
        if disabled_by_acbrowse:
            return "NEGADO", "ACBROWSE", "ACBROWSE"

        best_access = "SEM_REGRA"
        best_source = ""
        best_reason = "NO_EXPLICIT_RULE"

        for info in translated_features.values():
            access = self._normalize_access(info.get("access"))
            if self._access_rank(access) > self._access_rank(best_access):
                best_access = access
                best_source = info.get("rule_name", "")
                best_reason = access

        if best_access == "SEM_REGRA" and has_group_default:
            return "NAO_PERMITIDO", "GROUP_DEFAULT", "GROUP_DEFAULT"

        return best_access, best_source, best_reason

    def find_user(self, login):
        pk_candidates = ["USR_ID", "ID"]
        pk = self.resolve_col("SYS_USR", pk_candidates)
        login_candidates = ["USR_CODIGO", "USR_LOGIN", "LOGIN", "USR_USERNAME", "USR_COD"]
        login_col = self.resolve_col("SYS_USR", login_candidates)
        depto_candidates = ["USR_DEPTO", "USR_DEPT", "DEPTO", "DEPARTMENT"]
        depto_col = self.resolve_col("SYS_USR", depto_candidates)
        name_candidates = ["USR_NOME", "USR_NAME", "NOME", "NAME", "USR_FULLNAME"]
        name_col = self.resolve_col("SYS_USR", name_candidates)

        if not pk or not login_col:
            print("  \033[93m[!]\033[0m Nao foi possivel identificar colunas em SYS_USR")
            return None

        select_cols = [pk, login_col]
        if depto_col:
            select_cols.append(depto_col)
        if name_col:
            select_cols.append(name_col)

        where = f"{login_col} = ?"
        params = [login]
        where, params = self._apply_non_blocked_user_filter(where, params)

        rows = fetch_dicts(self.conn,
            f"SELECT {', '.join(select_cols)} FROM SYS_USR WHERE {where}",
            params)
        if not rows:
            print(f"  \033[93m[!]\033[0m Usuario '\033[1m{login}\033[0m' nao encontrado em SYS_USR")
            return None

        user = rows[0]
        depto_info = f" (Depto: {user[depto_col].strip()})" if depto_col and user.get(depto_col) and user[depto_col].strip() else ""
        name_info = f" - {user[name_col].strip()}" if name_col and user.get(name_col) and user[name_col].strip() else ""
        print(f"  \033[92m[OK]\033[0m Usuario{name_info}: \033[1m{user[login_col].strip()}\033[0m (ID: {user[pk]}){depto_info}")
        return {
            "id": user[pk],
            "login": user[login_col],
            "pk_col": pk,
            "depto": user.get(depto_col, "").strip() if depto_col else "",
            "name": user.get(name_col, "").strip() if name_col else "",
        }

    def list_non_blocked_users(self):
        pk_candidates = ["USR_ID", "ID"]
        pk = self.resolve_col("SYS_USR", pk_candidates)
        login_candidates = ["USR_CODIGO", "USR_LOGIN", "LOGIN", "USR_USERNAME", "USR_COD"]
        login_col = self.resolve_col("SYS_USR", login_candidates)
        depto_candidates = ["USR_DEPTO", "USR_DEPT", "DEPTO", "DEPARTMENT"]
        depto_col = self.resolve_col("SYS_USR", depto_candidates)
        name_candidates = ["USR_NOME", "USR_NAME", "NOME", "NAME", "USR_FULLNAME"]
        name_col = self.resolve_col("SYS_USR", name_candidates)

        if not pk or not login_col:
            print("  \033[93m[!]\033[0m Nao foi possivel identificar colunas em SYS_USR")
            return []

        select_cols = [pk, login_col]
        if depto_col:
            select_cols.append(depto_col)
        if name_col:
            select_cols.append(name_col)

        where = "1=1"
        params = []

        where, params = self._apply_non_blocked_user_filter(where, params)

        rows = fetch_dicts(self.conn,
            f"SELECT {', '.join(select_cols)} FROM SYS_USR WHERE {where}",
            params)

        users = []
        for row in rows:
            users.append({
                "id": row[pk],
                "login": row[login_col].strip() if row[login_col] else "",
                "depto": row[depto_col].strip() if depto_col and row.get(depto_col) else "",
                "name": row[name_col].strip() if name_col and row.get(name_col) else "",
            })

        print(f"  \033[92m[OK]\033[0m Usuarios nao bloqueados encontrados: \033[1m{len(users)}\033[0m")
        return users

    def map_menu_modules(self, user_id):
        usr_col = self.resolve_col("SYS_USR_MODULE", ["USR_ID", "UMD_USR_ID", "USM_USR_ID"])
        menu_col = self.resolve_col("SYS_USR_MODULE", ["USR_ARQMENU", "USR_MODULO", "USR_CODMOD", "UMD_MENU_ID", "MENU_ID", "USM_MENU_ID"])
        access_col = self.resolve_col("SYS_USR_MODULE", ["USR_ACESSO", "ACESSO"])
        del_col = self.resolve_col("SYS_USR_MODULE", ["D_E_L_E_T_"])

        if not usr_col or not menu_col:
            print("  \033[93m[AVISO]\033[0m Tabela SYS_USR_MODULE nao encontrada ou colunas nao identificadas")
            return []

        where = f"{usr_col} = ?"
        params = [user_id]
        if access_col:
            where += f" AND {access_col} = ?"
            params.append("T")
        if del_col:
            where += f" AND {del_col} = ?"
            params.append(" ")

        rows = fetch_dicts(self.conn,
            f"SELECT {menu_col} FROM SYS_USR_MODULE WHERE {where}",
            params)

        menu_ids = [row[menu_col] for row in rows]
        print(f"  Menus diretos do usuario (ativos): {len(menu_ids)} encontrados")
        return menu_ids, menu_col

    def map_user_access_codes(self, user_id):
        usr_col = self.resolve_col("SYS_USR_ACCESS", ["USR_ID", "USA_USR_ID", "USER_ID"])
        code_col = self.resolve_col("SYS_USR_ACCESS", ["USR_CODACESSO", "USA_CODACESSO", "COD_ACESSO", "ACCESS_CODE"])
        enabled_col = self.resolve_col("SYS_USR_ACCESS", ["USR_ACESSO", "USA_ACESSO", "ACESSO", "ACCESS"])
        del_col = self.resolve_col("SYS_USR_ACCESS", ["D_E_L_E_T_"])

        if not usr_col or not code_col:
            return []

        where = f"{usr_col} = ?"
        params = [user_id]
        if enabled_col:
            where += f" AND {enabled_col} = ?"
            params.append("T")
        if del_col:
            where += f" AND {del_col} = ?"
            params.append(" ")

        rows = fetch_dicts(self.conn,
            f"SELECT {code_col}{', ' + enabled_col if enabled_col else ''} FROM SYS_USR_ACCESS WHERE {where}",
            params)

        result = []
        for row in rows:
            c_code_raw = str(row.get(code_col) or "").strip()
            if not c_code_raw:
                continue
            c_code = _normalize_access_code(c_code_raw)
            if not c_code:
                continue
            code_info = USER_ACCESS_CODES.get(c_code, {})
            result.append({
                "code": c_code,
                "enabled": str(row.get(enabled_col) or "T").strip().upper() == "T" if enabled_col else True,
                "name": code_info.get("name", ""),
                "description": code_info.get("description", ""),
                "functions": code_info.get("functions", []),
            })

        return sorted(result, key=lambda item: item["code"])

    def map_menu_tree(self, menu_ids, join_column=None):
        if not menu_ids:
            return []

        m_pk = self.resolve_col("MPMENU_MENU", ["M_ID", "ID"])
        m_name = self.resolve_col("MPMENU_MENU", ["M_NAME", "NAME"])
        m_module = self.resolve_col("MPMENU_MENU", ["M_MODULE", "MODULE"])
        m_del = self.resolve_col("MPMENU_MENU", ["D_E_L_E_T_"])

        if not m_pk:
            print("  [AVISO] Tabela MPMENU_MENU nao encontrada")
            return []

        use_module_join = (join_column == "USR_MODULO" and m_module is not None)
        join_col = m_module if use_module_join else m_pk

        base_cols = [m_pk, m_module] if use_module_join else [m_pk]
        if m_name:
            base_cols.append(m_name)

        placeholders = ",".join("?" for _ in menu_ids)
        where = f"{join_col} IN ({placeholders})"
        params = list(menu_ids)
        if m_del:
            where += f" AND {m_del} = ?"
            params.append(" ")
        if m_name:
            where += f" AND {m_name} NOT LIKE ?"
            params.append("#%")

        menus = fetch_dicts(self.conn,
            f"SELECT {', '.join(base_cols)} FROM MPMENU_MENU WHERE {where}",
            params)

        result = []
        for menu in menus:
            menu_data = {
                "menu_id": menu[m_pk],
                "menu_name": menu.get(m_name, "") if m_name else "",
                "module": menu.get(m_module, "") if m_module else "",
                "items": self._map_menu_items(menu[m_pk]),
            }
            item_count = len(menu_data["items"])
            print(f"  Menu '{menu_data['menu_name']}': {item_count} itens mapeados")
            result.append(menu_data)

        return result

    def _map_menu_items(self, menu_id):
        i_pk = self.resolve_col("MPMENU_ITEM", ["I_ID", "ID"])
        i_menu = self.resolve_col("MPMENU_ITEM", ["I_ID_MENU", "ID_MENU", "I_MENU_ID"])
        i_func = self.resolve_col("MPMENU_ITEM", ["I_ID_FUNC", "ID_FUNC", "I_FUNC_ID"])
        i_father = self.resolve_col("MPMENU_ITEM", ["I_FATHER", "FATHER", "I_PARENT"])
        i_status = self.resolve_col("MPMENU_ITEM", ["I_STATUS", "STATUS"])
        i_access = self.resolve_col("MPMENU_ITEM", ["I_ACCESS", "ACCESS"])
        i_tp_menu = self.resolve_col("MPMENU_ITEM", ["I_TP_MENU", "TP_MENU"])
        i_del = self.resolve_col("MPMENU_ITEM", ["D_E_L_E_T_"])

        f_pk = self.resolve_col("MPMENU_FUNCTION", ["F_ID", "ID"])
        f_func = self.resolve_col("MPMENU_FUNCTION", ["F_FUNCTION", "FUNCTION", "F_ROTINA"])

        n_parent = self.resolve_col("MPMENU_I18N", ["N_PAREN_ID", "PAREN_ID", "I18N_PAREN_ID"])
        n_lang = self.resolve_col("MPMENU_I18N", ["N_LANG", "LANG"])
        n_desc = self.resolve_col("MPMENU_I18N", ["N_DESC", "DESC", "DESCRIPTION"])
        n_del = self.resolve_col("MPMENU_I18N", ["D_E_L_E_T_"])

        if not i_pk or not i_menu:
            return []

        item_cols = [i_pk]
        if i_father:
            item_cols.append(i_father)
        if i_func:
            item_cols.append(i_func)
        if i_access:
            item_cols.append(i_access)
        if i_tp_menu:
            item_cols.append(i_tp_menu)

        where = f"{i_menu} = ?"
        params = [menu_id]
        if i_status:
            where += f" AND {i_status} = ?"
            params.append("1")
        if i_del:
            where += f" AND {i_del} = ?"
            params.append(" ")

        items = fetch_dicts(self.conn,
            f"SELECT {', '.join(item_cols)} FROM MPMENU_ITEM WHERE {where} ORDER BY {i_pk}",
            params)

        item_ids = [it[i_pk] for it in items]
        function_ids = [it[i_func] for it in items if i_func and it.get(i_func) is not None]

        functions_map = {}
        if function_ids and f_pk and f_func:
            placeholders = ",".join("?" for _ in function_ids)
            func_rows = fetch_dicts(self.conn,
                f"SELECT {f_pk}, {f_func} FROM MPMENU_FUNCTION WHERE {f_pk} IN ({placeholders})",
                function_ids)
            functions_map = {row[f_pk]: row.get(f_func, "") for row in func_rows}

        desc_map = {}
        if n_parent and n_lang and n_desc and item_ids:
            placeholders = ",".join("?" for _ in item_ids)
            desc_where = f"{n_parent} IN ({placeholders}) AND {n_lang} = ?"
            desc_params = list(item_ids) + ["1"]
            if n_del:
                desc_where += f" AND {n_del} = ?"
                desc_params.append(" ")
            desc_rows = fetch_dicts(self.conn,
                f"SELECT {n_parent}, {n_desc} FROM MPMENU_I18N WHERE {desc_where}",
                desc_params)
            desc_map = {row[n_parent]: row[n_desc] for row in desc_rows}

        result = []
        for item in items:
            item_id = item[i_pk]
            father_id = item.get(i_father) if i_father else None
            func_id = item.get(i_func) if i_func else None
            access_raw = (item.get(i_access) or "").strip() if i_access else ""
            tp_menu = (item.get(i_tp_menu) or "").strip() if i_tp_menu else ""

            func_code = functions_map.get(func_id, "") if func_id else ""
            description = desc_map.get(item_id, desc_map.get(father_id, ""))

            browse_features = {}
            if tp_menu == "2" and access_raw:
                for idx, feature_name in enumerate(BROWSE_FEATURES):
                    if idx < len(access_raw):
                        browse_features[feature_name] = (access_raw[idx] in ("x", "X", "1"))

            result.append({
                "item_id": item_id,
                "father_id": father_id,
                "function_code": func_code,
                "description": description,
                "tp_menu": tp_menu,
                "browse_features": browse_features,
            })

        return result

    def map_user_groups(self, user_id):
        usr_col = self.resolve_col("SYS_USR_GROUPS", ["USR_ID", "USG_USR_ID", "USG_USER_ID"])
        grp_col = self.resolve_col("SYS_USR_GROUPS", ["USR_GRUPO", "USG_GRP_ID", "GRP_ID", "USG_GROUP_ID"])
        del_col = self.resolve_col("SYS_USR_GROUPS", ["D_E_L_E_T_"])

        if not usr_col or not grp_col:
            print("  [AVISO] Tabela SYS_USR_GROUPS nao encontrada")
            return []

        where = f"{usr_col} = ?"
        params = [user_id]
        if del_col:
            where += f" AND {del_col} = ?"
            params.append(" ")

        rows = fetch_dicts(self.conn,
            f"SELECT {grp_col} FROM SYS_USR_GROUPS WHERE {where}",
            params)

        group_ids = [row[grp_col] for row in rows]

        grp_name = self.resolve_col("SYS_GRP_GROUP", ["GR__NOME", "GRP_NAME", "NAME", "GROUP_NAME"])
        grp_pk = self.resolve_col("SYS_GRP_GROUP", ["GR__ID", "GRP_ID", "ID"])

        groups = []
        if group_ids and grp_pk and grp_name:
            placeholders = ",".join("?" for _ in group_ids)
            grp_rows = fetch_dicts(self.conn,
                f"SELECT {grp_pk}, {grp_name} FROM SYS_GRP_GROUP WHERE {grp_pk} IN ({placeholders})",
                group_ids)
            groups = [{"group_id": self._row_value(row, grp_pk), "group_name": self._row_value(row, grp_name, "")} for row in grp_rows if self._row_value(row, grp_pk) not in (None, "")]

        print(f"  Grupos do usuario: {len(groups)} encontrados")
        return groups

    def map_group_privileges(self, group_ids):
        if not group_ids:
            return {}

        grp_ids = list(group_ids)

        gr_col = self.resolve_col("SYS_RULES_GRP_RULES", ["GROUP_ID", "GRR_GRP_ID", "GRP_ID", "RGR_GRP_ID"])
        rul_col = self.resolve_col("SYS_RULES_GRP_RULES", ["GR__RL_ID", "GRR_RUL_ID", "RUL_ID", "RGR_RUL_ID"])

        if not gr_col or not rul_col:
            print("  [AVISO] Tabela SYS_RULES_GRP_RULES nao encontrada")
            return {}

        placeholders = ",".join("?" for _ in grp_ids)
        gr_rules = fetch_dicts(self.conn,
            f"SELECT DISTINCT {rul_col} FROM SYS_RULES_GRP_RULES WHERE {gr_col} IN ({placeholders})",
            grp_ids)

        rule_ids = list(set(r[rul_col] for r in gr_rules))

        rul_pk = self.resolve_col("SYS_RULES", ["RL__ID", "RUL_ID", "ID"])
        rul_name = self.resolve_col("SYS_RULES", ["RL__CODIGO", "RUL_NAME", "NAME", "RULES_NAME"])

        rules_map = {}
        if rule_ids and rul_pk:
            placeholders = ",".join("?" for _ in rule_ids)
            rule_cols = [rul_pk]
            if rul_name:
                rule_cols.append(rul_name)
            rule_rows = fetch_dicts(self.conn,
                f"SELECT {', '.join(rule_cols)} FROM SYS_RULES WHERE {rul_pk} IN ({placeholders})",
                rule_ids)
            rules_map = {self._row_value(row, rul_pk): row.get(rul_name, "") if rul_name else "" for row in rule_rows if self._row_value(row, rul_pk) not in (None, "")}

        fet_rul = self.resolve_col("SYS_RULES_FEATURES", ["RL__ID", "FET_RUL_ID", "RUL_ID", "RFE_RUL_ID"])
        fet_func = self.resolve_col("SYS_RULES_FEATURES",
            ["RL__ROTINA", "FET_FUNCTION", "FUNCTION", "RFE_FUNCTION", "RFE_ROTINA"])
        fet_feat = self.resolve_col("SYS_RULES_FEATURES",
            ["RL__DESMDEF", "FET_FEATURE", "FEATURE", "RFE_FEATURE", "RFE_DESMDEF"])
        fet_access = self.resolve_col("SYS_RULES_FEATURES",
            ["RL__ACESSO", "FET_ACCESS", "ACCESS", "RFE_ACCESS", "RFE_ACESSO"])
        fet_menuoper = self.resolve_col("SYS_RULES_FEATURES", ["RL__MENUOPER", "MENUOPER"])
        fet_menudef = self.resolve_col("SYS_RULES_FEATURES", ["RL__MENUDEF", "MENUDEF"])
        fet_del = self.resolve_col("SYS_RULES_FEATURES", ["D_E_L_E_T_"])

        privileges = {}
        if rule_ids and fet_rul and fet_func:
            placeholders = ",".join("?" for _ in rule_ids)
            feat_cols = [fet_rul, fet_func]
            if fet_feat:
                feat_cols.append(fet_feat)
            if fet_access:
                feat_cols.append(fet_access)
            if fet_menuoper:
                feat_cols.append(fet_menuoper)
            if fet_menudef:
                feat_cols.append(fet_menudef)

            feat_where = f"{fet_rul} IN ({placeholders})"
            feat_params = list(rule_ids)
            if fet_del:
                feat_where += f" AND {fet_del} = ?"
                feat_params.append(" ")

            feat_rows = fetch_dicts(self.conn,
                f"SELECT {', '.join(feat_cols)} FROM SYS_RULES_FEATURES WHERE {feat_where}",
                feat_params)

            for row in feat_rows:
                c_rule_id = self._row_value(row, fet_rul)
                func = self._row_value(row, fet_func, "")
                feature = self._row_value(row, fet_feat, "") if fet_feat else ""
                access = self._row_value(row, fet_access, "?") if fet_access else "?"
                menu_oper = self._row_value(row, fet_menuoper) if fet_menuoper else None
                menu_def = self._row_value(row, fet_menudef, "") if fet_menudef else ""
                if c_rule_id in (None, "") or not func:
                    continue
                rule_name = rules_map.get(c_rule_id, f"Rule_{c_rule_id}")

                if func not in privileges:
                    privileges[func] = {}
                privileges[func][feature] = {
                    "access": access,
                    "rule_name": rule_name,
                    "rule_id": c_rule_id,
                    "menu_oper": menu_oper,
                    "menu_def": menu_def,
                    "binding_type": "group",
                }

        print(f"  Privilegios mapeados: {len(privileges)} rotinas com features")
        return privileges

    def map_user_privileges_direct(self, user_id):
        usr_col = self.resolve_col("SYS_RULES_USR_RULES", ["USER_ID", "URR_USR_ID", "USR_ID", "RUR_USR_ID"])
        rul_col = self.resolve_col("SYS_RULES_USR_RULES", ["USR_RL_ID", "URR_RUL_ID", "RUL_ID", "RUR_RUL_ID"])

        if not usr_col or not rul_col:
            return {}

        placeholders = ",".join("?" for _ in [user_id])
        rows = fetch_dicts(self.conn,
            f"SELECT DISTINCT {rul_col} FROM SYS_RULES_USR_RULES WHERE {usr_col} = ?",
            (user_id,))

        rule_ids = list(set(r[rul_col] for r in rows))

        rules_map = self._build_rule_map(rule_ids)

        fet_rul = self.resolve_col("SYS_RULES_FEATURES", ["RL__ID", "FET_RUL_ID", "RUL_ID"])
        fet_func = self.resolve_col("SYS_RULES_FEATURES",
            ["RL__ROTINA", "FET_FUNCTION", "FUNCTION"])
        fet_feat = self.resolve_col("SYS_RULES_FEATURES",
            ["RL__DESMDEF", "FET_FEATURE", "FEATURE"])
        fet_access = self.resolve_col("SYS_RULES_FEATURES",
            ["RL__ACESSO", "FET_ACCESS", "ACCESS"])
        fet_menuoper = self.resolve_col("SYS_RULES_FEATURES", ["RL__MENUOPER", "MENUOPER"])
        fet_menudef = self.resolve_col("SYS_RULES_FEATURES", ["RL__MENUDEF", "MENUDEF"])
        fet_del = self.resolve_col("SYS_RULES_FEATURES", ["D_E_L_E_T_"])

        privileges = {}
        if rule_ids and fet_rul and fet_func:
            placeholders = ",".join("?" for _ in rule_ids)
            feat_cols = [fet_rul, fet_func]
            if fet_feat:
                feat_cols.append(fet_feat)
            if fet_access:
                feat_cols.append(fet_access)
            if fet_menuoper:
                feat_cols.append(fet_menuoper)
            if fet_menudef:
                feat_cols.append(fet_menudef)

            feat_where = f"{fet_rul} IN ({placeholders})"
            feat_params = list(rule_ids)
            if fet_del:
                feat_where += f" AND {fet_del} = ?"
                feat_params.append(" ")

            feat_rows = fetch_dicts(self.conn,
                f"SELECT {', '.join(feat_cols)} FROM SYS_RULES_FEATURES WHERE {feat_where}",
                feat_params)

            for row in feat_rows:
                c_rule_id = self._row_value(row, fet_rul)
                func = self._row_value(row, fet_func, "")
                feature = self._row_value(row, fet_feat, "") if fet_feat else ""
                access = self._row_value(row, fet_access, "?") if fet_access else "?"
                menu_oper = self._row_value(row, fet_menuoper) if fet_menuoper else None
                menu_def = self._row_value(row, fet_menudef, "") if fet_menudef else ""
                if c_rule_id in (None, "") or not func:
                    continue
                if func not in privileges:
                    privileges[func] = {}
                privileges[func][feature] = {
                    "access": access,
                    "rule_name": rules_map.get(c_rule_id, {}).get("rule_name", f"Rule_{c_rule_id}"),
                    "rule_id": c_rule_id,
                    "menu_oper": menu_oper,
                    "menu_def": menu_def,
                    "binding_type": "user",
                }

        return privileges

    def map_system_profile(self, user_id):
        try:
            rows = fetch_dicts(self.conn,
                "SELECT RTRIM(P_NAME) AS P_NAME, RTRIM(P_PROG) AS P_PROG, "
                "RTRIM(P_TASK) AS P_TASK, RTRIM(P_TYPE) AS P_TYPE, P_DEFS "
                "FROM MP_SYSTEM_PROFILE "
                "WHERE RTRIM(P_NAME) = ? AND P_TYPE = 'ACBROWSE' AND D_E_L_E_T_ = ' '",
                (user_id,))
        except Exception:
            return {}

        overrides = {}
        for row in rows:
            prog = (row.get("P_PROG") or "").strip()
            data = self._to_bytes(row.get("P_DEFS"))
            if not data or len(data) < 6:
                continue
            entries = self._parse_acbrowse(data)
            if prog not in overrides:
                overrides[prog] = {}
            overrides[prog].update(entries)

        return overrides

    def _to_bytes(self, value):
        if value is None:
            return b""
        if isinstance(value, bytes):
            return value
        if isinstance(value, str):
            if not value.strip():
                return b""
            import base64
            try:
                return base64.b64decode(value)
            except Exception:
                return value.encode("latin-1")
        return bytes(value)

    def _parse_acbrowse(self, data):
        entries = {}
        pos = 0
        routine = None
        while pos + 5 <= len(data):
            typ = chr(data[pos]) if data[pos] < 128 else "?"
            val = struct.unpack_from("<I", data, pos + 1)[0]
            pos += 5
            if typ == "C":
                chunk = data[pos:pos + val]
                pos += val
                text = chunk.decode("ascii", errors="replace").rstrip("\0")
                if not routine:
                    routine = text
                else:
                    entries[routine] = text
                    routine = None
            elif typ == "A":
                pass
            elif typ in ("D", "E"):
                pass
            else:
                break
        return entries

    def map_routine_users(self, routine):
        f_pk = self.resolve_col("MPMENU_FUNCTION", ["F_ID", "ID"])
        f_func = self.resolve_col("MPMENU_FUNCTION", ["F_FUNCTION", "FUNCTION", "F_ROTINA"])
        if not f_func or not f_pk:
            return {"user_ids": [], "routine": routine, "error": "MPMENU_FUNCTION not found"}

        f_rows = fetch_dicts(self.conn,
            f"SELECT {f_pk} FROM MPMENU_FUNCTION WHERE {f_func} = ?",
            (routine,))
        if not f_rows:
            return {"user_ids": [], "routine": routine}

        func_id = f_rows[0][f_pk]

        i_menu = self.resolve_col("MPMENU_ITEM", ["I_ID_MENU", "ID_MENU", "I_MENU_ID"])
        i_func = self.resolve_col("MPMENU_ITEM", ["I_ID_FUNC", "ID_FUNC", "I_FUNC_ID"])

        if not i_func or not i_menu:
            return {"user_ids": [], "routine": routine, "error": "MPMENU_ITEM not found"}

        i_rows = fetch_dicts(self.conn,
            f"SELECT {i_menu} FROM MPMENU_ITEM WHERE {i_func} = ?",
            (func_id,))
        menu_ids = list(set(r[i_menu] for r in i_rows))
        if not menu_ids:
            return {"user_ids": [], "routine": routine}

        placeholders = ",".join("?" for _ in menu_ids)
        usr_col = self.resolve_col("SYS_USR_MODULE", ["USR_ID", "UMD_USR_ID"])
        menu_col = self.resolve_col("SYS_USR_MODULE", ["USR_ARQMENU", "USR_MODULO", "UMD_MENU_ID"])

        user_ids = set()
        if usr_col and menu_col:
            rows = fetch_dicts(self.conn,
                f"SELECT DISTINCT {usr_col} FROM SYS_USR_MODULE WHERE {menu_col} IN ({placeholders})",
                menu_ids)
            user_ids = set(str(r[usr_col]) for r in rows)

        if not user_ids:
            return {"user_ids": [], "routine": routine,
                    "function_id": func_id, "menu_ids": menu_ids}

        usr_pk = self.resolve_col("SYS_USR", ["USR_ID", "ID"])
        usr_login = self.resolve_col("SYS_USR", ["USR_CODIGO", "USR_LOGIN", "LOGIN", "USR_USERNAME", "USR_COD"])
        if not usr_pk or not usr_login:
            return {"user_ids": sorted(user_ids), "routine": routine,
                    "function_id": func_id, "menu_ids": menu_ids}

        placeholders = ",".join("?" for _ in user_ids)
        where = f"{usr_pk} IN ({placeholders})"
        params = list(user_ids)
        where, params = self._apply_non_blocked_user_filter(where, params)
        user_rows = fetch_dicts(self.conn,
            f"SELECT {usr_pk}, {usr_login} FROM SYS_USR WHERE {where}",
            params)

        allowed_user_ids = set()
        c_routine = str(routine or "").strip().upper()
        for row in user_rows:
            c_login = str(row.get(usr_login) or "").strip()
            if not c_login:
                continue
            report = self.build_full_report(c_login)
            if not report:
                continue
            for routine_info in report.get("routines_summary", []):
                if str(routine_info.get("routine") or "").strip().upper() != c_routine:
                    continue
                if str(routine_info.get("effective_access") or "").strip().upper() == "PERMITIDO":
                    allowed_user_ids.add(str(row.get(usr_pk)))
                    break

        return {"user_ids": sorted(allowed_user_ids), "routine": routine,
                "function_id": func_id, "menu_ids": menu_ids}

    def build_full_report(self, login):
        G = "\033[92m"; C = "\033[96m"; Y = "\033[93m"; D = "\033[2m"; B = "\033[1m"; R = "\033[0m"

        print(f"\n  {C}[1/4]{R} Buscando usuario '{B}{login}{R}'...")
        user = self.find_user(login)
        if not user:
            return None

        print(f"\n  {C}[2/4]{R} Mapeando menus do usuario...")
        menu_ids, menu_col = self.map_menu_modules(user["id"])
        menu_tree = self.map_menu_tree(menu_ids, menu_col)

        acbrowse_overrides = self.map_system_profile(user["id"])

        def _get_program_overrides(menu):
            c_menu_name = str(menu.get("menu_name") or "").strip()
            if c_menu_name and c_menu_name in acbrowse_overrides:
                return acbrowse_overrides[c_menu_name]
            return {}

        def _get_ancestor_status(item_id, by_id, program_overrides):
            cur = by_id.get(item_id)
            while cur:
                father = cur.get("father_id")
                if not father:
                    return None
                cur = by_id.get(father)
                if not cur:
                    return None
                desc = (cur.get("description") or "").strip()
                if desc in program_overrides and program_overrides[desc] == "D":
                    return "DISABLED"
                if desc in program_overrides and program_overrides[desc] in ("E", "D"):
                    return "ENABLED" if program_overrides[desc] == "E" else "DISABLED"
            return None

        # build a flat lookup (item_id -> item) for ancestor walking
        all_items_by_id = {}
        for menu in menu_tree:
            for item in menu.get("items", []):
                iid = item.get("item_id", "")
                if iid:
                    all_items_by_id[iid] = item

        def _get_effective_permission(item, program_overrides):
            desc = (item.get("description") or "").strip()
            func = (item.get("function_code") or "").strip()

            ancestor = _get_ancestor_status(item.get("item_id", ""), all_items_by_id, program_overrides)
            folder_status = ancestor

            if desc in program_overrides and program_overrides[desc] in ("D", "E"):
                folder_status = "DISABLED" if program_overrides[desc] == "D" else "ENABLED"

            override_str = None
            if func and func in program_overrides:
                ov = program_overrides[func]
                if ov not in ("D", "E"):
                    override_str = ov
            elif desc in program_overrides:
                ov = program_overrides[desc]
                if ov not in ("D", "E"):
                    override_str = ov

            return folder_status, override_str

        print(f"\n  {C}[3/4]{R} Mapeando grupos e privilegios...")
        groups = self.map_user_groups(user["id"])
        access_codes = self.map_user_access_codes(user["id"])
        group_ids = [g["group_id"] for g in groups]
        group_privileges = self.map_group_privileges(group_ids)
        direct_privileges = self.map_user_privileges_direct(user["id"])
        try:
            existing_privilege_sets = self.map_existing_privilege_sets()
        except Exception as e:
            print(f"  [AVISO] Nao foi possivel inventariar regras existentes: {e}")
            existing_privilege_sets = []

        all_privileges = self._merge_privilege_maps(group_privileges, direct_privileges)
        privilege_recommendations = self._analyze_existing_privilege_recommendations(all_privileges, existing_privilege_sets)
        has_group_default = any(
            str(group.get("group_id", "")).strip() == "*" or str(group.get("group_name", "")).strip() == "*"
            for group in groups
        )

        print(f"\n  {C}[4/4]{R} Consolidando relatorio...")
        routines_flat = []
        seen = set()
        for menu in menu_tree:
            program_overrides = _get_program_overrides(menu)
            for item in menu.get("items", []):
                func = item.get("function_code", "")
                if not func or func in seen:
                    continue
                seen.add(func)
                priv_for_func = all_privileges.get(func, {})

                translated_features = {}
                for feat, info in priv_for_func.items():
                    translated_features[feat] = {
                        "access": self._normalize_access(info["access"]),
                        "access_raw": info["access"],
                        "rule_name": info["rule_name"],
                        "menu_oper": info.get("menu_oper"),
                        "menu_def": info.get("menu_def", ""),
                    }

                browse_features_available = item.get("browse_features", {})
                acbrowse_status, acbrowse_override = _get_effective_permission(item, program_overrides)
                disabled_by_acbrowse = (acbrowse_status in ("D", "DISABLED"))

                if acbrowse_override and len(acbrowse_override) >= 10:
                    for pos in range(min(10, len(acbrowse_override))):
                        fname = BROWSE_FEATURES[pos] if pos < len(BROWSE_FEATURES) else f"OP{pos+1}"
                        if acbrowse_override[pos] == " ":
                            browse_features_available[fname] = False
                        elif acbrowse_override[pos] in ("x", "X"):
                            browse_features_available[fname] = True

                browse_permissions = []
                if browse_features_available:
                    for pos in range(10):
                        menu_oper = float(pos + 1)
                        avail = browse_features_available.get(BROWSE_FEATURES[pos], False) if pos < len(BROWSE_FEATURES) else False
                        if disabled_by_acbrowse:
                            avail = False
                        op_features = []
                        for fname, finfo in priv_for_func.items():
                            fmo = finfo.get("menu_oper")
                            if fmo is not None:
                                fmo = float(fmo)
                                if abs(fmo - menu_oper) < 0.001:
                                    op_features.append({
                                        "name": fname.strip() if fname else "",
                                        "action": (finfo.get("menu_def") or "").strip(),
                                        "granted": self._normalize_access(finfo["access"]),
                                        "access_raw": finfo["access"],
                                    })
                        browse_permissions.append({
                            "pos": pos,
                            "menu_oper": int(menu_oper),
                            "available": avail,
                            "features": op_features,
                        })

                effective_access, decision_source, denial_reason = self._resolve_routine_access(
                    translated_features,
                    has_group_default,
                    disabled_by_acbrowse,
                )

                routines_flat.append({
                    "routine": func,
                    "description": item.get("description", ""),
                    "menu_name": menu.get("menu_name", ""),
                    "module": menu.get("module", ""),
                    "in_menu": True,
                    "features": translated_features,
                    "has_explicit_privilege": len(priv_for_func) > 0,
                    "effective_access": effective_access,
                    "decision_source": decision_source,
                    "denial_reason": denial_reason,
                    "browse_permissions": browse_permissions,
                    "disabled_by_acbrowse": disabled_by_acbrowse,
                    "acbrowse_status": acbrowse_status,
                })

        for func, features in all_privileges.items():
            if func not in seen:
                seen.add(func)
                translated_features = {}
                for feat, info in features.items():
                    translated_features[feat] = {
                        "access": self._normalize_access(info["access"]),
                        "access_raw": info["access"],
                        "rule_name": info["rule_name"],
                        "menu_oper": info.get("menu_oper"),
                        "menu_def": info.get("menu_def", ""),
                    }
                effective_access, decision_source, denial_reason = self._resolve_routine_access(
                    translated_features,
                    has_group_default,
                    False,
                )
                routines_flat.append({
                    "routine": func,
                    "description": "",
                    "menu_name": "",
                    "module": "",
                    "in_menu": False,
                    "features": translated_features,
                    "has_explicit_privilege": True,
                    "effective_access": effective_access,
                    "decision_source": decision_source,
                    "denial_reason": denial_reason,
                    "browse_permissions": [],
                    "disabled_by_acbrowse": False,
                    "acbrowse_status": None,
                })

        report = {
            "user": login,
            "user_id": user["id"],
            "user_depto": user.get("depto", ""),
            "user_name": user.get("name", ""),
            "total_menus": len(menu_tree),
            "total_routines": len(routines_flat),
            "groups": groups,
            "access_codes": access_codes,
            "menus": menu_tree,
            "routines_summary": routines_flat,
            "privileges_raw": all_privileges,
            "existing_privilege_sets": existing_privilege_sets,
            "privilege_recommendations": privilege_recommendations,
        }

        routines_with_priv = sum(1 for r in routines_flat if r["has_explicit_privilege"])
        print(f"\n  {C}{D}{chr(0x250C)}{'─' * 45}{chr(0x2510)}{R}")
        print(f"  {C}{chr(0x2502)}{R} {B}RESUMO{R}")
        print(f"  {C}{chr(0x2502)}{R} Menus acessiveis .............. {G}{len(menu_tree)}{R}")
        print(f"  {C}{chr(0x2502)}{R} Rotinas mapeadas .............. {len(routines_flat)}")
        print(f"  {C}{chr(0x2502)}{R} Rotinas com privilegio ........ {G}{routines_with_priv}{R}")
        print(f"  {C}{chr(0x2502)}{R} Rotinas sem privilegio ........ {Y}{len(routines_flat) - routines_with_priv}{R}")
        print(f"  {C}{chr(0x2502)}{R} Grupos ........................ {len(groups)}")
        print(f"  {C}{D}{chr(0x2514)}{'─' * 45}{chr(0x2518)}{R}")

        return report
