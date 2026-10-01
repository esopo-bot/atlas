import json
import os
import re
import subprocess
import sys
import tempfile
from functools import lru_cache
from pathlib import Path

PROTEGIDAS_EMBUTIDAS = {
    "main", "master", "trunk",
    "develop", "development",
    "homolog", "homologacao", "staging", "stage", "hml", "qa", "uat",
    "release", "prod", "producao", "production",
}
ARQUIVO_DE_BRANCHES_PROTEGIDAS = ".claude/branches-protegidas.txt"
ARQUIVO_CONFIGURACAO = "nucleo/configuracao.json"
CHAVE_DAS_AUTORIZACOES = "autorizacoes"
CHAVE_POR_INCORPORACAO = "branches_por_incorporacao"
MARCA_DE_COMENTARIO = "#"
PASTA_DO_GIT = ".git"

VARIAVEL_DA_RAIZ_DO_PROJETO = "CLAUDE_PROJECT_DIR"
NIVEIS_DO_GANCHO_ATE_A_RAIZ = 2

BANDEIRAS_GLOBAIS_SIMPLES = {"--no-pager", "--paginate", "-p", "--bare",
                             "--literal-pathspecs"}
BANDEIRAS_GLOBAIS_QUE_COMEM_O_TOKEN_SEGUINTE = {
    "-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path",
    "-R", "--repo"}

SEPARADORES_DE_COMANDO = re.compile(r"&&|\|\||;|\||\n|\r|\$\(|`|\)")
SUBSTITUICAO_QUE_A_ASPA_DUPLA_NAO_SEGURA = re.compile(r"\$\(|`")
MARCA_DO_DOCUMENTO_LITERAL = re.compile(r"<<-?[ \t]*(['\"])(\w+)\1")
FIM_DO_CORPO_DO_DOCUMENTO = r"^\t*{}[ \t\r]*$"
ASPA_SIMPLES = "'"
ASPA_DUPLA = '"'
ASPAS = "\"'"
CONTRABARRA = "\\"
ABRE_ASPA_ANSI = "$'"
FECHA_A_ASPA = {ASPA_SIMPLES: ASPA_SIMPLES, ASPA_DUPLA: ASPA_DUPLA,
                ABRE_ASPA_ANSI: ASPA_SIMPLES}
FERRAMENTA_BASH = "Bash"
FERRAMENTA_POWERSHELL = "PowerShell"
CRASE = "`"
CRASE_ESCAPADA = CONTRABARRA + CRASE
NA_ASPA_SIMPLES = "aspa simples"
NA_ASPA_DUPLA = "aspa dupla"
NA_ASPA_ANSI = "aspa $'...'"
NO_TEXTO_LITERAL = "texto literal de várias linhas"
NO_TEXTO_QUE_EXPANDE = "texto de várias linhas que expande"
NO_DOCUMENTO_LITERAL = "corpo do documento literal"
NO_DOCUMENTO_QUE_EXPANDE = "corpo do documento que expande"
ONDE_O_ESCAPE_VALE = (None, NA_ASPA_DUPLA, NA_ASPA_ANSI, NO_TEXTO_QUE_EXPANDE,
                      NO_DOCUMENTO_QUE_EXPANDE)
ONDE_SO_HA_TEXTO = (NA_ASPA_SIMPLES, NA_ASPA_ANSI, NO_TEXTO_LITERAL)
ONDE_SO_HA_DADO = (NO_DOCUMENTO_LITERAL, NO_DOCUMENTO_QUE_EXPANDE)
ONDE_A_CRASE_ESCAPADA_ANINHA = (None, NA_ASPA_DUPLA)
ASPAS_SIMPLES_DO_POWERSHELL = ("'\N{LEFT SINGLE QUOTATION MARK}"
                               "\N{RIGHT SINGLE QUOTATION MARK}"
                               "\N{SINGLE LOW-9 QUOTATION MARK}"
                               "\N{SINGLE HIGH-REVERSED-9 QUOTATION MARK}")
ASPAS_DUPLAS_DO_POWERSHELL = ('"\N{LEFT DOUBLE QUOTATION MARK}'
                              "\N{RIGHT DOUBLE QUOTATION MARK}"
                              "\N{DOUBLE LOW-9 QUOTATION MARK}")
ESCAPE_DO_SHELL = {FERRAMENTA_BASH: CONTRABARRA, FERRAMENTA_POWERSHELL: CRASE}
CONTINUACAO_DE_LINHA_NO_SHELL = {
    FERRAMENTA_BASH: re.compile(r"\\\n"),
    FERRAMENTA_POWERSHELL: re.compile(r"`\r?\n"),
}
O_QUE_A_CONTINUACAO_DEIXA = {FERRAMENTA_BASH: "", FERRAMENTA_POWERSHELL: " "}
ONDE_A_LINHA_CONTINUA = {
    FERRAMENTA_BASH: (None, NA_ASPA_DUPLA, NO_DOCUMENTO_QUE_EXPANDE),
    FERRAMENTA_POWERSHELL: (None,),
}
ASPA_QUE_ABRE_NO_SHELL = {
    FERRAMENTA_BASH: (
        (NA_ASPA_ANSI, re.compile(re.escape(ABRE_ASPA_ANSI))),
        (NA_ASPA_SIMPLES, re.compile(ASPA_SIMPLES)),
        (NA_ASPA_DUPLA, re.compile(ASPA_DUPLA))),
    FERRAMENTA_POWERSHELL: (
        (NO_TEXTO_LITERAL,
         re.compile(rf"@[{ASPAS_SIMPLES_DO_POWERSHELL}][ \t]*(?=\r?\n)")),
        (NO_TEXTO_QUE_EXPANDE,
         re.compile(rf"@[{ASPAS_DUPLAS_DO_POWERSHELL}][ \t]*(?=\r?\n)")),
        (NA_ASPA_SIMPLES, re.compile(f"[{ASPAS_SIMPLES_DO_POWERSHELL}]")),
        (NA_ASPA_DUPLA, re.compile(f"[{ASPAS_DUPLAS_DO_POWERSHELL}]"))),
}
FECHO_DA_ASPA_NO_SHELL = {
    FERRAMENTA_BASH: {
        NA_ASPA_ANSI: re.compile(ASPA_SIMPLES),
        NA_ASPA_SIMPLES: re.compile(ASPA_SIMPLES),
        NA_ASPA_DUPLA: re.compile(ASPA_DUPLA)},
    FERRAMENTA_POWERSHELL: {
        NO_TEXTO_LITERAL: re.compile(rf"\n[{ASPAS_SIMPLES_DO_POWERSHELL}]@"),
        NO_TEXTO_QUE_EXPANDE:
            re.compile(rf"\n[{ASPAS_DUPLAS_DO_POWERSHELL}]@"),
        NA_ASPA_SIMPLES: re.compile(f"[{ASPAS_SIMPLES_DO_POWERSHELL}]"),
        NA_ASPA_DUPLA: re.compile(f"[{ASPAS_DUPLAS_DO_POWERSHELL}]")},
}
SUBSTITUICAO_QUE_ABRE_NO_SHELL = {
    FERRAMENTA_BASH: {
        None: (("$(", ")"), ("(", ")"), (CRASE, CRASE)),
        NA_ASPA_DUPLA: (("$(", ")"), (CRASE, CRASE)),
        NO_DOCUMENTO_QUE_EXPANDE: (("$(", ")"), (CRASE, CRASE))},
    FERRAMENTA_POWERSHELL: {
        None: (("$(", ")"), ("(", ")"), ("{", "}")),
        NA_ASPA_DUPLA: (("$(", ")"),),
        NO_TEXTO_QUE_EXPANDE: (("$(", ")"),)},
}
CORTE_NO_CODIGO_DO_SHELL = {
    FERRAMENTA_BASH: re.compile(r"&&|\|\||\|&|;|\||&|\n|\r|\)|\{(?=\s)"),
    FERRAMENTA_POWERSHELL: re.compile(r"&&|\|\||;|\||&|\n|\r|\)|\}"),
}
QUEBRAS_DE_LINHA = ("\n", "\r")
CORTE_QUANDO_A_LEITURA_NAO_FECHA = {
    FERRAMENTA_BASH: re.compile(r"&&|\|\||;|\||&|\n|\r|\$\(|\(|`|\)"),
    FERRAMENTA_POWERSHELL: re.compile(
        r"&&|\|\||;|\||&|\n|\r|\$\(|\(|\)|\{|\}"),
}
DOCUMENTO_QUE_ABRE_NO_SHELL = {FERRAMENTA_BASH: re.compile(
    r"<<(?!<)(-?)[ \t]*((?:'[^'\n]*'|\"[^\"\n]*\"|\\.|[^\s;&|<>()'\"\\])+)")}
CADEIA_QUE_NAO_ABRE_DOCUMENTO = {FERRAMENTA_BASH: re.compile(r"<<<")}
MARCAS_QUE_TORNAM_O_DOCUMENTO_LITERAL = "'\"\\"
FECHO_DO_DOCUMENTO = r"\n{}{}[ \t\r]*(?=\n|\Z)"
TABULACOES_QUE_O_MENOS_TIRA = r"\t*"
SHELL_QUE_LE_O_DOCUMENTO = re.compile(
    r"(?<![\w.-])(?:sh|bash|zsh|dash|ksh)(?:\.exe)?(?![\w.-])", re.I)
PREFIXOS_ANTES_DO_PROGRAMA = ("sudo", "env", "exec", "command", "nohup",
                              "nice", "time", "xargs", "builtin")
LETRA_DE_OPCAO_NO_SHELL = "-"
MARCA_DE_ATRIBUICAO_NO_SHELL = "="
CANO_UNICO = "|"
CANO_COM_O_ERRO = "|&"
CANOS = (CANO_UNICO, CANO_COM_O_ERRO)
PROGRAMA_QUE_DEVOLVE_O_DOCUMENTO = "cat"
AVALIADORES_DO_SHELL = ("eval", "iex", "invoke-expression")
LEITORES_DE_ARQUIVO_NO_SHELL = ("source", ".")
ABRE_A_SUBSTITUICAO_DE_PROCESSO = "<"
LEITOR_DO_TEXTO_QUE_A_SUBSTITUICAO_DEVOLVE = {
    FERRAMENTA_BASH: "eval", FERRAMENTA_POWERSHELL: "iex"}
LETRA_QUE_ENTREGA_O_CODIGO_AO_SHELL = "c"
TEXTO_ENTRE_ASPAS_NO_SEGMENTO = re.compile(
    r"'[^']*(?:'|$)|\"(?:\\.|[^\"\\])*(?:\"|$)")
COMENTARIO_NO_SHELL = {
    FERRAMENTA_BASH: re.compile(r"(?<![^\s;&|()<>])#[^\n]*"),
    FERRAMENTA_POWERSHELL: re.compile(
        r"<#.*?#>|(?<![^\s;&|(){}])#[^\n]*", re.S),
}
PALAVRA_QUE_ABRE_O_COMANDO_NO_SHELL = {FERRAMENTA_BASH: re.compile(
    r"(?:!|\}|do|done|then|else|elif|fi|if|while|until|time|coproc)"
    r"(?=[\s;&|()]|\Z)")}
ESPACOS_ENTRE_PALAVRAS = " \t\r\n"
CAMINHO_DO_WINDOWS_NA_PALAVRA = re.compile(r"[A-Za-z]:\\|^\\\\|^\.{1,2}\\")
O_QUE_A_CONTRABARRA_ESCAPA_NA_ASPA_DUPLA = "$`\"\\\n"
CODIGOS_DOS_ESCAPES_DA_ASPA_ANSI = {"n": 10, "t": 9, "r": 13, "a": 7,
                                    "b": 8, "e": 27, "E": 27, "f": 12,
                                    "v": 11}
CODIGOS_DOS_ESCAPES_DO_POWERSHELL = {"0": 0, "a": 7, "b": 8, "e": 27,
                                     "f": 12, "n": 10, "r": 13, "t": 9,
                                     "v": 11}
ESCAPE_NUMERICO_DA_ASPA_ANSI = re.compile(r"x([0-9A-Fa-f]{1,2})|([0-7]{1,3})")
BASE_HEXADECIMAL = 16
BASE_OCTAL = 8
PROGRAMAS_QUE_SO_MUDAM_DE_PASTA = ("cd", "pushd", "popd")
CARACTERE_QUE_PEDE_ASPA = re.compile(r"[\s'\"\\`$;&|<>(){}#*?\[\]~]")

VERBO_PUSH = "push"
VERBO_BRANCH = "branch"
VERBOS_QUE_MEXEM_EM_BRANCH = {VERBO_PUSH, VERBO_BRANCH}
BANDEIRAS_DE_APAGAR = {"-d", "--delete"}
BANDEIRAS_DE_RENOMEAR = {"-m", "--move"}
BANDEIRAS_DE_FORCA = {"-f", "--force"}
BANDEIRAS_DE_FORCA_COM_RESSALVA = ("--force-with-lease", "--force-if-includes")
BANDEIRA_DE_ESPELHO = "--mirror"
LETRAS_QUE_LEVAM_VALOR_NO_VERBO = {VERBO_PUSH: "o", VERBO_BRANCH: "u"}
PREFIXO_DE_APAGAR_POR_REFSPEC = ":"
PREFIXO_DE_FORCAR_POR_REFSPEC = "+"
ACAO_APAGAR = "apagar"
ACAO_RENOMEAR = "renomear"
ACAO_COMMIT = "commit"
ACAO_PUSH = "push"
ACAO_PUBLICAR = "publicar"
ACAO_MESCLAR = "mesclar"
VERBO_COMMIT = "commit"
BANDEIRAS_DO_COMMIT_QUE_NAO_GRAVAM = {"--dry-run", "--help", "-h"}
OPCOES_DO_COMMIT_QUE_COMEM_O_SEGUINTE = {
    "-m", "--message", "-F", "--file", "-C", "--reuse-message", "-c",
    "--reedit-message", "-t", "--template", "--author", "--date",
    "--cleanup", "--trailer", "--fixup", "--squash", "--pathspec-from-file"}
LETRAS_DO_COMMIT_QUE_COMEM_O_SEGUINTE = "mFCct"
VERBO_MERGE = "merge"
VERBO_PULL = "pull"
VERBOS_QUE_PODEM_MESCLAR = {VERBO_MERGE, VERBO_PULL}
BANDEIRA_QUE_NAO_CRIA_COMMIT = "--ff-only"
MARCAS_QUE_SO_O_SHELL_USA = "<>&|"
VERBO_INIT = "init"
VERBO_CHECKOUT = "checkout"
VERBO_SWITCH = "switch"
VERBOS_QUE_TROCAM_DE_BRANCH = {VERBO_CHECKOUT, VERBO_SWITCH}
BANDEIRAS_QUE_CRIAM_BRANCH = {"-b", "-c"}
FIM_DAS_BANDEIRAS = "--"
SEPARADOR_QUE_ENCADEIA = "&&"
COMANDO_DAS_BRANCHES = ["git", "for-each-ref", "--format=%(refname:short)",
                        "refs/heads/"]

NOMES_DO_GIT = {"git", "git.exe"}
BANDEIRA_DA_PASTA = "-C"
NOME_DO_GH = "gh"
EXTENSAO_EXE = ".exe"
PROGRAMAS_QUE_ACIONAM = ("git", "gh")
PREFIXOS_TRANSPARENTES = ("command", "builtin", "exec", "sudo", "nohup",
                          "time", "env", "timeout", "nice", "stdbuf")
PREFIXO_COM_ARGUMENTO_PROPRIO = "timeout"
OPCOES_DE_PREFIXO_QUE_COMEM_O_SEGUINTE = ("-n", "-u", "-s", "-k", "-o",
                                          "-C")
ATRIBUICAO_DE_AMBIENTE = re.compile(r"^[A-Za-z_]\w*=")
MODULO_QUE_DESEMBRULHA = "desembrulhar-comando.py"
CACHE_DO_DESEMBRULHADOR = []
COMANDO_CD = "cd"
COMANDO_DA_BRANCH_ATUAL = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
TEMPO_LIMITE_DO_GIT = 5
HEAD_SOLTA = "head"
PREFIXO_DE_REFS_DE_BRANCH = re.compile(r"^refs/heads/")

SUBVERBOS_QUE_SO_PEDEM = {
    "pr": frozenset({"create", "new", "view", "list", "ls", "status", "diff",
                     "checks", "comment", "edit", "ready", "checkout", "co",
                     "close", "reopen", "review", "lock", "unlock"}),
    "release": frozenset({"view", "list", "ls", "download", "verify",
                          "verify-asset"}),
}
SEM_SUBVERBO = ""
SUBVERBOS_QUE_EMPURRAM = {"pr": frozenset({"update-branch", "revert"})}
BANDEIRAS_DE_AJUDA_DO_GH = frozenset({"--help", "-h"})
BANDEIRA_DO_REBASE_PELO_SERVIDOR = "--rebase"
VERBOS_POR_ACAO = {
    ACAO_COMMIT: (VERBO_COMMIT,),
    ACAO_PUSH: (VERBO_PUSH,),
    ACAO_PUBLICAR: ("pr", "release"),
}
OMISSAO_NAO_E_PERMISSAO = {ACAO_COMMIT: False, ACAO_PUSH: False,
                           ACAO_MESCLAR: False}
VERBO_DO_PEDIDO = "pr"
INDICE_DO_VERBO_SEM_BANDEIRA_ANTES = 1
BANDEIRAS_DA_MESCLA_DA_CASA = frozenset({"--merge"})
VARIAVEIS_QUE_TROCAM_O_REPOSITORIO_DO_GH = ("gh_repo", "gh_host")

VERBO_DA_API = "api"
METODO_QUE_SO_LE = "GET"
METODO_QUANDO_HA_CAMPO = "POST"
OPCOES_DO_METODO_DA_API = frozenset({"-X", "--method"})
OPCOES_DE_CAMPO_DA_API = frozenset({"-f", "-F", "--field", "--raw-field",
                                    "--input"})
LETRAS_DA_API_QUE_LEVAM_VALOR = "XfFHqtp"
OPCOES_LONGAS_DA_API_QUE_LEVAM_VALOR = frozenset({
    "--method", "--field", "--raw-field", "--header", "--input", "--jq",
    "--template", "--hostname", "--cache", "--preview"})
PREFIXO_DO_ENDERECO_DA_API = r"^/?(?:https?://[^/]+/(?:api/v3/)?)?"
FIM_DO_ENDERECO_DA_API = r"/?$"
CONSULTA_OU_FRAGMENTO_DO_ENDERECO = re.compile(r"[?#]")
ENDERECO_DA_MESCLA_PELA_API = re.compile(
    PREFIXO_DO_ENDERECO_DA_API + r"repos/[^/]+/[^/]+/pulls/[^/]+/merge"
    + FIM_DO_ENDERECO_DA_API, re.I)
ENDERECO_DA_RELEASE_PELA_API = re.compile(
    PREFIXO_DO_ENDERECO_DA_API + r"repos/[^/]+/[^/]+/releases(?:/.*)?"
    + FIM_DO_ENDERECO_DA_API, re.I)
ENDERECO_DAS_NOTAS_DA_RELEASE = re.compile(
    PREFIXO_DO_ENDERECO_DA_API + r"repos/[^/]+/[^/]+/releases/generate-notes"
    + FIM_DO_ENDERECO_DA_API, re.I)
ENDERECO_DO_GRAPHQL = re.compile(
    r"^/?(?:https?://[^/]+/(?:api/)?)?graphql" + FIM_DO_ENDERECO_DA_API, re.I)
MUTACOES_QUE_PUBLICAM = ("mergepullrequest", "enablepullrequestautomerge")

MARCA_DO_GIT = "git"
MARCA_DO_GH = "gh "
MARCA_DO_GH_DO_WINDOWS = NOME_DO_GH + EXTENSAO_EXE
MARCAS_DO_GIT_E_DO_GH = (MARCA_DO_GIT, MARCA_DO_GH, MARCA_DO_GH_DO_WINDOWS)
ESCAPE_E_ASPA_QUE_O_SHELL_TIRA = re.compile(
    r"\\\n|`\r?\n|[" + re.escape(CONTRABARRA + CRASE
                                 + ASPAS_SIMPLES_DO_POWERSHELL
                                 + ASPAS_DUPLAS_DO_POWERSHELL) + "]")
EVENTO_ANTES_DA_FERRAMENTA = "PreToolUse"
DECISAO_DE_NEGAR = "deny"
BANDEIRA_DE_TESTE = "--testar"
SEM_ACAO = ""
SEM_VERBO = -1
SEM_RECUSA = ""
SILENCIO = 0
MARCADORES_DE_EXPANSAO = ("$", "`", "%")
RECUSA_SEM_MEDIR_O_ALVO = (
    "Este gancho ia recusar, mas não sabe qual repositório o comando toca: o "
    "alvo é {!r}, e o gancho recebe o texto cru, sem expansão. Julgar pela "
    "raiz da sessão daria uma razão inventada — e razão inventada manda quem "
    "lê procurar o problema no lugar errado. Passe o caminho literal no lugar "
    "da expansão e refaça o comando; o veto volta a julgar o repositório certo."
)
RECUSA_SEM_ENTENDER = (
    "Este gancho não entendeu o pedido, e por isso recusa em vez de liberar: "
    "{} — {}. Quem veta e não consegue julgar não pode dizer sim: a parede "
    "sumiria em silêncio, e o verde passaria a significar `ninguém olhou`. "
    "Se o pedido é legítimo, conserte o gancho ou desligue-o em "
    ".claude/settings.json — o caminho nunca é atravessar por aqui."
)

