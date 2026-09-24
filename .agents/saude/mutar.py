import argparse
import contextlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

BANDEIRA_DE_TESTE = "--testar"
USO = ("a mutação no fim: prova que a bancada de uma peça enxerga a peça. "
       "Copia a árvore para uma pasta descartável, desfaz cada peça por troca "
       "de texto e roda os --testar escolhidos.")
AJUDA_DAS_MUTACOES = ('arquivo JSON com a lista de mutações, cada uma '
                      '{"nome", "arquivo", "trocar", "por", "testar": [...]}; '
                      'uma mutação sozinha é uma lista de um')

MORTA = "MORTA"
VIVA = "VIVA"
NAO_MEDIDA = "NÃO MEDIDA"
CAMPOS_DE_TEXTO = ("nome", "arquivo", "trocar", "por")
CAMPO_DAS_BANCADAS = "testar"
TEMPO_DE_UMA_BANCADA = 600
PREFIXO_DA_COPIA = "atlas-mutar-"
LISTAR_A_ARVORE = ("git", "ls-files", "-z", "--cached", "--others",
                   "--exclude-standard")
PREPARAR_A_COPIA = (("git", "init", "-q"), ("git", "add", "-A"))
RAIZ_DO_REPOSITORIO = ("git", "rev-parse", "--show-toplevel")
OPCAO_DO_MODO_UTF8 = ("-X", "utf8")
CHAVE_SEM_BYTECODE = "PYTHONDONTWRITEBYTECODE"
SEM_BYTECODE_EM_DISCO = {CHAVE_SEM_BYTECODE: "1"}
FIM_DE_LINHA_DO_WINDOWS = "\r\n"
VOLTAS_DA_LIMPEZA = 3
PAUSA_ENTRE_AS_VOLTAS_S = 1.0
LINHAS_DA_QUEDA = 4

ENTRADA_NAO_E_LISTA = ("a entrada tem de ser uma lista de mutações; uma "
                       "mutação sozinha é uma lista de um")
ENTRADA_VAZIA = "a lista de mutações está vazia: nada a medir"
MUTACAO_NAO_E_OBJETO = "mutação {}: tem de ser um objeto"
CAMPO_QUE_FALTA = "mutação {}: falta o campo de texto {!r}"
BANCADAS_QUE_FALTAM = ("mutação {}: o campo 'testar' tem de ser uma lista não "
                       "vazia de caminhos de instrumento")
TROCA_QUE_NAO_TROCA = ("mutação {}: 'trocar' e 'por' são iguais, e a troca "
                       "não desfaz nada")

MOTIVO_BANCADA_VERMELHA = "a bancada {} já cai sem mutação (saída {})"
MOTIVO_BANCADA_ESGOTADA = "a bancada {} esgotou {} s sem mutação"
MOTIVO_FORA_DA_COPIA = ("{} cai fora da cópia da árvore — caminho absoluto "
                        "ou que escapa dela mediria o original, não a "
                        "mutação; use o caminho relativo à raiz")
MOTIVO_ARQUIVO_AUSENTE = "{} não existe na cópia da árvore"
MOTIVO_NAO_E_TEXTO = "{} não é texto UTF-8"
MOTIVO_DO_TRECHO = ("o trecho aparece {} vez(es) em {}, e a troca exige "
                    "exatamente uma")
MOTIVO_ESGOTADA = "{} esgotou {} s com a mutação"
MOTIVO_MORTA = "caiu: {} — a bancada enxerga a peça"
MOTIVO_VIVA = "passaram: {} — a bancada NÃO enxerga a peça"
QUEDA = "{} (saída {})"

CABECALHO = "mutação no fim — {} mutação(ões) numa cópia de {}"
LINHA_DO_VEREDITO = "{:<11} {} — {}"
LINHA_DA_SAIDA = "              {}"
RESUMO = "resumo: {} MORTA, {} VIVA, {} NÃO MEDIDA"
ENTRADA_RECUSADA = "NÃO MEDIDA: a entrada foi recusada —\n{}"
COPIA_FALHOU = "NÃO MEDIDA: a cópia da árvore falhou — {}"
COPIA_FICOU = ("AVISO: a cópia descartável {} não saiu do disco em {} "
               "tentativas; o veredito vale, o disco ficou com sobra")

