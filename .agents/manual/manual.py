import argparse
import html
import io
import re
import sys
import unicodedata
from contextlib import redirect_stdout
from pathlib import Path

BANDEIRA_DE_TESTE = "--testar"
USO = ("gera o manual do atlas num arquivo HTML só, a partir das páginas de "
       "conhecimento/: abre com duplo clique, sem servidor e sem rede")

DESTINO = "manual.html"
PASTA_DAS_PAGINAS = "conhecimento"
PAGINA_DA_RECEITA = "execucoes/LEIAME.md"
ABERTURA = ("conhecimento/LEIAME.md", "conhecimento/mapa-do-repositorio.md")
COPIAS_SEM_MARCA = {
    PAGINA_DA_RECEITA: "modulos/encadeador/execucoes/LEIAME.md",
}

TITULO_DO_MANUAL = "O manual do atlas"
CHAMADA = ("Um arquivo só, gerado das páginas de <code>conhecimento/</code> "
           "por <code>python3 .agents/manual/manual.py --escrever</code>. "
           "Editar este HTML é trabalho perdido: a próxima geração o "
           "reescreve.")
SECAO_DAS_PERGUNTAS = "O que este manual responde"
SECAO_DOS_COMANDOS = "Os comandos do dia a dia"
SECAO_DAS_PAGINAS = "As páginas, inteiras"

PERGUNTAS = (
    ("O que cada pasta é", "As pastas, uma linha cada"),
    ("O que ali não se edita porque é regenerado, e qual é a fonte",
     "Fonte e cópia: edite sempre a fonte"),
    ("A receita do executor de roteiros",
     "A receita do disparo, em linhas copiáveis"),
    ("Os comandos do dia a dia", SECAO_DOS_COMANDOS),
)

LINGUAGEM_DOS_COMANDOS = "bash"
SELO_COM_MARCA = ("Gerada de <code>{}</code> — não edite esta página, edite "
                  "a fonte.")
SELO_POR_CAMINHO = ("Cópia gerada de <code>{}</code> — não edite esta "
                    "página, edite a fonte.")

MARCA_DE_GERADO = re.compile(r"^<!--\s*GERAD[AO] de (\S+)")
TITULO_MD = re.compile(r"^(#{1,6})\s+(.*)$")
ITEM_MD = re.compile(r"^(?:[-*]|\d+\.)\s+(.*)$")
ITEM_ORDENADO_MD = re.compile(r"^\d+\.\s")
CERCA_MD = re.compile(r"^```(\w*)\s*$")
CODIGO_MD = re.compile(r"`([^`]+)`")
NEGRITO_MD = re.compile(r"\*\*([^*]+)\*\*")
ITALICO_MD = re.compile(r"(?<!\*)\*(?!\*)([^*]+)\*(?!\*)")
LINK_MD = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
NAO_ANCORAVEL = re.compile(r"[^a-z0-9]+")

SINAIS_DE_REDE = ("src=", 'href="http', "@import", "<script", "<link",
                  "url(http")

ESCRITO = "manual escrito em {} — {} páginas, {} comandos, {} KB"
EM_DIA = "manual em dia — {} bate com as {} páginas de origem"
DIVERGIU = ("manual DESATUALIZADO: {} não bate com as páginas de origem. "
            "Rode `python3 .agents/manual/manual.py --escrever`.")
SEM_MANUAL = ("manual NÃO ESCRITO: {} não existe. Rode `python3 "
              ".agents/manual/manual.py --escrever`.")
ERRO_SEM_PAGINAS = "erro de uso: nenhuma página em {}/*.md"
ERRO_SEM_ANCORA = ("erro de fronteira: a pergunta {!r} aponta para a seção "
                   "{!r}, que nenhuma página do manual tem. Corrija a "
                   "PERGUNTAS ou a página.")
ERRO_DE_AMBIENTE = "erro de ambiente: {}"

TESTE_FALHA = "FALHOU: {}"
TESTE_RESUMO_FALHA = "FALHOU: {} de {} casos"
TESTE_RESUMO_OK = "OK: {} casos"

