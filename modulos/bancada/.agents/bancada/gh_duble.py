import json
import os
import subprocess
import sys
import time
from pathlib import Path

GH_REAL = os.environ.get("BANCADA_GH_REAL", "C:/Program Files/GitHub CLI/gh.exe")
REGISTRO = os.environ.get("BANCADA_GH_REGISTRO", "")
CRIADAS = os.environ.get("BANCADA_GH_CRIADAS", "")
REPOSITORIO = os.environ.get("BANCADA_GH_REPOSITORIO", "") or "duble/duble"
TOKEN_DE_MENTIRA = "gho_duble_da_bancada"
PRIMEIRO_NUMERO = 9001

LEITURAS = {
    "issue": {"view", "list", "status"},
    "pr": {"view", "list", "checks", "diff", "status"},
    "repo": {"view", "list", "clone"},
    "search": {"issues", "prs", "repos", "code", "commits"},
    "label": {"list"},
    "release": {"list", "view"},
    "run": {"list", "view"},
    "workflow": {"list", "view"},
    "auth": {"status"},
    "browse": set(),
    "project": {"list", "view", "item-list", "field-list"},
}
ESCRITAS = {
    "issue": {"create", "comment", "edit", "close", "reopen", "delete", "pin",
              "unpin", "transfer", "lock", "unlock", "develop"},
    "pr": {"create", "edit", "merge", "close", "reopen", "comment", "review",
           "ready", "checkout", "lock", "unlock", "update-branch"},
    "release": {"create", "delete", "edit", "upload"},
    "repo": {"create", "delete", "edit", "fork", "rename", "archive", "sync",
             "set-default"},
    "label": {"create", "edit", "delete", "clone"},
    "gist": {"create", "edit", "delete"},
    "project": {"create", "edit", "delete", "item-add", "item-edit", "item-create",
                "item-delete", "close", "copy", "field-create", "field-delete",
                "link", "unlink", "mark-template"},
    "workflow": {"run", "enable", "disable"},
    "run": {"cancel", "rerun", "delete", "watch"},
    "secret": {"set", "delete"},
    "variable": {"set", "delete"},
    "auth": {"login", "logout", "refresh", "setup-git", "switch"},
}
BANDEIRAS_QUE_ESCREVEM_NA_API = {"-X", "--method", "-f", "-F", "--field",
                                 "--raw-field", "--input"}


def registrar(tipo: str, argv: list, codigo: int, corpo: str = "") -> None:
    if not REGISTRO:
        return
    linha = {"quando": time.strftime("%Y-%m-%dT%H:%M:%S"), "cwd": os.getcwd(),
             "argv": argv, "tipo": tipo, "exit": codigo}
    if corpo:
        linha["corpo"] = corpo
    with Path(REGISTRO).open("a", encoding="utf-8") as saida:
        saida.write(json.dumps(linha, ensure_ascii=False) + "\n")


