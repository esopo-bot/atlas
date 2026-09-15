import argparse
import ast
import contextlib
import fnmatch
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
VARIAVEL_DA_RAIZ_NO_AMBIENTE = "CLAUDE_PROJECT_DIR"
ENTRADA_VAZIA_DO_GANCHO = "{}"
TEMPO_DE_UM_GANCHO = 30
PASTA_DAS_SKILLS = ".claude/skills"
PASTA_DAS_SKILLS_FONTE = ".agents/skills"
PASTA_DOS_GANCHOS = ".claude/hooks"
PASTA_DE_REGRAS = ".claude/rules"
MARCA_DE_REGRA_POR_CAMINHO = re.compile(r"^paths:", re.M)
PASTA_DOS_SUBAGENTES = ".claude/agents"
PASTA_DOS_INSTRUMENTOS = ".agents"
PASTA_DO_CONHECIMENTO = "conhecimento"
INSTALADOR = "montar.py"
INTERPRETADOR = sys.executable
INTERPRETADOR_NO_SHELL = f'"{sys.executable}"'
ARQUIVO_DO_LANCADOR = ".claude/hooks/interpretador.sh"
SHELL_DO_LANCADOR = "bash"
LINHA_DOS_CANDIDATOS = re.compile(r'^CANDIDATOS="([^"]*)"', re.M)
PERGUNTA_DA_VERSAO = "import sys; print(sys.version_info[0])"
VERSAO_QUE_SERVE = "3"
TETO_DO_INTERPRETADOR_S = 10
FONTE_DAS_REGRAS = "nucleo/regras.json"
TITULO_ENTREGA = "A ENTREGA — o que ainda não saiu da máquina"
TITULO_LARGADA = "A LARGADA — o que toda sessão paga antes de trabalhar"
TITULO_DAS_MEDIDAS = ("AS MEDIDAS DA VERSÃO — três; a versão nova é melhor "
                 "quando nenhuma piora além do ruído e uma melhora")
VERSAO_NO_INSTALADOR = re.compile(r'^VERSAO\s*=\s*"([^"]+)"', re.M)
LINHA_DA_MEDIDA = "  {:<18} {}"
MEDIDA_VERSAO = "versão"
MEDIDA_LARGADA = "largada"
MEDIDA_CUSTO = "custo por entrega"
MEDIDA_ROTA = "acerto de rota"
MEDIDA_LARGADA_COM_TETO = "{} bytes, teto {}"
MEDIDA_LARGADA_SEM_TETO = "{} bytes, sem teto declarado"
MEDIDA_CUSTO_MEDIDO = ("mediana US$ {:.2f} por execução, {} execução(ões), "
                       "{:.0f}% do gasto sem etapa atribuída")
MEDIDA_CUSTO_SEM_EXECUCAO = "não medido: nenhuma execução gravada"
MEDIDA_ROTA_NAO_MEDIDA = ("não medido nesta linha — rode `{} verificacoes.py "
                          "gatilho` cinco vezes e tome a mediana; a escolha "
                          "de skill varia ~1 acerto por rodada")
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
COMANDO_DAS_ARVORES = "git worktree list --porcelain"
MARCA_DA_ARVORE = "worktree "
UMA_ARVORE_SO = "  Uma árvore de trabalho só — a medida acima vale para ela."
ARVORES_AO_LADO = (
    "  {} árvores de trabalho neste repositório, medidas às {}: {}.\n"
    "  A medida acima é do INSTANTE em que rodou, e só desta árvore: outra\n"
    "  sessão pode commitar entre a medida e a leitura, então não declare\n"
    "  estado final de árvore compartilhada — cite a hora.")
ARVORES_NAO_MEDIDAS = "  Quantas árvores de trabalho existem: não medido."
CHAVE_DAS_BRANCHES = "branches"
CHAVE_DA_INTEGRACAO = "integracao"
CHAVE_DO_NUMERO_DO_PEDIDO = "number"
TEMPO_DA_REDE = 25
COMANDO_DA_BUSCA_NO_REMOTO = "git fetch --quiet origin {} {}"
COMANDO_DO_QUE_A_INCORPORACAO_NAO_TEM = (
    "git log --oneline --no-decorate {}..{}")
COMANDO_DO_PEDIDO_ABERTO = ("gh", "pr", "list", "--base", "{0}", "--head",
                            "{1}", "--state", "open", "--json",
                            CHAVE_DO_NUMERO_DO_PEDIDO)
PEDIDO_PULADO_SEM_INCORPORACAO = (
    "Pedido de incorporação: pulado — {} não declara {}, e sem a branch de "
    "incorporação não há para onde pedir.")
PEDIDO_PULADO_NA_INCORPORACAO = (
    "Pedido de incorporação: pulado — {} é a própria branch de incorporação; "
    "daqui não se pede, se publica.")
PEDIDO_PULADO_SEM_INTEGRACAO = (
    "Pedido de incorporação: pulado — {} não declara {}.{}, e sem a "
    "integração não dá para dizer o que espera o dono.")
PEDIDO_BUSCA_NAO_MEDIDA = (
    "Pedido de incorporação: NÃO MEDIDO — `git fetch origin {} {}` falhou "
    "({}). Medir contra espelho velho acusaria o que o dono já mesclou.")
PEDIDO_LIMPO = ("E {} já contém tudo de {}: nenhum commit espera pedido de "
                "incorporação.")
PEDIDO_ABERTO = ("{} commit(s) em {} esperam o dono no pedido #{} — o passo "
                 "seguinte está aberto.")
PEDIDO_NAO_MEDIDO = (
    "{} commit(s) em {} fora de {} — e se há pedido aberto, NÃO MEDIDO: "
    "`gh pr list` não respondeu. Confira à mão: gh pr list --base {} "
    "--head {} --state open")
PEDIDO_POR_ABRIR = ("{} commit(s) em {} que NÃO estão em {} e sem pedido de "
                    "incorporação aberto — entregue não é; só parece pronto:")
PEDIDO_COMO_ABRIR = ("  abra o pedido de incorporação: gh pr create --base {} "
                     "--head {}")
ARQUIVO_DO_EXECUTOR = "nucleo/executor.json"
CHAVE_DAS_ISSUES = "issues"
CHAVE_DO_REPOSITORIO_DAS_ISSUES = "repositorio"
TITULO_DO_QUADRO = "ONDE AS ISSUES NASCEM"
QUADRO_DECLARADO = "  {}"
QUADRO_SEM_ARQUIVO = (
    "  {} não existe aqui — sem ele a sessão não sabe onde a issue "
    "nasce, e\n  procurar no repositório de código devolve zero, que "
    "parece resposta.\n  Copie {} e preencha.")
QUADRO_ILEGIVEL = "  {} não se deixou ler: {}"
QUADRO_POR_PREENCHER = (
    "  {} ainda não declara o repositório das issues — o campo {}.{} "
    "está\n  vazio ou por preencher.")
ARQUIVO_DO_EXEMPLO_DO_EXECUTOR = "nucleo/executor.exemplo.json"
TITULO_DA_ABERTURA = "A ABERTURA — o que a sessão precisa ter em mãos"
ARQUIVO_DAS_INSTRUCOES = "AGENTS.md"
ARQUIVO_DA_DECLARACAO_DE_MCP = ".mcp.json"
CHAVE_DOS_SERVIDORES_DE_MCP = "mcpServers"
ARQUIVO_DOS_ALVOS_DO_INDICE = ".agents/indice/alvos.json"
INSTRUMENTO_DO_INDICE = ".agents/indice/indexar.py"
BUSCADOR_DO_INDICE = ".agents/indice/buscar.py"
BANDEIRA_DO_ESTADO_DO_INDICE = "--estado"
TEMPO_DO_ESTADO_DO_INDICE = 60
TETO_DE_LINHAS_DO_ERRO = 6
INSTRUCOES_NO_LUGAR = "  {} está aqui — a sessão abriu na raiz."
INSTRUCOES_AUSENTES = (
    "  {} não está aqui: esta pasta não é a raiz do repositório, e a sessão\n"
    "  aberta fora dela não carrega instrução nenhuma (regra 1). Abra a\n"
    "  sessão na pasta que tem o {}.")
MCP_DECLARADO = "  {} declara {} servidor(es): {}."
MCP_SEM_ARQUIVO = (
    "  {} não existe aqui — nenhum servidor de contexto é declarado, então\n"
    "  a sessão só tem as ferramentas do próprio agente. Se este repositório\n"
    "  não usa servidor, a linha é essa mesma; se usa, o arquivo faltou.")
