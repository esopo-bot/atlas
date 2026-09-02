import argparse
import json
import os
import re
import shlex
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "gh"))
import gh

DESCRICAO_DA_CLI = (
    "põe, atualiza e poda linha no quadro — a caixa permanente onde defeito "
    "e melhoria moram juntos, cada linha com a etiqueta do seu tipo. Mesma "
    "identidade, mesma linha: o quadro não vira log. O relatório da rodada "
    "não é linha: entra como comentário novo, um por rodada")

BANDEIRA_DE_TESTE = "--testar"

MARCA_ABRE = "<!-- escrito pelo executor de roteiros -->"
MARCA_FECHA = "<!-- /escrito pelo executor de roteiros -->"

DEFEITO = "defeito"
MELHORIA = "melhoria"
TIPOS = (DEFEITO, MELHORIA)
CAMPO_DA_CAIXA = {DEFEITO: "defeitos", MELHORIA: "melhorias"}
PODA = "podar"
RELATO = "relatar"

SEPARADOR = " · visto em "
LIGA_ASSUNTO_AO_CORPO = " — "
LINHA_DO_ACHADO = "- **{id}** `{tipo}` — {assunto}" + SEPARADOR + "{quando}"
LEITURA_DA_LINHA = re.compile(
    r"^- \*\*(?P<id>[a-z0-9][a-z0-9-]*)\*\* `(?P<tipo>"
    + "|".join(TIPOS) + r")` — (?P<assunto>.+?)"
    + re.escape(SEPARADOR) + r"(?P<quando>\d{4}-\d{2}-\d{2})$")
COMECO_DA_LINHA = re.compile(r"^- \*\*")
PADRAO_DA_IDENTIDADE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
PADRAO_DA_DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ESPACO_DEMAIS = re.compile(r"\s+")

RECUSA_IDENTIDADE = (
    "erro de uso: a identidade {valor!r} não serve. Ela é a chave que faz o "
    "mesmo achado virar UMA linha entre rodadas — use minúsculas, dígitos e "
    "hífen, e nomeie o ASSUNTO, nunca a ocorrência")
RECUSA_SEM_ASSUNTO = (
    "erro de uso: --assunto vazio. A linha precisa dizer o que é, ou o "
    "quadro guarda uma chave que ninguém entende")
RECUSA_DATA = (
    "erro de uso: --quando {valor!r} não é uma data AAAA-MM-DD")
RECUSA_SEM_BLOCO = (
    "erro de ambiente: o corpo da caixa não tem o bloco marcado. O "
    "instrumento só escreve entre {abre} e {fecha} — sem os dois ele não "
    "escreve nada, para não apagar texto que gente pôs à mão")
RECUSA_LINHA_QUE_NAO_LEIO = (
    "erro de ambiente: a caixa {issue} tem no bloco uma linha que eu não sei "
    "ler, e reescrever o bloco a apagaria. Passe-a para o formato de hoje "
    "({formato}) e rode de novo. A primeira que achei: {linha}")
RECUSA_LINHA_QUE_NAO_EXISTE = (
    "erro de uso: não achei a linha {id} no quadro da(s) caixa(s) {issues}. "
    "Poda-se o que está lá — veja a identidade e rode de novo")
RECUSA_SEM_CORPO = (
    "erro de uso: --corpo vazio. O relatório é o comentário inteiro: sem "
    "texto eu não abro comentário nenhum na caixa")

ARQUIVO_DO_EXECUTOR = "nucleo/executor.json"
CAMPO_DAS_CAIXAS = "caixas"
CAMPO_DAS_ISSUES = "issues"
CAMPO_DO_REPOSITORIO = "repositorio"
CAMPO_DA_CONTA = "conta_gh"
MARCA_DE_VALOR_POR_PREENCHER = "${"
TENTATIVAS_DE_GRAVACAO = 3

RECUSA_TIPO = "erro de uso: tipo {valor!r} não existe. Os que existem: {tipos}"
RECUSA_QUADRO = (
    "erro de uso: --quadro {valor!r} não é número de issue. Aponte o "
    "instrumento para o quadro de outro assunto com o número dele — o "
    "repositório e a conta continuam vindo da configuração, porque o quadro "
    "do cliente nasce no mesmo repositório")
RECUSA_SEM_CONFIGURACAO = (
    "erro de ambiente: não li {alvo} ({erro}). É lá que moram os números das "
    "caixas, e é por ele ser local que eles não entram em texto rastreado")
RECUSA_SEM_CAIXAS = (
    "erro de ambiente: {alvo} não declara {campo}. Declare {campo}.defeitos "
    "e {campo}.melhorias, cada um com o número da sua issue permanente — sem "
    "isso não escrevo em lugar nenhum, e não invento issue")
RECUSA_SEM_O_TIPO = (
    "erro de ambiente: {alvo} não declara {campo}.{qual}, que é o número da "
    "caixa de {qual} — sem ele não escrevo em lugar nenhum")
RECUSA_SEM_REPOSITORIO = (
    "erro de ambiente: {alvo} não declara {campo}.{qual}, e sem ele não sei "
    "em que repositório a caixa mora")
FALHA_AO_LER = "erro de ambiente: não li a caixa {issue} — {motivo}"
FALHA_AO_GRAVAR = "erro de ambiente: não gravei na caixa {issue} — {motivo}"
FALHA_AO_COMENTAR = (
    "erro de ambiente: não comentei na caixa {issue} — {motivo}. A linha "
    "{id} continua no quadro: sem o registro do fechamento, não podo")
FALHA_AO_RELATAR = (
    "erro de ambiente: não comentei o relatório na caixa {issue} — {motivo}. "
    "Nada foi escrito: o quadro não mudou")
NAO_ESTA_LA = (
    "erro de ambiente: gravei na caixa {issue} e reli, e a linha {id} NÃO "
    "está lá. Duas sessões escrevendo ao mesmo tempo é a explicação mais "
    "provável: quem grava por último vence. Rode de novo e confesse isto na "
    "evidência")
AINDA_ESTA_LA = (
    "erro de ambiente: podei na caixa {issue} e reli, e a linha {id} AINDA "
    "está lá. O comentário do fechamento já subiu: rode de novo e confesse "
    "isto na evidência")

