import functools
import datetime
import re
import json
import os
import shutil
import subprocess
import sys
import textwrap
from collections import namedtuple
from pathlib import Path

LARGURA_DA_REGUA = 79

INSTALADOR_NO_CLONE = "python <pasta do clone do atlas>/montar.py"
ERRO_FONTE_DE_REGRAS_INVALIDA = "{} inválido: {}"
ERRO_IDS_FORA_DE_ORDEM = ("{}: ids devem ser 1..{}, na ordem "
                          "— são citados por número em outras páginas.")
ERRO_FONTE_DO_NUCLEO_INVALIDA = "{} ou {} inválido: {}"
ERRO_SEM_PAGINAS = ("Nenhuma página encontrada. Rode na raiz do repositório "
                    "da camada.")
ERRO_MODULO_DESCONHECIDO = ("Módulo que não existe nesta camada: {}.\n"
                            "Disponíveis: {} "
                            "(veja com: " + INSTALADOR_NO_CLONE
                            + " --modulos)")
ERRO_FORA_DA_RAIZ = ("Rode na raiz do repositório: pasta .git não encontrada "
                     "aqui.")
ERRO_ARGUMENTO_DESCONHECIDO = (
    "Argumento que não existe: {}.\n"
    "Os que existem: {}.\n"
    "Parei sem escrever nada: argumento errado não pode virar montagem "
    "silenciosa numa sessão sem dono por perto.")
CAMINHO_DO_MODULO = "{} → {}"
PASTA_DOS_INSTRUMENTOS = ".agents/"
LOG_COPIA_DE_MODULO_DIVERGE = (
    'A cópia em uso não bate com a fonte do módulo:\n  {}\n'
    '  A fonte é modulos/<nome>/; o que está em uso é cópia gerada.\n'
    '  Edite a fonte e rode --sincronizar, que regrava a cópia.')
LOG_COPIA_DE_MODULO_REGRAVADA = (
    'Cópia em uso regravada a partir da fonte do módulo:\n  {}\n'
    '  A fonte é modulos/<nome>/; a cópia é gerada — nunca a edite à mão.')
ERRO_MODULO_SEM_NOME = (
    "A bandeira {} pede o nome do módulo logo depois dela.\n"
    "Veja os que existem com: " + INSTALADOR_NO_CLONE + " --modulos")
ERRO_CASA_SEM_GIT = (
    "O instalador lê a camada da pasta em que mora, {}, e ela não é a raiz "
    "de um repositório git.\n"
    "Só entra o que o git rastreia: sem ele, não há como separar a camada do "
    "que sobrou no disco.\n"
    "Parei sem escrever nada. Clone o repositório da camada com `git clone` "
    "e rode, de dentro do repositório que vai recebê-la:\n"
    "    " + INSTALADOR_NO_CLONE)
ARQUIVO_DO_REGISTRO_DA_INSTALACAO = ".agents/camada/registro-da-instalacao.json"
COMENTARIO_DO_REGISTRO = (
    "O que a camada instalou aqui: cada arquivo que o montar.py copiou da "
    "pasta da camada e que ficou com o conteúdo dela. Nasce na instalação e "
    "se regrava a cada --atualizar. Não edite à mão: a próxima atualização o "
    "reescreve.")
SECAO_DO_REGISTRO = "\n{}. O registro do que a camada instalou"
LOG_REGISTRO_GRAVADO = "  registrado: {} — {} arquivo(s) da camada"
LOG_REGISTRO_EM_DIA = "  em dia:  {} — {} arquivo(s) da camada"
LOG_A_CASA_NAO_SE_REGISTRA = ("  pulado:  esta é a casa da camada, e casa não "
                              "se registra como destino")


LOG_REGRAS_EM_DIA = "Regras: {} em dia com a fonte."
LOG_REGRAS_FORA_DE_DIA = "Regras: {} fora de dia com {}."
LOG_REGRAS_GERADAS = "Regras: {} gerada de {} ({} regras)."
LOG_INSTRUCOES_EM_DIA = "Instruções: {} em dia com o núcleo."
LOG_INSTRUCOES_FORA_DE_DIA = "Instruções: {} fora de dia com o núcleo."
LOG_INSTRUCOES_GERADAS = "Instruções: {} gerado de {}."
LOG_INSTALADA_EM_DIA = "\nA camada instalada aqui está em dia com a origem."
LOG_INSTALADA_ATRASADA = (
    "\n{} arquivo(s) atrás da origem — rode, daqui, `" + INSTALADOR_NO_CLONE
    + " {}`.")
LOG_PAGINA_ATRASADA = "  atrás: {}"
TETO_DE_ATRASADAS_MOSTRADAS = 10
LOG_INSTRUCOES_DO_DONO = ("Instruções: {} é do repositório — sem a marca de "
                          "gerado, não se reescreve.")
ERRO_SINCRONIZAR_FORA_DE_CASA = (
    "{} regenera, a partir do disco, a página de regras, as instruções, as "
    "cópias de módulo e o espelho das skills, então só roda na casa do "
    "instalador.\nAqui é {}; a casa é {}.\nParei sem escrever nada: daqui, "
    "ele regeraria esses arquivos a partir deste repositório.\n"
    "Para atualizar a camada instalada aqui, use, daqui, "
    + INSTALADOR_NO_CLONE + " {}.")

LOG_TOTAL_DE_PAGINAS = "\n{} páginas {} — camada {}."
ACAO_QUE_VIAJAM = "viajam para quem instala"
ACAO_VERIFICADAS = "verificadas"
LOG_SKILLS_ESPELHADAS = "\nSkills de {} {} {}"
ACAO_ESPELHADAS_PARA = "espelhadas para"
ACAO_VERIFICADAS_CONTRA = "verificadas contra"
LOG_DIVERGENCIA_EM_CASA = "\nDivergência: rode `python montar.py {}`."
LOG_DIVERGENCIA_NO_ALVO = (
    "\nDivergência: a camada instalada aqui está atrás da origem — rode, "
    "daqui, `" + INSTALADOR_NO_CLONE + " {}`.\nO `{}` é da casa do "
    "instalador e recusa aqui: daqui ele regeraria as cópias a partir DESTE "
    "repositório.")
LOG_TUDO_EM_DIA = "\nTudo em dia — nada a sincronizar."

ACAO_COPIADO = "copiado"
ACAO_FORA_DE_DIA = "fora de dia"
ACAO_REMOVIDO = "removido"
ACAO_SOBRANDO = "sobrando"
LOG_ITEM_DO_ESPELHO = "  {}: {}"
LOG_NADA_A_ESPELHAR = "  nada a espelhar (as cópias já estavam em dia)"

LOG_EM_DIA = "  em dia:  {}"
LOG_AJUSTADO = "  ajustado: {} (+{})"
LOG_MANTIDO = "  mantido: {}"
MARCA_DE_COPIA_DIVERGENTE = "DIFERENTE da camada"
LOG_MANTIDO_E_DIVERGENTE = ("  mantido: {} — " + MARCA_DE_COPIA_DIVERGENTE
                            + " deste instalador, e NÃO foi trocado.")
LOG_MANTIDO_SEM_LER = ("  mantido: {} — NÃO LIDO: o arquivo existe e não se "
                       "deixou ler, então não sei se difere da camada.")
LOG_CRIADO = "  criado:  {}"
LOG_TROCADO_NA_ATUALIZACAO = "  trocado: {}"
LOG_CRIADO_NA_ATUALIZACAO = "  criado : {}"

LOG_GANCHO_PULADO = "  pulado:  {} (o gancho não está no disco)"
LOG_GANCHO_EM_DIA = "  em dia:  {} no settings.json"
LOG_GANCHO_LIGADO = "  ligado:  {} no settings.json"
LOG_GANCHO_REESCRITO = ("  reescrito: {} no settings.json — a linha passa ao "
                        "formato que roda em qualquer concha")

LOG_DEVIN_EM_DIA = "  em dia:  configuração do Devin (ponte desligada)"
LOG_DEVIN_AJUSTADO = ("  ajustado: .devin/config.json (ponte desligada, "
                      "negações próprias)")
LOG_SEM_AGENTS_MD = "  pulado: AGENTS.md não existe aqui"
LOG_SEM_MCP_DECLARADO = ("  pulado: .mcp.json não existe aqui — nenhum servidor "
                         "MCP a liberar")
LOG_MCP_LIBERADO = ("  liberado: {} servidor(es) do .mcp.json entraram em "
                    "allowedMcpServers de .claude/settings.local.json — onde a "
                    "organização aplica lista branda, é isto que devolve o "
                    "servidor à sessão")
LOG_MCP_JA_LIBERADO = ("  em dia:  os {} servidor(es) do .mcp.json já estão em "
                       "allowedMcpServers")
LOG_MCP_ESPELHADO_NO_DEVIN = ("  espelhado: {} servidor(es) do .mcp.json em "
                              ".devin/mcp_config.local.json")
LOG_MCP_DEVIN_EM_DIA = "  em dia:  .devin/mcp_config.local.json igual ao .mcp.json"
LOG_INDICE_REGISTRADO = ("  registrado: servidor MCP `indice` no .mcp.json — "
                         "versão presa, nunca @latest")
LOG_INDICE_JA_REGISTRADO = "  em dia:  servidor MCP `indice` já está no .mcp.json"
LOG_ALVOS_JA_EXISTEM = ("  em dia:  .agents/indice/alvos.json já existe — "
                        "os alvos são seus, não os toco")
LOG_ALVOS_SEMEADOS = ("  semeado: .agents/indice/alvos.json com {} alvo(s), "
                      "DESLIGADO. Para indexar sem gastar contexto de sessão, "
                      "rode no terminal: {}")
LOG_ALVOS_SEM_NADA_PARA_INDEXAR = ("  pulado:  nenhum alvo indexável na "
                                   "árvore — alvos.json não nasceu")
LOG_ALVOS_SEM_GIT_PROPRIO = ("  fora:    {} sem `.git` próprio — pasta comum "
                             "não é repositório vizinho, e indexá-la mandaria "
                             "para o índice o que mora ao lado. Ponha à mão "
                             "se quiser mesmo.")
LOG_CONFIGURACAO_ILEGIVEL = ("  AVISO: {} não é JSON válido ({}) — pulei sem "
                             "escrever; conserte o arquivo e rode de novo")
LOG_PONTEIRO_EM_DIA = "  em dia:  o AGENTS.md aponta a lista de regras"
LOG_PONTEIRO_ACRESCENTADO = ("  acrescentado: o endereço da lista de regras, "
                             "no fim do AGENTS.md")
LOG_LISTA_PROTEGIDA_EM_DIA = "  em dia:  lista de branches protegidas"
LOG_LISTA_DE_AUTOMACAO_EM_DIA = ("  em dia:  lista de caminhos da automação")
LOG_LISTA_DE_DIRETIVAS_EM_DIA = (
    "  em dia:  lista de diretivas de ferramenta")
LOG_LISTA_DE_POLITICA_EM_DIA = (
    "  em dia:  lista de caminhos de política")
LOG_CONFIGURACAO_EM_DIA = "  em dia:  configuração do repositório"
LOG_CONFIGURACAO_NO_ENDERECO_VELHO = ("  aviso:   {} virou {} — passe os "
                                      "valores para lá e apague o velho")
LOG_LEITURA_JA_LIVRE = ("  em dia:  leitura livre (nenhum deny aposentado no "
                        "settings.json)")
LOG_DENY_APOSENTADO_REMOVIDO = ("  removido: deny de leitura aposentado ({}) "
                                "— regra 8: ler é livre")
LOG_REGRAS_NATIVAS_EM_DIA = ("  em dia:  regras nativas Edit(...) de cópia "
                             "gerada e de automação no settings.json")
LOG_REGRAS_NATIVAS_ACRESCENTADAS = (
    "  acrescentado: {} regra(s) nativa(s) Edit(...) no settings.json — o "
    "cliente recusa editar cópia gerada e automação mesmo sem o gancho")
MARCA_DE_COMENTARIO = "#"

LOG_ESQUELETO_DE_FORA = ("  fica de fora sem --esqueleto (é para a raiz de um "
                         "workspace)")
LOG_SEM_MODULOS = "  nenhum — módulo entra por `--modulo <nome>` e por mais nada"
LOG_MODULO_INSTALADO_AGORA = "  módulo {}:"
LOG_CAMADA_SEM_MODULOS = "A camada {} não traz nenhum módulo opcional."
LOG_CABECALHO_DOS_MODULOS = "Módulos opcionais da camada {}, em: {}\n"
ESTADO_NAO_INSTALADO = "não instalado"
ESTADO_INSTALADO = "instalado ({} arquivos)"
ESTADO_INSTALADO_PELA_METADE = "instalado pela metade ({} de {})"
LOG_LINHA_DE_MODULO = "  {:<20} {}"
USO_INSTALAR_MODULO = ("\nInstalar:   " + INSTALADOR_NO_CLONE
                       + " --modulo <nome>")
USO_ATUALIZAR_MODULOS = ("Atualizar:  " + INSTALADOR_NO_CLONE
                         + " --atualizar  (só o que já está instalado)")

LOG_CABECALHO_DA_MONTAGEM = "Montando em: {} — camada {}\n"
LOG_CABECALHO_DA_SINCRONIZACAO = "Sincronizando as páginas de: {}\n"
LOG_CABECALHO_DA_VERIFICACAO = "Verificando as páginas de: {}\n"
LOG_CABECALHO_DA_ATUALIZACAO = ("Atualizando a camada em: {} — camada {} "
                                "(piso de migração: instalações da versão {} "
                                "em diante)")
LOG_VERSAO = "camada {}"
MARCO_SEM_COMMIT = "sem commit"
LOG_PRONTO = "\nPronto."

SECAO_DA_MONTAGEM_CONFIGURACAO = "1. Configuração para agentes de IA"
SECAO_DA_MONTAGEM_ESQUELETO = "\n2. Esqueleto do workspace"
SECAO_DA_MONTAGEM_PAGINAS = "\n3. Páginas da camada"
SECAO_DA_MONTAGEM_MODULOS = "\n4. Módulos opcionais"
SECAO_DA_MONTAGEM_SKILLS = "\n5. Skills de {} espelhadas para {}"
NUMERO_DOS_AJUSTES_NA_MONTAGEM = 7

SECAO_DA_ATUALIZACAO_PAGINAS = "1. Páginas"
SECAO_DA_ATUALIZACAO_MODULOS = "\n2. Módulos opcionais"
SECAO_DA_ATUALIZACAO_ESQUELETO = "\n3. Esqueleto do workspace"
SECAO_DA_ATUALIZACAO_SKILLS = "\n4. Skills de {} espelhadas para {}"
NUMERO_DOS_AJUSTES_NA_ATUALIZACAO = 6

SECAO_DOS_AJUSTES = "\n{}. Ajustes garantidos na configuração"
SECAO_DO_VERSIONAMENTO = "\n{}. O git enxerga o que a camada escreveu?"

AJUDA_ABAIXO_DO_PISO = ("Repositório mais velho que o piso: rode a montagem "
                        "de novo — e confira no settings.json se sobrou "
                        "declaração de gancho antiga (caminho relativo): essa "
                        "sai à mão.\n")
AJUDA_DO_FIM_DA_ATUALIZACAO = (
    "\nNão foram REESCRITOS, de propósito: AGENTS.md e CLAUDE.md — instrução\n"
    "é de cada repositório. A única coisa que a atualização acrescenta ao\n"
    "AGENTS.md é o endereço da lista de regras, e só se ele não o tiver:\n"
    "sem isso, regra nova nunca chegaria a quem já montou a camada.\n"
    "Na configuração, só os ajustes acima são garantidos.\n"
    "Módulo que não está aqui não é instalado por --atualizar: peça pelo\n"
    "nome (" + INSTALADOR_NO_CLONE + " --modulos mostra quais existem)."
)
AVISO_DO_INSTALADOR_ANTIGO_NA_RAIZ = (
    "\nAVISO: {} na raiz daqui é o instalador antigo, que a receita de antes "
    "copiava para cá.\nEle não é mais a origem da camada e ficou intacto: "
    "apagar é decisão sua.")
LOG_SEM_GIT = "  pulado: git não encontrado — o ignore não pôde ser verificado"
LOG_GIT_NAO_RESPONDEU = "  pulado: git não respondeu ({})"
LOG_GIT_NAO_RESPONDEU_AO_INDICE = ("  pulado: git não respondeu ao ls-files — "
                                   "o índice não pôde ser verificado")
LOG_VERSIONAMENTO_EM_DIA = "  em dia:  o git versiona os {} arquivos da camada"
AVISO_IGNORADOS = (
    "  AVISO:   {} de {} arquivos da camada\n"
    "           existem no disco e o git os ignora — não chegam ao clone:"
)
AVISO_IGNORADO_ITEM = "             {}  <-  {}"
AVISO_IGNORADOS_RODAPE = (
    "           Conserte a regra (a barra inicial ancora na raiz) ou abra\n"
    "           a exceção. Este script não mexe no ignore que é seu."
)
AVISO_FORA_DO_INDICE = (
    "  AVISO:   {} de {} arquivos da camada\n"
    "           existem no disco e não estão no índice do git — commit\n"
    "           nenhum os leva ao clone nem à sessão na nuvem:"
)
AVISO_FORA_DO_INDICE_ITEM = "             {}"
AVISO_FORA_DO_INDICE_RODAPE = ("           `git add` os põe no índice; "
                               "commitar é de quem revisa.")

CHAVE_DO_TETO_DA_LARGADA = "teto_da_largada_em_bytes"
INSTRUMENTO_DA_CAMADA = ".agents/camada/camada.py"
BANDEIRA_DA_LARGADA = "--largada"
MARCA_DA_LARGADA_MEDIDA = "Largada: "
TEMPO_DA_MEDICAO_DA_LARGADA_S = 120
LOG_TETO_DA_LARGADA_MEDIDO = "  teto da largada: nasceu da medição da árvore recém-montada — {} bytes"
LOG_TETO_DA_LARGADA_EM_DIA = "  em dia:  teto da largada"
LOG_TETO_DA_LARGADA_NAO_MEDIDO = "  aviso:   a largada não foi medida — o teto ficou por declarar em nucleo/configuracao.json"
REGRA_DO_TETO_MEDIDO = (
    "`teto_da_largada_em_bytes` nasceu da medição da instalação em {}: {} "
    "bytes é o que a árvore recém-montada paga em toda sessão, e a rotina "
    "`largada` acusa qualquer salto acima disso. Subir o teto é decisão sua, "
    "escrita aqui — nunca da camada.")
CASO_TETO_DA_LARGADA_NASCE_MEDIDO = ("a instalação nasce com o teto da largada medido na árvore recém-montada")
CASO_TETO_DA_LARGADA_DECLARADO_FICA = ("teto já declarado pelo dono não é reescrito pela medição")
CASO_MOLDE_E_JSON = "o molde da configuração é JSON válido"
CASO_MOLDE_POR_PREENCHER = ("o molde nasce por preencher: ${...} no "
                            "repositório das issues")
CASO_MOLDE_MANDA_PERGUNTAR = ("o molde manda perguntar em vez de criar issue "
                              "com ${...} sem valor")
CASO_MOLDE_CHEGA_AO_REPOSITORIO = "repositório sem a camada ganha o molde em {}"
CASO_ATUALIZACAO_NAO_REESCREVE = ("a atualização NÃO reescreve o que o "
                                  "repositório preencheu")
CASO_ENDERECO_VELHO_AVISADO = ("o repositório parado no endereço velho é "
                               "avisado, não sobrescrito em silêncio")
CASO_CONFIGURACAO_FORA_DE_PAGINAS = ("a configuração do repositório não viaja "
                                     "entre as páginas da camada")
CASO_CONFIGURACAO_FORA_DE_FONTES = ("a configuração do repositório não entra "
                                    "no FONTES")
CASO_CACHE_DE_EXECUCAO_FICA_FORA = ("cache de execução (__pycache__, .pyc) não "
                                    "entra na camada lida nem no espelho das "
                                    "skills")
CASO_SEM_GITIGNORE_NAO_NASCE = (
    "o executor NÃO nasce enquanto o .gitignore não esconder o caminho — o "
    "endereço nomeia repositório e conta")
CASO_COM_GITIGNORE_NASCE = (
    "com o .gitignore já escondendo o caminho, o executor nasce no destino")
CASO_ENDERECO_ENTRA_NO_LUGAR = (
    "o endereço informado entra no lugar da marca do exemplo")
CASO_O_RESTO_SEGUE_POR_PREENCHER = (
    "o que a instalação não pergunta segue por preencher: conta, quadro e "
    "caixas só pesam quando um roteiro os cita")
CASO_NAO_SOBRESCREVE_O_QUE_JA_EXISTE = (
    "executor que já existe no destino não é tocado")
CASO_ENDERECO_TORTO_NAO_NASCE = (
    "endereço fora da forma dono/repositório não vira arquivo")
CASO_SEM_QUEM_RESPONDA_NASCE_COM_OS_PADROES = (
    "sem bandeira e sem ninguém para responder, o executor nasce com os "
    "padrões e diz que o endereço ficou por preencher, em vez de travar")
CASO_A_RESPOSTA_ENTRA_NO_EXECUTOR = (
    "modo, padrão de branch e integração respondidos entram no executor")
CASO_RESPOSTA_QUE_NAO_SERVE_FICA_O_PADRAO = (
    "modo que não existe e padrão de branch sem <numero> não entram: fica o "
    "padrão")
CASO_BRANCH_QUE_O_GIT_RECUSA_NAO_ENTRA = (
    "padrão de branch com espaço e integração com .. não entram: o git "
    "recusaria os dois nomes, e fica o padrão")
CASO_ENDERECO_PEDIDO_NAO_SE_PERGUNTA = (
    "com o endereço dado pela bandeira, ele não se pergunta, e o resto sim")
CASO_O_PADRAO_VEM_DO_REMOTO = (
    "o padrão do endereço vem do remoto origin, e o da integração, da branch "
    "atual quando o remoto não diz a dele")
CASO_OBSERVABILIDADE_E_INSIGHTS_FORA_DO_PADRAO = (
    "observabilidade e insights não vêm ligados: quem usa pede pelo nome")
CASO_ATUALIZAR_NAO_INSTALA_MODULO_AUSENTE = (
    "--atualizar não instala módulo que não estava aqui, nem os do padrão")
CASO_O_MOLDE_SO_CITA_SKILL_QUE_EXISTE = (
    "o AGENTS.md de uma instalação nova só cita skill que existe na camada")
CASO_A_BANDEIRA_ACEITA_IGUAL = "a bandeira do quadro aceita a forma com igual"
CASO_A_FORMA_DO_ENDERECO_E_MEDIDA = (
    "a forma do endereço é medida: um pedaço só, três pedaços e espaço no nome "
    "não passam")
FALHA_DO_CASO = "  FALHOU — {}"
RESUMO_DE_FALHA = "FALHOU: {} de {} casos"
RESUMO_DE_SUCESSO = ("OK: {} casos — configuração escrita uma vez, argumento "
                     "desconhecido recusado, cópia de módulo verificada")
CASO_LANCADOR_RODA_PYTHON_3 = ("o lançador, rodado pelo bash, acha um "
                               "interpretador que responde que é da série 3")
CASO_MARCADOR_SAI_DO_COMANDO = ("o comando do gancho sai sem marcador — "
                                "nenhum gancho nasce com <interpretador>")
CASO_TODO_GANCHO_CHAMA_O_INTERPRETADOR = (
    "toda linha de gancho começa pelo interpretador medido nesta máquina, e "
    "nenhuma nomeia python3 fixo — o atalho da loja está no PATH e não roda")
CASO_SEM_PYTHON_O_GANCHO_VOLTA_AO_LANCADOR = (
    "sem interpretador que responda, a linha volta ao lançador — que sonda a "
    "cada execução, em vez de nascer apontando para o nada")
CASO_CAMINHO_COM_ESPACO_VAI_ENTRE_ASPAS = (
    "interpretador com espaço no caminho entra entre aspas, senão o shell "
    "parte o comando em dois")
CASO_GANCHO_COM_OUTRO_INTERPRETADOR_E_REESCRITO = (
    "gancho já declarado com outro interpretador é reescrito no lugar para "
    "o lançador, sem duplicar")
CASO_GANCHO_DE_OUTRO_ARQUIVO_NAO_CONTA = (
    "gancho de outro arquivo não é confundido com o declarado")
CASO_ARVORE_VIRGEM_RECEBE_O_LANCADOR = (
    "a árvore virgem montada recebe o lançador, um settings.json sem python3 "
    "e o atributo de quebra de linha")
CASO_COPIA_DIVERGENTE_E_DITA = (
    "instalar módulo sem sobrescrever NÃO troca a cópia que já existe, e "
    "quando ela difere da camada diz isso por extenso, com o comando que "
    "iguala — o `mantido` calado fez uma sessão depurar defeito que não "
    "existia, rodando a cópia velha enquanto lia a fonte nova")
CASO_COPIA_IGUAL_SEGUE_SO_MANTIDA = (
    "das cópias mantidas, só a divergente ganha o alarme: a igual segue "
    "`mantido`, senão o aviso vira ruído")
CASO_ARQUIVO_BINARIO_NAO_SE_NORMALIZA = (
    "fim de linha só se iguala em arquivo de TEXTO: em arquivo binário, byte "
    "diferente é arquivo diferente")
CASO_ARVORE_VIRGEM_TEM_TODA_CERCA_DO_DESPACHANTE = (
    "toda cerca que o despachante instalado lista chegou à árvore virgem — "
    "o despachante nega por conta da cerca que não carrega, então cerca "
    "listada e fora da camada tranca a instalação inteira")
CASO_ARVORE_VIRGEM_DEIXA_LER = (
    "na árvore virgem, o despachante instalado deixa passar uma leitura "
    "comum: instalação que recusa o primeiro Read nasceu trancada")
CASO_ARVORE_VIRGEM_LIGA_A_COBRANCA_DO_CLONE = (
    "o aviso de clone atrasado chega à árvore virgem com as DUAS ligações: "
    "a de antes da ferramenta, pelo despachante, e a de fim de turno, no "
    "settings.json")
BLOCO_DAS_CERCAS_NO_DESPACHANTE = re.compile(r"^CERCAS = \((.*?)^\)",
                                             re.M | re.S)
CERCA_NO_DESPACHANTE = re.compile(r'\("([A-Za-z0-9_-]+)",\s*"[^"]*"')
CASO_SEM_PAGINA_NAO_E_DO_DONO = ("AGENTS.md que não existe não é do dono — a "
                                 "instalação pode criá-lo")
CASO_PAGINA_MARCADA_E_DA_CAMADA = ("AGENTS.md com a marca de gerado é da "
                                   "camada, e se reescreve")
CASO_PAGINA_SEM_MARCA_E_DO_DONO = ("AGENTS.md sem a marca é do repositório, e "
                                   "não se toca")
CASO_SINCRONIZAR_SO_EM_CASA = ("--sincronizar para fora da casa do "
                               "instalador, antes de escrever")
CASO_SINCRONIZAR_EM_CASA_PASSA = "--sincronizar passa calado na casa dele"
CASO_AUTORIZACAO_NASCE_NEGADA = ("toda autorização do molde nasce em false — "
                                 "omissão não é permissão, regra 9")
CASO_MAIN_ENTRA_POR_INCORPORACAO = ("o molde declara a main como branch de "
                                    "incorporação, não de gravação")
CASO_CONSELHO_EM_CASA = "em casa, a divergência manda sincronizar"
CASO_ALVO_EM_DIA_NAO_ACUSA = ("alvo com a camada em dia não acusa nada — o "
                              "instalador não grita por módulo que não viaja")
CASO_ALVO_ATRASADO_ACUSA = "alvo com página atrás da origem é acusado pelo nome"
CASO_ALVO_SEM_PAGINA_ACUSA = "página que falta no alvo conta como atrás"
CASO_CONSELHO_NO_ALVO = ("no alvo, a divergência manda atualizar — nunca um "
                         "comando que recusaria ali")
REPOSITORIO_DO_TESTE = "repositorio/deles"
TEXTO_QUALQUER_DO_TESTE = "valor velho\n"
VALOR_FICTICIO_DA_SENHA_NO_ESPELHO = "valor-ficticio-que-nao-pode-aparecer"
CASO_BANDEIRA_FANTASMA_ACUSADA = ("bandeira que não existe é acusada pelo "
                                  "nome, antes de qualquer escrita")
CASO_BANDEIRAS_DE_VERDADE_PASSAM = "toda bandeira do contrato passa calada"
CASO_MODULO_COM_IGUAL_PASSA = "a forma --modulo=<nome> não é confundida com fantasma"
CASO_VALOR_DE_MODULO_NAO_E_BANDEIRA = ("o nome do módulo não é lido como "
                                       "bandeira")
CASO_POSICIONAL_TORTO_ACUSADO = ("argumento sem os traços também é "
                                 "acusado, não vira montagem")
CASO_MODULO_SEM_NOME_PARA = "--modulo sem nome para, em vez de montar tudo"
CASO_PROCEDENCIA_DE_PAGINA_VIVA_ENTRA = ("a regra cita a procedência quando a página dela viaja com a camada")
CASO_PROCEDENCIA_DE_PAGINA_MORTA_SAI = ("a regra cala a procedência de página que não viaja — o endereço não existe para quem instala, e citar só na origem deixava toda árvore instalada fora de dia; o da fonte fica esperando a página viajar")
CASO_ESQUELETO_BATE_COM_O_DISCO = ("cada peça do esqueleto embutida no instalador bate com o arquivo em disco quando ele existe: {}")
CASO_REGRAS_SEM_CABECALHO = ("a página de regras nasce pelo aviso de gerada — cabeçalho de site morreu junto com o site")
CASO_COPIA_IGUAL_CALA = "cópia igual à fonte do módulo não vira ruído"
CASO_COPIA_DIVERGENTE_ACUSADA = ("cópia em uso que diverge da fonte do "
                                 "módulo é acusada pelo caminho")
CASO_ROTEIRO_DIVERGENTE_ACUSADO = ("roteiro em uso que diverge da fonte do "
                                   "módulo também é acusado — o conserto que "
                                   "fica só na cópia é publicado ao contrário")
CASO_COPIA_REGRAVADA_DA_FONTE = ("sincronizar escrevendo regrava a cópia em "
                                 "uso a partir da fonte — fim da cópia à mão")
CASO_COPIA_EM_DIA_NAO_REESCREVE = ("cópia em dia não é reescrita — "
                                   "sincronizar de novo é silêncio")
CASO_COPIA_AUSENTE_NAO_E_INSTALADA = ("arquivo de fonte sem cópia em uso não "
                                      "é instalado à força — quem não "
                                      "instalou o módulo não o ganha")
CASO_MOLDE_SEGUE_INTACTO = ("território do repositório não é regravado — o "
                            "molde de conhecimento fica como o dono deixou")
CASO_SEM_MCP_NADA_NASCE = ("sem .mcp.json, nenhum dos três arquivos nasce — "
                           "liberar o nada criaria settings.local vazio")
CASO_LIBERACAO_SAI_DA_DECLARACAO = ("a liberação sai do .mcp.json: stdio vira "
                                    "serverCommand exato, http vira serverUrl, "
                                    "o resto do settings.local fica")
CASO_LIBERACAO_NAO_DUPLICA = "rodar de novo não duplica entrada"
CASO_DEVIN_RECEBE_O_ESPELHO = ("o Devin recebe o mesmo mcpServers em "
                               "mcp_config.local.json")
CASO_ESPELHO_DO_DEVIN_FICA_FORA_DO_GIT = ("o espelho do Devin é pessoal: "
                                          ".devin/.gitignore o exclui")
CASO_INDICE_ENTRA_SEM_APAGAR_OS_OUTROS = ("o módulo índice registra o servidor "
                                          "`indice` no .mcp.json sem tocar nos "
                                          "outros, com a versão presa")
CASO_INDICE_DO_DONO_NAO_E_SOBRESCRITO = ("entrada `indice` que o dono já tem "
                                         "não é sobrescrita")
CASO_ALVOS_NASCEM_DESLIGADOS = ("o alvos.json semeado traz só os alvos que "
                                "existem na árvore, cada vizinho de projetos/ "
                                "entre eles, e nasce com ligado=false — quem "
                                "liga é o dono")
CASO_ALVOS_NAO_MANDA_RODAR_ATALHO_DA_LOJA = (
    "a receita do alvos.json semeado chama o interpretador medido nesta "
    "máquina, nunca um `python3` fixo — que no Windows é o atalho da loja")
CASO_ALVOS_SO_QUEM_TEM_GIT_PROPRIO = ("pasta comum dentro de projetos/ fica "
                                      "FORA dos alvos do índice — sem `.git` "
                                      "próprio o git de dentro dela responde "
                                      "pela árvore de cima, e `git -C` nunca "
                                      "acusa a diferença — e o que ficou fora "
                                      "é dito em voz alta")
CASO_ALVOS_DO_DONO_NAO_SAO_TOCADOS = ("alvos.json que o dono já tem não é "
                                      "sobrescrito pela instalação: os "
                                      "caminhos são da máquina dele")
CASO_INDICE_NO_WINDOWS_PASSA_PELO_CMD = ("no Windows o npx passa por cmd /c, "
                                         "senão o servidor não sobe")
CASO_JSON_QUEBRADO_AVISA_E_NAO_ESCREVE = ("settings.local quebrado: avisa e não "
                                          "escreve por cima")
CASO_MOLDE_DO_REPOSITORIO_NAO_CONTA = ("subpasta de conhecimento/ é território "
                                       "do repositório, e não se compara")
CASO_MONTAGEM_INTEIRA_RODA = ("a montagem inteira roda numa árvore nova — sem isto, nome que sumiu do topo só aparece na máquina de quem instala")
CASO_MONTAGEM_ENTREGA_AS_INSTRUCOES = ("a montagem deixa as instruções no destino — é o arquivo pelo qual toda sessão começa")
CASO_INSTRUCOES_DIZEM_ONDE_A_ISSUE_NASCE = (
    "as instruções dizem onde a issue nasce, pelo caminho e nunca pelo valor — "
    "sem isso a sessão procura no repositório de código e o zero parece "
    "resposta")
CASO_INSTRUCOES_NAO_CARREGAM_O_ENDERECO = (
    "as instruções NÃO carregam endereço nenhum: o valor mora em arquivo local "
    "e não viaja em texto rastreado")
CASO_CHEGADA_MUTILADA_ACUSA = ("arquivo de módulo instalado e depois "
                               "mutilado é acusado, nomeando-o")
CASO_CHEGADA_INTEIRA_CALA = ("a mesma árvore, sem mutilar, sai em dia")
CASO_INSTALACAO_FRESCA_NAO_CAI_NO_RAMO_ERRADO = ("instalação fresca, sem modulos/ de origem, cai no ramo de ""verificar_a_camada_instalada — não no de sincronizar")
CASO_TERRITORIO_NAO_E_COBRADO = ("arquivo sob conhecimento/<subpasta>/ do "
                                 "módulo, que é território do repositório, "
                                 "não é cobrado pela prova de chegada")
CASO_NAO_RASTREADO_NAO_E_INSTALADO = (
    "arquivo não rastreado dentro de uma pasta da camada, no clone, não é "
    "instalado — nem como página, nem como arquivo de módulo")
CASO_CASA_SEM_GIT_E_RECUSADA = (
    "pasta do instalador que não é repositório git: a instalação é recusada "
    "sem escrever nada no destino, e o recado manda clonar")