MCP_ILEGIVEL = "  {} não se deixou ler: {}"
MCP_SEM_SERVIDOR = "  {} existe e não declara servidor nenhum em {}."
ARQUIVO_DE_ESTADO_DO_CLIENTE = ".claude.json"
ARQUIVO_DE_AUTENTICACAO_PENDENTE = ".claude/mcp-needs-auth-cache.json"
CHAVE_DOS_PROJETOS_DO_CLIENTE = "projects"
CHAVE_DOS_SERVIDORES_DESLIGADOS = "disabledMcpjsonServers"
ESTADO_DO_CLIENTE_AUSENTE = (
    "  o cliente não tem estado gravado sobre esses servidores ({} não\n"
    "  existe na casa): nada a acrescentar sobre eles antes da primeira\n"
    "  chamada.")
ESTADO_DO_CLIENTE_ILEGIVEL = "  o estado do cliente em {} não se deixou ler: {}"
ESTADO_DO_CLIENTE_DESLIGOU = (
    "  o cliente desligou {} deste(s) neste projeto: {} — a sessão abre sem\n"
    "  ele(s); religue no cliente ou peça ao dono.")
ESTADO_DO_CLIENTE_PEDE_AUTENTICACAO = (
    "  o cliente marca {} deste(s) pedindo autenticação: {} — a sessão abre\n"
    "  sem ele(s) até alguém autenticar.")
ESTADO_DO_CLIENTE_NADA_ACUSA = (
    "  o cliente não acusa servidor desligado nem pendente de autenticação.")
ESTADO_DO_CLIENTE_NAO_GUARDA_CONEXAO = (
    "  Conectado ou falhou o cliente não guarda em disco: servidor que sobe e\n"
    "  cai só aparece na primeira chamada — se ela falhar, avise na primeira\n"
    "  resposta.")
INDICE_NAO_INSTALADO = (
    "  o módulo do índice não está instalado aqui ({} não existe) — a busca\n"
    "  por significado não é desta camada, e nada a cobra.")
INDICE_SEM_ALVOS = (
    "  {} não existe — o indexador não sabe o que indexar, e a busca\n"
    "  responde menos do que existe. Declare os alvos.")
INDICE_DE_PE = (
    "  o índice responde, e a busca sem servidor de contexto é `python {}`.")
INDICE_FORA = (
    "  o índice não respondeu — `python {} {}` saiu {}:\n{}\n"
    "  Sem ele, a busca por significado não existe nesta sessão; a busca por\n"
    "  termo exato continua em `python {}`.")
ABERTURA_INTEGRA = "Abertura íntegra: {} peça(s) de pé."
ABERTURA_INCOMPLETA = (
    "Abertura INCOMPLETA: {} peça(s) faltando. A sessão que seguir daqui "
    "trabalha\ncom menos do que pensa ter — conserte o que está acima antes "
    "de trabalhar.")
MARCA_POR_PREENCHER = "${"
SAIDA_LIMPA = 0
SAIDA_COM_ACHADO = 1
SAIDA_NAO_MEDIDO = 2
ARQUIVO_DAS_PROTEGIDAS = ".claude/branches-protegidas.txt"
CHAVE_POR_INCORPORACAO = "branches_por_incorporacao"
MARCA_DE_COMENTARIO_NA_LISTA = "#"
PREFIXO_DO_REMOTO = "origin/"
CABECA_DO_REMOTO = "origin/HEAD"
SEPARADOR_DO_REMOTO = "/"
COMANDO_DA_REFERENCIA = "git rev-parse --verify --quiet {}"
COMANDO_DAS_LOCAIS = 'git branch --format="%(refname:short)"'
COMANDO_DAS_REMOTAS = 'git branch -r --format="%(refname:short)"'
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
COMANDO_DOS_GANCHOS_RASTREADOS = 'git ls-files ".claude/hooks/*.py"'
COMANDO_DOS_INSTRUMENTOS_RASTREADOS = 'git ls-files ".agents/*/*.py"'
NOME_DO_ESCOPO_DA_MATRICULA = "matricula"
NOME_DE_FONTES = "FONTES"
NOME_DE_MODULOS = "MODULOS"
NOME_DO_GANCHO_DECLARADO = "GanchoDeclarado"
CAMINHO_DE_GANCHO = re.compile(r"\.claude/hooks/[^\"'\s]+\.py")
GANCHO_DO_DESPACHANTE = f"{PASTA_DOS_GANCHOS}/despachar-cercas.py"
BLOCO_DAS_CERCAS = re.compile(r"^CERCAS = \((.*?)^\)", re.M | re.S)
CERCA_DECLARADA = re.compile(r'\("([A-Za-z0-9_-]+)",\s*"([^"]*)"')
BRIEFING_DA_SESSAO = ".agents/prompts/bootstart.md"
LINHA_DA_CERCA_NA_TABELA = "| `{}` |"
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
PASTA_DOS_MODULOS_DA_MATRICULA = "modulos"
MARCA_DE_MODULO_PRIVADO = "MODULO_PRIVADO"
SALDO_ORFA = "órfã — matriculada e ausente do disco"
SALDO_SEM_DECLARACAO = "ligado no settings.json sem GanchoDeclarado"
SALDO_DESLIGADO = ("declarado no montar.py e desligado no settings.json")
SALDO_MATCHER_DIVERGENTE = ("matcher diferente no despachante e no "
                            "instalador — um dos dois mente")
SALDO_FORA_DO_BRIEFING = ("cerca que o despachante roda sem linha na tabela "
                          "de ganchos do briefing — a sessão leva a recusa "
                          "sem saber que ela existe")
SALDO_EXCECAO_VELHA = "exceção que envelheceu — declarada e fora do git"
INTERPRETADOR_QUE_SOME = (
    "  INTERPRETADOR QUE SOME: `{0}` está registrado no comando de gancho e "
    "não existe no PATH desta máquina. Gancho que não roda não acusa, e o "
    "silêncio dele é indistinguível de verde — todos os ganchos registrados "
    "com `{0}` morrem juntos e calados. Conserte o comando em "
    ".claude/settings.json (ou settings.local.json) para um interpretador que "
    "resolve, e rode `python .agents/camada/camada.py --matricula` de novo.")
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
COMANDO_DOS_JSON_RASTREADOS = 'git ls-files "*.json"'
COMANDO_DO_QUE_O_GIT_IGNORA = 'git check-ignore -q "{}"'
CHAVE_DAS_REFERENCIAS_FORA_DO_GIT = "referencias_que_ficam_fora_do_git"
CAMPO_DO_CAMINHO_DECLARADO = "caminho"
ARQUIVO_DO_GITIGNORE = ".gitignore"
TITULO_DOS_DECLARADOS = ("O QUE FICA FORA DO GIT — a declaração e o git "
                         "dizem a mesma coisa")
DECLARADO_IGNORADO = "o git ignora"
DECLARADO_SOLTO = "SOLTO: o git ainda o vê"
LINHA_DO_DECLARADO = "  {:<44} {}"
SEM_DECLARACAO = ("{} não declara caminho nenhum fora do git — nada a "
                  "alinhar.")
DECLARACAO_DESALINHADA = (
    "{} caminho(s) declarado(s) em {} que o git NÃO ignora. Declaração pela "
    "metade é pior que nenhuma: a sessão lê que o caminho está fora do git, "
    "o `git status` continua acusando, e a cobrança de destino pede destino "
    "para o que ninguém vai commitar. Ponha cada um em {}.")
DECLARACAO_ALINHADA = ("Os {} caminho(s) declarados fora do git estão em {}: "
                       "a declaração e o git dizem a mesma coisa.")
COMANDO_DOS_JSON_FORA_DO_GIT = 'git ls-files --others "*.json"'
SUFIXO_DO_EXEMPLO = ".exemplo.json"
VALOR_QUE_A_MAQUINA_PREENCHE = re.compile(r"^\$\{[^}]*\}$")
CHAVE_DA_MAQUINA = "dado da máquina"
CHAVE_DO_REPOSITORIO = "fato do repositório"
CHAVE_DAS_EXCECOES_SEM_LEITOR = "chaves_de_configuracao_sem_leitor"
CAMPO_DO_ARQUIVO = "arquivo"
CAMPO_DA_CHAVE = "chave"
CAMPO_DO_MOTIVO = "motivo"
COMANDO_DOS_LEITORES_RASTREADOS = 'git ls-files "*.py"'
CONFIGURACAO_ILEGIVEL = ("Chaves NÃO MEDIDAS: {} não se deixou ler — {}. "
                         "Sem a declaração não há chave a cobrar, e zero "
                         "aqui seria invenção.")
