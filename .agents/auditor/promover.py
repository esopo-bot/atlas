import argparse
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

import auditor

DESCRICAO_DA_CLI = (
    "audita a execução de um trabalho e põe na caixa cada achado que o "
    "auditor sabe nomear — a colheita de melhoria deste repositório. Fica "
    "aqui: quem instala recebe o auditor que verifica e acusa, sem bandeira "
    "para ligar a promoção")
BANDEIRA_DE_TESTE = "--testar"
TEMPO_DA_CAIXA = 120
CAIXA = auditor._achar_a_camada() / "caixa/caixa.py"
CODIGO_DE_PROMOCAO_INCOMPLETA = 2

TITULO_PROMOVIDO = "PROMOVIDO — o achado que virou linha na caixa"
LINHA_SIMPLES = "  {}"
ASSUNTO_DO_ACHADO = "{trabalho}: {texto}"
NADA_A_PROMOVER = ("nada: dos supostos acima, nenhum é dos que o auditor sabe "
                   "nomear — os outros ficam só impressos")
CAIXA_AUSENTE = ("instrumento da caixa não encontrado em {} — nada foi "
                 "promovido, e isso é não promovido, não é caixa vazia")
FALHOU_AO_PROMOVER = "não promovi {}: {}"

FALSA_CAIXA = """import os
import sys
from pathlib import Path

with Path(os.environ["PROMOVER_TESTE_LOG"]).open("a", encoding="utf-8") as log:
    log.write(" ".join(sys.argv[1:]).replace(chr(10), " ") + chr(10))
sys.exit(2 if os.environ.get("PROMOVER_TESTE_RECUSA") else 0)
"""


def promover(trabalho: str, nomeados: list, cwd: str = "") -> tuple:
    if not CAIXA.is_file():
        return False, [CAIXA_AUSENTE.format(CAIXA)]
    recados, inteiro = [], True
    for um in nomeados:
        comando = [sys.executable, str(CAIXA), um["tipo"], "--id", um["id"],
                   "--assunto", ASSUNTO_DO_ACHADO.format(trabalho=trabalho,
                                                         texto=um["texto"])]
        if cwd:
            comando += ["--cwd", cwd]
        try:
            feito = subprocess.run(comando, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                   timeout=TEMPO_DA_CAIXA)
        except (OSError, subprocess.SubprocessError) as erro:
            recados.append(FALHOU_AO_PROMOVER.format(um["id"], erro))
            inteiro = False
            continue
        if feito.returncode != 0:
            inteiro = False
        recados.append((feito.stdout + feito.stderr).strip()
                       or FALHOU_AO_PROMOVER.format(um["id"],
                                                    feito.returncode))
    return inteiro, recados


def auditar_e_promover(pasta: Path, cwd: str = "") -> int:
    codigo, nomeados = auditor.auditar_e_nomear(pasta, cwd)
    print(f"\n{TITULO_PROMOVIDO}")
    if not nomeados:
        print(LINHA_SIMPLES.format(NADA_A_PROMOVER))
        return codigo
    inteiro, recados = promover(pasta.name, nomeados, cwd)
    for recado in recados:
        print(LINHA_SIMPLES.format(recado))
    return codigo if inteiro else CODIGO_DE_PROMOCAO_INCOMPLETA


def testar() -> int:
    import contextlib
    import io
    import os
    import tempfile
    global CAIXA
    falhas, rodados = [], []

    def caso(rotulo, condicao):
        rodados.append(rotulo)
        if not condicao:
            falhas.append(rotulo)

    nomeados = [
        {"id": auditor.ACHADO_PROVA_NAO_REPRODUZ, "tipo": auditor.TIPO_DEFEITO,
         "texto": "a prova declarada dá outra coisa"},
        {"id": auditor.ACHADO_CICLO_REPETIDO, "tipo": auditor.TIPO_MELHORIA,
         "texto": "duas etapas gastaram mais de um ciclo"},
    ]
    guardada = CAIXA
    with tempfile.TemporaryDirectory(prefix="promover-teste-") as pasta:
        registro = Path(pasta) / "registro.txt"
        CAIXA = Path(pasta) / "falsa_caixa.py"
        CAIXA.write_text(FALSA_CAIXA, encoding="utf-8")
        os.environ["PROMOVER_TESTE_LOG"] = str(registro)
        try:
            registro.write_text("", encoding="utf-8")
            inteiro, recados = promover("suja", nomeados)
            chamadas = registro.read_text(encoding="utf-8").splitlines()
            caso("chama a caixa uma vez por achado nomeado",
                 inteiro and len(chamadas) == len(nomeados))
            caso("o assunto promovido diz de qual trabalho veio",
                 all("suja:" in uma for uma in chamadas))
            caso("a identidade não carrega o trabalho: é estável entre eles",
                 sum(1 for uma in chamadas
                     if "--id " + auditor.ACHADO_PROVA_NAO_REPRODUZ in uma)
                 == 1)
            caso("o tipo do achado vira a ação da caixa",
                 chamadas[0].startswith(auditor.TIPO_DEFEITO)
                 and chamadas[1].startswith(auditor.TIPO_MELHORIA))

            os.environ["PROMOVER_TESTE_RECUSA"] = "1"
            inteiro, _ = promover("suja", nomeados)
            caso("caixa que recusa deixa a promoção incompleta",
                 not inteiro)
            os.environ.pop("PROMOVER_TESTE_RECUSA")

            CAIXA = Path(pasta) / "nao-existe.py"
            inteiro, recados = promover("suja", nomeados)
            caso("caixa ausente é não promovido, não é caixa vazia",
                 not inteiro and recados == [CAIXA_AUSENTE.format(CAIXA)])

            vazia = Path(pasta) / "vazia"
            vazia.mkdir()
            with contextlib.redirect_stdout(io.StringIO()):
                codigo_da_vazia = auditar_e_promover(vazia)
            caso("pasta sem evidência não promove e devolve o código do "
                 "auditor", codigo_da_vazia == 2)
        finally:
            CAIXA = guardada
            os.environ.pop("PROMOVER_TESTE_LOG", None)

    total = len(rodados)
    if falhas:
        for falha in falhas:
            print(f"  [{falha}]")
        print(f"FALHOU: {len(falhas)} de {total} casos")
        return 1
    print(f"OK: {total} casos — promoção do achado nomeado para a caixa")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=DESCRICAO_DA_CLI)
    ap.add_argument("pasta", help="a pasta de evidências de um trabalho")
    ap.add_argument("--cwd", default="",
                    help="onde re-executar as provas (padrão: aqui)")
    a = ap.parse_args()
    return auditar_e_promover(Path(a.pasta), a.cwd)


if __name__ == "__main__":
    sys.exit(testar() if BANDEIRA_DE_TESTE in sys.argv else main())