ESTILO = """
:root{--tinta:#1c1c1c;--fraca:#5b5b5b;--papel:#fdfcfa;--borda:#dcd7cf;
--realce:#7a3e12;--caixa:#f4f1ec}
*{box-sizing:border-box}
body{margin:0;background:var(--papel);color:var(--tinta);
font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
font-size:16px;line-height:1.6}
.folha{max-width:1180px;margin:0 auto;padding:0 24px 80px;
display:grid;grid-template-columns:250px 1fr;gap:40px}
header{grid-column:1/-1;padding:36px 0 8px;border-bottom:2px solid var(--tinta)}
header h1{margin:0 0 8px;font-size:2rem;letter-spacing:-.02em}
header p{margin:0;color:var(--fraca);max-width:60ch}
nav{position:sticky;top:0;align-self:start;padding-top:28px;
max-height:100vh;overflow:auto;font-size:.9rem}
nav h2{font-size:.75rem;text-transform:uppercase;letter-spacing:.08em;
color:var(--fraca);margin:20px 0 8px}
nav ol{list-style:none;margin:0;padding:0}
nav li{margin:0 0 6px}
nav a{color:var(--tinta);text-decoration:none;border-left:2px solid var(--borda);
padding-left:10px;display:block}
nav a:hover{border-left-color:var(--realce);color:var(--realce)}
main{min-width:0;padding-top:28px}
section{margin:0 0 52px;scroll-margin-top:16px}
h2{font-size:1.5rem;margin:0 0 14px;padding-bottom:6px;
border-bottom:1px solid var(--borda)}
h3{font-size:1.15rem;margin:30px 0 10px}
h4{font-size:1rem;margin:22px 0 8px;color:var(--fraca)}
p{margin:0 0 14px;max-width:74ch}
ul,ol{margin:0 0 14px;padding-left:24px;max-width:74ch}
li{margin:0 0 6px}
code{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
font-size:.88em;background:var(--caixa);padding:1px 4px;border-radius:3px}
pre{background:var(--caixa);border:1px solid var(--borda);border-radius:4px;
padding:12px 14px;overflow:auto;margin:0 0 14px}
pre code{background:none;padding:0;font-size:.85rem;line-height:1.5}
table{border-collapse:collapse;margin:0 0 16px;width:100%;font-size:.92rem}
th,td{border:1px solid var(--borda);padding:7px 10px;text-align:left;
vertical-align:top}
th{background:var(--caixa)}
a{color:var(--realce)}
.selo{background:#fff6e8;border-left:3px solid var(--realce);padding:8px 12px;
margin:0 0 16px;font-size:.9rem;color:var(--realce)}
.origem{font-size:.8rem;color:var(--fraca);margin:0 0 6px}
.pergunta{font-weight:600}
@media(max-width:900px){.folha{grid-template-columns:1fr}
nav{position:static;max-height:none}}
"""


def ancorar(texto: str) -> str:
    cru = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore")
    return NAO_ANCORAVEL.sub("-", cru.decode("ascii").lower()).strip("-")


def alvo_do_link(destino: str, ancoras: dict) -> str:
    return ancoras.get(destino.split("#")[0], "")


def em_texto(cru: str, ancoras: dict) -> str:
    saida = html.escape(cru)

    def link(achado):
        rotulo = achado.group(1)
        destino = achado.group(2)
        if (ancora := alvo_do_link(destino, ancoras)):
            return f'<a href="#{ancora}">{rotulo}</a>'
        return f"{rotulo} (<code>{destino}</code>)"

    saida = LINK_MD.sub(link, saida)
    saida = NEGRITO_MD.sub(r"<strong>\1</strong>", saida)
    return ITALICO_MD.sub(r"<em>\1</em>", saida)


def em_linha(cru: str, ancoras: dict) -> str:
    pedacos = CODIGO_MD.split(cru)
    return "".join(f"<code>{html.escape(p)}</code>" if impar % 2
                   else em_texto(p, ancoras)
                   for impar, p in enumerate(pedacos))


