import argparse
import json
import re
import sys
import tempfile
from datetime import date
from pathlib import Path

NAO_MEDIDO = "nao-medido"
NAO_COMPARAVEL = "nao-comparavel"
SUBIU = "subiu"
CAIU = "caiu"
IGUAL = "igual"
MUDOU = "mudou"
SITUACOES = (SUBIU, CAIU, IGUAL, MUDOU, NAO_COMPARAVEL)
LADO_ANTES = "antes"
LADO_DEPOIS = "depois"
AUSENTE = object()

PASTA_DE_SAIDA = "dados"
NOME_DO_ARQUIVO = "delta-{caso}-{de}-{ate}.json"
FONTE = ("scripts/comparar_retratos.py — delta folha a folha entre dois "
         "retratos datados do mesmo caso; ausente ou nao-medido num dos "
         "lados sai nao-comparavel, nunca zero")
CHAVES_DE_DATA = ("data", "data_do_retrato")
CHAVE_DO_NEGOCIO = "negocio"
CHAVES_DO_CABECALHO = CHAVES_DE_DATA + (CHAVE_DO_NEGOCIO,)
CHAVES_DE_IDENTIDADE = ("nome", "handle", "bairro")
CHAVES_DE_CODIGO = ("http", "rdap")
DATA_NO_NOME = re.compile(r"\d{4}-\d{2}-\d{2}")
CASAS_DO_DELTA = 2
CASAS_DO_PERCENTUAL = 1
LARGURA_DA_CELULA = 60
RETICENCIAS = "…"
VAZIO = "—"

MOTIVO_AUSENTE = "ausente em {}"
MOTIVO_NAO_MEDIDO = "nao-medido em {}"
MOTIVO_TIPOS = "tipos diferentes: {} antes, {} depois"
RETRATO_NAO_E_OBJETO = "retrato precisa ser um objeto JSON, veio {} em {}"
SEM_DATA = "retrato sem data em {}: nem chave {} nem AAAA-MM-DD no nome do arquivo"
DATA_ILEGIVEL = "data ilegivel em {}: {!r} nao e AAAA-MM-DD"
NEGOCIOS_DIFERENTES = "retratos de negocios diferentes nao se comparam: {!r} e {!r}"

TITULO_MD = "# Delta de {caso}: {de} a {ate}, {dias} dia(s)"
CABECALHO_MD = ("| campo | antes | depois | delta | situacao |",
                "| --- | --- | --- | --- | --- |")
LINHA_MD = "| {} | {} | {} | {} | {} |"
GRAVADO = "gravado: {}"


def e_numero(valor):
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def chave_de_identidade(lista):
    if not lista or not all(isinstance(item, dict) for item in lista):
        return None
    for chave in CHAVES_DE_IDENTIDADE:
        rotulos = [item.get(chave) for item in lista]
        if None not in rotulos and len(set(map(str, rotulos))) == len(lista):
            return chave
    return None


def folhas_da_lista(lista, prefixo):
    chave = chave_de_identidade(lista)
    achadas = {}
    for posicao, item in enumerate(lista):
        if chave:
            rotulo = item[chave]
            corpo = {nome: valor for nome, valor in item.items() if nome != chave}
        else:
            rotulo, corpo = posicao, item
        achadas.update(folhas(corpo, f"{prefixo}[{rotulo}]."))
    return achadas


def folhas(valor, prefixo=""):
    if isinstance(valor, dict):
        achadas = {}
        for chave, filho in valor.items():
            achadas.update(folhas(filho, f"{prefixo}{chave}."))
        return achadas
    if isinstance(valor, list):
        return folhas_da_lista(valor, prefixo[:-1])
    return {prefixo[:-1]: valor}


def nome_da_folha(campo):
    return campo.rsplit(".", 1)[-1]


def nao_comparavel(campo, antes, depois, motivo):
    return {"campo": campo,
            "antes": None if antes is AUSENTE else antes,
            "depois": None if depois is AUSENTE else depois,
            "delta": None, "variacao_pct": None,
            "situacao": NAO_COMPARAVEL, "motivo": motivo}


