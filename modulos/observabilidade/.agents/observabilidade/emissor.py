import argparse
import importlib.util
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

PADRAO_DO_RECIBO = re.compile(r"(\d{2})-(.+)-c(\d+)\.json\Z")
CAMPOS_DE_GASTO = ("turnos", "custo", "duracao", "assinatura")

VARIAVEL_DA_CHAVE = "DD_API_KEY"
VARIAVEL_DO_SITE = "DD_SITE"
SITE_PADRAO = "datadoghq.com"
APLICACAO_PADRAO = "atlas-execucoes"
VARIAVEL_DA_APLICACAO = "DD_LLMOBS_ML_APP"

AMBIENTE_DA_EMISSAO = {
    "DD_LLMOBS_ENABLED": "1",
    "DD_LLMOBS_AGENTLESS_ENABLED": "1",
    "DD_TRACE_ENABLED": "false",
    "DD_TRACE_GIT_METADATA_ENABLED": "false",
}

METRICA_DOS_RECIBOS = "atlas.recibo.total"
METRICA_DA_COBERTURA = "atlas.recibo.cobertura"
METRICA_DO_CUSTO = "atlas.custo.usd"
METRICA_DOS_TOKENS = "atlas.custo.tokens"
PASSO_DA_EXECUCAO_INTEIRA = "execucao-inteira"
MARCA_DE_CACHE_NO_MODELO = "["
EXTENSAO_DO_LOG = ".log"
MOTOR_NAO_DECLARADO = "nao-declarado"
VEREDITO_PIOR_PRIMEIRO = ("para", "pergunta", "segue")
TIPO_CONTADOR = 1
TIPO_MEDIDOR = 3

METRICA_DO_CREDITO = "atlas.motor.credito.usado"
METRICA_DA_FONTE_DO_CREDITO = "atlas.motor.credito.medido"
METRICA_DOS_TOKENS_DO_MOTOR = "atlas.motor.tokens"
METRICA_DAS_CHAMADAS_DO_MOTOR = "atlas.motor.chamadas"
INSTRUMENTO_DOS_MOTORES = Path(".agents") / "motores" / "motores.py"
ARQUIVO_DO_CADASTRO = Path("nucleo") / "executor.json"
MOTOR_COM_REGISTRO = "codex"
MOLDE_DO_ROLLOUT = "**/rollout-*.jsonl"
JANELA_QUE_A_API_ACEITA_S = 3600
FOLGA_DA_JANELA_S = 120

TEMPO_DA_REDE_S = 20
PRAZO_DURO_DA_EMISSAO_S = 60
PRAZO_ESTOURADO = ("a emissão passou de {}s e o processo foi encerrado sem "
                   "esperar a biblioteca")
SEM_MEDICAO = ("não medido: {}. A emissão é opcional e nunca derruba quem a "
               "chamou.")
SEM_CHAVE = "a variável " + VARIAVEL_DA_CHAVE + " não está no ambiente"
SEM_BIBLIOTECA = "a biblioteca ddtrace não está instalada"
SEM_RECIBO = "a pasta {} não tem recibo de etapa"
EMITIDO = "emitido: {etapas} etapa(s) de {trabalho}, {pontos} ponto(s) de métrica"
FALHA_DA_METRICA = "a métrica não subiu: {}"
SEM_MOTORES = "o instrumento dos motores não está em {}"
SEM_CADASTRO = "nenhum motor cadastrado em {}"
EMITIDO_DOS_MOTORES = ("emitido: {pontos} ponto(s) de crédito e gasto dos "
                       "motores; {fora} registro(s) do Codex mais velhos que "
                       "a janela que a API aceita ficaram de fora")
OK_DO_TESTE = "OK: {} casos — emissor de observabilidade"
FALHA_DO_TESTE = "FALHOU: {} de {} casos"
LINHA_DE_FALHA = "FALHOU: {}"

SILENCIO = 0
QUEBROU = 1


def chave_de_api() -> str:
    return os.environ.get(VARIAVEL_DA_CHAVE, "").strip()


def aplicacao() -> str:
    return os.environ.get(VARIAVEL_DA_APLICACAO, "").strip() or APLICACAO_PADRAO


def instante_do_marco(quando):
    try:
        return datetime.fromisoformat(quando).timestamp()
    except (TypeError, ValueError):
        return None


def sem_a_marca_de_cache(modelo: str) -> str:
    return modelo.split(MARCA_DE_CACHE_NO_MODELO, 1)[0].strip()


def motor_do_modelo(modelo: str) -> str:
    return sem_a_marca_de_cache(modelo).split("-", 1)[0].lower() or "?"


def modelos_do_log(recibo: Path) -> dict:
    log = recibo.with_suffix(EXTENSAO_DO_LOG)
    try:
        bruto = log.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    achados = {}
    for linha in bruto.splitlines():
        try:
            dado = json.loads(linha)
        except ValueError:
            continue
        uso = dado.get("modelUsage") if isinstance(dado, dict) else None
        if isinstance(uso, dict):
            for nome, medida in uso.items():
                if isinstance(medida, dict):
                    achados[sem_a_marca_de_cache(nome)] = medida
    return achados


