import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "gh"))
import gh

BANDEIRA_DE_TESTE = "--testar"
USO = ("posta o relato de entrega da sessão como comentário na issue: o que "
       "foi pedido, o que foi executado, o que foi entregue e o que é do "
       "dono agora — cada item com link. Item para o dono etiqueta a issue e "
       "move o cartão para a coluna de espera; issue cujo corpo abre com "
       "`Retomar em: aaaa-mm-dd` no futuro espera o relógio, e fica com "
       "`retomar-em`. Sai 0 quando tudo foi, 2 quando recusou sem postar, e "
       "3 quando o relato FOI postado e a etiqueta ou o cartão falhou: "
       "nesse caso não rode de novo")


ARQUIVO_DO_EXECUTOR = "nucleo/executor.json"
CAMPO_DO_REPOSITORIO = ("issues", "repositorio")
CAMPO_DA_CONTA = ("issues", "conta_gh")
SITUACAO_DE_ESPERA = "parada"
ETIQUETA_PARADO_EM_VOCE = "parado-em-voce"
ETIQUETA_RETOMAR_EM = "retomar-em"
LINHA_DE_RETOMADA = re.compile(r"^Retomar em:\s*(.*?)\s*$")
SAIDA_PELA_METADE = 3
ESPERA_PELO_DONO = "dono"
ESPERA_PELO_RELOGIO = "relogio"
ESPERA_QUE_VENCEU = "venceu"
MARCA_DE_ORDEM_DE_BYTES = "﻿"
ETIQUETAS_DE_CADA_ESPERA = {
    ESPERA_PELO_DONO: (ETIQUETA_PARADO_EM_VOCE, ETIQUETA_RETOMAR_EM),
    ESPERA_PELO_RELOGIO: (ETIQUETA_RETOMAR_EM, ETIQUETA_PARADO_EM_VOCE),
    ESPERA_QUE_VENCEU: (ETIQUETA_PARADO_EM_VOCE, ETIQUETA_RETOMAR_EM),
}
QUADRO_FEITO, QUADRO_DISPENSADO, QUADRO_FALHOU = "feito", "dispensado", "falhou"
RECADO_ESPERA_PELO_RELOGIO = (
    "a issue espera o relógio até {data}: fica com `{etiqueta}` e o cartão "
    "não vai para a coluna do dono")
RECADO_DATA_INVALIDA = (
    "a linha de retomada traz uma data que não se entende ({texto!r}): "
    "tratei como espera pelo dono, confira")
RECADO_CORPO_NAO_LIDO = (
    "não li o corpo da issue ({motivo}), então não sei se ela espera o "
    "relógio: tratei como espera pelo dono, confira a etiqueta")
RECADO_QUADRO_NAO_IMPORTOU = (
    "cartão não movido: o módulo do executor de roteiros está instalado e "
    "não importou ({motivo})")
RECADO_QUADRO_FALHOU = "cartão não movido: {motivo}"
RECADO_PELA_METADE = (
    "ENTREGA PELA METADE — o relato JÁ ESTÁ na issue: NÃO rode este "
    "instrumento de novo, comentário postado duas vezes é ruído que ninguém "
    "apaga. Refaça à mão só o que falhou: {falhas}")
MODULO_DO_EXECUTOR = ".agents/encadeador"
NOME_DO_EXECUTOR = "encadeador"

SEPARADOR_DO_ITEM = "|"
ENDERECO = re.compile(r"https?://\S+")
PASTA_DOS_VIZINHOS = "projetos"
ENDERECO_LOCAL = re.compile(r"local:([A-Za-z0-9_][A-Za-z0-9_.-]*)@([0-9a-f]{7,40})")
TEMPO_DO_GIT_LOCAL_S = 20
LOCAL_NAO_MEDIDO = ("NÃO MEDIDO: `{endereco}` é endereço local, e sem a raiz do "
                    "workspace em `--cwd` não há como conferir o vizinho nem "
                    "o commit")
LOCAL_SEM_VIZINHO = ("`{endereco}`: não achei o repositório `{vizinho}` em "
                     "`{pasta}/` — endereço local nomeia o vizinho, nunca um "
                     "caminho")