MOTIVO_BRANCH_PROTEGIDA = "{} a branch protegida '{}'"
MOTIVO_GRAVA_EM_PROTEGIDA = (
    "{} direto na branch '{}', que este repositório declarou de "
    "incorporação — o controle é o pedido de "
    "incorporação, não a gravação. Abra uma branch de trabalho, "
    "entregue nela e peça a incorporação. Autorização declarada não "
    "vale para branch de longa duração.")
MOTIVO_ESPELHO = ("reescrever todas as refs do remoto de uma vez (--mirror), "
                  "as protegidas inclusive")
MOTIVO_APAGAR_POR_REFSPEC = (
    "apagar a branch protegida '{}' (refspec com dois-pontos)")
MOTIVO_FORCAR_POR_REFSPEC = (
    "reescrever a branch protegida '{}' (refspec com mais)")
MOTIVO_REESCREVER_HISTORIA = (
    "reescrever a história da branch protegida '{}'")
MOTIVO_REESCREVER_A_BRANCH_ATUAL = (
    "reescrever a história de '{}', a branch atual e protegida")
MOTIVO_SEM_AUTORIZACAO = (
    "{} sem autorização declarada — `autorizacoes.{}` não está ligado em {}")
MARCA_DA_RECUSA_POR_AUTORIZACAO = "sem autorização declarada"
MARCA_DA_RECUSA_PELO_CADASTRO = "declara como integração ou base"
MOTIVO_COMMIT_NA_INTEGRACAO = (
    "commit direto na branch '{}', que `nucleo/executor.json` "
    + MARCA_DA_RECUSA_PELO_CADASTRO + " deste repositório "
    "(`projetos.<nome>.branches`, ou o bloco `branches` da raiz para quem "
    "não declara)")

MANDA_GRAVAR = (
    "\nGrave o aprendizado antes de tentar de novo — regra 4, a memória "
    "mora no disco, e recusa que a próxima sessão repete não ensinou "
    "nada. A linha, em `conhecimento/`:\n"
    "    {}"
)
APRENDIZADO_DA_AUTORIZACAO = (
    "o que a automação faz sozinha se declara em `nucleo/configuracao.json`, "
    "campo `autorizacoes` — omissão não é permissão."
)
APRENDIZADO_DA_BRANCH = (
    "branch de longa duração não se reescreve nem se apaga daqui: trabalhe "
    "na sua branch e peça a promoção ao dono."
)
RECUSA_POR_AUTORIZACAO = (
    "Regra 9 da camada: isto quer {}. O que a automação faz sozinha se "
    "declara — ligue a chave em `nucleo/configuracao.json`, campo "
    "`autorizacoes`, ou peça ao dono que rode o comando. Omissão não é "
    "permissão."
)
RECUSA_POR_BRANCH_PROTEGIDA = (
    "Regra 12 da camada: isto quer {}. Branch de longa duração é "
    "infraestrutura de outras pessoas — desfazer é público e caro. O "
    "caminho: trabalhe na sua branch e peça a promoção ao dono, que roda o "
    "comando ele mesmo. Se esta branch não deveria estar protegida, tire o "
    "nome de .claude/branches-protegidas.txt."
)
RECUSA_POR_COMMIT_NA_INTEGRACAO = (
    "Regra 12 da camada: isto quer {}. A integração, da raiz ou de um "
    "vizinho, recebe o trabalho pela mescla `git merge --no-ff` de uma "
    "branch de trabalho, nunca por commit direto. O caminho: crie a branch "
    "de trabalho com o nome que `branches.padrao_de_trabalho` de "
    "`nucleo/executor.json` monta, a partir da base declarada, commite nela "
    "e mescle na integração com `--no-ff`; a mescla que parou em conflito se "
    "conclui com `git merge --continue`. Se a integração declarada está "
    "errada, corrija o cadastro em `nucleo/executor.json`."
)
APRENDIZADO_DA_INTEGRACAO = (
    "a integração, da raiz ou de vizinho, recebe trabalho pela mescla "
    "`--no-ff` de uma branch de trabalho; commit direto nela é recusado "
    "pelo que `nucleo/executor.json` declara."
)
MOTIVO_PUBLICAR = (
    "publicar — criar ou mudar release, ou mesclar pedido de incorporação "
    "fora da forma `gh pr merge <número> --merge` rodada da pasta do "
    "repositório")
RECUSA_POR_PUBLICAR = (
    "Regra 9 da camada: isto quer {}. Publicar é do dono, sempre: release, "
    "mescla que contorna a aprovação (`--admin`, `--auto`), que apaga a "
    "branch de cabeça, que vai pela API ou que troca de repositório (`-R`, "
    "`GH_REPO`) não se liberam por chave, porque publicação não se desfaz. O "
    "caminho: deixe o pedido de incorporação aberto, diga ao dono o que "
    "espera por ele e pare. Onde a raiz declara "
    "`autorizacoes.mesclar`, a sessão mescla o que o dono aprovou só pela "
    "forma `gh pr merge <número> --merge`, rodada da pasta dela."
)
MOTIVO_MESCLA_COM_OUTRO_REMOTO = (
    "publicar — mesclar de uma pasta com remoto além do `origin`, onde o gh "
    "pode escolher outro repositório")
TRECHO_DA_CHAVE_DA_MESCLA = "`autorizacoes.mesclar`"
RECUSA_POR_MESCLA_SEM_CHAVE = (
    "Regra 9 da camada: isto quer {}. Ligar " + TRECHO_DA_CHAVE_DA_MESCLA
    + " é decisão do dono, não da sessão, e ela só vale na raiz do "
    "workspace. O caminho: deixe o pedido aprovado aberto, diga ao dono que "
    "ele espera a mescla e pare."
)
APRENDIZADO_DA_MESCLA = (
    "a sessão mescla o pedido aprovado só onde a raiz declara "
    + TRECHO_DA_CHAVE_DA_MESCLA + ", e só pela forma `gh pr merge <número> "
    "--merge`, da pasta do repositório; ligar a chave é do dono."
)
APRENDIZADO_DE_PUBLICAR = (
    "publicar é do dono, sempre: release e mescla fora da forma da casa não "
    "se liberam por chave; a mescla da casa segue `autorizacoes.mesclar` e a "
    "aprovação que o servidor exige."
)
MOTIVO_REBASE_PELO_SERVIDOR = (
    "reescrever pelo servidor a história da branch de cabeça do pedido "
    "(`gh pr update-branch --rebase`)")
RECUSA_POR_REBASE_PELO_SERVIDOR = (
    "Regra 12 da camada: isto quer {}. O gancho não vê qual é a branch de "
    "cabeça do pedido, e ela pode ser uma branch de longa duração — "
    "reescrevê-la pelo servidor é público e caro de desfazer. O caminho: "
    "atualize sem reescrever, com `gh pr update-branch` sem `--rebase`, que "
    "mescla a base na cabeça; o rebase, se precisar, se faz na sua branch de "
    "trabalho, localmente."
)
APRENDIZADO_DO_REBASE_PELO_SERVIDOR = (
    "o rebase pelo servidor (`gh pr update-branch --rebase`) reescreve a "
    "branch de cabeça do pedido sem que o gancho veja qual é; a atualização "
    "vai pela mescla, sem `--rebase`."
)

FALHA_DEVIA_BARRAR = "  DEVIA BARRAR e passou — {}: {}"
FALHA_DEVIA_PASSAR = "  DEVIA PASSAR e barrou — {}: {} ({})"
FALHA_DEVIA_BARRAR_SEM_AUTORIZACAO = (
    "  DEVIA BARRAR sem autorização e passou — {}")
FALHA_DEVIA_PASSAR_COM_AUTORIZACAO = (
    "  DEVIA PASSAR com autorização e barrou — {}")
FALHA_RECUSA_NAO_ENSINA = "  a recusa não ensina — {}"
FALHA_FORCA_MESMO_AUTORIZADO = (
    "  DEVIA BARRAR: força em protegida, mesmo autorizado")
RESUMO_FALHOU = "FALHOU: {} de {} casos"
RESUMO_OK = "OK: {} casos — {} barrados, {} liberados"


def shell_da_ferramenta(ferramenta) -> str:
    return (ferramenta if ferramenta in ESCAPE_DO_SHELL
            else FERRAMENTA_BASH)


def tamanho_do_casado(padrao, comando: str, i: int) -> int:
    achado = padrao.match(comando, i) if padrao else None
    return achado.end() - i if achado else 0


def aspa_que_abre(comando: str, i: int, shell: str):
    for aspa, abertura in ASPA_QUE_ABRE_NO_SHELL[shell]:
        if achada := abertura.match(comando, i):
            return aspa, achada.end() - i
    return None


def tamanho_do_fecho_da_aspa(comando: str, i: int, aspa_aberta, shell: str,
                             fecho_do_documento=None) -> int:
    fecho = (fecho_do_documento if aspa_aberta in ONDE_SO_HA_DADO
             else FECHO_DA_ASPA_NO_SHELL[shell].get(aspa_aberta))
    return tamanho_do_casado(fecho, comando, i)


def substituicao_que_abre(comando: str, i: int, aspa_aberta, shell: str):
    for abertura, fecho in SUBSTITUICAO_QUE_ABRE_NO_SHELL[shell].get(
            aspa_aberta, ()):
        if comando.startswith(abertura, i):
            return abertura, fecho
    return None


def tamanho_da_continuacao_de_linha(comando: str, i: int, aspa_aberta,
                                    shell: str) -> int:
    if aspa_aberta not in ONDE_A_LINHA_CONTINUA[shell]:
        return 0
    return tamanho_do_casado(CONTINUACAO_DE_LINHA_NO_SHELL[shell], comando, i)


def documento_que_abre(comando: str, i: int, shell: str):
    if cadeia := tamanho_do_casado(CADEIA_QUE_NAO_ABRE_DOCUMENTO.get(shell),
                                   comando, i):
        return cadeia, None
    abertura = DOCUMENTO_QUE_ABRE_NO_SHELL.get(shell)
    achado = abertura.match(comando, i) if abertura else None
    if not achado:
        return None
    menos, palavra = achado.groups()
    delimitador = "".join(letra for letra in palavra if letra
                          not in MARCAS_QUE_TORNAM_O_DOCUMENTO_LITERAL)
    fecho = re.compile(FECHO_DO_DOCUMENTO.format(
        TABULACOES_QUE_O_MENOS_TIRA if menos else "",
        re.escape(delimitador)))
    corpo = (NO_DOCUMENTO_LITERAL if delimitador != palavra
             else NO_DOCUMENTO_QUE_EXPANDE)
    return achado.end() - i, (corpo, fecho)


def nome_do_programa_no_shell(token: str) -> str:
    return Path(sem_o_par_de_aspas_que_envolve(token).replace(
        CONTRABARRA, "/")).name


def programa_do_segmento(segmento: str) -> str:
    palavras = [lida for _, lida in palavras_como_o_shell_le(
        segmento, FERRAMENTA_BASH)]
    while palavras and (
            palavras[0].startswith(LETRA_DE_OPCAO_NO_SHELL)
            or MARCA_DE_ATRIBUICAO_NO_SHELL in palavras[0]
            or nome_do_programa_no_shell(palavras[0])
            in PREFIXOS_ANTES_DO_PROGRAMA):
        palavras.pop(0)
    return nome_do_programa_no_shell(palavras[0]) if palavras else ""


def o_documento_e_lido_por_um_shell(segmentos_da_linha: list) -> bool:
    return any(SHELL_QUE_LE_O_DOCUMENTO.fullmatch(programa_do_segmento(s))
               for s in segmentos_da_linha)


def entrega_o_codigo_ao_shell(opcao: str) -> bool:
    return (opcao.startswith(LETRA_DE_OPCAO_NO_SHELL)
            and not opcao.startswith(LETRA_DE_OPCAO_NO_SHELL * 2)
            and LETRA_QUE_ENTREGA_O_CODIGO_AO_SHELL in opcao[1:])


def a_substituicao_e_o_codigo_de_um_shell(antes: str, aspa_aberta) -> bool:
    fechado = antes + (ASPA_DUPLA if aspa_aberta == NA_ASPA_DUPLA else "")
    palavras = [lida for _, lida in palavras_como_o_shell_le(
        fechado, FERRAMENTA_BASH)]
    abre_palavra_nova = aspa_aberta is None and (
        not antes or antes[-1] in ESPACOS_ENTRE_PALAVRAS)
    anteriores = palavras if abre_palavra_nova else palavras[:-1]
    if not anteriores:
        return False
    programa = programa_do_segmento(fechado) or anteriores[0]
    le_o_arquivo_que_a_substituicao_abre = (
        aspa_aberta is None
        and antes.endswith(ABRE_A_SUBSTITUICAO_DE_PROCESSO)
        and (bool(SHELL_QUE_LE_O_DOCUMENTO.fullmatch(programa))
             or programa in LEITORES_DE_ARQUIVO_NO_SHELL))
    return (programa.lower() in AVALIADORES_DO_SHELL
            or le_o_arquivo_que_a_substituicao_abre or bool(
                SHELL_QUE_LE_O_DOCUMENTO.fullmatch(programa)
                and entrega_o_codigo_ao_shell(anteriores[-1])))


def o_documento_e_o_codigo_da_substituicao(segmentos: list,
                                           pilha: list) -> bool:
    codigo_desde = pilha[-1][-1] if pilha else None
    if codigo_desde is None:
        return False
    conteudo = [s for s in segmentos[codigo_desde:] if s.strip()]
    return len(conteudo) == 1 and (programa_do_segmento(conteudo[0])
                                   == PROGRAMA_QUE_DEVOLVE_O_DOCUMENTO)


def tamanho_da_palavra_que_abre_o_comando(comando: str, i: int, atual: list,
                                          shell: str) -> int:
    if "".join(atual).strip():
        return 0
    return tamanho_do_casado(PALAVRA_QUE_ABRE_O_COMANDO_NO_SHELL.get(shell),
                             comando, i)


def cortar_respeitando_aspas(comando: str,
                             ferramenta: str = FERRAMENTA_BASH):
    shell = shell_da_ferramenta(ferramenta)
    segmentos, atual, aspa_aberta, pilha = [], [], None, []
    apos_cano, cano_pendente = [], False
    pendentes, fecho_do_documento, inicio_da_linha = [], None, 0
    i = 0
    while i < len(comando):
        c = comando[i]
        fecha_a_substituicao = (aspa_aberta is None and pilha
                                and comando.startswith(pilha[-1][0], i))
        if (aspa_aberta in ONDE_A_CRASE_ESCAPADA_ANINHA
                and comando.startswith(CRASE_ESCAPADA, i)
                and any(aberta[0] == CRASE for aberta in pilha)):
            segmentos.append("".join(atual))
            apos_cano.append(cano_pendente)
            cano_pendente = False
            atual = []
            i += len(CRASE_ESCAPADA)
        elif continuacao := tamanho_da_continuacao_de_linha(
                comando, i, aspa_aberta, shell):
            atual.append(O_QUE_A_CONTINUACAO_DEIXA[shell])
            i += continuacao
        elif c == ESCAPE_DO_SHELL[shell] and aspa_aberta in ONDE_O_ESCAPE_VALE:
            if aspa_aberta not in ONDE_SO_HA_DADO:
                atual.append(comando[i:i + 2])
            i += 2
        elif tamanho := tamanho_do_fecho_da_aspa(
                comando, i, aspa_aberta, shell, fecho_do_documento):
            if aspa_aberta in ONDE_SO_HA_DADO:
                aspa_aberta, fecho_do_documento = (
                    pendentes.pop(0) if pendentes else (None, None))
            else:
                atual.append(comando[i:i + tamanho])
                aspa_aberta = None
            i += tamanho
        elif aspa_aberta in ONDE_SO_HA_TEXTO:
            atual.append(c)
            i += 1
        elif fecha_a_substituicao:
            fecho, aspa_aberta, fecho_do_documento, codigo_desde = (
                pilha.pop())
            segmentos.append("".join(atual))
            apos_cano.append(cano_pendente)
            cano_pendente = False
            atual = []
            i += len(fecho)
            if codigo_desde is not None:
                segmentos.append(
                    LEITOR_DO_TEXTO_QUE_A_SUBSTITUICAO_DEVOLVE[shell])
                apos_cano.append(True)
        elif abertura := substituicao_que_abre(comando, i, aspa_aberta,
                                               shell):
            segmentos.append("".join(atual))
            codigo_desde = (len(segmentos)
                            if a_substituicao_e_o_codigo_de_um_shell(
                                segmentos[-1], aspa_aberta) else None)
            pilha.append((abertura[1], aspa_aberta, fecho_do_documento,
                          codigo_desde))
            aspa_aberta = None
            apos_cano.append(cano_pendente)
            cano_pendente = False
            atual = []
            i += len(abertura[0])
        elif aspa_aberta in ONDE_SO_HA_DADO:
            i += 1
        elif aspa_aberta is None and (
                documento := documento_que_abre(comando, i, shell)):
            tamanho, pendente = documento
            atual.append(comando[i:i + tamanho])
            pendentes += [pendente] if pendente else []
            i += tamanho
        elif aspa_aberta is None and (comentario := tamanho_do_casado(
                COMENTARIO_NO_SHELL[shell], comando, i)):
            i += comentario
        elif aspa_aberta is None and (
                palavra := tamanho_da_palavra_que_abre_o_comando(
                    comando, i, atual, shell)):
            i += palavra
        elif aspa_aberta is None and (aspa := aspa_que_abre(comando, i,
                                                            shell)):
            atual.append(comando[i:i + aspa[1]])
            aspa_aberta = aspa[0]
            i += aspa[1]
        elif aspa_aberta is None and (
                corte := CORTE_NO_CODIGO_DO_SHELL[shell].match(comando, i)):
            segmentos.append("".join(atual))
            apos_cano.append(cano_pendente)
            cano_pendente = corte.group() in CANOS
            atual = []
            i = corte.end()
            if corte.group() not in QUEBRAS_DE_LINHA:
                continue
            if pendentes and (
                    o_documento_e_lido_por_um_shell(
                        segmentos[inicio_da_linha:])
                    or o_documento_e_o_codigo_da_substituicao(segmentos,
                                                              pilha)):
                pendentes = []
            elif pendentes:
                aspa_aberta, fecho_do_documento = pendentes.pop(0)
                i = corte.start()
            inicio_da_linha = len(segmentos)
        else:
            atual.append(c)
            i += 1
    if pilha or (aspa_aberta is not None and aspa_aberta not in ONDE_SO_HA_DADO):
        return None
    segmentos.append("".join(atual))
    apos_cano.append(cano_pendente)
    return segmentos, apos_cano


def o_que_o_escape_le(segmento: str, i: int, aspa_aberta, shell: str):
    seguinte = segmento[i + 1:i + 2]
    if shell == FERRAMENTA_POWERSHELL:
        codigo = CODIGOS_DOS_ESCAPES_DO_POWERSHELL.get(seguinte)
        return (seguinte if codigo is None else chr(codigo)), 2
    if aspa_aberta == NA_ASPA_ANSI:
        if seguinte in CODIGOS_DOS_ESCAPES_DA_ASPA_ANSI:
            return chr(CODIGOS_DOS_ESCAPES_DA_ASPA_ANSI[seguinte]), 2
        if numero := ESCAPE_NUMERICO_DA_ASPA_ANSI.match(segmento, i + 1):
            hexadecimal, octal = numero.groups()
            codigo = (int(hexadecimal, BASE_HEXADECIMAL) if hexadecimal
                      else int(octal, BASE_OCTAL))
            return chr(codigo), 1 + len(numero.group())
        return seguinte, 2
    if (aspa_aberta is None
            or seguinte in O_QUE_A_CONTRABARRA_ESCAPA_NA_ASPA_DUPLA):
        return seguinte, 2
    return segmento[i:i + 2], 2


def palavras_como_o_shell_le(segmento: str, shell: str):
    palavras, crua, lida, aspa_aberta, i = [], [], [], None, 0
    while i < len(segmento):
        c = segmento[i]
        if aspa_aberta is None and c in ESPACOS_ENTRE_PALAVRAS:
            palavras.append(("".join(crua), "".join(lida)))
            crua, lida = [], []
            i += 1
        elif c == ESCAPE_DO_SHELL[shell] and aspa_aberta in ONDE_O_ESCAPE_VALE:
            escapado, tamanho = o_que_o_escape_le(segmento, i, aspa_aberta,
                                                  shell)
            crua.append(segmento[i:i + tamanho])
            lida.append(escapado)
            i += tamanho
        elif tamanho := tamanho_do_fecho_da_aspa(segmento, i, aspa_aberta,
                                                 shell):
            crua.append(segmento[i:i + tamanho])
            aspa_aberta = None
            i += tamanho
        elif aspa_aberta is None and (aspa := aspa_que_abre(segmento, i,
                                                            shell)):
            crua.append(segmento[i:i + aspa[1]])
            aspa_aberta = aspa[0]
            i += aspa[1]
        else:
            crua.append(c)
            lida.append(c)
            i += 1
    palavras.append(("".join(crua), "".join(lida)))
    if aspa_aberta is not None:
        return []
    return [(crua, lida) for crua, lida in palavras if crua]


def palavra_como_a_cerca_le(crua: str, lida: str, shell: str) -> str:
    if (shell == FERRAMENTA_BASH
            and CAMINHO_DO_WINDOWS_NA_PALAVRA.search(crua)):
        return sem_o_par_de_aspas_que_envolve(crua)
    return lida


