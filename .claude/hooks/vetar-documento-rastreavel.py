
import json
import os
import subprocess
import sys
from pathlib import Path

MARCA_DE_REPOSITORIO = ".git"
VARIAVEL_DA_RAIZ_DO_PROJETO = "CLAUDE_PROJECT_DIR"
NIVEIS_DO_GANCHO_ATE_A_RAIZ = 2
COMANDO_DO_GIT_QUE_IGNORA = ("git", "check-ignore", "-q")
TEMPO_DO_GIT = 20
EVENTO_ANTES_DA_FERRAMENTA = "PreToolUse"
DECISAO_DE_NEGAR = "deny"
SILENCIO = 0
BANDEIRA_DE_TESTE = "--testar"

CAMPOS_DE_CAMINHO = ("file_path", "notebook_path")
EXTENSOES_DE_DOCUMENTO = (".pptx", ".docx", ".xlsx", ".pdf", ".odt", ".ods",
                          ".odp", ".key", ".pages", ".numbers", ".rtf")
ARQUIVO_DOS_DOCUMENTOS_VERSIONADOS = ".claude/documentos-versionados.txt"
MARCA_DE_COMENTARIO = "#"
MARCA_DE_PASTA = "/"

RECUSA = (
    "Regra 13 da camada: isto quer gerar '{}' em caminho que o git RASTREIA, "
    "e documento binário não se revisa — a varredura não o lê e ninguém o lê "
    "num diff, então ele entra no commit às cegas. Foi assim que uma "
    "apresentação com dado pessoal ficou horas na raiz de um repositório, com "
    "uma trava só entre ela e o repositório público.\n"
    "O caminho: grave em pasta que este repositório já declarou fora do "
    "git{}. Se este documento DEVE ser versionado, declare o caminho em "
    f"{ARQUIVO_DOS_DOCUMENTOS_VERSIONADOS} e a cerca cala."
)
PASTAS_QUE_SERVEM = " — as que existem aqui: {}"
SEM_GIT = ("atlas: `git check-ignore` não respondeu em '{}', então a cerca de "
           "documento não mediu nada e deixou passar — sem git não há o que "
           "rastrear, logo não há o que vazar.")


def raiz_do_alvo(caminho: str, declarada: Path) -> Path:
    alvo = Path(str(caminho).replace("\\", "/"))
    if not alvo.is_absolute():
        return declarada
    try:
        alvo.resolve().relative_to(declarada.resolve())
        return declarada
    except (ValueError, OSError):
        pass
    donas = [p for p in alvo.resolve().parents
             if (p / MARCA_DE_REPOSITORIO).exists()]
    return donas[-1] if donas else declarada


def raiz_do_projeto_nunca_o_cwd() -> Path:
    declarada = os.environ.get(VARIAVEL_DA_RAIZ_DO_PROJETO)
    if declarada:
        return Path(declarada)
    return Path(__file__).resolve().parents[NIVEIS_DO_GANCHO_ATE_A_RAIZ]


def caminho_do_evento(entrada: dict) -> str:
    dado = entrada.get("tool_input", {}) or {}
    for campo in CAMPOS_DE_CAMINHO:
        valor = dado.get(campo)
        if isinstance(valor, str) and valor.strip():
            return valor.strip()
    return ""


def e_documento(caminho: str) -> bool:
    return caminho.lower().endswith(EXTENSOES_DE_DOCUMENTO)


def linhas_declaradas(raiz: Path) -> list:
    try:
        cru = (raiz / ARQUIVO_DOS_DOCUMENTOS_VERSIONADOS).read_text(
            encoding="utf-8")
    except OSError:
        return []
    linhas = []
    for linha in cru.splitlines():
        limpa = linha.strip()
        if limpa and not limpa.startswith(MARCA_DE_COMENTARIO):
            linhas.append(limpa)
    return linhas


def foi_declarado(caminho: str, declarados: list) -> bool:
    normal = caminho.replace("\\", "/")
    for linha in declarados:
        if linha.endswith(MARCA_DE_PASTA):
            if f"/{linha}" in f"/{normal}" or normal.startswith(linha):
                return True
        elif normal == linha or normal.endswith(f"/{linha}"):
            return True
    return False


def o_git_ignora(raiz: Path, caminho: str):
    try:
        feito = subprocess.run(
            [*COMANDO_DO_GIT_QUE_IGNORA, "--", caminho.replace("\\", "/")],
            cwd=str(raiz), capture_output=True, timeout=TEMPO_DO_GIT)
    except (OSError, subprocess.SubprocessError):
        return None
    if feito.returncode == 0:
        return True
    if feito.returncode == 1:
        return False
    return None


def pastas_fora_do_git(raiz: Path) -> list:
    try:
        cru = (raiz / ".gitignore").read_text(encoding="utf-8")
    except OSError:
        return []
    achadas = []
    for linha in cru.splitlines():
        limpa = linha.strip()
        if not limpa.startswith("/") or limpa.startswith("/*"):
            continue
        nome = limpa.lstrip("/").rstrip("*").rstrip("/")
        if nome and "." not in nome and nome not in achadas:
            achadas.append(nome + "/")
    return achadas


