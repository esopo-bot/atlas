
import json
import os
import subprocess
import sys
from pathlib import Path

VARIAVEL_DA_RAIZ_DO_PROJETO = "CLAUDE_PROJECT_DIR"
NIVEIS_DO_GANCHO_ATE_A_RAIZ = 2
MARCA_DE_REPOSITORIO = ".git"
CAMPOS_DE_CAMINHO = ("file_path", "notebook_path")
CAMPO_DO_DIRETORIO = "cwd"
MARCA_DE_ETAPA_NO_AMBIENTE = "ENCADEADOR_ETAPA"
COMANDO_DO_GIT_QUE_IGNORA = ("git", "check-ignore", "-q")
CHAVE_DA_DECLARACAO = "camada.raizSoEspelhaAIntegracao"
COMANDO_DA_DECLARACAO = ("git", "config", "--local", "--bool", "--get",
                         CHAVE_DA_DECLARACAO)
TEMPO_DO_GIT = 20
EVENTO_ANTES_DA_FERRAMENTA = "PreToolUse"
DECISAO_DE_NEGAR = "deny"
SILENCIO = 0
BANDEIRA_DE_TESTE = "--testar"

RECUSA = (
    "Isto quer gravar '{caminho}' direto na raiz, e esta raiz se declarou, na "
    f"configuração local do git ({CHAVE_DA_DECLARACAO}), espelho da "
    "integração: ela avança sozinha na abertura, e o que o git não ignora se "
    "edita numa worktree. Raiz editada à mão fica suja, deixa de avançar, e "
    "toda sessão aberta nela passa a rodar ganchos velhos.\n"
    "O caminho: abra uma worktree da integração — `git worktree add "
    ".claude/worktrees/<nome> -b issue/<n>-<assunto> origin/<integração>`, "
    "com a integração de `branches.integracao` em nucleo/executor.json; no "
    "Claude Code, a ferramenta EnterWorktree — e edite lá. O que o git ignora "
    "(configuração local, perfis, credenciais) segue livre na raiz."
)
SEM_GIT = ("atlas: `git check-ignore` não respondeu em '{}', então a cerca da "
           "raiz não mediu e deixou passar — sem a resposta do git ela não "
           "sabe se o arquivo é rastreado.")
SEM_GIT_NA_DECLARACAO = (
    "atlas: `git config` não respondeu em '{}', então a cerca da raiz não "
    "mediu se ela se declarou espelho da integração, e deixou passar.")


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


def alvo_absoluto(caminho: str, entrada: dict) -> Path:
    alvo = Path(caminho.replace("\\", "/"))
    if alvo.is_absolute():
        return alvo.resolve()
    diretorio = entrada.get(CAMPO_DO_DIRETORIO)
    base = Path(diretorio) if isinstance(diretorio, str) and diretorio \
        else raiz_do_projeto_nunca_o_cwd()
    return (base / alvo).resolve()


def arvore_dona(alvo: Path):
    for pasta in (alvo, *alvo.parents):
        if (pasta / MARCA_DE_REPOSITORIO).exists():
            return pasta
    return None


def declara_que_so_espelha(raiz: Path):
    try:
        feito = subprocess.run(list(COMANDO_DA_DECLARACAO), cwd=str(raiz),
                               capture_output=True, text=True,
                               timeout=TEMPO_DO_GIT)
    except (OSError, subprocess.SubprocessError):
        return None
    if feito.returncode == 0:
        return feito.stdout.strip() == "true"
    if feito.returncode == 1:
        return False
    return None


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


def recusar_a_escrita(caminho: str) -> int:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": EVENTO_ANTES_DA_FERRAMENTA,
        "permissionDecision": DECISAO_DE_NEGAR,
        "permissionDecisionReason": RECUSA.format(caminho=caminho),
    }}))
    return SILENCIO


