
import json
import os
import sys
import tempfile
from pathlib import Path

VARIAVEL_DA_RAIZ_DO_PROJETO = "CLAUDE_PROJECT_DIR"
NIVEIS_DO_GANCHO_ATE_A_RAIZ = 2
ARQUIVO_DA_CONFIGURACAO = "nucleo/configuracao.json"
CAMPO_DO_TETO = "teto_de_agentes_por_sessao"
TETO_QUANDO_NAO_DECLARADO = 24
TETO_QUE_DESLIGA = 0

EVENTO_ANTES_DA_FERRAMENTA = "PreToolUse"
DECISAO_DE_NEGAR = "deny"
CHAVE_DA_SAIDA = "hookSpecificOutput"
CHAVE_DO_CONTEXTO = "additionalContext"
SILENCIO = 0
BANDEIRA_DE_TESTE = "--testar"

FERRAMENTAS_QUE_DISPARAM = ("Task", "Agent", "Workflow")
FERRAMENTA_DE_ROTEIRO = "Workflow"
CAMPO_DA_FERRAMENTA = "tool_name"
CAMPO_DA_ENTRADA = "tool_input"
CAMPO_DA_SESSAO = "session_id"
CAMPO_DO_AGENTE = "agent_id"
CAMPO_DO_RASCUNHO = "scratchpad_dir"
CAMPO_DO_ROTEIRO = "script"

PREFIXO_DO_PLACAR = "atlas-enxame-"
SUFIXO_DO_PLACAR = ".json"
CHAVE_DOS_DISPAROS = "disparos"
CHAVE_DOS_AGENTES_VISTOS = "agentes_vistos"
SESSAO_SEM_NOME = "sessao-sem-nome"

CHAMADA_DE_AGENTE = "agent("
MULTIPLICADORES = ("parallel(", "pipeline(", "while ", "for (", ".map(")

RECUSA = (
    "Regra 6 da camada: esta sessão já pôs {vistos} agente(s) para rodar, e o "
    "teto declarado é {teto}. Enxame não é profundidade: poucas perguntas "
    "viram dezenas de agentes, espera longa e gasto que não aparece na "
    "conta que a sessão mostra.\n"
    "O caminho: responda com as ferramentas que você já tem, ou reaproveite "
    "um agente que já rodou. Se o trabalho exige mesmo mais gente, o teto é "
    f"do dono: ele o sobe em {ARQUIVO_DA_CONFIGURACAO}, campo "
    f"{CAMPO_DO_TETO}, e o motor tem os dele em "
    "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS e "
    "CLAUDE_CODE_WORKFLOW_MAX_CONCURRENT_AGENTS."
)

AVISO_DO_ROTEIRO = (
    "atlas: este roteiro declara {chamadas} chamada(s) de agente e usa "
    "multiplicador ({multiplicador}), então o total real pode ser muito "
    "maior que a conta literal. A sessão já viu {vistos} de {teto} agentes. "
    "Dimensione o roteiro para caber no que resta, e diga no log quantos "
    "agentes ele vai abrir."
)

CERCA_CEGA = (
    "atlas: a cerca de enxame não entendeu este evento ({erro}: {detalhe}) e "
    "deixou passar sem medir. O disparo não entrou no placar da sessão, então "
    "o teto pode ser ultrapassado sem ninguém ver. Isto vai ao dono na "
    "primeira resposta: silêncio de cerca não é aprovação."
)

CONTEXTO_DO_PLACAR = (
    "atlas: {vistos} de {teto} agentes desta sessão já foram usados."
)

QUANDO_AVISAR_QUE_RESTA_POUCO = 2


def raiz_do_projeto_nunca_o_cwd() -> Path:
    declarada = os.environ.get(VARIAVEL_DA_RAIZ_DO_PROJETO)
    if declarada:
        return Path(declarada)
    return Path(__file__).resolve().parents[NIVEIS_DO_GANCHO_ATE_A_RAIZ]