def comparar_numeros(campo, antes, depois):
    delta = depois - antes
    if isinstance(delta, float):
        delta = round(delta, CASAS_DO_DELTA)
    variacao = round(delta / antes * 100, CASAS_DO_PERCENTUAL) if antes else None
    situacao = SUBIU if delta > 0 else CAIU if delta < 0 else IGUAL
    return {"campo": campo, "antes": antes, "depois": depois, "delta": delta,
            "variacao_pct": variacao, "situacao": situacao}


def comparar_folha(campo, antes, depois):
    for lado, valor in ((LADO_ANTES, antes), (LADO_DEPOIS, depois)):
        if valor is AUSENTE:
            return nao_comparavel(campo, antes, depois, MOTIVO_AUSENTE.format(lado))
        if valor == NAO_MEDIDO:
            return nao_comparavel(campo, antes, depois, MOTIVO_NAO_MEDIDO.format(lado))
    numeros = (e_numero(antes), e_numero(depois))
    if all(numeros) and nome_da_folha(campo) not in CHAVES_DE_CODIGO:
        return comparar_numeros(campo, antes, depois)
    if any(numeros) and not all(numeros):
        motivo = MOTIVO_TIPOS.format(type(antes).__name__, type(depois).__name__)
        return nao_comparavel(campo, antes, depois, motivo)
    return {"campo": campo, "antes": antes, "depois": depois, "delta": None,
            "variacao_pct": None, "situacao": IGUAL if antes == depois else MUDOU}


def comparar(antes, depois):
    folhas_antes, folhas_depois = folhas(antes), folhas(depois)
    campos = list(folhas_antes) + [c for c in folhas_depois if c not in folhas_antes]
    return [comparar_folha(campo, folhas_antes.get(campo, AUSENTE),
                           folhas_depois.get(campo, AUSENTE))
            for campo in campos if campo not in CHAVES_DO_CABECALHO]


def ler_retrato(arquivo):
    with open(arquivo, encoding="utf-8") as origem:
        retrato = json.load(origem)
    if not isinstance(retrato, dict):
        raise SystemExit(RETRATO_NAO_E_OBJETO.format(type(retrato).__name__, arquivo))
    return retrato


def data_do(retrato, arquivo):
    texto = next((retrato[chave] for chave in CHAVES_DE_DATA
                  if isinstance(retrato.get(chave), str)), None)
    if texto is None:
        achada = DATA_NO_NOME.search(Path(arquivo).name)
        if not achada:
            raise SystemExit(SEM_DATA.format(arquivo, " ou ".join(CHAVES_DE_DATA)))
        texto = achada.group(0)
    try:
        return date.fromisoformat(texto)
    except ValueError:
        raise SystemExit(DATA_ILEGIVEL.format(arquivo, texto)) from None


def lados_em_ordem(arquivo_a, arquivo_b):
    lados = []
    for arquivo in (arquivo_a, arquivo_b):
        retrato = ler_retrato(arquivo)
        lados.append((data_do(retrato, arquivo), arquivo, retrato))
    lados.sort(key=lambda lado: lado[0])
    negocios = [lado[2].get(CHAVE_DO_NEGOCIO) for lado in lados]
    if all(negocios) and negocios[0] != negocios[1]:
        raise SystemExit(NEGOCIOS_DIFERENTES.format(*negocios))
    return lados


def montar_delta(caso, arquivo_a, arquivo_b):
    (de, arquivo_de, antes), (ate, arquivo_ate, depois) = lados_em_ordem(arquivo_a, arquivo_b)
    comparacoes = comparar(antes, depois)
    return {"fonte": FONTE, "caso": caso,
            "de": de.isoformat(), "ate": ate.isoformat(), "dias": (ate - de).days,
            "retratos": {LADO_ANTES: Path(arquivo_de).name,
                         LADO_DEPOIS: Path(arquivo_ate).name},
            "resumo": {situacao: sum(c["situacao"] == situacao for c in comparacoes)
                       for situacao in SITUACOES},
            "comparacoes": comparacoes}


