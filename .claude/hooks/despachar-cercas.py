
import contextlib
import importlib.util
import io
import json
import pathlib
import re
import sys

EVENTO_ANTES_DA_FERRAMENTA = "PreToolUse"
DECISAO_DE_NEGAR = "deny"
DECISAO_DE_PERGUNTAR = "ask"
SILENCIO = 0
BANDEIRA_DE_TESTE = "--testar"

CHAVE_DA_SAIDA = "hookSpecificOutput"
CHAVE_DO_EVENTO = "hookEventName"
CHAVE_DA_DECISAO = "permissionDecision"
CHAVE_DA_RAZAO = "permissionDecisionReason"
CHAVE_DO_CONTEXTO = "additionalContext"

CERCAS = (
    ("vetar-branch-protegida", "Bash|PowerShell"),
    ("orientar-credencial", "Bash|PowerShell|Read"),
    ("vetar-conhecimento-em-codigo", "Write|Edit|NotebookEdit|Bash|PowerShell"),
    ("vetar-andamento-em-arquivo", "Write|Edit|NotebookEdit|Bash|PowerShell"),
    ("vetar-automacao", "Write|Edit|NotebookEdit|Bash|PowerShell"),
    ("vetar-escrita-em-somente-leitura",
     "Write|Edit|NotebookEdit|Bash|PowerShell"),
    ("vetar-pergunta-ja-respondida", "AskUserQuestion"),
    ("vetar-escrita-fora-da-execucao",
     "Write|Edit|NotebookEdit|Bash|PowerShell"),
    ("vetar-comentario-explicativo", "Write|Edit|MultiEdit"),
    ("vetar-escrita-em-copia-gerada",
     "Write|Edit|NotebookEdit|Bash|PowerShell"),
    ("vetar-escrita-em-politica", "Write|Edit|NotebookEdit|Bash|PowerShell"),
    ("avisar-sessao-paralela", "Write|Edit|NotebookEdit|Bash|PowerShell"),
    ("vetar-caminho-relativo-apos-cd", "Bash|PowerShell"),
    ("vetar-escrita-em-sessao-de-pesquisa",
     "Write|Edit|NotebookEdit|Bash|PowerShell"),
    ("vetar-documento-rastreavel", "Write|Edit|NotebookEdit"),
    ("vetar-despejo-de-ambiente", "Bash|PowerShell"),
)

CHAVE_DA_FERRAMENTA = "tool_name"

CERCA_QUEBRADA = (
    "atlas: a cerca {} estourou ({}: {}), e o despachante nega por ela em vez "
    "de deixar passar sem cerca. As outras cercas seguiram sendo avaliadas. "
    "Rode `bash .claude/hooks/interpretador.sh .claude/hooks/{}.py` sozinha "
    "para ver o erro inteiro."
)

CERCA_NAO_CARREGOU = (
    "atlas: a cerca {} não carregou ({}: {}), e o despachante nega por ela. "
    "As outras cercas seguiram sendo avaliadas."
)

UMA_RAZAO = "{}: {}"


def pasta_das_cercas() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent


def carregar(pasta, nome):
    caminho = pathlib.Path(pasta) / (nome + ".py")
    especificacao = importlib.util.spec_from_file_location(
        "cerca_" + nome.replace("-", "_"), caminho)
    if especificacao is None or especificacao.loader is None:
        raise ImportError(nome)
    modulo = importlib.util.module_from_spec(especificacao)
    especificacao.loader.exec_module(modulo)
    return modulo


def rodar_uma(modulo, corpo: str):
    saida = io.StringIO()
    erro = io.StringIO()
    guardado = sys.stdin
    sys.stdin = io.StringIO(corpo)
    estouro = None
    try:
        with contextlib.redirect_stdout(saida), contextlib.redirect_stderr(erro):
            modulo.main()
    except SystemExit as parada:
        if parada.code not in (None, 0, SILENCIO):
            estouro = parada
    except Exception as falha:
        estouro = falha
    finally:
        sys.stdin = guardado
    return saida.getvalue(), erro.getvalue(), estouro


def ler_a_saida_da_cerca(texto: str):
    for linha in texto.strip().splitlines():
        limpa = linha.strip()
        if not limpa.startswith("{"):
            continue
        try:
            dado = json.loads(limpa)
        except ValueError:
            continue
        if isinstance(dado, dict) and isinstance(dado.get(CHAVE_DA_SAIDA), dict):
            return dado[CHAVE_DA_SAIDA]
    return None


