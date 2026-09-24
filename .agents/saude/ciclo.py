import argparse
import contextlib
import shutil
import stat
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

BANDEIRA_DE_TESTE = "--testar"
USO = ("mede o ciclo de edição de fonte — uma linha a mais numa skill, depois "
       "montar.py --sincronizar, --verificar e --testar — em rodadas "
       "alternadas entre um commit de referência e o HEAD, e dá a mediana "
       "por etapa")
INTERPRETADOR = sys.executable
INSTALADOR = "montar.py"
ETAPAS = (
    ("sincronizar", (INTERPRETADOR, INSTALADOR, "--sincronizar")),
    ("verificar", (INTERPRETADOR, INSTALADOR, "--verificar")),
    ("testar", (INTERPRETADOR, INSTALADOR, "--testar")),
)
RODADAS_PADRAO = 3
TEMPO_DE_UMA_ETAPA = 1800
PASTA_DAS_SKILLS = ".agents/skills"
ARQUIVO_DA_SKILL = "SKILL.md"
LINHA_DA_EDICAO = "Linha a mais do medidor do ciclo."
LADO_DA_REFERENCIA = "referência"
LADO_DO_HEAD = "HEAD"
PASTA_DE_CADA_LADO = {LADO_DA_REFERENCIA: "referencia", LADO_DO_HEAD: "head"}
PREFIXO_DA_PASTA = "atlas-ciclo-"
ROTULO_DO_CICLO = "ciclo inteiro"
ROTULO_DOS_SUJOS = "arquivos sujos"
LETRAS_DA_ULTIMA_LINHA = 120
VOLTAS_DA_LIMPEZA = 3
PAUSA_ENTRE_AS_VOLTAS_S = 1.0
FORMATO_DO_TEMPO = ("{:.1f} s", "{:.1f}")
FORMATO_DA_CONTAGEM = ("{:g}", "{:g}")

AJUDA_DA_REFERENCIA = "o commit contra o qual o HEAD é medido"
AJUDA_DAS_RODADAS = f"quantas rodadas de cada lado (padrão: {RODADAS_PADRAO})"
AJUDA_DA_SKILL = (f"a skill que ganha a linha a mais (padrão: a primeira de "
                  f"{PASTA_DAS_SKILLS}/ em ordem)")
RODADAS_DE_MENOS = "--rodadas precisa de pelo menos uma rodada"
FORA_DE_REPOSITORIO = "NÃO MEDIDO: esta pasta não está num repositório git — {}"
SEM_SKILL = f"NÃO MEDIDO: nenhuma skill em {PASTA_DAS_SKILLS}/ para editar"
NAO_MEDIDO_POR = "NÃO MEDIDO: {}"
COMMIT_QUE_NAO_EXISTE = "o commit {} não existe: {}"
WORKTREE_QUE_NAO_MONTOU = "a worktree do lado {} não montou: {}"
SKILL_AUSENTE = "a skill {} não existe no lado {} ({})"
NOMES_QUE_ANDAM_NA_ARVORE = (".", "..")
LETRAS_DE_CAMINHO = ("/", "\\", ":")
SKILL_QUE_NAO_E_NOME = ("--skill {!r} não é nome simples de pasta — sem "
                        "separador, sem drive e sem '..' —, e a linha a mais "
                        "cairia fora das worktrees descartáveis")
SKILL_QUE_NAO_EXISTE = "--skill {!r} não existe em {}/ da raiz"
VOLTA_QUE_FALHOU = "a worktree {} não voltou ao commit — git {}: {}"
REMOCAO_QUE_FALHOU = "AVISO: a worktree {} não saiu pelo git: {}"
PODA_QUE_FALHOU = "AVISO: git worktree prune falhou: {}"
PASTA_QUE_FICOU = ("AVISO: a pasta descartável {} não saiu do disco em {} "
                   "tentativas; a medida vale, o disco ficou com sobra")

