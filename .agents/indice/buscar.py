import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

BANDEIRA_DE_TESTE = "--testar"
USO = ("busca no acervo indexado por significado E por termo exato, falando "
       "HTTP direto com o servidor de vetores e o de embeddings. É a porta "
       "normal para o acervo: não depende de cliente MCP — que política de "
       "organização pode barrar sem aviso — e usa só a biblioteca padrão. "
       "Descobre sozinho o que o indexador já indexou")

ARQUIVO_DOS_ALVOS = ".agents/indice/alvos.json"
CAMPO_DO_AMBIENTE = "ambiente"
CHAVE_DO_MODELO = "EMBEDDING_MODEL"
CHAVE_DO_SERVIDOR_DE_MODELO = "OLLAMA_HOST"
CHAVE_DO_BANCO = "MILVUS_ADDRESS"

MODELO_PADRAO = "nomic-embed-text"
BANCO_PADRAO = "127.0.0.1:19530"
SERVIDOR_DE_MODELO_PADRAO = "127.0.0.1:11434"
CAMINHO_DO_VETOR = "/api/embeddings"
CAMINHO_DA_BUSCA_DENSA = "/v2/vectordb/entities/search"
CAMINHO_DA_BUSCA_HIBRIDA = "/v2/vectordb/entities/hybrid_search"
CAMINHO_DA_CONSULTA = "/v2/vectordb/entities/query"
CAMINHO_DAS_COLECOES = "/v2/vectordb/collections/list"
CAMINHO_DA_DESCRICAO = "/v2/vectordb/collections/describe"
CAMINHO_DA_CONTAGEM = "/v2/vectordb/collections/get_stats"
PREFIXO_DA_COLECAO = "hybrid_code_chunks_"
MARCA_DO_CAMINHO_NA_DESCRICAO = "codebasePath:"
LETRAS_DO_RESUMO = 8
CAMPO_DO_VETOR_DENSO = "vector"
CAMPO_DO_VETOR_ESPARSO = "sparse_vector"
CAMPOS_QUE_VOLTAM = ["relativePath", "startLine", "content"]
FUSAO = {"strategy": "rrf", "params": {"k": 100}}
FUNIL_DA_FUSAO = 3
TEMPO_DA_CHAMADA = 90
QUANTOS_POR_PADRAO = 5
LETRAS_DO_TRECHO = 160

TETO_DE_TRECHOS_NA_AMOSTRA = 400
PERGUNTAS_POR_ALVO = 8
REPETICOES = 2
TERMO = re.compile(r"[A-Za-z_][\w\-]{5,}")
LETRAS_QUE_MARCAM_NOME = "-_"
FILTRO_DE_TUDO = "id != ''"
TOPO = 1
TRES_PRIMEIROS = 3

RECUSA_SEM_PERGUNTA = "sem pergunta: diga o que você quer achar, entre aspas"
RECUSA_ALVO_NAO_INDEXADO = ("alvo que não está indexado: {}. O que existe no "
                            "banco:\n{}")
NADA_INDEXADO = ("nada indexado no banco em {}: rode `indexar.py` antes. "
                 "Zero aqui não quer dizer que a resposta não existe")
VAZIA = "  {} — coleção existe mas está VAZIA: a indexação não gravou nada"
SEM_RESPOSTA = "  {} — nenhum trecho parecido"
CABECA = "BUSCA {} — \"{}\" em {} alvo(s)"
MODO_HIBRIDO = "híbrida (significado + termo exato)"
MODO_DENSO = "densa (só significado)"
LINHA_DO_ALVO = "  {}"
LINHA_DO_ACHADO = "    [{:.3f}] {}:{}"
LINHA_DO_TRECHO = "           {}"
RODAPE = ("\nA pontuação é a semelhança medida, não a certeza: o banco sempre "
          "devolve os mais próximos que tiver, mesmo quando nenhum serve.")
FALHOU_A_CHAMADA = "não consegui falar com {}: {}"
CABECA_DA_MEDICAO = ("MEDIÇÃO — denso puro contra híbrido, {} pergunta(s) por "
                     "termo exato, cada uma {}x por modo")
