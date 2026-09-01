import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

ARQUIVO_DE_DECLARACAO = ".mcp.json"
CHAVE_DOS_SERVIDORES = "mcpServers"
CHAVE_DO_COMANDO = "command"
CHAVE_DOS_ARGUMENTOS = "args"
CHAVE_DO_AJUDANTE_DE_CABECALHO = "headersHelper"

VARIAVEL_DA_RAIZ_DO_PROJETO = "CLAUDE_PROJECT_DIR"
NIVEIS_DO_GANCHO_ATE_A_RAIZ = 2

EXTENSOES_DE_EXECUTAVEL_OU_SCRIPT = {".py", ".js", ".mjs", ".cjs", ".ts",
                                     ".sh", ".ps1", ".cmd", ".bat", ".exe",
                                     ".jar", ".rb", ".php"}
PREFIXOS_DE_BANDEIRA_E_DE_PACOTE_COM_ESCOPO = ("-", "@")
MARCAS_DE_URL_VARIAVEL_E_CURINGA = ("${", "://", "*")
SEPARADORES_DE_PASTA = ("/", "\\")

MARCA_DE_ETAPA_NO_AMBIENTE = "ENCADEADOR_ETAPA"
COMANDO_DO_GIT_QUE_IGNORA = ("git", "check-ignore", "-q")
TEMPO_DO_GIT = 10

EVENTO_DE_INICIO_DE_SESSAO = "SessionStart"
BANDEIRA_DE_TESTE = "--testar"
SILENCIO = 0
FALHA_ABERTO = 0

LINHA_DO_CAMINHO_AUSENTE = "- servidor `{}`: `{}` não existe no disco"
AVISO = (
    "AVISO do gancho verificar-mcp: o .mcp.json declara caminho que não "
    "existe. O servidor não vai subir e o sintoma é silencioso — ele "
    "some da lista de ferramentas como se nunca tivesse sido "
    "configurado.\n{}\n"
    "Avise o dono antes de precisar da ferramenta, não depois de ela "
    "faltar."
)

FALHA_DEVIA_ACUSAR = "  DEVIA ACUSAR e calou — {}"
FALHA_DEVIA_CALAR = "  DEVIA CALAR e acusou — {}: {}"
RESUMO_FALHOU = "FALHOU: {} de {} casos"
RESUMO_OK = "OK: {} casos — {} acusados, {} calados"


def parece_caminho_verificavel(token: str) -> bool:
    if not token or token.startswith(PREFIXOS_DE_BANDEIRA_E_DE_PACOTE_COM_ESCOPO):
        return False
    if any(marca in token for marca in MARCAS_DE_URL_VARIAVEL_E_CURINGA):
        return False
    if any(token.lower().endswith(extensao)
           for extensao in EXTENSOES_DE_EXECUTAVEL_OU_SCRIPT):
        return True
    return any(separador in token for separador in SEPARADORES_DE_PASTA)


def tokens_do_comando(texto: str) -> list:
    try:
        return shlex.split(texto, posix=False)
    except ValueError:
        return texto.split()


def tokens_de_caminho_do_servidor(servidor: dict) -> list:
    tokens = []
    comando = servidor.get(CHAVE_DO_COMANDO, "")
    if isinstance(comando, str) and comando:
        tokens += tokens_do_comando(comando)
    argumentos = servidor.get(CHAVE_DOS_ARGUMENTOS, [])
    if isinstance(argumentos, list):
        tokens += [a for a in argumentos if isinstance(a, str)]
    ajudante = servidor.get(CHAVE_DO_AJUDANTE_DE_CABECALHO, "")
    if isinstance(ajudante, str) and ajudante:
        tokens += tokens_do_comando(ajudante)
    return [t.strip('"') for t in tokens if isinstance(t, str)]


def alvo_no_disco(raiz: Path, token: str) -> Path:
    caminho = Path(token.replace("\\", "/"))
    return caminho if caminho.is_absolute() else raiz / caminho


def caminhos_declarados_que_sumiram(declaracao: dict, raiz: Path) -> list:
    ausentes = []
    for nome, servidor in declaracao.get(CHAVE_DOS_SERVIDORES, {}).items():
        if not isinstance(servidor, dict):
            continue
        for token in tokens_de_caminho_do_servidor(servidor):
            if not parece_caminho_verificavel(token):
                continue
            if not alvo_no_disco(raiz, token).exists():
                ausentes.append((nome, token))
    return ausentes


def raiz_do_projeto_nunca_o_cwd() -> Path:
    declarada = os.environ.get(VARIAVEL_DA_RAIZ_DO_PROJETO)
    if declarada:
        return Path(declarada)
    return Path(__file__).resolve().parents[NIVEIS_DO_GANCHO_ATE_A_RAIZ]


def dentro_de_uma_etapa() -> bool:
    return bool(os.environ.get(MARCA_DE_ETAPA_NO_AMBIENTE))


def o_git_ignora(caminho: str, raiz: Path) -> bool:
    try:
        feito = subprocess.run(
            [*COMANDO_DO_GIT_QUE_IGNORA, caminho.replace("\\", "/")],
            cwd=str(raiz), capture_output=True, timeout=TEMPO_DO_GIT)
    except (OSError, subprocess.SubprocessError):
        return False
    return feito.returncode == 0


