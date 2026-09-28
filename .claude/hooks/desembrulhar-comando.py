import re
import sys
from pathlib import Path

BANDEIRA_DE_TESTE = "--testar"

SEPARADORES_DE_COMANDO = re.compile(r"&&|\|\||;|\||\n|\r|\$\(|`|\)")
ASPA_SIMPLES = "'"
ASPA_DUPLA = '"'
ASPAS = "\"'"
ESCAPE = "\\"

INTERPRETADORES = ("python", "python3", "node", "nodejs", "ruby",
                   "perl", "php")
SHELLS_QUE_RECEBEM_COMANDO = ("sh", "bash", "zsh", "dash", "ksh")
SHELLS_DO_POWERSHELL = ("pwsh", "powershell")
SHELLS_DO_WINDOWS = ("cmd",)
OPCAO_QUE_ENTREGA_O_COMANDO = "c"
AVALIADORES = ("eval", "iex", "invoke-expression")
AVALIADORES_DO_POWERSHELL = ("iex", "invoke-expression")
FERRAMENTA_BASH = "Bash"
FERRAMENTA_POWERSHELL = "PowerShell"
PROGRAMA_QUE_ENTREGA_A_ENTRADA_COMO_ARGUMENTO = "xargs"
OPCOES_DO_XARGS_QUE_LEVAM_VALOR = ("-I", "-L", "-n", "-P", "-d", "-E", "-s",
                                   "-a")
LANCADORES_DE_PROGRAMA = ("start-process", "saps", "start")
PARAMETROS_DO_PROGRAMA_LANCADO = ("filepath", "path", "pspath")
PARAMETROS_DOS_ARGUMENTOS_DO_LANCADO = ("argumentlist", "args")
CHAVES_DO_LANCADOR = ("wait", "nonewwindow", "passthru", "usenewenvironment",
                      "loaduserprofile")
SEPARADOR_DA_LISTA_DO_POWERSHELL = ","
DOCUMENTO_QUE_ABRE = re.compile(
    r"<<(?!<)(-?)[ \t]*((?:'[^'\n]*'|\"[^\"\n]*\"|\\.|[^\s;&|<>()'\"\\])+)")
CADEIA_QUE_NAO_ABRE_DOCUMENTO = "<<<"
MARCAS_QUE_TORNAM_O_DOCUMENTO_LITERAL = "'\"\\"
FECHO_DO_DOCUMENTO = r"\n{}{}[ \t\r]*(?=\n|\Z)"
TABULACOES_QUE_O_MENOS_TIRA = r"\t*"
QUEBRA_DE_LINHA = "\n"
COMENTARIO_DO_SHELL = "#"
ANTES_DO_COMENTARIO = " \t\n;&|("
SEPARADORES_DA_LINHA = re.compile(r"&&|\|\||;|\||&")
SHELLS_QUE_LEEM_O_DOCUMENTO = SHELLS_QUE_RECEBEM_COMANDO + SHELLS_DO_POWERSHELL
LETRA_DE_OPCAO = "-"
LETRAS_DE_OPCAO_DO_POWERSHELL = ("-", "/")
OPCAO_DO_COMANDO_DO_POWERSHELL = "command"
OPCAO_DO_COMANDO_CODIFICADO = "encodedcommand"
APELIDOS_DO_COMANDO_CODIFICADO = ("ec",)
OPCAO_DO_ARQUIVO_DO_POWERSHELL = "file"
CODIFICACAO_DO_COMANDO_CODIFICADO = "utf-16-le"
OPCOES_DO_CMD_QUE_ENTREGAM_O_COMANDO = ("/c", "/k")
TRACO_QUE_LE_A_ENTRADA = "-"
BANDEIRA_DO_SHELL_QUE_LE_A_ENTRADA = "s"
SUFIXO_DE_PROGRAMA_DO_WINDOWS = ".exe"
CADEIA_ENTREGUE_AO_SHELL = re.compile(
    r"<<<\s*('[^']*'|\"(?:\\.|[^\"\\])*\"|\S+)")
