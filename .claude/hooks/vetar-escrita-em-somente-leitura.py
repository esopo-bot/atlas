import json
import os
import re
import sys
from pathlib import Path

ARQUIVO_EXECUTOR = "nucleo/executor.json"
CHAVE_DOS_PROJETOS = "projetos"
CHAVE_DO_REPOSITORIO = "repositorio"
CHAVE_DO_SO_LEITURA = "somente_leitura"
MARCA_DE_MOLDE_NAO_PREENCHIDO = "${"
PASTA_DO_GIT = ".git"

FERRAMENTAS_DE_ESCRITA = ("Write", "Edit", "NotebookEdit")
CAMPOS_DE_CAMINHO = ("file_path", "notebook_path")

SEPARADORES_DE_COMANDO = re.compile(r"&&|\|\||;|\||\n|\r|\$\(|`|\)")
EXPANSAO_QUE_ASPA_DUPLA_NAO_SEGURA = re.compile(r"\$\(|`|\)")
DOCUMENTO_LITERAL_QUE_NAO_EXPANDE = re.compile(
    r"<<-?\s*(['\"])(\w+)\1.*?(?:^\2\s*$|\Z)", re.S | re.M)
REDIRECIONAMENTO_DE_SHELL = re.compile(r">>?\s*([^\s;|&<>]+)")
ASPA_SIMPLES = "'"
ASPA_DUPLA = '"'
ASPAS = "\"'"

COMANDO_CD = "cd"
NOMES_DO_GIT = ("git", "git.exe")
NOME_DO_GH = "gh"
EXTENSAO_EXE = ".exe"

BANDEIRAS_GLOBAIS_SIMPLES = {"--no-pager", "--paginate", "-p", "--bare",
                             "--literal-pathspecs"}
BANDEIRAS_GLOBAIS_QUE_COMEM_O_TOKEN_SEGUINTE = {
    "-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path",
    "-R", "--repo"}
BANDEIRA_DO_DIRETORIO_DO_GIT = ("-C",)
BANDEIRAS_DO_REPOSITORIO_DO_GH = ("-R", "--repo")

VERBOS_DO_GIT_QUE_ESCREVEM = {
    "add", "am", "apply", "checkout", "cherry-pick", "clean", "commit",
    "init", "merge", "mv", "push", "rebase", "reset", "restore", "revert",
    "rm", "stash", "switch"}
VERBOS_DO_GIT_QUE_SO_ESCREVEM_COM_ARGUMENTO = {
    "branch": {"--show-current", "--list", "-l", "-a", "--all", "-r",
               "--remotes", "-v", "-vv", "--verbose", "--contains",
               "--merged", "--no-merged", "--points-at"},
    "tag": {"--list", "-l", "-n", "--contains", "--points-at", "--merged"},
}
SUBVERBOS_DO_GH_QUE_LEEM = {
    "pr": {"view", "list", "status", "diff", "checks"},
    "issue": {"view", "list", "status"},
    "release": {"view", "list", "download"},
    "repo": {"view", "list"},
}

SUBVERBOS_DO_GH_QUE_CONVERSAM = {
    "issue": {"comment", "create", "edit"},
    "pr": {"comment", "close"},
}

COMANDOS_QUE_ESCREVEM_NOS_ARGUMENTOS = ("rm", "rmdir", "mv", "tee", "touch",
                                        "mkdir", "truncate", "chmod", "chown")
COMANDOS_QUE_ESCREVEM_NO_ULTIMO = ("cp", "ln", "install")
COMANDO_QUE_ESCREVE_NO_LUGAR = "sed"
BANDEIRA_DE_ESCRITA_NO_LUGAR = "-i"
BANDEIRA_DE_ESCRITA_NO_LUGAR_POR_EXTENSO = "--in-place"

VARIAVEL_DA_RAIZ_DO_PROJETO = "CLAUDE_PROJECT_DIR"
NIVEIS_DO_GANCHO_ATE_A_RAIZ = 2

EVENTO_ANTES_DA_FERRAMENTA = "PreToolUse"
DECISAO_DE_NEGAR = "deny"
BANDEIRA_DE_TESTE = "--testar"
SEM_VERBO = -1
SEM_NOME = ""
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
    "repositório declarado somente leitura não recebe escrita: a "
    "mudança vira pedido de incorporação como sugestão, e quem o abre "
    "é o dono."
)

