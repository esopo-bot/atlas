import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone

DESCRICAO = (
    "dispara uma consulta do CloudWatch Logs Insights, espera ela terminar e "
    "devolve o resultado já em colunas. Tudo por argumento: o grupo de log, a "
    "região, a consulta e a janela. Nenhum valor nasce embutido — o que é de "
    "um cliente mora no workspace dele, nunca aqui.")

BANDEIRA_DE_TESTE = "--testar"
AWS = shlex.split(os.environ.get("INSIGHTS_AWS", "aws"))
CAMPO_INTERNO = "@ptr"
INTERVALO_DA_ESPERA_S = 1.0
TETO_DA_ESPERA_S = 60
STATUS_QUE_SEGUEM = ("Scheduled", "Running")
STATUS_COMPLETO = "Complete"

ERRO_JANELA = ("janela inválida em {rotulo}: {valor!r} — use ISO 8601 "
               "(2026-09-01T08:00:00Z) ou epoch em segundos")
ERRO_INICIO_DEPOIS_DO_FIM = "a janela começa depois de terminar: {desde} > {ate}"
ERRO_AWS_MUDO = "o aws não respondeu: {}"
ERRO_SEM_QUERY_ID = "o start-query não devolveu queryId: {}"
ERRO_CONSULTA_FALHOU = "a consulta terminou em {status}"
ERRO_ESPERA_ESTOUROU = ("a consulta não terminou em {teto}s — ainda {status}; "
                        "aumente --teto se a janela for larga")
RECADO_SEM_LINHA = "a consulta não devolveu nenhuma linha"


def instante_em_epoch(valor: str, rotulo: str) -> int:
    if valor.isdigit():
        return int(valor)
    try:
        texto = valor.replace("Z", "+00:00")
        return int(datetime.fromisoformat(texto)
                   .replace(tzinfo=timezone.utc if "+" not in texto
                            and "T" in texto else None)
                   .timestamp())
    except ValueError:
        raise SystemExit(ERRO_JANELA.format(rotulo=rotulo, valor=valor))


def linhas_do_resultado(resultado: dict) -> list:
    linhas = []
    for linha in resultado.get("results") or []:
        colunas = {par.get("field"): par.get("value") for par in linha
                   if par.get("field") and par.get("field") != CAMPO_INTERNO}
        if colunas:
            linhas.append(colunas)
    return linhas


def em_colunas(linhas: list) -> str:
    if not linhas:
        return RECADO_SEM_LINHA
    cabecalho = []
    for linha in linhas:
        for chave in linha:
            if chave not in cabecalho:
                cabecalho.append(chave)
    largura = {c: max(len(c), *(len(str(l.get(c, ""))) for l in linhas))
               for c in cabecalho}
    def formata(valores):
        return "  ".join(str(valores.get(c, "")).ljust(largura[c])
                         for c in cabecalho)
    corpo = [formata(dict(zip(cabecalho, cabecalho)))]
    corpo += [formata(linha) for linha in linhas]
    return "\n".join(corpo)


def _aws_json(argumentos: list, regiao: str) -> dict:
    try:
        feito = subprocess.run(AWS + argumentos + ["--region", regiao],
                               capture_output=True, text=True)
    except OSError as erro:
        raise SystemExit(ERRO_AWS_MUDO.format(erro))
    if feito.returncode != 0:
        raise SystemExit(ERRO_AWS_MUDO.format(
            (feito.stderr or feito.stdout).strip()))
    return json.loads(feito.stdout or "{}")


def disparar(grupo, regiao, consulta, desde, ate, teto) -> dict:
    aberto = _aws_json(
        ["logs", "start-query", "--log-group-name", grupo,
         "--start-time", str(desde), "--end-time", str(ate),
         "--query-string", consulta], regiao)
    query_id = aberto.get("queryId")
    if not query_id:
        raise SystemExit(ERRO_SEM_QUERY_ID.format(aberto))
    limite = time.monotonic() + teto
    while True:
        resultado = _aws_json(
            ["logs", "get-query-results", "--query-id", query_id], regiao)
        status = resultado.get("status")
        if status == STATUS_COMPLETO:
            return resultado
        if status not in STATUS_QUE_SEGUEM:
            raise SystemExit(ERRO_CONSULTA_FALHOU.format(status=status))
        if time.monotonic() >= limite:
            raise SystemExit(ERRO_ESPERA_ESTOUROU.format(teto=teto,
                                                         status=status))
        time.sleep(INTERVALO_DA_ESPERA_S)