LINHA_DA_MEDICAO = "  {:<52} {:>3} perg.  topo {:>3}/{:<3} três {:>3}/{:<3}"
TOTAL_DA_MEDICAO = "  {:<52} {:>3} perg.  topo {:>3}/{:<3} três {:>3}/{:<3}"
RUIDO_DA_MEDICAO = ("  ruído: {} resposta(s) de topo mudaram entre repetições "
                    "iguais, em {} chamadas")
VEREDITO_DA_MEDICAO = "  veredito: {}"
HIBRIDO_VENCE_OU_EMPATA = "o híbrido vence ou empata em tudo"
HIBRIDO_PERDE = "o híbrido PERDE em {} — o denso não pode sair da porta"
NAO_MEDIDO = ("  não medido: {} — a medição precisa do banco e do gerador de "
              "vetores de pé")
SEM_PERGUNTA_NA_AMOSTRA = ("  {} — nenhum termo único na amostra; nada a "
                           "perguntar")


def colecao_do_alvo(caminho: str) -> str:
    absoluto = str(Path(caminho).expanduser().resolve())
    resumo = hashlib.md5(absoluto.encode()).hexdigest()[:LETRAS_DO_RESUMO]
    return PREFIXO_DA_COLECAO + resumo


def configuracao(cwd: str = "") -> dict:
    alvo = Path(cwd or ".") / ARQUIVO_DOS_ALVOS
    try:
        return json.loads(alvo.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def endereco(ambiente: dict, chave: str, padrao: str) -> str:
    valor = (ambiente or {}).get(chave) or padrao
    return valor if valor.startswith("http") else f"http://{valor}"


def http(url: str, corpo: dict):
    pedido = urllib.request.Request(
        url, data=json.dumps(corpo).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(pedido, timeout=TEMPO_DA_CHAMADA) as resposta:
        return json.loads(resposta.read().decode("utf-8"))


class Banco:
    def __init__(self, ambiente: dict):
        self.ambiente = ambiente or {}
        self.base = endereco(self.ambiente, CHAVE_DO_BANCO, BANCO_PADRAO)
        self.modelo = endereco(self.ambiente, CHAVE_DO_SERVIDOR_DE_MODELO,
                               SERVIDOR_DE_MODELO_PADRAO)
        self.vetores = {}

    def vetor(self, pergunta: str) -> list:
        if pergunta not in self.vetores:
            dito = http(self.modelo + CAMINHO_DO_VETOR, {
                "model": self.ambiente.get(CHAVE_DO_MODELO) or MODELO_PADRAO,
                "prompt": pergunta})
            self.vetores[pergunta] = dito.get("embedding") or []
        return self.vetores[pergunta]

    def colecoes(self) -> list:
        return [c for c in http(self.base + CAMINHO_DAS_COLECOES, {})
                .get("data") or [] if c.startswith(PREFIXO_DA_COLECAO)]

    def caminho_de(self, colecao: str) -> str:
        dito = http(self.base + CAMINHO_DA_DESCRICAO,
                    {"collectionName": colecao}).get("data") or {}
        return caminho_da_descricao(dito.get("description") or "")

    def quantos_trechos(self, colecao: str) -> int:
        dito = http(self.base + CAMINHO_DA_CONTAGEM,
                    {"collectionName": colecao}).get("data") or {}
        return int(dito.get("rowCount") or 0)

    def alvos_indexados(self) -> list:
        achados = []
        for colecao in self.colecoes():
            caminho = self.caminho_de(colecao) or colecao
            achados.append((caminho, colecao, self.quantos_trechos(colecao)))
        return sorted(achados)

    def buscar(self, pergunta: str, colecao: str, quantos: int,
               hibrida: bool) -> list:
        vetor = self.vetor(pergunta)
        if hibrida:
            dito = http(self.base + CAMINHO_DA_BUSCA_HIBRIDA,
                        pedido_hibrido(vetor, pergunta, colecao, quantos))
        else:
            dito = http(self.base + CAMINHO_DA_BUSCA_DENSA,
                        pedido_denso(vetor, colecao, quantos))
        return dito.get("data") or []

    def amostra(self, colecao: str) -> list:
        dito = http(self.base + CAMINHO_DA_CONSULTA, {
            "collectionName": colecao, "filter": FILTRO_DE_TUDO,
            "limit": TETO_DE_TRECHOS_NA_AMOSTRA,
            "outputFields": CAMPOS_QUE_VOLTAM + ["id"]})
        return sorted(dito.get("data") or [], key=lambda t: t.get("id", ""))


def caminho_da_descricao(descricao: str) -> str:
    if not descricao.startswith(MARCA_DO_CAMINHO_NA_DESCRICAO):
        return ""
    return descricao[len(MARCA_DO_CAMINHO_NA_DESCRICAO):].strip()


def pedido_denso(vetor: list, colecao: str, quantos: int) -> dict:
    return {"collectionName": colecao, "data": [vetor],
            "annsField": CAMPO_DO_VETOR_DENSO, "limit": quantos,
            "outputFields": CAMPOS_QUE_VOLTAM}


def pedido_hibrido(vetor: list, pergunta: str, colecao: str,
                   quantos: int) -> dict:
    funil = quantos * FUNIL_DA_FUSAO
    return {"collectionName": colecao,
            "search": [{"data": [vetor], "annsField": CAMPO_DO_VETOR_DENSO,
                        "limit": funil},
                       {"data": [pergunta], "annsField": CAMPO_DO_VETOR_ESPARSO,
                        "limit": funil}],
            "rerank": FUSAO, "limit": quantos,
            "outputFields": CAMPOS_QUE_VOLTAM}


def mesmo_alvo(pedido: str, caminho: str) -> bool:
    if not pedido:
        return True
    absoluto = str(Path(pedido).expanduser().resolve())
    return caminho == absoluto or caminho.endswith("/" + pedido.strip("/"))


def escolher_alvos(indexados: list, pedido: str) -> list:
    return [a for a in indexados if mesmo_alvo(pedido, a[0])]


def uma_linha(texto: str) -> str:
    return " ".join((texto or "").split())[:LETRAS_DO_TRECHO]


def buscar(pergunta: str, dado: dict, alvo: str = "",
           quantos: int = QUANTOS_POR_PADRAO, hibrida: bool = True) -> int:
    if not (pergunta or "").strip():
        print(RECUSA_SEM_PERGUNTA, file=sys.stderr)
        return 2
    banco = Banco(dado.get(CAMPO_DO_AMBIENTE))
    try:
        indexados = banco.alvos_indexados()
    except (urllib.error.URLError, OSError, ValueError) as erro:
        print(FALHOU_A_CHAMADA.format(banco.base, erro), file=sys.stderr)
        return 2
    if not indexados:
        print(NADA_INDEXADO.format(banco.base), file=sys.stderr)
        return 2
    alvos = escolher_alvos(indexados, alvo)
    if not alvos:
        print(RECUSA_ALVO_NAO_INDEXADO.format(
            alvo, "\n".join(f"  {c}" for c, _, _ in indexados)),
            file=sys.stderr)
        return 2
    print(CABECA.format(MODO_HIBRIDO if hibrida else MODO_DENSO, pergunta,
                        len(alvos)))
    achou = 0
    for caminho, colecao, trechos in alvos:
        if not trechos:
            print(VAZIA.format(caminho))
            continue
        try:
            achados = banco.buscar(pergunta, colecao, quantos, hibrida)
        except (urllib.error.URLError, OSError, ValueError) as erro:
            print(FALHOU_A_CHAMADA.format(caminho, erro), file=sys.stderr)
            continue
        if not achados:
            print(SEM_RESPOSTA.format(caminho))
            continue
        print(LINHA_DO_ALVO.format(caminho))
        for item in achados:
            achou += 1
            print(LINHA_DO_ACHADO.format(
                item.get("distance", 0.0), item.get("relativePath", "?"),
                item.get("startLine", "?")))
            print(LINHA_DO_TRECHO.format(uma_linha(item.get("content"))))
    if achou:
        print(RODAPE)
    return 0 if achou else 1


def frequencia_dos_termos(trechos: list) -> dict:
    contagem = {}
    for trecho in trechos:
        for termo in set(t.lower() for t in TERMO.findall(
                trecho.get("content") or "")):
            contagem[termo] = contagem.get(termo, 0) + 1
    return contagem


def termo_unico_do_trecho(trecho: dict, frequencia: dict) -> str:
    candidatos = {t for t in TERMO.findall(trecho.get("content") or "")
                  if frequencia.get(t.lower()) == 1}
    if not candidatos:
        return ""
    return max(candidatos, key=lambda t: (
        any(l in t for l in LETRAS_QUE_MARCAM_NOME), len(t), t))


def perguntas_da_amostra(trechos: list, quantas: int) -> list:
    frequencia = frequencia_dos_termos(trechos)
    passo = max(1, len(trechos) // quantas) if trechos else 1
    perguntas = []
    for trecho in trechos[::passo]:
        termo = termo_unico_do_trecho(trecho, frequencia)
        if termo:
            perguntas.append((termo, trecho.get("relativePath"),
                              trecho.get("startLine")))
        if len(perguntas) == quantas:
            break
    return perguntas


def posicao_do_alvo(achados: list, endereco_certo: tuple) -> int:
    for posicao, item in enumerate(achados, start=1):
        if (item.get("relativePath"), item.get("startLine")) == endereco_certo:
            return posicao
    return 0


def placar_vazio() -> dict:
    return {"perguntas": 0, "topo": {False: 0, True: 0},
            "tres": {False: 0, True: 0}, "chamadas": 0, "ruido": 0}


def somar_no_placar(placar: dict, posicoes: dict) -> None:
    placar["perguntas"] += 1
    for hibrida, vistas in posicoes.items():
        placar["chamadas"] += len(vistas)
        placar["ruido"] += len(set(vistas)) - 1
        primeira = vistas[0]
        placar["topo"][hibrida] += 1 if primeira == TOPO else 0
        placar["tres"][hibrida] += 1 if 0 < primeira <= TRES_PRIMEIROS else 0


def hibrido_vence_ou_empata(placar: dict) -> list:
    perdas = []
    for medida in ("topo", "tres"):
        if placar[medida][True] < placar[medida][False]:
            perdas.append(medida)
    return perdas


def medir_o_placar(banco: Banco, alvos: list) -> tuple:
    total, por_alvo = placar_vazio(), []
    for caminho, colecao, trechos in alvos:
        if not trechos:
            continue
        perguntas = perguntas_da_amostra(banco.amostra(colecao),
                                         PERGUNTAS_POR_ALVO)
        placar = placar_vazio()
        for termo, arquivo, linha in perguntas:
            posicoes = {}
            for hibrida in (False, True):
                posicoes[hibrida] = [
                    posicao_do_alvo(
                        banco.buscar(termo, colecao, TRES_PRIMEIROS, hibrida),
                        (arquivo, linha))
                    for _ in range(REPETICOES)]
            somar_no_placar(placar, posicoes)
            somar_no_placar(total, posicoes)
        por_alvo.append((caminho, placar))
    return total, por_alvo


def linha_do_placar(molde: str, rotulo: str, placar: dict) -> str:
    n = placar["perguntas"]
    return molde.format(rotulo[-52:], n, placar["topo"][False],
                        placar["topo"][True], placar["tres"][False],
                        placar["tres"][True])


def medir(dado: dict, alvo: str = "") -> tuple:
    banco = Banco(dado.get(CAMPO_DO_AMBIENTE))
    try:
        alvos = escolher_alvos(banco.alvos_indexados(), alvo)
        total, por_alvo = medir_o_placar(banco, alvos)
    except (urllib.error.URLError, OSError, ValueError) as erro:
        print(NAO_MEDIDO.format(erro))
        return None, []
    print(CABECA_DA_MEDICAO.format(total["perguntas"], REPETICOES))
    print(LINHA_DA_MEDICAO.format("alvo", "", "denso", "híbr.", "denso",
                                  "híbr."))
    for caminho, placar in por_alvo:
        print(linha_do_placar(LINHA_DA_MEDICAO, caminho, placar)
              if placar["perguntas"] else SEM_PERGUNTA_NA_AMOSTRA.format(
                  caminho[-52:]))
    print(linha_do_placar(TOTAL_DA_MEDICAO, "TOTAL", total))
    print(RUIDO_DA_MEDICAO.format(total["ruido"], total["chamadas"]))
    perdas = hibrido_vence_ou_empata(total)
    print(VEREDITO_DA_MEDICAO.format(
        HIBRIDO_VENCE_OU_EMPATA if not perdas
        else HIBRIDO_PERDE.format(", ".join(perdas))))
    return total, por_alvo


def testar() -> int:
    import tempfile

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
        acervo = raiz / "acervo"
        acervo.mkdir()

        esperado = (PREFIXO_DA_COLECAO
                    + hashlib.md5(str(acervo.resolve()).encode()
                                  ).hexdigest()[:LETRAS_DO_RESUMO])
        caso("o nome da coleção sai do md5 do caminho ABSOLUTO — medido "
             "contra o banco real, e é o que liga alvo a coleção",
             colecao_do_alvo(str(acervo)) == esperado)
        caso("o caminho indexado sai da descrição que o servidor grava na "
             "coleção — é assim que o buscador descobre o acervo sem "
             "arquivo local",
             caminho_da_descricao("codebasePath:/x/y ") == "/x/y"
             and caminho_da_descricao("outra coisa") == "")

        indexados = [("/a/conhecimento", "c1", 10), ("/a/skills", "c2", 3),
                     ("/b/memory", "c3", 0)]
        caso("sem --alvo, todo alvo indexado entra na busca",
             escolher_alvos(indexados, "") == indexados)
        caso("--alvo bate com o caminho absoluto ou com o fim do caminho",
             escolher_alvos(indexados, "skills") == [indexados[1]]
             and escolher_alvos(indexados, "/a/conhecimento")
             == [indexados[0]])
        caso("--alvo que não está indexado não bate com nada — a recusa diz "
             "o que existe, em vez de devolver vazio calado",
             escolher_alvos(indexados, "fantasma") == [])

        pedido = pedido_hibrido([0.1, 0.2], "termo raro", "c1", 5)
        caso("o pedido híbrido leva o vetor no campo denso e a pergunta em "
             "texto cru no esparso, fundidos por RRF — é o que o servidor "
             "MCP fazia, agora por REST",
             pedido["search"][0]["annsField"] == CAMPO_DO_VETOR_DENSO
             and pedido["search"][1]["data"] == ["termo raro"]
             and pedido["search"][1]["annsField"] == CAMPO_DO_VETOR_ESPARSO
             and pedido["rerank"]["strategy"] == "rrf")
        caso("cada perna do híbrido pede mais do que o topo final, para a "
             "fusão ter o que reordenar",
             pedido["search"][0]["limit"] == 5 * FUNIL_DA_FUSAO
             and pedido["limit"] == 5)
        caso("o pedido denso é a busca de um campo só",
             pedido_denso([0.1], "c1", 3)["annsField"] == CAMPO_DO_VETOR_DENSO)

        caso("endereço sem esquema ganha http, e com esquema fica",
             endereco({}, CHAVE_DO_BANCO, "1.2.3.4:19530")
             == "http://1.2.3.4:19530"
             and endereco({CHAVE_DO_BANCO: "https://x"}, CHAVE_DO_BANCO, "y")
             == "https://x")
        caso("o ambiente declarado manda no endereço, nunca o código",
             endereco({CHAVE_DO_SERVIDOR_DE_MODELO: "127.0.0.1:9999"},
                      CHAVE_DO_SERVIDOR_DE_MODELO, "127.0.0.1:11434")
             == "http://127.0.0.1:9999")
        caso("trecho de várias linhas vira uma linha e é cortado",
             uma_linha("a\n  b\n\nc") == "a b c"
             and len(uma_linha("x" * 500)) == LETRAS_DO_TRECHO)

        trechos = [
            {"id": "1", "content": "o gancho vetar-andamento-em-arquivo recusa",
             "relativePath": "a.md", "startLine": 1},
            {"id": "2", "content": "a função corre roda o comando; recusa",
             "relativePath": "b.md", "startLine": 9},
            {"id": "3", "content": "recusa recusa", "relativePath": "c.md",
             "startLine": 2},
        ]
        frequencia = frequencia_dos_termos(trechos)
        caso("a pergunta por termo exato é o termo que aparece num trecho "
             "só — nome de gancho ou de função vence palavra comum",
             termo_unico_do_trecho(trechos[0], frequencia)
             == "vetar-andamento-em-arquivo"
             and termo_unico_do_trecho(trechos[1], frequencia) == "comando")
        caso("trecho sem termo único não vira pergunta: seria pergunta sem "
             "resposta conhecida",
             termo_unico_do_trecho(trechos[2], frequencia) == ""
             and len(perguntas_da_amostra(trechos, 8)) == 2)
        caso("a resposta conhecida é o endereço arquivo:linha do trecho",
             perguntas_da_amostra(trechos, 8)[0][1:] == ("a.md", 1))

        achados = [{"relativePath": "b.md", "startLine": 9},
                   {"relativePath": "a.md", "startLine": 1}]
        caso("a posição do alvo entre os achados é 1 no topo, 2 no segundo "
             "e 0 quando não veio",
             posicao_do_alvo(achados, ("b.md", 9)) == 1
             and posicao_do_alvo(achados, ("a.md", 1)) == 2
             and posicao_do_alvo(achados, ("z.md", 1)) == 0)

        placar = placar_vazio()
        somar_no_placar(placar, {False: [2, 2], True: [1, 1]})
        somar_no_placar(placar, {False: [0, 0], True: [3, 1]})
        caso("o placar conta acerto no topo e nos três primeiros por modo, "
             "e o ruído é a resposta que mudou entre repetições iguais",
             placar["topo"] == {False: 0, True: 1}
             and placar["tres"] == {False: 1, True: 2}
             and placar["ruido"] == 1 and placar["chamadas"] == 8)
        caso("híbrido que vence ou empata em tudo não tem perda",
             hibrido_vence_ou_empata(placar) == [])
        pior = placar_vazio()
        somar_no_placar(pior, {False: [1], True: [2]})
        caso("híbrido atrás do denso em qualquer medida é perda nomeada",
             hibrido_vence_ou_empata(pior) == ["topo"])

    total, _ = medir(configuracao("."))
    if total is not None and total["perguntas"]:
        caso("MEDIDO no banco desta máquina: o híbrido vence ou empata o "
             "denso puro no topo e nos três primeiros — senão ele não pode "
             "ser a porta normal",
             hibrido_vence_ou_empata(total) == [])

    print(f"{'OK' if not falhou else 'FALHOU'}: {passou + falhou} casos")
    return 1 if falhou else 0


def montar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=USO)
    parser.add_argument("pergunta", nargs="?", default="",
                        help="o que você quer achar, em linguagem natural ou "
                             "o termo exato")
    parser.add_argument("--alvo", default="",
                        help="busca só neste caminho indexado (padrão: todos "
                             "os que o banco tem)")
    parser.add_argument("--quantos", type=int, default=QUANTOS_POR_PADRAO,
                        help="trechos por alvo")
    parser.add_argument("--denso", action="store_true",
                        help="só o vetor denso, sem o termo exato — para "
                             "comparar")
    parser.add_argument("--medir", action="store_true",
                        help="mede denso contra híbrido em perguntas com "
                             "resposta conhecida, tiradas do próprio acervo")
    parser.add_argument("--cwd", default=".")
    parser.add_argument(BANDEIRA_DE_TESTE, action="store_true")
    return parser


def main() -> int:
    if BANDEIRA_DE_TESTE in sys.argv[1:]:
        return testar()
    a = montar_parser().parse_args()
    dado = configuracao(a.cwd)
    if a.medir:
        total, _ = medir(dado, a.alvo)
        return 0 if total is not None and not hibrido_vence_ou_empata(total) \
            else 1
    return buscar(a.pergunta, dado, a.alvo, a.quantos, not a.denso)


if __name__ == "__main__":
    sys.exit(main())