def celulas(linha: str) -> list:
    return [c.strip() for c in linha.strip().strip("|").split("|")]


def em_tabela(linhas: list, ancoras: dict) -> str:
    cabecalho = celulas(linhas[0])
    corpo = [celulas(ln) for ln in linhas[2:]]
    saida = ["<table>", "<thead><tr>"]
    saida += [f"<th>{em_linha(c, ancoras)}</th>" for c in cabecalho]
    saida.append("</tr></thead><tbody>")
    for fila in corpo:
        saida.append("<tr>")
        saida += [f"<td>{em_linha(c, ancoras)}</td>" for c in fila]
        saida.append("</tr>")
    saida.append("</tbody></table>")
    return "".join(saida)


def itens_da_lista(linhas: list) -> list:
    itens = []
    for linha in linhas:
        recuo = len(linha) - len(linha.lstrip())
        if (achado := ITEM_MD.match(linha.strip())):
            itens.append([recuo, achado.group(1)])
        elif itens:
            itens[-1][1] += " " + linha.strip()
    return itens


def em_lista(linhas: list, ancoras: dict) -> str:
    marca = "ol" if ITEM_ORDENADO_MD.match(linhas[0].strip()) else "ul"
    raso = min(recuo for recuo, _ in itens_da_lista(linhas))
    saida = [f"<{marca}>"]
    aninhado = False
    for recuo, texto in itens_da_lista(linhas):
        if recuo > raso and not aninhado:
            saida.append("<ul>")
            aninhado = True
        elif recuo == raso and aninhado:
            saida.append("</ul>")
            aninhado = False
        saida.append(f"<li>{em_linha(texto, ancoras)}</li>")
    if aninhado:
        saida.append("</ul>")
    saida.append(f"</{marca}>")
    return "".join(saida)


def e_estrutura(linha: str) -> bool:
    return (not linha.strip() or TITULO_MD.match(linha)
            or CERCA_MD.match(linha) or linha.strip().startswith("|")
            or bool(ITEM_MD.match(linha.strip())))


def ate_o_fim_do_bloco(linhas: list, inicio: int, ainda_do_bloco) -> int:
    fim = inicio
    while fim < len(linhas) and ainda_do_bloco(linhas[fim]):
        fim += 1
    return fim


def titulos_da_pagina(texto: str) -> list:
    return [achado.group(2) for linha in texto.splitlines()
            if (achado := TITULO_MD.match(linha)) and len(achado.group(1)) > 1]


def selo_da_pagina(rel: str, texto: str) -> str:
    if (achado := MARCA_DE_GERADO.match(texto.lstrip())):
        return SELO_COM_MARCA.format(achado.group(1))
    if rel in COPIAS_SEM_MARCA:
        return SELO_POR_CAMINHO.format(COPIAS_SEM_MARCA[rel])
    return ""


def converter(texto: str, ancoras: dict, comandos: list, origem: str) -> str:
    linhas = texto.splitlines()
    saida = []
    i = 0
    while i < len(linhas):
        linha = linhas[i]
        if not linha.strip() or MARCA_DE_GERADO.match(linha):
            i += 1
        elif (achado := TITULO_MD.match(linha)):
            nivel = min(len(achado.group(1)) + 1, 6)
            rotulo = achado.group(2)
            if nivel > 2:
                saida.append(f'<h{nivel} id="{ancorar(rotulo)}">'
                             f"{em_linha(rotulo, ancoras)}</h{nivel}>")
            i += 1
        elif (cerca := CERCA_MD.match(linha)):
            fim = ate_o_fim_do_bloco(linhas, i + 1,
                                     lambda ln: not CERCA_MD.match(ln))
            corpo = "\n".join(linhas[i + 1:fim])
            if cerca.group(1) == LINGUAGEM_DOS_COMANDOS:
                comandos.append((origem, corpo))
            saida.append(f"<pre><code>{html.escape(corpo)}</code></pre>")
            i = fim + 1
        elif linha.strip().startswith("|"):
            fim = ate_o_fim_do_bloco(
                linhas, i, lambda ln: ln.strip().startswith("|"))
            saida.append(em_tabela(linhas[i:fim], ancoras))
            i = fim
        elif ITEM_MD.match(linha.strip()):
            fim = ate_o_fim_do_bloco(
                linhas, i, lambda ln: bool(ln.strip())
                and (ITEM_MD.match(ln.strip()) or ln.startswith(" ")))
            saida.append(em_lista(linhas[i:fim], ancoras))
            i = fim
        else:
            fim = ate_o_fim_do_bloco(linhas, i,
                                     lambda ln: not e_estrutura(ln))
            junto = " ".join(ln.strip() for ln in linhas[i:fim])
            saida.append(f"<p>{em_linha(junto, ancoras)}</p>")
            i = fim
    return "\n".join(saida)


