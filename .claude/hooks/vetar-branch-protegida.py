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
MARCA_DE_COMENTARIO = "#"
PASTA_DO_GIT = ".git"

VARIAVEL_DA_RAIZ_DO_PROJETO = "CLAUDE_PROJECT_DIR"
NIVEIS_DO_GANCHO_ATE_A_RAIZ = 2

BANDEIRAS_GLOBAIS_SIMPLES = {"--no-pager", "--paginate", "-p", "--bare",
                             "--literal-pathspecs"}
BANDEIRAS_GLOBAIS_QUE_COMEM_O_TOKEN_SEGUINTE = {
    "-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}

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

NOMES_DO_GIT = {"git", "git.exe"}
NOME_DO_GH = "gh"
EXTENSAO_EXE = ".exe"
PROGRAMAS_QUE_ACIONAM = ("git", "gh")
COMANDO_CD = "cd"
COMANDO_DA_BRANCH_ATUAL = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
TEMPO_LIMITE_DO_GIT = 5
HEAD_SOLTA = "head"
PREFIXO_DE_REFS_DE_BRANCH = re.compile(r"^refs/heads/")

VERBOS_POR_ACAO = {
    "commit": ("commit",),
    "push": ("push",),
    "publicar": ("pr", "release", "merge"),
}
OMISSAO_NAO_E_PERMISSAO = {"commit": False, "push": False, "publicar": False}

MARCA_DO_GIT = "git"
MARCA_DO_GH = "gh "
EVENTO_ANTES_DA_FERRAMENTA = "PreToolUse"
DECISAO_DE_NEGAR = "deny"
BANDEIRA_DE_TESTE = "--testar"
SEM_ACAO = ""
SEM_RECUSA = ""
SILENCIO = 0
FALHA_ABERTO = 0

MOTIVO_BRANCH_PROTEGIDA = "{} a branch protegida '{}'"
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


def verbo_e_resto(tokens: list):
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
        return t.lower(), tokens[i + 1:]
    return None, []


def branch_atual(raiz: Path):
    try:
        r = subprocess.run(COMANDO_DA_BRANCH_ATUAL, cwd=raiz,
                           capture_output=True, text=True,
                           timeout=TEMPO_LIMITE_DO_GIT)
    except (OSError, subprocess.SubprocessError):
        return None
    nome = r.stdout.strip().lower()
    return nome if r.returncode == 0 and nome and nome != HEAD_SOLTA else None


def cd_que_abre_o_comando(comando: str) -> str:
    segmentos = separar(comando)
    primeiro = segmentos[0].strip() if segmentos else ""
    tokens = partir_em_tokens(primeiro)
    if len(tokens) >= 2 and Path(tokens[0]).name == COMANDO_CD:
        return tokens[1]
    return ""


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
    argumentos = [t for t in tokens[1:] if not t.startswith("-")]
    if not argumentos:
        return SEM_ACAO
    for acao, verbos in VERBOS_POR_ACAO.items():
        if argumentos[0].lower() in verbos:
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
                         atingidas: list, protegidas: set, raiz: Path) -> str:
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
        atual = branch_atual(raiz)
        if atual in protegidas:
            return MOTIVO_REESCREVER_A_BRANCH_ATUAL.format(atual)
    return SEM_RECUSA


def motivo_da_recusa(comando: str, protegidas: set, raiz: Path,
                     permitido: dict = None):
    permitido = OMISSAO_NAO_E_PERMISSAO if permitido is None else permitido
    recusa_por_autorizacao_pendente = SEM_RECUSA
    for segmento in separar(comando):
        tokens = partir_em_tokens(segmento.strip())
        if not tokens or not (e_git(tokens[0]) or e_gh(tokens[0])):
            continue

        acao = acao_do_comando(tokens)
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
                                       protegidas, raiz))
        if recusa:
            return recusa
    return recusa_por_autorizacao_pendente or None