CASO_REGISTRO_LISTA_O_QUE_FOI_ESCRITO = (
    "o destino ganha o registro do que foi instalado, e ele lista "
    "exatamente os arquivos da camada que a instalação escreveu")
CASO_REGISTRO_NOMEIA_O_COMMIT = (
    "o registro nomeia o commit da pasta da camada, o marco que muda a cada "
    "entrega, e não traz mais o número de versão congelado")
CASO_MODULO_SOLTO_NAO_TIRA_PAGINA = (
    "pasta de módulo não rastreada, no clone, não tira da instalação a "
    "página rastreada que ela repete")
CASO_A_CASA_NAO_SE_REGISTRA = (
    "a casa da camada não grava registro de instalação em si mesma: o "
    "registro é o que separa destino de casa")
CASO_VERSAO_E_O_COMMIT = (
    "--versao diz o commit da pasta do instalador; pasta sem git é recusada "
    "com o recado de clonar")
CASO_ATUALIZACAO_AVISA_DO_INSTALADOR_ANTIGO = (
    "atualização sobre árvore com o montar.py antigo na raiz avisa que ele "
    "não é mais a origem, e o deixa intacto")
CASO_REGRAS_NATIVAS_DE_EDICAO = (
    "a atualização grava no settings.json as regras nativas Edit(...) do "
    "espelho das skills, da automação e das cópias de módulo instaladas, "
    "sem o território, sem repetir e sem tirar a regra que já estava lá")
CASO_SINCRONIZAR_NAO_GRAVA_O_INSTALADOR = (
    "sincronizar numa casa com fonte editada não grava o instalador: a "
    "camada viaja lida da pasta, e o montar.py não carrega cópia dela")
CASO_ATUALIZACAO_PRESERVA_O_PROPRIO = (
    "atualização sobre árvore instalada, com arquivos próprios nas pastas da "
    "camada e sob conhecimento/: os próprios ficam intactos, byte a byte, e "
    "os da camada ficam em dia")


BANDEIRA_TESTAR = "--testar"
BANDEIRA_VERSAO = "--versao"
BANDEIRA_MODULOS = "--modulos"
BANDEIRA_MODULO = "--modulo"
BANDEIRA_MODULO_COM_IGUAL = "--modulo="
BANDEIRA_VERIFICAR = "--verificar"
BANDEIRA_SINCRONIZAR = "--sincronizar"
BANDEIRA_ATUALIZAR = "--atualizar"
BANDEIRA_ESQUELETO = "--esqueleto"
BANDEIRA_DEVIN = "--devin"
BANDEIRA_CODEX = "--codex"
BANDEIRA_ESCREVER = "--escrever"
BANDEIRA_DO_QUADRO = "--repositorio-das-issues"
BANDEIRA_DO_QUADRO_COM_IGUAL = BANDEIRA_DO_QUADRO + "="
BANDEIRAS_CONHECIDAS = (BANDEIRA_TESTAR, BANDEIRA_VERSAO,
                        BANDEIRA_MODULOS, BANDEIRA_MODULO,
                        BANDEIRA_VERIFICAR, BANDEIRA_SINCRONIZAR,
                        BANDEIRA_ATUALIZAR, BANDEIRA_ESQUELETO,
                        BANDEIRA_DEVIN,
                        BANDEIRA_CODEX, BANDEIRA_ESCREVER,
                        BANDEIRA_DO_QUADRO)

ARQUIVO_DO_LANCADOR = ".claude/hooks/interpretador.sh"
SHELL_DO_LANCADOR = "bash"
OPCAO_QUE_LIGA_O_MODO_UTF8 = "-X utf8"
ARQUIVO_DA_PONTE = ".agents/travessia/ponte.py"
ARQUIVO_DOS_GANCHOS_DA_OUTRA = ".devin/hooks.v1.json"
PASTA_DO_AGENTE_SEM_BARRA = ".codex"
ARQUIVO_DE_CONFIGURACAO_DO_AGENTE_SEM_BARRA = "config.toml"
SECAO_DO_SERVIDOR_NO_TOML = "[mcp_servers.{}]"
SECAO_DO_AMBIENTE_NO_TOML = "[mcp_servers.{}.env]"
CHAVE_DO_AMBIENTE_DO_MCP = "env"
MARCA_DE_VARIAVEL_POR_PREENCHER = "${"
MARCADOR_COMPLETO_DE_VARIAVEL = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
NOME_DE_VARIAVEL = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
SUFIXO_DA_COPIA_DE_SEGURANCA = ".antes-do-atlas"
TITULO_DO_ESPELHO_SEM_BARRA = (
    "\nO ESPELHO DOS SERVIDORES DE CONTEXTO — para o agente que lê "
    "{}/{}")
ENSAIO_DO_ESPELHO = (
    "\nENSAIO: nada foi escrito. Isto é o que entraria no arquivo, e "
    "`{} {}` escreve, guardando cópia do arquivo de antes:")
ESPELHO_SEM_DECLARACAO = (
    "  {} não declara servidor nenhum aqui — não há o que espelhar.")
ESPELHO_SEM_ARQUIVO_DE_DESTINO = (
    "  {} não existe nesta máquina — o agente que o lê não está instalado, "
    "ou\n  nunca abriu. Nada foi escrito.")
ESPELHO_FORA_POR_FALTA_DE_COMANDO = (
    "  fora: {} não declara comando — quem o serve é o próprio agente, não "
    "esta máquina.")
ESPELHO_PEDE_VARIAVEL = (
    "  {} espera no ambiente: {}. Exporte-as antes de abrir a sessão: o "
    "valor\n  não entra em arquivo nenhum, e sem elas o servidor sobe e não "
    "responde.")
ESPELHO_RECUSOU_NOME = (
    "  {} declara o que não é nome de variável, e isso ficou fora da lista "
    "de\n  variáveis liberadas: {}. O conteúdo não é repetido aqui, porque "
    "chave\n  torta pode trazer o próprio segredo colado. Nome é letra ou "
    "sublinhado,\n  seguido de letra, dígito ou sublinhado. Corrija na "
    "declaração do servidor.")
RECUSA_DE_CHAVE_DO_AMBIENTE = "a chave nº {} de `env`"
RECUSA_DE_ITEM_DA_LISTA = "o item nº {} de `env_vars`"
RECUSA_DA_LISTA_QUE_NAO_E_LISTA = "`env_vars` inteiro, que não é lista"
ESPELHO_ESCRITO = (
    "\nEscrito em {}: {} servidor(es). A cópia de antes ficou em {}.")
ESPELHO_EM_DIA = "\nJá estava em dia: {} servidor(es), nada a reescrever."
ARQUIVO_DOS_GANCHOS_DO_AGENTE_SEM_BARRA = ".codex/hooks.json"
COMANDO_DA_PONTE_SEM_BARRA = (f"{SHELL_DO_LANCADOR} {ARQUIVO_DO_LANCADOR} "
                              f"{OPCAO_QUE_LIGA_O_MODO_UTF8} "
                              f"{ARQUIVO_DA_PONTE} --codex")
EVENTOS_DA_PONTE_SEM_BARRA = ("PreToolUse", "SessionStart", "Stop")
TEMPO_DA_PONTE_SEM_BARRA_S = 60
GANCHOS_DO_AGENTE_SEM_BARRA = {
    "hooks": {evento: [{"hooks": [{"type": "command",
                                   "command": COMANDO_DA_PONTE_SEM_BARRA,
                                   "timeout": TEMPO_DA_PONTE_SEM_BARRA_S}]}]
              for evento in EVENTOS_DA_PONTE_SEM_BARRA}}
LOG_PONTE_SEM_BARRA = ("  ponte para o agente que lê {} declarada: as mesmas "
                       "cercas, a abertura e a parada valem lá")
LOG_PONTE_SEM_BARRA_PEDE_CONFIANCA = (
    "  o agente IGNORA em silêncio gancho que o dono ainda não revisou: abra "
    "uma sessão dele nesta pasta, rode `/hooks` e marque os três como "
    "confiáveis, uma vez; gancho que muda pede revisão de novo. Sem isso a "
    "ponte existe e não roda.")
LOG_PONTE_SEM_BARRA_EM_DIA = "  em dia:  {} já declara a ponte"
ENSAIO_DA_PONTE_SEM_BARRA = ("  ensaio: {} receberia a ponte das cercas "
                             "(`{} {}` escreve)")
ENSAIO_DA_PONTE_DO_DEVIN = ("  ensaio: nada foi escrito. {} receberia a ponte das "
                            "cercas, e a camada seria montada nesta pasta, com os "
                            "módulos que vêm ligados (`{} {}` escreve)")
SECAO_DOS_RECURSOS_NO_TOML = "[features]"
LINHA_QUE_LIGA_OS_GANCHOS_NO_TOML = "hooks = true"
CHAVE_DOS_CABECALHOS_DO_MCP = "headers"
CABECALHO_DE_AUTORIZACAO = "Authorization"
PREFIXO_DO_PORTADOR = "Bearer "
CHAVE_DO_PORTADOR_NO_TOML = "bearer_token_env_var"
SECAO_DOS_CABECALHOS_NO_TOML = "[mcp_servers.{}.http_headers]"
SECAO_DOS_CABECALHOS_POR_VARIAVEL_NO_TOML = "[mcp_servers.{}.env_http_headers]"
CHAVE_DAS_VARIAVEIS_LIBERADAS_NO_TOML = "env_vars"
COMANDO_DA_PONTE = (f'{SHELL_DO_LANCADOR} "$DEVIN_PROJECT_DIR/{ARQUIVO_DO_LANCADOR}" '
                    f'{OPCAO_QUE_LIGA_O_MODO_UTF8} '
                    f'"$DEVIN_PROJECT_DIR/{ARQUIVO_DA_PONTE}"')
EVENTO_DA_OUTRA = "PreToolUse"
PREFIXO_DE_BANDEIRA = "--"

PASTA_DO_GIT = ".git"
ARQUIVO_GITIGNORE = ".gitignore"
ARQUIVO_DE_PASTA_VAZIA = ".gitkeep"
ARQUIVO_SETTINGS = ".claude/settings.json"
ARQUIVO_BRANCHES_PROTEGIDAS = ".claude/branches-protegidas.txt"
ARQUIVO_CAMINHOS_DE_AUTOMACAO = ".claude/caminhos-de-automacao.txt"
ARQUIVO_DIRETIVAS_DE_FERRAMENTA = ".claude/diretivas-de-ferramenta.txt"
ARQUIVO_CAMINHOS_DE_POLITICA = ".claude/caminhos-de-politica.txt"
ARQUIVO_CONFIG_DO_DEVIN = ".devin/config.json"
ARQUIVO_CONFIGURACAO = "nucleo/configuracao.json"
ARQUIVO_CONFIGURACAO_ANTES_DA_0_124 = "configuracao-da-casa.md"
ARQUIVO_REGRAS = "nucleo/regras.json"
PAGINA_REGRAS = "conhecimento/regras-da-camada.md"
PAGINA_INSTRUCOES = "AGENTS.md"
PASTA_DO_CONHECIMENTO = "conhecimento"
PASTA_MODULOS = "modulos"
BANCADA_QUE_NAO_VIAJA = "testes.py"
ORIGEM_SKILLS = ".agents/skills"
COPIA_SKILLS = ".claude/skills"
PASTA_DE_REGRAS = ".claude/rules"
ARQUIVO_DA_REGRA_DE_CODIGO = ".claude/rules/padrao-de-codigo.md"
SKILL_DO_PADRAO_DE_CODIGO = ".agents/skills/padrao-de-codigo/SKILL.md"
CAMINHOS_QUE_ACORDAM_A_REGRA_DE_CODIGO = (
    "**/*.py", "**/*.js", "**/*.ts", "**/*.tsx", "**/*.jsx", "**/*.cs",
    "**/*.java", "**/*.go", "**/*.rb", "**/*.php", "**/*.kt", "**/*.rs",
    "**/*.sh", "**/*.sql")
SECAO_DOS_PEDIDOS_DE_EXEMPLO = "\n## Pedidos de exemplo\n"
FECHAMENTO_DO_FRONTMATTER = "\n---\n"
GANCHOS_APOSENTADOS = (".claude/hooks/injetar-padrao-de-codigo.py",)
LOG_REGRA_POR_CAMINHO = "Regra por caminho gerada de {}: {}"
LOG_GANCHO_APOSENTADO_REMOVIDO = ("  removido do settings.json: {} — aposentado, a "
                                  "regra por caminho o substitui")
CARTAO_DO_MODULO = "LEIAME.md"

CHAVE_DOS_GANCHOS = "hooks"
CHAVE_DA_PONTE = "read_config_from"
ARQUIVO_DE_DECLARACAO_DE_MCP = ".mcp.json"
ARQUIVO_SETTINGS_LOCAL = ".claude/settings.local.json"
ARQUIVO_MCP_LOCAL_DO_DEVIN = ".devin/mcp_config.local.json"
CHAVE_DOS_SERVIDORES_MCP = "mcpServers"
CHAVE_DOS_MCP_PERMITIDOS = "allowedMcpServers"
CHAVE_DO_COMANDO_DO_MCP = "command"
CHAVE_DOS_ARGUMENTOS_DO_MCP = "args"
CHAVE_DA_URL_DO_MCP = "url"
CHAVE_DO_COMANDO_PERMITIDO = "serverCommand"
CHAVE_DA_URL_PERMITIDA = "serverUrl"
NOME_DO_MCP_DO_INDICE = "indice"
ARQUIVO_QUE_PROVA_O_MODULO_INDICE = ".agents/indice/indexar.py"
PACOTE_DO_SERVIDOR_DO_INDICE = "@zilliz/claude-context-mcp@0.1.15"
AMBIENTE_DO_SERVIDOR_DO_INDICE = {
    "EMBEDDING_PROVIDER": "Ollama",
    "EMBEDDING_MODEL": "nomic-embed-text",
    "OLLAMA_HOST": "http://127.0.0.1:11434",
    "MILVUS_ADDRESS": "127.0.0.1:19530",
}
ARQUIVO_DOS_ALVOS_DO_INDICE = ".agents/indice/alvos.json"
SERVIDOR_PADRAO_DO_INDICE = ("~/.local/share/atlas-indice/node_modules/"
                             "@zilliz/claude-context-mcp/dist/index.js")
COMANDO_DE_INDEXAR = "{} " + ARQUIVO_QUE_PROVA_O_MODULO_INDICE
ALVOS_CANDIDATOS_DO_INDICE = ("conhecimento", ".agents/skills", ".agents",
                              ".claude/hooks")
PASTA_DOS_VIZINHOS_INDEXAVEIS = "projetos"
COMENTARIO_DOS_ALVOS = ("Arquivo LOCAL: os caminhos e o servidor sao desta "
                        "maquina, e por isso ele fica fora do git. O indice "
                        "nunca viaja — so a receita. Nasce DESLIGADO: quem "
                        "liga e o dono, com --ligar.")
INVOCADOR_DO_NPX_NO_WINDOWS = ("cmd", "/c")
CHAVE_DO_CLAUDE = "claude"
CHAVE_DAS_PERMISSOES = "permissions"
CHAVE_DO_DENY = "deny"
CHAVE_DO_COMANDO = "command"
TIPO_DE_COMANDO = "command"

MARCADOR_DO_INTERPRETADOR = "<interpretador>"
PERGUNTA_DA_VERSAO = "import sys; print(sys.version_info[0])"
VERSAO_QUE_SERVE = "3"
TETO_DO_INTERPRETADOR_S = 10

RAIZ_DO_PROJETO_NO_GANCHO = "${CLAUDE_PROJECT_DIR}"
PROGRAMA_QUE_RODA_O_GANCHO = (
    "import os,sys,runpy;"
    "r=os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd();"
    "a=os.path.join(r,sys.argv[1]);"
    "os.path.isfile(a) or sys.exit(print('gancho ausente: '+a,file=sys.stderr) or 2);"
    "sys.argv=[a];sys.path[0]=os.path.dirname(a);"
    "runpy.run_path(a,run_name='__main__')")


def comando_do_gancho(arquivo: str) -> str:
    return (f'{MARCADOR_DO_INTERPRETADOR} {OPCAO_QUE_LIGA_O_MODO_UTF8} '
            f'-c "{PROGRAMA_QUE_RODA_O_GANCHO}" {arquivo}')


LANCADOR_NO_GANCHO = (
    f'{SHELL_DO_LANCADOR} "{RAIZ_DO_PROJETO_NO_GANCHO}/{ARQUIVO_DO_LANCADOR}"')
LINHA_DOS_CANDIDATOS = re.compile(r'^CANDIDATOS="([^"]*)"', re.M)
LINHA_DOS_CANDIDATOS_NO_WINDOWS = re.compile(
    r'^CANDIDATOS_NO_WINDOWS="([^"]*)"', re.M)
LOG_INTERPRETADOR_MEDIDO = (
    "  ganchos chamam {} direto — medido nesta máquina. Sem bash no "
    "caminho,\n  a chamada de ferramenta economiza a partida dele")
LOG_INTERPRETADOR_SEM_RESPOSTA = (
    "  nenhum Python 3 respondeu aqui (tentei: {}) — os ganchos ficam com o\n"
    "  lançador, que sonda a cada execução. Instale o Python e rode a atualização")
ARQUIVO_GITATTRIBUTES = ".gitattributes"
ATRIBUTOS_DO_LANCADOR = (f"{ARQUIVO_DO_LANCADOR} text eol=lf",)
ROTULO_DOS_ATRIBUTOS = ".gitattributes (quebra de linha do lançador)"
MOTIVO_DOS_ATRIBUTOS = ("# O lançador dos ganchos é lido pelo bash, que não "
                        "aceita quebra de linha CRLF.")

ARQUIVO_DO_GANCHO_DE_BRANCH = ".claude/hooks/vetar-branch-protegida.py"
ARQUIVO_DO_GANCHO_DE_CONHECIMENTO = ".claude/hooks/vetar-conhecimento-em-codigo.py"
ARQUIVO_DO_GANCHO_DE_AUTOMACAO = ".claude/hooks/vetar-automacao.py"
ARQUIVO_DO_GANCHO_DE_SOMENTE_LEITURA = (".claude/hooks/vetar-escrita-em-somente-leitura.py")
ARQUIVO_DO_GANCHO_DE_FORA_DA_EXECUCAO = (".claude/hooks/vetar-escrita-fora-da-execucao.py")
ARQUIVO_DO_GANCHO_DE_PERGUNTA = (".claude/hooks/vetar-pergunta-ja-respondida.py")
ARQUIVO_DO_GANCHO_DE_COMENTARIO = (".claude/hooks/vetar-comentario-explicativo.py")
SUBAGENTE_VARREDOR = ".claude/agents/varredor.md"
ARQUIVO_DO_GANCHO_DE_CREDENCIAL = ".claude/hooks/orientar-credencial.py"
ARQUIVO_DO_GANCHO_DE_MCP = ".claude/hooks/verificar-mcp.py"
ARQUIVO_DO_GANCHO_DE_AMBIENTE = ".claude/hooks/verificar-ambiente.py"
ARQUIVO_DO_GANCHO_DE_ENCERRAMENTO = ".claude/hooks/lembrar-encerramento.py"
ARQUIVO_DO_GANCHO_DE_COPIA_GERADA = ".claude/hooks/vetar-escrita-em-copia-gerada.py"
ARQUIVO_DO_GANCHO_DE_DESTINO = ".claude/hooks/cobrar-destino-da-entrega.py"
ARQUIVO_DO_DESPACHANTE_DE_CERCAS = ".claude/hooks/despachar-cercas.py"
ARQUIVO_DO_COMANDO_DE_ABERTURA = ".claude/commands/bootstart.md"
ARQUIVO_DO_COMANDO_DE_PARTIDA = ".claude/commands/partida.md"
ARQUIVO_DO_GANCHO_DE_DOCUMENTO = ".claude/hooks/vetar-documento-rastreavel.py"
ARQUIVO_DOS_DOCUMENTOS_VERSIONADOS = ".claude/documentos-versionados.txt"
ARQUIVO_DOS_TRECHOS_PERDOADOS = ".claude/trechos-que-a-varredura-perdoa.txt"
ARQUIVO_DO_GANCHO_DE_RELATO = ".claude/hooks/cobrar-relato-da-sessao.py"
ARQUIVO_DO_GANCHO_DE_APRESENTACAO = ".claude/hooks/cobrar-apresentacao-da-entrega.py"
ARQUIVO_DO_GANCHO_DE_PENDENCIA = ".claude/hooks/cobrar-pergunta-em-pendencia.py"
ARQUIVO_DO_GANCHO_DE_POLITICA = (".claude/hooks/vetar-escrita-em-politica.py")
ARQUIVO_DO_GANCHO_DE_ANDAMENTO = (".claude/hooks/vetar-andamento-em-arquivo.py")
ARQUIVO_DO_GANCHO_DE_SESSAO_PARALELA = (
    ".claude/hooks/avisar-sessao-paralela.py")
ARQUIVO_DO_GANCHO_DE_CLONE_ATRASADO = (
    ".claude/hooks/avisar-clone-desatualizado.py")
ARQUIVO_DO_GANCHO_DE_INDICE_FORA = ".claude/hooks/avisar-indice-fora.py"
ARQUIVO_DO_GANCHO_DE_MOTORES = ".claude/hooks/avisar-motores-auxiliares.py"
ARQUIVO_DO_GANCHO_DE_CD = ".claude/hooks/vetar-caminho-relativo-apos-cd.py"
ARQUIVO_DO_GANCHO_DE_PESQUISA = (
    ".claude/hooks/vetar-escrita-em-sessao-de-pesquisa.py")
ARQUIVO_DO_GANCHO_DE_DESPEJO = ".claude/hooks/vetar-despejo-de-ambiente.py"
ARQUIVO_DO_GANCHO_DE_ENXAME = ".claude/hooks/vetar-enxame-de-agentes.py"
ARQUIVO_DO_DESEMBRULHADOR_DE_COMANDO = ".claude/hooks/desembrulhar-comando.py"

COMANDO_DO_VETO_DE_BRANCH = comando_do_gancho(ARQUIVO_DO_GANCHO_DE_BRANCH)
COMANDO_DO_VETO_DE_CONHECIMENTO = comando_do_gancho(ARQUIVO_DO_GANCHO_DE_CONHECIMENTO)
COMANDO_DO_VETO_DE_ANDAMENTO = comando_do_gancho(ARQUIVO_DO_GANCHO_DE_ANDAMENTO)
COMANDO_DO_VETO_DE_AUTOMACAO = comando_do_gancho(ARQUIVO_DO_GANCHO_DE_AUTOMACAO)
COMANDO_DO_VETO_DE_SOMENTE_LEITURA = comando_do_gancho(ARQUIVO_DO_GANCHO_DE_SOMENTE_LEITURA)
COMANDO_DO_VETO_DE_FORA_DA_EXECUCAO = comando_do_gancho(ARQUIVO_DO_GANCHO_DE_FORA_DA_EXECUCAO)
COMANDO_DO_VETO_DE_PERGUNTA = comando_do_gancho(ARQUIVO_DO_GANCHO_DE_PERGUNTA)
COMANDO_DO_VETO_DE_COMENTARIO = comando_do_gancho(ARQUIVO_DO_GANCHO_DE_COMENTARIO)
COMANDO_DA_ORIENTACAO_DE_CREDENCIAL = comando_do_gancho(ARQUIVO_DO_GANCHO_DE_CREDENCIAL)
COMANDO_DA_VERIFICACAO_DE_MCP = comando_do_gancho(ARQUIVO_DO_GANCHO_DE_MCP)
COMANDO_DA_VERIFICACAO_DE_AMBIENTE = comando_do_gancho(ARQUIVO_DO_GANCHO_DE_AMBIENTE)
COMANDO_DO_LEMBRETE_DE_ESFRIAMENTO = comando_do_gancho(ARQUIVO_DO_GANCHO_DE_ENCERRAMENTO)
COMANDO_DO_VETO_DE_COPIA_GERADA = comando_do_gancho(ARQUIVO_DO_GANCHO_DE_COPIA_GERADA)
COMANDO_DA_COBRANCA_DE_DESTINO = comando_do_gancho(ARQUIVO_DO_GANCHO_DE_DESTINO)
COMANDO_DA_COBRANCA_DE_RELATO = comando_do_gancho(ARQUIVO_DO_GANCHO_DE_RELATO)
COMANDO_DA_COBRANCA_DE_APRESENTACAO = comando_do_gancho(ARQUIVO_DO_GANCHO_DE_APRESENTACAO)
COMANDO_DA_COBRANCA_DE_PENDENCIA = comando_do_gancho(ARQUIVO_DO_GANCHO_DE_PENDENCIA)
COMANDO_DO_VETO_DE_POLITICA = comando_do_gancho(ARQUIVO_DO_GANCHO_DE_POLITICA)
COMANDO_DO_AVISO_DE_SESSAO_PARALELA = comando_do_gancho(ARQUIVO_DO_GANCHO_DE_SESSAO_PARALELA)
COMANDO_DO_AVISO_DE_CLONE_ATRASADO = comando_do_gancho(ARQUIVO_DO_GANCHO_DE_CLONE_ATRASADO)
COMANDO_DO_AVISO_DE_INDICE_FORA = comando_do_gancho(ARQUIVO_DO_GANCHO_DE_INDICE_FORA)
COMANDO_DO_AVISO_DE_MOTORES = comando_do_gancho(ARQUIVO_DO_GANCHO_DE_MOTORES)
COMANDO_DO_VETO_DE_PESQUISA = comando_do_gancho(ARQUIVO_DO_GANCHO_DE_PESQUISA)

COMANDO_DO_DESPACHANTE_DE_CERCAS = comando_do_gancho(ARQUIVO_DO_DESPACHANTE_DE_CERCAS)
COMANDO_DO_VETO_DE_DOCUMENTO = comando_do_gancho(ARQUIVO_DO_GANCHO_DE_DOCUMENTO)
COMANDO_DO_VETO_DE_DESPEJO = comando_do_gancho(ARQUIVO_DO_GANCHO_DE_DESPEJO)
COMANDO_DO_VETO_DE_ENXAME = comando_do_gancho(ARQUIVO_DO_GANCHO_DE_ENXAME)

CERCAS_QUE_O_DESPACHANTE_ASSUMIU = (
    ARQUIVO_DO_GANCHO_DE_BRANCH,
    ARQUIVO_DO_GANCHO_DE_CONHECIMENTO,
    ARQUIVO_DO_GANCHO_DE_AUTOMACAO,
    ARQUIVO_DO_GANCHO_DE_ANDAMENTO,
    ARQUIVO_DO_GANCHO_DE_SOMENTE_LEITURA,
    ARQUIVO_DO_GANCHO_DE_FORA_DA_EXECUCAO,
    ARQUIVO_DO_GANCHO_DE_PERGUNTA,
    ARQUIVO_DO_GANCHO_DE_COMENTARIO,
    ARQUIVO_DO_GANCHO_DE_CREDENCIAL,
    ARQUIVO_DO_GANCHO_DE_COPIA_GERADA,
    ARQUIVO_DO_GANCHO_DE_POLITICA,
    ARQUIVO_DO_GANCHO_DE_SESSAO_PARALELA,
    ARQUIVO_DO_GANCHO_DE_CD,
    ARQUIVO_DO_GANCHO_DE_PESQUISA,
)
LOG_CERCA_ASSUMIDA = ("  tirado do settings.json: {} — quem as roda agora é o "
                      "despachante, num processo só; os arquivos seguem "
                      "viajando e rodando sozinhos")

EVENTO_DE_ABERTURA = "SessionStart"
EVENTO_ANTES_DA_FERRAMENTA = "PreToolUse"
EVENTO_DE_FIM_DE_TURNO = "Stop"

MATCHER_DO_SHELL = "Bash|PowerShell"
MATCHER_DA_ESCRITA_E_DO_SHELL = "Write|Edit|NotebookEdit|Bash|PowerShell"
MATCHER_DA_LEITURA_E_DO_SHELL = "Bash|PowerShell|Read"
MATCHER_DA_ESCRITA_EM_ARQUIVO = "Write|Edit|MultiEdit"
MATCHER_DA_PERGUNTA = "AskUserQuestion"
MATCHER_DE_TODAS_AS_CERCAS = ("Write|Edit|NotebookEdit|MultiEdit|Bash|"
                              "PowerShell|Read|AskUserQuestion|Task|Agent|"
                              "Workflow")
MATCHER_DO_ENXAME = ("Task|Agent|Workflow|Write|Edit|NotebookEdit|Bash|"
                     "PowerShell|Read")
MATCHER_DA_ESCRITA = "Write|Edit|NotebookEdit"
MATCHER_DA_LEITURA_DE_VIZINHO = "Read|Bash|PowerShell"
SEM_MATCHER = ""
LIGA_MESMO_SEM_O_GANCHO_NO_DISCO = ""

GanchoDeclarado = namedtuple(
    "GanchoDeclarado", "nome evento matcher comando arquivo_exigido")

GANCHO_DO_VETO_DE_BRANCH = GanchoDeclarado(
    "veto de branch protegida", EVENTO_ANTES_DA_FERRAMENTA, MATCHER_DO_SHELL,
    COMANDO_DO_VETO_DE_BRANCH, ARQUIVO_DO_GANCHO_DE_BRANCH)
GANCHO_DO_VETO_DE_CONHECIMENTO = GanchoDeclarado(
    "veto de conhecimento", EVENTO_ANTES_DA_FERRAMENTA,
    MATCHER_DA_ESCRITA_E_DO_SHELL,
    COMANDO_DO_VETO_DE_CONHECIMENTO, ARQUIVO_DO_GANCHO_DE_CONHECIMENTO)
GANCHO_DO_VETO_DE_AUTOMACAO = GanchoDeclarado(
    "veto de automação", EVENTO_ANTES_DA_FERRAMENTA,
    MATCHER_DA_ESCRITA_E_DO_SHELL,
    COMANDO_DO_VETO_DE_AUTOMACAO, ARQUIVO_DO_GANCHO_DE_AUTOMACAO)
GANCHO_DO_VETO_DE_ANDAMENTO = GanchoDeclarado(
    "veto de andamento em arquivo", EVENTO_ANTES_DA_FERRAMENTA,
    MATCHER_DA_ESCRITA_E_DO_SHELL,
    COMANDO_DO_VETO_DE_ANDAMENTO, ARQUIVO_DO_GANCHO_DE_ANDAMENTO)
GANCHO_DO_VETO_DE_SOMENTE_LEITURA = GanchoDeclarado(
    "veto de escrita em somente leitura", EVENTO_ANTES_DA_FERRAMENTA,
    MATCHER_DA_ESCRITA_E_DO_SHELL,
    COMANDO_DO_VETO_DE_SOMENTE_LEITURA,
    ARQUIVO_DO_GANCHO_DE_SOMENTE_LEITURA)
GANCHO_DO_VETO_DE_FORA_DA_EXECUCAO = GanchoDeclarado(
    "veto de escrita fora da árvore da execução", EVENTO_ANTES_DA_FERRAMENTA,
    MATCHER_DA_ESCRITA_E_DO_SHELL,
    COMANDO_DO_VETO_DE_FORA_DA_EXECUCAO,
    ARQUIVO_DO_GANCHO_DE_FORA_DA_EXECUCAO)
GANCHO_DO_VETO_DE_PERGUNTA = GanchoDeclarado(
    "veto de pergunta já respondida", EVENTO_ANTES_DA_FERRAMENTA,
    MATCHER_DA_PERGUNTA,
    COMANDO_DO_VETO_DE_PERGUNTA, ARQUIVO_DO_GANCHO_DE_PERGUNTA)
GANCHO_DO_VETO_DE_COMENTARIO = GanchoDeclarado(
    "veto de comentário explicativo", EVENTO_ANTES_DA_FERRAMENTA,
    MATCHER_DA_ESCRITA_EM_ARQUIVO,
    COMANDO_DO_VETO_DE_COMENTARIO, ARQUIVO_DO_GANCHO_DE_COMENTARIO)
GANCHO_DA_ORIENTACAO_DE_CREDENCIAL = GanchoDeclarado(
    "orientação de credencial", EVENTO_ANTES_DA_FERRAMENTA,
    MATCHER_DA_LEITURA_E_DO_SHELL,
    COMANDO_DA_ORIENTACAO_DE_CREDENCIAL, ARQUIVO_DO_GANCHO_DE_CREDENCIAL)
GANCHO_DO_LEMBRETE_DE_ESFRIAMENTO = GanchoDeclarado(
    "lembrete de esfriamento", EVENTO_DE_FIM_DE_TURNO, SEM_MATCHER,
    COMANDO_DO_LEMBRETE_DE_ESFRIAMENTO, ARQUIVO_DO_GANCHO_DE_ENCERRAMENTO)
GANCHO_DA_VERIFICACAO_DE_MCP = GanchoDeclarado(
    "verificação de MCP", EVENTO_DE_ABERTURA, SEM_MATCHER,
    COMANDO_DA_VERIFICACAO_DE_MCP, ARQUIVO_DO_GANCHO_DE_MCP)
GANCHO_DA_VERIFICACAO_DE_AMBIENTE = GanchoDeclarado(
    "verificação de ambiente", EVENTO_DE_ABERTURA, SEM_MATCHER,
    COMANDO_DA_VERIFICACAO_DE_AMBIENTE, ARQUIVO_DO_GANCHO_DE_AMBIENTE)
GANCHO_DO_VETO_DE_COPIA_GERADA = GanchoDeclarado(
    "veto de escrita em cópia gerada", EVENTO_ANTES_DA_FERRAMENTA,
    MATCHER_DA_ESCRITA_E_DO_SHELL,
    COMANDO_DO_VETO_DE_COPIA_GERADA, ARQUIVO_DO_GANCHO_DE_COPIA_GERADA)
GANCHO_DA_COBRANCA_DE_DESTINO = GanchoDeclarado(
    "cobrança de destino da entrega", EVENTO_DE_FIM_DE_TURNO, SEM_MATCHER,
    COMANDO_DA_COBRANCA_DE_DESTINO, ARQUIVO_DO_GANCHO_DE_DESTINO)
GANCHO_DA_COBRANCA_DE_RELATO = GanchoDeclarado(
    "cobrança do relato de entrega da sessão", EVENTO_DE_FIM_DE_TURNO,
    SEM_MATCHER,
    COMANDO_DA_COBRANCA_DE_RELATO, ARQUIVO_DO_GANCHO_DE_RELATO)
GANCHO_DA_COBRANCA_DE_APRESENTACAO = GanchoDeclarado(
    "cobrança da apresentação da entrega ao dono", EVENTO_DE_FIM_DE_TURNO,
    SEM_MATCHER,
    COMANDO_DA_COBRANCA_DE_APRESENTACAO, ARQUIVO_DO_GANCHO_DE_APRESENTACAO)
GANCHO_DA_COBRANCA_DE_PENDENCIA = GanchoDeclarado(
    "cobrança da pergunta quando a resposta deixa decisão em prosa",
    EVENTO_DE_FIM_DE_TURNO, SEM_MATCHER, COMANDO_DA_COBRANCA_DE_PENDENCIA,
    ARQUIVO_DO_GANCHO_DE_PENDENCIA)
GANCHO_DO_VETO_DE_POLITICA = GanchoDeclarado(
    "veto de escrita em caminho de política", EVENTO_ANTES_DA_FERRAMENTA,
    MATCHER_DA_ESCRITA_E_DO_SHELL,
    COMANDO_DO_VETO_DE_POLITICA, ARQUIVO_DO_GANCHO_DE_POLITICA)
