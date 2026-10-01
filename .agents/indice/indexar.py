import argparse
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

BANDEIRA_DE_TESTE = "--testar"
USO = ("indexa o acervo pelo ck no modo léxico, um alvo por vez: o índice é "
       "arquivo dentro de cada alvo, sem serviço de pé e sem modelo baixado. "
       "Antes do primeiro índice de um alvo com git, põe .ck/ e .ckignore no "
       ".git/info/exclude dele quando o git ainda não os ignora")

ARQUIVO_DOS_ALVOS = ".agents/indice/alvos.json"
CAMPO_DOS_ALVOS = "alvos"
CAMPO_DO_LIGADO = "ligado"
ARQUIVO_DA_ULTIMA_RONDA = ".agents/indice/ultima-ronda.json"
ARQUIVO_DO_INDICE_DO_CK = "manifest.json"
CAMPO_DO_CARIMBO = "updated"
PERGUNTA_QUE_DISPARA_O_INDICE = "indice"
BUSCADOR_IRMAO = "buscar.py"
NOME_DO_BUSCADOR_IRMAO = "buscar_do_indice"
TEMPO_POR_ALVO = 1800
TEMPO_DA_RONDA = 300
TEMPO_DA_VERSAO = 30
META_DO_JA_ESTAVA_EM_SEGUNDOS = 5
CODIGO_DA_INTERRUPCAO = 130

RONDA_DESLIGADA = ("índice desligado em {}: nada a indexar. Ligue com "
                   "`indexar.py --ligar` quando quiser a ronda no ritual")
LIGADO = "índice LIGADO em {}: a ronda indexa o que mudou em {} alvo(s)"
DESLIGADO = "índice desligado em {}: a ronda não roda"
MOTOR_DE_PE = "motor: {} em {}, modo léxico — nenhum serviço de pé"
SEM_O_CK = ("o `ck` não está no PATH: a ronda não indexa e a busca cai no "
            "grep. Para instalar: {}")
ESTADO_DA_ULTIMA_RONDA = ("última ronda em {quando}: {feitos} indexado(s), "
                          "{pulados} já estava(m), {sem_elegivel} sem arquivo "
                          "elegível, {falharam} falhou(ram), em {duracao}")
SEM_RONDA_AINDA = "nenhuma ronda registrada ainda"
CAMPO_DOS_QUE_FALHARAM = "quais_falharam"
QUAIS_FALHARAM = "  falhou(ram): {quais}"
ALVO_AUSENTE_NAO_MEDIDO = ("  não medido: {} não existe no disco — alvo "
                           "declarado em outra árvore; a ronda segue sem ele")
NENHUM_ALVO_NO_DISCO = ("nenhum alvo declarado existe nesta árvore: a ronda "
                        "não mediu nada")
RECUSA_SEM_ALVOS = ("sem alvos: declare `{}` com a lista de caminhos a "
                    "indexar. O instrumento não adivinha o que é acervo")
CABECA_DO_ENSAIO = "ENSAIO — {} alvo(s), nada será indexado:"
LINHA_DO_ENSAIO = "  {} — {}; {}"
COM_INDICE = "índice de {}"
SEM_INDICE = "sem índice ainda"
GIT_JA_IGNORA = "o git dele já ignora .ck/ e .ckignore"
GIT_VAI_RECEBER = "o .git/info/exclude dele recebe .ck/ e .ckignore"
SEM_GIT = "sem git: nada além do .ck/"
CABECA_DA_RODADA = "indexando {} alvo(s) pelo ck, modo léxico"
LINHA_DO_FIM = "  [{}/{}] {} — {} em {}"
FEITO = "indexado"
ATUALIZADO = "atualizado"
JA_ESTAVA = "já estava indexado"
FALHOU = "FALHOU"
LINHA_DO_ERRO = "        {}"
LIMPO_ANTES = "  {} — índice anterior apagado pelo `ck --clean`, para refazer"
SEM_INDICE_PROPRIO = ("  {} — o índice que responde mora acima dele; "
                      "`--refazer` não apaga o índice de outro alvo")