def raiz_do_projeto_nunca_o_cwd() -> Path:
    declarada = os.environ.get(VARIAVEL_DA_RAIZ_DO_PROJETO)
    if declarada:
        return Path(declarada)
    return Path(__file__).resolve().parents[NIVEIS_DO_GANCHO_ATE_A_RAIZ]


def main() -> int:
    try:
        entrada = json.load(sys.stdin)
        comando = entrada.get("tool_input", {}).get("command", "")
        onde = entrada.get("cwd") or ""
    except (json.JSONDecodeError, AttributeError, TypeError):
        return FALHA_ABERTO

    baixo = (comando or "").lower()
    nada_de_git_nem_de_gh = (MARCA_DO_GIT not in baixo
                             and MARCA_DO_GH not in baixo)
    if not comando or nada_de_git_nem_de_gh:
        return SILENCIO

    raiz = raiz_do_projeto_nunca_o_cwd()
    motivo = motivo_da_recusa(
        comando, nomes_protegidos(raiz), raiz,
        autorizacoes(repositorio_que_o_comando_muda(onde, raiz, comando)))
    if not motivo:
        return SILENCIO

    e_recusa_por_autorizacao = MARCA_DA_RECUSA_POR_AUTORIZACAO in motivo
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": EVENTO_ANTES_DA_FERRAMENTA,
        "permissionDecision": DECISAO_DE_NEGAR,
        "permissionDecisionReason": (
            RECUSA_POR_AUTORIZACAO.format(motivo) if e_recusa_por_autorizacao
            else RECUSA_POR_BRANCH_PROTEGIDA.format(motivo)),
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

BARRA_SEM_AUTORIZACAO = [
    ("commit sem autorização", "git commit -m x"),
    ("push sem autorização", "git push origin feature/minha"),
    ("abrir PR sem autorização", "gh pr create --fill"),
    ("mesclar PR sem autorização", "gh pr merge 1 --merge"),
    ("publicar release sem autorização", "gh release create v1"),
]

AUTORIZA_TUDO = {"commit": True, "push": True, "publicar": True}
FORCA_EM_PROTEGIDA = "git push --force origin main"


def testar() -> int:
    protegidas = set(PROTEGIDAS_EMBUTIDAS)
    raiz = Path.cwd()
    falhas = []
    for rotulo, comando in BARRA:
        if not motivo_da_recusa(comando, protegidas, raiz, AUTORIZA_TUDO):
            falhas.append(FALHA_DEVIA_BARRAR.format(rotulo, comando))
    for rotulo, comando in DEIXA_PASSAR:
        motivo = motivo_da_recusa(comando, protegidas, raiz, AUTORIZA_TUDO)
        if motivo:
            falhas.append(FALHA_DEVIA_PASSAR.format(rotulo, comando, motivo))
    for rotulo, comando in BARRA_SEM_AUTORIZACAO:
        if not motivo_da_recusa(comando, protegidas, raiz):
            falhas.append(FALHA_DEVIA_BARRAR_SEM_AUTORIZACAO.format(rotulo))
        if motivo_da_recusa(comando, protegidas, raiz, AUTORIZA_TUDO):
            falhas.append(FALHA_DEVIA_PASSAR_COM_AUTORIZACAO.format(rotulo))
    if not motivo_da_recusa(FORCA_EM_PROTEGIDA, protegidas, raiz,
                            AUTORIZA_TUDO):
        falhas.append(FALHA_FORCA_MESMO_AUTORIZADO)

    total = (len(BARRA) + len(DEIXA_PASSAR)
             + len(BARRA_SEM_AUTORIZACAO) * 2 + 1)
    if falhas:
        print(RESUMO_FALHOU.format(len(falhas), total))
        print("\n".join(falhas))
        return 1
    print(RESUMO_OK.format(total, len(BARRA), len(DEIXA_PASSAR)))
    return 0


if __name__ == "__main__":
    sys.exit(testar() if BANDEIRA_DE_TESTE in sys.argv else main())
