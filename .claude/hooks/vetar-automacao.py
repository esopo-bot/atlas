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
    ".git/hooks/",
)

FERRAMENTAS_DE_ESCRITA = ("Write", "Edit", "NotebookEdit")
CAMPOS_DE_CAMINHO = ("file_path", "notebook_path")
REDIRECIONAMENTO_DE_SHELL = re.compile(r">>?\s*([^\s;|&]+)")
SEPARADORES_DE_COMANDO = re.compile(
    r"&&|\|\||;|\||\n|\r|\$\(|`|\)")
DOCUMENTO_LITERAL_QUE_NAO_EXPANDE = re.compile(
    r"<<-?\s*(['\"])(\w+)\1.*?(?:^\2\s*$|\Z)", re.S | re.M)
ASPA_SIMPLES_COM_CORPO = re.compile(r"'[^']*'")
ASPA_DUPLA_COM_CORPO = re.compile(r"\"[^\"]*\"")
EXPANSAO_QUE_EXECUTA = ("$(", "`")
COMANDOS_QUE_ESCREVEM_SEM_SETA = ("tee", "cp", "mv", "install", "touch",
                                  "rm")
COMANDO_QUE_ESCREVE_NO_LUGAR = "sed"
BANDEIRA_DE_ESCRITA_NO_LUGAR = "-i"
BANDEIRA_DE_ESCRITA_NO_LUGAR_POR_EXTENSO = "--in-place"

VARIAVEL_DA_RAIZ_DO_PROJETO = "CLAUDE_PROJECT_DIR"
NIVEIS_DO_GANCHO_ATE_A_RAIZ = 2

EVENTO_ANTES_DA_FERRAMENTA = "PreToolUse"
DECISAO_DE_NEGAR = "deny"
BANDEIRA_DE_TESTE = "--testar"
PASSA = ""
SILENCIO = 0
RECUSA_SEM_ENTENDER = (
    "Este gancho não entendeu o pedido, e por isso recusa em vez de liberar: "
    "{} — {}. Quem veta e não consegue julgar não pode dizer sim: a parede "
    "sumiria em silêncio, e o verde passaria a significar `ninguém olhou`. "
    "Se o pedido é legítimo, conserte o gancho ou desligue-o em "
    ".claude/settings.json — o caminho nunca é atravessar por aqui."
)
MANDA_GRAVAR = (
    "\nGrave o aprendizado antes de tentar de novo — regra 4, a memória "
    "mora no disco, e recusa que a próxima sessão repete não ensinou "
    "nada. A linha, em `conhecimento/`:\n"
    "    {}"
)
APRENDIZADO = (
    "configuração de automação não se edita de passagem: a mudança se "
    "propõe ao dono, e a lista dos caminhos protegidos está em "
    ".claude/caminhos-de-automacao.txt."
)

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


def sem_o_que_e_so_dado(trecho: str) -> str:
    sem_aspa_simples = ASPA_SIMPLES_COM_CORPO.sub(" ", trecho)
    return ASPA_DUPLA_COM_CORPO.sub(
        lambda achado: achado.group(0)
        if any(marca in achado.group(0) for marca in EXPANSAO_QUE_EXECUTA)
        else " ", sem_aspa_simples)


def segmentos_que_executam(comando: str) -> list:
    sem_documento = DOCUMENTO_LITERAL_QUE_NAO_EXPANDE.sub(" ", comando)
    return [sem_o_que_e_so_dado(s)
            for s in SEPARADORES_DE_COMANDO.split(sem_documento)]


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
    achados = []
    for segmento in segmentos_que_executam(comando):
        achados += [m.group(1)
                    for m in REDIRECIONAMENTO_DE_SHELL.finditer(segmento)]
        try:
            pedacos = shlex.split(segmento, posix=False)
        except ValueError:
            pedacos = segmento.split()
        programa = Path(pedacos[0]).name if pedacos else ""
        if programa in COMANDOS_QUE_ESCREVEM_SEM_SETA:
            achados += pedacos[1:]
        elif programa == COMANDO_QUE_ESCREVE_NO_LUGAR and any(
                t == BANDEIRA_DE_ESCRITA_NO_LUGAR_POR_EXTENSO
                or t.startswith(BANDEIRA_DE_ESCRITA_NO_LUGAR)
                for t in pedacos[1:] if t.startswith("-")):
            achados += pedacos[1:]
    return [a.strip("\"'") for a in achados if a and not a.startswith("-")]


