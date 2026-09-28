import json
import os
import re
import sys
import tempfile
from pathlib import Path

MARCA_DE_ETAPA_NO_AMBIENTE = "ENCADEADOR_ETAPA"
VARIAVEL_DA_RAIZ_DO_PROJETO = "CLAUDE_PROJECT_DIR"

FERRAMENTAS_DE_ESCRITA = ("Write", "Edit", "NotebookEdit")
CAMPOS_DE_CAMINHO = ("file_path", "notebook_path")
MODULO_QUE_DESEMBRULHA = "desembrulhar-comando.py"
CACHE_DO_DESEMBRULHADOR = []

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

BANDEIRAS_GLOBAIS_SIMPLES = {"--no-pager", "--paginate", "-p", "--bare",
                             "--literal-pathspecs"}
BANDEIRAS_GLOBAIS_QUE_COMEM_O_TOKEN_SEGUINTE = {
    "-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path",
    "-R", "--repo"}
BANDEIRA_DO_DIRETORIO_DO_GIT = ("-C",)

VERBOS_DO_GIT_QUE_ESCREVEM = {
    "add", "am", "apply", "checkout", "cherry-pick", "clean", "commit",
    "init", "merge", "mv", "push", "rebase", "reset", "restore", "revert",
    "rm", "stash", "switch"}