RECADO_POSTO = "posto na caixa {issue}: {id}"
RECADO_ATUALIZADO = "atualizado na caixa {issue}: {id}"
RECADO_JA_ESTAVA = "já estava igual na caixa {issue}: {id} — não regravei"
RECADO_DO_ENSAIO = "ensaio — o bloco da caixa {issue} ficaria assim:{miolo}"
RECADO_PODADO = (
    "podado do quadro da caixa {issue}: {id} — o fechamento ficou em "
    "comentário")
RECADO_DO_ENSAIO_DA_PODA = (
    "ensaio — a linha {id} sairia do quadro da caixa {issue}, e o comentário "
    "seria:\n{registro}")
RECADO_RELATADO = "relatório em comentário novo na caixa {issue}"
RECADO_DO_ENSAIO_DO_RELATO = (
    "ensaio — o relatório entraria como comentário novo na caixa {issue}, e "
    "seria:\n{corpo}")

REGISTRO_DA_PODA = ("Podado do quadro em {quando} — a linha, como estava:"
                    "\n\n{linha}\n")
MOTIVO_DA_PODA = "\nMotivo: {motivo}\n"

AJUDA_ACAO = ("em que caixa a linha entra, `" + PODA + "` para tirar a "
              "linha do quadro, ou `" + RELATO + "` para escrever o "
              "relatório da rodada como comentário novo")
AJUDA_ID = "a identidade estável do achado, em kebab minúsculo"
AJUDA_ASSUNTO = "o que a linha diz — o assunto, nunca a ocorrência"
AJUDA_MOTIVO = "por que a linha saiu — entra no comentário do fechamento"
AJUDA_QUANDO = "a data do avistamento (padrão: hoje)"
AJUDA_CORPO = ("em `" + RELATO + "`, o relatório inteiro, que vira o "
               "comentário novo; em defeito e melhoria, o detalhe que entra "
               "na linha atrás do assunto — nunca é descartado")
AJUDA_CWD = "a raiz onde mora " + ARQUIVO_DO_EXECUTOR + " (padrão: aqui)"
AJUDA_ENSAIO = "mostra o que subiria, sem escrever na caixa"
AJUDA_QUADRO = ("número da issue do quadro, quando não for o declarado na "
                "configuração — é assim que um assunto com quadro próprio "
                "recebe as linhas dele")


def identidade_serve(valor) -> bool:
    return bool(valor and PADRAO_DA_IDENTIDADE.match(valor))


def na_linha(texto: str) -> str:
    return ESPACO_DEMAIS.sub(" ", (texto or "").strip())


def achado(tipo: str, identidade: str, assunto: str, quando: str,
           corpo: str = "") -> dict:
    return {"id": identidade, "tipo": tipo,
            "assunto": na_linha(assunto_com_o_corpo(assunto, corpo)),
            "quando": quando}


def assunto_com_o_corpo(assunto: str, corpo: str) -> str:
    if not (corpo or "").strip():
        return assunto
    return assunto + LIGA_ASSUNTO_AO_CORPO + corpo


def partes_do_corpo(corpo: str) -> tuple:
    abre = corpo.find(MARCA_ABRE)
    fecha = corpo.find(MARCA_FECHA)
    if abre < 0 or fecha < 0 or fecha < abre:
        return ()
    return (corpo[:abre + len(MARCA_ABRE)],
            corpo[abre + len(MARCA_ABRE):fecha],
            corpo[fecha:])


def e_achado(item) -> bool:
    return isinstance(item, dict)


def so_espaco(item) -> bool:
    return not e_achado(item) and not item.strip()


def itens_do_miolo(miolo: str) -> list:
    itens = []
    for linha in miolo.splitlines():
        encontrado = LEITURA_DA_LINHA.match(linha.strip())
        itens.append(encontrado.groupdict() if encontrado else linha)
    while itens and so_espaco(itens[0]):
        itens.pop(0)
    while itens and so_espaco(itens[-1]):
        itens.pop()
    return itens


def achados_do_miolo(miolo: str) -> list:
    return [item for item in itens_do_miolo(miolo) if e_achado(item)]


def linhas_que_nao_leio(miolo: str) -> list:
    perdidas = []
    for linha in miolo.splitlines():
        limpa = linha.strip()
        if COMECO_DA_LINHA.match(limpa) and not LEITURA_DA_LINHA.match(limpa):
            perdidas.append(limpa)
    return perdidas


def o_mesmo_achado(item, identidade: str) -> bool:
    return e_achado(item) and item["id"] == identidade


def com_o_achado(itens: list, novo: dict) -> list:
    trocados = [dict(novo) if o_mesmo_achado(item, novo["id"]) else item
                for item in itens]
    if not any(o_mesmo_achado(item, novo["id"]) for item in itens):
        trocados.append(dict(novo))
    return trocados


def miolo_com(itens: list) -> str:
    if not itens:
        return "\n"
    return "\n" + "".join(
        (LINHA_DO_ACHADO.format(**item) if e_achado(item) else item) + "\n"
        for item in itens)


def corpo_com(corpo: str, novo: dict) -> str:
    partes = partes_do_corpo(corpo)
    if not partes:
        return ""
    antes, miolo, depois = partes
    return antes + miolo_com(com_o_achado(itens_do_miolo(miolo), novo)) \
        + depois


def corpo_sem(corpo: str, identidade: str) -> str:
    partes = partes_do_corpo(corpo)
    if not partes:
        return ""
    antes, miolo, depois = partes
    sobrando = [item for item in itens_do_miolo(miolo)
                if not o_mesmo_achado(item, identidade)]
    return antes + miolo_com(sobrando) + depois


def preenchido(valor) -> bool:
    if valor is None or valor == "":
        return False
    return MARCA_DE_VALOR_POR_PREENCHER not in str(valor)


