import os
import shlex
import subprocess
import sys

BANDEIRA_DE_TESTE = "--testar"
USO = ("roda o `gh` na conta declarada, e devolve o berro legível quando ele "
       "recusa. Importado por quem fala com issue, etiqueta ou quadro — o "
       "token sai do `gh auth token --user`, e nunca de variável no disco")

GH_PADRAO = "gh"
VARIAVEL_DO_GH = "ATLAS_GH"
SISTEMA_WINDOWS = "nt"
ASPAS = "\"'"
TEMPO_DO_GH = 60
LIMITE_DO_ERRO = 300
NAO_RODOU = "o gh não rodou"


def _sem_as_aspas_que_envolvem(token: str) -> str:
    if len(token) >= 2 and token[0] in ASPAS and token[-1] == token[0]:
        return token[1:-1]
    return token


def partir_comando(valor: str, windows: bool = os.name == SISTEMA_WINDOWS) -> list:
    if not windows:
        return shlex.split(valor)
    return [_sem_as_aspas_que_envolvem(t) for t in shlex.split(valor, posix=False)]


def linha_de_comando(*partes) -> str:
    return " ".join(f'"{parte}"' for parte in partes)


def _comando() -> list:
    return partir_comando(os.environ.get(VARIAVEL_DO_GH, GH_PADRAO))


def rodar(argumentos: list, ambiente: dict = None, entrada=None):
    try:
        return subprocess.run(
            _comando() + argumentos, input=entrada, capture_output=True,
            text=True, timeout=TEMPO_DO_GH,
            env=dict(os.environ, **(ambiente or {})))
    except (OSError, subprocess.SubprocessError):
        return None


def token_da_conta(conta: str) -> str:
    if not conta:
        return ""
    achou = rodar(["auth", "token", "--user", conta])
    return achou.stdout.strip() if achou and achou.returncode == 0 else ""


def na_conta(conta: str, argumentos: list, entrada=None):
    token = token_da_conta(conta)
    return rodar(argumentos, {"GH_TOKEN": token} if token else {}, entrada)


def berro(feito) -> str:
    if feito is None:
        return NAO_RODOU
    return ((feito.stderr or feito.stdout).strip()
            or str(feito.returncode))[:LIMITE_DO_ERRO]


FALSO = """import os
import pathlib
import sys

CAIXA = pathlib.Path(os.environ["GH_TESTE_CAIXA"])
argv = sys.argv[1:]
(CAIXA / "chamadas.txt").open("a").write(
    " ".join(argv) + chr(9) + os.environ.get("GH_TOKEN", "sem-token") + chr(10))
if argv[:2] == ["auth", "token"]:
    print("token-de-" + argv[-1])
elif (CAIXA / "recusa.txt").exists():
    sys.stderr.write("nao vai\\n")
    sys.exit(2)
sys.exit(0)
"""


def testar() -> int:
    import tempfile
    from pathlib import Path

    passou = falhou = 0

    def caso(nome: str, condicao: bool) -> None:
        nonlocal passou, falhou
        if condicao:
            passou += 1
        else:
            falhou += 1
            print(f"FALHOU: {nome}")

    with tempfile.TemporaryDirectory() as pasta:
        caixa = Path(pasta)
        falso = caixa / "gh-falso.py"
        falso.write_text(FALSO, encoding="utf-8")
        os.environ["GH_TESTE_CAIXA"] = str(caixa)
        os.environ[VARIAVEL_DO_GH] = linha_de_comando(sys.executable, falso)

        caso("caminho do Windows com espaço e contrabarra fica inteiro: o "
             "shlex posix quebrava C:\\Program Files em dois e comia as barras, "
             "e o gh falso nunca rodava",
             partir_comando(
                 '"C:\\Program Files\\Python314\\python.exe" "C:\\x\\gh falso.py"',
                 windows=True)
             == ["C:\\Program Files\\Python314\\python.exe", "C:\\x\\gh falso.py"])
        caso("no Linux o mesmo comando entre aspas também fica inteiro",
             partir_comando('"/tmp/com espaco/python3" "/tmp/x/gh.py"',
                            windows=False)
             == ["/tmp/com espaco/python3", "/tmp/x/gh.py"])
        caso("a linha de comando que os testes montam vai com aspas em cada "
             "parte — é o que sobrevive aos dois sistemas",
             linha_de_comando("a b", "c") == '"a b" "c"')

        caso("sem conta declarada não há token — e o gh usa a conta ativa",
             token_da_conta("") == "")
        caso("com conta declarada, o token sai do `gh auth token --user`",
             token_da_conta("alguem") == "token-de-alguem")

        na_conta("alguem", ["issue", "view", "1"])
        chamadas = (caixa / "chamadas.txt").read_text(encoding="utf-8")
        caso("o comando roda com o token da conta pedida, sem trocar a ativa",
             "token-de-alguem" in chamadas)

        (caixa / "recusa.txt").write_text("x", encoding="utf-8")
        feito = na_conta("alguem", ["issue", "comment", "1"])
        caso("recusa do gh vira berro legível, nunca silêncio",
             feito is not None and "nao vai" in berro(feito))
        caso("berro de comando que nem rodou também tem texto",
             berro(None) == NAO_RODOU)

        os.environ[VARIAVEL_DO_GH] = "/caminho/que/nao/existe/gh"
        caso("gh que não existe devolve None, e não estoura na cara de quem "
             "chamou",
             rodar(["auth", "status"]) is None)
        os.environ.pop(VARIAVEL_DO_GH, None)
        os.environ.pop("GH_TESTE_CAIXA", None)

    print(f"{'OK' if not falhou else 'FALHOU'}: {passou + falhou} casos")
    return 1 if falhou else 0


if __name__ == "__main__":
    if BANDEIRA_DE_TESTE in sys.argv[1:]:
        sys.exit(testar())
    print(USO)
