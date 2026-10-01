import importlib.util
import json
import re
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

EVENTO_DA_NEGATIVA = "PermissionDenied"
SILENCIO = 0
BANDEIRA_DE_TESTE = "--testar"

NIVEIS_DO_GANCHO_ATE_A_RAIZ = 2
PASTA_DO_GIT = ".git"
PASTA_DO_REGISTRO = "tmp"
ARQUIVO_DO_REGISTRO = "negativas-do-classificador.jsonl"
DETECTOR_DE_SEGREDO = ".agents/historico/historico.py"
NOME_DO_DETECTOR = "detector_de_segredo_do_historico"
NOME_DAS_FORMAS = "FORMAS_DE_SEGREDO"
TEMPO_DO_GIT_S = 5
TETO_DO_COMANDO = 4000

CHAVE_DA_FERRAMENTA = "tool_name"
CHAVE_DA_ENTRADA_DA_FERRAMENTA = "tool_input"
CHAVE_DO_COMANDO = "command"

MARCA_DO_SEGREDO = "«segredo: {}»"
FORMA_DO_PORTADOR = "portador"
FORMA_DO_NOME_SENSIVEL = "valor de nome sensível"
FORMA_DA_SEQUENCIA_LONGA = "sequência longa"
PORTADOR = re.compile(r"(?i)Bearer\s+\S+")
NOME_SENSIVEL = re.compile(
    r"(?i)([A-Za-z0-9_.-]*(?:KEY|TOKEN|SECRET|PASS|AUTH)[A-Za-z0-9_.-]*)"
    r"(\s*[:=]\s*)(['\"]?)([^\s'\"«]+)")
SEQUENCIA_LONGA = re.compile(r"[A-Za-z0-9/+_-]{20,}")
ATRIBUICAO_DE_AMBIENTE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

MOTIVO_SEM_DETECTOR = ("detector de segredo ausente ({}): o comando não foi "
                       "gravado")
NAO_MEDIU = ("registrar-negativa NÃO MEDIU: {}. A negativa, se houve, ficou "
             "fora do registro.")
NAO_GRAVOU = ("registrar-negativa NÃO GRAVOU em {}: {}. A negativa ficou fora "
              "do registro.")
SEM_ARVORE_PRINCIPAL = ("registrar-negativa: o git não disse a árvore "
                        "principal de {} ({}); gravo no tmp/ desta árvore, "
                        "que some com ela se for worktree.")


def raiz_da_camada_pelo_gancho(arquivo_do_gancho) -> Path:
    return Path(arquivo_do_gancho).resolve().parents[
        NIVEIS_DO_GANCHO_ATE_A_RAIZ]


def arvore_principal_pelo_git_comum(raiz: Path) -> Path:
    try:
        feito = subprocess.run(
            ["git", "-C", str(raiz), "rev-parse", "--path-format=absolute",
             "--git-common-dir"], capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=TEMPO_DO_GIT_S)
    except (OSError, subprocess.SubprocessError) as falha:
        print(SEM_ARVORE_PRINCIPAL.format(raiz, type(falha).__name__),
              file=sys.stderr)
        return raiz
    comum = Path(feito.stdout.strip()) if feito.stdout.strip() else None
    if feito.returncode != 0 or comum is None or comum.name != PASTA_DO_GIT:
        print(SEM_ARVORE_PRINCIPAL.format(
            raiz, "saiu %d" % feito.returncode), file=sys.stderr)
        return raiz
    return comum.parent


def formas_do_detector(raiz: Path) -> tuple:
    caminho = raiz / DETECTOR_DE_SEGREDO
    try:
        origem = importlib.util.spec_from_file_location(NOME_DO_DETECTOR,
                                                        caminho)
        modulo = importlib.util.module_from_spec(origem)
        origem.loader.exec_module(modulo)
        return tuple(getattr(modulo, NOME_DAS_FORMAS)), ""
    except Exception as falha:
        return None, MOTIVO_SEM_DETECTOR.format(type(falha).__name__)


def mascarar(texto: str, formas) -> str:
    for forma, padrao in formas:
        texto = padrao.sub(MARCA_DO_SEGREDO.format(forma), texto)
    texto = PORTADOR.sub(MARCA_DO_SEGREDO.format(FORMA_DO_PORTADOR), texto)
    texto = NOME_SENSIVEL.sub(
        lambda achado: achado.group(1) + achado.group(2) + achado.group(3)
        + MARCA_DO_SEGREDO.format(FORMA_DO_NOME_SENSIVEL), texto)
    return SEQUENCIA_LONGA.sub(
        MARCA_DO_SEGREDO.format(FORMA_DA_SEQUENCIA_LONGA), texto)


