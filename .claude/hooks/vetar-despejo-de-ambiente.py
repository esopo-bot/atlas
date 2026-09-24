import json
import os
import re
import shlex
import sys

EVENTO_ANTES_DA_FERRAMENTA = "PreToolUse"
DECISAO_DE_NEGAR = "deny"
DECISAO_DE_PERGUNTAR = "ask"
CAMPO_DO_MODO_DE_PERMISSAO = "permission_mode"
MODO_QUE_NAO_MOSTRA_A_PERGUNTA_DO_GANCHO = "bypassPermissions"
MARCA_DE_ETAPA_NO_AMBIENTE = "ENCADEADOR_ETAPA"
BANDEIRA_DE_TESTE = "--testar"
SILENCIO = 0
PASSA = ""

CAMPO_DA_ENTRADA = "tool_input"
CAMPO_DO_COMANDO = "command"

SEPARADORES_DE_COMANDO = re.compile(r"&&|\|\||\||;|\n|\r|\d*&?>>?")
DOCUMENTO_LITERAL = re.compile(
    r"^(?P<abertura>[^\n]*?<<-?\s*(?P<aspa>['\"]?)(?P<marca>\w+)(?P=aspa)"
    r"[^\n]*)\n(?P<corpo>.*?)(?:^(?P=marca)\s*$|\Z)", re.S | re.M)
INTERPRETADORES_QUE_EXECUTAM_O_DOCUMENTO = (
    "python", "python3", "node", "nodejs", "ruby", "perl", "php",
    "sh", "bash", "zsh", "dash", "ksh", "pwsh", "powershell")
INTERPRETADORES_DE_SHELL = ("sh", "bash", "zsh", "dash", "ksh")
SUBSTITUICAO_QUE_EXECUTA = ("$(", "`")
ABRE_SUBSTITUICAO = "$("
PROFUNDIDADE_DO_PARENTESE = {"(": 1, ")": -1}
ABRE_ASPA_ANSI = "$'"
CRASE = "`"
CONTRABARRA = "\\"
ASPA_SIMPLES = "'"
ASPA_DUPLA = '"'
FECHA_GRUPO = ")"
PALAVRA_QUE_O_SHELL_TROCA = "''"
NO_CORPO = "corpo do documento"
NA_SUBSTITUICAO = "substituição"
NA_CRASE = "crase"
NA_ASPA_SIMPLES = "aspa simples"
NA_ASPA_DUPLA = "aspa dupla"
NA_ASPA_ANSI = "aspa $'...'"
GUARDAM_COMANDO = (NA_SUBSTITUICAO, NA_CRASE)
ABRE_ASPA_NO_COMANDO = {ASPA_SIMPLES: NA_ASPA_SIMPLES, ASPA_DUPLA: NA_ASPA_DUPLA}
ATRIBUICAO_DE_AMBIENTE = re.compile(r"^[A-Za-z_]\w*=")
PREFIXOS_TRANSPARENTES = ("command", "builtin", "exec", "sudo", "nohup", "time")
ASPAS = "\"'"
MARCA_DE_OPCAO = "-"
BARRA_DE_CAMINHO = "/"
DESPEJAM_TUDO_SEM_ARGUMENTO = ("env", "printenv")
LISTA_TUDO_SEM_ARGUMENTO = "set"
EXPORTA = "export"
OPCAO_QUE_LISTA_O_EXPORTADO = "-p"
DECLARAM = ("declare", "typeset")
OPCOES_DE_DECLARE_QUE_DESPEJAM = ("-x", "-p")
SUBSTITUICAO_QUE_DESPEJA = re.compile(r"(?:\$\(|`)\s*(env|printenv)\s*(?:\)|`)")
ENVIRON_DO_PROCESSO = re.compile(r"/proc/(?:self|\d+|\$\w+|\$\{\w+\})/environ")

FERRAMENTAS_DE_BUSCA = ("grep", "rg", "egrep", "fgrep", "findstr",
                        "select-string", "sls", "ag", "ack", "git")
