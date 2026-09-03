import argparse
import ast
import contextlib
import io
import json
import os
import re
import subprocess
import shutil
import sys
import pathlib
import tempfile
import time
import tokenize
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent / "camada"))
from camada import (
    provar as _provar,
    FERRAMENTAS_DA_SIMULACAO, MODELO_DA_SIMULACAO, PEDIDO,
    bytes_que_os_ganchos_injetam, colher_json as _colher_json,
    corre, perguntas as _perguntas,
    teste_toca_o_proprio_codigo as _teste_toca_o_proprio_codigo)

BANDEIRA_DE_TESTE = "--testar"
USO = ("mede o atlas: comentário, teste, camada, contexto, tamanho e formato. "
       "A simulação NÃO entra no padrão: ela gasta uma sessão de verdade.")

MARCA_DE_BLOCO = "# ==="
TETO_DE_FUNCAO = 40
TETO_DE_ARQUIVO = 800
TETO_DE_PARAMETROS = 5

PASTAS_DE_INSTRUMENTO = (".agents", ".claude/hooks")
GLOB_DE_INSTRUMENTO = "*.py"

CARREGADOS_EM_TODA_SESSAO = ("AGENTS.md", "CLAUDE.md")
FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.S)
CAMPO_NOME = re.compile(r"^name:\s*(.+)$", re.M)
CAMPO_DESCRICAO = re.compile(r"^description:\s*(.+)$", re.M)
LINHA_DO_CATALOGO = "- {}: {}\n"
INSTALADOR = "montar.py"
INTERPRETADOR = sys.executable
INTERPRETADOR_NO_SHELL = f'"{sys.executable}"'
CHAVE_DAS_PAGINAS = "PAGINAS"

TITULO_COMENTARIOS = "COMENTÁRIO E DOCSTRING — o alvo é zero"
TITULO_TESTES = "TESTES — contagem e tempo de parede"
TITULO_CAMADA = "CAMADA — embutido × disco"
TITULO_CONTEXTO = "CONTEXTO DE LARGADA — o que toda sessão paga"
CORPO_SO_AO_DISPARAR = "  (corpos das skills, cobrados só ao disparar)"
TITULO_TAMANHO = "TAMANHO — candidatos a refatoração"
TITULO_FORMATO = "FORMATO — o que o montar.py instala, por extensão"
TITULO_SIMULACAO = ("SIMULAÇÃO DE SESSÃO — acurácia e custo de uma sessão real")

LINHA_COMENTARIO = "  {:<52} comentarios={} docstrings={} marcas={}"
LINHA_TESTE = "  {:<48} {:>7.1f}s  {}"
LINHA_TOTAL_TESTE = "  {:<48} {:>7.1f}s  {} instrumentos, {} casos"
LINHA_CONTEXTO = "  {:<52} {:>7} bytes"
LINHA_FUNCAO = "  {:<52} {:>4} linhas  {}"
LINHA_ARQUIVO = "  {:<52} {:>4} linhas"
LINHA_PARAMETROS = "  {:<52} {:>4} parâmetros  {}"
LINHA_FORMATO = "  {:<12} {:>4} arquivos  {:>9} bytes"
LINHA_PERGUNTA = "  [{}] {:<34} {}"
LINHA_CUSTO = "  {:<34} {}"
SEM_CLAUDE = "  (claude fora do PATH — simulação não rodou)"
SEM_O_ARQUIVO = "a sessão não escreveu o arquivo"
MARCA_DO_CASO_DO_TESTE = "--testar"
PASTA_DAS_EVIDENCIAS = "tmp/evidencias/simulacao"
NOME_DO_ARTEFATO_REPROVADO = "artefato-que-reprovou.py"
ARTEFATO_GUARDADO = ("  (o artefato reprovado ficou em {} — a árvore da "
                     "simulação some, e medida que reprova sem deixar ver o "
                     "que reprovou não se investiga)")
SESSAO_MORREU = "  (a sessão morreu: {})"
NADA_A_MOSTRAR = "  (nada acima do teto)"
TITULO_BRACO_COM = "  com a camada instalada:"
TITULO_BRACO_SEM = "  sem a camada — braço de controle:"
LINHA_DO_DELTA = "  {}"
DELTA_QUE_A_CAMADA_ABRE = ("delta da camada: +{} de {} casos — a camada "
                           "melhorou a sessão nesta rodada.")
