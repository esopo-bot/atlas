import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

BANDEIRA_DE_TESTE = "--testar"
USO = ("busca no acervo pelo ck no modo léxico (BM25: termo e palavra, "
       "ranqueados), com índice em arquivo dentro de cada alvo e nenhum "
       "serviço de pé. É a porta normal para o acervo: não depende de "
       "cliente MCP e nunca pede o modo por significado, que baixaria modelo. "
       "Sem o ck no PATH, avisa numa linha e cai no grep")

ARQUIVO_DOS_ALVOS = ".agents/indice/alvos.json"
CAMPO_DOS_ALVOS = "alvos"
CAMPO_DO_QUE_IGNORAR = "ignorar"
PROGRAMA_DO_CK = "ck"
PASTA_DO_INDICE_DO_CK = ".ck"
LINHAS_QUE_O_CK_GRAVA = (".ck/", ".ckignore")
AMOSTRAS_DO_QUE_O_CK_GRAVA = {".ck/": ".ck/manifest.json",
                              ".ckignore": ".ckignore"}
COMO_INSTALAR_O_CK = ("baixe o zip da sua plataforma nas versões de "
                      "github.com/BeaconBay/ck, confira o SHA-256 e ponha o "
                      "`ck` no PATH (ou `cargo install ck-search`)")
PREFIXO_LONGO_DO_WINDOWS = "\\\\?\\"
QUANTOS_POR_PADRAO = 5
TETO_TOTAL_POR_PADRAO = 30
TETO_MINIMO = 1
TETO_DO_GIT = 30
TEMPO_DA_BUSCA = 600
LETRAS_DO_TRECHO = 160
LETRAS_MINIMAS_DA_PALAVRA = 3
TETO_DE_BYTES_DO_GREP = 1_000_000
AMOSTRA_DE_BINARIO = 4096
PASTAS_QUE_O_GREP_PULA = {"node_modules", "venv", "__pycache__", "vendor",
                          "dist", "build", "target"}
LINHA_DO_GIT_GREP = re.compile(r"^(.*?):(\d+):(.*)$")
PALAVRA = re.compile(r"[\w.\-]+")
SEM_ACHADO_NO_CK = "No matches"

RECUSA_SEM_PERGUNTA = "sem pergunta: diga o que você quer achar, entre aspas"
RECUSA_TETO_INVALIDO = ("--teto-total é o teto de trechos na resposta e "
                        "precisa ser {} ou mais: {} não corta, desliga a "
                        "conta — e resposta sem teto declarado despeja o "
                        "contexto da sessão sem ninguém pedir")
CORTADO_NO_TETO = ("\ncortado no teto de {}: havia {} trecho(s). O resto não "
                   "foi impresso — peça mais com --teto-total, ou estreite "
                   "com --alvo e --quantos")
RECUSA_ALVO_DESCONHECIDO = ("alvo que não existe nem está declarado: {}. Os "
                            "declarados em {}:\n{}")
ALVO_AUSENTE = "  não medido: {} não existe no disco — alvo declarado em outra árvore"
AVISO_SEM_CK = ("sem o `ck` no PATH: a busca cai no grep, por palavra e sem o "
                "ranking do BM25. Para instalar: " + COMO_INSTALAR_O_CK)
AVISO_DO_DENSO = ("--denso não muda nada: o motor é léxico, e o modo por "
                  "significado do ck baixaria modelo")
NAO_MEDIDO_SEM_DENSO = ("não medido: o motor é léxico e não tem denso nem "
                        "híbrido para comparar; a régua medida está em "
                        "conhecimento/indice.md")
EXCLUDE_ACRESCENTADO = ("  {}: {} acrescentado(s) — o índice do ck não "
                        "aparece no git de {}")
GIT_NAO_RESPONDEU = ("  não medido: o git de {} não respondeu ({}) — o .ck/ "
                     "pode aparecer no git status dele")