def endereco_da_caixa(tipo: str, cwd: str = "", quadro: str = "") -> tuple:
    if tipo not in TIPOS:
        return {}, RECUSA_TIPO.format(valor=tipo, tipos=", ".join(TIPOS))
    pedido = str(quadro).strip()
    if quadro and not (pedido.isascii() and pedido.isdigit()):
        return {}, RECUSA_QUADRO.format(valor=quadro)
    alvo = (Path(cwd) if cwd else Path.cwd()) / ARQUIVO_DO_EXECUTOR
    try:
        dado = json.loads(alvo.read_text(encoding="utf-8"))
    except (OSError, ValueError) as erro:
        return {}, RECUSA_SEM_CONFIGURACAO.format(alvo=ARQUIVO_DO_EXECUTOR,
                                                  erro=erro)
    caixas = dado.get(CAMPO_DAS_CAIXAS) if isinstance(dado, dict) else None
    if not isinstance(caixas, dict):
        return {}, RECUSA_SEM_CAIXAS.format(alvo=ARQUIVO_DO_EXECUTOR,
                                            campo=CAMPO_DAS_CAIXAS)
    qual = CAMPO_DA_CAIXA[tipo]
    if not preenchido(caixas.get(qual)):
        return {}, RECUSA_SEM_O_TIPO.format(alvo=ARQUIVO_DO_EXECUTOR,
                                            campo=CAMPO_DAS_CAIXAS, qual=qual)
    issues = dado.get(CAMPO_DAS_ISSUES)
    issues = issues if isinstance(issues, dict) else {}
    if not preenchido(issues.get(CAMPO_DO_REPOSITORIO)):
        return {}, RECUSA_SEM_REPOSITORIO.format(alvo=ARQUIVO_DO_EXECUTOR,
                                                 campo=CAMPO_DAS_ISSUES,
                                                 qual=CAMPO_DO_REPOSITORIO)
    return {"issue": int(quadro) if quadro else caixas[qual],
            "repositorio": issues[CAMPO_DO_REPOSITORIO],
            "conta": issues.get(CAMPO_DA_CONTA) or ""}, ""


def enderecos_das_caixas(cwd: str = "", quadro: str = "") -> tuple:
    enderecos, primeiro_erro = [], ""
    for tipo in TIPOS:
        endereco, erro = endereco_da_caixa(tipo, cwd, quadro)
        if erro:
            primeiro_erro = primeiro_erro or erro
        elif endereco["issue"] not in [um["issue"] for um in enderecos]:
            enderecos.append(endereco)
    return enderecos, "" if enderecos else primeiro_erro


def ler_corpo(endereco: dict) -> tuple:
    feito = gh.na_conta(endereco["conta"],
                         ["issue", "view", str(endereco["issue"]),
                          "--repo", endereco["repositorio"],
                          "--json", "body"])
    if feito is None or feito.returncode != 0:
        return "", FALHA_AO_LER.format(issue=endereco["issue"],
                                       motivo=gh.berro(feito))
    try:
        return json.loads(feito.stdout).get("body") or "", ""
    except (ValueError, AttributeError) as erro:
        return "", FALHA_AO_LER.format(issue=endereco["issue"], motivo=erro)


def gravar_corpo(endereco: dict, corpo: str) -> str:
    feito = gh.na_conta(endereco["conta"],
                         ["issue", "edit", str(endereco["issue"]),
                          "--repo", endereco["repositorio"],
                          "--body-file", "-"], entrada=corpo)
    if feito is None or feito.returncode != 0:
        return FALHA_AO_GRAVAR.format(issue=endereco["issue"],
                                      motivo=gh.berro(feito))
    return ""


def comentar(endereco: dict, texto: str) -> str:
    feito = gh.na_conta(endereco["conta"],
                         ["issue", "comment", str(endereco["issue"]),
                          "--repo", endereco["repositorio"],
                          "--body-file", "-"], entrada=texto)
    if feito is None or feito.returncode != 0:
        return gh.berro(feito)
    return ""


def _achados_do_corpo(corpo: str) -> list:
    partes = partes_do_corpo(corpo)
    return achados_do_miolo(partes[1]) if partes else []


def _identidades_do_corpo(corpo: str) -> set:
    return {um["id"] for um in _achados_do_corpo(corpo)}


def a_linha(corpo: str, identidade: str) -> dict:
    achadas = [um for um in _achados_do_corpo(corpo)
               if um["id"] == identidade]
    return achadas[0] if achadas else {}


def recusa_do_bloco(corpo: str, issue) -> str:
    partes = partes_do_corpo(corpo)
    if not partes:
        return RECUSA_SEM_BLOCO.format(abre=MARCA_ABRE, fecha=MARCA_FECHA)
    perdidas = linhas_que_nao_leio(partes[1])
    if perdidas:
        return RECUSA_LINHA_QUE_NAO_LEIO.format(issue=issue,
                                                formato=LINHA_DO_ACHADO,
                                                linha=perdidas[0])
    return ""


def gravar_relendo(endereco: dict, corpo: str, refazer, o_que) -> tuple:
    esperadas = _identidades_do_corpo(refazer(corpo, o_que))
    tiradas = _identidades_do_corpo(corpo) - esperadas
    gravacoes = 0
    while True:
        atual, erro = ler_corpo(endereco)
        if erro:
            return gravacoes, set(), erro
        erro = recusa_do_bloco(atual, endereco["issue"])
        if erro:
            return gravacoes, set(), erro
        presentes = _identidades_do_corpo(atual)
        divergentes = (esperadas - presentes) | (tiradas & presentes)
        proposto = refazer(atual, o_que)
        if proposto == atual or gravacoes == TENTATIVAS_DE_GRAVACAO:
            return gravacoes, divergentes, ""
        esperadas |= _identidades_do_corpo(proposto)
        tiradas |= presentes - _identidades_do_corpo(proposto)
        erro = gravar_corpo(endereco, proposto)
        if erro:
            return gravacoes, set(), erro
        gravacoes += 1


def por_na_caixa(endereco: dict, novo: dict, ensaio: bool = False) -> tuple:
    corpo, erro = ler_corpo(endereco)
    if erro:
        return 2, erro
    erro = recusa_do_bloco(corpo, endereco["issue"])
    if erro:
        return 2, erro
    if ensaio:
        return 0, RECADO_DO_ENSAIO.format(
            issue=endereco["issue"],
            miolo=partes_do_corpo(corpo_com(corpo, novo))[1])
    ja_estava = any(um["id"] == novo["id"] for um in _achados_do_corpo(corpo))
    gravacoes, divergentes, erro = gravar_relendo(endereco, corpo, corpo_com,
                                                  novo)
    if erro:
        return 2, erro
    if divergentes:
        return 2, NAO_ESTA_LA.format(issue=endereco["issue"],
                                     id=", ".join(sorted(divergentes)))
    if not gravacoes:
        return 0, RECADO_JA_ESTAVA.format(issue=endereco["issue"],
                                          id=novo["id"])
    recado = RECADO_ATUALIZADO if ja_estava else RECADO_POSTO
    return 0, recado.format(issue=endereco["issue"], id=novo["id"])