DELTA_QUE_NAO_ABRE = ("delta da camada: {} de {} casos — a camada NÃO "
                      "melhorou a sessão nesta rodada, e o número fica dito.")
MAIOR_DO_MONTE = ("  o que a régua usa: maior arquivo {} linhas ({}), "
                  "maior função {} linhas ({})")
SEM_TESTE = "sem --testar"




def arquivos_python():
    saida = subprocess.run(["git", "ls-files", "-z", "*.py"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", check=True).stdout
    return sorted(p for p in saida.split("\0") if p)


def arvore(caminho):
    return ast.parse(Path(caminho).read_text(encoding="utf-8"))


def contar_comentarios(caminho):
    fonte = Path(caminho).read_text(encoding="utf-8")
    textos = [t.string for t in tokenize.generate_tokens(io.StringIO(fonte).readline)
              if t.type == tokenize.COMMENT]
    marcas = sum(1 for t in textos if t.startswith(MARCA_DE_BLOCO))
    docstrings = sum(
        1 for no in ast.walk(ast.parse(fonte))
        if isinstance(no, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                           ast.ClassDef)) and ast.get_docstring(no) is not None)
    return len(textos) - marcas, docstrings, marcas


def funcoes_de(caminho):
    for no in ast.walk(arvore(caminho)):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fim = getattr(no, "end_lineno", no.lineno)
            argumentos = no.args
            quantos = (len(argumentos.posonlyargs) + len(argumentos.args)
                       + len(argumentos.kwonlyargs))
            yield no.name, no.lineno, fim - no.lineno + 1, quantos


def medir_comentarios():
    linhas, soma = [], [0, 0, 0]
    for caminho in arquivos_python():
        contagem = contar_comentarios(caminho)
        soma = [a + b for a, b in zip(soma, contagem)]
        linhas.append(LINHA_COMENTARIO.format(caminho, *contagem))
    linhas.append(LINHA_COMENTARIO.format("TOTAL", *soma))
    return linhas, {"comentarios": soma[0], "docstrings": soma[1], "marcas": soma[2]}


def instrumentos_com_teste():
    achados = sorted(Path().glob(GLOB_DE_INSTRUMENTO))
    for pasta in PASTAS_DE_INSTRUMENTO:
        achados += sorted(Path(pasta).rglob(GLOB_DE_INSTRUMENTO))
    return [a.as_posix() for a in achados if a.is_file()
            and BANDEIRA_DE_TESTE in a.read_text(
                encoding="utf-8", errors="replace")]


def medir_testes():
    linhas, contas = _provar(Path("."))
    linhas.append(LINHA_TOTAL_TESTE.format(
        "TOTAL", contas["segundos"], contas["rodados"], contas["casos"]))
    return linhas, {"segundos": contas["segundos"], "casos": contas["casos"],
                    "instrumentos": contas["rodados"],
                    "caem": contas["caem"]}


def medir_camada():
    _, sincronia = corre(f"{INTERPRETADOR_NO_SHELL} montar.py --verificar 2>&1 | tail -1")
    _, copias = corre(
        "find modulos -name '*.py' -path '*/.agents/*' | sort | while read -r c; do "
        "o=\".agents/${c#*/.agents/}\"; [ -f \"$o\" ] || continue; "
        "cmp -s \"$o\" \"$c\" && echo \"$c: igual\" || echo \"$c: DIVERGE\"; done")
    linhas = ["  " + sincronia] + ["  " + l for l in copias.splitlines()]
    em_dia = sincronia.startswith("Tudo em dia") and "DIVERGE" not in copias
    return linhas, {"em_dia": em_dia}


def linha_do_catalogo(skill):
    texto = skill.read_text(encoding="utf-8")
    frente = FRONTMATTER.match(texto)
    if not frente:
        return "", len(texto)
    nome = CAMPO_NOME.search(frente.group(1))
    descricao = CAMPO_DESCRICAO.search(frente.group(1))
    if not (nome and descricao):
        return "", len(texto)
    listada = LINHA_DO_CATALOGO.format(nome.group(1).strip(),
                                       descricao.group(1).strip())
    return listada, len(texto.encode()) - len(frente.group(1).encode())






def medir_contexto():
    linhas, total, adiado = [], 0, 0
    for nome in CARREGADOS_EM_TODA_SESSAO:
        caminho = Path(nome)
        if caminho.exists():
            tamanho = len(caminho.read_bytes())
            total += tamanho
            linhas.append(LINHA_CONTEXTO.format(nome, tamanho))
    for skill in sorted(Path(".agents/skills").glob("*/SKILL.md")):
        listada, corpo = linha_do_catalogo(skill)
        total += len(listada.encode())
        adiado += corpo
        linhas.append(LINHA_CONTEXTO.format(skill.as_posix(),
                                            len(listada.encode())))
    injetado_por_gancho, ganchos_cegos = bytes_que_os_ganchos_injetam(
        Path.cwd())
    total += injetado_por_gancho
    linhas.append(LINHA_CONTEXTO.format("ganchos de abertura",
                                        injetado_por_gancho))
    linhas.append(LINHA_CONTEXTO.format("TOTAL", total))
    linhas.append(CORPO_SO_AO_DISPARAR)
    linhas.append(LINHA_CONTEXTO.format("adiado", adiado))
    return linhas, {"bytes": total, "adiado": adiado,
                    "injetado_por_gancho": injetado_por_gancho,
                    "ganchos_nao_medidos": ganchos_cegos}


def medir_tamanho():
    grandes, longas, parrudas = [], [], []
    for caminho in arquivos_python():
        linhas_do_arquivo = Path(caminho).read_text(encoding="utf-8").count("\n") + 1
        if linhas_do_arquivo > TETO_DE_ARQUIVO:
            grandes.append((linhas_do_arquivo, caminho))
        for nome, comeco, tamanho, parametros in funcoes_de(caminho):
            if tamanho > TETO_DE_FUNCAO:
                longas.append((tamanho, f"{caminho}:{comeco}", nome))
            if parametros > TETO_DE_PARAMETROS:
                parrudas.append((parametros, f"{caminho}:{comeco}", nome))
    saida = [f"  arquivos acima de {TETO_DE_ARQUIVO} linhas:"]
    saida += [LINHA_ARQUIVO.format(c, n) for n, c in sorted(grandes, reverse=True)] \
        or [NADA_A_MOSTRAR]
    saida.append(f"  funções acima de {TETO_DE_FUNCAO} linhas:")
    saida += [LINHA_FUNCAO.format(onde, n, nome)
              for n, onde, nome in sorted(longas, reverse=True)[:20]] \
        or [NADA_A_MOSTRAR]
    saida.append(f"  funções com mais de {TETO_DE_PARAMETROS} parâmetros:")
    saida += [LINHA_PARAMETROS.format(onde, n, nome)
              for n, onde, nome in sorted(parrudas, reverse=True)] or [NADA_A_MOSTRAR]
    maior_arquivo = max(grandes, default=(0, ""))
    maior_funcao = max(longas, default=(0, "", ""))
    saida.append(MAIOR_DO_MONTE.format(maior_arquivo[0], maior_arquivo[1],
                                       maior_funcao[0], maior_funcao[2]))
    return saida, {"arquivos_grandes": len(grandes), "funcoes_longas": len(longas),
                   "funcoes_parrudas": len(parrudas),
                   "maior_arquivo": maior_arquivo[0],
                   "maior_funcao": maior_funcao[0]}


def paginas_instaladas():
    escopo = {"__name__": "saude"}
    exec(compile(Path(INSTALADOR).read_text(encoding="utf-8"),
                 INSTALADOR, "exec"), escopo)
    return sorted(escopo[CHAVE_DAS_PAGINAS])


def medir_formato():
    contagem = {}
    for nome in paginas_instaladas():
        caminho = Path(nome)
        if not caminho.is_file():
            continue
        extensao = caminho.suffix or "(sem)"
        quantos, bytes_ = contagem.get(extensao, (0, 0))
        contagem[extensao] = (quantos + 1, bytes_ + len(caminho.read_bytes()))
    linhas = [LINHA_FORMATO.format(e, q, b)
              for e, (q, b) in sorted(contagem.items(), key=lambda i: -i[1][1])]
    return linhas, {e: q for e, (q, _) in contagem.items()}


TEMPO_DA_SIMULACAO = 600
ARQUIVO_PEDIDO = "tmp/somar.py"
FONTE_DAS_REGRAS = "nucleo/regras.json"











def _arvore_com_a_camada(pasta):
    corre(f'git init -q "{pasta}"')
    codigo, saida = corre(f'cd "{pasta}" && {INTERPRETADOR_NO_SHELL} "{Path(INSTALADOR).resolve()}" 2>&1')
    return codigo == 0, saida


def _arvore_sem_a_camada(pasta):
    codigo, saida = corre(f'git init -q "{pasta}"')
    Path(pasta, Path(ARQUIVO_PEDIDO).parent).mkdir(parents=True, exist_ok=True)
    return codigo == 0, saida




def guardar_o_artefato_se_reprovou(alvo: Path, acertos: list) -> str:
    reprovou = any(not ok for rotulo, ok, _ in acertos
                   if ARQUIVO_PEDIDO in rotulo or MARCA_DO_CASO_DO_TESTE in rotulo)
    if not reprovou or not alvo.is_file():
        return ""
    destino = Path(PASTA_DAS_EVIDENCIAS) / NOME_DO_ARTEFATO_REPROVADO
    with contextlib.suppress(OSError):
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(alvo.read_text(encoding="utf-8"), encoding="utf-8")
        return str(destino)
    return ""


def _pontuar_a_sessao(pasta: str, quantas: int) -> dict:
    partida = time.monotonic()
    _, bruto = corre(
        f'cd "{pasta}" && claude -p {json.dumps(PEDIDO.format(arquivo=ARQUIVO_PEDIDO))} '
        f'--output-format json --model {MODELO_DA_SIMULACAO} '
        f'--allowedTools "{FERRAMENTAS_DA_SIMULACAO}"',
        tempo=TEMPO_DA_SIMULACAO)
    parede = time.monotonic() - partida

    sessao = _colher_json(bruto)
    resposta = _colher_json(str(sessao.get("result", "")))
    acertos = [(rotulo, bool(prova(resposta)),
                "" if prova(resposta) else str(resposta.get(chave, ""))[:50])
               for rotulo, chave, prova in _perguntas(quantas)]

    alvo = Path(pasta) / ARQUIVO_PEDIDO
    if alvo.is_file():
        codigo_do_teste, berro = corre(
            f'cd "{pasta}" && {INTERPRETADOR_NO_SHELL} "{ARQUIVO_PEDIDO}" --testar')
    else:
        codigo_do_teste, berro = 1, SEM_O_ARQUIVO
    acertos.append((f"entregou {ARQUIVO_PEDIDO} com --testar que passa",
                    alvo.is_file() and codigo_do_teste == 0,
                    berro.strip().splitlines()[-1][:58] if berro else ""))
    acertos.append(("o --testar exercita o código do arquivo",
                    alvo.is_file() and _teste_toca_o_proprio_codigo(alvo), ""))
    return {"rodou": True, "acertos": acertos, "alvo": alvo,
            "certos": sum(1 for _, ok, _ in acertos if ok),
            "parede": parede, "sessao": sessao}


def _rodar_um_braco(montar_a_arvore, quantas: int) -> dict:
    pasta = tempfile.mkdtemp(prefix="atlas-simulacao-")
    try:
        montou, saida = montar_a_arvore(pasta)
        if not montou:
            return {"rodou": False, "porque": saida[-120:]}
        return _pontuar_a_sessao(pasta, quantas)
    finally:
        shutil.rmtree(pasta, ignore_errors=True)


def _linhas_de_um_braco(braco: dict, titulo: str) -> list:
    uso = braco["sessao"].get("usage") or {}
    return [titulo] + [
        LINHA_PERGUNTA.format("OK  " if ok else "FALHA", rotulo, porque)
        for rotulo, ok, porque in braco["acertos"]] + [
        LINHA_CUSTO.format("acurácia",
                           f"{braco['certos']}/{len(braco['acertos'])}"),
        LINHA_CUSTO.format("turnos", braco["sessao"].get("num_turns", "?")),
        LINHA_CUSTO.format("tempo de parede", f"{braco['parede']:.1f} s"),
        LINHA_CUSTO.format("custo em dólar",
                           f"{braco['sessao'].get('total_cost_usd', 0):.4f}"),
        LINHA_CUSTO.format("tokens de entrada", uso.get("input_tokens", "?")),
        LINHA_CUSTO.format("tokens de saída", uso.get("output_tokens", "?")),
    ]


def recado_do_delta(delta: int, casos: int) -> str:
    return (DELTA_QUE_A_CAMADA_ABRE if delta > 0
            else DELTA_QUE_NAO_ABRE).format(delta, casos)


def medir_simulacao():
    if not shutil.which("claude"):
        return [SEM_CLAUDE], {"rodou": False}

    quantas = len(json.loads(Path(FONTE_DAS_REGRAS).read_text(
        encoding="utf-8"))["regras"])
    com = _rodar_um_braco(_arvore_com_a_camada, quantas)
    if not com["rodou"]:
        return [SESSAO_MORREU.format(com["porque"])], {"rodou": False}
    guardado = guardar_o_artefato_se_reprovou(com["alvo"], com["acertos"])
    sem = _rodar_um_braco(_arvore_sem_a_camada, quantas)
    if not sem["rodou"]:
        return [SESSAO_MORREU.format(sem["porque"])], {"rodou": False}

    delta = com["certos"] - sem["certos"]
    casos = len(com["acertos"])
    linhas = _linhas_de_um_braco(com, TITULO_BRACO_COM)
    if guardado:
        linhas.append(ARTEFATO_GUARDADO.format(guardado))
    linhas += _linhas_de_um_braco(sem, TITULO_BRACO_SEM)
    linhas += [LINHA_DO_DELTA.format(recado_do_delta(delta, casos))]
    return linhas, {"rodou": True, "acertos": com["certos"], "casos": casos,
                    "acertos_sem_a_camada": sem["certos"], "delta": delta,
                    "turnos": com["sessao"].get("num_turns"),
                    "segundos": round(com["parede"], 1),
                    "dolar": com["sessao"].get("total_cost_usd"),
                    "dolar_sem_a_camada": sem["sessao"].get("total_cost_usd")}


MEDIDAS = (
    ("comentarios", TITULO_COMENTARIOS, medir_comentarios),
    ("tamanho", TITULO_TAMANHO, medir_tamanho),
    ("formato", TITULO_FORMATO, medir_formato),
)

SOB_PEDIDO_TAMBEM = (
    ("testes", TITULO_TESTES, medir_testes),
)

SOB_PEDIDO = SOB_PEDIDO_TAMBEM + (
    ("simulacao", TITULO_SIMULACAO, medir_simulacao),
)


def relatorio(escolhidas):
    resumo = {}
    for nome, titulo, medir in MEDIDAS + SOB_PEDIDO:
        pedida = nome in escolhidas
        if (escolhidas and not pedida) or (not escolhidas and nome not in
                                           [m[0] for m in MEDIDAS]):
            continue
        linhas, dados = medir()
        print(f"\n{titulo}")
        for linha in linhas:
            print(linha)
        resumo[nome] = dados
    return resumo


def medidas_que_nao_rodaram(resumo: dict) -> list:
    return sorted(nome for nome, dados in resumo.items()
                  if isinstance(dados, dict) and dados.get("rodou") is False)


FALHA_DO_CASO = "  [{}]"
NAO_MEDIDO = ("NÃO MEDIDO: {} — o número que falta não é zero, e sair 0 aqui "
              "faria a medida morta passar por medida boa.")
RESUMO_FALHOU_AQUI = "FALHOU: {} de {} casos"
RESUMO_OK_AQUI = "OK: {} casos — contagem de comentário e forma de função"
COM_SUJEIRA = """# um comentário
# === bloco marcado ===
def f():
    \"\"\"docstring\"\"\"
    return 1
"""
LIMPO = """def f(a, b, *, c):
    return a + b + c


async def g(x):
    return x
"""


def testar() -> int:
    import tempfile
    falhas, casos = [], []

    def caso(rotulo, condicao):
        casos.append(rotulo)
        if not condicao:
            falhas.append(rotulo)

    with tempfile.TemporaryDirectory(prefix="saude-teste-") as pasta:
        sujo = Path(pasta) / "sujo.py"
        sujo.write_text(COM_SUJEIRA, encoding="utf-8")
        comentarios, docstrings, marcas = contar_comentarios(sujo)
        caso("comentário comum é contado", comentarios == 1)
        caso("marca de bloco não conta como comentário", marcas == 1)
        caso("docstring é contada à parte", docstrings == 1)

        limpo = Path(pasta) / "limpo.py"
        limpo.write_text(LIMPO, encoding="utf-8")
        caso("arquivo sem sujeira soma zero",
             contar_comentarios(limpo) == (0, 0, 0))

        achadas = {nome: (linhas, quantos)
                   for nome, _, linhas, quantos in funcoes_de(limpo)}
        caso("conta todo parâmetro, inclusive o que só vem por nome",
             achadas["f"][1] == 3)
        caso("função assíncrona é vista", "g" in achadas)
        caso("o tamanho da função sai em linhas", achadas["f"][0] == 2)

    with tempfile.TemporaryDirectory() as pasta:
        artefato = pathlib.Path(pasta) / "somar.py"
        artefato.write_text("x = 1\n", encoding="utf-8")
        passou = [("entregou tmp/somar.py com --testar que passa", True, ""),
                  ("o --testar exercita o código do arquivo", True, "")]
        caso("simulação que passou não deixa artefato para trás",
             guardar_o_artefato_se_reprovou(artefato, passou) == "")
        caso("sem artefato no disco não há o que guardar",
             guardar_o_artefato_se_reprovou(
                 pathlib.Path(pasta) / "nao-existe.py",
                 [("o --testar exercita o código do arquivo", False, "")]) == "")

    with tempfile.TemporaryDirectory(prefix="saude-controle-") as pasta:
        montou, _ = _arvore_sem_a_camada(pasta)
        caso("o braço de controle monta a árvore", montou)
        caso("o braço de controle NÃO instala a camada",
             not (Path(pasta) / "AGENTS.md").exists())
        caso("o braço de controle deixa a pasta do arquivo pedido pronta, "
             "para o único diferente ser a camada",
             (Path(pasta) / Path(ARQUIVO_PEDIDO).parent).is_dir())

    caso("delta positivo diz que a camada melhorou a sessão",
         recado_do_delta(5, 8).startswith("delta da camada: +5 de 8")
         and "NÃO" not in recado_do_delta(5, 8))
    caso("delta zero diz, com todas as letras, que a camada NÃO melhorou",
         "NÃO melhorou" in recado_do_delta(0, 8))
    caso("delta negativo também diz que a camada NÃO melhorou",
         "NÃO melhorou" in recado_do_delta(-2, 8))

    with tempfile.TemporaryDirectory(prefix="saude-raiz-") as pasta:
        arvore = Path(pasta)
        (arvore / ".agents" / "peca").mkdir(parents=True)
        (arvore / ".agents" / "peca" / "peca.py").write_text(
            BANDEIRA_DE_TESTE, encoding="utf-8")
        (arvore / "instrumento-da-raiz.py").write_text(
            BANDEIRA_DE_TESTE, encoding="utf-8")
        (arvore / "sem-teste-na-raiz.py").write_text(
            "x = 1\n", encoding="utf-8")
        de_onde = Path.cwd()
        try:
            os.chdir(arvore)
            inventario = instrumentos_com_teste()
        finally:
            os.chdir(de_onde)
        caso("instrumento da raiz com --testar entra no inventário",
             "instrumento-da-raiz.py" in inventario)
        caso("arquivo da raiz sem --testar fica de fora",
             "sem-teste-na-raiz.py" not in inventario)
        caso("instrumento de pasta segue no inventário",
             ".agents/peca/peca.py" in inventario)

    caso("medida que não rodou é acusada pelo nome",
         medidas_que_nao_rodaram({"simulacao": {"rodou": False},
                                  "camada": {"paginas": 3}}) == ["simulacao"])
    caso("medida que rodou não vira acusação",
         medidas_que_nao_rodaram({"simulacao": {"rodou": True}}) == [])
    caso("medida sem a chave rodou não vira acusação",
         medidas_que_nao_rodaram({"camada": {"paginas": 3}, "outra": 1}) == [])

    total = len(casos)
    if falhas:
        for falha in falhas:
            print(FALHA_DO_CASO.format(falha))
        print(RESUMO_FALHOU_AQUI.format(len(falhas), total))
        return 1
    print(RESUMO_OK_AQUI.format(total))
    return 0


def main():
    ap = argparse.ArgumentParser(description=USO)
    ap.add_argument("medida", nargs="*",
                    choices=[m[0] for m in MEDIDAS + SOB_PEDIDO] or None,
                    help="quais medidas rodar (padrão: todas)")
    ap.add_argument("--resumo", action="store_true",
                    help="imprime só o JSON do resumo, para comparar entre rodadas")
    a = ap.parse_args()
    if a.resumo:
        import contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            resumo = relatorio(set(a.medida))
    else:
        resumo = relatorio(set(a.medida))
    print(json.dumps(resumo, ensure_ascii=False, indent=2))
    if (nao_rodaram := medidas_que_nao_rodaram(resumo)):
        print(NAO_MEDIDO.format(", ".join(nao_rodaram)), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(testar() if BANDEIRA_DE_TESTE in sys.argv
             else main())