GANCHO_DO_AVISO_DE_SESSAO_PARALELA = GanchoDeclarado(
    "aviso de sessão paralela", EVENTO_ANTES_DA_FERRAMENTA,
    MATCHER_DA_ESCRITA_E_DO_SHELL,
    COMANDO_DO_AVISO_DE_SESSAO_PARALELA,
    ARQUIVO_DO_GANCHO_DE_SESSAO_PARALELA)
GANCHO_DO_AVISO_DE_CLONE_ATRASADO = GanchoDeclarado(
    "aviso de clone de vizinho atrasado", EVENTO_ANTES_DA_FERRAMENTA,
    MATCHER_DA_LEITURA_DE_VIZINHO, COMANDO_DO_AVISO_DE_CLONE_ATRASADO,
    ARQUIVO_DO_GANCHO_DE_CLONE_ATRASADO)
GANCHO_DA_COBRANCA_DO_CLONE_ATRASADO = GanchoDeclarado(
    "cobrança da data na conclusão tirada de clone atrasado",
    EVENTO_DE_FIM_DE_TURNO, SEM_MATCHER, COMANDO_DO_AVISO_DE_CLONE_ATRASADO,
    ARQUIVO_DO_GANCHO_DE_CLONE_ATRASADO)
GANCHO_DO_AVISO_DE_INDICE_FORA = GanchoDeclarado(
    "aviso de índice fora do ar", EVENTO_DE_ABERTURA, SEM_MATCHER,
    COMANDO_DO_AVISO_DE_INDICE_FORA, ARQUIVO_DO_GANCHO_DE_INDICE_FORA)
GANCHO_DO_AVISO_DE_MOTORES = GanchoDeclarado(
    "aviso dos motores auxiliares desta máquina", EVENTO_DE_ABERTURA,
    SEM_MATCHER, COMANDO_DO_AVISO_DE_MOTORES, ARQUIVO_DO_GANCHO_DE_MOTORES)
GANCHO_DO_VETO_DE_PESQUISA = GanchoDeclarado(
    "veto de escrita na sessão de pesquisa", EVENTO_ANTES_DA_FERRAMENTA,
    MATCHER_DA_ESCRITA_E_DO_SHELL, COMANDO_DO_VETO_DE_PESQUISA,
    ARQUIVO_DO_GANCHO_DE_PESQUISA)
GANCHO_DO_DESPACHANTE_DE_CERCAS = GanchoDeclarado(
    "despachante das cercas", EVENTO_ANTES_DA_FERRAMENTA,
    MATCHER_DE_TODAS_AS_CERCAS, COMANDO_DO_DESPACHANTE_DE_CERCAS,
    ARQUIVO_DO_DESPACHANTE_DE_CERCAS)
GANCHO_DO_VETO_DE_DOCUMENTO = GanchoDeclarado(
    "veto de documento onde o git rastreia", EVENTO_ANTES_DA_FERRAMENTA,
    MATCHER_DA_ESCRITA, COMANDO_DO_VETO_DE_DOCUMENTO,
    ARQUIVO_DO_GANCHO_DE_DOCUMENTO)
GANCHO_DO_VETO_DE_DESPEJO = GanchoDeclarado(
    "veto de despejo de ambiente", EVENTO_ANTES_DA_FERRAMENTA,
    MATCHER_DO_SHELL, COMANDO_DO_VETO_DE_DESPEJO,
    ARQUIVO_DO_GANCHO_DE_DESPEJO)
GANCHO_DO_VETO_DE_ENXAME = GanchoDeclarado(
    "veto de enxame de agentes", EVENTO_ANTES_DA_FERRAMENTA,
    MATCHER_DO_ENXAME, COMANDO_DO_VETO_DE_ENXAME,
    ARQUIVO_DO_GANCHO_DE_ENXAME)

PISO_DE_ATUALIZACAO = "0.88"

PERMISSOES_DO_CLAUDE = (
    '  "permissions": {\n'
    '    "allow": [],\n'
    '    "deny": []\n'
    '  }\n'
)

DENYS_DE_LEITURA_APOSENTADOS = ("Read(.env*)", "Read(**/.env*)",
                                "Read(**/appsettings*)",
                                "Read(.credenciais/**)")

PERMISSOES_DO_DEVIN = (
    '  "permissions": {\n'
    '    "allow": [],\n'
    '    "deny": [\n'
    '      "Read(.env*)",\n'
    '      "Read(**/.env*)",\n'
    '      "Read(**/appsettings*)",\n'
    '      "Read(.credenciais/**)",\n'
    '      "Write(.env*)",\n'
    '      "Write(**/.env*)",\n'
    '      "Write(**/appsettings*)",\n'
    '      "Write(.credenciais/**)"\n'
    '    ]\n'
    '  }\n'
)

LISTA_PROTEGIDA = (
    "# As branches de longa duração deste repositório.\n"
    "#\n"
    "# O gancho .claude/hooks/vetar-branch-protegida.py recusa apagar,\n"
    "# renomear e forçar qualquer nome desta lista. Push normal, commit e\n"
    "# branch nova passam sem saber que ele existe.\n"
    "#\n"
    "# Um nome por linha; linha com # é comentário. Tire o que não existe\n"
    "# aqui e acrescente os nomes do seu repositório — este arquivo é seu, "
    "e a\n"
    "# atualização da camada não o sobrescreve.\n"
    "main\n"
    "master\n"
    "develop\n"
    "homolog\n"
    "staging\n"
    "release\n"
    "production\n"
)

LISTA_DE_DIRETIVAS = (
    "# As diretivas de ferramenta que o veto de comentário deixa "
    "passar.\n"
    "#\n"
    "# O gancho .claude/hooks/vetar-comentario-explicativo.py recusa\n"
    "# toda linha de comentário acrescentada a arquivo de código.\n"
    "# Passam o shebang e a linha que contém um dos trechos desta\n"
    "# lista — a diretiva que uma FERRAMENTA lê e obedece, nunca a\n"
    "# prosa que explica o código para gente.\n"
    "#\n"
    "# A lista é do dono: o próprio gancho recusa Write e Edit sobre\n"
    "# este arquivo, porque cerca que o agente afrouxa não é cerca.\n"
    "# Quem a muda é você, no editor.\n"
    "#\n"
    "# Sem este arquivo o gancho falha fechado — só o shebang passa, e\n"
    "# a recusa nomeia a falta.\n"
    "#\n"
    "# Um trecho por linha, procurado em minúsculas dentro da linha\n"
    "# inteira; linha com # é comentário. Tire o que não existe aqui e\n"
    "# acrescente as diretivas do seu repositório — este arquivo é\n"
    "# seu, e a atualização da camada não o sobrescreve.\n"
    "eslint-\n"
    "@ts-\n"
    "noqa\n"
    "pragma\n"
    "type:\n"
    "shellcheck\n"
    "coding:\n"
)

LISTA_DE_POLITICA = (
    "# Os arquivos que decidem qual cerca existe neste repositório.\n"
    "#\n"
    "# O gancho .claude/hooks/vetar-escrita-em-politica.py recusa "
    "escrever, apagar\n"
    "# ou mover qualquer caminho desta lista DURANTE uma etapa do "
    "executor de\n"
    "# roteiros — pela ferramenta de edição ou por comando de "
    "terminal. Ler passa\n"
    "# calado, e em sessão interativa do dono a cerca não morde: é ela "
    "que muda\n"
    "# esta lista e o código dos ganchos.\n"
    "#\n"
    "# Linha terminada em barra é pasta: pega tudo que estiver dentro "
    "dela, em\n"
    "# qualquer profundidade. Linha sem barra pega o caminho que TERMINA\n"
    "# nela, então\n"
    "# `nucleo/regras.json` pega o arquivo em qualquer repositório e "
    "não pega\n"
    "# `outro-regras.json`.\n"
    "#\n"
    "# A lista está nela mesma, de propósito: cerca que o agente "
    "afrouxa não é\n"
    "# cerca. Os caminhos também vivem embutidos no gancho, e o que "
    "vale é a união\n"
    "# dos dois — apagar este arquivo não derruba a cerca.\n"
    "#\n"
    "# Um caminho por linha; linha com # é comentário. Tire o que não "
    "existe aqui\n"
    "# e acrescente os caminhos do seu repositório — este arquivo é seu, e a\n"
    "# atualização da camada não o sobrescreve.\n"
    ".claude/settings.json\n"
    ".claude/hooks/\n"
    ".claude/branches-protegidas.txt\n"
    ".claude/caminhos-de-automacao.txt\n"
    ".claude/diretivas-de-ferramenta.txt\n"
    ".claude/caminhos-de-politica.txt\n"
    "nucleo/regras.json\n"
    "nucleo/configuracao.json\n"
)

LISTA_DE_AUTOMACAO = (
    "# A configuração da automação deste repositório.\n"
    "#\n"
    "# O gancho .claude/hooks/vetar-automacao.py recusa escrever, apagar ou\n"
    "# mover qualquer caminho desta lista — pela ferramenta de edição ou por\n"
    "# comando de terminal. Ler passa calado.\n"
    "#\n"
    "# Linha terminada em barra é pasta: pega tudo que estiver dentro dela,\n"
    "# em qualquer profundidade. Linha sem barra é arquivo, e vale em\n"
    "# qualquer pasta.\n"
    "#\n"
    "# Um caminho por linha; linha com # é comentário. Tire o que não\n"
    "# existe aqui e acrescente os caminhos do seu repositório — este\n"
    "# arquivo é seu, e a atualização da camada não o sobrescreve.\n"
    ".github/workflows/\n"
    ".gitlab-ci.yml\n"
    ".circleci/\n"
    "Jenkinsfile\n"
    "azure-pipelines.yml\n"
    "bitbucket-pipelines.yml\n"
    ".travis.yml\n"
)

MOLDE_DO_REPOSITORIO_DAS_ISSUES = "${DONO}/${REPOSITORIO}"

MOLDE_DA_CONFIGURACAO = {
    "comentario": (
        "A configuração DESTE repositório: onde a issue nasce, com que nome, "
        "e o que a automação está autorizada a fazer. O arquivo é seu — a "
        "camada o cria uma vez e a atualização nunca o sobrescreve. Troque "
        "os ${...} pelos valores daqui. O que se executa: skill "
        "trabalho-por-issue. `enderecos_do_onde_esta` é a lista das páginas "
        "que situam quem chega: a que existir no cwd entra no bloco "
        "onde-está pelo ENDEREÇO, nunca pelo conteúdo; a que não existir "
        "não aparece, e a lista não é cobrada de novo neste bloco."
    ),
    "repositorio_das_issues": MOLDE_DO_REPOSITORIO_DAS_ISSUES,
    "padrao_de_nome": "${PADRAO_DO_NOME_DA_ISSUE}",
    "enderecos_do_onde_esta": ["conhecimento/mapa-do-repositorio.md",
                               "conhecimento/projetos/indice.json"],
    "autorizacoes": {"commit": False, "push": False, "publicar": False},
    "branches_por_incorporacao": ["main"],
    "teto_da_largada_em_bytes": None,
    "regras": [
        "As três autorizações nascem em false, como manda a regra 9: omissão "
        "não é permissão. Ligue à mão a que este repositório quiser dar à "
        "automação — enquanto estiver em false, o gancho recusa e diz por quê.",
        "`branches_por_incorporacao` são as branches em que NÃO se grava "
        "direto, nem com autorização ligada: a entrada nelas é o pedido de "
        "incorporação. Isto é diferente de `.claude/branches-protegidas.txt`, "
        "que trata de apagar, renomear e forçar. Uma branch de integração em "
        "que o dono commita à mão fica FORA desta lista.",
        "Enquanto houver ${...} sem valor nesta configuração, não se cria "
        "issue — pergunta-se ao dono.",
        "Toda issue deste trabalho nasce no repositório das issues declarado "
        "acima, mesmo quando o código mora em outro. Nunca criar issue em "
        "repositório de código.",
        "O fluxo da fila é DESTE repositório e se escreve aqui: quando uma "
        "issue nova entra, o que acontece com achado no meio do trabalho, e "
        "o que vira pergunta ao dono antes de entrar. A camada não tem "
        "opinião sobre isso — ela só garante que a resposta esteja escrita.",
    ],
}
CONFIGURACAO_POR_PREENCHER = json.dumps(MOLDE_DA_CONFIGURACAO,
                                        ensure_ascii=False, indent=2) + "\n"

ARQUIVOS = {
    "AGENTS.md": (
        "# Instruções para agentes\n"
        "\n"
        "Instruções neutras para qualquer agente de IA neste repositório.\n"
        "Descreva aqui: o que é o projeto, como rodar, regras e estilo.\n"
        "\n"
        "Acabou de instalar a camada? Três passos: leia este arquivo, preencha\n"
        "`nucleo/configuracao.json` — sem autorização escrita ali a camada não\n"
        "commita nem empurra — e prove que ela está de pé com\n"
        "`python .agents/camada/camada.py medir provar`. A documentação da\n"
        "camada fica no repositório de origem dela; aqui viajam as regras, as\n"
        "skills, os instrumentos e os ganchos.\n"
        "\n"
        "Onde as issues nascem está no mesmo `nucleo/configuracao.json`, campo\n"
        "`repositorio_das_issues`. Toda issue nasce lá, mesmo quando o código\n"
        "mora em outro repositório — procurar no repositório de código devolve\n"
        "zero, e zero parece resposta.\n"
        "\n"
        "## Antes de criar algo novo\n"
        "\n"
        "Procure o que já existe e cite o que achou (skill busca-de-codigo-existente).\n"
        "O perfil dos projetos, quando gerado pela skill perfil-de-repositorio, fica em\n"
        "conhecimento/projetos/. Não reimplemente o que o conjunto já oferece.\n"
        "\n"
        "## A memória do workspace\n"
        "\n"
        "As subpastas de conhecimento/ (wiki, notas, decisões) são a memória deste\n"
        "workspace. Consulte antes de redescobrir ou decidir de novo. Aprendizado\n"
        "que vale só para este workspace se escreve lá; lição genérica muda de\n"
        "endereço para a camada.\n"
        "\n"
        "O trabalho EM ANDAMENTO é a exceção: ele mora na issue, não num\n"
        "arquivo. Arquivo de andamento vira uma segunda verdade que ninguém\n"
        "atualiza junto, e é ela que a próxima sessão lê. O .md só entra no\n"
        "encerramento, para extrair o que vale adiante.\n"
        "\n"
        "## Ao dar um trabalho por pronto\n"
        "\n"
        "Faça a análise de promoção (skill analise-de-promocao): o que nasceu\n"
        "genérico é proposto para a camada; o que é do workspace vira nota em\n"
        "conhecimento/; na dúvida, é pessoal e fica.\n"
        "\n"
        "## Onde as coisas ficam\n"
        "\n"
        "- Rascunho e arquivo gerado vão para `tmp/`: descartável, fora do git.\n"
        "  Nada de arquivo de uma vez só na raiz.\n"
        "- Pasta nasce quando o material já cansa a leitura, nunca por\n"
        "  antecipação: pasta com um arquivo só cobra pedágio e não paga nada.\n"
        "- Em conhecimento/, um nível de subpasta. Cada uma nasce com um LEIAME\n"
        "  de uma linha dizendo o que mora ali.\n"
        "- Nome de pasta e de arquivo: minúsculo, sem acento e sem espaço —\n"
        "  acento e maiúscula quebram em outro sistema, e sem aviso.\n"
        "\n"
        "## Regras\n"
        "\n"
        "A lista numerada completa está em `conhecimento/regras-da-camada.md` —\n"
        "leia antes de propor procedimento, de mexer em branch de longa duração\n"
        "e de tocar em configuração de integração contínua. O que segue é o\n"
        "essencial dela.\n"
        "\n"
        "- Abra a sessão na raiz, a pasta com o AGENTS.md: o que decide é onde\n"
        "  você abre, não onde o arquivo mora. Aberta numa subpasta, a sessão\n"
        "  roda sem skill nenhuma — e nada avisa.\n"
        "- Não invente passo onde já existe receita: procedimento que este\n"
        "  repositório já tem (subir, publicar, liberar acesso) se procura na\n"
        "  documentação dele e se cita. Não achou? Peça o endereço —\n"
        "  automação improvisada em cima de automação parece pronta e quebra\n"
        "  longe de onde nasce.\n"
        "- Trabalhe econômico: repositório grande não se varre inteiro — use o\n"
        "  índice, a wiki e a busca dirigida; identifique a linguagem pelo\n"
        "  manifesto e leia primeiro LEIAME e pontos de entrada. Rede e MCP só\n"
        "  quando a tarefa exigir, com pausa entre chamadas.\n"
        "- Ler credencial localmente é livre. Segredo não entra em git nenhum —\n"
        "  público ou privado: em texto rastreado, sempre ${VARIAVEL}, nunca o\n"
        "  valor. Usou credencial para configurar algo? Avise o dono para\n"
        "  tirá-la de vista — o backup é dele.\n"
        "- Branch de longa duração (integração, homologação, produção) e\n"
        "  configuração de integração contínua NÃO se tocam: não apague, não\n"
        "  renomeie, não\n"
        "  force push, não reescreva história, não edite a automação de\n"
        "  passagem. É infraestrutura de outras pessoas e desfazer é público e\n"
        "  caro. Na dúvida se uma branch é dessas, ela é.\n"
        "- Destrutivo é do dono. Commit e push seguem o que ESTE repositório\n"
        "  autorizou por escrito — sem registro, não commite e não empurre; e o\n"
        "  que aciona integração contínua, implantação ou aviso a alguém é\n"
        "  sempre dele.\n"
        "  Sincronizar não é entregar.\n"
        "- Só chame de pronto o que um instrumento provou (build, teste, listagem).\n"
        "- Conteúdo e comunicação em pt-BR.\n"
        "\n"
        "## Como provar que a camada está de pé\n"
        "\n"
        "Um comando, e ele viaja junto com ela:\n"
        "\n"
        "```bash\n"
        "python .agents/camada/camada.py medir provar\n"
        "```\n"
        "\n"
        "`medir` diz quanto esta camada cobra de contexto em toda sessão;\n"
        "`provar` roda o `--testar` de cada gancho e instrumento e acusa o que\n"
        "cair. Rode ao mexer em skill, página ou gancho, e antes de dar\n"
        "trabalho por pronto — regra 2: só é pronto o que um instrumento\n"
        "provou, e a camada traz o instrumento junto com a regra.\n"
    ),
    ARQUIVO_CONFIGURACAO: CONFIGURACAO_POR_PREENCHER,
    "CLAUDE.md": (
        "# CLAUDE.md\n"
        "\n"
        "As instruções deste repositório estão em:\n"
        "\n"
        "@AGENTS.md\n"
    ),
    ".agents/skills/.gitkeep": "",
    ARQUIVO_SETTINGS: "{\n" + PERMISSOES_DO_CLAUDE + "}\n",
    ".claude/.gitignore": "settings.local.json\n",
    ".claude/commands/.gitkeep": "",
    ".claude/skills/.gitkeep": "",
    ".claude/agents/.gitkeep": "",
    ARQUIVO_CONFIG_DO_DEVIN: (
        "{\n"
        '  "comentario": "O deny de leitura fica AQUI de propósito: a camada'
        ' ainda não porta o professor de credencial para os hooks do Devin,'
        ' então este repositório fica só com o muro. Muro só sai de onde'
        ' CHEGOU'
        ' instrumento melhor.",\n'
        '  "read_config_from": {\n'
        '    "claude": false\n'
        "  },\n" + PERMISSOES_DO_DEVIN + "}\n"
    ),
    ".devin/skills/.gitkeep": "",
    ".devin/.gitignore": "mcp_config.local.json\n",
    ARQUIVO_BRANCHES_PROTEGIDAS: LISTA_PROTEGIDA,
    ARQUIVO_CAMINHOS_DE_AUTOMACAO: LISTA_DE_AUTOMACAO,
    ARQUIVO_DIRETIVAS_DE_FERRAMENTA: LISTA_DE_DIRETIVAS,
    ARQUIVO_CAMINHOS_DE_POLITICA: LISTA_DE_POLITICA,
    "tmp/LEIAME.md": (
        "# tmp\n"
        "\n"
        "Rascunho, saída gerada, arquivo de uma vez só. Tudo aqui é\n"
        "descartável e fica fora do git — apagar a pasta inteira não perde\n"
        "nada. O que virar entrega muda de endereço.\n"
    ),
}

ESQUELETO = {
    'projetos/LEIAME.md': '# projetos\n\nOs repositórios de código, um por pasta, cada um com o seu próprio git.\nPor isso esta pasta fica fora do git da raiz.\n',
    '.credenciais/LEIAME.txt': 'Senhas, chaves e tokens.\n\nEsta pasta fica fora de todo git, inclusive de repositorio privado.\nNenhum agente abre arquivo daqui.\n\nTOKENS DE MCP\n\nEscreva NOME=valor no arquivo mcp.env, ao lado deste, e rode:\n\n    python .credenciais/publicar-mcp-env.py\n\nNo .mcp.json fica so ${NOME} - segredo nunca no arquivo. Nenhum valor e\nexibido pelo publicador: so os nomes.\n\nPOR QUE O PUBLICADOR FAZ DUAS COISAS NO LINUX\n\nSao dois canais, e a diferenca foi medida: o aplicativo aberto pelo icone\nnao le o perfil do shell, entao variavel publicada so para o terminal nao\nchega nele - e o servidor MCP morre em silencio, com o mcp.env perfeito.\n\n  - uma linha em ~/.profile e ~/.bashrc carrega o mcp.env na abertura do\n    shell. Terminal novo enxerga na hora, e o valor continua morando aqui.\n  - um arquivo em ~/.config/environment.d/ e o canal que a sessao grafica\n    le. O icone so enxerga depois de deslogar e logar.\n\nO segundo canal e COPIA do valor, e por isso: trocou token, rode o\npublicador de novo. No Windows nao ha essa divisao - cada NOME=valor vira\nvariavel do usuario, e uma sessao ja aberta so enxerga depois de fechar e\nabrir o terminal.\n\nQUANDO FALTA ALGUMA COISA\n\nO que este workspace espera do ambiente se declara pelo NOME em\nnucleo/ambiente.json, e o gancho verificar-ambiente acusa a falta na\nabertura da sessao. Nome de variavel nao e segredo; valor e.\n',
    '.credenciais/publicar-mcp-env.py': 'import os\nimport subprocess\nimport sys\nfrom pathlib import Path\n\nENVFILE = Path(__file__).with_name("mcp.env")\nSEM_COFRE = "mcp.env não existe ao lado deste script."\nFALHA_AO_PUBLICAR = "FALHA ao publicar {}: {}"\nMARCA_QUE_TORNA_A_LINHA_IDEMPOTENTE = (\n    "# carrega os nomes do mcp.env no shell (publicar-mcp-env.py)")\nLINHA_QUE_CALA_SE_O_COFRE_SUMIR = (\n    \'[ -f "%s" ] && { set -a; . "%s"; set +a; }  %s\\n\')\nPERFIS_DO_SHELL = (".profile", ".bashrc")\nPASTA_DO_CANAL_DA_SESSAO_GRAFICA = (".config", "environment.d")\nARQUIVO_DO_CANAL_DA_SESSAO_GRAFICA = "90-mcp.conf"\nSO_O_DONO_LE = 0o600\nAVISO_DE_SESSAO_ABERTA = ("Sessão aberta não enxerga variável nova: feche e "\n                          "abra o terminal ou o VS Code.")\nAVISO_DOS_DOIS_CANAIS = ("Terminal novo já os enxerga; o ícone (sessão "\n                         "gráfica), só depois de deslogar e logar.")\n\nif not ENVFILE.exists():\n    sys.exit(SEM_COFRE)\n\nnomes = []\nfor linha in ENVFILE.read_text(encoding="utf-8").splitlines():\n    if not linha or linha.startswith("#") or "=" not in linha:\n        continue\n    nome, _, valor = linha.partition("=")\n    nomes.append((nome.strip(), valor))\n\nif os.name == "nt":\n    for nome, valor in nomes:\n        publicou = subprocess.run(["setx", nome, valor],\n                                  capture_output=True, text=True, encoding="utf-8", errors="replace")\n        if publicou.returncode != 0:\n            sys.exit(FALHA_AO_PUBLICAR.format(\n                nome, publicou.stderr.strip()[:100]))\n    print("Publicadas:", ", ".join(n for n, _ in nomes))\n    print(AVISO_DE_SESSAO_ABERTA)\nelse:\n    carrega = LINHA_QUE_CALA_SE_O_COFRE_SUMIR % (\n        ENVFILE, ENVFILE, MARCA_QUE_TORNA_A_LINHA_IDEMPOTENTE)\n    for nome_do_perfil in PERFIS_DO_SHELL:\n        perfil = Path.home() / nome_do_perfil\n        texto = perfil.read_text(encoding="utf-8") if perfil.exists() else ""\n        if MARCA_QUE_TORNA_A_LINHA_IDEMPOTENTE in texto:\n            print(f"já instalado: {perfil}")\n            continue\n        with perfil.open("a", encoding="utf-8") as arquivo:\n            if texto and not texto.endswith("\\n"):\n                arquivo.write("\\n")\n            arquivo.write(carrega)\n        print(f"instalado:   {perfil}")\n\n    pasta = Path.home().joinpath(*PASTA_DO_CANAL_DA_SESSAO_GRAFICA)\n    pasta.mkdir(parents=True, exist_ok=True)\n    canal_da_sessao_grafica = pasta / ARQUIVO_DO_CANAL_DA_SESSAO_GRAFICA\n    canal_da_sessao_grafica.write_text(\n        "".join(f"{n}={v}\\n" for n, v in nomes), encoding="utf-8")\n    canal_da_sessao_grafica.chmod(SO_O_DONO_LE)\n    print(f"drop-in:     {canal_da_sessao_grafica}")\n    print("Nomes no mcp.env:", ", ".join(n for n, _ in nomes))\n    print(AVISO_DOS_DOIS_CANAIS)\n',
    'recursos/LEIAME.md': '# recursos\n\nMaterial de terceiro: template comprado, kit de design, manual, base de\nreferência. Não é seu código e não entra no seu git — costuma ser pesado\ne ter licença própria. O agente lê daqui normalmente.\n',
}

IGNORAR = (
    "/projetos/*", "!/projetos/LEIAME.md",
    "/.credenciais/*", "!/.credenciais/LEIAME.txt",
    "!/.credenciais/publicar-mcp-env.py",
    "/recursos/*", "!/recursos/LEIAME.md",
)
MOTIVO_IGNORAR = "# Fora do git de propósito: cada pasta explica o porquê no seu LEIAME."

FONTES = (PAGINA_REGRAS,
          ARQUIVO_REGRAS,
          "nucleo/executor.exemplo.json",
          "nucleo/bancada.exemplo.json",
          ".agents/skills/**/*",
          ".agents/prompts/bootstart.md",
          ".agents/prompts/partida.md",
          "conhecimento/verificacao-pos-atualizacao.md",
          "conhecimento/organizar-conhecimento-e-projetos.md",
          "conhecimento/motores-auxiliares.md",
          "conhecimento/windows-e-git-bash.md",
          ".agents/evidencia/evidencia.py",
          ".agents/evidencia/recibo.schema.json",
          ".agents/verificar/verificar.py",
          ".agents/limpeza/limpeza.py",
          ".agents/camada/camada.py",
          ".agents/gh/gh.py",
          ".agents/caixa/caixa.py",
          ".agents/entrega/entrega.py",
          ".agents/gasto/gasto.py",
          ".agents/gatilho/gatilho.py",
          ".agents/motores/motores.py",
          ".agents/travessia/travessia.py",
          ".agents/travessia/ponte.py",
          ARQUIVO_DO_DESPACHANTE_DE_CERCAS,
          ARQUIVO_DO_GANCHO_DE_DOCUMENTO,
          ARQUIVO_DO_GANCHO_DE_BRANCH,
          ARQUIVO_DO_GANCHO_DE_CONHECIMENTO,
          ARQUIVO_DO_GANCHO_DE_AUTOMACAO,
          ARQUIVO_DO_GANCHO_DE_SOMENTE_LEITURA,
          ARQUIVO_DO_GANCHO_DE_FORA_DA_EXECUCAO,
          ARQUIVO_DO_GANCHO_DE_PERGUNTA,
          ARQUIVO_DO_GANCHO_DE_COMENTARIO,
          SUBAGENTE_VARREDOR,
          ARQUIVO_DO_GANCHO_DE_CREDENCIAL,
          ARQUIVO_DO_GANCHO_DE_MCP,
          ARQUIVO_DO_GANCHO_DE_AMBIENTE,
          ARQUIVO_DO_GANCHO_DE_ENCERRAMENTO,
          ARQUIVO_DO_GANCHO_DE_COPIA_GERADA,
          ARQUIVO_DO_GANCHO_DE_DESTINO,
          ARQUIVO_DO_GANCHO_DE_RELATO,
          ARQUIVO_DO_GANCHO_DE_APRESENTACAO,
          ARQUIVO_DO_GANCHO_DE_PENDENCIA,
          ARQUIVO_DO_GANCHO_DE_POLITICA,
          ARQUIVO_DO_GANCHO_DE_ANDAMENTO,
          ARQUIVO_DO_GANCHO_DE_SESSAO_PARALELA,
          ARQUIVO_DO_GANCHO_DE_CLONE_ATRASADO,
          ARQUIVO_DO_GANCHO_DE_INDICE_FORA,
          ARQUIVO_DO_GANCHO_DE_MOTORES,
          ARQUIVO_DO_GANCHO_DE_PESQUISA,
          ARQUIVO_DO_GANCHO_DE_DESPEJO,
          ARQUIVO_DO_GANCHO_DE_ENXAME,
          ARQUIVO_DO_DESEMBRULHADOR_DE_COMANDO,
          ARQUIVO_DO_LANCADOR,
          ARQUIVO_DO_COMANDO_DE_ABERTURA,
          ARQUIVO_DO_COMANDO_DE_PARTIDA,
          ".markdownlint.jsonc")

IGNORAR_LIXO = ("/tmp/*", "!/tmp/LEIAME.md", "__pycache__/", "*.pyc",
                ".pytest_cache/", ".ruff_cache/", ".mypy_cache/",
                ".playwright-mcp/", "/.tmp.driveupload/")
MOTIVO_LIXO = "# Descartáveis: rascunho e cache de ferramenta. Apagar não perde nada."

ARQUIVO_DO_EXECUTOR_LOCAL = "nucleo/executor.json"
ARQUIVO_DO_EXEMPLO_DO_EXECUTOR = "nucleo/executor.exemplo.json"
MARCA_DO_ENDERECO_NO_EXEMPLO = "${DONO}/${REPOSITORIO_DE_ISSUES}"
LETRAS_QUE_UM_ENDERECO_ACEITA = "._-"
IGNORAR_LOCAL = (ARQUIVO_DO_EXECUTOR_LOCAL, "aprovacoes/")
MOTIVO_LOCAL = ("# Configuração deste repositório e resultado de execução, que "
                "não viajam.\n# O executor.json nomeia repositório, conta e "
                "quadro, e não se apaga — o exemplo\n# dela viaja em "
                "nucleo/executor.exemplo.json. A pasta aprovacoes/ guarda a "
                "decisão\n# do dono numa execução: é evento daquela rodada, "
                "não fato da camada.")

SECAO_DO_ENDERECO_DO_QUADRO = "\nOnde as issues deste workspace nascem"
PERGUNTA_DA_CONFIGURACAO = "  {rotulo}\n  [Enter = {padrao}] > "
SEM_PADRAO = "fica por preencher"
CAMPO_DO_ENDERECO_DAS_ISSUES = "issues.repositorio"
ROTULO_DO_ENDERECO = ("Onde nascem as issues deste workspace? dono/repositório "
                      "— fica só nesta máquina, fora do git.")
ROTULO_DO_MODO = ("Modo do executor de roteiros: completo roda a execução "
                  "inteira; so-issues só abre issue.")
ROTULO_DO_PADRAO_DA_BRANCH = ("Nome da branch de trabalho, com <numero> no "
                              "lugar do número da issue.")
ROTULO_DA_INTEGRACAO = "Branch que recebe o trabalho pronto."
MODOS_DO_EXECUTOR = ("completo", "so-issues")
PADRAO_DO_MODO = "completo"
PADRAO_DA_BRANCH_DE_TRABALHO = "issue/<numero>-<assunto>"
MARCA_DO_NUMERO_NA_BRANCH = "<numero>"
MARCA_LIVRE_NA_BRANCH = re.compile(r"<[^<>]+>")
PADRAO_DA_INTEGRACAO = "main"
MOLDE_DO_ENDERECO_NO_REMOTO = re.compile(r"[:/]([^/:]+)/([^/]+?)(?:\.git)?/?$")
TETO_DO_GIT_DA_PERGUNTA = 10
LOG_EXECUTOR_JA_EXISTE = "  {} já existe — não toquei nele."
LOG_EXECUTOR_NASCEU = "  {} criado com:\n    {}"
LOG_EXECUTOR_POR_PREENCHER = (
    "  Ficou por preencher: {}. A abertura (camada.py --abertura) acusa até "
    "lá.\n  Os outros campos com ${{...}} só pesam quando um roteiro os cita.")
LOG_RESPOSTA_QUE_NAO_SERVE = "  {!r} não serve para {}; fica {!r}."
LOG_EXECUTOR_ENDERECO_TORTO = (
    "  {!r} não tem a forma dono/repositório — {} NÃO foi criado.")
LOG_EXECUTOR_SEM_GITIGNORE = (
    "  {} NÃO foi criado: {} ainda não ignora esse caminho, e o endereço "
    "nomeia\n  repositório e conta — isso não entra no git de ninguém.")
ROTULO_DO_GITIGNORE_DO_LIXO = ".gitignore (descartáveis)"
ROTULO_DO_GITIGNORE_LOCAL = ".gitignore (local)"
ROTULO_DO_GITIGNORE_DO_DEVIN = ".devin/.gitignore (espelho pessoal do MCP)"
MOTIVO_DO_ESPELHO_PESSOAL = ("# Espelho pessoal do .mcp.json para o Devin CLI: "
                             "nasce do --atualizar e não viaja.")

MARCA_GERADA = ("<!-- GERADA de nucleo/regras.json pelo "
                "`montar.py --sincronizar`. Edite lá: o que for escrito "
                "aqui se perde na próxima sincronização. -->")
MARCA_INSTRUCOES = ("<!-- GERADO de nucleo/regras.json pelo "
                    "`montar.py --sincronizar`. Editar aqui se perde. -->")
MARCA_DE_PAGINA_GERADA = "GERADO de nucleo/regras.json"

RECUO_DO_ITEM = "    - "
RECUO_DA_CONTINUACAO = "      "
PREFIXO_DA_PROCEDENCIA = "    - Procedência: "
MARCADOR_DE_ITEM = "- "
RECUO_DO_MARCADOR = "  "

TITULO_DAS_INSTRUCOES = "# Instruções para agentes"
ABERTURA_DAS_INSTRUCOES = "Para qualquer agente de IA neste repositório."
TITULO_DAS_REGRAS = "## As regras da camada"
ABERTURA_DAS_REGRAS = ("Citadas por número; os itens de cada uma: "
                       "`conhecimento/regras-da-camada.md`.")
