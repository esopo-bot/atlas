import json
import os
import re
import sys
from collections import namedtuple
from pathlib import Path

Acao = namedtuple("Acao", "descricao repositorio alvo operacao_reconhecida",
                  defaults=(False,))
Recusa = namedtuple("Recusa", "descricao repositorio cadastro_medido")
CadastroDosVizinhos = namedtuple("CadastroDosVizinhos", "nomes medido")
AQUI_MESMO = "."

ARQUIVO_EXECUTOR = "nucleo/executor.json"
CHAVE_DOS_PROJETOS = "projetos"
CHAVE_DO_REPOSITORIO = "repositorio"
CHAVE_DO_SO_LEITURA = "somente_leitura"
MARCA_DE_MOLDE_NAO_PREENCHIDO = "${"
PASTA_DO_GIT = ".git"

FERRAMENTAS_DE_ESCRITA = ("Write", "Edit", "NotebookEdit")
CAMPOS_DE_CAMINHO = ("file_path", "notebook_path")

REDIRECIONAMENTO_DE_SHELL = re.compile(r">>?\s*([^\s;|&<>]+)")
ASPA_SIMPLES = "'"
ASPA_DUPLA = '"'
ASPAS = "\"'"
CONTRABARRA = "\\"
ABRE_ASPA_ANSI = "$'"
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

COMANDO_CD = "cd"
NOMES_DO_GIT = ("git", "git.exe")
NOME_DO_GH = "gh"
EXTENSAO_EXE = ".exe"

BANDEIRAS_GLOBAIS_SIMPLES = {"--no-pager", "--paginate", "-p", "--bare",
                             "--literal-pathspecs"}
BANDEIRAS_GLOBAIS_QUE_COMEM_O_TOKEN_SEGUINTE = {
    "-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path",
    "-R", "--repo"}
BANDEIRAS_QUE_CARREGAM_PROSA = ("-m", "-am", "--message", "-F", "--file")
BANDEIRA_DO_DIRETORIO_DO_GIT = ("-C",)
BANDEIRA_DA_PASTA_DO_GIT = ("--git-dir",)
BANDEIRA_DA_ARVORE_DE_TRABALHO = ("--work-tree",)
BANDEIRAS_DO_REPOSITORIO_DO_GH = ("-R", "--repo")

VERBOS_DO_GIT_QUE_ESCREVEM = {
    "add", "am", "apply", "checkout", "cherry-pick", "clean", "clone",
    "commit", "init", "merge", "mv", "push", "rebase", "reset", "restore",
    "revert", "rm", "stash", "switch"}
VERBOS_DO_GIT_QUE_MATERIALIZAM_ARQUIVO = {
    "am", "apply", "checkout", "cherry-pick", "clean", "merge", "mv", "pull",
    "rebase", "reset", "restore", "revert", "rm", "stash", "switch"}
VERBO_DO_GIT_QUE_CRIA_REPOSITORIO = "init"
VERBO_DO_GIT_QUE_CLONA = "clone"
BANDEIRAS_DO_VERBO_QUE_COMEM_O_TOKEN_SEGUINTE = {
    "--depth", "--branch", "-b", "--origin", "-o", "--reference",
    "--reference-if-able", "--separate-git-dir", "--template", "--config",
    "-c", "--jobs", "-j", "--filter", "--shallow-since", "--shallow-exclude",
    "--upload-pack", "-u", "--server-option", "--initial-branch",
    "--object-format", "--ref-format", "--bundle-uri", "--revision"}
VERBOS_DO_GIT_QUE_SO_ESCREVEM_COM_ARGUMENTO = {
    "branch": {"--show-current", "--list", "-l", "-a", "--all", "-r",
               "--remotes", "-v", "-vv", "--verbose", "--contains",
               "--merged", "--no-merged", "--points-at"},
    "tag": {"--list", "-l", "-n", "--contains", "--points-at", "--merged"},
}
SUBVERBOS_DO_GH_QUE_LEEM = {
    "pr": {"view", "list", "status", "diff", "checks"},
    "issue": {"view", "list", "status"},
    "release": {"view", "list", "download"},
    "repo": {"view", "list"},
}

SUBVERBOS_DO_GH_QUE_CONVERSAM = {
    "issue": {"comment", "create", "edit"},
    "pr": {"comment", "close"},
}

COMANDOS_QUE_ESCREVEM_NOS_ARGUMENTOS = ("rm", "rmdir", "mv", "tee", "touch",
                                        "mkdir", "truncate", "chmod", "chown")
COMANDOS_QUE_ESCREVEM_NO_ULTIMO = ("cp", "ln", "install", "rsync")
COMANDOS_QUE_ESCREVEM_NO_LUGAR = ("sed", "perl")
COMANDOS_QUE_ESCREVEM_NA_OPCAO = {"curl": ("-o", "--output"),
                                  "wget": ("-O", "--output-document")}
LETRA_DE_ESCRITA_NO_LUGAR = "i"
PREFIXO_DE_OPCAO = "-"
BANDEIRA_LONGA = "--"
IGUAL = "="
COMANDO_DD = "dd"
PREFIXO_DA_SAIDA_DO_DD = "of="
BANDEIRA_DE_ESCRITA_NO_LUGAR = "-i"
BANDEIRA_DE_ESCRITA_NO_LUGAR_POR_EXTENSO = "--in-place"
FIM_DAS_OPCOES = "--"
LETRAS_QUE_TRAZEM_O_ROTEIRO = {"sed": "ef", "perl": "eE"}
LETRAS_QUE_TRAZEM_OUTRO_VALOR = {"sed": "l", "perl": ""}
NOMES_LONGOS_QUE_TRAZEM_O_ROTEIRO = {"sed": {"expression": "e", "file": "f"},
                                     "perl": {}}
PROGRAMAS_CUJAS_OPCOES_ACABAM_NO_PRIMEIRO_OPERANDO = ("perl",)
LETRA_DO_ROTEIRO_EM_ARQUIVO = "f"
PROGRAMAS_CUJO_ROTEIRO_ESCREVE_ARQUIVO = ("sed",)
MARCA_DE_ESCRITA_NO_ROTEIRO = re.compile(
    r"(?<![A-Za-z\\])[wW]|(?<=[^A-Za-z0-9\s\\])[gpiImMe0-9]*w")
TETO_DO_ROTEIRO_EM_ARQUIVO = 65536
QUEBRA_DE_LINHA = "\n"
ESCAPE_DO_SED = "\\"
ENDERECO_POR_EXPRESSAO = "/"
CARACTERES_DE_ENDERECO_POR_NUMERO = "0123456789$~+"
BANDEIRAS_DO_ENDERECO = "IM"
SEPARADOR_DE_ENDERECOS = ","
NEGACAO_DO_ENDERECO = "!"
ESPACOS_DO_SED = " \t"
ENTRE_COMANDOS_DO_SED = " \t\n;"
FIM_DO_ROTULO = ";\n"
DIGITOS = "0123456789"
COMANDOS_DO_SED_QUE_ESCREVEM = "wW"
COMANDOS_DO_SED_COM_DUAS_PARTES = "sy"
COMANDO_DO_SED_QUE_SUBSTITUI = "s"
BANDEIRAS_DO_SUBSTITUIR = "gpiImMe0123456789"
BANDEIRA_DO_SUBSTITUIR_QUE_ESCREVE = "w"
COMANDOS_DO_SED_COM_O_RESTO_DA_LINHA = "aicrRe#"
COMANDOS_DO_SED_COM_ROTULO = "btT:v"
COMANDOS_DO_SED_COM_NUMERO = "qQlL"
COMANDOS_DO_SED_SEM_ARGUMENTO = "=dDgGhHnNpPxzF{}"
ABRE_COLCHETE = "["
FECHA_COLCHETE = "]"
NEGACAO_DO_COLCHETE = "^"
ABERTURAS_DE_CLASSE = ("[:", "[.", "[=")
LEITURAS_DO_COLCHETE = (True, False)
MODULO_QUE_DESEMBRULHA = "desembrulhar-comando.py"
CACHE_DO_DESEMBRULHADOR = []
MARCADORES_DE_EXPANSAO = ("$", "`", "%")
NOME_COMO_PASTA_NO_TEXTO = r"(?:^|[\s\"'=/\\]){}(?=[/\\\s\"';]|$)"

VARIAVEL_DA_RAIZ_DO_PROJETO = "CLAUDE_PROJECT_DIR"
NIVEIS_DO_GANCHO_ATE_A_RAIZ = 2

EVENTO_ANTES_DA_FERRAMENTA = "PreToolUse"
DECISAO_DE_NEGAR = "deny"
BANDEIRA_DE_TESTE = "--testar"
SEM_VERBO = -1
SEM_NOME = ""
SILENCIO = 0
CADASTRO_NAO_MEDIDO = CadastroDosVizinhos(frozenset(), False)
RECUSA_SEM_ENTENDER = (
    "Este gancho não entendeu o pedido, e por isso recusa em vez de liberar: "
    "{} — {}. Quem veta e não consegue julgar não pode dizer sim: a parede "
    "sumiria em silêncio, e o verde passaria a significar `ninguém olhou`. "
    "Se o pedido é legítimo, conserte o gancho ou desligue-o em "
    ".claude/settings.json — o caminho nunca é atravessar por aqui."
)
MANDA_GRAVAR = (
    "\nGrave o aprendizado antes de tentar de novo — regra 4, a memória "
    "mora no disco, e recusa que a próxima sessão repete não ensinou "
    "nada. A linha, em `conhecimento/`:\n"
    "    {}"
)
APRENDIZADO = (
    "repositório declarado somente leitura não recebe escrita: a "
    "mudança vira pedido de incorporação como sugestão, que a sessão abre "
    "só depois do sim expresso do dono, e que ele aprova."
)

ACAO_ESCREVER_EM = "escrever em {!r}"
ACAO_RODAR = "rodar `{}`"
RECUSA_SEM_CADASTRO = (
    "Regra 9 da camada: isto quer {}, e o alvo mora no repositório {!r}, que "
    "não é este. O cadastro de vizinhos não pôde ser lido em {}, então esta "
    "cerca NÃO MEDIU se aquele território é somente leitura — e quem não "
    "mede não libera: conjunto vazio significaria `nada é protegido`, e a "
    "parede cairia em silêncio. Os caminhos: ponha o cadastro no lugar, com "
    "`{}` declarando cada vizinho, ou escreva dentro desta árvore. Ler "
    "continua livre."
)
RECUSA = (
    "Regra 9 da camada: isto quer {}. O repositório {!r} está declarado "
    "somente leitura, "
    "sempre: dele se lê, nele não se escreve. Ele é território de outra "
    "pessoa, e mudança aplicada por cima dela chega sem a revisão de quem "
    "responde pelo que quebrar. O caminho que existe é propor, não aplicar: "
    "a mudança vira um pedido de incorporação como sugestão, com {} "
    "marcado para revisão, que a sessão abre só depois do sim expresso do "
    "dono, e que ele aprova. Ler continua livre: `cat`, `git log`, `git show`, `grep`, "
    "`gh issue view` e `gh pr view` passam. Para mudar a lista: "
    "`{}` em {}."
)