PREFIXOS_QUE_ENTREGAM_O_PROGRAMA = ("sudo", "env", "exec", "command",
                                    "nohup", "nice", "time")
PREFIXOS_QUE_INVOCAM_OUTRO = PREFIXOS_QUE_ENTREGAM_O_PROGRAMA + ("xargs",)
MARCA_DE_ATRIBUICAO = "="

MARCA_DE_ESCRITA_DENTRO_DO_SCRIPT = re.compile(
    r"""write|truncate|unlink|remove|rename|\bmkdir\b|['"]w[+bt]*['"]""")
ATRIBUICAO = re.compile(r"\s*(\w+)\s*=[^=]")
NOME_QUE_ESCREVE = re.compile(
    r"(\w+)\s*\.\s*(?:write_text|write_bytes|write|unlink|rename|mkdir)"
    r"|open\s*\(\s*(\w+)\s*,"
    r"|(?:copy|copyfile|move|rmtree)\s*\([^)]*?(\w+)\s*[,)]")
SUFIXOS_DE_ARQUIVO = (".py", ".md", ".json", ".yml", ".yaml", ".ts",
                      ".js", ".txt", ".jsonc")
TAMANHO_MINIMO_DE_LITERAL = 3
TAMANHO_MAXIMO_DE_LITERAL = 300


def literais_entre_aspas(linha: str) -> list:
    achados, aspa_aberta, atual = [], None, []
    i = 0
    while i < len(linha):
        c = linha[i]
        if aspa_aberta is None:
            if c in ASPAS:
                aspa_aberta, atual = c, []
        elif c == ESCAPE and i + 1 < len(linha):
            atual.append(linha[i + 1])
            i += 1
        elif c == aspa_aberta:
            achados.append("".join(atual))
            aspa_aberta = None
        else:
            atual.append(c)
        i += 1
    com_os_de_dentro = []
    for achado in achados:
        com_os_de_dentro.append(achado)
        if any(aspa in achado for aspa in ASPAS):
            com_os_de_dentro += literais_entre_aspas(achado)
    return [a for a in com_os_de_dentro
            if TAMANHO_MINIMO_DE_LITERAL <= len(a) <= TAMANHO_MAXIMO_DE_LITERAL]


def parece_caminho(texto: str) -> bool:
    return ("'" not in texto and '"' not in texto
            and ("/" in texto or texto.endswith(SUFIXOS_DE_ARQUIVO)))


def literais_que_parecem_caminho(linha: str) -> list:
    return [a for a in literais_entre_aspas(linha) if parece_caminho(a)]


def nome_do_programa(token: str) -> str:
    return Path(token.replace("\\", "/")).name.lower().removesuffix(
        SUFIXO_DE_PROGRAMA_DO_WINDOWS)


def chama_interpretador(comando: str) -> bool:
    for segmento in SEPARADORES_DE_COMANDO.split(comando):
        for token in segmento.split():
            if nome_do_programa(token) in INTERPRETADORES:
                return True
    return False


def nomes_que_a_linha_guarda(linha: str) -> list:
    achou = ATRIBUICAO.match(linha)
    return [achou.group(1)] if achou and literais_que_parecem_caminho(
        linha) else []


def nomes_que_a_linha_escreve(linha: str) -> list:
    return [grupo for m in NOME_QUE_ESCREVE.finditer(linha)
            for grupo in m.groups() if grupo]


def caminhos_escritos_dentro_do_script(comando: str) -> list:
    if not chama_interpretador(comando):
        return []
    if not MARCA_DE_ESCRITA_DENTRO_DO_SCRIPT.search(comando):
        return []
    escritos, por_nome = [], {}
    for linha in comando.splitlines():
        literais = literais_que_parecem_caminho(linha)
        if MARCA_DE_ESCRITA_DENTRO_DO_SCRIPT.search(linha):
            escritos += literais
        for nome in nomes_que_a_linha_guarda(linha):
            por_nome.setdefault(nome, []).extend(literais)
    for linha in comando.splitlines():
        if not MARCA_DE_ESCRITA_DENTRO_DO_SCRIPT.search(linha):
            continue
        for nome in nomes_que_a_linha_escreve(linha):
            escritos += por_nome.get(nome, [])
    return escritos