def recibos_da_execucao(pasta: Path) -> list:
    colhidos = []
    for arquivo in sorted(pasta.glob("*.json")):
        casado = PADRAO_DO_RECIBO.match(arquivo.name)
        if not casado:
            continue
        try:
            dado = json.loads(arquivo.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(dado, dict):
            continue
        terminou = instante_do_marco(dado.get("quando"))
        if terminou is None:
            continue
        duracao = dado.get("duracao")
        duracao = float(duracao) if isinstance(duracao, (int, float)) else 0.0
        colhidos.append({
            "ordem": int(casado.group(1)),
            "ciclo": int(casado.group(3)),
            "passo": casado.group(2),
            "recibo": dado,
            "comecou": terminou - duracao,
            "terminou": terminou,
            "duracao": duracao,
            "modelos": modelos_do_log(arquivo),
        })
    return sorted(colhidos, key=lambda e: (e["ordem"], e["ciclo"]))


def tokens_do_recibo(recibo: dict) -> dict:
    custo = recibo.get("custo")
    tokens = custo.get("tokens") if isinstance(custo, dict) else None
    return tokens if isinstance(tokens, dict) else {}


def pior_veredito(recibos: list) -> str:
    vistos = {r.get("veredito") for r in recibos}
    for veredito in VEREDITO_PIOR_PRIMEIRO:
        if veredito in vistos:
            return veredito
    return "?"


def motor_do_grupo(grupo: list) -> tuple:
    modelos = set()
    for etapa in grupo:
        modelos.update(etapa.get("modelos") or {})
    if len(modelos) != 1:
        return MOTOR_NAO_DECLARADO, MOTOR_NAO_DECLARADO
    unico = sorted(modelos)[0]
    return motor_do_modelo(unico), unico


def pontos_do_gasto(trabalho: str, passo: str, grupo: list,
                    quando: float) -> list:
    recibos = [e["recibo"] for e in grupo]
    usd = sum(r["custo"]["usd"] for r in recibos
              if isinstance(r.get("custo"), dict)
              and isinstance(r["custo"].get("usd"), (int, float)))
    medidos = [r for r in recibos if isinstance(r.get("custo"), dict)]
    if not medidos:
        return []
    motor, modelo = motor_do_grupo(grupo)
    etiquetas = ["passo:" + passo, "trabalho:" + trabalho,
                 "motor:" + motor, "modelo:" + modelo]
    pontos = [{"metric": METRICA_DO_CUSTO, "type": TIPO_MEDIDOR,
               "points": [{"timestamp": int(quando), "value": float(usd)}],
               "tags": list(etiquetas)}]
    somados = {}
    for recibo in medidos:
        for chave, valor in (tokens_do_recibo(recibo) or {}).items():
            if isinstance(valor, int):
                somados[chave] = somados.get(chave, 0) + valor
    for chave, valor in sorted(somados.items()):
        pontos.append({"metric": METRICA_DOS_TOKENS, "type": TIPO_MEDIDOR,
                       "points": [{"timestamp": int(quando),
                                   "value": float(valor)}],
                       "tags": etiquetas + ["token:" + chave]})
    return pontos


def metricas_do_desenho(trabalho: str, etapas: list, quando: float) -> list:
    pontos = []
    por_passo = {}
    for etapa in etapas:
        por_passo.setdefault(etapa["passo"], []).append(etapa)
    for passo, grupo in sorted(por_passo.items()):
        recibos = [e["recibo"] for e in grupo]
        pontos += pontos_do_gasto(trabalho, passo, grupo, quando)
        pontos.append({
            "metric": METRICA_DOS_RECIBOS,
            "type": TIPO_CONTADOR,
            "points": [{"timestamp": int(quando), "value": float(len(recibos))}],
            "tags": ["passo:" + passo, "trabalho:" + trabalho],
        })
        for campo in CAMPOS_DE_GASTO:
            medidos = sum(1 for r in recibos
                          if r.get(campo) not in (None, "", {}, []))
            pontos.append({
                "metric": METRICA_DA_COBERTURA,
                "type": TIPO_MEDIDOR,
                "points": [{"timestamp": int(quando),
                            "value": medidos / float(len(recibos))}],
                "tags": ["passo:" + passo, "campo:" + campo,
                         "trabalho:" + trabalho],
            })
    return pontos


def desenho_da_execucao(pasta: Path) -> dict:
    etapas = recibos_da_execucao(pasta)
    if not etapas:
        return {}
    trabalho = etapas[0]["recibo"].get("trabalho") or pasta.name
    comecou = min(e["comecou"] for e in etapas)
    terminou = max(e["terminou"] for e in etapas)
    return {
        "trabalho": trabalho,
        "comecou": comecou,
        "terminou": terminou,
        "etapas": etapas,
        "metricas": metricas_do_desenho(trabalho, etapas, terminou),
    }


def preparar_o_ambiente() -> None:
    for nome, valor in AMBIENTE_DA_EMISSAO.items():
        os.environ.setdefault(nome, valor)
    os.environ.setdefault(VARIAVEL_DA_APLICACAO, aplicacao())
    os.environ.setdefault("DD_SERVICE", aplicacao())
    os.environ.setdefault("DD_ENV", "local")


def emitir_spans(desenho: dict, sessao: str) -> int:
    preparar_o_ambiente()
    from ddtrace.llmobs import LLMObs

    LLMObs.enable()
    trabalho = desenho["trabalho"]
    with LLMObs.agent(name="execucao-" + trabalho, session_id=sessao) as raiz:
        raiz.start_ns = int(desenho["comecou"] * 1e9)
        LLMObs.annotate(span=raiz, tags={
            "projeto": "atlas", "trabalho": trabalho, "session_id": sessao,
            "origem": "emissor", "passo": PASSO_DA_EXECUCAO_INTEIRA,
            "veredito": pior_veredito([e["recibo"]
                                       for e in desenho["etapas"]])},
            input_data="execução do encadeador, lida dos recibos",
            output_data="%d etapa(s)" % len(desenho["etapas"]))
        for etapa in desenho["etapas"]:
            recibo = etapa["recibo"]
            tokens = tokens_do_recibo(recibo)
            modelos = etapa.get("modelos") or {}
            unico = sorted(modelos)[0] if len(modelos) == 1 else ""
            abrir = LLMObs.llm if tokens else LLMObs.task
            argumentos = {"name": etapa["passo"], "session_id": sessao}
            if tokens and unico:
                argumentos["model_name"] = unico
            with abrir(**argumentos) as filho:
                filho.start_ns = int(etapa["comecou"] * 1e9)
                medidas = {}
                if tokens:
                    medidas = {
                        "input_tokens": tokens.get("entrada", 0),
                        "output_tokens": tokens.get("saida", 0),
                        "cache_read_input_tokens": tokens.get("cache-lido", 0),
                    }
                if isinstance(recibo.get("turnos"), int):
                    medidas["turnos"] = recibo["turnos"]
                anotacao = {"tags": {
                    "projeto": "atlas", "passo": etapa["passo"],
                    "trabalho": trabalho, "origem": "emissor",
                    "veredito": recibo.get("veredito", "?"),
                    "modelo": unico or MOTOR_NAO_DECLARADO,
                    "motor": motor_do_modelo(unico) if unico
                    else MOTOR_NAO_DECLARADO,
                    "session_id": sessao}, "metrics": medidas}
                if tokens:
                    anotacao["cost_tags"] = ["passo", "trabalho", "veredito",
                                             "motor", "modelo"]
                LLMObs.annotate(span=filho, **anotacao)
                filho.finish(finish_time=etapa["terminou"])
        raiz.finish(finish_time=desenho["terminou"])
    LLMObs.flush()
    return len(desenho["etapas"])


def mandar_pontos(pontos: list) -> int:
    if not pontos:
        return 0
    site = os.environ.get(VARIAVEL_DO_SITE, "").strip() or SITE_PADRAO
    corpo = json.dumps({"series": pontos}).encode("utf-8")
    pedido = urllib.request.Request("https://api." + site + "/api/v2/series",
                                    data=corpo, method="POST")
    pedido.add_header("Content-Type", "application/json")
    pedido.add_header("DD-API-KEY", chave_de_api())
    with urllib.request.urlopen(pedido, timeout=TEMPO_DA_REDE_S) as resposta:
        resposta.read()
    return len(pontos)


def emitir_metricas(desenho: dict) -> int:
    return mandar_pontos(desenho.get("metricas") or [])


def ponto_medido(metrica: str, valor: float, quando: float,
                 etiquetas: list) -> dict:
    return {"metric": metrica, "type": TIPO_MEDIDOR,
            "points": [{"timestamp": int(quando), "value": float(valor)}],
            "tags": list(etiquetas)}


def etiqueta_sem_acento(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto or "?").encode(
        "ascii", "ignore").decode("ascii")
    return "-".join(sem_acento.lower().split()) or "?"


def pontos_do_credito(creditos: dict, quando: float) -> list:
    pontos = []
    for nome, (cobranca, usado) in sorted(creditos.items()):
        etiquetas = ["motor:" + nome,
                     "cobranca:" + etiqueta_sem_acento(cobranca)]
        medido = isinstance(usado, (int, float))
        pontos.append(ponto_medido(METRICA_DA_FONTE_DO_CREDITO,
                                   1.0 if medido else 0.0, quando, etiquetas))
        if medido:
            pontos.append(ponto_medido(METRICA_DO_CREDITO, usado, quando,
                                       etiquetas))
    return pontos


def instante_do_registro(quando):
    if isinstance(quando, str) and quando.endswith("Z"):
        quando = quando[:-1] + "+00:00"
    return instante_do_marco(quando)


def gasto_do_rollout(arquivo: Path) -> dict:
    try:
        bruto = arquivo.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    sessao, modelo, total, chamadas, ultimo = "", "", None, 0, None
    for linha in bruto.splitlines():
        try:
            dado = json.loads(linha)
        except ValueError:
            continue
        if not isinstance(dado, dict):
            continue
        corpo = dado.get("payload")
        corpo = corpo if isinstance(corpo, dict) else {}
        if dado.get("type") == "session_meta":
            sessao = str(corpo.get("id") or corpo.get("session_id") or "")
        elif (dado.get("type") == "turn_context"
              and isinstance(corpo.get("model"), str)):
            modelo = corpo["model"]
        elif corpo.get("type") == "token_count":
            informe = corpo.get("info")
            uso = (informe.get("total_token_usage")
                   if isinstance(informe, dict) else None)
            instante = instante_do_registro(dado.get("timestamp"))
            if isinstance(uso, dict) and instante is not None:
                total, ultimo = uso, instante
                chamadas += 1
    if total is None:
        return {}

    def contado(campo):
        valor = total.get(campo)
        return valor if isinstance(valor, int) else 0

    return {"sessao": sessao or arquivo.stem, "modelo": modelo,
            "quando": ultimo, "chamadas": chamadas,
            "tokens": {"entrada": max(0, contado("input_tokens")
                                      - contado("cached_input_tokens")),
                       "cache-lido": contado("cached_input_tokens"),
                       "cache-criado": contado("cache_write_input_tokens"),
                       "saida": contado("output_tokens")}}


def pontos_do_codex(gastos: list, agora: float) -> tuple:
    pontos, fora = [], 0
    for gasto in gastos:
        if not gasto:
            continue
        if agora - gasto["quando"] > JANELA_QUE_A_API_ACEITA_S - FOLGA_DA_JANELA_S:
            fora += 1
            continue
        etiquetas = ["motor:codex",
                     "modelo:" + (gasto["modelo"] or MOTOR_NAO_DECLARADO),
                     "sessao:" + gasto["sessao"]]
        for tipo, valor in sorted(gasto["tokens"].items()):
            pontos.append(ponto_medido(METRICA_DOS_TOKENS_DO_MOTOR, valor,
                                       gasto["quando"],
                                       etiquetas + ["token:" + tipo]))
        pontos.append(ponto_medido(METRICA_DAS_CHAMADAS_DO_MOTOR,
                                   gasto["chamadas"], gasto["quando"],
                                   etiquetas))
    return pontos, fora


def rollouts_recentes(pasta: Path, agora: float) -> list:
    achados = []
    for arquivo in sorted(pasta.glob(MOLDE_DO_ROLLOUT)):
        try:
            mexido = arquivo.stat().st_mtime
        except OSError:
            continue
        if mexido >= agora - JANELA_QUE_A_API_ACEITA_S:
            achados.append(arquivo)
    return achados


def carregar_os_motores(raiz: Path):
    caminho = raiz / INSTRUMENTO_DOS_MOTORES
    if not caminho.is_file():
        return None
    especificacao = importlib.util.spec_from_file_location(
        "motores_lidos_pelo_emissor", caminho)
    modulo = importlib.util.module_from_spec(especificacao)
    try:
        especificacao.loader.exec_module(modulo)
    except (OSError, SyntaxError, ImportError):
        return None
    return modulo


def desenho_dos_motores(raiz: Path, agora: float) -> dict:
    modulo = carregar_os_motores(raiz)
    if modulo is None:
        return {"pontos": [], "fora": 0, "impedimento": SEM_MOTORES.format(
            raiz / INSTRUMENTO_DOS_MOTORES)}
    cadastro = modulo.ler_o_cadastro(raiz / ARQUIVO_DO_CADASTRO)
    motores = cadastro.get("motores") if isinstance(cadastro, dict) else None
    if not isinstance(motores, dict) or not motores:
        return {"pontos": [], "fora": 0, "impedimento": SEM_CADASTRO.format(
            raiz / ARQUIVO_DO_CADASTRO)}
    creditos = {}
    for nome in motores:
        receita = modulo.receita_do_motor(nome) or {}
        limite = modulo.credito_do_motor(receita) if receita else {}
        creditos[nome] = (receita.get("cobranca", "?"),
                          limite.get("usado_por_cento"))
    pontos = pontos_do_credito(creditos, agora)
    fora = 0
    fonte = (modulo.receita_do_motor(MOTOR_COM_REGISTRO) or {}).get(
        "fonte_do_limite")
    if MOTOR_COM_REGISTRO in motores and fonte:
        gastos = [gasto_do_rollout(arquivo) for arquivo in
                  rollouts_recentes(Path(fonte).expanduser(), agora)]
        do_codex, fora = pontos_do_codex(gastos, agora)
        pontos += do_codex
    return {"pontos": pontos, "fora": fora, "impedimento": ""}


def emitir_os_motores(raiz: Path) -> int:
    if not chave_de_api():
        print(SEM_MEDICAO.format(SEM_CHAVE))
        return SILENCIO
    desenho = desenho_dos_motores(raiz, time.time())
    if desenho["impedimento"]:
        print(SEM_MEDICAO.format(desenho["impedimento"]))
        return SILENCIO
    try:
        enviados = mandar_pontos(desenho["pontos"])
    except (urllib.error.URLError, OSError, ValueError) as falha:
        print(FALHA_DA_METRICA.format(falha))
        enviados = 0
    print(EMITIDO_DOS_MOTORES.format(pontos=enviados, fora=desenho["fora"]))
    return SILENCIO


def porque_nao_mede(pasta: Path) -> str:
    if not chave_de_api():
        return SEM_CHAVE
    preparar_o_ambiente()
    try:
        import ddtrace.llmobs
    except ImportError:
        return SEM_BIBLIOTECA
    del ddtrace
    if not recibos_da_execucao(pasta):
        return SEM_RECIBO.format(pasta)
    return ""


def emitir_a_execucao(pasta: Path, sessao: str) -> int:
    impedimento = porque_nao_mede(pasta)
    if impedimento:
        print(SEM_MEDICAO.format(impedimento))
        return SILENCIO
    desenho = desenho_da_execucao(pasta)
    quantas = emitir_spans(desenho, sessao)
    try:
        pontos = emitir_metricas(desenho)
    except (urllib.error.URLError, OSError, ValueError) as falha:
        print(FALHA_DA_METRICA.format(falha))
        pontos = 0
    print(EMITIDO.format(etapas=quantas, trabalho=desenho["trabalho"],
                         pontos=pontos))
    return SILENCIO


def armar_o_prazo_duro(prazo_s: float):
    import threading

    def encerrar_o_processo_sem_esperar_ninguem():
        print(SEM_MEDICAO.format(PRAZO_ESTOURADO.format(prazo_s)), flush=True)
        os._exit(SILENCIO)

    relogio = threading.Timer(prazo_s, encerrar_o_processo_sem_esperar_ninguem)
    relogio.daemon = True
    relogio.start()
    return relogio


def sair_sem_esperar_a_biblioteca(codigo: int) -> None:
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(codigo)


def montar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="emissor.py",
        description="lê os recibos de uma execução e manda span e métrica "
                    "para a ferramenta de observabilidade. A emissão é "
                    "opcional: sem chave no ambiente ou sem a biblioteca, "
                    "ela diz não medido e sai zero")
    parser.add_argument("--execucao", help="a pasta de evidências do trabalho")
    parser.add_argument("--motores", action="store_true",
                        help="emite o crédito de cada motor auxiliar "
                             "cadastrado e o gasto do Codex lido do registro "
                             "dele; lê o cadastro da raiz, que é a pasta atual")
    parser.add_argument("--sessao", default="", help="o identificador da "
                                                     "sessão que agrupa os spans")
    parser.add_argument("--ensaio", action="store_true",
                        help="mostra o que emitiria, sem emitir")
    parser.add_argument("--testar", action="store_true")
    return parser


