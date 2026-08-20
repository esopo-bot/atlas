import argparse
import ast
import contextlib
import io
import json
import re
import subprocess
import shutil
import sys
import tempfile
import time
import tokenize
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent / "camada"))
from camada import (
    CONFIGURACOES_DO_CLAUDE, ENTRADA_VAZIA_DO_GANCHO,
    FERRAMENTAS_DA_SIMULACAO, MODELO_DA_SIMULACAO, PEDIDO,
    RAIZ_NO_COMANDO, RAIZ_NO_COMANDO_SEM_CHAVES, TEMPO_DE_UM_GANCHO,
    bytes_que_os_ganchos_injetam, colher_json as _colher_json,
    comandos_de_abertura, corre, perguntas as _perguntas,
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
SESSAO_MORREU = "  (a sessão morreu: {})"
NADA_A_MOSTRAR = "  (nada acima do teto)"
MAIOR_DO_MONTE = ("  o que a régua usa: maior arquivo {} linhas ({}), "
                  "maior função {} linhas ({})")
SEM_TESTE = "sem --testar"




def arquivos_python():
    saida = subprocess.run(["git", "ls-files", "-z", "*.py"],
                           capture_output=True, text=True, check=True).stdout
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
    achados = [Path(INSTALADOR)]
    for pasta in PASTAS_DE_INSTRUMENTO:
        achados += sorted(Path(pasta).rglob(GLOB_DE_INSTRUMENTO))
    return [a for a in achados if a.is_file()
            and BANDEIRA_DE_TESTE in a.read_text(
                encoding="utf-8", errors="replace")]


def medir_testes():
    linhas, total, casos, instrumentos = [], 0.0, 0, 0
    for alvo in instrumentos_com_teste():
        if not Path(alvo).exists():
            linhas.append(LINHA_TESTE.format(alvo, 0.0, SEM_TESTE))
            continue
        partida = time.monotonic()
        _, saida = corre(f'{INTERPRETADOR_NO_SHELL} "{alvo}" --testar 2>&1 | tail -1')
        gasto = time.monotonic() - partida
        numeros = [int(p) for p in saida.replace(":", " ").split() if p.isdigit()]
        casos += numeros[0] if saida.startswith("OK") and numeros else 0
        instrumentos += 1
        total += gasto
        linhas.append(LINHA_TESTE.format(alvo, gasto, saida[:60]))
    linhas.append(LINHA_TOTAL_TESTE.format("TOTAL", total, instrumentos, casos))
    return linhas, {"segundos": round(total, 1), "casos": casos,
                    "instrumentos": instrumentos}


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




def medir_simulacao():
    if not shutil.which("claude"):
        return [SEM_CLAUDE], {"rodou": False}

    quantas = len(json.loads(Path(FONTE_DAS_REGRAS).read_text(
        encoding="utf-8"))["regras"])
    pasta = tempfile.mkdtemp(prefix="atlas-simulacao-")
    try:
        montou, saida = _arvore_com_a_camada(pasta)
        if not montou:
            return [SESSAO_MORREU.format(saida[-120:])], {"rodou": False}

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

        linhas = [LINHA_PERGUNTA.format("OK  " if ok else "FALHA", rotulo, porque)
                  for rotulo, ok, porque in acertos]
        certos = sum(1 for _, ok, _ in acertos if ok)
        uso = sessao.get("usage") or {}
        linhas += [
            LINHA_CUSTO.format("acurácia", f"{certos}/{len(acertos)}"),
            LINHA_CUSTO.format("turnos", sessao.get("num_turns", "?")),
            LINHA_CUSTO.format("tempo de parede", f"{parede:.1f} s"),
            LINHA_CUSTO.format("custo em dólar",
                               f"{sessao.get('total_cost_usd', 0):.4f}"),
            LINHA_CUSTO.format("tokens de entrada", uso.get("input_tokens", "?")),
            LINHA_CUSTO.format("tokens de saída", uso.get("output_tokens", "?")),
        ]
        return linhas, {"rodou": True, "acertos": certos, "casos": len(acertos),
                        "turnos": sessao.get("num_turns"),
                        "segundos": round(parede, 1),
                        "dolar": sessao.get("total_cost_usd")}
    finally:
        shutil.rmtree(pasta, ignore_errors=True)


MEDIDAS = (
    ("comentarios", TITULO_COMENTARIOS, medir_comentarios),
    ("testes", TITULO_TESTES, medir_testes),
    ("camada", TITULO_CAMADA, medir_camada),
    ("contexto", TITULO_CONTEXTO, medir_contexto),
    ("tamanho", TITULO_TAMANHO, medir_tamanho),
    ("formato", TITULO_FORMATO, medir_formato),
)

SOB_PEDIDO = (
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


FALHA_DO_CASO = "  [{}]"
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
    falhas = []

    def caso(rotulo, condicao):
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

    total = 7
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
        print(json.dumps(resumo, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps(relatorio(set(a.medida)), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(testar() if BANDEIRA_DE_TESTE in sys.argv
             else main())