def paginas_do_disco(raiz: Path) -> list:
    pasta = raiz / PASTA_DAS_PAGINAS
    todas = sorted(f"{PASTA_DAS_PAGINAS}/{p.name}" for p in pasta.glob("*.md"))
    ordenadas = [rel for rel in ABERTURA if rel in todas]
    ordenadas += [rel for rel in todas if rel not in ordenadas]
    if (raiz / PAGINA_DA_RECEITA).is_file():
        ordenadas.append(PAGINA_DA_RECEITA)
    return ordenadas


def ler_paginas(raiz: Path) -> list:
    lidas = []
    for rel in paginas_do_disco(raiz):
        texto = (raiz / rel).read_text(encoding="utf-8")
        titulo = next((achado.group(2) for linha in texto.splitlines()
                       if (achado := TITULO_MD.match(linha))), rel)
        lidas.append({"rel": rel, "titulo": titulo, "texto": texto,
                      "ancora": ancorar(rel)})
    return lidas


def ancoras_das_paginas(paginas: list) -> dict:
    ancoras = {}
    for pagina in paginas:
        ancoras[pagina["rel"]] = pagina["ancora"]
        ancoras[pagina["rel"].rsplit("/", 1)[-1]] = pagina["ancora"]
    return ancoras


def ancoras_das_secoes(paginas: list) -> dict:
    das_secoes = {SECAO_DOS_COMANDOS: ancorar(SECAO_DOS_COMANDOS)}
    for pagina in paginas:
        for titulo in titulos_da_pagina(pagina["texto"]):
            das_secoes.setdefault(titulo, ancorar(titulo))
    return das_secoes


def bloco_das_perguntas(paginas: list) -> str:
    das_secoes = ancoras_das_secoes(paginas)
    saida = [f'<section id="{ancorar(SECAO_DAS_PERGUNTAS)}">',
             f"<h2>{SECAO_DAS_PERGUNTAS}</h2>", "<ul>"]
    for pergunta, secao in PERGUNTAS:
        if secao not in das_secoes:
            raise ValueError(ERRO_SEM_ANCORA.format(pergunta, secao))
        saida.append(f'<li><span class="pergunta">{pergunta}</span> — '
                     f'<a href="#{das_secoes[secao]}">{secao}</a></li>')
    saida += ["</ul>", "</section>"]
    return "\n".join(saida)


def bloco_dos_comandos(comandos: list, ancoras: dict) -> str:
    ancora = ancorar(SECAO_DOS_COMANDOS)
    saida = [f'<section id="{ancora}">',
             f"<h2>{SECAO_DOS_COMANDOS}</h2>",
             "<p>Todo bloco de comando das páginas, junto. A origem de cada "
             "um leva ao texto que o explica.</p>"]
    for origem, corpo in comandos:
        alvo = ancoras.get(origem, "")
        saida.append(f'<p class="origem"><a href="#{alvo}">{origem}</a></p>')
        saida.append(f"<pre><code>{html.escape(corpo)}</code></pre>")
    saida.append("</section>")
    return "\n".join(saida)


