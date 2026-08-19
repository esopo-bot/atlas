import json
import os
import re
import shlex
import sys
from pathlib import Path

ARQUIVO_EXECUTOR = "nucleo/executor.json"
CHAVE_DOS_DIRETORIOS_SO_CODIGO = "diretorios_so_codigo"
CHAVE_DAS_EXTENSOES = "extensoes_de_conhecimento"
EXTENSOES_DE_CONHECIMENTO = (".md", ".txt")
MARCA_DE_MOLDE_NAO_PREENCHIDO = "${"
PASTA_DO_GIT = ".git"

FERRAMENTAS_DE_ESCRITA = ("Write", "Edit", "NotebookEdit")
CAMPOS_DE_CAMINHO = ("file_path", "notebook_path")
REDIRECIONAMENTO_DE_SHELL = re.compile(r">>?\s*([^\s;|&]+)")
COMANDOS_QUE_ESCREVEM_SEM_SETA = ("tee", "cp", "mv", "install", "touch")

VARIAVEL_DA_RAIZ_DO_PROJETO = "CLAUDE_PROJECT_DIR"
NIVEIS_DO_GANCHO_ATE_A_RAIZ = 2

EVENTO_ANTES_DA_FERRAMENTA = "PreToolUse"
DECISAO_DE_NEGAR = "deny"
BANDEIRA_DE_TESTE = "--testar"
PASSA = ""
SILENCIO = 0
FALHA_ABERTO = 0

MOTIVO_NASCE_EM_PASTA_DE_CODIGO = (
    "criar {!r} em {!r}, que a configuração declara como diretório só de "
    "código")
RECUSA = (
    "Isto quer {}. Conhecimento não nasce em pasta de código: lá ninguém o "
    "procura, e ele viaja por engano no commit do repositório errado. "
    "Escreva em `conhecimento/`, ou — se o texto é DAQUELE repositório "
    "(README, docs/) — crie dentro dele, que o fluxo de revisão dele julga. "
    "Para mudar a cerca: `diretorios_so_codigo` em {}."
)

FALHA_BARRA = "BARRA [{}]: deixou passar"
FALHA_DEIXA_PASSAR = "DEIXA_PASSAR [{}]: barrou — {}"
FALHA_COMPORTAMENTO = "COMPORTAMENTO [{}]"
LINHA_DE_FALHA = "FALHOU: {}"
RESUMO_FALHOU = "FALHOU: {} de {} casos"
RESUMO_OK = "OK: {} casos — {} barrados, {} liberados, {} de comportamento"


def configuracao_da_cerca(raiz: Path):
    try:
        dado = json.loads(
            (raiz / ARQUIVO_EXECUTOR).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(dado, dict):
        return None
    diretorios = [d for d in (dado.get(CHAVE_DOS_DIRETORIOS_SO_CODIGO) or [])
                  if isinstance(d, str) and d.strip()
                  and MARCA_DE_MOLDE_NAO_PREENCHIDO not in d]
    if not diretorios:
        return None
    extensoes = tuple(dado.get(CHAVE_DAS_EXTENSOES)
                      or EXTENSOES_DE_CONHECIMENTO)
    return {"diretorios": diretorios, "extensoes": extensoes}


def e_arquivo_de_conhecimento(caminho: str, extensoes) -> bool:
    return caminho.lower().endswith(tuple(e.lower() for e in extensoes))


def e_de_um_repositorio_com_fluxo_proprio(alvo: Path, fronteira: Path) -> bool:
    atual = alvo.parent
    while True:
        if (atual / PASTA_DO_GIT).exists():
            return True
        if atual == fronteira or atual.parent == atual:
            return False
        atual = atual.parent


def motivo_da_recusa(caminho: str, raiz: Path, configuracao) -> str:
    if not configuracao or not caminho:
        return PASSA
    if not e_arquivo_de_conhecimento(caminho, configuracao["extensoes"]):
        return PASSA
    alvo = Path(caminho)
    if not alvo.is_absolute():
        alvo = (raiz / alvo)
    try:
        alvo = alvo.resolve(strict=False)
    except OSError:
        return PASSA
    e_edicao_do_que_ja_existe = alvo.exists()
    if e_edicao_do_que_ja_existe:
        return PASSA
    for declarado in configuracao["diretorios"]:
        fronteira = (raiz / declarado).resolve(strict=False) \
            if not Path(declarado).is_absolute() else Path(declarado).resolve()
        if not fronteira.is_dir():
            continue
        if fronteira not in alvo.parents:
            continue
        if e_de_um_repositorio_com_fluxo_proprio(alvo, fronteira):
            return PASSA
        return MOTIVO_NASCE_EM_PASTA_DE_CODIGO.format(alvo.name, declarado)
    return PASSA


def caminhos_que_o_pedido_criaria(entrada: dict) -> list:
    ferramenta = entrada.get("tool_name", "")
    dado = entrada.get("tool_input", {}) or {}
    if ferramenta in FERRAMENTAS_DE_ESCRITA:
        for campo in CAMPOS_DE_CAMINHO:
            if dado.get(campo):
                return [dado[campo]]
        return []
    comando = dado.get("command", "")
    if not comando:
        return []
    achados = [m.group(1) for m in REDIRECIONAMENTO_DE_SHELL.finditer(comando)]
    try:
        pedacos = shlex.split(comando)
    except ValueError:
        pedacos = comando.split()
    if pedacos and Path(pedacos[0]).name in COMANDOS_QUE_ESCREVEM_SEM_SETA:
        achados += pedacos[1:]
    return [a.strip("\"'") for a in achados if a and not a.startswith("-")]


def raiz_do_projeto_nunca_o_cwd() -> Path:
    declarada = os.environ.get(VARIAVEL_DA_RAIZ_DO_PROJETO)
    if declarada:
        return Path(declarada)
    return Path(__file__).resolve().parents[NIVEIS_DO_GANCHO_ATE_A_RAIZ]


def main() -> int:
    try:
        entrada = json.load(sys.stdin)
    except (json.JSONDecodeError, AttributeError, TypeError, ValueError):
        return FALHA_ABERTO

    raiz = raiz_do_projeto_nunca_o_cwd()
    configuracao = configuracao_da_cerca(raiz)
    if not configuracao:
        return SILENCIO

    for caminho in caminhos_que_o_pedido_criaria(entrada):
        motivo = motivo_da_recusa(caminho, raiz, configuracao)
        if motivo:
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": EVENTO_ANTES_DA_FERRAMENTA,
                "permissionDecision": DECISAO_DE_NEGAR,
                "permissionDecisionReason": RECUSA.format(
                    motivo, ARQUIVO_EXECUTOR),
            }}))
            return SILENCIO
    return SILENCIO