def teto_declarado(raiz: Path) -> int:
    try:
        cru = (raiz / ARQUIVO_DA_CONFIGURACAO).read_text(encoding="utf-8")
        declarado = json.loads(cru)
    except (OSError, ValueError):
        return TETO_QUANDO_NAO_DECLARADO
    if not isinstance(declarado, dict):
        return TETO_QUANDO_NAO_DECLARADO
    valor = declarado.get(CAMPO_DO_TETO)
    if isinstance(valor, bool) or not isinstance(valor, int) or valor < 0:
        return TETO_QUANDO_NAO_DECLARADO
    return valor


def pasta_do_placar(entrada: dict) -> Path:
    rascunho = entrada.get(CAMPO_DO_RASCUNHO)
    if isinstance(rascunho, str) and rascunho.strip():
        candidata = Path(rascunho.strip())
        if candidata.is_dir():
            return candidata
    return Path(tempfile.gettempdir())


def nome_da_sessao(entrada: dict) -> str:
    bruto = entrada.get(CAMPO_DA_SESSAO)
    if not isinstance(bruto, str) or not bruto.strip():
        return SESSAO_SEM_NOME
    limpo = "".join(c for c in bruto.strip() if c.isalnum() or c in "-_")
    return limpo or SESSAO_SEM_NOME


def caminho_do_placar(entrada: dict) -> Path:
    nome = PREFIXO_DO_PLACAR + nome_da_sessao(entrada) + SUFIXO_DO_PLACAR
    return pasta_do_placar(entrada) / nome


def ler_placar(caminho: Path) -> dict:
    try:
        dado = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {CHAVE_DOS_DISPAROS: 0, CHAVE_DOS_AGENTES_VISTOS: []}
    if not isinstance(dado, dict):
        return {CHAVE_DOS_DISPAROS: 0, CHAVE_DOS_AGENTES_VISTOS: []}
    disparos = dado.get(CHAVE_DOS_DISPAROS)
    vistos = dado.get(CHAVE_DOS_AGENTES_VISTOS)
    return {
        CHAVE_DOS_DISPAROS: disparos if isinstance(disparos, int) else 0,
        CHAVE_DOS_AGENTES_VISTOS: vistos if isinstance(vistos, list) else [],
    }


def gravar_placar(caminho: Path, placar: dict) -> None:
    try:
        caminho.write_text(json.dumps(placar), encoding="utf-8")
    except OSError:
        pass


def registrar_o_agente_que_agiu(placar: dict, entrada: dict) -> bool:
    identidade = entrada.get(CAMPO_DO_AGENTE)
    if not isinstance(identidade, str) or not identidade.strip():
        return False
    vistos = placar[CHAVE_DOS_AGENTES_VISTOS]
    if identidade in vistos:
        return False
    vistos.append(identidade)
    return True


def quantos_ja_rodaram(placar: dict) -> int:
    return max(placar[CHAVE_DOS_DISPAROS],
               len(placar[CHAVE_DOS_AGENTES_VISTOS]))


def roteiro_do_evento(entrada: dict) -> str:
    dado = entrada.get(CAMPO_DA_ENTRADA) or {}
    if not isinstance(dado, dict):
        return ""
    roteiro = dado.get(CAMPO_DO_ROTEIRO)
    return roteiro if isinstance(roteiro, str) else ""


def multiplicador_do_roteiro(roteiro: str) -> str:
    for marca in MULTIPLICADORES:
        if marca in roteiro:
            return marca
    return ""


def chamadas_do_roteiro(roteiro: str) -> int:
    return roteiro.count(CHAMADA_DE_AGENTE)


def negar_o_disparo(vistos: int, teto: int) -> int:
    print(json.dumps({CHAVE_DA_SAIDA: {
        "hookEventName": EVENTO_ANTES_DA_FERRAMENTA,
        "permissionDecision": DECISAO_DE_NEGAR,
        "permissionDecisionReason": RECUSA.format(vistos=vistos, teto=teto),
    }}))
    return SILENCIO