def raiz_do_projeto_nunca_o_cwd() -> Path:
    declarada = os.environ.get(VARIAVEL_DA_RAIZ_DO_PROJETO)
    if declarada:
        return Path(declarada)
    return Path(__file__).resolve().parents[NIVEIS_DO_GANCHO_ATE_A_RAIZ]


def recusa_por_nao_entender(falha) -> int:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": EVENTO_ANTES_DA_FERRAMENTA,
        "permissionDecision": DECISAO_DE_NEGAR,
        "permissionDecisionReason": RECUSA_SEM_ENTENDER.format(
            type(falha).__name__, falha),
    }}, ensure_ascii=False))
    return SILENCIO


def decidir() -> int:
    try:
        entrada = json.load(sys.stdin)
    except (json.JSONDecodeError, AttributeError, TypeError,
            ValueError) as falha:
        return recusa_por_nao_entender(falha)

    raiz = raiz_do_projeto_nunca_o_cwd()
    declarados = caminhos_declarados(raiz)

    for caminho in caminhos_que_o_pedido_toca(entrada):
        motivo = motivo_da_recusa(caminho, declarados)
        if motivo:
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": EVENTO_ANTES_DA_FERRAMENTA,
                "permissionDecision": DECISAO_DE_NEGAR,
                "permissionDecisionReason": (
                    RECUSA.format(
                        motivo, ARQUIVO_DE_CAMINHOS_DE_AUTOMACAO)
                    + MANDA_GRAVAR.format(APRENDIZADO)),
            }}, ensure_ascii=False))
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
    ("gancho do git, que não entra no git e roda a cada commit",
     ".git/hooks/pre-commit"),
    ("gancho do git por caminho absoluto",
     "/home/alguem/repo/.git/hooks/pre-push"),
]