def main(argv) -> int:
    ap = argparse.ArgumentParser(description=DESCRICAO)
    ap.add_argument("--grupo", required=True,
                    help="o log group inteiro — /aws/lambda/... etc")
    ap.add_argument("--regiao", required=True)
    ap.add_argument("--consulta", required=True,
                    help="a query string do Insights")
    ap.add_argument("--desde", required=True,
                    help="início da janela: ISO 8601 ou epoch em segundos")
    ap.add_argument("--ate", required=True, help="fim da janela")
    ap.add_argument("--teto", type=int, default=TETO_DA_ESPERA_S,
                    help="segundos de espera antes de desistir")
    ap.add_argument("--json", action="store_true",
                    help="devolve as linhas como JSON, não colunas")
    a = ap.parse_args(argv)
    desde = instante_em_epoch(a.desde, "--desde")
    ate = instante_em_epoch(a.ate, "--ate")
    if desde > ate:
        raise SystemExit(ERRO_INICIO_DEPOIS_DO_FIM.format(desde=a.desde,
                                                          ate=a.ate))
    linhas = linhas_do_resultado(
        disparar(a.grupo, a.regiao, a.consulta, desde, ate, a.teto))
    print(json.dumps(linhas, ensure_ascii=False, indent=2) if a.json
          else em_colunas(linhas))
    return 0


def testar() -> int:
    falhas = []

    def caso(rotulo, condicao):
        if not condicao:
            falhas.append(rotulo)

    fields = {"status": STATUS_COMPLETO, "results": [
        [{"field": "@timestamp", "value": "2026-09-01 08:00:00.000"},
         {"field": "@message", "value": "erro na rota"},
         {"field": "@ptr", "value": "Cg..."}]]}
    stats = {"status": STATUS_COMPLETO, "results": [
        [{"field": "rota", "value": "/x"}, {"field": "quantas", "value": "42"}],
        [{"field": "rota", "value": "/y"}, {"field": "quantas", "value": "9"}]]}

    achado = linhas_do_resultado(fields)
    caso("fields vira coluna e o campo interno @ptr fica de fora",
         achado == [{"@timestamp": "2026-09-01 08:00:00.000",
                     "@message": "erro na rota"}])
    achado_stats = linhas_do_resultado(stats)
    caso("stats vira coluna sem assumir nome de campo — o formato que voltava "
         "vazio calado",
         achado_stats == [{"rota": "/x", "quantas": "42"},
                          {"rota": "/y", "quantas": "9"}])
    caso("resultado vazio é uma linha só de recado, não erro",
         linhas_do_resultado({"results": []}) == []
         and em_colunas([]) == RECADO_SEM_LINHA)
    saida = em_colunas(achado_stats)
    caso("as colunas trazem o cabeçalho e uma linha por resultado",
         saida.splitlines()[0].split() == ["rota", "quantas"]
         and len(saida.splitlines()) == 3)
    caso("epoch em segundos atravessa como número",
         instante_em_epoch("1756713600", "--desde") == 1756713600)
    caso("ISO com Z vira epoch",
         instante_em_epoch("2026-09-01T00:00:00Z", "--desde") > 0)
    try:
        instante_em_epoch("ontem de manhã", "--desde")
        caso("janela inválida é recusada na fronteira", False)
    except SystemExit:
        caso("janela inválida é recusada na fronteira", True)

    if falhas:
        print("FALHOU: " + "; ".join(falhas))
        return 1
    print(f"OK: {7} casos — normalização stats×fields, colunas e janela")
    return 0


if __name__ == "__main__":
    sys.exit(testar() if BANDEIRA_DE_TESTE in sys.argv[1:2]
             else main(sys.argv[1:]))