def rodar(tipo: str, identidade: str, assunto: str, quando: str,
          cwd: str = "", ensaio: bool = False, quadro: str = "",
          corpo: str = "") -> tuple:
    if not identidade_serve(identidade):
        return 2, RECUSA_IDENTIDADE.format(valor=identidade)
    if not na_linha(assunto):
        return 2, RECUSA_SEM_ASSUNTO
    if not PADRAO_DA_DATA.match(quando or ""):
        return 2, RECUSA_DATA.format(valor=quando)
    endereco, erro = endereco_da_caixa(tipo, cwd, quadro)
    if erro:
        return 2, erro
    return por_na_caixa(endereco,
                        achado(tipo, identidade, assunto, quando, corpo),
                        ensaio)


def achar_a_linha(enderecos: list, identidade: str) -> tuple:
    for endereco in enderecos:
        corpo, erro = ler_corpo(endereco)
        if erro:
            return {}, "", erro
        erro = recusa_do_bloco(corpo, endereco["issue"])
        if erro:
            return {}, "", erro
        if a_linha(corpo, identidade):
            return endereco, corpo, ""
    return {}, "", RECUSA_LINHA_QUE_NAO_EXISTE.format(
        id=identidade,
        issues=", ".join(str(um["issue"]) for um in enderecos))


def registro_da_poda(alvo: dict, quando: str, motivo: str) -> str:
    escrito = REGISTRO_DA_PODA.format(quando=quando,
                                      linha=LINHA_DO_ACHADO.format(**alvo))
    limpo = na_linha(motivo)
    return escrito + (MOTIVO_DA_PODA.format(motivo=limpo) if limpo else "")


def podar_da_caixa(endereco: dict, corpo: str, identidade: str,
                   registro: str, ensaio: bool = False) -> tuple:
    if ensaio:
        return 0, RECADO_DO_ENSAIO_DA_PODA.format(issue=endereco["issue"],
                                                  id=identidade,
                                                  registro=registro)
    berro = comentar(endereco, registro)
    if berro:
        return 2, FALHA_AO_COMENTAR.format(issue=endereco["issue"],
                                           id=identidade, motivo=berro)
    _, divergentes, erro = gravar_relendo(endereco, corpo, corpo_sem,
                                          identidade)
    if erro:
        return 2, erro
    if identidade in divergentes:
        return 2, AINDA_ESTA_LA.format(issue=endereco["issue"], id=identidade)
    if divergentes:
        return 2, NAO_ESTA_LA.format(issue=endereco["issue"],
                                     id=", ".join(sorted(divergentes)))
    return 0, RECADO_PODADO.format(issue=endereco["issue"], id=identidade)


def podar(identidade: str, quando: str, cwd: str = "", motivo: str = "",
          ensaio: bool = False, quadro: str = "") -> tuple:
    if not identidade_serve(identidade):
        return 2, RECUSA_IDENTIDADE.format(valor=identidade)
    if not PADRAO_DA_DATA.match(quando or ""):
        return 2, RECUSA_DATA.format(valor=quando)
    enderecos, erro = enderecos_das_caixas(cwd, quadro)
    if erro:
        return 2, erro
    endereco, corpo, erro = achar_a_linha(enderecos, identidade)
    if erro:
        return 2, erro
    return podar_da_caixa(
        endereco, corpo, identidade,
        registro_da_poda(a_linha(corpo, identidade), quando, motivo), ensaio)


def relatar(corpo: str, cwd: str = "", ensaio: bool = False,
            quadro: str = "") -> tuple:
    if not (corpo or "").strip():
        return 2, RECUSA_SEM_CORPO
    enderecos, erro = enderecos_das_caixas(cwd, quadro)
    if erro:
        return 2, erro
    endereco = enderecos[0]
    if ensaio:
        return 0, RECADO_DO_ENSAIO_DO_RELATO.format(issue=endereco["issue"],
                                                    corpo=corpo)
    berro = comentar(endereco, corpo)
    if berro:
        return 2, FALHA_AO_RELATAR.format(issue=endereco["issue"],
                                          motivo=berro)
    return 0, RECADO_RELATADO.format(issue=endereco["issue"])


FALSO_GH = """import json
import os
import sys
from pathlib import Path

CORPO = Path(os.environ["CAIXA_TESTE_CORPO"])
LOG = Path(os.environ["CAIXA_TESTE_LOG"])
COMENTARIOS = Path(os.environ["CAIXA_TESTE_COMENTARIOS"])

with LOG.open("a", encoding="utf-8") as registro:
    registro.write(" ".join(sys.argv[1:]) + chr(10))
if "view" in sys.argv:
    print(json.dumps({"body": CORPO.read_text(encoding="utf-8")}))
elif "comment" in sys.argv:
    if os.environ.get("CAIXA_TESTE_RECUSA_COMENTARIO"):
        sys.exit(2)
    with COMENTARIOS.open("a", encoding="utf-8") as escrito:
        escrito.write(sys.stdin.read() + chr(10))
elif "edit" in sys.argv and not os.environ.get("CAIXA_TESTE_ENGOLE"):
    CORPO.write_text(sys.stdin.read(), encoding="utf-8")
"""