VERBOS_DO_GIT_QUE_SO_ESCREVEM_COM_ARGUMENTO = {
    "branch": {"--show-current", "--list", "-l", "-a", "--all", "-r",
               "--remotes", "-v", "-vv", "--verbose", "--contains",
               "--merged", "--no-merged", "--points-at"},
    "tag": {"--list", "-l", "-n", "--contains", "--points-at", "--merged"},
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
PROGRAMAS_COM_REDIRECIONAMENTO_PROPRIO = ("awk", "gawk", "mawk", "nawk")
REDIRECIONAMENTO_DE_DENTRO = re.compile(
    r">>?\s*[\"']([^\"']+)[\"']")
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

COMANDO_DD = "dd"
PREFIXO_DA_SAIDA_DO_DD = "of="

COMANDO_TAR = "tar"
BANDEIRAS_DE_EXTRACAO_DO_TAR = ("--extract", "--get")
BANDEIRAS_DE_CRIACAO_DO_TAR = ("--create",)
LETRA_DE_EXTRACAO_DO_TAR = "x"
LETRA_DE_CRIACAO_DO_TAR = "c"
LETRA_DO_ARQUIVO_DO_TAR = "f"
BANDEIRAS_DO_DIRETORIO_DO_TAR = ("-C", "--directory")
BANDEIRAS_DO_ARQUIVO_DO_TAR = ("-f", "--file")

COMANDOS_COM_DESTINO_POR_BANDEIRA = ("cp", "mv", "ln", "install")
BANDEIRAS_DO_DESTINO = ("-t", "--target-directory")

PREFIXO_DE_BANDEIRA = "-"
PREFIXO_DE_BANDEIRA_LONGA = "--"
DIRETORIO_CORRENTE = "."

PREFIXO_DOS_DISPOSITIVOS = "/dev/"

EVENTO_ANTES_DA_FERRAMENTA = "PreToolUse"
DECISAO_DE_NEGAR = "deny"
BANDEIRA_DE_TESTE = "--testar"
SEM_VERBO = -1
SEM_NOME = ""
SILENCIO = 0
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
LIMITE_CONFESSADO = (
    "O que esta cerca não cobre, dito de frente para ninguém confiar "
    "demais nela: ela lê o comando, não o que o programa faz por dentro. "
    "Escrita decidida dentro de um documento literal — `python3 - <<'PY' "
    "... PY`, e o mesmo com qualquer interpretador — atravessa sem ser "
    "vista. Isso não é permissão: é o limite do instrumento, e quem "
    "escreve fora da raiz por ali continua perdendo o trabalho na pasta "
    "temporária."
)

RECUSA = (
    "Regra 16 da camada: isto quer escrever em {!r}, que resolve para {} — "
    "fora da raiz desta execução, que é {}. Arquivo escrito fora da árvore "
    "não entra no commit desta branch de trabalho e some com a pasta que o "
    "guardou: a etapa seguinte encontra a árvore limpa e a execução termina "
    "sem entregar nada. Escreva dentro da raiz, de preferência por caminho "
    "relativo, e commite na branch de trabalho antes de fechar a sua "
    "evidência. Ler continua livre: `cat`, `grep`, `git log` e `sed -n` "
    "passam, aqui e lá fora. Esta cerca só existe enquanto uma etapa do "
    "executor de roteiros estiver rodando — é a marca {} no ambiente que a "
    "levanta; em sessão interativa do dono ela não morde.\n"
    + LIMITE_CONFESSADO
)
APRENDIZADO = (
    "durante etapa do executor de roteiros, escrever fora da raiz da "
    "execução é recusado: o caminho é relativo, dentro da árvore, e "
    "commitado na branch de trabalho."
)

PASTA_DO_RASCUNHO_DO_AGENTE = "claude"
SEPARADOR_DO_RASCUNHO = "-"
FALHA_BARRA = "BARRA [{}]: deixou passar"
FALHA_DEIXA_PASSAR = "DEIXA_PASSAR [{}]: barrou — {}"
FALHA_COMPORTAMENTO = "COMPORTAMENTO [{}]"
LINHA_DE_FALHA = "FALHOU: {}"
RESUMO_FALHOU = "FALHOU: {} de {} casos"
RESUMO_OK = "OK: {} casos — {} barrados, {} liberados, {} de comportamento"


def a_cerca_esta_de_pe(ambiente) -> bool:
    return bool((ambiente or {}).get(MARCA_DE_ETAPA_NO_AMBIENTE))


def raiz_da_execucao(entrada: dict, ambiente) -> Path:
    declarada = (ambiente or {}).get(VARIAVEL_DA_RAIZ_DO_PROJETO)
    bruta = declarada or (entrada or {}).get("cwd") or os.getcwd()
    try:
        return Path(bruta).resolve(strict=False)
    except OSError:
        return Path(bruta)


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


def separar(comando: str, ferramenta: str = FERRAMENTA_BASH) -> list:
    shell = shell_da_ferramenta(ferramenta)
    cortado = cortar_respeitando_aspas(comando, shell)
    if cortado is None:
        segmentos = CORTE_QUANDO_A_LEITURA_NAO_FECHA[shell].split(comando)
        apos_cano = [False] * len(segmentos)
    else:
        segmentos, apos_cano = cortado
    lidos, canos = com_a_leitura_do_shell(segmentos, shell, apos_cano)
    return desembrulhador().com_os_corpos_desembrulhados(
        lidos, separar, canos)


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


def e_git(token: str) -> bool:
    return Path(token.replace("\\", "/")).name.lower() in NOMES_DO_GIT


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


def letras_das_bandeiras_curtas(tokens: list) -> str:
    curtas = [t for t in tokens[1:]
              if t.startswith(PREFIXO_DE_BANDEIRA)
              and not t.startswith(PREFIXO_DE_BANDEIRA_LONGA)]
    return "".join(t[1:] for t in curtas)


def valor_depois_do_grupo_curto(tokens: list, letra: str) -> str:
    for i, token in enumerate(tokens):
        curta = token.startswith(PREFIXO_DE_BANDEIRA) \
            and not token.startswith(PREFIXO_DE_BANDEIRA_LONGA)
        if curta and token.endswith(letra) and i + 1 < len(tokens):
            return tokens[i + 1]
    return SEM_NOME


def caminho_escrito_pelo_git(tokens: list) -> str:
    if not verbo_do_git_que_escreve(tokens):
        return SEM_NOME
    return valor_da_bandeira(tokens, BANDEIRA_DO_DIRETORIO_DO_GIT) \
        or DIRETORIO_CORRENTE


def caminho_escrito_pelo_dd(tokens: list) -> str:
    for token in tokens[1:]:
        if token.startswith(PREFIXO_DA_SAIDA_DO_DD):
            return token[len(PREFIXO_DA_SAIDA_DO_DD):]
    return SEM_NOME


def caminho_escrito_pelo_tar(tokens: list) -> str:
    letras = letras_das_bandeiras_curtas(tokens)
    extrai = LETRA_DE_EXTRACAO_DO_TAR in letras \
        or any(b in tokens for b in BANDEIRAS_DE_EXTRACAO_DO_TAR)
    if extrai:
        return valor_da_bandeira(tokens, BANDEIRAS_DO_DIRETORIO_DO_TAR) \
            or DIRETORIO_CORRENTE
    cria = LETRA_DE_CRIACAO_DO_TAR in letras \
        or any(b in tokens for b in BANDEIRAS_DE_CRIACAO_DO_TAR)
    if cria:
        return valor_da_bandeira(tokens, BANDEIRAS_DO_ARQUIVO_DO_TAR) \
            or valor_depois_do_grupo_curto(tokens, LETRA_DO_ARQUIVO_DO_TAR)
    return SEM_NOME


def caminhos_escritos_por_bandeira(programa: str, tokens: list) -> list:
    if e_git(tokens[0]):
        return [caminho_escrito_pelo_git(tokens)]
    if programa == COMANDO_DD:
        return [caminho_escrito_pelo_dd(tokens)]
    if programa == COMANDO_TAR:
        return [caminho_escrito_pelo_tar(tokens)]
    if programa in COMANDOS_COM_DESTINO_POR_BANDEIRA:
        return [valor_da_bandeira(tokens, BANDEIRAS_DO_DESTINO)]
    return []


def caminhos_que_o_programa_redireciona(programa: str, tokens: list) -> list:
    if programa not in PROGRAMAS_COM_REDIRECIONAMENTO_PROPRIO:
        return []
    corpo = next((t for t in tokens[1:] if not t.startswith("-")), SEM_NOME)
    return [m.group(1)
            for m in REDIRECIONAMENTO_DE_DENTRO.finditer(corpo)]


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



def caminhos_escritos_pelo_segmento(segmento: str, tokens: list,
                                    onde: str) -> list:
    escritos = [m.group(1)
                for m in REDIRECIONAMENTO_DE_SHELL.finditer(segmento)]
    if tokens:
        programa = Path(tokens[0].replace("\\", "/")).name.lower()
        escritos += caminhos_que_o_programa_redireciona(programa, tokens)
        posicionais = [t for t in tokens[1:] if not t.startswith("-")]
        destino = valor_da_bandeira(tokens, BANDEIRAS_DO_DESTINO) \
            if programa in COMANDOS_COM_DESTINO_POR_BANDEIRA else SEM_NOME
        if programa in COMANDOS_QUE_ESCREVEM_NOS_ARGUMENTOS:
            escritos += posicionais
        elif programa in COMANDOS_QUE_ESCREVEM_NO_ULTIMO and posicionais \
                and not destino:
            escritos.append(posicionais[-1])
        elif programa in COMANDOS_QUE_ESCREVEM_NO_LUGAR \
                and escreve_no_lugar(tokens):
            escritos += arquivos_editados_no_lugar(programa, tokens, onde)
        escritos += caminhos_escritos_por_bandeira(programa, tokens)
        escritos += caminhos_escritos_na_opcao(programa, tokens)
    return [sem_o_par_de_aspas_que_envolve(e) for e in escritos if e]


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


def e_dispositivo(caminho: str) -> bool:
    return caminho.startswith(PREFIXO_DOS_DISPOSITIVOS)


def escritas_do_comando(comando: str, onde: str,
                        ferramenta: str = FERRAMENTA_BASH) -> list:
    escritas = []
    for segmento in separar(comando, ferramenta):
        tokens = partir_em_tokens(segmento.strip())
        for caminho in caminhos_escritos_pelo_segmento(segmento, tokens,
                                                       onde):
            escritas.append((caminho, resolver(caminho, onde)))
        if tokens and Path(tokens[0]).name == COMANDO_CD and len(tokens) > 1:
            destino = resolver(sem_o_par_de_aspas_que_envolve(tokens[1]), onde)
            onde = str(destino) if destino else onde
    return escritas


def escritas_do_pedido(entrada: dict, onde: str) -> list:
    dado = (entrada or {}).get("tool_input") or {}
    if (entrada or {}).get("tool_name") in FERRAMENTAS_DE_ESCRITA:
        for campo in CAMPOS_DE_CAMINHO:
            if dado.get(campo):
                return [(dado[campo], resolver(dado[campo], onde))]
        return []
    comando = dado.get("command", "")
    ferramenta = (entrada or {}).get("tool_name")
    return escritas_do_comando(comando, onde, ferramenta) if comando else []


def e_rascunho_do_agente(alvo) -> bool:
    try:
        dentro = alvo.resolve().relative_to(
            Path(tempfile.gettempdir()).resolve())
    except (ValueError, OSError):
        return False
    if not dentro.parts:
        return False
    primeira = dentro.parts[0]
    return primeira == PASTA_DO_RASCUNHO_DO_AGENTE or primeira.startswith(
        PASTA_DO_RASCUNHO_DO_AGENTE + SEPARADOR_DO_RASCUNHO)


def fora_da_raiz(declarado: str, alvo, raiz: Path) -> bool:
    if alvo is None or e_dispositivo(declarado):
        return False
    if e_rascunho_do_agente(alvo):
        return False
    return alvo != raiz and raiz not in alvo.parents


def recusa_do_pedido(entrada: dict, raiz: Path, onde: str):
    for declarado, alvo in escritas_do_pedido(entrada, onde):
        if fora_da_raiz(declarado, alvo, raiz):
            return declarado, alvo
    return None


def recusa_por_nao_entender(falha) -> int:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": EVENTO_ANTES_DA_FERRAMENTA,
        "permissionDecision": DECISAO_DE_NEGAR,
        "permissionDecisionReason": RECUSA_SEM_ENTENDER.format(
            type(falha).__name__, falha),
    }}))
    return SILENCIO


