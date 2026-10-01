import argparse
import ast
import calendar
import contextlib
import fnmatch
import functools
import hashlib
import importlib.util
import io
import json
import os
import posixpath
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
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
TITULO_ENTREGA = ("A ENTREGA — o que ainda não saiu da máquina, medido em {} "
                  "na branch {}")
TITULO_LARGADA = "A LARGADA — o que toda sessão paga antes de trabalhar"
TITULO_DAS_MEDIDAS = ("AS MEDIDAS DA VERSÃO — três; a versão nova é melhor "
                 "quando nenhuma piora além do ruído e uma melhora")
REGISTRO_DA_INSTALACAO = ".agents/camada/registro-da-instalacao.json"
MARCO_DO_COMMIT = "commit {}"
COMANDO_DO_COMMIT_DA_ARVORE = "git rev-parse --short HEAD"
INSTALADOR_ANTIGO_NA_RAIZ = (
    "{} na raiz, sem modulos/: é o instalador antigo, que a receita de antes "
    "copiava para cá, e não a origem; a instalação se verifica do clone da "
    "camada, com python <pasta do clone do atlas>/montar.py --verificar")
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
                          "evals` na rodada; o `claude plugin eval` mede o "
                          "disparo das skills")
ARQUIVO_DE_CONFIGURACAO = "nucleo/configuracao.json"
CHAVE_DO_TETO = "teto_da_largada_em_bytes"
LARGADA_SEM_TETO = ("Largada: {} bytes. Sem teto declarado em {} ({}) — "
                    "medido, não cobrado.")
LARGADA_NA_REGUA = "Largada: {} bytes, dentro do teto de {}."
LARGADA_NAO_MEDIDA = ("Largada NÃO MEDIDA: {} bytes contados, e {} gancho(s) "
                      "de abertura não responderam. A parcela que falta pode "
                      "ser qualquer tamanho, então não há veredito: conserte "
                      "o gancho e meça de novo.")
LARGADA_ACIMA = ("Largada: {} bytes, ACIMA do teto de {}. Cada byte "
                 "aqui é pago por toda sessão, antes de ela trabalhar: "
                 "corte página, skill ou gancho de abertura, ou mude o teto por decisão.")
COMANDO_DA_BRANCH = "git rev-parse --abbrev-ref HEAD"
COMANDO_DO_UPSTREAM = "git rev-parse --abbrev-ref --symbolic-full-name @{u}"
COMANDO_DO_ESPELHO = "git rev-parse --abbrev-ref origin/{}"
COMANDO_DO_QUE_FALTA = "git log {}..HEAD --oneline"
COMANDO_DO_QUE_SO_EXISTE_AQUI = "git log HEAD --not --remotes --oneline"
COMANDO_DOS_REMOTOS_QUE_CONTEM_A_CABECA = "git branch -r --contains HEAD"
MARCA_DO_PONTEIRO_DO_REMOTO = "->"
CABECA_DESTACADA = "HEAD"
SEM_UPSTREAM_E_SEM_COMMIT_PROPRIO = (
    "Nada ficou para trás: {} não tem upstream, mas todo commit dela já está "
    "em algum remoto — não há trabalho que só exista nesta máquina.")
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
BANDEIRA_SEM_O_PEDIDO = "--sem-pedido"
MEDIDA_PULADA = "pulada"
PEDIDO_PULADO_A_PEDIDO = (
    "Pedido de incorporação: pulado a pedido de quem chamou ({}), que o "
    "mede por conta própria — a categoria dele sai 'pulada', nunca zero.")
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
INSTRUMENTO_DO_HISTORICO = ".agents/historico/historico.py"
BANDEIRA_DAS_PENDENTES = "--pendentes"
ROTULO_DO_HISTORICO = "histórico das issues encerradas"
CHAVE_DOS_AVISOS_DA_ABERTURA = "avisos_da_abertura"
CAMPOS_DO_MODULO_INSCRITO = ("instrumento", "bandeira", "rotulo")
INSCRITOS_SEM_LISTA = "não é lista"
INSCRITOS_TORTOS = "{} item(ns) sem instrumento, bandeira e rotulo em texto"
TEMPO_DO_AVISO_DE_MODULO = 60
SAIDA_DO_MODULO_COM_AVISO = 1
AVISO_DE_MODULO_NAO_MEDIDO = "{rotulo}: não medido — {motivo}"
VARIAVEL_DA_NUVEM = "CLAUDE_CODE_REMOTE"
NA_NUVEM_NAO_SE_MEDE = (
    "na nuvem, não se medem o {historico} nem os módulos de {chave}:\n"
    "  pedem a conta de cada papel pelo `gh` e programas da máquina local, e\n"
    "  a nuvem tem uma conta só. A receita: "
    "conhecimento/estado-que-nao-viaja.md")
INSTRUMENTO_DO_INDICE = ".agents/indice/indexar.py"
BUSCADOR_DO_INDICE = ".agents/indice/buscar.py"
BANDEIRA_DO_ESTADO_DO_INDICE = "--estado"
TEMPO_DO_ESTADO_DO_INDICE = 60
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
MCP_SO_NA_RAIZ_PRINCIPAL = (
    "  {arquivo} não existe nesta worktree; a raiz principal do repositório,\n"
    "  {principal}, declara {quantos} servidor(es): {nomes}. O que a sessão\n"
    "  carrega depende do cliente: o de terminal lê só a pasta aberta e não\n"
    "  os vê; o app de mesa resolve o projeto pela raiz principal e os\n"
    "  carrega. Confira pelas ferramentas que a sessão tem, e se faltarem,\n"
    "  copie o {arquivo} da raiz principal para cá.")
COMANDO_DA_RAIZ_COMUM = "git rev-parse --path-format=absolute --git-common-dir"
MCP_SEM_SERVIDOR = "  {} existe e não declara servidor nenhum em {}."
BANDEIRA_DA_CONEXAO = "--conexao"
TEMPO_DO_APERTO_DE_MAO = 45
CONEXAO_DE_PE = "de pé"
CONEXAO_CAIU = "caiu"
CONEXAO_NAO_MEDIDA = "não medida"
ID_DO_APERTO_DE_MAO = 1
PEDIDO_DO_APERTO_DE_MAO = {
    "jsonrpc": "2.0", "id": ID_DO_APERTO_DE_MAO, "method": "initialize",
    "params": {"protocolVersion": "2025-06-18", "capabilities": {},
               "clientInfo": {"name": "camada-abertura", "version": "1"}}}
CODIGO_DE_PARAMETRO_INVALIDO = -32602
MARCAS_DE_LOGIN_VENCIDO = ("invalidgrant", "invalid_grant")
TIPOS_DE_SERVIDOR_REMOTO = ("http", "sse", "streamable-http")
COMANDO_QUE_DERRUBA_A_ARVORE_DO_PROCESSO = ["taskkill", "/PID", "{}", "/T", "/F"]
TEMPO_PARA_DERRUBAR = 10
TEMPO_PARA_A_SAIDA_ASSENTAR = 2
MCP_CONEXAO_NAO_PEDIDA = (
    "  Provada a declaração, não a conexão: servidor que cai ao subir só\n"
    "  aparece aqui com `--abertura {}`, que faz o aperto de mão com cada um.")
MCP_TITULO_DA_CONEXAO = (
    "  Aperto de mão com cada servidor, até {} s cada, em paralelo:")
MCP_CONEXAO_DE_PE = "    {}: respondeu ao initialize."
MCP_CONEXAO_CAIU = "    {}: CAIU — {}."
MCP_CONEXAO_NAO_MEDIDA = (
    "    {}: NÃO MEDIDA — não é stdio ({}), e o aperto de mão daqui só fala "
    "stdio.")
MCP_CONEXAO_SEM_RESPOSTA = (
    "    {}: NÃO MEDIDA — não respondeu ao initialize em {} s e seguia vivo: "
    "no prazo, lento e mudo são iguais.")
MOTIVO_LOGIN_VENCIDO = (
    "login do perfil vencido ({}), ato do dono: renove o login e reabra a "
    "sessão")
MOTIVO_SEM_RESPOSTA = "não respondeu ao initialize em {} s"
MOTIVO_SAIU = "saiu sem responder ao initialize: {}"
MOTIVO_NAO_SOBE = "não subiu: {}"
MOTIVO_ERRO = "respondeu com erro {}: {}"
MOTIVO_SEM_COMANDO = "a declaração não tem comando"
MCP_CONEXAO_CAIDOS = "  {} servidor(es) caíram no aperto de mão: {}."
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
    "  do acervo não é desta camada, e nada a cobra.")
INDICE_DE_PE = (
    "  o índice é o ck em {}, no modo léxico e sem serviço de pé; a busca é\n"
    "  `python {}`.")
INDICE_SEM_O_CK = (
    "  o `ck` não está no PATH — a busca do acervo cai no grep, por palavra\n"
    "  e sem ranking, em `python {}`. A receita de instalar está em\n"
    "  conhecimento/indice.md.")
PROGRAMA_DO_INDICE = "ck"
ABERTURA_INTEGRA = "Abertura íntegra: {} peça(s) de pé."
ABERTURA_INCOMPLETA = (
    "Abertura INCOMPLETA: {} peça(s) faltando. A sessão que seguir daqui "
    "trabalha\ncom menos do que pensa ter — conserte o que está acima antes "
    "de trabalhar.")
TEMPO_DO_GIT_DOS_GANCHOS = 15
COMANDO_DA_REF_DA_INTEGRACAO = ("git", "rev-parse", "--verify", "--quiet",
                                "{}")
COMANDO_DOS_GANCHOS_CONTRA_A_REF = ("git", "diff", "--quiet", "{}", "--",
                                    PASTA_DOS_GANCHOS)
COMANDO_DOS_GANCHOS_QUE_FALTAM = ("git", "rev-list", "--count", "HEAD..{}",
                                  "--", PASTA_DOS_GANCHOS)
COMANDO_DO_COMMIT_DOS_GANCHOS = ("git", "log", "-1", "--format=%h", "{}", "--",
                                 PASTA_DOS_GANCHOS)
COMANDO_DOS_GANCHOS_FORA_DE_COMMIT = ("git", "diff", "--quiet", "HEAD", "--",
                                      PASTA_DOS_GANCHOS)
GANCHOS_IGUAIS = 0
GANCHOS_DIFERENTES = 1
SEM_AVISO_DOS_GANCHOS = ""
NENHUM_COMMIT_DE_GANCHO = "nenhum commit"
SUFIXO_DOS_GANCHOS_SUJOS = ", mais mudança sem commit"
CHAVE_DA_RAIZ_QUE_ESPELHA = "camada.raizSoEspelhaAIntegracao"
GANCHOS_SEM_INTEGRACAO = (
    "  Ganchos desta árvore contra a integração: não medido — {arquivo} não\n"
    "  declara {chave}, e sem ela não há contra o que comparar.")
GANCHOS_SEM_REF = (
    "  Ganchos desta árvore contra {ref}: não medido — a ref não existe aqui\n"
    "  (sem git, sem remoto ou nunca buscada); a abertura só busca na raiz\n"
    f"  que se declara espelho (git config {CHAVE_DA_RAIZ_QUE_ESPELHA} true).")
GANCHOS_NAO_MEDIDOS_PELO_GIT = (
    "  Ganchos desta árvore contra {ref}: não medido — `{comando}` saiu "
    "{codigo}.")
GANCHOS_DEFASADOS = (
    "  Ganchos DEFASADOS: os de {pasta} desta árvore são do {daqui}{sujos},\n"
    "  e faltam {faltam} commit(s) de gancho de {ref} ({dela}, ref local,\n"
    "  sem busca): a sessão roda cercas sem esses consertos.\n"
    "  Avance: {avanco}")
GANCHOS_SO_DESTA_ARVORE = (
    "  Ganchos desta árvore: diferem de {ref} ({dela}, ref local, sem busca)\n"
    "  só pelo que ela mesma mudou ({daqui}{sujos}).\n"
    "  Todo commit de gancho da integração já está aqui: não há o que avançar.")
AVANCO_POR_MESCLA = ("git fetch origin {integracao} && git merge {ref},\n"
                     "  e abra a sessão de novo.")
AVANCO_NUMA_ARVORE_DA_INTEGRACAO = (
    "{branch} não recebe mescla da sessão: depois de git fetch origin\n"
    "  {integracao}, abra a sessão numa worktree nova de {ref}.")
TEMPO_DA_BUSCA_NO_REMOTO = 30
AMBIENTE_DA_BUSCA_SEM_PERGUNTA = {"GIT_TERMINAL_PROMPT": "0",
                                  "GCM_INTERACTIVE": "never"}
TEMPO_DO_AVANCO_DA_RAIZ = 300
COMANDO_DA_DECLARACAO_DA_RAIZ = ("git", "config", "--local", "--bool", "--get",
                                 CHAVE_DA_RAIZ_QUE_ESPELHA)
COMANDO_DA_PASTA_COMUM_DO_GIT = ("git", "rev-parse", "--path-format=absolute",
                                 "--git-common-dir")
COMANDO_DA_MUDANCA_RASTREADA = ("git", "status", "--porcelain",
                                "--untracked-files=no")
COMANDO_DA_BUSCA_NO_ORIGIN = ("git", "fetch", "--quiet", "origin")
COMANDO_DOS_REMOTOS = ("git", "remote")
COMANDO_DOS_COMMITS_ENTRE = ("git", "rev-list", "--count", "{}..{}")
COMANDO_DO_AVANCO_RAPIDO = ("git", "merge", "--ff-only",
                            "--no-overwrite-ignore", "--quiet", "{}")
COMANDO_DO_COMMIT_CURTO = ("git", "rev-parse", "--short", "{}")
MARCA_DA_SESSAO_DE_PESQUISA = "ATLAS_SO_LEITURA"
VARIAVEL_DA_SESSAO_DO_CLIENTE = "CLAUDE_CODE_SESSION_ID"
GANCHO_DAS_SESSOES_VIVAS = ".claude/hooks/avisar-sessao-paralela.py"
NIVEIS_DA_CAMADA_ATE_A_ARVORE = 2
LETRAS_DO_APELIDO_DA_SESSAO = 8
TETO_DA_LISTA_DE_SUJOS = 5
SUJOS_ALEM_DO_TETO = " e mais {}"
RAIZ_SEM_INTEGRACAO = (
    "  A raiz contra a integração: não medido — {arquivo} não declara "
    "{chave}.")
RAIZ_NAO_MEDIDA = "  A raiz contra {ref}: não medido — {motivo}."
RAIZ_FORA_DA_INTEGRACAO = (
    "  A raiz está em {branch}, não na integração {integracao}: a abertura "
    "não a avança.")
RAIZ_EM_DIA = "  A raiz está em dia com {ref} ({curto})."
RAIZ_AVANCOU = (
    "  A raiz avançou {atras} commit(s) até {ref} ({curto}): a sessão aberta "
    "nela passa a rodar os ganchos de hoje.")
RAIZ_SUJA = (
    "  A raiz NÃO avançou: {quantos} arquivo(s) rastreado(s) mudado(s) nela "
    "— {lista}.\n"
    "  Ela fica {atras} commit(s) atrás de {ref}, e toda sessão aberta nela "
    "roda os ganchos de lá.\n"
    "  Quem mudou esses arquivos leva a mudança a uma worktree ou a desfaz; "
    "sem saber de quem é, pergunte ao dono antes de tocar.")