def testar() -> int:
    import tempfile
    falhas, rodados = [], []

    def caso(rotulo, condicao):
        rodados.append(rotulo)
        if not condicao:
            falhas.append(rotulo)

    molde = ("prosa de gente antes\n\n" + MARCA_ABRE + "\n" + MARCA_FECHA
             + "\n\nprosa de gente depois\n")
    hoje = "2026-08-22"
    amanha = "2026-08-23"
    um = achado(DEFEITO, "prova-nao-reproduz",
                "a prova declarada dá outra coisa", hoje)
    velha = "- **linha-velha** — sem etiqueta nenhuma" + SEPARADOR + hoje

    com_corpo = achado(DEFEITO, "com-corpo", "o assunto curto", hoje,
                       corpo="a receita de repetir\ne o contorno")
    caso("--corpo não é descartado: o detalhe entra na linha, atrás do "
         "assunto, e a linha continua de uma linha só",
         com_corpo["assunto"] == "o assunto curto — a receita de repetir "
         "e o contorno")
    caso("sem corpo, o assunto sai como sempre",
         achado(DEFEITO, "sem-corpo", "só o assunto", hoje)["assunto"]
         == "só o assunto")
    caso("identidade em kebab minúsculo serve",
         identidade_serve("prova-nao-reproduz"))
    caso("identidade com espaço não serve", not identidade_serve("prova nao"))
    caso("identidade com maiúscula não serve",
         not identidade_serve("Prova"))
    caso("identidade vazia não serve", not identidade_serve(""))

    posto = corpo_com(molde, um)
    caso("o achado posto vira uma linha no bloco",
         len(achados_do_miolo(partes_do_corpo(posto)[1])) == 1)

    de_novo = corpo_com(posto, um)
    caso("o mesmo achado, posto duas vezes, deixa UMA linha",
         len(achados_do_miolo(partes_do_corpo(de_novo)[1])) == 1)
    caso("e posto duas vezes o corpo nem muda", de_novo == posto)

    mudou = corpo_com(posto, achado(DEFEITO, "prova-nao-reproduz",
                                    "agora reproduz noutra máquina", amanha))
    lidos = achados_do_miolo(partes_do_corpo(mudou)[1])
    caso("achado que mudou de estado atualiza a linha, não acrescenta outra",
         len(lidos) == 1 and lidos[0]["quando"] == amanha)

    outro = corpo_com(posto, achado(MELHORIA, "seguiu-sem-prova",
                                    "etapa sem prova", hoje))
    lidos = achados_do_miolo(partes_do_corpo(outro)[1])
    caso("achado de outra identidade entra sem apagar o que já estava",
         [um["id"] for um in lidos]
         == ["prova-nao-reproduz", "seguiu-sem-prova"])

    caso("a linha escrita traz a etiqueta do tipo",
         "`" + DEFEITO + "`" in posto)
    caso("defeito e melhoria moram no mesmo bloco, cada um com sua etiqueta",
         [um["tipo"] for um in lidos] == [DEFEITO, MELHORIA])

    virou = corpo_com(posto, achado(MELHORIA, "prova-nao-reproduz",
                                    "a prova declarada dá outra coisa", hoje))
    lidos = achados_do_miolo(partes_do_corpo(virou)[1])
    caso("a mesma identidade com outro tipo troca a etiqueta, sem duplicar",
         len(lidos) == 1 and lidos[0]["tipo"] == MELHORIA)

    caso("linha sem etiqueta de tipo não se lê como achado",
         achados_do_miolo("\n" + velha + "\n") == [])
    caso("e ela é nomeada como linha que o instrumento não sabe ler",
         linhas_que_nao_leio("\n" + velha + "\n") == [velha])
    caso("linha que o instrumento sabe ler não entra nessa lista",
         linhas_que_nao_leio(partes_do_corpo(posto)[1]) == [])

    estranho = ("  nota indentada debaixo da linha",
                "Prosa solta que alguém pôs no meio do bloco.",
                "<!-- marca que alguém deixou aqui -->")
    com_estranhas = (MARCA_ABRE + "\n" + LINHA_DO_ACHADO.format(**um) + "\n"
                     + "\n".join(estranho) + "\n" + MARCA_FECHA + "\n")
    escrito = corpo_com(com_estranhas, achado(DEFEITO, "chegou-depois",
                                              "achado novo", amanha))
    caso("linha que o instrumento não entende sobrevive à escrita seguinte",
         all(linha in escrito for linha in estranho))
    caso("e a escrita que a preservou também pôs o achado novo",
         "chegou-depois" in escrito)
    caso("a poda preserva a linha que o instrumento não entende",
         all(linha in corpo_sem(com_estranhas, "prova-nao-reproduz")
             for linha in estranho))
    caso("escrever duas vezes não multiplica linha preservada nem em branco",
         corpo_com(escrito, achado(DEFEITO, "chegou-depois",
                                   "achado novo", amanha)) == escrito)

    tirado = corpo_sem(outro, "prova-nao-reproduz")
    caso("a poda tira só a linha pedida e deixa as outras",
         [um["id"] for um in achados_do_miolo(partes_do_corpo(tirado)[1])]
         == ["seguiu-sem-prova"])
    caso("e a poda não toca no texto que gente pôs fora do bloco",
         tirado.startswith("prosa de gente antes")
         and tirado.endswith("prosa de gente depois\n"))

    atualizado = corpo_com(outro, achado(DEFEITO, "prova-nao-reproduz",
                                         "de novo", amanha))
    caso("linha atualizada fica onde estava, não vai para o fim",
         [um["id"] for um in achados_do_miolo(partes_do_corpo(atualizado)[1])]
         == ["prova-nao-reproduz", "seguiu-sem-prova"])

    caso("texto posto à mão FORA do bloco sobrevive à escrita",
         posto.startswith("prosa de gente antes")
         and posto.endswith("prosa de gente depois\n"))
    caso("e sobrevive à segunda escrita também",
         outro.startswith("prosa de gente antes")
         and outro.endswith("prosa de gente depois\n"))

    caso("corpo sem o bloco marcado não é escrito",
         corpo_com("só prosa, sem marca nenhuma\n", um) == "")
    caso("corpo com a marca de abrir e sem a de fechar não é escrito",
         corpo_com("a\n" + MARCA_ABRE + "\nb\n", um) == "")

    caso("linha que não é achado, dentro do bloco, não vira achado",
         achados_do_miolo("\n- uma nota de gente\ntexto solto\n") == [])

    quebrado = corpo_com(molde, achado(DEFEITO, "com-quebra",
                                       "primeira\nsegunda", hoje))
    lidos = achados_do_miolo(partes_do_corpo(quebrado)[1])
    caso("assunto com quebra de linha vira uma linha só",
         len(lidos) == 1 and lidos[0]["assunto"] == "primeira segunda")

    com_separador = corpo_com(molde, achado(
        DEFEITO, "com-separador", "o texto tem" + SEPARADOR + "no meio",
        hoje))
    lidos = achados_do_miolo(partes_do_corpo(com_separador)[1])
    caso("assunto que contém o separador ainda se lê inteiro",
         len(lidos) == 1 and lidos[0]["quando"] == hoje
         and lidos[0]["assunto"].endswith("no meio"))

    escrito = registro_da_poda(um, amanha, "entregue na rodada de hoje")
    caso("o registro da poda guarda a linha inteira, como ela estava",
         LINHA_DO_ACHADO.format(**um) in escrito and amanha in escrito)
    caso("e guarda o motivo quando alguém deu um",
         "entregue na rodada de hoje" in escrito)
    caso("sem motivo, o registro não inventa um",
         "Motivo" not in registro_da_poda(um, amanha, ""))

    with tempfile.TemporaryDirectory(prefix="caixa-teste-") as pasta:
        base = Path(pasta)
        (base / "nucleo").mkdir()
        vazia = base / "sem-configuracao"
        vazia.mkdir()
        corpo = base / "corpo.md"
        registro = base / "registro.txt"
        comentarios = base / "comentarios.md"
        falso_gh = base / "falso_gh.py"
        falso_gh.write_text(FALSO_GH, encoding="utf-8")

        def com_configuracao(dado):
            (base / ARQUIVO_DO_EXECUTOR).write_text(
                json.dumps(dado) if isinstance(dado, dict) else dado,
                encoding="utf-8")

        def do_zero(texto=molde):
            corpo.write_text(texto, encoding="utf-8")
            registro.write_text("", encoding="utf-8")
            comentarios.write_text("", encoding="utf-8")

        def chamadas(qual):
            return registro.read_text(encoding="utf-8").count(qual)

        def no_quadro(identidade):
            return any(um["id"] == identidade for um in _achados_do_corpo(
                corpo.read_text(encoding="utf-8")))

        guardado = dict(os.environ)
        os.environ[gh.VARIAVEL_DO_GH] = " ".join(
            shlex.quote(str(parte)) for parte in (sys.executable, falso_gh))
        os.environ["CAIXA_TESTE_CORPO"] = str(corpo)
        os.environ["CAIXA_TESTE_LOG"] = str(registro)
        os.environ["CAIXA_TESTE_COMENTARIOS"] = str(comentarios)
        try:
            declarada = {"caixas": {"defeitos": 7, "melhorias": 8},
                         "issues": {"repositorio": "exemplo/exemplo"}}
            quadro = {"caixas": {"defeitos": 7, "melhorias": 7},
                      "issues": {"repositorio": "exemplo/exemplo"}}

            com_configuracao({"issues": {"repositorio": "exemplo/exemplo"}})
            do_zero()
            codigo, recado = rodar(DEFEITO, "sem-caixas", "o que for", hoje,
                                   cwd=str(base))
            caso("sem `caixas` declarada, o instrumento sai diferente de zero",
                 codigo != 0)
            caso("a recusa nomeia o campo que falta",
                 CAMPO_DAS_CAIXAS in recado)
            caso("e recusando, não chama o GitHub nenhuma vez",
                 chamadas("issue") == 0)

            com_configuracao(quadro)
            do_zero()
            codigo, recado = rodar(DEFEITO, "linha-do-cliente", "o que for",
                                   hoje, cwd=str(base), quadro="99")
            caso("com --quadro, a linha vai para a issue apontada, não para "
                 "a declarada na configuração",
                 codigo == 0 and chamadas("99") >= 1
                 and chamadas("issue 7") == 0)
            caso("e o repositório continua vindo da configuração — o quadro "
                 "do cliente nasce no mesmo repositório",
                 chamadas("exemplo/exemplo") >= 1)
            codigo, recado = rodar(DEFEITO, "quadro-torto", "o que for",
                                   hoje, cwd=str(base), quadro="nao-e-numero")
            caso("--quadro que não é número de issue é erro de uso",
                 codigo == 2)
            codigo, _ = rodar(DEFEITO, "quadro-exotico", "o que for", hoje,
                              cwd=str(base), quadro="\u00b2")
            caso("dígito que não é ASCII é recusa declarada, não traceback: "
                 "isdigit() aceita o expoente e int() não",
                 codigo == 2)
            caso("e recusando, não chama o GitHub", chamadas("nao-e-numero") == 0)
            do_zero()

            com_configuracao({"caixas": {"melhorias": 8},
                              "issues": {"repositorio": "exemplo/exemplo"}})
            codigo, recado = rodar(DEFEITO, "so-a-outra", "o que for", hoje,
                                   cwd=str(base))
            caso("caixa declarada só para o outro tipo também é recusa",
                 codigo != 0 and "defeitos" in recado)

            com_configuracao({"caixas": {"defeitos": "${NUMERO}"},
                              "issues": {"repositorio": "exemplo/exemplo"}})
            codigo, _ = rodar(DEFEITO, "por-preencher", "o que for", hoje,
                              cwd=str(base))
            caso("número ainda por preencher não é número de caixa",
                 codigo != 0)

            com_configuracao({"caixas": {"defeitos": 7}})
            codigo, recado = rodar(DEFEITO, "sem-repositorio", "o que for",
                                   hoje, cwd=str(base))
            caso("sem o repositório das issues, recusa e diz qual campo",
                 codigo != 0 and CAMPO_DO_REPOSITORIO in recado)

            codigo, recado = rodar(DEFEITO, "sem-arquivo", "o que for", hoje,
                                   cwd=str(vazia))
            caso("sem o arquivo de configuração, recusa nomeando o arquivo",
                 codigo != 0 and ARQUIVO_DO_EXECUTOR in recado)

            com_configuracao("isto não é json")
            codigo, _ = rodar(DEFEITO, "json-quebrado", "o que for", hoje,
                              cwd=str(base))
            caso("configuração ilegível é recusa, não é escrita às cegas",
                 codigo != 0 and chamadas("issue") == 0)

            com_configuracao(declarada)
            codigo, _ = rodar("bilhete", "tipo-que-nao-existe", "o que for",
                              hoje, cwd=str(base))
            caso("tipo que não existe é recusado antes de tudo", codigo != 0)

            do_zero()
            codigo, recado = rodar(DEFEITO, "prova-nao-reproduz",
                                   "a prova declarada dá outra coisa", hoje,
                                   cwd=str(base))
            caso("com a caixa declarada, o achado vira linha no corpo",
                 codigo == 0
                 and len(_achados_do_corpo(corpo.read_text(encoding="utf-8")))
                 == 1)
            codigo, recado = rodar(DEFEITO, "prova-nao-reproduz",
                                   "a prova declarada dá outra coisa", hoje,
                                   cwd=str(base))
            caso("posto de novo, a caixa continua com UMA linha",
                 codigo == 0
                 and len(_achados_do_corpo(corpo.read_text(encoding="utf-8")))
                 == 1)
            caso("e a segunda vez nem regrava o corpo", chamadas("edit") == 1)

            codigo, recado = rodar(DEFEITO, "prova-nao-reproduz",
                                   "agora dá outra coisa ainda", amanha,
                                   cwd=str(base))
            lidos = _achados_do_corpo(corpo.read_text(encoding="utf-8"))
            caso("achado que mudou atualiza a linha na caixa de verdade",
                 codigo == 0 and len(lidos) == 1
                 and lidos[0]["quando"] == amanha)

            com_configuracao(quadro)
            do_zero()
            rodar(DEFEITO, "prova-nao-reproduz", "a prova dá outra coisa",
                  hoje, cwd=str(base))
            rodar(MELHORIA, "caixa-aprende-a-podar", "a poda entra", hoje,
                  cwd=str(base))
            lidos = _achados_do_corpo(corpo.read_text(encoding="utf-8"))
            caso("com as duas caixas na mesma issue, os dois tipos entram no "
                 "mesmo quadro, cada um com sua etiqueta",
                 [(um["id"], um["tipo"]) for um in lidos]
                 == [("prova-nao-reproduz", DEFEITO),
                     ("caixa-aprende-a-podar", MELHORIA)])

            codigo, recado = podar("caixa-aprende-a-podar", amanha,
                                   cwd=str(base), motivo="entregue na #7")
            escrito = comentarios.read_text(encoding="utf-8")
            caso("a poda tira a linha do quadro sem ninguém dizer o tipo",
                 codigo == 0 and not no_quadro("caixa-aprende-a-podar"))
            caso("e a poda não leva junto a linha da vizinha",
                 no_quadro("prova-nao-reproduz"))
            caso("o fechamento fica em comentário na caixa, com a linha "
                 "inteira e o motivo",
                 chamadas("comment") == 1
                 and "caixa-aprende-a-podar" in escrito
                 and "a poda entra" in escrito
                 and "entregue na #7" in escrito)

            codigo, recado = podar("nunca-esteve-no-quadro", amanha,
                                   cwd=str(base))
            caso("podar linha que não está no quadro é recusa, sem escrita",
                 codigo != 0 and chamadas("comment") == 1
                 and chamadas("edit") == 3)

            do_zero()
            rodar(MELHORIA, "caixa-aprende-a-podar", "a poda entra", hoje,
                  cwd=str(base))
            codigo, recado = podar("caixa-aprende-a-podar", amanha,
                                   cwd=str(base), ensaio=True)
            caso("o ensaio da poda mostra o que sairia e não toca na caixa",
                 codigo == 0 and "caixa-aprende-a-podar" in recado
                 and chamadas("comment") == 0 and chamadas("edit") == 1
                 and no_quadro("caixa-aprende-a-podar"))

            os.environ["CAIXA_TESTE_RECUSA_COMENTARIO"] = "1"
            codigo, recado = podar("caixa-aprende-a-podar", amanha,
                                   cwd=str(base))
            del os.environ["CAIXA_TESTE_RECUSA_COMENTARIO"]
            caso("comentário que não subiu impede a poda — a linha fica",
                 codigo != 0 and chamadas("edit") == 1
                 and no_quadro("caixa-aprende-a-podar"))

            do_zero()
            relatorio = "# A rodada\n\nO que ela mediu.\n"
            codigo, recado = relatar(relatorio, cwd=str(base), ensaio=True)
            caso("o ensaio do relatório mostra o corpo e não escreve na "
                 "caixa",
                 codigo == 0 and relatorio in recado
                 and chamadas("comment") == 0 and chamadas("edit") == 0)

            codigo, recado = relatar(relatorio, cwd=str(base))
            caso("o relatório entra como comentário novo, nunca como linha "
                 "no quadro",
                 codigo == 0 and chamadas("comment") == 1
                 and chamadas("edit") == 0
                 and relatorio in comentarios.read_text(encoding="utf-8")
                 and not _achados_do_corpo(
                     corpo.read_text(encoding="utf-8")))

            codigo, recado = relatar(relatorio, cwd=str(base))
            caso("relatar de novo abre OUTRO comentário — cada rodada tem o "
                 "seu",
                 codigo == 0 and chamadas("comment") == 2)

            for vazio in ("", "   \n\t "):
                codigo, recado = relatar(vazio, cwd=str(base))
                caso(f"corpo vazio ({vazio!r}) é recusado com recado, sem "
                     "chamar o GitHub",
                     codigo == 2 and recado == RECUSA_SEM_CORPO
                     and chamadas("comment") == 2)

            os.environ["CAIXA_TESTE_RECUSA_COMENTARIO"] = "1"
            codigo, recado = relatar(relatorio, cwd=str(base))
            del os.environ["CAIXA_TESTE_RECUSA_COMENTARIO"]
            caso("comentário que não subiu vira erro confessado, nunca "
                 "relatório dado por escrito",
                 codigo == 2 and recado.startswith(
                     FALHA_AO_RELATAR.split("{motivo}")[0].format(issue=7)))

            com_configuracao({"issues": {"repositorio": "exemplo/exemplo"}})
            codigo, recado = relatar(relatorio, cwd=str(base))
            caso("sem `caixas` declarada, relatar recusa e não comenta",
                 codigo == 2 and CAMPO_DAS_CAIXAS in recado)
            com_configuracao(quadro)
            do_zero()
            rodar(MELHORIA, "caixa-aprende-a-podar", "a poda entra", hoje,
                  cwd=str(base))

            os.environ["CAIXA_TESTE_ENGOLE"] = "1"
            codigo, recado = podar("caixa-aprende-a-podar", amanha,
                                   cwd=str(base))
            del os.environ["CAIXA_TESTE_ENGOLE"]
            caso("poda que se perdeu é confessada, não é dada por feita",
                 codigo != 0 and "caixa-aprende-a-podar" in recado
                 and no_quadro("caixa-aprende-a-podar"))

            do_zero(molde.replace(MARCA_FECHA, velha + "\n" + MARCA_FECHA))
            codigo, recado = rodar(DEFEITO, "com-linha-velha", "o que for",
                                   hoje, cwd=str(base))
            caso("linha que o instrumento não sabe ler trava a escrita, em "
                 "vez de sumir na reescrita do bloco",
                 codigo != 0 and chamadas("edit") == 0
                 and "não sei ler" in recado
                 and velha in corpo.read_text(encoding="utf-8"))
            codigo, recado = podar("linha-velha", amanha, cwd=str(base))
            caso("e trava a poda também, sem comentar nada",
                 codigo != 0 and chamadas("edit") == 0
                 and chamadas("comment") == 0 and "não sei ler" in recado)

            com_configuracao(declarada)
            do_zero("prosa de gente, sem bloco marcado nenhum\n")
            codigo, recado = rodar(DEFEITO, "sem-o-bloco", "o que for", hoje,
                                   cwd=str(base))
            caso("caixa sem o bloco marcado não é escrita",
                 codigo != 0 and chamadas("edit") == 0)

            do_zero()
            codigo, recado = rodar(DEFEITO, "no-ensaio", "o que for", hoje,
                                   cwd=str(base), ensaio=True)
            caso("o ensaio mostra o bloco e não escreve",
                 codigo == 0 and "no-ensaio" in recado
                 and chamadas("edit") == 0)

            do_zero()
            os.environ["CAIXA_TESTE_ENGOLE"] = "1"
            codigo, recado = rodar(DEFEITO, "escrita-perdida", "o que for",
                                   hoje, cwd=str(base))
            caso("escrita que se perdeu é confessada, não é dada por feita",
                 codigo != 0 and "escrita-perdida" in recado)
        finally:
            os.environ.clear()
            os.environ.update(guardado)

    este_modulo = sys.modules[__name__]
    de_verdade = (este_modulo.ler_corpo, este_modulo.gravar_corpo,
                  este_modulo.comentar)
    gravado = {"corpo": ""}
    endereco = {"issue": 40, "repositorio": "exemplo/exemplo", "conta": ""}
    de_a = achado(MELHORIA, "linha-da-sessao-a", "posta pela sessão A", hoje)
    de_b = achado(DEFEITO, "linha-da-sessao-b", "posta pela sessão B", hoje)

    def com_a_leitura_atrasada(atrasado, que_some=""):
        leituras = {"quantas": 0}

        def ler(_endereco):
            leituras["quantas"] += 1
            return (atrasado if leituras["quantas"] == 1
                    else gravado["corpo"]), ""

        def gravar(_endereco, escrito):
            gravado["corpo"] = (corpo_sem(escrito, que_some) if que_some
                                else escrito)
            return ""

        def nao_comenta(*_):
            return ""

        (este_modulo.ler_corpo, este_modulo.gravar_corpo,
         este_modulo.comentar) = ler, gravar, nao_comenta

    def identidades_gravadas():
        return sorted(um["id"] for um in _achados_do_corpo(gravado["corpo"]))

    try:
        gravado["corpo"] = corpo_com(molde, de_b)
        com_a_leitura_atrasada(molde)
        codigo, recado = por_na_caixa(endereco, de_a)
        caso("sessão que leu o quadro atrasada põe a linha dela sem apagar "
             "a linha da outra sessão",
             codigo == 0 and identidades_gravadas()
             == ["linha-da-sessao-a", "linha-da-sessao-b"])

        gravado["corpo"] = corpo_com(molde, de_b)
        com_a_leitura_atrasada(gravado["corpo"],
                               que_some="linha-da-sessao-b")
        codigo, recado = por_na_caixa(endereco, de_a)
        caso("linha de outra sessão que some entre a gravação e a releitura "
             "sai com código 2, nunca 0",
             codigo == 2 and "linha-da-sessao-b" in recado)

        gravado["corpo"] = corpo_com(corpo_com(molde, de_a), de_b)
        com_a_leitura_atrasada(corpo_com(molde, de_a))
        onde, atrasado, _ = achar_a_linha([endereco], "linha-da-sessao-a")
        codigo, recado = podar_da_caixa(onde, atrasado, "linha-da-sessao-a",
                                        "o registro do fechamento")
        caso("a poda que leu o quadro atrasada tira a linha pedida sem "
             "apagar a linha da outra sessão",
             codigo == 0 and identidades_gravadas()
             == ["linha-da-sessao-b"])
    finally:
        (este_modulo.ler_corpo, este_modulo.gravar_corpo,
         este_modulo.comentar) = de_verdade

    total = len(rodados)
    if falhas:
        for falha in falhas:
            print(f"  [{falha}]")
        print(f"FALHOU: {len(falhas)} de {total} casos")
        return 1
    print(f"OK: {total} casos — identidade, etiqueta do tipo, bloco marcado, "
          "recusa, escrita e poda")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=DESCRICAO_DA_CLI)
    ap.add_argument("acao", choices=TIPOS + (PODA, RELATO), help=AJUDA_ACAO)
    ap.add_argument("--id", default="", dest="identidade", help=AJUDA_ID)
    ap.add_argument("--assunto", default="", help=AJUDA_ASSUNTO)
    ap.add_argument("--corpo", default="", help=AJUDA_CORPO)
    ap.add_argument("--motivo", default="", help=AJUDA_MOTIVO)
    ap.add_argument("--quando", default=date.today().isoformat(),
                    help=AJUDA_QUANDO)
    ap.add_argument("--cwd", default="", help=AJUDA_CWD)
    ap.add_argument("--ensaio", action="store_true", help=AJUDA_ENSAIO)
    ap.add_argument("--quadro", default="", help=AJUDA_QUADRO)
    a = ap.parse_args()
    if a.acao == RELATO:
        codigo, recado = relatar(a.corpo, a.cwd, a.ensaio, a.quadro)
    elif a.acao == PODA:
        codigo, recado = podar(a.identidade, a.quando, a.cwd, a.motivo,
                               a.ensaio, a.quadro)
    else:
        codigo, recado = rodar(a.acao, a.identidade, a.assunto, a.quando,
                               a.cwd, a.ensaio, a.quadro, a.corpo)
    print(recado, file=sys.stderr if codigo else sys.stdout)
    return codigo


if __name__ == "__main__":
    sys.exit(testar() if BANDEIRA_DE_TESTE in sys.argv else main())
