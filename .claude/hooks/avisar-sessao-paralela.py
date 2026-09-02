import json
import os
import sys
import tempfile
import time
from pathlib import Path

VARIAVEL_DA_RAIZ_DO_PROJETO = "CLAUDE_PROJECT_DIR"
NIVEIS_DO_GANCHO_ATE_A_RAIZ = 2
PASTA_DOS_TRANSCRITOS = ".claude/projects"
EXTENSAO_DO_TRANSCRITO = ".jsonl"
JANELA_DE_VIDA_EM_SEGUNDOS = 600
QUANTAS_SESSOES_NOMEADAS = 3
LETRAS_DO_APELIDO = 8
PREFIXO_DA_MARCA = "avisou-sessao-paralela-"

CHAVE_DA_SESSAO = "session_id"
CHAVE_DA_ENTRADA = "tool_input"
CHAVE_DO_ARQUIVO = "file_path"
CHAVE_DO_CWD = "cwd"
CHAVE_DA_FERRAMENTA = "tool_name"
FERRAMENTAS_DE_ARQUIVO = ("Write", "Edit", "NotebookEdit")

SILENCIO = 0
EVENTO_ANTES_DA_FERRAMENTA = "PreToolUse"
BANDEIRA_DE_TESTE = "--testar"

AVISO = (
    "Outra sessão está viva neste mesmo repositório agora — {}.\n"
    "{}\n"
    "Isto NÃO impede a sua escrita: é aviso, e sai uma vez por sessão. "
    "Duas sessões na mesma pasta já receberam a mesma tarefa e só não "
    "colidiram porque uma verificou antes de escrever.\n"
    "Antes de commitar: `git status` para ver de quem é cada arquivo, e "
    "`git add` por caminho — nunca `-A` nem `.`, que varrem o trabalho da "
    "outra sessão para dentro do seu commit. Se o escopo pode se cruzar, "
    "diga a ela o que você vai tocar."
)
UMA_SESSAO = "a sessão {}, ativa há {}"
LINHA_DA_SESSAO = "  - sessão {}, ativa há {}"
AGORA_MESMO = "menos de um minuto"
HA_MINUTOS = "{} min"


def raiz_do_projeto_nunca_o_cwd() -> Path:
    declarada = os.environ.get(VARIAVEL_DA_RAIZ_DO_PROJETO)
    if declarada:
        return Path(declarada)
    return Path(__file__).resolve().parents[NIVEIS_DO_GANCHO_ATE_A_RAIZ]


def pasta_dos_transcritos(raiz: Path, lar: Path) -> Path:
    return lar / PASTA_DOS_TRANSCRITOS / str(raiz).replace(os.sep, "-")