RAIZ_DIVERGIU = (
    "  A raiz NÃO avançou: tem {adiante} commit(s) que {ref} não tem, e o "
    "avanço rápido não passa por cima deles. Esses commits são de alguém: "
    "leve-os ao dono antes de qualquer coisa.")
RAIZ_AVANCO_RECUSADO = (
    "  A raiz NÃO avançou: `git merge --ff-only {ref}` recusou — {motivo}.")
RAIZ_COM_SESSAO_VIVA = (
    "  A raiz NÃO avançou: {quantas} outra(s) sessão(ões) viva(s) nela ({lista})."
    "\n  Avançar trocaria os arquivos debaixo delas; ela fica {atras} commit(s) "
    "atrás de {ref}, e a próxima abertura tenta de novo.")
RAIZ_EM_PESQUISA = (
    f"  A raiz: a sessão de pesquisa ({MARCA_DA_SESSAO_DE_PESQUISA}) não busca "
    "nem avança a raiz.")
RAIZ_BUSCADA_PELA_MANUTENCAO = (
    "  A integração {ref} foi buscada pela manutenção às {hora}: a abertura "
    "não busca de novo.")
BANDEIRA_DA_MANUTENCAO = "--manutencao"
BANDEIRA_DO_AGENDAMENTO = "--agendar"
ARQUIVO_DA_MARCA_DA_MANUTENCAO = "tmp/manutencao-noturna.json"
SUFIXO_DO_PROVISORIO = ".provisorio"
JANELA_DA_MANUTENCAO_H = 12
SEGUNDOS_DA_HORA = 3600
FORMATO_DO_INSTANTE = "%Y-%m-%dT%H:%M:%SZ"
FORMATO_DA_HORA = "%H:%M"
CHAVE_DE_QUANDO_RODOU = "rodou_em"
CHAVE_DOS_PASSOS = "passos"
CHAVE_DO_ESTADO_DO_PASSO = "estado"
CHAVE_DA_REF_BUSCADA = "ref"
CHAVE_DO_MOTIVO_DO_PASSO = "motivo"
CHAVE_DA_ULTIMA_LINHA = "ultima_linha"
CHAVE_DAS_FALHAS = "falhas"
CHAVE_DOS_BUSCADOS = "buscados"
CHAVE_DOS_PULADOS = "pulados"
PASSO_DA_INTEGRACAO = "integracao"
PASSO_DOS_VIZINHOS = "vizinhos"
PASSO_DO_HISTORICO = "historico"
PASSO_DO_INDICE = "indice"
ESTADO_OK = "ok"
ESTADO_FALHOU = "falhou"
ESTADO_PULADO = "pulado"
PASTA_DOS_VIZINHOS = "projetos"
CAMPO_DA_PASTA_DO_VIZINHO = "repositorio"
PASTA_DO_GIT = ".git"
BANDEIRA_DA_COLHEITA = "--colher"
BANDEIRA_DA_RONDA_DO_INDICE = "--ronda"
TEMPO_DA_COLHEITA = 900
TEMPO_DA_RONDA_DO_INDICE = 1800
TITULO_DA_MANUTENCAO = "A MANUTENÇÃO — o que a abertura deixa de pagar"
LINHA_DO_PASSO = "  {nome}: {estado} ({segundos} s){detalhe}"
SEPARADOR_DO_DETALHE = " — "
SEM_VIZINHO_COM_CLONE = "nenhum vizinho cadastrado tem clone com .git"
VIZINHO_SEM_O_REMOTO_DA_BUSCA = "sem o remoto {}"
MODULO_NAO_INSTALADO = "{} não está instalado"
MANUTENCAO_EM_DIA = "Marca gravada em {arquivo}: nenhum passo falhou."
MANUTENCAO_COM_FALHA = ("Marca gravada em {arquivo}: {quantos} passo(s) "
                        "falharam — {quais}.")
MARCA_QUE_NAO_SE_GRAVOU = (
    "A marca NÃO se gravou em {arquivo} ({motivo}): a abertura seguinte "
    "busca como sempre.")
MARCA_ILEGIVEL = (
    "  A marca da manutenção em {arquivo} não se deixou ler ({motivo}): a "
    "abertura busca como sempre.")
MARCA_SEM_FORMA = "não é um objeto JSON"
INTERPRETADOR_SEM_JANELA = "pythonw.exe"
INTERPRETADOR_COM_CONSOLE = "python.exe"
CAMINHO_DESTE_INSTRUMENTO = ".agents/camada/camada.py"
HORA_DA_MANUTENCAO = "05:30"
NOME_DA_TAREFA = "{}\\manutencao-noturna"
TETO_DO_COMANDO_DA_TAREFA = 261
PREFIXO_SEM_CONVERSAO = "MSYS_NO_PATHCONV=1 schtasks"
TITULO_DO_AGENDAMENTO = (
    "O AGENDAMENTO — o comando que agenda a manutenção todo dia; aqui ele só "
    "se imprime")
AGENDAMENTO_NO_WINDOWS = (
    "  Registrar a tarefa é configuração persistente da máquina e pede o sim "
    "do dono.\n"
    "  Criar, no Git Bash:\n"
    "    {prefixo} /Create /TN \"{tarefa}\" /SC DAILY /ST {hora} /F /TR "
    "\"{acao}\"\n"
    "  Conferir: {prefixo} /Query /TN \"{tarefa}\" /V /FO LIST\n"
    "  Rodar agora: {prefixo} /Run /TN \"{tarefa}\"\n"
    "  Remover: {prefixo} /Delete /TN \"{tarefa}\" /F\n"
    "  A tarefa é do usuário e roda com ele logado. Máquina dormindo na hora "
    "pula o dia,\n  e a abertura seguinte busca como sempre.")
AGENDAMENTO_SEM_JANELA_AUSENTE = (
    "  AVISO: {} não existe ao lado de {}: a tarefa abre uma janela a cada "
    "rodada.")
AGENDAMENTO_ACIMA_DO_TETO = (
    "  AVISO: o /TR tem {} caracteres, acima do teto de {} do schtasks: "
    "encurte o caminho da raiz ou crie a tarefa pelo XML.")
AGENDAMENTO_FORA_DO_WINDOWS = (
    "  Registrar o agendamento é configuração persistente da máquina e pede "
    "o sim do dono.\n"
    "  Fora do Windows, a linha do crontab (crontab -e):\n"
    "    {minuto} {hora} * * * {acao}")
TITULO_DA_CONFIANCA_DO_CODEX = (
    "A CONFIANÇA DOS GANCHOS DO CODEX — a impressão de hoje contra a "
    "confiada")
ARQUIVO_DOS_GANCHOS_DO_CODEX = ".codex/hooks.json"
PASTA_DO_CODEX_NA_CASA = ".codex"
VARIAVEL_DA_PASTA_DO_CODEX = "CODEX_HOME"
CONFIGURACAO_DO_CODEX = "config.toml"
CHAVE_DO_ESTADO_DOS_GANCHOS = "state"
CHAVE_DA_IMPRESSAO_CONFIADA = "trusted_hash"
CHAVE_DO_GANCHO_LIGADO = "enabled"
CHAVE_DO_FILTRO_DO_GANCHO = "matcher"
CHAVE_DO_TIPO_DO_GANCHO = "type"
CHAVE_DO_TEMPO_DO_GANCHO = "timeout"
CHAVE_DO_GANCHO_ASSINCRONO = "async"
CHAVE_DO_EVENTO_NA_IMPRESSAO = "event_name"
TIPO_DO_GANCHO_DE_COMANDO = "command"
CAMPOS_QUE_O_GANCHO_EXIGE = frozenset({CHAVE_DO_TIPO_DO_GANCHO,
                                       CHAVE_DO_COMANDO})
CAMPOS_DO_GANCHO_QUE_A_IMPRESSAO_REPRODUZ = (CAMPOS_QUE_O_GANCHO_EXIGE
                                             | {CHAVE_DO_TEMPO_DO_GANCHO})
CAMPOS_DO_GRUPO_QUE_A_IMPRESSAO_REPRODUZ = frozenset(
    {CHAVE_DO_FILTRO_DO_GANCHO, CHAVE_DOS_GANCHOS})
EVENTOS_QUE_IGNORAM_O_FILTRO = ("user_prompt_submit", "stop", "interrupt")
EVENTOS_DE_TEMPO_CURTO = ("session_end", "interrupt")
TEMPO_PADRAO_DO_GANCHO_S = 600
TEMPO_MINIMO_DO_GANCHO_S = 1
TEMPO_CURTO_PADRAO_S = 1
TEMPO_CURTO_MAXIMO_S = 3
PREFIXO_DA_IMPRESSAO = "sha256:"
PREFIXO_DE_CAMINHO_LITERAL = "\\\\?\\"
SEPARADOR_DA_CHAVE_DO_GANCHO = ":"
PARTES_DA_CHAVE_DEPOIS_DO_CAMINHO = 3
MAIUSCULA_QUE_ABRE_PALAVRA = re.compile(r"(?<!^)(?=[A-Z])")
GANCHO_CONFIADO = "confiado"
GANCHO_COM_CONFIANCA_VELHA = "confiança velha"
GANCHO_NUNCA_CONFIADO = "nunca confiado"
GANCHO_DESLIGADO = "desligado no /hooks"
GANCHO_FORA_DA_CONTA = "não medido: campo que esta leitura não reproduz"
LINHA_DO_GANCHO_DO_CODEX = "  {}:{}:{} — {}"
CODEX_SEM_PONTE = (
    "  {} não existe aqui ou não declara gancho: não há ponte do Codex, e\n"
    "  nada a confiar.")
CODEX_SEM_CONFIGURACAO = (
    "  o Codex não guardou configuração nesta máquina ({} não existe na\n"
    "  pasta dele): não há confiança a ler.")
CODEX_SEM_LEITOR_DE_TOML = (
    "  este Python não lê TOML (o leitor chegou no 3.11): a confiança não se\n"
    "  mede aqui, e a prova é a sonda do item 7 da partida, numa sessão do\n"
    "  Codex.")
CODEX_CONFIGURACAO_ILEGIVEL = (
    "  o {} do Codex não se deixou ler como TOML. O conteúdo não se repete\n"
    "  aqui, porque o arquivo guarda segredo. Sem ele a leitura não mede, e a\n"
    "  prova é a sonda do item 7 da partida, numa sessão do Codex.")
CODEX_PONTE_ILEGIVEL = "  {} não se deixou ler: {}"
CODEX_GANCHOS_CONFIADOS = (
    "Os {} gancho(s) do Codex estão confiados: a impressão de hoje bate com "
    "a\nque o dono confiou.")
CODEX_GANCHOS_NUNCA_CONFIADOS = (
    "Nenhum dos {} gancho(s) do Codex foi confiado nesta pasta: se o Codex\n"
    "abrir aqui, as cercas não rodam. Pasta onde o Codex não trabalha, como\n"
    "worktree nova, fica assim e passa.")
CODEX_GANCHOS_PULADOS = (
    "{} de {} gancho(s) do Codex não rodam aqui: o Codex os pula em "
    "silêncio,\ne a escrita que a cerca barraria passa. Confiança velha é o "
    "{}\nque mudou depois da última confiança. Confiar é do dono: /hooks no "
    "Codex\nde terminal aberto nesta raiz. Acusou logo depois de confiar: a "
    "conta do\nCodex mudou, e a prova é a sonda do item 7 da partida.")
CODEX_GANCHOS_FORA_DA_CONTA = (
    "{} de {} gancho(s) do Codex usam campo que esta leitura não reproduz: "
    "ela\nrefaz a conta só de type, command, timeout e matcher. Sem a conta "
    "não se\nsabe se o Codex os roda, e a prova é a sonda do item 7 da "
    "partida.")
MARCA_POR_PREENCHER = "${"
SAIDA_LIMPA = 0
SAIDA_COM_ACHADO = 1
SAIDA_NAO_MEDIDO = 2
ARQUIVO_DAS_PROTEGIDAS = ".claude/branches-protegidas.txt"
CHAVE_POR_INCORPORACAO = "branches_por_incorporacao"
MARCA_DE_COMENTARIO_NA_LISTA = "#"
PREFIXO_DO_REMOTO = "origin/"
CABECA_DO_REMOTO = "HEAD"
SEPARADOR_DO_REMOTO = "/"
COMANDO_DA_REFERENCIA = "git rev-parse --verify --quiet {}"
COMANDO_DOS_TOPOS = ('git for-each-ref --format="%(objectname) %(refname)" '
                     'refs/heads refs/remotes')
PREFIXO_DAS_LOCAIS = "refs/heads/"
PREFIXO_DAS_REMOTAS = "refs/remotes/"
COMANDO_DO_QUE_ACRESCENTA = ("git", "diff", "--quiet", "{}...{}")
DIFFS_EM_PARALELO = 8
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
CATEGORIAS_DA_ENTREGA = ("CATEGORIAS DA ENTREGA: commit-sem-destino={} "
                         "branch-por-podar={} integracao-sem-pedido={}")
PODA_COM_SOBRA = ("{} branch(es) que não acrescentam nada a {} e seguem de pé "
                  "— o rastro da entrega, que se acumula porque ninguém o vê:")
PODA_LOCAL = "  poda local:  git branch -d {}"
PODA_REMOTA = "  poda remota: git push origin --delete {}"
PODA_EM_USO = ("  fora da poda: {} — aberta(s) numa árvore de trabalho, e o git "
               "não apaga branch em uso; volta à poda quando a árvore fechar. "
               "Árvore apagada à mão ainda prende a branch: `git worktree "
               "prune` a solta.")
MARCA_DA_BRANCH_NA_ARVORE = "branch refs/heads/"
PODA_ESCAPE = ("  Quer guardar alguma? Declare o nome em {} — o arquivo é seu, "
               "e a atualização da camada não o sobrescreve.")

TITULO_MATRICULA = ("A MATRÍCULA — todo gancho e instrumento rastreado viaja "
                    "no instalador")
TODOS_OS_EVENTOS = ""
COMANDO_DOS_GANCHOS_RASTREADOS = 'git ls-files ".claude/hooks/*.py"'
COMANDO_DOS_INSTRUMENTOS_RASTREADOS = 'git ls-files ".agents/*/*.py"'
NOME_DO_ESCOPO_DA_MATRICULA = "matricula"
NOME_DE_FONTES = "FONTES"
NOME_DO_LEITOR_DA_CAMADA = "camada_da_pasta"
INSTALADOR_SEM_LEITOR = ("o instalador não tem {}, o leitor que diz o que "
                         "viaja por módulo")