ACAO_ESCREVER_EM = "escrever em {!r}"
ACAO_RODAR = "rodar `{}`"
RECUSA = (
    "Regra 9 da camada: isto quer {}. O repositório {!r} está declarado "
    "somente leitura, "
    "sempre: dele se lê, nele não se escreve. Ele é território de outra "
    "pessoa, e mudança aplicada por cima dela chega sem a revisão de quem "
    "responde pelo que quebrar. O caminho que existe é propor, não aplicar: "
    "a mudança vira um pedido de incorporação como SUGESTÃO, com {} "
    "marcado para revisão — e quem abre o pedido é o "
    "dono. Ler continua livre: `cat`, `git log`, `git show`, `grep`, "
    "`gh issue view` e `gh pr view` passam. Para mudar a lista: "
    "`{}` em {}."
)

FALHA_BARRA = "BARRA [{}]: deixou passar"
FALHA_DEIXA_PASSAR = "DEIXA_PASSAR [{}]: barrou — {}"
FALHA_COMPORTAMENTO = "COMPORTAMENTO [{}]"
LINHA_DE_FALHA = "FALHOU: {}"
RESUMO_FALHOU = "FALHOU: {} de {} casos"
RESUMO_OK = "OK: {} casos — {} barrados, {} liberados, {} de comportamento"


CHAVE_DO_REVISOR = "revisor"
SEM_REVISOR = "quem cuida daquele território"