def bloco_do_indice(paginas: list) -> str:
    saida = ["<nav>", "<h2>O manual</h2>", "<ol>",
             f'<li><a href="#{ancorar(SECAO_DAS_PERGUNTAS)}">'
             f"{SECAO_DAS_PERGUNTAS}</a></li>",
             f'<li><a href="#{ancorar(SECAO_DOS_COMANDOS)}">'
             f"{SECAO_DOS_COMANDOS}</a></li>", "</ol>",
             f"<h2>{SECAO_DAS_PAGINAS}</h2>", "<ol>"]
    for pagina in paginas:
        saida.append(f'<li><a href="#{pagina["ancora"]}">'
                     f"{html.escape(pagina['titulo'])}</a></li>")
    saida += ["</ol>", "</nav>"]
    return "\n".join(saida)


def bloco_das_paginas(paginas: list, ancoras: dict, comandos: list) -> str:
    saida = []
    for pagina in paginas:
        saida.append(f'<section id="{pagina["ancora"]}">')
        saida.append(f"<h2>{html.escape(pagina['titulo'])}</h2>")
        saida.append(f'<p class="origem"><code>{pagina["rel"]}</code></p>')
        if (selo := selo_da_pagina(pagina["rel"], pagina["texto"])):
            saida.append(f'<p class="selo">{selo}</p>')
        saida.append(converter(pagina["texto"], ancoras, comandos,
                               pagina["rel"]))
        saida.append("</section>")
    return "\n".join(saida)


def montar(raiz: Path, comandos: list = None) -> str:
    paginas = ler_paginas(raiz)
    if not paginas:
        raise ValueError(ERRO_SEM_PAGINAS.format(PASTA_DAS_PAGINAS))
    ancoras = ancoras_das_paginas(paginas)
    comandos = [] if comandos is None else comandos
    corpo = bloco_das_paginas(paginas, ancoras, comandos)
    return "\n".join((
        "<!DOCTYPE html>", '<html lang="pt-BR">', "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        f"<title>{TITULO_DO_MANUAL}</title>",
        f"<style>{ESTILO}</style>", "</head>", "<body>",
        '<div class="folha">',
        f"<header><h1>{TITULO_DO_MANUAL}</h1><p>{CHAMADA}</p></header>",
        bloco_do_indice(paginas), "<main>",
        bloco_das_perguntas(paginas),
        bloco_dos_comandos(comandos, ancoras),
        corpo,
        "</main>", "</div>", "</body>", "</html>", ""))