TITULO_DOS_NOMES = "## Os nomes"
TEXTO_DOS_NOMES = ("O nome de uma peça declara a responsabilidade dela, em "
                   "português comum. Use o nome que este repositório já usa "
                   "para a coisa; não invente jargão nem sinônimo novo para o "
                   "que já tem nome. Quem lê o nome tem de saber o que a peça "
                   "faz sem abrir o arquivo.")

SECOES_INSTRUCOES = [
    ("Antes de qualquer pedido", [
        "O checklist de partida, `.agents/prompts/partida.md`, roda sob "
        "demanda, em qualquer agente: quando o dono pedir, ou quando o "
        "`--abertura` acusar peça em falta. Ele custa minutos e muitos tokens "
        "por sessão, então não é o primeiro ato de toda sessão. No Claude Code "
        "ele é `/partida`.",
        "Leia `.agents/prompts/bootstart.md` INTEIRO antes de escolher skill, "
        "abrir arquivo ou responder: é o briefing da camada para qualquer "
        "agente — o que a sessão vai encontrar, o que os ganchos recusam, e a "
        "tabela que diz o que atende cada tipo de pedido. Pedido que já nomeia "
        "uma skill, um vizinho ou uma issue não dispensa a leitura.",
        "Depois rode `python .agents/camada/camada.py --abertura`, com "
        "`--raiz` e o caminho por extenso, e relate na primeira resposta o que ele acusou em falta "
        "— instrução, servidor de contexto, endereço do quadro ou índice. "
        "Sessão que abre sem eles trabalha com menos do que pensa ter.",
    ]),
    ("O repositório", [
        "Camada genérica de skills e conhecimento para sessões de "
        "IA; `montar.py` a instala em outros repositórios.",
        "Viaja para quem instala: regras (`nucleo/`, "
        "`conhecimento/regras-da-camada.md`), skills, instrumentos, ganchos e "
        "módulos ligados; as outras páginas de `conhecimento/` ficam aqui.",
        "Fonte que instrumento lê: `nucleo/`.",
        "Onde escrever cada coisa: `conhecimento/mapa-do-repositorio.md`. Os "
        "vizinhos clonados moram em `projetos/<nome>` — `ls projetos/` lista "
        "o que existe; a wiki deles, `conhecimento/projetos/`, é perfil, não "
        "prova.",
        "Rode `python montar.py --sincronizar` depois de editar página, "
        "skill, módulo ou `nucleo/`.",
        "Onde as issues nascem: `nucleo/configuracao.json`, campo "
        "`repositorio_das_issues`, que aponta o arquivo local com o endereço. "
        "Toda issue nasce lá, mesmo quando o código mora em outro repositório "
        "— procurar no repositório de código devolve zero, e zero parece "
        "resposta.",
    ]),
    ("Ordens deste repositório", [
        "Publicar é do dono, sempre: publicação não se desfaz, e o teto "
        "da sessão é o ensaio, que mostra o que subiria sem subir. "
        "Commit e push seguem `autorizacoes` em "
        "`nucleo/configuracao.json`, que é a mesma fonte que o gancho "
        "lê — omissão não é permissão, e sem declaração ninguém "
        "commita. Destrutivo é do dono. Este é o único lugar desta "
        "regra: outro arquivo que disser diferente está errado.",
        "Repositório público: nada de nome de pessoa ou empresa, credencial "
        "ou caminho de máquina em arquivo, commit, branch ou issue. Na "
        "dúvida, pergunte.",
        "Não altere o que não foi pedido.",
        "Escreva em pt-BR: conclusão primeiro, frases curtas.",
    ]),
]

PONTEIRO_DAS_REGRAS = (
    "\n"
    "## As regras desta camada\n"
    "\n"
    "A lista numerada está em `conhecimento/regras-da-camada.md`. Leia antes de\n"
    "propor procedimento, de mexer em branch de longa duração e de tocar em\n"
    "configuração de integração contínua.\n"
)
TERMO_DA_LISTA_DE_REGRAS = "regras-da-camada"

CACHE_DE_EXECUCAO = "__pycache__"
SUFIXOS_COMPILADOS = (".pyc", ".pyo")
SEPARADOR_NUL = "\0"
CAMPOS_POR_CAMINHO_IGNORADO = 4
MARCA_DE_NEGACAO = "!"
SAIDAS_ESPERADAS_DO_CHECK_IGNORE = (0, 1)
GIT_NAO_RESPONDEU = None
NENHUM_MODULO = "nenhum"
GLOB_DO_NUCLEO = "nucleo/*"


def pediram(bandeira: str) -> bool:
    return bandeira in sys.argv


def texto_ou_bytes(caminho: Path):
    try:
        return caminho.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return caminho.read_bytes()


def gravar_texto_com_quebras_unix(destino: Path, texto: str) -> None:
    destino.write_text(texto, encoding="utf-8", newline="\n")


def gravar_configuracao_json(destino: Path, configuracao: dict) -> None:
    gravar_texto_com_quebras_unix(
        destino, json.dumps(configuracao, indent=2, ensure_ascii=False) + "\n")


def ler_json_ou_vazio(origem: Path) -> dict:
    if not origem.exists():
        return {}
    return json.loads(origem.read_text(encoding="utf-8"))


def texto_das_linhas(linhas: list) -> str:
    return "\n".join(linhas).rstrip("\n") + "\n"


def paragrafo_na_regua(texto: str) -> list:
    return textwrap.wrap(texto, width=LARGURA_DA_REGUA) + [""]


def quebrar_na_regua_sem_partir_hifen(texto: str, **estilo) -> list:
    return textwrap.wrap(texto, width=LARGURA_DA_REGUA,
                         break_on_hyphens=False, **estilo)


def itens_em_lista(itens: list) -> list:
    linhas = []
    for item in itens:
        linhas += quebrar_na_regua_sem_partir_hifen(
            item, initial_indent=MARCADOR_DE_ITEM,
            subsequent_indent=RECUO_DO_MARCADOR)
    return linhas + [""]


def ganchos_declarados() -> list:
    return [valor for valor in globals().values()
            if isinstance(valor, GanchoDeclarado)]


def comandos_do_bloco(bloco: dict) -> list:
    ganchos = bloco.get(CHAVE_DOS_GANCHOS, []) if isinstance(bloco, dict) else []
    return [gancho.get(CHAVE_DO_COMANDO, "")
            for gancho in ganchos if isinstance(gancho, dict)]


CAMINHO_DO_GANCHO_NO_COMANDO = re.compile(r"\.claude/hooks/[^\"'\s]+\.py")


def arquivo_do_gancho_no_comando(comando: str) -> str:
    achados = CAMINHO_DO_GANCHO_NO_COMANDO.findall(comando or "")
    return achados[-1] if achados else ""


def gancho_declarado_com_a_cauda(blocos: list, comando: str):
    alvo = arquivo_do_gancho_no_comando(comando)
    if not alvo:
        return None
    for bloco in blocos:
        ganchos = bloco.get(CHAVE_DOS_GANCHOS, []) if isinstance(bloco, dict) else []
        for gancho in ganchos:
            if isinstance(gancho, dict) and arquivo_do_gancho_no_comando(
                    gancho.get(CHAVE_DO_COMANDO, "")) == alvo:
                return gancho
    return None


def tem_comando_declarado(blocos: list, comando: str) -> bool:
    return gancho_declarado_com_a_cauda(blocos, comando) is not None


def paginas_no_disco(raiz: Path, rastreados=None) -> dict:
    achados = {}
    em_uso_de_modulo = caminhos_em_uso_dos_modulos(raiz, rastreados=rastreados)
    for padrao in FONTES:
        for caminho in sorted(raiz.glob(padrao)):
            if not caminho.is_file() or caminho.name == ARQUIVO_DE_PASTA_VAZIA:
                continue
            if e_cache_de_execucao(caminho):
                continue
            rotulo = caminho.relative_to(raiz).as_posix()
            if rotulo in em_uso_de_modulo:
                continue
            if rastreados is not None and rotulo not in rastreados:
                continue
            achados[rotulo] = texto_ou_bytes(caminho)
    return achados


def e_cache_de_execucao(caminho: Path) -> bool:
    return (CACHE_DE_EXECUCAO in caminho.parts
            or caminho.suffix in SUFIXOS_COMPILADOS)


def arquivos_de_um_modulo(pasta: Path, rastreados=None) -> dict:
    arquivos = {}
    for caminho in sorted(pasta.rglob("*")):
        if not caminho.is_file() or caminho.name == ARQUIVO_DE_PASTA_VAZIA:
            continue
        if e_cache_de_execucao(caminho):
            continue
        rotulo = caminho.relative_to(pasta).as_posix()
        if rotulo in (CARTAO_DO_MODULO, MARCA_DE_MODULO_PRIVADO):
            continue
        if rastreados is not None and rotulo not in rastreados:
            continue
        arquivos[rotulo] = texto_ou_bytes(caminho)
    return arquivos


MODULOS_QUE_JA_VEM_LIGADOS = ("encadeador", "indice", "auditor")
MODULOS_QUE_NAO_VIAJAM = ()
MARCA_DE_MODULO_PRIVADO = "MODULO_PRIVADO"


def e_modulo_privado(pasta: Path) -> bool:
    return (pasta / MARCA_DE_MODULO_PRIVADO).is_file()


def espelho_da_skill(rotulo: str) -> str:
    prefixo = ORIGEM_SKILLS + "/"
    return COPIA_SKILLS + "/" + rotulo[len(prefixo):] \
        if rotulo.startswith(prefixo) else ""


def qualquer_modulo(pasta: Path) -> bool:
    return True


def caminhos_em_uso_dos_modulos(raiz: Path, escolhe=qualquer_modulo,
                                rastreados=None) -> set:
    caminhos = set()
    origem = raiz / PASTA_MODULOS
    if not origem.is_dir():
        return caminhos
    for pasta in sorted(p for p in origem.iterdir()
                        if p.is_dir() and escolhe(p)):
        for rotulo in arquivos_de_um_modulo(
                pasta, rastreados_dentro_do_modulo(rastreados, pasta.name)):
            caminhos.add(rotulo)
            if espelho_da_skill(rotulo):
                caminhos.add(espelho_da_skill(rotulo))
    return caminhos


def caminhos_de_modulos_privados(raiz: Path) -> set:
    return caminhos_em_uso_dos_modulos(raiz, e_modulo_privado)


def modulos_que_viajam(raiz: Path, rastreados=None) -> dict:
    viajam = {}
    for nome, arquivos in modulos_no_disco(raiz, rastreados).items():
        if nome in MODULOS_QUE_NAO_VIAJAM or \
                e_modulo_privado(raiz / PASTA_MODULOS / nome):
            continue
        sem_bancada = {rotulo: conteudo
                       for rotulo, conteudo in arquivos.items()
                       if Path(rotulo).name != BANCADA_QUE_NAO_VIAJA}
        if sem_bancada:
            viajam[nome] = sem_bancada
    return viajam


def rastreados_dentro_do_modulo(rastreados, nome: str):
    if rastreados is None:
        return None
    prefixo = f"{PASTA_MODULOS}/{nome}/"
    return {caminho[len(prefixo):] for caminho in rastreados
            if caminho.startswith(prefixo)}


def modulos_no_disco(raiz: Path, rastreados=None) -> dict:
    achados = {}
    origem = raiz / PASTA_MODULOS
    if not origem.is_dir():
        return achados
    for pasta in sorted(p for p in origem.iterdir() if p.is_dir()):
        arquivos = arquivos_de_um_modulo(
            pasta, rastreados_dentro_do_modulo(rastreados, pasta.name))
        if arquivos:
            achados[pasta.name] = arquivos
    return achados


def arquivos_rastreados_na_pasta(pasta: Path):
    try:
        topo = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                              cwd=pasta, capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        if topo.returncode != 0 or not os.path.samefile(topo.stdout.strip(),
                                                        pasta):
            return None
        lista = subprocess.run(["git", "ls-files", "-z"], cwd=pasta,
                               capture_output=True)
    except OSError:
        return None
    if lista.returncode != 0:
        return None
    return {caminho for caminho in lista.stdout.decode("utf-8", "replace")
            .split(SEPARADOR_NUL) if caminho}


@functools.lru_cache(maxsize=None)
def camada_da_pasta(casa: Path) -> tuple:
    rastreados = arquivos_rastreados_na_pasta(casa)
    if rastreados is None:
        sys.exit(ERRO_CASA_SEM_GIT.format(casa))
    paginas = paginas_no_disco(casa, rastreados)
    if not paginas:
        sys.exit(ERRO_SEM_PAGINAS)
    return paginas, modulos_que_viajam(casa, rastreados)


def camada_da_casa() -> tuple:
    return camada_da_pasta(casa_do_instalador())


def paginas_da_camada() -> dict:
    return camada_da_casa()[0]


def modulos_da_camada() -> dict:
    return camada_da_casa()[1]


def ficou_com_o_conteudo_da_camada(destino: Path, conteudo) -> bool:
    return difere_da_camada(destino, conteudo) is False


@functools.lru_cache(maxsize=None)
def commit_da_pasta(pasta: Path):
    try:
        ponta = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                               cwd=pasta, capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
    except OSError:
        return None
    return ponta.stdout.strip() if ponta.returncode == 0 else None


def marco_da_camada() -> str:
    return commit_da_pasta(casa_do_instalador()) or MARCO_SEM_COMMIT


def registro_da_instalacao(raiz: Path) -> dict:
    paginas, modulos = camada_da_casa()
    return {
        "comentario": COMENTARIO_DO_REGISTRO,
        "commit_da_camada": commit_da_pasta(casa_do_instalador()),
        "paginas": sorted(
            caminho for caminho, conteudo in paginas.items()
            if ficou_com_o_conteudo_da_camada(raiz / caminho, conteudo)),
        "modulos": {
            nome: sorted(
                caminho for caminho, conteudo in arquivos.items()
                if ficou_com_o_conteudo_da_camada(raiz / caminho, conteudo))
            for nome, arquivos in modulos.items()
            if modulo_instalado(raiz, nome)},
    }


def registrar_a_instalacao(raiz: Path, numero: int) -> None:
    print(SECAO_DO_REGISTRO.format(numero))
    if e_a_casa_do_desenvolvimento(raiz):
        print(LOG_A_CASA_NAO_SE_REGISTRA)
        return
    registro = registro_da_instalacao(raiz)
    quantos = len(registro["paginas"]) + sum(
        len(arquivos) for arquivos in registro["modulos"].values())
    texto = json.dumps(registro, indent=2, ensure_ascii=False) + "\n"
    destino = raiz / ARQUIVO_DO_REGISTRO_DA_INSTALACAO
    if destino.is_file() and destino.read_text(encoding="utf-8") == texto:
        print(LOG_REGISTRO_EM_DIA.format(ARQUIVO_DO_REGISTRO_DA_INSTALACAO,
                                         quantos))
        return
    gravar(destino, texto)
    print(LOG_REGISTRO_GRAVADO.format(ARQUIVO_DO_REGISTRO_DA_INSTALACAO,
                                      quantos))


def sincronizar_copias_de_modulo(raiz: Path, escrevendo: bool) -> list:
    mexidas = []
    for nome, arquivos in modulos_no_disco(raiz).items():
        for rotulo, texto in arquivos.items():
            if e_territorio_do_repositorio(rotulo):
                continue
            em_uso = raiz / rotulo
            if not em_uso.is_file() or texto_ou_bytes(em_uso) == texto:
                continue
            if escrevendo:
                if isinstance(texto, bytes):
                    em_uso.write_bytes(texto)
                else:
                    gravar_texto_com_quebras_unix(em_uso, texto)
            mexidas.append(CAMINHO_DO_MODULO.format(nome, rotulo))
    return mexidas


def copias_de_modulo_que_divergem(raiz: Path) -> list:
    return sincronizar_copias_de_modulo(raiz, escrevendo=False)


def publicar_texto_gerado(destino: Path, novo: str, escrevendo: bool,
                          aviso_em_dia: str, aviso_fora_de_dia: str,
                          aviso_gerado: str) -> bool:
    atual = destino.read_text(encoding="utf-8") if destino.exists() else ""
    if novo == atual:
        print(aviso_em_dia)
        return False
    if not escrevendo:
        print(aviso_fora_de_dia)
        return True
    gravar_texto_com_quebras_unix(destino, novo)
    print(aviso_gerado)
    return True


def dados_das_regras_conferidos(fonte: Path) -> dict:
    try:
        dados = json.loads(fonte.read_text(encoding="utf-8"))
        regras = dados["regras"]
        ids = [regra["id"] for regra in regras]
    except (json.JSONDecodeError, KeyError, TypeError) as erro:
        sys.exit(ERRO_FONTE_DE_REGRAS_INVALIDA.format(ARQUIVO_REGRAS, erro))
    if ids != list(range(1, len(regras) + 1)):
        sys.exit(ERRO_IDS_FORA_DE_ORDEM.format(ARQUIVO_REGRAS, len(regras)))
    return dados


def linhas_da_pagina_de_regras(dados: dict, paginas_que_viajam: set) -> list:
    linhas = [MARCA_GERADA, "", f"# {dados['titulo']}", ""]
    for paragrafo in dados["introducao"]:
        linhas += paragrafo_na_regua(paragrafo)
    for regra in dados["regras"]:
        numero = f"{regra['id']}. "
        linhas += textwrap.wrap(f"**{regra['regra']}**",
                                width=LARGURA_DA_REGUA,
                                initial_indent=numero,
                                subsequent_indent=" " * len(numero))
        for item in regra.get("faca", []):
            linhas += textwrap.wrap(item, width=LARGURA_DA_REGUA,
                                    initial_indent=RECUO_DO_ITEM,
                                    subsequent_indent=RECUO_DA_CONTINUACAO)
        procedencia = regra.get("procedencia")
        if procedencia and endereco_da_pagina_de_conhecimento(
                procedencia["endereco"]) in paginas_que_viajam:
            linhas.append(
                PREFIXO_DA_PROCEDENCIA
                + f"[{procedencia['titulo']}]({procedencia['endereco']}).")
        linhas.append("")
    linhas += [f"## {dados['rodape_titulo']}", ""]
    for paragrafo in dados["rodape"]:
        linhas += paragrafo_na_regua(paragrafo)
    return linhas


def endereco_da_pagina_de_conhecimento(endereco: str) -> str:
    return f"{PASTA_DO_CONHECIMENTO}/{endereco}"


def gerar_pagina_de_regras(raiz: Path, escrevendo: bool = True) -> bool:
    fonte = raiz / ARQUIVO_REGRAS
    if not fonte.exists():
        return False
    dados = dados_das_regras_conferidos(fonte)
    return publicar_texto_gerado(
        raiz / PAGINA_REGRAS,
        texto_das_linhas(linhas_da_pagina_de_regras(
            dados, set(paginas_da_camada()))), escrevendo,
        LOG_REGRAS_EM_DIA.format(PAGINA_REGRAS),
        LOG_REGRAS_FORA_DE_DIA.format(PAGINA_REGRAS, ARQUIVO_REGRAS),
        LOG_REGRAS_GERADAS.format(PAGINA_REGRAS, ARQUIVO_REGRAS,
                                  len(dados["regras"])))


def linhas_das_instrucoes(regras: list) -> list:
    linhas = [MARCA_INSTRUCOES, "", TITULO_DAS_INSTRUCOES, "",
              ABERTURA_DAS_INSTRUCOES, ""]
    for titulo, itens in SECOES_INSTRUCOES:
        linhas += [f"## {titulo}", ""] + itens_em_lista(itens)
    linhas += [TITULO_DAS_REGRAS, ""]
    linhas += quebrar_na_regua_sem_partir_hifen(ABERTURA_DAS_REGRAS) + [""]
    for regra in regras:
        numero = f"{regra['id']}. "
        linhas += quebrar_na_regua_sem_partir_hifen(
            regra["regra"], initial_indent=numero,
            subsequent_indent=" " * len(numero))
    linhas += ["", TITULO_DOS_NOMES, ""]
    linhas += quebrar_na_regua_sem_partir_hifen(TEXTO_DOS_NOMES) + [""]
    return linhas


def candidatos_do_lancador_da_camada() -> tuple:
    texto = paginas_da_camada().get(ARQUIVO_DO_LANCADOR, "")
    no_windows = LINHA_DOS_CANDIDATOS_NO_WINDOWS.search(texto)
    geral = LINHA_DOS_CANDIDATOS.search(texto)
    if os.name == "nt" and no_windows:
        return tuple(no_windows.group(1).split())
    return tuple(geral.group(1).split()) if geral else ()


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
def interpretador_desta_maquina() -> str:
    candidatos = candidatos_do_lancador_da_camada()
    achado = interpretador_que_roda(candidatos)
    print(LOG_INTERPRETADOR_MEDIDO.format(achado) if achado
          else LOG_INTERPRETADOR_SEM_RESPOSTA.format(" ".join(candidatos)))
    return achado or ""


def chamada_do_gancho(interpretador: str) -> str:
    if not interpretador:
        return LANCADOR_NO_GANCHO
    return interpretador if " " not in interpretador else f'"{interpretador}"'


def comando_com_o_interpretador(comando: str, interpretador=None) -> str:
    nome = (interpretador_desta_maquina() if interpretador is None
            else interpretador)
    return comando.replace(MARCADOR_DO_INTERPRETADOR,
                           chamada_do_gancho(nome))


def conselho_da_divergencia(raiz: Path) -> str:
    if e_a_casa_do_desenvolvimento(raiz):
        return LOG_DIVERGENCIA_EM_CASA.format(BANDEIRA_SINCRONIZAR)
    return LOG_DIVERGENCIA_NO_ALVO.format(BANDEIRA_ATUALIZAR,
                                          BANDEIRA_SINCRONIZAR)


def casa_do_instalador() -> Path:
    return Path(__file__).resolve().parent


def e_a_casa_do_desenvolvimento(raiz: Path) -> bool:
    return (raiz.resolve() == casa_do_instalador()
            and (raiz / PASTA_MODULOS).is_dir())


def recusar_sincronizar_fora_de_casa(raiz: Path) -> None:
    if not e_a_casa_do_desenvolvimento(raiz):
        sys.exit(ERRO_SINCRONIZAR_FORA_DE_CASA.format(
            BANDEIRA_SINCRONIZAR, raiz, casa_do_instalador(),
            BANDEIRA_ATUALIZAR))


def e_instrucao_do_dono(pagina: Path) -> bool:
    if not pagina.is_file():
        return False
    texto = pagina.read_text(encoding="utf-8", errors="replace")
    return MARCA_DE_PAGINA_GERADA not in texto


def gerar_instrucoes_de_agente(raiz: Path, escrevendo: bool = True) -> bool:
    fonte_regras = raiz / ARQUIVO_REGRAS
    if not fonte_regras.exists():
        return False
    if e_instrucao_do_dono(raiz / PAGINA_INSTRUCOES):
        print(LOG_INSTRUCOES_DO_DONO.format(PAGINA_INSTRUCOES))
        return False
    try:
        regras = json.loads(fonte_regras.read_text(encoding="utf-8"))["regras"]
    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as erro:
        sys.exit(ERRO_FONTE_DO_NUCLEO_INVALIDA.format(
            ARQUIVO_REGRAS, erro))
    return publicar_texto_gerado(
        raiz / PAGINA_INSTRUCOES,
        texto_das_linhas(linhas_das_instrucoes(regras)),
        escrevendo,
        LOG_INSTRUCOES_EM_DIA.format(PAGINA_INSTRUCOES),
        LOG_INSTRUCOES_FORA_DE_DIA.format(PAGINA_INSTRUCOES),
        LOG_INSTRUCOES_GERADAS.format(PAGINA_INSTRUCOES, ARQUIVO_REGRAS))


def arquivos_de_modulos_instalados(raiz: Path) -> dict:
    esperados = {}
    for nome, arquivos in modulos_da_camada().items():
        if not modulo_instalado(raiz, nome):
            continue
        for caminho, conteudo in arquivos.items():
            if not e_territorio_do_repositorio(caminho):
                esperados[caminho] = conteudo
    return esperados


def paginas_instaladas_fora_de_dia(raiz: Path) -> list:
    esperados = dict(paginas_da_camada())
    esperados.update(arquivos_de_modulos_instalados(raiz))
    return [caminho for caminho, texto in esperados.items()
            if not (raiz / caminho).is_file()
            or (raiz / caminho).read_text(encoding="utf-8",
                                          errors="replace") != texto]


def verificar_a_camada_instalada(raiz: Path) -> int:
    gerar_pagina_de_regras(raiz, escrevendo=False)
    gerar_instrucoes_de_agente(raiz, escrevendo=False)
    atrasadas = paginas_instaladas_fora_de_dia(raiz)
    total = len(paginas_da_camada()) + len(arquivos_de_modulos_instalados(raiz))
    print(LOG_TOTAL_DE_PAGINAS.format(total, ACAO_VERIFICADAS,
                                      marco_da_camada()))
    if not atrasadas:
        print(LOG_INSTALADA_EM_DIA)
        return 0
    print(LOG_INSTALADA_ATRASADA.format(len(atrasadas), BANDEIRA_ATUALIZAR))
    for caminho in atrasadas[:TETO_DE_ATRASADAS_MOSTRADAS]:
        print(LOG_PAGINA_ATRASADA.format(caminho))
    return 1


def sincronizar(raiz: Path, escrevendo: bool = True) -> int:
    regras_fora_de_dia = gerar_pagina_de_regras(raiz, escrevendo)
    instrucoes_fora_de_dia = gerar_instrucoes_de_agente(raiz, escrevendo)
    paginas, _ = camada_da_pasta(raiz)
    print(LOG_TOTAL_DE_PAGINAS.format(len(paginas), ACAO_QUE_VIAJAM,
                                      marco_da_camada()))

    divergentes = sincronizar_copias_de_modulo(raiz, escrevendo)
    if divergentes:
        print((LOG_COPIA_DE_MODULO_REGRAVADA if escrevendo
               else LOG_COPIA_DE_MODULO_DIVERGE).format(
            "\n  ".join(divergentes)))

    espelho = ACAO_ESPELHADAS_PARA if escrevendo else ACAO_VERIFICADAS_CONTRA
    print(LOG_SKILLS_ESPELHADAS.format(ORIGEM_SKILLS, espelho, COPIA_SKILLS))
    mexidos = espelhar_e_relatar(raiz, escrevendo)
    regra = espelhar_regra_de_codigo(raiz, escrevendo)
    for acao, caminho in regra:
        print(LOG_REGRA_POR_CAMINHO.format(SKILL_DO_PADRAO_DE_CODIGO,
                                           f"{acao}: {caminho}"))
    mexidos += regra

    if escrevendo:
        return 0
    fora_de_dia = (regras_fora_de_dia or instrucoes_fora_de_dia
                   or bool(mexidos) or bool(divergentes))
    print(conselho_da_divergencia(raiz) if fora_de_dia else LOG_TUDO_EM_DIA)
    return 1 if fora_de_dia else 0


def copiar_skills_para_o_espelho(origem: Path, destino: Path, raiz: Path,
                                 escrevendo: bool) -> list:
    mexidos = []
    for arquivo in sorted(origem.rglob("*")):
        if arquivo.is_dir() or arquivo.name == ARQUIVO_DE_PASTA_VAZIA:
            continue
        if e_cache_de_execucao(arquivo):
            continue
        alvo = destino / arquivo.relative_to(origem)
        dados = arquivo.read_bytes()
        if alvo.exists() and alvo.read_bytes() == dados:
            continue
        if escrevendo:
            alvo.parent.mkdir(parents=True, exist_ok=True)
            alvo.write_bytes(dados)
        mexidos.append((ACAO_COPIADO if escrevendo else ACAO_FORA_DE_DIA,
                        alvo.relative_to(raiz).as_posix()))
    return mexidos


def remover_do_espelho_o_que_a_fonte_ja_nao_tem(origem: Path, destino: Path,
                                                raiz: Path,
                                                escrevendo: bool) -> list:
    mexidos = []
    if not destino.is_dir():
        return mexidos
    for arquivo in sorted(destino.rglob("*")):
        if arquivo.is_dir() or arquivo.name == ARQUIVO_DE_PASTA_VAZIA:
            continue
        if e_cache_de_execucao(arquivo):
            continue
        relativo = arquivo.relative_to(destino)
        if not (origem / relativo).exists():
            if escrevendo:
                arquivo.unlink()
            mexidos.append((ACAO_REMOVIDO if escrevendo else ACAO_SOBRANDO,
                            (destino / relativo).relative_to(raiz).as_posix()))
    if escrevendo:
        for pasta in sorted(destino.rglob("*"), reverse=True):
            if pasta.is_dir() and not any(pasta.iterdir()):
                pasta.rmdir()
    return mexidos


def espelhar_skills(raiz: Path, escrevendo: bool = True) -> list:
    origem, destino = raiz / ORIGEM_SKILLS, raiz / COPIA_SKILLS
    if not origem.is_dir():
        return []
    return (copiar_skills_para_o_espelho(origem, destino, raiz, escrevendo)
            + remover_do_espelho_o_que_a_fonte_ja_nao_tem(origem, destino,
                                                          raiz, escrevendo))


def casos_do_orfao_no_espelho_de_skills(caso) -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as pasta:
        raiz = Path(pasta)
        fonte = raiz / ORIGEM_SKILLS / "uma"
        fonte.mkdir(parents=True)
        (fonte / "SKILL.md").write_text("corpo", encoding="utf-8")
        copia = raiz / COPIA_SKILLS
        (copia / "uma").mkdir(parents=True)
        (copia / "uma" / "SKILL.md").write_text("corpo", encoding="utf-8")
        (copia / "solto.md").write_text("sem fonte", encoding="utf-8")
        (copia / "uma" / "velho.md").write_text("sem fonte", encoding="utf-8")
        (copia / ARQUIVO_DE_PASTA_VAZIA).write_text("", encoding="utf-8")
        caso("a verificação ACUSA arquivo do espelho de skills que a fonte "
             "não tem, solto na raiz ou dentro de uma skill, em vez de dizer "
             "tudo em dia",
             espelhar_skills(raiz, escrevendo=False) == [
                 (ACAO_SOBRANDO, COPIA_SKILLS + "/solto.md"),
                 (ACAO_SOBRANDO, COPIA_SKILLS + "/uma/velho.md")])
        espelhar_skills(raiz, escrevendo=True)
        caso("e a sincronização tira o órfão, porque a cerca de cópia gerada "
             "não deixa a sessão apagá-lo à mão; o marcador de pasta vazia "
             "fica, de propósito",
             sorted(p.relative_to(copia).as_posix()
                    for p in copia.rglob("*") if p.is_file())
             == [ARQUIVO_DE_PASTA_VAZIA, "uma/SKILL.md"])


def espelhar_e_relatar(raiz: Path, escrevendo: bool = True) -> list:
    mexidos = espelhar_skills(raiz, escrevendo)
    for acao, caminho in mexidos:
        print(LOG_ITEM_DO_ESPELHO.format(acao, caminho))
    if not mexidos:
        print(LOG_NADA_A_ESPELHAR)
    return mexidos


def acrescentar_linhas_que_faltam(destino: Path, linhas_exigidas, rotulo: str,
                                  motivo: str = MOTIVO_IGNORAR) -> None:
    texto = destino.read_text(encoding="utf-8") if destino.exists() else ""
    faltando = [linha for linha in linhas_exigidas
                if linha not in texto.splitlines()]
    if not faltando:
        print(LOG_EM_DIA.format(rotulo))
        return

    novo = texto
    if novo and not novo.endswith("\n"):
        novo += "\n"
    if novo:
        novo += "\n"
    if motivo not in texto:
        novo += motivo + "\n"
    novo += "\n".join(faltando) + "\n"
    gravar_texto_com_quebras_unix(destino, novo)
    print(LOG_AJUSTADO.format(rotulo, ", ".join(faltando)))


def garantir_ponte_do_devin_desligada(raiz: Path) -> None:
    destino = raiz / ARQUIVO_CONFIG_DO_DEVIN
    if not destino.exists():
        return
    configuracao = json.loads(destino.read_text(encoding="utf-8"))
    ponte = configuracao.get(CHAVE_DA_PONTE, {}).get(CHAVE_DO_CLAUDE)
    if ponte is False and CHAVE_DAS_PERMISSOES in configuracao:
        print(LOG_DEVIN_EM_DIA)
        return
    configuracao.setdefault(CHAVE_DA_PONTE, {})[CHAVE_DO_CLAUDE] = False
    configuracao.setdefault(
        CHAVE_DAS_PERMISSOES,
        json.loads("{" + PERMISSOES_DO_DEVIN + "}")[CHAVE_DAS_PERMISSOES])
    gravar_configuracao_json(destino, configuracao)
    print(LOG_DEVIN_AJUSTADO)


def ler_json_ou_avisar(origem: Path):
    try:
        return ler_json_ou_vazio(origem)
    except json.JSONDecodeError as erro:
        print(LOG_CONFIGURACAO_ILEGIVEL.format(origem.name, erro.msg))
        return None


def servidores_mcp_declarados(raiz: Path) -> dict:
    declaracao = ler_json_ou_avisar(raiz / ARQUIVO_DE_DECLARACAO_DE_MCP)
    servidores = (declaracao or {}).get(CHAVE_DOS_SERVIDORES_MCP, {})
    return servidores if isinstance(servidores, dict) else {}


def entrada_de_permissao_do_mcp(servidor: dict):
    if CHAVE_DA_URL_DO_MCP in servidor:
        return {CHAVE_DA_URL_PERMITIDA: servidor[CHAVE_DA_URL_DO_MCP]}
    if CHAVE_DO_COMANDO_DO_MCP in servidor:
        return {CHAVE_DO_COMANDO_PERMITIDO: [
            servidor[CHAVE_DO_COMANDO_DO_MCP],
            *servidor.get(CHAVE_DOS_ARGUMENTOS_DO_MCP, [])]}
    return None


def liberar_servidores_mcp_declarados(raiz: Path) -> None:
    servidores = servidores_mcp_declarados(raiz)
    if not servidores:
        print(LOG_SEM_MCP_DECLARADO)
        return
    entradas = [entrada for entrada in map(entrada_de_permissao_do_mcp,
                                           servidores.values()) if entrada]
    destino = raiz / ARQUIVO_SETTINGS_LOCAL
    configuracao = ler_json_ou_avisar(destino)
    if configuracao is None:
        return
    permitidos = configuracao.setdefault(CHAVE_DOS_MCP_PERMITIDOS, [])
    faltam = [entrada for entrada in entradas if entrada not in permitidos]
    if not faltam:
        print(LOG_MCP_JA_LIBERADO.format(len(entradas)))
        return
    permitidos.extend(faltam)
    destino.parent.mkdir(parents=True, exist_ok=True)
    gravar_configuracao_json(destino, configuracao)
    print(LOG_MCP_LIBERADO.format(len(faltam)))


def espelhar_mcp_para_o_devin(raiz: Path) -> None:
    servidores = servidores_mcp_declarados(raiz)
    if not servidores:
        return
    destino = raiz / ARQUIVO_MCP_LOCAL_DO_DEVIN
    espelho = {CHAVE_DOS_SERVIDORES_MCP: servidores}
    if ler_json_ou_avisar(destino) == espelho:
        print(LOG_MCP_DEVIN_EM_DIA)
        return
    destino.parent.mkdir(parents=True, exist_ok=True)
    gravar_configuracao_json(destino, espelho)
    print(LOG_MCP_ESPELHADO_NO_DEVIN.format(len(servidores)))
    acrescentar_linhas_que_faltam(destino.parent / ARQUIVO_GITIGNORE,
                                  (destino.name,), ROTULO_DO_GITIGNORE_DO_DEVIN,
                                  MOTIVO_DO_ESPELHO_PESSOAL)


