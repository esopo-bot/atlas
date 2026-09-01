import argparse
import contextlib
import errno
import signal
import functools
import hashlib
import json
import os
import re
import importlib.util
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DESCRICAO_DA_CLI = ("painel de controle — dispara sessão headless e mostra o "
                    "estado do executor de roteiros, no navegador")
AJUDA_CWD = "worktree ou clone descartável onde a sessão roda"
AJUDA_ROTEIROS = ("pastas de roteiro, por vírgula; a primeira vence "
                  "o nome repetido")
AJUDA_FORCAR_ARVORE_SUJA = "sobe mesmo com mudança não commitada no --cwd"

ERRO_CWD_OBRIGATORIO = (
    "erro de uso: --cwd é obrigatório (worktree ou clone descartável);\n"
    "a sessão da execução pula permissões e não deve tocar a árvore "
    "que importa.")
ERRO_CWD_NAO_E_PASTA = "erro de uso: --cwd não é pasta: {}"
ERRO_SEM_ENCADEADOR = ("erro de ambiente: falta o encadeador — rode\n"
                       "  python montar.py --modulo encadeador")
ERRO_SEM_O_COMANDO_CLAUDE = (
    "erro de ambiente: o comando {} não está no PATH; a etapa de "
    "sessão morreria. Quem manda no comando é ENCADEADOR_SESSAO.")
ERRO_ARVORE_SUJA = (
    "PAREI — {} tem mudança não commitada.\n"
    "A sessão da execução roda com permissões puladas: numa árvore com "
    "trabalho seu dentro, um erro dela custa caro.\n"
    "Use um worktree descartável:\n"
    "  git worktree add /tmp/executor HEAD\n"
    "Se você sabe o que está fazendo: --forcar-arvore-suja")
ERRO_PORTA_NAO_ABRIU = "erro de ambiente: não consegui abrir a porta {}: {}"

RECADO_PORTA_JA_E_DESTE_REPOSITORIO = (
    "o painel de controle deste repositório já está no ar: "
    "http://127.0.0.1:{porta}\n"
    "  (nada a fazer — abra o endereço acima)")
RECADO_PORTA_MESMA_CASA_OUTRO_ALVO = (
    "PAREI — a porta {porta} já serve o painel de controle desta camada, "
    "mas apontando para OUTRO alvo:\n"
    "  {alvo_velho}\n"
    "Derrube o antigo, ou suba este noutra porta:\n"
    "  --porta {proxima_porta}")
RECADO_PORTA_DE_OUTRO_REPOSITORIO = (
    "PAREI — a porta {porta} é do painel de controle de OUTRO repositório:\n"
    "  {ocupante}\n"
    "Uma porta por repositório é o desenho. Suba este noutra:\n"
    "  --porta {proxima_porta}")
RECADO_PORTA_DE_ESTRANHO = (
    "PAREI — a porta {porta} está ocupada, e não por um painel de controle.\n"
    "Quem está nela:\n"
    "  ss -ltnp | grep :{porta}\n"
    "Encerre aquele, ou suba este noutra porta:\n"
    "  --porta {outra_porta}")

ANUNCIO_NO_AR = "painel de controle em http://127.0.0.1:{} — camada {}"
ANUNCIO_REPOSITORIO = "  repositório (o painel de controle): {}"
ANUNCIO_SESSOES = "  sessões rodam em:                   {}"
ANUNCIO_EVIDENCIAS = "  evidências em:                         {}"
ANUNCIO_ROTEIROS = "  roteiros de:                      {} ({} encontrados)"
ANUNCIO_COMO_ENCERRAR = "Ctrl+C encerra."
ANUNCIO_ENCERRADO = "\nencerrado."

ERRO_ROTA_DESCONHECIDA = "rota desconhecida"
ERRO_CORPO_INVALIDO = "corpo inválido"
ERRO_NOME_DE_TRABALHO = ("nome de trabalho inválido: minúsculo, sem barra nem "
                         "espaço, até 64")
ERRO_ALVO_OCUPADO = (
    "já existe execução rodando neste alvo: {}. "
    "Uma por vez — duas sessões na mesma árvore se atropelam. "
    "Espere terminar, ou suba outro painel de controle "
    "apontando para outro repositório.")
ERRO_SEM_PEDIDO = "escreva um pedido ou escolha um roteiro"
ERRO_ROTEIRO_COLADO_NO_LUGAR_DO_PEDIDO = (
    "isso é um roteiro, não um pedido. Salve-o como .json "
    "na pasta de roteiros e escolha-o na lista — colado "
    "aqui, o JSON inteiro viraria o texto de UMA sessão.")
ERRO_ROTEIRO_DESCONHECIDO = "roteiro desconhecido: {}"
ERRO_ROTEIRO_ILEGIVEL = "roteiro ilegível: {}"
ERRO_ROTEIRO_SEM_ETAPAS = "roteiro sem lista de etapas"
ERRO_ANDAMENTO_SEM_JSON = "o andamento não devolveu JSON"
ERRO_ANDAMENTO_FALHOU = "o andamento falhou: {}"
ERRO_DISPARO_FALHOU = "não consegui disparar: {}"

RECADO_TRAVA_DE_OUTRO_PAINEL = "{} (outro painel de controle, pid {})"
RECADO_SEM_REPOSITORIO_DE_ISSUES = "sem repositório de issues configurado"
RECADO_GH_MUDO = "sem dado (o gh não respondeu)"
RECADO_SEM_REDE_OU_GH = "sem dado (rede ou gh indisponível)"
PROXIMA_ACAO_JA_ESTA_NO_AR = (
    "rodando agora — espere. A etapa só escreve evidência quando termina; "
    "o que ela escreve enquanto isso está no bloco AGORA, acima. "
    "Não dispare de novo: duas execuções na mesma árvore se atropelam.")

RESULTADO_DO_CASO_FALHO = "FALHOU: {}"
RESUMO_DOS_CASOS = "{}: {} casos"
RESUMO_DAS_FALHAS = " — {} falharam"
VEREDITO_OK = "OK"
VEREDITO_FALHOU = "FALHOU"

CODIGO_NADA_A_FAZER = 0
CODIGO_ERRO_DE_USO = 2

VERSAO_DESCONHECIDA = "desconhecida"
PREFIXO_DA_VERSAO_NO_MONTAR = "VERSAO = "
ABERTURAS_DO_CABECALHO_DO_MONTAR = ("#", '"', "'")

TIMEOUT_DA_PERGUNTA_A_PORTA_S = 3
TIMEOUT_DO_GIT_S = 20
TIMEOUT_DO_GH_S = 30
TIMEOUT_DO_ANDAMENTO_S = 60

TETO_SESSAO_S_ESPELHO_DO_ENCADEADOR = 3600
SITUACOES_GRAVADAS_QUE_VENCEM_A_INFERENCIA = ("dormindo", "aguardando-resposta")
SITUACAO_GRAVADA_RODANDO = "rodando"
ESTADO_QUE_ESPERA_APROVACAO = "aguardando-aprovacao"
SITUACOES_DE_EXECUCAO_NO_AR = ("rodando", "dormindo", "aguardando-resposta")
CHAVES_GRAVADAS_QUE_A_MESA_MOSTRA = ("desde", "ate", "porque", "issue",
                                     "etapa", "escrita_em")
SITUACAO_DESCONHECIDA = "desconhecida"
SITUACAO_ENCERRADO = "encerrado"
SITUACAO_TRABALHANDO = "trabalhando"
PROCESSO_RODANDO = "rodando"
PROCESSO_ENCERRADO = "encerrado"
PROCESSO_DESCONHECIDO = "desconhecido"
ESTADO_EM_CURSO = "em-curso"

ARQUIVO_ESTADO = "estado.json"
ARQUIVO_EXECUTOR = "nucleo/executor.json"
ARQUIVO_EXECUTOR_EXEMPLO = "nucleo/executor.exemplo.json"
CHAVE_DECLARADA_E_AUSENTE = "faltando"
CHAVE_COM_VALOR_POR_PREENCHER = "por_preencher"
RECADO_SEM_EXEMPLO_PARA_COMPARAR = (
    f"não há com o que comparar: {ARQUIVO_EXECUTOR_EXEMPLO} não está neste "
    "disco")
RECADO_SEM_CONFIGURACAO_LOCAL = (
    f"não medido: {ARQUIVO_EXECUTOR} não foi lido nesta máquina")
SUFIXO_DO_ROTEIRO = ".roteiro.json"
MARCADOR_DE_MUDO = "tmp/narracao-muda"
PRAZO_DO_PANICO_S = 15
SITUACOES_QUE_O_PANICO_PARA = ("rodando", "dormindo")
ERRO_SO_LEITURA = ("mesa em só-leitura — a rota de escrita foi recusada "
                   "pelo servidor")
SUFIXO_DA_DESCRICAO = ".md"
INSTALADOR = "montar.py"
BANDEIRA_DE_VERSAO = "--versao"
MARCA_DA_VERSAO = "camada"
TEMPO_DO_INSTALADOR = 60
CHAVE_DESCRICAO = "descricao"
SEM_DESCRICAO = ("Esta rotina não tem descrição: escreva um .md com o mesmo "
                 "nome ao lado do roteiro, ou um campo \"descricao\" nele.")
SUFIXO_DO_LOG = ".log"
SUFIXO_DA_EVIDENCIA = ".json"
PADRAO_DO_LOG_DE_ETAPA = re.compile(r"([0-9]{2})-(.+)-c([0-9]+)\.log\Z")
CAUDA_DA_ETAPA_VIVA = 3000
MARCA_DA_LOGICA_NA_PAGINA = "/* a lógica da mesa entra aqui */"
PREFIXO_DA_TRAVA = ".trava-"
DIGITOS_DO_RESUMO_DO_ALVO = 12
INTERVALO_DO_QUADRO_S_POR_CORTESIA_DE_REDE = 120
LIMITE_DE_ISSUES_NO_QUADRO = 30
MARCA_DE_MOLDE_NAO_PREENCHIDO = "${"
PASTA_DAS_SKILLS_FONTE = ".agents/skills"
PASTA_DAS_SKILLS_COPIA = ".claude/skills"
GLOB_DA_SKILL = "*/SKILL.md"
FRONTMATTER_DA_SKILL = re.compile(r"^---\n(.*?)\n---\n", re.S)
CAMPO_NOME_DA_SKILL = re.compile(r"^name:\s*(.+)$", re.M)
CAMPO_DESCRICAO_DA_SKILL = re.compile(r"^description:\s*(.+)$", re.M)
RECADO_SEM_PASTA_DE_SKILLS = ("não medido: nem .agents/skills nem "
                              ".claude/skills existem aqui")

COMANDO_DO_NAVEGADOR_SEM_TELA = "node"
TIMEOUT_DO_NAVEGADOR_S = 30
RECADO_SEM_NAVEGADOR_SEM_TELA = (
    "não medido: as decisões da mesa não foram exercitadas — falta o "
    "comando node nesta máquina")
RECADO_NODE_RECUSOU = "o node recusou a lógica da mesa: {}"
ABERTURA_DA_MEDIDA_NO_NODE = "\nconst medido = {};\n"
FECHO_DA_MEDIDA_NO_NODE = "\nconsole.log(JSON.stringify(medido));\n"

COMANDO_DO_CLI_DE_SESSAO = "claude"
ARGUMENTOS_DA_LISTA_DE_MCP = ("mcp", "list")
SEPARADOR_DO_ESTADO_MCP = " - "
MARCA_DE_MCP_CONECTADO = "Connected"
TIMEOUT_DO_MCP_S = 60
RECADO_SEM_CLI_PARA_MEDIR_MCP = ("não medido: o comando de sessão não está no "
                                 "PATH desta máquina")
RECADO_MCP_NAO_RESPONDEU = "não medido: a listagem de MCP não respondeu ({})"

COMANDO_DO_AGENDADOR = "systemctl"
ARGUMENTOS_DA_LISTA_DE_ROTINAS = ("--user", "list-units", "--type=timer",
                                  "--all", "--no-legend", "--plain")
ARGUMENTOS_DO_DETALHE_DA_ROTINA = ("--user", "show")
PROPRIEDADES_DA_ROTINA = ("--property=NextElapseUSecRealtime",
                          "--property=LastTriggerUSec",
                          "--property=Unit")
PROPRIEDADES_DO_SERVICO = ("--property=ExecStart",)
PROPRIEDADE_DO_SERVICO = "Unit"
PROPRIEDADE_DO_COMANDO = "ExecStart"
CAMINHO_DENTRO_DO_COMANDO = re.compile(r"path=([^ ;]+)")
PROPRIEDADE_DA_PROXIMA = "NextElapseUSecRealtime"
PROPRIEDADE_DA_ULTIMA = "LastTriggerUSec"
SUFIXO_DA_UNIDADE_DE_TEMPO = ".timer"
TIMEOUT_DO_AGENDADOR_S = 20
RECADO_SEM_AGENDADOR = ("não medido: esta máquina não tem o agendador que o "
                        "painel de controle sabe ler")
NOME_DO_WINDOWS = "nt"
RECADO_AGENDADOR_DO_WINDOWS = (
    "não medido: no Windows o agendador é outro, e o formato da saída dele "
    "muda com o idioma e a versão. Escrever o leitor sem rodar num Windows "
    "de verdade daria número sem procedência — que é o oposto do que este "
    "painel de controle serve para mostrar. Para fechar, rode uma vez "
    "`schtasks /query /fo csv /v` na máquina e leve a saída para quem "
    "mantém a camada: com o formato real na mão, o leitor nasce com teste.")
RECADO_AGENDADOR_NAO_RESPONDEU = "não medido: o agendador não respondeu ({})"

COMANDO_DOS_CONTAINERS = "docker"
ARGUMENTOS_DA_LISTA_DE_CONTAINERS = ("compose", "ls", "-a", "--format",
                                     "json")
MARCA_DE_CONTAINERS_DE_PE = "running"
TIMEOUT_DOS_CONTAINERS_S = 20
RECADO_SEM_DOCKER = ("não medido: esta máquina não tem o docker que o "
                     "painel de controle sabe ler")
RECADO_CONTAINERS_NAO_RESPONDERAM = ("não medido: a listagem de containers "
                                     "não respondeu ({})")
INTERVALO_DOS_CONTAINERS_S = 30

INTERVALO_DA_MAQUINA_S = 300

PASSOS_DO_GUIA = (
    ("o que é", "O executor de roteiros roda um trabalho em estágios e "
                "guarda a prova de cada um. Você dispara e vai embora: se "
                "algum estágio não provar o que fez, ele para, escreve o "
                "motivo na issue e devolve o estado anterior."),
    ("um pedido meu", "Escreva o pedido inteiro na caixa. A sessão nasce sem "
                      "contexto nenhum: diga onde olhar, o que mudar e o que "
                      "você aceita como prova. Pedido vago volta trabalho "
                      "vago."),
    ("um roteiro", "Roteiro é receita pronta, escrita antes de rodar. Escolha "
                   "no seletor; a descrição ao lado diz o que ele faz. "
                   "Roteiro é melhor que pedido para o que se repete."),
    ("turnos e ciclos", "Turnos é quantas vezes a sessão pode falar antes de "
                        "ser interrompida. Ciclos é quantas vezes a execução "
                        "pode reprovar antes de escalar para você. Os padrões "
                        "servem: mexa só quando souber por quê."),
    ("issue", "Se você puser o número da issue, a execução conta a história "
              "lá — passo a passo, com a prova. É por isso que a sessão "
              "seguinte retoma sem você reexplicar nada."),
    ("onde as coisas caem", "A sessão roda em {alvo} e as evidências ficam em "
                            "{evidencias}. O alvo é árvore descartável de "
                            "propósito: a sessão roda sem pedir permissão a "
                            "cada passo."),
    ("quando ela para", "Parada quer dizer que uma verificação recusou — o "
                        "motivo está na fita e na issue. Pergunta quer dizer "
                        "que ela precisa de uma decisão sua: responda na "
                        "issue e mande seguir."),
    ("a prova", "Nada é pronto porque a sessão disse que é. O que vale é o "
                "que um instrumento provou, e a evidência guarda o comando e "
                "a saída para você reexecutar."),
)

CAUDA_DO_LOG_NA_TELA = 4000
CAUDA_DO_ERRO_DO_ANDAMENTO = 400

TETO_PADRAO_DE_CICLOS, TETO_MINIMO, TETO_MAXIMO = 3, 1, 9
TURNOS_PADRAO_ACIMA_DO_TETO_DO_MOTOR, TURNOS_MINIMO, TURNOS_MAXIMO = 24, 4, 120
ETAPA_DO_PEDIDO = "pedido"
ETAPA_DA_VERIFICACAO = "verifica"
PREFIXO_DO_PEDIDO_DO_PAINEL = "painel"
PREFIXO_DA_ISSUE = "issue-"
PREFIXO_DA_EXECUCAO_SEM_NOME = "execucao"
NOME_QUE_PODE_VIRAR_PASTA = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")

PORTA_PADRAO = 4000
DIR_EVIDENCIAS_PADRAO = "tmp/evidencias"
ROTEIROS_PADRAO = "execucoes,tmp"
ENDERECO_LOCAL = "127.0.0.1"
SILENCIO_DO_SERVIDOR = None


def raiz_da_camada_procurando_o_encadeador() -> Path:
    este_arquivo = Path(__file__).resolve()
    for pasta in este_arquivo.parents:
        if (pasta / ".agents" / "encadeador" / "encadeador.py").exists():
            return pasta
    return este_arquivo.parents[2]


RAIZ = raiz_da_camada_procurando_o_encadeador()
ENCADEADOR = RAIZ / ".agents" / "encadeador" / "encadeador.py"
CAIXA = RAIZ / ".agents" / "caixa" / "caixa.py"
RECADO_SEM_CAIXA = ("nenhuma caixa declarada nesta máquina — a chave "
                    "`caixas` do executor.json diz onde o quadro mora")
ERRO_PODA_SEM_ID_OU_MOTIVO = ("poda exige a identidade da linha e o motivo "
                              "do fechamento")
VERIFICAR = RAIZ / ".agents" / "verificar" / "verificar.py"
LIMITE_DO_TITULO_DE_ROTEIRO = 72
PREFIXO_DA_LINHA_ACUSA = "ACUSA "
MARCA_DO_CRITERIO_SEM_RESPOSTA = ("critério da issue sem resposta nas "
                                  "evidências: ")
MARCA_DO_FIM_DO_CRITERIO = " — nada no provado"
MARCA_DE_ISSUE_SEM_CRITERIO = "não traz critério aberto"
TOTAL_DE_CRITERIOS = re.compile(r"(?:de|todos os) (\d+) critérios abertos")
ERRO_RESPOSTA_VAZIA = ("resposta vazia — escreva o que o executor de "
                       "roteiros deve saber ao retomar")
ERRO_SEM_ROTEIRO_PARA_RETOMAR = (
    "não achei o roteiro deste trabalho — nem a cópia nas evidências, nem o "
    "caminho no estado gravado; sem ele não há retomada")
ERRO_RESPONDER_COM_EXECUCAO_VIVA = ("a execução ainda está viva — a "
                                    "resposta entra quando ela parar")
RECADO_TRABALHO_SEM_ISSUE = ("este trabalho não declara issue — não há "
                             "critério a cobrar")
RECADO_RESPOSTA_NA_ISSUE = "comentei na issue {} — o comentário diz quem foi"
RECADO_RESPOSTA_SO_NA_RETOMADA = ("sem issue ou sem repositório configurado: "
                                  "a resposta entrou só na retomada, sem "
                                  "registrar autor")
RECADO_CONTA_DO_MOTOR_NAO_ASSINA = (
    "não comentei: a conta ativa do gh é a declarada em issues.conta_gh, e "
    "comentário dela não diz quem decidiu — troque a conta ativa ou use o "
    "arquivo de aprovação citado na pergunta")
MARCA_DA_DEVOLUCAO = "<!-- devolucao pela mesa: nao aprovado -->"
MOLDE_DO_COMENTARIO_DE_DEVOLUCAO = (MARCA_DA_DEVOLUCAO
                                    + "\n**Devolvido com recado:**\n\n{}")
RECADO_DEVOLUCAO_NA_ISSUE = ("devolvi pela issue {} — a execução segue "
                             "parada, esperando a aprovação")
ERRO_DEVOLUCAO_SEM_REGISTRO = ("não devolvi — {}. A devolução só existe "
                               "como comentário na issue")
LINHAS_DA_CAUDA_TRADUZIDA = 14
LARGURA_DE_UMA_LINHA_DA_CAUDA = 200
FERRAMENTA_NA_CAUDA = "→ ferramenta {}"
FIM_NA_CAUDA = "■ fim da sessão: {}"
MARCA_DE_DESTROCO_DE_JSON = '":'


def quem_responde_na_porta(porta: int) -> tuple:
    try:
        with urllib.request.urlopen(
                f"http://{ENDERECO_LOCAL}:{porta}/trabalhos",
                timeout=TIMEOUT_DA_PERGUNTA_A_PORTA_S) as resposta:
            dado = json.loads(resposta.read())
            return dado.get("repositorio"), dado.get("alvo")
    except (OSError, ValueError, json.JSONDecodeError):
        return None, None


def descendentes_lendo_proc(pai: int) -> list:
    filhos_por_pai = {}
    try:
        for entrada in os.listdir("/proc"):
            if not entrada.isdigit():
                continue
            try:
                with open(f"/proc/{entrada}/stat", encoding="utf-8") as arquivo:
                    campos = arquivo.read().rsplit(")", 1)[1].split()
                filhos_por_pai.setdefault(int(campos[1]), []).append(int(entrada))
            except (OSError, IndexError, ValueError):
                continue
    except OSError:
        return []
    fila, achados = [pai], []
    while fila:
        for pid in filhos_por_pai.get(fila.pop(), []):
            achados.append(pid)
            fila.append(pid)
    return achados


VARIAVEL_DA_SESSAO = "ENCADEADOR_SESSAO"
PADRAO_DA_SESSAO = "claude"


def comando_da_sessao() -> str:
    declarado = os.environ.get(VARIAVEL_DA_SESSAO, PADRAO_DA_SESSAO)
    return (shlex.split(declarado) or [PADRAO_DA_SESSAO])[0]


def sessoes_de_modelo_entre(pids: list) -> int:
    vivas = 0
    for pid in pids:
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as arquivo:
                if comando_da_sessao().encode() in arquivo.read():
                    vivas += 1
        except OSError:
            continue
    return vivas


def so_o_que_foi_medido(dado: dict) -> dict:
    return {chave: valor for chave, valor in dado.items() if valor is not None}


def vivacidade_do_que_o_motor_gravou(gravado: dict, **acrescimo) -> dict:
    posto = {chave: gravado.get(chave)
             for chave in CHAVES_GRAVADAS_QUE_A_MESA_MOSTRA}
    return so_o_que_foi_medido({"situacao": gravado["situacao"], **posto,
                                **acrescimo})


def vivacidade(proc, inicio: float | None, gravado: dict = None) -> dict:
    if proc is None:
        if gravado and gravado.get("situacao"):
            return vivacidade_do_que_o_motor_gravou(gravado, de_fora=True)
        return {"situacao": SITUACAO_DESCONHECIDA}
    if proc.poll() is not None:
        return {"situacao": SITUACAO_ENCERRADO, "codigo": proc.returncode}
    filhos = descendentes_lendo_proc(proc.pid)
    sessoes = sessoes_de_modelo_entre(filhos) if filhos else None
    decorrido = int(time.time() - inicio) if inicio else None
    situacao_gravada = gravado.get("situacao") if gravado else None
    if situacao_gravada in SITUACOES_GRAVADAS_QUE_VENCEM_A_INFERENCIA:
        return vivacidade_do_que_o_motor_gravou(
            gravado, sessoes=sessoes, decorrido_s=decorrido)
    return so_o_que_foi_medido({
        "situacao": SITUACAO_TRABALHANDO,
        "sessoes": sessoes,
        "decorrido_s": decorrido,
        "teto_s": TETO_SESSAO_S_ESPELHO_DO_ENCADEADOR,
        "resta_s": (max(0, TETO_SESSAO_S_ESPELHO_DO_ENCADEADOR - decorrido)
                    if decorrido is not None else None)})