def programa_do_comando(comando: str) -> str:
    try:
        palavras = shlex.split(comando)
    except ValueError:
        palavras = comando.split()
    for palavra in palavras:
        if not ATRIBUICAO_DE_AMBIENTE.match(palavra):
            return palavra
    return ""


def registro_da_negativa(entrada: dict, formas, motivo: str) -> dict:
    dada = entrada.get(CHAVE_DA_ENTRADA_DA_FERRAMENTA)
    comando = dada.get(CHAVE_DO_COMANDO) if isinstance(dada, dict) else None
    if isinstance(comando, str):
        cru, programa = comando, programa_do_comando(comando)
    else:
        cru, programa = json.dumps(dada, ensure_ascii=False), ""
    razao = entrada.get("reason")
    registro = {
        "quando": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sessao": entrada.get("session_id", ""),
        "agente": entrada.get("agent_type", ""),
        "cwd": entrada.get("cwd", ""),
        "ferramenta": entrada.get(CHAVE_DA_FERRAMENTA, ""),
        "tamanho": len(cru)}
    if formas is None:
        registro.update(programa=None, comando=None, razao=None,
                        motivo=motivo)
        return registro
    registro.update(
        programa=mascarar(programa, formas),
        comando=mascarar(cru, formas)[:TETO_DO_COMANDO],
        razao=mascarar(razao, formas) if isinstance(razao, str) else None)
    return registro


def atender(corpo: str, arquivo_do_gancho) -> int:
    try:
        entrada = json.loads(corpo)
    except ValueError as falha:
        print(NAO_MEDIU.format("%s: %s" % (type(falha).__name__, falha)),
              file=sys.stderr)
        return SILENCIO
    if not isinstance(entrada, dict):
        print(NAO_MEDIU.format("a entrada não é um objeto JSON"),
              file=sys.stderr)
        return SILENCIO
    raiz = raiz_da_camada_pelo_gancho(arquivo_do_gancho)
    formas, motivo = formas_do_detector(raiz)
    destino = (arvore_principal_pelo_git_comum(raiz) / PASTA_DO_REGISTRO
               / ARQUIVO_DO_REGISTRO)
    linha = json.dumps(registro_da_negativa(entrada, formas, motivo),
                       ensure_ascii=False)
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        with destino.open("a", encoding="utf-8", newline="\n") as arquivo:
            arquivo.write(linha + "\n")
    except OSError as falha:
        print(NAO_GRAVOU.format(destino, type(falha).__name__),
              file=sys.stderr)
    return SILENCIO


def main() -> int:
    return atender(sys.stdin.read(), __file__)


FORMAS_DE_MENTIRA = (
    "import re\n"
    "FORMAS_DE_SEGREDO = (\n"
    "    (\"forma de bancada\", re.compile(r\"zz[0-9]{3}\")),)\n")
RAZAO_DE_MENTIRA = "[Irreversible Action] empurra direto na branch protegida"


def negativa_de_mentira(comando=None, cwd="", ferramenta="Bash",
                        entrada_da_ferramenta=None, razao=RAZAO_DE_MENTIRA):
    dada = (entrada_da_ferramenta if entrada_da_ferramenta is not None
            else {CHAVE_DO_COMANDO: comando, "description": "de mentira"})
    return json.dumps({"session_id": "sessao-de-mentira", "cwd": cwd,
                       "permission_mode": "auto",
                       "hook_event_name": EVENTO_DA_NEGATIVA,
                       CHAVE_DA_FERRAMENTA: ferramenta,
                       CHAVE_DA_ENTRADA_DA_FERRAMENTA: dada,
                       "tool_use_id": "toolu_de_mentira", "reason": razao})


def git_da_bancada(onde: Path, *argumentos):
    subprocess.run(["git", "-C", str(onde), "-c", "user.name=Prova", "-c",
                    "user.email=t@t", *argumentos], check=True,
                   capture_output=True, timeout=60)


def registrar_na_bancada(corpo: str, arquivo_do_gancho) -> tuple:
    import contextlib
    import io
    saida, erro = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(saida), contextlib.redirect_stderr(erro):
        codigo = atender(corpo, arquivo_do_gancho)
    return codigo, saida.getvalue(), erro.getvalue()