AVISO_DO_VIZINHO_SO_NOMEADO = (
    "AVISO, não recusa: o comando escreve num destino que a cerca não "
    "consegue resolver e nomeia o vizinho somente leitura `{}`. Se o destino "
    "cair dentro dele, a escrita é proibida: confira o destino antes de "
    "seguir, e prefira o caminho por extenso, que a cerca sabe julgar.")

FALHA_BARRA = "BARRA [{}]: deixou passar"
FALHA_DEIXA_PASSAR = "DEIXA_PASSAR [{}]: barrou — {}"
FALHA_AVISOU_SEM_MOTIVO = "DEIXA_PASSAR [{}]: passou, mas com aviso"
FALHA_NEGOU_O_QUE_SO_AVISA = "SO_AVISA [{}]: negou o que só se avisa"
FALHA_NAO_AVISOU = "SO_AVISA [{}]: passou calado, sem nomear o vizinho"
FALHA_COMPORTAMENTO = "COMPORTAMENTO [{}]"
LINHA_DE_FALHA = "FALHOU: {}"
RESUMO_FALHOU = "FALHOU: {} de {} casos"
RESUMO_OK = ("OK: {} casos — {} barrados, {} avisados, {} liberados, "
             "{} de comportamento")


CHAVE_DO_REVISOR = "revisor"
SEM_REVISOR = "quem cuida daquele território"


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


