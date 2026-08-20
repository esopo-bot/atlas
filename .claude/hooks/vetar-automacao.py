import json
import os
import re
import shlex
import sys
from fnmatch import fnmatch
from pathlib import Path

ARQUIVO_DE_CAMINHOS_DE_AUTOMACAO = ".claude/caminhos-de-automacao.txt"
MARCA_DE_COMENTARIO = "#"

CAMINHOS_EMBUTIDOS = (
    ".github/workflows/",
    ".gitlab-ci.yml",
    ".circleci/",
    "Jenkinsfile",
    "azure-pipelines.yml",
    "bitbucket-pipelines.yml",
    ".travis.yml",
)

FERRAMENTAS_DE_ESCRITA = ("Write", "Edit", "NotebookEdit")
CAMPOS_DE_CAMINHO = ("file_path", "notebook_path")
REDIRECIONAMENTO_DE_SHELL = re.compile(r">>?\s*([^\s;|&]+)")
COMANDOS_QUE_ESCREVEM_SEM_SETA = ("tee", "cp", "mv", "install", "touch",
                                  "rm", "sed")

VARIAVEL_DA_RAIZ_DO_PROJETO = "CLAUDE_PROJECT_DIR"
NIVEIS_DO_GANCHO_ATE_A_RAIZ = 2

EVENTO_ANTES_DA_FERRAMENTA = "PreToolUse"
DECISAO_DE_NEGAR = "deny"
BANDEIRA_DE_TESTE = "--testar"
PASSA = ""
SILENCIO = 0
FALHA_ABERTO = 0

MOTIVO_TOCA_A_AUTOMACAO = (
    "escrever em {!r}, que este repositório declara como configuração da "
    "automação")
RECUSA = (
    "Regra 12 da camada: isto quer {}. Configuração de automação é "
    "infraestrutura de outras pessoas — quem a altera de passagem quebra a "
    "entrega de todo mundo, e o estrago aparece longe de onde nasceu. O "
    "caminho: proponha a mudança ao dono, que a faz e a revisa por pedido de "
    "incorporação. Se este caminho não deveria estar protegido, tire a linha "
    "de {}."
)

FALHA_BARRA = "BARRA [{}]: deixou passar"
FALHA_DEIXA_PASSAR = "DEIXA_PASSAR [{}]: barrou — {}"
FALHA_COMPORTAMENTO = "COMPORTAMENTO [{}]"
LINHA_DE_FALHA = "FALHOU: {}"
RESUMO_FALHOU = "FALHOU: {} de {} casos"
RESUMO_OK = "OK: {} casos — {} barrados, {} liberados, {} de comportamento"


def caminhos_declarados(raiz: Path) -> tuple:
    arquivo = raiz / ARQUIVO_DE_CAMINHOS_DE_AUTOMACAO
    try:
        linhas = arquivo.read_text(encoding="utf-8").splitlines()
    except OSError:
        return tuple(CAMINHOS_EMBUTIDOS)
    declarados = tuple(
        l.strip() for l in linhas
        if l.strip() and not l.strip().startswith(MARCA_DE_COMENTARIO))
    return declarados or tuple(CAMINHOS_EMBUTIDOS)


def em_forma_de_posix(caminho: str) -> str:
    return caminho.replace("\\", "/").strip().strip("\"'").strip("/")


def bate(caminho: str, declarado: str) -> bool:
    alvo = "/" + em_forma_de_posix(caminho)
    if not alvo.strip("/"):
        return False
    if declarado.endswith("/"):
        pasta = em_forma_de_posix(declarado)
        return "/" + pasta + "/" in alvo
    arquivo = em_forma_de_posix(declarado)
    return alvo.endswith("/" + arquivo) or fnmatch(alvo.lstrip("/"), arquivo)


def motivo_da_recusa(caminho: str, declarados) -> str:
    for declarado in declarados:
        if bate(caminho, declarado):
            return MOTIVO_TOCA_A_AUTOMACAO.format(em_forma_de_posix(caminho))
    return PASSA


def caminhos_que_o_pedido_toca(entrada: dict) -> list:
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
        pedacos = shlex.split(comando, posix=False)
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
    declarados = caminhos_declarados(raiz)

    for caminho in caminhos_que_o_pedido_toca(entrada):
        motivo = motivo_da_recusa(caminho, declarados)
        if motivo:
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": EVENTO_ANTES_DA_FERRAMENTA,
                "permissionDecision": DECISAO_DE_NEGAR,
                "permissionDecisionReason": RECUSA.format(
                    motivo, ARQUIVO_DE_CAMINHOS_DE_AUTOMACAO),
            }}))
            return SILENCIO
    return SILENCIO