def contextualizar(texto: str) -> int:
    print(json.dumps({CHAVE_DA_SAIDA: {
        "hookEventName": EVENTO_ANTES_DA_FERRAMENTA,
        CHAVE_DO_CONTEXTO: texto,
    }}))
    return SILENCIO


def decidir() -> int:
    entrada = json.load(sys.stdin)
    teto = teto_declarado(raiz_do_projeto_nunca_o_cwd())
    if teto == TETO_QUE_DESLIGA:
        return SILENCIO
    caminho = caminho_do_placar(entrada)
    placar = ler_placar(caminho)
    mudou = registrar_o_agente_que_agiu(placar, entrada)
    ferramenta = entrada.get(CAMPO_DA_FERRAMENTA)
    if ferramenta not in FERRAMENTAS_QUE_DISPARAM:
        if mudou:
            gravar_placar(caminho, placar)
        return SILENCIO
    vistos = quantos_ja_rodaram(placar)
    if vistos >= teto:
        gravar_placar(caminho, placar)
        return negar_o_disparo(vistos, teto)
    placar[CHAVE_DOS_DISPAROS] = placar[CHAVE_DOS_DISPAROS] + 1
    gravar_placar(caminho, placar)
    if ferramenta == FERRAMENTA_DE_ROTEIRO:
        roteiro = roteiro_do_evento(entrada)
        multiplicador = multiplicador_do_roteiro(roteiro)
        if multiplicador:
            return contextualizar(AVISO_DO_ROTEIRO.format(
                chamadas=chamadas_do_roteiro(roteiro),
                multiplicador=multiplicador.strip(), vistos=vistos, teto=teto))
    if teto - vistos <= QUANDO_AVISAR_QUE_RESTA_POUCO:
        return contextualizar(CONTEXTO_DO_PLACAR.format(vistos=vistos,
                                                        teto=teto))
    return SILENCIO


def main() -> int:
    try:
        return decidir()
    except Exception as falha:
        return contextualizar(CERCA_CEGA.format(
            erro=type(falha).__name__, detalhe=falha))


def evento_de_enxame(ferramenta: str, sessao: str, rascunho: str,
                     agente: str = "", roteiro: str = "") -> str:
    corpo = {CAMPO_DA_FERRAMENTA: ferramenta, CAMPO_DA_SESSAO: sessao,
             CAMPO_DO_RASCUNHO: rascunho, CAMPO_DA_ENTRADA: {}}
    if agente:
        corpo[CAMPO_DO_AGENTE] = agente
    if roteiro:
        corpo[CAMPO_DA_ENTRADA] = {CAMPO_DO_ROTEIRO: roteiro}
    return json.dumps(corpo)