def nome_do_arquivo(caso, de, ate):
    return NOME_DO_ARQUIVO.format(caso=caso, de=de, ate=ate)


def gravar(delta, pasta):
    destino = Path(pasta) / nome_do_arquivo(delta["caso"], delta["de"], delta["ate"])
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "w", encoding="utf-8") as saida:
        json.dump(delta, saida, ensure_ascii=False, indent=1)
    return destino


def numero_md(valor, com_sinal=False):
    texto = f"{valor:+}" if com_sinal and valor else f"{valor}"
    return texto.replace(".", ",")


def celula(valor):
    if valor is None:
        return VAZIO
    texto = numero_md(valor) if e_numero(valor) else str(valor)
    texto = " ".join(texto.split()).replace("|", "\\|")
    if len(texto) > LARGURA_DA_CELULA:
        texto = texto[:LARGURA_DA_CELULA - 1] + RETICENCIAS
    return texto


def delta_md(comparacao):
    if comparacao["situacao"] == NAO_COMPARAVEL:
        return comparacao["motivo"]
    if comparacao["delta"] is None:
        return VAZIO
    texto = numero_md(comparacao["delta"], com_sinal=True)
    if comparacao["variacao_pct"]:
        texto += f" ({numero_md(comparacao['variacao_pct'], com_sinal=True)}%)"
    return texto


def tabela_markdown(delta):
    linhas = [TITULO_MD.format(**delta), "", *CABECALHO_MD]
    for comparacao in delta["comparacoes"]:
        linhas.append(LINHA_MD.format(celula(comparacao["campo"]),
                                      celula(comparacao["antes"]),
                                      celula(comparacao["depois"]),
                                      delta_md(comparacao),
                                      comparacao["situacao"]))
    resumo = " | ".join(f"{situacao} {delta['resumo'][situacao]}"
                        for situacao in SITUACOES)
    return "\n".join(linhas + ["", resumo])


FIXTURE_ANTES = {
    "data": "2026-01-10", "negocio": "Loja Exemplo",
    "instagram": {"handle": "@lojaexemplo", "seguidores": 1000, "seguindo": 200,
                  "posts": 50, "seguidores_da_meta": 990, "estado": "vivo"},
    "google": {"nota": 4.5, "avaliacoes": 80, "http": 200},
    "facebook": {"seguidores": 300},
    "site": {"titulo": "Loja | Exemplo", "cta_whatsapp": None, "gerador": "construtor"},
    "renda": {"bairros": [{"bairro": "Centro", "razao_sobre_municipio": 1.2},
                          {"bairro": "Norte", "razao_sobre_municipio": 0.8}]},
    "concorrentes": [{"nome": "Rival A", "avaliacoes": 100},
                     {"nome": "Rival B", "avaliacoes": 10}],
    "destaques": ["promo", "horario"],
    "linktree": {"vivo": True},
    "reels": {"vistos": 0},
}
FIXTURE_DEPOIS = {
    "data": "2026-02-09", "negocio": "Loja Exemplo",
    "instagram": {"handle": "@lojaexemplo", "seguidores": 1100, "seguindo": 200,
                  "posts": NAO_MEDIDO, "seguidores_da_meta": "1 mil", "estado": "morto"},
    "google": {"nota": 4.4, "avaliacoes": 100, "http": 404},
    "site": {"titulo": "Loja | Exemplo", "cta_whatsapp": "https://wa.me/000",
             "gerador": "construtor"},
    "renda": {"bairros": [{"bairro": "Centro", "razao_sobre_municipio": 1.25},
                          {"bairro": "Sul", "razao_sobre_municipio": 0.9}]},
    "concorrentes": [{"nome": "Rival B", "avaliacoes": 12},
                     {"nome": "Rival A", "avaliacoes": 100}],
    "destaques": ["promo", "horario", "novo"],
    "linktree": {"vivo": False},
    "reels": {"vistos": 5},
    "youtube": {"inscritos": 40},
}
FIXTURE_OUTRO_NEGOCIO = {"data": "2026-02-09", "negocio": "Outra Loja"}
FIXTURE_SEM_DATA = {"negocio": "Loja Exemplo", "google": {"avaliacoes": 1}}
FIXTURE_DATA_ILEGIVEL = {"data": "2026-13-40", "negocio": "Loja Exemplo"}
CASO_DE_TESTE = "exemplo"