NOME_DO_GANCHO_DECLARADO = "GanchoDeclarado"
EVENTO_DO_DESPACHANTE = "PreToolUse"
CAMINHO_DE_GANCHO = re.compile(r"\.claude/hooks/[^\"'\s]+\.py")
GANCHO_DO_DESPACHANTE = f"{PASTA_DOS_GANCHOS}/despachar-cercas.py"
BLOCO_DAS_CERCAS = re.compile(r"^CERCAS = \((.*?)^\)", re.M | re.S)
CERCA_DECLARADA = re.compile(r'\("([A-Za-z0-9_-]+)",\s*"([^"]*)"')
BRIEFING_DA_SESSAO = ".agents/prompts/bootstart.md"
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
    ".agents/saude/mutar.py": (
        "a mutação no fim prova as bancadas deste repositório numa cópia "
        "dele; ela serve a quem constrói a camada, e quem instala não tem as "
        "bancadas que ela desfaz"),
    ".agents/saude/ciclo.py": (
        "mede o ciclo de edição de fonte deste repositório contra um commit "
        "dele; quem instala não tem montar.py nem a fonte das skills para o "
        "ciclo existir"),
}
INSTRUMENTO_DE_MODULO_DE_MENTIRA = ".agents/mod/mod.py"
INSTALADOR_DE_MENTIRA = (
    "from collections import namedtuple\n"
    "GanchoDeclarado = namedtuple(\n"
    "    'GanchoDeclarado',\n"
    "    'nome evento matcher comando arquivo_exigido')\n"
    "FONTES = ('.claude/hooks/bom.py',)\n"
    "def camada_da_pasta(casa):\n"
    f"    return {{}}, {{'m': {{'{INSTRUMENTO_DE_MODULO_DE_MENTIRA}': ''}}}}\n"
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
CHAVE_APOSENTADA = "publicar"
CHAVE_DAS_AUTORIZACOES = "autorizacoes"
CHAVE_DOS_CADASTROS = "projetos"
CHAVE_APOSENTADA_NA_CONFIGURACAO = f"{CHAVE_DAS_AUTORIZACOES}.{CHAVE_APOSENTADA}"
CHAVE_APOSENTADA_NO_CADASTRO = (
    f"{CHAVE_DOS_CADASTROS}.<cadastro>.{CHAVE_APOSENTADA_NA_CONFIGURACAO}")
CADASTROS_COM_A_CHAVE_APOSENTADA = "{}, em {} cadastro(s)"
AVISO_DE_CHAVE_APOSENTADA = (
    "AVISO, chave aposentada: `{}` em {}. Publicar é do dono, sempre, e "
    "gancho nenhum lê esta chave — ligada ou desligada, ela não muda nada. "
    "Apague-a à mão: a camada não reescreve o arquivo de quem instalou.")
CHAVE_APOSENTADA_NAO_MEDIDA = (
    "Chave aposentada NÃO MEDIDA em {}: o arquivo não se deixou ler — {}. "
    "Sem lê-lo não se sabe se `{}` sobrou nele.")

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
PASTA_DOS_COMANDOS_DE_BARRA = ".claude/commands/"
COMANDO_DE_BARRA = ("comando de barra: o cliente o lê quando alguém digita o "
                    "comando, e a rotina não mede quem digita")
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
MARCA_DE_PONTO_DE_DESVIO = 0x400
ETIQUETA_DE_PONTO_DE_MONTAGEM = 0xA0000003
ETIQUETA_DE_LINK_SIMBOLICO = 0xA000000C
ETIQUETAS_QUE_DESVIAM_O_CAMINHO = frozenset(
    {ETIQUETA_DE_PONTO_DE_MONTAGEM, ETIQUETA_DE_LINK_SIMBOLICO})
TETO_DE_DIAS_NO_RASCUNHO = 7
SEGUNDOS_DO_DIA = 86400
PASTAS_DE_INSTRUMENTO_NO_RASCUNHO = {
    "evidencias": ("as evidências das execuções, que o executor de roteiros "
                   "escreve — a rodada as reabre"),
    "encerramento-lembrado": ("a marca de uma vez por sessão do gancho que "
                             "lembra o encerramento"),
    "relato-cobrado": ("a marca de uma vez por sessão do gancho que cobra "
                       "o relato da sessão"),
    "bancada": ("as rodadas do módulo bancada, que o julgamento dele "
                "reabre"),
}
COMANDO_DOS_RASCUNHOS_RASTREADOS = "git ls-files tmp/"
TITULO_RASCUNHO = "O RASCUNHO — o que envelhece em tmp/"
LINHA_DO_ESQUECIDO = "  {:<52} {} dias parado"
LINHA_DA_PASTA_DE_INSTRUMENTO = "  {:<24} fora da conta: {}"
SEM_RASCUNHO = "Sem {} no disco — nada a medir."
RASCUNHO_NAO_MEDIDO = (
    "Rascunho NÃO MEDIDO: `{}` falhou. Sem a listagem do git não sei o que "
    "ali é rastreado, e chamar tudo de esquecido acusaria o que viaja.")
RASCUNHO_QUE_E_ATALHO = (
    "Rascunho NÃO MEDIDO: `{}` é um atalho para outra pasta, e esta rotina "
    "não atravessa atalho — seguir levaria a limpeza para dentro da "
    "instalação de outro projeto. Zero aqui seria invenção: não é que não "
    "haja rascunho velho, é que eu não olhei. Desfaça o atalho, ou aponte a "
    "pasta de verdade.")
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
NOME_DO_MODULO_DA_BANCADA = "testes"
BANCADA_NAO_VIAJA = (
    MARCA_DE_BANCADA_AUSENTE + ": ela não viaja com a camada, e mora no "
    "repositório onde a camada é construída. Nada a rodar aqui.")
FORA_DA_PROVA = "FORA"
MARCA_DE_BYTE_QUE_NAO_E_UTF8 = "\ufffd"
OPCAO_DO_MODO_UTF8_DO_GANCHO = "-X utf8"
SAIDA_FORA_DO_UTF8 = ("a saída não é UTF-8: sem o modo UTF-8 do Python ela "
                      "sai em cp1252, e quem a lê vê letra trocada")
MARCA_DE_QUE_PASSOU = "OK  "
MARCA_DE_QUE_CAIU = "CAIU"

ORCAMENTO_DAS_BANCADAS_TOCADAS = 120
TEMPO_DE_UMA_BANCADA_TOCADA = 60
BANCADAS_AO_MESMO_TEMPO = 8
TETOS_PROPRIOS_DE_BANCADA = {
    ".agents/camada": 180,
    ".claude/hooks/vetar-branch-protegida.py": 180,
    ".claude/hooks/cobrar-destino-da-entrega.py": 180,
    ".agents/encadeador": 360,
    "modulos/encadeador/.agents/encadeador": 360,
}
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
BANCADA_ONDE_MEDIU = "Medido em {}, na branch {}."
BRANCH_QUE_O_GIT_NAO_DISSE = "que o git não disse"
BRANCH_DE_HEAD_DESTACADO = "nenhuma: o HEAD está destacado"
MARCA_DE_ARVORE_PODAVEL = "prunable"
BANCADA_SUJEIRA_NAO_MEDIDA = (
    "o git não listou o que nasceu na árvore, antes ou depois das bancadas: "
    "se elas sujaram, ninguém viu")
COMANDO_DA_BRANCH_ATUAL = "git branch --show-current"
COMANDO_DAS_ARVORES_DE_TRABALHO = "git worktree list --porcelain"
MARCA_DE_ARVORE_DE_TRABALHO = "worktree "
BANCADA_HA_OUTRA_ARVORE = (
    "Este repositório tem outra árvore de trabalho: {}. O zero acima é desta "
    "raiz; se o trabalho da sessão mora noutra, rode de lá ou diga --raiz.")
BANCADA_ARVORES_NAO_MEDIDAS = (
    "As outras árvores de trabalho NÃO FORAM MEDIDAS: o git não as listou. "
    "O zero acima vale só para esta raiz.")
BANCADA_SEM_TESTE = ("{} — instrumento tocado sem --testar próprio: não há "
                     "bancada para rodar, e a falta dela não reprova esta "
                     "rotina")
BANCADA_QUE_NAO_VIAJA = ("{} — bancada de testes ausente: ela não viaja com "
                         "a camada, e aqui não há o que rodar")
BANCADA_NAO_COUBE = ("{} — não coube no teto de {}s desta rotina: isto não é "
                     "reprovação, é orçamento. Rode-a à parte, com o tempo "
                     "que ela pedir")
BANCADA_NAO_RODOU = "{} — a bancada não chegou a rodar: {}"
PREFIXO_DA_PASTA_DE_FORA = "bancada-fora-da-raiz-"
PASTA_DE_FORA_QUE_FICOU = ("  a pasta temporária {} não se apagou ({}): um "
                           "processo da bancada ainda a segura. Ela fica "
                           "para o sistema limpar, e a rotina segue")
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
TIPO_DA_MENSAGEM_DO_ASSISTENTE = "assistant"
TIPO_DO_BLOCO_DE_TEXTO = "text"
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
PREFIXO_DA_COPIA_DA_SIMULACAO = "camada-simulacao-"
TEMPO_DO_GIT_DA_SIMULACAO = 60
COMANDO_DA_ARVORE_DA_SIMULACAO = ["git", "ls-files", "-z", "--cached",
                                  "--others", "--exclude-standard"]
ARQUIVOS_LOCAIS_DA_SIMULACAO = ("nucleo/executor.json", ".mcp.json",
                                ".agents/indice/alvos.json",
                                ".claude/settings.local.json")
SEM_COPIA = ("  (a simulação não rodou: a árvore não se copiou — {}. A sessão "
             "simulada escreve e roda comando, e na raiz ela mexeria no que é "
             "de quem instalou)")
COPIA_QUE_FICOU = ("  (AVISO: a cópia da simulação ficou em {} — {}; a medida "
                   "acima vale, o disco ficou com sobra)")
NUMERO_DESCONHECIDO = "Número que não existe: {}.\nOs que existem: {}."
NUMERO_NAO_MEDIDO = "não medido"
PASSO_DESCONHECIDO = "passo que não existe: {}. Os que existem: {}."
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


def corre(comando, tempo=TEMPO_DE_UM_TESTE, cwd=None, ambiente=None):
    r = subprocess.run(comando, shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=tempo, cwd=cwd, env=ambiente)
    return r.returncode, (r.stdout + r.stderr).strip()


def ambiente_sem_o_modo_utf8() -> dict:
    ambiente = {nome: valor for nome, valor in os.environ.items()
                if nome != "PYTHONIOENCODING"}
    ambiente["PYTHONUTF8"] = "0"
    return ambiente


def bandeiras_sem_janela() -> int:
    if sys.stdout is not None:
        return 0
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)


def corre_a_lista(argumentos: list, tempo=TEMPO_DE_UM_TESTE, cwd=None):
    r = subprocess.run(argumentos, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=tempo,
                       cwd=cwd, creationflags=bandeiras_sem_janela())
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

TETO_DO_CORPO_DA_SKILL = 36000
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
            and any(ARQUIVO_DO_LANCADOR in pedaco
                    for pedaco in pedacos[1:3]))


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


def referencia_e_topo(raiz: Path, nome: str) -> tuple:
    for candidata in (f"{PREFIXO_DO_REMOTO}{nome}", nome):
        codigo, topo = corre(COMANDO_DA_REFERENCIA.format(candidata), cwd=raiz)
        if codigo == 0:
            return candidata, topo
    return "", ""


def referencia_que_existe(raiz: Path, nome: str) -> str:
    return referencia_e_topo(raiz, nome)[0]


def nome_curto_da_branch(bruta: str) -> str:
    sem_remoto = bruta.split(PREFIXO_DO_REMOTO, 1)[-1] \
        if bruta.startswith(PREFIXO_DO_REMOTO) else bruta
    return sem_remoto.strip()


def branch_da_referencia(completa: str):
    for prefixo, e_remota in ((PREFIXO_DAS_LOCAIS, False),
                              (PREFIXO_DAS_REMOTAS, True)):
        if not completa.startswith(prefixo):
            continue
        nome = completa[len(prefixo):]
        if e_remota and (SEPARADOR_DO_REMOTO not in nome
                         or nome.split(SEPARADOR_DO_REMOTO, 1)[1]
                         == CABECA_DO_REMOTO):
            return None
        return nome, e_remota
    return None


def acrescenta_a_referencia(raiz: Path, referencia: str, completa: str):
    comando = [parte.format(referencia, completa)
               for parte in COMANDO_DO_QUE_ACRESCENTA]
    try:
        codigo, _ = corre_a_lista(comando, cwd=raiz)
    except (OSError, subprocess.SubprocessError):
        return False, False
    if codigo not in (NAO_ACRESCENTA_NADA, ACRESCENTA_ALGUMA_COISA):
        return False, False
    return codigo == NAO_ACRESCENTA_NADA, True


def topo_lido_no_git(raiz: Path, referencia: str) -> str:
    codigo, topo = corre(COMANDO_DO_TOPO.format(referencia), cwd=raiz)
    return topo.strip() if codigo == 0 else ""


def branches_ja_entregues(raiz: Path, referencia: str, atual: str,
                          protegidas: set, topo_da_referencia=None) -> tuple:
    topo_da_referencia = (topo_lido_no_git(raiz, referencia)
                          if topo_da_referencia is None
                          else topo_da_referencia.strip())
    topos = linhas_do_git(raiz, COMANDO_DOS_TOPOS)
    if not topo_da_referencia or topos is None:
        return [], [], False
    a_julgar = []
    for linha in topos:
        topo, _, completa = linha.partition(" ")
        achada = branch_da_referencia(completa.strip())
        if achada is None or topo == topo_da_referencia:
            continue
        nome, e_remota = achada
        curto = nome_curto_da_branch(nome)
        if not curto or curto == atual or curto.lower() in protegidas:
            continue
        a_julgar.append((nome, e_remota, completa.strip()))
    with ThreadPoolExecutor(max_workers=DIFFS_EM_PARALELO) as grupo:
        julgados = list(grupo.map(
            lambda candidata: acrescenta_a_referencia(
                raiz, referencia, candidata[2]), a_julgar))
    locais, remotas, mediu = [], [], True
    for (nome, e_remota, _), (rastro, julgou) in zip(a_julgar, julgados):
        mediu = mediu and julgou
        if rastro:
            (remotas if e_remota else locais).append(nome)
    return locais, remotas, mediu


def remotos_que_contem_a_cabeca(raiz: Path) -> list:
    codigo, saida = corre(COMANDO_DOS_REMOTOS_QUE_CONTEM_A_CABECA, cwd=raiz)
    if codigo != 0:
        return []
    return [linha.strip() for linha in saida.split("\n")
            if linha.strip() and MARCA_DO_PONTEIRO_DO_REMOTO not in linha]


def destino_da_cabeca_destacada(raiz: Path) -> str:
    integracao = integracao_declarada(raiz)
    if integracao:
        return referencia_que_existe(raiz, integracao)
    remotos = remotos_que_contem_a_cabeca(raiz)
    return remotos[0] if remotos else ""


def o_que_ainda_nao_saiu(raiz: Path, atual: str, dizer=print) -> int:
    if atual == CABECA_DESTACADA:
        alvo = destino_da_cabeca_destacada(raiz)
        codigo = 0 if alvo else 1
    else:
        codigo, alvo = corre(COMANDO_DO_UPSTREAM, cwd=raiz)
        if codigo != 0 or not alvo:
            codigo, alvo = corre(COMANDO_DO_ESPELHO.format(atual), cwd=raiz)
    if codigo != 0 or not alvo:
        codigo, so_aqui = corre(COMANDO_DO_QUE_SO_EXISTE_AQUI, cwd=raiz)
        if codigo == 0 and not so_aqui.strip():
            dizer(SEM_UPSTREAM_E_SEM_COMMIT_PROPRIO.format(atual))
            return SAIDA_LIMPA
        dizer(SEM_ENTREGA.format(atual, atual))
        return SAIDA_COM_ACHADO
    _, sobra = corre(COMANDO_DO_QUE_FALTA.format(alvo), cwd=raiz)
    linhas = [l for l in sobra.split("\n") if l.strip()]
    if not linhas:
        dizer(ENTREGA_LIMPA.format(atual, alvo))
        return SAIDA_LIMPA
    dizer(ENTREGA_COM_SOBRA.format(len(linhas), atual, alvo))
    for linha in linhas:
        dizer(f"  {linha}")
    return SAIDA_COM_ACHADO