RESUMO_COM_PULADOS = ("{} indexado(s), {} já estava(m), {} pulado(s) sem arquivo "
                      "elegível, {} falhou(ram), em {}")
META_CUMPRIDA = "o já estava levou {:.2f} s — meta: menos de {} s"
META_ESTOURADA = ("ACIMA DA META: o já estava levou {:.2f} s, e a meta é "
                  "menos de {} s")
INTERROMPIDO = "interrompido: o que ficou pela metade o ck refaz na próxima ronda"


def buscador_irmao():
    caminho = Path(__file__).resolve().with_name(BUSCADOR_IRMAO)
    origem = importlib.util.spec_from_file_location(NOME_DO_BUSCADOR_IRMAO,
                                                    caminho)
    modulo = importlib.util.module_from_spec(origem)
    origem.loader.exec_module(modulo)
    return modulo


BUSCA = buscador_irmao()


def duracao(segundos: float) -> str:
    return f"{segundos / 60:.1f} min" if segundos >= 60 else f"{segundos:.1f}s"


def configuracao(cwd: str = "") -> dict:
    alvo = Path(cwd or ".") / ARQUIVO_DOS_ALVOS
    try:
        return json.loads(alvo.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def gravar_configuracao(dado: dict, cwd: str = "") -> None:
    alvo = Path(cwd or ".") / ARQUIVO_DOS_ALVOS
    alvo.write_text(json.dumps(dado, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


def esta_ligado(dado: dict) -> bool:
    return bool(dado.get(CAMPO_DO_LIGADO))


def estado_em_uma_linha(dado: dict) -> str:
    if esta_ligado(dado):
        return LIGADO.format(ARQUIVO_DOS_ALVOS,
                             len(dado.get(CAMPO_DOS_ALVOS) or []))
    return DESLIGADO.format(ARQUIVO_DOS_ALVOS)


def ligar(dado: dict, cwd: str, ligado: bool) -> int:
    dado[CAMPO_DO_LIGADO] = ligado
    gravar_configuracao(dado, cwd)
    print(estado_em_uma_linha(dado))
    return 0


def ultima_ronda(cwd: str = ""):
    alvo = Path(cwd or ".") / ARQUIVO_DA_ULTIMA_RONDA
    try:
        return json.loads(alvo.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def gravar_ultima_ronda(cwd: str, resumo: dict) -> None:
    alvo = Path(cwd or ".") / ARQUIVO_DA_ULTIMA_RONDA
    alvo.parent.mkdir(parents=True, exist_ok=True)
    alvo.write_text(json.dumps(resumo, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


def versao_do_ck(ck: str) -> str:
    try:
        feito = subprocess.run([ck, "--version"], capture_output=True,
                               text=True, encoding="utf-8", errors="replace",
                               timeout=TEMPO_DA_VERSAO)
    except (OSError, subprocess.SubprocessError):
        return BUSCA.PROGRAMA_DO_CK
    return feito.stdout.strip() or BUSCA.PROGRAMA_DO_CK


def estado(dado: dict, cwd: str, localizar=None) -> int:
    print(estado_em_uma_linha(dado))
    ck = (localizar or BUSCA.o_ck)()
    print(MOTOR_DE_PE.format(versao_do_ck(ck), ck) if ck
          else SEM_O_CK.format(BUSCA.COMO_INSTALAR_O_CK))
    registro = ultima_ronda(cwd)
    print(ESTADO_DA_ULTIMA_RONDA.format(**registro) if registro
          else SEM_RONDA_AINDA)
    if registro and registro.get(CAMPO_DOS_QUE_FALHARAM):
        print(QUAIS_FALHARAM.format(
            quais=", ".join(registro[CAMPO_DOS_QUE_FALHARAM])))
    return 0 if ck or not esta_ligado(dado) else 1


def indice_que_responde(pasta: Path):
    for lugar in (pasta, *pasta.parents):
        manifesto = lugar / BUSCA.PASTA_DO_INDICE_DO_CK / ARQUIVO_DO_INDICE_DO_CK
        if manifesto.is_file():
            return manifesto
    return None


def carimbo(pasta: Path):
    manifesto = indice_que_responde(pasta)
    if manifesto is None:
        return None
    try:
        return json.loads(manifesto.read_text(encoding="utf-8")).get(
            CAMPO_DO_CARIMBO)
    except (OSError, json.JSONDecodeError):
        return None


def presentes(alvos: list) -> list:
    achados = [p for p in alvos if p.is_dir()]
    for ausente in [p for p in alvos if not p.is_dir()]:
        print(ALVO_AUSENTE_NAO_MEDIDO.format(ausente))
    return achados


def git_do_alvo(pasta: Path) -> str:
    if not BUSCA.dentro_do_git(pasta):
        return SEM_GIT
    ignora = all(BUSCA.ignorado_pelo_git(pasta, amostra) for amostra
                 in BUSCA.AMOSTRAS_DO_QUE_O_CK_GRAVA.values())
    return GIT_JA_IGNORA if ignora else GIT_VAI_RECEBER


def ensaiar(alvos: list) -> int:
    print(CABECA_DO_ENSAIO.format(len(alvos)))
    for pasta in alvos:
        visto = carimbo(pasta)
        indice = (COM_INDICE.format(time.strftime(
            "%Y-%m-%d %H:%M", time.localtime(visto))) if visto
            else SEM_INDICE)
        print(LINHA_DO_ENSAIO.format(pasta, indice, git_do_alvo(pasta)))
    return 0


def refazer_o_alvo(ck: str, pasta: Path) -> None:
    if not (pasta / BUSCA.PASTA_DO_INDICE_DO_CK).is_dir():
        if indice_que_responde(pasta):
            print(SEM_INDICE_PROPRIO.format(pasta), flush=True)
        return
    subprocess.run([ck, "--clean", "."], capture_output=True, text=True,
                   encoding="utf-8", errors="replace",
                   timeout=TEMPO_DA_VERSAO, cwd=str(pasta))
    print(LIMPO_ANTES.format(pasta), flush=True)


def indexar_um_alvo(ck: str, pasta: Path, teto: int, exclusoes) -> tuple:
    recado = BUSCA.esconder_do_git(pasta)
    if recado:
        print(recado, flush=True)
    antes = carimbo(pasta)
    try:
        feito = subprocess.run(
            [ck, "--lex", "-q", "--topk", "1", *exclusoes,
             PERGUNTA_QUE_DISPARA_O_INDICE, str(pasta)],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=teto, cwd=str(pasta))
    except subprocess.TimeoutExpired:
        return FALHOU, f"não terminou em {duracao(teto)}"
    except OSError as erro:
        return FALHOU, f"{type(erro).__name__}: {erro}"
    saida = (feito.stderr + feito.stdout).strip()
    if feito.returncode not in (0, 1) or (
            feito.returncode == 1 and BUSCA.SEM_ACHADO_NO_CK not in saida):
        return FALHOU, saida[-300:] or f"o ck saiu {feito.returncode}"
    depois = carimbo(pasta)
    if depois is None:
        return FALHOU, "o ck saiu sem gravar o índice"
    if antes is None:
        return FEITO, ""
    return (ATUALIZADO if depois != antes else JA_ESTAVA), ""


def indexar(dado: dict, alvos: list, teto: int, refazer: bool = False,
            cwd: str = "", localizar=None) -> int:
    ck = (localizar or BUSCA.o_ck)()
    if not ck:
        print(SEM_O_CK.format(BUSCA.COMO_INSTALAR_O_CK), file=sys.stderr)
        return 1
    print(CABECA_DA_RODADA.format(len(alvos)), flush=True)
    exclusoes = BUSCA.exclusoes_do_ck(dado)
    feitos = pulados = 0
    quem_falhou = []
    comeco_da_rodada = time.monotonic()
    try:
        for i, pasta in enumerate(alvos, 1):
            if refazer:
                refazer_o_alvo(ck, pasta)
            comeco = time.monotonic()
            dito, erro = indexar_um_alvo(ck, pasta, teto, exclusoes)
            print(LINHA_DO_FIM.format(i, len(alvos), pasta, dito,
                                      duracao(time.monotonic() - comeco)),
                  flush=True)
            if erro:
                print(LINHA_DO_ERRO.format(erro), flush=True)
            feitos += 1 if dito in (FEITO, ATUALIZADO) else 0
            pulados += 1 if dito == JA_ESTAVA else 0
            if dito == FALHOU:
                quem_falhou.append(str(pasta))
    except KeyboardInterrupt:
        print(INTERROMPIDO, file=sys.stderr)
        return CODIGO_DA_INTERRUPCAO
    segundos = time.monotonic() - comeco_da_rodada
    print(RESUMO_COM_PULADOS.format(feitos, pulados, 0, len(quem_falhou),
                                    duracao(segundos)))
    gravar_ultima_ronda(cwd, {
        "quando": time.strftime("%Y-%m-%dT%H:%M:%S"), "feitos": feitos,
        "pulados": pulados, "sem_elegivel": 0,
        "falharam": len(quem_falhou), CAMPO_DOS_QUE_FALHARAM: quem_falhou,
        "duracao": duracao(segundos)})
    if quem_falhou:
        return 1
    if feitos == 0:
        estourou = segundos >= META_DO_JA_ESTAVA_EM_SEGUNDOS
        print((META_ESTOURADA if estourou else META_CUMPRIDA).format(
            segundos, META_DO_JA_ESTAVA_EM_SEGUNDOS))
        return 1 if estourou else 0
    return 0


def testar() -> int:
    import contextlib
    import io
    import os
    import tempfile
    falhas, rodados = [], []

    def caso(rotulo, passou):
        rodados.append(rotulo)
        if not passou:
            falhas.append(rotulo)

    def saida_de(funcao, *argumentos, **nomeados):
        fora = io.StringIO()
        with contextlib.redirect_stdout(fora), \
                contextlib.redirect_stderr(fora):
            codigo = funcao(*argumentos, **nomeados)
        return codigo, fora.getvalue()

    sem_ck = lambda: ""
    with tempfile.TemporaryDirectory(prefix="indexar-") as base:
        base = Path(base)
        codigo, dito = saida_de(estado, {"ligado": True}, str(base),
                                localizar=sem_ck)
        caso("sem o ck, o --estado diz que ele falta e como instalar, e sai 1 "
             "com o índice ligado",
             codigo == 1 and "não está no PATH" in dito
             and "BeaconBay/ck" in dito)
        codigo, _ = saida_de(estado, {"ligado": False}, str(base),
                             localizar=sem_ck)
        caso("desligado, a falta do ck não reprova o --estado", codigo == 0)
        codigo, dito = saida_de(indexar, {}, [base], 10, cwd=str(base),
                                localizar=sem_ck)
        caso("sem o ck, a ronda ligada não indexa e diz como instalar",
             codigo == 1 and "BeaconBay/ck" in dito
             and not (base / BUSCA.PASTA_DO_INDICE_DO_CK).exists())

        acima = base / "acima"
        (acima / BUSCA.PASTA_DO_INDICE_DO_CK).mkdir(parents=True)
        (acima / BUSCA.PASTA_DO_INDICE_DO_CK / ARQUIVO_DO_INDICE_DO_CK
         ).write_text(json.dumps({"updated": 7}), encoding="utf-8")
        (acima / "sub").mkdir()
        caso("o carimbo de uma subpasta é o do índice que responde acima dela",
             carimbo(acima / "sub") == 7 and carimbo(base) is None)

        ck = BUSCA.o_ck()
        if not ck:
            print("não medido: o ck não está no PATH — a ronda real não rodou")
        else:
            vizinho = base / "vizinho"
            (vizinho / "docs").mkdir(parents=True)
            (vizinho / "docs" / "a.md").write_text(
                "A regra dezesseis cobra destino.\n", encoding="utf-8")
            for argumentos in (("init", "-q"), ("add", "."),
                               ("-c", "user.email=a@b", "-c", "user.name=a",
                                "commit", "-qm", "x")):
                BUSCA.git_da_pasta(vizinho, *argumentos)
            casa = Path(os.environ.get("USERPROFILE") or Path.home())
            modelos = [casa / ".cache" / "ck",
                       Path(os.environ.get("LOCALAPPDATA") or casa) / "ck"]
            havia = [m.exists() for m in modelos]
            codigo, dito = saida_de(indexar, {}, [vizinho], 60,
                                    cwd=str(base))
            _, status = BUSCA.git_da_pasta(vizinho, "status", "--short")
            caso("a primeira ronda indexa o vizinho e o git dele fica limpo",
                 codigo == 0 and FEITO in dito and status.strip() == ""
                 and ultima_ronda(str(base))["feitos"] == 1)
            codigo, dito = saida_de(indexar, {}, [vizinho], 60,
                                    cwd=str(base))
            caso("a segunda ronda diz já estava, dentro da meta de tempo",
                 codigo == 0 and JA_ESTAVA in dito and "meta" in dito
                 and ultima_ronda(str(base))["pulados"] == 1)
            caso("nenhuma pasta de modelo do ck nasceu",
                 [m.exists() for m in modelos] == havia)

    if falhas:
        for f in falhas:
            print(f"FALHOU: {f}")
        print(f"FALHOU: {len(falhas)} de {len(rodados)} casos")
        return 1
    print(f"OK: o indexador do índice — {len(rodados)} casos")
    return 0


def montar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=USO)
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--ensaio", action="store_true",
                        help="mostra os alvos e o que cada um recebe, sem "
                             "indexar")
    parser.add_argument("--tempo-limite", type=int, default=TEMPO_POR_ALVO,
                        help="teto em segundos de cada alvo")
    parser.add_argument("--refazer", action="store_true",
                        help="apaga o índice de cada alvo e indexa do zero")
    parser.add_argument("--ligar", action="store_true",
                        help="liga a ronda: o ritual passa a indexar o que "
                             "mudou")
    parser.add_argument("--desligar", action="store_true",
                        help="desliga a ronda sem apagar nada")
    parser.add_argument("--estado", action="store_true",
                        help="diz se está ligado, se o ck está no PATH e "
                             "como foi a última ronda")
    parser.add_argument("--ronda", action="store_true",
                        help="indexa só o que mudou, se ligado; feito para o "
                             "ritual, com teto curto por alvo")
    parser.add_argument(BANDEIRA_DE_TESTE, action="store_true")
    return parser


def main() -> int:
    if BANDEIRA_DE_TESTE in sys.argv[1:]:
        return testar()
    a = montar_parser().parse_args()
    dado = configuracao(a.cwd)
    if a.ligar or a.desligar:
        return ligar(dado, a.cwd, a.ligar)
    if a.estado:
        return estado(dado, a.cwd)
    if a.ronda and not esta_ligado(dado):
        print(RONDA_DESLIGADA.format(ARQUIVO_DOS_ALVOS))
        return 0
    if not dado.get(CAMPO_DOS_ALVOS):
        print(RECUSA_SEM_ALVOS.format(ARQUIVO_DOS_ALVOS), file=sys.stderr)
        return 2
    alvos = presentes(BUSCA.alvos_declarados(dado, a.cwd))
    if not alvos:
        print(NENHUM_ALVO_NO_DISCO)
        return 0
    if a.ensaio:
        return ensaiar(alvos)
    teto = TEMPO_DA_RONDA if a.ronda and a.tempo_limite == TEMPO_POR_ALVO \
        else a.tempo_limite
    return indexar(dado, alvos, teto, a.refazer, a.cwd)


if __name__ == "__main__":
    for canal in (sys.stdin, sys.stdout, sys.stderr):
        if not getattr(canal, "closed", True) and hasattr(canal, "reconfigure"):
            canal.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