ITERACAO_DO_AMBIENTE = re.compile(
    r"\bfor\s+[\w\s,()]+?\s+in\s+"
    r"(?:(?:dict|list|sorted|iter|enumerate|set|tuple)\()?"
    r"os\.environ(?:\.(?:items|keys|values)\(\))?\)?\s*(?::|\]|\)|\bif\b|$)",
    re.M)
METODO_QUE_DESPEJA_VALORES = re.compile(r"\bos\.environ\.(?:items|values)\(\)")
CHAMADA_COM_O_AMBIENTE_INTEIRO = re.compile(
    r"\b(\w+(?:\.\w+)*)\(\s*os\.environ\s*[,)]")
CHAMADAS_QUE_SO_LISTAM_NOMES = frozenset({
    "list", "sorted", "len", "set", "frozenset", "tuple", "iter",
    "enumerate", "bool"})

LISTAGEM_DO_AMBIENTE_NO_POWERSHELL = re.compile(
    r"\b(?:Get-ChildItem|gci|dir|ls|Get-Item|gi)\s+(?:-Path\s+)?env:\\?"
    r"(?:[\w*?]*[*?][\w*?]*)?\s*(?:$|\||;)", re.I | re.M)
TODAS_AS_VARIAVEIS_NO_POWERSHELL = re.compile(
    r"GetEnvironmentVariables\(\)\s*(?:$|\||;)", re.I | re.M)

RECUSA = (
    "Regra 8 da camada: este comando despeja o ambiente sem nomear a variável "
    "— `{}`. Ambiente se lê por variável NOMEADA: `echo \"$NOME\"`, "
    "`printenv NOME`, `os.environ.get('NOME')`, `$env:NOME`. Despejo largo "
    "põe credencial no transcript, que não se apaga — o token de mensageria "
    "da sessão já foi impresso assim uma vez, e filtrar por "
    "padrão de nome (`if 'X' in k`) não muda nada, porque o valor vai junto. "
    "Se o que falta é o nome, liste só NOMES — `compgen -e` no bash, "
    "`(gci env:).Name` no PowerShell, `sorted(os.environ)` no Python — e "
    "depois leia a variável pelo nome."
)
MANDA_GRAVAR = (
    "\nGrave o aprendizado antes de tentar de novo — regra 4, a memória "
    "mora no disco, e recusa que a próxima sessão repete não ensinou "
    "nada. A linha, em `conhecimento/`:\n"
    "    {}"
)
APRENDIZADO = (
    "ambiente se lê por variável NOMEADA; despejo largo (`env`, `printenv`, "
    "`os.environ` inteiro, `gci env:`) põe credencial no transcript, que não "
    "se apaga (regra 8)."
)
RECUSA_SEM_ENTENDER = (
    "Este gancho não entendeu o pedido, e por isso recusa em vez de liberar: "
    "{} — {}. Quem veta e não consegue julgar não pode dizer sim: a parede "
    "sumiria em silêncio, e o verde passaria a significar `ninguém olhou`. "
    "Se o pedido é legítimo, conserte o gancho ou desligue-o em "
    ".claude/settings.json — o caminho nunca é atravessar por aqui."
)