def revisor_de(raiz: Path, repositorio: str) -> str:
    try:
        dado = json.loads(
            (raiz / ARQUIVO_EXECUTOR).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return SEM_REVISOR
    projetos = (dado or {}).get(CHAVE_DOS_PROJETOS) or {}
    if not isinstance(projetos, dict):
        return SEM_REVISOR
    for projeto in projetos.values():
        if not isinstance(projeto, dict):
            continue
        if projeto.get(CHAVE_DO_REPOSITORIO) != repositorio:
            continue
        nome = projeto.get(CHAVE_DO_REVISOR)
        return f"`{nome}`" if isinstance(nome, str) and nome else SEM_REVISOR
    return SEM_REVISOR


def nomes_somente_leitura(raiz: Path) -> frozenset:
    try:
        dado = json.loads(
            (raiz / ARQUIVO_EXECUTOR).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return frozenset()
    if not isinstance(dado, dict):
        return frozenset()
    projetos = dado.get(CHAVE_DOS_PROJETOS) or {}
    if not isinstance(projetos, dict):
        return frozenset()
    nomes = set()
    for projeto in projetos.values():
        if not isinstance(projeto, dict):
            continue
        if not projeto.get(CHAVE_DO_SO_LEITURA):
            continue
        nome = projeto.get(CHAVE_DO_REPOSITORIO)
        if isinstance(nome, str) and nome.strip() \
                and MARCA_DE_MOLDE_NAO_PREENCHIDO not in nome:
            nomes.add(nome.strip().lower())
    return frozenset(nomes)


def cortar_respeitando_aspas(comando: str):
    segmentos, atual, aspa_aberta = [], [], None
    i = 0
    while i < len(comando):
        c = comando[i]
        if aspa_aberta == ASPA_SIMPLES:
            atual.append(c)
            aspa_aberta = None if c == ASPA_SIMPLES else aspa_aberta
            i += 1
        elif aspa_aberta == ASPA_DUPLA and c == ASPA_DUPLA:
            atual.append(c)
            aspa_aberta = None
            i += 1
        elif aspa_aberta is None and c in ASPAS:
            atual.append(c)
            aspa_aberta = c
            i += 1
        elif corte := (EXPANSAO_QUE_ASPA_DUPLA_NAO_SEGURA if aspa_aberta
                       else SEPARADORES_DE_COMANDO).match(comando, i):
            segmentos.append("".join(atual))
            atual = []
            i = corte.end()
        else:
            atual.append(c)
            i += 1
    if aspa_aberta is not None:
        return None
    segmentos.append("".join(atual))
    return segmentos


def separar(comando: str) -> list:
    sem_documento = DOCUMENTO_LITERAL_QUE_NAO_EXPANDE.sub(" ", comando)
    segmentos = cortar_respeitando_aspas(sem_documento)
    aspas_nao_fecharam = segmentos is None
    if aspas_nao_fecharam:
        return SEPARADORES_DE_COMANDO.split(sem_documento)
    return segmentos


def sem_o_par_de_aspas_que_envolve(token: str) -> str:
    for aspa in (ASPA_DUPLA, ASPA_SIMPLES):
        if len(token) >= 2 and token.startswith(aspa) and token.endswith(aspa):
            return token[1:-1]
    return token


def partir_em_tokens(segmento: str) -> list:
    try:
        import shlex
        tokens = shlex.split(segmento, posix=False)
    except ValueError:
        tokens = segmento.split()
    return [sem_o_par_de_aspas_que_envolve(t) for t in tokens]


def e_git(token: str) -> bool:
    return Path(token.replace("\\", "/")).name.lower() in NOMES_DO_GIT


def e_gh(token: str) -> bool:
    return Path(token).name.lower().removesuffix(EXTENSAO_EXE) == NOME_DO_GH


def indice_do_verbo(tokens: list) -> int:
    i = 1
    while i < len(tokens):
        t = tokens[i]
        if t in BANDEIRAS_GLOBAIS_QUE_COMEM_O_TOKEN_SEGUINTE:
            i += 2
            continue
        colada_por_igual = any(
            t.startswith(g + "=")
            for g in BANDEIRAS_GLOBAIS_QUE_COMEM_O_TOKEN_SEGUINTE)
        if colada_por_igual or t in BANDEIRAS_GLOBAIS_SIMPLES:
            i += 1
            continue
        if t.startswith("-"):
            i += 1
            continue
        return i
    return SEM_VERBO


def valor_da_bandeira(tokens: list, bandeiras) -> str:
    i = 1
    while i < len(tokens):
        t = tokens[i]
        if t in bandeiras and i + 1 < len(tokens):
            return tokens[i + 1]
        for bandeira in bandeiras:
            if t.startswith(bandeira + "="):
                return t.split("=", 1)[1]
        i += 1
    return SEM_NOME


def argumento_faz_escrever(verbo: str, resto: list) -> bool:
    de_leitura = VERBOS_DO_GIT_QUE_SO_ESCREVEM_COM_ARGUMENTO[verbo]
    bandeiras = [t for t in resto if t.startswith("-")]
    posicionais = [t for t in resto if not t.startswith("-")]
    if any(b.split("=", 1)[0].lower() not in de_leitura for b in bandeiras):
        return True
    return bool(posicionais) and not bandeiras


def verbo_do_git_que_escreve(tokens: list) -> str:
    i = indice_do_verbo(tokens)
    if i == SEM_VERBO:
        return SEM_NOME
    verbo = tokens[i].lower()
    if verbo in VERBOS_DO_GIT_QUE_ESCREVEM:
        return verbo
    if verbo in VERBOS_DO_GIT_QUE_SO_ESCREVEM_COM_ARGUMENTO:
        return verbo if argumento_faz_escrever(verbo, tokens[i + 1:]) \
            else SEM_NOME
    return SEM_NOME


def subverbo_do_gh_que_escreve(tokens: list) -> str:
    i = indice_do_verbo(tokens)
    if i == SEM_VERBO:
        return SEM_NOME
    verbo = tokens[i].lower()
    if verbo not in SUBVERBOS_DO_GH_QUE_LEEM:
        return SEM_NOME
    posicionais = [t for t in tokens[i + 1:] if not t.startswith("-")]
    subverbo = posicionais[0].lower() if posicionais else SEM_NOME
    if (not subverbo
            or subverbo in SUBVERBOS_DO_GH_QUE_LEEM[verbo]
            or subverbo in SUBVERBOS_DO_GH_QUE_CONVERSAM.get(verbo, ())):
        return SEM_NOME
    return verbo + " " + subverbo


def resolver(caminho: str, onde: str):
    if not caminho:
        return None
    alvo = Path(os.path.expanduser(caminho))
    if not alvo.is_absolute():
        alvo = Path(onde or ".") / alvo
    try:
        return alvo.resolve(strict=False)
    except OSError:
        return None


def repositorio_de(alvo: Path):
    atual = alvo
    while True:
        if (atual / PASTA_DO_GIT).exists():
            return atual
        if atual.parent == atual:
            return None
        atual = atual.parent


def repositorio_do_caminho(caminho: str, onde: str) -> str:
    alvo = resolver(caminho, onde)
    if alvo is None:
        return SEM_NOME
    repositorio = repositorio_de(alvo)
    return repositorio.name.lower() if repositorio else SEM_NOME


def repositorio_do_nome_remoto(valor: str) -> str:
    return valor.strip().rstrip("/").split("/")[-1].lower()


def caminhos_escritos_pelo_segmento(segmento: str, tokens: list) -> list:
    escritos = [m.group(1) for m in REDIRECIONAMENTO_DE_SHELL.finditer(segmento)]
    if not tokens:
        return escritos
    programa = Path(tokens[0].replace("\\", "/")).name.lower()
    posicionais = [t for t in tokens[1:] if not t.startswith("-")]
    if programa in COMANDOS_QUE_ESCREVEM_NOS_ARGUMENTOS:
        escritos += posicionais
    elif programa in COMANDOS_QUE_ESCREVEM_NO_ULTIMO and posicionais:
        escritos.append(posicionais[-1])
    elif programa == COMANDO_QUE_ESCREVE_NO_LUGAR and any(
            t == BANDEIRA_DE_ESCRITA_NO_LUGAR_POR_EXTENSO
            or t.startswith(BANDEIRA_DE_ESCRITA_NO_LUGAR)
            for t in tokens[1:] if t.startswith("-")):
        escritos += posicionais
    return [sem_o_par_de_aspas_que_envolve(e) for e in escritos if e]


def acoes_do_comando(comando: str, onde: str) -> list:
    acoes = []
    for segmento in separar(comando):
        tokens = partir_em_tokens(segmento.strip())
        for caminho in caminhos_escritos_pelo_segmento(segmento, tokens):
            acoes.append((ACAO_ESCREVER_EM.format(caminho),
                          repositorio_do_caminho(caminho, onde)))
        if tokens and e_git(tokens[0]):
            verbo = verbo_do_git_que_escreve(tokens)
            if verbo:
                declarado = valor_da_bandeira(tokens,
                                              BANDEIRA_DO_DIRETORIO_DO_GIT)
                acoes.append((ACAO_RODAR.format("git " + verbo),
                              repositorio_do_caminho(declarado or ".", onde)))
        if tokens and e_gh(tokens[0]):
            subverbo = subverbo_do_gh_que_escreve(tokens)
            if subverbo:
                declarado = valor_da_bandeira(tokens,
                                              BANDEIRAS_DO_REPOSITORIO_DO_GH)
                acoes.append((ACAO_RODAR.format("gh " + subverbo),
                              repositorio_do_nome_remoto(declarado)
                              if declarado
                              else repositorio_do_caminho(".", onde)))
        if tokens and Path(tokens[0]).name == COMANDO_CD and len(tokens) > 1:
            destino = resolver(sem_o_par_de_aspas_que_envolve(tokens[1]), onde)
            onde = str(destino) if destino else onde
    return acoes


def acoes_do_pedido(entrada: dict, onde: str) -> list:
    ferramenta = entrada.get("tool_name", "")
    dado = entrada.get("tool_input", {}) or {}
    if ferramenta in FERRAMENTAS_DE_ESCRITA:
        for campo in CAMPOS_DE_CAMINHO:
            if dado.get(campo):
                return [(ACAO_ESCREVER_EM.format(dado[campo]),
                         repositorio_do_caminho(dado[campo], onde))]
        return []
    comando = dado.get("command", "")
    return acoes_do_comando(comando, onde) if comando else []


def recusa_do_pedido(entrada: dict, nomes, onde: str):
    if not nomes:
        return None
    for acao, repositorio in acoes_do_pedido(entrada, onde):
        if repositorio and repositorio in nomes:
            return acao, repositorio
    return None


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
        onde = entrada.get("cwd") or os.getcwd()
    except (json.JSONDecodeError, AttributeError, TypeError,
            ValueError) as falha:
        return recusa_por_nao_entender(falha)

    raiz = raiz_do_projeto_nunca_o_cwd()
    recusa = recusa_do_pedido(entrada, nomes_somente_leitura(raiz), onde)
    if not recusa:
        return SILENCIO

    acao, repositorio = recusa
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": EVENTO_ANTES_DA_FERRAMENTA,
        "permissionDecision": DECISAO_DE_NEGAR,
        "permissionDecisionReason": (
            RECUSA.format(
                acao, repositorio, revisor_de(raiz, repositorio),
                CHAVE_DOS_PROJETOS, ARQUIVO_EXECUTOR)
            + MANDA_GRAVAR.format(APRENDIZADO)),
    }}, ensure_ascii=False))
    return SILENCIO