LOCAL_COM_REMOTO = ("`{endereco}`: `{vizinho}` tem remoto. Endereço local é só "
                    "para repositório sem remoto; aqui o link de verdade "
                    "existe, e é ele que abre de qualquer máquina")
LOCAL_SEM_COMMIT = ("`{endereco}`: o commit `{commit}` não existe em "
                    "`{vizinho}`")
LOCAL_GIT_FALHOU = ("NÃO MEDIDO: o git não respondeu sobre `{vizinho}` "
                    "({motivo}) — `{endereco}` ficou sem conferência")

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


def o_git_do_vizinho(pasta: Path, *argumentos):
    try:
        feito = subprocess.run(
            ["git", "-C", str(pasta), *argumentos], capture_output=True,
            text=True, encoding="utf-8", errors="replace",
            timeout=TEMPO_DO_GIT_LOCAL_S)
    except (OSError, subprocess.TimeoutExpired) as erro:
        return None, type(erro).__name__
    return feito.returncode, feito.stdout.strip()


def endereco_local_do(item: str):
    _, link = partido_no_separador(item)
    return ENDERECO_LOCAL.fullmatch((link or "").strip())


def recusa_do_endereco_local(achado, cwd: str) -> str:
    endereco, vizinho, commit = achado.group(0), achado.group(1), achado.group(2)
    if not cwd:
        return LOCAL_NAO_MEDIDO.format(endereco=endereco)
    pasta = Path(cwd) / PASTA_DOS_VIZINHOS / vizinho
    if not (pasta / ".git").exists():
        return LOCAL_SEM_VIZINHO.format(endereco=endereco, vizinho=vizinho,
                                        pasta=PASTA_DOS_VIZINHOS)
    saida, remotos = o_git_do_vizinho(pasta, "remote")
    if saida != 0:
        return LOCAL_GIT_FALHOU.format(vizinho=vizinho, motivo=remotos,
                                       endereco=endereco)
    if remotos:
        return LOCAL_COM_REMOTO.format(endereco=endereco, vizinho=vizinho)
    saida, dito = o_git_do_vizinho(pasta, "cat-file", "-e",
                                   commit + "^{commit}")
    if saida is None:
        return LOCAL_GIT_FALHOU.format(vizinho=vizinho, motivo=dito,
                                       endereco=endereco)
    if saida != 0:
        return LOCAL_SEM_COMMIT.format(endereco=endereco, commit=commit,
                                       vizinho=vizinho)
    return ""


def recusa_do_pedido(issue, pedido: str, executado: list, entregue: list,
                     seu: list, cwd: str = "") -> str:
    if not issue:
        return RECUSA_SEM_ISSUE
    if not (pedido or "").strip():
        return RECUSA_SEM_PEDIDO
    if not [um for um in (executado or []) if um.strip()]:
        return RECUSA_SEM_EXECUTADO
    for bandeira, itens in (("--entregue", entregue), ("--seu", seu)):
        for item in itens or []:
            if (local := endereco_local_do(item)):
                if (recusa := recusa_do_endereco_local(local, cwd)):
                    return recusa
            elif item_sem_link(item):
                return RECUSA_SEM_LINK.format(bandeira=bandeira, item=item)
    return ""


def corpo_e_etiquetas_da_issue(conta: str, repositorio: str, issue) -> tuple:
    feito = gh.na_conta(conta, ["issue", "view", str(issue), "--repo",
                                 repositorio, "--json", "body,labels"])
    if feito is None or feito.returncode != 0:
        return None, set(), gh.berro(feito)
    try:
        dado = json.loads(feito.stdout or "{}")
        corpo = dado.get("body")
        etiquetas = {str(e.get("name")) for e in dado.get("labels") or []
                     if isinstance(e, dict)}
    except (ValueError, AttributeError) as falha:
        return None, set(), f"{type(falha).__name__}: {falha}"
    if not isinstance(corpo, str):
        return None, set(), "o rastreador não devolveu o corpo"
    return corpo, etiquetas, ""