FALHA_DO_CASO = "  [{}]"
RESUMO_FALHOU_AQUI = "FALHOU: {} de {} casos"
RESUMO_OK_AQUI = ("OK: {} casos — veredito da mutação, cópia descartável e "
                  "entrada")
PECA_DE_MENTIRA = ("def dobro(x):\n    return x * 2\n\n\n"
                   "def metade(x):\n    return x / 2\n")
QUEDA_DA_BANCADA_DE_MENTIRA = "FALHOU: o dobro de 2"
BANCADA_DE_MENTIRA = (
    "import sys\nfrom peca import dobro\nprint('linha de sempre')\n"
    "falhou = dobro(2) != 4\n"
    f"print({QUEDA_DA_BANCADA_DE_MENTIRA!r} if falhou else 'OK: 1 caso')\n"
    "sys.exit(1 if falhou else 0)\n")
BANCADA_VERMELHA_DE_MENTIRA = "import sys\nsys.exit(1)\n"
IGNORADO_DE_MENTIRA = "ignorado.txt"


def problemas_da_mutacao(posicao: int, mutacao) -> list:
    if not isinstance(mutacao, dict):
        return [MUTACAO_NAO_E_OBJETO.format(posicao)]
    problemas = [CAMPO_QUE_FALTA.format(posicao, campo)
                 for campo in CAMPOS_DE_TEXTO
                 if not isinstance(mutacao.get(campo), str)]
    bancadas = mutacao.get(CAMPO_DAS_BANCADAS)
    if not (isinstance(bancadas, list) and bancadas
            and all(isinstance(b, str) and b for b in bancadas)):
        problemas.append(BANCADAS_QUE_FALTAM.format(posicao))
    if not problemas and mutacao["trocar"] == mutacao["por"]:
        problemas.append(TROCA_QUE_NAO_TROCA.format(posicao))
    return problemas


def mutacoes_validas(dado) -> list:
    if not isinstance(dado, list):
        raise ValueError(ENTRADA_NAO_E_LISTA)
    if not dado:
        raise ValueError(ENTRADA_VAZIA)
    problemas = [problema for posicao, mutacao in enumerate(dado, 1)
                 for problema in problemas_da_mutacao(posicao, mutacao)]
    if problemas:
        raise ValueError("\n".join(problemas))
    return dado


def raiz_do_repositorio(pasta: Path) -> Path:
    saida = subprocess.run(RAIZ_DO_REPOSITORIO, cwd=pasta, capture_output=True,
                           text=True, encoding="utf-8", errors="replace",
                           check=True).stdout
    return Path(saida.strip())


def arquivos_da_arvore(raiz: Path) -> list:
    saida = subprocess.run(LISTAR_A_ARVORE, cwd=raiz, capture_output=True,
                           check=True).stdout
    return sorted({nome for nome in saida.decode("utf-8").split("\0") if nome})


def copiar_a_arvore(raiz: Path, copia: Path) -> None:
    for nome in arquivos_da_arvore(raiz):
        origem = raiz / nome
        if origem.is_file():
            destino = copia / nome
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(origem, destino)
    for comando in PREPARAR_A_COPIA:
        subprocess.run(comando, cwd=copia, capture_output=True, check=True)


def rodar_a_bancada(copia: Path, bancada: str, tempo: int) -> tuple:
    try:
        r = subprocess.run(
            [sys.executable, *OPCAO_DO_MODO_UTF8, bancada, BANDEIRA_DE_TESTE],
            cwd=copia, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=tempo,
            env={**os.environ, **SEM_BYTECODE_EM_DISCO})
    except subprocess.TimeoutExpired:
        return None, ""
    return r.returncode, (r.stdout + r.stderr).strip()


def bancadas_citadas(mutacoes: list) -> list:
    return list(dict.fromkeys(bancada for mutacao in mutacoes
                              for bancada in mutacao[CAMPO_DAS_BANCADAS]))


def fora_da_copia(copia: Path, nome: str) -> bool:
    caminho = Path(nome)
    if caminho.is_absolute() or caminho.drive or caminho.root:
        return True
    return not (copia / caminho).resolve().is_relative_to(copia.resolve())


def rodar_o_controle(copia: Path, bancadas: list, tempo: int) -> dict:
    return {bancada: rodar_a_bancada(copia, bancada, tempo)
            for bancada in bancadas if not fora_da_copia(copia, bancada)}