def palavra_citada(palavra: str) -> str:
    if palavra and not CARACTERE_QUE_PEDE_ASPA.search(palavra):
        return palavra
    if ASPA_SIMPLES not in palavra:
        return ASPA_SIMPLES + palavra + ASPA_SIMPLES
    if ASPA_DUPLA not in palavra:
        return ASPA_DUPLA + palavra + ASPA_DUPLA
    return palavra


def segmento_como_o_shell_le(segmento: str, shell: str) -> str:
    palavras = palavras_como_o_shell_le(segmento, shell)
    lidas = [palavra_como_a_cerca_le(crua, lida, shell)
             for crua, lida in palavras]
    if not lidas or lidas[0] in PROGRAMAS_QUE_SO_MUDAM_DE_PASTA:
        return ""
    if all(lida == sem_o_par_de_aspas_que_envolve(crua)
           for (crua, _), lida in zip(palavras, lidas)):
        return ""
    return " ".join(palavra_citada(lida) for lida in lidas)


def com_a_leitura_do_shell(segmentos: list, shell: str,
                           apos_cano: list = None) -> tuple:
    canos = apos_cano if apos_cano is not None else [False] * len(segmentos)
    lidos, canos_lidos = [], []
    for segmento, cano in zip(segmentos, canos):
        lidos.append(segmento)
        canos_lidos.append(cano)
        if como_o_shell_le := segmento_como_o_shell_le(segmento, shell):
            lidos.append(como_o_shell_le)
            canos_lidos.append(False)
    return lidos, canos_lidos


def separar_desembrulhando(comando: str,
                           ferramenta: str = FERRAMENTA_BASH) -> list:
    shell = shell_da_ferramenta(ferramenta)
    cortado = cortar_respeitando_aspas(comando, shell)
    if cortado is None:
        segmentos = CORTE_QUANDO_A_LEITURA_NAO_FECHA[shell].split(comando)
        apos_cano = [False] * len(segmentos)
    else:
        segmentos, apos_cano = cortado
    lidos, canos = com_a_leitura_do_shell(segmentos, shell, apos_cano)
    return desembrulhador().com_os_corpos_desembrulhados(
        lidos, separar_desembrulhando, canos)


def desembrulhador():
    import importlib.util
    if CACHE_DO_DESEMBRULHADOR:
        return CACHE_DO_DESEMBRULHADOR[0]
    caminho = Path(__file__).resolve().with_name(MODULO_QUE_DESEMBRULHA)
    origem = importlib.util.spec_from_file_location(
        "desembrulhar_comando", caminho)
    modulo = importlib.util.module_from_spec(origem)
    origem.loader.exec_module(modulo)
    CACHE_DO_DESEMBRULHADOR.append(modulo)
    return modulo


def sem_os_prefixos_transparentes(tokens: list) -> list:
    restantes = list(tokens)
    while restantes:
        if ATRIBUICAO_DE_AMBIENTE.match(restantes[0]):
            restantes.pop(0)
            continue
        prefixo = Path(restantes[0]).name.lower()
        if prefixo not in PREFIXOS_TRANSPARENTES:
            break
        restantes.pop(0)
        while restantes and restantes[0].startswith(FIM_DAS_BANDEIRAS[0]):
            opcao = restantes.pop(0)
            if opcao in OPCOES_DE_PREFIXO_QUE_COMEM_O_SEGUINTE and restantes:
                restantes.pop(0)
        if prefixo == PREFIXO_COM_ARGUMENTO_PROPRIO and restantes:
            restantes.pop(0)
    return restantes


def nomes_protegidos(raiz: Path) -> set:
    arquivo = raiz / ARQUIVO_DE_BRANCHES_PROTEGIDAS
    try:
        linhas = arquivo.read_text(encoding="utf-8").splitlines()
    except OSError:
        return set(PROTEGIDAS_EMBUTIDAS)
    nomes = {l.strip().lower() for l in linhas
             if l.strip() and not l.strip().startswith(MARCA_DE_COMENTARIO)}
    return nomes or set(PROTEGIDAS_EMBUTIDAS)


def branch_de_destino_do_ref(ref: str) -> str:
    ref = ref.strip().lstrip(PREFIXO_DE_FORCAR_POR_REFSPEC)
    if PREFIXO_DE_APAGAR_POR_REFSPEC in ref:
        ref = ref.split(PREFIXO_DE_APAGAR_POR_REFSPEC, 1)[1]
    ref = PREFIXO_DE_REFS_DE_BRANCH.sub("", ref)
    return ref.strip().lower()


def e_git(token: str) -> bool:
    return Path(token.replace("\\", "/")).name.lower() in NOMES_DO_GIT


def e_gh(token: str) -> bool:
    return Path(token).name.lower().removesuffix(EXTENSAO_EXE) == NOME_DO_GH


def sem_o_par_de_aspas_que_envolve(token: str) -> str:
    for aspa in (ASPA_DUPLA, ASPA_SIMPLES):
        if len(token) >= 2 and token.startswith(aspa) and token.endswith(aspa):
            return token[1:-1]
    return token


def tokens_sem_prefixos_transparentes(segmento: str) -> list:
    try:
        import shlex
        tokens = shlex.split(segmento, posix=False)
    except ValueError:
        tokens = segmento.split()
    return sem_os_prefixos_transparentes(
        [sem_o_par_de_aspas_que_envolve(t) for t in tokens])


def indice_do_verbo(tokens: list) -> int:
    i = 1
    while i < len(tokens):
        t = tokens[i]
        if t in BANDEIRAS_GLOBAIS_QUE_COMEM_O_TOKEN_SEGUINTE:
            i += 2
            continue
        colada_por_igual = any(
            t.startswith(g + "=")
            for g in BANDEIRAS_GLOBAIS_QUE_COMEM_O_TOKEN_SEGUINTE)
        if colada_por_igual or t in BANDEIRAS_GLOBAIS_SIMPLES:
            i += 1
            continue
        if t.startswith("-"):
            i += 1
            continue
        return i
    return SEM_VERBO


def verbo_e_resto(tokens: list):
    i = indice_do_verbo(tokens)
    if i == SEM_VERBO:
        return None, []
    return tokens[i].lower(), tokens[i + 1:]


def branch_atual(alvo: Path):
    try:
        r = subprocess.run(COMANDO_DA_BRANCH_ATUAL, cwd=alvo,
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=TEMPO_LIMITE_DO_GIT)
    except (OSError, subprocess.SubprocessError):
        return None
    nome = r.stdout.strip().lower()
    return nome if r.returncode == 0 and nome and nome != HEAD_SOLTA else None


def branches_conhecidas(alvo: Path) -> set:
    try:
        r = subprocess.run(COMANDO_DAS_BRANCHES, cwd=alvo,
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=TEMPO_LIMITE_DO_GIT)
    except (OSError, subprocess.SubprocessError):
        return set()
    if r.returncode != 0:
        return set()
    return {linha.strip().lower() for linha in r.stdout.splitlines()
            if linha.strip()}


def branch_pedida_ao_checkout(resto: list):
    if FIM_DAS_BANDEIRAS in resto:
        return "", False
    espera_o_nome = False
    for token in resto:
        if espera_o_nome:
            return token.lower(), True
        if token.lower() in BANDEIRAS_QUE_CRIAM_BRANCH:
            espera_o_nome = True
            continue
        if token.startswith("-"):
            continue
        return token.lower(), False
    return "", False


def texto_que_o_shell_interpreta(comando: str) -> str:
    lido, aspa_aberta, i, delimitadores = [], None, 0, []
    while i < len(comando):
        c = comando[i]
        if c == CONTRABARRA and aspa_aberta != ASPA_SIMPLES:
            i += 2
            continue
        substituicao = (SUBSTITUICAO_QUE_A_ASPA_DUPLA_NAO_SEGURA.match(
            comando, i) if aspa_aberta == ASPA_DUPLA else None)
        if substituicao:
            lido.append(substituicao.group())
            i = substituicao.end()
            continue
        marca = (MARCA_DO_DOCUMENTO_LITERAL.match(comando, i)
                 if aspa_aberta is None else None)
        if marca:
            delimitadores.append(marca.group(2))
            i = marca.end()
            continue
        if aspa_aberta is None and c in QUEBRAS_DE_LINHA and delimitadores:
            fim = re.compile(FIM_DO_CORPO_DO_DOCUMENTO.format(
                re.escape(delimitadores.pop(0))), re.M).search(comando, i + 1)
            i = fim.end() if fim else len(comando)
            continue
        if aspa_aberta is None and comando.startswith(ABRE_ASPA_ANSI, i):
            aspa_aberta = ABRE_ASPA_ANSI
            i += len(ABRE_ASPA_ANSI)
            continue
        if aspa_aberta is None and c in ASPAS:
            aspa_aberta = c
        elif aspa_aberta is None:
            lido.append(c)
        elif c == FECHA_A_ASPA[aspa_aberta]:
            aspa_aberta = None
        i += 1
    return comando if aspa_aberta else "".join(lido)


def a_linha_so_encadeia(comando: str) -> bool:
    return not SEPARADORES_DE_COMANDO.search(
        texto_que_o_shell_interpreta(comando).replace(
            SEPARADOR_QUE_ENCADEIA, " "))


def branch_depois_do_segmento(tokens: list, aqui: str, conhecidas: set) -> str:
    if not tokens or not e_git(tokens[0]):
        return aqui
    verbo, resto = verbo_e_resto(tokens)
    if verbo not in VERBOS_QUE_TROCAM_DE_BRANCH:
        return aqui
    nome, criada = branch_pedida_ao_checkout(resto)
    if not nome:
        return aqui
    return nome if criada or nome in conhecidas else aqui


def cd_que_abre_o_comando(comando: str,
                          ferramenta: str = FERRAMENTA_BASH) -> str:
    segmentos = separar_desembrulhando(comando, ferramenta)
    primeiro = segmentos[0].strip() if segmentos else ""
    tokens = tokens_sem_prefixos_transparentes(primeiro)
    if len(tokens) >= 2 and Path(tokens[0]).name == COMANDO_CD:
        return tokens[1]
    return ""


def pasta_que_a_bandeira_c_aponta(comando: str,
                                  ferramenta: str = FERRAMENTA_BASH) -> str:
    for segmento in separar_desembrulhando(comando, ferramenta):
        tokens = tokens_sem_prefixos_transparentes(segmento.strip())
        if not tokens or not e_git(tokens[0]):
            continue
        for i, token in enumerate(tokens[1:], start=1):
            if token == BANDEIRA_DA_PASTA and i + 1 < len(tokens):
                return tokens[i + 1]
            if token.startswith(BANDEIRA_DA_PASTA) \
                    and len(token) > len(BANDEIRA_DA_PASTA):
                return token[len(BANDEIRA_DA_PASTA):]
    return ""


def comando_traz_git_init(comando: str,
                          ferramenta: str = FERRAMENTA_BASH) -> bool:
    for segmento in separar_desembrulhando(comando, ferramenta):
        tokens = tokens_sem_prefixos_transparentes(segmento.strip())
        if not tokens or not e_git(tokens[0]):
            continue
        i = indice_do_verbo(tokens)
        if i != SEM_VERBO and tokens[i].lower() == VERBO_INIT:
            return True
    return False


ALVO_QUE_O_SHELL_EXPANDIRIA = re.compile(
    r"""(?:-C\s*|\bcd\s+)['"]?((?:\$\(|\$\{|\$|`|%)[^\s'"|;&]*)""")


def expansao_que_o_gancho_nao_resolve(
        comando: str, ferramenta: str = FERRAMENTA_BASH) -> str:
    destino = (pasta_que_a_bandeira_c_aponta(comando, ferramenta)
               or cd_que_abre_o_comando(comando, ferramenta))
    if destino and any(marca in destino for marca in MARCADORES_DE_EXPANSAO):
        return destino
    no_texto_cru = ALVO_QUE_O_SHELL_EXPANDIRIA.search(comando or "")
    return no_texto_cru.group(1) if no_texto_cru else ""


def repositorio_que_o_comando_muda(onde: str, padrao: Path,
                                   comando: str = "",
                                   ferramenta: str = FERRAMENTA_BASH) -> Path:
    destino = (pasta_que_a_bandeira_c_aponta(comando, ferramenta)
               or cd_que_abre_o_comando(comando, ferramenta))
    if destino:
        alvo = Path(destino)
        onde = str(alvo if alvo.is_absolute() else Path(onde or ".") / alvo)
    if not onde:
        return padrao
    atual = Path(onde)
    try:
        atual = atual.resolve(strict=False)
    except OSError:
        return padrao
    if comando_traz_git_init(comando, ferramenta):
        return atual
    while True:
        if (atual / PASTA_DO_GIT).exists():
            return atual
        if atual.parent == atual:
            return padrao
        atual = atual.parent