NOME_DO_SOMENTE_LEITURA = "so-leitura"
REVISOR_DO_TESTE = "quem-cuida"
NOME_DO_QUE_ACEITA_ESCRITA = "pode-escrever"


def montar_workspace_de_mentira(pasta: Path) -> None:
    (pasta / PASTA_DO_GIT).mkdir(parents=True, exist_ok=True)
    (pasta / "nucleo").mkdir(parents=True, exist_ok=True)
    (pasta / "nucleo" / "executor.json").write_text(json.dumps(
        {CHAVE_DOS_PROJETOS: {"alvo": {CHAVE_DO_REPOSITORIO: NOME_DO_SOMENTE_LEITURA, CHAVE_DO_SO_LEITURA: True, CHAVE_DO_REVISOR: REVISOR_DO_TESTE}}}),
        encoding="utf-8")
    for nome in (NOME_DO_SOMENTE_LEITURA, NOME_DO_QUE_ACEITA_ESCRITA):
        (pasta / "projetos" / nome / PASTA_DO_GIT).mkdir(
            parents=True, exist_ok=True)
        (pasta / "projetos" / nome / "src").mkdir(parents=True, exist_ok=True)
        (pasta / "projetos" / nome / "x.py").write_text("velho",
                                                        encoding="utf-8")
    (pasta / "conhecimento").mkdir(parents=True, exist_ok=True)


