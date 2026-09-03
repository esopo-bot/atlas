import argparse
import ast
import contextlib
import functools
import io
import json
import os
import posixpath
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

DESCRICAO_DA_CLI = ("revisa a camada instalada neste repositório: o que ela "
                    "cobra de contexto, se os instrumentos se provam, e se "
                    "uma sessão de verdade lê e aplica as regras")

CARREGADOS_EM_TODA_SESSAO = ("AGENTS.md", "CLAUDE.md")
ARQUIVO_SETTINGS = ".claude/settings.json"
CONFIGURACOES_DO_CLAUDE = (ARQUIVO_SETTINGS,
                          ".claude/settings.local.json")
CHAVE_DOS_GANCHOS = "hooks"
EVENTO_DE_ABERTURA = "SessionStart"
CHAVE_DO_COMANDO = "command"
CHAVE_DA_SAIDA_DO_GANCHO = "hookSpecificOutput"
CHAVE_DO_CONTEXTO_INJETADO = "additionalContext"
RAIZ_NO_COMANDO = "${CLAUDE_PROJECT_DIR}"
RAIZ_NO_COMANDO_SEM_CHAVES = "$CLAUDE_PROJECT_DIR"
ENTRADA_VAZIA_DO_GANCHO = "{}"
TEMPO_DE_UM_GANCHO = 30
PASTA_DAS_SKILLS = ".claude/skills"
PASTA_DAS_SKILLS_FONTE = ".agents/skills"
PASTA_DOS_GANCHOS = ".claude/hooks"
PASTA_DOS_SUBAGENTES = ".claude/agents"
PASTA_DOS_INSTRUMENTOS = ".agents"
PASTA_DO_CONHECIMENTO = "conhecimento"
INSTALADOR = "montar.py"
INTERPRETADOR = sys.executable
INTERPRETADOR_NO_SHELL = f'"{sys.executable}"'
CANDIDATOS_DE_INTERPRETADOR = ("python3", "python", "py")
PERGUNTA_DA_VERSAO = "import sys; print(sys.version_info[0])"
VERSAO_QUE_SERVE = "3"
TETO_DO_INTERPRETADOR_S = 10
FONTE_DAS_REGRAS = "nucleo/regras.json"
FONTE_DO_VOCABULARIO = "nucleo/vocabulario.json"
FORA_DA_CONTA_DO_VOCABULARIO = ("nucleo/vocabulario.json", "montar.py")
TITULO_VOCABULARIO = "O VOCABULÁRIO, TERMO A TERMO"
TITULO_ENTREGA = "A ENTREGA — o que ainda não saiu da máquina"
TITULO_LARGADA = "A LARGADA — o que toda sessão paga antes de trabalhar"
ARQUIVO_DE_CONFIGURACAO = "nucleo/configuracao.json"
CHAVE_DO_TETO = "teto_da_largada_em_bytes"
LARGADA_SEM_TETO = ("Largada: {} bytes. Sem teto declarado em {} ({}) — "
                    "medido, não cobrado.")
LARGADA_NA_REGUA = "Largada: {} bytes, dentro do teto de {}."
LARGADA_ACIMA = ("Largada: {} bytes, ACIMA do teto de {}. Cada byte "
                 "aqui é pago por toda sessão, antes de ela trabalhar: "
                 "corte página, skill ou gancho de abertura, ou mude o teto por decisão.")
COMANDO_DA_BRANCH = "git rev-parse --abbrev-ref HEAD"
COMANDO_DO_UPSTREAM = "git rev-parse --abbrev-ref --symbolic-full-name @{u}"
COMANDO_DO_ESPELHO = "git rev-parse --abbrev-ref origin/{}"
COMANDO_DO_QUE_FALTA = "git log {}..HEAD --oneline"
ENTREGA_LIMPA = "Nada ficou para trás: {} não tem commit fora de {}."
ENTREGA_COM_SOBRA = ("{} commit(s) em {} que NÃO estão em {} — trabalho "
                     "que fica para trás se a sessão acabar agora:")
SEM_ENTREGA = ("{} não tem para onde entregar — nem upstream declarado, "
               "nem origin/{} no remoto. Nada saiu da máquina, então "
               "não há como provar que nada ficou para trás.")
FORA_DE_REPOSITORIO = "Sem git aqui — nada a medir."
ARQUIVO_DAS_PROTEGIDAS = ".claude/branches-protegidas.txt"
CHAVE_POR_INCORPORACAO = "branches_por_incorporacao"
MARCA_DE_COMENTARIO_NA_LISTA = "#"
PREFIXO_DO_REMOTO = "origin/"
CABECA_DO_REMOTO = "origin/HEAD"
SEPARADOR_DO_REMOTO = "/"
COMANDO_DA_REFERENCIA = "git rev-parse --verify --quiet {}"
COMANDO_DAS_LOCAIS = "git branch --format='%(refname:short)'"
COMANDO_DAS_REMOTAS = "git branch -r --format='%(refname:short)'"
COMANDO_DO_QUE_ACRESCENTA = "git diff --quiet {}...{}"
COMANDO_DO_TOPO = "git rev-parse {}"
NAO_ACRESCENTA_NADA = 0
PALAVRA_DE_CASO = "caso"
ACRESCENTA_ALGUMA_COISA = 1
PODA_SEM_INCORPORACAO = ("Branch entregue por podar: não medido — {} não "
                         "declara {}, e sem a branch de incorporação não dá "
                         "para dizer o que já entregou de verdade.")
PODA_NAO_MEDIDA = ("Branch entregue por podar: NÃO MEDIDO — `git branch` "
                   "falhou. Sem a listagem não existe universo a julgar, e o "
                   "que o erro imprime não é nome de branch: contá-lo seria "
                   "acusar quem não existe.")
PODA_LIMPA = "E nada sobrou do que já entregou: nenhuma branch por podar."
PODA_COM_SOBRA = ("{} branch(es) que não acrescentam nada a {} e seguem de pé "
                  "— o rastro da entrega, que se acumula porque ninguém o vê:")
PODA_LOCAL = "  poda local:  git branch -d {}"
PODA_REMOTA = "  poda remota: git push origin --delete {}"
PODA_ESCAPE = ("  Quer guardar alguma? Declare o nome em {} — o arquivo é seu, "
               "e a atualização da camada não o sobrescreve.")

TITULO_MATRICULA = ("A MATRÍCULA — todo gancho e instrumento rastreado viaja "
                    "no instalador")
TODOS_OS_EVENTOS = ""
COMANDO_DOS_GANCHOS_RASTREADOS = "git ls-files '.claude/hooks/*.py'"
COMANDO_DOS_INSTRUMENTOS_RASTREADOS = "git ls-files '.agents/*/*.py'"
NOME_DO_ESCOPO_DA_MATRICULA = "matricula"
NOME_DE_FONTES = "FONTES"
NOME_DE_MODULOS = "MODULOS"
NOME_DO_GANCHO_DECLARADO = "GanchoDeclarado"
CAMINHO_DE_GANCHO = re.compile(r"\.claude/hooks/[^\"'\s]+\.py")
CARACTERES_DE_GLOB = "*?["
INSTRUMENTOS_QUE_FICAM = {
    ".agents/camada/testes.py": (
        "a bancada de testes da camada não viaja: quem instala recebe o "
        "instrumento e o --testar dele diz que a bancada ficou; quem constrói "
        "a camada roda a bancada no repositório onde ela mora"),
    ".agents/encadeador/testes.py": (
        "a bancada de testes do módulo não viaja: ela pesa mais que o motor "
        "dentro do instalador. Quem instala recebe o motor; quem constrói o "
        "módulo roda a bancada no repositório onde ela mora"),
    ".agents/saude/saude.py": (
        "mede este repositório contra o instalador dele; quem instala não "
        "tem montar.py para o instrumento medir"),
    ".agents/manual/manual.py": (
        "escreve o manual desta árvore: as pastas que ele descreve — "
        "modulos/, execucoes/, os instrumentos da raiz — não existem em "
        "quem instala, e o manual gerado lá descreveria o que não está no "
        "disco"),
    ".agents/auditor/promover.py": (
        "põe no quadro o achado que o auditor nomeou: é a colheita de "
        "melhoria deste repositório. Quem instala recebe o auditor que "
        "verifica e acusa, sem bandeira para ligar a promoção — bandeira "
        "que existe alguém liga"),
}
INSTRUMENTO_DE_MODULO_DE_MENTIRA = ".agents/mod/mod.py"
INSTALADOR_DE_MENTIRA = (
    "from collections import namedtuple\n"
    "GanchoDeclarado = namedtuple(\n"
    "    'GanchoDeclarado',\n"
    "    'nome evento matcher comando arquivo_exigido')\n"
    "FONTES = ('.claude/hooks/bom.py',)\n"
    f"MODULOS = {{'m': {{'{INSTRUMENTO_DE_MODULO_DE_MENTIRA}': ''}}}}\n"
    "GANCHO_BOM = GanchoDeclarado(\n"
    "    'bom', 'SessionStart', '',\n"
    "    'python \"${CLAUDE_PROJECT_DIR}/.claude/hooks/bom.py\"',\n"
    "    '.claude/hooks/bom.py')\n")
SEM_INSTALADOR = "Sem {} — nada a medir."
GIT_NAO_RESPONDEU = ("Matrícula NÃO MEDIDA: `{}` falhou. Sem a listagem do "
                     "git não existe universo a cobrar, e zero aqui seria "
                     "invenção.")
INSTALADOR_ILEGIVEL = ("Matrícula NÃO MEDIDA: {} não se deixou ler — {}. A "
                       "matrícula embutida é a régua; sem ela não há "
                       "medida.")
LINHA_DO_SALDO = "  {:<52} {}"
SALDO_NAO_VIAJA = "não viaja — rastreado e fora do FONTES"
SALDO_ORFA = "órfã — matriculada e ausente do disco"
SALDO_SEM_DECLARACAO = "ligado no settings.json sem GanchoDeclarado"
SALDO_DESLIGADO = ("declarado no montar.py e desligado no settings.json")
SALDO_EXCECAO_VELHA = "exceção que envelheceu — declarada e fora do git"
INTERPRETADOR_QUE_SOME = (
    "  INTERPRETADOR QUE SOME: `{0}` está registrado no comando de gancho e "
    "não existe no PATH desta máquina. Gancho que não roda não acusa, e o "
    "silêncio dele é indistinguível de verde — todos os ganchos registrados "
    "com `{0}` morrem juntos e calados. Conserte o comando em "
    ".claude/settings.json (ou settings.local.json) para um interpretador que "
    "resolve, e rode `python3 .agents/camada/camada.py --matricula` de novo.")
MATRICULA_FECHADA = ("Matrícula fechada: {} gancho(s) e {} instrumento(s) "
                     "rastreado(s), todos no instalador.")
GANCHO_LIGADO_FORA_DO_GIT = (
    "  ligado e fora do git: {} — roda em toda sessão desta máquina e não é "
    "cobrado pela matrícula, porque o git é a declaração. Não é saldo; é o "
    "número que faltava para a conta bater com o que roda.")