def decidir() -> int:
    entrada = json.load(sys.stdin)
    caminho = caminho_do_evento(entrada)
    if not caminho:
        return SILENCIO
    alvo = alvo_absoluto(caminho, entrada)
    dona = arvore_dona(alvo)
    if dona is None or not (dona / MARCA_DE_REPOSITORIO).is_dir():
        return SILENCIO
    declarada = declara_que_so_espelha(dona)
    if declarada is None:
        print(SEM_GIT_NA_DECLARACAO.format(dona), file=sys.stderr)
        return SILENCIO
    if not declarada:
        return SILENCIO
    relativo = alvo.relative_to(dona).as_posix()
    if relativo == MARCA_DE_REPOSITORIO or \
            relativo.startswith(MARCA_DE_REPOSITORIO + "/"):
        return SILENCIO
    ignorado = o_git_ignora(dona, relativo)
    if ignorado is None:
        print(SEM_GIT.format(caminho), file=sys.stderr)
        return SILENCIO
    if ignorado:
        return SILENCIO
    return recusar_a_escrita(caminho)


def main() -> int:
    try:
        return decidir()
    except Exception as falha:
        print("atlas: a cerca da raiz não entendeu o evento (%s: %s) e deixou "
              "passar sem medir." % (type(falha).__name__, falha),
              file=sys.stderr)
        return SILENCIO


