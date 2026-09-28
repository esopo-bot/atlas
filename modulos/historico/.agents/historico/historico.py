import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

for _acima in Path(__file__).resolve().parents:
    if (_acima / ".agents" / "gh" / "gh.py").is_file():
        sys.path.insert(0, str(_acima / ".agents" / "gh"))
        break
import gh

BANDEIRA_DE_TESTE = "--testar"
USO = ("destila o corpo final de cada issue fechada num histórico local, por "
       "projeto, em conhecimento/issues_encerradas/<projeto>/"
       "<numero>-<assunto>.md, sempre na árvore principal — gravado numa "
       "worktree, ele sumiria com ela. Vale só daqui para frente: o marco é o "
       "commit que trouxe o instrumento ao checkout, ou a primeira vez que "
       "ele roda quando não há commit, e o .desde escrito vence os dois. "
       "Confere o texto por forma de "
       "segredo antes de gravar e recusa sem mostrar o valor, e só grava onde "
       "o git ignora. Depois de gravar, pede a ronda do índice")

ARQUIVO_DO_EXECUTOR = "nucleo/executor.json"
PASTA_DO_HISTORICO = "conhecimento/issues_encerradas"
ARQUIVO_DO_MARCO = ".desde"
PASTA_SEM_PROJETO = "sem-projeto"
INDEXADOR = ".agents/indice/indexar.py"
BANDEIRA_DA_RONDA = "--ronda"
TETO_DO_ASSUNTO = 60
TETO_DE_COMMITS = 30
TETO_DA_LISTA = 100
TEMPO_DO_GIT = 30
TEMPO_DA_RONDA = 900
SAIDA_LIMPA = 0
SAIDA_COM_ACHADO = 1
SAIDA_NAO_MEDIDA = 2

PREFIXO_DO_TITULO = re.compile(r"^\s*\S+\s+-\s+")
FORA_DO_ASSUNTO = re.compile(r"[^a-z0-9]+")
NOME_DE_PASTA_QUE_SERVE = re.compile(r"^[A-Za-z0-9_.-]+$")
TITULO_DE_SECAO = re.compile(r"^#{1,3}\s+(.+?)\s*$")
LINHA_DE_CRITERIO = re.compile(r"^\s*[-*]\s+\[( |x|X)\]\s+")
ENDERECO_DO_REPOSITORIO = re.compile(r"^([^/\s]+)/([^/\s]+)$")