def espera_da_issue(corpo: str, hoje: date) -> tuple:
    primeira = corpo.lstrip(MARCA_DE_ORDEM_DE_BYTES).replace(
        "\r", "").split("\n", 1)[0]
    achada = LINHA_DE_RETOMADA.match(primeira)
    if not achada:
        return ESPERA_PELO_DONO, "", True
    try:
        quando = date.fromisoformat(achada.group(1))
    except ValueError:
        return ESPERA_PELO_DONO, RECADO_DATA_INVALIDA.format(
            texto=achada.group(1)), False
    if quando > hoje:
        return ESPERA_PELO_RELOGIO, RECADO_ESPERA_PELO_RELOGIO.format(
            data=quando.isoformat(), etiqueta=ETIQUETA_RETOMAR_EM), True
    return ESPERA_QUE_VENCEU, "", True


def etiquetar(conta: str, repositorio: str, issue, poe: str,
              tira: str = "") -> tuple:
    argumentos = ["issue", "edit", str(issue), "--repo", repositorio,
                  "--add-label", poe]
    if tira:
        argumentos += ["--remove-label", tira]
    feito = gh.na_conta(conta, argumentos)
    if feito is None or feito.returncode != 0:
        return False, RECADO_ETIQUETA_FALHOU.format(
            etiqueta=poe, motivo=gh.berro(feito))
    return True, RECADO_ETIQUETA.format(etiqueta=poe)


def _executor_instalado(cwd: str) -> tuple:
    pasta = Path(cwd or ".") / MODULO_DO_EXECUTOR
    arquivo = pasta / f"{NOME_DO_EXECUTOR}.py"
    if not arquivo.is_file():
        return None, ""
    sys.path.insert(0, str(pasta))
    anterior = sys.modules.get(NOME_DO_EXECUTOR)
    try:
        origem = importlib.util.spec_from_file_location(NOME_DO_EXECUTOR,
                                                        arquivo)
        modulo = importlib.util.module_from_spec(origem)
        sys.modules[NOME_DO_EXECUTOR] = modulo
        origem.loader.exec_module(modulo)
    except (Exception, SystemExit) as falha:
        sys.modules.pop(NOME_DO_EXECUTOR, None)
        if anterior is not None:
            sys.modules[NOME_DO_EXECUTOR] = anterior
        return None, f"{type(falha).__name__}: {falha}"
    return modulo, ""


def mover_o_cartao(configuracao: dict, issue, cwd: str = "") -> tuple:
    executor, por_que_nao = _executor_instalado(cwd)
    if executor is None:
        if por_que_nao:
            return QUADRO_FALHOU, RECADO_QUADRO_NAO_IMPORTOU.format(
                motivo=por_que_nao)
        return QUADRO_DISPENSADO, RECADO_QUADRO_SEM_MODULO
    moveu, dito = executor.mover_no_quadro(configuracao, issue,
                                           SITUACAO_DE_ESPERA)
    if moveu:
        return QUADRO_FEITO, dito
    if not dito:
        return QUADRO_DISPENSADO, ""
    return QUADRO_FALHOU, RECADO_QUADRO_FALHOU.format(motivo=dito)


def avisar_o_dono(configuracao: dict, conta: str, repositorio: str, issue,
                  cwd: str, hoje: date) -> tuple:
    corpo, postas, por_que_nao_leu = corpo_e_etiquetas_da_issue(
        conta, repositorio, issue)
    recados, falhas = [], []
    if corpo is None:
        espera, confirmada = ESPERA_PELO_DONO, False
        recados.append(RECADO_CORPO_NAO_LIDO.format(motivo=por_que_nao_leu))
    else:
        espera, nota, confirmada = espera_da_issue(corpo, hoje)
        recados.append(nota)
    if not confirmada:
        falhas.append(recados[-1])
    pelo_relogio = espera == ESPERA_PELO_RELOGIO
    poe, tira = ETIQUETAS_DE_CADA_ESPERA[espera]
    etiquetou, dito = etiquetar(
        conta, repositorio, issue, poe,
        tira if confirmada and tira in postas else "")
    recados.append(dito)
    if not etiquetou:
        falhas.append(dito)
    if not pelo_relogio:
        estado, dito = mover_o_cartao(configuracao, issue, cwd)
        recados.append(dito)
        if estado == QUADRO_FALHOU:
            falhas.append(dito)
    return recados, falhas