def montar_workspace_de_mentira(pasta: Path):
    (pasta / "nucleo").mkdir(parents=True, exist_ok=True)
    (pasta / "nucleo" / "executor.json").write_text(json.dumps({
        CHAVE_DOS_DIRETORIOS_SO_CODIGO: ["projetos"]}), encoding="utf-8")
    (pasta / "projetos" / "app" / ".git").mkdir(parents=True, exist_ok=True)
    (pasta / "projetos" / "solta").mkdir(parents=True, exist_ok=True)
    (pasta / "projetos" / "ja-existe.md").write_text("velho", encoding="utf-8")
    (pasta / "conhecimento").mkdir(exist_ok=True)
    return configuracao_da_cerca(pasta)


BARRA = [
    ("nota na raiz do diretório declarado", "projetos/nota.md"),
    ("texto na raiz do diretório declarado", "projetos/rascunho.txt"),
    ("nota em subpasta que não é repositório", "projetos/solta/ideia.md"),
]

DEIXA_PASSAR = [
    ("README dentro de um repositório", "projetos/app/README.md"),
    ("doc dentro de um repositório", "projetos/app/docs/uso.md"),
    ("código no diretório declarado", "projetos/solta/main.py"),
    ("nota fora do diretório declarado", "conhecimento/nota.md"),
    ("arquivo de conhecimento que JÁ EXISTE", "projetos/ja-existe.md"),
]


def testar() -> int:
    import tempfile
    falhas = []
    with tempfile.TemporaryDirectory(prefix="veto-conhecimento-") as tmp:
        raiz = Path(tmp)
        configuracao = montar_workspace_de_mentira(raiz)
        for rotulo, caminho in BARRA:
            if not motivo_da_recusa(caminho, raiz, configuracao):
                falhas.append(FALHA_BARRA.format(rotulo))
        for rotulo, caminho in DEIXA_PASSAR:
            motivo = motivo_da_recusa(caminho, raiz, configuracao)
            if motivo:
                falhas.append(FALHA_DEIXA_PASSAR.format(rotulo, motivo))

        comportamento = []

        def caso(rotulo, condicao):
            comportamento.append((rotulo, bool(condicao)))

        caso("sem executor.json a cerca não existe",
             not motivo_da_recusa("projetos/nota.md", raiz, None))
        (raiz / "nucleo" / "executor.json").write_text(json.dumps({
            CHAVE_DOS_DIRETORIOS_SO_CODIGO: ["${DIRETORIO}"]}),
            encoding="utf-8")
        caso("diretório ainda no molde não vira cerca",
             configuracao_da_cerca(raiz) is None)
        montar_workspace_de_mentira(raiz)

        caso("redirecionamento por shell é alcançado",
             caminhos_que_o_pedido_criaria({"tool_name": "Bash", "tool_input": {
                 "command": "echo oi > projetos/nota.md"}})
             == ["projetos/nota.md"])
        caso("append também",
             "projetos/n.md" in caminhos_que_o_pedido_criaria({
                 "tool_name": "Bash",
                 "tool_input": {"command": "echo a >> projetos/n.md"}}))
        caso("tee também",
             "projetos/t.md" in caminhos_que_o_pedido_criaria({
                 "tool_name": "Bash",
                 "tool_input": {"command": "tee projetos/t.md"}}))
        caso("a ferramenta Write é alcançada",
             caminhos_que_o_pedido_criaria({"tool_name": "Write", "tool_input": {
                 "file_path": "projetos/nota.md"}}) == ["projetos/nota.md"])
        caso("comando sem escrita nenhuma não devolve alvo",
             caminhos_que_o_pedido_criaria({
                 "tool_name": "Bash",
                 "tool_input": {"command": "ls projetos"}}) == [])
        caso("entrada quebrada não prende a sessão (falha aberto)",
             caminhos_que_o_pedido_criaria({}) == [])
        caso("aspas desbalanceadas não derrubam o gancho",
             isinstance(caminhos_que_o_pedido_criaria({
                 "tool_name": "Bash", "tool_input": {
                     "command": "echo 'sem fechar > projetos/x.md"}}), list))
        falhas += [FALHA_COMPORTAMENTO.format(rotulo)
                   for rotulo, passou in comportamento if not passou]

    total = len(BARRA) + len(DEIXA_PASSAR) + len(comportamento)
    if falhas:
        for falha in falhas:
            print(LINHA_DE_FALHA.format(falha))
        print(RESUMO_FALHOU.format(len(falhas), total))
        return 1
    print(RESUMO_OK.format(total, len(BARRA), len(DEIXA_PASSAR),
                           len(comportamento)))
    return 0


if __name__ == "__main__":
    if BANDEIRA_DE_TESTE in sys.argv:
        sys.exit(testar())
    sys.exit(main())