def motivo_do_controle(bancada: str, codigo, tempo: int) -> str:
    if codigo is None:
        return MOTIVO_BANCADA_ESGOTADA.format(bancada, tempo)
    if codigo != 0:
        return MOTIVO_BANCADA_VERMELHA.format(bancada, codigo)
    return ""


def no_fim_de_linha_do(texto: str, trecho: str) -> str:
    if FIM_DE_LINHA_DO_WINDOWS not in texto:
        return trecho
    return trecho.replace(FIM_DE_LINHA_DO_WINDOWS, "\n").replace(
        "\n", FIM_DE_LINHA_DO_WINDOWS)


def linhas_que_mudaram(saida: str, do_controle: str) -> list:
    vistas = set(do_controle.splitlines())
    cheias = [linha for linha in saida.splitlines() if linha.strip()]
    novas = [linha for linha in cheias if linha not in vistas]
    return novas[:LINHAS_DA_QUEDA] if novas else cheias[-LINHAS_DA_QUEDA:]


def veredito(mutacao: dict, tipo: str, motivo: str, saidas=()) -> dict:
    return {"nome": mutacao["nome"], "veredito": tipo, "motivo": motivo,
            "saidas": list(saidas)}


def veredito_das_rodadas(mutacao: dict, rodadas: list, tempo: int,
                         controle=None) -> dict:
    caidas = [(b, codigo, saida) for b, codigo, saida in rodadas
              if codigo not in (0, None)]
    if caidas:
        bancada, _, saida = caidas[0]
        return veredito(mutacao, MORTA, MOTIVO_MORTA.format(", ".join(
            QUEDA.format(b, codigo) for b, codigo, _ in caidas)),
            linhas_que_mudaram(saida, (controle or {}).get(bancada,
                                                           (0, ""))[1]))
    esgotadas = [b for b, codigo, _ in rodadas if codigo is None]
    if esgotadas:
        return veredito(mutacao, NAO_MEDIDA,
                        MOTIVO_ESGOTADA.format(", ".join(esgotadas), tempo))
    return veredito(mutacao, VIVA,
                    MOTIVO_VIVA.format(", ".join(b for b, _, _ in rodadas)))


def julgar_a_mutacao(copia: Path, mutacao: dict, controle: dict,
                     tempo: int) -> dict:
    nome = mutacao["arquivo"]
    fora = [caminho for caminho in [nome, *mutacao[CAMPO_DAS_BANCADAS]]
            if fora_da_copia(copia, caminho)]
    if fora:
        return veredito(mutacao, NAO_MEDIDA,
                        MOTIVO_FORA_DA_COPIA.format(", ".join(fora)))
    presas = [motivo for b in mutacao[CAMPO_DAS_BANCADAS]
              if (motivo := motivo_do_controle(b, controle[b][0], tempo))]
    if presas:
        return veredito(mutacao, NAO_MEDIDA, "; ".join(presas))
    arquivo = copia / nome
    if not arquivo.is_file():
        return veredito(mutacao, NAO_MEDIDA,
                        MOTIVO_ARQUIVO_AUSENTE.format(nome))
    original = arquivo.read_bytes()
    try:
        texto = original.decode("utf-8")
    except UnicodeDecodeError:
        return veredito(mutacao, NAO_MEDIDA, MOTIVO_NAO_E_TEXTO.format(nome))
    trocar = no_fim_de_linha_do(texto, mutacao["trocar"])
    vezes = texto.count(trocar)
    if vezes != 1:
        return veredito(mutacao, NAO_MEDIDA,
                        MOTIVO_DO_TRECHO.format(vezes, nome))
    por = no_fim_de_linha_do(texto, mutacao["por"])
    try:
        arquivo.write_bytes(texto.replace(trocar, por).encode("utf-8"))
        rodadas = [(b, *rodar_a_bancada(copia, b, tempo))
                   for b in mutacao[CAMPO_DAS_BANCADAS]]
    finally:
        arquivo.write_bytes(original)
    return veredito_das_rodadas(mutacao, rodadas, tempo, controle)


def liberar_o_somente_leitura(pasta: Path) -> None:
    for achado in pasta.rglob("*"):
        with contextlib.suppress(OSError):
            achado.chmod(achado.stat().st_mode | stat.S_IWRITE)