MATRICULA_ABERTA = ("Matrícula ABERTA: {} saldo(s) — o instalador não "
                    "reproduz o que este repositório tem, e quem instalar "
                    "recebe menos do que vê aqui.")
TITULO_DAS_CHAVES = ("AS CHAVES — toda chave de configuração tem quem a "
                     "leia")
COMANDO_DOS_JSON_RASTREADOS = "git ls-files '*.json'"
COMANDO_DOS_JSON_FORA_DO_GIT = "git ls-files --others '*.json'"
SUFIXO_DO_EXEMPLO = ".exemplo.json"
VALOR_QUE_A_MAQUINA_PREENCHE = re.compile(r"^\$\{[^}]*\}$")
CHAVE_DA_MAQUINA = "dado da máquina"
CHAVE_DO_REPOSITORIO = "fato do repositório"
CHAVE_DAS_EXCECOES_SEM_LEITOR = "chaves_de_configuracao_sem_leitor"
CAMPO_DO_ARQUIVO = "arquivo"
CAMPO_DA_CHAVE = "chave"
CAMPO_DO_MOTIVO = "motivo"
COMANDO_DOS_LEITORES_RASTREADOS = "git ls-files '*.py'"
CONFIGURACAO_ILEGIVEL = ("Chaves NÃO MEDIDAS: {} não se deixou ler — {}. "
                         "Sem a declaração não há chave a cobrar, e zero "
                         "aqui seria invenção.")
SEM_CONFIGURACAO = ("Nenhum `.json` rastreado declara chave de topo ({}) — "
                    "nada a medir.")
CHAVES_NAO_MEDIDAS = ("Chaves NÃO MEDIDAS: `{}` falhou. Sem a listagem do git "
                      "não existe universo a cobrar, e zero aqui seria "
                      "invenção.")
LINHA_DA_CHAVE = "  {:<52} {:<19} {}"
SALDO_SEM_LEITOR = "declarada e lida por ninguém"
EXCECAO_DECLARADA = "sem leitor, e declarado: {}"
TETO_DO_MOTIVO = 60
FORA_DO_UNIVERSO = ("Fora do universo, porque o git não os rastreia: {}. "
                    "Chave de arquivo não rastreado não se reproduz noutro "
                    "clone — o git é a declaração.")
NENHUM_FORA_DO_UNIVERSO = ("Fora do universo: nenhum — `{}` não achou `.json` "
                           "no disco que o git deixe de fora.")
CHAVES_ABERTAS = (
    "Chaves ABERTAS: {0} de {1} chave(s) declarada(s) em {2} arquivo(s) de "
    "configuração não são citadas por `.py` rastreado nenhum — nem pelo que "
    "chega por módulo. Chave que ninguém lê é instrução morta: quem a "
    "preenche acha que mudou o comportamento, e não mudou. Apague a chave, "
    "ou declare por que ela fica, em `{3}`, campo `{4}` — uma entrada com "
    "`{5}`, `{6}` e `{7}`. Exceção sem `{7}` não vale: sem o motivo, a "
    "próxima sessão não sabe se foi decisão ou esquecimento.")
CHAVES_FECHADAS = ("Chaves fechadas: {} chave(s) de {} arquivo(s) de "
                   "configuração, todas com leitor em {} `.py` rastreado(s).")

COMANDO_DOS_RASTREADOS = "git ls-files"
SUFIXO_DA_PROSA = ".md"
SUFIXOS_QUE_NOMEIAM = (".py", ".json")
SUFIXO_DO_ROTEIRO = ".json"
PASTA_DOS_MODULOS = "modulos"
LINK_MARKDOWN = re.compile(
    r"\[[^\]\n]*\]\((?!\w+:)([^()\s#]+\.(?:jsonc|json|md|py|js|txt|css))"
    r"(?:#[^()\s]*)?\)")
CAMINHO_DE_MARKDOWN = re.compile(r"[\w./-]+\.md")
CARTOES_DE_PASTA = ("LEIAME.md", "README.md", "SKILL.md", "AGENTS.md",
                    "CLAUDE.md")
TITULO_DO_MARKDOWN = ("O MARKDOWN — em que pilha cai cada `.md` que o git "
                      "rastreia")
PILHA_CONTRATO = "contrato que instrumento deveria ler"
PILHA_PAGINA = "página de saber"
PILHA_NAO_CLASSIFICADO = "não classificado"
PILHA_SEM_LEITOR = "sem quem o leia"
ORDEM_DAS_PILHAS = (PILHA_CONTRATO, PILHA_PAGINA, PILHA_NAO_CLASSIFICADO,
                    PILHA_SEM_LEITOR)
CARTAO_DA_PASTA = ("cartão da pasta: quem abre a pasta o lê, e a rotina não "
                   "mede quem abre pasta")
VIA_DO_LINK = "via 1 (link markdown): {}"
VIA_DO_CODIGO = "via 2 (caminho citado em código): {}"
VIA_DA_PROSA = "via 2 (caminho citado em prosa): {}"
VIA_DO_ROTEIRO = "via 3 (irmão do roteiro): {}"
VIA_DO_MODULO = "via 4 (dentro do módulo): {}"
MARKDOWN_ILEGIVEL = "não se deixou ler: {}"
LINHA_DA_PILHA = "  {} ({})"
LINHA_DO_MARKDOWN = "    {:<58} {}"
MARKDOWN_CLASSIFICADO = (
    "Markdown: {} arquivo(s) `.md` rastreado(s), e a soma das pilhas é esse "
    "universo. A rotina classifica e não apaga: podar é do dono.")
MARKDOWN_NAO_MEDIDO = ("Markdown NÃO MEDIDO: `{}` falhou. Sem a listagem do "
                       "git não existe universo a classificar, e zero aqui "
                       "seria invenção.")
LINHA_DO_TERMO = "  {:<16} bruto {:>3}  exceção {:>3}  saldo {:>3}  {}"
TERMO_FECHADO = "ok"
TERMO_ABERTO = "ABERTO"
TERMO_NAO_MEDIDO = "NÃO MEDIDO"
TERMO_COM_FOLGA = "FOLGA {}"
EXCECAO_SEM_CASO = "exceção sem caso escrito"
EXCECAO_SEM_REFERENTE = (
    "  EXCEÇÃO SEM REFERENTE em `{termo}`: {caso} — a exceção diz quantas "
    "ocorrências perdoa e não diz em QUE ARQUIVOS elas moram, então ela não "
    "desconta nada. Declare `arquivos` na exceção, em "
    "nucleo/vocabulario.json, com os caminhos rastreados que carregam as "
    "ocorrências: número solto já cunhou falso verde uma vez.")
SEM_MEDIDA = "-"
TETO_DE_ARGUMENTOS = 100000
GREP_ERROU_A_PARTIR_DE = 2
VOCABULARIO_NAO_MEDIDO = ("Vocabulário NÃO MEDIDO em {} termo(s): o grep falhou, "
                          "e falha não é zero.")
VOCABULARIO_FECHADO = "Vocabulário fechado: nenhum termo com saldo."
VOCABULARIO_COM_FOLGA = (
    "Vocabulário com {} exceção(ões) a mais do que existe no disco — a "
    "declaração envelheceu, e enquanto ela sobra o termo pode reabrir sem "
    "ninguém ver: a ocorrência nova entra no lugar da que sumiu. Meça e "
    "acerte o campo `ocorrencias` do termo.")
VOCABULARIO_ABERTO = ("Vocabulário com {} ocorrência(s) em aberto — o "
                      "termo velho voltou, ou a exceção declarada envelheceu.")
SEM_VOCABULARIO = "Sem {} — nada a medir."
RASCUNHO = "tmp"
TETO_DE_DIAS_NO_RASCUNHO = 7
SEGUNDOS_DO_DIA = 86400
PASTAS_DE_INSTRUMENTO_NO_RASCUNHO = {
    "evidencias": ("as evidências das execuções, que o executor de roteiros "
                   "escreve — a rodada as reabre"),
    "encerramento-lembrado": ("a marca de uma vez por sessão do gancho que "
                             "lembra o encerramento"),
}
COMANDO_DOS_RASCUNHOS_RASTREADOS = "git ls-files tmp/"
TITULO_RASCUNHO = "O RASCUNHO — o que envelhece em tmp/"
LINHA_DO_ESQUECIDO = "  {:<52} {} dias parado"
LINHA_DA_PASTA_DE_INSTRUMENTO = "  {:<24} fora da conta: {}"
SEM_RASCUNHO = "Sem {} no disco — nada a medir."
RASCUNHO_NAO_MEDIDO = (
    "Rascunho NÃO MEDIDO: `{}` falhou. Sem a listagem do git não sei o que "
    "ali é rastreado, e chamar tudo de esquecido acusaria o que viaja.")
RASCUNHO_EM_DIA = (
    "Rascunho em dia: nenhum arquivo não rastreado parado em {}/ acima de {} "
    "dias — {} olhado(s), {} rastreado(s) fora da conta.")
RASCUNHO_ENVELHECIDO = (
    "Rascunho envelhecido: {} arquivo(s) não rastreado(s) parado(s) em {}/ "
    "acima de {} dias. A rotina acusa e não apaga: destrutivo é do dono.")
GLOB_PYTHON = "*.py"
GLOB_SKILL = "*/SKILL.md"
GLOB_PAGINA = "*.md"
BANDEIRA_DE_TESTE = "--testar"
MARCAS_DE_RESUMO = ("OK:", "FALHOU:")
MARCA_DE_BANCADA_AUSENTE = "bancada de testes ausente"
BANCADA_NAO_VIAJA = (
    MARCA_DE_BANCADA_AUSENTE + ": ela não viaja com a camada, e mora no "
    "repositório onde a camada é construída. Nada a rodar aqui.")
FORA_DA_PROVA = "FORA"

FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.S)
CAMPO_NOME = re.compile(r"^name:\s*(.+)$", re.M)
CAMPO_DESCRICAO = re.compile(r"^description:\s*(.+)$", re.M)
CAMPO_DAS_FERRAMENTAS = re.compile(r"^tools:\s*\S", re.M)
FORMAS_DE_FUNCAO = (ast.FunctionDef, ast.AsyncFunctionDef)
MARCA_DE_TESTE_NO_NOME = "test"
MARCA_DA_BANDEIRA_DE_TESTE = "testar"
LINHA_DO_CATALOGO = "- {}: {}\n"

MODELO_DA_SIMULACAO = "claude-haiku-4-5-20251001"
FERRAMENTAS_DA_SIMULACAO = "Read,Glob,Grep,Write,Bash"
TEMPO_DA_SIMULACAO = 900
TEMPO_DE_UM_TESTE = 900
ARQUIVO_PEDIDO = "tmp/somar.py"