def autorizacoes(raiz: Path) -> dict:
    permitido = dict(OMISSAO_NAO_E_PERMISSAO)
    try:
        dado = json.loads(
            (raiz / ARQUIVO_CONFIGURACAO).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return permitido
    declarado = (dado.get(CHAVE_DAS_AUTORIZACOES)
                 if isinstance(dado, dict) else None)
    if not isinstance(declarado, dict):
        return permitido
    for acao in permitido:
        valor = declarado.get(acao)
        if isinstance(valor, bool):
            permitido[acao] = valor
    return permitido


def e_pedaco_de_shell(token: str) -> bool:
    return any(marca in token for marca in MARCAS_QUE_SO_O_SHELL_USA)


def so_avanca_para_o_proprio_espelho(tokens: list, aqui: str) -> bool:
    i = indice_do_verbo(tokens)
    resto = tokens[i + 1:] if i != SEM_VERBO else []
    if BANDEIRA_QUE_NAO_CRIA_COMMIT not in {t.lower() for t in resto}:
        return False
    atual = (aqui or "").strip().lower()
    if not atual:
        return False
    for token in resto:
        if token.startswith("-") or e_pedaco_de_shell(token):
            continue
        nome = branch_de_destino_do_ref(token)
        if nome != atual and not nome.endswith("/" + atual):
            return False
    return True


def opcao_do_commit_come_o_seguinte(token: str) -> bool:
    if token in OPCOES_DO_COMMIT_QUE_COMEM_O_SEGUINTE:
        return True
    grupo_de_letras = (token.startswith("-") and not token.startswith("--")
                       and len(token) > 2)
    return grupo_de_letras and token[-1] in LETRAS_DO_COMMIT_QUE_COMEM_O_SEGUINTE


def commit_que_nao_grava(resto: list) -> bool:
    valor_da_opcao_anterior = False
    for token in resto:
        if valor_da_opcao_anterior:
            valor_da_opcao_anterior = False
            continue
        if token == FIM_DAS_BANDEIRAS:
            return False
        if token in BANDEIRAS_DO_COMMIT_QUE_NAO_GRAVAM:
            return True
        valor_da_opcao_anterior = opcao_do_commit_come_o_seguinte(token)
    return False


def leitura_da_chamada_a_api(resto: list) -> tuple:
    opcoes, posicionais, i = [], [], 0
    while i < len(resto):
        token = resto[i]
        i += 1
        if token == FIM_DAS_BANDEIRAS:
            posicionais.extend(resto[i:])
            break
        if token.startswith(FIM_DAS_BANDEIRAS):
            nome, igual, valor = token.partition(MARCA_DE_ATRIBUICAO_NO_SHELL)
            if (not igual and nome in OPCOES_LONGAS_DA_API_QUE_LEVAM_VALOR
                    and i < len(resto)):
                valor, i = resto[i], i + 1
            opcoes.append((nome, valor))
        elif token.startswith(LETRA_DE_OPCAO_NO_SHELL) and len(token) > 1:
            for depois_da_letra, letra in enumerate(token[1:], start=2):
                opcao = LETRA_DE_OPCAO_NO_SHELL + letra
                if letra not in LETRAS_DA_API_QUE_LEVAM_VALOR:
                    opcoes.append((opcao, ""))
                    continue
                valor = token[depois_da_letra:].removeprefix(
                    MARCA_DE_ATRIBUICAO_NO_SHELL)
                if not valor and i < len(resto):
                    valor, i = resto[i], i + 1
                opcoes.append((opcao, valor))
                break
        else:
            posicionais.append(token)
    return opcoes, posicionais


def metodo_da_chamada_a_api(resto: list) -> str:
    opcoes, _ = leitura_da_chamada_a_api(resto)
    metodos = [valor for nome, valor in opcoes
               if nome in OPCOES_DO_METODO_DA_API]
    if metodos:
        return metodos[-1].upper()
    if any(nome in OPCOES_DE_CAMPO_DA_API for nome, _ in opcoes):
        return METODO_QUANDO_HA_CAMPO
    return METODO_QUE_SO_LE


def endereco_da_chamada_a_api(resto: list) -> str:
    _, posicionais = leitura_da_chamada_a_api(resto)
    endereco = posicionais[0] if posicionais else ""
    return CONSULTA_OU_FRAGMENTO_DO_ENDERECO.split(endereco, 1)[0]


def a_api_mescla_pedido(resto: list) -> bool:
    return (bool(ENDERECO_DA_MESCLA_PELA_API.match(
        endereco_da_chamada_a_api(resto)))
        and metodo_da_chamada_a_api(resto) != METODO_QUE_SO_LE)


def a_api_mexe_em_release(resto: list) -> bool:
    endereco = endereco_da_chamada_a_api(resto)
    return (bool(ENDERECO_DA_RELEASE_PELA_API.match(endereco))
            and not ENDERECO_DAS_NOTAS_DA_RELEASE.match(endereco)
            and metodo_da_chamada_a_api(resto) != METODO_QUE_SO_LE)


def a_mutacao_graphql_publica(resto: list, texto_cru: str) -> bool:
    if not ENDERECO_DO_GRAPHQL.match(endereco_da_chamada_a_api(resto)):
        return False
    lido = " ".join([texto_cru or "", *resto]).lower()
    return any(mutacao in lido for mutacao in MUTACOES_QUE_PUBLICAM)


def a_api_publica(resto: list, texto_cru: str = "") -> bool:
    return (a_api_mescla_pedido(resto) or a_api_mexe_em_release(resto)
            or a_mutacao_graphql_publica(resto, texto_cru))


def pede_so_a_ajuda(resto: list) -> bool:
    return (any(t in BANDEIRAS_DE_AJUDA_DO_GH for t in resto)
            and all(t in BANDEIRAS_DE_AJUDA_DO_GH
                    or not t.startswith(LETRA_DE_OPCAO_NO_SHELL)
                    for t in resto))


def pede_rebase_pelo_servidor(tokens: list) -> bool:
    return e_gh(tokens[0]) and any(
        t.lower().startswith(BANDEIRA_DO_REBASE_PELO_SERVIDOR)
        for t in tokens[1:])


def acao_do_gh(verbo: str, resto: list, texto_cru: str = "") -> str:
    if pede_so_a_ajuda(resto):
        return SEM_ACAO
    if verbo == VERBO_DA_API:
        return ACAO_PUBLICAR if a_api_publica(resto, texto_cru) else SEM_ACAO
    palavras = [verbo, *resto]
    j = indice_do_verbo(palavras)
    subverbo = palavras[j].lower() if j != SEM_VERBO else SEM_SUBVERBO
    if (subverbo == SEM_SUBVERBO
            or subverbo in SUBVERBOS_QUE_SO_PEDEM.get(verbo, frozenset())):
        return SEM_ACAO
    if subverbo in SUBVERBOS_QUE_EMPURRAM.get(verbo, frozenset()):
        return ACAO_PUSH
    if (verbo == VERBO_DO_PEDIDO and subverbo == VERBO_MERGE
            and j == INDICE_DO_VERBO_SEM_BANDEIRA_ANTES
            and e_a_mescla_da_casa(palavras[j + 1:])):
        return ACAO_MESCLAR
    return ACAO_PUBLICAR if verbo in VERBOS_POR_ACAO[ACAO_PUBLICAR] \
        else SEM_ACAO


def e_a_mescla_da_casa(argumentos: list) -> bool:
    bandeiras = {a for a in argumentos if a.startswith(LETRA_DE_OPCAO_NO_SHELL)}
    pedidos = [a for a in argumentos
               if not a.startswith(LETRA_DE_OPCAO_NO_SHELL)]
    return (bandeiras == BANDEIRAS_DA_MESCLA_DA_CASA and len(pedidos) == 1
            and pedidos[0].isascii() and pedidos[0].isdigit())


def mescla_no_repositorio_da_pasta(indice_do_verbo: int,
                                   texto_cru: str) -> bool:
    baixo = (texto_cru or "").lower()
    return (indice_do_verbo == INDICE_DO_VERBO_SEM_BANDEIRA_ANTES
            and not any(nome in baixo or nome.upper() in os.environ
                        for nome in VARIAVEIS_QUE_TROCAM_O_REPOSITORIO_DO_GH))


def acao_do_comando(tokens: list, aqui: str = "", texto_cru: str = "") -> str:
    if not tokens:
        return SEM_ACAO
    programa = Path(tokens[0]).name.lower().removesuffix(EXTENSAO_EXE)
    if programa not in PROGRAMAS_QUE_ACIONAM:
        return SEM_ACAO
    i = indice_do_verbo(tokens)
    if i == SEM_VERBO:
        return SEM_ACAO
    primeiro = tokens[i].lower()
    if programa == NOME_DO_GH:
        acao = acao_do_gh(primeiro, tokens[i + 1:], texto_cru)
        if acao == ACAO_MESCLAR and not mescla_no_repositorio_da_pasta(
                i, texto_cru):
            return ACAO_PUBLICAR
        return acao
    if primeiro in VERBOS_QUE_PODEM_MESCLAR:
        if so_avanca_para_o_proprio_espelho(tokens, aqui):
            return SEM_ACAO
        return ACAO_COMMIT
    if primeiro == VERBO_COMMIT and commit_que_nao_grava(tokens[i + 1:]):
        return SEM_ACAO
    for acao, verbos in VERBOS_POR_ACAO.items():
        if primeiro in verbos:
            return acao
    return SEM_ACAO


def bandeiras_do_verbo(verbo: str, resto: list) -> set:
    bandeiras = set()
    for token in resto:
        if not token.startswith(LETRA_DE_OPCAO_NO_SHELL):
            continue
        bandeiras.add(token.lower())
        if token.startswith(FIM_DAS_BANDEIRAS):
            continue
        for letra in token[1:]:
            if letra in LETRAS_QUE_LEVAM_VALOR_NO_VERBO.get(verbo, ""):
                break
            bandeiras.add(LETRA_DE_OPCAO_NO_SHELL + letra.lower())
    return bandeiras


def recusa_do_verbo_branch(bandeiras: set, atingidas: list) -> str:
    apaga = bool(bandeiras & BANDEIRAS_DE_APAGAR)
    renomeia = bool(bandeiras & BANDEIRAS_DE_RENOMEAR)
    if (apaga or renomeia) and atingidas:
        return MOTIVO_BRANCH_PROTEGIDA.format(
            ACAO_APAGAR if apaga else ACAO_RENOMEAR, atingidas[0])
    return SEM_RECUSA


def recusa_do_verbo_push(bandeiras: set, resto: list, refs: list,
                         atingidas: list, protegidas: set, alvo: Path,
                         aqui: str = None) -> str:
    if BANDEIRA_DE_ESPELHO in bandeiras:
        return MOTIVO_ESPELHO

    apaga = bool(bandeiras & BANDEIRAS_DE_APAGAR)
    forca = bool(bandeiras & BANDEIRAS_DE_FORCA) or any(
        b.startswith(BANDEIRAS_DE_FORCA_COM_RESSALVA) for b in bandeiras)

    def destinos_com_prefixo(prefixo):
        return [branch_de_destino_do_ref(t) for t in resto
                if not t.startswith("-") and t.startswith(prefixo)]

    for nome in destinos_com_prefixo(PREFIXO_DE_APAGAR_POR_REFSPEC):
        if nome in protegidas:
            return MOTIVO_APAGAR_POR_REFSPEC.format(nome)
    for nome in destinos_com_prefixo(PREFIXO_DE_FORCAR_POR_REFSPEC):
        if nome in protegidas:
            return MOTIVO_FORCAR_POR_REFSPEC.format(nome)
    if apaga and atingidas:
        return MOTIVO_BRANCH_PROTEGIDA.format(ACAO_APAGAR, atingidas[0])
    if forca and atingidas:
        return MOTIVO_REESCREVER_HISTORIA.format(atingidas[0])
    if forca and not refs:
        atual = branch_atual(alvo) if aqui is None else aqui
        if atual in protegidas:
            return MOTIVO_REESCREVER_A_BRANCH_ATUAL.format(atual)
    return SEM_RECUSA


def branches_por_incorporacao(raiz: Path) -> set:
    try:
        dado = json.loads(
            (raiz / ARQUIVO_CONFIGURACAO).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    declarado = (dado.get(CHAVE_POR_INCORPORACAO)
                 if isinstance(dado, dict) else None)
    if not isinstance(declarado, list):
        return set()
    return {str(nome).strip().lower() for nome in declarado if str(nome).strip()}


def motivo_da_recusa(comando: str, protegidas: set, alvo: Path,
                     permitido: dict = None, aqui: str = None,
                     por_incorporacao: set = None, conhecidas: set = None,
                     sem_commit_direto: set = frozenset(),
                     ferramenta: str = FERRAMENTA_BASH):
    permitido = OMISSAO_NAO_E_PERMISSAO if permitido is None else permitido
    aqui = branch_atual(alvo) if aqui is None else aqui
    por_incorporacao = (branches_por_incorporacao(alvo)
                        if por_incorporacao is None else por_incorporacao)
    conhecidas = (branches_conhecidas(alvo) if conhecidas is None
                  else conhecidas)
    recusa_por_autorizacao_pendente = SEM_RECUSA
    recusa_por_publicar_pendente = SEM_RECUSA
    segue_a_branch = a_linha_so_encadeia(comando)
    for segmento in separar_desembrulhando(comando, ferramenta):
        tokens = tokens_sem_prefixos_transparentes(segmento.strip())
        if not tokens or not (e_git(tokens[0]) or e_gh(tokens[0])):
            continue
        if segue_a_branch:
            aqui = branch_depois_do_segmento(tokens, aqui, conhecidas)

        acao = acao_do_comando(tokens, aqui, comando)
        if acao == ACAO_PUBLICAR:
            recusa_por_publicar_pendente = MOTIVO_PUBLICAR
            continue
        if acao == ACAO_PUSH and pede_rebase_pelo_servidor(tokens):
            return MOTIVO_REBASE_PELO_SERVIDOR
        if acao == ACAO_COMMIT and aqui in por_incorporacao:
            return MOTIVO_GRAVA_EM_PROTEGIDA.format(acao, aqui)
        verbo, resto = verbo_e_resto(tokens)
        if (acao == ACAO_COMMIT and verbo == VERBO_COMMIT
                and e_git(tokens[0]) and aqui in sem_commit_direto):
            return MOTIVO_COMMIT_NA_INTEGRACAO.format(aqui)
        if (acao and not permitido.get(acao, False)
                and not recusa_por_autorizacao_pendente):
            recusa_por_autorizacao_pendente = MOTIVO_SEM_AUTORIZACAO.format(
                acao, acao, ARQUIVO_CONFIGURACAO)

        if verbo not in VERBOS_QUE_MEXEM_EM_BRANCH:
            continue

        bandeiras = bandeiras_do_verbo(verbo, resto)
        refs = [branch_de_destino_do_ref(t)
                for t in resto if not t.startswith("-")]
        atingidas = [r for r in refs if r in protegidas]

        recusa = (recusa_do_verbo_branch(bandeiras, atingidas)
                  if verbo == VERBO_BRANCH else
                  recusa_do_verbo_push(bandeiras, resto, refs, atingidas,
                                       protegidas, alvo, aqui))
        if recusa:
            return recusa
    return (recusa_por_publicar_pendente or recusa_por_autorizacao_pendente
            or None)


def comando_mescla(comando: str, ferramenta: str = FERRAMENTA_BASH) -> bool:
    return any(
        acao_do_comando(tokens_sem_prefixos_transparentes(segmento.strip()),
                        texto_cru=comando) == ACAO_MESCLAR
        for segmento in separar_desembrulhando(comando, ferramenta))


def motivo_que_vale_em_qualquer_repositorio(
        comando: str, ferramenta: str = FERRAMENTA_BASH) -> str:
    reescreve_pelo_servidor = False
    for segmento in separar_desembrulhando(comando, ferramenta):
        tokens = tokens_sem_prefixos_transparentes(segmento.strip())
        if not tokens or not e_gh(tokens[0]):
            continue
        acao = acao_do_comando(tokens, texto_cru=comando)
        if acao == ACAO_PUBLICAR:
            return MOTIVO_PUBLICAR
        if acao == ACAO_PUSH and pede_rebase_pelo_servidor(tokens):
            reescreve_pelo_servidor = True
    return MOTIVO_REBASE_PELO_SERVIDOR if reescreve_pelo_servidor \
        else SEM_RECUSA


ARQUIVO_EXECUTOR = "nucleo/executor.json"
CHAVE_DOS_PROJETOS = "projetos"
CHAVE_DO_REPOSITORIO = "repositorio"
CHAVE_DO_SO_LEITURA = "somente_leitura"
CHAVE_DAS_AUTORIZACOES_DO_VIZINHO = "autorizacoes"
CHAVE_DAS_BRANCHES_DO_CADASTRO = "branches"
CHAVE_DA_BASE = "base"
CHAVE_DA_INTEGRACAO = "integracao"
CHAVES_DAS_BRANCHES_SEM_COMMIT_DIRETO = (CHAVE_DA_INTEGRACAO, CHAVE_DA_BASE)
REPOSITORIO_DA_PROPRIA_RAIZ = "."
COMANDO_DO_REMOTO = ["git", "-C", "{alvo}", "remote", "get-url", "origin"]
COMANDO_DOS_REMOTOS = ["git", "-C", "{alvo}", "remote"]
REMOTO_QUE_A_MESCLA_ACEITA = "origin"
NOME_DO_REPOSITORIO_NO_FIM_DA_URL = re.compile(r"([^/\\:]+?)(?:\.git)?[/\\]*$")


def _executor(raiz: Path) -> dict:
    try:
        dado = json.loads(
            (raiz / ARQUIVO_EXECUTOR).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return dado if isinstance(dado, dict) else {}


def _projetos(raiz: Path) -> dict:
    projetos = _executor(raiz).get(CHAVE_DOS_PROJETOS) or {}
    return projetos if isinstance(projetos, dict) else {}


def _projeto_pelo_nome(projetos: dict, nome: str) -> dict:
    if not nome:
        return {}
    for projeto in projetos.values():
        if isinstance(projeto, dict) \
                and projeto.get(CHAVE_DO_REPOSITORIO) == nome:
            return projeto
    return {}


def _projeto_do_repositorio(raiz: Path, nome: str) -> dict:
    return _projeto_pelo_nome(_projetos(raiz), nome)


@lru_cache(maxsize=None)
def endereco_do_remoto(alvo: Path) -> str:
    comando = [parte.format(alvo=alvo) for parte in COMANDO_DO_REMOTO]
    try:
        r = subprocess.run(comando, capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           timeout=TEMPO_LIMITE_DO_GIT)
    except (OSError, subprocess.SubprocessError):
        return ""
    return r.stdout.strip() if r.returncode == 0 else ""


def so_o_origin_como_remoto(alvo: Path) -> bool:
    comando = [parte.format(alvo=alvo) for parte in COMANDO_DOS_REMOTOS]
    try:
        r = subprocess.run(comando, capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           timeout=TEMPO_LIMITE_DO_GIT)
    except (OSError, subprocess.SubprocessError):
        return False
    return r.returncode == 0 and r.stdout.split() == [REMOTO_QUE_A_MESCLA_ACEITA]


def nome_do_repositorio_no_remoto(alvo: Path) -> str:
    casou = NOME_DO_REPOSITORIO_NO_FIM_DA_URL.search(endereco_do_remoto(alvo))
    return casou.group(1) if casou else ""


def e_a_propria_raiz(raiz: Path, alvo: Path) -> bool:
    if Path(alvo) == Path(raiz):
        return True
    do_alvo = endereco_do_remoto(Path(alvo))
    return bool(do_alvo) and do_alvo == endereco_do_remoto(Path(raiz))


def projeto_do_alvo(raiz: Path, alvo: Path) -> dict:
    projetos = _projetos(raiz)
    pela_pasta = _projeto_pelo_nome(projetos, Path(alvo).name)
    if pela_pasta or not projetos or Path(alvo) == Path(raiz):
        return pela_pasta
    return _projeto_pelo_nome(projetos, nome_do_repositorio_no_remoto(alvo))


def e_somente_leitura(raiz: Path, alvo: Path) -> bool:
    projeto = _projeto_do_repositorio(raiz, Path(alvo).name)
    return bool(projeto.get(CHAVE_DO_SO_LEITURA))


def branches_sem_commit_direto(raiz: Path, alvo: Path,
                               projeto: dict = None) -> set:
    projeto = projeto_do_alvo(raiz, alvo) if projeto is None else projeto
    if not projeto:
        if not e_a_propria_raiz(raiz, alvo):
            return set()
        projeto = _projeto_pelo_nome(_projetos(raiz),
                                     REPOSITORIO_DA_PROPRIA_RAIZ)
    do_projeto = projeto.get(CHAVE_DAS_BRANCHES_DO_CADASTRO)
    do_topo = _executor(raiz).get(CHAVE_DAS_BRANCHES_DO_CADASTRO)
    nomes = set()
    for chave in CHAVES_DAS_BRANCHES_SEM_COMMIT_DIRETO:
        declarada = ((do_projeto.get(chave)
                      if isinstance(do_projeto, dict) else None)
                     or (do_topo.get(chave)
                         if isinstance(do_topo, dict) else None))
        if isinstance(declarada, str) and declarada.strip():
            nomes.add(declarada.strip().lower())
    return nomes


def autorizacoes_do_alvo(raiz: Path, alvo: Path, projeto: dict = None) -> dict:
    if Path(alvo) == Path(raiz):
        return autorizacoes(alvo)
    projeto = projeto_do_alvo(raiz, alvo) if projeto is None else projeto
    declarado = projeto.get(CHAVE_DAS_AUTORIZACOES_DO_VIZINHO)
    if isinstance(declarado, dict):
        permitido = dict(OMISSAO_NAO_E_PERMISSAO)
        for acao in permitido:
            if isinstance(declarado.get(acao), bool):
                permitido[acao] = declarado[acao]
    else:
        permitido = autorizacoes(alvo)
    if e_a_propria_raiz(raiz, alvo):
        return permitido
    return {**permitido, ACAO_MESCLAR: False}


def raiz_do_projeto_nunca_o_cwd() -> Path:
    declarada = os.environ.get(VARIAVEL_DA_RAIZ_DO_PROJETO)
    if declarada:
        return Path(declarada)
    return Path(__file__).resolve().parents[NIVEIS_DO_GANCHO_ATE_A_RAIZ]


def texto_traz_git_ou_gh(texto: str) -> bool:
    normalizado = " ".join(texto.lower().split()) + " "
    return any(marca in normalizado for marca in MARCAS_DO_GIT_E_DO_GH)


def comando_sem_git_nem_gh(comando: str,
                           ferramenta: str = FERRAMENTA_BASH) -> bool:
    baixo = (comando or "").lower()
    lido = ESCAPE_E_ASPA_QUE_O_SHELL_TIRA.sub("", baixo)
    if any(marca in texto for texto in (baixo, lido)
           for marca in MARCAS_DO_GIT_E_DO_GH):
        return False
    aberto = " ".join(separar_desembrulhando(comando, ferramenta))
    return not texto_traz_git_ou_gh(aberto)


def recusa_por_nao_medir_o_alvo(alvo: str) -> int:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": EVENTO_ANTES_DA_FERRAMENTA,
        "permissionDecision": DECISAO_DE_NEGAR,
        "permissionDecisionReason": RECUSA_SEM_MEDIR_O_ALVO.format(alvo),
    }}))
    return SILENCIO


def recusa_por_nao_entender(falha) -> int:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": EVENTO_ANTES_DA_FERRAMENTA,
        "permissionDecision": DECISAO_DE_NEGAR,
        "permissionDecisionReason": RECUSA_SEM_ENTENDER.format(
            type(falha).__name__, falha),
    }}))
    return SILENCIO


def decidir() -> int:
    try:
        entrada = json.load(sys.stdin)
        comando = entrada.get("tool_input", {}).get("command", "")
        onde = entrada.get("cwd") or ""
        ferramenta = entrada.get("tool_name") or FERRAMENTA_BASH
    except (json.JSONDecodeError, AttributeError, TypeError,
            ValueError) as falha:
        return recusa_por_nao_entender(falha)

    if not comando or comando_sem_git_nem_gh(comando, ferramenta):
        return SILENCIO
    if em_qualquer_repositorio := motivo_que_vale_em_qualquer_repositorio(
            comando, ferramenta):
        return negar_ensinando_o_caminho(em_qualquer_repositorio)

    raiz = raiz_do_projeto_nunca_o_cwd()
    alvo = repositorio_que_o_comando_muda(onde, raiz, comando, ferramenta)
    if e_somente_leitura(raiz, alvo):
        return (negar_ensinando_o_caminho(MOTIVO_PUBLICAR)
                if comando_mescla(comando, ferramenta) else SILENCIO)
    projeto = projeto_do_alvo(raiz, alvo)
    motivo = motivo_da_recusa(
        comando, nomes_protegidos(alvo), alvo,
        autorizacoes_do_alvo(raiz, alvo, projeto), None,
        branches_por_incorporacao(alvo), None,
        branches_sem_commit_direto(raiz, alvo, projeto), ferramenta)
    if not motivo:
        return (fecho_da_mescla_liberada(comando, ferramenta, alvo)
                if comando_mescla(comando, ferramenta) else SILENCIO)
    if nao_expandido := expansao_que_o_gancho_nao_resolve(comando,
                                                          ferramenta):
        return recusa_por_nao_medir_o_alvo(nao_expandido)
    return negar_ensinando_o_caminho(motivo)


def fecho_da_mescla_liberada(comando: str, ferramenta: str, alvo: Path) -> int:
    if nao_expandido := expansao_que_o_gancho_nao_resolve(comando, ferramenta):
        return recusa_por_nao_medir_o_alvo(nao_expandido)
    if not so_o_origin_como_remoto(alvo):
        return negar_ensinando_o_caminho(MOTIVO_MESCLA_COM_OUTRO_REMOTO)
    return SILENCIO


def negar_ensinando_o_caminho(motivo: str) -> int:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": EVENTO_ANTES_DA_FERRAMENTA,
        "permissionDecision": DECISAO_DE_NEGAR,
        "permissionDecisionReason": recusa_que_ensina_o_caminho(motivo),
    }}))
    return SILENCIO


def recusa_que_ensina_o_caminho(motivo: str) -> str:
    if motivo in (MOTIVO_PUBLICAR, MOTIVO_MESCLA_COM_OUTRO_REMOTO):
        return (RECUSA_POR_PUBLICAR.format(motivo)
                + MANDA_GRAVAR.format(APRENDIZADO_DE_PUBLICAR))
    if TRECHO_DA_CHAVE_DA_MESCLA in motivo:
        return (RECUSA_POR_MESCLA_SEM_CHAVE.format(motivo)
                + MANDA_GRAVAR.format(APRENDIZADO_DA_MESCLA))
    if motivo == MOTIVO_REBASE_PELO_SERVIDOR:
        return (RECUSA_POR_REBASE_PELO_SERVIDOR.format(motivo)
                + MANDA_GRAVAR.format(APRENDIZADO_DO_REBASE_PELO_SERVIDOR))
    if MARCA_DA_RECUSA_POR_AUTORIZACAO in motivo:
        return (RECUSA_POR_AUTORIZACAO.format(motivo)
                + MANDA_GRAVAR.format(APRENDIZADO_DA_AUTORIZACAO))
    if MARCA_DA_RECUSA_PELO_CADASTRO in motivo:
        return (RECUSA_POR_COMMIT_NA_INTEGRACAO.format(motivo)
                + MANDA_GRAVAR.format(APRENDIZADO_DA_INTEGRACAO))
    return (RECUSA_POR_BRANCH_PROTEGIDA.format(motivo)
            + MANDA_GRAVAR.format(APRENDIZADO_DA_BRANCH))


CODIFICADO_DO_PUSH = ("ZwBpAHQAIABwAHUAcwBoACAALQAtAGYAbwByAGMAZQAgAG8AcgBp"
                      "AGcAaQBuACAAbQBhAGkAbgA=")