def revisor_de(raiz: Path, repositorio: str) -> str:
    try:
        dado = json.loads(
            (raiz / ARQUIVO_EXECUTOR).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return SEM_REVISOR
    projetos = (dado or {}).get(CHAVE_DOS_PROJETOS) or {}
    if not isinstance(projetos, dict):
        return SEM_REVISOR
    for projeto in projetos.values():
        if not isinstance(projeto, dict):
            continue
        if projeto.get(CHAVE_DO_REPOSITORIO) != repositorio:
            continue
        nome = projeto.get(CHAVE_DO_REVISOR)
        return f"`{nome}`" if isinstance(nome, str) and nome else SEM_REVISOR
    return SEM_REVISOR


def cadastro_dos_vizinhos(raiz: Path) -> CadastroDosVizinhos:
    try:
        dado = json.loads(
            (raiz / ARQUIVO_EXECUTOR).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return CADASTRO_NAO_MEDIDO
    if not isinstance(dado, dict):
        return CADASTRO_NAO_MEDIDO
    projetos = dado.get(CHAVE_DOS_PROJETOS)
    if projetos is None:
        return CadastroDosVizinhos(frozenset(), True)
    if not isinstance(projetos, dict):
        return CADASTRO_NAO_MEDIDO
    nomes = set()
    for projeto in projetos.values():
        if isinstance(projeto, str):
            continue
        if not isinstance(projeto, dict):
            return CADASTRO_NAO_MEDIDO
        if not projeto.get(CHAVE_DO_SO_LEITURA):
            continue
        nome = projeto.get(CHAVE_DO_REPOSITORIO)
        if not isinstance(nome, str) or not nome.strip() \
                or MARCA_DE_MOLDE_NAO_PREENCHIDO in nome:
            return CADASTRO_NAO_MEDIDO
        nomes.add(nome.strip().lower())
    return CadastroDosVizinhos(frozenset(nomes), True)


def nomes_somente_leitura(raiz: Path) -> frozenset:
    return cadastro_dos_vizinhos(raiz).nomes


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


def sem_o_par_de_aspas_que_envolve(token: str) -> str:
    for aspa in (ASPA_DUPLA, ASPA_SIMPLES):
        if len(token) >= 2 and token.startswith(aspa) and token.endswith(aspa):
            return token[1:-1]
    return token


def partir_em_tokens(segmento: str) -> list:
    import shlex
    analisador = shlex.shlex(segmento, posix=True)
    analisador.whitespace_split = True
    analisador.escape = ""
    analisador.commenters = ""
    try:
        return list(analisador)
    except ValueError:
        return [sem_o_par_de_aspas_que_envolve(t) for t in segmento.split()]


REDIRECIONAMENTO_SOLTO = re.compile(r"^[0-9&]?(>>?|<)$")
REDIRECIONAMENTO_COLADO_AO_ALVO = re.compile(r"^[0-9&]?(>>?|<).+")
ATRIBUICAO_DE_VARIAVEL = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def sem_o_que_o_shell_consome_antes_do_comando(tokens: list) -> list:
    i = 0
    while i < len(tokens):
        if REDIRECIONAMENTO_SOLTO.match(tokens[i]):
            i += 2
        elif REDIRECIONAMENTO_COLADO_AO_ALVO.match(tokens[i]) \
                or ATRIBUICAO_DE_VARIAVEL.match(tokens[i]):
            i += 1
        else:
            break
    return tokens[i:]


def e_git(token: str) -> bool:
    return Path(token.replace("\\", "/")).name.lower() in NOMES_DO_GIT


def e_gh(token: str) -> bool:
    return Path(token).name.lower().removesuffix(EXTENSAO_EXE) == NOME_DO_GH


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


def valor_da_bandeira(tokens: list, bandeiras) -> str:
    i = 1
    while i < len(tokens):
        t = tokens[i]
        if t in bandeiras and i + 1 < len(tokens):
            return tokens[i + 1]
        for bandeira in bandeiras:
            if t.startswith(bandeira + "="):
                return t.split("=", 1)[1]
        i += 1
    return SEM_NOME


def posicionais_depois_do_verbo(tokens: list) -> list:
    i = indice_do_verbo(tokens)
    if i == SEM_VERBO:
        return []
    sobra, come_o_proximo = [], False
    for token in tokens[i + 1:]:
        if come_o_proximo:
            come_o_proximo = False
            continue
        if token.startswith(PREFIXO_DE_OPCAO):
            come_o_proximo = \
                token in BANDEIRAS_DO_VERBO_QUE_COMEM_O_TOKEN_SEGUINTE
            continue
        sobra.append(token)
    return sobra


def sob_o_diretorio_declarado(tokens: list, caminho: str) -> str:
    base = valor_da_bandeira(tokens, BANDEIRA_DO_DIRETORIO_DO_GIT)
    if not base or Path(caminho).is_absolute():
        return caminho
    return (Path(base) / caminho).as_posix()


def alvos_escritos_pelo_git(verbo: str, tokens: list) -> list:
    posicionais = posicionais_depois_do_verbo(tokens)
    if verbo == VERBO_DO_GIT_QUE_CRIA_REPOSITORIO:
        return [sob_o_diretorio_declarado(
            tokens, posicionais[0] if posicionais else AQUI_MESMO)]
    if verbo == VERBO_DO_GIT_QUE_CLONA:
        return [sob_o_diretorio_declarado(
            tokens, posicionais[1] if len(posicionais) > 1 else AQUI_MESMO)]
    alvos = [valor_da_bandeira(tokens, BANDEIRA_DA_PASTA_DO_GIT)
             or valor_da_bandeira(tokens, BANDEIRA_DO_DIRETORIO_DO_GIT)
             or AQUI_MESMO]
    arvore = valor_da_bandeira(tokens, BANDEIRA_DA_ARVORE_DE_TRABALHO)
    if arvore and verbo in VERBOS_DO_GIT_QUE_MATERIALIZAM_ARQUIVO:
        alvos.append(arvore)
    return alvos


def argumento_faz_escrever(verbo: str, resto: list) -> bool:
    de_leitura = VERBOS_DO_GIT_QUE_SO_ESCREVEM_COM_ARGUMENTO[verbo]
    bandeiras = [t for t in resto if t.startswith("-")]
    posicionais = [t for t in resto if not t.startswith("-")]
    if any(b.split("=", 1)[0].lower() not in de_leitura for b in bandeiras):
        return True
    return bool(posicionais) and not bandeiras


def verbo_do_git_que_escreve(tokens: list) -> str:
    i = indice_do_verbo(tokens)
    if i == SEM_VERBO:
        return SEM_NOME
    verbo = tokens[i].lower()
    if verbo in VERBOS_DO_GIT_QUE_ESCREVEM:
        return verbo
    if verbo in VERBOS_DO_GIT_QUE_SO_ESCREVEM_COM_ARGUMENTO:
        return verbo if argumento_faz_escrever(verbo, tokens[i + 1:]) \
            else SEM_NOME
    return SEM_NOME


def subverbo_do_gh_que_escreve(tokens: list) -> str:
    i = indice_do_verbo(tokens)
    if i == SEM_VERBO:
        return SEM_NOME
    verbo = tokens[i].lower()
    if verbo not in SUBVERBOS_DO_GH_QUE_LEEM:
        return SEM_NOME
    posicionais = [t for t in tokens[i + 1:] if not t.startswith("-")]
    subverbo = posicionais[0].lower() if posicionais else SEM_NOME
    if (not subverbo
            or subverbo in SUBVERBOS_DO_GH_QUE_LEEM[verbo]
            or subverbo in SUBVERBOS_DO_GH_QUE_CONVERSAM.get(verbo, ())):
        return SEM_NOME
    return verbo + " " + subverbo


def resolver(caminho: str, onde: str):
    if not caminho:
        return None
    alvo = Path(os.path.expanduser(caminho))
    if not alvo.is_absolute():
        alvo = Path(onde or ".") / alvo
    try:
        return alvo.resolve(strict=False)
    except OSError:
        return None


def repositorio_de(alvo: Path):
    atual = alvo
    while True:
        if (atual / PASTA_DO_GIT).exists():
            return atual
        if atual.parent == atual:
            return None
        atual = atual.parent


def repositorio_do_caminho(caminho: str, onde: str) -> str:
    alvo = resolver(caminho, onde)
    if alvo is None:
        return SEM_NOME
    repositorio = repositorio_de(alvo)
    return repositorio.name.lower() if repositorio else SEM_NOME


def repositorio_do_nome_remoto(valor: str) -> str:
    return valor.strip().rstrip("/").split("/")[-1].lower()


def caminhos_escritos_pelo_segmento(segmento: str, tokens: list,
                                    onde: str) -> list:
    escritos = [m.group(1) for m in REDIRECIONAMENTO_DE_SHELL.finditer(segmento)]
    if not tokens:
        return escritos
    programa = Path(tokens[0].replace("\\", "/")).name.lower()
    posicionais = [t for t in tokens[1:] if not t.startswith("-")]
    if programa in COMANDOS_QUE_ESCREVEM_NOS_ARGUMENTOS:
        escritos += posicionais
    elif programa in COMANDOS_QUE_ESCREVEM_NO_ULTIMO and posicionais:
        escritos.append(posicionais[-1])
    elif programa in COMANDOS_QUE_ESCREVEM_NO_LUGAR and escreve_no_lugar(tokens):
        escritos += arquivos_editados_no_lugar(programa, tokens, onde)
    escritos += caminhos_escritos_na_opcao(programa, tokens)
    escritos += saida_do_dd(programa, tokens)
    return [sem_o_par_de_aspas_que_envolve(e).strip(ASPAS)
            for e in escritos if e]


def escreve_no_lugar(tokens: list) -> bool:
    return any(t == BANDEIRA_DE_ESCRITA_NO_LUGAR_POR_EXTENSO
               or t.startswith(BANDEIRA_DE_ESCRITA_NO_LUGAR)
               or (not t.startswith(BANDEIRA_LONGA)
                   and LETRA_DE_ESCRITA_NO_LUGAR in t[1:])
               for t in tokens[1:] if t.startswith(PREFIXO_DE_OPCAO))


def letra_que_leva_valor(aglomerado: str, letras_com_valor: str):
    for posicao, letra in enumerate(aglomerado):
        if letra == LETRA_DE_ESCRITA_NO_LUGAR:
            return SEM_NOME, SEM_NOME, False
        if letra in letras_com_valor:
            valor = aglomerado[posicao + 1:]
            return letra, valor, bool(valor)
    return SEM_NOME, SEM_NOME, False


def nome_longo_que_traz_o_roteiro(programa: str, token: str):
    nome, igual, valor = token[len(BANDEIRA_LONGA):].partition(IGUAL)
    letra = next((letra for longo, letra
                  in NOMES_LONGOS_QUE_TRAZEM_O_ROTEIRO[programa].items()
                  if nome and longo.startswith(nome)), SEM_NOME)
    return letra, valor, bool(igual)


def opcao_que_leva_valor(programa: str, token: str, letras_com_valor: str):
    if token.startswith(BANDEIRA_LONGA):
        return nome_longo_que_traz_o_roteiro(programa, token)
    return letra_que_leva_valor(token[len(PREFIXO_DE_OPCAO):],
                                letras_com_valor)


def roteiro_que_o_arquivo_traz(caminho: str, onde: str):
    alvo = resolver(caminho, onde)
    try:
        if alvo is None or not alvo.is_file() \
                or alvo.stat().st_size > TETO_DO_ROTEIRO_EM_ARQUIVO:
            return None
        return alvo.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def alvos_depois_de_cada_marca_de_escrita(texto: str) -> list:
    alvos = [texto[marca.end():].split(QUEBRA_DE_LINHA, 1)[0].strip()
             for marca in MARCA_DE_ESCRITA_NO_ROTEIRO.finditer(texto)]
    return [alvo for alvo in alvos if alvo]


def depois_de(texto: str, posicao: int, caracteres: str) -> int:
    while posicao < len(texto) and texto[posicao] in caracteres:
        posicao += 1
    return posicao


def ate_um_de(texto: str, posicao: int, caracteres: str) -> int:
    while posicao < len(texto) and texto[posicao] not in caracteres:
        posicao += 1
    return posicao


def depois_do_colchete(texto: str, posicao: int):
    posicao += texto.startswith(NEGACAO_DO_COLCHETE, posicao)
    posicao += texto.startswith(FECHA_COLCHETE, posicao)
    while posicao < len(texto):
        par = texto[posicao:posicao + 2]
        if texto[posicao] == FECHA_COLCHETE:
            return posicao + 1
        if par in ABERTURAS_DE_CLASSE:
            fim = texto.find(par[1] + FECHA_COLCHETE, posicao + 2)
            if fim < 0:
                return None
            posicao = fim + 2
        else:
            posicao += 1
    return None


def depois_do_delimitado(texto: str, posicao: int, delimitador: str,
                         colchete_conta: bool):
    while posicao is not None and posicao < len(texto):
        if texto[posicao] == ESCAPE_DO_SED:
            posicao += 2
        elif texto[posicao] == delimitador:
            return posicao + 1
        elif colchete_conta and texto[posicao] == ABRE_COLCHETE:
            posicao = depois_do_colchete(texto, posicao + 1)
        else:
            posicao += 1
    return None


def depois_do_endereco(texto: str, posicao: int, colchete_conta: bool):
    if texto.startswith(ESCAPE_DO_SED, posicao):
        delimitador = texto[posicao + 1:posicao + 2]
        posicao = depois_do_delimitado(
            texto, posicao + 2, delimitador, colchete_conta) \
            if delimitador else None
    elif texto.startswith(ENDERECO_POR_EXPRESSAO, posicao):
        posicao = depois_do_delimitado(texto, posicao + 1,
                                       ENDERECO_POR_EXPRESSAO, colchete_conta)
    else:
        return depois_de(texto, posicao, CARACTERES_DE_ENDERECO_POR_NUMERO)
    return None if posicao is None \
        else depois_de(texto, posicao, BANDEIRAS_DO_ENDERECO)


def depois_dos_enderecos(texto: str, posicao: int, colchete_conta: bool):
    posicao = depois_do_endereco(texto, posicao, colchete_conta)
    if posicao is not None \
            and texto.startswith(SEPARADOR_DE_ENDERECOS, posicao):
        posicao = depois_do_endereco(
            texto, depois_de(texto, posicao + 1, ESPACOS_DO_SED),
            colchete_conta)
    if posicao is None:
        return None
    return depois_de(texto, posicao, ESPACOS_DO_SED + NEGACAO_DO_ENDERECO)


def resto_da_linha(texto: str, posicao: int):
    fim = ate_um_de(texto, posicao, QUEBRA_DE_LINHA)
    return texto[posicao:fim].strip(), fim


def argumento_de_duas_partes(comando: str, texto: str, posicao: int,
                             colchete_conta: bool):
    delimitador = texto[posicao:posicao + 1]
    substitui = comando == COMANDO_DO_SED_QUE_SUBSTITUI
    if not delimitador or delimitador in QUEBRA_DE_LINHA + ESCAPE_DO_SED:
        return SEM_NOME, None
    posicao = depois_do_delimitado(texto, posicao + 1, delimitador,
                                   colchete_conta and substitui)
    if posicao is not None:
        posicao = depois_do_delimitado(texto, posicao, delimitador, False)
    if posicao is None or not substitui:
        return SEM_NOME, posicao
    posicao = depois_de(texto, posicao, BANDEIRAS_DO_SUBSTITUIR)
    if texto.startswith(BANDEIRA_DO_SUBSTITUIR_QUE_ESCREVE, posicao):
        return resto_da_linha(texto, posicao + 1)
    return SEM_NOME, posicao


def argumento_do_comando(comando: str, texto: str, posicao: int,
                         colchete_conta: bool):
    if comando in COMANDOS_DO_SED_QUE_ESCREVEM:
        return resto_da_linha(texto, posicao)
    if comando in COMANDOS_DO_SED_COM_DUAS_PARTES:
        return argumento_de_duas_partes(comando, texto, posicao,
                                        colchete_conta)
    if comando in COMANDOS_DO_SED_COM_O_RESTO_DA_LINHA:
        return SEM_NOME, ate_um_de(texto, posicao, QUEBRA_DE_LINHA)
    if comando in COMANDOS_DO_SED_COM_ROTULO:
        return SEM_NOME, ate_um_de(texto, posicao, FIM_DO_ROTULO)
    if comando in COMANDOS_DO_SED_COM_NUMERO:
        return SEM_NOME, depois_de(
            texto, depois_de(texto, posicao, ESPACOS_DO_SED), DIGITOS)
    if comando in COMANDOS_DO_SED_SEM_ARGUMENTO:
        return SEM_NOME, posicao
    return SEM_NOME, None


def alvos_numa_leitura(texto: str, colchete_conta: bool):
    alvos, posicao = [], depois_de(texto, 0, ENTRE_COMANDOS_DO_SED)
    while posicao < len(texto):
        posicao = depois_dos_enderecos(texto, posicao, colchete_conta)
        if posicao is None or posicao >= len(texto):
            return None
        alvo, posicao = argumento_do_comando(texto[posicao], texto,
                                             posicao + 1, colchete_conta)
        if posicao is None:
            return None
        alvos += [alvo] if alvo else []
        posicao = depois_de(texto, posicao, ENTRE_COMANDOS_DO_SED)
    return alvos


def alvos_que_o_roteiro_escreve(texto: str):
    leituras = [alvos_numa_leitura(texto, colchete_conta)
                for colchete_conta in LEITURAS_DO_COLCHETE]
    if None in leituras:
        return None
    return list(dict.fromkeys(
        alvo for leitura in leituras for alvo in leitura))


def escritas_de_dentro_dos_roteiros(programa: str, roteiros: list,
                                    onde: str) -> list:
    if programa not in PROGRAMAS_CUJO_ROTEIRO_ESCREVE_ARQUIVO:
        return []
    escritas = []
    for letra, roteiro in roteiros:
        texto = roteiro_que_o_arquivo_traz(roteiro, onde) \
            if letra == LETRA_DO_ROTEIRO_EM_ARQUIVO else roteiro
        alvos = alvos_que_o_roteiro_escreve(texto) \
            if texto is not None else None
        if alvos is not None:
            escritas += alvos
        elif texto is None:
            escritas.append(roteiro)
        elif na_duvida := alvos_depois_de_cada_marca_de_escrita(texto):
            escritas += [roteiro] + na_duvida
    return escritas


def arquivos_editados_no_lugar(programa: str, tokens: list,
                               onde: str) -> list:
    letras_do_roteiro = LETRAS_QUE_TRAZEM_O_ROTEIRO[programa]
    letras_com_valor = letras_do_roteiro + LETRAS_QUE_TRAZEM_OUTRO_VALOR[programa]
    operandos, roteiros = [], []
    letra_que_espera, so_operandos = SEM_NOME, False
    for token in tokens[1:]:
        if letra_que_espera:
            roteiros.append((letra_que_espera, token))
            letra_que_espera = SEM_NOME
        elif so_operandos or not token.startswith(PREFIXO_DE_OPCAO) \
                or token == PREFIXO_DE_OPCAO:
            operandos.append(token)
            so_operandos = so_operandos or \
                programa in PROGRAMAS_CUJAS_OPCOES_ACABAM_NO_PRIMEIRO_OPERANDO
        elif token == FIM_DAS_OPCOES:
            so_operandos = True
        else:
            letra, valor, colado = opcao_que_leva_valor(
                programa, token, letras_com_valor)
            if letra and colado:
                roteiros.append((letra, valor))
            letra_que_espera = SEM_NOME if colado else letra
    roteiros = [(letra, valor) for letra, valor in roteiros
                if letra and letra in letras_do_roteiro]
    if not roteiros and operandos:
        roteiros, operandos = [(SEM_NOME, operandos[0])], operandos[1:]
    return operandos + escritas_de_dentro_dos_roteiros(programa, roteiros,
                                                       onde)


def caminhos_escritos_na_opcao(programa: str, tokens: list) -> list:
    bandeiras = COMANDOS_QUE_ESCREVEM_NA_OPCAO.get(programa)
    if not bandeiras:
        return []
    achados = []
    for i, t in enumerate(tokens[1:], start=1):
        if t in bandeiras and i + 1 < len(tokens):
            achados.append(tokens[i + 1])
        achados += [t.split(IGUAL, 1)[1] for b in bandeiras
                    if t.startswith(b + IGUAL)]
    return achados


def saida_do_dd(programa: str, tokens: list) -> list:
    if programa != COMANDO_DD:
        return []
    return [t[len(PREFIXO_DA_SAIDA_DO_DD):] for t in tokens[1:]
            if t.startswith(PREFIXO_DA_SAIDA_DO_DD)]


def acoes_do_comando(comando: str, onde: str,
                     ferramenta: str = FERRAMENTA_BASH) -> list:
    acoes = [Acao(ACAO_ESCREVER_EM.format(caminho),
                  repositorio_do_caminho(caminho, onde), caminho)
             for caminho in
             desembrulhador().caminhos_escritos_dentro_do_script(comando)]
    for segmento in separar_desembrulhando(comando, ferramenta):
        tokens = partir_em_tokens(segmento.strip())
        for caminho in caminhos_escritos_pelo_segmento(segmento, tokens,
                                                       onde):
            acoes.append(Acao(ACAO_ESCREVER_EM.format(caminho),
                              repositorio_do_caminho(caminho, onde), caminho))
        tokens = sem_o_que_o_shell_consome_antes_do_comando(tokens)
        if tokens and e_git(tokens[0]):
            verbo = verbo_do_git_que_escreve(tokens)
            if verbo:
                for alvo in alvos_escritos_pelo_git(verbo, tokens):
                    acoes.append(Acao(ACAO_RODAR.format("git " + verbo),
                                      repositorio_do_caminho(alvo, onde),
                                      alvo, True))
        if tokens and e_gh(tokens[0]):
            subverbo = subverbo_do_gh_que_escreve(tokens)
            if subverbo:
                declarado = valor_da_bandeira(tokens,
                                              BANDEIRAS_DO_REPOSITORIO_DO_GH)
                acoes.append(Acao(ACAO_RODAR.format("gh " + subverbo),
                                  repositorio_do_nome_remoto(declarado)
                                  if declarado
                                  else repositorio_do_caminho(".", onde),
                                  declarado or AQUI_MESMO, True))
        if tokens and Path(tokens[0]).name == COMANDO_CD and len(tokens) > 1:
            destino = resolver(sem_o_par_de_aspas_que_envolve(tokens[1]), onde)
            onde = str(destino) if destino else onde
    return acoes


def acoes_do_pedido(entrada: dict, onde: str) -> list:
    ferramenta = entrada.get("tool_name", "")
    dado = entrada.get("tool_input", {}) or {}
    if ferramenta in FERRAMENTAS_DE_ESCRITA:
        for campo in CAMPOS_DE_CAMINHO:
            if dado.get(campo):
                return [Acao(ACAO_ESCREVER_EM.format(dado[campo]),
                             repositorio_do_caminho(dado[campo], onde),
                             dado[campo])]
        return []
    comando = dado.get("command", "")
    return acoes_do_comando(comando, onde, ferramenta) if comando else []


def repositorio_dono_de(caminho: str, onde: str):
    alvo = resolver(caminho, onde)
    return repositorio_de(alvo) if alvo else None


def recusa_por_cadastro_nao_medido(acoes: list, raiz, onde: str):
    nosso = repositorio_dono_de(str(raiz), onde) if raiz else None
    for acao in acoes:
        dono = repositorio_dono_de(acao.alvo, onde)
        if dono is not None and dono != nosso:
            return Recusa(acao.descricao, dono.name.lower(), False)
    return None


def recusa_do_pedido(entrada: dict, cadastro, onde: str, raiz=None):
    if not isinstance(cadastro, CadastroDosVizinhos):
        cadastro = CadastroDosVizinhos(cadastro, True)
    if not cadastro.medido:
        return recusa_por_cadastro_nao_medido(
            acoes_do_pedido(entrada, onde), raiz, onde)
    if not cadastro.nomes:
        return None
    acoes = acoes_do_pedido(entrada, onde)
    for acao in acoes:
        if acao.repositorio and acao.repositorio in cadastro.nomes:
            return Recusa(acao.descricao, acao.repositorio, True)
    nomeado = protegido_nomeado_no_texto_cru(
        entrada, [acao for acao in acoes if acao.operacao_reconhecida],
        cadastro.nomes, a_prosa_conta=False)
    return Recusa(nomeado[0], nomeado[1], True) if nomeado else None


def alvo_que_o_gancho_nao_resolve(caminho: str) -> bool:
    return any(marca in caminho for marca in MARCADORES_DE_EXPANSAO)


SEPARADORES_DE_CAMINHO = "/\\"


def da_frase_entre_aspas_so_o_que_tem_cara_de_caminho(
        token: str, a_prosa_conta: bool = True) -> str:
    palavras = token.split()
    if len(palavras) < 2:
        return token
    com_cara_de_caminho = [
        palavra for palavra in palavras
        if any(s in palavra for s in SEPARADORES_DE_CAMINHO)]
    if not a_prosa_conta and len(com_cara_de_caminho) < len(palavras):
        return ""
    return " ".join(com_cara_de_caminho)


def so_o_que_pode_ser_caminho(comando: str,
                              ferramenta: str = FERRAMENTA_BASH,
                              a_prosa_conta: bool = True) -> str:
    sobra = []
    for segmento in separar_desembrulhando(comando, ferramenta):
        tokens = partir_em_tokens(segmento.strip())
        comando = sem_o_que_o_shell_consome_antes_do_comando(tokens)
        if not (comando and (e_git(comando[0]) or e_gh(comando[0]))):
            sobra += [da_frase_entre_aspas_so_o_que_tem_cara_de_caminho(
                t, a_prosa_conta) for t in tokens]
            continue
        sobra += tokens[:len(tokens) - len(comando)]
        pula_o_proximo, aspa_aberta_na_prosa = False, ""
        for token in comando:
            if aspa_aberta_na_prosa:
                if token.endswith(aspa_aberta_na_prosa):
                    aspa_aberta_na_prosa = ""
                continue
            if pula_o_proximo:
                pula_o_proximo = False
                continue
            if token in BANDEIRAS_QUE_CARREGAM_PROSA:
                pula_o_proximo = True
                continue
            colada = next((bandeira for bandeira in BANDEIRAS_QUE_CARREGAM_PROSA
                           if token.startswith(bandeira + IGUAL)), "")
            if colada:
                valor = token[len(colada) + len(IGUAL):]
                if valor[:1] in ASPAS and valor[:1] \
                        and not valor[1:].endswith(valor[:1]):
                    aspa_aberta_na_prosa = valor[:1]
                continue
            sobra.append(token)
    return " ".join(sobra)


def protegido_nomeado_no_texto_cru(entrada: dict, acoes: list, nomes,
                                   a_prosa_conta: bool = True):
    sem_resolver = [acao.descricao for acao in acoes
                    if alvo_que_o_gancho_nao_resolve(acao.alvo)]
    if not sem_resolver:
        return None
    comando = so_o_que_pode_ser_caminho(
        (entrada.get("tool_input") or {}).get("command", ""),
        entrada.get("tool_name"), a_prosa_conta)
    for nome in nomes:
        if re.search(NOME_COMO_PASTA_NO_TEXTO.format(re.escape(nome)),
                     comando, re.I | re.M):
            return sem_resolver[0], nome
    return None


def vizinho_so_nomeado_no_texto_cru(entrada: dict, cadastro, onde: str):
    if not isinstance(cadastro, CadastroDosVizinhos):
        cadastro = CadastroDosVizinhos(cadastro, True)
    if not (cadastro.medido and cadastro.nomes):
        return None
    escritas_sem_operacao_reconhecida = [
        acao for acao in acoes_do_pedido(entrada, onde)
        if not acao.operacao_reconhecida]
    nomeado = protegido_nomeado_no_texto_cru(
        entrada, escritas_sem_operacao_reconhecida, cadastro.nomes)
    return nomeado[1] if nomeado else None


def raiz_do_projeto_nunca_o_cwd() -> Path:
    declarada = os.environ.get(VARIAVEL_DA_RAIZ_DO_PROJETO)
    if declarada:
        return Path(declarada)
    return Path(__file__).resolve().parents[NIVEIS_DO_GANCHO_ATE_A_RAIZ]


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
        onde = entrada.get("cwd") or os.getcwd()
    except (json.JSONDecodeError, AttributeError, TypeError,
            ValueError) as falha:
        return recusa_por_nao_entender(falha)

    raiz = raiz_do_projeto_nunca_o_cwd()
    cadastro = cadastro_dos_vizinhos(raiz)
    recusa = recusa_do_pedido(entrada, cadastro, onde, raiz)
    if not recusa:
        nomeado = vizinho_so_nomeado_no_texto_cru(entrada, cadastro, onde)
        if nomeado:
            print(json.dumps(o_aviso_do_vizinho_so_nomeado(nomeado)))
        return SILENCIO

    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": EVENTO_ANTES_DA_FERRAMENTA,
        "permissionDecision": DECISAO_DE_NEGAR,
        "permissionDecisionReason": razao_da_recusa(recusa, raiz),
    }}))
    return SILENCIO