def mostrar_o_ensaio(pasta: Path) -> int:
    desenho = desenho_da_execucao(pasta)
    if not desenho:
        print(SEM_MEDICAO.format(SEM_RECIBO.format(pasta)))
        return SILENCIO
    print("ensaio de %s — nada será emitido:" % desenho["trabalho"])
    for etapa in desenho["etapas"]:
        tokens = tokens_do_recibo(etapa["recibo"])
        print("  %02d-%s-c%d  %s  %.3fs  %s"
              % (etapa["ordem"], etapa["passo"], etapa["ciclo"],
                 etapa["recibo"].get("veredito", "?"), etapa["duracao"],
                 "llm" if tokens else "task"))
    print("  %d ponto(s) de métrica" % len(desenho["metricas"]))
    return SILENCIO


def mostrar_o_ensaio_dos_motores(raiz: Path) -> int:
    desenho = desenho_dos_motores(raiz, time.time())
    if desenho["impedimento"]:
        print(SEM_MEDICAO.format(desenho["impedimento"]))
        return SILENCIO
    print("ensaio dos motores — nada será emitido:")
    for ponto in desenho["pontos"]:
        print("  %s = %s  %s" % (ponto["metric"],
                                 ponto["points"][0]["value"],
                                 " ".join(ponto["tags"])))
    print("  %d registro(s) do Codex fora da janela" % desenho["fora"])
    return SILENCIO