FORMAS_DE_SEGREDO = (
    ("chave de API", re.compile(r"sk-[A-Za-z0-9_\-]{16,}")),
    ("token do GitHub",
     re.compile(r"(?:gh[pousr]|github_pat)_[A-Za-z0-9_]{20,}")),
    ("chave da AWS", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("chave privada", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("token JWT",
     re.compile(r"eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.")),
    ("token do Slack", re.compile(r"xox[baprs]-[A-Za-z0-9\-]{10,}")),
    ("senha ou token escrito por extenso",
     re.compile(r"(?i)\b(?:senha|password|passwd|secret|segredo|token)\b"
                r"\s*[:=]\s*(?!\$\{)[^\s`'\"]{6,}")),
    ("endereço de e-mail",
     re.compile(r"[A-Za-z0-9._%+\-]+@(?!users\.noreply\.github\.com)"
                r"[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")),
)

MOTIVO_DO_FECHAMENTO = {"COMPLETED": "concluída", "NOT_PLANNED": "descartada",
                        "DUPLICATE": "duplicada", "REOPENED": "reaberta"}
SECOES_DO_PEDIDO = ("objetivo", "o pedido, como veio")
SECAO_DO_ESTADO = "estado"
PEDACO_DA_SECAO_DE_DECISAO = "decis"
PEDACO_DA_SECAO_DE_ONDE_MORA = "onde mora"

CONSULTA_DA_ISSUE = (
    "query($dono: String!, $nome: String!, $numero: Int!) { "
    "repository(owner: $dono, name: $nome) { issue(number: $numero) { "
    "number title body url stateReason closedAt "
    "labels(first: 30) { nodes { name } } "
    "closedByPullRequestsReferences(first: 10, includeClosedPrs: true) { "
    "nodes { number title url mergedAt } } } } }")

MOLDE_DO_HISTORICO = """# {numero} — {titulo}

- **Projeto:** `{projeto}`
- **Fechada em:** {quando}, {motivo}
- **Issue:** {url}
- **Fechada por:** {fechada_por}
- **Commits com a marca `(issue {numero})`:** {quantos_commits}

## O que foi pedido

{pedido}

## Os critérios, como estavam no fechamento

{criterios}

{em_branco}

## Decisões

{decisoes}

## O estado no fechamento

{estado}

## Onde mora o que se aprendeu

{onde_mora}

## Os commits

{commits}
"""
FECHADA_A_MAO = "à mão, sem pedido de incorporação que a feche"
LINHA_DO_PEDIDO_QUE_FECHOU = "{url} — {titulo}{mesclado}"
MESCLADO_EM = ", mesclado em {}"
LINHA_DO_COMMIT = "- `{hash}` {assunto}"
SEM_SECAO = "_O corpo final não tinha esta seção._"
SEM_CRITERIO = "_O corpo final não tinha critério marcável._"
SEM_COMMIT = "_Nenhum commit traz a marca desta issue._"
NENHUM_EM_BRANCO = "Nenhum critério em branco no fechamento."
COM_CRITERIO_EM_BRANCO = (
    "**Em branco no fechamento: {quantos}.** A issue fechou com critério sem "
    "marca, e o histórico não a dá por pronta: o fechamento não lê os "
    "critérios.")
SEM_ONDE_MORA = (
    "_O corpo final não declarou onde mora o que se aprendeu: credencial, "
    "conta de teste, fato do vizinho e lição genérica ficaram sem ponteiro._")

RECUSA_SEM_CONFIGURACAO = (
    "não medido: não li {arquivo} ({motivo}) — é dele que saem o repositório "
    "das issues e os projetos")
RECUSA_SEM_REPOSITORIO = (
    "não medido: {arquivo} não declara `issues.repositorio` no formato "
    "dono/nome, e sem ele não sei onde as issues fecham")
FALHA_AO_LISTAR = "não medido: não listei as issues fechadas — {motivo}"
FALHA_AO_LER_A_ISSUE = "não li a issue {numero} — {motivo}"
RECUSA_ANTES_DO_MARCO = (
    "a issue {numero} fechou em {quando}, antes do marco {marco}: o histórico "
    "vale só daqui para frente, e ela não se colhe")
RECUSA_ABERTA = "a issue {numero} não está fechada: não há o que colher"
RECUSA_SEGREDO = (
    "não gravei o histórico da issue {numero}: o texto tem forma de "
    "segredo — {achados}. O valor não aparece aqui de propósito. Tire-o do "
    "corpo da issue: o valor vai para .credenciais/acessos/, a conta ganha "
    "uma linha sem valor no .credenciais/INVENTARIO.md, e o corpo guarda só "
    "o ponteiro. Depois rode de novo")
ACHADO_DE_SEGREDO = "linha {linha}: {forma}"
RECUSA_FORA_DO_IGNORE = (
    "não gravei o histórico da issue {numero}: o git NÃO ignora {alvo}, e "
    "o que está rastreado sobe para o espelho. Declare a pasta fora do git "
    "antes — no .gitignore da raiz, ou com o .gitignore que o módulo "
    "instala dentro dela")
RECUSA_PASTA_FORA_DO_IGNORE = (
    "não medido: o git NÃO ignora {alvo}/, e nem o marco se grava ali — o "
    "que está rastreado sobe para o espelho. Declare a pasta fora do git "
    "antes: no .gitignore da raiz, ou com o .gitignore que o módulo instala "
    "dentro dela")
RECADO_GRAVADO = "histórico gravado: {caminho} (na árvore principal, {raiz})"
RECADO_DO_ENSAIO = "ENSAIO — o histórico de {caminho} seria:\n\n{texto}"
RECADO_SEM_PENDENTE = "nenhuma issue fechada sem histórico desde {marco}"
RECADO_PENDENTES = (
    "{quantas} issue(s) fechada(s) sem histórico desde {marco}: {lista} — "
    "rode `python .agents/historico/historico.py --colher`")
RECADO_MARCO_NOVO = ("marco do histórico posto agora, {marco}: as issues "
                     "fechadas antes dele não se colhem")
RECADO_MARCO_DA_CHEGADA = (
    "marco do histórico posto em {marco}, a data do commit que trouxe o "
    "instrumento a este checkout: as issues fechadas antes dele não se colhem")
RECADO_RONDA = "índice: {ultima}"
RECADO_RONDA_FALHOU = "índice: a ronda não rodou ({motivo}) — rode {comando}"
RECADO_SEM_INDICE = "índice: o módulo não está instalado, e nada se reindexou"


def agora_em_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def instante(texto: str):
    try:
        return datetime.fromisoformat((texto or "").replace("Z", "+00:00"))
    except ValueError:
        return None


def rodar_git(pasta: Path, *argumentos) -> tuple:
    try:
        feito = subprocess.run(["git", "-C", str(pasta), *argumentos],
                               capture_output=True, text=True,
                               encoding="utf-8", errors="replace",
                               timeout=TEMPO_DO_GIT)
    except (OSError, subprocess.SubprocessError) as falha:
        return None, f"{type(falha).__name__}: {falha}"
    return feito.returncode, feito.stdout.strip()


def arvore_principal(cwd: Path) -> Path:
    codigo, comum = rodar_git(cwd, "rev-parse", "--path-format=absolute",
                              "--git-common-dir")
    if codigo != 0 or not comum:
        return Path(cwd).resolve()
    pasta = Path(comum)
    return pasta.parent.resolve() if pasta.name == ".git" \
        else Path(cwd).resolve()


def configuracao(principal: Path, cwd: Path) -> tuple:
    ultimo_motivo = "o arquivo não existe"
    for raiz in (principal, cwd):
        alvo = Path(raiz) / ARQUIVO_DO_EXECUTOR
        try:
            return json.loads(alvo.read_text(encoding="utf-8")), ""
        except OSError as falha:
            ultimo_motivo = f"{type(falha).__name__}"
        except ValueError as falha:
            return None, RECUSA_SEM_CONFIGURACAO.format(
                arquivo=ARQUIVO_DO_EXECUTOR, motivo=falha)
    return None, RECUSA_SEM_CONFIGURACAO.format(arquivo=ARQUIVO_DO_EXECUTOR,
                                                motivo=ultimo_motivo)


def endereco_das_issues(dado: dict) -> tuple:
    issues = dado.get("issues") if isinstance(dado, dict) else None
    issues = issues if isinstance(issues, dict) else {}
    repositorio = issues.get("repositorio")
    if not isinstance(repositorio, str) or "${" in repositorio \
            or not ENDERECO_DO_REPOSITORIO.match(repositorio.strip()):
        return None, RECUSA_SEM_REPOSITORIO.format(
            arquivo=ARQUIVO_DO_EXECUTOR)
    conta = issues.get("conta_gh") if isinstance(issues.get("conta_gh"),
                                                 str) else ""
    return {"repositorio": repositorio.strip(), "conta": conta}, ""


def projetos_cadastrados(dado: dict) -> list:
    projetos = dado.get("projetos") if isinstance(dado, dict) else None
    if not isinstance(projetos, dict):
        return []
    return [nome for nome, valor in projetos.items() if isinstance(valor, dict)]


def projeto_da_issue(etiquetas: list, cadastrados: list) -> str:
    postas = set(etiquetas)
    for nome in cadastrados:
        if nome in postas and NOME_DE_PASTA_QUE_SERVE.match(nome):
            return nome
    return PASTA_SEM_PROJETO


def assunto_do_titulo(titulo: str) -> str:
    sem_prefixo = PREFIXO_DO_TITULO.sub("", titulo or "", count=1)
    decomposto = unicodedata.normalize("NFKD", sem_prefixo.lower())
    sem_acento = "".join(c for c in decomposto
                         if not unicodedata.combining(c))
    kebab = FORA_DO_ASSUNTO.sub("-", sem_acento).strip("-")
    if len(kebab) > TETO_DO_ASSUNTO:
        kebab = kebab[:TETO_DO_ASSUNTO].rsplit("-", 1)[0]
    return kebab or "sem-assunto"


def nome_do_arquivo(numero: int, titulo: str) -> str:
    return f"{numero}-{assunto_do_titulo(titulo)}.md"


def secoes_do_corpo(corpo: str) -> list:
    secoes, titulo, linhas = [], "", []
    for linha in (corpo or "").replace("\r", "").split("\n"):
        achado = TITULO_DE_SECAO.match(linha)
        if achado:
            if titulo or any(l.strip() for l in linhas):
                secoes.append((titulo, "\n".join(linhas).strip()))
            titulo, linhas = achado.group(1), []
        else:
            linhas.append(linha)
    if titulo or any(l.strip() for l in linhas):
        secoes.append((titulo, "\n".join(linhas).strip()))
    return secoes


def secoes_que(secoes: list, casa) -> str:
    achadas = [texto for titulo, texto in secoes
               if casa(titulo.lower()) and texto]
    return "\n\n".join(achadas)


def criterios_do_corpo(corpo: str) -> list:
    return [linha.strip() for linha in (corpo or "").replace("\r", "")
            .split("\n") if LINHA_DE_CRITERIO.match(linha)]


def em_branco(criterios: list) -> list:
    return [linha for linha in criterios
            if LINHA_DE_CRITERIO.match(linha).group(1) == " "]


def commits_da_issue(principal: Path, numero: int) -> list:
    codigo, saida = rodar_git(principal, "log", "--all", "-F",
                              f"--grep=(issue {numero})",
                              "--format=%h%x09%s", f"-n{TETO_DE_COMMITS}")
    if codigo != 0 or not saida:
        return []
    return [tuple(linha.split("\t", 1)) for linha in saida.splitlines()
            if "\t" in linha]


def fechada_por(issue: dict) -> str:
    pedidos = ((issue.get("closedByPullRequestsReferences") or {})
               .get("nodes") or [])
    if not pedidos:
        return FECHADA_A_MAO
    return "; ".join(LINHA_DO_PEDIDO_QUE_FECHOU.format(
        url=pedido.get("url", ""), titulo=pedido.get("title", ""),
        mesclado=(MESCLADO_EM.format(pedido["mergedAt"][:10])
                  if pedido.get("mergedAt") else ""))
        for pedido in pedidos)


def historico_da_issue(issue: dict, projeto: str, commits: list) -> str:
    corpo = issue.get("body") or ""
    secoes = secoes_do_corpo(corpo)
    criterios = criterios_do_corpo(corpo)
    brancos = em_branco(criterios)
    return MOLDE_DO_HISTORICO.format(
        numero=issue.get("number"), titulo=issue.get("title", ""),
        projeto=projeto, quando=(issue.get("closedAt") or "")[:10],
        motivo=MOTIVO_DO_FECHAMENTO.get(issue.get("stateReason") or "",
                                        issue.get("stateReason") or "?"),
        url=issue.get("url", ""), fechada_por=fechada_por(issue),
        quantos_commits=len(commits),
        pedido=secoes_que(secoes, lambda t: t.startswith(SECOES_DO_PEDIDO))
        or SEM_SECAO,
        criterios="\n".join(criterios) or SEM_CRITERIO,
        em_branco=(COM_CRITERIO_EM_BRANCO.format(quantos=len(brancos))
                   if brancos else NENHUM_EM_BRANCO),
        decisoes=secoes_que(secoes, lambda t: PEDACO_DA_SECAO_DE_DECISAO in t)
        or SEM_SECAO,
        estado=secoes_que(secoes, lambda t: t == SECAO_DO_ESTADO) or SEM_SECAO,
        onde_mora=secoes_que(
            secoes, lambda t: t.startswith(PEDACO_DA_SECAO_DE_ONDE_MORA))
        or SEM_ONDE_MORA,
        commits="\n".join(LINHA_DO_COMMIT.format(hash=h, assunto=a)
                          for h, a in commits) or SEM_COMMIT)


def formas_de_segredo(texto: str) -> list:
    achados = []
    for numero, linha in enumerate(texto.split("\n"), start=1):
        for forma, padrao in FORMAS_DE_SEGREDO:
            if padrao.search(linha):
                achados.append(ACHADO_DE_SEGREDO.format(linha=numero,
                                                        forma=forma))
    return achados


def pasta_do_historico(principal: Path) -> Path:
    return Path(principal) / PASTA_DO_HISTORICO


def chegada_do_instrumento(instrumento: Path, principal: Path):
    pasta = Path(instrumento).resolve().parent
    if arvore_principal(pasta) != Path(principal).resolve():
        return None
    codigo, saida = rodar_git(pasta, "log", "--diff-filter=A", "--format=%cI",
                              "--", Path(instrumento).name)
    datas = [instante(linha) for linha in saida.splitlines()] \
        if codigo == 0 else []
    datas = [data for data in datas if data is not None]
    return min(datas).astimezone(timezone.utc) if datas else None


def marco_do_historico(principal: Path, agora: datetime,
                       instrumento: Path) -> tuple:
    arquivo = pasta_do_historico(principal) / ARQUIVO_DO_MARCO
    try:
        lido = instante(arquivo.read_text(encoding="utf-8").strip())
    except OSError:
        lido = None
    if lido is not None:
        return lido, ""
    chegada = chegada_do_instrumento(instrumento, principal)
    marco = chegada or agora
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_text(marco.isoformat() + "\n", encoding="utf-8")
    molde = RECADO_MARCO_DA_CHEGADA if chegada else RECADO_MARCO_NOVO
    return marco, molde.format(marco=marco.isoformat())


def numeros_com_historico(principal: Path) -> set:
    pasta = pasta_do_historico(principal)
    numeros = set()
    for arquivo in pasta.glob("*/*.md") if pasta.is_dir() else []:
        cabeca = arquivo.name.split("-", 1)[0]
        if cabeca.isdigit():
            numeros.add(int(cabeca))
    return numeros


def fechadas_desde(endereco: dict, marco: datetime) -> tuple:
    feito = gh.na_conta(endereco["conta"], [
        "issue", "list", "--repo", endereco["repositorio"], "--state",
        "closed", "--search", f"closed:>={marco.date().isoformat()}",
        "--limit", str(TETO_DA_LISTA), "--json", "number,closedAt"])
    if feito is None or feito.returncode != 0:
        return None, FALHA_AO_LISTAR.format(motivo=gh.berro(feito))
    try:
        lidas = json.loads(feito.stdout or "[]")
    except ValueError as falha:
        return None, FALHA_AO_LISTAR.format(motivo=falha)
    fechadas = []
    for issue in lidas if isinstance(lidas, list) else []:
        quando = instante(issue.get("closedAt"))
        if isinstance(issue.get("number"), int) and quando is not None \
                and quando >= marco:
            fechadas.append(issue["number"])
    return sorted(fechadas), ""


def ler_a_issue(endereco: dict, numero: int) -> tuple:
    dono, nome = endereco["repositorio"].split("/", 1)
    feito = gh.na_conta(endereco["conta"], [
        "api", "graphql", "-f", f"query={CONSULTA_DA_ISSUE}",
        "-f", f"dono={dono}", "-f", f"nome={nome}", "-F", f"numero={numero}"])
    if feito is None or feito.returncode != 0:
        return None, FALHA_AO_LER_A_ISSUE.format(numero=numero,
                                                 motivo=gh.berro(feito))
    try:
        issue = json.loads(feito.stdout)["data"]["repository"]["issue"]
    except (ValueError, KeyError, TypeError) as falha:
        return None, FALHA_AO_LER_A_ISSUE.format(numero=numero, motivo=falha)
    if not isinstance(issue, dict):
        return None, FALHA_AO_LER_A_ISSUE.format(
            numero=numero, motivo="o rastreador não devolveu a issue")
    return issue, ""


def git_ignora(principal: Path, alvo: Path) -> bool:
    codigo, _ = rodar_git(principal, "check-ignore", "-q",
                          str(alvo.relative_to(principal).as_posix()))
    if codigo == 0:
        return True
    return codigo not in (1,) and not (principal / ".git").exists()


def pedir_a_ronda(principal: Path) -> str:
    indexador = Path(principal) / INDEXADOR
    if not indexador.is_file():
        return RECADO_SEM_INDICE
    comando = [sys.executable, str(indexador), BANDEIRA_DA_RONDA, "--cwd",
               str(principal)]
    try:
        feito = subprocess.run(comando, capture_output=True, text=True,
                               encoding="utf-8", errors="replace",
                               timeout=TEMPO_DA_RONDA, cwd=str(principal))
    except (OSError, subprocess.SubprocessError) as falha:
        return RECADO_RONDA_FALHOU.format(motivo=type(falha).__name__,
                                          comando=" ".join(comando[1:]))
    linhas = [l for l in (feito.stdout + feito.stderr).splitlines()
              if l.strip()]
    if feito.returncode != 0:
        return RECADO_RONDA_FALHOU.format(
            motivo=(linhas[-1] if linhas else feito.returncode),
            comando=" ".join(comando[1:]))
    return RECADO_RONDA.format(ultima=linhas[-1] if linhas else "sem saída")


def colher_uma(principal: Path, endereco: dict, cadastrados: list,
               numero: int, marco: datetime, ensaio: bool) -> tuple:
    issue, erro = ler_a_issue(endereco, numero)
    if erro:
        return False, erro
    fechou = instante(issue.get("closedAt"))
    if fechou is None:
        return False, RECUSA_ABERTA.format(numero=numero)
    if fechou < marco:
        return False, RECUSA_ANTES_DO_MARCO.format(
            numero=numero, quando=fechou.isoformat(), marco=marco.isoformat())
    etiquetas = [no.get("name") for no in
                 (issue.get("labels") or {}).get("nodes") or []]
    projeto = projeto_da_issue(etiquetas, cadastrados)
    texto = historico_da_issue(issue, projeto,
                               commits_da_issue(principal, numero))
    achados = formas_de_segredo(texto)
    if achados:
        return False, RECUSA_SEGREDO.format(numero=numero,
                                            achados="; ".join(achados))
    alvo = (pasta_do_historico(principal) / projeto
            / nome_do_arquivo(numero, issue.get("title", "")))
    relativo = alvo.relative_to(principal).as_posix()
    if ensaio:
        return True, RECADO_DO_ENSAIO.format(caminho=relativo, texto=texto)
    if not git_ignora(principal, alvo):
        return False, RECUSA_FORA_DO_IGNORE.format(numero=numero,
                                                   alvo=relativo)
    alvo.parent.mkdir(parents=True, exist_ok=True)
    alvo.write_text(texto, encoding="utf-8")
    return True, RECADO_GRAVADO.format(caminho=relativo, raiz=principal)


def preparar(cwd: str, agora: datetime, instrumento: Path = None) -> tuple:
    principal = arvore_principal(Path(cwd or "."))
    dado, erro = configuracao(principal, Path(cwd or "."))
    if erro:
        return None, erro
    endereco, erro = endereco_das_issues(dado)
    if erro:
        return None, erro
    arquivo_do_marco = pasta_do_historico(principal) / ARQUIVO_DO_MARCO
    if not git_ignora(principal, arquivo_do_marco):
        return None, RECUSA_PASTA_FORA_DO_IGNORE.format(
            alvo=arquivo_do_marco.parent.relative_to(principal).as_posix())
    marco, recado_do_marco_novo = marco_do_historico(
        principal, agora, Path(instrumento or __file__))
    return {"principal": principal, "endereco": endereco, "marco": marco,
            "recado_do_marco_novo": recado_do_marco_novo,
            "cadastrados": projetos_cadastrados(dado)}, ""


def pendentes(cwd: str = "", agora: datetime = None,
              instrumento: Path = None) -> tuple:
    contexto, erro = preparar(cwd, agora or agora_em_utc(), instrumento)
    if erro:
        return SAIDA_NAO_MEDIDA, erro
    fechadas, erro = fechadas_desde(contexto["endereco"], contexto["marco"])
    if erro:
        return SAIDA_NAO_MEDIDA, erro
    faltam = [n for n in fechadas
              if n not in numeros_com_historico(contexto["principal"])]
    marco = contexto["marco"].isoformat()
    if not faltam:
        return SAIDA_LIMPA, (contexto["recado_do_marco_novo"]
                             or RECADO_SEM_PENDENTE.format(marco=marco))
    return SAIDA_COM_ACHADO, RECADO_PENDENTES.format(
        quantas=len(faltam), marco=marco,
        lista=", ".join(f"#{n}" for n in faltam))


def colher(numeros=(), cwd: str = "", ensaio: bool = False,
           agora: datetime = None, reindexar: bool = True,
           instrumento: Path = None) -> tuple:
    contexto, erro = preparar(cwd, agora or agora_em_utc(), instrumento)
    if erro:
        return SAIDA_NAO_MEDIDA, [erro]
    alvos = [int(n) for n in numeros or []]
    if not alvos:
        fechadas, erro = fechadas_desde(contexto["endereco"],
                                        contexto["marco"])
        if erro:
            return SAIDA_NAO_MEDIDA, [erro]
        ja = numeros_com_historico(contexto["principal"])
        alvos = [n for n in fechadas if n not in ja]
    if not alvos:
        pasta = pasta_do_historico(contexto["principal"])
        arquivo = pasta / "LEIAME.md"
        if git_ignora(contexto["principal"], arquivo) and not arquivo.exists():
            pasta.mkdir(parents=True, exist_ok=True)
            arquivo.write_text(
                "Aqui moram os históricos das issues encerradas, por projeto.\n",
                encoding="utf-8")
        return SAIDA_LIMPA, [RECADO_SEM_PENDENTE.format(
            marco=contexto["marco"].isoformat())]
    recados, gravou, falhou = [], False, False
    for numero in alvos:
        certo, recado = colher_uma(contexto["principal"], contexto["endereco"],
                                   contexto["cadastrados"], numero,
                                   contexto["marco"], ensaio)
        recados.append(recado)
        gravou = gravou or (certo and not ensaio)
        falhou = falhou or not certo
    if gravou and reindexar:
        recados.append(pedir_a_ronda(contexto["principal"]))
    return (SAIDA_NAO_MEDIDA if falhou else SAIDA_LIMPA), recados


GH_DE_MENTIRA = """import json
import os
import pathlib
import sys

CAIXA = pathlib.Path(os.environ["HISTORICO_TESTE_CAIXA"])
sys.stdout.reconfigure(encoding="utf-8")
argv = sys.argv[1:]
(CAIXA / "chamadas.txt").open("a", encoding="utf-8").write(
    " ".join(argv) + chr(10))
if argv[:2] == ["auth", "token"]:
    print("token-de-" + argv[-1])
elif argv[:2] == ["issue", "list"]:
    print((CAIXA / "fechadas.json").read_text(encoding="utf-8"))
elif argv[:2] == ["api", "graphql"]:
    numero = [a for a in argv if a.startswith("numero=")][0].split("=")[1]
    issue = json.loads((CAIXA / ("issue-" + numero + ".json"))
                       .read_text(encoding="utf-8"))
    print(json.dumps({"data": {"repository": {"issue": issue}}}))
sys.exit(0)
"""

INDEXADOR_DE_MENTIRA = """import pathlib
import sys
pathlib.Path(sys.argv[0]).with_name("ronda-pedida.txt").write_text(
    " ".join(sys.argv[1:]), encoding="utf-8")
print("ronda: 1 alvo com mudança, indexado")
"""

CORPO_FICTICIO = """**Sessão:** concluída

## Objetivo
O relatório da vitrine fictícia fecha com o total certo.

## Critério de aceitação
- [x] o total bate — prova: `rodar-o-relatorio` → total 42
- [ ] o estorno aparece na linha dele

## Decisões do dono
- 01/01: o estorno fica para depois, porque ninguém o usa hoje.

## Estado
Feito: o total. Falta: o estorno.

## Onde mora o que se aprendeu
- conta de teste da vitrine: linha no `.credenciais/INVENTARIO.md`, papel "cliente"
"""


def _repositorio(pasta: Path) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    for argumentos in (["init", "-q", "-b", "principal"],
                       ["config", "user.email", "prova@exemplo"],
                       ["config", "user.name", "Prova"]):
        subprocess.run(["git", "-C", str(pasta), *argumentos], check=True,
                       capture_output=True)
    (pasta / ".gitignore").write_text(
        "/" + PASTA_DO_HISTORICO + "/\n/nucleo/executor.json\n",
        encoding="utf-8")
    (pasta / "nucleo").mkdir(exist_ok=True)
    (pasta / ARQUIVO_DO_EXECUTOR).write_text(json.dumps({
        "issues": {"repositorio": "dono-ficticio/quadro", "conta_gh": "robo"},
        "projetos": {"vitrine": {"repositorio": "vitrine"},
                     "balcao": {"repositorio": "balcao"}}}),
        encoding="utf-8")
    subprocess.run(["git", "-C", str(pasta), "add", "."], check=True,
                   capture_output=True)
    subprocess.run(["git", "-C", str(pasta), "commit", "-q", "-m",
                    "o total da vitrine bate (issue 7)"], check=True,
                   capture_output=True)
    return pasta


def _issue(numero: int, fechou: str, corpo: str = CORPO_FICTICIO,
           etiquetas=("vitrine",), pedidos=()) -> dict:
    return {"number": numero,
            "title": "vitrine - O relatório fecha com o total certo",
            "body": corpo, "url": f"https://exemplo.invalido/issues/{numero}",
            "stateReason": "COMPLETED", "closedAt": fechou,
            "labels": {"nodes": [{"name": nome} for nome in etiquetas]},
            "closedByPullRequestsReferences": {"nodes": list(pedidos)}}


CAMINHO_EM_QUEM_INSTALA = ".agents/historico/historico.py"
CAMINHO_NA_CASA = "modulos/historico/.agents/historico/historico.py"


def _commit_em(pasta: Path, quando: str, mensagem: str) -> None:
    datado = dict(os.environ, GIT_AUTHOR_DATE=quando,
                  GIT_COMMITTER_DATE=quando)
    subprocess.run(["git", "-C", str(pasta), "add", "-A"], check=True,
                   capture_output=True)
    subprocess.run(["git", "-C", str(pasta), "commit", "-q", "-m", mensagem],
                   check=True, capture_output=True, env=datado)


def _instrumento_no_checkout(pasta: Path, caminho: str,
                             chegou_em: str = "") -> Path:
    instrumento = pasta / caminho
    instrumento.parent.mkdir(parents=True, exist_ok=True)
    instrumento.write_text("print('instrumento de prova')\n",
                           encoding="utf-8")
    if chegou_em:
        _commit_em(pasta, chegou_em, "o histórico chega")
    return instrumento


def _marco_lido(principal: Path):
    arquivo = pasta_do_historico(principal) / ARQUIVO_DO_MARCO
    return instante(arquivo.read_text(encoding="utf-8").strip()) \
        if arquivo.is_file() else None


def testar() -> int:
    passou = falhou = 0

    def caso(nome: str, condicao) -> None:
        nonlocal passou, falhou
        if condicao:
            passou += 1
        else:
            falhou += 1
            print(f"FALHOU: {nome}")

    caso("o assunto do arquivo sai do título sem o prefixo do projeto, sem "
         "acento e em kebab",
         nome_do_arquivo(7, "vitrine_fixa - Relatório: o total é CERTO!")
         == "7-relatorio-o-total-e-certo.md")
    caso("assunto longo corta na palavra, não no meio dela",
         len(assunto_do_titulo("x - " + "palavra " * 30)) <= TETO_DO_ASSUNTO
         and not assunto_do_titulo("x - " + "palavra " * 30).endswith("-"))
    caso("o projeto sai da etiqueta que é também chave do cadastro",
         projeto_da_issue(["bug", "balcao"], ["vitrine", "balcao"])
         == "balcao")
    caso("sem etiqueta cadastrada, a issue vai para a pasta sem projeto",
         projeto_da_issue(["bug"], ["vitrine"]) == PASTA_SEM_PROJETO)
    criterios = criterios_do_corpo(CORPO_FICTICIO)
    caso("os critérios saem como estavam, marcados e em branco",
         criterios == ["- [x] o total bate — prova: `rodar-o-relatorio` → "
                       "total 42", "- [ ] o estorno aparece na linha dele"]
         and len(em_branco(criterios)) == 1)
    valor_falso = "ghp_" + "a1B2c3D4e5F6g7H8i9J0" * 2
    achados = formas_de_segredo(f"linha limpa\ntoken novo {valor_falso}\n")
    caso("texto com token falso é acusado pela linha e pela forma, e o "
         "recado não carrega o valor",
         achados == ["linha 2: token do GitHub"]
         and valor_falso not in "; ".join(achados))
    caso("CONTROLE: variável por nome e texto comum não são segredo",
         formas_de_segredo("token: `${GH_TOKEN}`\no total bate\n") == [])
    caso("senha escrita por extenso também é acusada",
         formas_de_segredo("senha: abobrinha123") != [])

    with tempfile.TemporaryDirectory(prefix="historico-") as pasta:
        base = Path(pasta)
        principal = _repositorio(base / "principal")
        irma = base / "irma"
        subprocess.run(["git", "-C", str(principal), "worktree", "add", "-q",
                        "-b", "trabalho", str(irma)], check=True,
                       capture_output=True)
        caso("de dentro da worktree, a árvore principal é a raiz de onde ela "
             "saiu",
             arvore_principal(irma) == principal.resolve())

        caixa = base / "caixa"
        caixa.mkdir()
        (caixa / "gh.py").write_text(GH_DE_MENTIRA, encoding="utf-8")
        guardado = dict(os.environ)
        os.environ["HISTORICO_TESTE_CAIXA"] = str(caixa)
        os.environ[gh.VARIAVEL_DO_GH] = gh.linha_de_comando(sys.executable,
                                                           caixa / "gh.py")
        try:
            antes = datetime(2030, 1, 1, tzinfo=timezone.utc)
            depois = "2030-01-02T10:00:00Z"
            (caixa / "fechadas.json").write_text(json.dumps([
                {"number": 7, "closedAt": depois},
                {"number": 8, "closedAt": depois},
                {"number": 3, "closedAt": "2029-12-31T10:00:00Z"}]),
                encoding="utf-8")
            (caixa / "issue-7.json").write_text(json.dumps(_issue(
                7, depois, pedidos=[{
                    "number": 70, "title": "o total certo",
                    "url": "https://exemplo.invalido/pull/70",
                    "mergedAt": depois}])), encoding="utf-8")
            (caixa / "issue-8.json").write_text(json.dumps(_issue(
                8, depois, etiquetas=("balcao",))), encoding="utf-8")
            (caixa / "issue-3.json").write_text(json.dumps(_issue(
                3, "2029-12-31T10:00:00Z")), encoding="utf-8")
            (caixa / "issue-9.json").write_text(json.dumps(_issue(
                9, depois, corpo=CORPO_FICTICIO + f"\n{valor_falso}\n")),
                encoding="utf-8")

            codigo, recado = pendentes(cwd=str(irma), agora=antes)
            caso("a primeira medida põe o marco e já acusa as issues "
                 "fechadas depois dele sem histórico — a de antes não conta",
                 codigo == SAIDA_COM_ACHADO and "#7" in recado
                 and "#8" in recado and "#3" not in recado
                 and (principal / PASTA_DO_HISTORICO / ARQUIVO_DO_MARCO)
                 .is_file())

            codigo, recados = colher([7], cwd=str(irma), agora=antes)
            gravado = (principal / PASTA_DO_HISTORICO / "vitrine"
                       / "7-o-relatorio-fecha-com-o-total-certo.md")
            texto = gravado.read_text(encoding="utf-8") \
                if gravado.is_file() else ""
            caso("a issue fechada por pedido de incorporação vira histórico "
                 "na pasta do projeto dela, na árvore PRINCIPAL",
                 codigo == SAIDA_LIMPA and gravado.is_file()
                 and not (irma / PASTA_DO_HISTORICO / "vitrine").exists())
            caso("o histórico traz os critérios como estavam e aponta o que "
                 "ficou em branco, sem dar a issue por pronta",
                 "- [ ] o estorno aparece na linha dele" in texto
                 and "Em branco no fechamento: 1" in texto)
            caso("e traz o pedido que a fechou, o commit pela marca, a "
                 "decisão e o ponteiro de onde mora o que se aprendeu",
                 "https://exemplo.invalido/pull/70" in texto
                 and "o total da vitrine bate (issue 7)" in texto
                 and "o estorno fica para depois" in texto
                 and ".credenciais/INVENTARIO.md" in texto)
            caso("o recado prova que gravou na árvore principal",
                 str(principal) in " ".join(recados))

            (principal / INDEXADOR).parent.mkdir(parents=True)
            (principal / INDEXADOR).write_text(INDEXADOR_DE_MENTIRA,
                                               encoding="utf-8")
            codigo, recados = colher([8], cwd=str(irma), agora=antes)
            caso("a issue fechada à mão, sem pedido, também vira histórico, "
                 "e diz que fechou à mão",
                 codigo == SAIDA_LIMPA
                 and FECHADA_A_MAO in (principal / PASTA_DO_HISTORICO
                                       / "balcao" / nome_do_arquivo(
                                           8, _issue(8, depois)["title"]))
                 .read_text(encoding="utf-8"))
            caso("depois de gravar, o índice recebe o pedido da ronda",
                 (principal / INDEXADOR).with_name("ronda-pedida.txt")
                 .is_file() and "índice: ronda" in " ".join(recados))

            codigo, recado = pendentes(cwd=str(irma), agora=antes)
            caso("com o histórico nascido, o aviso para de acusar",
                 codigo == SAIDA_LIMPA and "#7" not in recado)

            principal_vazia = _repositorio(base / "principal-vazia")
            irma_vazia = base / "irma-vazia"
            subprocess.run(["git", "-C", str(principal_vazia), "worktree",
                            "add", "-q", "-b", "vazia", str(irma_vazia)],
                           check=True, capture_output=True)
            caixa_vazia = base / "caixa-vazia"
            caixa_vazia.mkdir()
            (caixa_vazia / "fechadas.json").write_text("[]", encoding="utf-8")
            os.environ["HISTORICO_TESTE_CAIXA"] = str(caixa_vazia)
            try:
                codigo, recados = colher(cwd=str(irma_vazia), agora=antes,
                                        reindexar=False)
                leiame = pasta_do_historico(principal_vazia) / "LEIAME.md"
                caso("colher sem issue pendente cria LEIAME com uma linha "
                     "na árvore principal",
                     codigo == SAIDA_LIMPA and leiame.is_file()
                     and len(leiame.read_text(encoding="utf-8").splitlines()) == 1)
                leiame.write_text(
                    "Texto escolhido por quem mantém a pasta.\n",
                    encoding="utf-8")
                codigo, recados = colher(cwd=str(irma_vazia), agora=antes,
                                        reindexar=False)
                caso("colher preserva o LEIAME já escrito",
                     codigo == SAIDA_LIMPA
                     and leiame.read_text(encoding="utf-8")
                     == "Texto escolhido por quem mantém a pasta.\n")
            finally:
                os.environ["HISTORICO_TESTE_CAIXA"] = str(caixa)

            codigo, recados = colher([3], cwd=str(irma), agora=antes)
            caso("issue fechada antes do marco não se colhe: o histórico vale "
                 "só daqui para frente",
                 codigo == SAIDA_NAO_MEDIDA and "antes do marco" in recados[0])

            codigo, recados = colher([9], cwd=str(irma), agora=antes)
            caso("corpo com valor de credencial falso é recusado ANTES de "
                 "gravar, e o recado não mostra o valor",
                 codigo == SAIDA_NAO_MEDIDA and "forma de segredo" in recados[0]
                 and valor_falso not in recados[0]
                 and not list((principal / PASTA_DO_HISTORICO)
                              .glob("*/9-*.md")))

            (principal / ".gitignore").write_text("/nucleo/executor.json\n",
                                                  encoding="utf-8")
            (caixa / "issue-10.json").write_text(json.dumps(_issue(
                10, depois)), encoding="utf-8")
            codigo, recados = colher([10], cwd=str(irma), agora=antes)
            caso("pasta que o git não ignora não recebe histórico: o que é "
                 "rastreado sobe para o espelho",
                 codigo == SAIDA_NAO_MEDIDA and "NÃO ignora" in recados[0]
                 and not list((principal / PASTA_DO_HISTORICO)
                              .glob("*/10-*.md")))
            (principal / ".gitignore").write_text(
                "/" + PASTA_DO_HISTORICO + "/\n/nucleo/executor.json\n",
                encoding="utf-8")

            codigo, recados = colher([7], cwd=str(irma), agora=antes,
                                     ensaio=True)
            caso("o ensaio mostra o histórico e não grava",
                 codigo == SAIDA_LIMPA and "ENSAIO" in recados[0])

            chegada = "2029-12-30T10:00:00+00:00"
            primeira_vez = datetime(2030, 1, 5, tzinfo=timezone.utc)
            tarde = _repositorio(base / "chegou-antes")
            instrumento = _instrumento_no_checkout(
                tarde, CAMINHO_EM_QUEM_INSTALA, chegada)
            codigo, recado = pendentes(cwd=str(tarde), agora=primeira_vez,
                                       instrumento=instrumento)
            caso("checkout que recebe o instrumento tarde: o marco é o commit "
                 "que o trouxe, e a issue fechada entre a chegada e a "
                 "primeira execução entra na conta",
                 codigo == SAIDA_COM_ACHADO and "#3" in recado
                 and _marco_lido(tarde) == instante(chegada))

            instrumento.unlink()
            _commit_em(tarde, "2030-01-03T10:00:00+00:00", "o histórico sai")
            _instrumento_no_checkout(tarde, CAMINHO_EM_QUEM_INSTALA,
                                     "2030-01-04T10:00:00+00:00")
            (pasta_do_historico(tarde) / ARQUIVO_DO_MARCO).unlink(
                missing_ok=True)
            pendentes(cwd=str(tarde), agora=primeira_vez,
                      instrumento=instrumento)
            caso("instrumento que saiu e voltou conta a primeira chegada: a "
                 "sobra aparece como pendência, a falta sumiria calada",
                 _marco_lido(tarde) == instante(chegada))

            escolhido = "2030-01-01T00:00:00+00:00"
            (pasta_do_historico(tarde) / ARQUIVO_DO_MARCO).write_text(
                escolhido + "\n", encoding="utf-8")
            codigo, recado = pendentes(cwd=str(tarde), agora=primeira_vez,
                                       instrumento=instrumento)
            caso("CONTROLE: o .desde escrito vence a data do commit — é a "
                 "escolha de quem o escreveu",
                 "#3" not in recado and "#7" in recado
                 and _marco_lido(tarde) == instante(escolhido))

            casa = _repositorio(base / "casa")
            da_casa = _instrumento_no_checkout(casa, CAMINHO_NA_CASA,
                                               "2030-01-03T10:00:00+00:00")
            codigo, recado = pendentes(cwd=str(casa), agora=primeira_vez,
                                       instrumento=da_casa)
            caso("na casa a fonte mora em outro caminho, e a chegada sai do "
                 "caminho do próprio instrumento; o recado diz de onde veio "
                 "o marco",
                 codigo == SAIDA_LIMPA and "commit que trouxe" in recado
                 and _marco_lido(casa) == instante("2030-01-03T10:00:00Z"))

            sem_commit = _repositorio(base / "sem-commit")
            solto = _instrumento_no_checkout(sem_commit,
                                             CAMINHO_EM_QUEM_INSTALA)
            codigo, recado = pendentes(cwd=str(sem_commit),
                                       agora=primeira_vez, instrumento=solto)
            caso("CONTROLE: instrumento instalado e ainda sem commit cai no "
                 "comportamento de hoje — o marco é a primeira execução",
                 codigo == SAIDA_LIMPA and "#3" not in recado
                 and _marco_lido(sem_commit) == primeira_vez)

            alheio = _repositorio(base / "alheio")
            codigo, recado = pendentes(cwd=str(alheio), agora=primeira_vez,
                                       instrumento=instrumento)
            caso("CONTROLE: o instrumento de outro repositório não dá a "
                 "chegada a este checkout — cai no comportamento de hoje",
                 "#3" not in recado and _marco_lido(alheio) == primeira_vez)
        finally:
            os.environ.clear()
            os.environ.update(guardado)

        sem_linha = _repositorio(base / "sem-linha")
        (sem_linha / ".gitignore").write_text("/nucleo/executor.json\n",
                                              encoding="utf-8")
        codigo, recado = pendentes(cwd=str(sem_linha))
        caso("raiz cujo git não ignora a pasta não recebe nem o marco: a "
             "medida diz que não mediu e nada nasce solto no git status",
             codigo == SAIDA_NAO_MEDIDA and "NÃO ignora" in recado
             and not (sem_linha / PASTA_DO_HISTORICO).exists())

        sem_endereco = _repositorio(base / "sem-endereco")
        (sem_endereco / ARQUIVO_DO_EXECUTOR).write_text("{}",
                                                         encoding="utf-8")
        codigo, recado = pendentes(cwd=str(sem_endereco))
        caso("sem o repositório das issues declarado, a medida diz que não "
             "mediu, em vez de dizer que não há pendência",
             codigo == SAIDA_NAO_MEDIDA and "issues.repositorio" in recado)

    print(f"{'OK' if not falhou else 'FALHOU'}: {passou + falhou} casos")
    return 1 if falhou else 0


def montar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=USO)
    parser.add_argument("--pendentes", action="store_true",
                        help="diz quantas issues fecharam depois do marco e "
                             "ainda não têm histórico; sai 1 se houver")
    parser.add_argument("--colher", action="store_true",
                        help="grava o histórico das pendentes, ou só das "
                             "pedidas em --issue")
    parser.add_argument("--issue", action="append", type=int, default=[],
                        help="o número de uma issue fechada; repita a "
                             "bandeira")
    parser.add_argument("--ensaio", action="store_true",
                        help="mostra o histórico sem gravar")
    parser.add_argument("--cwd", default=".")
    parser.add_argument(BANDEIRA_DE_TESTE, action="store_true")
    return parser


def main() -> int:
    if BANDEIRA_DE_TESTE in sys.argv[1:]:
        return testar()
    a = montar_parser().parse_args()
    if a.colher or a.issue:
        codigo, recados = colher(a.issue, a.cwd, a.ensaio)
        for recado in recados:
            print(recado)
        return codigo
    codigo, recado = pendentes(a.cwd)
    print(recado)
    return codigo


if __name__ == "__main__":
    for canal in (sys.stdin, sys.stdout, sys.stderr):
        if not getattr(canal, "closed", True) and hasattr(canal, "reconfigure"):
            canal.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