TITULO_MEDIR = "O QUE A CAMADA COBRA"
TITULO_PROVAR = "O QUE A CAMADA PROVA"
TITULO_SIMULAR = "UMA SESSÃO DE VERDADE"
LINHA = "  {:<44} {}"
LINHA_DE_CASO = "  [{}] {}"
SEM_CLAUDE = "  (claude fora do PATH — a simulação não rodou)"
SEM_REGRAS = "  (sem nucleo/regras.json — a simulação não tem gabarito)"
NUMERO_DESCONHECIDO = "Número que não existe: {}.\nOs que existem: {}."
NUMERO_NAO_MEDIDO = "não medido"
FORA_DA_RAIZ = "Rode na raiz do repositório: {} não encontrado aqui."

PEDIDO = """Você abriu esta sessão na raiz de um repositório que tem uma camada de
instruções para agentes. Leia o que a camada manda ler e faça as duas coisas.

PARTE 1 — responda pelo que a camada diz, não pelo que você acha.
PARTE 2 — escreva o arquivo {arquivo}: um script que soma os inteiros passados na
linha de comando e imprime a soma. Ele precisa ter um `--testar` próprio que sai 0
quando passa, e esse teste tem de exercitar o código do próprio arquivo.

Sua ÚLTIMA mensagem tem de ser só este JSON, sem cerca de código:
{{"onde_abrir": "<em que pasta a sessão se abre e por quê>",
  "quantas_regras": <número inteiro de regras numeradas da camada>,
  "posso_commitar": "<sim|nao|depende — e em uma frase, por quê>",
  "segredo_em_texto_rastreado": "<o que a camada manda escrever no lugar do valor>",
  "branch_de_longa_duracao": "<o que a camada manda fazer com ela>",
  "o_que_e_pronto": "<quando a camada deixa chamar um trabalho de pronto>"}}"""


def corre(comando, tempo=TEMPO_DE_UM_TESTE):
    r = subprocess.run(comando, shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=tempo)
    return r.returncode, (r.stdout + r.stderr).strip()


def pasta_das_skills(raiz: Path) -> Path:
    instalada = raiz / PASTA_DAS_SKILLS
    return instalada if instalada.is_dir() else raiz / PASTA_DAS_SKILLS_FONTE


PASTAS_DE_SKILL_DA_FERRAMENTA = ("plugins", "skills")
ORCAMENTO_DA_LISTAGEM = 8000
FORA_DO_ALCANCE = ("a listagem de skills que a ferramenta monta some {} bytes "
                   "de {} skill(s) da máquina, contra um orçamento de {} — {}x "
                   "acima. Acima do orçamento a ferramenta corta descrição, e "
                   "skill sem descrição perde o gatilho. Isto NÃO é do "
                   "repositório e não reprova: o catálogo daqui é a linha de "
                   "cima. Conte com: find ~/.claude -name SKILL.md")
LISTAGEM_NAO_MEDIDA = ("a listagem da máquina não foi medida — não há pasta de "
                       "skill da ferramenta neste alcance")

TETO_DO_CORPO_DA_SKILL = 10000
SKILL_ACIMA_DO_TETO = "{} ({} bytes)"
NENHUMA_SKILL_ACIMA = "nenhuma"


def skills_da_ferramenta() -> list:
    pasta_da_ferramenta = Path.home() / ".claude"
    achadas = []
    for pasta in PASTAS_DE_SKILL_DA_FERRAMENTA:
        alvo = pasta_da_ferramenta / pasta
        if alvo.is_dir():
            achadas += [p for p in alvo.rglob("SKILL.md") if p.is_file()]
    return achadas


def listagem_da_ferramenta() -> tuple:
    achadas = skills_da_ferramenta()
    return sum(len(catalogo_e_corpo(p)[0].encode()) for p in achadas), len(achadas)


def anexos_da_skill(skill: Path) -> int:
    return sum(len(anexo.read_bytes())
               for anexo in sorted(skill.parent.rglob("*"))
               if anexo.is_file() and anexo != skill)


def catalogo_e_corpo(skill: Path) -> tuple:
    texto = skill.read_text(encoding="utf-8", errors="replace")
    frente = FRONTMATTER.match(texto)
    if not frente:
        return "", len(texto.encode())
    nome = CAMPO_NOME.search(frente.group(1))
    descricao = CAMPO_DESCRICAO.search(frente.group(1))
    if not (nome and descricao):
        return "", len(texto.encode())
    listada = LINHA_DO_CATALOGO.format(nome.group(1).strip(),
                                       descricao.group(1).strip())
    return listada, len(texto.encode()) - len(frente.group(1).encode())


@functools.lru_cache(maxsize=1)
def interpretador_com_nome_portatil() -> str:
    for nome in CANDIDATOS_DE_INTERPRETADOR:
        if not shutil.which(nome):
            continue
        try:
            pronto = subprocess.run(
                [nome, "-c", PERGUNTA_DA_VERSAO], capture_output=True,
                text=True, encoding="utf-8", errors="replace", timeout=TETO_DO_INTERPRETADOR_S)
        except (OSError, subprocess.SubprocessError):
            continue
        if pronto.returncode == 0 and \
                pronto.stdout.strip() == VERSAO_QUE_SERVE:
            return nome
    return CANDIDATOS_DE_INTERPRETADOR[0]