SEM_CONFIGURACAO = ("Chaves NÃO MEDIDAS: `{}` não devolveu nenhum `.json` "
                    "rastreado. Universo vazio não é universo limpo — um "
                    "repositório sem configuração nenhuma é raro, e a "
                    "listagem que volta vazia por engano se parece com ele. "
                    "Confira o comando antes de acreditar no verde.")
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
TERMO_ABERTO = "ABERTO"
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
MARCA_DE_QUE_PASSOU = "OK  "
MARCA_DE_QUE_CAIU = "CAIU"

ORCAMENTO_DAS_BANCADAS_TOCADAS = 120
TEMPO_DE_UMA_BANCADA_TOCADA = 60
MARCA_DE_QUE_NAO_COUBE = "TETO"
ARQUIVO_DA_BANCADA_DA_PASTA = "testes.py"
IMPORTE_DA_BANCADA_DA_PASTA = "from testes import"
COMANDO_DO_QUE_MUDOU = "git diff --name-only HEAD"
COMANDO_DO_QUE_NASCEU = "git ls-files --others --exclude-standard"
COMANDO_DO_QUE_A_BRANCH_TEM = "git diff --name-only {}...HEAD"
TITULO_DA_BANCADA = "A BANCADA DE CADA INSTRUMENTO QUE A SESSÃO TOCOU"
BANCADA_SEM_GIT = ("o git não disse o que esta sessão mexeu, e sem essa "
                   "lista não há como saber que instrumento provar")
BANCADA_SEM_BASE = (
    "não há contra o que comparar os commits desta branch — nem upstream "
    "declarado, nem branch de incorporação que exista no disco ou no "
    "remoto. A árvore suja até se leria, mas metade da pergunta ficaria "
    "cega, e meia medida se lê como medida inteira")
BANCADA_SEM_COMPARACAO = "o git não comparou esta branch com {}"
BANCADA_NAO_MEDIDA = ("Bancada NÃO MEDIDA: {}. Sair 0 aqui faria a rotina "
                      "cega passar por rotina verde.")
BANCADA_O_QUE_TOCOU = ("{} arquivo(s) tocado(s) nesta sessão, contados na "
                       "árvore suja e nos commits que {} ainda não tem: {} "
                       "instrumento(s) com bancada e {} sem.")
BANCADA_NENHUM_TOCADO = ("Nenhum instrumento tocado nesta sessão — não há "
                         "bancada a rodar, e fica dito.")
BANCADA_SEM_TESTE = ("{} — instrumento tocado sem --testar próprio: não há "
                     "bancada para rodar, e a falta dela não reprova esta "
                     "rotina")
BANCADA_QUE_NAO_VIAJA = ("{} — bancada de testes ausente: ela não viaja com "
                         "a camada, e aqui não há o que rodar")
BANCADA_NAO_COUBE = ("{} — não coube no teto de {}s desta rotina: isto não é "
                     "reprovação, é orçamento. Rode-a à parte, com o tempo "
                     "que ela pedir")
BANCADA_NAO_RODOU = "{} — a bancada não chegou a rodar: {}"
LINHA_DA_BANCADA = "{} — {:.1f}s — {}"
BANCADA_FORA_DO_ORCAMENTO = (
    "Fora do orçamento: {} instrumento(s) tocado(s) NÃO rodaram, porque "
    "esta rotina se anuncia barata e gasta no máximo {}s — o ritual roda "
    "várias vezes por sessão. Ficaram de fora: {}.")
COMO_PROVAR_O_QUE_FICOU_DE_FORA = ("  a bancada inteira sai em: python "
                                   ".agents/saude/saude.py testes")
BANCADA_LIMPA = "Bancada em dia: {} instrumento(s) tocado(s), todos verdes."
BANCADA_VERMELHA = ("Bancada VERMELHA: {} de {} instrumento(s) tocado(s) "
                    "caíram — {}.")
BANCADA_QUE_SUJOU = (
    "Bancada SUJOU a árvore: rodar os testes fez nascer {}. Fixture tem de "
    "morrer com o temporário que a criou; a que escreve fora dele volta na "
    "rodada seguinte e, quando o ambiente não declara TEMP, o tempfile do "
    "Python cai no diretório atual e a sujeira nasce na raiz do "
    "repositório. Apague o que nasceu e faça a fixture morar dentro do "
    "TemporaryDirectory.")

FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.S)
CAMPO_NOME = re.compile(r"^name:\s*(.+)$", re.M)
CAMPO_DESCRICAO = re.compile(r"^description:\s*(.+)$", re.M)
CAMPO_DAS_FERRAMENTAS = re.compile(r"^tools:\s*\S", re.M)
FORMAS_DE_FUNCAO = (ast.FunctionDef, ast.AsyncFunctionDef)
MARCA_DE_TESTE_NO_NOME = "test"
MARCA_DA_BANDEIRA_DE_TESTE = "testar"
LINHA_DO_CATALOGO = "- {}: {}\n"

MODELO_DA_SIMULACAO = "claude-haiku-4-5-20251001"
TIPO_DO_RESULTADO = "result"
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


def corre(comando, tempo=TEMPO_DE_UM_TESTE, cwd=None):
    r = subprocess.run(comando, shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=tempo, cwd=cwd)
    return r.returncode, (r.stdout + r.stderr).strip()


def corre_a_lista(argumentos: list, tempo=TEMPO_DE_UM_TESTE, cwd=None):
    r = subprocess.run(argumentos, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=tempo,
                       cwd=cwd)
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


def candidatos_do_lancador(raiz: Path) -> tuple:
    try:
        texto = (raiz / ARQUIVO_DO_LANCADOR).read_text(encoding="utf-8")
    except OSError:
        return ()
    achado = LINHA_DOS_CANDIDATOS.search(texto)
    return tuple(achado.group(1).split()) if achado else ()


def responde_python_3(nome: str) -> bool:
    try:
        pronto = subprocess.run(
            [shutil.which(nome) or nome, "-c", PERGUNTA_DA_VERSAO],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=TETO_DO_INTERPRETADOR_S)
    except (OSError, subprocess.SubprocessError):
        return False
    return pronto.returncode == 0 and pronto.stdout.strip() == VERSAO_QUE_SERVE


def interpretador_que_roda(candidatos: tuple):
    for nome in candidatos:
        if responde_python_3(nome):
            return nome
    return None


@functools.lru_cache(maxsize=1)
def interpretador_com_nome_portatil(raiz: Path) -> str:
    return (interpretador_que_roda(candidatos_do_lancador(raiz))
            or INTERPRETADOR_NO_SHELL)


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


ASPAS_QUE_O_SHELL_TIRARIA = "\"'"


def chama_o_lancador(pedacos: list) -> bool:
    return (pedacos[0] == SHELL_DO_LANCADOR and len(pedacos) > 1
            and pedacos[1].endswith(ARQUIVO_DO_LANCADOR))


def interpretadores_que_somem(comandos: list, raiz: Path) -> list:
    candidatos = candidatos_do_lancador(raiz)
    ausentes = []
    for comando in comandos:
        pedacos = [p.strip(ASPAS_QUE_O_SHELL_TIRARIA)
                   for p in shlex.split(comando, posix=os.name != "nt")]
        if not pedacos:
            continue
        chamado = pedacos[0]
        if chama_o_lancador(pedacos):
            chamado = ARQUIVO_DO_LANCADOR
            roda = bool(shutil.which(SHELL_DO_LANCADOR)
                        and interpretador_que_roda(candidatos))
        elif chamado in candidatos:
            roda = responde_python_3(chamado)
        else:
            roda = bool(shutil.which(chamado) or Path(chamado).is_file())
        if not roda and chamado not in ausentes:
            ausentes.append(chamado)
    return sorted(ausentes)


def ganchos_com_interpretador_que_some(raiz: Path) -> list:
    return interpretadores_que_somem(
        comandos_dos_ganchos(raiz, CONFIGURACOES_DO_CLAUDE, ""), raiz)


def comandos_de_abertura(raiz: Path) -> list:
    return comandos_dos_ganchos(raiz, CONFIGURACOES_DO_CLAUDE,
                                EVENTO_DE_ABERTURA)