def sem_o_par_de_aspas_que_envolve(token: str) -> str:
    for aspa in (ASPA_DUPLA, ASPA_SIMPLES):
        if len(token) >= 2 and token.startswith(aspa) and token.endswith(aspa):
            return token[1:-1]
    return token


def tokens_crus_de(segmento: str) -> list:
    import shlex
    try:
        return shlex.split(segmento, posix=False)
    except ValueError:
        return segmento.split()


def entrega_o_comando(opcao: str) -> bool:
    return (opcao.startswith(LETRA_DE_OPCAO)
            and not opcao.startswith(LETRA_DE_OPCAO * 2)
            and OPCAO_QUE_ENTREGA_O_COMANDO in opcao[1:])


def sem_as_aspas_juntos(tokens: list) -> str:
    return " ".join(sem_o_par_de_aspas_que_envolve(t) for t in tokens)


def comando_decodificado(texto: str) -> str:
    import base64
    try:
        return base64.b64decode(sem_o_par_de_aspas_que_envolve(texto),
                                validate=True).decode(
            CODIFICACAO_DO_COMANDO_CODIFICADO)
    except ValueError:
        return ""


def corpo_entregue_ao_shell(segmento: str, resto: list) -> list:
    for j, token in enumerate(resto):
        if entrega_o_comando(token) and j + 1 < len(resto):
            return [sem_o_par_de_aspas_que_envolve(resto[j + 1])]
        if not token.startswith(LETRA_DE_OPCAO):
            break
    cadeia = CADEIA_ENTREGUE_AO_SHELL.search(segmento)
    return [sem_o_par_de_aspas_que_envolve(cadeia.group(1))] if cadeia else []


def e_opcao_do_powershell(token: str) -> bool:
    return len(token) > 1 and token[0] in LETRAS_DE_OPCAO_DO_POWERSHELL


def corpo_ou_leitura_da_entrada(corpo: str) -> list:
    return [] if corpo == TRACO_QUE_LE_A_ENTRADA else [corpo]


def corpo_entregue_ao_powershell(resto: list) -> list:
    for j, token in enumerate(resto):
        if not e_opcao_do_powershell(token):
            continue
        nome, seguintes = token[1:].lower(), resto[j + 1:]
        if OPCAO_DO_COMANDO_DO_POWERSHELL.startswith(nome) and seguintes:
            return corpo_ou_leitura_da_entrada(sem_as_aspas_juntos(seguintes))
        if seguintes and (nome in APELIDOS_DO_COMANDO_CODIFICADO
                          or OPCAO_DO_COMANDO_CODIFICADO.startswith(nome)):
            decodificado = comando_decodificado(seguintes[0])
            return [decodificado] if decodificado else []
        if OPCAO_DO_ARQUIVO_DO_POWERSHELL.startswith(nome):
            return []
    posicionais = [t for t in resto if not e_opcao_do_powershell(t)]
    return (corpo_ou_leitura_da_entrada(sem_as_aspas_juntos(posicionais))
            if posicionais else [])


def corpo_entregue_ao_cmd(resto: list) -> list:
    for j, token in enumerate(resto):
        if (token.lower() in OPCOES_DO_CMD_QUE_ENTREGAM_O_COMANDO
                and resto[j + 1:]):
            return [sem_as_aspas_juntos(resto[j + 1:])]
    return []


def sem_os_prefixos_que_invocam(tokens: list) -> list:
    restantes = list(tokens)
    while restantes and (
            nome_do_programa(restantes[0]) in PREFIXOS_QUE_INVOCAM_OUTRO
            or restantes[0].startswith(LETRA_DE_OPCAO)
            or MARCA_DE_ATRIBUICAO in restantes[0]):
        restantes.pop(0)
    return restantes