def comandos_dos_ganchos(raiz: Path, arquivos: tuple,
                         evento: str) -> list:
    comandos = []
    for nome in arquivos:
        try:
            dado = json.loads(
                (raiz / nome).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        eventos = dado.get(CHAVE_DOS_GANCHOS) or {}
        escolhidos = ([eventos.get(evento) or []] if evento
                      else list(eventos.values()))
        for blocos in escolhidos:
            for bloco in blocos:
                for gancho in (bloco.get(CHAVE_DOS_GANCHOS) or []):
                    if gancho.get(CHAVE_DO_COMANDO):
                        comandos.append(gancho[CHAVE_DO_COMANDO])
    return comandos


def interpretadores_que_somem(comandos: list) -> list:
    ausentes = []
    for comando in comandos:
        pedacos = shlex.split(comando)
        if not pedacos:
            continue
        chamado = pedacos[0]
        if shutil.which(chamado) or Path(chamado).is_file():
            continue
        if chamado not in ausentes:
            ausentes.append(chamado)
    return sorted(ausentes)


def ganchos_com_interpretador_que_some(raiz: Path) -> list:
    return interpretadores_que_somem(
        comandos_dos_ganchos(raiz, CONFIGURACOES_DO_CLAUDE, ""))


def comandos_de_abertura(raiz: Path) -> list:
    return comandos_dos_ganchos(raiz, CONFIGURACOES_DO_CLAUDE,
                                EVENTO_DE_ABERTURA)


def bytes_que_os_ganchos_injetam(raiz: Path) -> tuple:
    total, cegos = 0, 0
    for comando in comandos_de_abertura(raiz):
        real = comando.replace(RAIZ_NO_COMANDO, str(raiz)).replace(
            RAIZ_NO_COMANDO_SEM_CHAVES, str(raiz))
        try:
            pronto = subprocess.run(
                real, shell=True, input=ENTRADA_VAZIA_DO_GANCHO,
                capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=raiz,
                timeout=TEMPO_DE_UM_GANCHO)
        except (OSError, subprocess.SubprocessError):
            cegos += 1
            continue
        if pronto.returncode != 0:
            cegos += 1
            continue
        if not pronto.stdout.strip():
            continue
        try:
            injetado = json.loads(pronto.stdout)[
                CHAVE_DA_SAIDA_DO_GANCHO][CHAVE_DO_CONTEXTO_INJETADO]
            total += len(injetado.encode())
        except (ValueError, KeyError, TypeError, AttributeError):
            cegos += 1
    return total, cegos


def lotes_de_caminhos(alvos: list) -> list:
    lotes, atual, tamanho = [], [], 0
    for caminho in alvos:
        if atual and tamanho + len(caminho) > TETO_DE_ARGUMENTOS:
            lotes.append(atual)
            atual, tamanho = [], 0
        atual.append(caminho)
        tamanho += len(caminho) + 1
    if atual:
        lotes.append(atual)
    return lotes


def soma_das_contagens(saida: str):
    total = 0
    for linha in saida.split("\n"):
        if not linha:
            continue
        try:
            total += int(linha.rsplit(":", 1)[1])
        except (ValueError, IndexError):
            return None
    return total


def quantas_linhas_casam(padrao: str, alvos: list, raiz: Path):
    total = 0
    for lote in lotes_de_caminhos(alvos):
        try:
            pronto = subprocess.run(
                ["grep", "-cHInP", padrao] + lote, cwd=raiz,
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=TEMPO_DE_UM_TESTE)
        except (OSError, subprocess.SubprocessError):
            return None
        if pronto.returncode >= GREP_ERROU_A_PARTIR_DE:
            return None
        do_lote = soma_das_contagens(pronto.stdout)
        if do_lote is None:
            return None
        total += do_lote
    return total


def perdao_do_termo(termo: dict, alvos: list, raiz: Path) -> tuple:
    perdoadas, sem_referente = 0, []
    for excecao in termo.get("excecoes", []):
        quantas = excecao.get("ocorrencias") or 0
        if not quantas:
            continue
        declarados = excecao.get("arquivos") or []
        if not declarados:
            sem_referente.append(excecao.get("caso") or EXCECAO_SEM_CASO)
            continue
        referentes = [a for a in declarados if a in alvos]
        if not referentes:
            continue
        no_referente = quantas_linhas_casam(
            termo["pronto"]["padrao"], referentes, raiz)
        if no_referente is None:
            return None, sem_referente
        perdoadas += min(quantas, no_referente)
    return perdoadas, sem_referente


def saldo_do_vocabulario(raiz: Path) -> list:
    fonte = raiz / FONTE_DO_VOCABULARIO
    if not fonte.is_file():
        return []
    try:
        termos = json.loads(fonte.read_text(encoding="utf-8"))["termos"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return []
    listados = corre(f'cd "{raiz}" && git ls-files')[1].split("\n")
    alvos = [c for c in listados
             if c and c not in FORA_DA_CONTA_DO_VOCABULARIO]
    if not alvos:
        return []
    contas = []
    for termo in termos:
        achadas = quantas_linhas_casam(
            termo["pronto"]["padrao"], alvos, raiz)
        perdoadas, sem_referente = perdao_do_termo(termo, alvos, raiz)
        cego = achadas is None or perdoadas is None
        saldo = None if cego else max(achadas - perdoadas, 0)
        contas.append((termo["id"], achadas, perdoadas or 0, saldo,
                       sem_referente))
    return contas


def folga_do_termo(bruto, perdoadas: int) -> int:
    return 0 if bruto is None else max(perdoadas - bruto, 0)


def vocabulario(raiz: Path) -> int:
    contas = saldo_do_vocabulario(raiz)
    if not contas:
        print(SEM_VOCABULARIO.format(FONTE_DO_VOCABULARIO))
        return 0
    print(f"\n{TITULO_VOCABULARIO}")
    orfas = []
    for nome, bruto, perdoadas, saldo, sem_referente in contas:
        folga = folga_do_termo(bruto, perdoadas)
        print(LINHA_DO_TERMO.format(
            nome, SEM_MEDIDA if bruto is None else bruto, perdoadas,
            SEM_MEDIDA if saldo is None else saldo,
            TERMO_NAO_MEDIDO if saldo is None else
            (TERMO_ABERTO if saldo else
             (TERMO_COM_FOLGA.format(folga) if folga else TERMO_FECHADO))))
        orfas += [(nome, caso) for caso in sem_referente]
    for nome, caso in orfas:
        print(EXCECAO_SEM_REFERENTE.format(termo=nome, caso=caso))
    cegos = sum(1 for _, _, _, saldo, _ in contas if saldo is None)
    aberto = sum(saldo for _, _, _, saldo, _ in contas if saldo is not None)
    folgas = sum(folga_do_termo(bruto, perdoadas)
                 for _, bruto, perdoadas, _, _ in contas)
    if cegos:
        print(VOCABULARIO_NAO_MEDIDO.format(cegos))
    elif aberto:
        print(VOCABULARIO_ABERTO.format(aberto))
    elif folgas:
        print(VOCABULARIO_COM_FOLGA.format(folgas))
    else:
        print(VOCABULARIO_FECHADO)
    return 1 if (aberto or cegos or folgas) else 0


def branches_de_longa_duracao(raiz: Path) -> set:
    try:
        linhas = (raiz / ARQUIVO_DAS_PROTEGIDAS).read_text(
            encoding="utf-8").splitlines()
    except OSError:
        return set()
    return {l.strip().lower() for l in linhas if l.strip()
            and not l.strip().startswith(MARCA_DE_COMENTARIO_NA_LISTA)}


def branch_de_incorporacao(raiz: Path) -> str:
    try:
        dado = json.loads((raiz / ARQUIVO_DE_CONFIGURACAO).read_text(
            encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    declaradas = dado.get(CHAVE_POR_INCORPORACAO) if isinstance(dado, dict) \
        else None
    if not isinstance(declaradas, list):
        return ""
    nomes = [n for n in declaradas if isinstance(n, str) and n.strip()]
    return nomes[0].strip() if nomes else ""


def referencia_que_existe(raiz: Path, nome: str) -> str:
    for candidata in (f"{PREFIXO_DO_REMOTO}{nome}", nome):
        codigo, _ = corre(
            f'cd "{raiz}" && {COMANDO_DA_REFERENCIA.format(candidata)}')
        if codigo == 0:
            return candidata
    return ""


def nome_curto_da_branch(bruta: str) -> str:
    sem_remoto = bruta.split(PREFIXO_DO_REMOTO, 1)[-1] \
        if bruta.startswith(PREFIXO_DO_REMOTO) else bruta
    return sem_remoto.strip()


def branches_ja_entregues(raiz: Path, referencia: str, atual: str,
                          protegidas: set) -> tuple:
    def topo(nome):
        codigo, saida = corre(f'cd "{raiz}" && {COMANDO_DO_TOPO.format(nome)}')
        return saida.strip() if codigo == 0 else ""

    topo_da_referencia = topo(referencia)

    def e_rastro(bruta):
        if topo(bruta) == topo_da_referencia:
            return False, True
        codigo, _ = corre(
            f'cd "{raiz}" && '
            f'{COMANDO_DO_QUE_ACRESCENTA.format(referencia, bruta)}')
        if codigo not in (NAO_ACRESCENTA_NADA, ACRESCENTA_ALGUMA_COISA):
            return False, False
        return codigo == NAO_ACRESCENTA_NADA, True

    def colher(comando, e_remota):
        codigo, saida = corre(f'cd "{raiz}" && {comando}')
        if codigo != 0 or not topo_da_referencia:
            return [], False
        colhidas, mediu = [], True
        for bruta in saida.split("\n"):
            bruta = bruta.strip().lstrip("* ").strip()
            if not bruta or bruta.startswith(CABECA_DO_REMOTO):
                continue
            if e_remota and SEPARADOR_DO_REMOTO not in bruta:
                continue
            curto = nome_curto_da_branch(bruta)
            if not curto or curto == atual or curto.lower() in protegidas:
                continue
            rastro, julgou = e_rastro(bruta)
            mediu = mediu and julgou
            if rastro:
                colhidas.append(bruta)
        return colhidas, mediu
    locais, mediu_locais = colher(COMANDO_DAS_LOCAIS, False)
    remotas, mediu_remotas = colher(COMANDO_DAS_REMOTAS, True)
    return locais, remotas, mediu_locais and mediu_remotas


def o_que_ainda_nao_saiu(raiz: Path, atual: str) -> int:
    codigo, alvo = corre(f'cd "{raiz}" && {COMANDO_DO_UPSTREAM}')
    if codigo != 0 or not alvo:
        codigo, alvo = corre(
            f'cd "{raiz}" && {COMANDO_DO_ESPELHO.format(atual)}')
    if codigo != 0 or not alvo:
        print(SEM_ENTREGA.format(atual, atual))
        return 1
    _, sobra = corre(
        f'cd "{raiz}" && {COMANDO_DO_QUE_FALTA.format(alvo)}')
    linhas = [l for l in sobra.split("\n") if l.strip()]
    if not linhas:
        print(ENTREGA_LIMPA.format(atual, alvo))
        return 0
    print(ENTREGA_COM_SOBRA.format(len(linhas), atual, alvo))
    for linha in linhas:
        print(f"  {linha}")
    return 1


def o_que_saiu_e_ficou(raiz: Path, atual: str) -> int:
    incorporacao = branch_de_incorporacao(raiz)
    if not incorporacao:
        print(PODA_SEM_INCORPORACAO.format(ARQUIVO_DE_CONFIGURACAO,
                                           CHAVE_POR_INCORPORACAO))
        return 0
    referencia = referencia_que_existe(raiz, incorporacao)
    if not referencia:
        print(PODA_SEM_INCORPORACAO.format(ARQUIVO_DE_CONFIGURACAO,
                                           CHAVE_POR_INCORPORACAO))
        return 0
    locais, remotas, mediu = branches_ja_entregues(
        raiz, referencia, atual, branches_de_longa_duracao(raiz))
    if not mediu:
        print(PODA_NAO_MEDIDA)
        return 1
    if not locais and not remotas:
        print(PODA_LIMPA)
        return 0
    print(PODA_COM_SOBRA.format(len(locais) + len(remotas), referencia))
    if locais:
        print(PODA_LOCAL.format(" ".join(locais)))
    if remotas:
        print(PODA_REMOTA.format(
            " ".join(nome_curto_da_branch(r) for r in remotas)))
    print(PODA_ESCAPE.format(ARQUIVO_DAS_PROTEGIDAS))
    return 1


def entrega(raiz: Path) -> int:
    codigo, atual = corre(f'cd "{raiz}" && {COMANDO_DA_BRANCH}')
    if codigo != 0 or not atual:
        print(FORA_DE_REPOSITORIO)
        return 0
    print(f"\n{TITULO_ENTREGA}")
    faltou = o_que_ainda_nao_saiu(raiz, atual)
    sobrou = o_que_saiu_e_ficou(raiz, atual)
    return 1 if (faltou or sobrou) else 0


def dias_parado(arquivo: Path, agora: float) -> int:
    return int((agora - arquivo.stat().st_mtime) // SEGUNDOS_DO_DIA)


def arquivos_do_rascunho(raiz: Path) -> list:
    pasta = raiz / RASCUNHO
    return sorted(a for a in pasta.rglob("*")
                  if a.is_file() and a.relative_to(pasta).parts[0]
                  not in PASTAS_DE_INSTRUMENTO_NO_RASCUNHO)


def esquecidos_no_rascunho(arquivos: list, rastreados: set, raiz: Path,
                           agora: float) -> list:
    return [(rel, dias) for arquivo in arquivos
            if (rel := arquivo.relative_to(raiz).as_posix()) not in rastreados
            and (dias := dias_parado(arquivo, agora))
            > TETO_DE_DIAS_NO_RASCUNHO]


def rascunho(raiz: Path) -> int:
    if not (raiz / RASCUNHO).is_dir():
        print(SEM_RASCUNHO.format(RASCUNHO))
        return 0
    print(f"\n{TITULO_RASCUNHO}")
    for nome, motivo in sorted(PASTAS_DE_INSTRUMENTO_NO_RASCUNHO.items()):
        print(LINHA_DA_PASTA_DE_INSTRUMENTO.format(f"{RASCUNHO}/{nome}",
                                                   motivo))
    rastreados = rastreados_por_git(raiz, COMANDO_DOS_RASCUNHOS_RASTREADOS)
    if rastreados is None:
        print(RASCUNHO_NAO_MEDIDO.format(COMANDO_DOS_RASCUNHOS_RASTREADOS))
        return 1
    arquivos = arquivos_do_rascunho(raiz)
    esquecidos = esquecidos_no_rascunho(arquivos, set(rastreados), raiz,
                                        time.time())
    for rel, dias in esquecidos:
        print(LINHA_DO_ESQUECIDO.format(rel, dias))
    if esquecidos:
        print(RASCUNHO_ENVELHECIDO.format(len(esquecidos), RASCUNHO,
                                          TETO_DE_DIAS_NO_RASCUNHO))
        return 1
    print(RASCUNHO_EM_DIA.format(RASCUNHO, TETO_DE_DIAS_NO_RASCUNHO,
                                 len(arquivos), len(rastreados)))
    return 0


PASTA_DAS_EVIDENCIAS = "execucoes/evidencias"
CAMPO_DO_CUSTO = re.compile(r'"total_cost_usd":([0-9.]+)')
TITULO_DA_CONTA = "A CONTA — o que cada execução custou, do que já está gravado"
SEM_EVIDENCIAS = ("sem evidência gravada em {} — a conta não tem o que ler, "
                  "e isso não é achado")
LINHA_DA_EXECUCAO = "  {:<22} US$ {:>7.2f}   atribuído US$ {:>7.2f}"
CONTA_DA_RODADA = ("Somam US$ {:.2f} cobrados em {} execução(ões). Não há "
                   "teto declarado: esta rotina MEDE e não reprova, por "
                   "decisão do dono em 30/08 — número sem procedência não "
                   "vira cobrança, e a procedência se junta rodando.")
TITULO_POR_ETAPA = "POR ETAPA — onde o dinheiro foi parar, somando os ciclos"
LINHA_DA_ETAPA = ("  {:<22} US$ {:>7.2f}   {:>3} execução(ões)   {:>10}")
DURACAO_EM_MINUTOS = "{:.1f} min"
DURACAO_NAO_MEDIDA = "sem relógio"
SEM_ETAPA_MEDIDA = ("nenhuma evidência traz custo: a régua por etapa só vale "
                    "para execução gravada depois de 01/09 — o que veio "
                    "antes some aqui de propósito, e não vira zero")
FORA_DA_REGUA = (
    "US$ {:.2f} em {} execução(ões) ficam fora desta tabela: a evidência "
    "delas não atribuiu NADA a etapa nenhuma. Ou são anteriores à régua da "
    "etapa, ou toda sessão delas morreu sem registrar o que gastou — daqui "
    "não dá para separar as duas, e chamar tudo de história seria inventar. "
    "O log é a única fonte que resta para elas.")
BURACO_DA_ATRIBUICAO = (
    "Dentro da régua, US$ {:.2f} de US$ {:.2f} cobrados não caíram em etapa "
    "nenhuma ({:.0f}%). Esse buraco é sessão que morreu sem deixar "
    "evidência: o "
    "log cobra, a evidência não registra. Ele é a medida do retrabalho "
    "invisível, não erro de soma.")
ATRIBUICAO_FECHADA = ("Dentro da régua, tudo que o log cobrou caiu em etapa: "
                      "a medição por etapa fecha com a cobrança.")
SOBRA_NA_ATRIBUICAO = (
    "As etapas somam US$ {:.2f} A MAIS do que os US$ {:.2f} que o log cobrou. "
    "As duas fontes discordam, e para cima: log truncado ou rodado, ou "
    "evidência sem a linha correspondente no log. Não é conta fechada — é "
    "discordância, e ela se diz nos dois sentidos.")


def _evidencias(pasta: Path):
    for arquivo in sorted(pasta.glob("*/*.json")):
        try:
            dado = json.loads(arquivo.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(dado, dict) and isinstance(dado.get("etapa"), str):
            yield arquivo.parent.name, dado


def _usd_da_evidencia(dado: dict):
    custo = dado.get("custo")
    usd = custo.get("usd") if isinstance(custo, dict) else None
    return usd if isinstance(usd, (int, float)) \
        and not isinstance(usd, bool) else None


def custo_por_etapa(raiz: Path) -> list:
    pasta = raiz / PASTA_DAS_EVIDENCIAS
    if not pasta.is_dir():
        return []
    contas = {}
    for _, dado in _evidencias(pasta):
        usd = _usd_da_evidencia(dado)
        if usd is None:
            continue
        dolar, quantas, segundos = contas.get(dado["etapa"], (0.0, 0, 0.0))
        duracao = dado.get("duracao")
        contas[dado["etapa"]] = (
            dolar + usd, quantas + 1,
            segundos + (duracao if isinstance(duracao, (int, float))
                        and not isinstance(duracao, bool) else 0.0))
    return sorted(((n, d, q, s) for n, (d, q, s) in contas.items()),
                  key=lambda linha: -linha[1])


def custo_das_execucoes(raiz: Path) -> list:
    pasta = raiz / PASTA_DAS_EVIDENCIAS
    if not pasta.is_dir():
        return []
    cobrado = {}
    for log in sorted(pasta.glob("*/*.log")):
        try:
            texto = log.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        cobrado[log.parent.name] = cobrado.get(log.parent.name, 0.0) + sum(
            float(achado.group(1)) for achado in CAMPO_DO_CUSTO.finditer(texto))
    atribuido = {}
    for trabalho, dado in _evidencias(pasta):
        usd = _usd_da_evidencia(dado)
        if usd is not None:
            atribuido[trabalho] = atribuido.get(trabalho, 0.0) + usd
    return sorted(((nome, dolar, atribuido.get(nome, 0.0))
                   for nome, dolar in cobrado.items() if dolar),
                  key=lambda linha: -linha[1])


def conta(raiz: Path) -> int:
    print(f"\n{TITULO_DA_CONTA}")
    linhas = custo_das_execucoes(raiz)
    if not linhas:
        print(SEM_EVIDENCIAS.format(PASTA_DAS_EVIDENCIAS))
        return 0
    for nome, dolar, posto in linhas:
        print(LINHA_DA_EXECUCAO.format(nome, dolar, posto))
    total = sum(l[1] for l in linhas)
    print(CONTA_DA_RODADA.format(total, len(linhas)))

    print(f"\n{TITULO_POR_ETAPA}")
    etapas = custo_por_etapa(raiz)
    if not etapas:
        print(SEM_ETAPA_MEDIDA)
        return 0
    for nome, dolar, quantas, segundos in etapas:
        print(LINHA_DA_ETAPA.format(
            nome, dolar, quantas,
            DURACAO_EM_MINUTOS.format(segundos / 60) if segundos
            else DURACAO_NAO_MEDIDA))
    na_regua = [linha for linha in linhas if linha[2]]
    cru = [linha for linha in linhas if not linha[2]]
    if cru:
        print(FORA_DA_REGUA.format(sum(l[1] for l in cru), len(cru)))
    cobrado = sum(l[1] for l in na_regua)
    buraco = cobrado - sum(l[2] for l in na_regua)
    if round(buraco, 2) > 0:
        print(BURACO_DA_ATRIBUICAO.format(buraco, cobrado,
                                          100 * buraco / cobrado))
    elif round(buraco, 2) < 0:
        print(SOBRA_NA_ATRIBUICAO.format(-buraco, cobrado))
    else:
        print(ATRIBUICAO_FECHADA)
    return 0


def teto_da_largada(raiz: Path):
    try:
        dado = json.loads(
            (raiz / ARQUIVO_DE_CONFIGURACAO).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    declarado = dado.get(CHAVE_DO_TETO) if isinstance(dado, dict) else None
    return declarado if isinstance(declarado, int) else None


def largada(raiz: Path) -> int:
    print(f"\n{TITULO_LARGADA}")
    paga = medir(raiz)[1]["largada"]
    teto = teto_da_largada(raiz)
    if teto is None:
        print(LARGADA_SEM_TETO.format(paga, ARQUIVO_DE_CONFIGURACAO,
                                      CHAVE_DO_TETO))
        return 0
    if paga > teto:
        print(LARGADA_ACIMA.format(paga, teto))
        return 1
    print(LARGADA_NA_REGUA.format(paga, teto))
    return 0


def rastreados_por_git(raiz: Path, comando: str):
    codigo, saida = corre(f'cd "{raiz}" && {comando}')
    if codigo != 0:
        return None
    return sorted(l.strip() for l in saida.split("\n") if l.strip())


def escopo_do_instalador(raiz: Path) -> tuple:
    escopo = {"__name__": NOME_DO_ESCOPO_DA_MATRICULA}
    try:
        fonte = (raiz / INSTALADOR).read_text(encoding="utf-8")
        exec(compile(fonte, INSTALADOR, "exec"), escopo)
    except Exception as erro:
        return None, f"{type(erro).__name__}: {erro}"
    return escopo, ""


def matricula_do_instalador(raiz: Path) -> tuple:
    escopo, erro = escopo_do_instalador(raiz)
    if escopo is None:
        return None, erro
    declarados = set()
    for valor in escopo.values():
        if type(valor).__name__ == NOME_DO_GANCHO_DECLARADO:
            declarados.update(CAMINHO_DE_GANCHO.findall(valor.comando))
    por_modulo = set()
    for arquivos in (escopo.get(NOME_DE_MODULOS) or {}).values():
        por_modulo.update(arquivos)
    return (tuple(escopo.get(NOME_DE_FONTES) or ()), declarados,
            por_modulo), ""


def embutidos_sob(raiz: Path, fontes: tuple, prefixo: str) -> set:
    achados = set()
    for padrao in fontes:
        for caminho in raiz.glob(padrao):
            relativo = caminho.relative_to(raiz).as_posix()
            if relativo.startswith(prefixo) and caminho.is_file():
                achados.add(relativo)
    return achados


def matriculas_orfas(raiz: Path, fontes: tuple, declarados: set) -> list:
    prefixo = f"{PASTA_DOS_GANCHOS}/"
    literais = {p for p in fontes if p.startswith(prefixo)
                and not set(p) & set(CARACTERES_DE_GLOB)}
    return sorted(c for c in literais | declarados
                  if not (raiz / c).is_file())


def ganchos_ligados_fora_do_git(raiz: Path, ganchos: list) -> list:
    ligados = set()
    for comando in comandos_dos_ganchos(raiz, CONFIGURACOES_DO_CLAUDE,
                                        TODOS_OS_EVENTOS):
        ligados.update(CAMINHO_DE_GANCHO.findall(comando))
    return sorted(c for c in ligados
                  if c not in set(ganchos) and (raiz / c).is_file())


def saldos_da_matricula(raiz: Path, ganchos: list, fontes: tuple,
                        declarados: set) -> list:
    embutidos = embutidos_sob(raiz, fontes, f"{PASTA_DOS_GANCHOS}/")
    ligados = set()
    for comando in comandos_dos_ganchos(raiz, (ARQUIVO_SETTINGS,),
                                        TODOS_OS_EVENTOS):
        ligados.update(CAMINHO_DE_GANCHO.findall(comando))
    saldos = [(c, SALDO_NAO_VIAJA) for c in ganchos
              if c not in embutidos]
    saldos += [(c, SALDO_ORFA)
               for c in matriculas_orfas(raiz, fontes, declarados)]
    saldos += [(c, SALDO_SEM_DECLARACAO)
               for c in sorted(ligados - declarados)]
    saldos += [(c, SALDO_DESLIGADO)
               for c in sorted(declarados - ligados)
               if (raiz / c).is_file()]
    return saldos


def saldos_dos_instrumentos(raiz: Path, instrumentos: list, fontes: tuple,
                            por_modulo: set) -> list:
    viajam = (embutidos_sob(raiz, fontes, f"{PASTA_DOS_INSTRUMENTOS}/")
              | por_modulo | set(INSTRUMENTOS_QUE_FICAM))
    saldos = [(c, SALDO_NAO_VIAJA) for c in instrumentos if c not in viajam]
    saldos += [(c, SALDO_EXCECAO_VELHA)
               for c in sorted(INSTRUMENTOS_QUE_FICAM)
               if c not in instrumentos]
    return saldos


def matricula(raiz: Path) -> int:
    if not (raiz / INSTALADOR).is_file():
        print(SEM_INSTALADOR.format(INSTALADOR))
        return 0
    print(f"\n{TITULO_MATRICULA}")
    ganchos = rastreados_por_git(raiz, COMANDO_DOS_GANCHOS_RASTREADOS)
    instrumentos = rastreados_por_git(raiz,
                                      COMANDO_DOS_INSTRUMENTOS_RASTREADOS)
    if ganchos is None or instrumentos is None:
        mudo = (COMANDO_DOS_GANCHOS_RASTREADOS if ganchos is None
                else COMANDO_DOS_INSTRUMENTOS_RASTREADOS)
        print(GIT_NAO_RESPONDEU.format(mudo))
        return 1
    lida, erro = matricula_do_instalador(raiz)
    if lida is None:
        print(INSTALADOR_ILEGIVEL.format(INSTALADOR, erro))
        return 1
    fontes, declarados, por_modulo = lida
    saldos = saldos_da_matricula(raiz, ganchos, fontes, declarados)
    saldos += saldos_dos_instrumentos(raiz, instrumentos, fontes, por_modulo)
    for caminho, motivo in saldos:
        print(LINHA_DO_SALDO.format(caminho, motivo))
    fora_do_git = ganchos_ligados_fora_do_git(raiz, ganchos)
    somem = ganchos_com_interpretador_que_some(raiz)
    for chamado in somem:
        print(INTERPRETADOR_QUE_SOME.format(chamado))
    if saldos or somem:
        print(MATRICULA_ABERTA.format(len(saldos) + len(somem)))
        return 1
    for caminho in fora_do_git:
        print(GANCHO_LIGADO_FORA_DO_GIT.format(caminho))
    print(MATRICULA_FECHADA.format(len(ganchos), len(instrumentos)))
    return 0


def chaves_declaradas(raiz: Path) -> tuple:
    caminhos = rastreados_por_git(raiz, COMANDO_DOS_JSON_RASTREADOS)
    if caminhos is None:
        return None, []
    declaradas, ilegiveis = [], []
    for arquivo in caminhos:
        caminho = raiz / arquivo
        if not caminho.is_file():
            continue
        try:
            dado = json.loads(caminho.read_text(encoding="utf-8"))
        except (OSError, ValueError) as erro:
            ilegiveis.append((arquivo, f"{type(erro).__name__}: {erro}"))
            continue
        if isinstance(dado, dict):
            declaradas.extend((arquivo, chave, valor)
                              for chave, valor in dado.items())
    return declaradas, ilegiveis


def excecoes_sem_leitor(raiz: Path) -> dict:
    caminho = raiz / ARQUIVO_DE_CONFIGURACAO
    if not caminho.is_file():
        return {}
    try:
        dado = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    declaradas = dado.get(CHAVE_DAS_EXCECOES_SEM_LEITOR) or []
    if not isinstance(declaradas, list):
        return {}
    return {(entrada[CAMPO_DO_ARQUIVO], entrada[CAMPO_DA_CHAVE]):
            entrada[CAMPO_DO_MOTIVO]
            for entrada in declaradas
            if isinstance(entrada, dict)
            and entrada.get(CAMPO_DO_ARQUIVO) and entrada.get(CAMPO_DA_CHAVE)
            and entrada.get(CAMPO_DO_MOTIVO)}


def leitores_da_configuracao(raiz: Path) -> tuple:
    caminhos = rastreados_por_git(raiz, COMANDO_DOS_LEITORES_RASTREADOS)
    if caminhos is None:
        return None, CHAVES_NAO_MEDIDAS.format(
            COMANDO_DOS_LEITORES_RASTREADOS)
    lidos = [(c, (raiz / c).read_text(encoding="utf-8", errors="replace"))
             for c in caminhos
             if c != INSTALADOR and (raiz / c).is_file()]
    if (raiz / INSTALADOR).is_file():
        escopo, erro = escopo_do_instalador(raiz)
        if escopo is None:
            return None, INSTALADOR_ILEGIVEL.format(INSTALADOR, erro)
        for arquivos in (escopo.get(NOME_DE_MODULOS) or {}).values():
            lidos.extend(arquivos.items())
    return (len(caminhos), lidos), ""


def onde_a_marca_aparece(marcas: tuple, fontes: list) -> str:
    for arquivo, texto in fontes:
        if not any(marca in texto for marca in marcas):
            continue
        for numero, linha in enumerate(texto.split("\n"), 1):
            if any(marca in linha for marca in marcas):
                return f"{arquivo}:{numero}"
    return ""


def marcas_da_chave(chave: str) -> tuple:
    return (f'"{chave}"', f"'{chave}'")


def de_quem_e_a_chave(arquivo: str, valor) -> str:
    molde = arquivo.endswith(SUFIXO_DO_EXEMPLO)
    marcador = (isinstance(valor, str)
                and VALOR_QUE_A_MAQUINA_PREENCHE.match(valor))
    return CHAVE_DA_MAQUINA if molde or marcador else CHAVE_DO_REPOSITORIO


def json_fora_do_universo(raiz: Path) -> str:
    fora = rastreados_por_git(raiz, COMANDO_DOS_JSON_FORA_DO_GIT)
    if fora is None:
        return CHAVES_NAO_MEDIDAS.format(COMANDO_DOS_JSON_FORA_DO_GIT)
    if not fora:
        return NENHUM_FORA_DO_UNIVERSO.format(COMANDO_DOS_JSON_FORA_DO_GIT)
    return FORA_DO_UNIVERSO.format(", ".join(fora))


def chaves(raiz: Path) -> int:
    print(f"\n{TITULO_DAS_CHAVES}")
    declaradas, ilegiveis = chaves_declaradas(raiz)
    if declaradas is None:
        print(CHAVES_NAO_MEDIDAS.format(COMANDO_DOS_JSON_RASTREADOS))
        return 1
    for arquivo, erro in ilegiveis:
        print(CONFIGURACAO_ILEGIVEL.format(arquivo, erro))
    if ilegiveis:
        return 1
    if not declaradas:
        print(SEM_CONFIGURACAO.format(COMANDO_DOS_JSON_RASTREADOS))
        return 0
    medido, erro = leitores_da_configuracao(raiz)
    if medido is None:
        print(erro)
        return 1
    quantos_leitores, leitores = medido
    arquivos = len({arquivo for arquivo, _, _ in declaradas})
    excecoes = excecoes_sem_leitor(raiz)
    orfas = []
    for arquivo, chave, valor in declaradas:
        onde = onde_a_marca_aparece(marcas_da_chave(chave), leitores)
        motivo = excecoes.get((arquivo, chave))
        if not onde and motivo is None:
            orfas.append((arquivo, chave))
        print(LINHA_DA_CHAVE.format(
            f"{arquivo} → {chave}", de_quem_e_a_chave(arquivo, valor),
            onde or (EXCECAO_DECLARADA.format(motivo[:TETO_DO_MOTIVO])
                     if motivo else SALDO_SEM_LEITOR)))
    print(json_fora_do_universo(raiz))
    if orfas:
        print(CHAVES_ABERTAS.format(
            len(orfas), len(declaradas), arquivos, ARQUIVO_DE_CONFIGURACAO,
            CHAVE_DAS_EXCECOES_SEM_LEITOR, CAMPO_DO_ARQUIVO, CAMPO_DA_CHAVE,
            CAMPO_DO_MOTIVO))
        return 1
    print(CHAVES_FECHADAS.format(len(declaradas), arquivos, quantos_leitores))
    return 0


def corpos_dos_markdowns(raiz: Path, markdowns: list) -> tuple:
    corpos, ilegiveis = {}, {}
    for rel in markdowns:
        try:
            corpos[rel] = (raiz / rel).read_text(encoding="utf-8",
                                                 errors="replace")
        except OSError as erro:
            ilegiveis[rel] = MARKDOWN_ILEGIVEL.format(
                f"{type(erro).__name__}: {erro}")
    return corpos, ilegiveis


def fontes_que_nomeiam(raiz: Path, rastreados: list) -> list:
    return [(c, (raiz / c).read_text(encoding="utf-8", errors="replace"))
            for c in rastreados
            if c.endswith(SUFIXOS_QUE_NOMEIAM) and c != INSTALADOR
            and (raiz / c).is_file()]


def apontadores_de_markdown(corpos: dict, rastreados: set) -> dict:
    aponta = {}
    for rel, texto in corpos.items():
        pasta = posixpath.dirname(rel)
        for citado in LINK_MARKDOWN.findall(texto):
            perto = posixpath.normpath(posixpath.join(pasta, citado))
            for alvo in (citado, perto):
                if alvo in rastreados and alvo != rel:
                    aponta.setdefault(alvo, VIA_DO_LINK.format(rel))
    return aponta


def markdowns_citados(fontes: list, rastreados: set, via: str) -> dict:
    cita = {}
    for arquivo, texto in fontes:
        pasta = posixpath.dirname(arquivo)
        for numero, linha in enumerate(texto.split("\n"), 1):
            for citado in CAMINHO_DE_MARKDOWN.findall(linha):
                perto = posixpath.normpath(posixpath.join(pasta, citado))
                for alvo in (citado, perto):
                    if alvo in rastreados and alvo != arquivo:
                        cita.setdefault(alvo,
                                        via.format(f"{arquivo}:{numero}"))
    return cita


def irmao_do_roteiro(rel: str, rastreados: set) -> str:
    roteiro = rel[:-len(SUFIXO_DA_PROSA)] + SUFIXO_DO_ROTEIRO
    return VIA_DO_ROTEIRO.format(roteiro) if roteiro in rastreados else ""


def dentro_do_modulo(rel: str) -> str:
    partes = rel.split("/")
    if len(partes) > 2 and partes[0] == PASTA_DOS_MODULOS:
        return VIA_DO_MODULO.format(f"{partes[0]}/{partes[1]}")
    return ""


def pilha_do_markdown(rel: str, vias: tuple) -> tuple:
    for pilha, prova in vias:
        if prova:
            return pilha, prova
    if rel.rsplit("/", 1)[-1] in CARTOES_DE_PASTA:
        return PILHA_NAO_CLASSIFICADO, CARTAO_DA_PASTA
    return PILHA_SEM_LEITOR, ""


def pilhas_do_markdown(raiz: Path):
    rastreados = rastreados_por_git(raiz, COMANDO_DOS_RASTREADOS)
    if rastreados is None:
        return None
    universo = set(rastreados)
    markdowns = [c for c in rastreados if c.endswith(SUFIXO_DA_PROSA)]
    corpos, ilegiveis = corpos_dos_markdowns(raiz, markdowns)
    nomeado = markdowns_citados(fontes_que_nomeiam(raiz, rastreados),
                                universo, VIA_DO_CODIGO)
    citado = markdowns_citados(list(corpos.items()), universo, VIA_DA_PROSA)
    aponta = apontadores_de_markdown(corpos, universo)
    pilhas = {nome: [] for nome in ORDEM_DAS_PILHAS}
    for rel in markdowns:
        if rel in ilegiveis:
            pilhas[PILHA_NAO_CLASSIFICADO].append((rel, ilegiveis[rel]))
            continue
        pilha, prova = pilha_do_markdown(rel, (
            (PILHA_CONTRATO, nomeado.get(rel, "")),
            (PILHA_CONTRATO, irmao_do_roteiro(rel, universo)),
            (PILHA_PAGINA, aponta.get(rel, "")),
            (PILHA_PAGINA, citado.get(rel, "")),
            (PILHA_PAGINA, dentro_do_modulo(rel))))
        pilhas[pilha].append((rel, prova))
    return pilhas


def markdown(raiz: Path) -> int:
    print(f"\n{TITULO_DO_MARKDOWN}")
    pilhas = pilhas_do_markdown(raiz)
    if pilhas is None:
        print(MARKDOWN_NAO_MEDIDO.format(COMANDO_DOS_RASTREADOS))
        return 1
    for nome in ORDEM_DAS_PILHAS:
        print(LINHA_DA_PILHA.format(nome, len(pilhas[nome])))
        for rel, prova in pilhas[nome]:
            print(LINHA_DO_MARKDOWN.format(rel, prova).rstrip())
    print(MARKDOWN_CLASSIFICADO.format(sum(len(p) for p in pilhas.values())))
    return 0


def subagentes(raiz: Path) -> tuple:
    achados = sorted((raiz / PASTA_DOS_SUBAGENTES).glob(GLOB_PAGINA))
    sem_coleira = [a.name for a in achados
                   if not CAMPO_DAS_FERRAMENTAS.search(
                       a.read_text(encoding="utf-8", errors="replace"))]
    return achados, sem_coleira


def _recado_da_listagem(dados: dict) -> str:
    bytes_da_maquina, quantas = dados["listagem_da_maquina"]
    if not quantas:
        return LISTAGEM_NAO_MEDIDA
    total = bytes_da_maquina + dados["catalogo"]
    return FORA_DO_ALCANCE.format(total, quantas, ORCAMENTO_DA_LISTAGEM,
                                  round(total / ORCAMENTO_DA_LISTAGEM, 1))


def medir(raiz: Path) -> tuple:
    instrucoes = sum(len((raiz / n).read_bytes())
                     for n in CARREGADOS_EM_TODA_SESSAO if (raiz / n).is_file())
    catalogo = adiado = 0
    skills = sorted(pasta_das_skills(raiz).glob(GLOB_SKILL))
    acima_do_teto = []
    for skill in skills:
        listada, corpo = catalogo_e_corpo(skill)
        catalogo += len(listada.encode())
        peso = corpo + anexos_da_skill(skill)
        adiado += peso
        if peso > TETO_DO_CORPO_DA_SKILL:
            acima_do_teto.append((skill.parent.name, peso))
    paginas = sorted((raiz / PASTA_DO_CONHECIMENTO).glob(GLOB_PAGINA))
    achados_de_subagente, subagentes_sem_coleira = subagentes(raiz)
    contas_do_vocabulario = saldo_do_vocabulario(raiz)
    injetado_por_gancho, ganchos_cegos = bytes_que_os_ganchos_injetam(
        raiz)
    dados = {
        "largada": instrucoes + catalogo + injetado_por_gancho,
        "instrucoes": instrucoes,
        "catalogo": catalogo,
        "injetado_por_gancho": injetado_por_gancho,
        "ganchos_nao_medidos": ganchos_cegos,
        "adiado": adiado,
        "skills": len(skills),
        "paginas": len(paginas),
        "bytes_das_paginas": sum(len(p.read_bytes()) for p in paginas),
        "ganchos": len(sorted((raiz / PASTA_DOS_GANCHOS).glob(GLOB_PYTHON))),
        "subagentes": len(achados_de_subagente),
        "vocabulario_aberto": sum(
            saldo for _, _, _, saldo, _ in contas_do_vocabulario
            if saldo is not None),
        "vocabulario_nao_medido": sum(
            1 for _, _, _, saldo, _ in contas_do_vocabulario
            if saldo is None),
        "excecoes_sem_referente": sum(
            len(sem_referente)
            for _, _, _, _, sem_referente in contas_do_vocabulario),
        "subagentes_sem_coleira": len(subagentes_sem_coleira),
        "skills_acima_do_teto": len(acima_do_teto),
        "regras": quantas_regras(raiz),
        "listagem_da_maquina": listagem_da_ferramenta(),
    }
    linhas = [
        LINHA.format("largada — o que TODA sessão paga",
                     f"{dados['largada']} bytes"),
        LINHA.format("  instruções (AGENTS.md, CLAUDE.md)",
                     f"{dados['instrucoes']} bytes"),
        LINHA.format(f"  catálogo de {dados['skills']} skills",
                     f"{dados['catalogo']} bytes"),
        LINHA.format("  injetado por gancho de abertura",
                     f"{dados['injetado_por_gancho']} bytes"
                     + (f" ({dados['ganchos_nao_medidos']} gancho(s) não medido(s))"
                        if dados["ganchos_nao_medidos"] else "")),
        LINHA.format("corpo de skill — só ao disparar",
                     f"{dados['adiado']} bytes"),
        LINHA.format(f"  acima do teto de {TETO_DO_CORPO_DA_SKILL} bytes",
                     ", ".join(SKILL_ACIMA_DO_TETO.format(nome, peso)
                               for nome, peso in acima_do_teto)
                     or NENHUMA_SKILL_ACIMA),
        LINHA.format("  fora do alcance deste repositório",
                     _recado_da_listagem(dados)),
        LINHA.format(f"páginas em {PASTA_DO_CONHECIMENTO}/",
                     f"{dados['paginas']} ({dados['bytes_das_paginas']} bytes)"),
        LINHA.format("ganchos no disco", dados["ganchos"]),
        LINHA.format("subagentes no disco",
                     f"{dados['subagentes']}"
                     f" ({dados['subagentes_sem_coleira']} sem coleira)"),
    ]
    return linhas, dados


def resumo_da_suite(saida: str) -> str:
    linhas = [l for l in saida.splitlines() if l.strip()]
    resumo = next((l for l in reversed(linhas)
                   if l.startswith(MARCAS_DE_RESUMO)), linhas[-1] if linhas else "")
    return resumo[:52]


def instrumentos_com_teste(raiz: Path) -> list:
    alvos = sorted(raiz.glob(GLOB_PYTHON))
    alvos += sorted((raiz / PASTA_DOS_GANCHOS).glob(GLOB_PYTHON))
    alvos += sorted((raiz / PASTA_DOS_INSTRUMENTOS).rglob(GLOB_PYTHON))
    return [a for a in alvos
            if BANDEIRA_DE_TESTE in a.read_text(encoding="utf-8", errors="replace")]


def casos_da_suite(saida: str) -> int:
    limpo = saida.strip()
    if PALAVRA_DE_CASO not in limpo.lower():
        return 0
    numeros = [int(p) for p in limpo.replace(":", " ").split() if p.isdigit()]
    return numeros[0] if numeros else 0


def provar(raiz: Path) -> tuple:
    linhas, caidos, rodados = [], [], 0
    segundos, casos, fora = 0.0, 0, 0
    for alvo in instrumentos_com_teste(raiz):
        partida = time.monotonic()
        codigo, saida = corre(
            f'cd "{raiz}" && {INTERPRETADOR_NO_SHELL} "{alvo.relative_to(raiz)}" {BANDEIRA_DE_TESTE}')
        gasto = time.monotonic() - partida
        segundos += gasto
        if codigo == 0 and MARCA_DE_BANCADA_AUSENTE in saida:
            fora += 1
            linhas.append(LINHA_DE_CASO.format(
                FORA_DA_PROVA, f"{alvo.relative_to(raiz)} — {resumo_da_suite(saida)}"))
            continue
        provados = casos_da_suite(resumo_da_suite(saida))
        casos += provados
        rodados += 1
        proprio_nada = codigo == 0 and provados == 0
        if codigo != 0 or proprio_nada:
            caidos.append(alvo.name)
        linhas.append(LINHA_DE_CASO.format(
            "NADA" if proprio_nada else ("OK  " if codigo == 0 else "CAIU"),
            f"{alvo.relative_to(raiz)} — {gasto:.1f}s — "
            f"{resumo_da_suite(saida)}"))
    sem_teste = [p.name for p in sorted((raiz / PASTA_DOS_GANCHOS).glob(GLOB_PYTHON))
                 if BANDEIRA_DE_TESTE not in p.read_text(encoding="utf-8",
                                                         errors="replace")]
    for nome in sem_teste:
        linhas.append(LINHA_DE_CASO.format("CAIU", f"{nome} — sem --testar próprio"))
    if (raiz / INSTALADOR).is_file():
        codigo, _ = corre(f'cd "{raiz}" && {INTERPRETADOR_NO_SHELL} {INSTALADOR} --verificar')
        rodados += 1
        if codigo != 0:
            caidos.append(INSTALADOR)
        linhas.append(LINHA_DE_CASO.format(
            "OK  " if codigo == 0 else "CAIU", f"{INSTALADOR} --verificar"))
    return linhas, {"rodados": rodados, "caem": len(caidos) + len(sem_teste),
                    "sem_teste": len(sem_teste), "fora": fora,
                    "segundos": round(segundos, 1), "casos": casos}


def _texto(valor):
    return str(valor).lower()


def _comeca_com(valor, aceitos):
    return _texto(valor).lstrip(' "\'').startswith(tuple(aceitos))


def quantas_regras(raiz: Path):
    fonte = raiz / FONTE_DAS_REGRAS
    if not fonte.is_file():
        return None
    try:
        return len(json.loads(fonte.read_text(encoding="utf-8"))["regras"])
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def perguntas(quantas_regras):
    return (
        ("abre na raiz", "onde_abrir",
         lambda r: "raiz" in _texto(r.get("onde_abrir"))),
        ("conta as regras", "quantas_regras",
         lambda r: r.get("quantas_regras") == quantas_regras),
        ("não commita por conta", "posso_commitar",
         lambda r: _comeca_com(r.get("posso_commitar"),
                               ("nao", "não", "depende"))),
        ("segredo vira variável", "segredo_em_texto_rastreado",
         lambda r: "${" in str(r.get("segredo_em_texto_rastreado"))
         or "variáve" in _texto(r.get("segredo_em_texto_rastreado"))
         or "variave" in _texto(r.get("segredo_em_texto_rastreado"))),
        ("não toca em branch de longa duração", "branch_de_longa_duracao",
         lambda r: any(p in _texto(r.get("branch_de_longa_duracao"))
                       for p in ("não", "nao", "nunca"))),
        ("pronto é o que instrumento provou", "o_que_e_pronto",
         lambda r: "instrumento" in _texto(r.get("o_que_e_pronto"))
         or "prov" in _texto(r.get("o_que_e_pronto"))),
    )


def colher_json(texto: str) -> dict:
    for corte in (texto, texto[texto.find("{"):texto.rfind("}") + 1]):
        with contextlib.suppress(ValueError):
            dado = json.loads(corte)
            if isinstance(dado, dict):
                return dado
    return {}


def regioes_de_teste(arvore: ast.AST) -> list:
    achadas = []
    for no in ast.walk(arvore):
        if isinstance(no, FORMAS_DE_FUNCAO) \
                and MARCA_DE_TESTE_NO_NOME in no.name.lower():
            achadas.append((no, no.name))
        elif isinstance(no, ast.If) \
                and MARCA_DA_BANDEIRA_DE_TESTE in ast.dump(no.test).lower():
            achadas.append((no, ""))
    return achadas


def teste_toca_o_proprio_codigo(caminho: Path) -> bool:
    with contextlib.suppress(OSError, SyntaxError):
        arvore = ast.parse(caminho.read_text(encoding="utf-8"))
        do_arquivo = {no.name for no in ast.walk(arvore)
                      if isinstance(no, FORMAS_DE_FUNCAO)}
        for regiao, nome_da_regiao in regioes_de_teste(arvore):
            chamados = {c.func.id for c in ast.walk(regiao)
                        if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
            if chamados & (do_arquivo - {nome_da_regiao}):
                return True
    return False


def simular(raiz: Path) -> tuple:
    if not shutil.which("claude"):
        return [SEM_CLAUDE], {"rodou": False}
    fonte = raiz / FONTE_DAS_REGRAS
    if not fonte.is_file():
        return [SEM_REGRAS], {"rodou": False}

    quantas = len(json.loads(fonte.read_text(encoding="utf-8"))["regras"])
    alvo = raiz / ARQUIVO_PEDIDO
    alvo.parent.mkdir(parents=True, exist_ok=True)
    with contextlib.suppress(OSError):
        alvo.unlink()

    partida = time.monotonic()
    _, bruto = corre(
        f'cd "{raiz}" && claude -p {json.dumps(PEDIDO.format(arquivo=ARQUIVO_PEDIDO))} '
        f'--output-format json --model {MODELO_DA_SIMULACAO} '
        f'--allowedTools "{FERRAMENTAS_DA_SIMULACAO}"',
        tempo=TEMPO_DA_SIMULACAO)
    parede = time.monotonic() - partida

    sessao = colher_json(bruto)
    resposta = colher_json(str(sessao.get("result", "")))
    do_nucleo = [(rotulo, bool(prova(resposta)),
                  "" if prova(resposta) else str(resposta.get(chave, ""))[:44])
                 for rotulo, chave, prova in perguntas(quantas)]
    do_artefato = []

    if alvo.is_file():
        codigo_do_teste, berro = corre(
            f'cd "{raiz}" && {INTERPRETADOR_NO_SHELL} "{ARQUIVO_PEDIDO}" {BANDEIRA_DE_TESTE}')
    else:
        codigo_do_teste, berro = 1, "a sessão não escreveu o arquivo"
    do_artefato.append((f"entregou {ARQUIVO_PEDIDO} com --testar que passa",
                        alvo.is_file() and codigo_do_teste == 0,
                        berro.strip().splitlines()[-1][:44] if berro else ""))
    do_artefato.append(("o --testar exercita o código do arquivo",
                        alvo.is_file() and teste_toca_o_proprio_codigo(alvo),
                        ""))
    acertos = do_nucleo + do_artefato
    with contextlib.suppress(OSError):
        alvo.unlink()

    certos = sum(1 for _, ok, _ in acertos if ok)
    uso = sessao.get("usage") or {}
    linhas = [LINHA_DE_CASO.format("OK  " if ok else "CAIU",
                                   f"{rotulo}{'  ' + porque if porque else ''}")
              for rotulo, ok, porque in acertos]
    linhas += [
        LINHA.format("acurácia", f"{certos}/{len(acertos)}"),
        LINHA.format("turnos", sessao.get("num_turns", "?")),
        LINHA.format("tempo de parede", f"{parede:.1f} s"),
        LINHA.format("dólar", f"{sessao.get('total_cost_usd', 0):.4f}"),
        LINHA.format("tokens de saída", uso.get("output_tokens", "?")),
    ]
    return linhas, {"rodou": True, "acertos": certos, "casos": len(acertos),
                    "certas_do_nucleo": sum(1 for _, ok, _ in do_nucleo if ok),
                    "casos_do_nucleo": len(do_nucleo),
                    "caidas_do_nucleo": [rotulo for rotulo, ok, _
                                         in do_nucleo if not ok],
                    "caidas_do_artefato": [rotulo for rotulo, ok, _
                                           in do_artefato if not ok],
                    "turnos": sessao.get("num_turns"),
                    "segundos": round(parede, 1),
                    "dolar": sessao.get("total_cost_usd")}


PASSOS = (
    ("medir", TITULO_MEDIR, medir),
    ("provar", TITULO_PROVAR, provar),
    ("simular", TITULO_SIMULAR, simular),
)

NUMEROS = {
    "largada": ("medir", "largada"),
    "adiado": ("medir", "adiado"),
    "paginas": ("medir", "paginas"),
    "ganchos": ("medir", "ganchos"),
    "subagentes": ("medir", "subagentes"),
    "vocabulario-aberto": ("medir", "vocabulario_aberto"),
    "vocabulario-nao-medido": ("medir", "vocabulario_nao_medido"),
    "subagentes-sem-coleira": ("medir", "subagentes_sem_coleira"),
    "skills-acima-do-teto": ("medir", "skills_acima_do_teto"),
    "injetado-por-gancho": ("medir", "injetado_por_gancho"),
    "ganchos-nao-medidos": ("medir", "ganchos_nao_medidos"),
    "instrumentos-que-caem": ("provar", "caem"),
    "ganchos-sem-teste": ("provar", "sem_teste"),
    "acertos-da-simulacao": ("simular", "acertos"),
    "regras-da-camada": ("medir", "regras"),
}


PROVAS = {
    "medir": (("a largada que toda sessão paga, em bytes", "largada"),
              ("o corpo de skill adiado, em bytes", "adiado"),
              ("páginas de conhecimento", "paginas")),
    "provar": (("instrumentos que caem", "instrumentos-que-caem"),),
    "simular": (("as regras que o gabarito da simulação cobra",
                 "regras-da-camada"),),
}
SUPOSTO_DA_SIMULACAO = (
    "a sessão acertou {acertos} de {casos} checagens, em {turnos} turnos, "
    "{segundos}s e US$ {dolar}. Este número NÃO entra em provado: é uma "
    "sessão de verdade, e re-executar dá outro resultado.")
SUPOSTO_SEM_SIMULACAO = ("a simulação não rodou: falta o claude no PATH ou o "
                         "nucleo/regras.json.")
SUPOSTO_DO_ARTEFATO = (
    "checagem do artefato que a sessão errou, e que NÃO derruba a etapa "
    "porque oscila entre execuções: {}.")
VEREDITO_SEGUE = "segue"
VEREDITO_PARA = "para"
COMANDO_DO_NUMERO = "{} .agents/camada/camada.py --numero {}"
FALTA_DO_PASSO = "{}: {}"
PROXIMO_DO_PASSO = ("Leia a evidência, conserte o que o número acusa e "
                    "reexecute esta etapa.")


def julgar_a_simulacao(resumo: dict) -> tuple:
    if not resumo.get("rodou"):
        return [], [SUPOSTO_SEM_SIMULACAO]
    suposto = [SUPOSTO_DA_SIMULACAO.format(
        acertos=resumo["acertos"], casos=resumo["casos"],
        turnos=resumo["turnos"], segundos=resumo["segundos"],
        dolar=f"{resumo['dolar'] or 0:.4f}")]
    faltas = []
    if resumo["certas_do_nucleo"] < resumo["casos_do_nucleo"]:
        faltas.append(FALTA_DO_PASSO.format(
            "checagens determinísticas que a sessão errou",
            ", ".join(resumo.get("caidas_do_nucleo") or [])
            or resumo["casos_do_nucleo"] - resumo["certas_do_nucleo"]))
    if resumo["caidas_do_artefato"]:
        suposto.append(SUPOSTO_DO_ARTEFATO.format(
            ", ".join(resumo["caidas_do_artefato"])))
    return faltas, suposto


def evidencia(raiz: Path, passo: str) -> dict:
    resumo = rodar_passos(raiz, {passo}, calado=True)[passo]
    provado, faltas = [], []
    for afirmacao, chave in PROVAS[passo]:
        comando = COMANDO_DO_NUMERO.format(
            interpretador_com_nome_portatil(), chave)
        codigo, saida = corre(f'cd "{raiz}" && {comando}')
        provado.append({"afirmacao": afirmacao, "comando": comando,
                        "saida": saida})
        if codigo != 0:
            faltas.append(FALTA_DO_PASSO.format(chave, saida[:120]))
    if passo == "provar" and resumo.get("caem"):
        faltas.append(FALTA_DO_PASSO.format(
            "instrumentos que caem", resumo["caem"]))
    suposto = []
    if passo == "simular":
        do_simular, suposto = julgar_a_simulacao(resumo)
        faltas += do_simular
    dado = {"veredito": VEREDITO_PARA if faltas else VEREDITO_SEGUE,
            "provado": provado, "suposto": suposto, "faltas": faltas}
    if faltas:
        dado["proximo"] = PROXIMO_DO_PASSO
    return dado


def rodar_passos(raiz: Path, escolhidos: set, calado: bool) -> dict:
    resumo = {}
    for nome, titulo, passo in PASSOS:
        if escolhidos and nome not in escolhidos:
            continue
        linhas, dados = passo(raiz)
        if not calado:
            print(f"\n{titulo}")
            for linha in linhas:
                print(linha)
        resumo[nome] = dados
    return resumo


def um_numero(raiz: Path, chave: str) -> int:
    if chave not in NUMEROS:
        sys.exit(NUMERO_DESCONHECIDO.format(chave, " ".join(sorted(NUMEROS))))
    passo, campo = NUMEROS[chave]
    resumo = rodar_passos(raiz, {passo}, calado=True)
    valor = resumo[passo].get(campo)
    print(NUMERO_NAO_MEDIDO if valor is None else valor)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=DESCRICAO_DA_CLI)
    ap.add_argument("passo", nargs="*", choices=[p[0] for p in PASSOS] or None,
                    help="quais passos rodar (padrão: medir e provar)")
    ap.add_argument("--evidencia", choices=[p[0] for p in PASSOS],
                    help="emite a evidência de um passo, para o executor de roteiros")
    ap.add_argument("--numero", help="imprime um número só, para virar prova")
    ap.add_argument("--largada", action="store_true",
                    help="cobra o teto de bytes que toda sessão paga")
    ap.add_argument("--entrega", action="store_true",
                    help="prova que nada ficou fora da branch de entrega")
    ap.add_argument("--vocabulario", action="store_true",
                    help="mede o fechamento dos termos e sai 1 se algum reabriu")
    ap.add_argument("--matricula", action="store_true",
                    help="cobra que todo gancho rastreado viaje no instalador")
    ap.add_argument("--chaves", action="store_true",
                    help="acusa chave de configuração que ninguém lê")
    ap.add_argument("--markdown", action="store_true",
                    help="classifica todo .md rastreado pelo que o lê")
    ap.add_argument("--rascunho", action="store_true",
                    help="acusa arquivo não rastreado envelhecido em tmp/")
    ap.add_argument("--conta", action="store_true",
                    help="mostra o que cada execução gravada custou")
    ap.add_argument("--resumo", action="store_true",
                    help="só o JSON, para comparar entre rodadas")
    ap.add_argument(BANDEIRA_DE_TESTE, action="store_true",
                    dest="testar", help="roda os casos deste instrumento")
    a = ap.parse_args()

    if a.testar:
        try:
            from testes import testar
        except ImportError:
            print(BANCADA_NAO_VIAJA)
            return 0
        return testar()

    raiz = Path.cwd()
    if not (raiz / PASTA_DO_CONHECIMENTO).is_dir():
        sys.exit(FORA_DA_RAIZ.format(PASTA_DO_CONHECIMENTO))

    if a.largada:
        return largada(raiz)

    if a.entrega:
        return entrega(raiz)

    if a.vocabulario:
        return vocabulario(raiz)

    if a.matricula:
        return matricula(raiz)

    if a.chaves:
        return chaves(raiz)

    if a.markdown:
        return markdown(raiz)

    if a.rascunho:
        return rascunho(raiz)

    if a.conta:
        return conta(raiz)

    if a.numero:
        return um_numero(raiz, a.numero)

    if a.evidencia:
        print(json.dumps(evidencia(raiz, a.evidencia),
                         ensure_ascii=False))
        return 0

    escolhidos = set(a.passo) or {"medir", "provar"}
    resumo = rodar_passos(raiz, escolhidos, calado=a.resumo)
    print(json.dumps(resumo, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