def main(argv) -> int:
    parser = montar_parser()
    if BANDEIRA_DE_TESTE in argv:
        return testar()
    args = parser.parse_args(argv)
    if args.motores:
        if args.ensaio:
            return mostrar_o_ensaio_dos_motores(Path.cwd())
        armar_o_prazo_duro(PRAZO_DURO_DA_EMISSAO_S)
        sair_sem_esperar_a_biblioteca(emitir_os_motores(Path.cwd()))
    if not args.execucao:
        parser.error("informe --execucao com a pasta de evidências, "
                     "ou --motores")
    pasta = Path(args.execucao)
    if args.ensaio:
        return mostrar_o_ensaio(pasta)
    armar_o_prazo_duro(PRAZO_DURO_DA_EMISSAO_S)
    sair_sem_esperar_a_biblioteca(
        emitir_a_execucao(pasta, args.sessao or pasta.name))


BANDEIRA_DE_TESTE = "--testar"


def _recibo(passo, **troca):
    base = {"etapa": passo, "trabalho": "t", "veredito": "segue",
            "provado": [], "suposto": [], "faltas": [],
            "quando": "2026-09-20T10:00:00-03:00", "ciclo": {"i": 1, "teto": 3}}
    base.update(troca)
    return base


def testar() -> int:
    import tempfile
    falhas, casos = [], []

    def caso(rotulo, condicao):
        casos.append(rotulo)
        if not condicao:
            falhas.append(rotulo)

    with tempfile.TemporaryDirectory(prefix="emissor-") as tmp:
        pasta = Path(tmp) / "t"
        pasta.mkdir()
        guardado = os.environ.pop(VARIAVEL_DA_CHAVE, None)
        caso("sem chave no ambiente, o emissor diz não medido e sai zero — "
             "quem não pode medir não pode derrubar quem o chamou",
             porque_nao_mede(pasta) == SEM_CHAVE
             and emitir_a_execucao(pasta, "s") == SILENCIO)
        os.environ[VARIAVEL_DA_CHAVE] = "chave-de-mentira"
        caso("com chave e pasta vazia, ainda é não medido, e não estouro",
             porque_nao_mede(pasta).startswith("a pasta"))

        (pasta / "01-primeiro-c1.json").write_text(
            json.dumps(_recibo("primeiro", duracao=2.0)), encoding="utf-8")
        (pasta / "02-segundo-c1.json").write_text(json.dumps(_recibo(
            "segundo", duracao=4.0, turnos=3,
            quando="2026-09-20T10:00:10-03:00",
            custo={"usd": 0.5, "tokens": {"entrada": 1, "saida": 2,
                                          "cache-lido": 3,
                                          "cache-criado": 4}})),
            encoding="utf-8")
        desenho = desenho_da_execucao(pasta)

        caso("o desenho acha as duas etapas, na ordem do prefixo",
             [e["passo"] for e in desenho["etapas"]] == ["primeiro", "segundo"])
        caso("o começo de cada etapa é o carimbo menos a duração, porque o "
             "recibo grava o FIM e o span precisa do início",
             abs(desenho["etapas"][0]["comecou"]
                 - (desenho["etapas"][0]["terminou"] - 2.0)) < 0.001)
        caso("a execução começa na etapa mais antiga e termina na mais nova",
             desenho["comecou"] == desenho["etapas"][0]["comecou"]
             and desenho["terminou"] == desenho["etapas"][1]["terminou"])
        caso("etapa com custo vira span de modelo; sem custo, vira tarefa — "
             "chamar de modelo o que não chamou modelo inventaria gasto",
             not tokens_do_recibo(desenho["etapas"][0]["recibo"])
             and tokens_do_recibo(desenho["etapas"][1]["recibo"]))

        nomes = [p["metric"] for p in desenho["metricas"]]
        caso("sai um ponto de contagem por passo",
             nomes.count(METRICA_DOS_RECIBOS) == 2)
        caso("e um ponto de cobertura por passo e por campo de gasto",
             nomes.count(METRICA_DA_COBERTURA) == 2 * len(CAMPOS_DE_GASTO))

        def cobertura(passo, campo):
            for ponto in desenho["metricas"]:
                if ponto["metric"] != METRICA_DA_COBERTURA:
                    continue
                if ("passo:" + passo) in ponto["tags"] \
                        and ("campo:" + campo) in ponto["tags"]:
                    return ponto["points"][0]["value"]
            return None

        caso("cobertura de custo é 1 no passo que mediu e 0 no que não mediu: "
             "ausência é zero de COBERTURA, nunca custo zero",
             cobertura("segundo", "custo") == 1.0
             and cobertura("primeiro", "custo") == 0.0)
        caso("cobertura de assinatura é 0 quando o campo não existe, e isso "
             "é idade do campo, não defeito de medição",
             cobertura("primeiro", "assinatura") == 0.0)
        caso("todo ponto de métrica leva o trabalho na etiqueta, senão duas "
             "execuções somam sem ninguém pedir",
             all(any(t.startswith("trabalho:") for t in p["tags"])
                 for p in desenho["metricas"]))

        def valor_de(nome, passo):
            for ponto in desenho["metricas"]:
                if ponto["metric"] == nome \
                        and ("passo:" + passo) in ponto["tags"]:
                    return ponto["points"][0]["value"]
            return None

        caso("o custo sai como métrica NOSSA, tirada do recibo: a estimativa "
             "do fornecedor não existe quando o modelo não é declarado, e "
             "declarar modelo que não se mediu inventaria o preço",
             valor_de(METRICA_DO_CUSTO, "segundo") == 0.5)
        caso("passo sem custo medido não emite ponto de custo — zero dólares "
             "diria que rodou de graça, e o que houve foi não medir",
             valor_de(METRICA_DO_CUSTO, "primeiro") is None)
        caso("os tokens saem quebrados por tipo, cada um na sua etiqueta",
             len([p for p in desenho["metricas"]
                  if p["metric"] == METRICA_DOS_TOKENS]) == 4)
        caso("o pior veredito da execução manda: uma etapa que parou faz a "
             "execução inteira parar, e a raiz não pode dizer segue",
             pior_veredito([{"veredito": "segue"}, {"veredito": "para"}])
             == "para"
             and pior_veredito([{"veredito": "segue"}]) == "segue")

        caso("a marca de cache sai do nome do modelo: o fornecedor não "
             "reconhece o nome com o sufixo, e sem reconhecer não precifica",
             sem_a_marca_de_cache("claude-opus-5[1m]") == "claude-opus-5")
        caso("o motor sai do nome do modelo, que foi LIDO do log da sessão, "
             "não escolhido por mim",
             motor_do_modelo("claude-opus-5[1m]") == "claude")
        caso("etapa sem log não ganha modelo nem motor inventado",
             motor_do_grupo([{"modelos": {}}])
             == (MOTOR_NAO_DECLARADO, MOTOR_NAO_DECLARADO))
        caso("grupo com DOIS modelos não atribui nenhum: dizer qual foi "
             "exigiria escolher, e escolher aqui é inventar",
             motor_do_grupo([{"modelos": {"claude-opus-5": {}}},
                             {"modelos": {"outro-motor-9": {}}}])
             == (MOTOR_NAO_DECLARADO, MOTOR_NAO_DECLARADO))
        caso("grupo com um modelo só atribui os dois",
             motor_do_grupo([{"modelos": {"claude-opus-5": {}}}])
             == ("claude", "claude-opus-5"))

        (pasta / "03-quebrado-c1.json").write_text("{ isto nao e json",
                                                   encoding="utf-8")
        caso("recibo ilegível é pulado sem derrubar a leitura dos outros",
             len(recibos_da_execucao(pasta)) == 2)
        (pasta / "04-sem-quando-c1.json").write_text(
            json.dumps({"etapa": "x", "trabalho": "t", "veredito": "segue"}),
            encoding="utf-8")
        caso("recibo sem carimbo de tempo é pulado: sem início não há span "
             "honesto, e inventar o instante seria fabricar medição",
             len(recibos_da_execucao(pasta)) == 2)
        (pasta / "ambiente.json").write_text("{}", encoding="utf-8")
        caso("arquivo que não casa o molde de recibo não entra na conta",
             len(recibos_da_execucao(pasta)) == 2)

        guardados = {nome: os.environ.pop(nome, None)
                     for nome in AMBIENTE_DA_EMISSAO}
        porque_nao_mede(pasta)
        caso("o ambiente do modo sem agente é posto ANTES de qualquer "
             "importação da biblioteca: ela lê a configuração no import, e "
             "ligar depois não liga nada — o emissor diria enviado sem "
             "enviar, que é pior do que não medir",
             all(os.environ.get(nome) == valor
                 for nome, valor in AMBIENTE_DA_EMISSAO.items()))
        for nome, valor in guardados.items():
            if valor is None:
                os.environ.pop(nome, None)
            else:
                os.environ[nome] = valor

        if guardado is None:
            os.environ.pop(VARIAVEL_DA_CHAVE, None)
        else:
            os.environ[VARIAVEL_DA_CHAVE] = guardado

    agora = 1790000000.0
    creditos = {"codex": ("assinatura", 46.0),
                "devin": ("pré-pago por token", None)}
    pontos = pontos_do_credito(creditos, agora)

    def pontos_de(nome, motor):
        return [p for p in pontos if p["metric"] == nome
                and ("motor:" + motor) in p["tags"]]

    caso("o crédito lido sem gastar vira métrica do motor que tem fonte",
         [p["points"][0]["value"] for p in pontos_de(METRICA_DO_CREDITO,
                                                     "codex")] == [46.0])
    caso("motor sem fonte local de crédito fica AUSENTE da métrica, nunca "
         "zero: zero diria janela vazia, e o que houve foi não saber",
         pontos_de(METRICA_DO_CREDITO, "devin") == [])
    caso("a ausência se vê pela cobertura: 1 no motor com fonte, 0 no sem",
         [p["points"][0]["value"] for p in pontos_de(
             METRICA_DA_FONTE_DO_CREDITO, "codex")] == [1.0]
         and [p["points"][0]["value"] for p in pontos_de(
             METRICA_DA_FONTE_DO_CREDITO, "devin")] == [0.0])
    caso("a cobrança vai na etiqueta, sem acento nem espaço",
         any("cobranca:pre-pago-por-token" in p["tags"]
             for p in pontos_de(METRICA_DA_FONTE_DO_CREDITO, "devin")))

    with tempfile.TemporaryDirectory(prefix="emissor-motores-") as tmp:
        raiz = Path(tmp)
        rollout = raiz / "sessoes" / "rollout-teste.jsonl"
        rollout.parent.mkdir(parents=True)
        linhas = [
            {"type": "session_meta", "payload": {"id": "sessao-9"}},
            {"type": "turn_context", "payload": {"model": "modelo-do-log"}},
            {"timestamp": "2026-09-21T12:00:00.000Z", "type": "event_msg",
             "payload": {"type": "token_count", "info": None}},
            {"timestamp": "2026-09-21T12:00:05.000Z", "type": "event_msg",
             "payload": {"type": "token_count", "info": {"total_token_usage": {
                 "input_tokens": 100, "cached_input_tokens": 60,
                 "cache_write_input_tokens": 0, "output_tokens": 7}}}},
            {"timestamp": "2026-09-21T12:00:09.000Z", "type": "event_msg",
             "payload": {"type": "token_count", "info": {"total_token_usage": {
                 "input_tokens": 300, "cached_input_tokens": 200,
                 "cache_write_input_tokens": 5, "output_tokens": 20}}}},
        ]
        rollout.write_text("\n".join(json.dumps(l) for l in linhas)
                           + "\n{ partida", encoding="utf-8")
        gasto = gasto_do_rollout(rollout)
        quando = gasto.get("quando") or 0.0
        caso("o gasto do Codex sai do registro dele: o ÚLTIMO total acumulado, "
             "com a entrada sem o cache, como no recibo da casa",
             gasto.get("tokens") == {"entrada": 100, "cache-lido": 200,
                                     "cache-criado": 5, "saida": 20})
        caso("chamada é contagem de token lido, e evento sem uso não conta",
             gasto.get("chamadas") == 2)
        caso("o modelo e a sessão saem do próprio registro, nunca escolhidos",
             gasto.get("modelo") == "modelo-do-log"
             and gasto.get("sessao") == "sessao-9")
        caso("o instante é o do último uso lido, e é ele que faz a emissão "
             "repetida cair no mesmo ponto em vez de somar",
             quando == instante_do_marco(
                 "2026-09-21T12:00:09.000+00:00"))
        vazio = raiz / "sessoes" / "rollout-vazio.jsonl"
        vazio.write_text(json.dumps(linhas[0]), encoding="utf-8")
        caso("registro sem uso de token não vira gasto zero: vira nada",
             gasto_do_rollout(vazio) == {})

        recente, fora = pontos_do_codex([gasto], quando + 60)
        caso("gasto recente sai em ponto por tipo de token, mais as chamadas",
             len([p for p in recente
                  if p["metric"] == METRICA_DOS_TOKENS_DO_MOTOR]) == 4
             and [p["points"][0]["value"] for p in recente if p["metric"]
                  == METRICA_DAS_CHAMADAS_DO_MOTOR] == [2.0] and fora == 0)
        caso("todo ponto de gasto leva motor, modelo e sessão na etiqueta",
             bool(recente)
             and all({"motor:codex", "modelo:modelo-do-log", "sessao:sessao-9"}
                     <= set(p["tags"]) for p in recente))
        velho, fora = pontos_do_codex(
            [gasto], quando + JANELA_QUE_A_API_ACEITA_S + 1)
        caso("gasto mais velho que a janela que a API aceita não sai, e é "
             "contado: ponto velho some calado na ingestão",
             velho == [] and fora == 1)

        os.utime(vazio, (agora - 2 * JANELA_QUE_A_API_ACEITA_S,) * 2)
        os.utime(rollout, (agora - 10,) * 2)
        caso("só o registro mexido dentro da janela é lido",
             rollouts_recentes(raiz / "sessoes", agora) == [rollout])

        caso("sem o instrumento dos motores, os motores são não medidos, "
             "e isso não estoura",
             desenho_dos_motores(raiz, agora)["impedimento"].startswith(
                 SEM_MOTORES.split("{")[0]))
        instrumento = raiz / INSTRUMENTO_DOS_MOTORES
        instrumento.parent.mkdir(parents=True)
        instrumento.write_text(MOTORES_DE_MENTIRA.format(
            sessoes=str(raiz / "sessoes")), encoding="utf-8")
        (raiz / "nucleo").mkdir()
        (raiz / ARQUIVO_DO_CADASTRO).write_text(json.dumps(
            {"motores": {"codex": {}, "devin": {}}}), encoding="utf-8")
        desenho = desenho_dos_motores(raiz, quando + 60)
        nomes = [p["metric"] for p in desenho["pontos"]]
        caso("o desenho dos motores junta o crédito de cada motor cadastrado "
             "e o gasto do Codex dos registros recentes",
             nomes.count(METRICA_DA_FONTE_DO_CREDITO) == 2
             and nomes.count(METRICA_DO_CREDITO) == 1
             and nomes.count(METRICA_DOS_TOKENS_DO_MOTOR) == 4)

        guardada = os.environ.pop(VARIAVEL_DA_CHAVE, None)
        caso("sem chave, a emissão dos motores diz não medido e sai zero",
             emitir_os_motores(raiz) == SILENCIO)
        if guardada is not None:
            os.environ[VARIAVEL_DA_CHAVE] = guardada

    morreu, saida, dito = processo_que_trava_com_o_prazo_armado(1)
    caso("emissor que TRAVA não vive além do prazo: o processo de verdade "
         "está morto depois dele, sai zero e diz não medido — tempo limite "
         "que não mata não é tempo limite",
         morreu and saida == SILENCIO and "não medido" in dito)

    if falhas:
        for falha in falhas:
            print(LINHA_DE_FALHA.format(falha))
        print(FALHA_DO_TESTE.format(len(falhas), len(casos)))
        return QUEBROU
    print(OK_DO_TESTE.format(len(casos)))
    return SILENCIO