BARRA = [
    ("apagar local, forma óbvia", "git branch -d homolog"),
    ("apagar local, maiúscula", "git branch -D develop"),
    ("apagar no remoto", "git push origin --delete homolog"),
    ("apagar por refspec", "git push origin :homolog"),
    ("forçar, forma óbvia", "git push --force origin main"),
    ("forçar, o que o glob não pega", "git push origin +homolog"),
    ("forçar com lease ainda reescreve",
     "git push --force-with-lease origin develop"),
    ("escondida depois de &&", "git status && git push --force origin homolog"),
    ("bandeira antes do verbo", "git -C /tmp/x push --force origin main"),
    ("configuração antes do verbo", "git -c user.name=x branch -D main"),
    ("caminho absoluto do programa", "/usr/bin/git branch -d homolog"),
    ("no Windows, com .exe", "git.exe push origin --delete main"),
    ("renomear a protegida", "git branch -m develop develop-velha"),
    ("refs/heads explícito", "git push origin +refs/heads/main"),
    ("forçar na forma curta", "git push -f origin homolog"),
    ("caminho do Windows antes do verbo",
     r"git -C C:\repo push --force origin main"),
    ("escondido depois da quebra de linha",
     "git status\ngit push --force origin main"),
    ("aspas duplas no nome da branch", 'git branch -D "main"'),
    ("aspas simples no nome da branch", "git push origin --delete 'homolog'"),
    ("espelhar reescreve tudo", "git push --mirror origin"),
    ("escondido dentro de subcomando",
     "git status $(git push --force origin main)"),
    ("aspa solta não abre porta",
     "git status ' && git push --force origin main"),
    ("aspas duplas não seguram o subcomando",
     'git status "$(git push --force origin main)"'),
    ("documento que expande ainda executa",
     "cat <<FIM\n$(git push --force origin main)\nFIM"),
    ("env na frente não disfarça", "env git push --force origin main"),
    ("env com variável própria na frente",
     "env GIT_TRACE=1 git push --force origin main"),
    ("timeout com o prazo na frente",
     "timeout 30 git push --force origin main"),
    ("nice na frente", "nice git push --force origin main"),
    ("nice com prioridade na frente", "nice -n 10 git push --force origin main"),
    ("stdbuf com opção na frente", "stdbuf -oL git push --force origin main"),
    ("sh -c embrulha o push", "sh -c 'git push --force origin main'"),
    ("bash -lc embrulha o push", 'bash -lc "git push --force origin main"'),
    ("eval embrulha o push", "eval 'git push --force origin main'"),
    ("xargs entrega o sh -c que apaga",
     "ls | xargs -I{} sh -c 'git branch -D homolog'"),
    ("a aspa escapada não abre aspa, e o push entre dois echo é do shell",
     'echo \\" ; git push --force origin main ; echo \\"'),
    ("a contrabarra no fim da linha junta a seguinte ao push",
     "git push \\\n --force origin main"),
    ("dentro da aspa simples a contrabarra não escapa, e a aspa fecha antes "
     "do push", "echo 'a\\' ; git push --force origin main"),
    ("o ponto e vírgula dentro do $() entre aspas duplas é do shell",
     'echo "$(true; git push --force origin main)"'),
    ("o ponto e vírgula dentro da crase entre aspas duplas é do shell",
     'echo "`true; git push --force origin main`"'),
    ("o parêntese dentro do $() não fecha a substituição",
     'echo "$( (true) ; git push --force origin main )"'),
    ("a crase escapada dentro da crase abre a substituição de dentro",
     "echo `echo \\`git push --force origin main\\``"),
    ("o parêntese abre um subshell", "(git push --force origin main)"),
    ("o & solto separa o comando", "true & git push --force origin main"),
    ("a aspa no corpo do documento que expande não esconde o push",
     "cat <<EOF\n'\nEOF\ngit push --force origin main\necho '"),
    ("nem quando o documento está dentro do $() entre aspas duplas",
     'echo "$(cat <<EOF\n\'\nEOF\n)"; git push --force origin main\n'
     "echo ')\""),
    ("a contrabarra no fim da linha antes do comando some, e o push fica "
     "inteiro", "\\\ngit push --force origin main"),
    ("a contrabarra no fim da linha depois do && também some",
     "true &&\\\ngit push --force origin main"),
    ("a contrabarra no fim da linha entre o programa e o verbo some",
     "git \\\n push --force origin main"),
    ("a contrabarra no fim da linha no meio do verbo junta o verbo",
     "git pu\\\nsh --force origin main"),
    ("a marca de documento dentro da aspa não apaga o resto do comando",
     "echo \"<<'X'\"; git push --force origin main"),
    ("nem dentro da mensagem de commit",
     "git commit -m \"veja <<'EOF'\"; git push --force origin main"),
    ("o resto da linha que abre o documento literal é comando",
     "cat <<'EOF'; git push --force origin main\nhello\nEOF"),
    ("o documento literal que o bash lê é comando",
     "bash <<'EOF'\ngit push --force origin main\nEOF"),
    ("o documento literal que vai pelo cano ao sh é comando",
     "cat <<'EOF' | sh\ngit push --force origin main\nEOF"),
    ("a aspa dentro do comentário não esconde a linha seguinte",
     "echo ok # \"\ngit push --force origin main\n# \""),
    ("as chaves agrupam comandos", "{ git push --force origin main; }"),
    ("o corpo da função é comando",
     "f() { git push --force origin main; }; f"),
    ("a função com a palavra function também",
     "function f { git push --force origin main; }"),
    ("a exclamação na frente não disfarça", "! git push --force origin main"),
    ("o do do laço não disfarça",
     "for f in a; do git push --force origin main; done"),
    ("o then do if não disfarça",
     "if true; then git push --force origin main; fi"),
    ("a contrabarra no meio do programa não disfarça o git",
     "gi\\t push --force origin main"),
    ("a aspa no meio do programa não disfarça o git",
     "\"gi\"t push --force origin main"),
    ("a aspa vazia na frente do programa não disfarça o git",
     "''git push --force origin main"),
    ("a aspa $'...' em volta do programa não disfarça o git",
     "$'git' push --force origin main"),
    ("o escape numérico da aspa $'...' não disfarça o git",
     "$'\\x67it' push --force origin main"),
    ("a contrabarra no meio da branch não disfarça a main",
     "git push --force origin ma\\in"),
    ("a aspa no meio da branch não disfarça a main",
     "git push --force origin \"ma\"in"),
    ("o texto que o echo entrega ao sh pelo cano é comando",
     "echo 'git push --force origin main' | sh"),
    ("o texto que o printf entrega ao bash pelo cano é comando",
     "printf '%s' 'git push --force origin main' | bash"),
    ("a cadeia do <<< entrega o push ao bash",
     "bash <<< 'git push --force origin main'"),
    ("pwsh -c embrulha o push", 'pwsh -c "git push --force origin main"'),
    ("powershell -Command embrulha o push",
     'powershell -NoProfile -Command "git push --force origin main"'),
    ("cmd /c embrulha o push", 'cmd /c "git push --force origin main"'),
    ("o documento dentro do bash -c é comando",
     "bash -c \"$(cat <<'EOF'\ngit push --force origin main\nEOF\n)\""),
    ("o documento dentro do eval é comando",
     "eval \"$(cat <<'EOF'\n"
     "git push --force origin main\nEOF\n)\""),
    ("o documento do bash -c com a substituição aberta na linha de cima "
     "é comando",
     "bash -c \"$(\ncat <<'EOF'\n"
     "git push --force origin main\nEOF\n)\""),
    ("o -EncodedCommand do PowerShell se decodifica e cai na cerca",
     "pwsh -NoProfile -EncodedCommand " + CODIFICADO_DO_PUSH),
    ("o nome do shell entre aspas na frente do documento é comando",
     "\"bash\" <<EOF\ngit push --force origin main\nEOF"),
    ("o nome do shell com aspa no meio na frente do documento é comando",
     "b\"as\"h <<'EOF'\ngit push --force origin main\nEOF"),
    ("o documento entregue ao sh com posicional é comando",
     "echo 'git push --force origin main' | sh -s -- x"),
    ("o eval roda o texto que a substituição devolve",
     "eval $(echo 'git push --force origin main')"),
    ("o eval roda o texto que a crase devolve",
     "eval `echo 'git push --force origin main'`"),
    ("o eval entre aspas roda o texto que a substituição devolve",
     'eval "$(echo git push --force origin main)"'),
    ("o source lê o comando da substituição de processo",
     "source <(echo 'git push --force origin main')"),
    ("o bash lê o comando da substituição de processo",
     "bash <(echo 'git push --force origin main')"),
    ("o |& entrega o texto ao bash como o cano",
     "echo 'git push --force origin main' |& bash"),
    ("o corpo do pwsh -c se lê com a crase do PowerShell, não com a do Bash",
     "pwsh -c \"echo \\`'; git push --force origin main; echo \\`'\\` x\""),
    ("o xargs entrega o git", "ls | xargs git push --force origin main"),
    ("o xargs entrega o git depois da opção que leva valor",
     "ls | xargs -n 1 git push --force origin main"),
    ("a força agrupada com outra bandeira curta", "git push -fu origin main"),
    ("a força no fim do grupo de bandeiras curtas",
     "git push -uf origin main"),
    ("apagar agrupado com forçar", "git branch -Df main"),
    ("forçar agrupado com apagar", "git branch -fD homolog"),
]

SO_PEDEM = [
    ("abrir PR é pedir, não publicar — o dono é quem incorpora",
     "gh pr create --fill"),
    ("ver PR não muda nada", "gh pr view 1"),
    ("listar PR não muda nada", "gh pr list"),
    ("comentar em PR é falar, não publicar",
     "gh pr comment 13 --body texto"),
    ("etiquetar PR não incorpora nada", "gh pr edit 13 --add-label pronto"),
    ("tirar o rascunho não incorpora nada", "gh pr ready 13"),
    ("baixar o PR mexe só na cópia local", "gh pr checkout 13"),
    ("o apelido do list só lista", "gh pr ls"),
    ("o apelido do create só pede", "gh pr new --title t --body b"),
    ("o apelido do checkout mexe só na cópia local", "gh pr co 7"),
    ("o apelido do list da release só lista", "gh release ls"),
    ("o pr sozinho só imprime a ajuda", "gh pr"),
    ("a release sozinha também", "gh release"),
    ("ver a release não muda nada", "gh release view v1"),
    ("listar as releases não muda nada", "gh release list"),
    ("baixar os anexos da release mexe só na cópia local",
     "gh release download v1"),
    ("conferir a atestação da release só lê", "gh release verify v1"),
    ("trancar a conversa do pedido não incorpora nada", "gh pr lock 13"),
    ("destrancar a conversa também não", "gh pr unlock 13"),
    ("o manual do merge não mescla nada", "gh pr merge --help"),
    ("o manual do update-branch não empurra nada",
     "gh pr update-branch --help"),
    ("o -R antes do subverbo não esconde que só se vê",
     "gh pr -R o/r view 1"),
    ("ler a mescla do pedido pela API não mescla nada",
     "gh api repos/d/r/pulls/7/merge"),
    ("mudar o título do pedido pela API não o mescla",
     "gh api -X PATCH repos/d/r/pulls/7 -f title=x"),
    ("listar os pedidos pela API não mescla nada", "gh api repos/d/r/pulls"),
    ("o link da mescla no corpo do pedido é valor, não endereço",
     "gh api -X PATCH repos/d/r/pulls/7 "
     "-f body=https://github.com/d/r/pulls/7/merge"),
    ("o grupo curto com o GET colado só lê",
     "gh api -iXGET repos/d/r/pulls/7/merge"),
    ("o grupo curto com o GET separado só lê",
     "gh api -iX GET repos/d/r/pulls/7/merge"),
    ("vale o último método, e o último é GET",
     "gh api -X PUT -X GET repos/d/r/pulls/7/merge"),
    ("listar as releases pela API só lê", "gh api repos/d/r/releases"),
    ("gerar as notas pela API não cria a release",
     "gh api repos/d/r/releases/generate-notes -f tag_name=v1"),
    ("as notas com a barra no fim também não",
     "gh api repos/d/r/releases/generate-notes/ -f tag_name=v1"),
    ("a consulta GraphQL que só lê não mescla nada",
     "gh api graphql -f query='query{viewer{login}}'"),
]

PERMITE_COMMIT_E_PUSH = {ACAO_COMMIT: True, ACAO_PUSH: True}
TRECHO_DE_PUBLICAR_E_DO_DONO = "Publicar é do dono, sempre"
TRECHO_QUE_MANDA_LIGAR_A_CHAVE = "ligue a chave"
TRECHO_DA_AUTORIZACAO_DO_PUSH = "`autorizacoes.push`"
EMPURRAM_PELO_SERVIDOR = [
    ("atualizar a branch do pedido é empurrar pelo servidor",
     "gh pr update-branch 13"),
    ("reverter o pedido cria branch nova e um pedido: é empurrar",
     "gh pr revert 13"),
]
REESCREVEM_PELO_SERVIDOR = [
    ("o rebase pelo servidor reescreve a branch de cabeça do pedido",
     "gh pr update-branch 13 --rebase"),
    ("com o valor colado por igual também",
     "gh pr update-branch 13 --rebase=true"),
]
PUBLICAR_E_DO_DONO = [
    ("mesclar contornando a aprovação", "gh pr merge 1 --merge --admin"),
    ("ligar a mescla automática", "gh pr merge 1 --auto --merge"),
    ("mesclar apagando a branch de cabeça",
     "gh pr merge 1 --merge --delete-branch"),
    ("a letra curta de apagar também", "gh pr merge 1 -m -d"),
    ("mesclar amassando os commits", "gh pr merge 1 --squash"),
    ("mesclar rebaseando os commits", "gh pr merge 1 --rebase"),
    ("mesclar sem dizer o método", "gh pr merge 1"),
    ("a letra curta do método fica fora da forma da casa", "gh pr merge 1 -m"),
    ("sem número, o pedido que o gh escolhe", "gh pr merge --merge"),
    ("dois números", "gh pr merge 1 2 --merge"),
    ("o pedido pelo endereço, que nomeia outro repositório",
     "gh pr merge https://github.com/d/r/pull/1 --merge"),
    ("o pedido pelo nome da branch", "gh pr merge minha-branch --merge"),
    ("o algarismo de outra escrita não é número",
     "gh pr merge " + chr(0x661) + " --merge"),
    ("a bandeira de repositório entre o pr e o merge",
     "gh pr -R d/r merge 1 --merge"),
    ("a bandeira de repositório depois do método",
     "gh pr merge 1 --merge -R d/r"),
    ("a bandeira longa de repositório colada por igual",
     "gh pr merge 1 --merge --repo=d/r"),
    ("o repositório trocado pelo ambiente",
     "GH_REPO=d/r gh pr merge 1 --merge"),
    ("o servidor trocado pelo ambiente",
     "GH_HOST=outro.exemplo gh pr merge 1 --merge"),
    ("qualquer outra bandeira fecha a forma da casa",
     "gh pr merge 1 --merge --body texto"),
    ("criar a release", "gh release create v1"),
    ("o apelido do create da release também cria", "gh release new v1"),
    ("a bandeira global longa não esconde a mescla",
     "gh --repo d/r pr merge 13 --merge"),
    ("a bandeira global curta também não", "gh -R d/r pr merge 13 --merge"),
    ("tirar a release do rascunho é lançá-la",
     "gh release edit v1 --draft=false"),
    ("a mescla pela API", "gh api -X PUT repos/d/r/pulls/7/merge"),
    ("a mescla pela API com o método por extenso",
     "gh api --method PUT repos/{owner}/{repo}/pulls/7/merge "
     "-f merge_method=squash"),
    ("o método colado por igual e a barra na frente do endereço",
     "gh api --method=PUT /repos/d/r/pulls/7/merge"),
    ("o método colado na letra", "gh api -XPUT repos/d/r/pulls/7/merge"),
    ("o método depois do endereço, em minúscula",
     "gh api repos/d/r/pulls/7/merge -X put"),
    ("o endereço inteiro",
     "gh api -X PUT https://api.github.com/repos/d/r/pulls/7/merge"),
    ("sem -X e com campo o gh manda POST",
     "gh api repos/d/r/pulls/7/merge -f merge_method=squash"),
    ("sem -X e com --input também",
     "gh api repos/d/r/pulls/7/merge --input corpo.json"),
    ("vale o último método, e o último não é GET",
     "gh api -X GET -X PUT repos/d/r/pulls/7/merge"),
    ("o grupo curto com o método separado",
     "gh api -iX PUT repos/d/r/pulls/7/merge"),
    ("o método em variável não é GET",
     'gh api -X "$METODO" repos/d/r/pulls/7/merge'),
    ("a mescla pela mutação GraphQL",
     "gh api graphql -f query='mutation{mergePullRequest(input:"
     "{pullRequestId:\"X\"}){clientMutationId}}'"),
    ("a mescla automática pela mutação GraphQL",
     "gh api graphql -f query='mutation{enablePullRequestAutoMerge(input:"
     "{pullRequestId:\"X\"}){clientMutationId}}'"),
    ("criar a release pela API", "gh api repos/d/r/releases -f tag_name=v1"),
    ("lançar o rascunho pela API",
     "gh api -X PATCH repos/d/r/releases/1 -F draft=false"),
    ("as notas na consulta do endereço não fazem do lançamento as notas",
     "gh api -X PATCH 'repos/d/r/releases/1?x=/releases/generate-notes' "
     "-F draft=false"),
    ("as notas no fragmento do endereço também não",
     "gh api -X PATCH 'repos/d/r/releases/1#/releases/generate-notes' "
     "-F draft=false"),
    ("criar a release com as notas na consulta do endereço",
     "gh api 'repos/d/r/releases?/releases/generate-notes' -f tag_name=v1"),
    ("o caminho que só termina como o das notas não é o das notas",
     "gh api -X PATCH repos/d/r/releases/1/releases/generate-notes "
     "-F draft=false"),
    ("o gh.exe contorna igual", "gh.exe pr merge 8 --merge --admin"),
    ("o gh.exe mescla igual pela API",
     "gh.exe api -X PUT repos/d/r/pulls/8/merge"),
]
FALHA_PUBLICAR_LIBERADO = "  DEVIA NEGAR como publicar, {} — {}: saiu {!r}"
MESCLA_DA_CASA = [
    ("a mescla da casa", "gh pr merge 1 --merge"),
    ("o método antes do número", "gh pr merge --merge 1"),
    ("o gh.exe mescla igual", "gh.exe pr merge 8 --merge"),
    ("o token do robô na frente não troca o repositório",
     "GH_TOKEN=x gh pr merge 1 --merge"),
]
PERMITE_A_MESCLA = {ACAO_COMMIT: True, ACAO_PUSH: True, ACAO_MESCLAR: True}
TRECHO_DA_AUTORIZACAO_DA_MESCLA = TRECHO_DA_CHAVE_DA_MESCLA
TRECHO_DA_DECISAO_DO_DONO = "é decisão do dono, não da sessão"
FALHA_RECUSA_DA_MESCLA = (
    "  a recusa da mescla sem chave não diz que ligar a chave é do dono, ou "
    "manda a sessão ligá-la")
FALHA_MESCLA_DA_CASA = (
    "  [a mescla da casa segue autorizacoes.mesclar] {} — {}: saiu {!r}")
FALHA_RECUSA_DE_PUBLICAR = (
    "  a recusa de publicar não diz que é do dono, sempre, ou manda ligar a "
    "chave")
FALHA_EMPURRA_PELO_SERVIDOR = (
    "  [empurrar pelo servidor segue autorizacoes.push] {} — {}: saiu {!r}")
FALHA_REBASE_PELO_SERVIDOR = (
    "  [o rebase pelo servidor se nega com motivo próprio] {}: saiu {!r}")

DEIXA_PASSAR = [
    ("push normal na protegida", "git push origin develop"),
    ("o texto que a substituição devolve ao diff é dado, não comando",
     "diff <(echo 'git push --force origin main') <(echo x)"),
    ("o eval do agente de chaves roda só o que o agente imprime",
     'eval "$(ssh-agent -s)"'),
    ("a opção do push com valor colado não vira bandeira de força",
     "git push -oforce origin main"),
    ("push normal, sem ref", "git push"),
    ("apagar branch de trabalho", "git branch -d feature/x"),
    ("forçar branch de trabalho", "git push --force origin feature/x"),
    ("nome que só parece", "git branch -d develop-antiga"),
    ("nome que contém a protegida",
     "git push origin --delete feature/main-menu"),
    ("outro programa", "docker push imagem:main"),
    ("commit comum", "git commit -m 'apaga develop do texto'"),
    ("criar branch a partir da protegida", "git branch feature/nova develop"),
    ("checkout da protegida", "git checkout main"),
    ("buscar do remoto", "git fetch origin main"),
    ("listar branches", "git branch -a"),
    ("push normal para a protegida", "git push origin main"),
    ("quebra de linha, trabalho comum", "git status\ngit push origin feature/x"),
    ("aspas duplas em branch de trabalho", 'git branch -D "feature/x"'),
    ("aspas simples em nome que só parece",
     "git push origin --delete 'feature/homolog-antiga'"),
    ("espelhar em clone não é push",
     "git clone --mirror https://exemplo.invalido/r.git"),
    ("subcomando que não empurra nada", "git status $(git rev-parse HEAD)"),
    ("mensagem de commit que cita o veto",
     'git commit -m "não rode git push --force origin main"'),
    ("aspas simples seguram o comando inteiro",
     "echo 'git push --force origin main'"),
    ("documento literal é dado, não comando",
     "gh issue comment 13 --body-file - <<'FIM'\ngit push --force origin main"
     "\nFIM"),
    ("timeout na frente de trabalho comum", "timeout 30 git fetch origin main"),
    ("env -i não come o programa", "env -i git status"),
    ("sh -c que só lê", "sh -c 'git status'"),
    ("a aspa dupla de verdade segura o ponto e vírgula",
     'echo "x; git push --force origin main"'),
    ("a contrabarra dentro da aspa simples é texto, e a aspa segura o "
     "ponto e vírgula", "echo 'a\\b; git push --force origin main'"),
    ("fora das aspas a contrabarra torna o ponto e vírgula texto",
     "git commit -m x\\; y"),
    ("a aspa simples dentro do $() segura o ponto e vírgula",
     "echo \"$(echo 'a; git push --force origin main')\""),
    ("sem crase aberta, a crase escapada na aspa dupla é texto",
     'git commit -m "cita \\`git push --force origin main\\`"'),
    ("o documento que expande só com texto é dado",
     "cat <<EOF\ngit push --force origin main\nEOF"),
    ("a cadeia do <<< é texto entre aspas",
     "cat <<< 'texto; git push --force origin main; texto'"),
    ("depois do documento que expande a aspa volta a segurar o ponto e "
     "vírgula",
     "cat <<EOF\ntexto\nEOF\necho 'texto; git push --force origin main; "
     "texto'"),
    ("o comentário é do shell, não comando",
     "git status # git push --force origin main"),
    ("o grep que procura sh não roda o texto que chega pelo cano",
     "echo 'git push --force origin main' | grep sh"),
    ("o nome do shell dentro da aspa da mensagem não faz do documento um "
     "comando",
     "git commit -m \"conserta o bash $(cat <<'EOF'\ngit push --force "
     "origin main\nEOF\n)\""),
    ("a mensagem do commit que vem do documento é dado",
     "git commit -m \"$(cat <<'EOF'\n"
     "git push --force origin main\nEOF\n)\""),
    ("o documento que o bash -c recebe como posicional é dado",
     "bash -c 'echo \"$1\"' x \"$(cat <<'EOF'\n"
     "git push --force origin main\nEOF\n)\""),
    ("o documento literal sem terminador é dado até o fim",
     "cat <<'EOF'\ngit push --force origin main"),
    ("o nome do shell como argumento do grep na linha do documento é dado",
     "cat <<'EOF' | grep -c bash\ngit push --force origin main\nEOF"),
    ("o nome do shell como argumento do python na linha do documento é dado",
     "python - bash <<'EOF'\ngit push --force origin main\nEOF"),
    ("o nome do shell como argumento do echo não é executor",
     "echo pwsh 'git push --force origin main'"),
    ("o texto antes do ponto e vírgula não é entregue ao shell seguinte",
     "echo 'git push --force origin main'; bash -s"),
    ("o texto antes do && não é entregue ao shell seguinte",
     "echo 'git push --force origin main' && bash"),
]