def e_o_parametro(nome: str, parametros: tuple) -> bool:
    return bool(nome) and (parametros[0].startswith(nome)
                           or nome in parametros[1:])


def comando_que_o_lancador_chama(resto: list) -> list:
    programa, argumentos, i = "", [], 0
    while i < len(resto):
        token = resto[i]
        if not (token.startswith(LETRA_DE_OPCAO) and len(token) > 1):
            argumentos += [token] if programa else []
            programa = programa or token
            i += 1
            continue
        nome = token[1:].lower().rstrip(":")
        seguinte = resto[i + 1:i + 2]
        if nome in CHAVES_DO_LANCADOR:
            i += 1
            continue
        if e_o_parametro(nome, PARAMETROS_DO_PROGRAMA_LANCADO):
            programa = seguinte[0] if seguinte else programa
        elif e_o_parametro(nome, PARAMETROS_DOS_ARGUMENTOS_DO_LANCADO):
            argumentos += seguinte
        i += 2
    lista = SEPARADOR_DA_LISTA_DO_POWERSHELL.join(argumentos).split(
        SEPARADOR_DA_LISTA_DO_POWERSHELL)
    partes = [sem_o_par_de_aspas_que_envolve(parte.strip())
              for parte in lista if parte.strip()]
    return ([" ".join([sem_o_par_de_aspas_que_envolve(programa)] + partes)]
            if programa else [])


def sem_os_prefixos_que_entregam_o_programa(tokens: list) -> list:
    restantes = list(tokens)
    while restantes and (
            nome_do_programa(restantes[0]) in PREFIXOS_QUE_ENTREGAM_O_PROGRAMA
            or restantes[0].startswith(LETRA_DE_OPCAO)
            or MARCA_DE_ATRIBUICAO in restantes[0]):
        restantes.pop(0)
    return restantes


def comando_que_o_xargs_entrega(segmento: str) -> list:
    tokens = sem_os_prefixos_que_entregam_o_programa(tokens_crus_de(segmento))
    if not tokens or nome_do_programa(tokens[0]) != (
            PROGRAMA_QUE_ENTREGA_A_ENTRADA_COMO_ARGUMENTO):
        return []
    i = 1
    while i < len(tokens) and tokens[i].startswith(LETRA_DE_OPCAO):
        i += 2 if tokens[i] in OPCOES_DO_XARGS_QUE_LEVAM_VALOR else 1
    return [" ".join(tokens[i:])] if tokens[i:] else []


def corpos_embrulhados(segmento: str) -> list:
    tokens = sem_os_prefixos_que_invocam(tokens_crus_de(segmento))
    if not tokens:
        return []
    nome, resto = nome_do_programa(tokens[0]), tokens[1:]
    if nome in AVALIADORES and resto:
        return [sem_as_aspas_juntos(resto)]
    if nome in SHELLS_QUE_RECEBEM_COMANDO:
        return corpo_entregue_ao_shell(segmento, resto)
    if nome in SHELLS_DO_POWERSHELL:
        return corpo_entregue_ao_powershell(resto)
    if nome in SHELLS_DO_WINDOWS:
        return corpo_entregue_ao_cmd(resto)
    if nome in LANCADORES_DE_PROGRAMA:
        return comando_que_o_lancador_chama(resto)
    return comando_que_o_xargs_entrega(segmento)


def shell_que_le_o_corpo(segmento: str) -> str:
    tokens = sem_os_prefixos_que_invocam(tokens_crus_de(segmento))
    nome = nome_do_programa(tokens[0]) if tokens else ""
    return (FERRAMENTA_POWERSHELL
            if nome in SHELLS_DO_POWERSHELL + AVALIADORES_DO_POWERSHELL
            else FERRAMENTA_BASH)