def sem_o_que_e_local_de_propria_declaracao(ausentes: list,
                                            raiz: Path) -> list:
    return [(nome, caminho) for nome, caminho in ausentes
            if not o_git_ignora(caminho, raiz)]


def main() -> int:
    raiz = raiz_do_projeto_nunca_o_cwd()
    arquivo = raiz / ARQUIVO_DE_DECLARACAO
    if not arquivo.exists():
        return SILENCIO

    try:
        declaracao = json.loads(arquivo.read_text(encoding="utf-8"))
        ausentes = caminhos_declarados_que_sumiram(declaracao, raiz)
    except (OSError, json.JSONDecodeError, AttributeError, TypeError):
        return FALHA_ABERTO

    if dentro_de_uma_etapa():
        ausentes = sem_o_que_e_local_de_propria_declaracao(ausentes, raiz)

    if not ausentes:
        return SILENCIO

    linhas = [LINHA_DO_CAMINHO_AUSENTE.format(nome, caminho)
              for nome, caminho in ausentes]
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": EVENTO_DE_INICIO_DE_SESSAO,
        "additionalContext": AVISO.format("\n".join(linhas)),
    }}))
    return SILENCIO


def testar() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as pasta:
        raiz = Path(pasta)
        (raiz / "existe").mkdir()
        (raiz / "existe/servidor.py").write_text("", encoding="utf-8")
        absoluto = str(raiz / "existe/servidor.py")

        ACUSA = [
            ("arg relativo que sumiu",
             {"command": "python", "args": [".agents/mcp/x/servidor.py"]}),
            ("ajudante de cabeçalho ausente",
             {"type": "http", "url": "https://exemplo.com/mcp",
              "headersHelper": "python .claude/servidor/cabecalho.py"}),
            ("o próprio command é caminho morto",
             {"command": "./bin/servidor.exe"}),
            ("caminho com barra invertida",
             {"command": "python", "args": ["pasta\\faltante.py"]}),
            ("caminho absoluto que não existe",
             {"command": "python", "args": [absoluto + ".sumiu"]}),
        ]

        CALA = [
            ("arquivo relativo que existe",
             {"command": "python", "args": ["existe/servidor.py"]}),
            ("programa do PATH com módulo",
             {"command": "python", "args": ["-m", "modulo.qualquer"]}),
            ("pacote npm com escopo não é arquivo",
             {"command": "npx", "args": ["-y", "@escopo/pacote-mcp"]}),
            ("servidor http sem caminho nenhum",
             {"type": "http", "url": "https://exemplo.com/mcp",
              "headers": {"Authorization": "Bearer ${TOKEN}"}}),
            ("variável não resolvida fica de fora",
             {"command": "python", "args": ["${CAMINHO}/servidor.py"]}),
            ("caminho absoluto que existe",
             {"command": "python", "args": [absoluto]}),
        ]

        falhas = []
        for rotulo, servidor in ACUSA:
            if not caminhos_declarados_que_sumiram(
                    {CHAVE_DOS_SERVIDORES: {"s": servidor}}, raiz):
                falhas.append(FALHA_DEVIA_ACUSAR.format(rotulo))
        for rotulo, servidor in CALA:
            achou = caminhos_declarados_que_sumiram(
                {CHAVE_DOS_SERVIDORES: {"s": servidor}}, raiz)
            if achou:
                falhas.append(FALHA_DEVIA_CALAR.format(rotulo, achou))

        comportamento = []

        def caso(rotulo, condicao):
            comportamento.append(rotulo)
            if not condicao:
                falhas.append(FALHA_DEVIA_CALAR.format(rotulo, "não"))

        subprocess.run(["git", "init", "-q"], cwd=str(raiz),
                       capture_output=True)
        (raiz / ".gitignore").write_text("/local/\n", encoding="utf-8")
        local, rastreado = "local/servidor.py", "existe/outro.py"
        ausentes = [("local", local), ("rastreado", rastreado)]
        caso("caminho que o git ignora sai da lista dentro de uma etapa",
             sem_o_que_e_local_de_propria_declaracao(ausentes, raiz)
             == [("rastreado", rastreado)])
        moda_windows = "local\\servidor.py"
        caso("caminho a moda Windows tambem sai da lista, mesma ignoracao",
             sem_o_que_e_local_de_propria_declaracao(
                 [("windows", moda_windows)], raiz) == [])
        guardado = os.environ.pop(MARCA_DE_ETAPA_NO_AMBIENTE, None)
        caso("fora de uma etapa, quem lê o aviso é o dono e nada se filtra",
             not dentro_de_uma_etapa())
        os.environ[MARCA_DE_ETAPA_NO_AMBIENTE] = "1"
        caso("dentro de uma etapa a marca do executor é reconhecida",
             dentro_de_uma_etapa())
        if guardado is None:
            os.environ.pop(MARCA_DE_ETAPA_NO_AMBIENTE, None)
        else:
            os.environ[MARCA_DE_ETAPA_NO_AMBIENTE] = guardado

        total = len(ACUSA) + len(CALA) + len(comportamento)
        if falhas:
            print(RESUMO_FALHOU.format(len(falhas), total))
            print("\n".join(falhas))
            return 1
        print(RESUMO_OK.format(total, len(ACUSA), len(CALA)))
        return 0


if __name__ == "__main__":
    sys.exit(testar() if BANDEIRA_DE_TESTE in sys.argv else main())
