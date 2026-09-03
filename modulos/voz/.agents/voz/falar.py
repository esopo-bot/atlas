import argparse
import ctypes
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DESCRICAO_DA_CLI = (
    "fala um texto em voz alta: motor neural quando há rede, reserva "
    "offline quando não há")

AQUI = Path(__file__).resolve().parent
NOME_DO_MODULO = "voz"
PASTA_DA_FONTE_DE_MODULOS = "modulos"
ARQUIVO_DA_CONFIGURACAO = AQUI / "voz.json"
PASTA_DO_VENV = AQUI / "venv"

BANDEIRA_DE_TESTE = "--testar"

CHAVE_LIGADA = "ligada"
CHAVE_VOZ = "voz"
CHAVE_RITMO = "ritmo"
CHAVE_TRATAMENTO = "tratamento"

PADRAO = {
    CHAVE_LIGADA: True,
    CHAVE_VOZ: "pt-BR-FranciscaNeural",
    CHAVE_RITMO: "-8%",
    CHAVE_TRATAMENTO: "",
}

MARCA_DE_PLACEHOLDER = "${"
PARTES_DO_IDIOMA = 2
SEPARADOR_DA_VOZ = "-"

PACOTE_DO_MOTOR = "edge-tts"
EXECUTAVEL_DO_MOTOR = "edge-tts"
EXECUTAVEL_DO_PIP = "pip"
PREFIXO_DO_AUDIO = "falar-"
SUFIXO_DO_AUDIO = ".mp3"
TETO_DO_ERRO = 400

SISTEMA_WINDOWS = "Windows"
SISTEMA_LINUX = "Linux"
SISTEMA_MAC = "Darwin"

PASTA_DOS_BINARIOS = {SISTEMA_WINDOWS: "Scripts"}
PASTA_DOS_BINARIOS_PADRAO = "bin"
SUFIXO_DO_EXECUTAVEL = {SISTEMA_WINDOWS: ".exe"}

TOCADORES = (
    ("pw-play", ()),
    ("paplay", ()),
    ("mpv", ("--no-video", "--really-quiet")),
    ("ffplay", ("-nodisp", "-autoexit", "-loglevel", "quiet")),
    ("mpg123", ("-q",)),
)

RESERVA_DO_LINUX = "spd-say"
RITMO_DA_RESERVA = "-25"
RESERVA_DO_MAC = "say"

APELIDO_DO_MCI = "falar"
ABRIR_NO_MCI = 'open "{}" type mpegvideo alias {}'
TOCAR_NO_MCI = "play {} wait"
FECHAR_NO_MCI = "close {}"
MCI_DEU_CERTO = 0

SAIDA_OK = 0
SAIDA_SEM_VOZ = 3

LOG_DESLIGADA = "voz desligada em voz.json — nada falado"
LOG_CRIANDO_O_VENV = "criando o venv da voz em {} e instalando " + PACOTE_DO_MOTOR
LOG_MOTOR_NAO_INSTALOU = "motor neural indisponível ({}) — indo para a reserva"
LOG_SEM_VOZ = (
    "nada falou: nem o motor neural nem a reserva offline responderam")
CONFIGURACAO_INVALIDA = "configuração inválida em {}: {}"
RODANDO_NA_FONTE = (
    "este é o falar.py da FONTE do módulo, em modulos/{}/ — rodá-lo aqui "
    "criaria o venv dentro da fonte, e o montar.py embutiria o venv "
    "inteiro. Instale primeiro: python montar.py --modulo {} no "
    "repositório de destino, e rode a cópia de lá.")


def esta_na_fonte_do_modulo(pasta: Path = AQUI) -> bool:
    for base in pasta.parents:
        if (base.name == NOME_DO_MODULO
                and base.parent.name == PASTA_DA_FONTE_DE_MODULOS):
            return True
    return False


def valor_declarado(valor) -> bool:
    if not isinstance(valor, str):
        return True
    return bool(valor.strip()) and MARCA_DE_PLACEHOLDER not in valor


def configuracao_de_texto(texto: str) -> dict:
    escolhida = dict(PADRAO)
    if not texto.strip():
        return escolhida
    for chave, valor in json.loads(texto).items():
        if chave in PADRAO and valor_declarado(valor):
            escolhida[chave] = valor
    return escolhida


