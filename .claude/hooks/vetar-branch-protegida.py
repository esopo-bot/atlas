import json
import os
import re
import subprocess
import sys
from pathlib import Path

PROTEGIDAS_EMBUTIDAS = {
    "main", "master", "trunk",
    "develop", "development",
    "homolog", "homologacao", "staging", "stage", "hml", "qa", "uat",
    "release", "prod", "producao", "production",
}
ARQUIVO_DE_BRANCHES_PROTEGIDAS = ".claude/branches-protegidas.txt"
ARQUIVO_CONFIGURACAO = "nucleo/configuracao.json"
CHAVE_DAS_AUTORIZACOES = "autorizacoes"
CHAVE_POR_INCORPORACAO = "branches_por_incorporacao"
MARCA_DE_COMENTARIO = "#"
PASTA_DO_GIT = ".git"

VARIAVEL_DA_RAIZ_DO_PROJETO = "CLAUDE_PROJECT_DIR"
NIVEIS_DO_GANCHO_ATE_A_RAIZ = 2

BANDEIRAS_GLOBAIS_SIMPLES = {"--no-pager", "--paginate", "-p", "--bare",
                             "--literal-pathspecs"}
BANDEIRAS_GLOBAIS_QUE_COMEM_O_TOKEN_SEGUINTE = {
    "-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path",
    "-R", "--repo"}

SEPARADORES_DE_COMANDO = re.compile(r"&&|\|\||;|\||\n|\r|\$\(|`|\)")
EXPANSAO_QUE_ASPA_DUPLA_NAO_SEGURA = re.compile(r"\$\(|`|\)")
DOCUMENTO_LITERAL_QUE_NAO_EXPANDE = re.compile(
    r"<<-?\s*(['\"])(\w+)\1.*?(?:^\2\s*$|\Z)", re.S | re.M)
ASPA_SIMPLES = "'"
ASPA_DUPLA = '"'
ASPAS = "\"'"

VERBO_PUSH = "push"
VERBO_BRANCH = "branch"
VERBOS_QUE_MEXEM_EM_BRANCH = {VERBO_PUSH, VERBO_BRANCH}
BANDEIRAS_DE_APAGAR = {"-d", "--delete"}
BANDEIRAS_DE_RENOMEAR = {"-m", "--move"}
BANDEIRAS_DE_FORCA = {"-f", "--force"}
BANDEIRAS_DE_FORCA_COM_RESSALVA = ("--force-with-lease", "--force-if-includes")
BANDEIRA_DE_ESPELHO = "--mirror"
PREFIXO_DE_APAGAR_POR_REFSPEC = ":"
PREFIXO_DE_FORCAR_POR_REFSPEC = "+"
ACAO_APAGAR = "apagar"
ACAO_RENOMEAR = "renomear"
ACAO_COMMIT = "commit"
VERBO_MERGE = "merge"
VERBO_INIT = "init"
VERBO_CHECKOUT = "checkout"
VERBO_SWITCH = "switch"
VERBOS_QUE_TROCAM_DE_BRANCH = {VERBO_CHECKOUT, VERBO_SWITCH}
BANDEIRAS_QUE_CRIAM_BRANCH = {"-b", "-c"}
FIM_DAS_BANDEIRAS = "--"
SEPARADOR_QUE_ENCADEIA = "&&"
COMANDO_DAS_BRANCHES = ["git", "for-each-ref", "--format=%(refname:short)",
                        "refs/heads/"]

NOMES_DO_GIT = {"git", "git.exe"}
NOME_DO_GH = "gh"
EXTENSAO_EXE = ".exe"
PROGRAMAS_QUE_ACIONAM = ("git", "gh")
COMANDO_CD = "cd"
COMANDO_DA_BRANCH_ATUAL = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
TEMPO_LIMITE_DO_GIT = 5
HEAD_SOLTA = "head"
PREFIXO_DE_REFS_DE_BRANCH = re.compile(r"^refs/heads/")

SUBVERBOS_QUE_SO_PEDEM = {
    "pr": frozenset({"create", "view", "list", "status", "diff", "checks",
                     "comment", "edit", "ready", "checkout", "close",
                     "reopen", "review"}),
}
VERBOS_POR_ACAO = {
    "commit": ("commit",),
    "push": ("push",),
    "publicar": ("pr", "release", VERBO_MERGE),
}
OMISSAO_NAO_E_PERMISSAO = {"commit": False, "push": False, "publicar": False}

MARCA_DO_GIT = "git"
MARCA_DO_GH = "gh "
EVENTO_ANTES_DA_FERRAMENTA = "PreToolUse"
DECISAO_DE_NEGAR = "deny"
BANDEIRA_DE_TESTE = "--testar"
SEM_ACAO = ""
SEM_VERBO = -1
SEM_RECUSA = ""
SILENCIO = 0
RECUSA_SEM_ENTENDER = (
    "Este gancho não entendeu o pedido, e por isso recusa em vez de liberar: "
    "{} — {}. Quem veta e não consegue julgar não pode dizer sim: a parede "
    "sumiria em silêncio, e o verde passaria a significar `ninguém olhou`. "
    "Se o pedido é legítimo, conserte o gancho ou desligue-o em "
    ".claude/settings.json — o caminho nunca é atravessar por aqui."
)

MOTIVO_BRANCH_PROTEGIDA = "{} a branch protegida '{}'"
MOTIVO_GRAVA_EM_PROTEGIDA = (
    "{} direto na branch '{}', que este repositório declarou de "
    "incorporação — o controle é o pedido de "
    "incorporação, não a gravação. Abra uma branch de trabalho, "
    "entregue nela e peça a incorporação. Autorização declarada não "
    "vale para branch de longa duração.")
MOTIVO_ESPELHO = ("reescrever todas as refs do remoto de uma vez (--mirror), "
                  "as protegidas inclusive")
MOTIVO_APAGAR_POR_REFSPEC = (
    "apagar a branch protegida '{}' (refspec com dois-pontos)")
