import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "gh"))
import gh

BANDEIRA_DE_TESTE = "--testar"
USO = ("posta o relato de entrega da sessão como comentário na issue: o que "
       "foi pedido, o que foi executado, o que foi entregue e o que é do "
       "dono agora — cada item com link. Item para o dono etiqueta a issue e "
       "move o cartão para a coluna de espera")


ARQUIVO_DO_EXECUTOR = "nucleo/executor.json"
CAMPO_DO_REPOSITORIO = ("issues", "repositorio")
CAMPO_DA_CONTA = ("issues", "conta_gh")
SITUACAO_DE_ESPERA = "parada"
ETIQUETA_PARADO_EM_VOCE = "parado-em-voce"
MODULO_DO_EXECUTOR = ".agents/encadeador"
NOME_DO_EXECUTOR = "encadeador"

SEPARADOR_DO_ITEM = "|"
ENDERECO = re.compile(r"https?://\S+")

TITULO = "## Entrega da sessão"
BLOCO_DO_PEDIDO = "**O que você pediu**"
BLOCO_DO_EXECUTADO = "**O que foi executado**"
BLOCO_DO_ENTREGUE = "**O que foi entregue**"
BLOCO_DO_SEU = "**O que é seu agora**"
NADA_PARA_VOCE = "_Nada espera por você._"
LINHA_DO_ITEM = "- {texto} — {link}"
LINHA_SIMPLES = "- {texto}"

RECUSA_SEM_ISSUE = "sem issue: o relato de entrega é comentário, e comentário tem dono"
RECUSA_SEM_PEDIDO = ("sem `--pedido`: o relato abre pelo que VOCÊ pediu, "
                     "colado, senão ninguém verifica se foi isso mesmo")
RECUSA_SEM_EXECUTADO = "sem `--executado`: entrega sem trabalho executado não é entrega"
RECUSA_SEM_LINK = ("`{bandeira}` sem link: `{item}`. Todo item entregue e "
                   "todo item que fica para o dono carrega o endereço que o "
                   "abre — número solto obriga a garimpar")
RECUSA_SEM_ENDERECO = ("sem repositório declarado: preencha "
                       "`issues.repositorio` em {arquivo}")
FALHA_AO_POSTAR = "não consegui comentar na issue {issue}: {motivo}"
RECADO_POSTADO = "entrega relatada na issue {issue}"
RECADO_DO_ENSAIO = "ENSAIO — o relato que iria para a issue {issue}:\n\n{corpo}"
RECADO_ETIQUETA = "etiqueta `{etiqueta}` posta"
RECADO_ETIQUETA_FALHOU = "não consegui pôr a etiqueta `{etiqueta}`: {motivo}"
RECADO_QUADRO_SEM_MODULO = ("cartão não movido: o módulo do executor de "
                            "roteiros não está instalado, e é dele a fala "
                            "com o quadro")