def o_aviso_do_vizinho_so_nomeado(nome: str) -> dict:
    return {"hookSpecificOutput": {
        "hookEventName": EVENTO_ANTES_DA_FERRAMENTA,
        "additionalContext": AVISO_DO_VIZINHO_SO_NOMEADO.format(nome)}}


def razao_da_recusa(recusa: Recusa, raiz: Path) -> str:
    if not recusa.cadastro_medido:
        return RECUSA_SEM_CADASTRO.format(
            recusa.descricao, recusa.repositorio,
            (raiz / ARQUIVO_EXECUTOR).as_posix(), CHAVE_DOS_PROJETOS)
    return (RECUSA.format(
        recusa.descricao, recusa.repositorio,
        revisor_de(raiz, recusa.repositorio),
        CHAVE_DOS_PROJETOS, ARQUIVO_EXECUTOR)
        + MANDA_GRAVAR.format(APRENDIZADO))


NOME_DO_SOMENTE_LEITURA = "so-leitura"
REVISOR_DO_TESTE = "quem-cuida"
NOME_DO_QUE_ACEITA_ESCRITA = "pode-escrever"


def montar_workspace_de_mentira(pasta: Path) -> None:
    (pasta / PASTA_DO_GIT).mkdir(parents=True, exist_ok=True)
    (pasta / "nucleo").mkdir(parents=True, exist_ok=True)
    (pasta / "nucleo" / "executor.json").write_text(json.dumps(
        {CHAVE_DOS_PROJETOS: {"alvo": {CHAVE_DO_REPOSITORIO: NOME_DO_SOMENTE_LEITURA, CHAVE_DO_SO_LEITURA: True, CHAVE_DO_REVISOR: REVISOR_DO_TESTE}}}),
        encoding="utf-8")
    for nome in (NOME_DO_SOMENTE_LEITURA, NOME_DO_QUE_ACEITA_ESCRITA):
        (pasta / "projetos" / nome / PASTA_DO_GIT).mkdir(
            parents=True, exist_ok=True)
        (pasta / "projetos" / nome / "src").mkdir(parents=True, exist_ok=True)
        (pasta / "projetos" / nome / "x.py").write_text("velho",
                                                        encoding="utf-8")
    (pasta / "conhecimento").mkdir(parents=True, exist_ok=True)
    (pasta / "projetos" / NOME_DO_SOMENTE_LEITURA / "roteiro.sed").write_text(
        "s/a/b/\n", encoding="utf-8")
    (pasta / "conhecimento" / "escreve.sed").write_text(
        f"w projetos/{NOME_DO_SOMENTE_LEITURA}/x.py\n", encoding="utf-8")
    (pasta / "fora").mkdir(parents=True, exist_ok=True)
    (pasta / "vendor" / "vizinho" / PASTA_DO_GIT).mkdir(
        parents=True, exist_ok=True)