def pedido_de_shell(comando: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": comando}}


def pedido_de_escrita(ferramenta: str, caminho: str) -> dict:
    campo = "notebook_path" if ferramenta == "NotebookEdit" else "file_path"
    return {"tool_name": ferramenta, "tool_input": {campo: caminho}}


BARRA = [
    ("Write nasce dentro do somente leitura",
     pedido_de_escrita("Write", "projetos/so-leitura/novo.py")),
    ("Edit de arquivo que já existe lá",
     pedido_de_escrita("Edit", "projetos/so-leitura/x.py")),
    ("NotebookEdit lá dentro",
     pedido_de_escrita("NotebookEdit", "projetos/so-leitura/n.ipynb")),
    ("git commit por -C", pedido_de_shell(
        "git -C projetos/so-leitura commit -m mudanca")),
    ("git push por -C", pedido_de_shell("git -C projetos/so-leitura push")),
    ("git push depois de cd", pedido_de_shell(
        "cd projetos/so-leitura && git push origin HEAD")),
    ("git checkout -b por -C", pedido_de_shell(
        "git -C projetos/so-leitura checkout -b issue/1-teste")),
    ("git merge por -C", pedido_de_shell(
        "git -C projetos/so-leitura merge origin/main")),
    ("git branch com nome novo", pedido_de_shell(
        "git -C projetos/so-leitura branch nova")),
    ("gh pr create depois de cd", pedido_de_shell(
        "cd projetos/so-leitura && gh pr create --fill")),
    ("gh pr create pelo nome do remoto", pedido_de_shell(
        "gh pr create --repo dono/so-leitura --fill")),
    ("gh issue close fecha trabalho alheio", pedido_de_shell(
        "gh issue close 7 --repo dono/so-leitura")),
    ("gh pr merge aplica por cima", pedido_de_shell(
        "gh pr merge 5 --repo dono/so-leitura --squash")),
    ("redirecionamento para dentro", pedido_de_shell(
        "echo oi > projetos/so-leitura/x.txt")),
    ("apagar lá dentro", pedido_de_shell("rm -rf projetos/so-leitura/src")),
    ("mover lá dentro", pedido_de_shell(
        "mv projetos/so-leitura/x.py projetos/so-leitura/y.py")),
    ("sed no lugar", pedido_de_shell(
        "sed -i 's/a/b/' projetos/so-leitura/x.py")),
    ("copiar PARA dentro", pedido_de_shell(
        "cp projetos/pode-escrever/x.py projetos/so-leitura/x.py")),
]

DEIXA_PASSAR = [
    ("cat lê lá dentro", pedido_de_shell("cat projetos/so-leitura/x.py")),
    ("git log", pedido_de_shell("git -C projetos/so-leitura log --oneline")),
    ("git show", pedido_de_shell(
        "git -C projetos/so-leitura show HEAD:x.py")),
    ("git status", pedido_de_shell(
        "git -C projetos/so-leitura status --porcelain")),
    ("git diff", pedido_de_shell("git -C projetos/so-leitura diff")),
    ("git branch --show-current", pedido_de_shell(
        "git -C projetos/so-leitura branch --show-current")),
    ("git tag -l", pedido_de_shell("git -C projetos/so-leitura tag -l v1*")),
    ("git fetch não muda conteúdo", pedido_de_shell(
        "git -C projetos/so-leitura fetch origin")),
    ("grep varre lá dentro", pedido_de_shell(
        "grep -rn assunto projetos/so-leitura")),
    ("gh issue view", pedido_de_shell(
        "cd projetos/so-leitura && gh issue view 3")),
    ("gh pr view", pedido_de_shell(
        "cd projetos/so-leitura && gh pr view 2")),
    ("gh issue comment leva resposta, não muda código", pedido_de_shell(
        "gh issue comment 7 --repo dono/so-leitura --body-file r.md")),
    ("gh issue create leva achado com evidência", pedido_de_shell(
        "gh issue create --repo dono/so-leitura --title t --body-file c.md")),
    ("gh pr comment conversa no fio", pedido_de_shell(
        "cd projetos/so-leitura && gh pr comment 5 --body oi")),
    ("gh pr close retira a própria sugestão", pedido_de_shell(
        "gh pr close 5 --repo dono/so-leitura")),
    ("gh issue edit corrige a própria proposta", pedido_de_shell(
        "gh issue edit 7 --repo dono/so-leitura --body-file c.md")),
    ("sed que só lê", pedido_de_shell(
        "sed -n '1,5p' projetos/so-leitura/x.py")),
    ("copiar DE dentro para fora", pedido_de_shell(
        "cp projetos/so-leitura/x.py projetos/pode-escrever/copia.py")),
    ("Write no repositório que aceita escrita",
     pedido_de_escrita("Write", "projetos/pode-escrever/novo.py")),
    ("git push no repositório que aceita escrita", pedido_de_shell(
        "git -C projetos/pode-escrever push")),
    ("Write no próprio workspace",
     pedido_de_escrita("Write", "conhecimento/nota.md")),
]


def testar() -> int:
    import tempfile
    falhas, comportamento = [], []
    with tempfile.TemporaryDirectory(prefix="veto-somente-leitura-") as tmp:
        raiz = Path(tmp).resolve()
        montar_workspace_de_mentira(raiz)
        onde = str(raiz)
        nomes = nomes_somente_leitura(raiz)

        for rotulo, pedido in BARRA:
            if not recusa_do_pedido(pedido, nomes, onde):
                falhas.append(FALHA_BARRA.format(rotulo))
        for rotulo, pedido in DEIXA_PASSAR:
            recusa = recusa_do_pedido(pedido, nomes, onde)
            if recusa:
                falhas.append(FALHA_DEIXA_PASSAR.format(rotulo, recusa[0]))

        def caso(rotulo, condicao):
            comportamento.append((rotulo, bool(condicao)))

        caso("gancho que veta e não entende o pedido RECUSA, e nomeia a "
             "falha — quem não consegue julgar não pode dizer sim",
             recusou_sem_entender(TypeError("forma que o gancho não conhece")))
        caso("a lista declarada vira cerca",
             nomes == frozenset({NOME_DO_SOMENTE_LEITURA}))
        (raiz / "nucleo" / "executor.json").write_text(json.dumps({}),
                                                       encoding="utf-8")
        caso("sem o campo declarado, nada muda",
             not nomes_somente_leitura(raiz)
             and not recusa_do_pedido(BARRA[0][1],
                                      nomes_somente_leitura(raiz), onde))
        (raiz / "nucleo" / "executor.json").write_text(json.dumps(
            {CHAVE_DOS_PROJETOS: {"alvo": {CHAVE_DO_REPOSITORIO: "${NOME}", CHAVE_DO_SO_LEITURA: True}}}), encoding="utf-8")
        caso("nome ainda no molde não vira cerca",
             not nomes_somente_leitura(raiz))
        montar_workspace_de_mentira(raiz)

        recusa = recusa_do_pedido(BARRA[3][1], nomes, onde)
        mensagem = RECUSA.format(recusa[0], recusa[1],
                                 revisor_de(raiz, recusa[1]),
                                 CHAVE_DOS_PROJETOS, ARQUIVO_EXECUTOR)
        caso("a mensagem nomeia o repositório",
             NOME_DO_SOMENTE_LEITURA in mensagem)
        caso("a mensagem nomeia o revisor declarado, nao só o território",
             REVISOR_DO_TESTE in mensagem)
        caso("sem revisor declarado, ela cai no território sem quebrar",
             SEM_REVISOR in RECUSA.format(
                 "x", "nao-declarado", revisor_de(raiz, "nao-declarado"),
                 CHAVE_DOS_PROJETOS, ARQUIVO_EXECUTOR))
        caso("a recusa nomeia a regra 9, diz onde o valor certo mora e "
             "manda gravar o aprendizado em conhecimento/",
             "Regra 9" in mensagem + MANDA_GRAVAR.format(APRENDIZADO)
             and ARQUIVO_EXECUTOR in mensagem
             and "regra 4" in MANDA_GRAVAR.format(APRENDIZADO)
             and "`conhecimento/`" in MANDA_GRAVAR.format(APRENDIZADO))
        caso("a mensagem ensina o pedido de incorporação como sugestão",
             "SUGESTÃO" in mensagem and "incorporação" in mensagem)
        caso("a mensagem ensina a marcar quem revisa",
             "revisão" in mensagem and "território" in mensagem)
        caso("a mensagem diz onde se muda a lista",
             CHAVE_DOS_PROJETOS in mensagem
             and ARQUIVO_EXECUTOR in mensagem)

        caso("caminho absoluto é o mesmo repositório",
             recusa_do_pedido(pedido_de_escrita(
                 "Write", str(raiz / "projetos" / NOME_DO_SOMENTE_LEITURA
                              / "abs.py")), nomes, onde))
        caso("caminho fora de repositório nenhum passa",
             not recusa_do_pedido(pedido_de_escrita("Write", "/dev/null"),
                                  nomes, onde))
        caso("aspas desbalanceadas não derrubam o gancho",
             isinstance(acoes_do_comando(
                 "echo 'sem fechar > projetos/so-leitura/x.txt", onde), list))
        caso("documento literal não vira comando",
             not recusa_do_pedido(pedido_de_shell(
                 "python3 - <<'PY'\ngit -C projetos/so-leitura push\nPY"),
                 nomes, onde))
        caso("entrada sem ferramenta nem comando não devolve ação",
             acoes_do_pedido({}, onde) == [])
        caso("2>&1 não vira arquivo escrito",
             not recusa_do_pedido(pedido_de_shell(
                 "git -C projetos/so-leitura log 2>&1"), nomes, onde))

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



def recusou_sem_entender(falha) -> bool:
    import contextlib
    import io
    saida = io.StringIO()
    with contextlib.redirect_stdout(saida):
        recusa_por_nao_entender(falha)
    try:
        dado = json.loads(saida.getvalue())["hookSpecificOutput"]
    except (ValueError, KeyError):
        return False
    return (dado.get("permissionDecision") == DECISAO_DE_NEGAR
            and type(falha).__name__
            in dado.get("permissionDecisionReason", ""))


def main() -> int:
    try:
        return decidir()
    except Exception as falha:
        return recusa_por_nao_entender(falha)


if __name__ == "__main__":
    if BANDEIRA_DE_TESTE in sys.argv:
        sys.exit(testar())
    sys.exit(main())