def valor_de_toml(valor) -> str:
    if isinstance(valor, bool):
        return "true" if valor else "false"
    if isinstance(valor, int):
        return str(valor)
    if isinstance(valor, (list, tuple)):
        return "[" + ", ".join(valor_de_toml(item) for item in valor) + "]"
    return json.dumps(str(valor), ensure_ascii=False)


def ambiente_sem_o_que_e_segredo(servidor: dict) -> tuple:
    declarado = servidor.get(CHAVE_DO_AMBIENTE_DO_MCP) or {}
    if not isinstance(declarado, dict):
        return {}, [], []
    literais, por_variavel, recusados = {}, set(), []
    for posicao, (nome, valor) in enumerate(declarado.items(), 1):
        e_variavel = (isinstance(valor, str)
                      and MARCA_DE_VARIAVEL_POR_PREENCHER in valor)
        if e_variavel:
            if e_nome_de_variavel(nome):
                por_variavel.add(nome)
            else:
                recusados.append(
                    RECUSA_DE_CHAVE_DO_AMBIENTE.format(posicao))
            citado = MARCADOR_COMPLETO_DE_VARIAVEL.fullmatch(valor.strip())
            if citado:
                por_variavel.add(citado.group(1))
            continue
        literais[nome] = valor
    return literais, sorted(por_variavel), recusados


def e_nome_de_variavel(candidato) -> bool:
    return isinstance(candidato, str) \
        and NOME_DE_VARIAVEL.fullmatch(candidato) is not None


def variaveis_liberadas(servidor: dict) -> tuple:
    _, calculadas, recusados = ambiente_sem_o_que_e_segredo(servidor)
    a_mao = servidor.get(CHAVE_DAS_VARIAVEIS_LIBERADAS_NO_TOML)
    if a_mao is None:
        return calculadas, recusados
    if not isinstance(a_mao, (list, tuple)):
        return calculadas, recusados + [RECUSA_DA_LISTA_QUE_NAO_E_LISTA]
    aceitas = set(calculadas)
    for posicao, item in enumerate(a_mao, 1):
        if e_nome_de_variavel(item):
            aceitas.add(item)
        else:
            recusados.append(RECUSA_DE_ITEM_DA_LISTA.format(posicao))
    return sorted(aceitas), recusados


def linhas_do_servidor_no_toml(nome: str, servidor: dict) -> list:
    linhas = [SECAO_DO_SERVIDOR_NO_TOML.format(nome)]
    for chave, valor in servidor.items():
        if chave in (CHAVE_DO_AMBIENTE_DO_MCP, CHAVE_DA_URL_DO_MCP,
                     CHAVE_DAS_VARIAVEIS_LIBERADAS_NO_TOML):
            continue
        if isinstance(valor, (dict, type(None))):
            continue
        linhas.append(f"{chave} = {valor_de_toml(valor)}")
    literais, _, _ = ambiente_sem_o_que_e_segredo(servidor)
    por_variavel, _ = variaveis_liberadas(servidor)
    if por_variavel:
        linhas.append(f"{CHAVE_DAS_VARIAVEIS_LIBERADAS_NO_TOML} = "
                      f"{valor_de_toml(por_variavel)}")
    if literais:
        linhas.append("")
        linhas.append(SECAO_DO_AMBIENTE_NO_TOML.format(nome))
        for chave, valor in literais.items():
            linhas.append(f"{chave} = {valor_de_toml(valor)}")
    return linhas + [""]


def nome_da_variavel_por_preencher(valor: str) -> str:
    dentro = valor[valor.index(MARCA_DE_VARIAVEL_POR_PREENCHER) + 2:]
    return dentro.split("}", 1)[0].strip()


def cabecalhos_sem_o_que_e_segredo(servidor: dict) -> tuple:
    declarados = servidor.get(CHAVE_DOS_CABECALHOS_DO_MCP) or {}
    if not isinstance(declarados, dict):
        return {}, {}, None
    literais, por_variavel, portador = {}, {}, None
    for nome, valor in declarados.items():
        valor = str(valor)
        if MARCA_DE_VARIAVEL_POR_PREENCHER not in valor:
            literais[nome] = valor
        elif nome == CABECALHO_DE_AUTORIZACAO and \
                valor.startswith(PREFIXO_DO_PORTADOR):
            portador = nome_da_variavel_por_preencher(valor)
        else:
            por_variavel[nome] = nome_da_variavel_por_preencher(valor)
    return literais, por_variavel, portador


def linhas_do_servidor_http_no_toml(nome: str, servidor: dict) -> list:
    linhas = [SECAO_DO_SERVIDOR_NO_TOML.format(nome),
              f"{CHAVE_DA_URL_DO_MCP} = "
              f"{valor_de_toml(servidor[CHAVE_DA_URL_DO_MCP])}"]
    literais, por_variavel, portador = cabecalhos_sem_o_que_e_segredo(servidor)
    if portador:
        linhas.append(f"{CHAVE_DO_PORTADOR_NO_TOML} = {valor_de_toml(portador)}")
    for secao, cabecalhos in ((SECAO_DOS_CABECALHOS_NO_TOML, literais),
                              (SECAO_DOS_CABECALHOS_POR_VARIAVEL_NO_TOML,
                               por_variavel)):
        if cabecalhos:
            linhas.append("")
            linhas.append(secao.format(nome))
            for chave, valor in cabecalhos.items():
                linhas.append(f"{valor_de_toml(chave)} = {valor_de_toml(valor)}")
    return linhas + [""]


def variaveis_que_o_servidor_http_espera(servidor: dict) -> list:
    _, por_variavel, portador = cabecalhos_sem_o_que_e_segredo(servidor)
    return sorted(set(por_variavel.values()) | ({portador} if portador
                                                 else set()))


def espelho_para_o_agente_sem_barra(servidores: dict) -> tuple:
    linhas, recados = [], []
    espelhados = []
    for nome in sorted(servidores):
        servidor = servidores[nome]
        if isinstance(servidor, dict) and servidor.get(CHAVE_DA_URL_DO_MCP) \
                and not servidor.get(CHAVE_DO_COMANDO_DO_MCP):
            linhas += linhas_do_servidor_http_no_toml(nome, servidor)
            espelhados.append(nome)
            esperadas = variaveis_que_o_servidor_http_espera(servidor)
            if esperadas:
                recados.append(ESPELHO_PEDE_VARIAVEL.format(
                    nome, ", ".join(esperadas)))
            continue
        if not isinstance(servidor, dict) or \
                not servidor.get(CHAVE_DO_COMANDO_DO_MCP):
            recados.append(ESPELHO_FORA_POR_FALTA_DE_COMANDO.format(nome))
            continue
        linhas += linhas_do_servidor_no_toml(nome, servidor)
        espelhados.append(nome)
        por_variavel, recusados = variaveis_liberadas(servidor)
        if por_variavel:
            recados.append(ESPELHO_PEDE_VARIAVEL.format(
                nome, ", ".join(por_variavel)))
        if recusados:
            recados.append(ESPELHO_RECUSOU_NOME.format(
                nome, ", ".join(recusados)))
    return espelhados, linhas, recados


def nome_do_servidor_da_secao(enxuta: str) -> str:
    prefixo = SECAO_DO_SERVIDOR_NO_TOML.split("{", 1)[0]
    if not enxuta.startswith(prefixo):
        return ""
    return enxuta[len(prefixo):].split("]", 1)[0].split(".", 1)[0].strip("'\"")


def secoes_de_servidor_fora(texto: str, nomes=None) -> str:
    guardadas, dentro = [], False
    for linha in texto.splitlines():
        enxuta = linha.strip()
        if enxuta.startswith("["):
            nome = nome_do_servidor_da_secao(enxuta)
            dentro = bool(nome) and (nomes is None or nome in nomes)
        if not dentro:
            guardadas.append(linha)
    while guardadas and not guardadas[-1].strip():
        guardadas.pop()
    return "\n".join(guardadas)


def com_os_ganchos_ligados(texto: str) -> str:
    linhas = texto.splitlines()
    dentro, ja_dito, onde = False, False, None
    for indice, linha in enumerate(linhas):
        enxuta = linha.strip()
        if enxuta.startswith("["):
            dentro = enxuta == SECAO_DOS_RECURSOS_NO_TOML
            if dentro:
                onde = indice
            continue
        if dentro and enxuta.split("=", 1)[0].strip() == "hooks":
            ja_dito = True
            if enxuta != LINHA_QUE_LIGA_OS_GANCHOS_NO_TOML:
                linhas[indice] = LINHA_QUE_LIGA_OS_GANCHOS_NO_TOML
    if ja_dito:
        return "\n".join(linhas)
    if onde is None:
        return "\n".join(linhas + ["", SECAO_DOS_RECURSOS_NO_TOML,
                                   LINHA_QUE_LIGA_OS_GANCHOS_NO_TOML])
    linhas.insert(onde + 1, LINHA_QUE_LIGA_OS_GANCHOS_NO_TOML)
    return "\n".join(linhas)


def caminho_da_configuracao_do_agente_sem_barra(lar: Path) -> Path:
    return (lar / PASTA_DO_AGENTE_SEM_BARRA
            / ARQUIVO_DE_CONFIGURACAO_DO_AGENTE_SEM_BARRA)


CASOS_DO_ESPELHO_SEM_BARRA = "espelho para o agente sem comando de barra"


def casos_do_espelho_sem_barra(caso) -> None:
    import contextlib
    import io
    import tempfile
    import tomllib

    servidores = {
        "sem_comando": {"type": "sse"},
        "com_credencial": {"command": "python", "args": ["servidor.py"],
                           "env": {"SENHA": "${SENHA_DO_BANCO}",
                                   "ENDERECO": "127.0.0.1:5432"}},
        "simples": {"command": "npx", "args": ["-y", "pacote@1.2.3"],
                    "startup_timeout_sec": 30},
    }
    os.environ["SENHA_DO_BANCO"] = VALOR_FICTICIO_DA_SENHA_NO_ESPELHO
    espelhados, linhas, recados = espelho_para_o_agente_sem_barra(servidores)
    texto = "\n".join(linhas)
    caso("servidor sem comando fica FORA do espelho, e a razão diz que quem o "
         "serve é o próprio agente",
         "sem_comando" not in espelhados
         and any("sem_comando" in r for r in recados))
    caso("servidor simples entra com comando, argumentos e o tempo de partida, "
         "no formato de seção do arquivo de configuração",
         "[mcp_servers.simples]" in texto
         and 'command = "npx"' in texto
         and 'args = ["-y", "pacote@1.2.3"]' in texto
         and "startup_timeout_sec = 30" in texto)
    caso("valor de ambiente que é VARIÁVEL não vai para o arquivo — o espelho "
         "pede a exportação pelo NOME, e o VALOR não entra em texto nenhum, "
         "nem nos recados",
         VALOR_FICTICIO_DA_SENHA_NO_ESPELHO not in texto
         and not any(VALOR_FICTICIO_DA_SENHA_NO_ESPELHO in r for r in recados)
         and any("SENHA" in r and "com_credencial" in r for r in recados))
    caso("valor de ambiente literal, que não é segredo, entra na seção de "
         "ambiente do servidor",
         "[mcp_servers.com_credencial.env]" in texto
         and 'ENDERECO = "127.0.0.1:5432"' in texto)

    caso("servidor com variável de segredo ganha a lista branca env_vars com "
         "os DOIS nomes: o que o servidor espera e o que o marcador cita, "
         "que é o que a máquina tem — o agente sem barra não expande "
         "marcador, só repassa nome",
         'env_vars = ["SENHA", "SENHA_DO_BANCO"]' in texto)
    caso("quando o marcador cita o mesmo nome que o servidor espera, sobra "
         "uma entrada só",
         ambiente_sem_o_que_e_segredo(
             {"env": {"TOKEN": "${TOKEN}"}})[1] == ["TOKEN"])
    caso("só marcador COMPLETO empresta o nome: marcador com valor padrão "
         "ou pela metade não vira nome de variável na lista branca",
         ambiente_sem_o_que_e_segredo(
             {"env": {"A": "${ORIGEM:-padrao}", "B": "${PELA_METADE",
                      "C": "prefixo-${NO_MEIO}"}})[1] == ["A", "B", "C"])
    com_chave_torta = {"torto": {"command": "x", "env": {
        "NOME=valor colado": "${ALFA}", "COM ESPACO": "${BETA}",
        "": "${GAMA}", "9COMECA_COM_DIGITO": "${DELTA}", "BOA": "${BOA}"}}}
    _, linhas_tortas, recados_tortos = \
        espelho_para_o_agente_sem_barra(com_chave_torta)
    caso("chave que não é nome de variável não entra na lista branca: entra "
         "a chave boa e o nome que cada marcador completo cita",
         'env_vars = ["ALFA", "BETA", "BOA", "DELTA", "GAMA"]'
         in "\n".join(linhas_tortas))
    pede = ESPELHO_PEDE_VARIAVEL.split("{}")[1]
    recusou = ESPELHO_RECUSOU_NOME.split("{}")[1]
    caso("o recado que manda exportar não cita chave torta como se fosse "
         "variável a preencher",
         any(pede in recado for recado in recados_tortos)
         and not any(pede in recado and "COM ESPACO" in recado
                     for recado in recados_tortos))
    caso("e um recado próprio diz ONDE está cada recusado, pela posição, em "
         "vez de calar",
         any(recusou in recado
             and all(RECUSA_DE_CHAVE_DO_AMBIENTE.format(n) in recado
                     for n in (1, 2, 3, 4))
             and RECUSA_DE_CHAVE_DO_AMBIENTE.format(5) not in recado
             for recado in recados_tortos))
    caso("nenhum recado repete o conteúdo recusado: chave com valor colado "
         "pode ser o próprio segredo, e recado vai para o terminal",
         not any("valor colado" in recado or "COM ESPACO" in recado
                 or "9COMECA" in recado for recado in recados_tortos))
    caso("o que o espelho escreve passa pelo parser de TOML, com uma lista "
         "branca só",
         tomllib.loads("\n".join(linhas_tortas))["mcp_servers"]["torto"][
             "env_vars"] == ["ALFA", "BETA", "BOA", "DELTA", "GAMA"])
    a_mao = {"manual": {"command": "x", "env": {"T": "${T}"},
                        "env_vars": ["BOA_A_MAO", 7, {"objeto": 1},
                                     "tem espaco", "T"]}}
    _, linhas_a_mao, recados_a_mao = espelho_para_o_agente_sem_barra(a_mao)
    texto_a_mao = "\n".join(linhas_a_mao)
    caso("lista branca declarada à mão passa pelo mesmo filtro e se junta à "
         "calculada numa linha só: número, objeto e texto com espaço ficam "
         "de fora",
         texto_a_mao.count("env_vars = ") == 1
         and 'env_vars = ["BOA_A_MAO", "T"]' in texto_a_mao)
    caso("e o que saiu da lista declarada à mão é dito pela posição, sem o "
         "conteúdo",
         any(recusou in recado
             and all(RECUSA_DE_ITEM_DA_LISTA.format(n) in recado
                     for n in (2, 3, 4))
             and "tem espaco" not in recado and "objeto" not in recado
             for recado in recados_a_mao))
    caso("e a lista unida passa pelo parser, sem chave repetida",
         tomllib.loads(texto_a_mao)["mcp_servers"]["manual"]["env_vars"]
         == ["BOA_A_MAO", "T"])
    for rotulo_do_torto, torto in (("texto", "PARECE_NOME"),
                                   ("objeto", {"A": 1}), ("número", 7)):
        _, linhas_do_torto, recados_do_torto = \
            espelho_para_o_agente_sem_barra(
                {"s": {"command": "x", "env": {"T": "${T}"},
                       "env_vars": torto}})
        caso(f"`env_vars` que é {rotulo_do_torto} em vez de lista é recusado "
             "inteiro: iterar texto liberaria letra por letra, e objeto, as "
             "chaves",
             tomllib.loads("\n".join(linhas_do_torto))["mcp_servers"]["s"][
                 "env_vars"] == ["T"]
             and any(RECUSA_DA_LISTA_QUE_NAO_E_LISTA in recado
                     for recado in recados_do_torto))
    caso("`env_vars` nulo é o mesmo que ausente: sem recado de recusa",
         not any(recusou in recado
                 for recado in espelho_para_o_agente_sem_barra(
                     {"s": {"command": "x", "env": {"T": "${T}"},
                            "env_vars": None}})[2]))
    caso("`env` que não é objeto devolve os três retornos vazios, sem "
         "estourar quem desempacota",
         ambiente_sem_o_que_e_segredo({"env": ["torto"]}) == ({}, [], []))
    caso("todos recusados: nenhuma linha de lista branca é escrita",
         "env_vars" not in "\n".join(espelho_para_o_agente_sem_barra(
             {"s": {"command": "x", "env": {"A B": "${PELA_METADE"}}})[1]))
    caso("controle: servidor só com nome bom não ganha recado de recusa",
         not any(recusou in recado
                 for recado in espelho_para_o_agente_sem_barra(
                     {"limpo": {"command": "x",
                                "env": {"TOKEN": "${TOKEN}"}}})[2]))
    http = {"github": {"type": "http", "url": "https://x.invalido/mcp/",
                       "headers": {"Authorization": "Bearer ${TOKEN_X}",
                                   "X-Leitura": "true",
                                   "X-Chave": "${OUTRA}"}}}
    espelhados_http, linhas_http, recados_http = \
        espelho_para_o_agente_sem_barra(http)
    texto_http = "\n".join(linhas_http)
    caso("servidor HTTP entra pela url, com o portador pelo NOME da variável "
         "e nunca pelo valor",
         "github" in espelhados_http
         and 'url = "https://x.invalido/mcp/"' in texto_http
         and 'bearer_token_env_var = "TOKEN_X"' in texto_http
         and "${" not in texto_http)
    caso("cabeçalho literal vai em http_headers e cabeçalho por variável em "
         "env_http_headers",
         "[mcp_servers.github.http_headers]" in texto_http
         and '"X-Leitura" = "true"' in texto_http
         and "[mcp_servers.github.env_http_headers]" in texto_http
         and '"X-Chave" = "OUTRA"' in texto_http)
    caso("o recado do servidor HTTP nomeia as variáveis que ele espera",
         any("github" in r and "OUTRA" in r and "TOKEN_X" in r
             for r in recados_http))
    caso("[features] sem hooks ganha a linha que liga os ganchos",
         com_os_ganchos_ligados("a = 1\n\n[features]\nmemories = true")
         == "a = 1\n\n[features]\nhooks = true\nmemories = true")
    caso("sem [features], a seção nasce no fim com os ganchos ligados",
         com_os_ganchos_ligados("a = 1").endswith("[features]\nhooks = true"))
    caso("hooks = false vira true, e hooks = true fica como está",
         com_os_ganchos_ligados("[features]\nhooks = false")
         == "[features]\nhooks = true"
         and com_os_ganchos_ligados("[features]\nhooks = true")
         == "[features]\nhooks = true")

    with tempfile.TemporaryDirectory(prefix="montar-ponte-") as pasta:
        raiz_da_ponte = Path(pasta)
        dito = io.StringIO()
        with contextlib.redirect_stdout(dito):
            garantir_ponte_para_o_agente_sem_barra(raiz_da_ponte, False)
        caso("a ponte dos ganchos em ensaio só anuncia e não escreve",
             not (raiz_da_ponte / ARQUIVO_DOS_GANCHOS_DO_AGENTE_SEM_BARRA
                  ).exists() and "ensaio" in dito.getvalue())
        with contextlib.redirect_stdout(io.StringIO()):
            garantir_ponte_para_o_agente_sem_barra(raiz_da_ponte, True)
        escrito = json.loads((raiz_da_ponte
                              / ARQUIVO_DOS_GANCHOS_DO_AGENTE_SEM_BARRA
                              ).read_text(encoding="utf-8"))
        caso("a ponte escrita cobre cerca, abertura e parada, todas pela "
             "mesma ponte no dialeto do agente",
             set(escrito["hooks"]) == set(EVENTOS_DA_PONTE_SEM_BARRA)
             and all(g["hooks"][0]["command"].endswith("--codex")
                     for grupos in escrito["hooks"].values() for g in grupos))
        dito = io.StringIO()
        with contextlib.redirect_stdout(dito):
            garantir_ponte_para_o_agente_sem_barra(raiz_da_ponte, True)
        caso("ponte já escrita é dada como em dia, sem reescrever",
             "em dia" in dito.getvalue())

    guardado = """model = "o-modelo"

[mcp_servers.velho]
command = "sai"

[projects.'d:\\algum']
trust_level = "trusted"
"""
    caso("só a seção do servidor DECLARADO sai do arquivo de antes; servidor "
         "que é do próprio agente e o resto do arquivo ficam de pé — espelho "
         "não é atropelo",
         "[mcp_servers.velho]" in secoes_de_servidor_fora(guardado, ["simples"])
         and "[mcp_servers.simples]" not in secoes_de_servidor_fora(
             guardado + "\n[mcp_servers.simples]\ncommand = \"x\"\n"
             "[mcp_servers.simples.env]\nA = \"1\"\n", ["simples"])
         and 'model = "o-modelo"' in secoes_de_servidor_fora(guardado, [])
         and "trust_level" in secoes_de_servidor_fora(guardado, []))

    with tempfile.TemporaryDirectory(prefix="montar-espelho-") as pasta:
        lar = Path(pasta)
        raiz = lar / "repositorio"
        raiz.mkdir()
        (raiz / ARQUIVO_DE_DECLARACAO_DE_MCP).write_text(
            json.dumps({CHAVE_DOS_SERVIDORES_MCP: servidores}),
            encoding="utf-8")
        dito = io.StringIO()
        with contextlib.redirect_stdout(dito):
            sem_destino = espelhar_mcp_para_o_agente_sem_barra(
                raiz, escrevendo=True, lar=lar)
        caso("sem o arquivo de configuração do agente na máquina, o espelho "
             "ACUSA e não escreve nada — não inventa instalação de ninguém",
             sem_destino == 1
             and not caminho_da_configuracao_do_agente_sem_barra(
                 lar).exists())

        dito = io.StringIO()
        with contextlib.redirect_stdout(dito):
            ensaio = espelhar_mcp_para_o_agente_sem_barra(
                raiz, escrevendo=False, lar=lar)
        caso("o ensaio imprime o que escreveria e NÃO escreve, que é o padrão "
             "da bandeira",
             ensaio == 0 and "[mcp_servers.simples]" in dito.getvalue()
             and not caminho_da_configuracao_do_agente_sem_barra(
                 lar).exists())
        caso("nem no ensaio o VALOR da variável aparece, e o nome que o "
             "marcador cita aparece",
             VALOR_FICTICIO_DA_SENHA_NO_ESPELHO not in dito.getvalue()
             and "SENHA_DO_BANCO" in dito.getvalue())
        os.environ.pop("SENHA_DO_BANCO", None)

        destino = caminho_da_configuracao_do_agente_sem_barra(lar)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(guardado, encoding="utf-8")
        dito = io.StringIO()
        with contextlib.redirect_stdout(dito):
            escreveu = espelhar_mcp_para_o_agente_sem_barra(
                raiz, escrevendo=True, lar=lar, hoje="2026-09-09")
        agora = destino.read_text(encoding="utf-8")
        caso("com a bandeira de escrever, o espelho entra, o resto do arquivo "
             "sobrevive — inclusive servidor que não é do atlas —, os ganchos "
             "ficam ligados e a cópia de antes fica guardada com a data",
             escreveu == 0
             and "[mcp_servers.simples]" in agora
             and 'model = "o-modelo"' in agora
             and "[mcp_servers.velho]" in agora
             and "hooks = true" in agora
             and (destino.parent / (
                 destino.name + SUFIXO_DA_COPIA_DE_SEGURANCA
                 + "-2026-09-09")).is_file())

        dito = io.StringIO()
        with contextlib.redirect_stdout(dito):
            de_novo = espelhar_mcp_para_o_agente_sem_barra(
                raiz, escrevendo=True, lar=lar, hoje="2026-09-09")
        caso("rodar duas vezes não reescreve nem faz cópia nova: já estava em "
             "dia",
             de_novo == 0 and "em dia" in dito.getvalue())


def espelhar_mcp_para_o_agente_sem_barra(raiz: Path, escrevendo: bool,
                                         lar: Path = None,
                                         hoje: str = None) -> int:
    lar = Path.home() if lar is None else lar
    destino = caminho_da_configuracao_do_agente_sem_barra(lar)
    print(TITULO_DO_ESPELHO_SEM_BARRA.format(
        PASTA_DO_AGENTE_SEM_BARRA,
        ARQUIVO_DE_CONFIGURACAO_DO_AGENTE_SEM_BARRA))
    servidores = servidores_mcp_declarados(raiz)
    if not servidores:
        print(ESPELHO_SEM_DECLARACAO.format(ARQUIVO_DE_DECLARACAO_DE_MCP))
        return 0
    espelhados, linhas, recados = espelho_para_o_agente_sem_barra(servidores)
    for recado in recados:
        print(recado)
    if not escrevendo:
        print(ENSAIO_DO_ESPELHO.format(BANDEIRA_CODEX, BANDEIRA_ESCREVER))
        print("\n".join(linhas))
        return 0
    if not destino.is_file():
        print(ESPELHO_SEM_ARQUIVO_DE_DESTINO.format(destino))
        return 1
    antes = destino.read_text(encoding="utf-8", errors="replace")
    novo = (com_os_ganchos_ligados(secoes_de_servidor_fora(antes, espelhados))
            + "\n\n" + "\n".join(linhas))
    if antes.strip() == novo.strip():
        print(ESPELHO_EM_DIA.format(len(espelhados)))
        return 0
    copia = destino.with_name(
        destino.name + SUFIXO_DA_COPIA_DE_SEGURANCA + "-" + hoje
        if hoje else destino.name + SUFIXO_DA_COPIA_DE_SEGURANCA)
    copia.write_text(antes, encoding="utf-8")
    gravar_texto_com_quebras_unix(destino, novo)
    print(ESPELHO_ESCRITO.format(destino, len(espelhados), copia))
    return 0


def servidor_mcp_do_indice(windows: bool = os.name == "nt") -> dict:
    comando = ["npx", PACOTE_DO_SERVIDOR_DO_INDICE]
    if windows:
        comando = [*INVOCADOR_DO_NPX_NO_WINDOWS, *comando]
    return {CHAVE_DO_COMANDO_DO_MCP: comando[0],
            CHAVE_DOS_ARGUMENTOS_DO_MCP: comando[1:],
            "env": dict(AMBIENTE_DO_SERVIDOR_DO_INDICE)}


def registrar_mcp_do_indice(raiz: Path) -> None:
    if not (raiz / ARQUIVO_QUE_PROVA_O_MODULO_INDICE).exists():
        return
    destino = raiz / ARQUIVO_DE_DECLARACAO_DE_MCP
    declaracao = ler_json_ou_avisar(destino)
    if declaracao is None:
        return
    servidores = declaracao.setdefault(CHAVE_DOS_SERVIDORES_MCP, {})
    if NOME_DO_MCP_DO_INDICE in servidores:
        print(LOG_INDICE_JA_REGISTRADO)
        return
    servidores[NOME_DO_MCP_DO_INDICE] = servidor_mcp_do_indice()
    gravar_configuracao_json(destino, declaracao)
    print(LOG_INDICE_REGISTRADO)


def e_repositorio_vizinho(pasta: Path) -> bool:
    return (pasta.is_dir() and not pasta.name.startswith(".")
            and (pasta / PASTA_DO_GIT).exists())


def pastas_sem_repositorio_proprio(raiz: Path) -> list:
    vizinhos = raiz / PASTA_DOS_VIZINHOS_INDEXAVEIS
    if not vizinhos.is_dir():
        return []
    return sorted(f"{PASTA_DOS_VIZINHOS_INDEXAVEIS}/{pasta.name}"
                  for pasta in vizinhos.iterdir()
                  if pasta.is_dir() and not pasta.name.startswith(".")
                  and not e_repositorio_vizinho(pasta))


def alvos_do_indice_que_existem(raiz: Path) -> list:
    achados = [alvo for alvo in ALVOS_CANDIDATOS_DO_INDICE
               if (raiz / alvo).is_dir()]
    vizinhos = raiz / PASTA_DOS_VIZINHOS_INDEXAVEIS
    if vizinhos.is_dir():
        achados += sorted(
            f"{PASTA_DOS_VIZINHOS_INDEXAVEIS}/{pasta.name}"
            for pasta in vizinhos.iterdir() if e_repositorio_vizinho(pasta))
    return achados


def semear_alvos_do_indice(raiz: Path) -> None:
    if not (raiz / ARQUIVO_QUE_PROVA_O_MODULO_INDICE).exists():
        return
    destino = raiz / ARQUIVO_DOS_ALVOS_DO_INDICE
    if destino.exists():
        print(LOG_ALVOS_JA_EXISTEM)
        return
    alvos = alvos_do_indice_que_existem(raiz)
    for fora in pastas_sem_repositorio_proprio(raiz):
        print(LOG_ALVOS_SEM_GIT_PROPRIO.format(fora))
    if not alvos:
        print(LOG_ALVOS_SEM_NADA_PARA_INDEXAR)
        return
    gravar_configuracao_json(destino, {
        "comentario": COMENTARIO_DOS_ALVOS,
        "servidor": SERVIDOR_PADRAO_DO_INDICE,
        "ambiente": dict(AMBIENTE_DO_SERVIDOR_DO_INDICE),
        "alvos": alvos,
        "ligado": False})
    print(LOG_ALVOS_SEMEADOS.format(
        len(alvos), comando_com_o_interpretador(
            COMANDO_DE_INDEXAR.format(MARCADOR_DO_INTERPRETADOR))))


def garantir_gancho_declarado(raiz: Path, gancho) -> None:
    if gancho.arquivo_exigido and not (raiz / gancho.arquivo_exigido).exists():
        print(LOG_GANCHO_PULADO.format(gancho.nome))
        return

    destino = raiz / ARQUIVO_SETTINGS
    configuracao = ler_json_ou_vazio(destino)
    declarados = configuracao.setdefault(CHAVE_DOS_GANCHOS, {}).setdefault(
        gancho.evento, [])
    comando = comando_com_o_interpretador(gancho.comando)
    declarado = gancho_declarado_com_a_cauda(declarados, gancho.comando)
    if declarado is not None and declarado.get(CHAVE_DO_COMANDO) == comando:
        print(LOG_GANCHO_EM_DIA.format(gancho.nome))
        return

    if declarado is not None:
        declarado[CHAVE_DO_COMANDO] = comando
        print(LOG_GANCHO_REESCRITO.format(gancho.nome))
    else:
        bloco = {CHAVE_DOS_GANCHOS: [{"type": TIPO_DE_COMANDO,
                                      CHAVE_DO_COMANDO: comando}]}
        declarados.append({"matcher": gancho.matcher, **bloco}
                          if gancho.matcher else bloco)
        print(LOG_GANCHO_LIGADO.format(gancho.nome))
    destino.parent.mkdir(parents=True, exist_ok=True)
    gravar_configuracao_json(destino, configuracao)


def garantir_lista_de_branches_protegidas(raiz: Path) -> None:
    destino = raiz / ARQUIVO_BRANCHES_PROTEGIDAS
    if destino.exists():
        print(LOG_LISTA_PROTEGIDA_EM_DIA)
        return
    escrever(destino, LISTA_PROTEGIDA, ARQUIVO_BRANCHES_PROTEGIDAS)


def garantir_lista_de_caminhos_de_automacao(raiz: Path) -> None:
    destino = raiz / ARQUIVO_CAMINHOS_DE_AUTOMACAO
    if destino.exists():
        print(LOG_LISTA_DE_AUTOMACAO_EM_DIA)
        return
    escrever(destino, LISTA_DE_AUTOMACAO, ARQUIVO_CAMINHOS_DE_AUTOMACAO)


def garantir_lista_de_diretivas_de_ferramenta(raiz: Path) -> None:
    destino = raiz / ARQUIVO_DIRETIVAS_DE_FERRAMENTA
    if destino.exists():
        print(LOG_LISTA_DE_DIRETIVAS_EM_DIA)
        return
    escrever(destino, LISTA_DE_DIRETIVAS, ARQUIVO_DIRETIVAS_DE_FERRAMENTA)


LISTA_DE_DOCUMENTOS_VERSIONADOS = """\
# Os documentos que ESTE repositório versiona de propósito.
#
# O gancho .claude/hooks/vetar-documento-rastreavel.py recusa gerar documento
# binário (.pptx, .docx, .xlsx, .pdf e afins) em caminho que o git rastreia:
# binário não se revisa num diff, então ele entraria no commit às cegas. Quem
# responde se o caminho é rastreado é o próprio git, por `check-ignore` — a
# cerca não crava pasta nenhuma.
#
# Repositório que versiona documento de propósito — um manual em PDF, uma
# planilha de fixture — declara o caminho aqui, uma por linha, e a cerca cala.
# Linha terminada em barra é pasta e pega tudo dentro dela. Linha sem barra
# pega o caminho que TERMINA nela.
#
# Nasce vazia: o padrão é documento gerado cair fora do git.
"""
LISTA_DE_TRECHOS_PERDOADOS = (
    "# Os trechos que a varredura da publicação perdoa NESTE repositório.\n"
    "#\n"
    "# O publicar.py recusa subir qualquer texto rastreado que carregue nome de\n"
    "# pessoa, de empresa ou caminho de máquina. A lista de nomes proibidos é\n"
    "# deliberadamente burra: ela normaliza acento antes de comparar, então uma\n"
    "# palavra do português comum que também seja parte de um nome próprio bate no\n"
    "# padrão e reprova a leva. Errar para o lado de acusar é mais barato que\n"
    "# vazar: deixar de publicar algo genérico se resolve amanhã, e o que vazou não\n"
    "# se despublica.\n"
    "#\n"
    "# O que se declara aqui é o TRECHO, nunca a palavra sozinha. Perdoar a palavra\n"
    "# deixaria o nome próprio passar junto — e é justamente o nome próprio que\n"
    "# esta varredura existe para pegar. Perdoando o trecho literal, a frase que\n"
    "# você escreveu passa, e qualquer OUTRA frase com a mesma palavra continua\n"
    "# sendo acusada até alguém a declarar aqui.\n"
    "#\n"
    "# Um trecho por linha, copiado do texto como ele está — com acento, com a\n"
    "# pontuação, do jeito que a página o escreve. Linha com # é comentário, e o\n"
    "# comentário é o lugar de dizer POR QUE aquele trecho é português comum.\n"
    "#\n"
    "# Este arquivo é seu: a atualização da camada não o sobrescreve, e ele não vai\n"
    "# para o espelho público.\n"
    "#\n"
    "# Nasce vazia: o padrão é a varredura acusar, e a decisão de perdoar um trecho\n"
    "# ser explícita.\n"
)
LOG_LISTA_DE_TRECHOS_EM_DIA = ("  em dia:  lista de trechos que a varredura perdoa")
LOG_LISTA_DE_DOCUMENTOS_EM_DIA = "  em dia:  lista de documentos versionados"


def garantir_lista_de_documentos_versionados(raiz: Path) -> None:
    destino = raiz / ARQUIVO_DOS_DOCUMENTOS_VERSIONADOS
    if destino.exists():
        print(LOG_LISTA_DE_DOCUMENTOS_EM_DIA)
        return
    escrever(destino, LISTA_DE_DOCUMENTOS_VERSIONADOS,
             ARQUIVO_DOS_DOCUMENTOS_VERSIONADOS)