def apagar_o_cadastro(alvo: Path) -> None:
    import shutil
    if alvo.is_dir():
        shutil.rmtree(alvo)
    elif alvo.exists():
        alvo.unlink()


def virar_pasta_no_lugar_do_cadastro(alvo: Path) -> None:
    apagar_o_cadastro(alvo)
    alvo.mkdir(parents=True, exist_ok=True)


def quebrar_o_json_do_cadastro(alvo: Path) -> None:
    apagar_o_cadastro(alvo)
    alvo.write_text("{ isto não fecha", encoding="utf-8")


def torcer_a_forma_do_cadastro(alvo: Path) -> None:
    apagar_o_cadastro(alvo)
    alvo.write_text(json.dumps({CHAVE_DOS_PROJETOS: []}), encoding="utf-8")


ESTRAGOS_DO_CADASTRO = (
    ("ausente", apagar_o_cadastro),
    ("com pasta no lugar do arquivo", virar_pasta_no_lugar_do_cadastro),
    ("com o JSON quebrado", quebrar_o_json_do_cadastro),
    ("com a chave dos projetos fora da forma", torcer_a_forma_do_cadastro),
)


def pedido_de_shell(comando: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": comando}}


def pedido_do_powershell(comando: str) -> dict:
    return {"tool_name": FERRAMENTA_POWERSHELL,
            "tool_input": {"command": comando}}


def o_que_a_cerca_imprime(pedido: dict, raiz: Path, onde: str) -> dict:
    import contextlib
    import io
    global raiz_do_projeto_nunca_o_cwd
    de_verdade, entrada_de_verdade = raiz_do_projeto_nunca_o_cwd, sys.stdin
    impresso = io.StringIO()
    try:
        raiz_do_projeto_nunca_o_cwd = lambda: raiz
        sys.stdin = io.StringIO(json.dumps({**pedido, "cwd": onde}))
        with contextlib.redirect_stdout(impresso):
            decidir()
    finally:
        raiz_do_projeto_nunca_o_cwd, sys.stdin = de_verdade, entrada_de_verdade
    return json.loads(impresso.getvalue() or "{}").get(
        "hookSpecificOutput", {})


def pedido_de_escrita(ferramenta: str, caminho: str) -> dict:
    campo = "notebook_path" if ferramenta == "NotebookEdit" else "file_path"
    return {"tool_name": ferramenta, "tool_input": {campo: caminho}}


BARRA = [
    ("Write nasce dentro do somente leitura",
     pedido_de_escrita("Write", "projetos/so-leitura/novo.py")),
    ("Edit de arquivo que já existe lá",
     pedido_de_escrita("Edit", "projetos/so-leitura/x.py")),
    ("NotebookEdit lá dentro",
     pedido_de_escrita("NotebookEdit", "projetos/so-leitura/n.ipynb")),
    ("git commit por -C", pedido_de_shell(
        "git -C projetos/so-leitura commit -m mudanca")),
    ("git push por -C", pedido_de_shell("git -C projetos/so-leitura push")),
    ("git push depois de cd", pedido_de_shell(
        "cd projetos/so-leitura && git push origin HEAD")),
    ("git checkout -b por -C", pedido_de_shell(
        "git -C projetos/so-leitura checkout -b issue/1-teste")),
    ("git merge por -C", pedido_de_shell(
        "git -C projetos/so-leitura merge origin/main")),
    ("git branch com nome novo", pedido_de_shell(
        "git -C projetos/so-leitura branch nova")),
    ("gh pr create depois de cd", pedido_de_shell(
        "cd projetos/so-leitura && gh pr create --fill")),
    ("gh pr create pelo nome do remoto", pedido_de_shell(
        "gh pr create --repo dono/so-leitura --fill")),
    ("gh issue close fecha trabalho alheio", pedido_de_shell(
        "gh issue close 7 --repo dono/so-leitura")),
    ("gh pr merge aplica por cima", pedido_de_shell(
        "gh pr merge 5 --repo dono/so-leitura --squash")),
    ("redirecionamento para dentro", pedido_de_shell(
        "echo oi > projetos/so-leitura/x.txt")),
    ("apagar lá dentro", pedido_de_shell("rm -rf projetos/so-leitura/src")),
    ("curl -o lá dentro", pedido_de_shell(
        "curl -s -o projetos/so-leitura/x.txt https://x/y")),
    ("wget -O lá dentro", pedido_de_shell(
        "wget -O projetos/so-leitura/x.txt https://x/y")),
    ("rsync para lá dentro", pedido_de_shell(
        "rsync -a src/ projetos/so-leitura/src/")),
    ("perl -i lá dentro", pedido_de_shell(
        "perl -i -pe s/a/b/ projetos/so-leitura/x.py")),
    ("dd gravando lá dentro", pedido_de_shell(
        "dd if=/dev/zero of=projetos/so-leitura/x.bin count=1")),
    ("mover lá dentro", pedido_de_shell(
        "mv projetos/so-leitura/x.py projetos/so-leitura/y.py")),
    ("sed no lugar", pedido_de_shell(
        "sed -i 's/a/b/' projetos/so-leitura/x.py")),
    ("copiar para dentro", pedido_de_shell(
        "cp projetos/pode-escrever/x.py projetos/so-leitura/x.py")),
    ("python -c que escreve lá dentro", pedido_de_shell(
        "python -c \"open('projetos/so-leitura/x.py', 'w').write('x')\"")),
    ("python -c que guarda o alvo em variável antes de escrever",
     pedido_de_shell(
         "python -c \"p = 'projetos/so-leitura/x.py'; open(p, 'w')\"")),
    ("node -e que escreve lá dentro", pedido_de_shell(
        "node -e \"require('fs').writeFileSync('projetos/so-leitura/x.py', "
        "'x')\"")),
    ("sh -c embrulha o redirecionamento", pedido_de_shell(
        "sh -c 'echo oi > projetos/so-leitura/x.txt'")),
    ("bash -lc embrulha o git push", pedido_de_shell(
        'bash -lc "git -C projetos/so-leitura push"')),
    ("eval embrulha o rm", pedido_de_shell(
        "eval 'rm -rf projetos/so-leitura/src'")),
    ("xargs entrega o sh -c que escreve", pedido_de_shell(
        "ls | xargs -I{} sh -c 'touch projetos/so-leitura/{}'")),
    ("CONTROLE da operação reconhecida: git com o diretório em variável, e "
     "o vizinho nomeado como caminho no comando — o verbo é conhecido, só o "
     "alvo não resolve, e o texto cru segue negando",
     pedido_de_shell(
         "ALVO=projetos/so-leitura; git -C $ALVO push")),
    ("o mesmo, com mensagem junto: tirar a prosa da busca não pode tirar o "
     "caminho que está fora dela",
     pedido_de_shell(
         'ALVO=projetos/so-leitura; git -C $ALVO commit -m "nota"')),
    ("redirecionamento antes do git não esconde o git: o shell roda o push "
     "do mesmo jeito, e a operação segue reconhecida",
     pedido_de_shell(
         'ALVO=projetos/so-leitura; > "$ALVO/log" git -C "$ALVO" push')),
    ("o mesmo com a saída de erro redirecionada antes do verbo",
     pedido_de_shell(
         'ALVO=projetos/so-leitura; 2> "$ALVO/log" git -C "$ALVO" reset '
         '--hard')),
    ("atribuição de variável antes do git também não o esconde",
     pedido_de_shell("ALVO=projetos/so-leitura; LANG=C git -C $ALVO push")),
    ("a pasta do git aponta o protegido: é lá que o commit grava",
     pedido_de_shell(
         "git --git-dir=projetos/so-leitura/.git commit -m nota")),
    ("a árvore de trabalho aponta o protegido e o verbo materializa arquivo",
     pedido_de_shell("git --work-tree=projetos/so-leitura checkout .")),
    ("init posicional cria repositório dentro do protegido",
     pedido_de_shell("git init projetos/so-leitura/sub")),
    ("clone posicional despeja árvore inteira dentro do protegido",
     pedido_de_shell(
         "git clone https://exemplo.invalido/r.git projetos/so-leitura/novo")),
    ("init posicional resolve contra o diretório que a bandeira declara, "
     "não contra a pasta de onde o comando sai",
     pedido_de_shell("git -C projetos/so-leitura init sub")),
    ("sed -i com o roteiro por -e e o arquivo lá dentro", pedido_de_shell(
        "sed -i -e 's/a/b/' projetos/so-leitura/x.py")),
    ("sed -ie: o e colado ao i é sufixo, não roteiro", pedido_de_shell(
        "sed -ie 's/a/b/' projetos/so-leitura/x.py")),
    ("sed -i com um arquivo nosso e outro lá dentro, os dois como arquivo",
     pedido_de_shell(
         "sed -i 's/a/b/' conhecimento/nota.md projetos/so-leitura/x.py")),
    ("sed -i com --expression= e o arquivo lá dentro", pedido_de_shell(
        "sed -i --expression='s/a/b/' projetos/so-leitura/x.py")),
    ("sed -i com -- antes do arquivo lá dentro", pedido_de_shell(
        "sed -i -e 's/a/b/' -- projetos/so-leitura/x.py")),
    ("sed -ni: o n antes do i não esconde o alvo", pedido_de_shell(
        "sed -ni 's/a/b/p' projetos/so-leitura/x.py")),
    ("perl para de ler opção no primeiro arquivo: o -e depois dele é "
     "arquivo, e o de lá dentro também", pedido_de_shell(
         "perl -pi -e 's/a/b/' conhecimento/nota.md -e "
         "projetos/so-leitura/x.py")),
    ("o mesmo com o roteiro em arquivo e sem -e", pedido_de_shell(
        "perl -pi roteiro.pl conhecimento/nota.md -e projetos/so-leitura/x.py")),
    ("o comando w do roteiro escreve no arquivo que ele nomeia",
     pedido_de_shell(
         "sed -i 'w projetos/so-leitura/x.py' conhecimento/nota.md")),
    ("o mesmo com o comando W", pedido_de_shell(
        "sed -i 'W projetos/so-leitura/x.py' conhecimento/nota.md")),
    ("o mesmo com a bandeira w do s", pedido_de_shell(
        "sed -i 's/a/b/w projetos/so-leitura/x.py' conhecimento/nota.md")),
    ("o roteiro do -f que se lê e escreve com w", pedido_de_shell(
        "sed -i -f conhecimento/escreve.sed conhecimento/nota.md")),
    ("o roteiro do -f que não se lê volta a ser julgado como antes",
     pedido_de_shell(
         "sed -i -f projetos/so-leitura/ausente.sed conhecimento/nota.md")),
    ("a bandeira w do s depois de outra bandeira", pedido_de_shell(
        "sed -i 's/a/b/gw projetos/so-leitura/x.py' conhecimento/nota.md")),
    ("o comando w depois de um endereço por número", pedido_de_shell(
        "sed -i '1w projetos/so-leitura/x.py' conhecimento/nota.md")),
    ("o comando w depois de um endereço por expressão", pedido_de_shell(
        "sed -i '/x/w projetos/so-leitura/x.py' conhecimento/nota.md")),
    ("a / dentro do colchete não fecha a expressão do s", pedido_de_shell(
        "sed -i 's/[/]/a/w projetos/so-leitura/x.py' conhecimento/nota.md")),
    ("o ] logo depois do [ é literal e não fecha o colchete",
     pedido_de_shell(
         "sed -i 's/[]/]/a/w projetos/so-leitura/x.py' conhecimento/nota.md")),
    ("a contrabarra escapa o delimitador da expressão do s",
     pedido_de_shell(
         "sed -i 's/\\/x/a/w projetos/so-leitura/x.py' conhecimento/nota.md")),
    ("a / dentro do colchete não fecha o endereço por expressão",
     pedido_de_shell(
         "sed -i '/[/]/w projetos/so-leitura/x.py' conhecimento/nota.md")),
    ("a aspa escapada não abre aspa, e o rm entre dois echo é do shell",
     pedido_de_shell('echo \\" ; rm projetos/so-leitura/x.py ; echo \\"')),
    ("a contrabarra no fim da linha junta o vizinho ao rm",
     pedido_de_shell("rm \\\n projetos/so-leitura/x.py")),
    ("dentro da aspa simples a contrabarra não escapa, e a aspa fecha antes "
     "do rm", pedido_de_shell("echo 'a\\' ; rm projetos/so-leitura/x.py")),
    ("o ponto e vírgula dentro do $() entre aspas duplas é do shell",
     pedido_de_shell('echo "$(true; rm projetos/so-leitura/x.py)"')),
    ("o ponto e vírgula dentro da crase entre aspas duplas é do shell",
     pedido_de_shell('echo "`true; rm projetos/so-leitura/x.py`"')),
    ("no PowerShell a contrabarra é texto, e a aspa fecha antes do rm",
     pedido_do_powershell(
         'echo "a\\" ; rm projetos/so-leitura/x.py ; echo \\"b"')),
    ("no PowerShell a crase escapa a aspa, e o rm entre dois echo é do "
     "shell", pedido_do_powershell(
         'echo `"; rm projetos/so-leitura/x.py; echo `"')),
    ("a aspa no corpo do documento que expande, dentro do $() entre aspas "
     "duplas, não esconde o rm",
     pedido_de_shell('echo "$(cat <<EOF\n\'\nEOF\n)"; '
                     "rm projetos/so-leitura/x.py\necho ')\"")),
    ("a contrabarra no fim da linha antes do comando some, e o rm fica "
     "inteiro", pedido_de_shell("\\\nrm projetos/so-leitura/x.py")),
    ("a contrabarra no fim da linha depois do && também some",
     pedido_de_shell("true &&\\\nrm projetos/so-leitura/x.py")),
    ("a marca de documento dentro da aspa não apaga o resto do comando",
     pedido_de_shell("echo \"<<'X'\"; rm projetos/so-leitura/x.py")),
    ("o resto da linha que abre o documento literal é comando",
     pedido_de_shell("cat <<'EOF'; rm projetos/so-leitura/x.py\nx\nEOF")),
    ("o redirecionamento depois da marca do documento literal é do shell",
     pedido_de_shell("cat <<'EOF' > projetos/so-leitura/x.py\nx\nEOF")),
    ("o documento literal que o bash lê é comando",
     pedido_de_shell("bash <<'EOF'\nrm projetos/so-leitura/x.py\nEOF")),
    ("o documento literal que vai pelo cano ao sh é comando",
     pedido_de_shell("cat <<'EOF' | sh\nrm projetos/so-leitura/x.py\nEOF")),
    ("a aspa dentro do comentário não esconde a linha seguinte",
     pedido_de_shell("echo ok # \"\nrm projetos/so-leitura/x.py\n# \"")),
    ("as chaves agrupam comandos",
     pedido_de_shell("{ rm projetos/so-leitura/x.py; }")),
    ("a exclamação na frente não disfarça",
     pedido_de_shell("! rm projetos/so-leitura/x.py")),
    ("o then do if não disfarça",
     pedido_de_shell("if true; then rm projetos/so-leitura/x.py; fi")),
    ("o do do laço não disfarça",
     pedido_de_shell("for f in a; do rm projetos/so-leitura/x.py; done")),
    ("no PowerShell o comentário de bloco na frente não disfarça",
     pedido_do_powershell("<# c #> rm projetos/so-leitura/x.py")),
    ("no PowerShell a aspa dentro do comentário não esconde a linha "
     "seguinte", pedido_do_powershell(
         "echo ok # \"\nrm projetos/so-leitura/x.py\n# \"")),
    ("a contrabarra no meio do programa não disfarça o rm",
     pedido_de_shell("r\\m projetos/so-leitura/x.py")),
    ("a contrabarra no meio do caminho não disfarça o vizinho",
     pedido_de_shell("rm projetos/so-leitu\\ra/x.py")),
    ("no PowerShell a crase no meio do programa não disfarça o rm",
     pedido_do_powershell("r`m projetos/so-leitura/x.py")),
    ("o texto que o echo entrega ao sh pelo cano é comando",
     pedido_de_shell("echo 'rm projetos/so-leitura/x.py' | sh")),
    ("o texto que o printf entrega ao bash pelo cano é comando",
     pedido_de_shell("printf '%s' 'rm projetos/so-leitura/x.py' | bash")),
    ("a cadeia do <<< entrega o rm ao bash",
     pedido_de_shell("bash <<< 'rm projetos/so-leitura/x.py'")),
    ("pwsh -c embrulha o rm",
     pedido_de_shell('pwsh -c "rm projetos/so-leitura/x.py"')),
    ("powershell -Command embrulha o rm",
     pedido_de_shell(
         'powershell -NoProfile -Command "rm projetos/so-leitura/x.py"')),
    ("cmd /c embrulha o rm",
     pedido_de_shell('cmd /c "rm projetos/so-leitura/x.py"')),
    ("no PowerShell o Invoke-Expression embrulha o rm",
     pedido_do_powershell('Invoke-Expression "rm projetos/so-leitura/x.py"')),
    ("no PowerShell o iex embrulha o rm",
     pedido_do_powershell("iex 'rm projetos/so-leitura/x.py'")),
    ("no PowerShell o texto que chega ao iex pelo cano é comando",
     pedido_do_powershell("'rm projetos/so-leitura/x.py' | iex")),
    ("o documento dentro do bash -c é comando",
     pedido_de_shell("bash -c \"$(cat <<'EOF'\n"
                     "rm projetos/so-leitura/x.py\nEOF\n)\"")),
    ("o documento dentro do eval é comando",
     pedido_de_shell("eval \"$(cat <<'EOF'\n"
                     "rm projetos/so-leitura/x.py\nEOF\n)\"")),
    ("o documento do bash -c com a substituição aberta na linha de cima "
     "é comando",
     pedido_de_shell("bash -c \"$(\ncat <<'EOF'\n"
                     "rm projetos/so-leitura/x.py\nEOF\n)\"")),
    ("o nome do shell entre aspas lê o documento e apaga lá dentro",
     pedido_de_shell("\"bash\" <<EOF\nrm projetos/so-leitura/x.py\nEOF")),
    ("o documento entregue ao sh com posicional apaga lá dentro",
     pedido_de_shell("echo 'rm projetos/so-leitura/x.py' | sh -s -- x")),
    ("o caminho com espaço guardado em variável segue caminho, não frase",
     pedido_de_shell('ALVO="D:/meu projeto/projetos/so-leitura"; '
                     'git -C "$ALVO" merge --no-ff x')),
    ("o eval roda o texto que a substituição devolve",
     pedido_de_shell("eval $(echo 'rm projetos/so-leitura/x.py')")),
    ("o source lê o comando da substituição de processo",
     pedido_de_shell("source <(echo 'rm projetos/so-leitura/x.py')")),
    ("o |& entrega o texto ao bash como o cano",
     pedido_de_shell("echo 'rm projetos/so-leitura/x.py' |& bash")),
    ("no PowerShell o iex roda o texto que o parêntese devolve",
     pedido_do_powershell("iex (echo 'rm projetos/so-leitura/x.py')")),
]

SO_AVISA = [
    ("alvo guardado em variável: o repositório está no texto cru",
     pedido_de_shell("ALVO=projetos/so-leitura/x.txt; echo oi > $ALVO")),
    ("alvo montado com a raiz em variável", pedido_de_shell(
        'echo oi > "$RAIZ/projetos/so-leitura/x.txt"')),
    ("prosa ecoada que traz o vizinho como caminho, para destino em "
     "variável: o destino pode ser um rascunho, e negar aqui era adivinhar",
     pedido_de_shell(
         'echo "copia de projetos/so-leitura/x.py" > $RASCUNHO/nota.txt')),
    ("o nome do vizinho solto fora de aspas, com destino em variável: ali "
     "ele pode ser a pasta, e pode não ser",
     pedido_de_shell("cd projetos; cat x.py so-leitura > $SAIDA")),
    ("alvo do sed -i guardado em variável", pedido_de_shell(
        "ALVO=projetos/so-leitura/x.py; sed -i 's/a/b/' \"$ALVO\"")),
]

DEIXA_PASSAR = [
    ("cat lê lá dentro", pedido_de_shell("cat projetos/so-leitura/x.py")),
    ("git log", pedido_de_shell("git -C projetos/so-leitura log --oneline")),
    ("git show", pedido_de_shell(
        "git -C projetos/so-leitura show HEAD:x.py")),
    ("git status", pedido_de_shell(
        "git -C projetos/so-leitura status --porcelain")),
    ("git diff", pedido_de_shell("git -C projetos/so-leitura diff")),
    ("git branch --show-current", pedido_de_shell(
        "git -C projetos/so-leitura branch --show-current")),
    ("git tag -l", pedido_de_shell("git -C projetos/so-leitura tag -l v1*")),
    ("git fetch não muda conteúdo", pedido_de_shell(
        "git -C projetos/so-leitura fetch origin")),
    ("grep varre lá dentro", pedido_de_shell(
        "grep -rn assunto projetos/so-leitura")),
    ("gh issue view", pedido_de_shell(
        "cd projetos/so-leitura && gh issue view 3")),
    ("gh pr view", pedido_de_shell(
        "cd projetos/so-leitura && gh pr view 2")),
    ("gh issue comment leva resposta, não muda código", pedido_de_shell(
        "gh issue comment 7 --repo dono/so-leitura --body-file r.md")),
    ("gh issue create leva achado com evidência", pedido_de_shell(
        "gh issue create --repo dono/so-leitura --title t --body-file c.md")),
    ("gh pr comment conversa no fio", pedido_de_shell(
        "cd projetos/so-leitura && gh pr comment 5 --body oi")),
    ("gh pr close retira a própria sugestão", pedido_de_shell(
        "gh pr close 5 --repo dono/so-leitura")),
    ("gh issue edit corrige a própria proposta", pedido_de_shell(
        "gh issue edit 7 --repo dono/so-leitura --body-file c.md")),
    ("sed que só lê", pedido_de_shell(
        "sed -n '1,5p' projetos/so-leitura/x.py")),
    ("copiar de dentro para fora", pedido_de_shell(
        "cp projetos/so-leitura/x.py projetos/pode-escrever/copia.py")),
    ("Write no repositório que aceita escrita",
     pedido_de_escrita("Write", "projetos/pode-escrever/novo.py")),
    ("git push no repositório que aceita escrita", pedido_de_shell(
        "git -C projetos/pode-escrever push")),
    ("Write no próprio workspace",
     pedido_de_escrita("Write", "conhecimento/nota.md")),
    ("python -c que só lê lá dentro", pedido_de_shell(
        "python -c \"print(open('projetos/so-leitura/x.py').read())\"")),
    ("node -e que só lê lá dentro", pedido_de_shell(
        "node -e \"console.log(require('fs').readFileSync("
        "'projetos/so-leitura/x.py', 'utf8'))\"")),
    ("sh -c que só lê", pedido_de_shell(
        "sh -c 'cat projetos/so-leitura/x.py'")),
    ("alvo em variável sem repositório protegido no texto",
     pedido_de_shell("echo oi > $SAIDA")),
    ("commit no repositório próprio cuja mensagem fala do vizinho: prosa "
     "não é caminho, e o alvo do commit está resolvido",
     pedido_de_shell('git commit -m "ajusta o tema so-leitura da casca"')),
    ("o mesmo commit com o nome em maiúscula na mensagem",
     pedido_de_shell('git commit -m "tema So-Leitura"')),
    ("pasta do repositório próprio que por acaso se chama como o vizinho",
     pedido_de_shell("git add src/temas/so-leitura/componentes.scss")),
    ("a mesma pasta, pela ferramenta de escrita",
     pedido_de_escrita("Write", "src/temas/so-leitura/componentes.scss")),
    ("alvo em variável e o vizinho só na prosa do -m: prosa não é caminho, "
     "e o texto cru não pode lê-la",
     pedido_de_shell('git -C $ALVO commit -m "ajusta o tema so-leitura"')),
    ("o mesmo, com a mensagem pela bandeira longa",
     pedido_de_shell('git -C $ALVO commit --message="tema so-leitura"')),
    ("o mesmo, com atribuição de variável antes do git: o prefixo não pode "
     "devolver a prosa do -m à busca",
     pedido_de_shell(
         'LANG=C git -C $ALVO commit -m "nota sobre projetos/so-leitura/x"')),
    ("CONTROLE do anterior, sem o prefixo: a prosa do -m já ficava fora",
     pedido_de_shell(
         'git -C $ALVO commit -m "nota sobre projetos/so-leitura/x"')),
    ("redirecionamento para variável com o vizinho só na prosa ecoada: "
     "palavra solta dentro de aspas não é caminho",
     pedido_de_shell(
         'echo "o clone so-leitura esta atrasado" > $RASCUNHO/nota.txt')),
    ("o mesmo, com aspas simples e o nome no fim da frase",
     pedido_de_shell("echo 'conferi o so-leitura' >> $RASCUNHO/nota.txt")),
    ("a mescla com o alvo em variável e o vizinho só na frase do printf ao "
     "lado: frase não é destino do git",
     pedido_de_shell("git -C \"$WT\" merge --no-ff issue/1-x; "
                     "printf 'mesclei sem tocar em projetos/so-leitura\\n'")),
    ("o mesmo, com a frase do printf antes da mescla",
     pedido_de_shell("printf 'o vizinho projetos/so-leitura fica fora\\n' "
                     "&& git -C \"$WT\" merge --no-ff issue/1-x")),
    ("o mesmo pelo printf, com o nome no meio de um formato",
     pedido_de_shell(
         'printf "%s\\n" "vizinho so-leitura medido" > "$RASCUNHO/nota.txt"')),
    ("a árvore de trabalho aponta o protegido, mas o índice é o nosso e o "
     "verbo só lê a árvore",
     pedido_de_shell(
         "git --git-dir=.git --work-tree=projetos/so-leitura add .")),
    ("clone que despeja fora de repositório protegido nenhum",
     pedido_de_shell("git clone https://exemplo.invalido/r.git fora/novo")),
    ("mensagem com espaço colada no igual não vira bandeira global",
     pedido_de_shell('git commit -m="nota com espaço e igual"')),
    ("clonar de dentro do protegido para fora é leitura: o valor de uma "
     "opção não é o destino",
     pedido_de_shell(
         "git clone --depth 1 projetos/so-leitura fora/novo")),
    ("clonar de fora para fora, com a origem por bandeira",
     pedido_de_shell(
         "git clone --branch main https://exemplo.invalido/r.git fora/outro")),
    ("sed -i num arquivo nosso e o vizinho citado em outro comando",
     pedido_de_shell("sed -i 's/a/b/' conhecimento/nota.md && "
                     "grep x projetos/so-leitura/x.py")),
    ("roteiro do sed -i com cifrão não vira alvo que a cerca não resolve",
     pedido_de_shell("sed -i 's/a$/b/' conhecimento/nota.md && "
                     "grep x projetos/so-leitura/x.py")),
    ("segundo roteiro por -e com cifrão, e o vizinho só lido depois",
     pedido_de_shell("sed -i -e 's/a/b/' -e 's/c$/d/' conhecimento/nota.md; "
                     "wc -l projetos/so-leitura/x.py")),
    ("o arquivo de roteiro do -f lá dentro é lido, não escrito",
     pedido_de_shell(
         "sed -i -f projetos/so-leitura/roteiro.sed conhecimento/nota.md")),
    ("o mesmo com o -f depois de um -e", pedido_de_shell(
        "sed -i -e 's/a/b/' -f projetos/so-leitura/roteiro.sed "
        "conhecimento/nota.md")),
    ("perl -pi com cifrão no roteiro e o vizinho só lido depois",
     pedido_de_shell("perl -pi -e 's/a$/b/' conhecimento/nota.md && "
                     "cat projetos/so-leitura/x.py")),
    ("no sed a opção depois do arquivo continua opção: o -f lá dentro só é "
     "lido", pedido_de_shell(
         "sed -i -e 's/a/b/' conhecimento/nota.md "
         "-f projetos/so-leitura/roteiro.sed")),
    ("a bandeira w do s para a saída padrão não escreve no vizinho",
     pedido_de_shell("sed -i 's/a/b/w /dev/stdout' conhecimento/nota.md")),
    ("o w no texto de substituição não é o comando w",
     pedido_de_shell("sed -i 's/a/w/' conhecimento/nota.md")),
    ("o w na expressão do s não é o comando w",
     pedido_de_shell("sed -i 's/w/x/' conhecimento/nota.md")),
    ("bandeira do s que não escreve",
     pedido_de_shell("sed -i 's/a/b/g' conhecimento/nota.md")),
    ("o w no y não é o comando w",
     pedido_de_shell("sed -i 'y/abc/wxy/' conhecimento/nota.md")),
    ("o w num endereço por expressão não é o comando w",
     pedido_de_shell("sed -i '/w/d' conhecimento/nota.md")),
    ("o w com cifrão na expressão do s, e o vizinho só lido depois",
     pedido_de_shell("sed -i 's/w$/x/' conhecimento/nota.md && "
                     "grep x projetos/so-leitura/x.py")),
    ("o colchete com a / dentro, num s que não escreve",
     pedido_de_shell("sed -i 's/[/]/x/g' conhecimento/nota.md")),
    ("a aspa dupla de verdade segura o ponto e vírgula",
     pedido_de_shell('echo "x; rm projetos/so-leitura/x.py"')),
    ("a contrabarra dentro da aspa simples é texto, e a aspa segura o "
     "ponto e vírgula",
     pedido_de_shell("echo 'a\\b; rm projetos/so-leitura/x.py'")),
    ("fora das aspas a contrabarra torna o ponto e vírgula texto",
     pedido_de_shell("echo x\\; y")),
    ("a aspa simples dentro do $() segura o ponto e vírgula",
     pedido_de_shell("echo \"$(echo 'a; rm projetos/so-leitura/x.py')\"")),
    ("no PowerShell a crase escapa a aspa, e a aspa segue segurando o "
     "ponto e vírgula", pedido_do_powershell(
         'echo "a`" ; rm projetos/so-leitura/x.py ; echo `"b"')),
    ("no PowerShell a contrabarra não escapa, e a aspa abre o texto",
     pedido_do_powershell(
         'echo \\" ; rm projetos/so-leitura/x.py ; echo \\"')),
    ("no PowerShell a contrabarra na aspa simples é texto",
     pedido_do_powershell("echo 'a\\b; rm projetos/so-leitura/x.py'")),
    ("o documento que expande só com texto é dado",
     pedido_de_shell("cat <<EOF\nrm projetos/so-leitura/x.py\nEOF")),
    ("a cadeia do <<< é texto entre aspas",
     pedido_de_shell("cat <<< 'x; rm projetos/so-leitura/x.py; y'")),
    ("depois do documento que expande a aspa volta a segurar o ponto e "
     "vírgula", pedido_de_shell(
         "cat <<EOF\nx\nEOF\necho 'x; rm projetos/so-leitura/x.py; y'")),
    ("o grep que procura sh não roda o texto que chega pelo cano",
     pedido_de_shell("echo 'rm projetos/so-leitura/x.py' | grep sh")),
    ("o nome do shell dentro da aspa não faz do documento um comando",
     pedido_de_shell("echo \"conserta o bash $(cat <<'EOF'\n"
                     "rm projetos/so-leitura/x.py\nEOF\n)\"")),
    ("a mensagem do commit que vem do documento é dado",
     pedido_de_shell("git commit -m \"$(cat <<'EOF'\n"
                     "rm projetos/so-leitura/x.py\nEOF\n)\"")),
    ("o documento que o bash -c recebe como posicional é dado",
     pedido_de_shell("bash -c 'echo \"$1\"' x \"$(cat <<'EOF'\n"
                     "rm projetos/so-leitura/x.py\nEOF\n)\"")),
    ("o documento literal sem terminador é dado, não apaga lá dentro",
     pedido_de_shell("cat <<'EOF'\nrm projetos/so-leitura/x.py")),
    ("o nome do shell como argumento do echo não apaga lá dentro",
     pedido_de_shell("echo pwsh 'rm projetos/so-leitura/x.py'")),
    ("dois shells nus seguidos não entram em laço",
     pedido_de_shell("bash; bash")),
]


def testar() -> int:
    import tempfile
    falhas, comportamento = [], []
    with tempfile.TemporaryDirectory(prefix="veto-somente-leitura-") as tmp:
        raiz = Path(tmp).resolve()
        montar_workspace_de_mentira(raiz)
        onde = str(raiz)
        cadastro = cadastro_dos_vizinhos(raiz)
        nomes = cadastro.nomes

        for rotulo, pedido in BARRA:
            if not recusa_do_pedido(pedido, cadastro, onde, raiz):
                falhas.append(FALHA_BARRA.format(rotulo))
        for rotulo, pedido in DEIXA_PASSAR:
            recusa = recusa_do_pedido(pedido, cadastro, onde, raiz)
            if recusa:
                falhas.append(FALHA_DEIXA_PASSAR.format(rotulo, recusa[0]))
            elif vizinho_so_nomeado_no_texto_cru(pedido, cadastro, onde):
                falhas.append(FALHA_AVISOU_SEM_MOTIVO.format(rotulo))
        for rotulo, pedido in SO_AVISA:
            impresso = o_que_a_cerca_imprime(pedido, raiz, onde)
            if "permissionDecision" in impresso:
                falhas.append(FALHA_NEGOU_O_QUE_SO_AVISA.format(rotulo))
            elif NOME_DO_SOMENTE_LEITURA not in impresso.get(
                    "additionalContext", ""):
                falhas.append(FALHA_NAO_AVISOU.format(rotulo))

        def caso(rotulo, condicao):
            comportamento.append((rotulo, bool(condicao)))

        aviso = o_aviso_do_vizinho_so_nomeado(NOME_DO_SOMENTE_LEITURA)
        caso("o aviso do vizinho só nomeado é contexto para o modelo: nomeia "
             "o vizinho e não carrega decisão nenhuma",
             NOME_DO_SOMENTE_LEITURA
             in aviso["hookSpecificOutput"]["additionalContext"]
             and "permissionDecision" not in aviso["hookSpecificOutput"])
        caso("gancho que veta e não entende o pedido recusa, e nomeia a "
             "falha — quem não consegue julgar não pode dizer sim",
             recusou_sem_entender(TypeError("forma que o gancho não conhece")))
        caso("a lista declarada vira cerca",
             nomes == frozenset({NOME_DO_SOMENTE_LEITURA}))
        (raiz / "nucleo" / "executor.json").write_text(json.dumps({}),
                                                       encoding="utf-8")
        caso("sem o campo declarado, nada muda",
             not nomes_somente_leitura(raiz)
             and cadastro_dos_vizinhos(raiz).medido
             and not recusa_do_pedido(BARRA[0][1],
                                      cadastro_dos_vizinhos(raiz), onde,
                                      raiz))
        (raiz / "nucleo" / "executor.json").write_text(json.dumps(
            {CHAVE_DOS_PROJETOS: {"alvo": {CHAVE_DO_REPOSITORIO: "${NOME}", CHAVE_DO_SO_LEITURA: True}}}), encoding="utf-8")
        caso("nome ainda no molde não vira cerca",
             not nomes_somente_leitura(raiz))
        caso("protegido declarado sem nome legível é cadastro NÃO MEDIDO, "
             "não cadastro vazio",
             not cadastro_dos_vizinhos(raiz).medido)
        (raiz / "nucleo" / "executor.json").write_text(json.dumps(
            {CHAVE_DOS_PROJETOS: {"alvo": []}}), encoding="utf-8")
        caso("entrada de projeto fora da forma é NÃO MEDIDO: ignorá-la "
             "calada deixaria o vizinho protegido invisível",
             not cadastro_dos_vizinhos(raiz).medido)
        (raiz / "nucleo" / "executor.json").write_text(json.dumps(
            {CHAVE_DOS_PROJETOS: {"comentario": "prosa que explica a chave"}}),
            encoding="utf-8")
        caso("prosa entre os projetos continua sendo prosa, e o cadastro "
             "segue medido",
             cadastro_dos_vizinhos(raiz).medido)
        homonimo = raiz / "homonimo" / raiz.name
        (homonimo / PASTA_DO_GIT).mkdir(parents=True, exist_ok=True)
        apagar_o_cadastro(raiz / ARQUIVO_EXECUTOR)
        caso("sem cadastro, repositório de mesmo nome não passa por este: a "
             "identidade é o caminho, não o nome da pasta",
             recusa_do_pedido(
                 pedido_de_escrita("Write", f"homonimo/{raiz.name}/x.py"),
                 cadastro_dos_vizinhos(raiz), onde, raiz))

        for rotulo, estragar in ESTRAGOS_DO_CADASTRO:
            estragar(raiz / ARQUIVO_EXECUTOR)
            ilegivel = cadastro_dos_vizinhos(raiz)
            caso(f"cadastro {rotulo}: a cerca diz NÃO MEDI em vez de liberar "
                 "território alheio",
                 not ilegivel.medido
                 and recusa_do_pedido(BARRA[0][1], ilegivel, onde, raiz))
            caso(f"cadastro {rotulo}: escrita na própria árvore continua "
                 "livre, senão clone novo e worktree nova ficam trancados",
                 not recusa_do_pedido(
                     pedido_de_escrita("Write", "conhecimento/nota.md"),
                     ilegivel, onde, raiz))
            caso(f"cadastro {rotulo}: repositório aninhado fora da pasta de "
                 "projetos também é território alheio",
                 recusa_do_pedido(
                     pedido_de_escrita("Write", "vendor/vizinho/x.py"),
                     ilegivel, onde, raiz))
        montar_workspace_de_mentira(raiz)

        recusa = recusa_do_pedido(BARRA[3][1], nomes, onde)
        mensagem = RECUSA.format(recusa[0], recusa[1],
                                 revisor_de(raiz, recusa[1]),
                                 CHAVE_DOS_PROJETOS, ARQUIVO_EXECUTOR)
        caso("a mensagem nomeia o repositório",
             NOME_DO_SOMENTE_LEITURA in mensagem)
        caso("a mensagem nomeia o revisor declarado, nao só o território",
             REVISOR_DO_TESTE in mensagem)
        caso("sem revisor declarado, ela cai no território sem quebrar",
             SEM_REVISOR in RECUSA.format(
                 "x", "nao-declarado", revisor_de(raiz, "nao-declarado"),
                 CHAVE_DOS_PROJETOS, ARQUIVO_EXECUTOR))
        caso("a recusa nomeia a regra 9, diz onde o valor certo mora e "
             "manda gravar o aprendizado em conhecimento/",
             "Regra 9" in mensagem + MANDA_GRAVAR.format(APRENDIZADO)
             and ARQUIVO_EXECUTOR in mensagem
             and "regra 4" in MANDA_GRAVAR.format(APRENDIZADO)
             and "`conhecimento/`" in MANDA_GRAVAR.format(APRENDIZADO))
        caso("a mensagem ensina o pedido de incorporação como sugestão",
             "sugestão" in mensagem and "incorporação" in mensagem)
        caso("a mensagem ensina a marcar quem revisa",
             "revisão" in mensagem and "território" in mensagem)
        caso("a mensagem diz onde se muda a lista",
             CHAVE_DOS_PROJETOS in mensagem
             and ARQUIVO_EXECUTOR in mensagem)

        caso("caminho absoluto é o mesmo repositório",
             recusa_do_pedido(pedido_de_escrita(
                 "Write", str(raiz / "projetos" / NOME_DO_SOMENTE_LEITURA
                              / "abs.py")), nomes, onde))
        caso("caminho fora de repositório nenhum passa",
             not recusa_do_pedido(pedido_de_escrita("Write", "/dev/null"),
                                  nomes, onde))
        caso("aspas desbalanceadas não derrubam o gancho",
             isinstance(acoes_do_comando(
                 "echo 'sem fechar > projetos/so-leitura/x.txt", onde), list))
        caso("documento literal não vira comando",
             not recusa_do_pedido(pedido_de_shell(
                 "python3 - <<'PY'\ngit -C projetos/so-leitura push\nPY"),
                 nomes, onde))
        caso("entrada sem ferramenta nem comando não devolve ação",
             acoes_do_pedido({}, onde) == [])
        caso("2>&1 não vira arquivo escrito",
             not recusa_do_pedido(pedido_de_shell(
                 "git -C projetos/so-leitura log 2>&1"), nomes, onde))

        falhas += [FALHA_COMPORTAMENTO.format(rotulo)
                   for rotulo, passou in comportamento if not passou]

    total = (len(BARRA) + len(SO_AVISA) + len(DEIXA_PASSAR)
             + len(comportamento))
    if falhas:
        for falha in falhas:
            print(LINHA_DE_FALHA.format(falha))
        print(RESUMO_FALHOU.format(len(falhas), total))
        return 1
    print(RESUMO_OK.format(total, len(BARRA), len(SO_AVISA),
                           len(DEIXA_PASSAR), len(comportamento)))
    return 0



def recusou_sem_entender(falha) -> bool:
    import contextlib
    import io
    saida = io.StringIO()
    with contextlib.redirect_stdout(saida):
        recusa_por_nao_entender(falha)
    try:
        dado = json.loads(saida.getvalue())["hookSpecificOutput"]
    except (ValueError, KeyError):
        return False
    return (dado.get("permissionDecision") == DECISAO_DE_NEGAR
            and type(falha).__name__
            in dado.get("permissionDecisionReason", ""))


def main() -> int:
    try:
        return decidir()
    except Exception as falha:
        return recusa_por_nao_entender(falha)


if __name__ == "__main__":
    if BANDEIRA_DE_TESTE in sys.argv:
        sys.exit(testar())
    sys.exit(main())