def branches_das_arvores(linhas) -> set:
    return {linha[len(MARCA_DA_BRANCH_NA_ARVORE):] for linha in linhas or []
            if linha.startswith(MARCA_DA_BRANCH_NA_ARVORE)}


def branches_abertas_em_arvore(raiz: Path) -> set:
    return branches_das_arvores(
        linhas_do_git(raiz, COMANDO_DAS_ARVORES_DE_TRABALHO))


def o_que_saiu_e_ficou(raiz: Path, atual: str, dizer=print,
                       abertas_em_arvore=branches_abertas_em_arvore) -> int:
    incorporacao = branch_de_incorporacao(raiz)
    if not incorporacao:
        dizer(PODA_SEM_INCORPORACAO.format(ARQUIVO_DE_CONFIGURACAO,
                                           CHAVE_POR_INCORPORACAO))
        return 0
    referencia, topo = referencia_e_topo(raiz, incorporacao)
    if not referencia:
        dizer(PODA_SEM_INCORPORACAO.format(ARQUIVO_DE_CONFIGURACAO,
                                           CHAVE_POR_INCORPORACAO))
        return 0
    locais, remotas, mediu = branches_ja_entregues(
        raiz, referencia, atual, branches_de_longa_duracao(raiz), topo)
    if not mediu:
        dizer(PODA_NAO_MEDIDA)
        return SAIDA_NAO_MEDIDO
    abertas = abertas_em_arvore(raiz)
    em_uso = sorted(set(locais) & abertas)
    locais = [branch for branch in locais if branch not in em_uso]
    remotas = [remota for remota in remotas
               if nome_curto_da_branch(remota) not in abertas]
    if not locais and not remotas:
        dizer(PODA_LIMPA)
        if em_uso:
            dizer(PODA_EM_USO.format(" ".join(em_uso)))
        return SAIDA_LIMPA
    dizer(PODA_COM_SOBRA.format(len(locais) + len(remotas), referencia))
    if locais:
        dizer(PODA_LOCAL.format(" ".join(locais)))
    if remotas:
        dizer(PODA_REMOTA.format(
            " ".join(nome_curto_da_branch(r) for r in remotas)))
    if em_uso:
        dizer(PODA_EM_USO.format(" ".join(em_uso)))
    dizer(PODA_ESCAPE.format(ARQUIVO_DAS_PROTEGIDAS))
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


def resumo_das_arvores(linhas) -> str:
    if linhas is None:
        return ARVORES_NAO_MEDIDAS
    caminhos = [linha[len(MARCA_DA_ARVORE):].strip() for linha in linhas
                if linha.startswith(MARCA_DA_ARVORE)]
    if len(caminhos) < 2:
        return UMA_ARVORE_SO
    agora = time.strftime("%H:%M:%S")
    return ARVORES_AO_LADO.format(len(caminhos), agora,
                                  ", ".join(Path(c).name for c in caminhos))


def arvores_de_trabalho(raiz: Path) -> str:
    return resumo_das_arvores(linhas_do_git(raiz, COMANDO_DAS_ARVORES))


MEDIDAS_DA_ENTREGA_AO_MESMO_TEMPO = 3


def dito_na_ordem(medida, dito: list) -> int:
    veredito = medida.result()
    for linha in dito:
        print(linha)
    return veredito


def entrega(raiz: Path,
            consultar_pedidos=numeros_dos_pedidos_abertos,
            sem_pedido: bool = False) -> int:
    codigo, atual = corre(COMANDO_DA_BRANCH, cwd=raiz)
    if codigo != 0 or not atual:
        print(FORA_DE_REPOSITORIO)
        return SAIDA_LIMPA
    print(TITULO_ENTREGA.format(Path(raiz).resolve().as_posix(), atual))
    dito_do_que_falta, dito_do_que_sobrou = [], []
    with ThreadPoolExecutor(
            max_workers=MEDIDAS_DA_ENTREGA_AO_MESMO_TEMPO) as grupo:
        arvores = grupo.submit(linhas_do_git, raiz, COMANDO_DAS_ARVORES)
        falta = grupo.submit(o_que_ainda_nao_saiu, raiz, atual,
                             dito_do_que_falta.append)
        sobra = grupo.submit(
            o_que_saiu_e_ficou, raiz, atual, dito_do_que_sobrou.append,
            lambda _: branches_das_arvores(arvores.result()))
        faltou = dito_na_ordem(falta, dito_do_que_falta)
        sobrou = dito_na_ordem(sobra, dito_do_que_sobrou)
    if sem_pedido:
        print(PEDIDO_PULADO_A_PEDIDO.format(BANDEIRA_SEM_O_PEDIDO))
        espera = MEDIDA_PULADA
    else:
        espera = o_que_espera_incorporacao(raiz, atual, consultar_pedidos)
    print(resumo_das_arvores(arvores.result()))
    print(linha_das_categorias(faltou, sobrou, espera))
    return veredito_da_entrega(faltou, sobrou,
                               *([] if sem_pedido else [espera]))


def linha_das_categorias(faltou: int, sobrou: int, espera: int) -> str:
    return CATEGORIAS_DA_ENTREGA.format(faltou, sobrou, espera)


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