def bandeira_manda_ler_a_entrada(tokens: list) -> bool:
    return any(t.startswith(LETRA_DE_OPCAO)
               and not t.startswith(LETRA_DE_OPCAO * 2)
               and BANDEIRA_DO_SHELL_QUE_LE_A_ENTRADA in t[1:]
               for t in tokens)


def le_o_comando_da_entrada(segmento: str) -> bool:
    tokens = sem_os_prefixos_que_entregam_o_programa(tokens_crus_de(segmento))
    if not tokens:
        return False
    nome = nome_do_programa(tokens[0])
    argumentos = [t for t in tokens[1:] if not t.startswith(LETRA_DE_OPCAO)]
    if nome in SHELLS_QUE_RECEBEM_COMANDO:
        return not argumentos or bandeira_manda_ler_a_entrada(tokens[1:])
    if nome in SHELLS_DO_POWERSHELL:
        return not argumentos
    return nome in AVALIADORES and not tokens[1:]


def textos_que_chegam_pela_entrada(anterior: str) -> list:
    tokens = tokens_crus_de(anterior)
    textos = [sem_o_par_de_aspas_que_envolve(t) for t in tokens]
    return textos + ([sem_as_aspas_juntos(tokens[1:])]
                     if len(tokens) > 1 else [])


def com_os_corpos_desembrulhados(segmentos: list, separar,
                                 apos_cano: list = None) -> list:
    completos = []
    fila = list(segmentos)
    canos = list(apos_cano) if apos_cano is not None else [False] * len(fila)
    anterior = ""
    while fila:
        segmento = fila.pop(0)
        veio_pelo_cano = canos.pop(0) if canos else False
        completos.append(segmento)
        corpos = corpos_embrulhados(segmento)
        if (not corpos and anterior and veio_pelo_cano
                and le_o_comando_da_entrada(segmento)):
            corpos = textos_que_chegam_pela_entrada(anterior)
        shell = shell_que_le_o_corpo(segmento)
        for corpo in corpos:
            novos = list(separar(corpo, shell))
            fila = novos + fila
            canos = [False] * len(novos) + canos
        anterior = segmento
    return completos


def a_linha_entrega_o_documento_a_um_shell(linha: str) -> bool:
    for segmento in SEPARADORES_DA_LINHA.split(linha):
        tokens = sem_os_prefixos_que_invocam(tokens_crus_de(segmento))
        if tokens and nome_do_programa(sem_o_par_de_aspas_que_envolve(
                tokens[0])) in SHELLS_QUE_LEEM_O_DOCUMENTO:
            return True
    return False


def corpos_depois_da_linha(comando: str, quebra: int,
                           documentos: list) -> list:
    corpos, posicao = [], quebra
    for documento in documentos:
        menos, palavra = documento.groups()
        delimitador = "".join(letra for letra in palavra if letra
                              not in MARCAS_QUE_TORNAM_O_DOCUMENTO_LITERAL)
        fecho = re.compile(FECHO_DO_DOCUMENTO.format(
            TABULACOES_QUE_O_MENOS_TIRA if menos else "",
            re.escape(delimitador)))
        achado = fecho.search(comando, posicao)
        fim = achado.end() if achado else len(comando)
        corpos.append((posicao + 1, fim, delimitador != palavra))
        posicao = fim
    return corpos