BARRA_O_COMANDO = [
    ("env sozinho", "env"),
    ("env despejado num grep filtrado por nome — o valor vai junto",
     "env | grep -i claude"),
    ("printenv sozinho", "printenv"),
    ("printenv só com opção", "printenv -0"),
    ("export -p", "export -p"),
    ("export sem argumento também lista tudo", "export"),
    ("declare -x sem nome", "declare -x"),
    ("set sozinho", "set"),
    ("set sozinho no meio do encadeamento", "cd /tmp && set | head -50"),
    ("env por caminho absoluto", "/usr/bin/env"),
    ("env dentro de substituição de comando", "echo $(env)"),
    ("atribuição antes do env não o disfarça", "LC_ALL=C env"),
    ("environ do próprio processo",
     "cat /proc/self/environ | tr '\\0' '\\n'"),
    ("environ de outro processo", "strings /proc/1234/environ"),
    ("o caso que estreou a cerca: os.environ iterado e filtrado por nome",
     "python -c \"import os; [print(k, os.environ[k]) for k in os.environ "
     "if 'CLAUDE' in k.upper()]\""),
    ("os.environ.items()",
     "python -c \"import os; print(dict(os.environ.items()))\""),
    ("dict(os.environ) serializado",
     "python -c \"import os, json; print(json.dumps(dict(os.environ)))\""),
    ("print(os.environ)", "python -c \"import os; print(os.environ)\""),
    ("laço sobre items() em documento literal",
     "python - <<'PY'\nimport os\nfor k, v in os.environ.items():\n"
     "    print(k, v)\nPY"),
    ("laço sobre os.environ inteiro, mesmo só imprimindo a chave",
     "python -c \"import os\nfor k in os.environ:\n    print(k)\""),
    ("Get-ChildItem Env:", "Get-ChildItem Env:"),
    ("gci env:", "gci env:"),
    ("dir env:", "dir env:"),
    ("ls env: com pipe", "ls env: | Out-String"),
    ("gci env: filtrado por curinga", "gci env:CLAUDE*"),
    ("GetEnvironmentVariables() inteiro",
     "[Environment]::GetEnvironmentVariables()"),
    ("env despejado num arquivo", "env > /tmp/ambiente.txt"),
    ("env anexado num arquivo", "env >> /tmp/ambiente.txt"),
    ("env com o erro junto", "env 2>&1 | head"),
    ("printenv despejado num arquivo", "printenv > /tmp/ambiente.txt"),
    ("documento sem aspas alimentando o python ainda executa",
     "python - <<PY\nimport os\nprint(dict(os.environ))\nPY"),
    ("documento sem aspas com substituição que despeja",
     "cat <<FIM\n$(env)\nFIM"),
    ("comando depois do documento segue sendo julgado",
     "cat <<'FIM'\nx\nFIM\nenv"),
    ("declare -p sem nome", "declare -p"),
    ("documento que alimenta o bash é comando do shell: declare -p segue "
     "negado", "bash <<'FIM'\ndeclare -p\nFIM"),
    ("declare -x depois do documento do python segue negado",
     "python - <<'FIM'\nprint(1)\nFIM\ndeclare -x"),
    ("documento sem aspas executa o $(...) do corpo, seja quem for que o "
     "leia", "cat <<EOF\n$(\ndeclare -p\n)\nEOF"),
    ("documento sem aspas executa a crase do corpo",
     "cat <<EOF\n`declare -p`\nEOF"),
    ("documento sem aspas do python também executa o $(...) do corpo",
     "python - <<EOF\n$(declare -p)\nEOF"),
    ("substituição dentro de substituição também é comando do shell",
     "cat <<EOF\n$(echo $(declare -x))\nEOF"),
    ("o ) entre aspas simples não fecha a substituição",
     "cat <<EOF\n$(printf ')'; declare -p)\nEOF"),
    ("o ) entre aspas duplas não fecha a substituição",
     "cat <<EOF\n$(echo \")\"; declare -p)\nEOF"),
    ("dentro de $'...' a contrabarra escapa a aspa, e o ) não fecha",
     "cat <<EOF\n$(printf $'\\')'; declare -p)\nEOF"),
    ("a contrabarra antes do nome do comando não o esconde",
     "cat <<EOF\n$(\\declare -p)\nEOF"),
    ("contrabarra escapada não escapa o $ seguinte",
     "cat <<EOF\n\\\\$(declare -p)\nEOF"),
    ("substituição entre aspas duplas dentro da substituição executa",
     "cat <<EOF\n$(echo \"$(declare -p)\")\nEOF"),
]
DEIXA_PASSAR = [
    ("echo de variável nomeada", "echo $CLAUDE_PROJECT_DIR"),
    ("echo de variável entre aspas", 'echo "$HOME"'),
    ("printenv com nome", "printenv HOME"),
    ("env como lançador", "env python x.py"),
    ("env -i com comando depois", "env -i PATH=/usr/bin python x.py"),
    ("os.environ.get nomeado",
     "python -c \"import os; print(os.environ.get('HOME'))\""),
    ("os.environ indexado pelo nome",
     "python -c \"import os; print(os.environ['HOME'])\""),
    ("os.getenv", "python -c \"import os; print(os.getenv('HOME'))\""),
    ("teste de pertinência não despeja",
     "python -c \"import os; print('HOME' in os.environ)\""),
    ("ambiente espalhado para o filho",
     "python -c \"import os, subprocess; subprocess.run(['x'], "
     "env={**os.environ, 'A': '1'})\""),
    ("ambiente inteiro entregue ao filho por env=",
     "python -c \"import os, subprocess; subprocess.run(['x'], "
     "env=os.environ)\""),
    ("os.environ.copy() para montar o ambiente do filho",
     "python -c \"import os; e = os.environ.copy()\""),
    ("só os nomes, por sorted", "python -c \"import os; print(sorted(os.environ))\""),
    ("$env:NOME", "echo $env:HOME"),
    ("Get-Item Env:NOME", "Get-Item Env:HOME"),
    ("gci env:NOME sem curinga", "gci env:HOME"),
    ("(gci env:).Name lista só nomes", "(gci env:).Name"),
    ("git config --get-regexp", "git config --get-regexp user"),
    ("set -e", "set -e"),
    ("set -o pipefail", "set -o pipefail"),
    ("set -x", "set -x"),
    ("export com atribuição", "export FOO=1"),
    ("declare -x com nome", "declare -x FOO=1"),
    ("grep pelo código que itera o ambiente é busca, não despejo",
     "grep -rn \"for k in os.environ\" D:/x/src"),
    ("compgen -e lista só nomes", "compgen -e"),
    ("pasta chamada env", "ls env"),
    ("a palavra environ em outro contexto", "cat D:/x/docs/environ.md"),
    ("comando vazio", ""),
    ("documentar a regra 8 num documento literal não dispara a regra 8",
     "cat > conhecimento/regra-8.md <<'FIM'\nNão itere "
     "`os.environ.items()` nem rode `env | grep`.\nFIM"),
    ("documento literal para o gh com env dentro é texto",
     "gh issue comment 1 --body-file - <<'FIM'\nenv | grep x\nFIM"),
    ("documento sem aspas mas sem substituição também é texto",
     "cat > nota.md <<FIM\nfor k, v in os.environ.items()\nFIM"),
    ("variável nomeada despejada em arquivo", "echo $HOME > /tmp/x.txt"),
    ("DECLARE do SQL num documento que o python lê é código do python, não "
     "o declare do shell",
     "python - <<'EOF'\nsql = '''\nDO $$\nDECLARE\n    v_total integer;\n"
     "BEGIN\n    SELECT count(*) INTO v_total FROM t;\nEND $$;\n'''\n"
     "print(sql)\nEOF"),
    ("declare minúsculo do SQL, no documento do python, também",
     "python - <<'EOF'\nsql = 'do $$; declare; begin; end $$'\nEOF"),
    ("no documento que o cat lê, só a substituição executa: a linha env "
     "ao lado dela é texto", "cat <<FIM\n$(date)\nenv\nFIM"),
    ("DECLARE do SQL num documento sem aspas do python segue texto, ao lado "
     "de uma substituição inofensiva",
     "python - <<EOF\nsql = '''\nDO $$\nDECLARE\n    v_total integer;\n"
     "BEGIN\nEND $$;\n'''\nprint('$(date)')\nEOF"),
    ("no documento entre aspas nada se expande: $(declare -p) é texto",
     "cat <<'EOF'\n$(declare -p)\nEOF"),
    ("no documento sem aspas, \\$ torna a substituição literal",
     "cat <<EOF\n\\$(declare -p)\nEOF"),
    ("a mesma contrabarra vale para o $(env)",
     "cat <<EOF\n\\$(env)\nEOF"),
    ("dentro da substituição, o que está entre aspas simples é literal",
     "cat <<EOF\n$(printf '%s' '$(declare -p)')\nEOF"),
]