MOTIVO_FORCAR_POR_REFSPEC = (
    "reescrever a branch protegida '{}' (refspec com mais)")
MOTIVO_REESCREVER_HISTORIA = (
    "reescrever a história da branch protegida '{}'")
MOTIVO_REESCREVER_A_BRANCH_ATUAL = (
    "reescrever a história de '{}', a branch atual e protegida")
MOTIVO_SEM_AUTORIZACAO = (
    "{} sem autorização declarada — `autorizacoes.{}` não está ligado em {}")
MARCA_DA_RECUSA_POR_AUTORIZACAO = "sem autorização declarada"

MANDA_GRAVAR = (
    "\nGrave o aprendizado antes de tentar de novo — regra 4, a memória "
    "mora no disco, e recusa que a próxima sessão repete não ensinou "
    "nada. A linha, em `conhecimento/`:\n"
    "    {}"
)
APRENDIZADO_DA_AUTORIZACAO = (
    "o que a automação faz sozinha se declara em `nucleo/configuracao.json`, "
    "campo `autorizacoes` — omissão não é permissão."
)
APRENDIZADO_DA_BRANCH = (
    "branch de longa duração não se reescreve nem se apaga daqui: trabalhe "
    "na sua branch e peça a promoção ao dono."
)
RECUSA_POR_AUTORIZACAO = (
    "Regra 9 da camada: isto quer {}. O que a automação faz sozinha se "
    "declara — ligue a chave em `nucleo/configuracao.json`, campo "
    "`autorizacoes`, ou peça ao dono que rode o comando. Omissão não é "
    "permissão."
)
RECUSA_POR_BRANCH_PROTEGIDA = (
    "Regra 12 da camada: isto quer {}. Branch de longa duração é "
    "infraestrutura de outras pessoas — desfazer é público e caro. O "
    "caminho: trabalhe na sua branch e peça a promoção ao dono, que roda o "
    "comando ele mesmo. Se esta branch não deveria estar protegida, tire o "
    "nome de .claude/branches-protegidas.txt."
)

FALHA_DEVIA_BARRAR = "  DEVIA BARRAR e passou — {}: {}"
FALHA_DEVIA_PASSAR = "  DEVIA PASSAR e barrou — {}: {} ({})"
FALHA_DEVIA_BARRAR_SEM_AUTORIZACAO = (
    "  DEVIA BARRAR sem autorização e passou — {}")
FALHA_DEVIA_PASSAR_COM_AUTORIZACAO = (
    "  DEVIA PASSAR com autorização e barrou — {}")
FALHA_RECUSA_NAO_ENSINA = "  a recusa não ensina — {}"
FALHA_FORCA_MESMO_AUTORIZADO = (
    "  DEVIA BARRAR: força em protegida, mesmo autorizado")
RESUMO_FALHOU = "FALHOU: {} de {} casos"
RESUMO_OK = "OK: {} casos — {} barrados, {} liberados"


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


def nomes_protegidos(raiz: Path) -> set:
    arquivo = raiz / ARQUIVO_DE_BRANCHES_PROTEGIDAS
    try:
        linhas = arquivo.read_text(encoding="utf-8").splitlines()
    except OSError:
        return set(PROTEGIDAS_EMBUTIDAS)
    nomes = {l.strip().lower() for l in linhas
             if l.strip() and not l.strip().startswith(MARCA_DE_COMENTARIO)}
    return nomes or set(PROTEGIDAS_EMBUTIDAS)


def branch_de_destino_do_ref(ref: str) -> str:
    ref = ref.strip().lstrip(PREFIXO_DE_FORCAR_POR_REFSPEC)
    if PREFIXO_DE_APAGAR_POR_REFSPEC in ref:
        ref = ref.split(PREFIXO_DE_APAGAR_POR_REFSPEC, 1)[1]
    ref = PREFIXO_DE_REFS_DE_BRANCH.sub("", ref)
    return ref.strip().lower()


def e_git(token: str) -> bool:
    return Path(token.replace("\\", "/")).name.lower() in NOMES_DO_GIT


def e_gh(token: str) -> bool:
    return Path(token).name.lower().removesuffix(EXTENSAO_EXE) == NOME_DO_GH


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


def verbo_e_resto(tokens: list):
    i = indice_do_verbo(tokens)
    if i == SEM_VERBO:
        return None, []
    return tokens[i].lower(), tokens[i + 1:]


def branch_atual(alvo: Path):
    try:
        r = subprocess.run(COMANDO_DA_BRANCH_ATUAL, cwd=alvo,
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=TEMPO_LIMITE_DO_GIT)
    except (OSError, subprocess.SubprocessError):
        return None
    nome = r.stdout.strip().lower()
    return nome if r.returncode == 0 and nome and nome != HEAD_SOLTA else None


def branches_conhecidas(alvo: Path) -> set:
    try:
        r = subprocess.run(COMANDO_DAS_BRANCHES, cwd=alvo,
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=TEMPO_LIMITE_DO_GIT)
    except (OSError, subprocess.SubprocessError):
        return set()
    if r.returncode != 0:
        return set()
    return {linha.strip().lower() for linha in r.stdout.splitlines()
            if linha.strip()}


def branch_pedida_ao_checkout(resto: list):
    if FIM_DAS_BANDEIRAS in resto:
        return "", False
    espera_o_nome = False
    for token in resto:
        if espera_o_nome:
            return token.lower(), True
        if token.lower() in BANDEIRAS_QUE_CRIAM_BRANCH:
            espera_o_nome = True
            continue
        if token.startswith("-"):
            continue
        return token.lower(), False
    return "", False


def a_linha_so_encadeia(comando: str) -> bool:
    return not SEPARADORES_DE_COMANDO.search(
        comando.replace(SEPARADOR_QUE_ENCADEIA, " "))


def branch_depois_do_segmento(tokens: list, aqui: str, conhecidas: set) -> str:
    if not tokens or not e_git(tokens[0]):
        return aqui
    verbo, resto = verbo_e_resto(tokens)
    if verbo not in VERBOS_QUE_TROCAM_DE_BRANCH:
        return aqui
    nome, criada = branch_pedida_ao_checkout(resto)
    if not nome:
        return aqui
    return nome if criada or nome in conhecidas else aqui