def apagar_a_copia(pasta: Path) -> bool:
    for volta in range(VOLTAS_DA_LIMPEZA):
        if volta:
            time.sleep(PAUSA_ENTRE_AS_VOLTAS_S)
        liberar_o_somente_leitura(pasta)
        shutil.rmtree(pasta, ignore_errors=True)
        if not pasta.exists():
            return True
    return False


def relatar_o_veredito(dado: dict, relatar) -> None:
    relatar(LINHA_DO_VEREDITO.format(dado["veredito"], dado["nome"],
                                     dado["motivo"]))
    for linha in dado["saidas"]:
        relatar(LINHA_DA_SAIDA.format(linha))


def mutar(raiz: Path, mutacoes: list, tempo=TEMPO_DE_UMA_BANCADA,
          relatar=print) -> tuple:
    copia = Path(tempfile.mkdtemp(prefix=PREFIXO_DA_COPIA))
    vereditos = []
    try:
        copiar_a_arvore(raiz, copia)
        controle = rodar_o_controle(copia, bancadas_citadas(mutacoes), tempo)
        for mutacao in mutacoes:
            vereditos.append(julgar_a_mutacao(copia, mutacao, controle,
                                              tempo))
            relatar_o_veredito(vereditos[-1], relatar)
    finally:
        saiu = apagar_a_copia(copia)
        if not saiu:
            relatar(COPIA_FICOU.format(copia, VOLTAS_DA_LIMPEZA))
    return vereditos, copia, saiu


def codigo_de_saida(vereditos: list) -> int:
    tipos = {dado["veredito"] for dado in vereditos}
    if VIVA in tipos:
        return 1
    if NAO_MEDIDA in tipos:
        return 2
    return 0


def resumo(vereditos: list) -> str:
    tipos = [dado["veredito"] for dado in vereditos]
    return RESUMO.format(tipos.count(MORTA), tipos.count(VIVA),
                         tipos.count(NAO_MEDIDA))


def recusa(dado) -> str:
    try:
        mutacoes_validas(dado)
    except ValueError as erro:
        return str(erro)
    return ""


def mutacao_de_mentira(nome, trocar, por, bancada="bancada.py",
                       arquivo="peca.py") -> dict:
    return {"nome": nome, "arquivo": arquivo, "trocar": trocar, "por": por,
            "testar": [bancada]}


def veredito_de_mentira(tipo: str) -> dict:
    return {"nome": tipo, "veredito": tipo, "motivo": "", "saidas": []}


def montar_o_repositorio_de_mentira(raiz: Path) -> None:
    (raiz / "peca.py").write_text(PECA_DE_MENTIRA, encoding="utf-8")
    (raiz / "bancada.py").write_text(BANCADA_DE_MENTIRA, encoding="utf-8")
    (raiz / "vermelha.py").write_text(BANCADA_VERMELHA_DE_MENTIRA,
                                      encoding="utf-8")
    (raiz / ".gitignore").write_text(IGNORADO_DE_MENTIRA + "\n",
                                     encoding="utf-8")
    (raiz / IGNORADO_DE_MENTIRA).write_text("x * 2\n", encoding="utf-8")
    for comando in (("git", "init", "-q"),
                    ("git", "add", "bancada.py", ".gitignore")):
        subprocess.run(comando, cwd=raiz, capture_output=True, check=True)


def casos_da_entrada(caso) -> None:
    completa = mutacao_de_mentira("inteira", "a", "b")
    caso("entrada que não é lista é recusada", recusa(completa) != "")
    caso("lista vazia é recusada", recusa([]) != "")
    sem_bancada = {c: v for c, v in completa.items() if c != "testar"}
    caso("mutação sem o campo testar é recusada, e o recado diz o campo",
         "testar" in recusa([sem_bancada]))
    caso("troca que não troca nada é recusada",
         recusa([mutacao_de_mentira("igual", "a", "a")]) != "")
    caso("mutação completa passa pela entrada", recusa([completa]) == ""
         and mutacoes_validas([completa]) == [completa])