def sem_aspas(token: str) -> str:
    if len(token) >= 2 and token[0] in ASPAS and token[-1] == token[0]:
        return token[1:-1]
    return token


def tokens_de(segmento: str) -> list:
    try:
        return [sem_aspas(t) for t in shlex.split(segmento, posix=False)]
    except ValueError:
        return [sem_aspas(t) for t in segmento.split()]


def comando_e_argumentos(tokens: list) -> tuple:
    restantes = list(tokens)
    while restantes and (ATRIBUICAO_DE_AMBIENTE.match(restantes[0])
                         or restantes[0] in PREFIXOS_TRANSPARENTES):
        restantes.pop(0)
    if not restantes:
        return "", []
    nome = restantes[0].rsplit(BARRA_DE_CAMINHO, 1)[-1].lower()
    return nome, restantes[1:]


def despeja_sem_nomear(nome: str, argumentos: list) -> bool:
    so_opcoes = all(a.startswith(MARCA_DE_OPCAO) for a in argumentos)
    if nome in DESPEJAM_TUDO_SEM_ARGUMENTO:
        return so_opcoes
    if nome == LISTA_TUDO_SEM_ARGUMENTO:
        return not argumentos
    if nome == EXPORTA:
        return not argumentos or argumentos == [OPCAO_QUE_LISTA_O_EXPORTADO]
    if nome in DECLARAM:
        return so_opcoes and (not argumentos or any(
            a in OPCOES_DE_DECLARE_QUE_DESPEJAM for a in argumentos))
    return False