def cd_que_abre_o_comando(comando: str) -> str:
    segmentos = separar(comando)
    primeiro = segmentos[0].strip() if segmentos else ""
    tokens = partir_em_tokens(primeiro)
    if len(tokens) >= 2 and Path(tokens[0]).name == COMANDO_CD:
        return tokens[1]
    return ""


def comando_traz_git_init(comando: str) -> bool:
    for segmento in separar(comando):
        tokens = partir_em_tokens(segmento.strip())
        if not tokens or not e_git(tokens[0]):
            continue
        i = indice_do_verbo(tokens)
        if i != SEM_VERBO and tokens[i].lower() == VERBO_INIT:
            return True
    return False


def repositorio_que_o_comando_muda(onde: str, padrao: Path,
                                   comando: str = "") -> Path:
    if (destino := cd_que_abre_o_comando(comando)):
        alvo = Path(destino)
        onde = str(alvo if alvo.is_absolute() else Path(onde or ".") / alvo)
    if not onde:
        return padrao
    atual = Path(onde)
    try:
        atual = atual.resolve(strict=False)
    except OSError:
        return padrao
    if comando_traz_git_init(comando):
        return atual
    while True:
        if (atual / PASTA_DO_GIT).exists():
            return atual
        if atual.parent == atual:
            return padrao
        atual = atual.parent