def criadas() -> dict:
    if not CRIADAS or not Path(CRIADAS).exists():
        return {}
    try:
        return json.loads(Path(CRIADAS).read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def guardar_criada(numero: int, titulo: str, corpo: str, rotulos: list) -> None:
    if not CRIADAS:
        return
    todas = criadas()
    todas[str(numero)] = {"number": numero, "title": titulo, "body": corpo,
                          "labels": [{"name": r} for r in rotulos], "state": "OPEN",
                          "url": f"https://github.com/{REPOSITORIO}/issues/{numero}",
                          "comments": []}
    Path(CRIADAS).write_text(json.dumps(todas, ensure_ascii=False, indent=2),
                             encoding="utf-8")


def valor_da_bandeira(argv: list, nomes: tuple) -> str:
    for indice, token in enumerate(argv):
        if token in nomes and indice + 1 < len(argv):
            return argv[indice + 1]
        for nome in nomes:
            if token.startswith(nome + "="):
                return token.split("=", 1)[1]
    return ""


def valores_da_bandeira(argv: list, nomes: tuple) -> list:
    achados = []
    for indice, token in enumerate(argv):
        if token in nomes and indice + 1 < len(argv):
            achados.append(argv[indice + 1])
    return achados


def corpo_da_entrada() -> str:
    if sys.stdin is None or sys.stdin.isatty():
        return ""
    try:
        return sys.stdin.read()
    except OSError:
        return ""


def metodo_da_api(argv: list) -> str:
    for indice, token in enumerate(argv):
        if token in ("-X", "--method") and indice + 1 < len(argv):
            return argv[indice + 1].upper()
        if token.startswith("--method="):
            return token.split("=", 1)[1].upper()
    return "GET"


def classificar(argv: list) -> str:
    if not argv:
        return "desconhecido"
    grupo = argv[0]
    if grupo == "api":
        if len(argv) > 1 and argv[1] == "graphql":
            return "escrita" if "mutation" in " ".join(argv).lower() else "leitura"
        if metodo_da_api(argv) != "GET":
            return "escrita"
        if any(t in BANDEIRAS_QUE_ESCREVEM_NA_API or t.startswith("--input=")
               for t in argv):
            return "escrita"
        return "leitura"
    if grupo in ("--version", "help", "--help", "version"):
        return "leitura"
    verbo = argv[1] if len(argv) > 1 else ""
    if verbo in ESCRITAS.get(grupo, set()):
        return "escrita"
    if verbo in LEITURAS.get(grupo, set()):
        return "leitura"
    return "desconhecido"


def numero_no_argv(argv: list) -> str:
    for token in argv[2:]:
        if token.isdigit():
            return token
    return ""


def issue_criada_pedida(argv: list) -> dict:
    if argv[:2] != ["issue", "view"]:
        return {}
    numero = numero_no_argv(argv)
    return criadas().get(numero, {})


def mostrar_issue_criada(issue: dict, argv: list) -> None:
    campos = valor_da_bandeira(argv, ("--json",))
    if campos:
        pedidos = [c for c in campos.split(",") if c]
        print(json.dumps({c: issue.get(c) for c in pedidos}, ensure_ascii=False))
        return
    print(f"{issue['title']} {REPOSITORIO}#{issue['number']}")
    print(f"Open • duble opened now • 0 comments")
    print()
    print(issue["body"])
    print()
    print(issue["url"])


def resposta_de_mentira(argv: list, corpo: str) -> str:
    grupo, verbo = argv[0], argv[1] if len(argv) > 1 else ""
    if grupo == "issue" and verbo == "create":
        numero = PRIMEIRO_NUMERO + len(criadas())
        titulo = valor_da_bandeira(argv, ("--title", "-t"))
        texto = valor_da_bandeira(argv, ("--body", "-b")) or corpo
        rotulos = valores_da_bandeira(argv, ("--label", "-l"))
        guardar_criada(numero, titulo, texto, rotulos)
        return f"https://github.com/{REPOSITORIO}/issues/{numero}"
    if grupo == "pr" and verbo == "create":
        return f"https://github.com/{REPOSITORIO}/pull/{PRIMEIRO_NUMERO + 500}"
    if grupo in ("issue", "pr") and verbo == "comment":
        return f"https://github.com/{REPOSITORIO}/issues/{numero_no_argv(argv) or PRIMEIRO_NUMERO}#issuecomment-{PRIMEIRO_NUMERO}"
    if grupo == "api":
        return "{}"
    return ""


def passar_ao_gh_de_verdade(argv: list) -> int:
    ambiente = dict(os.environ)
    ambiente.pop("GH_TOKEN", None)
    configuracao_real = ambiente.pop("BANCADA_GH_CONFIG_REAL", "")
    if configuracao_real:
        ambiente["GH_CONFIG_DIR"] = configuracao_real
    else:
        ambiente.pop("GH_CONFIG_DIR", None)
    try:
        feito = subprocess.run([GH_REAL] + argv, env=ambiente, timeout=120)
    except (OSError, subprocess.SubprocessError) as erro:
        sys.stderr.write(f"duble do gh: o gh de verdade nao respondeu: {erro}\n")
        return 1
    return feito.returncode


def main() -> int:
    argv = sys.argv[1:]
    if argv[:2] == ["auth", "token"]:
        print(TOKEN_DE_MENTIRA)
        registrar("token", argv, 0)
        return 0
    criada = issue_criada_pedida(argv)
    if criada:
        mostrar_issue_criada(criada, argv)
        registrar("leitura-da-criada", argv, 0)
        return 0
    tipo = classificar(argv)
    if tipo == "leitura":
        codigo = passar_ao_gh_de_verdade(argv)
        registrar("leitura", argv, codigo)
        return codigo
    corpo = corpo_da_entrada()
    if tipo == "escrita":
        resposta = resposta_de_mentira(argv, corpo)
        if resposta:
            print(resposta)
        registrar("escrita", argv, 0, corpo)
        return 0
    sys.stderr.write("duble do gh: comando fora do previsto na bancada, nada foi "
                     f"executado: gh {' '.join(argv)}\n")
    registrar("desconhecido", argv, 1, corpo)
    return 1


if __name__ == "__main__":
    sys.exit(main())