def garantir_lista_de_trechos_perdoados(raiz: Path) -> None:
    destino = raiz / ARQUIVO_DOS_TRECHOS_PERDOADOS
    if destino.exists():
        print(LOG_LISTA_DE_TRECHOS_EM_DIA)
        return
    escrever(destino, LISTA_DE_TRECHOS_PERDOADOS,
             ARQUIVO_DOS_TRECHOS_PERDOADOS)


def garantir_lista_de_caminhos_de_politica(raiz: Path) -> None:
    destino = raiz / ARQUIVO_CAMINHOS_DE_POLITICA
    if destino.exists():
        print(LOG_LISTA_DE_POLITICA_EM_DIA)
        return
    escrever(destino, LISTA_DE_POLITICA, ARQUIVO_CAMINHOS_DE_POLITICA)


def garantir_configuracao_do_repositorio(raiz: Path) -> None:
    destino = raiz / ARQUIVO_CONFIGURACAO
    if destino.exists():
        print(LOG_CONFIGURACAO_EM_DIA)
    else:
        escrever(destino, CONFIGURACAO_POR_PREENCHER, ARQUIVO_CONFIGURACAO)

    if (raiz / ARQUIVO_CONFIGURACAO_ANTES_DA_0_124).exists():
        print(LOG_CONFIGURACAO_NO_ENDERECO_VELHO.format(
            ARQUIVO_CONFIGURACAO_ANTES_DA_0_124, ARQUIVO_CONFIGURACAO))


def largada_medida(raiz: Path):
    instrumento = raiz / INSTRUMENTO_DA_CAMADA
    if not instrumento.is_file():
        return None
    try:
        feito = subprocess.run(
            [sys.executable, str(instrumento), BANDEIRA_DA_LARGADA],
            cwd=raiz, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=TEMPO_DA_MEDICAO_DA_LARGADA_S)
    except (OSError, subprocess.SubprocessError):
        return None
    for linha in (feito.stdout or "").splitlines():
        if linha.startswith(MARCA_DA_LARGADA_MEDIDA):
            numero = linha[len(MARCA_DA_LARGADA_MEDIDA):].split()[0]
            return int(numero) if numero.isdigit() else None
    return None