def autorizacoes(raiz: Path) -> dict:
    permitido = dict(OMISSAO_NAO_E_PERMISSAO)
    try:
        dado = json.loads(
            (raiz / ARQUIVO_CONFIGURACAO).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return permitido
    declarado = (dado.get(CHAVE_DAS_AUTORIZACOES)
                 if isinstance(dado, dict) else None)
    if not isinstance(declarado, dict):
        return permitido
    for acao in permitido:
        valor = declarado.get(acao)
        if isinstance(valor, bool):
            permitido[acao] = valor
    return permitido


def acao_do_comando(tokens: list) -> str:
    if not tokens:
        return SEM_ACAO
    programa = Path(tokens[0]).name.lower().removesuffix(EXTENSAO_EXE)
    if programa not in PROGRAMAS_QUE_ACIONAM:
        return SEM_ACAO
    i = indice_do_verbo(tokens)
    if i == SEM_VERBO:
        return SEM_ACAO
    primeiro = tokens[i].lower()
    segundo = tokens[i + 1].lower() if i + 1 < len(tokens) else ""
    if segundo in SUBVERBOS_QUE_SO_PEDEM.get(primeiro, frozenset()):
        return SEM_ACAO
    e_do_git = Path(tokens[0]).name.lower() in NOMES_DO_GIT
    if primeiro == VERBO_MERGE and e_do_git:
        return ACAO_COMMIT
    for acao, verbos in VERBOS_POR_ACAO.items():
        if primeiro in verbos:
            return acao
    return SEM_ACAO


def recusa_do_verbo_branch(bandeiras: set, atingidas: list) -> str:
    apaga = bool(bandeiras & BANDEIRAS_DE_APAGAR)
    renomeia = bool(bandeiras & BANDEIRAS_DE_RENOMEAR)
    if (apaga or renomeia) and atingidas:
        return MOTIVO_BRANCH_PROTEGIDA.format(
            ACAO_APAGAR if apaga else ACAO_RENOMEAR, atingidas[0])
    return SEM_RECUSA


def recusa_do_verbo_push(bandeiras: set, resto: list, refs: list,
                         atingidas: list, protegidas: set, alvo: Path,
                         aqui: str = None) -> str:
    if BANDEIRA_DE_ESPELHO in bandeiras:
        return MOTIVO_ESPELHO

    apaga = bool(bandeiras & BANDEIRAS_DE_APAGAR)
    forca = bool(bandeiras & BANDEIRAS_DE_FORCA) or any(
        b.startswith(BANDEIRAS_DE_FORCA_COM_RESSALVA) for b in bandeiras)

    def destinos_com_prefixo(prefixo):
        return [branch_de_destino_do_ref(t) for t in resto
                if not t.startswith("-") and t.startswith(prefixo)]

    for nome in destinos_com_prefixo(PREFIXO_DE_APAGAR_POR_REFSPEC):
        if nome in protegidas:
            return MOTIVO_APAGAR_POR_REFSPEC.format(nome)
    for nome in destinos_com_prefixo(PREFIXO_DE_FORCAR_POR_REFSPEC):
        if nome in protegidas:
            return MOTIVO_FORCAR_POR_REFSPEC.format(nome)
    if apaga and atingidas:
        return MOTIVO_BRANCH_PROTEGIDA.format(ACAO_APAGAR, atingidas[0])
    if forca and atingidas:
        return MOTIVO_REESCREVER_HISTORIA.format(atingidas[0])
    if forca and not refs:
        atual = branch_atual(alvo) if aqui is None else aqui
        if atual in protegidas:
            return MOTIVO_REESCREVER_A_BRANCH_ATUAL.format(atual)
    return SEM_RECUSA


def branches_por_incorporacao(raiz: Path) -> set:
    try:
        dado = json.loads(
            (raiz / ARQUIVO_CONFIGURACAO).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    declarado = (dado.get(CHAVE_POR_INCORPORACAO)
                 if isinstance(dado, dict) else None)
    if not isinstance(declarado, list):
        return set()
    return {str(nome).strip().lower() for nome in declarado if str(nome).strip()}


def motivo_da_recusa(comando: str, protegidas: set, alvo: Path,
                     permitido: dict = None, aqui: str = None,
                     por_incorporacao: set = None, conhecidas: set = None):
    permitido = OMISSAO_NAO_E_PERMISSAO if permitido is None else permitido
    aqui = branch_atual(alvo) if aqui is None else aqui
    por_incorporacao = (branches_por_incorporacao(alvo)
                        if por_incorporacao is None else por_incorporacao)
    conhecidas = (branches_conhecidas(alvo) if conhecidas is None
                  else conhecidas)
    recusa_por_autorizacao_pendente = SEM_RECUSA
    segue_a_branch = a_linha_so_encadeia(comando)
    for segmento in separar(comando):
        tokens = partir_em_tokens(segmento.strip())
        if not tokens or not (e_git(tokens[0]) or e_gh(tokens[0])):
            continue
        if segue_a_branch:
            aqui = branch_depois_do_segmento(tokens, aqui, conhecidas)

        acao = acao_do_comando(tokens)
        if acao == ACAO_COMMIT and aqui in por_incorporacao:
            return MOTIVO_GRAVA_EM_PROTEGIDA.format(acao, aqui)
        if (acao and not permitido.get(acao, False)
                and not recusa_por_autorizacao_pendente):
            recusa_por_autorizacao_pendente = MOTIVO_SEM_AUTORIZACAO.format(
                acao, acao, ARQUIVO_CONFIGURACAO)

        verbo, resto = verbo_e_resto(tokens)
        if verbo not in VERBOS_QUE_MEXEM_EM_BRANCH:
            continue

        bandeiras = {t.lower() for t in resto if t.startswith("-")}
        refs = [branch_de_destino_do_ref(t)
                for t in resto if not t.startswith("-")]
        atingidas = [r for r in refs if r in protegidas]

        recusa = (recusa_do_verbo_branch(bandeiras, atingidas)
                  if verbo == VERBO_BRANCH else
                  recusa_do_verbo_push(bandeiras, resto, refs, atingidas,
                                       protegidas, alvo, aqui))
        if recusa:
            return recusa
    return recusa_por_autorizacao_pendente or None


ARQUIVO_EXECUTOR = "nucleo/executor.json"
CHAVE_DOS_PROJETOS = "projetos"
CHAVE_DO_REPOSITORIO = "repositorio"
CHAVE_DO_SO_LEITURA = "somente_leitura"
CHAVE_DAS_AUTORIZACOES_DO_VIZINHO = "autorizacoes"


def _projetos(raiz: Path) -> dict:
    try:
        dado = json.loads(
            (raiz / ARQUIVO_EXECUTOR).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    projetos = (dado or {}).get(CHAVE_DOS_PROJETOS) or {}
    return projetos if isinstance(projetos, dict) else {}


def _projeto_do_repositorio(raiz: Path, nome: str) -> dict:
    for projeto in _projetos(raiz).values():
        if isinstance(projeto, dict) \
                and projeto.get(CHAVE_DO_REPOSITORIO) == nome:
            return projeto
    return {}


def e_somente_leitura(raiz: Path, alvo: Path) -> bool:
    projeto = _projeto_do_repositorio(raiz, Path(alvo).name)
    return bool(projeto.get(CHAVE_DO_SO_LEITURA))


def autorizacoes_do_alvo(raiz: Path, alvo: Path) -> dict:
    if Path(alvo) == Path(raiz):
        return autorizacoes(alvo)
    declarado = _projeto_do_repositorio(raiz, Path(alvo).name).get(
        CHAVE_DAS_AUTORIZACOES_DO_VIZINHO)
    if isinstance(declarado, dict):
        permitido = dict(OMISSAO_NAO_E_PERMISSAO)
        for acao in permitido:
            if isinstance(declarado.get(acao), bool):
                permitido[acao] = declarado[acao]
        return permitido
    return autorizacoes(alvo)


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
        comando = entrada.get("tool_input", {}).get("command", "")
        onde = entrada.get("cwd") or ""
    except (json.JSONDecodeError, AttributeError, TypeError,
            ValueError) as falha:
        return recusa_por_nao_entender(falha)

    baixo = (comando or "").lower()
    nada_de_git_nem_de_gh = (MARCA_DO_GIT not in baixo
                             and MARCA_DO_GH not in baixo)
    if not comando or nada_de_git_nem_de_gh:
        return SILENCIO

    raiz = raiz_do_projeto_nunca_o_cwd()
    alvo = repositorio_que_o_comando_muda(onde, raiz, comando)
    if e_somente_leitura(raiz, alvo):
        return SILENCIO
    motivo = motivo_da_recusa(
        comando, nomes_protegidos(alvo), alvo,
        autorizacoes_do_alvo(raiz, alvo), None,
        branches_por_incorporacao(alvo))
    if not motivo:
        return SILENCIO

    e_recusa_por_autorizacao = MARCA_DA_RECUSA_POR_AUTORIZACAO in motivo
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": EVENTO_ANTES_DA_FERRAMENTA,
        "permissionDecision": DECISAO_DE_NEGAR,
        "permissionDecisionReason": (
            RECUSA_POR_AUTORIZACAO.format(motivo)
            + MANDA_GRAVAR.format(APRENDIZADO_DA_AUTORIZACAO)
            if e_recusa_por_autorizacao
            else RECUSA_POR_BRANCH_PROTEGIDA.format(motivo)
            + MANDA_GRAVAR.format(APRENDIZADO_DA_BRANCH)),
    }}))
    return SILENCIO