def despejo_de_shell(linhas_do_shell: str, comando: str) -> str:
    for segmento in SEPARADORES_DE_COMANDO.split(linhas_do_shell):
        tokens = tokens_de(segmento)
        nome, argumentos = comando_e_argumentos(tokens)
        if nome and despeja_sem_nomear(nome, argumentos):
            return segmento.strip()
    achado = SUBSTITUICAO_QUE_DESPEJA.search(linhas_do_shell)
    if achado:
        return achado.group(0)
    achado = ENVIRON_DO_PROCESSO.search(comando)
    return achado.group(0) if achado else PASSA


def primeiro_comando(comando: str) -> str:
    primeiro = SEPARADORES_DE_COMANDO.split(comando, 1)[0]
    nome, _ = comando_e_argumentos(tokens_de(primeiro))
    return nome


def despejo_de_python(comando: str) -> str:
    if primeiro_comando(comando) in FERRAMENTAS_DE_BUSCA:
        return PASSA
    achado = ITERACAO_DO_AMBIENTE.search(comando)
    if achado:
        return achado.group(0).strip()
    achado = METODO_QUE_DESPEJA_VALORES.search(comando)
    if achado:
        return achado.group(0)
    for achado in CHAMADA_COM_O_AMBIENTE_INTEIRO.finditer(comando):
        chamada = achado.group(1).rsplit(".", 1)[-1]
        if chamada not in CHAMADAS_QUE_SO_LISTAM_NOMES:
            return achado.group(0)
    return PASSA


def despejo_de_powershell(comando: str) -> str:
    achado = (LISTAGEM_DO_AMBIENTE_NO_POWERSHELL.search(comando)
              or TODAS_AS_VARIAVEIS_NO_POWERSHELL.search(comando))
    return achado.group(0).strip() if achado else PASSA


def leitor_do_documento(achado) -> str:
    abertura = SEPARADORES_DE_COMANDO.split(achado.group("abertura"))[-1]
    nome, _ = comando_e_argumentos(tokens_de(abertura))
    return nome


def o_documento_e_executado(achado) -> bool:
    if leitor_do_documento(achado) in INTERPRETADORES_QUE_EXECUTAM_O_DOCUMENTO:
        return True
    expande = not achado.group("aspa")
    return expande and any(marca in achado.group("corpo")
                           for marca in SUBSTITUICAO_QUE_EXECUTA)


def sem_os_documentos_que_sao_dado(comando: str) -> str:
    def corpo_ou_nada(achado):
        if o_documento_e_executado(achado):
            return achado.group(0)
        return achado.group("abertura") + "\n"
    return DOCUMENTO_LITERAL.sub(corpo_ou_nada, comando)


