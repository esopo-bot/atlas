import json
import re
import shlex
import sys

EVENTO_ANTES_DA_FERRAMENTA = "PreToolUse"
DECISAO_DE_NEGAR = "deny"
BANDEIRA_DE_TESTE = "--testar"
SILENCIO = 0

COMANDO_CD = "cd"
SEPARADORES_DE_COMANDO = re.compile(r"&&|\|\||;|\n|\r")
DOCUMENTO_LITERAL = re.compile(r"<<-?\s*['\"]?\w+['\"]?.*\Z", re.S)
ASPAS = "\"'"
PREFIXOS_QUE_JA_SAO_ABSOLUTOS = ("/", "~", "$", "%", "\\", "@")
MARCA_DE_URL = "://"
MARCA_DE_OPCAO = "-"
IGUAL = "="
BARRA = "/"
ARQUIVO_SOLTO = re.compile(r"^[\w.\-]*[A-Za-z_][\w.\-]*\.[A-Za-z]\w{0,5}$")

RECUSA = (
    "Regra 1 da camada: a sessão já está na raiz, e o harness devolve o cwd "
    "depois de todo `cd`. Prefixar o comando com `cd {pasta};` e seguir com "
    "caminho relativo (`{token}`) faz o auto mode parar e perguntar ao dono, "
    "porque ele não consegue saber que pasta o comando lê. Reescreva sem o "
    "`cd`, com o caminho absoluto no próprio argumento — por exemplo "
    "`{sugestao}`.")
RECUSA_SEM_ENTENDER = ("não entendi a entrada do gancho ({}: {}); na dúvida, "
                       "recuso")

BARRA_O_COMANDO = [
    ("cd na raiz e grep relativo",
     "cd /home/x/repo; grep -n x .agents/a.py"),
    ("cd com && e arquivo solto",
     "cd /home/x/repo && python3 montar.py --sincronizar"),
    ("cd com aspas e caminho relativo depois",
     'cd "/home/x/repo" && sed -n 1,5p nucleo/regras.json'),
    ("cd, comando limpo e depois outro relativo",
     "cd /tmp/x; git status; cat conhecimento/a.md"),
    ("cd com opção que carrega caminho relativo",
     "cd /home/x && ls --directory=tmp/rascunho"),
]
DEIXA_PASSAR = [
    ("sem cd", "grep -n x /home/x/repo/.agents/a.py"),
    ("cd sozinho", "cd /home/x/repo"),
    ("cd e comando sem caminho", "cd /home/x/repo && git status"),
    ("cd e caminho absoluto", "cd /tmp/x && python3 /home/x/repo/montar.py"),
    ("cd e caminho com til", "cd /tmp && ls ~/.local/share"),
    ("cd e variável", "cd /tmp && ls $HOME/x/y"),
    ("cd e url", "cd /tmp && curl -s http://127.0.0.1:19530/v2/x"),
    ("cd e número com ponto", "cd /tmp && sleep 1.5"),
    ("cd e versão de pacote", "cd /tmp && npm view @zilliz/x@0.1.15"),
    ("cd e documento literal com caminhos dentro",
     "cd /tmp && python3 - <<'PY'\nprint(open('a/b.py'))\nPY"),
    ("cd no meio, não na frente", "git status && cd /tmp && ls x/y"),
    ("cd e opção sem caminho", "cd /tmp && git log --oneline -3"),
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


def valor_do_token(token: str) -> str:
    if token.startswith(MARCA_DE_OPCAO):
        return token.split(IGUAL, 1)[1] if IGUAL in token else ""
    return token


def e_caminho_relativo(token: str) -> bool:
    valor = valor_do_token(token)
    if not valor or valor.startswith(PREFIXOS_QUE_JA_SAO_ABSOLUTOS) \
            or MARCA_DE_URL in valor:
        return False
    if BARRA in valor:
        return True
    return bool(ARQUIVO_SOLTO.match(valor))


def pasta_do_cd(comando: str) -> str:
    primeiro = SEPARADORES_DE_COMANDO.split(comando.strip(), 1)[0]
    tokens = tokens_de(primeiro)
    if len(tokens) >= 2 and tokens[0] == COMANDO_CD:
        return tokens[1]
    return ""


def caminho_relativo_apos_cd(comando: str) -> tuple:
    pasta = pasta_do_cd(comando or "")
    if not pasta:
        return "", ""
    resto = DOCUMENTO_LITERAL.sub("", comando.strip())
    for segmento in SEPARADORES_DE_COMANDO.split(resto)[1:]:
        for token in tokens_de(segmento):
            if e_caminho_relativo(token):
                return pasta, token
    return pasta, ""


def sugestao(pasta: str, token: str) -> str:
    return pasta.rstrip(BARRA) + BARRA + valor_do_token(token)


def recusar(pasta: str, token: str) -> int:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": EVENTO_ANTES_DA_FERRAMENTA,
        "permissionDecision": DECISAO_DE_NEGAR,
        "permissionDecisionReason": RECUSA.format(
            pasta=pasta, token=token, sugestao=sugestao(pasta, token)),
    }}, ensure_ascii=False))
    return SILENCIO


def recusa_por_nao_entender(falha) -> int:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": EVENTO_ANTES_DA_FERRAMENTA,
        "permissionDecision": DECISAO_DE_NEGAR,
        "permissionDecisionReason": RECUSA_SEM_ENTENDER.format(
            type(falha).__name__, falha),
    }}, ensure_ascii=False))
    return SILENCIO


def decidir() -> int:
    try:
        entrada = json.load(sys.stdin)
        comando = entrada.get("tool_input", {}).get("command", "")
    except (json.JSONDecodeError, AttributeError, TypeError,
            ValueError) as falha:
        return recusa_por_nao_entender(falha)
    pasta, token = caminho_relativo_apos_cd(comando)
    if not token:
        return SILENCIO
    return recusar(pasta, token)


def testar() -> int:
    falhas = []
    for rotulo, comando in BARRA_O_COMANDO:
        pasta, token = caminho_relativo_apos_cd(comando)
        if not token:
            falhas.append(f"devia barrar [{rotulo}]: {comando!r}")
    for rotulo, comando in DEIXA_PASSAR:
        pasta, token = caminho_relativo_apos_cd(comando)
        if token:
            falhas.append(f"devia passar [{rotulo}]: {comando!r} — barrou "
                          f"por {token!r}")
    pasta, token = caminho_relativo_apos_cd(
        "cd /home/x/repo; grep -n x .agents/a.py")
    if sugestao(pasta, token) != "/home/x/repo/.agents/a.py":
        falhas.append("a sugestão não juntou a pasta do cd com o caminho")
    if sugestao("/home/x", "--directory=tmp/r") != "/home/x/tmp/r":
        falhas.append("a sugestão não tirou a opção de antes do caminho")
    total = len(BARRA_O_COMANDO) + len(DEIXA_PASSAR) + 2
    for falha in falhas:
        print(f"FALHOU: {falha}")
    print(f"{'FALHOU' if falhas else 'OK'}: {total} casos — "
          f"{len(BARRA_O_COMANDO)} barrados, {len(DEIXA_PASSAR)} liberados")
    return 1 if falhas else 0


def main() -> int:
    try:
        return decidir()
    except Exception as falha:
        return recusa_por_nao_entender(falha)


if __name__ == "__main__":
    sys.exit(testar() if BANDEIRA_DE_TESTE in sys.argv else main())
