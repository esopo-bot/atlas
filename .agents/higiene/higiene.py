import argparse
import json
import re
import subprocess
import sys

DESCRICAO_DA_CLI = ("varre o rastreador pelos termos de um assunto e diz o "
                    "que ficou espalhado, o que envelheceu e o que não "
                    "aponta para a issue que consolidou o trabalho")

FERRAMENTA = "gh"
CAMPOS = "number,title,body,state,url"
TETO_DA_VARREDURA = 200
TEMPO_DA_REDE_S = 120

PALAVRAS_QUE_ENVELHECEM = (
    "em execução", "em execucao", "em andamento", "está aberta",
    "esta aberta", "continua aberta", "segue aberta", "ainda aberta",
    "em curso", "vai fechar", "falta fechar", "aguarda mescla",
    "aguardando mescla", "pendente de mescla")
REFERENCIA = re.compile(r"#(\d{1,6})\b")

TITULO = "A HIGIENE DO FIM DO TRABALHO — assunto {!r}"
SEM_TERMO = "  nenhum termo casou em issue aberta nenhuma"
CABECA_ESPALHADO = "  ESPALHADO — fala do assunto e não aponta para #{}:"
CABECA_ENVELHECIDO = "  ENVELHECIDO — diz que algo segue aberto, e não segue:"
CABECA_VIZINHA = "  VIZINHAS — falam do assunto e apontam para #{} (ok):"
LINHA = "    #{:<6} {}"
LINHA_COM_MOTIVO = "    #{:<6} {} — {}"
PLACAR = "  {} issue(s) varrida(s), {} com o assunto, {} a arrumar"
NADA_A_ARRUMAR = "  nada a arrumar"


def issues_abertas(repositorio):
    corrida = subprocess.run(
        [FERRAMENTA, "issue", "list", "--repo", repositorio, "--state", "open",
         "--limit", str(TETO_DA_VARREDURA), "--json", CAMPOS],
        capture_output=True, text=True, timeout=TEMPO_DA_REDE_S)
    if corrida.returncode != 0:
        return None
    return json.loads(corrida.stdout or "[]")


def estado_de_cada_referencia(repositorio, numeros):
    estados = {}
    for numero in sorted(numeros):
        corrida = subprocess.run(
            [FERRAMENTA, "issue", "view", str(numero), "--repo", repositorio,
             "--json", "state,title"],
            capture_output=True, text=True, timeout=TEMPO_DA_REDE_S)
        if corrida.returncode != 0:
            continue
        estados[numero] = json.loads(corrida.stdout)["state"]
    return estados


def fala_do_assunto(issue, termos):
    texto = f"{issue.get('title', '')}\n{issue.get('body') or ''}".lower()
    return [t for t in termos if t.lower() in texto]


def aponta_para(issue, consolidada):
    texto = f"{issue.get('title', '')}\n{issue.get('body') or ''}"
    return str(consolidada) in REFERENCIA.findall(texto)


def frases_que_envelheceram(issue, estados):
    texto = (issue.get("body") or "")
    baixo = texto.lower()
    achados = []
    for numero in {int(n) for n in REFERENCIA.findall(texto)}:
        if estados.get(numero) != "CLOSED":
            continue
        for palavra in PALAVRAS_QUE_ENVELHECEM:
            if palavra in baixo:
                achados.append(f"cita #{numero}, que já fechou, e diz "
                               f"{palavra!r}")
                break
    return achados


def varrer(issues, termos, consolidada, estados):
    espalhadas, envelhecidas, vizinhas = [], [], []
    for issue in issues:
        if issue.get("number") == consolidada:
            continue
        casou = fala_do_assunto(issue, termos)
        if not casou:
            continue
        if aponta_para(issue, consolidada):
            vizinhas.append((issue, casou))
        else:
            espalhadas.append((issue, casou))
        for motivo in frases_que_envelheceram(issue, estados):
            envelhecidas.append((issue, motivo))
    return espalhadas, envelhecidas, vizinhas


def numeros_citados(issues):
    citados = set()
    for issue in issues:
        citados.update(int(n) for n in REFERENCIA.findall(issue.get("body") or ""))
    return citados