def quadro_novo(onde: str) -> dict:
    return {"onde": onde, "lido": [], "grupos": 0}


def comandos_que_o_documento_executa(corpo: str) -> list:
    pilha, comandos, i = [quadro_novo(NO_CORPO)], [], 0
    while i < len(corpo):
        quadro, c, passo = pilha[-1], corpo[i], 1
        onde, lido = quadro["onde"], quadro["lido"]
        if onde == NA_ASPA_SIMPLES:
            if c == ASPA_SIMPLES:
                pilha.pop()
        elif c == CONTRABARRA:
            escapado = corpo[i + 1:i + 2]
            if onde in GUARDAM_COMANDO and escapado.isalnum():
                lido.append(escapado)
            passo = 2
        elif onde == NA_ASPA_ANSI:
            if c == ASPA_SIMPLES:
                pilha.pop()
        elif corpo.startswith(ABRE_SUBSTITUICAO, i) or (
                c == CRASE and onde != NA_CRASE):
            if onde in GUARDAM_COMANDO:
                lido.append(PALAVRA_QUE_O_SHELL_TROCA)
            pilha.append(quadro_novo(NA_CRASE if c == CRASE
                                     else NA_SUBSTITUICAO))
            passo = len(CRASE) if c == CRASE else len(ABRE_SUBSTITUICAO)
        elif (onde, c) == (NA_CRASE, CRASE) or (
                (onde, c) == (NA_SUBSTITUICAO, FECHA_GRUPO)
                and not quadro["grupos"]):
            comandos.append("".join(lido))
            pilha.pop()
        elif onde == NA_ASPA_DUPLA:
            if c == ASPA_DUPLA:
                pilha.pop()
        elif onde in GUARDAM_COMANDO:
            aspa = (NA_ASPA_ANSI if corpo.startswith(ABRE_ASPA_ANSI, i)
                    else ABRE_ASPA_NO_COMANDO.get(c))
            if aspa:
                lido.append(PALAVRA_QUE_O_SHELL_TROCA)
                pilha.append(quadro_novo(aspa))
                passo = len(ABRE_ASPA_ANSI) if aspa == NA_ASPA_ANSI else 1
            else:
                quadro["grupos"] += PROFUNDIDADE_DO_PARENTESE.get(c, 0)
                lido.append(c)
        i += passo
    return comandos + ["".join(quadro["lido"]) for quadro in pilha
                       if quadro["onde"] in GUARDAM_COMANDO]


def so_o_que_o_shell_executa(comando: str) -> str:
    def corpo_so_se_um_shell_le(achado):
        if leitor_do_documento(achado) in INTERPRETADORES_DE_SHELL:
            return achado.group(0)
        expandido = ([] if achado.group("aspa")
                     else comandos_que_o_documento_executa(
                         achado.group("corpo")))
        return "\n".join([achado.group("abertura"), *expandido]) + "\n"
    return DOCUMENTO_LITERAL.sub(corpo_so_se_um_shell_le, comando)


def despejo_no_comando(comando) -> str:
    if not isinstance(comando, str) or not comando.strip():
        return PASSA
    linhas_do_shell = so_o_que_o_shell_executa(comando)
    comando = sem_os_documentos_que_sao_dado(comando)
    return (despejo_de_shell(linhas_do_shell, comando)
            or despejo_de_python(comando) or despejo_de_powershell(comando))


def e_etapa_sem_ninguem(ambiente) -> bool:
    return bool((ambiente or {}).get(MARCA_DE_ETAPA_NO_AMBIENTE))


def modo_que_nao_mostra_a_pergunta(entrada: dict) -> bool:
    return (entrada or {}).get(
        CAMPO_DO_MODO_DE_PERMISSAO) == MODO_QUE_NAO_MOSTRA_A_PERGUNTA_DO_GANCHO


def verbo_do_veto(entrada: dict, ambiente) -> str:
    if (e_etapa_sem_ninguem(ambiente)
            or modo_que_nao_mostra_a_pergunta(entrada)):
        return DECISAO_DE_NEGAR
    return DECISAO_DE_PERGUNTAR