BARRA_NO_POWERSHELL = [
    ("no PowerShell a contrabarra é texto, e a aspa fecha antes do push",
     'echo "a\\" ; git push --force origin main ; echo \\"b"'),
    ("no PowerShell a crase escapa a aspa, e o push entre dois echo é do "
     "shell", 'echo `"; git push --force origin main; echo `"'),
    ("no PowerShell o ponto e vírgula dentro do $() entre aspas duplas",
     'echo "$(echo a; git push --force origin main)"'),
    ("no PowerShell o & chama o programa", "& git push --force origin main"),
    ("no PowerShell o bloco entre chaves é comando",
     "1 | ForEach-Object { git push --force origin main }"),
    ("no PowerShell a aspa curva fecha a aspa reta",
     'echo "a\N{RIGHT DOUBLE QUOTATION MARK} ; git push --force origin main'
     ' ; echo \N{LEFT DOUBLE QUOTATION MARK}b"'),
    ("no PowerShell a aspa dentro do texto de várias linhas é texto",
     '@"\n"\n"@; git push --force origin main; @"\n"\n"@'),
    ("no PowerShell não há documento do Bash que esconda o push",
     "echo \"<<'X'\"; git push --force origin main"),
    ("no PowerShell a crase no fim da linha junta o verbo ao programa",
     "git `\n push --force origin main"),
    ("no PowerShell o comentário de bloco na frente não disfarça",
     "<# c #> git push --force origin main"),
    ("no PowerShell a aspa dentro do comentário não esconde a linha "
     "seguinte", "echo ok # \"\ngit push --force origin main\n# \""),
    ("no PowerShell a crase no meio do verbo não disfarça o push",
     "git pu`sh --force origin main"),
    ("no PowerShell o Invoke-Expression embrulha o push",
     'Invoke-Expression "git push --force origin main"'),
    ("no PowerShell o iex embrulha o push",
     "iex 'git push --force origin main'"),
    ("no PowerShell o texto que chega ao iex pelo cano é comando",
     "'git push --force origin main' | iex"),
    ("no PowerShell o iex roda o texto que o parêntese devolve",
     "iex (echo 'git push --force origin main')"),
    ("no PowerShell o Start-Process chama o git com a lista",
     "Start-Process git -ArgumentList 'push','--force','origin','main'"),
    ("no PowerShell o Start-Process chama o git com a lista num texto só",
     "Start-Process -FilePath git -ArgumentList 'push --force origin main'"),
    ("no PowerShell o saps é o Start-Process",
     "saps git 'push --force origin main'"),
]

DEIXA_PASSAR_NO_POWERSHELL = [
    ("no PowerShell a aspa dupla segura o ponto e vírgula",
     'echo "x; git push --force origin main"'),
    ("no PowerShell a contrabarra na aspa simples é texto",
     "echo 'a\\b; git push --force origin main'"),
    ("no PowerShell a crase escapa a aspa, e a aspa segue segurando o "
     "ponto e vírgula",
     'echo "a`" ; git push --force origin main ; echo `"b"'),
    ("no PowerShell a contrabarra não escapa, e a aspa abre o texto",
     'echo \\" ; git push --force origin main ; echo \\"'),
    ("no PowerShell o texto literal de várias linhas é dado",
     "@'\ngit push --force origin main; it's\n'@"),
    ("no PowerShell a aspa simples dobrada segue dentro da aspa",
     "echo 'it''s; git push --force origin main'"),
    ("no PowerShell o comentário de bloco é do shell, não comando",
     "<# git push --force origin main #>"),
]

GIT_MERGE_NAO_E_PUBLICAR = [
    ("merge local em branch de trabalho não é publicar",
     "git merge --ff-only origin/main"),
    ("merge local com mensagem também não",
     'git merge homolog -m "junta"'),
]
GIT_MERGE_EM_PROTEGIDA = [
    ("merge grava na protegida sem passar pelo pedido",
     "git merge homolog"),
    ("o atalho de sempre é fetch mais merge, e pode gravar igual",
     "git pull"),
    ("o atalho com remoto e branch também pode gravar",
     "git pull origin homolog"),
    ("avançar para outra branch não cria commit, mas promove trabalho "
     "sem passar pelo pedido de incorporação",
     "git merge --ff-only issue/1-alguma-coisa"),
]
AVANCA_O_PONTEIRO_SEM_GRAVAR = [
    ("avançar para o próprio espelho não cria commit nenhum: é adotar o que "
     "o remoto já tem", "git merge --ff-only origin/{}"),
    ("o atalho travado em avanço também não cria commit", "git pull --ff-only"),
    ("redirecionar a saída não é apontar para outra branch",
     "git pull --ff-only 2>&1"),
    ("nem encadear com o que vem depois",
     "git merge --ff-only origin/{} 2>&1"),
]
GH_MERGE_CONTINUA_SENDO_PUBLICAR = [
    ("gh pr merge sem a chave continua recusado", "gh pr merge 8 --merge"),
]
SAI_DA_PROTEGIDA_ANTES_DE_GRAVAR = [
    ("o checkout na mesma linha tira a gravação da protegida",
     "git checkout homolog && git merge --ff-only main"),
    ("switch vale igual ao checkout",
     "git switch homolog && git merge main"),
    ("branch nova nasce fora da protegida, e o commit cai nela",
     "git checkout -b issue/9-x && git commit -m x"),
    ("switch -c também cria fora", "git switch -c issue/9-x && git commit -m x"),
    ("o corpo do documento literal da mensagem não solta o commit do "
     "checkout",
     "git checkout -b issue/9-x && git commit -F - <<'EOF'\nmsg; x\nEOF"),
]
ENTRA_NA_PROTEGIDA_E_GRAVA = [
    ("entrar na protegida e gravar continua barrado",
     "git checkout main && git commit -m x"),
    ("switch para a protegida idem", "git switch main && git merge outra"),
    ("checkout que pode falhar nao livra o commit seguinte quando o "
     "separador nao encadeia: com ponto e virgula o commit roda de todo "
     "jeito, e cai na protegida",
     "git checkout -b issue/9 ; git commit -m x"),
    ("nem com o ou-senao, que roda o seguinte justamente quando falhou",
     "git switch -c issue/9 || echo ja existe ; git commit -m x"),
    ("o documento literal não esconde o ponto e vírgula que solta o commit "
     "do checkout",
     "cat <<'EOF'; git checkout -b issue/9 ; git commit -m x"),
]
RESTAURA_ARQUIVO_E_NAO_TROCA_DE_BRANCH = [
    ("restaurar arquivo de outra branch nao e trocar de branch",
     "git checkout main -- montar.py && git commit -m x"),
    ("com o switch nao existe pathspec, mas o checkout de arquivo solto "
     "tambem nao troca nada",
     "git checkout main -- . && git commit -m x"),
]
FALHA_RESTAURO_VIROU_TROCA = (
    "  DEVIA PASSAR: restaurar arquivo de outra branch nao muda a branch "
    "atual — {}")
BRANCHES_CONHECIDAS_DO_TESTE = {"main", "homolog", "outra"}
FALHA_SAIU_DA_PROTEGIDA_E_BARROU = (
    "  DEVIA PASSAR: o checkout na linha muda a branch antes da gravação — {}")
FALHA_ENTROU_NA_PROTEGIDA_E_PASSOU = (
    "  DEVIA BARRAR: a linha entra na branch de incorporação e grava — {}")
FALHA_ARQUIVO_VIROU_BRANCH = (
    "  DEVIA BARRAR: 'git checkout arquivo.txt' não é troca de branch, e o "
    "commit seguinte ainda cai na protegida")
FALHA_MERGE_LOCAL_BARRADO = (
    "  DEVIA PASSAR: git merge local não é publicar — {}")
FALHA_EXPANSAO_NAO_VISTA = (
    "  expansão não vista ({}): em {!r} o gancho leu {!r}, e o alvo cru é {!r} "
    "— sem enxergar a expansão ele julga a branch da raiz e recusa com razão "
    "inventada")
FALHA_LITERAL_ACUSADO = (
    "  caminho literal acusado de expansão ({}): {!r} não tem expansão nenhuma "
    "e o gancho recusaria sem precisar")
FALHA_RECUSA_INVENTA_RAZAO = (
    "  a recusa por alvo não medido fala de branch protegida ou nomeia a main "
    "— é exatamente a razão inventada que ela existe para não dar")
FALHA_BANDEIRA_C_IGNORADA = (
    "  ALVO ERRADO: `git -C <pasta>` tem de apontar o mesmo repositório que "
    "`cd <pasta> &&`. Sem isso o gancho julga a branch da raiz e recusa "
    "mescla que ia para dentro da branch de trabalho. Esperado {}; pelo cd "
    "{}; pela bandeira separada {}; pela bandeira colada {}")
FALHA_MERGE_EM_PROTEGIDA_PASSOU = (
    "  DEVIA BARRAR: git merge grava na branch de incorporação — {}")
FALHA_AVANCO_BARRADO = (
    "  DEVIA PASSAR: avanço de ponteiro que não cria commit foi barrado — "
    "{} ({})")
FALHA_GH_MERGE_PASSOU = (
    "  DEVIA BARRAR sem autorização de publicar — {}")

BARRA_SEM_AUTORIZACAO = [
    ("commit sem autorização", "git commit -m x"),
    ("push sem autorização", "git push origin feature/minha"),
    ("o caminho do -C não é o verbo", "git -C /tmp/x commit -m algo"),
    ("a configuração do -c não é o verbo",
     "git -c user.name=x commit -m algo"),
]

AUTORIZA_TUDO = {"commit": True, "push": True, "mesclar": True,
                 "publicar": True}
FORCA_EM_PROTEGIDA = "git push --force origin main"
BRANCH_DE_TRABALHO_DO_TESTE = "issue/1-algo"
BRANCH_DE_INTEGRACAO_DO_TESTE = "homolog"
BRANCHES_POR_INCORPORACAO_DO_TESTE = ("main",)
GRAVA_EM_PROTEGIDA = (
    ("commit direto", 'git commit -m "algo"'),
    ("commit com todos", "git commit -am algo"),
    ("commit por caminho absoluto", '/usr/bin/git commit -m "algo"'),
)
FALHA_GRAVOU_EM_PROTEGIDA = (
    "  DEVIA BARRAR mesmo autorizado, em '{}' na branch '{}'")
FALHA_BARROU_NA_DE_TRABALHO = (
    "  DEVIA PASSAR na branch de trabalho — {}")
FALHA_BARROU_NA_INTEGRACAO = (
    "  DEVIA PASSAR na branch de integração não declarada — {}")
FALHA_SO_PEDE_E_BARROU = (
    "  DEVIA PASSAR sem autorização, porque só pede — {}")


NOME_DO_VIZINHO_SO_LEITURA = "vizinho-so-leitura"
NOME_DO_VIZINHO_LIBERADO = "vizinho-liberado"
FALHA_FALOU_NO_SO_LEITURA = (
    "  DEVIA CALAR no somente-leitura e falou — {}")
FALHA_BARROU_VIZINHO_LIBERADO = (
    "  DEVIA PASSAR no vizinho com autorizacao declarada e barrou — {}")
FALHA_PASSOU_VIZINHO_SEM_DECLARAR = (
    "  DEVIA BARRAR no vizinho sem autorizacao declarada e passou")


def _as_duas_recusas_se_distinguem(falhas):
    import json as _json
    import tempfile as _tempfile
    with _tempfile.TemporaryDirectory(prefix="vetar-vizinho-") as pasta:
        raiz = Path(pasta)
        (raiz / "nucleo").mkdir(parents=True, exist_ok=True)
        (raiz / ARQUIVO_EXECUTOR).write_text(_json.dumps({
            CHAVE_DOS_PROJETOS: {
                "a": {CHAVE_DO_REPOSITORIO: NOME_DO_VIZINHO_SO_LEITURA,
                      CHAVE_DO_SO_LEITURA: True},
                "b": {CHAVE_DO_REPOSITORIO: NOME_DO_VIZINHO_LIBERADO,
                      CHAVE_DAS_AUTORIZACOES_DO_VIZINHO: {"push": True,
                                                          "commit": True}},
                "c": {CHAVE_DO_REPOSITORIO: "vizinho-mudo"},
            }}), encoding="utf-8")

        so_leitura = raiz / "projetos" / NOME_DO_VIZINHO_SO_LEITURA
        liberado = raiz / "projetos" / NOME_DO_VIZINHO_LIBERADO
        mudo = raiz / "projetos" / "vizinho-mudo"
        for onde in (so_leitura, liberado, mudo):
            onde.mkdir(parents=True, exist_ok=True)

        if not e_somente_leitura(raiz, so_leitura):
            falhas.append(FALHA_FALOU_NO_SO_LEITURA.format("nao reconheceu"))
        if e_somente_leitura(raiz, liberado):
            falhas.append(FALHA_FALOU_NO_SO_LEITURA.format("falso positivo"))

        if not autorizacoes_do_alvo(raiz, liberado).get("push"):
            falhas.append(FALHA_BARROU_VIZINHO_LIBERADO.format("push"))
        if autorizacoes_do_alvo(raiz, mudo).get("push"):
            falhas.append(FALHA_PASSOU_VIZINHO_SEM_DECLARAR)


FALHA_JULGOU_PELA_BRANCH_ERRADA = (
    "[a branch julgada é a do repositório onde o comando roda] {}")
FALHA_INIT_ENCADEADO = "[init encadeado é julgado no berçário] {}"


def _o_init_encadeado_e_julgado_no_bercario(falhas):
    import subprocess as _subprocess
    import tempfile as _tempfile

    def _hook(projeto_dir, cwd, comando):
        entrada = json.dumps({"tool_input": {"command": comando},
                              "cwd": str(cwd)})
        r = _subprocess.run(
            [sys.executable, str(Path(__file__).resolve())],
            input=entrada, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            env={**os.environ, VARIAVEL_DA_RAIZ_DO_PROJETO: str(projeto_dir)})
        return r.stdout

    par = "git init -q -b issue/1 . && git commit --allow-empty -m x"
    with _tempfile.TemporaryDirectory(prefix="vetar-init-encadeado-") as pasta:
        atlas_de_mentira = Path(pasta) / "atlas"
        bercario = atlas_de_mentira / "projetos" / "novo"
        bercario.mkdir(parents=True)
        _subprocess.run(["git", "-C", str(atlas_de_mentira), "init", "-q",
                         "-b", "issue/1", "."], check=True,
                        capture_output=True, text=True, encoding="utf-8", errors="replace")
        (atlas_de_mentira / "nucleo").mkdir()
        (atlas_de_mentira / ARQUIVO_CONFIGURACAO).write_text(json.dumps(
            {CHAVE_DAS_AUTORIZACOES: {"commit": True, "push": True}}),
            encoding="utf-8")
        if "deny" not in _hook(atlas_de_mentira, bercario, par):
            falhas.append(FALHA_INIT_ENCADEADO.format(
                "pasta sem declaração — o par devia ser negado e passou"))
        (atlas_de_mentira / ARQUIVO_EXECUTOR).write_text(json.dumps({
            CHAVE_DOS_PROJETOS: {"n": {CHAVE_DO_REPOSITORIO: "novo",
                                       CHAVE_DAS_AUTORIZACOES_DO_VIZINHO: {
                                           "commit": True}}}}),
            encoding="utf-8")
        if _hook(atlas_de_mentira, bercario, par).strip():
            falhas.append(FALHA_INIT_ENCADEADO.format(
                "vizinho declarado com commit — o par devia calar e negou"))


def _a_branch_julgada_e_a_do_alvo(falhas):
    import subprocess as _subprocess
    import tempfile as _tempfile

    def _git(onde, *args):
        _subprocess.run(["git", "-C", str(onde), *args], check=True,
                        capture_output=True, text=True, encoding="utf-8", errors="replace")

    def _hook(projeto_dir, cwd, comando):
        entrada = json.dumps({"tool_input": {"command": comando},
                              "cwd": str(cwd)})
        r = _subprocess.run(
            [sys.executable, str(Path(__file__).resolve())],
            input=entrada, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            env={**os.environ, VARIAVEL_DA_RAIZ_DO_PROJETO: str(projeto_dir)})
        return r.stdout

    with _tempfile.TemporaryDirectory(prefix="vetar-branch-julgada-") as pasta:
        raiz = Path(pasta)
        atlas_de_mentira = raiz / "atlas"
        vizinho = raiz / "vizinho"
        for onde in (atlas_de_mentira, vizinho):
            onde.mkdir()
            _git(onde, "init", "-q", "-b", "issue/1", ".")
            _git(onde, "commit", "-q", "--allow-empty", "-m", "x")
        (atlas_de_mentira / "nucleo").mkdir()
        (atlas_de_mentira / ARQUIVO_EXECUTOR).write_text(json.dumps({
            CHAVE_DOS_PROJETOS: {"v": {CHAVE_DO_REPOSITORIO: "vizinho",
                                       CHAVE_DAS_AUTORIZACOES_DO_VIZINHO: {
                                           "push": True}}}}), encoding="utf-8")

        _git(vizinho, "checkout", "-q", "-b", "main")
        saida = _hook(atlas_de_mentira, vizinho, "git push --force")
        if "deny" not in saida:
            falhas.append(FALHA_JULGOU_PELA_BRANCH_ERRADA.format(
                "vizinho na main, atlas fora — devia negar e não negou"))
        if "main" not in saida:
            falhas.append(FALHA_JULGOU_PELA_BRANCH_ERRADA.format(
                "negou sem nomear a branch do vizinho"))

        _git(vizinho, "checkout", "-q", "-b", "issue/2")
        saida = _hook(atlas_de_mentira, vizinho, "git push --force")
        if saida.strip():
            falhas.append(FALHA_JULGOU_PELA_BRANCH_ERRADA.format(
                "vizinho fora da protegida — devia calar e negou"))

        (vizinho / ".claude").mkdir()
        (vizinho / ARQUIVO_DE_BRANCHES_PROTEGIDAS).write_text(
            "staging-do-vizinho\n", encoding="utf-8")
        _git(vizinho, "checkout", "-q", "-b", "staging-do-vizinho")
        saida = _hook(atlas_de_mentira, vizinho, "git push --force")
        if "deny" not in saida:
            falhas.append(FALHA_JULGOU_PELA_BRANCH_ERRADA.format(
                "vizinho declara sua própria branches-protegidas.txt — "
                "devia negar e não negou"))
        if "staging-do-vizinho" not in saida:
            falhas.append(FALHA_JULGOU_PELA_BRANCH_ERRADA.format(
                "negou sem nomear a branch declarada pelo vizinho"))


FALHA_DO_CADASTRO = (
    "[o cadastro guarda a integração da raiz e do vizinho] {} — esperado {}; "
    "saiu {!r}")