def sem_os_documentos_que_sao_dado(comando: str) -> str:
    dados, abertos, aspa, i, inicio_da_linha = [], [], None, 0, 0
    while i < len(comando):
        c, passo = comando[i], 1
        if aspa == ASPA_SIMPLES:
            aspa = None if c == ASPA_SIMPLES else aspa
        elif c == ESCAPE:
            passo = 2
        elif aspa == ASPA_DUPLA:
            aspa = None if c == ASPA_DUPLA else aspa
        elif c in ASPAS:
            aspa = c
        elif comando.startswith(CADEIA_QUE_NAO_ABRE_DOCUMENTO, i):
            passo = len(CADEIA_QUE_NAO_ABRE_DOCUMENTO)
        elif documento := DOCUMENTO_QUE_ABRE.match(comando, i):
            abertos.append(documento)
            passo = documento.end() - i
        elif c == COMENTARIO_DO_SHELL and (
                i == 0 or comando[i - 1] in ANTES_DO_COMENTARIO):
            fim = comando.find(QUEBRA_DE_LINHA, i)
            passo = (fim if fim >= 0 else len(comando)) - i
        elif c == QUEBRA_DE_LINHA and abertos:
            e_comando = a_linha_entrega_o_documento_a_um_shell(
                comando[inicio_da_linha:i])
            corpos = corpos_depois_da_linha(comando, i, abertos)
            dados += [(inicio, fim) for inicio, fim, literal in corpos
                      if literal and not e_comando]
            abertos, passo = [], corpos[-1][1] - i
        if c == QUEBRA_DE_LINHA and aspa is None:
            inicio_da_linha = i + passo
        i += passo
    for inicio, fim in reversed(dados):
        comando = comando[:inicio] + comando[fim:]
    return comando


CASOS_DE_LITERAL = (
    ("aspa simples", "open('a/b.py', 'w')", ["a/b.py"]),
    ("aspa dupla", 'open("a/b.py", "w")', ["a/b.py"]),
    ("fechamento não vira abertura",
     "x = 'w'; y = 'z'; p = 'a/b.py'", ["a/b.py"]),
    ("literal dentro do corpo aspeado do -c",
     "python -c \"p = 'a/b.py'; open(p, 'w')\"", ["a/b.py"]),
)

VETADO = "git push --force origin main"
CASOS_DE_EMBRULHO = (
    ("sh -c", "sh -c 'git push --force origin main'",
     ["git push --force origin main"]),
    ("bash -lc", 'bash -lc "echo x > a.yml"', ["echo x > a.yml"]),
    ("eval", "eval 'git push origin main'", ["git push origin main"]),
    ("xargs sh -c", "xargs -I{} sh -c 'rm {}'", ["rm {}"]),
    ("o nome do shell como argumento do echo não é executor",
     "echo pwsh 'git push --force origin main'", []),
    ("o iex como argumento do grep não é executor",
     "grep iex 'git push --force origin main' arquivo.txt", []),
    ("sem embrulho", "echo 'git push'", []),
    ("bash sem -c roda um arquivo, não um corpo", "bash roteiro.sh", []),
    ("o iex do PowerShell é o eval dele", f"iex '{VETADO}'", [VETADO]),
    ("o Invoke-Expression por extenso também",
     f'Invoke-Expression "{VETADO}"', [VETADO]),
    ("pwsh -c entrega o comando", f'pwsh -c "{VETADO}"', [VETADO]),
    ("powershell -Command depois de outras opções",
     f'powershell -NoProfile -ExecutionPolicy Bypass -Command "{VETADO}"',
     [VETADO]),
    ("o powershell sem -Command toma o texto como comando",
     f'powershell "{VETADO}"', [VETADO]),
    ("pwsh -File roda um arquivo, não um corpo", "pwsh -File roteiro.ps1",
     []),
    ("cmd /c entrega o comando", f'cmd /c "{VETADO}"', [VETADO]),
    ("a cadeia do <<< é o comando que o bash lê", f"bash <<< '{VETADO}'",
     [VETADO]),
    ("bash.exe também é bash", f"bash.exe -c '{VETADO}'", [VETADO]),
    ("o xargs entrega o programa que vem depois dele", f"xargs {VETADO}",
     [VETADO]),
    ("o xargs entrega o programa depois da opção que leva valor",
     f"xargs -n 1 {VETADO}", [VETADO]),
    ("o Start-Process chama o programa com a lista de argumentos",
     "Start-Process git -ArgumentList 'push','--force','origin','main'",
     [VETADO]),
    ("o Start-Process com a lista num texto só",
     f"Start-Process -FilePath git -ArgumentList '{VETADO[4:]}'", [VETADO]),
    ("o saps é o Start-Process, e a lista vem na segunda posição",
     f"saps git '{VETADO[4:]}'", [VETADO]),
)