def declarar_teto_da_largada_medido(raiz: Path) -> None:
    destino = raiz / ARQUIVO_CONFIGURACAO
    if not destino.is_file():
        return
    try:
        configuracao = json.loads(destino.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    if not isinstance(configuracao, dict):
        return
    if configuracao.get(CHAVE_DO_TETO_DA_LARGADA) is not None:
        print(LOG_TETO_DA_LARGADA_EM_DIA)
        return
    medida = largada_medida(raiz)
    if medida is None:
        print(LOG_TETO_DA_LARGADA_NAO_MEDIDO)
        return
    configuracao[CHAVE_DO_TETO_DA_LARGADA] = medida
    regras = configuracao.get("regras")
    if isinstance(regras, list):
        regras.append(REGRA_DO_TETO_MEDIDO.format(
            datetime.date.today().isoformat(), medida))
    gravar_configuracao_json(destino, configuracao)
    print(LOG_TETO_DA_LARGADA_MEDIDO.format(medida))


def garantir_ponteiro_das_regras(raiz: Path) -> None:
    destino = raiz / PAGINA_INSTRUCOES
    if not destino.exists():
        print(LOG_SEM_AGENTS_MD)
        return
    texto = destino.read_text(encoding="utf-8")
    if TERMO_DA_LISTA_DE_REGRAS in texto:
        print(LOG_PONTEIRO_EM_DIA)
        return
    if not texto.endswith("\n"):
        texto += "\n"
    gravar_texto_com_quebras_unix(destino, texto + PONTEIRO_DAS_REGRAS)
    print(LOG_PONTEIRO_ACRESCENTADO)


def garantir_leitura_livre(raiz: Path) -> None:
    destino = raiz / ARQUIVO_SETTINGS
    if not destino.exists():
        return
    configuracao = json.loads(destino.read_text(encoding="utf-8"))
    deny = configuracao.get(CHAVE_DAS_PERMISSOES, {}).get(CHAVE_DO_DENY, [])
    tirados = [regra for regra in deny
               if regra in DENYS_DE_LEITURA_APOSENTADOS]
    if not tirados:
        print(LOG_LEITURA_JA_LIVRE)
        return
    deny[:] = [regra for regra in deny
               if regra not in DENYS_DE_LEITURA_APOSENTADOS]
    gravar_configuracao_json(destino, configuracao)
    print(LOG_DENY_APOSENTADO_REMOVIDO.format(", ".join(tirados)))


def caminhos_de_automacao() -> list:
    return [linha.strip() for linha in LISTA_DE_AUTOMACAO.splitlines()
            if linha.strip() and not linha.startswith(MARCA_DE_COMENTARIO)]


def copias_de_modulo_registradas(raiz: Path) -> list:
    try:
        registro = ler_json_ou_vazio(raiz / ARQUIVO_DO_REGISTRO_DA_INSTALACAO)
    except ValueError:
        return []
    modulos = registro.get("modulos") if isinstance(registro, dict) else None
    if not isinstance(modulos, dict):
        return []
    return sorted(caminho for arquivos in modulos.values()
                  if isinstance(arquivos, list) for caminho in arquivos
                  if isinstance(caminho, str)
                  and not e_territorio_do_repositorio(caminho))


def regra_nativa_de_edicao(caminho: str) -> str:
    if caminho.endswith("/"):
        return f"Edit(/{caminho}**)"
    if "/" not in caminho:
        return f"Edit(**/{caminho})"
    return f"Edit(/{caminho})"


def regras_nativas_de_edicao(raiz: Path) -> list:
    caminhos = ([f"{COPIA_SKILLS}/", ARQUIVO_DA_REGRA_DE_CODIGO, PAGINA_REGRAS]
                + caminhos_de_automacao() + copias_de_modulo_registradas(raiz))
    return [regra_nativa_de_edicao(caminho) for caminho in caminhos]


def garantir_regras_nativas_de_edicao(raiz: Path) -> None:
    destino = raiz / ARQUIVO_SETTINGS
    if not destino.exists():
        return
    configuracao = json.loads(destino.read_text(encoding="utf-8"))
    negadas = configuracao.setdefault(CHAVE_DAS_PERMISSOES, {}).setdefault(
        CHAVE_DO_DENY, [])
    faltam = [regra for regra in regras_nativas_de_edicao(raiz)
              if regra not in negadas]
    if not faltam:
        print(LOG_REGRAS_NATIVAS_EM_DIA)
        return
    negadas.extend(faltam)
    gravar_configuracao_json(destino, configuracao)
    print(LOG_REGRAS_NATIVAS_ACRESCENTADAS.format(len(faltam)))


def montar_esqueleto(raiz: Path) -> None:
    if not pediram(BANDEIRA_ESQUELETO):
        print(LOG_ESQUELETO_DE_FORA)
        return
    for caminho, conteudo in ESQUELETO.items():
        escrever(raiz / caminho, conteudo, caminho)
    acrescentar_linhas_que_faltam(raiz / ARQUIVO_GITIGNORE, IGNORAR,
                                  ARQUIVO_GITIGNORE)


def modulos_pedidos() -> list:
    pedidos = []
    for posicao, argumento in enumerate(sys.argv):
        if argumento == BANDEIRA_MODULO and posicao + 1 < len(sys.argv):
            pedidos.append(sys.argv[posicao + 1])
        elif argumento.startswith(BANDEIRA_MODULO_COM_IGUAL):
            pedidos.append(argumento.split("=", 1)[1])
    return pedidos


def modulo_instalado(raiz: Path, nome: str) -> bool:
    return any((raiz / caminho).exists()
               for caminho in modulos_da_camada().get(nome, {}))


def e_territorio_do_repositorio(caminho: str) -> bool:
    partes = caminho.split("/")
    return len(partes) > 2 and partes[0] == PASTA_DO_CONHECIMENTO


def difere_da_camada_em_memoria(no_disco: bytes, conteudo) -> bool:
    if isinstance(conteudo, bytes):
        return no_disco != conteudo
    return (no_disco.replace(b"\r\n", b"\n")
            != conteudo.encode("utf-8").replace(b"\r\n", b"\n"))


def difere_da_camada(destino: Path, conteudo):
    try:
        no_disco = destino.read_bytes()
    except OSError:
        return None
    return difere_da_camada_em_memoria(no_disco, conteudo)


def manter_a_copia_do_modulo(raiz: Path, caminho: str, conteudo) -> bool:
    destino = raiz / caminho
    if not destino.exists() or e_territorio_do_repositorio(caminho):
        escrever(destino, conteudo, caminho)
        return False
    difere = difere_da_camada(destino, conteudo)
    if difere is None:
        print(LOG_MANTIDO_SEM_LER.format(caminho))
        return True
    if not difere:
        escrever(destino, conteudo, caminho)
        return False
    print(LOG_MANTIDO_E_DIVERGENTE.format(caminho))
    return True


def instalar_modulo(raiz: Path, nome: str, sobrescrever: bool) -> None:
    divergentes = 0
    for caminho, conteudo in modulos_da_camada()[nome].items():
        if sobrescrever and not e_territorio_do_repositorio(caminho):
            atualizar_arquivo(raiz, caminho, conteudo)
        else:
            divergentes += manter_a_copia_do_modulo(raiz, caminho, conteudo)
    if divergentes:
        print(conselho_da_divergencia(raiz))


def argumentos_desconhecidos() -> list:
    sobrando, resta = [], list(sys.argv[1:])
    while resta:
        argumento = resta.pop(0)
        if argumento == BANDEIRA_MODULO:
            if not resta or resta[0].startswith(PREFIXO_DE_BANDEIRA):
                sys.exit(ERRO_MODULO_SEM_NOME.format(BANDEIRA_MODULO))
            resta.pop(0)
        elif argumento.startswith(BANDEIRA_MODULO_COM_IGUAL):
            if argumento == BANDEIRA_MODULO_COM_IGUAL:
                sys.exit(ERRO_MODULO_SEM_NOME.format(BANDEIRA_MODULO))
        elif argumento == BANDEIRA_DO_QUADRO:
            if resta and not resta[0].startswith(PREFIXO_DE_BANDEIRA):
                resta.pop(0)
        elif argumento.startswith(BANDEIRA_DO_QUADRO_COM_IGUAL):
            continue
        elif argumento not in BANDEIRAS_CONHECIDAS:
            sobrando.append(argumento)
    return sobrando


def recusar_argumento_desconhecido() -> None:
    if desconhecidos := argumentos_desconhecidos():
        sys.exit(ERRO_ARGUMENTO_DESCONHECIDO.format(
            ", ".join(desconhecidos), " ".join(BANDEIRAS_CONHECIDAS)))


def recusar_modulo_desconhecido() -> None:
    if desconhecidos := [nome for nome in modulos_pedidos()
                         if nome not in modulos_da_camada()]:
        sys.exit(ERRO_MODULO_DESCONHECIDO.format(
            ", ".join(desconhecidos),
            ", ".join(sorted(modulos_da_camada())) or NENHUM_MODULO))


def modulos_a_montar(raiz: Path, sobrescrever: bool) -> list:
    modulos = modulos_da_camada()
    ja_aqui = ([nome for nome in modulos if modulo_instalado(raiz, nome)]
               if sobrescrever else [])
    ligados = [] if sobrescrever else [
        nome for nome in MODULOS_QUE_JA_VEM_LIGADOS if nome in modulos]
    return list(dict.fromkeys(ligados + modulos_pedidos() + ja_aqui))


def montar_modulos(raiz: Path, sobrescrever: bool) -> None:
    alvos = modulos_a_montar(raiz, sobrescrever)
    if not alvos:
        print(LOG_SEM_MODULOS)
        return
    for nome in alvos:
        print(LOG_MODULO_INSTALADO_AGORA.format(nome))
        instalar_modulo(raiz, nome, sobrescrever)


def estado_do_modulo(raiz: Path, arquivos: dict) -> str:
    presentes = sum(1 for caminho in arquivos if (raiz / caminho).exists())
    if presentes == 0:
        return ESTADO_NAO_INSTALADO
    if presentes == len(arquivos):
        return ESTADO_INSTALADO.format(presentes)
    return ESTADO_INSTALADO_PELA_METADE.format(presentes, len(arquivos))


def listar_modulos(raiz: Path) -> int:
    modulos = modulos_da_camada()
    if not modulos:
        print(LOG_CAMADA_SEM_MODULOS.format(marco_da_camada()))
        return 0
    print(LOG_CABECALHO_DOS_MODULOS.format(marco_da_camada(), raiz))
    for nome, arquivos in sorted(modulos.items()):
        print(LOG_LINHA_DE_MODULO.format(nome, estado_do_modulo(raiz,
                                                                arquivos)))
    print(USO_INSTALAR_MODULO)
    print(USO_ATUALIZAR_MODULOS)
    return 0


def atualizar(raiz: Path) -> int:
    paginas = paginas_da_camada()
    print(LOG_CABECALHO_DA_ATUALIZACAO.format(raiz, marco_da_camada(),
                                              PISO_DE_ATUALIZACAO))
    print(AJUDA_ABAIXO_DO_PISO)

    print(SECAO_DA_ATUALIZACAO_PAGINAS)
    for caminho, conteudo in paginas.items():
        atualizar_arquivo(raiz, caminho, conteudo)

    print(SECAO_DA_ATUALIZACAO_MODULOS)
    montar_modulos(raiz, sobrescrever=True)

    print(SECAO_DA_ATUALIZACAO_ESQUELETO)
    montar_esqueleto(raiz)

    print(SECAO_DA_ATUALIZACAO_SKILLS.format(ORIGEM_SKILLS, COPIA_SKILLS))
    espelhar_e_relatar(raiz)
    espelhar_regra_de_codigo(raiz)

    registrar_a_instalacao(raiz, NUMERO_DOS_AJUSTES_NA_ATUALIZACAO - 1)
    garantir_ajustes(raiz, NUMERO_DOS_AJUSTES_NA_ATUALIZACAO)

    print(AJUDA_DO_FIM_DA_ATUALIZACAO)
    avisar_do_instalador_antigo_na_raiz(raiz)
    return 0


def avisar_do_instalador_antigo_na_raiz(raiz: Path) -> None:
    antigo = raiz / Path(__file__).name
    if antigo.is_file() and not e_a_casa_do_desenvolvimento(raiz):
        print(AVISO_DO_INSTALADOR_ANTIGO_NA_RAIZ.format(antigo.name))


def garantir_ajustes(raiz: Path, numero: int) -> None:
    print(SECAO_DOS_AJUSTES.format(numero))
    remover_ganchos_aposentados(raiz)
    garantir_ponteiro_das_regras(raiz)
    garantir_lista_de_branches_protegidas(raiz)
    garantir_lista_de_caminhos_de_automacao(raiz)
    garantir_lista_de_diretivas_de_ferramenta(raiz)
    garantir_lista_de_caminhos_de_politica(raiz)
    garantir_lista_de_documentos_versionados(raiz)
    garantir_lista_de_trechos_perdoados(raiz)
    garantir_configuracao_do_repositorio(raiz)
    garantir_gancho_declarado(raiz, GANCHO_DO_DESPACHANTE_DE_CERCAS)
    garantir_gancho_declarado(raiz, GANCHO_DO_AVISO_DE_INDICE_FORA)
    garantir_gancho_declarado(raiz, GANCHO_DO_AVISO_DE_MOTORES)
    garantir_gancho_declarado(raiz, GANCHO_DA_COBRANCA_DE_DESTINO)
    garantir_gancho_declarado(raiz, GANCHO_DA_COBRANCA_DE_RELATO)
    garantir_gancho_declarado(raiz, GANCHO_DA_COBRANCA_DE_APRESENTACAO)
    garantir_gancho_declarado(raiz, GANCHO_DA_COBRANCA_DE_PENDENCIA)
    garantir_gancho_declarado(raiz, GANCHO_DA_COBRANCA_DO_CLONE_ATRASADO)
    garantir_ponte_para_a_outra_ferramenta(raiz)
    garantir_leitura_livre(raiz)
    garantir_regras_nativas_de_edicao(raiz)
    garantir_gancho_declarado(raiz, GANCHO_DO_LEMBRETE_DE_ESFRIAMENTO)
    garantir_gancho_declarado(raiz, GANCHO_DA_VERIFICACAO_DE_MCP)
    garantir_gancho_declarado(raiz, GANCHO_DA_VERIFICACAO_DE_AMBIENTE)
    garantir_ponte_do_devin_desligada(raiz)
    registrar_mcp_do_indice(raiz)
    semear_alvos_do_indice(raiz)
    liberar_servidores_mcp_declarados(raiz)
    espelhar_mcp_para_o_devin(raiz)
    acrescentar_linhas_que_faltam(raiz / ARQUIVO_GITIGNORE, IGNORAR_LIXO,
                                  ROTULO_DO_GITIGNORE_DO_LIXO, MOTIVO_LIXO)
    acrescentar_linhas_que_faltam(raiz / ARQUIVO_GITIGNORE, IGNORAR_LOCAL,
                                  ROTULO_DO_GITIGNORE_LOCAL, MOTIVO_LOCAL)
    acrescentar_linhas_que_faltam(raiz / ARQUIVO_GITATTRIBUTES,
                                  ATRIBUTOS_DO_LANCADOR, ROTULO_DOS_ATRIBUTOS,
                                  MOTIVO_DOS_ATRIBUTOS)

    print(SECAO_DO_VERSIONAMENTO.format(numero + 1))
    verificar_versionaveis(raiz)


def espelhos_com_fonte(raiz: Path) -> list:
    origem, copia = raiz / ORIGEM_SKILLS, raiz / COPIA_SKILLS
    espelhos = []
    if copia.exists():
        espelhos = [caminho.relative_to(raiz).as_posix()
                    for caminho in copia.rglob("*")
                    if caminho.is_file()
                    and (origem / caminho.relative_to(copia)).exists()]
    if (raiz / ARQUIVO_DA_REGRA_DE_CODIGO).is_file() \
            and (raiz / SKILL_DO_PADRAO_DE_CODIGO).is_file():
        espelhos.append(ARQUIVO_DA_REGRA_DE_CODIGO)
    return espelhos


def regra_de_codigo_gerada(raiz: Path):
    skill = raiz / SKILL_DO_PADRAO_DE_CODIGO
    if not skill.is_file():
        return None
    texto = skill.read_text(encoding="utf-8")
    corpo = texto.partition(FECHAMENTO_DO_FRONTMATTER)[2] \
        if texto.startswith("---") else texto
    corpo = corpo.partition(SECAO_DOS_PEDIDOS_DE_EXEMPLO)[0].strip() + "\n"
    frente = "---\npaths:\n" + "".join(
        f'  - "{c}"\n' for c in CAMINHOS_QUE_ACORDAM_A_REGRA_DE_CODIGO) + "---\n\n"
    return frente + corpo


def espelhar_regra_de_codigo(raiz: Path, escrevendo: bool = True) -> list:
    conteudo = regra_de_codigo_gerada(raiz)
    if conteudo is None:
        return []
    destino = raiz / ARQUIVO_DA_REGRA_DE_CODIGO
    if destino.exists() and destino.read_text(encoding="utf-8") == conteudo:
        return []
    if escrevendo:
        destino.parent.mkdir(parents=True, exist_ok=True)
        gravar_texto_com_quebras_unix(destino, conteudo)
    return [(ACAO_COPIADO if escrevendo else ACAO_FORA_DE_DIA,
             ARQUIVO_DA_REGRA_DE_CODIGO)]


def desligar_linhas_de_gancho(raiz: Path, caminhos, aviso: str) -> None:
    destino = raiz / ARQUIVO_SETTINGS
    configuracao = ler_json_ou_vazio(destino)
    ganchos = configuracao.get(CHAVE_DOS_GANCHOS) or {}
    mexeu = False
    for evento, blocos in list(ganchos.items()):
        vivos = [bloco for bloco in blocos
                 if not any(caminho in comando
                            for caminho in caminhos
                            for comando in comandos_do_bloco(bloco))]
        if len(vivos) != len(blocos):
            ganchos[evento] = vivos
            mexeu = True
    if mexeu:
        gravar_configuracao_json(destino, configuracao)
        print(aviso.format(", ".join(caminhos)))


def remover_ganchos_aposentados(raiz: Path) -> None:
    desligar_linhas_de_gancho(raiz, GANCHOS_APOSENTADOS,
                              LOG_GANCHO_APOSENTADO_REMOVIDO)
    desligar_linhas_de_gancho(raiz, CERCAS_QUE_O_DESPACHANTE_ASSUMIU,
                              LOG_CERCA_ASSUMIDA)


def caminhos_da_camada(raiz: Path) -> list:
    caminhos = (list(ARQUIVOS) + list(ESQUELETO) + list(paginas_da_camada())
                + [ARQUIVO_DO_REGISTRO_DA_INSTALACAO])
    for arquivos in modulos_da_camada().values():
        caminhos += list(arquivos)
    caminhos += espelhos_com_fonte(raiz)
    return sorted({caminho for caminho in caminhos if (raiz / caminho).exists()})


def caminhos_separados_por_nul(caminhos: list) -> bytes:
    return SEPARADOR_NUL.join(caminhos).encode("utf-8")


def e_regra_de_negacao(padrao: str) -> bool:
    return padrao.startswith(MARCA_DE_NEGACAO)


def ignorados_pelo_git(raiz: Path, caminhos: list):
    try:
        resposta = subprocess.run(
            ["git", "check-ignore", "-z", "-v", "--stdin"], cwd=raiz,
            input=caminhos_separados_por_nul(caminhos), capture_output=True)
    except OSError:
        print(LOG_SEM_GIT)
        return GIT_NAO_RESPONDEU
    if resposta.returncode not in SAIDAS_ESPERADAS_DO_CHECK_IGNORE:
        print(LOG_GIT_NAO_RESPONDEU.format(
            resposta.stderr.decode(errors="replace")[:60]))
        return GIT_NAO_RESPONDEU

    campos = resposta.stdout.decode("utf-8", "replace").split(SEPARADOR_NUL)
    escondidos = []
    for inicio in range(0, len(campos) - 3, CAMPOS_POR_CAMINHO_IGNORADO):
        fonte, numero, padrao, caminho = campos[
            inicio:inicio + CAMPOS_POR_CAMINHO_IGNORADO]
        if e_regra_de_negacao(padrao):
            continue
        escondidos.append((caminho, f"{fonte}:{numero}:{padrao}"))
    return escondidos


def fora_do_indice_do_git(raiz: Path, caminhos: list,
                          escondidos: list) -> list:
    rastreio = subprocess.run(["git", "ls-files", "-z"], cwd=raiz,
                              capture_output=True)
    if rastreio.returncode != 0:
        print(LOG_GIT_NAO_RESPONDEU_AO_INDICE)
        rastreados = set(caminhos)
    else:
        rastreados = set(rastreio.stdout.decode("utf-8", "replace")
                         .split(SEPARADOR_NUL))
    ja_escondidos = {caminho for caminho, _ in escondidos}
    return [caminho for caminho in caminhos
            if caminho not in rastreados and caminho not in ja_escondidos]


def relatar_versionamento(caminhos: list, escondidos: list,
                          fora_do_indice: list) -> None:
    if not escondidos and not fora_do_indice:
        print(LOG_VERSIONAMENTO_EM_DIA.format(len(caminhos)))
        return
    if escondidos:
        print(AVISO_IGNORADOS.format(len(escondidos), len(caminhos)))
        for caminho, regra in escondidos:
            print(AVISO_IGNORADO_ITEM.format(caminho, regra))
        print(AVISO_IGNORADOS_RODAPE)
    if fora_do_indice:
        print(AVISO_FORA_DO_INDICE.format(len(fora_do_indice), len(caminhos)))
        for caminho in fora_do_indice:
            print(AVISO_FORA_DO_INDICE_ITEM.format(caminho))
        print(AVISO_FORA_DO_INDICE_RODAPE)


def verificar_versionaveis(raiz: Path) -> None:
    caminhos = caminhos_da_camada(raiz)
    escondidos = ignorados_pelo_git(raiz, caminhos)
    if escondidos is GIT_NAO_RESPONDEU:
        return
    relatar_versionamento(caminhos, escondidos,
                          fora_do_indice_do_git(raiz, caminhos, escondidos))


def gravar(destino: Path, conteudo) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(conteudo, bytes):
        destino.write_bytes(conteudo)
        return
    gravar_texto_com_quebras_unix(destino, conteudo)


def escrever(destino: Path, conteudo, rotulo: str) -> None:
    if destino.exists():
        print(LOG_MANTIDO.format(rotulo))
        return
    gravar(destino, conteudo)
    print(LOG_CRIADO.format(rotulo))


def atualizar_arquivo(raiz: Path, caminho: str, conteudo) -> None:
    destino = raiz / caminho
    if not destino.exists():
        atual = None
    elif isinstance(conteudo, bytes):
        atual = destino.read_bytes()
    else:
        atual = destino.read_text(encoding="utf-8")
    if atual == conteudo:
        print(LOG_EM_DIA.format(caminho))
        return
    gravar(destino, conteudo)
    print((LOG_TROCADO_NA_ATUALIZACAO if atual is not None
           else LOG_CRIADO_NA_ATUALIZACAO).format(caminho))


def _saiu_com_erro(chamada) -> bool:
    try:
        chamada()
    except SystemExit:
        return True
    return False


BANCADA_SO_NA_CASA = ("bancada de testes ausente: os casos do instalador só "
                      "rodam no repositório da camada, onde modulos/ e as "
                      "fontes existem. Nada a rodar aqui.")


SONDA_DO_GANCHO = (
    "import json, os, sys\n"
    "json.dump({'argv0': sys.argv[0], 'arquivo': __file__, 'caminho0': sys.path[0], "
    "'resto': sys.argv[1:]}, open(os.path.join(os.path.dirname(__file__), 'visto.json'), 'w'))\n"
    "sys.exit(2)\n")
ARQUIVO_DA_SONDA_DO_GANCHO = ".claude/hooks/sonda-da-concha.py"
ENTRADA_QUE_O_CP1252_ESTRAGA = "ÁREA ÍNDICE"
SAIDA_FORA_DO_CP1252 = " → ok"
SONDA_DA_CODIFICACAO = (
    "import json, os, sys\n"
    "entrada = json.load(sys.stdin)\n"
    "json.dump({'visto': entrada['texto']}, open(os.path.join("
    "os.path.dirname(__file__), 'visto-codificacao.json'), 'w'))\n"
    "print(entrada['texto'] + " + ascii(SAIDA_FORA_DO_CP1252) + ")\n")
ARQUIVO_DA_SONDA_DA_CODIFICACAO = ".claude/hooks/sonda-da-codificacao.py"


def rodar_linha_de_gancho(linha: str, raiz: Path, cwd: Path, com_a_raiz: bool):
    import subprocess
    ambiente = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
    if com_a_raiz:
        ambiente["CLAUDE_PROJECT_DIR"] = str(raiz)
    return subprocess.run(linha, shell=True, cwd=str(cwd), env=ambiente,
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=60)


def rodar_linha_sem_o_modo_utf8(linha: str, raiz: Path, entrada: bytes):
    import subprocess
    ambiente = {k: v for k, v in os.environ.items()
                if k not in ("PYTHONUTF8", "PYTHONIOENCODING")}
    ambiente.update(PYTHONUTF8="0", PYTHONCOERCECLOCALE="0", LC_ALL="C",
                    CLAUDE_PROJECT_DIR=str(raiz))
    return subprocess.run(linha, shell=True, cwd=str(raiz), env=ambiente,
                          input=entrada, capture_output=True, timeout=60)


def casos_da_ponte_do_devin_com_ensaio(caso) -> None:
    import subprocess
    import tempfile

    instalador = str(Path(__file__).resolve())
    with tempfile.TemporaryDirectory(prefix="montar-devin-") as pasta:
        raiz = Path(pasta)
        subprocess.run(["git", "init", "-q", "."], cwd=raiz, capture_output=True)
        ensaio = subprocess.run([sys.executable, instalador, BANDEIRA_DEVIN], cwd=raiz,
                                capture_output=True, text=True, encoding="utf-8",
                                errors="replace", timeout=300)
        escrito = sorted(p.relative_to(raiz).as_posix() for p in raiz.rglob("*")
                         if ".git" not in p.relative_to(raiz).parts)
        caso("--devin sem --escrever não grava nada e diz o que gravaria — "
             "quem roda a bandeira achando que ensaia não instala a ponte "
             "nem módulo na raiz",
             ensaio.returncode == 0 and escrito == []
             and ARQUIVO_DOS_GANCHOS_DA_OUTRA in ensaio.stdout
             and BANDEIRA_ESCREVER in ensaio.stdout)
        gravado = subprocess.run([sys.executable, instalador, BANDEIRA_DEVIN,
                                  BANDEIRA_ESCREVER], cwd=raiz, capture_output=True,
                                 text=True, encoding="utf-8", errors="replace", timeout=300)
        caso("--devin --escrever instala a camada e liga a ponte, como a "
             "travessia espera",
             gravado.returncode == 0
             and (raiz / ARQUIVO_DOS_GANCHOS_DA_OUTRA).is_file()
             and (raiz / "AGENTS.md").is_file())


def casos_do_gancho_em_qualquer_concha(caso) -> None:
    import contextlib
    import io
    import tempfile

    molde = globals().get("comando_do_gancho")
    caso("todo gancho declarado sai sem variável de concha no texto do comando",
         all("$" not in comando_com_o_interpretador(g.comando, sys.executable)
             for g in ganchos_declarados()))
    caso("existe um molde só para o comando de gancho", callable(molde))
    if not callable(molde):
        return
    linha = comando_com_o_interpretador(molde(ARQUIVO_DA_SONDA_DO_GANCHO),
                                        sys.executable)
    with tempfile.TemporaryDirectory(prefix="montar-concha-") as pasta, \
            tempfile.TemporaryDirectory(prefix="montar-outro-cwd-") as outro:
        raiz = Path(pasta)
        sonda = raiz / ARQUIVO_DA_SONDA_DO_GANCHO
        sonda.parent.mkdir(parents=True)
        sonda.write_text(SONDA_DO_GANCHO, encoding="utf-8")
        visto = sonda.parent / "visto.json"
        corrida = rodar_linha_de_gancho(linha, raiz, Path(outro), True)
        leitura = (json.loads(visto.read_text(encoding="utf-8"))
                   if visto.is_file() else {})
        caso("a linha acha o gancho pela raiz do ambiente, mesmo com outro "
             "diretório atual, e devolve a saída 2 do gancho",
             corrida.returncode == 2
             and Path(leitura.get("arquivo", "")).resolve() == sonda.resolve())
        caso("o gancho vê a si mesmo em sys.argv[0], sem argumento sobrando",
             Path(leitura.get("argv0", "")).resolve() == sonda.resolve()
             and leitura.get("resto") == [])
        caso("a pasta dos ganchos entra no lugar do diretório atual no caminho "
             "de importação, e a biblioteca padrão não é sombreada por ele",
             Path(leitura.get("caminho0", "")).resolve()
             == sonda.parent.resolve())
        visto.unlink(missing_ok=True)
        sem_variavel = rodar_linha_de_gancho(linha, raiz, raiz, False)
        caso("sem a variável, a linha acha a raiz pelo diretório atual",
             sem_variavel.returncode == 2 and visto.is_file())
        ausente = rodar_linha_de_gancho(
            comando_com_o_interpretador(molde(".claude/hooks/nao-existe.py"),
                                        sys.executable), raiz, raiz, True)
        caso("gancho ausente sai 2, que barra, e diz qual arquivo faltou",
             ausente.returncode == 2 and "nao-existe.py" in ausente.stderr)
        antiga = ('python "${CLAUDE_PROJECT_DIR}/'
                  + ARQUIVO_DO_GANCHO_DE_BRANCH + '"')
        gancho_no_disco = raiz / ARQUIVO_DO_GANCHO_DE_BRANCH
        gancho_no_disco.write_text("", encoding="utf-8")
        evento = GANCHO_DO_VETO_DE_BRANCH.evento
        gravar_configuracao_json(raiz / ARQUIVO_SETTINGS, {CHAVE_DOS_GANCHOS: {
            evento: [{"matcher": GANCHO_DO_VETO_DE_BRANCH.matcher,
                      CHAVE_DOS_GANCHOS: [{"type": TIPO_DE_COMANDO,
                                           CHAVE_DO_COMANDO: antiga}]}]}})
        with contextlib.redirect_stdout(io.StringIO()):
            garantir_gancho_declarado(raiz, GANCHO_DO_VETO_DE_BRANCH)
        blocos = json.loads((raiz / ARQUIVO_SETTINGS).read_text(
            encoding="utf-8"))[CHAVE_DOS_GANCHOS][evento]
        caso("a linha antiga, com a variável no texto, é reescrita no lugar "
             "para o formato novo, sem duplicar o gancho",
             len(blocos) == 1
             and blocos[0][CHAVE_DOS_GANCHOS][0][CHAVE_DO_COMANDO]
             == comando_com_o_interpretador(COMANDO_DO_VETO_DE_BRANCH))
        codificacao = raiz / ARQUIVO_DA_SONDA_DA_CODIFICACAO
        codificacao.write_text(SONDA_DA_CODIFICACAO, encoding="utf-8")
        visto_na_entrada = codificacao.parent / "visto-codificacao.json"
        corrida = rodar_linha_sem_o_modo_utf8(
            comando_com_o_interpretador(molde(ARQUIVO_DA_SONDA_DA_CODIFICACAO),
                                        sys.executable),
            raiz, json.dumps({"texto": ENTRADA_QUE_O_CP1252_ESTRAGA},
                             ensure_ascii=False).encode("utf-8"))
        lido = (json.loads(visto_na_entrada.read_text(encoding="utf-8")).get(
            "visto") if visto_na_entrada.is_file() else None)
        caso("sem o modo UTF-8 no ambiente, a linha entrega ao gancho a "
             "entrada em UTF-8 intacta, com os bytes que o cp1252 não tem",
             lido == ENTRADA_QUE_O_CP1252_ESTRAGA)
        caso("sem o modo UTF-8 no ambiente, o gancho imprime o que o cp1252 "
             "não tem sem cair, e a saída sai em UTF-8",
             corrida.returncode == 0
             and corrida.stdout.decode("utf-8", errors="replace").strip()
             == ENTRADA_QUE_O_CP1252_ESTRAGA + SAIDA_FORA_DO_CP1252)
    caso("a ponte do Codex liga o modo UTF-8 no Python que o lançador escolhe",
         COMANDO_DA_PONTE_SEM_BARRA.startswith(
             f"{SHELL_DO_LANCADOR} {ARQUIVO_DO_LANCADOR} "
             f"{OPCAO_QUE_LIGA_O_MODO_UTF8} {ARQUIVO_DA_PONTE}"))
    caso("a ponte do Devin também liga o modo UTF-8",
         f"{ARQUIVO_DO_LANCADOR}\" {OPCAO_QUE_LIGA_O_MODO_UTF8} "
         in COMANDO_DA_PONTE)
    import tempfile
    with tempfile.TemporaryDirectory() as pasta:
        raiz = Path(pasta)
        antiga = COMANDO_DA_PONTE.replace(f"{OPCAO_QUE_LIGA_O_MODO_UTF8} ", "")
        (raiz / ARQUIVO_DOS_GANCHOS_DA_OUTRA).parent.mkdir(parents=True)
        (raiz / ARQUIVO_DOS_GANCHOS_DA_OUTRA).write_text(json.dumps(
            {EVENTO_DA_OUTRA: [{"hooks": [{"type": "command",
                                           CHAVE_DO_COMANDO: antiga}]}]}),
            encoding="utf-8")
        argumentos_de_verdade = sys.argv
        sys.argv = argumentos_de_verdade + [BANDEIRA_DEVIN]
        try:
            garantir_ponte_para_a_outra_ferramenta(raiz)
        finally:
            sys.argv = argumentos_de_verdade
        comandos = [g[CHAVE_DO_COMANDO] for grupo in json.loads(
            (raiz / ARQUIVO_DOS_GANCHOS_DA_OUTRA).read_text(
                encoding="utf-8"))[EVENTO_DA_OUTRA]
            for g in grupo["hooks"]]
        caso("a instalação troca a linha antiga da ponte do Devin no lugar, "
             "sem deixar duas", comandos == [COMANDO_DA_PONTE])


def casos_do_modulo_privado(caso) -> None:
    import tempfile

    with tempfile.TemporaryDirectory(prefix="montar-privado-") as pasta:
        raiz = Path(pasta)
        fonte = raiz / PASTA_MODULOS / "segredo" / ".agents" / "skills" / "s"
        fonte.mkdir(parents=True)
        (fonte / "SKILL.md").write_text("x", encoding="utf-8")
        publico = raiz / PASTA_MODULOS / "aberto" / ".agents" / "aberto"
        publico.mkdir(parents=True)
        (publico / "a.py").write_text("y", encoding="utf-8")
        em_uso = raiz / ORIGEM_SKILLS / "s"
        em_uso.mkdir(parents=True)
        (em_uso / "SKILL.md").write_text("x", encoding="utf-8")
        outra = raiz / ORIGEM_SKILLS / "livre"
        outra.mkdir(parents=True)
        (outra / "SKILL.md").write_text("z", encoding="utf-8")
        antes = sorted(modulos_que_viajam(raiz))
        (raiz / PASTA_MODULOS / "segredo" / MARCA_DE_MODULO_PRIVADO
         ).write_text("privado", encoding="utf-8")
        caso("sem a marca, o módulo viaja como qualquer outro",
             antes == ["aberto", "segredo"])
        caso("com a marca, o módulo privado não viaja, e o aberto continua",
             sorted(modulos_que_viajam(raiz)) == ["aberto"])
        caso("a marca não é instalada: ela é da pasta do módulo, não do "
             "destino",
             MARCA_DE_MODULO_PRIVADO not in arquivos_de_um_modulo(
                 raiz / PASTA_MODULOS / "segredo"))
        caso("a cópia em uso e o espelho da skill privada saem da lista do "
             "que é privado",
             caminhos_de_modulos_privados(raiz)
             == {".agents/skills/s/SKILL.md", ".claude/skills/s/SKILL.md"})
        lidas = paginas_no_disco(raiz)
        caso("o instalador não leva a cópia em uso da skill privada, e "
             "leva a skill que não é de módulo privado",
             ".agents/skills/s/SKILL.md" not in lidas
             and ".agents/skills/livre/SKILL.md" in lidas)
        skill_aberta = raiz / PASTA_MODULOS / "aberto" / ".agents" / "skills" / "a"
        skill_aberta.mkdir(parents=True)
        (skill_aberta / "SKILL.md").write_text("w", encoding="utf-8")
        copia_aberta = raiz / ORIGEM_SKILLS / "a"
        copia_aberta.mkdir(parents=True)
        (copia_aberta / "SKILL.md").write_text("w", encoding="utf-8")
        caso("o instalador não leva a cópia em uso da skill de módulo "
             "aberto: ela chega pelo módulo, e só a quem o liga",
             ".agents/skills/a/SKILL.md" not in paginas_no_disco(raiz)
             and ".agents/skills/livre/SKILL.md" in paginas_no_disco(raiz))
    caso("o ignore gerado trata como lixo o temporário do Google Drive "
         "para desktop, que nasce na raiz de pasta sincronizada",
         "/.tmp.driveupload/" in IGNORAR_LIXO)


PAGINA_NOVA_RASTREADA_DO_TESTE = ".agents/skills/portao/rastreada.md"
PAGINA_SOLTA_DO_TESTE = ".agents/skills/portao/solta.md"
ARQUIVO_DE_MODULO_SOLTO_DO_TESTE = ".agents/encadeador/solto.py"
PAGINA_QUE_A_CAMADA_MUDA_NO_TESTE = ".agents/skills/portao/SKILL.md"
COPIA_DE_MODULO_ENVELHECIDA_NO_TESTE = ".agents/encadeador/encadeador.py"
MODULO_COM_TERRITORIO_NO_TESTE = "observabilidade"
LINHA_NOVA_DA_CAMADA_NO_TESTE = "linha nova da camada\n"
ARQUIVOS_PROPRIOS_DO_TESTE = {
    ".agents/skills/minha-skill/SKILL.md": "a skill do repositório\n",
    ".claude/hooks/meu-gancho.py": "print('gancho do repositório')\r\n",
    ".agents/camada/meu-instrumento.py": "PRONTO = 1\n",
    "conhecimento/minha-pagina.md": "# página do repositório\n",
    "conhecimento/notas/minha-nota.md": "# nota do repositório\n",
    "montar.py": 'VERSAO = "0.1"\n',
}


REGRA_DO_DONO_NO_TESTE = "Edit(meu/**)"
PAGINAS_DA_CASA_DE_MENTIRA = (".agents/skills/portao/", "nucleo/",
                              PAGINA_REGRAS, ARQUIVO_DO_LANCADOR)
MODULOS_DA_CASA_DE_MENTIRA = ("encadeador", "observabilidade")


def rodar_git_calado(pasta: Path, *argumentos) -> None:
    subprocess.run(["git", *argumentos], cwd=pasta, check=True,
                   capture_output=True)


def copiar_a_camada_para(casa: Path) -> None:
    paginas, modulos = camada_da_pasta(casa_do_instalador())
    casa.mkdir(parents=True, exist_ok=True)
    for caminho, conteudo in paginas.items():
        if caminho.startswith(PAGINAS_DA_CASA_DE_MENTIRA):
            gravar(casa / caminho, conteudo)
    for nome, arquivos in modulos.items():
        if nome not in MODULOS_DA_CASA_DE_MENTIRA:
            continue
        for rotulo, conteudo in arquivos.items():
            gravar(casa / PASTA_MODULOS / nome / rotulo, conteudo)
    rodar_git_calado(casa, "init", "-q", ".")


def na_casa_de_mentira(casa: Path, chamada, gravacao=None,
                       sem_os_ajustes=False):
    import contextlib
    import io
    trocados = {"casa_do_instalador": lambda: casa,
                "declarar_teto_da_largada_medido": lambda raiz: None}
    if gravacao is not None:
        trocados["gravar"] = gravacao
    if sem_os_ajustes:
        trocados["garantir_ajustes"] = lambda raiz, numero: None
    de_verdade = {nome: globals()[nome] for nome in trocados}
    globals().update(trocados)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            return chamada()
    finally:
        globals().update(de_verdade)


def arquivos_da_camada(paginas: dict, modulos: dict) -> set:
    return set(paginas) | {rotulo for arquivos in modulos.values()
                           for rotulo in arquivos}


def enter_em_tudo(rotulo: str, padrao: str) -> str:
    return ""


def pergunta_que_nao_podia_sair(texto: str = "") -> str:
    raise AssertionError("o instalador perguntou sem terminal: " + texto)


def ler_o_executor_do_teste(raiz: Path) -> dict:
    try:
        return json.loads((raiz / ARQUIVO_DO_EXECUTOR_LOCAL).read_text(
            encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def nascer_no_teste(raiz: Path, respostas: dict, perguntados=None) -> dict:
    import contextlib
    import io
    import tempfile

    gravar_texto_com_quebras_unix(raiz / ARQUIVO_GITIGNORE,
                                  ARQUIVO_DO_EXECUTOR_LOCAL + "\n")

    def responder(rotulo: str, padrao: str) -> str:
        if perguntados is not None:
            perguntados.append(rotulo)
        return respostas.get(rotulo, "")
    with contextlib.redirect_stdout(io.StringIO()):
        nascer_o_executor(raiz, [BANDEIRA_DO_QUADRO, "dono/quadro"]
                          if perguntados is not None else [], responder)
    return ler_o_executor_do_teste(raiz)


def casos_da_configuracao_perguntada(caso) -> None:
    import contextlib
    import io
    import tempfile

    with tempfile.TemporaryDirectory() as pasta:
        dado = nascer_no_teste(Path(pasta), {
            ROTULO_DO_MODO: "so-issues",
            ROTULO_DO_PADRAO_DA_BRANCH: "trabalho/<numero>",
            ROTULO_DA_INTEGRACAO: "homolog"})
        caso(CASO_A_RESPOSTA_ENTRA_NO_EXECUTOR,
             dado.get("modo") == "so-issues"
             and dado.get("branches", {}).get("padrao_de_trabalho")
             == "trabalho/<numero>"
             and dado.get("branches", {}).get("integracao") == "homolog")
    with tempfile.TemporaryDirectory() as pasta:
        dado = nascer_no_teste(Path(pasta), {
            ROTULO_DO_MODO: "rapido",
            ROTULO_DO_PADRAO_DA_BRANCH: "trabalho/sem-o-numero"})
        caso(CASO_RESPOSTA_QUE_NAO_SERVE_FICA_O_PADRAO,
             dado.get("modo") == PADRAO_DO_MODO
             and dado.get("branches", {}).get("padrao_de_trabalho")
             == PADRAO_DA_BRANCH_DE_TRABALHO)
    with tempfile.TemporaryDirectory() as pasta:
        dado = nascer_no_teste(Path(pasta), {
            ROTULO_DO_PADRAO_DA_BRANCH: "issue/<numero> com espaco",
            ROTULO_DA_INTEGRACAO: "release..next"})
        caso(CASO_BRANCH_QUE_O_GIT_RECUSA_NAO_ENTRA,
             dado.get("branches", {}).get("padrao_de_trabalho")
             == PADRAO_DA_BRANCH_DE_TRABALHO
             and dado.get("branches", {}).get("integracao")
             == PADRAO_DA_INTEGRACAO)
    with tempfile.TemporaryDirectory() as pasta:
        perguntados = []
        dado = nascer_no_teste(Path(pasta), {}, perguntados)
        caso(CASO_ENDERECO_PEDIDO_NAO_SE_PERGUNTA,
             ROTULO_DO_ENDERECO not in perguntados
             and ROTULO_DO_MODO in perguntados
             and dado.get("issues", {}).get("repositorio") == "dono/quadro")
    with tempfile.TemporaryDirectory() as pasta:
        raiz = Path(pasta)
        rodar_git_calado(raiz, "init", "-q", "-b", "trabalho-do-teste")
        rodar_git_calado(raiz, "remote", "add", "origin",
                         "https://github.com/dono-do-teste/quadro-do-teste.git")
        dado = nascer_no_teste(raiz, {})
        caso(CASO_O_PADRAO_VEM_DO_REMOTO,
             dado.get("issues", {}).get("repositorio")
             == "dono-do-teste/quadro-do-teste"
             and dado.get("branches", {}).get("integracao")
             == "trabalho-do-teste")


def casos_dos_modulos_do_padrao(caso) -> None:
    import contextlib
    import io
    import tempfile

    caso(CASO_OBSERVABILIDADE_E_INSIGHTS_FORA_DO_PADRAO,
         "observabilidade" not in MODULOS_QUE_JA_VEM_LIGADOS
         and "insights" not in MODULOS_QUE_JA_VEM_LIGADOS)
    with tempfile.TemporaryDirectory() as pasta:
        caso(CASO_ATUALIZAR_NAO_INSTALA_MODULO_AUSENTE,
             modulos_a_montar(Path(pasta), sobrescrever=True) == []
             and "encadeador" in modulos_a_montar(Path(pasta),
                                                  sobrescrever=False))
    skills = casa_do_instalador() / ".agents" / "skills"
    citadas = re.findall(r"skill ([a-z]+-[a-z0-9-]+)", ARQUIVOS["AGENTS.md"])
    caso(CASO_O_MOLDE_SO_CITA_SKILL_QUE_EXISTE,
         citadas and all((skills / nome).is_dir() for nome in citadas))


def casos_do_leitor_da_pasta(caso) -> None:
    import contextlib
    import io
    import tempfile

    with tempfile.TemporaryDirectory() as pasta:
        ponta_da_casa = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=casa_do_instalador(),
            capture_output=True, text=True, encoding="utf-8",
            errors="replace").stdout.strip()
        registro = registro_da_instalacao(Path(pasta))
        caso(CASO_REGISTRO_NOMEIA_O_COMMIT,
             bool(ponta_da_casa)
             and registro.get("commit_da_camada") == ponta_da_casa
             and "versao" not in registro)
        dita = io.StringIO()
        with contextlib.redirect_stdout(dita):
            versao_do_instalador()
        sem_git = Path(pasta) / "sem-git"
        sem_git.mkdir()
        recado = ""
        try:
            na_casa_de_mentira(sem_git, versao_do_instalador)
        except SystemExit as saida:
            recado = str(saida.code)
        caso(CASO_VERSAO_E_O_COMMIT,
             bool(ponta_da_casa) and ponta_da_casa in dita.getvalue()
             and "git clone" in recado)

    with tempfile.TemporaryDirectory() as pasta:
        casa, alvo = Path(pasta) / "casa", Path(pasta) / "alvo"
        copiar_a_camada_para(casa)
        gravar(casa / PAGINA_NOVA_RASTREADA_DO_TESTE, TEXTO_QUALQUER_DO_TESTE)
        rodar_git_calado(casa, "add", "-A")
        gravar(casa / PAGINA_SOLTA_DO_TESTE, TEXTO_QUALQUER_DO_TESTE)
        gravar(casa / PASTA_MODULOS / "encadeador"
               / ARQUIVO_DE_MODULO_SOLTO_DO_TESTE, TEXTO_QUALQUER_DO_TESTE)
        gravar(casa / PASTA_MODULOS / "rascunho"
               / PAGINA_QUE_A_CAMADA_MUDA_NO_TESTE, TEXTO_QUALQUER_DO_TESTE)
        alvo.mkdir()
        rodar_git_calado(alvo, "init", "-q", ".")

        escritos = set()
        gravar_de_verdade = gravar

        def gravar_e_anotar(destino: Path, conteudo) -> None:
            if alvo in Path(destino).parents:
                escritos.add(Path(destino).relative_to(alvo).as_posix())
            gravar_de_verdade(destino, conteudo)

        argumentos_de_verdade = sys.argv
        sys.argv = argumentos_de_verdade + [BANDEIRA_MODULO,
                                            MODULO_COM_TERRITORIO_NO_TESTE]
        try:
            na_casa_de_mentira(casa, lambda: montar(alvo), gravar_e_anotar,
                               sem_os_ajustes=True)
        finally:
            sys.argv = argumentos_de_verdade
        caso(CASO_NAO_RASTREADO_NAO_E_INSTALADO,
             (alvo / PAGINA_NOVA_RASTREADA_DO_TESTE).is_file()
             and (alvo / COPIA_DE_MODULO_ENVELHECIDA_NO_TESTE).is_file()
             and not (alvo / PAGINA_SOLTA_DO_TESTE).exists()
             and not (alvo / ARQUIVO_DE_MODULO_SOLTO_DO_TESTE).exists())
        pagina_na_casa = casa / PAGINA_QUE_A_CAMADA_MUDA_NO_TESTE
        caso(CASO_MODULO_SOLTO_NAO_TIRA_PAGINA,
             pagina_na_casa.is_file()
             and (alvo / PAGINA_QUE_A_CAMADA_MUDA_NO_TESTE).is_file()
             and (alvo / PAGINA_QUE_A_CAMADA_MUDA_NO_TESTE).read_bytes()
             .replace(b"\r\n", b"\n")
             == pagina_na_casa.read_bytes().replace(b"\r\n", b"\n"))
        casa_resolvida = casa.resolve()
        na_casa_de_mentira(casa_resolvida,
                           lambda: registrar_a_instalacao(casa_resolvida, 0))
        caso(CASO_A_CASA_NAO_SE_REGISTRA,
             not (casa / ARQUIVO_DO_REGISTRO_DA_INSTALACAO).exists())

        registro = ler_json_ou_vazio(alvo / ARQUIVO_DO_REGISTRO_DA_INSTALACAO)
        registrados = set(registro.get("paginas", [])) | {
            rotulo for arquivos in (registro.get("modulos") or {}).values()
            for rotulo in arquivos}
        da_camada = arquivos_da_camada(*camada_da_pasta(casa))
        caso(CASO_REGISTRO_LISTA_O_QUE_FOI_ESCRITO,
             bool(registrados)
             and registrados == {rotulo for rotulo in escritos
                                 if rotulo in da_camada})

        for caminho, texto in ARQUIVOS_PROPRIOS_DO_TESTE.items():
            (alvo / caminho).parent.mkdir(parents=True, exist_ok=True)
            (alvo / caminho).write_bytes(texto.encode("utf-8"))
        do_territorio = next((rotulo for arquivos in (
            registro.get("modulos") or {}).values() for rotulo in arquivos
            if e_territorio_do_repositorio(rotulo)), None)
        proprios = dict(ARQUIVOS_PROPRIOS_DO_TESTE)
        if do_territorio:
            proprios[do_territorio] = "editado pelo repositório\n"
            (alvo / do_territorio).write_bytes(
                proprios[do_territorio].encode("utf-8"))
        (alvo / COPIA_DE_MODULO_ENVELHECIDA_NO_TESTE).write_text(
            "velho\n", encoding="utf-8")
        (alvo / PAGINA_QUE_A_CAMADA_MUDA_NO_TESTE).write_text(
            "velho\n", encoding="utf-8")
        na_casa = casa / PAGINA_QUE_A_CAMADA_MUDA_NO_TESTE
        if na_casa.is_file():
            gravar(na_casa, na_casa.read_text(encoding="utf-8")
                   + LINHA_NOVA_DA_CAMADA_NO_TESTE)
        camada_da_pasta.cache_clear()
        configuracao = ler_json_ou_vazio(alvo / ARQUIVO_SETTINGS)
        configuracao.setdefault(CHAVE_DAS_PERMISSOES, {}).setdefault(
            CHAVE_DO_DENY, []).append(REGRA_DO_DONO_NO_TESTE)
        gravar_configuracao_json(alvo / ARQUIVO_SETTINGS, configuracao)

        def atualizar_e_medir() -> tuple:
            dito = io.StringIO()
            with contextlib.redirect_stdout(dito):
                atualizar(alvo)
            return paginas_instaladas_fora_de_dia(alvo), dito.getvalue()

        atrasadas, dito = na_casa_de_mentira(casa, atualizar_e_medir)
        caso(CASO_ATUALIZACAO_AVISA_DO_INSTALADOR_ANTIGO,
             "instalador antigo" in dito
             and (alvo / "montar.py").read_bytes()
             == ARQUIVOS_PROPRIOS_DO_TESTE["montar.py"].encode("utf-8"))
        negadas = ler_json_ou_vazio(alvo / ARQUIVO_SETTINGS).get(
            CHAVE_DAS_PERMISSOES, {}).get(CHAVE_DO_DENY, [])
        na_casa_de_mentira(
            casa, lambda: garantir_regras_nativas_de_edicao(alvo))
        negadas_de_novo = ler_json_ou_vazio(alvo / ARQUIVO_SETTINGS).get(
            CHAVE_DAS_PERMISSOES, {}).get(CHAVE_DO_DENY, [])
        caso(CASO_REGRAS_NATIVAS_DE_EDICAO,
             {f"Edit(/{COPIA_SKILLS}/**)", "Edit(/.github/workflows/**)",
              "Edit(**/Jenkinsfile)",
              f"Edit(/{COPIA_DE_MODULO_ENVELHECIDA_NO_TESTE})",
              REGRA_DO_DONO_NO_TESTE} <= set(negadas)
             and do_territorio is not None
             and f"Edit(/{do_territorio})" not in negadas
             and len(negadas) == len(set(negadas))
             and negadas_de_novo == negadas)
        caso(CASO_ATUALIZACAO_PRESERVA_O_PROPRIO,
             do_territorio is not None
             and all((alvo / caminho).read_bytes() == texto.encode("utf-8")
                     for caminho, texto in proprios.items())
             and atrasadas == []
             and (alvo / PAGINA_QUE_A_CAMADA_MUDA_NO_TESTE).read_text(
                 encoding="utf-8").endswith(LINHA_NOVA_DA_CAMADA_NO_TESTE))

        gravados = []
        gravar_texto_de_verdade = gravar_texto_com_quebras_unix

        def gravar_so_dentro_da_casa(destino: Path, texto: str) -> None:
            gravados.append(Path(destino).resolve())
            if casa.resolve() in Path(destino).resolve().parents:
                gravar_texto_de_verdade(destino, texto)

        globals()["gravar_texto_com_quebras_unix"] = gravar_so_dentro_da_casa
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                sincronizar(casa)
        finally:
            globals()["gravar_texto_com_quebras_unix"] = gravar_texto_de_verdade
        caso(CASO_SINCRONIZAR_NAO_GRAVA_O_INSTALADOR,
             bool(gravados) and Path(__file__).resolve() not in gravados)

    with tempfile.TemporaryDirectory() as pasta:
        casa, alvo = Path(pasta) / "casa", Path(pasta) / "alvo"
        gravar(casa / PAGINA_NOVA_RASTREADA_DO_TESTE, TEXTO_QUALQUER_DO_TESTE)
        alvo.mkdir()
        rodar_git_calado(alvo, "init", "-q", ".")
        recado = ""
        try:
            na_casa_de_mentira(casa, lambda: montar(alvo))
        except SystemExit as saida:
            recado = str(saida.code)
        caso(CASO_CASA_SEM_GIT_E_RECUSADA,
             "git clone" in recado
             and [p.name for p in alvo.iterdir()] == [PASTA_DO_GIT])


def testar() -> int:
    if not e_a_casa_do_desenvolvimento(casa_do_instalador()):
        print(BANCADA_SO_NA_CASA)
        return 0
    import builtins
    import contextlib
    import io
    import tempfile

    ENDERECO_DA_CONFIGURACAO_COBRADO_A_MAO = "nucleo/configuracao.json"
    ENDERECO_ANTIGO_COBRADO_A_MAO = "configuracao-da-casa.md"

    falhas = []
    rodados = 0

    def caso(rotulo: str, passou: bool) -> None:
        nonlocal rodados
        rodados += 1
        if not passou:
            falhas.append(FALHA_DO_CASO.format(rotulo))

    try:
        molde = json.loads(CONFIGURACAO_POR_PREENCHER)
    except (json.JSONDecodeError, TypeError):
        molde = {}
    caso(CASO_MOLDE_E_JSON, isinstance(molde, dict) and molde)
    casos_do_espelho_sem_barra(caso)
    casos_do_orfao_no_espelho_de_skills(caso)
    casos_do_modulo_privado(caso)
    casos_do_gancho_em_qualquer_concha(caso)
    casos_da_ponte_do_devin_com_ensaio(caso)
    caso(CASO_MOLDE_POR_PREENCHER,
         "${" in str(molde.get("repositorio_das_issues", "")))
    caso(CASO_MOLDE_MANDA_PERGUNTAR,
         any("${" in regra and "issue" in regra
             for regra in molde.get("regras", []) if isinstance(regra, str)))

    with tempfile.TemporaryDirectory() as pasta:
        raiz = Path(pasta)
        alvo = raiz / ENDERECO_DA_CONFIGURACAO_COBRADO_A_MAO

        with contextlib.redirect_stdout(io.StringIO()):
            garantir_configuracao_do_repositorio(raiz)
        caso(CASO_MOLDE_CHEGA_AO_REPOSITORIO.format(
            ENDERECO_DA_CONFIGURACAO_COBRADO_A_MAO), alvo.is_file())

        if alvo.is_file():
            preenchido = alvo.read_text(encoding="utf-8").replace(
                MOLDE_DO_REPOSITORIO_DAS_ISSUES, REPOSITORIO_DO_TESTE)
            gravar_texto_com_quebras_unix(alvo, preenchido)
            with contextlib.redirect_stdout(io.StringIO()):
                garantir_configuracao_do_repositorio(raiz)
            caso(CASO_ATUALIZACAO_NAO_REESCREVE,
                 alvo.read_text(encoding="utf-8") == preenchido)

        (raiz / ENDERECO_ANTIGO_COBRADO_A_MAO).write_text(
            TEXTO_QUALQUER_DO_TESTE, encoding="utf-8")
        saida_capturada = io.StringIO()
        with contextlib.redirect_stdout(saida_capturada):
            garantir_configuracao_do_repositorio(raiz)
        caso(CASO_ENDERECO_VELHO_AVISADO,
             ENDERECO_ANTIGO_COBRADO_A_MAO in saida_capturada.getvalue())

    with tempfile.TemporaryDirectory() as pasta:
        raiz = Path(pasta)
        subprocess.run(["git", "init", "-q", str(raiz)], check=True,
                       capture_output=True)
        with contextlib.redirect_stdout(io.StringIO()):
            montar(raiz)
        declarado = json.loads(
            (raiz / ARQUIVO_CONFIGURACAO).read_text(encoding="utf-8")
        ).get(CHAVE_DO_TETO_DA_LARGADA)
        medida = largada_medida(raiz)
        caso(CASO_TETO_DA_LARGADA_NASCE_MEDIDO,
             isinstance(declarado, int) and medida is not None
             and declarado == medida > 0)
        configuracao = json.loads(
            (raiz / ARQUIVO_CONFIGURACAO).read_text(encoding="utf-8"))
        configuracao[CHAVE_DO_TETO_DA_LARGADA] = medida + 1000
        gravar_configuracao_json(raiz / ARQUIVO_CONFIGURACAO, configuracao)
        with contextlib.redirect_stdout(io.StringIO()):
            declarar_teto_da_largada_medido(raiz)
        caso(CASO_TETO_DA_LARGADA_DECLARADO_FICA,
             json.loads((raiz / ARQUIVO_CONFIGURACAO).read_text(
                 encoding="utf-8")).get(CHAVE_DO_TETO_DA_LARGADA)
             == medida + 1000)
        settings = (raiz / ARQUIVO_SETTINGS).read_text(encoding="utf-8")
        atributos = raiz / ARQUIVO_GITATTRIBUTES
        caso(CASO_ARVORE_VIRGEM_RECEBE_O_LANCADOR,
             (raiz / ARQUIVO_DO_LANCADOR).is_file()
             and "python3" not in settings
             and atributos.is_file()
             and ATRIBUTOS_DO_LANCADOR[0] in atributos.read_text(
                 encoding="utf-8"))
        despachante = raiz / ARQUIVO_DO_DESPACHANTE_DE_CERCAS
        bloco = BLOCO_DAS_CERCAS_NO_DESPACHANTE.search(
            despachante.read_text(encoding="utf-8"))
        listadas = CERCA_NO_DESPACHANTE.findall(bloco.group(1)) if bloco else []
        caso(CASO_ARVORE_VIRGEM_TEM_TODA_CERCA_DO_DESPACHANTE,
             bool(listadas) and all(
                 (despachante.parent / f"{nome}.py").is_file()
                 for nome in listadas))
        leitura = raiz / "LEIAME.txt"
        leitura.write_text(TEXTO_QUALQUER_DO_TESTE, encoding="utf-8")
        ambiente = dict(os.environ)
        ambiente["CLAUDE_PROJECT_DIR"] = str(raiz)
        resposta = subprocess.run(
            [sys.executable, str(despachante)], capture_output=True,
            text=True, encoding="utf-8", errors="replace", env=ambiente,
            cwd=str(raiz), timeout=120,
            input=json.dumps({"hook_event_name": EVENTO_ANTES_DA_FERRAMENTA,
                              "tool_name": "Read", "session_id": "virgem",
                              "cwd": str(raiz),
                              "tool_input": {"file_path": str(leitura)}}))
        caso(CASO_ARVORE_VIRGEM_DEIXA_LER,
             resposta.returncode == 0 and '"deny"' not in resposta.stdout)
        ligados_no_fim_de_turno = json.dumps(
            json.loads(settings).get("hooks", {}).get(EVENTO_DE_FIM_DE_TURNO))
        caso(CASO_ARVORE_VIRGEM_LIGA_A_COBRANCA_DO_CLONE,
             "avisar-clone-desatualizado" in listadas
             and "avisar-clone-desatualizado.py" in ligados_no_fim_de_turno)

    caso(CASO_CONFIGURACAO_FORA_DE_PAGINAS,
         ENDERECO_DA_CONFIGURACAO_COBRADO_A_MAO not in paginas_da_camada())
    caso(CASO_CONFIGURACAO_FORA_DE_FONTES,
         not any(ENDERECO_DA_CONFIGURACAO_COBRADO_A_MAO == padrao
                 or padrao.startswith(GLOB_DO_NUCLEO)
                 for padrao in FONTES))

    with tempfile.TemporaryDirectory() as pasta:
        raiz = Path(pasta)
        scripts = raiz / ORIGEM_SKILLS / "s" / "scripts"
        (scripts / CACHE_DE_EXECUCAO).mkdir(parents=True)
        (scripts / "s.py").write_text(TEXTO_QUALQUER_DO_TESTE, encoding="utf-8")
        (scripts / CACHE_DE_EXECUCAO / "s.pyc").write_bytes(b"\0")
        colhidas = paginas_no_disco(raiz)
        espelho = raiz / COPIA_SKILLS
        copiar_skills_para_o_espelho(raiz / ORIGEM_SKILLS, espelho, raiz, True)
        caso(CASO_CACHE_DE_EXECUCAO_FICA_FORA,
             f"{ORIGEM_SKILLS}/s/scripts/s.py" in colhidas
             and not any(CACHE_DE_EXECUCAO in rotulo for rotulo in colhidas)
             and (espelho / "s" / "scripts" / "s.py").is_file()
             and not (espelho / "s" / "scripts" / CACHE_DE_EXECUCAO).exists())

    with tempfile.TemporaryDirectory() as pasta:
        raiz = Path(pasta)
        fonte = raiz / PASTA_MODULOS / "m" / ".agents" / "m" / "m.py"
        fonte.parent.mkdir(parents=True)
        fonte.write_text(TEXTO_QUALQUER_DO_TESTE, encoding="utf-8")
        em_uso = raiz / ".agents" / "m" / "m.py"
        em_uso.parent.mkdir(parents=True)
        em_uso.write_text(TEXTO_QUALQUER_DO_TESTE, encoding="utf-8")
        caso(CASO_COPIA_IGUAL_CALA, copias_de_modulo_que_divergem(raiz) == [])
        em_uso.write_text(TEXTO_QUALQUER_DO_TESTE + "a", encoding="utf-8")
        caso(CASO_COPIA_DIVERGENTE_ACUSADA,
             len(copias_de_modulo_que_divergem(raiz)) == 1)
        roteiro = raiz / PASTA_MODULOS / "m" / "execucoes" / "r.json"
        roteiro.parent.mkdir(parents=True)
        roteiro.write_text(TEXTO_QUALQUER_DO_TESTE, encoding="utf-8")
        (raiz / "execucoes").mkdir()
        (raiz / "execucoes" / "r.json").write_text("outro", encoding="utf-8")
        caso(CASO_ROTEIRO_DIVERGENTE_ACUSADO,
             len(copias_de_modulo_que_divergem(raiz)) == 2)
        molde = (raiz / PASTA_MODULOS / "m" / PASTA_DO_CONHECIMENTO / "m"
                 / "p.md")
        molde.parent.mkdir(parents=True)
        molde.write_text(TEXTO_QUALQUER_DO_TESTE, encoding="utf-8")
        (raiz / PASTA_DO_CONHECIMENTO / "m").mkdir(parents=True)
        (raiz / PASTA_DO_CONHECIMENTO / "m" / "p.md").write_text(
            "outro", encoding="utf-8")
        caso(CASO_MOLDE_DO_REPOSITORIO_NAO_CONTA,
             len(copias_de_modulo_que_divergem(raiz)) == 2)
        escritas = sincronizar_copias_de_modulo(raiz, escrevendo=True)
        caso(CASO_COPIA_REGRAVADA_DA_FONTE,
             len(escritas) == 2
             and em_uso.read_text(encoding="utf-8")
             == TEXTO_QUALQUER_DO_TESTE
             and (raiz / "execucoes" / "r.json").read_text(encoding="utf-8")
             == TEXTO_QUALQUER_DO_TESTE)
        caso(CASO_COPIA_EM_DIA_NAO_REESCREVE,
             sincronizar_copias_de_modulo(raiz, escrevendo=True) == [])
        fonte_nova = raiz / PASTA_MODULOS / "m" / ".agents" / "m" / "novo.py"
        fonte_nova.write_text(TEXTO_QUALQUER_DO_TESTE, encoding="utf-8")
        caso(CASO_COPIA_AUSENTE_NAO_E_INSTALADA,
             sincronizar_copias_de_modulo(raiz, escrevendo=True) == []
             and not (raiz / ".agents" / "m" / "novo.py").exists())
        caso(CASO_MOLDE_SEGUE_INTACTO,
             (raiz / PASTA_DO_CONHECIMENTO / "m" / "p.md")
             .read_text(encoding="utf-8") == "outro")

    caso(CASO_AUTORIZACAO_NASCE_NEGADA,
         set(MOLDE_DA_CONFIGURACAO["autorizacoes"].values()) == {False})
    caso(CASO_MAIN_ENTRA_POR_INCORPORACAO,
         MOLDE_DA_CONFIGURACAO["branches_por_incorporacao"] == ["main"])
    with tempfile.TemporaryDirectory() as pasta:
        alvo = Path(pasta)
        for caminho, texto in paginas_da_camada().items():
            destino = alvo / caminho
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(texto, encoding="utf-8")
        caso(CASO_ALVO_EM_DIA_NAO_ACUSA,
             paginas_instaladas_fora_de_dia(alvo) == [])
        uma = next(iter(paginas_da_camada()))
        (alvo / uma).write_text("mudou", encoding="utf-8")
        caso(CASO_ALVO_ATRASADO_ACUSA,
             paginas_instaladas_fora_de_dia(alvo) == [uma])
        (alvo / uma).unlink()
        caso(CASO_ALVO_SEM_PAGINA_ACUSA,
             paginas_instaladas_fora_de_dia(alvo) == [uma])

    caso(CASO_CONSELHO_EM_CASA,
         BANDEIRA_SINCRONIZAR in conselho_da_divergencia(casa_do_instalador()))
    caso(CASO_CONSELHO_NO_ALVO,
         BANDEIRA_ATUALIZAR in conselho_da_divergencia(Path("/")))

    with tempfile.TemporaryDirectory() as pasta:
        raiz = Path(pasta)
        pagina = raiz / PAGINA_INSTRUCOES
        caso(CASO_SEM_PAGINA_NAO_E_DO_DONO, not e_instrucao_do_dono(pagina))
        pagina.write_text(MARCA_INSTRUCOES + "\n\n# gerado\n", encoding="utf-8")
        caso(CASO_PAGINA_MARCADA_E_DA_CAMADA, not e_instrucao_do_dono(pagina))
        pagina.write_text("# as instruções deste repositório\n",
                          encoding="utf-8")
        caso(CASO_PAGINA_SEM_MARCA_E_DO_DONO, e_instrucao_do_dono(pagina))
        caso(CASO_SINCRONIZAR_SO_EM_CASA,
             _saiu_com_erro(lambda: recusar_sincronizar_fora_de_casa(raiz)))
    caso(CASO_SINCRONIZAR_EM_CASA_PASSA,
         recusar_sincronizar_fora_de_casa(casa_do_instalador()) is None)

    lancador = casa_do_instalador() / ARQUIVO_DO_LANCADOR
    try:
        versao = subprocess.run(
            [shutil.which(SHELL_DO_LANCADOR) or SHELL_DO_LANCADOR,
             str(lancador), "-c", PERGUNTA_DA_VERSAO],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=TETO_DO_INTERPRETADOR_S)
        lancador_respondeu = (versao.returncode == 0
                              and versao.stdout.strip() == VERSAO_QUE_SERVE)
    except (OSError, subprocess.SubprocessError):
        lancador_respondeu = False
    caso(CASO_LANCADOR_RODA_PYTHON_3, lancador_respondeu)
    caso(CASO_MARCADOR_SAI_DO_COMANDO,
         MARCADOR_DO_INTERPRETADOR not in comando_com_o_interpretador(
             COMANDO_DO_VETO_DE_BRANCH))
    medido = interpretador_desta_maquina()
    caso(CASO_TODO_GANCHO_CHAMA_O_INTERPRETADOR,
         all(comando_com_o_interpretador(g.comando).startswith(
             chamada_do_gancho(medido)) for g in ganchos_declarados())
         and not any(comando_com_o_interpretador(g.comando).startswith(
             "python3 ") for g in ganchos_declarados()))
    caso(CASO_SEM_PYTHON_O_GANCHO_VOLTA_AO_LANCADOR,
         comando_com_o_interpretador(
             COMANDO_DO_VETO_DE_BRANCH, "").startswith(LANCADOR_NO_GANCHO))
    caso(CASO_CAMINHO_COM_ESPACO_VAI_ENTRE_ASPAS,
         comando_com_o_interpretador(
             COMANDO_DO_VETO_DE_BRANCH,
             "C:/Program Files/Python/python.exe").startswith(
                 '"C:/Program Files/Python/python.exe"'))
    de_outro_jeito = COMANDO_DO_VETO_DE_BRANCH.replace(
        MARCADOR_DO_INTERPRETADOR, "py -3")
    with tempfile.TemporaryDirectory() as pasta:
        raiz = Path(pasta)
        gancho_no_disco = raiz / ARQUIVO_DO_GANCHO_DE_BRANCH
        gancho_no_disco.parent.mkdir(parents=True)
        gancho_no_disco.write_text("", encoding="utf-8")
        evento = GANCHO_DO_VETO_DE_BRANCH.evento
        gravar_configuracao_json(raiz / ARQUIVO_SETTINGS, {CHAVE_DOS_GANCHOS: {
            evento: [{"matcher": GANCHO_DO_VETO_DE_BRANCH.matcher,
                      CHAVE_DOS_GANCHOS: [{"type": TIPO_DE_COMANDO,
                                           CHAVE_DO_COMANDO: de_outro_jeito}]}]}})
        with contextlib.redirect_stdout(io.StringIO()):
            garantir_gancho_declarado(raiz, GANCHO_DO_VETO_DE_BRANCH)
        blocos = json.loads((raiz / ARQUIVO_SETTINGS).read_text(
            encoding="utf-8"))[CHAVE_DOS_GANCHOS][evento]
        caso(CASO_GANCHO_COM_OUTRO_INTERPRETADOR_E_REESCRITO,
             len(blocos) == 1
             and blocos[0][CHAVE_DOS_GANCHOS][0][CHAVE_DO_COMANDO]
             == comando_com_o_interpretador(COMANDO_DO_VETO_DE_BRANCH))
    caso(CASO_GANCHO_DE_OUTRO_ARQUIVO_NAO_CONTA,
         not tem_comando_declarado(
             [{CHAVE_DOS_GANCHOS: [{CHAVE_DO_COMANDO: de_outro_jeito}]}],
             COMANDO_DO_VETO_DE_POLITICA))

    so_as_regras = {"titulo": "t", "introducao": [], "rodape_titulo": "r",
                    "rodape": [], "regras": []}
    caso(CASO_REGRAS_SEM_CABECALHO,
         linhas_da_pagina_de_regras(so_as_regras, set())[0]
         == MARCA_GERADA)

    regra_com_procedencia = {
        "titulo": "t", "introducao": [], "rodape_titulo": "r",
        "rodape": [],
        "regras": [{"id": 1, "regra": "r", "procedencia": {
            "titulo": "mapa", "endereco": "mapa.md"}}]}
    viaja = {endereco_da_pagina_de_conhecimento("mapa.md")}
    caso(CASO_PROCEDENCIA_DE_PAGINA_VIVA_ENTRA,
         any("(mapa.md)" in linha for linha in
             linhas_da_pagina_de_regras(regra_com_procedencia, viaja)))
    caso(CASO_PROCEDENCIA_DE_PAGINA_MORTA_SAI,
         not any("mapa.md" in linha for linha in
                 linhas_da_pagina_de_regras(regra_com_procedencia, set())))
    for caminho, embutido in ESQUELETO.items():
        no_disco = casa_do_instalador() / caminho
        caso(CASO_ESQUELETO_BATE_COM_O_DISCO.format(caminho),
             not no_disco.is_file()
             or no_disco.read_text(encoding="utf-8").replace("\r\n", "\n")
             == embutido)

    argv_de_verdade = sys.argv
    try:
        sys.argv = ["montar.py", "--conferir"]
        caso(CASO_BANDEIRA_FANTASMA_ACUSADA,
             argumentos_desconhecidos() == ["--conferir"])
        sem_valor = [b for b in BANDEIRAS_CONHECIDAS if b != BANDEIRA_MODULO]
        sys.argv = ["montar.py", *sem_valor, BANDEIRA_MODULO, "encadeador"]
        caso(CASO_BANDEIRAS_DE_VERDADE_PASSAM, argumentos_desconhecidos() == [])
        sys.argv = ["montar.py", BANDEIRA_MODULO_COM_IGUAL + "encadeador"]
        caso(CASO_MODULO_COM_IGUAL_PASSA, argumentos_desconhecidos() == [])
        sys.argv = ["montar.py", BANDEIRA_MODULO, "encadeador"]
        caso(CASO_VALOR_DE_MODULO_NAO_E_BANDEIRA, argumentos_desconhecidos() == [])
        sys.argv = ["montar.py", "verificar"]
        caso(CASO_POSICIONAL_TORTO_ACUSADO,
             argumentos_desconhecidos() == ["verificar"])
        sys.argv = ["montar.py", BANDEIRA_MODULO]
        caso(CASO_MODULO_SEM_NOME_PARA, _saiu_com_erro(argumentos_desconhecidos))
    finally:
        sys.argv = argv_de_verdade

    with tempfile.TemporaryDirectory() as pasta:
        alvo = Path(pasta)
        mudo = io.StringIO()
        with contextlib.redirect_stdout(mudo):
            saiu = montar(alvo)
        caso(CASO_MONTAGEM_INTEIRA_RODA, saiu == 0)
        caso(CASO_MONTAGEM_ENTREGA_AS_INSTRUCOES,
             (alvo / PAGINA_INSTRUCOES).is_file())
        entregues = ((alvo / PAGINA_INSTRUCOES).read_text(encoding="utf-8")
                     if (alvo / PAGINA_INSTRUCOES).is_file() else "")
        caso(CASO_INSTRUCOES_DIZEM_ONDE_A_ISSUE_NASCE,
             "onde as issues nascem" in entregues.lower()
             and ARQUIVO_CONFIGURACAO in entregues)
        desta_maquina = ""
        aqui = casa_do_instalador() / ARQUIVO_DO_EXECUTOR_LOCAL
        if aqui.is_file():
            try:
                declarado = json.loads(aqui.read_text(encoding="utf-8"))
                desta_maquina = (declarado.get("issues") or {}).get(
                    "repositorio") or ""
            except (json.JSONDecodeError, TypeError, AttributeError):
                desta_maquina = ""
        caso(CASO_INSTRUCOES_NAO_CARREGAM_O_ENDERECO,
             not desta_maquina or desta_maquina not in entregues)

    with tempfile.TemporaryDirectory() as pasta:
        alvo = Path(pasta)
        subprocess.run(["git", "init", "-q", "."], cwd=alvo, check=True)
        mudo = io.StringIO()
        with contextlib.redirect_stdout(mudo):
            montar(alvo)
            instalar_modulo(alvo, "encadeador", sobrescrever=True)
            chegada_inteira = verificar_a_camada_instalada(alvo)
        caso(CASO_CHEGADA_INTEIRA_CALA, chegada_inteira == 0)

        alvo_do_motor = alvo / ".agents/encadeador/encadeador.py"
        alvo_do_motor.write_text("lixo, nao sou o motor\n", encoding="utf-8")
        atrasadas = paginas_instaladas_fora_de_dia(alvo)
        caso(CASO_CHEGADA_MUTILADA_ACUSA,
             ".agents/encadeador/encadeador.py" in atrasadas)

        do_encadeador = modulos_da_camada()["encadeador"]
        outro_do_modulo = next(
            caminho for caminho in do_encadeador
            if caminho != ".agents/encadeador/encadeador.py"
            and not e_territorio_do_repositorio(caminho)
            and isinstance(do_encadeador[caminho], str))
        (alvo / outro_do_modulo).write_text("tambem divergi\n",
                                            encoding="utf-8")
        dito_sem_sobrescrever = io.StringIO()
        with contextlib.redirect_stdout(dito_sem_sobrescrever):
            instalar_modulo(alvo, "encadeador", sobrescrever=False)
        linhas_ditas = dito_sem_sobrescrever.getvalue().splitlines()
        acusadas = [linha for linha in linhas_ditas
                    if MARCA_DE_COPIA_DIVERGENTE in linha]
        caso(CASO_COPIA_DIVERGENTE_E_DITA,
             alvo_do_motor.read_text(encoding="utf-8")
             == "lixo, nao sou o motor\n"
             and any(".agents/encadeador/encadeador.py" in linha
                     for linha in acusadas)
             and any(outro_do_modulo in linha for linha in acusadas)
             and conselho_da_divergencia(alvo).strip()
             in dito_sem_sobrescrever.getvalue())
        caso(CASO_COPIA_IGUAL_SEGUE_SO_MANTIDA,
             len(acusadas) == 2
             and len(do_encadeador) > 2)
        caso(CASO_ARQUIVO_BINARIO_NAO_SE_NORMALIZA,
             difere_da_camada_em_memoria(b"\x00a\r\nb", b"\x00a\nb") is True
             and difere_da_camada_em_memoria(b"a\r\nb", "a\nb") is False)

        arquivo_do_territorio = next(
            (c for c in modulos_da_camada().get("observabilidade", {})
             if e_territorio_do_repositorio(c)), None)
        if arquivo_do_territorio:
            (alvo / arquivo_do_territorio).parent.mkdir(
                parents=True, exist_ok=True)
            (alvo / arquivo_do_territorio).write_text(
                "editado pelo repositorio\n", encoding="utf-8")
            caso(CASO_TERRITORIO_NAO_E_COBRADO,
                 arquivo_do_territorio
                 not in paginas_instaladas_fora_de_dia(alvo))

        de_verdade = casa_do_instalador
        globals()["casa_do_instalador"] = lambda: alvo
        try:
            caso(CASO_INSTALACAO_FRESCA_NAO_CAI_NO_RAMO_ERRADO,
                 not e_a_casa_do_desenvolvimento(alvo))
        finally:
            globals()["casa_do_instalador"] = de_verdade

    with tempfile.TemporaryDirectory() as pasta:
        raiz = Path(pasta)
        silencio = io.StringIO()
        with contextlib.redirect_stdout(silencio):
            liberar_servidores_mcp_declarados(raiz)
            espelhar_mcp_para_o_devin(raiz)
            registrar_mcp_do_indice(raiz)
        caso(CASO_SEM_MCP_NADA_NASCE,
             not (raiz / ARQUIVO_SETTINGS_LOCAL).exists()
             and not (raiz / ARQUIVO_MCP_LOCAL_DO_DEVIN).exists()
             and not (raiz / ARQUIVO_DE_DECLARACAO_DE_MCP).exists())

        declarados = {CHAVE_DOS_SERVIDORES_MCP: {
            "local": {"command": "python", "args": ["servidor.py", "--x"]},
            "remoto": {"type": "http", "url": "https://mcp.exemplo/mcp",
                       "headers": {"Authorization": "Bearer ${TOKEN}"}},
            "torto": {"type": "sdk"}}}
        gravar_configuracao_json(raiz / ARQUIVO_DE_DECLARACAO_DE_MCP,
                                 declarados)
        (raiz / ARQUIVO_SETTINGS_LOCAL).parent.mkdir(parents=True)
        gravar_configuracao_json(raiz / ARQUIVO_SETTINGS_LOCAL,
                                 {"permissions": {"allow": ["Bash(ls)"]}})
        with contextlib.redirect_stdout(silencio):
            liberar_servidores_mcp_declarados(raiz)
        local = ler_json_ou_vazio(raiz / ARQUIVO_SETTINGS_LOCAL)
        caso(CASO_LIBERACAO_SAI_DA_DECLARACAO,
             local.get(CHAVE_DOS_MCP_PERMITIDOS) == [
                 {"serverCommand": ["python", "servidor.py", "--x"]},
                 {"serverUrl": "https://mcp.exemplo/mcp"}]
             and local.get("permissions") == {"allow": ["Bash(ls)"]})
        antes = (raiz / ARQUIVO_SETTINGS_LOCAL).read_text(encoding="utf-8")
        with contextlib.redirect_stdout(silencio):
            liberar_servidores_mcp_declarados(raiz)
        caso(CASO_LIBERACAO_NAO_DUPLICA,
             (raiz / ARQUIVO_SETTINGS_LOCAL).read_text(
                 encoding="utf-8") == antes)

        with contextlib.redirect_stdout(silencio):
            espelhar_mcp_para_o_devin(raiz)
        caso(CASO_DEVIN_RECEBE_O_ESPELHO,
             ler_json_ou_vazio(raiz / ARQUIVO_MCP_LOCAL_DO_DEVIN) == declarados)
        caso(CASO_ESPELHO_DO_DEVIN_FICA_FORA_DO_GIT,
             ARQUIVOS[".devin/.gitignore"].strip()
             == Path(ARQUIVO_MCP_LOCAL_DO_DEVIN).name
             and Path(ARQUIVO_MCP_LOCAL_DO_DEVIN).name in (
                 raiz / ".devin" / ARQUIVO_GITIGNORE).read_text(
                     encoding="utf-8").splitlines())

        (raiz / ARQUIVO_QUE_PROVA_O_MODULO_INDICE).parent.mkdir(parents=True)
        (raiz / ARQUIVO_QUE_PROVA_O_MODULO_INDICE).write_text(
            "", encoding="utf-8")
        with contextlib.redirect_stdout(silencio):
            registrar_mcp_do_indice(raiz)
        registrados = servidores_mcp_declarados(raiz)
        caso(CASO_INDICE_ENTRA_SEM_APAGAR_OS_OUTROS,
             set(registrados) == {"local", "remoto", "torto",
                                  NOME_DO_MCP_DO_INDICE}
             and PACOTE_DO_SERVIDOR_DO_INDICE in (
                 registrados[NOME_DO_MCP_DO_INDICE]["args"]))
        registrados[NOME_DO_MCP_DO_INDICE] = {"command": "node",
                                              "args": ["meu.js"]}
        gravar_configuracao_json(raiz / ARQUIVO_DE_DECLARACAO_DE_MCP,
                                 {CHAVE_DOS_SERVIDORES_MCP: registrados})
        with contextlib.redirect_stdout(silencio):
            registrar_mcp_do_indice(raiz)
        caso(CASO_INDICE_DO_DONO_NAO_E_SOBRESCRITO,
             servidores_mcp_declarados(raiz)[NOME_DO_MCP_DO_INDICE]
             == {"command": "node", "args": ["meu.js"]})
        caso(CASO_INDICE_NO_WINDOWS_PASSA_PELO_CMD,
             servidor_mcp_do_indice(windows=True)["command"] == "cmd"
             and servidor_mcp_do_indice(windows=True)["args"][:2]
             == ["/c", "npx"]
             and servidor_mcp_do_indice(windows=False)["command"] == "npx")

        (raiz / PASTA_DOS_VIZINHOS_INDEXAVEIS / "vizinho"
         / PASTA_DO_GIT).mkdir(parents=True)
        (raiz / PASTA_DOS_VIZINHOS_INDEXAVEIS / "pasta-comum").mkdir()
        (raiz / "conhecimento").mkdir(exist_ok=True)
        dito = io.StringIO()
        with contextlib.redirect_stdout(dito):
            semear_alvos_do_indice(raiz)
        semeado = json.loads(
            (raiz / ARQUIVO_DOS_ALVOS_DO_INDICE).read_text(encoding="utf-8"))
        caso(CASO_ALVOS_NASCEM_DESLIGADOS,
             semeado["ligado"] is False
             and "conhecimento" in semeado["alvos"]
             and f"{PASTA_DOS_VIZINHOS_INDEXAVEIS}/vizinho" in semeado["alvos"]
             and all((raiz / alvo).is_dir() for alvo in semeado["alvos"]))
        caso(CASO_ALVOS_NAO_MANDA_RODAR_ATALHO_DA_LOJA,
             "python3" not in dito.getvalue()
             and ARQUIVO_QUE_PROVA_O_MODULO_INDICE
             in dito.getvalue())
        caso(CASO_ALVOS_SO_QUEM_TEM_GIT_PROPRIO,
             f"{PASTA_DOS_VIZINHOS_INDEXAVEIS}/pasta-comum"
             not in semeado["alvos"]
             and "pasta-comum" in dito.getvalue())
        semeado["alvos"] = ["so-o-meu"]
        gravar_configuracao_json(raiz / ARQUIVO_DOS_ALVOS_DO_INDICE, semeado)
        with contextlib.redirect_stdout(silencio):
            semear_alvos_do_indice(raiz)
        caso(CASO_ALVOS_DO_DONO_NAO_SAO_TOCADOS,
             json.loads((raiz / ARQUIVO_DOS_ALVOS_DO_INDICE).read_text(
                 encoding="utf-8"))["alvos"] == ["so-o-meu"])

        (raiz / ARQUIVO_SETTINGS_LOCAL).write_text("{quebrado",
                                                   encoding="utf-8")
        aviso = io.StringIO()
        with contextlib.redirect_stdout(aviso):
            liberar_servidores_mcp_declarados(raiz)
        caso(CASO_JSON_QUEBRADO_AVISA_E_NAO_ESCREVE,
             "AVISO" in aviso.getvalue()
             and (raiz / ARQUIVO_SETTINGS_LOCAL).read_text(
                 encoding="utf-8") == "{quebrado")

    ENDERECO_DO_TESTE = "quem-instala/o-quadro-dele"
    with tempfile.TemporaryDirectory() as pasta:
        raiz = Path(pasta)
        destino = raiz / ARQUIVO_DO_EXECUTOR_LOCAL
        pedido = [BANDEIRA_DO_QUADRO, ENDERECO_DO_TESTE]

        with contextlib.redirect_stdout(io.StringIO()):
            nascer_o_executor(raiz, pedido, enter_em_tudo)
        caso(CASO_SEM_GITIGNORE_NAO_NASCE, not destino.exists())

        gravar_texto_com_quebras_unix(raiz / ARQUIVO_GITIGNORE,
                                      ARQUIVO_DO_EXECUTOR_LOCAL + "\n")
        with contextlib.redirect_stdout(io.StringIO()):
            nascer_o_executor(raiz, pedido, enter_em_tudo)
        caso(CASO_COM_GITIGNORE_NASCE, destino.is_file())

        escrito = (destino.read_text(encoding="utf-8")
                   if destino.is_file() else "")
        caso(CASO_ENDERECO_ENTRA_NO_LUGAR,
             ENDERECO_DO_TESTE in escrito
             and MARCA_DO_ENDERECO_NO_EXEMPLO not in escrito)
        caso(CASO_O_RESTO_SEGUE_POR_PREENCHER, "${" in escrito)

        gravar_texto_com_quebras_unix(destino, TEXTO_QUALQUER_DO_TESTE)
        with contextlib.redirect_stdout(io.StringIO()):
            nascer_o_executor(raiz, pedido, enter_em_tudo)
        caso(CASO_NAO_SOBRESCREVE_O_QUE_JA_EXISTE,
             destino.read_text(encoding="utf-8") == TEXTO_QUALQUER_DO_TESTE)

    with tempfile.TemporaryDirectory() as outra_pasta:
        raiz = Path(outra_pasta)
        gravar_texto_com_quebras_unix(raiz / ARQUIVO_GITIGNORE,
                                      ARQUIVO_DO_EXECUTOR_LOCAL + "\n")
        with contextlib.redirect_stdout(io.StringIO()):
            nascer_o_executor(raiz, [BANDEIRA_DO_QUADRO, "so-um-pedaco"],
                              enter_em_tudo)
        caso(CASO_ENDERECO_TORTO_NAO_NASCE,
             not (raiz / ARQUIVO_DO_EXECUTOR_LOCAL).exists())
        dito = io.StringIO()
        entrada_de_verdade, pergunta_de_verdade = sys.stdin, builtins.input
        sys.stdin = io.StringIO("")
        builtins.input = pergunta_que_nao_podia_sair
        try:
            with contextlib.redirect_stdout(dito):
                nascer_o_executor(raiz, [])
        finally:
            sys.stdin, builtins.input = entrada_de_verdade, pergunta_de_verdade
        nascido = ler_o_executor_do_teste(raiz)
        caso(CASO_SEM_QUEM_RESPONDA_NASCE_COM_OS_PADROES,
             nascido.get("modo") == PADRAO_DO_MODO
             and (nascido.get("branches") or {}).get("padrao_de_trabalho")
             == PADRAO_DA_BRANCH_DE_TRABALHO
             and (nascido.get("branches") or {}).get("integracao")
             == PADRAO_DA_INTEGRACAO
             and MARCA_DO_ENDERECO_NO_EXEMPLO
             in (nascido.get("issues") or {}).get("repositorio", "")
             and CAMPO_DO_ENDERECO_DAS_ISSUES in dito.getvalue())

    caso(CASO_A_BANDEIRA_ACEITA_IGUAL,
         endereco_das_issues_pedido(
             [BANDEIRA_DO_QUADRO + "=" + ENDERECO_DO_TESTE])
         == ENDERECO_DO_TESTE)
    caso(CASO_A_FORMA_DO_ENDERECO_E_MEDIDA,
         tem_forma_de_endereco(ENDERECO_DO_TESTE)
         and not tem_forma_de_endereco("so-um-pedaco")
         and not tem_forma_de_endereco("de/mais/pedacos")
         and not tem_forma_de_endereco("com espaco/no-nome"))

    casos_da_configuracao_perguntada(caso)
    casos_dos_modulos_do_padrao(caso)
    casos_do_leitor_da_pasta(caso)

    if falhas:
        print(RESUMO_DE_FALHA.format(len(falhas), rodados))
        print("\n".join(falhas))
        return 1
    print(RESUMO_DE_SUCESSO.format(rodados))
    return 0


def tem_forma_de_endereco(endereco: str) -> bool:
    partes = endereco.split("/")
    if len(partes) != 2 or not all(partes):
        return False
    return all(letra.isalnum() or letra in LETRAS_QUE_UM_ENDERECO_ACEITA
               for parte in partes for letra in parte)


def endereco_das_issues_pedido(argumentos=None) -> str:
    argumentos = sys.argv if argumentos is None else argumentos
    for posicao, argumento in enumerate(argumentos):
        if argumento == BANDEIRA_DO_QUADRO and posicao + 1 < len(argumentos):
            return argumentos[posicao + 1].strip()
        if argumento.startswith(BANDEIRA_DO_QUADRO_COM_IGUAL):
            return argumento.split("=", 1)[1].strip()
    return ""


def pergunta_do_terminal():
    if not sys.stdin.isatty():
        return None

    def perguntar(rotulo: str, padrao: str) -> str:
        try:
            return input(PERGUNTA_DA_CONFIGURACAO.format(
                rotulo=rotulo, padrao=padrao or SEM_PADRAO)).strip()
        except (EOFError, KeyboardInterrupt):
            return ""
    return perguntar


def saida_do_git(raiz: Path, *argumentos) -> str:
    try:
        feito = subprocess.run(["git", "-C", str(raiz), *argumentos],
                               capture_output=True, text=True,
                               encoding="utf-8", errors="replace",
                               timeout=TETO_DO_GIT_DA_PERGUNTA)
    except (OSError, subprocess.SubprocessError):
        return ""
    return feito.stdout.strip() if feito.returncode == 0 else ""


def endereco_do_remoto(raiz: Path) -> str:
    casado = MOLDE_DO_ENDERECO_NO_REMOTO.search(
        saida_do_git(raiz, "remote", "get-url", "origin"))
    endereco = "/".join(casado.groups()) if casado else ""
    return endereco if tem_forma_de_endereco(endereco) else ""


def integracao_do_remoto(raiz: Path) -> str:
    do_remoto = saida_do_git(raiz, "symbolic-ref", "--short",
                             "refs/remotes/origin/HEAD")
    if do_remoto:
        return do_remoto.split("/", 1)[-1]
    return saida_do_git(raiz, "branch", "--show-current") or PADRAO_DA_INTEGRACAO


def perguntas_da_configuracao(raiz: Path, endereco_pedido: str) -> list:
    return [
        (CAMPO_DO_ENDERECO_DAS_ISSUES, ROTULO_DO_ENDERECO,
         endereco_pedido or endereco_do_remoto(raiz), tem_forma_de_endereco),
        ("modo", ROTULO_DO_MODO, PADRAO_DO_MODO,
         lambda valor: valor in MODOS_DO_EXECUTOR),
        ("branches.padrao_de_trabalho", ROTULO_DO_PADRAO_DA_BRANCH,
         PADRAO_DA_BRANCH_DE_TRABALHO,
         lambda valor: MARCA_DO_NUMERO_NA_BRANCH in valor
         and nome_de_branch_que_o_git_aceita(
             MARCA_LIVRE_NA_BRANCH.sub("x", valor))),
        ("branches.integracao", ROTULO_DA_INTEGRACAO,
         integracao_do_remoto(raiz), nome_de_branch_que_o_git_aceita),
    ]


def nome_de_branch_que_o_git_aceita(nome: str) -> bool:
    try:
        feito = subprocess.run(["git", "check-ref-format", "--branch", nome],
                               capture_output=True,
                               timeout=TETO_DO_GIT_DA_PERGUNTA)
    except (OSError, subprocess.SubprocessError):
        return False
    return feito.returncode == 0


def gravar_campo(dado: dict, campo: str, valor: str) -> None:
    *caminho, chave = campo.split(".")
    for parte in caminho:
        dado = dado.setdefault(parte, {})
    dado[chave] = valor


def preencher_a_configuracao(dado: dict, raiz: Path, endereco: str,
                             perguntar) -> tuple:
    gravados, pendentes = [], []
    for campo, rotulo, padrao, serve in perguntas_da_configuracao(raiz,
                                                                  endereco):
        ja_dito = campo == CAMPO_DO_ENDERECO_DAS_ISSUES and endereco
        resposta = (perguntar(rotulo, padrao)
                    if perguntar and not ja_dito else "")
        valor = resposta or padrao
        if resposta and not serve(resposta):
            print(LOG_RESPOSTA_QUE_NAO_SERVE.format(resposta, campo,
                                                    padrao or SEM_PADRAO))
            valor = padrao
        if valor:
            gravar_campo(dado, campo, valor)
            gravados.append("%s = %s" % (campo, valor))
        else:
            pendentes.append(campo)
    return gravados, pendentes


def o_gitignore_ja_esconde_o_executor(raiz: Path) -> bool:
    caminho = raiz / ARQUIVO_GITIGNORE
    if not caminho.is_file():
        return False
    return ARQUIVO_DO_EXECUTOR_LOCAL in caminho.read_text(encoding="utf-8")


def nascer_o_executor(raiz: Path, argumentos=None, perguntar=None) -> None:
    print(SECAO_DO_ENDERECO_DO_QUADRO)
    destino = raiz / ARQUIVO_DO_EXECUTOR_LOCAL
    if destino.exists():
        print(LOG_EXECUTOR_JA_EXISTE.format(ARQUIVO_DO_EXECUTOR_LOCAL))
        return
    if not o_gitignore_ja_esconde_o_executor(raiz):
        print(LOG_EXECUTOR_SEM_GITIGNORE.format(ARQUIVO_DO_EXECUTOR_LOCAL,
                                                ARQUIVO_GITIGNORE))
        return
    endereco = endereco_das_issues_pedido(argumentos)
    if endereco and not tem_forma_de_endereco(endereco):
        print(LOG_EXECUTOR_ENDERECO_TORTO.format(endereco,
                                                 ARQUIVO_DO_EXECUTOR_LOCAL))
        return
    dado = json.loads(paginas_da_camada()[ARQUIVO_DO_EXEMPLO_DO_EXECUTOR])
    gravados, pendentes = preencher_a_configuracao(
        dado, raiz, endereco, perguntar or pergunta_do_terminal())
    destino.parent.mkdir(parents=True, exist_ok=True)
    gravar_texto_com_quebras_unix(
        destino, json.dumps(dado, ensure_ascii=False, indent=2) + "\n")
    print(LOG_EXECUTOR_NASCEU.format(ARQUIVO_DO_EXECUTOR_LOCAL,
                                     "\n    ".join(gravados)))
    if pendentes:
        print(LOG_EXECUTOR_POR_PREENCHER.format(", ".join(pendentes)))


def montar(raiz: Path) -> int:
    paginas = paginas_da_camada()
    print(LOG_CABECALHO_DA_MONTAGEM.format(raiz, marco_da_camada()))

    print(SECAO_DA_MONTAGEM_CONFIGURACAO)
    for caminho, conteudo in ARQUIVOS.items():
        escrever(raiz / caminho, conteudo, caminho)

    print(SECAO_DA_MONTAGEM_ESQUELETO)
    montar_esqueleto(raiz)

    print(SECAO_DA_MONTAGEM_PAGINAS)
    for caminho, conteudo in paginas.items():
        escrever(raiz / caminho, conteudo, caminho)

    print(SECAO_DA_MONTAGEM_MODULOS)
    montar_modulos(raiz, sobrescrever=False)

    print(SECAO_DA_MONTAGEM_SKILLS.format(ORIGEM_SKILLS, COPIA_SKILLS))
    espelhar_e_relatar(raiz)
    espelhar_regra_de_codigo(raiz)

    registrar_a_instalacao(raiz, NUMERO_DOS_AJUSTES_NA_MONTAGEM - 1)
    garantir_ajustes(raiz, NUMERO_DOS_AJUSTES_NA_MONTAGEM)
    nascer_o_executor(raiz)
    declarar_teto_da_largada_medido(raiz)

    print(LOG_PRONTO)
    return 0


def garantir_ponte_para_o_agente_sem_barra(raiz: Path,
                                           escrevendo: bool) -> None:
    destino = raiz / ARQUIVO_DOS_GANCHOS_DO_AGENTE_SEM_BARRA
    if destino.exists() and ler_json_ou_avisar(destino) == \
            GANCHOS_DO_AGENTE_SEM_BARRA:
        print(LOG_PONTE_SEM_BARRA_EM_DIA.format(
            ARQUIVO_DOS_GANCHOS_DO_AGENTE_SEM_BARRA))
        return
    if not escrevendo:
        print(ENSAIO_DA_PONTE_SEM_BARRA.format(
            ARQUIVO_DOS_GANCHOS_DO_AGENTE_SEM_BARRA, BANDEIRA_CODEX,
            BANDEIRA_ESCREVER))
        return
    destino.parent.mkdir(parents=True, exist_ok=True)
    gravar_configuracao_json(destino, GANCHOS_DO_AGENTE_SEM_BARRA)
    print(LOG_PONTE_SEM_BARRA.format(ARQUIVO_DOS_GANCHOS_DO_AGENTE_SEM_BARRA))
    print(LOG_PONTE_SEM_BARRA_PEDE_CONFIANCA)


def garantir_ponte_para_a_outra_ferramenta(raiz: Path) -> None:
    if not pediram(BANDEIRA_DEVIN):
        return
    arquivo = raiz / ARQUIVO_DOS_GANCHOS_DA_OUTRA
    declarado = {}
    if arquivo.exists():
        try:
            declarado = json.loads(arquivo.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError):
            declarado = {}
    grupos = declarado.setdefault(EVENTO_DA_OUTRA, [])
    da_ponte = [g for grupo in grupos for g in grupo.get("hooks", [])
                if ARQUIVO_DA_PONTE in str(g.get(CHAVE_DO_COMANDO, ""))]
    for gancho in da_ponte:
        gancho[CHAVE_DO_COMANDO] = COMANDO_DA_PONTE
    if not da_ponte:
        grupos.append({"hooks": [{"type": "command",
                                  CHAVE_DO_COMANDO: COMANDO_DA_PONTE}]})
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_text(json.dumps(declarado, ensure_ascii=False, indent=2),
                       encoding="utf-8")

def versao_do_instalador() -> int:
    casa = casa_do_instalador()
    if arquivos_rastreados_na_pasta(casa) is None:
        sys.exit(ERRO_CASA_SEM_GIT.format(casa))
    print(LOG_VERSAO.format(marco_da_camada()))
    return 0


def main() -> int:
    recusar_argumento_desconhecido()

    if pediram(BANDEIRA_TESTAR):
        return testar()

    if pediram(BANDEIRA_VERSAO):
        return versao_do_instalador()

    raiz = Path.cwd()
    if not (raiz / PASTA_DO_GIT).exists():
        sys.exit(ERRO_FORA_DA_RAIZ)

    if pediram(BANDEIRA_MODULOS):
        return listar_modulos(raiz)

    recusar_modulo_desconhecido()

    if pediram(BANDEIRA_VERIFICAR):
        print(LOG_CABECALHO_DA_VERIFICACAO.format(raiz))
        if not e_a_casa_do_desenvolvimento(raiz):
            return verificar_a_camada_instalada(raiz)
        return sincronizar(raiz, escrevendo=False)

    if pediram(BANDEIRA_SINCRONIZAR):
        recusar_sincronizar_fora_de_casa(raiz)
        print(LOG_CABECALHO_DA_SINCRONIZACAO.format(raiz))
        return sincronizar(raiz)

    if pediram(BANDEIRA_ATUALIZAR):
        return atualizar(raiz)

    if pediram(BANDEIRA_CODEX):
        garantir_ponte_para_o_agente_sem_barra(
            raiz, escrevendo=pediram(BANDEIRA_ESCREVER))
        return espelhar_mcp_para_o_agente_sem_barra(
            raiz, escrevendo=pediram(BANDEIRA_ESCREVER))

    if pediram(BANDEIRA_DEVIN) and not pediram(BANDEIRA_ESCREVER):
        print(ENSAIO_DA_PONTE_DO_DEVIN.format(
            ARQUIVO_DOS_GANCHOS_DA_OUTRA, BANDEIRA_DEVIN, BANDEIRA_ESCREVER))
        return 0

    return montar(raiz)


if __name__ == "__main__":
    for canal in (sys.stdin, sys.stdout, sys.stderr):
        if not getattr(canal, "closed", True) and hasattr(canal, "reconfigure"):
            canal.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
