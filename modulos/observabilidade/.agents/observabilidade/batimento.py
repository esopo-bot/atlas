import argparse
import importlib.util
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

EMISSOR_AO_LADO = "emissor.py"
CACHE_DO_EMISSOR = []

PADRAO_DO_RECIBO = re.compile(r"(\d{2})-(.+)-c(\d+)\.json\Z")
PASTA_DAS_EVIDENCIAS = Path("execucoes") / "evidencias"
INDEXADOR = Path(".agents") / "indice" / "indexar.py"
CAMADA = Path(".agents") / "camada" / "camada.py"
DECLARACAO_DOS_SERVIDORES = ".mcp.json"
CHAVE_DOS_SERVIDORES = "mcpServers"

METRICA_DA_EXECUCAO = "atlas.execucao.horas_desde_a_ultima"
METRICA_DA_RONDA = "atlas.indice.horas_desde_a_ronda"
METRICA_DOS_ALVOS = "atlas.indice.alvos"
METRICA_DOS_SERVIDORES = "atlas.mcp.servidores"
METRICA_DE_CADA_SERVIDOR = "atlas.mcp.servidor"
TIPO_MEDIDOR = 3

SEGUNDOS_NA_HORA = 3600.0
ESTADOS_DA_RONDA = (("feitos", "indexado"), ("pulados", "ja-estava"),
                    ("sem_elegivel", "sem-arquivo"), ("falharam", "falhou"))

SEM_EXECUCAO = "não há recibo de etapa em {}"
SEM_RONDA = "o indexador não registrou ronda nenhuma"
SEM_SERVIDORES = "não há " + DECLARACAO_DOS_SERVIDORES + " na raiz"
SEM_CHAVE = "a variável DD_API_KEY não está no ambiente"
NAO_MEDIDO = "  não medido — {}"
BATEU = "batimento: {} ponto(s) enviado(s), {} medida(s) não medida(s)"
ENSAIO = "ensaio do batimento — nada será enviado:"
OK_DO_TESTE = "OK: {} casos — batimento de saúde local"
FALHA_DO_TESTE = "FALHOU: {} de {} casos"
LINHA_DE_FALHA = "FALHOU: {}"

SILENCIO = 0
QUEBROU = 1
BANDEIRA_DE_TESTE = "--testar"


def emissor():
    if CACHE_DO_EMISSOR:
        return CACHE_DO_EMISSOR[0]
    caminho = Path(__file__).resolve().with_name(EMISSOR_AO_LADO)
    origem = importlib.util.spec_from_file_location("emissor", caminho)
    modulo = importlib.util.module_from_spec(origem)
    origem.loader.exec_module(modulo)
    CACHE_DO_EMISSOR.append(modulo)
    return modulo


def horas_entre(antes: float, agora: float) -> float:
    return max(agora - antes, 0.0) / SEGUNDOS_NA_HORA


def medida(nome: str, valor: float, quando: float, etiquetas=()) -> dict:
    return {"metric": nome, "type": TIPO_MEDIDOR,
            "points": [{"timestamp": int(quando), "value": float(valor)}],
            "tags": list(etiquetas)}


def instante_do_recibo_mais_novo(pasta: Path):
    mais_novo = None
    for arquivo in pasta.rglob("*.json"):
        if not PADRAO_DO_RECIBO.match(arquivo.name):
            continue
        try:
            quando = arquivo.stat().st_mtime
        except OSError:
            continue
        if mais_novo is None or quando > mais_novo:
            mais_novo = quando
    return mais_novo


def pontos_da_execucao(pasta: Path, agora: float):
    mais_novo = instante_do_recibo_mais_novo(pasta)
    if mais_novo is None:
        return [], SEM_EXECUCAO.format(pasta)
    return [medida(METRICA_DA_EXECUCAO, horas_entre(mais_novo, agora),
                   agora)], ""


def pontos_da_ronda(ronda, agora: float):
    if not isinstance(ronda, dict) or not ronda:
        return [], SEM_RONDA
    pontos = []
    for chave, estado in ESTADOS_DA_RONDA:
        valor = ronda.get(chave)
        if isinstance(valor, int):
            pontos.append(medida(METRICA_DOS_ALVOS, valor, agora,
                                 ["estado:" + estado]))
    quando = ronda.get("quando")
    try:
        pontos.append(medida(METRICA_DA_RONDA,
                             horas_entre(datetime.fromisoformat(quando)
                                         .timestamp(), agora), agora))
    except (TypeError, ValueError):
        pass
    return pontos, "" if pontos else SEM_RONDA


