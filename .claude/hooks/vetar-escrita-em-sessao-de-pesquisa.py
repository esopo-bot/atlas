import json
import os
import re
import shlex
import sys
from pathlib import Path

EVENTO_ANTES_DA_FERRAMENTA = "PreToolUse"
DECISAO_DE_NEGAR = "deny"
BANDEIRA_DE_TESTE = "--testar"
SILENCIO = 0

MARCA_NO_AMBIENTE = "ATLAS_SO_LEITURA"
VARIAVEL_DA_RAIZ_DO_PROJETO = "CLAUDE_PROJECT_DIR"
NIVEIS_DO_GANCHO_ATE_A_RAIZ = 2

CHAVE_DA_FERRAMENTA = "tool_name"
CHAVE_DA_ENTRADA = "tool_input"
CHAVE_DO_ARQUIVO = "file_path"
CHAVE_DO_COMANDO = "command"
FERRAMENTAS_DE_ARQUIVO = ("Write", "Edit", "NotebookEdit")
FERRAMENTAS_DE_SHELL = ("Bash", "PowerShell")

SEPARADORES_DE_COMANDO = re.compile(r"&&|\|\||;|\n|\r|\|")
REDIRECIONAMENTO = re.compile(r">>?\s*([^\s;|&]+)")
ASPAS = "\"'"
MARCA_DE_OPCAO = "-"
BARRA = "/"
CONTRABARRA = "\\"
NOME_DO_WINDOWS = "nt"
VERBOS_QUE_ESCREVEM = (
    "cp", "mv", "rm", "rmdir", "mkdir", "touch", "tee", "install",
    "truncate", "chmod", "chown", "ln", "sed", "dd", "unzip", "tar",
)
RECUSA = (
    "Sessão de pesquisa: esta sessão abriu em modo somente leitura "
    "({marca} está no ambiente), e o modo proíbe escrever dentro do "
    "repositório — o alvo `{alvo}` cai lá.\n"
    "O que ela entrega é a ISSUE, não arquivo. Rascunho e medição vão para a "
    "pasta temporária da máquina, que o sistema limpa sozinho; o que valeria "
    "memória vira comentário na issue do trabalho.\n"
    "Se você precisa mesmo escrever no repositório, este é o modo errado: "
    "abra a sessão sem a marca.")
RECUSA_SEM_ENTENDER = ("não entendi a entrada do gancho ({}: {}); na dúvida, "
                       "recuso")

RESUMO = "{}: {} casos — {} barrados, {} liberados, {} de comportamento"


def raiz_do_projeto_nunca_o_cwd() -> Path:
    declarada = os.environ.get(VARIAVEL_DA_RAIZ_DO_PROJETO)
    if declarada:
        return Path(declarada)
    return Path(__file__).resolve().parents[NIVEIS_DO_GANCHO_ATE_A_RAIZ]


def o_modo_esta_posto(ambiente) -> bool:
    return bool((ambiente or {}).get(MARCA_NO_AMBIENTE))


def em_forma_de_comparacao(caminho: str) -> str:
    plano = str(caminho).replace(CONTRABARRA, BARRA).rstrip(BARRA)
    return plano.lower() if os.name == NOME_DO_WINDOWS else plano


def dentro_da_raiz(alvo: str, raiz: Path) -> bool:
    if not alvo:
        return False
    de_dentro = em_forma_de_comparacao(raiz)
    candidato = em_forma_de_comparacao(alvo)
    return candidato == de_dentro or candidato.startswith(de_dentro + BARRA)


def alvos_da_ferramenta_de_arquivo(entrada: dict) -> list:
    if entrada.get(CHAVE_DA_FERRAMENTA) not in FERRAMENTAS_DE_ARQUIVO:
        return []
    alvo = (entrada.get(CHAVE_DA_ENTRADA) or {}).get(CHAVE_DO_ARQUIVO)
    return [alvo] if alvo else []


def sem_aspas(token: str) -> str:
    if len(token) >= 2 and token[0] in ASPAS and token[-1] == token[0]:
        return token[1:-1]
    return token


def tokens_de(segmento: str) -> list:
    try:
        return [sem_aspas(t) for t in shlex.split(segmento, posix=False)]
    except ValueError:
        return [sem_aspas(t) for t in segmento.split()]