BARRA = [
    ("apagar local, forma óbvia", "git branch -d homolog"),
    ("apagar local, maiúscula", "git branch -D develop"),
    ("apagar no remoto", "git push origin --delete homolog"),
    ("apagar por refspec", "git push origin :homolog"),
    ("forçar, forma óbvia", "git push --force origin main"),
    ("forçar, o que o glob não pega", "git push origin +homolog"),
    ("forçar com lease ainda reescreve",
     "git push --force-with-lease origin develop"),
    ("escondida depois de &&", "git status && git push --force origin homolog"),
    ("bandeira antes do verbo", "git -C /tmp/x push --force origin main"),
    ("configuração antes do verbo", "git -c user.name=x branch -D main"),
    ("caminho absoluto do programa", "/usr/bin/git branch -d homolog"),
    ("no Windows, com .exe", "git.exe push origin --delete main"),
    ("renomear a protegida", "git branch -m develop develop-velha"),
    ("refs/heads explícito", "git push origin +refs/heads/main"),
    ("forçar na forma curta", "git push -f origin homolog"),
    ("caminho do Windows antes do verbo",
     r"git -C C:\repo push --force origin main"),
    ("escondido depois da quebra de linha",
     "git status\ngit push --force origin main"),
    ("aspas duplas no nome da branch", 'git branch -D "main"'),
    ("aspas simples no nome da branch", "git push origin --delete 'homolog'"),
    ("espelhar reescreve tudo", "git push --mirror origin"),
    ("escondido dentro de subcomando",
     "git status $(git push --force origin main)"),
    ("aspa solta não abre porta",
     "git status ' && git push --force origin main"),
    ("aspas duplas não seguram o subcomando",
     'git status "$(git push --force origin main)"'),
    ("documento que expande ainda executa",
     "cat <<FIM\n$(git push --force origin main)\nFIM"),
]

SO_PEDEM = [
    ("abrir PR é pedir, não publicar — o dono é quem incorpora",
     "gh pr create --fill"),
    ("ver PR não muda nada", "gh pr view 1"),
    ("listar PR não muda nada", "gh pr list"),
    ("comentar em PR é falar, não publicar",
     "gh pr comment 13 --body texto"),
    ("etiquetar PR não incorpora nada", "gh pr edit 13 --add-label pronto"),
    ("tirar o rascunho não incorpora nada", "gh pr ready 13"),
    ("baixar o PR mexe só na cópia local", "gh pr checkout 13"),
]

DEIXA_PASSAR = [
    ("push normal na protegida", "git push origin develop"),
    ("push normal, sem ref", "git push"),
    ("apagar branch de trabalho", "git branch -d feature/x"),
    ("forçar branch de trabalho", "git push --force origin feature/x"),
    ("nome que só parece", "git branch -d develop-antiga"),
    ("nome que contém a protegida",
     "git push origin --delete feature/main-menu"),
    ("outro programa", "docker push imagem:main"),
    ("commit comum", "git commit -m 'apaga develop do texto'"),
    ("criar branch a partir da protegida", "git branch feature/nova develop"),
    ("checkout da protegida", "git checkout main"),
    ("buscar do remoto", "git fetch origin main"),
    ("listar branches", "git branch -a"),
    ("push normal para a protegida", "git push origin main"),
    ("quebra de linha, trabalho comum", "git status\ngit push origin feature/x"),
    ("aspas duplas em branch de trabalho", 'git branch -D "feature/x"'),
    ("aspas simples em nome que só parece",
     "git push origin --delete 'feature/homolog-antiga'"),
    ("espelhar em clone não é push",
     "git clone --mirror https://exemplo.invalido/r.git"),
    ("subcomando que não empurra nada", "git status $(git rev-parse HEAD)"),
    ("mensagem de commit que cita o veto",
     'git commit -m "não rode git push --force origin main"'),
    ("aspas simples seguram o comando inteiro",
     "echo 'git push --force origin main'"),
    ("documento literal é dado, não comando",
     "gh issue comment 13 --body-file - <<'FIM'\ngit push --force origin main"
     "\nFIM"),
]

GIT_MERGE_NAO_E_PUBLICAR = [
    ("merge local em branch de trabalho não é publicar",
     "git merge --ff-only origin/main"),
    ("merge local com mensagem também não",
     'git merge homolog -m "junta"'),
]
GIT_MERGE_EM_PROTEGIDA = [
    ("merge grava na protegida sem passar pelo pedido",
     "git merge homolog"),
]
GH_MERGE_CONTINUA_SENDO_PUBLICAR = [
    ("gh pr merge continua exigindo autorização de publicar",
     "gh pr merge 8 --merge"),
]
SAI_DA_PROTEGIDA_ANTES_DE_GRAVAR = [
    ("o checkout na mesma linha tira a gravação da protegida",
     "git checkout homolog && git merge --ff-only main"),
    ("switch vale igual ao checkout",
     "git switch homolog && git merge main"),
    ("branch nova nasce fora da protegida, e o commit cai nela",
     "git checkout -b issue/9-x && git commit -m x"),
    ("switch -c também cria fora", "git switch -c issue/9-x && git commit -m x"),
]
ENTRA_NA_PROTEGIDA_E_GRAVA = [
    ("entrar na protegida e gravar continua barrado",
     "git checkout main && git commit -m x"),
    ("switch para a protegida idem", "git switch main && git merge outra"),
    ("checkout que pode FALHAR nao livra o commit seguinte quando o "
     "separador nao encadeia: com ponto e virgula o commit roda de todo "
     "jeito, e cai na protegida",
     "git checkout -b issue/9 ; git commit -m x"),
    ("nem com o ou-senao, que roda o seguinte justamente quando falhou",
     "git switch -c issue/9 || echo ja existe ; git commit -m x"),
]
RESTAURA_ARQUIVO_E_NAO_TROCA_DE_BRANCH = [
    ("restaurar arquivo de outra branch nao e trocar de branch",
     "git checkout main -- montar.py && git commit -m x"),
    ("com o switch nao existe pathspec, mas o checkout de arquivo solto "
     "tambem nao troca nada",
     "git checkout main -- . && git commit -m x"),
]
FALHA_RESTAURO_VIROU_TROCA = (
    "  DEVIA PASSAR: restaurar arquivo de outra branch nao muda a branch "
    "atual — {}")
BRANCHES_CONHECIDAS_DO_TESTE = {"main", "homolog", "outra"}
FALHA_SAIU_DA_PROTEGIDA_E_BARROU = (
    "  DEVIA PASSAR: o checkout na linha muda a branch antes da gravação — {}")
FALHA_ENTROU_NA_PROTEGIDA_E_PASSOU = (
    "  DEVIA BARRAR: a linha entra na branch de incorporação e grava — {}")
FALHA_ARQUIVO_VIROU_BRANCH = (
    "  DEVIA BARRAR: 'git checkout arquivo.txt' não é troca de branch, e o "
    "commit seguinte ainda cai na protegida")