def postar(issue, pedido: str, executado: list, entregue: list, seu: list,
           cwd: str = "", ensaio: bool = False, hoje: date = None) -> tuple:
    if (recusa := recusa_do_pedido(issue, pedido, executado, entregue, seu,
                                   cwd=cwd)):
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
    recados, falhas = [RECADO_POSTADO.format(issue=issue)], []
    if seu:
        ditos, falhas = avisar_o_dono(configuracao, conta, repositorio, issue,
                                      cwd, hoje or date.today())
        recados += ditos
    if falhas:
        recados.append(RECADO_PELA_METADE.format(falhas="; ".join(falhas)))
    return (SAIDA_PELA_METADE if falhas else 0,
            " · ".join(r for r in recados if r))


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
elif argv[:2] == ["issue", "view"]:
    if (CAIXA / "corpo-nao-se-le.txt").exists():
        sys.stderr.write("issue nao se deixou ler\\n")
        sys.exit(1)
    import json
    corpo = CAIXA / "corpo.md"
    postas = CAIXA / "etiquetas.txt"
    print(json.dumps({"body": corpo.read_text(encoding="utf-8")
                      if corpo.exists() else "Sem cabecalho nenhum.",
                      "labels": [{"name": nome} for nome in
                                 postas.read_text(encoding="utf-8").split()]
                      if postas.exists() else []}))
elif argv[:2] == ["issue", "edit"]:
    if "--remove-label" in argv and (CAIXA / "catalogo-sem-a-etiqueta.txt"
                                     ).exists():
        sys.stderr.write("etiqueta a remover nao existe no repositorio\\n")
        sys.exit(1)
    if (CAIXA / "etiqueta-recusada.txt").exists():
        sys.stderr.write("etiqueta nao existe\\n")
        sys.exit(1)
sys.exit(0)
"""

EXECUTOR_DE_MENTIRA = """import os
import pathlib

RESPOSTA = pathlib.Path(os.environ["ENTREGA_TESTE_CAIXA"]) / "quadro.txt"