def sobrou_de_prosa(texto: str) -> str:
    sobra = []
    for linha in texto.splitlines():
        limpa = linha.strip()
        if limpa.startswith("{") and CHAVE_DA_SAIDA in limpa:
            continue
        if limpa:
            sobra.append(limpa)
    return "\n".join(sobra)


def ferramenta_do_evento(corpo: str) -> str:
    try:
        entrada = json.loads(corpo)
    except (ValueError, TypeError):
        return ""
    if not isinstance(entrada, dict):
        return ""
    nome = entrada.get(CHAVE_DA_FERRAMENTA)
    return nome if isinstance(nome, str) else ""


def esta_no_alcance(matcher: str, ferramenta: str) -> bool:
    if not matcher:
        return True
    if not ferramenta:
        return True
    try:
        return re.search(matcher, ferramenta) is not None
    except re.error:
        return True


def despachar(pasta, corpo: str, cercas=CERCAS):
    razoes = []
    contextos = []
    prosa, perguntas = [], []
    ferramenta = ferramenta_do_evento(corpo)
    for item in cercas:
        nome, matcher = item if isinstance(item, tuple) else (item, "")
        if not esta_no_alcance(matcher, ferramenta):
            continue
        try:
            modulo = carregar(pasta, nome)
        except Exception as falha:
            razoes.append(CERCA_NAO_CARREGOU.format(
                nome, type(falha).__name__, falha))
            continue
        saida, erro, estouro = rodar_uma(modulo, corpo)
        bloco = ler_a_saida_da_cerca(saida)
        if bloco and bloco.get(CHAVE_DA_DECISAO) == DECISAO_DE_NEGAR:
            razoes.append(UMA_RAZAO.format(
                nome, bloco.get(CHAVE_DA_RAZAO, "")))
        elif bloco and bloco.get(CHAVE_DA_DECISAO) == DECISAO_DE_PERGUNTAR:
            perguntas.append(UMA_RAZAO.format(
                nome, bloco.get(CHAVE_DA_RAZAO, "")))
        if bloco and bloco.get(CHAVE_DO_CONTEXTO):
            contextos.append(bloco[CHAVE_DO_CONTEXTO])
        avulso = sobrou_de_prosa(saida)
        if avulso:
            prosa.append(UMA_RAZAO.format(nome, avulso))
        if erro.strip():
            prosa.append(UMA_RAZAO.format(nome, erro.strip()))
        if estouro is not None:
            razoes.append(CERCA_QUEBRADA.format(
                nome, type(estouro).__name__, estouro, nome))
    return razoes, contextos, prosa, perguntas


def responder(razoes, contextos, prosa, perguntas) -> int:
    for linha in prosa:
        print(linha, file=sys.stderr)
    if razoes:
        print(json.dumps({CHAVE_DA_SAIDA: {
            CHAVE_DO_EVENTO: EVENTO_ANTES_DA_FERRAMENTA,
            CHAVE_DA_DECISAO: DECISAO_DE_NEGAR,
            CHAVE_DA_RAZAO: "\n\n".join(razoes),
        }}, ensure_ascii=False))
        return SILENCIO
    if perguntas:
        print(json.dumps({CHAVE_DA_SAIDA: {
            CHAVE_DO_EVENTO: EVENTO_ANTES_DA_FERRAMENTA,
            CHAVE_DA_DECISAO: DECISAO_DE_PERGUNTAR,
            CHAVE_DA_RAZAO: "\n\n".join(perguntas),
        }}, ensure_ascii=False))
        return SILENCIO
    if contextos:
        print(json.dumps({CHAVE_DA_SAIDA: {
            CHAVE_DO_EVENTO: EVENTO_ANTES_DA_FERRAMENTA,
            CHAVE_DO_CONTEXTO: "\n\n".join(contextos),
        }}, ensure_ascii=False))
    return SILENCIO


def main() -> int:
    corpo = sys.stdin.read()
    razoes, contextos, prosa, perguntas = despachar(
        pasta_das_cercas(), corpo)
    return responder(razoes, contextos, prosa, perguntas)


CERCA_QUE_NEGA = '''
import json, sys
def main():
    entrada = json.load(sys.stdin)
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": "negado por " + entrada["tool_name"],
    }}))
    return 0
'''