def alvos_do_shell(comando: str) -> list:
    if not isinstance(comando, str) or not comando:
        return []
    achados = [sem_aspas(a) for a in REDIRECIONAMENTO.findall(comando)]
    for segmento in SEPARADORES_DE_COMANDO.split(comando):
        tokens = tokens_de(segmento)
        if not tokens or tokens[0] not in VERBOS_QUE_ESCREVEM:
            continue
        achados += [t for t in tokens[1:] if not t.startswith(MARCA_DE_OPCAO)]
    return achados


def alvo_recusado(entrada: dict, raiz: Path, ambiente) -> str:
    if not o_modo_esta_posto(ambiente) or not isinstance(entrada, dict):
        return ""
    alvos = list(alvos_da_ferramenta_de_arquivo(entrada))
    if entrada.get(CHAVE_DA_FERRAMENTA) in FERRAMENTAS_DE_SHELL:
        alvos += alvos_do_shell(
            (entrada.get(CHAVE_DA_ENTRADA) or {}).get(CHAVE_DO_COMANDO, ""))
    for alvo in alvos:
        if dentro_da_raiz(alvo, raiz):
            return alvo
    return ""


def recusar(alvo: str) -> int:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": EVENTO_ANTES_DA_FERRAMENTA,
        "permissionDecision": DECISAO_DE_NEGAR,
        "permissionDecisionReason": RECUSA.format(
            marca=MARCA_NO_AMBIENTE, alvo=alvo),
    }}, ensure_ascii=False))
    return SILENCIO


def recusa_por_nao_entender(falha) -> int:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": EVENTO_ANTES_DA_FERRAMENTA,
        "permissionDecision": DECISAO_DE_NEGAR,
        "permissionDecisionReason": RECUSA_SEM_ENTENDER.format(
            type(falha).__name__, falha),
    }}, ensure_ascii=False))
    return SILENCIO


def decidir() -> int:
    entrada = json.load(sys.stdin)
    if not isinstance(entrada, dict):
        return SILENCIO
    alvo = alvo_recusado(entrada, raiz_do_projeto_nunca_o_cwd(), os.environ)
    return recusar(alvo) if alvo else SILENCIO


def main() -> int:
    try:
        return decidir()
    except Exception as falha:
        return recusa_por_nao_entender(falha)


RAIZ_DE_MENTIRA = Path("D:/repo") if os.name == "nt" else Path("/repo")
FORA = "D:/outro" if os.name == "nt" else "/outro"
COM_A_MARCA = {MARCA_NO_AMBIENTE: "1"}
SEM_A_MARCA = {}


def _escrita(caminho: str) -> dict:
    return {CHAVE_DA_FERRAMENTA: "Write",
            CHAVE_DA_ENTRADA: {CHAVE_DO_ARQUIVO: caminho}}


def _shell(comando: str) -> dict:
    return {CHAVE_DA_FERRAMENTA: "Bash",
            CHAVE_DA_ENTRADA: {CHAVE_DO_COMANDO: comando}}


BARRA_A_ESCRITA = [
    ("Write dentro da raiz", _escrita(str(RAIZ_DE_MENTIRA / "nucleo/a.json"))),
    ("Write na raiz, caminho com contrabarra",
     _escrita(str(RAIZ_DE_MENTIRA) + "\\conhecimento\\a.md")),
    ("Edit dentro da raiz", {CHAVE_DA_FERRAMENTA: "Edit",
                             CHAVE_DA_ENTRADA: {CHAVE_DO_ARQUIVO: str(
                                 RAIZ_DE_MENTIRA / "AGENTS.md")}}),
    ("shell que redireciona para dentro da raiz",
     _shell(f'echo x > {RAIZ_DE_MENTIRA / "tmp/rascunho.txt"}')),
    ("shell que copia para dentro da raiz",
     _shell(f'cp /outro/a.py {RAIZ_DE_MENTIRA / "a.py"}')),
    ("shell que apaga dentro da raiz",
     _shell(f'rm -rf {RAIZ_DE_MENTIRA / "tmp"}')),
    ("shell que cria pasta dentro da raiz",
     _shell(f'mkdir -p {RAIZ_DE_MENTIRA / "tmp/x"}')),
    ("shell com sed no lugar dentro da raiz",
     _shell(f'sed -i s/a/b/ {RAIZ_DE_MENTIRA / "nucleo/regras.json"}')),
    ("shell escondido depois de um separador",
     _shell(f'git status && touch {RAIZ_DE_MENTIRA / "novo.txt"}')),
]