CASOS_DO_DOCUMENTO = (
    ("o corpo do documento literal lido pelo cat é dado",
     "cat <<'F'\nx\nF\ny", "cat <<'F'\n\ny"),
    ("o corpo do documento literal lido pelo bash é comando",
     "bash <<'F'\nx\nF", "bash <<'F'\nx\nF"),
    ("o corpo que desce pelo cano ao sh é comando",
     "cat <<'F' | sh\nx\nF", "cat <<'F' | sh\nx\nF"),
    ("a marca dentro de aspas não abre documento",
     "echo \"<<'F'\"\nx", "echo \"<<'F'\"\nx"),
    ("o corpo do documento que expande fica",
     "cat <<F\nx\nF", "cat <<F\nx\nF"),
    ("o resto da linha que abre o documento fica",
     "cat <<'F' > a.yml\nx\nF", "cat <<'F' > a.yml\n"),
)

CASOS_DO_SHELL_DO_CORPO = (
    ("o corpo do pwsh -c se lê como PowerShell", "pwsh -c 'x'", "PowerShell"),
    ("o corpo do iex se lê como PowerShell", "iex 'x'", "PowerShell"),
    ("o corpo do bash -c se lê como Bash", "bash -c 'x'", "Bash"),
    ("o corpo do eval se lê como Bash", "eval 'x'", "Bash"),
)

CASOS_DA_ENTRADA = (
    ("o texto do echo entregue ao sh pela entrada",
     [f"echo '{VETADO}' ", " sh"]),
    ("o texto do printf entregue ao bash pela entrada",
     [f"printf '%s' '{VETADO}' ", " bash"]),
    ("o texto entregue ao iex pela entrada",
     [f"'{VETADO}' ", " iex"]),
    ("o texto sem aspa entregue ao sh com opção", [f"echo {VETADO} ", " sh -s"]),
    ("o texto entregue ao bash -s com posicional pela entrada",
     [f"echo '{VETADO}' ", " bash -s x"]),
    ("o texto entregue ao sh -s -- com posicional pela entrada",
     [f"echo '{VETADO}' ", " sh -s -- x"]),
    ("o texto entregue ao powershell -Command - pela entrada",
     [f"echo '{VETADO}' ", " powershell -Command -"]),
    ("o texto entregue ao pwsh -c - pela entrada",
     [f"echo '{VETADO}' ", " pwsh -c -"]),
)
CASOS_DA_ENTRADA_QUE_NAO_E_COMANDO = (
    ("o grep que procura sh não roda o texto que chega",
     [f"echo '{VETADO}' ", " grep sh"]),
    ("o bash que roda um arquivo não lê a entrada como comando",
     [f"echo '{VETADO}' ", " bash roteiro.sh"]),
)
CASOS_QUE_NAO_SAO_CANO = (
    ("o texto antes do ; não é entregue ao shell seguinte",
     [f"echo '{VETADO}' ", " bash"], [False, False]),
    ("o shell nu depois do shell nu não entra em laço",
     ["bash", " bash"], [False, False]),
    ("o shell nu ligado por cano ao shell nu não entra em laço",
     ["bash", " bash"], [False, True]),
)


def canos_de_um_cano_so(segmentos: list) -> list:
    return [False] + [True] * (len(segmentos) - 1)