FALHA_MERGE_LOCAL_BARRADO = (
    "  DEVIA PASSAR: git merge local não é publicar — {}")
FALHA_MERGE_EM_PROTEGIDA_PASSOU = (
    "  DEVIA BARRAR: git merge grava na branch de incorporação — {}")
FALHA_GH_MERGE_PASSOU = (
    "  DEVIA BARRAR sem autorização de publicar — {}")

BARRA_SEM_AUTORIZACAO = [
    ("commit sem autorização", "git commit -m x"),
    ("push sem autorização", "git push origin feature/minha"),
    ("mesclar PR sem autorização", "gh pr merge 1 --merge"),
    ("publicar release sem autorização", "gh release create v1"),
    ("bandeira global não esconde o merge",
     "gh --repo d/r pr merge 13 --merge"),
    ("bandeira global curta também não esconde",
     "gh -R d/r pr merge 13 --merge"),
    ("o caminho do -C não é o verbo", "git -C /tmp/x commit -m algo"),
    ("a configuração do -c não é o verbo",
     "git -c user.name=x commit -m algo"),
]

AUTORIZA_TUDO = {"commit": True, "push": True, "publicar": True}
FORCA_EM_PROTEGIDA = "git push --force origin main"
BRANCH_DE_TRABALHO_DO_TESTE = "issue/1-algo"
BRANCH_DE_INTEGRACAO_DO_TESTE = "homolog"
BRANCHES_POR_INCORPORACAO_DO_TESTE = ("main",)
GRAVA_EM_PROTEGIDA = (
    ("commit direto", 'git commit -m "algo"'),
    ("commit com todos", "git commit -am algo"),
    ("commit por caminho absoluto", '/usr/bin/git commit -m "algo"'),
)
FALHA_GRAVOU_EM_PROTEGIDA = (
    "  DEVIA BARRAR mesmo autorizado, em '{}' na branch '{}'")
FALHA_BARROU_NA_DE_TRABALHO = (
    "  DEVIA PASSAR na branch de trabalho — {}")
FALHA_BARROU_NA_INTEGRACAO = (
    "  DEVIA PASSAR na branch de integração não declarada — {}")
FALHA_SO_PEDE_E_BARROU = (
    "  DEVIA PASSAR sem autorização, porque só pede — {}")


NOME_DO_VIZINHO_SO_LEITURA = "vizinho-so-leitura"
NOME_DO_VIZINHO_LIBERADO = "vizinho-liberado"
FALHA_FALOU_NO_SO_LEITURA = (
    "  DEVIA CALAR no somente-leitura e falou — {}")
FALHA_BARROU_VIZINHO_LIBERADO = (
    "  DEVIA PASSAR no vizinho com autorizacao declarada e barrou — {}")
FALHA_PASSOU_VIZINHO_SEM_DECLARAR = (
    "  DEVIA BARRAR no vizinho sem autorizacao declarada e passou")


def _as_duas_recusas_se_distinguem(falhas):
    import json as _json
    import tempfile as _tempfile
    with _tempfile.TemporaryDirectory(prefix="vetar-vizinho-") as pasta:
        raiz = Path(pasta)
        (raiz / "nucleo").mkdir(parents=True, exist_ok=True)
        (raiz / ARQUIVO_EXECUTOR).write_text(_json.dumps({
            CHAVE_DOS_PROJETOS: {
                "a": {CHAVE_DO_REPOSITORIO: NOME_DO_VIZINHO_SO_LEITURA,
                      CHAVE_DO_SO_LEITURA: True},
                "b": {CHAVE_DO_REPOSITORIO: NOME_DO_VIZINHO_LIBERADO,
                      CHAVE_DAS_AUTORIZACOES_DO_VIZINHO: {"push": True,
                                                          "commit": True}},
                "c": {CHAVE_DO_REPOSITORIO: "vizinho-mudo"},
            }}), encoding="utf-8")

        so_leitura = raiz / "projetos" / NOME_DO_VIZINHO_SO_LEITURA
        liberado = raiz / "projetos" / NOME_DO_VIZINHO_LIBERADO
        mudo = raiz / "projetos" / "vizinho-mudo"
        for onde in (so_leitura, liberado, mudo):
            onde.mkdir(parents=True, exist_ok=True)

        if not e_somente_leitura(raiz, so_leitura):
            falhas.append(FALHA_FALOU_NO_SO_LEITURA.format("nao reconheceu"))
        if e_somente_leitura(raiz, liberado):
            falhas.append(FALHA_FALOU_NO_SO_LEITURA.format("falso positivo"))

        if not autorizacoes_do_alvo(raiz, liberado).get("push"):
            falhas.append(FALHA_BARROU_VIZINHO_LIBERADO.format("push"))
        if autorizacoes_do_alvo(raiz, mudo).get("push"):
            falhas.append(FALHA_PASSOU_VIZINHO_SEM_DECLARAR)


FALHA_JULGOU_PELA_BRANCH_ERRADA = (
    "[a branch julgada é a do repositório onde o comando roda] {}")
FALHA_INIT_ENCADEADO = "[init encadeado é julgado no berçário] {}"