CERCA_QUE_PERGUNTA = '''
import json, sys
def main():
    entrada = json.load(sys.stdin)
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "ask",
        "permissionDecisionReason": "pergunta por " + entrada["tool_name"],
    }}))
    return 0
'''

CERCA_QUE_DEIXA_PASSAR = '''
import json, sys
def main():
    json.load(sys.stdin)
    return 0
'''

CERCA_QUE_ESTOURA = '''
def main():
    raise RuntimeError("estourei")
'''

CERCA_QUE_SAI_COM_ERRO = '''
import sys
def main():
    sys.exit(9)
'''

CERCA_QUE_SAI_LIMPA = '''
import sys
def main():
    sys.exit(0)
'''

CERCA_QUE_AVISA = '''
import json, sys
def main():
    json.load(sys.stdin)
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "additionalContext": "um aviso",
    }}))
    return 0
'''

CERCA_QUE_FALA_EM_PROSA = '''
import json, sys
def main():
    json.load(sys.stdin)
    print("aviso em prosa")
    return 0
'''

CERCA_QUE_EXIGE_O_CORPO_INTEIRO = '''
import json, sys
def main():
    entrada = json.load(sys.stdin)
    if entrada.get("tool_name") != "Bash":
        raise AssertionError("stdin chegou vazio ou truncado")
    return 0
'''

BANCADA = (
    ("uma cerca que nega faz o despachante negar",
     [("nega", CERCA_QUE_NEGA)], 1, 0),
    ("cerca que deixa passar não gera razão",
     [("passa", CERCA_QUE_DEIXA_PASSAR)], 0, 0),
    ("duas que negam viram duas razões",
     [("nega", CERCA_QUE_NEGA), ("nega2", CERCA_QUE_NEGA)], 2, 0),
    ("cerca que estoura nega por si, não solta o passe",
     [("estoura", CERCA_QUE_ESTOURA)], 1, 0),
    ("cerca que estoura não impede a seguinte de negar",
     [("estoura", CERCA_QUE_ESTOURA), ("nega", CERCA_QUE_NEGA)], 2, 0),
    ("sys.exit com erro conta como estouro",
     [("sai", CERCA_QUE_SAI_COM_ERRO)], 1, 0),
    ("sys.exit(0) é silêncio, não estouro",
     [("limpa", CERCA_QUE_SAI_LIMPA)], 0, 0),
    ("aviso sobrevive quando ninguém nega",
     [("avisa", CERCA_QUE_AVISA)], 0, 1),
    ("cada cerca recebe o corpo inteiro, não só a primeira",
     [("passa", CERCA_QUE_DEIXA_PASSAR),
      ("exige", CERCA_QUE_EXIGE_O_CORPO_INTEIRO),
      ("exige2", CERCA_QUE_EXIGE_O_CORPO_INTEIRO)], 0, 0),
    ("cerca que não existe nega em vez de sumir",
     [], 1, 0, ("cerca-que-nao-existe",)),
)

CORPO_DE_PROVA = '{"tool_name": "Bash", "tool_input": {"command": "ls"}}'

BANCADA_DO_ALCANCE = (
    ("Bash casa com a cerca de Bash", "Bash|PowerShell", "Bash", True),
    ("Read não casa com a cerca de Bash", "Bash|PowerShell", "Read", False),
    ("Read casa com quem o lista", "Bash|PowerShell|Read", "Read", True),
    ("NotebookEdit casa com quem o lista",
     "Write|Edit|NotebookEdit", "NotebookEdit", True),
    ("MultiEdit entra por Edit, e é de propósito",
     "Write|Edit|MultiEdit", "MultiEdit", True),
    ("AskUserQuestion não casa com Bash", "AskUserQuestion", "Bash", False),
    ("matcher vazio cobre tudo", "", "Bash", True),
    ("ferramenta ilegível roda todas", "AskUserQuestion", "", True),
    ("matcher quebrado roda em vez de calar", "[", "Bash", True),
)

BANCADA_DO_ROTEIRO = (
    ("cerca de outra ferramenta não nega este evento",
     "AskUserQuestion", 0),
    ("cerca desta ferramenta nega", "Bash|PowerShell", 1),
)


def montar_bancada(pasta, arquivos):
    nomes = []
    for nome, texto in arquivos:
        (pathlib.Path(pasta) / (nome + ".py")).write_text(
            texto, encoding="utf-8")
        nomes.append(nome)
    return nomes


def perguntas_de(pasta, cercas) -> list:
    return despachar(pasta, CORPO_DE_PROVA, cercas)[3]