def casos_do_veredito(caso) -> None:
    mutacao = mutacao_de_mentira("m", "a", "b")
    caso("bancada que esgota o tempo sem outra cair é NÃO MEDIDA",
         veredito_das_rodadas(mutacao, [("b.py", None, "")], 5)
         .get("veredito") == NAO_MEDIDA)
    caso("uma bancada que cai basta para MORTA, mesmo com outra esgotada",
         veredito_das_rodadas(mutacao, [("a.py", 1, "x"), ("b.py", None, "")],
                              5).get("veredito") == MORTA)
    caso("trecho de várias linhas casa com arquivo em CRLF",
         no_fim_de_linha_do("a\r\nb\r\n", "a\nb") == "a\r\nb")
    caso("arquivo em LF deixa o trecho como veio",
         no_fim_de_linha_do("a\nb\n", "a\nb") == "a\nb")
    caso("alguma VIVA sai 1", codigo_de_saida(
        [veredito_de_mentira(t) for t in (MORTA, VIVA, NAO_MEDIDA)]) == 1)
    caso("sem VIVA e com NÃO MEDIDA sai 2", codigo_de_saida(
        [veredito_de_mentira(t) for t in (MORTA, NAO_MEDIDA)]) == 2)
    caso("todas MORTAS sai 0", codigo_de_saida(
        [veredito_de_mentira(t) for t in (MORTA, MORTA)]) == 0)


def casos_do_bytecode(caso) -> None:
    with tempfile.TemporaryDirectory(prefix="mutar-bytecode-") as pasta:
        raiz = Path(pasta)
        (raiz / "peca.py").write_text(PECA_DE_MENTIRA, encoding="utf-8")
        (raiz / "bancada.py").write_text(BANCADA_DE_MENTIRA, encoding="utf-8")
        herdado = os.environ.pop(CHAVE_SEM_BYTECODE, None)
        try:
            codigo, _ = rodar_a_bancada(raiz, "bancada.py",
                                        TEMPO_DE_UMA_BANCADA)
        finally:
            if herdado is not None:
                os.environ[CHAVE_SEM_BYTECODE] = herdado
        caso("a bancada roda sem gravar bytecode em disco, mesmo com o "
             "ambiente de fora sem a variável — troca de mesmo tamanho no "
             "mesmo segundo reusaria o da mutação anterior",
             codigo == 0 and not (raiz / "__pycache__").exists())