def testar() -> int:
    import io
    import tempfile
    from contextlib import redirect_stderr, redirect_stdout
    global COMANDO_DO_GIT_QUE_IGNORA, COMANDO_DA_DECLARACAO
    falhas = []
    marca_herdada = os.environ.pop(MARCA_DE_ETAPA_NO_AMBIENTE, None)

    def git(pasta: Path, *argumentos):
        return subprocess.run(["git", *argumentos], cwd=str(pasta),
                              capture_output=True, text=True)

    def repositorio(pasta: Path, declarado) -> Path:
        pasta.mkdir(parents=True)
        git(pasta, "init", "-q")
        git(pasta, "config", "user.email", "prova@exemplo")
        git(pasta, "config", "user.name", "prova")
        if declarado is not None:
            git(pasta, "config", CHAVE_DA_DECLARACAO,
                "true" if declarado else "false")
        (pasta / ".gitignore").write_text(
            "/trabalho/\n/projetos/*\n/.claude/worktrees/\n", encoding="utf-8")
        (pasta / "leiame.md").write_text("partida\n", encoding="utf-8")
        git(pasta, "add", "-A")
        git(pasta, "commit", "-q", "-m", "partida")
        return pasta

    def veredito(corpo: dict, com_marca: bool = False) -> tuple:
        saida, erro = io.StringIO(), io.StringIO()
        guardado, sys.stdin = sys.stdin, io.StringIO(json.dumps(corpo))
        if com_marca:
            os.environ[MARCA_DE_ETAPA_NO_AMBIENTE] = "1"
        try:
            with redirect_stdout(saida), redirect_stderr(erro):
                decidir()
        finally:
            sys.stdin = guardado
            os.environ.pop(MARCA_DE_ETAPA_NO_AMBIENTE, None)
        return DECISAO_DE_NEGAR in saida.getvalue(), saida.getvalue(), \
            erro.getvalue()

    def edicao(caminho, cwd=None) -> dict:
        corpo = {"tool_name": "Edit", "tool_input": {"file_path": str(caminho)}}
        if cwd is not None:
            corpo[CAMPO_DO_DIRETORIO] = str(cwd)
        return corpo

    with tempfile.TemporaryDirectory(prefix="cerca-raiz-") as pasta:
        base = Path(pasta)
        casa = repositorio(base / "casa", True)
        sem = repositorio(base / "sem-declaracao", None)
        falsa = repositorio(base / "declaracao-falsa", False)
        (sem / "nucleo").mkdir()
        (sem / "nucleo" / "configuracao.json").write_text(
            json.dumps({"raiz_so_espelha_a_integracao": True}),
            encoding="utf-8")
        frente = casa / ".claude" / "worktrees" / "frente"
        git(casa, "worktree", "add", "-q", str(frente), "-b", "frente")
        vizinho = casa / "projetos" / "vizinho"
        vizinho.mkdir(parents=True)
        git(vizinho, "init", "-q")
        clone = base / "clone"
        git(base, "clone", "-q", str(casa), str(clone))
        fora = base / "fora-de-git"
        fora.mkdir()

        barra = (
            ("arquivo rastreado na raiz que declara",
             edicao(casa / "leiame.md"), False),
            ("arquivo novo, que o git não ignora, na raiz",
             edicao(casa / "conhecimento" / "nova.md"), False),
            ("caminho com barra normal",
             edicao((casa / "leiame.md").as_posix()), False),
            ("caminho relativo, resolvido pelo diretório do evento",
             edicao("leiame.md", cwd=casa), False),
            ("caderno, pelo campo do caderno",
             {"tool_name": "NotebookEdit",
              "tool_input": {"notebook_path": str(casa / "analise.ipynb")}},
             False),
            ("a marca de etapa não dá passe: a ponte do Codex a põe em toda "
             "chamada, e o executor rodado na raiz a leva junto",
             edicao(casa / "leiame.md"), True),
        )
        passa = (
            ("o que o git ignora, na raiz",
             edicao(casa / "trabalho" / "nota.md")),
            ("arquivo de worktree ligada que mora dentro da pasta da raiz",
             edicao(frente / "leiame.md")),
            ("vizinho clonado dentro da raiz, com git próprio",
             edicao(vizinho / "codigo.py")),
            ("clone da raiz: a declaração é da configuração local do git, e "
             "clone não a herda",
             edicao(clone / "leiame.md")),
            ("raiz sem a declaração, mesmo com a chave velha no arquivo "
             "rastreado de configuração",
             edicao(sem / "leiame.md")),
            ("raiz com a declaração falsa", edicao(falsa / "leiame.md")),
            ("fora de qualquer repositório", edicao(fora / "solto.md")),
            ("dentro da pasta do git", edicao(casa / ".git" / "info" / "exclude")),
            ("sem caminho no evento", {"tool_name": "Edit", "tool_input": {}}),
        )
        for titulo, corpo, com_marca in barra:
            negou, _, _ = veredito(corpo, com_marca)
            if not negou:
                falhas.append(f"{titulo} — devia barrar e deixou passar")
        for titulo, corpo in passa:
            negou, _, _ = veredito(corpo)
            if negou:
                falhas.append(f"{titulo} — devia passar e barrou")

        negou, texto, _ = veredito(edicao(casa / "leiame.md"))
        if not negou or "worktree" not in texto or "leiame.md" not in texto:
            falhas.append("a recusa devia nomear o arquivo e o caminho da "
                          "worktree")

        guardado = COMANDO_DO_GIT_QUE_IGNORA
        COMANDO_DO_GIT_QUE_IGNORA = ("git-que-nao-existe-aqui", "check-ignore")
        try:
            negou, _, erro = veredito(edicao(casa / "leiame.md"))
        finally:
            COMANDO_DO_GIT_QUE_IGNORA = guardado
        if negou or "não mediu" not in erro:
            falhas.append("git que não responde ao check-ignore — devia deixar "
                          "passar e avisar que não mediu")

        guardado = COMANDO_DA_DECLARACAO
        COMANDO_DA_DECLARACAO = ("git-que-nao-existe-aqui", "config")
        try:
            negou, _, erro = veredito(edicao(casa / "leiame.md"))
        finally:
            COMANDO_DA_DECLARACAO = guardado
        if negou or "não mediu" not in erro:
            falhas.append("git que não responde à leitura da declaração — "
                          "devia deixar passar e avisar que não mediu")

    if marca_herdada is not None:
        os.environ[MARCA_DE_ETAPA_NO_AMBIENTE] = marca_herdada
    total = len(barra) + len(passa) + 3
    if falhas:
        for linha in falhas:
            print("  " + linha)
        print("FALHOU: %d de %d casos — cerca da raiz" % (len(falhas), total))
        return 1
    print("OK: %d casos — cerca da raiz" % total)
    return 0


if __name__ == "__main__":
    if BANDEIRA_DE_TESTE in sys.argv:
        sys.exit(testar())
    sys.exit(main())