def por_campo(comparacoes):
    return {comparacao["campo"]: comparacao for comparacao in comparacoes}


def gravar_retrato(pasta, nome, retrato):
    caminho = Path(pasta) / nome
    caminho.write_text(json.dumps(retrato), encoding="utf-8")
    return str(caminho)


def recusa(funcao, *argumentos):
    try:
        funcao(*argumentos)
    except SystemExit:
        return True
    return False


def testar_numeros(caso, linhas):
    caso("seguidores que subiram saem com delta e percentual",
         linhas["instagram.seguidores"] == {
             "campo": "instagram.seguidores", "antes": 1000, "depois": 1100,
             "delta": 100, "variacao_pct": 10.0, "situacao": SUBIU})
    caso("nota que caiu sai com delta decimal arredondado",
         linhas["google.nota"]["delta"] == -0.1
         and linhas["google.nota"]["variacao_pct"] == -2.2
         and linhas["google.nota"]["situacao"] == CAIU)
    caso("avaliacoes que subiram calculam o percentual sobre o antes",
         linhas["google.avaliacoes"]["delta"] == 20
         and linhas["google.avaliacoes"]["variacao_pct"] == 25.0)
    caso("numero igual nos dois lados sai igual com delta zero",
         linhas["instagram.seguindo"]["situacao"] == IGUAL
         and linhas["instagram.seguindo"]["delta"] == 0)
    caso("antes zero nao divide: o percentual fica sem valor, nao zero",
         linhas["reels.vistos"]["delta"] == 5
         and linhas["reels.vistos"]["variacao_pct"] is None
         and linhas["reels.vistos"]["situacao"] == SUBIU)
    caso("razao de renda do bairro alinhado pelo nome sai com delta",
         linhas["renda.bairros[Centro].razao_sobre_municipio"]["delta"] == 0.05
         and linhas["renda.bairros[Centro].razao_sobre_municipio"]["variacao_pct"] == 4.2)
    caso("concorrente alinhado pelo nome compara mesmo com a ordem trocada",
         linhas["concorrentes[Rival B].avaliacoes"]["delta"] == 2
         and linhas["concorrentes[Rival A].avaliacoes"]["situacao"] == IGUAL)
    caso("a chave de identidade nao vira linha",
         "concorrentes[Rival A].nome" not in linhas
         and "renda.bairros[Centro].bairro" not in linhas)


def testar_nao_comparavel(caso, linhas):
    caso("campo ausente num dos lados sai nao-comparavel, nunca zero",
         linhas["facebook.seguidores"] == {
             "campo": "facebook.seguidores", "antes": 300, "depois": None,
             "delta": None, "variacao_pct": None, "situacao": NAO_COMPARAVEL,
             "motivo": "ausente em depois"}
         and linhas["youtube.inscritos"]["motivo"] == "ausente em antes"
         and linhas["youtube.inscritos"]["delta"] is None)
    caso("nao-medido num dos lados sai nao-comparavel com o lado no motivo",
         linhas["instagram.posts"]["situacao"] == NAO_COMPARAVEL
         and linhas["instagram.posts"]["motivo"] == "nao-medido em depois"
         and linhas["instagram.posts"]["delta"] is None)
    caso("numero contra texto e nao-comparavel: a leitura mudou, nao o valor",
         linhas["instagram.seguidores_da_meta"]["situacao"] == NAO_COMPARAVEL
         and linhas["instagram.seguidores_da_meta"]["motivo"]
         == "tipos diferentes: int antes, str depois")
    caso("bairro e item de lista que so existem num lado saem nao-comparavel",
         linhas["renda.bairros[Norte].razao_sobre_municipio"]["motivo"] == "ausente em depois"
         and linhas["renda.bairros[Sul].razao_sobre_municipio"]["motivo"] == "ausente em antes"
         and linhas["destaques[2]"]["motivo"] == "ausente em antes")