BARRA = [
    ("fluxo do GitHub na raiz", ".github/workflows/entrega.yml"),
    ("fluxo do GitHub em subpasta profunda",
     ".github/workflows/pastas/mais/fundo.yml"),
    ("configuração do GitLab", ".gitlab-ci.yml"),
    ("pasta do CircleCI", ".circleci/config.yml"),
    ("Jenkinsfile na raiz", "Jenkinsfile"),
    ("pipeline do Azure", "azure-pipelines.yml"),
    ("pipeline do Bitbucket", "bitbucket-pipelines.yml"),
    ("configuração do Travis", ".travis.yml"),
    ("caminho absoluto ainda é o mesmo arquivo",
     "/home/alguem/repo/.github/workflows/entrega.yml"),
    ("automação do repositório vizinho também é de outra gente",
     "../vizinho/.github/workflows/entrega.yml"),
    ("barra invertida do Windows não esconde a pasta",
     ".github\\workflows\\entrega.yml"),
]

DEIXA_PASSAR = [
    ("código comum", "src/app.py"),
    ("página de conhecimento", "conhecimento/nota.md"),
    ("nome que só parece", ".github/ISSUE_TEMPLATE/bug.md"),
    ("arquivo cujo nome contém o do protegido",
     "docs/como-ler-o-gitlab-ci.yml.md"),
    ("pasta que só começa igual", ".githubinho/workflows/x.yml"),
    ("configuração do próprio agente", ".claude/settings.json"),
]


def testar() -> int:
    falhas = []
    declarados = tuple(CAMINHOS_EMBUTIDOS)

    for rotulo, caminho in BARRA:
        if not motivo_da_recusa(caminho, declarados):
            falhas.append(FALHA_BARRA.format(rotulo))
    for rotulo, caminho in DEIXA_PASSAR:
        motivo = motivo_da_recusa(caminho, declarados)
        if motivo:
            falhas.append(FALHA_DEIXA_PASSAR.format(rotulo, motivo))

    comportamento = []

    def caso(rotulo, condicao):
        comportamento.append((rotulo, bool(condicao)))

    caso("a ferramenta Write é alcançada",
         caminhos_que_o_pedido_toca({
             "tool_name": "Write",
             "tool_input": {"file_path": ".github/workflows/x.yml"}})
         == [".github/workflows/x.yml"])
    caso("a ferramenta Edit é alcançada",
         caminhos_que_o_pedido_toca({
             "tool_name": "Edit",
             "tool_input": {"file_path": "Jenkinsfile"}}) == ["Jenkinsfile"])
    caso("redirecionamento por shell é alcançado",
         caminhos_que_o_pedido_toca({
             "tool_name": "Bash",
             "tool_input": {"command": "echo x > .gitlab-ci.yml"}})
         == [".gitlab-ci.yml"])
    caso("append também",
         ".travis.yml" in caminhos_que_o_pedido_toca({
             "tool_name": "Bash",
             "tool_input": {"command": "echo x >> .travis.yml"}}))
    caso("apagar a automação é tocar nela",
         motivo_da_recusa(caminhos_que_o_pedido_toca({
             "tool_name": "Bash",
             "tool_input": {"command": "rm .github/workflows/entrega.yml"}}
         )[0], declarados))
    caso("mover a automação para fora também",
         any(motivo_da_recusa(c, declarados) for c in
             caminhos_que_o_pedido_toca({
                 "tool_name": "Bash",
                 "tool_input": {
                     "command": "mv .github/workflows/e.yml /tmp/e.yml"}})))
    caso("sed no lugar do editor não escapa",
         any(motivo_da_recusa(c, declarados) for c in
             caminhos_que_o_pedido_toca({
                 "tool_name": "Bash",
                 "tool_input": {
                     "command": "sed -i s/a/b/ .github/workflows/e.yml"}})))
    caso("ler a automação passa calado",
         caminhos_que_o_pedido_toca({
             "tool_name": "Bash",
             "tool_input": {"command": "cat .github/workflows/e.yml"}}) == [])
    caso("comando sem escrita nenhuma não devolve alvo",
         caminhos_que_o_pedido_toca({
             "tool_name": "Bash", "tool_input": {"command": "ls .github"}})
         == [])
    caso("entrada quebrada não prende a sessão (falha aberto)",
         caminhos_que_o_pedido_toca({}) == [])
    caso("aspas desbalanceadas não derrubam o gancho",
         isinstance(caminhos_que_o_pedido_toca({
             "tool_name": "Bash",
             "tool_input": {"command": "echo 'sem fechar > .travis.yml"}}),
             list))
    caso("lista vazia cai no embutido, e o embutido barra",
         caminhos_declarados(Path("/pasta/que/nao/existe"))
         == tuple(CAMINHOS_EMBUTIDOS))
    caso("caminho vazio não vira acusação",
         not motivo_da_recusa("", declarados))
    caso("a lista do dono manda: sem ela nada é protegido",
         not motivo_da_recusa(".github/workflows/x.yml", ()))
    caso("a lista do dono manda: o que ela declara é protegido",
         motivo_da_recusa("infra/deploy.tf", ("infra/",)))

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