def mover_no_quadro(configuracao, issue, situacao):
    dito = RESPOSTA.read_text(encoding="utf-8") if RESPOSTA.exists() else ""
    (RESPOSTA.parent / "quadro-chamado.txt").write_text(situacao)
    if dito == "moveu":
        return True, "cartao movido"
    if dito == "recusou":
        return False, "o quadro recusou o movimento"
    return False, ""
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

        def repositorio_de_prova(nome: str, com_remoto: bool) -> str:
            onde = raiz / "workspace" / PASTA_DOS_VIZINHOS / nome
            onde.mkdir(parents=True)
            for comando in (["init", "-q"],
                            ["-c", "user.name=prova", "-c",
                             "user.email=prova@exemplo", "commit", "-q",
                             "--allow-empty", "-m", "um"]):
                subprocess.run(["git", "-C", str(onde), *comando], check=True,
                               capture_output=True)
            if com_remoto:
                subprocess.run(["git", "-C", str(onde), "remote", "add",
                                "origin", "https://x.invalido/r.git"],
                               check=True, capture_output=True)
            return subprocess.run(
                ["git", "-C", str(onde), "rev-parse", "--short", "HEAD"],
                check=True, capture_output=True, text=True,
                encoding="utf-8", errors="replace").stdout.strip()

        area = str(raiz / "workspace")
        feito_sem_remoto = repositorio_de_prova("sem-remoto", False)
        feito_com_remoto = repositorio_de_prova("com-remoto", True)

        def recusa_local(endereco: str) -> str:
            return recusa_do_pedido(1, "p", ["e"], [f"o commit|{endereco}"],
                                    [], cwd=area)

        caso("repositório sem remoto entrega pelo endereço local: o nome do "
             "vizinho e o commit que existe nele",
             recusa_local(f"local:sem-remoto@{feito_sem_remoto}") == "")
        caso("commit que não existe no vizinho é recusado: endereço local "
             "também se confere",
             "não existe" in recusa_local("local:sem-remoto@0123abc"))
        caso("vizinho que TEM remoto não entrega por endereço local: o link "
             "de verdade existe, e é ele que se abre de qualquer máquina",
             "tem remoto" in recusa_local(
                 f"local:com-remoto@{feito_com_remoto}"))
        caso("vizinho que não existe é recusado pelo nome",
             "não achei" in recusa_local(f"local:fantasma@{feito_sem_remoto}"))
        caso("endereço local não aceita caminho de máquina nem subida de "
             "pasta no lugar do nome",
             "--entregue" in recusa_local(
                 f"local:../sem-remoto@{feito_sem_remoto}")
             and "--entregue" in recusa_local(
                 f"local:{area}@{feito_sem_remoto}"))
        caso("sem a raiz do workspace o endereço local não se mede, e o "
             "relato recusa em vez de confiar",
             "NÃO MEDIDO" in recusa_do_pedido(
                 1, "p", ["e"],
                 [f"o commit|local:sem-remoto@{feito_sem_remoto}"], []))
        caso("o ensaio do relato inteiro confere o endereço local contra a "
             "raiz que recebeu: aceita o que existe e recusa o que não existe",
             postar(1, "p", ["e"],
                    [f"o commit|local:sem-remoto@{feito_sem_remoto}"], [],
                    cwd=area, ensaio=True)[0] == 0
             and postar(1, "p", ["e"], ["o commit|local:sem-remoto@0123abc"],
                        [], cwd=area, ensaio=True)[0] == 2)
        caso("e o relato escreve o endereço local como veio, sem caminho de "
             "máquina",
             f"local:sem-remoto@{feito_sem_remoto}" in corpo_do_relato(
                 "p", ["e"],
                 [f"o commit|local:sem-remoto@{feito_sem_remoto}"], [])
             and area not in corpo_do_relato(
                 "p", ["e"],
                 [f"o commit|local:sem-remoto@{feito_sem_remoto}"], []))

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

        hoje = date(2026, 9, 20)
        do_dono = ["mescla o PR|https://x/pull/1"]

        def entrega_com(corpo=None, arquivos=(), quadro=None,
                        executor=None, etiquetas="", vizinho=None):
            caixa = _bancada(raiz)
            if corpo is not None:
                (caixa / "corpo.md").write_text(corpo, encoding="utf-8")
            if etiquetas:
                (caixa / "etiquetas.txt").write_text(etiquetas,
                                                     encoding="utf-8")
            for nome in arquivos:
                (caixa / nome).write_text("x", encoding="utf-8")
            if quadro is not None:
                (caixa / "quadro.txt").write_text(quadro, encoding="utf-8")
            onde = _com_configuracao(raiz, {"issues": {
                "repositorio": "dono/repo", "conta_gh": "conta-x"}})
            if executor is not None:
                modulo = Path(onde) / MODULO_DO_EXECUTOR
                modulo.mkdir(parents=True)
                (modulo / f"{NOME_DO_EXECUTOR}.py").write_text(
                    executor, encoding="utf-8")
                if vizinho is not None:
                    (modulo / "vizinho_do_executor.py").write_text(
                        vizinho, encoding="utf-8")
            codigo, recado = postar(7, "quero X", ["fiz Y"], [], do_dono,
                                    cwd=onde, hoje=hoje)
            chamadas = (caixa / "chamadas.txt").read_text(encoding="utf-8")
            return codigo, recado, chamadas, caixa

        codigo, recado, chamadas, caixa = entrega_com(
            "Retomar em: 2026-09-21\n\ncorpo", quadro="moveu",
            executor=EXECUTOR_DE_MENTIRA, etiquetas="parado-em-voce")
        caso("issue que espera o RELÓGIO, com data futura, fica com "
             "`retomar-em` e SEM `parado-em-voce`: a entrega somava a "
             "segunda etiqueta e a issue terminava com as duas",
             codigo == 0
             and "--add-label retomar-em" in chamadas
             and "--remove-label parado-em-voce" in chamadas
             and "--add-label parado-em-voce" not in chamadas)
        caso("e o cartão NÃO vai para a coluna do dono: quem espera o "
             "relógio não espera por ele",
             not (caixa / "quadro-chamado.txt").exists()
             and "relógio" in recado)
        codigo, recado, chamadas, _ = entrega_com(
            "﻿Retomar em: 2026-09-21\n\ncorpo",
            etiquetas="parado-em-voce")
        caso("marca de ordem de bytes antes da linha de retomada não a "
             "esconde: a issue terminava com as duas etiquetas e sucesso",
             "--add-label retomar-em" in chamadas
             and "--add-label parado-em-voce" not in chamadas)

        for corpo, rotulo in (("Retomar em: 2026-09-20\n\nc", "de hoje"),
                              ("Retomar em: 2026-09-19\n\nc", "de ontem")):
            codigo, recado, chamadas, _ = entrega_com(
                corpo, etiquetas="retomar-em")
            caso(f"data {rotulo} já venceu: entra `parado-em-voce` e SAI "
                 "`retomar-em`, senão a issue fica nas duas filas",
                 codigo == 0
                 and "--add-label parado-em-voce" in chamadas
                 and "--remove-label retomar-em" in chamadas)

        codigo, recado, chamadas, _ = entrega_com(
            "corpo sem cabeçalho", etiquetas="retomar-em outra-qualquer")
        caso("issue SEM a linha de retomada e ainda com `retomar-em` "
             "pendurada perde a etiqueta velha: exclusividade vale também "
             "sem cabeçalho",
             codigo == 0 and "--add-label parado-em-voce" in chamadas
             and "--remove-label retomar-em" in chamadas)
        codigo, recado, chamadas, _ = entrega_com(
            "Retomar em: 2026-09-21\n",
            arquivos=("catalogo-sem-a-etiqueta.txt",))
        caso("etiqueta que a issue NÃO tem não se manda tirar: o "
             "rastreador recusa remover nome que o repositório não "
             "conhece, e a entrega saía pela metade sem precisar",
             codigo == 0 and "--remove-label" not in chamadas)

        codigo, recado, chamadas, _ = entrega_com("corpo sem cabeçalho")
        caso("CONTROLE: issue sem a linha de retomada segue como sempre — "
             "só ganha `parado-em-voce`",
             codigo == 0
             and f"--add-label {ETIQUETA_PARADO_EM_VOCE}" in chamadas
             and "--remove-label" not in chamadas)
        codigo, recado, chamadas, _ = entrega_com(
            "\nRetomar em: 2026-12-01\n")
        caso("a linha de retomada vale na PRIMEIRA linha física, como o "
             "dono decidiu: depois de linha vazia ela não conta",
             f"--add-label {ETIQUETA_PARADO_EM_VOCE}" in chamadas)

        codigo, recado, chamadas, _ = entrega_com(
            "Retomar em: amanhã cedo\n")
        caso("data INVÁLIDA não é cabeçalho ausente: a entrega diz que a "
             "data não se entende, chama o dono, e sai PELA METADE",
             codigo == SAIDA_PELA_METADE and "data" in recado.lower()
             and f"--add-label {ETIQUETA_PARADO_EM_VOCE}" in chamadas)
        codigo, recado, chamadas, _ = entrega_com(
            arquivos=("corpo-nao-se-le.txt",))
        caso("corpo que NÃO SE LEU não decide pela ausência: chama o dono, "
             "diz que não leu, e sai PELA METADE para alguém conferir",
             codigo == SAIDA_PELA_METADE and "não li" in recado
             and f"--add-label {ETIQUETA_PARADO_EM_VOCE}" in chamadas)

        codigo, recado, chamadas, caixa = entrega_com(
            "sem cabeçalho", arquivos=("etiqueta-recusada.txt",),
            quadro="moveu", executor=EXECUTOR_DE_MENTIRA)
        caso("etiqueta que FALHA não sai com código de sucesso: quem "
             "confere só o código recebia sucesso de entrega pela metade",
             codigo == SAIDA_PELA_METADE)
        caso("a entrega pela metade ainda diz a frase que o gancho do "
             "relato reconhece, manda NÃO rodar de novo, e postou UM "
             "comentário só",
             RECADO_POSTADO.format(issue=7) in recado
             and "NÃO rode" in recado
             and (caixa / "postado.md").read_text(
                 encoding="utf-8").count(TITULO) == 1)
        caso("e o cartão ainda é tentado depois de a etiqueta falhar, com a "
             "situação de espera, dita por extenso",
             (caixa / "quadro-chamado.txt").exists()
             and (caixa / "quadro-chamado.txt").read_text(
                 encoding="utf-8") == "parada")
        caso("o código da entrega pela metade é TRÊS, e a recusa é DOIS: "
             "quem chama confere número, e número trocado passava calado",
             codigo == 3 and SAIDA_PELA_METADE == 3)

        codigo, recado, _, _ = entrega_com(
            "sem cabeçalho", quadro="moveu",
            executor=("ESTADO = []\n"
                      "import vizinho_do_executor\n"
                      "def mover_no_quadro(configuracao, issue, situacao):\n"
                      "    vizinho_do_executor.marca()\n"
                      "    return True, 'estado %d' % len(ESTADO)\n"),
            vizinho=("def marca():\n"
                     "    import encadeador\n"
                     "    encadeador.ESTADO.append(1)\n"))
        caso("executor cujo VIZINHO o importa pelo nome enxerga a MESMA "
             "instância: carregado fora do registro de módulos, o vizinho "
             "mexia numa cópia",
             codigo == 0 and "estado 1" in recado)
        codigo, recado, _, _ = entrega_com(
            "sem cabeçalho",
            executor=("from __future__ import annotations\n"
                      "from dataclasses import dataclass\n"
                      "@dataclass\n"
                      "class Cartao:\n"
                      "    numero: int\n"
                      "def mover_no_quadro(configuracao, issue, situacao):\n"
                      "    return True, 'cartao %d' % Cartao(7).numero\n"))
        caso("executor com classe de dados e anotações adiadas carrega: "
             "a classe de dados procura o módulo no registro",
             codigo == 0 and "cartao 7" in recado)
        try:
            codigo, recado, _, _ = entrega_com(
                "sem cabeçalho", executor="raise SystemExit(2)\n")
        except SystemExit:
            codigo, recado = "escapou", ""
        caso("executor que ENCERRA o processo ao ser importado é falha da "
             "entrega pela metade, não saída do instrumento inteiro",
             codigo == 3 and "não importou" in recado)

        codigo, recado, _, _ = entrega_com(
            "sem cabeçalho", quadro="recusou", executor=EXECUTOR_DE_MENTIRA)
        caso("quadro que RECUSA o movimento é falha: sai pela metade e "
             "nomeia o que refazer",
             codigo == SAIDA_PELA_METADE and "quadro recusou" in recado)
        codigo, recado, _, _ = entrega_com(
            "sem cabeçalho", quadro="", executor=EXECUTOR_DE_MENTIRA)
        caso("CONTROLE: executor instalado SEM coluna configurada é "
             "dispensa legítima, não falha — sai zero",
             codigo == 0)
        codigo, recado, _, _ = entrega_com(
            "sem cabeçalho", executor="import modulo_que_nao_existe_aqui\n")
        caso("executor PRESENTE que não importa é falha, não ausência: "
             "dependência quebrada não se dispensa como módulo ausente",
             codigo == SAIDA_PELA_METADE and "não importou" in recado)
        codigo, recado, _, _ = entrega_com("sem cabeçalho")
        caso("CONTROLE: módulo do executor AUSENTE segue saindo zero",
             codigo == 0 and RECADO_QUADRO_SEM_MODULO in recado)

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
                        help="`o que|link` por artefato entregue; em "
                             "repositório SEM remoto, o link é "
                             "`local:<vizinho>@<commit>`, conferido no disco")
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
    for canal in (sys.stdin, sys.stdout, sys.stderr):
        if not getattr(canal, "closed", True) and hasattr(canal, "reconfigure"):
            canal.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