REMOTO_DE_TESTE = "https://exemplo.invalido/dono/{}.git"
NEGA = True
CALA = False
RECUSA_QUE_ENSINA_A_MESCLA = ("homolog", "--no-ff")
CASOS_DO_CADASTRO = (
    ("commit direto na integração do vizinho", "atlas", "vizinho",
     "git commit -m x", NEGA, RECUSA_QUE_ENSINA_A_MESCLA),
    ("a mescla --no-ff de uma branch de trabalho é o caminho da entrega",
     "atlas", "vizinho", "git merge --no-ff issue/1-x", CALA, ()),
    ("commit na branch de trabalho do vizinho passa", "atlas", "vizinho",
     "git switch issue/1-x && git commit -m x", CALA, ()),
    ("commit pela bandeira -C, de fora do vizinho", "atlas", "atlas",
     "git -C {vizinho} commit -m x", NEGA, RECUSA_QUE_ENSINA_A_MESCLA),
    ("worktree com outro nome e o remoto certo vale o cadastro: commit na "
     "branch de trabalho passa", "atlas", "vizinho-2", "git commit -m x",
     CALA, ()),
    ("worktree com outro nome e o remoto certo vale o cadastro: a base "
     "declarada também não recebe commit direto", "atlas", "vizinho-3",
     "git commit -m x", NEGA, ("develop", "--no-ff")),
    ("vizinho cadastrado sem branches herda o padrão do topo", "atlas",
     "herdeiro", "git commit -m x", NEGA, RECUSA_QUE_ENSINA_A_MESCLA),
    ("vizinho sem cadastro fica como antes, sem lista inventada", "atlas",
     "estranho", "git commit -m x", CALA, ()),
    ("no vizinho, trocar para a integração e commitar na mesma linha",
     "atlas", "vizinho-2", 'git switch homolog && git commit -m "x y"',
     NEGA, RECUSA_QUE_ENSINA_A_MESCLA),
    ("no vizinho, o ponto e vírgula dentro da mensagem não é separador do "
     "shell e não desliga a troca de branch", "atlas", "vizinho-2",
     'git switch homolog && git commit -m "x; y"', NEGA,
     RECUSA_QUE_ENSINA_A_MESCLA),
    ("no vizinho, a quebra de linha do documento literal também não "
     "desliga a troca de branch", "atlas", "vizinho-2",
     "git switch homolog && git commit -F - <<'FIM'\nx\nFIM", NEGA,
     RECUSA_QUE_ENSINA_A_MESCLA),
    ("a raiz também não recebe commit direto na integração que o bloco "
     "branches declara", "atlas", "atlas", 'git commit -m "x y"', NEGA,
     RECUSA_QUE_ENSINA_A_MESCLA),
    ("a mescla --no-ff na integração da raiz passa", "atlas", "atlas",
     "git merge --no-ff issue/1-x", CALA, ()),
    ("HEAD destacado da raiz: trocar para a integração e commitar na "
     "mesma linha", "atlas-destacada", "atlas-destacada",
     'git switch homolog && git commit -m "x y"', NEGA,
     RECUSA_QUE_ENSINA_A_MESCLA),
    ("ponto e vírgula dentro da mensagem do commit, na raiz",
     "atlas-destacada", "atlas-destacada",
     'git switch homolog && git commit -m "x; y"', NEGA,
     RECUSA_QUE_ENSINA_A_MESCLA),
    ("a worktree destacada da raiz, vista de outra raiz, é achada pelo "
     "remoto", "atlas", "atlas-destacada",
     'git switch homolog && git commit -m "x y"', NEGA,
     RECUSA_QUE_ENSINA_A_MESCLA),
    ("commit em HEAD destacado da raiz não cai na integração", "atlas",
     "atlas-destacada", "git commit -m x", CALA, ()),
    ("--dry-run mostra o que entraria e não cria commit", "atlas",
     "vizinho", "git commit --dry-run -m x", CALA, ()),
    ("--help abre o manual e não cria commit", "atlas", "vizinho",
     "git commit --help", CALA, ()),
    ("-h mostra o uso e não cria commit", "atlas", "vizinho",
     "git commit -h", CALA, ()),
    ("a mensagem que se chama --dry-run não livra o commit", "atlas",
     "vizinho", "git commit -m --dry-run", NEGA,
     RECUSA_QUE_ENSINA_A_MESCLA),
    ("a mescla com conflito se conclui por git merge --continue", "atlas",
     "vizinho", "git merge --continue", CALA, ()),
    ("no vizinho, a aspa escapada dentro da aspa dupla não fecha a "
     "mensagem, e o ponto e vírgula seguinte ainda é texto", "atlas",
     "vizinho-2", 'git switch homolog && git commit -m "x\\"; y"', NEGA,
     RECUSA_QUE_ENSINA_A_MESCLA),
    ("no vizinho, o '\\'' fecha a aspa simples, escapa uma aspa e reabre",
     "atlas", "vizinho-2",
     "git switch homolog && git commit -m 'x'\\''; y'", NEGA,
     RECUSA_QUE_ENSINA_A_MESCLA),
    ("no vizinho, dentro de $'...' a contrabarra escapa a aspa simples",
     "atlas", "vizinho-2",
     "git switch homolog && git commit -m $'x\\'; y'", NEGA,
     RECUSA_QUE_ENSINA_A_MESCLA),
)

FALHA_DO_ENCADEAMENTO = (
    "  [a troca de branch se acompanha pelo que o shell encadeia] {} — "
    "esperado {}, saiu {}: {!r}")
CASOS_DO_ENCADEAMENTO = (
    ("a contrabarra escapada fecha a aspa dupla, e o ponto e vírgula "
     "seguinte é do shell",
     'git switch homolog && git commit -m "x\\\\"; git status', False),
    ("dentro da aspa simples a contrabarra não escapa, e a aspa fecha",
     "git switch homolog && git commit -m 'x\\'; git status", False),
    ("fora das aspas a contrabarra torna o ponto e vírgula literal",
     "git switch homolog && git commit -m x\\; y", True),
    ("fora das aspas a aspa escapada não abre aspa, e o ponto e vírgula "
     "seguinte é do shell",
     'git switch homolog && git commit -m x\\" ; git status', False),
    ("a aspa escapada dentro de $'...' não fecha, e a aspa seguinte fecha",
     "git switch homolog && git commit -m $'x\\''; git status", False),
    ("a marca de documento literal só apaga o corpo: o ponto e vírgula da "
     "mesma linha é do shell",
     "git switch homolog && cat <<'EOF'; git commit -m x\nEOF", False),
    ("o corpo do documento literal não é separador",
     "git switch -c x && git commit -F - <<'EOF'\nmsg; y\nEOF", True),
)


FALHA_DO_PORTAO = (
    "  [o portão lê a palavra como o shell lê] {} — esperado {}, saiu {}: "
    "{!r}")
CASOS_DO_PORTAO = (
    ("a contrabarra no meio do programa não fecha o portão cedo",
     "gi\\t push --force origin main", False),
    ("a aspa no meio do programa não fecha o portão cedo",
     "\"gi\"t push --force origin main", False),
    ("a crase do PowerShell no meio do programa não fecha o portão cedo",
     "g`it push --force origin main", False),
    ("a aspa no meio do gh não fecha o portão cedo",
     "g\"h\" pr merge 1 --merge", False),
    ("o -EncodedCommand se abre e não fecha o portão cedo",
     "pwsh -NoProfile -EncodedCommand " + CODIFICADO_DO_PUSH, False),
    ("o escape numérico da aspa ansi não fecha o portão cedo",
     "$'\\x67it' push --force origin main", False),
    ("o gh separado por tabulação não fecha o portão cedo",
     "gh\tpr merge 13", False),
    ("o gh.exe do Windows não fecha o portão cedo",
     "gh.exe pr merge 8 --merge", False),
    ("o GH.EXE em maiúscula também não fecha o portão cedo",
     "GH.EXE pr merge 8", False),
    ("o gh.exe que chama a API não fecha o portão cedo",
     "gh.exe api -X PUT repos/d/r/pulls/8/merge", False),
    ("o caminho que termina em gh.exe não fecha o portão cedo",
     "C:\\ferramentas\\gh.exe pr merge 8", False),
    ("sem git nem gh o portão fecha cedo", "echo oi", True),
)

FALHA_DO_GH_DO_WINDOWS = (
    "  [o gh.exe passa pela cerca inteira] {} no {} — esperado {}, saiu {!r}")
CASOS_DO_GH_DO_WINDOWS = (
    ("o gh.exe mescla o pedido como o gh", "gh.exe pr merge 8 --merge", NEGA),
    ("o GH.EXE em maiúscula mescla igual", "GH.EXE pr merge 8", NEGA),
    ("o gh.exe mescla o pedido pela API",
     "gh.exe api -X PUT repos/d/r/pulls/8/merge", NEGA),
    ("CONTROLE: o gh.exe que só vê o pedido passa", "gh.exe pr view 8", CALA),
)

LIGA_AS_TRES_CHAVES = {ACAO_COMMIT: True, ACAO_PUSH: True,
                       ACAO_PUBLICAR: True}
NOME_DO_VIZINHO_DA_PROVA = "vizinho"
NOME_DO_CLONE_SO_LEITURA_DA_PROVA = "vizinho-so-leitura"
NOME_DA_RAIZ_DA_PROVA = "atlas"
CASOS_DE_PUBLICAR_PELO_ARQUIVO = (
    ("mesclar contornando a aprovação", "gh pr merge 8 --merge --admin", NEGA),
    ("criar a release", "gh release create v1", NEGA),
    ("mesclar pela API", "gh api -X PUT repos/d/r/pulls/8/merge", NEGA),
    ("CONTROLE: o push da branch de trabalho segue a chave, que está ligada",
     "git push origin " + BRANCH_DE_TRABALHO_DO_TESTE, CALA),
    ("CONTROLE: atualizar a branch do pedido segue o push, que está ligado",
     "gh pr update-branch 8", CALA),
    ("CONTROLE: ver a release passa", "gh release view v1", CALA),
)
CASOS_DE_PUBLICAR_ANTES_DO_ALVO = (
    ("no clone somente leitura, a mescla em outro repositório",
     NOME_DO_CLONE_SO_LEITURA_DA_PROVA, "gh -R dono/outro pr merge 8 --merge"),
    ("no clone somente leitura, a mescla pela API",
     NOME_DO_CLONE_SO_LEITURA_DA_PROVA,
     "gh api -X PUT repos/d/r/pulls/8/merge"),
    ("na raiz, com a pasta numa variável, a razão é publicar e não o alvo",
     NOME_DA_RAIZ_DA_PROVA, 'cd "$WT" && gh pr merge 8'),
)
CASOS_DO_REBASE_ANTES_DO_ALVO = (
    ("no clone somente leitura, o rebase pelo servidor em outro repositório",
     NOME_DO_CLONE_SO_LEITURA_DA_PROVA,
     "gh pr update-branch -R d/r 8 --rebase"),
    ("na raiz, com o cd para o clone somente leitura",
     NOME_DA_RAIZ_DA_PROVA,
     "cd ../" + NOME_DO_CLONE_SO_LEITURA_DA_PROVA
     + " && gh pr update-branch -R d/r 8 --rebase"),
)
FALHA_PUBLICAR_PELO_ARQUIVO = (
    "  [publicar não se liga pelo arquivo] {} em {} — esperado {}, saiu {!r}")
FALHA_REBASE_ANTES_DO_ALVO = (
    "  [o rebase pelo servidor se nega antes do alvo] {} em {} — saiu {!r}")
FALHA_A_CHAVE_PUBLICAR_FOI_LIDA = (
    "  [a chave publicar não se lê] {} devolveu {!r}")


def razao_da_negativa(saida: str) -> str:
    try:
        bloco = json.loads(saida).get("hookSpecificOutput", {})
    except (ValueError, AttributeError):
        return ""
    if bloco.get("permissionDecision") != DECISAO_DE_NEGAR:
        return ""
    return bloco.get("permissionDecisionReason", "")


def _publicar_nao_se_liga_pelo_arquivo(falhas):
    with tempfile.TemporaryDirectory(prefix="vetar-publicar-") as pasta:
        raiz = Path(pasta).resolve()
        atlas, vizinho, _ = [
            repositorio_de_prova(raiz / nome, BRANCH_DE_TRABALHO_DO_TESTE)
            for nome in (NOME_DA_RAIZ_DA_PROVA, NOME_DO_VIZINHO_DA_PROVA,
                         NOME_DO_CLONE_SO_LEITURA_DA_PROVA)]
        (atlas / ARQUIVO_CONFIGURACAO).write_text(json.dumps(
            {CHAVE_DAS_AUTORIZACOES: LIGA_AS_TRES_CHAVES}), encoding="utf-8")
        (atlas / ARQUIVO_EXECUTOR).write_text(json.dumps({
            CHAVE_DOS_PROJETOS: {
                "v": {CHAVE_DO_REPOSITORIO: NOME_DO_VIZINHO_DA_PROVA,
                      CHAVE_DAS_AUTORIZACOES_DO_VIZINHO: LIGA_AS_TRES_CHAVES},
                "s": {CHAVE_DO_REPOSITORIO: NOME_DO_CLONE_SO_LEITURA_DA_PROVA,
                      CHAVE_DO_SO_LEITURA: True}}}), encoding="utf-8")
        for lido, permitido in (
                ("a configuração da raiz", autorizacoes(atlas)),
                ("o cadastro do vizinho",
                 autorizacoes_do_alvo(atlas, vizinho))):
            if ACAO_PUBLICAR in permitido:
                falhas.append(FALHA_A_CHAVE_PUBLICAR_FOI_LIDA.format(
                    lido, permitido))
        for onde in (atlas, vizinho):
            for rotulo, comando, nega in CASOS_DE_PUBLICAR_PELO_ARQUIVO:
                saida = saida_do_gancho_inteiro(atlas, onde, comando)
                certo = (TRECHO_DE_PUBLICAR_E_DO_DONO in razao_da_negativa(
                    saida) if nega else not saida.strip())
                if not certo:
                    falhas.append(FALHA_PUBLICAR_PELO_ARQUIVO.format(
                        rotulo, onde.name,
                        "negar como publicar" if nega else "calar",
                        saida.strip()[:200]))
        for rotulo, nome, comando in CASOS_DE_PUBLICAR_ANTES_DO_ALVO:
            saida = saida_do_gancho_inteiro(atlas, raiz / nome, comando)
            if TRECHO_DE_PUBLICAR_E_DO_DONO not in razao_da_negativa(saida):
                falhas.append(FALHA_PUBLICAR_PELO_ARQUIVO.format(
                    rotulo, nome, "negar como publicar", saida.strip()[:200]))
        for rotulo, nome, comando in CASOS_DO_REBASE_ANTES_DO_ALVO:
            saida = saida_do_gancho_inteiro(atlas, raiz / nome, comando)
            if MOTIVO_REBASE_PELO_SERVIDOR not in razao_da_negativa(saida):
                falhas.append(FALHA_REBASE_ANTES_DO_ALVO.format(
                    rotulo, nome, saida.strip()[:200]))


PASSA_CALADO = ""
NOME_DA_RAIZ_COM_OUTRO_REMOTO = "atlas-com-upstream"
NOME_DA_WORKTREE_DA_RAIZ = "atlas-worktree"
TRECHO_DO_ALVO_NAO_MEDIDO = "não sabe qual repositório"
SEM_AMBIENTE_A_MAIS = {}
CASOS_DA_MESCLA_PELO_ALVO = (
    ("na raiz que liga a chave, a mescla da casa passa",
     NOME_DA_RAIZ_DA_PROVA, NOME_DA_RAIZ_DA_PROVA, "gh pr merge 8 --merge",
     PASSA_CALADO, SEM_AMBIENTE_A_MAIS),
    ("na raiz que liga a chave, a mescla que contorna a aprovação nega",
     NOME_DA_RAIZ_DA_PROVA, NOME_DA_RAIZ_DA_PROVA,
     "gh pr merge 8 --merge --admin", TRECHO_DE_PUBLICAR_E_DO_DONO,
     SEM_AMBIENTE_A_MAIS),
    ("da raiz, o repositório trocado pelo prefixo nega",
     NOME_DA_RAIZ_DA_PROVA, NOME_DA_RAIZ_DA_PROVA,
     "GH_REPO=d/vizinho gh pr merge 8 --merge", TRECHO_DE_PUBLICAR_E_DO_DONO,
     SEM_AMBIENTE_A_MAIS),
    ("da raiz, o repositório trocado no ambiente do gancho nega",
     NOME_DA_RAIZ_DA_PROVA, NOME_DA_RAIZ_DA_PROVA, "gh pr merge 8 --merge",
     TRECHO_DE_PUBLICAR_E_DO_DONO, {"GH_REPO": "d/vizinho"}),
    ("da raiz, a pasta numa variável não se mede e nega",
     NOME_DA_RAIZ_DA_PROVA, NOME_DA_RAIZ_DA_PROVA,
     'cd "$WT" && gh pr merge 8 --merge', TRECHO_DO_ALVO_NAO_MEDIDO,
     SEM_AMBIENTE_A_MAIS),
    ("da raiz, o cd para o vizinho leva o alvo junto",
     NOME_DA_RAIZ_DA_PROVA, NOME_DA_RAIZ_DA_PROVA,
     "cd ../" + NOME_DO_VIZINHO_DA_PROVA + " && gh pr merge 8 --merge",
     TRECHO_DA_DECISAO_DO_DONO, SEM_AMBIENTE_A_MAIS),
    ("no vizinho, a chave no cadastro não libera a mescla",
     NOME_DA_RAIZ_DA_PROVA, NOME_DO_VIZINHO_DA_PROVA, "gh pr merge 8 --merge",
     TRECHO_DA_DECISAO_DO_DONO, SEM_AMBIENTE_A_MAIS),
    ("no clone somente leitura, a mescla nega em vez de calar",
     NOME_DA_RAIZ_DA_PROVA, NOME_DO_CLONE_SO_LEITURA_DA_PROVA,
     "gh pr merge 8 --merge", TRECHO_DE_PUBLICAR_E_DO_DONO,
     SEM_AMBIENTE_A_MAIS),
    ("na worktree da raiz, a chave dela vale",
     NOME_DA_RAIZ_DA_PROVA, NOME_DA_WORKTREE_DA_RAIZ, "gh pr merge 8 --merge",
     PASSA_CALADO, SEM_AMBIENTE_A_MAIS),
    ("na raiz com remoto além do origin, a mescla nega",
     NOME_DA_RAIZ_COM_OUTRO_REMOTO, NOME_DA_RAIZ_COM_OUTRO_REMOTO,
     "gh pr merge 8 --merge", TRECHO_DE_PUBLICAR_E_DO_DONO,
     SEM_AMBIENTE_A_MAIS),
)
FALHA_DA_MESCLA_PELO_ALVO = (
    "  [a mescla segue a chave do alvo] {} — em {}: esperava {!r}, saiu {!r}")