def testar() -> int:
    import base64
    falhas = []
    for rotulo, linha, esperado in CASOS_DE_LITERAL:
        veio = literais_que_parecem_caminho(linha)
        if veio != esperado:
            falhas.append(f"literal [{rotulo}]: esperava {esperado}, "
                          f"veio {veio}")
    for rotulo, segmento, esperado in CASOS_DE_EMBRULHO:
        veio = corpos_embrulhados(segmento)
        if veio != esperado:
            falhas.append(f"embrulho [{rotulo}]: esperava {esperado}, "
                          f"veio {veio}")
    codificado = base64.b64encode(
        VETADO.encode(CODIFICACAO_DO_COMANDO_CODIFICADO)).decode()
    veio = corpos_embrulhados(f"pwsh -EncodedCommand {codificado}")
    if veio != [VETADO]:
        falhas.append(f"embrulho [o -EncodedCommand se decodifica]: "
                      f"esperava {[VETADO]}, veio {veio}")
    for rotulo, comando, esperado in CASOS_DO_DOCUMENTO:
        veio = sem_os_documentos_que_sao_dado(comando)
        if veio != esperado:
            falhas.append(f"documento [{rotulo}]: esperava {esperado!r}, "
                          f"veio {veio!r}")
    for rotulo, segmento, esperado in CASOS_DO_SHELL_DO_CORPO:
        lidos = []
        com_os_corpos_desembrulhados(
            [segmento], lambda c, shell: lidos.append(shell) or [c])
        if lidos != [esperado]:
            falhas.append(f"shell do corpo [{rotulo}]: esperava {esperado}, "
                          f"veio {lidos}")
    for rotulo, segmentos in CASOS_DA_ENTRADA:
        veio = com_os_corpos_desembrulhados(
            segmentos, lambda c, _shell: [c],
            canos_de_um_cano_so(segmentos))
        if VETADO not in veio:
            falhas.append(f"entrada [{rotulo}]: o texto não virou corpo: "
                          f"{veio}")
    for rotulo, segmentos in CASOS_DA_ENTRADA_QUE_NAO_E_COMANDO:
        veio = com_os_corpos_desembrulhados(
            segmentos, lambda c, _shell: [c],
            canos_de_um_cano_so(segmentos))
        if VETADO in veio:
            falhas.append(f"entrada [{rotulo}]: o texto virou corpo: {veio}")
    for rotulo, segmentos, canos in CASOS_QUE_NAO_SAO_CANO:
        veio = com_os_corpos_desembrulhados(
            segmentos, lambda c, _shell: [c], canos)
        if VETADO in veio:
            falhas.append(f"não-cano [{rotulo}]: o texto virou corpo: {veio}")
    aninhado = com_os_corpos_desembrulhados(
        ["sh -c 'bash -c \"git push --force origin main\"'"],
        lambda c, _shell: [c])
    if aninhado[-1] != "git push --force origin main":
        falhas.append(f"embrulho aninhado não abriu: {aninhado}")
    python_em_c = caminhos_escritos_dentro_do_script(
        "python -c \"open('.github/workflows/e.yml','w').write('x')\"")
    if python_em_c != [".github/workflows/e.yml"]:
        falhas.append(f"python -c não achou o alvo: {python_em_c}")
    node_em_e = caminhos_escritos_dentro_do_script(
        "node -e \"require('fs').writeFileSync('projetos/x/a.py','x')\"")
    if node_em_e != ["projetos/x/a.py"]:
        falhas.append(f"node -e não achou o alvo: {node_em_e}")
    so_le = caminhos_escritos_dentro_do_script(
        "python -c \"print(open('projetos/x/a.py').read())\"")
    if so_le:
        falhas.append(f"leitura virou escrita: {so_le}")
    total = (len(CASOS_DE_LITERAL) + len(CASOS_DE_EMBRULHO) + 1
             + len(CASOS_DA_ENTRADA) + len(CASOS_DA_ENTRADA_QUE_NAO_E_COMANDO)
             + len(CASOS_QUE_NAO_SAO_CANO) + len(CASOS_DO_SHELL_DO_CORPO)
             + len(CASOS_DO_DOCUMENTO)
             + 4)
    for falha in falhas:
        print("FALHOU: " + falha)
    print(f"{'FALHOU' if falhas else 'OK'}: {total} casos — "
          "desembrulhar comando")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(testar() if BANDEIRA_DE_TESTE in sys.argv else 0)