def escrever(raiz: Path) -> int:
    comandos = []
    feito = montar(raiz, comandos)
    destino = raiz / DESTINO
    destino.write_text(feito, encoding="utf-8")
    print(ESCRITO.format(DESTINO, len(ler_paginas(raiz)),
                         len(comandos), len(feito) // 1024))
    return 0


def verificar(raiz: Path) -> int:
    destino = raiz / DESTINO
    if not destino.is_file():
        print(SEM_MANUAL.format(DESTINO))
        return 1
    if destino.read_text(encoding="utf-8") != montar(raiz):
        print(DIVERGIU.format(DESTINO))
        return 1
    print(EM_DIA.format(DESTINO, len(ler_paginas(raiz))))
    return 0


def main(argumentos: list) -> int:
    ap = argparse.ArgumentParser(description=USO)
    ap.add_argument("--escrever", action="store_true",
                    help="grava o manual (o padrão é só verificar)")
    a = ap.parse_args(argumentos)
    raiz = Path.cwd()
    return escrever(raiz) if a.escrever else verificar(raiz)


def arvore_de_mentira(raiz: Path) -> Path:
    (raiz / PASTA_DAS_PAGINAS).mkdir(parents=True)
    (raiz / PASTA_DAS_PAGINAS / "LEIAME.md").write_text(
        "# conhecimento\n\nA porta de entrada, com um link para\n"
        "[o mapa](mapa-do-repositorio.md) e outro para\n"
        "[o defeito](https://exemplo.invalido/defeito).\n", encoding="utf-8")
    (raiz / PASTA_DAS_PAGINAS / "mapa-do-repositorio.md").write_text(
        "# Onde escrever cada coisa\n\n## As pastas, uma linha cada\n\n"
        "| Pasta | O que mora ali |\n| --- | --- |\n"
        "| `tmp/` | rascunho & sobra |\n\n"
        "## Fonte e cópia: edite sempre a fonte\n\n"
        "- a fonte, que se edita, e a linha\n  que continua o mesmo item\n"
        "    - o caso de dentro\n\n"
        "Depois de mexer, rode:\n\n```bash\npython montar.py --sincronizar\n"
        "```\n", encoding="utf-8")
    (raiz / PASTA_DAS_PAGINAS / "regras-da-camada.md").write_text(
        "<!-- GERADA de nucleo/regras.json pelo `montar.py --sincronizar`. "
        "Edite lá. -->\n\n# As regras da camada\n\n"
        "1. **Abra a sessão na raiz.**\n", encoding="utf-8")
    (raiz / "execucoes").mkdir()
    (raiz / PAGINA_DA_RECEITA).write_text(
        "# Roteiros que viajam com a camada\n\n"
        "## A receita do disparo, em linhas copiáveis\n\n"
        "```bash\npython3 encadeador.py ensaio\n```\n", encoding="utf-8")
    return raiz


def testar() -> int:
    import tempfile
    resultados = []

    def caso(nome: str, deu_certo: bool):
        resultados.append((nome, deu_certo))

    ancoras = {"mapa-do-repositorio.md": "conhecimento-mapa-do-repositorio-md"}
    caso("título de segundo nível ganha âncora navegável",
         'id="as-pastas-uma-linha-cada"'
         in converter("## As pastas, uma linha cada", ancoras, [], "x.md"))
    caso("a continuação de um item entra no mesmo item",
         "<li>a fonte e a linha de baixo</li>"
         in converter("- a fonte\n  e a linha de baixo", ancoras, [], "x.md"))
    caso("item mais indentado vira sub-lista",
         "<ul><li>de dentro</li></ul>"
         in converter("- de fora\n    - de dentro", ancoras, [], "x.md"))
    caso("tabela vira cabeçalho e corpo",
         "<th>Pasta</th>" in converter("| Pasta |\n| --- |\n| `tmp/` |",
                                       ancoras, [], "x.md"))
    colhidos = []
    caso("bloco bash vira comando colhido, com a página de origem",
         "<pre><code>ls -la</code></pre>"
         in converter("```bash\nls -la\n```", ancoras, colhidos, "x.md")
         and colhidos == [("x.md", "ls -la")])
    caso("bloco sem linguagem não vira comando do dia a dia",
         converter("```\nnada\n```", ancoras, (colhidos := []), "x.md")
         and colhidos == [])
    misturado = []
    converter("```bash\nls\n```\n\n```\nnao e comando\n```", ancoras,
              misturado, "x.md")
    caso("a contagem escrita é a dos comandos colhidos, não a dos blocos: "
         "bloco sem linguagem não entra na seção e não pode entrar no número",
         len(misturado) == 1)
    caso("link para página do manual vira âncora interna",
         '<a href="#conhecimento-mapa-do-repositorio-md">o mapa</a>'
         in converter("[o mapa](mapa-do-repositorio.md)", ancoras, [], "x.md"))
    caso("link de fora vira texto com o endereço, nunca href",
         converter("[o defeito](https://exemplo.invalido/x)", ancoras, [],
                   "x.md")
         == "<p>o defeito (<code>https://exemplo.invalido/x</code>)</p>")
    caso("marca de gerado na página vira selo com a fonte",
         selo_da_pagina("conhecimento/regras-da-camada.md",
                        "<!-- GERADA de nucleo/regras.json pelo x. -->\n")
         == SELO_COM_MARCA.format("nucleo/regras.json"))
    caso("cópia sem marca ganha selo pela declaração de caminho",
         selo_da_pagina(PAGINA_DA_RECEITA, "# Roteiros\n")
         == SELO_POR_CAMINHO.format(COPIAS_SEM_MARCA[PAGINA_DA_RECEITA]))
    caso("página que não é cópia não ganha selo",
         selo_da_pagina("conhecimento/LEIAME.md", "# conhecimento\n") == "")
    caso("o que parece marcação HTML na fonte sai escapado",
         "&lt;script&gt;"
         in converter("cuidado com <script> solto", ancoras, [], "x.md"))
    caso("negrito e código inline atravessam",
         converter("o **teto** de `60 s`", ancoras, [], "x.md")
         == "<p>o <strong>teto</strong> de <code>60 s</code></p>")

    mudo = io.StringIO()
    with tempfile.TemporaryDirectory() as pasta, redirect_stdout(mudo):
        raiz = arvore_de_mentira(Path(pasta))
        feito = montar(raiz)
        caso("a abertura vem primeiro, na ordem declarada",
             [p["rel"] for p in ler_paginas(raiz)][:2] == list(ABERTURA))
        caso("a receita do executor de roteiros entra por último",
             ler_paginas(raiz)[-1]["rel"] == PAGINA_DA_RECEITA)
        caso("toda pergunta declarada acha a seção que a responde no gerado",
             all(f'>{secao}</a>' in feito for _, secao in PERGUNTAS))
        caso("o gerado não busca nada da rede",
             not [s for s in SINAIS_DE_REDE if s in feito])
        caso("o gerado é um arquivo só: o CSS vai embutido",
             "<style>" in feito and ".folha{" in feito)
        caso("o índice cita toda página lida",
             all(f'href="#{p["ancora"]}"' in feito for p in ler_paginas(raiz)))
        ancoras_do_feito = re.findall(r'\bid="([^"]+)"', feito)
        caso("nenhuma âncora do manual nasce duplicada",
             len(ancoras_do_feito) == len(set(ancoras_do_feito)))
        caso("todo link do manual cai numa âncora que existe",
             all(alvo[1:] in ancoras_do_feito
                 for alvo in re.findall(r'href="([^"]+)"', feito)))
        caso("página sem nenhuma cai como erro de uso, não como manual vazio",
             erro_de(lambda: montar(Path(pasta) / "vazio"))
             is not None)
        caso("manual que ainda não existe reprova a verificação",
             verificar(raiz) == 1)
        caso("escrever grava e a verificação passa a bater",
             escrever(raiz) == 0 and verificar(raiz) == 0)
        (raiz / PASTA_DAS_PAGINAS / "nova.md").write_text(
            "# Página nova\n\nEla entra sozinha.\n", encoding="utf-8")
        caso("página nova sem regerar reprova a verificação",
             verificar(raiz) == 1)
        (raiz / PASTA_DAS_PAGINAS / "mapa-do-repositorio.md").write_text(
            "# Onde escrever cada coisa\n\n## Outra seção\n", encoding="utf-8")
        caso("pergunta que perdeu a seção falha alto, e não gera manual torto",
             ERRO_SEM_ANCORA.split(":")[0] in str(erro_de(
                 lambda: montar(raiz))))

    falhas = [nome for nome, deu_certo in resultados if not deu_certo]
    for falha in falhas:
        print(TESTE_FALHA.format(falha))
    if falhas:
        print(TESTE_RESUMO_FALHA.format(len(falhas), len(resultados)))
        return 1
    print(TESTE_RESUMO_OK.format(len(resultados)))
    return 0


def erro_de(chamada):
    try:
        chamada()
    except (ValueError, OSError) as caiu:
        return caiu
    return None


if __name__ == "__main__":
    if BANDEIRA_DE_TESTE in sys.argv[1:]:
        sys.exit(testar())
    try:
        sys.exit(main(sys.argv[1:]))
    except ValueError as uso:
        print(uso, file=sys.stderr)
        sys.exit(2)
    except OSError as ambiente:
        print(ERRO_DE_AMBIENTE.format(ambiente), file=sys.stderr)
        sys.exit(2)