DEIXA_PASSAR = [
    ("pasta de ganchos rastreada, que entra em revisão",
     ".githooks/pre-commit"),
    ("página que explica os ganchos do git", "docs/git-hooks.md"),
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

    def recusou_sem_entender(falha):
        import io
        import contextlib
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            recusa_por_nao_entender(falha)
        try:
            dado = json.loads(saida.getvalue())["hookSpecificOutput"]
        except (ValueError, KeyError):
            return False
        return (dado.get("permissionDecision") == DECISAO_DE_NEGAR
                and type(falha).__name__ in
                dado.get("permissionDecisionReason", ""))

    caso("gancho que veta e não entende o pedido RECUSA, e nomeia a falha — "
         "quem não consegue julgar não pode dizer sim",
         recusou_sem_entender(TypeError("forma que o gancho não conhece")))

    mensagem = (RECUSA.format(MOTIVO_TOCA_A_AUTOMACAO.format(
        ".github/workflows/entrega.yml"), ARQUIVO_DE_CAMINHOS_DE_AUTOMACAO)
        + MANDA_GRAVAR.format(APRENDIZADO))
    caso("a recusa nomeia a regra 12, diz onde o valor certo mora e manda "
         "gravar o aprendizado em conhecimento/",
         "Regra 12" in mensagem
         and ARQUIVO_DE_CAMINHOS_DE_AUTOMACAO in mensagem
         and "regra 4" in mensagem and "`conhecimento/`" in mensagem
         and APRENDIZADO in mensagem)

    caso("a ferramenta Write é alcançada",
         caminhos_que_o_pedido_toca({
             "tool_name": "Write",
             "tool_input": {"file_path": ".github/workflows/x.yml"}})
         == [".github/workflows/x.yml"])
    caso("`sed -n` é leitura e não entra nos alvos de escrita — a regra 8 "
         "diz que ler é livre, e o gancho vizinho já a respeita",
         caminhos_que_o_pedido_toca({
             "tool_name": "Bash",
             "tool_input": {"command":
                            "sed -n 1,20p .github/workflows/x.yml"}}) == [])
    caso("`sed -i` continua sendo escrita",
         ".github/workflows/x.yml" in caminhos_que_o_pedido_toca({
             "tool_name": "Bash",
             "tool_input": {"command":
                            "sed -i s/a/b/ .github/workflows/x.yml"}}))
    caso("`sed --in-place` por extenso também é escrita",
         "Jenkinsfile" in caminhos_que_o_pedido_toca({
             "tool_name": "Bash",
             "tool_input": {"command":
                            "sed --in-place s/a/b/ Jenkinsfile"}}))
    caso("os outros comandos da lista não dependem de bandeira nenhuma",
         caminhos_que_o_pedido_toca({
             "tool_name": "Bash",
             "tool_input": {"command": "rm .github/workflows/x.yml"}})
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
    caso("apagar escondido depois de &&",
         any(motivo_da_recusa(c, declarados) for c in
             caminhos_que_o_pedido_toca({
                 "tool_name": "Bash",
                 "tool_input": {"command": "git status && rm " + ".github/workflows/e.yml"}})))
    caso("mover escondido depois de ponto-e-vírgula",
         any(motivo_da_recusa(c, declarados) for c in
             caminhos_que_o_pedido_toca({
                 "tool_name": "Bash",
                 "tool_input": {"command": "ls ; mv " + ".github/workflows/e.yml" + " /tmp/x"}})))
    caso("redirecionamento escondido depois de &&",
         any(motivo_da_recusa(c, declarados) for c in
             caminhos_que_o_pedido_toca({
                 "tool_name": "Bash",
                 "tool_input": {"command": "ls && echo x > " + ".github/workflows/e.yml"}})))
    caso("subcomando dentro de aspas duplas ainda executa",
         any(motivo_da_recusa(c, declarados) for c in
             caminhos_que_o_pedido_toca({
                 "tool_name": "Bash",
                 "tool_input": {"command": 'echo "$(rm ' + ".github/workflows/e.yml" + ')"'}})))
    caso("aspas simples seguram o comando inteiro",
         not any(motivo_da_recusa(c, declarados) for c in
                 caminhos_que_o_pedido_toca({
                     "tool_name": "Bash",
                     "tool_input": {"command": "echo 'x > " + ".github/workflows/e.yml" + "'"}})))
    caso("aspas duplas sem expansão são dado",
         not any(motivo_da_recusa(c, declarados) for c in
                 caminhos_que_o_pedido_toca({
                     "tool_name": "Bash",
                     "tool_input": {"command": 'echo "x > ' + ".github/workflows/e.yml" + '"'}})))
    caso("documento literal é dado, não comando",
         not any(motivo_da_recusa(c, declarados) for c in
                 caminhos_que_o_pedido_toca({
                     "tool_name": "Bash",
                     "tool_input": {"command": "cat <<'FIM'\nx > " + ".github/workflows/e.yml" + "\nFIM"}})))
    caso("mensagem de commit que cita o caminho",
         not any(motivo_da_recusa(c, declarados) for c in
                 caminhos_que_o_pedido_toca({
                     "tool_name": "Bash",
                     "tool_input": {"command": 'git commit -m "documenta ' + ".github/workflows/e.yml" + '"'}})))
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


def main() -> int:
    try:
        return decidir()
    except Exception as falha:
        return recusa_por_nao_entender(falha)


if __name__ == "__main__":
    if BANDEIRA_DE_TESTE in sys.argv:
        sys.exit(testar())
    sys.exit(main())