MOTORES_DE_MENTIRA = '''import json
from pathlib import Path


def receita_do_motor(nome, binario=""):
    return {{"codex": {{"cobranca": "assinatura",
                       "fonte_do_limite": {sessoes!r}}},
            "devin": {{"cobranca": "pré-pago por token",
                       "fonte_do_limite": ""}}}}.get(nome, {{}})


def credito_do_motor(receita, raiz_das_sessoes=None):
    return {{"usado_por_cento": 46.0 if receita.get("fonte_do_limite")
            else None}}


def ler_o_cadastro(caminho):
    return json.loads(Path(caminho).read_text(encoding="utf-8"))
'''

ESPERA_PELA_MORTE_DO_PROCESSO_S = 15
PROCESSO_QUE_TRAVA = (
    "import sys, threading\n"
    "sys.stdout.reconfigure(encoding='utf-8')\n"
    "sys.path.insert(0, {pasta!r})\n"
    "import emissor\n"
    "emissor.armar_o_prazo_duro({prazo})\n"
    "threading.Event().wait(120)\n")


def processo_que_trava_com_o_prazo_armado(prazo_s: float) -> tuple:
    import subprocess
    processo = subprocess.Popen(
        [sys.executable, "-c", PROCESSO_QUE_TRAVA.format(
            pasta=str(Path(__file__).resolve().parent), prazo=prazo_s)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        encoding="utf-8", errors="replace")
    try:
        dito, _ = processo.communicate(timeout=ESPERA_PELA_MORTE_DO_PROCESSO_S)
    except subprocess.TimeoutExpired:
        processo.kill()
        processo.communicate()
        return False, None, ""
    return processo.poll() is not None, processo.returncode, dito


if __name__ == "__main__":
    for canal in (sys.stdin, sys.stdout, sys.stderr):
        if not getattr(canal, "closed", True) and hasattr(canal, "reconfigure"):
            canal.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
