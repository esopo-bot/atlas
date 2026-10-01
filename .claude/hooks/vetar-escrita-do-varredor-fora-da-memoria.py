
import json
import os
import sys
from pathlib import Path

VARIAVEL_DA_RAIZ_DO_PROJETO = "CLAUDE_PROJECT_DIR"
NIVEIS_DO_GANCHO_ATE_A_RAIZ = 2
AGENTE_PRESO = "varredor"
PASTA_DA_MEMORIA = ".claude/agent-memory-local/" + AGENTE_PRESO
FERRAMENTAS_QUE_ESCREVEM = ("Write", "Edit", "MultiEdit", "NotebookEdit")
CAMPOS_DE_CAMINHO = ("file_path", "notebook_path")
CAMPO_DA_FERRAMENTA = "tool_name"
CAMPO_DA_ENTRADA = "tool_input"
CAMPO_DO_TIPO_DE_AGENTE = "agent_type"
CAMPO_DO_DIRETORIO = "cwd"
EVENTO_ANTES_DA_FERRAMENTA = "PreToolUse"
DECISAO_DE_NEGAR = "deny"
SILENCIO = 0
BANDEIRA_DE_TESTE = "--testar"

RECUSA = (
    "O varredor só escreve na pasta da memória dele, `{pasta}/`, e isto quer "
    "gravar '{caminho}'. A memória liga Write e Edit em qualquer caminho, e o "
    "dono decidiu em 28/09/2026 que eles ficam presos nessa pasta.\n"
    "O caminho: o que poupa a próxima varredura vai em `{pasta}/MEMORY.md` ou "
    "num arquivo dentro da pasta; o que é do repositório volta na resposta, "
    "com `caminho:linha`, para quem te chamou decidir e gravar."
)
CERCA_CEGA = ("atlas: a cerca da memória do varredor não entendeu o evento "
              "({}: {}) e deixou passar sem medir.")


def raiz_do_projeto_nunca_o_cwd() -> Path:
    declarada = os.environ.get(VARIAVEL_DA_RAIZ_DO_PROJETO)
    if declarada:
        return Path(declarada)
    return Path(__file__).resolve().parents[NIVEIS_DO_GANCHO_ATE_A_RAIZ]


def e_o_agente_preso(entrada: dict) -> bool:
    return entrada.get(CAMPO_DO_TIPO_DE_AGENTE) == AGENTE_PRESO


def escreve_em_arquivo(entrada: dict) -> bool:
    return entrada.get(CAMPO_DA_FERRAMENTA) in FERRAMENTAS_QUE_ESCREVEM


def caminho_do_evento(entrada: dict) -> str:
    dado = entrada.get("tool_input", {}) or {}
    for campo in CAMPOS_DE_CAMINHO:
        valor = dado.get(campo)
        if isinstance(valor, str) and valor.strip():
            return valor.strip()
    return ""


def diretorio_do_evento(entrada: dict):
    diretorio = entrada.get(CAMPO_DO_DIRETORIO)
    if isinstance(diretorio, str) and diretorio.strip():
        return Path(diretorio.strip().replace("\\", "/"))
    return None


def resolvido(caminho: Path) -> Path:
    return Path(os.path.normcase(caminho.resolve()))


def alvo_resolvido(caminho: str, base: Path) -> Path:
    alvo = Path(caminho.replace("\\", "/"))
    if not alvo.is_absolute():
        alvo = base / alvo
    return resolvido(alvo)


def pastas_da_memoria(raiz: Path, diretorio) -> set:
    bases = [raiz] if diretorio is None else [raiz, diretorio]
    return {resolvido(base / PASTA_DA_MEMORIA) for base in bases}


def recusar_fora_da_memoria(caminho: str) -> int:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": EVENTO_ANTES_DA_FERRAMENTA,
        "permissionDecision": DECISAO_DE_NEGAR,
        "permissionDecisionReason": RECUSA.format(pasta=PASTA_DA_MEMORIA,
                                                  caminho=caminho),
    }}))
    return SILENCIO


def decidir() -> int:
    entrada = json.load(sys.stdin)
    if not e_o_agente_preso(entrada) or not escreve_em_arquivo(entrada):
        return SILENCIO
    caminho = caminho_do_evento(entrada)
    if not caminho:
        return SILENCIO
    raiz = raiz_do_projeto_nunca_o_cwd()
    diretorio = diretorio_do_evento(entrada)
    alvo = alvo_resolvido(caminho, diretorio or raiz)
    if pastas_da_memoria(raiz, diretorio) & set(alvo.parents):
        return SILENCIO
    return recusar_fora_da_memoria(caminho)


def main() -> int:
    try:
        return decidir()
    except Exception as falha:
        print(CERCA_CEGA.format(type(falha).__name__, falha), file=sys.stderr)
        return SILENCIO


def evento_de_escrita(ferramenta: str, caminho, agente: str = AGENTE_PRESO,
                      cwd=None, campo: str = "file_path") -> dict:
    corpo = {CAMPO_DA_FERRAMENTA: ferramenta,
             CAMPO_DA_ENTRADA: {campo: str(caminho)}}
    if agente:
        corpo[CAMPO_DO_TIPO_DE_AGENTE] = agente
    if cwd is not None:
        corpo[CAMPO_DO_DIRETORIO] = str(cwd)
    return corpo


def com_a_letra_da_unidade_trocada(caminho: Path) -> str:
    texto = str(caminho)
    return texto[0].swapcase() + texto[1:]