def bytes_que_os_ganchos_injetam(raiz: Path) -> tuple:
    total, cegos = 0, 0
    for comando in comandos_de_abertura(raiz):
        real = comando.replace(RAIZ_NO_COMANDO, str(raiz)).replace(
            RAIZ_NO_COMANDO_SEM_CHAVES, str(raiz))
        ambiente = dict(os.environ, **{VARIAVEL_DA_RAIZ_NO_AMBIENTE: str(raiz)})
        try:
            pronto = subprocess.run(
                real, shell=True, input=ENTRADA_VAZIA_DO_GANCHO,
                capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=raiz,
                env=ambiente, timeout=TEMPO_DE_UM_GANCHO)
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
        codigo, _ = corre(COMANDO_DA_REFERENCIA.format(candidata), cwd=raiz)
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
        codigo, saida = corre(COMANDO_DO_TOPO.format(nome), cwd=raiz)
        return saida.strip() if codigo == 0 else ""

    topo_da_referencia = topo(referencia)

    def e_rastro(bruta):
        if topo(bruta) == topo_da_referencia:
            return False, True
        codigo, _ = corre(COMANDO_DO_QUE_ACRESCENTA.format(referencia, bruta),
                          cwd=raiz)
        if codigo not in (NAO_ACRESCENTA_NADA, ACRESCENTA_ALGUMA_COISA):
            return False, False
        return codigo == NAO_ACRESCENTA_NADA, True

    def colher(comando, e_remota):
        codigo, saida = corre(comando, cwd=raiz)
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
    codigo, alvo = corre(COMANDO_DO_UPSTREAM, cwd=raiz)
    if codigo != 0 or not alvo:
        codigo, alvo = corre(COMANDO_DO_ESPELHO.format(atual), cwd=raiz)
    if codigo != 0 or not alvo:
        print(SEM_ENTREGA.format(atual, atual))
        return SAIDA_COM_ACHADO
    _, sobra = corre(COMANDO_DO_QUE_FALTA.format(alvo), cwd=raiz)
    linhas = [l for l in sobra.split("\n") if l.strip()]
    if not linhas:
        print(ENTREGA_LIMPA.format(atual, alvo))
        return SAIDA_LIMPA
    print(ENTREGA_COM_SOBRA.format(len(linhas), atual, alvo))
    for linha in linhas:
        print(f"  {linha}")
    return SAIDA_COM_ACHADO


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
        return SAIDA_NAO_MEDIDO
    if not locais and not remotas:
        print(PODA_LIMPA)
        return SAIDA_LIMPA
    print(PODA_COM_SOBRA.format(len(locais) + len(remotas), referencia))
    if locais:
        print(PODA_LOCAL.format(" ".join(locais)))
    if remotas:
        print(PODA_REMOTA.format(
            " ".join(nome_curto_da_branch(r) for r in remotas)))
    print(PODA_ESCAPE.format(ARQUIVO_DAS_PROTEGIDAS))
    return SAIDA_COM_ACHADO