def configuracao_do_executor(cwd: str = "") -> dict:
    alvo = Path(cwd or ".") / ARQUIVO_DO_EXECUTOR
    try:
        return json.loads(alvo.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _campo(dado: dict, caminho: tuple):
    for passo in caminho:
        if not isinstance(dado, dict):
            return ""
        dado = dado.get(passo)
    return dado if isinstance(dado, str) else ""


def partido_no_separador(item: str) -> tuple:
    texto, _, link = item.partition(SEPARADOR_DO_ITEM)
    return texto.strip(), link.strip()


def item_sem_link(item: str) -> bool:
    _, link = partido_no_separador(item)
    return not ENDERECO.search(link or item)


def primeiro_sem_link(itens: list) -> str:
    for item in itens or []:
        if item_sem_link(item):
            return item
    return ""


def _linhas_com_link(itens: list) -> list:
    linhas = []
    for item in itens:
        texto, link = partido_no_separador(item)
        linhas.append(LINHA_DO_ITEM.format(texto=texto, link=link)
                      if link else LINHA_SIMPLES.format(texto=item.strip()))
    return linhas


def corpo_do_relato(pedido: str, executado: list, entregue: list,
                    seu: list) -> str:
    partes = [TITULO, "", BLOCO_DO_PEDIDO, "", f"> {pedido.strip()}", "",
              BLOCO_DO_EXECUTADO, ""]
    partes += [LINHA_SIMPLES.format(texto=um.strip()) for um in executado]
    partes += ["", BLOCO_DO_ENTREGUE, ""]
    partes += _linhas_com_link(entregue) or [LINHA_SIMPLES.format(
        texto="nada — a sessão não produziu artefato")]
    partes += ["", BLOCO_DO_SEU, ""]
    partes += _linhas_com_link(seu) or [NADA_PARA_VOCE]
    return "\n".join(partes) + "\n"


def recusa_do_pedido(issue, pedido: str, executado: list, entregue: list,
                     seu: list) -> str:
    if not issue:
        return RECUSA_SEM_ISSUE
    if not (pedido or "").strip():
        return RECUSA_SEM_PEDIDO
    if not [um for um in (executado or []) if um.strip()]:
        return RECUSA_SEM_EXECUTADO
    for bandeira, itens in (("--entregue", entregue), ("--seu", seu)):
        if (achado := primeiro_sem_link(itens)):
            return RECUSA_SEM_LINK.format(bandeira=bandeira, item=achado)
    return ""


def etiquetar(conta: str, repositorio: str, issue) -> tuple:
    feito = gh.na_conta(conta, ["issue", "edit", str(issue), "--repo",
                                 repositorio, "--add-label",
                                 ETIQUETA_PARADO_EM_VOCE])
    if feito is None or feito.returncode != 0:
        return False, RECADO_ETIQUETA_FALHOU.format(
            etiqueta=ETIQUETA_PARADO_EM_VOCE, motivo=gh.berro(feito))
    return True, RECADO_ETIQUETA.format(etiqueta=ETIQUETA_PARADO_EM_VOCE)


def _executor_instalado(cwd: str):
    pasta = Path(cwd or ".") / MODULO_DO_EXECUTOR
    if not (pasta / f"{NOME_DO_EXECUTOR}.py").is_file():
        return None
    sys.path.insert(0, str(pasta))
    try:
        return __import__(NOME_DO_EXECUTOR)
    except ImportError:
        return None


def mover_o_cartao(configuracao: dict, issue, cwd: str = "") -> tuple:
    executor = _executor_instalado(cwd)
    if executor is None:
        return False, RECADO_QUADRO_SEM_MODULO
    return executor.mover_no_quadro(configuracao, issue, SITUACAO_DE_ESPERA)


def postar(issue, pedido: str, executado: list, entregue: list, seu: list,
           cwd: str = "", ensaio: bool = False) -> tuple:
    if (recusa := recusa_do_pedido(issue, pedido, executado, entregue, seu)):
        return 2, recusa
    corpo = corpo_do_relato(pedido, executado, entregue or [], seu or [])
    if ensaio:
        return 0, RECADO_DO_ENSAIO.format(issue=issue, corpo=corpo)
    configuracao = configuracao_do_executor(cwd)
    repositorio = _campo(configuracao, CAMPO_DO_REPOSITORIO)
    if not repositorio:
        return 2, RECUSA_SEM_ENDERECO.format(arquivo=ARQUIVO_DO_EXECUTOR)
    conta = _campo(configuracao, CAMPO_DA_CONTA)
    feito = gh.na_conta(conta, ["issue", "comment", str(issue), "--repo",
                                 repositorio, "--body-file", "-"],
                         entrada=corpo)
    if feito is None or feito.returncode != 0:
        return 2, FALHA_AO_POSTAR.format(issue=issue, motivo=gh.berro(feito))
    recados = [RECADO_POSTADO.format(issue=issue)]
    if seu:
        recados.append(etiquetar(conta, repositorio, issue)[1])
        recados.append(mover_o_cartao(configuracao, issue, cwd)[1])
    return 0, " · ".join(r for r in recados if r)


FALSO_GH = """import os
import pathlib
import sys

CAIXA = pathlib.Path(os.environ["ENTREGA_TESTE_CAIXA"])
argv = sys.argv[1:]
(CAIXA / "chamadas.txt").open("a").write(
    " ".join(argv) + chr(9) + os.environ.get("GH_TOKEN", "sem-token") + chr(10))
if argv[:2] == ["auth", "token"]:
    print("token-de-" + argv[-1])
elif argv[:2] == ["issue", "comment"]:
    if (CAIXA / "recusa.txt").exists():
        sys.stderr.write("nao vai\\n")
        sys.exit(2)
    (CAIXA / "postado.md").open("a").write(sys.stdin.read())
sys.exit(0)
"""


def _bancada(pasta: Path):
    caixa = Path(tempfile.mkdtemp(dir=str(pasta), prefix="caixa-"))
    falso = caixa / "gh-falso.py"
    falso.write_text(FALSO_GH, encoding="utf-8")
    os.environ["ENTREGA_TESTE_CAIXA"] = str(caixa)
    os.environ[gh.VARIAVEL_DO_GH] = gh.linha_de_comando(sys.executable, falso)
    return caixa


def _com_configuracao(pasta: Path, dado: dict) -> str:
    raiz = Path(tempfile.mkdtemp(dir=str(pasta), prefix="raiz-"))
    alvo = raiz / ARQUIVO_DO_EXECUTOR
    alvo.parent.mkdir(parents=True, exist_ok=True)
    alvo.write_text(json.dumps(dado, ensure_ascii=False), encoding="utf-8")
    return str(raiz)


def testar() -> int:
    passou = falhou = 0

    def caso(nome: str, condicao: bool) -> None:
        nonlocal passou, falhou
        if condicao:
            passou += 1
        else:
            falhou += 1
            print(f"FALHOU: {nome}")

    with tempfile.TemporaryDirectory() as pasta:
        raiz = Path(pasta)
        caso("entrega sem issue não existe — comentário tem dono",
             recusa_do_pedido("", "p", ["e"], [], []) == RECUSA_SEM_ISSUE)
        caso("entrega sem o pedido colado é relatório, não prestação de contas",
             recusa_do_pedido(1, "  ", ["e"], [], []) == RECUSA_SEM_PEDIDO)
        caso("entrega sem trabalho executado não é entrega",
             recusa_do_pedido(1, "p", [" "], [], []) == RECUSA_SEM_EXECUTADO)
        caso("entregue sem link é recusado: número solto obriga a garimpar",
             "--entregue" in recusa_do_pedido(1, "p", ["e"], ["a issue 13"],
                                              []))
        caso("o que fica para o dono também carrega o link",
             "--seu" in recusa_do_pedido(1, "p", ["e"], [], ["mescla o PR"]))
        caso("com link nos dois blocos, nada é recusado",
             recusa_do_pedido(1, "p", ["e"], ["o PR|http://x/1"],
                              ["mescla|http://x/1"]) == "")
        caso("link solto no meio do texto também vale — o separador é ajuda, "
             "não cerca",
             recusa_do_pedido(1, "p", ["e"], ["saiu em http://x/1"], []) == "")

        corpo = corpo_do_relato("quero X", ["fiz Y"],
                                ["o PR|https://x/pull/1"],
                                ["mescla o PR|https://x/pull/1"])
        caso("o relato abre pelo pedido do dono, colado",
             "> quero X" in corpo)
        caso("os quatro blocos existem, sempre na mesma ordem",
             corpo.index(BLOCO_DO_PEDIDO) < corpo.index(BLOCO_DO_EXECUTADO)
             < corpo.index(BLOCO_DO_ENTREGUE) < corpo.index(BLOCO_DO_SEU))
        caso("item com separador vira texto e link",
             "- o PR — https://x/pull/1" in corpo)
        vazio = corpo_do_relato("q", ["y"], [], [])
        caso("sem nada para o dono, o bloco diz isso em vez de sumir — bloco "
             "ausente se lê como esquecimento",
             NADA_PARA_VOCE in vazio)

        _bancada(raiz)
        cwd = _com_configuracao(raiz, {"issues": {
            "repositorio": "dono/repo", "conta_gh": "conta-x"}})
        codigo, recado = postar(7, "quero X", ["fiz Y"], [], [], cwd=cwd,
                                ensaio=True)
        caso("no ensaio o relato aparece e nada é postado",
             codigo == 0 and "quero X" in recado
             and not (Path(os.environ["ENTREGA_TESTE_CAIXA"])
                      / "postado.md").exists())

        caixa = _bancada(raiz)
        codigo, recado = postar(7, "quero X", ["fiz Y"],
                                ["o PR|https://x/pull/1"], [], cwd=cwd)
        postado = (caixa / "postado.md").read_text(encoding="utf-8")
        chamadas = (caixa / "chamadas.txt").read_text(encoding="utf-8")
        caso("sem item para o dono, o relato é postado e mais nada acontece",
             codigo == 0 and "quero X" in postado
             and "--add-label" not in chamadas)
        caso("o relato é postado pela conta declarada nas issues",
             "token-de-conta-x" in chamadas)

        caixa = _bancada(raiz)
        codigo, recado = postar(7, "quero X", ["fiz Y"], [],
                                ["mescla o PR|https://x/pull/1"], cwd=cwd)
        chamadas = (caixa / "chamadas.txt").read_text(encoding="utf-8")
        caso("com item para o dono, a issue ganha a etiqueta de espera",
             codigo == 0 and ETIQUETA_PARADO_EM_VOCE in chamadas)
        caso("sem o módulo do executor, o cartão não move e a sessão diz por "
             "quê — em vez de calar e parecer que moveu",
             RECADO_QUADRO_SEM_MODULO in recado)

        caixa = _bancada(raiz)
        (caixa / "recusa.txt").write_text("x", encoding="utf-8")
        codigo, recado = postar(7, "quero X", ["fiz Y"], [], [], cwd=cwd)
        caso("gh que recusa vira recusa, não silêncio",
             codigo == 2 and "não consegui comentar" in recado)

        sem_endereco = _com_configuracao(raiz, {})
        codigo, recado = postar(7, "quero X", ["fiz Y"], [], [],
                                cwd=sem_endereco)
        caso("sem repositório declarado, a entrega recusa e ensina o campo",
             codigo == 2 and "issues.repositorio" in recado)

    print(f"{'OK' if not falhou else 'FALHOU'}: {passou + falhou} casos")
    return 1 if falhou else 0


def montar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=USO)
    parser.add_argument("--issue", help="o número da issue que recebe o relato")
    parser.add_argument("--pedido", default="",
                        help="o pedido do dono, colado como ele escreveu")
    parser.add_argument("--executado", action="append", default=[],
                        help="uma linha por passo executado; repita a bandeira")
    parser.add_argument("--entregue", action="append", default=[],
                        help="`o que|link` por artefato entregue")
    parser.add_argument("--seu", action="append", default=[],
                        help="`o que|link` por item que espera pelo dono")
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--ensaio", action="store_true",
                        help="mostra o relato sem postar")
    parser.add_argument(BANDEIRA_DE_TESTE, action="store_true")
    return parser


def main() -> int:
    if BANDEIRA_DE_TESTE in sys.argv[1:]:
        return testar()
    a = montar_parser().parse_args()
    codigo, recado = postar(a.issue, a.pedido, a.executado, a.entregue,
                            a.seu, a.cwd, a.ensaio)
    print(recado)
    return codigo


if __name__ == "__main__":
    sys.exit(main())