def decidir() -> int:
    if not a_cerca_esta_de_pe(os.environ):
        return SILENCIO
    try:
        entrada = json.load(sys.stdin)
        onde = entrada.get("cwd") or os.getcwd()
    except (json.JSONDecodeError, AttributeError, TypeError,
            ValueError) as falha:
        return recusa_por_nao_entender(falha)

    raiz = raiz_da_execucao(entrada, os.environ)
    recusa = recusa_do_pedido(entrada, raiz, onde)
    if not recusa:
        return SILENCIO

    declarado, alvo = recusa
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": EVENTO_ANTES_DA_FERRAMENTA,
        "permissionDecision": DECISAO_DE_NEGAR,
        "permissionDecisionReason": (
            RECUSA.format(declarado, alvo, raiz,
                          MARCA_DE_ETAPA_NO_AMBIENTE)
            + MANDA_GRAVAR.format(APRENDIZADO)),
    }}))
    return SILENCIO


def pedido_de_shell(comando: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": comando}}


def pedido_do_powershell(comando: str) -> dict:
    return {"tool_name": FERRAMENTA_POWERSHELL,
            "tool_input": {"command": comando}}


def pedido_de_escrita(ferramenta: str, caminho: str) -> dict:
    campo = "notebook_path" if ferramenta == "NotebookEdit" else "file_path"
    return {"tool_name": ferramenta, "tool_input": {campo: caminho}}


def montar_arvores_de_mentira(pasta: Path) -> None:
    (pasta / "raiz" / "sub").mkdir(parents=True, exist_ok=True)
    (pasta / "raiz" / "tmp").mkdir(parents=True, exist_ok=True)
    (pasta / "raiz" / "x.py").write_text("velho", encoding="utf-8")
    (pasta / "raiz-vizinha" / "sub").mkdir(parents=True, exist_ok=True)
    (pasta / "fora").mkdir(parents=True, exist_ok=True)
    (pasta / "fora" / "x.py").write_text("velho", encoding="utf-8")
    (pasta / "fora" / "roteiro.sed").write_text("s/a/b/\n", encoding="utf-8")
    (pasta / "raiz" / "sub" / "escreve.sed").write_text(
        f"w {(pasta / 'fora' / 'x.py').as_posix()}\n", encoding="utf-8")


def casos_que_barram(fora: str, vizinha: str) -> list:
    return [
        ("Write por caminho absoluto fora da raiz",
         pedido_de_escrita("Write", f"{fora}/novo.py")),
        ("pasta qualquer sob a temporária não é rascunho do agente — "
         "reconhecer o rascunho por prefixo não pode abrir a temporária "
         "inteira para escrita",
         pedido_de_escrita(
             "Write", f"{tempfile.gettempdir()}/claudia/x/nota.md")),
        ("nem uma que só comece com o nome, sem ser a pasta nem o formato "
         "com hífen",
         pedido_de_escrita(
             "Write", f"{tempfile.gettempdir()}/claudeoutra/x/nota.md")),
        ("Edit de arquivo que já existe fora",
         pedido_de_escrita("Edit", f"{fora}/x.py")),
        ("NotebookEdit fora",
         pedido_de_escrita("NotebookEdit", f"{fora}/n.ipynb")),
        ("redirecionamento para fora",
         pedido_de_shell(f"echo oi > {fora}/anotacao.txt")),
        ("redirecionamento que acrescenta fora",
         pedido_de_shell(f"echo oi >> {fora}/anotacao.txt")),
        ("copiar para fora",
         pedido_de_shell(f"cp raiz/x.py {fora}/copia.py")),
        ("mover para fora",
         pedido_de_shell(f"mv raiz/x.py {fora}/x.py")),
        ("apagar fora", pedido_de_shell(f"rm -rf {fora}/x.py")),
        ("criar pasta fora", pedido_de_shell(f"mkdir -p {fora}/nova")),
        ("sed no lugar fora", pedido_de_shell(f"sed -i 's/a/b/' {fora}/x.py")),
        ("tee fora", pedido_de_shell(f"echo oi | tee {fora}/x.txt")),
        ("curl -o fora", pedido_de_shell(
            f"curl -s -o {fora}/baixado.txt https://x/y")),
        ("wget -O fora", pedido_de_shell(
            f"wget -O {fora}/baixado.txt https://x/y")),
        ("rsync para fora", pedido_de_shell(f"rsync -a raiz/ {fora}/copia/")),
        ("perl -i fora", pedido_de_shell(f"perl -pi -e s/a/b/ {fora}/x.py")),
        ("touch fora", pedido_de_shell(f"touch {fora}/x.txt")),
        ("cd para fora e depois escrever por caminho relativo",
         pedido_de_shell(f"cd {fora} && echo oi > anotacao.txt")),
        ("pasta vizinha de nome parecido é fora, não dentro",
         pedido_de_escrita("Write", f"{vizinha}/sub/novo.py")),
        ("sed -i com o roteiro por -e e o arquivo fora",
         pedido_de_shell(f"sed -i -e 's/a/b/' {fora}/x.py")),
        ("sed -ie: o e colado ao i é sufixo, não roteiro",
         pedido_de_shell(f"sed -ie 's/a/b/' {fora}/x.py")),
        ("sed -i com um arquivo dentro e outro fora, os dois como arquivo",
         pedido_de_shell(f"sed -i 's/a/b/' sub/x.py {fora}/x.py")),
        ("sed -i com --expression= e o arquivo fora",
         pedido_de_shell(f"sed -i --expression='s/a/b/' {fora}/x.py")),
        ("sed -i com -- antes do arquivo fora",
         pedido_de_shell(f"sed -i -e 's/a/b/' -- {fora}/x.py")),
        ("sed -ni: o n antes do i não esconde o alvo",
         pedido_de_shell(f"sed -ni 's/a/b/p' {fora}/x.py")),
        ("perl para de ler opção no primeiro arquivo: o -e depois dele é "
         "arquivo, e o de fora também",
         pedido_de_shell(f"perl -pi -e 's/a/b/' sub/x.py -e {fora}/x.py")),
        ("o mesmo com o roteiro em arquivo e sem -e",
         pedido_de_shell(f"perl -pi roteiro.pl sub/x.py -e {fora}/x.py")),
        ("o comando w do roteiro escreve no arquivo que ele nomeia",
         pedido_de_shell(f"sed -i 'w {fora}/x.py' sub/x.py")),
        ("o mesmo com o comando W",
         pedido_de_shell(f"sed -i 'W {fora}/x.py' sub/x.py")),
        ("o mesmo com a bandeira w do s",
         pedido_de_shell(f"sed -i 's/a/b/w {fora}/x.py' sub/x.py")),
        ("o roteiro do -f que se lê e escreve com w",
         pedido_de_shell("sed -i -f sub/escreve.sed sub/x.py")),
        ("o roteiro do -f que não se lê volta a ser julgado como antes",
         pedido_de_shell(f"sed -i -f {fora}/ausente.sed sub/x.py")),
        ("a bandeira w do s depois de outra bandeira",
         pedido_de_shell(f"sed -i 's/a/b/gw {fora}/x.py' sub/x.py")),
        ("o comando w depois de um endereço por número",
         pedido_de_shell(f"sed -i '1w {fora}/x.py' sub/x.py")),
        ("o comando w depois de um endereço por expressão",
         pedido_de_shell(f"sed -i '/x/w {fora}/x.py' sub/x.py")),
        ("a / dentro do colchete não fecha a expressão do s",
         pedido_de_shell(f"sed -i 's/[/]/a/w {fora}/x.py' sub/x.py")),
        ("o ] logo depois do [ é literal e não fecha o colchete",
         pedido_de_shell(f"sed -i 's/[]/]/a/w {fora}/x.py' sub/x.py")),
        ("a contrabarra escapa o delimitador da expressão do s",
         pedido_de_shell(f"sed -i 's/\\/x/a/w {fora}/x.py' sub/x.py")),
        ("a / dentro do colchete não fecha o endereço por expressão",
         pedido_de_shell(f"sed -i '/[/]/w {fora}/x.py' sub/x.py")),
        ("a aspa escapada não abre aspa, e o rm entre dois echo é do shell",
         pedido_de_shell(f'echo \\" ; rm {fora}/x.py ; echo \\"')),
        ("a contrabarra no fim da linha junta o caminho de fora ao rm",
         pedido_de_shell(f"rm \\\n {fora}/x.py")),
        ("dentro da aspa simples a contrabarra não escapa, e a aspa fecha "
         "antes do rm", pedido_de_shell(f"echo 'a\\' ; rm {fora}/x.py")),
        ("o ponto e vírgula dentro do $() entre aspas duplas é do shell",
         pedido_de_shell(f'echo "$(true; rm {fora}/x.py)"')),
        ("o ponto e vírgula dentro da crase entre aspas duplas é do shell",
         pedido_de_shell(f'echo "`true; rm {fora}/x.py`"')),
        ("no PowerShell a contrabarra é texto, e a aspa fecha antes do rm",
         pedido_do_powershell(
             f'echo "a\\" ; rm {fora}/x.py ; echo \\"b"')),
        ("no PowerShell a crase escapa a aspa, e o rm entre dois echo é do "
         "shell", pedido_do_powershell(
             f'echo `"; rm {fora}/x.py; echo `"')),
        ("a aspa no corpo do documento que expande, dentro do $() entre "
         "aspas duplas, não esconde o rm",
         pedido_de_shell(f'echo "$(cat <<EOF\n\'\nEOF\n)"; '
                         f"rm {fora}/x.py\necho ')\"")),
        ("a contrabarra no fim da linha antes do comando some, e o rm fica "
         "inteiro", pedido_de_shell(f"\\\nrm {fora}/x.py")),
        ("a contrabarra no fim da linha depois do && também some",
         pedido_de_shell(f"true &&\\\nrm {fora}/x.py")),
        ("a marca de documento dentro da aspa não apaga o resto do comando",
         pedido_de_shell(f"echo \"<<'X'\"; rm {fora}/x.py")),
        ("o resto da linha que abre o documento literal é comando",
         pedido_de_shell(f"cat <<'EOF'; rm {fora}/x.py\nx\nEOF")),
        ("o redirecionamento depois da marca do documento literal é do "
         "shell", pedido_de_shell(f"cat <<'EOF' > {fora}/x.py\nx\nEOF")),
        ("o documento literal que o bash lê é comando",
         pedido_de_shell(f"bash <<'EOF'\nrm {fora}/x.py\nEOF")),
        ("o documento literal que vai pelo cano ao sh é comando",
         pedido_de_shell(f"cat <<'EOF' | sh\nrm {fora}/x.py\nEOF")),
        ("a aspa dentro do comentário não esconde a linha seguinte",
         pedido_de_shell(f"echo ok # \"\nrm {fora}/x.py\n# \"")),
        ("as chaves agrupam comandos",
         pedido_de_shell(f"{{ rm {fora}/x.py; }}")),
        ("a exclamação na frente não disfarça",
         pedido_de_shell(f"! rm {fora}/x.py")),
        ("o then do if não disfarça",
         pedido_de_shell(f"if true; then rm {fora}/x.py; fi")),
        ("o do do laço não disfarça",
         pedido_de_shell(f"for f in a; do rm {fora}/x.py; done")),
        ("no PowerShell o comentário de bloco na frente não disfarça",
         pedido_do_powershell(f"<# c #> rm {fora}/x.py")),
        ("no PowerShell a aspa dentro do comentário não esconde a linha "
         "seguinte",
         pedido_do_powershell(f"echo ok # \"\nrm {fora}/x.py\n# \"")),
        ("a contrabarra no meio do programa não disfarça o rm",
         pedido_de_shell(f"r\\m {fora}/x.py")),
        ("no PowerShell a crase no meio do programa não disfarça o rm",
         pedido_do_powershell(f"r`m {fora}/x.py")),
        ("eval embrulha o rm", pedido_de_shell(f'eval "rm {fora}/x.py"')),
        ("sh -c embrulha o rm", pedido_de_shell(f"sh -c 'rm {fora}/x.py'")),
        ("o texto que o echo entrega ao sh pelo cano é comando",
         pedido_de_shell(f"echo 'rm {fora}/x.py' | sh")),
        ("o texto que o printf entrega ao bash pelo cano é comando",
         pedido_de_shell(f"printf '%s' 'rm {fora}/x.py' | bash")),
        ("a cadeia do <<< entrega o rm ao bash",
         pedido_de_shell(f"bash <<< 'rm {fora}/x.py'")),
        ("pwsh -c embrulha o rm",
         pedido_de_shell(f'pwsh -c "rm {fora}/x.py"')),
        ("powershell -Command embrulha o rm",
         pedido_de_shell(f'powershell -NoProfile -Command "rm {fora}/x.py"')),
        ("cmd /c embrulha o rm",
         pedido_de_shell(f'cmd /c "rm {fora}/x.py"')),
        ("no PowerShell o Invoke-Expression embrulha o rm",
         pedido_do_powershell(f'Invoke-Expression "rm {fora}/x.py"')),
        ("no PowerShell o iex embrulha o rm",
         pedido_do_powershell(f"iex 'rm {fora}/x.py'")),
        ("no PowerShell o texto que chega ao iex pelo cano é comando",
         pedido_do_powershell(f"'rm {fora}/x.py' | iex")),
        ("o documento dentro do bash -c é comando",
         pedido_de_shell(
             f"bash -c \"$(cat <<'EOF'\nrm {fora}/x.py\nEOF\n)\"")),
        ("o documento dentro do eval é comando",
         pedido_de_shell(f"eval \"$(cat <<'EOF'\n"
                         f"rm {fora}/x.py\nEOF\n)\"")),
        ("o documento do bash -c com a substituição aberta na linha de cima "
         "é comando",
         pedido_de_shell(f"bash -c \"$(\ncat <<'EOF'\n"
                         f"rm {fora}/x.py\nEOF\n)\"")),
        ("o nome do shell entre aspas na frente do documento é comando",
         pedido_de_shell(f"\"bash\" <<EOF\nrm {fora}/x.py\nEOF")),
        ("o documento entregue ao sh com posicional é comando",
         pedido_de_shell(f"echo 'rm {fora}/x.py' | sh -s -- x")),
        ("o eval roda o texto que a substituição devolve",
         pedido_de_shell(f"eval $(echo 'rm {fora}/x.py')")),
        ("o source lê o comando da substituição de processo",
         pedido_de_shell(f"source <(echo 'rm {fora}/x.py')")),
        ("o |& entrega o texto ao bash como o cano",
         pedido_de_shell(f"echo 'rm {fora}/x.py' |& bash")),
        ("no PowerShell o iex roda o texto que o parêntese devolve",
         pedido_do_powershell(f"iex (echo 'rm {fora}/x.py')")),
    ]


def casos_dos_escapes_mecanicos(fora: str) -> list:
    return [
        ("git: verbo que escreve com -C para fora",
         pedido_de_shell(f"git -C {fora} commit -m mudanca")),
        ("git: init fora por -C", pedido_de_shell(f"git -C {fora} init")),
        ("dd: o valor de of= é o que ele escreve",
         pedido_de_shell(f"dd if=/dev/zero of={fora}/x.img bs=1 count=1")),
        ("tar: extração com -C para fora",
         pedido_de_shell(f"tar -xzf pacote.tar.gz -C {fora}")),
        ("tar: criação com -f escrevendo o pacote fora",
         pedido_de_shell(f"tar -czf {fora}/pacote.tar.gz sub")),
        ("tar: criação por bandeira longa fora",
         pedido_de_shell(f"tar --create --file={fora}/p.tar sub")),
        ("cp: destino por -t fora",
         pedido_de_shell(f"cp -t {fora} raiz/x.py")),
        ("mv: destino por --target-directory fora",
         pedido_de_shell(f"mv --target-directory={fora} raiz/x.py")),
        ("install: destino por -t fora",
         pedido_de_shell(f"install -t {fora} raiz/x.py")),
    ]


def casos_que_passam(raiz: str, fora: str) -> list:
    return [
        ("Write por caminho relativo dentro",
         pedido_de_escrita("Write", "sub/novo.py")),
        ("Write por caminho absoluto dentro",
         pedido_de_escrita("Write", f"{raiz}/sub/novo.py")),
        ("Edit dentro", pedido_de_escrita("Edit", f"{raiz}/x.py")),
        ("NotebookEdit dentro",
         pedido_de_escrita("NotebookEdit", "sub/n.ipynb")),
        ("a própria raiz não é fora dela mesma",
         pedido_de_shell(f"touch {raiz}")),
        ("redirecionamento dentro", pedido_de_shell("echo oi > tmp/x.txt")),
        ("mkdir dentro", pedido_de_shell("mkdir -p sub/nova")),
        ("cd para uma pasta de dentro e escrever lá",
         pedido_de_shell("cd sub && echo oi > x.txt")),
        ("o rascunho que o próprio agente recebe não é escrita fora",
         pedido_de_escrita(
             "Write",
             f"{tempfile.gettempdir()}/claude-1000/projeto/sessao/"
             "scratchpad/nota.md")),
        ("e escrever nele por shell também passa",
         pedido_de_shell(
             f"echo oi > {tempfile.gettempdir()}/claude-7/x/y/"
             "scratchpad/n.txt")),
        ("o rascunho no outro formato — pasta `claude` sem sufixo, com o "
         "projeto e a sessão abaixo — também é rascunho: a ferramenta grava "
         "assim nesta plataforma, e exigir o hífen deixava a sessão sem "
         "lugar para escrever",
         pedido_de_escrita(
             "Write",
             f"{tempfile.gettempdir()}/claude/projeto/sessao/"
             "scratchpad/nota.md")),
        ("e nele por shell também",
         pedido_de_shell(
             f"echo oi > {tempfile.gettempdir()}/claude/p/s/"
             "scratchpad/n.txt")),
        ("ler fora é livre", pedido_de_shell(f"cat {fora}/x.py")),
        ("varrer fora é livre", pedido_de_shell(f"grep -rn assunto {fora}")),
        ("git log fora é livre", pedido_de_shell(f"git -C {fora} log")),
        ("sed que só lê fora", pedido_de_shell(f"sed -n '1,5p' {fora}/x.py")),
        ("copiar de fora para dentro",
         pedido_de_shell(f"cp {fora}/x.py sub/copia.py")),
        ("escrever em /dev/null não é escrever em arquivo",
         pedido_de_shell("python3 -m json.tool > /dev/null")),
        ("2>&1 não vira arquivo escrito",
         pedido_de_shell(f"git -C {fora} log 2>&1")),
        ("git que só lê continua livre com -C fora",
         pedido_de_shell(f"git -C {fora} status --porcelain")),
        ("tar que só lista o pacote lá fora",
         pedido_de_shell(f"tar -tzf {fora}/pacote.tar.gz")),
        ("tar que extrai aqui dentro",
         pedido_de_shell("tar -xzf pacote.tar.gz")),
        ("dd que lê de fora e escreve dentro",
         pedido_de_shell(f"dd if={fora}/x.py of=sub/copia.py")),
        ("cp de fora para dentro com destino por -t",
         pedido_de_shell(f"cp -t sub {fora}/x.py")),
        ("roteiro do sed -i que começa com barra é roteiro, não caminho",
         pedido_de_shell("sed -i '/^#/d' sub/x.py")),
        ("o arquivo de roteiro do -f fora é lido, não escrito",
         pedido_de_shell(f"sed -i -f {fora}/roteiro.sed sub/x.py")),
        ("o mesmo com o -f depois de um -e",
         pedido_de_shell(f"sed -i -e 's/a/b/' -f {fora}/roteiro.sed sub/x.py")),
        ("o mesmo com --file e o valor separado",
         pedido_de_shell(f"sed -i --file {fora}/roteiro.sed sub/x.py")),
        ("perl -ni com o roteiro que começa com barra",
         pedido_de_shell("perl -ni -e '/^#/ or print' sub/x.py")),
        ("no sed a opção depois do arquivo continua opção: o -f de fora só "
         "é lido", pedido_de_shell(
             f"sed -i -e 's/a/b/' sub/x.py -f {fora}/roteiro.sed")),
        ("a bandeira w do s para a saída padrão não escreve em arquivo",
         pedido_de_shell("sed -i 's/a/b/w /dev/stdout' sub/x.py")),
        ("roteiro com palavra que tem w no meio não é o comando w",
         pedido_de_shell("sed -i 's/old/new/' sub/x.py")),
        ("o w no texto de substituição não é o comando w",
         pedido_de_shell("sed -i 's/a/w/' sub/x.py")),
        ("o w na expressão do s não é o comando w",
         pedido_de_shell("sed -i 's/w/x/' sub/x.py")),
        ("bandeira do s que não escreve",
         pedido_de_shell("sed -i 's/a/b/g' sub/x.py")),
        ("o w no y não é o comando w",
         pedido_de_shell("sed -i 'y/abc/wxy/' sub/x.py")),
        ("o w num endereço por expressão não é o comando w",
         pedido_de_shell("sed -i '/w/d' sub/x.py")),
        ("o comando w que escreve dentro da raiz",
         pedido_de_shell("sed -i '/^#/w sub/comentarios.txt' sub/x.py")),
        ("o colchete com a / dentro, num s que não escreve",
         pedido_de_shell("sed -i 's/[/]/x/g' sub/x.py")),
        ("a aspa dupla de verdade segura o ponto e vírgula",
         pedido_de_shell(f'echo "x; rm {fora}/x.py"')),
        ("a contrabarra dentro da aspa simples é texto, e a aspa segura o "
         "ponto e vírgula", pedido_de_shell(f"echo 'a\\b; rm {fora}/x.py'")),
        ("fora das aspas a contrabarra torna o ponto e vírgula texto",
         pedido_de_shell("echo x\\; y")),
        ("a aspa simples dentro do $() segura o ponto e vírgula",
         pedido_de_shell(f"echo \"$(echo 'a; rm {fora}/x.py')\"")),
        ("no PowerShell a crase escapa a aspa, e a aspa segue segurando o "
         "ponto e vírgula", pedido_do_powershell(
             f'echo "a`" ; rm {fora}/x.py ; echo `"b"')),
        ("no PowerShell a contrabarra não escapa, e a aspa abre o texto",
         pedido_do_powershell(
             f'echo \\" ; rm {fora}/x.py ; echo \\"')),
        ("no PowerShell a contrabarra na aspa simples é texto",
         pedido_do_powershell(f"echo 'a\\b; rm {fora}/x.py'")),
        ("o documento que expande só com texto é dado",
         pedido_de_shell(f"cat <<EOF\nrm {fora}/x.py\nEOF")),
        ("a cadeia do <<< é texto entre aspas",
         pedido_de_shell(f"cat <<< 'x; rm {fora}/x.py; y'")),
        ("depois do documento que expande a aspa volta a segurar o ponto e "
         "vírgula",
         pedido_de_shell(f"cat <<EOF\nx\nEOF\necho 'x; rm {fora}/x.py; y'")),
        ("o grep que procura sh não roda o texto que chega pelo cano",
         pedido_de_shell(f"echo 'rm {fora}/x.py' | grep sh")),
        ("o nome do shell dentro da aspa não faz do documento um comando",
         pedido_de_shell(f"echo \"conserta o bash $(cat <<'EOF'\n"
                         f"rm {fora}/x.py\nEOF\n)\"")),
        ("a mensagem do commit que vem do documento é dado",
         pedido_de_shell(f"git commit -m \"$(cat <<'EOF'\n"
                         f"rm {fora}/x.py\nEOF\n)\"")),
        ("o documento que o bash -c recebe como posicional é dado",
         pedido_de_shell(f"bash -c 'echo \"$1\"' x \"$(cat <<'EOF'\n"
                         f"rm {fora}/x.py\nEOF\n)\"")),
        ("o documento literal sem terminador é dado, não comando",
         pedido_de_shell(f"cat <<'EOF'\nrm {fora}/x.py")),
        ("o nome do shell como argumento do grep na linha do documento é dado",
         pedido_de_shell(f"cat <<'EOF' | grep -c bash\nrm {fora}/x.py\nEOF")),
        ("o nome do shell como argumento do echo não é executor",
         pedido_de_shell(f"echo pwsh 'rm {fora}/x.py'")),
        ("o texto antes do ponto e vírgula não vai ao shell seguinte",
         pedido_de_shell(f"echo 'rm {fora}/x.py'; bash -s")),
        ("dois shells nus seguidos não entram em laço",
         pedido_de_shell("bash; bash")),
    ]


def testar() -> int:
    falhas, comportamento = [], []
    with tempfile.TemporaryDirectory(prefix="veto-fora-da-execucao-") as tmp:
        base = Path(tmp).resolve()
        montar_arvores_de_mentira(base)
        raiz = base / "raiz"
        fora = str(base / "fora")
        vizinha = str(base / "raiz-vizinha")
        onde = str(raiz)

        barra = casos_que_barram(fora, vizinha) \
            + casos_dos_escapes_mecanicos(fora)
        passa = casos_que_passam(str(raiz), fora)
        for rotulo, pedido in barra:
            if not recusa_do_pedido(pedido, raiz, onde):
                falhas.append(FALHA_BARRA.format(rotulo))
        for rotulo, pedido in passa:
            recusa = recusa_do_pedido(pedido, raiz, onde)
            if recusa:
                falhas.append(FALHA_DEIXA_PASSAR.format(rotulo, recusa[0]))

        def caso(rotulo, condicao):
            comportamento.append((rotulo, bool(condicao)))

        caso("gancho que veta e não entende o pedido recusa, e nomeia a "
             "falha — quem não consegue julgar não pode dizer sim",
             recusou_sem_entender(TypeError("forma que o gancho não conhece")))
        caso("sem a marca da etapa no ambiente a cerca nem se levanta",
             not a_cerca_esta_de_pe({})
             and not a_cerca_esta_de_pe({"OUTRA": "1"}))
        caso("com a marca da etapa no ambiente a cerca se levanta",
             a_cerca_esta_de_pe({MARCA_DE_ETAPA_NO_AMBIENTE: "1"}))
        caso("a raiz declarada no ambiente manda",
             raiz_da_execucao({"cwd": fora},
                              {VARIAVEL_DA_RAIZ_DO_PROJETO: str(raiz)})
             == raiz)
        caso("sem raiz declarada, ela sai do cwd do pedido",
             raiz_da_execucao({"cwd": str(raiz)}, {}) == raiz)

        recusa = recusa_do_pedido(barra[0][1], raiz, onde) or ("", "")
        mensagem = (RECUSA.format(recusa[0], recusa[1], raiz,
                                  MARCA_DE_ETAPA_NO_AMBIENTE)
                    + MANDA_GRAVAR.format(APRENDIZADO))
        caso("a mensagem nomeia o caminho pedido", fora in mensagem)
        caso("a mensagem nomeia a raiz da execução", str(raiz) in mensagem)
        caso("a mensagem ensina o caminho que existe: escrever dentro e "
             "commitar", "commite" in mensagem and "Escreva dentro" in mensagem)
        caso("a mensagem diz que ler continua livre", "Ler continua livre"
             in mensagem)
        caso("a mensagem diz quem levanta a cerca",
             MARCA_DE_ETAPA_NO_AMBIENTE in mensagem)
        caso("a mensagem nomeia a regra 16, que é o que a motivou",
             "Regra 16" in mensagem)
        caso("a mensagem confessa o limite que o caso acima registra: "
             "escrita dentro de documento literal atravessa",
             "documento literal" in mensagem
             and "atravessa" in mensagem)
        caso("a mensagem manda gravar o aprendizado em conhecimento/, "
             "com a linha concreta",
             "regra 4" in mensagem and "`conhecimento/`" in mensagem
             and APRENDIZADO in mensagem)

        caso("entrada sem ferramenta nem comando não devolve escrita",
             escritas_do_pedido({}, onde) == [])
        caso("aspas desbalanceadas não derrubam o gancho",
             isinstance(escritas_do_comando(
                 f"echo 'sem fechar > {fora}/x.txt", onde), list))
        caso("Write sem caminho não devolve escrita",
             escritas_do_pedido({"tool_name": "Write", "tool_input": {}},
                                onde) == [])
        caso("o gancho lê o comando, não o que o programa faz por dentro — "
             "limite confessado: escrita dentro de documento literal passa",
             not recusa_do_pedido(pedido_de_shell(
                 f"python3 - <<'PY'\nopen('{fora}/x','w')\nPY"), raiz, onde))
        caso("awk que redireciona por dentro do próprio programa é escrita, "
             "e a cerca passou a lê-lo",
             bool(recusa_do_pedido(pedido_de_shell(
                 "awk '{print > \"%s/x.txt\"}' raiz/x.py" % fora),
                 raiz, onde)))
        caso("awk que redireciona para dentro da raiz segue livre",
             not recusa_do_pedido(pedido_de_shell(
                 "awk '{print > \"sub/x.txt\"}' raiz/x.py"), raiz, onde))
        caso("awk que só lê não vira escrita",
             not recusa_do_pedido(pedido_de_shell(
                 "awk '{print $1}' %s/x.py" % fora), raiz, onde))

        falhas += [FALHA_COMPORTAMENTO.format(rotulo)
                   for rotulo, passou in comportamento if not passou]

    total = len(barra) + len(passa) + len(comportamento)
    if falhas:
        for falha in falhas:
            print(LINHA_DE_FALHA.format(falha))
        print(RESUMO_FALHOU.format(len(falhas), total))
        return 1
    print(RESUMO_OK.format(total, len(barra), len(passa), len(comportamento)))
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