VAZIA = "  {} — nenhum trecho casou com a pergunta: tente outra palavra"
CABECA = "BUSCA {} — \"{}\" em {} alvo(s)"
MODO_LEXICO = "léxica pelo ck (BM25: termo e palavra)"
MODO_GREP = "por grep (sem o ck)"
LINHA_DO_ALVO = "  {}"
LINHA_DO_ACHADO = "    [{:.3f}] {}:{}"
LINHA_DO_TRECHO = "           {}"
RODAPE = ("\nA pontuação mede palavra em comum, não significado: o BM25 do ck "
          "ou, no grep, a fração das palavras da pergunta que a linha tem.")
FALHOU_A_CHAMADA = "não consegui buscar em {}: {}"


def configuracao(cwd: str = "") -> dict:
    alvo = Path(cwd or ".") / ARQUIVO_DOS_ALVOS
    try:
        return json.loads(alvo.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def o_ck() -> str:
    return shutil.which(PROGRAMA_DO_CK) or ""


def com_barra(caminho) -> str:
    return os.path.normcase(os.path.normpath(str(caminho))).replace(
        "\\", "/").rstrip("/")


def git_da_pasta(pasta, *argumentos) -> tuple:
    feito = subprocess.run(["git", *argumentos], capture_output=True,
                           text=True, encoding="utf-8", errors="replace",
                           timeout=TETO_DO_GIT, cwd=str(pasta))
    return feito.returncode, feito.stdout


def raizes_do_git(cwd: str = "") -> list:
    try:
        codigo, saida = git_da_pasta(cwd or ".", "rev-parse",
                                     "--path-format=absolute",
                                     "--git-common-dir")
    except (OSError, subprocess.SubprocessError):
        return []
    comum = saida.strip()
    return [Path(comum).parent] if codigo == 0 and comum else []


def alvos_declarados(dado: dict, cwd: str = "", raizes=None) -> list:
    raizes = raizes_do_git(cwd) if raizes is None else raizes
    base = Path(raizes[0]) if raizes else Path(cwd or ".")
    declarados = []
    for alvo in dado.get(CAMPO_DOS_ALVOS) or []:
        caminho = Path(alvo).expanduser()
        declarados.append((caminho if caminho.is_absolute()
                           else base / caminho).resolve())
    return declarados


def formas_do_pedido(pedido: str, cwd: str, raizes) -> list:
    caminho = Path(pedido).expanduser()
    if caminho.is_absolute():
        return [caminho]
    return [Path(cwd or ".") / caminho] + [Path(r) / caminho for r in raizes]


def escolher_alvos(pedido: str, declarados: list, cwd: str = "",
                   raizes=()) -> list:
    presentes = [p for p in declarados if p.is_dir()]
    if not pedido:
        return presentes or ([] if declarados else [Path(cwd or ".").resolve()])
    formas = formas_do_pedido(pedido, cwd, raizes)
    iguais = {com_barra(forma) for forma in formas}
    exatos = [p for p in presentes if com_barra(p) in iguais]
    if exatos:
        return exatos
    fim = "/" + com_barra(pedido).strip("/")
    pelo_fim = [p for p in presentes if com_barra(p).endswith(fim)]
    if pelo_fim:
        return pelo_fim
    return [forma.resolve() for forma in formas[:1] if forma.is_dir()]


def ignorado_pelo_git(pasta: Path, amostra: str) -> bool:
    codigo, _ = git_da_pasta(pasta, "check-ignore", "-q", amostra)
    return codigo == 0


def esconder_do_git(pasta: Path) -> str:
    try:
        codigo, _ = git_da_pasta(pasta, "rev-parse", "--is-inside-work-tree")
        if codigo != 0:
            return ""
        faltam = [linha for linha in LINHAS_QUE_O_CK_GRAVA
                  if not ignorado_pelo_git(
                      pasta, AMOSTRAS_DO_QUE_O_CK_GRAVA[linha])]
        if not faltam:
            return ""
        codigo, saida = git_da_pasta(pasta, "rev-parse",
                                     "--path-format=absolute", "--git-path",
                                     "info/exclude")
    except (OSError, subprocess.SubprocessError) as erro:
        return GIT_NAO_RESPONDEU.format(pasta, type(erro).__name__)
    if codigo != 0 or not saida.strip():
        return GIT_NAO_RESPONDEU.format(pasta, f"git saiu {codigo}")
    exclude = Path(saida.strip())
    atual = exclude.read_text(encoding="utf-8") if exclude.is_file() else ""
    novas = [linha for linha in faltam if linha not in atual.splitlines()]
    if not novas:
        return ""
    exclude.parent.mkdir(parents=True, exist_ok=True)
    emenda = "" if not atual or atual.endswith("\n") else "\n"
    with exclude.open("a", encoding="utf-8", newline="\n") as saida_do_arquivo:
        saida_do_arquivo.write(emenda + "\n".join(novas) + "\n")
    return EXCLUDE_ACRESCENTADO.format(exclude, ", ".join(novas), pasta)


def exclusoes_do_ck(dado: dict) -> list:
    nomes = [str(padrao).strip("*/") for padrao
             in dado.get(CAMPO_DO_QUE_IGNORAR) or []]
    return [parte for nome in nomes if nome
            for parte in ("--exclude", nome)]


def relativo_ao_alvo(caminho: str, pasta: Path) -> str:
    limpo = caminho[len(PREFIXO_LONGO_DO_WINDOWS):] \
        if caminho.startswith(PREFIXO_LONGO_DO_WINDOWS) else caminho
    try:
        return os.path.relpath(limpo, str(pasta)).replace("\\", "/")
    except ValueError:
        return limpo.replace("\\", "/")


def achado_do_ck(linha: str, pasta: Path) -> dict:
    dado = json.loads(linha)
    return {"arquivo": relativo_ao_alvo(dado.get("path", "?"), pasta),
            "linha": (dado.get("span") or {}).get("line_start", "?"),
            "trecho": dado.get("snippet", ""),
            "pontos": float(dado.get("score") or 0.0)}


def buscar_pelo_ck(ck: str, pasta: Path, pergunta: str, quantos: int,
                   exclusoes=()) -> list:
    if not (pasta / PASTA_DO_INDICE_DO_CK).is_dir():
        recado = esconder_do_git(pasta)
        if recado:
            print(recado, file=sys.stderr)
    feito = subprocess.run(
        [ck, "--lex", "--jsonl", "-q", "--topk", str(quantos), *exclusoes,
         pergunta, str(pasta)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=TEMPO_DA_BUSCA, cwd=str(pasta))
    if feito.returncode != 0:
        if SEM_ACHADO_NO_CK in feito.stderr + feito.stdout:
            return []
        raise ValueError((feito.stderr or feito.stdout).strip()[-300:]
                         or f"o ck saiu {feito.returncode}")
    return [achado_do_ck(linha, pasta) for linha in feito.stdout.splitlines()
            if linha.strip().startswith("{")]


def palavras_da_pergunta(pergunta: str) -> list:
    palavras = [p for p in PALAVRA.findall(pergunta.lower())
                if len(p) >= LETRAS_MINIMAS_DA_PALAVRA]
    return list(dict.fromkeys(palavras)) or [pergunta.lower().strip()]


def linhas_pelo_git_grep(pasta: Path, palavras: list):
    argumentos = ["grep", "-n", "-I", "-i", "-F", "--no-color", "--untracked"]
    for palavra in palavras:
        argumentos += ["-e", palavra]
    codigo, saida = git_da_pasta(pasta, *argumentos, "--", ".")
    if codigo not in (0, 1):
        raise ValueError(f"git grep saiu {codigo}")
    for linha in saida.splitlines():
        casou = LINHA_DO_GIT_GREP.match(linha)
        if casou:
            yield casou.group(1), int(casou.group(2)), casou.group(3)


def arquivos_de_texto(pasta: Path):
    for raiz, pastas, arquivos in os.walk(pasta):
        pastas[:] = [p for p in pastas if not p.startswith(".")
                     and p not in PASTAS_QUE_O_GREP_PULA]
        for nome in arquivos:
            caminho = Path(raiz) / nome
            try:
                if caminho.stat().st_size > TETO_DE_BYTES_DO_GREP:
                    continue
                conteudo = caminho.read_bytes()
            except OSError:
                continue
            if b"\0" in conteudo[:AMOSTRA_DE_BINARIO]:
                continue
            yield caminho, conteudo.decode("utf-8", errors="replace")


def linhas_pelo_python(pasta: Path, palavras: list):
    for caminho, texto in arquivos_de_texto(pasta):
        relativo = caminho.relative_to(pasta).as_posix()
        for numero, linha in enumerate(texto.splitlines(), 1):
            minuscula = linha.lower()
            if any(palavra in minuscula for palavra in palavras):
                yield relativo, numero, linha


def dentro_do_git(pasta: Path) -> bool:
    try:
        codigo, saida = git_da_pasta(pasta, "rev-parse",
                                     "--is-inside-work-tree")
    except (OSError, subprocess.SubprocessError):
        return False
    return codigo == 0 and saida.strip() == "true"


def buscar_pelo_grep(pasta: Path, pergunta: str, quantos: int) -> list:
    palavras = palavras_da_pergunta(pergunta)
    linhas = (linhas_pelo_git_grep(pasta, palavras) if dentro_do_git(pasta)
              else linhas_pelo_python(pasta, palavras))
    achados = []
    for arquivo, numero, linha in linhas:
        minuscula = linha.lower()
        casadas = sum(1 for palavra in palavras if palavra in minuscula)
        achados.append({"arquivo": arquivo, "linha": numero, "trecho": linha,
                        "pontos": casadas / len(palavras)})
    achados.sort(key=lambda a: (-a["pontos"], a["arquivo"], a["linha"]))
    return achados[:quantos]


def uma_linha(texto: str) -> str:
    return " ".join((texto or "").split())[:LETRAS_DO_TRECHO]


def buscar(pergunta: str, dado: dict, alvo: str = "",
           quantos: int = QUANTOS_POR_PADRAO,
           teto_total: int = TETO_TOTAL_POR_PADRAO, cwd: str = "",
           localizar=o_ck, raizes=None) -> int:
    if not (pergunta or "").strip():
        print(RECUSA_SEM_PERGUNTA, file=sys.stderr)
        return 2
    if teto_total < TETO_MINIMO:
        print(RECUSA_TETO_INVALIDO.format(TETO_MINIMO, teto_total),
              file=sys.stderr)
        return 2
    raizes = raizes_do_git(cwd) if raizes is None else raizes
    declarados = alvos_declarados(dado, cwd, raizes)
    alvos = escolher_alvos(alvo, declarados, cwd, raizes)
    if not alvos:
        print(RECUSA_ALVO_DESCONHECIDO.format(
            alvo, ARQUIVO_DOS_ALVOS,
            "\n".join(f"  {p}" for p in declarados) or "  (nenhum)"),
            file=sys.stderr)
        return 2
    if not alvo:
        for ausente in [p for p in declarados if not p.is_dir()]:
            print(ALVO_AUSENTE.format(ausente), file=sys.stderr)
    ck = localizar()
    if not ck:
        print(AVISO_SEM_CK, file=sys.stderr)
    print(CABECA.format(MODO_LEXICO if ck else MODO_GREP, pergunta,
                        len(alvos)))
    achou = mostrados = 0
    for pasta in alvos:
        try:
            achados = (buscar_pelo_ck(ck, pasta, pergunta, quantos,
                                      exclusoes_do_ck(dado)) if ck
                       else buscar_pelo_grep(pasta, pergunta, quantos))
        except (OSError, subprocess.SubprocessError, ValueError) as erro:
            print(FALHOU_A_CHAMADA.format(pasta, erro), file=sys.stderr)
            continue
        if not achados:
            print(VAZIA.format(pasta))
            continue
        if mostrados < teto_total:
            print(LINHA_DO_ALVO.format(pasta))
        for item in achados:
            achou += 1
            if mostrados >= teto_total:
                continue
            mostrados += 1
            print(LINHA_DO_ACHADO.format(item["pontos"], item["arquivo"],
                                         item["linha"]))
            print(LINHA_DO_TRECHO.format(uma_linha(item["trecho"])))
    if achou > mostrados:
        print(CORTADO_NO_TETO.format(teto_total, achou))
    if achou:
        print(RODAPE)
    return 0 if achou else 1


def testar() -> int:
    import contextlib
    import io
    import tempfile
    falhas, rodados = [], []

    def caso(rotulo, passou):
        rodados.append(rotulo)
        if not passou:
            falhas.append(rotulo)

    def repositorio(pasta: Path, gitignore: str = "") -> None:
        (pasta / "docs").mkdir(parents=True)
        (pasta / "docs" / "a.md").write_text(
            "# Regra\n\nA regra dezesseis cobra destino da entrega.\n",
            encoding="utf-8")
        if gitignore:
            (pasta / ".gitignore").write_text(gitignore, encoding="utf-8")
        git_da_pasta(pasta, "init", "-q")
        git_da_pasta(pasta, "add", ".")
        git_da_pasta(pasta, "-c", "user.email=a@b", "-c", "user.name=a",
                     "commit", "-qm", "x")

    def saida_de(*argumentos, **nomeados):
        fora, erro = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(fora), contextlib.redirect_stderr(erro):
            codigo = buscar(*argumentos, **nomeados)
        return codigo, fora.getvalue(), erro.getvalue()

    with tempfile.TemporaryDirectory(prefix="buscar-") as base:
        base = Path(base)
        vizinho = base / "vizinho"
        repositorio(vizinho, gitignore="*.log\n")
        (vizinho / ".ck").mkdir()
        (vizinho / ".ck" / "manifest.json").write_text("{}", encoding="utf-8")
        (vizinho / ".ckignore").write_text("*.png\n", encoding="utf-8")
        recado = esconder_do_git(vizinho)
        _, status = git_da_pasta(vizinho, "status", "--short")
        exclude = (vizinho / ".git" / "info" / "exclude").read_text(
            encoding="utf-8").splitlines()
        caso("vizinho com git: as duas linhas vão ao exclude dele, e o git "
             "status fica limpo",
             bool(recado) and status.strip() == ""
             and all(linha in exclude for linha in LINHAS_QUE_O_CK_GRAVA))
        caso("o .gitignore rastreado do vizinho não muda",
             (vizinho / ".gitignore").read_text(encoding="utf-8") == "*.log\n")
        caso("a segunda vez não duplica a linha",
             esconder_do_git(vizinho) == ""
             and (vizinho / ".git" / "info" / "exclude").read_text(
                 encoding="utf-8").splitlines().count(".ck/") == 1)

        raiz = base / "raiz"
        repositorio(raiz, gitignore=".ck/\n.ckignore\n")
        antes = (raiz / ".git" / "info" / "exclude").read_text(
            encoding="utf-8")
        caso("repositório cujo .gitignore já esconde o .ck: o exclude não "
             "muda",
             esconder_do_git(raiz) == ""
             and (raiz / ".git" / "info" / "exclude").read_text(
                 encoding="utf-8") == antes)

        solta = base / "solta"
        solta.mkdir()
        (solta / "nota.md").write_text("destino da entrega sem git\n",
                                       encoding="utf-8")
        caso("pasta sem git: nada se escreve", esconder_do_git(solta) == ""
             and sorted(p.name for p in solta.iterdir()) == ["nota.md"])

        sem_ck = lambda: ""
        codigo, fora, erro = saida_de("destino entrega", {}, str(solta),
                                      cwd=str(base), localizar=sem_ck,
                                      raizes=[])
        caso("sem o ck, a busca avisa numa linha e cai no grep em Python, "
             "sem erro",
             codigo == 0 and erro.count("\n") == 1 and "grep" in erro
             and "nota.md:1" in fora and MODO_GREP in fora)
        codigo, fora, erro = saida_de("destino entrega",
                                      {"alvos": [str(vizinho)]}, "vizinho",
                                      cwd=str(base), localizar=sem_ck,
                                      raizes=[])
        caso("sem o ck, num alvo com git, o grep é o git grep e o alvo "
             "declarado casa pelo fim do caminho",
             codigo == 0 and "docs/a.md:3" in fora)
        codigo, _, erro = saida_de("x", {"alvos": [str(vizinho)]},
                                   "nao-existe", cwd=str(base),
                                   localizar=sem_ck, raizes=[])
        caso("alvo que não existe nem está declarado é recusado pelo nome, "
             "com a lista dos declarados",
             codigo == 2 and "nao-existe" in erro and str(vizinho) in erro)
        muitos = base / "muitos"
        muitos.mkdir()
        (muitos / "tres.md").write_text("destino\ndestino\ndestino\n",
                                        encoding="utf-8")
        codigo, fora, _ = saida_de("destino", {}, str(muitos), quantos=5,
                                   teto_total=1, cwd=str(base),
                                   localizar=sem_ck, raizes=[])
        caso("teto-total corta e diz quanto havia",
             codigo == 0 and "cortado no teto de 1: havia 3" in fora
             and fora.count("tres.md:") == 1)

        achado = achado_do_ck(json.dumps({
            "path": PREFIXO_LONGO_DO_WINDOWS + str(vizinho / "docs" / "a.md"),
            "span": {"line_start": 3}, "snippet": "A regra", "score": 0.5}),
            vizinho)
        caso("o achado do ck vira arquivo relativo ao alvo e linha, sem o "
             "prefixo longo do Windows",
             achado["arquivo"] == "docs/a.md" and achado["linha"] == 3)
        caso("o ignorar dos alvos vira --exclude do ck pelo nome da pasta",
             exclusoes_do_ck({"ignorar": ["**/vendor/**"]})
             == ["--exclude", "vendor"])

        if o_ck():
            novo = base / "novo"
            repositorio(novo)
            codigo, fora, _ = saida_de("destino entrega", {}, str(novo),
                                       cwd=str(base), raizes=[])
            _, status = git_da_pasta(novo, "status", "--short")
            caso("com o ck, a busca léxica indexa na primeira vez, devolve "
                 "arquivo:linha e o trecho, e o git do alvo fica limpo",
                 codigo == 0 and "docs/a.md:" in fora and MODO_LEXICO in fora
                 and (novo / PASTA_DO_INDICE_DO_CK).is_dir()
                 and status.strip() == "")
        else:
            print("não medido: o ck não está no PATH — o caso da busca real "
                  "não rodou")

    if falhas:
        for f in falhas:
            print(f"FALHOU: {f}")
        print(f"FALHOU: {len(falhas)} de {len(rodados)} casos")
        return 1
    print(f"OK: a busca do índice — {len(rodados)} casos")
    return 0


def montar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=USO)
    parser.add_argument("pergunta", nargs="?", default="",
                        help="o termo exato ou as palavras que o trecho tem")
    parser.add_argument("--alvo", default="",
                        help="busca só neste alvo: o fim do caminho de um "
                             "declarado ou uma pasta (padrão: todos os "
                             "declarados)")
    parser.add_argument("--quantos", type=int, default=QUANTOS_POR_PADRAO,
                        help="trechos por alvo")
    parser.add_argument("--teto-total", type=int,
                        default=TETO_TOTAL_POR_PADRAO,
                        help="teto de trechos na resposta inteira, somando "
                             "os alvos; o que passar do teto não é impresso "
                             "e a resposta diz quanto havia")
    parser.add_argument("--denso", action="store_true",
                        help="não muda nada: o motor é léxico")
    parser.add_argument("--medir", action="store_true",
                        help="não medido: o motor é léxico")
    parser.add_argument("--cwd", default=".")
    parser.add_argument(BANDEIRA_DE_TESTE, action="store_true")
    return parser


def main() -> int:
    if BANDEIRA_DE_TESTE in sys.argv[1:]:
        return testar()
    a = montar_parser().parse_args()
    if a.medir:
        print(NAO_MEDIDO_SEM_DENSO)
        return 1
    if a.denso:
        print(AVISO_DO_DENSO, file=sys.stderr)
    return buscar(a.pergunta, configuracao(a.cwd), a.alvo, a.quantos,
                  a.teto_total, a.cwd)


if __name__ == "__main__":
    for canal in (sys.stdin, sys.stdout, sys.stderr):
        if not getattr(canal, "closed", True) and hasattr(canal, "reconfigure"):
            canal.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