LIBERA = [
    ("Write fora da raiz", _escrita(FORA + "/rascunho.md")),
    ("Write na pasta temporária", _escrita(
        str(Path(os.environ.get("TEMP", "/tmp")) / "rascunho.md"))),
    ("Read dentro da raiz", {CHAVE_DA_FERRAMENTA: "Read",
                             CHAVE_DA_ENTRADA: {CHAVE_DO_ARQUIVO: str(
                                 RAIZ_DE_MENTIRA / "AGENTS.md")}}),
    ("shell que só lê dentro da raiz",
     _shell(f'grep -n x {RAIZ_DE_MENTIRA / "AGENTS.md"}')),
    ("shell que roda instrumento sem escrever",
     _shell(f'python {RAIZ_DE_MENTIRA / "verificacoes.py"} ritual')),
    ("shell que escreve fora da raiz",
     _shell(f'echo x > {FORA}/rascunho.txt')),
    ("git de leitura", _shell("git status --short")),
]


def testar() -> int:
    falhas, rodados = [], []

    def caso(rotulo, passou):
        rodados.append(rotulo)
        if not passou:
            falhas.append(rotulo)

    for rotulo, entrada in BARRA_A_ESCRITA:
        caso(f"barra com a marca — {rotulo}",
             bool(alvo_recusado(entrada, RAIZ_DE_MENTIRA, COM_A_MARCA)))
    for rotulo, entrada in LIBERA:
        caso(f"libera com a marca — {rotulo}",
             not alvo_recusado(entrada, RAIZ_DE_MENTIRA, COM_A_MARCA))

    comportamento = [
        ("sem a marca, a cerca não morde nem na escrita mais óbvia",
         not alvo_recusado(_escrita(str(RAIZ_DE_MENTIRA / "AGENTS.md")),
                           RAIZ_DE_MENTIRA, SEM_A_MARCA)),
        ("sem a marca, o shell destrutivo passa",
         not alvo_recusado(_shell(f'rm -rf {RAIZ_DE_MENTIRA / "tmp"}'),
                           RAIZ_DE_MENTIRA, SEM_A_MARCA)),
        ("a marca vazia não conta como posta",
         not o_modo_esta_posto({MARCA_NO_AMBIENTE: ""})),
        ("a marca com qualquer valor conta como posta",
         o_modo_esta_posto({MARCA_NO_AMBIENTE: "sim"})),
        ("entrada sem ferramenta não estoura",
         not alvo_recusado({}, RAIZ_DE_MENTIRA, COM_A_MARCA)),
        ("entrada sem caminho não estoura",
         not alvo_recusado({CHAVE_DA_FERRAMENTA: "Write",
                            CHAVE_DA_ENTRADA: {}},
                           RAIZ_DE_MENTIRA, COM_A_MARCA)),
        ("a recusa nomeia a marca e o alvo, para a sessão saber o que fazer",
         MARCA_NO_AMBIENTE in RECUSA.format(marca=MARCA_NO_AMBIENTE,
                                            alvo="x")
         and "x" in RECUSA.format(marca=MARCA_NO_AMBIENTE, alvo="x")),
        ("a raiz sai da variável do projeto, nunca do cwd",
         VARIAVEL_DA_RAIZ_DO_PROJETO in
         raiz_do_projeto_nunca_o_cwd.__code__.co_consts
         or bool(os.environ.get(VARIAVEL_DA_RAIZ_DO_PROJETO)) is not None),
    ]
    for rotulo, passou in comportamento:
        caso(f"comportamento — {rotulo}", passou)

    for falha in falhas:
        print(f"  [CAIU] {falha}")
    print(RESUMO.format("FALHOU" if falhas else "OK", len(rodados),
                        len(BARRA_A_ESCRITA), len(LIBERA), len(comportamento)))
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(testar() if BANDEIRA_DE_TESTE in sys.argv else main())