CABECALHO = "ciclo de edição da fonte — skill {}, {} rodada(s), referência {}"
LINHA_DA_RODADA = "rodada {} — {}: {}; sujos {}"
PEDACO_DA_ETAPA = "{} {} ({})"
TITULO_DO_LADO = "{} {} — {} rodada(s)"
LINHA_DA_TABELA = "  {:<16} {:>12}   {:<24} {}"
CABECALHO_DA_TABELA = ("etapa", "mediana", "por rodada", "saídas")
NAO_MEDIDO = "não medido"
ESGOTOU = "esgotou"
TITULO_DAS_QUEDAS = "etapas que não saíram 0:"
QUEDA = "  {} saiu {} na rodada {} ({}): {}"
QUEDA_POR_TEMPO = "  {} esgotou {} s na rodada {} ({})"
TODAS_SAIRAM_ZERO = "todas as etapas saíram 0"

FALHA_DO_CASO = "  [{}]"
RESUMO_FALHOU_AQUI = "FALHOU: {} de {} casos"
RESUMO_OK_AQUI = ("OK: {} casos — rodadas alternadas, mediana, etapa que cai "
                  "e worktrees que somem")
SKILL_DE_MENTIRA = "alfa"
SKILL_SO_DO_HEAD = "gama"
CONTA_AS_LINHAS = (
    "import sys; from pathlib import Path; "
    f"linhas = Path('{PASTA_DAS_SKILLS}/{SKILL_DE_MENTIRA}/{ARQUIVO_DA_SKILL}')"
    ".read_text(encoding='utf-8').splitlines(); "
    "sys.exit(0 if len(linhas) == 2 else 3)")
ETAPAS_DE_MENTIRA = (
    ("passa", (INTERPRETADOR, "-c", "pass")),
    ("conta", (INTERPRETADOR, "-c", CONTA_AS_LINHAS)),
    ("cai", (INTERPRETADOR, "-c", "import sys; sys.exit(1)")),
)
AUTORIA_DE_MENTIRA = ("-c", "user.name=teste",
                      "-c", "user.email=t@t",
                      "-c", "commit.gpgsign=false")