def _o_init_encadeado_e_julgado_no_bercario(falhas):
    import subprocess as _subprocess
    import tempfile as _tempfile

    def _hook(projeto_dir, cwd, comando):
        entrada = json.dumps({"tool_input": {"command": comando},
                              "cwd": str(cwd)})
        r = _subprocess.run(
            [sys.executable, str(Path(__file__).resolve())],
            input=entrada, capture_output=True, text=True,
            env={**os.environ, VARIAVEL_DA_RAIZ_DO_PROJETO: str(projeto_dir)})
        return r.stdout

    par = "git init -q -b issue/1 . && git commit --allow-empty -m x"
    with _tempfile.TemporaryDirectory(prefix="vetar-init-encadeado-") as pasta:
        atlas_de_mentira = Path(pasta) / "atlas"
        bercario = atlas_de_mentira / "projetos" / "novo"
        bercario.mkdir(parents=True)
        _subprocess.run(["git", "-C", str(atlas_de_mentira), "init", "-q",
                         "-b", "issue/1", "."], check=True,
                        capture_output=True, text=True, encoding="utf-8", errors="replace")
        (atlas_de_mentira / "nucleo").mkdir()
        (atlas_de_mentira / ARQUIVO_CONFIGURACAO).write_text(json.dumps(
            {CHAVE_DAS_AUTORIZACOES: {"commit": True, "push": True}}),
            encoding="utf-8")
        if "deny" not in _hook(atlas_de_mentira, bercario, par):
            falhas.append(FALHA_INIT_ENCADEADO.format(
                "pasta sem declaração — o par devia ser negado e passou"))
        (atlas_de_mentira / ARQUIVO_EXECUTOR).write_text(json.dumps({
            CHAVE_DOS_PROJETOS: {"n": {CHAVE_DO_REPOSITORIO: "novo",
                                       CHAVE_DAS_AUTORIZACOES_DO_VIZINHO: {
                                           "commit": True}}}}),
            encoding="utf-8")
        if _hook(atlas_de_mentira, bercario, par).strip():
            falhas.append(FALHA_INIT_ENCADEADO.format(
                "vizinho declarado com commit — o par devia calar e negou"))


def _a_branch_julgada_e_a_do_alvo(falhas):
    import subprocess as _subprocess
    import tempfile as _tempfile

    def _git(onde, *args):
        _subprocess.run(["git", "-C", str(onde), *args], check=True,
                        capture_output=True, text=True, encoding="utf-8", errors="replace")

    def _hook(projeto_dir, cwd, comando):
        entrada = json.dumps({"tool_input": {"command": comando},
                              "cwd": str(cwd)})
        r = _subprocess.run(
            [sys.executable, str(Path(__file__).resolve())],
            input=entrada, capture_output=True, text=True,
            env={**os.environ, VARIAVEL_DA_RAIZ_DO_PROJETO: str(projeto_dir)})
        return r.stdout

    with _tempfile.TemporaryDirectory(prefix="vetar-branch-julgada-") as pasta:
        raiz = Path(pasta)
        atlas_de_mentira = raiz / "atlas"
        vizinho = raiz / "vizinho"
        for onde in (atlas_de_mentira, vizinho):
            onde.mkdir()
            _git(onde, "init", "-q", "-b", "issue/1", ".")
            _git(onde, "commit", "-q", "--allow-empty", "-m", "x")
        (atlas_de_mentira / "nucleo").mkdir()
        (atlas_de_mentira / ARQUIVO_EXECUTOR).write_text(json.dumps({
            CHAVE_DOS_PROJETOS: {"v": {CHAVE_DO_REPOSITORIO: "vizinho",
                                       CHAVE_DAS_AUTORIZACOES_DO_VIZINHO: {
                                           "push": True}}}}), encoding="utf-8")

        _git(vizinho, "checkout", "-q", "-b", "main")
        saida = _hook(atlas_de_mentira, vizinho, "git push --force")
        if "deny" not in saida:
            falhas.append(FALHA_JULGOU_PELA_BRANCH_ERRADA.format(
                "vizinho na main, atlas fora — devia negar e não negou"))
        if "main" not in saida:
            falhas.append(FALHA_JULGOU_PELA_BRANCH_ERRADA.format(
                "negou sem nomear a branch do vizinho"))

        _git(vizinho, "checkout", "-q", "-b", "issue/2")
        saida = _hook(atlas_de_mentira, vizinho, "git push --force")
        if saida.strip():
            falhas.append(FALHA_JULGOU_PELA_BRANCH_ERRADA.format(
                "vizinho fora da protegida — devia calar e negou"))

        (vizinho / ".claude").mkdir()
        (vizinho / ARQUIVO_DE_BRANCHES_PROTEGIDAS).write_text(
            "staging-do-vizinho\n", encoding="utf-8")
        _git(vizinho, "checkout", "-q", "-b", "staging-do-vizinho")
        saida = _hook(atlas_de_mentira, vizinho, "git push --force")
        if "deny" not in saida:
            falhas.append(FALHA_JULGOU_PELA_BRANCH_ERRADA.format(
                "vizinho declara sua própria branches-protegidas.txt — "
                "devia negar e não negou"))
        if "staging-do-vizinho" not in saida:
            falhas.append(FALHA_JULGOU_PELA_BRANCH_ERRADA.format(
                "negou sem nomear a branch declarada pelo vizinho"))


def _as_duas_recusas_ensinam(falhas):
    por_autorizacao = (RECUSA_POR_AUTORIZACAO.format("empurrar")
                       + MANDA_GRAVAR.format(APRENDIZADO_DA_AUTORIZACAO))
    por_branch = (RECUSA_POR_BRANCH_PROTEGIDA.format("apagar")
                  + MANDA_GRAVAR.format(APRENDIZADO_DA_BRANCH))
    if not ("Regra 9" in por_autorizacao
            and ARQUIVO_CONFIGURACAO in por_autorizacao
            and "regra 4" in por_autorizacao
            and "`conhecimento/`" in por_autorizacao):
        falhas.append(FALHA_RECUSA_NAO_ENSINA.format(
            "sem autorização declarada"))
    if not ("Regra 12" in por_branch
            and ARQUIVO_DE_BRANCHES_PROTEGIDAS in por_branch
            and "regra 4" in por_branch
            and "`conhecimento/`" in por_branch):
        falhas.append(FALHA_RECUSA_NAO_ENSINA.format("branch protegida"))