def linhas_do_registro(arvore: Path) -> list:
    alvo = arvore / PASTA_DO_REGISTRO / ARQUIVO_DO_REGISTRO
    if not alvo.is_file():
        return []
    return [json.loads(linha) for linha in
            alvo.read_text(encoding="utf-8").splitlines() if linha.strip()]


def texto_do_registro(arvore: Path) -> str:
    alvo = arvore / PASTA_DO_REGISTRO / ARQUIVO_DO_REGISTRO
    return alvo.read_text(encoding="utf-8") if alvo.is_file() else ""


def linha_do_registro_no_settings() -> list:
    configuracao = Path(__file__).resolve().parents[1] / "settings.json"
    try:
        blocos = json.loads(configuracao.read_text(encoding="utf-8"))[
            "hooks"][EVENTO_DA_NEGATIVA]
        ligados = [bloco.get("matcher", "") for bloco in blocos
                   if any(Path(__file__).name in gancho.get("command", "")
                          for gancho in bloco.get("hooks", []))]
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as erro:
        return ["a linha do gancho no %s NÃO MEDIU: %s" % (
            configuracao.name, type(erro).__name__)]
    if ligados != [""]:
        return ["a linha que chama este gancho em %s tem de ser uma só, no "
                "evento %s, sem matcher — veio %r" % (
                    configuracao.name, EVENTO_DA_NEGATIVA, ligados)]
    return []