def idade_legivel(segundos: float) -> str:
    minutos = int(segundos // 60)
    return AGORA_MESMO if minutos < 1 else HA_MINUTOS.format(minutos)


def sessoes_vivas_ao_lado(pasta: Path, minha: str, agora: float) -> list:
    if not pasta.is_dir():
        return []
    vivas = []
    for transcrito in pasta.glob(f"*{EXTENSAO_DO_TRANSCRITO}"):
        if transcrito.stem == minha:
            continue
        try:
            idade = agora - transcrito.stat().st_mtime
        except OSError:
            continue
        if 0 <= idade <= JANELA_DE_VIDA_EM_SEGUNDOS:
            vivas.append((idade, transcrito.stem))
    return sorted(vivas)[:QUANTAS_SESSOES_NOMEADAS]


def texto_do_aviso(vivas: list) -> str:
    if not vivas:
        return ""
    if len(vivas) == 1:
        idade, quem = vivas[0]
        return AVISO.format(
            UMA_SESSAO.format(quem[:LETRAS_DO_APELIDO], idade_legivel(idade)),
            "")
    corpo = "\n".join(
        LINHA_DA_SESSAO.format(quem[:LETRAS_DO_APELIDO], idade_legivel(idade))
        for idade, quem in vivas)
    return AVISO.format(f"{len(vivas)} delas", corpo)


def ja_avisou(marca: Path) -> bool:
    if marca.exists():
        return True
    try:
        marca.touch()
    except OSError:
        return False
    return False


def aqui_dentro(entrada: dict, raiz: Path) -> bool:
    if entrada.get(CHAVE_DA_FERRAMENTA) not in FERRAMENTAS_DE_ARQUIVO:
        return True
    alvo = (entrada.get(CHAVE_DA_ENTRADA) or {}).get(CHAVE_DO_ARQUIVO)
    return bool(alvo) and str(Path(alvo)).startswith(str(raiz))


def decisao(entrada: dict, raiz: Path, lar: Path, agora: float,
            temporaria: Path) -> str:
    minha = str(entrada.get(CHAVE_DA_SESSAO) or "")
    if not minha or not aqui_dentro(entrada, raiz):
        return ""
    vivas = sessoes_vivas_ao_lado(pasta_dos_transcritos(raiz, lar), minha,
                                  agora)
    if not vivas:
        return ""
    if ja_avisou(temporaria / f"{PREFIXO_DA_MARCA}{minha}"):
        return ""
    return texto_do_aviso(vivas)


def main() -> int:
    try:
        entrada = json.load(sys.stdin)
        if not isinstance(entrada, dict):
            return SILENCIO
        aviso = decisao(entrada, raiz_do_projeto_nunca_o_cwd(), Path.home(),
                        time.time(), Path(tempfile.gettempdir()))
    except Exception:
        return SILENCIO
    if aviso:
        print(json.dumps({"systemMessage": aviso}, ensure_ascii=False))
    return SILENCIO


def testar() -> int:
    falhas, rodados = [], []

    def caso(rotulo, passou):
        rodados.append(rotulo)
        if not passou:
            falhas.append(rotulo)

    with tempfile.TemporaryDirectory(prefix="aviso-paralela-") as pasta:
        base = Path(pasta)
        raiz = base / "repo"
        raiz.mkdir()
        lar = base / "lar"
        transcritos = pasta_dos_transcritos(raiz, lar)
        transcritos.mkdir(parents=True)
        agora = time.time()
        marcas = base / "marcas"
        marcas.mkdir()
        alvo = str(raiz / "arquivo.py")
        pedido = {CHAVE_DA_SESSAO: "minha",
                  CHAVE_DA_FERRAMENTA: "Write",
                  CHAVE_DA_ENTRADA: {CHAVE_DO_ARQUIVO: alvo}}

        caso("sem transcrito nenhum ao lado, o gancho cala",
             decisao(pedido, raiz, lar, agora, marcas) == "")

        (transcritos / "minha.jsonl").write_text("x", encoding="utf-8")
        os.utime(transcritos / "minha.jsonl", (agora, agora))
        caso("o meu próprio transcrito não me acusa de ser dois",
             decisao(pedido, raiz, lar, agora, marcas) == "")

        outra = transcritos / "outra-sessao.jsonl"
        outra.write_text("x", encoding="utf-8")
        os.utime(outra, (agora - 120, agora - 120))
        dito = decisao(pedido, raiz, lar, agora, marcas)
        caso("transcrito vivo de outra sessão vira aviso", bool(dito))
        caso("e o aviso nomeia a outra sessão", "outra-se" in dito)
        caso("e diz há quanto tempo ela se mexeu", "2 min" in dito)
        caso("e ensina o git add por caminho", "`git add` por caminho" in dito)
        caso("e não manda parar: o aviso não bloqueia",
             "impede" in dito and "NÃO impede" in dito)

        caso("o aviso sai uma vez por sessão, não a cada escrita",
             decisao(pedido, raiz, lar, agora, marcas) == "")

        velha = transcritos / "sessao-de-ontem.jsonl"
        velha.write_text("x", encoding="utf-8")
        os.utime(velha, (agora - 90000, agora - 90000))
        marcas_limpas = base / "marcas-limpas"
        marcas_limpas.mkdir()
        so_a_velha = base / "lar2"
        pasta_velha = pasta_dos_transcritos(raiz, so_a_velha)
        pasta_velha.mkdir(parents=True)
        (pasta_velha / "sessao-de-ontem.jsonl").write_text("x",
                                                           encoding="utf-8")
        os.utime(pasta_velha / "sessao-de-ontem.jsonl",
                 (agora - 90000, agora - 90000))
        caso("sessão de ontem não é sessão viva",
             decisao(pedido, raiz, so_a_velha, agora, marcas_limpas) == "")

        marcas_de_fora = base / "marcas-de-fora"
        marcas_de_fora.mkdir()
        fora = dict(pedido, **{CHAVE_DA_ENTRADA: {
            CHAVE_DO_ARQUIVO: str(base / "outro-repo" / "arquivo.py")}})
        caso("escrita fora do repositório não é colisão daqui",
             decisao(fora, raiz, lar, agora, marcas_de_fora) == "")

        marcas_do_shell = base / "marcas-do-shell"
        marcas_do_shell.mkdir()
        pelo_shell = {CHAVE_DA_SESSAO: "minha", CHAVE_DA_FERRAMENTA: "Bash",
                      CHAVE_DA_ENTRADA: {"command": "echo oi"}}
        caso("comando de shell também avisa: neste repositório se escreve por "
             "heredoc, e um aviso que só olha Write nunca aparece",
             bool(decisao(pelo_shell, raiz, lar, agora, marcas_do_shell)))

        marcas_sem_nada = base / "marcas-sem-nada"
        marcas_sem_nada.mkdir()
        sem_arquivo = {CHAVE_DA_SESSAO: "minha", CHAVE_DA_FERRAMENTA: "Write",
                       CHAVE_DA_ENTRADA: {}}
        caso("escrita sem arquivo declarado não vira aviso",
             decisao(sem_arquivo, raiz, lar, agora, marcas_sem_nada) == "")

        caso("o apelido da sessão é curto, e não o identificador inteiro",
             len("outra-se") == LETRAS_DO_APELIDO)

    if falhas:
        for falha in falhas:
            print(f"FALHOU: {falha}")
        print(f"FALHOU: {len(falhas)} de {len(rodados)} caso(s)")
        return 1
    print(f"OK: o aviso de sessão paralela — {len(rodados)} casos")
    return 0


if __name__ == "__main__":
    if BANDEIRA_DE_TESTE in sys.argv:
        sys.exit(testar())
    sys.exit(main())