def testar_categoricos(caso, linhas):
    caso("estado de link que mudou sai mudou, sem delta",
         linhas["instagram.estado"]["situacao"] == MUDOU
         and linhas["instagram.estado"]["delta"] is None)
    caso("codigo HTTP muda, nao soma",
         linhas["google.http"]["situacao"] == MUDOU
         and linhas["google.http"]["delta"] is None)
    caso("booleano nao e numero: vivo que virou morto sai mudou",
         linhas["linktree.vivo"]["situacao"] == MUDOU
         and linhas["linktree.vivo"]["delta"] is None)
    caso("nulo que ganhou valor sai mudou",
         linhas["site.cta_whatsapp"]["situacao"] == MUDOU)
    caso("texto igual e item de lista igual saem igual",
         linhas["site.gerador"]["situacao"] == IGUAL
         and linhas["destaques[0]"]["situacao"] == IGUAL)
    caso("data e negocio sao cabecalho, nao linha",
         "data" not in linhas and "negocio" not in linhas)
    caso("lista de objetos sem nome unico se alinha pela posicao",
         "duplos[1].n" in por_campo(comparar(
             {"duplos": [{"nome": "x", "n": 1}, {"nome": "x", "n": 2}]},
             {"duplos": [{"nome": "x", "n": 1}, {"nome": "x", "n": 3}]})))


def testar_fronteiras(caso, pasta):
    antes = gravar_retrato(pasta, "retrato-exemplo-2026-01-10.json", FIXTURE_ANTES)
    depois = gravar_retrato(pasta, "retrato-exemplo-2026-02-09.json", FIXTURE_DEPOIS)
    delta = montar_delta(CASO_DE_TESTE, antes, depois)
    caso("o delta e datado pelos dois retratos e conta os dias entre eles",
         delta["de"] == "2026-01-10" and delta["ate"] == "2026-02-09"
         and delta["dias"] == 30 and delta["fonte"] == FONTE
         and delta["retratos"] == {"antes": "retrato-exemplo-2026-01-10.json",
                                   "depois": "retrato-exemplo-2026-02-09.json"})
    caso("a ordem dos argumentos nao importa: a data manda",
         montar_delta(CASO_DE_TESTE, depois, antes) == delta)
    caso("o resumo conta cada situacao e fecha com o total de linhas",
         sum(delta["resumo"].values()) == len(delta["comparacoes"])
         and delta["resumo"][NAO_COMPARAVEL] == 7)
    mesmo = montar_delta(CASO_DE_TESTE, antes, antes)
    caso("retrato contra ele mesmo e delta zero: tudo igual, nada nao-comparavel",
         mesmo["dias"] == 0
         and all(c["situacao"] == IGUAL for c in mesmo["comparacoes"])
         and all(c["delta"] in (0, None) for c in mesmo["comparacoes"]))
    destino = gravar(delta, Path(pasta) / "saida")
    caso("o arquivo gravado leva caso e as duas datas no nome e le de volta igual",
         destino.name == "delta-exemplo-2026-01-10-2026-02-09.json"
         and json.loads(destino.read_text(encoding="utf-8")) == delta)
    caso("retratos de negocios diferentes sao recusados",
         recusa(montar_delta, CASO_DE_TESTE, antes,
                gravar_retrato(pasta, "retrato-outro-2026-02-09.json", FIXTURE_OUTRO_NEGOCIO)))
    sem_data = gravar_retrato(pasta, "retrato-exemplo-2026-03-01.json", FIXTURE_SEM_DATA)
    caso("retrato sem chave de data usa a data do nome do arquivo",
         data_do(FIXTURE_SEM_DATA, sem_data) == date(2026, 3, 1))
    caso("retrato sem data em lugar nenhum, ou com data ilegivel, e recusado",
         recusa(data_do, FIXTURE_SEM_DATA, gravar_retrato(pasta, "retrato.json", FIXTURE_SEM_DATA))
         and recusa(data_do, FIXTURE_DATA_ILEGIVEL, "retrato.json"))
    caso("retrato que nao e objeto JSON e recusado",
         recusa(ler_retrato, gravar_retrato(pasta, "lista.json", [1, 2])))
    return delta