def vetar(entrada: dict, razao: str, ambiente) -> int:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": EVENTO_ANTES_DA_FERRAMENTA,
        "permissionDecision": verbo_do_veto(entrada, ambiente),
        "permissionDecisionReason": razao,
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
        comando = (entrada.get(CAMPO_DA_ENTRADA) or {}).get(CAMPO_DO_COMANDO, "")
    except (json.JSONDecodeError, AttributeError, TypeError,
            ValueError) as falha:
        return recusa_por_nao_entender(falha)
    achado = despejo_no_comando(comando)
    if not achado:
        return SILENCIO
    return vetar(entrada, RECUSA.format(achado)
                 + MANDA_GRAVAR.format(APRENDIZADO), os.environ)


RAZAO_DO_TESTE = "a razão que o veto explicaria"
MODO_DA_SESSAO_INTERATIVA = "default"
SESSAO_INTERATIVA = {CAMPO_DO_MODO_DE_PERMISSAO: MODO_DA_SESSAO_INTERATIVA}
SESSAO_QUE_NAO_MOSTRA_A_PERGUNTA = {
    CAMPO_DO_MODO_DE_PERMISSAO: MODO_QUE_NAO_MOSTRA_A_PERGUNTA_DO_GANCHO}
PEDIDO_SEM_MODO_DECLARADO = {}
AMBIENTE_SEM_A_MARCA = {}
AMBIENTE_DA_ETAPA_SEM_NINGUEM = {MARCA_DE_ETAPA_NO_AMBIENTE: "1"}
ANINHAMENTO_ALEM_DA_PILHA = sys.getrecursionlimit() + 1
SUBSTITUICOES_ANINHADAS_DEMAIS = (
    "cat <<EOF\n" + "$(echo " * ANINHAMENTO_ALEM_DA_PILHA + "ok"
    + ")" * ANINHAMENTO_ALEM_DA_PILHA + "\nEOF")

FALHA_BARRA = "BARRA [{}]: deixou passar {!r}"
FALHA_DEIXA_PASSAR = "DEIXA_PASSAR [{}]: barrou {!r} por {!r}"
FALHA_COMPORTAMENTO = "COMPORTAMENTO [{}]"
LINHA_DE_FALHA = "FALHOU: {}"
RESUMO_FALHOU = "FALHOU: {} de {} casos"
RESUMO_OK = "OK: {} casos — {} barrados, {} liberados, {} de comportamento"


def saida_em_json(funcao, *argumentos) -> dict:
    import contextlib
    import io
    saida = io.StringIO()
    with contextlib.redirect_stdout(saida):
        funcao(*argumentos)
    try:
        return json.loads(saida.getvalue())["hookSpecificOutput"]
    except (ValueError, KeyError):
        return {}


def veredito_sem_estourar(comando: str) -> str:
    try:
        return despejo_no_comando(comando)
    except RecursionError as falha:
        return type(falha).__name__