def servidores_da_raiz_principal(raiz: Path) -> str:
    codigo, comum = corre(COMANDO_DA_RAIZ_COMUM, cwd=raiz)
    if codigo != 0 or not comum.strip():
        return ""
    principal = Path(comum.strip().splitlines()[-1]).parent
    if mesma_pasta(str(principal), raiz):
        return ""
    try:
        dado = json.loads((principal / ARQUIVO_DA_DECLARACAO_DE_MCP)
                          .read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    declarados = (dado.get(CHAVE_DOS_SERVIDORES_DE_MCP)
                  if isinstance(dado, dict) else None)
    if not isinstance(declarados, dict) or not declarados:
        return ""
    return MCP_SO_NA_RAIZ_PRINCIPAL.format(
        arquivo=ARQUIVO_DA_DECLARACAO_DE_MCP, principal=principal,
        quantos=len(declarados), nomes=", ".join(sorted(declarados)))


def derrubar_a_arvore_do_processo(processo: subprocess.Popen) -> None:
    if processo.poll() is not None:
        return
    try:
        if os.name == "nt":
            subprocess.run([parte.format(processo.pid) for parte in
                            COMANDO_QUE_DERRUBA_A_ARVORE_DO_PROCESSO],
                           capture_output=True, timeout=TEMPO_PARA_DERRUBAR,
                           creationflags=bandeiras_sem_janela())
        else:
            processo.kill()
        processo.wait(timeout=TEMPO_PARA_DERRUBAR)
    except (OSError, subprocess.SubprocessError) as falha:
        print(f"  o processo de pid {processo.pid} não caiu: {falha}",
              file=sys.stderr)


def resposta_ao_aperto_de_mao(processo: subprocess.Popen, tempo: float):
    achada = {}

    def ler():
        for linha in processo.stdout:
            with contextlib.suppress(ValueError):
                dado = json.loads(linha)
                if isinstance(dado, dict) \
                        and dado.get("id") == ID_DO_APERTO_DE_MAO:
                    achada.update(dado)
                    return

    leitor = threading.Thread(target=ler, daemon=True)
    leitor.start()
    leitor.join(tempo)
    return achada


def codigo_de_saida_assentado(processo: subprocess.Popen):
    try:
        return processo.wait(TEMPO_PARA_A_SAIDA_ASSENTAR)
    except subprocess.TimeoutExpired:
        return None


def e_login_vencido(*textos) -> bool:
    juntos = " ".join(str(texto) for texto in textos).lower()
    return any(marca in juntos for marca in MARCAS_DE_LOGIN_VENCIDO)


def motivo_da_queda(resposta: dict, berro: str, saiu, tempo) -> str:
    erro = resposta.get("error")
    if isinstance(erro, dict):
        codigo, mensagem = erro.get("code"), str(erro.get("message", ""))
        if e_login_vencido(mensagem, berro) \
                or (codigo == CODIGO_DE_PARAMETRO_INVALIDO
                    and e_login_vencido(berro)):
            return MOTIVO_LOGIN_VENCIDO.format(codigo)
        return MOTIVO_ERRO.format(codigo, mensagem[:120])
    if e_login_vencido(berro):
        return MOTIVO_LOGIN_VENCIDO.format("InvalidGrant")
    if saiu is not None:
        ultima = (berro.strip().splitlines() or [f"código {saiu}"])[-1]
        return MOTIVO_SAIU.format(ultima[:120])
    return MOTIVO_SEM_RESPOSTA.format(tempo)


def aperto_de_mao(raiz: Path, nome: str, declaracao: dict,
                  tempo: float = TEMPO_DO_APERTO_DE_MAO) -> tuple:
    declaracao = declaracao if isinstance(declaracao, dict) else {}
    tipo = str(declaracao.get("type", "")).lower()
    if tipo in TIPOS_DE_SERVIDOR_REMOTO or declaracao.get("url"):
        return CONEXAO_NAO_MEDIDA, MCP_CONEXAO_NAO_MEDIDA.format(
            nome, tipo or "url")
    comando = os.path.expandvars(str(declaracao.get("command") or ""))
    if not comando:
        return CONEXAO_CAIU, MCP_CONEXAO_CAIU.format(nome, MOTIVO_SEM_COMANDO)
    argumentos = [shutil.which(comando) or comando] + [
        os.path.expandvars(str(a)) for a in declaracao.get("args") or []]
    ambiente = dict(os.environ)
    ambiente.update({chave: os.path.expandvars(str(valor)) for chave, valor
                     in (declaracao.get("env") or {}).items()})
    with tempfile.TemporaryFile() as berros:
        try:
            processo = subprocess.Popen(
                argumentos, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=berros, cwd=raiz, env=ambiente, text=True,
                encoding="utf-8", errors="replace")
        except OSError as falha:
            return CONEXAO_CAIU, MCP_CONEXAO_CAIU.format(
                nome, MOTIVO_NAO_SOBE.format(falha))
        try:
            with contextlib.suppress(OSError):
                processo.stdin.write(json.dumps(PEDIDO_DO_APERTO_DE_MAO) + "\n")
                processo.stdin.flush()
            resposta = resposta_ao_aperto_de_mao(processo, tempo)
            saiu = codigo_de_saida_assentado(processo)
        finally:
            derrubar_a_arvore_do_processo(processo)
        berros.seek(0)
        berro = berros.read().decode("utf-8", "replace")
    if "result" in resposta:
        return CONEXAO_DE_PE, MCP_CONEXAO_DE_PE.format(nome)
    if not resposta and saiu is None and not e_login_vencido(berro):
        return CONEXAO_NAO_MEDIDA, MCP_CONEXAO_SEM_RESPOSTA.format(
            nome, tempo)
    return CONEXAO_CAIU, MCP_CONEXAO_CAIU.format(
        nome, motivo_da_queda(resposta, berro, saiu, tempo))


def conexao_dos_servidores(raiz: Path, declarados: dict,
                           tempo: float) -> tuple:
    nomes = sorted(declarados)
    with ThreadPoolExecutor(max_workers=max(1, len(nomes))) as grupo:
        apertos = list(grupo.map(
            lambda nome: aperto_de_mao(raiz, nome, declarados[nome], tempo),
            nomes))
    caidos = [nome for nome, (estado, _) in zip(nomes, apertos)
              if estado == CONEXAO_CAIU]
    linhas = [MCP_TITULO_DA_CONEXAO.format(tempo)]
    linhas += [linha for _, linha in apertos]
    if caidos:
        linhas.append(MCP_CONEXAO_CAIDOS.format(len(caidos),
                                                ", ".join(caidos)))
    return not caidos, "\n".join(linhas)


def servidores_de_contexto(raiz: Path, casa: Path = None,
                           conexao: bool = False,
                           tempo_da_conexao: float = TEMPO_DO_APERTO_DE_MAO
                           ) -> tuple:
    alvo = raiz / ARQUIVO_DA_DECLARACAO_DE_MCP
    if not alvo.is_file():
        return None, (servidores_da_raiz_principal(raiz)
                      or MCP_SEM_ARQUIVO.format(ARQUIVO_DA_DECLARACAO_DE_MCP))
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
    if not conexao:
        return True, (f"{declaracao}\n{estado}\n"
                      f"{MCP_CONEXAO_NAO_PEDIDA.format(BANDEIRA_DA_CONEXAO)}")
    de_pe, linhas = conexao_dos_servidores(raiz, declarados, tempo_da_conexao)
    return de_pe, f"{declaracao}\n{estado}\n{linhas}"


def o_programa_do_indice() -> str:
    return shutil.which(PROGRAMA_DO_INDICE) or ""


def indice_da_abertura(raiz: Path) -> tuple:
    if not (raiz / INSTRUMENTO_DO_INDICE).is_file():
        return None, INDICE_NAO_INSTALADO.format(INSTRUMENTO_DO_INDICE)
    programa = o_programa_do_indice()
    if not programa:
        return False, INDICE_SEM_O_CK.format(BUSCADOR_DO_INDICE)
    return True, INDICE_DE_PE.format(programa, BUSCADOR_DO_INDICE)


def git_dos_ganchos(raiz: Path, comando: tuple, *valores) -> tuple:
    argumentos = [parte.format(*valores) for parte in comando]
    try:
        codigo, saida = corre_a_lista(argumentos,
                                      tempo=TEMPO_DO_GIT_DOS_GANCHOS, cwd=raiz)
    except (OSError, subprocess.SubprocessError) as falha:
        return type(falha).__name__, "", " ".join(argumentos)
    ultima_linha = saida.strip().splitlines()[-1].strip() if saida.strip() \
        else ""
    return codigo, ultima_linha, " ".join(argumentos)


def commit_dos_ganchos(raiz: Path, ponta: str) -> str:
    codigo, curto, _ = git_dos_ganchos(raiz, COMANDO_DO_COMMIT_DOS_GANCHOS,
                                       ponta)
    return MARCO_DO_COMMIT.format(curto) if codigo == 0 and curto \
        else NENHUM_COMMIT_DE_GANCHO


def avanco_dos_ganchos(raiz: Path, integracao: str, referencia: str) -> str:
    codigo, branch, _ = git_dos_ganchos(raiz, tuple(COMANDO_DA_BRANCH.split()))
    branch = branch if codigo == 0 else ""
    if (branch.lower() in branches_de_longa_duracao(raiz)
            and branch.lower() != integracao.lower()):
        return AVANCO_NUMA_ARVORE_DA_INTEGRACAO.format(
            branch=branch, integracao=integracao, ref=referencia)
    return AVANCO_POR_MESCLA.format(integracao=integracao, ref=referencia)


def ganchos_contra_a_integracao(raiz: Path) -> str:
    integracao = integracao_declarada(raiz)
    if not integracao:
        return GANCHOS_SEM_INTEGRACAO.format(
            arquivo=ARQUIVO_DO_EXECUTOR,
            chave=f"{CHAVE_DAS_BRANCHES}.{CHAVE_DA_INTEGRACAO}")
    referencia = f"{PREFIXO_DO_REMOTO}{integracao}"
    codigo, _, _ = git_dos_ganchos(raiz, COMANDO_DA_REF_DA_INTEGRACAO,
                                   referencia)
    if codigo != 0:
        return GANCHOS_SEM_REF.format(ref=referencia)
    codigo, _, comando = git_dos_ganchos(
        raiz, COMANDO_DOS_GANCHOS_CONTRA_A_REF, referencia)
    if codigo == GANCHOS_IGUAIS:
        return SEM_AVISO_DOS_GANCHOS
    if codigo != GANCHOS_DIFERENTES:
        return GANCHOS_NAO_MEDIDOS_PELO_GIT.format(
            ref=referencia, comando=comando, codigo=codigo)
    codigo, faltam, comando = git_dos_ganchos(
        raiz, COMANDO_DOS_GANCHOS_QUE_FALTAM, referencia)
    if codigo != 0 or not faltam.isdigit():
        return GANCHOS_NAO_MEDIDOS_PELO_GIT.format(
            ref=referencia, comando=comando, codigo=codigo)
    sujos, _, _ = git_dos_ganchos(raiz, COMANDO_DOS_GANCHOS_FORA_DE_COMMIT)
    campos = dict(
        pasta=PASTA_DOS_GANCHOS, ref=referencia, faltam=faltam,
        daqui=commit_dos_ganchos(raiz, "HEAD"),
        dela=commit_dos_ganchos(raiz, referencia),
        sujos=SUFIXO_DOS_GANCHOS_SUJOS if sujos == GANCHOS_DIFERENTES else "")
    if int(faltam) == 0:
        return GANCHOS_SO_DESTA_ARVORE.format(**campos)
    return GANCHOS_DEFASADOS.format(
        avanco=avanco_dos_ganchos(raiz, integracao, referencia), **campos)


def declara_que_a_raiz_espelha(raiz: Path) -> bool:
    codigo, saida = git_da_raiz(raiz, COMANDO_DA_DECLARACAO_DA_RAIZ)
    return codigo == 0 and ultima_linha(saida) == "true"


def git_da_raiz(pasta: Path, comando: tuple, *valores,
                tempo=TEMPO_DO_GIT_DOS_GANCHOS) -> tuple:
    argumentos = [parte.format(*valores) for parte in comando]
    try:
        return corre_a_lista(argumentos, tempo=tempo, cwd=pasta)
    except (OSError, subprocess.SubprocessError) as falha:
        return None, type(falha).__name__


def ultima_linha(texto: str) -> str:
    linhas = [linha.strip() for linha in (texto or "").splitlines()
              if linha.strip()]
    return linhas[-1] if linhas else ""


def arvore_principal(raiz: Path):
    codigo, saida = git_da_raiz(raiz, COMANDO_DA_PASTA_COMUM_DO_GIT)
    comum = ultima_linha(saida) if codigo == 0 else ""
    return Path(comum).parent if comum else None


def commit_curto(pasta: Path, ponta: str) -> str:
    codigo, saida = git_da_raiz(pasta, COMANDO_DO_COMMIT_CURTO, ponta)
    return ultima_linha(saida) if codigo == 0 else ponta


def lista_dos_sujos(sujos: list) -> str:
    lista = ", ".join(sujos[:TETO_DA_LISTA_DE_SUJOS])
    alem = len(sujos) - TETO_DA_LISTA_DE_SUJOS
    return lista + (SUJOS_ALEM_DO_TETO.format(alem) if alem > 0 else "")


def buscar_no_remoto(pasta: Path, ramo: str) -> str:
    argumentos = list(COMANDO_DA_BUSCA_NO_ORIGIN) + ([ramo] if ramo else [])
    buscado = ramo or COMANDO_DA_BUSCA_NO_ORIGIN[-1]
    try:
        processo = subprocess.Popen(
            argumentos, cwd=str(pasta),
            env=dict(os.environ, **AMBIENTE_DA_BUSCA_SEM_PERGUNTA),
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, creationflags=bandeiras_sem_janela())
    except (OSError, subprocess.SubprocessError) as falha:
        return f"a busca de {buscado} não rodou ({type(falha).__name__})"
    try:
        codigo = processo.wait(timeout=TEMPO_DA_BUSCA_NO_REMOTO)
    except subprocess.TimeoutExpired:
        derrubar_a_arvore_do_processo(processo)
        return f"a busca de {buscado} passou de {TEMPO_DA_BUSCA_NO_REMOTO} s"
    if codigo != 0:
        return f"a busca de {buscado} no remoto saiu {codigo}"
    return ""


def instante_em_utc(segundos: float) -> str:
    return time.strftime(FORMATO_DO_INSTANTE, time.gmtime(segundos))


def segundos_do_instante(texto):
    try:
        return float(calendar.timegm(time.strptime(texto, FORMATO_DO_INSTANTE)))
    except (TypeError, ValueError):
        return None


def busca_feita_pela_manutencao(principal: Path, integracao: str,
                                agora: float) -> tuple:
    marca, erro = json_que_se_deixa_ler(
        principal / ARQUIVO_DA_MARCA_DA_MANUTENCAO)
    if not erro and marca is not None and not isinstance(marca, dict):
        erro = MARCA_SEM_FORMA
    if erro:
        return "", MARCA_ILEGIVEL.format(arquivo=ARQUIVO_DA_MARCA_DA_MANUTENCAO,
                                         motivo=erro)
    if marca is None:
        return "", ""
    passos = marca.get(CHAVE_DOS_PASSOS)
    passo = passos.get(PASSO_DA_INTEGRACAO) if isinstance(passos, dict) \
        else None
    rodou = segundos_do_instante(marca.get(CHAVE_DE_QUANDO_RODOU))
    vale = (isinstance(passo, dict)
            and passo.get(CHAVE_DO_ESTADO_DO_PASSO) == ESTADO_OK
            and passo.get(CHAVE_DA_REF_BUSCADA) == integracao
            and rodou is not None
            and 0 <= agora - rodou < JANELA_DA_MANUTENCAO_H * SEGUNDOS_DA_HORA)
    if not vale:
        return "", ""
    return time.strftime(FORMATO_DA_HORA, time.localtime(rodou)), ""


def sessoes_vivas_na_raiz(principal: Path, lar: Path, minha: str,
                          agora: float):
    gancho = (Path(__file__).resolve().parents[NIVEIS_DA_CAMADA_ATE_A_ARVORE]
              / GANCHO_DAS_SESSOES_VIVAS)
    try:
        espec = importlib.util.spec_from_file_location(
            "sessoes_vivas_da_raiz", gancho)
        modulo = importlib.util.module_from_spec(espec)
        espec.loader.exec_module(modulo)
        pasta = modulo.pasta_dos_transcritos(principal, lar)
        vivas = modulo.sessoes_vivas_ao_lado(pasta, minha, agora)
    except Exception:
        return None
    return [apelido[:LETRAS_DO_APELIDO_DA_SESSAO] for _, apelido in vivas]


def avancar_a_raiz(raiz: Path, lar=None, minha=None, agora=None,
                   dizer=print) -> str:
    if not declara_que_a_raiz_espelha(raiz):
        return ""
    if os.environ.get(MARCA_DA_SESSAO_DE_PESQUISA):
        return RAIZ_EM_PESQUISA
    principal = arvore_principal(raiz)
    if principal is None:
        return RAIZ_NAO_MEDIDA.format(
            ref="a integração", motivo="o git não disse onde mora a árvore "
            "principal")
    integracao = integracao_declarada(principal)
    if not integracao:
        return RAIZ_SEM_INTEGRACAO.format(
            arquivo=ARQUIVO_DO_EXECUTOR,
            chave=f"{CHAVE_DAS_BRANCHES}.{CHAVE_DA_INTEGRACAO}")
    referencia = f"{PREFIXO_DO_REMOTO}{integracao}"
    codigo, branch = git_da_raiz(principal, tuple(COMANDO_DA_BRANCH.split()))
    branch = ultima_linha(branch) if codigo == 0 else ""
    if branch != integracao:
        return RAIZ_FORA_DA_INTEGRACAO.format(branch=branch or "?",
                                              integracao=integracao)
    agora = time.time() if agora is None else agora
    hora, marca_torta = busca_feita_pela_manutencao(principal, integracao,
                                                    agora)
    if marca_torta:
        dizer(marca_torta)
    if hora:
        dizer(RAIZ_BUSCADA_PELA_MANUTENCAO.format(ref=referencia, hora=hora))
    falha = "" if hora else buscar_no_remoto(principal, integracao)
    if falha:
        return RAIZ_NAO_MEDIDA.format(ref=referencia, motivo=falha)
    codigo_atras, atras = git_da_raiz(principal, COMANDO_DOS_COMMITS_ENTRE,
                                      "HEAD", referencia)
    codigo_adiante, adiante = git_da_raiz(principal, COMANDO_DOS_COMMITS_ENTRE,
                                          referencia, "HEAD")
    atras, adiante = ultima_linha(atras), ultima_linha(adiante)
    if codigo_atras != 0 or codigo_adiante != 0 or not atras.isdigit() \
            or not adiante.isdigit():
        return RAIZ_NAO_MEDIDA.format(
            ref=referencia, motivo="o git não contou os commits entre a raiz "
            "e a integração")
    codigo, estado = git_da_raiz(principal, COMANDO_DA_MUDANCA_RASTREADA)
    if codigo != 0:
        return RAIZ_NAO_MEDIDA.format(
            ref=referencia, motivo=f"`git status` saiu {codigo}")
    sujos = [linha.strip().split(maxsplit=1)[-1]
             for linha in estado.splitlines() if linha.strip()]
    if sujos:
        return RAIZ_SUJA.format(quantos=len(sujos), lista=lista_dos_sujos(sujos),
                                atras=atras, ref=referencia)
    if int(adiante):
        return RAIZ_DIVERGIU.format(adiante=adiante, ref=referencia)
    if not int(atras):
        return RAIZ_EM_DIA.format(ref=referencia,
                                  curto=commit_curto(principal, "HEAD"))
    vivas = sessoes_vivas_na_raiz(
        principal, Path.home() if lar is None else Path(lar),
        os.environ.get(VARIAVEL_DA_SESSAO_DO_CLIENTE, "") if minha is None
        else minha, agora)
    if vivas is None:
        return RAIZ_NAO_MEDIDA.format(
            ref=referencia, motivo="não se leu se há outra sessão viva na "
            "raiz, e sem isso ela não se troca")
    if vivas:
        return RAIZ_COM_SESSAO_VIVA.format(quantas=len(vivas),
                                           lista=", ".join(vivas),
                                           atras=atras, ref=referencia)
    codigo, saida = git_da_raiz(principal, COMANDO_DO_AVANCO_RAPIDO, referencia,
                                tempo=TEMPO_DO_AVANCO_DA_RAIZ)
    if codigo != 0:
        return RAIZ_AVANCO_RECUSADO.format(
            ref=referencia, motivo=ultima_linha(saida) or codigo)
    return RAIZ_AVANCOU.format(atras=atras, ref=referencia,
                               curto=commit_curto(principal, "HEAD"))


def aviso_do_modulo(raiz: Path, instrumento: str, bandeira: str,
                    rotulo: str) -> str:
    if not (raiz / instrumento).is_file():
        return ""
    try:
        codigo, saida = corre_a_lista(
            [INTERPRETADOR, instrumento, bandeira, "--cwd", str(raiz)],
            tempo=TEMPO_DO_AVISO_DE_MODULO, cwd=raiz)
    except (OSError, subprocess.SubprocessError) as falha:
        return AVISO_DE_MODULO_NAO_MEDIDO.format(rotulo=rotulo,
                                                 motivo=type(falha).__name__)
    if codigo == 0:
        return ""
    ultima = saida.splitlines()[-1].strip() if saida else str(codigo)
    if codigo == SAIDA_DO_MODULO_COM_AVISO:
        return ultima
    return AVISO_DE_MODULO_NAO_MEDIDO.format(rotulo=rotulo, motivo=ultima)


def aviso_do_historico(raiz: Path) -> str:
    return aviso_do_modulo(raiz, INSTRUMENTO_DO_HISTORICO,
                           BANDEIRA_DAS_PENDENTES, ROTULO_DO_HISTORICO)


def modulo_inscrito_de_pe(item) -> bool:
    return isinstance(item, dict) and all(
        isinstance(item.get(campo), str) and item[campo].strip()
        for campo in CAMPOS_DO_MODULO_INSCRITO)


def modulos_inscritos(raiz: Path) -> tuple:
    principal = arvore_principal(raiz) or raiz
    executor, erro = json_que_se_deixa_ler(principal / ARQUIVO_DO_EXECUTOR)
    if erro:
        return [], erro
    inscritos = (executor.get(CHAVE_DOS_AVISOS_DA_ABERTURA)
                 if isinstance(executor, dict) else None)
    if inscritos is None:
        return [], ""
    if not isinstance(inscritos, list):
        return [], INSCRITOS_SEM_LISTA
    de_pe = [item for item in inscritos if modulo_inscrito_de_pe(item)]
    tortos = len(inscritos) - len(de_pe)
    return de_pe, INSCRITOS_TORTOS.format(tortos) if tortos else ""


def avisos_dos_modulos_inscritos(raiz: Path) -> list:
    de_pe, motivo = modulos_inscritos(raiz)
    avisos = [aviso_do_modulo(raiz, *(item[campo]
                                      for campo in CAMPOS_DO_MODULO_INSCRITO))
              for item in de_pe]
    if motivo:
        avisos.append(AVISO_DE_MODULO_NAO_MEDIDO.format(
            rotulo=f"{CHAVE_DOS_AVISOS_DA_ABERTURA} de {ARQUIVO_DO_EXECUTOR}",
            motivo=motivo))
    return [aviso for aviso in avisos if aviso]


def sessao_na_nuvem() -> bool:
    return os.environ.get(VARIAVEL_DA_NUVEM) == "true"


def pecas_da_abertura(raiz: Path, conexao: bool = False) -> list:
    declarado, recado = quadro_declarado(raiz)
    return [instrucoes_da_raiz(raiz),
            servidores_de_contexto(raiz, conexao=conexao),
            (bool(declarado), recado),
            indice_da_abertura(raiz)]


def abertura(raiz: Path, conexao: bool = False) -> int:
    print(f"\n{TITULO_DA_ABERTURA}")
    pecas = pecas_da_abertura(raiz, conexao=conexao)
    for _, recado in pecas:
        print(recado)
    aviso_da_raiz = avancar_a_raiz(raiz)
    if aviso_da_raiz:
        print(aviso_da_raiz)
    aviso_dos_ganchos = ganchos_contra_a_integracao(raiz)
    if aviso_dos_ganchos:
        print(aviso_dos_ganchos)
    if sessao_na_nuvem():
        print(NA_NUVEM_NAO_SE_MEDE.format(
            historico=ROTULO_DO_HISTORICO, chave=CHAVE_DOS_AVISOS_DA_ABERTURA))
    else:
        quadro_de_pe = pecas[2][0]
        aviso_das_encerradas = (aviso_do_historico(raiz) if quadro_de_pe
                                else "")
        if aviso_das_encerradas:
            print(aviso_das_encerradas)
        for aviso in avisos_dos_modulos_inscritos(raiz):
            print(aviso)
    faltam = [ok for ok, _ in pecas if ok is False]
    if faltam:
        print(ABERTURA_INCOMPLETA.format(len(faltam)))
        return SAIDA_COM_ACHADO
    print(ABERTURA_INTEGRA.format(len([ok for ok, _ in pecas if ok])))
    return SAIDA_LIMPA


def passo_cronometrado(fazer, *argumentos) -> dict:
    comeco = time.time()
    feito = fazer(*argumentos)
    return dict(feito, instante=instante_em_utc(comeco),
                segundos=round(time.time() - comeco, 1))


def passo_da_integracao(principal: Path) -> dict:
    integracao = integracao_declarada(principal)
    if not integracao:
        return {CHAVE_DO_ESTADO_DO_PASSO: ESTADO_PULADO,
                CHAVE_DO_MOTIVO_DO_PASSO: f"{ARQUIVO_DO_EXECUTOR} não declara "
                f"{CHAVE_DAS_BRANCHES}.{CHAVE_DA_INTEGRACAO}"}
    falha = buscar_no_remoto(principal, integracao)
    if falha:
        return {CHAVE_DO_ESTADO_DO_PASSO: ESTADO_FALHOU,
                CHAVE_DA_REF_BUSCADA: integracao,
                CHAVE_DO_MOTIVO_DO_PASSO: falha}
    return {CHAVE_DO_ESTADO_DO_PASSO: ESTADO_OK,
            CHAVE_DA_REF_BUSCADA: integracao}


def nome_de_pasta_simples(nome) -> bool:
    return (isinstance(nome, str) and nome not in ("", ".", "..")
            and nome.strip() == nome and Path(nome).name == nome)


def pastas_dos_vizinhos(principal: Path) -> tuple:
    executor, erro = json_que_se_deixa_ler(principal / ARQUIVO_DO_EXECUTOR)
    if erro:
        return None, erro
    cadastros = (executor.get(CHAVE_DOS_CADASTROS)
                 if isinstance(executor, dict) else None)
    nomes = {cadastro.get(CAMPO_DA_PASTA_DO_VIZINHO)
             for cadastro in (cadastros.values()
                              if isinstance(cadastros, dict) else ())
             if isinstance(cadastro, dict)}
    pastas = [principal / PASTA_DOS_VIZINHOS / nome
              for nome in sorted(n for n in nomes if nome_de_pasta_simples(n))]
    return [pasta for pasta in pastas if (pasta / PASTA_DO_GIT).exists()], ""


def falta_o_remoto_da_busca(pasta: Path) -> bool:
    codigo, saida = git_da_raiz(pasta, COMANDO_DOS_REMOTOS)
    return codigo == 0 and COMANDO_DA_BUSCA_NO_ORIGIN[-1] not in saida.split()


def passo_dos_vizinhos(principal: Path) -> dict:
    pastas, erro = pastas_dos_vizinhos(principal)
    if pastas is None:
        return {CHAVE_DO_ESTADO_DO_PASSO: ESTADO_FALHOU,
                CHAVE_DO_MOTIVO_DO_PASSO: f"{ARQUIVO_DO_EXECUTOR}: {erro}"}
    if not pastas:
        return {CHAVE_DO_ESTADO_DO_PASSO: ESTADO_PULADO,
                CHAVE_DO_MOTIVO_DO_PASSO: SEM_VIZINHO_COM_CLONE}
    sem_remoto = [pasta for pasta in pastas if falta_o_remoto_da_busca(pasta)]
    buscaveis = [pasta for pasta in pastas if pasta not in sem_remoto]
    motivo_do_pulo = VIZINHO_SEM_O_REMOTO_DA_BUSCA.format(
        COMANDO_DA_BUSCA_NO_ORIGIN[-1])
    falhas = []
    for pasta in buscaveis:
        falha = buscar_no_remoto(pasta, "")
        if falha:
            falhas.append(f"{pasta.name}: {falha}")
    estado = (ESTADO_FALHOU if falhas
              else ESTADO_OK if buscaveis else ESTADO_PULADO)
    return {CHAVE_DO_ESTADO_DO_PASSO: estado,
            CHAVE_DOS_BUSCADOS: len(buscaveis), CHAVE_DAS_FALHAS: falhas,
            CHAVE_DOS_PULADOS: [f"{pasta.name}: {motivo_do_pulo}"
                                for pasta in sem_remoto]}


def interpretador_com_console() -> str:
    python = Path(INTERPRETADOR)
    com_console = python.with_name(INTERPRETADOR_COM_CONSOLE)
    if (python.name.lower() == INTERPRETADOR_SEM_JANELA
            and com_console.is_file()):
        return str(com_console)
    return INTERPRETADOR


def passo_do_modulo(principal: Path, instrumento: str, bandeiras: tuple,
                    tempo: int) -> dict:
    if not (principal / instrumento).is_file():
        return {CHAVE_DO_ESTADO_DO_PASSO: ESTADO_PULADO,
                CHAVE_DO_MOTIVO_DO_PASSO: MODULO_NAO_INSTALADO.format(
                    instrumento)}
    try:
        codigo, saida = corre_a_lista(
            [interpretador_com_console(), instrumento, *bandeiras, "--cwd",
             str(principal)],
            tempo=tempo, cwd=principal)
    except (OSError, subprocess.SubprocessError) as falha:
        return {CHAVE_DO_ESTADO_DO_PASSO: ESTADO_FALHOU,
                CHAVE_DA_ULTIMA_LINHA: type(falha).__name__}
    return {CHAVE_DO_ESTADO_DO_PASSO: ESTADO_OK if codigo == 0
            else ESTADO_FALHOU,
            CHAVE_DA_ULTIMA_LINHA: ultima_linha(saida) or f"saiu {codigo}"}


def passo_do_indice(principal: Path) -> dict:
    ronda = passo_do_modulo(principal, INSTRUMENTO_DO_INDICE,
                            (BANDEIRA_DA_RONDA_DO_INDICE,),
                            TEMPO_DA_RONDA_DO_INDICE)
    if ronda[CHAVE_DO_ESTADO_DO_PASSO] != ESTADO_OK:
        return ronda
    visto = passo_do_modulo(principal, INSTRUMENTO_DO_INDICE,
                            (BANDEIRA_DO_ESTADO_DO_INDICE,),
                            TEMPO_DO_ESTADO_DO_INDICE)
    return dict(visto, ronda=ronda[CHAVE_DA_ULTIMA_LINHA])


def gravar_a_marca(principal: Path, marca: dict) -> str:
    destino = principal / ARQUIVO_DA_MARCA_DA_MANUTENCAO
    provisorio = destino.with_name(destino.name + SUFIXO_DO_PROVISORIO)
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        provisorio.write_text(json.dumps(marca, ensure_ascii=False, indent=2)
                              + "\n", encoding="utf-8")
        os.replace(provisorio, destino)
    except OSError as falha:
        with contextlib.suppress(OSError):
            provisorio.unlink()
        return f"{type(falha).__name__}: {falha}"
    return ""


def detalhe_do_passo(passo: dict) -> str:
    detalhe = (passo.get(CHAVE_DO_MOTIVO_DO_PASSO)
               or passo.get(CHAVE_DA_ULTIMA_LINHA)
               or "; ".join((passo.get(CHAVE_DAS_FALHAS) or [])
                            + (passo.get(CHAVE_DOS_PULADOS) or [])))
    return f"{SEPARADOR_DO_DETALHE}{detalhe}" if detalhe else ""


def manutencao(raiz: Path) -> int:
    principal = arvore_principal(raiz) or raiz
    comeco = time.time()
    passos = {
        PASSO_DA_INTEGRACAO: passo_cronometrado(passo_da_integracao,
                                                principal),
        PASSO_DOS_VIZINHOS: passo_cronometrado(passo_dos_vizinhos, principal),
        PASSO_DO_HISTORICO: passo_cronometrado(
            passo_do_modulo, principal, INSTRUMENTO_DO_HISTORICO,
            (BANDEIRA_DA_COLHEITA,), TEMPO_DA_COLHEITA),
        PASSO_DO_INDICE: passo_cronometrado(passo_do_indice, principal)}
    print(f"\n{TITULO_DA_MANUTENCAO}")
    for nome, passo in passos.items():
        print(LINHA_DO_PASSO.format(
            nome=nome, estado=passo[CHAVE_DO_ESTADO_DO_PASSO],
            segundos=passo["segundos"], detalhe=detalhe_do_passo(passo)))
    erro = gravar_a_marca(principal, {CHAVE_DE_QUANDO_RODOU:
                                      instante_em_utc(comeco),
                                      CHAVE_DOS_PASSOS: passos})
    if erro:
        print(MARCA_QUE_NAO_SE_GRAVOU.format(
            arquivo=ARQUIVO_DA_MARCA_DA_MANUTENCAO, motivo=erro))
        return SAIDA_COM_ACHADO
    falhos = [nome for nome, passo in passos.items()
              if passo[CHAVE_DO_ESTADO_DO_PASSO] == ESTADO_FALHOU]
    if falhos:
        print(MANUTENCAO_COM_FALHA.format(
            arquivo=ARQUIVO_DA_MARCA_DA_MANUTENCAO, quantos=len(falhos),
            quais=", ".join(falhos)))
        return SAIDA_COM_ACHADO
    print(MANUTENCAO_EM_DIA.format(arquivo=ARQUIVO_DA_MARCA_DA_MANUTENCAO))
    return SAIDA_LIMPA


def agendamento(raiz: Path) -> int:
    principal = arvore_principal(raiz) or raiz
    python = Path(sys.executable)
    sem_janela = python.with_name(INTERPRETADOR_SEM_JANELA)
    interpretador = sem_janela if sem_janela.is_file() else python
    instrumento = principal / CAMINHO_DESTE_INSTRUMENTO
    print(f"\n{TITULO_DO_AGENDAMENTO}")
    if os.name != "nt":
        hora, minuto = HORA_DA_MANUTENCAO.split(":")
        print(AGENDAMENTO_FORA_DO_WINDOWS.format(
            minuto=int(minuto), hora=int(hora),
            acao=f'"{python}" -X utf8 "{instrumento}" {BANDEIRA_DA_MANUTENCAO} '
                 f'--raiz "{principal}"'))
        return SAIDA_LIMPA
    acao = (f'"{interpretador}" -X utf8 "{instrumento}" '
            f'{BANDEIRA_DA_MANUTENCAO} --raiz "{principal}"')
    print(AGENDAMENTO_NO_WINDOWS.format(
        prefixo=PREFIXO_SEM_CONVERSAO, tarefa=NOME_DA_TAREFA.format(
            principal.name), hora=HORA_DA_MANUTENCAO,
        acao=acao.replace('"', '\\"')))
    if interpretador == python:
        print(AGENDAMENTO_SEM_JANELA_AUSENTE.format(INTERPRETADOR_SEM_JANELA,
                                                    python))
    if len(acao) > TETO_DO_COMANDO_DA_TAREFA:
        print(AGENDAMENTO_ACIMA_DO_TETO.format(len(acao),
                                               TETO_DO_COMANDO_DA_TAREFA))
    return SAIDA_LIMPA


def onde_a_issue_nasce(raiz: Path) -> int:
    print(f"\n{TITULO_DO_QUADRO}")
    declarado, recado = quadro_declarado(raiz)
    print(recado)
    return 0 if declarado else 1


def rotulo_do_evento(evento: str) -> str:
    return MAIUSCULA_QUE_ABRE_PALAVRA.sub("_", evento).lower()


def tempo_do_gancho(rotulo: str, tempo) -> int:
    if rotulo in EVENTOS_DE_TEMPO_CURTO:
        pedido = TEMPO_CURTO_PADRAO_S if tempo is None else tempo
        return min(max(pedido, TEMPO_MINIMO_DO_GANCHO_S), TEMPO_CURTO_MAXIMO_S)
    pedido = TEMPO_PADRAO_DO_GANCHO_S if tempo is None else tempo
    return max(pedido, TEMPO_MINIMO_DO_GANCHO_S)


def impressao_do_gancho(rotulo: str, filtro, gancho: dict) -> str:
    identidade = {CHAVE_DO_EVENTO_NA_IMPRESSAO: rotulo, CHAVE_DOS_GANCHOS: [{
        CHAVE_DO_TIPO_DO_GANCHO: TIPO_DO_GANCHO_DE_COMANDO,
        CHAVE_DO_COMANDO: gancho[CHAVE_DO_COMANDO],
        CHAVE_DO_TEMPO_DO_GANCHO: tempo_do_gancho(
            rotulo, gancho.get(CHAVE_DO_TEMPO_DO_GANCHO)),
        CHAVE_DO_GANCHO_ASSINCRONO: False}]}
    if filtro is not None and rotulo not in EVENTOS_QUE_IGNORAM_O_FILTRO:
        identidade[CHAVE_DO_FILTRO_DO_GANCHO] = filtro
    texto = json.dumps(identidade, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False)
    return PREFIXO_DA_IMPRESSAO + hashlib.sha256(
        texto.encode("utf-8")).hexdigest()


def caminho_comparavel(caminho: str) -> str:
    return os.path.normcase(os.path.normpath(
        caminho.removeprefix(PREFIXO_DE_CAMINHO_LITERAL)))


def pasta_do_codex(casa: Path = None) -> Path:
    if casa is not None:
        return casa / PASTA_DO_CODEX_NA_CASA
    return Path(os.environ.get(VARIAVEL_DA_PASTA_DO_CODEX)
                or Path.home() / PASTA_DO_CODEX_NA_CASA)


def confiancas_guardadas(texto_da_configuracao: str) -> dict:
    import tomllib
    lida = tomllib.loads(texto_da_configuracao)
    estados = lida.get(CHAVE_DOS_GANCHOS, {}).get(
        CHAVE_DO_ESTADO_DOS_GANCHOS, {})
    guardadas = {}
    for chave, estado in estados.items():
        partes = chave.rsplit(SEPARADOR_DA_CHAVE_DO_GANCHO,
                              PARTES_DA_CHAVE_DEPOIS_DO_CAMINHO)
        if (len(partes) == PARTES_DA_CHAVE_DEPOIS_DO_CAMINHO + 1
                and isinstance(estado, dict)):
            guardadas[(caminho_comparavel(partes[0]), *partes[1:])] = estado
    return guardadas


def situacao_do_gancho(rotulo: str, grupo: dict, gancho: dict,
                       estado) -> str:
    if (not CAMPOS_QUE_O_GANCHO_EXIGE <= set(gancho)
            <= CAMPOS_DO_GANCHO_QUE_A_IMPRESSAO_REPRODUZ
            or not set(grupo) <= CAMPOS_DO_GRUPO_QUE_A_IMPRESSAO_REPRODUZ
            or gancho[CHAVE_DO_TIPO_DO_GANCHO] != TIPO_DO_GANCHO_DE_COMANDO):
        return GANCHO_FORA_DA_CONTA
    estado = estado or {}
    if estado.get(CHAVE_DO_GANCHO_LIGADO) is False:
        return GANCHO_DESLIGADO
    confiada = estado.get(CHAVE_DA_IMPRESSAO_CONFIADA)
    if not confiada:
        return GANCHO_NUNCA_CONFIADO
    atual = impressao_do_gancho(rotulo, grupo.get(CHAVE_DO_FILTRO_DO_GANCHO),
                                gancho)
    return GANCHO_CONFIADO if confiada == atual else GANCHO_COM_CONFIANCA_VELHA


def ganchos_declarados_ao_codex(declarados: dict):
    for evento, grupos in declarados.get(CHAVE_DOS_GANCHOS, {}).items():
        for n_grupo, grupo in enumerate(grupos):
            for n_gancho, gancho in enumerate(grupo.get(CHAVE_DOS_GANCHOS,
                                                        [])):
                yield rotulo_do_evento(evento), n_grupo, n_gancho, grupo, gancho


def situacoes_da_ponte_do_codex(arquivo: Path, guardadas: dict) -> list:
    caminhos = {caminho_comparavel(os.path.abspath(arquivo)),
                caminho_comparavel(str(arquivo.resolve()))}
    declarados = json.loads(arquivo.read_text(encoding="utf-8"))
    situacoes = []
    for rotulo, n_grupo, n_gancho, grupo, gancho in \
            ganchos_declarados_ao_codex(declarados):
        posicao = (rotulo, str(n_grupo), str(n_gancho))
        estado = next((guardadas[(caminho, *posicao)] for caminho in caminhos
                       if (caminho, *posicao) in guardadas), None)
        situacoes.append((*posicao, situacao_do_gancho(rotulo, grupo, gancho,
                                                       estado)))
    return situacoes


def veredito_da_confianca_do_codex(situacoes: list) -> int:
    for rotulo, n_grupo, n_gancho, situacao in situacoes:
        print(LINHA_DO_GANCHO_DO_CODEX.format(rotulo, n_grupo, n_gancho,
                                              situacao))
    total = len(situacoes)
    so_situacoes = [situacao for *_, situacao in situacoes]
    if so_situacoes.count(GANCHO_CONFIADO) == total:
        print(CODEX_GANCHOS_CONFIADOS.format(total))
        return SAIDA_LIMPA
    if so_situacoes.count(GANCHO_NUNCA_CONFIADO) == total:
        print(CODEX_GANCHOS_NUNCA_CONFIADOS.format(total))
        return SAIDA_LIMPA
    fora_da_conta = so_situacoes.count(GANCHO_FORA_DA_CONTA)
    pulados = total - so_situacoes.count(GANCHO_CONFIADO) - fora_da_conta
    if pulados:
        print(CODEX_GANCHOS_PULADOS.format(pulados, total,
                                           ARQUIVO_DOS_GANCHOS_DO_CODEX))
        return SAIDA_COM_ACHADO
    print(CODEX_GANCHOS_FORA_DA_CONTA.format(fora_da_conta, total))
    return SAIDA_NAO_MEDIDO


def confianca_dos_ganchos_do_codex(raiz: Path, casa: Path = None) -> int:
    print(f"\n{TITULO_DA_CONFIANCA_DO_CODEX}")
    arquivo = raiz / ARQUIVO_DOS_GANCHOS_DO_CODEX
    configuracao = pasta_do_codex(casa) / CONFIGURACAO_DO_CODEX
    if not arquivo.is_file():
        print(CODEX_SEM_PONTE.format(ARQUIVO_DOS_GANCHOS_DO_CODEX))
        return SAIDA_LIMPA
    if not configuracao.is_file():
        print(CODEX_SEM_CONFIGURACAO.format(CONFIGURACAO_DO_CODEX))
        return SAIDA_LIMPA
    try:
        guardadas = confiancas_guardadas(
            configuracao.read_text(encoding="utf-8"))
    except ImportError:
        print(CODEX_SEM_LEITOR_DE_TOML)
        return SAIDA_NAO_MEDIDO
    except (OSError, ValueError, AttributeError):
        print(CODEX_CONFIGURACAO_ILEGIVEL.format(CONFIGURACAO_DO_CODEX))
        return SAIDA_NAO_MEDIDO
    try:
        situacoes = situacoes_da_ponte_do_codex(arquivo, guardadas)
    except (OSError, ValueError, AttributeError, TypeError) as falha:
        print(CODEX_PONTE_ILEGIVEL.format(ARQUIVO_DOS_GANCHOS_DO_CODEX, falha))
        return SAIDA_NAO_MEDIDO
    if not situacoes:
        print(CODEX_SEM_PONTE.format(ARQUIVO_DOS_GANCHOS_DO_CODEX))
        return SAIDA_LIMPA
    return veredito_da_confianca_do_codex(situacoes)


def dias_parado(arquivo: Path, agora: float) -> int:
    return int((agora - arquivo.stat().st_mtime) // SEGUNDOS_DO_DIA)


def e_desvio_de_caminho(atributos: int, etiqueta: int) -> bool:
    if not atributos & MARCA_DE_PONTO_DE_DESVIO:
        return False
    return etiqueta in ETIQUETAS_QUE_DESVIAM_O_CAMINHO


def aponta_para_outro_lugar(caminho: Path) -> bool:
    if caminho.is_symlink():
        return True
    try:
        estado = caminho.lstat()
        atributos = estado.st_file_attributes
    except (AttributeError, OSError):
        return False
    return e_desvio_de_caminho(atributos, getattr(estado, "st_reparse_tag", 0))


def arquivos_do_rascunho(raiz: Path):
    pasta = raiz / RASCUNHO
    if aponta_para_outro_lugar(pasta):
        return None
    achados = []
    for aqui, dentro, nomes in os.walk(pasta):
        atual = Path(aqui)
        dentro[:] = [nome for nome in dentro
                     if not aponta_para_outro_lugar(atual / nome)]
        for nome in nomes:
            arquivo = atual / nome
            if aponta_para_outro_lugar(arquivo) or not arquivo.is_file():
                continue
            if arquivo.relative_to(pasta).parts[0] \
                    in PASTAS_DE_INSTRUMENTO_NO_RASCUNHO:
                continue
            achados.append(arquivo)
    return sorted(achados, key=lambda a: a.as_posix())


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
    if arquivos is None:
        print(RASCUNHO_QUE_E_ATALHO.format(RASCUNHO))
        return 1
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
CAMPO_DA_SESSAO = re.compile(r'"session_id":"([^"]+)"')
TITULO_DA_CONTA = "A CONTA — o que cada execução custou, do que já está gravado"
SEM_EVIDENCIAS = ("sem evidência gravada em {} — a conta não tem o que ler, "
                  "e isso não é achado")
LINHA_DA_EXECUCAO = "  {:<22} US$ {:>7.2f}   atribuído US$ {:>7.2f}"
CONTA_DA_RODADA = ("Somam US$ {:.2f} cobrados em {} execução(ões). Não há "
                   "teto declarado: esta rotina MEDE e não reprova, por "
                   "decisão do dono — número sem procedência não "
                   "vira cobrança, e a procedência se junta rodando.")
TITULO_POR_ETAPA = "POR ETAPA — onde o dinheiro foi parar, somando os ciclos"
LINHA_DA_ETAPA = ("  {:<22} US$ {:>7.2f}   {:>3} execução(ões)   {:>10}")
DURACAO_EM_MINUTOS = "{:.1f} min"
DURACAO_NAO_MEDIDA = "sem relógio"
SEM_ETAPA_MEDIDA = ("nenhuma evidência traz custo: a régua por etapa só vale "
                    "para execução gravada com custo por etapa — o que veio "
                    "antes dela some aqui de propósito, e não vira zero")
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


def _cobrado_no_log(texto: str) -> float:
    ultimo_da_sessao, sem_sessao = {}, 0.0
    for linha in texto.splitlines():
        custo = CAMPO_DO_CUSTO.search(linha)
        if not custo:
            continue
        sessao = CAMPO_DA_SESSAO.search(linha)
        if sessao:
            ultimo_da_sessao[sessao.group(1)] = float(custo.group(1))
        else:
            sem_sessao += float(custo.group(1))
    return sem_sessao + sum(ultimo_da_sessao.values())


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
        cobrado[log.parent.name] = (cobrado.get(log.parent.name, 0.0)
                                    + _cobrado_no_log(texto))
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


def e_a_casa_da_camada(raiz: Path) -> bool:
    return ((raiz / PASTA_DOS_MODULOS).is_dir()
            and not (raiz / REGISTRO_DA_INSTALACAO).is_file())


def commit_do_registro(raiz: Path) -> str:
    try:
        registro = json.loads((raiz / REGISTRO_DA_INSTALACAO).read_text(
            encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    commit = registro.get("commit_da_camada") if isinstance(registro, dict) \
        else None
    return commit if isinstance(commit, str) else ""


def commit_da_arvore(raiz: Path) -> str:
    codigo, saida = corre(COMANDO_DO_COMMIT_DA_ARVORE, cwd=raiz)
    return saida.strip() if codigo == 0 else ""


def versao_da_camada(raiz: Path) -> str:
    commit = (commit_da_arvore(raiz) if e_a_casa_da_camada(raiz)
              else commit_do_registro(raiz))
    return MARCO_DO_COMMIT.format(commit) if commit else NUMERO_NAO_MEDIDO


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
        (MEDIDA_VERSAO, versao_da_camada(raiz)),
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
    medida = medir(raiz)[1]
    paga = medida["largada"]
    if medida["ganchos_nao_medidos"]:
        print(LARGADA_NAO_MEDIDA.format(paga, medida["ganchos_nao_medidos"]))
        return SAIDA_NAO_MEDIDO
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


def modulos_pelo_leitor_do_instalador(escopo: dict, raiz: Path) -> tuple:
    leitor = escopo.get(NOME_DO_LEITOR_DA_CAMADA)
    if leitor is None:
        return None, INSTALADOR_SEM_LEITOR.format(NOME_DO_LEITOR_DA_CAMADA)
    try:
        return leitor(raiz)[1], ""
    except SystemExit as saida:
        return None, str(saida.code)
    except Exception as erro:
        return None, f"{type(erro).__name__}: {erro}"


def matricula_do_instalador(raiz: Path) -> tuple:
    escopo, erro = escopo_do_instalador(raiz)
    if escopo is None:
        return None, erro
    declarados = set()
    for valor in escopo.values():
        if type(valor).__name__ == NOME_DO_GANCHO_DECLARADO:
            declarados.update(CAMINHO_DE_GANCHO.findall(valor.comando))
    modulos, erro = modulos_pelo_leitor_do_instalador(escopo, raiz)
    if modulos is None:
        return None, erro
    por_modulo = set()
    for arquivos in modulos.values():
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
    declarado, do_evento_do_despachante = {}, set()
    for valor in escopo.values():
        if type(valor).__name__ != NOME_DO_GANCHO_DECLARADO:
            continue
        for caminho in CAMINHO_DE_GANCHO.findall(valor.comando):
            if valor.evento == EVENTO_DO_DESPACHANTE:
                do_evento_do_despachante.add(caminho)
                declarado[caminho] = valor.matcher
            elif caminho not in do_evento_do_despachante:
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
    if (raiz / INSTALADOR).is_file() and e_a_casa_da_camada(raiz):
        escopo, erro = escopo_do_instalador(raiz)
        if escopo is None:
            return None, INSTALADOR_ILEGIVEL.format(INSTALADOR, erro)
        modulos, erro = modulos_pelo_leitor_do_instalador(escopo, raiz)
        if modulos is None:
            return None, INSTALADOR_ILEGIVEL.format(INSTALADOR, erro)
        for arquivos in modulos.values():
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


def json_que_se_deixa_ler(caminho: Path) -> tuple:
    if not caminho.is_file():
        return None, ""
    try:
        return json.loads(caminho.read_text(encoding="utf-8")), ""
    except (OSError, ValueError) as erro:
        return None, f"{type(erro).__name__}: {erro}"


def autorizacoes_declaradas_em(dado) -> dict:
    declarado = (dado.get(CHAVE_DAS_AUTORIZACOES) if isinstance(dado, dict)
                 else None)
    return declarado if isinstance(declarado, dict) else {}


def chaves_aposentadas(raiz: Path) -> list:
    avisos = []
    configuracao, erro = json_que_se_deixa_ler(raiz / ARQUIVO_DE_CONFIGURACAO)
    if erro:
        avisos.append(CHAVE_APOSENTADA_NAO_MEDIDA.format(
            ARQUIVO_DE_CONFIGURACAO, erro, CHAVE_APOSENTADA))
    elif CHAVE_APOSENTADA in autorizacoes_declaradas_em(configuracao):
        avisos.append(AVISO_DE_CHAVE_APOSENTADA.format(
            CHAVE_APOSENTADA_NA_CONFIGURACAO, ARQUIVO_DE_CONFIGURACAO))
    executor, erro = json_que_se_deixa_ler(raiz / ARQUIVO_DO_EXECUTOR)
    if erro:
        avisos.append(CHAVE_APOSENTADA_NAO_MEDIDA.format(
            ARQUIVO_DO_EXECUTOR, erro, CHAVE_APOSENTADA))
        return avisos
    cadastros = (executor.get(CHAVE_DOS_CADASTROS)
                 if isinstance(executor, dict) else None)
    com_a_chave = sum(
        1 for cadastro in (cadastros.values()
                           if isinstance(cadastros, dict) else ())
        if CHAVE_APOSENTADA in autorizacoes_declaradas_em(cadastro))
    if com_a_chave:
        avisos.append(AVISO_DE_CHAVE_APOSENTADA.format(
            CHAVE_APOSENTADA_NO_CADASTRO,
            CADASTROS_COM_A_CHAVE_APOSENTADA.format(
                ARQUIVO_DO_EXECUTOR, com_a_chave)))
    return avisos


def chaves(raiz: Path) -> int:
    print(f"\n{TITULO_DAS_CHAVES}")
    for aviso in chaves_aposentadas(raiz):
        print(aviso)
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
    if rel.startswith(PASTA_DOS_COMANDOS_DE_BARRA):
        return PILHA_NAO_CLASSIFICADO, COMANDO_DE_BARRA
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
    briefing = (len((raiz / BRIEFING_DA_SESSAO).read_bytes())
                if (raiz / BRIEFING_DA_SESSAO).is_file() else 0)
    dados = {
        "largada": instrucoes + briefing + catalogo + injetado_por_gancho,
        "instrucoes": instrucoes,
        "briefing": briefing,
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
        LINHA.format("  briefing de abertura, lido inteiro por ordem do "
                     "AGENTS.md", f"{dados['briefing']} bytes"),
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
        opcao = (OPCAO_DO_MODO_UTF8_DO_GANCHO
                 if alvo.parent == raiz / PASTA_DOS_GANCHOS else "")
        codigo, saida = corre(
            f'{INTERPRETADOR_NO_SHELL} {opcao} "{alvo.relative_to(raiz)}" '
            f'{BANDEIRA_DE_TESTE}',
            cwd=raiz, ambiente=ambiente_sem_o_modo_utf8())
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
        fora_do_utf8 = MARCA_DE_BYTE_QUE_NAO_E_UTF8 in saida
        if codigo != 0 or proprio_nada or fora_do_utf8:
            caidos.append(alvo.name)
        linhas.append(LINHA_DE_CASO.format(
            "NADA" if proprio_nada else (
                "OK  " if codigo == 0 and not fora_do_utf8 else "CAIU"),
            f"{alvo.relative_to(raiz)} — {gasto:.1f}s — "
            + (SAIDA_FORA_DO_UTF8 if fora_do_utf8
               else resumo_da_suite(saida))))
    sem_teste = [p.name for p in sorted((raiz / PASTA_DOS_GANCHOS).glob(GLOB_PYTHON))
                 if BANDEIRA_DE_TESTE not in p.read_text(encoding="utf-8",
                                                         errors="replace")]
    for nome in sem_teste:
        linhas.append(LINHA_DE_CASO.format("CAIU", f"{nome} — sem --testar próprio"))
    if (raiz / INSTALADOR).is_file() and not e_a_casa_da_camada(raiz):
        linhas.append(LINHA_DE_CASO.format(
            FORA_DA_PROVA, INSTALADOR_ANTIGO_NA_RAIZ.format(INSTALADOR)))
    elif (raiz / INSTALADOR).is_file():
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
        r = subprocess.run(comando, shell=True, capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           timeout=TEMPO_DE_UM_TESTE, cwd=raiz)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return [linha.strip() for linha in r.stdout.splitlines() if linha.strip()]


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


def corre_e_derruba_a_arvore_no_teto(argumentos: list, tempo: float,
                                     cwd: Path) -> tuple:
    processo = subprocess.Popen(argumentos, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True,
                                encoding="utf-8", errors="replace", cwd=cwd,
                                creationflags=bandeiras_sem_janela())
    try:
        saida, erro = processo.communicate(timeout=tempo)
    except subprocess.TimeoutExpired:
        derrubar_a_arvore_do_processo(processo)
        with contextlib.suppress(subprocess.TimeoutExpired):
            processo.communicate(timeout=TEMPO_PARA_DERRUBAR)
        raise
    return processo.returncode, (saida + erro).strip()


def apagar_a_pasta_de_fora(pasta: Path) -> None:
    try:
        shutil.rmtree(pasta)
    except OSError as falha:
        print(PASTA_DE_FORA_QUE_FICOU.format(pasta.as_posix(), falha))


def rodar_uma_bancada(raiz: Path, caminho: str, teto: float,
                      de_onde: Path = None) -> tuple:
    partida = time.monotonic()
    try:
        codigo, saida = corre_e_derruba_a_arvore_no_teto(
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


def pecas_na_fonte_dos_modulos(raiz: Path) -> list:
    return sorted((raiz / PASTA_DOS_MODULOS).glob(
        f"*/{PASTA_DOS_INSTRUMENTOS}/**/{GLOB_PYTHON}"))


def separar_por_bancada(raiz: Path, tocados: list) -> tuple:
    pecas = {p.relative_to(raiz).as_posix(): p
             for p in (pecas_de_instrumento(raiz)
                       + pecas_na_fonte_dos_modulos(raiz))}
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


def teto_desta_bancada(caminho: str, teto: float, tetos: dict = None) -> float:
    proprios = TETOS_PROPRIOS_DE_BANCADA if tetos is None else tetos
    declarado = proprios.get(
        caminho, proprios.get(Path(caminho).parent.as_posix(), 0))
    return max(teto, declarado)


def orcamento_das_bancadas(com_bancada: list, orcamento: float,
                           teto: float, tetos: dict = None) -> float:
    sobra = sum(teto_desta_bancada(caminho, teto, tetos) - teto
                for caminho in com_bancada)
    return orcamento + sobra


def arvores_vivas_da_listagem(linhas: list, raiz: Path) -> list:
    arvores, podaveis = [], set()
    for linha in linhas:
        if linha.startswith(MARCA_DE_ARVORE_DE_TRABALHO):
            arvores.append(Path(linha[len(MARCA_DE_ARVORE_DE_TRABALHO):]))
        elif linha.startswith(MARCA_DE_ARVORE_PODAVEL) and arvores:
            podaveis.add(arvores[-1])
    return [arvore.as_posix() for arvore in arvores
            if arvore not in podaveis and arvore.resolve() != raiz.resolve()]


def outras_arvores_de_trabalho(raiz: Path):
    linhas = linhas_do_git(raiz, COMANDO_DAS_ARVORES_DE_TRABALHO)
    if linhas is None:
        return None
    return arvores_vivas_da_listagem(linhas, raiz)


def nome_da_branch_medida(linhas) -> str:
    if linhas is None:
        return BRANCH_QUE_O_GIT_NAO_DISSE
    return linhas[0] if linhas else BRANCH_DE_HEAD_DESTACADO


def o_que_a_bancada_sujou(nasceu_antes, nasceu_depois):
    if nasceu_antes is None or nasceu_depois is None:
        return None
    return sorted(set(nasceu_depois) - set(nasceu_antes))


def anunciar_as_outras_arvores(outras) -> None:
    if outras is None:
        print(BANCADA_ARVORES_NAO_MEDIDAS)
    elif outras:
        print(BANCADA_HA_OUTRA_ARVORE.format(", ".join(outras)))


def anunciar_onde_mediu(raiz: Path) -> bool:
    branch = linhas_do_git(raiz, COMANDO_DA_BRANCH_ATUAL)
    print(BANCADA_ONDE_MEDIU.format(raiz.as_posix(),
                                    nome_da_branch_medida(branch)))
    return branch is not None


def bancada_dos_tocados(raiz: Path,
                        orcamento: float = ORCAMENTO_DAS_BANCADAS_TOCADAS,
                        teto: float = TEMPO_DE_UMA_BANCADA_TOCADA,
                        tetos: dict = None) -> int:
    print(f"\n{TITULO_DA_BANCADA}")
    tocados, base = caminhos_que_a_sessao_tocou(raiz)
    if tocados is None:
        print(BANCADA_NAO_MEDIDA.format(base))
        return SAIDA_NAO_MEDIDO
    com_bancada, sem_bancada = separar_por_bancada(raiz, tocados)
    print(BANCADA_O_QUE_TOCOU.format(len(tocados), base, len(com_bancada),
                                     len(sem_bancada)))
    disse_a_branch = anunciar_onde_mediu(raiz)
    for caminho in sem_bancada:
        print(LINHA_DE_CASO.format(FORA_DA_PROVA,
                                   BANCADA_SEM_TESTE.format(caminho)))
    if not com_bancada:
        print(BANCADA_NENHUM_TOCADO)
        outras = [] if tocados else outras_arvores_de_trabalho(raiz)
        anunciar_as_outras_arvores(outras)
        return (SAIDA_LIMPA if disse_a_branch and outras is not None
                else SAIDA_NAO_MEDIDO)
    partida = time.monotonic()
    caidos, nao_couberam, rodadas, fora_do_orcamento = [], [], 0, []
    nasceu_antes = linhas_do_git(raiz, COMANDO_DO_QUE_NASCEU)
    orcamento = orcamento_das_bancadas(com_bancada, orcamento, teto, tetos)
    fora = tempfile.mkdtemp(prefix=PREFIXO_DA_PASTA_DE_FORA)
    try:
        def rodar_se_couber(caminho):
            if time.monotonic() - partida >= orcamento:
                return None
            return rodar_uma_bancada(
                raiz, caminho, teto_desta_bancada(caminho, teto, tetos),
                Path(fora))

        with ThreadPoolExecutor(max_workers=BANCADAS_AO_MESMO_TEMPO) as grupo:
            resultados = grupo.map(rodar_se_couber, com_bancada)
            for caminho, resultado in zip(com_bancada, resultados):
                if resultado is None:
                    fora_do_orcamento.append(caminho)
                    continue
                marca, texto = resultado
                print(LINHA_DE_CASO.format(marca, texto))
                rodadas += 1
                if marca == MARCA_DE_QUE_CAIU:
                    caidos.append(caminho)
                if marca == MARCA_DE_QUE_NAO_COUBE:
                    nao_couberam.append(caminho)
    finally:
        apagar_a_pasta_de_fora(Path(fora))
    sujou = o_que_a_bancada_sujou(
        nasceu_antes, linhas_do_git(raiz, COMANDO_DO_QUE_NASCEU))
    anunciar_o_que_ficou_de_fora(fora_do_orcamento, orcamento)
    ficou_cego = bool(nao_couberam or fora_do_orcamento or sujou is None
                      or not disse_a_branch)
    if sujou is None:
        print(BANCADA_NAO_MEDIDA.format(BANCADA_SUJEIRA_NAO_MEDIDA))
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


def textos_do_assistente(bruto: str) -> list:
    try:
        eventos = json.loads(bruto[bruto.find("["):bruto.rfind("]") + 1])
    except ValueError:
        return []
    if not isinstance(eventos, list):
        return []
    return [bloco.get("text", "") for evento in eventos
            if isinstance(evento, dict)
            and evento.get("type") == TIPO_DA_MENSAGEM_DO_ASSISTENTE
            for bloco in (evento.get("message") or {}).get("content") or []
            if isinstance(bloco, dict)
            and bloco.get("type") == TIPO_DO_BLOCO_DE_TEXTO]


def resposta_da_sessao(bruto: str, chaves: list) -> dict:
    final = str(colher_json(bruto).get("result", ""))
    for texto in [final] + textos_do_assistente(bruto)[::-1]:
        dado = colher_json(texto)
        if any(chave in dado for chave in chaves):
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


def copiar_a_arvore_da_simulacao(raiz: Path, destino: Path) -> str:
    try:
        listagem = subprocess.run(COMANDO_DA_ARVORE_DA_SIMULACAO, cwd=raiz,
                                  capture_output=True,
                                  timeout=TEMPO_DO_GIT_DA_SIMULACAO)
        if listagem.returncode != 0:
            return (listagem.stderr.decode("utf-8", "replace").strip()
                    or "git ls-files falhou")
        nomes = listagem.stdout.decode("utf-8", "replace").split("\0")
        for nome in nomes + list(ARQUIVOS_LOCAIS_DA_SIMULACAO):
            origem = raiz / nome
            if nome and origem.is_file():
                (destino / nome).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(origem, destino / nome)
        subprocess.run(["git", "init", "-q"], cwd=destino,
                       capture_output=True, timeout=TEMPO_DO_GIT_DA_SIMULACAO)
    except (OSError, subprocess.SubprocessError) as falha:
        return str(falha)
    return ""


def apagar_a_copia_da_simulacao(copia: Path) -> str:
    for achado in copia.rglob("*"):
        if achado.is_file():
            with contextlib.suppress(OSError):
                achado.chmod(stat.S_IWRITE | stat.S_IREAD)
    try:
        shutil.rmtree(copia)
    except OSError as falha:
        return COPIA_QUE_FICOU.format(copia, falha)
    return ""


def simular(raiz: Path) -> tuple:
    if not shutil.which("claude"):
        return [SEM_CLAUDE], {"rodou": False}
    if not (raiz / FONTE_DAS_REGRAS).is_file():
        return [SEM_REGRAS], {"rodou": False}
    copia = Path(tempfile.mkdtemp(prefix=PREFIXO_DA_COPIA_DA_SIMULACAO))
    try:
        falha = copiar_a_arvore_da_simulacao(raiz, copia)
        if falha:
            linhas, dados = [SEM_COPIA.format(falha)], {"rodou": False}
        else:
            linhas, dados = simular_na_copia(copia)
    finally:
        aviso = apagar_a_copia_da_simulacao(copia)
    return (linhas + [aviso] if aviso else linhas), dados


def simular_na_copia(raiz: Path) -> tuple:
    fonte = raiz / FONTE_DAS_REGRAS
    quantas = len(json.loads(fonte.read_text(encoding="utf-8"))["regras"])
    alvo = raiz / ARQUIVO_PEDIDO
    alvo.parent.mkdir(parents=True, exist_ok=True)
    with contextlib.suppress(OSError):
        alvo.unlink()

    partida = time.monotonic()
    _, bruto = corre_a_lista(
        ["claude", "-p", PEDIDO.format(arquivo=ARQUIVO_PEDIDO),
         "--output-format", "json", "--verbose",
         "--model", MODELO_DA_SIMULACAO,
         "--allowedTools", FERRAMENTAS_DA_SIMULACAO],
        tempo=TEMPO_DA_SIMULACAO, cwd=raiz)
    parede = time.monotonic() - partida

    sessao = colher_json(bruto)
    gabarito = perguntas(quantas)
    resposta = resposta_da_sessao(bruto, [chave for _, chave, _ in gabarito])
    do_nucleo = [(rotulo, bool(prova(resposta)),
                  "" if prova(resposta) else str(resposta.get(chave, ""))[:44])
                 for rotulo, chave, prova in gabarito]
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
NOMES_DOS_PASSOS = tuple(nome for nome, _titulo, _passo in PASSOS)

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


def passos_desconhecidos(pedidos) -> list:
    return list(dict.fromkeys(pedido for pedido in pedidos
                              if pedido not in NOMES_DOS_PASSOS))


def leitor_de_argumentos() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=DESCRICAO_DA_CLI)
    ap.add_argument("passo", nargs="*",
                    metavar="{" + ",".join(NOMES_DOS_PASSOS) + "}",
                    help="quais passos rodar, entre "
                         + ", ".join(NOMES_DOS_PASSOS)
                         + " (padrão: medir e provar)")
    ap.add_argument("--evidencia", choices=NOMES_DOS_PASSOS,
                    help="emite a evidência de um passo, para o executor de roteiros")
    ap.add_argument("--numero", help="imprime um número só, para virar prova")
    ap.add_argument("--largada", action="store_true",
                    help="cobra o teto de bytes que toda sessão paga")
    ap.add_argument("--abertura", action="store_true",
                    help="prova que a sessão tem instruções, servidores de "
                         "contexto, endereço do quadro e índice de pé")
    ap.add_argument(BANDEIRA_DA_CONEXAO, action="store_true",
                    help="com --abertura, faz o aperto de mão MCP com cada "
                         "servidor stdio declarado e nomeia o que caiu")
    ap.add_argument(BANDEIRA_DA_MANUTENCAO, action="store_true",
                    help="busca a integração e os vizinhos, colhe o histórico "
                         "e roda a ronda do índice; grava a marca que deixa "
                         f"a abertura sem buscar por {JANELA_DA_MANUTENCAO_H} "
                         "h")
    ap.add_argument(BANDEIRA_DO_AGENDAMENTO, action="store_true",
                    help="imprime, sem registrar, o comando que agenda a "
                         "manutenção todo dia")
    ap.add_argument("--entrega", action="store_true",
                    help="prova que nada ficou fora da branch de entrega")
    ap.add_argument(BANDEIRA_SEM_O_PEDIDO, action="store_true",
                    dest="sem_pedido",
                    help="com --entrega, pula a medida do pedido de "
                         "incorporação, para quem a mede por conta própria")
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
    ap.add_argument("--confianca-do-codex", action="store_true",
                    dest="confianca_do_codex",
                    help="compara a impressão de cada gancho do "
                         ".codex/hooks.json com a que o dono confiou no "
                         "Codex, sem chamar o Codex")
    ap.add_argument("--conta", action="store_true",
                    help="mostra o que cada execução gravada custou")
    ap.add_argument("--versao", action="store_true",
                    help="as medidas da versão: versão, largada, custo por "
                         "entrega e acerto de rota via evals, para comparar versões")
    ap.add_argument("--resumo", action="store_true",
                    help="só o JSON, para comparar entre rodadas")
    ap.add_argument("--raiz", default=None,
                    help="a raiz a medir, por extenso; sem ela, o diretório "
                         "atual")
    ap.add_argument(BANDEIRA_DE_TESTE, action="store_true",
                    dest="testar", help="roda os casos deste instrumento")
    return ap


def main() -> int:
    ap = leitor_de_argumentos()
    a = ap.parse_args()
    if desconhecidos := passos_desconhecidos(a.passo):
        ap.error(PASSO_DESCONHECIDO.format(", ".join(desconhecidos),
                                           ", ".join(NOMES_DOS_PASSOS)))

    if a.testar:
        try:
            from testes import testar
        except ModuleNotFoundError as falta:
            if falta.name != NOME_DO_MODULO_DA_BANCADA:
                raise
            print(BANCADA_NAO_VIAJA)
            return 0
        return testar()

    raiz = Path(a.raiz).resolve() if a.raiz else Path.cwd()
    if not (raiz / PASTA_DO_CONHECIMENTO).is_dir():
        sys.exit(FORA_DA_RAIZ.format(PASTA_DO_CONHECIMENTO))

    if a.largada:
        return largada(raiz)

    if a.abertura:
        return abertura(raiz, conexao=a.conexao)

    if a.agendar:
        return agendamento(raiz)

    if a.manutencao:
        return manutencao(raiz)

    if a.entrega:
        return entrega(raiz, sem_pedido=a.sem_pedido)

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

    if a.confianca_do_codex:
        return confianca_dos_ganchos_do_codex(raiz)

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
    for canal in (sys.stdin, sys.stdout, sys.stderr):
        if not getattr(canal, "closed", True) and hasattr(canal, "reconfigure"):
            canal.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