def testar() -> int:
    import io
    from contextlib import redirect_stdout, redirect_stderr
    falhas = []
    with tempfile.TemporaryDirectory(prefix="cerca-enxame-") as pasta:
        raiz = Path(pasta) / "arvore"
        (raiz / "nucleo").mkdir(parents=True)
        rascunho = Path(pasta) / "rascunho"
        rascunho.mkdir()
        os.environ[VARIAVEL_DA_RAIZ_DO_PROJETO] = str(raiz)

        def declarar(teto) -> None:
            (raiz / ARQUIVO_DA_CONFIGURACAO).write_text(
                json.dumps({CAMPO_DO_TETO: teto}), encoding="utf-8")

        def veredito(corpo: str):
            saida = io.StringIO()
            guardado, sys.stdin = sys.stdin, io.StringIO(corpo)
            try:
                with redirect_stdout(saida), redirect_stderr(io.StringIO()):
                    decidir()
            finally:
                sys.stdin = guardado
            return saida.getvalue()

        def resposta_da_cerca_inteira(corpo: str) -> str:
            saida = io.StringIO()
            guardado, sys.stdin = sys.stdin, io.StringIO(corpo)
            try:
                with redirect_stdout(saida), redirect_stderr(io.StringIO()):
                    main()
            finally:
                sys.stdin = guardado
            return saida.getvalue()

        declarar(3)
        for volta in range(3):
            resposta = veredito(evento_de_enxame("Task", "s1", str(rascunho)))
            if DECISAO_DE_NEGAR in resposta:
                falhas.append("disparo %d de 3 devia passar e foi negado"
                              % (volta + 1))
        if DECISAO_DE_NEGAR not in veredito(evento_de_enxame("Task", "s1",
                                                   str(rascunho))):
            falhas.append("o disparo acima do teto devia ser negado e passou")

        if DECISAO_DE_NEGAR in veredito(evento_de_enxame("Task", "s2", str(rascunho))):
            falhas.append("outra sessão tem placar próprio e foi negada")

        declarar(3)
        for indice in range(3):
            veredito(evento_de_enxame("Bash", "s3", str(rascunho),
                            agente="agente-%d" % indice))
        if DECISAO_DE_NEGAR not in veredito(evento_de_enxame("Task", "s3",
                                                   str(rascunho))):
            falhas.append(
                "três agentes distintos agiram na sessão e o disparo seguinte "
                "devia ser negado: é assim que a cerca enxerga quem nasceu "
                "dentro do motor de roteiro, que não pede Task")

        declarar(3)
        for _ in range(4):
            veredito(evento_de_enxame("Bash", "s4", str(rascunho), agente="o-mesmo"))
        if DECISAO_DE_NEGAR in veredito(evento_de_enxame("Task", "s4", str(rascunho))):
            falhas.append("o mesmo agente agindo quatro vezes conta uma só")

        declarar(9)
        resposta = veredito(evento_de_enxame("Workflow", "s5", str(rascunho),
                                   roteiro="await parallel(x.map(f))"))
        if CHAVE_DO_CONTEXTO not in resposta:
            falhas.append("roteiro com multiplicador devia avisar e não avisou")
        resposta = veredito(evento_de_enxame("Workflow", "s6", str(rascunho),
                                   roteiro="await agent(um)"))
        if CHAVE_DO_CONTEXTO in resposta:
            falhas.append("roteiro sem multiplicador não devia avisar")

        declarar(TETO_QUE_DESLIGA)
        for _ in range(5):
            if veredito(evento_de_enxame("Task", "s7", str(rascunho))).strip():
                falhas.append("teto zero desliga a cerca e ela falou")
                break

        declarar(2)
        if DECISAO_DE_NEGAR in veredito(evento_de_enxame("Read", "s8", str(rascunho))):
            falhas.append("ferramenta que não dispara agente não se nega")

        (raiz / ARQUIVO_DA_CONFIGURACAO).write_text("{", encoding="utf-8")
        if teto_declarado(raiz) != TETO_QUANDO_NAO_DECLARADO:
            falhas.append("configuração quebrada devia cair no teto padrão")

        (raiz / ARQUIVO_DA_CONFIGURACAO).write_text("[]", encoding="utf-8")
        if teto_declarado(raiz) != TETO_QUANDO_NAO_DECLARADO:
            falhas.append("configuração que lê mas não é objeto devia cair no "
                          "teto padrão, e não derrubar a cerca inteira")

        declarar(2)
        if CHAVE_DO_CONTEXTO not in resposta_da_cerca_inteira("[]"):
            falhas.append("evento que a cerca não entende devia avisar quem "
                          "lê a sessão, não só o registro de erro que "
                          "ninguém abre")

    total = 13
    if falhas:
        for linha in falhas:
            print("  " + linha)
        print("FALHOU: %d de %d casos — cerca de enxame de agentes"
              % (len(falhas), total))
        return 1
    print("OK: %d casos — cerca de enxame de agentes" % total)
    return 0


if __name__ == "__main__":
    if BANDEIRA_DE_TESTE in sys.argv:
        sys.exit(testar())
    sys.exit(main())