def git(pasta, *argumentos) -> tuple:
    r = subprocess.run(["git", "-C", str(pasta), *argumentos],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return r.returncode, (r.stdout if r.returncode == 0
                          else r.stdout + r.stderr).strip()


def skill_padrao(raiz: Path) -> str:
    pasta = raiz / PASTA_DAS_SKILLS
    if not pasta.is_dir():
        return ""
    nomes = sorted(p.name for p in pasta.iterdir()
                   if (p / ARQUIVO_DA_SKILL).is_file())
    return nomes[0] if nomes else ""


def problema_da_skill(raiz: Path, skill: str) -> str:
    if (not skill or skill in NOMES_QUE_ANDAM_NA_ARVORE
            or any(letra in skill for letra in LETRAS_DE_CAMINHO)):
        return SKILL_QUE_NAO_E_NOME.format(skill)
    if not fonte_da_skill(raiz, skill).is_file():
        return SKILL_QUE_NAO_EXISTE.format(skill, PASTA_DAS_SKILLS)
    return ""


def fonte_da_skill(pasta: Path, skill: str) -> Path:
    return pasta / PASTA_DAS_SKILLS / skill / ARQUIVO_DA_SKILL


def montar_os_lados(raiz: Path, referencia: str, skill: str, pasta: Path,
                    criadas: list) -> tuple:
    lados, commits = [], {}
    for lado, pedido in ((LADO_DA_REFERENCIA, referencia),
                         (LADO_DO_HEAD, "HEAD")):
        codigo, commit = git(raiz, "rev-parse", "--verify",
                             f"{pedido}^{{commit}}")
        if codigo != 0:
            return [], commits, COMMIT_QUE_NAO_EXISTE.format(pedido, commit)
        destino = pasta / PASTA_DE_CADA_LADO[lado]
        codigo, saida = git(raiz, "worktree", "add", "--detach",
                            str(destino), commit)
        if codigo != 0:
            return [], commits, WORKTREE_QUE_NAO_MONTOU.format(lado, saida)
        criadas.append(destino)
        if not fonte_da_skill(destino, skill).is_file():
            return [], commits, SKILL_AUSENTE.format(skill, lado, commit[:7])
        lados.append((lado, destino))
        commits[lado] = commit
    return lados, commits, ""


def voltar_ao_commit(destino: Path) -> None:
    for argumentos in (("reset", "-q", "--hard"), ("clean", "-qfd")):
        codigo, saida = git(destino, *argumentos)
        if codigo != 0:
            raise RuntimeError(VOLTA_QUE_FALHOU.format(
                destino, " ".join(argumentos), saida))


def acrescentar_uma_linha(arquivo: Path) -> None:
    conteudo = arquivo.read_bytes()
    fim = b"\r\n" if b"\r\n" in conteudo else b"\n"
    comeco = fim if conteudo and not conteudo.endswith(b"\n") else b""
    arquivo.write_bytes(conteudo + comeco + LINHA_DA_EDICAO.encode("utf-8")
                        + fim)


def ultima_linha(saida: bytes) -> str:
    linhas = [linha for linha in saida.decode("utf-8", errors="replace")
              .splitlines() if linha.strip()]
    return linhas[-1][:LETRAS_DA_ULTIMA_LINHA] if linhas else ""


def cronometrar(argumentos, pasta: Path) -> dict:
    partida = time.monotonic()
    try:
        r = subprocess.run(list(argumentos), cwd=pasta, capture_output=True,
                           timeout=TEMPO_DE_UMA_ETAPA)
    except subprocess.TimeoutExpired:
        return {"segundos": None, "codigo": None, "ultima": ""}
    return {"segundos": time.monotonic() - partida, "codigo": r.returncode,
            "ultima": ultima_linha(r.stdout + r.stderr)}


def contar_sujos(destino: Path):
    codigo, saida = git(destino, "status", "--porcelain")
    if codigo != 0:
        return None
    return len([linha for linha in saida.splitlines() if linha.strip()])


def medir_um_lado(rodada: int, lado: str, destino: Path, skill: str,
                  etapas) -> dict:
    voltar_ao_commit(destino)
    acrescentar_uma_linha(fonte_da_skill(destino, skill))
    medidas = {nome: cronometrar(argumentos, destino)
               for nome, argumentos in etapas}
    return {"rodada": rodada, "lado": lado, "etapas": medidas,
            "sujos": contar_sujos(destino)}


def ordem_da_rodada(rodada: int, lados: list) -> list:
    return lados if rodada % 2 else lados[::-1]


def liberar_o_somente_leitura(pasta: Path) -> None:
    for achado in pasta.rglob("*"):
        with contextlib.suppress(OSError):
            achado.chmod(achado.stat().st_mode | stat.S_IWRITE)


def apagar_a_pasta(pasta: Path) -> bool:
    for volta in range(VOLTAS_DA_LIMPEZA):
        if volta:
            time.sleep(PAUSA_ENTRE_AS_VOLTAS_S)
        liberar_o_somente_leitura(pasta)
        shutil.rmtree(pasta, ignore_errors=True)
        if not pasta.exists():
            return True
    return False


def desmontar(raiz: Path, criadas: list, pasta: Path) -> list:
    avisos = []
    for destino in criadas:
        codigo, saida = git(raiz, "worktree", "remove", "--force",
                            str(destino))
        if codigo != 0:
            avisos.append(REMOCAO_QUE_FALHOU.format(destino, saida))
    if pasta.exists() and not apagar_a_pasta(pasta):
        avisos.append(PASTA_QUE_FICOU.format(pasta, VOLTAS_DA_LIMPEZA))
    codigo, saida = git(raiz, "worktree", "prune")
    if codigo != 0:
        avisos.append(PODA_QUE_FALHOU.format(saida))
    return avisos


def texto_do_valor(valor, formato: str) -> str:
    return NAO_MEDIDO if valor is None else formato.format(valor)


def texto_do_codigo(codigo) -> str:
    return ESGOTOU if codigo is None else str(codigo)


def linha_da_rodada(registro: dict) -> str:
    pedacos = [PEDACO_DA_ETAPA.format(
        nome, texto_do_valor(etapa["segundos"], FORMATO_DO_TEMPO[0]),
        texto_do_codigo(etapa["codigo"]))
        for nome, etapa in registro["etapas"].items()]
    return LINHA_DA_RODADA.format(
        registro["rodada"], registro["lado"], ", ".join(pedacos),
        texto_do_valor(registro["sujos"], FORMATO_DA_CONTAGEM[0]))


def medir(raiz: Path, referencia: str, rodadas: int, skill: str,
          etapas=ETAPAS, relatar=print) -> dict:
    medida = {"commits": {}, "registros": [], "avisos": [], "pasta": None,
              "problema": problema_da_skill(raiz, skill)}
    if medida["problema"]:
        return medida
    pasta = medida["pasta"] = Path(tempfile.mkdtemp(prefix=PREFIXO_DA_PASTA))
    criadas = []
    try:
        lados, medida["commits"], medida["problema"] = montar_os_lados(
            raiz, referencia, skill, pasta, criadas)
        for rodada in range(1, rodadas + 1) if lados else ():
            for lado, destino in ordem_da_rodada(rodada, lados):
                registro = medir_um_lado(rodada, lado, destino, skill, etapas)
                medida["registros"].append(registro)
                relatar(linha_da_rodada(registro))
    finally:
        medida["avisos"] = desmontar(raiz, criadas, pasta)
        for aviso in medida["avisos"]:
            relatar(aviso)
    return medida


def mediana(valores: list):
    medidos = [valor for valor in valores if valor is not None]
    return statistics.median(medidos) if medidos else None


def ciclo_do_registro(registro: dict):
    segundos = [etapa["segundos"] for etapa in registro["etapas"].values()]
    return None if None in segundos else sum(segundos)


def resumo_do_lado(registros: list, nomes: list) -> list:
    series = [(nome, [r["etapas"][nome]["segundos"] for r in registros])
              for nome in nomes]
    series.append((ROTULO_DO_CICLO, [ciclo_do_registro(r) for r in registros]))
    series.append((ROTULO_DOS_SUJOS, [r["sujos"] for r in registros]))
    return [(rotulo, mediana(valores), valores) for rotulo, valores in series]


def tabela_do_lado(lado: str, commit: str, registros: list,
                   nomes: list) -> list:
    linhas = [TITULO_DO_LADO.format(lado, commit[:7], len(registros)),
              LINHA_DA_TABELA.format(*CABECALHO_DA_TABELA)]
    for rotulo, valor, valores in resumo_do_lado(registros, nomes):
        da_mediana, da_rodada = (FORMATO_DA_CONTAGEM
                                 if rotulo == ROTULO_DOS_SUJOS
                                 else FORMATO_DO_TEMPO)
        saidas = (" ".join(texto_do_codigo(r["etapas"][rotulo]["codigo"])
                           for r in registros) if rotulo in nomes else "")
        linhas.append(LINHA_DA_TABELA.format(
            rotulo, texto_do_valor(valor, da_mediana),
            " ".join(texto_do_valor(v, da_rodada) for v in valores),
            saidas).rstrip())
    return linhas


def quedas(registros: list) -> list:
    linhas = []
    for registro in registros:
        for nome, etapa in registro["etapas"].items():
            if etapa["codigo"] is None:
                linhas.append(QUEDA_POR_TEMPO.format(
                    nome, TEMPO_DE_UMA_ETAPA, registro["rodada"],
                    registro["lado"]))
            elif etapa["codigo"] != 0:
                linhas.append(QUEDA.format(
                    nome, etapa["codigo"], registro["rodada"],
                    registro["lado"], etapa["ultima"]))
    return linhas


def relatorio(medida: dict, nomes: list) -> list:
    linhas = []
    for lado in (LADO_DA_REFERENCIA, LADO_DO_HEAD):
        registros = [r for r in medida["registros"] if r["lado"] == lado]
        if registros:
            linhas += tabela_do_lado(lado, medida["commits"].get(lado, ""),
                                     registros, nomes)
    caidas = quedas(medida["registros"])
    return linhas + ([TITULO_DAS_QUEDAS] + caidas if caidas
                     else [TODAS_SAIRAM_ZERO])


def codigo_de_saida(medida: dict) -> int:
    if medida["problema"]:
        return 2
    caiu = any(etapa["codigo"] != 0 for registro in medida["registros"]
               for etapa in registro["etapas"].values())
    return 1 if caiu else 0


def commitar_tudo(raiz: Path, mensagem: str) -> None:
    git(raiz, "add", "-A")
    git(raiz, *AUTORIA_DE_MENTIRA, "commit", "-q", "--no-verify",
        "-m", mensagem)


def montar_o_repositorio_de_mentira(raiz: Path) -> None:
    for nome in ("beta", SKILL_DE_MENTIRA):
        pasta = raiz / PASTA_DAS_SKILLS / nome
        pasta.mkdir(parents=True)
        (pasta / ARQUIVO_DA_SKILL).write_text(f"# {nome}\n", encoding="utf-8")
    git(raiz, "init", "-q")
    commitar_tudo(raiz, "um")
    (raiz / "segundo.txt").write_text("dois\n", encoding="utf-8")
    (raiz / PASTA_DAS_SKILLS / SKILL_SO_DO_HEAD).mkdir(parents=True)
    fonte_da_skill(raiz, SKILL_SO_DO_HEAD).write_text(
        f"# {SKILL_SO_DO_HEAD}\n", encoding="utf-8")
    commitar_tudo(raiz, "dois")


def linhas_do_worktree_list(raiz: Path) -> int:
    codigo, saida = git(raiz, "worktree", "list")
    return len(saida.splitlines()) if codigo == 0 else -1


def registro_de_mentira(rodada: int, segundos_a, segundos_b, sujos) -> dict:
    return {"rodada": rodada, "lado": LADO_DA_REFERENCIA, "sujos": sujos,
            "etapas": {"a": {"segundos": segundos_a, "codigo": 0, "ultima": ""},
                       "b": {"segundos": segundos_b, "codigo": 0,
                             "ultima": ""}}}


def casos_da_mediana(caso) -> None:
    registros = [registro_de_mentira(1, 3.0, 1.0, 2),
                 registro_de_mentira(2, 1.0, 1.0, 5),
                 registro_de_mentira(3, 2.0, 10.0, 2)]
    medianas = {rotulo: valor for rotulo, valor, _
                in resumo_do_lado(registros, ["a", "b"])}
    caso("a mediana de cada etapa sai certa",
         medianas.get("a") == 2.0 and medianas.get("b") == 1.0)
    caso("a mediana do ciclo inteiro é a das somas por rodada, não a soma "
         "das medianas", medianas.get(ROTULO_DO_CICLO) == 4.0)
    caso("a mediana dos arquivos sujos sai certa",
         medianas.get(ROTULO_DOS_SUJOS) == 2)
    caso("etapa que esgotou o tempo não vira zero na mediana",
         mediana([None, 2.0, 4.0]) == 3.0 and mediana([None]) is None)
    caso("medida sem problema e com etapas em 0 sai 0",
         codigo_de_saida({"problema": "", "registros": registros}) == 0)


def casos_da_medida(caso) -> None:
    with tempfile.TemporaryDirectory(prefix="ciclo-teste-") as pasta:
        raiz = Path(pasta) / "repositorio"
        raiz.mkdir()
        montar_o_repositorio_de_mentira(raiz)
        caso("a skill padrão é a primeira de .agents/skills em ordem",
             skill_padrao(raiz) == SKILL_DE_MENTIRA)

        relatado = []
        medida = medir(raiz, "HEAD~1", 2, SKILL_DE_MENTIRA, ETAPAS_DE_MENTIRA,
                       relatar=relatado.append)
        registros = medida["registros"]
        caso("a ordem dos lados alterna entre as rodadas",
             [(r["rodada"], r["lado"]) for r in registros]
             == [(1, LADO_DA_REFERENCIA), (1, LADO_DO_HEAD),
                 (2, LADO_DO_HEAD), (2, LADO_DA_REFERENCIA)])
        caso("a linha a mais cai na fonte da skill, e a worktree volta ao "
             "commit antes de cada rodada",
             bool(registros) and all(r["etapas"]["conta"]["codigo"] == 0
                                     for r in registros))
        caso("os arquivos sujos contam a linha a mais",
             bool(registros) and all(r["sujos"] == 1 for r in registros))
        caso("os dois lados medem commits diferentes",
             len(set(medida["commits"].values())) == 2)
        nomes = [nome for nome, _ in ETAPAS_DE_MENTIRA]
        caso("etapa que sai diferente de 0 é dita",
             any("cai saiu 1" in linha for linha in relatorio(medida, nomes)))
        caso("etapa que cai faz a medida sair 1", codigo_de_saida(medida) == 1)
        caso("as worktrees e a pasta descartável somem no fim",
             bool(registros) and linhas_do_worktree_list(raiz) == 1
             and not medida["avisos"] and not medida["pasta"].exists())

        falhou = medir(raiz, "nao-existe", 1, SKILL_DE_MENTIRA,
                       ETAPAS_DE_MENTIRA, relatar=relatado.append)
        caso("referência que não existe não monta as worktrees e sai 2",
             codigo_de_saida(falhou) == 2 and not falhou["registros"]
             and linhas_do_worktree_list(raiz) == 1)
        sem_skill = medir(raiz, "HEAD~1", 1, SKILL_SO_DO_HEAD,
                          ETAPAS_DE_MENTIRA, relatar=relatado.append)
        caso("skill que falta num dos lados não mede e desmonta o que montou",
             codigo_de_saida(sem_skill) == 2 and not sem_skill["registros"]
             and linhas_do_worktree_list(raiz) == 1)

        fonte = fonte_da_skill(raiz, SKILL_DE_MENTIRA)
        antes = fonte.read_bytes()
        absoluta = medir(raiz, "HEAD~1", 1, str(fonte.parent),
                         ETAPAS_DE_MENTIRA, relatar=relatado.append)
        caso("skill em caminho absoluto é recusada antes de montar worktree, "
             "e a fonte original não ganha a linha",
             codigo_de_saida(absoluta) == 2 and not absoluta["registros"]
             and absoluta["pasta"] is None and fonte.read_bytes() == antes
             and linhas_do_worktree_list(raiz) == 1)
        recusadas = ("", ".", "..", "alfa/../beta", "alfa/x", "alfa\\x",
                     "C:alfa", str(fonte.parent), "nao-existe")
        caso("--skill só aceita nome simples de pasta que existe em "
             ".agents/skills da raiz",
             all(problema_da_skill(raiz, nome) for nome in recusadas)
             and problema_da_skill(raiz, SKILL_DE_MENTIRA) == "")


def testar() -> int:
    falhas, casos = [], []

    def caso(rotulo, condicao):
        casos.append(rotulo)
        if not condicao:
            falhas.append(rotulo)

    casos_da_mediana(caso)
    casos_da_medida(caso)

    if falhas:
        for falha in falhas:
            print(FALHA_DO_CASO.format(falha))
        print(RESUMO_FALHOU_AQUI.format(len(falhas), len(casos)))
        return 1
    print(RESUMO_OK_AQUI.format(len(casos)))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=USO)
    ap.add_argument("--referencia", required=True, help=AJUDA_DA_REFERENCIA)
    ap.add_argument("--rodadas", type=int, default=RODADAS_PADRAO,
                    help=AJUDA_DAS_RODADAS)
    ap.add_argument("--skill", help=AJUDA_DA_SKILL)
    argumentos = ap.parse_args()
    if argumentos.rodadas < 1:
        ap.error(RODADAS_DE_MENOS)
    codigo, raiz = git(Path.cwd(), "rev-parse", "--show-toplevel")
    if codigo != 0:
        print(FORA_DE_REPOSITORIO.format(raiz), file=sys.stderr)
        return 2
    raiz = Path(raiz)
    skill = argumentos.skill or skill_padrao(raiz)
    if not skill:
        print(SEM_SKILL, file=sys.stderr)
        return 2
    if (problema := problema_da_skill(raiz, skill)):
        print(NAO_MEDIDO_POR.format(problema), file=sys.stderr)
        return 2
    print(CABECALHO.format(skill, argumentos.rodadas, argumentos.referencia))
    try:
        medida = medir(raiz, argumentos.referencia, argumentos.rodadas, skill)
    except (OSError, RuntimeError) as erro:
        print(NAO_MEDIDO_POR.format(erro), file=sys.stderr)
        return 2
    if medida["problema"]:
        print(NAO_MEDIDO_POR.format(medida["problema"]), file=sys.stderr)
        return 2
    for linha in relatorio(medida, [nome for nome, _ in ETAPAS]):
        print(linha)
    return codigo_de_saida(medida)


if __name__ == "__main__":
    for canal in (sys.stdin, sys.stdout, sys.stderr):
        if not getattr(canal, "closed", True) and hasattr(canal, "reconfigure"):
            canal.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(testar() if BANDEIRA_DE_TESTE in sys.argv else main())