def negar(caminho: str, sugestao: str) -> int:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": EVENTO_ANTES_DA_FERRAMENTA,
        "permissionDecision": DECISAO_DE_NEGAR,
        "permissionDecisionReason": RECUSA.format(caminho, sugestao),
    }}, ensure_ascii=False))
    return SILENCIO


def decidir() -> int:
    entrada = json.load(sys.stdin)
    caminho = caminho_do_evento(entrada)
    if not caminho or not e_documento(caminho):
        return SILENCIO
    raiz = raiz_do_projeto_nunca_o_cwd()
    if foi_declarado(caminho, linhas_declaradas(raiz)):
        return SILENCIO
    dona = raiz_do_alvo(caminho, raiz)
    ignorado = o_git_ignora(dona, caminho)
    if ignorado is None:
        print(SEM_GIT.format(caminho), file=sys.stderr)
        return SILENCIO
    if ignorado:
        return SILENCIO
    pastas = pastas_fora_do_git(dona)
    sugestao = PASTAS_QUE_SERVEM.format(", ".join(pastas)) if pastas else ""
    return negar(caminho, sugestao)


def main() -> int:
    try:
        return decidir()
    except Exception as falha:
        print("atlas: a cerca de documento não entendeu o evento (%s: %s) e "
              "deixou passar sem medir." % (type(falha).__name__, falha),
              file=sys.stderr)
        return SILENCIO


BARRA = (
    ("apresentação na raiz", "comparacao.pptx"),
    ("planilha na raiz", "numeros.xlsx"),
    ("texto na pasta de conhecimento", "conhecimento/relatorio.docx"),
    ("pdf em pasta rastreada", "docs/manual.pdf"),
    ("caminho com barra invertida", "conhecimento\\nota.pptx"),
)

DEIXA_PASSAR = (
    ("código, que se revisa em diff", "montar.py"),
    ("markdown, que se revisa em diff", "conhecimento/pagina.md"),
    ("documento em pasta fora do git", "trabalho/comparacao.pptx"),
    ("documento em outra pasta fora do git", "projetos/x/planilha.xlsx"),
    ("sem caminho no evento", ""),
)


def evento(caminho: str) -> str:
    return json.dumps({"tool_name": "Write",
                       "tool_input": {"file_path": caminho}})


def testar() -> int:
    import io
    import tempfile
    falhas = []
    with tempfile.TemporaryDirectory(prefix="cerca-documento-") as pasta:
        raiz = Path(pasta) / "arvore"
        raiz.mkdir()
        (raiz / ".gitignore").write_text(
            "/trabalho/\n/projetos/*\n!/projetos/LEIAME.md\n",
            encoding="utf-8")
        (raiz / ".claude").mkdir()
        subprocess.run(["git", "init", "-q"], cwd=raiz, capture_output=True)
        import os
        os.environ["CLAUDE_PROJECT_DIR"] = str(raiz)

        def veredito(caminho: str) -> bool:
            saida = io.StringIO()
            guardado, sys.stdin = sys.stdin, io.StringIO(evento(caminho))
            try:
                from contextlib import redirect_stdout, redirect_stderr
                with redirect_stdout(saida), redirect_stderr(io.StringIO()):
                    decidir()
            finally:
                sys.stdin = guardado
            return DECISAO_DE_NEGAR in saida.getvalue()

        for titulo, caminho in BARRA:
            if not veredito(caminho):
                falhas.append("%s — devia barrar '%s' e deixou passar"
                              % (titulo, caminho))
        for titulo, caminho in DEIXA_PASSAR:
            if veredito(caminho):
                falhas.append("%s — devia passar '%s' e barrou"
                              % (titulo, caminho))

        (raiz / ARQUIVO_DOS_DOCUMENTOS_VERSIONADOS).write_text(
            "# os que este repositório versiona de propósito\ndocs/manual.pdf\n",
            encoding="utf-8")
        if veredito("docs/manual.pdf"):
            falhas.append("declarado na lista — devia passar e barrou")
        if not veredito("docs/outro.pdf"):
            falhas.append("fora da lista — devia barrar e passou")

        ao_lado = raiz.parent / (raiz.name + "-ao-lado")
        (ao_lado / "conhecimento").mkdir(parents=True)
        subprocess.run(["git", "init", "-q"], cwd=ao_lado,
                       capture_output=True)
        de_la = str(ao_lado / "conhecimento" / "proposta.pptx")
        if not veredito(de_la):
            falhas.append(
                "documento em caminho rastreado de OUTRA árvore de trabalho "
                "— devia barrar e passou. O git se pergunta na árvore do "
                "ALVO; antes disso a cerca calava em toda worktree")
        if raiz_do_alvo(de_la, raiz) != ao_lado:
            falhas.append("a raiz do alvo devia ser a árvore dele")
        if raiz_do_alvo("conhecimento/x.pptx", raiz) != raiz:
            falhas.append("caminho relativo devia ficar na raiz declarada")

    total = len(BARRA) + len(DEIXA_PASSAR) + 5
    if falhas:
        for linha in falhas:
            print("  " + linha)
        print("FALHOU: %d de %d casos — cerca de documento rastreável"
              % (len(falhas), total))
        return 1
    print("OK: %d casos — cerca de documento rastreável" % total)
    return 0


if __name__ == "__main__":
    if BANDEIRA_DE_TESTE in sys.argv:
        sys.exit(testar())
    sys.exit(main())