def testar_markdown(caso, delta):
    tabela = tabela_markdown(delta)
    linhas = tabela.splitlines()
    caso("a tabela abre com o titulo datado e o cabecalho",
         linhas[0] == "# Delta de exemplo: 2026-01-10 a 2026-02-09, 30 dia(s)"
         and linhas[2:4] == list(CABECALHO_MD))
    caso("a tabela tem uma linha por comparacao",
         sum(linha.startswith("| ") for linha in linhas) - 2 == len(delta["comparacoes"]))
    caso("delta e percentual saem com sinal e virgula decimal",
         "| renda.bairros[Centro].razao_sobre_municipio | 1,2 | 1,25 | +0,05 (+4,2%) | subiu |" in linhas
         and "| instagram.seguindo | 200 | 200 | 0 | igual |" in linhas)
    caso("ausente e nao-medido levam o motivo na coluna do delta",
         "| facebook.seguidores | 300 | — | ausente em depois | nao-comparavel |" in linhas
         and "| instagram.posts | 50 | nao-medido | nao-medido em depois | nao-comparavel |" in linhas)
    caso("barra vertical no valor e escapada e o resumo fecha a tabela",
         "Loja \\| Exemplo" in tabela
         and linhas[-1].startswith("subiu ") and "nao-comparavel 7" in linhas[-1])
    caso("celula comprida e cortada com reticencias",
         celula("x" * 80).endswith(RETICENCIAS) and len(celula("x" * 80)) == LARGURA_DA_CELULA)


def testar():
    casos, falhas = [], []

    def caso(nome, deu_certo):
        casos.append(nome)
        if not deu_certo:
            falhas.append(nome)

    linhas = por_campo(comparar(FIXTURE_ANTES, FIXTURE_DEPOIS))
    testar_numeros(caso, linhas)
    testar_nao_comparavel(caso, linhas)
    testar_categoricos(caso, linhas)
    with tempfile.TemporaryDirectory() as pasta:
        delta = testar_fronteiras(caso, pasta)
    testar_markdown(caso, delta)
    for nome in falhas:
        print(f"CAIU: {nome}")
    if falhas:
        print(f"FALHOU: {len(falhas)} de {len(casos)} casos")
        return 1
    print(f"OK: {len(casos)} casos")
    return 0


def principal():
    if "--testar" in sys.argv[1:]:
        return testar()
    parser = argparse.ArgumentParser(
        description="Delta entre dois retratos datados do mesmo caso, folha a "
                    "folha: seguidores, avaliacoes, razoes de renda, links "
                    "vivos ou mortos. Grava o JSON e imprime a tabela "
                    "Markdown. Ausente ou nao-medido num dos lados sai "
                    "nao-comparavel, nunca zero.")
    parser.add_argument("--antes", required=True,
                        help="retrato datado de uma rodada; a data corrige a ordem")
    parser.add_argument("--depois", required=True,
                        help="retrato datado da outra rodada, do mesmo caso")
    parser.add_argument("--caso", required=True, help="nome do caso, vai no nome do arquivo")
    parser.add_argument("--saida-dir", default=PASTA_DE_SAIDA)
    args = parser.parse_args()
    delta = montar_delta(args.caso, args.antes, args.depois)
    destino = gravar(delta, args.saida_dir)
    print(tabela_markdown(delta))
    print(GRAVADO.format(destino), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(principal())