def casos_da_mutacao(caso) -> None:
    with tempfile.TemporaryDirectory(prefix="mutar-teste-") as pasta:
        raiz = Path(pasta)
        montar_o_repositorio_de_mentira(raiz)
        original = (raiz / "peca.py").read_bytes()
        mutacoes = [
            mutacao_de_mentira("dobro triplica", "x * 2", "x * 3"),
            mutacao_de_mentira("metade quarteia", "x / 2", "x / 4"),
            mutacao_de_mentira("trecho ausente", "x * 9", "x"),
            mutacao_de_mentira("trecho repetido", "return", "yield"),
            mutacao_de_mentira("bancada vermelha", "x * 2", "x * 5",
                               bancada="vermelha.py"),
            mutacao_de_mentira("arquivo ignorado", "x * 2", "x * 7",
                               arquivo=IGNORADO_DE_MENTIRA),
            mutacao_de_mentira("fora da cópia", "x", "y",
                               arquivo="../fora.py"),
            mutacao_de_mentira("bancada em caminho absoluto", "x * 2", "x * 3",
                               bancada=str(raiz / "bancada.py")),
            mutacao_de_mentira("bancada que escapa da cópia", "x * 2",
                               "x * 3",
                               bancada=f"../{raiz.name}/bancada.py"),
            mutacao_de_mentira("peça em caminho absoluto", "x * 2", "x * 3",
                               arquivo=str(raiz / "peca.py")),
        ]
        vereditos, copia, saiu = mutar(raiz, mutacoes,
                                       relatar=lambda _linha: None)
        por_nome = {v["nome"]: v for v in vereditos}

        def tipo(nome):
            return por_nome.get(nome, {}).get("veredito")

        def motivo(nome):
            return por_nome.get(nome, {}).get("motivo", "")

        caso("a mutação que a bancada pega sai MORTA — e a peça fora do "
             "índice chegou à cópia", tipo("dobro triplica") == MORTA)
        caso("a MORTA diz qual bancada caiu",
             "bancada.py" in motivo("dobro triplica"))
        caso("a MORTA mostra só o que a bancada disse de diferente do "
             "controle, e é ali que está o caso que caiu",
             por_nome.get("dobro triplica", {}).get("saidas")
             == [QUEDA_DA_BANCADA_DE_MENTIRA])
        caso("a mutação que a bancada não pega sai VIVA — o que só acontece "
             "se a peça voltou ao original depois da MORTA e se nenhum "
             "bytecode da troca anterior, de mesmo tamanho e no mesmo "
             "segundo, ficou em disco",
             tipo("metade quarteia") == VIVA)
        caso("trecho ausente é NÃO MEDIDA, com a contagem",
             tipo("trecho ausente") == NAO_MEDIDA
             and "0 vez" in motivo("trecho ausente"))
        caso("trecho que aparece duas vezes é NÃO MEDIDA, com a contagem",
             tipo("trecho repetido") == NAO_MEDIDA
             and "2 vez" in motivo("trecho repetido"))
        caso("bancada que já cai sem mutação torna a mutação NÃO MEDIDA e "
             "é nomeada", tipo("bancada vermelha") == NAO_MEDIDA
             and "vermelha.py" in motivo("bancada vermelha")
             and "sem mutação" in motivo("bancada vermelha"))
        caso("arquivo que o git ignora não entra na cópia",
             tipo("arquivo ignorado") == NAO_MEDIDA
             and "não existe" in motivo("arquivo ignorado"))
        caso("arquivo fora da árvore não é tocado",
             tipo("fora da cópia") == NAO_MEDIDA
             and "fora da cópia" in motivo("fora da cópia"))
        caso("bancada em caminho absoluto é NÃO MEDIDA — ela rodaria o "
             "original, fora da cópia mutada, e sairia VIVA por engano",
             tipo("bancada em caminho absoluto") == NAO_MEDIDA
             and "fora da cópia" in motivo("bancada em caminho absoluto"))
        caso("bancada que escapa da cópia por .. também é NÃO MEDIDA",
             tipo("bancada que escapa da cópia") == NAO_MEDIDA
             and "fora da cópia" in motivo("bancada que escapa da cópia"))
        caso("peça em caminho absoluto é NÃO MEDIDA, e o original não muda",
             tipo("peça em caminho absoluto") == NAO_MEDIDA
             and "fora da cópia" in motivo("peça em caminho absoluto"))
        caso("a peça da raiz não muda",
             (raiz / "peca.py").read_bytes() == original)
        caso("a cópia descartável sai do disco no fim",
             bool(vereditos) and saiu and not copia.exists())


def testar() -> int:
    falhas, casos = [], []

    def caso(rotulo, condicao):
        casos.append(rotulo)
        if not condicao:
            falhas.append(rotulo)

    casos_da_entrada(caso)
    casos_do_veredito(caso)
    casos_do_bytecode(caso)
    casos_da_mutacao(caso)

    if falhas:
        for falha in falhas:
            print(FALHA_DO_CASO.format(falha))
        print(RESUMO_FALHOU_AQUI.format(len(falhas), len(casos)))
        return 1
    print(RESUMO_OK_AQUI.format(len(casos)))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=USO)
    ap.add_argument("--mutacoes", required=True, help=AJUDA_DAS_MUTACOES)
    argumentos = ap.parse_args()
    try:
        mutacoes = mutacoes_validas(json.loads(
            Path(argumentos.mutacoes).read_text(encoding="utf-8")))
    except (OSError, ValueError) as erro:
        print(ENTRADA_RECUSADA.format(erro), file=sys.stderr)
        return 2
    try:
        raiz = raiz_do_repositorio(Path.cwd())
        print(CABECALHO.format(len(mutacoes), raiz))
        vereditos, _, _ = mutar(raiz, mutacoes)
    except (OSError, subprocess.CalledProcessError) as erro:
        print(COPIA_FALHOU.format(erro), file=sys.stderr)
        return 2
    print(resumo(vereditos))
    return codigo_de_saida(vereditos)


if __name__ == "__main__":
    for canal in (sys.stdin, sys.stdout, sys.stderr):
        if not getattr(canal, "closed", True) and hasattr(canal, "reconfigure"):
            canal.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(testar() if BANDEIRA_DE_TESTE in sys.argv else main())