def testar() -> int:
    protegidas = set(PROTEGIDAS_EMBUTIDAS)
    raiz = Path.cwd()
    falhas = []
    fora = BRANCH_DE_TRABALHO_DO_TESTE
    for rotulo, comando in BARRA:
        if not motivo_da_recusa(comando, protegidas, raiz, AUTORIZA_TUDO, fora):
            falhas.append(FALHA_DEVIA_BARRAR.format(rotulo, comando))
    for rotulo, comando in DEIXA_PASSAR:
        motivo = motivo_da_recusa(comando, protegidas, raiz, AUTORIZA_TUDO, fora)
        if motivo:
            falhas.append(FALHA_DEVIA_PASSAR.format(rotulo, comando, motivo))
    for rotulo, comando in SO_PEDEM:
        if motivo_da_recusa(comando, protegidas, raiz, None, fora):
            falhas.append(FALHA_SO_PEDE_E_BARROU.format(rotulo))

    for rotulo, comando in BARRA_SEM_AUTORIZACAO:
        if not motivo_da_recusa(comando, protegidas, raiz, None, fora):
            falhas.append(FALHA_DEVIA_BARRAR_SEM_AUTORIZACAO.format(rotulo))
        if motivo_da_recusa(comando, protegidas, raiz, AUTORIZA_TUDO, fora):
            falhas.append(FALHA_DEVIA_PASSAR_COM_AUTORIZACAO.format(rotulo))
    if not motivo_da_recusa(FORCA_EM_PROTEGIDA, protegidas, raiz,
                            AUTORIZA_TUDO, fora):
        falhas.append(FALHA_FORCA_MESMO_AUTORIZADO)

    declaradas_do_merge = set(BRANCHES_POR_INCORPORACAO_DO_TESTE)
    sabidas = set(BRANCHES_CONHECIDAS_DO_TESTE)
    for rotulo, comando in SAI_DA_PROTEGIDA_ANTES_DE_GRAVAR:
        for onde in declaradas_do_merge:
            if motivo_da_recusa(comando, protegidas, raiz, AUTORIZA_TUDO,
                                onde, declaradas_do_merge, sabidas):
                falhas.append(
                    FALHA_SAIU_DA_PROTEGIDA_E_BARROU.format(rotulo))
    for rotulo, comando in ENTRA_NA_PROTEGIDA_E_GRAVA:
        if not motivo_da_recusa(comando, protegidas, raiz, AUTORIZA_TUDO,
                                "main", declaradas_do_merge, sabidas):
            falhas.append(
                FALHA_ENTROU_NA_PROTEGIDA_E_PASSOU.format(rotulo))
    for rotulo, comando in RESTAURA_ARQUIVO_E_NAO_TROCA_DE_BRANCH:
        if motivo_da_recusa(comando, protegidas, raiz, AUTORIZA_TUDO,
                            fora, declaradas_do_merge, sabidas):
            falhas.append(FALHA_RESTAURO_VIROU_TROCA.format(rotulo))
    if motivo_da_recusa("git checkout arquivo.txt && git commit -m x",
                        protegidas, raiz, AUTORIZA_TUDO, "main",
                        declaradas_do_merge, sabidas) is None:
        falhas.append(FALHA_ARQUIVO_VIROU_BRANCH)
    for rotulo, comando in GIT_MERGE_NAO_E_PUBLICAR:
        if motivo_da_recusa(comando, protegidas, raiz, AUTORIZA_TUDO,
                            fora, declaradas_do_merge):
            falhas.append(FALHA_MERGE_LOCAL_BARRADO.format(rotulo))
    for rotulo, comando in GIT_MERGE_EM_PROTEGIDA:
        for onde in declaradas_do_merge:
            if not motivo_da_recusa(comando, protegidas, raiz,
                                    AUTORIZA_TUDO, onde,
                                    declaradas_do_merge):
                falhas.append(
                    FALHA_MERGE_EM_PROTEGIDA_PASSOU.format(rotulo))
    for rotulo, comando in GH_MERGE_CONTINUA_SENDO_PUBLICAR:
        if not motivo_da_recusa(comando, protegidas, raiz, None, fora):
            falhas.append(FALHA_GH_MERGE_PASSOU.format(rotulo))

    declaradas = set(BRANCHES_POR_INCORPORACAO_DO_TESTE)
    for rotulo, comando in GRAVA_EM_PROTEGIDA:
        for onde in declaradas:
            if not motivo_da_recusa(comando, protegidas, raiz,
                                    AUTORIZA_TUDO, onde, declaradas):
                falhas.append(FALHA_GRAVOU_EM_PROTEGIDA.format(rotulo, onde))
        if motivo_da_recusa(comando, protegidas, raiz, AUTORIZA_TUDO, fora,
                            declaradas):
            falhas.append(FALHA_BARROU_NA_DE_TRABALHO.format(rotulo))
        if motivo_da_recusa(comando, protegidas, raiz, AUTORIZA_TUDO,
                            BRANCH_DE_INTEGRACAO_DO_TESTE, declaradas):
            falhas.append(FALHA_BARROU_NA_INTEGRACAO.format(rotulo))

    _as_duas_recusas_se_distinguem(falhas)
    _as_duas_recusas_ensinam(falhas)
    _a_branch_julgada_e_a_do_alvo(falhas)
    _o_init_encadeado_e_julgado_no_bercario(falhas)

    total = (6 + len(GRAVA_EM_PROTEGIDA)
             * (len(BRANCHES_POR_INCORPORACAO_DO_TESTE) + 2)
             + len(SO_PEDEM) + len(BARRA) + len(DEIXA_PASSAR)
             + len(BARRA_SEM_AUTORIZACAO) * 2 + 1
             + len(GIT_MERGE_NAO_E_PUBLICAR)
             + len(GIT_MERGE_EM_PROTEGIDA)
             * len(BRANCHES_POR_INCORPORACAO_DO_TESTE)
             + len(GH_MERGE_CONTINUA_SENDO_PUBLICAR)) + 7
    if falhas:
        print(RESUMO_FALHOU.format(len(falhas), total))
        print("\n".join(falhas))
        return 1
    print(RESUMO_OK.format(total, len(BARRA), len(DEIXA_PASSAR)))
    return 0


def main() -> int:
    try:
        return decidir()
    except Exception as falha:
        return recusa_por_nao_entender(falha)


if __name__ == "__main__":
    sys.exit(testar() if BANDEIRA_DE_TESTE in sys.argv else main())