def testar() -> int:
    import tempfile
    falhas, rodados, saidas = [], [], []

    def caso(rotulo, passou):
        rodados.append(rotulo)
        if not passou:
            falhas.append(rotulo)

    def registrar(corpo, gancho):
        codigo, saida, erro = registrar_na_bancada(corpo, gancho)
        saidas.append(saida)
        return codigo, erro

    chave_de_mentira = "".join(("0123456789abcdef", "fedcba9876543210"))
    senha_do_banco = "senha" + "Falsa" + "42"

    with tempfile.TemporaryDirectory(prefix="negativa-") as pasta:
        base = Path(pasta).resolve()
        camada = base / "camada"
        camada.mkdir()
        git_da_bancada(camada, "init", "-q")
        git_da_bancada(camada, "commit", "-q", "--allow-empty", "-m", "raiz")
        gancho = camada / ".claude" / "hooks" / "registrar-negativa.py"
        gancho.parent.mkdir(parents=True)
        detector = camada / DETECTOR_DE_SEGREDO
        detector.parent.mkdir(parents=True)
        detector.write_text(FORMAS_DE_MENTIRA, encoding="utf-8")

        def gravada(corpo, arquivo_do_gancho=gancho):
            antes = len(linhas_do_registro(camada))
            codigo, _ = registrar(corpo, arquivo_do_gancho)
            linhas = linhas_do_registro(camada)
            nova = linhas[-1] if len(linhas) == antes + 1 else {}
            return codigo, nova, texto_do_registro(camada)

        tmp_antes = (camada / PASTA_DO_REGISTRO).exists()
        comando = "git push origin HEAD:main"
        codigo, nova, _ = gravada(negativa_de_mentira(comando, str(camada)))
        caso("VERMELHO — a negativa do Bash vira uma linha com o programa, o "
             "tamanho, o comando e a razão",
             codigo == SILENCIO and nova.get("programa") == "git"
             and nova.get("tamanho") == len(comando)
             and nova.get("comando") == comando
             and nova.get("razao") == RAZAO_DE_MENTIRA
             and nova.get("ferramenta") == "Bash")
        caso("o tmp/ ausente nasce na primeira negativa",
             not tmp_antes and (camada / PASTA_DO_REGISTRO).is_dir())

        _, nova, _ = gravada(negativa_de_mentira(
            ferramenta="mcp__servidor__consulta",
            entrada_da_ferramenta={"consulta": "select 1"}))
        caso("ferramenta de MCP grava a entrada serializada, sem programa",
             nova.get("comando") == json.dumps({"consulta": "select 1"})
             and nova.get("programa") == "")

        comando = ("DD_API_KEY=" + chave_de_mentira + " curl -X POST "
                   "https://api.exemplo/v1/series")
        _, nova, texto = gravada(negativa_de_mentira(
            comando, razao="[Data Exfiltration] manda DD_API_KEY="
            + chave_de_mentira))
        caso("DD_API_KEY com 32 hex sai mascarada no comando e na razão, e o "
             "programa é o curl, não a atribuição",
             nova.get("programa") == "curl"
             and MARCA_DO_SEGREDO.format(FORMA_DO_NOME_SENSIVEL)
             in nova.get("comando", "")
             and MARCA_DO_SEGREDO.format(FORMA_DO_NOME_SENSIVEL)
             in nova.get("razao", "")
             and chave_de_mentira not in texto)

        comando = "PGPASSWORD=" + senha_do_banco + " psql -h banco -U leitor"
        _, nova, texto = gravada(negativa_de_mentira(comando))
        caso("PGPASSWORD sai mascarada, e o programa é o psql",
             nova.get("programa") == "psql"
             and nova.get("tamanho") == len(comando)
             and MARCA_DO_SEGREDO.format(FORMA_DO_NOME_SENSIVEL)
             in nova.get("comando", "")
             and senha_do_banco not in texto)

        _, nova, _ = gravada(negativa_de_mentira("echo zz123 Bearer abc"))
        caso("a forma do detector do histórico e o portador saem mascarados",
             MARCA_DO_SEGREDO.format("forma de bancada")
             in nova.get("comando", "")
             and MARCA_DO_SEGREDO.format(FORMA_DO_PORTADOR)
             in nova.get("comando", "")
             and "zz123" not in nova.get("comando", "")
             and "abc" not in nova.get("comando", ""))

        vizinho = camada / "projetos" / "vizinho"
        vizinho.mkdir(parents=True)
        git_da_bancada(vizinho, "init", "-q")
        _, nova, _ = gravada(negativa_de_mentira("git status", str(vizinho)))
        caso("cwd dentro de projetos/<vizinho> grava no tmp/ da camada, "
             "achada pelo gancho, e nada no vizinho",
             nova.get("cwd") == str(vizinho)
             and not (vizinho / PASTA_DO_REGISTRO).exists())

        worktree = camada / ".claude" / "worktrees" / "x"
        git_da_bancada(camada, "worktree", "add", "-q", "--detach",
                       str(worktree))
        gancho_na_worktree = worktree / ".claude" / "hooks" / gancho.name
        gancho_na_worktree.parent.mkdir(parents=True)
        segredo_sem_detector = "PGPASSWORD=" + senha_do_banco + " psql"
        _, nova, texto = gravada(
            negativa_de_mentira(segredo_sem_detector, str(worktree)),
            gancho_na_worktree)
        caso("o gancho da worktree grava no tmp/ da árvore principal, pelo "
             "--git-common-dir, e nada na worktree",
             nova.get("cwd") == str(worktree)
             and not (worktree / PASTA_DO_REGISTRO).exists())
        caso("sem o detector do histórico, comando, programa e razão saem "
             "nulos com o motivo, e o tamanho fica",
             bool(nova) and nova.get("comando") is None
             and nova.get("programa") is None and nova.get("razao") is None
             and "detector de segredo ausente" in nova.get("motivo", "")
             and nova.get("tamanho") == len(segredo_sem_detector)
             and senha_do_banco not in texto)

        antes = len(linhas_do_registro(camada))
        for rotulo, corpo in (("a lista", "[1, 2]"),
                              ("o texto solto", "isto não é JSON")):
            codigo, erro = registrar(corpo, gancho)
            caso("entrada ilegível (%s): sai 0, uma linha de NÃO MEDIU no "
                 "erro, nada gravado" % rotulo,
                 codigo == SILENCIO and erro.count("\n") == 1
                 and "NÃO MEDIU" in erro
                 and len(linhas_do_registro(camada)) == antes)

    caso("o stdout fica vazio em todo caso: o gancho nunca manda retry",
         len(saidas) > 0 and all(saida == "" for saida in saidas))

    real = raiz_da_camada_pelo_gancho(__file__)
    if (real / DETECTOR_DE_SEGREDO).is_file():
        formas, motivo = formas_do_detector(real)
        caso("o detector de verdade desta árvore carrega pelo caminho do "
             "gancho" + (" — " + motivo if motivo else ""), bool(formas))

    ligacao = linha_do_registro_no_settings()
    caso("a linha chega: o settings.json chama este gancho no evento certo"
         + (" — " + "; ".join(ligacao) if ligacao else ""), not ligacao)

    if falhas:
        for f in falhas:
            print(f"FALHOU: {f}")
        print(f"FALHOU: {len(falhas)} de {len(rodados)} casos")
        return 1
    print(f"OK: o registro da negativa do classificador — {len(rodados)} "
          f"casos")
    return 0


if __name__ == "__main__":
    if BANDEIRA_DE_TESTE in sys.argv:
        sys.exit(testar())
    sys.exit(main())