def testar() -> int:
    falhas = []
    for rotulo, comando in BARRA_O_COMANDO:
        if not despejo_no_comando(comando):
            falhas.append(FALHA_BARRA.format(rotulo, comando))
    for rotulo, comando in DEIXA_PASSAR:
        achado = despejo_no_comando(comando)
        if achado:
            falhas.append(FALHA_DEIXA_PASSAR.format(rotulo, comando, achado))

    comportamento = []

    def caso(rotulo, condicao):
        comportamento.append((rotulo, bool(condicao)))

    recusa = saida_em_json(recusa_por_nao_entender,
                           TypeError("forma que o gancho não conhece"))
    caso("gancho que veta e não entende o pedido RECUSA, e nomeia a falha — "
         "quem não consegue julgar não pode dizer sim",
         recusa.get("permissionDecision") == DECISAO_DE_NEGAR
         and "TypeError" in recusa.get("permissionDecisionReason", ""))
    caso("em modo `default` sem a marca da etapa o dono vê a pergunta: "
         "`ask`, e ele decide",
         saida_em_json(vetar, SESSAO_INTERATIVA, RAZAO_DO_TESTE,
                       AMBIENTE_SEM_A_MARCA)
         .get("permissionDecision") == DECISAO_DE_PERGUNTAR)
    caso("em `bypassPermissions` sem a marca pode haver gente, mas o cliente "
         "não garante mostrar a pergunta do gancho nesse modo: `deny`, o "
         "único jeito de a regra valer",
         saida_em_json(vetar, SESSAO_QUE_NAO_MOSTRA_A_PERGUNTA,
                       RAZAO_DO_TESTE, AMBIENTE_SEM_A_MARCA)
         .get("permissionDecision") == DECISAO_DE_NEGAR)
    caso("na etapa do executor, com a marca no ambiente, ninguém responde "
         "nem em modo `default`: `deny`",
         saida_em_json(vetar, SESSAO_INTERATIVA, RAZAO_DO_TESTE,
                       AMBIENTE_DA_ETAPA_SEM_NINGUEM)
         .get("permissionDecision") == DECISAO_DE_NEGAR)
    caso("pedido sem o modo declarado e sem a marca recebe `ask` — nega só "
         "a etapa sem ninguém ou o modo que não mostra a pergunta",
         saida_em_json(vetar, PEDIDO_SEM_MODO_DECLARADO, RAZAO_DO_TESTE,
                       AMBIENTE_SEM_A_MARCA)
         .get("permissionDecision") == DECISAO_DE_PERGUNTAR)
    caso("a razão viaja na resposta, com `ask` e com `deny`",
         saida_em_json(vetar, SESSAO_INTERATIVA, RAZAO_DO_TESTE,
                       AMBIENTE_SEM_A_MARCA)
         .get("permissionDecisionReason") == RAZAO_DO_TESTE
         and saida_em_json(vetar, SESSAO_QUE_NAO_MOSTRA_A_PERGUNTA,
                           RAZAO_DO_TESTE, AMBIENTE_SEM_A_MARCA)
         .get("permissionDecisionReason") == RAZAO_DO_TESTE)
    razao_inteira = RECUSA.format("env") + MANDA_GRAVAR.format(APRENDIZADO)
    caso("a recusa nomeia a regra 8, ensina a leitura NOMEADA, cita o "
         "despejo que barrou e manda gravar o aprendizado (regra 4)",
         "Regra 8" in razao_inteira and "NOMEADA" in razao_inteira
         and "`env`" in razao_inteira and "regra 4" in razao_inteira
         and "`conhecimento/`" in razao_inteira)
    caso("o que a recusa cita é o trecho que despejou, não o comando inteiro",
         despejo_no_comando("cd /tmp && env | grep x") == "env"
         and despejo_no_comando(
             "python -c \"import os; print(dict(os.environ))\"")
         == "dict(os.environ)")
    caso("comando que não é texto não estoura a cerca",
         despejo_no_comando(None) == PASSA
         and despejo_no_comando(["env"]) == PASSA)
    caso("substituições aninhadas além do limite de recursão do Python não "
         "estouram a cerca: a varredura não usa a pilha dele",
         veredito_sem_estourar(SUBSTITUICOES_ANINHADAS_DEMAIS) == PASSA)

    falhas += [FALHA_COMPORTAMENTO.format(rotulo)
               for rotulo, passou in comportamento if not passou]
    total = len(BARRA_O_COMANDO) + len(DEIXA_PASSAR) + len(comportamento)
    if falhas:
        for falha in falhas:
            print(LINHA_DE_FALHA.format(falha))
        print(RESUMO_FALHOU.format(len(falhas), total))
        return 1
    print(RESUMO_OK.format(total, len(BARRA_O_COMANDO), len(DEIXA_PASSAR),
                           len(comportamento)))
    return 0


def main() -> int:
    try:
        return decidir()
    except Exception as falha:
        return recusa_por_nao_entender(falha)


if __name__ == "__main__":
    sys.exit(testar() if BANDEIRA_DE_TESTE in sys.argv else main())