def dicionario_do_arquivo(caminho: Path) -> dict | None:
    try:
        dado = json.loads(Path(caminho).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return dado if isinstance(dado, dict) else None


def configuracao_do_executor_sem_validar(cwd) -> dict | None:
    return dicionario_do_arquivo(Path(cwd) / ARQUIVO_EXECUTOR)


def estado_que_o_motor_gravou(dir_evidencias, trabalho) -> dict | None:
    return dicionario_do_arquivo(
        Path(dir_evidencias) / trabalho / ARQUIVO_ESTADO)


def ainda_e_molde(valor) -> bool:
    if isinstance(valor, str):
        return MARCA_DE_MOLDE_NAO_PREENCHIDO in valor
    if isinstance(valor, list):
        return any(ainda_e_molde(item) for item in valor)
    return False


def confronto_chave_a_chave(exemplo: dict, local: dict, prefixo: str = ""):
    for chave, declarado in exemplo.items():
        if MARCA_DE_MOLDE_NAO_PREENCHIDO in chave:
            continue
        caminho = f"{prefixo}.{chave}" if prefixo else chave
        preenchido = local.get(chave)
        if chave not in local:
            yield caminho, CHAVE_DECLARADA_E_AUSENTE
        elif isinstance(declarado, dict) and isinstance(preenchido, dict):
            yield from confronto_chave_a_chave(declarado, preenchido, caminho)
        elif ainda_e_molde(preenchido):
            yield caminho, CHAVE_COM_VALOR_POR_PREENCHER


def configuracao_que_falta_nesta_maquina(cwd) -> dict:
    exemplo = dicionario_do_arquivo(Path(cwd) / ARQUIVO_EXECUTOR_EXEMPLO)
    if exemplo is None:
        return {"recado": RECADO_SEM_EXEMPLO_PARA_COMPARAR}
    local = configuracao_do_executor_sem_validar(cwd)
    if local is None:
        return {"recado": RECADO_SEM_CONFIGURACAO_LOCAL}
    confronto = list(confronto_chave_a_chave(exemplo, local))
    return {"recado": None,
            CHAVE_DECLARADA_E_AUSENTE:
                [c for c, e in confronto if e == CHAVE_DECLARADA_E_AUSENTE],
            CHAVE_COM_VALOR_POR_PREENCHER:
                [c for c, e in confronto
                 if e == CHAVE_COM_VALOR_POR_PREENCHER]}


def roteiro_gravado_no_estado(dir_evidencias, trabalho) -> Path | None:
    caminho = (estado_que_o_motor_gravou(dir_evidencias, trabalho)
               or {}).get("roteiro")
    if caminho and Path(caminho).is_file():
        return Path(caminho)
    return None


@functools.lru_cache(maxsize=1)
def encadeador_em_processo():
    spec = importlib.util.spec_from_file_location(
        "encadeador_do_painel", ENCADEADOR)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def estado_provado_do_motor(dir_evidencias, trabalho) -> dict | None:
    gravado = estado_que_o_motor_gravou(dir_evidencias, trabalho)
    return encadeador_em_processo().situacao_provada(
        dir_evidencias, trabalho, gravado)


def a_execucao_esta_no_ar(estado: dict) -> bool:
    if estado.get("processo") == PROCESSO_RODANDO:
        return True
    gravado = estado.get("gravado") or {}
    return gravado.get("situacao") == SITUACAO_GRAVADA_RODANDO


def a_execucao_espera_aprovacao(estado: dict) -> bool:
    return (estado.get("estado") == ESTADO_QUE_ESPERA_APROVACAO
            and any(e.get("pergunta") for e in estado.get("etapas") or []))


def calar_o_convite_a_disparar_o_que_ja_esta_no_ar(estado: dict) -> dict:
    situacao = (estado.get("vivacidade") or {}).get("situacao")
    esperando_alguem = situacao in SITUACOES_GRAVADAS_QUE_VENCEM_A_INFERENCIA
    if (a_execucao_esta_no_ar(estado) and not esperando_alguem
            and estado.get("estado") == ESTADO_EM_CURSO):
        estado["proxima_acao"] = PROXIMA_ACAO_JA_ESTA_NO_AR
    return estado


def cauda_do_arquivo(caminho: Path, quantos_bytes: int) -> str:
    with caminho.open("rb") as arquivo:
        tamanho = arquivo.seek(0, os.SEEK_END)
        arquivo.seek(max(0, tamanho - quantos_bytes))
        dado = arquivo.read()
    while dado and (dado[0] & 0xC0) == 0x80:
        dado = dado[1:]
    return dado.decode("utf-8", errors="replace")


def _uma_linha_do_evento(evento: dict) -> str | None:
    tipo = evento.get("type")
    if tipo == "assistant":
        partes = ((evento.get("message") or {}).get("content") or [])
        pedacos = []
        for parte in partes:
            if not isinstance(parte, dict):
                continue
            if parte.get("type") == "tool_use":
                pedacos.append(FERRAMENTA_NA_CAUDA.format(
                    parte.get("name", "?")))
            elif parte.get("type") == "text" and str(
                    parte.get("text", "")).strip():
                pedacos.append(str(parte["text"]).strip()
                               [:LARGURA_DE_UMA_LINHA_DA_CAUDA])
        return "\n".join(pedacos) or None
    if tipo == "result":
        return FIM_NA_CAUDA.format(evento.get("subtype", "?"))
    return None


def resumo_da_cauda(texto: str) -> str:
    linhas = []
    for linha in texto.splitlines():
        crua = linha.strip()
        if not (crua.startswith("{") and crua.endswith("}")):
            if crua and MARCA_DE_DESTROCO_DE_JSON not in crua:
                linhas.append(linha)
            continue
        try:
            evento = json.loads(crua)
        except ValueError:
            linhas.append(linha)
            continue
        resumo = _uma_linha_do_evento(evento if isinstance(evento, dict)
                                      else {})
        if resumo:
            linhas.append(resumo)
    return "\n".join(linhas[-LINHAS_DA_CAUDA_TRADUZIDA:])


def etapa_que_escreve_sem_ter_terminado(pasta: Path) -> dict | None:
    candidatas = []
    for log in pasta.glob(f"*{SUFIXO_DO_LOG}"):
        casado = PADRAO_DO_LOG_DE_ETAPA.fullmatch(log.name)
        if casado and not log.with_suffix(SUFIXO_DA_EVIDENCIA).exists():
            candidatas.append((int(casado.group(1)), int(casado.group(3)),
                               casado.group(2), log))
    if not candidatas:
        return None
    ordem, ciclo, nome, log = max(candidatas)
    with contextlib.suppress(OSError):
        return {"ordem": ordem, "ciclo": ciclo, "nome": nome,
                "arquivo": log.name, "bytes": log.stat().st_size,
                "cauda": resumo_da_cauda(
                    cauda_do_arquivo(log, CAUDA_DA_ETAPA_VIVA))}
    return None


def instante_da_pasta_ou_o_comeco_do_tempo(pasta: Path) -> float:
    with contextlib.suppress(OSError):
        return pasta.stat().st_mtime
    return 0.0


def trabalho_que_a_mesa_abre(trabalhos: list) -> str | None:
    execucoes = [t for t in trabalhos if t.get("execucao")]
    viva = next((t for t in execucoes
                 if t.get("situacao") in SITUACOES_DE_EXECUCAO_NO_AR), None)
    escolhida = viva or (execucoes[0] if execucoes else None)
    return escolhida["nome"] if escolhida else None


def decidir_porta_ocupada(porta: int, repositorio: str, alvo: str,
                          ocupante: str | None,
                          alvo_do_ocupante: str | None) -> tuple:
    if ocupante == repositorio and alvo_do_ocupante == alvo:
        return CODIGO_NADA_A_FAZER, RECADO_PORTA_JA_E_DESTE_REPOSITORIO.format(
            porta=porta)
    if ocupante == repositorio:
        return CODIGO_ERRO_DE_USO, RECADO_PORTA_MESMA_CASA_OUTRO_ALVO.format(
            porta=porta, alvo_velho=alvo_do_ocupante,
            proxima_porta=porta + 1)
    if ocupante:
        return CODIGO_ERRO_DE_USO, RECADO_PORTA_DE_OUTRO_REPOSITORIO.format(
            porta=porta, ocupante=ocupante, proxima_porta=porta + 1)
    return CODIGO_ERRO_DE_USO, RECADO_PORTA_DE_ESTRANHO.format(
        porta=porta, outra_porta=porta + 10)


def versao_da_camada_declarada_no_topo_do_montar() -> str:
    try:
        linhas = (RAIZ / "montar.py").read_text(encoding="utf-8").splitlines()
    except OSError:
        return VERSAO_DESCONHECIDA
    for linha in linhas:
        if linha.startswith(PREFIXO_DA_VERSAO_NO_MONTAR):
            return linha.split("=", 1)[1].strip().strip("\"'")
        if linha.strip() and not linha.startswith(ABERTURAS_DO_CABECALHO_DO_MONTAR):
            break
    return VERSAO_DESCONHECIDA


def carimbo_utc_de_agora() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def nome_de_trabalho(prefixo: str = PREFIXO_DO_PEDIDO_DO_PAINEL,
                     issue=None) -> str:
    if isinstance(issue, int) and not isinstance(issue, bool) and issue > 0:
        return f"{PREFIXO_DA_ISSUE}{issue}"
    return f"{prefixo}-{carimbo_utc_de_agora()}"


def recusa_do_nome_de_trabalho(nome: str) -> str | None:
    if not NOME_QUE_PODE_VIRAR_PASTA.match(nome or ""):
        return ERRO_NOME_DE_TRABALHO
    return None


def inteiro_na_faixa_ou_padrao(valor, minimo: int, maximo: int,
                               padrao: int) -> int:
    esta_na_faixa = isinstance(valor, int) and minimo <= valor <= maximo
    return valor if esta_na_faixa else padrao


def descricao_do_roteiro(caminho: Path) -> str:
    irmao = caminho.with_suffix(SUFIXO_DA_DESCRICAO)
    if irmao.is_file():
        texto = irmao.read_text(encoding="utf-8", errors="replace").strip()
        if texto:
            return texto
    with contextlib.suppress(OSError, json.JSONDecodeError):
        dado = json.loads(caminho.read_text(encoding="utf-8"))
        if isinstance(dado, dict) and isinstance(dado.get(CHAVE_DESCRICAO), str):
            return dado[CHAVE_DESCRICAO].strip()
    return SEM_DESCRICAO


def titulo_do_roteiro(nome: str, descricao: str) -> str:
    primeira = next((linha.strip().lstrip("# ").strip()
                     for linha in (descricao or "").splitlines()
                     if linha.strip()), "")
    if primeira and descricao != SEM_DESCRICAO:
        return primeira[:LIMITE_DO_TITULO_DE_ROTEIRO]
    return Path(nome).stem.replace("-", " ")


def placar_dos_criterios(codigo: int, saida: str) -> dict:
    abertos, avisos = [], []
    for linha in saida.splitlines():
        if not linha.startswith(PREFIXO_DA_LINHA_ACUSA):
            continue
        resto = linha[len(PREFIXO_DA_LINHA_ACUSA):]
        if MARCA_DO_CRITERIO_SEM_RESPOSTA in resto:
            pedaco = resto.split(MARCA_DO_CRITERIO_SEM_RESPOSTA, 1)[1]
            nome = pedaco.rsplit(MARCA_DO_FIM_DO_CRITERIO, 1)[0].strip()
            abertos.append(nome.strip("'\""))
        else:
            avisos.append(resto.strip())
    achado = TOTAL_DE_CRITERIOS.search(saida)
    total = (int(achado.group(1)) if achado
             else 0 if MARCA_DE_ISSUE_SEM_CRITERIO in saida
             else len(abertos))
    return {"total": total, "abertos": abertos, "avisos": avisos}


def comando_de_retomada(roteiro: Path, trabalho: str, dir_evidencias: Path,
                        cwd: Path, resposta: str | None) -> list:
    comando = [sys.executable, str(ENCADEADOR), "executar",
               "--roteiro", str(roteiro), "--trabalho", trabalho,
               "--dir", str(dir_evidencias), "--cwd", str(cwd), "--retomar"]
    if resposta:
        comando += ["--resposta", resposta]
    return comando


CAMPO_DO_CUSTO_NO_LOG = re.compile(r'"total_cost_usd":([0-9.]+)')
CAMPO_DOS_TURNOS_NO_LOG = re.compile(r'"num_turns":(\d+)')
PADRAO_DO_LOG_DA_ETAPA = re.compile(r"^[\w.-]+\.log$")
INTERVALO_DA_CONTA_S = 30
ERRO_LOG_FORA_DO_PADRAO = "nome de log fora do padrão das etapas"


def conta_das_execucoes(dir_evidencias: Path) -> dict:
    por_trabalho, dia = {}, 0.0
    hoje = time.strftime("%Y-%m-%d")
    if not dir_evidencias.is_dir():
        return {"por_trabalho": {}, "dia_usd": 0.0}
    for log in sorted(dir_evidencias.glob("*/*.log")):
        try:
            texto = log.read_text(encoding="utf-8", errors="replace")
            no_dia = time.strftime(
                "%Y-%m-%d", time.localtime(log.stat().st_mtime)) == hoje
        except OSError:
            continue
        custo = sum(float(a.group(1))
                    for a in CAMPO_DO_CUSTO_NO_LOG.finditer(texto))
        turnos = sum(int(a.group(1))
                     for a in CAMPO_DOS_TURNOS_NO_LOG.finditer(texto))
        if not custo and not turnos:
            continue
        soma = por_trabalho.setdefault(
            log.parent.name, {"usd": 0.0, "turnos": 0, "etapas": {}})
        soma["usd"] = round(soma["usd"] + custo, 4)
        soma["turnos"] += turnos
        soma["etapas"][log.stem] = round(custo, 4)
        if no_dia:
            dia += custo
    return {"por_trabalho": por_trabalho, "dia_usd": round(dia, 2)}


def linha_do_tempo_do_dia(dir_evidencias: Path) -> dict:
    hoje = time.strftime("%Y-%m-%d")
    raias = []
    if not dir_evidencias.is_dir():
        return {"dia": hoje, "raias": []}
    for pasta in sorted(dir_evidencias.iterdir()):
        if not pasta.is_dir():
            continue
        blocos, anterior = [], None
        for evidencia in sorted(pasta.glob("[0-9]*.json")):
            try:
                dado = json.loads(evidencia.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if not isinstance(dado, dict):
                continue
            quando = str(dado.get("quando") or "")
            if not quando.startswith(hoje):
                anterior = quando or anterior
                continue
            log = evidencia.with_suffix(".log")
            blocos.append({"etapa": dado.get("etapa") or evidencia.stem,
                           "inicio": anterior, "fim": quando,
                           "ciclo": (dado.get("ciclo") or {}).get("i"),
                           "log": log.name if log.exists() else None})
            anterior = quando
        marcas = []
        gravado = estado_que_o_motor_gravou(dir_evidencias, pasta.name) or {}
        desde = str(gravado.get("desde") or "")
        if gravado.get("situacao") in ("aguardando-resposta", "parada") \
                and desde.startswith(hoje):
            marcas.append({"tipo": gravado["situacao"], "quando": desde})
        if blocos or marcas:
            raias.append({"trabalho": pasta.name, "blocos": blocos,
                          "marcas": marcas})
    return {"dia": hoje, "raias": raias}


PADRAO_DA_LINHA_DA_CAIXA = re.compile(
    r"^- \*\*(?P<id>[^*]+)\*\* `(?P<tipo>[a-z]+)` — (?P<texto>.*?)"
    r"(?: · visto em (?P<visto>\S+))?$")


def linhas_do_corpo_da_caixa(corpo: str) -> list:
    achadas = []
    for linha in (corpo or "").splitlines():
        casada = PADRAO_DA_LINHA_DA_CAIXA.match(linha.strip())
        if casada:
            achadas.append({"id": casada["id"], "tipo": casada["tipo"],
                            "texto": casada["texto"],
                            "visto": casada["visto"]})
    return achadas


def parece_roteiro(dado) -> bool:
    return isinstance(dado, dict) and isinstance(dado.get("etapas"), list)


CHAVE_DA_AUDITORIA = "auditoria"


def lembrar_a_auditoria(cwd: Path, ligada: bool) -> None:
    alvo = Path(cwd) / ARQUIVO_EXECUTOR
    try:
        dado = json.loads(alvo.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    if not isinstance(dado, dict) or dado.get(CHAVE_DA_AUDITORIA) == ligada:
        return
    dado[CHAVE_DA_AUDITORIA] = ligada
    try:
        alvo.write_text(json.dumps(dado, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    except OSError:
        return


def roteiro_do_pedido_com_verificacao(
        prompt: str, teto: int = TETO_PADRAO_DE_CICLOS,
        turnos: int = TURNOS_PADRAO_ACIMA_DO_TETO_DO_MOTOR,
        issue: int = None, auditoria: bool = False) -> dict:
    roteiro = {
        "teto": teto,
        "etapas": [
            {"nome": ETAPA_DO_PEDIDO, "tipo": "sessao", "prompt": prompt,
             "max-turnos": turnos},
            {"nome": ETAPA_DA_VERIFICACAO, "tipo": "verificacao",
             "depende": [ETAPA_DO_PEDIDO]},
        ],
    }
    if issue:
        roteiro["issue"] = int(issue)
    if auditoria:
        roteiro[CHAVE_DA_AUDITORIA] = True
    return roteiro


def tem_mudanca_nao_commitada(cwd: Path) -> bool:
    try:
        r = subprocess.run(["git", "status", "--porcelain"], cwd=cwd,
                           capture_output=True, text=True,
                           timeout=TIMEOUT_DO_GIT_S)
    except (OSError, subprocess.SubprocessError):
        return False
    return r.returncode == 0 and bool(r.stdout.strip())


def _processo_vivo(pid) -> bool:
    try:
        os.kill(int(pid), 0)
    except (ProcessLookupError, ValueError, TypeError):
        return False
    except PermissionError:
        return True
    return True


def _conta_ativa_do_gh() -> str:
    try:
        feito = subprocess.run(["gh", "api", "user", "--jq", ".login"],
                               capture_output=True, text=True,
                               timeout=TIMEOUT_DO_GH_S)
    except (OSError, subprocess.SubprocessError):
        return ""
    return feito.stdout.strip() if feito.returncode == 0 else ""


def _pid_ainda_e_do_encadeador(pid) -> bool:
    if not Path("/proc").exists():
        return True
    try:
        linha_de_comando = Path(f"/proc/{int(pid)}/cmdline").read_bytes()
    except (OSError, ValueError, TypeError):
        return False
    return ENCADEADOR.name.encode() in linha_de_comando


class PonteParaOEncadeador:

    def __init__(self, cwd: Path, dir_evidencias: Path, dirs_roteiros: list):
        self.cwd = cwd
        self.dir = dir_evidencias
        self.roteiros = dirs_roteiros
        self.rodando: dict[str, subprocess.Popen] = {}
        self.inicio: dict[str, float] = {}
        self.em_voo: set[str] = set()
        self.trava = threading.Lock()
        self._quadro, self._quadro_em = None, 0.0
        self._maquina, self._maquina_em = None, 0.0
        self._caixas, self._caixas_em = None, 0.0
        self._conta, self._conta_em = None, 0.0
        self._containers, self._containers_em = None, 0.0
        self._criterios = {}

    def maquina_com_cache(self, relendo: bool = False) -> dict:
        momento = time.time()
        with self.trava:
            fresco = momento - self._maquina_em
            if self._maquina and not relendo \
                    and fresco < INTERVALO_DA_MAQUINA_S:
                return self._maquina
        achado = {"skills": skills_no_disco(RAIZ),
                  "mcp": servidores_mcp_com_estado(),
                  "rotinas": rotinas_do_workspace(RAIZ),
                  "guia": guia_do_executor(self),
                  "configuracao": configuracao_que_falta_nesta_maquina(
                      self.cwd)}
        with self.trava:
            self._maquina, self._maquina_em = achado, momento
        return achado

    def containers_com_cache(self) -> dict:
        momento = time.time()
        with self.trava:
            fresco = momento - self._containers_em
            if self._containers and fresco < INTERVALO_DOS_CONTAINERS_S:
                return self._containers
        achado = containers_do_workspace(RAIZ)
        with self.trava:
            self._containers, self._containers_em = achado, momento
        return achado

    def _arquivo_de_trava_deste_alvo(self) -> Path:
        resumo_do_caminho_do_alvo = hashlib.sha256(
            str(self.cwd).encode()).hexdigest()[:DIGITOS_DO_RESUMO_DO_ALVO]
        return self.dir / f"{PREFIXO_DA_TRAVA}{resumo_do_caminho_do_alvo}.json"

    def _trabalho_desta_sessao_ainda_no_ar(self) -> str | None:
        with self.trava:
            for nome, proc in self.rodando.items():
                if proc.poll() is None:
                    return nome
        return None

    def _dono_vivo_da_trava_em_arquivo(self) -> str | None:
        try:
            dono = json.loads(self._arquivo_de_trava_deste_alvo()
                              .read_text(encoding="utf-8"))
            os.kill(int(dono["pid"]), 0)
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            return None
        return RECADO_TRAVA_DE_OUTRO_PAINEL.format(
            dono.get("trabalho", "?"), dono["pid"])

    def ocupado(self) -> str | None:
        return (self._trabalho_desta_sessao_ainda_no_ar()
                or self._dono_vivo_da_trava_em_arquivo())

    def gravar_trava(self, pid: int, trabalho: str) -> None:
        self._arquivo_de_trava_deste_alvo().write_text(
            json.dumps({"pid": pid, "trabalho": trabalho,
                        "cwd": str(self.cwd)}),
            encoding="utf-8")

    def _roteiros_por_nome_com_a_primeira_pasta_vencendo(self) -> dict:
        achados = {}
        for pasta in self.roteiros:
            if not pasta.is_dir():
                continue
            for candidato in sorted(pasta.glob("*.json")):
                if not candidato.is_file() or candidato.name in achados:
                    continue
                try:
                    dado = json.loads(candidato.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                if parece_roteiro(dado):
                    achados[candidato.name] = candidato
        return achados

    def catalogo(self) -> list:
        return sorted(self._roteiros_por_nome_com_a_primeira_pasta_vencendo())

    def catalogo_com_descricao(self) -> list:
        achados = self._roteiros_por_nome_com_a_primeira_pasta_vencendo()
        return [{"nome": nome,
                 "descricao": descricao_do_roteiro(achados[nome]),
                 "titulo": titulo_do_roteiro(
                     nome, descricao_do_roteiro(achados[nome]))}
                for nome in sorted(achados)]

    def ler_roteiro_do_catalogo(self, nome: str) -> tuple[dict | None, str | None]:
        alvo = self._roteiros_por_nome_com_a_primeira_pasta_vencendo().get(nome)
        if alvo is None:
            return None, ERRO_ROTEIRO_DESCONHECIDO.format(nome)
        try:
            dado = json.loads(alvo.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            return None, ERRO_ROTEIRO_ILEGIVEL.format(e)
        if not parece_roteiro(dado):
            return None, ERRO_ROTEIRO_SEM_ETAPAS
        return dado, None

    def disparar(self, roteiro: dict, trabalho: str) -> dict:
        self.dir.mkdir(parents=True, exist_ok=True)
        alvo = self.dir / f"{trabalho}{SUFIXO_DO_ROTEIRO}"
        alvo.write_text(json.dumps(roteiro, ensure_ascii=False, indent=2),
                        encoding="utf-8")
        log = (self.dir / f"{trabalho}{SUFIXO_DO_LOG}").open("w",
                                                             encoding="utf-8")
        proc = subprocess.Popen(
            [sys.executable, str(ENCADEADOR), "executar",
             "--roteiro", str(alvo), "--trabalho", trabalho,
             "--dir", str(self.dir), "--cwd", str(self.cwd)],
            stdout=log, stderr=subprocess.STDOUT, cwd=str(self.cwd))
        with self.trava:
            self.rodando[trabalho] = proc
            self.inicio[trabalho] = time.time()
        self.gravar_trava(proc.pid, trabalho)
        return {"trabalho": trabalho, "roteiro": alvo.name}

    def _execucoes_vivas(self) -> dict:
        vivas = {}
        with self.trava:
            for trabalho, proc in self.rodando.items():
                if proc.poll() is None:
                    vivas[trabalho] = {"pid": proc.pid, "proc": proc}
        if self.dir.is_dir():
            for pasta in self.dir.iterdir():
                if not pasta.is_dir() or pasta.name in vivas:
                    continue
                gravado = estado_que_o_motor_gravou(self.dir,
                                                    pasta.name) or {}
                pid = gravado.get("pid")
                if (gravado.get("situacao") in SITUACOES_QUE_O_PANICO_PARA
                        and pid and _processo_vivo(pid)
                        and _pid_ainda_e_do_encadeador(pid)):
                    vivas[pasta.name] = {"pid": pid, "proc": None}
        return vivas

    @staticmethod
    def _segue_viva(alvo) -> bool:
        proc = alvo["proc"]
        return proc.poll() is None if proc else _processo_vivo(alvo["pid"])

    def panico(self) -> dict:
        alvos = self._execucoes_vivas()
        for alvo in alvos.values():
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.kill(alvo["pid"], signal.SIGTERM)
        prazo = time.time() + PRAZO_DO_PANICO_S
        parados = []
        for trabalho, alvo in sorted(alvos.items()):
            while time.time() < prazo and self._segue_viva(alvo):
                time.sleep(0.3)
            derrubado = self._segue_viva(alvo)
            if derrubado:
                with contextlib.suppress(ProcessLookupError,
                                         PermissionError):
                    os.kill(alvo["pid"], signal.SIGKILL)
            parados.append({"trabalho": trabalho, "pid": alvo["pid"],
                            "parada": "derrubada" if derrubado else "limpa"})
        return {"parados": parados, "prazo_s": PRAZO_DO_PANICO_S}

    def mudo(self, ligado: bool) -> dict:
        marcador = Path(self.cwd) / MARCADOR_DE_MUDO
        if ligado:
            marcador.parent.mkdir(exist_ok=True)
            marcador.touch()
        else:
            with contextlib.suppress(FileNotFoundError):
                marcador.unlink()
        return {"muda": marcador.exists()}

    def _roteiro_pronto_para_retomar(self, trabalho: str) -> tuple:
        if erro := recusa_do_nome_de_trabalho(trabalho or ""):
            return None, {"erro": erro}
        copia = self.dir / f"{trabalho}{SUFIXO_DO_ROTEIRO}"
        roteiro = (copia if copia.exists()
                   else roteiro_gravado_no_estado(self.dir, trabalho))
        if not roteiro:
            return None, {"erro": ERRO_SEM_ROTEIRO_PARA_RETOMAR}
        with self.trava:
            vivo = self.rodando.get(trabalho)
            if trabalho in self.em_voo or (vivo and vivo.poll() is None):
                return None, {"erro": ERRO_RESPONDER_COM_EXECUCAO_VIVA}
            self.em_voo.add(trabalho)
        if recado := self.ocupado():
            self._liberar_a_reserva(trabalho)
            return None, {"erro": ERRO_ALVO_OCUPADO.format(recado)}
        return roteiro, None

    def _liberar_a_reserva(self, trabalho: str) -> None:
        with self.trava:
            self.em_voo.discard(trabalho)

    def _disparar_retomada(self, trabalho: str, roteiro: Path,
                           resposta: str | None = None) -> None:
        log = (self.dir / f"{trabalho}{SUFIXO_DO_LOG}").open(
            "a", encoding="utf-8")
        proc = subprocess.Popen(
            comando_de_retomada(roteiro, trabalho, self.dir, self.cwd,
                                resposta),
            stdout=log, stderr=subprocess.STDOUT, cwd=str(self.cwd))
        with self.trava:
            self.rodando[trabalho] = proc
            self.inicio[trabalho] = time.time()
        self.gravar_trava(proc.pid, trabalho)

    def responder(self, trabalho: str, resposta: str,
                  devolver: bool = False) -> dict:
        if not (resposta or "").strip():
            return {"erro": ERRO_RESPOSTA_VAZIA}
        if devolver:
            return self._devolver_com_recado(trabalho, resposta.strip())
        roteiro, recusa = self._roteiro_pronto_para_retomar(trabalho)
        if recusa:
            return recusa
        try:
            _, registro = self._comentar_a_resposta_na_issue(
                trabalho, resposta.strip())
            self._disparar_retomada(trabalho, roteiro, resposta.strip())
        finally:
            self._liberar_a_reserva(trabalho)
        return {"trabalho": trabalho, "retomada": True, "registro": registro}

    def _devolver_com_recado(self, trabalho: str, recado: str) -> dict:
        if erro := recusa_do_nome_de_trabalho(trabalho or ""):
            return {"erro": erro}
        postou, registro = self._comentar_a_resposta_na_issue(
            trabalho, MOLDE_DO_COMENTARIO_DE_DEVOLUCAO.format(recado),
            molde_do_sucesso=RECADO_DEVOLUCAO_NA_ISSUE)
        if not postou:
            return {"erro": ERRO_DEVOLUCAO_SEM_REGISTRO.format(registro)}
        return {"trabalho": trabalho, "devolvido": True, "registro": registro}

    def retomar_em_um_clique(self, trabalho: str) -> dict:
        roteiro, recusa = self._roteiro_pronto_para_retomar(trabalho)
        if recusa:
            return recusa
        try:
            self._disparar_retomada(trabalho, roteiro)
        finally:
            self._liberar_a_reserva(trabalho)
        return {"trabalho": trabalho, "retomada": True}

    def conta_com_cache(self) -> dict:
        momento = time.time()
        with self.trava:
            if self._conta and momento - self._conta_em < INTERVALO_DA_CONTA_S:
                return self._conta
        achado = conta_das_execucoes(self.dir)
        with self.trava:
            self._conta, self._conta_em = achado, momento
        return achado

    def caixas_com_cache(self) -> dict:
        momento = time.time()
        with self.trava:
            fresco = momento - self._caixas_em
            if self._caixas and fresco < INTERVALO_DO_QUADRO_S_POR_CORTESIA_DE_REDE:
                return self._caixas
        configuracao = configuracao_do_executor_sem_validar(self.cwd) or {}
        declaradas = configuracao.get("caixas") or {}
        repositorio = (configuracao.get("issues") or {}).get(
            "repositorio") or ""
        numeros = sorted({int(str(v)) for v in declaradas.values()
                          if str(v).isdigit()})
        achado = {"caixas": []}
        if not numeros or not repositorio \
                or MARCA_DE_MOLDE_NAO_PREENCHIDO in repositorio:
            achado["recado"] = RECADO_SEM_CAIXA
        for numero in numeros:
            try:
                r = subprocess.run(
                    ["gh", "issue", "view", str(numero), "--repo",
                     repositorio, "--json", "body,title"],
                    capture_output=True, text=True, timeout=TIMEOUT_DO_GH_S)
                if r.returncode != 0:
                    achado["recado"] = RECADO_GH_MUDO
                    continue
                dado = json.loads(r.stdout)
                achado["caixas"].append(
                    {"numero": numero, "titulo": dado.get("title", ""),
                     "linhas": linhas_do_corpo_da_caixa(dado.get("body"))})
            except (OSError, subprocess.SubprocessError, ValueError):
                achado["recado"] = RECADO_SEM_REDE_OU_GH
        with self.trava:
            self._caixas, self._caixas_em = achado, momento
        return achado

    def podar(self, identidade: str, motivo: str) -> dict:
        if not (identidade or "").strip() or not (motivo or "").strip():
            return {"erro": ERRO_PODA_SEM_ID_OU_MOTIVO}
        try:
            r = subprocess.run(
                [sys.executable, str(CAIXA), "podar",
                 "--id", identidade.strip(), "--motivo", motivo.strip(),
                 "--cwd", str(self.cwd)],
                capture_output=True, text=True, timeout=TIMEOUT_DO_GH_S * 3)
        except (OSError, subprocess.SubprocessError) as e:
            return {"erro": ERRO_DISPARO_FALHOU.format(e)}
        with self.trava:
            self._caixas, self._caixas_em = None, 0.0
        return {"codigo": r.returncode,
                "saida": (r.stdout + r.stderr).strip()[-1500:]}

    def _comentar_a_resposta_na_issue(
            self, trabalho: str, resposta: str,
            molde_do_sucesso: str = RECADO_RESPOSTA_NA_ISSUE) -> tuple:
        gravado = estado_que_o_motor_gravou(self.dir, trabalho) or {}
        issue = gravado.get("issue")
        configuracao = configuracao_do_executor_sem_validar(self.cwd) or {}
        repositorio = (configuracao.get("issues") or {}).get(
            "repositorio") or ""
        if not issue or not repositorio \
                or MARCA_DE_MOLDE_NAO_PREENCHIDO in repositorio:
            return False, RECADO_RESPOSTA_SO_NA_RETOMADA
        conta_das_issues = (configuracao.get("issues") or {}).get(
            "conta_gh") or ""
        if conta_das_issues \
                and MARCA_DE_MOLDE_NAO_PREENCHIDO not in conta_das_issues \
                and _conta_ativa_do_gh() == conta_das_issues:
            return False, RECADO_CONTA_DO_MOTOR_NAO_ASSINA
        try:
            feito = subprocess.run(
                ["gh", "issue", "comment", str(issue), "--repo", repositorio,
                 "--body", resposta],
                capture_output=True, text=True, timeout=TIMEOUT_DO_GH_S)
        except (OSError, subprocess.SubprocessError):
            return False, RECADO_SEM_REDE_OU_GH
        return ((True, molde_do_sucesso.format(issue))
                if feito.returncode == 0 else (False, RECADO_GH_MUDO))

    def criterios_com_cache(self, trabalho: str) -> dict:
        momento = time.time()
        with self.trava:
            guardado, em = self._criterios.get(trabalho, (None, 0.0))
            if guardado and (momento - em
                             < INTERVALO_DO_QUADRO_S_POR_CORTESIA_DE_REDE):
                return guardado
        achado = self._criterios_da_issue(trabalho)
        with self.trava:
            self._criterios[trabalho] = (achado, momento)
        return achado

    def _criterios_da_issue(self, trabalho: str) -> dict:
        gravado = estado_que_o_motor_gravou(self.dir, trabalho) or {}
        issue = gravado.get("issue")
        if not issue:
            return {"recado": RECADO_TRABALHO_SEM_ISSUE}
        configuracao = configuracao_do_executor_sem_validar(self.cwd) or {}
        repositorio = (configuracao.get("issues") or {}).get(
            "repositorio") or ""
        if not repositorio or MARCA_DE_MOLDE_NAO_PREENCHIDO in repositorio:
            return {"recado": RECADO_SEM_REPOSITORIO_DE_ISSUES}
        try:
            corpo = subprocess.run(
                ["gh", "issue", "view", str(issue), "--repo", repositorio,
                 "--json", "body", "-q", ".body"],
                capture_output=True, text=True, timeout=TIMEOUT_DO_GH_S)
            if corpo.returncode != 0:
                return {"recado": RECADO_GH_MUDO}
            medido = subprocess.run(
                [sys.executable, str(VERIFICAR), "criterios",
                 str(self.dir / trabalho), "--criterios", "-"],
                input=corpo.stdout, capture_output=True, text=True,
                timeout=TIMEOUT_DO_ANDAMENTO_S)
        except (OSError, subprocess.SubprocessError):
            return {"recado": RECADO_SEM_REDE_OU_GH}
        if medido.returncode not in (0, 4):
            return {"recado": (medido.stderr or medido.stdout)
                    .strip()[:CAUDA_DO_ERRO_DO_ANDAMENTO]}
        return {"issue": issue,
                **placar_dos_criterios(
                    medido.returncode, f"{medido.stdout}{medido.stderr}")}

    def andamento(self, trabalho: str, roteiro: Path | None = None) -> dict:
        comando = [sys.executable, str(ENCADEADOR), "andamento",
                   "--trabalho", trabalho, "--dir", str(self.dir)]
        alvo = (roteiro if roteiro and roteiro.exists()
                else roteiro_gravado_no_estado(self.dir, trabalho))
        if alvo:
            comando += ["--roteiro", str(alvo)]
        r = subprocess.run(comando, capture_output=True, text=True,
                           cwd=str(self.cwd), timeout=TIMEOUT_DO_ANDAMENTO_S)
        if r.returncode != 0:
            return {"erro": (r.stderr or r.stdout)
                    .strip()[:CAUDA_DO_ERRO_DO_ANDAMENTO]}
        try:
            estado = json.loads(r.stdout)
        except json.JSONDecodeError:
            return {"erro": ERRO_ANDAMENTO_SEM_JSON}
        with self.trava:
            proc = self.rodando.get(trabalho)
        estado["processo"] = (PROCESSO_RODANDO if proc and proc.poll() is None
                              else PROCESSO_ENCERRADO if proc
                              else PROCESSO_DESCONHECIDO)
        gravado = estado.get("gravado")
        estado["vivacidade"] = vivacidade(proc, self.inicio.get(trabalho),
                                          gravado)
        calar_o_convite_a_disparar_o_que_ja_esta_no_ar(estado)
        estado["espera_aprovacao"] = a_execucao_espera_aprovacao(estado)
        if a_execucao_esta_no_ar(estado):
            estado["etapa_viva"] = etapa_que_escreve_sem_ter_terminado(
                self.dir / trabalho)
        log = self.dir / f"{trabalho}{SUFIXO_DO_LOG}"
        estado["log"] = (log.read_text(encoding="utf-8",
                                       errors="replace")[-CAUDA_DO_LOG_NA_TELA:]
                         if log.exists() else "")
        return estado

    def _issues_abertas_do_repositorio(self, repositorio: str) -> dict:
        try:
            r = subprocess.run(
                ["gh", "issue", "list", "--repo", repositorio, "--state",
                 "open", "--limit", str(LIMITE_DE_ISSUES_NO_QUADRO),
                 "--json", "number,title,labels"],
                capture_output=True, text=True, timeout=TIMEOUT_DO_GH_S)
            if r.returncode != 0:
                return {"issues": [], "recado": RECADO_GH_MUDO}
            issues = json.loads(r.stdout)
            for issue in issues:
                issue["labels"] = [etiqueta.get("name", "")
                                   for etiqueta in issue.get("labels") or []]
            return {"issues": issues, "repositorio": repositorio}
        except (OSError, subprocess.SubprocessError, ValueError):
            return {"issues": [], "recado": RECADO_SEM_REDE_OU_GH}

    def backlog_das_issues_com_cache(self) -> dict:
        momento = time.time()
        with self.trava:
            fresco = momento - self._quadro_em
            if self._quadro and fresco < INTERVALO_DO_QUADRO_S_POR_CORTESIA_DE_REDE:
                return self._quadro
        configuracao = configuracao_do_executor_sem_validar(self.cwd) or {}
        repositorio = (configuracao.get("issues") or {}).get("repositorio") or ""
        if not repositorio or MARCA_DE_MOLDE_NAO_PREENCHIDO in repositorio:
            achado = {"issues": [], "recado": RECADO_SEM_REPOSITORIO_DE_ISSUES}
        else:
            achado = self._issues_abertas_do_repositorio(repositorio)
        with self.trava:
            self._quadro, self._quadro_em = achado, momento
        return achado

    def _resumo_do_trabalho(self, nome: str) -> dict:
        gravado = estado_provado_do_motor(self.dir, nome) or {}
        tem_roteiro_ao_lado = (self.dir / f"{nome}{SUFIXO_DO_ROTEIRO}").exists()
        return {"nome": nome,
                "execucao": bool(gravado) or tem_roteiro_ao_lado,
                "situacao": gravado.get("situacao"),
                "issue": gravado.get("issue")}

    def trabalhos(self) -> list:
        if not self.dir.is_dir():
            return []
        achados = [(self._resumo_do_trabalho(pasta.name),
                    instante_da_pasta_ou_o_comeco_do_tempo(pasta))
                   for pasta in self.dir.iterdir() if pasta.is_dir()]
        achados.sort(key=lambda par: (par[0]["execucao"], par[1],
                                      par[0]["nome"]), reverse=True)
        return [resumo for resumo, _ in achados]


LOGICA_DA_MESA = """
// A lógica da mesa: conta e monta texto, nunca toca no documento. Mora
// separada porque assim ela roda fora do navegador — o --testar deste
// arquivo executa estas funções no node e verifica o HTML que sai delas.
// Enquanto viviam no meio do DOM, ninguém conseguia medi-las.
function esc(s){return String(s??'').replace(/[<&>"']/g,c=>({'<':'&lt;','&':'&amp;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function mm(s){return s==null?'':Math.floor(s/60)+'m'+String(s%60).padStart(2,'0')}

// Vivacidade: sessão de modelo espera a API quase o tempo todo — medido, 443s
// de relógio para 5s de CPU. O sinal aqui não é processador: é o processo
// existir, quantas sessões respiram, e quanto falta para o teto que mata
// sozinho. Espera com prazo não é travamento.
//
// Onde não houve medida, o pedaço SOME. O "?" que o rodapé mostrava dizia
// que a mesa mediu e o resultado foi esse — e ninguém tinha medido nada.
function vivo(v){
  if(!v||v.situacao==='desconhecida')return '';
  if(v.situacao==='encerrado')return `processo <b>encerrado</b> · exit ${v.codigo}`;
  const p=[];
  // Espera não é trabalho. O motor grava dormindo e aguardando-resposta, e a
  // mesa repete o que ele gravou em vez de dizer "trabalhando" com ninguém
  // trabalhando — era o defeito 4.
  if(v.situacao==='dormindo'){
    p.push('<b>dormindo</b>'+(v.ate?` até ${esc(v.ate)}`:'')
           +(v.porque?` (${esc(v.porque)})`:''));
    if(v.etapa)p.push(`na etapa <b>${esc(v.etapa)}</b>`);
    p.push('ninguém está trabalhando');
  }else if(v.situacao==='aguardando-resposta'){
    p.push('<b>aguardando você</b>'+(v.issue?` na issue ${esc(v.issue)}`:''));
    if(v.etapa)p.push(`etapa <b>${esc(v.etapa)}</b>`);
    p.push('responda lá e retome');
  }else{
    // Execução que a mesa não disparou: ela não tem o processo na mão, então
    // não mede sessão nem relógio. Dizer de quem é a execução explica o
    // rodapé curto — inventar número seria a mentira de novo.
    if(v.de_fora)p.push('<b>execução aberta fora desta mesa</b>');
    if(v.sessoes!=null)
      p.push(`<b>${v.sessoes}</b> sessão${v.sessoes===1?'':'es'} viva${v.sessoes===1?'':'s'}`);
    if(v.decorrido_s!=null)p.push(`<b>${mm(v.decorrido_s)}</b> corridos`);
    if(v.resta_s!=null)p.push(`morre sozinha em ${mm(v.resta_s)}`);
    if(v.desde)p.push(`desde ${esc(v.desde)}`);
    if(v.etapa)p.push(`etapa <b>${esc(v.etapa)}</b>`);
  }
  // Estado sem carimbo de tempo não se audita: de quem diz estar no ar, a
  // mesa mostra quando foi a última escrita de verdade. É a linha que separa
  // "está trabalhando" de "está parado dizendo que trabalha".
  if(v.escrita_em)p.push(`última escrita ${esc(v.escrita_em)}`);
  return p.join(' · ');
}

// AGORA: a etapa em curso não fechou evidência nenhuma — e mesmo assim está
// escrevendo. O fim do .log dela é a diferença entre "nada aconteceu" e
// "está acontecendo isto". O bloco só existe enquanto ela escreve.
function agora(d){
  const e=d.etapa_viva;
  if(!e)return '';
  const ordem=String(e.ordem).padStart(2,'0');
  return `<div class="agora">
    <div class="agora-topo">
      <span>agora · etapa ${ordem} ${esc(e.nome)}</span>
      <span>ciclo ${esc(e.ciclo)} · ${esc(e.bytes)} bytes, sem evidência ainda</span>
    </div><pre class="agora-cauda">${esc(e.cauda)}</pre></div>`;
}

function fita(d){
  const et=d.etapas||[];
  if(!et.length)return d.etapa_viva
    ? `<p class="vazia">a etapa ${esc(d.etapa_viva.nome)} está escrevendo — `
      + `a evidência só fecha quando ela termina</p>`
    : '<p class="vazia">nenhuma evidência ainda</p>';
  return et.map(e=>{
    const vd=e.veredito||'espera';
    const faltas=(e.faltas||[]).map(esc).join('<br>');
    const perg=e.pergunta?`<b>${esc(e.pergunta)}</b>`:'';
    const det=[perg,faltas].filter(Boolean).join('<br>');
    return `<li class="linha-r">
      <span class="ordem">${String(e.ordem).padStart(2,'0')}</span>
      <span class="nome">${esc(e.nome)}</span>
      <span class="vd ${vd}">${vd==='espera'?'·····':vd}</span>
      <span class="ciclo">${e.ciclo?e.ciclo.i+'/'+e.ciclo.teto:''}</span>
      ${det?`<span class="detalhe">${det}</span>`:''}</li>`;
  }).join('');
}

// Os estágios da execução: a mesma matéria-prima da fita, lida de relance.
// Cada etapa é um bloco — verde passou, vermelho parou, e a que está em curso
// ganha o contorno. Quem olha vê o passo atual e o que falta sem ler linha.
// Mora numa caixa com rótulo, como a fita e o agora: solto, o primeiro bloco
// verde da tela parecia um botão, e o olho ia parar no lugar errado.
function desenho(d){
  const et=d.etapas||[];
  if(!et.length)return '';
  const atual=et.findIndex(e=>!e.veredito);
  const passos=et.map((e,i)=>{
    const vd=e.veredito||'espera';
    const eu=(i===atual)?' agora':'';
    return `<span class="passo ${vd}${eu}" title="${esc(e.nome)}: ${vd}">` +
           `${esc(e.nome)}</span>`;
  }).join('<span class="seta">→</span>');
  const feitas=et.filter(e=>e.veredito).length;
  return `<div class="estagios">
    <div class="estagios-topo"><span>estágios da execução</span>
      <span>${feitas} de ${et.length} etapas · ${et.length-feitas} pela frente</span>
    </div><div class="desenho">${passos}</div></div>`;
}

// O corpo da mesa, inteiro, em texto. Quem chama é que põe no documento.
// A caixa do log recebe de fora o estado em que estava: repintar recria o
// elemento, e <details> recriado nasce fechado. Era a caixa que se fechava
// sozinha no meio da leitura, a cada 2,5s.
// O HERÓI do "esperando você": a pergunta em corpo grande, o placar dos
// critérios ao lado dos botões, e a resposta que retoma do ponto exato.
// Nada roda enquanto o dono não falar — então a tela inteira aponta para cá.
function heroi(d){
  if(!d.espera_aprovacao)return '';
  const perg=(d.etapas||[]).filter(e=>e.pergunta);
  if(!perg.length)return '';
  return `<div class="heroi" id="heroi">
    <div class="heroi-rotulo">o executor de roteiros está esperando você</div>
    <div class="heroi-pergunta">${perg.map(e=>esc(e.pergunta)).join('<br>')}</div>
    <div id="placar" class="placar">critérios da issue: medindo…</div>
    <textarea id="resposta" placeholder="A resposta entra na retomada — a execução continua do ponto exato. Vazio, Aprovar segue com 'Aprovado.'"></textarea>
    <div class="heroi-botoes">
      <button id="aprovar">Aprovar e retomar</button>
      <button id="devolver" class="secundario">Devolver com recado</button>
    </div>
    <p class="nota">Ela fica parada até você responder — nada roda enquanto isso.
    Aprovar comenta na issue em seu nome, e é o comentário que registra quem
    aprovou. Devolver registra a recusa na issue, com o recado, e não retoma
    nada — a execução segue parada. O arquivo que a pergunta cita continua
    valendo para quem trabalha sem a issue à mão;
    ele não ganha botão porque não tem autor.</p>
  </div>`;
}

// CONFIGURAÇÃO FALTANDO: o exemplo público diz o que existe; o arquivo local
// desta máquina diz o que foi preenchido. Sai daqui o NOME da chave e mais
// nada — o valor local nomeia repositório e conta, e não sobe para a tela.
// Sem nada a apontar o bloco SOME: caixa verde permanente vira paisagem, e
// paisagem ninguém lê.
function pintaConfiguracao(d){
  if(!d) return '';
  if(d.recado) return '<div class="maq"><p class="naomedido">'+esc(d.recado)+'</p></div>';
  const bloco=(titulo,chaves)=>(chaves&&chaves.length)?'<h3>'+esc(titulo)+'</h3><ul>'
    +chaves.map(c=>'<li><b>'+esc(c)+'</b></li>').join('')+'</ul>':'';
  const corpo=bloco('declaradas no exemplo e ausentes aqui',d.faltando)
    +bloco('presentes com valor por preencher',d.por_preencher);
  return corpo?'<div class="maq">'+corpo+'</div>':'';
}

function corpoDaMesa(d,logAberto){
  if(d.erro)return `<div class="recado ruim"><b>não consegui ler</b>${esc(d.erro)}</div>`;
  const v=vivo(d.vivacidade);
  return `
    ${heroi(d)}
    ${desenho(d)}
    ${agora(d)}
    <div class="fita">
      <div class="fita-topo"><span>fita de evidências</span>
        <span>${esc(d.estado||'')} · ${d.paras??0} parada${d.paras===1?'':'s'}</span></div>
      <ul class="tira">${fita(d)}</ul>
    </div>
    ${d.proxima_acao?`<div class="recado"><b>próxima ação</b>${esc(d.proxima_acao)}</div>`:''}
    ${v?`<div class="rodape">${v}</div>`:''}
    ${d.log?`<details class="log"${logAberto?' open':''}><summary>log da execução</summary><pre>${esc(d.log)}</pre></details>`:''}`;
}
"""


PAGINA_MOLDE = """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mesa do executor de roteiros</title><style>
/* A mesa é um instrumento, não um site. Uma família monoespaçada carrega
   todo dado e todo rótulo — placa de equipamento, silkscreen —, e a sans
   entra só onde há frase para ler. Cor é SINAL: o que não é estado não tem
   cor.

   A PALETA é uma só, e é a escura aprovada no épico — não há mais versão
   clara para o navegador escolher. Cada valor abaixo é do desenho aprovado;
   nenhum hex nasce fora daqui, e o único tom derivado se deriva à vista.
   Semântica, igual em toda aba: violeta = rodando · âmbar = esperando você ·
   verde = completa · vermelho = falha · cinza = fila. Cor nunca sozinha:
   sempre ponto mais rótulo. */
:root{
  --papel:#08090a; --superficie:#0f1011; --sulco:#161718;
  --risco:#1b1d21; --linha:#23252a; --borda:#2a2e33;
  --tinta:#f7f8f8; --grafite:#8a8f98;
  --fraco:color-mix(in srgb,#8a8f98 72%,#08090a);
  --corre:#5e6ad2; --segue:#4cb782; --pergunta:#f2c94c; --para:#eb5757;
  --mono:ui-monospace,"SF Mono","Cascadia Mono","Roboto Mono",Menlo,monospace;
  --sans:ui-sans-serif,system-ui,"Segoe UI",Roboto,sans-serif;
}
/* Número não dança ao atualizar: onde o mono carrega dado, largura fixa. */
.selo,.coord dd,.ordem,.ciclo,.linha-i .num,.rodape,.agora-topo,
.estagios-topo,.linha-r{font-variant-numeric:tabular-nums}
*{box-sizing:border-box}
[hidden]{display:none!important}
body{margin:0;padding:0;background:var(--papel);color:var(--tinta);
  font:14px/1.55 var(--sans);-webkit-font-smoothing:antialiased}

/* AS CINCO ABAS: barra lateral de 220px, em texto, com a versão da camada ao
   lado do nome. Cada aba marca a própria linha, e só a folha dela fica sem
   [hidden] — trocar de assunto não recarrega página nem perde a execução que
   a mesa está acompanhando. */
.mesa{display:grid;grid-template-columns:220px minmax(0,1fr)}
.abas{position:sticky;top:0;align-self:start;height:100vh;display:flex;
  flex-direction:column;gap:2px;padding:14px 10px;
  background:var(--superficie);border-right:1px solid var(--borda)}
.marca{display:flex;align-items:center;gap:8px;flex-wrap:wrap;
  padding:6px 10px 16px;font:600 11px/1.4 var(--mono);letter-spacing:.18em;
  text-transform:uppercase;color:var(--grafite)}
.aba{width:100%;min-height:36px;padding:9px 11px;border-radius:4px;
  background:transparent;color:var(--grafite);text-align:left;
  font:500 13px/1.2 var(--sans);letter-spacing:0;text-transform:none}
.aba:hover{background:var(--sulco);color:var(--tinta)}
.aba.atual{background:var(--sulco);color:var(--tinta);
  box-shadow:inset 2px 0 0 var(--corre)}
.conteudo{min-width:0;padding-bottom:64px}
.folha{max-width:1200px;margin:0 auto;padding:0 20px}
.folha>h2{font:600 11px/1 var(--mono);letter-spacing:.18em;
  text-transform:uppercase;color:var(--fraco);margin:22px 0 8px}

/* O QUE A ABA AINDA NÃO TEM. Esta fatia distribuiu nas abas o que as rotas
   de hoje já servem; o resto do desenho aprovado espera rota. Aba que não
   tem tudo diz o que falta na cara — tela vazia sem explicação faz quem olha
   achar que a mesa quebrou. */
.falta{border-left:2px solid var(--pergunta);background:var(--sulco);
  padding:11px 14px;margin:12px 0 0;border-radius:0 3px 3px 0;
  font:12.5px/1.6 var(--sans);color:var(--grafite)}

/* A FAIXA DE ESTADO: fixa no topo, respondendo "preciso agir?" antes de
   qualquer outra coisa — em qualquer estado. À esquerda o estado em voz de
   placa; no meio a resposta em uma frase; à direita a ÚNICA ação principal
   da tela. O resto da mesa mora nas duas colunas abaixo. */
.faixa{position:sticky;top:0;z-index:5;display:flex;align-items:center;
  gap:8px 16px;flex-wrap:wrap;min-height:44px;padding:8px 20px;
  background:var(--papel);border-bottom:2px solid var(--tinta)}
.faixa .estado{display:flex;align-items:center;gap:8px;
  font:600 12px/1 var(--mono);letter-spacing:.18em;text-transform:uppercase}
.faixa .devo{font:12.5px/1.4 var(--sans);color:var(--grafite)}
.abas #panico{margin-top:auto;color:var(--para);border-color:var(--para);
  font-size:12px;min-height:36px}
.abas #panico.armado{background:var(--para);color:var(--tinta)}
.abas .selo-leitura{font:11px/1.4 var(--sans);color:var(--pergunta);
  border:1px solid var(--pergunta);border-radius:8px;padding:4px 8px;
  margin-top:auto;text-align:center}
.abas .selo-leitura:not([hidden])+#panico{margin-top:8px}
.mono-n{font-family:var(--mono);font-variant-numeric:tabular-nums}
.raia{display:flex;align-items:center;gap:8px;margin:4px 0}
.raia-nome{font:11px/1.2 var(--mono);color:var(--grafite);width:180px;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;text-align:right}
.raia-faixa{position:relative;flex:1;height:22px;background:var(--superficie);
  border:1px solid var(--risco);border-radius:6px;overflow:hidden}
.raia-faixa .bloco{position:absolute;top:2px;bottom:2px;background:var(--sulco);
  border:1px solid var(--borda);border-radius:4px;font:10px/1.6 var(--mono);
  color:var(--grafite);padding:0 4px;overflow:hidden;white-space:nowrap;
  cursor:pointer}
.raia-faixa .bloco:hover{color:var(--tinta);border-color:var(--corre)}
.raia-faixa .marca{position:absolute;top:0;bottom:0;width:2px;
  background:var(--pergunta)}
.tempo-log pre{max-height:16rem;overflow:auto;font:11px/1.5 var(--mono);
  background:var(--superficie);border:1px solid var(--risco);border-radius:6px;
  padding:8px;margin-top:6px}
.linha-t .retomar-1{margin-left:auto;font:11px/1 var(--sans);color:var(--segue);
  border:1px solid var(--segue);border-radius:8px;padding:3px 8px}
.linha-t .retomar-1:hover{background:var(--segue);color:var(--papel)}
.linha-i.caixa-fixa{border-style:dashed;opacity:.85}
.podar-linha{color:var(--para);border-color:var(--para)}
.faixa .sino{font:12px/1 var(--sans);color:var(--papel);background:var(--pergunta);
  border-radius:10px;padding:5px 10px;white-space:nowrap}
.faixa .sino b{font-variant-numeric:tabular-nums}
.faixa #mudo{min-height:32px;font-size:12px}
.faixa #mudo.muda{color:var(--pergunta);border-color:var(--pergunta)}
.faixa #acao{margin-left:auto;min-height:40px}
.selo{font:500 10px/1 var(--mono);letter-spacing:.1em;
  color:var(--fraco);border:1px solid var(--linha);border-radius:2px;
  padding:3px 6px;text-transform:none}
.bulbo{width:8px;height:8px;border-radius:50%;background:var(--fraco);
  box-shadow:0 0 0 3px color-mix(in srgb,var(--fraco) 22%,transparent)}
.f-corre .bulbo{background:var(--corre);box-shadow:0 0 0 3px color-mix(in srgb,var(--corre) 22%,transparent);animation:pulsa 1.6s ease-in-out infinite}
.f-corre .estado{color:var(--corre)} .f-segue .bulbo{background:var(--segue)}
.f-segue .estado{color:var(--segue)}
.f-para .bulbo{background:var(--para)} .f-para .estado{color:var(--para)}
.f-pergunta .bulbo{background:var(--pergunta)}
.f-pergunta .estado{color:var(--pergunta)}
@keyframes pulsa{0%,100%{opacity:1}50%{opacity:.35}}
@media(prefers-reduced-motion:reduce){.f-corre .bulbo{animation:none}}

/* AS DUAS COLUNAS DA ABA MESA: a fila de issues (de onde o trabalho sai) e o
   palco (onde a execução viva aparece). A fila é estreita e de linhas curtas;
   o palco recebe o resto. */
.colunas{display:grid;grid-template-columns:340px minmax(0,1fr);
  gap:8px 30px;margin:14px 0 0;align-items:start}
.fila h2,.palco h2{font:600 10px/1 var(--mono);letter-spacing:.18em;
  text-transform:uppercase;color:var(--fraco);margin:18px 0 6px}
.linha-t{display:flex;align-items:center;gap:10px;min-height:44px;
  width:100%;padding:4px 10px;border:0;border-bottom:1px solid var(--risco);
  background:transparent;color:var(--tinta);font:13px/1.4 var(--mono);
  text-align:left;cursor:pointer;text-transform:none;letter-spacing:0}
.linha-t:hover{background:var(--sulco)}
.linha-t span:first-child{min-width:0;overflow:hidden;
  text-overflow:ellipsis;white-space:nowrap}
.linha-t.atual{border-left:2px solid var(--corre);background:var(--sulco)}
.linha-t .selo-s{margin-left:auto;font:600 9px/1 var(--mono);
  letter-spacing:.12em;text-transform:uppercase;color:var(--grafite)}
.linha-i{display:flex;align-items:center;gap:8px;min-height:44px;
  padding:4px 10px;border-bottom:1px solid var(--risco);font:13px/1.4 var(--mono)}
.linha-i .num{color:var(--fraco);min-width:3.2rem}
.linha-i .tit{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;
  white-space:nowrap}
.linha-i button{padding:7px 12px;font-size:10px}

/* O HERÓI do esperando-você: pergunta grande, placar ao lado dos botões. */
.heroi{border:1px solid var(--linha);border-left:3px solid var(--pergunta);
  border-radius:0 3px 3px 0;background:var(--sulco);padding:16px 18px;
  margin:14px 0 0}
.heroi-rotulo{font:600 10px/1 var(--mono);letter-spacing:.16em;
  text-transform:uppercase;color:var(--pergunta);margin-bottom:10px}
.heroi-pergunta{font:600 19px/1.45 var(--sans);margin-bottom:12px}
.placar{border:1px solid var(--linha);border-radius:3px;background:var(--papel);
  padding:10px 12px;font:12.5px/1.6 var(--sans);color:var(--grafite)}
.placar b{color:var(--tinta)}
.placar ul{margin:6px 0 0;padding-left:18px}
.heroi-botoes{display:flex;gap:10px;flex-wrap:wrap;margin-top:12px}
button.secundario{background:transparent;color:var(--tinta);
  border:1px solid var(--tinta)}

/* comandos */
.comandos{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:6px}
label.campo{display:flex;align-items:center;gap:7px;
  font:500 10px/1 var(--mono);letter-spacing:.14em;color:var(--fraco);
  text-transform:uppercase}
select,input,textarea{font:13px/1.4 var(--mono);color:var(--tinta);
  background:var(--sulco);border:1px solid var(--linha);border-radius:3px;
  padding:7px 9px}
select{max-width:100%;min-width:0}
.fila,.palco{min-width:0}
label.campo{flex-wrap:wrap;max-width:100%;min-width:0}
textarea{width:100%;min-height:104px;resize:vertical;margin:10px 0 0;
  background:var(--sulco)}
button{font:600 11px/1 var(--mono);letter-spacing:.16em;text-transform:uppercase;
  color:#fff;background:var(--corre);border:0;border-radius:3px;
  padding:11px 20px;cursor:pointer}
button:disabled{opacity:.4;cursor:default}
:focus-visible{outline:2px solid var(--corre);outline-offset:2px}
.nota{font:12px/1.5 var(--sans);color:var(--fraco);flex:1 1 220px}
.direita{margin-left:auto}

/* COMEÇAR UM TRABALHO: o formulário completo mora na aba Execuções, abaixo
   da lista. O caminho de um clique é a linha do backlog, que fica na aba
   Mesa — a que abre; este é o caminho do pedido escrito à mão. */
#pedido{margin-top:18px;border-top:1px solid var(--linha);padding-top:14px}

/* A MÁQUINA: o que existe aqui e não é do trabalho em curso. Chega pela rota
   /maquina e se reparte entre duas abas — servidores e rotinas em
   Instrumentos, guia e skills em Prompts & skills. É consulta, não
   acompanhamento: muda em dias, não em segundos, então só se lê quando
   alguém abre a aba. A distinção que a cor carrega é uma só: medido e vazio
   é um fato; não medido é a confissão de que ninguém olhou. */
.coord{display:grid;grid-template-columns:auto 1fr;gap:0 18px;
  border-bottom:1px solid var(--linha);padding:10px 0;margin:8px 0 12px}
.coord dt{font:500 10px/1.9 var(--mono);letter-spacing:.16em;color:var(--fraco);
  text-transform:uppercase}
.coord dd{margin:0;font:13px/1.9 var(--mono);word-break:break-all}
.maq-topo{display:flex;align-items:center;gap:.6rem;margin:.4rem 0 .8rem}
button.miudo{padding:.25rem .6rem;font-size:10px}
.maq h3{font:600 11px/1 var(--mono);letter-spacing:.12em;text-transform:uppercase;
  color:var(--grafite);margin:1.1rem 0 .4rem}
.maq ul{list-style:none;padding:0;margin:0}
.maq li{padding:.35rem 0;border-bottom:1px solid var(--risco);
  font:12px/1.5 var(--sans)}
.maq li b{font:600 12px/1.5 var(--mono);color:var(--tinta)}
.maq li span{color:var(--grafite)}
.maq p{font:12px/1.6 var(--sans);color:var(--grafite);margin:.2rem 0 .6rem}
.maq .naomedido{color:var(--pergunta)}
.maq .depe{color:var(--segue)}
.maq .caido{color:var(--para)}
.faixa .depe{color:var(--segue)}
.faixa .caido{color:var(--para)}

/* AGORA: o único bloco da mesa que muda sozinho enquanto você olha. Fica
   acima da fita porque é o presente, e a fita é o passado. Some no instante
   em que a etapa fecha a evidência — a partir dali quem conta a história é a
   fita. */
.agora{margin:20px 0 0;border:1px solid var(--linha);
  border-left:2px solid var(--corre);border-radius:0 3px 3px 0;
  background:var(--sulco);overflow:hidden}
.agora-topo{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;
  padding:9px 14px;border-bottom:1px solid var(--linha);
  font:600 10px/1.4 var(--mono);letter-spacing:.14em;text-transform:uppercase;
  color:var(--corre)}
.agora-topo span+span{color:var(--fraco);font-weight:500;letter-spacing:.1em}
.agora-cauda{margin:0;border:0;border-radius:0;max-height:190px;
  background:transparent}

/* A ASSINATURA: a fita de evidências. O encadeador imprime uma evidência por etapa,
   em ordem — a tela mostra a fita saindo dele, com a borda serrilhada de
   papel picotado feita só com gradiente. */
.fita{margin:24px 0 0;border:1px solid var(--linha);border-radius:3px;
  background:var(--sulco);overflow:hidden}
.fita-topo{display:flex;justify-content:space-between;align-items:center;
  padding:9px 14px 9px 30px;border-bottom:1px solid var(--linha);
  font:500 10px/1 var(--mono);letter-spacing:.16em;color:var(--fraco);
  text-transform:uppercase}
.tira{position:relative;margin:0;padding:0;list-style:none}
.tira::before{content:"";position:absolute;left:9px;top:0;bottom:0;width:7px;
  background:radial-gradient(circle at 3.5px 5px,var(--papel) 2.2px,transparent 2.4px)
    0 0/7px 13px repeat-y}
.linha-r{display:grid;grid-template-columns:34px 1fr 84px 52px;gap:12px;
  align-items:baseline;padding:11px 14px 11px 30px;
  border-bottom:1px dashed var(--linha);font:13px/1.5 var(--mono)}
.linha-r:last-child{border-bottom:0}
.ordem{color:var(--fraco);font-size:11px;letter-spacing:.08em}
.nome{font-weight:500}
.vd{font:600 10px/1 var(--mono);letter-spacing:.14em;text-transform:uppercase}
.vd.segue{color:var(--segue)}
.estagios{margin:14px 0 0;border:1px solid var(--linha);border-radius:3px;
  background:var(--sulco);overflow:hidden}
.estagios-topo{display:flex;justify-content:space-between;gap:12px;
  flex-wrap:wrap;padding:9px 14px;border-bottom:1px solid var(--linha);
  font:500 10px/1.4 var(--mono);letter-spacing:.16em;text-transform:uppercase;
  color:var(--fraco)}
.desenho{display:flex;flex-wrap:wrap;align-items:center;gap:.35rem;
  padding:12px 14px}
.passo{padding:.2rem .5rem;border-radius:3px;font-size:.82rem;
  border:1px solid var(--linha);white-space:nowrap}
.passo.segue{background:var(--segue);color:#fff;border-color:var(--segue)}
.passo.para{background:var(--para);color:#fff;border-color:var(--para)}
.passo.pergunta{background:var(--pergunta);color:#000;border-color:var(--pergunta)}
.passo.espera{opacity:.55}
.passo.agora{outline:2px solid var(--corre);outline-offset:1px;font-weight:600}
.seta{opacity:.4;font-size:.8rem}
.quadro{max-height:24rem;overflow:auto}
.quadro-topo{padding:.35rem 10px;color:var(--fraco);font:11px/1.5 var(--sans)}
.vd.para{color:var(--para)}
.vd.pergunta{color:var(--pergunta)} .vd.espera{color:var(--fraco)}
.ciclo{color:var(--fraco);font-size:11px;text-align:right}
.detalhe{grid-column:2/-1;font:12.5px/1.55 var(--sans);color:var(--grafite);
  margin-top:5px;max-height:8.5em;overflow-y:auto}
.detalhe b{color:var(--tinta)}
.vazia{padding:22px 30px;color:var(--fraco);font:13px/1 var(--mono)}


/* recados */
.recado{border-left:2px solid var(--corre);background:var(--sulco);
  padding:12px 15px;margin:20px 0 0;border-radius:0 3px 3px 0;
  font:13.5px/1.6 var(--sans)}
.recado b{font:600 10px/1 var(--mono);letter-spacing:.16em;text-transform:uppercase;
  display:block;margin-bottom:6px;color:var(--grafite)}
.recado.perg{border-left-color:var(--pergunta)}
.recado.perg b{color:var(--pergunta)}
.recado.ruim{border-left-color:var(--para)} .recado.ruim b{color:var(--para)}

/* rodapé de vivacidade e o log cru */
.rodape{display:flex;gap:10px 26px;flex-wrap:wrap;align-items:baseline;
  margin-top:16px;padding-top:12px;border-top:1px solid var(--linha);
  font:12px/1.6 var(--mono);color:var(--grafite)}
.rodape b{color:var(--tinta);font-weight:600}
details{margin-top:16px}
summary{cursor:pointer;font:500 10px/1 var(--mono);letter-spacing:.16em;
  color:var(--fraco);text-transform:uppercase;padding:6px 0}
pre{margin:8px 0 0;padding:13px 15px;background:var(--sulco);
  border:1px solid var(--linha);border-radius:3px;overflow:auto;max-height:300px;
  font:12px/1.6 var(--mono);white-space:pre-wrap;color:var(--grafite)}
.oquefaz{grid-column:1/-1;margin:2px 0 6px;padding:8px 10px;
  border-left:3px solid var(--linha);background:var(--sulco);
  font:12px/1.55 var(--mono);white-space:pre-wrap;color:var(--grafite)}
/* TELA ESTREITA: a barra lateral deita e vira uma tira rolável no topo, as
   colunas empilham, o palco sobe, a fila vira gaveta logo abaixo, e o botão
   principal ganha dedo (48px). */
@media(max-width:700px){
  .mesa{grid-template-columns:1fr}
  .abas{position:static;height:auto;flex-direction:row;flex-wrap:wrap;
    padding:8px;border-right:0;border-bottom:1px solid var(--borda)}
  .marca{padding:6px 10px;flex-basis:100%}
  .aba{width:auto;min-height:44px;white-space:nowrap}
  .colunas{grid-template-columns:1fr;gap:4px}
  .palco{order:0}
  .fila{order:1;border-top:1px solid var(--linha);padding-top:6px}
  .faixa #acao,#b{min-height:48px}
  #b{width:100%}
  .linha-r{grid-template-columns:28px 1fr;gap:6px}
  .vd,.ciclo{grid-column:2;text-align:left}
}
</style></head><body>

<div class="mesa">
<nav class="abas" id="abas" aria-label="as cinco abas da mesa">
  <div class="marca">a mesa<span class="selo" id="versao">—</span></div>
  <button class="aba atual" id="aba-mesa" data-aba="mesa">Mesa</button>
  <button class="aba" id="aba-execucoes" data-aba="execucoes">Execuções</button>
  <button class="aba" id="aba-instrumentos" data-aba="instrumentos">Instrumentos</button>
  <button class="aba" id="aba-prompts" data-aba="prompts">Prompts &amp; skills</button>
  <button class="aba" id="aba-nucleo" data-aba="nucleo">Configurações</button>
  <span class="selo-leitura" id="selo-leitura" hidden>só-leitura — o servidor recusa escrita</span>
  <button id="panico" title="parada limpa: sinal educado, ponto de retomada na issue, prazo curto, derrubada">parada de emergência</button>
</nav>

<div class="conteudo">
<header class="faixa" id="faixa">
  <span class="estado"><span class="bulbo"></span><span id="farol-txt">medindo…</span></span>
  <span class="devo" id="devo">preciso agir? medindo…</span>
  <span class="devo mono-n" id="conta-dia" hidden title="soma dos registros do executor gravados hoje"></span>
  <span class="devo" id="containers" hidden title="containers deste workspace, medidos pelo docker"></span>
  <span class="sino" id="sino" hidden><b id="sino-n">0</b> esperando você</span>
  <button id="mudo" title="mudo cala a narração na hora — a execução nunca pausa">som</button>
  <button id="acao" hidden></button>
</header>

<section class="folha" id="folha-mesa">
<div class="colunas">
<aside class="fila" id="fila">
  <h2>a fila de issues</h2>
  <div id="quadro" class="quadro"></div>
</aside>

<main class="palco" id="palco">
  <div id="saida"></div>
</main>
</div>
<h2>a linha do tempo do dia</h2>
<div id="tempo-raias"><p class="nota">nenhuma etapa gravada hoje.</p></div>
<div id="tempo-log" class="tempo-log" hidden><pre id="tempo-log-texto"></pre></div>
</section>

<section class="folha" id="folha-execucoes" hidden>
  <h2>execuções</h2>
  <div id="execucoes"></div>
  <label class="campo" title="mostrar também os trabalhos que já terminaram">
    <input id="historico" type="checkbox"> mostrar o histórico
  </label>
  <div id="pedido">
    <h2>começar um trabalho do zero</h2>
    <div class="comandos">
      <label class="campo">o que executar
        <select id="modo"><option value="prompt">um pedido meu</option></select>
      </label>
      <div id="oquefaz" class="oquefaz" hidden></div>
    </div>
    <textarea id="p" placeholder="O pedido, completo. A sessão nasce sem contexto: diga onde olhar, o que medir e o que você aceita como prova."></textarea>
    <div class="comandos">
      <label class="campo" id="lissue" title="o número da issue que este trabalho atende: a execução conta a história lá, passo a passo">nº da issue
        <input id="issue" type="number" min="1" placeholder="—" style="width:64px">
      </label>
      <label class="campo" id="lturnos" title="quantos turnos de sessão cada etapa pode gastar antes de fechar">turnos por etapa
        <input id="turnos" type="number" value="24" min="4" max="120" style="width:62px">
      </label>
      <label class="campo" id="lteto" title="quantas vezes a execução pode reprovar antes de escalar">tentativas
        <input id="teto" type="number" value="3" min="1" max="9" style="width:52px">
      </label>
      <label class="campo" id="lauditoria" title="ao fim da execução o auditor relê as evidências e diz o que ficou por provar; desligado, nada muda">
        <input id="auditoria" type="checkbox"> auditar ao fim
      </label>
    </div>
    <div class="comandos">
      <button id="b">Executar</button>
      <span class="nota" id="dica"></span>
    </div>
  </div>
</section>

<section class="folha" id="folha-instrumentos" hidden>
  <h2>instrumentos</h2>
  <div class="maq-topo">
    <span class="nota">lido uma vez e guardado; nada aqui é do trabalho em curso.</span>
    <button class="maquina-reler miudo">reler</button>
  </div>
  <div id="instrumentos-corpo"></div>
  <h2>o quadro das caixas</h2>
  <div id="caixas-corpo"><p class="nota">abra a aba para ler — o quadro custa rede.</p></div>
  <p class="falta">Esta aba mostra o que as rotas <b>/maquina</b> e
  <b>/caixas</b> medem: servidores MCP, rotinas agendadas e as linhas das
  caixas permanentes, com poda por linha. As rotinas de verificação com botão
  e o instalador esperam rota que os sirva — a fatia seguinte é que os traz.</p>
</section>

<section class="folha" id="folha-prompts" hidden>
  <h2>prompts &amp; skills</h2>
  <div class="maq-topo">
    <span class="nota">lido uma vez e guardado; nada aqui é do trabalho em curso.</span>
    <button class="maquina-reler miudo">reler</button>
  </div>
  <div id="prompts-corpo"></div>
  <p class="falta">Esta aba mostra o que a rota <b>/maquina</b> já mede: o guia
  do executor de roteiros e as skills lidas do disco, com o para-quê de cada
  uma. Os prompts de abertura, com abrir no editor e copiar, esperam rota que
  os sirva — nenhuma existe hoje.</p>
</section>

<section class="folha" id="folha-nucleo" hidden>
  <h2>configurações</h2>
  <dl class="coord">
    <dt>repositório</dt><dd id="repositorio">—</dd>
    <dt>sessão</dt><dd id="alvo">—</dd>
    <dt>evidências</dt><dd id="evidencias">—</dd>
    <dt>modo</dt><dd id="modo-lido">—</dd>
    <dt>auditar ao fim</dt><dd id="auditoria-lida">—</dd>
    <dt>narração</dt><dd>chaves <code>notificacao.ferramenta</code> ("desktop" usa a notificação do sistema), <code>notificacao.tipos</code> e <code>notificacao.silencio</code> (HH:MM-HH:MM) no executor.json — o mudo do cabeçalho cala na hora, sem pausar execução</dd>
  </dl>
  <div class="maq-topo">
    <span class="nota">desligar derruba só a mesa: execução viva sobrevive e segue gravando evidência.</span>
    <button id="desligar" class="miudo" title="POST /desligar — servidor.shutdown()">desligar a mesa</button>
  </div>
  <div class="maq-topo">
    <span class="nota">o exemplo público contra o arquivo desta máquina: só o nome do que falta.</span>
    <button class="maquina-reler miudo">reler</button>
  </div>
  <div id="nucleo-corpo"></div>
  <p class="falta">Esta aba mostra o que as rotas <b>/trabalhos</b> e
  <b>/maquina</b> já medem: onde a mesa está apoiada, o modo do executor de
  roteiros, a auditoria gravada e as chaves de configuração que esta máquina
  não preencheu. Abrir cada arquivo do núcleo no editor espera rota que
  sirva — nenhuma existe hoje.</p>
</section>
</div>
</div>
<script>
const $=i=>document.getElementById(i);
let atual=null, assinatura='', parado=false, ultimoQuadro={};
let ultimaConta={}, tempoLidoEm=0;

/* a lógica da mesa entra aqui */

const ESTADOS={'aguardando-aprovacao':['f-pergunta','esperando você'],
  'parada':['f-para','parada'],'completa':['f-segue','completa'],
  'em-curso':['f-corre','executando'],'dormindo':['f-corre','dormindo']};
const TITULOS={'aguardando-aprovacao':'❓ ESPERANDO VOCÊ','parada':'⛔ parada',
  'completa':'✓ completa','em-curso':'⏳ executando'};

function modoRoteiro(){return $('modo').value!=='prompt'}

let ROTINAS={};
function ajusta(){
  const m=modoRoteiro();
  for(const i of ['p','lteto','lturnos'])$(i).style.display=m?'none':'';
  const cx=$('oquefaz'), texto=m?(ROTINAS[$('modo').value]||''):'';
  cx.textContent=texto; cx.hidden=!texto;
  $('dica').textContent=m
    ?'execução de várias etapas — o prompt de cada uma está dentro do arquivo'
    :'vira uma execução de uma etapa mais a verificação. Turnos de menos = a sessão morre sem entregar nada';
}

// Mesa sem execução: o palco convida, em vez de ficar em branco.
const CONVITE='<div class="recado"><b>mesa sem execução</b>'
  +'Nada para acompanhar. Execute uma issue da fila ao lado, ou escreva '
  +'um pedido — a fita de evidências aparece aqui.</div>';

// A FAIXA responde "preciso agir?" em qualquer estado, e carrega a ÚNICA
// ação principal da tela. Texto curto de propósito: três segundos.
function faixa(estado){
  const [cls,txt]=ESTADOS[estado]||['','ocioso'];
  $('faixa').className='faixa '+cls; $('farol-txt').textContent=txt;
  document.title=(TITULOS[estado]?TITULOS[estado]+' · ':'')+'Mesa do executor de roteiros';
  const backlog=(ultimoQuadro.issues||[]);
  const casos={
    'aguardando-aprovacao':['sim — responda a pergunta.','Responder',()=>rolarAte('heroi')],
    'parada':['sim — leia a falta e decida.','Ler a falta',()=>rolarAte('saida')],
    'em-curso':['não — acompanhe; a etapa atual ainda escreve.','Acompanhar',()=>rolarAte('saida')],
    'dormindo':['não — o motor dorme e volta sozinho.','Acompanhar',()=>rolarAte('saida')],
  };
  let par=casos[estado];
  if(!par)par=backlog.length
    ?['sim — a fila tem trabalho.','Executar a primeira da fila',()=>executarIssue(backlog[0].number)]
    :['sim — escreva um pedido.','Escrever um pedido',abrirPedido];
  $('devo').textContent='preciso agir? '+par[0];
  const a=$('acao'); a.hidden=false; a.textContent=par[1]; a.onclick=par[2];
}
// AS CINCO ABAS. Só uma fica sem [hidden], e a barra marca a própria linha.
// A escolhida vive no endereço para o F5 devolver quem olha onde ele estava.
// A máquina custa rede, então só se lê quando a aba que a mostra abre.
const ABAS=['mesa','execucoes','instrumentos','prompts','nucleo'];
const ABAS_QUE_LEEM_A_MAQUINA=['instrumentos','prompts','nucleo'];
function irPara(aba){
  if(!ABAS.includes(aba))aba=ABAS[0];
  for(const a of ABAS){
    $('folha-'+a).hidden=(a!==aba);
    $('aba-'+a).classList.toggle('atual',a===aba);
  }
  if(location.hash.slice(1)!==aba)location.hash=aba;
  if(ABAS_QUE_LEEM_A_MAQUINA.includes(aba)&&!maquinaLida)maquina(false);
}

// A faixa aponta para peças que moram na aba Mesa: levar até lá é parte de
// chegar nelas — rolar até um elemento escondido não move nada.
function rolarAte(id){irPara('mesa');const el=$(id);if(el)el.scrollIntoView({behavior:'smooth'})}
function abrirPedido(){irPara('execucoes');const cx=$('p');cx.focus()}

// A fila de execuções: linhas de 44px, clique acompanha. A fila nunca cai
// num avulso por conta própria — sem escolha, vale o padrão do servidor.
const SELOS={'dormindo':'💤','aguardando-resposta':'⏸',
  'aguardando-aprovacao':'❓','completa':'✅','parada':'❌','rodando':'⏳'};
function pintaFila(lista){
  const alvo=$('execucoes');
  const chave=lista.map(x=>x.nome+(x.situacao||'')+(x.nome===atual?'*':'')
    +((ultimaConta[x.nome]||{}).usd||'')).join('|');
  if(alvo.dataset.chave===chave)return;
  alvo.dataset.chave=chave;
  const custoDe=x=>{const c=ultimaConta[x.nome];if(!c||!c.usd)return '';
    const etapas=Object.entries(c.etapas||{}).map(([e,v])=>e+': US$ '+v).join('\\n');
    return `<span class="selo-s mono-n" title="${esc(etapas)}">US$ ${c.usd.toFixed(2)}</span>`};
  alvo.innerHTML=lista.map(x=>
    `<button class="linha-t${x.nome===atual?' atual':''}" data-n="${esc(x.nome)}">
      <span>${esc(x.nome)}</span>
      ${x.issue?`<span class="selo-s">#${x.issue}</span>`:''}
      <span class="selo-s">${SELOS[x.situacao]||''} ${esc(x.situacao||'avulsa')}</span>
      ${custoDe(x)}
      ${x.situacao==='parada'?`<span class="retomar-1" data-n="${esc(x.nome)}" title="retoma do ponto de retomada — etapa provada não se repete">retomar</span>`:''}
    </button>`).join('')
    ||'<p class="nota">nenhuma execução ainda.</p>';
  alvo.querySelectorAll('.linha-t').forEach(el=>el.onclick=()=>{
    atual=el.dataset.n;assinatura='';ciclo()});
  // Retomar em um clique: a linha parada carrega o próprio botão. O clique
  // não abre a linha — retoma.
  alvo.querySelectorAll('.retomar-1').forEach(el=>el.onclick=async ev=>{
    ev.stopPropagation();
    let r; try{ r=await (await fetch('/retomar',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({trabalho:el.dataset.n})})).json() }
    catch(e){ r={erro:String(e)} }
    if(r.erro)alert(r.erro); else {atual=el.dataset.n;assinatura='';ciclo()}
  });
}

// O que o repintar não pode apagar: a caixa de log que você abriu. A mesa
// guarda o estado dela aqui fora, porque lá dentro o elemento é recriado.
let logAberto=false;
function pinta(d){
  $('saida').innerHTML=corpoDaMesa(d,logAberto);
  const cauda=$('saida').querySelector('.agora-cauda');
  if(cauda)cauda.scrollTop=cauda.scrollHeight;
  const log=$('saida').querySelector('details.log');
  if(log)log.ontoggle=()=>{logAberto=log.open};
  ligarHeroi(d);
}

// O herói responde pelo dono: Aprovar retoma com "Aprovado." (ou com o que
// estiver escrito); Devolver exige o recado. O placar dos critérios da issue
// chega por /criterios e fica ao lado dos botões — nomeado, não somado.
function ligarHeroi(d){
  const ap=$('aprovar'); if(!ap)return;
  ap.onclick=()=>responder((($('resposta')||{}).value||'').trim()||'Aprovado.',false);
  $('devolver').onclick=()=>{
    const r=(($('resposta')||{}).value||'').trim();
    if(!r){$('resposta').focus();return}
    responder(r,true);
  };
  pintaPlacar(d.trabalho);
}
async function pintaPlacar(t){
  const alvo=$('placar'); if(!alvo)return;
  let c; try{
    c=await (await fetch('/criterios?trabalho='+encodeURIComponent(t||''))).json();
  }catch(e){alvo.textContent='critérios da issue: não medi';return}
  if(c.recado){alvo.textContent='critérios da issue: '+c.recado;return}
  const feitos=c.total-(c.abertos||[]).length;
  alvo.innerHTML=`<b>${feitos} de ${c.total}</b> critérios da issue com prova`
    +((c.abertos||[]).length
      ?` — faltam, nomeados:<ul>${c.abertos.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`
      :' — todos.');
}
async function responder(texto,devolver){
  const botoes=[$('aprovar'),$('devolver')].filter(Boolean);
  botoes.forEach(b=>b.disabled=true);
  let d; try{
    d=await (await fetch('/responder',{method:'POST',
      headers:{'content-type':'application/json'},
      body:JSON.stringify({trabalho:atual,resposta:texto,devolver:!!devolver})})).json();
  }catch(e){botoes.forEach(b=>b.disabled=false);return}
  botoes.forEach(b=>b.disabled=false);
  if(d.erro){$('saida').insertAdjacentHTML('afterbegin',
    `<div class="recado ruim"><b>${devolver?'não devolvi':'não retomei'}</b>${esc(d.erro)}</div>`);return}
  if(d.registro){$('saida').insertAdjacentHTML('afterbegin',
    `<div class="recado"><b>${devolver?'devolvido':'retomando'}</b>${esc(d.registro)}</div>`)}
  assinatura=''; ciclo();
}

async function ciclo(regarrado){
  let d; try{ d=await (await fetch('/estado?trabalho='+encodeURIComponent(atual||''))).json() }
  catch(e){ return }
  $('versao').textContent='camada '+d.versao;
  $('repositorio').textContent=d.repositorio; $('alvo').textContent=d.alvo;
  $('evidencias').textContent=d.evidencias;
  $('modo-lido').textContent=d.modo||'completo';
  $('auditoria-lida').textContent=d.auditoria?'ligada':'desligada';
  ultimoQuadro=d.quadro||{};

  // O sino: quantos trabalhos param em você. Mudo cala a narração na
  // hora e NUNCA pausa execução — a regra dura da F3.
  const PARAM_EM_VOCE=['parada','aguardando-resposta','aguardando-aprovacao'];
  const sinoN=d.trabalhos.filter(x=>PARAM_EM_VOCE.includes(x.situacao)).length;
  $('sino-n').textContent=sinoN; $('sino').hidden=!sinoN;
  $('selo-leitura').hidden=!d.so_leitura;

  // O custo é coluna de primeira classe: por execução na fila, soma do
  // dia na faixa. O número nasce dos registros do executor, nunca da mesa.
  ultimaConta=(d.conta&&d.conta.por_trabalho)||{};
  const somaDia=(d.conta&&d.conta.dia_usd)||0;
  $('conta-dia').hidden=!somaDia;
  $('conta-dia').textContent='US$ '+somaDia.toFixed(2)+' hoje';

  const cs=d.containers||{}, chip=$('containers');
  if(cs.recado){chip.hidden=false;chip.textContent='containers: não medidos';
    chip.title=cs.recado}
  else if((cs.itens||[]).length){chip.hidden=false;
    chip.innerHTML=cs.itens.map(c=>'<span class="'+(c.de_pe?'depe':'caido')+'">'
      +(c.de_pe?'●':'○')+' '+esc(c.nome)+'</span>').join(' ');
    chip.title='containers deste workspace — '
      +cs.itens.map(c=>c.nome+': '+c.estado).join(' · ')}
  else chip.hidden=true;
  if(Date.now()-tempoLidoEm>30000){tempoLidoEm=Date.now();pintaTempo()}

  const mu=$('mudo');
  mu.textContent=d.muda?'mudo':'som';
  mu.classList.toggle('muda',!!d.muda);
  mu.onclick=async()=>{try{await fetch('/mudo',{method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({ligado:!d.muda})})}catch(e){} ciclo()};

  // O seletor de roteiro fala português: o rótulo é o título vindo da
  // descrição, nunca o nome do arquivo.
  const md=$('modo'), antesM=md.value, rot=d.rotinas||[];
  const chaveM=rot.map(r=>r.nome).join('|');
  if(md.dataset.chave!==chaveM){
    md.dataset.chave=chaveM;
    md.innerHTML='<option value="prompt">um pedido meu</option>'
      +rot.map(r=>`<option value="${esc(r.nome)}">${esc(r.titulo||r.nome)}</option>`).join('');
    if(antesM)md.value=antesM;
  }
  ROTINAS={}; for(const r of rot)ROTINAS[r.nome]=r.descricao;
  const au=$('auditoria');
  if(au&&!au.dataset.tocado)au.checked=!!d.auditoria;
  ajusta();

  // A fila de issues: cada linha EXECUTA em um clique — com três recusas
  // da triagem: issue com execução viva não tem botão, caixa permanente é
  // quadro e não se executa, e issue de outro projeto vai separada com a
  // etiqueta dela.
  const q=$('quadro');
  const qs=(d.quadro&&d.quadro.issues)||[];
  const caixasN=d.caixas_numeros||[], declarados=d.projetos_declarados||[];
  const vivas=new Set(d.trabalhos
    .filter(x=>['rodando','dormindo','aguardando-resposta','aguardando-aprovacao'].includes(x.situacao))
    .map(x=>String(x.issue)));
  const chave=JSON.stringify(qs)+(d.modo||'')+caixasN.join()+[...vivas].join()+(d.projeto_do_alvo||'');
  if(q.dataset.chave!==chave){
    q.dataset.chave=chave;
    const soIssues=d.modo==='so-issues';
    const etiquetaDe=i=>(i.labels||[]).find(l=>declarados.includes(l));
    const linha=i=>{
      const caixa=caixasN.includes(i.number), viva=vivas.has(String(i.number));
      const etiqueta=etiquetaDe(i);
      return `<div class="linha-i${caixa?' caixa-fixa':''}"><span class="num">#${i.number}</span>
        <span class="tit" title="${esc(i.title)}">${esc(i.title)}</span>
        ${etiqueta?`<span class="selo-s">${esc(etiqueta)}</span>`:''}
        ${caixa?'<span class="selo-s">caixa — não se executa</span>':''}
        ${viva?'<span class="selo-s">em execução</span>':''}
        ${(soIssues||caixa||viva)?'':`<button class="executar-issue" data-n="${i.number}">executar</button>`}
       </div>`};
    const daCasa=qs.filter(i=>{const e=etiquetaDe(i);return !e||e===d.projeto_do_alvo});
    const deFora=qs.filter(i=>{const e=etiquetaDe(i);return e&&e!==d.projeto_do_alvo});
    q.innerHTML=qs.length
      ? daCasa.map(linha).join('')
        +(deFora.length?'<div class="quadro-topo">outros projetos</div>'+deFora.map(linha).join(''):'')
      : `<div class="quadro-topo">${esc((d.quadro||{}).recado||'nenhuma issue aberta')}</div>`;
    q.querySelectorAll('.executar-issue').forEach(b=>b.onclick=()=>executarIssue(+b.dataset.n));
  }

  // Trabalho terminado sai da lista padrão: mesa com trinta itens mortos
  // esconde o que está vivo. O histórico continua a um clique.
  const tudo=$('historico')&&$('historico').checked;
  const lista=tudo?d.trabalhos
    :d.trabalhos.filter(x=>!['completa','parada'].includes(x.situacao));
  const nomes=lista.map(x=>x.nome);
  if(!atual||!nomes.includes(atual))atual=d.padrao||null;
  pintaFila(lista);

  // Com uma execução no ar, o botão de executar FECHA. A trava por alvo
  // recusaria a segunda, mas deixar o botão vivo é convidar para o erro.
  const EM_CURSO=['rodando','dormindo','aguardando-resposta'];
  const ocupada=d.trabalhos.filter(x=>EM_CURSO.includes(x.situacao));
  const b=$('b');
  if(b){
    b.disabled=ocupada.length>0;
    b.title=ocupada.length
      ? `${ocupada[0].nome} está no ar (${ocupada[0].situacao}) — a trava do alvo recusaria uma segunda execução`
      : '';
    b.textContent=ocupada.length?'No ar…':'Executar';
  }

  const a=d.andamento;
  // Primeira pintura com execução no ar: o padrão acabou de chegar e o
  // andamento ainda não veio — busca de novo UMA vez, em vez de piscar o
  // convite de mesa vazia por 2,5s em cima de trabalho vivo.
  if(!a&&atual&&!regarrado)return ciclo(true);
  if(!a){assinatura='';$('saida').innerHTML=CONVITE;faixa(undefined);return}
  if(!nomes.includes(atual)||!d.trabalhos.find(x=>x.nome===atual&&x.execucao)){
    $('saida').innerHTML=`<div class="recado"><b>fora do executor de roteiros</b>
      <code>${esc(atual||'')}</code> é trilha de evidências avulsas — de um gancho, por
      exemplo —, sem roteiro ao lado. Lida como execução daria estado falso,
      então a mesa não opina.</div>`; faixa(undefined); return;
  }
  faixa(a.erro?undefined:a.estado);
  // Só repinta quando algo mudou: a mesa fica aberta por horas e repintar
  // HTML a cada 2,5s por nada custa bateria e derruba texto selecionado.
  const nova=JSON.stringify(a);
  if(nova!==assinatura){assinatura=nova; pinta(a)}
  parado=a.processo!=='rodando';
}

// Executar a partir de uma issue da fila: UM clique, sem formulário.
async function executarIssue(n){
  await mandar({prompt:`Trabalhe a issue #${n}: leia o corpo dela e siga o `
      +`prompt refinado que estiver lá.`,
    teto:+$('teto').value||3,turnos:+$('turnos').value||24,issue:n,
    auditoria:$('auditoria').checked});
}

async function executar(){
  $('auditoria').dataset.tocado='1';
  const corpo=modoRoteiro()?{roteiro:$('modo').value,auditoria:$('auditoria').checked,issue:+$('issue').value||null}
    :{prompt:$('p').value.trim(),teto:+$('teto').value,turnos:+$('turnos').value,issue:+$('issue').value||null,auditoria:$('auditoria').checked};
  if(!modoRoteiro()&&!corpo.prompt){abrirPedido();return}
  await mandar(corpo);
}

async function mandar(corpo){
  const b=$('b'); b.disabled=true; b.textContent='Executando…';
  let d; try{
    d=await (await fetch('/disparar',{method:'POST',
      headers:{'content-type':'application/json'},body:JSON.stringify(corpo)})).json();
  } finally { b.disabled=false; b.textContent='Executar' }
  if(d.erro){$('saida').innerHTML=`<div class="recado ruim"><b>não executei</b>${esc(d.erro)}</div>`;return}
  atual=d.trabalho; assinatura=''; ciclo();
}

// Medido e vazio é um FATO; não medido é confissão. A tela separa os dois,
// porque lista vazia com cara de resposta é o engano mais barato de acreditar.
function blocoDeLista(titulo,d,linha){
  const cabeca='<h3>'+esc(titulo)+'</h3>';
  if(!d) return cabeca+'<p class="naomedido">não medido: o painel de controle não recebeu este bloco.</p>';
  if(d.recado) return cabeca+'<p class="naomedido">'+esc(d.recado)+'</p>';
  if(!d.itens||!d.itens.length) return cabeca+'<p>nenhum — e isto foi medido.</p>';
  return cabeca+'<ul>'+d.itens.map(linha).join('')+'</ul>';
}

// A máquina chega numa leitura só e se reparte entre duas abas: o que está
// de pé aqui fora vai para Instrumentos, e o que se lê do disco vai para
// Prompts & skills.
function pintaInstrumentos(d){
  return '<div class="maq">'
    +blocoDeLista('servidores MCP',d.mcp,
      s=>'<li><b>'+esc(s.nome)+'</b> <span class="'+(s.de_pe?'depe':'caido')+'">'
        +esc(s.estado)+'</span><br><span>'+esc(s.alvo)+'</span></li>')
    +blocoDeLista('rotinas deste workspace',d.rotinas,
      r=>'<li><b>'+esc(r.unidade)+'</b> <span>'+esc(r.ativa)+'</span><br><span>'
        +esc(r.descricao)+'</span><br><span>próxima: '+esc(r.proxima||'—')
        +' · última: '+esc(r.ultima||'—')+'</span></li>')
    +((d.rotinas&&d.rotinas.de_fora)?'<p>e '+d.rotinas.de_fora
      +' agendamento(s) do sistema operacional, que não são deste workspace.</p>':'')
    +'</div>';
}

function pintaPromptsESkills(d){
  const guia=(d.guia||[]).map(p=>'<li><b>'+esc(p.titulo)+'</b><br><span>'+esc(p.corpo)+'</span></li>').join('');
  return '<div class="maq">'
    +'<h3>como usar</h3><ul>'+guia+'</ul>'
    +blocoDeLista('skills desta máquina',d.skills,
      s=>'<li><b>'+esc(s.nome)+'</b><br><span>'+esc(s.descricao)+'</span></li>')
    +'</div>';
}

let maquinaLida=false;
// A linha do tempo do dia: uma raia por execução, um bloco por etapa
// gravada hoje. O início de um bloco é o fim do anterior — o primeiro do
// dia não tem largura conhecida e vira um traço. Clique abre o log.
async function pintaTempo(){
  const alvo=$('tempo-raias');
  let d; try{ d=await (await fetch('/linha-do-tempo')).json() }catch(e){ return }
  const raias=(d.raias||[]).filter(r=>r.blocos.length||r.marcas.length);
  if(!raias.length){alvo.innerHTML='<p class="nota">nenhuma etapa gravada hoje.</p>';return}
  const ts=s=>s?new Date(s).getTime():null;
  let min=Infinity,max=-Infinity;
  for(const r of raias)for(const b of r.blocos){
    const f=ts(b.fim),i=ts(b.inicio);
    if(f){min=Math.min(min,i||f);max=Math.max(max,f)}
  }
  for(const r of raias)for(const m of r.marcas){
    const q=ts(m.quando); if(q){min=Math.min(min,q);max=Math.max(max,q)}
  }
  const larg=Math.max(max-min,60000);
  const pct=t=>((t-min)/larg*100).toFixed(2)+'%';
  alvo.innerHTML=raias.map(r=>
    '<div class="raia"><span class="raia-nome">'+esc(r.trabalho)+'</span><div class="raia-faixa">'
    +r.blocos.map(b=>{
      const f=ts(b.fim),i=ts(b.inicio)||f-30000;
      return '<span class="bloco" style="left:'+pct(i)+';width:'
        +Math.max((f-i)/larg*100,0.6).toFixed(2)+'%"'
        +(b.log?' data-t="'+esc(r.trabalho)+'" data-l="'+esc(b.log)+'"':'')
        +' title="'+esc(b.etapa)+(b.ciclo?' (ciclo '+b.ciclo+')':'')
        +' — fim '+esc((b.fim||'').slice(11,19))+'">'+esc(b.etapa)+'</span>'}).join('')
    +r.marcas.map(m=>{const q=ts(m.quando);return q?'<span class="marca" style="left:'
      +pct(q)+'" title="'+esc(m.tipo)+' desde '+esc(m.quando.slice(11,19))+'"></span>':''}).join('')
    +'</div></div>').join('');
  alvo.querySelectorAll('.bloco[data-l]').forEach(el=>el.onclick=async()=>{
    let texto; try{ texto=await (await fetch('/log-da-etapa?trabalho='
      +encodeURIComponent(el.dataset.t)+'&arquivo='+encodeURIComponent(el.dataset.l))).text() }
    catch(e){ texto=String(e) }
    $('tempo-log').hidden=false; $('tempo-log-texto').textContent=texto;
  });
}

// O quadro das caixas: linhas com tipo/id/visto-em e a poda por linha.
// Poda pede o motivo — sem registro do fechamento, o caixa.py recusa.
async function pintaCaixas(){
  const alvo=$('caixas-corpo');
  let d; try{ d=await (await fetch('/caixas')).json() }
  catch(e){ alvo.innerHTML='<p class="naomedido">não medido: '+esc(e)+'</p>'; return }
  const blocos=(d.caixas||[]).map(c=>
    '<div class="maq"><b>#'+c.numero+' '+esc(c.titulo)+'</b>'
    +(c.linhas.length?c.linhas.map(l=>
      '<div class="linha-i"><span class="selo-s">'+esc(l.tipo)+'</span>'
      +'<span class="num">'+esc(l.id)+'</span>'
      +'<span class="tit" title="'+esc(l.texto)+'">'+esc(l.texto)+'</span>'
      +(l.visto?'<span class="selo-s">visto '+esc(l.visto)+'</span>':'')
      +'<button class="podar-linha miudo" data-id="'+esc(l.id)+'">podar</button>'
      +'</div>').join('')
      :'<p class="nota">quadro vazio.</p>')
    +'</div>').join('');
  alvo.innerHTML=(d.recado?'<p class="nota">'+esc(d.recado)+'</p>':'')
    +(blocos||'');
  alvo.querySelectorAll('.podar-linha').forEach(b=>b.onclick=async()=>{
    const motivo=prompt('o motivo do fechamento — o commit, a medição ou a issue que a fechou:');
    if(!motivo)return;
    b.disabled=true; b.textContent='podando…';
    let r; try{ r=await (await fetch('/podar',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({id:b.dataset.id,motivo})})).json() }
    catch(e){ r={erro:String(e)} }
    alert(r.erro||r.saida||'sem saída');
    pintaCaixas();
  });
}

async function maquina(reler){
  pintaCaixas();
  const onde={'instrumentos-corpo':pintaInstrumentos,'prompts-corpo':pintaPromptsESkills,
    'nucleo-corpo':d=>pintaConfiguracao(d.configuracao)};
  for(const id in onde)
    $(id).innerHTML='<p class="nota">lendo — o estado dos servidores custa rede.</p>';
  try{
    const d=await (await fetch('/maquina'+(reler?'?reler=1':''))).json();
    for(const id in onde)$(id).innerHTML=onde[id](d);
    maquinaLida=true;
  }catch(e){
    for(const id in onde)
      $(id).innerHTML='<div class="maq"><p class="naomedido">não medido: '+esc(e)+'</p></div>';
  }
}

$('b').onclick=executar;
// O pânico em dois passos: o primeiro clique arma, o segundo dispara.
// Seis segundos sem o segundo clique desarmam sozinhos.
let panicoArmado=null;
$('panico').onclick=async()=>{
  const p=$('panico');
  if(!panicoArmado){
    p.textContent='confirmar a parada?'; p.classList.add('armado');
    panicoArmado=setTimeout(()=>{p.textContent='parada de emergência';
      p.classList.remove('armado');panicoArmado=null},6000);
    return;
  }
  clearTimeout(panicoArmado); panicoArmado=null;
  p.textContent='parando…'; p.disabled=true;
  let r; try{ r=await (await fetch('/panico',{method:'POST'})).json() }
  catch(e){ r={erro:String(e)} }
  p.textContent='parada de emergência'; p.classList.remove('armado');
  p.disabled=false;
  const linhas=(r.parados||[]).map(x=>'<div class="linha-i"><span class="num">'
    +esc(x.trabalho)+'</span><span class="tit">parada '+esc(x.parada)
    +'</span><button class="retomar-panico" data-t="'+esc(x.trabalho)
    +'">retomar</button></div>').join('');
  $('saida').innerHTML='<div class="recado"><b>relatório da parada de emergência</b>'
    +(r.erro?'<p>'+esc(r.erro)+'</p>':(linhas||'<p>nenhuma execução viva para parar.</p>'))
    +'</div>';
  irPara('mesa');
  document.querySelectorAll('.retomar-panico').forEach(b=>b.onclick=()=>{
    atual=b.dataset.t;irPara('execucoes');ciclo()});
};
$('desligar').onclick=async()=>{
  if(!confirm('desligar a mesa? execução viva sobrevive.'))return;
  try{await fetch('/desligar',{method:'POST'})}catch(e){}
  document.body.innerHTML='<p style="padding:24px">mesa desligada — a execução viva, se havia, segue no processo dela.</p>';
};
$('historico').onchange=()=>{assinatura='';ciclo()};
$('modo').onchange=ajusta;
for(const a of ABAS)$('aba-'+a).onclick=()=>irPara(a);
window.addEventListener('hashchange',()=>irPara(location.hash.slice(1)));
document.querySelectorAll('.maquina-reler').forEach(b=>b.onclick=()=>maquina(true));
irPara(location.hash.slice(1));
ajusta(); ciclo();
// Ritmo por necessidade: 2,5s enquanto a execução anda, 10s quando não há o
// que ver. Uma mesa aberta a noite inteira não deve acordar o disco à toa.
setInterval(()=>{if(!parado||Math.random()<.25)ciclo()},2500);
</script></body></html>"""


PAGINA = PAGINA_MOLDE.replace(MARCA_DA_LOGICA_NA_PAGINA, LOGICA_DA_MESA)


def nome_e_descricao_do_frontmatter(texto: str) -> tuple:
    frente = FRONTMATTER_DA_SKILL.match(texto)
    if not frente:
        return "", ""
    nome = CAMPO_NOME_DA_SKILL.search(frente.group(1))
    descricao = CAMPO_DESCRICAO_DA_SKILL.search(frente.group(1))
    return (nome.group(1).strip() if nome else "",
            descricao.group(1).strip() if descricao else "")


def skills_no_disco(raiz: Path) -> dict:
    pastas = [raiz / PASTA_DAS_SKILLS_FONTE, raiz / PASTA_DAS_SKILLS_COPIA]
    viva = next((p for p in pastas if p.is_dir()), None)
    if viva is None:
        return {"itens": [], "recado": RECADO_SEM_PASTA_DE_SKILLS}
    achadas = {}
    for skill in sorted(viva.glob(GLOB_DA_SKILL)):
        with contextlib.suppress(OSError):
            nome, descricao = nome_e_descricao_do_frontmatter(
                skill.read_text(encoding="utf-8", errors="replace"))
            chave = nome or skill.parent.name
            achadas[chave] = {"nome": chave, "descricao": descricao}
    return {"itens": list(achadas.values()), "recado": None,
            "de_onde": str(viva.relative_to(raiz))}


def linha_de_servidor_mcp(linha: str) -> dict | None:
    if SEPARADOR_DO_ESTADO_MCP not in linha or ":" not in linha:
        return None
    endereco, _, estado = linha.rpartition(SEPARADOR_DO_ESTADO_MCP)
    nome, _, alvo = endereco.partition(":")
    if not nome.strip():
        return None
    return {"nome": nome.strip(), "alvo": alvo.strip(),
            "estado": estado.strip(),
            "de_pe": MARCA_DE_MCP_CONECTADO in estado}


def servidores_mcp_com_estado() -> dict:
    if not shutil.which(COMANDO_DO_CLI_DE_SESSAO):
        return {"itens": [], "recado": RECADO_SEM_CLI_PARA_MEDIR_MCP}
    try:
        saida = subprocess.run(
            [COMANDO_DO_CLI_DE_SESSAO, *ARGUMENTOS_DA_LISTA_DE_MCP],
            capture_output=True, text=True, timeout=TIMEOUT_DO_MCP_S)
    except (OSError, subprocess.SubprocessError) as e:
        return {"itens": [], "recado": RECADO_MCP_NAO_RESPONDEU.format(e)}
    itens = [s for s in map(linha_de_servidor_mcp, saida.stdout.splitlines())
             if s]
    if not itens and saida.returncode != 0:
        return {"itens": [], "recado": RECADO_MCP_NAO_RESPONDEU.format(
            saida.returncode)}
    return {"itens": itens, "recado": None}


def unidades_de_rotina(saida: str) -> list:
    unidades = []
    for linha in saida.splitlines():
        partes = linha.split(None, 4)
        if len(partes) >= 4 and partes[0].endswith(SUFIXO_DA_UNIDADE_DE_TEMPO):
            unidades.append({"unidade": partes[0], "ativa": partes[2],
                             "descricao": partes[4] if len(partes) > 4 else ""})
    return unidades


def propriedades_do_agendador(unidade: str, propriedades: tuple) -> dict:
    try:
        saida = subprocess.run(
            [COMANDO_DO_AGENDADOR, *ARGUMENTOS_DO_DETALHE_DA_ROTINA, unidade,
             *propriedades],
            capture_output=True, text=True, timeout=TIMEOUT_DO_AGENDADOR_S)
    except (OSError, subprocess.SubprocessError):
        return {}
    return dict(linha.split("=", 1) for linha in saida.stdout.splitlines()
                if "=" in linha)


def quando_a_rotina_dispara(unidade: str) -> dict:
    return propriedades_do_agendador(unidade, PROPRIEDADES_DA_ROTINA)


def o_que_a_rotina_executa(servico: str) -> str:
    bruto = propriedades_do_agendador(
        servico, PROPRIEDADES_DO_SERVICO).get(PROPRIEDADE_DO_COMANDO, "")
    achado = CAMINHO_DENTRO_DO_COMANDO.search(bruto)
    return achado.group(1) if achado else ""


def e_rotina_deste_workspace(comando: str, raiz: Path) -> bool:
    if not comando or not Path(comando).is_absolute():
        return False
    with contextlib.suppress(ValueError, OSError):
        return Path(comando).resolve().is_relative_to(raiz.resolve())
    return False


def rotinas_do_workspace(raiz: Path) -> dict:
    if os.name == NOME_DO_WINDOWS:
        return {"itens": [], "recado": RECADO_AGENDADOR_DO_WINDOWS}
    if not shutil.which(COMANDO_DO_AGENDADOR):
        return {"itens": [], "recado": RECADO_SEM_AGENDADOR}
    try:
        saida = subprocess.run(
            [COMANDO_DO_AGENDADOR, *ARGUMENTOS_DA_LISTA_DE_ROTINAS],
            capture_output=True, text=True, timeout=TIMEOUT_DO_AGENDADOR_S)
    except (OSError, subprocess.SubprocessError) as e:
        return {"itens": [], "recado": RECADO_AGENDADOR_NAO_RESPONDEU.format(e)}
    if saida.returncode != 0:
        return {"itens": [], "recado": RECADO_AGENDADOR_NAO_RESPONDEU.format(
            saida.returncode)}
    itens, de_fora = [], 0
    for achada in unidades_de_rotina(saida.stdout):
        detalhe = quando_a_rotina_dispara(achada["unidade"])
        servico = detalhe.get(PROPRIEDADE_DO_SERVICO) or achada["unidade"]
        comando = o_que_a_rotina_executa(servico)
        if not e_rotina_deste_workspace(comando, raiz):
            de_fora += 1
            continue
        itens.append({**achada, "comando": comando,
                      "proxima": detalhe.get(PROPRIEDADE_DA_PROXIMA, ""),
                      "ultima": detalhe.get(PROPRIEDADE_DA_ULTIMA, "")})
    return {"itens": itens, "recado": None, "de_fora": de_fora}


def e_projeto_deste_workspace(arquivos_de_configuracao: str,
                              raiz: Path) -> bool:
    for arquivo in arquivos_de_configuracao.split(","):
        arquivo = arquivo.strip()
        if not arquivo or not Path(arquivo).is_absolute():
            continue
        with contextlib.suppress(ValueError, OSError):
            if Path(arquivo).resolve().is_relative_to(raiz.resolve()):
                return True
    return False


def projeto_de_containers(bruto: dict, raiz: Path) -> dict | None:
    nome, estado = bruto.get("Name", ""), bruto.get("Status", "")
    if not nome or not e_projeto_deste_workspace(
            bruto.get("ConfigFiles", ""), raiz):
        return None
    return {"nome": nome, "estado": estado,
            "de_pe": estado.startswith(MARCA_DE_CONTAINERS_DE_PE)}


def containers_do_workspace(raiz: Path) -> dict:
    if not shutil.which(COMANDO_DOS_CONTAINERS):
        return {"itens": [], "recado": RECADO_SEM_DOCKER}
    try:
        saida = subprocess.run(
            [COMANDO_DOS_CONTAINERS, *ARGUMENTOS_DA_LISTA_DE_CONTAINERS],
            capture_output=True, text=True, timeout=TIMEOUT_DOS_CONTAINERS_S)
    except (OSError, subprocess.SubprocessError) as e:
        return {"itens": [],
                "recado": RECADO_CONTAINERS_NAO_RESPONDERAM.format(e)}
    if saida.returncode != 0:
        return {"itens": [], "recado": RECADO_CONTAINERS_NAO_RESPONDERAM.
                format(saida.returncode)}
    try:
        achados = json.loads(saida.stdout or "[]")
    except json.JSONDecodeError as e:
        return {"itens": [],
                "recado": RECADO_CONTAINERS_NAO_RESPONDERAM.format(e)}
    itens = [p for p in (projeto_de_containers(a, raiz) for a in achados)
             if p]
    return {"itens": itens, "recado": None,
            "de_fora": len(achados) - len(itens)}


def guia_do_executor(ponte: PonteParaOEncadeador) -> list:
    return [{"titulo": titulo, "corpo": corpo.format(
        alvo=ponte.cwd, evidencias=ponte.dir)}
        for titulo, corpo in PASSOS_DO_GUIA]


def numeros_das_caixas(configuracao: dict) -> list:
    declaradas = (configuracao or {}).get("caixas") or {}
    return sorted({int(str(v)) for v in declaradas.values()
                   if str(v).isdigit()})


def nomes_dos_projetos(configuracao: dict) -> list:
    declarados = (configuracao or {}).get("projetos") or {}
    return sorted(nome for nome, valor in declarados.items()
                  if isinstance(valor, dict))


def projeto_do_alvo(configuracao: dict, cwd) -> str | None:
    nome = Path(cwd).name
    return nome if nome in nomes_dos_projetos(configuracao) else None


def corpo_com_coordenadas_modo_e_quadro(ponte: PonteParaOEncadeador) -> dict:
    configuracao = configuracao_do_executor_sem_validar(ponte.cwd) or {}
    trabalhos = ponte.trabalhos()
    return {"versao": versao_da_camada_declarada_no_topo_do_montar(),
            "repositorio": str(RAIZ),
            "alvo": str(ponte.cwd),
            "evidencias": str(ponte.dir),
            "trabalhos": trabalhos,
            "padrao": trabalho_que_a_mesa_abre(trabalhos),
            "roteiros": ponte.catalogo(),
            "rotinas": ponte.catalogo_com_descricao(),
            "modo": configuracao.get("modo"),
            "auditoria": bool(configuracao.get(CHAVE_DA_AUDITORIA)),
            "muda": (Path(ponte.cwd) / MARCADOR_DE_MUDO).exists(),
            "so_leitura": bool(getattr(ponte, "so_leitura", False)),
            "conta": ponte.conta_com_cache(),
            "caixas_numeros": numeros_das_caixas(configuracao),
            "projetos_declarados": nomes_dos_projetos(configuracao),
            "projeto_do_alvo": projeto_do_alvo(configuracao, ponte.cwd),
            "containers": ponte.containers_com_cache(),
            "quadro": ponte.backlog_das_issues_com_cache()}


def prefixo_do_nome_do_roteiro(escolhido: str) -> str:
    limpo = re.sub(r"[^a-z0-9]+", "-", Path(escolhido).stem.lower()).strip("-")
    return limpo or PREFIXO_DA_EXECUCAO_SEM_NOME


def roteiro_e_prefixo_do_corpo(ponte: PonteParaOEncadeador,
                               corpo: dict) -> tuple:
    auditoria = corpo.get(CHAVE_DA_AUDITORIA) is True
    lembrar_a_auditoria(ponte.cwd, auditoria)
    escolhido = (corpo.get("roteiro") or "").strip()
    if escolhido:
        roteiro, erro = ponte.ler_roteiro_do_catalogo(escolhido)
        if erro:
            return None, None, erro
        if auditoria:
            roteiro = dict(roteiro, **{CHAVE_DA_AUDITORIA: True})
        issue = corpo.get("issue")
        if isinstance(issue, int) and not isinstance(issue, bool) and issue > 0:
            roteiro = dict(roteiro, issue=issue)
        return roteiro, prefixo_do_nome_do_roteiro(escolhido), None
    prompt = (corpo.get("prompt") or "").strip()
    if not prompt:
        return None, None, ERRO_SEM_PEDIDO
    if prompt.lstrip().startswith("{") and '"etapas"' in prompt:
        return None, None, ERRO_ROTEIRO_COLADO_NO_LUGAR_DO_PEDIDO
    teto = inteiro_na_faixa_ou_padrao(corpo.get("teto"), TETO_MINIMO,
                                      TETO_MAXIMO, TETO_PADRAO_DE_CICLOS)
    turnos = inteiro_na_faixa_ou_padrao(
        corpo.get("turnos"), TURNOS_MINIMO, TURNOS_MAXIMO,
        TURNOS_PADRAO_ACIMA_DO_TETO_DO_MOTOR)
    issue = corpo.get("issue")
    issue = issue if isinstance(issue, int) and issue > 0 else None
    return (roteiro_do_pedido_com_verificacao(prompt, teto, turnos, issue,
                                             auditoria),
            PREFIXO_DO_PEDIDO_DO_PAINEL, None)


def fazer_handler(ponte: PonteParaOEncadeador):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *_):
            return SILENCIO_DO_SERVIDOR

        def _envia(self, corpo: bytes, tipo: str, codigo: int = 200):
            self.send_response(codigo)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

        def _json(self, dado: dict, codigo: int = 200):
            self._envia(json.dumps(dado, ensure_ascii=False).encode(),
                        "application/json; charset=utf-8", codigo)

        def do_GET(self):
            rota = urllib.parse.urlparse(self.path)
            if rota.path == "/":
                return self._envia(PAGINA.encode(), "text/html; charset=utf-8")
            if rota.path == "/trabalhos":
                return self._json(corpo_com_coordenadas_modo_e_quadro(ponte))
            if rota.path == "/maquina":
                consulta = urllib.parse.parse_qs(rota.query)
                return self._json(ponte.maquina_com_cache(
                    relendo=bool(consulta.get("reler"))))
            if rota.path == "/estado":
                consulta = urllib.parse.parse_qs(rota.query)
                nome = (consulta.get("trabalho") or [""])[0]
                corpo = corpo_com_coordenadas_modo_e_quadro(ponte)
                if nome and not recusa_do_nome_de_trabalho(nome):
                    try:
                        corpo["andamento"] = ponte.andamento(
                            nome, ponte.dir / f"{nome}{SUFIXO_DO_ROTEIRO}")
                    except (OSError, subprocess.SubprocessError) as e:
                        corpo["andamento"] = {
                            "erro": ERRO_ANDAMENTO_FALHOU.format(e)}
                return self._json(corpo)
            if rota.path == "/andamento":
                consulta = urllib.parse.parse_qs(rota.query)
                nome = (consulta.get("trabalho") or [""])[0]
                if erro := recusa_do_nome_de_trabalho(nome):
                    return self._json({"erro": erro}, 400)
                roteiro = ponte.dir / f"{nome}{SUFIXO_DO_ROTEIRO}"
                try:
                    return self._json(ponte.andamento(nome, roteiro))
                except (OSError, subprocess.SubprocessError) as e:
                    return self._json(
                        {"erro": ERRO_ANDAMENTO_FALHOU.format(e)}, 500)
            if rota.path == "/caixas":
                return self._json(ponte.caixas_com_cache())
            if rota.path == "/linha-do-tempo":
                return self._json(linha_do_tempo_do_dia(ponte.dir))
            if rota.path == "/log-da-etapa":
                consulta = urllib.parse.parse_qs(rota.query)
                nome = (consulta.get("trabalho") or [""])[0]
                arquivo = (consulta.get("arquivo") or [""])[0]
                if erro := recusa_do_nome_de_trabalho(nome):
                    return self._json({"erro": erro}, 400)
                if not PADRAO_DO_LOG_DA_ETAPA.match(arquivo):
                    return self._json({"erro": ERRO_LOG_FORA_DO_PADRAO}, 400)
                caminho = ponte.dir / nome / arquivo
                if not caminho.is_file():
                    return self._json({"erro": ERRO_ROTA_DESCONHECIDA}, 404)
                return self._envia(
                    cauda_do_arquivo(caminho, 20000).encode(),
                    "text/plain; charset=utf-8")
            if rota.path == "/criterios":
                consulta = urllib.parse.parse_qs(rota.query)
                nome = (consulta.get("trabalho") or [""])[0]
                if erro := recusa_do_nome_de_trabalho(nome):
                    return self._json({"erro": erro}, 400)
                return self._json(ponte.criterios_com_cache(nome))
            return self._json({"erro": ERRO_ROTA_DESCONHECIDA}, 404)

        def do_POST(self):
            caminho = urllib.parse.urlparse(self.path).path
            if caminho not in ("/disparar", "/responder", "/mudo",
                               "/desligar", "/panico", "/retomar", "/podar"):
                return self._json({"erro": ERRO_ROTA_DESCONHECIDA}, 404)
            if getattr(ponte, "so_leitura", False) and caminho != "/desligar":
                return self._json({"erro": ERRO_SO_LEITURA}, 403)
            try:
                tamanho = int(self.headers.get("Content-Length") or 0)
                corpo = json.loads(self.rfile.read(tamanho) or b"{}")
            except (ValueError, json.JSONDecodeError):
                return self._json({"erro": ERRO_CORPO_INVALIDO}, 400)
            if caminho == "/panico":
                return self._json(ponte.panico())
            if caminho == "/retomar":
                achado = ponte.retomar_em_um_clique(
                    corpo.get("trabalho") or "")
                return self._json(achado, 400 if "erro" in achado else 200)
            if caminho == "/podar":
                achado = ponte.podar(corpo.get("id") or "",
                                     corpo.get("motivo") or "")
                return self._json(achado, 400 if "erro" in achado else 200)
            if caminho == "/desligar":
                self._json({"desligando": True})
                return threading.Thread(target=self.server.shutdown,
                                        daemon=True).start()
            if caminho == "/mudo":
                return self._json(ponte.mudo(bool(corpo.get("ligado"))))
            if caminho == "/responder":
                try:
                    achado = ponte.responder(corpo.get("trabalho") or "",
                                             corpo.get("resposta") or "",
                                             devolver=bool(
                                                 corpo.get("devolver")))
                except (OSError, subprocess.SubprocessError) as e:
                    return self._json(
                        {"erro": ERRO_DISPARO_FALHOU.format(e)}, 500)
                return self._json(achado, 400 if "erro" in achado else 200)
            if ocupado := ponte.ocupado():
                return self._json(
                    {"erro": ERRO_ALVO_OCUPADO.format(ocupado)}, 409)
            roteiro, prefixo, erro = roteiro_e_prefixo_do_corpo(ponte, corpo)
            if erro:
                return self._json({"erro": erro}, 400)
            trabalho = nome_de_trabalho(prefixo, roteiro.get("issue"))
            if erro := recusa_do_nome_de_trabalho(trabalho):
                return self._json({"erro": erro}, 400)
            try:
                return self._json(ponte.disparar(roteiro, trabalho))
            except (OSError, subprocess.SubprocessError) as e:
                return self._json(
                    {"erro": ERRO_DISPARO_FALHOU.format(e)}, 500)

    return Handler


class BancadaDoPainel:
    def __init__(self):
        self.casos = 0
        self.falhas = []

    def caso(self, nome, ok) -> None:
        self.casos += 1
        if not ok:
            self.falhas.append(nome)


def versao_impressa_pelo_instalador():
    instalador = RAIZ / INSTALADOR
    if not instalador.is_file():
        return versao_da_camada_declarada_no_topo_do_montar()
    saida = subprocess.run(
        [sys.executable, str(instalador), BANDEIRA_DE_VERSAO],
        capture_output=True, text=True,
        timeout=TEMPO_DO_INSTALADOR).stdout.split(MARCA_DA_VERSAO)[-1].split()
    return saida[0] if saida else ""


def html_que_a_logica_da_mesa_produz(medidas: dict) -> tuple:
    if not shutil.which(COMANDO_DO_NAVEGADOR_SEM_TELA):
        return None, RECADO_SEM_NAVEGADOR_SEM_TELA
    corpo = "\n".join(f"medido[{json.dumps(nome)}] = String({expressao});"
                      for nome, expressao in medidas.items())
    with tempfile.TemporaryDirectory(prefix="mesa-node-") as tmp:
        arquivo = Path(tmp) / "medida.mjs"
        arquivo.write_text(LOGICA_DA_MESA + ABERTURA_DA_MEDIDA_NO_NODE
                           + corpo + FECHO_DA_MEDIDA_NO_NODE,
                           encoding="utf-8")
        rodou = subprocess.run(
            [COMANDO_DO_NAVEGADOR_SEM_TELA, str(arquivo)],
            capture_output=True, text=True, timeout=TIMEOUT_DO_NAVEGADOR_S)
    if rodou.returncode != 0:
        return None, RECADO_NODE_RECUSOU.format(rodou.stderr.strip())
    return json.loads(rodou.stdout), None


MEDIDAS_QUE_PASSAM_TODAS_POR_CORPO_DA_MESA = {
    "sem medida nenhuma":
        "corpoDaMesa({etapas:[],vivacidade:{situacao:'trabalhando'}},false)",
    "com medida":
        "corpoDaMesa({etapas:[],vivacidade:{situacao:'trabalhando',"
        "sessoes:2,decorrido_s:125}},false)",
    "com etapa escrevendo":
        "corpoDaMesa({etapas:[],etapa_viva:{ordem:2,nome:'consertar',ciclo:1,"
        "bytes:65,cauda:'escrevendo a correcao agora mesmo'}},false)",
    "sem etapa escrevendo": "corpoDaMesa({etapas:[]},false)",
    "log que estava aberto":
        "corpoDaMesa({etapas:[],log:'a linha do log'},true)",
    "log que estava fechado":
        "corpoDaMesa({etapas:[],log:'a linha do log'},false)",
    "execução que diz estar no ar":
        "corpoDaMesa({etapas:[],vivacidade:{situacao:'parada',de_fora:true,"
        "escrita_em:'2026-08-22T09:14:07-03:00'}},false)",
}


MEDIDAS_DO_ESCAPE_DE_ATRIBUTO = {
    "aspas duplas": """esc('"')""",
    "aspas simples": '''esc("'")''',
    "sinais de tag": "esc('<&>')",
}


MEDIDAS_DA_CONFIGURACAO_QUE_FALTA = {
    "nada faltando":
        "pintaConfiguracao({recado:null,faltando:[],por_preencher:[]})",
    "chave ausente e chave por preencher":
        "pintaConfiguracao({recado:null,faltando:['voz'],"
        "por_preencher:['issues.repositorio']})",
    "sem exemplo com que comparar":
        "pintaConfiguracao({recado:'não há com o que comparar: x'})",
    "bloco que a rota não mandou": "pintaConfiguracao(undefined)",
}


ABAS_DA_MESA = (
    ("mesa", "Mesa", "quadro"),
    ("execucoes", "Execuções", "execucoes"),
    ("instrumentos", "Instrumentos", "instrumentos-corpo"),
    ("prompts", "Prompts &amp; skills", "prompts-corpo"),
    ("nucleo", "Configurações", "repositorio"),
)

ABA_E_A_ROTA_QUE_HOJE_A_ALIMENTA = (("instrumentos", "/maquina"),
                                    ("prompts", "/maquina"),
                                    ("nucleo", "/trabalhos"),
                                    ("nucleo", "/maquina"))

CORES_DA_PALETA_APROVADA = ("#08090a", "#0f1011", "#161718", "#1b1d21",
                            "#23252a", "#2a2e33", "#f7f8f8", "#8a8f98",
                            "#5e6ad2", "#4cb782", "#f2c94c", "#eb5757")

ROTA_QUE_A_PAGINA_BUSCA = re.compile(r"fetch\('(/[a-z-]*)")
ROTA_QUE_O_HANDLER_DECLARA = re.compile(r'"(/[a-z-]*)"')
ABERTURA_DO_HANDLER = "def fazer_handler("
FECHO_DO_HANDLER = "\nclass BancadaDoPainel"


def trecho_da_aba(chave: str) -> str:
    abre = PAGINA.index(f'id="folha-{chave}"')
    return PAGINA[abre:PAGINA.index("</section>", abre)]


def rotas_que_o_servidor_atende() -> set:
    fonte = Path(__file__).read_text(encoding="utf-8")
    corpo = fonte[fonte.index(ABERTURA_DO_HANDLER):
                  fonte.index(FECHO_DO_HANDLER)]
    return set(ROTA_QUE_O_HANDLER_DECLARA.findall(corpo))


def _sobre_as_cinco_abas(b) -> None:
    b.caso("a navegação existe: uma barra lateral, e nela as cinco abas",
         PAGINA.count("<nav") == 1
         and PAGINA.count('data-aba="') == len(ABAS_DA_MESA) == 5)
    b.caso("a barra lateral tem os 220px do desenho aprovado",
         "grid-template-columns:220px" in PAGINA)
    b.caso("a barra carrega a versão da camada ao lado do nome",
         'id="versao"' in PAGINA[PAGINA.index("<nav"):PAGINA.index("</nav>")])
    for chave, rotulo, alvo in ABAS_DA_MESA:
        b.caso(f"a aba {rotulo} tem item na barra e conteúdo na folha dela",
             f'data-aba="{chave}"' in PAGINA and rotulo in PAGINA
             and f'id="{alvo}"' in trecho_da_aba(chave))
    b.caso("a aba que abre é a Mesa — as outras quatro nascem escondidas",
         [c for c, _, _ in ABAS_DA_MESA if " hidden" in trecho_da_aba(c)[:44]]
         == ["execucoes", "instrumentos", "prompts", "nucleo"])
    b.caso("cada aba marca a própria linha na barra",
         "$('aba-'+a).classList.toggle('atual',a===aba)" in PAGINA
         and ".aba.atual{" in PAGINA)
    b.caso("trocar de aba só troca a folha visível: não recarrega a página "
           "nem larga a execução que a mesa acompanha",
         "function irPara(" in PAGINA
         and "$('folha-'+a).hidden=(a!==aba)" in PAGINA)
    buscadas = set(ROTA_QUE_A_PAGINA_BUSCA.findall(PAGINA))
    b.caso("nenhuma aba serve rota que não existe: tudo que a página busca "
           "está entre as rotas que o servidor atende",
         len(buscadas) >= 5 and buscadas <= rotas_que_o_servidor_atende())
    for chave, rota in ABA_E_A_ROTA_QUE_HOJE_A_ALIMENTA:
        aba = trecho_da_aba(chave)
        b.caso(f"a aba {chave} mostra o que {rota} já serve e diz na cara o "
               "que ainda espera rota",
             'class="falta"' in aba and rota in aba and "espera" in aba)


def _sobre_o_que_a_tela_escreve(b) -> None:
    escrito, recado = html_que_a_logica_da_mesa_produz(
        MEDIDAS_QUE_PASSAM_TODAS_POR_CORPO_DA_MESA
        | MEDIDAS_DO_ESCAPE_DE_ATRIBUTO)
    if recado:
        print(recado)
    if escrito is None:
        b.caso(recado, recado == RECADO_SEM_NAVEGADOR_SEM_TELA)
        return

    b.caso("mentira 3 — sem medida nenhuma o rodapé não escreve nada: o '?' "
           "que ele mostrava dizia que a mesa mediu e deu isso",
           "?" not in escrito["sem medida nenhuma"]
           and 'class="rodape"' not in escrito["sem medida nenhuma"])
    b.caso("e o que foi medido continua aparecendo — o rodapé some por falta "
           "de medida, não por preguiça",
           'class="rodape"' in escrito["com medida"]
           and "2m05" in escrito["com medida"])
    b.caso("mentira 2 — com etapa escrevendo, a tela mostra o fim do .log "
           "dela, que é a diferença entre nada acontece e isto está "
           "acontecendo",
           "escrevendo a correcao agora mesmo" in escrito["com etapa escrevendo"]
           and "agora · etapa 02 consertar" in escrito["com etapa escrevendo"])
    b.caso("e a fita para de dizer que não há evidência nenhuma: diz qual "
           "etapa está escrevendo",
           "nenhuma evidência ainda" not in escrito["com etapa escrevendo"]
           and "a evidência só fecha quando ela termina"
           in escrito["com etapa escrevendo"])
    b.caso("sem etapa escrevendo, o bloco de agora some e a fita volta a "
           "confessar o vazio — o vazio medido é um fato",
           'class="agora"' not in escrito["sem etapa escrevendo"]
           and "nenhuma evidência ainda" in escrito["sem etapa escrevendo"])
    b.caso("mentira 5 — a caixa de log volta do repintar aberta, se estava "
           "aberta: repintar recria o elemento, e ele nascia fechado",
           '<details class="log" open>' in escrito["log que estava aberto"])
    b.caso("e volta fechada se estava fechada — a mesa devolve o que você "
           "escolheu, não o que ela prefere",
           '<details class="log">' in escrito["log que estava fechado"])
    b.caso("de quem diz estar no ar, a mesa mostra QUANDO foi a última "
           "escrita — estado sem carimbo de tempo não se audita",
           "última escrita 2026-08-22T09:14:07-03:00"
           in escrito["execução que diz estar no ar"])
    b.caso("aspas viram entidade no esc — texto vindo de issue não escapa "
           "do atributo em que a mesa o escreve",
           escrito["aspas duplas"] == "&quot;"
           and escrito["aspas simples"] == "&#39;"
           and escrito["sinais de tag"] == "&lt;&amp;&gt;")


def _sobre_a_ordem_da_tela(b) -> None:
    b.caso("a faixa de estado vem antes de tudo — o estado é a primeira "
           "coisa que a mesa diz",
           PAGINA.index('id="faixa"') < PAGINA.index('id="fila"')
           and PAGINA.index('id="faixa"') < PAGINA.index('id="palco"'))
    b.caso("a faixa é fixa: rolar não esconde a resposta de 'preciso agir?'",
           "position:sticky" in PAGINA)
    b.caso("o formulário do pedido mora na aba Execuções, e o caminho de um "
           "clique é a linha do backlog — que fica na aba que abre",
           PAGINA.index('id="quadro"') < PAGINA.index('id="pedido"')
           and 'id="pedido"' in trecho_da_aba("execucoes")
           and 'id="quadro"' in trecho_da_aba("mesa"))
    b.caso("o detalhe de uma evidência rola dentro de si: prosa longa "
           "de execução terminada não empurra o resto para fora da tela",
           "max-height:8.5em;overflow-y:auto" in PAGINA)
    b.caso("a fila lista execuções como linhas clicáveis, e a linha "
           "acompanhada fica marcada",
           'class="linha-t' in PAGINA and "linha-t.atual" in PAGINA)
    b.caso("mesa sem execução convida em vez de ficar em branco",
           "mesa sem execução" in PAGINA and "escreva" in PAGINA)


def _sobre_a_configuracao_que_falta(b) -> None:
    exemplo = {"modo": "${completo | so-issues}",
               "issues": {"repositorio": "${DONO}/${REPO}",
                          "conta_gh": "${CONTA}"},
               "notificacao": {"ferramenta": "${CAMINHO}"},
               "projetos": {"${ETIQUETA_DO_PROJETO}": {"repositorio": "${X}"}}}
    with tempfile.TemporaryDirectory(prefix="mesa-config-") as pasta:
        base = Path(pasta)
        (base / "nucleo").mkdir()
        def escrever(nome, dado):
            (base / "nucleo" / nome).write_text(
                json.dumps(dado, ensure_ascii=False), encoding="utf-8")

        escrever("executor.exemplo.json", exemplo)
        escrever("executor.json", {"modo": "completo",
                                   "issues": {"repositorio": "dono/fila",
                                              "conta_gh": "robo"},
                                   "projetos": {"atlas": {"repositorio":
                                                          "atlas"}}})
        achado = configuracao_que_falta_nesta_maquina(base)
        b.caso("a mesa mostra as chaves declaradas no exemplo e ausentes no "
               "local, pelo nome",
               achado["faltando"] == ["notificacao"])
        b.caso("chave do exemplo que é ela mesma um molde não vira falta: "
               "${ETIQUETA_DO_PROJETO} nomeia o lugar, não a chave",
               not any(c.startswith("projetos.") for c in achado["faltando"]))
        b.caso("nenhum valor de chave local aparece em rota nenhuma: o que "
               "sai do confronto é só nome",
               "dono/fila" not in json.dumps(achado, ensure_ascii=False)
               and "robo" not in json.dumps(achado, ensure_ascii=False))

        escrever("executor.json", {"modo": "completo",
                                   "issues": {"repositorio": "${DONO}/${REPO}",
                                              "conta_gh": "robo"},
                                   "notificacao": {"ferramenta":
                                                   "/usr/bin/avisar"},
                                   "projetos": {}})
        achado = configuracao_que_falta_nesta_maquina(base)
        b.caso("a mesa mostra as chaves presentes cujo valor ainda é ${...}, "
               "pelo caminho até elas",
               achado["por_preencher"] == ["issues.repositorio"]
               and achado["faltando"] == [])

        escrever("executor.json", exemplo)
        escrever("executor.exemplo.json", exemplo)
        b.caso("chave de lista com molde dentro também é chave por preencher",
               ainda_e_molde(["já preenchido", "${AINDA_NAO}"])
               and not ainda_e_molde(["já preenchido"]))

        escrever("executor.json", {"modo": "completo",
                                   "issues": {"repositorio": "dono/fila",
                                              "conta_gh": "robo"},
                                   "notificacao": {"ferramenta":
                                                   "/usr/bin/avisar"},
                                   "projetos": {"atlas": {"repositorio":
                                                          "atlas"}}})
        completo = configuracao_que_falta_nesta_maquina(base)
        b.caso("com o local completo a mesa não acende nada — as duas listas "
               "voltam vazias, e não há caixa verde para pintar",
               completo["faltando"] == []
               and completo["por_preencher"] == []
               and completo["recado"] is None)

        (base / "nucleo" / "executor.exemplo.json").unlink()
        sem_exemplo = configuracao_que_falta_nesta_maquina(base)
        b.caso("sem o .exemplo.json no disco a mesa não quebra: diz que não "
               "há com o que comparar",
               sem_exemplo["recado"] == RECADO_SEM_EXEMPLO_PARA_COMPARAR)

    with tempfile.TemporaryDirectory(prefix="mesa-config-vazio-") as pasta:
        base = Path(pasta)
        (base / "nucleo").mkdir()
        (base / "nucleo" / "executor.exemplo.json").write_text(
            json.dumps(exemplo), encoding="utf-8")
        sem_local = configuracao_que_falta_nesta_maquina(base)
        b.caso("sem o executor.json local o resultado é NÃO MEDIDO, nunca "
               "uma lista vazia com cara de tudo preenchido",
               sem_local["recado"] == RECADO_SEM_CONFIGURACAO_LOCAL)

    escrito, recado = html_que_a_logica_da_mesa_produz(
        MEDIDAS_DA_CONFIGURACAO_QUE_FALTA)
    if escrito is None:
        b.caso(recado, recado == RECADO_SEM_NAVEGADOR_SEM_TELA)
        return
    b.caso("com o local completo o bloco da tela some inteiro",
           escrito["nada faltando"] == "")
    b.caso("e some também quando a rota não mandou o bloco",
           escrito["bloco que a rota não mandou"] == "")
    b.caso("com falta, a tela nomeia a chave ausente e a que está por "
           "preencher",
           "voz" in escrito["chave ausente e chave por preencher"]
           and "issues.repositorio"
           in escrito["chave ausente e chave por preencher"])
    b.caso("sem exemplo, a tela diz que não há com o que comparar em vez de "
           "ficar em branco",
           "não há com o que comparar"
           in escrito["sem exemplo com que comparar"])


def _sobre_a_ponte_e_o_catalogo(b) -> None:
    with tempfile.TemporaryDirectory(prefix="painel-h6-") as tmp:
        base = Path(tmp)
        (base / "evidencias" / "t-dorme").mkdir(parents=True)
        (base / "evidencias" / "t-dorme" / "estado.json").write_text(json.dumps({
            "situacao": "dormindo", "ate": "12:36", "porque": "limite de uso",
            "etapa": "analisa", "desde": "2026-08-18T06:36:00-03:00"}),
            encoding="utf-8")
        (base / "evidencias" / "t-espera").mkdir(parents=True)
        (base / "evidencias" / "t-espera" / "estado.json").write_text(json.dumps({
            "situacao": "aguardando-resposta", "issue": 39,
            "etapa": "decide"}), encoding="utf-8")
        (base / "evidencias" / "t-pronta").mkdir(parents=True)
        (base / "evidencias" / "t-pronta" / "estado.json").write_text(json.dumps({
            "situacao": "completa"}), encoding="utf-8")

        class ProcVivo:
            pid = 1

            def poll(self):
                return None

        v = vivacidade(ProcVivo(), time.time() - 60,
                       estado_que_o_motor_gravou(base / "evidencias", "t-dorme"))
        b.caso("motor dormindo NÃO é 'trabalhando' na mesa",
             v["situacao"] == "dormindo" and v["ate"] == "12:36")
        v = vivacidade(ProcVivo(), time.time() - 60,
                       estado_que_o_motor_gravou(base / "evidencias", "t-espera"))
        b.caso("aguardando resposta aparece com o número da issue",
             v["situacao"] == "aguardando-resposta" and v["issue"] == 39)
        v = vivacidade(ProcVivo(), time.time() - 60, None)
        b.caso("sem estado gravado, a mesa segue como era",
             v["situacao"] == "trabalhando")
        b.caso("estado ilegível não derruba a leitura",
             estado_que_o_motor_gravou(base / "evidencias", "nao-existe") is None)

        morto = subprocess.Popen([sys.executable, "-c", "pass"])
        morto.wait()
        (base / "evidencias" / "t-fantasma").mkdir(parents=True)
        (base / "evidencias" / "t-fantasma" / "estado.json").write_text(
            json.dumps({"situacao": "rodando", "pid": morto.pid,
                        "desde": "2026-08-22T10:00:00-03:00"}),
            encoding="utf-8")

        ponte = PonteParaOEncadeador(base, base / "evidencias", [])
        situacoes = {x["nome"]: x["situacao"] for x in ponte.trabalhos()}
        b.caso("a lista de trabalhos carrega a situação de cada um",
             situacoes == {"t-dorme": "dormindo",
                           "t-espera": "aguardando-resposta",
                           "t-pronta": "completa",
                           "t-fantasma": "parada"})
        b.caso("e a da lista é a situação PROVADA, a mesma do resto da mesa: "
               "'rodando' de processo morto não chega à lista lateral",
             situacoes["t-fantasma"] == "parada")
        b.caso("e ela sai do disco, sem um subprocesso por trabalho",
             ponte.trabalhos() == ponte.trabalhos())

        e = calar_o_convite_a_disparar_o_que_ja_esta_no_ar({
            "processo": "rodando", "estado": "em-curso",
            "proxima_acao": "responda na issue",
            "vivacidade": {"situacao": "aguardando-resposta"}})
        b.caso("quem espera não recebe 'rodando agora — espere'",
             e["proxima_acao"] == "responda na issue")
        e = calar_o_convite_a_disparar_o_que_ja_esta_no_ar({
            "processo": "rodando", "estado": "em-curso",
            "proxima_acao": "execute", "vivacidade": {}})
        b.caso("mas o convite a disparar de novo continua calado",
             "ão dispare de novo" in e["proxima_acao"])

        b.caso("sem repositório configurado o quadro devolve recado, não erro",
             ponte.backlog_das_issues_com_cache()["issues"] == []
             and "sem repositório" in ponte.backlog_das_issues_com_cache()["recado"])
        (base / "nucleo").mkdir()
        (base / "nucleo" / "executor.json").write_text(json.dumps({
            "modo": "so-issues",
            "issues": {"repositorio": "${DONO}/${REPO}"}}), encoding="utf-8")
        ponte._quadro = None
        b.caso("repositório ainda no molde também não vira chamada de rede",
             "sem repositório" in ponte.backlog_das_issues_com_cache()["recado"])
        b.caso("o modo do executor é lido para a mesa esconder o disparo",
             (configuracao_do_executor_sem_validar(base) or {}).get("modo")
             == "so-issues")

    with tempfile.TemporaryDirectory(prefix="mesa-roteiro-do-estado-") as tmp:
        base = Path(tmp)
        pasta = base / "ev" / "t-meio"
        pasta.mkdir(parents=True)
        roteiro = base / "tres-etapas.json"
        roteiro.write_text(json.dumps({"etapas": [
            {"nome": "a", "tipo": "codigo", "comando": "true"},
            {"nome": "b", "tipo": "codigo", "comando": "true",
             "depende": ["a"]},
            {"nome": "c", "tipo": "codigo", "comando": "true",
             "depende": ["b"]}]}), encoding="utf-8")
        (pasta / "01-a-c1.json").write_text(json.dumps(
            {"etapa": "a", "trabalho": "t-meio",
             "quando": "2026-08-23T10:00:00-03:00", "veredito": "segue",
             "provado": [{"afirmacao": "x", "comando": "true", "saida": ""}],
             "suposto": [], "faltas": [], "ciclo": {"i": 1, "teto": 3}}),
            encoding="utf-8")
        (pasta / "estado.json").write_text(json.dumps(
            {"situacao": "parada", "roteiro": str(roteiro)}),
            encoding="utf-8")
        ponte = PonteParaOEncadeador(base, base / "ev", [])
        meio = ponte.andamento("t-meio", base / "ev" / "t-meio.json")
        b.caso("sem a cópia do roteiro ao lado das evidências, a mesa acha "
               "o caminho gravado no estado — a fita sai inteira",
             len(meio.get("etapas", [])) == 3)



def _sobre_o_disparo_e_a_regua(b) -> None:
    b.caso("o vínculo com a issue viaja no roteiro do pedido",
         roteiro_do_pedido_com_verificacao("x", 3, 24, 39)["issue"] == 39)
    b.caso("e sem issue o roteiro não inventa o campo",
         "issue" not in roteiro_do_pedido_com_verificacao("x"))
    b.caso("o modo roteiro também manda a issue no corpo do disparo",
         "roteiro:$('modo').value,auditoria:$('auditoria').checked,"
         "issue:+$('issue').value||null" in PAGINA)
    with tempfile.TemporaryDirectory(prefix="mesa-issue-roteiro-") as tmp:
        base = Path(tmp)
        pasta_roteiros = base / "roteiros"
        pasta_roteiros.mkdir(parents=True)
        (pasta_roteiros / "nomeado.json").write_text(json.dumps({
            "etapas": [{"nome": "a", "tipo": "codigo", "comando": "true"}]}),
            encoding="utf-8")
        ponte = PonteParaOEncadeador(base, base / "ev", [pasta_roteiros])
        levado, prefixo_levado, erro = roteiro_e_prefixo_do_corpo(
            ponte, {"roteiro": "nomeado.json", "issue": 41})
        b.caso("o disparo por roteiro nomeado leva a issue da tela",
             erro is None and levado.get("issue") == 41)
        parado, prefixo_parado, _ = roteiro_e_prefixo_do_corpo(
            ponte, {"roteiro": "nomeado.json"})
        b.caso("sem issue na tela o roteiro do catálogo fica como está",
             "issue" not in parado)
        torto, _, _ = roteiro_e_prefixo_do_corpo(
            ponte, {"roteiro": "nomeado.json", "issue": 0})
        b.caso("issue inválida não entra no roteiro",
             "issue" not in torto)
        b.caso("disparo por roteiro do catálogo com issue nomeia o trabalho "
               "pela issue, não pelo nome do roteiro",
             nome_de_trabalho(prefixo_levado,
                              levado.get("issue")) == "issue-41")
        b.caso("e sem issue o nome continua saindo do roteiro escolhido",
             nome_de_trabalho(prefixo_parado,
                              parado.get("issue")).startswith("nomeado-"))
    b.caso("o botão de disparar fecha com execução no ar",
         "b.disabled=ocupada.length>0" in PAGINA
         and "'rodando','dormindo','aguardando-resposta'" in PAGINA)
    b.caso("e o motivo aparece no próprio botão",
         "a trava do alvo recusaria uma segunda execução" in PAGINA)
    b.caso("a página desenha a execução e o backlog",
         'function desenho' in PAGINA and 'id="quadro"' in PAGINA
         and 'id="issue"' in PAGINA and 'id="historico"' in PAGINA)
    b.caso("o desenho usa os tokens de cor que já existem",
         '.passo.segue' in PAGINA and '.passo.agora' in PAGINA)

    b.caso("com issue, o nome do trabalho sai dela — quem abre a pasta de "
           "evidências sabe a que trabalho ela pertence",
         nome_de_trabalho(PREFIXO_DO_PEDIDO_DO_PAINEL, 41) == "issue-41")
    b.caso("o número da issue manda, não o prefixo: o mesmo trabalho tem o "
           "mesmo endereço venha de onde vier",
         nome_de_trabalho("entrega", 41)
         == nome_de_trabalho(PREFIXO_DO_PEDIDO_DO_PAINEL, 41))
    b.caso("o nome derivado da issue passa na régua da evidência",
         recusa_do_nome_de_trabalho(
             nome_de_trabalho(PREFIXO_DO_PEDIDO_DO_PAINEL, 41)) is None)
    b.caso("sem issue, o nome continua o de hoje: prefixo e carimbo de hora",
         nome_de_trabalho("entrega").startswith("entrega-")
         and len(nome_de_trabalho("entrega")) == len("entrega-") + 15)
    b.caso("issue que não é número positivo não vira nome de trabalho",
         nome_de_trabalho("entrega", 0).startswith("entrega-")
         and nome_de_trabalho("entrega", True).startswith("entrega-")
         and nome_de_trabalho("entrega", "41").startswith("entrega-"))
    b.caso("nome de trabalho passa na régua da evidência",
         recusa_do_nome_de_trabalho(nome_de_trabalho()) is None)
    b.caso("nome com barra é recusado",
         recusa_do_nome_de_trabalho("a/b") is not None)
    b.caso("nome com maiúscula é recusado",
         recusa_do_nome_de_trabalho("Alfa") is not None)
    b.caso("nome vazio é recusado", recusa_do_nome_de_trabalho("") is not None)
    b.caso("nome de 65 é recusado",
         recusa_do_nome_de_trabalho("a" * 65) is not None)



def _sobre_a_auditoria_no_disparo(b) -> None:
    import tempfile as _tempfile
    b.caso("a mesa mostra onde se liga a auditoria",
           'id="auditoria"' in PAGINA and "auditar ao fim" in PAGINA)
    b.caso("a escolha viaja no corpo do disparo",
           "auditoria:$('auditoria').checked" in PAGINA)
    b.caso("a mesa reabre com a escolha da vez passada",
           "au.checked=!!d.auditoria" in PAGINA)

    b.caso("desligada, o roteiro não ganha o campo — quem não pediu não paga",
           CHAVE_DA_AUDITORIA
           not in roteiro_do_pedido_com_verificacao("x", auditoria=False))
    b.caso("ligada, o roteiro declara a auditoria",
           roteiro_do_pedido_com_verificacao(
               "x", auditoria=True).get(CHAVE_DA_AUDITORIA) is True)

    with _tempfile.TemporaryDirectory(prefix="mesa-auditoria-") as pasta:
        raiz = Path(pasta)
        (raiz / "nucleo").mkdir(parents=True, exist_ok=True)
        alvo = raiz / ARQUIVO_EXECUTOR
        alvo.write_text(json.dumps({"modo": "completo"}), encoding="utf-8")

        lembrar_a_auditoria(raiz, True)
        b.caso("a escolha fica gravada para a proxima execucao",
               json.loads(alvo.read_text(encoding="utf-8"))
               .get(CHAVE_DA_AUDITORIA) is True)

        lembrar_a_auditoria(raiz, False)
        b.caso("e desligar tambem fica gravado",
               json.loads(alvo.read_text(encoding="utf-8"))
               .get(CHAVE_DA_AUDITORIA) is False)

        antes = json.loads(alvo.read_text(encoding="utf-8"))
        lembrar_a_auditoria(raiz, False)
        b.caso("gravar o mesmo valor nao reescreve o arquivo",
               json.loads(alvo.read_text(encoding="utf-8")) == antes)

        vazia = raiz / "sem-configuracao"
        vazia.mkdir()
        lembrar_a_auditoria(vazia, True)
        b.caso("sem executor.json ele nao cria arquivo nenhum",
               not (vazia / ARQUIVO_EXECUTOR).exists())


def _sobre_o_roteiro_do_pedido(b) -> None:
    m = roteiro_do_pedido_com_verificacao("olhe o repositório")
    b.caso("prompt livre vira etapa de sessão", m["etapas"][0]["tipo"] == "sessao")
    b.caso("o prompt viaja inteiro", m["etapas"][0]["prompt"] == "olhe o repositório")
    b.caso("a verificação entra sempre", m["etapas"][1]["tipo"] == "verificacao")
    b.caso("a verificação depende da sessão",
         m["etapas"][1]["depende"] == ["pedido"])
    b.caso("o teto viaja", roteiro_do_pedido_com_verificacao("x", 7)["teto"] == 7)

    b.caso("o encadeador está no lugar esperado", ENCADEADOR.exists())
    b.caso("a página cita o disparo", 'id="b"' in PAGINA and "/disparar" in PAGINA)
    b.caso("a página não embute segredo",
         "token" not in PAGINA.lower() and "senha" not in PAGINA.lower())



def _sobre_o_servidor_e_a_porta(b) -> None:
    fonte = Path(__file__).read_text(encoding="utf-8")
    b.caso("o servidor atende mais de uma conexão ao mesmo tempo",
         "ThreadingHTTPServer" in fonte)
    b.caso("porta ocupada vira recado, não traceback",
         "EADDRINUSE" in fonte and "PAREI — a porta" in fonte)
    b.caso("porta livre não tem painel de controle atendendo",
         quem_responde_na_porta(1) == (None, None))
    b.caso("segundo F5 do MESMO repositório e MESMO alvo sai 0 — o que se "
         "queria já está no ar, e sair 0 apaga o popup do depurador",
         decidir_porta_ocupada(4000, "/raiz-a", "/alvo", "/raiz-a", "/alvo")[0]
         == 0)
    b.caso("e o recado dá o endereço em vez de reclamar",
         "http://127.0.0.1:4000" in decidir_porta_ocupada(
             4000, "/raiz-a", "/alvo", "/raiz-a", "/alvo")[1])
    b.caso("painel de controle de OUTRO repositório na porta sai 2",
         decidir_porta_ocupada(4000, "/raiz-a", "/a", "/outra", "/a")[0] == 2)
    b.caso("e o recado nomeia o outro repositório",
         "/outra" in decidir_porta_ocupada(4000, "/raiz-a", "/a", "/outra",
                                           "/a")[1])
    b.caso("mesmo repositório servindo OUTRO alvo não é 'nada a fazer' — "
         "quem pediu alvo novo não pode herdar o velho em silêncio",
         decidir_porta_ocupada(4000, "/raiz-a", "/novo", "/raiz-a", "/velho")[0]
         == 2)
    b.caso("e o recado nomeia o alvo velho",
         "/velho" in decidir_porta_ocupada(4000, "/raiz-a", "/novo", "/raiz-a",
                                           "/velho")[1])
    b.caso("porta ocupada por quem não é painel de controle sai 2",
         decidir_porta_ocupada(4000, "/raiz-a", "/a", None, None)[0] == 2)
    b.caso("a página mostra os três lugares",
         all(f'id="{i}"' in PAGINA for i in ("repositorio", "alvo", "evidencias")))
    b.caso("uma chamada por ciclo, não duas", "/estado?trabalho=" in PAGINA
         and "/andamento?trabalho=" not in PAGINA)
    b.caso("só repinta quando o estado muda", "assinatura" in PAGINA)
    b.caso("a fita de evidências é a peça central", 'class="fita"' in PAGINA
         and "fita de evidências" in PAGINA)
    b.caso("todo texto de fora passa por escape", "function esc(" in PAGINA)
    b.caso("respeita quem pediu menos movimento",
         "prefers-reduced-motion" in PAGINA)
    b.caso("foco de teclado é visível", ":focus-visible" in PAGINA)
    b.caso("a paleta é uma só, a escura do desenho aprovado — nenhum resto "
         "do tema claro de antes ficou na página",
         all(c in PAGINA for c in CORES_DA_PALETA_APROVADA)
         and "prefers-color-scheme" not in PAGINA)
    b.caso("nenhum caminho absoluto de máquina entra no HTML estático — "
         "nem a raiz deste repositório, nem os lugares comuns de um "
         "disco pessoal",
         str(RAIZ) not in PAGINA
         and not any(p in PAGINA for p in ("/home/", "/Users/", "C:\\")))
    b.caso("a versão sai do montar.py, e é a mesma que o --versao imprime",
           versao_impressa_pelo_instalador() ==
           versao_da_camada_declarada_no_topo_do_montar())
    b.caso("a página tem onde mostrar a versão", 'id="versao"' in PAGINA)
    b.caso("o título da aba grita a espera, para quem trocou de aba ficar "
         "sabendo que a execução travou esperando resposta",
         "aguardando-aprovacao':'❓ ESPERANDO VOCÊ" in PAGINA)
    b.caso("o título distingue os quatro estados",
         all(e in PAGINA for e in ("parada", "completa", "em-curso")))



def _sobre_a_pergunta_e_a_vivacidade(b) -> None:
    b.caso("a pergunta da etapa aparece na tela", "e.pergunta" in PAGINA)
    b.caso("a pergunta tem caixa própria, separada da próxima ação — é o "
           "herói do esperando-você",
         'class="heroi"' in PAGINA and ".heroi-pergunta{" in PAGINA)

    class ProcFalso:
        def __init__(self, esta_vivo, pid=1):
            self._esta_vivo, self.pid, self.returncode = esta_vivo, pid, 0

        def poll(self):
            return None if self._esta_vivo else 0

    b.caso("sem processo, a situação é desconhecida — não 'morto'",
         vivacidade(None, None)["situacao"] == "desconhecida")
    b.caso("processo encerrado é dito encerrado",
         vivacidade(ProcFalso(False), time.time())["situacao"] == "encerrado")
    vv = vivacidade(ProcFalso(True), time.time() - 120)
    b.caso("processo vivo é dito trabalhando", vv["situacao"] == "trabalhando")
    b.caso("mostra quanto tempo já corre", vv["decorrido_s"] >= 120)
    b.caso("e quanto falta para o teto que mata sozinho",
         vv["resta_s"] == TETO_SESSAO_S_ESPELHO_DO_ENCADEADOR - vv["decorrido_s"])
    b.caso("o teto do painel de controle espelha o do encadeador",
         f"TEMPO_SESSAO = {TETO_SESSAO_S_ESPELHO_DO_ENCADEADOR}" in
         (ENCADEADOR.read_text(encoding="utf-8") if ENCADEADOR.exists() else
          f"TEMPO_SESSAO = {TETO_SESSAO_S_ESPELHO_DO_ENCADEADOR}"))
    b.caso("este processo enxerga os próprios descendentes ou diz que não mede",
         isinstance(descendentes_lendo_proc(os.getpid()), list))
    b.caso("a página mostra a vivacidade", "vivo(d.vivacidade)" in PAGINA)




def _sobre_a_mesa_e_os_turnos(b) -> None:
    with tempfile.TemporaryDirectory() as t:
        base = Path(t)
        (base / "evidencias" / "vinda-de-execucao").mkdir(parents=True)
        (base / "evidencias" / "trilha-de-gancho").mkdir(parents=True)
        (base / "evidencias" / "vinda-de-execucao.roteiro.json").write_text("{}")
        (base / "roteiros").mkdir()
        (base / "roteiros" / "boa.json").write_text(
            json.dumps(roteiro_do_pedido_com_verificacao("oi")), encoding="utf-8")
        (base / "roteiros" / "quebrada.json").write_text("{isso não é json",
                                                         encoding="utf-8")
        (base / "roteiros" / "sem-etapas.json").write_text('{"teto":3}',
                                                           encoding="utf-8")
        (base / "oficiais").mkdir()
        (base / "oficiais" / "boa.json").write_text(
            json.dumps(roteiro_do_pedido_com_verificacao("sou a oficial")),
            encoding="utf-8")
        (base / "oficiais" / "so-daqui.json").write_text(
            json.dumps(roteiro_do_pedido_com_verificacao("x")), encoding="utf-8")
        ponte = PonteParaOEncadeador(base, base / "evidencias",
                                     [base / "oficiais", base / "roteiros"])

        marcas = {t["nome"]: t["execucao"] for t in ponte.trabalhos()}
        b.caso("trabalho com roteiro é execução", marcas["vinda-de-execucao"])
        b.caso("trilha de gancho NÃO é execução",
             marcas["trilha-de-gancho"] is False)

        b.caso("o catálogo junta as duas pastas, e só o que é roteiro — a "
             "quebrada e a sem-etapas ficam de fora",
             ponte.catalogo() == sorted(["boa.json", "so-daqui.json"]))

        (base / "oficiais" / "boa.md").write_text(
            "# A boa\n\nEla faz o que o dono precisa.\n", encoding="utf-8")
        descricoes = {r["nome"]: r["descricao"]
                      for r in ponte.catalogo_com_descricao()}
        b.caso("a descrição vem do .md irmão, inteira",
             "Ela faz o que o dono precisa." in descricoes["boa.json"])
        b.caso("roteiro sem .md irmão nem campo confessa que não tem descrição",
             descricoes["so-daqui.json"] == SEM_DESCRICAO)
        (base / "roteiros" / "com-campo.json").write_text(
            json.dumps(dict(roteiro_do_pedido_com_verificacao("x"),
                            descricao="a descrição mora no roteiro")),
            encoding="utf-8")
        com_campo = {r["nome"]: r["descricao"]
                     for r in ponte.catalogo_com_descricao()}
        b.caso("sem .md irmão, o campo descricao do roteiro serve",
             com_campo["com-campo.json"] == "a descrição mora no roteiro")
        b.caso("nome repetido fica com a pasta oficial",
             ponte.ler_roteiro_do_catalogo("boa.json")[0]["etapas"][0]["prompt"]
             == "sou a oficial")
        b.caso("pasta de roteiros que não existe não derruba",
             PonteParaOEncadeador(base, base / "evidencias",
                                  [base / "nao-existe"]).catalogo() == [])
        b.caso("nada rodando, nada ocupado", ponte.ocupado() is None)
        b.caso("roteiro bom é lido",
             ponte.ler_roteiro_do_catalogo("boa.json")[0] is not None)
        b.caso("roteiro ilegível vira erro, não exceção",
             ponte.ler_roteiro_do_catalogo("quebrada.json")[1] is not None)
        b.caso("roteiro sem etapas é recusado",
             ponte.ler_roteiro_do_catalogo("sem-etapas.json")[1] is not None)
        b.caso("nome fora do catálogo é recusado",
             ponte.ler_roteiro_do_catalogo("../../etc/passwd")[1] is not None)
        b.caso("caminho absoluto é recusado",
             ponte.ler_roteiro_do_catalogo("/etc/passwd")[1] is not None)

        (base / "roteiros" / "nao-e-roteiro.json").write_text(
            '{"regras": [{"id": 1}]}', encoding="utf-8")
        b.caso("json sem etapas fica fora do catálogo — a proposta de regra que "
             "a síntese escreve não é execução",
             "nao-e-roteiro.json" not in ponte.catalogo())
        b.caso("json quebrado também fica fora",
             "quebrada.json" not in ponte.catalogo())
        b.caso("roteiro de verdade continua no catálogo",
             "boa.json" in ponte.catalogo())

        pid_que_nao_existe = 2 ** 22
        ponte.gravar_trava(os.getpid(), "trabalho-vivo")
        b.caso("trava de dono vivo segura, mesmo sendo de OUTRO processo",
             ponte.ocupado() is not None)
        b.caso("a trava diz de quem é", "pid" in (ponte.ocupado() or ""))
        ponte.gravar_trava(pid_que_nao_existe, "trabalho-fantasma")
        b.caso("trava de dono morto não segura ninguém", ponte.ocupado() is None)
        ponte._arquivo_de_trava_deste_alvo().write_text("isso não é json",
                                                        encoding="utf-8")
        b.caso("trava ilegível não trava o repositório", ponte.ocupado() is None)
        ponte._arquivo_de_trava_deste_alvo().unlink()
        b.caso("alvos diferentes, travas diferentes",
             ponte._arquivo_de_trava_deste_alvo()
             != PonteParaOEncadeador(base / "outro", base / "evidencias", [])
             ._arquivo_de_trava_deste_alvo())

    b.caso("o pedido do painel de controle declara os turnos, em vez de herdar "
         "o padrão do motor, que matava o pedido no teto",
         roteiro_do_pedido_com_verificacao("x")["etapas"][0]["max-turnos"] == 24)
    b.caso("e quem dispara pode escolher",
         roteiro_do_pedido_com_verificacao("x", 3, 60)["etapas"][0]["max-turnos"]
         == 60)
    b.caso("turnos aparece na tela, não só ciclos",
         'id="turnos"' in PAGINA and "turnos:+$('turnos').value" in PAGINA)



def _sobre_a_proxima_acao(b) -> None:
    rodando = calar_o_convite_a_disparar_o_que_ja_esta_no_ar({
        "processo": "rodando", "estado": "em-curso",
        "proxima_acao": "nada rodou ainda — rode: python ... executar ..."})
    b.caso("processo vivo: a próxima ação para de mandar executar",
         "executar" not in rodando["proxima_acao"])
    b.caso("e diz que pasta vazia no começo é o esperado",
         "evidência quando termina" in rodando["proxima_acao"])
    encerrado = calar_o_convite_a_disparar_o_que_ja_esta_no_ar({
        "processo": "encerrado", "estado": "em-curso",
        "proxima_acao": "nada rodou ainda — rode: ... executar ..."})
    b.caso("processo morto: o convite a executar FICA — ali ele é verdade",
         "executar" in encerrado["proxima_acao"])
    completa = calar_o_convite_a_disparar_o_que_ja_esta_no_ar({
        "processo": "rodando", "estado": "completa",
        "proxima_acao": "leia as evidências"})
    b.caso("execução completa não tem a mensagem trocada",
         completa["proxima_acao"] == "leia as evidências")



def _sobre_o_que_a_rodada_1_consertou(b) -> None:
    de_fora = calar_o_convite_a_disparar_o_que_ja_esta_no_ar({
        "processo": PROCESSO_DESCONHECIDO, "estado": ESTADO_EM_CURSO,
        "gravado": {"situacao": SITUACAO_GRAVADA_RODANDO},
        "proxima_acao": "nada rodou ainda — rode: python ... executar ..."})
    b.caso("execução aberta fora da mesa também cala o convite a executar — "
           "o convite aparecia embaixo de um cabeçalho dizendo TRABALHANDO",
           "executar" not in de_fora["proxima_acao"])

    with tempfile.TemporaryDirectory(prefix="mesa-r1-") as tmp:
        pasta = Path(tmp)
        (pasta / "01-levantar-c1.log").write_text("terminei", encoding="utf-8")
        (pasta / "01-levantar-c1.json").write_text("{}", encoding="utf-8")
        b.caso("etapa com evidência ao lado não é etapa em curso",
               etapa_que_escreve_sem_ter_terminado(pasta) is None)
        (pasta / "02-consertar-c1.log").write_text("estou escrevendo agora",
                                                   encoding="utf-8")
        viva = etapa_que_escreve_sem_ter_terminado(pasta) or {}
        b.caso("a etapa que escreve sem ter terminado é achada pelo .log sem "
               "evidência ao lado", viva.get("nome") == "consertar")
        b.caso("e vem com ordem, ciclo e o fim do que ela escreveu — o dado "
               "estava no disco, faltava alguém ler",
               (viva.get("ordem"), viva.get("ciclo")) == (2, 1)
               and viva.get("cauda", "").endswith("agora"))
        acentuado = pasta / "acentuado.log"
        acentuado.write_bytes(("é" * 40).encode("utf-8"))
        cortada = cauda_do_arquivo(acentuado, 5)
        b.caso("a cauda não nasce com caractere de substituição quando o "
               "corte cai no meio de um acento",
               "�" not in cortada and cortada == "é" * 2)

    class ProcFalso:
        def __init__(self):
            self.pid, self.returncode = os.getpid(), 0

        def poll(self):
            return None

    sem_relogio = vivacidade(ProcFalso(), None)
    b.caso("medida que não houve não vira chave: o '?' do rodapé era None "
           "viajando até a tela e virando texto",
           "decorrido_s" not in sem_relogio and "resta_s" not in sem_relogio)
    dormindo_sem_prazo = vivacidade_do_que_o_motor_gravou({
        "situacao": "dormindo", "ate": None, "porque": "limite de uso"})
    b.caso("o que o motor gravou vazio também não viaja",
           "ate" not in dormindo_sem_prazo
           and dormindo_sem_prazo["porque"] == "limite de uso")
    b.caso("e o carimbo da última escrita chega até o rodapé da mesa",
           vivacidade_do_que_o_motor_gravou(
               {"situacao": "parada", "escrita_em": "2026-08-22T09:14:07-03:00"}
           ).get("escrita_em") == "2026-08-22T09:14:07-03:00")

    with tempfile.TemporaryDirectory(prefix="mesa-r1b-") as tmp:
        evidencias = Path(tmp) / "evidencias"
        (evidencias / "simulacao").mkdir(parents=True)
        (evidencias / "hist-29").mkdir()
        (evidencias / "hist-29" / ARQUIVO_ESTADO).write_text(
            json.dumps({"situacao": SITUACAO_GRAVADA_RODANDO}),
            encoding="utf-8")
        os.utime(evidencias / "simulacao", (2_000_000_000, 2_000_000_000))
        os.utime(evidencias / "hist-29", (1_000_000_000, 1_000_000_000))
        ponte = PonteParaOEncadeador(Path(tmp), evidencias, [])
        listados = ponte.trabalhos()
        b.caso("execução vem antes de trilha avulsa, ainda que o nome dela "
               "perca na ordem alfabética invertida",
               [t["nome"] for t in listados] == ["hist-29", "simulacao"])

    b.caso("com duas execuções, a mesa abre na que está no ar — não na mais "
           "recente",
           trabalho_que_a_mesa_abre([
               {"nome": "ontem-completa", "execucao": True,
                "situacao": "completa"},
               {"nome": "agora-no-ar", "execucao": True,
                "situacao": SITUACAO_GRAVADA_RODANDO}]) == "agora-no-ar")
    b.caso("sem execução nenhuma, a mesa não escolhe trilha avulsa",
           trabalho_que_a_mesa_abre(
               [{"nome": "trilha", "execucao": False}]) is None)


def _sobre_o_encadeador_de_verdade(b) -> None:
    if ENCADEADOR.exists() and shutil.which("git"):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "m.json"
            p.write_text(json.dumps(roteiro_do_pedido_com_verificacao("oi")),
                         encoding="utf-8")
            r = subprocess.run(
                [sys.executable, str(ENCADEADOR), "ensaio", "--roteiro", str(p),
                 "--trabalho", "teste-painel", "--dir", tmp, "--cwd", str(RAIZ)],
                capture_output=True, text=True, timeout=60)
            b.caso("o encadeador aceita de verdade o roteiro que o painel de "
                 "controle escreve",
                 r.returncode == 0)
            b.caso("o ensaio lista as duas etapas",
                 "pedido" in r.stdout and "verifica" in r.stdout)



def _sobre_a_maquina(b) -> None:
    b.caso("a máquina se reparte entre as abas Instrumentos e Prompts & "
           "skills, e as duas se enchem da rota /maquina",
           'id="instrumentos-corpo"' in trecho_da_aba("instrumentos")
           and 'id="prompts-corpo"' in trecho_da_aba("prompts")
           and "/maquina" in PAGINA)
    b.caso("a máquina só é lida quando alguém abre a aba — rede não se paga "
           "à toa",
           "maquinaLida" in PAGINA
           and "ABAS_QUE_LEEM_A_MAQUINA.includes(aba)&&!maquinaLida" in PAGINA)

    with tempfile.TemporaryDirectory() as pasta:
        raiz = Path(pasta)
        skill = raiz / PASTA_DAS_SKILLS_FONTE / "medir" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("---\nname: medir\ndescription: mede o que existe\n"
                         "---\n\n# medir\n", encoding="utf-8")
        achadas = skills_no_disco(raiz)
        b.caso("a skill do disco entra com nome e descrição",
               achadas["itens"] == [{"nome": "medir",
                                     "descricao": "mede o que existe"}])
        b.caso("e o painel de controle diz de qual pasta leu",
               achadas["de_onde"] == PASTA_DAS_SKILLS_FONTE)
    with tempfile.TemporaryDirectory() as pasta:
        vazia = skills_no_disco(Path(pasta))
        b.caso("sem pasta de skills o resultado é NÃO MEDIDO, nunca zero",
               vazia["itens"] == [] and vazia["recado"] is not None)

    b.caso("servidor conectado é lido com nome, alvo e estado",
           linha_de_servidor_mcp("agenda: https://x/mcp - ✔ Connected")
           == {"nome": "agenda", "alvo": "https://x/mcp",
               "estado": "✔ Connected", "de_pe": True})
    b.caso("servidor que pede autenticação não passa por de pé",
           linha_de_servidor_mcp(
               "desenho: https://y/mcp (HTTP) - ! Needs authentication"
           )["de_pe"] is False)
    b.caso("a linha de cabeçalho da listagem não vira servidor",
           linha_de_servidor_mcp("Checking MCP server health…") is None)
    b.caso("linha sem estado não vira servidor de mentira",
           linha_de_servidor_mcp("") is None)

    lista = ("relatorio-diario.timer loaded active waiting Dispara a rotina\n"
             "outra.service loaded active running Um serviço qualquer\n")
    achadas = unidades_de_rotina(lista)
    b.caso("só o que é rotina agendada entra na lista",
           [u["unidade"] for u in achadas] == ["relatorio-diario.timer"])
    b.caso("e a descrição do agendador vem junto",
           achadas[0]["descricao"] == "Dispara a rotina")

    with tempfile.TemporaryDirectory() as pasta:
        raiz = Path(pasta)
        minha = raiz / "rotinas" / "executar.sh"
        minha.parent.mkdir(parents=True)
        minha.write_text("", encoding="utf-8")
        b.caso("rotina que executa deste workspace é minha",
               e_rotina_deste_workspace(str(minha), raiz) is True)
        b.caso("rotina do sistema operacional não entra na lista",
               e_rotina_deste_workspace("/usr/bin/apt-get", raiz) is False)
        b.caso("rotina sem comando legível não vira minha por engano",
               e_rotina_deste_workspace("", raiz) is False)
        b.caso("comando sem caminho não vira meu pela pasta em que eu rodo",
               e_rotina_deste_workspace("find", raiz) is False)
    b.caso("a tela confessa quantos agendamentos ficaram de fora",
           "de_fora" in PAGINA and "sistema operacional" in PAGINA)
    b.caso("no Windows a confissão diz o comando que fecharia a lacuna",
           "schtasks" in RECADO_AGENDADOR_DO_WINDOWS
           and "não medido" in RECADO_AGENDADOR_DO_WINDOWS)

    with tempfile.TemporaryDirectory() as pasta:
        raiz = Path(pasta)
        meu = {"Name": "vetores", "Status": "running(2)",
               "ConfigFiles": str(raiz / "modulos" / "docker-compose.yml")}
        b.caso("projeto de containers do workspace rodando é lido como de pé",
               projeto_de_containers(meu, raiz)
               == {"nome": "vetores", "estado": "running(2)", "de_pe": True})
        b.caso("projeto de containers parado não passa por de pé",
               projeto_de_containers(
                   {**meu, "Status": "exited(4)"}, raiz)["de_pe"] is False)
        b.caso("projeto de containers de fora do workspace não entra na lista",
               projeto_de_containers(
                   {**meu, "ConfigFiles": "/srv/fora/compose.yml"}, raiz)
               is None)
        b.caso("projeto de containers sem nome não vira medida de mentira",
               projeto_de_containers(
                   {"Name": "", "ConfigFiles": str(raiz / "c.yml")}, raiz)
               is None)
    b.caso("a faixa da mesa mostra os containers com o estado de cada um",
           'id="containers"' in PAGINA and "d.containers" in PAGINA)
    b.caso("sem docker o resultado é NÃO MEDIDO, nunca zero",
           "não medido" in RECADO_SEM_DOCKER)

    b.caso("o guia fala de prova, de parada e de pergunta",
           {"a prova", "quando ela para"} <= {t for t, _ in PASSOS_DO_GUIA})
    b.caso("a tela separa não medido de medido e vazio",
           "naomedido" in PAGINA and "e isto foi medido" in PAGINA)


def _sobre_o_botao_de_aprovar(b) -> None:
    esperando = {"estado": "aguardando-aprovacao",
                 "etapas": [{"nome": "entrega", "pergunta": "Aprova?"}]}
    rodando = {"estado": "em-curso",
               "etapas": [{"nome": "trabalha", "pergunta": None}]}
    completa = {"estado": "completa",
                "etapas": [{"nome": "entrega", "pergunta": None}]}

    b.caso("o botão de aprovar aparece quando a execução está esperando "
           "aprovação",
         a_execucao_espera_aprovacao(esperando))
    b.caso("não aparece em execução rodando",
         not a_execucao_espera_aprovacao(rodando))
    b.caso("não aparece em execução completa",
         not a_execucao_espera_aprovacao(completa))
    b.caso("pergunta velha sem o estado de espera não ressuscita o botão",
         not a_execucao_espera_aprovacao(
             {"estado": "completa",
              "etapas": [{"nome": "entrega", "pergunta": "Aprova?"}]}))
    b.caso("a tela só desenha o herói pelo que o servidor mediu, em vez de "
           "reinferir o estado",
         "if(!d.espera_aprovacao)return ''" in PAGINA)
    b.caso("não nasce botão para o arquivo entrega.ok: a via sem autor "
           "aparece só em texto",
         "entrega.ok" not in PAGINA
         and "não ganha botão porque não tem autor" in PAGINA)
    b.caso("o botão de aprovar usa a rota POST /responder, que já existe",
         "fetch('/responder',{method:'POST'" in PAGINA
         and '"/responder"' in Path(__file__).read_text(encoding="utf-8"))
    b.caso("a marca da devolução é a mesma nas duas pontas do protocolo",
         not ENCADEADOR.is_file()
         or MARCA_DA_DEVOLUCAO in ENCADEADOR.read_text(encoding="utf-8"))
    b.caso("o devolver viaja na chamada e os botões dormem durante o voo",
         "devolver:!!devolver" in PAGINA
         and "botoes.forEach(b=>b.disabled=true)" in PAGINA)
    b.caso("o registro do comentário é pintado na tela, não jogado fora",
         "d.registro" in PAGINA and "devolvido" in PAGINA)
    with tempfile.TemporaryDirectory(prefix="mesa-aprovar-") as tmp:
        base = Path(tmp)
        ponte = PonteParaOEncadeador(base, base / "ev", [])
        b.caso("trabalho sem issue gravada não chama a rede: a resposta "
               "entra só na retomada, e a mesa diz que ficou sem autor",
             ponte._comentar_a_resposta_na_issue("t-x", "Aprovado.")
             == (False, RECADO_RESPOSTA_SO_NA_RETOMADA))
        b.caso("devolução que não registra em lugar nenhum é erro, não "
               "silêncio",
             RECADO_RESPOSTA_SO_NA_RETOMADA in ponte.responder(
                 "t-x", "não aprovo", devolver=True).get("erro", ""))
        (base / "ev").mkdir(exist_ok=True)
        (base / "ev" / "t-x.roteiro.json").write_text("{}", encoding="utf-8")
        ponte.em_voo.add("t-x")
        b.caso("segundo clique com retomada em voo é barrado — no responder "
               "e no retomar",
             ponte.responder("t-x", "sim")
             == {"erro": ERRO_RESPONDER_COM_EXECUCAO_VIVA}
             and ponte.retomar_em_um_clique("t-x")
             == {"erro": ERRO_RESPONDER_COM_EXECUCAO_VIVA})
        ponte.em_voo.discard("t-x")
        feito = ponte.retomar_em_um_clique("t-x")
        vivo = ponte.rodando.get("t-x")
        b.caso("depois do disparo a reserva está solta e o processo "
               "rastreado",
             feito.get("retomada") is True and "t-x" not in ponte.em_voo
             and vivo is not None)
        if vivo:
            vivo.wait(timeout=15)


def _sobre_a_mesa_pelo_desenho_aprovado(b) -> None:
    b.caso("a faixa de estado fixa existe e responde 'preciso agir?'",
         'id="faixa"' in PAGINA and "preciso agir" in PAGINA
         and 'id="acao"' in PAGINA)
    b.caso("a mesa tem duas colunas: a fila e o palco",
         'id="fila"' in PAGINA and 'id="palco"' in PAGINA)
    b.caso("o backlog executa em um clique — o botão da linha executa, "
           "não preenche formulário",
         "executarIssue(" in PAGINA and "$('p').focus()" not in PAGINA)
    b.caso("rótulo de roteiro é a primeira linha da descrição, nunca o "
           "nome do arquivo",
         titulo_do_roteiro("entrega.json",
                           "Abre branch, trabalha e verifica.\ndetalhe")
         == "Abre branch, trabalha e verifica."
         and titulo_do_roteiro("revisar-a-camada.json", "")
         == "revisar a camada")
    b.caso("o vocabulário fechou: o nome velho não aparece no front",
         ("est" + "eira") not in PAGINA.lower())
    b.caso("um sentido por palavra: quem começa execução é Executar — "
           "'disparar' saiu das palavras visíveis da tela",
         "disparar" not in PAGINA.lower().replace("/disparar", ""))
    b.caso("o estado esperando-você tem pergunta como herói, aprovar, "
           "devolver e o placar ao lado",
         "heroi" in PAGINA and 'id="aprovar"' in PAGINA
         and 'id="devolver"' in PAGINA and 'id="placar"' in PAGINA)
    b.caso("o placar lê a saída do verificar: abertos NOMEADOS, não somados",
         placar_dos_criterios(4,
             "ACUSA critério da issue sem resposta nas evidências: "
             "'a paginação devolve a segunda página' — nada no provado, "
             "no suposto ou nas faltas cita paginação\n"
             "\n1 de 8 critérios abertos sem resposta.")
         == {"total": 8,
             "abertos": ["a paginação devolve a segunda página"],
             "avisos": []})
    b.caso("e a saída limpa vira placar cheio",
         placar_dos_criterios(0, "todos os 8 critérios abertos da issue "
                                 "têm resposta em 12 evidências.")
         == {"total": 8, "abertos": [], "avisos": []})
    b.caso("issue sem critério aberto não vira placar zero mentiroso",
         placar_dos_criterios(0, "a issue não traz critério aberto — nada "
                                 "a verificar.")["total"] == 0)
    comando = comando_de_retomada(Path("rot.json"), "t-x", Path("/ev"),
                                  Path("/alvo"), "aprovo")
    b.caso("a resposta do dono monta a retomada exata do motor",
         "--retomar" in comando
         and comando[comando.index("--resposta") + 1] == "aprovo"
         and comando[comando.index("--trabalho") + 1] == "t-x")
    with tempfile.TemporaryDirectory(prefix="mesa-responder-") as tmp:
        base = Path(tmp)
        ponte = PonteParaOEncadeador(base, base / "ev", [])
        b.caso("responder sem texto é recusado antes de tocar o motor",
             "erro" in ponte.responder("t-x", "   "))
        recusa = ponte.responder("t-x", "aprovo")
        b.caso("responder sem roteiro conhecido devolve recado claro",
             "erro" in recusa and "roteiro" in recusa["erro"])
    b.caso("a cauda traduzida troca o jsonl cru por linhas legíveis",
         "Bash" in resumo_da_cauda(
             '{"type":"assistant","message":{"content":'
             '[{"type":"tool_use","name":"Bash"}]}}')
         and resumo_da_cauda("linha solta") == "linha solta"
         and "thinking_tokens" not in resumo_da_cauda(
             '{"type":"system","subtype":"thinking_tokens","tokens":9}'))
    b.caso("fragmento de jsonl serrado pelo corte em bytes não passa por "
           "linha legível",
         resumo_da_cauda('X7mZ{"input_tokens":2,"cache_read":1}') == "")
    b.caso("a fila nunca cai num avulso por conta própria",
         "atual=d.padrao||null" in PAGINA)
    b.caso("a primeira pintura com execução no ar não pisca o convite — "
           "o ciclo rebusca uma vez quando o padrão acabou de chegar",
         "return ciclo(true)" in PAGINA)
    b.caso("a referência saiu do lugar nobre: coordenadas moram na aba "
           "Configurações, a última da barra",
         PAGINA.index('id="repositorio"') > PAGINA.index('id="palco"')
         and 'id="repositorio"' in trecho_da_aba("nucleo"))
    b.caso("tela estreita tem gaveta e botão principal de 48px",
         "max-width:700px" in PAGINA and "min-height:48px" in PAGINA)
    b.caso("a mesa fala com o motor por /responder e /criterios",
         "/responder" in PAGINA and "/criterios" in PAGINA)


def _sobre_a_triagem_da_fila(b) -> None:
    b.caso("o primeiro paint diz medindo — nunca veste ocioso antes da "
           "primeira medida",
           'id="farol-txt">medindo…<' in PAGINA
           and 'id="farol-txt">ocioso<' not in PAGINA)
    b.caso("a fila conhece as três recusas: caixa não se executa, execução "
           "viva fecha o botão, outro projeto vai separado com etiqueta",
           "caixa — não se executa" in PAGINA and "em execução" in PAGINA
           and "outros projetos" in PAGINA)
    b.caso("os números das caixas saem da configuração, dígito ou texto, "
           "e o comentário fica de fora",
           numeros_das_caixas({"caixas": {"defeitos": "40",
                                          "melhorias": 40,
                                          "comentario": "x"}}) == [40]
           and numeros_das_caixas({}) == [])
    b.caso("os projetos declarados são só os que têm corpo de dicionário",
           nomes_dos_projetos({"projetos": {"a": {}, "comentario": "x",
                                            "b": {"y": 1}}}) == ["a", "b"])
    b.caso("o projeto do alvo é o nome da pasta quando declarado, e nada "
           "quando não é",
           projeto_do_alvo({"projetos": {"meu-repo": {}}},
                           "/qualquer/meu-repo") == "meu-repo"
           and projeto_do_alvo({"projetos": {"outro": {}}},
                               "/qualquer/meu-repo") is None)
    b.caso("a fila lê as etiquetas das issues, que o quadro agora carrega",
           '"number,title,labels"' in Path(__file__).read_text(
               encoding="utf-8"))


def _sobre_a_conta_e_a_linha_do_tempo(b) -> None:
    b.caso("conta e linha do tempo são rotas servidas, e o log da etapa "
           "também",
           {"/linha-do-tempo", "/log-da-etapa"}
           <= rotas_que_o_servidor_atende())
    b.caso("a tela carrega a soma do dia, a coluna de custo e as raias",
           'id="conta-dia"' in PAGINA and "tempo-raias" in PAGINA
           and "pintaTempo" in PAGINA and "ultimaConta" in PAGINA)
    b.caso("o padrão do log da etapa barra fuga de caminho e extensão "
           "estranha",
           not PADRAO_DO_LOG_DA_ETAPA.match("../fuga.log")
           and not PADRAO_DO_LOG_DA_ETAPA.match("01-x-c1.txt")
           and PADRAO_DO_LOG_DA_ETAPA.match("01-abrir-branch-c1.log"))
    with tempfile.TemporaryDirectory() as raiz:
        base = Path(raiz)
        b.caso("sem pasta de evidências a conta é zero, não erro",
               conta_das_execucoes(base / "nao-existe")
               == {"por_trabalho": {}, "dia_usd": 0.0})
        pasta = base / "t-conta"
        pasta.mkdir()
        (pasta / "01-uma-c1.log").write_text(
            '{"total_cost_usd":0.5,"num_turns":3}\n'
            '{"total_cost_usd":0.25,"num_turns":2}\n', encoding="utf-8")
        (pasta / "02-outra-c1.log").write_text(
            '{"total_cost_usd":1.0,"num_turns":1}\n', encoding="utf-8")
        achada = conta_das_execucoes(base)
        soma = achada["por_trabalho"]["t-conta"]
        b.caso("a conta soma custo e turnos dos registros do executor, "
               "com a quebra por etapa",
               soma["usd"] == 1.75 and soma["turnos"] == 6
               and soma["etapas"] == {"01-uma-c1": 0.75, "02-outra-c1": 1.0})
        b.caso("registro escrito agora conta na soma do dia",
               achada["dia_usd"] == 1.75)

        hoje = time.strftime("%Y-%m-%d")
        tempo = base / "t-tempo"
        tempo.mkdir()
        (tempo / "01-uma-c1.json").write_text(json.dumps(
            {"etapa": "uma", "quando": "2000-01-01T08:00:00-03:00",
             "ciclo": {"i": 1}}), encoding="utf-8")
        (tempo / "02-duas-c1.json").write_text(json.dumps(
            {"etapa": "duas", "quando": f"{hoje}T09:00:00-03:00",
             "ciclo": {"i": 1}}), encoding="utf-8")
        (tempo / "02-duas-c1.log").write_text("registro", encoding="utf-8")
        (tempo / "03-tres-c1.json").write_text(json.dumps(
            {"etapa": "tres", "quando": f"{hoje}T09:30:00-03:00",
             "ciclo": {"i": 2}}), encoding="utf-8")
        (tempo / "04-fora-do-molde-c1.json").write_text(
            "[]", encoding="utf-8")
        (tempo / "estado.json").write_text(json.dumps(
            {"situacao": "aguardando-resposta",
             "desde": f"{hoje}T09:31:00-03:00"}), encoding="utf-8")
        dia = linha_do_tempo_do_dia(base)
        raia = next(r for r in dia["raias"] if r["trabalho"] == "t-tempo")
        b.caso("etapa de outro dia fica fora da raia, mas empresta o início "
               "ao primeiro bloco de hoje",
               [x["etapa"] for x in raia["blocos"]] == ["duas", "tres"]
               and raia["blocos"][0]["inicio"]
               == "2000-01-01T08:00:00-03:00")
        b.caso("bloco com log ao lado sabe o nome dele; sem log, não inventa",
               raia["blocos"][0]["log"] == "02-duas-c1.log"
               and raia["blocos"][1]["log"] is None)
        b.caso("a intervenção pendente vira marca na raia",
               raia["marcas"] == [{"tipo": "aguardando-resposta",
                                   "quando": f"{hoje}T09:31:00-03:00"}])
        b.caso("evidência com JSON que não é objeto fica fora da raia em "
               "vez de derrubar a rota",
               [x["etapa"] for x in raia["blocos"]] == ["duas", "tres"])


def _sobre_o_retomar_e_a_poda(b) -> None:
    b.caso("retomar, podar e caixas são rotas que o servidor atende",
           {"/retomar", "/podar", "/caixas"} <= rotas_que_o_servidor_atende())
    b.caso("a linha parada da fila carrega o retomar em um clique",
           "retomar-1" in PAGINA and "x.situacao==='parada'" in PAGINA)
    b.caso("a poda pela mesa pede o motivo antes de chamar o instrumento",
           "podar-linha" in PAGINA and "motivo do fechamento" in PAGINA)
    b.caso("sem resposta o comando de retomada omite a bandeira; com "
           "resposta ele a leva",
           "--resposta" not in comando_de_retomada(
               Path("r.json"), "t", Path("ev"), Path("."), None)
           and "--resposta" in comando_de_retomada(
               Path("r.json"), "t", Path("ev"), Path("."), "sim"))
    linha_real = ("- **id-de-teste** `melhoria` — o texto da linha, com "
                  "detalhe · visto em 2026-08-30")
    fora_do_formato = "- texto solto que não é linha de caixa"
    achadas = linhas_do_corpo_da_caixa(
        f"cabeçalho\n{linha_real}\n{fora_do_formato}\n")
    b.caso("o leitor de caixa acha a linha no formato do instrumento e "
           "ignora o resto",
           achadas == [{"id": "id-de-teste", "tipo": "melhoria",
                        "texto": "o texto da linha, com detalhe",
                        "visto": "2026-08-30"}])
    b.caso("linha sem o visto-em ainda é linha",
           linhas_do_corpo_da_caixa("- **x** `defeito` — só o texto")
           == [{"id": "x", "tipo": "defeito", "texto": "só o texto",
                "visto": None}])
    with tempfile.TemporaryDirectory() as raiz:
        base = Path(raiz)
        ponte = PonteParaOEncadeador(base, base / "ev", [])
        b.caso("poda sem identidade ou sem motivo é recusada antes de "
               "tocar o instrumento",
               "erro" in ponte.podar("", "motivo")
               and "erro" in ponte.podar("id", " "))
        b.caso("retomar em um clique recusa trabalho sem roteiro para "
               "retomar",
               ponte.retomar_em_um_clique("t-sem-nada")
               == {"erro": ERRO_SEM_ROTEIRO_PARA_RETOMAR})
        b.caso("retomar em um clique recusa nome de trabalho fora da regra",
               "erro" in ponte.retomar_em_um_clique("../fuga"))


def _sobre_o_panico_e_a_so_leitura(b) -> None:
    b.caso("o pânico é global — botão na barra das abas, em dois passos",
           'id="panico"' in PAGINA and "confirmar a parada?" in PAGINA
           and "panicoArmado" in PAGINA)
    b.caso("o pânico é rota que o servidor atende",
           "/panico" in rotas_que_o_servidor_atende())
    b.caso("o selo de só-leitura mora na barra, visível em toda aba",
           'id="selo-leitura"' in PAGINA and "só-leitura" in PAGINA)
    fonte = Path(__file__).read_text(encoding="utf-8")
    b.caso("a recusa do só-leitura é do servidor, e só o desligar passa",
           'caminho != "/desligar"' in fonte and "ERRO_SO_LEITURA" in fonte)
    b.caso("um processo vivo é vivo, um pid impossível não é",
           _processo_vivo(os.getpid()) and not _processo_vivo(2 ** 22 + 1)
           and not _processo_vivo(None))
    ha_proc_para_verificar = Path("/proc").exists()
    b.caso("o pid desta sessão não passa pela identidade do encadeador — "
           "onde há /proc para verificar",
           not ha_proc_para_verificar
           or not _pid_ainda_e_do_encadeador(os.getpid()))
    with tempfile.TemporaryDirectory() as raiz:
        base = Path(raiz)
        ponte = PonteParaOEncadeador(base, base / "ev", [])
        b.caso("pânico sem execução viva devolve relatório vazio, com o "
               "prazo declarado",
               ponte.panico() == {"parados": [], "prazo_s": PRAZO_DO_PANICO_S})
        pasta = base / "ev" / "t-panico"
        pasta.mkdir(parents=True)
        alheio = subprocess.run(
            ["sh", "-c", "sleep 60 >/dev/null 2>&1 & echo $!"],
            capture_output=True, text=True)
        pid_alheio = int(alheio.stdout.strip())
        (pasta / "estado.json").write_text(json.dumps(
            {"situacao": "rodando", "pid": pid_alheio}), encoding="utf-8")
        b.caso("pid que o disco aponta mas hoje é de processo alheio não "
               "entra no alvo do pânico — onde há /proc para verificar",
               not ha_proc_para_verificar
               or ponte.panico()["parados"] == [])
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.kill(pid_alheio, signal.SIGKILL)
        berco = subprocess.run(
            ["sh", "-c",
             "sh -c 'sleep 60; :' encadeador.py-de-mentira "
             ">/dev/null 2>&1 & echo $!"],
            capture_output=True, text=True)
        pid_orfao = int(berco.stdout.strip())
        (pasta / "estado.json").write_text(json.dumps(
            {"situacao": "rodando", "pid": pid_orfao}),
            encoding="utf-8")
        relatorio = ponte.panico()
        b.caso("pânico manda o sinal educado e a execução de mentira para "
               "limpa, com o trabalho nomeado no relatório",
               relatorio["parados"] == [{"trabalho": "t-panico",
                                         "pid": pid_orfao,
                                         "parada": "limpa"}])
        b.caso("estado completa não entra no alvo do pânico",
               (pasta / "estado.json").write_text(json.dumps(
                   {"situacao": "completa", "pid": os.getpid()}),
                   encoding="utf-8") and ponte.panico()["parados"] == [])


def _sobre_o_sino_o_mudo_e_o_desligar(b) -> None:
    b.caso("o cabeçalho carrega o sino do esperando-você e o botão de mudo",
           'id="sino"' in PAGINA and 'id="mudo"' in PAGINA
           and "esperando você" in PAGINA)
    b.caso("o sino conta os três estados que param em você",
           "'parada','aguardando-resposta','aguardando-aprovacao'" in PAGINA)
    b.caso("mudo e desligar são rotas que o servidor atende",
           {"/mudo", "/desligar"} <= rotas_que_o_servidor_atende())
    b.caso("o desligar tem botão nas configurações, com confirmação e o "
           "recado de que a execução sobrevive",
           'id="desligar"' in PAGINA and "execução viva sobrevive" in PAGINA
           and "confirm(" in PAGINA)
    b.caso("as chaves de narração aparecem nas configurações pelo nome",
           "notificacao.tipos" in PAGINA and "notificacao.silencio" in PAGINA)
    with tempfile.TemporaryDirectory() as raiz:
        base = Path(raiz)
        ponte = PonteParaOEncadeador(base, base / "ev", [])
        ligado = ponte.mudo(True)
        marcador = base / MARCADOR_DE_MUDO
        b.caso("ligar o mudo grava o marcador que o motor lê, e responde o "
               "estado novo",
               ligado == {"muda": True} and marcador.exists())
        desligado = ponte.mudo(False)
        b.caso("desligar o mudo apaga o marcador — e apagar duas vezes não "
               "erra",
               desligado == {"muda": False} and not marcador.exists()
               and ponte.mudo(False) == {"muda": False})
        b.caso("o corpo que a mesa serve diz se está muda",
               '"muda"' in Path(__file__).read_text(encoding="utf-8"))
    fonte = Path(__file__).read_text(encoding="utf-8")
    b.caso("o desligar chama o shutdown do servidor noutra linha de "
           "execução — responder antes de morrer",
           "self.server.shutdown" in fonte and "threading.Thread" in fonte)


TEMAS_DO_PAINEL = (
    _sobre_as_cinco_abas,
    _sobre_a_mesa_pelo_desenho_aprovado,
    _sobre_o_botao_de_aprovar,
    _sobre_a_maquina,
    _sobre_a_configuracao_que_falta,
    _sobre_a_ponte_e_o_catalogo,
    _sobre_o_disparo_e_a_regua,
    _sobre_a_auditoria_no_disparo,
    _sobre_o_roteiro_do_pedido,
    _sobre_o_servidor_e_a_porta,
    _sobre_a_pergunta_e_a_vivacidade,
    _sobre_a_mesa_e_os_turnos,
    _sobre_a_proxima_acao,
    _sobre_o_que_a_rodada_1_consertou,
    _sobre_o_que_a_tela_escreve,
    _sobre_a_ordem_da_tela,
    _sobre_o_sino_o_mudo_e_o_desligar,
    _sobre_o_panico_e_a_so_leitura,
    _sobre_o_retomar_e_a_poda,
    _sobre_a_conta_e_a_linha_do_tempo,
    _sobre_a_triagem_da_fila,
    _sobre_o_encadeador_de_verdade,
)


def testar() -> int:
    b = BancadaDoPainel()
    for tema in TEMAS_DO_PAINEL:
        tema(b)
    for falha in b.falhas:
        print(RESULTADO_DO_CASO_FALHO.format(falha))
    print(RESUMO_DOS_CASOS.format(
        VEREDITO_FALHOU if b.falhas else VEREDITO_OK, b.casos)
        + (RESUMO_DAS_FALHAS.format(len(b.falhas)) if b.falhas else ""))
    return 1 if b.falhas else 0


def ler_argumentos():
    ap = argparse.ArgumentParser(description=DESCRICAO_DA_CLI)
    ap.add_argument("--cwd", help=AJUDA_CWD)
    ap.add_argument("--porta", type=int, default=PORTA_PADRAO)
    ap.add_argument("--dir", default=DIR_EVIDENCIAS_PADRAO)
    ap.add_argument("--roteiros", default=ROTEIROS_PADRAO, help=AJUDA_ROTEIROS)
    ap.add_argument("--forcar-arvore-suja", action="store_true",
                    help=AJUDA_FORCAR_ARVORE_SUJA)
    ap.add_argument("--so-leitura", action="store_true",
                    help="o servidor recusa toda rota de escrita; "
                         "só o desligar passa")
    ap.add_argument("--testar", action="store_true")
    return ap.parse_args()


def recusa_do_ambiente(cwd: Path, forcar_arvore_suja: bool) -> str | None:
    if not cwd.is_dir():
        return ERRO_CWD_NAO_E_PASTA.format(cwd)
    if not ENCADEADOR.exists():
        return ERRO_SEM_ENCADEADOR
    if not shutil.which(comando_da_sessao()):
        return ERRO_SEM_O_COMANDO_CLAUDE.format(comando_da_sessao())
    if tem_mudanca_nao_commitada(cwd) and not forcar_arvore_suja:
        return ERRO_ARVORE_SUJA.format(cwd)
    return None


def caminho_sob_a_raiz(valor: str) -> Path:
    caminho = Path(valor)
    return (caminho.resolve() if caminho.is_absolute()
            else (RAIZ / caminho).resolve())


def servidor_de_uma_thread_por_conexao(porta: int, handler):
    return ThreadingHTTPServer((ENDERECO_LOCAL, porta), handler)


def recusar_porta(porta: int, erro: OSError, alvo: str) -> int:
    if erro.errno == errno.EADDRINUSE:
        ocupante, alvo_do_ocupante = quem_responde_na_porta(porta)
        codigo, recado = decidir_porta_ocupada(
            porta, str(RAIZ), alvo, ocupante, alvo_do_ocupante)
        print(recado, file=sys.stdout if codigo == CODIGO_NADA_A_FAZER
              else sys.stderr)
        return codigo
    print(ERRO_PORTA_NAO_ABRIU.format(porta, erro), file=sys.stderr)
    return CODIGO_ERRO_DE_USO


def anunciar_a_subida(porta: int, cwd: Path, dir_evidencias: Path,
                      dirs_roteiros: list, roteiros_achados: int) -> None:
    print(ANUNCIO_NO_AR.format(
        porta, versao_da_camada_declarada_no_topo_do_montar()))
    print(ANUNCIO_REPOSITORIO.format(RAIZ))
    print(ANUNCIO_SESSOES.format(cwd))
    print(ANUNCIO_EVIDENCIAS.format(dir_evidencias))
    print(ANUNCIO_ROTEIROS.format(", ".join(str(p) for p in dirs_roteiros),
                                  roteiros_achados))
    print(ANUNCIO_COMO_ENCERRAR)


def main() -> int:
    argumentos = ler_argumentos()
    if argumentos.testar:
        return testar()
    if not argumentos.cwd:
        print(ERRO_CWD_OBRIGATORIO, file=sys.stderr)
        return CODIGO_ERRO_DE_USO
    cwd = Path(argumentos.cwd).expanduser().resolve()
    if recusa := recusa_do_ambiente(cwd, argumentos.forcar_arvore_suja):
        print(recusa, file=sys.stderr)
        return CODIGO_ERRO_DE_USO

    dir_evidencias = caminho_sob_a_raiz(argumentos.dir)
    dirs_roteiros = [caminho_sob_a_raiz(p)
                     for p in argumentos.roteiros.split(",") if p.strip()]
    ponte = PonteParaOEncadeador(cwd, dir_evidencias, dirs_roteiros)
    ponte.so_leitura = argumentos.so_leitura
    try:
        servidor = servidor_de_uma_thread_por_conexao(argumentos.porta,
                                                      fazer_handler(ponte))
    except OSError as e:
        return recusar_porta(argumentos.porta, e, str(cwd))
    servidor.daemon_threads = True
    anunciar_a_subida(argumentos.porta, cwd, dir_evidencias, dirs_roteiros,
                      len(ponte.catalogo()))
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print(ANUNCIO_ENCERRADO)
    return 0


if __name__ == "__main__":
    sys.exit(main())