def integracao_declarada(raiz: Path) -> str:
    try:
        dado = json.loads((raiz / ARQUIVO_DO_EXECUTOR).read_text(
            encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    branches = dado.get(CHAVE_DAS_BRANCHES) if isinstance(dado, dict) \
        else None
    if not isinstance(branches, dict):
        return ""
    declarada = branches.get(CHAVE_DA_INTEGRACAO)
    return str(declarada).strip() if declarada else ""


def comando_do_pedido_aberto(base: str, cabeca: str) -> list:
    return [parte.format(base, cabeca) for parte in COMANDO_DO_PEDIDO_ABERTO]


def numeros_dos_pedidos_abertos(raiz: Path, base: str, cabeca: str):
    try:
        codigo, saida = corre_a_lista(comando_do_pedido_aberto(base, cabeca),
                                      tempo=TEMPO_DA_REDE, cwd=raiz)
    except (OSError, subprocess.SubprocessError):
        return None
    if codigo != 0:
        return None
    try:
        pedidos = json.loads(saida or "[]")
    except ValueError:
        return None
    if not isinstance(pedidos, list):
        return None
    return [p[CHAVE_DO_NUMERO_DO_PEDIDO] for p in pedidos
            if isinstance(p, dict) and CHAVE_DO_NUMERO_DO_PEDIDO in p]


MARCA_DA_BUSCA_FEITA_POR_QUEM_CHAMOU = "ATLAS_BUSCA_FEITA"
VALIDADE_DA_MARCA_DA_BUSCA_S = 30


def quem_chamou_ja_buscou(branches, ambiente=None, agora=None) -> bool:
    marca = (os.environ if ambiente is None else ambiente).get(
        MARCA_DA_BUSCA_FEITA_POR_QUEM_CHAMOU, "")
    instante, _, buscadas = marca.partition("|")
    try:
        idade = (time.time() if agora is None else agora) - float(instante)
    except ValueError:
        return False
    return (0 <= idade <= VALIDADE_DA_MARCA_DA_BUSCA_S
            and set(branches) <= set(buscadas.split(",")))


def o_que_espera_incorporacao(raiz: Path, atual: str,
                              consultar_pedidos=numeros_dos_pedidos_abertos
                              ) -> int:
    incorporacao = branch_de_incorporacao(raiz)
    if not incorporacao:
        print(PEDIDO_PULADO_SEM_INCORPORACAO.format(ARQUIVO_DE_CONFIGURACAO,
                                                    CHAVE_POR_INCORPORACAO))
        return SAIDA_LIMPA
    if atual == incorporacao:
        print(PEDIDO_PULADO_NA_INCORPORACAO.format(atual))
        return SAIDA_LIMPA
    integracao = integracao_declarada(raiz)
    if not integracao:
        print(PEDIDO_PULADO_SEM_INTEGRACAO.format(
            ARQUIVO_DO_EXECUTOR, CHAVE_DAS_BRANCHES, CHAVE_DA_INTEGRACAO))
        return SAIDA_LIMPA
    codigo, falha = ((0, "") if quem_chamou_ja_buscou(
        (integracao, incorporacao)) else corre(
        COMANDO_DA_BUSCA_NO_REMOTO.format(integracao, incorporacao),
        tempo=TEMPO_DA_REDE, cwd=raiz))
    if codigo != 0:
        print(PEDIDO_BUSCA_NAO_MEDIDA.format(integracao, incorporacao,
                                             falha.splitlines()[-1]
                                             if falha else codigo))
        return SAIDA_NAO_MEDIDO
    espelho = f"{PREFIXO_DO_REMOTO}{integracao}"
    referencia = f"{PREFIXO_DO_REMOTO}{incorporacao}"
    _, sobra = corre(COMANDO_DO_QUE_A_INCORPORACAO_NAO_TEM.format(
        referencia, espelho), cwd=raiz)
    commits = [l for l in sobra.split("\n") if l.strip()]
    if not commits:
        print(PEDIDO_LIMPO.format(referencia, espelho))
        return SAIDA_LIMPA
    pedidos = consultar_pedidos(raiz, incorporacao, integracao)
    if pedidos is None:
        print(PEDIDO_NAO_MEDIDO.format(len(commits), espelho, referencia,
                                       incorporacao, integracao))
        return SAIDA_NAO_MEDIDO
    if pedidos:
        print(PEDIDO_ABERTO.format(len(commits), espelho, pedidos[0]))
        return SAIDA_LIMPA
    print(PEDIDO_POR_ABRIR.format(len(commits), espelho, referencia))
    for commit in commits:
        print(f"  {commit}")
    print(PEDIDO_COMO_ABRIR.format(incorporacao, integracao))
    return SAIDA_COM_ACHADO


def veredito_da_entrega(*pontas: int) -> int:
    if SAIDA_COM_ACHADO in pontas:
        return SAIDA_COM_ACHADO
    if SAIDA_NAO_MEDIDO in pontas:
        return SAIDA_NAO_MEDIDO
    return SAIDA_LIMPA


def arvores_de_trabalho(raiz: Path) -> str:
    try:
        codigo, saida = corre(COMANDO_DAS_ARVORES, cwd=raiz)
    except (OSError, subprocess.SubprocessError):
        return ARVORES_NAO_MEDIDAS
    if codigo != 0:
        return ARVORES_NAO_MEDIDAS
    caminhos = [linha[len(MARCA_DA_ARVORE):].strip()
                for linha in saida.split("\n")
                if linha.startswith(MARCA_DA_ARVORE)]
    if len(caminhos) < 2:
        return UMA_ARVORE_SO
    agora = time.strftime("%H:%M:%S")
    return ARVORES_AO_LADO.format(len(caminhos), agora,
                                  ", ".join(Path(c).name for c in caminhos))


def entrega(raiz: Path,
            consultar_pedidos=numeros_dos_pedidos_abertos) -> int:
    codigo, atual = corre(COMANDO_DA_BRANCH, cwd=raiz)
    if codigo != 0 or not atual:
        print(FORA_DE_REPOSITORIO)
        return SAIDA_LIMPA
    print(f"\n{TITULO_ENTREGA}")
    faltou = o_que_ainda_nao_saiu(raiz, atual)
    sobrou = o_que_saiu_e_ficou(raiz, atual)
    espera = o_que_espera_incorporacao(raiz, atual, consultar_pedidos)
    print(arvores_de_trabalho(raiz))
    return veredito_da_entrega(faltou, sobrou, espera)


def quadro_declarado(raiz: Path) -> tuple:
    caminho = raiz / ARQUIVO_DO_EXECUTOR
    if not caminho.is_file():
        return "", QUADRO_SEM_ARQUIVO.format(ARQUIVO_DO_EXECUTOR,
                                             ARQUIVO_DO_EXEMPLO_DO_EXECUTOR)
    try:
        dado = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, ValueError) as falha:
        return "", QUADRO_ILEGIVEL.format(ARQUIVO_DO_EXECUTOR, falha)
    declarado = ""
    if isinstance(dado, dict):
        issues = dado.get(CHAVE_DAS_ISSUES)
        if isinstance(issues, dict):
            declarado = str(
                issues.get(CHAVE_DO_REPOSITORIO_DAS_ISSUES) or "").strip()
    if not declarado or MARCA_POR_PREENCHER in declarado:
        return "", QUADRO_POR_PREENCHER.format(
            ARQUIVO_DO_EXECUTOR, CHAVE_DAS_ISSUES,
            CHAVE_DO_REPOSITORIO_DAS_ISSUES)
    return declarado, QUADRO_DECLARADO.format(declarado)


def instrucoes_da_raiz(raiz: Path) -> tuple:
    if (raiz / ARQUIVO_DAS_INSTRUCOES).is_file():
        return True, INSTRUCOES_NO_LUGAR.format(ARQUIVO_DAS_INSTRUCOES)
    return False, INSTRUCOES_AUSENTES.format(ARQUIVO_DAS_INSTRUCOES,
                                             ARQUIVO_DAS_INSTRUCOES)


def mesma_pasta(um: str, outra: Path) -> bool:
    try:
        return Path(um).resolve() == outra.resolve()
    except (OSError, ValueError):
        return False


def servidores_desligados_no_cliente(raiz: Path, casa: Path) -> set:
    estado = casa / ARQUIVO_DE_ESTADO_DO_CLIENTE
    dado = json.loads(estado.read_text(encoding="utf-8"))
    projetos = dado.get(CHAVE_DOS_PROJETOS_DO_CLIENTE, {})
    if not isinstance(projetos, dict):
        return set()
    desligados = set()
    for caminho, entrada in projetos.items():
        if isinstance(entrada, dict) and mesma_pasta(caminho, raiz):
            desligados.update(entrada.get(CHAVE_DOS_SERVIDORES_DESLIGADOS)
                              or [])
    return desligados


def servidores_pedindo_autenticacao(casa: Path) -> set:
    pendencia = casa / ARQUIVO_DE_AUTENTICACAO_PENDENTE
    if not pendencia.is_file():
        return set()
    dado = json.loads(pendencia.read_text(encoding="utf-8"))
    return set(dado) if isinstance(dado, dict) else set()


def estado_do_cliente_sobre_os_servidores(raiz: Path, declarados: list,
                                          casa: Path = None) -> str:
    casa = Path.home() if casa is None else casa
    if not (casa / ARQUIVO_DE_ESTADO_DO_CLIENTE).is_file():
        return ESTADO_DO_CLIENTE_AUSENTE.format(ARQUIVO_DE_ESTADO_DO_CLIENTE)
    try:
        desligados = sorted(
            set(declarados) & servidores_desligados_no_cliente(raiz, casa))
        pendentes = sorted(
            set(declarados) & servidores_pedindo_autenticacao(casa))
    except (OSError, ValueError) as falha:
        return ESTADO_DO_CLIENTE_ILEGIVEL.format(ARQUIVO_DE_ESTADO_DO_CLIENTE,
                                                 falha)
    linhas = []
    if desligados:
        linhas.append(ESTADO_DO_CLIENTE_DESLIGOU.format(
            len(desligados), ", ".join(desligados)))
    if pendentes:
        linhas.append(ESTADO_DO_CLIENTE_PEDE_AUTENTICACAO.format(
            len(pendentes), ", ".join(pendentes)))
    if not linhas:
        linhas.append(ESTADO_DO_CLIENTE_NADA_ACUSA)
    linhas.append(ESTADO_DO_CLIENTE_NAO_GUARDA_CONEXAO)
    return "\n".join(linhas)


CHAVE_DA_LISTA_PERMITIDA = "allowedMcpServers"
FONTES_DA_LISTA_PERMITIDA_NA_CASA = (".claude/remote-settings.json", ".claude/settings.json")
FONTES_DA_LISTA_PERMITIDA_NO_PROJETO = (".claude/settings.local.json", ".claude/settings.json")
MCP_BARRADO_PELA_LISTA = (
    "  a lista permitida barra {} deste(s): {} — o cliente nem tenta subir e\n"
    "  não avisa; o comando ou o endereço declarado tem de casar exato com uma\n"
    "  entrada de allowedMcpServers, e só vale em sessão aberta depois.")


def entradas_da_lista_permitida(raiz: Path, casa: Path):
    entradas, achou = [], False
    candidatos = ([casa / f for f in FONTES_DA_LISTA_PERMITIDA_NA_CASA]
                  + [raiz / f for f in FONTES_DA_LISTA_PERMITIDA_NO_PROJETO])
    for arquivo in candidatos:
        try:
            dado = json.loads(arquivo.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        lista = dado.get(CHAVE_DA_LISTA_PERMITIDA) if isinstance(dado, dict) else None
        if isinstance(lista, list):
            achou = True
            entradas.extend(e for e in lista if isinstance(e, dict))
    return entradas if achou else None


def servidor_passa_pela_lista(nome: str, declaracao: dict, entradas: list) -> bool:
    comandos = [e["serverCommand"] for e in entradas if "serverCommand" in e]
    enderecos = [e["serverUrl"] for e in entradas if "serverUrl" in e]
    nomes = {e.get("serverName") for e in entradas if "serverName" in e}
    if "command" in declaracao:
        linha = [declaracao["command"], *declaracao.get("args", [])]
        return linha in comandos if comandos else nome in nomes
    if "url" in declaracao:
        return (any(fnmatch.fnmatchcase(declaracao["url"], padrao) for padrao in enderecos)
                if enderecos else nome in nomes)
    return nome in nomes


def servidores_barrados_pela_lista(raiz: Path, declarados: dict, casa: Path) -> list:
    entradas = entradas_da_lista_permitida(raiz, casa)
    if entradas is None:
        return []
    return sorted(nome for nome, declaracao in declarados.items()
                  if isinstance(declaracao, dict)
                  and not servidor_passa_pela_lista(nome, declaracao, entradas))


def servidores_de_contexto(raiz: Path, casa: Path = None) -> tuple:
    alvo = raiz / ARQUIVO_DA_DECLARACAO_DE_MCP
    if not alvo.is_file():
        return None, MCP_SEM_ARQUIVO.format(ARQUIVO_DA_DECLARACAO_DE_MCP)
    try:
        dado = json.loads(alvo.read_text(encoding="utf-8"))
    except (OSError, ValueError) as falha:
        return False, MCP_ILEGIVEL.format(ARQUIVO_DA_DECLARACAO_DE_MCP, falha)
    declarados = (dado.get(CHAVE_DOS_SERVIDORES_DE_MCP)
                  if isinstance(dado, dict) else None)
    if not isinstance(declarados, dict) or not declarados:
        return False, MCP_SEM_SERVIDOR.format(ARQUIVO_DA_DECLARACAO_DE_MCP,
                                              CHAVE_DOS_SERVIDORES_DE_MCP)
    nomes = sorted(declarados)
    declaracao = MCP_DECLARADO.format(ARQUIVO_DA_DECLARACAO_DE_MCP,
                                      len(nomes), ", ".join(nomes))
    estado = estado_do_cliente_sobre_os_servidores(raiz, nomes, casa=casa)
    barrados = servidores_barrados_pela_lista(
        raiz, declarados, Path.home() if casa is None else casa)
    if barrados:
        estado = MCP_BARRADO_PELA_LISTA.format(len(barrados), ", ".join(barrados)) + "\n" + estado
    return True, f"{declaracao}\n{estado}"


def indice_da_abertura(raiz: Path) -> tuple:
    if not (raiz / INSTRUMENTO_DO_INDICE).is_file():
        return None, INDICE_NAO_INSTALADO.format(INSTRUMENTO_DO_INDICE)
    if not (raiz / ARQUIVO_DOS_ALVOS_DO_INDICE).is_file():
        return False, INDICE_SEM_ALVOS.format(ARQUIVO_DOS_ALVOS_DO_INDICE)
    try:
        codigo, saida = corre_a_lista(
            [INTERPRETADOR, INSTRUMENTO_DO_INDICE,
             BANDEIRA_DO_ESTADO_DO_INDICE],
            tempo=TEMPO_DO_ESTADO_DO_INDICE, cwd=raiz)
    except (OSError, subprocess.SubprocessError) as falha:
        return False, INDICE_FORA.format(
            INSTRUMENTO_DO_INDICE, BANDEIRA_DO_ESTADO_DO_INDICE,
            type(falha).__name__, f"    {falha}", BUSCADOR_DO_INDICE)
    if codigo != 0:
        ultimas = saida.splitlines()[-TETO_DE_LINHAS_DO_ERRO:]
        return False, INDICE_FORA.format(
            INSTRUMENTO_DO_INDICE, BANDEIRA_DO_ESTADO_DO_INDICE, codigo,
            "\n".join(f"    {linha}" for linha in ultimas),
            BUSCADOR_DO_INDICE)
    return True, INDICE_DE_PE.format(BUSCADOR_DO_INDICE)


def pecas_da_abertura(raiz: Path) -> list:
    declarado, recado = quadro_declarado(raiz)
    return [instrucoes_da_raiz(raiz),
            servidores_de_contexto(raiz),
            (bool(declarado), recado),
            indice_da_abertura(raiz)]


def abertura(raiz: Path) -> int:
    print(f"\n{TITULO_DA_ABERTURA}")
    pecas = pecas_da_abertura(raiz)
    for _, recado in pecas:
        print(recado)
    faltam = [ok for ok, _ in pecas if ok is False]
    if faltam:
        print(ABERTURA_INCOMPLETA.format(len(faltam)))
        return SAIDA_COM_ACHADO
    print(ABERTURA_INTEGRA.format(len([ok for ok, _ in pecas if ok])))
    return SAIDA_LIMPA


def onde_a_issue_nasce(raiz: Path) -> int:
    print(f"\n{TITULO_DO_QUADRO}")
    declarado, recado = quadro_declarado(raiz)
    print(recado)
    return 0 if declarado else 1


def dias_parado(arquivo: Path, agora: float) -> int:
    return int((agora - arquivo.stat().st_mtime) // SEGUNDOS_DO_DIA)


def arquivos_do_rascunho(raiz: Path) -> list:
    pasta = raiz / RASCUNHO
    return sorted((a for a in pasta.rglob("*")
                   if a.is_file() and a.relative_to(pasta).parts[0]
                   not in PASTAS_DE_INSTRUMENTO_NO_RASCUNHO),
                  key=lambda a: a.as_posix())


def esquecidos_no_rascunho(arquivos: list, rastreados: set, raiz: Path,
                           agora: float) -> list:
    return [(rel, dias) for arquivo in arquivos
            if (rel := arquivo.relative_to(raiz).as_posix()) not in rastreados
            and (dias := dias_parado(arquivo, agora))
            > TETO_DE_DIAS_NO_RASCUNHO]


def caminho_que_o_git_ignora(raiz: Path, caminho: str) -> bool:
    codigo, _ = corre(COMANDO_DO_QUE_O_GIT_IGNORA.format(caminho), cwd=raiz)
    return codigo == 0


def declarados_fora_do_git(raiz: Path) -> int:
    print(f"\n{TITULO_DOS_DECLARADOS}")
    caminho = raiz / ARQUIVO_DE_CONFIGURACAO
    if not caminho.is_file():
        print(SEM_DECLARACAO.format(ARQUIVO_DE_CONFIGURACAO))
        return 0
    try:
        dado = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, ValueError) as erro:
        print(CONFIGURACAO_ILEGIVEL.format(ARQUIVO_DE_CONFIGURACAO, erro))
        return 1
    declaracao = dado.get(CHAVE_DAS_REFERENCIAS_FORA_DO_GIT) or []
    if not isinstance(declaracao, list) or not declaracao:
        print(SEM_DECLARACAO.format(ARQUIVO_DE_CONFIGURACAO))
        return 0
    desalinhados = []
    for entrada in declaracao:
        tem_caminho = (isinstance(entrada, dict)
                       and entrada.get(CAMPO_DO_CAMINHO_DECLARADO))
        if not tem_caminho:
            continue
        alvo = entrada[CAMPO_DO_CAMINHO_DECLARADO]
        ignorado = caminho_que_o_git_ignora(raiz, alvo)
        print(LINHA_DO_DECLARADO.format(
            alvo, DECLARADO_IGNORADO if ignorado else DECLARADO_SOLTO))
        if not ignorado:
            desalinhados.append(alvo)
    if desalinhados:
        print(DECLARACAO_DESALINHADA.format(
            len(desalinhados), ARQUIVO_DE_CONFIGURACAO, ARQUIVO_DO_GITIGNORE))
        return 1
    print(DECLARACAO_ALINHADA.format(len(declaracao), ARQUIVO_DO_GITIGNORE))
    return 0


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


def versao_do_instalador(raiz: Path) -> str:
    try:
        texto = (raiz / INSTALADOR).read_text(encoding="utf-8")
    except OSError:
        return NUMERO_NAO_MEDIDO
    achado = VERSAO_NO_INSTALADOR.search(texto)
    return achado.group(1) if achado else NUMERO_NAO_MEDIDO


def custo_por_entrega(execucoes: list) -> str:
    if not execucoes:
        return MEDIDA_CUSTO_SEM_EXECUCAO
    cobrados = sorted(dolar for _, dolar, _ in execucoes)
    meio = len(cobrados) // 2
    mediana = cobrados[meio] if len(cobrados) % 2 else \
        (cobrados[meio - 1] + cobrados[meio]) / 2
    cobrado = sum(cobrados)
    atribuido = sum(a for _, _, a in execucoes)
    return MEDIDA_CUSTO_MEDIDO.format(
        mediana, len(cobrados), 100 * max(cobrado - atribuido, 0) / cobrado)


def medidas_da_versao(raiz: Path) -> list:
    paga = medir(raiz)[1]["largada"]
    teto = teto_da_largada(raiz)
    return [
        (MEDIDA_VERSAO, versao_do_instalador(raiz)),
        (MEDIDA_LARGADA, MEDIDA_LARGADA_COM_TETO.format(paga, teto)
         if teto is not None else MEDIDA_LARGADA_SEM_TETO.format(paga)),
        (MEDIDA_CUSTO, custo_por_entrega(custo_das_execucoes(raiz))),
        (MEDIDA_ROTA, MEDIDA_ROTA_NAO_MEDIDA.format(
            interpretador_com_nome_portatil(raiz))),
    ]


def versao(raiz: Path) -> int:
    print(f"\n{TITULO_DAS_MEDIDAS}")
    for medida, valor in medidas_da_versao(raiz):
        print(LINHA_DA_MEDIDA.format(medida, valor))
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
    codigo, saida = corre(comando, cwd=raiz)
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


def cercas_do_despachante(raiz: Path) -> dict:
    try:
        texto = (raiz / GANCHO_DO_DESPACHANTE).read_text(encoding="utf-8")
    except OSError:
        return {}
    bloco = BLOCO_DAS_CERCAS.search(texto)
    if bloco is None:
        return {}
    return {f"{PASTA_DOS_GANCHOS}/{nome}.py": matcher
            for nome, matcher in CERCA_DECLARADA.findall(bloco.group(1))}


def cercas_que_o_despachante_roda(raiz: Path) -> set:
    return set(cercas_do_despachante(raiz))


def matchers_declarados(raiz: Path) -> dict:
    escopo, _ = escopo_do_instalador(raiz)
    if escopo is None:
        return {}
    declarado = {}
    for valor in escopo.values():
        if type(valor).__name__ == NOME_DO_GANCHO_DECLARADO:
            for caminho in CAMINHO_DE_GANCHO.findall(valor.comando):
                declarado[caminho] = valor.matcher
    return declarado


def divergencias_do_despachante(raiz: Path) -> list:
    do_despachante = cercas_do_despachante(raiz)
    if not do_despachante:
        return []
    declarado = matchers_declarados(raiz)
    saldos = []
    for caminho, matcher in sorted(do_despachante.items()):
        esperado = declarado.get(caminho)
        if esperado is not None and esperado != matcher:
            saldos.append((caminho, SALDO_MATCHER_DIVERGENTE))
    return saldos


def cercas_fora_da_tabela_do_briefing(raiz: Path) -> list:
    try:
        tabela = (raiz / BRIEFING_DA_SESSAO).read_text(encoding="utf-8")
    except OSError:
        return []
    return [(caminho, SALDO_FORA_DO_BRIEFING)
            for caminho in sorted(cercas_do_despachante(raiz))
            if LINHA_DA_CERCA_NA_TABELA.format(Path(caminho).stem)
            not in tabela]


def saldos_da_matricula(raiz: Path, ganchos: list, fontes: tuple,
                        declarados: set) -> list:
    embutidos = embutidos_sob(raiz, fontes, f"{PASTA_DOS_GANCHOS}/")
    ligados = set()
    for comando in comandos_dos_ganchos(raiz, (ARQUIVO_SETTINGS,),
                                        TODOS_OS_EVENTOS):
        ligados.update(CAMINHO_DE_GANCHO.findall(comando))
    if GANCHO_DO_DESPACHANTE in ligados:
        ligados |= cercas_que_o_despachante_roda(raiz)
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


def instrumentos_de_modulo_privado(raiz: Path) -> set:
    base = raiz / PASTA_DOS_MODULOS_DA_MATRICULA
    if not base.is_dir():
        return set()
    return {arquivo.relative_to(pasta).as_posix()
            for pasta in base.iterdir()
            if pasta.is_dir() and (pasta / MARCA_DE_MODULO_PRIVADO).is_file()
            for arquivo in pasta.rglob("*.py") if arquivo.is_file()}


def saldos_dos_instrumentos(raiz: Path, instrumentos: list, fontes: tuple,
                            por_modulo: set) -> list:
    viajam = (embutidos_sob(raiz, fontes, f"{PASTA_DOS_INSTRUMENTOS}/")
              | por_modulo | set(INSTRUMENTOS_QUE_FICAM)
              | instrumentos_de_modulo_privado(raiz))
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
    saldos += divergencias_do_despachante(raiz)
    saldos += cercas_fora_da_tabela_do_briefing(raiz)
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
        return 1
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


def regras_da_pasta(raiz: Path) -> tuple:
    sempre = por_caminho = 0
    for regra in sorted((raiz / PASTA_DE_REGRAS).rglob(GLOB_PAGINA)):
        texto = regra.read_text(encoding="utf-8", errors="replace")
        frente = FRONTMATTER.match(texto)
        if frente and MARCA_DE_REGRA_POR_CAMINHO.search(frente.group(1)):
            por_caminho += len(texto.encode()) - len(frente.group(1).encode())
        else:
            sempre += len(texto.encode())
    return sempre, por_caminho


def medir(raiz: Path) -> tuple:
    instrucoes = sum(len((raiz / n).read_bytes())
                     for n in CARREGADOS_EM_TODA_SESSAO if (raiz / n).is_file())
    regras_sempre, regras_por_caminho = regras_da_pasta(raiz)
    instrucoes += regras_sempre
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
    injetado_por_gancho, ganchos_cegos = bytes_que_os_ganchos_injetam(
        raiz)
    dados = {
        "largada": instrucoes + catalogo + injetado_por_gancho,
        "instrucoes": instrucoes,
        "regras_sempre": regras_sempre,
        "regras_por_caminho": regras_por_caminho,
        "catalogo": catalogo,
        "injetado_por_gancho": injetado_por_gancho,
        "ganchos_nao_medidos": ganchos_cegos,
        "adiado": adiado,
        "skills": len(skills),
        "paginas": len(paginas),
        "bytes_das_paginas": sum(len(p.read_bytes()) for p in paginas),
        "ganchos": len(sorted((raiz / PASTA_DOS_GANCHOS).glob(GLOB_PYTHON))),
        "subagentes": len(achados_de_subagente),
        "subagentes_sem_coleira": len(subagentes_sem_coleira),
        "skills_acima_do_teto": len(acima_do_teto),
        "regras": quantas_regras(raiz),
        "listagem_da_maquina": listagem_da_ferramenta(),
    }
    linhas = [
        LINHA.format("largada — o que TODA sessão paga",
                     f"{dados['largada']} bytes"),
        LINHA.format("  instruções (AGENTS.md, CLAUDE.md, regras sempre)",
                     f"{dados['instrucoes']} bytes"),
        LINHA.format("  regras por caminho — só quando o arquivo tocado bate",
                     f"{dados['regras_por_caminho']} bytes, fora da largada"),
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


def pecas_de_instrumento(raiz: Path) -> list:
    alvos = sorted(raiz.glob(GLOB_PYTHON))
    alvos += sorted((raiz / PASTA_DOS_GANCHOS).glob(GLOB_PYTHON))
    alvos += sorted((raiz / PASTA_DOS_INSTRUMENTOS).rglob(GLOB_PYTHON))
    return alvos


def tem_bancada(peca: Path) -> bool:
    return BANDEIRA_DE_TESTE in peca.read_text(encoding="utf-8",
                                               errors="replace")


def instrumentos_com_teste(raiz: Path) -> list:
    return [a for a in pecas_de_instrumento(raiz) if tem_bancada(a)]


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
            f'{INTERPRETADOR_NO_SHELL} "{alvo.relative_to(raiz)}" {BANDEIRA_DE_TESTE}',
            cwd=raiz)
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
        codigo, _ = corre(f'{INTERPRETADOR_NO_SHELL} {INSTALADOR} --verificar', cwd=raiz)
        rodados += 1
        if codigo != 0:
            caidos.append(INSTALADOR)
        linhas.append(LINHA_DE_CASO.format(
            "OK  " if codigo == 0 else "CAIU", f"{INSTALADOR} --verificar"))
    return linhas, {"rodados": rodados, "caem": len(caidos) + len(sem_teste),
                    "sem_teste": len(sem_teste), "fora": fora,
                    "segundos": round(segundos, 1), "casos": casos}


def linhas_do_git(raiz: Path, comando: str):
    try:
        codigo, saida = corre(comando, cwd=raiz)
    except (OSError, subprocess.SubprocessError):
        return None
    if codigo != 0:
        return None
    return [linha.strip() for linha in saida.splitlines() if linha.strip()]


def base_dos_commits_da_sessao(raiz: Path) -> str:
    try:
        codigo, alvo = corre(COMANDO_DO_UPSTREAM, cwd=raiz)
        if codigo == 0 and alvo.strip():
            return alvo.strip()
        declarada = integracao_declarada(raiz) or branch_de_incorporacao(raiz)
        return referencia_que_existe(raiz, declarada) if declarada else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def caminhos_que_a_sessao_tocou(raiz: Path) -> tuple:
    mudados = linhas_do_git(raiz, COMANDO_DO_QUE_MUDOU)
    nascidos = linhas_do_git(raiz, COMANDO_DO_QUE_NASCEU)
    if mudados is None or nascidos is None:
        return None, BANCADA_SEM_GIT
    base = base_dos_commits_da_sessao(raiz)
    if not base:
        return None, BANCADA_SEM_BASE
    commitados = linhas_do_git(raiz, COMANDO_DO_QUE_A_BRANCH_TEM.format(base))
    if commitados is None:
        return None, BANCADA_SEM_COMPARACAO.format(base)
    return sorted(set(mudados) | set(nascidos) | set(commitados)), base


def rodar_uma_bancada(raiz: Path, caminho: str, teto: float,
                      de_onde: Path = None) -> tuple:
    partida = time.monotonic()
    try:
        codigo, saida = corre_a_lista(
            [INTERPRETADOR, str(raiz / caminho), BANDEIRA_DE_TESTE],
            tempo=teto, cwd=de_onde or raiz)
    except subprocess.TimeoutExpired:
        return MARCA_DE_QUE_NAO_COUBE, BANCADA_NAO_COUBE.format(caminho, teto)
    except (OSError, subprocess.SubprocessError) as falha:
        return MARCA_DE_QUE_CAIU, BANCADA_NAO_RODOU.format(caminho, falha)
    gasto = time.monotonic() - partida
    if codigo == 0 and MARCA_DE_BANCADA_AUSENTE in saida:
        return FORA_DA_PROVA, BANCADA_QUE_NAO_VIAJA.format(caminho)
    return (MARCA_DE_QUE_PASSOU if codigo == 0 else MARCA_DE_QUE_CAIU,
            LINHA_DA_BANCADA.format(caminho, gasto, resumo_da_suite(saida)))


def delega_a_bancada_da_pasta(peca: Path) -> bool:
    vizinha = peca.parent / ARQUIVO_DA_BANCADA_DA_PASTA
    if peca.name == ARQUIVO_DA_BANCADA_DA_PASTA or not vizinha.is_file():
        return False
    return IMPORTE_DA_BANCADA_DA_PASTA in peca.read_text(encoding="utf-8",
                                                         errors="replace")


def sem_a_bancada_repetida(raiz: Path, com: list) -> list:
    pastas_com_bancada = {Path(c).parent.as_posix() for c in com
                          if Path(c).name == ARQUIVO_DA_BANCADA_DA_PASTA}
    return [c for c in com
            if Path(c).parent.as_posix() not in pastas_com_bancada
            or not delega_a_bancada_da_pasta(raiz / c)]


def separar_por_bancada(raiz: Path, tocados: list) -> tuple:
    pecas = {p.relative_to(raiz).as_posix(): p
             for p in pecas_de_instrumento(raiz)}
    escolhidas = sorted(set(tocados) & set(pecas))
    com = sem_a_bancada_repetida(
        raiz, [c for c in escolhidas if tem_bancada(pecas[c])])
    return com, [c for c in escolhidas if c not in com and c not in
                 [x for x in escolhidas if tem_bancada(pecas[x])]]


def anunciar_o_que_ficou_de_fora(fora: list, orcamento: float) -> None:
    if not fora:
        return
    print(BANCADA_FORA_DO_ORCAMENTO.format(len(fora), orcamento,
                                           ", ".join(fora)))
    print(COMO_PROVAR_O_QUE_FICOU_DE_FORA)


def bancada_dos_tocados(raiz: Path,
                        orcamento: float = ORCAMENTO_DAS_BANCADAS_TOCADAS,
                        teto: float = TEMPO_DE_UMA_BANCADA_TOCADA) -> int:
    print(f"\n{TITULO_DA_BANCADA}")
    tocados, base = caminhos_que_a_sessao_tocou(raiz)
    if tocados is None:
        print(BANCADA_NAO_MEDIDA.format(base))
        return SAIDA_NAO_MEDIDO
    com_bancada, sem_bancada = separar_por_bancada(raiz, tocados)
    print(BANCADA_O_QUE_TOCOU.format(len(tocados), base, len(com_bancada),
                                     len(sem_bancada)))
    for caminho in sem_bancada:
        print(LINHA_DE_CASO.format(FORA_DA_PROVA,
                                   BANCADA_SEM_TESTE.format(caminho)))
    if not com_bancada:
        print(BANCADA_NENHUM_TOCADO)
        return SAIDA_LIMPA
    partida = time.monotonic()
    caidos, nao_couberam, rodadas, fora_do_orcamento = [], [], 0, []
    nasceu_antes = set(linhas_do_git(raiz, COMANDO_DO_QUE_NASCEU) or [])
    with tempfile.TemporaryDirectory(prefix="bancada-fora-da-raiz-") as fora:
        for lugar, caminho in enumerate(com_bancada):
            if time.monotonic() - partida >= orcamento:
                fora_do_orcamento = com_bancada[lugar:]
                break
            marca, texto = rodar_uma_bancada(raiz, caminho, teto, Path(fora))
            print(LINHA_DE_CASO.format(marca, texto))
            rodadas += 1
            if marca == MARCA_DE_QUE_CAIU:
                caidos.append(caminho)
            if marca == MARCA_DE_QUE_NAO_COUBE:
                nao_couberam.append(caminho)
    sujou = sorted(set(linhas_do_git(raiz, COMANDO_DO_QUE_NASCEU) or [])
                   - nasceu_antes)
    anunciar_o_que_ficou_de_fora(fora_do_orcamento, orcamento)
    ficou_cego = bool(nao_couberam or fora_do_orcamento)
    if sujou:
        print(BANCADA_QUE_SUJOU.format(", ".join(sujou)))
    if caidos:
        print(BANCADA_VERMELHA.format(len(caidos), rodadas, ", ".join(caidos)))
    elif not ficou_cego and not sujou:
        print(BANCADA_LIMPA.format(rodadas))
    return veredito_da_entrega(
        SAIDA_COM_ACHADO if (caidos or sujou) else SAIDA_LIMPA,
        SAIDA_NAO_MEDIDO if ficou_cego else SAIDA_LIMPA)


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


def o_evento_do_resultado(eventos: list) -> dict:
    for evento in reversed(eventos):
        if isinstance(evento, dict) and evento.get("type") == TIPO_DO_RESULTADO:
            return evento
    for evento in reversed(eventos):
        if isinstance(evento, dict):
            return evento
    return {}


def colher_json(texto: str) -> dict:
    cortes = (texto,
              texto[texto.find("{"):texto.rfind("}") + 1],
              texto[texto.find("["):texto.rfind("]") + 1])
    for corte in cortes:
        with contextlib.suppress(ValueError):
            dado = json.loads(corte)
            if isinstance(dado, dict):
                return dado
            if isinstance(dado, list):
                return o_evento_do_resultado(dado)
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
    _, bruto = corre_a_lista(
        ["claude", "-p", PEDIDO.format(arquivo=ARQUIVO_PEDIDO),
         "--output-format", "json", "--model", MODELO_DA_SIMULACAO,
         "--allowedTools", FERRAMENTAS_DA_SIMULACAO],
        tempo=TEMPO_DA_SIMULACAO, cwd=raiz)
    parede = time.monotonic() - partida

    sessao = colher_json(bruto)
    resposta = colher_json(str(sessao.get("result", "")))
    do_nucleo = [(rotulo, bool(prova(resposta)),
                  "" if prova(resposta) else str(resposta.get(chave, ""))[:44])
                 for rotulo, chave, prova in perguntas(quantas)]
    do_artefato = []

    if alvo.is_file():
        codigo_do_teste, berro = corre(
            f'{INTERPRETADOR_NO_SHELL} "{ARQUIVO_PEDIDO}" {BANDEIRA_DE_TESTE}', cwd=raiz)
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
            interpretador_com_nome_portatil(raiz), chave)
        codigo, saida = corre(comando, cwd=raiz)
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
    ap.add_argument("--abertura", action="store_true",
                    help="prova que a sessão tem instruções, servidores de "
                         "contexto, endereço do quadro e índice de pé")
    ap.add_argument("--entrega", action="store_true",
                    help="prova que nada ficou fora da branch de entrega")
    ap.add_argument("--matricula", action="store_true",
                    help="cobra que todo gancho rastreado viaje no instalador")
    ap.add_argument("--bancada", action="store_true",
                    help="roda a bancada de cada instrumento que a sessão "
                         "tocou, medida pelo git")
    ap.add_argument("--chaves", action="store_true",
                    help="acusa chave de configuração que ninguém lê")
    ap.add_argument("--declarados", action="store_true",
                    help="cobra que todo caminho declarado fora do git "
                         "esteja mesmo no .gitignore")
    ap.add_argument("--markdown", action="store_true",
                    help="classifica todo .md rastreado pelo que o lê")
    ap.add_argument("--rascunho", action="store_true",
                    help="acusa arquivo não rastreado envelhecido em tmp/")
    ap.add_argument("--quadro", action="store_true",
                    help="imprime onde as issues deste workspace nascem")
    ap.add_argument("--conta", action="store_true",
                    help="mostra o que cada execução gravada custou")
    ap.add_argument("--versao", action="store_true",
                    help="as medidas da versão: versão, largada, custo por "
                         "entrega e acerto de rota, para comparar versões")
    ap.add_argument("--resumo", action="store_true",
                    help="só o JSON, para comparar entre rodadas")
    ap.add_argument("--raiz", default=None,
                    help="a raiz a medir, por extenso; sem ela, o diretório "
                         "atual")
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

    raiz = Path(a.raiz).resolve() if a.raiz else Path.cwd()
    if not (raiz / PASTA_DO_CONHECIMENTO).is_dir():
        sys.exit(FORA_DA_RAIZ.format(PASTA_DO_CONHECIMENTO))

    if a.largada:
        return largada(raiz)

    if a.abertura:
        return abertura(raiz)

    if a.entrega:
        return entrega(raiz)

    if a.matricula:
        return matricula(raiz)

    if a.bancada:
        return bancada_dos_tocados(raiz)

    if a.chaves:
        return chaves(raiz)

    if a.declarados:
        return declarados_fora_do_git(raiz)

    if a.markdown:
        return markdown(raiz)

    if a.rascunho:
        return rascunho(raiz)

    if a.quadro:
        return onde_a_issue_nasce(raiz)

    if a.conta:
        return conta(raiz)

    if a.versao:
        return versao(raiz)

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