def testar() -> int:
    import tempfile
    falhas = []
    with tempfile.TemporaryDirectory() as pasta:
        montar_bancada(pasta, [("pergunta", CERCA_QUE_PERGUNTA),
                               ("nega", CERCA_QUE_NEGA),
                               ("passa", CERCA_QUE_DEIXA_PASSAR)])
        so_pergunta = (("pergunta", ""),)
        perguntas = perguntas_de(pasta, so_pergunta)
        if len(perguntas) != 1:
            falhas.append(
                "cerca que PERGUNTA tem de chegar ao dono pelo despachante — "
                "esperava 1 pergunta, veio %d. Foi assim que as quatro cercas "
                "de julgamento ficaram mudas em sessão interativa: o "
                "despachante só recolhia `deny` e descartava o `ask`, e a "
                "escrita passava sem ninguém decidir" % len(perguntas))
        razoes, _, _, perguntas = despachar(
            pasta, CORPO_DE_PROVA,
            (("pergunta", ""), ("nega", ""), ("passa", "")))
        if not (len(razoes) == 1 and len(perguntas) == 1):
            falhas.append(
                "negar e perguntar convivem: esperava 1 razão e 1 pergunta, "
                "veio %d e %d" % (len(razoes), len(perguntas)))
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            responder(razoes, [], [], perguntas)
        decidido = json.loads(saida.getvalue())[CHAVE_DA_SAIDA]
        if decidido.get(CHAVE_DA_DECISAO) != DECISAO_DE_NEGAR:
            falhas.append(
                "com uma negando e outra perguntando, quem manda é a NEGA — "
                "veio %s" % decidido.get(CHAVE_DA_DECISAO))
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            responder([], [], [], perguntas)
        decidido = json.loads(saida.getvalue())[CHAVE_DA_SAIDA]
        if decidido.get(CHAVE_DA_DECISAO) != DECISAO_DE_PERGUNTAR:
            falhas.append(
                "sem nega, a pergunta chega ao dono com a razão dela — veio "
                "%s" % decidido.get(CHAVE_DA_DECISAO))
        if "pergunta por" not in decidido.get(CHAVE_DA_RAZAO, ""):
            falhas.append("a razão da cerca que pergunta se perdeu no "
                          "caminho")
    for caso in BANCADA:
        titulo, arquivos, negas_esperadas, contextos_esperados = caso[:4]
        forcados = caso[4] if len(caso) > 4 else None
        with tempfile.TemporaryDirectory() as pasta:
            nomes = montar_bancada(pasta, arquivos)
            alvo = forcados if forcados is not None else tuple(nomes)
            razoes, contextos, _, _ = despachar(pasta, CORPO_DE_PROVA, alvo)
            if len(razoes) != negas_esperadas:
                falhas.append("%s — esperava %d razão(ões), veio %d: %s" % (
                    titulo, negas_esperadas, len(razoes), razoes))
            elif len(contextos) != contextos_esperados:
                falhas.append("%s — esperava %d contexto(s), veio %d" % (
                    titulo, contextos_esperados, len(contextos)))
    for titulo, matcher, ferramenta, esperado in BANCADA_DO_ALCANCE:
        veio = esta_no_alcance(matcher, ferramenta)
        if veio is not esperado:
            falhas.append("%s — esperava %s, veio %s" % (
                titulo, esperado, veio))

    for titulo, matcher, negas_esperadas in BANCADA_DO_ROTEIRO:
        with tempfile.TemporaryDirectory() as pasta:
            montar_bancada(pasta, [("nega", CERCA_QUE_NEGA)])
            razoes, _, _, _ = despachar(
                pasta, CORPO_DE_PROVA, (("nega", matcher),))
            if len(razoes) != negas_esperadas:
                falhas.append("%s — esperava %d razão(ões), veio %d" % (
                    titulo, negas_esperadas, len(razoes)))

    total = len(BANCADA) + len(BANCADA_DO_ALCANCE) + len(BANCADA_DO_ROTEIRO)
    if falhas:
        for linha in falhas:
            print("  " + linha)
        print("FALHOU: %d de %d casos — despachante das cercas" % (
            len(falhas), total))
        return 1
    print("OK: %d casos — despachante das cercas" % total)
    return 0


if __name__ == "__main__":
    if BANDEIRA_DE_TESTE in sys.argv:
        sys.exit(testar())
    sys.exit(main())