def relatar(issues, termos, consolidada, estados):
    print(TITULO.format(", ".join(termos)))
    espalhadas, envelhecidas, vizinhas = varrer(issues, termos, consolidada,
                                                estados)
    if not (espalhadas or vizinhas):
        print(SEM_TERMO)
        return 0
    if espalhadas:
        print(CABECA_ESPALHADO.format(consolidada))
        for issue, casou in espalhadas:
            print(LINHA_COM_MOTIVO.format(issue["number"],
                                          issue["title"][:52],
                                          ", ".join(casou)))
    if envelhecidas:
        print(CABECA_ENVELHECIDO)
        for issue, motivo in envelhecidas:
            print(LINHA_COM_MOTIVO.format(issue["number"],
                                          issue["title"][:52], motivo))
    if vizinhas:
        print(CABECA_VIZINHA.format(consolidada))
        for issue, _ in vizinhas:
            print(LINHA.format(issue["number"], issue["title"][:60]))
    a_arrumar = len(espalhadas) + len(envelhecidas)
    print(PLACAR.format(len(issues), len(espalhadas) + len(vizinhas),
                        a_arrumar))
    if not a_arrumar:
        print(NADA_A_ARRUMAR)
    return 1 if a_arrumar else 0


ISSUES_DE_TESTE = [
    {"number": 1, "title": "farol - troca do login", "state": "OPEN",
     "body": "o login novo depende da sessão compartilhada. ver #9"},
    {"number": 2, "title": "outro assunto", "state": "OPEN",
     "body": "nada a ver com nada"},
    {"number": 3, "title": "farol - resíduo do login", "state": "OPEN",
     "body": "sobrou isto do login antigo, sem apontar para lugar nenhum"},
    {"number": 4, "title": "farol - vizinha do login", "state": "OPEN",
     "body": "isto é do login e está consolidado em #9"},
    {"number": 5, "title": "farol - fala de fechada", "state": "OPEN",
     "body": "o login sai por #99, que está em execução"},
    {"number": 9, "title": "a consolidada do login", "state": "OPEN",
     "body": "aqui mora o assunto login"},
]
ESTADOS_DE_TESTE = {9: "OPEN", 99: "CLOSED"}
BANDEIRA_DE_TESTE = "--testar"
FALHA = "  FALHA {}: esperado {!r}, veio {!r}"
PLACAR_DO_TESTE = "higiene: {} de {} casos"


def testar():
    quebrou = 0
    espalhadas, envelhecidas, vizinhas = varrer(
        ISSUES_DE_TESTE, ["login"], 9, ESTADOS_DE_TESTE)
    casos = (
        ("espalhadas", sorted(i["number"] for i, _ in espalhadas), [3, 5]),
        ("vizinhas", sorted(i["number"] for i, _ in vizinhas), [1, 4]),
        ("envelhecidas", sorted(i["number"] for i, _ in envelhecidas), [5]),
        ("a consolidada nao se acusa", 9 in [i["number"] for i, _ in espalhadas],
         False),
        ("quem nao fala do assunto fica fora",
         2 in [i["number"] for i, _ in espalhadas + vizinhas], False),
        ("termo casa no titulo tambem",
         bool(fala_do_assunto({"title": "do LOGIN", "body": ""}, ["login"])),
         True),
        ("referencia so conta numero de verdade",
         aponta_para({"title": "", "body": "ver #91"}, 9), False),
        ("issue fechada sem palavra que envelhece nao acusa",
         frases_que_envelheceram({"body": "ver #99"}, ESTADOS_DE_TESTE), []),
        ("issue aberta com palavra que envelhece nao acusa",
         frases_que_envelheceram({"body": "#9 em execução"}, ESTADOS_DE_TESTE),
         []),
        ("numeros citados sao colhidos",
         sorted(numeros_citados(ISSUES_DE_TESTE)), [9, 99]),
    )
    for nome, veio, esperado in casos:
        if veio != esperado:
            quebrou += 1
            print(FALHA.format(nome, esperado, veio))
    print(PLACAR_DO_TESTE.format(len(casos) - quebrou, len(casos)))
    return 1 if quebrou else 0


def main(argv=None):
    p = argparse.ArgumentParser(description=DESCRICAO_DA_CLI)
    p.add_argument("--repositorio", help="dono/nome do repositório")
    p.add_argument("--consolidada", type=int,
                   help="a issue que consolidou o trabalho")
    p.add_argument("--termo", action="append", default=[],
                   help="termo do assunto; repita para vários")
    p.add_argument(BANDEIRA_DE_TESTE, action="store_true")
    a = p.parse_args(argv)
    if a.testar:
        return testar()
    if not (a.repositorio and a.consolidada and a.termo):
        p.error("--repositorio, --consolidada e ao menos um --termo")
    issues = issues_abertas(a.repositorio)
    if issues is None:
        print("  o rastreador não respondeu")
        return 1
    estados = estado_de_cada_referencia(a.repositorio, numeros_citados(issues))
    return relatar(issues, a.termo, a.consolidada, estados)


if __name__ == "__main__":
    sys.exit(main())