def pontos_dos_servidores(declarados, desligados, pendentes, agora: float):
    if declarados is None:
        return [], SEM_SERVIDORES
    daqui = set(declarados)
    fora = set(desligados or ()) & daqui
    esperando = set(pendentes or ()) & daqui
    pontos = [
        medida(METRICA_DOS_SERVIDORES, len(daqui), agora,
               ["estado:declarado"]),
        medida(METRICA_DOS_SERVIDORES, len(fora), agora,
               ["estado:desligado"]),
        medida(METRICA_DOS_SERVIDORES, len(esperando), agora,
               ["estado:pendente"]),
    ]
    for nome in sorted(daqui):
        estado = ("desligado" if nome in fora
                  else "pendente" if nome in esperando else "de-pe")
        pontos.append(medida(METRICA_DE_CADA_SERVIDOR, 1, agora,
                             ["servidor:" + nome, "estado:" + estado]))
    return pontos, ""


def servidores_declarados(raiz: Path):
    try:
        dado = json.loads((raiz / DECLARACAO_DOS_SERVIDORES)
                          .read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    servidores = dado.get(CHAVE_DOS_SERVIDORES) if isinstance(dado, dict) else None
    return list(servidores) if isinstance(servidores, dict) else None


def carregar(caminho: Path, apelido: str):
    try:
        origem = importlib.util.spec_from_file_location(apelido, caminho)
        modulo = importlib.util.module_from_spec(origem)
        origem.loader.exec_module(modulo)
        return modulo
    except Exception:
        return None


def ronda_do_indexador(raiz: Path):
    modulo = carregar(raiz / INDEXADOR, "indexador")
    if modulo is None or not hasattr(modulo, "ultima_ronda"):
        return None
    try:
        return modulo.ultima_ronda(str(raiz))
    except Exception:
        return None


def servidores_em_falta(raiz: Path):
    modulo = carregar(raiz / CAMADA, "camada")
    if modulo is None:
        return set(), set()
    casa = Path.home()
    desligados, pendentes = set(), set()
    try:
        desligados = modulo.servidores_desligados_no_cliente(raiz, casa)
    except Exception:
        pass
    try:
        pendentes = modulo.servidores_pedindo_autenticacao(casa)
    except Exception:
        pass
    return desligados, pendentes


def bater(raiz: Path, agora: float):
    pontos, faltas = [], []
    for grupo, falta in (
            pontos_da_execucao(raiz / PASTA_DAS_EVIDENCIAS, agora),
            pontos_da_ronda(ronda_do_indexador(raiz), agora)):
        pontos += grupo
        if falta:
            faltas.append(falta)
    desligados, pendentes = servidores_em_falta(raiz)
    grupo, falta = pontos_dos_servidores(servidores_declarados(raiz),
                                         desligados, pendentes, agora)
    pontos += grupo
    if falta:
        faltas.append(falta)
    return pontos, faltas


def mostrar_o_ensaio(pontos: list, faltas: list) -> int:
    print(ENSAIO)
    for ponto in pontos:
        print("  %-38s %8.3f  %s" % (ponto["metric"],
                                     ponto["points"][0]["value"],
                                     " ".join(ponto["tags"]) or "sem etiqueta"))
    for falta in faltas:
        print(NAO_MEDIDO.format(falta))
    return SILENCIO


def main(argv) -> int:
    if BANDEIRA_DE_TESTE in argv:
        return testar()
    parser = argparse.ArgumentParser(
        prog="batimento.py",
        description="manda o estado local para a ferramenta de "
                    "observabilidade: há quanto tempo foi a última execução, "
                    "como foi a última ronda do índice, e quantos servidores "
                    "de contexto estão declarados, desligados ou pendentes. "
                    "Medida que não dá para fazer vira não medido, nunca zero")
    parser.add_argument("--raiz", default=".", help="a raiz do repositório")
    parser.add_argument("--ensaio", action="store_true",
                        help="mostra o que enviaria, sem enviar")
    args = parser.parse_args(argv)

    raiz = Path(args.raiz).resolve()
    pontos, faltas = bater(raiz, time.time())
    if args.ensaio:
        return mostrar_o_ensaio(pontos, faltas)
    if not emissor().chave_de_api():
        print(NAO_MEDIDO.format(SEM_CHAVE).strip())
        return SILENCIO
    try:
        enviados = emissor().mandar_pontos(pontos)
    except Exception as falha:
        print(NAO_MEDIDO.format("o envio falhou: %s" % falha).strip())
        return SILENCIO
    print(BATEU.format(enviados, len(faltas)))
    for falta in faltas:
        print(NAO_MEDIDO.format(falta))
    return SILENCIO


def testar() -> int:
    import tempfile
    falhas, casos = [], []

    def caso(rotulo, condicao):
        casos.append(rotulo)
        if not condicao:
            falhas.append(rotulo)

    agora = 1000000.0
    caso("a idade nunca é negativa: recibo com carimbo no futuro vira zero "
         "horas, e não uma idade ao contrário",
         horas_entre(agora + 7200, agora) == 0.0)
    caso("duas horas atrás dá duas horas",
         abs(horas_entre(agora - 7200, agora) - 2.0) < 1e-9)

    with tempfile.TemporaryDirectory(prefix="batimento-") as tmp:
        raiz = Path(tmp)
        evidencias = raiz / PASTA_DAS_EVIDENCIAS
        evidencias.mkdir(parents=True)
        pontos, falta = pontos_da_execucao(evidencias, agora)
        caso("pasta sem recibo nenhum vira NÃO MEDIDO, nunca idade zero — "
         "zero horas diria que acabou de rodar, que é o oposto da verdade",
             pontos == [] and falta.startswith("não há recibo"))

        (evidencias / "01-x-c1.json").write_text("{}", encoding="utf-8")
        pontos, falta = pontos_da_execucao(evidencias, agora)
        caso("com recibo, sai um ponto de idade e nenhuma falta",
             len(pontos) == 1 and falta == ""
             and pontos[0]["metric"] == METRICA_DA_EXECUCAO)

        (evidencias / "ambiente.json").write_text("{}", encoding="utf-8")
        caso("arquivo que não é recibo não conta como execução",
             instante_do_recibo_mais_novo(evidencias) is not None)

    ronda = {"quando": "2026-09-20T04:33:39", "feitos": 0, "pulados": 12,
             "sem_elegivel": 0, "falharam": 3}
    pontos, falta = pontos_da_ronda(ronda, agora)
    nomes = [p["metric"] for p in pontos]
    caso("a ronda vira um ponto por estado, mais a idade dela",
         nomes.count(METRICA_DOS_ALVOS) == 4
         and nomes.count(METRICA_DA_RONDA) == 1 and falta == "")
    falhou = [p for p in pontos if "estado:falhou" in p["tags"]]
    caso("alvo que falhou sai com o número dele, que é o que acende o "
         "alerta — falha de indexação some se virar só contagem total",
         falhou and falhou[0]["points"][0]["value"] == 3.0)
    pontos, falta = pontos_da_ronda(None, agora)
    caso("sem ronda registrada, é não medido e não zero",
         pontos == [] and falta == SEM_RONDA)
    pontos, falta = pontos_da_ronda({"feitos": 1}, agora)
    caso("ronda sem carimbo ainda dá os estados, e não inventa idade",
         [p["metric"] for p in pontos] == [METRICA_DOS_ALVOS])

    pontos, falta = pontos_dos_servidores(["a", "b"], {"a"}, set(), agora)
    valores = {p["tags"][0]: p["points"][0]["value"] for p in pontos
               if p["metric"] == METRICA_DOS_SERVIDORES}
    caso("servidor declarado, desligado e pendente saem separados: somar os "
         "três esconderia justamente o que interessa",
         valores == {"estado:declarado": 2.0, "estado:desligado": 1.0,
                     "estado:pendente": 0.0})
    pontos, falta = pontos_dos_servidores(None, set(), set(), agora)
    caso("sem declaração de servidor, é não medido — zero servidores e "
         "arquivo ausente são coisas diferentes",
         pontos == [] and falta == SEM_SERVIDORES)

    pontos, falta = pontos_dos_servidores(
        ["a"], {"de-outro-projeto"}, {"tambem-de-outro"}, agora)
    contagens = {p["tags"][0]: p["points"][0]["value"] for p in pontos
                 if p["metric"] == METRICA_DOS_SERVIDORES}
    caso("servidor desligado ou pendente de OUTRO projeto não conta aqui: o "
         "cliente guarda o estado da máquina inteira, e atribuir isso a este "
         "repositório inventaria defeito que não é dele",
         contagens == {"estado:declarado": 1.0, "estado:desligado": 0.0,
                       "estado:pendente": 0.0})

    pontos, falta = pontos_dos_servidores(["um", "dois"], {"dois"}, set(),
                                          agora)
    nomeados = {p["tags"][0]: p["tags"][1] for p in pontos
                if p["metric"] == METRICA_DE_CADA_SERVIDOR}
    caso("cada servidor sai NOMEADO com o estado dele: contagem diz quantos "
         "e não diz quais, e quando um cai é o nome que importa",
         nomeados == {"servidor:dois": "estado:desligado",
                      "servidor:um": "estado:de-pe"})

    caso("todo ponto é medidor, nunca contador: estado do mundo se lê como "
         "valor de agora, e contador somaria batimento com batimento",
         all(p["type"] == TIPO_MEDIDOR
             for p in pontos_da_ronda(ronda, agora)[0]))

    if falhas:
        for falha in falhas:
            print(LINHA_DE_FALHA.format(falha))
        print(FALHA_DO_TESTE.format(len(falhas), len(casos)))
        return QUEBROU
    print(OK_DO_TESTE.format(len(casos)))
    return SILENCIO


if __name__ == "__main__":
    for canal in (sys.stdin, sys.stdout, sys.stderr):
        if not getattr(canal, "closed", True) and hasattr(canal, "reconfigure"):
            canal.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