def testar() -> int:
    import io
    import tempfile
    from contextlib import redirect_stderr, redirect_stdout
    falhas = []
    raiz_herdada = os.environ.get(VARIAVEL_DA_RAIZ_DO_PROJETO)

    def veredito(corpo) -> tuple:
        saida, erro = io.StringIO(), io.StringIO()
        texto = corpo if isinstance(corpo, str) else json.dumps(corpo)
        guardado, sys.stdin = sys.stdin, io.StringIO(texto)
        try:
            with redirect_stdout(saida), redirect_stderr(erro):
                main()
        finally:
            sys.stdin = guardado
        return DECISAO_DE_NEGAR in saida.getvalue(), saida.getvalue(), \
            erro.getvalue()

    with tempfile.TemporaryDirectory(prefix="cerca-varredor-") as pasta:
        raiz = Path(pasta) / "arvore"
        memoria = raiz / PASTA_DA_MEMORIA
        memoria.mkdir(parents=True)
        outra_arvore = Path(pasta) / "worktree-da-sessao"
        fora = raiz / "conhecimento" / "nota.md"
        os.environ[VARIAVEL_DA_RAIZ_DO_PROJETO] = str(raiz)

        de_outro = raiz / ".claude" / "agent-memory-local"
        barra = [
            ("Write fora da memória",
             evento_de_escrita("Write", fora.as_posix())),
            ("Edit fora da memória",
             evento_de_escrita("Edit", fora.as_posix())),
            ("MultiEdit fora da memória",
             evento_de_escrita("MultiEdit", fora)),
            ("caderno fora da memória, pelo campo do caderno",
             evento_de_escrita("NotebookEdit", raiz / "analise.ipynb",
                               campo="notebook_path")),
            ("caminho relativo, resolvido pelo diretório do evento",
             evento_de_escrita("Write", "conhecimento/nota.md", cwd=raiz)),
            ("`..` que sai da memória",
             evento_de_escrita(
                 "Write",
                 memoria.as_posix() + "/../../../conhecimento/nota.md")),
            ("`..` relativo, a partir da memória",
             evento_de_escrita("Edit", "../../../conhecimento/nota.md",
                               cwd=memoria)),
            ("barra invertida",
             evento_de_escrita("Write", fora.as_posix().replace("/", "\\"))),
            ("pasta vizinha que começa com o mesmo nome",
             evento_de_escrita("Write",
                               de_outro / "varredor-vizinho" / "nota.md")),
            ("memória de outro agente",
             evento_de_escrita("Write", de_outro / "escritor" / "MEMORY.md")),
        ]
        passa = [
            ("o MEMORY.md da memória",
             evento_de_escrita("Write", memoria / "MEMORY.md")),
            ("Edit em subpasta da memória",
             evento_de_escrita("Edit", memoria / "assuntos" / "busca.md")),
            ("relativo, dentro da memória",
             evento_de_escrita("Write", PASTA_DA_MEMORIA + "/MEMORY.md",
                               cwd=raiz)),
            ("`..` que volta para dentro da memória",
             evento_de_escrita(
                 "Write", memoria.as_posix() + "/assuntos/../MEMORY.md")),
            ("barra invertida, dentro da memória",
             evento_de_escrita(
                 "Write",
                 (memoria / "MEMORY.md").as_posix().replace("/", "\\"))),
            ("a memória na árvore do diretório do evento, quando a sessão "
             "entrou numa worktree",
             evento_de_escrita("Write",
                               outra_arvore / PASTA_DA_MEMORIA / "MEMORY.md",
                               cwd=outra_arvore)),
            ("outro agente escreve fora da memória",
             evento_de_escrita("Write", fora, agente="escritor")),
            ("a sessão principal, sem agent_type",
             evento_de_escrita("Write", fora, agente="")),
            ("o varredor lê fora da memória",
             evento_de_escrita("Read", fora)),
            ("sem caminho no evento",
             {CAMPO_DA_FERRAMENTA: "Write", CAMPO_DA_ENTRADA: {},
              CAMPO_DO_TIPO_DE_AGENTE: AGENTE_PRESO}),
        ]
        if os.name == "nt":
            barra.append((
                "letra da unidade em outra caixa, fora da memória",
                evento_de_escrita("Write",
                                  com_a_letra_da_unidade_trocada(fora))))
            passa.append((
                "letra da unidade em outra caixa, dentro da memória",
                evento_de_escrita("Write", com_a_letra_da_unidade_trocada(
                    memoria / "MEMORY.md"))))

        for titulo, corpo in barra:
            negou, _, _ = veredito(corpo)
            if not negou:
                falhas.append(f"{titulo} — devia barrar e deixou passar")
        for titulo, corpo in passa:
            negou, _, _ = veredito(corpo)
            if negou:
                falhas.append(f"{titulo} — devia passar e barrou")

        negou, texto, _ = veredito(evento_de_escrita("Write", fora))
        if not negou or PASTA_DA_MEMORIA not in texto or "nota.md" not in texto:
            falhas.append("a recusa devia nomear a pasta da memória e o "
                          "arquivo recusado")

        negou, _, erro = veredito("[]")
        if negou or "sem medir" not in erro:
            falhas.append("evento ilegível devia deixar passar e avisar que "
                          "não mediu")

    if raiz_herdada is None:
        os.environ.pop(VARIAVEL_DA_RAIZ_DO_PROJETO, None)
    else:
        os.environ[VARIAVEL_DA_RAIZ_DO_PROJETO] = raiz_herdada
    total = len(barra) + len(passa) + 2
    if falhas:
        for linha in falhas:
            print("  " + linha)
        print("FALHOU: %d de %d casos — cerca da memória do varredor"
              % (len(falhas), total))
        return 1
    print("OK: %d casos — cerca da memória do varredor" % total)
    return 0


if __name__ == "__main__":
    if BANDEIRA_DE_TESTE in sys.argv:
        sys.exit(testar())
    sys.exit(main())
