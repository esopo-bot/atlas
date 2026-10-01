import base64
import binascii
import json
import os
import subprocess
import sys
from pathlib import Path

VARIAVEL_DA_RAIZ_DO_PROJETO = "CLAUDE_PROJECT_DIR"
NIVEIS_DO_GANCHO_ATE_A_RAIZ = 2
VARIAVEL_DA_NUVEM = "CLAUDE_CODE_REMOTE"
VALOR_DA_NUVEM = "true"
VARIAVEL_DO_EXECUTOR = "ATLAS_EXECUTOR_BASE64"
ARQUIVO_DO_EXECUTOR = "nucleo/executor.json"
RECEITA = "conhecimento/estado-que-nao-viaja.md, seção \"A sessão na nuvem\""
TETO_DO_GIT_S = 10

EVENTO_DE_INICIO_DE_SESSAO = "SessionStart"
SILENCIO = 0
BANDEIRA_DE_TESTE = "--testar"

REPOSTO = "- `{}` reposto a partir da variável `{}`.".format(
    ARQUIVO_DO_EXECUTOR, VARIAVEL_DO_EXECUTOR)
SEM_VARIAVEL = (
    "- `{}` falta e a variável `{}` não veio no ambiente da nuvem: sem ele "
    "não se cria issue. Declare a variável no ambiente.").format(
        ARQUIVO_DO_EXECUTOR, VARIAVEL_DO_EXECUTOR)
VALOR_ILEGIVEL = (
    "- a variável `{}` não decodifica para um objeto JSON; `{}` não foi "
    "gravado. Gere o valor de novo pela receita.").format(
        VARIAVEL_DO_EXECUTOR, ARQUIVO_DO_EXECUTOR)
NAO_IGNORADO = (
    "- `{}` não está no .gitignore deste repositório; a sessão não o grava, "
    "porque ele carrega nome de conta e de repositório.").format(
        ARQUIVO_DO_EXECUTOR)
AVISO = (
    "SESSÃO NA NUVEM — o que muda aqui:\n{}\n"
    "- push só na branch desta sessão: o proxy do GitHub recusa as outras. "
    "A entrega é o pedido de incorporação dessa branch; a mescla na "
    "integração sai de uma sessão local.\n"
    "- `gh` responde pela conta do dono, e nenhuma outra conta existe aqui: "
    "o instrumento que pede `gh auth token --user <conta>` recusa.\n"
    "- servidor de contexto local, credencial de nuvem e banco não chegam; "
    "conector do claude.ai chega.\n"
    "A receita: {}"
)


def raiz_do_projeto_nunca_o_cwd() -> Path:
    declarada = os.environ.get(VARIAVEL_DA_RAIZ_DO_PROJETO)
    if declarada:
        return Path(declarada)
    return Path(__file__).resolve().parents[NIVEIS_DO_GANCHO_ATE_A_RAIZ]


def git_ignora(raiz: Path, caminho: str) -> bool:
    try:
        pronto = subprocess.run(
            ["git", "-C", str(raiz), "check-ignore", "-q", caminho],
            capture_output=True, timeout=TETO_DO_GIT_S)
    except (OSError, subprocess.SubprocessError):
        return False
    return pronto.returncode == 0


def executor_decodificado(valor: str):
    try:
        dado = json.loads(base64.b64decode(valor, validate=True))
    except (binascii.Error, ValueError):
        return None
    return dado if isinstance(dado, dict) else None


def repor_executor(raiz: Path, env, ignorado=git_ignora) -> str:
    alvo = raiz / ARQUIVO_DO_EXECUTOR
    if alvo.is_file():
        return ""
    valor = env.get(VARIAVEL_DO_EXECUTOR, "").strip()
    if not valor:
        return SEM_VARIAVEL
    dado = executor_decodificado(valor)
    if dado is None:
        return VALOR_ILEGIVEL
    if not ignorado(raiz, ARQUIVO_DO_EXECUTOR):
        return NAO_IGNORADO
    alvo.parent.mkdir(parents=True, exist_ok=True)
    alvo.write_text(json.dumps(dado, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    return REPOSTO


def decisao(raiz: Path, env, ignorado=git_ignora) -> str:
    if env.get(VARIAVEL_DA_NUVEM) != VALOR_DA_NUVEM:
        return ""
    linha_do_executor = repor_executor(raiz, env, ignorado)
    return AVISO.format(linha_do_executor or "- `{}` já está no disco.".format(
        ARQUIVO_DO_EXECUTOR), RECEITA)


def main() -> int:
    try:
        aviso = decisao(raiz_do_projeto_nunca_o_cwd(), os.environ)
    except Exception:
        return SILENCIO
    if aviso:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": EVENTO_DE_INICIO_DE_SESSAO,
            "additionalContext": aviso}}))
    return SILENCIO


def testar() -> int:
    import tempfile
    falhas, rodados = [], []

    def caso(rotulo, passou):
        rodados.append(rotulo)
        if not passou:
            falhas.append(rotulo)

    executor = {"issues": {"repositorio": "dona/quadro"}}
    codificado = base64.b64encode(
        json.dumps(executor).encode("utf-8")).decode("ascii")
    nuvem = {VARIAVEL_DA_NUVEM: VALOR_DA_NUVEM}
    sempre_ignorado = lambda raiz, caminho: True
    nunca_ignorado = lambda raiz, caminho: False

    with tempfile.TemporaryDirectory(prefix="sessao-na-nuvem-") as pasta:
        raiz = Path(pasta)
        alvo = raiz / ARQUIVO_DO_EXECUTOR

        caso("fora da nuvem o gancho cala e não grava, mesmo com a variável",
             decisao(raiz, {VARIAVEL_DO_EXECUTOR: codificado},
                     sempre_ignorado) == "" and not alvo.exists())

        caso("na nuvem sem a variável avisa que falta, e não grava",
             SEM_VARIAVEL in decisao(raiz, nuvem, sempre_ignorado)
             and not alvo.exists())

        caso("valor que não é base64 de um objeto avisa e não grava",
             VALOR_ILEGIVEL in decisao(
                 raiz, dict(nuvem, **{VARIAVEL_DO_EXECUTOR: "@@@"}),
                 sempre_ignorado) and not alvo.exists())

        caso("arquivo que o git não ignora não se grava",
             NAO_IGNORADO in decisao(
                 raiz, dict(nuvem, **{VARIAVEL_DO_EXECUTOR: codificado}),
                 nunca_ignorado) and not alvo.exists())

        aviso = decisao(raiz, dict(nuvem, **{VARIAVEL_DO_EXECUTOR: codificado}),
                        sempre_ignorado)
        caso("na nuvem com a variável repõe o arquivo, igual ao declarado",
             REPOSTO in aviso and alvo.is_file() and json.loads(
                 alvo.read_text(encoding="utf-8")) == executor)

        caso("o aviso nunca carrega o valor da variável",
             codificado not in aviso and "dona/quadro" not in aviso)

        alvo.write_text("{\"meu\": 1}", encoding="utf-8")
        decisao(raiz, dict(nuvem, **{VARIAVEL_DO_EXECUTOR: codificado}),
                sempre_ignorado)
        caso("arquivo que já existe não se sobrescreve",
             json.loads(alvo.read_text(encoding="utf-8")) == {"meu": 1})

    if falhas:
        print("FALHOU: {} de {} casos".format(len(falhas), len(rodados)))
        print("\n".join("  " + f for f in falhas))
        return 1
    print("OK: {} casos".format(len(rodados)))
    return 0


if __name__ == "__main__":
    sys.exit(testar() if BANDEIRA_DE_TESTE in sys.argv else main())