def ler_a_configuracao(caminho: Path = ARQUIVO_DA_CONFIGURACAO) -> dict:
    if not caminho.is_file():
        return dict(PADRAO)
    try:
        return configuracao_de_texto(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError as erro:
        sys.exit(CONFIGURACAO_INVALIDA.format(caminho, erro))


def frase_com_tratamento(texto: str, tratamento: str) -> str:
    if not tratamento.strip():
        return texto
    return f"{tratamento}, {texto}"


def idioma_da_voz(voz: str) -> str:
    return SEPARADOR_DA_VOZ.join(
        voz.split(SEPARADOR_DA_VOZ)[:PARTES_DO_IDIOMA])


def executavel_no_venv(pasta_do_venv: Path, nome: str, sistema: str) -> Path:
    binarios = PASTA_DOS_BINARIOS.get(sistema, PASTA_DOS_BINARIOS_PADRAO)
    return pasta_do_venv / binarios / (
        nome + SUFIXO_DO_EXECUTAVEL.get(sistema, ""))


def comando_do_motor(executavel: Path, conf: dict, frase: str,
                     destino: Path) -> list:
    return [str(executavel), "-v", conf[CHAVE_VOZ],
            f"--rate={conf[CHAVE_RITMO]}", "--text", frase,
            "--write-media", str(destino)]


def comando_do_tocador(arquivo: Path, achar=shutil.which) -> list:
    for nome, argumentos in TOCADORES:
        if (caminho := achar(nome)):
            return [caminho, *argumentos, str(arquivo)]
    return []


def comando_da_reserva(frase: str, idioma: str, sistema: str) -> list:
    if sistema == SISTEMA_LINUX:
        return [RESERVA_DO_LINUX, "-w", "-l", idioma, "-r",
                RITMO_DA_RESERVA, frase]
    if sistema == SISTEMA_MAC:
        return [RESERVA_DO_MAC, frase]
    return []


def instalar_o_motor(pasta_do_venv: Path, sistema: str) -> bool:
    pip = executavel_no_venv(pasta_do_venv, EXECUTAVEL_DO_PIP, sistema)
    passos = ([sys.executable, "-m", "venv", str(pasta_do_venv)],
              [str(pip), "install", "--quiet", PACOTE_DO_MOTOR])
    for comando in passos:
        concluido = subprocess.run(comando, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if concluido.returncode != 0:
            print(LOG_MOTOR_NAO_INSTALOU.format(
                concluido.stderr.strip()[:TETO_DO_ERRO]))
            return False
    return True


def garantir_o_motor(pasta_do_venv: Path, sistema: str):
    executavel = executavel_no_venv(pasta_do_venv, EXECUTAVEL_DO_MOTOR,
                                    sistema)
    if executavel.is_file():
        return executavel
    print(LOG_CRIANDO_O_VENV.format(pasta_do_venv))
    if not instalar_o_motor(pasta_do_venv, sistema):
        return None
    return executavel if executavel.is_file() else None


def tocar_no_windows(arquivo: Path) -> bool:
    mci = ctypes.windll.winmm.mciSendStringW
    if mci(ABRIR_NO_MCI.format(arquivo, APELIDO_DO_MCI), None, 0,
           None) != MCI_DEU_CERTO:
        return False
    tocou = mci(TOCAR_NO_MCI.format(APELIDO_DO_MCI), None, 0,
                None) == MCI_DEU_CERTO
    mci(FECHAR_NO_MCI.format(APELIDO_DO_MCI), None, 0, None)
    return tocou


def tocar(arquivo: Path, sistema: str) -> bool:
    if sistema == SISTEMA_WINDOWS:
        return tocar_no_windows(arquivo)
    comando = comando_do_tocador(arquivo)
    if not comando:
        return False
    return subprocess.run(comando, capture_output=True).returncode == 0


def falar_pelo_motor(frase: str, conf: dict, sistema: str) -> bool:
    executavel = garantir_o_motor(PASTA_DO_VENV, sistema)
    if executavel is None:
        return False
    descritor, caminho = tempfile.mkstemp(prefix=PREFIXO_DO_AUDIO,
                                          suffix=SUFIXO_DO_AUDIO)
    os.close(descritor)
    destino = Path(caminho)
    try:
        gerou = subprocess.run(
            comando_do_motor(executavel, conf, frase, destino),
            capture_output=True).returncode == 0
        return gerou and destino.stat().st_size > 0 and tocar(destino,
                                                              sistema)
    finally:
        destino.unlink(missing_ok=True)


def falar_pela_reserva(frase: str, conf: dict, sistema: str) -> bool:
    comando = comando_da_reserva(frase, idioma_da_voz(conf[CHAVE_VOZ]),
                                 sistema)
    if not comando or not shutil.which(comando[0]):
        return False
    return subprocess.run(comando, capture_output=True).returncode == 0


def falar(texto: str, conf: dict, sistema: str = "",
          pelo_motor=falar_pelo_motor, pela_reserva=falar_pela_reserva) -> int:
    sistema = sistema or platform.system()
    if not conf[CHAVE_LIGADA]:
        print(LOG_DESLIGADA)
        return SAIDA_OK
    frase = frase_com_tratamento(texto, conf[CHAVE_TRATAMENTO])
    if pelo_motor(frase, conf, sistema):
        return SAIDA_OK
    if pela_reserva(frase, conf, sistema):
        return SAIDA_OK
    print(LOG_SEM_VOZ)
    return SAIDA_SEM_VOZ


def testar() -> int:
    rodados, falhas = [], []

    def caso(nome: str, deu_certo: bool):
        rodados.append(nome)
        if not deu_certo:
            falhas.append(nome)

    caso("sem arquivo no disco, vale o padrão",
         ler_a_configuracao(AQUI / "nao-existe.json") == PADRAO)

    caso("o placeholder da configuração não vira valor",
         configuracao_de_texto('{"tratamento": "${COMO_CHAMAR}"}')[
             CHAVE_TRATAMENTO] == "")

    caso("o valor do disco vence o padrão",
         configuracao_de_texto('{"voz": "pt-BR-AntonioNeural"}')[
             CHAVE_VOZ] == "pt-BR-AntonioNeural")

    caso("desligar é booleano e atravessa o filtro de texto",
         configuracao_de_texto('{"ligada": false}')[CHAVE_LIGADA] is False)

    caso("chave que a camada não conhece é ignorada",
         "inventada" not in configuracao_de_texto('{"inventada": 1}'))

    caso("tratamento declarado abre a frase",
         frase_com_tratamento("subiu", "chefe") == "chefe, subiu")

    caso("tratamento vazio não põe vírgula em ninguém",
         frase_com_tratamento("subiu", "  ") == "subiu")

    caso("o idioma da reserva sai da voz do motor",
         idioma_da_voz("pt-BR-FranciscaNeural") == "pt-BR")

    caso("o comando do motor leva voz e ritmo da configuração",
         comando_do_motor(Path("/e/edge-tts"), PADRAO, "oi", Path("/t.mp3"))
         == ["/e/edge-tts", "-v", "pt-BR-FranciscaNeural", "--rate=-8%",
             "--text", "oi", "--write-media", "/t.mp3"])

    caso("o tocador é o primeiro da lista que existe no disco",
         comando_do_tocador(Path("/t.mp3"),
                            achar=lambda n: "/usr/bin/mpv"
                            if n == "mpv" else None)
         == ["/usr/bin/mpv", "--no-video", "--really-quiet", "/t.mp3"])

    caso("sem tocador nenhum, o comando sai vazio, não sai errado",
         comando_do_tocador(Path("/t.mp3"), achar=lambda n: None) == [])

    caso("a reserva do Linux leva o idioma da voz",
         comando_da_reserva("oi", "pt-BR", SISTEMA_LINUX)
         == [RESERVA_DO_LINUX, "-w", "-l", "pt-BR", "-r", RITMO_DA_RESERVA,
             "oi"])

    caso("Windows não tem reserva offline declarada — lacuna confessada",
         comando_da_reserva("oi", "pt-BR", SISTEMA_WINDOWS) == [])

    caso("no Windows o executável do motor muda de pasta e ganha sufixo",
         executavel_no_venv(Path("/v"), EXECUTAVEL_DO_MOTOR, SISTEMA_WINDOWS)
         == Path("/v/Scripts/edge-tts.exe"))

    caso("no Linux o executável do motor fica em bin, sem sufixo",
         executavel_no_venv(Path("/v"), EXECUTAVEL_DO_MOTOR, SISTEMA_LINUX)
         == Path("/v/bin/edge-tts"))

    desligada = dict(PADRAO, ligada=False)
    tentativas = []

    def anotar(valor):
        def motor(frase, conf, sistema):
            tentativas.append(frase)
            return valor
        return motor

    caso("voz desligada sai zero sem tentar motor nenhum",
         falar("oi", desligada, SISTEMA_LINUX, anotar(True), anotar(True))
         == SAIDA_OK and tentativas == [])

    caso("motor que fala encerra antes da reserva",
         falar("oi", PADRAO, SISTEMA_LINUX, anotar(True), anotar(True))
         == SAIDA_OK and tentativas == ["oi"])

    tentativas.clear()
    caso("motor mudo cai na reserva, e a reserva ouve a mesma frase",
         falar("oi", PADRAO, SISTEMA_LINUX, anotar(False), anotar(True))
         == SAIDA_OK and tentativas == ["oi", "oi"])

    caso("sem motor e sem reserva, a saída é diferente de zero",
         falar("oi", PADRAO, SISTEMA_LINUX, anotar(False), anotar(False))
         == SAIDA_SEM_VOZ)

    caso("o falar.py da fonte do módulo se reconhece",
         esta_na_fonte_do_modulo(
             Path("/w/modulos/voz/.agents/voz")) is True)

    caso("o falar.py instalado não se confunde com a fonte",
         esta_na_fonte_do_modulo(Path("/w/.agents/voz")) is False)

    if falhas:
        for falha in falhas:
            print(f"  [{falha}]")
        print(f"FALHOU: {len(falhas)} de {len(rodados)} casos")
        return 1
    print(f"OK: {len(rodados)} casos — configuração, motor, tocador, reserva")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=DESCRICAO_DA_CLI)
    ap.add_argument("texto", nargs="+", help="o que falar")
    a = ap.parse_args()
    if esta_na_fonte_do_modulo():
        sys.exit(RODANDO_NA_FONTE.format(NOME_DO_MODULO, NOME_DO_MODULO))
    return falar(" ".join(a.texto), ler_a_configuracao())


if __name__ == "__main__":
    sys.exit(testar() if BANDEIRA_DE_TESTE in sys.argv[1:] else main())