def repositorio_de_prova_com_remotos(onde: Path, *remotos: str) -> Path:
    repositorio_de_prova(onde, BRANCH_DE_TRABALHO_DO_TESTE)
    for remoto in remotos:
        subprocess.run(["git", "-C", str(onde), "remote", "add", remoto,
                        REMOTO_DE_TESTE.format(onde.name + "-" + remoto)],
                       check=True,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return onde


def raiz_de_prova_que_liga_a_mescla(onde: Path, *remotos: str) -> Path:
    repositorio_de_prova_com_remotos(onde, *remotos)
    (onde / ARQUIVO_CONFIGURACAO).write_text(json.dumps(
        {CHAVE_DAS_AUTORIZACOES: PERMITE_A_MESCLA}), encoding="utf-8")
    return onde


def _a_mescla_segue_a_chave_do_alvo(falhas):
    with tempfile.TemporaryDirectory(prefix="vetar-mescla-") as pasta:
        raiz = Path(pasta).resolve()
        atlas = raiz_de_prova_que_liga_a_mescla(
            raiz / NOME_DA_RAIZ_DA_PROVA, REMOTO_QUE_A_MESCLA_ACEITA)
        worktree = raiz / NOME_DA_WORKTREE_DA_RAIZ
        subprocess.run(["git", "-C", str(atlas), "worktree", "add", "-q",
                        "--detach", str(worktree)], check=True,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
        (worktree / "nucleo").mkdir(exist_ok=True)
        (worktree / ARQUIVO_CONFIGURACAO).write_text(json.dumps(
            {CHAVE_DAS_AUTORIZACOES: PERMITE_A_MESCLA}), encoding="utf-8")
        raiz_de_prova_que_liga_a_mescla(
            raiz / NOME_DA_RAIZ_COM_OUTRO_REMOTO, REMOTO_QUE_A_MESCLA_ACEITA,
            "upstream")
        for nome in (NOME_DO_VIZINHO_DA_PROVA,
                     NOME_DO_CLONE_SO_LEITURA_DA_PROVA):
            repositorio_de_prova_com_remotos(raiz / nome,
                                             REMOTO_QUE_A_MESCLA_ACEITA)
        (atlas / ARQUIVO_EXECUTOR).write_text(json.dumps({
            CHAVE_DOS_PROJETOS: {
                "v": {CHAVE_DO_REPOSITORIO: NOME_DO_VIZINHO_DA_PROVA,
                      CHAVE_DAS_AUTORIZACOES_DO_VIZINHO: PERMITE_A_MESCLA},
                "s": {CHAVE_DO_REPOSITORIO: NOME_DO_CLONE_SO_LEITURA_DA_PROVA,
                      CHAVE_DO_SO_LEITURA: True}}}), encoding="utf-8")
        for (rotulo, projeto, nome, comando, esperado,
             ambiente) in CASOS_DA_MESCLA_PELO_ALVO:
            saida = saida_do_gancho_inteiro(raiz / projeto, raiz / nome,
                                            comando, ambiente=ambiente)
            certo = (not saida.strip() if esperado == PASSA_CALADO
                     else esperado in razao_da_negativa(saida))
            if not certo:
                falhas.append(FALHA_DA_MESCLA_PELO_ALVO.format(
                    rotulo, nome, esperado or "calar", saida.strip()[:200]))


def saida_do_gancho_inteiro(projeto_dir: Path, cwd: Path, comando: str,
                            ferramenta: str = FERRAMENTA_BASH,
                            ambiente: dict = None) -> str:
    entrada = json.dumps({"tool_name": ferramenta,
                          "tool_input": {"command": comando},
                          "cwd": str(cwd)})
    r = subprocess.run(
        [sys.executable, str(Path(__file__).resolve())],
        input=entrada, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        env={**os.environ, VARIAVEL_DA_RAIZ_DO_PROJETO: str(projeto_dir),
             **(ambiente or {})})
    return r.stdout


def repositorio_de_prova(onde: Path, branch: str) -> Path:
    onde.mkdir(parents=True, exist_ok=True)
    for argumentos in (("init", "-q", "-b", branch, "."),
                       ("-c", "user.name=Prova", "-c", "user.email=t@t",
                        "commit", "-q", "--allow-empty", "-m", "x")):
        subprocess.run(["git", "-C", str(onde), *argumentos], check=True,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    (onde / "nucleo").mkdir(exist_ok=True)
    return onde


def _o_gh_do_windows_passa_pela_cerca(falhas):
    with tempfile.TemporaryDirectory(prefix="vetar-gh-exe-") as pasta:
        atlas = repositorio_de_prova(Path(pasta).resolve() / "atlas",
                                     BRANCH_DE_TRABALHO_DO_TESTE)
        (atlas / ARQUIVO_CONFIGURACAO).write_text(json.dumps(
            {CHAVE_DAS_AUTORIZACOES: {"commit": True, "push": True}}),
            encoding="utf-8")
        for ferramenta in (FERRAMENTA_BASH, FERRAMENTA_POWERSHELL):
            for rotulo, comando, nega in CASOS_DO_GH_DO_WINDOWS:
                saida = saida_do_gancho_inteiro(atlas, atlas, comando,
                                                ferramenta)
                if (DECISAO_DE_NEGAR in saida) != nega:
                    falhas.append(FALHA_DO_GH_DO_WINDOWS.format(
                        rotulo, ferramenta, "negar" if nega else "calar",
                        saida.strip()[:160]))


def _o_portao_le_a_palavra_como_o_shell(falhas):
    for rotulo, comando, esperado in CASOS_DO_PORTAO:
        saiu = comando_sem_git_nem_gh(comando)
        if saiu != esperado:
            falhas.append(FALHA_DO_PORTAO.format(
                rotulo, esperado, saiu, comando))


def _o_encadeamento_le_o_escape_do_shell(falhas):
    for rotulo, comando, esperado in CASOS_DO_ENCADEAMENTO:
        saiu = a_linha_so_encadeia(comando)
        if saiu != esperado:
            falhas.append(FALHA_DO_ENCADEAMENTO.format(
                rotulo, esperado, saiu, comando))


def _o_cadastro_guarda_a_integracao(falhas):
    import subprocess as _subprocess
    import tempfile as _tempfile

    def _git(onde, *args):
        _subprocess.run(["git", "-C", str(onde), "-c", "user.name=Prova",
                         "-c", "user.email=t@t", *args],
                        check=True, capture_output=True, text=True,
                        encoding="utf-8", errors="replace")

    def _hook(projeto_dir, cwd, comando):
        entrada = json.dumps({"tool_input": {"command": comando},
                              "cwd": str(cwd)})
        r = _subprocess.run(
            [sys.executable, str(Path(__file__).resolve())],
            input=entrada, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            env={**os.environ, VARIAVEL_DA_RAIZ_DO_PROJETO: str(projeto_dir)})
        return r.stdout

    with _tempfile.TemporaryDirectory(prefix="vetar-cadastro-") as pasta:
        raiz = Path(pasta).resolve()
        pastas = {nome: raiz / nome for nome in (
            "atlas", "atlas-destacada", "vizinho", "vizinho-2", "vizinho-3",
            "herdeiro", "estranho")}
        for nome in ("atlas", "vizinho", "herdeiro", "estranho"):
            pastas[nome].mkdir()
            _git(pastas[nome], "init", "-q", "-b", "homolog", ".")
            _git(pastas[nome], "commit", "-q", "--allow-empty", "-m", "x")
        atlas = pastas["atlas"]
        (atlas / "nucleo").mkdir()
        (atlas / ARQUIVO_CONFIGURACAO).write_text(json.dumps(
            {CHAVE_DAS_AUTORIZACOES: {"commit": True}}), encoding="utf-8")
        _git(atlas, "add", ARQUIVO_CONFIGURACAO)
        _git(atlas, "commit", "-q", "-m", "configuracao")
        _git(atlas, "remote", "add", "origin", REMOTO_DE_TESTE.format("atlas"))
        _git(atlas, "worktree", "add", "-q", "--detach",
             str(pastas["atlas-destacada"]))
        vizinho = pastas["vizinho"]
        _git(vizinho, "remote", "add", "origin",
             REMOTO_DE_TESTE.format("vizinho"))
        _git(vizinho, "branch", "issue/1-x")
        _git(vizinho, "branch", "develop")
        _git(vizinho, "worktree", "add", "-q", str(pastas["vizinho-2"]),
             "issue/1-x")
        _git(vizinho, "worktree", "add", "-q", str(pastas["vizinho-3"]),
             "develop")
        (atlas / ARQUIVO_EXECUTOR).write_text(json.dumps({
            CHAVE_DAS_BRANCHES_DO_CADASTRO: {CHAVE_DA_BASE: "homolog",
                                             CHAVE_DA_INTEGRACAO: "homolog"},
            CHAVE_DOS_PROJETOS: {
                "v": {CHAVE_DO_REPOSITORIO: "vizinho",
                      CHAVE_DAS_BRANCHES_DO_CADASTRO: {
                          CHAVE_DA_BASE: "develop",
                          CHAVE_DA_INTEGRACAO: "homolog"},
                      CHAVE_DAS_AUTORIZACOES_DO_VIZINHO: {"commit": True}},
                "h": {CHAVE_DO_REPOSITORIO: "herdeiro",
                      CHAVE_DAS_AUTORIZACOES_DO_VIZINHO: {"commit": True}},
            }}), encoding="utf-8")
        (pastas["atlas-destacada"] / ARQUIVO_EXECUTOR).write_text(
            (atlas / ARQUIVO_EXECUTOR).read_text(encoding="utf-8"),
            encoding="utf-8")
        (pastas["estranho"] / "nucleo").mkdir()
        (pastas["estranho"] / ARQUIVO_CONFIGURACAO).write_text(json.dumps(
            {CHAVE_DAS_AUTORIZACOES: {"commit": True}}), encoding="utf-8")

        for (rotulo, da_sessao, onde, comando, nega,
             trechos) in CASOS_DO_CADASTRO:
            saida = _hook(pastas[da_sessao], pastas[onde],
                          comando.format(vizinho=vizinho))
            negou = DECISAO_DE_NEGAR in saida
            faltou_trecho = any(t not in saida for t in trechos)
            if negou != nega or faltou_trecho:
                falhas.append(FALHA_DO_CADASTRO.format(
                    rotulo, "negar citando " + ", ".join(trechos) if nega
                    else "calar", saida.strip()[:240]))

    ensina = recusa_que_ensina_o_caminho(
        MOTIVO_COMMIT_NA_INTEGRACAO.format("homolog"))
    if not all(trecho in ensina for trecho in (
            "Regra 12", "--no-ff", ARQUIVO_EXECUTOR, "regra 4",
            "`conhecimento/`")):
        falhas.append(FALHA_RECUSA_NAO_ENSINA.format(
            "commit direto na integração"))


def _as_duas_recusas_ensinam(falhas):
    por_autorizacao = (RECUSA_POR_AUTORIZACAO.format("empurrar")
                       + MANDA_GRAVAR.format(APRENDIZADO_DA_AUTORIZACAO))
    por_branch = (RECUSA_POR_BRANCH_PROTEGIDA.format("apagar")
                  + MANDA_GRAVAR.format(APRENDIZADO_DA_BRANCH))
    if not ("Regra 9" in por_autorizacao
            and ARQUIVO_CONFIGURACAO in por_autorizacao
            and "regra 4" in por_autorizacao
            and "`conhecimento/`" in por_autorizacao):
        falhas.append(FALHA_RECUSA_NAO_ENSINA.format(
            "sem autorização declarada"))
    if not ("Regra 12" in por_branch
            and ARQUIVO_DE_BRANCHES_PROTEGIDAS in por_branch
            and "regra 4" in por_branch
            and "`conhecimento/`" in por_branch):
        falhas.append(FALHA_RECUSA_NAO_ENSINA.format("branch protegida"))


def testar() -> int:
    for nome in VARIAVEIS_QUE_TROCAM_O_REPOSITORIO_DO_GH:
        os.environ.pop(nome.upper(), None)
    protegidas = set(PROTEGIDAS_EMBUTIDAS)
    raiz = Path.cwd()
    falhas = []
    fora = BRANCH_DE_TRABALHO_DO_TESTE
    for rotulo, comando in BARRA:
        if not motivo_da_recusa(comando, protegidas, raiz, AUTORIZA_TUDO, fora):
            falhas.append(FALHA_DEVIA_BARRAR.format(rotulo, comando))
    for rotulo, comando in DEIXA_PASSAR:
        motivo = motivo_da_recusa(comando, protegidas, raiz, AUTORIZA_TUDO, fora)
        if motivo:
            falhas.append(FALHA_DEVIA_PASSAR.format(rotulo, comando, motivo))
    for rotulo, comando in BARRA_NO_POWERSHELL:
        if not motivo_da_recusa(comando, protegidas, raiz, AUTORIZA_TUDO,
                                fora, ferramenta=FERRAMENTA_POWERSHELL):
            falhas.append(FALHA_DEVIA_BARRAR.format(rotulo, comando))
    for rotulo, comando in DEIXA_PASSAR_NO_POWERSHELL:
        motivo = motivo_da_recusa(comando, protegidas, raiz, AUTORIZA_TUDO,
                                  fora, ferramenta=FERRAMENTA_POWERSHELL)
        if motivo:
            falhas.append(FALHA_DEVIA_PASSAR.format(rotulo, comando, motivo))
    for rotulo, comando in SO_PEDEM:
        if motivo_da_recusa(comando, protegidas, raiz, None, fora):
            falhas.append(FALHA_SO_PEDE_E_BARROU.format(rotulo))
    for rotulo, comando in PUBLICAR_E_DO_DONO:
        for leitura, permitido in (("sem autorização", None),
                                   ("com tudo ligado", AUTORIZA_TUDO)):
            motivo = motivo_da_recusa(comando, protegidas, raiz, permitido,
                                      fora)
            if motivo != MOTIVO_PUBLICAR:
                falhas.append(FALHA_PUBLICAR_LIBERADO.format(
                    leitura, rotulo, motivo))
    for rotulo, comando in MESCLA_DA_CASA:
        for leitura, permitido, liberada in (
                ("sem autorização", None, False),
                ("com commit e push, sem a chave", PERMITE_COMMIT_E_PUSH,
                 False),
                ("com a chave ligada", PERMITE_A_MESCLA, True)):
            motivo = motivo_da_recusa(comando, protegidas, raiz, permitido,
                                      fora)
            certo = (not motivo if liberada
                     else TRECHO_DA_AUTORIZACAO_DA_MESCLA in (motivo or ""))
            if not certo:
                falhas.append(FALHA_MESCLA_DA_CASA.format(leitura, rotulo,
                                                          motivo))
    recusa_da_mescla = recusa_que_ensina_o_caminho(MOTIVO_SEM_AUTORIZACAO.format(
        ACAO_MESCLAR, ACAO_MESCLAR, ARQUIVO_CONFIGURACAO))
    if (TRECHO_DA_DECISAO_DO_DONO not in recusa_da_mescla
            or TRECHO_QUE_MANDA_LIGAR_A_CHAVE in recusa_da_mescla.lower()):
        falhas.append(FALHA_RECUSA_DA_MESCLA)
    recusa_de_publicar = recusa_que_ensina_o_caminho(MOTIVO_PUBLICAR)
    if (TRECHO_DE_PUBLICAR_E_DO_DONO not in recusa_de_publicar
            or TRECHO_QUE_MANDA_LIGAR_A_CHAVE in recusa_de_publicar.lower()):
        falhas.append(FALHA_RECUSA_DE_PUBLICAR)
    for rotulo, comando in EMPURRAM_PELO_SERVIDOR:
        liberado = motivo_da_recusa(comando, protegidas, raiz,
                                    PERMITE_COMMIT_E_PUSH, fora)
        if liberado:
            falhas.append(FALHA_EMPURRA_PELO_SERVIDOR.format(
                rotulo, "com commit e push ligados devia passar", liberado))
        negado = motivo_da_recusa(comando, protegidas, raiz, None, fora) or ""
        if TRECHO_DA_AUTORIZACAO_DO_PUSH not in negado:
            falhas.append(FALHA_EMPURRA_PELO_SERVIDOR.format(
                rotulo, "sem autorização devia negar citando "
                + TRECHO_DA_AUTORIZACAO_DO_PUSH, negado))
    for rotulo, comando in REESCREVEM_PELO_SERVIDOR:
        motivo = motivo_da_recusa(comando, protegidas, raiz, AUTORIZA_TUDO,
                                  fora)
        recusa = recusa_que_ensina_o_caminho(motivo) if motivo else ""
        if (motivo != MOTIVO_REBASE_PELO_SERVIDOR
                or ARQUIVO_DE_BRANCHES_PROTEGIDAS in recusa):
            falhas.append(FALHA_REBASE_PELO_SERVIDOR.format(rotulo, motivo))

    for rotulo, comando in BARRA_SEM_AUTORIZACAO:
        if not motivo_da_recusa(comando, protegidas, raiz, None, fora):
            falhas.append(FALHA_DEVIA_BARRAR_SEM_AUTORIZACAO.format(rotulo))
        if motivo_da_recusa(comando, protegidas, raiz, AUTORIZA_TUDO, fora):
            falhas.append(FALHA_DEVIA_PASSAR_COM_AUTORIZACAO.format(rotulo))
    if not motivo_da_recusa(FORCA_EM_PROTEGIDA, protegidas, raiz,
                            AUTORIZA_TUDO, fora):
        falhas.append(FALHA_FORCA_MESMO_AUTORIZADO)

    declaradas_do_merge = set(BRANCHES_POR_INCORPORACAO_DO_TESTE)
    sabidas = set(BRANCHES_CONHECIDAS_DO_TESTE)
    for rotulo, comando in SAI_DA_PROTEGIDA_ANTES_DE_GRAVAR:
        for onde in declaradas_do_merge:
            if motivo_da_recusa(comando, protegidas, raiz, AUTORIZA_TUDO,
                                onde, declaradas_do_merge, sabidas):
                falhas.append(
                    FALHA_SAIU_DA_PROTEGIDA_E_BARROU.format(rotulo))
    for rotulo, comando in ENTRA_NA_PROTEGIDA_E_GRAVA:
        if not motivo_da_recusa(comando, protegidas, raiz, AUTORIZA_TUDO,
                                "main", declaradas_do_merge, sabidas):
            falhas.append(
                FALHA_ENTROU_NA_PROTEGIDA_E_PASSOU.format(rotulo))
    for rotulo, comando in RESTAURA_ARQUIVO_E_NAO_TROCA_DE_BRANCH:
        if motivo_da_recusa(comando, protegidas, raiz, AUTORIZA_TUDO,
                            fora, declaradas_do_merge, sabidas):
            falhas.append(FALHA_RESTAURO_VIROU_TROCA.format(rotulo))
    if motivo_da_recusa("git checkout arquivo.txt && git commit -m x",
                        protegidas, raiz, AUTORIZA_TUDO, "main",
                        declaradas_do_merge, sabidas) is None:
        falhas.append(FALHA_ARQUIVO_VIROU_BRANCH)
    for rotulo, comando in GIT_MERGE_NAO_E_PUBLICAR:
        if motivo_da_recusa(comando, protegidas, raiz, AUTORIZA_TUDO,
                            fora, declaradas_do_merge):
            falhas.append(FALHA_MERGE_LOCAL_BARRADO.format(rotulo))
    ALVOS_POR_EXPANSAO = (
        ("variável simples", 'git -C "$WT" commit -m x', "$WT"),
        ("variável entre chaves", "git -C ${RAIZ} push origin main", "${RAIZ}"),
        ("variável do outro shell", "git -C %RAIZ% push origin main", "%RAIZ%"),
        ("substituição de comando", "git -C $(pwd) push origin main", "$(pwd)"),
        ("cd por variável", 'cd "$WT" && git commit -m x', "$WT"),
    )
    for rotulo, comando, esperado in ALVOS_POR_EXPANSAO:
        if expansao_que_o_gancho_nao_resolve(comando) != esperado:
            falhas.append(FALHA_EXPANSAO_NAO_VISTA.format(
                rotulo, comando, expansao_que_o_gancho_nao_resolve(comando),
                esperado))
    ALVOS_LITERAIS = (
        ("caminho absoluto no -C", "git -C /tmp/x push origin main"),
        ("caminho relativo no -C", "git -C ../vizinho push origin main"),
        ("sem alvo nenhum", "git push origin main"),
    )
    for rotulo, comando in ALVOS_LITERAIS:
        if expansao_que_o_gancho_nao_resolve(comando):
            falhas.append(FALHA_LITERAL_ACUSADO.format(rotulo, comando))
    if ("protegida" in RECUSA_SEM_MEDIR_O_ALVO
            or "main" in RECUSA_SEM_MEDIR_O_ALVO):
        falhas.append(FALHA_RECUSA_INVENTA_RAZAO)

    with tempfile.TemporaryDirectory(prefix="alvo-do-comando-") as pasta:
        vizinho = (Path(pasta) / "outro-repo").resolve()
        (vizinho / PASTA_DO_GIT).mkdir(parents=True)
        daqui = str(Path.cwd())
        pelo_cd = repositorio_que_o_comando_muda(
            daqui, raiz, f"cd {vizinho} && git merge origin/main")
        separado = repositorio_que_o_comando_muda(
            daqui, raiz, f"git -C {vizinho} merge origin/main")
        colado = repositorio_que_o_comando_muda(
            daqui, raiz, f"git -C{vizinho} merge origin/main")
        if not (pelo_cd == separado == colado == vizinho):
            falhas.append(FALHA_BANDEIRA_C_IGNORADA.format(
                vizinho, pelo_cd, separado, colado))
    for rotulo, comando in GIT_MERGE_EM_PROTEGIDA:
        for onde in declaradas_do_merge:
            if not motivo_da_recusa(comando, protegidas, raiz,
                                    AUTORIZA_TUDO, onde,
                                    declaradas_do_merge):
                falhas.append(
                    FALHA_MERGE_EM_PROTEGIDA_PASSOU.format(rotulo))
    for rotulo, molde in AVANCA_O_PONTEIRO_SEM_GRAVAR:
        for onde in declaradas_do_merge:
            comando = molde.format(onde)
            if motivo_da_recusa(comando, protegidas, raiz, AUTORIZA_TUDO,
                                onde, declaradas_do_merge):
                falhas.append(FALHA_AVANCO_BARRADO.format(rotulo, comando))
    for rotulo, comando in GH_MERGE_CONTINUA_SENDO_PUBLICAR:
        if not motivo_da_recusa(comando, protegidas, raiz, None, fora):
            falhas.append(FALHA_GH_MERGE_PASSOU.format(rotulo))

    declaradas = set(BRANCHES_POR_INCORPORACAO_DO_TESTE)
    for rotulo, comando in GRAVA_EM_PROTEGIDA:
        for onde in declaradas:
            if not motivo_da_recusa(comando, protegidas, raiz,
                                    AUTORIZA_TUDO, onde, declaradas):
                falhas.append(FALHA_GRAVOU_EM_PROTEGIDA.format(rotulo, onde))
        if motivo_da_recusa(comando, protegidas, raiz, AUTORIZA_TUDO, fora,
                            declaradas):
            falhas.append(FALHA_BARROU_NA_DE_TRABALHO.format(rotulo))
        if motivo_da_recusa(comando, protegidas, raiz, AUTORIZA_TUDO,
                            BRANCH_DE_INTEGRACAO_DO_TESTE, declaradas):
            falhas.append(FALHA_BARROU_NA_INTEGRACAO.format(rotulo))

    _as_duas_recusas_se_distinguem(falhas)
    _as_duas_recusas_ensinam(falhas)
    _a_branch_julgada_e_a_do_alvo(falhas)
    _o_init_encadeado_e_julgado_no_bercario(falhas)
    _o_cadastro_guarda_a_integracao(falhas)
    _o_encadeamento_le_o_escape_do_shell(falhas)
    _o_portao_le_a_palavra_como_o_shell(falhas)
    _o_gh_do_windows_passa_pela_cerca(falhas)
    _publicar_nao_se_liga_pelo_arquivo(falhas)
    _a_mescla_segue_a_chave_do_alvo(falhas)

    total = (6 + len(CASOS_DO_CADASTRO) + 1 + len(CASOS_DO_ENCADEAMENTO)
             + len(CASOS_DO_PORTAO) + len(CASOS_DO_GH_DO_WINDOWS) * 2
             + len(PUBLICAR_E_DO_DONO) * 2 + 1
             + len(MESCLA_DA_CASA) * 3 + 1 + len(CASOS_DA_MESCLA_PELO_ALVO)
             + len(EMPURRAM_PELO_SERVIDOR) * 2 + len(REESCREVEM_PELO_SERVIDOR)
             + 2 + len(CASOS_DE_PUBLICAR_PELO_ARQUIVO) * 2
             + len(CASOS_DE_PUBLICAR_ANTES_DO_ALVO)
             + len(CASOS_DO_REBASE_ANTES_DO_ALVO)
             + len(GRAVA_EM_PROTEGIDA)
             * (len(BRANCHES_POR_INCORPORACAO_DO_TESTE) + 2)
             + len(SO_PEDEM) + len(BARRA) + len(DEIXA_PASSAR)
             + len(BARRA_NO_POWERSHELL) + len(DEIXA_PASSAR_NO_POWERSHELL)
             + len(BARRA_SEM_AUTORIZACAO) * 2 + 1
             + len(GIT_MERGE_NAO_E_PUBLICAR)
             + (len(GIT_MERGE_EM_PROTEGIDA)
                + len(AVANCA_O_PONTEIRO_SEM_GRAVAR))
             * len(BRANCHES_POR_INCORPORACAO_DO_TESTE)
             + len(GH_MERGE_CONTINUA_SENDO_PUBLICAR)) + 7
    if falhas:
        print(RESUMO_FALHOU.format(len(falhas), total))
        print("\n".join(falhas))
        return 1
    print(RESUMO_OK.format(total, len(BARRA) + len(BARRA_NO_POWERSHELL),
                           len(DEIXA_PASSAR)
                           + len(DEIXA_PASSAR_NO_POWERSHELL)))
    return 0


def main() -> int:
    try:
        return decidir()
    except Exception as falha:
        return recusa_por_nao_entender(falha)


if __name__ == "__main__":
    sys.exit(testar() if BANDEIRA_DE_TESTE in sys.argv else main())
